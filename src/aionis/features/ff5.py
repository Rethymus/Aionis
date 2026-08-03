"""Stock-specific rolling FF5/DFF exposures + loading-interaction features (RES-02).

Baseline-ladder design (``tasks/active/TASK-RES-02-baseline-ff5.md``): the raw
FF5/DFF factor series are market-wide TIME SERIES — identical for every stock
within a month — so they can never be cross-sectional features (RD-13 would
flag them CONSTANT and the rank-IC estimator would be degenerate). Every column
this module emits is STOCK-SPECIFIC and varies across the cross-section within
a month:

**A. Rolling factor exposures** (6 cols) — for each stock i and month-end t, a
trailing 252-trading-day window (min 126 obs) ending at t of daily data::

    r_i,d − RF_d = α + Σ_k β_k·F_k,d + ε        (FF5, multivariate OLS)
    r_i,d − RF_d = α + β_dff·ΔDFF_d + ε         (ΔDFF, univariate OLS)

→ ``beta_mkt, beta_smb, beta_hml, beta_rmw, beta_cma, beta_dff``.

**B. Loading × stock-feature interactions** (5 cols) — PIT fundamentals
(filed-date aligned, never period-end)::

    beta_smb_x_size   = beta_smb × ln(mktcap)
    beta_hml_x_value  = beta_hml × pb_ratio
    beta_rmw_x_prof   = beta_rmw × roa
    beta_cma_x_invest = beta_cma × Δfund_assets/fund_assets
    beta_dff_x_lev    = beta_dff × (fund_long_term_debt / fund_assets)

**PIT (no same-month future use)** — the exposure window at month-end t uses
ONLY daily observations with ``date <= t`` (FF5 d-day values are posted after
the d close, DFF d-day values at 16:30 ET on d; both are knowable from d+1's
open, and the month-end value is consumed by the model on the first session of
month t+1). :func:`broadcast_monthly_exposures` carries the month-end values to
sessions STRICTLY AFTER t (backward ``merge_asof`` with
``allow_exact_matches=False``): a session s gets the value computed at the most
recent month-end strictly before s, so sessions within month t never see a
value computed from month t's own data.

**Determinism (H6)** — pure ``numpy.linalg.lstsq`` on pinned inputs; no
parallelism (n_jobs=1); two calls on identical inputs are bit-identical.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from aionis.features.diagnostics import (
    VERDICT_ALL_MISSING,
    VERDICT_CONSTANT,
    VERDICT_FEW_VALID,
    VERDICT_NEAR_CONSTANT,
    feature_variation_diagnostics,
)

# --- exposure estimation (TASK-RES-02 §A) -------------------------------------
BETA_WINDOW = 252  # trailing trading days in the rolling window
BETA_MIN_OBS = 126  # minimum valid observations; fewer -> NaN (LightGBM missing)

EXPOSURE_COLS = (
    "beta_mkt",
    "beta_smb",
    "beta_hml",
    "beta_rmw",
    "beta_cma",
    "beta_dff",
)
INTERACTION_COLS = (
    "beta_smb_x_size",
    "beta_hml_x_value",
    "beta_rmw_x_prof",
    "beta_cma_x_invest",
    "beta_dff_x_lev",
)
ALL_FEATURE_COLS = EXPOSURE_COLS + INTERACTION_COLS

# Factor columns the exposure builder expects in the daily factor frame.
_FACTOR_INPUT_COLS = ("mkt_rf", "smb", "hml", "rmw", "cma", "rf", "dff_change")

# Stock-feature columns the interaction builder reads (PIT, filed-date aligned).
_STOCK_FEATURE_COLS = (
    "mktcap",
    "pb_ratio",
    "roa",
    "fund_assets",
    "fund_long_term_debt",
    "asset_growth",
)

# RD-13 verdicts that fail a column closed (TASK-RD-13 / TASK-RES-02 §RD-13).
_FAILED_VERDICTS = frozenset(
    {VERDICT_CONSTANT, VERDICT_NEAR_CONSTANT, VERDICT_ALL_MISSING, VERDICT_FEW_VALID}
)


def rolling_factor_exposures(
    daily_returns: pd.DataFrame,
    factors: pd.DataFrame,
    as_of_dates: pd.DatetimeIndex,
) -> pd.DataFrame:
    """Rolling factor exposures at each month-end — (date, ticker) panel.

    For every (ticker, as-of date t): take the last ``BETA_WINDOW`` daily
    observations with ``date <= t`` (exact ``t`` included — knowable from
    t+1's open, per the module docstring), regress excess returns on the five
    FF5 daily factors (multivariate OLS with intercept) and on ΔDFF
    (univariate OLS with intercept) after dropping rows with any non-finite
    value (never filled). Fewer than ``BETA_MIN_OBS`` valid observations ->
    NaN row (LightGBM missing policy).

    Args:
        daily_returns: wide frame, index = trading dates (unique, sorted
            ascending), columns = tickers, values = daily decimal returns.
        factors: date-indexed frame with columns ``mkt_rf, smb, hml, rmw, cma,
            rf, dff_change`` (ΔDFF as-of, see ``aionis.ingest.macro_dff``).
        as_of_dates: month-end dates at which exposures are computed (sorted;
            each must be <= the last daily date — beyond it is a lookahead
            guard error).

    Returns:
        DataFrame indexed by ``(date, ticker)`` with columns
        ``EXPOSURE_COLS`` (beta_mkt … beta_dff), one row per (month-end,
        ticker), NaN where the window is too short.
    """
    if missing := set(_FACTOR_INPUT_COLS) - set(factors.columns):
        raise ValueError(f"factors missing columns: {sorted(missing)}")
    if daily_returns.index.has_duplicates:
        raise ValueError("daily_returns index must be unique")
    if not daily_returns.index.is_monotonic_increasing:
        raise ValueError("daily_returns index must be sorted ascending")
    if len(daily_returns.columns) == 0:
        raise ValueError("daily_returns must have at least one ticker column")

    dates = pd.DatetimeIndex(as_of_dates).normalize()
    idx = daily_returns.index
    if len(dates) and dates.max() > idx.max():
        raise ValueError(
            "as_of_dates extend beyond the daily history "
            "(a feature at t may never use observations after t)"
        )

    # Deterministic factor column order (never trust the caller's ordering).
    f = factors.reindex(idx)[list(_FACTOR_INPUT_COLS)]
    rf = f["rf"].to_numpy(dtype=float)
    x5 = f[["mkt_rf", "smb", "hml", "rmw", "cma"]].to_numpy(dtype=float)
    x_dff = f["dff_change"].to_numpy(dtype=float)

    rows: list[tuple[pd.Timestamp, str, float, float, float, float, float, float]] = []
    for ticker in daily_returns.columns:
        rets = daily_returns[ticker].to_numpy(dtype=float)
        for t in dates:
            j = idx.searchsorted(t, side="right")  # first index strictly after t
            lo = max(0, j - BETA_WINDOW)
            if j - lo < BETA_MIN_OBS:
                rows.append((t, ticker, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan))
                continue
            y = rets[lo:j] - rf[lo:j]
            ok5 = np.isfinite(y) & np.isfinite(x5[lo:j]).all(axis=1)
            ok_dff = ok5 & np.isfinite(x_dff[lo:j])
            n5 = int(ok5.sum())
            n_dff = int(ok_dff.sum())
            if n5 < BETA_MIN_OBS:
                rows.append((t, ticker, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan))
                continue
            yv5 = y[ok5]
            x5v = x5[lo:j][ok5]
            betas5, *_ = np.linalg.lstsq(
                np.column_stack([np.ones(n5), x5v]), yv5, rcond=None
            )
            if n_dff < BETA_MIN_OBS:
                beta_dff = np.nan
            else:
                yv_dff = y[ok_dff]
                x_dff_v = x_dff[lo:j][ok_dff]
                beta_dff, *_ = np.linalg.lstsq(
                    np.column_stack([np.ones(n_dff), x_dff_v]), yv_dff, rcond=None
                )
            rows.append(
                (
                    t,
                    ticker,
                    float(betas5[1]),
                    float(betas5[2]),
                    float(betas5[3]),
                    float(betas5[4]),
                    float(betas5[5]),
                    float(beta_dff[1]) if isinstance(beta_dff, np.ndarray) else np.nan,
                )
            )

    out = pd.DataFrame(rows, columns=["date", "ticker", *EXPOSURE_COLS])
    return out.set_index(["date", "ticker"])


def asset_growth_from_filings(
    long: pd.DataFrame,
    as_of_dates: pd.DatetimeIndex,
    tickers: list[str],
) -> pd.DataFrame:
    """Δfund_assets/fund_assets between consecutive filings — PIT, (date, ticker).

    Per ticker and per as-of date d: take the two most recent ASSETS facts with
    ``filed <= d`` (distinct filing dates — same-day duplicates keep the last);
    growth = latest/previous − 1. Fewer than two distinct filings, a missing /
    non-finite value, or a non-positive previous value -> NaN. This is the
    filed-date PIT growth (never a period-end or a month-over-month as-of
    pseudo-change).

    Args:
        long: long fundamentals frame [ticker, metric, filed, value, ...] (the
            ``aionis.ingest.fundamentals.build_fundamentals`` shape).
        as_of_dates: month-end dates (sorted).
        tickers: universe tickers.

    Returns:
        Wide DataFrame (as_of_dates × tickers) of decimal asset growth.
    """
    dates = pd.DatetimeIndex(as_of_dates).normalize()
    wide = pd.DataFrame(index=dates, columns=list(tickers), dtype=float)
    if long.empty or "metric" not in long.columns:
        return wide
    sub = long[long["metric"] == "assets"].copy()
    if sub.empty:
        return wide
    sub["filed"] = pd.to_datetime(sub["filed"]).dt.normalize()
    sub = sub.dropna(subset=["filed", "value"]).sort_values("filed")
    sub = sub.drop_duplicates(["ticker", "filed"], keep="last")
    if sub.empty:
        return wide

    grouped = {t: g for t, g in sub.groupby("ticker")}
    day_nums = dates.to_numpy(dtype="datetime64[ns]")
    for t in tickers:
        s = grouped.get(t)
        if s is None or len(s) < 2:
            continue
        filed = s["filed"].to_numpy(dtype="datetime64[ns]")
        vals = s["value"].to_numpy(dtype=float)
        pos = np.searchsorted(filed, day_nums, side="right")  # facts with filed <= d
        out = np.full(len(dates), np.nan)
        prev_ok = np.isfinite(vals)
        for k, jk in enumerate(pos):
            if jk >= 2 and prev_ok[jk - 2] and prev_ok[jk - 1] and vals[jk - 2] > 0:
                out[k] = vals[jk - 1] / vals[jk - 2] - 1.0
        wide[t] = out
    return wide


def build_ff5_interactions(
    exposures: pd.DataFrame,
    stock_features: pd.DataFrame,
) -> pd.DataFrame:
    """The five loading × stock-feature interactions — (date, ticker) panel.

    ``exposures`` is the (date, ticker)-indexed exposure panel from
    :func:`rolling_factor_exposures`; ``stock_features`` is a (date, ticker)-
    indexed frame with PIT (filed-date aligned) columns ``mktcap, pb_ratio,
    roa, fund_assets, fund_long_term_debt, asset_growth`` on the SAME date
    grid. Missing or non-positive inputs propagate to NaN (never silently
    filled or clipped).

    Returns a (date, ticker)-indexed frame with columns ``INTERACTION_COLS``.
    """
    if missing := set(_STOCK_FEATURE_COLS) - set(stock_features.columns):
        raise ValueError(f"stock_features missing columns: {sorted(missing)}")
    if not isinstance(exposures.index, pd.MultiIndex):
        raise ValueError("exposures must be (date, ticker) MultiIndex")
    if not isinstance(stock_features.index, pd.MultiIndex):
        raise ValueError("stock_features must be (date, ticker) MultiIndex")

    joined = exposures.join(stock_features, how="left")
    mktcap = joined["mktcap"]
    assets = joined["fund_assets"]
    with np.errstate(invalid="ignore", divide="ignore"):
        ln_mktcap = np.log(mktcap).where(mktcap > 0)
        leverage = (joined["fund_long_term_debt"] / assets).where(assets > 0)

    out = pd.DataFrame(index=joined.index)
    out["beta_smb_x_size"] = joined["beta_smb"] * ln_mktcap
    out["beta_hml_x_value"] = joined["beta_hml"] * joined["pb_ratio"]
    out["beta_rmw_x_prof"] = joined["beta_rmw"] * joined["roa"]
    out["beta_cma_x_invest"] = joined["beta_cma"] * joined["asset_growth"]
    out["beta_dff_x_lev"] = joined["beta_dff"] * leverage
    return out[list(INTERACTION_COLS)]


def broadcast_monthly_exposures(
    monthly: pd.DataFrame,
    sessions: pd.DatetimeIndex,
) -> pd.DataFrame:
    """Carry month-end feature values to sessions PIT (no same-month future).

    A feature computed at month-end t (from data <= t) is knowable from the
    FIRST session of month t+1. A session s therefore gets the value computed
    at the most recent month-end STRICTLY BEFORE s (backward ``merge_asof``,
    ``allow_exact_matches=False``): sessions within month t never see a value
    computed from month t's own data; sessions before the first month-end are
    NaN.

    Args:
        monthly: (date, ticker)-indexed frame of month-end feature values.
        sessions: the session grid of the frozen panel (sorted, unique).

    Returns:
        (date, ticker)-indexed frame on the session grid with the same columns
        (NaN before the first month-end).
    """
    if not isinstance(monthly.index, pd.MultiIndex):
        raise ValueError("monthly must be (date, ticker) MultiIndex")
    if monthly.index.nlevels != 2:
        raise ValueError("monthly index must have exactly (date, ticker) levels")

    sessions = pd.DatetimeIndex(sessions).normalize()
    month_ends = pd.DatetimeIndex(
        sorted(pd.DatetimeIndex(monthly.index.get_level_values(0)).normalize().unique())
    )

    left = pd.DataFrame({"d": sessions})
    right = pd.DataFrame({"d": month_ends}).assign(order=np.arange(len(month_ends)))
    merged = pd.merge_asof(left, right, on="d", direction="backward", allow_exact_matches=False)
    orders = merged["order"].to_numpy()
    known = ~pd.isna(orders)
    src = orders[known].astype(int)

    tickers = sorted(monthly.index.get_level_values(1).unique())
    grid = pd.MultiIndex.from_product([sessions, tickers], names=["date", "ticker"])
    parts: dict[str, np.ndarray] = {}
    for col in monthly.columns:
        wide = monthly[col].unstack().reindex(index=month_ends, columns=tickers)
        vals = wide.to_numpy(dtype=float)  # n_month_ends × n_tickers
        out = np.full((len(sessions), len(tickers)), np.nan, dtype=float)
        if len(month_ends):
            out[known] = vals[src]
        # grid is date-major product(sessions, tickers) == C-order ravel.
        parts[col] = out.ravel()

    frame = pd.DataFrame(parts, index=grid)
    return frame


def rd13_diagnostics(panel: pd.DataFrame) -> pd.DataFrame:
    """RD-13 per-(month, column) cross-sectional variation diagnostics.

    Thin wrapper over :func:`aionis.features.diagnostics.feature_variation_diagnostics`
    (read-only; the RD-13 module itself is COMPLETE and never modified): a
    (date, ticker)-indexed panel -> the long diagnostic report [date, feature,
    verdict, unique_count, std, coverage, valid_count, reason].
    """
    if not isinstance(panel.index, pd.MultiIndex):
        raise ValueError("panel must be (date, ticker) MultiIndex")
    if panel.empty:
        raise ValueError("panel must not be empty")
    return feature_variation_diagnostics(panel)


def rd13_filter_columns(
    diag: pd.DataFrame,
    columns: list[str],
) -> tuple[list[str], dict[str, list[str]]]:
    """Fail-closed RD-13 gate: keep columns with NO failing month.

    A column passes only if EVERY (month, column) verdict is VARIATION — any
    month with CONSTANT / NEAR_CONSTANT / ALL_MISSING / FEW_VALID excludes the
    column (TASK-RES-02 §RD-13: fail closed; the reason codes go to the trial
    registry). Market-wide raw factor columns are CONSTANT by construction and
    are therefore structurally excluded here.

    Args:
        diag: output of :func:`rd13_diagnostics`.
        columns: candidate feature columns.

    Returns:
        ``(passing, failing)`` — the columns that pass, and ``{column:
        ["<month>: <verdict>", ...]}`` for the failures.
    """
    failing: dict[str, list[str]] = {}
    for col in columns:
        sub = diag[diag["feature"] == col]
        flagged = sub[sub["verdict"].isin(_FAILED_VERDICTS)]
        if not flagged.empty:
            failing[col] = [
                f"{pd.Timestamp(d).date()}: {v}"
                for d, v in zip(flagged["date"], flagged["verdict"], strict=True)
            ]
    passing = [c for c in columns if c not in failing]
    return passing, failing


def verdict_rollup(diag: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """One row per column: (passing months, failing months) from the RD-13 report."""
    rows = []
    for col in columns:
        sub = diag[diag["feature"] == col]
        counts = sub["verdict"].value_counts().to_dict()
        rows.append(
            {
                "feature": col,
                "n_months": int(len(sub)),
                "n_variation": int(counts.get("VARIATION", 0)),
                "n_failed": int(sum(counts.get(v, 0) for v in sorted(_FAILED_VERDICTS))),
                "verdicts": ", ".join(f"{v}:{counts[v]}" for v in sorted(counts)),
            }
        )
    cols = ["feature", "n_months", "n_variation", "n_failed", "verdicts"]
    return pd.DataFrame(rows, columns=cols)


__all__ = [
    "BETA_WINDOW",
    "BETA_MIN_OBS",
    "EXPOSURE_COLS",
    "INTERACTION_COLS",
    "ALL_FEATURE_COLS",
    "rolling_factor_exposures",
    "asset_growth_from_filings",
    "build_ff5_interactions",
    "broadcast_monthly_exposures",
    "rd13_diagnostics",
    "rd13_filter_columns",
    "verdict_rollup",
]
