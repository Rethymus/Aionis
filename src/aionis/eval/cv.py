"""Purged validation adapters delegated to the ``purgedcv`` wheel.

``WalkForwardSplit`` is chronological; ``PurgedGroupKFold`` is purged cross-fit
and may train on observations later than its test block. ``validation_kind`` makes
that distinction explicit on every returned split.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

_ZERO_EMBARGO = pd.Timedelta(0)
ValidationKind = Literal["chronological", "purged_cross_fit"]


@dataclass(frozen=True)
class CVSplit:
    train_idx: np.ndarray
    test_idx: np.ndarray
    fold: int
    validation_kind: ValidationKind = "purged_cross_fit"


def assert_chronological_split(
    split: CVSplit,
    prediction_times: pd.Series,
    evaluation_times: pd.Series,
) -> None:
    """Fail unless ``split`` satisfies the strict chronological contract."""
    if split.validation_kind != "chronological":
        raise ValueError(
            f"fold {split.fold} is {split.validation_kind!r}, not chronological"
        )
    pt = pd.Series(pd.to_datetime(prediction_times)).reset_index(drop=True)
    et = pd.Series(pd.to_datetime(evaluation_times)).reset_index(drop=True)
    if len(pt) != len(et):
        raise ValueError("prediction_times / evaluation_times length mismatch")
    if len(split.train_idx) == 0 or len(split.test_idx) == 0:
        raise ValueError(f"fold {split.fold} has an empty train or test partition")
    try:
        train_prediction_time = pt.iloc[split.train_idx].max()
        train_evaluation_time = et.iloc[split.train_idx].max()
        test_start = pt.iloc[split.test_idx].min()
    except IndexError as exc:
        raise ValueError(f"fold {split.fold} contains an out-of-bounds index") from exc
    if pd.isna(train_prediction_time) or pd.isna(train_evaluation_time) or pd.isna(test_start):
        raise ValueError(f"fold {split.fold} contains missing validation times")
    if not train_prediction_time < test_start:
        raise ValueError(
            f"fold {split.fold} prediction_time is not strictly before test_start"
        )
    if not train_evaluation_time <= test_start:
        raise ValueError(
            f"fold {split.fold} evaluation_time extends beyond test_start"
        )


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
        split = CVSplit(
            train_idx=train_idx,
            test_idx=test_idx,
            fold=fold,
            validation_kind="chronological",
        )
        assert_chronological_split(split, pt, et)
        out.append(split)
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
    """Purged, embargoed cross-fit grouped by ``groups`` (Phase B §8.0: month).

    Each group is wholly in train OR test (a split group raises
    ``purgedcv.GroupLeakageError``); train samples whose label (evaluation_time)
    overlaps a test group are purged; ``embargo`` enforces a buffer after each test
    block (``purgedcv.EmbargoViolationError`` on violation). Candidate train rows
    are the test complement, so this is not chronological validation. Both Phase B
    arms share the same frozen fold indices.
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
        out.append(
            CVSplit(
                train_idx=train_idx,
                test_idx=test_idx,
                fold=fold,
                validation_kind="purged_cross_fit",
            )
        )
    if not out:
        raise ValueError("CV produced no usable splits (too few groups?)")
    return out
