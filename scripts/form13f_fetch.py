"""Bounded 13F-HR star-manager holdings fetch (display-only, exploratory).

~12 celebrity institutional managers × the 2 most recent DISTINCT report
quarters (the second quarter exists purely for the quarter-over-quarter frame
diff shown in the /institutions panel). NOT the ~9,000-filer full 13F
universe — scope is deliberately tiny and polite.

All CIKs below were verified live against EDGAR submissions JSON on
2026-08-20 (entity name + a 13F-HR filing ≤45 days old). Politeness: ≥2s host
spacing via ``_policy_get``; every response cached idempotently under
``data/cache/`` so reruns make zero HTTP calls.

Writes ``data/cache/form13f_aggregate.parquet`` (gitignored, regenerable) —
one row per (manager, quarter, issuer line):
``[cik, manager_name, zh_name, quarter, filing_date, accession, form, issuer,
title_class, cusip, value_usd, shares, option_type]``.

Usage (from the repo root)::

    uv run python scripts/form13f_fetch.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from aionis.ingest.form13f import fetch_manager_holdings

# Star-manager registry — CIKs verified against data.sec.gov/submissions on
# 2026-08-20 (see module docstring). CIK -> (EDGAR entity name, zh display name).
# zh_name is display-layer only (the panel's optional Chinese label).
MANAGERS: dict[int, tuple[str, str]] = {
    1067983: ("BERKSHIRE HATHAWAY INC", "伯克希尔·哈撒韦（巴菲特）"),
    1350694: ("Bridgewater Associates, LP", "桥水基金（达利欧）"),
    1697748: ("ARK Investment Management LLC", "ARK 投资（伍德）"),
    1759760: ("H&H International Investment, LLC", "H&H 国际投资（段永平）"),
    1709323: ("Himalaya Capital Management LLC", "喜马拉雅资本（李录）"),
    1336528: ("Pershing Square Capital Management, L.P.", "潘兴广场（阿克曼）"),
    1167483: ("TIGER GLOBAL MANAGEMENT LLC", "老虎环球"),
    1656456: ("Appaloosa LP", "Appaloosa（泰珀）"),
    1135730: ("COATUE MANAGEMENT LLC", "蔻图资本"),
    1103804: ("VIKING GLOBAL INVESTORS LP", "Viking 全球投资"),
    1647251: ("TCI Fund Management Ltd", "TCI 基金（霍恩）"),
    1037389: ("RENAISSANCE TECHNOLOGIES LLC", "文艺复兴科技（西蒙斯）"),
}

QUARTERS = 2  # latest report quarter + previous (frame diff needs both)
OUT = Path("data/cache/form13f_aggregate.parquet")


def main() -> None:
    frames: list[pd.DataFrame] = []
    for i, (cik, (name, zh)) in enumerate(MANAGERS.items(), 1):
        print(f"[form13f-fetch] ({i}/{len(MANAGERS)}) {name} (CIK {cik:010d})", flush=True)
        df = fetch_manager_holdings(cik, name, quarters=QUARTERS)
        if df.empty:
            print("  -> 0 holdings (graceful skip; manager excluded)", flush=True)
            continue
        df["zh_name"] = zh
        quarters_found = sorted(df["quarter"].unique(), reverse=True)
        latest = df[df["quarter"] == quarters_found[0]]
        print(
            f"  -> {len(df)} rows across {len(quarters_found)} quarter(s) "
            f"({', '.join(quarters_found)}); latest: {len(latest)} positions, "
            f"${latest['value_usd'].sum() / 1e9:,.2f}B",
            flush=True,
        )
        frames.append(df)

    if not frames:
        print("[form13f-fetch] no holdings across managers; nothing written", flush=True)
        return

    agg = pd.concat(frames, ignore_index=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    agg.to_parquet(OUT, index=False)
    latest_quarter = agg["quarter"].max()
    n_latest = len(agg[agg["quarter"] == latest_quarter])
    print(
        f"[form13f-fetch] final: {len(agg)} rows, {agg['cik'].nunique()} managers, "
        f"latest quarter {latest_quarter} ({n_latest} positions) -> {OUT}",
        flush=True,
    )


if __name__ == "__main__":
    main()
