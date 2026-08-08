"""Deflated Sharpe Ratio + PBO — anti-overfit utilities for multiple testing.

When a research process tries many configurations (e.g. an adaptive learner
auto-tuning toward better IC), the best observed performance is inflated by
chance. The **Deflated Sharpe Ratio** (Bailey & López de Prado 2014) corrects
the observed Sharpe for (a) the number of independent trials N and (b)
non-normality (skew/kurtosis), returning P(true Sharpe > 0 | observed) after
deflation. The **Probability of Backtest Overfit** (Bailey-Borwein-LdP-Zhu) is
the complementary view via combinatorially-symmetric cross-validation.

Pure utility — writes NO ledger / frozen surface. Track Adaptive prereg §8
(`docs/track-adaptive-preregistration.md`) requires this multiplicity
accounting; the utilities are reusable for any multiple-testing correction.

References (verified):
- Bailey & López de Prado (2014), "The Deflated Sharpe Ratio", J. Portfolio Mgmt
  https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551
- Bailey, Borwein, López de Prado, Zhu, "The Probability of Backtest Overfitting"
  https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf
"""

from __future__ import annotations

import math
from itertools import combinations

import numpy as np
from scipy.stats import norm  # available transitively via statsmodels/arch

_EULER_MASCHERONI = 0.5772156649015329


def _expected_max_standard_normal(n_trials: int) -> float:
    """E[max of N iid standard normals] (Bailey-LdP approximation).

    ≈ (1-γ)·Φ⁻¹(1 - 1/N) + γ·Φ⁻¹(1 - 1/(N·e)), γ = Euler-Mascheroni.
    n_trials=1 → 0 (no inflation from a single draw).
    """
    if n_trials <= 1:
        return 0.0
    z1 = norm.ppf(1.0 - 1.0 / n_trials)
    z2 = norm.ppf(1.0 - 1.0 / (n_trials * math.e))
    return float((1.0 - _EULER_MASCHERONI) * z1 + _EULER_MASCHERONI * z2)


def expected_max_sharpe(n_trials: int, n_obs: int) -> float:
    """Expected maximum *observed* Sharpe under n_trials null (true-SR=0) trials.

    Scales the expected-max standard normal by the null Sharpe SE, which at
    SR=0 reduces to sqrt(1/(n_obs-1)) regardless of skew/kurtosis. This is the
    multiple-testing "hurdle" the observed Sharpe must clear.
    """
    if n_trials < 1 or n_obs < 2:
        return float("nan")
    return float(_expected_max_standard_normal(n_trials) * math.sqrt(1.0 / (n_obs - 1)))


def deflated_sharpe_ratio(
    observed_sharpe: float,
    n_trials: int,
    n_obs: int,
    skew: float = 0.0,
    kurtosis: float = 3.0,
) -> float:
    """P(true Sharpe > 0 | observed), deflated for n_trials + non-normality.

    Returns a probability in [0, 1]. Higher = stronger evidence the observed
    Sharpe is real rather than a multiple-testing artifact. Non-finite inputs,
    n_trials<1, n_obs<2, or a non-positive variance term → NaN.
    """
    if n_trials < 1 or n_obs < 2:
        return float("nan")
    if not all(math.isfinite(x) for x in (observed_sharpe, skew, kurtosis)):
        return float("nan")
    sr_eq = expected_max_sharpe(n_trials, n_obs)
    # Lo (2002)-style non-normal variance of the Sharpe estimator, evaluated at
    # the observed Sharpe (Bailey-LdP deflation form).
    var_term = 1.0 - skew * observed_sharpe + (kurtosis - 1.0) / 4.0 * observed_sharpe ** 2
    if var_term <= 0:
        return float("nan")
    se = math.sqrt(var_term / (n_obs - 1))
    stat = (observed_sharpe - sr_eq) / se
    return float(norm.cdf(stat))


def probability_of_backtest_overfit(
    isr_matrix: np.ndarray | list[list[float]],
    max_partitions: int = 20000,
) -> float:
    """PBO via combinatorially-symmetric cross-validation (Bailey-Borwein-LdP-Zhu).

    ``isr_matrix``: 2-D array (rows = observation samples, cols = strategies) of
    Sharpe-ratio-like values. For every C(N, N/2) partition into in-sample /
    out-of-sample halves, the best in-sample strategy is ranked out-of-sample;
    λ = relative OOS rank in (0, 1). PBO = P(λ > 0.5) — the IS-best strategy
    tends to land below the OOS median. **PBO > 0.5 flags overfit.**

    Combinatorial cost is C(N, N/2); raises ValueError if that exceeds
    ``max_partitions`` (use a subsample for large N).
    """
    m = np.asarray(isr_matrix, dtype=float)
    if m.ndim != 2 or m.shape[0] < 2 or m.shape[1] < 2:
        raise ValueError("isr_matrix must be 2-D with >=2 rows and >=2 cols")
    n, s = m.shape
    half = n // 2
    if half < 1:
        raise ValueError("need >=2 rows to form CSCV halves")
    n_partitions = math.comb(n, half)
    if n_partitions > max_partitions:
        raise ValueError(
            f"C({n},{half})={n_partitions} > max_partitions={max_partitions}; "
            "subsample rows or raise max_partitions."
        )
    idx = list(range(n))
    lambdas: list[float] = []
    for subset in combinations(idx, half):
        insample = m[list(subset), :]
        oos = m[[i for i in idx if i not in subset], :]
        best_is = int(insample.mean(axis=0).argmax())  # best in-sample strategy
        oos_desc = oos.mean(axis=0).argsort()[::-1]  # rank 0 = best OOS
        oos_rank = int(np.where(oos_desc == best_is)[0][0])
        lambdas.append((oos_rank + 1) / s)
    return float(np.mean([lm > 0.5 for lm in lambdas]))
