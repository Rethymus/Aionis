"""Frozen LightGBM learner — hermetic (determinism + shape + NaN handling)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from aionis.eval.learner import FROZEN_PARAMS, LightGBMFrozen


def _data(seed: int = 0) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    n = 240
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n)
    y = 0.5 * x1 - 0.3 * x2 + rng.normal(scale=0.1, size=n)
    df = pd.DataFrame({"x1": x1, "x2": x2, "y": y})
    return df.iloc[:160].copy(), df.iloc[160:].copy()


def test_frozen_params_match_prereg_section_8() -> None:
    assert FROZEN_PARAMS["n_estimators"] == 500
    assert FROZEN_PARAMS["learning_rate"] == 0.05
    assert FROZEN_PARAMS["num_leaves"] == 31
    assert FROZEN_PARAMS["n_jobs"] == 1 and FROZEN_PARAMS["random_state"] == 0


def test_fit_predict_is_bit_identical_across_runs() -> None:
    """H6 foundation: same data -> same scores (n_jobs=1 + all seeds pinned)."""
    tr, te = _data()
    m = LightGBMFrozen()
    s1 = m.fit_predict(tr, te, ["x1", "x2"], "y")
    s2 = m.fit_predict(tr, te, ["x1", "x2"], "y")
    np.testing.assert_array_equal(s1.to_numpy(), s2.to_numpy())


def test_fit_predict_shape_finite_and_picks_up_signal() -> None:
    tr, te = _data()
    s = LightGBMFrozen().fit_predict(tr, te, ["x1", "x2"], "y")
    assert len(s) == len(te)
    assert np.isfinite(s.to_numpy()).all()
    corr = np.corrcoef(s.to_numpy(), te["y"].to_numpy())[0, 1]
    assert corr > 0.5  # strong signal in x1/x2 -> model recovers it


def test_handles_nan_features_natively_no_imputation() -> None:
    """PIT fundamentals are NaN before first filing; LightGBM must not choke."""
    tr, te = _data()
    tr.loc[tr.index[:30], "x2"] = np.nan
    te.loc[te.index[:8], "x2"] = np.nan
    s = LightGBMFrozen().fit_predict(tr, te, ["x1", "x2"], "y")
    assert len(s) == len(te)
    assert np.isfinite(s.to_numpy()).all()


def _rank_data(seed: int = 0) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Synthetic ranking data: train = 2 consecutive query groups of 80; test = 80.

    Relevance (0..4 quintiles) rises with x1, giving the lambdarank model a signal.
    Train is group-sorted (consecutive) so ``group_sizes=[80,80]`` is valid.
    """
    rng = np.random.default_rng(seed)

    def _block(n: int, offset: float) -> pd.DataFrame:
        x1 = rng.normal(size=n) + offset
        x2 = rng.normal(size=n)
        score = 0.6 * x1 - 0.2 * x2
        rel = np.digitize(score, np.quantile(score, [0.2, 0.4, 0.6, 0.8]))
        return pd.DataFrame({"x1": x1, "x2": x2, "rel": rel.astype(np.int32)})

    tr = pd.concat([_block(80, 0.0), _block(80, 1.0)], ignore_index=True)
    te = _block(80, 0.5)
    return tr, te


def test_fit_predict_rank_is_bit_identical_across_runs() -> None:
    """H6 for the lambdarank path (config #41): same data -> same scores."""
    tr, te = _rank_data()
    rel = tr["rel"].to_numpy(dtype=np.int32)
    group_sizes = np.array([80, 80], dtype=np.int32)
    m = LightGBMFrozen()
    s1 = m.fit_predict_rank(tr, te, ["x1", "x2"], rel, group_sizes)
    s2 = m.fit_predict_rank(tr, te, ["x1", "x2"], rel, group_sizes)
    np.testing.assert_array_equal(s1.to_numpy(), s2.to_numpy())


def test_fit_predict_rank_shape_finite_and_picks_up_signal() -> None:
    """lambdarank scores: finite, len==test, and correlated with the relevance driver (x1)."""
    tr, te = _rank_data()
    rel = tr["rel"].to_numpy(dtype=np.int32)
    group_sizes = np.array([80, 80], dtype=np.int32)
    s = LightGBMFrozen().fit_predict_rank(tr, te, ["x1", "x2"], rel, group_sizes)
    assert len(s) == len(te)
    assert np.isfinite(s.to_numpy()).all()
    corr = np.corrcoef(s.to_numpy(), te["x1"].to_numpy())[0, 1]
    assert corr > 0.3  # x1 drives relevance -> scores recover the signal
