"""Learner factories: XGBoost and a small MLP.

CPU-only by design (the locked environment has no GPU). Both share the uniform
``fit_predict(X_train, y_train, X_test) -> np.ndarray`` interface, so the same
learners are used for the price-only model and the ERL-augmented model — the
only difference is the feature matrix, which is exactly the ablation we want.
"""

from __future__ import annotations

import numpy as np


def fit_predict_xgb(X_train, y_train, X_test) -> np.ndarray:
    import xgboost as xgb

    model = xgb.XGBRegressor(
        n_estimators=400,
        max_depth=3,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=5,
        reg_lambda=1.0,
        tree_method="hist",
        n_jobs=1,  # single-threaded for STRICT run-to-run determinism
        random_state=0,  # (hist + multithread is non-deterministic even with a seed)
        early_stopping_rounds=None,
    )
    model.fit(X_train.to_numpy(dtype=float), np.asarray(y_train, float))
    return model.predict(X_test.to_numpy(dtype=float))


def fit_predict_mlp(X_train, y_train, X_test) -> np.ndarray:
    from sklearn.neural_network import MLPRegressor
    from sklearn.preprocessing import StandardScaler

    Xtr = X_train.to_numpy(dtype=float)
    Xs = X_test.to_numpy(dtype=float)
    x_scaler = StandardScaler().fit(Xtr)
    # Standardize the target too: returns are ~1e-2 magnitude and an unscaled
    # relu head explodes numerically (observed MAE 10x baseline). Inverse the
    # transform on the way out so predictions stay in return units.
    y = np.asarray(y_train, float)
    y_mean, y_std = float(y.mean()), float(y.std() or 1.0)
    y_scaled = (y - y_mean) / y_std

    model = MLPRegressor(
        hidden_layer_sizes=(16,),
        activation="tanh",
        alpha=1e-2,
        learning_rate_init=1e-3,
        max_iter=1000,
        early_stopping=True,
        n_iter_no_change=30,
        random_state=0,
    )
    model.fit(x_scaler.transform(Xtr), y_scaled)
    return model.predict(x_scaler.transform(Xs)) * y_std + y_mean


LEARNERS: dict[str, callable] = {
    "xgb": fit_predict_xgb,
    "mlp": fit_predict_mlp,
}
