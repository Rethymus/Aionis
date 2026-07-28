"""Phase D confirmatory run — WRL.Relationship bundle vs fundamentals-only.

Mirrors :mod:`aionis.eval.phase_c`'s anti-leakage discipline with the arm axis =
the relationship feature set: ``arm_base`` (Phase B/C fundamentals-only baseline,
``align_on="end_lag"``) vs ``arm_rel`` (``arm_base`` + the {peer_mom,
stakes_13d_event} relationship bundle). Both arms share prices / universe / folds
/ learner / fundamental timing, so the rank-IC differential isolates the
relationship bundle (phase-d-preregistration §1).

The relationship bundle is per-(ticker, date) (peer momentum + the 13D event
indicator), so it enters via the ``extra_features`` path (a left join on the
panel's existing rows -> columns only -> the shared-fold layout assertion holds).
Both bundle columns are CHANGE / EVENT features (not levels), per the framework's
"take the surprise, drop the level" discipline.

Anti-leakage anchors (same as Phase B/C): HIGH-1 ``config_committed`` BEFORE any
result; HIGH-2 the bundle-shuffle placebo perturbs ``arm_rel`` ONLY; HIGH-3 CV
scheme in the pre-committed config; HIGH-4 ``config_sig`` covers versions +
frozen params + bundle column names + input shas; H6 on IC + raw scores.
Shared helpers (differential, haircut, ledger) are reused from
:mod:`aionis.eval.phase_c`.
"""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from aionis.eval.metrics import diebold_mariano_mbb
from aionis.eval.phase_c import (
    N_TRIALS_GRID,
    PUBLISH_CI_HALF,
    _frozen_params,
    _scores_equal,
    append_ledger,
)
from aionis.eval.rank_ic import rank_ic_monthly, rank_ic_summary
from aionis.eval.two_arm import compute_shared_folds, run_arm_oos

HORIZON = 21
N_SPLITS = 5
EMBARGO = 21
FEATURE_COLS = [
    "mktcap", "pb_ratio", "roa",
    "fund_assets", "fund_revenue", "fund_net_income",
    "fund_equity", "fund_shares_out", "fund_long_term_debt",
]
# the confirmatory relationship bundle (per-(ticker,date); all change/event)
REL_COLS = ["peer_mom", "stakes_13d_event"]


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _sha(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def _versions() -> dict:
    import arch
    import lightgbm
    import purgedcv

    return {"lightgbm": lightgbm.__version__, "purgedcv": purgedcv.__version__,
            "arch": arch.__version__}


# --- bundle-shuffle placebo (perturb arm_rel ONLY) --------------------------


def shuffle_rel_extra(extra: pd.DataFrame, seed: int = 0) -> pd.DataFrame:
    """Permute every value column across tickers WITHIN each date (NaN-preserving).

    The relationship bundle's alignment is "which company's peer-momentum / 13D
    event lands on which (ticker, date)". Scrambling the value->ticker mapping at
    a fixed date preserves the date (so each value stays at a date it was
    knowable) and the NaN structure, but destroys the company->value link ->
    bundle-shuffle placebo (phase-d-preregistration §5 #2)."""
    rng = np.random.default_rng(seed)
    out = extra.copy()
    val_cols = [c for c in out.columns if c not in ("date", "ticker")]
    for _d, grp in out.groupby("date", sort=False):
        idx = grp.index.to_numpy()
        for col in val_cols:
            vals = out.loc[idx, col].to_numpy(dtype=float).copy()  # writable copy
            mask = ~np.isnan(vals)
            if int(mask.sum()) > 1:
                picked = vals[mask].copy()
                rng.shuffle(picked)
                vals[mask] = picked
                out.loc[idx, col] = vals
    return out


# --- config + ledger anchor --------------------------------------------------


def build_config(shas: dict, rel_meta: dict) -> dict:
    """The complete frozen config (HIGH-4). Its sha256 is the durable anchor."""
    cfg = {
        "phase": "D",
        "feature_cols": FEATURE_COLS,
        "rel_cols": REL_COLS,
        "horizon": HORIZON,
        "n_splits": N_SPLITS,
        "embargo_sessions": EMBARGO,
        "frozen_params": _frozen_params(),
        "publish_ci_half": PUBLISH_CI_HALF,
        "multiple_testing_family_n": 3,
        "n_trials_grid": list(N_TRIALS_GRID),
        "versions": _versions(),
    }
    cfg.update(shas)
    cfg.update(rel_meta)
    return cfg


def commit_config(config: dict, ledger_path: str | Path) -> str:
    """HIGH-1: write ``config_committed`` to the ledger BEFORE any result."""
    sig = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    append_ledger(
        {"ts": _now(), "event": "config_committed", "phase": "D",
         "config_sig": sig, "config": config},
        ledger_path,
    )
    return sig


def differential(ic_a: pd.Series, ic_b: pd.Series) -> dict:
    """rank-IC differential ``ic_a - ic_b`` with HAC CI + MBB-DM (pre-reg §1/§7)."""
    common = ic_a.index.intersection(ic_b.index)
    s = ic_a.loc[common].to_numpy(dtype=float)
    b = ic_b.loc[common].to_numpy(dtype=float)
    diff = pd.Series(s - b, index=common, name="ic_diff")
    summ = rank_ic_summary(diff)
    groups = np.arange(len(common))
    dm = diebold_mariano_mbb(-s, -b, groups, horizon=1)
    mean_diff = float(summ["mean_ic"])
    ci_half = float(summ["ci_half"])
    return {
        "n_months": int(len(common)),
        "mean_diff": mean_diff,
        "se_hac": float(summ["se_hac"]),
        "ci_half": ci_half,
        "ci_lo": mean_diff - ci_half,
        "ci_hi": mean_diff + ci_half,
        "dm_stat": dm["stat"],
        "dm_p_mbb": dm["p_value"],
        "dm_flag": dm["flag"],
        "publishable_ci_half": bool(ci_half < PUBLISH_CI_HALF),
    }


# --- the orchestrator (pure compute on injected data + rel bundle) -----------


def _arm_ic(fund, px, mem, folds, ref, feature_cols, params, *, horizon, extra=None):
    panel = run_arm_oos(
        px, fund, mem, horizon, feature_cols, "end_lag", folds, ref, params,
        extra_features=extra,
    )
    ic = rank_ic_monthly(panel, "score", "y_fwd_ret")
    return ic, rank_ic_summary(ic), panel


def run_confirmatory(
    fund: pd.DataFrame, px: pd.DataFrame, mem: pd.DataFrame,
    *, rel_extra: pd.DataFrame, config: dict, sig: str,
    feature_cols: list[str] | None = None, rel_cols: list[str] | None = None,
    horizon: int = HORIZON, n_splits: int = N_SPLITS, embargo: int = EMBARGO,
    params: dict | None = None,
    ledger_path: str | Path | None = None, results_base: str | Path | None = None,
) -> dict:
    """Run the full Phase D confirmatory pipeline on injected data + rel bundle.

    No network -- the rel bundle (peer_mom + stakes_13d_event) is pre-built by the
    caller (the script's build step; synthetic in the hermetic test). Order: shared
    folds -> arm_base + arm_rel -> differential -> H6 re-run -> bundle-shuffle
    placebo + leave-one-out -> save_run -> (confirmatory:first ledger row if
    ``ledger_path``, AFTER ``config_committed``)."""
    from aionis.reporting import results

    feature_cols = FEATURE_COLS if feature_cols is None else feature_cols
    rel_cols = REL_COLS if rel_cols is None else rel_cols
    params = _frozen_params() if params is None else params

    folds, ref = compute_shared_folds(px, mem, horizon, n_splits, embargo)

    # --- headline (CV-proxy individual-arm ICs; the differential is the OOS claim)
    ic_b, sum_b, pan_b = _arm_ic(fund, px, mem, folds, ref, feature_cols, params, horizon=horizon)
    ic_r, sum_r, pan_r = _arm_ic(
        fund, px, mem, folds, ref, feature_cols + rel_cols, params,
        horizon=horizon, extra=rel_extra,
    )
    diff = differential(ic_r, ic_b)

    # --- H6 determinism (IC series AND raw scores, both arms)
    ic_b2, _, pan_b2 = _arm_ic(fund, px, mem, folds, ref, feature_cols, params, horizon=horizon)
    ic_r2, _, pan_r2 = _arm_ic(
        fund, px, mem, folds, ref, feature_cols + rel_cols, params,
        horizon=horizon, extra=rel_extra,
    )
    h6 = bool(
        np.array_equal(ic_r.to_numpy(), ic_r2.to_numpy())
        and np.array_equal(ic_b.to_numpy(), ic_b2.to_numpy())
        and _scores_equal(pan_r, pan_r2) and _scores_equal(pan_b, pan_b2)
    )

    # --- controls (HIGH-2: arm_rel perturbed, arm_base REAL, shared folds)
    ic_p, _, _ = _arm_ic(
        fund, px, mem, folds, ref, feature_cols + rel_cols, params,
        horizon=horizon, extra=shuffle_rel_extra(rel_extra),
    )
    placebo = differential(ic_p, ic_b)

    # --- leave-one-out attribution (exploratory, NOT a gate; pre-reg §5 #5)
    loo: dict[str, dict] = {}
    for drop in rel_cols:
        keep_cols = [c for c in feature_cols + rel_cols if c != drop]
        keep_extra = rel_extra.drop(columns=[drop]) if drop in rel_extra.columns else rel_extra
        ic_l, _, _ = _arm_ic(
            fund, px, mem, folds, ref, keep_cols, params, horizon=horizon, extra=keep_extra,
        )
        loo[drop] = differential(ic_l, ic_b)

    controls = {"bundle_shuffle_placebo": placebo, "leave_one_out": loo}

    if results_base is not None:
        results.save_run(
            sig, ic_state=ic_r, ic_base=ic_b, summary_state=sum_r, summary_base=sum_b,
            differential=diff, controls=controls, config=config,
            h6_deterministic=h6, base=results_base,
        )

    result = {
        "config_sig": sig,
        "arm_rel_cvproxy": sum_r,
        "arm_base_cvproxy": sum_b,
        "differential_rel_minus_base": diff,
        "H6_deterministic": h6,
        "controls": controls,
        "n_trials_grid": list(N_TRIALS_GRID),
        "notes": (
            "Individual-arm ICs are CV-proxy (5-fold); the §1 DIFFERENTIAL is the "
            "OOS claim. Controls perturb arm_rel only (arm_base real, shared folds). "
            "Bundle-shuffle placebo scrambles the rel bundle's value->ticker "
            "alignment; leave-one-out is exploratory attribution (NOT a gate). "
            "ic_state=arm_rel, ic_base=arm_base in the saved artifacts."
        ),
    }
    if ledger_path is not None:
        append_ledger(
            {"ts": _now(), "event": "confirmatory:first", "phase": "D", **result},
            ledger_path,
        )
    return result
