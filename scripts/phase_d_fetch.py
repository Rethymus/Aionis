"""Phase D batch data fetch: SIC + external (non-self) 13D events for the frozen
OOS-resolvable universe — the two relationship-bundle inputs for the Phase D
confirmatory run.

Mirrors ``scripts/phase_b_fetch.py``: incremental + resumable. Each ticker's result
(SIC + the external 13D event list) is cached to ``data/cache/phase_d/<T>.json`` as
soon as it is fetched, so a kill/restart loses at most the in-flight ticker and
progress is visible. Both output parquets are reassembled from the per-ticker caches
at the end of every run (cheap), so they always reflect everything cached so far.

SEC spacing (0.15s) + exp-backoff live inside the ingest modules — no extra sleeps.

Run:  uv run python scripts/phase_d_fetch.py            # full 587-ticker batch
      uv run python scripts/phase_d_fetch.py --limit 3   # smoke test
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from aionis.config import settings
from aionis.ingest.stakes_13d import sic_for_cik
from aionis.ingest.stakes_13d_efts import external_13d_events
from aionis.ingest.universe import build_oos_resolvable_universe

# Start a year before the 2016 OOS window for feature warmup; end at the OOS close.
# 13D events are PIT via filing_date (immutable; consumer aligns backward-as-of).
START, END = "2015-01-01", "2026-06-30"
CACHE = settings.data_dir / "cache"
PDIR = CACHE / "phase_d"


def _load_cached(fp: Path) -> dict | None:
    """Load a per-ticker JSON cache, or None if missing/corrupt (-> re-fetch)."""
    if not fp.exists():
        return None
    try:
        return json.loads(fp.read_text())
    except (OSError, ValueError):
        return None


def _events_to_records(ev: pd.DataFrame) -> list[dict]:
    """External-13D DataFrame -> JSON-safe ``[{filer_cik, filing_date, ...}]``.

    ``filing_date`` -> ``YYYY-MM-DD`` string (re-parsed to datetime on assembly);
    ``filer_cik`` cast to int so ``json.dumps`` succeeds (numpy ints are not
    JSON-serializable)."""
    out: list[dict] = []
    for r in ev.itertuples(index=False):
        out.append({
            "filer_cik": int(r.filer_cik),
            "filing_date": r.filing_date.strftime("%Y-%m-%d"),
            "accession": str(r.accession),
            "form": str(r.form),
        })
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase D SIC + 13D batch fetch")
    parser.add_argument("--limit", type=int, default=None,
                        help="cap the universe size (smoke test); default = all")
    args = parser.parse_args()

    u = build_oos_resolvable_universe()
    cik_map: dict[str, int] = u["ciks"]  # {ticker: cik}
    tickers = list(u["tickers"])
    if args.limit is not None:
        tickers = tickers[: args.limit]
    print(f"[phase_d] universe: {len(tickers)} tickers "
          f"({u['n_clean']} resolvable in full)", flush=True)

    PDIR.mkdir(parents=True, exist_ok=True)
    sic_rows: list[dict] = []
    ev_rows: list[dict] = []
    failed: list[tuple[str, str]] = []

    for n, t in enumerate(tickers, 1):
        cik = int(cik_map[t])
        fp = PDIR / f"{t}.json"
        cached = _load_cached(fp)
        if cached is None:
            try:
                sic, desc = sic_for_cik(cik, CACHE)
                ev = external_13d_events(cik, start=START, end=END, cache_dir=CACHE)
            except RuntimeError as e:  # 4xx (bad CIK) or exhausted retries -> skip
                print(f"[phase_d]   SKIP {t} (cik={cik}): {e}", flush=True)
                failed.append((t, str(e)))
                continue
            cached = {
                "ticker": t,
                "cik": cik,
                "sic": sic,
                "sic_description": desc,
                "events": _events_to_records(ev),
            }
            fp.write_text(json.dumps(cached))

        sic_rows.append({
            "ticker": t,
            "cik": cached["cik"],
            "sic": cached["sic"],
            "sic_description": cached["sic_description"],
        })
        for e in cached["events"]:
            ev_rows.append({
                "ticker": t,
                "cik": cached["cik"],
                "filer_cik": e["filer_cik"],
                "filing_date": e["filing_date"],
                "accession": e["accession"],
                "form": e["form"],
            })
        print(f"[phase_d]   {n}/{len(tickers)} {t} (cik={cik}) "
              f"sic={cached['sic']!r} +{len(cached['events'])} events", flush=True)

    sic_df = pd.DataFrame(sic_rows, columns=["ticker", "cik", "sic", "sic_description"])
    sic_path = CACHE / "phase_d_sic_map.parquet"
    sic_df.to_parquet(sic_path)

    ev_df = pd.DataFrame(
        ev_rows, columns=["ticker", "cik", "filer_cik", "filing_date", "accession", "form"],
    )
    if not ev_df.empty:
        ev_df["filing_date"] = pd.to_datetime(ev_df["filing_date"]).dt.normalize()
    ev_path = CACHE / "phase_d_13d_events.parquet"
    ev_df.to_parquet(ev_path)

    n_issuers = int(ev_df["ticker"].nunique()) if not ev_df.empty else 0
    print(f"[phase_d] SIC map: {len(sic_df)} rows -> {sic_path}", flush=True)
    print(f"[phase_d] 13D events: {len(ev_df)} rows across {n_issuers} issuers "
          f"-> {ev_path}", flush=True)
    if failed:
        print(f"[phase_d] FAILED/SKIPPED ({len(failed)}): "
              f"{[t for t, _ in failed]}", flush=True)
    print("[phase_d] FETCH DONE", flush=True)


if __name__ == "__main__":
    main()
