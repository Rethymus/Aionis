"""Build the meso regime layer (Track C) and write to cache.

CLI entry point for computing the cross-sector momentum regime from US SIC and
CN shenwan sector classifications. Writes ``data/cache/regime_meso.parquet``
(gitignored) with sha256 logging.

Usage::

    # CN shenwan fetch enabled (default: off for hermetic tests)
    ENABLE_CN_FETCH=1 uv run python scripts/build_regime_meso.py

    # US-only meso (no CN fetch)
    uv run python scripts/build_regime_meso.py

Output (gitignored, NOT ledger):
    - data/cache/regime_meso.parquet (daily meso_regime series)

Anti-leakage:
    - Sector momentum: past-only rolling(21, min_periods=21)
    - baostock: ≥2s pause (G7 politeness)
    - NO ledger write (exploratory only)

H6 determinism: synthetic tests use seed=0; real fetch deterministic by cache hit.
"""
from __future__ import annotations

import hashlib
import os
import sys

import pandas as pd
import structlog

from aionis.config import settings
from aionis.features.regime_meso import build_meso_regime

log = structlog.get_logger()

# Cache paths
CACHE = settings.data_dir / "cache"
US_PRICES = CACHE / "phase_b_prices.parquet"
CN_PRICES = CACHE / "ashare_prices_csi300.parquet"
OUT = CACHE / "regime_meso.parquet"

# Date range for Track C (2016-01-01 to 2026-08-04, inclusive)
START_DATE = "2016-01-01"
END_DATE = "2026-08-04"


def _load_cn_prices_wide() -> pd.DataFrame:
    """Load CN prices from long parquet and convert to wide format."""
    if not CN_PRICES.exists():
        log.warning("cn_prices_missing", path=str(CN_PRICES))
        return pd.DataFrame()

    df = pd.read_parquet(CN_PRICES)
    if df.empty:
        return pd.DataFrame()

    # Convert to wide format [dates x tickers]
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df = df.sort_values("date")

    # Filter to date range
    df = df[(df["date"] >= START_DATE) & (df["date"] <= END_DATE)]

    # Pivot to wide
    wide = df.pivot(index="date", columns="ticker", values="close")

    log.info(
        "cn_prices_loaded",
        n_dates=len(wide),
        n_tickers=len(wide.columns),
        date_range=(wide.index.min(), wide.index.max()),
    )

    return wide


def _load_us_prices_wide() -> pd.DataFrame:
    """Load US prices (already wide format) and filter to date range."""
    if not US_PRICES.exists():
        raise RuntimeError(f"US prices not found at {US_PRICES}")

    df = pd.read_parquet(US_PRICES)
    df.index = pd.to_datetime(df.index).normalize()

    # Filter to date range
    df = df[(df.index >= START_DATE) & (df.index <= END_DATE)]

    log.info(
        "us_prices_loaded",
        n_dates=len(df),
        n_tickers=len(df.columns),
        date_range=(df.index.min(), df.index.max()),
    )

    return df


def main() -> int:
    """Build meso regime and write to cache."""
    # Check for US prices (required)
    if not US_PRICES.exists():
        log.error("us_prices_required_missing", path=str(US_PRICES))
        print(f"[ERROR] US prices required: {US_PRICES}", file=sys.stderr)
        return 1

    # Load price panels
    print("[S] Loading price panels...", flush=True)
    us_prices = _load_us_prices_wide()
    cn_prices = _load_cn_prices_wide()

    if us_prices.empty:
        log.error("us_prices_empty_after_filter")
        print("[ERROR] US prices empty after date filter", file=sys.stderr)
        return 1

    # Check CN fetch flag
    enable_cn_fetch = int(os.environ.get("ENABLE_CN_FETCH", "0")) == 1

    if not cn_prices.empty and enable_cn_fetch:
        print("[S] CN fetch enabled (pause=2.0s per query)...", flush=True)
    elif not cn_prices.empty:
        print("[S] CN prices loaded but fetch DISABLED (set ENABLE_CN_FETCH=1)", flush=True)
    else:
        print("[S] CN prices not available (US-only meso)", flush=True)

    # Build meso regime
    print("[S] Building meso regime...", flush=True)
    meso_regime = build_meso_regime(
        us_prices=us_prices,
        cn_prices=cn_prices,
        cache_dir=CACHE,
        enable_cn_fetch=enable_cn_fetch,
        cn_fetch_pause=2.0,
    )

    # Write output
    CACHE.mkdir(parents=True, exist_ok=True)
    meso_regime_df = pd.DataFrame({"meso_regime": meso_regime})
    meso_regime_df.index.name = "date"
    meso_regime_df.to_parquet(OUT)

    sha = hashlib.sha256(OUT.read_bytes()).hexdigest()

    print(f"[S] DONE: wrote {OUT}", flush=True)
    print(f"[S] sha256={sha[:16]}", flush=True)
    n_valid = meso_regime.notna().sum()
    print(
        f"[S] meso_regime: {len(meso_regime)} dates, {n_valid} valid",
        flush=True,
    )
    print(
        f"[S] date range: {meso_regime.first_valid_index()} to "
        f"{meso_regime.last_valid_index()}",
        flush=True,
    )
    print(
        "[S] US SIC decision: PERMISSIVE SOURCE USED (EDGAR public domain)",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    import os

    raise SystemExit(main())
