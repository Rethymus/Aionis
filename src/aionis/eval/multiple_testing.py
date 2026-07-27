"""Multiple-testing audit for the Phase B headline (pre-reg §6).

The filed-date vs period-end rank-IC claim is one of many comparisons the
project will run, so the headline Sharpe / rank-IC must survive a
multiple-testing correction before it is reported as skill. This module
wraps four established corrections, reusing the project's existing wheels
(``purgedcv`` for DSR + PBO, ``arch`` for Hansen SPA / MCS) and porting a
Bonferroni/Holm haircut from a CC0 reference for Harvey-Liu:

1. :func:`deflated_sharpe` — Bailey & Lopez de Prado (2014) DSR evaluated at
   user-supplied moments; :func:`deflated_sharpe_from_returns` delegates to
   ``purgedcv.deflated_sharpe_ratio_full`` (same PSR formula, sample moments).
2. :func:`pbo` — Combinatorially Symmetric Cross-Validation (CSCV)
   Probability of Backtest Overfitting via
   ``purgedcv.probability_of_backtest_overfitting`` (which reconstructs the
   IS/OOS paths internally; ``purgedcv.reconstruct_paths`` is the companion
   for building the matrix from fold-level predictions).
3. :func:`hansen_spa` / :func:`hansen_mcs` — Hansen (2005) Superior
   Predictive Ability test and the Hansen-Lincezewski-White Model Confidence
   Set via ``arch.bootstrap``.
4. :func:`harvey_liu_haircut` — Bonferroni/Holm shrinkage of the observed
   Sharpe given ``n_trials`` (Harvey & Liu; CC0 port reference:
   ``YannickKae/Evaluating-Investment-Strategies``).

Report rule (pre-reg §6): every reported Sharpe carries the
``deflated + haircut + PBO`` triple.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats  # transitive dep via statsmodels/purgedcv; std normal CDF/ppf

# --- constants ---------------------------------------------------------------

# Euler-Mascheroni constant for the DSR extreme-value bracket (Bailey-LdP 2014).
_GAMMA_EM = 0.5772156649015329


# ============================================================================
# 1. Deflated Sharpe Ratio (Bailey & Lopez de Prado, 2014)
# ============================================================================


def _sr_variance(sharpe: float, n_obs: int, skew: float, kurtosis: float) -> float:
    """Per-observation variance of the Sharpe estimator (Lo 2002; Mertens 2002).

    ``V[SR] = (1 - gamma3 * SR + (gamma4 - 1)/4 * SR^2) / (n - 1)``, where
    ``gamma4`` is kurtosis (NOT excess). This is the same denominator term
    ``purgedcv`` uses inside its PSR, so the analytical DSR computed here
    matches ``purgedcv.deflated_sharpe_ratio_full`` to numerical precision
    when the same moments are supplied (verified in the hermetic test).
    """
    denom_sq = 1.0 - skew * sharpe + (kurtosis - 1.0) / 4.0 * sharpe**2
    if not np.isfinite(denom_sq) or denom_sq <= 0:
        raise ValueError(
            f"Sharpe moments are too extreme for the Gaussian approximation "
            f"(denominator={denom_sq:.4g}); lower |sharpe| or relax skew/kurtosis."
        )
    return float(denom_sq / (n_obs - 1))


def _expected_max_z(n_trials: int) -> float:
    """Standardized expected max of ``n_trials`` iid N(0,1) draws (Bailey-LdP 2014).

    The extreme-value bracket ``(1 - gamma) * Phi_inv(1 - 1/n)
    + gamma * Phi_inv(1 - 1/(n*e))``. A single trial has no maximum to correct
    for, so it returns 0 (DSR then reduces to PSR against a zero benchmark).
    Mirrors ``purgedcv._metrics._expected_max_z``.
    """
    if n_trials <= 1:
        return 0.0
    return float(
        (1.0 - _GAMMA_EM) * stats.norm.ppf(1.0 - 1.0 / n_trials)
        + _GAMMA_EM * stats.norm.ppf(1.0 - 1.0 / (n_trials * np.e))
    )


def deflated_sharpe(
    sharpe: float,
    n_trials: int,
    n_obs: int,
    skew: float = 0.0,
    kurtosis: float = 3.0,
    *,
    var_sharpe: float | None = None,
) -> dict[str, Any]:
    """Analytical Deflated Sharpe Ratio (Bailey & Lopez de Prado, 2014).

    Probability that the true Sharpe exceeds the deflated benchmark
    ``SR*_n = sqrt(V[SR]) * E[max_z]`` that accounts for ``n_trials``
    independent searches. Closed-form at user-supplied moments; this is the
    same PSR formula ``purgedcv.deflated_sharpe_ratio_full`` evaluates at
    *sample* moments (cross-checked equal in the hermetic test).

    Args:
        sharpe: Observed per-period Sharpe ratio (NOT annualised; DSR is
            intrinsically per-observation).
        n_trials: Number of independent configurations tried before reporting
            this Sharpe (>= 1). ``n_trials == 1`` reduces DSR to PSR(0).
        n_obs: Track-record length (>= 2).
        skew: Sample skew of the return distribution (default 0 = symmetric).
        kurtosis: Sample kurtosis (NOT excess; default 3 = normal).
        var_sharpe: Per-observation variance of Sharpe ratios across the
            trials. When ``None`` (the common case where only the headline
            Sharpe is available) it defaults to the Lo (2002) Sharpe-estimator
            variance ``V[SR]`` — the textbook convention. Pass an explicit
            value (e.g. from an Optuna ``TrialSharpeRecorder``) if the
            across-trial Sharpe spread is known.

    Returns:
        Dict with ``dsr`` (the probability in [0, 1]), ``p_value`` (one-sided:
        ``1 - dsr``), ``dsr_stat`` (the standardised z), the deflated
        benchmark ``sr_star``, the bracket ``expected_max_z``, the
        per-observation ``var_sharpe`` used, and the echoed inputs.
    """
    if not isinstance(n_trials, (int, np.integer)) or isinstance(n_trials, bool):
        raise TypeError(f"n_trials must be an integer, got {type(n_trials).__name__}.")
    if n_trials < 1:
        raise ValueError(f"n_trials must be >= 1, got {n_trials}.")
    if n_obs < 2:
        raise ValueError(f"n_obs must be >= 2, got {n_obs}.")
    if not np.isfinite(sharpe):
        raise ValueError(f"sharpe must be finite, got {sharpe}.")

    if var_sharpe is None:
        var_sharpe = _sr_variance(sharpe, n_obs, skew, kurtosis)
    else:
        if not np.isfinite(var_sharpe) or var_sharpe < 0:
            raise ValueError(f"var_sharpe must be a non-negative finite number, got {var_sharpe}.")

    expected_max_z = _expected_max_z(int(n_trials))
    sr_star = float(np.sqrt(var_sharpe) * expected_max_z)
    denom_sq = 1.0 - skew * sharpe + (kurtosis - 1.0) / 4.0 * sharpe**2
    if not np.isfinite(denom_sq) or denom_sq <= 0:
        raise ValueError(
            f"Sharpe moments too extreme for the Gaussian approximation "
            f"(denominator={denom_sq:.4g})."
        )
    # z = (SR_hat - SR*) * sqrt(n-1) / sqrt(denom); identical to purgedcv PSR.
    z = (sharpe - sr_star) * np.sqrt(n_obs - 1) / np.sqrt(denom_sq)
    dsr = float(stats.norm.cdf(z))
    return {
        "dsr": dsr,
        "p_value": 1.0 - dsr,
        "dsr_stat": float(z),
        "sr_star": sr_star,
        "expected_max_z": float(expected_max_z),
        "var_sharpe": float(var_sharpe),
        "observed_sr": float(sharpe),
        "n_trials": int(n_trials),
        "n_obs": int(n_obs),
    }


def deflated_sharpe_from_returns(
    returns: np.ndarray,
    n_trials: int,
    var_sharpe: float,
    *,
    bars_per_year: int | None = None,
) -> dict[str, Any]:
    """Thin delegation to ``purgedcv.deflated_sharpe_ratio_full``.

    Use this when you have the raw return series (so sample moments are
    estimated, not asserted) and an explicit across-trial Sharpe variance.
    See :func:`deflated_sharpe` for the analytical, moment-supplied form.
    """
    import purgedcv

    diag = purgedcv.deflated_sharpe_ratio_full(
        np.asarray(returns, dtype=float), int(n_trials), float(var_sharpe),
        bars_per_year=bars_per_year,
    )
    return {
        "dsr": float(diag.dsr),
        "p_value": 1.0 - float(diag.dsr),
        "dsr_stat": float(stats.norm.ppf(diag.dsr)) if 0.0 < diag.dsr < 1.0 else float("nan"),
        "sr_star": float(diag.sr_star),
        "expected_max_z": float(diag.expected_max_z),
        "var_sharpe": float(diag.var_sharpe),
        "observed_sr": float(diag.observed_sr),
        "n_trials": int(diag.n_trials),
        "n_obs": int(diag.n_obs),
        "skew": float(diag.skew),
        "kurt": float(diag.kurt),
    }


# ============================================================================
# 2. Probability of Backtest Overfitting (Bailey-LdP CSCV, via purgedcv)
# ============================================================================


def pbo(
    is_oos_matrix: np.ndarray | pd.DataFrame,
    n_splits: int = 16,
    *,
    metric: Any = None,
    prediction_times: pd.Series | None = None,
    evaluation_times: pd.Series | None = None,
    purge_horizon: Any = None,
    embargo: Any = None,
) -> dict[str, Any]:
    """Combinatorially Symmetric CV Probability of Backtest Overfitting.

    Wraps ``purgedcv.probability_of_backtest_overfitting``, which partitions
    the (n_strategies x n_obs) matrix into CSCV IS/OOS combinations
    (CombinatorialPurgedCV — the CPCV path reconstruction), scores the
    IS-best configuration's OOS relative rank per combination, and reports
    the fraction whose logit < 0. ``purgedcv.reconstruct_paths`` is the
    companion utility for building ``is_oos_matrix`` from fold-level
    predictions when you start from CV folds rather than a dense matrix.

    Args:
        is_oos_matrix: ``(n_strategies, n_obs)`` array/DataFrame of strategy
            returns. Rows = configurations, columns = observations.
        n_splits: Even integer >= 2; CSCV forms ``C(n_splits, n_splits//2)``
            IS/OOS combinations. Default 16 (per purgedcv).
        metric: Config scorer returning a scalar (default = sample Sharpe).
        prediction_times / evaluation_times / purge_horizon / embargo:
            Forwarded to ``purgedcv`` to apply purge + embargo (CPCV). Both
            time series must be supplied together; lengths must match n_obs.

    Returns:
        Dict with ``pbo`` (the probability in [0, 1]; ``>0.5`` ⇒ the search
        is mostly fitting noise), the path distribution
        (``logits_min``/``logits_mean``/``logits_median``), the OOS-on-IS
        ``slope`` (``>0`` ⇒ IS strength carries over), ``n_combos``, and the
        echoed dimensions.
    """
    import purgedcv

    matrix = np.asarray(is_oos_matrix, dtype=float)
    n_strategies, n_obs_m = matrix.shape
    kwargs: dict[str, Any] = {}
    if metric is not None:
        kwargs["metric"] = metric
    if prediction_times is not None or evaluation_times is not None:
        kwargs["prediction_times"] = prediction_times
        kwargs["evaluation_times"] = evaluation_times
    if purge_horizon is not None:
        kwargs["purge_horizon"] = purge_horizon
    if embargo is not None:
        kwargs["embargo"] = embargo
    result = purgedcv.probability_of_backtest_overfitting(
        matrix, n_splits=int(n_splits), **kwargs,
    )
    logits = np.asarray(result.logits, dtype=float)
    return {
        "pbo": float(result.pbo),
        "logits_min": float(np.min(logits)) if logits.size else float("nan"),
        "logits_mean": float(np.mean(logits)) if logits.size else float("nan"),
        "logits_median": float(np.median(logits)) if logits.size else float("nan"),
        "n_logits": int(logits.size),
        "slope": float(result.slope),
        "n_combos": int(result.n_combos),
        "n_strategies": int(n_strategies),
        "n_obs": int(n_obs_m),
        "n_splits": int(n_splits),
    }


# ============================================================================
# 3. Hansen SPA (Superior Predictive Ability) + Model Confidence Set (arch)
# ============================================================================


def hansen_spa(
    loss_matrix: np.ndarray | pd.DataFrame,
    benchmark_losses: np.ndarray | pd.Series,
    *,
    reps: int = 1000,
    block_size: int | None = None,
    bootstrap: str = "stationary",
    studentize: bool = True,
    seed: int = 0,
) -> dict[str, Any]:
    """Hansen (2005) Superior Predictive Ability test via ``arch.bootstrap.SPA``.

    H0: *no* model is superior to the benchmark (models do not beat it).
    A small ``consistent`` p-value rejects H0 ⇒ at least one model has
    lower loss than the benchmark (i.e. genuinely better). Inputs are
    **losses** (lower = better), matching arch's convention.

    Args:
        loss_matrix: ``(n_strategies, n_obs)`` of model losses (rows =
            strategies, columns = time). Transposed internally to arch's
            ``(n_obs, n_models)`` layout.
        benchmark_losses: ``(n_obs,)`` benchmark loss series.
        reps: Bootstrap replications.
        block_size: Bootstrap block length (default ``sqrt(n_obs)``).
        bootstrap: arch block scheme (``"stationary"``, ``"circular"``/``"cbb"``,
            ``"moving block"``/``"mbb"``).
        studentize: Studentize loss differentials (recommended).
        seed: RNG seed for reproducibility.

    Returns:
        Dict with ``pvalues`` (``lower``/``consistent``/``upper``),
        ``consistent_pvalue`` (Hansen's recommended headline), plus
        ``n_models``, ``n_obs``, ``reps``, ``seed``.
    """
    from arch.bootstrap import SPA

    losses = np.asarray(loss_matrix, dtype=float)
    if losses.ndim != 2:
        raise ValueError(f"loss_matrix must be 2-D (n_strategies, n_obs), got {losses.ndim}-D.")
    bench = np.asarray(benchmark_losses, dtype=float).ravel()
    n_models, n_obs = losses.shape
    if bench.shape[0] != n_obs:
        raise ValueError(
            f"benchmark_losses length {bench.shape[0]} != loss_matrix n_obs {n_obs}."
        )
    spa = SPA(
        benchmark=bench,
        models=losses.T,  # arch wants (n_obs, n_models)
        block_size=block_size,
        reps=int(reps),
        bootstrap=bootstrap,
        studentize=studentize,
        seed=int(seed),
    )
    spa.compute()
    pv = spa.pvalues
    pvals = {k: float(pv.loc[k]) for k in ("lower", "consistent", "upper")}
    return {
        "pvalues": pvals,
        "consistent_pvalue": pvals["consistent"],
        "lower_pvalue": pvals["lower"],
        "upper_pvalue": pvals["upper"],
        "n_models": int(n_models),
        "n_obs": int(n_obs),
        "reps": int(reps),
        "seed": int(seed),
    }


def hansen_mcs(
    loss_matrix: np.ndarray | pd.DataFrame,
    *,
    size: float = 0.05,
    reps: int = 1000,
    block_size: int | None = None,
    method: str = "R",
    bootstrap: str = "stationary",
    seed: int = 0,
) -> dict[str, Any]:
    """Hansen-Lincezewski-White Model Confidence Set via ``arch.bootstrap.MCS``.

    The MCS is the *set* of models that are statistically indistinguishable
    from the best at level ``size`` — i.e. the models you cannot rule out as
    inferior. Unlike SPA it needs no declared benchmark: all columns compete.

    Args:
        loss_matrix: ``(n_strategies, n_obs)`` of losses (rows = strategies).
            Transposed internally to arch's ``(n_obs, n_models)`` layout.
        size: Confidence level (default 0.05 ⇒ 95% MCS).
        reps / block_size / bootstrap / seed: as in :func:`hansen_spa`.
        method: ``"R"`` (range) or ``"max"`` statistic.

    Returns:
        Dict with ``included`` / ``excluded`` strategy indices (the MCS
        membership), the per-model ``pvalues``, and the echoed dimensions.
    """
    from arch.bootstrap import MCS

    losses = np.asarray(loss_matrix, dtype=float)
    if losses.ndim != 2:
        raise ValueError(f"loss_matrix must be 2-D (n_strategies, n_obs), got {losses.ndim}-D.")
    n_models, n_obs = losses.shape
    mcs = MCS(
        losses=losses.T,  # arch wants (n_obs, n_models)
        size=float(size),
        reps=int(reps),
        block_size=block_size,
        method=method,
        bootstrap=bootstrap,
        seed=int(seed),
    )
    mcs.compute()
    included = list(mcs.included)
    excluded = list(mcs.excluded)
    pvals = mcs.pvalues
    # arch returns a DataFrame indexed by model with a single "Pvalue" column.
    if isinstance(pvals, pd.DataFrame):
        pval_map = {idx: float(row["Pvalue"]) for idx, row in pvals.iterrows()}
    elif hasattr(pvals, "items"):  # pandas Series keyed by model name
        pval_map = {k: float(v) for k, v in pvals.items()}
    else:  # plain sequence aligned to columns
        pval_map = {i: float(v) for i, v in enumerate(pvals)}
    return {
        "included": included,
        "excluded": excluded,
        "pvalues": pval_map,
        "size": float(size),
        "n_models": int(n_models),
        "n_obs": int(n_obs),
        "reps": int(reps),
        "seed": int(seed),
    }


# ============================================================================
# 4. Harvey-Liu haircut Sharpe (Bonferroni/Holm shrinkage)
# ============================================================================


def harvey_liu_haircut(
    sharpe: float,
    n_trials: int,
    n_obs: int,
    *,
    skew: float = 0.0,
    kurtosis: float = 3.0,
    alpha: float = 0.05,
) -> dict[str, Any]:
    """Harvey-Liu haircut Sharpe ratio — Bonferroni/Holm multiple-testing shrinkage.

    Shrinks the observed Sharpe by re-evaluating it at the Bonferroni-adjusted
    p-value. The haircut Sharpe is the Sharpe implied by the survival
    threshold under ``n_trials`` independent tests:

        z_obs   = SR / SE,  SE = sqrt(V[SR])  (Lo 2002 Sharpe-estimator SE)
        p_raw   = 1 - Phi(z_obs)                      (one-sided, SR > 0)
        p_bonf  = min(1, n_trials * p_raw)            (Bonferroni)
        SR_hair = Phi^{-1}(1 - p_bonf) * SE           (shrunk Sharpe)

    ``haircut_pct = (SR - SR_hair) / SR * 100``. With ``n_trials == 1`` there
    is no correction (``p_bonf = p_raw`` ⇒ ``SR_hair = SR`` ⇒ 0% haircut);
    as ``n_trials`` grows the haircut grows, and once ``p_bonf`` saturates at
    1 the Sharpe no longer survives Bonferroni (``SR_hair <= 0``). For a
    single best strategy Holm's step-down coincides with Bonferroni (the
    smallest p is multiplied by N in both), so the reported haircut is the
    Holm haircut too.

    Port reference: ``YannickKae/Evaluating-Investment-Strategies`` (CC0-1.0,
    public domain — verified). Implemented here from the Bonferroni/Holm
    shrinkage formula rather than copied, since the method is a closed form.

    Args:
        sharpe: Observed per-period Sharpe ratio (must be > 0; a non-positive
            Sharpe already fails the one-sided skill test).
        n_trials: Number of independent configurations tried (>= 1).
        n_obs: Track-record length (>= 2).
        skew / kurtosis: Sample moments (kurtosis NOT excess; defaults normal).
        alpha: Significance level (informational; reported for context).

    Returns:
        Dict with ``observed_sr``, ``haircut_sharpe`` (the shrunk Sharpe;
        may be ``<= 0`` when the Sharpe does not survive Bonferroni),
        ``haircut_pct`` (percentage of the original Sharpe trimmed),
        ``z_obs``, ``se``, ``p_raw``, ``p_bonferroni``, ``survives_bonferroni``
        (``p_bonf <= alpha``), and ``method``.
    """
    if not isinstance(n_trials, (int, np.integer)) or isinstance(n_trials, bool):
        raise TypeError(f"n_trials must be an integer, got {type(n_trials).__name__}.")
    if n_trials < 1:
        raise ValueError(f"n_trials must be >= 1, got {n_trials}.")
    if n_obs < 2:
        raise ValueError(f"n_obs must be >= 2, got {n_obs}.")
    if not np.isfinite(sharpe):
        raise ValueError(f"sharpe must be finite, got {sharpe}.")
    if sharpe <= 0:
        raise ValueError(
            f"sharpe must be > 0 for a one-sided skill haircut, got {sharpe}; "
            "a non-positive Sharpe already fails the skill test."
        )

    var_sharpe = _sr_variance(sharpe, n_obs, skew, kurtosis)
    se = float(np.sqrt(var_sharpe))
    z_obs = float(sharpe / se)
    p_raw = float(stats.norm.sf(z_obs))  # 1 - Phi(z_obs), one-sided
    p_bonf = float(min(1.0, n_trials * p_raw))
    # z implied by the Bonferroni-adjusted p-value. If p_bonf saturates at 1
    # the Sharpe does not survive: ppf(0) = -inf => haircut_sharpe = -inf,
    # i.e. no credible skill remains. We surface that honestly rather than
    # floor it; callers branch on `survives_bonferroni`.
    z_bonf = float(stats.norm.ppf(1.0 - p_bonf))
    haircut_sharpe = z_bonf * se
    haircut_pct = (sharpe - haircut_sharpe) / sharpe * 100.0
    return {
        "observed_sr": float(sharpe),
        "haircut_sharpe": float(haircut_sharpe),
        "haircut_pct": float(haircut_pct),
        "z_obs": z_obs,
        "se": se,
        "p_raw": p_raw,
        "p_bonferroni": p_bonf,
        "survives_bonferroni": bool(p_bonf <= alpha),
        "alpha": float(alpha),
        "n_trials": int(n_trials),
        "n_obs": int(n_obs),
        "method": "bonferroni",
    }
