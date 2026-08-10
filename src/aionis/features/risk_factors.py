"""Cross-sectional risk factors for the terminal's risk theme.

True risk factors (downside risk, tail risk, crash sensitivity), distinct from
the price theme's volatility/beta. Computes downside beta, idiosyncratic volatility,
and tail/downside risk metrics from daily returns.

Pure function, deterministic (no randomness), no network calls.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import structlog

log = structlog.get_logger()

# Constants
_EPS = 1e-9
_DAYS_PER_MONTH = 21
_DAYS_PER_YEAR = 252
_DOWNSIDE_BETA_WINDOW = 252  # ~1 year for downside beta
_IDIO_VOL_WINDOW = 63  # ~3 months for idiosyncratic vol
_TAIL_RISK_WINDOW = 63  # ~3 months for tail risk metrics


def _compute_returns_from_panel(panel: pd.DataFrame) -> pd.DataFrame:
    """Compute daily returns from the panel's close prices.

    Args:
        panel: Panel with columns [date, ticker, close, ...].

    Returns:
        DataFrame with columns [date, ticker, return], sorted by date then ticker.
    """
    # Pivot to wide format for efficient pct_change
    prices_wide = panel.pivot(index="date", columns="ticker", values="close")
    returns_wide = prices_wide.pct_change()

    # Stack back to long format
    returns_long = (
        returns_wide.stack()
        .reset_index()
        .rename(columns={0: "return", "level_0": "date", "level_1": "ticker"})
    )
    returns_long = returns_long.sort_values(["date", "ticker"]).reset_index(drop=True)

    return returns_long


def _compute_market_returns(returns_wide: pd.DataFrame) -> pd.Series:
    """Compute equal-weighted market returns from all stocks.

    Args:
        returns_wide: Wide-format returns DataFrame [dates x tickers].

    Returns:
        Series of market returns indexed by date.
    """
    # Equal-weighted market return (mean across all stocks with non-NaN returns)
    return returns_wide.mean(axis=1)


def downside_beta(
    returns_wide: pd.DataFrame,
    market_returns: pd.Series,
    window: int = _DOWNSIDE_BETA_WINDOW,
) -> pd.DataFrame:
    """Downside beta: covariance with market on DOWN days only.

    Classic "crash sensitivity" factor. Measures how much a stock tends to move
    when the market is falling. High downside beta = amplifies market crashes.

    Args:
        returns_wide: Wide-format returns [dates x tickers].
        market_returns: Market return series (equal-weighted portfolio).
        window: Rolling window in trading days, default 252 (~1 year).

    Returns:
        DataFrame of downside betas [dates x tickers]. NaN where insufficient
        down-day observations.
    """
    min_periods = max(10, window // 4)  # Require at least 10 down days

    # Identify down market days
    down_days = market_returns < 0
    down_days_clean = down_days.reindex(returns_wide.index).fillna(False)

    downside_betas = pd.DataFrame(
        index=returns_wide.index, columns=returns_wide.columns, dtype=float
    )

    # Market variance on DOWN days only (rolling)
    market_down_returns = market_returns.copy()
    market_down_returns[~down_days_clean] = np.nan
    market_var_down = (
        market_down_returns.rolling(window=window, min_periods=min_periods).var()
    )

    # Compute downside beta for each stock
    for ticker in returns_wide.columns:
        stock_returns = returns_wide[ticker]
        stock_down_returns = stock_returns.copy()
        stock_down_returns[~down_days_clean] = np.nan

        # Covariance on down days
        cov_down = (
            stock_down_returns.rolling(window=window, min_periods=min_periods).cov(
                market_down_returns
            )
        )

        # Downside beta = cov_down / var_down
        downside_betas[ticker] = np.where(
            market_var_down > _EPS, cov_down / market_var_down, np.nan
        )

    return downside_betas


def idiosyncratic_volatility(
    returns_wide: pd.DataFrame,
    market_returns: pd.Series,
    window: int = _IDIO_VOL_WINDOW,
) -> pd.DataFrame:
    """Idiosyncratic volatility: residual std after market-beta regression.

    Stock-specific risk NOT explained by market exposure. High idio vol =
    high firm-specific uncertainty/noise.

    Computed via rolling regression: r_t = alpha + beta * r_m_t + epsilon_t
    Idio vol = std(epsilon_t)

    Args:
        returns_wide: Wide-format returns [dates x tickers].
        market_returns: Market return series.
        window: Rolling window in trading days, default 63 (~3 months).

    Returns:
        DataFrame of idiosyncratic volatilities [dates x tickers].
    """
    min_periods = max(10, window // 2)

    idio_vols = pd.DataFrame(
        index=returns_wide.index, columns=returns_wide.columns, dtype=float
    )

    # Pre-compute rolling market variance and covariances for efficiency
    market_var = market_returns.rolling(window=window, min_periods=min_periods).var()

    for ticker in returns_wide.columns:
        stock_returns = returns_wide[ticker]

        # Rolling beta (same as regular beta computation)
        cov_stock_market = (
            stock_returns.rolling(window=window, min_periods=min_periods).cov(
                market_returns
            )
        )
        beta = np.where(market_var > _EPS, cov_stock_market / market_var, np.nan)

        # Market component = beta * market_return
        market_component = beta * market_returns

        # Residual = stock_return - market_component
        residual = stock_returns - market_component

        # Idiosyncratic volatility = rolling std of residuals
        idio_vols[ticker] = residual.rolling(
            window=window, min_periods=min_periods
        ).std()

    return idio_vols


def tail_risk_skewness(
    returns_wide: pd.DataFrame,
    window: int = _TAIL_RISK_WINDOW,
) -> pd.DataFrame:
    """Tail risk via return skewness (negative = fat left tail).

    Negative skewness means the distribution has a fat left tail - more extreme
    negative returns than expected under a normal distribution. This is a classic
    tail/crash risk measure.

    Args:
        returns_wide: Wide-format returns [dates x tickers].
        window: Rolling window in trading days, default 63 (~3 months).

    Returns:
        DataFrame of skewness values [dates x tickers]. Negative values indicate
        left-tail risk.
    """
    min_periods = max(10, window // 2)

    skewness = returns_wide.rolling(
        window=window, min_periods=min_periods
    ).skew()

    return skewness


def worst_day_drawdown(
    returns_wide: pd.DataFrame,
    window: int = _TAIL_RISK_WINDOW,
) -> pd.DataFrame:
    """Worst single-day drawdown over the window (tail risk metric).

    Maximum loss from peak to trough within a single day. Captures extreme
    crash risk that VaR might miss.

    Args:
        returns_wide: Wide-format returns [dates x tickers].
        window: Rolling window in trading days, default 63 (~3 months).

    Returns:
        DataFrame of worst daily drawdowns [dates x tickers]. Values are
        negative (e.g., -0.15 means -15% worst day).
    """
    min_periods = max(5, window // 4)

    # Worst daily return = minimum return over the window
    worst_return = (
        returns_wide.rolling(window=window, min_periods=min_periods).min()
    )

    return worst_return


def compute_risk_factors(
    panel: pd.DataFrame,
    downside_beta_window: int = _DOWNSIDE_BETA_WINDOW,
    idio_vol_window: int = _IDIO_VOL_WINDOW,
    tail_risk_window: int = _TAIL_RISK_WINDOW,
) -> pd.DataFrame:
    """Compute cross-sectional risk factors from the panel.

    Returns a panel keyed by (date, ticker) with new risk columns:
    - downside_beta: crash sensitivity (covariance with market on down days)
    - idiosyncratic_volatility: stock-specific risk (residual vol)
    - return_skewness: tail risk (negative = fat left tail)
    - worst_day_drawdown: worst single-day loss in the window

    Args:
        panel: Panel with columns [date, ticker, close, ...].
        downside_beta_window: Window for downside beta, default 252.
        idio_vol_window: Window for idiosyncratic vol, default 63.
        tail_risk_window: Window for tail risk metrics, default 63.

    Returns:
        DataFrame with columns [date, ticker, downside_beta, idiosyncratic_volatility,
        return_skewness, worst_day_drawdown]. Mergeable into the original panel.
    """
    # Compute returns from close prices
    returns_long = _compute_returns_from_panel(panel)

    # Pivot to wide for vectorized computations
    returns_wide = returns_long.pivot(index="date", columns="ticker", values="return")

    # Compute market returns (equal-weighted)
    market_returns = _compute_market_returns(returns_wide)

    # Compute risk factors
    downside_betas = downside_beta(
        returns_wide, market_returns, window=downside_beta_window
    )
    idio_vols = idiosyncratic_volatility(
        returns_wide, market_returns, window=idio_vol_window
    )
    skewness = tail_risk_skewness(returns_wide, window=tail_risk_window)
    worst_drawdown = worst_day_drawdown(returns_wide, window=tail_risk_window)

    # Stack to long format and merge
    result = pd.DataFrame()
    for factor_name, factor_wide in [
        ("downside_beta", downside_betas),
        ("idiosyncratic_volatility", idio_vols),
        ("return_skewness", skewness),
        ("worst_day_drawdown", worst_drawdown),
    ]:
        factor_long = (
            factor_wide.stack()
            .reset_index()
            .rename(columns={0: factor_name, "level_0": "date", "level_1": "ticker"})
        )
        if result.empty:
            result = factor_long
        else:
            result = result.merge(
                factor_long, on=["date", "ticker"], how="outer"
            )

    return result.sort_values(["date", "ticker"]).reset_index(drop=True)


# Pre-specified factor column list (for config freeze)
TRACK_B_RISK_FACTOR_COLS: list[str] = [
    "downside_beta",
    "idiosyncratic_volatility",
    "return_skewness",
    "worst_day_drawdown",
]
"""Track B cross-sectional risk factor columns.

Pre-specified list of risk factors for config freeze. 4 factors total.
Distinct from price theme volatility/beta — focuses on downside/tail risk.
"""
