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

import json
from pathlib import Path

import pandas as pd
import structlog

log = structlog.get_logger()

DFF_SERIES_ID = "DFF"

# FRED ALFRED hard cap: at most 2000 vintage dates per request. DFF is a DAILY
# series (vintages accrue daily), so a full-history request (realtime_start=2000-01-01
# ... realtime_end=9999-12-31) exceeds the cap (5093 vintages) and FRED returns 400.
# The workaround is to SLICE the realtime window per calendar year — each slice is
# within the cap (verified: 2016/2020/2024 each return ~23-26k observations) — and
# accumulate. The per-year window must cover every vintage the analysis period needs.
_DFF_REALTIME_START_YEAR = 2015   # one year before the analysis window (2016+)
_DFF_REALTIME_END_YEAR = 2026     # current year (2026-08-03)

# FRED page cap (matches aionis.features.macro_surprise._PAGE_LIMIT).
_DFF_PAGE_LIMIT = 100_000


def _current_utc_year() -> int:
    from datetime import datetime, timezone

    return int(datetime.now(timezone.utc).strftime("%Y"))


def _download_dff_vintage_year(fred_api_key: str, year: int) -> list[dict]:
    """One ALFRED observations page (or set of pages) for DFF within a year window.

    FRED rejects a ``realtime_end`` AFTER today's date (400), so the current
    year's window is clamped to today (the analysis never needs a future
    vintage anyway — only vintages with ``realtime_start <= today`` exist).
    """
    from datetime import datetime, timezone

    from aionis.ingest.universe import _policy_get

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    realtime_end = f"{year}-12-31" if year < int(today[:4]) else today
    url = "https://api.stlouisfed.org/fred/series/observations"
    observations: list[dict] = []
    offset = 0
    while True:
        params = {
            "series_id": DFF_SERIES_ID,
            "api_key": fred_api_key,
            "file_type": "json",
            "realtime_start": f"{year}-01-01",
            "realtime_end": realtime_end,
            "limit": _DFF_PAGE_LIMIT,
            "offset": offset,
        }
        resp = _policy_get(url, params=params, timeout=60)
        resp.raise_for_status()
        rows = resp.json().get("observations", [])
        observations.extend(rows)
        offset += len(rows)
        if len(rows) < _DFF_PAGE_LIMIT:
            break
    return observations


def fetch_dff_vintages(fred_api_key: str, cache_dir: Path) -> pd.DataFrame:
    """Vintage frame [ref_date, realtime_start, value] for DFF, cached.

    Raw ALFRED JSON is cached at ``data/cache/alfred_DFF.json`` (the shared
    ALFRED cache). A cache hit previously returned verbatim — which froze the
    fedfunds/real-rate display cards at whatever day the cache was first built
    (observed 2026-09-04: tail stuck at 2026-08-25 while every other panel
    advanced). On a hit the CURRENT year's slice is now re-downloaded and
    merged, so new days/vintages accrue without re-pulling 2015+ history.

    Contract-safe: FRED vintages are immutable (G3) and the analysis consumes
    FIRST prints only (``dff_as_of_levels`` idxmin rule), so appended
    later-realtime rows can never rewrite a historical as-of value — they only
    add days that did not exist when the cache was written.

    DFF is a DAILY FRED series: a single ALFRED request for the full realtime
    window exceeds FRED's 2000-vintage hard cap (5093 vintages -> HTTP 400).
    This fetcher therefore SLICES the realtime window per calendar year and
    accumulates the pages (each slice is within the cap; verified 2016/2020/2024
    each return ~23-26k observations). The merged payload is cached the same
    way as the shared ALFRED cache.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"alfred_{DFF_SERIES_ID}.json"
    if cache_file.exists():
        payload = json.loads(cache_file.read_text())
        if fred_api_key:
            try:
                current_year = max(_DFF_REALTIME_START_YEAR, _current_utc_year())
                fresh = _download_dff_vintage_year(fred_api_key, current_year)
                stale_keys = {
                    (o["date"], o["realtime_start"], o.get("value"))
                    for o in payload.get("observations", [])
                }
                added = [
                    o
                    for o in fresh
                    if (o["date"], o["realtime_start"], o.get("value")) not in stale_keys
                ]
                if added:
                    payload.setdefault("observations", []).extend(added)
                    cache_file.write_text(json.dumps(payload))
                    log.info(
                        "dff_alfred_cache_tail_merged",
                        year=current_year,
                        added=len(added),
                        path=str(cache_file),
                    )
                else:
                    log.info("dff_alfred_cache_current", year=current_year, path=str(cache_file))
            except Exception as exc:
                # The cached panel stays authoritative on a FRED outage — a
                # failed tail refresh degrades to the plain cache hit, it never
                # kills the consumer (export/regime build) that called us.
                log.warning(
                    "dff_alfred_tail_refresh_failed",
                    error=str(exc)[:160],
                    path=str(cache_file),
                )
        else:
            log.info("dff_alfred_cache_hit_no_key", path=str(cache_file))
        vintages = _vintages_frame(payload)
        log.info("dff_alfred_cache_hit", path=str(cache_file), n_obs=len(vintages))
        return vintages

    observations: list[dict] = []
    for year in range(_DFF_REALTIME_START_YEAR, _DFF_REALTIME_END_YEAR + 1):
        obs_year = _download_dff_vintage_year(fred_api_key, year)
        observations.extend(obs_year)
        log.info(
            "dff_alfred_slice_fetched",
            year=year,
            n_obs=len(obs_year),
        )
    payload = {"observations": observations}
    cache_file.write_text(json.dumps(payload))
    vintages = _vintages_frame(payload)
    log.info("dff_alfred_cache_written", path=str(cache_file), n_obs=len(vintages))
    return vintages


def _vintages_frame(payload: dict) -> pd.DataFrame:
    """Raw ALFRED payload -> [ref_date, realtime_start, value] frame (missing dropped)."""
    rows = payload.get("observations", [])
    recs = []
    for o in rows:
        value = o.get("value")
        if value is None or value == ".":
            continue
        recs.append(
            {
                "ref_date": o["date"],
                "realtime_start": o["realtime_start"],
                "value": float(value),
            }
        )
    df = pd.DataFrame(recs)
    # FRED serializes dates as ISO strings; coerce to datetime64 so the
    # as-of merge (merge_asof on realtime_start) has matching dtypes.
    df["ref_date"] = pd.to_datetime(df["ref_date"])
    df["realtime_start"] = pd.to_datetime(df["realtime_start"])
    return df


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
