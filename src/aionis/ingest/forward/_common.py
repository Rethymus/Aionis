"""Shared snapshot-on-arrival discipline for E3 forward ingest (Slice 2).

The three forward collectors (13D poll / FRED-ALFRED macro / 8-K earnings) all
follow the SAME anti-leakage discipline as :mod:`aionis.ingest.reddit_sentiment`:

  * **immutable raw archive** (sha256-pinned, one file per ``snapshot_ts``);
  * **append-only cumulative parquet** (concat, NEVER overwrite — priors
    preserved; a re-freeze of the SAME ``snapshot_ts`` dedups so the sealed
    snapshot is byte-stable across idempotent re-runs);
  * one **``data_ingest`` ledger row** carrying ``forward_only: true`` +
    ``snapshot_ts`` (idempotent: a re-freeze does not append a duplicate); and
  * the **I3 monotonic-forward clock**: ``event_ts <= snapshot_ts`` for every
    emitted row, asserted as a hard post-filter gate (a violation means the
    collector admitted lookahead into ``I_t`` -> RAISE, never silently drop).

This module holds ONLY the shared mechanism; each collector owns its own feature
shape + source fetch. Reuses the ledger-append MECHANISM of
:mod:`aionis.ingest.reddit_sentiment._append_ingest_ledger` /
:func:`aionis.reporting.run_log.log_run` (one JSON line, UTC ``ts`` at second
precision, never overwrite) — ``log_run`` is Phase-A-shaped (``{config, results,
notes}``) and cannot carry the forward ``data_ingest`` schema, so we reuse its
atomic-append mechanism, not its body.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import structlog

from aionis.config import settings

log = structlog.get_logger()


# ---------------------------------------------------------------------------
# paths + timestamps
# ---------------------------------------------------------------------------


def cache_dir(cache_dir: Path | None = None) -> Path:
    """Resolve (and create) the forward-ingest cache dir.

    Defaults to ``settings.data_dir / "cache"`` — the same cache root as
    :mod:`aionis.ingest.stakes_13d` / :mod:`aionis.ingest.fundamentals`, so a
    forward collector reuses the same cached ``submissions_*.json`` /
    ``alfred_*.json`` files (a cache hit makes no HTTP call).
    """
    d = cache_dir or settings.data_dir / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def ledger_path(runs_dir: Path | str | None = None) -> Path:
    """The append-only ledger path under ``runs_dir`` (defaults to project runs)."""
    root = Path(runs_dir) if runs_dir is not None else settings.runs_dir
    return root / "ledger.jsonl"


def to_utc_dt(ts: str | datetime) -> datetime:
    """Parse an ISO string or normalize a datetime to a tz-aware UTC datetime.

    Date-only strings (e.g. an EDGAR ``filingDate`` of ``2024-03-15``) parse to
    midnight UTC, which is the PIT-correct knowability boundary for a filed-date
    event (a filing dated ``d`` is knowable at any ``snapshot_ts >= d 00:00 UTC``).
    Naive datetimes are assumed UTC per project convention.
    """
    dt = datetime.fromisoformat(ts) if isinstance(ts, str) else ts
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def snapshot_ts_now() -> str:
    """Canonical UTC ISO timestamp at second precision — the live FREEZE key."""
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")


def canonical_snapshot_ts(snapshot_ts: str | datetime | None = None) -> str:
    """Canonicalize a caller-supplied ``snapshot_ts`` to UTC ISO (seconds).

    ``None`` resolves to NOW. Canonicalizing means a re-freeze spelled
    ``2024-03-31T20:00:00+00:00`` vs ``2024-03-31T20:00:00Z`` collapses to ONE
    key, so the sealed raw-archive filename and the ledger ``snapshot_ts``
    cannot diverge on timestamp FORMAT alone (mirrors
    :func:`aionis.reporting.forward_ledger._canonical_ts`).
    """
    if snapshot_ts is None:
        return snapshot_ts_now()
    return to_utc_dt(snapshot_ts).isoformat(timespec="seconds")


def compact_snapshot_ts(snapshot_ts: str) -> str:
    """Filesystem-safe compact form of a canonical ``snapshot_ts`` for filenames."""
    return re.sub(r"[^0-9A-Za-z]", "", str(snapshot_ts)) or "unknown"


# ---------------------------------------------------------------------------
# immutable raw archive (sha256-pinned)
# ---------------------------------------------------------------------------


def sha256_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def archive_raw(
    cache_dir: Path,
    dataset: str,
    snapshot_ts: str,
    payload: list | dict,
) -> tuple[Path, str]:
    """Write the immutable raw pull for ``(dataset, snapshot_ts)`` and sha256-pin it.

    Sealed per ``snapshot_ts``: a re-freeze of the SAME ``snapshot_ts`` finds the
    prior raw file present and returns its ``(path, sha256)`` WITHOUT rewriting,
    so the raw archive is bit-stable across idempotent re-runs (I3 / H6). A later
    ``snapshot_ts`` writes a NEW raw file (priors preserved). Mirrors the
    immutable-archive discipline of
    :func:`aionis.ingest.reddit_sentiment` (``data/cache/<dataset>_raw_<ts>.json``).
    """
    raw_path = cache_dir / f"{dataset}_raw_{compact_snapshot_ts(snapshot_ts)}.json"
    if raw_path.exists():
        digest = sha256_bytes(raw_path)
        log.info("forward_raw_sealed", dataset=dataset, path=str(raw_path), sha256=digest)
        return raw_path, digest
    raw_path.write_text(json.dumps(payload, ensure_ascii=False, default=str))
    digest = sha256_bytes(raw_path)
    log.info("forward_raw_archived", dataset=dataset, path=str(raw_path), sha256=digest)
    return raw_path, digest


# ---------------------------------------------------------------------------
# cumulative parquet (append-only, dedup, never overwrite)
# ---------------------------------------------------------------------------


def append_cumulative_parquet(path: Path, new_rows: pd.DataFrame) -> pd.DataFrame:
    """Concat ``new_rows`` onto the cumulative parquet, dedup, NEVER overwrite.

    Dedup key = the FULL row (all columns). A re-freeze of the same
    ``snapshot_ts`` re-emits byte-identical rows that collapse back to one copy,
    so the cumulative frame is stable across idempotent re-runs (H6). A later
    ``snapshot_ts`` contributes genuinely new rows (``snapshot_ts`` differs) and
    priors are preserved (I3 forward-only, no backfill, no overwrite).

    An empty ``new_rows`` never creates an empty parquet and never disturbs an
    existing cumulative file (a freeze with zero new events is still a valid,
    ledger-recorded freeze — it just adds no data rows).
    """
    if new_rows.empty:
        if path.exists():
            return pd.read_parquet(path)
        return new_rows
    if path.exists():
        prior = pd.read_parquet(path)
        combined = pd.concat([prior, new_rows], ignore_index=True)
    else:
        combined = new_rows.copy()
    combined = combined.drop_duplicates(keep="first").reset_index(drop=True)
    combined.to_parquet(path, index=False)
    return combined


# ---------------------------------------------------------------------------
# data_ingest ledger row (forward_only: true + snapshot_ts, idempotent)
# ---------------------------------------------------------------------------


def _existing_ingest_rows(runs_dir: Path | str | None) -> list[dict]:
    ledger = ledger_path(runs_dir)
    if not ledger.exists():
        return []
    out: list[dict] = []
    for line in ledger.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue  # defensive: a malformed line must not abort a freeze
        if r.get("event") == "data_ingest":
            out.append(r)
    return out


def append_data_ingest_ledger(
    runs_dir: Path | str | None,
    *,
    dataset: str,
    snapshot_ts: str,
    data_sha256: str,
    source: str,
    license: str,
    **extra: object,
) -> dict | None:
    """Append one ``data_ingest`` row with ``forward_only: true`` + ``snapshot_ts``.

    Idempotent: if a ``data_ingest`` row already exists for
    ``(dataset, snapshot_ts)`` with the SAME ``data_sha256``, NO duplicate is
    appended (a re-freeze of a sealed snapshot is a ledger no-op). A later
    ``snapshot_ts`` or a different sha256 (the underlying source changed) appends
    a new row. Returns the appended row dict, or ``None`` if skipped as
    idempotent.
    """
    for r in _existing_ingest_rows(runs_dir):
        if (
            r.get("dataset") == dataset
            and r.get("snapshot_ts") == snapshot_ts
            and r.get("data_sha256") == data_sha256
        ):
            log.info("forward_ingest_idempotent", dataset=dataset, snapshot_ts=snapshot_ts)
            return None
    row = {
        "ts": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
        "event": "data_ingest",
        "dataset": dataset,
        "source": source,
        "license": license,
        "mode": "exploratory",
        "forward_only": True,
        "snapshot_ts": snapshot_ts,
        "data_sha256": data_sha256,
        **extra,
    }
    ledger = ledger_path(runs_dir)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, default=str) + "\n")
    log.info(
        "forward_ingest_logged", dataset=dataset, snapshot_ts=snapshot_ts, ledger=str(ledger),
    )
    return row


# ---------------------------------------------------------------------------
# shared forward-collector persist tail (archive + cumulative + ledger)
# ---------------------------------------------------------------------------


def persist_snapshot(
    cdir: Path,
    runs_dir: Path | str | None,
    *,
    dataset: str,
    snapshot_ts: str,
    raw_payload: dict,
    frame: pd.DataFrame,
    source: str,
    license: str,
    extra_ledger_fields: dict[str, object] | None = None,
) -> tuple[Path, str]:
    """Shared forward-collector tail: archive raw + append cumulative + ledger row.

    DRYs the identical archive→cumulative→ledger sequence used by the three
    forward collectors (13D / macro / 8-K). Returns ``(raw_path, digest)`` so the
    caller may log them. ``extra_ledger_fields`` carries per-collector specifics
    (e.g. ``n_tickers`` / ``series``); ``n_rows`` is appended LAST to preserve the
    original per-collector ledger key order (byte-identical ledger output, H6).
    """
    raw_path, digest = archive_raw(cdir, dataset, snapshot_ts, raw_payload)
    cumulative = cdir / f"{dataset}.parquet"
    append_cumulative_parquet(cumulative, frame)
    extra: dict[str, object] = dict(extra_ledger_fields or {})
    extra["n_rows"] = int(len(frame))
    append_data_ingest_ledger(
        runs_dir,
        dataset=dataset,
        snapshot_ts=snapshot_ts,
        data_sha256=digest,
        source=source,
        license=license,
        **extra,
    )
    return raw_path, digest


# ---------------------------------------------------------------------------
# I3 leakage gate — the monotonic-forward clock
# ---------------------------------------------------------------------------


def assert_forward_clock(
    df: pd.DataFrame, event_ts_col: str, snapshot_ts: str
) -> None:
    """I3 leakage gate: every row's ``event_ts_col`` value must be ``<= snapshot_ts``.

    Called by each collector AFTER its forward filter, as a defensive
    post-condition. A violation means the filter admitted a not-yet-released
    event into ``I_t`` (lookahead) — this is a leakage bug, so we RAISE rather
    than silently drop. A missing/NaT ``event_ts`` is ALSO a violation: an event
    with no knowable timestamp cannot be PIT-anchored and must not enter the
    snapshot. An empty frame trivially passes.

    This is the Slice 2 acceptance gate (plan §2 I3): the test suite seeds
    future-dated fixtures and asserts (a) the filter excludes them and (b) this
    gate raises on any that slip through.
    """
    if df.empty:
        return
    snap = to_utc_dt(snapshot_ts)
    ev = pd.to_datetime(df[event_ts_col], utc=True, errors="coerce")
    bad_mask = ev.isna() | (ev > snap)
    if bad_mask.any():
        n_bad = int(bad_mask.sum())
        violators = df.loc[bad_mask, [event_ts_col]].head(5).to_dict("records")
        raise RuntimeError(
            f"I3 forward-clock violation: {n_bad} row(s) with event_ts > "
            f"snapshot_ts={snap.isoformat()} (lookahead admitted to I_t). "
            f"First violators: {violators}"
        )


__all__ = [
    "cache_dir",
    "ledger_path",
    "to_utc_dt",
    "snapshot_ts_now",
    "canonical_snapshot_ts",
    "compact_snapshot_ts",
    "sha256_bytes",
    "archive_raw",
    "append_cumulative_parquet",
    "append_data_ingest_ledger",
    "persist_snapshot",
    "assert_forward_clock",
]
