"""Tests for Fit Quality pure helpers (6b)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from scipy.stats import linregress

from dashboard.app import (
    _ic_by_regime,
    _r2,
    _regression_line_coords,
)


def test_r2_on_perfect_correlation() -> None:
    """R² should be 1.0 for perfect linear fit."""
    rng = np.random.default_rng(7)
    x = rng.normal(0, 1, 100)
    y = 2 * x + 3  # Perfect linear relationship
    oos = pd.DataFrame({"score": x, "y_fwd_ret": y})

    r2 = _r2(oos)
    assert r2 == pytest.approx(1.0, abs=1e-10)


def test_r2_on_no_correlation() -> None:
    """R² should be near 0 for uncorrelated data."""
    rng = np.random.default_rng(7)
    x = rng.normal(0, 1, 100)
    y = rng.normal(0, 1, 100)  # Independent
    oos = pd.DataFrame({"score": x, "y_fwd_ret": y})

    r2 = _r2(oos)
    assert 0.0 <= r2 < 0.2  # Allow some noise


def test_r2_handles_nan() -> None:
    """R² should drop NaN values."""
    rng = np.random.default_rng(7)
    x = rng.normal(0, 1, 100)
    y = 2 * x + 3
    oos = pd.DataFrame({"score": x, "y_fwd_ret": y})
    oos.loc[0, "y_fwd_ret"] = np.nan

    r2 = _r2(oos)
    assert r2 == pytest.approx(1.0, abs=1e-10)


def test_r2_requires_minimum_data() -> None:
    """R² should return NaN on insufficient data."""
    oos = pd.DataFrame({"score": [1.0], "y_fwd_ret": [2.0]})
    r2 = _r2(oos)
    assert pd.isna(r2)


def test_ic_by_regime_quartiles() -> None:
    """IC-by-regime should create 4 regimes from rolling-σ quartiles."""
    rng = np.random.default_rng(7)
    months = pd.date_range("2017-01-31", periods=125, freq="ME")
    ic = pd.Series(rng.normal(0.01, 0.05, 125), index=months, name="ic")

    regimes = _ic_by_regime(ic, n_regimes=4)

    # Should return a DataFrame with regime labels
    assert isinstance(regimes, pd.DataFrame)
    assert "regime" in regimes.columns
    assert "ic" in regimes.columns
    # Length may be less due to rolling window warmup and NaN drop
    assert len(regimes) <= len(ic)
    assert len(regimes) > 0


def test_ic_by_regime_has_four_regimes() -> None:
    """Should create exactly 4 regimes (quartiles)."""
    rng = np.random.default_rng(7)
    months = pd.date_range("2017-01-31", periods=125, freq="ME")
    ic = pd.Series(rng.normal(0.01, 0.05, 125), index=months, name="ic")

    regimes = _ic_by_regime(ic, n_regimes=4)

    unique_regimes = regimes["regime"].dropna().unique()
    assert len(unique_regimes) == 4
    # Regimes should be labeled 0, 1, 2, 3
    assert set(unique_regimes).issubset({0, 1, 2, 3})


def test_regression_line_coords() -> None:
    """Regression line coords should match scipy linregress."""
    rng = np.random.default_rng(7)
    x = rng.normal(0, 1, 100)
    y = 2 * x + 3
    oos = pd.DataFrame({"score": x, "y_fwd_ret": y})

    x_line, y_line, r2_value = _regression_line_coords(oos)

    # Check against scipy
    result = linregress(oos["score"].dropna(), oos["y_fwd_ret"].dropna())
    assert r2_value == pytest.approx(result.rvalue ** 2, abs=1e-10)
    assert len(x_line) == len(y_line)
    assert len(x_line) == 2  # Should have start and end points


def test_regression_line_handles_nan() -> None:
    """Regression line should handle NaN values."""
    rng = np.random.default_rng(7)
    x = rng.normal(0, 1, 100)
    y = 2 * x + 3
    oos = pd.DataFrame({"score": x, "y_fwd_ret": y})
    oos.loc[0, "score"] = np.nan

    x_line, y_line, r2_value = _regression_line_coords(oos)

    # Should still work
    assert len(x_line) == 2
    assert not np.isnan(r2_value)
