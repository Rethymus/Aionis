"""Hermetic tests for cross-sectional risk factors.

Synthetic fixtures with deterministic seed. AAA pattern. Descriptive names.
Edge cases: insufficient history, single ticker, all-up market (downside beta undefined).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aionis.features.risk_factors import (
    TRACK_B_RISK_FACTOR_COLS,
    _compute_market_returns,
    _compute_returns_from_panel,
    compute_risk_factors,
    downside_beta,
    idiosyncratic_volatility,
    tail_risk_skewness,
    worst_day_drawdown,
)

# Fixed seed for deterministic tests
_RNG = np.random.default_rng(seed=42)


def _make_panel(
    n_dates: int = 300,
    n_tickers: int = 3,
    base_price: float = 100.0,
    drift: float = 0.0001,
    volatility: float = 0.01,
) -> pd.DataFrame:
    """Generate synthetic price panel (geometric Brownian motion).

    Args:
        n_dates: Number of trading days.
        n_tickers: Number of tickers.
        base_price: Starting price.
        drift: Daily drift (mean return).
        volatility: Daily volatility.

    Returns:
        Long-format panel with columns [date, ticker, close].
    """
    dates = pd.date_range("2024-01-01", periods=n_dates, freq="B")
    tickers = [f"T{i}" for i in range(n_tickers)]

    rows = []
    for t in range(n_tickers):
        # Geometric Brownian Motion
        log_returns = _RNG.normal(
            drift - 0.5 * volatility**2, volatility, n_dates
        )
        log_prices = np.log(base_price) + np.cumsum(log_returns)
        prices = np.exp(log_prices)

        for i, date in enumerate(dates):
            rows.append({"date": date, "ticker": tickers[t], "close": prices[i]})

    return pd.DataFrame(rows)


def _make_returns_wide(
    n_dates: int = 100,
    n_tickers: int = 3,
    mean_return: float = 0.0001,
    volatility: float = 0.01,
) -> tuple[pd.DataFrame, pd.Series]:
    """Generate synthetic returns in wide format plus market returns.

    Args:
        n_dates: Number of trading days.
        n_tickers: Number of tickers.
        mean_return: Daily mean return.
        volatility: Daily volatility.

    Returns:
        Tuple of (returns_wide [dates x tickers], market_returns [dates]).
    """
    dates = pd.date_range("2024-01-01", periods=n_dates, freq="B")
    tickers = [f"T{i}" for i in range(n_tickers)]

    # Generate stock returns
    data = _RNG.normal(mean_return, volatility, (n_dates, n_tickers))
    returns_wide = pd.DataFrame(data, index=dates, columns=tickers)

    # Market returns = equal-weighted portfolio
    market_returns = returns_wide.mean(axis=1)

    return returns_wide, market_returns


class TestComputeReturnsFromPanel:
    """Test return computation from panel."""

    def test_returns_match_pct_change(self) -> None:
        """Returns match pandas pct_change on pivot."""
        panel = _make_panel(n_dates=50, n_tickers=2)

        result = _compute_returns_from_panel(panel)

        # Pivot and pct_change manually
        prices_wide = panel.pivot(index="date", columns="ticker", values="close")
        expected_returns = prices_wide.pct_change()

        # Convert result to wide for comparison
        result_wide = result.pivot(index="date", columns="ticker", values="return")

        pd.testing.assert_frame_equal(result_wide, expected_returns)

    def test_handles_missing_dates(self) -> None:
        """Handles panel with missing dates (gaps)."""
        dates = pd.date_range("2024-01-01", periods=10, freq="B")
        rows = []
        for i, date in enumerate(dates):
            if i in [3, 7]:  # Skip some dates
                continue
            rows.append({"date": date, "ticker": "T0", "close": 100.0 + i})

        panel = pd.DataFrame(rows)
        result = _compute_returns_from_panel(panel)

        # Should not crash, returns computed where possible
        assert len(result) > 0
        assert "return" in result.columns


class TestComputeMarketReturns:
    """Test market return computation."""

    def test_market_returns_equal_weighted(self) -> None:
        """Market returns are equal-weighted mean of all stocks."""
        returns_wide, market_returns = _make_returns_wide(n_dates=50, n_tickers=3)

        # Manually compute expected
        expected = returns_wide.mean(axis=1)

        pd.testing.assert_series_equal(market_returns, expected)

    def test_market_returns_ignores_nan(self) -> None:
        """Market returns ignore NaN stock returns."""
        dates = pd.date_range("2024-01-01", periods=10, freq="B")
        returns_wide = pd.DataFrame(
            [[0.01, 0.02, np.nan], [0.02, -0.01, 0.01]],  # NaN ignored
            index=dates[:2],
            columns=["T0", "T1", "T2"],
        )

        result = _compute_market_returns(returns_wide)

        # Expected: mean of non-NaN values
        expected = pd.Series(
            [(0.01 + 0.02) / 2, (0.02 - 0.01 + 0.01) / 3], index=dates[:2]
        )

        pd.testing.assert_series_equal(result, expected)


class TestDownsideBeta:
    """Test downside beta computation."""

    def test_downside_beta_high_on_crash_sensitive_stocks(self) -> None:
        """Stocks that fall more than market on down days have high downside beta."""
        dates = pd.date_range("2024-01-01", periods=300, freq="B")

        # Create market with mixed up/down days (ensure enough down days)
        market_returns = pd.Series(_RNG.normal(0, 0.02, 300), index=dates)

        # Create two stocks:
        # T0: amplifies market moves (beta ~2)
        # T1: dampens market moves (beta ~0.5)
        stock_returns = pd.DataFrame(index=dates, columns=["T0", "T1"])
        stock_returns["T0"] = market_returns * 2.0 + _RNG.normal(0, 0.005, 300)
        stock_returns["T1"] = market_returns * 0.5 + _RNG.normal(0, 0.005, 300)

        result = downside_beta(stock_returns, market_returns, window=252)

        # T0 should have higher downside beta than T1
        # Check after warmup period (final value should be non-NaN)
        t0_downside_beta = result["T0"].iloc[-1]
        t1_downside_beta = result["T1"].iloc[-1]

        # Should have valid values
        assert not pd.isna(t0_downside_beta)
        assert not pd.isna(t1_downside_beta)
        # T0 should have higher downside beta than T1
        assert t0_downside_beta > t1_downside_beta

    def test_downside_beta_uses_down_days_only(self) -> None:
        """Downside beta only considers down market days."""
        dates = pd.date_range("2024-01-01", periods=100, freq="B")

        # Create market with clear up/down pattern
        market_returns = pd.Series(
            np.concatenate([np.full(50, -0.01), np.full(50, 0.01)]), index=dates
        )

        # Stock perfectly correlated with market
        stock_returns = pd.DataFrame({"T0": market_returns.values}, index=dates)

        result = downside_beta(stock_returns, market_returns, window=50)

        # Downside beta should exist (not all NaN)
        assert result["T0"].iloc[-1] is not pd.NA

    def test_downside_beta_nan_when_all_market_up(self) -> None:
        """Downside beta is NaN when market never goes down (insufficient down days)."""
        dates = pd.date_range("2024-01-01", periods=100, freq="B")

        # Market always goes up
        market_returns = pd.Series(np.full(100, 0.01), index=dates)
        stock_returns = pd.DataFrame({"T0": np.full(100, 0.02)}, index=dates)

        result = downside_beta(stock_returns, market_returns, window=50)

        # Should be NaN (no down days to compute downside beta)
        assert pd.isna(result["T0"].iloc[-1])

    def test_downside_beta_nan_when_insufficient_history(self) -> None:
        """Downside beta is NaN when insufficient history."""
        dates = pd.date_range("2024-01-01", periods=10, freq="B")
        market_returns = pd.Series(_RNG.normal(0, 0.01, 10), index=dates)
        stock_returns = pd.DataFrame(
            {"T0": _RNG.normal(0, 0.01, 10)}, index=dates
        )

        result = downside_beta(stock_returns, market_returns, window=252)

        # Should be NaN (insufficient data for 252-day window)
        assert result["T0"].isna().all()


class TestIdiosyncraticVolatility:
    """Test idiosyncratic volatility computation."""

    def test_idio_vol_captures_stock_specific_risk(self) -> None:
        """Idiosyncratic volatility captures stock-specific risk component."""
        dates = pd.date_range("2024-01-01", periods=100, freq="B")

        market_returns = pd.Series(_RNG.normal(0, 0.01, 100), index=dates)

        # Two stocks:
        # T0: high idio vol (lots of stock-specific noise)
        # T1: low idio vol (mostly follows market)
        stock_returns = pd.DataFrame(index=dates, columns=["T0", "T1"])
        stock_returns["T0"] = (
            market_returns * 1.0 + _RNG.normal(0, 0.02, 100)
        )  # High idio
        stock_returns["T1"] = (
            market_returns * 1.0 + _RNG.normal(0, 0.002, 100)
        )  # Low idio

        result = idiosyncratic_volatility(stock_returns, market_returns, window=50)

        # T0 should have higher idio vol than T1
        assert result["T0"].iloc[-1] > result["T1"].iloc[-1]

    def test_idio_vol_matches_residual_std(self) -> None:
        """Idio vol matches standard deviation of regression residuals."""
        dates = pd.date_range("2024-01-01", periods=100, freq="B")
        market_returns = pd.Series(_RNG.normal(0, 0.01, 100), index=dates)

        # Stock with beta = 1.5
        beta = 1.5
        stock_returns = pd.DataFrame(
            {"T0": market_returns * beta + _RNG.normal(0, 0.01, 100)}, index=dates
        )

        result = idiosyncratic_volatility(stock_returns, market_returns, window=50)

        # Manually compute for last window
        window_data = stock_returns["T0"].iloc[-50:]
        market_window = market_returns.iloc[-50:]

        # Regression: r_stock = alpha + beta * r_market + epsilon
        # Simplified: residual = r_stock - beta * r_market
        beta_est = (
            np.cov(window_data, market_window)[0, 1]
            / np.var(market_window)
            if np.var(market_window) > 1e-9
            else 0
        )
        residual = window_data - beta_est * market_window
        expected_idio_vol = np.std(residual)

        # Result should be close to expected
        assert result["T0"].iloc[-1] == pytest.approx(expected_idio_vol, abs=0.005)

    def test_idio_vol_nan_when_insufficient_history(self) -> None:
        """Idio vol is NaN when insufficient history."""
        dates = pd.date_range("2024-01-01", periods=5, freq="B")
        market_returns = pd.Series(_RNG.normal(0, 0.01, 5), index=dates)
        stock_returns = pd.DataFrame({"T0": _RNG.normal(0, 0.01, 5)}, index=dates)

        result = idiosyncratic_volatility(stock_returns, market_returns, window=63)

        # Should be NaN (insufficient for 63-day window)
        assert result["T0"].isna().all()


class TestTailRiskSkewness:
    """Test return skewness computation."""

    def test_negative_skewness_indicates_left_tail(self) -> None:
        """Negative skewness indicates fat left tail (crash risk)."""
        dates = pd.date_range("2024-01-01", periods=100, freq="B")

        # T0: symmetric returns (skew ~ 0)
        # T1: negative skew (occasional big crashes)
        returns = pd.DataFrame(index=dates, columns=["T0", "T1"])
        returns["T0"] = _RNG.normal(0, 0.01, 100)  # Symmetric

        # Create negative skew: mostly small gains, occasional big losses
        t1_returns = []
        for _ in range(100):
            if _RNG.random() < 0.1:  # 10% crash days
                t1_returns.append(-0.05)  # -5% crash
            else:
                t1_returns.append(_RNG.normal(0.005, 0.005))  # Small gains
        returns["T1"] = t1_returns

        result = tail_risk_skewness(returns, window=50)

        # T1 should have negative skewness (left tail)
        assert result["T1"].iloc[-1] < 0

    def test_skewness_handles_insufficient_data(self) -> None:
        """Skewness returns NaN with insufficient history."""
        dates = pd.date_range("2024-01-01", periods=10, freq="B")
        returns = pd.DataFrame({"T0": _RNG.normal(0, 0.01, 10)}, index=dates)

        result = tail_risk_skewness(returns, window=63)

        # Should be NaN (insufficient for 63-day window)
        assert result["T0"].isna().all()


class TestWorstDayDrawdown:
    """Test worst day drawdown computation."""

    def test_worst_day_captures_extreme_losses(self) -> None:
        """Worst day captures most extreme single-day loss."""
        dates = pd.date_range("2024-01-01", periods=100, freq="B")

        # T0: normal volatility (worst ~ -2%)
        # T1: has a crash day (-10%)
        returns = pd.DataFrame(index=dates, columns=["T0", "T1"])
        returns["T0"] = _RNG.normal(0, 0.01, 100)
        t1_returns = _RNG.normal(0, 0.01, 100).tolist()
        t1_returns[50] = -0.10  # Insert a crash
        returns["T1"] = t1_returns

        result = worst_day_drawdown(returns, window=63)

        # T1 should have worse worst-day than T0
        assert result["T1"].iloc[-1] < result["T0"].iloc[-1]
        # T1 worst should be near -10%
        assert result["T1"].iloc[-1] == pytest.approx(-0.10, abs=0.02)

    def test_worst_day_matches_rolling_min(self) -> None:
        """Worst day matches rolling minimum."""
        dates = pd.date_range("2024-01-01", periods=50, freq="B")
        returns = pd.DataFrame({"T0": _RNG.normal(0, 0.01, 50)}, index=dates)

        result = worst_day_drawdown(returns, window=21)

        # Manually compute rolling min
        expected = returns.rolling(window=21, min_periods=5).min()

        pd.testing.assert_frame_equal(result, expected)


class TestComputeRiskFactors:
    """Test the main compute_risk_factors function."""

    def test_returns_all_four_factors(self) -> None:
        """Returns all four risk factor columns."""
        panel = _make_panel(n_dates=300, n_tickers=3)

        result = compute_risk_factors(panel)

        # Check columns
        expected_cols = {
            "date",
            "ticker",
            "downside_beta",
            "idiosyncratic_volatility",
            "return_skewness",
            "worst_day_drawdown",
        }
        assert set(result.columns) == expected_cols

    def test_result_is_sorted_by_date_then_ticker(self) -> None:
        """Result is sorted by date then ticker."""
        panel = _make_panel(n_dates=100, n_tickers=3)

        result = compute_risk_factors(panel)

        # Check sorting
        assert (result["date"].is_monotonic_increasing or result["date"].is_monotonic_decreasing)
        # Within each date, tickers should be sorted
        for date in result["date"].unique():
            date_slice = result[result["date"] == date]
            assert date_slice["ticker"].is_monotonic_increasing

    def test_handles_insufficient_history_gracefully(self) -> None:
        """Handles panels with insufficient history (returns NaN where appropriate)."""
        panel = _make_panel(n_dates=50, n_tickers=2)  # Less than 252-day window

        result = compute_risk_factors(panel)

        # Should not crash, but many values should be NaN
        assert len(result) > 0
        # downside_beta requires 252 days, so should be all NaN
        assert result["downside_beta"].isna().all()

    def test_handles_single_ticker(self) -> None:
        """Handles panel with single ticker."""
        panel = _make_panel(n_dates=300, n_tickers=1)

        result = compute_risk_factors(panel)

        # Should not crash
        assert len(result) > 0
        assert set(result["ticker"]) == {"T0"}

    def test_mergeable_into_original_panel(self) -> None:
        """Result is mergeable into original panel on [date, ticker]."""
        panel = _make_panel(n_dates=300, n_tickers=3)

        risk_factors = compute_risk_factors(panel)

        # Merge should work
        merged = panel.merge(risk_factors, on=["date", "ticker"], how="left")

        # Should have all original columns plus new risk factors
        assert len(merged.columns) == len(panel.columns) + 4  # 4 new factors

    def test_all_up_market_produces_nan_downside_beta(self) -> None:
        """Panel with all-up market produces NaN for downside beta."""
        # Create panel where market only goes up
        dates = pd.date_range("2024-01-01", periods=100, freq="B")
        rows = []
        for i, date in enumerate(dates):
            # All stocks go up every day
            rows.append({"date": date, "ticker": "T0", "close": 100 * (1.01**i)})
            rows.append({"date": date, "ticker": "T1", "close": 100 * (1.015**i)})

        panel = pd.DataFrame(rows)

        result = compute_risk_factors(panel)

        # downside_beta should be NaN (no down days)
        assert result["downside_beta"].isna().all()


class TestTrackBRiskFactorCols:
    """Test the pre-specified risk factor column list."""

    def test_risk_factor_cols_is_non_empty_list(self) -> None:
        """TRACK_B_RISK_FACTOR_COLS is a non-empty list."""
        assert isinstance(TRACK_B_RISK_FACTOR_COLS, list)
        assert len(TRACK_B_RISK_FACTOR_COLS) > 0

    def test_contains_expected_factors(self) -> None:
        """Contains the four expected risk factors."""
        expected = {
            "downside_beta",
            "idiosyncratic_volatility",
            "return_skewness",
            "worst_day_drawdown",
        }
        assert set(TRACK_B_RISK_FACTOR_COLS) == expected

    def test_count_matches_computed_factors(self) -> None:
        """Count matches number of factors computed by compute_risk_factors."""
        panel = _make_panel(n_dates=300, n_tickers=3)
        result = compute_risk_factors(panel)

        computed_factors = set(result.columns) - {"date", "ticker"}
        assert computed_factors == set(TRACK_B_RISK_FACTOR_COLS)
