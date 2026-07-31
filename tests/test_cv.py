"""Purged cross-fit and chronological validation contracts."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aionis.eval.cv import (
    CVSplit,
    assert_chronological_split,
    purged_group_kfold_splits,
    purged_walk_forward_splits,
)
from aionis.features.alignment import nyse_sessions
from aionis.synthetic import make_synthetic_events, make_synthetic_prices


def _chronological_split() -> CVSplit:
    return CVSplit(
        train_idx=np.array([0]),
        test_idx=np.array([1]),
        fold=1,
        validation_kind="chronological",
    )


def test_cvsplit_three_argument_construction_defaults_to_cross_fit() -> None:
    split = CVSplit(np.array([0]), np.array([1]), 1)

    assert split.validation_kind == "purged_cross_fit"


def test_chronological_assertion_rejects_prediction_time_at_test_start() -> None:
    times = pd.Series(pd.to_datetime(["2024-01-02", "2024-01-02"]))

    with pytest.raises(ValueError, match="prediction_time is not strictly before"):
        assert_chronological_split(_chronological_split(), times, times)


def test_chronological_assertion_rejects_evaluation_time_after_test_start() -> None:
    prediction_times = pd.Series(pd.to_datetime(["2024-01-01", "2024-01-02"]))
    evaluation_times = pd.Series(pd.to_datetime(["2024-01-03", "2024-01-02"]))

    with pytest.raises(ValueError, match="evaluation_time extends beyond"):
        assert_chronological_split(
            _chronological_split(), prediction_times, evaluation_times
        )


def test_chronological_assertion_allows_evaluation_time_at_test_start() -> None:
    prediction_times = pd.Series(pd.to_datetime(["2024-01-01", "2024-01-02"]))
    evaluation_times = pd.Series(pd.to_datetime(["2024-01-02", "2024-01-02"]))

    assert_chronological_split(
        _chronological_split(), prediction_times, evaluation_times
    )


@pytest.fixture(scope="module")
def times():
    sessions = nyse_sessions("2022-01-03", "2023-06-30")
    prices = make_synthetic_prices(sessions, ["XLK", "SPY"], seed=1)
    events = make_synthetic_events(sessions, n=40, seed=2)
    from aionis.features.design_matrix import build_design_matrix

    dm = build_design_matrix(events, prices, sessions, ["XLK"], horizon=1)
    return dm.prediction_times.reset_index(drop=True), dm.evaluation_times.reset_index(drop=True)


def test_each_row_in_at_most_one_test_fold(times) -> None:
    pt, et = times
    splits = purged_walk_forward_splits(pt, et, n_splits=5, embargo=pd.Timedelta(days=1))
    all_test = np.concatenate([s.test_idx for s in splits])
    assert len(all_test) == len(np.unique(all_test)), "row appeared in >1 test fold"


def test_no_train_test_overlap(times) -> None:
    pt, et = times
    for s in purged_walk_forward_splits(pt, et, n_splits=5, embargo=pd.Timedelta(days=1)):
        assert len(np.intersect1d(s.train_idx, s.test_idx)) == 0


def test_train_strictly_before_test(times) -> None:
    """Expanding window: every train prediction_time precedes the test window."""
    pt, et = times
    for s in purged_walk_forward_splits(pt, et, n_splits=5, embargo=pd.Timedelta(days=1)):
        train_pt_max = pt.iloc[s.train_idx].max()
        test_pt_min = pt.iloc[s.test_idx].min()
        assert train_pt_max < test_pt_min


def test_walk_forward_is_explicitly_chronological(times) -> None:
    pt, et = times
    splits = purged_walk_forward_splits(pt, et, n_splits=5, embargo=pd.Timedelta(days=1))
    for split in splits:
        assert split.validation_kind == "chronological"
        assert_chronological_split(split, pt, et)


def test_train_labels_end_before_test(times) -> None:
    """No train label extends into the test prediction window (the core no-leak rule).

    Note: purgedcv's ``embargo`` guards the post-test boundary (next fold), while
    purge handles label/test-prediction overlap. The invariant we need is that every
    train label ends at or before the test window starts.
    """
    pt, et = times
    for s in purged_walk_forward_splits(pt, et, n_splits=5, embargo=pd.Timedelta(days=2)):
        test_start = pt.iloc[s.test_idx].min()
        train_eval_max = et.iloc[s.train_idx].max()
        assert train_eval_max <= test_start


def test_embargo_purges_more_than_no_embargo(times) -> None:
    pt, et = times
    none = purged_walk_forward_splits(pt, et, n_splits=5, embargo=pd.Timedelta(0))
    big = purged_walk_forward_splits(pt, et, n_splits=5, embargo=pd.Timedelta(days=30))
    for s_n, s_b in zip(none, big, strict=True):
        assert len(s_n.train_idx) >= len(s_b.train_idx)


def test_too_few_events_raises() -> None:
    pt = pd.Series(pd.date_range("2023-01-03", periods=1, freq="D"))
    et = pt + pd.Timedelta(days=1)
    with pytest.raises(ValueError):
        purged_walk_forward_splits(pt, et, n_splits=5, embargo=pd.Timedelta(0))


def _monthly_panel() -> pd.DataFrame:
    """12 months x 3 tickers of daily business-day rows (enough groups for K=5)."""
    dates = pd.bdate_range("2024-01-01", "2024-12-31")
    rows = [{"date": d, "ticker": t} for d in dates for t in ("A", "B", "C")]
    df = pd.DataFrame(rows)
    df["eval"] = df["date"] + pd.Timedelta(days=21)   # label resolves ~h=21 sessions later
    df["month"] = df["date"].dt.to_period("M").astype(str)
    return df


def test_purged_group_kfold_never_splits_a_group_across_train_test() -> None:
    """A month (group) is wholly in train OR wholly in test — never both."""
    df = _monthly_panel()
    splits = purged_group_kfold_splits(
        df["date"], df["eval"], df["month"], n_splits=5, embargo=pd.Timedelta(days=21))
    assert len(splits) >= 2
    months = df["month"].to_numpy()
    for s in splits:
        tr = set(months[s.train_idx])
        te = set(months[s.test_idx])
        assert tr.isdisjoint(te), f"fold {s.fold} splits a month across train/test"


def test_purged_group_kfold_each_group_tested_at_most_once() -> None:
    df = _monthly_panel()
    splits = purged_group_kfold_splits(
        df["date"], df["eval"], df["month"], n_splits=5, embargo=pd.Timedelta(days=21))
    seen_idx: list[int] = []
    for s in splits:
        seen_idx.extend(s.test_idx.tolist())
    # each ROW appears in at most one test fold (a whole month tested once)
    assert len(seen_idx) == len(set(seen_idx))


def test_purged_group_kfold_no_train_test_index_overlap() -> None:
    df = _monthly_panel()
    splits = purged_group_kfold_splits(
        df["date"], df["eval"], df["month"], n_splits=5, embargo=pd.Timedelta(days=21))
    for s in splits:
        assert len(np.intersect1d(s.train_idx, s.test_idx)) == 0


def test_purged_group_kfold_is_cross_fit_not_chronological() -> None:
    df = _monthly_panel()
    splits = purged_group_kfold_splits(
        df["date"], df["eval"], df["month"], n_splits=5, embargo=pd.Timedelta(days=21)
    )
    assert all(split.validation_kind == "purged_cross_fit" for split in splits)
    assert any(
        df["date"].iloc[split.train_idx].max()
        >= df["date"].iloc[split.test_idx].min()
        for split in splits
    )
    with pytest.raises(ValueError, match="not chronological"):
        assert_chronological_split(splits[0], df["date"], df["eval"])
