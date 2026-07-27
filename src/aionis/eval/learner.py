"""Frozen LightGBM learner for Phase B (deterministic: n_jobs=1, all seeds pinned).

Hyperparameters come from the pre-reg §8.0 frozen table. The extra seed pins
(``bagging_seed`` / ``feature_fraction_seed`` / ``drop_seed`` = 0) are LightGBM's
deterministic defaults made EXPLICIT so H6 (bit-identical reruns) holds — they do
not change behavior, only document it. NaNs in features are handled natively by
LightGBM (no imputation — imputation could leak), which matters because PIT
fundamentals are NaN before a firm's first filing.
"""
from __future__ import annotations

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
