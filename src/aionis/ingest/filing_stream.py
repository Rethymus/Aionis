"""Unified whole-market filing stream v2 — DIRECT multi-form queries (display-only).

v1 derived ``/events``'s all-market feed by MERGING the terminal's own committed
per-form panels — coverage was bounded by each panel's visible cap and the 10-K /
10-Q families were absent entirely. v2 queries EDGAR **directly**, one root form
at a time, so the stream IS the source (no panel caps inherited):

  * EFTS root-form queries (whole market, no ``ciks=``): ``8-K`` / ``10-K`` /
    ``10-Q`` / ``S-1`` / ``4`` / ``D`` — each expands to its amendment family
    (``8-K/A``, ``10-K/A``, ``S-1/A``, ``4/A``, ``D/A`` …). ONE form parameter
    per query, NEVER a comma list — efts mis-parses root+amendment lists
    (verified for SC 13D in :mod:`aionis.ingest.stakes_13d_efts`; same engine).
  * ``SC 13D`` / ``SC 13G``: EFTS **froze on the whole Schedule 13 family after
    2024-12-17** (:mod:`aionis.ingest.stakes_13d_daily_index`; re-verified live
    2026-08-23 — a recent-window probe returns 0 hits, the probe is cached and
    re-run each window as the machine-verified zero). The two roots are still
    probed (one cached page each) so a healed index would be picked up, and the
    rows are recovered from the EDGAR **daily crawler index** — the current
    dissemination feed — via the shared per-day caches of the 13D/13G lanes.

CAP SAFETY (the Form D / 13F lesson): EFTS hard-caps a query at 10,000 hits and
pagination beyond the cap silently returns nothing, so every window is checked
against its DECLARED total and split at the midpoint when ``total >= 9,500``
(the same threshold/floor pattern as :mod:`aionis.ingest.form13f_dir`, floors
scaled to this module's 14-day windows). Form 4 — the busiest family, estimated
10-15k/14d in filing season — is split UNCONDITIONALLY into two ~7-day halves
(so its cache files are the split transcript), which costs the same page count
as one unsplit query and is season-proof. Measured 2026-08-23 (August lull):
4 = 6,196 over 14 days — under the cap; the unconditional halves landed ~3k
each and the machinery stays armed for earnings season.

ROWS are normalized to the v1 stream shape ``{form, who, ticker, filed_date,
doc_url}`` (plus ``accession`` for dedup): ``who`` = company name
(:func:`aionis.ingest.form_ipo._parse_company`) on company filings, the
REPORTING PERSON (first ``display_names`` entry — verified live: Form 4 lists
``"Papermaster Mark D (CIK …)"`` before the issuer) on Form 4, and
``"FILER → TARGET"`` on Schedule 13 (subject = the group member whose CIK
resolves a ticker offline, the :func:`scripts.export_terminal_data._sm_dedup_enrich`
heuristic; an unresolvable group keeps every member honestly, never a
placeholder). ``ticker`` = as-of-filing ticker parsed from ``display_names``
when present, else the offline SEC ``company_tickers`` snapshot — a CURRENT
snapshot, fine for a display label, never a research input (the established
13D-panel caveat). ``doc_url`` = the filing index page
(:func:`aionis.ingest.form_ipo._filing_index_url`) — zero extra requests.

EXCLUDED: ``DEF 14A`` (proxy season is TASK-V's dedicated panel lane) and
``13F-HR`` (quarterly manager filings, not company events — the /filers
registry carries them).

7-gate: SEC EDGAR public domain (17 U.S.C. §105) — G1✓; PIT via ``file_date``
/ dissemination date — G2✓; immutable (every /A amendment is a NEW accession,
never a silent overwrite) — G3✓; exploratory display-only — G5✓; polite ≥2s
spacing (process-wide HttpRequestPolicy + explicit 2.1s page sleeps) +
idempotent per-form caches — G7✓.
"""
from __future__ import annotations

import json
import time
from datetime import date as date_t
from pathlib import Path

import pandas as pd
import structlog

from aionis.ingest.form4_efts import _cache_dir, _get_json
from aionis.ingest.form_ipo import (
    _filing_index_url,
    _issuer_cik,
    _parse_company,
    parse_ticker,
)
from aionis.ingest.stakes_13d_daily_index import fetch_recent_13d_daily
from aionis.ingest.stakes_13g import fetch_recent_13g_daily

log = structlog.get_logger()

_EFTS_URL = "https://efts.sec.gov/LATEST/search-index"
_PAGE_SIZE = 100  # efts default + max per request; paginate via from=

# One root form per EFTS query (NEVER a comma list — efts mis-parses
# root+amendment families; verified for SC 13D, same engine for all).
ROOT_EFTS_FORMS = ("8-K", "10-K", "10-Q", "S-1", "4", "D")
# EFTS froze on Schedule 13 after 2024-12-17 — probed each run (cached,
# machine-verified zero), rows recovered from the daily crawler index.
SCHEDULE13_ROOT_FORMS = ("SC 13D", "SC 13G")

# Cap safety (form13f_dir pattern): split a window whose DECLARED total is
# this close to EFTS's 10,000-hit hard cap. Floor scaled to 14-day windows —
# a ~7-day half of the busiest family cannot approach 10k (measured 4 ≈ 3k
# per 7-day half); a capped window AT the floor keeps its capped hits,
# disclosed by the caller.
_SPLIT_THRESHOLD = 9500
_SPLIT_FLOOR_DAYS = 7
# Form 4 is split UNCONDITIONALLY into two halves: the busiest family
# (10-15k/14d in filing season exceeds the 10k cap), and two 7-day halves
# cost the same page count as one unsplit query.
_ALWAYS_SPLIT_FORMS = ("4",)

_STREAM_COLUMNS = [
    "form", "who", "ticker", "filed_date", "doc_url", "accession",
]


def _efts_url(root_form: str, start: str, end: str, from_: int) -> str:
    """One efts page URL for a FORM-LEVEL (whole-market) query.

    No ``ciks=`` parameter — the unified stream is a whole-market question.
    ``forms`` carries exactly ONE root form (expands to its /A family);
    never the comma list. Exposed for tests."""
    return (
        f"{_EFTS_URL}?q=&forms={root_form.replace(' ', '%20')}"
        f"&dateRange=custom&startdt={start}&enddt={end}&from={from_}"
    )


def _fetch_window_hits(
    root_form: str, start: str, end: str, cache_dir: Path | None = None,
) -> dict:
    """Every ``_source`` for ``root_form`` filed in [start, end], paginated and
    cached as ONE assembled window file.

    Returns ``{"hits", "capped", "total", "requests"}`` — ``total`` is the
    DECLARED window total (the cap check), ``requests`` the page GET count for
    the request accounting the panel methodology discloses. ``capped`` is True
    when the declared total hit EFTS's 10,000 ceiling and the caller should
    split (the capped hits still carry the newest-first 10k; the split halves
    are the honest full coverage)."""
    slug = root_form.replace(" ", "").replace("/", "-")
    fp = _cache_dir(cache_dir) / f"efts_fstream_{slug}_{start}_{end}.json"
    if fp.exists():
        return json.loads(fp.read_text())
    out: list[dict] = []
    from_ = 0
    total = 0
    requests_ = 0
    while True:
        if requests_:
            time.sleep(2.1)  # explicit page spacing (policy adds its own ≥2s)
        data = _get_json(_efts_url(root_form, start, end, from_))
        requests_ += 1
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
    rec = {
        "hits": out,
        "capped": total >= 10_000,
        "total": total,
        "requests": requests_,
    }
    fp.write_text(json.dumps(rec))
    return rec


def _split_window(start: str, end: str) -> tuple[str, str] | None:
    """(left, right) midpoint split of [start, end], or None at the floor.

    Same Timestamp midpoint arithmetic as form13f_dir (day-number averaging
    would break across month boundaries). The halves share the boundary day —
    aggregation dedups by accession, mirroring the 13F lane."""
    ts_start, ts_end = pd.Timestamp(start), pd.Timestamp(end)
    if (ts_end - ts_start).days <= _SPLIT_FLOOR_DAYS:
        return None
    mid = (ts_start + (ts_end - ts_start) / 2).date().isoformat()
    return (start, mid), (mid, end)


def _fetch_form_window(
    root_form: str, start: str, end: str,
    cache_dir: Path | None, stats: dict,
) -> list[dict]:
    """One window's hits, adaptively split near the cap (form13f_dir pattern).

    A window whose DECLARED total is ≥ ``_SPLIT_THRESHOLD`` (9,500) — close
    enough to EFTS's 10,000 hard cap that pagination may silently truncate —
    splits at the midpoint into two halves (recursion bounded by the split
    floor). A capped window AT the floor keeps its capped hits: the honest
    newest-first 10k, disclosed via ``stats["capped_kept"]``."""
    rec = _fetch_window_hits(root_form, start, end, cache_dir)
    stats["windows"].append(
        {"start": start, "end": end, "total": rec["total"],
         "requests": rec["requests"], "capped": rec["capped"]}
    )
    if rec["total"] >= _SPLIT_THRESHOLD:
        halves = _split_window(start, end)
        if halves is None:
            if rec["capped"]:
                # Floor reached while capped: keep the newest-first 10k.
                stats["capped_kept"] = True
            return rec["hits"]
        (ls, le), (rs, re_) = halves
        left = _fetch_form_window(root_form, ls, le, cache_dir, stats)
        time.sleep(2.1)  # spacing between sibling windows
        right = _fetch_form_window(root_form, rs, re_, cache_dir, stats)
        return left + right
    return rec["hits"]


def fetch_form_family(
    root_form: str, start: str, end: str, cache_dir: Path | None = None,
) -> tuple[list[dict], dict]:
    """(hits, stats) for one root form over [start, end], cap-safe.

    ``stats`` = ``{"windows": [{start, end, total, requests, capped}], "rows":
    n, "split": bool, "capped_kept": bool}`` — the per-form request accounting
    (filing_stream_fetch prints it; the export discloses it). Form 4 is split
    unconditionally into two ~7-day halves (busiest family; same page count as
    one query, season-proof)."""
    stats: dict = {"windows": [], "rows": 0, "split": False, "capped_kept": False}
    if root_form in _ALWAYS_SPLIT_FORMS:
        halves = _split_window(start, end)
        if halves:
            stats["split"] = True
            (ls, le), (rs, re_) = halves
            hits = _fetch_form_window(root_form, ls, le, cache_dir, stats)
            time.sleep(2.1)
            hits += _fetch_form_window(root_form, rs, re_, cache_dir, stats)
        else:
            hits = _fetch_form_window(root_form, start, end, cache_dir, stats)
    else:
        hits = _fetch_form_window(root_form, start, end, cache_dir, stats)
    seen_acc: set[str] = set()
    deduped: list[dict] = []
    for s in hits:  # sibling halves share the boundary day — dedup by accession
        acc = str(s.get("adsh", ""))
        if acc and acc not in seen_acc:
            seen_acc.add(acc)
            deduped.append(s)
    stats["rows"] = len(deduped)
    return deduped, stats


def _ticker_maps(cache_dir: Path | None = None) -> dict[int, str]:
    """Offline CIK→ticker map from the SEC ``company_tickers`` snapshot cached
    by :mod:`aionis.ingest.cik_resolver` (``cik_resolver_raw.json``, falling
    back to the parsed ``cik_resolver_tickers.json``). A CIK with several
    tickers resolves to its first plain ticker in snapshot order —
    deterministic, common-stock-first. CURRENT snapshot, display label only
    (the established 13D-panel caveat; never a research input)."""
    cik2tk: dict[int, str] = {}
    for name in ("cik_resolver_raw.json", "cik_resolver_tickers.json"):
        fp = _cache_dir(cache_dir) / name
        if not fp.exists():
            continue
        try:
            raw = json.loads(fp.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        by_cik: dict[int, list[str]] = {}
        if name.endswith("raw.json"):
            values = raw.values() if isinstance(raw, dict) else []
            for v in values:
                if isinstance(v, dict) and v.get("cik_str") and v.get("ticker"):
                    by_cik.setdefault(int(v["cik_str"]), []).append(str(v["ticker"]))
        else:
            for tk, cik in raw.items():
                by_cik.setdefault(int(cik), []).append(str(tk))
        if by_cik:
            for cik, tks in by_cik.items():
                plain = [t for t in tks if "-" not in t]
                cik2tk[cik] = (plain or tks)[0]
            break
    return cik2tk


def _company_ticker(source: dict, cik2tk: dict[int, str]) -> str:
    """Ticker for a company-form hit: as-of-filing from ``display_names`` when
    the filer carries one, else the offline snapshot by a named CIK. Empty when
    neither resolves (honest, never guessed)."""
    tk = parse_ticker(source.get("display_names"))
    if tk:
        return tk
    for c in source.get("ciks") or []:
        try:
            if int(str(c)) in cik2tk:
                return cik2tk[int(str(c))]
        except (TypeError, ValueError):
            continue
    return ""


def _efts_row(source: dict, root_form: str, cik2tk: dict[int, str]) -> dict | None:
    """One normalized stream row from an EFTS hit, or None (unusable).

    who: the FIRST ``display_names`` entry — the company on company filings,
    and the REPORTING PERSON on Form 4 (verified live: ``"Papermaster Mark D
    (CIK …)"`` precedes the issuer AMD) — the insider is the actor, the
    issuer rides along as the ticker. None→"" hygiene per the v1 add()."""
    who = _parse_company(source.get("display_names"))
    ticker = _company_ticker(source, cik2tk)
    d = str(source.get("file_date", ""))
    accession = str(source.get("adsh", ""))
    cik = _issuer_cik(source)
    if not d or not accession or not who:
        return None
    return {
        "form": str(source.get("form", root_form)) or root_form,
        "who": who,
        "ticker": ticker if isinstance(ticker, str) and ticker != "None" else "",
        "filed_date": d,
        "doc_url": _filing_index_url(cik, accession) if cik else "",
        "accession": accession,
    }


def _schedule13_rows(
    start: str, end: str, cache_dir: Path | None = None,
    cik2tk: dict[int, str] | None = None,
) -> list[dict]:
    """Normalized SC 13D / SC 13G(/A) rows for [start, end] via the daily
    crawler index lanes (EFTS froze on Schedule 13 — the frozen roots are
    probed separately by the caller so a healed index is picked up).

    The daily index lists a filing under EVERY covered company (subject AND
    filers); rows are grouped by accession and the subject is the member whose
    CIK resolves a ticker offline (the ``_sm_dedup_enrich`` heuristic). A
    group with exactly one resolvable subject collapses to ONE row
    ``who = "FILERS → SUBJECT"``; zero/multiple keeps EVERY member honestly
    (no placeholder filer is ever emitted). http→https is normalized."""
    cik2tk = cik2tk if cik2tk is not None else _ticker_maps(cache_dir)
    daily: list[dict] = []
    ds, de = date_t.fromisoformat(start), date_t.fromisoformat(end)
    daily.extend(fetch_recent_13d_daily(ds, de, cache_dir))
    daily.extend(fetch_recent_13g_daily(ds, de, cache_dir))
    groups: dict[str, list[dict]] = {}
    for r in daily:
        acc = str(r.get("accession", "")).removesuffix("-index.htm")
        if acc:
            groups.setdefault(acc, []).append(r)

    def _url(u: str) -> str:
        u = str(u or "")
        if u.startswith("http://www.sec.gov"):
            u = "https" + u[len("http"):]
        return u

    def _tk_of(m: dict) -> str:
        return cik2tk.get(int(m.get("target_cik", 0)), "")

    out: list[dict] = []
    for acc, members in groups.items():
        resolvable = [m for m in members if _tk_of(m)]
        distinct = {_tk_of(m) for m in resolvable}
        if len(distinct) == 1:
            subj = resolvable[0]
            others = [
                str(m.get("target", "")).strip()
                for m in members
                if m is not subj and str(m.get("target", "")).strip()
            ]
            target = str(subj.get("target", "")).strip()
            who = (
                f"{' / '.join(others[:2])} → {target}"
                if others and target
                else target
            )
            if who:
                out.append({
                    "form": str(subj.get("form", "")),
                    "who": who,
                    "ticker": _tk_of(subj),
                    "filed_date": str(subj.get("date", "")),
                    "doc_url": _url(subj.get("url")),
                    "accession": acc,
                })
            continue
        for m in members:  # honest unresolved: every member, no placeholder
            who = str(m.get("target", "")).strip()
            if not who or not str(m.get("date", "")):
                continue
            out.append({
                "form": str(m.get("form", "")),
                "who": who,
                "ticker": _tk_of(m),
                "filed_date": str(m.get("date", "")),
                "doc_url": _url(m.get("url")),
                "accession": acc,
            })
    return out


def fetch_filing_stream(
    *, start: str, end: str, cache_dir: Path | None = None,
) -> tuple[pd.DataFrame, dict]:
    """The v2 unified stream over [start, end]: direct per-root-form queries,
    accession-deduplicated, newest-first.

    Returns ``(df, stats)``: ``df`` columns ``[form, who, ticker, filed_date,
    doc_url, accession]``; ``stats`` carries the per-form request accounting
    (``stats["forms"][root] = stats-dict``) that the fetcher prints and the
    export discloses. Rows without a usable who/doc_url are dropped (the v1
    add() hygiene)."""
    cik2tk = _ticker_maps(cache_dir)
    rows: list[dict] = []
    seen: set[str] = set()
    stats: dict = {"forms": {}, "window": {"start": start, "end": end}}
    for root_form in ROOT_EFTS_FORMS:
        hits, form_stats = fetch_form_family(root_form, start, end, cache_dir)
        stats["forms"][root_form] = form_stats
        for s in hits:
            row = _efts_row(s, root_form, cik2tk)
            if row is None or row["accession"] in seen or not row["doc_url"]:
                continue
            seen.add(row["accession"])
            rows.append(row)
    # Schedule 13: probe both frozen roots (machine-verified zero while
    # frozen; a healed index would contribute rows here too), then ONE
    # combined daily crawler index lane — the primary recent source for
    # both roots. Dedup by accession makes the lanes complementary.
    for root_form in SCHEDULE13_ROOT_FORMS:
        hits, form_stats = fetch_form_family(root_form, start, end, cache_dir)
        stats["forms"][root_form] = form_stats
        for s in hits:
            row = _efts_row(s, root_form, cik2tk)
            if row is None or row["accession"] in seen or not row["doc_url"]:
                continue
            seen.add(row["accession"])
            rows.append(row)
    if SCHEDULE13_ROOT_FORMS:
        time.sleep(2.1)
        daily_rows = _schedule13_rows(start, end, cache_dir, cik2tk)
        stats["schedule13_daily_lane_rows"] = len(daily_rows)
        for r in daily_rows:
            if r["accession"] in seen or not r["doc_url"]:
                continue
            seen.add(r["accession"])
            rows.append(r)
    df = pd.DataFrame(rows, columns=_STREAM_COLUMNS)
    stats["total_rows"] = len(df)
    if df.empty:
        return df, stats
    df = df.sort_values(
        ["filed_date", "form", "who"], ascending=[False, True, True]
    ).reset_index(drop=True)
    return df, stats
