"""Hermetic tests for the close-only qlib factor module (no panel file needed).

Locks the per-factor formulas on hand-computed monotonic / flat / mixed series,
the PIT-honest leading-NaN behavior, and per-ticker isolation.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from aionis.features.qlib_close_factors import (
    _per_ticker_factors,
    compute_qlib_close_factors,
)


def _series(vals: list[float]) -> pd.Series:
    return pd.Series(vals, dtype=float)


def test_monotonic_up_factors_at_last_point() -> None:
    # close = 1..10, window 5. Last point: all up-moves, current is the window max.
    close = _series(list(range(1, 11)))
    out = _per_ticker_factors(close, 5)
    last = out.iloc[-1]
    assert last["rank_5d"] == 1.0  # 10 is the max of [6,7,8,9,10]
    assert abs(last["rsi_5d"] - 1.0) < 1e-9  # all gains, no losses
    assert abs(last["cntp_5d"] - 1.0) < 1e-9  # every day up
    assert abs(last["timetohigh_5d"] - 0.0) < 1e-9  # current is the high
    assert abs(last["range_5d"] - 0.4) < 1e-9  # (10-6)/10


def test_monotonic_down_factors_at_last_point() -> None:
    # close = 10..1, window 5. Last point: all down, current is the window min.
    close = _series(list(range(10, 0, -1)))
    out = _per_ticker_factors(close, 5)
    last = out.iloc[-1]
    assert abs(last["rsi_5d"] - 0.0) < 1e-9  # no gains
    assert abs(last["cntp_5d"] - 0.0) < 1e-9  # no up-days
    assert abs(last["timetohigh_5d"] - 1.0) < 1e-9  # current is min, high opened window
    # range = (max-min)/close = (6-2... wait window is [5,4,3,2,1]) → (5-1)/1 = 4.0
    assert abs(last["range_5d"] - 4.0) < 1e-9


def test_flat_series_range_zero_rsi_nan() -> None:
    # A perfectly flat close: range is 0; rsi is NaN (no abs change → 0/0).
    close = _series([5.0] * 8)
    out = _per_ticker_factors(close, 5)
    last = out.iloc[-1]
    assert abs(last["range_5d"] - 0.0) < 1e-9
    assert np.isnan(last["rsi_5d"])  # 0/0 guarded to NaN


def test_window_longer_than_series_all_nan() -> None:
    # PIT-honest: not enough history → NaN (no lookahead fabrication).
    close = _series([1.0, 2.0, 3.0])
    out = _per_ticker_factors(close, 5)
    assert out["rank_5d"].isna().all()
    assert out["rsi_5d"].isna().all()


def test_leading_window_minus_one_rows_are_nan() -> None:
    close = _series(list(range(1, 11)))  # 10 points
    out = _per_ticker_factors(close, 5)
    # close-based factors (rank/range/cntp/timetohigh): first window-1 rows NaN.
    assert out["rank_5d"].iloc[:4].isna().all()
    assert out["rank_5d"].iloc[4:].notna().all()
    # rsi uses close.diff(), whose first value is NaN → one extra leading NaN
    # (window, not window-1). PIT-honest: the first difference is undefined.
    assert out["rsi_5d"].iloc[:5].isna().all()
    assert out["rsi_5d"].iloc[5:].notna().all()


def test_timetohigh_zero_at_high_one_at_low() -> None:
    # V-shape: 5..1 then 1..5. At the trough (min), timetohigh should be ~1
    # (far from recent high); at the final point (new high), ~0.
    close = _series([5.0, 4.0, 3.0, 2.0, 1.0, 2.0, 3.0, 4.0, 5.0])
    out = _per_ticker_factors(close, 5)
    # At i=4 (trough=1.0): window [5,4,3,2,1], max at position 0 → (5-1-0)/4 = 1.0
    assert abs(out["timetohigh_5d"].iloc[4] - 1.0) < 1e-9
    # At i=8 (back to 5.0): window [1,2,3,4,5], max at position 4 → (5-1-4)/4 = 0.0
    assert abs(out["timetohigh_5d"].iloc[8] - 0.0) < 1e-9


def test_compute_adds_columns_without_touching_existing() -> None:
    panel = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=12, freq="D").tolist() * 2,
            "ticker": ["AAA"] * 12 + ["BBB"] * 12,
            "close": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0] * 2,
            "momentum_21d": [0.01] * 24,  # an existing column that must be preserved
        }
    )
    enriched = compute_qlib_close_factors(panel, windows=(5,))
    # Existing column untouched.
    assert (enriched["momentum_21d"] == panel["momentum_21d"]).all()
    # New factor columns present.
    for col in ("rank_5d", "rsi_5d", "cntp_5d", "range_5d", "timetohigh_5d"):
        assert col in enriched.columns


def test_per_ticker_isolation() -> None:
    # AAA trends up, BBB trends down — their factors must not bleed into each other.
    panel = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=10, freq="D").tolist() * 2,
            "ticker": ["AAA"] * 10 + ["BBB"] * 10,
            "close": list(range(1, 11)) + list(range(10, 0, -1)),
        }
    )
    enriched = compute_qlib_close_factors(panel, windows=(5,))
    aaa_last = enriched[enriched["ticker"] == "AAA"].iloc[-1]
    bbb_last = enriched[enriched["ticker"] == "BBB"].iloc[-1]
    assert abs(aaa_last["rsi_5d"] - 1.0) < 1e-9  # AAA all up
    assert abs(bbb_last["rsi_5d"] - 0.0) < 1e-9  # BBB all down


def test_no_close_column_returns_panel_unchanged() -> None:
    panel = pd.DataFrame({"date": [1, 2], "ticker": ["A", "A"], "x": [1.0, 2.0]})
    out = compute_qlib_close_factors(panel, value_col="close")
    assert list(out.columns) == ["date", "ticker", "x"]
