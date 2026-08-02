"""Frozen LightGBM learner for Phase B (deterministic: n_jobs=1, all seeds pinned).

Hyperparameters come from the pre-reg §8.0 frozen table. The extra seed pins
(``bagging_seed`` / ``feature_fraction_seed`` / ``drop_seed`` = 0) are LightGBM's
deterministic defaults made EXPLICIT so H6 (bit-identical reruns) holds — they do
not change behavior, only document it. NaNs in features are handled natively by
LightGBM (no imputation — imputation could leak), which matters because PIT
fundamentals are NaN before a firm's first filing.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

FROZEN_PARAMS: dict = {
    "objective": "regression",
    "n_estimators": 500,
    "learning_rate": 0.05,
    "num_leaves": 31,
    "min_child_samples": 20,
    "reg_lambda": 1.0,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 1,
    "n_jobs": 1,
    "random_state": 0,
    # determinism pins (LightGBM defaults = 0; made explicit for H6):
    "bagging_seed": 0,
    "feature_fraction_seed": 0,
    "drop_seed": 0,
    "verbose": -1,
}


class LightGBMFrozen:
    """Thin wrapper around ``lightgbm.train`` with the Phase B frozen config.

    Determinism contract: two ``fit_predict`` calls on identical data produce
    bit-identical scores (the foundation of the H6 determinism test).
    """

    def __init__(self, params: dict | None = None) -> None:
        self.params = {**FROZEN_PARAMS, **(params or {})}

    def fit_predict(
        self,
        train: pd.DataFrame,
        test: pd.DataFrame,
        feature_cols: list[str],
        y_col: str,
    ) -> pd.Series:
        """Fit on ``train`` (no early stopping — frozen ``n_estimators`` rounds),
        predict scores for ``test``. Returns a Series indexed like ``test``."""
        import lightgbm as lgb

        n_rounds = int(self.params.get("n_estimators", 100))
        train_params = {k: v for k, v in self.params.items() if k != "n_estimators"}
        Xtr = train[feature_cols].to_numpy(dtype=float)
        ytr = train[y_col].to_numpy(dtype=float)
        Xte = test[feature_cols].to_numpy(dtype=float)
        dtr = lgb.Dataset(Xtr, label=ytr)
        bst = lgb.train(train_params, dtr, num_boost_round=n_rounds)
        return pd.Series(bst.predict(Xte), index=test.index, name="score")

    def fit_predict_rank(
        self,
        train: pd.DataFrame,
        test: pd.DataFrame,
        feature_cols: list[str],
        relevance: np.ndarray,
        group_sizes: np.ndarray,
    ) -> pd.Series:
        """Fit LightGBM **lambdarank** (relevance label + query groups), predict test scores.

        Additive ranking path (Track B; config #41 objective=lambdarank, RD-15) —
        does NOT alter :meth:`fit_predict` (the regression path used by B/C/D/E1).
        H6-deterministic via the frozen seed pins (random_state / bagging_seed /
        feature_fraction_seed / drop_seed = 0, n_jobs=1, version-pinned).

        Args:
            train: training rows; MUST be sorted by group so rows of the same query
                (month) are consecutive (LightGBM ``group`` requirement).
            test: test rows to score.
            feature_cols: pre-specified feature columns (config #41).
            relevance: integer relevance labels (0..n_bins-1) aligned with ``train``;
                from ``ranking_contract.transform_to_relevance`` on FROZEN train-fold bins.
            group_sizes: query-group sizes (``ranking_contract.get_group_sizes``),
                summing to ``len(train)`` and ordered by ascending group ID (== train order).

        Returns:
            Series of ranking scores indexed like ``test``.
        """
        import lightgbm as lgb

        params = {**self.params, "objective": "lambdarank", "metric": "ndcg"}
        n_rounds = int(params.pop("n_estimators", 100))
        xtr = train[feature_cols].to_numpy(dtype=float)
        xte = test[feature_cols].to_numpy(dtype=float)
        rel = np.asarray(relevance, dtype=np.int32)
        groups = np.asarray(group_sizes, dtype=np.int32)
        dtr = lgb.Dataset(xtr, label=rel, group=groups)
        bst = lgb.train(params, dtr, num_boost_round=n_rounds)
        return pd.Series(bst.predict(xte), index=test.index, name="score")
