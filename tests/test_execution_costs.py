"""Tests for execution_costs.py — hermetic with hand-computed oracles.

All test fixtures use synthetic panels; no network I/O, no real data.
Expected values are shown in comments with explicit arithmetic.
"""

import pandas as pd
import pytest

from aionis.eval.execution_costs import (
    linear_bps_slippage,
    next_session_open,
    one_way_turnover,
)


def test_next_session_open_basic() -> None:
    """Signal at 2024-01-02 close → execution at 2024-01-03 open.

    Oracle:
        signal 2024-01-02 → next session 2024-01-03 → open = 101.0
        signal 2024-01-03 → next session 2024-01-04 → open = 102.0
    """
    signals = pd.Series(
        pd.to_datetime(["2024-01-02", "2024-01-03"]),
        name="signal_date",
    )
    opens = pd.DataFrame(
        {"open": [100.0, 101.0, 102.0]},
        index=pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
    )

    result = next_session_open(signals, opens)

    expected = pd.Series([101.0, 102.0], index=signals.index, dtype=float)
    pd.testing.assert_series_equal(result, expected)


def test_next_session_open_rejects_same_day() -> None:
    """Same-day execution is rejected: signal and execution on same session.

    Oracle: ValueError because only one session exists (no next session).
    This tests the boundary case where signal_date == only_available_session.
    """
    signals = pd.Series(pd.to_datetime(["2024-01-02"]))
    opens = pd.DataFrame(
        {"open": [100.0]},
        index=pd.to_datetime(["2024-01-02"]),
    )

    with pytest.raises(ValueError, match="beyond available session data"):
        next_session_open(signals, opens)


def test_next_session_open_fail_closed_missing_open() -> None:
    """Missing next session open → FAIL CLOSED (raises ValueError).

    Oracle: ValueError because next session (2024-01-03) has NaN open.
    """
    signals = pd.Series(pd.to_datetime(["2024-01-02"]))
    opens = pd.DataFrame(
        {"open": [100.0, float("nan")]},
        index=pd.to_datetime(["2024-01-02", "2024-01-03"]),
    )

    with pytest.raises(ValueError, match="Fail closed.*next session open"):
        next_session_open(signals, opens)


def test_next_session_open_fail_closed_halted() -> None:
    """Halted instrument (no next session) → FAIL CLOSED.

    Oracle: ValueError because signal at 2024-01-02 has no session after it.
    """
    signals = pd.Series(pd.to_datetime(["2024-01-02"]))
    opens = pd.DataFrame(
        {"open": [100.0]},
        index=pd.to_datetime(["2024-01-02"]),
    )

    with pytest.raises(ValueError, match="Signal date.*beyond available"):
        next_session_open(signals, opens)


def test_next_session_open_empty_signals() -> None:
    """Empty signals → empty Series with same index type.

    Oracle: len() == 0, dtype == float.
    """
    signals = pd.Series([], dtype="datetime64[ns]")
    opens = pd.DataFrame(
        {"open": [100.0]},
        index=pd.to_datetime(["2024-01-02"]),
    )

    result = next_session_open(signals, opens)

    assert len(result) == 0
    assert result.dtype == float


def test_one_way_turnover_basic_with_drift() -> None:
    """Drift-adjusted pre-trade weights → traded notional (long/short split).

    Oracle:
        pre = [0.5, 0.3, 0.2]
        returns = [0.01, -0.01, 0.0]
        drift_adjusted = [0.5*1.01, 0.3*0.99, 0.2*1.0] = [0.505, 0.297, 0.2]
        target = [0.6, 0.3, 0.1]
        trades = [0.6-0.505, 0.3-0.297, 0.1-0.2] = [0.095, 0.003, -0.1]

        long_trades (drift > 0): abs(0.095) + abs(0.003) + abs(-0.1) = 0.198
        short_trades (drift ≤ 0): none = 0.0
        total = 0.198 + 0.0 = 0.198
    """
    pre = pd.Series([0.5, 0.3, 0.2])
    target = pd.Series([0.6, 0.3, 0.1])
    returns = pd.Series([0.01, -0.01, 0.0])

    result = one_way_turnover(pre, target, returns)

    assert result["traded_notional"] == pytest.approx(0.198)
    assert result["long_trades"] == pytest.approx(0.198)
    assert result["short_trades"] == pytest.approx(0.0)
    pd.testing.assert_series_equal(
        result["drift_adjusted_pre"],
        pd.Series([0.505, 0.297, 0.2]),
        check_exact=False,
        atol=1e-10,
    )


def test_one_way_turnover_with_short_positions() -> None:
    """Long and short positions traded separately.

    Oracle:
        pre = [0.4, -0.2, 0.1]  (short second position)
        returns = [0.0, 0.05, 0.0]
        drift_adjusted = [0.4, -0.21, 0.1]
        target = [0.5, -0.3, 0.2]
        trades = [0.1, -0.09, 0.1]

        long_trades (drift > 1e-10): abs(0.1) + abs(0.1) = 0.2
        short_trades (drift ≤ 1e-10): abs(-0.09) = 0.09
        total = 0.2 + 0.09 = 0.29
    """
    pre = pd.Series([0.4, -0.2, 0.1])
    target = pd.Series([0.5, -0.3, 0.2])
    returns = pd.Series([0.0, 0.05, 0.0])

    result = one_way_turnover(pre, target, returns)

    assert result["traded_notional"] == pytest.approx(0.29)
    assert result["long_trades"] == pytest.approx(0.2)
    assert result["short_trades"] == pytest.approx(0.09)


def test_one_way_turnover_length_mismatch_raises() -> None:
    """Weight length mismatch → ValueError.

    Oracle: ValueError because pre (3) ≠ target (2).
    """
    pre = pd.Series([0.5, 0.3, 0.2])
    target = pd.Series([0.6, 0.4])
    returns = pd.Series([0.0, 0.0, 0.0])

    with pytest.raises(ValueError, match="Weight length mismatch"):
        one_way_turnover(pre, target, returns)


def test_one_way_turnover_returns_mismatch_raises() -> None:
    """Returns length mismatch → ValueError.

    Oracle: ValueError because weights (3) ≠ returns (2).
    """
    pre = pd.Series([0.5, 0.3, 0.2])
    target = pd.Series([0.6, 0.3, 0.1])
    returns = pd.Series([0.0, 0.0])

    with pytest.raises(ValueError, match="Weight/returns length mismatch"):
        one_way_turnover(pre, target, returns)


def test_linear_bps_slippage_basic() -> None:
    """Linear bps cost: bps * notional * 1e-4.

    Oracle: cost = 5.0 * 1_000_000 * 0.0001 = 500.0
    """
    traded = 1_000_000
    bps = 5.0

    result = linear_bps_slippage(traded, bps)

    assert result == pytest.approx(500.0)


def test_linear_bps_slippage_zero_bps() -> None:
    """Zero bps → zero cost.

    Oracle: cost = 0.0 * 1_000_000 * 0.0001 = 0.0
    """
    traded = 1_000_000
    bps = 0.0

    result = linear_bps_slippage(traded, bps)

    assert result == pytest.approx(0.0)


def test_linear_bps_slippage_rejects_negative_bps() -> None:
    """Negative bps → rejected (ValueError).

    Oracle: ValueError because bps_param = -5.0 < 0.
    """
    traded = 1_000_000
    bps = -5.0

    with pytest.raises(ValueError, match="Negative bps_param rejected"):
        linear_bps_slippage(traded, bps)


def test_linear_bps_slippage_zero_notional() -> None:
    """Zero traded notional → zero cost.

    Oracle: cost = 5.0 * 0 * 0.0001 = 0.0
    """
    traded = 0.0
    bps = 5.0

    result = linear_bps_slippage(traded, bps)

    assert result == pytest.approx(0.0)


def test_linear_bps_slippage_high_bps() -> None:
    """High bps (100 bps = 1%) scales linearly.

    Oracle: cost = 100.0 * 1_000_000 * 0.0001 = 10_000.0
    """
    traded = 1_000_000
    bps = 100.0

    result = linear_bps_slippage(traded, bps)

    assert result == pytest.approx(10_000.0)


def test_duplicate_tickers_deterministic_handling() -> None:
    """Duplicate tickers in signals → deterministic (order preserved).

    Oracle:
        Signals: ['A', 'A', 'B']
        Execution opens: [101.0, 101.0, 102.0]
        Index alignment is preserved.
    """
    signals = pd.Series(
        pd.to_datetime(["2024-01-02", "2024-01-02", "2024-01-03"]),
        name="signal_date",
    )
    opens = pd.DataFrame(
        {"open": [100.0, 101.0, 102.0]},
        index=pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"]),
    )

    result = next_session_open(signals, opens)

    expected = pd.Series([101.0, 101.0, 102.0], index=signals.index, dtype=float)
    pd.testing.assert_series_equal(result, expected)


def test_ranking_ties_deterministic() -> None:
    """Tied weights → deterministic turnover computation.

    Oracle:
        pre = [0.5, 0.5]  (tied)
        target = [0.6, 0.4]  (rebalance to break tie)
        returns = [0.0, 0.0]
        trades = [0.1, -0.1]
        long_trades = 0.1 + 0.1 = 0.2
        short_trades = 0.0
        total = 0.2
    """
    pre = pd.Series([0.5, 0.5])
    target = pd.Series([0.6, 0.4])
    returns = pd.Series([0.0, 0.0])

    result = one_way_turnover(pre, target, returns)

    assert result["traded_notional"] == pytest.approx(0.2)
    assert result["long_trades"] == pytest.approx(0.2)
    assert result["short_trades"] == pytest.approx(0.0)


def test_missing_prices_boundary() -> None:
    """Signal with missing next session → fail closed.

    Oracle: ValueError because 2024-01-03 has no next session in data.
    """
    signals = pd.Series(pd.to_datetime(["2024-01-03"]))
    opens = pd.DataFrame(
        {"open": [100.0, 101.0]},
        index=pd.to_datetime(["2024-01-02", "2024-01-03"]),
    )

    with pytest.raises(ValueError, match="beyond available session data"):
        next_session_open(signals, opens)


def test_integration_end_to_end() -> None:
    """Full pipeline: next-open → drift-adjusted turnover → slippage cost.

    Oracle:
        # 1. Next-open timing
        Signal 2024-01-02 → open 101.0
        Signal 2024-01-03 → open 102.0

        # 2. Realized returns from signal to execution
        Asset A: (101.0 - 100.0) / 100.0 = 0.01
        Asset B: (102.0 - 100.0) / 100.0 = 0.02

        # 3. Drift-adjusted turnover
        pre = [0.5, 0.5]
        drift = [0.5*1.01, 0.5*1.02] = [0.505, 0.51]
        target = [0.6, 0.4]
        trades = [0.095, -0.11]
        long_trades = 0.095 + 0.11 = 0.205
        traded_notional = 0.205 * 1_000_000 = 205_000

        # 4. Slippage at 10 bps
        cost = 10.0 * 0.0001 * 205_000 = 205.0
    """
    # Next-open setup
    signals = pd.Series(pd.to_datetime(["2024-01-02", "2024-01-03"]))
    opens = pd.DataFrame(
        {"open": [100.0, 101.0, 102.0, 103.0]},
        index=pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]),
    )
    exec_opens = next_session_open(signals, opens)  # [101.0, 102.0]

    # Compute realized returns
    pre_prices = pd.Series([100.0, 100.0])
    returns = (exec_opens.values - pre_prices.values) / pre_prices.values  # [0.01, 0.02]

    # Turnover computation
    portfolio_value = 1_000_000
    pre_weights = pd.Series([0.5, 0.5])
    target_weights = pd.Series([0.6, 0.4])
    returns_series = pd.Series(returns)

    turnover = one_way_turnover(pre_weights, target_weights, returns_series)
    traded_notional = turnover["traded_notional"] * portfolio_value  # 0.205 * 1M = 205_000

    # Slippage
    cost = linear_bps_slippage(traded_notional, bps_param=10.0)

    assert cost == pytest.approx(205.0)
