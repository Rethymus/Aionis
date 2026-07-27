"""Phase B control gates — hermetic (synthetic fundamentals)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from aionis.eval.phase_b_controls import lag_shift_filed, within_month_placebo


def _fund() -> pd.DataFrame:
    rows = []
    for t, base in [("A", 100.0), ("B", 200.0), ("C", 300.0)]:
        for metric in ("assets", "revenue"):
            for end, filed in (("2023-12-31", "2024-03-01"), ("2024-12-31", "2025-03-01")):
                rows.append({
                    "ticker": t, "metric": metric, "end": end, "filed": filed,
                    "form": "10-K", "fy": 2023 if end.startswith("2023") else 2024,
                    "fp": "FY",
                    "value": base + (10 if metric == "revenue" else 0)
                    + (1 if end.startswith("2024") else 0), "unit": "USD",
                })
    return pd.DataFrame(rows)


def test_lag_shift_is_per_ticker_constant() -> None:
    fund = _fund()
    shifted = lag_shift_filed(fund, seed=0)
    for t in fund["ticker"].unique():
        orig = pd.to_datetime(fund[fund.ticker == t]["filed"]).sort_values().to_numpy()
        new = pd.to_datetime(shifted[shifted.ticker == t]["filed"]).sort_values().to_numpy()
        delta = (new - orig).astype("timedelta64[D]").astype(int)
        assert np.all(delta == delta[0]), f"ticker {t} lag not constant"


def test_lag_shift_is_deterministic() -> None:
    a = lag_shift_filed(_fund(), seed=0)
    b = lag_shift_filed(_fund(), seed=0)
    pd.testing.assert_series_equal(a["filed"], b["filed"])


def test_within_month_placebo_keeps_timing_preserves_multiset() -> None:
    fund = _fund()
    pl = within_month_placebo(fund, seed=1)
    assert set(pl["filed"]) == set(fund["filed"])  # timing preserved
    # placebo permutes WITHIN (metric, month) -> each metric's global multiset preserved
    for metric in fund["metric"].unique():
        fv = sorted(fund.loc[fund.metric == metric, "value"])
        pv = sorted(pl.loc[pl.metric == metric, "value"])
        assert fv == pv
    # non-trivial: at least one seed across 0..9 breaks within-group alignment
    mask = (fund.metric == "assets") & (fund.filed == "2024-03-01")
    g_orig = fund.loc[mask].sort_values("ticker")["value"].to_numpy()
    broke = False
    for s in range(10):
        p = within_month_placebo(fund, seed=s)
        gpl = p.loc[mask].sort_values("ticker")["value"].to_numpy()
        if not (g_orig == gpl).all():
            broke = True
            break
    assert broke, "placebo never broke alignment across 10 seeds"
