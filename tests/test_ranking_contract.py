"""Tests for ranking_contract module — leakage guards and invariants.

All tests use synthetic/labeled fixtures. No real data, no network, no model training.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aionis.eval.ranking_contract import (
    LightGBMRankingObjective,
    RankingReasonCode,
    construct_month_groups,
    filter_valid_ranking_samples,
    fit_monthly_bins,
    get_group_sizes,
    transform_to_relevance,
    validate_objective,
)

# ---------------------------------------------------------------------------
# Test validate_objective
# ---------------------------------------------------------------------------


def test_validate_objective_valid() -> None:
    """Test that valid objectives are accepted."""
    assert validate_objective("lambdarank") == LightGBMRankingObjective.LAMBDARANK
    assert validate_objective("rank_xendcg") == LightGBMRankingObjective.RANK_XENDCG


def test_validate_objective_invalid() -> None:
    """Test that invalid objectives are rejected with clear error."""
    with pytest.raises(ValueError, match="Invalid ranking objective"):
        validate_objective("rank_net")

    with pytest.raises(ValueError, match="Invalid ranking objective"):
        validate_objective("rank_pairwise")

    with pytest.raises(ValueError, match="Invalid ranking objective"):
        validate_objective("mse")


# ---------------------------------------------------------------------------
# Hand-computed monthly fixture for testing
# ---------------------------------------------------------------------------


@pytest.fixture
def monthly_panel() -> tuple[pd.Series, np.ndarray, pd.DatetimeIndex]:
    """Hand-computed monthly panel: 3 months, 5 stocks each.

    Month 2020-01 (group_id=24240): returns [0.01, 0.02, 0.03, 0.04, 0.05]
    Month 2020-02 (group_id=24241): returns [-0.02, -0.01, 0.00, 0.01, 0.02]
    Month 2020-03 (group_id=24242): returns [0.10, 0.15, 0.20, 0.25, 0.30]

    Expected quintile edges (20% steps):
    - 2020-01: [0.01, 0.02, 0.03, 0.04, 0.05] (5 unique values)
    - 2020-02: [-0.02, -0.01, 0.00, 0.01, 0.02] (5 unique values)
    - 2020-03: [0.10, 0.15, 0.20, 0.25, 0.30] (5 unique values)
    """
    dates = pd.to_datetime([
        "2020-01-15",
        "2020-01-15",
        "2020-01-15",
        "2020-01-15",
        "2020-01-15",
        "2020-02-15",
        "2020-02-15",
        "2020-02-15",
        "2020-02-15",
        "2020-02-15",
        "2020-03-15",
        "2020-03-15",
        "2020-03-15",
        "2020-03-15",
        "2020-03-15",
    ])

    returns = pd.Series([
        0.01,
        0.02,
        0.03,
        0.04,
        0.05,  # 2020-01
        -0.02,
        -0.01,
        0.00,
        0.01,
        0.02,  # 2020-02
        0.10,
        0.15,
        0.20,
        0.25,
        0.30,  # 2020-03
    ])

    groups = construct_month_groups(dates)

    return returns, groups, dates


# ---------------------------------------------------------------------------
# Test construct_month_groups
# ---------------------------------------------------------------------------


def test_construct_month_groups(
    monthly_panel: tuple[pd.Series, np.ndarray, pd.DatetimeIndex],
) -> None:
    """Test month group construction from dates."""
    returns, groups, dates = monthly_panel

    # Expected group IDs: year*12 + (month-1)
    expected_groups = np.array([
        24240,  # 2020-01: 2020*12 + 0
        24240,
        24240,
        24240,
        24240,
        24241,  # 2020-02: 2020*12 + 1
        24241,
        24241,
        24241,
        24241,
        24242,  # 2020-03: 2020*12 + 2
        24242,
        24242,
        24242,
        24242,
    ])

    assert np.array_equal(groups, expected_groups)
    assert len(np.unique(groups)) == 3  # 3 months


def test_construct_month_groups_empty() -> None:
    """Test that empty dates raise error."""
    with pytest.raises(ValueError, match="dates cannot be empty"):
        construct_month_groups(pd.DatetimeIndex([]))


# ---------------------------------------------------------------------------
# Test get_group_sizes
# ---------------------------------------------------------------------------


def test_get_group_sizes(monthly_panel: tuple[pd.Series, np.ndarray, pd.DatetimeIndex]) -> None:
    """Test group size computation."""
    returns, groups, dates = monthly_panel

    group_sizes = get_group_sizes(groups)

    # Each month has 5 stocks
    assert np.array_equal(group_sizes, np.array([5, 5, 5]))


def test_get_group_sizes_empty() -> None:
    """Test that empty groups raise error."""
    with pytest.raises(ValueError, match="groups cannot be empty"):
        get_group_sizes(np.array([]))


def test_get_group_sizes_unsorted() -> None:
    """Test that unsorted group IDs raise error."""
    unsorted_groups = np.array([2, 0, 1, 2])

    with pytest.raises(ValueError, match="Group IDs must be sorted"):
        get_group_sizes(unsorted_groups)


# ---------------------------------------------------------------------------
# Test fit_monthly_bins
# ---------------------------------------------------------------------------


def test_fit_monthly_bins_quintiles(
    monthly_panel: tuple[pd.Series, np.ndarray, pd.DatetimeIndex],
) -> None:
    """Test per-month quintile binning (n_bins=5)."""
    returns, groups, dates = monthly_panel

    fitted_bins = fit_monthly_bins(returns, groups, n_bins=5)

    # Should have 3 months worth of bins
    assert len(fitted_bins) == 3

    # Check 2020-01 (24240): quintile edges at 0%, 20%, 40%, 60%, 80%, 100%
    # With 5 values, quantiles should be close to the values themselves
    month_24240_edges = fitted_bins[24240]
    assert month_24240_edges[0] == pytest.approx(0.01, abs=1e-6)  # min
    assert month_24240_edges[-1] == pytest.approx(0.05, abs=1e-6)  # max
    assert len(month_24240_edges) == 6  # n_bins + 1

    # Check 2020-02 (24241): quintile edges
    month_24241_edges = fitted_bins[24241]
    assert month_24241_edges[0] == pytest.approx(-0.02, abs=1e-6)  # min
    assert month_24241_edges[-1] == pytest.approx(0.02, abs=1e-6)  # max
    assert len(month_24241_edges) == 6  # n_bins + 1

    # Check 2020-03 (24242): quintile edges
    month_24242_edges = fitted_bins[24242]
    assert month_24242_edges[0] == pytest.approx(0.10, abs=1e-6)  # min
    assert month_24242_edges[-1] == pytest.approx(0.30, abs=1e-6)  # max
    assert len(month_24242_edges) == 6  # n_bins + 1


def test_fit_monthly_bins_deciles(
    monthly_panel: tuple[pd.Series, np.ndarray, pd.DatetimeIndex],
) -> None:
    """Test per-month decile binning (n_bins=10)."""
    returns, groups, dates = monthly_panel

    fitted_bins = fit_monthly_bins(returns, groups, n_bins=10)

    assert len(fitted_bins) == 3

    # Each month should have 11 edges (n_bins + 1)
    for _month_id, edges in fitted_bins.items():
        assert len(edges) == 11


def test_fit_monthly_bins_empty() -> None:
    """Test that empty returns raise error."""
    with pytest.raises(ValueError, match="train_returns cannot be empty"):
        fit_monthly_bins(pd.Series([]), np.array([]), n_bins=5)


def test_fit_monthly_bins_length_mismatch() -> None:
    """Test that length mismatch raises error."""
    returns = pd.Series([0.01, 0.02, 0.03])
    groups = np.array([24240, 24241])  # Wrong length

    with pytest.raises(ValueError, match="length mismatch"):
        fit_monthly_bins(returns, groups, n_bins=5)


def test_fit_monthly_bins_invalid_n_bins() -> None:
    """Test that invalid n_bins raises error."""
    returns = pd.Series([0.01, 0.02, 0.03])
    groups = np.array([24240, 24240, 24240])

    with pytest.raises(ValueError, match="n_bins must be 5 or 10"):
        fit_monthly_bins(returns, groups, n_bins=3)  # Invalid

    with pytest.raises(ValueError, match="n_bins must be 5 or 10"):
        fit_monthly_bins(returns, groups, n_bins=7)  # Invalid


def test_fit_monthly_bins_all_nan() -> None:
    """Test that all-NaN returns raise error."""
    returns = pd.Series([np.nan, np.nan, np.nan])
    groups = np.array([24240, 24240, 24240])

    with pytest.raises(ValueError, match="no valid"):
        fit_monthly_bins(returns, groups, n_bins=5)


# ---------------------------------------------------------------------------
# Test transform_to_relevance
# ---------------------------------------------------------------------------


def test_transform_to_relevance_quintiles(
    monthly_panel: tuple[pd.Series, np.ndarray, pd.DatetimeIndex],
) -> None:
    """Test transform with quintiles on train fold."""
    returns, groups, dates = monthly_panel

    # Fit on train fold
    fitted_bins = fit_monthly_bins(returns, groups, n_bins=5)

    # Transform train fold (should be within range)
    relevance, reason_codes = transform_to_relevance(
        returns, groups, fitted_bins, n_bins=5
    )

    # All samples should have valid relevance (1-5)
    assert np.all(relevance >= 1)
    assert np.all(relevance <= 5)

    # All should be NORMAL
    assert all(rc == RankingReasonCode.NORMAL.value for rc in reason_codes)

    # Check hand-computed case: 0.01 in 2020-01 should map to relevance 1 (lowest quintile)
    assert relevance[0] == 1

    # Check hand-computed case: 0.05 in 2020-01 should map to relevance 5 (highest quintile)
    assert relevance[4] == 5


def test_transform_to_relevance_out_of_range_clamp() -> None:
    """Test out-of-range clamping with reason codes."""
    # Train fold: 2020-01 with returns [0.01, 0.02, 0.03, 0.04, 0.05]
    train_dates = pd.to_datetime(["2020-01-15"] * 5)
    train_returns = pd.Series([0.01, 0.02, 0.03, 0.04, 0.05])
    train_groups = construct_month_groups(train_dates)

    fitted_bins = fit_monthly_bins(train_returns, train_groups, n_bins=5)

    # Test fold: same month, but extreme values
    test_dates = pd.to_datetime(["2020-01-15", "2020-01-15", "2020-01-15"])
    test_returns = pd.Series([-0.10, 0.03, 0.20])  # -0.10 below min, 0.20 above max
    test_groups = construct_month_groups(test_dates)

    relevance, reason_codes = transform_to_relevance(
        test_returns, test_groups, fitted_bins, n_bins=5
    )

    # -0.10 should clamp to relevance 1 (lowest) with OUT_OF_RANGE_LOW
    assert relevance[0] == 1
    assert reason_codes[0] == RankingReasonCode.OUT_OF_RANGE_LOW.value

    # 0.03 should be normal (within range)
    assert relevance[1] >= 2 and relevance[1] <= 4
    assert reason_codes[1] == RankingReasonCode.NORMAL.value

    # 0.20 should clamp to relevance 5 (highest) with OUT_OF_RANGE_HIGH
    assert relevance[2] == 5
    assert reason_codes[2] == RankingReasonCode.OUT_OF_RANGE_HIGH.value


def test_transform_to_relevance_nan_returns() -> None:
    """Test NaN return handling."""
    dates = pd.to_datetime(["2020-01-15", "2020-01-15", "2020-01-15"])
    returns = pd.Series([0.01, np.nan, 0.05])
    groups = construct_month_groups(dates)

    # Fit on non-NaN data
    train_dates = pd.to_datetime(["2020-01-15"] * 2)
    train_returns = pd.Series([0.01, 0.05])
    train_groups = construct_month_groups(train_dates)

    fitted_bins = fit_monthly_bins(train_returns, train_groups, n_bins=5)

    # Transform with NaN
    relevance, reason_codes = transform_to_relevance(
        returns, groups, fitted_bins, n_bins=5
    )

    # First sample should be normal
    assert relevance[0] >= 1 and relevance[0] <= 5
    assert reason_codes[0] == RankingReasonCode.NORMAL.value

    # Second sample (NaN) should have relevance -1 and RETURN_MISSING
    assert relevance[1] == -1
    assert reason_codes[1] == RankingReasonCode.RETURN_MISSING.value

    # Third sample should be normal
    assert relevance[2] >= 1 and relevance[2] <= 5
    assert reason_codes[2] == RankingReasonCode.NORMAL.value


def test_transform_to_relevance_unseen_month() -> None:
    """Test unseen month handling with pooled edges."""
    # Train fold: only 2020-01
    train_dates = pd.to_datetime(["2020-01-15"] * 5)
    train_returns = pd.Series([0.01, 0.02, 0.03, 0.04, 0.05])
    train_groups = construct_month_groups(train_dates)

    fitted_bins = fit_monthly_bins(train_returns, train_groups, n_bins=5)

    # Test fold: 2020-02 (not in train fold)
    test_dates = pd.to_datetime(["2020-02-15"] * 3)
    test_returns = pd.Series([0.015, 0.025, 0.035])
    test_groups = construct_month_groups(test_dates)

    relevance, reason_codes = transform_to_relevance(
        test_returns, test_groups, fitted_bins, n_bins=5
    )

    # All should have valid relevance (using pooled edges)
    assert np.all(relevance >= 1)
    assert np.all(relevance <= 5)

    # All should have UNSEEN_MONTH_POOLED reason
    assert all(rc == RankingReasonCode.UNSEEN_MONTH_POOLED.value for rc in reason_codes)


def test_transform_to_relevance_empty_fitted_bins() -> None:
    """Test that empty fitted_bins raise error."""
    returns = pd.Series([0.01, 0.02])
    groups = np.array([24240, 24240])

    with pytest.raises(ValueError, match="fitted_bins cannot be empty"):
        transform_to_relevance(returns, groups, {}, n_bins=5)


def test_transform_to_relevance_length_mismatch() -> None:
    """Test that length mismatch raises error."""
    returns = pd.Series([0.01, 0.02])
    groups = np.array([24240])

    fitted_bins = {24240: np.array([0.0, 0.05, 0.10])}

    with pytest.raises(ValueError, match="length mismatch"):
        transform_to_relevance(returns, groups, fitted_bins, n_bins=5)


# ---------------------------------------------------------------------------
# Test filter_valid_ranking_samples
# ---------------------------------------------------------------------------


def test_filter_valid_ranking_samples() -> None:
    """Test filtering NaN-return samples."""
    returns = pd.Series([0.01, np.nan, 0.03, np.nan, 0.05])
    relevance = np.array([1, -1, 3, -1, 5])
    groups = np.array([24240, 24240, 24240, 24240, 24240])

    returns_clean, relevance_clean, groups_clean = filter_valid_ranking_samples(
        returns, relevance, groups
    )

    # Should have 3 valid samples
    assert len(returns_clean) == 3
    assert len(relevance_clean) == 3
    assert len(groups_clean) == 3

    # Check that we kept the right samples
    assert np.array_equal(returns_clean.values, pd.Series([0.01, 0.03, 0.05]))
    assert np.array_equal(relevance_clean, np.array([1, 3, 5]))
    assert np.array_equal(groups_clean, np.array([24240, 24240, 24240]))


def test_filter_valid_ranking_samples_all_nan() -> None:
    """Test that all-NaN returns raise error."""
    returns = pd.Series([np.nan, np.nan])
    relevance = np.array([-1, -1])
    groups = np.array([24240, 24240])

    with pytest.raises(ValueError, match="No valid samples"):
        filter_valid_ranking_samples(returns, relevance, groups)


def test_filter_valid_ranking_samples_length_mismatch() -> None:
    """Test that length mismatch raises error."""
    returns = pd.Series([0.01, 0.02])
    relevance = np.array([1])
    groups = np.array([24240, 24240])

    with pytest.raises(ValueError, match="same length"):
        filter_valid_ranking_samples(returns, relevance, groups)


# ---------------------------------------------------------------------------
# LEAKAGE INVARIANTS (the crux of the contract)
# ---------------------------------------------------------------------------


def test_month_permutation_invariance() -> None:
    """Test: Permuting month order does not change bin edges."""
    # Create dataset with 3 months
    dates = pd.to_datetime([
        "2020-01-15",
        "2020-01-15",
        "2020-02-15",
        "2020-02-15",
        "2020-03-15",
        "2020-03-15",
    ])
    returns = pd.Series([0.01, 0.05, -0.02, 0.02, 0.10, 0.30])
    groups = construct_month_groups(dates)

    # Fit on original order
    fitted_bins_original = fit_monthly_bins(returns, groups, n_bins=5)

    # Permute the order (shuffle rows)
    np.random.seed(0)  # H6 determinism
    perm_idx = np.random.permutation(len(returns))
    returns_perm = returns.iloc[perm_idx]
    groups_perm = groups[perm_idx]

    # Fit on permuted order
    fitted_bins_permuted = fit_monthly_bins(returns_perm, groups_perm, n_bins=5)

    # Assert: bin edges for each month are IDENTICAL
    for month_id in fitted_bins_original:
        assert month_id in fitted_bins_permuted
        assert np.allclose(
            fitted_bins_original[month_id],
            fitted_bins_permuted[month_id],
            rtol=1e-10,
        ), f"Month {month_id} bin edges changed after permutation"

    # Should have same months
    assert len(fitted_bins_original) == len(fitted_bins_permuted)


def test_future_truncation_invariance() -> None:
    """Test: Removing future months does not change past months' bin edges."""
    # Create dataset with 6 months
    dates = pd.to_datetime([
        "2020-01-15",
        "2020-01-15",
        "2020-02-15",
        "2020-02-15",
        "2020-03-15",
        "2020-03-15",
        "2020-04-15",
        "2020-04-15",
        "2020-05-15",
        "2020-05-15",
        "2020-06-15",
        "2020-06-15",
    ])
    returns = pd.Series([
        0.01,
        0.05,
        -0.02,
        0.02,
        0.10,
        0.30,
        0.15,
        0.25,
        -0.05,
        0.08,
        0.12,
        0.18,
    ])
    groups = construct_month_groups(dates)

    # Fit on full dataset
    fitted_bins_full = fit_monthly_bins(returns, groups, n_bins=5)

    # Truncate: remove last 2 months (2020-05, 2020-06)
    max_month = groups.max()
    trunc_months = max_month - 2  # Remove last 2 months
    trunc_mask = groups <= trunc_months
    returns_trunc = returns[trunc_mask]
    groups_trunc = groups[trunc_mask]

    # Fit on truncated dataset
    fitted_bins_trunc = fit_monthly_bins(returns_trunc, groups_trunc, n_bins=5)

    # Assert: bin edges for retained months (2020-01, 2020-02, 2020-03, 2020-04) are IDENTICAL
    for month_id in fitted_bins_trunc:
        assert month_id in fitted_bins_full
        assert np.allclose(
            fitted_bins_full[month_id],
            fitted_bins_trunc[month_id],
            rtol=1e-10,
        ), f"Month {month_id} bin edges changed after truncating future months"

    # Truncated fit should have fewer months
    assert len(fitted_bins_trunc) < len(fitted_bins_full)


def test_train_fold_only_fitting() -> None:
    """Test: transform_to_relevance never refits bin edges."""
    # Train fold: 2020-01, 2020-02
    train_dates = pd.to_datetime([
        "2020-01-15",
        "2020-01-15",
        "2020-02-15",
        "2020-02-15",
    ])
    train_returns = pd.Series([0.01, 0.05, -0.02, 0.02])
    train_groups = construct_month_groups(train_dates)

    # Fit on train fold
    fitted_bins = fit_monthly_bins(train_returns, train_groups, n_bins=5)

    # Deep copy to compare later (frozen edges must not change)
    fitted_bins_copy = {k: v.copy() for k, v in fitted_bins.items()}

    # Test fold 1: 2020-03 (different data)
    test1_dates = pd.to_datetime(["2020-03-15", "2020-03-15"])
    test1_returns = pd.Series([0.10, 0.30])
    test1_groups = construct_month_groups(test1_dates)

    relevance1, _ = transform_to_relevance(
        test1_returns, test1_groups, fitted_bins, n_bins=5
    )

    # Assert: fitted_bins object unchanged (same values, no modification)
    for month_id in fitted_bins_copy:
        if month_id in fitted_bins:
            assert np.allclose(
                fitted_bins[month_id],
                fitted_bins_copy[month_id],
                rtol=1e-10,
            ), f"Bin edges for month {month_id} were modified during transform"

    # Test fold 2: very different data (extreme values)
    test2_dates = pd.to_datetime(["2020-03-15", "2020-03-15"])
    test2_returns = pd.Series([-100.0, 100.0])  # Extreme values
    test2_groups = construct_month_groups(test2_dates)

    relevance2, _ = transform_to_relevance(
        test2_returns, test2_groups, fitted_bins, n_bins=5
    )

    # Assert: fitted_bins STILL unchanged
    for month_id in fitted_bins_copy:
        if month_id in fitted_bins:
            assert np.allclose(
                fitted_bins[month_id],
                fitted_bins_copy[month_id],
                rtol=1e-10,
            ), f"Bin edges for month {month_id} were modified during second transform"

    # Transform should produce different relevance for different inputs
    # (proves it's actually transforming, not just returning constant)
    assert not np.array_equal(relevance1, relevance2)


def test_group_size_stability() -> None:
    """Test: Filtering NaN returns updates group sizes correctly."""
    # Create dataset with 2 months, some NaN returns
    dates = pd.to_datetime([
        "2020-01-15",
        "2020-01-15",
        "2020-01-15",
        "2020-01-15",
        "2020-01-15",
        "2020-02-15",
        "2020-02-15",
        "2020-02-15",
    ])
    returns = pd.Series([0.01, np.nan, 0.03, 0.04, 0.05, np.nan, 0.02, 0.08])
    groups = construct_month_groups(dates)

    # Transform to relevance
    fitted_bins = fit_monthly_bins(
        returns[~pd.isna(returns)], groups[~pd.isna(returns)], n_bins=5
    )
    relevance, _ = transform_to_relevance(
        returns, groups, fitted_bins, n_bins=5
    )

    # Count samples per group BEFORE filtering
    unique_groups, counts_before = np.unique(groups, return_counts=True)

    # Filter NaN returns
    returns_clean, relevance_clean, groups_clean = filter_valid_ranking_samples(
        returns, relevance, groups
    )

    # Count samples per group AFTER filtering
    _, counts_after = np.unique(groups_clean, return_counts=True)

    # Assert: no group has MORE samples after filtering
    for i, group_id in enumerate(unique_groups):
        before = counts_before[i]
        # Find this group in after-counts
        after_idx = np.where(np.unique(groups_clean) == group_id)[0]
        after = counts_after[after_idx][0] if len(after_idx) > 0 else 0

        assert after <= before, (
            f"Group {group_id} has {after} samples after filtering, "
            f"but had {before} before (filtering increased count!)"
        )

    # Total samples should decrease
    assert len(groups_clean) < len(groups)

    # Sum of group sizes should equal total row count
    group_sizes_after = get_group_sizes(groups_clean)
    assert np.sum(group_sizes_after) == len(groups_clean)


def test_group_size_stability_with_all_valid() -> None:
    """Test group size stability when all samples are valid."""
    # All valid samples
    dates = pd.to_datetime(["2020-01-15", "2020-01-15", "2020-02-15", "2020-02-15"])
    returns = pd.Series([0.01, 0.05, -0.02, 0.02])
    groups = construct_month_groups(dates)

    fitted_bins = fit_monthly_bins(returns, groups, n_bins=5)
    relevance, _ = transform_to_relevance(returns, groups, fitted_bins, n_bins=5)

    returns_clean, relevance_clean, groups_clean = filter_valid_ranking_samples(
        returns, relevance, groups
    )

    # Should have same number of samples
    assert len(returns_clean) == len(returns)
    assert len(groups_clean) == len(groups)

    # Group sizes should be identical
    group_sizes_before = get_group_sizes(groups)
    group_sizes_after = get_group_sizes(groups_clean)
    assert np.array_equal(group_sizes_before, group_sizes_after)


# ---------------------------------------------------------------------------
# Test ties policy (equal returns → same relevance)
# ---------------------------------------------------------------------------


def test_ties_equal_returns_same_relevance() -> None:
    """Test that equal returns get same relevance."""
    dates = pd.to_datetime(["2020-01-15"] * 6)
    returns = pd.Series([0.01, 0.01, 0.02, 0.02, 0.02, 0.05])
    groups = construct_month_groups(dates)

    fitted_bins = fit_monthly_bins(returns, groups, n_bins=5)
    relevance, _ = transform_to_relevance(returns, groups, fitted_bins, n_bins=5)

    # Equal returns should have same relevance
    assert relevance[0] == relevance[1]  # Both 0.01
    assert relevance[2] == relevance[3] == relevance[4]  # All 0.02


# ---------------------------------------------------------------------------
# Test both bin_count values (5 and 10)
# ---------------------------------------------------------------------------


def test_bin_count_parameter() -> None:
    """Test that bin_count is a parameter, not hardcoded."""
    dates = pd.to_datetime(["2020-01-15"] * 10)
    returns = pd.Series([
        0.01,
        0.02,
        0.03,
        0.04,
        0.05,
        0.06,
        0.07,
        0.08,
        0.09,
        0.10,
    ])
    groups = construct_month_groups(dates)

    # Quintiles (5 bins)
    fitted_bins_5 = fit_monthly_bins(returns, groups, n_bins=5)
    relevance_5, _ = transform_to_relevance(returns, groups, fitted_bins_5, n_bins=5)

    # Should have 5 bins
    assert np.max(relevance_5) <= 5
    assert len(fitted_bins_5[groups[0]]) == 6  # n_bins + 1

    # Deciles (10 bins)
    fitted_bins_10 = fit_monthly_bins(returns, groups, n_bins=10)
    relevance_10, _ = transform_to_relevance(returns, groups, fitted_bins_10, n_bins=10)

    # Should have 10 bins
    assert np.max(relevance_10) <= 10
    assert len(fitted_bins_10[groups[0]]) == 11  # n_bins + 1


# ---------------------------------------------------------------------------
# Test error handling
# ---------------------------------------------------------------------------


def test_validate_objective_case_sensitive() -> None:
    """Test that objective validation is case-sensitive."""
    with pytest.raises(ValueError, match="Invalid ranking objective"):
        validate_objective("LAMBDARANK")  # Uppercase

    with pytest.raises(ValueError, match="Invalid ranking objective"):
        validate_objective("LambdaRank")  # Mixed case


def test_construct_month_groups_with_nat() -> None:
    """Test that NaT dates are handled."""
    # NaT should still produce a group ID (even if invalid)
    dates = pd.to_datetime(["2020-01-15", None, "2020-02-15"])

    # Should not raise error, but NaT produces invalid group
    groups = construct_month_groups(dates)
    assert len(groups) == 3
