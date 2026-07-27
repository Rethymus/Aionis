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
        print(f"[5b] fetching prices {START}..{END} (Tiingo -> Alpaca, per-symbol)...",
              flush=True)
        series: dict[str, pd.Series] = {}
        if settings.tiingo_api_key:
            series = _from_tiingo(tickers, START, END, settings.tiingo_api_key)
        missing = [t for t in tickers if t not in series]
        if missing and settings.alpaca_key_id and settings.alpaca_secret_key:
            print(f"[5b]   {len(missing)} tickers missing from Tiingo -> Alpaca",
                  flush=True)
            series.update(_from_alpaca(missing, START, END,
                                       settings.alpaca_key_id, settings.alpaca_secret_key))
        still_missing = [t for t in tickers if t not in series]
        px = pd.DataFrame(series)
        px.to_parquet(px_path)
        print(f"[5b] prices: {px.shape}  still-missing({len(still_missing)}): "
              f"{still_missing[:12]} -> {px_path}", flush=True)

    print("[5b] FETCH DONE", flush=True)


if __name__ == "__main__":
    main()
