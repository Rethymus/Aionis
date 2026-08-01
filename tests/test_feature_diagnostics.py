"""Tests for cross-sectional feature variation diagnostics.

Hermetic tests using synthetic/labeled fixtures only (no real data, no network).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aionis.features.diagnostics import (
    MIN_VALID_COUNT,
    NEAR_CONSTANT_STD_THRESHOLD,
    VERDICT_ALL_MISSING,
    VERDICT_CONSTANT,
    VERDICT_FEW_VALID,
    VERDICT_NEAR_CONSTANT,
    VERDICT_VARIATION,
    feature_variation_diagnostics,
)


@pytest.fixture
def sample_panel() -> pd.DataFrame:
    """Create a sample feature panel with various variation patterns.

    Panel structure:
        - Dates: 2024-01-01, 2024-02-01 (2 months)
        - Tickers: A, B, C, D, E (5 tickers)
        - Features:
            * const_feat: CONSTANT (all same value per month)
            * near_const_feat: NEAR_CONSTANT (std below threshold)
            * all_missing_feat: ALL_MISSING (all NaN)
            * few_valid_feat: FEW_VALID (only 2 valid values < min_valid_count=5)
            * real_var_feat: VARIATION (real cross-sectional spread)
    """
    dates = pd.to_datetime([
        "2024-01-01",
        "2024-01-01",
        "2024-01-01",
        "2024-01-01",
        "2024-01-01",
        "2024-02-01",
        "2024-02-01",
        "2024-02-01",
        "2024-02-01",
        "2024-02-01",
    ])
    tickers = ["A", "B", "C", "D", "E", "A", "B", "C", "D", "E"]

    index = pd.MultiIndex.from_arrays([dates, tickers], names=["date", "ticker"])

    data = {
        # CONSTANT: same value for all tickers in each month
        "const_feat": [10.0, 10.0, 10.0, 10.0, 10.0, 20.0, 20.0, 20.0, 20.0, 20.0],

        # NEAR_CONSTANT: very small std (below 1e-6 threshold)
        "near_const_feat": [
            1.0, 1.0 + 1e-7, 1.0, 1.0, 1.0,  # Jan: std ≈ 4.47e-8
            2.0, 2.0, 2.0 + 5e-7, 2.0, 2.0,  # Feb: std ≈ 2.24e-7
        ],

        # ALL_MISSING: all NaN values
        "all_missing_feat": [np.nan] * 10,

        # FEW_VALID: only 2 valid values per month (below MIN_VALID_COUNT=5)
        "few_valid_feat": [
            1.0, 2.0, np.nan, np.nan, np.nan,  # Jan: 2 valid values
            3.0, 4.0, np.nan, np.nan, np.nan,  # Feb: 2 valid values
        ],

        # VARIATION: real cross-sectional spread
        "real_var_feat": [
            1.0, 2.0, 3.0, 4.0, 5.0,  # Jan: std = 1.58
            10.0, 20.0, 30.0, 40.0, 50.0,  # Feb: std = 15.81
        ],
    }

    return pd.DataFrame(data, index=index)


class TestFeatureVariationDiagnostics:
    """Test suite for feature_variation_diagnostics function."""

    def test_returns_correct_structure(self, sample_panel):
        """Test that output DataFrame has correct columns and structure."""
        result = feature_variation_diagnostics(sample_panel)

        assert isinstance(result, pd.DataFrame)
        expected_columns = [
            "date", "feature", "verdict", "unique_count", "std", "coverage",
            "valid_count", "reason",
        ]
        assert list(result.columns) == expected_columns

    def test_detects_constant_features(self, sample_panel):
        """Test CONSTANT verdict for month-constant features."""
        result = feature_variation_diagnostics(sample_panel)

        const_rows = result[result["feature"] == "const_feat"]
        assert len(const_rows) == 2  # One per month

        for _, row in const_rows.iterrows():
            assert row["verdict"] == VERDICT_CONSTANT
            assert row["unique_count"] == 1
            assert row["std"] == 0.0
            assert row["coverage"] == 1.0
            assert row["valid_count"] == 5
            assert "Unique count = 1" in row["reason"]

    def test_detects_near_constant_features(self, sample_panel):
        """Test NEAR_CONSTANT verdict for features below std threshold."""
        result = feature_variation_diagnostics(sample_panel)

        near_const_rows = result[result["feature"] == "near_const_feat"]
        assert len(near_const_rows) == 2

        for _, row in near_const_rows.iterrows():
            assert row["verdict"] == VERDICT_NEAR_CONSTANT
            assert row["std"] <= NEAR_CONSTANT_STD_THRESHOLD
            assert row["coverage"] == 1.0
            assert row["valid_count"] == 5
            assert "threshold" in row["reason"].lower()

    def test_detects_all_missing_features(self, sample_panel):
        """Test ALL_MISSING verdict for features with zero coverage."""
        result = feature_variation_diagnostics(sample_panel)

        all_missing_rows = result[result["feature"] == "all_missing_feat"]
        assert len(all_missing_rows) == 2

        for _, row in all_missing_rows.iterrows():
            assert row["verdict"] == VERDICT_ALL_MISSING
            assert row["unique_count"] == 0
            assert pd.isna(row["std"])
            assert row["coverage"] == 0.0
            assert row["valid_count"] == 0
            assert "No valid values" in row["reason"]

    def test_detects_few_valid_features(self, sample_panel):
        """Test FEW_VALID verdict for features below minimum valid count."""
        result = feature_variation_diagnostics(sample_panel)

        few_valid_rows = result[result["feature"] == "few_valid_feat"]
        assert len(few_valid_rows) == 2

        for _, row in few_valid_rows.iterrows():
            assert row["verdict"] == VERDICT_FEW_VALID
            assert row["valid_count"] < MIN_VALID_COUNT
            assert row["coverage"] < 1.0
            assert "min_valid" in row["reason"].lower()

    def test_detects_variation_features(self, sample_panel):
        """Test VARIATION verdict for features with real cross-sectional spread."""
        result = feature_variation_diagnostics(sample_panel)

        var_rows = result[result["feature"] == "real_var_feat"]
        assert len(var_rows) == 2

        for _, row in var_rows.iterrows():
            assert row["verdict"] == VERDICT_VARIATION
            assert row["std"] > NEAR_CONSTANT_STD_THRESHOLD
            assert row["valid_count"] >= MIN_VALID_COUNT
            assert row["coverage"] == 1.0
            assert "Real variation" in row["reason"]

    def test_sorted_output_ordering(self, sample_panel):
        """Test that output is deterministically sorted by date, feature, verdict."""
        result = feature_variation_diagnostics(sample_panel)

        # Check sorting is correct: date -> feature -> verdict
        dates = result["date"].tolist()
        features = result["feature"].tolist()
        verdicts = result["verdict"].tolist()

        # Should be sorted in ascending order
        for i in range(len(result) - 1):
            # Date comparison
            if dates[i] != dates[i + 1]:
                assert dates[i] < dates[i + 1], f"Row {i} not sorted by date"
                continue

            # Same date: check feature
            if features[i] != features[i + 1]:
                assert features[i] < features[i + 1], f"Row {i} not sorted by feature"
                continue

            # Same date and feature: check verdict
            assert verdicts[i] <= verdicts[i + 1], f"Row {i} not sorted by verdict"

    def test_input_validation_empty_dataframe(self):
        """Test that empty DataFrame raises ValueError."""
        empty_df = pd.DataFrame()
        with pytest.raises(ValueError, match="must have MultiIndex"):
            feature_variation_diagnostics(empty_df)

    def test_input_validation_none(self):
        """Test that None input raises ValueError."""
        with pytest.raises(ValueError, match="must not be None"):
            feature_variation_diagnostics(None)  # type: ignore

    def test_input_validation_no_multiindex(self):
        """Test that DataFrame without MultiIndex raises ValueError."""
        df = pd.DataFrame({"feat": [1, 2, 3]})
        with pytest.raises(ValueError, match="must have MultiIndex"):
            feature_variation_diagnostics(df)

    def test_input_validation_wrong_index_levels(self):
        """Test that DataFrame with wrong number of index levels raises ValueError."""
        index = pd.MultiIndex.from_arrays([[1, 2], ["A", "B"], ["X", "Y"]])
        df = pd.DataFrame({"feat": [1, 2]}, index=index)
        with pytest.raises(ValueError, match="exactly 2 levels"):
            feature_variation_diagnostics(df)

    def test_input_validation_non_datetime_date_level(self):
        """Test that non-DatetimeIndex date level raises ValueError."""
        index = pd.MultiIndex.from_arrays([[1, 2], ["A", "B"]], names=["date", "ticker"])
        df = pd.DataFrame({"feat": [1, 2]}, index=index)
        with pytest.raises(ValueError, match="must be DatetimeIndex"):
            feature_variation_diagnostics(df)

    def test_input_validation_no_features(self):
        """Test that DataFrame with no feature columns raises ValueError."""
        dates = pd.to_datetime(["2024-01-01", "2024-01-01"])
        tickers = ["A", "B"]
        index = pd.MultiIndex.from_arrays([dates, tickers], names=["date", "ticker"])
        df = pd.DataFrame(index=index)  # No columns
        with pytest.raises(ValueError, match="at least one feature column"):
            feature_variation_diagnostics(df)

    def test_custom_thresholds(self, sample_panel):
        """Test that custom thresholds are respected."""
        # Use a very LOW std threshold - should classify NEAR_CONSTANT as VARIATION
        result = feature_variation_diagnostics(
            sample_panel,
            near_constant_std_threshold=1e-10,  # Much lower than default
        )

        near_const_rows = result[result["feature"] == "near_const_feat"]
        assert len(near_const_rows) == 2

        # With very low threshold, these should now be VARIATION (their std > 1e-10)
        for _, row in near_const_rows.iterrows():
            assert row["verdict"] == VERDICT_VARIATION
            assert row["std"] > 1e-10  # Still above our very low threshold

    def test_single_value_std_handling(self):
        """Test that single value produces std=0 (CONSTANT)."""
        dates = pd.to_datetime(["2024-01-01", "2024-01-01", "2024-01-01"])
        tickers = ["A", "B", "C"]
        index = pd.MultiIndex.from_arrays([dates, tickers], names=["date", "ticker"])

        # Only one unique value
        data = {"single_val": [5.0, 5.0, 5.0]}
        df = pd.DataFrame(data, index=index)

        result = feature_variation_diagnostics(df)
        assert len(result) == 1
        row = result.iloc[0]
        assert row["verdict"] == VERDICT_CONSTANT
        assert row["std"] == 0.0
        assert row["unique_count"] == 1

    def test_two_values_unique_count(self):
        """Test that two distinct values produce unique_count=2."""
        dates = pd.to_datetime(["2024-01-01", "2024-01-01", "2024-01-01"])
        tickers = ["A", "B", "C"]
        index = pd.MultiIndex.from_arrays([dates, tickers], names=["date", "ticker"])

        # Two unique values
        data = {"two_val": [5.0, 5.0, 7.0]}
        df = pd.DataFrame(data, index=index)

        result = feature_variation_diagnostics(df)
        assert len(result) == 1
        row = result.iloc[0]
        assert row["unique_count"] == 2

    def test_does_not_modify_input(self, sample_panel):
        """Test that function does not modify the input DataFrame."""
        original = sample_panel.copy()
        feature_variation_diagnostics(sample_panel)
        pd.testing.assert_frame_equal(sample_panel, original)

    def test_multiple_dates_stable_sorting(self):
        """Test deterministic sorting across multiple dates."""
        dates = pd.to_datetime([
            "2024-03-01", "2024-03-01",
            "2024-01-01", "2024-01-01",
            "2024-02-01", "2024-02-01",
        ])
        tickers = ["A", "B"] * 3
        index = pd.MultiIndex.from_arrays([dates, tickers], names=["date", "ticker"])

        data = {
            "feat_z": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            "feat_a": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        }
        df = pd.DataFrame(data, index=index)

        result = feature_variation_diagnostics(df)

        # Should be sorted: 2024-01-01 -> feat_a, feat_z (alphabetical)
        #                  2024-02-01 -> feat_a, feat_z
        #                  2024-03-01 -> feat_a, feat_z
        assert result.iloc[0]["date"] == pd.Timestamp("2024-01-01")
        assert result.iloc[0]["feature"] == "feat_a"
        assert result.iloc[1]["date"] == pd.Timestamp("2024-01-01")
        assert result.iloc[1]["feature"] == "feat_z"

    def test_coverage_calculation(self):
        """Test coverage calculation for partial missing data."""
        dates = pd.to_datetime(["2024-01-01"] * 10)
        tickers = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]
        index = pd.MultiIndex.from_arrays([dates, tickers], names=["date", "ticker"])

        # 7 valid out of 10 = 0.7 coverage
        data = {"partial": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, np.nan, np.nan, np.nan]}
        df = pd.DataFrame(data, index=index)

        result = feature_variation_diagnostics(df)
        assert len(result) == 1
        row = result.iloc[0]
        assert row["coverage"] == 0.7
        assert row["valid_count"] == 7

    def test_deterministic_output_same_input(self, sample_panel):
        """Test that identical input produces identical output (determinism)."""
        result1 = feature_variation_diagnostics(sample_panel)
        result2 = feature_variation_diagnostics(sample_panel)

        pd.testing.assert_frame_equal(result1, result2)
