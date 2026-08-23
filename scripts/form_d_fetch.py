"""Bounded US Form D exempt-offering fetch (display-only, exploratory).

Whole-market EDGAR EFTS form-level query over a ROLLING ~30-day window. The
first probe (2026-08-23) requested 90 days and hit EFTS's hard cap: exactly
10,000 hits served = only the newest 41 days (~244 notices/day; the older
month of the request silently truncated by the cap). A 30-day query (~7,300
filings) fits under the cap with headroom, so the fetch queries the newest
30 days each run and the parquet AGGREGATE accumulates (dedup by accession
— the same accumulating-recent-stream pattern as stakes13g; the 10,000
rows from today's capped 90-day probe seed the aggregate's older days).

~30 polite EFTS pages per run (>=2s host spacing), idempotent per-window
caches. Writes ``data/cache/form_d_aggregate.parquet`` (gitignored,
regenerable); ``scripts/export_terminal_data.py`` reads it into the tracked
web payload.

Usage::

    uv run python scripts/form_d_fetch.py
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from aionis.ingest.form_d import fetch_form_d_filings

# Rolling window: EFTS serves at most 10,000 hits per query; ~244 Form D
# notices/day means a 30-day window (~7,300) fits with headroom. The
# AGGREGATE below accumulates across runs (the panel's window spans
# everything ever fetched, deduped by accession).
_WINDOW_DAYS = 30
START = (date.today() - timedelta(days=_WINDOW_DAYS)).isoformat()
END = date.today().isoformat()
OUT = Path("data/cache/form_d_aggregate.parquet")


def main() -> None:
    print(f"[form-d-fetch] window {START}..{END}", flush=True)
    running = pd.read_parquet(OUT) if OUT.exists() else None
    if running is not None and not running.empty:
        print(f"[form-d-fetch] seeded aggregate: {len(running)} filings", flush=True)

    df = fetch_form_d_filings(start=START, end=END)
    if df.empty:
        print("[form-d-fetch] 0 filings (graceful skip; nothing written)", flush=True)
        return
    by_form = df["form"].value_counts().to_dict()
    print(f"[form-d-fetch] fetched: {len(df)} filings {by_form}", flush=True)

    if running is not None and not running.empty:
        df = pd.concat([running, df], ignore_index=True)
    df = (
        df.drop_duplicates(subset=["accession"], keep="last")
        .sort_values("filed_date", ascending=False)
        .reset_index(drop=True)
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT, index=False)
    by_form = df["form"].value_counts().to_dict()
    print(
        f"[form-d-fetch] final: {len(df)} filings across "
        f"{df['issuer_cik'].nunique()} issuers {by_form} -> {OUT}",
        flush=True,
    )


if __name__ == "__main__":
    main()
