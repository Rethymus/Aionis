"""Bounded percent-of-class parsing for SC 13D/13G filings (display-only).

The competitor's signature /stakes feature — the holding percentage with a
previous-vs-current contrast ("40.5% (prev 12.2%)") and the active/passive/
exited state machine — needs values that live INSIDE the filing documents,
not in any index. This module adds the BOUNDED second stage the 13G/13D
panels deferred: for the panels' VISIBLE rows only (13G top-150 + 13D
top-120), fetch the filing's EDGAR ``index.json`` (1 request), pick the
primary document, fetch it (1 request), and regex-extract:

* ``pct_now``  — the cover-page percent of class. Priority: the structured
  XML tags (``<percentOfClass>`` on 13D-style, ``<classPercent>`` on
  13G-style submissions, first reporting person's cover page — group filings
  repeat one cover per reporter), else the HTML cover label ("Percent of
  class: 5.5%" / "PERCENT OF CLASS REPRESENTED BY AMOUNT IN ROW (11) 5.5%"),
  else the narrative "X.X% of the ... class / outstanding shares" sentence.
* ``pct_prev`` — amendments only, from "previous 5.2%"-style narrative
  ("previously reported 5.2%", "increased from 5.2% to 6.1%", "down from
  5.2%"). Original (non-/A) filings never get a prev — enforced by the
  caller passing ``is_amendment`` and re-enforced by the export contract.

Everything not found is an HONEST null — never guessed, never defaulted.
Failures are counted, not papered over.

Politeness: every request rides ``_policy_get`` (≥2s host spacing + bounded
transient-only retry), so ~2 requests/row × 2s ≈ 20-30 min for the ~270
visible rows. Idempotent per-accession disk cache
(``data/cache/stakes_pct_parsed.json``): rows already parsed (``ok``) are
never re-fetched; failed rows (``ok: false``) are retried on the next run.

SEC EDGAR public domain (17 U.S.C. §105) — G1✓; the filing text is the
as-filed immutable document (amendments are new accessions) — G3✓;
display-only, exploratory — G5✓; regex-extraction boundaries disclosed in
the panel methodology — G6✓. See ``docs/data-intake-edgar-13g.md``.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from aionis.config import settings
from aionis.ingest.universe import _policy_get

_UA = "Aionis research stakes-pct contact@example.com"

# --- primary-document selection (index.json → filename) -----------------------

# The EDGAR-generated index/header pages are never the form itself.
_INDEX_PAGE = re.compile(r"-index(-headers)?\.html?$", re.IGNORECASE)
# Traditional filer-prepared primary docs: sc13d.htm, sc13g.htm, form_sc13g.htm,
# 13G.txt-style names. Exhibits (ex*, exhibit*) are excluded.
_TRADITIONAL_DOC = re.compile(r"(sc[\s_-]*13[\s_-]*[dg]|13[\s_-]*[dg])", re.IGNORECASE)
_EXHIBIT = re.compile(r"^(ex[\s_-]*\d*|exhibit)", re.IGNORECASE)


def pick_primary_doc(names: list[str]) -> str | None:
    """Pick the primary Schedule-13 document filename from an index listing.

    Priority (live-verified 2026-08-23): (1) ``primary_doc.xml`` — the modern
    structured Schedule-13 submission, whose cover page carries
    ``percentOfClass`` / ``classPercent`` directly; (2) a traditional
    ``sc13d/sc13g``-named ``.htm/.html/.txt`` that is not an exhibit; (3) any
    non-index, non-exhibit ``.htm/.html`` document. Pure function.
    """
    clean = [n for n in names if n and not _INDEX_PAGE.search(n)]
    if "primary_doc.xml" in clean:
        return "primary_doc.xml"
    trad = [
        n
        for n in clean
        if n.lower().endswith((".htm", ".html", ".txt"))
        and _TRADITIONAL_DOC.search(n)
        and not _EXHIBIT.search(n)
    ]
    if trad:
        return sorted(trad)[0]
    other = [
        n
        for n in clean
        if n.lower().endswith((".htm", ".html")) and not _EXHIBIT.search(n)
    ]
    return sorted(other)[0] if other else None


# --- percent extraction (pure regex over text; hermetic-testable) -------------

# Structured cover-page tags: 13D-style <percentOfClass>25.9</percentOfClass>,
# 13G-style <classPercent>13.0%</classPercent> (optional % and stray spaces).
_XML_PCT_NOW = re.compile(
    r"<(?:percentOfClass|classPercent)>\s*([\d.]+)\s*%?\s*<"
)
# HTML cover label: "Percent of class: 5.5%",
# "PERCENT OF CLASS REPRESENTED BY AMOUNT IN ROW (11) 5.5%" (the gap between
# the label and the value is non-greedy so it can never swallow the digits).
_LABEL_PCT_NOW = re.compile(
    r"percent(?:age)?\s+of\s+class(?:\s+represented[^:\n]{0,60}?)?\s*[:\-]?\s*"
    r"([\d.]+)\s*%",
    re.IGNORECASE,
)
# Narrative: "4.99% of the outstanding shares of Class A Common Stock",
# "5.2% of the class of securities", "represents approximately 6.1% of the
# outstanding common stock".
_NARR_PCT_NOW = re.compile(
    r"([\d.]+)\s*%\s*(?:of|in)\s+(?:the\s+|approximately\s+|such\s+|approximately the\s+)?"
    r"[\w\s,]{0,60}?(?:class|common stock|shares outstanding|outstanding shares|"
    r"outstanding common|common equity)",
    re.IGNORECASE,
)
# Previous-value narrative (amendments): "previous 5.2%",
# "previously reported 5.2%", "previously owned 5.2%",
# "increased/decreased ... from 5.2% to 6.1%", "down from 5.2%".
_PREV_LABEL = re.compile(
    r"previous(?:ly)?(?:\s+(?:reported|owned|held|filed))?[^.\n%]{0,40}?"
    r"([\d.]+)\s*%",
    re.IGNORECASE,
)
_PREV_FROM_TO = re.compile(
    r"(?:from|of)\s+([\d.]+)\s*%\s+(?:to|down to|up to)\s+[\d.]+\s*%",
    re.IGNORECASE,
)
_PREV_DIRECTIONAL = re.compile(
    r"(?:increas|decreas|reduc|amend|down|up)[\w\s,()]{0,80}?from\s+([\d.]+)\s*%",
    re.IGNORECASE,
)


def strip_markup(text: str) -> str:
    """Reduce HTML/XML to searchable text: drop tags/scripts/styles, unescape.

    Keeps percent-bearing sentences intact (cover-page tables become adjacent
    label+value text). Pure function.
    """
    import html

    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", text)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = html.unescape(t)
    return re.sub(r"[ \t]+", " ", t)


def _clean_pct(raw: str) -> float | None:
    try:
        v = float(raw)
    except ValueError:
        return None
    return v if 0.0 <= v <= 100.0 else None


def extract_pct_now(doc_text: str) -> float | None:
    """Percent of class as of THIS filing, or an honest None.

    Priority: structured XML tag (first reporting person's cover page — group
    filings repeat one cover per reporter), then the cover-page label, then the
    class/outstanding-shares narrative. Values outside [0, 100] are rejected.
    """
    m = _XML_PCT_NOW.search(doc_text)
    if m:
        v = _clean_pct(m.group(1))
        if v is not None:
            return v
    text = strip_markup(doc_text)
    for pat in (_LABEL_PCT_NOW, _NARR_PCT_NOW):
        m = pat.search(text)
        if m:
            v = _clean_pct(m.group(1))
            if v is not None:
                return v
    return None


def extract_pct_prev(doc_text: str, *, is_amendment: bool) -> float | None:
    """Previously-reported percent, amendments only, or an honest None.

    Original (non-/A) filings never carry a prev — the caller gates on
    ``is_amendment`` AND this function refuses to run without it, so the
    export contract ("prev only in amendments") holds at every layer.
    """
    if not is_amendment:
        return None
    text = strip_markup(doc_text)
    for pat in (_PREV_LABEL, _PREV_FROM_TO, _PREV_DIRECTIONAL):
        m = pat.search(text)
        if m:
            v = _clean_pct(m.group(1))
            if v is not None:
                return v
    return None


# --- bounded network fetch (idempotent per accession) -------------------------

_CACHE_NAME = "stakes_pct_parsed.json"


def _cache_path(cache_dir: Path | None = None) -> Path:
    d = cache_dir or settings.data_dir / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d / _CACHE_NAME


def load_pct_cache(cache_dir: Path | None = None) -> dict[str, dict]:
    """Load the per-accession parse cache; empty dict on absence/corruption."""
    import json

    try:
        loaded = json.loads(_cache_path(cache_dir).read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def save_pct_cache(cache: dict[str, dict], cache_dir: Path | None = None) -> None:
    import json

    _cache_path(cache_dir).write_text(json.dumps(cache, indent=1, sort_keys=True))


def _acc_nodash(accession: str) -> str:
    return accession.replace("-", "")


def parse_filing_pct(
    cik: int, accession: str, *, is_amendment: bool, cache_dir: Path | None = None
) -> dict:
    """Fetch + parse one filing's percent fields (≤2 requests, polite).

    Returns ``{"pct_now": float|None, "pct_prev": float|None, "ok": bool,
    "doc": str|None, "error": str|None}``. ``ok=True`` means the filing was
    reached and parsed (nulls are honest extraction misses — terminal, cached);
    ``ok=False`` is a fetch failure (NOT terminal — retried on the next run).
    """
    base = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{_acc_nodash(accession)}"
    try:
        r = _policy_get(
            f"{base}/index.json",
            total_attempts=2,
            backoff_base=4,
            headers={"User-Agent": _UA},
            timeout=60,
        )
        items = r.json().get("directory", {}).get("item", [])
        names = [str(it.get("name", "")) for it in items]
        doc = pick_primary_doc(names)
        if doc is None:
            return {
                "pct_now": None, "pct_prev": None, "ok": True,
                "doc": None, "error": "no_primary_doc",
            }
        r2 = _policy_get(
            f"{base}/{doc}",
            total_attempts=2,
            backoff_base=4,
            headers={"User-Agent": _UA},
            timeout=60,
        )
        text = r2.text
        return {
            "pct_now": extract_pct_now(text),
            "pct_prev": extract_pct_prev(text, is_amendment=is_amendment),
            "ok": True,
            "doc": doc,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001 — per-row resilience, honestly counted
        return {
            "pct_now": None, "pct_prev": None, "ok": False,
            "doc": None, "error": f"{type(exc).__name__}: {exc}"[:200],
        }


def stamp_row(row: dict) -> dict:
    out = dict(row)
    out["parsed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return out
