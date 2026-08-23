"""Bounded daily fetch of ARK Invest's 8 ETF holdings CSVs (official, free).

Thin runner over ``aionis.ingest.ark_holdings`` (parse + polite fetch live
there so the exporter reuses the same parser — the cache and the tracked
JSON can never disagree on row semantics). 8 polite GETs per run (≥2s
spacing); output is idempotent per fund+date:
``data/cache/ark_holdings/<TICK>_<YYYYMMDD>.csv`` (gitignored). ARK keeps
no CSV history — each run appends one dated snapshot; the cache IS the
time series. Display lane ONLY.

Usage::

    uv run python scripts/ark_holdings_fetch.py
"""
from __future__ import annotations

from pathlib import Path

from aionis.ingest.ark_holdings import FUND_CSV_URLS, fetch_all

OUT_DIR = Path("data/cache/ark_holdings")


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
    print("[ark-fetch] " + " | ".join(summary), flush=True)
    ok = [s for s in summary if "FAIL" not in s]
    print(
        f"[ark-fetch] done: {len(ok)}/{len(FUND_CSV_URLS)} funds refreshed "
        f"({total_skipped} rows skipped: disclaimer footer / no-ticker / CASHX; "
        "honest per-fund failures listed above)",
        flush=True,
    )


if __name__ == "__main__":
    main()
