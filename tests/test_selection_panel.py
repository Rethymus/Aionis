"""Selection-panel PIT invariants — hermetic (no network).

Pins the S0/S1 feature table: the label y_fwd_ret is the strictly-future h-ahead
return; PIT fundamentals use the value FILED <= t (so a value filed after t does
not appear at t); FF/macro broadcast identically across tickers at a date.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from aionis.features.selection_panel import build_selection_panel, forward_returns


def _prices() -> pd.DataFrame:
    # 5 sessions, 2 tickers. close rises 100..104 for A, 50..54 for B.
    idx = pd.DatetimeIndex(pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04",
                                           "2024-01-05", "2024-01-08"]))
    return pd.DataFrame({"A": [100.0, 101.0, 102.0, 103.0, 104.0],
                         "B": [50.0, 51.0, 52.0, 53.0, 54.0]}, index=idx)


def test_forward_return_label_is_strictly_future() -> None:
    """y_fwd_ret at (t, ticker) == close[t+h]/close[t] - 1; the last h rows are NaN."""
    P = _prices()
    tidy = build_selection_panel(P, pd.DataFrame(), horizon=1)
    a = tidy[tidy.ticker == "A"].sort_values("date")
    # t=0: 101/100-1 = 0.01 ; t=3 (last with a 1-ahead): 104/103-1
    np.testing.assert_allclose(a["y_fwd_ret"].iloc[0], 0.01, atol=1e-12)
    assert np.isnan(a["y_fwd_ret"].iloc[-1])     # no 1-ahead at the final date


def test_pit_fundamental_not_visible_before_filing() -> None:
    """A fact FILED on 2024-01-04 is NOT in the panel at 2024-01-03 (PIT)."""
    fund = pd.DataFrame([{
        "ticker": "A", "metric": "assets", "end": "2023-12-31",
        "filed": "2024-01-04", "form": "10-K", "fy": 2023, "fp": "FY",
        "value": 999.0, "unit": "USD",
    }])
    tidy = build_selection_panel(_prices(), fund, horizon=1)
    a = tidy[tidy.ticker == "A"].sort_values("date").set_index("date")
    assert np.isnan(a.loc["2024-01-02", "fund_assets"])   # before filing
    assert np.isnan(a.loc["2024-01-03", "fund_assets"])   # before filing
    assert a.loc["2024-01-04", "fund_assets"] == 999.0    # filed on this date
    assert a.loc["2024-01-08", "fund_assets"] == 999.0    # held after filing


def test_derived_mktcap_uses_pit_shares_and_current_close() -> None:
    """mktcap = close[t] * shares (filed<=t); uses the close AT t, not future."""
    fund = pd.DataFrame([
        {"ticker": "A", "metric": "shares_out", "end": "2023-12-31",
         "filed": "2024-01-02", "form": "10-K", "fy": 2023, "fp": "FY",
         "value": 1_000_000.0, "unit": "shares"},
    ])
    tidy = build_selection_panel(_prices(), fund, horizon=1)
    a = tidy[tidy.ticker == "A"].sort_values("date").set_index("date")
    # close[2024-01-02]=100, shares=1e6 -> mktcap=1e8
    np.testing.assert_allclose(a.loc["2024-01-02", "mktcap"], 1e8, rtol=1e-9)
    # close[2024-01-03]=101 -> mktcap=1.01e8 (shares held; close updates)
    np.testing.assert_allclose(a.loc["2024-01-03", "mktcap"], 1.01e8, rtol=1e-9)


def test_factors_broadcast_identically_across_tickers() -> None:
    """FF/macro are date-indexed; at each date they're the same for every ticker."""
    ff = pd.DataFrame({"ff_mkt_rf": [0.1, 0.2, 0.3, 0.4, 0.5]},
                      index=pd.DatetimeIndex(pd.to_datetime(
                          ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08"])))
    tidy = build_selection_panel(_prices(), pd.DataFrame(), horizon=1, ff=ff)
    by_date = tidy.groupby("date")["ff_mkt_rf"].nunique()
    assert (by_date == 1).all()                      # one value per date across tickers
    assert tidy[tidy.date == "2024-01-03"]["ff_mkt_rf"].iloc[0] == 0.2


def test_forward_returns_helper_shape() -> None:
    fr = forward_returns(_prices(), h=2)
    assert fr.shape == (5, 2)
    # at t=0, 2-ahead = close[2]/close[0]-1 = 102/100-1 for A
    np.testing.assert_allclose(fr["A"].iloc[0], 0.02, atol=1e-12)
    assert np.isnan(fr["A"].iloc[-1]) and np.isnan(fr["A"].iloc[-2])


def test_align_on_arm_makes_fundamental_visible_at_different_time() -> None:
    """Phase B two-arm timing via ``build_selection_panel(align_on=...)``.

    One 10-K fact: end 2023-07-03, filed 2024-01-04, +6mo(end) = 2024-01-03.
      * ``align_on='filed'`` (arm_state): knowable at 2024-01-04 (NOT 01-03).
      * ``align_on='end_lag'`` (arm_base): knowable at 2024-01-03 (end+6mo; the
        2024-01-04 filing date is irrelevant to this arm).
    Same fact, same prices, same panel — ONLY the knowability time differs.
    """
    fund = pd.DataFrame([{
        "ticker": "A", "metric": "assets", "end": "2023-07-03", "filed": "2024-01-04",
        "form": "10-K", "fy": 2023, "fp": "FY", "value": 999.0, "unit": "USD",
    }])
    P = _prices()
    filed = build_selection_panel(P, fund, horizon=1, align_on="filed")
    lag = build_selection_panel(P, fund, horizon=1, align_on="end_lag")
    fa = filed[filed.ticker == "A"].set_index("date")["fund_assets"]
    la = lag[lag.ticker == "A"].set_index("date")["fund_assets"]
    # arm_state (filed): NaN through 01-03, value from the 01-04 filing
    assert np.isnan(fa.loc["2024-01-03"]) and fa.loc["2024-01-04"] == 999.0
    # arm_base (end+6mo): value from 01-03 (end+lag); filing date 01-04 is ignored
    assert fa.loc["2024-01-03"] != la.loc["2024-01-03"]   # the two arms DIFFER here
    assert la.loc["2024-01-03"] == 999.0 and np.isnan(la.loc["2024-01-02"])
