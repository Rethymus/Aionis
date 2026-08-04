"""Net-cost backtest layer (mount②) — turnover-based execution costs on a long-short strategy.

Exploratory utility that estimates the after-cost per-period Sharpe of a monthly
long-short strategy by applying linear-bps slippage to its one-way turnover. It answers:
given a scenario assumption about per-dollar-traded slippage (bps), what is the after-cost
Sharpe?

Cost model (turnover-based; does NOT consume open prices — a linear-bps model only needs the
fraction of the book traded, not the execution price)::

    For each month-end rebalance t (chronological):
      target_t   = long top-k (+1/k), short bottom-k (-1/k) by score
                   (k = max(1, int(n * quantile)))
      pre_t      = previous rebalance's target weights, reindexed to today's universe
                   (0 for new tickers; 0 everywhere on the FIRST rebalance = from cash)
      turnover_t = one_way_turnover(pre_t, target_t, realized=0)['traded_notional']
                   = fraction of portfolio traded (real position changes; NOT a constant)
      cost_t     = linear_bps_slippage(turnover_t, bps)        # fraction of portfolio lost
      net_return_t = gross_return_t - cost_t                   # per-period, NOT a flat average

The no-drift simplification (``realized=0``) means pre-trade weights are not grown by the
return earned before rebalancing; this is a documented conservative simplification, NOT a
stub. Many production cost models use exactly this approximation.

Reuses existing kernels (no reinvention):
  * aionis.eval.execution_costs.one_way_turnover / linear_bps_slippage  — the cost kernels
  * aionis.eval.strategy_returns.long_short_returns / sharpe_monthly     — gross leg;
    long_short_returns internally subsamples a daily panel to month-end cross-sections
    (rebalance="monthly"), so a daily OOS panel is a valid input here.
  * empyrical.max_drawdown (Apache-2.0, pinned in uv.lock)              — risk metric.

NOT wired to the pipeline; writes NO ledger. Pure functions only — no network I/O, no
mutation of inputs, no LLM calls. Hermetic tests with synthetic fixtures (seed=0).

The execution-timing (next-open) assumption is baked into the caller's ``y_fwd_ret`` (those
are forward returns); next_session_open validation belongs upstream, not in this
turnover-bps cost model.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from aionis.eval.execution_costs import linear_bps_slippage, one_way_turnover


@dataclass(frozen=True)
class NetCostMetrics:
    """Net-cost summary for a monthly long-short strategy.

    Sharpe values are per-period (non-annualized) — multiply by sqrt(12) for annualized.
    """

    gross_sharpe: float
    net_sharpe: float
    avg_turnover: float  # mean one-way turnover fraction per rebalance (0.0 .. 2.0)
    total_cost_bps: float  # cumulative slippage drag over the sample, in bps of portfolio
    n_rebalance: int
    gross_max_drawdown: float
    gross_annual_volatility: float  # monthly returns annualized (std * sqrt(12))


def net_cost_summary(
    oos_panel: pd.DataFrame,
    *,
    bps: float = 5.0,
    quantile: float = 0.2,
    score_col: str = "score",
    ret_col: str = "y_fwd_ret",
    date_col: str = "date",
    ticker_col: str = "ticker",
    long_threshold: float = 1e-10,
) -> NetCostMetrics:
    """Compute after-cost (linear-bps slippage on turnover) metrics for an OOS score panel.

    Args:
        oos_panel: OOS score panel with columns [date, ticker, score, y_fwd_ret]. May be
            daily — long_short_returns subsamples to month-end cross-sections internally.
        bps: slippage per dollar traded (scenario assumption). Default 5.0 = S&P 500 liquid.
            Non-negative by contract; negative values raise ValueError.
        quantile: leg size as a fraction of the cross-section (default 0.2 = quintile).
        score_col / ret_col: ranking signal / forward-return column names.
        date_col / ticker_col: date / ticker column names.
        long_threshold: minimum drifted weight to count a position as long (delegates to
            one_way_turnover).

    Returns:
        NetCostMetrics. gross/net Sharpe are NaN when fewer than 2 rebalances qualify.

    Raises:
        ValueError: if bps < 0 (negative costs are an invalid scenario assumption).
    """
    import empyrical

    from aionis.eval.strategy_returns import long_short_returns, sharpe_monthly

    if bps < 0:
        raise ValueError(
            f"Negative bps rejected: {bps}. "
            "Bps parameter must be non-negative as a scenario assumption."
        )

    # 1. Gross monthly long-short returns (long_short_returns handles month-end subsampling
    #    of a daily panel via rebalance="monthly").
    gross_returns = long_short_returns(
        oos_panel, score_col=score_col, ret_col=ret_col, quantile=quantile
    )

    if len(gross_returns) < 2:
        return NetCostMetrics(
            gross_sharpe=float("nan"),
            net_sharpe=float("nan"),
            avg_turnover=0.0,
            total_cost_bps=0.0,
            n_rebalance=0,
            gross_max_drawdown=float("nan"),
            gross_annual_volatility=float("nan"),
        )

    gross_sharpe_val = float(sharpe_monthly(gross_returns))

    # 2. Per-rebalance turnover and cost (chronological). Reconstruct the SAME month-end
    #    cross-sections long_short_returns selects (last available trading date per month).
    panel = oos_panel.dropna(subset=[score_col]).copy()
    panel[date_col] = pd.to_datetime(panel[date_col]).dt.normalize()
    period = panel[date_col].dt.to_period("M")
    month_last = panel.groupby(period)[date_col].transform("max")
    month_end_panel = panel[panel[date_col] == month_last]

    cost_by_date: dict[pd.Timestamp, float] = {}
    turnover_by_date: dict[pd.Timestamp, float] = {}
    prev_target: pd.Series | None = None

    for rebalance_date in sorted(month_end_panel[date_col].unique()):
        df = month_end_panel[month_end_panel[date_col] == rebalance_date]
        n = len(df)
        k = max(1, int(n * quantile))
        if n < 2 * k:
            continue

        df_sorted = df.sort_values(score_col)
        tickers = df_sorted[ticker_col].to_numpy()
        target = pd.Series(0.0, index=tickers)
        target[df_sorted[ticker_col].iloc[-k:].to_numpy()] = 1.0 / k  # long top-k
        target[df_sorted[ticker_col].iloc[:k].to_numpy()] = -1.0 / k  # short bottom-k

        if prev_target is None:
            # First rebalance: build from cash (pre-trade = 0).
            pre = pd.Series(0.0, index=target.index)
            tgt = target
        else:
            # Subsequent: previous target reindexed onto today's universe; membership
            # changes (newly entered / freshly absent tickers) contribute 0 on the missing
            # side, which is exactly the position change we want to charge for.
            union = target.index.union(prev_target.index)
            pre = prev_target.reindex(union, fill_value=0.0)
            tgt = target.reindex(union, fill_value=0.0)

        # No-drift simplification (documented): pre-trade weights are not grown by the
        # pre-rebalance return. realized=0 → drift_adjusted = pre.
        realized = pd.Series(0.0, index=pre.index)

        turnover = one_way_turnover(pre, tgt, realized, long_threshold=long_threshold)
        traded_notional = float(turnover["traded_notional"])
        cost = linear_bps_slippage(traded_notional, bps)  # fraction of portfolio

        cost_by_date[rebalance_date] = float(cost)
        turnover_by_date[rebalance_date] = traded_notional
        prev_target = target

    # 3. Per-period net returns: each period less its OWN cost (not a flat average).
    if cost_by_date:
        cost_series = pd.Series(cost_by_date).reindex(gross_returns.index, fill_value=0.0)
    else:
        cost_series = pd.Series(0.0, index=gross_returns.index)
    net_returns = gross_returns - cost_series
    net_sharpe_val = float(sharpe_monthly(net_returns))

    # 4. Gross risk metrics via empyrical (no hand-rolled formulas).
    gross_max_dd = float(empyrical.max_drawdown(gross_returns))
    gross_ann_vol = float(gross_returns.std(ddof=1) * np.sqrt(12))

    n_reb = len(turnover_by_date)
    avg_turnover = float(np.mean(list(turnover_by_date.values()))) if n_reb else 0.0
    total_cost_bps = float(cost_series.sum() * 1e4)

    return NetCostMetrics(
        gross_sharpe=gross_sharpe_val,
        net_sharpe=net_sharpe_val,
        avg_turnover=avg_turnover,
        total_cost_bps=total_cost_bps,
        n_rebalance=n_reb,
        gross_max_drawdown=gross_max_dd,
        gross_annual_volatility=gross_ann_vol,
    )
