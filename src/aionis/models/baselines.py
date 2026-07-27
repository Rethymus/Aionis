"""Naive baselines. The price-only model must beat these before it means anything.

Every baseline implements the uniform learner interface
``fit_predict(X_train, y_train, X_test) -> np.ndarray`` so they drop into the same
cross-validation harness as the real learners.
"""

from __future__ import annotations

import numpy as np


def fit_predict_zero(X_train, y_train, X_test) -> np.ndarray:
    return np.zeros(len(X_test))


def fit_predict_mean(X_train, y_train, X_test) -> np.ndarray:
    return np.full(len(X_test), float(np.mean(y_train)))


def fit_predict_always_up(X_train, y_train, X_test) -> np.ndarray:
    # Tiny positive constant => sign == +1 everywhere; DA == up_baseline.
    return np.full(len(X_test), 1e-6)


def fit_predict_ar1(X_train, y_train, X_test) -> np.ndarray:
    """OLS y ~ 1 + ret_1d on train, applied to test.

    Falls back to the training mean where the lag-1 return feature is absent or
    degenerate (so the AR(1) baseline never crashes a fold).
    """
    y = np.asarray(y_train, float)
    if "ret_1d" not in X_train.columns or len(X_train) < 5:
        return fit_predict_mean(X_train, y_train, X_test)
    x = X_train["ret_1d"].to_numpy(dtype=float)
    xt = X_test["ret_1d"].to_numpy(dtype=float)
    if not np.isfinite(x).all() or np.std(x) < 1e-12:
        return fit_predict_mean(X_train, y_train, X_test)
    X = np.column_stack([np.ones_like(x), x])
    coef, *_ = np.linalg.lstsq(X, y - y.mean(), rcond=None)
    return y.mean() + coef[0] + coef[1] * xt


BASELINES: dict[str, callable] = {
    "predict_0": fit_predict_zero,
    "predict_mean": fit_predict_mean,
    "always_up": fit_predict_always_up,
    "ar1": fit_predict_ar1,
}
