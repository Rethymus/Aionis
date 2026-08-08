"""Zero-credential Reddit retail-sentiment forward-collect (display-only, exploratory).

Pulls recent submissions from r/wallstreetbets / r/stocks / r/investing via the
public Atom RSS feed (NO API key, NO OAuth approval — Reddit blocked both the
unauthenticated ``.json`` path (403, 2026) and new OAuth tokens via the
Responsible Builder Policy). The RSS path is Reddit's OWN published subscription
format — ToS-clean for low-rate feed-reader consumption (G7), unlike a ``.json``
scrape.

The collector (``aionis.ingest.reddit_sentiment``) writes, per run:
  * ``data/cache/reddit_snapshots.parquet`` — append-only cumulative snapshots;
  * ``data/cache/reddit_raw_<ts>.json`` — immutable raw archive (sha256-pinned);
  * ``data/cache/reddit_last_run.json`` — status sidecar for the terminal display;
  * one ``data_ingest`` ledger row (``mode: exploratory``, ``forward_only: true``).

``scripts/export_terminal_data.py::export_reddit_meta`` reads the snapshot +
sidecar into the tracked web payload.

Forward-collection only: NO backfill (Pushshift dead 2023; no permissive
historical Reddit corpus). The series accumulates from the first run. Exploratory
only — never enters the Aionis OOS research pipeline (no PIT history to test).
``transport="auto"`` means: if ``REDDIT_CLIENT_ID`` / ``SECRET`` are later set in
``.env``, the collector auto-upgrades to PRAW (carries ``score``).

Usage::

    uv run python scripts/reddit_fetch.py

Re-run safely: the cumulative parquet is append-only; each run adds one snapshot.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from aionis.ingest.reddit_sentiment import collect_reddit_sentiment

PANEL = Path("data/cache/track_b_panel.parquet")

# Fallback scan universe if the Track B panel is absent: mega-cap + retail-popular
# tickers. Self-contained so the fetch runs without the panel; the panel (S&P 500
# PIT constituents) is preferred when present so long-tail mentions are caught too.
_FALLBACK_TICKERS = sorted(
    {
        # mega-cap tech
        "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "GOOG", "META", "TSLA", "AVGO",
        "AMD", "NFLX", "CRM", "ORCL", "ADBE", "ACN", "CSCO", "INTC", "MU", "QCOM",
        # mega-cap other
        "JPM", "V", "MA", "JNJ", "WMT", "PG", "UNH", "HD", "BAC", "XOM", "KO",
        "PEP", "COST", "LLY", "ABT", "ABBV", "PFE", "MRK", "TMO", "CVX", "MCD",
        "NKE", "DIS",
        # retail-popular / meme-adjacent
        "BABA", "PLTR", "COIN", "HOOD", "SOFI", "GME", "AMC", "SHOP", "SQ", "SNAP",
        "F", "GM", "AAL", "UAL", "DKNG", "RBLX", "MARA", "RIOT", "CHWY", "NKLA",
    }
)


def _load_scan_universe() -> list[str]:
    if PANEL.exists():
        return sorted(pd.read_parquet(PANEL)["ticker"].dropna().astype(str).unique())
    return _FALLBACK_TICKERS


def main() -> None:
    tickers = _load_scan_universe()
    print(
        f"[reddit-fetch] scanning {len(tickers)} tickers across "
        "r/wallstreetbets / r/stocks / r/investing (zero-credential RSS)",
        flush=True,
    )
    df = collect_reddit_sentiment(tickers, transport="auto")
    if df.empty:
        print(
            "[reddit-fetch] no in-window ticker mentions this run "
            "(snapshot + ledger row still recorded)",
            flush=True,
        )
        return
    top = df.sort_values("mentions", ascending=False).head(10)
    print(f"[reddit-fetch] {len(df)} ticker rows in this snapshot:", flush=True)
    for _, row in top.iterrows():
        bull = row["bull_ratio"]
        bull_s = "n/a" if pd.isna(bull) else f"{float(bull):.2f}"
        print(
            f"  {row['ticker']}: {int(row['mentions'])} mentions, "
            f"sentiment {float(row['sentiment_mean']):+.2f}, bull {bull_s}",
            flush=True,
        )
    print(
        "[reddit-fetch] -> data/cache/reddit_snapshots.parquet "
        "(cumulative append; ledger row appended; reddit_last_run.json updated)",
        flush=True,
    )


if __name__ == "__main__":
    main()
