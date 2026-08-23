"""US Form D exempt-offering notices via EDGAR full-text search (efts).

Primary-market (一级市场) stream for the terminal's /ipo page — Form D
notices (Regulation D / other exempt offerings) complement the S-1/424B4
public-IPO stream. Whole-market FORM-LEVEL query, the identical no-CIK
pattern as :mod:`aionis.ingest.form_ipo`.

VERIFIED efts query (2026-08-23 live probe; do not re-derive)::

    https://efts.sec.gov/LATEST/search-index?q=&forms=D
        &dateRange=custom&startdt={start}&enddt={end}&from={n}

  * ``forms=D`` expands to BOTH ``D`` and ``D/A`` (probe page: 87 D + 13 D/A;
    same root-form expansion engine as ``S-1`` -> ``S-1/A``). Do NOT pass a
    comma list — efts mis-parses root+amendment lists.
  * Volume: 3,324 hits over a 23-day window (~145/day) — a 90-day window is
    ~4,300 filings / ~44 pages, polite at >=2s spacing per run.
  * ``display_names`` carries NO ticker for private filers (``"ImpactMatrix,
    LLC  (CIK 0002151517)"``) — ``ticker`` stays empty honestly, never
    guessed (a Form D issuer is typically pre-symbol by definition).

STATUS DERIVATION (v1, filing-stream level): ``D`` -> ``new`` (a new exempt
offering notice, 新申报); ``D/A`` -> ``amendment`` (修正 — a new accession,
the same immutable-amendment discipline as S-1/A and 8-K/A).

HONEST v1 LIMITS (disclosed, never papered over): the offering amount, sold
amount, industry, and related persons live INSIDE the filing's primary XML
document; v1 does not fetch or parse them (one primary doc per filing would
cost ~4,300 extra requests for the window — deferred to keep the lane
polite). Each row links the filing's EDGAR index page instead.

7-gate: SEC EDGAR public domain (17 U.S.C. §105) — G1✓; PIT via
``file_date`` — G2✓; immutable (D/A amendments are NEW accessions) — G3✓;
exploratory display-only — G5✓; polite >=2s + idempotent caches — G7✓.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from aionis.ingest.form4_efts import _cache_dir, _get_json
from aionis.ingest.form_ipo import _filing_index_url, _issuer_cik, _parse_company, parse_ticker

_EFTS_URL = "https://efts.sec.gov/LATEST/search-index"
_PAGE_SIZE = 100

_ROOT_FORM = "D"


def _efts_url(start: str, end: str, from_: int) -> str:
    """One efts page URL for the FORM-LEVEL (whole-market) Form D query."""
    return (
        f"{_EFTS_URL}?q=&forms={_ROOT_FORM}"
        f"&dateRange=custom&startdt={start}&enddt={end}&from={from_}"
    )


def _fetch_efts_hits(start: str, end: str, cache_dir: Path | None = None) -> list[dict]:
    """Every ``_source`` for Form D / D/A filings filed in [start, end]."""
    fp = _cache_dir(cache_dir) / f"efts_form_d_{start}_{end}.json"
    if fp.exists():
        return json.loads(fp.read_text())
    out: list[dict] = []
    from_ = 0
    while True:
        data = _get_json(_efts_url(start, end, from_))
        hits = data.get("hits", {})
        batch = [h.get("_source", {}) for h in hits.get("hits", [])]
        out.extend(batch)
        total_node = hits.get("total", 0)
        total = total_node.get("value", 0) if isinstance(total_node, dict) else total_node
        if len(batch) < _PAGE_SIZE or len(out) >= total:
            break
        from_ += _PAGE_SIZE
    fp.write_text(json.dumps(out))
    return out


def form_d_status(form: str) -> str:
    """Filing-level status from the (immutable) form type: D -> new,
    D/A -> amendment; anything else -> "" (dropped, defense-in-depth)."""
    f = str(form).strip().upper()
    if f == "D":
        return "new"
    if f == "D/A":
        return "amendment"
    return ""


def fetch_form_d_filings(
    *, start: str, end: str, cache_dir: Path | None = None,
) -> pd.DataFrame:
    """All Form D / D/A filings (whole market) filed in [start, end].

    Rows are per-ACCESSION (a D/A amendment is a new row), deduplicated
    across pages. Returns ``[issuer_cik, company, ticker, filed_date, form,
    status, accession, doc_url]`` sorted by ``filed_date`` descending.
    ``ticker`` is empty for private filers (the normal case — honest, never
    guessed). PIT anchor is ``filed_date`` (immutable).
    """
    rows: list[dict] = []
    seen: set[str] = set()
    for s in _fetch_efts_hits(start, end, cache_dir):
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
            "status": form_d_status(s.get("form", "")),
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
