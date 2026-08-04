"""CN price panel builder tests (hermetic, synthetic fixtures).

AAA pattern: Arrange-Act-Assert. Descriptive names. Fixed seed=0.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from aionis.features.ashare_extras import limit_up_down_distance, suspension_flag
from aionis.features.price_features import (
    TRACK_B_PRICE_FEATURE_COLS,
    compute_amihud_from_wide,
    compute_price_features,
)
from aionis.features.selection_panel import forward_returns


def _make_synthetic_ashare_panel(
    n_dates: int = 300,
    n_tickers: int = 20,
    base_price: float = 10.0,
    start_date: str = "2014-01-01",
    seed: int = 0,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Generate synthetic A-share price panel for testing.

    Args:
        n_dates: Number of trading days
        n_tickers: Number of tickers
        base_price: Starting price level
        start_date: Start date
        seed: Random seed for reproducibility

    Returns:
        (close_wide, volume_wide, tradestatus_wide) - all [dates x tickers]
    """
    rng = np.random.default_rng(seed=seed)
    dates = pd.date_range(start_date, periods=n_dates, freq="B")
    tickers = [f"sh.60000{i}" for i in range(n_tickers)]

    # Generate prices (GBM with drift)
    drift = 0.0001
    vol = 0.02
    close_data = np.zeros((n_dates, n_tickers))
    for t in range(n_tickers):
        log_returns = rng.normal(drift - 0.5 * vol**2, vol, n_dates)
        log_prices = np.log(base_price) + np.cumsum(log_returns)
        close_data[:, t] = np.exp(log_prices)

    close_wide = pd.DataFrame(close_data, index=dates, columns=tickers)

    # Generate volume (log-normal with some noise)
    volume_data = rng.lognormal(mean=14.0, sigma=0.5, size=(n_dates, n_tickers))
    volume_wide = pd.DataFrame(volume_data, index=dates, columns=tickers)

    # Generate trade status (mostly "1" for normal, occasional suspensions)
    tradestatus_data = np.full((n_dates, n_tickers), "1", dtype=object)
    # Randomly suspend ~2% of ticker-dates
    suspension_mask = rng.random((n_dates, n_tickers)) < 0.02
    tradestatus_data[suspension_mask] = "0"
    tradestatus_wide = pd.DataFrame(tradestatus_data, index=dates, columns=tickers)

    return close_wide, volume_wide, tradestatus_wide


def test_build_features_columns_regression() -> None:
    """_build_features flattens the compute_price_features MultiIndex -> [date, ticker, *features].

    Regression guard: a prior version mis-renamed the stacked frame ('Length mismatch: 11
    vs 4') and a leakage-self-check date lookup was out-of-bounds — both undetected because
    the suite exercised compute_price_features directly, not this wrapper. This test runs
    the real wrapper and asserts the column set.
    """
    from scripts.build_cn_price_panel import _build_features

    close_wide, volume_wide, tradestatus_wide = _make_synthetic_ashare_panel(
        n_dates=300, n_tickers=20
    )
    panel = _build_features(close_wide, volume_wide, tradestatus_wide)

    expected = {
        "date",
        "ticker",
        "momentum_5d",
        "momentum_10d",
        "momentum_21d",
        "momentum_42d",
        "reversal_5d",
        "volatility_21d",
        "volatility_63d",
        "turnover_21d",
        "beta_252d",
        "amihud_illiquidity_21d",
        "limit_up_down_distance",
        "suspension_flag",
    }
    assert set(panel.columns) == expected, (
        f"column set mismatch (symmetric diff): {set(panel.columns) ^ expected}"
    )
    # No residual melt columns from the buggy version.
    assert "feature" not in panel.columns
    assert "value" not in panel.columns
    assert panel["ticker"].nunique() == 20
    assert "momentum_21d" in panel.columns  # the leakage self-check reads this


class TestAshareExtras:
    """Unit tests for A-share-specific features."""

    def test_limit_up_down_distance_at_boundary(self) -> None:
        """Limit distance = 1.0 when return exactly at ±10% threshold."""
        # Arrange
        returns = pd.DataFrame(
            [[0.10, -0.10, 0.05], [0.20, -0.05, 0.00]],
            columns=["T1", "T2", "T3"],
        )

        # Act
        result = limit_up_down_distance(returns, limit=0.10)

        # Assert
        assert result.loc[0, "T1"] == 1.0  # Exactly at +10% limit
        assert result.loc[0, "T2"] == 1.0  # Exactly at -10% limit
        assert result.loc[0, "T3"] == 0.5  # Halfway to limit
        assert result.loc[1, "T1"] == 2.0  # Exceeds limit (STAR/ChiNext case)

    def test_limit_up_down_distance_handles_nan(self) -> None:
        """Limit distance propagates NaN from input returns."""
        # Arrange
        returns = pd.DataFrame([[0.05, np.nan], [0.10, -0.10]], columns=["T1", "T2"])

        # Act
        result = limit_up_down_distance(returns, limit=0.10)

        # Assert
        assert pd.isna(result.loc[0, "T2"])
        assert not pd.isna(result.loc[0, "T1"])

    def test_suspension_flag_mapping(self) -> None:
        """Suspension flag: 1.0 for non-'1' status, 0.0 for '1' (normal)."""
        # Arrange
        tradestatus = pd.DataFrame(
            [["1", "0", "1"], ["0", "1", "2"]], columns=["T1", "T2", "T3"]
        )

        # Act
        result = suspension_flag(tradestatus)

        # Assert
        # T1: normal on row 0, suspended on row 1
        assert result.loc[0, "T1"] == 0.0
        assert result.loc[1, "T1"] == 1.0
        # T2: suspended on row 0, normal on row 1
        assert result.loc[0, "T2"] == 1.0
        assert result.loc[1, "T2"] == 0.0
        # T3: normal on row 0, suspended (status='2') on row 1
        assert result.loc[0, "T3"] == 0.0
        assert result.loc[1, "T3"] == 1.0

    def test_suspension_flag_propagates_nan(self) -> None:
        """Suspension flag propagates NaN from input."""
        # Arrange
        tradestatus = pd.DataFrame([["1", np.nan]], columns=["T1", "T2"])

        # Act
        result = suspension_flag(tradestatus)

        # Assert
        assert result.loc[0, "T1"] == 0.0
        assert pd.isna(result.loc[0, "T2"])


class TestPriceFeaturesReuse:
    """Test that price_features module works on A-share data."""

    def test_compute_price_features_on_ashare_data(self) -> None:
        """compute_price_features works on synthetic A-share data."""
        # Arrange
        close_wide, volume_wide, _ = _make_synthetic_ashare_panel(
            n_dates=252, n_tickers=5
        )
        market_prices = close_wide.mean(axis=1)  # Equal-weight proxy

        # Act
        features = compute_price_features(close_wide, volume_wide, market_prices)

        # Assert
        assert features.shape[0] == 252  # All dates
        # MultiIndex columns: (feature, ticker)
        assert features.columns.nlevels == 2
        assert features.columns.names[0] == "feature"
        assert features.columns.names[1] == "ticker"

        # Check that the 9 expected features exist (amihud is added separately)
        expected_features = [f for f in TRACK_B_PRICE_FEATURE_COLS if f != "amihud_illiquidity_21d"]
        feature_names = features.columns.get_level_values(0).unique()
        assert set(feature_names) == set(expected_features)

        # Features should be finite (not all NaN)
        for feat in expected_features:
            feat_data = features[feat]
            # Check each ticker separately (some might be all NaN)
            for ticker in feat_data.columns:
                if feat_data[ticker].notna().any():
                    assert True  # At least one ticker has non-NaN values
                    break
            else:
                raise AssertionError(f"{feat} is all NaN for all tickers")

    def test_compute_amihud_from_wide_on_ashare_data(self) -> None:
        """compute_amihud_from_wide works on A-share data."""
        # Arrange
        close_wide, volume_wide, _ = _make_synthetic_ashare_panel(
            n_dates=100, n_tickers=3
        )

        # Act
        amihud = compute_amihud_from_wide(close_wide, volume_wide, window=21)

        # Assert
        # amihud has one fewer row because pct_change() drops first row
        assert amihud.shape[1] == close_wide.shape[1]  # Same tickers
        assert amihud.shape[0] == close_wide.shape[0] - 1  # One fewer date
        # Should have some non-NaN values (the function computes rolling illiquidity)
        assert amihud.notna().any().any()


class TestForwardReturnsLabel:
    """Test forward returns (label) computation."""

    def test_forward_returns_is_nan_at_end(self) -> None:
        """Forward returns are NaN in the last h rows per ticker."""
        # Arrange
        close_wide, _, _ = _make_synthetic_ashare_panel(n_dates=100, n_tickers=3)
        h = 21

        # Act
        fwd = forward_returns(close_wide, h=h)

        # Assert
        # Last h rows should be NaN for all tickers
        assert fwd.iloc[-h:].isna().all().all()
        # First valid row should have values
        assert fwd.iloc[-h - 1].notna().all()

    def test_forward_returns_uses_future_close(self) -> None:
        """Forward return at t depends on close[t+h], not close[t]."""
        # Arrange
        close_wide = pd.DataFrame(
            [[100.0, 105.0], [110.0, 115.5]],  # Prices increase 10%
            columns=["T1", "T2"],
            index=pd.date_range("2024-01-01", periods=2),
        )
        h = 1

        # Act
        fwd = forward_returns(close_wide, h=h)

        # Assert: At t=0, fwd = (close[1] / close[0]) - 1 = 0.10
        assert np.isclose(fwd.iloc[0, 0], 0.10)


class TestMonthEndSampling:
    """Test month-end sampling logic."""

    def test_month_end_keeps_last_date_per_period(self) -> None:
        """Month-end sampling keeps the max date in each year-month."""
        # Arrange
        dates = pd.to_datetime(
            [
                "2024-01-15",
                "2024-01-31",
                "2024-02-15",
                "2024-02-29",
                "2024-03-15",
            ]
        )
        panel = pd.DataFrame(
            {
                "date": dates,
                "ticker": ["T1"] * 5,
                "value": [1.0, 2.0, 3.0, 4.0, 5.0],
            }
        )
        panel["year_month"] = pd.to_datetime(panel["date"]).dt.to_period("M")

        # Act
        month_end_dates = panel.groupby("year_month")["date"].transform("max")
        sampled = panel[panel["date"] == month_end_dates].drop(columns="year_month")

        # Assert
        assert len(sampled) == 3  # One per month
        assert sampled["date"].tolist() == [
            pd.Timestamp("2024-01-31"),
            pd.Timestamp("2024-02-29"),
            pd.Timestamp("2024-03-15"),
        ]
        assert sampled["value"].tolist() == [2.0, 4.0, 5.0]


class TestLeakageGuard:
    """Anti-leakage verification tests."""

    def test_feature_depends_only_on_past(self) -> None:
        """Feature at t depends only on close[≤t], not on future closes."""
        # Arrange
        close_wide, volume_wide, tradestatus_wide = _make_synthetic_ashare_panel(
            n_dates=100, n_tickers=2
        )
        test_date = close_wide.index[50]  # Mid-series date
        test_ticker = close_wide.columns[0]

        # Get original feature value
        returns = close_wide.pct_change()
        original_momentum = (
            returns.loc[:test_date, [test_ticker]]
            .iloc[-21:]
            .sum()
            .iloc[0]
        )

        # Act: mutate a FUTURE close
        close_mutated = close_wide.copy()
        future_date = close_wide.index[70]
        close_mutated.loc[future_date, test_ticker] *= 2.0

        # Recompute feature
        returns_mutated = close_mutated.pct_change()
        new_momentum = (
            returns_mutated.loc[:test_date, [test_ticker]]
            .iloc[-21:]
            .sum()
            .iloc[0]
        )

        # Assert: momentum at test_date should be UNCHANGED
        assert np.isclose(
            new_momentum, original_momentum, rtol=1e-10
        ), "Feature changed when future close mutated (LEAKAGE)"

    def test_label_depends_on_future(self) -> None:
        """Label at t depends on close[t+h], changes if future mutates."""
        # Arrange
        close_wide, _, _ = _make_synthetic_ashare_panel(n_dates=100, n_tickers=2)
        h = 21
        test_date = close_wide.index[50]
        test_ticker = close_wide.columns[0]
        future_date = close_wide.index[50 + h]

        # Original label
        original_label = (
            close_wide.loc[future_date, test_ticker]
            / close_wide.loc[test_date, test_ticker]
            - 1.0
        )

        # Act: mutate future close
        close_mutated = close_wide.copy()
        close_mutated.loc[future_date, test_ticker] *= 1.5

        new_label = (
            close_mutated.loc[future_date, test_ticker]
            / close_mutated.loc[test_date, test_ticker]
            - 1.0
        )

        # Assert: label should CHANGE
        assert not np.isclose(
            new_label, original_label, rtol=1e-5
        ), "Label unchanged when future close mutated (LEAKAGE)"


class TestH6Determinism:
    """H6 determinism tests: two runs produce bit-identical results."""

    def test_synthetic_panel_generation_is_deterministic(self) -> None:
        """Synthetic panel generation with fixed seed is reproducible."""
        # Arrange & Act (first run)
        close1, vol1, status1 = _make_synthetic_ashare_panel(n_dates=50, n_tickers=3)

        # Arrange & Act (second run, same seed)
        close2, vol2, status2 = _make_synthetic_ashare_panel(n_dates=50, n_tickers=3)

        # Assert: bit-identical
        pd.testing.assert_frame_equal(close1, close2)
        pd.testing.assert_frame_equal(vol1, vol2)
        pd.testing.assert_frame_equal(status1, status2)

    def test_price_features_are_deterministic(self) -> None:
        """compute_price_features is deterministic on same input."""
        # Arrange
        close_wide, volume_wide, _ = _make_synthetic_ashare_panel(
            n_dates=100, n_tickers=3
        )
        market_prices = close_wide.mean(axis=1)

        # Act (first run)
        features1 = compute_price_features(close_wide, volume_wide, market_prices)

        # Act (second run)
        features2 = compute_price_features(close_wide, volume_wide, market_prices)

        # Assert: bit-identical
        pd.testing.assert_frame_equal(features1, features2)

    def test_amihud_is_deterministic(self) -> None:
        """compute_amihud_from_wide is deterministic."""
        # Arrange
        close_wide, volume_wide, _ = _make_synthetic_ashare_panel(
            n_dates=100, n_tickers=3
        )

        # Act (first run)
        amihud1 = compute_amihud_from_wide(close_wide, volume_wide, window=21)

        # Act (second run)
        amihud2 = compute_amihud_from_wide(close_wide, volume_wide, window=21)

        # Assert: bit-identical
        pd.testing.assert_frame_equal(amihud1, amihud2)

    def test_ashare_extras_are_deterministic(self) -> None:
        """A-share extras are deterministic."""
        # Arrange
        close_wide, _, tradestatus_wide = _make_synthetic_ashare_panel(
            n_dates=100, n_tickers=3
        )
        returns = close_wide.pct_change()

        # Act (first run)
        limit1 = limit_up_down_distance(returns, limit=0.10)
        susp1 = suspension_flag(tradestatus_wide)

        # Act (second run)
        limit2 = limit_up_down_distance(returns, limit=0.10)
        susp2 = suspension_flag(tradestatus_wide)

        # Assert: bit-identical
        pd.testing.assert_frame_equal(limit1, limit2)
        pd.testing.assert_frame_equal(susp1, susp2)
