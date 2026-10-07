"""Data-snapshot audit — make the no-revision contract VERIFIABLE (v0, exploratory).

Why
---
Schwarz, Walter & Weiss (JFQA, 2026-03) documented that CRSP silently replaced
its stock tape in 2025-01 and published backtests stopped reproducing on the
revised data. Aionis's own no-revision contract (VIX unrevised, ALFRED
first-print immutability, EDGAR filed-date stability) currently rests on
TRUST in the upstream sources. This script turns it into a CHECK:

- **baseline mode** records, per tracked research-history cache, the row
  count, max row date, full-file sha256, and — the load-bearing part — the
  sha256 of the *historical prefix* (all rows dated <= baseline max date,
  deterministically sorted and re-serialized);
- **audit mode** (any later run) recomputes and classifies each file:
  prefix hash unchanged -> OK (appended rows are tolerated and reported);
  prefix hash changed -> **HISTORY REWRITTEN** (the CRSP alarm); fewer rows
  or lower max date -> TRUNCATED. Exit code 1 on any alarm.

Bounds and honesty
------------------
- EXPLORATORY diagnostic (ledger row on baseline creation); NOT wired into
  the nightly lane or any gate — that integration is owner-gated by design.
- Prefix hashing re-serializes through the pinned pandas/pyarrow stack
  (uv.lock) — hashes are comparable only within the pinned environment.
- Covers the RESEARCH history caches; display-only aggregates are out of
  scope (they legitimately rewrite).

Usage::

    uv run python scripts/data_snapshot_audit.py             # baseline or audit
    uv run python scripts/data_snapshot_audit.py --baseline  # force re-baseline
    SNAP_NO_LEDGER=1 uv run python scripts/data_snapshot_audit.py
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "cache"
BASELINE = ROOT / "reports" / "exploratory" / "data-snapshot-baseline.json"
LEDGER = ROOT / "runs" / "ledger.jsonl"

# Research-history caches (display-only aggregates deliberately excluded).
# date_col None -> full-hash-only (no append tolerance; static maps).
TRACKED: list[dict] = [
    {"name": "phase_b_fundamentals", "date_col": "filed", "kind": "parquet"},
    {"name": "phase_d_13d_events", "date_col": "filing_date", "kind": "parquet"},
    {"name": "phase_d_sic_map", "date_col": None, "kind": "parquet"},
    {"name": "cot_aggregate", "date_col": "date", "kind": "parquet"},
    {"name": "earnings_8k_forward", "date_col": "filing_date", "kind": "parquet"},
    {"name": "form8k_aggregate", "date_col": "filing_date", "kind": "parquet"},
    {"name": "ashare_prices_csi300", "date_col": "date", "kind": "parquet"},
    {"name": "gdelt_news_sentiment", "date_col": None, "kind": "json"},
]


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _parquet_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    return buf.getvalue()


def _snapshot_one(spec: dict) -> dict:
    if spec["kind"] == "json":
        raw = (CACHE / f"{spec['name']}.json").read_bytes()
        rec = {
            "name": spec["name"], "n_rows": None, "max_date": None,
            "sha_full": _sha(raw),
            "sha_prefix": None,
            "note": "full-hash only (dict-shaped source)",
        }
        # record GDELT coverage window for human context
        try:
            d = json.loads(raw)
            rec["coverage"] = [d.get("coverage_start"), d.get("coverage_end")]
        except Exception:
            pass
        return rec

    df = pd.read_parquet(CACHE / f"{spec['name']}.parquet")
    rec: dict = {
        "name": spec["name"], "n_rows": int(len(df)),
        "max_date": None, "sha_full": None, "sha_prefix": None,
    }
    full = df.copy()
    if spec["date_col"] is not None:
        dc = spec["date_col"]
        full = full.sort_values(dc, kind="mergesort")
        rec["max_date"] = str(full[dc].max())
        rec["sha_prefix"] = _sha(_parquet_bytes(full))
    else:
        full = full.sort_values(list(full.columns), kind="mergesort")
        rec["note"] = "static map — full-hash only"
    rec["sha_full"] = _sha(_parquet_bytes(full))
    return rec


def _prefix_now(spec: dict, max_date: str) -> str | None:
    """Hash today's rows dated <= the baseline's max date (None -> n/a)."""
    if spec["date_col"] is None or spec["kind"] != "parquet":
        return None
    df = pd.read_parquet(CACHE / f"{spec['name']}.parquet")
    dc = spec["date_col"]
    df = df[df[dc] <= max_date].sort_values(dc, kind="mergesort")
    return _sha(_parquet_bytes(df))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--baseline", action="store_true",
                        help="force (re-)create the baseline snapshot")
    args = parser.parse_args()

    if args.baseline or not BASELINE.exists():
        snaps = [_snapshot_one(s) for s in TRACKED]
        payload = {
            "as_of": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "kind": "data-snapshot-baseline",
            "exploratory": True,
            "caveats": [
                "prefix hashes are comparable only within the pinned "
                "pandas/pyarrow environment (uv.lock)",
                "append-tolerant history check; display-only aggregates out "
                "of scope",
                "NOT wired into any gate — owner-gated integration",
            ],
            "files": snaps,
        }
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                            encoding="utf-8")
        print(f"[snapshot] BASELINE written: {len(snaps)} files -> {BASELINE}")
        for s in snaps:
            print(f"  {s['name']:28s} rows={s['n_rows']} max={s['max_date']}")
        if not os.environ.get("SNAP_NO_LEDGER"):
            entry = {
                "ts": payload["as_of"],
                "event": "exploratory",
                "phase": "data_snapshot_baseline",
                "n_files": len(snaps),
                "notes": (
                    "Baseline content hashes of the research-history caches "
                    "(prefix = rows <= baseline max date). Rerun "
                    "scripts/data_snapshot_audit.py to verify no upstream "
                    "history rewrite (CRSP-tape lesson, JFQA 2026-03). "
                    "EXPLORATORY; not a gate."
                ),
            }
            with open(LEDGER, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
            print(f"[snapshot] appended exploratory row to {LEDGER}")
        return 0

    # audit mode
    base = json.loads(BASELINE.read_text(encoding="utf-8"))
    base_by = {b["name"]: b for b in base["files"]}
    alarms: list[str] = []
    lines: list[str] = []
    for spec in TRACKED:
        name = spec["name"]
        b = base_by.get(name)
        if b is None:
            lines.append(f"  {name:28s} NEW (not in baseline)")
            continue
        today = _snapshot_one(spec)
        if (b.get("n_rows") is not None and today["n_rows"] is not None
                and today["n_rows"] < b["n_rows"]):
            alarms.append(f"{name}: TRUNCATED {b['n_rows']} -> {today['n_rows']} rows")
            lines.append(f"  {name:28s} TRUNCATED  rows {b['n_rows']} -> {today['n_rows']}")
            continue
        prefix = _prefix_now(spec, b["max_date"]) if b.get("max_date") else None
        if b.get("sha_prefix") and prefix and prefix != b["sha_prefix"]:
            alarms.append(f"{name}: HISTORY REWRITTEN (prefix sha changed "
                          f"for rows <= {b['max_date']})")
            lines.append(f"  {name:28s} HISTORY REWRITTEN (<= {b['max_date']})")
        else:
            appended = (today.get("n_rows") or 0) - (b.get("n_rows") or 0)
            app_note = f" (+{appended} appended)" if appended > 0 else ""
            lines.append(f"  {name:28s} OK{app_note}")
    print(f"[snapshot] audit vs baseline {base['as_of']}:")
    print("\n".join(lines))
    if alarms:
        print("[snapshot] ALARMS:", file=sys.stderr)
        for a in alarms:
            print(f"  - {a}", file=sys.stderr)
        return 1
    print("[snapshot] no history rewrite detected (appends tolerated)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
