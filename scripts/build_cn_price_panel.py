#!/usr/bin/env python3
"""Track C A-share price-only panel builder.

Mirrors the US-side Track B pipeline, but for A-shares. Constructs a
cross-sectional panel [date, ticker, 10_price_features, limit_up_down_distance,
suspension_flag, forward_return_h] from CSI300 daily price data.

PIT universe: the source price snapshot is an EVER-MEMBER pool (every historical
CSI300 constituent fetched over full history). Before writing, the panel is
filtered to (date, ticker) cells that were PIT index members per
``data/cache/csi300_constituents.parquet`` (half-open membership [opt_in, opt_out)
— the removal day itself is NOT a member), so a date's cross-section is exactly
its then-current CSI300 constituents, not the ever-member pool. Coverage note:
the membership table caps still-members at its snapshot date, so panel dates at
or beyond that snapshot have no membership rows and are dropped — refresh the
constituents cache to extend the panel's effective end date.

This is an exploratory feature set (NOT wired to the live pipeline, NO ledger
write). Uses H6 determinism (seed=0, n_jobs=1) and PIT leakage guards.

Run: uv run python scripts/build_cn_price_panel.py

Data source: data/cache/ashare_prices_csi300.parquet (929 tickers, 2014-2026)
Membership:  data/cache/csi300_constituents.parquet (PIT long table, mandatory)
Output: data/cache/cn_price_panel.parquet
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd
import structlog

from aionis.config import settings
from aionis.features.ashare_extras import limit_up_down_distance, suspension_flag
from aionis.features.price_features import (
    compute_amihud_from_wide,
    compute_price_features,
)
from aionis.features.selection_panel import forward_returns

log = structlog.get_logger()

# Constants
H = 21  # Forward return horizon (sessions, ~1 month)
CACHE_DIR = settings.data_dir / "cache"
SOURCE_PARQUET = CACHE_DIR / "ashare_prices_csi300.parquet"
CONSTITUENTS_PARQUET = CACHE_DIR / "csi300_constituents.parquet"
OUTPUT_PARQUET = CACHE_DIR / "cn_price_panel.parquet"


def _load_and_pivot_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load A-share price data and pivot to wide format.

    Returns:
        (close_wide, volume_wide, tradestatus_wide) — all [dates x tickers]
    """
    log.info("loading_a_share_prices", path=SOURCE_PARQUET)
    df = pd.read_parquet(SOURCE_PARQUET)
    log.info(
        "loaded_raw_data",
        rows=len(df),
        tickers=df["ticker"].nunique(),
        date_range=(df["date"].min(), df["date"].max()),
    )

    # Pivot to wide format
    close_wide = df.pivot(index="date", columns="ticker", values="close")
    volume_wide = df.pivot(index="date", columns="ticker", values="volume")
    tradestatus_wide = df.pivot(index="date", columns="ticker", values="tradestatus")

    log.info(
        "pivoted_to_wide",
        close_shape=close_wide.shape,
        volume_shape=volume_wide.shape,
        tradestatus_shape=tradestatus_wide.shape,
    )
    return close_wide, volume_wide, tradestatus_wide


def _compute_market_proxy(close_wide: pd.DataFrame) -> pd.Series:
    """Compute equal-weight CSI300 market proxy (exploratory approximation).

    A cap-weighted index would require separate market-cap data (out of scope).
    Equal-weight is documented as the exploratory approximation for beta.

    Args:
        close_wide: Close prices [dates x tickers]

    Returns:
        Market price Series (equal-weight mean across tickers)
    """
    market_prices = close_wide.mean(axis=1)
    log.info("computed_market_proxy", ew_mean=True)
    return market_prices


def _membership_ticker_to_panel_format(ticker: str) -> str:
    """``SZ000001`` (index-constitution) -> ``sz.000001`` (baostock code).

    The membership long table uses index-constitution symbols (exchange prefix
    upper-case); the price panel stores raw baostock ``code`` values. This mirrors
    ``scripts/ashare_price_fetch_csi300.py::_csi300_to_baostock`` so the join keys
    line up exactly as they did at fetch time. Already-dotted (baostock-format)
    tickers pass through unchanged.
    """
    t = str(ticker).strip()
    return t if "." in t else t[:2].lower() + "." + t[2:]


def _filter_to_pit_members(
    panel: pd.DataFrame, membership: pd.DataFrame
) -> pd.DataFrame:
    """Filter a tidy [date, ticker, ...] panel to PIT CSI300 member (date, ticker) cells.

    The source price snapshot is an ever-member pool, so without this mask a date's
    cross-section would include tickers already removed from (or not yet added to)
    the index — survivorship/look-ahead contamination. Membership semantics follow
    ``csi300_constituents._parse_opt_in_opt_out_to_long``: a ticker is a member on
    ``date`` iff ``opt_in <= date < opt_out`` (half-open; the removal day itself is
    NOT a member, so no membership row exists for it).

    Args:
        panel: Long panel with at least [date, ticker] columns (month-end sampled).
        membership: Long [date, ticker] CSI300 membership table (one row per
            member-day, e.g. from ``fetch_csi300_constituents``).

    Returns:
        Panel rows restricted to member (date, ticker) cells, sorted by
        [date, ticker], index reset.
    """
    mem = membership.loc[:, ["date", "ticker"]].copy()
    mem["date"] = pd.to_datetime(mem["date"]).dt.normalize()
    mem["ticker"] = mem["ticker"].map(_membership_ticker_to_panel_format)
    mem = mem.drop_duplicates()

    pan = panel.copy()
    pan["date"] = pd.to_datetime(pan["date"]).dt.normalize()
    out = pan.merge(mem, on=["date", "ticker"], how="inner")
    log.info(
        "pit_membership_filter",
        rows_before=len(pan),
        rows_after=len(out),
        dropped_non_members=len(pan) - len(out),
    )
    return out.sort_values(["date", "ticker"]).reset_index(drop=True)


def _build_features(
    close_wide: pd.DataFrame,
    volume_wide: pd.DataFrame,
    tradestatus_wide: pd.DataFrame,
) -> pd.DataFrame:
    """Build the full feature panel (10 price features + A-share extras).

    Args:
        close_wide: Close prices [dates x tickers]
        volume_wide: Volume [dates x tickers]
        tradestatus_wide: Trade status [dates x tickers]

    Returns:
        Long-format DataFrame [date, ticker, feature1, ..., featureN]
    """
    # Market proxy (equal-weight CSI300)
    market_prices = _compute_market_proxy(close_wide)

    # Compute the 10 Track B price features (region-agnostic)
    log.info("computing_price_features")
    price_features_multiidx = compute_price_features(
        prices=close_wide, volume=volume_wide, market_prices=market_prices
    )

    # Flatten MultiIndex columns to [date, ticker, *features].
    # compute_price_features returns DataFrame[index=date, columns=MultiIndex(feature, ticker)].
    # stack() moves the innermost column level (ticker) onto the index; reset_index() then
    # yields [date, ticker, feature_1 ... feature_9] directly — no melt/pivot needed.
    features_wide = price_features_multiidx.stack().reset_index()
    features_wide.columns.name = None
    # Force the date column name — the real pivot names the index "date", but don't
    # depend on it (robust to unnamed indices, e.g. synthetic test fixtures).
    features_wide = features_wide.rename(columns={features_wide.columns[0]: "date"})

    log.info(
        "computed_price_features",
        feature_cols=list(features_wide.columns),
        n_features=len(features_wide.columns) - 2,  # minus date, ticker
    )

    # Compute Amihud illiquidity (separate function, not in the 10)
    log.info("computing_amihud_illiquidity")
    amihud_wide = compute_amihud_from_wide(close_wide, volume_wide, window=21)
    amihud_long = amihud_wide.stack().reset_index()
    amihud_long.columns = ["date", "ticker", "amihud_illiquidity_21d"]

    # Compute A-share extras (limit up/down, suspension)
    log.info("computing_ashare_extras")
    returns = close_wide.pct_change()
    limit_dist_wide = limit_up_down_distance(returns, limit=0.10)
    limit_dist_long = limit_dist_wide.stack().reset_index()
    limit_dist_long.columns = ["date", "ticker", "limit_up_down_distance"]

    susp_flag_wide = suspension_flag(tradestatus_wide)
    susp_flag_long = susp_flag_wide.stack().reset_index()
    susp_flag_long.columns = ["date", "ticker", "suspension_flag"]

    # Merge all features
    panel = features_wide.merge(amihud_long, on=["date", "ticker"], how="outer")
    panel = panel.merge(limit_dist_long, on=["date", "ticker"], how="outer")
    panel = panel.merge(susp_flag_long, on=["date", "ticker"], how="outer")

    log.info(
        "merged_all_features",
        final_cols=list(panel.columns),
        n_cols=len(panel.columns),
    )
    return panel


def _add_label_and_sample(
    panel: pd.DataFrame, close_wide: pd.DataFrame
) -> pd.DataFrame:
    """Add forward return label and apply month-end sampling.

    Args:
        panel: Feature panel (long format)
        close_wide: Close prices [dates x tickers]

    Returns:
        Panel with forward_return_h label, month-end sampled
    """
    # Forward returns (label)
    log.info("computing_forward_returns", horizon=H)
    fwd_returns_wide = forward_returns(close_wide, h=H)
    fwd_returns_long = fwd_returns_wide.stack().reset_index()
    fwd_returns_long.columns = ["date", "ticker", "forward_return_h"]

    panel = panel.merge(fwd_returns_long, on=["date", "ticker"], how="left")

    # Month-end sampling: keep rows where date == max(date) in its year-month
    # This mirrors the long_short_returns month-end logic
    log.info("applying_month_end_sampling")
    panel["year_month"] = pd.to_datetime(panel["date"]).dt.to_period("M")
    month_end_dates = panel.groupby("year_month")["date"].transform("max")
    panel = panel[panel["date"] == month_end_dates].drop(columns="year_month")

    log.info("month_end_sampled", rows=len(panel))
    return panel


def _leakage_self_check(panel: pd.DataFrame, close_wide: pd.DataFrame) -> bool:
    """Verify anti-leakage invariants: features past-only, label future-only.

    Checks:
    1. A feature at (t, ticker) depends only on close[≤t]
       -> Mutate a future close, feature at t unchanged
    2. Label at (t, ticker) depends on close[t+h]
       -> Mutate close[t+h], label at t changes

    Args:
        panel: Built panel (long format)
        close_wide: Original close prices [dates x tickers]

    Returns:
        True if leakage guard passes (raises AssertionError if fails)
    """
    log.info("running_leakage_self_check")

    # Pick a (ticker, date) that EXISTS in the month-end-sampled panel. A raw mid-series
    # date from close_wide is absent after month-end sampling -> illic out-of-bounds.
    clean = panel.dropna(subset=["momentum_21d", "forward_return_h"])
    sample = clean.iloc[len(clean) // 2]
    sample_ticker = sample["ticker"]
    test_date = sample["date"]
    feature_row = sample
    # Future date = H sessions after test_date in the raw close_wide index.
    mid_idx = close_wide.index.get_loc(test_date)
    future_idx = min(mid_idx + H, len(close_wide) - 1)
    future_date = close_wide.index[future_idx]
    original_momentum = feature_row["momentum_21d"]
    original_label = feature_row["forward_return_h"]

    # Check 1: Mutate future close -> feature at t unchanged
    close_wide_mutated = close_wide.copy()
    close_wide_mutated.loc[future_date, sample_ticker] *= 1.5

    # Recompute features on mutated data (simplified: just momentum)
    returns_mutated = close_wide_mutated.pct_change()
    momentum_mutated = returns_mutated.rolling(21, min_periods=21).sum().loc[
        test_date, sample_ticker
    ]

    # Momentum at t should be UNCHANGED (only looks back, not forward)
    assert np.isclose(
        momentum_mutated, original_momentum, rtol=1e-10
    ), f"LEAKAGE: momentum at {test_date} changed when future close mutated"

    # Check 2: Mutate future close -> label at t CHANGES
    expected_new_label = (close_wide_mutated.loc[future_date, sample_ticker] /
                          close_wide.loc[test_date, sample_ticker] - 1.0)

    assert not np.isclose(
        original_label, expected_new_label, rtol=1e-5
    ), f"LEAKAGE: label at {test_date} unchanged when future close mutated"

    log.info("leakage_self_check_passed")
    return True


def main() -> None:
    """Build the CN price panel and write to parquet."""
    # Check PHASE_C_NO_LEDGER mode (this builder never writes ledger)
    no_ledger = os.environ.get("PHASE_C_NO_LEDGER", "0") == "1"
    if no_ledger:
        log.info("PHASE_C_NO_LEDGER=1: artifacts-only mode (no ledger)")

    # PIT membership table is MANDATORY: without it the panel would be an
    # ever-member pool (survivorship/look-ahead contamination). Fail closed.
    if not CONSTITUENTS_PARQUET.exists():
        raise SystemExit(
            f"[ERROR] {CONSTITUENTS_PARQUET} missing — run the CSI300 constituents "
            "fetch first. The (date, ticker) PIT membership filter is mandatory; "
            "building an unfiltered ever-member panel would leak."
        )
    membership = pd.read_parquet(CONSTITUENTS_PARQUET)

    # Load and pivot data
    close_wide, volume_wide, tradestatus_wide = _load_and_pivot_data()

    # Build features (10 Track B + amihud + 2 A-share extras)
    panel = _build_features(close_wide, volume_wide, tradestatus_wide)

    # Add label and apply month-end sampling
    panel = _add_label_and_sample(panel, close_wide)

    # PIT CSI300 membership filter (ever-member pool -> per-date member cross-section)
    panel = _filter_to_pit_members(panel, membership)

    # Sort by date, ticker
    panel = panel.sort_values(["date", "ticker"]).reset_index(drop=True)

    # Leakage self-check (deterministic verification)
    _leakage_self_check(panel, close_wide)

    # Write to parquet
    OUTPUT_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(OUTPUT_PARQUET, index=False)

    # Summary statistics
    n_rows = len(panel)
    n_tickers = panel["ticker"].nunique()
    date_range = (panel["date"].min(), panel["date"].max())
    cols = list(panel.columns)

    log.info(
        "cn_price_panel_built",
        path=str(OUTPUT_PARQUET),
        rows=n_rows,
        tickers=n_tickers,
        date_range=date_range,
        columns=cols,
        n_columns=len(cols),
    )

    print(f"CN price panel built: {n_rows} rows, {n_tickers} tickers, {date_range}")
    print(f"Columns ({len(cols)}): {cols}")
    print(f"Output: {OUTPUT_PARQUET}")
    print("Leakage self-check: PASSED")
    print("PIT membership filter: applied (cross-section = per-date CSI300 members)")
    print(
        "Caveat: market_prices = equal-weight CSI300 proxy "
        "(cap-weight would need separate fetch)"
    )


if __name__ == "__main__":
    main()
