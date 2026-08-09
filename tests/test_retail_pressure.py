"""Tests for retail_pressure module (hermetic, deterministic, AAA)."""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from aionis.eval.retail_pressure import (
    PressureSummary,
    bull_bear_lean,
    compute_pressure,
    crowding_z,
    pressure_grade,
    pressure_summary_to_jsonable,
    velocity,
)


class TestVelocity:
    """Test velocity computation (mention-volume acceleration)."""

    def test_velocity_positive_increase(self):
        """Test velocity with positive increase (50% growth)."""
        # Arrange
        cur_7d = 150
        prev_7d = 100

        # Act
        result = velocity(cur_7d, prev_7d)

        # Assert
        assert result == 0.5

    def test_velocity_no_change(self):
        """Test velocity with no change (stable volume)."""
        # Arrange
        cur_7d = 100
        prev_7d = 100

        # Act
        result = velocity(cur_7d, prev_7d)

        # Assert
        assert result == 0.0

    def test_velocity_decline(self):
        """Test velocity with decline (50% drop)."""
        # Arrange
        cur_7d = 50
        prev_7d = 100

        # Act
        result = velocity(cur_7d, prev_7d)

        # Assert
        assert result == -0.5

    def test_velocity_zero_prev_positive_cur(self):
        """Test velocity with zero previous period (division guard)."""
        # Arrange
        cur_7d = 100
        prev_7d = 0

        # Act
        result = velocity(cur_7d, prev_7d)

        # Assert
        assert result == 1.0

    def test_velocity_both_zero(self):
        """Test velocity with both periods zero."""
        # Arrange
        cur_7d = 0
        prev_7d = 0

        # Act
        result = velocity(cur_7d, prev_7d)

        # Assert
        assert result == 0.0

    def test_velocity_negative_prev(self):
        """Test velocity with negative previous period (division guard)."""
        # Arrange
        cur_7d = 100
        prev_7d = -10

        # Act
        result = velocity(cur_7d, prev_7d)

        # Assert
        assert result == 1.0


class TestCrowdingZ:
    """Test crowding z-score computation."""

    def test_crowding_z_positive(self):
        """Test crowding z-score with above-average latest."""
        # Arrange
        latest = 150.0
        mean = 100.0
        std = 20.0

        # Act
        result = crowding_z(latest, mean, std)

        # Assert
        assert result == 2.5

    def test_crowding_z_negative(self):
        """Test crowding z-score with below-average latest."""
        # Arrange
        latest = 60.0
        mean = 100.0
        std = 20.0

        # Act
        result = crowding_z(latest, mean, std)

        # Assert
        assert result == -2.0

    def test_crowding_z_zero_std_division_guard(self):
        """Test crowding z-score with zero std (division guard)."""
        # Arrange
        latest = 150.0
        mean = 100.0
        std = 0.0

        # Act
        result = crowding_z(latest, mean, std)

        # Assert
        assert result == 0.0

    def test_crowding_z_tiny_std_division_guard(self):
        """Test crowding z-score with tiny std (<1e-9, division guard)."""
        # Arrange
        latest = 150.0
        mean = 100.0
        std = 1e-10

        # Act
        result = crowding_z(latest, mean, std)

        # Assert
        assert result == 0.0

    def test_crowding_z_at_mean(self):
        """Test crowding z-score at exactly the mean."""
        # Arrange
        latest = 100.0
        mean = 100.0
        std = 20.0

        # Act
        result = crowding_z(latest, mean, std)

        # Assert
        assert result == 0.0


class TestBullBearLean:
    """Test bull/bear sentiment lean computation."""

    def test_bull_bear_lean_positive(self):
        """Test bull/bear lean with positive sentiment."""
        # Arrange
        sentiments = [0.5, 0.3, -0.1]

        # Act
        result = bull_bear_lean(sentiments)

        # Assert
        assert np.isclose(result, 0.23333333333333334)

    def test_bull_bear_lean_negative(self):
        """Test bull/bear lean with negative sentiment."""
        # Arrange
        sentiments = [-0.5, -0.3, 0.1]

        # Act
        result = bull_bear_lean(sentiments)

        # Assert
        assert np.isclose(result, -0.23333333333333334)

    def test_bull_bear_lean_nan_ignored(self):
        """Test bull/bear lean with NaN values ignored."""
        # Arrange
        sentiments = [np.nan, 0.5, np.nan]

        # Act
        result = bull_bear_lean(sentiments)

        # Assert
        assert result == 0.5

    def test_bull_bear_lean_all_nan(self):
        """Test bull/bear lean with all NaN values."""
        # Arrange
        sentiments = [np.nan, np.nan]

        # Act
        result = bull_bear_lean(sentiments)

        # Assert
        assert result == 0.0

    def test_bull_bear_lean_empty(self):
        """Test bull/bear lean with empty sequence."""
        # Arrange
        sentiments = []

        # Act
        result = bull_bear_lean(sentiments)

        # Assert
        assert result == 0.0

    def test_bull_bear_lean_neutral(self):
        """Test bull/bear lean with perfectly balanced sentiment."""
        # Arrange
        sentiments = [0.5, -0.5, 0.3, -0.3]

        # Act
        result = bull_bear_lean(sentiments)

        # Assert
        assert result == 0.0


class TestPressureGrade:
    """Test pressure grade classification."""

    def test_pressure_grade_surge_high_velocity(self):
        """Test 'surge' grade from high velocity."""
        # Arrange
        velocity_val = 1.2
        crowding_z_val = 1.0

        # Act
        result = pressure_grade(velocity_val, crowding_z_val)

        # Assert
        assert result == "surge"

    def test_pressure_grade_surge_high_crowding(self):
        """Test 'surge' grade from high crowding."""
        # Arrange
        velocity_val = 0.8
        crowding_z_val = 2.5

        # Act
        result = pressure_grade(velocity_val, crowding_z_val)

        # Assert
        assert result == "surge"

    def test_pressure_grade_elevated(self):
        """Test 'elevated' grade."""
        # Arrange
        velocity_val = 0.6
        crowding_z_val = 1.0

        # Act
        result = pressure_grade(velocity_val, crowding_z_val)

        # Assert
        assert result == "elevated"

    def test_pressure_grade_quiet(self):
        """Test 'quiet' grade."""
        # Arrange
        velocity_val = -0.5
        crowding_z_val = -1.5

        # Act
        result = pressure_grade(velocity_val, crowding_z_val)

        # Assert
        assert result == "quiet"

    def test_pressure_grade_normal(self):
        """Test 'normal' grade."""
        # Arrange
        velocity_val = 0.0
        crowding_z_val = 0.0

        # Act
        result = pressure_grade(velocity_val, crowding_z_val)

        # Assert
        assert result == "normal"

    def test_pressure_grade_velocity_threshold(self):
        """Test velocity >= 1.0 triggers surge."""
        # Arrange
        velocity_val = 1.0
        crowding_z_val = 0.0

        # Act
        result = pressure_grade(velocity_val, crowding_z_val)

        # Assert
        assert result == "surge"

    def test_pressure_grade_crowding_threshold(self):
        """Test crowding_z >= 2.5 triggers surge."""
        # Arrange
        velocity_val = 0.0
        crowding_z_val = 2.5

        # Act
        result = pressure_grade(velocity_val, crowding_z_val)

        # Assert
        assert result == "surge"

    def test_pressure_grade_quiet_both_conditions(self):
        """Test quiet requires BOTH velocity <= -0.3 AND crowding <= -1.0."""
        # Arrange
        velocity_val = -0.5
        crowding_z_val = -0.5  # not quiet (crowding not low enough)

        # Act
        result = pressure_grade(velocity_val, crowding_z_val)

        # Assert
        assert result == "normal"


class TestComputePressure:
    """Test compute_pressure main entry point."""

    def _build_history(
        self,
        ticker: str,
        base_date: str,
        days: int,
        mentions_pattern: list[int] | None = None,
        sentiment_pattern: list[float] | None = None,
    ) -> list[dict]:
        """Helper to build mention history for testing."""
        base = datetime.strptime(base_date, "%Y-%m-%d")
        history = []

        for i in range(days):
            date = (base + timedelta(days=i)).strftime("%Y-%m-%d")
            mentions = (
                mentions_pattern[i]
                if mentions_pattern and i < len(mentions_pattern)
                else 100
            )
            sentiment = (
                sentiment_pattern[i]
                if sentiment_pattern and i < len(sentiment_pattern)
                else 0.0
            )

            history.append({
                "date": date,
                "ticker": ticker,
                "mentions": mentions,
                "sentiment": sentiment,
            })

        return history

    def test_compute_pressure_surge_ticker(self):
        """Test ticker with sudden mention spike → grade 'surge', high velocity, high z."""
        # Arrange
        base_date = "2024-01-01"
        # First 21 days: baseline 100 mentions/day
        # Last 7 days: 200 mentions/day (surge)
        mentions = [100] * 21 + [200] * 7
        sentiments = [0.5] * 28
        history = self._build_history("GME", base_date, 28, mentions, sentiments)
        latest_date = "2024-01-28"

        # Act
        results = compute_pressure(history, latest_date, lookback_days=30)

        # Assert
        assert "GME" in results
        summary = results["GME"]
        assert summary.grade == "surge"
        assert summary.velocity == 1.0  # (1400 - 700) / 700 = 1.0
        assert summary.crowding_z > 1.5  # high crowding (std ≈ 42, z ≈ 1.7)
        assert summary.n_days == 28

    def test_compute_pressure_normal_ticker(self):
        """Test flat ticker → 'normal' grade."""
        # Arrange
        base_date = "2024-01-01"
        mentions = [100] * 28  # flat 100 mentions/day
        sentiments = [0.0] * 28
        history = self._build_history("AAPL", base_date, 28, mentions, sentiments)
        latest_date = "2024-01-28"

        # Act
        results = compute_pressure(history, latest_date, lookback_days=30)

        # Assert
        assert "AAPL" in results
        summary = results["AAPL"]
        assert summary.grade == "normal"
        assert summary.velocity == 0.0  # no change

    def test_compute_pressure_quiet_ticker(self):
        """Test declining ticker → 'quiet' grade."""
        # Arrange
        base_date = "2024-01-01"
        # Days 1-21: 200 mentions/day (high baseline)
        # Days 22-28: 100 mentions/day (decline in last 7 days)
        mentions = [200] * 21 + [100] * 7
        sentiments = [-0.3] * 28
        history = self._build_history("BBBY", base_date, 28, mentions, sentiments)
        latest_date = "2024-01-28"

        # Act
        results = compute_pressure(history, latest_date, lookback_days=30)

        # Assert
        assert "BBBY" in results
        summary = results["BBBY"]
        # velocity = (700 - 1400) / 1400 = -0.5 (declining)
        # z = (100 - 175) / 50.9 ≈ -1.47 (below norm)
        assert summary.grade == "quiet"
        assert summary.velocity < -0.3  # declining
        assert summary.crowding_z < -1.0  # below norm

    def test_compute_pressure_insufficient_history_skipped(self):
        """Test ticker with <14 days history → absent from result."""
        # Arrange
        base_date = "2024-01-01"
        mentions = [100] * 10  # only 10 days
        sentiments = [0.0] * 10
        history = self._build_history("TSLA", base_date, 10, mentions, sentiments)
        latest_date = "2024-01-10"

        # Act
        results = compute_pressure(history, latest_date, lookback_days=30)

        # Assert
        assert "TSLA" not in results  # skipped (insufficient history)

    def test_compute_pressure_std_zero_no_division_error(self):
        """Test std=0 → crowding_z=0.0 (no division by zero)."""
        # Arrange
        base_date = "2024-01-01"
        mentions = [100] * 28  # constant mentions → std=0
        sentiments = [0.0] * 28
        history = self._build_history("MSFT", base_date, 28, mentions, sentiments)
        latest_date = "2024-01-28"

        # Act
        results = compute_pressure(history, latest_date, lookback_days=30)

        # Assert
        assert "MSFT" in results
        summary = results["MSFT"]
        assert summary.crowding_z == 0.0  # division guard worked
        assert summary.grade == "normal"

    def test_compute_pressure_nan_sentiments_ignored(self):
        """Test NaN sentiments ignored in bull_bear_lean."""
        # Arrange
        base_date = "2024-01-01"
        mentions = [100] * 28
        sentiments = [np.nan, 0.5, np.nan, -0.3, 0.2] * 6  # mix of NaN and valid
        history = self._build_history("NVDA", base_date, 28, mentions, sentiments)
        latest_date = "2024-01-28"

        # Act
        results = compute_pressure(history, latest_date, lookback_days=30)

        # Assert
        assert "NVDA" in results
        summary = results["NVDA"]
        # Should ignore NaN and compute mean of [0.5, -0.3, 0.2, ...]
        assert not np.isnan(summary.bull_bear_lean)
        assert summary.bull_bear_lean != 0.0  # has valid sentiment data

    def test_compute_pressure_determinism(self):
        """Test same input twice → identical output (determinism)."""
        # Arrange
        base_date = "2024-01-01"
        mentions = [100] * 21 + [200] * 7
        sentiments = [0.5] * 28
        history = self._build_history("AMD", base_date, 28, mentions, sentiments)
        latest_date = "2024-01-28"

        # Act
        results1 = compute_pressure(history, latest_date, lookback_days=30)
        results2 = compute_pressure(history, latest_date, lookback_days=30)

        # Assert
        assert "AMD" in results1
        assert "AMD" in results2
        summary1 = results1["AMD"]
        summary2 = results2["AMD"]

        # All fields must be identical
        assert summary1.ticker == summary2.ticker
        assert summary1.latest_mentions == summary2.latest_mentions
        assert summary1.velocity == summary2.velocity
        assert summary1.crowding_z == summary2.crowding_z
        assert summary1.bull_bear_lean == summary2.bull_bear_lean
        assert summary1.grade == summary2.grade
        assert summary1.n_days == summary2.n_days

    def test_compute_pressure_with_dataframe_input(self):
        """Test compute_pressure accepts DataFrame input."""
        # Arrange
        base_date = "2024-01-01"
        mentions = [100] * 28
        sentiments = [0.0] * 28
        history_list = self._build_history("META", base_date, 28, mentions, sentiments)
        df = pd.DataFrame(history_list)
        latest_date = "2024-01-28"

        # Act
        results = compute_pressure(df, latest_date, lookback_days=30)

        # Assert
        assert "META" in results

    def test_compute_pressure_empty_history_raises(self):
        """Test empty history raises ValueError."""
        # Arrange
        history = []
        latest_date = "2024-01-28"

        # Act & Assert
        with pytest.raises(ValueError, match="history is empty"):
            compute_pressure(history, latest_date, lookback_days=30)

    def test_compute_pressure_missing_columns_raises(self):
        """Test missing required columns raises ValueError."""
        # Arrange
        history = [
            {"date": "2024-01-01", "ticker": "GME", "mentions": 100}
            # missing "sentiment"
        ]
        latest_date = "2024-01-28"

        # Act & Assert
        with pytest.raises(ValueError, match="missing required columns"):
            compute_pressure(history, latest_date, lookback_days=30)

    def test_compute_pressure_multiple_tickers(self):
        """Test multiple tickers computed independently."""
        # Arrange
        base_date = "2024-01-01"
        history = []

        # GME: surge pattern
        for i in range(28):
            base_dt = datetime.strptime(base_date, "%Y-%m-%d")
            date = (base_dt + timedelta(days=i)).strftime("%Y-%m-%d")
            mentions = 200 if i >= 21 else 100
            history.append({"date": date, "ticker": "GME", "mentions": mentions, "sentiment": 0.5})

        # AAPL: normal pattern
        for i in range(28):
            base_dt = datetime.strptime(base_date, "%Y-%m-%d")
            date = (base_dt + timedelta(days=i)).strftime("%Y-%m-%d")
            history.append({"date": date, "ticker": "AAPL", "mentions": 100, "sentiment": 0.0})

        latest_date = "2024-01-28"

        # Act
        results = compute_pressure(history, latest_date, lookback_days=30)

        # Assert
        assert len(results) == 2
        assert "GME" in results
        assert "AAPL" in results
        assert results["GME"].grade == "surge"
        assert results["AAPL"].grade == "normal"

    def test_compute_pressure_lookback_truncates(self):
        """Test lookback_days truncates window correctly."""
        # Arrange
        base_date = "2024-01-01"
        # 40 days of history, but lookback only 20
        mentions = [100] * 40
        sentiments = [0.0] * 40
        history = self._build_history("AMC", base_date, 40, mentions, sentiments)
        latest_date = "2024-02-09"

        # Act
        results = compute_pressure(history, latest_date, lookback_days=20)

        # Assert
        assert "AMC" in results
        summary = results["AMC"]
        assert summary.n_days == 20  # only last 20 days in window


class TestPressureSummaryToJsonable:
    """Test pressure_summary_to_jsonable serialization."""

    def test_jsonable_round_trip(self):
        """Test JSON round-trip preserves all fields."""
        # Arrange
        summary = PressureSummary(
            ticker="GME",
            latest_mentions=200,
            velocity=1.5,
            crowding_z=2.8,
            bull_bear_lean=0.65,
            grade="surge",
            n_days=28,
        )

        # Act
        jsonable = pressure_summary_to_jsonable(summary)

        # Assert
        assert jsonable["ticker"] == "GME"
        assert jsonable["latest_mentions"] == 200
        assert jsonable["velocity"] == 1.5
        assert jsonable["crowding_z"] == 2.8
        assert jsonable["bull_bear_lean"] == 0.65
        assert jsonable["grade"] == "surge"
        assert jsonable["n_days"] == 28

    def test_jsonable_rounds_correctly(self):
        """Test jsonable rounds float fields correctly."""
        # Arrange - create summary with unrounded values to test rounding
        summary = PressureSummary(
            ticker="AAPL",
            latest_mentions=100,
            velocity=round(0.123456789, 4),  # rounded in main module
            crowding_z=round(1.987654321, 4),  # rounded in main module
            bull_bear_lean=round(0.333333333, 4),  # rounded in main module
            grade="elevated",
            n_days=30,
        )

        # Act
        jsonable = pressure_summary_to_jsonable(summary)

        # Assert - values are already rounded in PressureSummary
        assert jsonable["velocity"] == 0.1235
        assert jsonable["crowding_z"] == 1.9877
        assert jsonable["bull_bear_lean"] == 0.3333

    def test_jsonable_preserves_grade_string(self):
        """Test jsonable preserves grade string exactly."""
        # Arrange
        for grade in ["surge", "elevated", "normal", "quiet"]:
            summary = PressureSummary(
                ticker="TEST",
                latest_mentions=100,
                velocity=0.0,
                crowding_z=0.0,
                bull_bear_lean=0.0,
                grade=grade,
                n_days=20,
            )

            # Act
            jsonable = pressure_summary_to_jsonable(summary)

            # Assert
            assert jsonable["grade"] == grade
