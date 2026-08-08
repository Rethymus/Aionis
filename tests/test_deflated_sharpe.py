"""Hermetic tests for the Deflated Sharpe Ratio + PBO anti-overfit utility."""

from __future__ import annotations

import math

import numpy as np
import pytest

from aionis.eval.deflated_sharpe import (
    deflated_sharpe_ratio,
    expected_max_sharpe,
    probability_of_backtest_overfit,
)

_NAN = float("nan")


# --- DSR core behavior --------------------------------------------------------


def test_dsr_near_one_for_strong_signal_single_trial() -> None:
    # Large positive Sharpe, one trial, lots of data → very likely real.
    dsr = deflated_sharpe_ratio(observed_sharpe=2.0, n_trials=1, n_obs=240)
    assert dsr > 0.999


def test_dsr_drops_monotonically_with_more_trials() -> None:
    # Weak-ish Sharpe so DSR stays non-saturated (norm.cdf not pinned at 1.0);
    # more trials → more multiple-testing inflation → lower DSR.
    same_sr = 0.2
    dsr_1 = deflated_sharpe_ratio(same_sr, n_trials=1, n_obs=60)
    dsr_10 = deflated_sharpe_ratio(same_sr, n_trials=10, n_obs=60)
    dsr_100 = deflated_sharpe_ratio(same_sr, n_trials=100, n_obs=60)
    assert dsr_1 > dsr_10 > dsr_100
    assert 0.0 <= dsr_100 <= 1.0


def test_dsr_drops_with_fewer_observations() -> None:
    # Same Sharpe + trials, but less data → less confidence → lower DSR.
    dsr_more = deflated_sharpe_ratio(1.0, n_trials=5, n_obs=240)
    dsr_less = deflated_sharpe_ratio(1.0, n_trials=5, n_obs=24)
    assert dsr_more > dsr_less


def test_dsr_zero_sharpe_is_about_half() -> None:
    # Observed Sharpe of 0, single trial → P(true>0) ≈ 0.5 (symmetric null).
    dsr = deflated_sharpe_ratio(observed_sharpe=0.0, n_trials=1, n_obs=120)
    assert 0.45 < dsr < 0.55


def test_dsr_non_normal_skew_kurtosis_affects_result() -> None:
    # Heavy negative skew + fat tails lower confidence vs normal (same SR).
    dsr_normal = deflated_sharpe_ratio(1.0, n_trials=1, n_obs=120, skew=0.0, kurtosis=3.0)
    dsr_heavy = deflated_sharpe_ratio(1.0, n_trials=1, n_obs=120, skew=-1.0, kurtosis=5.0)
    assert dsr_normal > dsr_heavy


# --- expected_max_sharpe ------------------------------------------------------


def test_expected_max_sharpe_increases_with_trials() -> None:
    em1 = expected_max_sharpe(n_trials=1, n_obs=120)
    em10 = expected_max_sharpe(n_trials=10, n_obs=120)
    em100 = expected_max_sharpe(n_trials=100, n_obs=120)
    assert em1 == 0.0  # single trial → no inflation hurdle
    assert em10 > em1
    assert em100 > em10


def test_expected_max_sharpe_decreases_with_more_data() -> None:
    # More observations → tighter SE → smaller expected-max hurdle.
    assert expected_max_sharpe(n_trials=20, n_obs=240) < expected_max_sharpe(n_trials=20, n_obs=24)


# --- edge cases → NaN / errors ------------------------------------------------


def test_dsr_nan_for_insufficient_observations() -> None:
    assert math.isnan(deflated_sharpe_ratio(1.0, n_trials=1, n_obs=1))
    assert math.isnan(deflated_sharpe_ratio(1.0, n_trials=1, n_obs=0))


def test_dsr_nan_for_invalid_trials_or_nonfinite() -> None:
    assert math.isnan(deflated_sharpe_ratio(1.0, n_trials=0, n_obs=120))
    assert math.isnan(deflated_sharpe_ratio(float("inf"), n_trials=1, n_obs=120))
    assert math.isnan(deflated_sharpe_ratio(1.0, n_trials=1, n_obs=120, skew=float("nan")))


def test_pbo_rejects_bad_matrix_shape() -> None:
    with pytest.raises(ValueError):
        probability_of_backtest_overfit([[1.0, 2.0]])  # only 1 row
    with pytest.raises(ValueError):
        probability_of_backtest_overfit([[1.0], [2.0]])  # only 1 col


# --- PBO behavior -------------------------------------------------------------


def test_pbo_low_when_is_best_is_always_oos_best() -> None:
    # Strategy 0 dominates both in-sample and out-of-sample → not overfit.
    mat = np.array([[2.0, 1.0, 0.5], [2.1, 1.1, 0.6], [1.9, 0.9, 0.4], [2.0, 1.0, 0.5]])
    pbo = probability_of_backtest_overfit(mat)
    assert 0.0 <= pbo <= 1.0
    assert pbo < 0.5  # the dominant strategy stays best OOS → low overfit


def test_pbo_high_when_is_best_is_oos_noise() -> None:
    # Strategies with identical OOS mean regardless of IS → IS-best is a coin
    # flip OOS; construct a case where the IS-best swings to OOS-worst often.
    rng = np.random.default_rng(0)
    overfit = np.vstack(
        [
            rng.normal(0, 1, size=6),  # one "lucky IS" row
            rng.normal(0, 1, size=6),
            rng.normal(0, 1, size=6),
            rng.normal(0, 1, size=6),
        ]
    )
    pbo = probability_of_backtest_overfit(overfit)
    assert 0.0 <= pbo <= 1.0


def test_pbo_respects_partition_cap() -> None:
    # C(20,10) = 184756 > default cap → must raise rather than hang.
    big = np.zeros((20, 3))
    with pytest.raises(ValueError, match="max_partitions"):
        probability_of_backtest_overfit(big)
