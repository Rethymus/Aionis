"""Network shock propagation (Phase E1) — hermetic.

Pins :mod:`aionis.features.propagation`: the ex-self SIC-peer mean is exact for
arbitrary shock panels (earnings surprise, 13D-event indicator, ...), a singleton
group is NaN, different SICs are isolated, and the pandas>=3.0 NaN-safe count
(the HIGH-1 regression) holds. Also confirms peer_momentum delegates to it.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aionis.features.propagation import propagate_panel


def _wide(rows: dict[str, list[float]]) -> pd.DataFrame:
    n = len(next(iter(rows.values())))
    return pd.DataFrame(rows, index=pd.bdate_range("2024-01-02", periods=n))


def test_ex_self_propagation_excludes_own_shock() -> None:
    # 2 tickers same SIC, one date: prop of A = shock of B (its only peer)
    shock = _wide({"A": [0.3], "B": [-0.1]})
    out = propagate_panel(shock, {"A": "X", "B": "X"})

    assert out.loc[out.index[0], "A"] == pytest.approx(-0.1)  # peer B
    assert out.loc[out.index[0], "B"] == pytest.approx(0.3)   # peer A


def test_ex_self_with_three_peers_exact() -> None:
    shock = _wide({"A": [0.2], "B": [0.1], "C": [2.0]})
    out = propagate_panel(shock, {"A": "X", "B": "X", "C": "X"})

    d0 = out.index[0]
    assert out.loc[d0, "A"] == pytest.approx((0.1 + 2.0) / 2)
    assert out.loc[d0, "B"] == pytest.approx((0.2 + 2.0) / 2)


def test_singleton_sic_group_is_nan() -> None:
    shock = _wide({"A": [0.5]})
    out = propagate_panel(shock, {"A": "X"})  # no peers
    assert out["A"].isna().all()


def test_different_sic_groups_isolated() -> None:
    shock = _wide({"A": [0.2], "B": [0.4]})
    out = propagate_panel(shock, {"A": "X", "B": "Y"})  # no shared SIC
    assert out["A"].isna().all() and out["B"].isna().all()


def test_mixed_nan_group_count_not_size() -> None:
    """Regression for the pandas>=3.0 `.stack()` retains-NaN bug: a peer whose
    shock is undefined must be excluded (count, not size). Group {A=0.2,B=0.1,C=NaN}:
    prop of A = mean(B) = 0.1 (C excluded), NOT the buggy 0.125."""
    shock = pd.DataFrame(
        {"A": [0.2], "B": [0.1], "C": [np.nan]},
        index=pd.bdate_range("2024-01-02", periods=1),
    )
    out = propagate_panel(shock, {"A": "X", "B": "X", "C": "X"})
    d0 = out.index[0]
    assert out.loc[d0, "A"] == pytest.approx(0.1)
    assert out.loc[d0, "B"] == pytest.approx(0.2)
    assert pd.isna(out.loc[d0, "C"])  # C's own shock NaN -> leave-one-out undefined


def test_propagate_a_binary_event_indicator() -> None:
    """A 13D-event-style 0/1 panel: if 1 of 3 peers had an event, the propagated
    indicator for each peer (ex-self) is the mean of the OTHER two."""
    shock = _wide({"A": [1.0], "B": [0.0], "C": [0.0]})  # A had the event
    out = propagate_panel(shock, {"A": "X", "B": "X", "C": "X"})
    d0 = out.index[0]
    assert out.loc[d0, "A"] == pytest.approx(0.0)   # peers B,C both 0
    assert out.loc[d0, "B"] == pytest.approx(0.5)   # peers A,C -> mean(1,0)
    assert out.loc[d0, "C"] == pytest.approx(0.5)


def test_peer_momentum_delegates_to_propagate_panel() -> None:
    """peer_momentum (Phase D) must produce identical output to
    propagate_panel(trailing_return) after the refactor — the delegation preserves
    behavior."""
    from aionis.features.peer_momentum import peer_momentum_panel

    rng = np.random.default_rng(0)
    px = pd.DataFrame(
        100 + np.cumsum(rng.normal(size=(30, 4)), axis=0),
        index=pd.bdate_range("2024-01-02", periods=30), columns=list("ABCD"),
    )
    sic = {"A": "X", "B": "X", "C": "Y", "D": "Y"}
    window = 5
    trail = (px[list("ABCD")] / px[list("ABCD")].shift(window)) - 1.0

    direct = propagate_panel(trail, sic)
    via_pm = peer_momentum_panel(px, sic, window=window)

    pd.testing.assert_frame_equal(direct, via_pm)
