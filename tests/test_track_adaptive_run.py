"""Hermetic tests for the Track Adaptive weekly runner (leakage boundaries)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import track_adaptive_run as ta  # noqa: E402

_FEATURES = ta.FEATURES


def _syn_daily(n_days: int = 40, n_tickers: int = 12) -> pd.DataFrame:
    """Tiny synthetic DAILY panel with all feature cols (random) + close."""
    rng = np.random.default_rng(0)
    sessions = pd.bdate_range("2020-01-01", periods=n_days)  # business days
    rows = []
    for t in range(n_tickers):
        close = 100.0 * np.exp(np.cumsum(rng.normal(0, 0.01, n_days)))
        for i, d in enumerate(sessions):
            row = {"date": d, "ticker": f"T{t:02d}", "close": close[i]}
            for f in _FEATURES:
                row[f] = float(rng.normal(0, 1))
            rows.append(row)
    return pd.DataFrame(rows)


# --- helpers -----------------------------------------------------------------


def test_weekly_reduce_one_row_per_iso_week() -> None:
    daily = _syn_daily(n_days=30)
    w = ta.weekly_reduce(daily)
    assert w["week_id"].is_monotonic_increasing
    assert w.groupby("week_id").size().eq(12).all()  # one row per ticker per week
    assert "fwd_5s" in w.columns


def test_fit_binner_and_to_relevance_round_trip() -> None:
    rng = np.random.default_rng(1)
    fwd = pd.Series(rng.normal(0, 1, 1000))
    edges = ta.fit_binner(fwd, n_bins=5)
    rel = ta.to_relevance(fwd.to_numpy(), edges)
    assert rel.min() >= 0 and rel.max() <= 4
    assert set(np.unique(rel)) >= {0, 4}  # spans the range


def test_week_group_sizes_sum_to_rows() -> None:
    weekly_ids = np.array([1, 1, 1, 2, 2, 3])  # 3 groups
    sizes = ta.week_group_sizes(weekly_ids)
    assert sizes.tolist() == [3, 2, 1]
    assert sizes.sum() == len(weekly_ids)


def test_hac_mean_recovers_known_mean_within_tolerance() -> None:
    rng = np.random.default_rng(2)
    s = pd.Series(rng.normal(0.01, 0.1, 500))
    out = ta.hac_mean(s)
    # hac_mean rounds the display to 6 decimals — tolerance accounts for that.
    assert abs(out["mean"] - s.mean()) < 5e-7
    assert out["n"] == 500
    assert out["se"] > 0


# --- anti-leakage: frozen fit must EXCLUDE all OOS rows ----------------------


def test_frozen_arm_train_excludes_oos(monkeypatch: pytest.MonkeyPatch) -> None:
    daily = _syn_daily(n_days=60)
    weekly = ta.weekly_reduce(daily)
    train_end = weekly["date"].iloc[20]  # an interior date as the frozen cutoff
    edges = ta.fit_binner(weekly.loc[weekly["date"] <= train_end, "fwd_5s"])

    captured: dict = {}

    class _Stub:
        def __init__(self, params: dict) -> None:
            self.params = params

        def fit_predict_rank(self, train, test, feats, rel, groups):  # noqa: ANN001
            captured["train"] = train
            return pd.Series(np.zeros(len(test)), index=test.index, name="score")

    monkeypatch.setattr(ta, "LightGBMFrozen", _Stub)
    ta.run_frozen_arm(weekly, str(train_end.date()), _FEATURES, edges)
    assert captured["train"]["date"].max() <= pd.Timestamp(train_end)


# --- anti-leakage: expanding embargo — train strictly before predict minus 5 --


def test_expanding_arm_embargo_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    daily = _syn_daily(n_days=80)
    daily_sessions = np.sort(pd.to_datetime(daily["date"]).unique())
    weekly = ta.weekly_reduce(daily)
    edges = ta.fit_binner(weekly["fwd_5s"])

    captured: list = []

    class _Stub:
        def __init__(self, params: dict) -> None:
            self.params = params

        def fit_predict_rank(self, train, test, feats, rel, groups):  # noqa: ANN001
            captured.append({"train_max": train["date"].max(), "test_date": test["date"].iloc[0]})
            return pd.Series(np.zeros(len(test)), index=test.index, name="score")

    monkeypatch.setattr(ta, "LightGBMFrozen", _Stub)
    ta.MIN_TRAIN_ROWS = 20  # small synthetic panel
    ta.run_expanding_arm(weekly, daily_sessions, _FEATURES, edges, embargo=5)

    sess = pd.DatetimeIndex(daily_sessions)
    for c in captured:
        # train_max must be <= (test_date's session index − embargo)
        idx_test = sess.get_loc(pd.Timestamp(c["test_date"]))
        cutoff = sess[max(idx_test - 5, 0)]
        assert pd.Timestamp(c["train_max"]) <= pd.Timestamp(cutoff), (
            f"embargo leak: train {c['train_max']} > cutoff {cutoff} for test {c['test_date']}"
        )


def test_expanding_arm_train_labels_realized_by_predict_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Decisive leakage invariant: every train row's fwd_5s is REALIZED by the
    predict point (predict is at the week's CLOSE, so close[t_w] is known; train
    labels may use close[<=t_w] but NOT close[t_w+k]).

    Settles whether embargo=5 suffices: the latest train week (W-1, close ≈
    t_w − 5 sessions) has fwd_5s realizing at t_w (close[t_w] known) — realized
    BY the predict point, no lookahead. If this fails, embargo must grow.
    """
    daily = _syn_daily(n_days=80)
    daily_sessions = np.sort(pd.to_datetime(daily["date"]).unique())
    weekly = ta.weekly_reduce(daily)
    edges = ta.fit_binner(weekly["fwd_5s"])
    captured: list = []

    class _Stub:
        def __init__(self, params: dict) -> None:
            pass

        def fit_predict_rank(self, train, test, feats, rel, groups):  # noqa: ANN001
            captured.append({"train_max": train["date"].max(), "test_date": test["date"].iloc[0]})
            return pd.Series(np.zeros(len(test)), index=test.index, name="score")

    monkeypatch.setattr(ta, "LightGBMFrozen", _Stub)
    ta.MIN_TRAIN_ROWS = 20
    ta.run_expanding_arm(weekly, daily_sessions, _FEATURES, edges, embargo=5)

    sess = pd.DatetimeIndex(daily_sessions)
    for c in captured:
        idx_train_max = sess.get_loc(pd.Timestamp(c["train_max"]))
        idx_test = sess.get_loc(pd.Timestamp(c["test_date"]))
        # train_max's fwd_5s realizes 5 sessions later; must be <= predict session.
        realize_idx = min(idx_train_max + 5, len(sess) - 1)
        assert realize_idx <= idx_test, (
            f"LEAK: train_max {c['train_max']}'s fwd_5s realizes at session "
            f"{sess[realize_idx]} > predict {sess[idx_test]} ({c['test_date']})"
        )


def test_expanding_arm_skips_weeks_with_insufficient_train(monkeypatch: pytest.MonkeyPatch) -> None:
    # First OOS week has almost no realized train → must be skipped (no fit).
    daily = _syn_daily(n_days=80)
    daily_sessions = np.sort(pd.to_datetime(daily["date"]).unique())
    weekly = ta.weekly_reduce(daily)
    edges = ta.fit_binner(weekly["fwd_5s"])

    n_fits = 0

    class _Stub:
        def __init__(self, params: dict) -> None:
            pass

        def fit_predict_rank(self, train, test, feats, rel, groups):  # noqa: ANN001
            nonlocal n_fits
            n_fits += 1
            return pd.Series(np.zeros(len(test)), index=test.index, name="score")

    monkeypatch.setattr(ta, "LightGBMFrozen", _Stub)
    ta.MIN_TRAIN_ROWS = 10_000  # impossibly high → every week skipped
    out = ta.run_expanding_arm(weekly, daily_sessions, _FEATURES, edges, embargo=5)
    assert n_fits == 0
    assert out.empty
