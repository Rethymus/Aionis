"""Anti-degeneracy tests for Track C joint US-CN fold estimator.

Each test targets a concrete failure mode observed this session (region dropped, unified
group, weak chronological assert, date confusion, currency contamination, non-determinism).
Structural tests are hermetic + fast; the end-to-end test uses a synthetic joint panel +
small LightGBM to prove the machinery runs and is H6 bit-identical across reruns.

These tests exercise the WRAPPER (fit_track_c_joint / build_joint_panel), not just reused
kernels — directly countering the "deceptively green" pattern (handoff 2026-08-04).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aionis.eval.track_c_joint import (
    TrackCJointResult,
    _assert_per_region_chronological,
    _month_end_sample,
    build_joint_panel,
    construct_region_month_groups,
    fit_track_c_joint,
)

# ---------------------------------------------------------------------------
# Synthetic fixture builders (hermetic, deterministic)
# ---------------------------------------------------------------------------


def _synthetic_joint_panel(
    n_months: int = 70,
    n_us: int = 25,
    n_cn: int = 25,
    seed: int = 0,
    signal: float = 0.3,
) -> pd.DataFrame:
    """Deterministic synthetic joint panel: 3 features, mild signal in feat_0.

    US uses calendar month-end; CN uses month-end + 1 day (to exercise per-region calendar
    divergence). forward_return_h = signal*feat_0 + noise (same currency within region by
    construction — synthetic, so the currency concern is moot here).
    """
    rng = np.random.default_rng(seed)
    months = pd.date_range("2018-01-31", periods=n_months, freq="ME")
    rows: list[dict] = []
    for region, n_tickers in (("us", n_us), ("cn", n_cn)):
        for t in range(n_tickers):
            for m in months:
                # CN month-end offset +1 trading day to diverge from US (per-region calendar)
                d = m + pd.Timedelta(days=1) if region == "cn" else m
                f0, f1, f2 = rng.normal(), rng.normal(), rng.normal()
                fwd = signal * f0 + rng.normal(scale=0.1)
                rows.append(
                    {
                        "date": d,
                        "ticker": f"{region}_{t:03d}",
                        "region": region,
                        "feat_0": f0,
                        "feat_1": f1,
                        "feat_2": f2,
                        "forward_return_h": fwd,
                    }
                )
    df = pd.DataFrame(rows)
    return df.sort_values(["date", "region", "ticker"]).reset_index(drop=True)


def _synthetic_regime(panel: pd.DataFrame, seed: int = 0) -> pd.Series:
    """Daily regime series covering the panel span (PIT-irrelevant for synthetic tests)."""
    rng = np.random.default_rng(seed)
    start = panel["date"].min() - pd.Timedelta(days=10)
    end = panel["date"].max() + pd.Timedelta(days=10)
    idx = pd.date_range(start, end, freq="B")
    return pd.Series(rng.normal(size=len(idx)), index=idx, name="regime_state")


# ---------------------------------------------------------------------------
# D1: region-month group construction
# ---------------------------------------------------------------------------


def test_construct_region_month_groups_us_cn_differ_and_monotonic() -> None:
    # Arrange: same calendar month, both regions
    dates = pd.DatetimeIndex(["2024-01-31", "2024-01-31", "2024-02-28", "2024-02-28"])
    regions = pd.Series(["us", "cn", "us", "cn"])

    # Act
    groups = construct_region_month_groups(dates, regions)

    # Assert: us/cn same month differ; monotonic in time
    assert groups[0] != groups[1], "us and cn in the same month must get distinct group ids"
    assert groups[1] != groups[2], "cn-month and next us-month must differ"
    assert np.all(np.diff(groups) > 0), "group ids must be strictly increasing in this order"


def test_construct_region_month_groups_rejects_unknown_region() -> None:
    dates = pd.DatetimeIndex(["2024-01-31"])
    regions = pd.Series(["jp"])
    with pytest.raises(ValueError, match="unknown region"):
        construct_region_month_groups(dates, regions)


# ---------------------------------------------------------------------------
# build_joint_panel (D5 shared features, window, both regions)
# ---------------------------------------------------------------------------


def test_build_joint_panel_has_both_regions_window_and_shared_cols(tmp_path) -> None:
    # Arrange: minimal US + CN parquets with the 2 shared features
    shared = ["momentum_21d", "volatility_21d"]
    us = pd.DataFrame(
        {
            "date": pd.to_datetime(["2015-12-31", "2016-01-31", "2016-02-28"]),
            "ticker": ["AAPL", "AAPL", "AAPL"],
            "momentum_21d": [0.1, 0.2, 0.3],
            "volatility_21d": [0.4, 0.5, 0.6],
            "forward_return_h": [0.01, 0.02, 0.03],
            "us_only_col": [1, 2, 3],  # must be dropped (not shared)
        }
    )
    cn = pd.DataFrame(
        {
            "date": pd.to_datetime(["2016-01-31", "2016-02-28"]),
            "ticker": ["sh.600000", "sh.600000"],
            "momentum_21d": [0.7, 0.8],
            "volatility_21d": [0.9, 1.0],
            "forward_return_h": [0.04, 0.05],
            "limit_up_down_distance": [0.0, 0.0],  # must be dropped (not shared)
        }
    )
    usp = tmp_path / "us.parquet"
    cnp = tmp_path / "cn.parquet"
    us.to_parquet(usp)
    cn.to_parquet(cnp)

    # Act
    joint = build_joint_panel(usp, cnp, feature_cols=shared, window_start="2016-01-01")

    # Assert: both regions, pre-2016 dropped, only shared+meta+label cols
    assert set(joint["region"]) == {"us", "cn"}, "both regions must survive concat"
    assert joint["date"].min() >= pd.Timestamp("2016-01-01"), "pre-window rows must be dropped"
    assert "us_only_col" not in joint.columns, "US-only columns must not leak into joint panel"
    assert "limit_up_down_distance" not in joint.columns, "CN-only columns must not leak"
    assert set(shared).issubset(joint.columns), "shared features must be present"
    assert (joint[joint["region"] == "us"].shape[0] > 0) and (
        joint[joint["region"] == "cn"].shape[0] > 0
    ), "neither region may be empty"


# ---------------------------------------------------------------------------
# I1: per-region chronological assertion
# ---------------------------------------------------------------------------


def test_assert_per_region_chronological_raises_on_us_violation() -> None:
    # Arrange: US train date (Mar 31) >= US test date (Mar 15) — a per-region violation.
    panel = pd.DataFrame(
        {
            "date": pd.to_datetime(
                ["2024-01-31", "2024-03-31", "2024-03-15", "2024-01-31"]
            ),
            "region": ["us", "us", "us", "cn"],
        }
    )
    train_idx = np.array([0, 1])  # US Jan + US Mar 31
    test_idx = np.array([2, 3])  # US Mar 15 + CN Jan

    # Act / Assert
    with pytest.raises(AssertionError, match="region='us'"):
        _assert_per_region_chronological(
            panel, train_idx, test_idx, fold=1, date_col="date", region_col="region"
        )


def test_assert_per_region_chronological_passes_valid_split() -> None:
    panel = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-31", "2024-01-31", "2024-03-31", "2024-03-31"]),
            "region": ["us", "cn", "us", "cn"],
        }
    )
    train_idx = np.array([0, 1])
    test_idx = np.array([2, 3])
    # Must not raise
    _assert_per_region_chronological(
        panel, train_idx, test_idx, fold=1, date_col="date", region_col="region"
    )


# ---------------------------------------------------------------------------
# month-end sampling per region
# ---------------------------------------------------------------------------


def test_month_end_sample_is_per_region_and_idempotent_on_monthend() -> None:
    # Arrange: US has 2 intra-month dates for Jan (daily), CN already month-end.
    panel = pd.DataFrame(
        {
            "date": pd.to_datetime(
                ["2024-01-15", "2024-01-31", "2024-01-31", "2024-02-15", "2024-02-28", "2024-02-28"]
            ),
            "ticker": ["us_a", "us_a", "cn_a", "us_a", "us_a", "cn_a"],
            "region": ["us", "us", "cn", "us", "us", "cn"],
        }
    )
    out = _month_end_sample(panel, "date", "ticker", "region")
    # Each (region, ticker, month) keeps exactly 1 row, the max date.
    keys = out.groupby(["region", "ticker", out["date"].dt.to_period("M")]).size()
    assert (keys == 1).all(), "exactly one row per (region,ticker,month) after sampling"
    # US Jan kept 2024-01-31 (max), not 2024-01-15
    us_jan_mask = (
        (out["region"] == "us") & (out["ticker"] == "us_a") & (out["date"] == "2024-01-31")
    )
    assert len(out[us_jan_mask]) == 1


# ---------------------------------------------------------------------------
# input validation
# ---------------------------------------------------------------------------


def test_fit_rejects_single_region_panel() -> None:
    panel = _synthetic_joint_panel()
    panel = panel[panel["region"] == "us"].copy()  # drop CN
    regime = _synthetic_regime(panel)
    with pytest.raises(ValueError, match="BOTH regions"):
        fit_track_c_joint(
            panel, feature_cols=["feat_0", "feat_1", "feat_2"], regime_state=regime,
            min_train_months=24,
        )


# ---------------------------------------------------------------------------
# end-to-end: machinery runs + H6 bit-identical + D2 currency-clean combined IC
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("seed", [0])
def test_fit_track_c_joint_end_to_end_deterministic(seed: int) -> None:
    # Arrange
    panel = _synthetic_joint_panel(n_months=70, n_us=25, n_cn=25, seed=seed)
    regime = _synthetic_regime(panel, seed=seed)
    fast_params = {"n_estimators": 30, "num_leaves": 8}

    # Act
    r1 = fit_track_c_joint(
        panel,
        feature_cols=["feat_0", "feat_1", "feat_2"],
        regime_state=regime,
        min_train_months=24,
        frozen_params=fast_params,
    )
    r2 = fit_track_c_joint(
        panel,
        feature_cols=["feat_0", "feat_1", "feat_2"],
        regime_state=regime,
        min_train_months=24,
        frozen_params=fast_params,
    )

    # Assert: result type + both IC series populated
    assert isinstance(r1, TrackCJointResult)
    assert not r1.us_ic_series.empty, "US IC series must be populated"
    assert not r1.cn_ic_series.empty, "CN IC series must be populated"
    assert not r1.combined_ic_series.empty, "combined IC series must be populated"
    assert r1.n_walk_folds > 0
    # conditional regression ran (finite, p in [0,1])
    assert np.isfinite(r1.cond_beta), "cond_beta must be finite"
    assert 0.0 <= r1.cond_beta_p <= 1.0, "cond_beta_p must be a valid probability"
    assert r1.cond_n_months > 0

    # H6: two reruns bit-identical (oos_scores + IC series)
    pd.testing.assert_frame_equal(
        r1.oos_scores.sort_values(["date", "region", "ticker"]).reset_index(drop=True),
        r2.oos_scores.sort_values(["date", "region", "ticker"]).reset_index(drop=True),
        check_exact=True,
    )
    pd.testing.assert_series_equal(r1.combined_ic_series, r2.combined_ic_series, check_exact=True)


def test_combined_ic_is_equal_weight_mean_of_regions() -> None:
    # Arrange
    panel = _synthetic_joint_panel(n_months=70, seed=1)
    regime = _synthetic_regime(panel, seed=1)
    fast_params = {"n_estimators": 30, "num_leaves": 8}

    # Act
    res = fit_track_c_joint(
        panel,
        feature_cols=["feat_0", "feat_1", "feat_2"],
        regime_state=regime,
        min_train_months=24,
        frozen_params=fast_params,
    )

    # Assert: combined_ic == mean(us_ic, cn_ic) per month (D2 currency-clean aggregation)
    paired = pd.concat([res.us_ic_series.rename("us"), res.cn_ic_series.rename("cn")], axis=1)
    expected = paired.mean(axis=1, skipna=True).dropna()
    pd.testing.assert_series_equal(
        res.combined_ic_series.sort_index(),
        expected.sort_index(),
        check_names=False,
        check_dtype=False,
    )
