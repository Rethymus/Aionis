"""Track B volume fetch (Turnover, Amihud, Beta require volume + benchmark).

Pure data preparation: fetches volume data for the OOS-resolvable universe
and SPY benchmark, caches to gitignored parquet. No model, no rank-IC,
no ledger writes, no frozen config touches.

Usage:
    uv run python scripts/track_b_fetch_volume.py

Output:
    data/cache/volumes/<T>.parquet (per-ticker volume series)
    data/cache/spy_benchmark.parquet (SPY adjClose for beta calculation)

Alpaca-only: volume is available in bars endpoint (v field). SPY is fetched
as a single ticker. Polite: >=2s spacing between calls via shared HTTP policy.
"""
from __future__ import annotations

import time

import pandas as pd
import structlog

from aionis.config import settings
from aionis.ingest.market import _from_alpaca, _volume_from_alpaca
from aionis.ingest.universe import build_oos_resolvable_universe

log = structlog.get_logger()

# Date range matches phase_b_prices.parquet (2011-2016 train + 2017-2026 OOS)
START, END = "2011-01-01", "2026-06-30"
CACHE_DIR = settings.data_dir / "cache"
VOLUME_DIR = CACHE_DIR / "volumes"
SPY_PATH = CACHE_DIR / "spy_benchmark.parquet"

# Polite delay: >=2s between batch API calls
POLITE_DELAY = 2.0


def _fetch_spy_benchmark() -> pd.DataFrame:
    """Fetch SPY adjusted close for beta calculation (Alpaca).

    Returns DataFrame with [date, adjClose] columns.
    """
    if not settings.alpaca_key_id or not settings.alpaca_secret_key:
        raise RuntimeError("Alpaca keys required for SPY benchmark")

    log.info("fetch_spy_start", symbol="SPY", start=START, end=END)

    spy_data = _from_alpaca(
        ["SPY"],
        START,
        END,
        settings.alpaca_key_id,
        settings.alpaca_secret_key,
    )

    if "SPY" not in spy_data or spy_data["SPY"].empty:
        raise RuntimeError("SPY returned empty series")

    spy_series = spy_data["SPY"]
    df = pd.DataFrame({"date": spy_series.index, "adjClose": spy_series.to_numpy(float)})

    log.info(
        "fetch_spy_complete",
        rows=len(df),
        date_min=str(df["date"].min()),
        date_max=str(df["date"].max()),
    )

    return df


def main() -> None:
    """Main fetch pipeline: volume for all tickers + SPY benchmark."""
    log.info("track_b_volume_fetch_start")

    # 1. Build OOS-resolvable universe
    u = build_oos_resolvable_universe()
    tickers = u["tickers"]
    log.info("universe_loaded", n_tickers=len(tickers))

    if not settings.alpaca_key_id or not settings.alpaca_secret_key:
        raise RuntimeError(
            "Alpaca keys (ALPACA_KEY_ID, ALPACA_SECRET_KEY) required for volume fetch"
        )

    # 2. Create volume cache directory
    VOLUME_DIR.mkdir(parents=True, exist_ok=True)

    # 3. Fetch volume per ticker (resumable)
    series: dict[str, pd.Series] = {}
    for t in tickers:
        fp = VOLUME_DIR / f"{t}.parquet"
        if fp.exists():
            df = pd.read_parquet(fp)
            if not df.empty and "volume" in df.columns:
                series[t] = pd.Series(
                    df["volume"].to_numpy(float),
                    index=pd.to_datetime(df["date"]).dt.normalize(),
                    name=t,
                )

    todo = [t for t in tickers if t not in series]
    log.info("volume_cache_status", cached=len(series), to_fetch=len(todo))

    # Fetch in small batches (still per-symbol API calls, but progress tracking)
    BATCH = 10
    failed: list[str] = []

    for i in range(0, len(todo), BATCH):
        batch = todo[i : i + BATCH]

        # Alpaca volume fetch (per-symbol, polite spacing via _policy_get)
        got = _volume_from_alpaca(
            batch,
            START,
            END,
            settings.alpaca_key_id,
            settings.alpaca_secret_key,
        )

        # Cache each successfully fetched volume series
        for t, vol_series in got.items():
            vol_df = pd.DataFrame(
                {"date": vol_series.index, "volume": vol_series.to_numpy(float)}
            )
            vol_df.to_parquet(VOLUME_DIR / f"{t}.parquet", index=False)
            series[t] = vol_series

        # Track failures
        batch_failed = [t for t in batch if t not in got]
        failed.extend(batch_failed)

        done = min(i + BATCH, len(todo))
        log.info(
            "volume_batch_progress",
            batch_done=done,
            batch_total=len(todo),
            this_batch_fetched=len(got),
            this_batch_failed=len(batch_failed),
            total_cached=len(series),
        )

        # Polite delay between batches (skip after last batch)
        if done < len(todo):
            time.sleep(POLITE_DELAY)

    # 4. Fetch SPY benchmark
    if SPY_PATH.exists():
        log.info("spy_benchmark_cached", path=str(SPY_PATH))
    else:
        spy_df = _fetch_spy_benchmark()
        spy_df.to_parquet(SPY_PATH, index=False)
        log.info("spy_benchmark_saved", path=str(SPY_PATH))

    # 5. Summary report
    log.info(
        "track_b_volume_fetch_complete",
        n_tickers_total=len(tickers),
        n_volume_success=len(series),
        n_volume_failed=len(failed),
        volume_cache_dir=str(VOLUME_DIR),
        spy_path=str(SPY_PATH),
        failed_sample=failed[:20],
    )

    print("\n" + "=" * 60)
    print("Track B Volume Fetch Report")
    print("=" * 60)
    print(f"\nTotal tickers: {len(tickers)}")
    print(f"Volume fetched: {len(series)}")
    print(f"Volume failed: {len(failed)}")
    print(f"Cache dir: {VOLUME_DIR}")
    print(f"SPY benchmark: {SPY_PATH}")

    if failed:
        print(f"\nFailed tickers (first {min(50, len(failed))}):")
        for t in failed[:50]:
            print(f"  - {t}")
        if len(failed) > 50:
            print(f"  ... and {len(failed) - 50} more")

    print("=" * 60)


if __name__ == "__main__":
    main()
