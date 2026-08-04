"""A-share daily price ingestion via baostock (MIT), mirroring ``ingest/market.py``.

Track C (dual-region US+CN) headline price source for CSI300 constituents.

G3 no-revision contract: the raw OHLCV is exchange-fixed (low revision risk),
but baostock's ``adjustflag`` (复权 factor) IS retroactively revisable when new
corporate actions occur. The default ``adjustflag="3"`` (raw, unadjusted) defers
the freeze strategy to config — see ``docs/data-intake-ashare-price-baostock.md``
§G3 (方案 A = raw + frozen local factor snapshot; 方案 B = frozen pre-adjusted
series). NEVER silently change ``adjustflag``: a different value is a different
frozen series = a new ledger row, not an in-place overwrite.

Politeness (G7): baostock is a login-session API (not per-call HTTP), so the
≥2s data-fetch spacing is an explicit inter-query ``pause``. Survivorship (G6):
the caller supplies PIT constituents (incl. delisted, via ``query_all_stock``);
suspension (``tradestatus != "1"``) is NaN'd here so a halted day never carries a
stale close into a label window.

Lazy import: baostock is intentionally NOT a core dependency. Activate with
``uv add baostock`` before the first real pull (MIT license, passes the
allowlist). Tests mock the module via ``sys.modules``.

7-gate intake: ``docs/data-intake-ashare-price-baostock.md`` (PROPOSED, PASS with
G3 缓解).
"""

from __future__ import annotations

import time
from typing import Any

import pandas as pd
import structlog

log = structlog.get_logger()

# baostock tradestatus: "1" = normal trading, "0" = suspended.
_TRADE_NORMAL = "1"
_OHLCV = ["open", "high", "low", "close", "volume"]
_COLUMNS = ["date", "ticker", "open", "high", "low", "close", "volume", "tradestatus"]


def _require_baostock() -> Any:
    """Lazy-import baostock (intentionally not a core dependency)."""
    try:
        import baostock as bs
    except ImportError as e:  # pragma: no cover - exercised only without baostock installed
        raise ImportError(
            "baostock is required for A-share price ingestion (Track C S0). It is "
            "intentionally NOT a core dependency. Activate with `uv add baostock` "
            "(MIT license, passes the data-license-allowlist)."
        ) from e
    return bs


def _ensure_login(bs: Any) -> None:
    """``bs.login()`` with fail-closed on auth error (G7 politeness + ToS)."""
    lg = bs.login()
    if str(getattr(lg, "error_code", "0")) != "0":
        raise RuntimeError(
            f"baostock login failed: code={getattr(lg, 'error_code', '?')} "
            f"msg={getattr(lg, 'error_msg', '?')}"
        )


def _query_one(
    bs: Any, code: str, start: str, end: str, adjustflag: str
) -> pd.DataFrame:
    """Query one baostock code under an existing login; return a tidy long frame.

    Assumes the caller manages the login session (see :func:`fetch_ashare_prices`).
    """
    rs = bs.query_history_k_data_plus(
        code,
        start_date=start,
        end_date=end,
        frequency="d",
        adjustflag=adjustflag,
        fields="date,code,open,high,low,close,volume,tradestatus",
    )
    if str(getattr(rs, "error_code", "0")) != "0":
        raise RuntimeError(
            f"baostock query failed for {code}: code={getattr(rs, 'error_code', '?')} "
            f"msg={getattr(rs, 'error_msg', '?')}"
        )
    rows: list[list[str]] = []
    while rs.next():  # type: ignore[union-attr]
        rows.append(list(rs.get_row_data()))  # type: ignore[union-attr]
    cols = list(getattr(rs, "fields", []) or _COLUMNS)
    if not rows:
        return pd.DataFrame(columns=_COLUMNS)

    raw = pd.DataFrame(rows, columns=cols)
    return pd.DataFrame(
        {
            "date": pd.to_datetime(raw["date"]).dt.normalize(),
            "ticker": raw["code"].astype(str),
            "open": pd.to_numeric(raw["open"], errors="coerce"),
            "high": pd.to_numeric(raw["high"], errors="coerce"),
            "low": pd.to_numeric(raw["low"], errors="coerce"),
            "close": pd.to_numeric(raw["close"], errors="coerce"),
            "volume": pd.to_numeric(raw["volume"], errors="coerce"),
            "tradestatus": raw["tradestatus"].astype(str),
        }
    ).sort_values("date").reset_index(drop=True)


def apply_suspension(df: pd.DataFrame) -> pd.DataFrame:
    """NaN OHLCV where ``tradestatus != "1"`` (G6: suspension, no stale carry)."""
    if df.empty:
        return df
    out = df.copy()
    mask = out["tradestatus"] != _TRADE_NORMAL
    if mask.any():
        out.loc[mask, _OHLCV] = pd.NA
    for col in _OHLCV:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def fetch_ashare_prices(
    codes: list[str],
    start: str,
    end: str,
    adjustflag: str = "3",
    pause: float = 2.0,
) -> pd.DataFrame:
    """Fetch A-share daily OHLCV for many baostock codes (e.g. ``sh.600000``).

    One login session spans the batch; ≥``pause`` seconds elapse between queries
    (G7 politeness). Returns a concatenated tidy long frame with the columns in
    ``_COLUMNS`` and suspension NaN'd via :func:`apply_suspension`.

    ``adjustflag``: ``"3"`` raw (default, G3 方案 A), ``"1"`` forward-adjusted,
    ``"2"`` backward-adjusted. Changing it = a new frozen series = a new ledger
    row; the default deliberately defers the G3 freeze strategy to config.
    """
    bs = _require_baostock()
    _ensure_login(bs)
    try:
        frames: list[pd.DataFrame] = []
        for idx, code in enumerate(codes):
            frames.append(_query_one(bs, code, start, end, adjustflag))
            if pause > 0 and idx < len(codes) - 1:
                time.sleep(pause)
    finally:
        try:
            bs.logout()
        except Exception:  # noqa: BLE001 - logout is best-effort
            log.warning("baostock_logout_failed")
    if not frames:
        return pd.DataFrame(columns=_COLUMNS)
    return apply_suspension(pd.concat(frames, ignore_index=True))
