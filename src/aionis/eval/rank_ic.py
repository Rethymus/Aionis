"""Cross-sectional rank-IC evaluation (Phase B primary metric).

Reuses, not hand-rolls:
  * Spearman rank-IC = Pearson corr of pandas ranks (no scipy dep).
  * Newey-West HAC inference on the IC time series (``statsmodels`` OLS on a
    constant with ``cov_type='HAC'``) — the publishable default for
    autocorrelated IC series (``frontier_positioning.md`` §2A; pre-reg §4).

rank-IC is the per-date Spearman correlation between a model's cross-sectional
score and the realized h-ahead return. The headline is the time-series mean of
monthly rank-IC with a HAC t-stat. An IC series is itself a loss/differential
channel — feed it to ``eval.metrics`` MBB-DM for a small-n robustness complement.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def rank_ic_by_date(
    panel: pd.DataFrame, score_col: str, y_col: str, date_col: str = "date",
    min_rows: int = 5,
) -> pd.Series:
    """Per-date Spearman rank-IC of ``score_col`` vs ``y_col``.

    Returns a Series indexed by sorted date; dates with fewer than ``min_rows``
    non-NaN cross-sectional rows are dropped (they carry no rank information).
    """
    sub = panel[[date_col, score_col, y_col]].dropna()

    def _ic(g: pd.DataFrame) -> float:
        if len(g) < min_rows:
            return np.nan
        return float(g[score_col].rank().corr(g[y_col].rank()))

    ic = sub.groupby(date_col).apply(_ic)
    return ic.dropna().sort_index()


def rank_ic_monthly(
    panel: pd.DataFrame, score_col: str, y_col: str, date_col: str = "date",
    min_rows: int = 5,
) -> pd.Series:
    """Monthly cross-sectional rank-IC (Phase B §4 headline granularity).

    Reduces the panel to the LAST session of each calendar month (standard monthly
    rebalance), then per-month Spearman of score vs the h-ahead forward return.
    Feeding a daily OOS panel here gives the monthly IC series the pre-reg prescribes
    (not a noisy daily series). Returns a Series indexed by month-end date.
    """
    df = panel[[date_col, score_col, y_col]].dropna().copy()
    df[date_col] = pd.to_datetime(df[date_col]).dt.normalize()
    month = df[date_col].dt.to_period("M")
    keep = df.groupby(month)[date_col].transform("max") == df[date_col]
    return rank_ic_by_date(df[keep], score_col, y_col, date_col, min_rows)


def rank_ic_summary(ic: pd.Series, maxlag: int | None = None) -> dict:
    """Mean rank-IC + Newey-West HAC t-stat / p on the IC time series.

    ``maxlag`` defaults to the Newey-West rule of thumb
    ``int(4 * (n/100) ** (2/9))``. Returns ``n`` and the realized ``maxlag`` so
    the publishability check (pre-reg §7: 95% CI half-width < 0.015) is auditable.
    """
    ic = ic.dropna()
    n = len(ic)
    if n < 2:
        return {"mean_ic": float("nan"), "t_hac": float("nan"),
                "p_hac": float("nan"), "se_hac": float("nan"),
                "ci_half": float("nan"), "n": n, "maxlag": 0}
    if maxlag is None:
        maxlag = max(1, int(4 * (n / 100.0) ** (2 / 9)))

    from statsmodels.regression.linear_model import OLS

    res = OLS(ic.to_numpy(dtype=float), np.ones(n)).fit(
        cov_type="HAC", cov_kwds={"maxlags": maxlag})
    se = float(res.bse[0])
    mean_ic = float(ic.mean())
    # 95% CI half-width on the mean = 1.96 * HAC SE (the publishability gate).
    ci_half = 1.959963985 * se
    return {"mean_ic": mean_ic, "t_hac": float(res.tvalues[0]),
            "p_hac": float(res.pvalues[0]), "se_hac": se,
            "ci_half": ci_half, "n": n, "maxlag": maxlag}
