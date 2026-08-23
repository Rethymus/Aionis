"""Bounded fetch of the 13F filer directory (EFTS form-level, display-only).

Trailing annual cycle (~4 quarters + current partial) of 13F-HR / 13F-HR/A
filings, aggregated per-CIK into the directory. ~97 pages per quarter at
>=2s spacing (~5 min per cold quarter; idempotent per-window caches make
re-runs cheap). Writes ``data/cache/form13f_dir.parquet`` (gitignored,
regenerable); ``scripts/export_terminal_data.py`` builds the tracked JSON.

Usage::

    uv run python scripts/form13f_dir_fetch.py
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from aionis.ingest.form13f_dir import fetch_filer_directory

OUT = Path("data/cache/form13f_dir.parquet")

# Trailing annual cycle of calendar quarters (ISO windows). The current
# partial quarter runs to today. A filer active ANY time in the cycle
# appears — 13F-HR is at minimum an annual obligation.
_QUARTERS = [
    ("2025-09-01", "2025-11-30"),
    ("2025-12-01", "2026-02-28"),
    ("2026-03-01", "2026-05-31"),
    ("2026-06-01", "2026-08-31"),
]


def main() -> None:
    print(
        f"[13f-dir-fetch] windows {_QUARTERS[0][0]}..{_QUARTERS[-1][1]} "
        f"(today {date.today().isoformat()})",
        flush=True,
    )
    df = fetch_filer_directory(quarters=_QUARTERS)
    if df.empty:
        print("[13f-dir-fetch] 0 filers (graceful skip; nothing written)", flush=True)
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT, index=False)
    with_amend = int((df["n_amendments"] > 0).sum())
    print(
        f"[13f-dir-fetch] {len(df)} filers -> {OUT} "
        f"(filings sum {int(df['n_filings'].sum())}, {with_amend} with "
        f"amendments, latest {df['latest_filed'].max()})",
        flush=True,
    )


if __name__ == "__main__":
    main()
