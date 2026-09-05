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

# Large-cap issuer CIKs (SEC EDGAR public). Bounded universe — each issuer =
# 1 EFTS query + per-accession XML, polite ≥2s. The 5-issuer seed kept the
# daily cron's cold pull inside its budget; v2 breadth (2026-08-23) adds 25
# mega/large caps (CIKs resolved from the SEC company_tickers.json snapshot
# via cik_resolver and cross-checked — the same entries the form8k v2/v3
# universes verified live). A cold 2016→today pull at 30 issuers is hours of
# polite spacing, so the bounded breadth run uses ``--start 2026-01-01`` and
# export_form4's retain-merge keeps the committed 2013-2025 history.
ISSUERS: dict[int, str] = {
    # form4 seed (v1, full 2016+ history in the committed panel)
    320193: "AAPL",
    789019: "MSFT",
    1045810: "NVDA",
    1652044: "GOOGL",
    1018724: "AMZN",
    # v2 breadth (2026 window): financials / payments
    19617: "JPM",
    1067983: "BRK-B",
    1403161: "V",
    1141391: "MA",
    # healthcare / staples
    731766: "UNH",
    200406: "JNJ",
    78003: "PFE",
    310158: "MRK",
    59478: "LLY",
    104169: "WMT",
    354950: "HD",
    21344: "KO",
    80424: "PG",
    # energy / industrials
    93410: "CVX",
    34088: "XOM",
    12927: "BA",
    # tech / comm / consumer discretionary
    1730168: "AVGO",
    858877: "CSCO",
    1326801: "META",
    1318605: "TSLA",
    # v2 additions from the form8k v3 set
    1341439: "ORCL",
    1108524: "CRM",
    1065280: "NFLX",
    2488: "AMD",
    50863: "INTC",
}
START = "2016-01-01"
# Dynamic end: the old hardcoded "2026-08-31" froze the incremental window at
# the month it was written — filings after that date never entered the cache
# and the committed panel's as_of stuck at 2026-08-25.
END = datetime.now().strftime("%Y-%m-%d")
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
    import sys

    # ``--start YYYY-MM-DD`` bounds a breadth run (e.g. 30 issuers × 2026 YTD)
    # without touching the incremental per-issuer cursor for cached issuers.
    cli_start = None
    if "--start" in sys.argv:
        i = sys.argv.index("--start")
        if i + 1 >= len(sys.argv):
            raise SystemExit("form4_fetch: --start requires a YYYY-MM-DD value")
        cli_start = sys.argv[i + 1]

    # Incremental design: read existing aggregate to get per-issuer latest filing date
    latest_dates = _get_latest_filing_date_perissuer(OUT)
    first_run = not latest_dates
    bounded = cli_start is not None
    if bounded:
        print(
            f"[form4-fetch] bounded breadth run: cold window from {cli_start} "
            "(committed pre-window history is preserved by export_form4's "
            "retain-merge)",
            flush=True,
        )

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
            fetch_start = cli_start if bounded else START

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
