"""Hermetic tests for the regime composite (equal-weight z-scored layers + TACO).

Synthetic deterministic fixtures (seed=0). AAA pattern. No network, no real data.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aionis.features.regime_composite import (
    regime_composite,
    rolling_zscore,
    taco_normalize,
)


def _series(seed: int, n: int = 600, drift: float = 0.0) -> pd.Series:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2018-01-01", periods=n, freq="B")
    return pd.Series(rng.standard_normal(n) + drift, index=idx)


def test_rolling_zscore_is_past_only() -> None:
    """z-score at t excludes x_t from its own mean/std (shift(1) gate)."""
    s = _series(seed=0)
    z = rolling_zscore(s, window=50, min_periods=30)
    # Mutate a future value -> z at an earlier date must not change.
    z_before = z.iloc[100]
    s_mut = s.copy()
    s_mut.iloc[200] += 50.0
    z_after = rolling_zscore(s_mut, window=50, min_periods=30).iloc[100]
    assert z_before == pytest.approx(z_after, abs=1e-12)


def test_taco_normalize_uses_expanding_std() -> None:
    """TACO at t = x_t / std(x[t0..t]) (expanding; no future)."""
    s = _series(seed=1, n=400)
    taco = taco_normalize(s, min_periods=50)
    t = 300
    expected = s.iloc[t] / s.iloc[: t + 1].std(ddof=1)
    assert taco.iloc[t] == pytest.approx(expected, rel=1e-9, abs=1e-12)


def test_regime_composite_equal_weight_of_zscored_layers() -> None:
    """Composite (pre-TACO) is the equal-weight mean of the layers' z-scores."""
    a = _series(seed=0, n=600)
    z_a = rolling_zscore(a, window=50, min_periods=30)
    composite_same = regime_composite(
        {"x": a, "y": a.copy()},
        taco_min_periods=50,
        zscore_window=50,
        zscore_min_periods=30,
    )
    raw = (z_a + z_a) / 2.0
    expected = taco_normalize(raw, min_periods=50)
    pd.testing.assert_series_equal(
        composite_same.dropna(), expected.dropna(), check_names=False, check_freq=False
    )


def test_regime_composite_leakage_guard() -> None:
    """regime_state at t depends only on layer data ≤ t (past-only z + expanding TACO)."""
    a = _series(seed=0, n=600)
    b = _series(seed=1, n=600)
    regime = regime_composite({"a": a, "b": b}, taco_min_periods=50)
    val_before = regime.iloc[400]
    a_mut = a.copy()
    a_mut.iloc[500] += 100.0  # mutate the future
    regime_mut = regime_composite({"a": a_mut, "b": b}, taco_min_periods=50)
    assert val_before == pytest.approx(regime_mut.iloc[400], abs=1e-10)


def test_regime_composite_h6_deterministic() -> None:
    """Two runs on identical inputs are bit-identical."""
    a = _series(seed=2, n=500)
    b = _series(seed=3, n=500)
    r1 = regime_composite({"a": a, "b": b}, taco_min_periods=50)
    r2 = regime_composite({"a": a, "b": b}, taco_min_periods=50)
    pd.testing.assert_series_equal(r1, r2)


def test_regime_composite_empty_layers() -> None:
    """Empty layer dict -> empty Series (no crash)."""
    out = regime_composite({})
    assert out.empty
    assert out.name == "regime_state"
