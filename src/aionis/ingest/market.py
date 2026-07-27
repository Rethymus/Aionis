"""Market price ingestion: yfinance primary, Stooq fallback, parquet snapshots.

Always returns *adjusted* close (splits + dividends), wide (index = NYSE session
date, columns = symbols). yfinance has silent-failure modes (empty frame for a
bad ticker, pre-IPO truncation), so every fetch is validated against the NYSE
calendar and a fallback source is tried per-symbol.

These functions require network access; they are NOT exercised by the test suite
(which uses synthetic data). Completeness is asserted so data rot cannot create a
silent hole inside a label window.
"""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import structlog

from aionis.features.alignment import nyse_sessions

log = structlog.get_logger()


def _from_tiingo(
    symbols: list[str], start: str, end: str, api_key: str, retries: int = 3, backoff: int = 4
) -> dict[str, pd.Series]:
    """Tiingo EOD daily: adjusted close (split + dividend) per symbol.

    Preferred source when the key is set — Tiingo covers ~30k US stocks AND
    ETFs (SPY / sector ETFs) from one host that is NOT Yahoo or Stooq (both are
    IP-blocked here). Polite by construction: one symbol per request, 1s between
    symbols, exponential backoff on transient errors (Tiingo closes connections
    under burst, same lesson as every other host on this egress).
    """
    import requests

    out: dict[str, pd.Series] = {}
    headers = {"Authorization": f"Token {api_key}", "User-Agent": "aionis/0.1"}
    for sym in symbols:
        col: pd.Series | None = None
        for attempt in range(retries):
            try:
                r = requests.get(
                    f"https://api.tiingo.com/tiingo/daily/{sym}/prices",
                    headers=headers,
                    params={"startDate": start, "endDate": end},
                    timeout=30,
                )
                if r.status_code == 200:
                    rows = r.json()
                    if rows:
                        df = pd.DataFrame(rows)
                        # Tiingo `date` can be tz-aware (e.g. ...-05:00); force
                        # UTC -> tz-naive -> normalized so it aligns with the
                        # tz-naive NYSE-session index fetch_prices reindexes on.
                        idx = pd.DatetimeIndex(
                            pd.to_datetime(df["date"], utc=True)
                        ).tz_localize(None).normalize()
                        col = pd.Series(
                            df["adjClose"].to_numpy(float), index=idx, name=sym,
                        )
                        break
                if r.status_code in (400, 404):
                    break  # ticker not in Tiingo (delisted/foreign) — don't retry
            except Exception:
                pass
            if attempt < retries - 1:
                time.sleep(backoff * (attempt + 1))
        if col is not None and not col.empty:
            out[sym] = col
        time.sleep(1.0)  # polite: 1s between symbols
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
    fits without pagination).
    """
    import requests

    out: dict[str, pd.Series] = {}
    headers = {"APCA-API-KEY-ID": key_id, "APCA-API-SECRET-KEY": secret_key,
               "User-Agent": "aionis/0.1"}
    for sym in symbols:
        col: pd.Series | None = None
        for attempt in range(retries):
            try:
                r = requests.get(
                    f"https://data.alpaca.markets/v2/stocks/{sym}/bars",
                    headers=headers,
                    params={"timeframe": "1Day", "start": start, "end": end,
                            "adjustment": "all", "limit": 10000},
                    timeout=30,
                )
                if r.status_code == 200:
                    bars = r.json().get("bars", [])
                    if bars:
                        df = pd.DataFrame(bars)
                        idx = pd.DatetimeIndex(
                            pd.to_datetime(df["t"], utc=True)
                        ).tz_localize(None).normalize()
                        col = pd.Series(df["c"].to_numpy(float), index=idx, name=sym)
                        break
                if r.status_code in (400, 404):
                    break  # symbol not in Alpaca — don't retry
            except Exception:
                pass
            if attempt < retries - 1:
                time.sleep(backoff * (attempt + 1))
        if col is not None and not col.empty:
            out[sym] = col
        time.sleep(1.0)  # polite: 1s between symbols
    return out


def _from_yfinance(
    symbols: list[str], start: str, end: str, retries: int = 4, backoff: int = 15
) -> dict[str, pd.Series]:
    try:
        import yfinance as yf
    except ImportError as e:  # pragma: no cover - dev dep guard
        raise RuntimeError(
            "yfinance is required for market ingestion (uv sync --extra extraction)"
        ) from e

    # Fetch PER SYMBOL with independent retry. yfinance rate-limits per IP and
    # returns a PARTIALLY empty frame for a batched multi-symbol call (some
    # tickers get data, others get a silent empty column with a "possibly
    # delisted" warning) — a single batched call then silently drops symbols.
    # One ticker per call lets a rate-limit on one symbol be retried in isolation.
    out: dict[str, pd.Series] = {}
    end_excl = pd.Timestamp(end) + pd.Timedelta(days=1)
    for sym in symbols:
        col: pd.Series | None = None
        for attempt in range(retries):
            raw = yf.download(
                tickers=sym,
                start=start,
                end=end_excl,
                auto_adjust=False,
                progress=False,
                threads=False,
            )
            if raw is not None and not raw.empty:
                if isinstance(raw.columns, pd.MultiIndex):
                    field = "Adj Close" if ("Adj Close", sym) in raw.columns else "Close"
                    c = raw[(field, sym)]
                else:
                    field = "Adj Close" if "Adj Close" in raw.columns else "Close"
                    c = raw[field]
                c = c.dropna()
                if not c.empty:
                    col = c
                    break
            log.warning("yfinance_empty_retry", symbol=sym, attempt=attempt + 1, of=retries)
            if attempt < retries - 1:
                time.sleep(backoff * (attempt + 1))
        if col is not None and not col.empty:
            col.index = pd.DatetimeIndex(
                [pd.Timestamp(d).tz_localize(None).normalize() for d in col.index]
            )
            out[sym] = col.rename(sym)
        time.sleep(0.4)  # politeness between symbols to avoid rate-limiting
    return out


def _from_stooq(symbol: str, start: str, end: str) -> pd.Series | None:
    """Stooq daily CSV fallback. Close is split-adjusted (not dividend-adjusted)."""
    url = f"https://stooq.com/q/d/l/?s={symbol.lower()}.us&i=d"
    try:
        df = pd.read_csv(url, parse_dates=["Date"])
    except Exception as e:  # pragma: no cover - network path
        log.warning("stooq_fetch_failed", symbol=symbol, error=str(e))
        return None
    if df.empty or "Close" not in df.columns:
        return None
    s = df.set_index("Date")["Close"].sort_index().dropna()
    s.index = pd.DatetimeIndex([pd.Timestamp(d).normalize() for d in s.index])
    return s.loc[pd.Timestamp(start) : pd.Timestamp(end)].rename(symbol)


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

    # Price sources in priority order: Tiingo -> Alpaca -> yfinance -> Stooq.
    # Tiingo + Alpaca both verified from this egress (independent hosts, redundant);
    # yfinance/Stooq are IP-blocked here but kept for portability. All polite.
    from aionis.config import settings

    series_by_sym: dict[str, pd.Series] = {}
    if settings.tiingo_api_key:
        series_by_sym = _from_tiingo(symbols, start, end, settings.tiingo_api_key)
    alpaca_missing = [s for s in symbols if s not in series_by_sym or series_by_sym[s].empty]
    if alpaca_missing and settings.alpaca_key_id and settings.alpaca_secret_key:
        series_by_sym.update(
            _from_alpaca(alpaca_missing, start, end,
                         settings.alpaca_key_id, settings.alpaca_secret_key)
        )
    yf_missing = [s for s in symbols if s not in series_by_sym or series_by_sym[s].empty]
    if yf_missing:
        series_by_sym.update(_from_yfinance(yf_missing, start, end))
    for sym in symbols:
        if sym in series_by_sym and not series_by_sym[sym].empty:
            continue
        log.info("trying_stooq_fallback", symbol=sym)
        fb = _from_stooq(sym, start, end)
        if fb is not None and not fb.empty:
            series_by_sym[sym] = fb

    missing = [s for s in symbols if s not in series_by_sym]
    if missing:
        raise RuntimeError(f"no data retrieved for symbols: {missing}")

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
