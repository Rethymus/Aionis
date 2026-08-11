"""GDELT-based macro news-sentiment series (display-only, exploratory).

Feeds the ``news_sentiment`` theme in ``export_themes``. Aggregates GDELT Doc 2.0
``timelinetone`` (a pre-computed general-purpose lexicon tone, −100…+100) over
US English-language market/economy news into a **monthly** tone + volume series.

**Reuse (reuse-first; this is the load-bearing value of the gdeltdoc package):**
  * ``gdeltdoc.Filters.query_string`` (MIT, ``gdeltdoc==1.12.0``) constructs the
    GDELT query string (date formatting + theme/country syntax). We do NOT use
    the library's HTTP path — it fires bare ``requests.get`` with no host
    spacing, which violates GDELT's ≥5s rule.
  * HTTP is routed through the project's ``HttpRequestPolicy`` with
    ``HostSpacingPolicy(min_interval=15.0)`` — GDELT's documented minimum is
    ≥5s, but sustained cold pulls (dozens of quarterly chunks) at 5s triggered
    HTTP 429 on the 2026-08-11 CI run; 15s clears the abuse throttle.

**Honest scope (NOT a research claim):**
  * GDELT tone is a **general-purpose lexicon** score (not finance-domain); it
    conflates "bad world news" with "bad market news". It is a regime/stress
    proxy, NOT a per-stock signal.
  * Coverage starts 2017-04-01 (GDELT Doc 2.0 API debut); pre-2017 would require
    the GKG 2.0 endpoint (different format, out of scope here).
  * ``mode: exploratory`` — does NOT enter confirmatory / Phase-B.

Intake-rubric clearance (``docs/data-intake-rubric.md``):
  * **G1** — gdeltdoc MIT; GDELT data = facts/events + computed aggregates (not
    copyrightable); attribution in the panel methodology string.
  * **G2** — ``snapshot_ts`` UTC recorded; the series is the value known at
    collection time.
  * **G3** — each raw pull sha256-archived to ``data/cache/gdelt_raw_<ts>_<digest>.json``
    and is immutable; GDELT tone is revision-stable after ~2 weeks.
  * **G5** — ``mode: exploratory``; display-only theme layer.
  * **G6** — coverage biased to English/Western press (declared scope limit).
  * **G7** — ≥5s host spacing (GDELT requirement) + bounded exponential retry.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import requests
import structlog

from aionis.ingest.http_policy import HostSpacingPolicy, HttpRequestPolicy, RetryPolicy

log = structlog.get_logger()

# --- GDELT Doc 2.0 constants -------------------------------------------------
_GDELT_DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
_GDELT_MIN_INTERVAL = 5.0  # GDELT demands ≥5s (stricter than project 2s default)
_USER_AGENT = (
    "Aionis-research/0.1 (point-in-time quant research; contact: aionis@example.com)"
)
# GDELT Doc 2.0 API debuted 2017-04 — honest coverage start.
DOC_API_EARLIEST = date(2017, 4, 1)

# Default query: US English-language stock-market news. ``ECON_STOCKMARKET`` is
# the valid GDELT GKG theme code ("Any discussion of a stockmarket, NYSE, FTSE,
# etc." — per the official GDELT GKG Category List). The earlier ``ECON_MKT``
# was NOT a valid code → matched 0 articles → empty tone series (root cause of
# the 2026-08-11 CI run returning n_months=0). If this theme ever yields empty
# again (code retired/changed), fix is a one-line change here — no runtime
# fallback, per KISS.
DEFAULT_THEME = "ECON_STOCKMARKET"
DEFAULT_COUNTRY = "US"

# Module-private policy: ≥15s spacing + bounded retry, GDELT-specific. GDELT's
# documented minimum is ≥5s, but sustained cold pulls (38 quarterly chunks at
# 5s) triggered HTTP 429 on the 2026-08-11 CI cold run — 15s clears the abuse
# throttle. Incremental daily runs do only 1-4 chunks (recent quarters), so the
# warm-path cost is minimal.
_GDELT_MIN_INTERVAL = 15.0

# Module-private policy: ≥15s spacing + bounded retry, GDELT-specific.
_policy = HttpRequestPolicy(
    spacing=HostSpacingPolicy(min_interval=_GDELT_MIN_INTERVAL),
    retry=RetryPolicy(max_retries=2),
    retry_exceptions=(requests.RequestException,),
)

_CACHE_NAME = "gdelt_news_sentiment.json"


# --- pure parser (hermetic-testable, no network) -----------------------------


def parse_timelinetone(payload: dict) -> list[dict]:
    """Parse a GDELT ``timelinetone`` JSON response into ``[{date, tone?, volume?}]``.

    GDELT returns ``{"timeline": [{"series": "Average Tone", "data": [{"date",
    "value"}, ...]}, {"series": "Article Volume", "data": [...]}]}``. This
    collapses the multi-series layout into one row per date.

    Robust to: missing ``timeline`` key, empty data, missing values, either
    series arriving alone. Dates are returned as GDELT emits them
    (``YYYYMMDDTTTT`` for daily, or ``YYYYMM`` for monthly) — the caller
    normalizes.
    """
    timeline = payload.get("timeline") or []
    if not timeline:
        return []
    by_date: dict[str, dict] = {}
    for series in timeline:
        name = str(series.get("series", ""))
        for pt in series.get("data", []):
            d = pt.get("date")
            val = pt.get("value")
            if not d or val is None:
                continue  # skip dateless points + value-less points (no empty rows)
            row = by_date.setdefault(d, {"date": d})
            if "Tone" in name:
                row["tone"] = float(val)
            elif "Volume" in name:
                row["volume"] = int(val)
    return sorted(by_date.values(), key=lambda r: r["date"])


def aggregate_monthly(rows: list[dict]) -> list[dict]:
    """Aggregate fine-grained GDELT timeline rows into monthly tone + volume.

    Each input row is ``{date: "YYYYMMDDTTTT" | "YYYYMMDD", tone?, volume?}``.
    Output: ``[{month: "YYYY-MM", tone: mean, volume: sum, n: count}, ...]`` sorted
    ascending. Months with no tone values are dropped (volume-only months add no
    sentiment signal). ``tone`` is the mean of daily tones that month (cross-
    sectional aggregate of article tone); ``volume`` is the sum of daily article
    counts (total articles that month).
    """
    if not rows:
        return []
    df = pd.DataFrame(rows)
    # GDELT date is YYYYMMDDTTTT (12 digits, 15-min granularity) or YYYYMMDD (8).
    # Take the first 6 digits → YYYYMM.
    df["month"] = df["date"].astype(str).str[:6]
    parts: list[dict] = []
    for month, g in df.groupby("month"):
        tones = g["tone"].dropna() if "tone" in g else pd.Series([], dtype=float)
        vols = g["volume"].dropna() if "volume" in g else pd.Series([], dtype=int)
        if tones.empty:
            continue
        parts.append(
            {
                "month": f"{month[:4]}-{month[4:6]}",
                "tone": round(float(tones.mean()), 3),
                "volume": int(vols.sum()) if not vols.empty else 0,
                "n": int(len(tones)),
            }
        )
    parts.sort(key=lambda r: r["month"])
    return parts


def merge_series(cached: list[dict], new_rows: list[dict]) -> list[dict]:
    """Merge cached + newly-fetched monthly rows; dedupe by month (new wins)."""
    by_month: dict[str, dict] = {r["month"]: r for r in cached}
    for r in new_rows:
        by_month[r["month"]] = r
    return sorted(by_month.values(), key=lambda r: r["month"])


def _chunk_quarters(start: date, end: date) -> list[tuple[date, date]]:
    """Yield ``[start, end)`` quarterly ``[inclusive_start, exclusive_end)`` windows.

    Pure. Aligns to calendar-quarter boundaries so chunks tile cleanly.
    """
    if start >= end:
        return []
    chunks: list[tuple[date, date]] = []
    year, month = start.year, ((start.month - 1) // 3) * 3 + 1
    cur = date(year, month, 1)
    while cur < end:
        q = (cur.month - 1) // 3 + 1
        next_q_year = cur.year + (1 if q == 4 else 0)
        next_q_month = (q % 4) * 3 + 1
        next_start = date(next_q_year, next_q_month, 1)
        chunk_end = min(next_start, end)
        chunks.append((cur, chunk_end))
        cur = next_start
    return chunks


# --- network (routed through the polite policy) ------------------------------


def _build_query_string(start: date, end: date) -> str:
    """Build the GDELT Doc query string via ``gdeltdoc.Filters`` (MIT, reused).

    Filters handles date formatting (``YYYYMMDD000000``) and the theme/country
    syntax — the load-bearing reuse. We do NOT use the library's HTTP path.
    """
    from gdeltdoc import Filters  # MIT

    return Filters(
        start_date=start.strftime("%Y-%m-%d"),
        end_date=end.strftime("%Y-%m-%d"),
        theme=DEFAULT_THEME,
        country=DEFAULT_COUNTRY,
    ).query_string


def _gdelt_timeline_tone(query_string: str) -> dict:
    """One GDELT Doc ``timelinetone`` GET through the ≥5s policy. Returns parsed JSON.

    No ``timelinestep`` — let GDELT pick its granularity; ``aggregate_monthly``
    collapses any granularity (daily/weekly) to monthly by YYYYMM prefix.
    """
    url = f"{_GDELT_DOC_URL}?query={query_string}&mode=timelinetone&format=json"
    headers = {"User-Agent": _USER_AGENT}

    def operation() -> requests.Response:
        return requests.get(url, headers=headers, timeout=60)

    resp = _policy.request(_GDELT_DOC_URL, operation)
    resp.raise_for_status()
    return resp.json()


def fetch_tone_series(start: date, end: date) -> list[dict]:
    """Fetch monthly tone+volume via GDELT ``timelinetone``, chunked quarterly.

    Resilient: per-chunk failures are logged + skipped (partial series > crash),
    mirroring the per-day-403 resilience in ``stakes_13d_daily_index``. One
    query path (theme:ECON_STOCKMARKET) — no runtime fallback; a broken theme
    code is a one-line ``DEFAULT_THEME`` fix, not a backup layer.

    Args:
        start/end: inclusive start, exclusive end (date window to cover).
        ``start`` is clamped to ``DOC_API_EARLIEST`` (2017-04).

    Returns:
        List of monthly ``{month, tone, volume, n}`` dicts, ascending.
    """
    chunks = _chunk_quarters(max(start, DOC_API_EARLIEST), end)
    all_rows: list[dict] = []
    for cs, ce in chunks:
        qs = _build_query_string(cs, ce)
        try:
            payload = _gdelt_timeline_tone(qs)
            rows = parse_timelinetone(payload)
        except Exception as exc:  # bounded retry already applied; skip chunk
            log.warning(
                "gdelt_chunk_skip",
                start=cs.isoformat(),
                end=ce.isoformat(),
                error=str(exc)[:160],
            )
            continue
        all_rows.extend(rows)
        log.info("gdelt_chunk_ok", start=cs.isoformat(), n=len(rows))
    monthly = aggregate_monthly(all_rows)
    log.info(
        "gdelt_fetch_done",
        n_months=len(monthly),
        start=chunks[0][0].isoformat() if chunks else None,
    )
    return monthly


# --- snapshot + archive ------------------------------------------------------


def _archive_raw(rows: list[dict], cache_dir: Path) -> str:
    """sha256-archive the raw aggregated rows; return the archive filename."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    blob = json.dumps(rows, sort_keys=True).encode()
    digest = hashlib.sha256(blob).hexdigest()[:16]
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"gdelt_raw_{ts}_{digest}.json"
    path.write_text(json.dumps(rows, indent=2))
    return path.name


def load_cached_series(cache_dir: Path) -> list[dict]:
    """Load the cached monthly series; ``[]`` if absent/corrupt."""
    path = cache_dir / _CACHE_NAME
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text()).get("series", [])
    except (json.JSONDecodeError, KeyError, TypeError):
        return []


def _next_fetch_start(cached: list[dict], cold_start: date) -> date:
    """The first day to fetch given the cached series' latest month."""
    if not cached:
        return cold_start
    last = cached[-1]["month"]  # "YYYY-MM"
    ly, lm = (int(x) for x in last.split("-"))
    nm = lm + 1
    ny = ly + (1 if nm > 12 else 0)
    nm = ((nm - 1) % 12) + 1
    return date(ny, nm, 1)


def collect_news_sentiment(
    start: date | None = None,
    end: date | None = None,
    cache_dir: Path | None = None,
) -> dict:
    """Incremental fetch: cold-start backfill OR 1-quarter delta on subsequent runs.

    Daily-CI-cheap by design: the first run backfills quarterly chunks (one-time,
    ~36 queries × ≥5s ≈ 3 min); subsequent runs fetch only from the cached last
    month + 1 → today (typically one chunk, ~5s).

    Returns the snapshot dict (also written to ``data/cache/gdelt_news_sentiment.json``).
    """
    start = start or DOC_API_EARLIEST
    end = end or date.today()
    cache_dir = cache_dir or Path("data/cache")
    cache_dir.mkdir(parents=True, exist_ok=True)

    cached = load_cached_series(cache_dir)
    fetch_start = _next_fetch_start(cached, cold_start=max(start, DOC_API_EARLIEST))
    if fetch_start >= end:
        log.info("gdelt_cache_fresh", cached_months=len(cached))
        new_rows: list[dict] = []
    else:
        new_rows = fetch_tone_series(fetch_start, end)

    merged = merge_series(cached, new_rows)
    archive_name = _archive_raw(new_rows, cache_dir) if new_rows else ""
    snapshot_ts = datetime.now(timezone.utc).isoformat()

    snapshot = {
        "source": "GDELT Doc 2.0 timelinetone (theme:ECON_STOCKMARKET, country:US)",
        "query": f"theme:{DEFAULT_THEME} country:{DEFAULT_COUNTRY}",
        "coverage_start": merged[0]["month"] if merged else None,
        "coverage_end": merged[-1]["month"] if merged else None,
        "snapshot_ts": snapshot_ts,
        "archive": archive_name,
        "n_months": len(merged),
        "series": merged,
    }
    (cache_dir / _CACHE_NAME).write_text(json.dumps(snapshot, indent=2))
    log.info(
        "gdelt_snapshot_written",
        n_months=len(merged),
        new_rows=len(new_rows),
        archive=archive_name or None,
    )
    return snapshot
