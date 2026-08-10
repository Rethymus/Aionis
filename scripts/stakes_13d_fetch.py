"""Bounded SC 13D institutional stake fetch (display-only, exploratory).

Small large-cap issuer set, full Trump-era window (2016→today). Polite (≥2s host
spacing via the fetcher's ``_policy_get``), placeholder User-Agent (SEC tolerates
this for small polite pulls).

Writes ``data/cache/efts_13d_*.json`` (gitignored, regenerable) — raw EFTS
full-text search hits. ``scripts/export_terminal_data.py`` reads them into the
tracked web payload.

Usage::

    uv run python scripts/stakes_13d_fetch.py

Re-run safely: EFTS cache is idempotent (no re-fetch on cache hit).
"""
from __future__ import annotations

from aionis.ingest.stakes_13d_efts import _fetch_efts_hits

# Large-cap issuer CIKs (SEC EDGAR public). Small bounded set keeps the pull
# polite + fast. Mirrors the form4_fetch set; expand cautiously if needed.
# Extended set to include companies with actual 13D activity (activist targets
# and smaller companies where 13D filings occur).
ISSUERS: dict[int, str] = {
    # Large-cap tech (for consistency with form4_fetch)
    320193: "AAPL",
    789019: "MSFT",
    1045810: "NVDA",
    1652044: "GOOGL",
    1018724: "AMZN",
    # Companies with recent 13D activity (top 20 by latest filing date)
    1690820: "CVNA",      # Carvana - most recent 13D activity
    70858: "BAC",         # Bank of America
    1590955: "DISCA",     # Discovery/Form A
    38777: "AMGN",        # Amgen
    1858681: "META",      # Meta Platforms
    72971: "BMY",         # Bristol Myers Squibb
    1001250: "TWTR",      # Twitter
    1274494: "FOXA",      # Fox Form A
    1783180: "TSLA",      # Tesla
    2012383: "SPCE",      # Virgin Galactic
    350698: "AMC",        # AMC Entertainment
    1039684: "GME",       # GameStop
    1067983: "PLTR",      # Palantir
    753308: "NVAX",       # Novavax
    1335258: "RIVN",      # Rivian
    27904: "BBY",         # Best Buy
    1091667: "COIN",      # Coinbase
    886982: "HOOD",       # Robinhood
    1992243: "AFRM",      # Affirm
    32604: "ADP",         # ADP
}
START = "2015-01-01"  # Matches existing cache pattern
END = "2026-08-31"    # Extended beyond existing 2026-06-30 to capture new filings


def main() -> None:
    for cik, ticker in ISSUERS.items():
        print(f"[13d-fetch] {ticker} (CIK {cik:010d}) {START}..{END}", flush=True)
        hits = _fetch_efts_hits(
            issuer_cik=cik,
            start=START,
            end=END,
        )
        if not hits:
            print("  -> 0 filings (graceful skip)", flush=True)
            continue
        print(f"  -> {len(hits)} filing(s)", flush=True)


if __name__ == "__main__":
    main()
