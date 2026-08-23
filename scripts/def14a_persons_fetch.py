"""Bounded DEF 14A person-level fetch (display-only, exploratory).

Walks the NEWEST ~150 DEF 14A filings of the panel aggregate
(``data/cache/form_def14a_aggregate.parquet``, produced by
``scripts/def14a_fetch.py`` — run that first when absent), resolves each
filing's primary proxy document (<= 2 GETs per filing, idempotent per-
accession caches, >= 2.1s spacing), and parses directors / executive
officers with conservative tiered confidence (``aionis.ingest.def14a_persons``
— 宁可 null 不猜测). HARD 45-minute wall-clock budget: on expiry the loop
stops and coverage reports only the processed prefix (honest counting, never
extrapolated).

Writes ``data/cache/def14a_persons_parsed.json`` (gitignored, regenerable);
``scripts/export_terminal_data.py::export_def14a_persons`` reads it into the
tracked web payload ``def14a_persons.json``.

Usage::

    uv run python scripts/def14a_persons_fetch.py
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from aionis.ingest.def14a_persons import fetch_def14a_persons

AGGREGATE = Path("data/cache/form_def14a_aggregate.parquet")
OUT = Path("data/cache/def14a_persons_parsed.json")

LIMIT = 150  # newest-N of the panel (bounded politeness, disclosed coverage)
BUDGET_SECONDS = 45 * 60  # hard wall-clock stop


def main() -> None:
    if not AGGREGATE.exists():
        raise SystemExit(
            f"[def14a-persons] {AGGREGATE} not present — run scripts/def14a_fetch.py first"
        )
    df = pd.read_parquet(AGGREGATE)
    if df.empty:
        print("[def14a-persons] empty aggregate (graceful skip; nothing written)", flush=True)
        return
    rows = df.head(LIMIT).to_dict("records")  # newest-first (aggregate contract)
    print(
        f"[def14a-persons] target={len(rows)} newest filings "
        f"({rows[-1]['filed_date']}..{rows[0]['filed_date']}), "
        f"budget={BUDGET_SECONDS}s",
        flush=True,
    )
    out = fetch_def14a_persons(rows, limit=LIMIT, budget_seconds=BUDGET_SECONDS)

    n_with = sum(1 for r in out["results"].values() if r.get("parsed"))
    by_method: dict[str, int] = {}
    n_persons = 0
    for r in out["results"].values():
        m = r.get("method") or (r.get("error") or "unparsed")
        by_method[m] = by_method.get(m, 0) + 1
        n_persons += len(r.get("persons") or [])
    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "n_target": out["n_target"],
        "n_processed": out["n_processed"],
        "n_with_persons": n_with,
        "budget_seconds": out["budget_seconds"],
        "budget_hit": out["budget_hit"],
        "n_requests": out["n_requests"],
        "results": out["results"],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(
        f"[def14a-persons] processed {out['n_processed']}/{out['n_target']} "
        f"(budget_hit={out['budget_hit']}, requests={out['n_requests']}): "
        f"{n_with} filings with persons, {n_persons} person-rows, "
        f"methods {by_method} -> {OUT}",
        flush=True,
    )


if __name__ == "__main__":
    main()
