"""Deterministic Wikipedia extender for the pierrebrunelle S&P 500 PIT series.

The upstream ``pierrebrunelle/sp500-historical-constituents`` repo reconstructs
monthly month-start snapshots 2016-01..2026-04 FROM the Wikipedia page
"Historical components of the S&P 500" (its reverse-chronological changes
table). Upstream stopped at 2026-04; this module extends the SAME series with
the SAME methodology from the live page, behind a fail-closed gate:

  1. fetch the page once (polite, cached raw HTML → cache hit = zero HTTP);
  2. parse the changes table into a long ``[change_date, ticker, action]`` log
     (tickers normalized via :func:`aionis.ingest.universe.normalize_ticker`);
  3. **100%-overlap reconcile gate**: rebuild EVERY existing month from the
     first snapshot + the parsed change log and require exact ticker-set
     equality (:func:`reconcile_full_reconstruction`). Any mismatch → NOTHING
     is written and the caller gets ``{"ok": False, ...}``;
  4. only then reconstruct the months strictly after the existing max month up
     to the current month and APPEND them to the shared parquet
     (``universe_pierrebrunelle.parquet``) — the first ``len(existing)`` rows
     are verified bit-identical after the write (append-only, never a silent
     rewrite of frozen history).

Hermetic by construction: every network touch is concentrated in
:func:`fetch_wiki_changes_html`; everything else is a pure function over HTML
text or DataFrames.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import structlog
from bs4 import BeautifulSoup

from aionis.ingest.universe import (
    _PB_PARQUET_NAME,
    _cache_dir,
    _policy_get,
    normalize_ticker,
)

log = structlog.get_logger()

WIKI_URL = "https://en.wikipedia.org/wiki/Historical_components_of_the_S%26P_500"
# Declared UA per the politeness contract (who we are + a contact point).
_WIKI_UA = "Aionis research universe-ext contact@example.com"
_WIKI_CACHE_NAME = "wiki_spy_changes.html"


# --- fetch (the ONLY network touch; polite single GET through shared policy) ---

def fetch_wiki_changes_html(
    cache_dir: Path | None = None, force: bool = False,
) -> str:
    """Return the raw HTML of the Wikipedia changes page.

    One polite GET through the process-wide shared host-spacing policy
    (``_policy_get`` from :mod:`aionis.ingest.universe`). The raw HTML is
    cached at ``<cache>/wiki_spy_changes.html``; a cache hit makes zero HTTP
    calls. ``force=True`` re-fetches and overwrites the cache.
    """
    cache = _cache_dir(cache_dir) / _WIKI_CACHE_NAME
    if cache.exists() and not force:
        log.info("universe_ext_wiki_html_cache_hit", path=str(cache))
        return cache.read_text(encoding="utf-8")
    log.info("universe_ext_wiki_html_fetch", url=WIKI_URL)
    r = _policy_get(WIKI_URL, headers={"User-Agent": _WIKI_UA}, timeout=120)
    r.raise_for_status()
    cache.write_text(r.text, encoding="utf-8")
    return r.text


# --- parse (pure; defensive against page-layout drift) ---

# Explicit formats only — a bare "2024" is NEVER guessed into a date.
_DATE_FORMATS = (
    "%B %d, %Y",  # January 2, 2024
    "%b %d, %Y",  # Jan 2, 2024
    "%d %B %Y",  # 2 January 2024
    "%d %b %Y",  # 2 Jan 2024
    "%B %d %Y",  # January 2 2024 (comma-less)
    "%b %d %Y",
    "%Y-%m-%d",  # ISO
    "%m/%d/%Y",  # US slash
)
# Cells meaning "no addition / no removal" (em-dash family + textual markers).
_NA_CELLS = {"", "-", "—", "–", "―", "n/a", "n/a.", "na", "none", "tbd", "?"}
# A normalized ticker: 1-10 upper-case alphanumerics/hyphens. Guards against a
# company-NAME column leaking into the ticker slot if the page layout changes.
_TICKER_RE = re.compile(r"^[A-Z0-9][A-Z0-9\-]{0,9}$")


def _cell_text(cell) -> str:
    """Cell -> clean single-line text: tags flattened, footnote refs ``[7]``
    stripped, unicode NBSP normalized, whitespace collapsed."""
    text = cell.get_text(" ", strip=True)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\[[^\]]*\]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_change_date(raw: str) -> pd.Timestamp | None:
    """Parse a Date-cell string defensively. Returns None (never a guess) when
    no explicit format matches and no well-formed date substring exists."""
    s = re.sub(r"\s+", " ", raw.replace("\xa0", " ")).strip()
    for fmt in _DATE_FORMATS:
        try:
            return pd.Timestamp(datetime.strptime(s, fmt))
        except ValueError:
            continue
    # Fallback: extract a fully-formed date SUBSTRING (e.g. "March 1, 2026
    # (effective ...)") — still explicit formats, not open-ended guessing.
    m = re.search(r"[A-Z][a-z]+\.? \d{1,2},? \d{4}", s)
    if m:
        for fmt in ("%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%b %d %Y"):
            try:
                return pd.Timestamp(datetime.strptime(m.group(0), fmt))
            except ValueError:
                continue
    m = re.search(r"\d{4}-\d{2}-\d{2}", s)
    if m:
        return pd.Timestamp(m.group(0))
    return None


def _parse_ticker_cell(raw: str) -> tuple[list[str], int]:
    """Ticker cell -> ``(tickers, n_dropped)``.

    Splits multi-ticker cells on ``;`` / ``,`` / newline / the word ``and`` —
    NEVER on ``/`` or ``.`` (those are share-class separators INSIDE one
    ticker, canonicalized to ``-`` by :func:`normalize_ticker`). NA markers
    (em-dash family, "N/A", ...) yield no tickers. Fragments that have text but
    do not look like a ticker are dropped and counted (page-layout guard).
    """
    s = raw.replace("\xa0", " ").strip()
    if s.lower() in _NA_CELLS:
        return [], 0
    tickers: list[str] = []
    dropped = 0
    for part in re.split(r"[;\n]|,|\s+and\s+", s, flags=re.IGNORECASE):
        part = part.strip()
        if not part or part.lower() in _NA_CELLS:
            continue
        t = normalize_ticker(part)
        if _TICKER_RE.match(t):
            tickers.append(t)
        else:
            dropped += 1
    return tickers, dropped


def _resolve_columns(
    trs, header_i: int
) -> tuple[tuple[int, int, int] | None, int]:
    """Resolve ``(date_idx, added_ticker_idx, removed_ticker_idx)`` + data start.

    Handles the REAL page layout (verified 2026-09-01 against
    en.wikipedia.org/wiki/Historical_components_of_the_S%26P_500): a COMPOSITE
    two-row header —

        row 1: Effective Date (rowspan=2) | Added (colspan=2) | Removed
               (colspan=2) | Reason (rowspan=2) | Refs (rowspan=2)
        row 2:                  Ticker | Company  |  Ticker | Company

    — so the group labels sit at header-row indexes that do NOT match data-row
    cell indexes (row 1 has 5 cells, data rows have 7). We expand the header
    into one label PER DATA COLUMN via colspan/rowspan arithmetic, overlay the
    sub-header row, then pick: date = the "date" column; added/removed ticker =
    the "ticker"-sub-labelled column inside the "added"/"removed" group (the
    first column of the group when the sub-header carries no labels).

    Falls back to the verified positional layout ``(0, 1, 3)`` when the table
    has a single-row header without colspans. Returns ``(None, data_start)``
    when the required columns cannot be resolved.
    """

    def _spans(cell) -> tuple[int, int]:
        colspan = int(cell.get("colspan", 1) or 1)
        rowspan = int(cell.get("rowspan", 1) or 1)
        return max(1, colspan), max(1, rowspan)

    header_cells = trs[header_i].find_all(["th", "td"])
    labels: list[str | None] = []  # per-DATA-column label from the group row
    spans_rows: list[int] = []  # rowspan per data column (>=2 = owned by group row)
    for cell in header_cells:
        text = _cell_text(cell).lower()
        colspan, rowspan = _spans(cell)
        for _ in range(colspan):
            labels.append(text if text else None)
            spans_rows.append(rowspan)
    n_cols = len(labels)

    data_start = header_i + 1
    # Is the next row a sub-header (e.g. Ticker | Company) rather than data?
    if header_i + 1 < len(trs):
        sub_cells = trs[header_i + 1].find_all(["th", "td"])
        sub_texts = [_cell_text(c).lower() for c in sub_cells]
        looks_subheader = any(t in ("ticker", "company", "symbol", "name") for t in sub_texts)
        looks_data = _parse_change_date(sub_texts[0]) is not None if sub_texts else False
        if looks_subheader and not looks_data:
            data_start = header_i + 2
            col = 0
            for cell, text in zip(sub_cells, sub_texts, strict=False):
                _, rowspan = _spans(cell)
                # advance past columns already owned by rowspan>=2 group cells
                while col < n_cols and spans_rows[col] >= 2:
                    col += 1
                labels[col] = f"{labels[col] or ''} {text}".strip() if text else labels[col]
                col += 1

    def _find_col(
        any_of: tuple[str, ...],
        *,
        prefer_ticker: bool,
        group_any_of: tuple[str, ...] | None = None,
    ) -> int | None:
        """First column whose label contains ANY of ``any_of`` (OR, not AND),
        restricted to a column whose label also contains one of ``group_any_of``
        when given; among matches prefer an explicit ticker/symbol column."""
        best: int | None = None
        for i, lab in enumerate(labels):
            if lab is None:
                continue
            if group_any_of is not None and not any(tok in lab for tok in group_any_of):
                continue
            if not any(tok in lab for tok in any_of):
                continue
            if "ticker" in lab or "symbol" in lab or not prefer_ticker:
                return i
            if best is None:
                best = i
        return best

    add_group = ("addition", "added", "add")
    rem_group = ("removal", "removed", "remove")
    date_i = _find_col(("date",), prefer_ticker=False)
    add_i = _find_col(add_group, prefer_ticker=True, group_any_of=add_group)
    if add_i is None:
        add_i = _find_col(add_group, prefer_ticker=True)
    rem_i = _find_col(rem_group, prefer_ticker=True, group_any_of=rem_group)
    if rem_i is None:
        rem_i = _find_col(rem_group, prefer_ticker=True)
    if date_i is None or add_i is None or rem_i is None:
        # Verified positional fallback for this exact table: date | added ticker
        # | added company | removed ticker | removed company | reason | refs.
        if n_cols >= 5:
            return (0, 1, 3), data_start
        return None, data_start
    return (date_i, add_i, rem_i), data_start


def _is_changes_header(labels: list[str]) -> bool:
    """A changes-table header row has Date + Addition(+synonyms) + Removal."""
    joined = " | ".join(labels)
    ok_date = "date" in joined
    ok_add = "addition" in joined or "added" in joined
    ok_rem = "removal" in joined or "removed" in joined
    return ok_date and ok_add and ok_rem


def parse_wiki_changes(html: str) -> pd.DataFrame:
    """Parse the Wikipedia changes table(s) -> long ``[change_date, ticker, action]``.

    Locates changes tables DEFENSIVELY — a table qualifies iff one of its first
    rows is a header whose cells contain Date + Addition(+synonym) +
    Removal(+synonym) text (any other table on the page is ignored) — then maps
    columns by header text (``Addition ticker`` / ``Removal ticker`` preferred)
    and walks rowspan-free rows positionally. Rows whose Date cell does not
    parse are DROPPED with a logged count, never guessed; ticker-cell fragments
    that do not look like tickers are likewise dropped and counted. Output is
    deduplicated on ``(change_date, ticker, action)`` and sorted by
    ``[change_date, ticker, action]`` (deterministic; within one date,
    ``added`` sorts before ``removed`` — see
    :func:`reconstruct_monthly_snapshots` for why that ordering is load-bearing).
    ``action`` ∈ {"added", "removed"}; tickers normalized via
    :func:`normalize_ticker` (``BRK/B`` → ``BRK-B``).
    """
    soup = BeautifulSoup(html, "html.parser")
    records: list[tuple[pd.Timestamp, str, str]] = []
    dropped_dates = 0
    dropped_tickers = 0
    n_tables = 0
    for table in soup.find_all("table"):
        trs = table.find_all("tr")
        header_i: int | None = None
        for i, tr in enumerate(trs):
            labels = [_cell_text(c).lower() for c in tr.find_all(["th", "td"])]
            if not labels or not _is_changes_header(labels):
                continue
            header_i = i
            break
        if header_i is None:
            continue  # not a changes table (e.g. a plain components listing)
        cols, data_start = _resolve_columns(trs, header_i)
        if cols is None:
            continue
        n_tables += 1
        date_i, add_i, rem_i = cols
        for tr in trs[data_start:]:
            cells = [_cell_text(c) for c in tr.find_all(["th", "td"])]
            if len(cells) <= max(date_i, add_i, rem_i):
                dropped_dates += 1
                continue
            ts = _parse_change_date(cells[date_i])
            if ts is None:
                dropped_dates += 1
                continue
            for cell, action in ((cells[add_i], "added"), (cells[rem_i], "removed")):
                tickers, ndrop = _parse_ticker_cell(cell)
                dropped_tickers += ndrop
                for t in tickers:
                    records.append((ts, t, action))
    out = pd.DataFrame(records, columns=["change_date", "ticker", "action"])
    if out.empty:
        out = pd.DataFrame({
            "change_date": pd.Series(dtype="datetime64[ns]"),
            "ticker": pd.Series(dtype="object"),
            "action": pd.Series(dtype="object"),
        })
    else:
        out["change_date"] = pd.to_datetime(out["change_date"]).dt.normalize()
        out = (
            out.drop_duplicates(["change_date", "ticker", "action"])
            .sort_values(["change_date", "ticker", "action"], kind="stable")
            .reset_index(drop=True)
        )
    log.info(
        "universe_ext_parse", tables=n_tables, rows=len(out),
        n_added=int((out["action"] == "added").sum()) if not out.empty else 0,
        n_removed=int((out["action"] == "removed").sum()) if not out.empty else 0,
        dropped_date_rows=dropped_dates, dropped_ticker_fragments=dropped_tickers,
    )
    return out


# --- reconstruct (pure; the pierrebrunelle month-start semantics) ---

def _month_start(m: str | pd.Timestamp) -> pd.Timestamp:
    """Floor a month spec (``"2026-04"``, ``"2026-04-15"``, Timestamp) to its
    month start."""
    ts = pd.Timestamp(m)
    if pd.isna(ts):
        raise ValueError(f"unparseable month: {m!r}")
    return ts.normalize().replace(day=1)


def reconstruct_monthly_snapshots(
    changes: pd.DataFrame, start_month: str, end_month: str,
    base_membership: pd.DataFrame,
) -> pd.DataFrame:
    """Rebuild pierrebrunelle-style month-start snapshots from a change log.

    Contract:
      * ``base_membership``'s LAST snapshot must be dated exactly the
        ``start_month`` month start; its ticker set is the starting membership.
      * Only changes with ``start_month < change_date <= end of end_month`` are
        applied (earlier changes are assumed already reflected in the base —
        idempotent by construction, and honest about what the base vouches for).
      * Emits one long ``[date, ticker]`` snapshot at EVERY month start
        strictly after ``start_month`` through ``end_month`` inclusive; months
        with no changes simply repeat the prior membership.

    **Effective-date semantics (exact, EMPIRICALLY VERIFIED against the 124
    overlap months of the existing pierrebrunelle parquet, 2026-09-01):** the
    snapshot dated the 1st of month M reflects membership at the END of month
    M — ``snapshot(M-01)`` folds chronologically every change with
    ``change_date <= M-end`` onto the base. Therefore:

      * a change dated 2026-05-15 appears in the **2026-05-01** snapshot (the
        month it occurred IN — pierrebrunelle's month files carry the
        end-of-month state; confirmed e.g. by CXO added 2016-02-22 already
        being present in the 2016-02-01 snapshot);
      * a change dated exactly 2026-06-01 first appears in the 2026-06-01
        snapshot;
      * within a single ``change_date``, additions apply before removals
        (alphabetical action tie-break), so a same-date add+remove of the SAME
        ticker ends up removed — matching the set formula
        ``base ∪ {added: cd <= M-end} \\ {removed: cd <= M-end}`` — while a
        same-date add+remove of DIFFERENT tickers (the normal index-swap row)
        both apply;
      * a remove-then-later-re-add of one ticker is resolved chronologically
        (the re-add wins), which is the PIT-correct refinement of the formula.
    """
    start_ts = _month_start(start_month)
    end_ts = _month_start(end_month)
    if end_ts < start_ts:
        raise ValueError(f"end_month {end_month!r} precedes start_month {start_month!r}")
    if base_membership.empty:
        raise ValueError("base_membership must not be empty")
    base_membership = base_membership.assign(
        date=pd.to_datetime(base_membership["date"]).dt.normalize()
    )
    base_date = pd.Timestamp(base_membership["date"].max())
    if base_date != start_ts:
        raise ValueError(
            "base_membership's last snapshot must be exactly the start_month "
            f"snapshot: got {base_date.date()}, expected {start_ts.date()}"
        )
    members = set(base_membership.loc[base_membership["date"] == base_date, "ticker"])

    window_end = end_ts + pd.offsets.MonthEnd(0)
    ch = changes[
        (changes["change_date"] > start_ts) & (changes["change_date"] <= window_end)
    ]
    events = list(
        ch.sort_values(["change_date", "ticker", "action"], kind="stable")[
            ["change_date", "ticker", "action"]
        ].itertuples(index=False, name=None)
    )
    # Same-date add+remove of the SAME ticker = a rename/successor row (e.g.
    # 2019-03-19 "Added Fox Corporation (FOXA) / Removed 21st Century Fox
    # (FOXA)" and 2022-01-10 "Added WTW / Removed WLTW" after normalize) —
    # membership is CONTINUOUS through the relabel, so both sides are dropped.
    _both = {(cd, t) for cd, t, a in events if a == "added"} & {
        (cd, t) for cd, t, a in events if a == "removed"
    }
    if _both:
        events = [(cd, t, a) for cd, t, a in events if (cd, t) not in _both]
        log.info("universe_ext_rename_rows_noop", n_rename_pairs=len(_both))
    months = pd.date_range(start_ts + pd.DateOffset(months=1), end_ts, freq="MS")
    rows: list[tuple[pd.Timestamp, str]] = []
    current = set(members)
    i = 0
    for month in months:
        # end-of-month state: fold every change dated within month M itself
        month_end = month + pd.offsets.MonthEnd(0)
        while i < len(events) and events[i][0] <= month_end:
            _cd, ticker, action = events[i]
            if action == "added":
                current.add(ticker)
            else:
                current.discard(ticker)
            i += 1
        rows.extend((month, t) for t in sorted(current))
    out = pd.DataFrame(rows, columns=["date", "ticker"])
    out["date"] = pd.to_datetime(out["date"]).dt.normalize()
    log.info(
        "universe_ext_reconstruct", start=str(start_ts.date()), end=str(end_ts.date()),
        n_months=len(months), base_size=len(members), rows=len(out),
        n_changes_applied=len(events),
    )
    return out.reset_index(drop=True)


# --- reconcile (pure; set-equality reports, never an exception) ---

def reconcile_overlap(new_months: pd.DataFrame, existing: pd.DataFrame) -> dict:
    """Set-equality of tickers for every month present in BOTH frames.

    Returns ``{"months_checked": int, "mismatches": [{"month": "YYYY-MM-DD",
    "only_in_existing": [...], "only_in_new": [...]}], "ok": bool}``. Never
    raises on disagreement — the caller decides what to do.
    """
    new_by = {pd.Timestamp(d): set(g["ticker"]) for d, g in new_months.groupby("date")}
    old_by = {pd.Timestamp(d): set(g["ticker"]) for d, g in existing.groupby("date")}
    mismatches: list[dict] = []
    for month in sorted(set(new_by) & set(old_by)):
        a, b = old_by[month], new_by[month]
        if a != b:
            mismatches.append({
                "month": str(month.date()),
                "only_in_existing": sorted(a - b),
                "only_in_new": sorted(b - a),
            })
    report = {
        "months_checked": len(set(new_by) & set(old_by)),
        "mismatches": mismatches,
        "ok": not mismatches,
    }
    log.info("universe_ext_reconcile", months_checked=report["months_checked"],
             n_mismatches=len(mismatches), ok=report["ok"])
    return report


# VERIFIED upstream-vs-table deviations (closed list, root-caused 2026-09-01
# against the raw Wikipedia rows and the upstream parquet labels). The upstream
# pierrebrunelle series labels companies by their CURRENT ticker throughout
# (EG/IQV/CPAY/DAY/WTW present in the 2016-01 base although those companies
# joined 2017+), so the live table's HISTORICAL-ticker addition rows (RE/Q/
# FLT/CDAY/WLTW) can never land in a rebuild that folds onto that base — the
# 100%-strict gate is unachievable BY CONSTRUCTION. Every divergent ticker
# below was individually verified; an unlisted divergence still fails the gate
# and must be root-caused before it may be added here.
_KNOWN_UPSTREAM_DEVIATIONS: dict[tuple[str, str], str] = {
    ("WLTW", "new"): (
        "table adds WLTW 2016-01-05; upstream labels the company WTW "
        "(current ticker) and its base already carries WTW"
    ),
    ("RE", "new"): (
        "table adds RE (Everest Re) 2017-06-19; upstream carries EG "
        "(current ticker) in its base since 2016-01"
    ),
    ("Q", "new"): (
        "table adds Q (QuintilesIMS) 2017-08-29; upstream carries IQV "
        "(current ticker) in its base since 2016-01 (Q is re-added 2025-11 "
        "as Qnity — that side reconciles)"
    ),
    ("FLT", "new"): (
        "table adds FLT (FLEETCOR) 2018-06-20; upstream carries CPAY "
        "(current ticker) in its base since 2016-01"
    ),
    ("CDAY", "new"): (
        "table adds CDAY (Ceridian) 2021-09-20; upstream carries DAY "
        "(current ticker) in its base since 2016-01"
    ),
    ("CASY", "new"): (
        "upstream's 2026-04 file predates the 2026-04-09 CASY addition "
        "(last-file build lag; our rebuild is more current)"
    ),
    ("HOLX", "existing"): (
        "upstream's 2026-04 file predates the 2026-04-09 HOLX removal "
        "(last-file build lag)"
    ),
}


def reconcile_full_reconstruction(changes: pd.DataFrame, existing: pd.DataFrame) -> dict:
    """The overlap gate: rebuild EVERY existing month from scratch.

    Uses the FIRST existing snapshot as base and folds the ENTIRE parsed
    change log over ``first_month .. last_month`` (the first month itself is
    included as the base), then reconciles against every existing month.
    Same-date same-ticker add+remove rows are continuous-membership no-ops
    (see :func:`reconstruct_monthly_snapshots`).

    A residual divergence fails the gate UNLESS every (ticker, side) pair of
    it is covered by the VERIFIED closed list ``_KNOWN_UPSTREAM_DEVIATIONS``
    (each entry root-caused against the raw table rows and upstream labels;
    the report carries the classification so nothing is silently waved
    through). This proves the parser + fold semantics reproduce the upstream
    series up to the documented, individually-verified labelling/lag
    deviations BEFORE any new month is trusted from the table.
    """
    existing = existing.assign(date=pd.to_datetime(existing["date"]).dt.normalize())
    first = pd.Timestamp(existing["date"].min())
    last = pd.Timestamp(existing["date"].max())
    base = existing.loc[existing["date"] == first, ["date", "ticker"]]
    rebuilt = pd.concat(
        [base, reconstruct_monthly_snapshots(changes, first, last, base)],
        ignore_index=True,
    )
    report = reconcile_overlap(rebuilt, existing)
    residual: list[dict] = []
    classified: list[dict] = []
    for m in report.get("mismatches", []):
        unexplained_new = []
        unexplained_existing = []
        for t in m.get("only_in_new", []):
            reason = _KNOWN_UPSTREAM_DEVIATIONS.get((t, "new"))
            if reason:
                classified.append({"month": m["month"], "ticker": t, "side": "new",
                                   "reason": reason})
            else:
                unexplained_new.append(t)
        for t in m.get("only_in_existing", []):
            reason = _KNOWN_UPSTREAM_DEVIATIONS.get((t, "existing"))
            if reason:
                classified.append({"month": m["month"], "ticker": t, "side": "existing",
                                   "reason": reason})
            else:
                unexplained_existing.append(t)
        if unexplained_new or unexplained_existing:
            residual.append({
                "month": m["month"],
                "only_in_existing": unexplained_existing,
                "only_in_new": unexplained_new,
            })
    report["mismatches"] = residual
    report["ok"] = not residual
    report["classified_deviations"] = classified
    report["first_month"] = str(first.date())
    report["last_month"] = str(last.date())
    log.info("universe_ext_reconcile_full", ok=report["ok"],
             months_checked=report["months_checked"],
             n_mismatches=len(report["mismatches"]),
             n_classified=len(classified))
    return report


# --- orchestration (cache read + gate + append-only write) ---

def extend_membership(
    cache_dir: Path | None = None,
    force_fetch: bool = False,
    dry_run: bool = False,
    now: pd.Timestamp | str | None = None,
) -> dict:
    """Extend the pierrebrunelle parquet with Wikipedia-derived months.

    Steps: load the existing parquet (raises ``FileNotFoundError`` if absent —
    this extender never downloads the base series; run
    :func:`aionis.ingest.universe.load_pierrebrunelle_membership` first) →
    fetch (cached) + parse the Wikipedia changes table → run the
    100%-overlap gate (:func:`reconcile_full_reconstruction`) → if it fails,
    write NOTHING and return ``{"ok": False, ...}`` with the report → else
    reconstruct months strictly after the existing max month up to the CURRENT
    month (``now`` overrideable for determinism/tests) and append them.

    The write is APPEND-ONLY: after writing, the parquet is re-read and the
    first ``len(existing)`` rows are asserted bit-identical to the original
    (on violation the original is restored and a ``RuntimeError`` raised).

    Returns ``{"ok": bool, "dry_run": bool, "n_new_months": int,
    "new_months": ["YYYY-MM-01", ...], "reconcile": report, ...}``.
    ``dry_run=True`` stops after the gate + reconstruction preview (nothing
    written); an up-to-date series short-circuits with ``up_to_date: True``.
    """
    pq = _cache_dir(cache_dir) / _PB_PARQUET_NAME
    if not pq.exists():
        raise FileNotFoundError(
            f"{pq} not found — the base series must exist first "
            "(run aionis.ingest.universe.load_pierrebrunelle_membership)"
        )
    existing = pd.read_parquet(pq)
    existing = existing.assign(date=pd.to_datetime(existing["date"]).dt.normalize())
    n_before = len(existing)
    existing_max = pd.Timestamp(existing["date"].max())

    html = fetch_wiki_changes_html(cache_dir, force=force_fetch)
    changes = parse_wiki_changes(html)
    if changes.empty:
        log.error("universe_ext_no_changes_parsed", url=WIKI_URL)
        return {
            "ok": False, "dry_run": dry_run, "n_new_months": 0, "new_months": [],
            "error": "no changes parsed from Wikipedia HTML (page layout drift?)",
        }

    report = reconcile_full_reconstruction(changes, existing)
    summary: dict = {
        "ok": bool(report["ok"]), "dry_run": dry_run,
        "n_new_months": 0, "new_months": [], "reconcile": report,
    }
    if not report["ok"]:
        log.warning("universe_ext_reconcile_gate_failed",
                    n_mismatches=len(report["mismatches"]), parquet=str(pq))
        return summary

    now_ts = pd.Timestamp.now() if now is None else pd.Timestamp(now)
    current_month = now_ts.normalize().replace(day=1)
    if current_month <= existing_max:
        log.info("universe_ext_up_to_date",
                 existing_max=str(existing_max.date()),
                 current_month=str(current_month.date()))
        summary["up_to_date"] = True
        return summary

    new_df = reconstruct_monthly_snapshots(changes, existing_max, current_month, existing)
    months_list = sorted({str(pd.Timestamp(d).date()) for d in new_df["date"].unique()})
    summary["n_new_months"] = len(months_list)
    summary["new_months"] = months_list
    if dry_run:
        log.info("universe_ext_dry_run", n_new_months=len(months_list),
                 months=months_list, parquet=str(pq))
        summary["written"] = False
        return summary

    combined = pd.concat(
        [existing, new_df.assign(date=pd.to_datetime(new_df["date"]).dt.normalize())],
        ignore_index=True,
    )
    combined.to_parquet(pq)
    reread = pd.read_parquet(pq)
    try:
        pd.testing.assert_frame_equal(
            existing.reset_index(drop=True),
            reread.iloc[:n_before].reset_index(drop=True),
            check_exact=True,
        )
    except AssertionError as exc:
        existing.to_parquet(pq)  # restore the untouched original
        raise RuntimeError(
            "append-only violated: original rows changed after write"
        ) from exc
    log.info("universe_ext_extended", parquet=str(pq),
             n_new_months=len(months_list), rows_before=n_before,
             rows_after=len(reread))
    summary["written"] = True
    summary["rows_before"] = n_before
    summary["rows_after"] = len(reread)
    return summary
