"""Forward 13D/13D-A collector — snapshot-on-arrival (E3 Slice 2, source 1).

At each month-end FREEZE timestamp ``snapshot_ts``, polls EDGAR
``submissions_{cik}.json`` for every universe ticker and emits the SC 13D /
13D-A filings FILED in the half-open window ``(last_poll_ts, snapshot_ts]``. This
is the forward analog of :func:`aionis.ingest.stakes_13d.filings_13d`: same
source, same filed-date PIT anchor, same SEC polite-retry stack — but forward-
only (never reconstructs history; the first run starts the series at its own
``snapshot_ts``) and I3-sealed (``event_ts <= snapshot_ts`` asserted per row).

**HIGH reuse** — the only net-new logic is the forward window + the snapshot-on-
arrival archival discipline. Reuses:
  * :func:`aionis.ingest.stakes_13d.fetch_submissions` — the cached submissions
    JSON fetch (cache hit -> no HTTP).
  * :data:`aionis.ingest.stakes_13d._13D_FORMS` — the ``SC 13D`` / ``SC 13D/A``
    form set (amendments are NEW filings, never overwrites).
  * :mod:`aionis.ingest.forward._common` — immutable raw archive, cumulative
    parquet (concat, dedup), ``data_ingest`` ledger row, and the I3 assertion.

**Forward window** is the ``recent`` block only (the latest ~1000 filings): a
1-month forward poll is always within it, and historical backfill is explicitly
NOT done (forward discipline — there is no permissively-licensed 13D *history*
to reconstruct; we snapshot-on-arrival from the first run, like
:mod:`aionis.ingest.reddit_sentiment`).
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import structlog

from aionis.ingest import stakes_13d
from aionis.ingest.forward import _common

log = structlog.get_logger()

DATASET = "stakes_13d_forward"
SOURCE = "SEC EDGAR submissions (data.sec.gov)"
LICENSE = "SEC EDGAR public domain (17 U.S.C. §105); filed-date PIT"
_EVENT_TS_COL = "event_ts"  # == filing_date (the PIT anchor)


def _slice_13d_forward(
    recent: dict,
    last_poll_ts: str | datetime | None,
    snapshot_ts: str,
) -> list[dict]:
    """Filter the submissions ``recent`` block to 13D filings in the forward window.

    Half-open ``(last_poll_ts, snapshot_ts]``: a filing already collected at the
    prior snapshot (``filing_date <= last_poll_ts``) is excluded so it is not
    double-counted; a filing dated after ``snapshot_ts`` is excluded (PIT filter
    — not yet knowable at the freeze). Returns rows of
    ``{form, filing_date, accession, primary_doc}``.
    """
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accns = recent.get("accessionNumber", [])
    docs = recent.get("primaryDocument", [])
    last_dt = _common.to_utc_dt(last_poll_ts) if last_poll_ts else None
    snap_dt = _common.to_utc_dt(snapshot_ts)
    out: list[dict] = []
    for i, form in enumerate(forms):
        if form not in stakes_13d._13D_FORMS:
            continue
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
                "primary_doc": str(docs[i]) if i < len(docs) else "",
            }
        )
    return out


def collect_13d_forward(
    ciks: dict[str, int],
    *,
    snapshot_ts: str | datetime | None = None,
    last_poll_ts: str | datetime | None = None,
    cache_dir: Path | None = None,
    runs_dir: Path | str | None = None,
) -> pd.DataFrame:
    """One forward snapshot of SC 13D / 13D-A filings filed in ``(last_poll_ts, snapshot_ts]``.

    First run: pass ``last_poll_ts=None`` (lower bound open) to collect ALL
    filings filed ``<= snapshot_ts``; subsequent runs pass the prior
    ``snapshot_ts`` to collect only net-new filings.

    For each ``(ticker, cik)`` in ``ciks``, fetches the cached submissions JSON,
    slices the 13D filings in the forward window, and emits a long frame
    ``[ticker, cik, feature, value, form, filing_date, accession, event_ts,
    snapshot_ts]`` (``feature="stake_13d_filing"``, ``value=1.0`` per filing).

    Side effects (append-only, never overwrite):
      * archives the raw per-ticker filings to
        ``<cache>/<DATASET>_raw_<snapshot_ts>.json`` (immutable, sha256-pinned).
      * appends the snapshot rows to ``<cache>/<DATASET>.parquet`` (concat with
        dedup — prior snapshots preserved, re-freeze of the same snapshot_ts is
        idempotent).
      * appends one ``data_ingest`` ledger row (``forward_only: true``,
        ``snapshot_ts``, ``data_sha256``) under ``runs_dir`` (idempotent).

    The I3 gate is asserted on the emitted frame: every ``event_ts``
    (``= filing_date``) is ``<= snapshot_ts``.
    """
    snapshot_ts = _common.canonical_snapshot_ts(snapshot_ts)
    cdir = _common.cache_dir(cache_dir)

    raw_payload: dict[str, list[dict]] = {}
    rows: list[dict] = []
    for ticker, cik in ciks.items():
        tkr = str(ticker).strip().upper()
        try:
            sub = stakes_13d.fetch_submissions(int(cik), cdir)
        except Exception as e:  # a stubborn CIK must not abort the whole snapshot
            log.warning("forward_13d_cik_skip", ticker=tkr, cik=cik, error=str(e))
            continue
        recent = sub.get("filings", {}).get("recent", {})
        filings = _slice_13d_forward(recent, last_poll_ts, snapshot_ts)
        if filings:
            raw_payload[tkr] = filings
        for fr in filings:
            rows.append(
                {
                    "ticker": tkr,
                    "cik": int(cik),
                    "feature": "stake_13d_filing",
                    "value": 1.0,
                    "form": fr["form"],
                    "filing_date": fr["filing_date"],
                    "accession": fr["accession"],
                    "primary_doc": fr.get("primary_doc", ""),
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
        extra_ledger_fields={"n_tickers": len(ciks)},
    )
    log.info(
        "forward_13d_collected",
        snapshot_ts=snapshot_ts,
        n_rows=len(frame),
        n_tickers_with_filing=len(raw_payload),
    )
    return frame


__all__ = ["DATASET", "collect_13d_forward"]
