"""13D activist-stake event-indicator feature — hermetic (synthetic events).

Pins :mod:`aionis.features.stakes_13d_signal`: the indicator fires for
``window_days`` AFTER a filing (never before — PIT via filing_date), drops back
to 0 past the window, tickers with no event stay 0, and multiple filings/tickers
behave correctly.
"""
from __future__ import annotations

import pandas as pd

from aionis.features.stakes_13d_signal import stakes_13d_event_panel


def test_indicator_fires_after_filing_not_before() -> None:
    dates = pd.bdate_range("2024-01-02", periods=10)  # Jan 2,3,4,5,8,9,10,11,12,15
    events = pd.DataFrame({"ticker": ["A"], "filing_date": ["2024-01-05"]})  # Jan 5
    w = stakes_13d_event_panel(events, dates, ["A", "B"], window_days=7)

    assert w.loc[pd.Timestamp("2024-01-04"), "A"] == 0.0  # day before filing
    assert w.loc[pd.Timestamp("2024-01-05"), "A"] == 1.0  # filing day -> visible
    assert w.loc[pd.Timestamp("2024-01-12"), "A"] == 1.0  # +7 cal days (in window)
    assert w.loc[pd.Timestamp("2024-01-15"), "A"] == 0.0  # +10 cal days (past window)
    assert (w["B"] == 0.0).all()  # no event for B


def test_pit_filing_not_visible_before_filing_date() -> None:
    dates = pd.bdate_range("2024-01-02", periods=5)  # Jan 2,3,4,5,8
    events = pd.DataFrame({"ticker": ["A"], "filing_date": ["2024-01-08"]})  # last date
    w = stakes_13d_event_panel(events, dates, ["A"], window_days=30)

    # every date strictly before the filing is 0
    assert w.loc[: pd.Timestamp("2024-01-05"), "A"].sum() == 0.0
    assert w.loc[pd.Timestamp("2024-01-08"), "A"] == 1.0


def test_window_boundary_is_inclusive() -> None:
    dates = pd.bdate_range("2024-01-02", periods=10)  # Jan 2,3,4,5,8,9,...
    events = pd.DataFrame({"ticker": ["A"], "filing_date": ["2024-01-02"]})
    w = stakes_13d_event_panel(events, dates, ["A"], window_days=5)

    # firing window = [Jan2, Jan7] (5 calendar days, inclusive). gap is calendar
    # days from the filing: Jan5 = gap 3 (in), Jan8 = gap 6 (past).
    assert w.loc[pd.Timestamp("2024-01-05"), "A"] == 1.0   # gap 3, in window
    assert w.loc[pd.Timestamp("2024-01-08"), "A"] == 0.0   # gap 6, past window


def test_multiple_filings_extend_the_window() -> None:
    dates = pd.bdate_range("2024-01-02", periods=30)
    events = pd.DataFrame({
        "ticker": ["A", "A"],
        "filing_date": ["2024-01-05", "2024-02-01"],
    })
    w = stakes_13d_event_panel(events, dates, ["A"], window_days=10)

    # both filings contribute; the indicator is 1 anywhere within 10 days of either
    assert w.loc[pd.Timestamp("2024-01-05"), "A"] == 1.0
    assert w.loc[pd.Timestamp("2024-02-01"), "A"] == 1.0
    # a gap well between the two filings is 0
    assert w.loc[pd.Timestamp("2024-01-22"), "A"] == 0.0


def test_empty_events_is_all_zeros() -> None:
    dates = pd.bdate_range("2024-01-02", periods=5)
    w = stakes_13d_event_panel(pd.DataFrame(columns=["ticker", "filing_date"]),
                               dates, ["A", "B"], window_days=30)
    assert (w == 0.0).all().all()
    assert list(w.columns) == ["A", "B"]
