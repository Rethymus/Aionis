"""Form 8-K material-event filings via EDGAR full-text search (efts).

Third EFTS generation (after ``stakes_13d_efts`` / ``form4_efts``): query recent
8-K filings per issuer, fetch the primary document from EDGAR Archives, and
classify the reported items (``Item 2.01`` completion of acquisition, ``5.02``
officer changes, ``3.01`` delisting, ...). The item list is the legally
mandated event taxonomy — classification is a pure regex over the primary doc,
never a judgement call.

VERIFIED efts query (same shape as form4, 2026-08-21)::

    https://efts.sec.gov/LATEST/search-index?q=&ciks={cik:010d}&forms=8-K
        &dateRange=custom&startdt={start}&enddt={end}&from={n}

  * ``forms=8-K`` matches BOTH 8-K and 8-K/A (amendments).
  * ``_source`` carries ``adsh`` (accession), ``file_date``, ``form``,
    ``display_names`` (``"Apple Inc. (AAPL) (CIK 0000320193)"``).

7-gate: SEC EDGAR public domain (17 U.S.C. §105) — G1✓; PIT via ``file_date`` —
G2✓; immutable (8-K/A amendments are NEW accessions, never silent overwrites) —
G3✓; exploratory display-only — G5; polite ≥2s + idempotent caches — G7✓.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
import structlog

from aionis.ingest.form4_efts import _UA, _cache_dir, _get_json, _policy_get

log = structlog.get_logger()

_EFTS_URL = "https://efts.sec.gov/LATEST/search-index"
_ARCHIVE_BASE = "https://www.sec.gov/Archives/edgar/data"
_ROOT_FORM = "8-K"  # root form; efts expands to 8-K + 8-K/A
_PAGE_SIZE = 100

# Item → category. The precedence list below decides the ONE category shown per
# filing (rare-material first, boilerplate last); the full item list is always
# preserved in ``items``. Unmapped items (ABS 6.xx, technical 5.04-5.06, ...)
# never invent a category: a filing whose items are all unmapped is "other".
_ITEM_CATEGORY: list[tuple[str, str]] = [
    ("3.01", "delisting"),
    ("2.01", "merger_completion"),
    ("5.01", "control_change"),
    ("4.02", "non_reliance"),
    ("1.02", "agreement_termination"),
    ("5.02", "officer_changes"),
    ("2.05", "exit_costs"),
    ("2.03", "financial_obligation"),
    ("1.01", "major_agreement"),
    ("3.03", "security_terms"),
    ("5.03", "charter_amendment"),
    ("5.07", "vote_results"),
    ("2.02", "results"),
    ("7.01", "reg_fd"),
    ("8.01", "other_events"),
    ("9.01", "exhibits"),
]

_ITEM_RE = re.compile(r"Item\s+(\d{1,2}\.\d{2,3})", re.I)

# Exhibit-looking document names — the 8-K primary doc must not be one of these
# (``ex991.htm``, ``a8-kex991q3.htm`` — the "8-k" substring inside an exhibit
# name must NOT fool the primary-doc scorer, so match ``ex<digits>`` anywhere).
_EXHIBIT_RE = re.compile(r"(?:ex|dex)\d", re.I)


def _efts_url(issuer_cik: int, start: str, end: str, from_: int) -> str:
    return (
        f"{_EFTS_URL}?q=&ciks={int(issuer_cik):010d}"
        f"&forms={_ROOT_FORM}"
        f"&dateRange=custom&startdt={start}&enddt={end}&from={from_}"
    )


def extract_8k_items(text: str) -> list[str]:
    """Item numbers reported in an 8-K primary document, sorted unique.

    Handles the entity spellings found in EDGAR HTML: ``&nbsp;`` / ``&#160;``
    (nbsp) and ``&#8201;`` / ``&#8202;`` (thin-space entities used by the
    iXBRL-era rendering of ``Item 2.01`` headers). Pure function.
    """
    if not text:
        return []
    cleaned = text
    for entity in ("&#160;", "&nbsp;", "&#8201;", "&#8202;", "&#8203;", "&thinsp;"):
        cleaned = cleaned.replace(entity, " ")
    found = _ITEM_RE.findall(cleaned)
    return sorted(set(found))


def classify_8k(items: list[str]) -> str:
    """One category code per filing (precedence: rare-material first).

    ``unclassified`` when NO item was extracted (doc shape the regex missed —
    counted honestly, never guessed); ``other`` when items exist but none maps.
    Pure function.
    """
    if not items:
        return "unclassified"
    for item, cat in _ITEM_CATEGORY:
        if item in items:
            return cat
    return "other"


def _parse_company(display_names: list | str | None) -> str:
    """``"Apple Inc. (AAPL) (CIK 0000320193)"`` -> ``"Apple Inc."``."""
    if isinstance(display_names, list) and display_names:
        raw = str(display_names[0])
    elif isinstance(display_names, str):
        raw = display_names
    else:
        return ""
    return raw.split(" (", 1)[0].strip()


def _fetch_efts_hits(
    issuer_cik: int, start: str, end: str, cache_dir: Path | None = None,
) -> list[dict]:
    fp = _cache_dir(cache_dir) / f"efts_form8k_{int(issuer_cik):010d}_{start}_{end}.json"
    if fp.exists():
        return json.loads(fp.read_text())
    out: list[dict] = []
    from_ = 0
    while True:
        data = _get_json(_efts_url(issuer_cik, start, end, from_))
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


def _pick_form8k_doc(index_json: dict, accession: str) -> str | None:
    """Primary 8-K document filename from a filing ``index.json``.

    Scored, never "shortest wins" — the shortest ``.htm`` is usually the XBRL
    rendering (``R1.htm``) or a press-release exhibit (``q1fy27pr.htm``).
    Scores: 0 = primary conventions (EDGAR issuer-date machine naming
    ``nvda-20260818.htm`` or an explicit ``8-k``/``8k`` substring), 1 = other
    non-exhibit ``.htm``, 2 = ``R\\d+`` rendering, 3 = exhibit
    (``ex991.htm`` / ``a8-kex991q3.htm`` — the ``8-k`` inside an exhibit name
    does not fool the exhibit check, which runs first). Lowest score wins,
    shortest name only breaks exact ties. Falls back to the accession ``.txt``.
    """
    items: list[dict] = []
    directory = index_json.get("directory") if isinstance(index_json, dict) else None
    if isinstance(directory, dict):
        raw = directory.get("item", [])
        items = raw if isinstance(raw, list) else [raw]
    elif isinstance(index_json, dict) and isinstance(index_json.get("items"), list):
        items = index_json["items"]

    names = [str(it.get("name", "")) for it in items if isinstance(it, dict)]

    def _score(n: str) -> int:
        low = n.lower()
        if _EXHIBIT_RE.search(low):
            return 3
        if re.match(r"r\d", low):
            return 2
        if re.match(r"^[a-z][a-z0-9]*-\d{8}\.htm$", low) or "8-k" in low or "8k" in low:
            return 0
        return 1

    htms = [n for n in names if n.lower().endswith(".htm") and "index" not in n.lower()]
    if htms:
        return min(htms, key=lambda n: (_score(n), len(n)))
    no_dash = accession.replace("-", "")
    return next(
        (n for n in names if no_dash in n and n.lower().endswith(".txt")), None,
    )


def _doc_url(issuer_cik: int, accession: str, filename: str) -> str:
    return f"{_ARCHIVE_BASE}/{int(issuer_cik)}/{accession.replace('-', '')}/{filename}"


def fetch_form8k_doc(
    issuer_cik: int, accession: str, cache_dir: Path | None = None,
) -> tuple[str, str | None]:
    """Fetch the primary 8-K document text for ``(issuer_cik, accession)``.

    Idempotent (index + doc cached separately). Returns ``(text, doc_filename)``
    — ``("", None)`` when the index lists nothing usable (logged, not raised).
    """
    no_dash = accession.replace("-", "")
    doc_fp = _cache_dir(cache_dir) / f"form8k_doc_{int(issuer_cik):010d}_{no_dash}.bin"
    name_fp = doc_fp.with_suffix(".docname")
    if doc_fp.exists():
        name = name_fp.read_text() if name_fp.exists() else None
        return doc_fp.read_text(encoding="utf-8", errors="replace"), (name or None)

    idx_fp = _cache_dir(cache_dir) / f"form8k_index_{int(issuer_cik):010d}_{no_dash}.json"
    if idx_fp.exists():
        idx = json.loads(idx_fp.read_text())
    else:
        idx = _get_json(f"{_ARCHIVE_BASE}/{int(issuer_cik)}/{no_dash}/index.json")
        idx_fp.write_text(json.dumps(idx))

    doc = _pick_form8k_doc(idx, accession)
    if not doc:
        log.warning("form8k_no_doc_in_index", issuer_cik=issuer_cik, accession=accession)
        return "", None

    text = _policy_get(
        _doc_url(issuer_cik, accession, doc),
        total_attempts=4,
        backoff_base=4,
        backoff_mode="linear",
        headers={"User-Agent": _UA},
        timeout=60,
    ).text
    doc_fp.write_text(text, encoding="utf-8")
    name_fp.write_text(doc)
    return text, doc


def fetch_form8k_events(
    issuer_cik: int, *, ticker: str, start: str, end: str,
    cache_dir: Path | None = None,
) -> pd.DataFrame:
    """All classified 8-K events for ``issuer_cik`` in [start, end].

    EFTS metadata -> per-accession primary-doc fetch -> item extraction ->
    category. Failures per accession are logged and skipped. Returns
    ``[issuer_cik, ticker, company, filing_date, accession, form, items,
    category, doc_url]`` sorted by ``filing_date`` (PIT anchor) descending.
    """
    hits = _fetch_efts_hits(issuer_cik, start, end, cache_dir)
    rows: list[dict] = []
    for s in hits:
        d = str(s.get("file_date", ""))
        accession = str(s.get("adsh", ""))
        if not d or not accession or not (start <= d <= end):
            continue
        text, doc = fetch_form8k_doc(issuer_cik, accession, cache_dir)
        items = extract_8k_items(text) if text else []
        rows.append({
            "issuer_cik": int(issuer_cik),
            "ticker": ticker,
            "company": _parse_company(s.get("display_names")),
            "filing_date": d,
            "accession": accession,
            "form": str(s.get("form", "")),
            "items": ",".join(items),
            "category": classify_8k(items),
            "doc_url": _doc_url(issuer_cik, accession, doc) if doc else "",
        })
    df = pd.DataFrame(
        rows,
        columns=[
            "issuer_cik", "ticker", "company", "filing_date",
            "accession", "form", "items", "category", "doc_url",
        ],
    )
    if df.empty:
        return df
    return df.sort_values("filing_date", ascending=False).reset_index(drop=True)
