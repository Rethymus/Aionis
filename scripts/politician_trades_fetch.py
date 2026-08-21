"""Bounded House PTR filing-stream fetch (display-only, exploratory).

STOCK Act congressional trading, v1 = House Clerk PTR bulk index
(filing-stream level — member/office/filing-date/year/PDF link; transaction
detail lives in the PDFs and is NOT parsed). Senate eFD is Akamai-blocked
(documented honestly in the 7-gate doc). ONE polite request per year (the
daily-reissued {year}FD.zip); per-year parquet caches are idempotent (and are
the G3 freeze-snapshot of a source that re-emits daily).

Writes ``data/cache/politician_trades_aggregate.parquet`` (gitignored,
regenerable); ``scripts/export_terminal_data.py`` reads it into the tracked
web payload.

Usage::

    uv run python scripts/politician_trades_fetch.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from aionis.ingest.politician_trades import fetch_house_directory, fetch_house_ptr_year

# Recent window: current + previous year (the panel is a recent stream, not a
# 2008-2027 archive; expand by appending years here).
YEARS: tuple[int, ...] = (2025, 2026)
OUT = Path("data/cache/politician_trades_aggregate.parquet")


def main() -> None:
    # Party-join source (ONE polite cached request; current-member directory).
    directory = fetch_house_directory()
    print(
        f"[politician-trades-fetch] directory: {len(directory)} members "
        f"({directory['office'].nunique()} offices)",
        flush=True,
    )

    frames: list[pd.DataFrame] = []
    for year in YEARS:
        df = fetch_house_ptr_year(year)
        print(f"[politician-trades-fetch] {year}: {len(df)} PTR filings", flush=True)
        if not df.empty:
            frames.append(df)

    if not frames:
        print("[politician-trades-fetch] no filings; nothing written", flush=True)
        return
    out = (
        pd.concat(frames, ignore_index=True)
        .drop_duplicates(subset=["doc_url"], keep="last")
        .sort_values(["filing_date", "member"], ascending=[False, True])
        .reset_index(drop=True)
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(OUT, index=False)
    print(
        f"[politician-trades-fetch] final: {len(out)} filings "
        f"({out['member'].nunique()} members) -> {OUT}",
        flush=True,
    )


if __name__ == "__main__":
    main()
