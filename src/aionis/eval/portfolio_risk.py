"""Risk metrics summary for a return series (display-only, leakage-safe).

Pure computation transform: reads a return series, returns a RiskSummary frozen dataclass.
Uses empyrical where available; implements VaR/CVaR directly. Writes NO ledger/frozen/OOS
data — this is a display utility analogous to ``ff5_residual`` and ``score_calibration``.

Anti-leakage contract (this is the load-bearing part):
  - This module ONLY computes descriptive statistics on a passed-in return series.
    It does NOT fetch prices, does NOT access forward-looking data, does NOT write
    to ``runs/ledger.jsonl``, does NOT modify frozen configs, and does NOT affect
    any out-of-sample (OOS) research result.
  - The input is a pd.Series or np.ndarray of periodic returns (already computed).
    NaN values are dropped; fewer than 2 finite returns raises ValueError.
  - All metrics are either pure transforms (annual_return, sharpe_ratio, sortino_ratio,
    max_drawdown, calmar_ratio) via empyrical (a library of deterministic formulas)
    or simple percentile/mean operations (VaR, CVaR).
  - This module is NOT a research estimator — it is a terminal display layer that
    summarizes already-realized returns. The research verdict (combined rank-IC)
    lives in the ledger and is untouched by this code.

The empyrical dependency (already in uv.lock) provides:
  - annual_return: geometric mean, annualized
  - sharpe_ratio: (mean - rf) / std, annualized
  - sortino_ratio: (mean - rf) / downside_std, annualized
  - max_drawdown: maximum peak-to-trough decline
  - calmar_ratio: annual_return / abs(max_drawdown)

VaR/CVaR (implemented directly):
  - VaR_95: negative 5th percentile of returns (loss at 95% confidence)
  - CVaR_95: mean of returns at or below the 5th percentile (expected loss given
    we are in the worst 5% of outcomes)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

try:
    import empyrical

    _EMPYRICAL_AVAILABLE = True
except ImportError:
    _EMPYRICAL_AVAILABLE = False


@dataclass(frozen=True)
class RiskSummary:
    """Risk metrics for a return series (all fields are JSON-safe floats)."""

    n_periods: int  # number of finite return observations
    annual_return: float  # geometric mean, annualized
    sharpe: float  # (mean - rf) / std, annualized
    sortino: float  # (mean - rf) / downside_std, annualized
    max_drawdown: float  # maximum peak-to-trough decline (negative)
    calmar: float  # annual_return / abs(max_drawdown)
    var_95: float  # 5th percentile of returns (negative for loss)
    cvar_95: float  # mean of returns at/below 5th percentile (negative)
    periods_per_year: int  # annualization frequency (252 for daily, 12 for monthly)


def summarize(
    returns: pd.Series | np.ndarray,
    periods_per_year: int = 252,
    risk_free: float = 0.0,
) -> RiskSummary:
    """Compute risk metrics for a return series.

    Args:
        returns: Periodic returns (pd.Series or np.ndarray). NaN values are dropped.
        periods_per_year: Annualization frequency (252 for daily, 12 for monthly).
        risk_free: Annual risk-free rate (default 0.0).

    Returns:
        RiskSummary with all metrics computed.

    Raises:
        ValueError: If fewer than 2 finite returns are provided.
    """
    if isinstance(returns, pd.Series):
        arr = returns.to_numpy()
    else:
        arr = np.asarray(returns, dtype=float)

    # Drop NaN values
    finite = arr[np.isfinite(arr)]
    n_periods = len(finite)

    if n_periods < 2:
        raise ValueError(f"need >=2 returns, got {n_periods}")

    # Use empyrical if available; fallback to direct implementations
    if _EMPYRICAL_AVAILABLE:
        # empyrical expects period='daily'/'monthly' and annualization=<int>
        # We map periods_per_year to the appropriate period string
        period_map = {252: "daily", 52: "weekly", 12: "monthly", 4: "quarterly", 1: "yearly"}
        period = period_map.get(periods_per_year, "daily")  # Default to daily

        annual_return = float(
            empyrical.annual_return(finite, period=period, annualization=periods_per_year)
        )
        sharpe = float(
            empyrical.sharpe_ratio(finite, risk_free, period=period, annualization=periods_per_year)
        )
        sortino = float(
            empyrical.sortino_ratio(
                finite, risk_free, period=period, annualization=periods_per_year
            )
        )
        max_dd = float(empyrical.max_drawdown(finite))
        # calmar_ratio has different signature - just use annualization
        calmar = float(empyrical.calmar_ratio(finite, risk_free, annualization=periods_per_year))
    else:
        # Fallback implementations (should not happen in Aionis environment)
        _mean = finite.mean()
        _std = finite.std()
        _ann_mean = (1 + _mean) ** periods_per_year - 1
        _ann_std = _std * np.sqrt(periods_per_year)
        annual_return = float(_ann_mean)

        if _std > 0:
            sharpe = float((_ann_mean - risk_free) / _ann_std)
        else:
            sharpe = 0.0

        # Downside deviation: std of returns below mean
        downside = finite[finite < _mean]
        if len(downside) > 0:
            downside_std = downside.std() * np.sqrt(periods_per_year)
            sortino = float((_ann_mean - risk_free) / downside_std) if downside_std > 0 else 0.0
        else:
            sortino = 0.0

        # Max drawdown: cumulative max tracking
        cum_returns = np.cumprod(1 + finite)
        running_max = np.maximum.accumulate(cum_returns)
        drawdowns = (cum_returns - running_max) / running_max
        max_dd = float(drawdowns.min())

        if max_dd < 0:
            calmar = float(annual_return / abs(max_dd))
        else:
            calmar = 0.0

    # VaR/CVaR (always direct implementation)
    # VaR_95: 5th percentile of returns (will be negative for loss distribution)
    var_95 = float(np.percentile(finite, 5))

    # CVaR_95: mean of returns at/below 5th percentile (expected tail return)
    var_threshold = np.percentile(finite, 5)
    tail_losses = finite[finite <= var_threshold]
    cvar_95 = float(tail_losses.mean())

    return RiskSummary(
        n_periods=n_periods,
        annual_return=round(annual_return, 4),
        sharpe=round(sharpe, 4),
        sortino=round(sortino, 4),
        max_drawdown=round(max_dd, 4),
        calmar=round(calmar, 4),
        var_95=round(var_95, 4),
        cvar_95=round(cvar_95, 4),
        periods_per_year=periods_per_year,
    )


def risk_summary_to_jsonable(s: RiskSummary) -> dict[str, Any]:
    """JSON-safe view of RiskSummary (dataclasses are not json.dumps-able).

    All float fields are rounded to 4 decimal places for consistent serialization.
    """
    return {
        "n_periods": s.n_periods,
        "annual_return": s.annual_return,
        "sharpe": s.sharpe,
        "sortino": s.sortino,
        "max_drawdown": s.max_drawdown,
        "calmar": s.calmar,
        "var_95": s.var_95,
        "cvar_95": s.cvar_95,
        "periods_per_year": s.periods_per_year,
    }
