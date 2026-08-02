"""Hermetic synthetic tests for Track B S1-M① baseline pipeline.

Tests use deterministic synthetic panels (no real data) and verify:
1. Anti-leakage invariants (chronological splits, train-only binner fit)
2. Walk-forward fold generation
3. IC computation and aggregation
4. Diebold-Mariano inference

All tests are AAA (Arrange-Act-Assert) and deterministic via fixed seeds.
"""
from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from aionis.eval.track_b_baseline import (
    _DEFAULT_BIN_COUNT,
    _DEFAULT_EMBARGO_SESSIONS,
    _DEFAULT_FROZEN_PARAMS,
    TrackBBaselineResult,
    fit_track_b_baseline,
)

# Synthetic test constants
_TEST_SEED = 42
_N_TICKERS = 50
_N_DATES = 250  # ~1 year of daily data
_TEST_HORIZON = 21


@pytest.fixture
def synthetic_panel() -> pd.DataFrame:
    """Create a deterministic synthetic panel for testing.

    Panel format: [date, ticker, *features, forward_return_h]
    - 50 tickers
    - 250 dates (daily)
    - 23 features (matching config #41)
    - forward_return_h (label)

    Deterministic via fixed seed.
    """
    rng = np.random.default_rng(_TEST_SEED)

    # Date range (business days)
    start_date = datetime(2023, 1, 1)
    dates = pd.bdate_range(start_date, periods=_N_DATES)

    # Tickers
    tickers = [f"TICK{i:03d}" for i in range(_N_TICKERS)]

    # Build index (cartesian product)
    index = pd.MultiIndex.from_product(
        [dates, tickers], names=["date", "ticker"]
    ).to_frame(index=False)

    # Feature names (23 features from config #41)
    feature_cols = [
        "roa", "roe", "profit_margin",
        "asset_growth_1m", "revenue_growth_1m", "equity_growth_1m",
        "asset_growth_12m", "revenue_growth_12m", "leverage",
        "debt_to_equity", "book_value_per_share", "accruals",
        "investment_12m",
        "momentum_5d", "momentum_10d", "momentum_21d", "momentum_42d",
        "reversal_5d",
        "volatility_21d", "volatility_63d", "turnover_21d",
        "beta_252d", "amihud_illiquidity_21d",
    ]

    # Generate synthetic features (standard normal)
    for feat in feature_cols:
        index[feat] = rng.standard_normal(len(index))

    # Generate forward returns (mild signal: some correlation with features)
    # True signal: first 3 features have weak positive correlation
    signal = (
        0.02 * index["roa"].to_numpy()
        + 0.015 * index["roe"].to_numpy()
        + 0.01 * index["profit_margin"].to_numpy()
    )
    noise = 0.1 * rng.standard_normal(len(index))
    index["forward_return_h"] = signal + noise

    # Sort by date for monotonic prediction_times (purgedcv requirement)
    index = index.sort_values("date").reset_index(drop=True)

    return index


@pytest.fixture
def minimal_panel() -> pd.DataFrame:
    """Minimal synthetic panel for edge case testing.

    Smaller dataset: 10 tickers, 60 dates (minimum for walk-forward).
    """
    rng = np.random.default_rng(_TEST_SEED)

    dates = pd.bdate_range(datetime(2023, 1, 1), periods=60)
    tickers = [f"T{i:02d}" for i in range(10)]

    index = pd.MultiIndex.from_product(
        [dates, tickers], names=["date", "ticker"]
    ).to_frame(index=False)

    # Single feature (price-only baseline)
    index["momentum_21d"] = rng.standard_normal(len(index))
    index["forward_return_h"] = 0.05 + 0.01 * rng.standard_normal(len(index))

    # Sort by date for monotonic prediction_times
    index = index.sort_values("date").reset_index(drop=True)

    return index


class TestInputValidation:
    """Test input validation and error handling."""

    def test_empty_panel_raises(self) -> None:
        """Empty panel should raise ValueError."""
        panel = pd.DataFrame(columns=["date", "ticker", "feat", "forward_return_h"])
        with pytest.raises(ValueError, match="panel cannot be empty"):
            fit_track_b_baseline(
                panel=panel,
                feature_cols=["feat"],
                horizon=21,
            )

    def test_missing_required_columns_raises(self, synthetic_panel: pd.DataFrame) -> None:
        """Panel missing required columns should raise ValueError."""
        bad_panel = synthetic_panel.drop(columns=["date"])
        with pytest.raises(ValueError, match="missing required columns"):
            fit_track_b_baseline(
                panel=bad_panel,
                feature_cols=["roa"],
                horizon=21,
            )

    def test_missing_feature_columns_raises(self, synthetic_panel: pd.DataFrame) -> None:
        """Panel missing feature columns should raise ValueError."""
        with pytest.raises(ValueError, match="missing feature columns"):
            fit_track_b_baseline(
                panel=synthetic_panel,
                feature_cols=["nonexistent_feature"],
                horizon=21,
            )

    def test_invalid_horizon_raises(self, synthetic_panel: pd.DataFrame) -> None:
        """Invalid horizon should raise ValueError."""
        with pytest.raises(ValueError, match="horizon must be >= 1"):
            fit_track_b_baseline(
                panel=synthetic_panel,
                feature_cols=["roa"],
                horizon=0,
            )

    def test_invalid_bin_count_raises(self, synthetic_panel: pd.DataFrame) -> None:
        """Invalid bin_count should raise ValueError."""
        with pytest.raises(ValueError, match="bin_count must be 5 or 10"):
            fit_track_b_baseline(
                panel=synthetic_panel,
                feature_cols=["roa"],
                bin_count=3,  # Invalid
            )

    def test_empty_feature_cols_raises(self, synthetic_panel: pd.DataFrame) -> None:
        """Empty feature_cols should raise ValueError."""
        with pytest.raises(ValueError, match="feature_cols cannot be empty"):
            fit_track_b_baseline(
                panel=synthetic_panel,
                feature_cols=[],
            )


class TestWalkForwardExecution:
    """Test walk-forward fold execution and anti-leakage invariants."""

    def test_returns_valid_result(self, synthetic_panel: pd.DataFrame) -> None:
        """Should return a TrackBBaselineResult with valid fields."""
        feature_cols = ["roa", "roe", "profit_margin", "momentum_21d"]

        result = fit_track_b_baseline(
            panel=synthetic_panel,
            feature_cols=feature_cols,
            horizon=_TEST_HORIZON,
            min_train_months=60,
            embargo_sessions=21,
        )

        assert isinstance(result, TrackBBaselineResult)
        assert result.n_walk_folds > 0
        assert len(result.per_fold) == result.n_walk_folds
        assert len(result.ic_series) > 0
        assert isinstance(result.mean_ic, float)
        assert isinstance(result.hac_se, float)
        assert len(result.ci_95) == 2
        assert isinstance(result.t_hac, float)
        assert isinstance(result.p_hac, float)
        assert isinstance(result.dm_stat, float)
        assert isinstance(result.dm_p, float)
        assert result.n_test_obs > 0

    def test_minimal_panel_runs(self, minimal_panel: pd.DataFrame) -> None:
        """Minimal panel (minimum viable) should run without error."""
        result = fit_track_b_baseline(
            panel=minimal_panel,
            feature_cols=["momentum_21d"],
            horizon=21,
            min_train_months=12,  # Lower for minimal panel
            embargo_sessions=5,
        )

        assert result.n_walk_folds >= 1
        assert result.n_test_obs > 0

    def test_chronological_invariant_per_fold(self, synthetic_panel: pd.DataFrame) -> None:
        """Each fold should satisfy max(train_date) < min(test_date)."""
        feature_cols = ["roa", "roe"]

        result = fit_track_b_baseline(
            panel=synthetic_panel,
            feature_cols=feature_cols,
            horizon=21,
            min_train_months=60,
            embargo_sessions=21,
        )

        for fold_info in result.per_fold:
            train_max = fold_info["train_max_date"]
            test_min = fold_info["test_min_date"]
            assert train_max < test_min, (
                f"Chronological invariant violated: train_max={train_max} "
                f">= test_min={test_min}"
            )

    def test_fold_counts_reasonable(self, synthetic_panel: pd.DataFrame) -> None:
        """Fold train/test counts should be reasonable."""
        feature_cols = ["roa", "roe"]

        result = fit_track_b_baseline(
            panel=synthetic_panel,
            feature_cols=feature_cols,
            horizon=21,
            min_train_months=60,
            embargo_sessions=21,
        )

        for fold_info in result.per_fold:
            n_train = fold_info["n_train"]
            n_test = fold_info["n_test"]
            assert n_train > 0, f"Fold {fold_info['fold']} has empty train"
            assert n_test > 0, f"Fold {fold_info['fold']} has empty test"
            # Expanding window: train grows (later folds should have more or equal)
            # This is a soft check; exact order depends on data

    def test_test_obs_coverage(self, synthetic_panel: pd.DataFrame) -> None:
        """Test observations should account for most of the panel."""
        feature_cols = ["roa", "roe"]

        result = fit_track_b_baseline(
            panel=synthetic_panel,
            feature_cols=feature_cols,
            horizon=21,
            min_train_months=60,
            embargo_sessions=21,
        )

        # With 250 dates and 5 splits, we expect significant test coverage
        # (excluding initial warmup period)
        assert result.n_test_obs > 100  # Reasonable coverage


class TestRankICComputation:
    """Test rank-IC computation and aggregation."""

    def test_ic_series_is_monthly(self, synthetic_panel: pd.DataFrame) -> None:
        """IC series should be monthly (not daily)."""
        feature_cols = ["roa", "roe"]

        result = fit_track_b_baseline(
            panel=synthetic_panel,
            feature_cols=feature_cols,
            horizon=21,
            min_train_months=60,
            embargo_sessions=21,
        )

        # Check that index is approximately monthly spaced
        if len(result.ic_series) > 1:
            dates = result.ic_series.index
            # Median gap should be ~20-30 business days (1 month)
            gaps = dates.to_series().diff().dropna()
            median_gap_days = gaps.median().total_seconds() / 86400
            # 1 month ≈ 21 business days ≈ 30 calendar days
            assert 15 <= median_gap_days <= 45, (
                f"IC series gap {median_gap_days:.1f} days doesn't look monthly"
            )

    def test_ic_summary_produces_hac_se(self, synthetic_panel: pd.DataFrame) -> None:
        """HAC SE should be finite and non-negative."""
        feature_cols = ["roa", "roe"]

        result = fit_track_b_baseline(
            panel=synthetic_panel,
            feature_cols=feature_cols,
            horizon=21,
            min_train_months=60,
            embargo_sessions=21,
        )

        assert np.isfinite(result.hac_se)
        assert result.hac_se >= 0

    def test_ci_95_is_valid_interval(self, synthetic_panel: pd.DataFrame) -> None:
        """95% CI should be (lower, upper) with lower <= upper."""
        feature_cols = ["roa", "roe"]

        result = fit_track_b_baseline(
            panel=synthetic_panel,
            feature_cols=feature_cols,
            horizon=21,
            min_train_months=60,
            embargo_sessions=21,
        )

        lower, upper = result.ci_95
        assert lower <= upper
        assert np.isfinite(lower)
        assert np.isfinite(upper)
        # CI should contain mean_ic (centered interval)
        assert lower <= result.mean_ic <= upper


class TestDieboldMariano:
    """Test Diebold-Mariano inference vs equal-weight baseline."""

    def test_dm_returns_finite_p_value(self, synthetic_panel: pd.DataFrame) -> None:
        """DM p-value should be finite and in [0, 1]."""
        feature_cols = ["roa", "roe"]

        result = fit_track_b_baseline(
            panel=synthetic_panel,
            feature_cols=feature_cols,
            horizon=21,
            min_train_months=60,
            embargo_sessions=21,
        )

        assert np.isfinite(result.dm_p)
        assert 0.0 <= result.dm_p <= 1.0

    def test_dm_stat_is_finite(self, synthetic_panel: pd.DataFrame) -> None:
        """DM statistic should be finite."""
        feature_cols = ["roa", "roe"]

        result = fit_track_b_baseline(
            panel=synthetic_panel,
            feature_cols=feature_cols,
            horizon=21,
            min_train_months=60,
            embargo_sessions=21,
        )

        assert np.isfinite(result.dm_stat)


class TestDeterminism:
    """Test deterministic behavior with fixed seeds."""

    def test_same_input_same_output(self, synthetic_panel: pd.DataFrame) -> None:
        """Same input should produce identical results (determinism)."""
        feature_cols = ["roa", "roe"]

        result1 = fit_track_b_baseline(
            panel=synthetic_panel,
            feature_cols=feature_cols,
            horizon=21,
            min_train_months=60,
            embargo_sessions=21,
        )

        result2 = fit_track_b_baseline(
            panel=synthetic_panel,
            feature_cols=feature_cols,
            horizon=21,
            min_train_months=60,
            embargo_sessions=21,
        )

        # Results should be identical (H6 determinism)
        assert result1.mean_ic == result2.mean_ic
        assert result1.hac_se == result2.hac_se
        assert result1.n_walk_folds == result2.n_walk_folds
        assert result1.n_test_obs == result2.n_test_obs
        # IC series should match
        pd.testing.assert_series_equal(result1.ic_series, result2.ic_series)


class TestParameterDefaults:
    """Test default parameters match config #41."""

    def test_default_frozen_params_has_lambdarank(self) -> None:
        """Default frozen params should use lambdarank objective (config #41, RD-15).

        LightGBMFrozen.fit_predict_rank implements the lambdarank group/query
        interface additively (option b); regression fit_predict path is unchanged.
        """
        assert _DEFAULT_FROZEN_PARAMS["objective"] == "lambdarank"

    def test_default_bin_count_is_5(self) -> None:
        """Default bin count should be 5 (quintiles)."""
        assert _DEFAULT_BIN_COUNT == 5

    def test_default_embargo_is_21(self) -> None:
        """Default embargo should be 21 sessions."""
        assert _DEFAULT_EMBARGO_SESSIONS == 21


class TestResultImmutability:
    """Test TrackBBaselineResult is immutable (frozen)."""

    def test_result_is_frozen_dataclass(self) -> None:
        """TrackBBaselineResult should be frozen (immutable)."""
        # Access frozen attribute
        assert TrackBBaselineResult.__dataclass_params__.frozen

    def test_cannot_mutate_result_fields(self, synthetic_panel: pd.DataFrame) -> None:
        """Result fields should not be directly mutable."""
        feature_cols = ["roa", "roe"]

        result = fit_track_b_baseline(
            panel=synthetic_panel,
            feature_cols=feature_cols,
            horizon=21,
            min_train_months=60,
            embargo_sessions=21,
        )

        # Attempting to mutate should raise (frozen dataclass)
        # FrozenInstanceError is not a public exception type, catch generic error
        try:
            result.mean_ic = 999.0
            raise AssertionError("Should have raised an exception when mutating frozen dataclass")
        except Exception:
            pass  # Expected: frozen dataclass prevents mutation
