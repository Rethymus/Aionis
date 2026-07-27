"""Inference-metric invariants: HLN Diebold-Mariano + the moving-block-bootstrap
DM complement.

The MBB DM (``diebold_mariano_mbb``) is the small-n robustness check on the
analytic HLN/Student-t DM. Tests pin null calibration, power, agreement with the
analytic test on the same cases, determinism, the degenerate guard, and the
block-structure property (a block length > 1 must be no less conservative than
an iid/block-1 bootstrap on autocorrelated data).
"""

from __future__ import annotations

import numpy as np

from aionis.eval.metrics import diebold_mariano, diebold_mariano_mbb


def _from_diff(d: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build (loss_a, loss_b, groups) from a per-cluster differential series.

    One cluster per element, in sequence order — so autocorrelation in ``d`` is
    preserved for the block-structure test.
    """
    n = len(d)
    return np.asarray(d, float), np.zeros(n), np.arange(n)


# --- null calibration ---------------------------------------------------------


def test_mbb_null_is_calibrated_iid() -> None:
    """Under H0 (iid zero-mean differential) the p-value should usually be > 0.05."""
    rng = np.random.default_rng(0)
    passes = 0
    for _ in range(5):
        d = rng.standard_normal(44)
        p = diebold_mariano_mbb(*_from_diff(d), horizon=1, seed=7)["p_value"]
        passes += int(p > 0.05)
    assert passes >= 4  # under H0, P(p > 0.05) = 0.95 per draw


# --- power --------------------------------------------------------------------


def test_mbb_detects_a_real_edge() -> None:
    rng = np.random.default_rng(1)
    d = 0.5 + 0.1 * rng.standard_normal(44)  # large positive differential
    res = diebold_mariano_mbb(*_from_diff(d), horizon=1, seed=7)
    assert res["p_value"] < 0.01
    assert res["stat"] > 0


# --- agreement with the analytic HLN DM ---------------------------------------


def test_mbb_agrees_with_analytic_dm_on_null_and_power() -> None:
    rng = np.random.default_rng(2)
    null_d = rng.standard_normal(44)
    p_mbb_null = diebold_mariano_mbb(*_from_diff(null_d), horizon=1)["p_value"]
    p_ana_null = diebold_mariano(*_from_diff(null_d), horizon=1)["p_value"]
    assert (p_mbb_null > 0.05) == (p_ana_null > 0.05)

    rng = np.random.default_rng(3)
    power_d = 0.5 + 0.1 * rng.standard_normal(44)
    p_mbb_pow = diebold_mariano_mbb(*_from_diff(power_d), horizon=1)["p_value"]
    p_ana_pow = diebold_mariano(*_from_diff(power_d), horizon=1)["p_value"]
    assert (p_mbb_pow < 0.05) == (p_ana_pow < 0.05)


# --- determinism --------------------------------------------------------------


def test_mbb_deterministic_under_fixed_seed() -> None:
    rng = np.random.default_rng(4)
    d = rng.standard_normal(44)
    r1 = diebold_mariano_mbb(*_from_diff(d), horizon=1, seed=11)
    r2 = diebold_mariano_mbb(*_from_diff(d), horizon=1, seed=11)
    assert r1 == r2


# --- degenerate guard ---------------------------------------------------------


def test_mbb_degenerate_too_few_clusters() -> None:
    res = diebold_mariano_mbb(*_from_diff(np.array([0.1, 0.2, 0.3])), horizon=1)
    assert res["p_value"] == 1.0
    assert res["flag"] == "degenerate"


def test_mbb_degenerate_zero_variance() -> None:
    res = diebold_mariano_mbb(*_from_diff(np.full(20, 0.5)), horizon=1)
    assert res["p_value"] == 1.0
    assert res["flag"] == "degenerate"


# --- block structure: MBB is no less conservative than iid on autocorrelation --


def test_mbb_block_len_more_conservative_than_iid_on_autocorrelated_data() -> None:
    """Strongly autocorrelated H0 differential: an iid (block-1) bootstrap is
    anti-conservative (ignores the inflated variance of the mean); a block
    length > 1 must give a p-value at least as large."""
    rng = np.random.default_rng(5)
    n = 60
    rho = 0.9
    e = rng.standard_normal(n)
    d = np.empty(n)
    d[0] = e[0]
    for t in range(1, n):  # AR(1), mean zero -> H0
        d[t] = rho * d[t - 1] + e[t]

    p_block = diebold_mariano_mbb(*_from_diff(d), horizon=1, block_len=8, seed=7)["p_value"]
    p_iid = diebold_mariano_mbb(*_from_diff(d), horizon=1, block_len=1, seed=7)["p_value"]
    assert p_block >= p_iid


# --- block_len >= n: only one block, zero resampling variation -----------------


def test_mbb_underpowered_when_block_len_ge_n() -> None:
    """When block_len >= n there is a single block (the whole series), so every
    resample is identical and t_star is identically 0. The bootstrap cannot
    calibrate a p-value; it must report underpowered (p=1.0), NOT a misleading
    1/(n_boot+1) ~= 0.0005 flagged "ok"."""
    rng = np.random.default_rng(6)
    d = 0.5 + 0.1 * rng.standard_normal(10)  # strong signal, 10 clusters
    # horizon = n forces bl = max(10, ceil(10**(1/3))) = 10 = n -> one block.
    res = diebold_mariano_mbb(*_from_diff(d), horizon=10)
    assert res["p_value"] == 1.0
    assert res["flag"] == "underpowered"
    # An explicit oversized block_len is clamped to n and hits the same guard.
    res2 = diebold_mariano_mbb(*_from_diff(d), horizon=1, block_len=20)
    assert res2["p_value"] == 1.0
    assert res2["flag"] == "underpowered"
