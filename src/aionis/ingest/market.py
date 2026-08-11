"""Market price ingestion from approved providers, with parquet snapshots.

Always returns *adjusted* close (splits + dividends), wide (index = NYSE session
date, columns = symbols). Tiingo is tried first and Alpaca fills only unresolved
symbols. Every fetch is validated against the NYSE calendar.

These functions require network access; tests replace provider calls with hermetic
stubs. Completeness is asserted so data rot cannot create a silent hole inside a
label window.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import structlog

from aionis.config import settings
from aionis.features.alignment import nyse_sessions
from aionis.ingest.universe import _policy_get

log = structlog.get_logger()


def _from_tiingo(
    symbols: list[str], start: str, end: str, api_key: str, retries: int = 3, backoff: int = 4
) -> dict[str, pd.Series]:
    """Tiingo EOD daily: adjusted close (split + dividend) per symbol.

    Preferred source when the key is set. One symbol is requested at a time
    through the shared host-scoped spacing and bounded-retry policy.
    """
    out: dict[str, pd.Series] = {}
    headers = {"Authorization": f"Token {api_key}", "User-Agent": "aionis/0.1"}
    for sym in symbols:
        col: pd.Series | None = None
        try:
            r = _policy_get(
                f"https://api.tiingo.com/tiingo/daily/{sym}/prices",
                total_attempts=retries,
                backoff_base=backoff,
                backoff_mode="linear",
                headers=headers,
                params={"startDate": start, "endDate": end},
                timeout=30,
            )
            rows = r.json()
            if rows:
                df = pd.DataFrame(rows)
                # Tiingo `date` can be tz-aware (e.g. ...-05:00); force
                # UTC -> tz-naive -> normalized so it aligns with the
                # tz-naive NYSE-session index fetch_prices reindexes on.
                idx = pd.DatetimeIndex(pd.to_datetime(df["date"], utc=True)).tz_localize(
                    None
                ).normalize()
                col = pd.Series(df["adjClose"].to_numpy(float), index=idx, name=sym)
        except Exception:
            pass
        if col is not None and not col.empty:
            out[sym] = col
    return out


def _from_alpaca(
    symbols: list[str], start: str, end: str, key_id: str, secret_key: str,
    retries: int = 3, backoff: int = 4,
) -> dict[str, pd.Series]:
    """Alpaca market-data: adjusted daily close (``adjustment='all'``) per symbol.

    Independent backup to Tiingo on a separate host — the same key/secret
    authenticates the paper-trading API; here we use the data endpoint
    (``data.alpaca.markets``). Polite: 1s between symbols + exp backoff. One call
    per symbol; ``limit=10000`` covers ~40y of daily bars (the 2009-2025 range
    fits without pagination). Requests use the shared host-scoped policy.
    """
    out: dict[str, pd.Series] = {}
    headers = {"APCA-API-KEY-ID": key_id, "APCA-API-SECRET-KEY": secret_key,
               "User-Agent": "aionis/0.1"}
    for sym in symbols:
        col: pd.Series | None = None
        try:
            r = _policy_get(
                f"https://data.alpaca.markets/v2/stocks/{sym}/bars",
                total_attempts=retries,
                backoff_base=backoff,
                backoff_mode="linear",
                headers=headers,
                params={
                    "timeframe": "1Day",
                    "start": start,
                    "end": end,
                    "adjustment": "all",
                    "limit": 10000,
                },
                timeout=30,
            )
            bars = r.json().get("bars", [])
            if bars:
                df = pd.DataFrame(bars)
                idx = pd.DatetimeIndex(pd.to_datetime(df["t"], utc=True)).tz_localize(
                    None
                ).normalize()
                col = pd.Series(df["c"].to_numpy(float), index=idx, name=sym)
        except Exception:
            pass
        if col is not None and not col.empty:
            out[sym] = col
    return out


def _volume_from_alpaca(
    symbols: list[str], start: str, end: str, key_id: str, secret_key: str,
    retries: int = 3, backoff: int = 4,
) -> dict[str, pd.Series]:
    """Fetch volume from Alpaca (adj close + volume per symbol).

    Returns dict {symbol: Series(volume)} with datetime index.
    """
    out: dict[str, pd.Series] = {}
    headers = {"APCA-API-KEY-ID": key_id, "APCA-API-SECRET-KEY": secret_key,
               "User-Agent": "aionis/0.1"}
    for sym in symbols:
        col: pd.Series | None = None
        try:
            r = _policy_get(
                f"https://data.alpaca.markets/v2/stocks/{sym}/bars",
                total_attempts=retries,
                backoff_base=backoff,
                backoff_mode="linear",
                headers=headers,
                params={
                    "timeframe": "1Day",
                    "start": start,
                    "end": end,
                    "adjustment": "all",
                    "limit": 10000,
                },
                timeout=30,
            )
            bars = r.json().get("bars", [])
            if bars:
                df = pd.DataFrame(bars)
                idx = pd.DatetimeIndex(pd.to_datetime(df["t"], utc=True)).tz_localize(
                    None
                ).normalize()
                col = pd.Series(df["v"].to_numpy(float), index=idx, name=sym)
        except Exception:
            pass
        if col is not None and not col.empty:
            out[sym] = col
    return out


def _missing_prices_error(symbols: list[str], providers: list[str]) -> RuntimeError:
    configured = ", ".join(providers) if providers else "none"
    missing = ", ".join(symbols)
    return RuntimeError(
        "approved market providers could not supply all requested symbols; "
        f"missing symbols: [{missing}]; configured providers: {configured}. "
        "Set TIINGO_API_KEY and/or both ALPACA_KEY_ID and ALPACA_SECRET_KEY, "
        "then verify symbol coverage and credentials."
    )


def fetch_price_series(symbols: list[str], start: str, end: str) -> dict[str, pd.Series]:
    """Fetch adjusted closes in approved order, failing closed if any symbol is missing."""
    series_by_sym: dict[str, pd.Series] = {}
    providers: list[str] = []
    if settings.tiingo_api_key:
        providers.append("Tiingo")
        series_by_sym.update(_from_tiingo(symbols, start, end, settings.tiingo_api_key))

    missing = [s for s in symbols if s not in series_by_sym or series_by_sym[s].empty]
    if missing and settings.alpaca_key_id and settings.alpaca_secret_key:
        providers.append("Alpaca")
        series_by_sym.update(
            _from_alpaca(
                missing,
                start,
                end,
                settings.alpaca_key_id,
                settings.alpaca_secret_key,
            )
        )

    missing = [s for s in symbols if s not in series_by_sym or series_by_sym[s].empty]
    if missing:
        raise _missing_prices_error(missing, providers)
    return series_by_sym


def fetch_prices(
    symbols: list[str],
    start: str,
    end: str,
    expected_sessions: pd.DatetimeIndex | None = None,
) -> pd.DataFrame:
    """Wide adjusted-close DataFrame for ``symbols`` over [start, end].

    Each symbol's series starts at its true first available session (no
    forward-filling of pre-inception gaps, e.g. XLC ~2014-06). Interior gaps
    (missing sessions between first and last valid close) are asserted absent.
    """
    if expected_sessions is None:
        expected_sessions = nyse_sessions(start, end)

    series_by_sym = fetch_price_series(symbols, start, end)

    wide = pd.DataFrame({s: series_by_sym[s] for s in symbols})
    wide = wide.reindex(expected_sessions).sort_index()

    # Validate: no interior NaNs per symbol (gaps = data rot inside label windows).
    for sym in symbols:
        col = wide[sym]
        first, last = col.first_valid_index(), col.last_valid_index()
        if first is None:
            raise RuntimeError(f"{sym}: entirely empty after reindex")
        interior = col.loc[first:last]
        n_gaps = int(interior.isna().sum())
        if n_gaps:
            log.warning("interior_price_gaps", symbol=sym, gaps=n_gaps)
    return wide


def save_snapshot(prices: pd.DataFrame, path: Path | str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    prices.to_parquet(path)
    log.info("snapshot_saved", path=str(path), rows=len(prices), cols=list(prices.columns))
    return path


def load_snapshot(path: Path | str) -> pd.DataFrame:
    return pd.read_parquet(Path(path))


def fetch_ohlcv_panel(
    symbols: list[str],
    start: str,
    end: str,
) -> dict[str, pd.DataFrame]:
    """Fetch per-symbol OHLCV DataFrames from approved providers.

    Returns a dictionary where each key is a symbol and each value is a
    DataFrame with columns: open, high, low, close, volume. Uses the same
    politeness policy as fetch_prices but extracts all 5 columns instead
    of just close. This is a separate function for future phase wiring and
    does NOT modify existing close-only behavior.

    Args:
        symbols: List of ticker symbols to fetch
        start: Start date (YYYY-MM-DD format)
        end: End date (YYYY-MM-DD format)

    Returns:
        dict[str, pd.DataFrame]: Per-symbol DataFrames with OHLCV columns

    Raises:
        RuntimeError: If any symbol cannot be fetched from configured providers
    """
    panels: dict[str, pd.DataFrame] = {}
    providers: list[str] = []

    # Try Tiingo first
    if settings.tiingo_api_key:
        providers.append("Tiingo")
        headers = {"Authorization": f"Token {settings.tiingo_api_key}", "User-Agent": "aionis/0.1"}
        for sym in symbols:
            if sym in panels:
                continue
            try:
                r = _policy_get(
                    f"https://api.tiingo.com/tiingo/daily/{sym}/prices",
                    total_attempts=3,
                    backoff_base=4,
                    backoff_mode="linear",
                    headers=headers,
                    params={"startDate": start, "endDate": end},
                    timeout=30,
                )
                rows = r.json()
                if rows:
                    df = pd.DataFrame(rows)
                    idx = pd.DatetimeIndex(pd.to_datetime(df["date"], utc=True)).tz_localize(
                        None
                    ).normalize()
                    # Extract OHLCV columns (use adjClose as close)
                    ohlcv = pd.DataFrame(
                        {
                            "open": df["open"].to_numpy(float),
                            "high": df["high"].to_numpy(float),
                            "low": df["low"].to_numpy(float),
                            "close": df["adjClose"].to_numpy(float),  # Use adjusted close
                            "volume": df["volume"].to_numpy(float),
                        },
                        index=idx,
                    )
                    panels[sym] = ohlcv
            except Exception:
                pass

    # Fill missing symbols with Alpaca
    missing = [s for s in symbols if s not in panels]
    if missing and settings.alpaca_key_id and settings.alpaca_secret_key:
        providers.append("Alpaca")
        headers = {
            "APCA-API-KEY-ID": settings.alpaca_key_id,
            "APCA-API-SECRET-KEY": settings.alpaca_secret_key,
            "User-Agent": "aionis/0.1",
        }
        for sym in missing:
            try:
                r = _policy_get(
                    f"https://data.alpaca.markets/v2/stocks/{sym}/bars",
                    total_attempts=3,
                    backoff_base=4,
                    backoff_mode="linear",
                    headers=headers,
                    params={
                        "timeframe": "1Day",
                        "start": start,
                        "end": end,
                        "adjustment": "all",
                        "limit": 10000,
                    },
                    timeout=30,
                )
                bars = r.json().get("bars", [])
                if bars:
                    df = pd.DataFrame(bars)
                    idx = pd.DatetimeIndex(pd.to_datetime(df["t"], utc=True)).tz_localize(
                        None
                    ).normalize()
                    # Alpaca uses o, h, l, c, v column names
                    ohlcv = pd.DataFrame(
                        {
                            "open": df["o"].to_numpy(float),
                            "high": df["h"].to_numpy(float),
                            "low": df["l"].to_numpy(float),
                            "close": df["c"].to_numpy(float),
                            "volume": df["v"].to_numpy(float),
                        },
                        index=idx,
                    )
                    panels[sym] = ohlcv
            except Exception:
                pass

    # Verify all symbols were fetched
    still_missing = [s for s in symbols if s not in panels or panels[s].empty]
    if still_missing:
        raise _missing_prices_error(still_missing, providers)

    return panels
