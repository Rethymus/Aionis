"""CFTC Commitments of Traders (COT) fetch — display-only alt-data.

Free, no-API, US-government public domain. Weekly (Fri), historically archived
and NOT revised (each week is an immutable snapshot — cleanest possible PIT
surface, strictly better than ALFRED). Reuses the MIT-licensed ``cot_reports``
library for download + parsing (no hand-rolled COT column mapping).

Computes, per key futures market, the net non-commercial (speculator) positioning
= Long - Short contracts, plus a trailing 52-week crowding z-score. Writes
``data/cache/cot_aggregate.parquet`` (gitignored, regenerable); ``export_cot`` in
``export_terminal_data.py`` reads it into the tracked web payload.

Usage::

    uv run python scripts/cot_fetch.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from cot_reports import cot_year

# Curated exact COT "Market and Exchange Names" (legacy futures-only). Each must
# match the CFTC's exact string (case-insensitive, whitespace-trimmed). Misses are
# reported and skipped (resilient) — fix the string if a market reports MISS.
MARKETS: dict[str, str] = {
    "S&P 500": "E-MINI S&P 500 - CHICAGO MERCANTILE EXCHANGE",
    "Nasdaq 100": "NASDAQ-100 Consolidated - CHICAGO MERCANTILE EXCHANGE",
    "Russell 2000": "RUSSELL E-MINI - CHICAGO MERCANTILE EXCHANGE",
    "VIX": "VIX FUTURES - CBOE FUTURES EXCHANGE",
    "WTI Crude": "CRUDE OIL, LIGHT SWEET-WTI - ICE FUTURES EUROPE",
    "Gold": "GOLD - COMMODITY EXCHANGE INC.",
    "Silver": "SILVER - COMMODITY EXCHANGE INC.",
    "Copper": "COPPER- #1 - COMMODITY EXCHANGE INC.",
    "Euro FX": "EURO FX - CHICAGO MERCANTILE EXCHANGE",
    "Japanese Yen": "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE",
}
YEARS: tuple[int, ...] = (2024, 2025, 2026)
LONG_C = "Noncommercial Positions-Long (All)"
SHORT_C = "Noncommercial Positions-Short (All)"
DATE_C = "As of Date in Form YYYY-MM-DD"
NAME_C = "Market and Exchange Names"
TRAIL = 52  # weeks for the crowding z-score window
OUT = Path("data/cache/cot_aggregate.parquet")


def main() -> None:
    # Fetch per-year, resiliently: cftc.gov historical zips occasionally time out
    # (transient). Skip a failed year and use what's available rather than aborting.
    frames: list[pd.DataFrame] = []
    for y in YEARS:
        try:
            frames.append(cot_year(y, cot_report_type="legacy_fut"))
        except Exception as exc:  # noqa: BLE001 — a flaky source year must not abort the batch
            print(f"[cot] year {y} fetch failed ({type(exc).__name__}), skipping", flush=True)
    if not frames:
        print("[cot] no years fetched; nothing written", flush=True)
        return
    df = pd.concat(frames, ignore_index=True)
    df[DATE_C] = pd.to_datetime(df[DATE_C])

    out_frames: list[pd.DataFrame] = []
    for label, exact in MARKETS.items():
        sub = (
            df[df[NAME_C].astype(str).str.strip().str.upper() == exact.upper()]
            .sort_values(DATE_C)
        )
        if sub.empty:
            print(f"[cot] MISS: {label} — exact name not found, skipping", flush=True)
            continue
        sub = sub[[DATE_C, LONG_C, SHORT_C]].dropna().copy()
        sub["net"] = sub[LONG_C].astype(int) - sub[SHORT_C].astype(int)
        roll_mean = sub["net"].rolling(TRAIL, min_periods=20).mean()
        roll_std = sub["net"].rolling(TRAIL, min_periods=20).std()
        sub["zscore"] = (sub["net"] - roll_mean) / roll_std.replace(0, pd.NA)
        sub["market"] = label
        out_frames.append(
            sub[[DATE_C, "market", "net", "zscore", LONG_C, SHORT_C]].rename(
                columns={DATE_C: "date", LONG_C: "long", SHORT_C: "short"}
            )
        )
        latest_z = sub["zscore"].iloc[-1]
        print(
            f"[cot] {label}: {len(sub)} wks | latest net={int(sub['net'].iloc[-1]):+d} "
            f"z={latest_z:+.2f}",
            flush=True,
        )

    # cot_year writes ./annual.txt to cwd — clean up (avoid repo litter).
    Path("annual.txt").unlink(missing_ok=True)

    if not out_frames:
        print("[cot] no markets matched; nothing written", flush=True)
        return
    out = pd.concat(out_frames, ignore_index=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(OUT, index=False)
    print(
        f"[cot] wrote {len(out)} rows across {out['market'].nunique()} markets to {OUT}",
        flush=True,
    )


if __name__ == "__main__":
    main()
