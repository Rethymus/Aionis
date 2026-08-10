"""SC 13D filings via the EDGAR daily crawler index (display-only, exploratory).

The EFTS ``search-index`` stopped indexing SC 13D after 2024-12-17 (see memory
``aionis-edgar-efts-sc13d-frozen``). The EDGAR **daily crawler index**
(``crawler.{YYYYMMDD}.idx``) is the ground-truth, CURRENT dissemination feed —
one file per business day listing every filing disseminated, with company name,
form type, CIK, date, and URL. This module reads it to recover recent SC 13D
stakes that EFTS can no longer see.

EDGAR's daily crawler index is organized "by Company Name"; for SC 13D it lists
the filing under the **subject company** (the issuer/target whose securities are
reported — the reporting person is often an individual and is not indexed as a
"company"). So each parsed row gives the TARGET + its CIK + the filing date +
accession URL. The filer (activist) is in the cover page, not the index; left
blank here and surfaced honestly downstream.

Public domain (SEC). Polite via ``_policy_get`` (≥2s host spacing + backoff).
Filed-date PIT. Display-only, exploratory — NOT a research claim.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path

from aionis.config import settings
from aionis.ingest.universe import _policy_get

_UA = "Aionis research 13d-daily-index contact@example.com"
_DAILY_INDEX = "https://www.sec.gov/Archives/edgar/daily-index/{year}/QTR{q}/crawler.{yyyymmdd}.idx"
# Data rows are whitespace-aligned; fields are separated by 2+ spaces. The form
# type ("SCHEDULE 13D" / "SCHEDULE 13D/A") contains a single internal space, so a
# 2+-space split keeps it as one token.
_FIELD_SPLIT = re.compile(r"\s{2,}")


def _cache_dir(cache_dir: Path | None = None) -> Path:
    d = cache_dir or settings.data_dir / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _daily_index_url(d: date) -> str:
    return _DAILY_INDEX.format(year=d.year, q=(d.month - 1) // 3 + 1, yyyymmdd=d.strftime("%Y%m%d"))


def _daily_index_cache_path(d: date, cache_dir: Path | None) -> Path:
    return _cache_dir(cache_dir) / f"daily_idx_{d.strftime('%Y%m%d')}.txt"


def fetch_daily_crawler_index(
    d: date, cache_dir: Path | None = None, *, force: bool = False
) -> str:
    """Fetch (and cache) one business day's crawler index text.

    Idempotent: a cached file is returned as-is unless ``force``. Weekends return
    an empty string (EDGAR disseminates nothing Sat/Sun).
    """
    if d.weekday() >= 5:
        return ""
    fp = _daily_index_cache_path(d, cache_dir)
    if fp.exists() and not force:
        return fp.read_text()
    url = _daily_index_url(d)
    r = _policy_get(
        url, total_attempts=4, backoff_base=4, headers={"User-Agent": _UA}, timeout=60
    )
    text = r.text
    fp.write_text(text)
    return text


def parse_daily_13d(idx_text: str) -> list[dict]:
    """Parse a crawler index text → SC 13D / SC 13D/A rows.

    Pure function (no network) — the load-bearing, hermetic-testable piece. Each
    row: {target, target_cik, date, form, is_amendment, accession, url}.

    The index header is ~6 descriptive lines; data rows follow. A data row's
    fields (Company Name | Form Type | CIK | Date | URL) are separated by 2+
    spaces. We keep only rows whose Form Type is ``SCHEDULE 13D`` or the ``/A``
    amendment.
    """
    out: list[dict] = []
    for line in idx_text.splitlines():
        fields = _FIELD_SPLIT.split(line.strip())
        # Need: company name, form, CIK, date, URL — 5 fields.
        if len(fields) < 5:
            continue
        form = fields[1]
        if form not in ("SCHEDULE 13D", "SCHEDULE 13D/A"):
            continue
        try:
            cik = int(fields[2])
        except ValueError:
            continue
        datestr = fields[3]
        if not re.fullmatch(r"\d{8}", datestr):
            continue
        url = fields[4]
        # accession = the directory name in the URL (.../{accession-no-dashes}/).
        accession = url.rstrip("/").rsplit("/", 1)[-1]
        out.append(
            {
                "target": fields[0].strip(),
                "target_cik": cik,
                "date": f"{datestr[:4]}-{datestr[4:6]}-{datestr[6:8]}",
                "form": "SC 13D/A" if form.endswith("/A") else "SC 13D",
                "is_amendment": form.endswith("/A"),
                "accession": accession,
                "url": url,
            }
        )
    return out


def fetch_recent_13d_daily(
    start: date, end: date, cache_dir: Path | None = None, *, force: bool = False
) -> list[dict]:
    """Every SC 13D filing in [start, end], business days only.

    Polite: one fetch per business day (the index lists ALL of that day's
    filings). Cache-per-day makes re-runs free. Returns rows sorted newest-first.
    """
    rows: list[dict] = []
    cur = start
    while cur <= end:
        try:
            text = fetch_daily_crawler_index(cur, cache_dir, force=force)
        except Exception:
            # Per-day resilience: a 403/429/5xx on one day (EDGAR rate-limits)
            # must not kill the whole backfill. Skip + continue; cached days still
            # parse. The cron re-runs daily and fills gaps once EDGAR cools.
            cur += timedelta(days=1)
            continue
        if text:
            rows.extend(parse_daily_13d(text))
        cur += timedelta(days=1)
    rows.sort(key=lambda r: r["date"], reverse=True)
    return rows
