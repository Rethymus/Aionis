"""Cross-sectional rank-IC evaluation — hermetic (Phase B primary metric).

rank-IC = per-date Spearman correlation between the model's cross-sectional score
and the realized h-ahead return. The headline is the time-series mean of monthly
rank-IC with a Newey-West HAC t-stat (statsmodels) — the publishable default for
autocorrelated IC series (frontier §2A; pre-reg §4 primary metric).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from aionis.eval.rank_ic import rank_ic_by_date, rank_ic_monthly, rank_ic_summary


def test_rank_ic_sign_per_date_perfect_and_anti() -> None:
    """Perfect monotone score→return gives IC=+1; reversed gives −1, per date."""
    panel = pd.DataFrame({
        "date": ["2024-01-31"] * 5 + ["2024-02-29"] * 5,
        "score": [1.0, 2, 3, 4, 5, 1, 2, 3, 4, 5],
        "y": [10.0, 20, 30, 40, 50, 50, 40, 30, 20, 10],
    })
    ic = rank_ic_by_date(panel, "score", "y")
    assert len(ic) == 2
    np.testing.assert_allclose(ic.loc["2024-01-31"], 1.0, atol=1e-12)
    np.testing.assert_allclose(ic.loc["2024-02-29"], -1.0, atol=1e-12)


def test_rank_ic_drops_dates_with_too_few_rows() -> None:
    """A date with <5 cross-sectional rows is uninformative → dropped (NaN)."""
    panel = pd.DataFrame({
        "date": ["2024-01-31"] * 2 + ["2024-02-29"] * 5,
        "score": [1.0, 2, 1, 2, 3, 4, 5],
        "y": [10.0, 20, 10, 20, 30, 40, 50],
    })
    ic = rank_ic_by_date(panel, "score", "y")
    assert "2024-01-31" not in ic.index  # <5 rows dropped
    assert len(ic) == 1
    np.testing.assert_allclose(ic.loc["2024-02-29"], 1.0, atol=1e-12)


def test_rank_ic_summary_strong_positive_vs_null() -> None:
    """A strongly-positive IC series → large HAC t / tiny p; a null series → p large."""
    pos = pd.Series([0.04, 0.05, 0.06, 0.05] * 12)  # mean 0.05, strongly positive
    sp = rank_ic_summary(pos)
    np.testing.assert_allclose(sp["mean_ic"], 0.05, atol=1e-9)
    assert sp["t_hac"] > 10, sp
    assert sp["p_hac"] < 1e-6, sp

    null = pd.Series([0.001, -0.001, 0.0, 0.002, -0.002] * 10)  # mean ~0
    sn = rank_ic_summary(null)
    assert abs(sn["mean_ic"]) < 1e-6, sn
    assert sn["p_hac"] > 0.1, sn


def test_rank_ic_monthly_collapses_daily_to_month_end() -> None:
    """A daily panel with 2 months x many sessions collapses to 2 month-end ICs."""
    days = pd.date_range("2024-01-02", "2024-02-29", freq="B")
    rows = []
    for d in days:
        # 6 tickers, score monotonically increasing, y decreasing -> IC = -1 each day
        for i, _t in enumerate("ABCDEF"):
            rows.append({"date": d, "score": float(i), "y": float(6 - i)})
    panel = pd.DataFrame(rows)
    ic = rank_ic_monthly(panel, "score", "y")
    assert len(ic) == 2  # Jan + Feb month-ends
    np.testing.assert_allclose(ic.to_numpy(), -1.0, atol=1e-12)
