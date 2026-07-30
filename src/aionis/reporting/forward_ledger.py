"""E3 forward-ledger commit-reveal core (Slice 1 - the keystone).

Extends the project's "sha256-before-result" anti-leakage anchor from PER-RUN
granularity (``scripts/phase_b_run.py`` ``config_committed`` BEFORE any OOS metric)
to PER-PREDICTION granularity: every forward prediction is sha256-sealed in the
append-only ledger BEFORE its t+21 outcome can realize, and the reveal is gated on
both (a) a prior commit for that prediction and (b) wall-clock >= target_t.

Reuses, does not reinvent:
  * the append-only ledger ``runs/ledger.jsonl`` (heterogeneous; forward rows carry
    ``phase:"E3"`` + ``event:"forward_*"``) - same atomic-append pattern as
    ``ingest/reddit_sentiment._append_ingest_ledger`` / ``reporting.run_log.log_run``.
  * the per-run artifact-dir layout of ``reporting.results.save_run`` - mirrored to
    ``runs/forward/<config_sha256>/scores_<predict_ts>.parquet``.

sha256 serialization choices (load-bearing for I2/I7 - documented, not incidental):
  * ``config_sha256`` = ``sha256(json.dumps(config, sort_keys=True, default=str))``
    (full 64 hex chars) - matches ``scripts/phase_b_run.commit_config`` and the
    ``confirmatory:first`` convention. This IS the durable forward-sequence key
    (I8: changing the config -> new hash -> new sequence).
  * ``scores_sha256`` = ``sha256(<committed parquet file bytes>)`` - matches
    ``ingest.reddit_sentiment._sha256`` / ``scripts.phase_b_run._sha``. We hash the
    ARTIFACT BYTES (not a parallel serialization) so the commitment is auditable:
    anyone can later re-read the parquet and verify ``sha256(bytes) ==
    scores_sha256`` in the ledger. Reproducibility (I7) rests on (i) the version-
    pinned env (``uv.lock`` - the same foundation H6 bit-identical parquet already
    relies on in ``reporting.results.save_run``) and (ii) a deterministic write
    (ticker+arm sort, ``index=False``, float64 score coercion) so identical inputs
    produce byte-identical parquet -> identical hash. Mutation (I2) flips bytes ->
    flips the hash and is detected at re-commit.

Slice 1 scope ONLY: commit / reveal / read primitives. No fit, no ingest, no
scheduler, no scoring loop, no dashboard. See ``docs/phase-e3-implementation-plan.md``
§4 Slice 1 and ``docs/phase-e3-preregistration.md`` §9.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import structlog

from aionis.reporting.results import DEFAULT_RUNS_DIR, read_ledger

log = structlog.get_logger()

PHASE = "E3"
EVENT_COMMIT = "forward_prediction_committed"
EVENT_SCORED = "forward_outcome_scored"

_SCORE_COLS = ("ticker", "arm", "score")  # committed per-ticker score-panel schema


# ---------------------------------------------------------------------------
# identifiers + paths
# ---------------------------------------------------------------------------


def config_sha256(config: dict) -> str:
    """Full 64-char sha256 of the frozen config (the durable forward-sequence key).

    Changing ANY config field (incl. provider / causal schema / broadcast weights)
    yields a different hash -> a new forward sequence (I8). Mirrors
    ``scripts/phase_b_run.commit_config`` with ONE divergence: this uses
    ``json.dumps(..., default=str)`` (not the bare ``sort_keys=True`` form) so
    non-JSON-native config values (Paths, datetimes, sets) serialize deterministically
    instead of raising ``TypeError``. This does NOT affect comparability: E3 never
    cross-compares its config hash against a Phase B ``config_sig`` - the two phases
    hash structurally different configs over disjoint schemas, and I9 keeps the
    forward and confirmatory ledgers strictly separate. The hash is only ever
    compared to OTHER E3 forward hashes (same ``default=str`` canonicalization).
    """
    blob = json.dumps(config, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()


def _compact_ts(predict_ts: str) -> str:
    """Filesystem-safe compact form of a CANONICAL ``predict_ts`` for the parquet name.

    Operates on the ``_canonical_ts`` form, so e.g. canonical
    ``2026-07-31T20:00:00+00:00`` -> ``20260731T2000000000``. Because the input is
    already canonicalized, two originally-differently-spelled timestamps cannot
    collapse to the same compact form unless they denote the same instant. The full
    canonical value is always retained in the ledger row's ``predict_ts`` field.
    """
    return re.sub(r"[^0-9A-Za-z]", "", str(predict_ts)) or "unknown"


def _canonical_ts(ts: str | datetime) -> str:
    """Canonical ISO-8601 UTC key for a predict_ts / target_t (timespec=seconds).

    Parsing to UTC and re-emitting one canonical form means ``2026-07-31T20:00:00+00:00``,
    ``2026-07-31T20:00:00+0000``, and the ``Z`` form all collapse to the SAME key -
    so the parquet path key (derived via ``_compact_ts``) and the ledger row's
    ``predict_ts``/``target_t`` cannot diverge on timestamp FORMAT alone. Without
    this, ``+00:00`` vs ``+0000`` would strip to different compact strings yet parse
    to the same instant, risking a spurious path collision or a false
    mutation-refusal across equivalent spellings. Slice 3 still mints ``predict_ts``
    from ``pandas_market_calendars``; canonicalizing here is defensive
    belt-and-suspenders at the keystone boundary.
    """
    return _to_utc_dt(ts).isoformat(timespec="seconds")


def _forward_root(runs_dir: Path | str | None) -> Path:
    root = Path(runs_dir) if runs_dir is not None else DEFAULT_RUNS_DIR
    return root / "forward"


def _scores_path(
    config_sha: str, predict_ts: str, runs_dir: Path | str | None = None
) -> Path:
    """Per-prediction immutable artifact: ``<runs>/forward/<csha>/scores_<ts>.parquet``."""
    return _forward_root(runs_dir) / config_sha / f"scores_{_compact_ts(predict_ts)}.parquet"


def _ledger_path(runs_dir: Path | str | None) -> Path:
    root = Path(runs_dir) if runs_dir is not None else DEFAULT_RUNS_DIR
    return root / "ledger.jsonl"


# ---------------------------------------------------------------------------
# scores parquet - deterministic write + hash
# ---------------------------------------------------------------------------


def _normalize_scores(scores: pd.DataFrame) -> pd.DataFrame:
    """Validate + deterministically order the per-ticker score panel.

    Required columns: ``ticker``, ``arm``, ``score`` (the two-arm long shape; one
    row per ticker per arm). Sorted by (ticker, arm) with a reset index so two
    commits of the same logical panel produce byte-identical parquet (I7).
    """
    if not isinstance(scores, pd.DataFrame):
        raise TypeError(
            f"scores must be a pandas DataFrame [{_SCORE_COLS}], got {type(scores).__name__}."
        )
    missing = [c for c in _SCORE_COLS if c not in scores.columns]
    if missing:
        raise ValueError(f"scores is missing required column(s) {missing}; need {_SCORE_COLS}.")
    if len(scores) == 0:
        raise ValueError("scores is empty; a forward prediction requires >=1 ticker.")
    norm = scores[list(_SCORE_COLS)].copy()
    norm["score"] = pd.to_numeric(norm["score"], errors="raise").astype("float64")
    # stable sort by (ticker, arm); reset index; drop it from the parquet payload.
    return norm.sort_values(["ticker", "arm"], kind="mergesort").reset_index(drop=True)


def _sha256_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _now_iso(now: datetime | str | None = None) -> datetime:
    if now is None:
        return datetime.now(tz=timezone.utc)
    if isinstance(now, str):
        return _to_utc_dt(now)
    return now


def _to_utc_dt(x: datetime | str) -> datetime:
    """Parse an ISO string or normalize a datetime to a tz-aware UTC datetime."""
    if isinstance(x, str):
        dt = datetime.fromisoformat(x)
    else:
        dt = x
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)  # assume UTC (project convention)
    return dt.astimezone(timezone.utc)


def _append_ledger_row(runs_dir: Path | str | None, row: dict) -> dict:
    """Append one event-typed JSON line to ``<runs>/ledger.jsonl`` (UTC ``ts``).

    Mirrors ``ingest.reddit_sentiment._append_ingest_ledger`` / ``run_log.log_run``:
    one JSON line, ``ts`` at second precision, never overwrite. ``log_run`` itself
    is Phase-A-shaped (``{config, results, notes}``) and cannot carry the event-
    typed forward schema, so we reuse its atomic-append MECHANISM, not its body.
    """
    ledger = _ledger_path(runs_dir)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
        **row,
    }
    with ledger.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")
    # NOTE: structlog reserves ``event`` for the message name, so the row's event
    # type is logged under ``row_event`` to avoid a kwarg collision.
    log.info(
        "forward_ledger_appended",
        ledger=str(ledger),
        row_event=row.get("event"),
        config_sha256=row.get("config_sha256"),
    )
    return record


# ---------------------------------------------------------------------------
# public API - commit / reveal / read
# ---------------------------------------------------------------------------


def commit_forward_prediction(
    predict_ts: str,
    target_t: str,
    scores: pd.DataFrame,
    config: dict,
    iset_sha256: str,
    provider: str,
    provider_cutoff: str,
    *,
    runs_dir: Path | str | None = None,
    mode: str = "exploratory",
) -> dict:
    """Seal one forward prediction: write the immutable scores parquet + append the
    ``forward_prediction_committed`` ledger row (pre-reg §9).

    I2 immutability guard:
      * if the parquet for ``(config_sha256, predict_ts)`` already exists with
        IDENTICAL bytes -> idempotent (H6): return the commit fields WITHOUT
        rewriting or appending a duplicate row.
      * if it exists with DIFFERENT bytes -> mutation of a sealed prediction is
        refused (``committed: False``); the original artifact is left untouched and
        no commit row is appended.

    Returns the commit row dict (``committed: True``) or a refused-result dict
    (``committed: False`` + ``reason``).
    """
    # canonicalize the timestamp keys FIRST so the parquet path key and the ledger
    # row's predict_ts/target_t share one ISO form (no format-driven collision).
    predict_ts = _canonical_ts(predict_ts)
    target_t = _canonical_ts(target_t)
    csha = config_sha256(config)
    norm = _normalize_scores(scores)
    path = _scores_path(csha, predict_ts, runs_dir)
    rel_path = f"forward/{csha}/{path.name}"

    # serialize once to a stable byte image (do NOT touch the sealed file yet)
    tmp_bytes = _deterministic_parquet_bytes(norm)
    new_sha = hashlib.sha256(tmp_bytes).hexdigest()

    if path.exists():
        existing_sha = _sha256_bytes(path)
        if existing_sha == new_sha:
            # idempotent re-commit (H6): same scores -> no rewrite, no dup row
            log.info(
                "forward_commit_idempotent",
                config_sha256=csha, predict_ts=predict_ts, scores_sha256=new_sha,
            )
            row = _commit_row(
                predict_ts, target_t, csha, iset_sha256, new_sha, rel_path,
                provider, provider_cutoff, mode,
            )
            return {**row, "committed": True, "_appended": False}
        # MUTATION of a sealed prediction -> refuse, do not overwrite (I2)
        log.warning(
            "forward_commit_mutation_refused",
            config_sha256=csha, predict_ts=predict_ts,
            existing_sha256=existing_sha, tendered_sha256=new_sha,
        )
        return {
            "committed": False,
            "reason": (
                "scores_mutation_detected: a prediction for predict_ts="
                f"{predict_ts} under config_sha256={csha[:12]} is already sealed "
                f"(existing scores_sha256={existing_sha[:12]}); mutating a sealed "
                "prediction is forbidden (I2). Start a new forward sequence "
                "(new config) instead."
            ),
            "predict_ts": predict_ts,
            "target_t": target_t,
            "config_sha256": csha,
            "existing_scores_sha256": existing_sha,
            "tendered_scores_sha256": new_sha,
        }

    # first commit for this (config_sha256, predict_ts): persist artifact + append row
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(tmp_bytes)
    row = _commit_row(
        predict_ts, target_t, csha, iset_sha256, new_sha, rel_path,
        provider, provider_cutoff, mode,
    )
    appended = _append_ledger_row(runs_dir, row)
    return {**appended, "committed": True, "_appended": True}


def _commit_row(
    predict_ts: str,
    target_t: str,
    csha: str,
    iset_sha256: str,
    scores_sha: str,
    rel_path: str,
    provider: str,
    provider_cutoff: str,
    mode: str,
) -> dict:
    """Build the clean ``forward_prediction_committed`` ledger row (pre-reg §9 schema).

    This dict is what gets persisted to ``ledger.jsonl`` - it carries ONLY schema
    fields (no API-return metadata like ``committed``/``_appended``). ``config_sig``
    aliases ``config_sha256`` so existing ``read_ledger`` / ``list_runs``
    reconciliation (which groups by ``config_sig``) also works for forward rows.
    ``scores_path`` is relative to the runs dir (portable, auditable).
    """
    return {
        "event": EVENT_COMMIT,
        "phase": PHASE,
        "mode": mode,
        "predict_ts": predict_ts,
        "target_t": target_t,
        "config_sha256": csha,
        "config_sig": csha,  # compatibility alias (see docstring)
        "iset_sha256": iset_sha256,
        "scores_sha256": scores_sha,
        "scores_path": rel_path,
        "provider": provider,
        "provider_cutoff": provider_cutoff,
    }


def _deterministic_parquet_bytes(df: pd.DataFrame) -> bytes:
    """Serialize ``df`` to deterministic parquet bytes (independent of disk write path).

    Writing to an in-memory buffer via the pyarrow engine yields the same bytes as
    ``path.write_bytes(buffer)`` would, so the file on disk and the hash computed
    pre-write are consistent. Determinism rests on the version-pinned pyarrow (the
    same foundation ``reporting.results.save_run`` relies on for H6).
    """
    buf = io.BytesIO()
    df.to_parquet(buf, index=False, engine="pyarrow")
    return buf.getvalue()


def reveal_forward_outcome(
    target_t: str,
    ic_point: float,
    arm: str,
    *,
    predict_ts: str,
    config_sha256: str,
    runs_dir: Path | str | None = None,
    now: datetime | str | None = None,
    mode: str = "exploratory",
) -> dict:
    """Reveal the realized IC for one committed forward prediction (the I1 leakage gate).

    Appends ``forward_outcome_scored`` ONLY when BOTH hold:
      (a) a ``forward_prediction_committed`` row exists for
          ``(config_sha256, predict_ts)`` with matching ``target_t``; AND
      (b) wall-clock ``now`` >= ``target_t`` (the outcome has realized).

    Idempotent (I2): a second reveal for the same ``(config_sha256, predict_ts,
    arm)`` returns the existing scored row without appending a duplicate.

    Returns the scored row (``revealed: True``) or a refused-result dict
    (``revealed: False`` + ``reason``) distinguishing the two refusal causes.
    """
    # canonicalize so the lookup keys match how commit_forward_prediction stored them
    # (a differently-spelled-but-equivalent timestamp must still find its commit).
    predict_ts = _canonical_ts(predict_ts)
    target_t = _canonical_ts(target_t)
    now_dt = _now_iso(now)
    target_dt = _to_utc_dt(target_t)

    rows = read_forward_rows(runs_dir=runs_dir, config_sha256=config_sha256)
    commit = _find_commit(rows, predict_ts, target_t)

    if commit is None:
        log.warning(
            "forward_reveal_no_commit",
            config_sha256=config_sha256, predict_ts=predict_ts, target_t=target_t,
        )
        return {
            "revealed": False,
            "reason": (
                "no_matching_commit: no forward_prediction_committed row found for "
                f"predict_ts={predict_ts}, target_t={target_t}, "
                f"config_sha256={config_sha256[:12]}. Cannot reveal an unsealed "
                "prediction (I1)."
            ),
            "predict_ts": predict_ts,
            "target_t": target_t,
            "config_sha256": config_sha256,
        }

    if now_dt < target_dt:
        log.warning(
            "forward_reveal_before_target",
            config_sha256=config_sha256, predict_ts=predict_ts,
            target_t=target_t, now=now_dt.isoformat(),
        )
        return {
            "revealed": False,
            "reason": (
                f"before_target_t: wall-clock now={now_dt.isoformat(timespec='seconds')} "
                f"< target_t={target_t}; the forward outcome has not realized yet (I1). "
                "Reveal refused."
            ),
            "predict_ts": predict_ts,
            "target_t": target_t,
            "config_sha256": config_sha256,
        }

    # idempotency: already scored for this (config_sha256, predict_ts, arm)?
    existing = _find_scored(rows, predict_ts, arm)
    if existing is not None:
        log.info(
            "forward_reveal_idempotent",
            config_sha256=config_sha256, predict_ts=predict_ts, arm=arm,
        )
        return {
            "revealed": True,
            "ic_point": existing["ic_point"],
            "predict_ts": predict_ts,
            "target_t": target_t,
            "config_sha256": config_sha256,
            "arm": arm,
            "_appended": False,
        }

    row = {
        "event": EVENT_SCORED,
        "phase": PHASE,
        "mode": mode,
        "predict_ts": predict_ts,
        "target_t": target_t,
        "config_sha256": config_sha256,
        "config_sig": config_sha256,  # compatibility alias
        "arm": arm,
        "ic_point": float(ic_point),
    }
    appended = _append_ledger_row(runs_dir, row)
    return {**appended, "revealed": True, "_appended": True}


# ---------------------------------------------------------------------------
# read / filter
# ---------------------------------------------------------------------------


def read_forward_rows(
    *,
    runs_dir: Path | str | None = None,
    ledger: Path | str | None = None,
    config_sha256: str | None = None,
    event: str | None = None,
) -> list[dict]:
    """Read forward_* rows from the ledger, optionally filtered.

    Reuses ``reporting.results.read_ledger`` (defensive: skips malformed lines,
    handles the heterogeneous ledger). Forward rows are identified by
    ``event.startswith("forward_")`` + ``phase == "E3"``.
    """
    if ledger is None:
        ledger = _ledger_path(runs_dir)
    rows = read_ledger(ledger)
    out: list[dict] = []
    for r in rows:
        ev = r.get("event")
        if not isinstance(ev, str) or not ev.startswith("forward_"):
            continue
        if r.get("phase") != PHASE:
            continue
        if config_sha256 is not None and r.get("config_sha256") != config_sha256:
            continue
        if event is not None and ev != event:
            continue
        out.append(r)
    return out


# ---------------------------------------------------------------------------
# internal lookup helpers
# ---------------------------------------------------------------------------


def _find_commit(rows: list[dict], predict_ts: str, target_t: str) -> dict | None:
    for r in rows:
        if (
            r.get("event") == EVENT_COMMIT
            and r.get("predict_ts") == predict_ts
            and r.get("target_t") == target_t
        ):
            return r
    return None


def _find_scored(rows: list[dict], predict_ts: str, arm: str) -> dict | None:
    for r in rows:
        if (
            r.get("event") == EVENT_SCORED
            and r.get("predict_ts") == predict_ts
            and r.get("arm") == arm
        ):
            return r
    return None


__all__ = [
    "PHASE",
    "EVENT_COMMIT",
    "EVENT_SCORED",
    "config_sha256",
    "commit_forward_prediction",
    "reveal_forward_outcome",
    "read_forward_rows",
]
