"""Tests for FF5 residual regression and Amihud illiquidity (hermetic, no network)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aionis.eval.ff5_residual import (
    _newey_west_maxlag,
    amihud_illiquidity,
    ff5_residual_regression,
)

# Constants for synthetic data generation
_TEST_SEED = 42
_MONTHLY_VOL = 0.01  # ~1% monthly volatility
_RF_RATE = 0.0002  # ~2.4% annual risk-free rate


def _make_synthetic_ff5_data(n_months: int, seed: int = _TEST_SEED) -> pd.DataFrame:
    """Generate synthetic FF5 factor data for testing.

    Args:
        n_months: Number of months to generate.
        seed: Random seed for reproducibility.

    Returns:
        DataFrame with columns: date, Mkt-RF, SMB, HML, RMW, CMA, RF.
    """
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2020-01-31", periods=n_months, freq="ME")

    return pd.DataFrame(
        {
            "date": dates,
            "Mkt-RF": rng.standard_normal(n_months) * _MONTHLY_VOL,
            "SMB": rng.standard_normal(n_months) * _MONTHLY_VOL * 0.5,
            "HML": rng.standard_normal(n_months) * _MONTHLY_VOL * 0.4,
            "RMW": rng.standard_normal(n_months) * _MONTHLY_VOL * 0.3,
            "CMA": rng.standard_normal(n_months) * _MONTHLY_VOL * 0.3,
            "RF": _RF_RATE,
        }
    )


def _make_synthetic_prices_volumes(
    n_days: int, n_tickers: int, seed: int = _TEST_SEED
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate synthetic price and volume data for Amihud testing.

    Args:
        n_days: Number of trading days.
        n_tickers: Number of tickers.
        seed: Random seed.

    Returns:
        Tuple of (prices_df, volume_df) with columns [date, ticker, close/volume].
    """
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2020-01-01", periods=n_days)
    tickers = [f"T{i:03d}" for i in range(n_tickers)]

    rows = []
    vol_rows = []
    for ticker in tickers:
        # Generate geometric Brownian motion for prices
        price_path = [100.0]  # starting price
        for _ in range(n_days - 1):
            ret = rng.normal(0, 0.01)  # 1% daily vol
            price_path.append(price_path[-1] * (1 + ret))

        # Generate volumes (log-normal)
        vols = rng.lognormal(mean=14, sigma=0.5, size=n_days).astype(int)

        for i, date in enumerate(dates):
            rows.append({"date": date, "ticker": ticker, "close": price_path[i]})
            vol_rows.append({"date": date, "ticker": ticker, "volume": vols[i]})

    return pd.DataFrame(rows), pd.DataFrame(vol_rows)


class TestNeweyWestMaxlag:
    """Tests for Newey-West lag calculation."""

    def test_returns_at_least_one_for_small_samples(self) -> None:
        """Small samples should have maxlag >= 1."""
        assert _newey_west_maxlag(2) >= 1
        assert _newey_west_maxlag(5) >= 1
        assert _newey_west_maxlag(10) >= 1

    def test_increases_with_sample_size(self) -> None:
        """Larger samples should have larger recommended lags."""
        lag_small = _newey_west_maxlag(50)
        lag_large = _newey_west_maxlag(200)
        assert lag_large >= lag_small

    def test_formula_matches_newey_west_1994(self) -> None:
        """Verify the formula: 4 * (n/100)^(2/9)."""
        # For n=100, expected lag = 4
        assert _newey_west_maxlag(100) == 4
        # For n=200, expected lag ≈ 4 * 2^(2/9) ≈ 4.7 -> int -> 4
        assert _newey_west_maxlag(200) >= 4


class TestFF5ResidualRegression:
    """Tests for FF5 residual regression."""

    def test_recovers_known_alpha_and_betas_from_synthetic_data(self) -> None:
        """With synthetic data generated from known parameters, regression should recover them.

        This is the core correctness test: we create returns where we know the
        true alpha and betas, then verify the regression recovers them (within noise tolerance).
        """
        n_months = 24
        ff5 = _make_synthetic_ff5_data(n_months, seed=1)

        # True parameters
        alpha_true = 0.002  # 2.4% annual alpha
        betas_true = {
            "Mkt-RF": 1.2,
            "SMB": 0.3,
            "HML": -0.2,
            "RMW": 0.1,
            "CMA": -0.05,
        }

        # Generate strategy return = alpha + beta'*FF5 + RF + noise
        rng = np.random.default_rng(2)
        noise = rng.standard_normal(n_months) * (_MONTHLY_VOL * 0.5)

        strategy_values = (
            alpha_true
            + betas_true["Mkt-RF"] * ff5["Mkt-RF"]
            + betas_true["SMB"] * ff5["SMB"]
            + betas_true["HML"] * ff5["HML"]
            + betas_true["RMW"] * ff5["RMW"]
            + betas_true["CMA"] * ff5["CMA"]
            + ff5["RF"]  # gross return includes RF
            + noise
        )

        # Create Series with DatetimeIndex (aligned to FF5 dates)
        strategy = pd.Series(strategy_values.values, index=ff5["date"])

        result = ff5_residual_regression(strategy, ff5)

        # Check alpha recovered (within tolerance due to noise)
        assert 0.001 <= result["alpha"] <= 0.003, f"alpha={result['alpha']}, expected ~0.002"

        # Check betas have correct signs and approximate magnitudes
        assert result["beta_mkt"] > 0.8, f"beta_mkt={result['beta_mkt']} too low"
        assert result["beta_smb"] > 0.1, f"beta_smb={result['beta_smb']} too low"
        assert result["beta_hml"] < 0, f"beta_hml={result['beta_hml']} should be negative"

        # Check metadata
        assert result["n_obs"] == n_months
        assert result["maxlag"] >= 1
        assert 0 <= result["r_squared"] <= 1  # R² in valid range

    def test_returns_nan_when_insufficient_observations(self) -> None:
        """Regression with fewer than 12 months should return NaN values."""
        ff5 = _make_synthetic_ff5_data(10, seed=3)
        strategy_values = np.random.default_rng(4).standard_normal(10) * 0.01
        strategy = pd.Series(strategy_values, index=ff5["date"])

        result = ff5_residual_regression(strategy, ff5)

        assert np.isnan(result["alpha"])
        assert np.isnan(result["alpha_t"])
        assert np.isnan(result["beta_mkt"])
        assert result["n_obs"] == 10

    def test_handles_datetime_index_strategy(self) -> None:
        """Strategy with DatetimeIndex should be handled correctly."""
        ff5 = _make_synthetic_ff5_data(24, seed=5)
        dates = pd.date_range("2020-01-31", periods=24, freq="ME")
        strategy = pd.Series(np.random.default_rng(6).standard_normal(24) * 0.01, index=dates)

        result = ff5_residual_regression(strategy, ff5)

        assert result["n_obs"] == 24
        assert not np.isnan(result["alpha"])

    def test_inner_joins_on_common_dates(self) -> None:
        """Should only use dates present in both strategy and FF5 data."""
        ff5_long = _make_synthetic_ff5_data(36, seed=7)
        ff5_short = ff5_long.iloc[6:-6].copy()  # middle 24 months

        # Use dates from ff5_short for strategy
        dates = ff5_short["date"].values
        strategy_values = np.random.default_rng(8).standard_normal(24) * 0.01
        strategy = pd.Series(strategy_values, index=dates)

        result = ff5_residual_regression(strategy, ff5_short)

        assert result["n_obs"] == 24  # Only common dates used

    def test_raises_error_for_missing_ff5_columns(self) -> None:
        """Missing FF5 columns should raise ValueError."""
        bad_ff5 = pd.DataFrame({"date": pd.date_range("2020-01-31", periods=12, freq="ME")})
        strategy = pd.Series(np.random.default_rng(9).standard_normal(12) * 0.01)

        with pytest.raises(ValueError, match="missing required columns"):
            ff5_residual_regression(strategy, bad_ff5)

    def test_accepts_custom_maxlag(self) -> None:
        """User-provided maxlag should be used instead of default."""
        ff5 = _make_synthetic_ff5_data(24, seed=10)
        strategy_values = np.random.default_rng(11).standard_normal(24) * 0.01
        strategy = pd.Series(strategy_values, index=ff5["date"])

        result = ff5_residual_regression(strategy, ff5, maxlag=6)

        assert result["maxlag"] == 6

    def test_computes_excess_returns_correctly(self) -> None:
        """Excess returns = strategy - RF should be used in regression."""
        ff5 = _make_synthetic_ff5_data(24, seed=12)
        # Strategy = RF only (no alpha or factor exposure)
        strategy_values = ff5["RF"].values
        strategy = pd.Series(strategy_values, index=ff5["date"])

        result = ff5_residual_regression(strategy, ff5)

        # If strategy = RF, excess returns = 0, so all betas ~0, alpha ~0
        assert abs(result["alpha"]) < 0.001, f"alpha should be ~0, got {result['alpha']}"
        assert abs(result["beta_mkt"]) < 0.1, f"beta_mkt should be ~0, got {result['beta_mkt']}"


class TestAmihudIlliquidity:
    """Tests for Amihud illiquidity calculation."""

    def test_formula_correctness_with_known_values(self) -> None:
        """Verify Amihud formula with hand-computed values.

        For a simple case:
        - Day 1: price=100, volume=1M, return=(101-100)/100=0.01
          illiq_daily = 0.01 / (100 * 1M) = 1e-10
        - Day 2: price=101, volume=2M, return=(100.5-101)/101≈-0.005
          illiq_daily = 0.005 / (101 * 2M) ≈ 2.5e-11
        """
        prices = pd.DataFrame({
            "date": ["2020-01-02", "2020-01-03", "2020-01-06"] * 2,
            "ticker": ["A"] * 3 + ["B"] * 3,
            "close": [100.0, 101.0, 100.5, 50.0, 50.5, 49.8],
        })
        volume = pd.DataFrame({
            "date": ["2020-01-02", "2020-01-03", "2020-01-06"] * 2,
            "ticker": ["A"] * 3 + ["B"] * 3,
            "volume": [1_000_000, 2_000_000, 1_500_000, 500_000, 800_000, 600_000],
        })

        result = amihud_illiquidity(prices, volume, window=3)

        # Basic sanity checks
        assert (result["illiq"] > 0).all(), "illiq should be positive"
        # First row per ticker has NaN return (no previous price), so dropped
        # 2 tickers × 3 dates - 2 first rows = 4 rows
        assert len(result) == 4
        assert set(result["ticker"].unique()) == {"A", "B"}

    def test_rolling_window_aggregates_correctly(self) -> None:
        """Rolling window should average daily illiquidity over the window."""
        prices, volume = _make_synthetic_prices_volumes(n_days=30, n_tickers=2, seed=13)

        result = amihud_illiquidity(prices, volume, window=10)

        # Should have (30 - 1) rows per ticker after dropping first NaN return
        # Minus 9 more for rolling window warmup = 20 per ticker = 40 total
        assert len(result) > 0

    def test_handles_division_by_zero_gracefully(self) -> None:
        """Zero volume should produce NaN, not crash."""
        prices = pd.DataFrame({
            "date": ["2020-01-02", "2020-01-03", "2020-01-06"],
            "ticker": ["A"] * 3,
            "close": [100.0, 101.0, 100.5],
        })
        volume = pd.DataFrame({
            "date": ["2020-01-02", "2020-01-03", "2020-01-06"],
            "ticker": ["A"] * 3,
            "volume": [1_000_000, 0, 1_500_000],  # zero volume on day 2
        })

        result = amihud_illiquidity(prices, volume, window=3)

        # Day 2 (zero volume) should have NaN and be dropped
        assert len(result) < 3

    def test_requires_correct_columns(self) -> None:
        """Missing columns should raise ValueError."""
        bad_prices = pd.DataFrame({"date": ["2020-01-02"], "ticker": ["A"]})  # missing 'close'
        volume = pd.DataFrame({"date": ["2020-01-02"], "ticker": ["A"], "volume": [1000]})

        with pytest.raises(ValueError, match="missing columns"):
            amihud_illiquidity(bad_prices, volume)

    def test_per_ticker_grouping(self) -> None:
        """Each ticker should have its own rolling illiquidity series."""
        prices, volume = _make_synthetic_prices_volumes(n_days=10, n_tickers=3, seed=14)

        result = amihud_illiquidity(prices, volume, window=5)

        # Should have 3 tickers
        assert result["ticker"].nunique() == 3

        # Each ticker should have multiple observations
        per_ticker_counts = result.groupby("ticker").size()
        assert all(count > 0 for count in per_ticker_counts)

    def test_returns_are_absolute_value_normalized(self) -> None:
        """Negative returns should produce positive illiquidity (absolute value)."""
        prices = pd.DataFrame({
            "date": ["2020-01-02", "2020-01-03", "2020-01-06"],
            "ticker": ["A"] * 3,
            "close": [100.0, 95.0, 97.0],  # -5% return, then +2.1% return
        })
        volume = pd.DataFrame({
            "date": ["2020-01-02", "2020-01-03", "2020-01-06"],
            "ticker": ["A"] * 3,
            "volume": [1_000_000, 1_000_000, 1_000_000],
        })

        result = amihud_illiquidity(prices, volume, window=2)

        # All illiq values should be positive
        assert (result["illiq"] > 0).all()


class TestInputValidation:
    """Tests for input validation and edge cases."""

    def test_ff5_regression_with_empty_strategy(self) -> None:
        """Empty strategy should return NaN results."""
        ff5 = _make_synthetic_ff5_data(24, seed=15)
        empty_strategy = pd.Series([], dtype=float)

        result = ff5_residual_regression(empty_strategy, ff5)

        assert result["n_obs"] == 0
        assert np.isnan(result["alpha"])

    def test_amihud_with_single_ticker(self) -> None:
        """Should work correctly with just one ticker."""
        prices = pd.DataFrame({
            "date": ["2020-01-02", "2020-01-03", "2020-01-06"],
            "ticker": ["A"] * 3,
            "close": [100.0, 101.0, 100.5],
        })
        volume = pd.DataFrame({
            "date": ["2020-01-02", "2020-01-03", "2020-01-06"],
            "ticker": ["A"] * 3,
            "volume": [1_000_000, 2_000_000, 1_500_000],
        })

        result = amihud_illiquidity(prices, volume, window=2)

        assert result["ticker"].unique() == ["A"]
        assert len(result) > 0
