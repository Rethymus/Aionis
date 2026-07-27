"""Multiple-testing & backtest-overfit audit, on the ``purgedcv`` wheel.

Turns each model's OOS directional forecast into a long/short strategy and asks
the publishable questions: what's the Sharpe, is it deflated away by the number
of configs searched (DSR), and what's the probability the apparent edge is
overfit (PBO via CSCV)? All heavy lifting delegates to ``purgedcv``.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import structlog

log = structlog.get_logger()
_BARS_PER_YEAR = 252


def _sharpe(returns: np.ndarray) -> float:
    r = np.asarray(returns, float)
    if r.size < 2 or r.std(ddof=0) == 0:
        return float("nan")
    return float(r.mean() / r.std(ddof=0) * np.sqrt(_BARS_PER_YEAR))


def strategy_returns_by_symbol(oos: pd.DataFrame, model_name: str):
    """Long/short return per (symbol, event-date): sign(pred) * realized return.

    Returns (matrix[n_symbols, n_event_dates], prediction_times, evaluation_times)
    aligned to the event-date columns.
    """
    df = oos[["y_true", "symbol", "group", model_name, "prediction_time", "evaluation_time"]]
    df = df.assign(ret=np.sign(df[model_name]) * df["y_true"])
    pivot = df.pivot_table(index="symbol", columns="group", values="ret", aggfunc="mean")
    matrix = pivot.to_numpy()  # (n_symbols, n_event_dates)
    groups = pivot.columns
    meta = df.drop_duplicates("group").set_index("group").loc[groups]
    pt = pd.Series(meta["prediction_time"].to_numpy())
    et = pd.Series(meta["evaluation_time"].to_numpy())
    return matrix, pt, et


def backtest_audit(oos: pd.DataFrame, model_name: str, n_trials: int) -> dict[str, float]:
    """Sharpe + DSR + PBO for a model's OOS long/short strategy.

    ``n_trials`` = number of configs searched (deflates the Sharpe). Each metric is
    wrapped defensively so a ``purgedcv`` quirk reports NaN instead of aborting.
    """
    needed = {model_name, "y_true", "group", "symbol", "prediction_time", "evaluation_time"}
    if not needed <= set(oos.columns):
        return {}

    matrix, pt, et = strategy_returns_by_symbol(oos, model_name)
    # Missing (symbol, event-date) cells => no position taken => 0 return, and
    # purgedcv rejects NaN/inf, so sanitize the matrix before all downstream use.
    matrix = np.nan_to_num(matrix, nan=0.0, posinf=0.0, neginf=0.0)
    mean_ret = matrix.mean(axis=0)
    sharpe = _sharpe(mean_ret)
    per_sym_sharpe = [_sharpe(matrix[i]) for i in range(matrix.shape[0])]
    finite = [s for s in per_sym_sharpe if np.isfinite(s)]
    var_sharpe = float(np.var(finite)) if len(finite) > 1 else 1e-6
    out: dict[str, float] = {"sharpe": sharpe, "n_trials": float(n_trials)}

    try:
        import purgedcv

        out["dsr"] = float(
            purgedcv.deflated_sharpe_ratio(
                mean_ret, n_trials=n_trials, var_sharpe=var_sharpe, bars_per_year=_BARS_PER_YEAR
            )
        )
    except Exception as e:  # pragma: no cover - defensive
        log.warning("dsr_failed", error=str(e))
        out["dsr"] = float("nan")

    try:
        import purgedcv

        n_obs = matrix.shape[1]
        n_splits = max(2, min(16, n_obs // 2))
        n_splits -= n_splits % 2  # CSCV requires even
        if n_splits >= 2 and matrix.shape[0] >= 2 and n_obs >= 2 * n_splits:
            res = purgedcv.probability_of_backtest_overfitting(
                matrix, n_splits=n_splits, prediction_times=pt, evaluation_times=et
            )
            out["pbo"] = float(getattr(res, "pbo", float("nan")))
        else:
            out["pbo"] = float("nan")
    except Exception as e:  # pragma: no cover - defensive
        log.warning("pbo_failed", error=str(e))
        out["pbo"] = float("nan")

    return out
