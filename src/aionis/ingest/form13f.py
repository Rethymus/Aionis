"""Point-in-time SEC 13F-HR institutional holdings (star-manager subset).

SEC Form 13F-HR is the QUARTERLY holdings report that institutional investment
managers exercising discretion over ≥ US$100M in Section 13(f) securities MUST
file within 45 days of quarter-end. It is the only legally mandated public
window into what large funds hold (name / title class / CUSIP / value / shares
/ option type per position).

Data chain (all SEC EDGAR, public domain 17 U.S.C. §105):
  1. ``https://data.sec.gov/submissions/CIK{cik:010d}.json`` — the manager's
     filing history; we filter ``form in {13F-HR, 13F-HR/A}`` and keep
     ``(accession, filing_date, report_date, form)``. ``report_date`` is the
     quarter-end the holdings are AS OF; ``filing_date`` is the PIT anchor.
  2. ``https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/index.json`` —
     the filing directory; the information table is a standalone XML whose name
     varies by filer (``infotable.xml``, ``Form13FInfoTable.xml``, or an
     arbitrary ``56757.xml``) and is NEVER ``primary_doc.xml`` (that is the
     cover page).
  3. The information table XML itself (namespace
     ``http://www.sec.gov/edgar/document/thirteenf/informationtable``): one
     ``infoTable`` per (issuer, class, option-type) line with ``value`` in
     WHOLE DOLLARS — the "expressed in thousands" note applies only to the
     legacy HTML rendering, NOT the 2014+ EDGAR XML schema (verified
     2026-08-20 on Berkshire's filing: 175,622,680 / 692,000 sh = $253.79 =
     AAPL's June-2026 price; a thousands reading would imply $253,790/sh).

DISPLAY LANE ONLY — this module feeds the web terminal's institutions panel.
It is NOT part of any research pipeline (no features/, no eval/, no OOS path).

Politeness: every network call goes through ``_policy_get`` (≥2s host spacing,
bounded retries) — same contract as form4/stakes_13d. Disk caches under
``data/cache/`` are idempotent: a cached file is never re-fetched.

Hermetic testability: the parsers (``parse_infotable_xml``,
``pick_infotable_doc``, ``compute_changes``) are pure functions on strings /
dicts / DataFrames; the fetchers are thin network shells around them.
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import requests
import structlog

from aionis.config import settings
from aionis.ingest.http_policy import HTTPStatusError
from aionis.ingest.universe import _policy_get

log = structlog.get_logger()

_UA = "Aionis research form13f contact@example.com"
_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
_ARCHIVE_BASE = "https://www.sec.gov/Archives/edgar/data"

# Information-table XML namespace (SEC EDGAR 13F schema). Filings are
# namespaced in practice, but the parser tolerates a no-namespace variant too.
_INFOTABLE_NS = {"n": "http://www.sec.gov/edgar/document/thirteenf/informationtable"}

_HOLDING_COLUMNS = [
    "cik", "manager_name", "quarter", "filing_date", "accession", "form",
    "issuer", "title_class", "cusip", "value_usd", "shares", "option_type",
]

# Change directions for the quarter-over-quarter frame diff (display enum;
# mirrored in web/src/data/aionis/index.ts Form13fChange.direction).
_DIRECTIONS = ("new", "increased", "reduced", "exited")


@dataclass(frozen=True)
class Form13fHolding:
    """One ``infoTable`` line from a 13F-HR information table."""

    issuer: str
    title_class: str
    cusip: str
    value_usd: float  # whole USD as filed (EDGAR 2014+ XML is already dollars)
    shares: float
    option_type: str  # "" plain shares / PRN principal, "PUT", "CALL"


def _cache_dir(cache_dir: Path | None = None) -> Path:
    d = cache_dir or settings.data_dir / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _num(text: str | None) -> float | None:
    """Best-effort numeric parse for value/shares fields (may be empty)."""
    if text is None or not str(text).strip():
        return None
    try:
        return float(str(text).strip().replace(",", ""))
    except ValueError:
        return None


# --- pure parsers (hermetic: string/dict in, structures out) -----------------


def _find(parent: ET.Element, path_ns: str, path_plain: str) -> ET.Element | None:
    """Find a child via the namespaced path first, then the unqualified one."""
    elem = parent.find(path_ns, _INFOTABLE_NS)
    if elem is None:
        elem = parent.find(path_plain)
    return elem


def parse_infotable_xml(xml_text: str) -> list[Form13fHolding]:
    """Parse a 13F-HR information table XML into holdings.

    ``value`` is whole USD as filed (EDGAR 2014+ XML — see module docstring
    for the thousands-convention debunk). ``sshPrnamtType`` distinguishes share
    counts (SH) from principal amounts (PRN); ``putCall`` (when present) marks
    option lines. Rows missing issuer/cusip or with non-positive value are
    skipped with a warning (one bad line never aborts the table).
    """
    if not xml_text or not xml_text.strip():
        log.warning("form13f_empty_xml")
        return []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        log.warning("form13f_xml_parse_error", error=str(exc))
        return []

    holdings: list[Form13fHolding] = []
    for node in root.findall(".//n:infoTable", _INFOTABLE_NS) or root.findall(
        ".//infoTable"
    ):
        issuer_el = _find(node, "n:nameOfIssuer", "nameOfIssuer")
        title_el = _find(node, "n:titleOfClass", "titleOfClass")
        cusip_el = _find(node, "n:cusip", "cusip")
        value_el = _find(node, "n:value", "value")
        shares_el = _find(node, "n:shrsOrPrnAmt/n:sshPrnamt", "shrsOrPrnAmt/sshPrnamt")
        putcall_el = _find(node, "n:putCall", "putCall")

        issuer = (issuer_el.text or "").strip() if issuer_el is not None else ""
        cusip = (cusip_el.text or "").strip() if cusip_el is not None else ""
        value_k = _num(value_el.text if value_el is not None else None)
        shares = _num(shares_el.text if shares_el is not None else None)
        if not issuer or not cusip or value_k is None or value_k <= 0:
            continue
        holdings.append(
            Form13fHolding(
                issuer=issuer,
                title_class=(title_el.text or "").strip() if title_el is not None else "",
                cusip=cusip,
                value_usd=value_k,
                shares=float(shares) if shares is not None else 0.0,
                option_type=(putcall_el.text or "").strip().upper()
                if putcall_el is not None
                else "",
            )
        )
    log.info("form13f_parsed", count=len(holdings))
    return holdings


def holdings_to_dataframe(
    holdings: list[Form13fHolding],
    *,
    cik: int,
    manager_name: str,
    quarter: str,
    filing_date: str,
    accession: str,
    form: str,
) -> pd.DataFrame:
    """Attach filing metadata to parsed holdings -> one tidy quarter frame."""
    rows = [
        {
            "cik": int(cik),
            "manager_name": manager_name,
            "quarter": str(quarter)[:10],
            "filing_date": str(filing_date)[:10],
            "accession": accession,
            "form": form,
            "issuer": h.issuer,
            "title_class": h.title_class,
            "cusip": h.cusip,
            "value_usd": h.value_usd,
            "shares": h.shares,
            "option_type": h.option_type,
        }
        for h in holdings
    ]
    return pd.DataFrame(rows, columns=_HOLDING_COLUMNS)


def _extract_13f_rows(submissions_json: dict, cik: int) -> list[dict]:
    """Pull 13F-HR(/A) rows out of a submissions JSON (pure; hermetic).

    Uses ``filings.recent`` only — every manager in our bounded star subset has
    ≪1000 total filings, so ``recent`` always covers the full 13F history
    (oldest managers here have ~107 13F filings). Rows keep the LATEST filing
    per ``report_date`` (an amendment supersedes the original — never silently
    merges; both remain in EDGAR).
    """
    recent = (submissions_json.get("filings") or {}).get("recent") or {}
    rows: list[dict] = []
    forms = recent.get("form") or []
    for form, accession, filed, report, primary_doc in zip(
        forms,
        recent.get("accessionNumber") or [""] * len(forms),
        recent.get("filingDate") or [""] * len(forms),
        recent.get("reportDate") or [""] * len(forms),
        recent.get("primaryDocument") or [""] * len(forms),
        strict=False,
    ):
        if str(form) not in ("13F-HR", "13F-HR/A"):
            continue
        rows.append(
            {
                "cik": int(cik),
                "accession": str(accession),
                "filing_date": str(filed),
                "report_date": str(report),
                "form": str(form),
                "primary_doc": str(primary_doc),
            }
        )
    return rows


def pick_infotable_doc(index_json: dict) -> str | None:
    """Pick the information-table XML filename from a filing ``index.json``.

    The infotable is a standalone XML whose name varies by filer
    (``infotable.xml`` / ``Form13FInfoTable.xml`` / arbitrary ``NNNNN.xml``);
    ``primary_doc.xml`` is the COVER PAGE and must never be picked. Rule:
    non-primary ``.xml`` files → prefer names containing infotable/form13f →
    else the largest file (infotables dwarf cover pages). Returns ``None``
    when the filing has no machine-readable XML variant (rare; HTML-only).
    """
    directory = index_json.get("directory") if isinstance(index_json, dict) else None
    raw = directory.get("item", []) if isinstance(directory, dict) else []
    items = raw if isinstance(raw, list) else [raw]
    xmls = {
        str(it.get("name", "")): int(it.get("size") or 0)
        for it in items
        if isinstance(it, dict)
        and str(it.get("name", "")).lower().endswith(".xml")
        and "/" not in str(it.get("name", ""))
    }
    non_primary = {n: s for n, s in xmls.items() if n.lower() != "primary_doc.xml"}
    if not non_primary:
        return None
    named = {
        n: s
        for n, s in non_primary.items()
        if "infotable" in n.lower() or "form13f" in n.lower()
    }
    pool = named or non_primary
    return max(pool, key=lambda n: (pool[n], n))  # size desc, name tiebreak


def compute_changes(prev: pd.DataFrame, cur: pd.DataFrame) -> list[dict]:
    """Quarter-over-quarter frame diff -> display change rows (pure).

    Positions are keyed by ``(cusip, option_type)`` — the same CUSIP is the
    same security (share-class noise in ``titleOfClass`` strings across
    quarters must NOT read as an exit+rebuild pair), and a manager may report
    shares AND calls on one CUSIP as separate lines. Lines are summed within
    each quarter (filers split one issuer across several tranches).
    Directions: ``new`` (absent → present), ``exited`` (present → absent),
    ``increased``/``reduced`` (shares up/down). ``delta_pct`` is the SHARE
    change in percent (+25.3 = +25.3% shares); ``None`` for new/exited.
    ``delta_value`` is the whole-USD VALUE change (current − prior quarter,
    both sides kept by the merge): for ``new``/``exited`` it equals the full
    position value added/removed; for ``increased``/``reduced`` it is a plain
    difference whose sign may OPPOSE the share move (price drift between
    quarters) — display layers must not assume sign consistency with
    ``delta_pct``. Rows are sorted by position size involved (max(cur, prev)
    value) descending — the "top changes" surface.
    """
    key = ["cusip", "option_type"]

    def _agg(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame(columns=key + ["issuer", "title_class", "value_usd", "shares"])
        return df.groupby(key, as_index=False).agg(
            issuer=("issuer", "first"),
            title_class=("title_class", "first"),
            value_usd=("value_usd", "sum"),
            shares=("shares", "sum"),
        )

    p, c = _agg(prev), _agg(cur)
    merged = p.merge(c, on=key, how="outer", suffixes=("_prev", "_cur"))
    out: list[dict] = []
    for _, r in merged.iterrows():
        issuer = str(r["issuer_cur"] if pd.notna(r.get("issuer_cur")) else r["issuer_prev"])
        raw_title = (
            r["title_class_cur"]
            if pd.notna(r.get("title_class_cur"))
            else r.get("title_class_prev", "")
        )
        title = str(raw_title)
        v_prev = float(r["value_usd_prev"]) if pd.notna(r.get("value_usd_prev")) else 0.0
        v_cur = float(r["value_usd_cur"]) if pd.notna(r.get("value_usd_cur")) else 0.0
        s_prev = float(r["shares_prev"]) if pd.notna(r.get("shares_prev")) else 0.0
        s_cur = float(r["shares_cur"]) if pd.notna(r.get("shares_cur")) else 0.0
        if v_cur <= 0:
            direction, delta_pct = "exited", None
        elif v_prev <= 0:
            direction, delta_pct = "new", None
        elif s_cur > s_prev:
            direction, delta_pct = "increased", _pct(s_prev, s_cur)
        elif s_cur < s_prev:
            direction, delta_pct = "reduced", _pct(s_prev, s_cur)
        else:
            direction, delta_pct = None, 0.0  # share count unchanged
        if direction is None:
            continue
        out.append(
            {
                "issuer": issuer,
                "cusip": str(r["cusip"]),
                "title": title,
                "option": str(r["option_type"]),
                "direction": direction,
                "delta_pct": delta_pct,
                # Whole-USD value delta (cur − prev; both sides kept by the
                # outer merge): +full position for new, −full for exited.
                "delta_value": round(v_cur - v_prev, 0),
                "value_usd": v_cur if v_cur > 0 else v_prev,
                "_sort": max(v_cur, v_prev),
            }
        )
    out.sort(key=lambda d: (d["_sort"], d["issuer"]), reverse=True)
    for d in out:
        del d["_sort"]
    return out


def _pct(prev_shares: float, cur_shares: float) -> float:
    """Share-count change in percent; 0.0 when the base is zero (PRN lines)."""
    if prev_shares <= 0:
        return 0.0
    return round((cur_shares - prev_shares) / prev_shares * 100.0, 2)


# --- issuer-name → ticker exact linking (display label only) -----------------
#
# EDGAR 13F information tables carry CUSIPs, never tickers. The institutions
# panel still wants a link into the terminal's stock page, so issuers are
# linked by EXACT match of normalized names against a (name, ticker) source
# (the SEC ``company_tickers.json`` snapshot cached by
# ``aionis.ingest.cik_resolver`` plus the terminal's own US stock universe).
# EXACT means exact: normalization only collapses rendering noise (case,
# punctuation, apostrophes, EDGAR ``/DE/``-style location qualifiers, trailing
# legal suffixes). As-filed ABBREVIATIONS ("BANK OF AMER CORP", "APPLIED
# MATLS INC", 20-char-legacy truncations) do NOT match and stay null — no
# fuzzy/prefix guessing, ever. Display-only label, NOT a research input.

#: Trailing tokens dropped from BOTH sides of a name comparison. Legal-form +
#: EDGAR re-incorporation markers only — never words that disambiguate issuers
#: beyond their legal form (e.g. "INTERNATIONAL" is a legal-form word here in
#: the same spirit as "COMPANY"; both sides strip it identically).
_ISSUER_NAME_SUFFIXES = frozenset({
    "INC", "INCORPORATED", "CORP", "CORPORATION", "LTD", "LIMITED", "LLC", "LP",
    "LPA", "PLC", "CO", "COMPANY", "SA", "AG", "NV", "SE", "SPA", "TRUST",
    "HOLDINGS", "HOLDING", "HLDGS", "GROUP", "PARTNERS", "PARTNERSHIP", "FUND",
    "INTERNATIONAL", "DEL",
})


def normalize_issuer_name(name: str) -> str:
    """Normalize an issuer/company name for EXACT-match joining (pure).

    Case-fold; delete apostrophes (``MOODY'S`` → ``MOODYS`` — 13F filers omit
    them); strip EDGAR location qualifiers (``BANK OF AMERICA CORP /DE/``,
    ``VERISIGN INC/CA``); collapse remaining non-alphanumerics to spaces; drop
    a leading ``THE``; iteratively drop trailing legal-form suffixes and the
    single-letter fragments of foreign legal forms (``Ferrovial N.V.`` →
    ``FERROVIAL``). A name that normalizes to nothing stays ``""`` (never
    linked).
    """
    s = str(name).upper().replace("'", "")
    s = re.sub(r"/[A-Z]{2}/?\s*$", " ", s)  # trailing /DE/ /CA /CN
    s = re.sub(r"\s*/[A-Z]{2}/", " ", s)  # mid-string /DE/
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    tokens = [t for t in s.split() if t]
    while tokens and tokens[0] == "THE":
        tokens = tokens[1:]
    while len(tokens) > 1 and (tokens[-1] in _ISSUER_NAME_SUFFIXES or len(tokens[-1]) == 1):
        tokens = tokens[:-1]
    return " ".join(tokens)


def build_issuer_ticker_map(
    entities: list[tuple[str, int | str, str]],
) -> dict[str, str]:
    """Build normalized-name → ticker from (title, entity_id, ticker) triples.

    ``entities`` is consumed in SOURCE order (e.g. SEC ``company_tickers.json``
    order = market-cap descending, so a company's main listing precedes its OTC
    preferreds). Conflict policy, deliberately conservative:

    - a normalized name owned by exactly ONE ``entity_id`` (CIK) links to that
      entity's first hyphen-free ticker in source order (fallback: first);
    - a name claimed by 2+ distinct entity ids (e.g. bare "iShares" trust
      shells) is AMBIGUOUS → dropped entirely (null on lookup, no guessing).

    Pure function on its argument — hermetic; the caller owns sourcing.
    """
    key_entities: dict[str, set] = {}
    key_tickers: dict[str, list[str]] = {}
    for title, entity_id, ticker in entities:
        key = normalize_issuer_name(title)
        if not key:
            continue
        key_entities.setdefault(key, set()).add(entity_id)
        key_tickers.setdefault(key, []).append(str(ticker))
    out: dict[str, str] = {}
    for key, owners in key_entities.items():
        if len(owners) != 1:
            continue
        tickers = key_tickers[key]
        plain = [t for t in tickers if "-" not in t]
        out[key] = (plain or tickers)[0]
    return out


# --- thin network shells (idempotent disk cache + _policy_get) ---------------


def _get_polite(url: str) -> requests.Response:
    """One polite GET (≥2s host spacing, linear backoff, permanent-4xx fast)."""
    try:
        return _policy_get(
            url,
            total_attempts=4,
            backoff_base=4,
            backoff_mode="linear",
            headers={"User-Agent": _UA},
            timeout=60,
        )
    except HTTPStatusError as exc:
        if 400 <= exc.status_code < 500 and exc.status_code != 429:
            raise RuntimeError(f"{exc.status_code} permanent error for {url}") from exc
        raise RuntimeError(f"fetch failed for {url}: {exc}") from exc


def fetch_13f_filings(cik: int, cache_dir: Path | None = None) -> pd.DataFrame:
    """13F-HR(/A) filing list for ``cik`` from the EFTS submissions JSON.

    Idempotent: the extracted 13F rows are cached under
    ``data/cache/form13f_filings_{cik}.json`` — a warm rerun makes no HTTP call.
    Returns ``[cik, accession, filing_date, report_date, form, primary_doc]``
    sorted by ``filing_date`` ascending.
    """
    fp = _cache_dir(cache_dir) / f"form13f_filings_{int(cik):010d}.json"
    if fp.exists():
        rows = json.loads(fp.read_text())
    else:
        data = _get_polite(_SUBMISSIONS_URL.format(cik=int(cik))).json()
        rows = _extract_13f_rows(data, cik)
        fp.write_text(json.dumps(rows))
    df = pd.DataFrame(
        rows,
        columns=["cik", "accession", "filing_date", "report_date", "form", "primary_doc"],
    )
    if df.empty:
        return df
    return df.sort_values("filing_date").reset_index(drop=True)


def _accession_no_dash(accession: str) -> str:
    return accession.replace("-", "")


def fetch_infotable_xml(
    cik: int, accession: str, cache_dir: Path | None = None
) -> str:
    """Fetch (and cache) the information-table XML for one 13F filing.

    Two polite calls on cold cache: the filing ``index.json`` (cached), then
    the picked XML document (cached). Returns ``""`` when the filing has no
    XML infotable variant (HTML-only) — the caller skips that filing honestly.
    """
    nd = _accession_no_dash(accession)
    xml_fp = _cache_dir(cache_dir) / f"form13f_xml_{int(cik):010d}_{nd}.xml"
    if xml_fp.exists():
        return xml_fp.read_text()

    idx_fp = _cache_dir(cache_dir) / f"form13f_index_{int(cik):010d}_{nd}.json"
    if idx_fp.exists():
        idx = json.loads(idx_fp.read_text())
    else:
        idx = _get_polite(f"{_ARCHIVE_BASE}/{int(cik)}/{nd}/index.json").json()
        idx_fp.write_text(json.dumps(idx))

    doc = pick_infotable_doc(idx)
    if not doc:
        log.warning("form13f_no_xml_infotable", cik=cik, accession=accession)
        return ""
    text = _get_polite(f"{_ARCHIVE_BASE}/{int(cik)}/{nd}/{doc}").text
    xml_fp.write_text(text)
    return text


def fetch_manager_holdings(
    cik: int,
    manager_name: str,
    *,
    quarters: int = 2,
    cache_dir: Path | None = None,
) -> pd.DataFrame:
    """Holdings frames for the ``quarters`` most recent DISTINCT report dates.

    For each report quarter the LATEST filing wins (a 13F-HR/A amendment
    supersedes the original — EDGAR keeps both; we display the amended truth).
    Each filing's infotable is fetched + parsed politely and idempotently.
    Failures per filing are logged and skipped (one bad filing never aborts
    the manager).
    """
    filings = fetch_13f_filings(cik, cache_dir=cache_dir)
    if filings.empty:
        log.warning("form13f_no_filings", cik=cik)
        return pd.DataFrame(columns=_HOLDING_COLUMNS)
    latest_per_quarter = filings.sort_values("filing_date").groupby("report_date").tail(1)
    recent = latest_per_quarter.sort_values("report_date", ascending=False).head(quarters)

    frames: list[pd.DataFrame] = []
    for _, f in recent.iterrows():
        try:
            xml_text = fetch_infotable_xml(cik, str(f["accession"]), cache_dir=cache_dir)
        except RuntimeError as exc:
            log.warning("form13f_fetch_failed", cik=cik, accession=f["accession"], error=str(exc))
            continue
        holdings = parse_infotable_xml(xml_text)
        if not holdings:
            log.warning("form13f_empty_holdings", cik=cik, quarter=f["report_date"])
            continue
        frames.append(
            holdings_to_dataframe(
                holdings,
                cik=cik,
                manager_name=manager_name,
                quarter=str(f["report_date"]),
                filing_date=str(f["filing_date"]),
                accession=str(f["accession"]),
                form=str(f["form"]),
            )
        )
    if not frames:
        return pd.DataFrame(columns=_HOLDING_COLUMNS)
    return pd.concat(frames, ignore_index=True)
