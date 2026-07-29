"""Phase E1 confirmatory run — structural shock propagation along the SIC graph.

The WRL simulation/propagation layer's ZERO-LEAKAGE baseline (phase-e-
preregistration §2). ``arm_base_self`` = fundamentals + the firm's OWN shocks
(self earnings surprise + self 13D event); ``arm_prop`` = ``arm_base_self`` + the
SAME shocks PROPAGATED across same-SIC peers (ex-self, via
:func:`aionis.features.propagation.propagate_panel`). The differential isolates
whether peers' propagated shocks carry cross-sectional signal beyond the firm's
own — the "does information propagate across the relationship graph" question.

Pure structural propagation: deterministic rules on PIT data (earnings-surprise
via filed-date, 13D-event via filing_date, SIC edges), no LLM, no learned model —
the leakage-free baseline of the Phase E sequence (E2 adds LLM macro-causal with
cutoff control; E3 forward-live).

Anti-leakage anchors mirror Phase B/C/D: HIGH-1 ``config_committed`` BEFORE result;
HIGH-2 the bundle-shuffle placebo perturbs the PROPAGATED columns only
(``arm_base_self`` real); H6 on IC + raw scores. Shared helpers reused from
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
# the firm's OWN shocks (already-tested in Phase C/D, here the propagation baseline)
SELF_COLS = ["self_earnings_surprise", "self_13d_event"]
# the SAME shocks propagated across same-SIC peers (ex-self) — the E1 claim
PROP_COLS = ["peer_earnings_surprise", "peer_13d_event"]


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _versions() -> dict:
    import arch
    import lightgbm
    import purgedcv

    return {"lightgbm": lightgbm.__version__, "purgedcv": purgedcv.__version__,
            "arch": arch.__version__}


def _merge_extra(self_extra: pd.DataFrame, prop_extra: pd.DataFrame) -> pd.DataFrame:
    """Outer-merge the self + propagated long frames on (date, ticker)."""
    return self_extra.merge(prop_extra, on=["date", "ticker"], how="outer")


def shuffle_prop_extra(prop_extra: pd.DataFrame, seed: int = 0) -> pd.DataFrame:
    """Bundle-shuffle placebo: permute each PROPAGATED value column across tickers
    WITHIN each date (NaN-preserving). Breaks the propagation alignment (which
    peer's shock lands on which firm) while keeping the date + NaN structure."""
    rng = np.random.default_rng(seed)
    out = prop_extra.copy()
    val_cols = [c for c in out.columns if c not in ("date", "ticker")]
    for _d, grp in out.groupby("date", sort=False):
        idx = grp.index.to_numpy()
        for col in val_cols:
            vals = out.loc[idx, col].to_numpy(dtype=float).copy()
            mask = ~np.isnan(vals)
            if int(mask.sum()) > 1:
                picked = vals[mask].copy()
                rng.shuffle(picked)
                vals[mask] = picked
                out.loc[idx, col] = vals
    return out


def build_config(shas: dict, e1_meta: dict) -> dict:
    cfg = {
        "phase": "E1",
        "feature_cols": FEATURE_COLS,
        "self_cols": SELF_COLS,
        "prop_cols": PROP_COLS,
        "horizon": HORIZON,
        "n_splits": N_SPLITS,
        "embargo_sessions": EMBARGO,
        "frozen_params": _frozen_params(),
        "publish_ci_half": PUBLISH_CI_HALF,
        "multiple_testing_family_n": 4,
        "n_trials_grid": list(N_TRIALS_GRID),
        "versions": _versions(),
    }
    cfg.update(shas)
    cfg.update(e1_meta)
    return cfg


def commit_config(config: dict, ledger_path: str | Path) -> str:
    sig = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    append_ledger(
        {"ts": _now(), "event": "config_committed", "phase": "E1",
         "config_sig": sig, "config": config},
        ledger_path,
    )
    return sig


def differential(ic_a: pd.Series, ic_b: pd.Series) -> dict:
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


def _arm_ic(fund, px, mem, folds, ref, feature_cols, params, *, horizon, extra=None):
    panel = run_arm_oos(
        px, fund, mem, horizon, feature_cols, "end_lag", folds, ref, params,
        extra_features=extra,
    )
    ic = rank_ic_monthly(panel, "score", "y_fwd_ret")
    return ic, rank_ic_summary(ic), panel


def run_confirmatory(
    fund: pd.DataFrame, px: pd.DataFrame, mem: pd.DataFrame,
    *, self_extra: pd.DataFrame, prop_extra: pd.DataFrame,
    config: dict, sig: str,
    feature_cols: list[str] | None = None, self_cols: list[str] | None = None,
    prop_cols: list[str] | None = None,
    horizon: int = HORIZON, n_splits: int = N_SPLITS, embargo: int = EMBARGO,
    params: dict | None = None,
    ledger_path: str | Path | None = None, results_base: str | Path | None = None,
) -> dict:
    """Phase E1 pipeline on injected data + self/prop shock frames.

    arm_base_self (fundamentals + OWN shocks) vs arm_prop (+ propagated peer
    shocks). The differential isolates propagation beyond self. No network."""
    from aionis.reporting import results

    feature_cols = FEATURE_COLS if feature_cols is None else feature_cols
    self_cols = SELF_COLS if self_cols is None else self_cols
    prop_cols = PROP_COLS if prop_cols is None else prop_cols
    params = _frozen_params() if params is None else params
    full_extra = _merge_extra(self_extra, prop_extra)

    folds, ref = compute_shared_folds(px, mem, horizon, n_splits, embargo)

    # --- headline
    ic_bs, sum_bs, pan_bs = _arm_ic(
        fund, px, mem, folds, ref, feature_cols + self_cols, params,
        horizon=horizon, extra=self_extra,
    )
    ic_p, sum_p, pan_p = _arm_ic(
        fund, px, mem, folds, ref, feature_cols + self_cols + prop_cols, params,
        horizon=horizon, extra=full_extra,
    )
    diff = differential(ic_p, ic_bs)

    # --- H6
    ic_bs2, _, pan_bs2 = _arm_ic(
        fund, px, mem, folds, ref, feature_cols + self_cols, params,
        horizon=horizon, extra=self_extra,
    )
    ic_p2, _, pan_p2 = _arm_ic(
        fund, px, mem, folds, ref, feature_cols + self_cols + prop_cols, params,
        horizon=horizon, extra=full_extra,
    )
    h6 = bool(
        np.array_equal(ic_p.to_numpy(), ic_p2.to_numpy())
        and np.array_equal(ic_bs.to_numpy(), ic_bs2.to_numpy())
        and _scores_equal(pan_p, pan_p2) and _scores_equal(pan_bs, pan_bs2)
    )

    # --- controls: bundle-shuffle placebo (prop cols shuffled; base_self REAL)
    placebo_extra = _merge_extra(self_extra, shuffle_prop_extra(prop_extra))
    ic_pl, _, _ = _arm_ic(
        fund, px, mem, folds, ref, feature_cols + self_cols + prop_cols, params,
        horizon=horizon, extra=placebo_extra,
    )
    placebo = differential(ic_pl, ic_bs)

    # --- leave-one-out (drop each prop col)
    loo: dict[str, dict] = {}
    for drop in prop_cols:
        keep_prop = prop_extra.drop(columns=[drop]) if drop in prop_extra.columns else prop_extra
        keep_cols = [c for c in feature_cols + self_cols + prop_cols if c != drop]
        keep_full = _merge_extra(self_extra, keep_prop)
        ic_l, _, _ = _arm_ic(
            fund, px, mem, folds, ref, keep_cols, params, horizon=horizon, extra=keep_full,
        )
        loo[drop] = differential(ic_l, ic_bs)

    controls = {"bundle_shuffle_placebo": placebo, "leave_one_out": loo}
    # save_run artifacts (base=None -> the default project runs dir; an explicit
    # base hermetically redirects for tests).
    results.save_run(
        sig, ic_state=ic_p, ic_base=ic_bs, summary_state=sum_p, summary_base=sum_bs,
        differential=diff, controls=controls, config=config,
        h6_deterministic=h6, base=results_base,
    )

    result = {
        "config_sig": sig,
        "arm_prop_cvproxy": sum_p,
        "arm_base_self_cvproxy": sum_bs,
        "differential_prop_minus_base_self": diff,
        "H6_deterministic": h6,
        "controls": controls,
        "n_trials_grid": list(N_TRIALS_GRID),
        "notes": (
            "Phase E1 zero-leakage structural propagation. arm_base_self = "
            "fundamentals + OWN shocks; arm_prop = + SAME shocks propagated across "
            "same-SIC peers (ex-self). The differential isolates propagation beyond "
            "self. Placebo shuffles the propagated columns only (base_self real). "
            "ic_state=arm_prop, ic_base=arm_base_self in the saved artifacts."
        ),
    }
    if ledger_path is not None:
        append_ledger(
            {"ts": _now(), "event": "confirmatory:first", "phase": "E1", **result},
            ledger_path,
        )
    return result
