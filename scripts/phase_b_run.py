"""Phase B first confirmatory run (slice 5c-5f) — critic-revised.

Implements the fixes from the anti-leakage code review:
  * HIGH-1: a ``config_committed`` ledger entry is written BEFORE any result is
    observed (the durable-registry anchor is enforced, not aspirational).
  * HIGH-2: control gates (lag-shift, placebo) perturb arm_state ONLY and run
    against arm_base on the REAL fundamentals via ``run_arm_oos`` (shared folds),
    so the placebo no longer collapses both arms.
  * HIGH-3: the CV scheme (5-fold PurgedGroupKFold over the 2016+ resolvable
    window) is part of the pre-committed config; individual-arm ICs are labeled
    "CV-proxy" (not forward-OOS); the §1 differential is the OOS claim.
  * HIGH-4: ``config_sig`` covers versions + frozen params + lag_months + cv_scheme
    + membership + uv.lock sha256 (so same sig => bit-identical reruns).
  * MEDIUM-7: H6 determinism compares both the IC series AND the raw score arrays.
  * §6 multiple-testing: Harvey-Liu haircut on each arm's IC t-stat at
    n_trials in {1, 5, 20} (sensitivity); DSR/PBO/SPA wired for future use.

Per the durable-registry policy this is NOT one-shot: the config sha256 (committed
before this first result) is the anti-leakage anchor; same-config reruns are
expected + bit-identical under H6; changed-config = a new ledger row.
"""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from aionis.config import settings
from aionis.eval.learner import FROZEN_PARAMS
from aionis.eval.metrics import diebold_mariano_mbb
from aionis.eval.multiple_testing import harvey_liu_haircut
from aionis.eval.phase_b_controls import lag_shift_filed, within_month_placebo
from aionis.eval.rank_ic import rank_ic_monthly, rank_ic_summary
from aionis.eval.two_arm import compute_shared_folds, run_arm_oos
from aionis.ingest.fundamentals import _DEFAULT_END_LAG
from aionis.ingest.universe import load_pierrebrunelle_membership
from aionis.reporting import results

CACHE = settings.data_dir / "cache"
HORIZON = 21
N_SPLITS = 5
EMBARGO = 21
CV_SCHEME = ("5-fold PurgedGroupKFold (group=month, embargo=21 sessions) over the "
             "2016+ resolvable window; the explicit 2011-2016/2017-2026 split in "
             "pre-reg §8.0 is superseded because the resolvable universe is 2016+")
FEATURE_COLS = [
    "mktcap", "pb_ratio", "roa",
    "fund_assets", "fund_revenue", "fund_net_income",
    "fund_equity", "fund_shares_out", "fund_long_term_debt",
]
# Multiple-testing trial counts (sensitivity). n_trials=1 = raw (no correction);
# 5/20 = conservative estimates of exploratory attempts (the durable ledger tracks
# the true exploratory count; these bracket robustness).
N_TRIALS_GRID = (1, 5, 20)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def _versions() -> dict:
    import arch
    import lightgbm
    import purgedcv

    return {"lightgbm": lightgbm.__version__, "purgedcv": purgedcv.__version__,
            "arch": arch.__version__}


def _append(entry: dict) -> None:
    with open("runs/ledger.jsonl", "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_cached() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    fund = pd.read_parquet(CACHE / "phase_b_fundamentals.parquet")
    px = pd.read_parquet(CACHE / "phase_b_prices.parquet")
    mem = load_pierrebrunelle_membership()
    return fund, px, mem


def build_config() -> dict:
    """The complete frozen config (HIGH-4). Its sha256 is the durable anchor."""
    return {
        "feature_cols": FEATURE_COLS, "horizon": HORIZON, "n_splits": N_SPLITS,
        "embargo_sessions": EMBARGO, "cv_scheme": CV_SCHEME,
        "frozen_params": FROZEN_PARAMS, "end_lag_months": _DEFAULT_END_LAG,
        "versions": _versions(),
        "fund_sha256": _sha(CACHE / "phase_b_fundamentals.parquet"),
        "prices_sha256": _sha(CACHE / "phase_b_prices.parquet"),
        "membership_sha256": _sha(CACHE / "universe_pierrebrunelle.parquet"),
        "uv_lock_sha256": _sha(Path("uv.lock")),
    }


def commit_config(config: dict) -> str:
    """HIGH-1: write config_committed to the ledger BEFORE any result is observed."""
    sig = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    ts = _now()
    _append({"ts": ts, "event": "config_committed", "phase": "B",
             "config_sig": sig, "config": config})
    return sig


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def arm_ic(fund: pd.DataFrame, px: pd.DataFrame, mem: pd.DataFrame,
           folds, ref, align_on: str) -> tuple[pd.Series, dict, pd.DataFrame]:
    panel = run_arm_oos(px, fund, mem, HORIZON, FEATURE_COLS, align_on, folds, ref)
    ic = rank_ic_monthly(panel, "score", "y_fwd_ret")
    return ic, rank_ic_summary(ic), panel


def differential(ic_state: pd.Series, ic_base: pd.Series) -> dict:
    common = ic_state.index.intersection(ic_base.index)
    s = ic_state.loc[common].to_numpy()
    b = ic_base.loc[common].to_numpy()
    groups = np.arange(len(common))  # one cluster per month
    dm = diebold_mariano_mbb(-s, -b, groups, horizon=1)
    return {
        "n_months": int(len(common)),
        "mean_ic_diff_state_minus_base": float((s - b).mean()),
        "dm_stat": dm["stat"], "dm_p_mbb": dm["p_value"],
    }


def haircut_table(summary: dict) -> dict:
    """Harvey-Liu haircut on the arm's IC t-stat (mean_ic/se_hac as the 'Sharpe')
    across the n_trials grid. haircut_sharpe <= 0 means it fails to survive the
    multiple-testing correction at that trial count."""
    se = summary.get("se_hac") or 1e-12
    sharpe = float(summary["mean_ic"]) / float(se)
    n_obs = int(summary.get("n", 0))
    out = {}
    for nt in N_TRIALS_GRID:
        h = harvey_liu_haircut(sharpe, nt, n_obs)
        if h.get("p_raw_underflow"):
            # p_raw flushed to 0.0 (audit P1-1): the survival is real but the
            # haircut magnitude is not computable — propagate None + the flag,
            # never ±Infinity, and never crash on float(None).
            out[nt] = {"haircut_sharpe": None,
                       "survives": bool(h["survives_bonferroni"]),
                       "p_raw_underflow": True}
        else:
            out[nt] = {"haircut_sharpe": h["haircut_sharpe"], "survives": h["survives_bonferroni"]}
    return out


def main() -> None:
    fund, px, mem = load_cached()
    print(f"[5c] fund rows={len(fund)}  prices={px.shape}  membership={mem.shape}",
          flush=True)

    import os

    artifacts_only = os.environ.get("PHASE_B_NO_LEDGER") == "1"

    config = build_config()
    if artifacts_only:
        sig = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
        print(f"[B] ARTIFACTS-ONLY rerun (no ledger write); sig={sig}", flush=True)
        # sig-match guard: the rerun MUST be bit-identical (H6) to the frozen ledger
        # row before any metric is observed / any artifact is written.
        FROZEN = "17245a75d2d4cd17c68f36a9d0f4b4f7f3baf1db31b33b87be79e6e4a11400da"
        if sig != FROZEN:
            raise SystemExit(
                f"[B] ABORT: rerun sig {sig} != frozen ledger sig {FROZEN} — "
                "fund/prices/membership bytes, uv.lock, or lib versions drifted. "
                "Do NOT write artifacts or a ledger row."
            )
        print(f"[B] sig matches frozen ledger sig ({sig}); proceeding artifacts-only",
              flush=True)
    else:
        sig = commit_config(config)  # HIGH-1: BEFORE any result
        print(f"[5c] config_committed sig={sig}  (logged BEFORE result)", flush=True)

    folds, ref = compute_shared_folds(px, mem, HORIZON, N_SPLITS, EMBARGO)
    print(f"[5c] shared folds={len(folds)}  ref rows={len(ref)}", flush=True)

    # --- headline (CV-proxy individual-arm ICs; the differential is the OOS claim) ---
    ic_s, sum_s, pan_s = arm_ic(fund, px, mem, folds, ref, "filed")
    ic_b, sum_b, pan_b = arm_ic(fund, px, mem, folds, ref, "end_lag")
    print(f"[5c] arm_state(CV-proxy) mean_IC={sum_s['mean_ic']:.4f} "
          f"ci_half={sum_s['ci_half']:.4f} t_hac={sum_s['t_hac']:.3f}", flush=True)
    print(f"[5c] arm_base (CV-proxy) mean_IC={sum_b['mean_ic']:.4f} "
          f"ci_half={sum_b['ci_half']:.4f} t_hac={sum_b['t_hac']:.3f}", flush=True)

    diff = differential(ic_s, ic_b)
    print(f"[5f] differential state-base: mean={diff['mean_ic_diff_state_minus_base']:.4f} "
          f"DM p_mbb={diff['dm_p_mbb']:.4f}  n_months={diff['n_months']}", flush=True)

    # --- H6 determinism (MEDIUM-7: IC series AND raw scores) ---
    ic_s2, _, pan_s2 = arm_ic(fund, px, mem, folds, ref, "filed")
    ic_b2, _, pan_b2 = arm_ic(fund, px, mem, folds, ref, "end_lag")
    det_ok = bool(
        np.array_equal(ic_s.to_numpy(), ic_s2.to_numpy())
        and np.array_equal(ic_b.to_numpy(), ic_b2.to_numpy())
        and _scores_equal(pan_s, pan_s2) and _scores_equal(pan_b, pan_b2)
    )
    print(f"[5d] H6 deterministic (IC + raw scores) = {det_ok}", flush=True)

    # --- controls (HIGH-2: state perturbed, base REAL, shared folds) ---
    ctrl = {}
    for name, fn in (("lag_shift", lag_shift_filed), ("placebo", within_month_placebo)):
        cstate_ic, _, _ = arm_ic(fn(fund), px, mem, folds, ref, "filed")
        cdiff = differential(cstate_ic, ic_b)  # perturbed-state vs REAL-base
        ctrl[name] = cdiff
        print(f"[5e] control {name}: mean(state_perturbed - base_real)="
              f"{cdiff['mean_ic_diff_state_minus_base']:.4f} DM p_mbb={cdiff['dm_p_mbb']:.4f}",
              flush=True)

    # --- §6 multiple-testing (haircut sensitivity on each arm's IC t-stat) ---
    mt = {"arm_state": haircut_table(sum_s), "arm_base": haircut_table(sum_b)}

    # --- persist run artifacts for the dashboard (results.save_run) ---
    run_path = results.save_run(
        sig, ic_state=ic_s, ic_base=ic_b,
        summary_state=sum_s, summary_base=sum_b,
        differential=diff, controls=ctrl, config=config,
        h6_deterministic=det_ok,
        oos_state=pan_s, oos_base=pan_b,
    )
    print(f"[5f] saved run artifacts -> {run_path}", flush=True)

    # --- log result (the confirmatory:first entry, AFTER config_committed) ---
    if not artifacts_only:
        _append({
            "ts": _now(), "event": "confirmatory:first", "phase": "B", "config_sig": sig,
            "arm_state_cvproxy": sum_s, "arm_base_cvproxy": sum_b,
            "differential_state_minus_base": diff, "H6_deterministic": det_ok,
            "controls_state_perturbed_vs_base_real": ctrl,
            "multiple_testing_haircut": mt,
            "n_trials_grid": list(N_TRIALS_GRID),
            "notes": ("Individual-arm ICs are CV-proxy (5-fold, not forward-OOS) so their "
                      "publishability gates are optimistic; the §1 DIFFERENTIAL is the OOS "
                      "claim and is valid under shared-fold CV. Controls perturb arm_state "
                      "only (arm_base real). DSR/PBO/SPA wired in eval.multiple_testing for "
                      "future strategy-return evaluation."),
        })
        print(f"[5f] logged confirmatory:first (config_sig={sig})", flush=True)
    else:
        print("[5f] ARTIFACTS-ONLY: skipped confirmatory:first ledger append", flush=True)
    print("[5f] DONE", flush=True)


def _scores_equal(a: pd.DataFrame, b: pd.DataFrame) -> bool:
    """Compare the raw score arrays (aligned by date, ticker)."""
    sa = a.set_index(["date", "ticker"])["score"].sort_index()
    sb = b.set_index(["date", "ticker"])["score"].sort_index()
    if not sa.index.equals(sb.index):
        return False
    return np.array_equal(sa.to_numpy(), sb.to_numpy())


if __name__ == "__main__":
    main()
