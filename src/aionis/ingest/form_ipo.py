"""US IPO registration/pricing filings via EDGAR full-text search (efts).

IPO stream for the terminal's ``/ipo`` panel (filing-stream level, v1). Unlike
:mod:`aionis.ingest.form4_efts` / :mod:`aionis.ingest.form8k` (per-ISSUER
queries), an IPO pipeline is a WHOLE-MARKET question — the filers are not yet
known companies — so this module drops the ``ciks=`` parameter entirely and
queries EFTS at the FORM level, the same no-CIK pattern as
:mod:`aionis.ingest.stakes_13d_efts` (whose CIK is optional plumbing, not a
universe restriction).

VERIFIED efts queries (2026-08-22 live probe; do not re-derive)::

    https://efts.sec.gov/LATEST/search-index?q=&forms=S-1
        &dateRange=custom&startdt={start}&enddt={end}&from={n}
    https://efts.sec.gov/LATEST/search-index?q=&forms=424B4
        &dateRange=custom&startdt={start}&enddt={end}&from={n}

  * ``forms=S-1`` (root form) expands to BOTH ``S-1`` and ``S-1/A`` (probe:
    827 hits over a 119-day window, ``form`` field carries ``S-1/A`` on
    amendments). Do NOT pass the comma list — efts mis-parses root+amendment
    lists (verified for SC 13D in ``stakes_13d_efts``; same engine).
  * ``forms=424B4`` returns only ``424B4`` (219 hits over the same window).
  * ``_source`` carries ``ciks`` (``["0001786471"]`` — the filer/issuer for a
    registration statement), ``display_names``
    (``"Aptera Motors Corp  (SEV)  (CIK 0001786471)"`` — ticker embedded in
    the FIRST paren group when the filer has one; pre-ticker S-1 filers carry
    only the CIK group), ``adsh`` (accession), ``file_date``, ``form``.
    ``display_symbols`` is null on every probed hit — the ticker must be
    parsed from ``display_names``, never assumed.

STATUS DERIVATION (v1, filing-stream level — the legally mandated markers):

  * ``S-1`` / ``S-1/A`` → ``filed`` — a registration statement is on file
    with the SEC (已申报). Amendments are new accessions (new rows), the
    same immutable discipline as 8-K/A.
  * ``424B4`` → ``priced`` — the statutory FINAL prospectus (Securities Act
    §5(b) Rule 424(b)(4)) is filed AFTER pricing, so its appearance marks a
    PRICED IPO (已定价).

HONEST v1 LIMITS (disclosed in the panel methodology, never papered over):
the offer price, share count, proceeds, and expected listing date live INSIDE
the prospectus documents; v1 does not fetch or parse them (resolving one
primary doc per filing would cost ~1,000 extra index.json requests for the
window — deferred to keep the daily lane polite). Each row instead links the
filing's EDGAR index page, which lists every document in the filing.

7-gate: SEC EDGAR public domain (17 U.S.C. §105) — G1✓; PIT via ``file_date``
— G2✓; immutable (S-1/A amendments are NEW accessions, never silent
overwrites) — G3✓; exploratory display-only — G5✓; polite ≥2s +
idempotent caches — G7✓. See ``docs/data-intake-edgar-ipo.md``.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
import structlog

from aionis.ingest.form4_efts import _cache_dir, _get_json

log = structlog.get_logger()

_EFTS_URL = "https://efts.sec.gov/LATEST/search-index"
_ARCHIVE_BASE = "https://www.sec.gov/Archives/edgar/data"
_PAGE_SIZE = 100  # efts default + max per request; paginate via from=

# Root forms: S-1 expands to S-1 + S-1/A; 424B4 has no amendment family in
# practice (probe: every 424B4 hit carried form == "424B4").
_ROOT_FORMS = ("S-1", "424B4")

# Ticker group inside display_names: "Aptera Motors Corp  (SEV)  (CIK 0001786471)".
# The CIK group ("CIK 000…") never matches — it carries a space + digits, which
# fall outside the character class after "CIK"'s 3 letters would need a ')'
# immediately. EDGAR only wraps real symbols in the first group.
_TICKER_RE = re.compile(r"\(([A-Z][A-Z0-9.]{0,9})\)")


def _efts_url(root_form: str, start: str, end: str, from_: int) -> str:
    """One efts page URL for a FORM-LEVEL (whole-market) query.

    No ``ciks=`` parameter — an IPO pipeline cannot know the filers in
    advance. ``forms`` uses the root form (``S-1`` expands to ``S-1/A``).
    Exposed for tests."""
    return (
        f"{_EFTS_URL}?q=&forms={root_form.replace(' ', '%20')}"
        f"&dateRange=custom&startdt={start}&enddt={end}&from={from_}"
    )


def _fetch_efts_hits(
    root_form: str, start: str, end: str, cache_dir: Path | None = None,
) -> list[dict]:
    """Every ``_source`` for ``root_form`` filings filed in [start, end],
    paginated across ``from=`` pages and cached as one assembled list."""
    fp = _cache_dir(cache_dir) / f"efts_ipo_{root_form.replace('/', '-')}_{start}_{end}.json"
    if fp.exists():
        return json.loads(fp.read_text())
    out: list[dict] = []
    from_ = 0
    while True:
        data = _get_json(_efts_url(root_form, start, end, from_))
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


def _parse_company(display_names: list | str | None) -> str:
    """``"Aptera Motors Corp  (SEV)  (CIK 0001786471)"`` -> ``"Aptera Motors Corp"``.

    Same split as :func:`aionis.ingest.form8k._parse_company` — the name is
    everything before the first paren group."""
    if isinstance(display_names, list) and display_names:
        raw = str(display_names[0])
    elif isinstance(display_names, str):
        raw = display_names
    else:
        return ""
    return raw.split(" (", 1)[0].strip()


def parse_ticker(display_names: list | str | None) -> str:
    """Ticker embedded in ``display_names`` if the filer carries one.

    ``"Aptera Motors Corp  (SEV)  (CIK 0001786471)"`` -> ``"SEV"``;
    ``"Acme Holdings (CIK 0001234567)"`` -> ``""`` (an S-1 filer that has
    not chosen/registered a symbol yet — honest empty, never guessed).
    Pure function."""
    if isinstance(display_names, list) and display_names:
        raw = str(display_names[0])
    elif isinstance(display_names, str):
        raw = display_names
    else:
        return ""
    m = _TICKER_RE.search(raw)
    return m.group(1) if m else ""


def ipo_status(form: str) -> str:
    """Filing-level IPO status from the (immutable) form type.

    ``S-1``/``S-1/A`` -> ``filed`` (registration on file, 已申报);
    ``424B4`` -> ``priced`` (statutory final prospectus = pricing complete,
    已定价). Any other form is ``""`` (dropped by the caller — the EFTS
    query never returns one, this is defense-in-depth). Pure function."""
    f = str(form).strip().upper()
    if f in ("S-1", "S-1/A"):
        return "filed"
    if f == "424B4":
        return "priced"
    return ""


def _filing_index_url(issuer_cik: int, accession: str) -> str:
    """EDGAR filing-index URL — one stable link per filing, zero extra requests.

    v1 deliberately links the filing INDEX page (it lists every document,
    including the prospectus) instead of resolving the primary document via
    a per-accession ``index.json`` fetch (~1,000 extra requests for the
    window). Disclosed in the panel methodology."""
    return f"{_ARCHIVE_BASE}/{int(issuer_cik)}/{accession.replace('-', '')}/{accession}-index.htm"


def _issuer_cik(source: dict) -> int:
    """First named CIK — for a registration statement that is the filer/issuer."""
    for c in source.get("ciks") or []:
        try:
            return int(str(c))
        except (TypeError, ValueError):
            continue
    return 0


def fetch_ipo_filings(
    *, start: str, end: str, cache_dir: Path | None = None,
) -> pd.DataFrame:
    """All S-1 / S-1/A / 424B4 filings (whole market) filed in [start, end].

    Rows are per-ACCESSION (the filing stream: an S-1/A amendment is a new
    row, mirroring how 8-K/A streams in /events), deduplicated across the two
    root-form queries. Returns ``[issuer_cik, company, ticker, filed_date,
    form, status, accession, doc_url]`` sorted by ``filed_date`` descending.
    ``ticker`` is empty when the filer carries no symbol yet (honest, never
    guessed). PIT anchor is ``filed_date`` (immutable).
    """
    rows: list[dict] = []
    seen: set[str] = set()
    for root_form in _ROOT_FORMS:
        for s in _fetch_efts_hits(root_form, start, end, cache_dir):
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
                "status": ipo_status(s.get("form", "")),
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
