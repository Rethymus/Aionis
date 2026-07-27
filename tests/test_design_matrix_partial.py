"""Partial-history robustness — a symbol whose prices are NaN before inception.

The powered rerun extends the window back before some ETFs existed (XLRE
2015-10, XLC 2018-06). These tests pin the design-matrix drop policy for a
symbol with missing leading history:

  * (event, symbol) rows before inception (or without enough post-inception
    lookback) are ABSENT — never NaN-poisoned features or labels in X/y;
  * full-history symbols at the same events are byte-for-byte unaffected;
  * post-inception events with >= _MIN_HISTORY closes ARE present and finite;
  * no label is ever computed across the inception boundary (both label
    anchors must be real closes — imputation/ffill would fabricate data).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aionis.features.alignment import NYSE_TZ, nyse_sessions
from aionis.features.design_matrix import build_design_matrix
from aionis.features.market_state import _MIN_HISTORY
from aionis.synthetic import make_synthetic_events, make_synthetic_prices

SYMBOLS = ["XLK", "XLRE", "SPY"]  # SPY = benchmark column, always full history
TARGETS = ["XLK", "XLRE"]
FULL, PARTIAL = "XLK", "XLRE"
HORIZON = 1

# Session-grid positions (14:00 ET events: t_info = idx-1, label = [idx, idx+1]).
INCEPTION_IDX = 100
PRE_IDXS = [50, 60]  # full pre-inception (full-history symbols have ample lookback)
STRADDLE_IDX = INCEPTION_IDX - 1  # label_start pre-inception (NaN), label_end = inception
EARLY_POST_IDX = INCEPTION_IDX + 10  # post-inception but < _MIN_HISTORY closes
BOUNDARY_ABSENT_IDX = INCEPTION_IDX + _MIN_HISTORY - 1  # t_info has 21 closes -> drop
BOUNDARY_PRESENT_IDX = INCEPTION_IDX + _MIN_HISTORY  # t_info has exactly 22 -> keep
LATE_IDX = 140  # comfortably past inception + lookback


@pytest.fixture(scope="module")
def sessions() -> pd.DatetimeIndex:
    return nyse_sessions("2023-01-03", "2023-12-29")


@pytest.fixture(scope="module")
def full_prices(sessions: pd.DatetimeIndex) -> pd.DataFrame:
    return make_synthetic_prices(sessions, SYMBOLS, seed=11)


@pytest.fixture(scope="module")
def partial_prices(sessions: pd.DatetimeIndex, full_prices: pd.DataFrame) -> pd.DataFrame:
    """Same prices, but PARTIAL has no history strictly before its inception."""
    prices = full_prices.copy()
    prices.loc[prices.index < sessions[INCEPTION_IDX], PARTIAL] = np.nan
    return prices


def _events_at(sessions: pd.DatetimeIndex, indices: list[int]) -> pd.DataFrame:
    """Deterministic 14:00 ET events on the given session positions."""
    rows = [
        {
            "event_id": f"EV_{i}",
            "event_type": "FOMC",
            "event_ts": (
                pd.Timestamp(sessions[i]).normalize() + pd.Timedelta(hours=14)
            ).tz_localize(NYSE_TZ),
        }
        for i in indices
    ]
    return pd.DataFrame(rows)


# --- (a) pre-inception rows absent, matrix never NaN-poisoned -----------------


def test_pre_inception_rows_absent_and_matrix_finite(
    sessions: pd.DatetimeIndex, partial_prices: pd.DataFrame
) -> None:
    events = _events_at(sessions, [*PRE_IDXS, STRADDLE_IDX, EARLY_POST_IDX, LATE_IDX])
    dm = build_design_matrix(events, partial_prices, sessions, TARGETS, horizon=HORIZON)

    # PARTIAL only survives once it has >= _MIN_HISTORY post-inception closes.
    partial_events = set(dm.metadata.loc[dm.metadata["symbol"] == PARTIAL, "event_id"])
    assert partial_events == {f"EV_{LATE_IDX}"}
    # FULL is present at every event, including the ones PARTIAL lost.
    full_events = set(dm.metadata.loc[dm.metadata["symbol"] == FULL, "event_id"])
    assert full_events == {f"EV_{i}" for i in [*PRE_IDXS, STRADDLE_IDX, EARLY_POST_IDX, LATE_IDX]}

    # Nothing non-finite may reach the learner.
    assert np.isfinite(dm.X.to_numpy()).all()
    assert np.isfinite(dm.y.to_numpy()).all()


# --- (b) full-history symbols unaffected by a partial peer --------------------


def test_full_history_symbol_unaffected_by_partial_peer(
    sessions: pd.DatetimeIndex, full_prices: pd.DataFrame, partial_prices: pd.DataFrame
) -> None:
    events = make_synthetic_events(sessions, n=20, seed=5)
    dm_full = build_design_matrix(events, full_prices, sessions, TARGETS, horizon=HORIZON)
    dm_part = build_design_matrix(events, partial_prices, sessions, TARGETS, horizon=HORIZON)

    # The partial masking must actually bite (PARTIAL rows drop), ...
    assert len(dm_part) < len(dm_full)

    # ... but FULL's rows are identical in count, order, features, and labels.
    mask_f = (dm_full.metadata["symbol"] == FULL).to_numpy()
    mask_p = (dm_part.metadata["symbol"] == FULL).to_numpy()
    assert (
        dm_full.metadata.loc[mask_f, "event_id"].tolist()
        == dm_part.metadata.loc[mask_p, "event_id"].tolist()
    )
    pd.testing.assert_frame_equal(
        dm_full.X.loc[mask_f].reset_index(drop=True),
        dm_part.X.loc[mask_p].reset_index(drop=True),
    )
    pd.testing.assert_series_equal(
        dm_full.y.loc[mask_f].reset_index(drop=True),
        dm_part.y.loc[mask_p].reset_index(drop=True),
    )


# --- (c) inception must not nuke the symbol for the whole window --------------


def test_post_inception_rows_present_and_hand_verified(
    sessions: pd.DatetimeIndex, partial_prices: pd.DataFrame
) -> None:
    events = _events_at(sessions, [BOUNDARY_ABSENT_IDX, BOUNDARY_PRESENT_IDX, LATE_IDX])
    dm = build_design_matrix(events, partial_prices, sessions, TARGETS, horizon=HORIZON)

    partial_events = set(dm.metadata.loc[dm.metadata["symbol"] == PARTIAL, "event_id"])
    # Exactly _MIN_HISTORY post-inception closes at t_info is the keep boundary.
    assert partial_events == {f"EV_{BOUNDARY_PRESENT_IDX}", f"EV_{LATE_IDX}"}

    # Hand-recompute the LATE row from post-inception closes only.
    sel = (dm.metadata["symbol"] == PARTIAL) & (dm.metadata["event_id"] == f"EV_{LATE_IDX}")
    row = dm.metadata[sel].iloc[0]
    i = dm.metadata.index[sel][0]
    inception = sessions[INCEPTION_IDX]
    s = partial_prices.loc[
        (partial_prices.index >= inception) & (partial_prices.index <= row.t_info_date), PARTIAL
    ]
    assert s.notna().all()  # the feature window is entirely post-inception
    assert dm.X.loc[i, "ret_1d"] == pytest.approx(s.iloc[-1] / s.iloc[-2] - 1.0)
    assert dm.X.loc[i, "ret_21d"] == pytest.approx(s.iloc[-1] / s.iloc[-22] - 1.0)

    # Label anchors are both real post-inception closes.
    assert row.label_start_date >= inception and row.label_end_date >= inception
    ls = partial_prices.loc[row.label_start_date, PARTIAL]
    le = partial_prices.loc[row.label_end_date, PARTIAL]
    assert dm.y.loc[i] == pytest.approx(le / ls - 1.0)


# --- (d) no label across the inception boundary -------------------------------


def test_no_label_across_inception_boundary(
    sessions: pd.DatetimeIndex, partial_prices: pd.DataFrame
) -> None:
    # Straddle event: label_start is PARTIAL's last NaN session, label_end is
    # its first real close. Any ffill/imputation would fabricate this label.
    events = _events_at(sessions, [STRADDLE_IDX])
    dm = build_design_matrix(events, partial_prices, sessions, TARGETS, horizon=HORIZON)

    inception = sessions[INCEPTION_IDX]
    # Prove the case is exercised: FULL's row at this event does span inception.
    full_row = dm.metadata[dm.metadata["symbol"] == FULL].iloc[0]
    assert full_row.label_start_date < inception <= full_row.label_end_date
    # PARTIAL must be absent — its label_start close does not exist.
    assert (dm.metadata["symbol"] == PARTIAL).sum() == 0

    # Global invariant on a broad random event set: every emitted row's label
    # anchors are real (finite) closes in the input frame.
    many = make_synthetic_events(sessions, n=20, seed=5)
    dm2 = build_design_matrix(many, partial_prices, sessions, TARGETS, horizon=HORIZON)
    for r in dm2.metadata.itertuples(index=False):
        assert np.isfinite(partial_prices.loc[r.label_start_date, r.symbol])
        assert np.isfinite(partial_prices.loc[r.label_end_date, r.symbol])


# --- row-count bookkeeping -----------------------------------------------------


def test_n_events_reflects_surviving_rows_only(
    sessions: pd.DatetimeIndex, partial_prices: pd.DataFrame
) -> None:
    events = _events_at(sessions, [*PRE_IDXS, STRADDLE_IDX, LATE_IDX])
    dm = build_design_matrix(events, partial_prices, sessions, [PARTIAL], horizon=HORIZON)

    # 4 events in, but only the post-inception one yields a usable PARTIAL row.
    assert len(dm) == 1
    assert dm.n_events == 1
    assert dm.metadata["event_id"].tolist() == [f"EV_{LATE_IDX}"]


def test_all_rows_dropped_raises_not_silent_empty(
    sessions: pd.DatetimeIndex, partial_prices: pd.DataFrame
) -> None:
    events = _events_at(sessions, PRE_IDXS)
    with pytest.raises(ValueError, match="no usable rows"):
        build_design_matrix(events, partial_prices, sessions, [PARTIAL], horizon=HORIZON)
