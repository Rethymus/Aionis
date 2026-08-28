"""Bounded daily fetch of recent SC 13D stakes via the EDGAR crawler index.

Unfreezes the smart-money panel past the 2024-12-17 EFTS cutoff (see memory
``aionis-edgar-efts-sc13d-frozen``). The EDGAR daily crawler index is the
current dissemination feed; one fetch per business day yields every SC 13D
filed that day. Writes ``data/cache/sc13d_daily_aggregate.json`` (gitignored,
regenerable); ``scripts/export_terminal_data.py`` merges it with the EFTS
historical cache into the tracked web payload.

Default window: from the EFTS freeze (2024-12-17) to today — covers the full
gap (2025 + 2026) so the daily cron never regresses 2025 by using too-narrow a
window. Idempotent + resumable via ``data/cache/sc13d_daily_checkpoint.json``
(one entry per parsed day: sha256 fingerprint of the raw day index + rows):
each day is persisted the moment it is parsed, so a killed walk (timeout/CI
cap) loses no progress — a rerun reuses every cached day with ZERO re-parsing
and ZERO requests and only computes the missing days. Cached rows are trusted
only while the locally cached raw day index still hashes to the stored
fingerprint (disk-only check — covers the current-day dissemination window
where the index can still grow). The final aggregate is byte-identical to the
checkpoint-free path; the sidecar is intermediate state only (gitignored,
regenerable).

Polite: one GET per business day (≥2s via ``_policy_get``) — checkpoint hits
make no requests at all. Display-only, exploratory, filed-date PIT. SEC
public domain. NOT a research claim.

Usage::

    uv run python scripts/stakes_13d_daily_fetch.py              # freeze -> today
    uv run python scripts/stakes_13d_daily_fetch.py --start 2025-01-01
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path

from aionis.ingest.stakes_13d_daily_index import (
    fetch_recent_13d_daily,
    load_checkpoint,
)

OUT = Path("data/cache/sc13d_daily_aggregate.json")
# The EFTS SC 13D index froze on 2024-12-17 — backfill from there so 2025 is covered.
_DEFAULT_START = date(2024, 12, 17)


def _parse_start(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--start",
        type=_parse_start,
        default=_DEFAULT_START,
        help="window start (default: 2024-12-17, the EFTS SC 13D freeze date)",
    )
    args = ap.parse_args()

    end = date.today()
    start = args.start
    span = (end - start).days
    print(f"[13d-daily] window {start} .. {end} ({span} calendar days)", flush=True)
    print(
        f"[13d-daily] checkpoint: {len(load_checkpoint())} day(s) already "
        "parsed (reused on this run — zero re-parse, zero request)",
        flush=True,
    )

    rows = fetch_recent_13d_daily(start, end)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, indent=2))
    print(f"[13d-daily] wrote {len(rows)} SC 13D rows to {OUT}", flush=True)
    if rows:
        by_year: dict[str, int] = {}
        for r in rows:
            by_year[r["date"][:4]] = by_year.get(r["date"][:4], 0) + 1
        print(f"[13d-daily] by year: {dict(sorted(by_year.items()))}", flush=True)
        print(f"[13d-daily] latest: {rows[0]['date']}  {rows[0]['target'][:40]}", flush=True)


if __name__ == "__main__":
    main()

