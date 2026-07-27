"""Evaluation metrics: directional accuracy, naive baselines, Diebold-Mariano.

All inference is cluster-robust: loss differentials are first averaged within
each event-date (one event hits all sectors the same day, so rows are not
independent), then a Newey-West HAC variance with the Harvey-Leybourne-Newbold
small-sample correction is applied. CIs come from a moving-block bootstrap
(block length >= horizon) on the per-event-date series.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# --- point metrics -----------------------------------------------------------


def directional_accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.sign(np.asarray(y_true, float))
    y_pred = np.sign(np.asarray(y_pred, float))
    # A zero true return has no direction; only count agreements where y_true != 0.
    correct = (y_true == y_pred) & (y_true != 0)
    return float(np.mean(correct))


def up_baseline(y_true: np.ndarray) -> float:
    """Accuracy of the trivial 'always predict up' rule — the real null for DA."""
    return float(np.mean(np.asarray(y_true, float) > 0))


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    a = np.asarray(y_true, float) - np.asarray(y_pred, float)
    return float(np.mean(np.abs(a)))


def mse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    a = np.asarray(y_true, float) - np.asarray(y_pred, float)
    return float(np.mean(a * a))


# --- inference ---------------------------------------------------------------


def _nw_se(x: np.ndarray, max_lag: int) -> float:
    """Newey-West HAC standard error of the sample mean of x."""
    x = np.asarray(x, float)
    n = len(x)
    if n < 2:
        return float("nan")
    xc = x - x.mean()
    gamma0 = float(np.dot(xc, xc) / n)
    omega2 = gamma0
    for lag in range(1, max_lag + 1):
        w = 1.0 - lag / (max_lag + 1)
        gamma_l = float(np.dot(xc[:-lag], xc[lag:]) / n)
        omega2 += 2.0 * w * gamma_l
    omega2 = max(omega2, 1e-300)
    return float(np.sqrt(omega2 / n))


def diebold_mariano(
    loss_a: np.ndarray,
    loss_b: np.ndarray,
    groups: np.ndarray,
    horizon: int,
) -> dict:
    """Two-sided Diebold-Mariano on loss_a - loss_b, cluster-robust by event-date.

    Positive DM (positive mean differential) means loss_a > loss_b, i.e. model b
    is better. Convention here: we report the differential as loss_a - loss_b and
    its standardized statistic; callers interpret sign per their loss choice.
    """
    d = pd.Series(np.asarray(loss_a, float) - np.asarray(loss_b, float))
    g = pd.Series(groups)
    dg = d.groupby(g).mean().sort_index().to_numpy()
    n = len(dg)
    mean_d = float(dg.mean())
    max_lag = max(0, horizon - 1)
    se = _nw_se(dg, max_lag)
    if not np.isfinite(se) or se == 0:
        return {
            "dm_stat": float("nan"),
            "p_value": float("nan"),
            "mean_diff": mean_d,
            "n_clusters": n,
            "se": se,
        }
    dm = mean_d / se
    # Harvey-Leybourne-Newbold (HLN) small-sample correction. The h(h-1) term
    # is divided by n (canonical form); the whole factor is then /n, so:
    #   sqrt((n + 1 - 2h + h(h-1)/n) / n).
    hln_factor = np.sqrt((n + 1 - 2 * horizon + horizon * (horizon - 1) / n) / n)
    dm_hln = dm * hln_factor
    # HLN's small-sample point is to compare against Student-t with n-1 df,
    # not the Normal CDF.
    from scipy.stats import t as student_t

    p = 2.0 * student_t.sf(abs(dm_hln), df=n - 1)
    return {
        "dm_stat": float(dm_hln),
        "p_value": float(p),
        "mean_diff": mean_d,
        "n_clusters": n,
        "se": se,
    }


def diebold_mariano_mbb(
    loss_a: np.ndarray,
    loss_b: np.ndarray,
    groups: np.ndarray,
    horizon: int = 1,
    n_boot: int = 2000,
    block_len: int | None = None,
    seed: int = 7,
) -> dict:
    """Moving-block-bootstrap DM p-value on the clustered loss differential.

    Complements the analytic HLN-corrected :func:`diebold_mariano` at small n
    (~tens of event-date clusters), where the Student-t reference is only
    approximate. The differential ``loss_a - loss_b`` is first averaged within
    each event-date cluster (rows on the same day are not independent), giving
    an ordered series ``d_g`` of length n.

    Under H0 (equal predictive accuracy) ``E[d_g] = 0``; we studentize for
    pivotality as ``t = mean(d_g) / (std(d_g, ddof=1) / sqrt(n))``. The
    moving-block bootstrap (Kunsch 1989) resamples the H0-centered series in
    overlapping blocks of length ``block_len`` — default
    ``max(horizon, ceil(n ** (1/3)))`` per the Politis & White (2004) rule of
    thumb — recomputes the studentized statistic per resample, and the two-sided
    p-value is the share of ``|t*| >= |t_obs|`` with the ``(count+1)/(n_boot+1)``
    finite-sample correction. A block length > 1 is what makes this robust to
    serial correlation in the clustered differential (an iid/block-1 bootstrap
    would be anti-conservative there).

    Returns ``p_value = 1.0`` with ``flag = "degenerate"`` when ``n < 4`` or the
    differential has zero/non-finite variance. Positive ``stat`` means
    ``loss_a > loss_b`` (model b is better) — same sign convention as
    :func:`diebold_mariano`.
    """
    d = pd.Series(np.asarray(loss_a, float) - np.asarray(loss_b, float))
    g = pd.Series(groups)
    dg = d.groupby(g).mean().sort_index().to_numpy()
    n = len(dg)
    if n < 4:
        return {
            "stat": float("nan"), "p_value": 1.0, "block_len": 0,
            "n_boot": int(n_boot), "n_clusters": int(n), "flag": "degenerate",
        }
    sd = float(np.std(dg, ddof=1))
    if sd == 0.0 or not np.isfinite(sd):
        return {
            "stat": float("nan"), "p_value": 1.0, "block_len": 0,
            "n_boot": int(n_boot), "n_clusters": int(n), "flag": "degenerate",
        }
    bl = block_len if block_len is not None else max(horizon, int(np.ceil(n ** (1.0 / 3.0))))
    bl = max(1, min(bl, n))
    mean_d = float(np.mean(dg))
    t_obs = mean_d / (sd / np.sqrt(n))
    dc = dg - mean_d  # H0 centering: resamples live under the equal-accuracy null.

    rng = np.random.default_rng(seed)
    starts = np.arange(n - bl + 1)
    if len(starts) <= 1:
        # block_len >= n: a single block covers the whole series, so every
        # resample is identical and t_star is identically 0 -> the bootstrap has
        # zero resampling variation and cannot calibrate a p-value. Report
        # underpowered rather than a misleading 1/(n_boot+1) ~= 0.0005 "ok".
        return {
            "stat": float(t_obs), "p_value": 1.0, "block_len": int(bl),
            "n_boot": int(n_boot), "n_clusters": int(n), "flag": "underpowered",
        }
    block_idx = starts[:, None] + np.arange(bl)[None, :]  # (n_starts, bl)
    n_blocks = int(np.ceil(n / bl))
    count = 0
    abs_t_obs = abs(t_obs)
    for _ in range(n_boot):
        s = rng.integers(0, len(starts), size=n_blocks)
        idx = block_idx[s].ravel()[:n]
        sample = dc[idx]
        ms = float(np.std(sample, ddof=1))
        if ms == 0.0 or not np.isfinite(ms):
            count += 1  # degenerate resample: count as exceeding (conservative)
            continue
        t_star = float(np.mean(sample)) / (ms / np.sqrt(n))
        if abs(t_star) >= abs_t_obs:
            count += 1
    p = (count + 1.0) / (n_boot + 1.0)
    return {
        "stat": float(t_obs), "p_value": float(p), "block_len": int(bl),
        "n_boot": int(n_boot), "n_clusters": int(n), "flag": "ok",
    }


def block_bootstrap(
    x: np.ndarray,
    stat_fn,
    n_boot: int = 2000,
    block_len: int = 1,
    seed: int = 0,
) -> dict:
    """Moving-block bootstrap CI for ``stat_fn`` over a 1-D ordered series."""
    rng = np.random.default_rng(seed)
    x = np.asarray(x, float)
    n = len(x)
    block_len = max(1, min(block_len, n))
    stats = np.empty(n_boot)
    n_blocks = int(np.ceil(n / block_len))
    starts = np.arange(n - block_len + 1) if n >= block_len else np.array([0])
    for b in range(n_boot):
        idx = []
        for _ in range(n_blocks):
            s = rng.integers(0, len(starts))
            idx.extend(range(starts[s], starts[s] + block_len))
        sample = x[np.array(idx[:n]) % n]
        stats[b] = stat_fn(sample)
    lo, hi = np.percentile(stats, [2.5, 97.5])
    return {"estimate": float(stat_fn(x)), "ci_lo": float(lo), "ci_hi": float(hi), "n_boot": n_boot}
