#!/usr/bin/env python3
"""Track B panel materialization — PIT-aligned cross-section from cached data.

Pure data preparation: loads cached prices/fundamentals/universe/macro, computes
features, builds PIT panel, persists to gitignored parquet. No model, no rank-IC,
no ledger writes, no frozen config touches.

Reuses existing modules: corporate_vital_signs, price_features, panel_alignment,
universe. No network calls (all from cache).

Usage:
    uv run python scripts/track_b_materialize_panel.py

Output:
    data/cache/track_b_panel.parquet (gitignored)
    Console report: shape, coverage, date ranges, feature availability.
"""

from __future__ import annotations

import json

import pandas as pd
import structlog

from aionis.config import settings
from aionis.features.corporate_vital_signs import (
    TRACK_B_FEATURE_COLS,
    compute_corporate_vital_signs,
)
from aionis.features.panel_alignment import build_pit_panel
from aionis.features.price_features import (
    TRACK_B_PRICE_FEATURE_COLS,
    compute_amihud_from_wide,
    compute_price_features,
)
from aionis.ingest.fundamentals import METRIC_TAGS, pit_align
from aionis.ingest.universe import load_hanshof_membership

log = structlog.get_logger()

# Horizon from pre-registration (sessions)
_HORIZON = 21

# Output path
_OUTPUT_PATH = settings.data_dir / "cache" / "track_b_panel.parquet"


def _load_prices() -> tuple[pd.DataFrame, list[str]]:
    """Load prices from cache. Returns (long_df, tickers).

    Wide format [dates x tickers] → long [date, ticker, close].
    """
    path = settings.data_dir / "cache" / "phase_b_prices.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Prices cache not found: {path}")

    prices_wide = pd.read_parquet(path)
    tickers = prices_wide.columns.tolist()

    # Convert to long format
    prices_long = prices_wide.reset_index()
    prices_long.columns = ["date"] + tickers
    prices_long = prices_long.melt(
        id_vars=["date"], var_name="ticker", value_name="close"
    )

    log.info(
        "prices_loaded",
        rows=len(prices_long),
        dates=int(prices_wide.index.nunique()),
        tickers=len(tickers),
        date_min=str(prices_wide.index.min()),
        date_max=str(prices_wide.index.max()),
    )

    return prices_long, tickers


def _load_fundamentals(
    as_of_dates: pd.DatetimeIndex, tickers: list[str]
) -> dict[str, pd.DataFrame]:
    """Load fundamentals from cache, apply PIT alignment.

    Returns dict {metric: wide_df [as_of_dates x tickers]}.
    """
    path = settings.data_dir / "cache" / "phase_b_fundamentals.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Fundamentals cache not found: {path}")

    fund_long = pd.read_parquet(path)

    log.info(
        "fundamentals_loaded",
        rows=len(fund_long),
        metrics=fund_long["metric"].unique().tolist(),
        tickers=int(fund_long["ticker"].nunique()),
    )

    # PIT align: filed-date discipline
    panels = pit_align(
        fund_long,
        as_of_dates=as_of_dates,
        tickers=tickers,
        metrics=list(METRIC_TAGS.keys()),
        align_on="filed",
    )

    return panels


def _load_macro(as_of_dates: pd.DatetimeIndex) -> pd.DataFrame | None:
    """Load macro from ALFRED cache JSON.

    Returns long DataFrame [date, cpi..., payems..., vix...] or None.
    """
    cache_dir = settings.data_dir / "cache"

    macro_series = {
        "CPIAUCSL": "cpi",
        "PAYEMS": "payems",
        "VIXCLS": "vix",
    }

    rows: list[dict] = []
    for series_id, col_name in macro_series.items():
        path = cache_dir / f"alfred_{series_id}.json"
        if not path.exists():
            log.warning("macro_cache_missing", series=series_id)
            continue

        with path.open() as f:
            data = json.load(f)

        observations = data.get("observations", [])
        for obs in observations:
            # Use the first print (minimum realtime_start) as the knowable date
            # For simplicity in S0/S1, we use the observation date
            rows.append({
                "date": pd.to_datetime(obs["date"]),
                col_name: float(obs["value"]) if obs["value"] != "." else float("nan"),
            })

    if not rows:
        return None

    macro_df = pd.DataFrame(rows).groupby("date").last().reset_index()

    log.info(
        "macro_loaded",
        rows=len(macro_df),
        columns=macro_df.columns.tolist(),
        date_min=str(macro_df["date"].min()),
        date_max=str(macro_df["date"].max()),
    )

    return macro_df


def _load_universe() -> pd.DataFrame:
    """Load PIT universe from cache."""
    path = settings.data_dir / "cache" / "universe_hanshof.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Universe cache not found: {path}")

    membership = load_hanshof_membership()

    log.info(
        "universe_loaded",
        rows=len(membership),
        date_min=str(membership["date"].min()),
        date_max=str(membership["date"].max()),
    )

    return membership


def _compute_coverage(panel: pd.DataFrame) -> dict[str, float]:
    """Compute per-feature coverage (% non-NaN)."""
    coverage = {}
    for col in panel.columns:
        if col in ("date", "ticker", "forward_return_h"):
            continue
        non_nan = panel[col].notna().sum()
        total = len(panel)
        coverage[col] = non_nan / total * 100 if total > 0 else 0.0
    return coverage


def main() -> None:
    """Main materialization pipeline."""
    log.info("track_b_panel_materialization_start")

    # 1. Load prices
    prices_long, tickers = _load_prices()
    as_of_dates = pd.DatetimeIndex(prices_long["date"].unique()).sort_values()

    # 2. Load fundamentals + PIT align
    fund_panels = _load_fundamentals(as_of_dates, tickers)

    # 3. Compute fundamental features (13 features)
    log.info("computing_fundamental_features")
    fund_features = compute_corporate_vital_signs(fund_panels)

    # Convert to long format
    # fund_features has MultiIndex columns [feature, ticker]
    # After stack(), index becomes (date, ticker), columns become feature
    fund_features_long = fund_features.stack().reset_index()
    fund_features_long.columns = ["date", "ticker"] + list(fund_features.columns.levels[0])
    fund_features_wide = fund_features_long.melt(
        id_vars=["date", "ticker"], var_name="feature", value_name="value"
    )
    fund_features_wide = fund_features_wide.pivot(
        index=["date", "ticker"], columns="feature", values="value"
    ).reset_index()

    # 4. Load macro (optional, for S0)
    macro_df = _load_macro(as_of_dates)

    # 5. Load universe
    membership = _load_universe()

    # 6. Build PIT panel (without price features yet)
    # Use the raw prices + fundamentals for the base panel
    log.info("building_pit_panel")

    # Convert prices to long format with correct column names
    prices_for_panel = prices_long[["date", "ticker", "close"]].copy()
    prices_for_panel = prices_for_panel.sort_values(["date", "ticker"]).reset_index(drop=True)

    # Build base panel with prices only (fundamentals added separately)
    panel = build_pit_panel(
        prices=prices_for_panel,
        fundamentals=None,  # Skip for now, add features separately
        macro=macro_df,
        ff5=None,  # Skip FF5 for S0/S1
        membership=membership,
        horizon=_HORIZON,
    )

    # 7. Add fundamental features
    panel = panel.merge(fund_features_wide, on=["date", "ticker"], how="left")

    # 8. Compute price features
    # Convert prices to wide format for compute_price_features
    prices_wide = pd.read_parquet(settings.data_dir / "cache" / "phase_b_prices.parquet")

    # Check if volume is available (it's not in the current cache)
    volume_wide = None
    log.info("volume_check", has_volume=False, note="turnover_amihud_will_be_nan")

    # Compute price features (no volume, no market benchmark)
    price_features = compute_price_features(
        prices=prices_wide,
        volume=volume_wide,
        market_prices=None,  # No SPY in cache, beta will be NaN
    )

    # Convert to long format
    # price_features has MultiIndex columns [feature, ticker]
    # After stack(), index becomes (date, ticker), columns become feature
    price_features_stacked = price_features.stack()
    price_features_long = price_features_stacked.reset_index()
    price_features_long.columns = ["date", "ticker"] + list(price_features.columns.levels[0])
    price_features_wide = price_features_long.melt(
        id_vars=["date", "ticker"], var_name="feature", value_name="value"
    )
    price_features_wide = price_features_wide.pivot(
        index=["date", "ticker"], columns="feature", values="value"
    ).reset_index()

    # Add Amihud (separate function)
    if volume_wide is not None:
        amihud = compute_amihud_from_wide(prices_wide, volume_wide, window=21)
        amihud_long = amihud.stack().reset_index()
        amihud_long.columns = ["date", "ticker", "amihud_illiquidity_21d"]
        price_features_wide = price_features_wide.merge(
            amihud_long, on=["date", "ticker"], how="left"
        )
    else:
        # Add NaN column for amihud
        price_features_wide["amihud_illiquidity_21d"] = float("nan")

    # 9. Merge price features into panel
    panel = panel.merge(price_features_wide, on=["date", "ticker"], how="left")

    # 10. Filter to 2016+ window (per pre-registration)
    panel["date"] = pd.to_datetime(panel["date"])
    panel_2016 = panel[panel["date"] >= pd.Timestamp("2016-01-01")].copy()

    # 11. Persist
    panel_2016.to_parquet(_OUTPUT_PATH, index=False)

    # 12. Report
    coverage = _compute_coverage(panel_2016)

    log.info(
        "track_b_panel_materialization_complete",
        output=str(_OUTPUT_PATH),
        shape=panel_2016.shape,
        date_min=str(panel_2016["date"].min()),
        date_max=str(panel_2016["date"].max()),
        n_tickers=int(panel_2016["ticker"].nunique()),
        n_dates=int(panel_2016["date"].nunique()),
        coverage_summary={
            col: f"{pct:.1f}%" for col, pct in coverage.items()
        },
        volume_available=False,
        turnover_coverage=f"{coverage.get('turnover_21d', 0):.1f}%",
        amihud_coverage=f"{coverage.get('amihud_illiquidity_21d', 0):.1f}%",
        beta_coverage=f"{coverage.get('beta_252d', 0):.1f}%",
    )

    # Console report
    print("\n" + "=" * 60)
    print("Track B Panel Materialization Report")
    print("=" * 60)
    print(f"\nOutput: {_OUTPUT_PATH}")
    print(f"Shape: {panel_2016.shape[0]} rows × {panel_2016.shape[1]} columns")
    print(f"Date range: {panel_2016['date'].min()} to {panel_2016['date'].max()}")
    print(f"Unique tickers: {panel_2016['ticker'].nunique()}")
    print(f"Unique dates: {panel_2016['date'].nunique()}")

    print("\n--- Feature Coverage (2016+ window) ---")
    # Group by feature type
    fund_cols = TRACK_B_FEATURE_COLS
    price_cols = TRACK_B_PRICE_FEATURE_COLS

    print("\nFundamental features (13):")
    for col in fund_cols:
        cov = coverage.get(col, 0)
        status = "✓ OK" if cov > 50 else "✗ LOW" if cov > 0 else "✗ NaN"
        print(f"  {col:25s} {cov:6.2f}% {status}")

    print("\nPrice features (10):")
    for col in price_cols:
        cov = coverage.get(col, 0)
        status = "✓ OK" if cov > 50 else "✗ LOW" if cov > 0 else "✗ NaN"
        print(f"  {col:25s} {cov:6.2f}% {status}")

    print("\n--- Data Availability Notes ---")
    print("  Volume: NOT AVAILABLE in cache → turnover_21d = NaN")
    print("  Market benchmark: NOT AVAILABLE in cache → beta_252d = NaN")
    print("  Amihud: REQUIRES volume → amihud_illiquidity_21d = NaN")
    print("\n  (These NaNs are expected; features can be added when data available)")
    print("=" * 60)


if __name__ == "__main__":
    main()
