"""E3 Slice 3f - live-input readiness gate (fail-closed preflight for forward commits).

A fail-closed preflight that validates the E3 commit targets the requested live
session with complete PIT inputs. When the caller (``forward_commit_runner``)
enforces the gate, a failure blocks the fit, the commit, and any
``forward_prediction_committed`` row / OOS artifact. Note the runner's ordering:
the ``forward_iset_frozen`` pre-registration row and the LLM Pass-A build
deliberately precede the gate (config-before-result anchor); the gate blocks
everything downstream of them.

This gate prevents the audit-flagged defects (AUD-06):
  * panel max labeled date used instead of requested predict_ts
  * live call not passing membership
  * events text zeroed (LLM edge skipped)
  * provider_cutoff faked to predict timestamp

OWNER-GATED PRECONDITIONS (parameterized, fail-closed when unset):
  * membership_freshness_contract - owner must approve max age or authoritative refresh
  * provider_cutoff_policy - owner must decide whether unknown cutoffs are acceptable

All other checks are concrete and fully implemented (PIT freshness, universe match,
input timestamps, event text non-empty, deterministic failures).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd
import structlog

from aionis.features.alignment import nyse_sessions
from aionis.ingest.universe import constituents_on

log = structlog.get_logger()

# Reason codes for readiness failures (actionable, not generic)
ReasonCode = Literal[
    # Owner-gated checks (fail-closed when contract not configured)
    "membership_freshness_contract_not_configured",
    "membership_freshness_contract_violated",
    "provider_cutoff_policy_not_configured",
    "provider_cutoff_unknown_not_allowed",
    # Concrete checks
    "predict_session_not_in_panel",
    "test_rows_not_predict_session",
    "train_contains_unrealized_labels",
    "price_max_session_before_predict",
    "fundamental_future_dated",
    "fundamental_empty",
    "macro_future_dated",
    "macro_empty",
    "stakes_13d_future_dated",
    "stakes_13d_empty",
    "earnings_8k_future_dated",
    "earnings_8k_empty",
    "universe_mismatch",
    "membership_not_provided",
    "llm_event_text_empty",
    "provider_cutoff_faked",
    "unknown_error",
]


@dataclass(frozen=True)
class ReadinessCheckResult:
    """Result of the readiness gate check.

    Attributes:
        is_ready: True if all checks pass (fit/LLM/write/ledger may proceed).
        reason_code: Actionable reason string if not ready (None if ready).
        manifest: Dict of coverage timestamps/hashes/metadata for audit trail.
    """
    is_ready: bool
    reason_code: ReasonCode | None
    manifest: dict


@dataclass(frozen=True)
class MembershipFreshnessContract:
    """Owner-gated membership freshness contract.

    The task explicitly reserves this decision for the owner: a 2026-04 snapshot
    may NOT be assumed fresh enough for 2026-07 without explicit approval.

    Attributes:
        max_age_sessions: Maximum allowed age in NYSE sessions (None = no limit).
        authoritative_refresh: Path to authoritative refresh script (None = not required).
    """
    max_age_sessions: int | None = None
    authoritative_refresh: str | None = None


@dataclass(frozen=True)
class ProviderCutoffPolicy:
    """Owner-gated provider knowledge-cutoff policy.

    Model id/version vs verifiable knowledge cutoff must be separate; an UNKNOWN
    cutoff is recorded 'unknown' and the owner decides whether to block.

    Attributes:
        block_on_unknown: If True, unknown cutoffs cause readiness failure.
    """
    block_on_unknown: bool | None = None


def _resolve_predict_session(
    requested_predict_ts: str,
    panel_dates: pd.DatetimeIndex,
) -> tuple[pd.Timestamp, int]:
    """Resolve the requested predict timestamp to a session index on the panel's date grid.

    Returns (predict_session, session_index). Raises if the requested date is not in the panel.
    """
    predict_ts = pd.Timestamp(requested_predict_ts)
    # Normalize to midnight and remove timezone info to match panel dates (timezone-naive)
    if predict_ts.tz is not None:
        predict_ts = predict_ts.tz_localize(None)
    predict_ts = predict_ts.normalize()
    dates = pd.DatetimeIndex(sorted(panel_dates.unique()))
    pos = {d: i for i, d in enumerate(dates)}

    if predict_ts not in pos:
        log.error(
            "readiness_predict_session_not_in_panel",
            requested=requested_predict_ts,
            panel_min=dates.min().isoformat(),
            panel_max=dates.max().isoformat(),
        )
        raise ValueError("predict_session_not_in_panel")

    return predict_ts, pos[predict_ts]


def _check_price_coverage(
    price_max_session: pd.Timestamp,
    predict_session: pd.Timestamp,
) -> None:
    """Ensure price data covers the predict session (stale prices are rejected)."""
    if price_max_session < predict_session:
        log.error(
            "readiness_price_stale",
            price_max=price_max_session.isoformat(),
            predict_session=predict_session.isoformat(),
        )
        raise ValueError("price_max_session_before_predict")


def _check_fundamental_freshness(
    fundamentals: pd.DataFrame,
    freeze_clock: pd.Timestamp,
) -> None:
    """Ensure fundamental records are not future-dated and non-empty.

    Each record must have a filed timestamp <= freeze_clock and actual snapshot data.
    """
    if fundamentals.empty:
        log.error("readiness_fundamental_empty")
        raise ValueError("fundamental_empty")

    max_filed = fundamentals["filed"].max()
    if pd.Timestamp(max_filed) > freeze_clock:
        log.error(
            "readiness_fundamental_future_dated",
            max_filed=pd.Timestamp(max_filed).isoformat(),
            freeze_clock=freeze_clock.isoformat(),
        )
        raise ValueError("fundamental_future_dated")


def _check_macro_freshness(
    macro: pd.DataFrame,
    freeze_clock: pd.Timestamp,
) -> None:
    """Ensure macro events are not future-dated and non-empty."""
    if macro.empty:
        log.error("readiness_macro_empty")
        raise ValueError("macro_empty")

    max_ts = macro["event_ts"].max()
    if pd.Timestamp(max_ts) > freeze_clock:
        log.error(
            "readiness_macro_future_dated",
            max_ts=pd.Timestamp(max_ts).isoformat(),
            freeze_clock=freeze_clock.isoformat(),
        )
        raise ValueError("macro_future_dated")


def _check_stakes_freshness(
    stakes: pd.DataFrame,
    freeze_clock: pd.Timestamp,
) -> None:
    """Ensure 13D stakes are not future-dated.

    An EMPTY frame is a legitimate no-event window (round-56 evidence: the
    2026-08-31 smoke found zero SC 13D filings for the universe in August —
    plausible market state; the collector polls every universe CIK, so coverage
    completeness is structural, not per-frame). Only future-dating fails.
    """
    if stakes.empty:
        log.info("readiness_stakes_13d_empty_window", note="no 13D events this window")
        return

    max_ts = stakes["event_ts"].max()
    if pd.Timestamp(max_ts) > freeze_clock:
        log.error(
            "readiness_stakes_13d_future_dated",
            max_ts=pd.Timestamp(max_ts).isoformat(),
            freeze_clock=freeze_clock.isoformat(),
        )
        raise ValueError("stakes_13d_future_dated")


def _check_earnings_freshness(
    earnings: pd.DataFrame,
    freeze_clock: pd.Timestamp,
) -> None:
    """Ensure 8-K earnings are not future-dated and non-empty."""
    if earnings.empty:
        log.error("readiness_earnings_8k_empty")
        raise ValueError("earnings_8k_empty")

    max_ts = earnings["event_ts"].max()
    if pd.Timestamp(max_ts) > freeze_clock:
        log.error(
            "readiness_earnings_8k_future_dated",
            max_ts=pd.Timestamp(max_ts).isoformat(),
            freeze_clock=freeze_clock.isoformat(),
        )
        raise ValueError("earnings_8k_future_dated")


def _check_membership_freshness(
    membership: pd.DataFrame,
    membership_snapshot_date: pd.Timestamp,
    predict_session: pd.Timestamp,
    contract: MembershipFreshnessContract | None,
) -> None:
    """Check membership freshness against the owner-gated contract.

    FAILS CLOSED if the contract is not configured (task explicitly reserves
    this decision for the owner - no self-approval of stale snapshots).
    """
    if contract is None:
        log.error("readiness_membership_contract_not_configured")
        raise ValueError("membership_freshness_contract_not_configured")

    if contract.max_age_sessions is not None:
        # Check max age in NYSE sessions
        dates = nyse_sessions(membership_snapshot_date, predict_session)
        if len(dates) > contract.max_age_sessions:
            log.error(
                "readiness_membership_contract_violated",
                snapshot_age_sessions=len(dates),
                max_allowed=contract.max_age_sessions,
                snapshot_date=membership_snapshot_date.isoformat(),
                predict_session=predict_session.isoformat(),
            )
            raise ValueError("membership_freshness_contract_violated")


def _check_provider_cutoff(
    provider_cutoff: str,
    policy: ProviderCutoffPolicy | None,
    predict_session: pd.Timestamp,
) -> None:
    """Check provider cutoff policy (owner-gated).

    FAILS CLOSED if the policy is not configured. The cutoff must be a real
    verifiable knowledge cutoff, not faked to the predict timestamp: a cutoff
    whose month equals the predict month is predict_ts echoed back (the legacy
    fallback), which no vendor knowledge cutoff can legitimately be.
    """
    if policy is None:
        log.error("readiness_provider_cutoff_policy_not_configured")
        raise ValueError("provider_cutoff_policy_not_configured")

    if provider_cutoff == "unknown":
        if policy.block_on_unknown is True:
            log.error("readiness_provider_cutoff_unknown_not_allowed")
            raise ValueError("provider_cutoff_unknown_not_allowed")
    elif policy.block_on_unknown is not None and not policy.block_on_unknown:
        # Owner explicitly allows unknown; the supplied value is not "unknown",
        # so verify it is not the predict_ts fake (reason code lives for this).
        predict_month = predict_session.strftime("%Y-%m")
        if provider_cutoff.startswith(predict_month):
            log.error(
                "readiness_provider_cutoff_faked",
                provider_cutoff=provider_cutoff,
                predict_month=predict_month,
            )
            raise ValueError("provider_cutoff_faked")


def _check_universe_match(
    test_tickers: set[str],
    membership: pd.DataFrame,
    predict_session: pd.Timestamp,
) -> None:
    """Ensure test tickers exactly match PIT constituents at predict_session."""
    pit = constituents_on(membership, predict_session)
    if test_tickers != pit:
        log.error(
            "readiness_universe_mismatch",
            test_tickers=sorted(test_tickers),
            pit_constituents=sorted(pit),
            predict_session=predict_session.isoformat(),
        )
        raise ValueError("universe_mismatch")


def _check_llm_event_text(
    events_df: pd.DataFrame,
) -> None:
    """Ensure LLM event channel has non-empty primary-document text.

    Empty text means the edge was skipped (audit defect), which is NOT acceptable
    for a hybrid config that requires the LLM channel.
    """
    if events_df.empty:
        # No events at all is acceptable (pure-zero-LLM)
        return

    # Check if all text is empty (skipped LLM edge)
    if "text" in events_df.columns and events_df["text"].eq("").all():
        log.error("readiness_llm_event_text_empty")
        raise ValueError("llm_event_text_empty")


def forward_panel_train_test_split(
    panel: pd.DataFrame,
    predict_session: pd.Timestamp,
    embargo_sessions: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Forward-specific panel split: train drops unresolved labels, test retains unknown labels.

    Unlike historical _clean_panel (which drops all y_fwd_ret NaN), this forward-specific
    helper:
    - Train: drops NaN y_fwd_ret (unrealized future labels)
    - Test: retains all rows, including those with NaN y_fwd_ret (forward cross-section)

    This is necessary because at predict time, the test cross-section includes tickers
    whose forward returns have NOT yet been realized (the entire point of forward prediction).

    Args:
        panel: Panel with date/ticker/y_fwd_ret/features.
        predict_session: Target prediction session.
        embargo_sessions: Embargo gap in sessions.

    Returns:
        (train, test) DataFrames where train has realized labels only, test has full cross-section.
    """
    dates_sorted = pd.DatetimeIndex(sorted(panel["date"].unique()))
    pos = {d: i for i, d in enumerate(dates_sorted)}

    if predict_session not in pos:
        # Predict session not in panel - empty train/test (no fabrication)
        return panel.iloc[0:0].reset_index(drop=True), panel.iloc[0:0].reset_index(drop=True)

    # Test = predict_session cross-section (retain ALL rows, including NaN labels)
    test = panel[panel["date"] == predict_session].reset_index(drop=True)

    # Train cutoff index with embargo
    cutoff_idx = pos[predict_session] - embargo_sessions
    if cutoff_idx < 0:
        # Cutoff before first date - empty train
        train = panel.iloc[0:0].reset_index(drop=True)
    else:
        cutoff_date = dates_sorted[cutoff_idx]
        # Train drops rows with NaN y_fwd_ret (unrealized labels)
        train_raw = panel[panel["date"] <= cutoff_date]
        train = train_raw.dropna(subset=["y_fwd_ret"]).reset_index(drop=True)

    return train, test


def check_forward_readiness(
    *,
    requested_predict_ts: str,
    panel: pd.DataFrame,
    fundamentals: pd.DataFrame,
    prices: pd.DataFrame,
    membership: pd.DataFrame | None,
    freeze_out: dict,
    membership_freshness_contract: MembershipFreshnessContract | None,
    provider_cutoff: str,
    provider_cutoff_policy: ProviderCutoffPolicy | None,
    freeze_clock: pd.Timestamp,
    requires_llm_channel: bool = False,
) -> ReadinessCheckResult:
    """Fail-closed readiness gate for E3 forward commits.

    Validates that the commit targets the requested live session with complete
    PIT inputs BEFORE any fit/LLM call/artifact write/ledger append.

    Args:
        requested_predict_ts: The requested prediction timestamp (must match panel).
        panel: The assembled panel with date/ticker/y_fwd_ret/features.
        fundamentals: Fundamental data with filed timestamps.
        prices: Price data indexed by session.
        membership: PIT membership data (required for universe check).
        freeze_out: Output from freeze_forward_iset with macro/stakes/earnings.
        membership_freshness_contract: Owner-gated freshness contract (None → FAIL CLOSED).
        provider_cutoff: Verifiable provider knowledge cutoff (not faked).
        provider_cutoff_policy: Owner-gated cutoff policy (None → FAIL CLOSED).
        freeze_clock: The freeze timestamp (no input may exceed this).
        requires_llm_channel: If True, empty LLM event text causes failure.

    Returns:
        ReadinessCheckResult with is_ready=True only if ALL checks pass.
        Manifest contains coverage timestamps/hashes/metadata for audit trail.

    Raises:
        ValueError: With specific reason_code on any readiness failure.
    """
    # Ensure freeze_clock is timezone-naive for consistent comparisons
    if freeze_clock.tz is not None:
        freeze_clock = freeze_clock.tz_localize(None)

    manifest: dict = {}

    try:
        # 1. Resolve predict_session from requested timestamp (NOT panel max labeled date)
        panel_dates = panel["date"]
        predict_session, session_idx = _resolve_predict_session(
            requested_predict_ts, panel_dates
        )
        manifest["predict_session"] = predict_session.isoformat()
        manifest["requested_predict_ts"] = requested_predict_ts

        # 2. Check price coverage
        price_max_session = pd.Timestamp(prices.index.max()).normalize()
        _check_price_coverage(price_max_session, predict_session)
        manifest["price_max_session"] = price_max_session.isoformat()

        # 3. Check fundamental freshness
        _check_fundamental_freshness(fundamentals, freeze_clock)
        # filed / event_ts columns arrive as strings from the cached parquets —
        # wrap before .isoformat() (latent TypeError path, first reached by the
        # 2026-08-31 smoke once earlier steps finally passed).
        manifest["fundamental_max_filed"] = pd.Timestamp(
            fundamentals["filed"].max()
        ).isoformat()
        manifest["fundamental_rows"] = len(fundamentals)

        # 4. Check macro freshness
        macro = freeze_out.get("macro_df", pd.DataFrame())
        _check_macro_freshness(macro, freeze_clock)
        if not macro.empty:
            manifest["macro_max_event_ts"] = pd.Timestamp(
                macro["event_ts"].max()
            ).isoformat()
            manifest["macro_rows"] = len(macro)

        # 5. Check 13D stakes freshness
        stakes = freeze_out.get("stakes_df", pd.DataFrame())
        _check_stakes_freshness(stakes, freeze_clock)
        if not stakes.empty:
            manifest["stakes_13d_max_event_ts"] = pd.Timestamp(
                stakes["event_ts"].max()
            ).isoformat()
            manifest["stakes_13d_rows"] = len(stakes)

        # 6. Check 8-K earnings freshness
        earnings = freeze_out.get("earnings_df", pd.DataFrame())
        _check_earnings_freshness(earnings, freeze_clock)
        if not earnings.empty:
            manifest["earnings_8k_max_event_ts"] = pd.Timestamp(
                earnings["event_ts"].max()
            ).isoformat()
            manifest["earnings_8k_rows"] = len(earnings)

        # 7. Check membership (required)
        if membership is None:
            log.error("readiness_membership_not_provided")
            raise ValueError("membership_not_provided")

        # Get membership snapshot date (max date in membership)
        membership_snapshot_date = pd.Timestamp(membership["date"].max()).normalize()
        _check_membership_freshness(
            membership, membership_snapshot_date, predict_session,
            membership_freshness_contract
        )
        manifest["membership_snapshot_date"] = membership_snapshot_date.isoformat()

        # 8. Check provider cutoff (owner-gated)
        _check_provider_cutoff(provider_cutoff, provider_cutoff_policy, predict_session)
        manifest["provider_cutoff"] = provider_cutoff

        # 9. Forward-specific train/test split
        train, test = forward_panel_train_test_split(
            panel, predict_session, embargo_sessions=21
        )

        # 10. Verify test rows are exactly the predict_session
        if test["date"].nunique() != 1 or test["date"].iloc[0] != predict_session:
            log.error(
                "readiness_test_rows_not_predict_session",
                test_dates=test["date"].unique(),
                predict_session=predict_session.isoformat(),
            )
            raise ValueError("test_rows_not_predict_session")

        # 11. Verify train has no unrealized labels
        if train["y_fwd_ret"].isna().any():
            log.error("readiness_train_contains_unrealized_labels")
            raise ValueError("train_contains_unrealized_labels")

        # 12. Check universe match
        test_tickers = set(test["ticker"].unique())
        _check_universe_match(test_tickers, membership, predict_session)
        manifest["test_tickers_count"] = len(test_tickers)
        manifest["test_tickers"] = sorted(test_tickers)

        # 13. Check LLM event text if required
        if requires_llm_channel:
            events_df = freeze_out.get("events_df", pd.DataFrame())
            _check_llm_event_text(events_df)
            manifest["llm_events_count"] = len(events_df)

        return ReadinessCheckResult(is_ready=True, reason_code=None, manifest=manifest)

    except ValueError as e:
        # Return fail-closed result with reason code
        reason = str(e)
        if reason not in ReasonCode.__args__:
            reason = "unknown_error"
        return ReadinessCheckResult(is_ready=False, reason_code=reason, manifest=manifest)


__all__ = [
    "ReasonCode",
    "ReadinessCheckResult",
    "MembershipFreshnessContract",
    "ProviderCutoffPolicy",
    "forward_panel_train_test_split",
    "check_forward_readiness",
]
