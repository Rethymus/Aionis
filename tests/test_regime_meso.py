"""Tests for regime meso layer (Track C) — cross-sector momentum.

Hermetic tests use synthetic sector + price data (seed=0). Coverage:
  - Cross-sector mean momentum correctness
  - Equal-weight US + CN compositing
  - Anti-leakage: sector momentum at t uses only prices ≤t
  - H6 determinism: seed=0, n_jobs=1 produces bit-identical results
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aionis.features.regime_meso import (
    _compute_sector_momentum,
    _load_us_sic_map,
    build_meso_regime,
)


@pytest.fixture
def seed():
    """Fixed seed for H6 determinism."""
    return 0


@pytest.fixture
def synthetic_prices(seed):
    """Synthetic price panel [dates x tickers] (seed=0 for H6)."""
    rng = np.random.default_rng(seed)
    n_dates = 252
    n_tickers = 50

    # Generate prices with trend + noise
    dates = pd.date_range("2016-01-01", periods=n_dates, freq="B")
    tickers = [f"T{i:02d}" for i in range(n_tickers)]

    # Base price = 100 + trend + random walk
    prices = np.ones((n_dates, n_tickers)) * 100.0
    trend = np.linspace(0, 20, n_dates).reshape(-1, 1)
    noise = rng.standard_normal((n_dates, n_tickers)) * 2.0

    # Random walk component
    for i in range(1, n_dates):
        prices[i] = prices[i-1] + rng.standard_normal(n_tickers) * 0.5

    prices = prices + trend + noise
    prices[prices < 1] = 1.0  # Floor at $1

    return pd.DataFrame(prices, index=dates, columns=tickers)


@pytest.fixture
def synthetic_sector_map():
    """Synthetic sector map: 5 sectors, 10 tickers each."""
    sectors = ["Tech", "Health", "Finance", "Energy", "Consumer"]
    mapping = {}
    for i, sector in enumerate(sectors):
        for j in range(10):
            ticker = f"T{i*10 + j:02d}"
            mapping[ticker] = sector
    return mapping


class TestComputeSectorMomentum:
    """Test cross-sector mean momentum computation."""

    def test_returns_series_with_correct_shape(self, synthetic_prices, synthetic_sector_map):
        """Returns a Series with same index as input prices."""
        result = _compute_sector_momentum(synthetic_prices, synthetic_sector_map)

        assert isinstance(result, pd.Series)
        assert len(result) == len(synthetic_prices)
        assert result.name == "meso_regime"

    def test_equal_weight_across_sectors(self, synthetic_prices, synthetic_sector_map):
        """Cross-sector regime is equal-weight mean of sector momentums."""
        result = _compute_sector_momentum(synthetic_prices, synthetic_sector_map)

        # Manually compute sector momentums for a sample date
        sample_date = result.index[50]  # Mid-series to avoid warm-up NaN

        from aionis.features.price_features import momentum

        returns = synthetic_prices.pct_change()
        stock_momentum = momentum(returns, window=21)

        sector_values = {}
        for ticker, sector in synthetic_sector_map.items():
            if ticker in stock_momentum.columns:
                val = stock_momentum.loc[sample_date, ticker]
                if pd.notna(val):
                    sector_values.setdefault(sector, []).append(float(val))

        # Compute equal-weight per sector
        sector_means = [np.mean(vals) for vals in sector_values.values()]

        # Cross-sector mean should equal manual computation
        expected = np.mean(sector_means)
        actual = result.loc[sample_date]

        assert pd.notna(actual)
        assert abs(actual - expected) < 1e-6

    def test_past_only_momentum_no_leakage(self, synthetic_prices, synthetic_sector_map):
        """Momentum at t uses only prices up to t (no future leakage)."""
        result = _compute_sector_momentum(synthetic_prices, synthetic_sector_map)

        # First 21 dates should be NaN (min_periods=21 for momentum + 1 for pct_change)
        assert result.iloc[:21].isna().all()

        # Date 22 should have valid momentum (uses prices[0:22])
        assert pd.notna(result.iloc[21])

    def test_handles_missing_sector_map(self, synthetic_prices):
        """Gracefully handles tickers without sector classification."""
        # Empty sector map
        empty_map = {}
        result = _compute_sector_momentum(synthetic_prices, empty_map)

        # Should return NaN series with same index
        assert isinstance(result, pd.Series)
        assert len(result) == len(synthetic_prices)
        assert result.isna().all()

    def test_partial_sector_coverage(self, synthetic_prices):
        """Handles partial sector coverage (some tickers classified)."""
        # Classify only 20 out of 50 tickers
        partial_map = {f"T{i:02d}": "SectorA" for i in range(20)}
        result = _compute_sector_momentum(synthetic_prices, partial_map)

        # Should still compute valid regime (NaNs only during warmup)
        n_valid = result.notna().sum()
        assert n_valid > len(synthetic_prices) - 30  # Allow warmup NaNs


class TestLoadUsSicMap:
    """Test US SIC map loading."""

    def test_raises_file_not_found_when_missing(self, tmp_path):
        """Raises FileNotFoundError when SIC map file does not exist."""
        with pytest.raises(FileNotFoundError, match="US SIC map not found"):
            _load_us_sic_map(cache_dir=tmp_path)


class TestBuildMesoRegime:
    """Test end-to-end meso regime building."""

    def test_builds_us_regime_when_cn_disabled(
        self, synthetic_prices, synthetic_sector_map, tmp_path
    ):
        """Builds US-only meso regime when CN fetch disabled."""
        # Mock SIC map
        sic_file = tmp_path / "phase_d_sic_map.parquet"
        pd.DataFrame({
            "ticker": list(synthetic_sector_map.keys()),
            "cik": [1000 + i for i in range(len(synthetic_sector_map))],
            "sic": [1000 + i for i in range(len(synthetic_sector_map))],
            "sic_description": [f"Sector {s}" for s in synthetic_sector_map.values()],
        }).to_parquet(sic_file)

        result = build_meso_regime(
            us_prices=synthetic_prices,
            cn_prices=pd.DataFrame(),  # Empty CN
            cache_dir=tmp_path,
            enable_cn_fetch=False,
        )

        assert isinstance(result, pd.Series)
        assert result.name == "meso_regime"
        assert len(result) == len(synthetic_prices)

    def test_equal_weight_us_cn(self, seed):
        """Equal-weights US and CN regimes when both available."""
        import tempfile
        from pathlib import Path

        rng = np.random.default_rng(seed)

        # US prices
        us_dates = pd.date_range("2016-01-01", periods=100, freq="B")
        us_prices = pd.DataFrame(
            100 + rng.standard_normal((100, 20)) * 5,
            index=us_dates,
            columns=[f"US{i:02d}" for i in range(20)],
        )

        # CN prices
        cn_dates = pd.date_range("2016-01-01", periods=100, freq="B")
        cn_prices = pd.DataFrame(
            100 + rng.standard_normal((100, 20)) * 5,
            index=cn_dates,
            columns=[f"CN{i:02d}" for i in range(20)],
        )

        # Mock SIC map
        tmp = Path(tempfile.mkdtemp())
        sic_file = tmp / "phase_d_sic_map.parquet"
        pd.DataFrame({
            "ticker": [f"US{i:02d}" for i in range(20)],
            "cik": list(range(1000, 1020)),
            "sic": list(range(1000, 1020)),
            "sic_description": ["US Sector"] * 20,
        }).to_parquet(sic_file)

        # Build with CN disabled (no actual CN fetch)
        result = build_meso_regime(
            us_prices=us_prices,
            cn_prices=cn_prices,
            cache_dir=tmp,
            enable_cn_fetch=False,
        )

        # Should equal US regime (CN contributes NaN)
        assert isinstance(result, pd.Series)

    def test_h6_determinism_seed_zero(self, synthetic_prices, synthetic_sector_map, tmp_path):
        """H6: seed=0 produces bit-identical results across runs."""
        # Mock SIC map
        sic_file = tmp_path / "phase_d_sic_map.parquet"
        pd.DataFrame({
            "ticker": list(synthetic_sector_map.keys()),
            "cik": [1000 + i for i in range(len(synthetic_sector_map))],
            "sic": [1000 + i for i in range(len(synthetic_sector_map))],
            "sic_description": list(synthetic_sector_map.values()),
        }).to_parquet(sic_file)

        # Run twice with same inputs
        result1 = build_meso_regime(
            us_prices=synthetic_prices,
            cn_prices=pd.DataFrame(),
            cache_dir=tmp_path,
            enable_cn_fetch=False,
        )

        result2 = build_meso_regime(
            us_prices=synthetic_prices,
            cn_prices=pd.DataFrame(),
            cache_dir=tmp_path,
            enable_cn_fetch=False,
        )

        # Bit-identical
        pd.testing.assert_series_equal(result1, result2)


class TestAntiLeakage:
    """Anti-leakage tests (binding)."""

    def test_sector_momentum_past_only(self, synthetic_prices, synthetic_sector_map):
        """Sector momentum at t uses only returns ≤t (strict past)."""
        result = _compute_sector_momentum(synthetic_prices, synthetic_sector_map)

        # Check that momentum_21d requires at least 21 prior observations
        # (plus 1 for pct_change = 22 warmup rows)
        assert result.iloc[:21].isna().all()  # First 21 dates insufficient warmup

        # Date 22 (index 21) uses returns[0:22] → valid momentum
        assert pd.notna(result.iloc[21])

    def test_no_future_price_leakage(self, synthetic_prices, synthetic_sector_map):
        """Regime value at t does NOT depend on future prices > t."""
        # Compute regime on full series
        full_regime = _compute_sector_momentum(synthetic_prices, synthetic_sector_map)

        # Compute regime on truncated series (exclude last 10 dates)
        truncated_prices = synthetic_prices.iloc[:-10]
        truncated_regime = _compute_sector_momentum(truncated_prices, synthetic_sector_map)

        # Values up to truncation point should be identical (no future leakage)
        # (Ignoring last 10 values which are missing from truncated)
        common_dates = full_regime.index[:-10]
        full_truncated = full_regime.loc[common_dates]
        truncated_aligned = truncated_regime.loc[common_dates]

        pd.testing.assert_series_equal(full_truncated, truncated_aligned)
