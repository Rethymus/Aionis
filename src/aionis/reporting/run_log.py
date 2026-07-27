"""Persistent run ledger — every compared configuration is logged, no silent selection.

Appends one JSON line per comparison to runs/ledger.jsonl. This is the antidote
to the garden-of-forking-paths: the pre-registered primary metric is one row
among many, and every config tried (including nulls) is auditable.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import structlog

log = structlog.get_logger()


def _config_signature(config: dict) -> str:
    blob = json.dumps(config, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()[:12]


def log_run(
    runs_dir: Path,
    config: dict,
    results: list[dict],
    notes: str = "",
) -> Path:
    """Append a run record to the ledger. Returns the ledger path."""
    runs_dir = Path(runs_dir)
    runs_dir.mkdir(parents=True, exist_ok=True)
    ledger = runs_dir / "ledger.jsonl"
    record = {
        "ts": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
        "config_sig": _config_signature(config),
        "config": config,
        "results": results,
        "notes": notes,
    }
    with ledger.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")
    log.info(
        "run_logged", ledger=str(ledger), config_sig=record["config_sig"], n_results=len(results)
    )
    return ledger
