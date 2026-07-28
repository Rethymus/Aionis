"""Strategy-return evaluation — turn OOS rank-IC evidence into a tradeable
long-short portfolio and apply multiple-testing corrections.

The rank-IC nulls (Phase B/C) show the scores carry little *average* cross-
sectional predictive content. The strategy-return lens is complementary: does a
TRADEABLE long-short portfolio built from the scores earn a Sharpe that survives
deflation / overfitting / multiple-model comparison? A null IC can in principle
still yield a tail-concentrated positive Sharpe; conversely a near-zero IC almost
always means a flat long-short. This module makes both checkable on the SAME OOS
score panels the rank-IC used.

Portfolio construction (monthly rebalance, equal-weighted legs, no costs):
  * at each month's LAST session ``d``, rank the cross-section by score;
  * long the top ``quantile``, short the bottom ``quantile`` (equal weight);
  * the month's strategy return = mean(y_fwd_ret of longs) − mean(y_fwd_ret of
    shorts) — the h-session forward return (~next month), non-overlapping across
    month-end rebalances (consecutive month-ends are ~h sessions apart).

Multiple testing reuses :mod:`aionis.eval.multiple_testing` (DSR via ``purgedcv``,
PBO via CSCV, Hansen-SPA / MCS via ``arch``) — no new dependencies. Permissive
licenses only (pandas / numpy / arch NCSA / purgedcv).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from aionis.eval.multiple_testing import (
    deflated_sharpe,
    hansen_mcs,
    hansen_spa,
)


def long_short_returns(
    panel: pd.DataFrame,
    *,
    score_col: str = "score",
    ret_col: str = "y_fwd_ret",
    quantile: float = 0.2,
    rebalance: str = "monthly",
    min_per_leg: int = 3,
) -> pd.Series:
    """Monthly equal-weighted long-short returns from an OOS score panel.

    Args:
        panel: ``[date, ticker, score, y_fwd_ret]`` — the output of
            :func:`aionis.eval.two_arm.run_arm_oos`.
        score_col / ret_col: the ranking signal and the forward-return column.
        quantile: leg size as a fraction of the cross-section (default top/bottom
            decile — ``0.2`` = quintile). ``k = max(1, int(n * quantile))``.
        rebalance: ``"monthly"`` (default) — the last session of each calendar
            month. The forward return at that session realizes over the next
            ~month, so consecutive rebalances are non-overlapping.
        min_per_leg: skip a rebalance date whose cross-section is too thin to fill
            both legs with at least this many names.

    Returns a date-indexed :class:`~pandas.Series` of monthly L-S returns
    (long minus short), sorted by date. Dates with insufficient tickers are
    dropped (never imputed).
    """
    if panel is None or panel.empty:
        return pd.Series(dtype=float, name="ls_ret")
    df = panel.dropna(subset=[score_col, ret_col]).copy()
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    if df.empty:
        return pd.Series(dtype=float, name="ls_ret")

    if rebalance == "monthly":
        df["period"] = df["date"].dt.to_period("M")
        last = df.groupby("period")["date"].transform("max")
        df = df[df["date"] == last]
    else:
        raise ValueError(f"unknown rebalance {rebalance!r} (expected 'monthly')")

    out: dict[pd.Timestamp, float] = {}
    for d, g in df.groupby("date", sort=True):
        n = len(g)
        k = max(1, int(n * quantile))
        if k < min_per_leg or n < 2 * k:
            continue
        g = g.sort_values(score_col)
        short_ret = float(g[ret_col].iloc[:k].mean())
        long_ret = float(g[ret_col].iloc[-k:].mean())
        out[pd.Timestamp(d)] = long_ret - short_ret
    s = pd.Series(out, name="ls_ret", dtype=float)
    s.index = pd.DatetimeIndex(s.index).normalize()
    s.index.name = "date"
    return s.sort_index()


_DEGEN_SCALE_EPS = 1e-12  # below this std the Sharpe is degenerate (identical values)
_FLAT_SCALE_EPS = 1e-6    # below this std skip sample skew/kurt (scipy precision loss)


def sharpe_monthly(returns: pd.Series) -> float:
    """Per-period Sharpe (NOT annualized) — the input DSR/haircut expect."""
    r = np.asarray(returns.to_numpy(dtype=float), dtype=float)
    r = r[~np.isnan(r)]
    if r.size < 2:
        return float("nan")
    sd = float(r.std(ddof=1))
    # identical values leave a ~1e-17 floating-point residual (not exactly 0);
    # treat a near-zero scale as degenerate -> NaN (no meaningful Sharpe).
    if not np.isfinite(sd) or sd < _DEGEN_SCALE_EPS:
        return float("nan")
    return float(r.mean() / sd)


def _moments(returns: pd.Series) -> tuple[float, float, float, int]:
    """(sharpe, skew, kurtosis-not-excess, n_obs) from a return series.

    Sample skew/kurtosis are only computed when the series is not near-constant
    (``std >= _FLAT_SCALE_EPS``) — scipy emits a precision-loss warning and the
    moments are unreliable for near-flat series (the rank-IC nulls predict these)."""
    from scipy import stats as _stats  # transitive via statsmodels/purgedcv

    r = np.asarray(returns.to_numpy(dtype=float), dtype=float)
    r = r[~np.isnan(r)]
    n = int(r.size)
    if n < 2:
        return float("nan"), 0.0, 3.0, n
    sd = float(r.std(ddof=1))
    sharpe = float(r.mean() / sd) if (np.isfinite(sd) and sd >= _DEGEN_SCALE_EPS) else float("nan")
    skew = 0.0
    kurt = 3.0
    if np.isfinite(sd) and sd >= _FLAT_SCALE_EPS:
        with np.errstate(invalid="ignore"):
            if n >= 3:
                skew = float(_stats.skew(r, bias=False))
            if n >= 4:
                kurt = float(_stats.kurtosis(r, fisher=False, bias=False))
    return sharpe, skew, kurt, n


def strategy_eval(
    strategies: dict[str, pd.Series],
    *,
    benchmark: str | None = None,
    n_trials_grid: tuple[int, ...] = (1, 2, 5, 20),
    min_months_for_cross_tests: int = 12,
) -> dict:
    """Evaluate a set of L-S strategy return series with multiple-testing corrections.

    Args:
        strategies: ``{name: monthly L-S returns}`` (e.g. arm_base / arm_macro /
            placebo / sanity / leave-one-out variants). All series are aligned on
            their common months for the cross-strategy tests.
        benchmark: strategy name used as the SPA benchmark (H0: no strategy beats
            it). Default: the first strategy.
        n_trials_grid: DSR is reported at EACH trial count in the grid (mirrors
            ``phase_c.N_TRIALS_GRID``), because the honest family is the
            project-wide set of strategies tried (Phase B/C arms + controls ≈ 10+),
            not just the few evaluated in this lens. ``dsr_p_conservative`` is the
            p-value at the LARGEST trial count (the most deflation).
        min_months_for_cross_tests: Hansen-SPA/MCS need a real track record to be
            meaningful (studentizing loss differentials on n=2 is not). Below this
            floor the cross-tests are skipped with an explicit record.

    Returns:
        ``{"per_strategy": {name: {sharpe, dsr_by_trials, dsr_p_conservative, ...}},
        "spa": ..., "mcs": ..., "n_trials_grid", "n_months_common", "benchmark"}``.
    """
    names = list(strategies)
    if not names:
        raise ValueError("strategy_eval needs at least one strategy")
    benchmark = benchmark or names[0]
    if benchmark not in strategies:
        raise ValueError(f"benchmark {benchmark!r} not in strategies {names}")
    grid = tuple(int(t) for t in n_trials_grid)
    if not grid or any(t < 1 for t in grid):
        raise ValueError(f"n_trials_grid must be non-empty ints >= 1, got {n_trials_grid}")
    conservative_trials = max(grid)

    # align all series on the common months (intersection) for cross-strategy tests
    aligned = pd.DataFrame({n: strategies[n] for n in names}).sort_index()
    common = aligned.dropna()  # months where EVERY strategy has a return
    n_months = int(len(common))

    per: dict[str, dict] = {}
    for n in names:
        r = strategies[n].dropna()
        sharpe, skew, kurt, n_obs = _moments(r)
        dsr_by: dict[int, dict] = {}
        if np.isfinite(sharpe):
            for nt in grid:
                try:
                    d = deflated_sharpe(sharpe, nt, n_obs, skew=skew, kurtosis=kurt)
                except ValueError as e:  # denom_sq<=0 (extreme skew x sharpe) etc.
                    d = {"dsr": float("nan"), "p_value": float("nan"),
                         "sr_star": float("nan"), "dsr_error": str(e)}
                dsr_by[nt] = {
                    "dsr": float(d["dsr"]),
                    "p_value": float(d["p_value"]),
                    "sr_star": float(d["sr_star"]),
                }
        else:
            dsr_by = {nt: {"dsr": float("nan"), "p_value": float("nan"),
                          "sr_star": float("nan")} for nt in grid}
        per[n] = {
            "sharpe_monthly": sharpe,
            "sharpe_annualized": sharpe * np.sqrt(12) if np.isfinite(sharpe) else float("nan"),
            "mean_monthly": float(r.mean()) if n_obs else float("nan"),
            "n_months": int(n_obs),
            "dsr_by_trials": dsr_by,
            "dsr_p_conservative": dsr_by[conservative_trials]["p_value"],
            "survives_conservative": bool(
                np.isfinite(sharpe)
                and dsr_by[conservative_trials]["p_value"] < 0.05
            ),
        }

    out: dict = {
        "per_strategy": per,
        "n_trials_grid": list(grid),
        "n_months_common": n_months,
        "benchmark": benchmark,
    }

    # cross-strategy tests need >= 2 strategies AND a meaningful common track record
    if len(names) >= 2 and n_months >= min_months_for_cross_tests:
        # losses = -returns (lower = better); rows = strategies, cols = months
        loss = (-common).T.to_numpy(dtype=float)  # (n_strategies, n_months)
        try:
            spa = hansen_spa(
                loss, benchmark_losses=(-common[benchmark]).to_numpy(dtype=float),
                seed=0,
            )
            out["spa"] = spa
        except Exception as e:  # noqa: BLE001 — arch can be finicky on tiny/degenerate sets
            out["spa_error"] = str(e)
        try:
            out["mcs"] = hansen_mcs(loss, seed=0)
        except Exception as e:  # noqa: BLE001
            out["mcs_error"] = str(e)
    else:
        reason = ("insufficient_strategies" if len(names) < 2
                  else "insufficient_common_months")
        out["spa"] = {"skipped": reason, "n_strategies": len(names),
                      "n_months_common": n_months,
                      "min_months_required": min_months_for_cross_tests}
    return out
