"""Bounded Form 4 insider-trading fetch (display-only, exploratory).

Small large-cap issuer set, recent ~2.5y window. Polite (≥2s host spacing via
``_policy_get``), placeholder User-Agent (SEC tolerates this for small polite
pulls — verified 2026-08-06: AAPL EFTS returned 26 filings with no 429/403).

Writes ``data/cache/form4_aggregate.parquet`` (gitignored, regenerable).
``scripts/export_terminal_data.py`` reads it into the tracked web payload.

Usage::

    uv run python scripts/form4_fetch.py

Re-run safely: EFTS + XML caches are idempotent (no re-fetch on cache hit).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from aionis.ingest.form4_orchestrator import fetch_form4_transactions

# Large-cap issuer CIKs (SEC EDGAR public). Small bounded set keeps the pull
# polite + fast; expand cautiously (each issuer = EFTS + per-accession XML).
ISSUERS: dict[int, str] = {
    320193: "AAPL",
    789019: "MSFT",
    1045810: "NVDA",
    1652044: "GOOGL",
    1018724: "AMZN",
}
START = "2024-01-01"
END = "2026-06-30"
OUT = Path("data/cache/form4_aggregate.parquet")


def main() -> None:
    frames: list[pd.DataFrame] = []
    for cik, ticker in ISSUERS.items():
        print(f"[form4-fetch] {ticker} (CIK {cik:010d}) {START}..{END}", flush=True)
        df = fetch_form4_transactions(cik, start=START, end=END)
        if df.empty:
            print(f"  -> 0 transactions (graceful skip)", flush=True)
            continue
        df["issuer_ticker"] = ticker
        frames.append(df)
        buys = (df["acquired_or_disposed"] == "A").sum()
        sells = (df["acquired_or_disposed"] == "D").sum()
        print(f"  -> {len(df)} txns ({buys} buys / {sells} sells)", flush=True)

    if not frames:
        print("[form4-fetch] no transactions across issuers; nothing written")
        return

    out = pd.concat(frames, ignore_index=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(OUT, index=False)
    print(
        f"[form4-fetch] wrote {len(out)} txns across {len(frames)} issuers to {OUT}",
        flush=True,
    )


if __name__ == "__main__":
    main()
