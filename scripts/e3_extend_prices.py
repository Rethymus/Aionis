"""E3 forward-lane price/SIC coverage extension (round-56).

The frozen ``phase_b_prices.parquet`` (585 tickers) is pinned by frozen configs
(H6: NEVER modified). But the E3 readiness gate demands the predict cross-section
exactly equal the PIT constituents at the predict session — and index additions
since the frozen fetch (CASY, RDDT, FERG, ...) plus legacy Tiingo-resolution
gaps leave a handful of CURRENT constituents outside the frozen panel.

This script closes the gap WITHOUT touching the frozen file: it fetches full
history for the missing constituents (Tiingo via the shared polite policy) and
their SIC codes (EDGAR submissions, cached), writing FORWARD-ONLY artifacts:

    data/cache/phase_b_prices_e3.parquet   # frozen px + new ticker columns
    data/cache/phase_d_sic_map_e3.parquet  # frozen sic map + new rows

``forward_commit_runner._load_inputs`` prefers the ``_e3`` files when present.
Idempotent: rerun with no coverage gap writes nothing.

Run: ``uv run python scripts/e3_extend_prices.py``.
"""
from __future__ import annotations

import pandas as pd
import structlog

from aionis.config import settings
from aionis.ingest.market import fetch_price_series
from aionis.ingest.stakes_13d import fetch_submissions
from aionis.ingest.universe import constituents_on, load_pierrebrunelle_membership

log = structlog.get_logger()

CACHE = settings.data_dir / "cache"
PX_E3 = CACHE / "phase_b_prices_e3.parquet"
SIC_E3 = CACHE / "phase_d_sic_map_e3.parquet"

# Title-verified CIK overrides for members whose INDEX ticker is not their
# CURRENT SEC ticker (each verified against EDGAR on 2026-09-02 — the SEC
# company_tickers.json snapshot only carries current tickers):
#   BK  -> 1390777  "Bank of New York Mellon Corp" (SEC ticker now BNY)
#   EQR -> 906107   "VIVMARK RESIDENTIAL", EDGAR: "formerly: EQUITY RESIDENTIAL
#                    (filings through 2026-08-12)" — renamed 2026, hence absent
#                    from the current SEC ticker snapshot
#   SATS-> 1415404  "EchoStar CORP" (SEC ticker now ECHO)
_CIK_OVERRIDES: dict[str, int] = {
    "BK": 1390777,
    "EQR": 906107,
    "SATS": 1415404,
}


def main() -> int:
    px = pd.read_parquet(CACHE / "phase_b_prices.parquet")
    mem = load_pierrebrunelle_membership()
    sic = pd.read_parquet(CACHE / "phase_d_sic_map.parquet")

    predict_session = pd.Timestamp(px.index.max()).normalize()
    pit = sorted(constituents_on(mem, predict_session))
    have = set(px.columns)
    missing = [t for t in pit if t not in have]
    print(
        f"[e3-extend] predict_session={predict_session.date()} "
        f"pit={len(pit)} panel={len(have)} missing={len(missing)} {missing}",
        flush=True,
    )
    if not missing:
        print("[e3-extend] no coverage gap — nothing to do", flush=True)
        return 0

    # 1. Prices: full history for the missing tickers through the panel's edge.
    series = fetch_price_series(
        missing, start=str(px.index.min().date()), end=str(predict_session.date())
    )
    add = pd.DataFrame({t: series[t] for t in missing})
    add.index = pd.to_datetime(add.index).normalize()
    grid = pd.DatetimeIndex(px.index)
    add = add.reindex(grid)
    px_e3 = pd.concat([px, add], axis=1)
    px_e3.index.name = px.index.name or "date"
    px_e3.to_parquet(PX_E3)

    # 2. SIC codes from the (cached) EDGAR submissions of each ticker.
    from aionis.ingest.fundamentals import cik_map

    ciks = cik_map(CACHE)
    sic_rows = []
    for t in missing:
        cik = _CIK_OVERRIDES.get(t) or ciks.get(t)
        if cik is None:
            log.warning("e3_extend_no_cik", ticker=t)
            continue
        sub = fetch_submissions(int(cik), CACHE)
        code = str(sub.get("sic", "") or "").strip()
        if code:
            # match the frozen map's string dtype (pyarrow rejects mixed columns)
            sic_rows.append({"ticker": t, "sic": code})
        else:
            log.warning("e3_extend_no_sic", ticker=t)
    sic_e3 = pd.concat(
        [sic, pd.DataFrame(sic_rows, columns=["ticker", "sic"])], ignore_index=True
    )
    sic_e3.to_parquet(SIC_E3)

    gap_after = sorted(
        set(constituents_on(mem, predict_session)) - set(px_e3.columns)
    )
    print(
        f"[e3-extend] wrote {PX_E3.name} ({px_e3.shape}) + {SIC_E3.name} "
        f"({len(sic_rows)} new SIC rows); residual gap: {gap_after}",
        flush=True,
    )
    return 0 if not gap_after else 1


if __name__ == "__main__":
    raise SystemExit(main())
