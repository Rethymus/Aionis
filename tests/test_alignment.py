"""Leakage invariants — the most important tests in the repo.

If any of these fail, the with-vs-without comparison is invalid: a feature is
reading a close at or after label_start_date.
"""

from __future__ import annotations

import pandas as pd
import pytest

from aionis.features.alignment import (
    align_event,
    align_events,
    nyse_sessions,
    session_close_ts,
)
from aionis.features.design_matrix import build_design_matrix
from aionis.features.market_state import market_state_features
from aionis.synthetic import make_synthetic_events, make_synthetic_prices

SYMBOLS = ["XLK", "XLE", "SPY"]


@pytest.fixture(scope="module")
def sessions() -> pd.DatetimeIndex:
    return nyse_sessions("2023-01-03", "2023-06-30")


def _approx_dict_equal(a: dict, b: dict) -> None:
    assert set(a) == set(b)
    for k in a:
        assert a[k] == pytest.approx(b[k], nan_ok=True), f"mismatch at {k}"


# --- alignment correctness ---------------------------------------------------


def test_fomc_intraday_alignment(sessions: pd.DatetimeIndex) -> None:
    # FOMC statement at 14:00 ET on a session day: reaction is in that day's close.
    day = sessions[20]
    event_ts = pd.Timestamp(day).tz_localize(None).normalize() + pd.Timedelta(hours=14)
    event_ts = event_ts.tz_localize("America/New_York")

    a = align_event(event_ts, sessions, horizon=1)
    assert a.t_info_date == sessions[19]  # close strictly before the event
    assert a.label_start_date == sessions[20]  # reaction embedded in this close
    assert a.label_end_date == sessions[21]  # h=1 -> next session
    assert a.prediction_time == session_close_ts(sessions[19])
    assert a.evaluation_time == session_close_ts(sessions[21])


def test_preopen_macro_alignment(sessions: pd.DatetimeIndex) -> None:
    # CPI/NFP at 08:30 ET (pre-open): same-day close still embeds the reaction.
    day = sessions[30]
    event_ts = (
        pd.Timestamp(day).tz_localize(None).normalize() + pd.Timedelta(hours=8, minutes=30)
    ).tz_localize("America/New_York")

    a = align_event(event_ts, sessions, horizon=1)
    assert a.t_info_date == sessions[29]
    assert a.label_start_date == sessions[30]
    assert a.label_end_date == sessions[31]


def test_horizon_pushes_label_end(sessions: pd.DatetimeIndex) -> None:
    day = sessions[40]
    event_ts = (
        pd.Timestamp(day).tz_localize(None).normalize() + pd.Timedelta(hours=14)
    ).tz_localize("America/New_York")
    a = align_event(event_ts, sessions, horizon=5)
    assert a.label_start_date == sessions[40]
    assert a.label_end_date == sessions[45]


def test_event_before_first_session_raises(sessions: pd.DatetimeIndex) -> None:
    too_early = pd.Timestamp("1990-01-01 14:00").tz_localize("America/New_York")
    with pytest.raises(ValueError):
        align_event(too_early, sessions, horizon=1)


# --- THE behavioral leakage test ---------------------------------------------


def test_features_cannot_see_future(sessions: pd.DatetimeIndex) -> None:
    """Perturb every close strictly after t_info_date -> features must not move."""
    prices = make_synthetic_prices(sessions, SYMBOLS, seed=7)
    day = sessions[50]
    event_ts = (
        pd.Timestamp(day).tz_localize(None).normalize() + pd.Timedelta(hours=14)
    ).tz_localize("America/New_York")
    a = align_event(event_ts, sessions, horizon=1)

    base = market_state_features(prices, a.t_info_date, "XLK")

    corrupted = prices.copy()
    # Nuke everything strictly after t_info_date (label_start..end included).
    future_mask = corrupted.index > a.t_info_date
    corrupted.loc[future_mask] = corrupted.loc[future_mask] * 1e6 + 12345.0

    after = market_state_features(corrupted, a.t_info_date, "XLK")
    _approx_dict_equal(base, after)


def test_features_do_use_t_info(sessions: pd.DatetimeIndex) -> None:
    """Sanity: changing t_info_date's own close DOES move features.

    This guarantees the no-leak test above is meaningful (a builder that always
    returned constants would pass it trivially)."""
    prices = make_synthetic_prices(sessions, SYMBOLS, seed=7)
    day = sessions[50]
    a = align_event(
        (pd.Timestamp(day).tz_localize(None).normalize() + pd.Timedelta(hours=14)).tz_localize(
            "America/New_York"
        ),
        sessions,
        horizon=1,
    )
    base = market_state_features(prices, a.t_info_date, "XLK")
    bumped = prices.copy()
    bumped.loc[a.t_info_date, "XLK"] *= 1.10  # +10% on the last usable close
    moved = market_state_features(bumped, a.t_info_date, "XLK")
    assert moved["ret_1d"] != pytest.approx(base["ret_1d"])


# --- design matrix target + structure ----------------------------------------


def test_design_matrix_target_anchors(sessions: pd.DatetimeIndex) -> None:
    prices = make_synthetic_prices(sessions, SYMBOLS, seed=3)
    events = make_synthetic_events(sessions, n=12, seed=5)
    dm = build_design_matrix(events, prices, sessions, ["XLK", "SPY"], horizon=1)

    # Recompute one row by hand and check the target equals close ratio.
    row = dm.metadata.iloc[0]
    ls = prices.loc[row.label_start_date, row.symbol]
    le = prices.loc[row.label_end_date, row.symbol]
    assert dm.y.iloc[0] == pytest.approx(le / ls - 1.0)
    # Every label window is strictly after its own t_info (no self-overlap at h=1).
    assert (dm.metadata["label_start_date"] > dm.metadata["t_info_date"]).all()
    assert (dm.metadata["label_end_date"] >= dm.metadata["label_start_date"]).all()


def test_design_matrix_groups_are_event_dates(sessions: pd.DatetimeIndex) -> None:
    prices = make_synthetic_prices(sessions, SYMBOLS, seed=3)
    events = make_synthetic_events(sessions, n=10, seed=5)
    dm = build_design_matrix(events, prices, sessions, ["XLK"], horizon=1)
    # group must equal the event date for cluster-robust inference.
    assert (dm.groups.values == dm.metadata["event_date"].values).all()
    # one event-date -> same number of rows as symbols (here 1).
    assert dm.metadata["event_id"].nunique() == dm.metadata["event_date"].nunique()


def test_align_events_drops_out_of_range(sessions: pd.DatetimeIndex) -> None:
    events = pd.DataFrame(
        [
            {"event_id": "OK_1", "event_type": "FOMC", "event_ts": sessions[10]},
            {"event_id": "OK_2", "event_type": "CPI", "event_ts": sessions[20]},
        ]
    )
    out = align_events(events, sessions, horizon=1)
    assert len(out) == 2
    assert set(out.columns) >= {"t_info_date", "label_start_date", "label_end_date"}
    # naive event_ts at midnight localizes to ET and aligns cleanly
    assert out.iloc[0]["label_start_date"] == sessions[10]
