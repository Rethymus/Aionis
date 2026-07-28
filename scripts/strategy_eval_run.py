"""Strategy-return evaluation across the Phase B + Phase C OOS score panels.

Secondary/exploratory lens (pre-reg §6): the confirmatory claims are the rank-IC
differentials (Phase B/C nulls). This recomputes the headline OOS score panels
on the SAME frozen data / folds / learner, builds a monthly long-short portfolio
from each, and applies the multiple-testing corrections already wired in
``eval.multiple_testing`` (DSR / Hansen-SPA / MCS). Answers: does any score-based
L-S strategy earn a Sharpe that survives deflation and beats the fundamentals-only
benchmark — i.e. is there a TRADEABLE signal the rank-IC null might have missed?

Strategies (shared folds, so directly comparable):
  * ``B_arm_state``  — Phase B filed-date timing (fundamentals only)
  * ``arm_base``     — Phase B/C period-end+lag baseline (the SPA benchmark)
  * ``C_arm_macro``  — Phase C fundamentals + surprise bundle
  * ``C_placebo``    — Phase C bundle-shuffle placebo (must not beat base)
  * ``C_sanity``     — Phase C + priced Mkt-RF (calibration)

Run:  uv run python scripts/strategy_eval_run.py   (background-safe; ~15 min)

Logged to ``runs/ledger.jsonl`` as ``event: "exploratory"`` (NOT confirmatory) —
strategy-return is a secondary lens; the rank-IC differentials remain the
pre-registered falsifiable claims.
"""
from __future__ import annotations

import json

import pandas as pd

from aionis.config import settings
from aionis.eval.learner import FROZEN_PARAMS
from aionis.eval.phase_c import (
    BUNDLE_COLS,
    EMBARGO,
    FEATURE_COLS,
    HORIZON,
    N_SPLITS,
    SANITY_COL,
    build_bundle,
    build_sanity,
)
from aionis.eval.phase_c_controls import (
    shuffle_date_broadcast,
    shuffle_earnings_across_tickers,
)
from aionis.eval.strategy_returns import long_short_returns, strategy_eval
from aionis.eval.two_arm import compute_shared_folds, run_arm_oos
from aionis.ingest.universe import load_pierrebrunelle_membership

CACHE = settings.data_dir / "cache"
LEDGER = "runs/ledger.jsonl"


def _now() -> str:
    import datetime

    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _append(entry: dict) -> None:
    with open(LEDGER, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


def main() -> None:
    fund = pd.read_parquet(CACHE / "phase_b_fundamentals.parquet")
    px = pd.read_parquet(CACHE / "phase_b_prices.parquet")
    mem = load_pierrebrunelle_membership()
    print(f"[S] fund rows={len(fund)}  prices={px.shape}  membership={mem.shape}",
          flush=True)

    bundle_broadcast, earnings_long = build_bundle(fund, px, settings.fred_api_key, CACHE)
    sanity_broadcast = build_sanity(px)
    print(f"[S] bundle={bundle_broadcast.shape}  earnings={earnings_long.shape}  "
          f"sanity={sanity_broadcast.shape}", flush=True)

    folds, ref = compute_shared_folds(px, mem, HORIZON, N_SPLITS, EMBARGO)
    print(f"[S] shared folds={len(folds)}  ref rows={len(ref)}", flush=True)
    params = FROZEN_PARAMS

    def _arm(name, feature_cols, align_on, **kw):
        print(f"[S]   computing {name} ...", flush=True)
        panel = run_arm_oos(px, fund, mem, HORIZON, feature_cols, align_on,
                            folds, ref, params, **kw)
        print(f"[S]   {name}: {len(panel)} OOS rows", flush=True)
        return panel

    panels = {
        "B_arm_state": _arm("B_arm_state", FEATURE_COLS, "filed"),
        "arm_base": _arm("arm_base", FEATURE_COLS, "end_lag"),
        "C_arm_macro": _arm("C_arm_macro", FEATURE_COLS + BUNDLE_COLS, "end_lag",
                            macro=bundle_broadcast, extra_features=earnings_long),
        "C_placebo": _arm("C_placebo", FEATURE_COLS + BUNDLE_COLS, "end_lag",
                          macro=shuffle_date_broadcast(bundle_broadcast),
                          extra_features=shuffle_earnings_across_tickers(earnings_long)),
        "C_sanity": _arm("C_sanity", FEATURE_COLS + [SANITY_COL], "end_lag",
                         macro=sanity_broadcast),
    }

    ls = {name: long_short_returns(p, quantile=0.2) for name, p in panels.items()}
    print("[S] monthly L-S return lengths: "
          + ", ".join(f"{n}={len(s)}" for n, s in ls.items()), flush=True)
    for n, s in ls.items():
        if len(s):
            ann = (s.mean() / s.std(ddof=1) * (12 ** 0.5)) if s.std(ddof=1) > 0 else float("nan")
            print(f"[S]   {n}: mean={s.mean():+.5f} sharpe_ann={ann:+.3f} n={len(s)}",
                  flush=True)

    eval_out = strategy_eval(ls, benchmark="arm_base", n_trials=len(ls))
    print(f"[S] strategy_eval (benchmark=arm_base, n_trials={len(ls)}, "
          f"n_months_common={eval_out['n_months_common']}):", flush=True)
    for n, m in eval_out["per_strategy"].items():
        print(f"[S]   {n:12s} sharpe_ann={m['sharpe_annualized']:+.3f} "
              f"dsr={m['dsr']:.3f} dsr_p={m['dsr_p_value']:.3f}", flush=True)
    if "spa" in eval_out:
        print(f"[S]   Hansen-SPA consistent_p={eval_out['spa']['consistent_pvalue']:.3f} "
              f"(H0: nothing beats arm_base)", flush=True)
    if "mcs" in eval_out:
        inc = eval_out["mcs"]["included"]
        names = list(ls)
        print(f"[S]   Hansen-MCS included={ [names[i] for i in inc] }", flush=True)

    _append({
        "ts": _now(), "event": "exploratory", "phase": "strategy_return",
        "strategies": {n: {"sharpe_annualized": m["sharpe_annualized"],
                           "dsr": m["dsr"], "dsr_p_value": m["dsr_p_value"],
                           "n_months": m["n_months"]}
                       for n, m in eval_out["per_strategy"].items()},
        "spa": eval_out.get("spa"),
        "mcs_included": eval_out.get("mcs", {}).get("included"),
        "benchmark": "arm_base", "n_trials": len(ls),
        "n_months_common": eval_out["n_months_common"],
        "notes": ("Secondary/exploratory lens. Confirmatory claims remain the "
                  "Phase B/C rank-IC differentials. DSR deflated at n_trials="
                  f"{len(ls)} (the strategy family evaluated here)."),
    })
    print("[S] DONE", flush=True)


if __name__ == "__main__":
    main()
