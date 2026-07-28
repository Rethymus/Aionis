"""Phase D first confirmatory run — thin wrapper around :mod:`aionis.eval.phase_d`.

Loads the Phase B frozen data (fundamentals / prices / membership) + the Phase D
relationship-bundle inputs (SIC map + external 13D events from
``scripts/phase_d_fetch.py``), assembles the rel bundle (peer_mom +
stakes_13d_event), commits the config (sha256 BEFORE any result — the durable
anti-leakage anchor), then runs the confirmatory pipeline and persists artifacts.

Run:  uv run python scripts/phase_d_run.py   (background-safe)

The script is intentionally minimal: every testable decision lives in
``aionis.eval.phase_d`` so the hermetic test exercises the real pipeline.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from aionis.config import settings
from aionis.eval.phase_d import (
    FEATURE_COLS,
    REL_COLS,
    build_config,
    commit_config,
    run_confirmatory,
)
from aionis.features.peer_momentum import peer_momentum_panel
from aionis.features.stakes_13d_signal import stakes_13d_event_panel
from aionis.ingest.universe import load_pierrebrunelle_membership

CACHE = settings.data_dir / "cache"
LEDGER = "runs/ledger.jsonl"
PEER_WINDOW = 21        # trailing sessions for peer momentum (~1 month)
STAKES_WINDOW_DAYS = 60  # post-13D event window (~3 months, the drift horizon)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def _build_rel_extra(px: pd.DataFrame) -> pd.DataFrame:
    """Assemble the per-(ticker, date) rel bundle [date, ticker, peer_mom,
    stakes_13d_event] from the cached SIC map + external 13D events."""
    from aionis.features.alignment import nyse_sessions

    # defense-in-depth: px.index MUST be the NYSE session grid (market.py reindexes
    # prices to it). If a non-fetch-sourced px ever diverges, rel_extra dates would
    # mismatch the panel's session grid and silently NaN the rel features.
    sessions = nyse_sessions(px.index.min(), px.index.max())
    assert pd.DatetimeIndex(px.index).normalize().equals(pd.DatetimeIndex(sessions)), (
        "px.index is not the NYSE session grid — rel_extra would misalign with the panel"
    )

    sic = pd.read_parquet(CACHE / "phase_d_sic_map.parquet")
    events = pd.read_parquet(CACHE / "phase_d_13d_events.parquet")
    sic_map = dict(zip(sic["ticker"], sic["sic"], strict=True))
    tickers = [t for t in px.columns if t in sic_map]

    sessions = pd.DatetimeIndex(px.index).normalize()
    peer = peer_momentum_panel(px, sic_map, window=PEER_WINDOW, tickers=tickers)
    events_long = events[["ticker", "filing_date"]].copy()
    events_long["filing_date"] = pd.to_datetime(events_long["filing_date"]).dt.normalize()
    stakes = stakes_13d_event_panel(
        events_long, sessions, tickers, window_days=STAKES_WINDOW_DAYS,
    )

    peer_long = (
        peer[tickers].stack().rename("peer_mom").reset_index()
        .rename(columns={"level_0": "date", "level_1": "ticker"})
    )
    stakes_long = (
        stakes[tickers].stack().rename("stakes_13d_event").reset_index()
        .rename(columns={"level_0": "date", "level_1": "ticker"})
    )
    rel = peer_long.merge(stakes_long, on=["date", "ticker"], how="outer")
    rel["date"] = pd.to_datetime(rel["date"]).dt.normalize()
    print(f"[D] rel_extra: {len(rel)} rows; "
          f"peer_mom valid={int(rel['peer_mom'].notna().sum())}, "
          f"stakes_13d_event sum={int(rel['stakes_13d_event'].sum())}", flush=True)
    return rel


def main() -> None:
    import os

    artifacts_only = os.environ.get("PHASE_D_NO_LEDGER") == "1"

    fund = pd.read_parquet(CACHE / "phase_b_fundamentals.parquet")
    px = pd.read_parquet(CACHE / "phase_b_prices.parquet")
    mem = load_pierrebrunelle_membership()
    print(f"[D] fund rows={len(fund)}  prices={px.shape}  membership={mem.shape}",
          flush=True)

    rel_extra = _build_rel_extra(px)

    # coverage guard: refuse to commit a degenerate config from a partial/smoke
    # fetch (would write a meaningless confirmatory:first — or crash on missing
    # rel columns). The full universe resolves ~588 tickers; <80% or an all-NaN
    # peer_mom means the fetch is incomplete.
    sic_df = pd.read_parquet(CACHE / "phase_d_sic_map.parquet")
    cov = len(set(px.columns) & set(sic_df["ticker"])) / max(len(px.columns), 1)
    peer_valid = int(rel_extra["peer_mom"].notna().sum())
    stakes_sum = int(rel_extra["stakes_13d_event"].sum())
    print(f"[D] coverage={cov:.0%}  peer_mom_valid={peer_valid}  stakes_events={stakes_sum}",
          flush=True)
    if cov < 0.8 or peer_valid == 0:
        raise SystemExit(
            f"[D] ABORT: sic coverage {cov:.0%} (<80%) or peer_mom has no valid values "
            f"({peer_valid}) — the rel bundle is degenerate (fetch incomplete / smoke cache). "
            "Refusing to commit a meaningless confirmatory:first. "
            "Run: uv run python scripts/phase_d_fetch.py"
        )
    if stakes_sum == 0:
        print("[D] WARNING: zero 13D events in the window — stakes_13d_event is all-0 "
              "(no variance; proceeding but the 13D channel is degenerate).", flush=True)

    shas = {
        "fund_sha256": _sha(CACHE / "phase_b_fundamentals.parquet"),
        "prices_sha256": _sha(CACHE / "phase_b_prices.parquet"),
        "membership_sha256": _sha(CACHE / "universe_pierrebrunelle.parquet"),
        "uv_lock_sha256": _sha(Path("uv.lock")),
        "sic_map_sha256": _sha(CACHE / "phase_d_sic_map.parquet"),
        "events_sha256": _sha(CACHE / "phase_d_13d_events.parquet"),
    }
    rel_meta = {
        "peer_window_sessions": PEER_WINDOW,
        "stakes_window_days": STAKES_WINDOW_DAYS,
        "feature_cols_pinned": FEATURE_COLS,
        "rel_cols_pinned": REL_COLS,
    }
    config = build_config(shas, rel_meta)
    if artifacts_only:
        sig = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
        print(f"[D] ARTIFACTS-ONLY rerun (no ledger write); sig={sig}", flush=True)
    else:
        sig = commit_config(config, LEDGER)  # HIGH-1: BEFORE any result
        print(f"[D] config_committed sig={sig}  (logged BEFORE result)", flush=True)

    result = run_confirmatory(
        fund, px, mem, rel_extra=rel_extra, config=config, sig=sig,
        ledger_path=None if artifacts_only else LEDGER, results_base=None,
    )

    d = result["differential_rel_minus_base"]
    pl = result["controls"]["bundle_shuffle_placebo"]
    print(
        f"[D] arm_rel(CV-proxy) mean_IC={result['arm_rel_cvproxy']['mean_ic']:.4f} "
        f"t_hac={result['arm_rel_cvproxy']['t_hac']:.3f}", flush=True,
    )
    print(
        f"[D] arm_base(CV-proxy) mean_IC={result['arm_base_cvproxy']['mean_ic']:.4f} "
        f"t_hac={result['arm_base_cvproxy']['t_hac']:.3f}", flush=True,
    )
    print(
        f"[D] differential rel-base: mean={d['mean_diff']:.4f} "
        f"DM p_mbb={d['dm_p_mbb']:.4f} ci_half={d['ci_half']:.4f} "
        f"(publishable={d['publishable_ci_half']}) n={d['n_months']}", flush=True,
    )
    print(
        f"[D] bundle-shuffle placebo: mean={pl['mean_diff']:.4f} "
        f"DM p_mbb={pl['dm_p_mbb']:.4f} (must vanish if signal is real)", flush=True,
    )
    loo = result["controls"]["leave_one_out"]
    loo_str = ", ".join(f"{k}={v['mean_diff']:+.4f}" for k, v in loo.items())
    print(f"[D] leave-one-out: {loo_str}", flush=True)
    print(f"[D] H6 deterministic (IC + raw scores) = {result['H6_deterministic']}",
          flush=True)
    print(f"[D] logged confirmatory:first (config_sig={sig})", flush=True)
    print("[D] DONE", flush=True)


if __name__ == "__main__":
    main()
