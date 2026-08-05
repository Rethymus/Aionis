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


# Daily FRED series whose full-history ALFRED request exceeds the 2000-vintage
# cap (vintages accrue daily) -> need per-year realtime slice (macro_dff pattern).
_DAILY_SERIES_PER_YEAR: set[str] = {"GS10", "BAA10Y"}
_REALTIME_START_YEAR = 2015  # one year before the 2016+ analysis window
_REALTIME_END_YEAR = 2026    # current year
_GENERIC_PAGE_LIMIT = 100_000


def _download_vintage_year_generic(
    series_id: str, fred_api_key: str, year: int,
) -> list[dict]:
    """One ALFRED observations page for ``series_id`` within a year realtime window.

    Generic form of ``macro_dff._download_dff_vintage_year`` (series_id parameterized).
    Per-year slice dodges FRED's 2000-vintage hard cap for daily series (GS10/BAA10Y).
    Current year is clamped to today (FRED rejects future realtime_end with 400).
    """
    from datetime import datetime, timezone

    from aionis.ingest.universe import _policy_get

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    realtime_end = f"{year}-12-31" if year < int(today[:4]) else today
    url = "https://api.stlouisfed.org/fred/series/observations"
    observations: list[dict] = []
    offset = 0
    while True:
        params = {
            "series_id": series_id,
            "api_key": fred_api_key,
            "file_type": "json",
            "realtime_start": f"{year}-01-01",
            "realtime_end": realtime_end,
            "limit": _GENERIC_PAGE_LIMIT,
            "offset": offset,
        }
        resp = _policy_get(url, params=params, timeout=60)
        resp.raise_for_status()
        rows = resp.json().get("observations", [])
        observations.extend(rows)
        offset += len(rows)
        if len(rows) < _GENERIC_PAGE_LIMIT:
            break
    return observations


def _fetch_daily_vintages_per_year(
    series_id: str, fred_api_key: str, cache_dir: Path,
) -> pd.DataFrame:
    """Daily-series ALFRED vintages via per-year slice; cache ``alfred_{id}.json``.

    Reuses the macro_dff per-year-slice pattern (generic series_id) +
    ``macro_dff._vintages_frame`` for payload→frame. Cache hit makes no HTTP call.
    """
    import json as _json

    from aionis.ingest.macro_dff import _vintages_frame

    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"alfred_{series_id}.json"
    if cache_file.exists():
        payload = _json.loads(cache_file.read_text())
        log.info("macro_headline_daily_cache_hit", series_id=series_id, path=str(cache_file))
        return _vintages_frame(payload)
    observations: list[dict] = []
    for year in range(_REALTIME_START_YEAR, _REALTIME_END_YEAR + 1):
        obs_year = _download_vintage_year_generic(series_id, fred_api_key, year)
        observations.extend(obs_year)
        log.info(
            "macro_headline_daily_slice_fetched",
            series_id=series_id, year=year, n_obs=len(obs_year),
        )
    payload = {"observations": observations}
    cache_file.write_text(_json.dumps(payload))
    log.info(
        "macro_headline_daily_cache_written",
        series_id=series_id, path=str(cache_file), n_obs=len(observations),
    )
    return _vintages_frame(payload)


def _fetch_with_polite_spacing(
    series_id: str,
    fred_api_key: str,
    cache_dir: Path,
    last_call_time: list[float],
) -> pd.DataFrame:
    """Fetch ALFRED vintages with ≥2s politeness; per-year slice for daily series."""
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
    if series_id in _DAILY_SERIES_PER_YEAR:
        vintages = _fetch_daily_vintages_per_year(series_id, fred_api_key, cache_dir)
    else:
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


# ---------------------------------------------------------------------------
# A2b: CN macro 2 (CPI monthly + GDP annual surprise) — GREEN verdict
# (WebSearch 2026-08-05: MKTGDPCNA646NWDB World Bank + CPALTT01CNM659N OECD,
# both ALFRED vintage; FRED non-commercial research OK). Reuses
# macro_surprise.first_print_changes (monthly CPI) + surprise_time_series +
# the macro_surprise_date_broadcast merge_asof-backward PIT rule. CN GDP is
# ANNUAL (first_print_changes is monthly-specific -> custom annual prior_ref),
# with ~10 releases 2015-2026 < Z_MIN=12 -> surprise_z likely NaN (data limit,
# disclosed; GDP column broadcasts NaN, LightGBM handles missing).
# ---------------------------------------------------------------------------


def _broadcast_surprise_z(
    ts: pd.DataFrame,
    as_of_dates: pd.DatetimeIndex,
    name: str,
) -> pd.Series:
    """Broadcast release-based ``surprise_z`` to ``as_of_dates`` (PIT backward).

    Reuses the macro_surprise_date_broadcast merge_asof rule: a release at r is
    knowable at every d >= r and never at d < r (last-known-macro-surprise, PIT).
    """
    head = (
        ts.dropna(subset=["surprise_z"])
        .sort_values(["pub_date", "ref_date"])
        .drop_duplicates("pub_date", keep="last")[["pub_date", "surprise_z"]]
        .sort_values("pub_date")
    )
    dates = pd.DatetimeIndex(as_of_dates).normalize()
    head["pub_date"] = head["pub_date"].dt.normalize()
    left = pd.DataFrame({"date": dates})
    right = head.rename(columns={"pub_date": "date"})
    merged = pd.merge_asof(left, right, on="date", direction="backward")
    return pd.Series(merged["surprise_z"].to_numpy(), index=dates, name=name)


def cn_cpi_surprise(
    as_of_dates: pd.DatetimeIndex,
    fred_api_key: str | None = None,
    cache_dir: Path | None = None,
) -> pd.Series:
    """CN CPI surprise (CPALTT01CNM659N, monthly, release-based).

    Reuses macro_surprise.first_print_changes (monthly prior_ref = ref - 1M)
    + surprise_time_series + _broadcast_surprise_z.
    """
    from aionis.features.macro_surprise import (
        fetch_alfred_vintages,
        first_print_changes,
        surprise_time_series,
    )

    if cache_dir is None:
        cache_dir = settings.data_dir / "cache"
    vintages = fetch_alfred_vintages("CPALTT01CNM659N", fred_api_key or "", cache_dir)
    changes = first_print_changes(vintages, change_kind="pct")  # monthly CPI, MoM pct
    ts = surprise_time_series(changes)
    out = _broadcast_surprise_z(ts, as_of_dates, "cn_cpi_surprise_zscore")
    log.info(
        "cn_cpi_surprise_built",
        n=len(out), n_valid=int(out.notna().sum()),
    )
    return out


def cn_gdp_surprise(
    as_of_dates: pd.DatetimeIndex,
    fred_api_key: str | None = None,
    cache_dir: Path | None = None,
) -> pd.Series:
    """CN GDP surprise (MKTGDPCNA646NWDB, ANNUAL, release-based).

    first_print_changes is monthly-specific (prior_ref = ref - 1M), so this
    builds an ANNUAL variant (prior_ref = ref - 1Y) inline, then reuses
    surprise_time_series + _broadcast_surprise_z. Annual releases ~10 over
    2015-2026 < Z_MIN=12 -> surprise_z likely NaN (data limit; the column
    broadcasts NaN, which LightGBM's native missing handling covers).
    """
    from aionis.features.macro_surprise import (
        fetch_alfred_vintages,
        surprise_time_series,
    )

    if cache_dir is None:
        cache_dir = settings.data_dir / "cache"
    vintages = fetch_alfred_vintages("MKTGDPCNA646NWDB", fred_api_key or "", cache_dir)
    if "ref_date" not in vintages.columns or vintages.empty:
        return pd.Series(
            [float("nan")] * len(as_of_dates),
            index=pd.DatetimeIndex(as_of_dates),
            name="cn_gdp_surprise_zscore",
        )
    fp_idx = vintages.groupby("ref_date")["realtime_start"].idxmin()
    fp = (
        vintages.loc[fp_idx]
        .rename(columns={"realtime_start": "pub_date", "value": "first_print"})
        .sort_values("pub_date")
        .reset_index(drop=True)
    )
    fp["prior_ref"] = fp["ref_date"] - pd.DateOffset(years=1)  # ANNUAL prior
    prior_pool = (
        vintages.rename(
            columns={
                "ref_date": "prior_ref",
                "realtime_start": "prior_pub",
                "value": "prior_value",
            }
        )
        .sort_values("prior_pub")
        .reset_index(drop=True)
    )
    merged = pd.merge_asof(
        fp,
        prior_pool,
        left_on="pub_date",
        right_on="prior_pub",
        by="prior_ref",
        direction="backward",
        allow_exact_matches=False,
    )
    merged["actual_change"] = (
        merged["first_print"] / merged["prior_value"] - 1.0
    ) * 100.0  # YoY pct
    ts = surprise_time_series(
        merged[["ref_date", "pub_date", "first_print", "prior_pub", "prior_value", "actual_change"]]
    )
    out = _broadcast_surprise_z(ts, as_of_dates, "cn_gdp_surprise_zscore")
    log.info(
        "cn_gdp_surprise_built",
        n=len(out), n_valid=int(out.notna().sum()),
        caveat="annual releases < Z_MIN -> likely NaN (data limit)",
    )
    return out


def fetch_cn_macro_2(
    as_of_dates: pd.DatetimeIndex,
    fred_api_key: str | None = None,
    cache_dir: Path | None = None,
) -> pd.DataFrame:
    """Fetch CN macro 2 (CPI monthly surprise + GDP annual surprise).

    Args:
        as_of_dates: Target dates (sorted ascending).
        fred_api_key: FRED API key (CN series via FRED; non-commercial research OK).
        cache_dir: Override default cache dir.

    Returns:
        DataFrame [cn_cpi_surprise_zscore, cn_gdp_surprise_zscore] indexed by as_of_dates.
        GDP column is likely NaN (annual releases < Z_MIN=12).
    """
    if fred_api_key is None:
        fred_api_key = settings.fred_api_key
    return pd.DataFrame(
        {
            "cn_cpi_surprise_zscore": cn_cpi_surprise(as_of_dates, fred_api_key, cache_dir),
            "cn_gdp_surprise_zscore": cn_gdp_surprise(as_of_dates, fred_api_key, cache_dir),
        }
    )


# ---------------------------------------------------------------------------
# A3: join macro_headline_6 to the joint panel (per-region, by date)
# ---------------------------------------------------------------------------

MACRO_HEADLINE_6: list[str] = [
    "term_spread_1y_10y_zscore",
    "credit_spread_zscore",
    "vix_surprise_zscore",
    "dff_surprise_zscore",
    "cn_cpi_surprise_zscore",
    "cn_gdp_surprise_zscore",
]


def join_macro_to_joint_panel(
    joint_panel: pd.DataFrame,
    fred_api_key: str | None = None,
    cache_dir: Path | None = None,
    date_col: str = "date",
    region_col: str = "region",
) -> pd.DataFrame:
    """A3: join US macro 4 + CN macro 2 to the joint panel (per-region, by date).

    US rows get the 4 US macro cols; CN rows get the 2 CN macro cols. Cross-region
    macro cols are NaN (e.g. CN rows NaN in US macro). The GDP col is NaN (annual
    releases < Z_MIN; data limit — disclosed). Reuses fetch_us_macro_4 +
    fetch_cn_macro_2. The macro values are already PIT (merge_asof backward inside
    each builder), so the per-region by-date map preserves PIT.

    Returns:
        Copy of joint_panel with the 6 MACRO_HEADLINE_6 columns added.
    """
    if fred_api_key is None:
        fred_api_key = settings.fred_api_key
    if cache_dir is None:
        cache_dir = settings.data_dir / "cache"
    as_of = pd.DatetimeIndex(sorted(joint_panel[date_col].unique())).normalize()
    us_macro = fetch_us_macro_4(as_of, fred_api_key, cache_dir)
    cn_macro = fetch_cn_macro_2(as_of, fred_api_key, cache_dir)
    out = joint_panel.copy()
    out[date_col] = pd.to_datetime(out[date_col]).dt.normalize()
    us_mask = out[region_col] == "us"
    cn_mask = out[region_col] == "cn"
    for col in us_macro.columns:
        out.loc[us_mask, col] = out.loc[us_mask, date_col].map(us_macro[col])
    for col in cn_macro.columns:
        out.loc[cn_mask, col] = out.loc[cn_mask, date_col].map(cn_macro[col])
    log.info(
        "macro_headline_6_joined",
        n_rows=len(out), n_us=int(us_mask.sum()), n_cn=int(cn_mask.sum()),
        macro_cols=MACRO_HEADLINE_6,
    )
    return out


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
