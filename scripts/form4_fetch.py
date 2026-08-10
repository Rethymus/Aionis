"""Bounded Form 4 insider-trading fetch (display-only, exploratory).

Small large-cap issuer set, full Trump-era window (2016→today). Polite (≥2s host
spacing via ``_policy_get``), placeholder User-Agent (SEC tolerates this for small
polite pulls — verified 2026-08-06: AAPL EFTS returned 26 filings with no 429/403).

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
# Large-cap issuer CIKs (SEC EDGAR public). Bounded to 5 — the daily cron's cold
# pull (each issuer = EFTS + per-accession XML, polite ≥2s) must finish within the
# refresh job's 45-min budget; 10 issuers timed out. The data-cache action makes
# subsequent runs delta-only (fast). Expand cautiously + only after a timed cold run.
ISSUERS: dict[int, str] = {
    320193: "AAPL",
    789019: "MSFT",
    1045810: "NVDA",
    1652044: "GOOGL",
    1018724: "AMZN",
}
START = "2016-01-01"
END = "2026-08-31"
OUT = Path("data/cache/form4_aggregate.parquet")


def main() -> None:
    frames: list[pd.DataFrame] = []
    for cik, ticker in ISSUERS.items():
        print(f"[form4-fetch] {ticker} (CIK {cik:010d}) {START}..{END}", flush=True)
        df = fetch_form4_transactions(cik, start=START, end=END)
        if df.empty:
            print("  -> 0 transactions (graceful skip)", flush=True)
            continue
        df["issuer_ticker"] = ticker
        frames.append(df)
        buys = (df["buy_or_sell"] == "buy").sum()
        sells = (df["buy_or_sell"] == "sell").sum()
        print(f"  -> {len(df)} txns ({buys} buys / {sells} sells)", flush=True)
        # Merge-by-issuer: a full 2016→today pull is thousands of polite per-
        # accession XML fetches (multi-hour). Checkpoint after each issuer, KEEPING
        # existing issuers not (re)processed this run, so the fetch deepens each
        # issuer as it completes without dropping the others (no live breadth
        # regression). A full run re-processes all issuers; the per-accession XML
        # cache is idempotent, so completed issuers are fast on re-run.
        out = pd.concat(frames, ignore_index=True)
        if OUT.exists():
            prev = pd.read_parquet(OUT)
            done = {f["issuer_ticker"].iloc[0] for f in frames if not f.empty}
            keep_prev = prev[~prev["issuer_ticker"].isin(done)]
            out = pd.concat([keep_prev, out], ignore_index=True)
        OUT.parent.mkdir(parents=True, exist_ok=True)
        out.to_parquet(OUT, index=False)
        print(
            f"[form4-fetch] checkpoint: {len(out)} txns across "
            f"{out['issuer_ticker'].nunique()} issuers -> {OUT}",
            flush=True,
        )

    if not frames:
        print("[form4-fetch] no transactions across issuers; nothing written")


if __name__ == "__main__":
    main()
