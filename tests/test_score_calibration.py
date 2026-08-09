"""Hermetic tests for ``aionis.eval.score_calibration``.

Synthetic data only — no real panels, no network. Locks the anti-leakage
contract (latest month excluded from fit), the monotonicity invariant
(calibrated prob preserves score rank), the null-visibility signal
(prob range tight around base_rate when score has no signal), and the
NaN/edge guards.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aionis.eval.score_calibration import (
    build_pair_frame,
    calibrate_latest_month,
    calibrate_walk_forward,
    fit_region,
    meta_to_jsonable,
)

RNG = np.random.default_rng(0)


def _toy_oos(n_months: int = 40, n_tickers: int = 30, region: str = "us") -> pd.DataFrame:
    """Deterministic OOS panel: date, ticker, region, score (pure noise)."""
    rows = []
    for m in range(n_months):
        date = pd.Timestamp("2022-01-01") + pd.DateOffset(months=m)
        for t in range(n_tickers):
            rows.append(
                {
                    "date": date,
                    "ticker": f"{region}{t:03d}",
                    "region": region,
                    "score": float(RNG.standard_normal()),
                }
            )
    return pd.DataFrame(rows)


def _toy_panel(oos: pd.DataFrame, signal: float = 0.0) -> pd.DataFrame:
    """Panel with forward_return_h. ``signal`` controls how much score predicts up.

    signal=0.0 ⇒ pure noise (null); signal=0.8 ⇒ score strongly predicts up.
    Latest month gets NaN fwd_return (unrealized) — anti-leakage contract.
    """
    oos = oos.copy()
    latest = oos["date"].max()
    oos["forward_return_h"] = RNG.standard_normal(len(oos)) + signal * oos["score"]
    oos.loc[oos["date"] == latest, "forward_return_h"] = np.nan
    return oos[["date", "ticker", "forward_return_h"]]


# --- fit_region ---------------------------------------------------------------


def test_fit_region_monotonic_in_score() -> None:
    """Higher score ⇒ weakly higher P(up). Isotonic preserves rank."""
    scores = np.linspace(-3, 3, 200)
    realized = (scores + RNG.standard_normal(200) > 0).astype(int)
    cr = fit_region(scores, realized, "us")
    probs = cr.predict_proba(np.array([-2.0, 0.0, 2.0]))
    assert probs[0] <= probs[1] <= probs[2], "calibration must be monotonic"


def test_fit_region_null_signal_prob_range_tight_around_base_rate() -> None:
    """Platt on a null model collapses to a near-flat curve tightly around base_rate.

    This is the load-bearing 'honest null' signal: a 2-param sigmoid cannot
    manufacture discrimination, so on noise it produces a narrow band around
    the empirical base rate. (Isotonic, in contrast, overfits noise — which is
    exactly why Platt is the default.)
    """
    scores = RNG.standard_normal(2000)
    realized = RNG.integers(0, 2, 2000)  # pure noise, base_rate ≈ 0.5
    cr = fit_region(scores, realized, "us", method="platt")
    spread = cr.meta.prob_max - cr.meta.prob_min
    assert cr.meta.base_rate == pytest.approx(0.5, abs=0.05)
    assert spread < 0.10, f"platt on null should produce tight prob range, got spread={spread:.3f}"


def test_fit_region_isotonic_overfits_noise_wider_than_platt() -> None:
    """Isotonic on noise wanders more than Platt — the reason Platt is default."""
    scores = RNG.standard_normal(2000)
    realized = RNG.integers(0, 2, 2000)
    cr_iso = fit_region(scores, realized, "us", method="isotonic")
    cr_platt = fit_region(scores, realized, "us", method="platt")
    spread_iso = cr_iso.meta.prob_max - cr_iso.meta.prob_min
    spread_platt = cr_platt.meta.prob_max - cr_platt.meta.prob_min
    assert spread_iso > spread_platt


def test_fit_region_strong_signal_widens_prob_range() -> None:
    """When score strongly predicts up, both methods must spread widely."""
    scores = np.linspace(-3, 3, 2000)
    realized = (scores > 0).astype(int)  # near-perfect discrimination
    cr = fit_region(scores, realized, "us", method="platt")
    assert cr.meta.prob_min < 0.15
    assert cr.meta.prob_max > 0.85


def test_fit_region_rejects_insufficient_pairs() -> None:
    with pytest.raises(ValueError, match="Insufficient"):
        fit_region(np.array([1.0, 2.0]), np.array([0, 1]), "us")


def test_fit_region_drops_nan_and_inf() -> None:
    scores = np.array([np.nan, np.inf, 1.0, 2.0, 3.0] * 10)
    realized = np.array([1, 0, 1, 0, 1] * 10)
    cr = fit_region(scores, realized, "us")
    assert cr.meta.n_pairs == 30  # 50 raw − 20 NaN/Inf


def test_predict_proba_scalar_returns_float() -> None:
    scores = np.linspace(-2, 2, 100)
    realized = (scores > 0).astype(int)
    cr = fit_region(scores, realized, "us")
    out = cr.predict_proba(1.5)
    assert isinstance(out, float)
    assert 0.0 <= out <= 1.0


# --- build_pair_frame ---------------------------------------------------------


def test_build_pair_frame_inner_join_drops_non_matching() -> None:
    oos = pd.DataFrame(
        {
            "date": pd.to_datetime(["2022-01-01", "2022-01-01", "2022-02-01"]),
            "ticker": ["A", "B", "A"],
            "region": ["us", "us", "us"],
            "score": [0.5, -0.5, 1.0],
        }
    )
    panel = pd.DataFrame(
        {
            "date": pd.to_datetime(["2022-01-01", "2022-01-01"]),
            "ticker": ["A", "B"],
            "forward_return_h": [0.01, -0.02],
        }
    )
    out = build_pair_frame(oos, panel, "us")
    assert len(out) == 2
    assert set(out["ticker"]) == {"A", "B"}
    assert out["realized_up"].tolist() == [1, 0]


def test_build_pair_frame_keeps_nan_fwd_return_for_anti_leakage_audit() -> None:
    """NaN fwd_return rows are KEPT (not silently dropped) so calibrate_latest_month
    can exclude them by date and the audit trail is intact."""
    oos = pd.DataFrame(
        {
            "date": pd.to_datetime(["2022-01-01", "2022-02-01"]),
            "ticker": ["A", "A"],
            "region": ["us", "us"],
            "score": [0.5, 1.0],
        }
    )
    panel = pd.DataFrame(
        {
            "date": pd.to_datetime(["2022-01-01", "2022-02-01"]),
            "ticker": ["A", "A"],
            "forward_return_h": [0.01, np.nan],
        }
    )
    out = build_pair_frame(oos, panel, "us")
    assert len(out) == 2
    assert out["forward_return_h"].isna().sum() == 1


# --- calibrate_latest_month (anti-leakage integration) ------------------------


def test_calibrate_latest_month_excludes_latest_from_fit() -> None:
    """The latest month's NaN fwd_return must NOT enter the fit."""
    oos = _toy_oos(n_months=40, n_tickers=30, region="us")
    panel = _toy_panel(oos, signal=0.0)
    out = calibrate_latest_month(oos, us_panel=panel, cn_panel=pd.DataFrame())
    us = out["regions"]["us"]
    # 40 months × 30 tickers = 1200; latest excluded → 39 × 30 = 1170 fit pairs
    assert us["meta"].n_pairs == 39 * 30


def test_calibrate_latest_month_predicts_latest_tickers() -> None:
    oos = _toy_oos(n_months=40, n_tickers=30, region="us")
    panel = _toy_panel(oos, signal=0.5)
    out = calibrate_latest_month(oos, us_panel=panel, cn_panel=pd.DataFrame())
    latest = out["regions"]["us"]["latest"]
    assert len(latest) == 30
    assert {"ticker", "score", "prob_up"} <= set(latest.columns)
    assert latest["prob_up"].between(0.0, 1.0).all()


def test_calibrate_latest_month_skips_region_with_too_few_pairs() -> None:
    """If a region has <30 realized pairs, it's silently skipped (not crashed)."""
    oos = _toy_oos(n_months=2, n_tickers=10, region="us")  # only 1 history month = 10 pairs
    panel = _toy_panel(oos, signal=0.5)
    out = calibrate_latest_month(oos, us_panel=panel, cn_panel=pd.DataFrame())
    assert "us" not in out["regions"]


def test_calibrate_latest_month_walk_forward_disclosed_false() -> None:
    oos = _toy_oos(n_months=40, n_tickers=30, region="us")
    panel = _toy_panel(oos, signal=0.5)
    out = calibrate_latest_month(oos, us_panel=panel, cn_panel=pd.DataFrame())
    assert out["walk_forward"] is False
    assert out["regions"]["us"]["meta"].walk_forward is False


def test_calibrate_latest_month_handles_both_regions() -> None:
    us_oos = _toy_oos(n_months=40, n_tickers=30, region="us")
    cn_oos = _toy_oos(n_months=40, n_tickers=30, region="cn")
    oos = pd.concat([us_oos, cn_oos], ignore_index=True)
    us_panel = _toy_panel(us_oos, signal=0.3)
    cn_panel = _toy_panel(cn_oos, signal=0.0)  # null signal in CN
    out = calibrate_latest_month(oos, us_panel=us_panel, cn_panel=cn_panel)
    assert set(out["regions"]) == {"us", "cn"}
    us_spread = out["regions"]["us"]["meta"].prob_max - out["regions"]["us"]["meta"].prob_min
    cn_spread = out["regions"]["cn"]["meta"].prob_max - out["regions"]["cn"]["meta"].prob_min
    assert us_spread > cn_spread, "US (signal=0.3) should spread more than CN (signal=0.0)"


# --- meta_to_jsonable ---------------------------------------------------------


def test_meta_to_jsonable_round_trips_through_json() -> None:
    import json

    cr = fit_region(np.linspace(-2, 2, 100), (np.linspace(-2, 2, 100) > 0).astype(int), "us")
    js = meta_to_jsonable(cr.meta)
    s = json.dumps(js)  # must not raise
    assert json.loads(s)["region"] == "us"
    assert set(js) >= {"region", "n_pairs", "base_rate", "ece", "brier", "prob_min", "prob_max"}


# --- calibrate_walk_forward (display, leakage-safe) ---------------------------


def test_calibrate_walk_forward_excludes_target_month_from_fit() -> None:
    """Anti-leakage: month T's fit uses only months strictly before T."""
    oos = _toy_oos(n_months=20, n_tickers=30, region="us")
    panel = _toy_panel(oos, signal=0.5)
    out = calibrate_walk_forward(oos, us_panel=panel, cn_panel=pd.DataFrame(), min_train_months=12)
    series = out["regions"]["us"]["series"]
    # First target = month index 12 → train = months 0..11 = 12 × 30 = 360 pairs.
    assert series[0]["n_train_pairs"] == 12 * 30
    # Each later target grows the training window by exactly one month (30 pairs).
    assert series[1]["n_train_pairs"] == 13 * 30
    assert series[-1]["n_train_pairs"] == (len(series) - 1 + 12) * 30


def test_calibrate_walk_forward_disclosed_true() -> None:
    oos = _toy_oos(n_months=20, n_tickers=30, region="us")
    panel = _toy_panel(oos, signal=0.5)
    out = calibrate_walk_forward(oos, us_panel=panel, cn_panel=pd.DataFrame(), min_train_months=12)
    assert out["walk_forward"] is True


def test_calibrate_walk_forward_strong_signal_reliability_monotone() -> None:
    """Strong score→up signal: reliability endpoints rise (low bin < high bin)."""
    oos = _toy_oos(n_months=24, n_tickers=60, region="us")
    panel = _toy_panel(oos, signal=1.2)
    out = calibrate_walk_forward(oos, us_panel=panel, cn_panel=pd.DataFrame(), min_train_months=12)
    us = out["regions"]["us"]
    bins = [b for b in us["pooled_reliability"] if b["n"] > 0]
    assert bins[0]["emp_freq"] < bins[-1]["emp_freq"], "reliability rises across bins"
    # Signal present ⇒ latest month's prob range spreads wide (not collapsed at 0.5).
    last = us["series"][-1]
    assert (last["prob_max"] - last["prob_min"]) > 0.10


def test_calibrate_walk_forward_null_signal_keeps_prob_range_tight() -> None:
    """Null signal: Platt collapses to a tight band around base rate (honest null)."""
    oos = _toy_oos(n_months=24, n_tickers=60, region="us")
    panel = _toy_panel(oos, signal=0.0)
    out = calibrate_walk_forward(oos, us_panel=panel, cn_panel=pd.DataFrame(), min_train_months=12)
    last = out["regions"]["us"]["series"][-1]
    assert (last["prob_max"] - last["prob_min"]) < 0.15


def test_calibrate_walk_forward_deterministic_across_calls() -> None:
    """H6-style determinism: identical inputs ⇒ identical output dict."""
    oos = _toy_oos(n_months=20, n_tickers=30, region="us")
    panel = _toy_panel(oos, signal=0.5)
    a = calibrate_walk_forward(oos, us_panel=panel, cn_panel=pd.DataFrame(), min_train_months=12)
    b = calibrate_walk_forward(oos, us_panel=panel, cn_panel=pd.DataFrame(), min_train_months=12)
    assert a == b


def test_calibrate_walk_forward_skips_region_with_too_few_months() -> None:
    """Fewer realized months than min_train_months → region silently omitted."""
    oos = _toy_oos(n_months=5, n_tickers=30, region="us")
    panel = _toy_panel(oos, signal=0.5)
    out = calibrate_walk_forward(oos, us_panel=panel, cn_panel=pd.DataFrame(), min_train_months=12)
    assert "us" not in out["regions"]


def test_calibrate_walk_forward_handles_both_regions() -> None:
    us_oos = _toy_oos(n_months=20, n_tickers=30, region="us")
    cn_oos = _toy_oos(n_months=20, n_tickers=30, region="cn")
    oos = pd.concat([us_oos, cn_oos], ignore_index=True)
    us_panel = _toy_panel(us_oos, signal=0.8)
    cn_panel = _toy_panel(cn_oos, signal=0.0)  # null in CN
    out = calibrate_walk_forward(oos, us_panel=us_panel, cn_panel=cn_panel, min_train_months=12)
    assert set(out["regions"]) == {"us", "cn"}
    us_last = out["regions"]["us"]["series"][-1]
    cn_last = out["regions"]["cn"]["series"][-1]
    us_spread = us_last["prob_max"] - us_last["prob_min"]
    cn_spread = cn_last["prob_max"] - cn_last["prob_min"]
    assert us_spread > cn_spread, "US (signal=0.8) should spread more than CN (signal=0.0)"


def test_calibrate_walk_forward_jsonable() -> None:
    """The output must survive json.dumps (terminal export contract)."""
    import json

    oos = _toy_oos(n_months=20, n_tickers=30, region="us")
    panel = _toy_panel(oos, signal=0.5)
    out = calibrate_walk_forward(oos, us_panel=panel, cn_panel=pd.DataFrame(), min_train_months=12)
    s = json.dumps(out, default=str)  # must not raise
    assert "pooled_reliability" in json.loads(s)["regions"]["us"]
