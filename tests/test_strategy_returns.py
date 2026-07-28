"""Strategy-return evaluation — hermetic (synthetic OOS panels, no network).

Pins :mod:`aionis.eval.strategy_returns`: the long-short construction ranks the
cross-section at each month-end and pays the forward-return spread; the multiple-
testing wrappers (DSR / Hansen-SPA / MCS) run on the resulting monthly return
series. All inputs are synthetic so the assertions are exact.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aionis.eval.strategy_returns import (
    long_short_returns,
    sharpe_monthly,
    strategy_eval,
)


def _panel(months: list[str], tickers: list[str], seed: int = 0) -> pd.DataFrame:
    """Synthetic OOS panel: only each month's LAST session carries a signal
    (score == y_fwd_ret, a perfect cross-sectional rank); intra-month sessions
    are noise. Lets us assert the L-S spread exactly."""
    rng = np.random.default_rng(seed)
    rows = []
    for m in months:
        sessions = pd.bdate_range(pd.Timestamp(m), periods=3)
        last = sessions[-1]
        for d in sessions:
            for t in tickers:
                if d == last:
                    fr = float(rng.normal())
                    rows.append((d, t, fr, fr))  # score == fwd_ret (perfect rank)
                else:
                    rows.append((d, t, float(rng.normal()), float(rng.normal())))
    return pd.DataFrame(rows, columns=["date", "ticker", "score", "y_fwd_ret"])


# --- long-short construction ------------------------------------------------


def test_long_short_positive_when_score_ranks_forward_return() -> None:
    tickers = [f"T{i}" for i in range(10)]
    panel = _panel(["2024-01", "2024-02", "2024-03"], tickers, seed=1)

    ls = long_short_returns(panel, quantile=0.2, min_per_leg=1)

    assert ls.name == "ls_ret"
    assert len(ls) == 3  # one return per month
    assert (ls > 0).all()  # perfect rank -> long leg beats short leg every month


def test_long_short_value_is_top_minus_bottom_quantile_spread() -> None:
    # 5 tickers, quantile=0.2 -> k=1; one month-end session with known fwd_rets
    d = pd.Timestamp("2024-01-31")
    fwd = [0.01, 0.02, 0.03, 0.04, 0.05]  # ascending; score == fwd
    panel = pd.DataFrame(
        {"date": [d] * 5, "ticker": list("ABCDE"),
         "score": fwd, "y_fwd_ret": fwd}
    )

    ls = long_short_returns(panel, quantile=0.2, min_per_leg=1)

    assert len(ls) == 1
    # long top-1 (0.05) - short bottom-1 (0.01) = 0.04
    assert ls.iloc[0] == pytest.approx(0.04)


def test_thin_cross_section_dropped_not_imputed() -> None:
    d = pd.Timestamp("2024-01-31")
    panel = pd.DataFrame(
        {"date": [d] * 3, "ticker": list("ABC"),
         "score": [1.0, 2.0, 3.0], "y_fwd_ret": [0.1, 0.2, 0.3]}
    )

    ls = long_short_returns(panel, quantile=0.2, min_per_leg=3)  # k=1 < 3 -> skip

    assert ls.empty  # the lone rebalance had too few names


def test_long_short_ignores_nan_scores_and_returns() -> None:
    d = pd.Timestamp("2024-01-31")
    panel = pd.DataFrame(
        {"date": [d] * 5, "ticker": list("ABCDE"),
         "score": [np.nan, 2.0, 3.0, 4.0, 5.0],
         "y_fwd_ret": [0.1, np.nan, 0.3, 0.4, 0.5]}
    )

    ls = long_short_returns(panel, quantile=0.2, min_per_leg=1)

    # after dropna: only C/D/E remain (B had NaN ret, A had NaN score); k=1
    assert len(ls) == 1
    assert ls.iloc[0] == pytest.approx(0.5 - 0.3)  # top E (0.5) - bottom C (0.3)


def test_empty_panel_is_safe() -> None:
    assert long_short_returns(pd.DataFrame()).empty


# --- sharpe -----------------------------------------------------------------


def test_sharpe_monthly_matches_manual() -> None:
    r = pd.Series([0.1, -0.05, 0.2, 0.0, -0.1])

    assert sharpe_monthly(r) == pytest.approx(r.mean() / r.std(ddof=1))


def test_sharpe_monthly_zero_std_is_nan() -> None:
    assert np.isnan(sharpe_monthly(pd.Series([0.05, 0.05, 0.05])))


# --- strategy_eval (multiple-testing over a strategy set) -------------------


def test_strategy_eval_reports_per_strategy_sharpe_and_dsr() -> None:
    rng = np.random.default_rng(0)
    idx = pd.date_range("2017-01-31", periods=60, freq="ME")
    good = pd.Series(0.05 + rng.normal(0, 0.02, 60), index=idx)   # positive Sharpe
    flat = pd.Series(rng.normal(0, 0.02, 60), index=idx)          # ~zero Sharpe
    bad = pd.Series(-0.03 + rng.normal(0, 0.02, 60), index=idx)   # negative Sharpe

    out = strategy_eval({"good": good, "flat": flat, "bad": bad},
                        benchmark="flat", n_trials=3)

    assert set(out["per_strategy"]) == {"good", "flat", "bad"}
    good_sharpe = out["per_strategy"]["good"]["sharpe_monthly"]
    bad_sharpe = out["per_strategy"]["bad"]["sharpe_monthly"]
    assert good_sharpe > bad_sharpe
    assert out["n_months_common"] == 60
    assert out["n_trials"] == 3
    # cross-strategy tests ran (>= 2 strategies, >= 2 months)
    assert "spa" in out and "consistent_pvalue" in out["spa"]
    assert "mcs" in out and "included" in out["mcs"]


def test_strategy_eval_rejects_unknown_benchmark() -> None:
    idx = pd.date_range("2017-01-31", periods=24, freq="ME")
    s = pd.Series(np.ones(24) * 0.01, index=idx)
    with pytest.raises(ValueError, match="benchmark"):
        strategy_eval({"a": s}, benchmark="missing")


def test_strategy_eval_single_strategy_skips_cross_tests() -> None:
    idx = pd.date_range("2017-01-31", periods=24, freq="ME")
    s = pd.Series(np.linspace(0.01, 0.02, 24), index=idx)

    out = strategy_eval({"only": s})

    assert "spa" not in out and "mcs" not in out  # need >= 2 strategies
    assert "sharpe_monthly" in out["per_strategy"]["only"]
