"""Regime macro layer (Track C) — 5-line composite state.

This module builds the macro component of Track C's regime_state feature:
  1. vix — VIX level (risk-on/risk-off)
  2. credit_spread — BAA corporate bond yield minus AAA (default risk)
  3. term_spread — 10-year Treasury minus 1-year Treasury (yield curve)
  4. dff_surprise — ALFRED vintage DFF surprise (monetary policy shock)
  5. EPU — China Economic Policy Uncertainty (EXPLORATORY — if permissive source exists)

Each series is fetched from FRED (real, polite ≥2s spacing), standardized via
past-only rolling z-score (shift(1) before rolling), then equal-weight averaged
into a single daily macro regime series.

Anti-leakage (binding):
  * DFF: ALFRED vintage, strictly-before rule (allow_exact_matches=False)
  * VIX: unrevised no-revision contract (VIXCLS via vix_as_of)
  * Credit/term: FRED series (note: can be revised; snapshot+sha256 at fetch)
  * z-score windows: past-only (shift(1) before every rolling)

Boundary: this layer produces the z-scored equal-weight macro series ONLY. The
final TACO expanding-as-of σ normalization + 3-layer composite (macro + price +
sentiment) is a SEPARATE opus task (Track C config #46).

H6 determinism: all synthetic tests use seed=0; real fetch is deterministic
by cache hit (snapshot+sha256 pinned).
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import structlog

from aionis.config import settings
from aionis.ingest.macro_dff import dff_as_of_levels, fetch_dff_vintages
from aionis.ingest.universe import _policy_get
from aionis.ingest.vix import vix_as_of

log = structlog.get_logger()

# FRED series IDs
_CREDIT_BAA = "BAA"  # Moody's Seasoned Baa Corporate Bond Yield
_CREDIT_AAA = "AAA"  # Moody's Seasoned Aaa Corporate Bond Yield
_TERM_10Y = "DGS10"  # Market Yield on U.S. Treasury Securities at 10-Year Constant Maturity
_TERM_1Y = "DGS1"   # Market Yield on U.S. Treasury Securities at 1-Year Constant Maturity

# FRED API endpoints
_FRED_OBS_URL = "https://api.stlouisfed.org/fred/series/observations"

# Standardization parameters
_Z_WINDOW = 252  # trading days (~1 year) for rolling z-score
_Z_MIN = 126     # minimum periods (~6 months)
_Z_CLIP = 5.0    # |z| cap (matches macro_surprise)


def _sha256(path: Path) -> str:
    """Compute SHA256 of a file (cache pinning)."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _cache_dir(cache_dir: Path | None = None) -> Path:
    """Get cache directory, creating if needed."""
    d = cache_dir or settings.data_dir / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _fetch_fred_series(
    series_id: str,
    start: str,
    end: str,
    fred_api_key: str,
    cache_dir: Path | None = None,
) -> pd.Series:
    """Fetch a FRED observation series via the shared polite adapter.

    Cached at data/cache/{series_id}.parquet with sha256 pinning. A cache hit
    makes no HTTP call. Uses _policy_get (≥2s spacing enforced upstream).

    Args:
        series_id: FRED series ID (e.g., "BAA", "DGS10")
        start: Observation start date (ISO)
        end: Observation end date (ISO)
        fred_api_key: FRED API key
        cache_dir: Override cache directory

    Returns:
        Date-indexed Series (index = observation_date, name = series_id)

    Raises:
        RuntimeError: If fetch returns no observations
    """
    cdir = _cache_dir(cache_dir)
    pq = cdir / f"{series_id}.parquet"

    # Cache hit
    if pq.exists():
        df = pd.read_parquet(pq)
        s = pd.Series(df["value"].to_numpy(), index=pd.DatetimeIndex(df["date"]), name=series_id)
        log.info("fred_cache_hit", series_id=series_id, path=str(pq), n=len(s))
        return s

    # Cache miss — fetch
    params = {
        "series_id": series_id,
        "api_key": fred_api_key,
        "file_type": "json",
        "observation_start": start,
        "observation_end": end,
    }
    resp = _policy_get(_FRED_OBS_URL, params=params, timeout=60)
    resp.raise_for_status()
    rows = resp.json().get("observations", [])

    if not rows:
        raise RuntimeError(f"FRED returned no observations for {series_id!r}")

    # Parse: drop missing values ("."), convert dates/values
    dates = []
    values = []
    for r in rows:
        val = r.get("value")
        if val is None or val == ".":
            continue
        dates.append(pd.to_datetime(r["date"]))
        values.append(float(val))

    s = pd.Series(values, index=pd.DatetimeIndex(dates), name=series_id)

    # Cache write
    pd.DataFrame({"date": s.index, "value": s.to_numpy()}).to_parquet(pq)
    digest = _sha256(pq)
    log.info(
        "fred_fetched",
        series_id=series_id,
        n=len(s),
        date_min=str(s.index.min().date()),
        date_max=str(s.index.max().date()),
        sha256=digest,
    )

    return s


def rolling_zscore(
    series: pd.Series,
    window: int = _Z_WINDOW,
    min_periods: int = _Z_MIN,
) -> pd.Series:
    """Past-only rolling z-score (anti-leakage: shift(1) before rolling).

    The z-score at index t uses only data dated < t (strictly past). This is
    enforced by shift(1) before every rolling operation: the window at t is
    computed over series[t-1], series[t-2], ..., not including series[t] itself.

    Args:
        series: Input series (date-indexed)
        window: Rolling window size (default 252 trading days)
        min_periods: Minimum periods required (default 126)

    Returns:
        Z-scored series (same index, clipped to ±_Z_CLIP)
    """
    # Shift by 1 to enforce strictly-past window
    shifted = series.shift(1)
    rolling_mean = shifted.rolling(window, min_periods=min_periods).mean()
    rolling_std = shifted.rolling(window, min_periods=min_periods).std(ddof=1)

    z = (series - rolling_mean) / rolling_std
    z_clipped = z.clip(-_Z_CLIP, _Z_CLIP)
    z_clipped.name = f"{series.name}_z" if series.name else "z"
    return z_clipped


def fetch_vix_level(as_of_dates: pd.DatetimeIndex, cache_dir: Path | None = None) -> pd.Series:
    """Fetch VIX level (VIXCLS) via the PIT-safe vix_as_of accessor.

    Returns VIX close knowable at each date (latest vintage ≤ date). VIXCLS
    is unrevised (no-revision contract), so the current series IS the PIT truth.

    Args:
        as_of_dates: Dates to align to (sorted ascending)
        cache_dir: Override cache directory

    Returns:
        Date-indexed Series named "vix"
    """
    vix = vix_as_of(as_of_dates, cache_dir=cache_dir)
    vix.name = "vix"
    log.info("vix_level_fetched", n=len(vix), n_valid=int(vix.notna().sum()))
    return vix


def fetch_credit_spread(
    start: str,
    end: str,
    fred_api_key: str,
    cache_dir: Path | None = None,
) -> pd.Series:
    """Fetch credit spread (BAA - AAA) from FRED.

    Args:
        start: Observation start date
        end: Observation end date
        fred_api_key: FRED API key
        cache_dir: Override cache directory

    Returns:
        Date-indexed Series named "credit_spread"
    """
    baa = _fetch_fred_series(_CREDIT_BAA, start, end, fred_api_key, cache_dir)
    aaa = _fetch_fred_series(_CREDIT_AAA, start, end, fred_api_key, cache_dir)

    # Align and compute spread (outer join -> NaN where either side missing)
    combined = pd.DataFrame({"baa": baa, "aaa": aaa})
    spread = combined["baa"] - combined["aaa"]
    spread.name = "credit_spread"
    log.info(
        "credit_spread_fetched",
        n=len(spread),
        n_valid=int(spread.notna().sum()),
    )
    return spread


def fetch_term_spread(
    start: str,
    end: str,
    fred_api_key: str,
    cache_dir: Path | None = None,
) -> pd.Series:
    """Fetch term spread (10y - 1y Treasury) from FRED.

    Matches Track C config term_spread_1y_10y.

    Args:
        start: Observation start date
        end: Observation end date
        fred_api_key: FRED API key
        cache_dir: Override cache directory

    Returns:
        Date-indexed Series named "term_spread"
    """
    dgs10 = _fetch_fred_series(_TERM_10Y, start, end, fred_api_key, cache_dir)
    dgs1 = _fetch_fred_series(_TERM_1Y, start, end, fred_api_key, cache_dir)

    # Align and compute spread
    combined = pd.DataFrame({"dgs10": dgs10, "dgs1": dgs1})
    spread = combined["dgs10"] - combined["dgs1"]
    spread.name = "term_spread"
    log.info(
        "term_spread_fetched",
        n=len(spread),
        n_valid=int(spread.notna().sum()),
    )
    return spread


def fetch_dff_surprise_series(
    as_of_dates: pd.DatetimeIndex,
    fred_api_key: str,
    cache_dir: Path | None = None,
) -> pd.Series:
    """Fetch DFF surprise (ALFRED vintage) for the macro layer.

    Reuses macro_dff infrastructure: fetch ALFRED vintages, build as-of levels,
    then compute surprise via first-difference shock. This is the SURPRISE, not
    the level — as specified in Track C config.

    Args:
        as_of_dates: Dates to align to
        fred_api_key: FRED API key
        cache_dir: Override cache directory

    Returns:
        Date-indexed Series named "dff_surprise"
    """
    vintages = fetch_dff_vintages(fred_api_key, cache_dir=_cache_dir(cache_dir))
    levels = dff_as_of_levels(as_of_dates, vintages)
    # Surprise = first difference (one-day shock)
    surprise = levels.diff()
    surprise.name = "dff_surprise"
    log.info(
        "dff_surprise_computed",
        n=len(surprise),
        n_valid=int(surprise.notna().sum()),
    )
    return surprise


def standardize_macro_lines(
    vix: pd.Series,
    credit_spread: pd.Series,
    term_spread: pd.Series,
    dff_surprise: pd.Series,
    epu: pd.Series | None,  # Optional (exploratory)
) -> pd.DataFrame:
    """Standardize all 5 macro lines via past-only rolling z-score.

    Each input series is standardized independently (z-score), then the
    z-scores are returned as a DataFrame. EPU is optional: if None, the
    returned frame has 4 columns.

    Args:
        vix: VIX level series
        credit_spread: Credit spread series
        term_spread: Term spread series
        dff_surprise: DFF surprise series
        epu: EPU series (optional; if None, 4-line layer)

    Returns:
        DataFrame with columns [vix_z, credit_spread_z, term_spread_z, dff_surprise_z, (epu_z)]
        (5 columns if epu provided, 4 otherwise)
    """
    # Standardize each line independently
    vix_z = rolling_zscore(vix)
    credit_z = rolling_zscore(credit_spread)
    term_z = rolling_zscore(term_spread)
    dff_z = rolling_zscore(dff_surprise)

    # Build z-score frame
    z_dict = {
        "vix_z": vix_z,
        "credit_spread_z": credit_z,
        "term_spread_z": term_z,
        "dff_surprise_z": dff_z,
    }

    if epu is not None and not epu.empty:
        epu_z = rolling_zscore(epu)
        z_dict["epu_z"] = epu_z

    z_frame = pd.DataFrame(z_dict)

    log.info(
        "macro_lines_standardized",
        n_lines=len(z_frame.columns),
        n_dates=len(z_frame),
        n_valid_per_col=z_frame.notna().sum().to_dict(),
    )

    return z_frame


def equal_weight_composite(z_frame: pd.DataFrame) -> pd.Series:
    """Equal-weight average of standardized macro lines -> regime series.

    The macro regime state is the equal-weight mean of the z-scores. This is
    NOT the final Track C feature — the TACO expanding-as-of σ normalization
    and 3-layer composite (macro + price + sentiment) is a separate opus task.

    Args:
        z_frame: DataFrame of z-scored macro lines (from standardize_macro_lines)

    Returns:
        Date-indexed Series named "macro_regime"
    """
    # Equal-weight average (skipna=True propagates partial availability)
    composite = z_frame.mean(axis=1, skipna=True)
    composite.name = "macro_regime"

    log.info(
        "macro_composite_built",
        n=len(composite),
        n_valid=int(composite.notna().sum()),
        n_components=len(z_frame.columns),
    )

    return composite


def build_macro_regime(
    as_of_dates: pd.DatetimeIndex,
    fred_api_key: str,
    start_date: str,
    end_date: str,
    cache_dir: Path | None = None,
    include_epu: bool = False,
) -> pd.Series:
    """Build the macro regime layer end-to-end (fetch -> standardize -> composite).

    This is the main entry point for scripts/build_regime_macro.py.

    Args:
        as_of_dates: Session dates to align to (sorted ascending)
        fred_api_key: FRED API key
        start_date: Start date for FRED series fetch (ISO)
        end_date: End date for FRED series fetch (ISO)
        cache_dir: Override cache directory
        include_epu: If True, attempt to fetch EPU (experimental; currently 4-line)

    Returns:
        Date-indexed Series named "macro_regime" (equal-weight composite)

    Raises:
        RuntimeError: If any required fetch fails
    """
    log.info(
        "building_macro_regime",
        n_dates=len(as_of_dates),
        start=start_date,
        end=end_date,
        include_epu=include_epu,
    )

    # 1. Fetch the 4-5 raw macro lines
    vix = fetch_vix_level(as_of_dates, cache_dir)

    credit_spread = fetch_credit_spread(start_date, end_date, fred_api_key, cache_dir)
    term_spread = fetch_term_spread(start_date, end_date, fred_api_key, cache_dir)
    dff_surprise = fetch_dff_surprise_series(as_of_dates, fred_api_key, cache_dir)

    # EPU: exploratory (skip for now — 4-line layer)
    epu = None
    if include_epu:
        log.warning("epu_skipped", reason="no permissive PIT-safe source identified yet")

    # 2. Standardize each line (past-only rolling z-score)
    z_frame = standardize_macro_lines(vix, credit_spread, term_spread, dff_surprise, epu)

    # 3. Equal-weight composite
    macro_regime = equal_weight_composite(z_frame)

    log.info(
        "macro_regime_built",
        n=len(macro_regime),
        n_valid=int(macro_regime.notna().sum()),
        date_range=(macro_regime.first_valid_index(), macro_regime.last_valid_index()),
    )

    return macro_regime


__all__ = [
    "build_macro_regime",
    "fetch_vix_level",
    "fetch_credit_spread",
    "fetch_term_spread",
    "fetch_dff_surprise_series",
    "standardize_macro_lines",
    "equal_weight_composite",
    "rolling_zscore",
]
