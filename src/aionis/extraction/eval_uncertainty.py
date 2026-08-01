"""Deterministic uncertainty intervals for extraction evaluation metrics.

This module provides confidence intervals for metrics from eval_metrics (RD-06).
All intervals are deterministic (seed=0) and return JSON-serializable output.

Key functions:
- wilson_score_interval: Wilson score interval for binomial proportions
- stratified_bootstrap_f1: Stratified bootstrap for macro-F1 over event strata

Edge cases return warning metadata instead of fabricated precision:
- Empty input (n=0)
- Single sample (n=1)
- All success (p=1.0) or all failure (p=0.0)
- Missing strata or tiny stratum sizes (< 5)
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

# Named constants for reproducibility
DEFAULT_CONFIDENCE_LEVEL = 0.95
DEFAULT_BOOTSTRAP_RESAMPLES = 10000
BOOTSTRAP_SEED = 0
MINIMUM_STRATUM_SIZE = 5


def wilson_score_interval(
    successes: int,
    n: int,
    confidence_level: float = DEFAULT_CONFIDENCE_LEVEL,
) -> dict[str, Any]:
    """Compute Wilson score interval for a binomial proportion.

    The Wilson score interval is a confidence interval for a binomial proportion
    that performs well for small samples and extreme proportions.

    Args:
        successes: Number of successful trials
        n: Total number of trials
        confidence_level: Confidence level (e.g., 0.95 for 95% CI)

    Returns:
        JSON-serializable dict with keys:
        - proportion: point estimate (successes/n)
        - lower: lower bound of CI (or None if undefined)
        - upper: upper bound of CI (or None if undefined)
        - confidence_level: the confidence level used
        - warning: warning message if edge case encountered, else None

    Edge cases:
    - n=0: returns proportion=None, bounds=None, warning="empty_input"
    - n=1: returns point estimate, bounds=None, warning="single_sample"
    - p=0 or p=1: returns point estimate, bounds=None, warning="extreme_proportion"
    """
    if n <= 0:
        return {
            "proportion": None,
            "lower": None,
            "upper": None,
            "confidence_level": confidence_level,
            "warning": "empty_input",
        }

    if n == 1:
        proportion = successes / n
        return {
            "proportion": proportion,
            "lower": None,
            "upper": None,
            "confidence_level": confidence_level,
            "warning": "single_sample",
        }

    proportion = successes / n

    # Check for extreme proportions
    if proportion == 0.0 or proportion == 1.0:
        return {
            "proportion": proportion,
            "lower": None,
            "upper": None,
            "confidence_level": confidence_level,
            "warning": "extreme_proportion",
        }

    # Wilson score interval formula
    # z is the z-critical value for the confidence level
    z = _z_critical(confidence_level)
    z2 = z * z

    denominator = 1 + z2 / n
    center = (proportion + z2 / (2 * n)) / denominator
    margin = z * math.sqrt(
        (proportion * (1 - proportion) + z2 / (4 * n)) / n
    ) / denominator

    lower_bound = max(0.0, center - margin)
    upper_bound = min(1.0, center + margin)

    return {
        "proportion": proportion,
        "lower": lower_bound,
        "upper": upper_bound,
        "confidence_level": confidence_level,
        "warning": None,
    }


def _z_critical(confidence_level: float) -> float:
    """Compute z-critical value for a given confidence level using normal distribution.

    Args:
        confidence_level: Confidence level (e.g., 0.95)

    Returns:
        z-critical value (positive)
    """
    # Use scipy.stats.norm.ppf if available, otherwise use scipy.stats.chi2 approximation
    # For determinism and minimal dependencies, we use the chi2 approximation
    # z = sqrt(chi2.ppf(confidence_level, df=1))
    from scipy.stats import chi2

    return math.sqrt(chi2.ppf(confidence_level, 1))


def stratified_bootstrap_f1(
    tp_by_stratum: dict[str, int],
    fp_by_stratum: dict[str, int],
    fn_by_stratum: dict[str, int],
    n_resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    confidence_level: float = DEFAULT_CONFIDENCE_LEVEL,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    """Compute stratified bootstrap confidence interval for macro-F1.

    Bootstrap resamples within each stratum (e.g., event_type), then computes
    macro-F1 as the unweighted mean over strata. This accounts for uncertainty
    in small strata and respects the stratified structure of the data.

    Args:
        tp_by_stratum: Dict mapping stratum name to true positives count
        fp_by_stratum: Dict mapping stratum name to false positives count
        fn_by_stratum: Dict mapping stratum name to false negatives count
        n_resamples: Number of bootstrap resamples (default 10000)
        confidence_level: Confidence level for interval (default 0.95)
        seed: Random seed for reproducibility (default 0)

    Returns:
        JSON-serializable dict with keys:
        - f1_estimate: point estimate (macro-F1 from original data)
        - lower: lower bound of CI (percentile bootstrap)
        - upper: upper bound of CI (percentile bootstrap)
        - confidence_level: the confidence level used
        - n_resamples: number of bootstrap resamples performed
        - warnings: dict mapping stratum name to warning message for problematic strata
        - n_strata: number of strata in analysis
        - effective_strata: number of strata with valid F1 estimates

    Edge cases:
    - Empty stratum (n=0): excluded from bootstrap, warning added
    - Tiny stratum (n < MINIMUM_STRATUM_SIZE): included but warning added
    - Stratum with undefined F1 (zero denominator): excluded, warning added
    """
    # Create deterministic random number generator
    rng = np.random.default_rng(seed)

    # Validate input
    all_strata = set(tp_by_stratum) | set(fp_by_stratum) | set(fn_by_stratum)
    warnings: dict[str, str] = {}

    if not all_strata:
        return {
            "f1_estimate": None,
            "lower": None,
            "upper": None,
            "confidence_level": confidence_level,
            "n_resamples": n_resamples,
            "warnings": {"all": "no_strata_provided"},
            "n_strata": 0,
            "effective_strata": 0,
        }

    # Build stratum data and compute point estimate
    stratum_data: dict[str, dict[str, Any]] = {}
    valid_strata: list[str] = []

    for stratum in sorted(all_strata):
        tp = tp_by_stratum.get(stratum, 0)
        fp = fp_by_stratum.get(stratum, 0)
        fn = fn_by_stratum.get(stratum, 0)

        n_samples = tp + fp + fn
        f1_value: float | None = None

        # Check for empty stratum
        if n_samples == 0:
            warnings[stratum] = "empty_stratum"
            continue

        # Check for tiny stratum
        if n_samples < MINIMUM_STRATUM_SIZE:
            warnings[stratum] = f"tiny_stratum_n_{n_samples}"

        # Compute F1 for this stratum
        precision: float | None = None
        recall: float | None = None

        if tp + fp > 0:
            precision = tp / (tp + fp)
        if tp + fn > 0:
            recall = tp / (tp + fn)

        if precision is not None and recall is not None and (precision + recall) > 0:
            f1_value = 2 * precision * recall / (precision + recall)
            valid_strata.append(stratum)
        else:
            warnings[stratum] = "undefined_f1"

        stratum_data[stratum] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "n": n_samples,
            "f1": f1_value,
        }

    # Compute point estimate (macro-F1)
    point_f1_values = [stratum_data[s]["f1"] for s in valid_strata]
    if not point_f1_values:
        return {
            "f1_estimate": None,
            "lower": None,
            "upper": None,
            "confidence_level": confidence_level,
            "n_resamples": n_resamples,
            "warnings": warnings,
            "n_strata": len(all_strata),
            "effective_strata": 0,
        }

    f1_estimate = sum(point_f1_values) / len(point_f1_values)

    # Bootstrap resampling
    bootstrap_f1_values = np.zeros(n_resamples)

    for i in range(n_resamples):
        # Resample within each stratum with replacement
        resampled_f1s: list[float] = []

        for stratum in valid_strata:
            data = stratum_data[stratum]
            n = data["n"]

            # Multinomial resample: count how many of each class we get
            # Probabilities: P(TP) = tp/n, P(FP) = fp/n, P(FN) = fn/n
            p_tp = data["tp"] / n
            p_fp = data["fp"] / n
            p_fn = data["fn"] / n

            # Resample n times from this stratum
            resample_counts = rng.multinomial(n, [p_tp, p_fp, p_fn])
            resample_tp, resample_fp, resample_fn = resample_counts

            # Compute F1 for this resample
            resample_precision: float | None = None
            resample_recall: float | None = None

            if resample_tp + resample_fp > 0:
                resample_precision = resample_tp / (resample_tp + resample_fp)
            if resample_tp + resample_fn > 0:
                resample_recall = resample_tp / (resample_tp + resample_fn)

            if (
                resample_precision is not None
                and resample_recall is not None
                and (resample_precision + resample_recall) > 0
            ):
                resample_f1 = (
                    2 * resample_precision * resample_recall
                    / (resample_precision + resample_recall)
                )
                resampled_f1s.append(resample_f1)

        # Macro-F1: mean over strata
        if resampled_f1s:
            bootstrap_f1_values[i] = sum(resampled_f1s) / len(resampled_f1s)
        else:
            bootstrap_f1_values[i] = np.nan

    # Compute percentile interval
    alpha = 1 - confidence_level
    lower_percentile = (alpha / 2) * 100
    upper_percentile = (1 - alpha / 2) * 100

    valid_bootstrap = bootstrap_f1_values[~np.isnan(bootstrap_f1_values)]

    if len(valid_bootstrap) == 0:
        return {
            "f1_estimate": f1_estimate,
            "lower": None,
            "upper": None,
            "confidence_level": confidence_level,
            "n_resamples": n_resamples,
            "warnings": warnings,
            "n_strata": len(all_strata),
            "effective_strata": len(valid_strata),
        }

    lower_bound = float(np.percentile(valid_bootstrap, lower_percentile))
    upper_bound = float(np.percentile(valid_bootstrap, upper_percentile))

    return {
        "f1_estimate": f1_estimate,
        "lower": lower_bound,
        "upper": upper_bound,
        "confidence_level": confidence_level,
        "n_resamples": n_resamples,
        "warnings": warnings,
        "n_strata": len(all_strata),
        "effective_strata": len(valid_strata),
    }


__all__ = [
    "DEFAULT_CONFIDENCE_LEVEL",
    "DEFAULT_BOOTSTRAP_RESAMPLES",
    "BOOTSTRAP_SEED",
    "MINIMUM_STRATUM_SIZE",
    "wilson_score_interval",
    "stratified_bootstrap_f1",
]
