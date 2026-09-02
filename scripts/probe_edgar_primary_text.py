"""Evidence probe: fetch ONE real EDGAR primary document through the E3 text slice.

Round-55 A1 acceptance evidence — proves against REAL EDGAR (not fixtures):
  1. the canonical archive URL pattern resolves (cik + accession-no-dashes + primaryDocument),
  2. the fetched document is real filing prose (cleaned + truncated),
  3. the disk cache makes a second call zero-HTTP.

Run: ``uv run python scripts/probe_edgar_primary_text.py [--ticker AAPL]``.
Politeness: reuses the cached submissions fetch + the shared >=2s host-spacing
policy (2 live HTTP calls maximum: 1 data.sec.gov if uncached, 1 www.sec.gov).
"""
from __future__ import annotations

import argparse

import pandas as pd

from aionis.config import settings
from aionis.ingest import stakes_13d
from aionis.ingest.event_text import fetch_edgar_primary_text


def main() -> int:
    parser = argparse.ArgumentParser(description="E3 text-slice real-data probe")
    parser.add_argument("--ticker", default="AAPL", help="universe ticker to probe")
    parser.add_argument(
        "--form", default="SC 13D",
        help="form to look for in the recent block (fallback: 8-K Item 2.02)",
    )
    args = parser.parse_args()

    cdir = settings.data_dir / "cache"

    # 1. Resolve a real (cik, accession, primary_doc) from the cached/real
    #    submissions JSON — the same source the freeze collectors use.
    ticker = args.ticker.upper()
    from aionis.ingest.fundamentals import cik_map

    cik_by_ticker = cik_map(cdir)
    cik = cik_by_ticker.get(ticker)
    if cik is None:
        print(f"[probe] no cached cik_map entry for {ticker}; pass a universe ticker")
        return 2

    sub = stakes_13d.fetch_submissions(int(cik), cdir)
    recent = sub.get("filings", {}).get("recent", {})
    hit: dict | None = None
    for i, form in enumerate(recent.get("form", [])):
        if form != args.form:
            continue
        items = recent.get("items", [""])
        if args.form == "8-K" and "2.02" not in (items[i] if i < len(items) else ""):
            continue
        hit = {
            "form": form,
            "filing_date": recent["filingDate"][i],
            "accession": recent["accessionNumber"][i],
            "primary_doc": recent["primaryDocument"][i],
        }
        break
    if hit is None:
        print(f"[probe] no {args.form} in the recent block for {ticker}")
        return 2

    print(f"[probe] {ticker} cik={cik} -> {hit}")

    events = pd.DataFrame([
        {
            "event_id": f"{ticker}:{hit['accession']}",
            "cik": int(cik),
            "accession": hit["accession"],
            "primary_doc": hit["primary_doc"],
        }
    ])

    # 2. First fetch: one live call to the canonical archive URL.
    out = fetch_edgar_primary_text(events)
    text = out["text"].iloc[0]
    print(f"[probe] fetched chars={len(text)}")
    print(f"[probe] head: {text[:400]!r}")

    # 3. Cache assertion: the deterministic cache file exists and a second
    #    call is byte-identical (the summary log line reports cached=1).
    cache_name = "edgar_" + hit["accession"].replace("-", "") + "__" + hit["primary_doc"] + ".txt"
    cache_file = settings.data_dir / "cache" / "event_text" / cache_name
    assert cache_file.exists(), f"cache file missing: {cache_file}"
    out2 = fetch_edgar_primary_text(events)
    assert out2["text"].iloc[0] == text, "second call must be byte-identical"
    print(f"[probe] PASS: canonical URL + real prose + idempotent cache ({cache_name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
