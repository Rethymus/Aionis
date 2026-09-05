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
from collections.abc import Callable
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import requests
import structlog

from aionis.ingest.http_policy import HostSpacingPolicy, HttpRequestPolicy, RetryPolicy

log = structlog.get_logger()

# --- GDELT Doc 2.0 constants -------------------------------------------------
_GDELT_DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
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
_policy = HttpRequestPolicy(
    spacing=HostSpacingPolicy(min_interval=_GDELT_MIN_INTERVAL),
    retry=RetryPolicy(max_retries=2),
    retry_exceptions=(requests.RequestException,),
)

_CACHE_NAME = "gdelt_news_sentiment.json"


# --- pure parser (hermetic-testable, no network) -----------------------------


def parse_timelinetone(payload: dict) -> list[dict]:
    """Parse a GDELT timeline JSON response into ``[{date, tone?, volume?}]``.

    GDELT returns ``{"timeline": [{"series": "Average Tone", "data": [{"date",
    "value"}, ...]}, ...]}`` — ``timelinetone`` mode yields "Average Tone",
    ``timelinevol`` mode yields "Volume Intensity". This collapses the
    multi-series layout into one row per date.

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
            elif "Volume" in name or "Article" in name:
                row["volume"] = float(val)
    return sorted(by_date.values(), key=lambda r: r["date"])


def aggregate_monthly(rows: list[dict]) -> list[dict]:
    """Aggregate fine-grained GDELT timeline rows into monthly tone + volume.

    Each input row is ``{date: "YYYYMMDDTTTT" | "YYYYMMDD", tone?, volume?}``.
    Output: ``[{month: "YYYY-MM", tone: mean, volume: mean|None, n: count}, ...]``
    sorted ascending. Months with no tone values are dropped (volume-only months
    add no sentiment signal). ``tone`` is the mean of daily tones that month
    (cross-sectional aggregate of article tone); ``volume`` is the mean of the
    daily Volume Intensity values (GDELT's normalized 0-100 attention index — a
    MEAN, because summing an index is meaningless). A chunk whose volume query
    failed carries no volume observations → ``volume: None`` (NOT 0: a failed
    query is a missing observation, not a zero-attention month — and the merge
    must not overwrite a previously-fetched real volume with it).
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
        vols = g["volume"].dropna() if "volume" in g else pd.Series([], dtype=float)
        if tones.empty:
            continue
        parts.append(
            {
                "month": f"{month[:4]}-{month[4:6]}",
                "tone": round(float(tones.mean()), 3),
                "volume": round(float(vols.mean()), 1) if not vols.empty else None,
                "n": int(len(tones)),
            }
        )
    parts.sort(key=lambda r: r["month"])
    return parts


def merge_series(cached: list[dict], new_rows: list[dict]) -> list[dict]:
    """Merge cached + newly-fetched monthly rows; dedupe by month (new wins).

    One exception to new-wins: a new row with ``volume: None`` (its volume
    query failed — a missing observation) inherits the cached row's volume so a
    tone-only refresh cannot erase a previously-fetched attention reading.
    """
    by_month: dict[str, dict] = {r["month"]: r for r in cached}
    for r in new_rows:
        old = by_month.get(r["month"])
        if (
            old is not None
            and r.get("volume") is None
            and old.get("volume") is not None
        ):
            r = {**r, "volume": old["volume"]}
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


def _gdelt_timeline(query_string: str, mode: str) -> dict:
    """One GDELT Doc timeline GET through the ≥15s policy. Returns parsed JSON.

    No ``timelinestep`` — let GDELT pick its granularity; ``aggregate_monthly``
    collapses any granularity (daily/weekly) to monthly by YYYYMM prefix.
    """
    url = f"{_GDELT_DOC_URL}?query={query_string}&mode={mode}&format=json"
    headers = {"User-Agent": _USER_AGENT}

    def operation() -> requests.Response:
        return requests.get(url, headers=headers, timeout=60)

    resp = _policy.request(_GDELT_DOC_URL, operation)
    resp.raise_for_status()
    return resp.json()


def fetch_tone_series(
    start: date, end: date, on_chunk: Callable[[list[dict]], None] | None = None
) -> list[dict]:
    """Fetch monthly tone+attention via GDELT timelines, chunked quarterly.

    Per chunk two queries are made: ``timelinetone`` (Average Tone — the
    sentiment signal) and ``timelinevol`` (Volume Intensity — GDELT's
    normalized 0-100 news-attention index). ``timelinetone`` alone carries NO
    volume series, which is why the panel's volume signal sat at a meaningless
    constant 0 for its whole history. A failed/empty volume query degrades the
    chunk to tone-only (volume stays 0 there) — tone never blocks on volume.

    Resilient: per-chunk failures are logged + skipped (partial series > crash),
    mirroring the per-day-403 resilience in ``stakes_13d_daily_index``. One
    query path (theme:ECON_STOCKMARKET) — no runtime fallback; a broken theme
    code is a one-line ``DEFAULT_THEME`` fix, not a backup layer.

    If ``on_chunk`` is given, it's called with each chunk's monthly rows right
    after they're parsed+aggregated, so the caller can persist incrementally:
    a CI timeout mid-backfill keeps the chunks already fetched (root-cause #3
    — the cold pull exceeds the 20-min step-cap; without per-chunk writes the
    cache stayed empty and news_sentiment never surfaced).

    Args:
        start/end: inclusive start, exclusive end (date window to cover).
            ``start`` is clamped to ``DOC_API_EARLIEST`` (2017-04).
        on_chunk: optional callback ``(chunk_monthly_rows) -> None`` invoked
            after each successfully fetched chunk.

    Returns:
        List of monthly ``{month, tone, volume, n}`` dicts, ascending.
    """
    chunks = _chunk_quarters(max(start, DOC_API_EARLIEST), end)
    all_monthly: list[dict] = []
    for cs, ce in chunks:
        qs = _build_query_string(cs, ce)
        try:
            payload = _gdelt_timeline(qs, "timelinetone")
        except Exception as exc:  # bounded retry already applied; skip chunk
            log.warning(
                "gdelt_chunk_skip",
                start=cs.isoformat(),
                end=ce.isoformat(),
                error=str(exc)[:160],
            )
            continue
        try:
            vol_payload = _gdelt_timeline(qs, "timelinevol")
        except Exception as exc:  # tone survives a volume outage — degrade honestly
            vol_payload = {}
            log.warning(
                "gdelt_volume_chunk_skip",
                start=cs.isoformat(),
                end=ce.isoformat(),
                error=str(exc)[:160],
            )
        combined = {
            "timeline": (payload.get("timeline") or []) + (vol_payload.get("timeline") or [])
        }
        rows = parse_timelinetone(combined)
        # Aggregate per-chunk (quarters are calendar-aligned → months never
        # split across chunks, so per-chunk == full aggregation). Lets the
        # caller checkpoint after each chunk for timeout-safe persistence.
        chunk_monthly = aggregate_monthly(rows)
        all_monthly.extend(chunk_monthly)
        log.info("gdelt_chunk_ok", start=cs.isoformat(), n=len(rows))
        if on_chunk is not None:
            on_chunk(chunk_monthly)
    log.info(
        "gdelt_fetch_done",
        n_months=len(all_monthly),
        start=chunks[0][0].isoformat() if chunks else None,
    )
    return all_monthly


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


def _month_add(month: str, k: int = 1) -> str:
    """``"YYYY-MM"`` + k months (pure calendar arithmetic)."""
    y, m = (int(x) for x in month.split("-"))
    total = y * 12 + (m - 1) + k
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def _gap_backfill_windows(cached: list[dict]) -> list[tuple[date, date]]:
    """Exact refetch windows for interior gaps in the cached monthly series.

    The forward-only incremental cursor (``_next_fetch_start``) never revisits
    history, so a chunk that failed once (GDELT 429/outage) stayed missing
    forever — the committed panel had seven hole-runs (e.g. 2023-07→2024-01,
    2025-06→2025-10). This finds the missing months between the first and last
    cached months and returns one month-aligned ``[start, end)`` window per
    contiguous missing run — exact coverage, one query per run (quarter
    alignment would re-pull already-cached months around short holes). Pure →
    hermetic-testable.
    """
    if len(cached) < 2:
        return []
    months = [r["month"] for r in cached]
    present = set(months)
    windows: list[tuple[date, date]] = []
    run_start: str | None = None
    cursor = months[0]
    end_month = months[-1]
    while cursor < end_month:
        if cursor in present:
            if run_start is not None:
                windows.append((_month_to_date(run_start), _month_to_date(cursor)))
                run_start = None
        elif run_start is None:
            run_start = cursor
        cursor = _month_add(cursor)
    if run_start is not None:
        windows.append((_month_to_date(run_start), _month_to_date(end_month)))
    return windows


def _month_to_date(month: str) -> date:
    y, m = (int(x) for x in month.split("-"))
    return date(y, m, 1)


def _write_cache_snapshot(
    series: list[dict], cache_path: Path, archive: str = ""
) -> None:
    """Write (overwrite) the cache snapshot atomically-ish; pure side effect.

    Centralizes the snapshot shape so both the per-chunk checkpoint writer and
    the final write use the same schema. ``archive`` is only meaningful for the
    final write (the raw-row sha256 archive of *new* rows).
    """
    snapshot = {
        "source": (
            "GDELT Doc 2.0 timelines (timelinetone + timelinevol; "
            "theme:ECON_STOCKMARKET, country:US)"
        ),
        "query": f"theme:{DEFAULT_THEME} country:{DEFAULT_COUNTRY}",
        "volume_unit": "attention_index_0_100",
        "coverage_start": series[0]["month"] if series else None,
        "coverage_end": series[-1]["month"] if series else None,
        "snapshot_ts": datetime.now(timezone.utc).isoformat(),
        "archive": archive,
        "n_months": len(series),
        "series": series,
    }
    cache_path.write_text(json.dumps(snapshot, indent=2))


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
    cache_path = cache_dir / _CACHE_NAME

    cached = load_cached_series(cache_dir)
    fetch_start = _next_fetch_start(cached, cold_start=max(start, DOC_API_EARLIEST))
    # Windows to fetch: the forward tail (incremental delta — fetch_tone_series
    # quarter-chunks it internally) + exact refetches for interior gap runs (a
    # chunk lost to a past 429/outage used to stay missing forever — the
    # forward-only cursor never revisits history). Gap runs are interior by
    # construction, so they never overlap the tail.
    windows: list[tuple[date, date]] = []
    if fetch_start < end:
        windows.append((fetch_start, end))
    windows.extend(_gap_backfill_windows(cached))
    new_rows: list[dict] = []
    if not windows:
        log.info("gdelt_cache_fresh", cached_months=len(cached))
        merged = list(cached)
    else:
        # Per-chunk checkpoint: merge + write cache after EACH fetched chunk so a
        # CI timeout mid-backfill keeps what's already fetched. Root-cause #3 of
        # '新闻情绪数据没有体现': the cold pull (38 chunks × ≥15s + 429 backoff)
        # exceeded the 20-min step-cap, collect_news_sentiment never finished,
        # and the cache was never written — so the export saw an empty cache and
        # news_sentiment stayed 'forward_only' even though chunks succeeded.
        # Use a dict holder because Python closures can't rebind enclosing locals
        # via `=`.
        state: dict = {"merged": list(cached)}

        def _on_chunk(chunk_rows: list[dict]) -> None:
            state["merged"] = merge_series(state["merged"], chunk_rows)
            _write_cache_snapshot(state["merged"], cache_path)
            log.info(
                "gdelt_chunk_checkpoint",
                n_months=len(state["merged"]),
                new_in_chunk=len(chunk_rows),
            )

        for ws, we in windows:
            new_rows.extend(fetch_tone_series(ws, we, on_chunk=_on_chunk))

    # Final merge uses fetch_tone_series's full return (the checkpoint callback
    # is insurance — it fires per-chunk, but the authoritative new_rows here is
    # the complete delta). This also covers the case where a test stubs
    # fetch_tone_series without invoking on_chunk.
    merged = merge_series(cached, new_rows)

    archive_name = _archive_raw(new_rows, cache_dir) if new_rows else ""
    _write_cache_snapshot(merged, cache_path, archive=archive_name)
    log.info(
        "gdelt_snapshot_written",
        n_months=len(merged),
        new_rows=len(new_rows),
        archive=archive_name or None,
    )
    snapshot = json.loads(cache_path.read_text())
    return snapshot
