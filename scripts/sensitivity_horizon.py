"""EXPLORATORY horizon-robustness sweep of the frozen Phase B/C/D nulls.

Re-runs the two-arm rank-IC differential at h=10 and h=42. The frozen
confirmatory horizon is h=21; EVERY non-21 horizon is a changed-config
EXPLORATORY run (per the durable-registry policy), so this writes only ONE
``exploratory`` summary row to the ledger -- never a ``confirmatory:first``.

For each (phase, horizon) we compute the shared folds ONCE, run the two arms on
those folds, take monthly rank-IC of each, and report the differential (enhanced
arm minus ``arm_base``) with DM-p (:func:`diebold_mariano_mbb`) and ci_half
(:func:`rank_ic_summary` on the diff series -- reused from
:mod:`aionis.eval.phase_c`). If the three frozen h=21 nulls (no incremental
rank-IC from fundamental timing / the macro-earnings bundle / the relationship
bundle) survive at h=10 and h=42, the publishable-as-null result is strengthened;
if any horizon flips to a positive-significant differential, that is
scientifically interesting.

Lean by design: no H6 / placebo / LOO / save_run / config_committed per horizon.

Arms (mirror the frozen confirmatory specs):
  * Phase B: arm_state (align_on="filed")            vs arm_base (align_on="end_lag")
  * Phase C: arm_macro (FEATURE+BUNDLE, end_lag,     vs arm_base
             macro=bundle_broadcast, extra=earnings_long)
  * Phase D: arm_rel   (FEATURE+REL, end_lag,        vs arm_base
             extra=rel_extra)

``arm_base`` is ``align_on="end_lag"`` with ``FEATURE_COLS`` in ALL THREE phases
(``scripts.phase_b_run``, ``aionis.eval.phase_c.run_confirmatory``,
``aionis.eval.phase_d.run_confirmatory``), and the shared folds depend only on
``(px, mem, horizon, n_splits, embargo)``. So for a fixed horizon ``arm_base`` is
bit-identical across B/C/D -> computed ONCE and shared (the lean path; results
are unchanged vs. a per-phase recompute).

Run:  uv run python scripts/sensitivity_horizon.py   (background-safe; ~30-45 min)
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path

import pandas as pd

from aionis.config import settings
from aionis.eval.phase_c import BUNDLE_COLS, FEATURE_COLS, build_bundle, differential
from aionis.eval.phase_d import REL_COLS
from aionis.eval.rank_ic import rank_ic_monthly
from aionis.eval.two_arm import compute_shared_folds, run_arm_oos
from aionis.features.alignment import nyse_sessions
from aionis.features.peer_momentum import peer_momentum_panel
from aionis.features.stakes_13d_signal import stakes_13d_event_panel
from aionis.ingest.universe import load_pierrebrunelle_membership

CACHE = settings.data_dir / "cache"
LEDGER = Path("runs/ledger.jsonl")
HORIZONS = [10, 42]  # exploratory; h=21 is the frozen confirmatory horizon
FROZEN_HORIZON = 21
N_SPLITS = 5
EMBARGO = 21
PEER_WINDOW = 21  # trailing sessions (~1 month) -- mirrors scripts.phase_d_run
STAKES_WINDOW_DAYS = 60  # post-13D window (~3 months) -- mirrors scripts.phase_d_run


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _build_rel_extra(px: pd.DataFrame) -> pd.DataFrame:
    """Assemble the per-(ticker, date) rel bundle ``[date, ticker, peer_mom,
    stakes_13d_event]`` -- mirrors ``scripts.phase_d_run._build_rel_extra`` exactly
    (same cached SIC map + external 13D events, same windows)."""
    sessions = nyse_sessions(px.index.min(), px.index.max())
    assert pd.DatetimeIndex(px.index).normalize().equals(pd.DatetimeIndex(sessions)), (
        "px.index is not the NYSE session grid -- rel_extra would misalign with the panel"
    )
    sic = pd.read_parquet(CACHE / "phase_d_sic_map.parquet")
    events = pd.read_parquet(CACHE / "phase_d_13d_events.parquet")
    sic_map = dict(zip(sic["ticker"], sic["sic"], strict=True))
    tickers = [t for t in px.columns if t in sic_map]

    sess = pd.DatetimeIndex(px.index).normalize()
    peer = peer_momentum_panel(px, sic_map, window=PEER_WINDOW, tickers=tickers)
    events_long = events[["ticker", "filing_date"]].copy()
    events_long["filing_date"] = pd.to_datetime(events_long["filing_date"]).dt.normalize()
    stakes = stakes_13d_event_panel(events_long, sess, tickers, window_days=STAKES_WINDOW_DAYS)

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
    print(f"[H] rel_extra: {len(rel)} rows; "
          f"peer_mom valid={int(rel['peer_mom'].notna().sum())}, "
          f"stakes_13d_event sum={int(rel['stakes_13d_event'].sum())}", flush=True)
    return rel


def _null_holds(diff: dict) -> bool:
    """The null (no incremental rank-IC) holds iff the differential's 95% HAC CI
    brackets zero (cannot reject H0). A positive-significant flip = ``ci_lo > 0``."""
    return bool(diff["ci_lo"] <= 0.0 <= diff["ci_hi"])


def main() -> None:
    fund = pd.read_parquet(CACHE / "phase_b_fundamentals.parquet")
    px = pd.read_parquet(CACHE / "phase_b_prices.parquet")
    mem = load_pierrebrunelle_membership()
    print(f"[H] fund rows={len(fund)}  prices={px.shape}  membership={mem.shape}", flush=True)

    # horizon-independent bundles (cached ALFRED/VIX + cached SIC/13D -> no network)
    bundle_broadcast, earnings_long = build_bundle(fund, px, settings.fred_api_key, CACHE)
    print(f"[H] bundle_broadcast={bundle_broadcast.shape}  earnings_long={earnings_long.shape}",
          flush=True)
    rel_extra = _build_rel_extra(px)

    # the three phases' enhanced arms (arm_base is shared across phases per horizon)
    phases: dict[str, dict] = {
        "B": dict(name="arm_state", feature_cols=FEATURE_COLS, align_on="filed"),
        "C": dict(name="arm_macro", feature_cols=FEATURE_COLS + BUNDLE_COLS, align_on="end_lag",
                  macro=bundle_broadcast, extra=earnings_long),
        "D": dict(name="arm_rel", feature_cols=FEATURE_COLS + REL_COLS, align_on="end_lag",
                  extra=rel_extra),
    }

    results: dict[str, dict] = {}
    for horizon in HORIZONS:
        print(f"\n[H] === horizon={horizon} (exploratory; frozen confirmatory is "
              f"h={FROZEN_HORIZON}) ===", flush=True)
        folds, ref = compute_shared_folds(px, mem, horizon, N_SPLITS, EMBARGO)
        # shared arm_base: identical across B/C/D for a fixed horizon (see module docstring)
        base_panel = run_arm_oos(px, fund, mem, horizon, FEATURE_COLS, "end_lag", folds, ref)
        base_ic = rank_ic_monthly(base_panel, "score", "y_fwd_ret")
        print(f"[H]   arm_base mean_IC={base_ic.mean():+.4f}  n_months={len(base_ic)}", flush=True)
        results[str(horizon)] = {}
        for phase, cfg in phases.items():
            panel = run_arm_oos(
                px, fund, mem, horizon, cfg["feature_cols"], cfg["align_on"], folds, ref,
                macro=cfg.get("macro"), extra_features=cfg.get("extra"),
            )
            ic_e = rank_ic_monthly(panel, "score", "y_fwd_ret")
            diff = differential(ic_e, base_ic)
            null = _null_holds(diff)
            results[str(horizon)][phase] = {
                "arm_enhanced": cfg["name"],
                "enhanced_mean_ic": float(ic_e.mean()),
                "base_mean_ic": float(base_ic.mean()),
                **diff,
                "null_holds": null,
            }
            print(f"[H]   Phase {phase} ({cfg['name']}): enhanced_IC={ic_e.mean():+.4f} "
                  f"diff={diff['mean_diff']:+.4f}  DM p={diff['dm_p_mbb']:.4f}  "
                  f"ci_half={diff['ci_half']:.4f}  ci=[{diff['ci_lo']:+.4f},"
                  f"{diff['ci_hi']:+.4f}]  null_holds={null}", flush=True)

    _print_table(results)
    _append_ledger(results)
    all_robust = all(r["null_holds"] for h in results.values() for r in h.values())
    print(f"\n[H] horizon-robust (all 3 nulls hold at h=10 AND h=42): {all_robust}", flush=True)
    print("[H] DONE (exploratory; no confirmatory rows written)", flush=True)


def _print_table(results: dict[str, dict]) -> None:
    print("\n=== Horizon-robustness sweep (exploratory; frozen confirmatory = h=21) ===",
          flush=True)
    for phase in ("B", "C", "D"):
        cfg_name = {"B": "arm_state", "C": "arm_macro", "D": "arm_rel"}[phase]
        print(f"\nPhase {phase} ({cfg_name} - arm_base):", flush=True)
        for horizon in HORIZONS:
            r = results[str(horizon)][phase]
            print(f"  h={horizon:>2}: enhanced_IC={r['enhanced_mean_ic']:+.4f}  "
                  f"diff={r['mean_diff']:+.4f}  DM p={r['dm_p_mbb']:.4f}  "
                  f"CI[{r['ci_lo']:+.4f},{r['ci_hi']:+.4f}]  ci_half={r['ci_half']:.4f}  "
                  f"null={r['null_holds']}", flush=True)


def _append_ledger(results: dict[str, dict]) -> None:
    entry = {
        "ts": _now(),
        "event": "exploratory",
        "phase": "sensitivity_horizon",
        "horizons": HORIZONS,
        "frozen_confirmatory_horizon": FROZEN_HORIZON,
        "results": results,
        "null_criterion": "null_holds iff the differential's 95% HAC CI brackets zero",
        "notes": (
            "Horizon-robustness sweep of the frozen h=21 Phase B/C/D nulls. "
            "Differential = enhanced arm minus arm_base (shared folds). EXPLORATORY "
            "(h!=21 = changed config); no confirmatory rows written. arm_base is "
            "shared across phases per horizon (identical by construction)."
        ),
    }
    with open(LEDGER, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
    print(f"[H] appended exploratory summary row to {LEDGER}", flush=True)


if __name__ == "__main__":
    main()
