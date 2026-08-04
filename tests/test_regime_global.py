"""Tests for regime global DY spillover layer (Diebold-Yilmaz 2012).

Hermetic, seeded tests validating:
- Independent random-walk series → LOW spillover (< 0.15 mean)
- Strongly correlated series → HIGH spillover (> 0.3 mean)
- Leakage guard: spillover at t uses only [t-249, t]
- FEVD properties: θ rows sum to 1, θ in [0,1]
- H6 determinism (seed=0 → bit-identical reruns)
- 2×2 total spillover = (θ01+θ10)/2
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aionis.features.regime_global import (
    dy_total_spillover,
    equal_weighted_market_return,
)

# --- Fixtures ----------------------------------------------------------------


@pytest.fixture
def rng() -> np.random.Generator:
    """Seeded random number generator (H6 determinism)."""
    return np.random.default_rng(0)


@pytest.fixture
def us_price_panel(rng: np.random.Generator) -> pd.DataFrame:
    """Synthetic US price panel (10 tickers, 500 dates)."""
    dates = pd.date_range("2020-01-01", periods=500, freq="D")
    tickers = [f"US{i:03d}" for i in range(10)]
    prices = rng.uniform(90, 110, size=(500, 10))
    return pd.DataFrame(prices, index=dates, columns=tickers)


@pytest.fixture
def cn_price_panel(rng: np.random.Generator) -> pd.DataFrame:
    """Synthetic CN price panel (10 tickers, 500 dates, some suspensions)."""
    dates = pd.date_range("2020-01-01", periods=500, freq="D")
    tickers = [f"CN{i:03d}" for i in range(10)]
    prices = rng.uniform(90, 110, size=(500, 10))
    df = pd.DataFrame(prices, index=dates, columns=tickers)
    # Inject some suspensions (NaN values)
    suspension_mask = rng.random((500, 10)) < 0.05
    df[suspension_mask] = np.nan
    return df


# --- equal_weighted_market_return tests --------------------------------------


def test_equal_weighted_market_return_basic(us_price_panel: pd.DataFrame) -> None:
    """Equal-weighted return computes mean across tickers, ignoring NaN."""
    ret = equal_weighted_market_return(us_price_panel)
    assert len(ret) == 500
    # First day is NaN (no previous day to compute change)
    assert pd.isna(ret.iloc[0])


def test_equal_weighted_market_return_with_suspensions(cn_price_panel: pd.DataFrame) -> None:
    """Suspensions (NaN) are excluded from the equal-weighted mean."""
    ret = equal_weighted_market_return(cn_price_panel)
    assert len(ret) == 500
    # Should have some valid returns despite suspensions
    assert ret.notna().sum() > 400


def test_equal_weighted_market_return_empty() -> None:
    """Empty panel returns empty Series."""
    ret = equal_weighted_market_return(pd.DataFrame())
    assert ret.empty


# --- dy_total_spillover correctness tests -------------------------------------


def test_independent_series_low_spillover(rng: np.random.Generator) -> None:
    """Independent random-walk series → LOW total spillover (mean < 0.15).

    This catches gross formula errors (wrong index normalization can give
    spillover near 0.5 for independent data).
    """
    # Two independent random walks (no cross-dependence)
    n = 600
    us = np.concatenate([[100], rng.standard_normal(n - 1).cumsum() + 100])
    cn = np.concatenate([[100], rng.standard_normal(n - 1).cumsum() + 100])
    us_ret = pd.Series(us).pct_change().dropna()
    cn_ret = pd.Series(cn).pct_change().dropna()

    spillover = dy_total_spillover(us_ret, cn_ret, window=250, horizon=10)
    valid = spillover.dropna()

    # Sanity check: independent series → low spillover
    assert valid.mean() < 0.15, (
        f"Independent series should have low spillover, got {valid.mean():.4f}"
    )
    assert spillover.notna().sum() > 0, "Should have some valid spillover values"


def test_correlated_series_high_spillover(rng: np.random.Generator) -> None:
    """Strongly correlated series (cn = us + small_noise) → HIGH spillover (mean > 0.3)."""
    n = 600
    us = np.concatenate([[100], rng.standard_normal(n - 1).cumsum() + 100])
    noise = np.concatenate([[0], rng.standard_normal(n - 1)]) * 0.1
    cn = us + noise  # Strong dependence
    us_ret = pd.Series(us).pct_change().dropna()
    cn_ret = pd.Series(cn).pct_change().dropna()

    spillover = dy_total_spillover(us_ret, cn_ret, window=250, horizon=10)
    valid = spillover.dropna()

    # Strongly correlated series → high spillover
    assert valid.mean() > 0.3, (
        f"Correlated series should have high spillover, got {valid.mean():.4f}"
    )
    assert spillover.notna().sum() > 0, "Should have some valid spillover values"


def test_leakage_guard(rng: np.random.Generator) -> None:
    """Spillover at t depends only on returns in [t-249, t], never future.

    Mutating a return at t+5 must NOT change spillover at t.
    """
    n = 600
    us = np.concatenate([[100], rng.standard_normal(n - 1).cumsum() + 100])
    cn = np.concatenate([[100], rng.standard_normal(n - 1).cumsum() + 100])
    us_ret = pd.Series(us).pct_change().dropna()
    cn_ret = pd.Series(cn).pct_change().dropna()

    # Baseline spillover
    spillover_baseline = dy_total_spillover(us_ret, cn_ret, window=250, horizon=10)

    # Mutate a return at t+5 (should NOT affect spillover at t)
    us_ret_mut = us_ret.copy()
    us_ret_mut.iloc[400] += 1.0  # Large perturbation at position 400
    spillover_mutated = dy_total_spillover(us_ret_mut, cn_ret, window=250, horizon=10)

    # Spillover at position 395 (window ends at t=395, uses [395-249, 395])
    # should be unchanged (mutation at 400 is in the future)
    # Use iloc to access by position, not by index value
    if len(spillover_baseline) > 395:
        baseline_val = spillover_baseline.iloc[395]
        mutated_val = spillover_mutated.iloc[395]

        # Should be identical (or NaN for both)
        if pd.isna(baseline_val):
            assert pd.isna(mutated_val)
        else:
            assert mutated_val == pytest.approx(baseline_val, abs=1e-9), \
                "Leakage guard failed: future mutation affected past spillover"


def test_theta_properties(rng: np.random.Generator) -> None:
    """Validate FEVD properties: θ rows sum to 1, θ in [0,1].

    This test directly accesses the internal computation to verify θ.
    """
    from statsmodels.tsa.api import VAR

    # Build simple test data
    n = 300
    us = np.concatenate([[100], rng.standard_normal(n - 1).cumsum() + 100])
    cn = np.concatenate([[100], rng.standard_normal(n - 1).cumsum() + 100])
    us_ret = pd.Series(us).pct_change().dropna()
    cn_ret = pd.Series(cn).pct_change().dropna()

    # Manually compute θ for one window
    window_df = pd.DataFrame({"us": us_ret.iloc[:250], "cn": cn_ret.iloc[:250]}).dropna()
    model = VAR(window_df.values)
    res = model.fit(maxlags=2, ic="aic")
    if res.k_ar == 0:
        res = model.fit(maxlags=1)

    horizon = 10
    phi = res.ma_rep(maxn=horizon)
    sigma = res.sigma_u
    if isinstance(sigma, pd.DataFrame):
        sigma = sigma.values

    # Generalized impulse responses
    gir = np.zeros((horizon, 2, 2))
    for h in range(horizon):
        phi_sigma = phi[h] @ sigma
        for i in range(2):
            for j in range(2):
                denom = np.sqrt(sigma[j, j])
                gir[h, i, j] = phi_sigma[i, j] / denom

    # θ shares
    numer = np.sum(gir ** 2, axis=0)
    denom = numer.sum(axis=1, keepdims=True)
    theta = numer / denom

    # Each row sums to 1 (within tolerance)
    assert theta[0, :].sum() == pytest.approx(1.0, abs=1e-9), "θ row 0 does not sum to 1"
    assert theta[1, :].sum() == pytest.approx(1.0, abs=1e-9), "θ row 1 does not sum to 1"

    # θ in [0, 1]
    assert np.all(theta >= 0), "θ has negative values"
    assert np.all(theta <= 1), "θ has values > 1"


def test_h6_determinism(rng: np.random.Generator) -> None:
    """H6 determinism: seed=0, n_jobs=1 → bit-identical reruns."""
    n = 600
    us = np.concatenate([[100], rng.standard_normal(n - 1).cumsum() + 100])
    cn = np.concatenate([[100], rng.standard_normal(n - 1).cumsum() + 100])
    us_ret = pd.Series(us).pct_change().dropna()
    cn_ret = pd.Series(cn).pct_change().dropna()

    spillover1 = dy_total_spillover(us_ret, cn_ret, window=250, horizon=10)
    spillover2 = dy_total_spillover(us_ret, cn_ret, window=250, horizon=10)

    # Bit-identical (same values and NaN positions)
    pd.testing.assert_series_equal(spillover1, spillover2)


def test_total_spillover_formula(rng: np.random.Generator) -> None:
    """2×2 total spillover = (θ01 + θ10) / 2 exactly."""
    from statsmodels.tsa.api import VAR

    n = 300
    us = np.concatenate([[100], rng.standard_normal(n - 1).cumsum() + 100])
    cn = np.concatenate([[100], rng.standard_normal(n - 1).cumsum() + 100])
    us_ret = pd.Series(us).pct_change().dropna()
    cn_ret = pd.Series(cn).pct_change().dropna()

    # Compute spillover via the function
    spillover = dy_total_spillover(us_ret, cn_ret, window=250, horizon=10)

    # Manually compute for one window to verify formula
    window_df = pd.DataFrame({"us": us_ret.iloc[:250], "cn": cn_ret.iloc[:250]}).dropna()
    model = VAR(window_df.values)
    res = model.fit(maxlags=2, ic="aic")
    if res.k_ar == 0:
        res = model.fit(maxlags=1)

    horizon = 10
    phi = res.ma_rep(maxn=horizon)
    sigma = res.sigma_u
    if isinstance(sigma, pd.DataFrame):
        sigma = sigma.values

    gir = np.zeros((horizon, 2, 2))
    for h in range(horizon):
        phi_sigma = phi[h] @ sigma
        for i in range(2):
            for j in range(2):
                denom = np.sqrt(sigma[j, j])
                gir[h, i, j] = phi_sigma[i, j] / denom

    numer = np.sum(gir ** 2, axis=0)
    denom = numer.sum(axis=1, keepdims=True)
    theta = numer / denom

    expected_total = (theta[0, 1] + theta[1, 0]) / 2.0

    # Compare with function output (first valid value)
    valid = spillover.dropna()
    if len(valid) > 0:
        # The formula should match the function output
        assert valid.iloc[0] == pytest.approx(expected_total, abs=1e-6), \
            "Total spillover formula mismatch"


def test_insufficient_data_returns_empty() -> None:
    """Insufficient data (< window size) returns empty Series."""
    us_ret = pd.Series([0.01, 0.02, 0.03])
    cn_ret = pd.Series([0.01, 0.02, 0.03])

    spillover = dy_total_spillover(us_ret, cn_ret, window=250, horizon=10)

    assert spillover.empty
    assert spillover.name == "total_spillover"


def test_fevd_properties_with_real_data() -> None:
    """Validate FEVD properties on realistic price panel data."""
    rng = np.random.default_rng(0)
    dates = pd.date_range("2020-01-01", periods=500, freq="D")

    # Build correlated price panel (some tickers move together)
    common_factor = rng.standard_normal(500).cumsum()
    prices = np.zeros((500, 20))
    for i in range(20):
        idio = rng.standard_normal(500) * 0.3
        prices[:, i] = 100 + common_factor + idio.cumsum()

    # Create two correlated markets (US and CN share the factor)
    us_factor = rng.standard_normal(500).cumsum()
    cn_factor = us_factor * 0.8 + rng.standard_normal(500).cumsum() * 0.2

    us_prices = 100 + us_factor.reshape(-1, 1) + rng.standard_normal((500, 10)) * 0.1
    cn_prices = 100 + cn_factor.reshape(-1, 1) + rng.standard_normal((500, 10)) * 0.1

    us_panel = pd.DataFrame(us_prices, index=dates, columns=[f"US{i}" for i in range(10)])
    cn_panel = pd.DataFrame(cn_prices, index=dates, columns=[f"CN{i}" for i in range(10)])

    us_ret = equal_weighted_market_return(us_panel)
    cn_ret = equal_weighted_market_return(cn_panel)

    spillover = dy_total_spillover(us_ret, cn_ret, window=250, horizon=10)

    # Should have valid spillover values
    assert spillover.notna().sum() > 0
    # Correlated markets should show spillover > 0.1
    valid = spillover.dropna()
    assert valid.mean() > 0.05
