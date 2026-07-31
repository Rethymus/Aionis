"""E3 Slice 4d - forward results writer.

Mirrors the pattern of ``reporting.results.save_run`` for forward IC artifacts.
Writes forward results under ``runs/forward/<config_sig>/`` (I9: never touches
``runs/results/`` which holds published nulls).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import structlog

from aionis.reporting.results import DEFAULT_RUNS_DIR, _project_version

log = structlog.get_logger()

_IC_COL = "ic"  # parquet column name for the IC series (matches results.py)


def _forward_root(runs_dir: Path | str | None = None) -> Path:
    """Return the forward artifact root: ``<runs>/forward/``."""
    if runs_dir is not None:
        return Path(runs_dir) / "forward"
    return DEFAULT_RUNS_DIR / "forward"


def _forward_dir(config_sig: str, runs_dir: Path | str | None = None) -> Path:
    """Per-config forward artifact directory ``<runs>/forward/<config_sig>/``."""
    if not config_sig or not isinstance(config_sig, str):
        raise ValueError(f"config_sig must be a non-empty string, got {config_sig!r}.")
    # sanitize: keep it filesystem-safe (config sigs are hex hashes, but be defensive)
    safe = "".join(c for c in config_sig if c.isalnum() or c in "-_") or "unknown"
    return _forward_root(runs_dir) / safe


def _write_json(path: Path, obj: object) -> None:
    """Write JSON atomically (mirrors results.py helper)."""
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _write_ic(path: Path, ic: pd.Series) -> None:
    """Persist an IC series as parquet (mirrors results.py helper)."""
    if not isinstance(ic, pd.Series):
        raise TypeError(f"ic must be a pandas Series, got {type(ic).__name__}.")
    frame = ic.rename(_IC_COL).to_frame()
    # keep the index name round-trippable
    if frame.index.name is None:
        frame.index.name = "date"
    frame.to_parquet(path)


def save_forward_run(
    config_sig: str,
    *,
    ic_forward: pd.Series,
    summary: dict,
    config: dict,
    runs_dir: Path | str | None = None,
    h6_deterministic: bool = True,
) -> Path:
    """Persist ONE forward run to ``runs/forward/<config_sig>/`` and return that dir.

    Args:
        config_sig: the frozen-config signature (matches ledger rows).
        ic_forward: monthly differential IC series (e13 - base), output of
            ``accumulate_forward_ic_series``.
        summary: rank_ic_summary dict for the differential (mean_diff, ci_half, dm_*, ...).
        config: the frozen config that produced this forward run.
        runs_dir: override the ``runs`` dir (hermetic tests).
        h6_deterministic: the E3 determinism flag (bit-identical re-run).

    The artifacts written are:
        * ``ic_forward.parquet`` — the differential IC series (index=month).
        * ``summary_forward.json`` — the summary dict (inference + CI).
        * ``config.json`` — the frozen config.
        * ``meta.json`` — ts, config_sig, h6_deterministic, aionis_version, schema=2, phase=E3.

    Mirrors ``save_run``'s atomic-write pattern: directory created with
    ``exist_ok=True``, files written atomically, overwrites existing artifacts
    with the same config_sig (idempotent re-save).

    I9: forward artifacts live ONLY under ``runs/forward/``; the published-null
    dirs ``runs/results/<sig>/`` are never touched.
    """
    d = _forward_dir(config_sig, runs_dir)
    d.mkdir(parents=True, exist_ok=True)

    # Write core artifacts
    _write_ic(d / "ic_forward.parquet", ic_forward)
    _write_json(d / "summary_forward.json", summary)
    _write_json(d / "config.json", config)

    # Write meta.json LAST (after all data files)
    _write_json(
        d / "meta.json",
        {
            "ts": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
            "config_sig": config_sig,
            "h6_deterministic": bool(h6_deterministic),
            "aionis_version": _project_version(),
            "schema": 2,
            "phase": "E3",
        },
    )

    log.info(
        "forward_results_saved",
        config_sig=config_sig,
        n_ic_forward=len(ic_forward),
        dir=str(d),
    )

    return d


__all__ = ["save_forward_run"]
