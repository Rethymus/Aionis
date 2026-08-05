"""Hermetic tests for the bps-cost sensitivity sweep (mount② sister script).

The sweep is a thin loop over the already-tested :func:`net_cost_summary`; these
tests cover the sweep-specific logic: bps-grid parsing, break-even interpolation,
and the monotonic-decay / gross-invariance invariants of the loop itself.
Synthetic deterministic fixtures (numpy seed=0). AAA pattern. No network/data.
"""
from __future__ import annotations

import importlib
import math

import numpy as np
import pandas as pd
import pytest

from aionis.eval.net_cost import net_cost_summary

sweep = importlib.import_module("scripts.track_b_net_cost_sweep_run")


@pytest.fixture(autouse=True)
def set_seed() -> None:
    np.random.seed(0)


def _make_panel(n_tickers: int = 20, n_months: int = 24, seed: int = 0) -> pd.DataFrame:
    """Deterministic OOS score panel (mirrors tests/test_net_cost._make_panel)."""
    rng = np.random.default_rng(seed)
    tickers = [f"T{i:03d}" for i in range(n_tickers)]
    months = pd.date_range("2020-01-31", periods=n_months, freq="ME")
    rows = []
    for m in months:
        for t in tickers:
            rows.append({
                "date": m,
                "ticker": t,
                "score": float(rng.standard_normal()),
                "y_fwd_ret": float(rng.standard_normal() * 0.02),
            })
    return pd.DataFrame(rows)


# --- _parse_bps ---


def test_parse_bps_sorts_and_dedups() -> None:
    """parse normalizes order (ascending) and drops duplicates."""
    assert sweep._parse_bps("5,1,2,1,0") == (0.0, 1.0, 2.0, 5.0)


def test_parse_bps_rejects_negative() -> None:
    """Negative bps is an invalid scenario and is rejected."""
    with pytest.raises(ValueError, match="Negative bps rejected"):
        sweep._parse_bps("0,5,-1")


def test_parse_bps_rejects_empty() -> None:
    """An empty grid is rejected (no sweep to run)."""
    with pytest.raises(ValueError, match="Empty bps grid"):
        sweep._parse_bps(",,")


def test_default_grid_is_nonneg_and_includes_zero() -> None:
    """The default grid includes 0 (gross reference) and is ascending non-negative."""
    g = sweep.DEFAULT_BPS_GRID
    assert g[0] == 0.0
    assert g == tuple(sorted(g))
    assert all(b >= 0 for b in g)


# --- _break_even_bps ---


def test_break_even_none_when_net_always_positive() -> None:
    """If net_sharpe stays positive across the whole grid, there is no crossing."""
    rows = [
        {"bps": 0.0, "net_sharpe": 0.5},
        {"bps": 5.0, "net_sharpe": 0.3},
        {"bps": 10.0, "net_sharpe": 0.1},
    ]
    assert sweep._break_even_bps(rows) is None


def test_break_even_interpolates_between_bracketing_pair() -> None:
    """Crossing between bps=5 (net=0.3) and bps=10 (net=-0.2) → root at bps=8."""
    rows = [
        {"bps": 0.0, "net_sharpe": 0.6},
        {"bps": 5.0, "net_sharpe": 0.3},
        {"bps": 10.0, "net_sharpe": -0.2},
    ]
    be = sweep._break_even_bps(rows)
    assert be == pytest.approx(8.0, abs=1e-9)


def test_break_even_zero_when_gross_already_nonpositive() -> None:
    """If net_sharpe <= 0 even at bps=0, the break-even is 0."""
    rows = [{"bps": 0.0, "net_sharpe": -0.1}, {"bps": 5.0, "net_sharpe": -0.4}]
    assert sweep._break_even_bps(rows) == pytest.approx(0.0, abs=1e-9)


# --- sweep-loop invariants on a synthetic panel ---


def test_sweep_gross_invariant_and_net_monotone_decay() -> None:
    """Across the bps grid: gross_sharpe identical (cost affects net only);
    net_sharpe monotonically non-increasing in bps; total_cost_bps scales linearly."""
    # Arrange
    panel = _make_panel(n_tickers=20, n_months=24, seed=11)
    grid = (0.0, 2.0, 5.0, 10.0, 20.0)
    # Act
    ms = {b: net_cost_summary(panel, bps=b, quantile=0.2) for b in grid}
    # Assert — gross is invariant across bps (same underlying scores)
    gross_values = [m.gross_sharpe for m in ms.values()]
    assert all(math.isfinite(g) for g in gross_values), f"non-finite gross: {gross_values}"
    assert max(gross_values) - min(gross_values) < 1e-12, (
        f"gross_sharpe must be identical across bps; got {gross_values}"
    )
    # Assert — net_sharpe non-increasing in bps
    nets = [ms[b].net_sharpe for b in grid]
    for i in range(len(nets) - 1):
        assert nets[i] >= nets[i + 1] - 1e-12, (
            f"net_sharpe not monotone non-increasing at bps {grid[i]}->{grid[i + 1]}: {nets}"
        )
    # Assert — bps=0 ⇒ net == gross
    assert ms[0.0].net_sharpe == pytest.approx(ms[0.0].gross_sharpe, rel=1e-9, abs=1e-12)
    # Assert — linear cost scaling: turnover identical, total_cost_bps ∝ bps
    turnovers = [ms[b].avg_turnover for b in grid]
    assert max(turnovers) - min(turnovers) < 1e-12, (
        f"turnover must be identical across bps (same scores); got {turnovers}"
    )
    assert ms[10.0].total_cost_bps == pytest.approx(2.0 * ms[5.0].total_cost_bps, rel=1e-9)
