#!/usr/bin/env python3
"""Track C regime macro layer builder.

Builds the macro component of Track C's regime_state feature (5-line composite):
  1. vix — VIX level (VIXCLS via vix_as_of)
  2. credit_spread — BAA - AAA (FRED)
  3. term_spread — DGS10 - DGS1 (FRED)
  4. dff_surprise — ALFRED vintage DFF surprise
  5. EPU — EXPLORATORY (no permissive PIT-safe source yet — 4-line layer)

Output: data/cache/regime_macro.parquet (daily equal-weight composite).
NO ledger write — PHASE_C_NO_LEDGER=1 artifacts-only mode.

Run:
  uv run python scripts/build_regime_macro.py

Environment variables:
  FRED_API_KEY — required for FRED fetch
  PHASE_C_NO_LEDGER=1 — artifacts-only mode (default: true)

Anti-leakage:
  * DFF: ALFRED vintage, strictly-before rule
  * VIX: unrevised (no-revision contract)
  * Credit/term: FRED series (revised; snapshot+sha256 at fetch)
  * z-score: past-only (shift(1) before rolling)

H6 determinism: cache hit → bit-identical rerun.
"""
from __future__ import annotations

import hashlib
import os
import sys
from datetime import datetime, timezone

import pandas as pd
import structlog

from aionis.config import settings
from aionis.features.regime_macro import build_macro_regime

log = structlog.get_logger()


def _session_grid(
    start_date: str,
    end_date: str,
) -> pd.DatetimeIndex:
    """Generate NYSE session grid (trading days, Monday-Friday, no holidays).

    Simplified approximation — the real feature alignment uses the NYSE calendar.
    For this builder, we generate business days (Mon-Fri excluding holidays) as
    a reasonable proxy for trading sessions.

    Args:
        start_date: Start date (ISO)
        end_date: End date (ISO)

    Returns:
        DatetimeIndex of session dates (sorted ascending)
    """
    pd_bday = pd.bdate_range(start=start_date, end=end_date)
    log.info("session_grid_generated", n_sessions=len(pd_bday))
    return pd.DatetimeIndex(pd_bday)


def main() -> int:
    """Build the regime macro layer and write to parquet."""
    # Check NO_LEDGER mode (artifacts-only — no ledger write)
    no_ledger = os.environ.get("PHASE_C_NO_LEDGER", "1") == "1"
    if not no_ledger:
        log.warning("phase_c_ledger_write_attempted", blocked=True)
        print("ERROR: PHASE_C_NO_LEDGER=1 is required (artifacts-only mode)", file=sys.stderr)
        return 1

    # FRED API key check
    if not settings.fred_api_key:
        print("ERROR: FRED_API_KEY is required (set in .env or environment)", file=sys.stderr)
        return 1

    # Date range: use a reasonable analysis window (2016-01-01 to 2026-08-03)
    # This matches the Track C analysis window (pre-freeze → S0)
    start_date = "2016-01-01"
    end_date = datetime.now(tz=timezone.utc).date().isoformat()

    log.info(
        "regime_macro_builder_start",
        start=start_date,
        end=end_date,
        no_ledger=no_ledger,
    )

    # Generate session grid
    as_of_dates = _session_grid(start_date, end_date)

    # Build the macro regime layer (fetch → standardize → composite)
    try:
        macro_regime = build_macro_regime(
            as_of_dates=as_of_dates,
            fred_api_key=settings.fred_api_key,
            start_date=start_date,
            end_date=end_date,
            cache_dir=settings.data_dir / "cache",
            include_epu=False,  # 4-line layer (no permissive EPU source yet)
        )
    except Exception as e:
        log.exception("regime_macro_build_failed")
        print(f"ERROR: Failed to build macro regime: {e}", file=sys.stderr)
        return 1

    # Write output
    output_path = settings.data_dir / "cache" / "regime_macro.parquet"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert Series to DataFrame for parquet (date index + value column)
    df_out = pd.DataFrame({
        "date": macro_regime.index,
        "macro_regime": macro_regime.to_numpy(),
    })
    df_out.to_parquet(output_path)

    # Compute sha256 for reproducibility
    sha256_digest = hashlib.sha256(output_path.read_bytes()).hexdigest()

    log.info(
        "regime_macro_built",
        path=str(output_path),
        n_rows=len(df_out),
        n_valid=int(df_out["macro_regime"].notna().sum()),
        date_range=(
            df_out["date"].min().date().isoformat(),
            df_out["date"].max().date().isoformat(),
        ),
        sha256=sha256_digest,
        epu_included=False,
    )

    print(f"Built regime macro layer: {output_path}")
    print(f"  Rows: {len(df_out)}")
    print(f"  Valid (non-NaN): {int(df_out['macro_regime'].notna().sum())}")
    print(f"  Date range: {df_out['date'].min().date()} to {df_out['date'].max().date()}")
    print(f"  SHA256: {sha256_digest}")
    print("  EPU: NOT included (no permissive PIT-safe source identified)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
