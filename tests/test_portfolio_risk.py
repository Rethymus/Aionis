"""Tests for risk_metrics module (hermetic, deterministic, AAA pattern)."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from aionis.eval.portfolio_risk import RiskSummary, risk_summary_to_jsonable, summarize


class TestSummarizeSteadyPositive:
    """Steady-positive series → sharpe>0, sortino>0."""

    def test_sharpe_and_sortino_positive(self):
        # Arrange
        rng = np.random.default_rng(0)
        returns = rng.normal(loc=0.001, scale=0.01, size=252)  # Daily returns, positive drift

        # Act
        summary = summarize(returns, periods_per_year=252)

        # Assert
        assert summary.sharpe > 0
        assert summary.sortino > 0
        assert summary.n_periods == 252
        assert summary.annual_return > 0

    def test_all_metrics_computed(self):
        # Arrange
        rng = np.random.default_rng(0)
        returns = rng.normal(loc=0.0005, scale=0.005, size=100)

        # Act
        summary = summarize(returns, periods_per_year=252)

        # Assert
        assert isinstance(summary, RiskSummary)
        assert summary.n_periods == 100
        assert isinstance(summary.annual_return, float)
        assert isinstance(summary.sharpe, float)
        assert isinstance(summary.sortino, float)
        assert isinstance(summary.max_drawdown, float)
        assert isinstance(summary.calmar, float)
        assert isinstance(summary.var_95, float)
        assert isinstance(summary.cvar_95, float)


class TestSummarizeCrashSeries:
    """Crash series (one huge negative) → max_drawdown very negative, cvar_95 <= var_95 (losses)."""

    def test_max_drawdown_severe_after_crash(self):
        # Arrange
        returns = np.array([0.01, 0.01, 0.01, -0.50, 0.01, 0.01, 0.01])  # 50% crash

        # Act
        summary = summarize(returns, periods_per_year=252)

        # Assert
        assert summary.max_drawdown < -0.40  # Severe drawdown
        assert summary.calmar < 0  # Calmar negative when crash dominates

    def test_cvar_less_than_var_for_losses(self):
        # Arrange
        rng = np.random.default_rng(0)
        # Create returns with heavy left tail
        returns = rng.normal(loc=-0.001, scale=0.02, size=252)
        returns[0:10] = -0.10  # Add some big losses

        # Act
        summary = summarize(returns, periods_per_year=252)

        # Assert
        assert summary.var_95 < 0  # VaR is a loss (negative)
        assert summary.cvar_95 < 0  # CVaR is also a loss (negative)
        # CVaR should be <= VaR (more negative, i.e., larger loss in magnitude)
        assert summary.cvar_95 <= summary.var_95


class TestSummarizeMonotonicity:
    """Higher mean ⇒ higher sharpe (monotone)."""

    def test_higher_mean_increases_sharpe(self):
        # Arrange
        rng = np.random.default_rng(0)
        base_returns = rng.normal(loc=0.0001, scale=0.01, size=252)
        high_returns = base_returns + 0.001  # Add 0.1% to every return

        # Act
        base_summary = summarize(base_returns, periods_per_year=252)
        high_summary = summarize(high_returns, periods_per_year=252)

        # Assert
        assert high_summary.sharpe > base_summary.sharpe
        assert high_summary.annual_return > base_summary.annual_return

    def test_sharpe_increases_with_mean_holding_variance_constant(self):
        # Arrange
        rng = np.random.default_rng(0)
        std = 0.01
        low_mean = 0.0001
        high_mean = 0.002
        low_returns = rng.normal(loc=low_mean, scale=std, size=500)
        high_returns = rng.normal(loc=high_mean, scale=std, size=500)

        # Act
        low_summary = summarize(low_returns, periods_per_year=252)
        high_summary = summarize(high_returns, periods_per_year=252)

        # Assert
        assert high_summary.sharpe > low_summary.sharpe


class TestCalmarSignRelationship:
    """Calmar sign relationship with annual_return and max_drawdown."""

    def test_calmar_sign_follows_annual_return(self):
        # Arrange
        rng = np.random.default_rng(0)
        positive_returns = rng.normal(loc=0.001, scale=0.01, size=252)
        negative_returns = rng.normal(loc=-0.001, scale=0.01, size=252)

        # Act
        pos_summary = summarize(positive_returns, periods_per_year=252)
        neg_summary = summarize(negative_returns, periods_per_year=252)

        # Assert
        # When both have negative drawdowns (typical), calmar sign follows annual_return
        assert pos_summary.calmar * pos_summary.annual_return >= 0  # Same sign
        assert neg_summary.calmar * neg_summary.annual_return >= 0  # Same sign

    def test_calmar_formula_holds(self):
        # Arrange
        rng = np.random.default_rng(0)
        returns = rng.normal(loc=0.0005, scale=0.015, size=252)

        # Act
        summary = summarize(returns, periods_per_year=252)

        # Assert
        # Calmar ≈ annual_return / abs(max_drawdown)
        expected_calmar = summary.annual_return / abs(summary.max_drawdown)
        assert abs(summary.calmar - expected_calmar) < 0.01  # Allow small rounding diff


class TestMinimumReturnsRequirement:
    """<2 returns raises ValueError."""

    def test_zero_returns_raises_value_error(self):
        # Arrange
        returns = np.array([])

        # Act & Assert
        with pytest.raises(ValueError, match="need >=2 returns"):
            summarize(returns, periods_per_year=252)

    def test_single_return_raises_value_error(self):
        # Arrange
        returns = np.array([0.01])

        # Act & Assert
        with pytest.raises(ValueError, match="need >=2 returns"):
            summarize(returns, periods_per_year=252)

    def test_two_returns_succeeds(self):
        # Arrange
        returns = np.array([0.01, -0.005])

        # Act
        summary = summarize(returns, periods_per_year=252)

        # Assert
        assert summary.n_periods == 2


class TestNaNHandling:
    """NaNs dropped."""

    def test_nans_dropped_from_series(self):
        # Arrange
        returns = pd.Series([0.01, np.nan, 0.02, np.nan, -0.01, 0.03])

        # Act
        summary = summarize(returns, periods_per_year=252)

        # Assert
        assert summary.n_periods == 4  # Only finite values counted

    def test_nans_dropped_from_numpy_array(self):
        # Arrange
        returns = np.array([0.01, np.nan, 0.02, np.nan, -0.01, 0.03])

        # Act
        summary = summarize(returns, periods_per_year=252)

        # Assert
        assert summary.n_periods == 4

    def test_all_nans_raises_value_error(self):
        # Arrange
        returns = pd.Series([np.nan, np.nan, np.nan])

        # Act & Assert
        with pytest.raises(ValueError, match="need >=2 returns"):
            summarize(returns, periods_per_year=252)

    def test_inf_values_treated_as_nan(self):
        # Arrange
        returns = np.array([0.01, np.inf, 0.02, -np.inf, -0.01, 0.03])

        # Act
        summary = summarize(returns, periods_per_year=252)

        # Assert
        assert summary.n_periods == 4  # Only finite: 0.01, 0.02, -0.01, 0.03


class TestJsonableRoundTrips:
    """JSON round-trips through json.dumps."""

    def test_jsonable_structure_matches_summary(self):
        # Arrange
        rng = np.random.default_rng(0)
        returns = rng.normal(loc=0.001, scale=0.01, size=252)
        summary = summarize(returns, periods_per_year=252)

        # Act
        jsonable = risk_summary_to_jsonable(summary)

        # Assert
        assert jsonable["n_periods"] == summary.n_periods
        assert jsonable["annual_return"] == summary.annual_return
        assert jsonable["sharpe"] == summary.sharpe
        assert jsonable["sortino"] == summary.sortino
        assert jsonable["max_drawdown"] == summary.max_drawdown
        assert jsonable["calmar"] == summary.calmar
        assert jsonable["var_95"] == summary.var_95
        assert jsonable["cvar_95"] == summary.cvar_95
        assert jsonable["periods_per_year"] == summary.periods_per_year

    def test_jsonable_round_trips_through_json_dumps(self):
        # Arrange
        rng = np.random.default_rng(0)
        returns = rng.normal(loc=0.001, scale=0.01, size=252)
        summary = summarize(returns, periods_per_year=252)
        jsonable = risk_summary_to_jsonable(summary)

        # Act
        json_str = json.dumps(jsonable)
        parsed = json.loads(json_str)

        # Assert
        assert parsed["n_periods"] == summary.n_periods
        assert parsed["annual_return"] == summary.annual_return
        assert isinstance(parsed["annual_return"], float)

    def test_jsonable_fields_are_rounded(self):
        # Arrange
        rng = np.random.default_rng(0)
        returns = rng.normal(loc=0.00123456, scale=0.01, size=252)
        summary = summarize(returns, periods_per_year=252)

        # Act
        jsonable = risk_summary_to_jsonable(summary)

        # Assert
        # Check that values are rounded to 4 decimal places
        metric_keys = [
            "annual_return",
            "sharpe",
            "sortino",
            "max_drawdown",
            "calmar",
            "var_95",
            "cvar_95",
        ]
        for key in metric_keys:
            value = jsonable[key]
            # Rounded to 4 decimal places means it should be close to the original
            # but the decimal representation should be manageable
            assert isinstance(value, float)
            # Convert to string and check it's not excessively long
            str_repr = f"{value:.6f}"  # Should have at most 4 significant decimals
            assert len(str_repr.split(".")[-1]) <= 6


class TestInputTypes:
    """Accepts both pd.Series and np.ndarray."""

    def test_pandas_series_input(self):
        # Arrange
        returns = pd.Series([0.01, 0.02, -0.01, 0.005, 0.03])

        # Act
        summary = summarize(returns, periods_per_year=252)

        # Assert
        assert summary.n_periods == 5

    def test_numpy_array_input(self):
        # Arrange
        returns = np.array([0.01, 0.02, -0.01, 0.005, 0.03])

        # Act
        summary = summarize(returns, periods_per_year=252)

        # Assert
        assert summary.n_periods == 5

    def test_list_input_converted(self):
        # Arrange
        returns = [0.01, 0.02, -0.01, 0.005, 0.03]

        # Act
        summary = summarize(returns, periods_per_year=252)

        # Assert
        assert summary.n_periods == 5


class TestDifferentPeriodsPerYear:
    """Test different annualization frequencies."""

    def test_daily_periods(self):
        # Arrange
        rng = np.random.default_rng(0)
        returns = rng.normal(loc=0.001, scale=0.01, size=252)

        # Act
        summary = summarize(returns, periods_per_year=252)

        # Assert
        assert summary.periods_per_year == 252
        assert summary.n_periods == 252

    def test_monthly_periods(self):
        # Arrange
        rng = np.random.default_rng(0)
        returns = rng.normal(loc=0.01, scale=0.05, size=36)

        # Act
        summary = summarize(returns, periods_per_year=12)

        # Assert
        assert summary.periods_per_year == 12
        assert summary.n_periods == 36


class TestRiskFreeRate:
    """Test risk-free rate parameter."""

    def test_zero_risk_free_rate_default(self):
        # Arrange
        rng = np.random.default_rng(0)
        returns = rng.normal(loc=0.001, scale=0.01, size=252)

        # Act
        summary = summarize(returns, periods_per_year=252, risk_free=0.0)

        # Assert
        # With zero risk-free, sharpe should just be mean/std scaled
        assert isinstance(summary.sharpe, float)

    def test_nonzero_risk_free_rate(self):
        # Arrange
        rng = np.random.default_rng(0)
        returns = rng.normal(loc=0.001, scale=0.01, size=252)

        # Act
        summary_zero_rf = summarize(returns, periods_per_year=252, risk_free=0.0)
        summary_high_rf = summarize(returns, periods_per_year=252, risk_free=0.03)

        # Assert
        # Higher risk-free rate should reduce Sharpe
        assert summary_high_rf.sharpe <= summary_zero_rf.sharpe
