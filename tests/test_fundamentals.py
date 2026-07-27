"""Fundamentals PIT invariants — hermetic (no network).

The whole integrity of the Entity/State layer rests on the join using FILING
date (when a value became knowable), not period-end ``end``. These tests pin
that with synthetic facts so a regression to an ``end``-based join is caught
without touching EDGAR.
"""
from __future__ import annotations

import pandas as pd

from aionis.ingest.fundamentals import METRIC_TAGS, _extract, pit_align


def test_pit_join_uses_filed_not_end() -> None:
    # FY2020 10-K filed 2021-02-01. At 2021-01-15 (before filing) the value is
    # NOT yet knowable -> NaN. An `end`-based join would wrongly show 120.0.
    long = pd.DataFrame([
        {"ticker": "X", "metric": "assets", "end": "2019-12-31", "filed": "2020-02-01",
         "form": "10-K", "fy": 2019, "fp": "FY", "value": 100.0, "unit": "USD"},
        {"ticker": "X", "metric": "assets", "end": "2020-12-31", "filed": "2021-02-01",
         "form": "10-K", "fy": 2020, "fp": "FY", "value": 120.0, "unit": "USD"},
    ])
    dates = pd.DatetimeIndex(["2020-06-01", "2021-01-15", "2021-03-01"]).normalize()
    s = pit_align(long, dates, ["X"], ["assets"])["assets"]["X"]
    assert s.loc["2020-06-01"] == 100.0          # FY2019 filed 2020-02-01 -> knowable
    # The FY2020 value (120) is NOT yet filed on 2021-01-15, so the latest knowable
    # value is still FY2019's 100 — NOT 120, NOT NaN (a prior filing exists).
    assert s.loc["2021-01-15"] == 100.0
    assert s.loc["2021-03-01"] == 120.0           # FY2020 filed 2021-02-01 -> now knowable


def test_pit_revision_uses_latest_filed() -> None:
    # A restated value filed later supersedes the original FROM its filing date
    # (you used what was knowable at the time, then the revision).
    long = pd.DataFrame([
        {"ticker": "X", "metric": "assets", "end": "2020-12-31", "filed": "2021-02-01",
         "form": "10-K", "fy": 2020, "fp": "FY", "value": 120.0, "unit": "USD"},
        {"ticker": "X", "metric": "assets", "end": "2020-12-31", "filed": "2022-03-01",
         "form": "10-K", "fy": 2021, "fp": "FY", "value": 125.0, "unit": "USD"},
    ])
    dates = pd.DatetimeIndex(["2021-06-01", "2022-06-01"]).normalize()
    s = pit_align(long, dates, ["X"], ["assets"])["assets"]["X"]
    assert s.loc["2021-06-01"] == 120.0           # before the restatement was filed
    assert s.loc["2022-06-01"] == 125.0           # after the restatement was filed


def test_pit_nan_before_first_filing() -> None:
    # Before any filing, the metric is unknowable -> NaN (no forward-fill from
    # period-end, no leak of future filings).
    long = pd.DataFrame([
        {"ticker": "X", "metric": "equity", "end": "2020-12-31", "filed": "2021-03-01",
         "form": "10-K", "fy": 2020, "fp": "FY", "value": 5.0, "unit": "USD"},
    ])
    dates = pd.DatetimeIndex(["2020-12-31", "2021-02-28", "2021-04-01"]).normalize()
    s = pit_align(long, dates, ["X"], ["equity"])["equity"]["X"]
    assert pd.isna(s.loc["2020-12-31"]) and pd.isna(s.loc["2021-02-28"])
    assert s.loc["2021-04-01"] == 5.0


def test_extract_multi_tag_fallback() -> None:
    fact10k = {"form": "10-K", "fp": "FY", "fy": 2020,
               "end": "2020-12-31", "filed": "2021-02-01"}
    facts = {"facts": {"us-gaap": {
        "Assets": {"units": {"USD": [{**fact10k, "val": 9.0}]}},
        "StockholdersEquity": {"units": {"USD": [{**fact10k, "val": 5.0}]}},
    }}}
    assert len(_extract(facts, METRIC_TAGS["assets"])) == 1
    eq = _extract(facts, METRIC_TAGS["equity"])  # first tag StockholdersEquity hit
    assert eq and eq[0]["value"] == 5.0
    assert _extract(facts, ("NonexistentTag", "AlsoMissing")) == []


def test_period_end_lag_arm_aligns_on_end_plus_form_dependent_lag() -> None:
    """Phase B ``arm_base``: a fact is knowable at ``end + lag`` (10-K +6mo,
    10-Q +4mo) — NOT at ``filed`` and NOT before ``end + lag``. This is the
    standard-practice baseline the filed-date arm is measured against; it must
    NOT use the filing date (that is the treatment arm's job)."""
    long = pd.DataFrame([
        # 10-K: end 2023-12-31, filed 2024-02-28 -> period-end arm avail 2024-06-30
        {"ticker": "X", "metric": "assets", "end": "2023-12-31", "filed": "2024-02-28",
         "form": "10-K", "fy": 2023, "fp": "FY", "value": 100.0, "unit": "USD"},
        # 10-Q: end 2024-03-31, filed 2024-04-30 -> period-end arm avail 2024-07-31
        {"ticker": "X", "metric": "revenue", "end": "2024-03-31", "filed": "2024-04-30",
         "form": "10-Q", "fy": 2024, "fp": "Q1", "value": 200.0, "unit": "USD"},
    ])
    dates = pd.DatetimeIndex(
        ["2024-02-28", "2024-06-29", "2024-06-30", "2024-07-01",
         "2024-07-30", "2024-07-31"]).normalize()
    assets = pit_align(long, dates, ["X"], ["assets"], align_on="end_lag")["assets"]["X"]
    rev = pit_align(long, dates, ["X"], ["revenue"], align_on="end_lag")["revenue"]["X"]
    # 10-K: filed 2024-02-28 but period-end+6mo = 2024-06-30
    assert pd.isna(assets.loc["2024-02-28"]), "period-end arm must ignore filed date"
    assert pd.isna(assets.loc["2024-06-29"])
    assert assets.loc["2024-06-30"] == 100.0
    assert assets.loc["2024-07-01"] == 100.0
    # 10-Q: period-end+4mo = 2024-07-31
    assert pd.isna(rev.loc["2024-07-30"])
    assert rev.loc["2024-07-31"] == 200.0
