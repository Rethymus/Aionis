"""Build regime global DY spillover layer (US<->CN equity markets).

Loads US and CN price panels, computes equal-weighted market returns, aligns on
trading date intersection, and computes rolling Diebold-Yilmaz total spillover.

Run:  uv run python scripts/build_regime_global.py
Output: data/cache/regime_global_dy.parquet (gitignored)

Anti-leakage: rolling windows are past-only; exploratory (no ledger write).
"""

from __future__ import annotations

import hashlib

import pandas as pd

from aionis.config import settings
from aionis.features.regime_global import dy_total_spillover, equal_weighted_market_return

# Data paths (gitignored, cache only)
CACHE = settings.data_dir / "cache"
US_PRICES_PATH = CACHE / "phase_b_prices.parquet"
CN_PRICES_PATH = CACHE / "ashare_prices_csi300.parquet"
OUTPUT_PATH = CACHE / "regime_global_dy.parquet"


def main() -> None:
    print("[regime-global] Building Diebold-Yilmaz total spillover layer...", flush=True)

    # Load US price panel (wide: dates × S&P500 tickers, adjClose)
    if not US_PRICES_PATH.exists():
        raise FileNotFoundError(f"US price panel not found: {US_PRICES_PATH}")
    us_prices = pd.read_parquet(US_PRICES_PATH)
    print(f"[regime-global] US prices: {us_prices.shape}", flush=True)

    # Load CN price panel (long: [date, ticker, open, high, low, close, volume, tradestatus])
    if not CN_PRICES_PATH.exists():
        raise FileNotFoundError(f"CN price panel not found: {CN_PRICES_PATH}")
    cn_long = pd.read_parquet(CN_PRICES_PATH)
    print(f"[regime-global] CN prices (long): {cn_long.shape}", flush=True)

    # Pivot CN to wide format (dates × tickers, close)
    cn_prices = cn_long.pivot(index="date", columns="ticker", values="close")
    print(f"[regime-global] CN prices (wide): {cn_prices.shape}", flush=True)

    # Compute equal-weighted market returns (skip NaN for suspensions)
    us_ret = equal_weighted_market_return(us_prices)
    cn_ret = equal_weighted_market_return(cn_prices)
    print(f"[regime-global] US returns: {len(us_ret)} non-NaN", flush=True)
    print(f"[regime-global] CN returns: {len(cn_ret)} non-NaN", flush=True)

    # Align on intersection of trading dates (inner join)
    aligned = pd.DataFrame({"us": us_ret, "cn": cn_ret}).dropna()
    print(f"[regime-global] Aligned trading dates: {len(aligned)}", flush=True)

    # Compute rolling DY spillover (window=250, horizon=10)
    spillover = dy_total_spillover(
        aligned["us"],
        aligned["cn"],
        window=250,
        horizon=10,
    )
    non_nan = spillover.notna().sum()
    print(f"[regime-global] Spillover series: {len(spillover)} dates, {non_nan} non-NaN",
          flush=True)

    # Compute sha256 of the output data
    spillover_bytes = spillover.values.tobytes()
    data_hash = hashlib.sha256(spillover_bytes).hexdigest()[:8]
    print(f"[regime-global] Data sha256: {data_hash}", flush=True)

    # Log date range and statistics
    if non_nan > 0:
        valid = spillover.dropna()
        print(f"[regime-global] Date range: {valid.index[0]} to {valid.index[-1]}", flush=True)
        print(f"[regime-global] Statistics: mean={valid.mean():.4f}, min={valid.min():.4f}, "
              f"max={valid.max():.4f}, std={valid.std():.4f}", flush=True)

    # Write to parquet (gitignored)
    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    # Convert Series to DataFrame for parquet export
    spillover_df = spillover.to_frame("total_spillover")
    spillover_df.to_parquet(OUTPUT_PATH)
    print(f"[regime-global] Written: {OUTPUT_PATH}", flush=True)
    print("[regime-global] BUILD DONE", flush=True)


if __name__ == "__main__":
    main()
