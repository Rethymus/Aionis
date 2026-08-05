"""US macro headline 4 features — point-in-time daily surprise series.

Surprise definition for daily series (term_spread, credit_spread, vix, dff):
    **Trailing z-score (63-day window, min 21, clip ±5)**

Rationale: This adapts the monthly statistical expectation pattern from
`macro_surprise.py` (Balduzzi-Elton-Green 2001, Bauer-Swanson) to daily
frequency macro series. 63 trading days ≈ 3 months provides a reasonable
adaptive baseline for daily financial data; min 21 ensures sufficient
history for stable estimation; clipping at ±5 prevents fat-tailed
outliers from dominating the design matrix.

Alternative (first-difference z-score) was considered but rejected:
first-difference amplifies high-frequency noise without adding signal
for term/credit spreads where the level itself is the economic signal
(recession indicator, credit risk premium).

All series use as-of merge discipline from `macro_dff.py`:
    value_at(d) = latest first print with realtime_start STRICTLY BEFORE d
(allow_exact_matches=False). FRED publishes daily values at ~16:30 ET
— AFTER equity close — so same-day prints become knowable only on d+1.

4 features:
1. term_spread_1y_10y = GS10 − TB3MS (yield curve slope; recession signal)
2. credit_spread = BAA10Y − GS10 (Baa corporate spread; credit risk)
3. vix_surprise = VIXCLS z-score (volatility surprise; cached, no vintage tracking)
4. dff_surprise = DFF Δ z-score (Fed funds surprise; cached, reuse macro_dff)

Raw ALFRED JSON cached at `data/cache/alfred_{series_id}.json`; cache hit
makes no HTTP call. ≥2s politeness between FRED API calls enforced.

Phase C confirmatory spec #48 — US 4 headline + CN 2 exploratory.
"""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import structlog

from aionis.config import settings

log = structlog.get_logger()

# Daily surprise parameters (adapted from monthly Z_WINDOW/Z_MIN/Z_CLIP)
DAILY_SURPRISE_WINDOW = 63  # trailing days for mean/std (≈3 months)
DAILY_SURPRISE_MIN = 21  # min history for valid surprise
DAILY_Z_CLIP = 5.0  # |z| cap

# FRED politeness: ≥2s between calls (per CLAUDE.md rules)
_FRED_CALL_SPACING = 2.0


def _fetch_with_polite_spacing(
    series_id: str,
    fred_api_key: str,
    cache_dir: Path,
    last_call_time: list[float],
) -> pd.DataFrame:
    """Fetch ALFRED vintages with ≥2s politeness between FRED calls."""
    # Reuse macro_surprise.fetch_alfred_vintages via import to avoid code dup
    from aionis.features.macro_surprise import fetch_alfred_vintages

    now = time.monotonic()
    elapsed = now - last_call_time[0]
    if elapsed < _FRED_CALL_SPACING:
        sleep_time = _FRED_CALL_SPACING - elapsed
        log.info(
            "macro_headline_polite_sleep",
            series_id=series_id,
            sleep_s=sleep_time,
        )
        time.sleep(sleep_time)
    vintages = fetch_alfred_vintages(series_id, fred_api_key, cache_dir)
    last_call_time[0] = time.monotonic()
    return vintages


def _first_prints_asof(vintages: pd.DataFrame) -> pd.DataFrame:
    """Extract first prints per ref_date (minimum realtime_start).

    Returns [realtime_start, value] sorted by realtime_start for as-of merge.
    """
    if "ref_date" not in vintages.columns or "realtime_start" not in vintages.columns:
        raise ValueError("vintages must have columns ref_date / realtime_start / value")
    fp_idx = vintages.groupby("ref_date")["realtime_start"].idxmin()
    first_prints = (
        vintages.loc[fp_idx, ["realtime_start", "value"]]
        .sort_values("realtime_start")
        .reset_index(drop=True)
    )
    return first_prints


def _daily_asof_series(
    as_of_dates: pd.DatetimeIndex,
    vintages: pd.DataFrame,
    name: str,
) -> pd.Series:
    """PIT as-of daily series at each of as_of_dates (strictly-before rule).

    Args:
        as_of_dates: Target dates (sorted ascending).
        vintages: [ref_date, realtime_start, value] from fetch_alfred_vintages.
        name: Output series name.

    Returns:
        Date-indexed Series; NaN before the first strictly-prior print.
        Uses merge_asof with allow_exact_matches=False: same-day prints
        (16:30 ET release) are NOT knowable at the morning close.
    """
    first_prints = _first_prints_asof(vintages)
    dates = pd.DatetimeIndex(as_of_dates).normalize()
    left = pd.DataFrame({"d": dates})
    right = first_prints.rename(columns={"realtime_start": "d"})
    merged = pd.merge_asof(
        left,
        right,
        on="d",
        direction="backward",
        allow_exact_matches=False,  # strictly before d
    )
    out = pd.Series(
        merged["value"].to_numpy(dtype=float),
        index=dates,
        name=name,
    )
    return out


def _daily_zscore_series(
    series: pd.Series,
    window: int = DAILY_SURPRISE_WINDOW,
    min_periods: int = DAILY_SURPRISE_MIN,
    clip: float = DAILY_Z_CLIP,
) -> pd.Series:
    """Trailing z-score for a daily series (adapted from surprise_time_series).

    Returns z-score Series with same index as input.
    z(d) = (value(d) - trailing_mean(d-1)) / trailing_std(d-1), clipped to ±clip.

    The shift(1) before rolling ensures the window at d contains only values
    strictly before d (no lookahead). NaN when insufficient history.
    """
    prior_values = series.shift(1)
    rolling_mean = prior_values.rolling(window, min_periods=min_periods).mean()
    rolling_std = prior_values.rolling(window, min_periods=min_periods).std(ddof=1)
    z = ((series - rolling_mean) / rolling_std).clip(-clip, clip)
    return z.rename(f"{series.name}_zscore")


def term_spread_1y_10y(
    as_of_dates: pd.DatetimeIndex,
    fred_api_key: str,
    cache_dir: Path | None = None,
) -> pd.Series:
    """10y−3mo term spread (GS10 − TB3MS) daily as-of z-score.

    Fetches GS10 and TB3MS via ALFRED (cached), computes as-of spread,
    then applies daily trailing z-score (63-day window, min 21, clip ±5).

    Args:
        as_of_dates: Target dates (sorted ascending).
        fred_api_key: FRED API key.
        cache_dir: Override default cache dir (defaults to settings.data_dir/cache).

    Returns:
        Date-indexed Series `term_spread_1y_10y_zscore`.
    """
    if cache_dir is None:
        cache_dir = settings.data_dir / "cache"

    last_call = [time.monotonic() - _FRED_CALL_SPACING]  # allow first call immediately

    # Fetch GS10
    gs10_vintages = _fetch_with_polite_spacing("GS10", fred_api_key, cache_dir, last_call)
    gs10_asof = _daily_asof_series(as_of_dates, gs10_vintages, "gs10")

    # Fetch TB3MS (≥2s after GS10)
    tb3ms_vintages = _fetch_with_polite_spacing("TB3MS", fred_api_key, cache_dir, last_call)
    tb3ms_asof = _daily_asof_series(as_of_dates, tb3ms_vintages, "tb3ms")

    # Compute spread
    spread = (gs10_asof - tb3ms_asof).rename("term_spread_1y_10y")

    # Z-score
    return _daily_zscore_series(spread)


def credit_spread(
    as_of_dates: pd.DatetimeIndex,
    fred_api_key: str,
    cache_dir: Path | None = None,
) -> pd.Series:
    """Baa−10y credit spread (BAA10Y − GS10) daily as-of z-score.

    Fetches BAA10Y via ALFRED (cached), reuses GS10 from term_spread_1y_10y,
    computes as-of spread, then applies daily trailing z-score.

    Args:
        as_of_dates: Target dates (sorted ascending).
        fred_api_key: FRED API key.
        cache_dir: Override default cache dir.

    Returns:
        Date-indexed Series `credit_spread_zscore`.
    """
    if cache_dir is None:
        cache_dir = settings.data_dir / "cache"

    last_call = [time.monotonic() - _FRED_CALL_SPACING]

    # Fetch GS10 (needed for spread)
    gs10_vintages = _fetch_with_polite_spacing("GS10", fred_api_key, cache_dir, last_call)
    gs10_asof = _daily_asof_series(as_of_dates, gs10_vintages, "gs10")

    # Fetch BAA10Y (≥2s after GS10)
    baa10y_vintages = _fetch_with_polite_spacing("BAA10Y", fred_api_key, cache_dir, last_call)
    baa10y_asof = _daily_asof_series(as_of_dates, baa10y_vintages, "baa10y")

    # Compute spread
    spread = (baa10y_asof - gs10_asof).rename("credit_spread")

    # Z-score
    return _daily_zscore_series(spread)


def vix_surprise(
    as_of_dates: pd.DatetimeIndex,
    cache_dir: Path | None = None,
) -> pd.Series:
    """VIX surprise (z-score of first-differenced VIXCLS series).

    VIXCLS follows a no-revision contract — the published value is final,
    so vintage tracking is NOT needed (unlike GS10/TB3MS/BAA10Y). However,
    we still use the cached ALFRED file for consistency with other features.

    Computes: as-of VIXCLS level → daily change → trailing z-score
    (63-day window, min 21, clip ±5).

    Args:
        as_of_dates: Target dates (sorted ascending).
        cache_dir: Override default cache dir.

    Returns:
        Date-indexed Series `vix_surprise_zscore`.
    """
    if cache_dir is None:
        cache_dir = settings.data_dir / "cache"

    from aionis.features.macro_surprise import fetch_alfred_vintages

    # VIXCLS cached — no politeness needed (no HTTP call on cache hit)
    vix_vintages = fetch_alfred_vintages("VIXCLS", "", cache_dir)
    vix_asof = _daily_asof_series(as_of_dates, vix_vintages, "vixcls")

    # First difference
    vix_change = vix_asof.diff().rename("vix_change")

    # Z-score
    return _daily_zscore_series(vix_change)


def dff_surprise(
    as_of_dates: pd.DatetimeIndex,
    cache_dir: Path | None = None,
) -> pd.Series:
    """DFF surprise (z-score of first-differenced Fed funds rate).

    Reuses the as-of DFF series from `macro_dff.py` (already has strict
    allow_exact_matches=False discipline). Computes ΔDFF → trailing z-score
    (63-day window, min 21, clip ±5).

    Args:
        as_of_dates: Target dates (sorted ascending).
        cache_dir: Override default cache dir.

    Returns:
        Date-indexed Series `dff_surprise_zscore`.
    """
    if cache_dir is None:
        cache_dir = settings.data_dir / "cache"

    from aionis.ingest.macro_dff import dff_daily_changes, fetch_dff_vintages

    # DFF cached — reuses macro_dff fetch
    dff_vintages = fetch_dff_vintages("", cache_dir)
    dff_change = dff_daily_changes(as_of_dates, dff_vintages)

    # Z-score
    return _daily_zscore_series(dff_change)


def fetch_us_macro_4(
    as_of_dates: pd.DatetimeIndex,
    fred_api_key: str | None = None,
    cache_dir: Path | None = None,
) -> pd.DataFrame:
    """Fetch all 4 US macro headline features as a single DataFrame.

    Args:
        as_of_dates: Target dates (sorted ascending).
        fred_api_key: FRED API key (defaults to settings.fred_api_key).
        cache_dir: Override default cache dir.

    Returns:
        DataFrame with columns [term_spread_1y_10y_zscore, credit_spread_zscore,
        vix_surprise_zscore, dff_surprise_zscore], indexed by as_of_dates.

    Raises:
        ValueError: If fred_api_key is missing and not in settings.
    """
    if fred_api_key is None:
        fred_api_key = settings.fred_api_key
    if fred_api_key is None:
        raise ValueError("FRED_API_KEY required for US macro fetch (not in .env)")

    if cache_dir is None:
        cache_dir = settings.data_dir / "cache"

    results = {}
    results["term_spread_1y_10y_zscore"] = term_spread_1y_10y(as_of_dates, fred_api_key, cache_dir)
    results["credit_spread_zscore"] = credit_spread(as_of_dates, fred_api_key, cache_dir)
    results["vix_surprise_zscore"] = vix_surprise(as_of_dates, cache_dir)
    results["dff_surprise_zscore"] = dff_surprise(as_of_dates, cache_dir)

    df = pd.DataFrame(results)
    log.info(
        "us_macro_4_fetched",
        n_dates=len(df),
        n_valid_term=df["term_spread_1y_10y_zscore"].notna().sum(),
        n_valid_credit=df["credit_spread_zscore"].notna().sum(),
        n_valid_vix=df["vix_surprise_zscore"].notna().sum(),
        n_valid_dff=df["dff_surprise_zscore"].notna().sum(),
    )
    return df


__all__ = [
    "term_spread_1y_10y",
    "credit_spread",
    "vix_surprise",
    "dff_surprise",
    "fetch_us_macro_4",
    "DAILY_SURPRISE_WINDOW",
    "DAILY_SURPRISE_MIN",
    "DAILY_Z_CLIP",
]
