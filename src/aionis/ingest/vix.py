"""CBOE VIX daily close (FRED ``VIXCLS``) — the first risk-premium main-line feature.

VIX is the cleanest policy / risk-premium proxy in the market-driver framework.
FRED republishes it as ``VIXCLS``; ALFRED (FRED's archival twin) gives as-of
vintages, so the value knowable at date t can be reconstructed with no revision
leak. This module is exploratory / Phase-C prep — it does NOT enter Phase B.

Two accessors:
  * :func:`fetch_vix` — the realized daily series via ``pandas_datareader`` (the
    current view; for inspection / Phase-C scaffolding).
  * :func:`vix_as_of` — the PIT-safe accessor for feature alignment. It mirrors
    :mod:`aionis.features.macro_surprise`: ALFRED vintages downloaded from the
    ``fred/series/observations`` endpoint (``realtime_start`` = publication
    date), then a ``merge_asof(direction='backward')`` so the value at date d is
    the latest vintage published on or before d. A VIX close released on day d is
    therefore visible at d (the day's own close is knowable by end of session)
    but NOT at d-1; dates before the first release are NaN.

Divergence from macro_surprise's prior-month join: that one uses
``allow_exact_matches=False`` because a prior-month revision republished on the
release day itself must NOT be used. Here the join target IS the day's own
close, so exact matches are kept (the default) — day-d's VIX close is knowable
by end of session d. Everything else (ALFRED endpoint, paging, vintage frame
shape, missing-value ``"."`` drop) is reused verbatim from macro_surprise.

License: FRED public terms (permissive); ``pandas-datareader`` is BSD.
Raw fetch cached at ``data/cache/``; one ``data_ingest`` row is appended to
``runs/ledger.jsonl`` on first fetch (``mode: exploratory``).
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import structlog

from aionis.config import settings

log = structlog.get_logger()

_VIX_SERIES = "VIXCLS"
_ALFRED_OBS_URL = "https://api.stlouisfed.org/fred/series/observations"
_REALTIME_START = "1990-01-01"  # VIXCLS history begins 1990-01-02
_REALTIME_END = "9999-12-31"
_PAGE_LIMIT = 100_000  # FRED hard cap per request; page with offset past it


def _cache_dir(cache_dir: Path | None = None) -> Path:
    d = cache_dir or settings.data_dir / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ledger_path() -> Path:
    return settings.runs_dir / "ledger.jsonl"


def _append_ingest_ledger(payload: dict) -> Path:
    """Append one ``data_ingest`` row to ``runs/ledger.jsonl`` (append-only).

    Matches ``reporting.run_log.log_run``'s append discipline: one JSON line,
    UTC ``ts`` at second precision, never overwrite."""
    ledger = _ledger_path()
    ledger.parent.mkdir(parents=True, exist_ok=True)
    row = {"ts": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"), **payload}
    with ledger.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, default=str) + "\n")
    log.info("vix_ingest_logged", ledger=str(ledger), dataset=payload.get("dataset"))
    return ledger


# --- realized series (current view; for inspection / Phase-C scaffolding) ------


def _to_vix_series(dates, values) -> pd.Series:
    """Canonical VIX Series: index = NYSE session date (midnight), value = VIX
    close. One construction shared by the fetch and cache-read paths so they are
    byte-identical. ``pd.DatetimeIndex`` accepts both a Series (cache read) and a
    DatetimeIndex (fresh fetch) and, unlike ``.normalize()``, does not infer a
    spurious ``Day`` frequency on consecutive synthetic dates."""
    s = pd.Series(values, index=pd.DatetimeIndex(pd.to_datetime(dates)), name="vix")
    s.index.name = "date"
    return s


def fetch_vix(
    start: str,
    end: str,
    *,
    cache_dir: Path | None = None,
    force: bool = False,
) -> pd.Series:
    """Daily VIX close (FRED ``VIXCLS``), PIT-correct via ALFRED as-of join.

    Returns a Series indexed by NYSE session date (FRED ``observation_date`` is
    the trading session), value = VIX close. The raw fetch is cached at
    ``data/cache/vix_cls.parquet`` and sha256-pinned; a cache hit makes no fetch.
    The ``data_ingest`` ledger row is appended ONLY on an actual fetch.

    ``pandas_datareader`` reads ``FRED_API_KEY`` from the environment, so it is
    seeded from ``settings.fred_api_key`` before the call when set.
    """
    cdir = _cache_dir(cache_dir)
    pq = cdir / "vix_cls.parquet"
    if pq.exists() and not force:
        df = pd.read_parquet(pq)
        s = _to_vix_series(df["date"], df["vix"].to_numpy())
        log.info("vix_cache_hit", path=str(pq), n=len(s))
        return s

    import pandas_datareader as pdr

    key = settings.fred_api_key
    if key:
        os.environ.setdefault("FRED_API_KEY", key)
    raw = pdr.get_data_fred(_VIX_SERIES, start=start, end=end)[_VIX_SERIES].dropna()
    if raw.empty:
        raise RuntimeError(f"FRED returned no VIXCLS observations for [{start}, {end}]")
    s = _to_vix_series(raw.index, raw.to_numpy())
    pd.DataFrame({"date": s.index, "vix": s.to_numpy()}).to_parquet(pq)
    digest = _sha256(pq)
    _append_ingest_ledger(
        {
            "event": "data_ingest",
            "dataset": _VIX_SERIES,
            "source": "FRED/ALFRED",
            "license": "FRED public terms",
            "as_of": datetime.now(tz=timezone.utc).date().isoformat(),
            "range": [str(s.index.min().date()), str(s.index.max().date())],
            "n_rows": int(len(s)),
            "data_sha256": digest,
            "mode": "exploratory",
        }
    )
    log.info(
        "vix_fetched",
        n=len(s),
        date_min=str(s.index.min().date()),
        date_max=str(s.index.max().date()),
        sha256=digest,
    )
    return s


# --- PIT as-of accessor (mirrors macro_surprise's ALFRED as-of join) ----------


def _download_vix_vintages(fred_api_key: str) -> dict:
    """Full ``VIXCLS`` vintage archive (paged; FRED caps rows per request).

    Reuses macro_surprise's ``_download_vintages`` paging exactly."""
    import requests

    observations: list[dict] = []
    offset = 0
    while True:
        params = {
            "series_id": _VIX_SERIES,
            "api_key": fred_api_key,
            "file_type": "json",
            "realtime_start": _REALTIME_START,
            "realtime_end": _REALTIME_END,
            "limit": _PAGE_LIMIT,
            "offset": offset,
        }
        resp = requests.get(_ALFRED_OBS_URL, params=params, timeout=60)
        resp.raise_for_status()
        rows = resp.json().get("observations", [])
        observations.extend(rows)
        offset += len(rows)
        if len(rows) < _PAGE_LIMIT:
            break
    log.info("vix_vintages_downloaded", series_id=_VIX_SERIES, n_obs=len(observations))
    return {"observations": observations}


def fetch_vix_vintages(cache_dir: Path | None = None) -> pd.DataFrame:
    """Vintage frame ``[ref_date, realtime_start, value]`` for ``VIXCLS`` from
    cache or ALFRED. Missing values (FRED serializes them as ``"."``) are dropped.

    Cached as ``alfred_VIXCLS.json`` so a rerun makes no HTTP call (same
    convention as :func:`aionis.features.macro_surprise.fetch_alfred_vintages`).
    """
    cdir = _cache_dir(cache_dir)
    cache_file = cdir / f"alfred_{_VIX_SERIES}.json"
    if cache_file.exists():
        payload = json.loads(cache_file.read_text())
        log.info("vix_vintages_cache_hit", path=str(cache_file))
    else:
        key = settings.fred_api_key
        if not key:
            raise RuntimeError(
                "FRED_API_KEY required to fetch VIXCLS vintages "
                "(set settings.fred_api_key / FRED_API_KEY in .env)"
            )
        payload = _download_vix_vintages(key)
        cache_file.write_text(json.dumps(payload))
        log.info("vix_vintages_cache_written", path=str(cache_file))

    rows = payload.get("observations", [])
    if not rows:
        raise RuntimeError(f"ALFRED returned no observations for {_VIX_SERIES!r}")
    df = (
        pd.DataFrame(
            {
                "ref_date": pd.to_datetime([r["date"] for r in rows]),
                "realtime_start": pd.to_datetime([r["realtime_start"] for r in rows]),
                "value": pd.to_numeric([r.get("value") for r in rows], errors="coerce"),
            }
        )
        .dropna(subset=["value"])
        .reset_index(drop=True)
    )
    if df.empty:
        raise RuntimeError(f"ALFRED observations for {_VIX_SERIES!r} are all missing values")
    return df


def vix_as_of(as_of_dates: pd.DatetimeIndex, *, cache_dir: Path | None = None) -> pd.Series:
    """VIX value knowable at each date (latest vintage published on or before it).

    The PIT-safe accessor for feature alignment — mirrors
    :mod:`aionis.features.macro_surprise`'s ALFRED as-of discipline. A VIX close
    released on day d is visible at d (the day's own close is knowable by end of
    session d) but NOT at d-1; dates before the first release are NaN.

    ``as_of_dates`` should be sorted (the feature-alignment session calendar is);
    ``merge_asof`` requires a sorted left key and raises clearly otherwise.
    """
    vintages = fetch_vix_vintages(cache_dir)
    # Sort by publication date then reference date so a same-publication-date
    # catch-up (two ref days released at once) keeps the most recent ref day;
    # collapse to one value per publication date for the as-of join.
    v = (
        vintages.sort_values(["realtime_start", "ref_date"])
        .drop_duplicates("realtime_start", keep="last")[["realtime_start", "value"]]
        .rename(columns={"realtime_start": "d"})
    )
    left = pd.DataFrame({"d": pd.DatetimeIndex(as_of_dates).normalize()})
    merged = pd.merge_asof(left, v, on="d", direction="backward")
    out = pd.Series(merged["value"].to_numpy(), index=left["d"], name="vix")
    out.index.name = "date"
    return out
