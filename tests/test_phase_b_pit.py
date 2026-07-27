"""Phase B C5 — joined-panel PIT hermetic test (freeze-checklist #1).

The highest-risk surface in Phase B is the **joined** ticker panel: EDGAR as-filed
fundamentals (filed-date PIT) merged onto the price cross-section, then fed into
derived ratios (mktcap / P_B / ROA). These pin the invariant the filed-date arm
MUST satisfy (and that the future period-end control arm is measured against):

  For every panel row at date *t*, every feature column — raw ``fund_*`` AND derived
  ``mktcap``/``pb_ratio``/``roa`` — is a function ONLY of facts with ``filed <= t``
  and of ``close[t]``. A fact filed after *t* (incl. one filed inside an earlier
  row's forward-return window) must NOT appear in that row's features, raw/derived.

Hermetic: synthetic prices + synthetic facts, no network, no EDGAR. A regression to
an ``end``-based join, a forward-fill, or a cross-ticker merge bleed fails one of
these. (The raw-``fund_*``-at-filing-boundary case already lives in
``test_selection_panel.py``; these cover the derived + supersession + cross-ticker
gaps that the critic's C5 flagged as uncovered on the joined panel.)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from aionis.features.selection_panel import build_selection_panel


def _prices() -> pd.DataFrame:
    """5 NYSE sessions x 2 tickers; A rises 100..104, B rises 50..54."""
    idx = pd.DatetimeIndex(pd.to_datetime(
        ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08"]))
    return pd.DataFrame({"A": [100.0, 101.0, 102.0, 103.0, 104.0],
                         "B": [50.0, 51.0, 52.0, 53.0, 54.0]}, index=idx)


def _fact(ticker: str, metric: str, end: str, filed: str, value: float) -> dict:
    return {"ticker": ticker, "metric": metric, "end": end, "filed": filed,
            "form": "10-K", "fy": 2023, "fp": "FY", "value": value, "unit": "USD"}


def test_late_filed_facts_do_not_leak_into_raw_or_derived_features() -> None:
    """Facts FILED on 2024-01-05 are NaN in fund_* AND derived mktcap/pb at
    2024-01-02..01-04 (before filing), present from 2024-01-05.

    2024-01-05 falls INSIDE the h=1 forward-return window of the 2024-01-04 row
    (label = close[2024-01-05]/close[2024-01-04] - 1) — the exact "filed after
    label_start" leak the control gates must reject. An ``end``-based join or any
    forward-fill would surface the value early and fail this.
    """
    fund = pd.DataFrame([
        _fact("A", "shares_out", "2023-12-31", "2024-01-05", 1_000_000.0),
        _fact("A", "equity", "2023-12-31", "2024-01-05", 50_000_000.0),
    ])
    a = build_selection_panel(_prices(), fund, horizon=1)
    a = a[a.ticker == "A"].sort_values("date").set_index("date")

    for d in ["2024-01-02", "2024-01-03", "2024-01-04"]:  # before filing -> unknowable
        assert pd.isna(a.loc[d, "fund_shares_out"]), f"shares leaked at {d}"
        assert pd.isna(a.loc[d, "fund_equity"]), f"equity leaked at {d}"
        assert pd.isna(a.loc[d, "mktcap"]), f"mktcap leaked at {d}"
        assert pd.isna(a.loc[d, "pb_ratio"]), f"pb_ratio leaked at {d}"

    for d in ["2024-01-05", "2024-01-08"]:  # filed on/after 01-05 -> visible
        assert a.loc[d, "fund_shares_out"] == 1_000_000.0
        assert a.loc[d, "fund_equity"] == 50_000_000.0
        np.testing.assert_allclose(a.loc[d, "mktcap"], a.loc[d, "close"] * 1e6, rtol=1e-9)
        np.testing.assert_allclose(
            a.loc[d, "pb_ratio"], a.loc[d, "close"] * 1e6 / 50e6, rtol=1e-9)


def test_filed_supersession_holds_through_panel_and_derived() -> None:
    """A revised filing (filed 2024-01-05) supersedes the original (filed
    2024-01-02) ONLY from its filing date — not retroactively, not early. Tested
    through the full panel build incl. derived mktcap, not just ``pit_align``.
    """
    fund = pd.DataFrame([
        _fact("A", "shares_out", "2023-12-31", "2024-01-02", 1_000_000.0),
        _fact("A", "shares_out", "2023-12-31", "2024-01-05", 2_000_000.0),
    ])
    a = build_selection_panel(_prices(), fund, horizon=1)
    a = a[a.ticker == "A"].sort_values("date").set_index("date")

    for d in ["2024-01-02", "2024-01-03", "2024-01-04"]:  # original holds until revision
        assert a.loc[d, "fund_shares_out"] == 1_000_000.0
        np.testing.assert_allclose(a.loc[d, "mktcap"], a.loc[d, "close"] * 1e6, rtol=1e-9)
    for d in ["2024-01-05", "2024-01-08"]:  # revised value from its filing date
        assert a.loc[d, "fund_shares_out"] == 2_000_000.0
        np.testing.assert_allclose(a.loc[d, "mktcap"], a.loc[d, "close"] * 2e6, rtol=1e-9)


def test_no_cross_ticker_fundamental_bleed() -> None:
    """A fact filed for ticker A never appears under ticker B. Guards the
    per-ticker ``pit_align`` loop and the (date, ticker) merge."""
    fund = pd.DataFrame([
        _fact("A", "shares_out", "2023-12-31", "2024-01-02", 1_000_000.0),
    ])
    tidy = build_selection_panel(_prices(), fund, horizon=1)
    b = tidy[tidy.ticker == "B"].sort_values("date").set_index("date")
    a = tidy[tidy.ticker == "A"].sort_values("date").set_index("date")

    assert b["fund_shares_out"].isna().all(), "B inherited A's fundamental"
    assert b["mktcap"].isna().all(), "B inherited A's mktcap"
    assert (a["fund_shares_out"] == 1_000_000.0).all(), "A lost its own fundamental"
