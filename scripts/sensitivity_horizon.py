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
  * Phase E1: arm_prop (FEATURE+SELF+PROP, end_lag,  vs arm_base_self (FEATURE+SELF,
              extra=self+prop)                          end_lag, extra=self)

B/C/D share ONE plain ``arm_base`` (``FEATURE_COLS``, ``end_lag``) per horizon, so they
route through ``differential(ic_e, base_ic)``. Phase E1 is the exception: its base is
``arm_base_self`` (propagation beyond SELF), so it computes its own base and uses
``differential(ic_pr, ic_bs)``. Routing E1 against the shared ``base_ic`` would measure
"prop vs fundamentals-only" -- a scientifically meaningless differential. If the E1
propagation is degenerate (``peer_earnings_surprise`` all-NaN), the sweep degrades
gracefully (``null_holds=None``) instead of aborting, so B/C/D still land.

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
from aionis.eval.phase_e1 import PROP_COLS, SELF_COLS
from aionis.eval.rank_ic import rank_ic_monthly
from aionis.eval.two_arm import compute_shared_folds, run_arm_oos
from aionis.features.alignment import nyse_sessions
from aionis.features.earnings_surprise import earnings_surprise_as_of, earnings_surprise_long
from aionis.features.peer_momentum import peer_momentum_panel
from aionis.features.propagation import propagate_panel
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


def _long(wide: pd.DataFrame, tickers: list[str], name: str) -> pd.DataFrame:
    return (
        wide[tickers].stack().rename(name).reset_index()
        .rename(columns={"level_0": "date", "level_1": "ticker"})
    )


def _build_self_prop(px: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """self_extra [date,ticker,self_earnings_surprise,self_13d_event] +
    prop_extra [date,ticker,peer_earnings_surprise,peer_13d_event] -- mirrors
    ``scripts.phase_e1_run._build_self_prop`` exactly (same PIT construction:
    earnings-surprise via filed-date -> as_of; self_13D via filing_date;
    ``propagate_panel`` for the ex-self SIC-peer frames; ``STAKES_WINDOW_DAYS=60``).
    Horizon-independent -> computed ONCE in ``main``.

    Returns ``(self_extra, prop_extra, tickers)``; caller decides whether to run E1
    based on ``prop_extra["peer_earnings_surprise"]`` coverage (Edit 7 guard).
    """
    fund = pd.read_parquet(CACHE / "phase_b_fundamentals.parquet")
    sic = pd.read_parquet(CACHE / "phase_d_sic_map.parquet")
    events = pd.read_parquet(CACHE / "phase_d_13d_events.parquet")
    sic_map = dict(zip(sic["ticker"], sic["sic"], strict=True))
    tickers = [t for t in px.columns if t in sic_map]

    sessions = nyse_sessions(px.index.min(), px.index.max())
    assert pd.DatetimeIndex(px.index).normalize().equals(pd.DatetimeIndex(sessions)), (
        "px.index is not the NYSE session grid -- self_prop would misalign with the panel"
    )

    # self shocks (wide date x ticker), PIT via filed/filing_date
    surprise_long = earnings_surprise_long(fund)
    self_earn = earnings_surprise_as_of(surprise_long, pd.DatetimeIndex(sessions), tickers)
    events_long = events[["ticker", "filing_date"]].copy()
    events_long["filing_date"] = pd.to_datetime(events_long["filing_date"]).dt.normalize()
    self_13d = stakes_13d_event_panel(
        events_long, pd.DatetimeIndex(sessions), tickers, window_days=STAKES_WINDOW_DAYS,
    )

    # propagated across same-SIC peers (ex-self) -- the E1 claim
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
    print(f"[H] self_extra={len(self_extra)} prop_extra={len(prop_extra)} | "
          f"self_earn valid={int(self_extra['self_earnings_surprise'].notna().sum())}, "
          f"self_13d sum={int(self_extra['self_13d_event'].sum())}, "
          f"peer_earn valid={int(prop_extra['peer_earnings_surprise'].notna().sum())}, "
          f"peer_13d sum={int(prop_extra['peer_13d_event'].sum())}", flush=True)
    return self_extra, prop_extra, tickers


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
    # E1 self/prop shock frames (horizon-independent) -- built ONCE here, reused
    # at every horizon. peer_earn_valid gates the E1 branch (Edit 7 guard).
    self_extra, prop_extra, _e1_tickers = _build_self_prop(px)
    peer_earn_valid = int(prop_extra["peer_earnings_surprise"].notna().sum())
    e1_degenerate = peer_earn_valid == 0
    if e1_degenerate:
        print("[H] WARNING: E1 peer_earnings_surprise is all-NaN (degenerate SIC map / "
              "propagation yielded nothing); E1 null_holds will be None, B/C/D still run",
              flush=True)

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

        # === Phase E1: arm_prop vs arm_base_self (propagation beyond SELF) ===
        # STRUCTURAL TRAP: E1's base is arm_base_self (FEATURE+SELF), NOT the sweep's
        # shared plain base_ic (FEATURE-only). differential(ic_pr, ic_bs) measures
        # propagation beyond SELF; routing E1 through differential(ic_pr, base_ic)
        # would measure "prop vs fundamentals-only" -- scientifically meaningless.
        if e1_degenerate:
            results[str(horizon)]["E1"] = {
                "arm_enhanced": "arm_prop", "arm_base": "arm_base_self",
                "enhanced_mean_ic": None, "base_mean_ic": None,
                "mean_diff": None, "ci_lo": None, "ci_hi": None, "ci_half": None,
                "dm_p_mbb": None, "null_holds": None,
                "note": ("degenerate: peer_earnings_surprise all-NaN at build time "
                         "(SIC map empty / propagate_panel yielded nothing)"),
            }
            print("[H]   Phase E1 (arm_prop - arm_base_self): DEGENERATE "
                  "(peer_earnings_surprise all-NaN); null_holds=None", flush=True)
        else:
            full_extra_e1 = self_extra.merge(
                prop_extra, on=["date", "ticker"], how="outer",
            )
            bs_panel = run_arm_oos(
                px, fund, mem, horizon, FEATURE_COLS + SELF_COLS,
                "end_lag", folds, ref, extra_features=self_extra,
            )
            ic_bs = rank_ic_monthly(bs_panel, "score", "y_fwd_ret")
            pr_panel = run_arm_oos(
                px, fund, mem, horizon, FEATURE_COLS + SELF_COLS + PROP_COLS,
                "end_lag", folds, ref, extra_features=full_extra_e1,
            )
            ic_pr = rank_ic_monthly(pr_panel, "score", "y_fwd_ret")
            diff_e1 = differential(ic_pr, ic_bs)   # phase_c.differential; base = arm_base_self
            null_e1 = _null_holds(diff_e1)
            results[str(horizon)]["E1"] = {
                "arm_enhanced": "arm_prop",
                "arm_base": "arm_base_self",
                "enhanced_mean_ic": float(ic_pr.mean()),
                "base_mean_ic": float(ic_bs.mean()),
                **diff_e1,
                "null_holds": null_e1,
            }
            print(f"[H]   Phase E1 (arm_prop - arm_base_self): "
                  f"enhanced_IC={ic_pr.mean():+.4f}  diff={diff_e1['mean_diff']:+.4f}  "
                  f"DM p={diff_e1['dm_p_mbb']:.4f}  ci_half={diff_e1['ci_half']:.4f}  "
                  f"ci=[{diff_e1['ci_lo']:+.4f},{diff_e1['ci_hi']:+.4f}]  "
                  f"null_holds={null_e1}", flush=True)

    _print_table(results)
    _append_ledger(results)
    bcd_robust = all(
        results[str(h)][p]["null_holds"] for h in HORIZONS for p in ("B", "C", "D")
    )
    e1_rows = [results[str(h)]["E1"] for h in HORIZONS]
    e1_any_degenerate = any(r.get("null_holds") is None for r in e1_rows)
    e1_robust = all(bool(r.get("null_holds")) for r in e1_rows)
    print(f"\n[H] horizon-robust B/C/D (all 3 nulls hold at h=10 AND h=42): {bcd_robust}",
          flush=True)
    if e1_any_degenerate:
        print("[H] Phase E1: DEGENERATE at >=1 horizon (peer_earnings_surprise all-NaN); "
              "null_holds=None -- see row notes; not sig-gated (exploratory)", flush=True)
    else:
        print(f"[H] horizon-robust E1 (arm_prop-base_self null holds at h=10 AND h=42): "
              f"{e1_robust}", flush=True)
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

    # Phase E1: base is arm_base_self (NOT the shared arm_base) -> printed separately.
    print("\nPhase E1 (arm_prop - arm_base_self):", flush=True)
    for horizon in HORIZONS:
        r = results[str(horizon)]["E1"]
        if r.get("mean_diff") is None:
            print(f"  h={horizon:>2}: DEGENERATE (peer_earnings_surprise all-NaN); "
                  f"null={r['null_holds']}", flush=True)
        else:
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
            "Horizon-robustness sweep of the frozen h=21 Phase B/C/D nulls + the E1 "
            "(propagation-beyond-self) null. B/C/D differential = enhanced arm minus the "
            "shared plain arm_base (FEATURE_COLS, end_lag); Phase E1 differential = "
            "arm_prop minus arm_base_self (NOT the shared base -- propagation beyond SELF). "
            "EXPLORATORY (h!=21 = changed config); no confirmatory rows written. "
            "arm_base is shared across B/C/D per horizon (identical by construction)."
        ),
    }
    with open(LEDGER, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
    print(f"[H] appended exploratory summary row to {LEDGER}", flush=True)


if __name__ == "__main__":
    main()
