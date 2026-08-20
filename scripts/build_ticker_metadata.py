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
  - **A-share industries**: baostock ``query_stock_industry`` — CSRC (证监会)
    industry classification, free + anonymous (single login session, one bulk
    query). 7-gate intake: ``docs/data-intake-baostock-industry.md`` (PASS,
    display-only). Fetched lazily (baostock is intentionally NOT a core
    dependency, mirroring ``aionis/ingest/ashare_price.py``); rows missing an
    industry (e.g. delisted) fall back to the exchange-board tier.
  - **US names**: SEC ``company_tickers.json`` (US Government public domain,
    PIT-trivial, permissive — same source EDGAR itself surfaces).
  - **US sectors**: ``data/cache/phase_d_sic_map.parquet`` (already cached
    from EDGAR SIC pulls — public domain).

Output: ``data/cache/ticker_metadata.parquet`` with columns
``[ticker, region, name, sector, cn_tier]``. ``ticker`` matches the OOS panel
format (``DVN`` for US, ``sh.688041`` for CN). ``sector`` for CN rows is the
CSRC industry (formatted ``证监会: <门类代码+名称>``) with the exchange-board
tier as fallback; ``cn_tier`` always keeps the board tier (empty for US).

Usage::

    uv run python scripts/build_ticker_metadata.py              # build/refresh
    uv run python scripts/build_ticker_metadata.py --no-cache   # force re-fetch
    # with the CSRC industry upgrade (baostock is a lazy, ad-hoc dependency):
    uv run --with baostock python scripts/build_ticker_metadata.py --no-cache

Politeness (G7): single call to each HTTP endpoint (bulk list, not
per-ticker), 2s spacing between hosts; baostock is a login-session API —
ONE anonymous login + ONE bulk full-universe query (server-side pagination)
+ logout, never per-ticker requests. No API key. Failures degrade
gracefully (ticker remains in cache with tier sector / empty name — never
blocks export).
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
CN_INDUSTRY_CACHE = Path("data/cache/cn_industry.parquet")

# GitHub-hosted A-share + HK + US ticker-name map. Format: rows of
# [symbol_with_exchange, code, name, pinyin, abbrev, aliases, country, type, active, ...].
# We filter country=="CN" and type=="stock" for A-shares.
CN_LISTING_URL = (
    "https://raw.githubusercontent.com/ZhuLinsen/daily_stock_analysis/main/"
    "apps/dsa-web/public/stocks.index.json"
)
SEC_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_UA = "Aionis research contact@example.com"  # SEC fair-access: real-reachable contact

# Prefix marking the CN sector string's classification scheme (self-identifying
# on the display layer — the terminal must never present tier and industry as
# the same kind of thing).
CSRC_PREFIX = "证监会: "


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
    """A-share exchange-board tier from code prefix (auxiliary ``cn_tier`` column).

    The CN ``sector`` column is upgraded to the CSRC industry classification
    (baostock, see :func:`fetch_cn_industry`); board tier remains as the
    always-present ``cn_tier`` column AND as the fallback ``sector`` for rows
    where the industry lookup misses (e.g. delisted, or baostock
    unavailable). Not an industry — kept visually distinct via the
    ``证监会: `` prefix on true industry strings.
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
    """Pull A-share (code, name, tier) from the GitHub-hosted listing. 1 HTTP call."""
    try:
        resp = _policy_get(CN_LISTING_URL, timeout=30, total_attempts=2)
        rows = resp.json()
    except Exception as exc:  # pragma: no cover - network-conditional
        print(f"  [warn] A-share listing fetch failed: {exc!r}; returning empty cn frame")
        return pd.DataFrame(columns=["ticker", "region", "name", "cn_tier"])
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
        out.append({
            "ticker": ticker,
            "region": "cn",
            "name": name,
            "cn_tier": _board_classification(code),
        })
    return pd.DataFrame(out)


def _require_baostock() -> Any:
    """Lazy-import baostock (intentionally not a core dependency).

    Mirrors ``aionis.ingest.ashare_price._require_baostock``. BSD-licensed
    client (7-gate: ``docs/data-intake-baostock-industry.md`` G1) — activate
    ad hoc with ``uv run --with baostock …``; never add to the core lock.
    """
    try:
        import baostock as bs
    except ImportError as e:  # pragma: no cover - exercised only without baostock
        raise ImportError(
            "baostock is required for the CN CSRC-industry (证监会) upgrade. It "
            "is intentionally NOT a core dependency. Activate with "
            "`uv run --with baostock …` (BSD license, passes the allowlist — "
            "docs/data-intake-baostock-industry.md)."
        ) from e
    return bs


def fetch_cn_industry(force_refresh: bool = False) -> pd.DataFrame:
    """Pull the CSRC (证监会) industry classification snapshot via baostock.

    7-gate: ``docs/data-intake-baostock-industry.md`` (PASS, display-only).
    G7 politeness: ONE anonymous login + ONE bulk full-universe query (server
    pagination driven by ``rs.next()``) + logout — never per-ticker requests.
    G4 snapshot: idempotent cache at ``data/cache/cn_industry.parquet``;
    per-row ``update_date`` keeps the snapshot instant auditable (G2/G3).
    Failures return an empty frame — the caller falls back to board tier.
    """
    if CN_INDUSTRY_CACHE.exists() and not force_refresh:
        cached = pd.read_parquet(CN_INDUSTRY_CACHE)
        print(f"[cn_industry] cache hit: {len(cached)} rows "
              f"(update_date max={cached['update_date'].max() if len(cached) else 'n/a'})")
        return cached
    try:
        bs = _require_baostock()
        lg = bs.login()
        if str(getattr(lg, "error_code", "0")) != "0":
            raise RuntimeError(
                f"baostock login failed: code={getattr(lg, 'error_code', '?')} "
                f"msg={getattr(lg, 'error_msg', '?')}"
            )
        try:
            rs = bs.query_stock_industry(code="", date="")
            if str(getattr(rs, "error_code", "0")) != "0":
                raise RuntimeError(
                    f"query_stock_industry failed: code={getattr(rs, 'error_code', '?')} "
                    f"msg={getattr(rs, 'error_msg', '?')}"
                )
            rows: list[list[str]] = []
            while rs.next():  # type: ignore[union-attr]
                rows.append(list(rs.get_row_data()))  # type: ignore[union-attr]
            cols = list(getattr(rs, "fields", []) or [])
        finally:
            try:
                bs.logout()
            except Exception:  # noqa: BLE001 - logout is best-effort
                pass
        raw = pd.DataFrame(rows, columns=cols or ["updateDate", "code", "code_name", "industry"])
        df = pd.DataFrame({
            "ticker": raw["code"].astype(str),
            "industry": raw["industry"].astype(str).str.strip(),
            "update_date": raw["updateDate"].astype(str),
        }).drop_duplicates(subset=["ticker"], keep="first")
        CN_INDUSTRY_CACHE.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(CN_INDUSTRY_CACHE, index=False)
        print(f"[cn_industry] cached {len(df)} rows "
              f"(update_date max={df['update_date'].max()}) → {CN_INDUSTRY_CACHE}")
        return df
    except Exception as exc:  # pragma: no cover - network/dependency-conditional
        print(f"  [warn] CN industry fetch failed: {exc!r}; "
              "CN sector falls back to exchange-board tier")
        return pd.DataFrame(columns=["ticker", "industry", "update_date"])


def fetch_us_metadata() -> pd.DataFrame:
    """Pull US (ticker, title) via SEC company_tickers.json. 1 HTTP call."""
    headers = {"User-Agent": SEC_UA}  # SEC fair-access policy needs a real-reachable contact
    try:
        resp = _policy_get(SEC_URL, headers=headers, timeout=30, total_attempts=2)
    except Exception as exc:  # pragma: no cover - network-conditional
        print(f"  [warn] SEC fetch failed: {exc!r}; returning empty us frame")
        return pd.DataFrame(columns=["ticker", "region", "name", "sector", "cn_tier"])
    payload: dict[str, Any] = resp.json()
    rows = []
    for entry in payload.values():
        ticker = str(entry.get("ticker") or "").strip().upper()
        title = (entry.get("title") or "").strip()
        if not ticker:
            continue
        rows.append({"ticker": ticker, "region": "us", "name": title, "sector": "", "cn_tier": ""})
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
        df["cn_tier"] = ""
    return df


def _merge_cn_sector(cn: pd.DataFrame, industry: pd.DataFrame) -> pd.DataFrame:
    """Upgrade CN ``sector`` to the CSRC industry; board tier as fallback.

    ``cn`` must carry ``[ticker, name, cn_tier]``; returns the frame with a
    final ``sector`` column: ``证监会: <industry>`` where matched, board tier
    otherwise. Prints the honest fallback count (G6 disclosure).
    """
    if industry.empty:
        cn = cn.copy()
        cn["sector"] = cn["cn_tier"]
        print("  [warn] cn sector = board tier for ALL rows (industry source unavailable)")
        return cn
    cn = cn.merge(industry[["ticker", "industry"]], on="ticker", how="left")
    ind = cn["industry"].fillna("").astype(str).str.strip()
    cn["sector"] = [
        f"{CSRC_PREFIX}{i}" if i else tier
        for i, tier in zip(ind, cn["cn_tier"], strict=True)
    ]
    n_industry = int((ind != "").sum())
    print(f"  cn sector: {n_industry} rows CSRC industry, "
          f"{len(cn) - n_industry} rows fall back to board tier")
    return cn.drop(columns=["industry"])


def build(force_refresh: bool = False) -> pd.DataFrame:
    """Build the ticker_metadata cache. Returns the merged DataFrame."""
    if CACHE.exists() and not force_refresh:
        return pd.read_parquet(CACHE)
    print("[ticker_metadata] fetching A-share names (GitHub listing)…")
    cn = fetch_a_share_metadata()
    time.sleep(2.0)  # G7 politeness between hosts
    print(f"  cn rows: {len(cn)}")
    print("[ticker_metadata] fetching CN industry (baostock, 证监会分类)…")
    industry = fetch_cn_industry(force_refresh=force_refresh)
    cn = _merge_cn_sector(cn, industry)
    time.sleep(2.0)  # G7 politeness between hosts
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
    cn_rows = df[df["region"] == "cn"]
    cn_sources = {
        "csrc_industry": int(cn_rows["sector"].str.startswith(CSRC_PREFIX).sum()),
        "board_tier_fallback": int((~cn_rows["sector"].str.startswith(CSRC_PREFIX)).sum()),
    }
    print(json.dumps({
        "rows": len(df),
        "by_region": by_region,
        "cn_sector_sources": cn_sources,
    }, indent=2))


if __name__ == "__main__":
    main()
