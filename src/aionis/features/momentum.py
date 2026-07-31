"""
Momentum/reversal feature kernel - pure functions on monthly price panels.

Input contract: per-ticker, per-month-END total-return adjusted close,
already PIT-adjusted. Sourcing/corporate actions are upstream concerns.

Frozen formulas at prediction month t (1-indexed):
- momentum_12_1 = close[t-1] / close[t-12] - 1
- reversal_1m = -(close[t] / close[t-1] - 1)
- vol_adj_mom = momentum_12_1 / std(r[t-11], ..., r[t-1], ddof=1)

For ANY ticker: if any required close is missing, non-positive, or non-finite
→ return NaN. If std <= 0 → return NaN.

Do NOT fill months, winsorize, rank, or future-shift.
"""

from typing import Literal

import numpy as np
import pandas as pd


def _validate_price_series(prices: pd.Series, min_length: int) -> bool:
    """Check if price series meets minimum length and all values are positive finite."""
    if len(prices) < min_length:
        return False
    if not np.all(np.isfinite(prices.values)):
        return False
    if not np.all(prices.values > 0):
        return False
    return True


def momentum_12_1(prices: pd.Series) -> float:
    """
    12-1 momentum: close[t-1] / close[t-12] - 1.

    Requires exactly 12 consecutive month-end closes (t-12 through t-1).
    All closes must be positive and finite. Returns NaN if any requirement fails.

    Args:
        prices: Ordered Series of month-end closing prices (ascending by date).

    Returns:
        12-1 momentum value or NaN if requirements not met.
    """
    MIN_LENGTH = 12
    if not _validate_price_series(prices, MIN_LENGTH):
        return np.nan

    # Use the LAST 12 prices for momentum calculation
    # If we have exactly 12: use all of them
    # If we have more than 12 (e.g., vol_adj_mom case): use last 12
    prices_12 = prices.iloc[-12:]

    # prices_12[-12] is t-12, prices_12[-1] is t-1
    close_t_minus_12 = prices_12.iloc[0]
    close_t_minus_1 = prices_12.iloc[-1]

    # Formula: close[t-1] / close[t-12] - 1
    return close_t_minus_1 / close_t_minus_12 - 1.0


def reversal_1m(prices: pd.Series) -> float:
    """
    1-month reversal: -(close[t] / close[t-1] - 1).

    Requires exactly 2 consecutive month-end closes (t-1 and t).
    All closes must be positive and finite. Returns NaN if any requirement fails.

    Args:
        prices: Ordered Series of month-end closing prices (ascending by date).

    Returns:
        1-month reversal value or NaN if requirements not met.
    """
    MIN_LENGTH = 2
    if not _validate_price_series(prices, MIN_LENGTH):
        return np.nan

    # Get last 2 prices: prices[-2] is t-1, prices[-1] is t
    close_t_minus_1 = prices.iloc[-2]
    close_t = prices.iloc[-1]

    # Formula: -(close[t] / close[t-1] - 1)
    return -(close_t / close_t_minus_1 - 1.0)


def vol_adj_mom(prices: pd.Series) -> float:
    """
    Volatility-adjusted momentum: momentum_12_1 / std(returns).

    Returns r[m] = close[m] / close[m-1] - 1 for m in [t-11, ..., t-1].
    Exactly 11 monthly returns; std with ddof=1.

    Requires 13 closes (for 12-month momentum and 11 returns).
    All closes must be positive and finite. Returns NaN if:
    - Any price requirement fails
    - Std dev <= 0 (zero or negative volatility)

    Args:
        prices: Ordered Series of month-end closing prices (ascending by date).

    Returns:
        Volatility-adjusted momentum value or NaN if requirements not met.
    """
    MIN_LENGTH = 13  # Need 12 for momentum_12_1 + 1 extra for first return
    if not _validate_price_series(prices, MIN_LENGTH):
        return np.nan

    # For vol_adj_mom with 13+ prices:
    # - momentum_12_1 uses LAST 12 prices (formation window: t-12 through t-1)
    # - returns use consecutive pairs from that same formation window
    prices_12 = prices.iloc[-12:]  # Last 12 prices: indices -12 through -1 (t-12 through t-1)
    assert len(prices_12) == 12, f"Expected 12 prices, got {len(prices_12)}"

    # Compute momentum_12_1 on the 12-price window
    close_t_minus_12 = prices_12.iloc[0]   # Index 0 of original (t-12)
    close_t_minus_1 = prices_12.iloc[-1]   # Index 11 of original (t-1)
    mom = close_t_minus_1 / close_t_minus_12 - 1.0

    # Compute 11 returns from consecutive pairs in the 12-price window
    returns = []
    for i in range(1, len(prices_12)):  # 1 to 11 gives 11 returns
        ret = prices_12.iloc[i] / prices_12.iloc[i-1] - 1.0
        returns.append(ret)

    # Verify we have exactly 11 returns
    assert len(returns) == 11, f"Expected 11 returns, got {len(returns)}"

    # Compute std with ddof=1 (sample standard deviation)
    std_dev = np.std(returns, ddof=1)

    # Zero or negative volatility → NaN
    if std_dev <= 0:
        return np.nan

    # Formula: momentum_12_1 / std(returns)
    return mom / std_dev


def compute_momentum_features(
    prices: pd.Series,
    features: list[Literal["momentum_12_1", "reversal_1m", "vol_adj_mom"]] | None = None,
) -> dict[str, float]:
    """
    Compute all or subset of momentum features for a single ticker.

    Args:
        prices: Ordered Series of month-end closing prices.
        features: List of feature names to compute. None = all features.

    Returns:
        Dict mapping feature names to computed values (NaN if requirements not met).
    """
    if features is None:
        features = ["momentum_12_1", "reversal_1m", "vol_adj_mom"]

    result = {}
    for feature in features:
        if feature == "momentum_12_1":
            result[feature] = momentum_12_1(prices)
        elif feature == "reversal_1m":
            result[feature] = reversal_1m(prices)
        elif feature == "vol_adj_mom":
            result[feature] = vol_adj_mom(prices)
        else:
            raise ValueError(f"Unknown feature: {feature}")

    return result
