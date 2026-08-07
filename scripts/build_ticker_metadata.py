"""Build ticker → (name, sector) metadata cache for the fintech terminal.

Display-only: the terminal needs human-readable names + sector grouping for
the picks view. Research pipeline does NOT consume this — it stays a display
layer (analogous to ``form4.json``, ``cot.json``).

Data sources (all permissive, all real):
  - **A-share names**: ``ZhuLinsen/daily_stock_analysis`` GitHub-hosted
    ``stocks.index.json`` (~31K entries, ~5K of which are CN common shares).
    Raw factual ticker+name data — not copyrightable (Feist v. Rural; the
    list is sourced from public exchanges). We use it as display metadata
    only; we do not redistribute the raw list. This is more reliable than
    East Money push2 (which intermittently refuses connections) and adds
    zero runtime deps (akshare's heavy wrapper would pull lxml/html5lib/
    jsonpath/… into the lock — this drops the wrapper, keeps the data).
  - **US names**: SEC ``company_tickers.json`` (US Government public domain,
    PIT-trivial, permissive — same source EDGAR itself surfaces).
  - **US sectors**: ``data/cache/phase_d_sic_map.parquet`` (already cached
    from EDGAR SIC pulls — public domain).
  - **A-share sectors**: not in the GitHub file; left empty (sector breakdown
    shows US SIC until a permissive A-share industry source lands).

Output: ``data/cache/ticker_metadata.parquet`` with columns
``[ticker, region, name, sector]``. ``ticker`` matches the OOS panel format
(``DVN`` for US, ``sh.688041`` for CN).

Usage::

    uv run python scripts/build_ticker_metadata.py              # build/refresh
    uv run python scripts/build_ticker_metadata.py --no-cache   # force re-fetch

Politeness (G7): single call to each endpoint (bulk list, not per-ticker),
2s spacing between hosts. No API key. Failures degrade gracefully
(ticker remains in cache with empty name — never blocks export).
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import pandas as pd

from aionis.ingest.universe import _policy_get  # reuse polite HTTP primitive (G7 spacing + retry)

CACHE = Path("data/cache/ticker_metadata.parquet")

# GitHub-hosted A-share + HK + US ticker-name map. Format: rows of
# [symbol_with_exchange, code, name, pinyin, abbrev, aliases, country, type, active, ...].
# We filter country=="CN" and type=="stock" for A-shares.
CN_LISTING_URL = (
    "https://raw.githubusercontent.com/ZhuLinsen/daily_stock_analysis/main/"
    "apps/dsa-web/public/stocks.index.json"
)
SEC_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_UA = "Aionis research contact@example.com"  # SEC fair-access: real-reachable contact


def _to_baostock_code(code: str, exchange: str) -> str:
    """Convert (code, exchange) → baostock 'sh.XXXX' / 'sz.XXXX' / 'bj.XXXX'.

    Exchange tag comes from the listing file's symbol-with-exchange (e.g.
    ``000001.SZ``); the code prefix is the canonical routing key (same
    convention baostock itself uses).
    """
    ex = exchange.upper()
    if ex == "SH":
        return f"sh.{code}"
    if ex == "SZ":
        return f"sz.{code}"
    if ex == "BJ":
        return f"bj.{code}"
    # Fallback by code prefix.
    head = code[0] if code else "0"
    if head in {"6", "9"}:
        return f"sh.{code}"
    if head in {"4", "8"}:
        return f"bj.{code}"
    return f"sz.{code}"


def _board_classification(code: str) -> str:
    """A-share exchange-board tier from code prefix (lightweight sector proxy).

    The GitHub listing lacks industry data; board tier is a real, meaningful
    categorization for display (科创板 = STAR/tech-heavy, 创业板 = ChiNext/growth,
    主板 = main board, 北交所 = Beijing). Not an industry sector, but better
    than 'Unclassified' for the terminal's sector-grouping view.
    """
    head = code[0] if code else "0"
    if code.startswith("688"):
        return "科创板 (STAR Market)"
    if code.startswith("300") or code.startswith("301"):
        return "创业板 (ChiNext)"
    if head in {"6"}:
        return "沪主板 (SSE Main)"
    if code.startswith("003") or code.startswith("002") or code.startswith("000"):
        return "深主板 (SZSE Main)"
    if head in {"8", "4", "9"}:
        return "北交所 (BSE)"
    return "其他 (Other)"


def fetch_a_share_metadata() -> pd.DataFrame:
    """Pull A-share (code, name) from the GitHub-hosted listing. 1 HTTP call."""
    try:
        resp = _policy_get(CN_LISTING_URL, timeout=30, total_attempts=2)
        rows = resp.json()
    except Exception as exc:  # pragma: no cover - network-conditional
        print(f"  [warn] A-share listing fetch failed: {exc!r}; returning empty cn frame")
        return pd.DataFrame(columns=["ticker", "region", "name", "sector"])
    out = []
    for r in rows:
        # Row schema: [symbol_with_ex, code, name, pinyin, abbrev,
        # aliases, country, type, active, ...]
        if len(r) < 8:
            continue
        symbol_with_ex = str(r[0])
        code = str(r[1])
        name = str(r[2])
        country = str(r[6])
        kind = str(r[7])
        if country != "CN" or kind != "stock":
            continue
        if "." not in symbol_with_ex:
            continue
        _, exchange = symbol_with_ex.split(".", 1)
        # Keep only common-share A-shares on SH/SZ/BJ (skip NQ/other OTC).
        if exchange.upper() not in {"SH", "SZ", "BJ"}:
            continue
        ticker = _to_baostock_code(code, exchange)
        sector = _board_classification(code)
        out.append({"ticker": ticker, "region": "cn", "name": name, "sector": sector})
    return pd.DataFrame(out)


def fetch_us_metadata() -> pd.DataFrame:
    """Pull US (ticker, title) via SEC company_tickers.json. 1 HTTP call."""
    headers = {"User-Agent": SEC_UA}  # SEC fair-access policy needs a real-reachable contact
    try:
        resp = _policy_get(SEC_URL, headers=headers, timeout=30, total_attempts=2)
    except Exception as exc:  # pragma: no cover - network-conditional
        print(f"  [warn] SEC fetch failed: {exc!r}; returning empty us frame")
        return pd.DataFrame(columns=["ticker", "region", "name", "sector"])
    payload: dict[str, Any] = resp.json()
    rows = []
    for entry in payload.values():
        ticker = str(entry.get("ticker") or "").strip().upper()
        title = (entry.get("title") or "").strip()
        if not ticker:
            continue
        rows.append({"ticker": ticker, "region": "us", "name": title, "sector": ""})
    df = pd.DataFrame(rows)
    # Join SIC sector if cached.
    sic_path = Path("data/cache/phase_d_sic_map.parquet")
    if sic_path.exists():
        sic = pd.read_parquet(sic_path)[["ticker", "sic_description"]]
        sic = sic.rename(columns={"sic_description": "sector"})
        sic["ticker"] = sic["ticker"].str.upper()
        # Where SIC has a sector, prefer it; else keep empty.
        df = df.drop(columns=["sector"]).merge(sic, on="ticker", how="left")
        df["sector"] = df["sector"].fillna("")
    return df


def build(force_refresh: bool = False) -> pd.DataFrame:
    """Build the ticker_metadata cache. Returns the merged DataFrame."""
    if CACHE.exists() and not force_refresh:
        return pd.read_parquet(CACHE)
    print("[ticker_metadata] fetching A-share names + industry (East Money push2)…")
    cn = fetch_a_share_metadata()
    time.sleep(2.0)  # G7 politeness between hosts
    print(f"  cn rows: {len(cn)}")
    print("[ticker_metadata] fetching US names (SEC company_tickers.json)…")
    us = fetch_us_metadata()
    print(f"  us rows: {len(us)}")
    df = pd.concat([cn, us], ignore_index=True)
    df = df.drop_duplicates(subset=["ticker", "region"], keep="first")
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(CACHE, index=False)
    print(f"[ticker_metadata] cached {len(df)} rows → {CACHE}")
    return df


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--no-cache", action="store_true", help="force re-fetch even if cache exists")
    args = ap.parse_args()
    df = build(force_refresh=args.no_cache)
    by_region = df["region"].value_counts().to_dict()
    print(json.dumps({"rows": len(df), "by_region": by_region}, indent=2))


if __name__ == "__main__":
    main()
