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

import sys
from collections import Counter
from datetime import date, datetime

from aionis.ingest.news_feed import (
    DEFAULT_QUERY,
    DEFAULT_QUERY_ZHO,
    collect_news_feed,
    count_by_day,
)

# Round 211: GDELT occasionally serves a server-side CACHED batch for the
# heavy multi-OR eng query — a mechanically successful fetch whose newest
# seendate is days old (first live catch: 2026-10-06, newest 10-02 while a
# simple query served same-minute data). Exit nonzero when the merged feed's
# newest item is >2 days old so the lane records a SOFT-FAIL: the panel then
# honestly retains (verifier's accounted branch) instead of silently drifting.
_STALE_DAYS = 2


def _newest_seendate(rows: list[dict]) -> datetime | None:
    # rows carry the INGEST-normalized ISO form (normalize_seendate)
    newest = max((r.get("seendate") or "") for r in rows) if rows else ""
    try:
        return datetime.strptime(newest, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None


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
    newest = _newest_seendate(rows)
    if newest is not None:
        age_days = (date.today() - newest.date()).days
        if age_days > _STALE_DAYS:
            print(
                f"[news-feed] STALE-SOURCE: fetch completed but the newest "
                f"seendate is {newest.date()} ({age_days} days old) — GDELT "
                f"served a cached batch for this query. Exiting nonzero so "
                f"the lane records a soft-fail (panel retains honestly).",
                flush=True,
            )
            sys.exit(3)


if __name__ == "__main__":
    main()
