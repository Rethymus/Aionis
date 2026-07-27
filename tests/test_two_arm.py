"""Phase B two-arm runner — hermetic structural invariants (synthetic data).

Pins the core fairness property: with NO fundamentals, both arms build IDENTICAL
panels (align_on has no effect) → identical folds + deterministic LightGBM →
identical scores. So any score difference on real fundamentals comes ONLY from
fundamental timing, never from arm-specific bias.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from aionis.eval.two_arm import run_two_arm_oos


def _fixtures(seed: int = 0, n_sess: int = 120,
              tickers: tuple[str, ...] = ("A", "B", "C", "D")) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
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


_KW = dict(
    fundamentals_long=pd.DataFrame(), horizon=5, feature_cols=["close"],
    n_splits=3, embargo_sessions=5, params={"n_estimators": 40},
)


def test_empty_fundamentals_arms_produce_identical_scores() -> None:
    px, mem = _fixtures()
    out = run_two_arm_oos(prices=px, membership=mem, **_KW)
    a, b = out["arm_state"], out["arm_base"]
    assert set(a.columns) == {"date", "ticker", "y_fwd_ret", "score"}
    assert a[["date", "ticker"]].reset_index(drop=True).equals(
        b[["date", "ticker"]].reset_index(drop=True)
    )
    # No fundamentals -> identical panels -> identical scores (no arm bias).
    np.testing.assert_array_equal(a["score"].to_numpy(), b["score"].to_numpy())


def test_deterministic_across_runs() -> None:
    px, mem = _fixtures()
    o1 = run_two_arm_oos(prices=px, membership=mem, **_KW)["arm_state"]["score"].to_numpy()
    o2 = run_two_arm_oos(prices=px, membership=mem, **_KW)["arm_state"]["score"].to_numpy()
    np.testing.assert_array_equal(o1, o2)


def test_finite_scores_and_oos_rows_present() -> None:
    px, mem = _fixtures()
    out = run_two_arm_oos(prices=px, membership=mem, **_KW)
    for arm, df in out.items():
        assert len(df) > 0, f"{arm} produced no OOS rows"
        assert np.isfinite(df["score"].to_numpy()).all()
        assert np.isfinite(df["y_fwd_ret"].to_numpy()).all()


def test_scores_differ_when_fundamental_timing_differs() -> None:
    """Guard (critic 'Missing'): when a fact's filed date != end+lag, arm_state and
    arm_base see the value at DIFFERENT times -> their OOS score arrays must differ.
    Catches a future bug that silently makes the arms identical."""
    px, mem = _fixtures()
    tickers = list(px.columns)
    # 10-K: end 2024-01-02, filed 2024-03-15 (fast filer). end+6mo = 2024-07-02,
    # which is BEYOND the ~120-session panel -> arm_base never sees fund_assets
    # (all NaN) while arm_state sees it from 2024-03-15 -> feature matrices differ.
    fund = pd.DataFrame([
        {"ticker": t, "metric": "assets", "end": "2024-01-02", "filed": "2024-03-15",
         "form": "10-K", "fy": 2023, "fp": "FY", "value": float(i + 1) * 1000.0, "unit": "USD"}
        for i, t in enumerate(tickers)
    ])
    out = run_two_arm_oos(
        prices=px, membership=mem, fundamentals_long=fund, horizon=5,
        feature_cols=["close", "fund_assets"], n_splits=3, embargo_sessions=5,
        params={"n_estimators": 40},
    )
    a = out["arm_state"].set_index(["date", "ticker"])["score"]
    b = out["arm_base"].set_index(["date", "ticker"])["score"]
    common = a.index.intersection(b.index)
    assert len(common) > 0
    assert not np.array_equal(a.loc[common].to_numpy(), b.loc[common].to_numpy()), (
        "arm_state and arm_base produced identical scores despite different fund timing"
    )
