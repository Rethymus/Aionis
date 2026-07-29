"""Hermetic tests for :mod:`aionis.eval.event_study`.

All inputs are synthetic (numpy/pandas only); no real cache files are touched.
The drift synthetic places two same-ticker earnings events with different
event-day abnormal returns so CAR has across-event variance; the no-drift
synthetic uses identical price paths so AR == 0 everywhere.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from aionis.eval.event_study import (
    cumulative_abnormal_return,
    events_13d,
    events_earnings,
    events_macro,
)


def _drift_prices_events() -> tuple[pd.DataFrame, pd.DataFrame]:
    """3 tickers (B, C flat at 100; A jumps +3% / +6% on two event days).

    With B, C flat, the cross-section benchmark on a non-event day is 0 and on
    A's event day is bump/3, so AR[A, event_day] = bump * 2/3. Pre- and
    post-event AR is exactly 0, so CAR[offset] = 0 for offset < 0 and CAR[0] is
    the mean event-day AR.
    """
    dates = pd.date_range("2020-01-01", periods=80, freq="D")
    bumps = {15: 0.03, 55: 0.06}
    price_a = np.full(80, 100.0)
    for i in range(1, 80):
        price_a[i] = price_a[i - 1] * (1 + bumps.get(i, 0.0))
    prices = pd.DataFrame({"A": price_a, "B": 100.0, "C": 100.0}, index=dates)
    events = pd.DataFrame(
        {
            "ticker": ["A", "A"],
            "event_date": [dates[15], dates[55]],
            "event_type": ["earnings", "earnings"],
        }
    )
    return prices, events


def test_car_offset0_equals_mean_event_day_ar():
    prices, events = _drift_prices_events()
    summary, per_event = cumulative_abnormal_return(prices, events, k_before=10, k_after=20)

    car0 = summary.loc[summary["offset"] == 0, "car"].iloc[0]
    mean_event_day_ar = per_event.loc[per_event["offset"] == 0, "ar"].mean()

    # CAR[0] equals the mean event-day AR (pre-event AR is exactly 0, so the
    # cumsum from -k_before reduces to AR[0]).
    assert car0 == pytest.approx(mean_event_day_ar, abs=1e-12)
    # analytic value: mean(2/3*0.03, 2/3*0.06) = 0.03
    assert car0 == pytest.approx(0.03, abs=1e-12)


def test_pre_event_car_flat_on_drift_synthetic():
    prices, events = _drift_prices_events()
    summary, _ = cumulative_abnormal_return(prices, events, k_before=10, k_after=20)
    pre = summary[summary["offset"] < 0]
    assert np.allclose(pre["car"].to_numpy(), 0.0, atol=1e-12)


def test_pre_event_car_flat_for_no_drift_synthetic():
    # identical price paths -> cross-section benchmark equals each ticker's
    # return -> AR == 0 everywhere -> CAR is flat (zero) across all offsets.
    dates = pd.date_range("2020-01-01", periods=80, freq="D")
    prices = pd.DataFrame({"A": 100.0, "B": 100.0}, index=dates)
    events = pd.DataFrame(
        {
            "ticker": ["A", "B"],
            "event_date": [dates[20], dates[25]],
            "event_type": ["x", "x"],
        }
    )
    summary, _ = cumulative_abnormal_return(prices, events, k_before=10, k_after=20)
    pre = summary[summary["offset"] < 0]
    assert np.allclose(pre["car"].to_numpy(), 0.0, atol=1e-12)
    # post-event CAR is flat too in a no-drift world
    assert np.allclose(summary["car"].to_numpy(), 0.0, atol=1e-12)


def test_ci_brackets_car():
    prices, events = _drift_prices_events()
    summary, _ = cumulative_abnormal_return(prices, events, k_before=10, k_after=20)
    assert (summary["car"] >= summary["car_ci_lo"] - 1e-12).all()
    assert (summary["car"] <= summary["car_ci_hi"] + 1e-12).all()
    # event-day CI has nonzero width (two events with different AR)
    row0 = summary[summary["offset"] == 0].iloc[0]
    assert row0["car_ci_hi"] > row0["car_ci_lo"]


def test_n_events_counts_right():
    prices, events = _drift_prices_events()
    summary, _ = cumulative_abnormal_return(prices, events, k_before=10, k_after=20)
    # one event_type, two events, full window of 31 offsets
    assert (summary["n_events"] == 2).all()
    assert summary["offset"].min() == -10
    assert summary["offset"].max() == 20
    assert len(summary) == 31


def test_n_events_multi_type():
    prices, events = _drift_prices_events()
    extra = pd.DataFrame(
        {
            "ticker": ["B"],
            "event_date": [prices.index[30]],
            "event_type": ["13D"],
        }
    )
    events2 = pd.concat([events, extra], ignore_index=True)
    summary, _ = cumulative_abnormal_return(prices, events2, k_before=10, k_after=20)
    by_type = summary.groupby("event_type")["n_events"].first()
    assert by_type["earnings"] == 2
    assert by_type["13D"] == 1


def test_event_id_is_row_index_in_events():
    prices, events = _drift_prices_events()
    events = events.rename(index={0: 7, 1: 42})  # non-default index
    _, per_event = cumulative_abnormal_return(prices, events, k_before=10, k_after=20)
    assert set(per_event["event_id"]) == {7, 42}


def test_events_13d_helper(tmp_path):
    df = pd.DataFrame(
        {
            "ticker": ["AAPL", "MSFT"],
            "cik": [1, 2],
            "filing_date": pd.to_datetime(["2021-01-15", "2021-03-20"]),
            "accession": ["a", "b"],
            "form": ["SC 13D", "SC 13D/A"],
        }
    )
    path = tmp_path / "phase_d_13d_events.parquet"
    df.to_parquet(path)

    out = events_13d(path)
    assert list(out.columns) == ["ticker", "event_date", "event_type"]
    assert (out["event_type"] == "13D").all()
    assert list(out["ticker"]) == ["AAPL", "MSFT"]
    assert out["event_date"].iloc[0] == pd.Timestamp("2021-01-15")
    assert out["event_date"].iloc[1] == pd.Timestamp("2021-03-20")


def test_events_earnings_helper(tmp_path):
    df = pd.DataFrame(
        {
            "ticker": ["A", "A", "A", "B", "B"],
            "filed": ["2010-03-10", "2010-03-10", "2010-06-07", "2011-01-01", "2011-01-01"],
            "form": ["10-K", "10-K", "10-Q", "8-K", "10-Q"],
            "metric": ["rev", "eps", "rev", "rev", "rev"],  # duplicate (ticker,filed) rows
        }
    )
    path = tmp_path / "phase_b_fundamentals.parquet"
    df.to_parquet(path)

    out = events_earnings(path)
    assert list(out.columns) == ["ticker", "event_date", "event_type"]
    assert (out["event_type"] == "earnings").all()
    # 8-K filtered out; (A,2010-03-10) deduped; -> 3 distinct earnings events
    assert len(out) == 3
    pairs = set(
        zip(out["ticker"], out["event_date"].dt.strftime("%Y-%m-%d"), strict=True)
    )
    assert pairs == {("A", "2010-03-10"), ("A", "2010-06-07"), ("B", "2011-01-01")}


def test_events_macro_helper_cpi(tmp_path):
    data = {
        "observations": [
            {
                "realtime_start": "2023-02-10",
                "realtime_end": "9999-12-31",
                "date": "2023-01-01",
                "value": "X",
            },
            {
                "realtime_start": "2023-02-14",
                "realtime_end": "2023-03-10",
                "date": "2023-01-01",
                "value": "Xrev",
            },
            {
                "realtime_start": "2023-03-12",
                "realtime_end": "9999-12-31",
                "date": "2023-02-01",
                "value": "Y",
            },
        ]
    }
    (tmp_path / "alfred_CPIAUCSL.json").write_text(json.dumps(data))

    out = events_macro(tmp_path, "CPIAUCSL")
    assert list(out.columns) == ["ticker", "event_date", "event_type"]
    assert (out["event_type"] == "CPI").all()
    assert out["ticker"].isna().all()  # broadcast
    # first print per ref month; the 2023-02-14 revision is excluded
    dates = set(out["event_date"].dt.strftime("%Y-%m-%d"))
    assert dates == {"2023-02-10", "2023-03-12"}
    assert len(out) == 2


def test_events_macro_helper_nfp(tmp_path):
    data = {
        "observations": [
            {
                "realtime_start": "2023-02-10",
                "realtime_end": "9999-12-31",
                "date": "2023-01-01",
                "value": "1",
            },
        ]
    }
    (tmp_path / "alfred_PAYEMS.json").write_text(json.dumps(data))

    out = events_macro(tmp_path, "PAYEMS")
    assert (out["event_type"] == "NFP").all()
    assert out["ticker"].isna().all()
    assert len(out) == 1
