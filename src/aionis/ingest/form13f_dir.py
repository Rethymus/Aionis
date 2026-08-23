"""13F filer directory via EDGAR full-text search (efts) — display-only.

The /filers directory dimension (xiaoyinsi's ~9k-institution list): every
CIK that filed a 13F-HR (or 13F-HR/A) over the trailing ~4 quarters — the
annual filing cycle, so a filer active any time in the year appears.

``browse-edgar`` cannot enumerate a form type without a company (verified
2026-08-23: getcompany+type=13F-HR returns an empty atom feed; a bare UA on
cgi-bin 403s), so the directory rides the SAME EFTS form-level machinery as
form_ipo/form_d: ``forms=13F-HR`` expands to 13F-HR + 13F-HR/A (live-probed:
Q2-2026 = 9,625 filings, page carried both).

CAP SAFETY (the Form D lesson): a quarter can approach EFTS's 10,000-hit
hard cap (9,625 observed), so each quarter window is fetched adaptively —
if the declared total is >= 9,500 the window splits into two ~6-week halves
(recursion bounded by the split floor). ≥2s spacing between page GETs
(process-wide HttpRequestPolicy + explicit sleep). Per-window caches are
idempotent; aggregation is per-CIK: name, n_filings, n_amendments,
latest_filed — directory facts, never holdings (those stay in form13f).

7-gate: SEC EDGAR public domain (17 U.S.C. §105) — G1✓; PIT via file_date
— G2✓; immutable per accession — G3✓; exploratory display-only — G5✓;
polite ≥2s + idempotent caches — G7✓.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd

from aionis.ingest.form4_efts import _cache_dir, _get_json
from aionis.ingest.form_ipo import _issuer_cik, _parse_company

_EFTS_URL = "https://efts.sec.gov/LATEST/search-index"
_PAGE_SIZE = 100
_ROOT_FORM = "13F-HR"
# A quarter at 9,625 observed can cross 10k in busier windows — split below
# this declared total (two ~6-week halves land ~4-5k each, safely under cap).
_SPLIT_THRESHOLD = 9500
# ~3 weeks: the recursion floor (a window this small cannot approach 10k).
_SPLIT_FLOOR_DAYS = 21


def _efts_url(start: str, end: str, from_: int) -> str:
    return (
        f"{_EFTS_URL}?q=&forms={_ROOT_FORM}"
        f"&dateRange=custom&startdt={start}&enddt={end}&from={from_}"
    )


def _window_label(start: str, end: str) -> str:
    return f"{start}_{end}"


def _fetch_window_hits(
    start: str, end: str, cache_dir: Path | None = None,
) -> tuple[list[dict], bool]:
    """Every ``_source`` in [start, end], paginated + cached.

    Returns (hits, capped): ``capped`` is True when the declared total hit
    EFTS's 10,000 ceiling and the caller should split the window (the hits
    from the capped query are still returned — newest-first bias — but the
    split halves are the honest full coverage).
    """
    fp = _cache_dir(cache_dir) / f"efts_13f_dir_{_window_label(start, end)}.json"
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


def fetch_filer_window(
    start: str, end: str, cache_dir: Path | None = None,
) -> list[dict]:
    """Full hit list for [start, end], splitting adaptively near the cap."""
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
    left = fetch_filer_window(start, mid, cache_dir)
    time.sleep(2.1)
    right = fetch_filer_window(mid, end, cache_dir)
    return left + right


def fetch_filer_directory(
    *, quarters: list[tuple[str, str]], cache_dir: Path | None = None,
) -> pd.DataFrame:
    """Aggregate the filer directory across quarter windows.

    ``quarters`` is a list of (start, end) ISO windows covering the trailing
    ~annual cycle. Returns ``[cik, name, n_filings, n_amendments,
    latest_filed]`` sorted by latest_filed descending; per-CIK counts are
    deduplicated by accession across overlapping windows.
    """
    agg: dict[int, dict] = {}
    seen: set[str] = set()
    for qs, qe in quarters:
        for s in fetch_filer_window(qs, qe, cache_dir):
            accession = str(s.get("adsh", ""))
            d = str(s.get("file_date", ""))
            if not accession or not d or not (qs <= d <= qe):
                continue
            if accession in seen:
                continue
            seen.add(accession)
            cik = _issuer_cik(s)
            if not cik:
                continue
            form = str(s.get("form", ""))
            row = agg.setdefault(
                cik,
                {
                    "cik": cik,
                    "name": _parse_company(s.get("display_names")),
                    "n_filings": 0,
                    "n_amendments": 0,
                    "latest_filed": d,
                },
            )
            if form == "13F-HR/A":
                row["n_amendments"] += 1
            else:
                row["n_filings"] += 1
            row["latest_filed"] = max(row["latest_filed"], d)
    df = pd.DataFrame(
        list(agg.values()),
        columns=["cik", "name", "n_filings", "n_amendments", "latest_filed"],
    )
    if df.empty:
        return df
    return (
        df.sort_values(["latest_filed", "name"], ascending=[False, True])
        .reset_index(drop=True)
    )
