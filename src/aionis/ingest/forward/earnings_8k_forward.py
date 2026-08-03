"""Forward 8-K Item 2.02 earnings-release collector — snapshot-on-arrival
(E3 Slice 2, source 3).

At each month-end FREEZE timestamp ``snapshot_ts``, polls EDGAR
``submissions_{cik}.json`` for every universe ticker and emits the 8-K filings
reporting **Item 2.02** (Results of Operations and Financial Condition — the SEC-
mandated material earnings-release disclosure) FILED in the half-open window
``(last_poll_ts, snapshot_ts]``. This is the forward earnings-event stream; same
filed-date PIT anchor as :mod:`aionis.ingest.stakes_13d`, same snapshot-on-
arrival discipline, I3-sealed (``event_ts <= snapshot_ts`` asserted per row).

**NET-NEW** logic = the 8-K + Item 2.02 form-type filter (pre-reg §4 row 3:
"待建（复用 ``ingest/fundamentals.py`` EDGAR 栈；8-K form-type 过滤）"). The EDGAR
"stack" reused:
  * :func:`aionis.ingest.fundamentals.cik_map` — the cached ticker -> CIK map
    (current snapshot; PIT-correct for "as-of now" forward collection of the live
    universe — forward does not reconstruct historical/renamed tickers).
  * :func:`aionis.ingest.stakes_13d.fetch_submissions` — the cached submissions
    index (``data.sec.gov/submissions/CIK{cik}.json``). The submissions index
    (NOT ``fundamentals.company_facts`` — that is XBRL facts, which do not carry
    8-K filings or item codes) is what exposes ``form`` + ``filingDate`` +
    ``items`` per filing.
  * :mod:`aionis.ingest.forward._common` — immutable raw archive, cumulative
    parquet, ``data_ingest`` ledger row, and the I3 assertion.

**Item 2.02 filter**: the submissions ``recent`` block carries an ``items``
parallel array whose each entry is a string of comma/whitespace-separated SEC
item codes reported on that filing (e.g. ``"Item 2.02,Item 9.01"``). We keep only
filings where ``form == "8-K"`` AND the items string contains the token
``2.02`` (the material-earnings-release item). The word-boundary regex
(``\\b2\\.02\\b``) avoids colliding with ``2.020``, ``12.02``, etc.

Forward window = the ``recent`` block only (no historical backfill — forward
discipline; a 1-month poll is always within the latest ~1000 filings).
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import structlog

from aionis.ingest import fundamentals, stakes_13d
from aionis.ingest.forward import _common

log = structlog.get_logger()

DATASET = "earnings_8k_forward"
SOURCE = "SEC EDGAR submissions (data.sec.gov), 8-K Item 2.02 filter"
LICENSE = "SEC EDGAR public domain (17 U.S.C. §105); filed-date PIT"
_EVENT_TS_COL = "event_ts"  # == filing_date (the PIT anchor)
_8K_FORM = "8-K"
# Match the SEC item code "2.02" with word boundaries so "2.020" / "12.02" do not
# collide. EDGAR serializes items as e.g. "Item 2.02 Results of Operations...".
_ITEM_2_02_RE = re.compile(r"\b2\.02\b")


def _slice_8k_forward(
    recent: dict,
    last_poll_ts: str | datetime | None,
    snapshot_ts: str,
) -> list[dict]:
    """Filter the submissions ``recent`` block to 8-K Item 2.02 filings in the window.

    Half-open ``(last_poll_ts, snapshot_ts]``: a filing already collected at the
    prior snapshot is excluded; a filing dated after ``snapshot_ts`` is excluded
    (PIT filter). Returns rows of ``{form, filing_date, accession, items,
    primary_doc}``.
    """
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accns = recent.get("accessionNumber", [])
    docs = recent.get("primaryDocument", [])
    # EDGAR's recent block exposes `items` as a parallel array of comma/sep item
    # strings; fall back to an empty list if the field is absent (older payloads).
    items_arr = recent.get("items", []) or []
    last_dt = _common.to_utc_dt(last_poll_ts) if last_poll_ts else None
    snap_dt = _common.to_utc_dt(snapshot_ts)
    out: list[dict] = []
    for i, form in enumerate(forms):
        if form != _8K_FORM:
            continue
        items_str = str(items_arr[i]) if i < len(items_arr) else ""
        if not _ITEM_2_02_RE.search(items_str):
            continue  # only Item 2.02 (material earnings release)
        d = str(dates[i]) if i < len(dates) else ""
        if not d:
            continue
        ev = _common.to_utc_dt(d)
        if last_dt is not None and ev <= last_dt:
            continue  # already collected at a prior snapshot
        if ev > snap_dt:
            continue  # PIT filter: filed after snapshot_ts -> not yet knowable
        out.append(
            {
                "form": form,
                "filing_date": d,
                "accession": str(accns[i]) if i < len(accns) else "",
                "items": items_str,
                "primary_doc": str(docs[i]) if i < len(docs) else "",
            }
        )
    return out


def collect_8k_forward(
    tickers: list[str],
    *,
    snapshot_ts: str | datetime | None = None,
    last_poll_ts: str | datetime | None = None,
    cik_override: dict[str, int] | None = None,
    cache_dir: Path | None = None,
    runs_dir: Path | str | None = None,
) -> pd.DataFrame:
    """One forward snapshot of 8-K Item 2.02 earnings releases filed in
    ``(last_poll_ts, snapshot_ts]``.

    Resolves each ticker to a CIK via :func:`fundamentals.cik_map` (or
    ``cik_override``), fetches the cached submissions JSON, slices the 8-K Item
    2.02 filings in the forward window, and emits a long frame
    ``[ticker, cik, feature, value, form, filing_date, accession, items,
    event_ts, snapshot_ts]`` (``feature="earnings_8k_item_2_02"``, ``value=1.0``
    per release).

    Side effects (append-only, never overwrite):
      * archives the raw per-ticker filings to
        ``<cache>/<DATASET>_raw_<snapshot_ts>.json`` (immutable, sha256-pinned).
      * appends the snapshot rows to ``<cache>/<DATASET>.parquet`` (concat with
        dedup — prior snapshots preserved, re-freeze idempotent).
      * appends one ``data_ingest`` ledger row (``forward_only: true``,
        ``snapshot_ts``, ``data_sha256``) under ``runs_dir`` (idempotent).

    The I3 gate is asserted on the emitted frame: every ``event_ts``
    (``= filing_date``) is ``<= snapshot_ts``.
    """
    snapshot_ts = _common.canonical_snapshot_ts(snapshot_ts)
    cdir = _common.cache_dir(cache_dir)

    keyfn = str.upper
    cmap = cik_override if cik_override is not None else fundamentals.cik_map(cdir)

    raw_payload: dict[str, list[dict]] = {}
    rows: list[dict] = []
    for t in tickers:
        tkr = keyfn(str(t).strip())
        if not tkr:
            continue
        cik = cmap.get(tkr)
        if not cik:
            log.warning("forward_8k_no_cik", ticker=tkr)
            continue
        try:
            sub = stakes_13d.fetch_submissions(int(cik), cdir)
        except Exception as e:  # a stubborn CIK must not abort the whole snapshot
            log.warning("forward_8k_cik_skip", ticker=tkr, cik=cik, error=str(e))
            continue
        recent = sub.get("filings", {}).get("recent", {})
        filings = _slice_8k_forward(recent, last_poll_ts, snapshot_ts)
        if filings:
            raw_payload[tkr] = filings
        for fr in filings:
            rows.append(
                {
                    "ticker": tkr,
                    "cik": int(cik),
                    "feature": "earnings_8k_item_2_02",
                    "value": 1.0,
                    "form": fr["form"],
                    "filing_date": fr["filing_date"],
                    "accession": fr["accession"],
                    "items": fr["items"],
                    "event_ts": fr["filing_date"],
                    "snapshot_ts": snapshot_ts,
                }
            )

    frame = pd.DataFrame(rows)
    # I3 leakage gate (defensive post-condition; the slice already filtered).
    _common.assert_forward_clock(frame, _EVENT_TS_COL, snapshot_ts)

    _common.persist_snapshot(
        cdir,
        runs_dir,
        dataset=DATASET,
        snapshot_ts=snapshot_ts,
        raw_payload=raw_payload,
        frame=frame,
        source=SOURCE,
        license=LICENSE,
        extra_ledger_fields={"n_tickers": len(tickers)},
    )
    log.info(
        "forward_8k_collected",
        snapshot_ts=snapshot_ts, n_rows=len(frame),
        n_tickers_with_filing=len(raw_payload),
    )
    return frame


__all__ = ["DATASET", "collect_8k_forward"]
