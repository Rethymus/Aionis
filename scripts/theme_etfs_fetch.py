"""Bounded daily fetch of 10 theme-ETF holdings CSVs (issuer-official, free).

Thin runner over ``aionis.ingest.theme_etfs`` (parse + polite fetch live
there so the exporter reuses the same parsers — the cache and the tracked
JSON can never disagree on row semantics). 16 polite GETs per run (4 iShares
files + 6 Global X fund pages + 6 Global X dated files, >=2.1s spacing);
output is idempotent per fund+date:
``data/cache/theme_etfs/<TICK>_<YYYYMMDD>.csv`` (gitignored). Neither
issuer keeps a CSV history — each run appends one dated snapshot; the cache
IS the time series. Display lane ONLY.

Usage::

    uv run python scripts/theme_etfs_fetch.py
"""
from __future__ import annotations

from pathlib import Path

from aionis.ingest.theme_etfs import FUND_DEFS, fetch_all

OUT_DIR = Path("data/cache/theme_etfs")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fetched = fetch_all()
    summary: list[str] = []
    total_skipped = 0
    for tick, res in fetched.items():
        if "error" in res:
            summary.append(f"{tick}: FAIL {res['error']}")
            continue
        fp = OUT_DIR / f"{tick}_{res['as_of'].replace('-', '')}.csv"
        fp.write_text(res["text"], encoding="utf-8")
        total_skipped += res["skipped"]
        summary.append(
            f"{tick}: {len(res['rows'])} positions @ {res['as_of']} "
            f"({res['skipped']} skipped) -> {fp.name}"
        )
    print("[theme-etf-fetch] " + " | ".join(summary), flush=True)
    ok = [s for s in summary if "FAIL" not in s]
    print(
        f"[theme-etf-fetch] done: {len(ok)}/{len(FUND_DEFS)} funds refreshed "
        f"({total_skipped} rows skipped: iShares non-equity legs / Global X "
        "no-ticker cash-FX rows; honest per-fund failures listed above)",
        flush=True,
    )


if __name__ == "__main__":
    main()
