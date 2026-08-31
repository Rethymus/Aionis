"""BTS Freight Transportation Services Index (TSI) — first-party ingest (display-only).

TACO context: the reference site's TACO block is built on Trucking Activity Co.
satellite truck-count data — commercial, no license path (the original
exemption). The owner's boundary-revocation directive (2026-08-23) re-opened
the lane under the constraint that the replacement be a PUBLIC-DOMAIN
freight-activity series with the caliber difference honestly disclosed — a
degraded proxy, never masquerading as satellite data.

Main source (verified 2026-08-23): BTS's own Socrata distribution
``data.bts.gov/resource/bw6n-ddqk.json`` — dataset "Transportation Services
Index and Seasonally-Adjusted Transportation Data", attribution "Bureau of
Transportation Statistics" (U.S. DOT). ``tsi_freight`` = the monthly
seasonally-adjusted freight index (2000-01 →; 318 rows as of 2026-08-23,
latest month 2026-06 = 134.9). ``www.bts.gov`` HTML pages sit behind an
Akamai bot gate (HTTP 403 for non-browser clients — verified twice, 2026-08-23);
``data.bts.gov`` is BTS's programmatic distribution and serves openly.
FRED republishes the same index as ``TSIFRGHT`` (verified live 2026-08-23;
lags the BTS endpoint by ~1 month) — recorded in the 7-gate doc as the
verified mirror, not consumed here.

Auxiliary series: FRED ``CES4348400001`` (BLS CES "All Employees, Truck
Transportation", NAICS 484, monthly, thousands of persons) — the closest
public-domain truck-sector activity series to TACO's trucking focus. Fetched
through the approved shared FRED adapter (``universe._policy_get``), cached
with the same ``alfred_<SERIES>.json`` convention as ``vix.py``.

Revision honesty: unlike VIXCLS, the TSI IS revised (seasonal-adjustment
revisions of recent months + annual benchmark revisions). No no-revision
contract is claimed; the display panel always shows the current published
vintage and ``docs/data-intake-bts-tsi.md`` records this. Display lane ONLY:
nothing in this module may feed a research pipeline (live/current data,
anti-leakage constraint).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import structlog

from aionis.config import settings
from aionis.ingest.universe import _policy_get

log = structlog.get_logger()

# BTS Socrata (first-party programmatic distribution; www.bts.gov is Akamai-gated).
_BTS_RESOURCE_URL = "https://data.bts.gov/resource/bw6n-ddqk.json"
_BTS_QUERY = "?$select=obs_date,tsi_freight&$order=obs_date%20ASC&$limit=2000"
_BTS_SOURCE_URL = "https://data.bts.gov/Research-and-Statistics/Transportation-Services-Index-and-Seasonally-Adjus/bw6n-ddqk"

# FRED auxiliary: BLS CES truck-transportation employment (NAICS 484).
TRUCK_EMP_SERIES = "CES4348400001"
_FRED_OBSERVATIONS_URL = "https://api.stlouisfed.org/fred/series/observations"

_UA = {"User-Agent": "Aionis-Research/1.0 (educational; contact via repo)"}


def _cache_dir(cache_dir: Path | None = None) -> Path:
    d = cache_dir or settings.data_dir / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


# --- parsers (pure; hermetic-testable on plain dicts, no network) -------------


def parse_tsi_rows(rows: list[dict]) -> list[dict]:
    """Socrata rows → ``[{month, tsi}]`` ascending, gaps honestly dropped.

    Socrata serializes dates as ``2000-01-01T00:00:00.000`` and values as
    strings (``"134.9"``) or ``null`` (not-yet-published month); rows without
    a numeric ``tsi_freight`` are skipped, never guessed.
    """
    out: list[tuple[str, float]] = []
    for r in rows:
        obs = r.get("obs_date") or ""
        month = obs[:7]
        raw = r.get("tsi_freight")
        if len(month) != 7 or raw is None:
            continue
        try:
            out.append((month, float(raw)))
        except (TypeError, ValueError):
            continue
    return [{"month": m, "tsi": v} for m, v in sorted(out)]


def parse_fred_observations(payload: dict) -> list[dict]:
    """FRED observations envelope → ``[{month, value}]`` ascending.

    FRED serializes missing values as ``"."`` — dropped (same discipline as
    ``vix.py``). Returns ``[]`` when the payload carries no observations so
    callers can distinguish an honest empty series from a parse bug.
    """
    out: list[tuple[str, float]] = []
    for o in payload.get("observations", []):
        month = (o.get("date") or "")[:7]
        raw = o.get("value")
        if len(month) != 7 or raw in (None, ".", ""):
            continue
        try:
            out.append((month, float(raw)))
        except (TypeError, ValueError):
            continue
    return [{"month": m, "value": v} for m, v in sorted(out)]


# --- fetchers (cache-first; one polite GET per host per run) ------------------


def fetch_tsi_freight(
    *, cache_dir: Path | None = None, force: bool = False
) -> tuple[list[dict], dict]:
    """Full Freight TSI history from BTS Socrata → (parsed rows, meta).

    Cache-first: ``data/cache/bts_tsi_freight.json`` holds the raw envelope
    (fetched_at, dataset, n_rows, rows) and a hit makes no HTTP call. The
    fetch is ONE GET for the whole monthly history (dataset is a closed
    318-row series — no pagination, no per-month requests).
    """
    cdir = _cache_dir(cache_dir)
    cache_file = cdir / "bts_tsi_freight.json"
    if cache_file.exists() and not force:
        envelope = json.loads(cache_file.read_text(encoding="utf-8"))
        log.info("bts_tsi_cache_hit", path=str(cache_file), n=len(envelope.get("rows", [])))
        meta = {"fetched_at": envelope.get("fetched_at"), "n_rows": envelope.get("n_rows")}
        return parse_tsi_rows(envelope.get("rows", [])), meta

    response = _policy_get(_BTS_RESOURCE_URL + _BTS_QUERY, headers=_UA, timeout=60)
    response.raise_for_status()
    rows = response.json()
    if not rows:
        raise RuntimeError("BTS Socrata returned no tsi_freight observations")
    envelope = {
        "fetched_at": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
        "dataset": "bw6n-ddqk",
        "source": "U.S. Bureau of Transportation Statistics (data.bts.gov Socrata)",
        "n_rows": len(rows),
        "rows": rows,
    }
    cache_file.write_text(json.dumps(envelope), encoding="utf-8")
    parsed = parse_tsi_rows(rows)
    meta = {"fetched_at": envelope["fetched_at"], "n_rows": envelope["n_rows"]}
    log.info(
        "bts_tsi_fetched",
        n=len(parsed),
        first=parsed[0]["month"] if parsed else None,
        last=parsed[-1]["month"] if parsed else None,
    )
    return parsed, meta


def fetch_truck_employment(
    *, cache_dir: Path | None = None, force: bool = False
) -> list[dict]:
    """FRED ``CES4348400001`` (BLS CES truck employment) → ``[{month, value}]``.

    Cache-first with the ``alfred_<SERIES>.json`` convention shared with
    ``vix.py``; one polite GET through the approved FRED adapter on a miss
    (requires ``settings.fred_api_key``).
    """
    cdir = _cache_dir(cache_dir)
    cache_file = cdir / f"alfred_{TRUCK_EMP_SERIES}.json"
    if cache_file.exists() and not force:
        payload = json.loads(cache_file.read_text(encoding="utf-8"))
        log.info("truck_emp_cache_hit", path=str(cache_file))
    else:
        key = settings.fred_api_key
        if not key:
            raise RuntimeError(
                "FRED_API_KEY required to fetch CES4348400001 on a cache miss "
                "(set settings.fred_api_key / FRED_API_KEY in .env)"
            )
        response = _policy_get(
            _FRED_OBSERVATIONS_URL,
            params={
                "series_id": TRUCK_EMP_SERIES,
                "api_key": key,
                "file_type": "json",
            },
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        cache_file.write_text(json.dumps(payload), encoding="utf-8")
        log.info("truck_emp_fetched", n=len(payload.get("observations", [])))

    parsed = parse_fred_observations(payload)
    if not parsed:
        raise RuntimeError(f"FRED returned no numeric observations for {TRUCK_EMP_SERIES!r}")
    return parsed
