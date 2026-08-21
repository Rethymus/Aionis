"""Bounded Form 8-K material-event fetch (display-only, exploratory).

Same 5 large-cap issuers as ``form4_fetch.py`` (consistent universe), fixed
window anchored at 2026-05-01 (the panel is a RECENT-event stream, not a
2016 history — the window only grows). Polite (≥2s host spacing via
``_policy_get``), idempotent (EFTS + per-accession caches), aggregate
deduplicated by accession so reruns never double-count.

Writes ``data/cache/form8k_aggregate.parquet`` (gitignored, regenerable);
``scripts/export_terminal_data.py`` reads it into the tracked web payload.

Usage::

    uv run python scripts/form8k_fetch.py
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from aionis.ingest.form8k import fetch_form8k_events

# Same bounded issuer set as form4 (5 large caps; each issuer = 1 EFTS query +
# ~2 polite requests per new filing — the daily cron budget holds).
ISSUERS: dict[int, str] = {
    320193: "AAPL",
    789019: "MSFT",
    1045810: "NVDA",
    1652044: "GOOGL",
    1018724: "AMZN",
}
START = "2026-05-01"
END = date.today().isoformat()
OUT = Path("data/cache/form8k_aggregate.parquet")


def main() -> None:
    print(f"[form8k-fetch] window {START}..{END}", flush=True)
    running = pd.read_parquet(OUT) if OUT.exists() else None
    if running is not None and not running.empty:
        print(f"[form8k-fetch] seeded aggregate: {len(running)} filings", flush=True)

    for cik, ticker in ISSUERS.items():
        df = fetch_form8k_events(cik, ticker=ticker, start=START, end=END)
        if df.empty:
            print(f"[form8k-fetch] {ticker}: 0 filings (graceful skip)", flush=True)
            continue
        cats = df["category"].value_counts().to_dict()
        print(f"[form8k-fetch] {ticker}: {len(df)} filings {cats}", flush=True)
        running = df if running is None else pd.concat([running, df], ignore_index=True)
        running = (
            running.drop_duplicates(subset=["accession"], keep="last")
            .sort_values("filing_date", ascending=False)
            .reset_index(drop=True)
        )
        OUT.parent.mkdir(parents=True, exist_ok=True)
        running.to_parquet(OUT, index=False)
        print(f"[form8k-fetch] checkpoint: {len(running)} filings -> {OUT}", flush=True)

    if running is None or running.empty:
        print("[form8k-fetch] no filings; nothing written", flush=True)
        return
    print(
        f"[form8k-fetch] final: {len(running)} filings across "
        f"{running['ticker'].nunique()} issuers -> {OUT}",
        flush=True,
    )


if __name__ == "__main__":
    main()
