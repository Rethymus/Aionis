"""E3 Slice 3c - freeze the forward information set I_t (snapshot-on-arrival).

At each month-end predict timestamp, FREEZE the three forward collectors (Slice 2)
under ONE shared ``(snapshot_ts, last_poll_ts)`` clock, build a canonical manifest
of the sealed snapshot, and commit a ``forward_iset_frozen`` ledger row carrying
its sha256 - BEFORE any fit / commit happens (the per-freeze analog of the
project's ``config_committed BEFORE result`` anchor).

Reuses, does not reinvent:
  * the three Slice-2 collectors (:mod:`aionis.ingest.forward`) - each returns its
    long frame AND writes its OWN ``data_ingest`` row + immutable raw archive;
  * :func:`aionis.ingest.forward._common.sha256_bytes` to re-read the sealed raw
    archive (the manifest's per-dataset ``raw_sha256`` integrity anchor);
  * :func:`aionis.reporting.forward_ledger._append_ledger_row` for the
    ``forward_iset_frozen`` row (event-typed, idempotent on re-freeze).

No fit, no LLM, no scoring here. Slice 3c scope = freeze + manifest + iset-frozen
row. The fit/commit step lives in :mod:`aionis.eval.forward_commit` (Slice 3d).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import structlog

from aionis.ingest.forward import _common
from aionis.ingest.forward.earnings_8k_forward import (
    DATASET as EARNINGS_DATASET,
)
from aionis.ingest.forward.earnings_8k_forward import collect_8k_forward
from aionis.ingest.forward.macro_forward import DATASET as MACRO_DATASET
from aionis.ingest.forward.macro_forward import collect_macro_forward
from aionis.ingest.forward.stakes_13d_forward import (
    DATASET as STAKES_DATASET,
)
from aionis.ingest.forward.stakes_13d_forward import collect_13d_forward
from aionis.reporting import forward_ledger

log = structlog.get_logger()

PHASE = "E3"
EVENT_ISET_FROZEN = "forward_iset_frozen"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _iso_date(x: object) -> str:
    """Canonical YYYY-MM-DD for a pub/filing date (``""`` for missing/NaT).

    The manifest key must be a stable string so two freezes of the same logical
    date collapse to the same key regardless of whether the collector emitted a
    pandas Timestamp or an ISO string.
    """
    if x is None or (isinstance(x, float) and pd.isna(x)) or pd.isna(x):
        return ""
    try:
        return pd.Timestamp(x).normalize().strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return str(x)


def _macro_keys(df: pd.DataFrame) -> list[list[str]]:
    """Sorted ``(event_type, pub_date_iso, series_id)`` identity keys for the macro frame."""
    if df.empty:
        return []
    rows = [
        [str(r.event_type), _iso_date(r.pub_date), str(r.series_id)]
        for r in df.itertuples(index=False)
    ]
    return sorted(rows)


def _filing_keys(df: pd.DataFrame) -> list[list[str]]:
    """Sorted ``(ticker, filing_date_iso, accession)`` identity keys for 13d/8k frames."""
    if df.empty:
        return []
    rows = [
        [str(r.ticker), _iso_date(r.filing_date), str(r.accession)]
        for r in df.itertuples(index=False)
    ]
    return sorted(rows)


# ---------------------------------------------------------------------------
# freeze - the three collectors under ONE shared clock
# ---------------------------------------------------------------------------


def freeze_forward_iset(
    *,
    snapshot_ts: str,
    last_poll_ts: str | None,
    ciks: dict[str, int],
    tickers: list[str],
    fred_api_key: str | None,
    cache_dir: Path,
    runs_dir: Path | str,
) -> dict:
    """FREEZE the three forward collectors under ONE shared ``(snapshot_ts, last_poll_ts)`` clock.

    Each collector returns its long frame AND writes its own immutable raw archive
    + ``data_ingest`` ledger row (Slice 2). The freeze re-reads each sealed raw
    archive via :func:`_common.sha256_bytes` so the manifest's ``raw_sha256`` is an
    auditable integrity anchor (a byte mutation in the archive flips it).

    Returns ``{macro_df, stakes_df, earnings_df, snapshot_ts, raw_sha256s}``.
    """
    snap = _common.canonical_snapshot_ts(snapshot_ts)
    macro_df = collect_macro_forward(
        snapshot_ts=snap, last_poll_ts=last_poll_ts, fred_api_key=fred_api_key,
        cache_dir=cache_dir, runs_dir=runs_dir,
    )
    stakes_df = collect_13d_forward(
        ciks, snapshot_ts=snap, last_poll_ts=last_poll_ts,
        cache_dir=cache_dir, runs_dir=runs_dir,
    )
    earnings_df = collect_8k_forward(
        tickers, snapshot_ts=snap, last_poll_ts=last_poll_ts,
        cache_dir=cache_dir, runs_dir=runs_dir,
    )
    compact = _common.compact_snapshot_ts(snap)
    raw_sha256s = {
        name: _common.sha256_bytes(cache_dir / f"{name}_raw_{compact}.json")
        for name in (MACRO_DATASET, STAKES_DATASET, EARNINGS_DATASET)
    }
    log.info(
        "forward_iset_frozen_data",
        snapshot_ts=snap, n_macro=len(macro_df), n_stakes=len(stakes_df),
        n_earnings=len(earnings_df),
    )
    return {
        "macro_df": macro_df,
        "stakes_df": stakes_df,
        "earnings_df": earnings_df,
        "snapshot_ts": snap,
        "raw_sha256s": raw_sha256s,
    }


# ---------------------------------------------------------------------------
# manifest + iset sha256
# ---------------------------------------------------------------------------


def iset_manifest(freeze_out: dict, *, uv_lock_sha256: str) -> dict:
    """Canonical manifest of the sealed I_t snapshot (sorted, json-serializable).

    Per dataset: ``n_rows`` + ``raw_sha256`` (re-read from the sealed archive at
    freeze) + ``keys`` (sorted identity tuples). macro keys =
    ``(event_type, pub_date_iso, series_id)``; 13d/8k keys =
    ``(ticker, filing_date_iso, accession)``. Adding a filing OR mutating the raw
    bytes flips :func:`iset_sha256_from_manifest` (the freeze integrity anchor).
    """
    macro_df = freeze_out["macro_df"]
    stakes_df = freeze_out["stakes_df"]
    earnings_df = freeze_out["earnings_df"]
    raw = freeze_out["raw_sha256s"]
    return {
        MACRO_DATASET: {
            "n_rows": int(len(macro_df)),
            "raw_sha256": raw[MACRO_DATASET],
            "keys": _macro_keys(macro_df),
        },
        STAKES_DATASET: {
            "n_rows": int(len(stakes_df)),
            "raw_sha256": raw[STAKES_DATASET],
            "keys": _filing_keys(stakes_df),
        },
        EARNINGS_DATASET: {
            "n_rows": int(len(earnings_df)),
            "raw_sha256": raw[EARNINGS_DATASET],
            "keys": _filing_keys(earnings_df),
        },
        "snapshot_ts": freeze_out["snapshot_ts"],
        "uv_lock_sha256": uv_lock_sha256,
    }


def iset_sha256_from_manifest(manifest: dict) -> str:
    """sha256 of the canonical manifest (the freeze key; durable across reruns).

    ``sort_keys=True, default=str`` mirrors :func:`forward_ledger.config_sha256`
    so the freeze key is byte-stable for an identical manifest (H6) and flips on
    any structural change (added filing, mutated raw bytes, changed uv.lock).
    """
    blob = json.dumps(manifest, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()


# ---------------------------------------------------------------------------
# commit the forward_iset_frozen ledger row (idempotent)
# ---------------------------------------------------------------------------


def commit_forward_iset_frozen(
    *,
    snapshot_ts: str,
    iset_sha256: str,
    runs_dir: Path | str,
    mode: str = "exploratory",
    manifest_summary: dict | None = None,
    **extra: object,
) -> dict:
    """Append the ``forward_iset_frozen`` ledger row (idempotent on re-freeze).

    Dedup: if a ``forward_iset_frozen`` row already exists for the SAME
    ``(snapshot_ts, iset_sha256)``, NO duplicate is appended (a re-freeze of a
    sealed I_t is a ledger no-op). Returns the row dict with ``_appended: True``
    on a fresh append or ``_appended: False`` on an idempotent skip.
    """
    snap = _common.canonical_snapshot_ts(snapshot_ts)
    for r in forward_ledger.read_forward_rows(runs_dir=runs_dir, event=EVENT_ISET_FROZEN):
        if r.get("snapshot_ts") == snap and r.get("iset_sha256") == iset_sha256:
            log.info("forward_iset_frozen_idempotent", snapshot_ts=snap)
            return {**r, "_appended": False}
    row: dict = {
        "event": EVENT_ISET_FROZEN,
        "phase": PHASE,
        "mode": mode,
        "snapshot_ts": snap,
        "iset_sha256": iset_sha256,
    }
    if manifest_summary is not None:
        row["manifest_summary"] = manifest_summary
    row.update(extra)
    appended = forward_ledger._append_ledger_row(runs_dir, row)
    return {**appended, "_appended": True}


__all__ = [
    "PHASE",
    "EVENT_ISET_FROZEN",
    "freeze_forward_iset",
    "iset_manifest",
    "iset_sha256_from_manifest",
    "commit_forward_iset_frozen",
]
