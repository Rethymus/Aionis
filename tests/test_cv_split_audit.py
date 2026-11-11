"""Independent audit oracle for the PurgedGroupKFold split constructions.

Cross-audits the production fold builders — ``aionis.eval.cv.purged_group_kfold_splits``
(Phase B §8.0 cross-fit) and ``aionis.eval.two_arm.compute_shared_folds`` (folds shared
ONCE by every arm; group = calendar month, embargo = the calendar span of 21 sessions)
— against ``purgedcv.diagnostics`` primitives (``assert_groups_disjoint``,
``assert_no_temporal_leakage``, ``assert_embargo_respected``), the same library that
powers the splitter, used here as an independent checker of its output.

Hermetic: no network, synthetic labeled fixtures only (labeled unit-test fixtures are
the allowed mock domain; nothing here feeds the research pipeline). The audited
constructors are read-only anchors — this file changes no research surface.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from purgedcv.diagnostics import (
    EmbargoViolationError,
    GroupLeakageError,
    TemporalLeakageError,
    assert_embargo_respected,
    assert_groups_disjoint,
    assert_no_temporal_leakage,
)

from aionis.eval.cv import purged_group_kfold_splits
from aionis.eval.two_arm import compute_shared_folds


def _monthly_panel() -> pd.DataFrame:
    """12 months x 3 tickers of daily business-day rows (enough groups for K=5)."""
    dates = pd.bdate_range("2024-01-01", "2024-12-31")
    rows = [{"date": d, "ticker": t} for d in dates for t in ("A", "B", "C")]
    df = pd.DataFrame(rows)
    df["eval"] = df["date"] + pd.Timedelta(days=21)  # label resolves ~h=21 sessions later
    df["month"] = df["date"].dt.to_period("M").astype(str)
    return df


def _px_mem() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Synthetic prices + PIT membership, mirroring the test_two_arm fixture shape."""
    rng = np.random.default_rng(0)
    n_sess = 120
    tickers = ("A", "B", "C", "D")
    dates = pd.bdate_range("2024-01-02", periods=n_sess)
    px = pd.DataFrame(
        100 + np.cumsum(rng.normal(size=(n_sess, len(tickers))), axis=0),
        index=dates, columns=list(tickers),
    )
    months = pd.date_range(dates[0], dates[-1], freq="MS")
    mem = pd.DataFrame(
        [(m, t) for m in months for t in tickers], columns=["date", "ticker"],
    )
    return px, mem


def _two_arm_times_and_groups(ref: pd.DataFrame, horizon: int, embargo_sessions: int) -> tuple:
    """Rebuild (prediction_times, evaluation_times, groups, embargo) from the PUBLIC
    ``ref_layout`` returned by compute_shared_folds, pinning the documented contract
    (two_arm._folds_from_panel: eval = the session ``horizon`` positions after date;
    group = calendar month; embargo = calendar span of ``embargo_sessions`` sessions).
    Auditing against the contract — not the constructor's internals — is the point."""
    dates_sorted = pd.DatetimeIndex(sorted(ref["date"].unique()))
    pos = {d: i for i, d in enumerate(dates_sorted)}
    n_sess = len(dates_sorted)
    emb = min(max(embargo_sessions, 0), n_sess - 1)
    embargo_td = pd.Timedelta(dates_sorted[emb] - dates_sorted[0])
    pt = ref["date"]
    et = ref["date"].map(lambda d: dates_sorted[min(pos[d] + horizon, n_sess - 1)])
    gr = ref["date"].dt.to_period("M").astype(str)
    return pt, et, gr, embargo_td


def _audit_fold(train_idx, test_idx, pt, et, gr, embargo_td, fold: int) -> None:
    """Run all three diagnostics on one fold (failure messages name the fold)."""
    assert_groups_disjoint(train_idx, test_idx, gr)
    assert_no_temporal_leakage(train_idx, test_idx, pt, et)
    assert_embargo_respected(train_idx, test_idx, pt, et, embargo_td)


def test_oracle_cv_construction_passes_all_diagnostics() -> None:
    """cv.py cross-fit output: every fold is group-disjoint, temporally leak-free
    and embargo-respecting under the independent purgedcv.diagnostics oracle."""
    df = _monthly_panel()
    embargo = pd.Timedelta(days=21)
    splits = purged_group_kfold_splits(
        df["date"], df["eval"], df["month"], n_splits=5, embargo=embargo,
    )
    assert len(splits) >= 2
    for s in splits:
        _audit_fold(s.train_idx, s.test_idx, df["date"], df["eval"], df["month"], embargo, s.fold)


def test_oracle_two_arm_shared_folds_pass_all_diagnostics() -> None:
    """compute_shared_folds (group=month, embargo=21 sessions, folds computed ONCE):
    the shared folds pass all three diagnostics audited against the ref layout."""
    px, mem = _px_mem()
    horizon, n_splits, embargo_sessions = 5, 3, 21
    folds, ref = compute_shared_folds(
        px, mem, horizon, n_splits=n_splits, embargo_sessions=embargo_sessions,
    )
    assert len(folds) >= 2
    pt, et, gr, embargo_td = _two_arm_times_and_groups(ref, horizon, embargo_sessions)
    # the 21-session embargo spans strictly more than 21 calendar days (weekends
    # intervene) — pins that the embargo is session-calendar, not naive days
    assert embargo_td > pd.Timedelta(days=embargo_sessions)
    for s in folds:
        _audit_fold(s.train_idx, s.test_idx, pt, et, gr, embargo_td, s.fold)


def test_oracle_is_not_vacuous_group_overlap() -> None:
    """A group present in both train and test must trip assert_groups_disjoint."""
    groups = pd.Series(["g0", "g0", "g1"])
    with pytest.raises(GroupLeakageError):
        assert_groups_disjoint(np.array([0, 1, 2]), np.array([1]), groups)


def test_oracle_is_not_vacuous_temporal_leakage() -> None:
    """A train label horizon overlapping a test label horizon must trip
    assert_no_temporal_leakage (train row 1 horizon [Jan20, Feb10) intersects
    test row 0 horizon [Jan10, Jan31))."""
    pt = pd.to_datetime(pd.Series(["2024-01-10", "2024-01-20", "2024-03-01"]))
    et = pd.to_datetime(pd.Series(["2024-01-31", "2024-02-10", "2024-03-20"]))
    with pytest.raises(TemporalLeakageError):
        assert_no_temporal_leakage(np.array([1]), np.array([0]), pt, et)


def test_oracle_is_not_vacuous_embargo() -> None:
    """A train prediction_time inside the closed window [test_eval, test_eval +
    embargo] must trip assert_embargo_respected (row 1 pred Feb 10 ∈ [Jan 31,
    Feb 21]; rows strictly before all test evals are never flagged by design)."""
    pt = pd.to_datetime(pd.Series(["2024-01-10", "2024-02-10"]))
    et = pd.to_datetime(pd.Series(["2024-01-31", "2024-03-01"]))
    with pytest.raises(EmbargoViolationError):
        assert_embargo_respected(np.array([1]), np.array([0]), pt, et, pd.Timedelta(days=21))
