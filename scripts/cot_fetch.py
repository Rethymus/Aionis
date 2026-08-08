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

# Each market maps to one or more exact CFTC "Market and Exchange Names"
# (legacy futures-only). The CFTC renamed several equity + copper contracts
# around 2022, so both the pre-2022 and 2022+ variants are listed and their
# rows unioned (then de-duplicated by date) to recover full 2016→today history.
MARKETS: dict[str, tuple[str, ...]] = {
    "S&P 500": (
        "E-MINI S&P 500 STOCK INDEX - CHICAGO MERCANTILE EXCHANGE",  # pre-2022
        "E-MINI S&P 500 - CHICAGO MERCANTILE EXCHANGE",              # 2022+
    ),
    "Nasdaq 100": ("NASDAQ-100 Consolidated - CHICAGO MERCANTILE EXCHANGE",),
    "Russell 2000": (
        "RUSSELL 2000 MINI INDEX FUTURE - ICE FUTURES U.S.",         # 2016–mid-2017 (ICE)
        "E-MINI RUSSELL 2000 INDEX - CHICAGO MERCANTILE EXCHANGE",   # mid-2017–2021 (CME)
        "RUSSELL E-MINI - CHICAGO MERCANTILE EXCHANGE",              # 2022+ (CME renamed)
    ),
    "VIX": ("VIX FUTURES - CBOE FUTURES EXCHANGE",),
    "WTI Crude": ("CRUDE OIL, LIGHT SWEET-WTI - ICE FUTURES EUROPE",),
    "Gold": ("GOLD - COMMODITY EXCHANGE INC.",),
    "Silver": ("SILVER - COMMODITY EXCHANGE INC.",),
    "Copper": (
        "COPPER-GRADE #1 - COMMODITY EXCHANGE INC.",  # pre-2022
        "COPPER- #1 - COMMODITY EXCHANGE INC.",       # 2022+
    ),
    "Euro FX": ("EURO FX - CHICAGO MERCANTILE EXCHANGE",),
    "Japanese Yen": ("JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE",),
}
# Full Trump-era history (2016→today) so the positioning chart shows the
# multi-year arc, not just the recent ~1.5y. cot_year fetches one CFTC zip per
# year (legacy_fut archives back to 1986); resilient skip-on-fail (cftc.gov is
# intermittently unstable from some edge networks) keeps a partial year set usable.
YEARS: tuple[int, ...] = tuple(range(2016, 2027))
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
    for label, exact_names in MARKETS.items():
        sub = (
            df[df[NAME_C].astype(str).str.strip().str.upper().isin(
                [n.upper() for n in exact_names]
            )].sort_values(DATE_C)
        )
        if sub.empty:
            print(f"[cot] MISS: {label} — no variant name found, skipping", flush=True)
            continue
        sub = sub[[DATE_C, LONG_C, SHORT_C]].dropna().copy()
        # The pre/post-2022 rename overlaps a few transition weeks: keep one
        # row per date (the values are near-identical across variants).
        sub = sub.drop_duplicates(subset=[DATE_C], keep="last")
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
    # Monotonic merge: cftc.gov is intermittently unstable (per-year timeouts),
    # so a fresh run may fetch fewer years than a prior one. Union this run with
    # any existing parquet, de-duplicating by (date, market) and KEEPING the
    # existing row on overlap — so a run can only ADD dates, never lose them.
    if OUT.exists():
        prev = pd.read_parquet(OUT)
        prev["date"] = pd.to_datetime(prev["date"])
        keep = ["date", "market", "net", "zscore", "long", "short"]
        cols = [c for c in keep if c in prev.columns]
        out = (
            pd.concat([prev[cols], out[cols]], ignore_index=True)
            .drop_duplicates(subset=["date", "market"], keep="first")
            .sort_values(["market", "date"])
            .reset_index(drop=True)
        )
    out.to_parquet(OUT, index=False)
    print(
        f"[cot] wrote {len(out)} rows across {out['market'].nunique()} markets to {OUT}",
        flush=True,
    )


if __name__ == "__main__":
    main()
