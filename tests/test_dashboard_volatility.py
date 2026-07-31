"""Tests for Volatility pure helpers (6c)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from dashboard.app import (
    _calmar,
    _downside_deviation,
    _return_distribution,
    _sharpe,
    _vol_of_vol,
)


def test_sharpe_on_known_returns() -> None:
    """Annualized Sharpe on a known returns series."""
    rng = np.random.default_rng(7)
    months = pd.date_range("2017-01-31", periods=60, freq="ME")
    returns = pd.Series(rng.normal(0.01, 0.05, 60), index=months)

    sharpe = _sharpe(returns)

    # Should be finite (can be negative)
    assert isinstance(sharpe, float)
    assert np.isfinite(sharpe)
    # Rough sanity check (should be around -1.0 to 2.0 for these params)
    assert -1.0 < sharpe < 2.0


def test_sharpe_handles_short_series() -> None:
    """Sharpe should return NaN on insufficient data."""
    returns = pd.Series([0.01])  # Only 1 observation
    sharpe = _sharpe(returns)
    assert pd.isna(sharpe)


def test_calmar_on_drawdown_series() -> None:
    """Calmar = cumulative_return / max_drawdown."""
    rng = np.random.default_rng(7)
    months = pd.date_range("2017-01-31", periods=60, freq="ME")
    # Create a series with drawdowns
    returns = pd.Series(rng.normal(0.01, 0.08, 60), index=months)
    returns.iloc[20:30] = -0.05  # Add a drawdown period

    calmar = _calmar(returns)

    # Should be finite
    assert isinstance(calmar, float)
    assert np.isfinite(calmar) or pd.isna(calmar)


def test_calmar_zero_drawdown() -> None:
    """Calmar should handle zero or negative drawdown."""
    # Monotonically increasing series -> no drawdown
    returns = pd.Series([0.01] * 10)
    calmar = _calmar(returns)
    # Should be infinite or very large when no drawdown
    assert np.isinf(calmar) or calmar > 1e6


def test_downside_deviation() -> None:
    """Downside deviation = std of negative returns only."""
    returns = pd.Series([0.01, -0.02, 0.03, -0.01, -0.05, 0.02])

    dd = _downside_deviation(returns)

    # Should be positive
    assert isinstance(dd, float)
    assert dd > 0
    # Should be less than full std
    full_std = returns.std()
    assert dd < full_std


def test_downside_deviation_all_positive() -> None:
    """Downside deviation should be zero when all returns are positive."""
    returns = pd.Series([0.01, 0.02, 0.03, 0.04])
    dd = _downside_deviation(returns)
    assert dd == 0.0


def test_vol_of_vol() -> None:
    """Vol-of-vol = std of rolling-σ."""
    rng = np.random.default_rng(7)
    months = pd.date_range("2017-01-31", periods=60, freq="ME")
    returns = pd.Series(rng.normal(0.01, 0.05, 60), index=months)

    vov = _vol_of_vol(returns)

    # Should be positive and finite
    assert isinstance(vov, float)
    assert vov > 0
    assert np.isfinite(vov)


def test_return_distribution_shape() -> None:
    """Return distribution histogram figure should have correct shape."""
    rng = np.random.default_rng(7)
    returns = pd.Series(rng.normal(0.01, 0.05, 100))

    fig = _return_distribution(returns)

    # Should return a plotly Figure
    assert hasattr(fig, "data")
    assert len(fig.data) >= 2  # At least histogram + normal overlay


def test_return_distribution_with_normal_overlay() -> None:
    """Should include a normal PDF overlay."""
    rng = np.random.default_rng(7)
    returns = pd.Series(rng.normal(0.01, 0.05, 100))

    fig = _return_distribution(returns)

    # Check for histogram trace
    has_histogram = any(trace.type == "histogram" for trace in fig.data)
    assert has_histogram, "Should have a histogram trace"

    # Check for scatter/line trace (normal overlay)
    has_overlay = any(trace.type in ("scatter", "scattergl") for trace in fig.data)
    assert has_overlay, "Should have a normal overlay trace"


def test_return_distribution_handles_short_series() -> None:
    """Should handle short series gracefully."""
    returns = pd.Series([0.01, 0.02])
    fig = _return_distribution(returns)
    # Should still return a figure
    assert hasattr(fig, "data")
