"""GDELT bilingual (eng/zho) market news-feed fetch for the ``/news`` panel.

Two bounded GDELT Doc 2.0 ``artlist`` requests (one per language lane, each
≤200 records, auto-spaced ≥15s by the shared GDELT policy):
  * eng — fixed quoted-phrase market query (``DEFAULT_QUERY``);
  * zho — fixed domain-anchored query (``DEFAULT_QUERY_ZHO``, the
    probe-proven Chinese financial newswire lane; see the ingest docstring
    for the 2026-08-25 evidence table).

Writes ``data/cache/news_feed.parquet`` (gitignored, regenerable) with a
``lang`` code on every row; ``scripts/export_terminal_data.py`` reads it into
the tracked web payload (``news_feed.json``). A single-lane failure degrades
honestly (surviving lane merges, failure logged); both failing keeps the old
cache (the CI step is continue-on-error).

Idempotent: the 7d rolling lookback overlaps the previous run and rows dedupe
by exact URL; the cache keeps a trailing 30-day window. A missed day self-heals
on the next run.

Display-only, exploratory. Does NOT enter the research pipeline (no lookahead
leakage). Politeness: 2 requests per run through the shared GDELT
``HttpRequestPolicy`` (min_interval=15s).

Usage::

    uv run python scripts/news_feed_fetch.py
"""
from __future__ import annotations

from collections import Counter

from aionis.ingest.news_feed import (
    DEFAULT_QUERY,
    DEFAULT_QUERY_ZHO,
    collect_news_feed,
    count_by_day,
)


def main() -> None:
    rows = collect_news_feed()
    if not rows:
        print(
            "[news-feed] WARNING: empty feed (GDELT returned no usable "
            "articles on either lane); cached window retained nothing",
            flush=True,
        )
        return
    by_day = count_by_day(rows)
    domains = Counter(r["domain"] for r in rows if r["domain"])
    top = ", ".join(f"{d}×{n}" for d, n in domains.most_common(5))
    langs = Counter(r.get("lang", "") or "?" for r in rows)
    lang_summary = ", ".join(f"{k}={v}" for k, v in sorted(langs.items()))
    print(
        f"[news-feed] {len(rows)} articles over {by_day[0]['date']} → "
        f"{by_day[-1]['date']} ({len(by_day)} days, "
        f"{len(domains)} sources) [{lang_summary}]",
        flush=True,
    )
    print(f"[news-feed] top sources: {top}", flush=True)
    print(f"[news-feed] query[eng]: {DEFAULT_QUERY}", flush=True)
    print(f"[news-feed] query[zho]: {DEFAULT_QUERY_ZHO}", flush=True)
    if langs.get("zho", 0) == 0:
        print(
            "[news-feed] WARNING: zho lane contributed 0 rows (GDELT coverage "
            "gap or lane failure — see logs above); stream is English-only "
            "this run",
            flush=True,
        )
    print("[news-feed] Complete.", flush=True)


if __name__ == "__main__":
    main()
