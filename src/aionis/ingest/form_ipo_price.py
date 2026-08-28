"""Bounded cover-page offer-price parsing for 424B4 filings (display-only).

The bounded second stage the /ipo panel deferred in v1: for the NEWEST
priced (424B4) filings only (≤ ``TARGET_CAP`` = 80 by filed-date), fetch the
filing's EDGAR ``index.json`` (1 request), pick the 424B4 primary document
(1 request), and regex-extract the cover-page offer price. Graded confidence,
mirroring the :mod:`aionis.ingest.stakes_pct` precedent:

* ``exact`` — a single FINAL dollar figure in an offering-price anchor's
  line ("Initial public offering price   $   11.00   per share" /
  "Price to public(1) $16.00"). Exported as the row's ``offer_price``.
* ``low``   — the anchor matched but the amount sits in draft/range language
  ("proposed ... price range between $14.00 and $16.00"). Value is NEVER
  exported (honest blank) — counted and disclosed only.
* ``none``  — no offering-price anchor with a parseable single amount.

Hypothetical/scenario sentences ("if the initial public offering price were
$1 higher") are skipped entirely — they are neither exact nor low-confidence
evidence; scanning continues at later anchors.

Everything not found is an HONEST null — never guessed, never defaulted,
never widened to chase coverage. Failures are counted, not papered over.

Politeness: every request rides ``_policy_get`` (≥2s host spacing + bounded
transient-only retry), so ~2 requests/row × 2s+ pacing; total walk is budget-
capped (task budget ≤170 requests including the EFTS window refresh). Idempotent
per-accession disk cache (``data/cache/form_ipo_price_parsed.json``): rows
already parsed (``ok``) are never re-fetched — a rerun makes ZERO new requests;
failed rows (``ok: false``) retry on the next run.

SEC EDGAR public domain (17 U.S.C. §105) — G1✓; the as-filed document is
immutable (accession-keyed) — G3✓; display-only exploratory — G5✓;
extraction-boundary + coverage + request-budget disclosure lives in the panel
methodology and ``docs/data-intake-edgar-ipo.md`` — G6/G7✓.
"""
from __future__ import annotations

import re
from pathlib import Path

from aionis.config import settings
from aionis.ingest.stakes_pct import strip_markup
from aionis.ingest.universe import _policy_get

_UA = "Aionis research form-ipo-price contact@example.com"

# --- primary-document selection (index.json → filename) -----------------------

# EDGAR-generated index/header pages are never the form itself.
_INDEX_PAGE = re.compile(r"-index(-headers)?\.html?$", re.IGNORECASE)
_EXHIBIT = re.compile(r"^(ex[\s_-]*\d*|exhibit)", re.IGNORECASE)
# The statutory final prospectus itself (d123456d424b4.htm, tf…-1_424b4.htm).
_DOC_424B4 = re.compile(r"424b4", re.IGNORECASE)


def pick_primary_doc(names: list[str]) -> str | None:
    """Pick the 424B4 prospectus filename from an index.json listing.

    Priority: (1) any non-index, non-exhibit htm/html/txt whose name carries
    ``424b4``; (2) any other non-index non-exhibit ``.htm/.html`` document
    (some filers name the prospectus freely). Pure function."""
    clean = [n for n in names if n and not _INDEX_PAGE.search(n)]
    named = [
        n for n in clean
        if n.lower().endswith((".htm", ".html", ".txt"))
        and _DOC_424B4.search(n)
        and not _EXHIBIT.search(n)
    ]
    if named:
        return sorted(named)[0]
    other = [
        n for n in clean
        if n.lower().endswith((".htm", ".html")) and not _EXHIBIT.search(n)
    ]
    return sorted(other)[0] if other else None


# --- graded cover-price extraction (pure regex over text) ----------------------

CONF_EXACT = "exact"
CONF_LOW = "low"
CONF_NONE = "none"

# Offering-price anchors, in the order a reader sees them on the cover:
#   "Initial public offering price", "Price to public(1)", "IPO price",
# plus the bare phrase "initial public offering" (the full-form sentence
# inside the prospectus restates the same number, e.g. "...an initial public
# offering price of $11.00 per share").
_OFFER_ANCHOR = re.compile(
    r"initial\s+public\s+offering\s+(?:price|of\b)|price\s+to\s+public(?:\(\d+\))?"
    r"|ipo\s+price|offering\s+price",
    re.IGNORECASE,
)
# First currency amount after the anchor ("$11.00", "$ 11.00", "$11,000,000").
_AMT = re.compile(r"\$\s?([0-9][0-9,]*(?:\.[0-9]+)?)")
# Draft/range language in the gap between anchor and amount (a 424B4 body can
# still echo pre-pricing wording such as "proposed ... price range between");
# such amounts are NOT the final printed price → low tier, never exported.
_DRAFT_MARK = re.compile(
    r"\b(?:range|between|estimated?|est\.|anticipat\w*|expected?|proposed|"
    r"preliminary|assumed?)\b",
    re.IGNORECASE,
)
# Hypothetical/scenario framing ("If the initial public offering price had
# been $1 higher ...") — not evidence at all; checked in the lead-in BEFORE
# the anchor ("If ..." / "hypothetical") so counterfactual arithmetic is
# skipped entirely rather than mistaken for the printed price.
_HYPOTHETIC_PRE = re.compile(
    r"\b(?:if|hypothetical|scenario|illustrative|suppose)[^.\n]{0,60}$",
    re.IGNORECASE,
)
# Conditional-subjunctive wording INSIDE the gap ("... offering price were
# $1 higher") — same counterfactual exclusion as the lead-in.
_HYPOTHETIC_GAP = re.compile(
    r"^\s*(?:were|would|could|should|had)[^a-z]", re.IGNORECASE
)
# A second leg right after the first amount ("$14.00 and $16.00",
# "$14.00 - $16.00") marks a range → low tier.
_RANGE_TAIL = re.compile(r"^\s*(?:and|or|to|[-–—])\s*\$?\s*[0-9]", re.IGNORECASE)

# Sanity envelope for an IPO share price (generous, NOT a market judgement):
# excludes table artefacts like "$0.0001 par value" fractions yet admits
# sub-$1 penny-priced offers and even four-digit shares if one ever appears.
_MIN_PRICE, _MAX_PRICE = 0.01, 100000.0


def _clean_price(raw: str) -> float | None:
    try:
        v = float(raw.replace(",", ""))
    except ValueError:
        return None
    return v if _MIN_PRICE <= v <= _MAX_PRICE else None


def extract_offer_price(doc_text: str) -> tuple[float | None, str]:
    """Cover-page offer price from one 424B4 document, or an honest None.

    Returns ``(price, confidence)`` where ``confidence`` is one of
    ``exact`` (price is returned), ``low`` (draft/range evidence — price
    ALWAYS None, never guessed) or ``none``. Anchors scan in document order
    so the earliest cover-table line wins before any later narrative.
    Pure function.
    """
    text = strip_markup(doc_text or "")
    low_seen = False
    for m in _OFFER_ANCHOR.finditer(text):
        lead = text[max(0, m.start() - 70): m.start()]
        if _HYPOTHETIC_PRE.search(lead):
            continue  # counterfactual framing — neither exact nor low evidence
        window = text[m.end(): m.end() + 80]
        amt = _AMT.search(window)
        if amt is None:
            continue
        gap = window[: amt.start()]
        if _HYPOTHETIC_GAP.match(gap):
            continue  # scenario arithmetic — neither exact nor low evidence
        if _DRAFT_MARK.search(gap):
            low_seen = True
            continue
        tail = window[amt.end(): amt.end() + 28]
        if _RANGE_TAIL.match(tail) or _DRAFT_MARK.search(tail[:12]):
            low_seen = True
            continue
        v = _clean_price(amt.group(1))
        if v is None:
            continue
        return v, CONF_EXACT
    if low_seen:
        return None, CONF_LOW
    return None, CONF_NONE


# --- bounded network fetch (idempotent per accession) --------------------------

_CACHE_NAME = "form_ipo_price_parsed.json"


def _cache_path(cache_dir: Path | None = None) -> Path:
    d = cache_dir or settings.data_dir / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d / _CACHE_NAME


def load_price_cache(cache_dir: Path | None = None) -> dict[str, dict]:
    """Load the per-accession parse cache; empty dict on absence/corruption."""
    import json

    try:
        loaded = json.loads(_cache_path(cache_dir).read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    meta = loaded.get("_meta") if isinstance(loaded, dict) else None
    rows = loaded.get("rows") if isinstance(meta, dict) else loaded
    return rows if isinstance(rows, dict) else {}


def load_cache_meta(cache_dir: Path | None = None) -> dict:
    """The cache's ``_meta`` header (request ledger / window disclosure);
    empty dict when absent or when the cache predates the header."""
    import json

    try:
        loaded = json.loads(_cache_path(cache_dir).read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    meta = loaded.get("_meta") if isinstance(loaded, dict) else None
    return meta if isinstance(meta, dict) else {}


def save_price_cache(cache: dict[str, dict], meta: dict | None = None,
                     cache_dir: Path | None = None) -> None:
    """Write the accession-keyed parse cache as ``{"_meta": …, "rows": …}``.

    ``cache`` must contain ONLY accession-keyed entries; the run ledger /
    window disclosure travel in the separate ``_meta`` header so accession
    keys stay pure (stakes_pct keeps entries flat; the header split here
    carries the honest request accounting)."""
    import json

    _cache_path(cache_dir).write_text(
        json.dumps({"_meta": meta or {}, "rows": cache}, indent=1, sort_keys=True)
    )


def prune_price_cache_to_target(
    cache: dict[str, dict], target_accessions: set[str]
) -> dict[str, dict]:
    """Restrict the parse cache to the current bounded-walk target window.

    The target window only ever ADVANCES at its newest edge (a newly priced
    424B4 enters as an older one slides out) and filed dates are immutable, so
    an entry that left the newest-≤cap priced window can never re-enter:
    keeping it would be dead weight that ``merge_offer_prices`` still serves to
    every visible row while the export layer's ``conf["exact"]`` counts only
    in-window entries — the drift that broke the
    ``conf["exact"] == offer_price_parsed`` panel contract. Pruning makes the
    cache structurally equal to "the current bounded-walk state", i.e. exactly
    the window the panel discloses (single source of truth: the cache IS the
    window).

    FAIL (``ok: false``) entries whose accession is still in target ARE window
    state (they retry on the next run) and are kept like any other. Zero
    information loss: slid-out accessions are dropped whole, never rewritten
    or re-graded, and they would never be reached again by any future walk.
    Returns a NEW dict; the input is not mutated (pure function).
    """
    return {
        acc: entry for acc, entry in cache.items() if acc in target_accessions
    }


def _acc_nodash(accession: str) -> str:
    return accession.replace("-", "")


def parse_filing_offer_price(
    cik: int, accession: str, *, cache_dir: Path | None = None
) -> dict:
    """Fetch + parse one filing's cover offer price (≤2 requests, polite).

    Returns ``{"offer_price": float|None, "confidence": "exact"|"low"|"none"|None,
    "ok": bool, "doc": str|None, "error": str|None}``. ``ok=True`` means the
    filing was reached and parsed (nulls are honest extraction misses —
    terminal, cached forever); ``ok=False`` is a fetch failure (NOT terminal —
    retried on the next run, per the stakes_pct idempotency contract).
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
                "offer_price": None, "confidence": CONF_NONE, "ok": True,
                "doc": None, "error": "no_primary_doc",
            }
        r2 = _policy_get(
            f"{base}/{doc}",
            total_attempts=2,
            backoff_base=4,
            headers={"User-Agent": _UA},
            timeout=60,
        )
        price, conf = extract_offer_price(r2.text)
        return {
            "offer_price": price, "confidence": conf, "ok": True,
            "doc": doc, "error": None,
        }
    except Exception as exc:  # noqa: BLE001 — per-row resilience, honestly counted
        return {
            "offer_price": None, "confidence": None, "ok": False,
            "doc": None, "error": f"{type(exc).__name__}: {exc}"[:200],
        }


def stamp_row(row: dict) -> dict:
    """Copy of ``row`` plus an ISO-UTC ``parsed_at`` stamp — the idempotency
    hint shape demanded by the panel contract test. Delegates to the
    :mod:`aionis.ingest.stakes_pct` precedent implementation."""
    from aionis.ingest.stakes_pct import stamp_row as _stamp

    return _stamp(row)


def merge_offer_prices(rows: list[dict], cache: dict[str, dict]) -> list[dict]:
    """Attach ``offer_price`` to export-row dicts keyed via their EDGAR index
    URL (``.../{cik}/{nodash}/{accession}-index.htm`` → dashed accession).

    Exact-tier values pass through a final validity gate ([``_MIN_PRICE``,
    ``_MAX_PRICE``], any other value → null — export-layer contract defense,
    same shape as the stakes_pct clip). Every layer re-enforces the guarantee:
    low/no-match/failed ⇒ null. Mutates + returns ``rows``."""
    acc_re = re.compile(r"\d{10}-\d{2}-\d{6}")
    for r in rows:
        url = str(r.get("doc_url") or "")
        tail = url.rstrip("/").rsplit("/", 1)[-1]
        tail = tail.removesuffix("-index.htm").removesuffix("-index.html")
        e = cache.get(tail) if acc_re.fullmatch(tail) else None
        price = None
        if e is not None and e.get("confidence") == CONF_EXACT:
            p = e.get("offer_price")
            if isinstance(p, (int, float)) and _MIN_PRICE <= float(p) <= _MAX_PRICE:
                price = float(p)
        r["offer_price"] = price
    return rows
