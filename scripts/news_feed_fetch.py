"""GDELT market news-feed fetch for the ``/news`` panel (display-only).

One bounded GDELT Doc 2.0 ``artlist`` request (≤200 records, ≥15s host spacing)
for recent market headlines — quoted-phrase query, machine ``datedesc`` order,
metadata + outbound links only. Writes ``data/cache/news_feed.parquet``
(gitignored, regenerable); ``scripts/export_terminal_data.py`` reads it into
the tracked web payload (``news_feed.json``).

Idempotent: the 7d rolling lookback overlaps the previous run and rows dedupe
by exact URL; the cache keeps a trailing 30-day window. A missed day self-heals
on the next run.

Display-only, exploratory. Does NOT enter the research pipeline (no lookahead
leakage). Politeness: 1 request per run through the shared GDELT
``HttpRequestPolicy`` (min_interval=15s).

Usage::

    uv run python scripts/news_feed_fetch.py
"""
from __future__ import annotations

from collections import Counter

from aionis.ingest.news_feed import (
    DEFAULT_QUERY,
    collect_news_feed,
    count_by_day,
)


def main() -> None:
    rows = collect_news_feed()
    if not rows:
        print(
            "[news-feed] WARNING: empty feed (GDELT returned no usable "
            "articles); cached window retained nothing",
            flush=True,
        )
        return
    by_day = count_by_day(rows)
    domains = Counter(r["domain"] for r in rows if r["domain"])
    top = ", ".join(f"{d}×{n}" for d, n in domains.most_common(5))
    print(
        f"[news-feed] {len(rows)} articles over {by_day[0]['date']} → "
        f"{by_day[-1]['date']} ({len(by_day)} days, "
        f"{len(domains)} sources)",
        flush=True,
    )
    print(f"[news-feed] top sources: {top}", flush=True)
    print(f"[news-feed] query: {DEFAULT_QUERY}", flush=True)
    print("[news-feed] Complete.", flush=True)


if __name__ == "__main__":
    main()
