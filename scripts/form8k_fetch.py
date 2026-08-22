"""Bounded Form 8-K material-event fetch (display-only, exploratory).

50 large-cap issuers (v3 breadth expansion, 2026-08-22: the form4 5-issuer seed
+ 20 v2 mega/large caps + 25 v3 mega/large caps — browser-verified gap vs the
competitor's full-market 8-K stream; a BOUNDED step, still not full market).
Fixed window anchored at
2026-05-01 (the panel is a RECENT-event stream, not a 2016 history — the window
only grows). Polite (>=2s host spacing via ``_policy_get``), idempotent (EFTS +
per-accession caches), aggregate deduplicated by accession so reruns never
double-count and the merge is monotonic (concat + dedup, never drops rows).

Writes ``data/cache/form8k_aggregate.parquet`` (gitignored, regenerable);
``scripts/export_terminal_data.py`` reads it into the tracked web payload.

Usage::

    uv run python scripts/form8k_fetch.py
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from aionis.ingest.form8k import fetch_form8k_events

# v3 bounded universe: 50 tickers / 51 CIK entries. CIKs resolved from the SEC
# ``company_tickers.json`` snapshot via the repo's cik_resolver cache (entity
# titles cross-checked — see docs/data-intake-edgar-form8k.md G6). XOM carries
# TWO CIKs: Exxon Mobil Corp (34088) filed through the 2026-07-01 holding-
# company succession, after which ExxonMobil Holdings Corp (2115436) registered
# via 8-K12B and files onward — both are kept so the event stream is complete
# (accessions are globally unique; the aggregate dedup cannot collide).
# Request budget: 1 EFTS query per CIK per window + 2 polite requests per NEW
# filing (index.json + primary doc); per-accession caches make reruns free.
ISSUERS: dict[int, str] = {
    # form4 seed (v1)
    320193: "AAPL",
    789019: "MSFT",
    1045810: "NVDA",
    1652044: "GOOGL",
    1018724: "AMZN",
    # v2 breadth: financials
    19617: "JPM",
    1067983: "BRK-B",
    # v2 breadth: payments
    1403161: "V",
    1141391: "MA",
    # v2 breadth: healthcare / consumer staples
    731766: "UNH",
    200406: "JNJ",
    78003: "PFE",
    310158: "MRK",
    59478: "LLY",
    104169: "WMT",
    354950: "HD",
    21344: "KO",
    80424: "PG",
    # v2 breadth: energy / industrials
    93410: "CVX",
    34088: "XOM",       # Exxon Mobil Corp (pre-succession filer)
    2115436: "XOM",     # ExxonMobil Holdings Corp (8-K12B successor, 2026-07-01)
    12927: "BA",
    # v2 breadth: tech / comm / consumer discretionary
    1730168: "AVGO",
    858877: "CSCO",
    1326801: "META",
    1318605: "TSLA",
    # v3 breadth: tech / semis / software (2026-08-22, CIKs resolved from the
    # SEC company_tickers.json snapshot, entity titles cross-checked)
    1341439: "ORCL",    # Oracle Corp
    1108524: "CRM",     # Salesforce, Inc.
    1065280: "NFLX",    # Netflix Inc
    2488: "AMD",        # Advanced Micro Devices Inc
    50863: "INTC",      # Intel Corp
    804328: "QCOM",     # Qualcomm Inc/DE
    97476: "TXN",       # Texas Instruments Inc
    723125: "MU",       # Micron Technology Inc
    796343: "ADBE",     # Adobe Inc.
    51143: "IBM",       # International Business Machines Corp
    # v3 breadth: consumer staples / discretionary
    77476: "PEP",       # PepsiCo Inc
    63908: "MCD",       # McDonalds Corp
    320187: "NKE",      # Nike, Inc.
    909832: "COST",     # Costco Wholesale Corp /NEW
    # v3 breadth: industrials / defense / materials (DD = DuPont de Nemours —
    # the current listed entity; the DDGS mid-spin ticker is gone from the
    # snapshot, DD is the resolvable continuation)
    40545: "GE",        # General Electric Co (GE Aerospace filer)
    18230: "CAT",       # Caterpillar Inc
    315189: "DE",       # Deere & Co
    1666700: "DD",      # DuPont de Nemours, Inc.
    773840: "HON",      # Honeywell International Inc
    100885: "UNP",      # Union Pacific Corp
    936468: "LMT",      # Lockheed Martin Corp
    40533: "GD",        # General Dynamics Corp
    101829: "RTX",      # RTX Corp
    # v3 breadth: financials (bounded — v2 already carries JPM/BRK-B; the
    # suggested pool's trailing MS/SCHW were the two dropped to stay at 25)
    4962: "AXP",        # American Express Co
    886982: "GS",       # Goldman Sachs Group Inc
}
START = "2026-05-01"
END = date.today().isoformat()
OUT = Path("data/cache/form8k_aggregate.parquet")


def main() -> None:
    print(f"[form8k-fetch] window {START}..{END}", flush=True)
    running = pd.read_parquet(OUT) if OUT.exists() else None
    if running is not None and not running.empty:
        print(f"[form8k-fetch] seeded aggregate: {len(running)} filings", flush=True)

    for cik, ticker in ISSUERS.items():
        df = fetch_form8k_events(cik, ticker=ticker, start=START, end=END)
        if df.empty:
            print(f"[form8k-fetch] {ticker}: 0 filings (graceful skip)", flush=True)
            continue
        cats = df["category"].value_counts().to_dict()
        print(f"[form8k-fetch] {ticker}: {len(df)} filings {cats}", flush=True)
        running = df if running is None else pd.concat([running, df], ignore_index=True)
        running = (
            running.drop_duplicates(subset=["accession"], keep="last")
            .sort_values("filing_date", ascending=False)
            .reset_index(drop=True)
        )
        OUT.parent.mkdir(parents=True, exist_ok=True)
        running.to_parquet(OUT, index=False)
        print(f"[form8k-fetch] checkpoint: {len(running)} filings -> {OUT}", flush=True)

    if running is None or running.empty:
        print("[form8k-fetch] no filings; nothing written", flush=True)
        return
    print(
        f"[form8k-fetch] final: {len(running)} filings across "
        f"{running['ticker'].nunique()} issuers -> {OUT}",
        flush=True,
    )


if __name__ == "__main__":
    main()
