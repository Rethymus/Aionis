"""Tests for Event Study CAR helpers (dashboard/app.py)."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, "/home/re/code/Aionis")

from dashboard.app import _car_ci, _car_curve, _demo_event_windows, view_event_study


@pytest.fixture
def st_mock():
    """Mock streamlit module for testing view functions."""
    mock = MagicMock()
    mock.warning = MagicMock()
    mock.plotly_chart = MagicMock()
    mock.subheader = MagicMock()
    mock.caption = MagicMock()
    mock.markdown = MagicMock()
    return mock


def test_car_curve_basic_cumulation() -> None:
    """CAR(τ) = cumulative mean of abnormal returns across events."""
    # Three events, each with 5 time steps (τ=-2 to +2)
    df = pd.DataFrame({
        "event_type": ["A"] * 5 + ["B"] * 5 + ["C"] * 5,
        "event_id": ["e1"] * 5 + ["e2"] * 5 + ["e3"] * 5,
        "tau": [-2, -1, 0, 1, 2] * 3,
        "abnormal_return": [
            # Event 1: constant +0.01 per step
            0.01, 0.01, 0.01, 0.01, 0.01,
            # Event 2: constant +0.02 per step
            0.02, 0.02, 0.02, 0.02, 0.02,
            # Event 3: constant -0.01 per step
            -0.01, -0.01, -0.01, -0.01, -0.01,
        ],
    })
    result = _car_curve(df, t_pre=2, t_post=2)

    # Mean abnormal returns per τ: (0.01+0.02-0.01)/3 = 0.0067 at each τ
    # CAR convention: baseline at τ=-2 is 0, then cumsum
    # CAR at τ=-2: 0.0 (baseline)
    # CAR at τ=-1: 0.0067 (first cumulative step)
    # CAR at τ=0: 0.0133 (second cumulative step)
    expected = pd.Series([0.0, 0.006667, 0.013333, 0.02, 0.026667], index=[-2, -1, 0, 1, 2])
    pd.testing.assert_series_equal(result, expected, atol=1e-4)


def test_car_curve_baseline_convention() -> None:
    """CAR(−t_pre) = 0 by construction (cumsum from baseline)."""
    df = pd.DataFrame({
        "event_type": ["earnings"] * 5,
        "event_id": ["e1"] * 5,
        "tau": [-2, -1, 0, 1, 2],
        "abnormal_return": [0.01, 0.02, 0.03, 0.04, 0.05],
    })
    result = _car_curve(df, t_pre=2, t_post=2)
    # First τ in window should be zero (baseline before cumulation)
    assert result.iloc[0] == pytest.approx(0.0, abs=1e-10)


def test_car_ci_shape() -> None:
    """_car_ci returns DataFrame with mean, lo, hi columns."""
    df = pd.DataFrame({
        "event_type": ["X"] * 5,
        "event_id": ["e1"] * 5,
        "tau": [-2, -1, 0, 1, 2],
        "abnormal_return": [0.01, 0.02, 0.03, 0.04, 0.05],
    })
    result = _car_ci(df, t_pre=2, t_post=2)
    assert isinstance(result, pd.DataFrame)
    assert list(result.columns) == ["mean", "lo", "hi"]
    assert len(result) == 5  # one row per τ


def test_car_ci_monotone_widening() -> None:
    """CI widens monotonically with fewer events (std/sqrt(n))."""
    # Single event (large CI due to std/sqrt(1))
    single = pd.DataFrame({
        "event_type": ["A"] * 5,
        "event_id": ["e1"] * 5,
        "tau": [-2, -1, 0, 1, 2],
        "abnormal_return": [0.0, 0.1, -0.1, 0.2, -0.2],
    })
    # Hundred events (tighter CI)
    many = pd.concat([single] * 100, ignore_index=True)
    for i in range(100):
        many.loc[i * 5:(i + 1) * 5, "event_id"] = f"e{i}"

    ci_single = _car_ci(single, t_pre=2, t_post=2)
    ci_many = _car_ci(many, t_pre=2, t_post=2)

    # CI width for single event > CI width for many events
    single_width = (ci_single["hi"] - ci_single["lo"]).mean()
    many_width = (ci_many["hi"] - ci_many["lo"]).mean()
    assert single_width > many_width * 5  # much wider with n=1


def test_demo_event_windows_reproducibility() -> None:
    """_demo_event_windows with rng=7 produces identical output."""
    event_types = ["earnings", "13D", "macro"]
    df1 = _demo_event_windows(event_types, n_per_type=3, rng=np.random.default_rng(7))
    df2 = _demo_event_windows(event_types, n_per_type=3, rng=np.random.default_rng(7))
    pd.testing.assert_frame_equal(df1, df2)


def test_demo_event_windows_structure() -> None:
    """Demo window has correct columns and dimensions."""
    df = _demo_event_windows(["earnings"], n_per_type=2, rng=np.random.default_rng(7))
    assert list(df.columns) == ["event_type", "event_id", "tau", "abnormal_return"]
    assert len(df) == 2 * 31  # 2 events × 31 τ values (t_pre=10, t_post=20 → 31 steps)
    assert set(df["event_type"]) == {"earnings"}
    assert df["event_id"].nunique() == 2
    assert df["tau"].min() == -10
    assert df["tau"].max() == 20


def test_demo_event_windows_rng_default() -> None:
    """_demo_event_windows uses rng=7 when no seed provided (consistent demo)."""
    df1 = _demo_event_windows(["earnings"], n_per_type=2, rng=None)  # type: ignore
    df2 = _demo_event_windows(["earnings"], n_per_type=2, rng=None)  # type: ignore
    pd.testing.assert_frame_equal(df1, df2)


def test_view_event_study_demo_warning(st_mock) -> None:
    """view_event_study emits DEMO warning on synthetic run."""
    import streamlit as st
    synthetic_run = {
        "run_id": "demo-123",
        "config_committed": {"sha256": "abcd"},
        "ic_state": pd.Series([0.1, 0.2]),
        "ic_base": pd.Series([0.05, 0.15]),
    }
    # Mock streamlit functions
    st.warning = st_mock.warning
    st.plotly_chart = st_mock.plotly_chart
    st.subheader = st_mock.subheader
    st.caption = st_mock.caption
    st.markdown = st_mock.markdown

    view_event_study(synthetic_run, is_syn=True)
    warnings = [call.args[0] for call in st_mock.warning.call_args_list]
    assert any("DEMO" in w and "not a research conclusion" in w for w in warnings), \
        f"Expected DEMO warning, got: {warnings}"


def test_view_event_study_demo_no_real_module(st_mock) -> None:
    """Demo path renders even without real event_study module."""
    import streamlit as st
    synthetic_run = {
        "run_id": "demo-456",
        "config_committed": {"sha256": "efgh"},
        "ic_state": pd.Series([0.1, 0.2]),
        "ic_base": pd.Series([0.05, 0.15]),
    }
    # Mock streamlit functions
    st.warning = st_mock.warning
    st.plotly_chart = st_mock.plotly_chart
    st.subheader = st_mock.subheader
    st.caption = st_mock.caption
    st.markdown = st_mock.markdown

    # Should not raise, should render demo
    view_event_study(synthetic_run, is_syn=True)
    assert st_mock.warning.called
    assert st_mock.plotly_chart.called  # CAR curves rendered


def test_view_event_study_demo_rng_reproducibility(st_mock) -> None:
    """Demo CAR curves are identical across calls (rng=7)."""
    import streamlit as st
    synthetic_run = {
        "run_id": "demo-789",
        "config_committed": {"sha256": "ijkl"},
        "ic_state": pd.Series([0.1, 0.2]),
        "ic_base": pd.Series([0.05, 0.15]),
    }
    # Mock streamlit functions
    st.warning = st_mock.warning
    st.plotly_chart = st_mock.plotly_chart
    st.subheader = st_mock.subheader
    st.caption = st_mock.caption
    st.markdown = st_mock.markdown

    view_event_study(synthetic_run, is_syn=True)
    first_chart_args = st_mock.plotly_chart.call_args_list[0][0][0]

    st_mock.reset_mock()
    view_event_study(synthetic_run, is_syn=True)
    second_chart_args = st_mock.plotly_chart.call_args_list[0][0][0]

    # Plotly figures with identical data should serialize to same JSON
    import json
    assert json.dumps(first_chart_args, default=str) == json.dumps(second_chart_args, default=str)
