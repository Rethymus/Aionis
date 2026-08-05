"""Hermetic tests for the pure-noise bound (scripts.ic_pure_noise_bound).

Covers the closed-form Spearman null bound and the cross-section-size helper.
Deterministic; no network/real data.
"""
from __future__ import annotations

import importlib
import math

import pandas as pd
import pytest

pn = importlib.import_module("scripts.ic_pure_noise_bound")


# --- pure_noise_sigma: closed-form 1/sqrt(N-1) ---


def test_pure_noise_sigma_matches_closed_form() -> None:
    """sigma_null = 1/sqrt(N-1) for the Spearman null (exact, not asymptotic)."""
    for n in (2, 10, 100, 462, 500, 929, 1386):
        assert pn.pure_noise_sigma(n) == pytest.approx(1.0 / math.sqrt(n - 1))


def test_pure_noise_sigma_decreases_with_n() -> None:
    """Larger cross-section -> tighter pure-noise bound (monotone decreasing)."""
    assert pn.pure_noise_sigma(100) > pn.pure_noise_sigma(500) > pn.pure_noise_sigma(1386)


def test_pure_noise_sigma_known_values() -> None:
    """Spot-check canonical N -> sigma values used in the note."""
    assert pn.pure_noise_sigma(462) == pytest.approx(0.0466, abs=1e-4)
    assert pn.pure_noise_sigma(100) == pytest.approx(0.1005, abs=1e-4)
    assert pn.pure_noise_sigma(500) == pytest.approx(0.0448, abs=1e-4)


def test_pure_noise_sigma_too_small_returns_nan() -> None:
    """N < 2 has no defined Spearman variance -> NaN (no false precision)."""
    assert math.isnan(pn.pure_noise_sigma(1))
    assert math.isnan(pn.pure_noise_sigma(0))


# --- _n_cross_eff: per-month median cross-section size ---


def test_n_cross_eff_median_and_per_region() -> None:
    """Median tickers/month overall and per-region; min=1 edge case handled by median."""
    # 3 months: month 2 has only 1 ticker (edge), median is robust
    df = pd.DataFrame({
        "date": pd.to_datetime(["2020-01-31"] * 4 + ["2020-02-29"] * 1 + ["2020-03-31"] * 5),
        "ticker": list("ABCD") + ["Z"] + list("EFGHI"),
        "region": (["us"] * 2 + ["cn"] * 2) + ["us"] + (["us"] * 3 + ["cn"] * 2),
    })
    out = pn._n_cross_eff(df)
    # per-month unique tickers: 4, 1, 5 -> median 4
    assert out["n_cross_median"] == 4.0
    assert out["n_cross_min"] == 1
    assert out["n_cross_max"] == 5
    # per-region median: us months = [2, 1, 3] -> median 2; cn months = [2, -, 2] -> median 2
    assert out["n_cross_per_region"]["us"] == 2.0
    assert out["n_cross_per_region"]["cn"] == 2.0


def test_n_cross_eff_missing_columns_returns_empty() -> None:
    """A panel without date/ticker yields no cross-section stats."""
    out = pn._n_cross_eff(pd.DataFrame({"score": [1.0, 2.0]}))
    assert out == {}
