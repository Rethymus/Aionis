"""Display-only ALFRED macro series for the terminal's macro-driver sub-panel.

Fetches the three macro series that have NO research-pipeline owner — the
display-only additions that complete the President↔Fed dashboard:

  * ``DTWEXBGS`` — trade-weighted dollar index (the Fed-policy → dollar → market
    transmission channel).
  * ``T10Y2Y``   — 10Y minus 2Y Treasury spread (the yield-curve recession watch
    that constrains the Fed).
  * ``UNRATE``   — civilian unemployment rate (the max-employment mandate stock).

Each is cached to ``data/cache/alfred_{SID}.json`` in the SAME ``{observations}``
format as :mod:`aionis.ingest.macro_dff` and :mod:`aionis.features.macro_surprise`,
so the display exporter's ``_alfred_latest_series`` reads them identically.

Anti-leakage contract (this is the load-bearing part):
  * DISPLAY ONLY — these series never enter the research pipeline / OOS rank-IC /
    frozen config. They are terminal context, explicitly labelled "revised, NOT
    PIT-as-of" by the exporter.
  * The fetcher writes ONLY the three display-only series. It does NOT touch
    CPIAUCSL / PAYEMS / DFF (owned by ``macro_surprise`` / ``macro_dff``), so a
    research cache window is never shadowed by a shorter display window.
  * Latest-vintage (fully revised) values are what the public sees; the research
    pipeline's PIT first-print discipline is a separate path on separate series.

Politeness: uses ``_policy_get`` (≥2s host spacing + exponential backoff), the
same bound HTTP client as every other FRED/ALFRED call in the project.
"""
from __future__ import annotations

import json
from pathlib import Path

import structlog

log = structlog.get_logger()

# Display-only series for the macro-driver sub-panel (no research owner).
# Order matters for the runner log only.
DISPLAY_SERIES: tuple[str, ...] = ("DTWEXBGS", "T10Y2Y", "UNRATE")

# Realtime window starts one year before the analysis window (2016+) so the
# level/YoY charts have a clean left edge. Matches macro_dff's discipline.
_REALTIME_START_YEAR = 2015

# FRED page cap (matches macro_dff / macro_surprise).
_PAGE_LIMIT = 100_000


def _fetch_observations(
    fred_api_key: str,
    series_id: str,
    start_date: str = "2015-01-01",
) -> list[dict]:
    """Latest-vintage observations for ``series_id`` from ``start_date`` onward.

    Uses a plain ``observation_start`` query — NO realtime/vintage window. This
    returns the current public revised values directly (exactly what the display
    sub-panel wants) and sidesteps two failure modes that bite vintage (realtime)
    queries:

      * HTTP 400 for series without ALFRED vintage coverage (e.g. DTWEXBGS), and
      * FRED's 2000-vintage-per-request hard cap (which forces year-slicing for
        daily series under the vintage path — see ``macro_dff``).

    A plain observation query returns ONE row per date (no vintages), so even
    daily series stay well under the page cap in a single paginated call.
    """
    from aionis.ingest.universe import _policy_get

    url = "https://api.stlouisfed.org/fred/series/observations"
    observations: list[dict] = []
    offset = 0
    while True:
        params = {
            "series_id": series_id,
            "api_key": fred_api_key,
            "file_type": "json",
            "observation_start": start_date,
            "limit": _PAGE_LIMIT,
            "offset": offset,
        }
        resp = _policy_get(url, params=params, timeout=60)
        resp.raise_for_status()
        rows = resp.json().get("observations", [])
        observations.extend(rows)
        offset += len(rows)
        if len(rows) < _PAGE_LIMIT:
            break
    return observations


def fetch_display_series(
    fred_api_key: str,
    cache_dir: Path,
    series_id: str,
    *,
    force: bool = False,
) -> Path:
    """Fetch one display macro series and cache it.

    Args:
        fred_api_key: FRED API key.
        cache_dir: Cache directory (``data/cache``).
        series_id: FRED series id (e.g. ``"DTWEXBGS"``).
        force: If True, re-fetch even when a cache file exists.

    Returns:
        The cache file path written/read.

    Side effects:
        Writes ``<cache_dir>/alfred_{series_id}.json`` (``{observations: [...]}``
        — full FRED observation objects, latest-vintage readable by
        ``_alfred_latest_series``).
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"alfred_{series_id}.json"
    if cache_file.exists() and not force:
        log.info("macro_display_cache_hit", series_id=series_id, path=str(cache_file))
        return cache_file

    observations = _fetch_observations(
        fred_api_key,
        series_id,
        start_date=f"{_REALTIME_START_YEAR}-01-01",
    )
    log.info("macro_display_fetched", series_id=series_id, n_obs=len(observations))

    cache_file.write_text(json.dumps({"observations": observations}))
    log.info(
        "macro_display_cache_written",
        series_id=series_id,
        path=str(cache_file),
        n_obs=len(observations),
    )
    return cache_file


__all__ = ["DISPLAY_SERIES", "fetch_display_series"]
