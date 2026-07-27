"""Phase 3: the decisive with-ERL vs price-only comparison + control gates.

For each learner and each treatment (real ERL, neutral-text, shuffled-date):
  * run purged CV on the price-only design matrix and on the treatment matrix,
  * pair OOS predictions by (event_id, symbol),
  * report directional-accuracy lift with a cluster-robust block-bootstrap CI,
    and a Diebold-Mariano test on the squared-error loss differential.

The headline read is the real-ERL lift with its control gates: real must survive,
neutral and shuffled must vanish.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from aionis.eval.evaluate import cross_validate
from aionis.eval.metrics import (
    block_bootstrap,
    diebold_mariano,
    diebold_mariano_mbb,
    directional_accuracy,
)
from aionis.eval.risk_metrics import backtest_audit
from aionis.features.design_matrix import DesignMatrix


@dataclass
class LiftResult:
    treatment: str
    learner: str
    da_price: float
    da_treatment: float
    da_lift: float
    ci_lo: float
    ci_hi: float
    dm_stat: float  # on loss_treatment - loss_price (>0 => treatment worse)
    dm_p: float
    n_clusters: int
    # Multiple-testing / overfit audit (purgedcv): is the apparent edge real?
    sharpe: float = float("nan")
    dsr: float = float("nan")
    pbo: float = float("nan")
    # Moving-block-bootstrap DM p-value (small-n robustness on the analytic HLN DM).
    dm_p_mbb: float = float("nan")
    # Memorization / point-in-time audit: pre/post-LLM-cutoff lift gap (None if not run).
    pit: dict | None = None


def _per_event_date_da_lift(merged: pd.DataFrame, learner: str) -> np.ndarray:
    """Series of (treatment DA - price DA) per event-date, for block bootstrap."""
    y = merged["y_true"].to_numpy(float)
    correct_p = (np.sign(y) == np.sign(merged[f"{learner}_p"].to_numpy(float))).astype(float)
    correct_t = (np.sign(y) == np.sign(merged[f"{learner}_t"].to_numpy(float))).astype(float)
    df = pd.DataFrame({"group": merged["group"].to_numpy(), "p": correct_p, "t": correct_t})
    per = df.groupby("group").mean()
    return (per["t"] - per["p"]).to_numpy()


def compare_treatment(
    price_dm: DesignMatrix,
    treat_dm: DesignMatrix,
    learner_name: str,
    learner_fn,
    horizon: int,
    n_splits: int,
    embargo: pd.Timedelta,
    seed: int = 0,
    pit_cutoff: str | pd.Timestamp | None = None,
) -> LiftResult:
    res_p = cross_validate(
        price_dm, {learner_name: learner_fn}, n_splits=n_splits, embargo=embargo, horizon=horizon
    )
    res_t = cross_validate(
        treat_dm, {learner_name: learner_fn}, n_splits=n_splits, embargo=embargo, horizon=horizon
    )

    # Parity guard: price-only and treatment must be built from the SAME event set,
    # otherwise an asymmetric row drop (e.g. partial ERL extraction) confounds the
    # feature ablation with a training-set-size difference.
    p_keys = set(map(tuple, res_p.oos[["event_id", "symbol"]].to_numpy().tolist()))
    t_keys = set(map(tuple, res_t.oos[["event_id", "symbol"]].to_numpy().tolist()))
    if p_keys != t_keys:
        raise RuntimeError(
            "price-only and treatment OOS rows differ (asymmetric drop). Restrict "
            "events to the common set (those with cached ERLs) before building matrices."
        )

    # Explicit rename so columns are unambiguous regardless of merge suffix rules.
    left = res_p.oos.rename(columns={learner_name: f"{learner_name}_p"})
    right = res_t.oos[["event_id", "symbol", learner_name]].rename(
        columns={learner_name: f"{learner_name}_t"}
    )
    merged = left.merge(right, on=["event_id", "symbol"], validate="1:1")
    y = merged["y_true"].to_numpy(float)
    pp = merged[f"{learner_name}_p"].to_numpy(float)
    pt = merged[f"{learner_name}_t"].to_numpy(float)

    da_p = directional_accuracy(y, pp)
    da_t = directional_accuracy(y, pt)
    loss_p = (pp - y) ** 2
    loss_t = (pt - y) ** 2
    groups = merged["group"].to_numpy()
    dm = diebold_mariano(loss_t, loss_p, groups, horizon)
    dm_mbb = diebold_mariano_mbb(loss_t, loss_p, groups, horizon)

    # The headline lift AND its CI use the same clustered estimand (mean of
    # per-event-date lifts), so the bootstrap CI brackets the point estimate.
    lift_series = _per_event_date_da_lift(merged, learner_name)
    ci = block_bootstrap(lift_series, stat_fn=np.mean, block_len=max(1, horizon), seed=seed)

    # Multiple-testing / overfit audit on the treatment's OOS long/short strategy.
    n_trials = int(res_t.oos["symbol"].nunique()) if "symbol" in res_t.oos.columns else 1
    audit = backtest_audit(res_t.oos, learner_name, n_trials=max(n_trials, 1))

    # Memorization audit: if the ERL lift concentrates pre-LLM-cutoff it may be
    # parametric memorization, not signal. Only meaningful for the real ERL arm,
    # but cheap to compute for controls too (their pre/post gap should be ~0).
    pit = None
    if pit_cutoff is not None:
        from aionis.eval.pit_audit import memorization_audit

        pit = memorization_audit(res_p.oos, res_t.oos, learner_name, pit_cutoff)

    return LiftResult(
        treatment="",
        learner=learner_name,
        da_price=da_p,
        da_treatment=da_t,
        da_lift=float(np.mean(lift_series)),
        ci_lo=ci["ci_lo"],
        ci_hi=ci["ci_hi"],
        dm_stat=dm["dm_stat"],
        dm_p=dm["p_value"],
        n_clusters=dm["n_clusters"],
        sharpe=audit.get("sharpe", float("nan")),
        dsr=audit.get("dsr", float("nan")),
        pbo=audit.get("pbo", float("nan")),
        dm_p_mbb=dm_mbb["p_value"],
        pit=pit,
    )


def format_table(results: list[LiftResult]) -> str:
    rows = [
        {
            "treatment": r.treatment,
            "learner": r.learner,
            "DA_price": round(r.da_price, 4),
            "DA_treat": round(r.da_treatment, 4),
            "DA_lift": round(r.da_lift, 4),
            "CI95": f"[{r.ci_lo:+.3f},{r.ci_hi:+.3f}]",
            "DM_p": f"{r.dm_p:.3f}",
            "DMp_mbb": f"{r.dm_p_mbb:.3f}",
            "Sharpe": f"{r.sharpe:+.2f}",
            "DSR": f"{r.dsr:.3f}",
            "PBO": f"{r.pbo:.3f}",
            "n_evts": r.n_clusters,
        }
        for r in results
    ]
    return pd.DataFrame(rows).to_string(index=False)
