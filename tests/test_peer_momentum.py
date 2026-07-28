"""SIC ex-self peer-momentum feature — hermetic (synthetic prices, no network).

Pins :mod:`aionis.features.peer_momentum`: the peer signal excludes the firm's
own trailing return (ex-self exactness), a singleton SIC group yields NaN, the
trailing return is strictly backward (PIT), and different SIC groups are isolated.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aionis.features.peer_momentum import peer_momentum_panel


def _px(rows: dict[str, list[float]]) -> pd.DataFrame:
    n = len(next(iter(rows.values())))
    return pd.DataFrame(rows, index=pd.bdate_range("2024-01-02", periods=n))


def test_ex_self_peer_signal_excludes_own_return() -> None:
    # 2 tickers same SIC, window=1 -> peer signal of A = trail of B (its only peer)
    px = _px({"A": [10, 11, 12, 13], "B": [100, 110, 120, 130]})
    w = peer_momentum_panel(px, {"A": "X", "B": "X"}, window=1)

    d1 = px.index[1]
    # trail_A = 11/10-1 = 0.1; trail_B = 110/100-1 = 0.1
    assert w.loc[d1, "A"] == pytest.approx(0.1)  # peer of A is B -> trail_B
    assert w.loc[d1, "B"] == pytest.approx(0.1)  # peer of B is A -> trail_A
    assert pd.isna(w.loc[px.index[0], "A"])       # no prior session -> NaN


def test_ex_self_with_three_peers() -> None:
    px = _px({"A": [10, 12, 13], "B": [100, 110, 120], "C": [1, 3, 4]})
    w = peer_momentum_panel(px, {"A": "X", "B": "X", "C": "X"}, window=1)

    d1 = px.index[1]
    # trail_A=0.2, trail_B=0.1, trail_C=2.0 -> peer of A = mean(B,C) = 1.05
    assert w.loc[d1, "A"] == pytest.approx((0.1 + 2.0) / 2)
    assert w.loc[d1, "B"] == pytest.approx((0.2 + 2.0) / 2)


def test_singleton_sic_group_is_nan() -> None:
    px = _px({"A": [10, 11, 12]})
    w = peer_momentum_panel(px, {"A": "X"}, window=1)  # no peers
    assert w["A"].isna().all()


def test_mixed_nan_group_ex_self_mean_is_exact() -> None:
    """Regression for the pandas->3.0 `.stack()` retains-NaN bug: when a SIC group
    has a peer whose trailing return is undefined (warmup / newly entered), the
    ex-self mean must still be exact for the peers that DO have a trail.

    group {A=0.20, B=0.10, C=NaN}: peer of A = mean(B) = 0.10 (C excluded);
    peer of B = mean(A) = 0.20; C (no own trail) -> NaN. The old `transform(size)`
    counted C and gave A=0.125 (wrong); `transform(count)` gives 0.10 (exact)."""
    # window=1: trail[t] = px[t]/px[t-1]-1. Make C's trail NaN by giving it only
    # one observation after the first date (NaN at d1 via a NaN close).
    idx = pd.bdate_range("2024-01-02", periods=3)
    px = pd.DataFrame(
        {"A": [10.0, 12.0, 13.0],   # trail d1 = 0.20
         "B": [100.0, 110.0, 120.0],  # trail d1 = 0.10
         "C": [1.0, np.nan, 4.0]},    # trail d1 = NaN (NaN close)
        index=idx,
    )
    w = peer_momentum_panel(px, {"A": "X", "B": "X", "C": "X"}, window=1)
    d1 = idx[1]
    assert w.loc[d1, "A"] == pytest.approx(0.10)   # peer = B only (C NaN excluded)
    assert w.loc[d1, "B"] == pytest.approx(0.20)   # peer = A only
    assert pd.isna(w.loc[d1, "C"])                  # C has no own trail -> NaN


def test_different_sic_groups_are_isolated() -> None:
    px = _px({"A": [10, 12, 13], "B": [100, 110, 120]})
    w = peer_momentum_panel(px, {"A": "X", "B": "Y"}, window=1)  # no shared group
    assert w["A"].isna().all() and w["B"].isna().all()


def test_trailing_return_is_strictly_backward() -> None:
    """peer_mom at date t uses only close <= t (a backward window). Perturbing a
    FUTURE close cannot move the peer signal at t."""
    base = _px({"A": [10, 11, 12, 13, 14], "B": [100, 110, 120, 130, 140]})
    w0 = peer_momentum_panel(base, {"A": "X", "B": "X"}, window=2)

    future = base.copy()
    future.loc[future.index[-1], "B"] *= 10.0  # grossly perturb the LAST close
    w1 = peer_momentum_panel(future, {"A": "X", "B": "X"}, window=2)

    # peer_mom at index[2] = trail at [2] = close[2]/close[0]-1 (window=2 backward);
    # the last-close perturbation cannot enter, so the two are bit-equal.
    d2 = base.index[2]
    assert w0.loc[d2, "A"] == pytest.approx(w1.loc[d2, "A"])
