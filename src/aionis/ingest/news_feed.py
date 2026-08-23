"""GDELT market news-feed stream (display-only, exploratory).

Feeds the ``/news`` panel (``export_news_feed`` in
``scripts/export_terminal_data.py``). One bounded GDELT Doc 2.0 ``artlist``
query per run returns RECENT market-headline METADATA (title / url / domain /
seendate / language / sourcecountry) — the article itself stays at the
publisher; every panel row links out. No article text is stored, summarized or
fabricated.

**Reuse (same reuse-first stance as ``news_sentiment_gdelt``):**
  * HTTP is routed through the existing module's ``HttpRequestPolicy``
    (``HostSpacingPolicy(min_interval=15.0)``). GDELT's documented minimum is
    ≥5s, but sustained cold pulls at 5s triggered HTTP 429 on the 2026-08-11 CI
    run; 15s clears the abuse throttle. The news-feed lane fires ONE request
    per run, so the spacing cost is a single 15s slot.
  * Endpoint + User-Agent constants are imported from ``news_sentiment_gdelt``
    so the two GDELT consumers can never drift apart.

**Honest scope (NOT a research claim):**
  * The query is a FIXED market-headline phrase search
    (``("stock market" OR "S&P 500" OR "Federal Reserve") sourcelang:eng``).
    Phrases must be quoted — unquoted ``federal reserve`` matches the two words
    anywhere in an article and pulled junk (verified on the 2026-08-22 probe:
    a Nigerian job-scam story matched while every quoted-phrase hit was market
    coverage).
  * ``seendate`` is GDELT's first-seen UTC timestamp (15-min resolution), the
    PIT visibility anchor for display.
  * Dedup key = exact URL. Syndicated copies of the same story on different
    domains are NOT collapsed — shown as separate rows, honestly counted.
  * Ranking is GDELT ``sort=datedesc`` (machine ordering, not editorial).
  * Coverage is whatever GDELT's crawl saw (English-biased); gaps are gaps.
  * ``mode: exploratory`` — display lane only, never enters Phase-B/OOS.

Intake-rubric clearance (``docs/data-intake-gdelt-news-feed.md``):
  * **G1** — GDELT open data: URL/title/date/domain are facts (not
    copyrightable); article copyright stays with publishers (link-out only).
  * **G2** — ``seendate`` UTC recorded verbatim; snapshot_ts at collection.
  * **G3** — append-only stream; dedup key=url; reruns merge, never overwrite.
  * **G5** — display-only /news panel.
  * **G6** — fixed query + machine ranking declared; syndication dupes kept.
  * **G7** — ≥15s host spacing (GDELT) + 1 bounded request per run (≤200 recs).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode

import pandas as pd
import requests
import structlog

# Reuse the sibling GDELT module's endpoint / UA / polite policy so the two
# api.gdeltproject.org consumers share one discipline (precedent: form8k
# importing _policy_get from form4_efts).
from aionis.ingest.news_sentiment_gdelt import (
    _GDELT_DOC_URL,
    _USER_AGENT,
    _policy,
)

log = structlog.get_logger()

# Quoted phrases are load-bearing (see module docstring): each alternative is a
# phrase match, so "Federal Reserve" cannot match scattered words.
DEFAULT_QUERY = '("stock market" OR "S&P 500" OR "Federal Reserve") sourcelang:eng'
DEFAULT_TIMESPAN = "7d"  # rolling lookback; daily runs overlap + dedupe by url
MAX_RECORDS = 200  # GDELT artlist cap is 250; bounded below it per task budget
CACHE_KEEP_DAYS = 30  # the panel is a RECENT stream, not an archive
_COLUMNS = ["url", "title", "seendate", "domain", "language", "sourcecountry"]

_CACHE_NAME = "news_feed.parquet"


# --- pure parsers (hermetic-testable, no network) -----------------------------


def normalize_seendate(raw: object) -> str:
    """GDELT ``YYYYMMDDTHHMMSSZ`` → ISO ``YYYY-MM-DDTHH:MM:SSZ`` (``""`` if bad).

    Pure. Malformed stamps become empty strings — never guessed, never raised
    (a display row with an unknown time sorts last and shows honestly empty).
    """
    s = str(raw or "").strip()
    # ``YYYYMMDDTHHMMSSZ`` is 16 chars (8 date + T + 6 time + Z); the salvaged
    # lane checked 15, which emptied EVERY real stamp (merge_feed then drops
    # all rows — the feed could never fill). Caught by test_normalize_valid_stamp.
    if len(s) == 16 and s[8] == "T" and s.endswith("Z") and s[:8].isdigit():
        return f"{s[0:4]}-{s[4:6]}-{s[6:8]}T{s[9:11]}:{s[11:13]}:{s[13:15]}Z"
    return ""


def parse_artlist(payload: dict) -> list[dict]:
    """Parse a GDELT ``artlist`` JSON response into feed rows.

    Robust to: missing ``articles`` key, non-dict entries, missing fields
    (kept as ``""`` — honest empties, never fabricated). Entries without a
    ``url`` cannot be deduped or linked, so they are skipped and counted in
    the log — the dedup key is the identity contract.
    """
    articles = payload.get("articles") or []
    rows: list[dict] = []
    skipped = 0
    for a in articles:
        if not isinstance(a, dict):
            skipped += 1
            continue
        url = str(a.get("url") or "").strip()
        if not url:
            skipped += 1
            continue
        rows.append({
            "url": url,
            "title": str(a.get("title") or "").strip(),
            "seendate": normalize_seendate(a.get("seendate")),
            "domain": str(a.get("domain") or "").strip(),
            "language": str(a.get("language") or "").strip(),
            "sourcecountry": str(a.get("sourcecountry") or "").strip(),
        })
    if skipped:
        log.info("news_feed_artlist_skipped", n=skipped)
    return rows


def merge_feed(
    cached: list[dict], new_rows: list[dict], *, keep_days: int, today: date,
) -> list[dict]:
    """Merge cached + newly-fetched rows; dedupe by url (new wins), trim window.

    Pure. Trims to ``[today - keep_days, today]`` on the ``seendate`` DATE part
    (rows whose seendate failed to normalize are dropped — an undated entry
    cannot be placed on the stream timeline). Output sorted by ``seendate``
    descending (newest first — the feed reads top-down).
    """
    by_url: dict[str, dict] = {r["url"]: r for r in cached if r.get("url")}
    for r in new_rows:
        if r.get("url"):
            by_url[r["url"]] = r
    cutoff = (today - timedelta(days=keep_days)).isoformat()
    kept = [
        r for r in by_url.values()
        if r.get("seendate", "")[:10] >= cutoff
    ]
    return sorted(kept, key=lambda r: r.get("seendate", ""), reverse=True)


def count_by_day(rows: list[dict]) -> list[dict]:
    """``[{date, count}]`` ascending — the by-day volume summary (pure)."""
    counts: dict[str, int] = {}
    for r in rows:
        d = r.get("seendate", "")[:10]
        if d:
            counts[d] = counts.get(d, 0) + 1
    return [{"date": d, "count": n} for d, n in sorted(counts.items())]


# --- network (routed through the shared polite policy) ------------------------


def fetch_articles(
    query: str = DEFAULT_QUERY,
    timespan: str = DEFAULT_TIMESPAN,
    maxrecords: int = MAX_RECORDS,
) -> list[dict]:
    """One GDELT Doc ``artlist`` GET through the ≥15s policy → parsed rows.

    ``sort=datedesc`` (machine ordering). Raises on HTTP error after the
    bounded retry — the caller decides to keep the old cache (CI step is
    continue-on-error).
    """
    params = {
        "query": query,
        "mode": "artlist",
        "maxrecords": str(int(maxrecords)),
        "sort": "datedesc",
        "timespan": timespan,
        "format": "json",
    }
    url = f"{_GDELT_DOC_URL}?{urlencode(params)}"

    def operation() -> requests.Response:
        return requests.get(url, headers={"User-Agent": _USER_AGENT}, timeout=60)

    resp = _policy.request(_GDELT_DOC_URL, operation)
    resp.raise_for_status()
    return parse_artlist(resp.json())


# --- snapshot cache (idempotent parquet, dedup key=url) -----------------------


def load_cached_feed(cache_dir: Path | None = None) -> list[dict]:
    """Load the cached feed rows; ``[]`` if absent/corrupt (regenerable)."""
    fp = (cache_dir or Path("data/cache")) / _CACHE_NAME
    if not fp.exists():
        return []
    try:
        df = pd.read_parquet(fp)
        return df[_COLUMNS].to_dict("records")
    except (FileNotFoundError, KeyError, OSError):
        return []


def collect_news_feed(
    cache_dir: Path | None = None,
    query: str = DEFAULT_QUERY,
    timespan: str = DEFAULT_TIMESPAN,
) -> list[dict]:
    """Incremental fetch: one artlist pull merged into the trailing window.

    Daily-run-cheap by design: 1 request × ≤200 records; the 7d timespan
    overlaps the previous run and ``merge_feed`` dedupes by url, so reruns are
    idempotent and a missed day self-heals on the next run. Writes
    ``data/cache/news_feed.parquet`` (gitignored, regenerable) and returns the
    merged rows, newest first.
    """
    cache_dir = cache_dir or Path("data/cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    fp = cache_dir / _CACHE_NAME

    cached = load_cached_feed(cache_dir)
    new_rows = fetch_articles(query=query, timespan=timespan)
    merged = merge_feed(
        cached, new_rows, keep_days=CACHE_KEEP_DAYS, today=date.today()
    )
    pd.DataFrame(merged, columns=_COLUMNS).to_parquet(fp, index=False)
    log.info(
        "news_feed_snapshot_written",
        cached=len(cached),
        new=len(new_rows),
        merged=len(merged),
        window_days=CACHE_KEEP_DAYS,
        snapshot_ts=datetime.now().astimezone().isoformat(),
    )
    return merged
