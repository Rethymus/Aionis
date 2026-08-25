"""GDELT market news-feed stream — bilingual eng/zho (display-only, exploratory).

Feeds the ``/news`` panel (``export_news_feed`` in
``scripts/export_terminal_data.py``). Bounded GDELT Doc 2.0 ``artlist``
queries per run return RECENT market-headline METADATA (title / url / domain /
seendate / language / sourcecountry) — the article itself stays at the
publisher; every panel row links out. No article text is stored, summarized or
fabricated.

**Bilingual lanes (2026-08-25 probe, one polite request each):**
  * **eng lane** — the v1 fixed quoted-phrase query
    (``("stock market" OR "S&P 500" OR "Federal Reserve") sourcelang:eng``).
  * **zho lane** — ``sourcelang:zho domainis:wallstreetcn.com`` (华尔街见闻).
    Probe evidence (2026-08-25, all cached under ``data/cache/probe_zho_*``):
    (a) ``domainis:wallstreetcn.com`` → **52 distinct articles / 2d**, every
    row ``language: "Chinese"``, genuine financial-newswire titles (earnings,
    macro, tech) — the ≥50/2d depth bar; (b) ``domainis:cls.cn`` (财联社) →
    **0 articles** — not in GDELT's crawl, honestly disclosed rather than
    worked around; (c) CJK *phrase* search is unusable — GDELT rejects it
    with ``"The specified phrase is too short."`` even for 3-4 char phrases
    (美股 / 股票 / 纳斯达克 / 美联储), so the domain-anchored query is the
    only probe-proven form; (d) ``sourcelang:zho`` syntax verified valid
    (empty-but-valid response when paired with a zero-coverage domain).
    The zho lane is therefore a **single-domain seed** — breadth is bounded
    by what GDELT crawls from wallstreetcn.com, disclosed in the panel
    methodology.
  * The two lanes merge into ONE stream; every row carries a ``lang`` field
    ("eng"/"zho") derived from the **API ``language`` field** ("English" →
    eng, "Chinese" → zho) with per-request provenance (which lane produced
    the row) as the fallback when the API field is empty — never guessed
    from title bytes. Cross-language dedup is NOT attempted (different
    articles); url-dedup handles accidental overlap naturally.

**Reuse (same reuse-first stance as ``news_sentiment_gdelt``):**
  * HTTP is routed through the existing module's ``HttpRequestPolicy``
    (``HostSpacingPolicy(min_interval=15.0)``). GDELT's documented minimum is
    ≥5s, but sustained cold pulls at 5s triggered HTTP 429 on the 2026-08-11 CI
    run; 15s clears the abuse throttle. The news-feed lane fires TWO requests
    per run (one per language, auto-spaced ≥15s apart by the shared policy).
  * Endpoint + User-Agent constants are imported from ``news_sentiment_gdelt``
    so the two GDELT consumers can never drift apart.

**Honest scope (NOT a research claim):**
  * The eng query is a FIXED market-headline phrase search. Phrases must be
    quoted — unquoted ``federal reserve`` matches the two words anywhere in
    an article and pulled junk (verified on the 2026-08-22 probe: a Nigerian
    job-scam story matched while every quoted-phrase hit was market
    coverage). The zho query is a FIXED domain-anchored search (see above).
  * ``seendate`` is GDELT's first-seen UTC timestamp (15-min resolution), the
    PIT visibility anchor for display.
  * Dedup key = exact URL. Syndicated copies of the same story on different
    domains are NOT collapsed — shown as separate rows, honestly counted.
  * Ranking is GDELT ``sort=datedesc`` (machine ordering, not editorial).
  * Coverage is whatever GDELT's crawl saw (English-biased; zho lane bounded
    to the seeded domain); gaps are gaps.
  * A single-lane fetch failure degrades honestly: the surviving lane merges,
    the failure is logged, and the failed lane's cached rows age out of the
    30-day window. Both lanes failing keeps the old cache untouched.
  * ``mode: exploratory`` — display lane only, never enters Phase-B/OOS.

Intake-rubric clearance (``docs/data-intake-gdelt-news-feed.md``):
  * **G1** — GDELT open data: URL/title/date/domain are facts (not
    copyrightable); article copyright stays with publishers (link-out only).
  * **G2** — ``seendate`` UTC recorded verbatim; snapshot_ts at collection.
  * **G3** — append-only stream; dedup key=url; reruns merge, never overwrite.
  * **G5** — display-only /news panel.
  * **G6** — fixed queries + machine ranking declared; syndication dupes kept;
    zho single-domain seed + zero-coverage of cls.cn disclosed.
  * **G7** — ≥15s host spacing (GDELT) + 2 bounded requests per run
    (≤200 records each).
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
from aionis.ingest.http_policy import HTTPStatusError
from aionis.ingest.news_sentiment_gdelt import (
    _GDELT_DOC_URL,
    _USER_AGENT,
    _policy,
)

log = structlog.get_logger()

# Quoted phrases are load-bearing (see module docstring): each alternative is a
# phrase match, so "Federal Reserve" cannot match scattered words.
DEFAULT_QUERY = '("stock market" OR "S&P 500" OR "Federal Reserve") sourcelang:eng'
# Chinese lane — domain-anchored because GDELT rejects CJK phrase search
# ("The specified phrase is too short", 2026-08-25 probe) and 财联社 (cls.cn)
# has ZERO GDELT coverage; wallstreetcn.com is the probe-proven financial
# newswire (52 distinct articles / 2d, all language="Chinese"). See the module
# docstring for the full probe evidence table.
DEFAULT_QUERY_ZHO = "sourcelang:zho domainis:wallstreetcn.com"
DEFAULT_TIMESPAN = "7d"  # rolling lookback; daily runs overlap + dedupe by url
MAX_RECORDS = 200  # GDELT artlist cap is 250; bounded below it per task budget
CACHE_KEEP_DAYS = 30  # the panel is a RECENT stream, not an archive
_COLUMNS = [
    "url", "title", "seendate", "domain", "language", "sourcecountry", "lang",
]
# The two (query, lang) lanes merged by collect_news_feed — one polite request
# each, ≥15s apart via the shared policy. ``lang`` is the per-request
# PROVENANCE fallback used when the API's own ``language`` field is empty.
_LANES: tuple[tuple[str, str], ...] = (
    (DEFAULT_QUERY, "eng"),
    (DEFAULT_QUERY_ZHO, "zho"),
)

_CACHE_NAME = "news_feed.parquet"


# --- pure parsers (hermetic-testable, no network) -----------------------------


# GDELT artlist emits full language NAMES ("English" / "Chinese" — verified on
# the committed eng panel and the 2026-08-25 zho probe); map to the two stream
# codes the panel contract pins.
_LANG_CODES = {"english": "eng", "chinese": "zho"}


def lang_code(api_language: object, provenance: str = "") -> str:
    """API ``language`` name → "eng"/"zho"; empty/unmapped → provenance code.

    Pure. Precedence follows the no-guessing rule: the API's own language
    field wins when present and recognized (never inferred from title bytes);
    otherwise the per-request provenance (which lane produced the row) labels
    the row; if neither is a known code, ``""`` (honest empty, never guessed).
    """
    code = _LANG_CODES.get(str(api_language or "").strip().lower())
    if code:
        return code
    prov = str(provenance or "").strip().lower()
    return prov if prov in ("eng", "zho") else ""


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


def parse_artlist(payload: dict, provenance_lang: str = "") -> list[dict]:
    """Parse a GDELT ``artlist`` JSON response into feed rows.

    Robust to: missing ``articles`` key, non-dict entries, missing fields
    (kept as ``""`` — honest empties, never fabricated). Entries without a
    ``url`` cannot be deduped or linked, so they are skipped and counted in
    the log — the dedup key is the identity contract. Every row carries a
    ``lang`` code derived via :func:`lang_code` (API language field first,
    ``provenance_lang`` fallback — which lane produced the request).
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
        language = str(a.get("language") or "").strip()
        rows.append({
            "url": url,
            "title": str(a.get("title") or "").strip(),
            "seendate": normalize_seendate(a.get("seendate")),
            "domain": str(a.get("domain") or "").strip(),
            "language": language,
            "sourcecountry": str(a.get("sourcecountry") or "").strip(),
            "lang": lang_code(language, provenance_lang),
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
    lang: str = "",
) -> list[dict]:
    """One GDELT Doc ``artlist`` GET through the ≥15s policy → parsed rows.

    ``sort=datedesc`` (machine ordering). ``lang`` is the per-request
    PROVENANCE code ("eng"/"zho") used only when the API's own ``language``
    field is empty on a row. Raises on HTTP error after the bounded retry —
    the caller decides to keep the old cache (CI step is continue-on-error).
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
    return parse_artlist(resp.json(), provenance_lang=lang)


# --- snapshot cache (idempotent parquet, dedup key=url) -----------------------


def load_cached_feed(cache_dir: Path | None = None) -> list[dict]:
    """Load the cached feed rows; ``[]`` if absent/corrupt (regenerable).

    Legacy pre-bilingual caches (no ``lang`` column) are backfilled with
    ``"eng"`` — that is per-request provenance, not a guess: every row in
    them was produced by the eng-only ``DEFAULT_QUERY`` era of this module.
    """
    fp = (cache_dir or Path("data/cache")) / _CACHE_NAME
    if not fp.exists():
        return []
    try:
        df = pd.read_parquet(fp)
        if "lang" not in df.columns:
            df = df.copy()
            df["lang"] = "eng"
        return df[_COLUMNS].to_dict("records")
    except (FileNotFoundError, KeyError, OSError):
        return []


def collect_news_feed(
    cache_dir: Path | None = None,
    timespan: str = DEFAULT_TIMESPAN,
) -> list[dict]:
    """Incremental bilingual fetch: eng + zho artlist pulls merged per run.

    Daily-run-cheap by design: 2 requests × ≤200 records (one per language
    lane, auto-spaced ≥15s apart by the shared GDELT policy); the 7d timespan
    overlaps the previous run and ``merge_feed`` dedupes by url, so reruns are
    idempotent and a missed day self-heals on the next run. Cross-language
    dedup is NOT attempted (different articles). Honest lane degradation: if
    exactly ONE lane fails after its bounded retry, its failure is logged,
    the surviving lane still merges and the failed lane's cached rows simply
    age out of the trailing window; if BOTH lanes fail the old cache is kept
    untouched (exception propagates). Writes ``data/cache/news_feed.parquet``
    (gitignored, regenerable) and returns the merged rows, newest first.
    """
    cache_dir = cache_dir or Path("data/cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    fp = cache_dir / _CACHE_NAME

    cached = load_cached_feed(cache_dir)
    new_rows: list[dict] = []
    failed: list[tuple[str, BaseException]] = []
    for lane_query, lane_lang in _LANES:
        try:
            new_rows.extend(
                fetch_articles(query=lane_query, timespan=timespan, lang=lane_lang)
            )
        except (requests.RequestException, HTTPStatusError) as exc:
            failed.append((lane_lang, exc))
            log.warning(
                "news_feed_lane_failed",
                lang=lane_lang,
                query=lane_query,
                error=repr(exc),
            )
    if len(failed) == len(_LANES):
        # Total failure: keep the old cache untouched (raise, as the
        # single-lane design did — the CI step is continue-on-error).
        raise failed[0][1]

    merged = merge_feed(
        cached, new_rows, keep_days=CACHE_KEEP_DAYS, today=date.today()
    )
    pd.DataFrame(merged, columns=_COLUMNS).to_parquet(fp, index=False)
    lang_counts: dict[str, int] = {}
    for r in merged:
        lang_counts[r.get("lang", "")] = lang_counts.get(r.get("lang", ""), 0) + 1
    log.info(
        "news_feed_snapshot_written",
        cached=len(cached),
        new=len(new_rows),
        merged=len(merged),
        lang_counts=lang_counts,
        window_days=CACHE_KEEP_DAYS,
        snapshot_ts=datetime.now().astimezone().isoformat(),
    )
    return merged
