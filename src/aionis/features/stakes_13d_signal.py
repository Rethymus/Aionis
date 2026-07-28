"""13D activist-stake event-indicator feature (Phase D WRL.Relationship).

An SC 13D filing is the canonical ownership-edge event. This module turns the
per-issuer 13D filing stream (from :mod:`aionis.ingest.stakes_13d`) into a
per-(ticker, date) feature: 1.0 if at least one activist 13D was filed for that
ticker within the trailing ``window_days`` ending at ``d``, else 0.0.

Point-in-time by construction: a filing at ``F`` is visible at ``d >= F`` and
NEVER at ``d < F`` (a backward ``merge_asof`` on ``filing_date`` finds the most-
recent filing on/before ``d``; the indicator then fires only while ``d - F <=
window_days``). This mirrors the as-of discipline of
:func:`aionis.ingest.fundamentals.pit_align` and the earnings-surprise accessor.
Permissive licenses only (pandas).
"""
from __future__ import annotations

import pandas as pd


def stakes_13d_event_panel(
    events_long: pd.DataFrame,
    as_of_dates: pd.DatetimeIndex,
    tickers: list[str],
    *,
    window_days: int = 60,
) -> pd.DataFrame:
    """Wide (as_of_dates x tickers) 13D event-indicator panel.

    Args:
        events_long: ``[ticker, filing_date]`` of EXTERNAL (non-self) activist
            13D filings — e.g. the output of the self-filing-filtered stream.
            Tickers not present here get an all-zero column.
        as_of_dates: the session grid (sorted; the feature-alignment calendar).
        tickers: the cross-section (column order).
        window_days: the post-filing window over which the indicator stays 1
            (default 60 ~ 3 months, the post-13D drift horizon). ``d`` fires iff
            a filing exists with ``0 <= d - F <= window_days``.

    Returns a wide float frame (1.0 / 0.0); a filing at ``F`` is visible at
    ``d >= F`` only (PIT), and drops back to 0 after ``window_days``.
    """
    dates = pd.DatetimeIndex(as_of_dates).normalize()
    wide = pd.DataFrame(0.0, index=dates, columns=list(tickers))
    if events_long is None or events_long.empty:
        return wide
    ev = events_long.copy()
    ev["filing_date"] = pd.to_datetime(ev["filing_date"]).dt.normalize()
    left = pd.DataFrame({"d": dates})
    for t in tickers:
        fd = ev.loc[ev["ticker"] == t, "filing_date"].drop_duplicates().sort_values()
        if fd.empty:
            continue
        right = pd.DataFrame({"f": fd.to_numpy()})
        # backward asof: most-recent filing on/before each d (NaN before the first)
        m = pd.merge_asof(left, right, left_on="d", right_on="f", direction="backward")
        gap = (m["d"] - m["f"]).dt.days  # NaT -> NaN where no filing yet
        wide[t] = ((gap >= 0) & (gap <= window_days)).astype(float).to_numpy()
    return wide
