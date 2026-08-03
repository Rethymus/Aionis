"""Forward ALFRED macro-surprise collector — snapshot-on-arrival (E3 Slice 2, source 2).

At each month-end FREEZE timestamp ``snapshot_ts``, computes the ALFRED
scheduled-release (CPI/NFP) surprise for every release PUBLISHED in the half-open
window ``(last_poll_ts, snapshot_ts]``. The surprise for a release at time ``r``
is REVEALED AT ``r`` (08:30 ET) and is constructed ONLY from vintages published
strictly before ``r`` (the same no-lookahead rule as
:mod:`aionis.features.macro_surprise`).

**HIGH reuse** — the only net-new logic is the forward window + the snapshot-on-
arrival archival discipline. Reuses:
  * :func:`aionis.features.macro_surprise.fetch_alfred_vintages` — cached vintage
    frame (cache hit -> no HTTP).
  * :func:`aionis.features.macro_surprise.first_print_changes` + \
    :func:`aionis.features.macro_surprise.surprise_time_series` — the strictly-
    PIT expectation + clipped-z construction (unchanged).
  * :data:`aionis.features.macro_surprise.SERIES_FOR_EVENT_TYPE` — the
    CPI (CPIAUCSL, MoM %) / NFP (PAYEMS, MoM diff) series map.
  * :mod:`aionis.ingest.forward._common` — immutable raw archive, cumulative
    parquet, ``data_ingest`` ledger row, and the I3 assertion.

Macro surprise is a **cross-section-broadcast** feature (one value per release,
identical across tickers at freeze time); this collector emits date-keyed rows
``[series_id, event_type, feature, ref_date, pub_date, surprise_z, value,
event_ts, snapshot_ts]`` and the Slice 3 freeze broadcasts them across the
universe (same as :func:`aionis.features.macro_surprise.macro_surprise_date_broadcast`).
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import structlog

from aionis.config import settings
from aionis.features import macro_surprise
from aionis.ingest.forward import _common

log = structlog.get_logger()

DATASET = "macro_forward"
SOURCE = "FRED/ALFRED scheduled-release vintages"
LICENSE = "FRED public domain (https://fred.stlouisfed.org/legal/); vintage as-of join"
_EVENT_TS_COL = "event_ts"  # == pub_date (the release date — PIT anchor)


def collect_macro_forward(
    *,
    snapshot_ts: str | datetime | None = None,
    last_poll_ts: str | datetime | None = None,
    fred_api_key: str | None = None,
    cache_dir: Path | None = None,
    runs_dir: Path | str | None = None,
) -> pd.DataFrame:
    """One forward snapshot of CPI/NFP first-print surprises published in
    ``(last_poll_ts, snapshot_ts]``.

    For each CPI/NFP series, fetches the cached ALFRED vintages, rebuilds the
    strictly-PIT surprise time series, and emits one row per release with
    ``pub_date`` in the forward window. Emits
    ``[series_id, event_type, feature, ref_date, pub_date, surprise_z, value,
    event_ts, snapshot_ts]`` where ``value`` = ``surprise_z`` (may be NaN if the
    release is too early to compute a z — the consumer zero-fills, matching
    :func:`aionis.features.macro_surprise.build_surprise_features`).

    Side effects (append-only, never overwrite):
      * archives the raw per-series release rows to
        ``<cache>/<DATASET>_raw_<snapshot_ts>.json`` (immutable, sha256-pinned).
      * appends the snapshot rows to ``<cache>/<DATASET>.parquet`` (concat with
        dedup — prior snapshots preserved, re-freeze idempotent).
      * appends one ``data_ingest`` ledger row (``forward_only: true``,
        ``snapshot_ts``, ``data_sha256``) under ``runs_dir`` (idempotent).

    The I3 gate is asserted on the emitted frame: every ``event_ts``
    (``= pub_date``) is ``<= snapshot_ts``.
    """
    snapshot_ts = _common.canonical_snapshot_ts(snapshot_ts)
    key = fred_api_key or settings.fred_api_key
    if not key:
        raise RuntimeError(
            "FRED_API_KEY required for forward macro surprise (set FRED_API_KEY "
            "in .env or pass fred_api_key=). This module never fakes a pull and "
            "never backfills history."
        )
    cdir = _common.cache_dir(cache_dir)

    raw_payload: dict[str, list[dict]] = {}
    rows: list[dict] = []
    for event_type, (series_id, change_kind) in macro_surprise.SERIES_FOR_EVENT_TYPE.items():
        vintages = macro_surprise.fetch_alfred_vintages(series_id, key, cdir)
        ts = macro_surprise.surprise_time_series(
            macro_surprise.first_print_changes(vintages, change_kind)
        )
        series_rows: list[dict] = []
        for _, r in ts.iterrows():
            pub = r["pub_date"]
            if pd.isna(pub):
                continue
            ev = _common.to_utc_dt(pub)
            if last_poll_ts is not None and ev <= _common.to_utc_dt(last_poll_ts):
                continue  # already collected at a prior snapshot
            if ev > _common.to_utc_dt(snapshot_ts):
                continue  # PIT filter: published after snapshot_ts -> not yet knowable
            z = r["surprise_z"]
            z_val = float(z) if not pd.isna(z) else float("nan")
            row = {
                "series_id": series_id,
                "event_type": event_type,
                "feature": f"macro_{series_id.lower()}_surprise",
                "ref_date": r["ref_date"],
                "pub_date": pub,
                "surprise_z": z_val,
                "value": z_val,
                "event_ts": pub,
                "snapshot_ts": snapshot_ts,
            }
            rows.append(row)
            # archive_raw uses json.dumps(default=str) so Timestamps serialize fine.
            series_rows.append(row)
        if series_rows:
            raw_payload[series_id] = series_rows

    frame = pd.DataFrame(rows)
    # I3 leakage gate (defensive post-condition; the window filter already excluded future pubs).
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
        extra_ledger_fields={"series": list(macro_surprise.SERIES_FOR_EVENT_TYPE.keys())},
    )
    log.info(
        "forward_macro_collected",
        snapshot_ts=snapshot_ts, n_rows=len(frame),
        n_series=len(raw_payload),
    )
    return frame


__all__ = ["DATASET", "collect_macro_forward"]
