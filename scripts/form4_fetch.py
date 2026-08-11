"""Bounded Form 4 insider-trading fetch (display-only, exploratory).

Small large-cap issuer set, full Trump-era window (2016→today). Polite (≥2s host
spacing via ``_policy_get``), placeholder User-Agent (SEC tolerates this for small
polite pulls — verified 2026-08-06: AAPL EFTS returned 26 filings with no 429/403).

Writes ``data/cache/form4_aggregate.parquet`` (gitignored, regenerable).
``scripts/export_terminal_data.py`` reads it into the tracked web payload.

Incremental design:
- First run (no ``data/cache/form4_aggregate.parquet``): full 2016→today cold pull.
- Subsequent runs: read the aggregate's latest filing date per issuer and fetch
  only filings SINCE that date, then append/merge into the aggregate (deduplicated
  by accession). EFTS + per-accession XML caches stay idempotent (no re-fetch on hit).

Usage::

    uv run python scripts/form4_fetch.py

Re-run safely: EFTS + XML caches are idempotent (no re-fetch on cache hit).
Incremental fetch makes warm runs fast (only new filings are fetched).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from aionis.ingest.form4_orchestrator import fetch_form4_transactions

# Large-cap issuer CIKs (SEC EDGAR public). Small bounded set keeps the pull
# polite + fast; expand cautiously (each issuer = EFTS + per-accession XML).
# Large-cap issuer CIKs (SEC EDGAR public). Bounded to 5 — the daily cron's cold
# pull (each issuer = EFTS + per-accession XML, polite ≥2s) must finish within the
# refresh job's 45-min budget; 10 issuers timed out. The data-cache action makes
# subsequent runs delta-only (fast). Expand cautiously + only after a timed cold run.
ISSUERS: dict[int, str] = {
    320193: "AAPL",
    789019: "MSFT",
    1045810: "NVDA",
    1652044: "GOOGL",
    1018724: "AMZN",
}
START = "2016-01-01"
END = "2026-08-31"
OUT = Path("data/cache/form4_aggregate.parquet")


def _get_latest_filing_date_perissuer(aggregate_path: Path) -> dict[str, str]:
    """Read aggregate and return the latest filing date per issuer ticker.

    Returns empty dict if the file doesn't exist, is empty, or PREDATES the
    ``filing_date`` column (schema migration → caller does a full pull, replacing
    the old aggregate). Issuers whose ``filing_date`` is all-NaN are omitted
    (they fall back to the full-history START, repopulating ``filing_date``).
    Dates are YYYY-MM-DD strings (EDGAR filing_date, the PIT anchor).
    """
    if not aggregate_path.exists():
        return {}
    df = pd.read_parquet(aggregate_path)
    if df.empty or "filing_date" not in df.columns:
        return {}  # pre-filing_date aggregate → first-run fallback (full pull)
    valid = df.dropna(subset=["filing_date"])
    if valid.empty:
        return {}
    latest = valid.groupby("issuer_ticker")["filing_date"].max()
    return {
        ticker: pd.Timestamp(date).strftime("%Y-%m-%d")
        for ticker, date in latest.items()
        if pd.notna(date)
    }


def _accumulate(
    running: pd.DataFrame | None,
    new: pd.DataFrame,
) -> pd.DataFrame:
    """Append ``new`` to the running aggregate with EXACT-ROW dedupe (pure).

    Used for per-issuer write-through in ``main``: each completed issuer is
    accumulated + saved immediately, so a mid-run timeout preserves the issuers
    already finished. Full-row dedupe preserves multi-transaction accessions
    (one accession reports up to ~30 transactions; accession-only dedupe would
    collapse them — regression-tested). Always accumulates — the cursor-aware
    "seed vs replace" decision lives in ``main``'s seed line, NOT here.
    """
    if running is None or running.empty:
        return new.copy()
    return pd.concat([running, new], ignore_index=True).drop_duplicates(keep="last")


def main() -> None:
    # Incremental design: read existing aggregate to get per-issuer latest filing date
    latest_dates = _get_latest_filing_date_perissuer(OUT)
    first_run = not latest_dates

    if first_run:
        print("[form4-fetch] first run: cold pull from 2016-01-01", flush=True)
    else:
        print(
            "[form4-fetch] incremental run: fetching since last cached date per issuer",
            flush=True,
        )
        print(f"[form4-fetch] latest cached dates: {latest_dates}", flush=True)

    # Initialize running aggregate from OUT if it exists and has valid cursor.
    # This enables per-issuer write-through: each completed issuer is immediately
    # merged and saved, so a timeout mid-run preserves progress for completed issuers.
    running_agg = pd.read_parquet(OUT) if (OUT.exists() and latest_dates) else None
    if running_agg is not None and not running_agg.empty:
        print(
            f"[form4-fetch] seeded running aggregate with {len(running_agg)} txns",
            flush=True,
        )

    for cik, ticker in ISSUERS.items():
        # Determine fetch window: if issuer exists in cache, start from its latest
        # filing date + 1 day; otherwise start from the full-history START (2016-01-01).
        # The +1 day avoids re-fetching filings we already have on the boundary.
        if ticker in latest_dates:
            # +1 day avoids re-fetching the last cached filing on the boundary.
            start_dt = datetime.strptime(latest_dates[ticker], "%Y-%m-%d") + timedelta(days=1)
            fetch_start = start_dt.strftime("%Y-%m-%d")
        else:
            fetch_start = START

        print(f"[form4-fetch] {ticker} (CIK {cik:010d}) {fetch_start}..{END}", flush=True)
        df = fetch_form4_transactions(cik, start=fetch_start, end=END)
        if df.empty:
            print("  -> 0 transactions (graceful skip)", flush=True)
            continue
        df["issuer_ticker"] = ticker
        buys = (df["buy_or_sell"] == "buy").sum()
        sells = (df["buy_or_sell"] == "sell").sum()
        print(f"  -> {len(df)} txns ({buys} buys / {sells} sells)", flush=True)

        # Per-issuer write-through: accumulate this issuer into the running
        # aggregate and save immediately. A timeout mid-run still preserves
        # completed issuers. _accumulate ALWAYS concats (the cursor-aware seed
        # decision already happened above); using a cursor-aware merge here would
        # drop prior issuers on the first run (latest_dates empty).
        running_agg = _accumulate(running_agg, df)
        OUT.parent.mkdir(parents=True, exist_ok=True)
        running_agg.to_parquet(OUT, index=False)
        print(
            f"[form4-fetch] checkpoint: {len(running_agg)} txns across "
            f"{running_agg['issuer_ticker'].nunique()} issuers -> {OUT}",
            flush=True,
        )

    if running_agg is None or running_agg.empty:
        print("[form4-fetch] no transactions across issuers; nothing written")
        return

    print(
        f"[form4-fetch] final: {len(running_agg)} txns across "
        f"{running_agg['issuer_ticker'].nunique()} issuers -> {OUT}",
        flush=True,
    )


if __name__ == "__main__":
    main()
