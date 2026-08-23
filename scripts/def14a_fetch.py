"""Bounded US DEF 14A proxy-statement fetch (display-only, exploratory).

Whole-market EDGAR EFTS form-level query (``forms=DEF%2014A``) over a fixed
window anchored at 2026-04-25 (the same ~120-day anchor as form_ipo; the
window only grows, END rolls with today). First live probe (2026-08-23):
1,387 filings in the window — ~14 polite EFTS page requests (>=2.1s spacing
between pages, idempotent per-window caches; reruns make zero HTTP). The
window's growing anchor will eventually roll into proxy season and approach
EFTS's 10,000-hit cap, so the ingest reuses form13f_dir's adaptive cap-split
(not triggered today).

Writes ``data/cache/form_def14a_aggregate.parquet`` (gitignored,
regenerable); ``scripts/export_terminal_data.py`` reads it into the tracked
web payload.

Usage::

    uv run python scripts/def14a_fetch.py
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from aionis.ingest.form_def14a import fetch_form_def14a_filings

# Fixed window anchor (~120 days, mirroring form_ipo/form8k): START stays
# fixed (window only grows), END rolls with today.
START = "2026-04-25"
END = date.today().isoformat()
OUT = Path("data/cache/form_def14a_aggregate.parquet")


def main() -> None:
    print(f"[def14a-fetch] window {START}..{END}", flush=True)
    running = pd.read_parquet(OUT) if OUT.exists() else None
    if running is not None and not running.empty:
        print(f"[def14a-fetch] seeded aggregate: {len(running)} filings", flush=True)

    df = fetch_form_def14a_filings(start=START, end=END)
    if df.empty:
        print("[def14a-fetch] 0 filings (graceful skip; nothing written)", flush=True)
        return
    by_form = df["form"].value_counts().to_dict()
    print(f"[def14a-fetch] fetched: {len(df)} filings {by_form}", flush=True)

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
        f"[def14a-fetch] final: {len(df)} filings across "
        f"{df['issuer_cik'].nunique()} issuers {by_form} -> {OUT}",
        flush=True,
    )


if __name__ == "__main__":
    main()
