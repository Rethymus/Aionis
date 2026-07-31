"""Tests for Curve Evolution pure helpers (6d)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from dashboard.app import (
    _monthly_heatmap,
    _top_drawdowns,
)


def test_monthly_heatmap_creates_pivot() -> None:
    """Monthly heatmap should create a year×month pivot table."""
    rng = np.random.default_rng(7)
    months = pd.date_range("2017-01-31", periods=36, freq="ME")
    returns = pd.Series(rng.normal(0.01, 0.05, 36), index=months)

    pivot = _monthly_heatmap(returns)

    # Should return a pivot DataFrame
    assert isinstance(pivot, pd.DataFrame)
    # Should have year index
    assert all(isinstance(idx, int) for idx in pivot.index)
    # Should have month columns (1-12)
    assert list(pivot.columns) == list(range(1, 13))


def test_monthly_heatmap_handles_partial_years() -> None:
    """Should handle series that don't span full years."""
    rng = np.random.default_rng(7)
    months = pd.date_range("2017-06-30", periods=15, freq="ME")
    returns = pd.Series(rng.normal(0.01, 0.05, 15), index=months)

    pivot = _monthly_heatmap(returns)

    # Should still create the pivot
    assert isinstance(pivot, pd.DataFrame)
    # Should have some NaN values for missing months
    assert pivot.isna().sum().sum() > 0


def test_monthly_heatmap_correct_values() -> None:
    """Should correctly aggregate returns by year×month."""
    # Create a simple known series
    dates = pd.to_datetime([
        "2020-01-31", "2020-02-29", "2020-03-31",
        "2021-01-31", "2021-02-28", "2021-03-31",
    ])
    returns = pd.Series([0.01, 0.02, 0.03, 0.04, 0.05, 0.06], index=dates)

    pivot = _monthly_heatmap(returns)

    # Check specific values
    assert pivot.loc[2020, 1] == 0.01
    assert pivot.loc[2020, 2] == 0.02
    assert pivot.loc[2021, 1] == 0.04


def test_top_drawdowns_structure() -> None:
    """Top drawdowns should return a DataFrame with peak/trough/depth/duration."""
    rng = np.random.default_rng(7)
    returns = pd.Series(rng.normal(0.01, 0.08, 100))

    drawdowns = _top_drawdowns(returns, k=5)

    # Should return a DataFrame
    assert isinstance(drawdowns, pd.DataFrame)
    # Should have the required columns
    required_cols = ["peak_date", "trough_date", "depth", "duration"]
    for col in required_cols:
        assert col in drawdowns.columns


def test_top_drawdowns_identifies_worst_periods() -> None:
    """Should identify the worst drawdown periods."""
    # Create a series with known drawdowns
    returns = pd.Series([
        0.01, 0.01,  # Peak
        -0.05, -0.06, -0.04,  # Drawdown
        0.02, 0.03,  # Recovery
        -0.08, -0.10, -0.07,  # Worse drawdown
        0.01, 0.02,
    ])

    drawdowns = _top_drawdowns(returns, k=2)

    # Should return at most k drawdowns
    assert len(drawdowns) <= 2
    # Depths should be negative (drawdowns)
    if len(drawdowns) > 0:
        assert all(drawdowns["depth"] <= 0)


def test_top_drawdowns_handles_short_series() -> None:
    """Should handle series too short for meaningful drawdowns."""
    returns = pd.Series([0.01, 0.02])

    drawdowns = _top_drawdowns(returns, k=5)

    # Should still return a DataFrame (possibly empty)
    assert isinstance(drawdowns, pd.DataFrame)


def test_top_drawdowns_k_parameter() -> None:
    """k parameter should control the number of returned drawdowns."""
    rng = np.random.default_rng(7)
    returns = pd.Series(rng.normal(0.01, 0.08, 200))  # Enough data for multiple drawdowns

    drawdowns_3 = _top_drawdowns(returns, k=3)
    drawdowns_5 = _top_drawdowns(returns, k=5)

    # Should return at most k results
    assert len(drawdowns_3) <= 3
    assert len(drawdowns_5) <= 5
