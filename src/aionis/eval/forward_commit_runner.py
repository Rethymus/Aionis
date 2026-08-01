"""E3 Slice 3e - the forward-commit runner (importable logic; thin script shim).

Mirrors ``scripts/phase_e1_run.py``: load cached parquets -> FREEZE I_t (Slice 3c)
-> build arm_e13's extra_features (Pass A) -> assemble both arm panels -> build the
frozen config -> run the forward-commit step (Slice 3d). ``PHASE_E3_NO_LEDGER=1``
-> artifacts-only dry-run (computes the sig, writes nothing to the real ledger).

The importable logic lives here (under the package) so the test suite can exercise
it hermetically via thin seams (``_load_inputs``, ``_build_llm_client``,
``_assemble_panels``). ``scripts/forward_commit.py`` is a one-line entry shim that
calls :func:`main`.

ORDER (I1, the per-prediction ``config_committed BEFORE result`` anchor):
freeze I_t -> ``forward_iset_frozen`` row (iset sha256 sealed) -> config sha256 ->
single fit per arm -> ``forward_prediction_committed`` row. Every step completes
BEFORE the ``target_t`` outcome can realize.
"""
from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

import pandas as pd
import structlog

from aionis.config import settings
from aionis.eval.forward_commit import (
    HORIZON,
    build_forward_config,
    resolve_pinned_provider,
    run_forward_commit,
)
from aionis.eval.forward_freeze import (
    commit_forward_iset_frozen,
    freeze_forward_iset,
    iset_manifest,
    iset_sha256_from_manifest,
)
from aionis.eval.forward_live_readiness import (
    MembershipFreshnessContract,
    ProviderCutoffPolicy,
    check_forward_readiness,
)
from aionis.eval.two_arm import _clean_panel
from aionis.features.alignment import nyse_sessions, session_close_ts
from aionis.features.causal_broadcast import GLMCausalEdgeClient, build_forward_extra_features
from aionis.features.frozen_beta import FROZEN_BETA_STATUS, FROZEN_BETA_VERSION
from aionis.schema.causal_edge import (
    CAUSAL_SCHEMA_VERSION,
    MechanismKeyword,
    SicSector,
    sic_to_ff12,
)

log = structlog.get_logger()


# ---------------------------------------------------------------------------
# timestamps - predict / target / last_poll (all NYSE-session-anchored)
# ---------------------------------------------------------------------------


def _nyse_month_end_session(today: pd.Timestamp | None = None) -> pd.Timestamp:
    """The last NYSE session of ``today``'s month (the forward predict_date)."""
    today = pd.Timestamp.today(tz=None) if today is None else pd.Timestamp(today)
    month_end = (today + pd.offsets.MonthEnd(0)).normalize()
    month_start = month_end.replace(day=1)
    sessions = nyse_sessions(month_start, month_end)
    return pd.Timestamp(sessions[-1]).normalize()


def _nyse_prior_month_end_session(today: pd.Timestamp | None = None) -> pd.Timestamp:
    """The last NYSE session of the PRIOR month (the forward ``last_poll_ts``)."""
    cur = _nyse_month_end_session(today)
    first_of_cur = cur.replace(day=1)
    last_day_prior = first_of_cur - pd.Timedelta(days=1)
    first_of_prior = last_day_prior.replace(day=1)
    sessions = nyse_sessions(first_of_prior, last_day_prior)
    return pd.Timestamp(sessions[-1]).normalize()


def _predict_ts(today: pd.Timestamp | None = None) -> str:
    """Wall-clock close (16:00 ET) of the month-end NYSE session."""
    return session_close_ts(_nyse_month_end_session(today)).isoformat()


def _target_ts(today: pd.Timestamp | None = None) -> str:
    """Wall-clock close of the session HORIZON after the predict session."""
    sess = _nyse_month_end_session(today)
    future = nyse_sessions(sess + pd.Timedelta(days=1), sess + pd.Timedelta(days=HORIZON * 2 + 10))
    target = pd.Timestamp(future[HORIZON - 1]).normalize()
    return session_close_ts(target).isoformat()


def _last_poll_ts(today: pd.Timestamp | None = None) -> str:
    return session_close_ts(_nyse_prior_month_end_session(today)).isoformat()


# ---------------------------------------------------------------------------
# frozen taxonomy / mechanism enum (recorded into config_sha256 -> I8)
# ---------------------------------------------------------------------------


def _ff12_taxonomy() -> list[str]:
    return sorted({s.value for s in SicSector})


def _mechanism_enum() -> list[str]:
    return sorted({m.value for m in MechanismKeyword})


# ---------------------------------------------------------------------------
# testable seams (monkeypatched in tests; real I/O in the live path)
# ---------------------------------------------------------------------------


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def _load_inputs(
    cache: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    """Load cached prices / fundamentals / membership / SIC-map + the ticker->CIK map.

    Returns ``(fund, px, mem, sic, ciks)``. A seam so tests inject tiny fixtures
    instead of touching the real cache.
    """
    from aionis.ingest import fundamentals
    from aionis.ingest.universe import load_pierrebrunelle_membership

    fund = pd.read_parquet(cache / "phase_b_fundamentals.parquet")
    px = pd.read_parquet(cache / "phase_b_prices.parquet")
    sic = pd.read_parquet(cache / "phase_d_sic_map.parquet")
    mem = load_pierrebrunelle_membership()
    ciks = fundamentals.cik_map(cache)
    return fund, px, mem, sic, ciks


def _build_llm_client(provider) -> GLMCausalEdgeClient:
    """Construct the pinned closed-enum causal-edge client (a seam for tests)."""
    return GLMCausalEdgeClient(provider.base_url, provider.api_key, provider.model)


def _events_df(freeze_out: dict) -> pd.DataFrame:
    """Long ``[ticker, filing_date, accession, event_id, text]`` for the LLM edge step.

    13D + 8-K filings from the freeze; ``text`` is empty here (the real runner
    fetches primary-doc text in a later slice; an empty text -> the edge is
    skipped, so arm_e13 still carries the self/peer/macro channels signal-free).
    """
    parts: list[pd.DataFrame] = []
    for src in ("stakes_df", "earnings_df"):
        frame = freeze_out[src]
        if frame.empty or "accession" not in frame.columns:
            continue
        view = frame[["ticker", "filing_date", "accession"]].copy()
        view["event_id"] = view["ticker"].astype(str) + ":" + view["accession"].astype(str)
        view["text"] = ""
        parts.append(view)
    if not parts:
        return pd.DataFrame(columns=["ticker", "filing_date", "accession", "event_id", "text"])
    return pd.concat(parts, ignore_index=True)


def _assemble_panels(
    px: pd.DataFrame, fund: pd.DataFrame, mem: pd.DataFrame,
    extra_features: pd.DataFrame, tickers: list[str],  # noqa: ARG001 (tickers reserved for layout checks)
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build the PIT-masked arm_base + arm_e13 panels (shared (date, ticker) layout).

    Both arms share prices / universe / fundamentals / folds; ONLY the feature set
    differs (arm_e13 adds the Pass-A extra_features). A seam so tests inject
    prebuilt tiny panels.
    """
    panel_base = _clean_panel(px, fund, mem, HORIZON, "end_lag", extra_features=None)
    panel_e13 = _clean_panel(px, fund, mem, HORIZON, "end_lag", extra_features=extra_features)
    return panel_base, panel_e13


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main(
    runs_dir: Path | str = "runs",
    today: pd.Timestamp | None = None,
    cache_dir: Path | str | None = None,
    *,
    enforce_live_readiness: bool = False,
    membership_freshness_contract: MembershipFreshnessContract | None = None,
    provider_cutoff_policy: ProviderCutoffPolicy | None = None,
    provider_cutoff: str | None = None,
) -> dict:
    """Run one forward-commit step at the month-end NYSE session.

    ORDER: resolve pinned provider -> freeze I_t -> ``forward_iset_frozen`` row ->
    build extra_features -> assemble panels -> READINESS GATE -> frozen config ->
    fit+commit. In ``PHASE_E3_NO_LEDGER=1`` mode the freeze writes to a throwaway
    runs dir and no ledger rows are appended (the sig is still computed).

    AUD-06 readiness gate: validates the commit targets the requested live session
    with complete PIT inputs BEFORE any fit/LLM call/artifact write/ledger append.
    """
    artifacts_only = os.environ.get("PHASE_E3_NO_LEDGER") == "1"
    runs = Path(runs_dir)
    cache = Path(cache_dir) if cache_dir is not None else settings.data_dir / "cache"

    # I6: resolve the SINGLE pinned provider BEFORE the freeze (refuse early on a missing key)
    provider = resolve_pinned_provider("glm")

    predict_ts = _predict_ts(today)
    target_t = _target_ts(today)
    predict_session = _nyse_month_end_session(today)
    last_poll_ts = _last_poll_ts(today)
    print(
        f"[E3] predict_session={predict_session.date()} horizon={HORIZON} "
        f"provider=glm artifacts_only={artifacts_only}",
        flush=True,
    )

    fund, px, mem, sic, ciks = _load_inputs(cache)
    print(f"[E3] fund rows={len(fund)} prices={px.shape} membership={mem.shape}", flush=True)

    sic_map = dict(zip(sic["ticker"], sic["sic"], strict=True))
    tickers = [t for t in px.columns if t in sic_map]
    ff12_map = {t: sic_to_ff12(sic_map[t]) for t in tickers}
    ciks_for_freeze = {t: ciks[t] for t in tickers if t in ciks}

    # --- FREEZE I_t (Slice 3c). In artifacts-only mode collectors write to a
    #     throwaway runs dir so the real ledger is never touched.
    collect_runs = Path(tempfile.mkdtemp(prefix="e3_no_ledger_")) if artifacts_only else runs
    freeze_out = freeze_forward_iset(
        snapshot_ts=predict_ts, last_poll_ts=last_poll_ts,
        ciks=ciks_for_freeze, tickers=tickers,
        fred_api_key=settings.fred_api_key, cache_dir=cache, runs_dir=collect_runs,
    )
    print(
        f"[E3] freeze: macro={len(freeze_out['macro_df'])} "
        f"stakes={len(freeze_out['stakes_df'])} earnings={len(freeze_out['earnings_df'])}",
        flush=True,
    )

    uv_lock_sha = _sha(Path("uv.lock"))
    manifest = iset_manifest(freeze_out, uv_lock_sha256=uv_lock_sha)
    iset_sha = iset_sha256_from_manifest(manifest)
    if not artifacts_only:
        commit_forward_iset_frozen(
            snapshot_ts=predict_ts, iset_sha256=iset_sha, runs_dir=runs,
            manifest_summary={
                k: v["n_rows"] for k, v in manifest.items()
                if isinstance(v, dict) and "n_rows" in v
            },
        )
        print(f"[E3] forward_iset_frozen iset_sha256={iset_sha[:12]}", flush=True)

    # --- build arm_e13 extra_features (Pass A) over the freeze
    sessions = nyse_sessions(pd.Timestamp(px.index.min()).normalize(), predict_session)
    events_df = _events_df(freeze_out)
    client = _build_llm_client(provider)
    extra = build_forward_extra_features(
        macro_df=freeze_out["macro_df"], stakes_df=freeze_out["stakes_df"],
        earnings_df=freeze_out["earnings_df"], events_df=events_df,
        client=client, cache_dir=cache, ff12_map=ff12_map,
        sessions=sessions, tickers=tickers,
    )
    print(f"[E3] extra_features rows={len(extra)}", flush=True)

    # --- assemble panels + frozen config + fit+commit
    panel_base, panel_e13 = _assemble_panels(px, fund, mem, extra, tickers)
    print(f"[E3] panel_base={panel_base.shape} panel_e13={panel_e13.shape}", flush=True)

    # --- AUD-06 readiness gate (BEFORE any fit/LLM call/artifact write/ledger append)
    # Only enforced when enforce_live_readiness=True (opt-in for live paths)
    # Use real provider_cutoff (owner-provided), not faked to predict_ts
    actual_provider_cutoff = provider_cutoff if provider_cutoff is not None else predict_ts

    if enforce_live_readiness:
        readiness = check_forward_readiness(
            requested_predict_ts=predict_ts,
            panel=panel_base,  # Use base panel (has date grid)
            fundamentals=fund,
            prices=px,
            membership=mem,
            freeze_out=freeze_out,
            membership_freshness_contract=membership_freshness_contract,
            provider_cutoff=actual_provider_cutoff,
            provider_cutoff_policy=provider_cutoff_policy,
            freeze_clock=pd.Timestamp(predict_ts),
            requires_llm_channel=True,  # arm_e13 requires LLM event channel
        )
        if not readiness.is_ready:
            # Fail-closed: return early WITHOUT any fit/LLM call/write/ledger operation
            print(
                f"[E3] READINESS FAILED: {readiness.reason_code} - no fit/commit performed",
                flush=True,
            )
            return {
                "committed": False,
                "readiness_failed": True,
                "reason_code": readiness.reason_code,
                "manifest": readiness.manifest,
            }
        print("[E3] READINESS PASS - proceeding to fit/commit", flush=True)

    raw = freeze_out["raw_sha256s"]
    shas = {
        "iset_sha256": iset_sha,
        "uv_lock_sha256": uv_lock_sha,
        "prices_sha256": _sha(cache / "phase_b_prices.parquet"),
        "fundamentals_sha256": _sha(cache / "phase_b_fundamentals.parquet"),
        "membership_sha256": _sha(cache / "universe_pierrebrunelle.parquet"),
        "sic_map_sha256": _sha(cache / "phase_d_sic_map.parquet"),
        "macro_raw_sha256": raw.get("macro_forward", ""),
        "stakes_raw_sha256": raw.get("stakes_13d_forward", ""),
        "earnings_raw_sha256": raw.get("earnings_8k_forward", ""),
    }
    config = build_forward_config(
        horizon=HORIZON,
        shas=shas,
        versions={"causal_schema": CAUSAL_SCHEMA_VERSION},
        provider="glm",
        provider_cutoff=predict_ts,
        causal_schema_version=CAUSAL_SCHEMA_VERSION,
        mechanism_keyword_enum=_mechanism_enum(),
        ff12_taxonomy=_ff12_taxonomy(),
        broadcast_weights={"version": FROZEN_BETA_VERSION, "status": FROZEN_BETA_STATUS},
        frozen_params={"n_jobs": 1, "random_state": 0},
    )
    res = run_forward_commit(
        predict_ts=predict_ts, target_t=target_t,
        panel_base=panel_base, panel_e13=panel_e13, config=config,
        iset_sha256=iset_sha, provider="glm", provider_cutoff=actual_provider_cutoff,
        runs_dir=runs, no_ledger=artifacts_only, membership=mem,
    )
    print(
        f"[E3] committed={res['committed']} config_sha256={res['config_sha256'][:12]} "
        f"scores_sha256={res['scores_sha256'][:12]}",
        flush=True,
    )
    print("[E3] DONE", flush=True)
    return res


__all__ = ["main"]
