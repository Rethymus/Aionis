"""Price-panel anomaly audit (market-driver framework reliability mechanism ⑥) — hermetic.

Pins the contract of :mod:`aionis.features.anomaly_audit`: it flags the four
reliability defects a price panel can carry without raising — nonpositive
prints, interior gaps (a hole inside the traded span), discontinuities
(split-unadjusted / erroneous jumps), and stale runs (halted / delisted feeding
a flat line). All detection is on the wide ``date x ticker`` adjusted-close
frame the selection pipeline already builds; no network, deterministic.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from aionis.features.anomaly_audit import anomaly_summary, price_anomalies


def _wide(cols: dict[str, list[float]]) -> pd.DataFrame:
    """Build a wide date x ticker frame from equal-length lists."""
    idx = pd.date_range("2024-01-02", periods=len(next(iter(cols.values()))), freq="B")
    return pd.DataFrame(cols, index=idx)


# --- nonpositive ------------------------------------------------------------


def test_flags_nonpositive_close() -> None:
    px = _wide({"BAD": [1.0, 0.0, 2.0, -1.0, 3.0], "GOOD": [1.0, 1.1, 1.2, 1.3, 1.4]})

    a = price_anomalies(px)

    bad = a[a["ticker"] == "BAD"]
    assert (bad["anomaly"] == "nonpositive").any()
    row = bad[bad["anomaly"] == "nonpositive"].iloc[0]
    assert row["count"] == 2  # 0.0 and -1.0
    assert "GOOD" not in set(a[a["anomaly"] == "nonpositive"]["ticker"])


# --- interior gap -----------------------------------------------------------


def test_flags_interior_gap_not_leading_trailing_nan() -> None:
    # NaN at the START and END are membership/coverage, NOT interior gaps; only a
    # hole between two valid prints is a reliability defect.
    px = _wide({"HOLE": [np.nan, 2.0, np.nan, 4.0, np.nan]})

    a = price_anomalies(px)

    row = a[(a["ticker"] == "HOLE") & (a["anomaly"] == "interior_gap")]
    assert len(row) == 1
    assert row.iloc[0]["count"] == 1  # only the middle NaN is interior


def test_all_nan_series_not_interior_gap() -> None:
    px = _wide({"BLANK": [np.nan, np.nan, np.nan, np.nan, np.nan]})

    a = price_anomalies(px)

    assert not ((a["ticker"] == "BLANK") & (a["anomaly"] == "interior_gap")).any()


# --- jump -------------------------------------------------------------------


def test_flags_large_jump_above_threshold() -> None:
    # 1.0 -> 2.0 is a +100% session (|ret|=1.0 > default 0.50 threshold).
    px = _wide({"JMP": [1.0, 2.0, 2.1, 2.2, 2.3], "OK": [1.0, 1.01, 1.02, 1.03, 1.04]})

    a = price_anomalies(px)

    row = a[(a["ticker"] == "JMP") & (a["anomaly"] == "jump")]
    assert len(row) == 1
    assert row.iloc[0]["count"] == 1
    assert row.iloc[0]["detail"].startswith("max_abs_ret=")
    assert not ((a["ticker"] == "OK") & (a["anomaly"] == "jump")).any()


def test_jump_threshold_respected() -> None:
    px = _wide({"MILD": [1.0, 1.4, 1.4, 1.4, 1.4]})  # +40%, under default 0.50

    a = price_anomalies(px, jump_threshold=0.50)

    assert not ((a["ticker"] == "MILD") & (a["anomaly"] == "jump")).any()

    a2 = price_anomalies(px, jump_threshold=0.30)  # now +40% exceeds
    assert ((a2["ticker"] == "MILD") & (a2["anomaly"] == "jump")).any()


# --- stale ------------------------------------------------------------------


def test_flags_stale_run_at_or_above_threshold() -> None:
    # 12 identical in a row (default stale_run=10) -> stale; the first session
    # establishes the level so 11 of the 12 are "unchanged" sessions.
    px = _wide({"FLAT": [5.0] * 12, "LIVE": np.linspace(5.0, 5.5, 12).tolist()})

    a = price_anomalies(px)

    row = a[(a["ticker"] == "FLAT") & (a["anomaly"] == "stale")]
    assert len(row) == 1
    assert row.iloc[0]["detail"].startswith("max_run=")
    assert int(row.iloc[0]["detail"].split("=")[1]) >= 10
    assert not ((a["ticker"] == "LIVE") & (a["anomaly"] == "stale")).any()


def test_stale_run_below_threshold_not_flagged() -> None:
    px = _wide({"SHORT": [5.0] * 5})  # 4 unchanged, under default 10

    a = price_anomalies(px, stale_run=10)

    assert not ((a["ticker"] == "SHORT") & (a["anomaly"] == "stale")).any()


# --- clean + summary --------------------------------------------------------


def test_clean_panel_yields_no_anomalies() -> None:
    px = _wide({"GOOD": [1.0, 1.01, 1.02, 1.03, 1.04, 1.05, 1.06, 1.07, 1.08, 1.09]})

    a = price_anomalies(px)

    assert a.empty


def test_summary_counts_by_anomaly_and_ticker() -> None:
    px = _wide({
        "BAD": [1.0, 0.0, 2.0, 4.0, 8.0],     # nonpositive(1) + jump(2: 0->2, 2->4)
        "FLAT": [3.0] * 5,                     # stale(>=10? no, only 4 unchanged -> not flagged)
        "GOOD": [1.0, 1.01, 1.02, 1.03, 1.04],
    })

    a = price_anomalies(px, stale_run=3)
    s = anomaly_summary(a, n_tickers=3)

    assert s["n_tickers"] == 3
    assert s["n_flagged"] == 2  # BAD + FLAT
    assert "nonpositive" in s["by_anomaly"]
    assert s["by_anomaly"]["nonpositive"] == 1
    assert s["by_anomaly"]["stale"] == 1  # FLAT now flagged at stale_run=3


def test_empty_panel_is_safe() -> None:
    a = price_anomalies(pd.DataFrame())
    assert a.empty
    assert anomaly_summary(a)["n_tickers"] == 0
    assert anomaly_summary(a)["n_flagged"] == 0
