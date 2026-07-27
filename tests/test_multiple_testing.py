"""Multiple-testing audit (Phase B pre-reg §6) — hermetic, synthetic fixtures only.

Four corrections wrap existing wheels and must not regress:
  * :func:`deflated_sharpe` — Bailey-Lopez de Prado (2014); cross-checked equal
    to ``purgedcv.deflated_sharpe_ratio_full`` on the same returns.
  * :func:`pbo` — CSCV Probability of Backtest Overfitting via ``purgedcv``.
  * :func:`hansen_spa` / :func:`hansen_mcs` — Hansen (2005) SPA + MCS via ``arch``.
  * :func:`harvey_liu_haircut` — Bonferroni/Holm shrinkage of the Sharpe.

No network. All fixtures are small synthetic arrays; bootstrap tests assert the
DECISION (reject / fail to reject) under an overwhelming signal so they are
stable across reps/seed rather than pinning a noisy p-value.
"""
from __future__ import annotations

import numpy as np
import purgedcv
from scipy import stats

from aionis.eval.multiple_testing import (
    deflated_sharpe,
    deflated_sharpe_from_returns,
    hansen_mcs,
    hansen_spa,
    harvey_liu_haircut,
    pbo,
)

# ============================================================================
# 1. Deflated Sharpe
# ============================================================================


def test_deflated_sharpe_single_trial_is_psr_against_zero() -> None:
    """With n_trials=1 there is no multiple-testing correction: sr_star == 0
    (the expected max under the null across one trial is 0), so DSR reduces to
    PSR evaluated at a zero benchmark and a positive Sharpe gives DSR > 0.5."""
    # Arrange
    sharpe, n_obs = 0.5, 60
    # Act
    res = deflated_sharpe(sharpe, n_trials=1, n_obs=n_obs)
    # Assert
    assert res["sr_star"] == 0.0
    assert res["expected_max_z"] == 0.0
    assert 0.0 <= res["dsr"] <= 1.0
    assert res["dsr"] > 0.5  # positive Sharpe → likely skill under PSR(0)
    assert res["p_value"] == 1.0 - res["dsr"]


def test_deflated_sharpe_more_trials_lowers_the_probability() -> None:
    """Holding the Sharpe fixed, deflation gets harsher as n_trials grows:
    the deflated benchmark sr_star rises and DSR falls monotonically."""
    # Arrange
    sharpe, n_obs = 0.5, 60
    # Act
    dsr_by_trials = {n: deflated_sharpe(sharpe, n, n_obs)["dsr"] for n in (1, 5, 25, 100)}
    sr_star_by_trials = {n: deflated_sharpe(sharpe, n, n_obs)["sr_star"] for n in (1, 5, 25, 100)}
    # Assert
    assert dsr_by_trials[1] > dsr_by_trials[5] > dsr_by_trials[25] > dsr_by_trials[100]
    assert sr_star_by_trials[1] < sr_star_by_trials[5] < sr_star_by_trials[100]


def test_deflated_sharpe_matches_purgedcv_on_identical_moments() -> None:
    """The analytical DSR evaluated at sample moments + the Lo (2002) Sharpe
    variance must equal purgedcv.deflated_sharpe_ratio_full on the same returns
    to numerical precision — this is the proof that the closed form reuses
    purgedcv's PSR formula rather than re-deriving a different one."""
    # Arrange
    rng = np.random.default_rng(42)
    returns = rng.normal(0.001, 0.01, 250) * (1 + 0.3 * rng.standard_normal(250))
    arr = np.asarray(returns, dtype=float)
    n_trials = 25
    # Sample moments computed exactly as purgedcv computes them internally.
    sr_hat = float(arr.mean() / arr.std(ddof=0))
    g3 = float(stats.skew(arr, bias=False))
    g4 = float(stats.kurtosis(arr, bias=False, fisher=False))
    denom_sq = 1.0 - g3 * sr_hat + (g4 - 1.0) / 4.0 * sr_hat**2
    var_sharpe = float(denom_sq / (arr.size - 1))
    # Act
    mine = deflated_sharpe(sr_hat, n_trials, arr.size, skew=g3, kurtosis=g4, var_sharpe=var_sharpe)
    diag = purgedcv.deflated_sharpe_ratio_full(arr, n_trials, var_sharpe)
    # Assert
    np.testing.assert_allclose(mine["dsr"], float(diag.dsr), atol=1e-9)
    np.testing.assert_allclose(mine["sr_star"], float(diag.sr_star), atol=1e-12)
    np.testing.assert_allclose(mine["expected_max_z"], float(diag.expected_max_z), atol=1e-12)


def test_deflated_sharpe_rejects_non_finite_and_bad_counts() -> None:
    """Input guards: non-finite sharpe, n_obs < 2, n_trials < 1 all raise."""
    import pytest

    with pytest.raises(ValueError):
        deflated_sharpe(float("nan"), 5, 60)
    with pytest.raises(ValueError):
        deflated_sharpe(0.5, 5, 1)
    with pytest.raises(ValueError):
        deflated_sharpe(0.5, 0, 60)
    with pytest.raises(TypeError):
        deflated_sharpe(0.5, 2.0, 60)  # type: ignore[arg-type]


def test_deflated_sharpe_from_returns_delegates_to_purgedcv() -> None:
    """The returns-based entry point is a thin wrapper: its dsr equals
    purgedcv.deflated_sharpe_ratio (scalar form) for the same arguments."""
    # Arrange
    rng = np.random.default_rng(7)
    returns = rng.normal(0.001, 0.01, 200)
    n_trials, var_sharpe = 10, 0.01**2
    # Act
    res = deflated_sharpe_from_returns(returns, n_trials, var_sharpe)
    direct = purgedcv.deflated_sharpe_ratio(np.asarray(returns, float), n_trials, var_sharpe)
    # Assert
    np.testing.assert_allclose(res["dsr"], float(direct), atol=1e-12)
    assert 0.0 <= res["dsr"] <= 1.0
    assert res["n_obs"] == 200 and res["n_trials"] == 10


# ============================================================================
# 2. PBO (CSCV via purgedcv)
# ============================================================================


def test_pbo_identical_strategies_is_zero_with_zero_logits() -> None:
    """When every strategy is identical, IS-best is arbitrary and its OOS rank
    is exactly the median (all OOS performances equal → average rank), so every
    CSCV logit is exactly 0 and PBO = mean(logit < 0) = 0.0. A degenerate but
    deterministic, honest anchor (NOT 0.5: 0.5 would require uniform OOS ranks)."""
    # Arrange
    rng = np.random.default_rng(0)
    base = rng.standard_normal(40)
    identical = np.tile(base, (5, 1))  # 5 identical strategy rows
    # Act
    res = pbo(identical, n_splits=4)
    # Assert
    assert res["pbo"] == 0.0
    assert res["logits_mean"] == 0.0
    assert res["logits_median"] == 0.0
    assert res["n_combos"] > 0
    assert res["n_strategies"] == 5 and res["n_obs"] == 40


def test_pbo_detects_overfitting_when_is_and_oos_anti_correlated() -> None:
    """If each strategy's IS-period mean is anti-correlated with its OOS-period
    mean, the IS-best (highest IS) lands last out-of-sample → PBO = 1.0 (every
    CSCV combination overfits), the 'mostly fitting noise' regime. Built with
    n_splits=2 so the IS/OOS halves align with the construction (deterministic)."""
    # Arrange: per-strategy IS mean +mu_j, OOS mean -mu_j (anti-correlated).
    rng = np.random.default_rng(0)
    n_strat, n_obs = 8, 40
    mu = np.arange(1, n_strat + 1, dtype=float) * 0.5  # mu_j increasing
    matrix = 0.05 * rng.standard_normal((n_strat, n_obs))
    matrix[:, : n_obs // 2] += mu[:, None]  # IS-ish half: +mu_j
    matrix[:, n_obs // 2 :] -= mu[:, None]  # OOS-ish half: -mu_j
    # Act
    res = pbo(matrix, n_splits=2)
    # Assert
    assert res["pbo"] == 1.0
    assert res["logits_mean"] < 0.0  # all path mass below 0


def test_pbo_probability_in_unit_interval_and_reports_distribution() -> None:
    """On pure-noise strategies PBO lands in a sensible middle range and the
    path-distribution summary keys are all present and finite."""
    # Arrange
    rng = np.random.default_rng(3)
    noise = rng.standard_normal((8, 60))
    # Act
    res = pbo(noise, n_splits=6)
    # Assert
    assert 0.0 <= res["pbo"] <= 1.0
    for key in ("logits_min", "logits_mean", "logits_median"):
        assert np.isfinite(res[key])
    assert res["n_combos"] > 0


def test_pbo_is_deterministic_on_a_fixed_matrix() -> None:
    """CSCV enumerates all combinations (no RNG), so the same matrix → identical
    result across calls (H6 determinism property)."""
    # Arrange
    rng = np.random.default_rng(1)
    matrix = rng.standard_normal((6, 30))
    # Act
    r1 = pbo(matrix, n_splits=6)
    r2 = pbo(matrix, n_splits=6)
    # Assert
    assert r1 == r2


# ============================================================================
# 3. Hansen SPA + MCS (arch)
# ============================================================================


def test_spa_fails_to_reject_when_benchmark_dominates() -> None:
    """When the benchmark's loss is far below every model's loss, no model beats
    it → H0 (no superior model) is retained: consistent p-value is large."""
    # Arrange
    rng = np.random.default_rng(0)
    t = 120
    benchmark_losses = 0.01 * rng.standard_normal(t) ** 2          # ~0 loss
    model_losses = 1.0 + 0.1 * rng.standard_normal((4, t))         # loss ~1
    # Act
    res = hansen_spa(model_losses, benchmark_losses, reps=1000, seed=0)
    # Assert
    assert res["consistent_pvalue"] > 0.05  # fail to reject H0
    assert set(res["pvalues"]) == {"lower", "consistent", "upper"}
    assert res["n_models"] == 4 and res["n_obs"] == t


def test_spa_rejects_when_a_model_dominates_the_benchmark() -> None:
    """When models have far lower loss than the benchmark, at least one is
    superior → H0 rejected: consistent p-value is tiny."""
    # Arrange
    rng = np.random.default_rng(0)
    t = 120
    benchmark_losses = 1.0 + 0.1 * rng.standard_normal(t)          # loss ~1
    model_losses = 0.01 * rng.standard_normal((4, t)) ** 2         # loss ~0
    # Act
    res = hansen_spa(model_losses, benchmark_losses, reps=1000, seed=0)
    # Assert
    assert res["consistent_pvalue"] < 0.05  # reject H0
    assert res["pvalues"]["consistent"] == res["consistent_pvalue"]


def test_mcs_excludes_the_dominated_model() -> None:
    """A model with overwhelmingly higher loss is excluded from the 95% MCS;
    the rest survive in the included set."""
    # Arrange
    rng = np.random.default_rng(0)
    t = 120
    losses = np.vstack([
        0.01 * rng.standard_normal((3, t)),          # 3 good models
        5.0 + 0.1 * rng.standard_normal((1, t)),     # 1 dominated model
    ])
    # Act
    res = hansen_mcs(losses, size=0.05, reps=1000, seed=0)
    # Assert
    assert 3 in res["excluded"]                       # the bad model is out
    assert set(res["included"]) == {0, 1, 2}          # good models survive
    assert res["pvalues"][3] < res["pvalues"][0]      # bad model's p-value lower


# ============================================================================
# 4. Harvey-Liu haircut
# ============================================================================


def test_haircut_single_trial_is_zero_percent() -> None:
    """With n_trials=1 there is no multiple-testing correction, so the haircut
    Sharpe equals the observed Sharpe and the haircut percentage is 0."""
    # Arrange
    sharpe, n_obs = 0.5, 60
    # Act
    res = harvey_liu_haircut(sharpe, n_trials=1, n_obs=n_obs)
    # Assert
    np.testing.assert_allclose(res["haircut_sharpe"], sharpe, atol=1e-9)
    np.testing.assert_allclose(res["haircut_pct"], 0.0, atol=1e-9)
    assert res["p_bonferroni"] == res["p_raw"]
    assert res["survives_bonferroni"]


def test_haircut_grows_monotonically_with_n_trials() -> None:
    """More trials → harsher shrinkage: the haircut percentage rises and the
    haircut Sharpe falls as n_trials grows."""
    # Arrange
    sharpe, n_obs = 0.5, 60
    # Act
    pct = {n: harvey_liu_haircut(sharpe, n, n_obs)["haircut_pct"] for n in (1, 5, 25, 100)}
    hair = {n: harvey_liu_haircut(sharpe, n, n_obs)["haircut_sharpe"] for n in (1, 5, 25, 100)}
    # Assert
    assert pct[1] < pct[5] < pct[25] < pct[100]
    assert hair[1] > hair[5] > hair[25] > hair[100]
    for n in (1, 5, 25, 100):
        assert hair[n] <= sharpe + 1e-12  # shrinkage only


def test_haircut_marginal_sharpe_many_trials_does_not_survive() -> None:
    """A weak Sharpe with many trials fails Bonferroni: p_bonf saturates at/near
    1, survives_bonferroni is False, and the haircut Sharpe is <= 0."""
    # Arrange — weak per-period Sharpe over a short track, many trials.
    # Act
    res = harvey_liu_haircut(sharpe=0.02, n_trials=1000, n_obs=60)
    # Assert
    assert res["p_bonferroni"] >= 0.99
    assert not res["survives_bonferroni"]
    assert res["haircut_sharpe"] <= 0.0
    assert res["haircut_pct"] >= 100.0


def test_haircut_strong_sharpe_survives_modest_trials() -> None:
    """A strong Sharpe over a long track survives a modest number of trials:
    survives_bonferroni True and a positive (small) haircut."""
    # Arrange / Act
    res = harvey_liu_haircut(sharpe=0.5, n_trials=25, n_obs=250)
    # Assert
    assert res["survives_bonferroni"]
    assert res["haircut_pct"] > 0.0
    assert res["haircut_sharpe"] > 0.0


def test_haircut_rejects_non_positive_sharpe() -> None:
    """The one-sided skill haircut requires sharpe > 0; zero/negative raises."""
    import pytest

    with pytest.raises(ValueError):
        harvey_liu_haircut(0.0, n_trials=5, n_obs=60)
    with pytest.raises(ValueError):
        harvey_liu_haircut(-0.5, n_trials=5, n_obs=60)
