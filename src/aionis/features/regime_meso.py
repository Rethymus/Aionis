"""Regime meso layer (Track C) — cross-sector momentum regime.

This module builds the meso component of Track C's regime_state feature:
  - Classify each stock into a sector (US: SIC; CN: shenwan/申万)
  - Per sector, compute equal-weight member momentum_21d at date t
  - The meso regime at t = equal-weight MEAN of sector-momentum values across sectors
  - Compute separately for US and CN, then equal-weight the two

The meso regime is a market-wide daily series (NOT per-stock) — a single number
summarizing "how strong is the cross-sector momentum regime" at each date.

Anti-leakage (binding):
  - Sector momentum uses rolling(21, min_periods=21) — past-only
  - baostock industry fetch: polite ≥2s + snapshot (MIT, G7)
  - NO ledger write (exploratory, not wired to live pipeline)

H6 determinism: seed=0, n_jobs=1 for all synthetic tests.

Data sources (7-gate, permissive only):
  - US SIC: EDGAR submissions (public domain) via phase_d_sic_map.parquet
  - CN shenwan: baostock query_stock_industry() (MIT)
"""
from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import structlog

from aionis.config import settings
from aionis.features.price_features import momentum

log = structlog.get_logger()

# Sector momentum window (trading days)
_MOMENTUM_WINDOW = 21
# baostock industry fetch politeness (G7)
_BAOSTOCK_PAUSE = 2.0


def _cache_dir(cache_dir: Path | None = None) -> Path:
    """Get cache directory, creating if needed."""
    d = cache_dir or settings.data_dir / "cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _sha256(path: Path) -> str:
    """Compute SHA256 of a file (cache pinning)."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_baostock() -> Any:
    """Lazy-import baostock (intentionally not a core dependency)."""
    try:
        import baostock as bs
    except ImportError as e:  # pragma: no cover - exercised only without baostock installed
        raise ImportError(
            "baostock is required for CN shenwan industry classification (Track C meso). "
            "It is intentionally NOT a core dependency. Activate with `uv add baostock` "
            "(MIT license, passes the data-license-allowlist)."
        ) from e
    return bs


def _ensure_baostock_login(bs: Any) -> None:
    """``bs.login()`` with fail-closed on auth error (G7 politeness + ToS)."""
    lg = bs.login()
    if str(getattr(lg, "error_code", "0")) != "0":
        raise RuntimeError(
            f"baostock login failed: code={getattr(lg, 'error_code', '?')} "
            f"msg={getattr(lg, 'error_msg', '?')}"
        )


def _fetch_shenwan_sector_for_tickers(
    tickers: list[str],
    cache_dir: Path | None = None,
    pause: float = _BAOSTOCK_PAUSE,
) -> dict[str, str]:
    """Fetch shenwan (申万) industry classification for CN tickers via baostock.

    baostock ``query_stock_industry()`` returns the shenwan industry for a stock.
    Results are cached per ticker (sha256-pinned) so reruns make no HTTP call.
    Inter-query spacing ≥``pause`` seconds enforces G7 politeness.

    Args:
        tickers: CSI300 tickers (e.g., "sh.600000", "sz.000001")
        cache_dir: Override cache directory
        pause: Seconds to sleep between queries (default 2.0)

    Returns:
        Dict mapping ticker -> shenwan industry name (e.g., "银行", "医药生物")

    Raises:
        RuntimeError: If baostock login or query fails
    """
    bs = _require_baostock()
    _ensure_baostock_login(bs)
    cdir = _cache_dir(cache_dir)

    mapping: dict[str, str] = {}
    failures: list[tuple[str, str]] = []

    try:
        for idx, ticker in enumerate(tickers):
            # Check cache
            cache_file = cdir / f"shenwan_{ticker}.json"
            if cache_file.exists():
                import json

                data = json.loads(cache_file.read_text())
                if data.get("ticker") == ticker and data.get("industry"):
                    mapping[ticker] = data["industry"]
                    continue

            # Fetch from baostock
            try:
                rs = bs.query_stock_industry(ticker)
                if str(getattr(rs, "error_code", "0")) != "0":
                    failures.append((ticker, getattr(rs, "error_msg", "?")))
                    log.warning(
                        "baostock_industry_failed",
                        ticker=ticker,
                        msg=getattr(rs, "error_msg", "?"),
                    )
                    continue

                # Get first row's industry value
                industry = None
                while rs.next():  # type: ignore[union-attr]
                    industry = rs.get_row_data()[1]  # column 1 = industry name
                    break

                if industry:
                    mapping[ticker] = industry
                    # Cache
                    import json

                    cache_file.write_text(
                        json.dumps(
                            {"ticker": ticker, "industry": industry},
                            ensure_ascii=False,
                        )
                    )
                else:
                    failures.append((ticker, "no_industry_returned"))

                # Politeness: pause between queries (except last)
                if pause > 0 and idx < len(tickers) - 1:
                    time.sleep(pause)

            except Exception as e:  # noqa: BLE001
                failures.append((ticker, str(e)[:80]))
                log.warning("baostock_industry_error", ticker=ticker, error=str(e)[:80])

    finally:
        try:
            bs.logout()
        except Exception:  # noqa: BLE001
            log.warning("baostock_logout_failed")

    log.info(
        "shenwan_industry_fetched",
        n_total=len(tickers),
        n_success=len(mapping),
        n_failed=len(failures),
    )

    if failures:
        log.warning("shenwan_failures", sample=failures[:5])

    return mapping


def _load_us_sic_map(cache_dir: Path | None = None) -> dict[str, str]:
    """Load US SIC classification from cached EDGAR data.

    EDGAR public domain (17 U.S.C. §105) — passes 7-gate. SIC codes are
    extracted from SEC submissions (see :mod:`aionis.ingest.stakes_13d`).

    Args:
        cache_dir: Override cache directory

    Returns:
        Dict mapping ticker -> SIC code (string)

    Raises:
        FileNotFoundError: If phase_d_sic_map.parquet does not exist
    """
    cdir = _cache_dir(cache_dir)
    sic_file = cdir / "phase_d_sic_map.parquet"

    if not sic_file.exists():
        raise FileNotFoundError(
            f"US SIC map not found at {sic_file}. "
            "Run Phase D ingest first or document the gap for CN-only meso."
        )

    df = pd.read_parquet(sic_file)
    mapping = dict(zip(df["ticker"], df["sic"].astype(str), strict=True))

    log.info("us_sic_map_loaded", n_tickers=len(mapping), sha256=_sha256(sic_file))

    return mapping


def _compute_sector_momentum(
    prices_wide: pd.DataFrame,
    sector_map: dict[str, str],
    window: int = _MOMENTUM_WINDOW,
) -> pd.Series:
    """Compute cross-sector mean momentum regime.

    For each date t:
      1. Classify stocks into sectors via sector_map
      2. Compute momentum_21d for each stock (uses prices ≤ t)
      3. Per sector, compute equal-weight mean of member momentums
      4. Cross-sector regime = equal-weight mean of sector momentums

    This is a market-wide series (one value per date), NOT per-stock.

    Args:
        prices_wide: Price panel [dates x tickers] as DataFrame
        sector_map: Dict mapping ticker -> sector classification
        window: Momentum window (trading days, default 21)

    Returns:
        Date-indexed Series named "meso_regime" (cross-sector momentum)
    """
    if prices_wide.empty:
        return pd.Series(dtype=float, name="meso_regime")

    # Compute returns
    returns = prices_wide.pct_change()

    # Compute momentum per stock
    stock_momentum = momentum(returns, window=window)

    # Build sector frame: for each date, compute sector mean momentum
    dates = stock_momentum.index
    sectors_by_ticker = {
        ticker: sector
        for ticker, sector in sector_map.items()
        if ticker in stock_momentum.columns
    }

    # Handle empty sector map: return NaN series with same index
    if not sectors_by_ticker:
        log.warning("no_sector_coverage", n_total=len(sector_map), n_in_prices=0)
        return pd.Series(np.nan, index=dates, name="meso_regime")

    # For each date, compute sector means
    sector_means_by_date: dict[pd.Timestamp, list[float]] = {}

    for date in dates:
        sector_values: dict[str, list[float]] = {}
        row = stock_momentum.loc[date]

        for ticker, sector in sectors_by_ticker.items():
            val = row.get(ticker)
            if pd.notna(val):
                sector_values.setdefault(sector, []).append(float(val))

        # Equal-weight per sector
        if sector_values:
            sector_means = [np.mean(vals) for vals in sector_values.values()]
            sector_means_by_date[date] = sector_means
        else:
            sector_means_by_date[date] = []

    # Cross-sector mean (equal-weight across sectors at each date)
    cross_sector_values = []
    for date in dates:
        means = sector_means_by_date.get(date, [])
        if means:
            cross_sector_values.append(np.mean(means))
        else:
            cross_sector_values.append(np.nan)

    result = pd.Series(cross_sector_values, index=dates, name="meso_regime")

    log.info(
        "sector_momentum_computed",
        n_dates=len(result),
        n_valid=int(result.notna().sum()),
        n_sectors=len(set(sectors_by_ticker.values())),
        n_stocks=len(sectors_by_ticker),
    )

    return result


def build_meso_regime(
    us_prices: pd.DataFrame,
    cn_prices: pd.DataFrame,
    cache_dir: Path | None = None,
    enable_cn_fetch: bool = False,
    cn_fetch_pause: float = _BAOSTOCK_PAUSE,
) -> pd.Series:
    """Build the meso regime layer end-to-end.

    Loads sector classifications (US SIC from cache; CN shenwan via baostock),
    computes cross-sector momentum for each region, then equal-weights the two
    regional regimes into a single daily meso series.

    Args:
        us_prices: US price panel [dates x tickers] (wide DataFrame)
        cn_prices: CN price panel [dates x tickers] (wide DataFrame)
        cache_dir: Override cache directory
        enable_cn_fetch: If True, fetch CN shenwan data (default False)
        cn_fetch_pause: Seconds pause between baostock queries (default 2.0)

    Returns:
        Date-indexed Series named "meso_regime" (equal-weight US+CN)

    Raises:
        FileNotFoundError: If US SIC map missing
        RuntimeError: If CN fetch enabled and baostock fails
    """
    log.info("building_meso_regime", us_dates=len(us_prices), cn_dates=len(cn_prices))

    # US regime: SIC-based
    us_sector_map = _load_us_sic_map(cache_dir)
    us_regime = _compute_sector_momentum(us_prices, us_sector_map)
    us_regime.name = "meso_us"

    # CN regime: shenwan-based (if enabled)
    cn_regime = pd.Series(dtype=float, name="meso_cn")

    if enable_cn_fetch:
        # Convert CN price panel to baostock format if needed
        cn_tickers = cn_prices.columns.tolist()
        # Map CSI300 format to baostock format (e.g., SH600000 -> sh.600000)
        cn_tickers_bs = [t[:2].lower() + "." + t[2:] for t in cn_tickers]

        shenwan_map = _fetch_shenwan_sector_for_tickers(cn_tickers_bs, cache_dir, cn_fetch_pause)

        # Map back to original ticker format
        shenwan_map_original = {cn_tickers[i]: industry for i, industry in shenwan_map.items()}

        cn_regime = _compute_sector_momentum(cn_prices, shenwan_map_original)
        cn_regime.name = "meso_cn"
    else:
        log.warning("cn_regime_skipped", reason="enable_cn_fetch=False")

    # Equal-weight US + CN
    regimes = pd.DataFrame({"us": us_regime, "cn": cn_regime})
    meso_regime = regimes.mean(axis=1, skipna=True)
    meso_regime.name = "meso_regime"

    log.info(
        "meso_regime_built",
        n_dates=len(meso_regime),
        n_valid=int(meso_regime.notna().sum()),
        n_regions=int(regimes.notna().any(axis=1).sum()),
        date_range=(
            (meso_regime.first_valid_index(), meso_regime.last_valid_index())
            if meso_regime.notna().any()
            else (None, None)
        ),
    )

    return meso_regime


__all__ = [
    "build_meso_regime",
    "_compute_sector_momentum",
    "_load_us_sic_map",
    "_fetch_shenwan_sector_for_tickers",
]
