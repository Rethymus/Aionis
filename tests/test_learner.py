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
