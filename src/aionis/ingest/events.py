"""Scheduled macro-event ingestion: CPI/NFP via FRED, FOMC via Fed calendar.

Returns a tidy frame [event_id, event_type, event_ts] with tz-aware
America/New_York timestamps. Event *text* (the as-released primary document) is
fetched separately in ``extraction`` (Phase 2).

The FRED path uses the public REST API + ``requests`` (no extra dependency beyond
a free key) and sets the canonical 08:30 ET release time. The FOMC path scrapes
the Fed's published calendar; that HTML is redesign-fragile, so it fails loudly
and a CSV override is supported via ``load_events_csv``.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
import structlog

from aionis.features.alignment import NYSE_TZ

log = structlog.get_logger()

MACRO_RELEASE_TIME = "08:30"  # CPI / NFP
FOMC_RELEASE_TIME = "14:00"  # FOMC statement

_FRED_RELEASE_DATES = "https://api.stlouisfed.org/fred/release/dates"
_FOMC_CALENDAR = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"


def _with_time(d: pd.Timestamp, hhmm: str, tz: str = NYSE_TZ) -> pd.Timestamp:
    h, m = (int(x) for x in hhmm.split(":"))
    return (
        pd.Timestamp(d).tz_localize(None).normalize() + pd.Timedelta(hours=h, minutes=m)
    ).tz_localize(tz)


def fetch_fred_release_events(
    fred_api_key: str,
    release_id: int,
    event_type: str,
    start: str,
    end: str,
    release_time: str = MACRO_RELEASE_TIME,
) -> pd.DataFrame:
    """CPI/NFP: one event per historical release date of a FRED release."""
    import requests

    params = {"release_id": release_id, "api_key": fred_api_key, "file_type": "json"}
    resp = requests.get(_FRED_RELEASE_DATES, params=params, timeout=30)
    resp.raise_for_status()
    dates = [pd.Timestamp(r["date"]) for r in resp.json().get("release_dates", [])]
    mask = (pd.Series(dates) >= pd.Timestamp(start)) & (pd.Series(dates) <= pd.Timestamp(end))
    dates = [d for d, keep in zip(dates, mask.values, strict=False) if keep]
    if not dates:
        log.warning("fred_no_release_dates", release_id=release_id, event_type=event_type)
        return _empty_events()
    ts = [_with_time(d, release_time) for d in dates]
    return _frame(event_type, ts)


def fetch_fomc_events(start: str, end: str) -> pd.DataFrame:
    """FOMC statement dates at 14:00 ET, scraped from the Fed calendar.

    Fragile by nature (HTML redesigns). On any parsing problem it raises so the
    caller can fall back to ``load_events_csv`` rather than silently returning a
    wrong/partial calendar.
    """
    import requests
    from bs4 import BeautifulSoup

    resp = requests.get(_FOMC_CALENDAR, timeout=30, headers={"User-Agent": "aionis/0.1"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Meeting dates appear as "January 31 - February 1" style text or M/D/YYYY.
    # Collect every M/D/YYYY occurrence, then collapse consecutive trading days:
    # a 2-day meeting's statement lands on the later date.
    text = soup.get_text(" ")
    found = re.findall(r"(\d{1,2}/\d{1,2}/\d{4})", text)
    dates = sorted({pd.Timestamp(d) for d in found})
    if not dates:
        raise RuntimeError(
            "FOMC calendar parse returned no dates (HTML may have changed). "
            "Supply FOMC dates via load_events_csv() instead."
        )

    # Heuristic: meetings cluster as adjacent calendar/business days; keep the
    # last day of each <=2-day cluster as the statement date.
    statement_dates: list[pd.Timestamp] = []
    cluster: list[pd.Timestamp] = []
    for d in dates:
        if cluster and (d - cluster[-1]).days <= 4:
            cluster.append(d)
        else:
            if cluster:
                statement_dates.append(cluster[-1])
            cluster = [d]
    if cluster:
        statement_dates.append(cluster[-1])

    s = pd.Timestamp(start)
    e = pd.Timestamp(end)
    statement_dates = [d for d in statement_dates if s <= d <= e]
    if not statement_dates:
        return _empty_events()
    # Validity guard: FOMC statements are virtually always released on Wednesdays
    # (2-day meetings end midweek). If the scrape produced many non-Wednesdays the
    # regex is almost certainly catching unrelated page dates (minutes, testimony,
    # footers) — fail loudly rather than ship wrong event anchors.
    wed_share = sum(1 for d in statement_dates if d.weekday() == 2) / len(statement_dates)
    if wed_share < 0.7:
        raise RuntimeError(
            f"FOMC parse sanity check failed: only {wed_share:.0%} of parsed dates are "
            "Wednesdays. The calendar HTML likely changed; supply dates via --events-csv."
        )
    ts = [_with_time(d, FOMC_RELEASE_TIME) for d in statement_dates]
    log.info("fomc_parsed", n=len(ts), wed_share=f"{wed_share:.0%}")
    return _frame("FOMC", ts)


def fetch_events(
    start: str,
    end: str,
    fred_api_key: str | None,
    event_types: tuple[str, ...] = ("FOMC", "CPI", "NFP"),
    fred_releases: dict[str, int] | None = None,
) -> pd.DataFrame:
    """Union of all requested event sources, deduped by event_id."""
    from aionis.config import FRED_RELEASES

    fred_releases = fred_releases or FRED_RELEASES
    frames: list[pd.DataFrame] = []
    for et in event_types:
        if et == "FOMC":
            # Do NOT swallow FOMC failures: silently dropping the most market-moving
            # event type invalidates a pre-registered experiment. Let it raise so the
            # caller supplies a deterministic --events-csv override instead.
            frames.append(fetch_fomc_events(start, end))
        elif et in fred_releases:
            if not fred_api_key:
                log.warning("skipping_fred_event_no_key", event_type=et)
                continue
            frames.append(
                fetch_fred_release_events(fred_api_key, fred_releases[et], et, start, end)
            )
    if not frames:
        return _empty_events()
    out = pd.concat(frames, ignore_index=True).drop_duplicates("event_id").reset_index(drop=True)
    log.info("events_fetched", n=len(out), types=sorted(out.event_type.unique()))
    return out


def load_events_csv(path: str | Path) -> pd.DataFrame:
    """Manual override: CSV with columns event_type,date (YYYY-MM-DD) [+time HH:MM]."""
    df = pd.read_csv(path, parse_dates=["date"])
    rows = []
    for r in df.itertuples(index=False):
        t = getattr(r, "time", None) or (
            FOMC_RELEASE_TIME if r.event_type == "FOMC" else MACRO_RELEASE_TIME
        )
        rows.append(
            {
                "event_id": f"{r.event_type}_{pd.Timestamp(r.date):%Y%m%d}",
                "event_type": r.event_type,
                "event_ts": _with_time(pd.Timestamp(r.date), t),
            }
        )
    return pd.DataFrame(rows).drop_duplicates("event_id").reset_index(drop=True)


def _frame(event_type: str, ts: list[pd.Timestamp]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event_id": [f"{event_type}_{t.strftime('%Y%m%d')}" for t in ts],
            "event_type": event_type,
            "event_ts": ts,
        }
    )


def _empty_events() -> pd.DataFrame:
    return pd.DataFrame(columns=["event_id", "event_type", "event_ts"])
