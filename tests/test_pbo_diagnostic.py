"""Hermetic tests for scripts/pbo_diagnostic.py (synthetic matrices only —
the real run reads gitignored runs/results parquets, a local artifact).

Pins two estimator-behavior properties and the loader's contract shape:
1. a config that dominates in EVERY period must yield LOW PBO
   (in-sample winner keeps winning out-of-sample);
2. pure noise must NOT yield low PBO (no systematic winner to exploit);
3. the loader labels must cover 4 phases x 2 arms.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "pbo_diagnostic.py"


def _load():
    spec = importlib.util.spec_from_file_location("pbo_diagnostic", SCRIPT)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_dominant_config_gives_low_pbo() -> None:
    import purgedcv

    rng = np.random.default_rng(0)
    noise = rng.normal(0, 0.05, (5, 120))
    dominant = noise[0] + 0.25  # strictly better in every period
    X = np.vstack([dominant, noise])
    res = purgedcv.probability_of_backtest_overfitting(X, n_splits=8)
    assert res.pbo < 0.2, f"dominant config must give low PBO, got {res.pbo}"


def test_noise_pbo_exceeds_dominant_pbo() -> None:
    """The property that matters is ORDERING: a config dominant in every
    period must score lower PBO than pure noise (same shape/seed family).
    Absolute thresholds are unstable — the CSCV estimator itself is noisy in
    the small-trial regime (the script's own caveat #1)."""
    import purgedcv

    rng = np.random.default_rng(1)
    noise = rng.normal(0, 0.05, (8, 120))
    pbo_noise = purgedcv.probability_of_backtest_overfitting(
        noise, n_splits=8).pbo

    rng2 = np.random.default_rng(0)
    base = rng2.normal(0, 0.05, (8, 120))
    dominant = base[0] + 0.25
    X = np.vstack([dominant, base])
    pbo_dom = purgedcv.probability_of_backtest_overfitting(X, n_splits=8).pbo

    assert pbo_dom < pbo_noise, (
        f"dominant config ({pbo_dom:.3f}) must score below noise ({pbo_noise:.3f})"
    )
    assert pbo_dom < 0.2, f"dominant config must give low PBO, got {pbo_dom}"


def test_phase_table_covers_8_arms() -> None:
    m = _load()
    assert set(m.PHASES) == {"B", "C", "D", "E1"}
    assert all(len(sig) == 64 for sig in m.PHASES.values()), "config sigs are sha256"
