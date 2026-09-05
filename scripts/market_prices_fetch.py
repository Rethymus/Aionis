"""VIX daily fetch for market context (display-only, exploratory).

Fetches VIX (CBOE Volatility Index) from 2016-01-01 → today via FRED ALFRED.
Polite (≥2s host spacing via ``_policy_get``), writes to cache file
``export_market_context`` consumes:
  - ``data/cache/alfred_VIXCLS.json``: VIX daily observations (FRED ALFRED format)

Display-only: this series powers the terminal's market-context sub-panel;
does NOT enter the research pipeline (no lookahead leakage). VIX is the
market-stress gauge shown alongside the equal-weight market index (which uses
the existing ``track_b_panel.parquet`` from the research pipeline).

Usage::

    uv run python scripts/market_prices_fetch.py

Re-run safely: FRED responses are cached; existing cache is reused on re-fetch.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from aionis.config import settings
from aionis.ingest.universe import _policy_get

# FRED API base URL for VIX (ALFRED format)
FRED_SERIES = "https://api.stlouisfed.org/fred/series/observations"

# Time window: Trump-era (2016) to today
START = "2016-01-01"
END = datetime.now().strftime("%Y-%m-%d")

# Output path (must match export_market_context expectations)
VIX_CACHE = Path("data/cache/alfred_VIXCLS.json")


def _tail_refresh(api_key: str, cache_path: Path, start: str, end: str) -> None:
    """Incrementally extend an existing VIX cache to ``end``.

    The cache-exists short-circuit froze the terminal's VIX at whatever day the
    cache was first written (observed: taco/market_context stuck at 2026-08-26
    while every other panel advanced). VIXCLS is a no-revision series (the PIT
    contract is the no-revision property, not vintage tracking), so appending
    tail observations is contract-safe: fetched values only ADD days, never
    rewrite history.
    """
    existing = json.loads(cache_path.read_text())
    obs = existing.get("observations", [])
    dated = [o for o in obs if o.get("value") not in (None, ".", "")]
    if not dated:
        return  # malformed/empty cache — fall through to a full refetch below
    last = max(o["date"] for o in dated)
    if last >= end:
        print(f"[market-prices] VIX cache already current through {last}", flush=True)
        return

    # Re-pull FROM the last cached day (dedup makes the overlap free) so a
    # cache written mid-day cannot strand a partial day as the terminal's "latest".
    print(f"[market-prices] VIX tail refresh {last}..{end} via FRED...", flush=True)
    params = {
        "series_id": "VIXCLS",
        "api_key": api_key,
        "file_type": "json",
        "observation_start": last,
        "observation_end": end,
    }
    response = _policy_get(FRED_SERIES, params=params, timeout=120)
    response.raise_for_status()
    data = response.json()
    fresh = data.get("observations", [])

    by_date = {o["date"]: o for o in obs}
    added = 0
    for o in fresh:
        if o.get("value") in (None, ".", ""):
            continue  # holidays arrive as "." — keep the cache's shape, add only real days
        if o["date"] not in by_date:
            by_date[o["date"]] = o
            added += 1
    merged = sorted(by_date.values(), key=lambda o: o["date"])
    existing["observations"] = merged
    cache_path.write_text(json.dumps(existing, indent=2))
    print(
        f"[market-prices] VIX tail merged: +{added} observations "
        f"→ {merged[-1]['date']} (total {len(merged)})",
        flush=True,
    )


def fetch_vix_fred(api_key: str, cache_path: Path, start: str = START, end: str = END) -> Path:
    """Fetch VIX daily observations via FRED, cache in ALFRED JSON format.

    Uses FRED's public API for VIXCLS (CBOE Volatility Index). Writes in the
    standard ALFRED format ``export_market_context`` expects: ``{observations:
    [{date, value, realtime_start, realtime_end}, ...]}``. Display-only; research
    pipeline uses PIT vintages.

    An existing cache is extended incrementally (tail refresh), not reused
    verbatim — the reuse-only path froze the terminal's VIX/taco panels at the
    cache's creation date.

    Args:
        api_key: FRED API key (from settings)
        cache_path: Path to write JSON cache
        start: Start date (YYYY-MM-DD)
        end: End date (YYYY-MM-DD)

    Returns:
        Path to the cached JSON file
    """
    if cache_path.exists():
        print(f"[market-prices] VIX cache exists: {cache_path}", flush=True)
        if not api_key:
            print("[market-prices] ERROR: FRED_API_KEY required for tail refresh", flush=True)
            raise ValueError("FRED_API_KEY not set")
        _tail_refresh(api_key, cache_path, start, end)
        return cache_path

    print(f"[market-prices] Fetching VIX {start}..{end} via FRED...", flush=True)

    url = f"{FRED_SERIES}"
    params = {
        "series_id": "VIXCLS",
        "api_key": api_key,
        "file_type": "json",
        "observation_start": start,
        "observation_end": end,
    }

    response = _policy_get(url, params=params, timeout=120)
    response.raise_for_status()
    data = response.json()

    # Cache the full FRED response (ALFRED format)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(data, indent=2))

    obs_count = len(data.get("observations", []))
    print(f"[market-prices] VIX cached: {obs_count} observations", flush=True)
    return cache_path


def main() -> None:
    """Fetch VIX data and cache it for the terminal market context.

    The market index (equal-weight US) uses existing track_b_panel.parquet from
    the research pipeline; only VIX needs daily refresh for the terminal's
    market-context display.
    """
    print(f"[market-prices] Window: {START} → {END}", flush=True)

    # Fetch VIX via FRED
    vix_path = fetch_vix_fred(
        api_key=settings.fred_api_key or "",
        cache_path=VIX_CACHE,
        start=START,
        end=END,
    )

    # Verify VIX cache
    if vix_path.exists():
        vix_data = json.loads(vix_path.read_text())
        obs = vix_data.get("observations", [])
        print(f"[market-prices] VIX: {len(obs)} daily observations", flush=True)
        if obs:
            print(f"[market-prices] VIX range: {obs[0]['date']} to {obs[-1]['date']}", flush=True)
    else:
        print("[market-prices] WARNING: VIX cache not written", flush=True)

    print("[market-prices] Complete.", flush=True)


if __name__ == "__main__":
    main()
