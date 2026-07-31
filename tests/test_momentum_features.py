"""
Tests for momentum/reversal feature kernel with hand-computed oracle fixtures.

All fixture values are manually computed to verify the frozen formulas.
"""

import numpy as np
import pandas as pd
import pytest

from aionis.features.momentum import (
    compute_momentum_features,
    momentum_12_1,
    reversal_1m,
    vol_adj_mom,
)


class TestMomentum121:
    """Test 12-1 momentum: close[t-1] / close[t-12] - 1."""

    def test_hand_computed_basic(self):
        """Hand-computed: [100, ..., 125] → 125/100-1 = 0.25."""
        prices = pd.Series([100.0, 102.0, 105.0, 103.0, 108.0, 110.0,
                           112.0, 115.0, 118.0, 120.0, 122.0, 125.0])
        result = momentum_12_1(prices)
        expected = 125.0 / 100.0 - 1.0  # = 0.25
        assert np.isclose(result, expected), f"Expected {expected}, got {result}"

    def test_insufficient_length(self):
        """Less than 12 prices → NaN."""
        prices = pd.Series([100.0, 105.0, 110.0])
        result = momentum_12_1(prices)
        assert np.isnan(result), f"Expected NaN for insufficient length, got {result}"

    def test_missing_month_in_window(self):
        """Gap in required 12-month window → NaN."""
        # Have 13 prices but a gap at position -6 (t-7)
        prices = pd.Series([100.0, 102.0, 105.0, 103.0, 108.0, 110.0,
                           np.nan, 115.0, 118.0, 120.0, 122.0, 125.0, 128.0])
        result = momentum_12_1(prices)
        assert np.isnan(result), f"Expected NaN for missing month, got {result}"

    def test_non_positive_price(self):
        """Zero or negative price in window → NaN."""
        prices = pd.Series([100.0, 102.0, 105.0, 103.0, 108.0, 110.0,
                           0.0, 115.0, 118.0, 120.0, 122.0, 125.0])
        result = momentum_12_1(prices)
        assert np.isnan(result), f"Expected NaN for zero price, got {result}"

    def test_infinite_price(self):
        """Inf in window → NaN."""
        prices = pd.Series([100.0, 102.0, 105.0, 103.0, 108.0, 110.0,
                           112.0, np.inf, 118.0, 120.0, 122.0, 125.0])
        result = momentum_12_1(prices)
        assert np.isnan(result), f"Expected NaN for infinite price, got {result}"

    def test_pit_truncation_invariance(self):
        """Truncating future months preserves past outputs."""
        full_prices = pd.Series([100.0, 102.0, 105.0, 103.0, 108.0, 110.0,
                                 112.0, 115.0, 118.0, 120.0, 122.0, 125.0,
                                 128.0, 130.0])
        # Compute with first 12 prices (t=12)
        result_12 = momentum_12_1(full_prices.iloc[:12])
        # Compute with all 14 prices (t=14)
        result_14 = momentum_12_1(full_prices)
        # Both use prices[-12] and prices[-1] relative to their windows
        # First window: 100 to 125 → 0.25
        # Second window: 105 to 130 → 130/105-1
        expected_12 = 125.0 / 100.0 - 1.0
        expected_14 = 130.0 / 105.0 - 1.0
        assert np.isclose(result_12, expected_12)
        assert np.isclose(result_14, expected_14)
        assert not np.isclose(result_12, result_14), \
            "Different windows should give different results"


class TestReversal1m:
    """Test 1-month reversal: -(close[t] / close[t-1] - 1)."""

    def test_hand_computed_basic(self):
        """Hand-computed: [100, 105] → -(105/100-1) = -0.05."""
        prices = pd.Series([100.0, 105.0])
        result = reversal_1m(prices)
        expected = -(105.0 / 100.0 - 1.0)  # = -0.05
        assert np.isclose(result, expected), f"Expected {expected}, got {result}"

    def test_insufficient_length(self):
        """Less than 2 prices → NaN."""
        prices = pd.Series([100.0])
        result = reversal_1m(prices)
        assert np.isnan(result), f"Expected NaN for insufficient length, got {result}"

    def test_missing_t_or_t_minus_1(self):
        """Missing t or t-1 → NaN."""
        prices = pd.Series([100.0, np.nan])
        result = reversal_1m(prices)
        assert np.isnan(result), f"Expected NaN for missing t, got {result}"

    def test_non_positive_price(self):
        """Zero or negative price → NaN."""
        prices = pd.Series([0.0, 105.0])
        result = reversal_1m(prices)
        assert np.isnan(result), f"Expected NaN for zero price, got {result}"

    def test_infinite_price(self):
        """Inf → NaN."""
        prices = pd.Series([100.0, np.inf])
        result = reversal_1m(prices)
        assert np.isnan(result), f"Expected NaN for infinite price, got {result}"

    def test_pit_truncation_invariance(self):
        """Truncating future months preserves past outputs."""
        full_prices = pd.Series([100.0, 105.0, 110.0, 108.0])
        # t=2: [100, 105]
        result_t2 = reversal_1m(full_prices.iloc[:2])
        # t=4: [100, 105, 110, 108]
        result_t4 = reversal_1m(full_prices)
        expected_t2 = -(105.0 / 100.0 - 1.0)
        expected_t4 = -(108.0 / 110.0 - 1.0)
        assert np.isclose(result_t2, expected_t2)
        assert np.isclose(result_t4, expected_t4)


class TestVolAdjMom:
    """Test volatility-adjusted momentum: momentum_12_1 / std(returns)."""

    def test_hand_computed_basic(self):
        """
        Hand-computed with 13 prices.
        vol_adj_mom uses LAST 12 prices (formation window: indices 1-12).
        momentum_12_1 = 128/102-1 = 0.2549019607843137
        Returns: 11 values from price ratios, std ~0.01617, vol_adj_mom ~15.76
        """
        prices = pd.Series([100.0, 102.0, 105.0, 103.0, 108.0, 110.0,
                           112.0, 115.0, 118.0, 120.0, 122.0, 125.0, 128.0])
        result = vol_adj_mom(prices)

        # Hand-computed using LAST 12 prices (102 to 128)
        mom = 128.0 / 102.0 - 1.0  # 0.2549019607843137
        returns = [
            105.0/102.0 - 1.0,    # 0.029411764705882364
            103.0/105.0 - 1.0,    # -0.0190476190476196
            108.0/103.0 - 1.0,    # 0.04854368932038835
            110.0/108.0 - 1.0,    # 0.018518518518518517
            112.0/110.0 - 1.0,    # 0.018181818181818176
            115.0/112.0 - 1.0,    # 0.026785714285714334
            118.0/115.0 - 1.0,    # 0.02608695652173913
            120.0/118.0 - 1.0,    # 0.016949152542372881
            122.0/120.0 - 1.0,    # 0.016666666666666693
            125.0/122.0 - 1.0,    # 0.024590163934426226
            128.0/125.0 - 1.0,    # 0.024
        ]
        assert len(returns) == 11, f"Expected 11 returns, got {len(returns)}"
        std_dev = np.std(returns, ddof=1)
        expected = mom / std_dev

        assert np.isclose(result, expected, rtol=1e-10), \
            f"Expected {expected}, got {result}"

    def test_insufficient_length(self):
        """Less than 13 prices → NaN."""
        prices = pd.Series([100.0, 105.0, 110.0, 115.0, 120.0])
        result = vol_adj_mom(prices)
        assert np.isnan(result), f"Expected NaN for insufficient length, got {result}"

    def test_momentum_12_1_nan_propagates(self):
        """If momentum_12_1 is NaN, vol_adj_mom is NaN."""
        prices = pd.Series([100.0, 102.0, 105.0, 103.0, 108.0, 110.0,
                           0.0, 115.0, 118.0, 120.0, 122.0, 125.0, 128.0])
        result = vol_adj_mom(prices)
        assert np.isnan(result), f"Expected NaN when momentum_12_1 fails, got {result}"

    def test_zero_volatility(self):
        """All returns identical (std=0) → NaN."""
        # All prices identical → all returns = 0 → std = 0 exactly
        prices = pd.Series([100.0] * 13)  # 13 identical prices
        result = vol_adj_mom(prices)

        # All returns are exactly 0.0, so std is exactly 0.0
        # With std <= 0, vol_adj_mom should return NaN
        assert np.isnan(result), f"Expected NaN for zero volatility, got {result}"

    def test_negative_std(self):
        """Std can't be negative, but if computed as <=0 → NaN."""
        # This is impossible in practice (std is always >= 0)
        # But we test the guard clause
        prices = pd.Series([100.0, 102.0, 105.0, 103.0, 108.0, 110.0,
                           112.0, 115.0, 118.0, 120.0, 122.0, 125.0, 128.0])
        # First compute normally
        result_normal = vol_adj_mom(prices)
        # Should be a valid number
        assert not np.isnan(result_normal), "Normal case should not be NaN"
        # (We can't force std to be negative without mocking)

    def test_formation_window_is_last_12_prices(self):
        """vol_adj_mom MUST use LAST 12 closes (formation window), not FIRST 12."""
        # 15 prices: vol_adj_mom should use closes at indices 3-14 (last 12)
        # NOT indices 0-11 (first 12)
        prices = pd.Series([
            90.0,   # index 0 - should NOT be used (too old)
            92.0,   # index 1 - should NOT be used
            94.0,   # index 2 - should NOT be used
            100.0,  # index 3 - FIRST price of formation window (t-12)
            102.0,  # index 4
            105.0,  # index 5
            103.0,  # index 6
            108.0,  # index 7
            110.0,  # index 8
            112.0,  # index 9
            115.0,  # index 10
            118.0,  # index 11
            120.0,  # index 12
            122.0,  # index 13
            125.0,  # index 14 - LAST price of formation window (t-1)
        ])

        result = vol_adj_mom(prices)

        # Hand-compute expected using LAST 12 prices (indices 3-14)
        formation_window = prices.iloc[-12:]  # 100.0 to 125.0
        mom_expected = 125.0 / 100.0 - 1.0  # 0.25

        returns_expected = []
        for i in range(1, len(formation_window)):
            ret = formation_window.iloc[i] / formation_window.iloc[i-1] - 1.0
            returns_expected.append(ret)

        std_expected = np.std(returns_expected, ddof=1)
        expected = mom_expected / std_expected

        assert np.isclose(result, expected, rtol=1e-10), \
            f"Formation window regression: expected {expected}, got {result}"

    def test_small_positive_std_not_nan(self):
        """Small-but-positive volatility (e.g., std=1e-6) should NOT return NaN."""
        # Create prices with very small but positive variance
        # All returns are ~0.0001 (0.01%) except tiny variations
        base_return = 0.0001  # 0.01%
        prices = [100.0]
        for i in range(14):
            next_price = prices[-1] * (1 + base_return + (i * 1e-8))  # Tiny variation
            prices.append(next_price)

        prices_series = pd.Series(prices)

        result = vol_adj_mom(prices_series)

        # Should NOT be NaN - small positive std is valid
        assert not np.isnan(result), \
            f"Small positive std should not be NaN, got {result}"
        # Should be a finite number
        assert np.isfinite(result), \
            f"Small positive std should produce finite result, got {result}"


class TestBoundaryConditions:
    """Test boundary conditions: non-finite, non-positive, zero/negative std."""

    def test_nan_in_series(self):
        """NaN anywhere in required window → NaN for all features."""
        prices = pd.Series([100.0, 102.0, 105.0, np.nan, 108.0, 110.0,
                           112.0, 115.0, 118.0, 120.0, 122.0, 125.0])
        assert np.isnan(momentum_12_1(prices))

    def test_inf_in_series(self):
        """Inf anywhere → NaN."""
        prices = pd.Series([100.0, 102.0, 105.0, 103.0, 108.0, 110.0,
                           112.0, 115.0, np.inf, 120.0, 122.0, 125.0])
        assert np.isnan(momentum_12_1(prices))

    def test_negative_price(self):
        """Negative price anywhere → NaN."""
        prices = pd.Series([100.0, 102.0, 105.0, 103.0, 108.0, 110.0,
                           112.0, 115.0, -5.0, 120.0, 122.0, 125.0])
        assert np.isnan(momentum_12_1(prices))

    def test_zero_price(self):
        """Zero price anywhere → NaN."""
        prices = pd.Series([100.0, 102.0, 105.0, 103.0, 108.0, 0.0,
                           112.0, 115.0, 118.0, 120.0, 122.0, 125.0])
        assert np.isnan(momentum_12_1(prices))


class TestComputeMomentumFeatures:
    """Test the convenience function for computing multiple features."""

    def test_all_features(self):
        """Compute all three features."""
        prices = pd.Series([100.0, 102.0, 105.0, 103.0, 108.0, 110.0,
                           112.0, 115.0, 118.0, 120.0, 122.0, 125.0, 128.0])
        result = compute_momentum_features(prices)
        assert set(result.keys()) == {"momentum_12_1", "reversal_1m", "vol_adj_mom"}
        assert not np.isnan(result["momentum_12_1"])
        assert not np.isnan(result["reversal_1m"])
        assert not np.isnan(result["vol_adj_mom"])

    def test_subset_features(self):
        """Compute only requested features."""
        prices = pd.Series([100.0, 102.0, 105.0, 103.0, 108.0, 110.0,
                           112.0, 115.0, 118.0, 120.0, 122.0, 125.0, 128.0])
        result = compute_momentum_features(prices, features=["momentum_12_1", "reversal_1m"])
        assert set(result.keys()) == {"momentum_12_1", "reversal_1m"}
        assert "vol_adj_mom" not in result

    def test_unknown_feature_raises(self):
        """Requesting unknown feature raises ValueError."""
        prices = pd.Series([100.0, 105.0])
        with pytest.raises(ValueError, match="Unknown feature"):
            compute_momentum_features(prices, features=["unknown_feature"])

    def test_deterministic_same_input(self):
        """Same ordered series ⇒ identical output (deterministic)."""
        prices = pd.Series([100.0, 102.0, 105.0, 103.0, 108.0, 110.0,
                           112.0, 115.0, 118.0, 120.0, 122.0, 125.0, 128.0])
        result1 = compute_momentum_features(prices)
        result2 = compute_momentum_features(prices)
        for key in result1:
            assert result1[key] == result2[key], \
                f"Feature {key} not deterministic: {result1[key]} vs {result2[key]}"
