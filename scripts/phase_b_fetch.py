"""Phase B full data fetch (slice 5b): fundamentals + prices for the clean
OOS-resolvable universe. One-time, cached to parquet. Tolerant of missing symbols
(renamed/delisted drop out of the cross-section; both arms same -> differential valid).

Run:  uv run python scripts/phase_b_fetch.py   (~15-20 min; background-safe)
"""
from __future__ import annotations

import pandas as pd

from aionis.config import settings
from aionis.ingest.fundamentals import build_fundamentals
from aionis.ingest.market import _from_alpaca, _from_tiingo
from aionis.ingest.universe import build_oos_resolvable_universe

START, END = "2011-01-01", "2026-06-30"  # train 2011-2016 + OOS 2017-2026
CACHE = settings.data_dir / "cache"


def main() -> None:
    u = build_oos_resolvable_universe()
    tickers, ciks = u["tickers"], u["ciks"]
    print(f"[5b] clean OOS universe: {len(tickers)} tickers", flush=True)

    fund_path = CACHE / "phase_b_fundamentals.parquet"
    if fund_path.exists():
        print(f"[5b] fundamentals cached: {fund_path}", flush=True)
    else:
        print("[5b] fetching fundamentals (SEC company_facts, ~588 CIKs)...", flush=True)
        fund = build_fundamentals(tickers, cik_override=ciks)
        fund.to_parquet(fund_path)
        print(f"[5b] fundamentals: {len(fund)} rows, "
              f"{fund['ticker'].nunique()} tickers -> {fund_path}", flush=True)

    px_path = CACHE / "phase_b_prices.parquet"
    if px_path.exists():
        print(f"[5b] prices cached: {px_path}", flush=True)
    else:

        # Incremental + resumable: cache each symbol's series to cache/prices/<T>.parquet
        # as soon as it's fetched, so a kill/restart loses <= one batch (not 2h of work)
        # and progress is visible. Build the wide parquet at the end from the cache.
        pdir = CACHE / "prices"
        pdir.mkdir(exist_ok=True)
        series: dict[str, pd.Series] = {}
        for t in tickers:
            fp = pdir / f"{t}.parquet"
            if fp.exists():
                df = pd.read_parquet(fp)
                if not df.empty:
                    series[t] = pd.Series(
                        df["adjClose"].to_numpy(float),
                        index=pd.to_datetime(df["date"]).dt.normalize(), name=t,
                    )
        todo = [t for t in tickers if t not in series]
        print(f"[5b] prices {START}..{END}: {len(series)} cached, {len(todo)} to fetch",
              flush=True)
        # Tiingo health probe: a 429 (rate-limited for this IP) makes _from_tiingo
        # retry per-symbol (~25s each -> multi-hour). If unhealthy, skip Tiingo and
        # go straight to Alpaca (~1s/symbol).
        import requests as _rq
        use_tiingo = bool(settings.tiingo_api_key)
        if use_tiingo:
            try:
                _h = {
                    "Authorization": f"Token {settings.tiingo_api_key}",
                    "User-Agent": "aionis/0.1",
                }
                _r = _rq.get("https://api.tiingo.com/tiingo/daily/AAPL/prices", headers=_h,
                             params={"startDate": START, "endDate": END}, timeout=12)
                if _r.status_code != 200:
                    print(f"[5b] Tiingo unhealthy ({_r.status_code}) -> Alpaca-only",
                          flush=True)
                    use_tiingo = False
                else:
                    print("[5b] Tiingo healthy -> Tiingo+Alpaca fallback", flush=True)
            except Exception as _e:
                print(f"[5b] Tiingo probe failed ({_e}) -> Alpaca-only", flush=True)
                use_tiingo = False
        BATCH = 20
        for i in range(0, len(todo), BATCH):
            batch = todo[i:i + BATCH]
            got: dict[str, pd.Series] = {}
            if use_tiingo:
                got = _from_tiingo(batch, START, END, settings.tiingo_api_key)
            miss = [t for t in batch if t not in got]
            if miss and settings.alpaca_key_id and settings.alpaca_secret_key:
                got.update(_from_alpaca(miss, START, END,
                                        settings.alpaca_key_id, settings.alpaca_secret_key))
            for t, s in got.items():
                pd.DataFrame({"date": s.index, "adjClose": s.to_numpy()}).to_parquet(
                    pdir / f"{t}.parquet")
                series[t] = s
            done = min(i + BATCH, len(todo))
            print(f"[5b]   {done}/{len(todo)} done "
                  f"(+{len(got)}/{len(batch)} this batch; total {len(series)})",
                  flush=True)
        still_missing = [t for t in tickers if t not in series]
        px = pd.DataFrame(series)
        px.to_parquet(px_path)
        print(f"[5b] prices: {px.shape}  still-missing({len(still_missing)}): "
              f"{still_missing[:12]} -> {px_path}", flush=True)

    print("[5b] FETCH DONE", flush=True)


if __name__ == "__main__":
    main()
