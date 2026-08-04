"""Hermetic tests for the net-cost layer (mount②).

Synthetic deterministic fixtures (numpy seed=0). AAA pattern (Arrange/Act/Assert),
descriptive names. No network, no real data, no mutation.

Fixtures use >=20 tickers so long_short_returns (min_per_leg=3) produces real monthly
returns — the prior 3-ticker fixture silently produced NaN and made every assertion vacuous.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aionis.eval.execution_costs import linear_bps_slippage, one_way_turnover
from aionis.eval.net_cost import NetCostMetrics, net_cost_summary


@pytest.fixture(autouse=True)
def set_seed() -> None:
    """Pin numpy legacy seed for H6 determinism (fixtures use default_rng(seed) too)."""
    np.random.seed(0)


def _make_panel(
    n_tickers: int = 20,
    n_months: int = 24,
    seed: int = 0,
    stable: bool = False,
) -> pd.DataFrame:
    """Build a deterministic OOS score panel.

    stable=True → each ticker's score is constant across months (identical ranking every
    month) → low turnover after the first rebalance. stable=False → independent random
    scores each month → membership churns → high turnover.
    """
    rng = np.random.default_rng(seed)
    tickers = [f"T{i:03d}" for i in range(n_tickers)]
    months = pd.date_range("2020-01-31", periods=n_months, freq="ME")
    rows = []
    for m in months:
        for t in tickers:
            score = float(tickers.index(t)) if stable else float(rng.standard_normal())
            rows.append(
                {
                    "date": m,
                    "ticker": t,
                    "score": score,
                    "y_fwd_ret": float(rng.standard_normal() * 0.02),
                }
            )
    return pd.DataFrame(rows)


def test_net_sharpe_less_than_gross_when_bps_positive() -> None:
    """When bps > 0, net Sharpe is strictly below gross Sharpe (slippage drags returns)."""
    # Arrange
    panel = _make_panel(n_tickers=20, n_months=24, seed=0, stable=False)
    # Act
    m = net_cost_summary(panel, bps=5.0, quantile=0.2)
    # Assert — HARD (no isfinite skip): a NaN here means the fixture is too small.
    assert np.isfinite(m.gross_sharpe), f"gross_sharpe not finite; fixture/regression: {m}"
    assert np.isfinite(m.net_sharpe), f"net_sharpe not finite; fixture/regression: {m}"
    assert m.net_sharpe < m.gross_sharpe, (
        f"net ({m.net_sharpe}) must be < gross ({m.gross_sharpe}) when bps > 0"
    )
    assert m.total_cost_bps > 0.0
    assert m.n_rebalance >= 2


def test_bps_zero_implies_net_equals_gross() -> None:
    """When bps = 0, no slippage → net Sharpe equals gross Sharpe."""
    # Arrange
    panel = _make_panel(n_tickers=20, n_months=24, seed=1, stable=False)
    # Act
    m = net_cost_summary(panel, bps=0.0, quantile=0.2)
    # Assert
    assert np.isfinite(m.gross_sharpe), f"gross_sharpe not finite: {m}"
    assert m.net_sharpe == pytest.approx(m.gross_sharpe, rel=1e-9, abs=1e-12)


def test_negative_bps_raises_value_error() -> None:
    """Negative bps is an invalid scenario assumption and is rejected."""
    panel = _make_panel(n_tickers=20, n_months=24, seed=2)
    with pytest.raises(ValueError, match="Negative bps rejected"):
        net_cost_summary(panel, bps=-1.0, quantile=0.2)


def test_turnover_low_when_scores_stable_across_months() -> None:
    """Anti-degeneracy: identical ranking every month → low turnover (only first rebuild).

    A rebuild-from-cash-every-month bug would give avg_turnover == 2.0. The real model
    rebuilds only on the first rebalance (2.0) then trades nothing (identical targets), so
    avg_turnover ≈ 2.0 / n_rebalance.
    """
    # Arrange — stable scores → identical top/bottom quintile every month
    panel = _make_panel(n_tickers=20, n_months=12, seed=3, stable=True)
    # Act
    m = net_cost_summary(panel, bps=5.0, quantile=0.2)
    # Assert
    assert m.n_rebalance >= 2
    assert m.avg_turnover < 0.5, (
        f"avg_turnover={m.avg_turnover:.4f} is too high for stable rankings — "
        "suggests degenerate rebuild-from-cash every period"
    )
    assert m.avg_turnover > 0.0  # first rebalance still builds from cash


def test_turnover_higher_when_scores_churn() -> None:
    """Random scores each month (membership churn) → higher turnover than stable scores."""
    # Arrange
    stable = _make_panel(n_tickers=20, n_months=12, seed=4, stable=True)
    churned = _make_panel(n_tickers=20, n_months=12, seed=5, stable=False)
    # Act
    m_stable = net_cost_summary(stable, bps=5.0, quantile=0.2)
    m_churned = net_cost_summary(churned, bps=5.0, quantile=0.2)
    # Assert — turnover responds to real position changes
    assert m_churned.avg_turnover > m_stable.avg_turnover, (
        f"churned ({m_churned.avg_turnover:.4f}) should churn more than stable "
        f"({m_stable.avg_turnover:.4f})"
    )


def test_cost_scales_with_bps() -> None:
    """Doubling bps roughly doubles cumulative cost (linear model)."""
    # Arrange
    panel = _make_panel(n_tickers=20, n_months=24, seed=6, stable=False)
    # Act
    m5 = net_cost_summary(panel, bps=5.0, quantile=0.2)
    m10 = net_cost_summary(panel, bps=10.0, quantile=0.2)
    # Assert — turnover is identical (same scores); cost scales linearly with bps
    assert m10.total_cost_bps == pytest.approx(2.0 * m5.total_cost_bps, rel=1e-9)
    assert m5.avg_turnover == pytest.approx(m10.avg_turnover, rel=1e-12)


def test_h6_bit_identical_across_two_calls() -> None:
    """H6 determinism: two calls on identical inputs produce bit-identical metrics."""
    # Arrange
    panel = _make_panel(n_tickers=20, n_months=24, seed=7, stable=False)
    # Act
    m1 = net_cost_summary(panel, bps=5.0, quantile=0.2)
    m2 = net_cost_summary(panel, bps=5.0, quantile=0.2)
    # Assert
    for field in [
        "gross_sharpe",
        "net_sharpe",
        "avg_turnover",
        "total_cost_bps",
        "gross_max_drawdown",
        "gross_annual_volatility",
        "n_rebalance",
    ]:
        v1 = getattr(m1, field)
        v2 = getattr(m2, field)
        assert v1 == pytest.approx(v2, abs=1e-15), f"{field}: {v1} != {v2}"


def test_insufficient_data_returns_nan_metrics() -> None:
    """A single month (<2 rebalances) returns NaN Sharpe with zero cost."""
    # Arrange — 1 month only
    panel = _make_panel(n_tickers=20, n_months=1, seed=8)
    # Act
    m = net_cost_summary(panel, bps=5.0, quantile=0.2)
    # Assert
    assert np.isnan(m.gross_sharpe)
    assert np.isnan(m.net_sharpe)
    assert m.n_rebalance == 0
    assert m.total_cost_bps == 0.0


def test_net_cost_metrics_dataclass_frozen() -> None:
    """NetCostMetrics is a frozen (immutable) dataclass."""
    m = NetCostMetrics(
        gross_sharpe=1.0,
        net_sharpe=0.9,
        avg_turnover=0.4,
        total_cost_bps=50.0,
        n_rebalance=12,
        gross_max_drawdown=-0.15,
        gross_annual_volatility=0.2,
    )
    with pytest.raises((AttributeError, TypeError)):
        m.gross_sharpe = 1.1  # type: ignore[misc]


# --- execution_costs kernel coverage (the cost primitives net_cost composes) ---


def test_one_way_turnover_kernel() -> None:
    """one_way_turnover returns the expected keys and a positive traded notional."""
    pre = pd.Series([0.5, 0.3, 0.2])
    target = pd.Series([0.6, 0.3, 0.1])
    returns = pd.Series([0.0, 0.0, 0.0])
    result = one_way_turnover(pre, target, returns)
    assert {"traded_notional", "long_trades", "short_trades", "drift_adjusted_pre"} <= set(result)
    assert result["traded_notional"] > 0


def test_linear_bps_slippage_kernel() -> None:
    """linear_bps_slippage: 5 bps on $1M = $500."""
    assert linear_bps_slippage(1_000_000.0, 5.0) == pytest.approx(500.0)


def test_linear_bps_slippage_negative_bps_raises() -> None:
    """Negative bps_param is rejected by the kernel."""
    with pytest.raises(ValueError, match="Negative bps_param rejected"):
        linear_bps_slippage(1_000_000.0, -1.0)
