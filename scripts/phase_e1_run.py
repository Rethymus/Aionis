"""Phase E1 first confirmatory run — structural shock propagation.

Loads Phase B/C/D cached data + builds the self-shock frames (earnings surprise,
13D event) and their SIC-peer-propagated (ex-self) counterparts, commits the
config (sha256 BEFORE any result), then runs the E1 pipeline:
  arm_base_self (fundamentals + OWN shocks) vs arm_prop (+ propagated peer shocks)
  -> differential isolates propagation beyond self (phase-e-preregistration §2).

Zero-leakage baseline of the Phase E sequence. Run: uv run python scripts/phase_e1_run.py
(PHASE_E1_NO_LEDGER=1 -> artifacts-only reproducibility rerun, no ledger write).
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pandas as pd

from aionis.config import settings
from aionis.eval.phase_e1 import (
    FEATURE_COLS,
    PROP_COLS,
    SELF_COLS,
    build_config,
    commit_config,
    run_confirmatory,
)
from aionis.features.alignment import nyse_sessions
from aionis.features.earnings_surprise import earnings_surprise_as_of, earnings_surprise_long
from aionis.features.propagation import propagate_panel
from aionis.features.stakes_13d_signal import stakes_13d_event_panel
from aionis.ingest.universe import load_pierrebrunelle_membership

CACHE = settings.data_dir / "cache"
LEDGER = "runs/ledger.jsonl"
STAKES_WINDOW_DAYS = 60


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def _long(wide: pd.DataFrame, tickers: list[str], name: str) -> pd.DataFrame:
    return (
        wide[tickers].stack().rename(name).reset_index()
        .rename(columns={"level_0": "date", "level_1": "ticker"})
    )


def _build_self_prop(px: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """self_extra [date,ticker,self_earnings_surprise,self_13d_event] +
    prop_extra [date,ticker,peer_earnings_surprise,peer_13d_event]."""
    fund = pd.read_parquet(CACHE / "phase_b_fundamentals.parquet")
    sic = pd.read_parquet(CACHE / "phase_d_sic_map.parquet")
    events = pd.read_parquet(CACHE / "phase_d_13d_events.parquet")
    sic_map = dict(zip(sic["ticker"], sic["sic"], strict=True))
    tickers = [t for t in px.columns if t in sic_map]

    sessions = nyse_sessions(px.index.min(), px.index.max())
    assert pd.DatetimeIndex(px.index).normalize().equals(pd.DatetimeIndex(sessions)), (
        "px.index is not the NYSE session grid"
    )

    # self shocks (wide date x ticker), PIT via filed/filing_date
    surprise_long = earnings_surprise_long(fund)
    self_earn = earnings_surprise_as_of(surprise_long, pd.DatetimeIndex(sessions), tickers)
    events_long = events[["ticker", "filing_date"]].copy()
    events_long["filing_date"] = pd.to_datetime(events_long["filing_date"]).dt.normalize()
    self_13d = stakes_13d_event_panel(
        events_long, pd.DatetimeIndex(sessions), tickers, window_days=STAKES_WINDOW_DAYS,
    )

    # propagated across same-SIC peers (ex-self) — the E1 claim
    peer_earn = propagate_panel(self_earn, sic_map, tickers=tickers)
    peer_13d = propagate_panel(self_13d, sic_map, tickers=tickers)

    self_extra = _long(self_earn, tickers, "self_earnings_surprise").merge(
        _long(self_13d, tickers, "self_13d_event"), on=["date", "ticker"], how="outer",
    )
    prop_extra = _long(peer_earn, tickers, "peer_earnings_surprise").merge(
        _long(peer_13d, tickers, "peer_13d_event"), on=["date", "ticker"], how="outer",
    )
    for df in (self_extra, prop_extra):
        df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    print(f"[E1] self_extra={len(self_extra)} prop_extra={len(prop_extra)} | "
          f"self_earn valid={int(self_extra['self_earnings_surprise'].notna().sum())}, "
          f"self_13d sum={int(self_extra['self_13d_event'].sum())}, "
          f"peer_earn valid={int(prop_extra['peer_earnings_surprise'].notna().sum())}, "
          f"peer_13d sum={int(prop_extra['peer_13d_event'].sum())}", flush=True)
    return self_extra, prop_extra, tickers


def main() -> None:
    artifacts_only = os.environ.get("PHASE_E1_NO_LEDGER") == "1"
    fund = pd.read_parquet(CACHE / "phase_b_fundamentals.parquet")
    px = pd.read_parquet(CACHE / "phase_b_prices.parquet")
    mem = load_pierrebrunelle_membership()
    print(f"[E1] fund rows={len(fund)} prices={px.shape} membership={mem.shape}", flush=True)

    self_extra, prop_extra, _tickers = _build_self_prop(px)

    # coverage guard: propagation must have variance (peer_earn valid > 0)
    peer_earn_valid = int(prop_extra["peer_earnings_surprise"].notna().sum())
    if peer_earn_valid == 0:
        raise SystemExit(
            "[E1] ABORT: peer_earnings_surprise is all-NaN — no SIC peer groups "
            "formed (sic_map empty / fetch incomplete). Refusing to commit a "
            "meaningless confirmatory:first."
        )

    shas = {
        "fund_sha256": _sha(CACHE / "phase_b_fundamentals.parquet"),
        "prices_sha256": _sha(CACHE / "phase_b_prices.parquet"),
        "membership_sha256": _sha(CACHE / "universe_pierrebrunelle.parquet"),
        "uv_lock_sha256": _sha(Path("uv.lock")),
        "sic_map_sha256": _sha(CACHE / "phase_d_sic_map.parquet"),
        "events_sha256": _sha(CACHE / "phase_d_13d_events.parquet"),
    }
    e1_meta = {
        "stakes_window_days": STAKES_WINDOW_DAYS,
        "feature_cols_pinned": FEATURE_COLS,
        "self_cols_pinned": SELF_COLS,
        "prop_cols_pinned": PROP_COLS,
        "propagation": "ex-self SIC-peer mean (propagate_panel)",
    }
    config = build_config(shas, e1_meta)
    if artifacts_only:
        sig = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
        print(f"[E1] ARTIFACTS-ONLY rerun (no ledger write); sig={sig}", flush=True)
    else:
        sig = commit_config(config, LEDGER)
        print(f"[E1] config_committed sig={sig} (logged BEFORE result)", flush=True)

    result = run_confirmatory(
        fund, px, mem, self_extra=self_extra, prop_extra=prop_extra,
        config=config, sig=sig,
        ledger_path=None if artifacts_only else LEDGER, results_base=None,
    )

    d = result["differential_prop_minus_base_self"]
    pl = result["controls"]["bundle_shuffle_placebo"]
    print(f"[E1] arm_prop(CV-proxy) mean_IC={result['arm_prop_cvproxy']['mean_ic']:.4f} "
          f"t_hac={result['arm_prop_cvproxy']['t_hac']:.3f}", flush=True)
    bs = result["arm_base_self_cvproxy"]
    print(f"[E1] arm_base_self(CV-proxy) mean_IC={bs['mean_ic']:.4f} t_hac={bs['t_hac']:.3f}",
          flush=True)
    print(f"[E1] differential prop-base_self: mean={d['mean_diff']:.4f} "
          f"DM p_mbb={d['dm_p_mbb']:.4f} ci_half={d['ci_half']:.4f} "
          f"(publishable={d['publishable_ci_half']}) n={d['n_months']}", flush=True)
    print(f"[E1] bundle-shuffle placebo: mean={pl['mean_diff']:.4f} "
          f"DM p_mbb={pl['dm_p_mbb']:.4f} (must vanish if signal is real)", flush=True)
    loo = result["controls"]["leave_one_out"]
    loo_str = ", ".join(f"{k}={v['mean_diff']:+.4f}" for k, v in loo.items())
    print(f"[E1] leave-one-out: {loo_str}", flush=True)
    print(f"[E1] H6 deterministic (IC + raw scores) = {result['H6_deterministic']}", flush=True)
    print(f"[E1] logged confirmatory:first (config_sig={sig})", flush=True)
    print("[E1] DONE", flush=True)


if __name__ == "__main__":
    main()
