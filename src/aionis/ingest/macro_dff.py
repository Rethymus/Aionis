"""DFF (federal funds effective rate) — ALFRED vintage ingest + PIT as-of series.

Baseline-ladder macro source (``docs/baseline-ladder.md``): the effective
federal funds rate is a US-government series (FRED, public domain — G1 on the
same path as VIX in ``docs/data-intake-rubric.md``; no extra license sign-off).
FRED vintages are immutable (G3 — historical values are not silently
rewritten), so the FIRST print of each reference date is the frozen truth and
the series is PIT-safe via the ALFRED as-of join (same discipline as
``aionis.features.macro_surprise``).

The daily as-of level series is built with the SAME strictness as the
macro-surprise prior-month rule::

    level(d) = latest DFF first print with realtime_start STRICTLY BEFORE d

``merge_asof(..., allow_exact_matches=False)`` encodes that: FRED publishes the
DFF value for day d at ~16:30 ET on day d — AFTER the equity close — so a value
only becomes knowable on d+1. ``dff_daily_changes`` is the first difference of
that as-of level series (one-day conservative; it never borrows same-day
information).

The ΔDFF series is used ONLY as the factor input for the stock-level rolling
``beta_dff`` exposure (``aionis.features.ff5``) — never as a raw feature column
(a market-wide time series would be cross-sectionally CONSTANT; RD-13 forbids
it).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import structlog

from aionis.features.macro_surprise import fetch_alfred_vintages

log = structlog.get_logger()

DFF_SERIES_ID = "DFF"


def fetch_dff_vintages(fred_api_key: str, cache_dir: Path) -> pd.DataFrame:
    """Vintage frame [ref_date, realtime_start, value] for DFF, cached.

    Raw ALFRED JSON is cached at ``data/cache/alfred_DFF.json`` (the shared
    ALFRED cache); a cache hit makes no HTTP call.
    """
    vintages = fetch_alfred_vintages(DFF_SERIES_ID, fred_api_key, cache_dir)
    log.info("dff_vintages_loaded", n_obs=len(vintages))
    return vintages


def dff_as_of_levels(
    as_of_dates: pd.DatetimeIndex,
    vintages: pd.DataFrame,
) -> pd.Series:
    """PIT as-of DFF level at each of ``as_of_dates`` (strictly-before rule).

    First print per reference date (minimum ``realtime_start`` — later vintages
    of the same ref date, i.e. revisions, lose), then backward as-of join with
    ``allow_exact_matches=False``: the level at date d is the latest first print
    published STRICTLY BEFORE d. A same-day (16:30 ET) print therefore never
    enters the value at d itself — it becomes knowable at d+1.

    Args:
        as_of_dates: trading sessions at which the level is needed (sorted).
        vintages: [ref_date, realtime_start, value] frame from
            :func:`fetch_dff_vintages`.

    Returns:
        Date-indexed Series ``dff_level``; NaN before the first strictly-prior
        print.
    """
    if "ref_date" not in vintages.columns or "realtime_start" not in vintages.columns:
        raise ValueError("vintages must have columns ref_date / realtime_start / value")
    fp_idx = vintages.groupby("ref_date")["realtime_start"].idxmin()
    first_prints = (
        vintages.loc[fp_idx, ["realtime_start", "value"]]
        .sort_values("realtime_start")
        .reset_index(drop=True)
    )
    dates = pd.DatetimeIndex(as_of_dates).normalize()
    left = pd.DataFrame({"d": dates})
    right = first_prints.rename(columns={"realtime_start": "d"})
    merged = pd.merge_asof(
        left,
        right,
        on="d",
        direction="backward",
        allow_exact_matches=False,  # strictly before d — same-day print is future info
    )
    out = pd.Series(
        merged["value"].to_numpy(dtype=float),
        index=dates,
        name="dff_level",
    )
    return out


def dff_daily_changes(
    as_of_dates: pd.DatetimeIndex,
    vintages: pd.DataFrame,
) -> pd.Series:
    """ΔDFF: first difference of the as-of level series (PIT, one-day lagged).

    Returns a date-indexed Series ``dff_change`` (NaN on the first date, and
    everywhere the level is not yet knowable). This is the factor input for the
    stock-level ``beta_dff`` exposure.
    """
    return dff_as_of_levels(as_of_dates, vintages).diff().rename("dff_change")


__all__ = [
    "DFF_SERIES_ID",
    "fetch_dff_vintages",
    "dff_as_of_levels",
    "dff_daily_changes",
]
