"""Hermetic tests for the model-drift display utility (leakage-safe)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from aionis.eval.model_drift import (
    _monthly_rank_ic,
    _psi,
    compute_drift,
    drift_summary,
)

_RNG = np.random.default_rng(0)


def _pairs(scores: np.ndarray, fwd: np.ndarray, months: list[str]) -> pd.DataFrame:
    """Build a realized (date, ticker, score, forward_return_h, realized_up) frame."""
    dates: list[pd.Timestamp] = []
    tickers: list[str] = []
    sc: list[float] = []
    fr: list[float] = []
    n_per = len(scores) // len(months)
    for i, m in enumerate(months):
        ts = pd.Timestamp(f"{m}-15")
        for j in range(n_per):
            idx = i * n_per + j
            dates.append(ts)
            tickers.append(f"T{j:04d}")
            sc.append(float(scores[idx]))
            fr.append(float(fwd[idx]))
    df = pd.DataFrame({"date": dates, "ticker": tickers, "score": sc, "forward_return_h": fr})
    df["realized_up"] = (df["forward_return_h"] > 0).astype("Int64")
    return df


# --- PSI correctness ----------------------------------------------------------


def test_psi_identical_distribution_is_near_zero() -> None:
    ref = pd.Series(_RNG.normal(0, 1, 2000))
    sample = pd.Series(_RNG.normal(0, 1, 500))
    assert _psi(ref, sample) < 0.05  # same dist → tiny PSI


def test_psi_shifted_distribution_is_large() -> None:
    ref = pd.Series(_RNG.normal(0, 1, 2000))
    shifted = pd.Series(_RNG.normal(1.0, 1, 500))  # clear mean shift
    assert _psi(ref, shifted) > 0.25  # significant drift


def test_psi_constant_distribution_returns_zero() -> None:
    # Degenerate: constant scores have no distribution to compare.
    assert _psi(pd.Series([3.0] * 100), pd.Series([3.0] * 50)) == 0.0


# --- monthly rank-IC ----------------------------------------------------------


def test_monthly_rank_ic_positive_for_correlated_score_fwd() -> None:
    # Arrange: score positively predicts forward return.
    score = _RNG.normal(0, 1, 400)
    fwd = score * 0.5 + _RNG.normal(0, 0.1, 400)
    df = _pairs(score, fwd, ["2023-01", "2023-02", "2023-03", "2023-04"])
    # Act + Assert
    assert _monthly_rank_ic(df) > 0.5


def test_monthly_rank_ic_negative_for_anti_correlated() -> None:
    score = _RNG.normal(0, 1, 400)
    fwd = -score * 0.5 + _RNG.normal(0, 0.1, 400)
    df = _pairs(score, fwd, ["2023-01", "2023-02", "2023-03", "2023-04"])
    assert _monthly_rank_ic(df) < -0.5


def test_monthly_rank_ic_zero_for_noise() -> None:
    score = _RNG.normal(0, 1, 400)
    fwd = _RNG.normal(0, 1, 400)  # independent
    df = _pairs(score, fwd, ["2023-01", "2023-02", "2023-03", "2023-04"])
    assert abs(_monthly_rank_ic(df)) < 0.20  # null model band


# --- anti-leakage: unrealized latest month excluded ---------------------------


def test_compute_drift_excludes_unrealized_latest_month() -> None:
    # Arrange: 12 months × 50 tickers. Month 12 is UNREALIZED (NaN fwd).
    # Realized = months 1–11 (550 rows); recent_months=3 → recent M9–M11 (150),
    # history M1–M8 (400). M12's 50 rows must be excluded entirely.
    months = [f"2023-{m:02d}" for m in range(1, 13)]
    score = _RNG.normal(0, 1, 12 * 50)
    fwd = _RNG.normal(0, 1, 12 * 50)
    dates: list[pd.Timestamp] = []
    tickers: list[str] = []
    sc: list[float] = []
    fr: list[float] = []
    for i, m in enumerate(months):
        ts = pd.Timestamp(f"{m}-15")
        for j in range(50):
            idx = i * 50 + j
            dates.append(ts)
            tickers.append(f"T{j:04d}")
            sc.append(float(score[idx]))
            # last month unrealized:
            fr.append(float("nan") if i == 11 else float(fwd[idx]))
    panel = pd.DataFrame({"date": dates, "ticker": tickers, "forward_return_h": fr})
    oos = pd.DataFrame(
        {"date": dates, "ticker": tickers, "region": "us", "score": sc}
    )

    # Act
    meta = compute_drift(oos, panel, "us", recent_months=3)

    # Assert: M12's 50 unrealized rows are excluded → 550 realized rows used.
    assert meta is not None
    assert meta.n_history + meta.n_recent == 550


def test_compute_drift_regime_thresholds_track_psi() -> None:
    # Stable when distributions match; the regime string must follow PSI band.
    score = _RNG.normal(0, 1, 3000)
    fwd = _RNG.normal(0, 1, 3000)
    months = [f"2022-{m:02d}" for m in range(1, 13)] + [f"2023-{m:02d}" for m in range(1, 7)]
    df = _pairs(score, fwd, months)
    panel = df.rename(columns={"realized_up": "_drop"})[["date", "ticker", "forward_return_h"]]
    oos = df.assign(region="us")[["date", "ticker", "region", "score"]]
    meta = compute_drift(oos, panel, "us", recent_months=3)
    assert meta is not None
    if meta.psi < 0.1:
        assert meta.regime == "stable"
    elif meta.psi < 0.25:
        assert meta.regime == "moderate"
    else:
        assert meta.regime == "significant"


# --- degeneracy: insufficient data → graceful skip ---------------------------


def test_compute_drift_returns_none_for_insufficient_history() -> None:
    score = _RNG.normal(0, 1, 40)  # < _MIN_HISTORY
    fwd = _RNG.normal(0, 1, 40)
    df = _pairs(score, fwd, ["2023-01", "2023-02"])
    panel = df[["date", "ticker", "forward_return_h"]]
    oos = df.assign(region="us")[["date", "ticker", "region", "score"]]
    assert compute_drift(oos, panel, "us") is None


def test_compute_drift_returns_none_for_empty_panel() -> None:
    oos = pd.DataFrame({"date": [], "ticker": [], "region": [], "score": []})
    panel = pd.DataFrame({"date": [], "ticker": [], "forward_return_h": []})
    assert compute_drift(oos, panel, "us") is None


def test_drift_summary_skips_regions_with_insufficient_data() -> None:
    # Arrange: a US panel with enough history; a CN panel that is empty.
    score = _RNG.normal(0, 1, 3000)
    fwd = _RNG.normal(0, 1, 3000)
    months = [f"2022-{m:02d}" for m in range(1, 13)] + [f"2023-{m:02d}" for m in range(1, 7)]
    df = _pairs(score, fwd, months)
    us_panel = df[["date", "ticker", "forward_return_h"]]
    oos = df.assign(region="us")[["date", "ticker", "region", "score"]]
    cn_panel = pd.DataFrame({"date": [], "ticker": [], "forward_return_h": []})

    # Act
    summary = drift_summary(oos, us_panel, cn_panel, recent_months=3)

    # Assert: US present, CN skipped (no crash).
    assert "us" in summary["regions"]
    assert "cn" not in summary["regions"]
    assert summary["regions"]["us"]["region"] == "us"
    assert summary["methodology"]  # non-empty disclosure
