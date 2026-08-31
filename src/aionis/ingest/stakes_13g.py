"""SC 13G passive-stake filings via the EDGAR daily crawler index (display-only).

The passive twin of :mod:`aionis.ingest.stakes_13d_daily_index`. A 13G marks a
>5% holder that attests PASSIVE intent (no control/activist plan) — index funds
and quiet institutions; a 13D asserts ACTIVE intent. Aionis already streams 13D
(smart_money panel); this module adds the 13G/13G/A form-level stream.

WHY THE DAILY INDEX, NOT EFTS (live probe 2026-08-22; do not re-derive)::

    https://efts.sec.gov/LATEST/search-index?q=&forms=SC%2013G
        &dateRange=custom&startdt={start}&enddt={end}&from={n}

  * ``forms=SC 13G`` (root form; expands to ``SC 13G/A``, the same engine as
    ``SC 13D``) returned **0 hits** for every 2025/2026 window probed (e.g.
    2026-08-15..22, and the full 2026-04-25..08-22 window).
  * The same query over 2024-01-01..2024-12-17 returns >10,000 hits whose
    ``file_date`` tops out at **2024-12-17** — the EFTS ``search-index`` froze
    on the whole Schedule 13 family (``aionis-edgar-efts-sc13d-frozen``; the
    13D panel hit the identical wall and moved to the daily index).
  * EFTS therefore CANNOT source a recent 13G window; the EDGAR **daily crawler
    index** (``crawler.{YYYYMMDD}.idx``) is the current dissemination feed and
    lists every ``SCHEDULE 13G`` / ``SCHEDULE 13G/A`` filed each business day.

The daily index is organized "by Company Name" and lists a filing under EVERY
covered company — the subject AND the filer entities (verified live: accession
0000919574-26-005663 appears under both Catheter Precision, Inc. (subject) and
C/M CAPITAL PARTNERS, LP (filer)). Rows are therefore per-(accession, company);
the export lane groups by accession and resolves subject vs filer the same way
the 13D daily path does (``_sm_dedup_enrich`` in export_terminal_data.py).

HONEST v1 LIMITS (disclosed in the panel methodology, never papered over): the
% ownership, share count, and the event date live INSIDE the filing documents;
v1 does not fetch or parse them (a per-accession ``index.json`` fetch would cost
thousands of extra requests for the window — deferred to keep the daily lane
polite). The the reference site-style passive/active/exited state machine likewise needs
per-document parsing and is explicitly DEFERRED — each row is one immutable
filing event (a 13G/A amendment is a new accession, never a silent overwrite).

SEC EDGAR public domain (17 U.S.C. §105) — G1✓; PIT via the dissemination
``date`` (filed-date) — G2✓; immutable amendments — G3✓; exploratory
display-only — G5✓; polite ≥2s + idempotent per-day caches — G7✓. See
``docs/data-intake-edgar-13g.md``.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path

# Reuse the 13D module's per-day fetch + shared per-day cache (daily_idx_*.txt):
# the 13D cron and the 13G fetch then share one polite set of per-day pulls.
from aionis.ingest.stakes_13d_daily_index import fetch_daily_crawler_index

# Data rows are whitespace-aligned; fields are separated by 2+ spaces. The form
# type ("SCHEDULE 13G" / "SCHEDULE 13G/A") contains a single internal space, so
# a 2+-space split keeps it as one token.
_FIELD_SPLIT = re.compile(r"\s{2,}")

_13G_FORMS = ("SCHEDULE 13G", "SCHEDULE 13G/A")


def parse_daily_13g(idx_text: str) -> list[dict]:
    """Parse a crawler index text → SC 13G / SC 13G/A rows.

    Pure function (no network) — the load-bearing, hermetic-testable piece.
    Each row: ``{target, target_cik, date, form, is_amendment, accession, url}``
    where ``target`` is the indexed company name (subject OR filer — the index
    lists the filing under every covered company; the export lane resolves
    which is which per accession). ``accession`` is the no-dash directory name,
    with EDGAR's newer ``-index.htm`` suffix stripped so it is a stable join
    key across index formats. Rows whose form type is neither SCHEDULE 13G nor
    its /A amendment are dropped.
    """
    out: list[dict] = []
    for line in idx_text.splitlines():
        fields = _FIELD_SPLIT.split(line.strip())
        # Need: company name, form, CIK, date, URL — 5 fields.
        if len(fields) < 5:
            continue
        form = fields[1]
        if form not in _13G_FORMS:
            continue
        try:
            cik = int(fields[2])
        except ValueError:
            continue
        datestr = fields[3]
        if not re.fullmatch(r"\d{8}", datestr):
            continue
        url = fields[4]
        # accession = the directory name in the URL (.../{accession-no-dashes}/
        # or .../{accession}-index.htm — both formats appear in the live feed).
        accession = url.rstrip("/").rsplit("/", 1)[-1].removesuffix("-index.htm")
        out.append(
            {
                "target": fields[0].strip(),
                "target_cik": cik,
                "date": f"{datestr[:4]}-{datestr[4:6]}-{datestr[6:8]}",
                "form": "SC 13G/A" if form.endswith("/A") else "SC 13G",
                "is_amendment": form.endswith("/A"),
                "accession": accession,
                "url": url,
            }
        )
    return out


def fetch_recent_13g_daily(
    start: date, end: date, cache_dir: Path | None = None, *, force: bool = False
) -> list[dict]:
    """Every SC 13G / SC 13G/A filing in [start, end], business days only.

    Polite: one fetch per business day via :func:`fetch_daily_crawler_index`
    (≥2s host spacing + backoff; the index lists ALL of that day's filings).
    The shared per-day cache makes re-runs free; per-day failures (403/429/5xx)
    skip + continue — the cron re-runs daily and fills gaps once EDGAR cools.
    Returns rows sorted newest-first (per-(accession, company) — dedup happens
    in the export lane, mirroring the 13D daily path).
    """
    rows: list[dict] = []
    cur = start
    while cur <= end:
        try:
            text = fetch_daily_crawler_index(cur, cache_dir, force=force)
        except Exception:
            cur += timedelta(days=1)
            continue
        if text:
            rows.extend(parse_daily_13g(text))
        cur += timedelta(days=1)
    rows.sort(key=lambda r: r["date"], reverse=True)
    return rows
