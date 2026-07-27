"""Purged, embargoed walk-forward CV — delegated to the ``purgedcv`` wheel.

The leakage invariants (purge + embargo, no train/test overlap) are enforced by
``purgedcv.WalkForwardSplit`` itself: it raises ``TemporalLeakageError`` on any
violation. This module is now a thin adapter preserving the project's ``CVSplit``
shape so downstream code is unchanged. (Earlier hand-rolled purge/embargo logic
removed in favor of the audited wheel — AFML chs.7 & 12 reference implementation.)
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

_ZERO_EMBARGO = pd.Timedelta(0)


@dataclass(frozen=True)
class CVSplit:
    train_idx: np.ndarray
    test_idx: np.ndarray
    fold: int


def _safe_test_size(n_samples: int, n_splits: int) -> int:
    """Largest per-fold test size satisfying purgedcv's n_splits*test_size < n."""
    return max(1, (n_samples - 1) // n_splits)


def purged_walk_forward_splits(
    prediction_times: pd.Series,
    evaluation_times: pd.Series,
    n_splits: int = 5,
    embargo: pd.Timedelta = _ZERO_EMBARGO,
) -> list[CVSplit]:
    """Expanding walk-forward CV with purge + embargo (via ``purgedcv``).

    Train is strictly before test (expanding window); train labels reaching the
    embargoed test window are purged. The earliest block may be train-only (never
    tested), consistent with walk-forward semantics.
    """
    if n_splits < 2:
        raise ValueError("n_splits must be >= 2")
    pt = pd.Series(pd.to_datetime(prediction_times)).reset_index(drop=True)
    et = pd.Series(pd.to_datetime(evaluation_times)).reset_index(drop=True)
    if len(pt) != len(et):
        raise ValueError("prediction_times / evaluation_times length mismatch")
    n = len(pt)
    test_size = _safe_test_size(n, n_splits)
    if n_splits * test_size >= n:
        raise ValueError("too few samples for walk-forward CV")

    import purgedcv

    wf = purgedcv.WalkForwardSplit(
        n_splits=n_splits,
        test_size=test_size,
        window="expanding",
        prediction_times=pt,
        evaluation_times=et,
        embargo=embargo,
    )
    out: list[CVSplit] = []
    X = np.zeros((n, 1))
    for fold, (train_idx, test_idx) in enumerate(wf.split(X), start=1):
        train_idx = np.asarray(train_idx, dtype=int)
        test_idx = np.asarray(test_idx, dtype=int)
        if len(train_idx) == 0 or len(test_idx) == 0:
            continue
        out.append(CVSplit(train_idx=train_idx, test_idx=test_idx, fold=fold))
    if not out:
        raise ValueError("CV produced no usable splits (too few events?)")
    return out


def purged_group_kfold_splits(
    prediction_times: pd.Series,
    evaluation_times: pd.Series,
    groups: pd.Series,
    n_splits: int = 5,
    embargo: pd.Timedelta = _ZERO_EMBARGO,
) -> list[CVSplit]:
    """Purged, embargoed K-fold grouped by ``groups`` (Phase B §8.0: month).

    Each group is wholly in train OR test (a split group raises
    ``purgedcv.GroupLeakageError``); train samples whose label (evaluation_time)
    overlaps a test group are purged; ``embargo`` enforces a buffer after each test
    block (``purgedcv.EmbargoViolationError`` on violation). Both Phase B arms share
    the SAME folds (computed once on the aligned panel), so the rank-IC differential
    isolates fundamental-timing, not CV noise.
    """
    if n_splits < 2:
        raise ValueError("n_splits must be >= 2")
    pt = pd.Series(pd.to_datetime(prediction_times)).reset_index(drop=True)
    et = pd.Series(pd.to_datetime(evaluation_times)).reset_index(drop=True)
    gr = pd.Series(groups).reset_index(drop=True)
    n = len(pt)
    if not (len(et) == n == len(gr)):
        raise ValueError("prediction_times / evaluation_times / groups length mismatch")

    import purgedcv

    pg = purgedcv.PurgedGroupKFold(
        n_splits=n_splits,
        prediction_times=pt,
        evaluation_times=et,
        groups=gr,
        embargo=embargo,
    )
    out: list[CVSplit] = []
    X = np.zeros((n, 1))
    for fold, (train_idx, test_idx) in enumerate(pg.split(X), start=1):
        train_idx = np.asarray(train_idx, dtype=int)
        test_idx = np.asarray(test_idx, dtype=int)
        if len(train_idx) == 0 or len(test_idx) == 0:
            continue
        out.append(CVSplit(train_idx=train_idx, test_idx=test_idx, fold=fold))
    if not out:
        raise ValueError("CV produced no usable splits (too few groups?)")
    return out
