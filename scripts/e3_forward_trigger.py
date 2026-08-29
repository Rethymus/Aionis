"""E3 Slice 6 - NYSE month-end scheduler trigger.

Determines whether a given run date is the NYSE month-end session and, if so,
triggers the forward commit with live-readiness enforcement.

Uses pandas_market_calendars (XNYS calendar) to find the last NYSE trading
day of each month. Runs in shadow mode by default (PHASE_E3_NO_LEDGER=1).

This script is deterministic and fail-closed:
- Returns early (no-op) when run_date is NOT the month-end session
- Loads owner-gated contracts from config (fail-closed if missing)
- Calls forward_commit_runner.main() with enforce_live_readiness=True

Owner must ratify proposed contracts in config/e3_live_contracts.yaml before
enabling the automated cron (irreversible headline commits).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import pandas_market_calendars as mcal
import structlog
import yaml

from aionis.eval.forward_commit_runner import main as forward_commit_main
from aionis.eval.forward_live_readiness import (
    MembershipFreshnessContract,
    ProviderCutoffPolicy,
)

log = structlog.get_logger()


def _load_contracts(config_path: Path) -> tuple[MembershipFreshnessContract, ProviderCutoffPolicy]:
    """Load owner-gated live-readiness contracts from YAML config.

    Fail-closed: raises FileNotFoundError if config missing,
    raises ValueError if contracts not properly configured.
    """
    if not config_path.exists():
        log.error(
            "e3_trigger_config_missing",
            config_path=str(config_path),
        )
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path) as f:
        config = yaml.safe_load(f)

    membership_config = config.get("membership_freshness_contract", {})
    provider_config = config.get("provider_cutoff_policy", {})

    # Validate required fields
    if "max_age_sessions" not in membership_config:
        raise ValueError("membership_freshness_contract.max_age_sessions is required")

    if "block_on_unknown" not in provider_config:
        raise ValueError("provider_cutoff_policy.block_on_unknown is required")

    membership_contract = MembershipFreshnessContract(
        max_age_sessions=membership_config["max_age_sessions"],
        authoritative_refresh=membership_config.get("authoritative_refresh"),
    )

    provider_policy = ProviderCutoffPolicy(
        block_on_unknown=provider_config["block_on_unknown"],
    )

    return membership_contract, provider_policy


def _get_nyse_month_end_session(target_date: pd.Timestamp) -> pd.Timestamp:
    """Return the last NYSE trading session of target_date's month.

    Uses pandas_market_calendars XNYS calendar to find the month-end session.
    This is the deterministic session at which the forward commit should run.

    Args:
        target_date: Date within the target month (timezone-naive).

    Returns:
        The last NYSE session of that month (timezone-naive, midnight).
    """
    # Get XNYS (NYSE) calendar
    nyse = mcal.get_calendar("XNYS")

    # Find month boundaries
    month_start = target_date.replace(day=1)
    month_end = (month_start + pd.offsets.MonthEnd(0)).normalize()

    # Get all valid NYSE sessions in the month
    schedule = nyse.schedule(start_date=month_start, end_date=month_end)
    if schedule is None or schedule.empty:
        log.error(
            "e3_trigger_no_nyse_sessions",
            month_start=str(month_start.date()),
            month_end=str(month_end.date()),
        )
        raise ValueError(f"No NYSE sessions found in {target_date.strftime('%Y-%m')}")

    # The last session is the month-end session
    last_session = pd.Timestamp(schedule.index[-1]).normalize()
    return last_session


def _is_month_end_session(run_date: pd.Timestamp) -> bool:
    """Check if run_date is the NYSE month-end session.

    Args:
        run_date: The date to check (timezone-naive).

    Returns:
        True if run_date is the last NYSE session of its month.
    """
    month_end_session = _get_nyse_month_end_session(run_date)
    run_date_normalized = run_date.normalize()
    return run_date_normalized == month_end_session


def _load_provider_cutoff(config_path: Path) -> str | None:
    """Optional provider_cutoff from the FROZEN contracts config (None if absent).

    Round-39 wiring: the fail-closed guard refuses a None cutoff whenever
    provider_cutoff_policy is configured, so a real shadow/commit run requires
    a VERIFIED vendor-declared knowledge cutoff recorded in the contracts YAML
    (provider_cutoff: "YYYY-MM"). Never fabricate the value — vendor primary
    source only.
    """
    try:
        with open(config_path) as f:
            cfg = yaml.safe_load(f) or {}
    except (FileNotFoundError, yaml.YAMLError):
        return None
    pol = cfg.get("provider_cutoff_policy") or {}
    return pol.get("provider_cutoff") or None


def main(
    run_date: pd.Timestamp | None = None,
    config_path: Path | str = "config/e3_live_contracts.yaml",
    cache_dir: Path | str | None = None,
    runs_dir: Path | str = "runs",
) -> dict:
    """E3 forward trigger: run commit only on NYSE month-end session.

    Steps:
      1. Determine if run_date is the month-end NYSE session (no-op if not).
      2. Load owner-gated contracts from config (fail-closed if missing).
      3. Call forward_commit_runner.main() with enforce_live_readiness=True.

    Shadow mode (PHASE_E3_NO_LEDGER=1): computes everything but writes no
    ledger rows (the default for bring-up; owner enables cron after ratification).

    Args:
        run_date: The date to check (defaults to today).
        config_path: Path to YAML config with proposed contracts.
        cache_dir: Data cache directory (defaults to settings.data_dir/cache).
        runs_dir: Runs directory for outputs (defaults to "runs").

    Returns:
        Dict with status:
          - {"committed": False, "is_month_end": false} - no-op (not month-end)
          - {"committed": False, "readiness_failed": true, ...} - readiness blocked
          - {"committed": True, ...} - success (only in non-shadow mode)
    """
    # Normalize run_date to today if not provided
    if run_date is None:
        run_date = pd.Timestamp.today(tz=None).normalize()
    else:
        run_date = pd.Timestamp(run_date).normalize()

    # Step 1: Check if run_date is the month-end session
    if not _is_month_end_session(run_date):
        log.info(
            "e3_trigger_not_month_end",
            run_date=str(run_date.date()),
            reason="Not the NYSE month-end session - no commit performed",
        )
        return {"committed": False, "is_month_end": False}

    month_end_session = _get_nyse_month_end_session(run_date)
    log.info(
        "e3_trigger_month_end_detected",
        run_date=str(run_date.date()),
        month_end_session=str(month_end_session.date()),
    )

    # Step 2: Load owner-gated contracts (fail-closed if missing/malformed)
    config_path = Path(config_path)
    try:
        membership_contract, provider_policy = _load_contracts(config_path)
    except (FileNotFoundError, ValueError) as e:
        log.error(
            "e3_trigger_contracts_load_failed",
            error=str(e),
            reason="Owner contracts not configured - fail-closed, no commit performed",
        )
        return {"committed": False, "contracts_missing": True, "error": str(e)}

    log.info(
        "e3_trigger_contracts_loaded",
        max_age_sessions=membership_contract.max_age_sessions,
        block_on_unknown=provider_policy.block_on_unknown,
    )

    # Step 3: Call forward_commit_runner.main() with live-readiness enforcement
    # Shadow mode: PHASE_E3_NO_LEDGER=1 (set by caller via env or default)
    artifacts_only = os.environ.get("PHASE_E3_NO_LEDGER") == "1"
    if artifacts_only:
        log.info(
            "e3_trigger_shadow_mode",
            reason="PHASE_E3_NO_LEDGER=1 - no ledger writes",
        )

    # provider_cutoff: read from the FROZEN contracts config when present.
    # Round-39 wiring: the fail-closed guard (2026-08-29 hardening) refuses a
    # None cutoff whenever provider_cutoff_policy is configured, so a real
    # shadow/commit run requires a VERIFIED vendor-declared knowledge cutoff
    # recorded in config/e3_live_contracts.yaml (provider_cutoff: "YYYY-MM").
    # Absent → None → the guard fires with the AUD-06 message (fail-closed,
    # by design). Never fabricate the value — vendor primary source only.
    provider_cutoff = _load_provider_cutoff(config_path)

    try:
        result = forward_commit_main(
            runs_dir=runs_dir,
            today=month_end_session,
            cache_dir=cache_dir,
            enforce_live_readiness=True,
            membership_freshness_contract=membership_contract,
            provider_cutoff_policy=provider_policy,
            provider_cutoff=provider_cutoff,
        )
        log.info(
            "e3_trigger_commit_complete",
            committed=result.get("committed", False),
            config_sha256=(
                result.get("config_sha256", "")[:12]
                if result.get("config_sha256")
                else ""
            ),
        )
        return result
    except Exception as e:
        log.error(
            "e3_trigger_commit_failed",
            error=str(e),
            exc_info=True,
        )
        return {
            "committed": False,
            "error": str(e),
            "exception_type": type(e).__name__,
        }


if __name__ == "__main__":
    # CLI entry point: run with today's date
    result = main()
    # Exit with non-zero if commit failed (but not if just not month-end)
    if result.get("committed") is False:
        if result.get("is_month_end") is False:
            # No-op (not month-end) - clean exit
            sys.exit(0)
        # Month-end but failed - exit with error
        sys.exit(1)
    sys.exit(0)


__all__ = ["main", "_is_month_end_session", "_get_nyse_month_end_session"]
