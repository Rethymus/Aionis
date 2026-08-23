"""Fetch BTS Freight TSI + FRED truck-employment auxiliary into data/cache.

Thin runner over ``aionis.ingest.bts_tsi`` (parsers live there so the
exporter reuses them — cache and tracked JSON can never disagree on row
semantics). TWO polite GETs per run (one per host, ≥2.1s apart; per-host
serialization is additionally enforced by ``HttpRequestPolicy``):

  1. data.bts.gov Socrata  — full monthly Freight TSI history (bw6n-ddqk,
     first-party BTS, public domain) → ``data/cache/bts_tsi_freight.json``
  2. api.stlouisfed.org    — BLS CES truck-transportation employment
     (CES4348400001) → ``data/cache/alfred_CES4348400001.json`` (vix.py
     naming convention)

Cache-first/idempotent: a warm cache makes no HTTP call; ``--force`` refetches
both. The FRED auxiliary is best-effort (missing API key → honest SKIP with
the TSI still refreshed); the BTS main series is required — a failure exits
non-zero so CI never commits a half-refreshed panel.

Usage::

    uv run python scripts/bts_tsi_fetch.py [--force]

Display lane ONLY (see docs/data-intake-bts-tsi.md).
"""
from __future__ import annotations

import argparse
import sys
import time

from aionis.ingest.bts_tsi import fetch_tsi_freight, fetch_truck_employment


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="refetch even on warm cache")
    args = parser.parse_args()

    try:
        rows, meta = fetch_tsi_freight(force=args.force)
    except Exception as e:  # noqa: BLE001 — surfaced, never silently swallowed
        print(f"[bts-tsi-fetch] FAIL (main BTS series): {type(e).__name__}: {e}", flush=True)
        return 1
    print(
        f"[bts-tsi-fetch] BTS Freight TSI: {len(rows)} months "
        f"{rows[0]['month']} -> {rows[-1]['month']} "
        f"(latest {rows[-1]['month']} = {rows[-1]['tsi']}; fetched {meta.get('fetched_at', '?')})",
        flush=True,
    )

    time.sleep(2.1)  # politeness before the second host
    try:
        emp = fetch_truck_employment(force=args.force)
    except Exception as e:  # noqa: BLE001 — auxiliary is best-effort
        print(f"[bts-tsi-fetch] SKIP truck-employment auxiliary: {type(e).__name__}: {e}", flush=True)
        return 0
    print(
        f"[bts-tsi-fetch] FRED CES4348400001: {len(emp)} months "
        f"{emp[0]['month']} -> {emp[-1]['month']} (latest {emp[-1]['month']} = {emp[-1]['value']}k)",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
