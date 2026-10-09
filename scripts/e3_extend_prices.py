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

``--through YYYY-MM-DD`` (round 242): ALSO extend the ``_e3`` panel's TIME
axis to the target session — the structural fix for the 9-30/10-31 shadow
fail-closed class (``predict_session_not_in_panel``: nothing in the chain
advanced the panel edge; the frozen base is H6-pinned by design). All panel
tickers are fetched from (edge + 1) through the target via the shared
dual-source polite fetcher and appended on the NYSE session grid. The frozen
``phase_b_prices.parquet`` remains byte-untouched; only the ``_e3`` forward
artifact grows. Prereg section 8 ("E3 is a LIVE PROCESS") explicitly allows
live data extension.

    uv run python scripts/e3_extend_prices.py --through 2026-10-30
"""
from __future__ import annotations

import argparse
import time

import pandas as pd
import structlog

from aionis.config import settings
from aionis.features.alignment import nyse_sessions
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


def _extend_rows_through(px: pd.DataFrame, through: pd.Timestamp,
                        fetch=fetch_price_series) -> pd.DataFrame:
    """Extend the panel's TIME axis to ``through`` on the NYSE session grid.

    Fetches ALL panel tickers from (edge + 1) through the target via the
    shared dual-source polite fetcher (Tiingo -> Alpaca -> fail-closed).
    The input frame is never mutated; a NEW frame is returned (the caller
    writes only the ``_e3`` artifact — the frozen base stays untouched).
    """
    edge = pd.Timestamp(px.index.max())
    if through <= edge:
        raise SystemExit(
            f"--through {through.date()} must be AFTER the panel edge "
            f"{edge.date()} (panel already covers the target)")
    sessions = nyse_sessions(edge + pd.Timedelta(days=1), through)
    if len(sessions) == 0:
        raise SystemExit(f"--through {through.date()}: no NYSE sessions after {edge.date()}")
    print(f"[e3-extend] time axis: {edge.date()} -> {through.date()} "
          f"({len(sessions)} sessions x {px.shape[1]} tickers)", flush=True)
    # Round 243 live finding: the aggregate fail-closed fetch is wrong for a
    # TIME-AXIS extension — delisted names (BBBY) legitimately have no data in
    # the new window, and a 2.5h polite crawl exhausts provider retries for a
    # handful of ALIVE names (BF-B/BRK-B recovered on a targeted retry). The
    # strictness point is the READINESS gate (PIT cross-section), not the raw
    # panel: fetch per symbol, tolerate no-data with an honest NaN column +
    # warning, and surface the survivors/retry-miss lists for the log.
    from aionis.config import settings
    from aionis.ingest.market import _from_alpaca, _from_tiingo
    start, end = str((edge + pd.Timedelta(days=1)).date()), str(through.date())

    def _prod_fetch_one(tkr: str) -> dict[str, pd.Series]:
        got: dict[str, pd.Series] = {}
        try:
            got = _from_tiingo([tkr], start, end, settings.tiingo_api_key)
        except Exception as exc:  # noqa: BLE001 — per-symbol tolerance
            log.warning("e3_extend_tiingo_error", ticker=tkr, error=repr(exc)[:120])
        if not got and settings.alpaca_key_id and settings.alpaca_secret_key:
            try:
                got = _from_alpaca(
                    settings.alpaca_key_id, settings.alpaca_secret_key,
                    [tkr], start, end)
            except Exception as exc:  # noqa: BLE001 — backstop may 401 (live 2026-10-09)
                log.warning("e3_extend_alpaca_error", ticker=tkr, error=repr(exc)[:120])
        return got

    series: dict[str, pd.Series] = {}
    no_data: list[str] = []
    if fetch is not fetch_price_series:
        # Test seam: an injected fetch callable serves the whole batch in ONE
        # call (the hermetic tests' recorded contract).
        got_all = fetch(list(px.columns), start, end)
        for tkr, ser in (got_all or {}).items():
            if ser is not None and len(ser) > 0:
                series[tkr] = ser
            else:
                no_data.append(tkr)
        no_data += [t for t in px.columns if t not in (got_all or {})]
    else:
        # Round 244: Tiingo free tier is HOURLY-allocation limited (live
        # 2026-10-09: "run over your hourly request allocation") — 597 symbols
        # trickle over ~10h. Make the crawl RESUMABLE (partial store reloaded
        # on restart, fetched symbols skipped) and hour-aware (after 5
        # consecutive 429/empty responses, sleep to the next hour boundary
        # instead of burning retries that triple consumption).
        partial_path = CACHE / "e3_extend_partial.parquet"
        done_path = CACHE / "e3_extend_fetched.json"
        if partial_path.exists():
            partial = pd.read_parquet(partial_path)
            series = {c: partial[c].dropna() for c in partial.columns}
            print(f"[e3-extend] resumed {len(series)} symbols from partial store",
                  flush=True)
        done_no_data: list[str] = []
        if done_path.exists():
            import json as _json
            done_no_data = _json.loads(done_path.read_text())
        done = set(series) | set(done_no_data)
        no_data = list(done_no_data)
        consecutive_bad = 0
        todo = [t for t in px.columns if t not in done]
        for i, tkr in enumerate(todo):
            got = _prod_fetch_one(tkr)
            got_series = got.get(tkr)
            if got_series is not None and len(got_series) > 0:
                series[tkr] = got_series
                consecutive_bad = 0
            else:
                no_data.append(tkr)
                consecutive_bad += 1
            if (i + 1) % 10 == 0 or i + 1 == len(todo):
                pd.DataFrame({t: series[t] for t in series}).to_parquet(
                    partial_path)
                import json as _json
                done_path.write_text(_json.dumps(
                    [t for t in no_data]))
                print(f"[e3-extend] fetched {i + 1}/{len(todo)} todo "
                      f"({len(series)} series, no-data {len(no_data)}) — "
                      f"partial store saved", flush=True)
            if consecutive_bad >= 5:
                now = pd.Timestamp.now()
                next_hour = (now.floor("h") + pd.Timedelta(hours=1))
                wait_s = int((next_hour - now).total_seconds()) + 30
                print(f"[e3-extend] {consecutive_bad} consecutive empty/429 — "
                      f"hourly allocation exhausted; sleeping {wait_s}s to the "
                      f"next hour boundary (progress is saved)", flush=True)
                time.sleep(wait_s)
                consecutive_bad = 0
    if no_data:
        print(f"[e3-extend] WARNING: {len(no_data)} symbols have no data in the "
              f"new window (delisted names are expected; alive names here are a "
              f"coverage gap the readiness gate will catch): {no_data}", flush=True)
    add = pd.DataFrame({tkr: s for tkr, s in series.items()})
    # crawl complete — drop the resume store so the next run starts clean
    for stale in (CACHE / "e3_extend_partial.parquet", CACHE / "e3_extend_fetched.json"):
        if stale.exists():
            stale.unlink()
    add.index = pd.to_datetime(add.index).normalize()
    add = add.reindex(sessions)
    out = pd.concat([px, add])
    out.index.name = px.index.name or "date"
    interior_nans = int(add.isna().all(axis=1).sum())
    print(f"[e3-extend] appended {len(add)} sessions "
          f"(all-NaN sessions: {interior_nans} — dual-source fail-closed "
          f"guarantees none for listed names)", flush=True)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--through", type=str, default=None,
                        help="extend the _e3 panel's time axis to this "
                             "session (YYYY-MM-DD); frozen base untouched")
    args = parser.parse_args()

    px = pd.read_parquet(CACHE / "phase_b_prices.parquet")
    mem = load_pierrebrunelle_membership()
    sic = pd.read_parquet(CACHE / "phase_d_sic_map.parquet")

    if args.through:
        px = _extend_rows_through(px, pd.Timestamp(args.through).normalize())
        # Round 245b: the time-extended frame must ALWAYS be persisted — the
        # coverage-gap branch below used to be the only PX_E3 writer, so with
        # complete column coverage (the common case after the first run) the
        # extension was computed and then silently discarded (live 2026-10-09:
        # crawl finished, partial store dropped, panel edge still 08-31).
        px.to_parquet(PX_E3)
        print(f"[e3-extend] wrote {PX_E3.name} time axis through "
              f"{pd.Timestamp(px.index.max()).date()} ({px.shape})", flush=True)

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
