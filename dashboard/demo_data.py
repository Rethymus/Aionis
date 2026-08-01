"""Demonstrative synthetic data generators for Aionis dashboard v2.

All generators are DETERMINISTIC with seed=0 — same input → identical output.
Data is for DEMONSTRATION ONLY — shows analysis methods, not final conclusions.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Fixed seed for determinism
RANDOM_STATE = 0


def _rng() -> np.random.Generator:
    """Create a fresh RNG with the fixed seed for each call."""
    return np.random.default_rng(RANDOM_STATE)


def _monthly_ic_series(
    months: int = 125,
    mean_ic: float = 0.0,
    std_ic: float = 0.06,
) -> pd.DataFrame:
    """Generate a monthly rank-IC series (plausible S&P 500 cross-sectional IC).

    Args:
        months: Number of months (~10 years for S&P 500)
        mean_ic: True mean IC (0 = null signal)
        std_ic: Monthly IC volatility (0.06 = realistic for rank-IC)

    Returns:
        DataFrame with columns: date, ic_state, ic_base
    """
    dates = pd.date_range(start="2014-01-01", periods=months, freq="ME")
    rng = _rng()
    ic_state = rng.normal(mean_ic, std_ic, months)
    ic_base = rng.normal(mean_ic, std_ic, months)

    return pd.DataFrame({"date": dates, "ic_state": ic_state, "ic_base": ic_base})


def _oos_panel(
    months: int = 125,
    n_tickers: int = 500,
) -> pd.DataFrame:
    """Generate out-of-sample panel [date, ticker, score, y_fwd_ret].

    This is the full panel needed for scatter/quantile charts.

    Args:
        months: Number of months
        n_tickers: Approximate S&P 500 size

    Returns:
        DataFrame with columns: date, ticker, score, y_fwd_ret
    """
    dates = pd.date_range(start="2014-01-01", periods=months, freq="ME")
    tickers = [f"T{i:04d}" for i in range(n_tickers)]
    rng = _rng()

    rows = []
    for date in dates:
        # Score ~ N(0, 1)
        scores = rng.normal(0, 1, n_tickers)
        # Forward return ~ weakly correlated with score (IC ≈ 0.03)
        ic_true = 0.03
        epsilon = rng.normal(0, 1, n_tickers)
        y_fwd_ret = ic_true * scores + epsilon
        y_fwd_ret = y_fwd_ret * 0.05  # Scale to monthly return volatility

        for ticker, score, ret in zip(tickers, scores, y_fwd_ret, strict=True):
            rows.append({"date": date, "ticker": ticker, "score": score, "y_fwd_ret": ret})

    return pd.DataFrame(rows)


def _quantile_aggregate(oos_df: pd.DataFrame, n_quantiles: int = 5) -> pd.DataFrame:
    """Aggregate OOS panel to quantile-level [date, quantile, mean_score, mean_ret, n].

    Args:
        oos_df: OOS panel from _oos_panel()
        n_quantiles: Number of quantiles (5 = quintile, 10 = decile)

    Returns:
        DataFrame with columns: date, quantile, mean_score, mean_ret, n
    """
    result_rows = []

    for date, group in oos_df.groupby("date"):
        group = group.copy()
        group["quantile"] = pd.qcut(
            group["score"], q=n_quantiles, labels=False, duplicates="drop"
        ) + 1

        for q in range(1, n_quantiles + 1):
            q_group = group[group["quantile"] == q]
            if len(q_group) == 0:
                continue
            result_rows.append({
                "date": date,
                "quantile": q,
                "mean_score": q_group["score"].mean(),
                "mean_ret": q_group["y_fwd_ret"].mean(),
                "n": len(q_group),
            })

    return pd.DataFrame(result_rows)


def _ls_returns(
    months: int = 125,
    strategies: list[str] | None = None,
) -> pd.DataFrame:
    """Generate monthly long-short return series [date, <strategy>...].

    Args:
        months: Number of months
        strategies: Strategy names

    Returns:
        Wide DataFrame with date + column per strategy
    """
    if strategies is None:
        strategies = ["state", "base", "placebo"]

    dates = pd.date_range(start="2014-01-01", periods=months, freq="ME")
    rng = _rng()

    # Strategy returns: slight edge for state vs base, placebo ~ 0
    data = {"date": dates}
    for strat in strategies:
        if strat == "state":
            # Slight positive mean (0.005 monthly ≈ 6% annual)
            ret = rng.normal(0.005, 0.06, months)
        elif strat == "base":
            # Near zero
            ret = rng.normal(0.001, 0.06, months)
        else:  # placebo
            # Zero mean
            ret = rng.normal(0.0, 0.06, months)
        data[strat] = ret

    return pd.DataFrame(data)


def _car_path(
    window_days: int = 60,
    center: int = 20,
    n_events: int = 50,
) -> dict:
    """Generate CAR path around events for event-study demo.

    Args:
        window_days: Total window length (t=-20..t+40 = 60 days)
        center: Event day index in the window
        n_events: Number of events to simulate

    Returns:
        Dict with: window (tuple), car (list), ci_lo (list), ci_hi (list), n_events
    """
    t = np.arange(-center, window_days - center)
    rng = _rng()

    # CAR path: small drift upward post-event (demonstrative pattern)
    car = np.cumsum(rng.normal(0.001, 0.01, len(t)))
    # CI band via bootstrap-style simulation
    n_bootstrap = 1000
    bootstrap_paths = np.array([
        np.cumsum(rng.normal(0.001, 0.01, len(t)))
        for _ in range(n_bootstrap)
    ])
    ci_lo = np.percentile(bootstrap_paths, 2.5, axis=0)
    ci_hi = np.percentile(bootstrap_paths, 97.5, axis=0)

    return {
        "window": (-center, window_days - center),
        "t": list(t),
        "car": list(car),
        "ci_lo": list(ci_lo),
        "ci_hi": list(ci_hi),
        "n_events": n_events,
    }


def _differential_forest_plot() -> pd.DataFrame:
    """Generate differential data for forest plot (headline vs controls).

    Returns:
        DataFrame with columns: label, mean_diff, ci_lo, ci_hi
    """
    controls = ["headline", "lag_shift", "placebo", "leave_one_out"]
    rng = _rng()

    # Headline: slight positive but CI includes zero
    # Controls: near zero
    data = []
    for control in controls:
        if control == "headline":
            mean = 0.008
        else:
            mean = rng.normal(0.0, 0.002)
        ci_half = 0.012 if control == "headline" else 0.010
        data.append({
            "label": control,
            "mean_diff": mean,
            "ci_lo": mean - ci_half,
            "ci_hi": mean + ci_half,
        })

    return pd.DataFrame(data)


def _bootstrap_distribution() -> np.ndarray:
    """Generate bootstrap distribution of the mean differential.

    Returns:
        Array of bootstrap replicates
    """
    n_bootstrap = 1000
    rng = _rng()
    # True mean = 0.008, bootstrap reflects this with some spread
    return rng.normal(0.008, 0.004, n_bootstrap)


def _ci_half_by_phase() -> pd.DataFrame:
    """Generate CI half-width by phase for the publishability gate chart.

    Returns:
        DataFrame with columns: phase, ci_half
    """
    phases = ["B", "C", "D", "E1"]
    # Show some phases near the 0.015 gate, some above
    ci_halves = [0.018, 0.012, 0.014, 0.020]  # C and D "near publishable"
    return pd.DataFrame({"phase": phases, "ci_half": ci_halves})


def _factor_data_and_prices(
    months: int = 125,
    n_tickers: int = 500,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate factor data and price data for alphalens factor analysis.

    Returns:
        factor_data: DataFrame with index=[date, ticker], column='factor'
        prices: DataFrame with index=date, columns=tickers
    """
    # Use month-end dates with explicit frequency
    month_end_dates = pd.date_range(start="2014-01-31", periods=months, freq="ME")

    # Generate daily dates for the entire period (approx 20 trading days per month)
    start_date = "2014-01-01"
    end_date = pd.Timestamp(month_end_dates[-1]) + pd.DateOffset(months=1)
    dates = pd.date_range(start=start_date, end=end_date, freq="B")  # Business days

    tickers = [f"T{i:04d}" for i in range(n_tickers)]
    rng = _rng()

    # Generate prices (random walk starting from $100)
    # Use month-end frequency to match factor_data and avoid alphalens frequency errors
    price_data = {}
    for ticker in tickers:
        # Daily returns ~ N(0.0005, 0.02) (slight upward drift, 2% daily vol)
        daily_ret = rng.normal(0.0005, 0.02, len(dates))
        price_data[ticker] = 100 * np.cumprod(1 + daily_ret)

    prices = pd.DataFrame(price_data, index=dates)
    prices.index.name = "date"

    # Resample prices to month-end frequency to match factor_data
    # This is required by alphalens to avoid frequency mismatch errors
    prices = prices.resample("ME").last()
    prices.index = pd.DatetimeIndex(prices.index, freq="ME")

    # Generate factor scores (monthly, aligned to month ends)
    factor_rows = []

    for date in month_end_dates:
        for ticker in tickers:
            # Factor score ~ N(0, 1)
            factor_score = rng.normal(0, 1)
            factor_rows.append({"date": date, "ticker": ticker, "factor": factor_score})

    factor_data = pd.DataFrame(factor_rows)
    factor_data = factor_data.set_index(["date", "ticker"])

    return factor_data, prices
