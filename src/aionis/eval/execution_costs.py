"""Execution cost kernel: next-open timing, turnover, linear bps slippage.

Pure functions only — no network I/O, no mutation of inputs. All costs are
SCENARIO ASSUMPTIONS, not measured real costs. The bps parameter is explicit
and non-negative by validation — negative values are rejected.

Functions:
- next_session_open: Map signal close dates to next available session opens.
- one_way_turnover: Compute traded notional from drift-adjusted pre-trade → target.
- linear_bps_slippage: Apply cost = bps_param * traded_notional.
"""

from __future__ import annotations

import pandas as pd


def next_session_open(
    signal_dates: pd.Series,
    session_opens: pd.DataFrame,
    on: str = "date",
    open_col: str = "open",
) -> pd.Series:
    """Map signal close dates to the NEXT session's open price.

    Execution happens at the next available session open after a close-time signal.
    Missing open price or halted instrument → FAIL CLOSED (raises ValueError).

    Args:
        signal_dates: Series of signal generation timestamps (close times).
        session_opens: DataFrame with date index and open price columns.
            Must contain (date, open) columns for all tickers in signals.
        on: Column name in session_opens index to align with signal_dates.
        open_col: Column name containing open prices.

    Returns:
        Series indexed like signal_dates with next-session open prices.

    Raises:
        ValueError: If signal date equals execution date (same-day rejected).
        ValueError: If next session open price is missing (fail closed).
        ValueError: If signal date is after available session data.

    Example:
        >>> signals = pd.Series(pd.to_datetime(['2024-01-02', '2024-01-03']))
        >>> opens = pd.DataFrame(
        ...     {'open': [100.0, 101.0, 102.0]},
        ...     index=pd.to_datetime(['2024-01-02', '2024-01-03', '2024-01-04'])
        ... )
        >>> next_session_open(signals, opens)
        # 2024-01-02 signal → 2024-01-03 open = 101.0
        # 2024-01-03 signal → 2024-01-04 open = 102.0
    """
    if signal_dates.empty:
        return pd.Series(dtype=float, index=signal_dates.index)

    # Align signal dates with session index
    signal_aligned = pd.to_datetime(signal_dates)
    session_idx = pd.to_datetime(session_opens.index)

    # Find next session index for each signal
    next_idx = session_idx.searchsorted(signal_aligned, side="right")

    # Validate: signal date is within available data (not past the end)
    out_of_bounds = next_idx >= len(session_idx)
    if out_of_bounds.any():
        offender_idx = out_of_bounds.idxmax() if hasattr(out_of_bounds, "idxmax") else 0
        if hasattr(signal_aligned, "iloc"):
            offender_date = signal_aligned.iloc[offender_idx]
        else:
            offender_date = signal_aligned[offender_idx]
        raise ValueError(
            f"Signal date {offender_date} is beyond available session data. "
            "Cannot determine next session open."
        )

    # Validate: same-day execution (signal equals next session, not allowed)
    # This happens when searchsorted returns index pointing to same date
    next_sessions = session_idx[next_idx]
    same_day_mask = next_sessions == signal_aligned
    if same_day_mask.any():
        # Find first offender for error message
        offender_idx = same_day_mask.idxmax() if hasattr(same_day_mask, "idxmax") else 0
        if hasattr(signal_aligned, "iloc"):
            offender_date = signal_aligned.iloc[offender_idx]
        else:
            offender_date = signal_aligned[offender_idx]
        raise ValueError(
            f"Same-day execution rejected: signal at {offender_date} "
            "would execute on same session. Signals must close BEFORE execution."
        )

    # Extract next session open prices
    execution_opens = session_opens.loc[next_sessions, open_col]

    # Validate: no missing opens (fail closed)
    if execution_opens.isna().any():
        missing_dates = execution_opens[execution_opens.isna()].index.tolist()
        raise ValueError(
            f"Fail closed: next session open prices missing for {len(missing_dates)} signals. "
            f"Missing dates: {missing_dates[:3]}... (halted or no data)"
        )

    return pd.Series(execution_opens.values, index=signal_dates.index, dtype=float)


def one_way_turnover(
    pre_trade_weights: pd.Series,
    target_weights: pd.Series,
    realized_returns: pd.Series,
    long_threshold: float = 1e-10,
) -> dict:
    """Compute one-way turnover from drift-adjusted pre-trade to target weights.

    Turnover is the sum of absolute trades (long + short sides tracked separately).
    Pre-trade weights are drift-adjusted by realized returns BEFORE measuring trades.

    Args:
        pre_trade_weights: Weights before execution (sum = 1, can have long/short).
        target_weights: Desired weights after execution (sum = 1, can have long/short).
        realized_returns: Returns between signal and execution (pre-trade drift).
        long_threshold: Minimum weight to count as long (below = short/zero).

    Returns:
        Dict with:
            - traded_notional: Total absolute trades (sum of long + short trades).
            - long_trades: Sum of absolute trades on long side.
            - short_trades: Sum of absolute trades on short side.
            - drift_adjusted_pre: Pre-trade weights grown by realized returns.

    Formula:
        drift_adjusted = pre_trade_weights * (1 + realized_returns)
        trades = target_weights - drift_adjusted
        long_trades = sum(abs(trades) where drift_adjusted > long_threshold)
        short_trades = sum(abs(trades) where drift_adjusted <= long_threshold)
        traded_notional = long_trades + short_trades

    Example:
        >>> pre = pd.Series([0.5, 0.3, 0.2])  # 50%, 30%, 20% long
        >>> target = pd.Series([0.6, 0.3, 0.1])
        >>> returns = pd.Series([0.01, -0.01, 0.0])
        >>> # Drift-adjusted: [0.505, 0.297, 0.2]
        >>> # Trades: [0.095, 0.003, -0.1]
        >>> # Long trades: 0.095 + 0.003 = 0.098
        >>> # Short trades: abs(-0.1) = 0.1
        >>> # Total: 0.198
    """
    if len(pre_trade_weights) != len(target_weights):
        raise ValueError(
            f"Weight length mismatch: pre_trade={len(pre_trade_weights)}, "
            f"target={len(target_weights)}"
        )
    if len(pre_trade_weights) != len(realized_returns):
        raise ValueError(
            f"Weight/returns length mismatch: weights={len(pre_trade_weights)}, "
            f"returns={len(realized_returns)}"
        )

    # Drift-adjust pre-trade weights by realized returns
    drift_adjusted = pre_trade_weights * (1.0 + realized_returns)

    # Compute trades from drift-adjusted to target
    trades = target_weights - drift_adjusted

    # Split into long/short sides based on drift-adjusted weights
    is_long = drift_adjusted > long_threshold

    long_trades = trades[is_long].abs().sum()
    short_trades = trades[~is_long].abs().sum()
    traded_notional = long_trades + short_trades

    return {
        "traded_notional": float(traded_notional),
        "long_trades": float(long_trades),
        "short_trades": float(short_trades),
        "drift_adjusted_pre": drift_adjusted,
    }


def linear_bps_slippage(
    traded_notional: float,
    bps_param: float,
) -> float:
    """Apply linear bps slippage: cost = bps_param * traded_notional.

    This is a SCENARIO ASSUMPTION, not a measured real cost. The bps parameter
    must be explicit and non-negative; negative values are rejected.

    Args:
        traded_notional: Total absolute trades (from one_way_turnover).
        bps_param: Basis points parameter (non-negative). 1 bps = 0.0001.

    Returns:
        Slippage cost in same units as traded_notional.

    Raises:
        ValueError: If bps_param is negative (rejected as invalid assumption).

    Formula:
        cost = bps_param * 0.0001 * traded_notional

    Example:
        >>> traded_notional = 1_000_000  # $1M
        >>> bps_param = 5.0  # 5 bps = 0.05%
        >>> cost = linear_bps_slippage(traded_notional, bps_param)
        >>> # cost = 5 * 0.0001 * 1_000_000 = 500.0
    """
    if bps_param < 0:
        raise ValueError(
            f"Negative bps_param rejected: {bps_param}. "
            "Bps parameter must be non-negative as a scenario assumption."
        )

    cost = bps_param * 1e-4 * traded_notional
    return float(cost)
