"""Bounded US IPO registration/pricing fetch (display-only, exploratory).

Whole-market EDGAR EFTS query (form-level, no CIK — IPO filers are not a
known universe) over a fixed ~120-day window anchored at 2026-04-25 (the
panel is a RECENT filing stream, like form8k's 2026-05-01 anchor; the window
only grows). Two root forms: ``S-1`` (expands to S-1/A) -> status ``filed``,
``424B4`` -> status ``priced``. Polite (>=2s host spacing via ``_policy_get``
— ~12 EFTS page requests total for ~1,000 filings), idempotent (per
root-form EFTS hit-list caches), aggregate deduplicated by accession so
reruns never double-count.

Writes ``data/cache/form_ipo_aggregate.parquet`` (gitignored, regenerable);
``scripts/export_terminal_data.py`` reads it into the tracked web payload.

Usage::

    uv run python scripts/form_ipo_fetch.py
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from aionis.ingest.form_ipo import fetch_ipo_filings

# Fixed window anchor: ~120 days of registration/pricing activity. END rolls
# with today; START stays fixed (window only grows, mirroring form8k_fetch).
START = "2026-04-25"
END = date.today().isoformat()
OUT = Path("data/cache/form_ipo_aggregate.parquet")


def main() -> None:
    print(f"[form-ipo-fetch] window {START}..{END}", flush=True)
    running = pd.read_parquet(OUT) if OUT.exists() else None
    if running is not None and not running.empty:
        print(f"[form-ipo-fetch] seeded aggregate: {len(running)} filings", flush=True)

    df = fetch_ipo_filings(start=START, end=END)
    if df.empty:
        print("[form-ipo-fetch] 0 filings (graceful skip; nothing written)", flush=True)
        return
    by_status = df["status"].value_counts().to_dict()
    print(f"[form-ipo-fetch] fetched: {len(df)} filings {by_status}", flush=True)

    if running is not None and not running.empty:
        # Keep rows from older windows whose fixed anchor predates this run's
        # START (defensive — START is fixed, so this is normally a no-op merge).
        df = pd.concat([running, df], ignore_index=True)
    df = (
        df.drop_duplicates(subset=["accession"], keep="last")
        .sort_values("filed_date", ascending=False)
        .reset_index(drop=True)
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT, index=False)
    by_status = df["status"].value_counts().to_dict()
    print(
        f"[form-ipo-fetch] final: {len(df)} filings across "
        f"{df['issuer_cik'].nunique()} issuers {by_status} -> {OUT}",
        flush=True,
    )


if __name__ == "__main__":
    main()
