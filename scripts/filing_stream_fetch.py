"""Bounded fetch of the v2 unified filing stream (direct multi-form, display-only).

Trailing 14-day window of the whole-market stream — direct EFTS root-form
queries (8-K / 10-K / 10-Q / S-1 / 4 / D; one form parameter per query) plus
the daily crawler index lanes for SC 13D / SC 13G (EFTS froze on Schedule 13
after 2024-12-17 — the frozen roots are still probed, one cached page each,
as the machine-verified zero). Measured request volume (2026-08-23): ~140
pages at >=2.1s spacing (~6 min cold; idempotent per-form caches make re-runs
free). Writes ``data/cache/filing_stream_aggregate.parquet`` (gitignored,
regenerable) + ``filing_stream_stats.json`` (the per-form request accounting
the export discloses); ``scripts/export_terminal_data.py`` builds the tracked
JSON. Ticker resolution prefers as-of-filing display_names tickers and falls
back to the offline ``cik_resolver`` snapshot — copy/maintain
``data/cache/cik_resolver_raw.json`` locally for full label coverage.

Usage::

    uv run python scripts/filing_stream_fetch.py
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from aionis.ingest.filing_stream import fetch_filing_stream

OUT = Path("data/cache/filing_stream_aggregate.parquet")
STATS_OUT = Path("data/cache/filing_stream_stats.json")

# RECENT-stream window: trailing 14 days (inclusive of today). Form 4 is
# split into two ~7-day halves by the module (cap safety), so this window is
# also the split transcript the methodology discloses.
_WINDOW_DAYS = 14


def main() -> None:
    end = date.today()
    start = end - timedelta(days=_WINDOW_DAYS - 1)
    print(
        f"[fstream-fetch] window {start.isoformat()}..{end.isoformat()} "
        f"(today {date.today().isoformat()})",
        flush=True,
    )
    df, stats = fetch_filing_stream(
        start=start.isoformat(), end=end.isoformat()
    )
    # Per-form request accounting (the honest ledger the panel discloses).
    total_requests = 0
    for root, fs in stats["forms"].items():
        reqs = sum(w["requests"] for w in fs["windows"])
        total_requests += reqs
        windows = ", ".join(
            f"{w['start']}..{w['end']} total={w['total']} req={w['requests']}"
            for w in fs["windows"]
        )
        print(
            f"[fstream-fetch] {root}: {fs['rows']} rows over "
            f"{len(fs['windows'])} window(s) [{windows}]"
            f"{' SPLIT' if fs['split'] else ''}"
            f"{' CAPPED-KEPT' if fs['capped_kept'] else ''}",
            flush=True,
        )
    if "schedule13_daily_lane_rows" in stats:
        print(
            f"[fstream-fetch] Schedule-13 shared daily-index lane "
            f"(SC 13D + SC 13G): {stats['schedule13_daily_lane_rows']} rows",
            flush=True,
        )
    print(
        f"[fstream-fetch] {total_requests} EFTS page requests total",
        flush=True,
    )
    if df.empty:
        print(
            "[fstream-fetch] 0 rows (graceful skip; nothing written)",
            flush=True,
        )
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT, index=False)
    STATS_OUT.write_text(json.dumps(stats, indent=2))
    by_form = df["form"].value_counts().to_dict()
    print(
        f"[fstream-fetch] {len(df)} rows -> {OUT} "
        f"(by_form {dict(sorted(by_form.items(), key=lambda kv: -kv[1]))}, "
        f"filed {df['filed_date'].min()}..{df['filed_date'].max()})",
        flush=True,
    )


if __name__ == "__main__":
    main()
