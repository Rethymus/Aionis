"""A-share daily price fetch for the CSI300 universe (Track C S0).

baostock raw OHLCV (``adjustflag='3'``, G3 方案 A — raw + frozen local snapshot), ≥2s
inter-query politeness (G7 — baostock is a login-session API), per-ticker error isolation
(one bad code does not abort the batch), ONE login session spanning all tickers.
Suspension days (``tradestatus != '1'``) are NaN'd (G6 — no stale close into a label).

Source universe: ``data/cache/csi300_constituents.parquet`` (949 historical CSI300 members
incl. delisted → survivorship-safe). Writes ``data/cache/ashare_prices_csi300.parquet``
(gitignored); record its sha256 in the intake doc (NOT the ledger — S0 data snapshot).

Date range ``2014-01-01..2026-08-04``: 2yr lookback before the Track C 2016 window for
252-day features (momentum/beta). NOT incremental/resumable — simplicity over partial-restart
comfort; per-ticker isolation bounds a bad run, and re-runs overwrite wholesale.

Usage::

    uv add baostock && uv run python scripts/ashare_price_fetch_csi300.py
"""
from __future__ import annotations

import hashlib
import sys
import time

import pandas as pd
import structlog

from aionis.config import settings
from aionis.ingest.ashare_price import (
    _COLUMNS,
    _ensure_login,
    _query_one,
    _require_baostock,
    apply_suspension,
)

log = structlog.get_logger()

CACHE = settings.data_dir / "cache"
UNIVERSE = CACHE / "csi300_constituents.parquet"
OUT = CACHE / "ashare_prices_csi300.parquet"
START = "2014-01-01"  # 2yr lookback before Track C 2016 window (252d features)
END = "2026-08-04"
ADJUSTFLAG = "3"  # raw, G3 方案 A (frozen local snapshot; changing = new ledger row)
PAUSE = 2.0  # G7 politeness between queries


def _csi300_to_baostock(ticker: str) -> str:
    """CSI300 symbol -> baostock code: SZ000001 -> sz.000001, SH600000 -> sh.600000."""
    return ticker[:2].lower() + "." + ticker[2:]


def main() -> int:
    if not UNIVERSE.exists():
        print(
            f"[ERROR] {UNIVERSE} missing — run the CSI300 constituents fetch first.",
            file=sys.stderr,
        )
        return 1

    uni = pd.read_parquet(UNIVERSE)
    tickers = sorted(uni["ticker"].unique().tolist())
    codes = [_csi300_to_baostock(t) for t in tickers]
    print(
        f"[S] CSI300 universe: {len(codes)} tickers | {START}..{END} | "
        f"adjustflag={ADJUSTFLAG} pause={PAUSE}s",
        flush=True,
    )

    bs = _require_baostock()
    _ensure_login(bs)
    frames: list[pd.DataFrame] = []
    failures: list[tuple[str, str]] = []
    try:
        for i, code in enumerate(codes, 1):
            try:
                frames.append(_query_one(bs, code, START, END, ADJUSTFLAG))
            except Exception as e:  # noqa: BLE001 — isolate per-ticker failures
                failures.append((code, str(e)[:80]))
                log.warning("ticker_failed", code=code, err=str(e)[:80])
            if i % 50 == 0:
                print(f"[S] progress {i}/{len(codes)} (failures={len(failures)})", flush=True)
            if i < len(codes):
                time.sleep(PAUSE)
    finally:
        try:
            bs.logout()
        except Exception:  # noqa: BLE001 — best-effort
            log.warning("baostock_logout_failed")

    df = (
        apply_suspension(pd.concat(frames, ignore_index=True))
        if frames
        else pd.DataFrame(columns=_COLUMNS)
    )
    CACHE.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT)
    sha = hashlib.sha256(OUT.read_bytes()).hexdigest()
    print(
        f"[S] DONE: rows={len(df)} tickers_ok={df['ticker'].nunique()} "
        f"failures={len(failures)}",
        flush=True,
    )
    print(
        f"[S] wrote {OUT} | sha256={sha[:16]} | MB={OUT.stat().st_size / 1e6:.1f}",
        flush=True,
    )
    if failures:
        preview = failures[:5]
        print(f"[S] failed tickers: {preview}{'...' if len(failures) > 5 else ''}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
