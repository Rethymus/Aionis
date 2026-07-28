"""Phase C bundle-shuffle placebo controls — hermetic.

Pins the two NaN-preserving, seed-deterministic shuffles of
:mod:`aionis.eval.phase_c_controls`: the date-broadcast permutation must keep the
NaN / coverage structure and the multiset of values, and the earnings shuffle
must keep the per-date multiset while breaking the company→value mapping. A
placebo that is not reproducible or that leaks NaN would invalidate the §5 #2
control, so both properties are pinned.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from aionis.eval.phase_c_controls import (
    shuffle_date_broadcast,
    shuffle_earnings_across_tickers,
)


def _sorted_nonnan(values: np.ndarray) -> list[float]:
    v = np.asarray(values, dtype=float)
    return sorted(v[~np.isnan(v)].tolist())


# --- date-broadcast shuffle -------------------------------------------------


def test_date_broadcast_preserves_nan_mask_and_multiset() -> None:
    f = pd.DataFrame(
        {
            "a": [1.0, np.nan, 3.0, 4.0, np.nan, 6.0],
            "b": [10.0, 20.0, np.nan, 40.0, 50.0, np.nan],
        }
    )

    out = shuffle_date_broadcast(f, seed=0)

    for col in f.columns:
        np.testing.assert_array_equal(
            np.isnan(f[col].to_numpy()), np.isnan(out[col].to_numpy())
        )
        assert _sorted_nonnan(f[col].to_numpy()) == _sorted_nonnan(out[col].to_numpy())


def test_date_broadcast_is_seed_deterministic() -> None:
    rng = np.random.default_rng(0)
    f = pd.DataFrame({"x": rng.normal(size=40)})

    a = shuffle_date_broadcast(f, seed=3)
    b = shuffle_date_broadcast(f, seed=3)

    pd.testing.assert_frame_equal(a, b)


def test_date_broadcast_breaks_value_to_date_alignment() -> None:
    # enough values that a permutation is overwhelmingly not the identity
    f = pd.DataFrame({"x": np.arange(50.0)})

    out = shuffle_date_broadcast(f, seed=1)

    assert not np.array_equal(f["x"].to_numpy(), out["x"].to_numpy())
    assert sorted(f["x"].tolist()) == sorted(out["x"].tolist())


def test_date_broadcast_all_nan_or_single_value_untouched() -> None:
    f = pd.DataFrame({"blank": [np.nan] * 5, "one": [2.0, np.nan, np.nan, np.nan, np.nan]})

    out = shuffle_date_broadcast(f, seed=0)

    pd.testing.assert_frame_equal(f, out)


# --- earnings cross-ticker shuffle -----------------------------------------


def test_earnings_shuffle_preserves_per_date_multiset_and_nan() -> None:
    long = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-02"] * 4 + ["2024-01-03"] * 4),
            "ticker": ["A", "B", "C", "D"] * 2,
            "earnings_surprise": [1.0, 2.0, np.nan, 4.0, 5.0, 6.0, 7.0, np.nan],
        }
    )

    out = shuffle_earnings_across_tickers(long, seed=0)

    for d, grp in long.groupby("date"):
        got = out[out["date"] == d]
        np.testing.assert_array_equal(
            np.isnan(grp["earnings_surprise"].to_numpy()),
            np.isnan(got["earnings_surprise"].to_numpy()),
        )
        assert _sorted_nonnan(grp["earnings_surprise"].to_numpy()) == _sorted_nonnan(
            got["earnings_surprise"].to_numpy()
        )
        # tickers + dates unchanged — only the value→ticker mapping moved
        assert sorted(grp["ticker"].tolist()) == sorted(got["ticker"].tolist())


def test_earnings_shuffle_is_seed_deterministic() -> None:
    long = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-02"] * 6),
            "ticker": list("ABCDEF"),
            "earnings_surprise": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        }
    )

    a = shuffle_earnings_across_tickers(long, seed=4)
    b = shuffle_earnings_across_tickers(long, seed=4)

    pd.testing.assert_frame_equal(a, b)


def test_earnings_shuffle_breaks_company_to_value() -> None:
    # one date, six distinct values -> a non-trivial permutation (overwhelmingly
    # not the identity) but the same multiset, same tickers.
    long = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-02"] * 6),
            "ticker": list("ABCDEF"),
            "earnings_surprise": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
        }
    )

    out = shuffle_earnings_across_tickers(long, seed=2)

    assert not np.array_equal(
        long["earnings_surprise"].to_numpy(), out["earnings_surprise"].to_numpy()
    )
    assert _sorted_nonnan(long["earnings_surprise"].to_numpy()) == _sorted_nonnan(
        out["earnings_surprise"].to_numpy()
    )
