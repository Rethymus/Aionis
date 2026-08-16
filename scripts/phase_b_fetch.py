"""Phase B full data fetch (slice 5b): fundamentals + prices for the clean
OOS-resolvable universe. One-time, cached to parquet. The final price panel is
written only when every requested symbol is present.

Run:  uv run python scripts/phase_b_fetch.py   (~15-20 min; background-safe)
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from aionis.config import settings
from aionis.ingest.fundamentals import build_fundamentals
from aionis.ingest.market import _from_alpaca, _from_tiingo, _missing_prices_error
from aionis.ingest.universe import build_oos_resolvable_universe

START, END = "2011-01-01", "2026-06-30"  # train 2011-2016 + OOS 2017-2026 (FROZEN research panel)
CACHE = settings.data_dir / "cache"


def _require_complete_prices(tickers: list[str], series: dict[str, pd.Series]) -> None:
    missing = [ticker for ticker in tickers if ticker not in series or series[ticker].empty]
    if missing:
        providers = []
        if settings.tiingo_api_key:
            providers.append("Tiingo")
        if settings.alpaca_key_id and settings.alpaca_secret_key:
            providers.append("Alpaca")
        raise _missing_prices_error(missing, providers)


# Display path only: tolerate a small share of missing tickers. The display
# panel feeds terminal themes (aggregate freshness), NOT the research pipeline,
# so a few unresolved share-class variants must not block the refresh. Hard
# cap at 2% guards against a silent provider-wide outage masquerading as
# "a couple of edge-case tickers" — if >2% are missing, something is wrong and
# we still refuse (better a stale display than a misleading one).
_DISPLAY_MISSING_FRACTION_CAP = 0.02


def _require_display_prices(tickers: list[str], series: dict[str, pd.Series]) -> None:
    if not tickers:
        return
    missing = [t for t in tickers if t not in series or series[t].empty]
    frac = len(missing) / len(tickers)
    if frac > _DISPLAY_MISSING_FRACTION_CAP:
        providers = []
        if settings.tiingo_api_key:
            providers.append("Tiingo")
        if settings.alpaca_key_id and settings.alpaca_secret_key:
            providers.append("Alpaca")
        raise RuntimeError(
            f"display panel missing {len(missing)}/{len(tickers)} ({frac:.1%}) > "
            f"{_DISPLAY_MISSING_FRACTION_CAP:.0%} cap — likely a provider outage, "
            f"not edge-case coverage. Providers: {providers or 'none configured'}. "
            f"Sample missing: {missing[:12]}"
        )


def _final_panel_is_complete(path: Path, tickers: list[str]) -> bool:
    try:
        panel = pd.read_parquet(path)
    except (OSError, ValueError):
        return False
    return all(ticker in panel and panel[ticker].notna().any() for ticker in tickers)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--display",
        action="store_true",
        help=(
            "Display-only mode: fetch prices through TODAY and write "
            "phase_b_prices_display.parquet. Does NOT touch the frozen research "
            "panel (phase_b_prices.parquet, END=2026-06-30). The display panel "
            "feeds terminal themes with fresh as_of dates; it never enters "
            "aionis.eval / the research pipeline."
        ),
    )
    parser.add_argument(
        "--budget-minutes",
        type=float,
        default=None,
        help=(
            "Soft wall-clock budget for the price fetch loop. When the budget "
            "is nearly exhausted, stop fetching further batches and exit "
            "GRACEFULLY (status 0): per-ticker parquets already written stay in "
            "data/cache/prices/ so the next run resumes from them, and the "
            "normal exit means no orphan python processes are still writing "
            "when the CI cache post-step tars data/cache (a hard step timeout "
            "kill leaves orphans → 'tar: file changed as we read it' → cache "
            "save fails → every run restarts from 0 cached)."
        ),
    )
    parser.add_argument(
        "--fundamentals-only",
        action="store_true",
        help=(
            "Fetch ONLY the fundamentals parquet (SEC company_facts, ~20min cold) "
            "and exit 0 — no price fetching, no panel write. Lets CI warm the "
            "fundamentals cache in its own step so the price step's budget "
            "covers prices alone (one 30min step previously burned 20min on "
            "fundamentals cold-pull before prices even started)."
        ),
    )
    args = parser.parse_args()

    # `--display` wants prices through TODAY. Resolve it HERE to an ISO date —
    # the literal string "today" previously leaked into the Tiingo/Alpaca
    # endDate param, which both reject with HTTP 400 ("End date format was not
    # correct. Must be in YYYY-MM-DD format"). That single bug made every
    # display price fetch fail in CI (587 tickers, +0/N batches) — the real
    # root cause of the terminal's frozen display data, not IP blocking.
    from datetime import date as _date

    end = _date.today().isoformat() if args.display else END
    px_path = CACHE / ("phase_b_prices_display.parquet" if args.display
                       else "phase_b_prices.parquet")
    label = "DISPLAY" if args.display else "5b"

    u = build_oos_resolvable_universe()
    tickers, ciks = u["tickers"], u["ciks"]
    print(f"[{label}] clean OOS universe: {len(tickers)} tickers", flush=True)

    fund_path = CACHE / "phase_b_fundamentals.parquet"
    if fund_path.exists():
        print(f"[{label}] fundamentals cached: {fund_path}", flush=True)
    else:
        print(f"[{label}] fetching fundamentals (SEC company_facts, ~588 CIKs)...", flush=True)
        fund = build_fundamentals(tickers, cik_override=ciks)
        fund.to_parquet(fund_path)
        print(f"[{label}] fundamentals: {len(fund)} rows, "
              f"{fund['ticker'].nunique()} tickers -> {fund_path}", flush=True)

    if args.fundamentals_only:
        print(f"[{label}] FUNDAMENTALS-ONLY DONE", flush=True)
        return

    # Frozen path: END is a fixed date, so a ticker-complete file IS final —
    # reuse it (determinism; H6 bit-identical reruns). Display path: the target
    # end is TODAY, which moves — a ticker-complete file can still be
    # date-stale, and reusing it froze the panel at the file's build date
    # forever (observed live: theme_signals as_of pinned to 2026-06-30 across
    # multiple green daily runs because a complete-but-stale wide file kept
    # short-circuiting the fetch). Display therefore always rebuilds the wide
    # file from the per-ticker caches; their freshness rule (series must reach
    # end-5d) keeps the network tail near zero on a daily cadence. The stale
    # file is NOT unlinked first — a budget-exit run that cannot write a fresh
    # panel leaves it in place as the (old) input for materialize, which is no
    # worse than this run's starting state.
    reuse_prices = (
        not args.display
        and px_path.exists()
        and _final_panel_is_complete(px_path, tickers)
    )
    if reuse_prices:
        print(f"[{label}] prices cached: {px_path}", flush=True)
    else:
        if px_path.exists() and not args.display:
            print(f"[{label}] cached price panel incomplete; rebuilding: {px_path}", flush=True)
            px_path.unlink()

        # Incremental + resumable: cache each symbol's series to cache/prices/<T>.parquet
        # as soon as it's fetched, so a kill/restart loses <= one batch (not 2h of work)
        # and progress is visible. Build the wide parquet at the end from the cache.
        # NOTE: per-ticker cache is shared between frozen + display modes — the series
        # are date-ranged by START..end at fetch time, so display just extends them.
        pdir = CACHE / "prices"
        pdir.mkdir(exist_ok=True)
        series: dict[str, pd.Series] = {}
        # Display mode targets TODAY; a cached series only reaches ITS pull
        # date. Reuse a cached series ONLY if it reaches near the target end —
        # otherwise queue it for a fresh fetch (providers return the full
        # START..end range, so this overwrite-extends the cache). Without this,
        # a warm cache froze the display panel at the FIRST pull date forever
        # (observed: 06-30-era cache kept the panel at 06-30 even after the
        # today-400 fix landed). The frozen path (end=END) reuses freely
        # because END never moves. The --budget-minutes cap bounds the re-fetch
        # wave, so this converges across runs like the cold pull does.
        end_ts = pd.Timestamp(end)
        stale_grace = pd.Timedelta(days=5)  # weekends/holidays slack
        for t in tickers:
            fp = pdir / f"{t}.parquet"
            if fp.exists():
                df = pd.read_parquet(fp)
                if not df.empty:
                    s = pd.Series(
                        df["adjClose"].to_numpy(float),
                        index=pd.to_datetime(df["date"]).dt.normalize(), name=t,
                    )
                    if not args.display or s.index.max() >= (end_ts - stale_grace):
                        series[t] = s
        todo = [t for t in tickers if t not in series]
        print(f"[{label}] prices {START}..{end}: {len(series)} cached, {len(todo)} to fetch",
              flush=True)
        use_tiingo = bool(settings.tiingo_api_key)
        BATCH = 20
        import time as _time
        _t0 = _time.monotonic()
        _budget_s = (args.budget_minutes * 60.0) if args.budget_minutes else None
        # Reserve a safety margin so we exit BEFORE the CI step timeout kills us
        # (a killed process keeps orphan writers → cache save fails).
        _margin_s = 120.0 if _budget_s else 0.0
        _budget_hit = False
        for i in range(0, len(todo), BATCH):
            if _budget_s is not None and (_time.monotonic() - _t0) > (_budget_s - _margin_s):
                _budget_hit = True
                print(f"[{label}] budget reached ({args.budget_minutes}min): stopping "
                      f"after {len(series)} tickers cached; next run resumes",
                      flush=True)
                break
            batch = todo[i:i + BATCH]
            got: dict[str, pd.Series] = {}
            if use_tiingo:
                got = _from_tiingo(batch, START, end, settings.tiingo_api_key)
            miss = [t for t in batch if t not in got]
            if miss and settings.alpaca_key_id and settings.alpaca_secret_key:
                got.update(_from_alpaca(miss, START, end,
                                        settings.alpaca_key_id, settings.alpaca_secret_key))
            for t, s in got.items():
                pd.DataFrame({"date": s.index, "adjClose": s.to_numpy()}).to_parquet(
                    pdir / f"{t}.parquet")
                series[t] = s
            done = min(i + BATCH, len(todo))
            print(f"[{label}]   {done}/{len(todo)} done "
                  f"(+{len(got)}/{len(batch)} this batch; total {len(series)})",
                  flush=True)
        if _budget_hit:
            # Graceful budget exit. Per-ticker parquets are already on disk, so
            # the CI cache (saved on this NORMAL exit) carries them forward and
            # the next run resumes. If what we have already clears the display
            # coverage cap, write the panel now; otherwise exit 0 WITHOUT the
            # panel (tracked JSON keeps its last value — honest, no partial
            # panel as a misleading near-empty surface).
            if args.display:
                try:
                    _require_display_prices(tickers, series)
                except RuntimeError:
                    print(f"[{label}] budget exit: coverage below display cap; "
                          f"panel NOT written this run (cache kept for resume)",
                          flush=True)
                    return
                px = pd.DataFrame(series)
                px.to_parquet(px_path)
                print(f"[{label}] budget exit with sufficient coverage: "
                      f"{px.shape} -> {px_path}", flush=True)
            return
        still_missing = [t for t in tickers if t not in series]
        if args.display:
            # Display path: tolerate a small share of missing tickers. The
            # display panel is an aggregate freshness surface (themes shows
            # cross-sectional means + sparklines through TODAY), NOT a
            # backtestable research surface — so 1-2 unresolved share-class
            # variants (e.g. BF-B/BRK-B, where Tiingo/Alpaca coverage differs)
            # must not block the whole freshness refresh. The frozen research
            # path below keeps the strict complete-prices gate (anti-leakage).
            _require_display_prices(tickers, series)
        else:
            _require_complete_prices(tickers, series)
        px = pd.DataFrame(series)
        px.to_parquet(px_path)
        missing_note = (
            f"; dropped {len(still_missing)} unresolved: {still_missing[:8]}"
            if args.display and still_missing
            else ""
        )
        print(f"[{label}] prices: {px.shape}  still-missing({len(still_missing)}): "
              f"{still_missing[:12]} -> {px_path}{missing_note}", flush=True)

    print(f"[{label}] FETCH DONE", flush=True)


if __name__ == "__main__":
    main()
