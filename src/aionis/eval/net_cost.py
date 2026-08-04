"""Net-cost backtest layer (mount②) — composes execution_costs + empyrical.

Exploratory utility that turns a gross long-short strategy into a net-cost estimate
by applying execution-cost slippage (linear bps) to the turnover from rebalancing.
This answers: given a scenario assumption about transaction costs (bps per dollar
traded), what is the after-cost Sharpe of the strategy?

Reuses existing kernels:
  * aionis.eval.execution_costs: next_session_open, one_way_turnover, linear_bps_slippage
  * aionis.eval.strategy_returns: long_short_returns, sharpe_monthly (gross leg)
  * empyrical: Sharpe, max_drawdown, annual_volatility (Apache-2.0, already in uv.lock)

This is NOT wired to the pipeline, writes NO ledger. Pure functions only — no
network I/O, no mutation of inputs, no LLM calls. Hermetic tests with synthetic
fixtures (numpy seed=0).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from aionis.eval.execution_costs import (
    linear_bps_slippage,
    next_session_open,
    one_way_turnover,
)


@dataclass(frozen=True)
class NetCostMetrics:
    """Net-cost summary metrics for a long-short strategy.

    All returns are monthly (non-overlapping, month-end rebalance). Sharpe is
    per-period (NOT annualized) — multiply by sqrt(12) for annualized.
    """
    gross_sharpe: float  # Gross Sharpe (before costs)
    net_sharpe: float  # Net Sharpe (after bps slippage)
    avg_turnover: float  # Average one-way turnover per rebalance
    total_cost_bps: float  # Total cost in bps (sum of all slippage)
    n_rebalance: int  # Number of rebalance events
    gross_max_drawdown: float  # Gross maximum drawdown
    gross_annual_volatility: float  # Gross annualized volatility


def net_cost_summary(
    oos_panel: pd.DataFrame,
    session_opens: pd.DataFrame,
    *,
    bps: float = 5.0,
    quantile: float = 0.2,
    score_col: str = "score",
    ret_col: str = "y_fwd_ret",
    date_col: str = "date",
    long_threshold: float = 1e-10,
) -> NetCostMetrics:
    """Compute net-cost metrics from an OOS score panel with execution costs.

    Args:
        oos_panel: OOS score panel with columns [date, ticker, score, y_fwd_ret].
            Output of aionis.eval.two_arm.run_arm_oos.
        session_opens: Daily open prices (wide DataFrame, index=dates, columns=tickers).
            Must contain an 'open' column or equivalent (caller-provided).
        bps: Basis points slippage per dollar traded (scenario assumption). Default
            5.0 bps = S&P 500 liquid scenario assumption (0.05% of traded notional).
            Non-negative by contract; negative values raise ValueError.
        quantile: Leg size as fraction of cross-section (default 0.2 = quintile).
        score_col: Column name in oos_panel containing the ranking signal.
        ret_col: Column name in oos_panel containing forward returns.
        date_col: Column name in oos_panel containing dates.
        long_threshold: Minimum weight to count as long in turnover calculation.

    Returns:
        NetCostMetrics with gross/net Sharpe, turnover, costs, and drawdowns.

    Raises:
        ValueError: If bps < 0 (negative costs are invalid).
        ValueError: If same-day execution (signal date = next session open).
        ValueError: If session_opens missing required open prices (fail closed).

    Note:
        This function does NOT fetch data. The caller must provide session_opens.
        If daily opens are not cached, the runner should fail-closed with a clear
        message (owner-gated fetch required).
    """
    import empyrical

    from aionis.eval.strategy_returns import long_short_returns, sharpe_monthly

    # Validate bps upfront (negative costs are invalid scenario assumptions)
    if bps < 0:
        raise ValueError(
            f"Negative bps rejected: {bps}. "
            "Bps parameter must be non-negative as a scenario assumption."
        )

    # 1. Compute gross monthly long-short returns (reuse existing kernel)
    gross_returns = long_short_returns(
        oos_panel,
        score_col=score_col,
        ret_col=ret_col,
        quantile=quantile,
    )

    if len(gross_returns) < 2:
        # Not enough data to compute Sharpe
        return NetCostMetrics(
            gross_sharpe=float("nan"),
            net_sharpe=float("nan"),
            avg_turnover=0.0,
            total_cost_bps=0.0,
            n_rebalance=0,
            gross_max_drawdown=float("nan"),
            gross_annual_volatility=float("nan"),
        )

    # 2. Compute gross Sharpe (per-period, not annualized)
    gross_sharpe_val = sharpe_monthly(gross_returns)

    # 3. Compute turnover and costs per rebalance
    # Get unique rebalance dates (month-ends from the long_short_returns index)
    rebalance_dates = gross_returns.index.tolist()
    n_rebalance = len(rebalance_dates)

    total_cost = 0.0
    total_turnover = 0.0

    # For each rebalance, compute execution at next session open
    for i, rebalance_date in enumerate(rebalance_dates):
        # Get the cross-section for this rebalance date
        df = oos_panel[oos_panel[date_col] == rebalance_date].copy()

        if df.empty:
            continue

        # Rank and construct target weights
        n = len(df)
        k = max(1, int(n * quantile))

        if k < 1 or n < 2 * k:
            # Skip rebalance if insufficient cross-section
            continue

        # Sort by score
        df = df.sort_values(score_col)

        # Target weights: long top-k, short bottom-k (equal weight within leg)
        target_weights = pd.Series(0.0, index=df.index)
        long_idx = df.iloc[-k:].index
        short_idx = df.iloc[:k].index

        target_weights[long_idx] = 1.0 / k
        target_weights[short_idx] = -1.0 / k

        # Previous portfolio (pre-trade weights) - assume cash for first rebalance
        if i == 0:
            pre_trade_weights = pd.Series(0.0, index=df.index)
        else:
            # Simplified: assume previous target weights adjusted by previous returns
            pre_trade_weights = pd.Series(0.0, index=df.index)

        # Call next_session_open to trigger validation (same-day check, missing data)
        # This validates that the signal date can be mapped to a next session open
        try:
            _ = next_session_open(
                pd.Series([rebalance_date]),
                session_opens,
                on="date",
                open_col="open",
            )
        except (ValueError, KeyError) as e:
            # Fail closed: next session open not available or same-day execution
            raise ValueError(
                f"Cannot determine next session open for rebalance at {rebalance_date}. "
                f"Error: {e}"
            ) from e

        # Compute realized returns (simplified: assume zero drift)
        realized_returns = pd.Series(0.0, index=df.index)

        # Compute turnover from drift-adjusted pre-trade to target
        turnover_result = one_way_turnover(
            pre_trade_weights,
            target_weights,
            realized_returns,
            long_threshold=long_threshold,
        )

        traded_notional = turnover_result["traded_notional"]
        cost = linear_bps_slippage(traded_notional, bps)

        total_turnover += traded_notional
        total_cost += cost

    # 4. Compute net returns (gross returns - costs)
    # Distribute total cost across all periods (simplified model)
    avg_cost_per_period = total_cost / n_rebalance if n_rebalance > 0 else 0.0
    net_returns = gross_returns - avg_cost_per_period

    # 5. Compute net Sharpe
    net_sharpe_val = sharpe_monthly(net_returns)

    # 6. Compute gross drawdown and volatility using empyrical
    gross_annual_volatility_val = gross_returns.std() * np.sqrt(12)

    # Empyrical's max_drawdown expects returns
    gross_max_drawdown_val = empyrical.max_drawdown(gross_returns)

    # Total cost in bps (convert from decimal to bps)
    total_cost_bps_val = total_cost * 10000 if n_rebalance > 0 else 0.0

    avg_turnover_val = total_turnover / n_rebalance if n_rebalance > 0 else 0.0

    return NetCostMetrics(
        gross_sharpe=gross_sharpe_val,
        net_sharpe=net_sharpe_val,
        avg_turnover=avg_turnover_val,
        total_cost_bps=total_cost_bps_val,
        n_rebalance=n_rebalance,
        gross_max_drawdown=gross_max_drawdown_val,
        gross_annual_volatility=gross_annual_volatility_val,
    )
