"""Point-in-time memorization audit: does the ERL lift survive the LLM cutoff?

The extraction LLM may have memorized post-event market outcomes for events
inside its training window (parametric leakage / "functional lookahead bias",
Lopez-Lira et al. 2025). The structural-only ERL schema makes this unlikely to
carry outcome information, but the claim must be audited: if the ERL lift is
memorization, it should concentrate on events BEFORE the LLM's training-data
cutoff and vanish AFTER.

The audit mirrors the estimand in ``compare.py`` exactly — same
(event_id, symbol) pairing with the same parity guard, same event-date
clustering via the ``group`` column — then splits the per-event-date lift
series at the cutoff and bootstraps the pre-minus-post gap (iid over cluster
labels within each era, resampled independently).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import structlog

log = structlog.get_logger()

# Below this many event-date clusters in either era the gap CI is meaningless.
MIN_CLUSTERS_PER_SPLIT = 5


def memorization_audit(
    oos_price: pd.DataFrame,
    oos_treat: pd.DataFrame,
    model: str,
    cutoff: str | pd.Timestamp,
    n_boot: int = 2000,
    seed: int = 7,
) -> dict:
    """Pre/post-cutoff directional-accuracy lift gap with a bootstrap CI.

    ``oos_price`` and ``oos_treat`` are OOS prediction frames as produced by
    ``evaluate.cross_validate`` (columns ``event_id, symbol, y_true, group,
    <model>``). Per-row hits follow ``metrics.directional_accuracy`` (a zero
    true return is never a hit); per-row lift is hit_treat - hit_price,
    averaged within each event-date cluster.

    Returns a dict::

        {"pre":  {"lift": float, "n_clusters": int},
         "post": {"lift": float, "n_clusters": int},
         "gap": float,            # pre lift - post lift
         "gap_ci": (lo, hi),      # 95% percentile bootstrap CI on the gap
         "n_boot": int,
         "interpretation": "memorization-consistent" | "no-memorization-signal"
                           | "post-stronger" | "underpowered"}

    A gap CI entirely > 0 (pre-era lift significantly larger) is the
    memorization-consistent pattern. Either era with fewer than
    ``MIN_CLUSTERS_PER_SPLIT`` clusters yields ``gap_ci = (nan, nan)`` and
    ``"underpowered"`` instead of an exception.

    Note: this percentile CI is an EXPLORATORY diagnostic, not the headline
    significance test. The headline is the cluster-robust Diebold-Mariano in
    ``compare.py`` (analytic HLN + moving-block-bootstrap). At small per-era n
    the unstudentized percentile interval can undercover; treat its
    interpretation as suggestive, not decisive.
    """
    merged = _pair_arms(oos_price, oos_treat, model)
    per_cluster = _per_cluster_lift(merged, model)

    dates = pd.DatetimeIndex(pd.to_datetime(per_cluster.index))
    if dates.tz is not None:
        dates = dates.tz_localize(None)
    cutoff_ts = pd.Timestamp(cutoff)
    if cutoff_ts.tzinfo is not None:
        cutoff_ts = cutoff_ts.tz_localize(None)

    lifts = per_cluster.to_numpy(float)
    pre = lifts[dates < cutoff_ts]
    post = lifts[dates >= cutoff_ts]
    pre_lift = float(np.mean(pre)) if len(pre) else float("nan")
    post_lift = float(np.mean(post)) if len(post) else float("nan")

    out = {
        "pre": {"lift": pre_lift, "n_clusters": int(len(pre))},
        "post": {"lift": post_lift, "n_clusters": int(len(post))},
        "gap": float(pre_lift - post_lift),
        "n_boot": int(n_boot),
    }

    if len(pre) < MIN_CLUSTERS_PER_SPLIT or len(post) < MIN_CLUSTERS_PER_SPLIT:
        log.warning(
            "pit_audit_underpowered",
            n_pre=int(len(pre)),
            n_post=int(len(post)),
            min_required=MIN_CLUSTERS_PER_SPLIT,
        )
        return {**out, "gap_ci": (float("nan"), float("nan")), "interpretation": "underpowered"}

    ci_lo, ci_hi = _bootstrap_gap_ci(pre, post, n_boot=n_boot, seed=seed)
    return {**out, "gap_ci": (ci_lo, ci_hi), "interpretation": _interpret(ci_lo, ci_hi)}


def _pair_arms(oos_price: pd.DataFrame, oos_treat: pd.DataFrame, model: str) -> pd.DataFrame:
    """Pair the two arms 1:1 on (event_id, symbol) — same discipline as compare.py."""
    required_price = {"event_id", "symbol", "y_true", "group", model}
    required_treat = {"event_id", "symbol", model}
    missing_p = required_price - set(oos_price.columns)
    missing_t = required_treat - set(oos_treat.columns)
    if missing_p or missing_t:
        raise ValueError(
            f"oos frames missing required columns: price={sorted(missing_p)}, "
            f"treat={sorted(missing_t)}"
        )

    p_keys = set(map(tuple, oos_price[["event_id", "symbol"]].to_numpy().tolist()))
    t_keys = set(map(tuple, oos_treat[["event_id", "symbol"]].to_numpy().tolist()))
    if p_keys != t_keys:
        raise RuntimeError(
            "price-only and treatment OOS rows differ (asymmetric drop); the audit "
            "requires the same (event_id, symbol) set in both arms."
        )

    left = oos_price.rename(columns={model: f"{model}_p"})
    right = oos_treat[["event_id", "symbol", model]].rename(columns={model: f"{model}_t"})
    return left.merge(right, on=["event_id", "symbol"], validate="1:1")


def _per_cluster_lift(merged: pd.DataFrame, model: str) -> pd.Series:
    """Mean per-row lift (hit_treat - hit_price) within each event-date cluster.

    A hit follows ``metrics.directional_accuracy``: sign agreement AND a
    nonzero true return (a zero return has no direction, so neither arm scores).
    """
    sy = np.sign(merged["y_true"].to_numpy(float))
    hit_p = ((sy == np.sign(merged[f"{model}_p"].to_numpy(float))) & (sy != 0)).astype(float)
    hit_t = ((sy == np.sign(merged[f"{model}_t"].to_numpy(float))) & (sy != 0)).astype(float)
    df = pd.DataFrame({"group": merged["group"].to_numpy(), "lift": hit_t - hit_p})
    return df.groupby("group")["lift"].mean()


def _bootstrap_gap_ci(
    pre: np.ndarray, post: np.ndarray, n_boot: int, seed: int
) -> tuple[float, float]:
    """95% percentile CI for mean(pre) - mean(post), iid bootstrap per era."""
    rng = np.random.default_rng(seed)
    idx_pre = rng.integers(0, len(pre), size=(n_boot, len(pre)))
    idx_post = rng.integers(0, len(post), size=(n_boot, len(post)))
    gaps = pre[idx_pre].mean(axis=1) - post[idx_post].mean(axis=1)
    lo, hi = np.percentile(gaps, [2.5, 97.5])
    return float(lo), float(hi)


def _interpret(ci_lo: float, ci_hi: float) -> str:
    if ci_lo > 0:
        return "memorization-consistent"
    if ci_hi < 0:
        return "post-stronger"
    return "no-memorization-signal"
