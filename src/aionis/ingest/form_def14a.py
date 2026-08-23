"""US DEF 14A proxy-statement filings via EDGAR full-text search (efts).

Board/executive governance stream for the terminal's /executives page — the
definitive proxy statement (股东大会代理委托书) carries directors, executive
compensation, and beneficial-ownership tables. Whole-market FORM-LEVEL query,
the identical no-CIK pattern as :mod:`aionis.ingest.form_ipo` /
:mod:`aionis.ingest.form_d`.

VERIFIED efts query (2026-08-23 live probe; do not re-derive)::

    https://efts.sec.gov/LATEST/search-index?q=&forms=DEF%2014A
        &dateRange=custom&startdt={start}&enddt={end}&from={n}

  * ``forms=DEF%2014A`` (root form, space URL-encoded per form_ipo): **1,387
    hits over the 120-day window 2026-04-25..2026-08-23** — far under EFTS's
    10,000 cap (no split triggered today). Every sampled hit (pages at
    ``from=0`` and ``from=700``) carries ``form == "DEF 14A"`` with
    ``root_forms == ["DEF 14A"]``; ``display_symbols`` is null — the ticker
    is parsed from ``display_names`` (public filers usually carry one).
  * A DIRECT ``forms=DEF 14A/A`` query returned **0 hits** for the window:
    proxy amendments are in practice filed as **DEFA14A** (additional proxy
    soliciting material — a SEPARATE root form, 2,278 hits in the window,
    out of v1 scope, disclosed). The status map keeps the ``DEF 14A/A`` ->
    ``amendment`` arm as defense-in-depth (same as form_d's D/A arm) in case
    a future window carries one.
  * The fetch window's fixed anchor only grows forward, so within a year it
    rolls into the next Jan-Apr proxy season (DEF 14A volume is strongly
    seasonal — off-season ~12/day vs peak multiples of that) and WILL
    approach the 10,000 cap; the fetch therefore reuses form13f_dir's
    adaptive cap-split from day one.

STATUS DERIVATION (v1, filing-stream level): ``DEF 14A`` -> ``new`` (a new
definitive proxy statement, 新申报); ``DEF 14A/A`` -> ``amendment`` (修正 — a
new accession, the same immutable-amendment discipline as D/A and 8-K/A).

HONEST v1 LIMITS (disclosed, never papered over): director/executive NAMES,
compensation, and ownership live INSIDE the proxy statement's primary HTML
document (thousands of lines per filing); v1 does not fetch or parse them at
full-window scale (resolving + parsing one primary document per filing would
cost ~1,400 extra requests for the window). Each row links the filing's EDGAR
index page instead. v0.2 (2026-08-23) ships the BOUNDED person-level lane for
the panel's newest ~150 filings via :mod:`aionis.ingest.def14a_persons`
(conservative tiered parsing, honest nulls; the full-window deferral above
still holds for the stream panel).

7-gate: SEC EDGAR public domain (17 U.S.C. §105) — G1✓; PIT via
``file_date`` — G2✓; immutable (amendments are NEW accessions) — G3✓;
exploratory display-only — G5✓; polite >=2s page spacing + idempotent
caches — G7✓. See ``docs/data-intake-edgar-def14a.md``.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd

from aionis.ingest.form4_efts import _cache_dir, _get_json
from aionis.ingest.form_ipo import _filing_index_url, _issuer_cik, _parse_company, parse_ticker

_EFTS_URL = "https://efts.sec.gov/LATEST/search-index"
_PAGE_SIZE = 100

_ROOT_FORM = "DEF 14A"  # space URL-encoded below (form_ipo pattern)

# Cap-split contingency (form13f_dir pattern): the fixed anchor's window only
# grows, so it will eventually roll into proxy season and approach the cap.
# A window this small cannot approach 10k — the recursion floor.
_SPLIT_FLOOR_DAYS = 21


def _efts_url(start: str, end: str, from_: int) -> str:
    """One efts page URL for the FORM-LEVEL (whole-market) DEF 14A query.

    ``forms`` uses the root form with the space URL-encoded (form_ipo's
    ``root_form.replace(' ', '%20')`` pattern). Exposed for tests."""
    return (
        f"{_EFTS_URL}?q=&forms={_ROOT_FORM.replace(' ', '%20')}"
        f"&dateRange=custom&startdt={start}&enddt={end}&from={from_}"
    )


def _fetch_window_hits(
    start: str, end: str, cache_dir: Path | None = None,
) -> tuple[list[dict], bool]:
    """Every ``_source`` for DEF 14A-family filings filed in [start, end],
    paginated (>=2.1s sleep between page GETs) and cached as one list.

    Returns ``(hits, capped)``: ``capped`` is True when the declared total hit
    EFTS's 10,000 ceiling and the caller should split the window
    (:func:`fetch_def14a_window` does; form13f_dir's cap-split pattern)."""
    fp = _cache_dir(cache_dir) / f"efts_def14a_{start}_{end}.json"
    if fp.exists():
        cached = json.loads(fp.read_text())
        return cached["hits"], cached["capped"]
    out: list[dict] = []
    from_ = 0
    total = 0
    while True:
        if from_:
            time.sleep(2.1)
        data = _get_json(_efts_url(start, end, from_))
        hits = data.get("hits", {})
        batch = [h.get("_source", {}) for h in hits.get("hits", [])]
        if not total:
            total_node = hits.get("total", 0)
            total = (
                total_node.get("value", 0)
                if isinstance(total_node, dict)
                else int(total_node or 0)
            )
        out.extend(batch)
        if len(batch) < _PAGE_SIZE or len(out) >= total:
            break
        from_ += _PAGE_SIZE
    capped = total >= 10_000
    fp.write_text(json.dumps({"hits": out, "capped": capped, "total": total}))
    return out, capped


def fetch_def14a_window(
    start: str, end: str, cache_dir: Path | None = None,
) -> list[dict]:
    """Full hit list for [start, end], splitting adaptively near the cap.

    Not triggered by the 2026-08-23 probe (1,387 hits) but the fetch window's
    fixed anchor only grows — the recursion is the durable guard for the
    Jan-Apr proxy season."""
    hits, capped = _fetch_window_hits(start, end, cache_dir)
    if not capped:
        return hits
    # Split at the range midpoint (Timestamp arithmetic — day-number
    # averaging would break across month boundaries).
    ts_start, ts_end = pd.Timestamp(start), pd.Timestamp(end)
    if (ts_end - ts_start).days <= _SPLIT_FLOOR_DAYS:
        # Floor reached with a capped window: keep the capped hits (the
        # honest newest-first 10k) — disclosed by the caller.
        return hits
    mid = (ts_start + (ts_end - ts_start) / 2).date().isoformat()
    left = fetch_def14a_window(start, mid, cache_dir)
    time.sleep(2.1)
    right = fetch_def14a_window(mid, end, cache_dir)
    return left + right


def def14a_status(form: str) -> str:
    """Filing-level status from the (immutable) form type: DEF 14A -> new,
    DEF 14A/A -> amendment; anything else -> "" (dropped, defense-in-depth)."""
    f = str(form).strip().upper()
    if f == "DEF 14A":
        return "new"
    if f == "DEF 14A/A":
        return "amendment"
    return ""


def fetch_form_def14a_filings(
    *, start: str, end: str, cache_dir: Path | None = None,
) -> pd.DataFrame:
    """All DEF 14A-family filings (whole market) filed in [start, end].

    Rows are per-ACCESSION (an amendment is a new row), deduplicated across
    pages and split halves. Returns ``[issuer_cik, company, ticker,
    filed_date, form, status, accession, doc_url]`` sorted by ``filed_date``
    descending. ``ticker`` is empty when the display name carries none
    (honest, never guessed). PIT anchor is ``filed_date`` (immutable)."""
    rows: list[dict] = []
    seen: set[str] = set()
    for s in fetch_def14a_window(start, end, cache_dir):
        d = str(s.get("file_date", ""))
        accession = str(s.get("adsh", ""))
        if not d or not accession or not (start <= d <= end):
            continue
        if accession in seen:
            continue
        seen.add(accession)
        cik = _issuer_cik(s)
        rows.append({
            "issuer_cik": cik,
            "company": _parse_company(s.get("display_names")),
            "ticker": parse_ticker(s.get("display_names")),
            "filed_date": d,
            "form": str(s.get("form", "")),
            "status": def14a_status(s.get("form", "")),
            "accession": accession,
            "doc_url": _filing_index_url(cik, accession) if cik else "",
        })
    df = pd.DataFrame(
        rows,
        columns=[
            "issuer_cik", "company", "ticker", "filed_date",
            "form", "status", "accession", "doc_url",
        ],
    )
    if df.empty:
        return df
    return df.sort_values("filed_date", ascending=False).reset_index(drop=True)
