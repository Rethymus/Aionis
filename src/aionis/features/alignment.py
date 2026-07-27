"""Event-to-market alignment — the single source of truth for leakage safety.

Hard rule (see README):

    t_info_date      = last NYSE close STRICTLY BEFORE event_ts
    label_start_date = first NYSE close AT OR AFTER event_ts   (reaction embedded)
    label_end_date   = the session h trading sessions after label_start_date
    target           = close[label_end] / close[label_start] - 1

Every feature must be a function of closes on dates <= t_info_date. Nothing in
this module reads a close on or after label_start_date; the feature builders in
``market_state.py`` slice with ``prices.loc[:t_info_date]`` and are verified by
a behavioral leakage test (``tests/test_alignment.py``).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import pandas_market_calendars as mcal

NYSE_TZ = "America/New_York"
NYSE_CLOSE_OFFSET = pd.Timedelta(hours=16)


def nyse_sessions(start: str | pd.Timestamp, end: str | pd.Timestamp) -> pd.DatetimeIndex:
    """Sorted DatetimeIndex of NYSE session dates in [start, end] (naive dates).

    pandas-market-calendars v5.0+ removed ``sessions_in_range``; ``valid_days``
    returns tz-aware UTC midnights which we collapse to naive calendar dates.
    """
    cal = mcal.get_calendar("XNYS")
    sessions = cal.valid_days(pd.Timestamp(start), pd.Timestamp(end))
    return pd.DatetimeIndex([pd.Timestamp(d).tz_localize(None).normalize() for d in sessions])


def session_close_ts(session_date: str | pd.Timestamp) -> pd.Timestamp:
    """Wall-clock close timestamp (16:00 ET, tz-aware) for a session date."""
    d = pd.Timestamp(session_date).tz_localize(None).normalize()
    return (d + NYSE_CLOSE_OFFSET).tz_localize(NYSE_TZ)


def _ensure_et(ts: pd.Timestamp) -> pd.Timestamp:
    ts = pd.Timestamp(ts)
    if ts.tzinfo is None:
        ts = ts.tz_localize(NYSE_TZ)
    return ts


@dataclass(frozen=True)
class Alignment:
    """Point-in-time anchors for one event."""

    event_ts: pd.Timestamp
    t_info_date: pd.Timestamp  # last close strictly before the event
    label_start_date: pd.Timestamp  # first close at/after the event
    label_end_date: pd.Timestamp  # h sessions after label_start

    @property
    def prediction_time(self) -> pd.Timestamp:
        """When the prediction is made: close of t_info_date (model knows ≤ this)."""
        return session_close_ts(self.t_info_date)

    @property
    def evaluation_time(self) -> pd.Timestamp:
        """When the label is fully realized: close of label_end_date."""
        return session_close_ts(self.label_end_date)

    @property
    def event_date(self) -> pd.Timestamp:
        """Naive calendar date of the event — used as the cluster group."""
        return pd.Timestamp(self.event_ts).tz_localize(None).normalize()


def align_event(
    event_ts: str | pd.Timestamp,
    sessions: pd.DatetimeIndex,
    horizon: int,
) -> Alignment:
    """Map one event timestamp onto (t_info, label_start, label_end) sessions.

    Uses session *close* timestamps (date + 16:00 ET) so that intraday event
    times (FOMC 14:00 vs CPI/NFP 08:30) are handled by one rule.
    """
    if horizon < 1:
        raise ValueError("horizon must be >= 1")
    if len(sessions) == 0:
        raise ValueError("no sessions provided")

    event_ts = _ensure_et(event_ts)
    close_ts = pd.DatetimeIndex([session_close_ts(d) for d in sessions])

    before = close_ts < event_ts
    if not before.any():
        raise ValueError(f"event_ts {event_ts} is at/before the first session close")
    t_info_idx = int(np.nonzero(before)[0][-1])

    at_or_after = close_ts >= event_ts
    if not at_or_after.any():
        raise ValueError(f"event_ts {event_ts} is after the last session close")
    label_start_idx = int(np.nonzero(at_or_after)[0][0])

    label_end_idx = label_start_idx + horizon
    if label_end_idx >= len(sessions):
        raise ValueError(
            f"horizon {horizon} extends beyond available sessions for event {event_ts}"
        )

    return Alignment(
        event_ts=event_ts,
        t_info_date=sessions[t_info_idx],
        label_start_date=sessions[label_start_idx],
        label_end_date=sessions[label_end_idx],
    )


def align_events(
    events: pd.DataFrame,
    sessions: pd.DatetimeIndex,
    horizon: int,
) -> pd.DataFrame:
    """Align every row of ``events`` onto the session grid.

    ``events`` must have columns: event_id, event_type, event_ts.
    Returns one row per event with the Alignment fields plus prediction/eval times.
    Events that fall outside the session grid are dropped with a warning count.
    """
    required = {"event_id", "event_type", "event_ts"}
    missing = required - set(events.columns)
    if missing:
        raise ValueError(f"events missing columns: {missing}")

    rows: list[dict] = []
    dropped = 0
    for ev in events.itertuples(index=False):
        try:
            a = align_event(ev.event_ts, sessions, horizon)
        except ValueError:
            dropped += 1
            continue
        rows.append(
            {
                "event_id": ev.event_id,
                "event_type": ev.event_type,
                "event_ts": a.event_ts,
                "t_info_date": a.t_info_date,
                "label_start_date": a.label_start_date,
                "label_end_date": a.label_end_date,
                "prediction_time": a.prediction_time,
                "evaluation_time": a.evaluation_time,
                "event_date": a.event_date,
            }
        )
    if dropped:
        import warnings

        warnings.warn(
            f"align_events: dropped {dropped} event(s) outside the session grid", stacklevel=2
        )
    if not rows:
        return pd.DataFrame(
            columns=[
                "event_id",
                "event_type",
                "event_ts",
                "t_info_date",
                "label_start_date",
                "label_end_date",
                "prediction_time",
                "evaluation_time",
                "event_date",
            ]
        )
    return pd.DataFrame(rows)
