"""Tests for Uncertainty CV-fold helpers (dashboard/app.py)."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, "/home/re/code/Aionis")

from dashboard.app import _cv_fold_box, _demo_fold_ics, view_uncertainty


@pytest.fixture
def st_mock():
    """Mock streamlit module for testing view functions."""
    mock = MagicMock()
    mock.warning = MagicMock()
    mock.plotly_chart = MagicMock()
    mock.subheader = MagicMock()
    mock.caption = MagicMock()
    mock.markdown = MagicMock()
    # Return 3 column mocks for st.columns(3)
    mock.columns = MagicMock(return_value=[MagicMock(), MagicMock(), MagicMock()])
    # Mock metric method on columns
    for col_mock in mock.columns.return_value:
        col_mock.metric = MagicMock()
    return mock


def test_cv_fold_box_shape() -> None:
    """_cv_fold_box returns a plotly Figure with box traces."""
    df = pd.DataFrame({
        "fold": [1, 1, 2, 2, 3, 3],
        "repeat": [1, 2, 1, 2, 1, 2],
        "arm": ["treatment"] * 3 + ["base"] * 3,
        "ic": [0.05, 0.06, 0.04, 0.07, 0.03, 0.08],
    })
    fig = _cv_fold_box(df)

    # Should be a plotly Figure
    assert hasattr(fig, "add_trace")
    assert hasattr(fig, "update_layout")


def test_cv_fold_box_multiple_arms() -> None:
    """_cv_fold_box with multiple arms creates separate boxes."""
    df = pd.DataFrame({
        "fold": [1, 1, 2, 2],
        "repeat": [1, 1, 1, 1],
        "arm": ["treatment", "base", "treatment", "base"],
        "ic": [0.05, 0.03, 0.06, 0.04],
    })
    fig = _cv_fold_box(df)

    # Check that data was added
    assert len(fig.data) >= 2  # At least 2 box traces


def test_cv_fold_box_applies_theme() -> None:
    """_cv_fold_box applies dashboard theme to the figure."""
    df = pd.DataFrame({
        "fold": [1, 2, 3],
        "repeat": [1, 1, 1],
        "arm": ["treatment", "treatment", "treatment"],
        "ic": [0.05, 0.06, 0.04],
    })
    fig = _cv_fold_box(df)

    # Check theme application (font family should be set)
    layout = fig.layout
    assert layout.font.family is not None


def test_demo_fold_ics_reproducibility() -> None:
    """_demo_fold_ics with rng=7 produces identical output."""
    df1 = _demo_fold_ics(n_folds=5, n_repeats=3, rng=np.random.default_rng(7))
    df2 = _demo_fold_ics(n_folds=5, n_repeats=3, rng=np.random.default_rng(7))
    pd.testing.assert_frame_equal(df1, df2)


def test_demo_fold_ics_structure() -> None:
    """Demo fold ICs has correct columns and dimensions."""
    df = _demo_fold_ics(n_folds=5, n_repeats=3, rng=np.random.default_rng(7))
    assert list(df.columns) == ["fold", "repeat", "arm", "ic"]
    assert len(df) == 5 * 3 * 2  # n_folds * n_repeats * 2 arms
    assert df["fold"].nunique() == 5
    assert df["repeat"].nunique() == 3
    assert set(df["arm"]) == {"treatment", "base"}


def test_demo_fold_ics_rng_default() -> None:
    """_demo_fold_ics uses rng=7 when no seed provided."""
    df1 = _demo_fold_ics(n_folds=3, n_repeats=2, rng=None)  # type: ignore
    df2 = _demo_fold_ics(n_folds=3, n_repeats=2, rng=None)  # type: ignore
    pd.testing.assert_frame_equal(df1, df2)


def test_view_uncertainty_cv_fold_demo(st_mock) -> None:
    """view_uncertainty renders CV-fold stability section on demo."""
    import streamlit as st
    runs = []
    run = {
        "run_id": "demo-unc",
        "config_committed": {"sha256": "abcd"},
        "config_sig": "a1b2c3d4e5f6g7h8",
        "differential": {"mean_diff": 0.01, "ci_lo": -0.005, "ci_hi": 0.025},
        "controls": {},
    }

    # Mock streamlit functions
    st.warning = st_mock.warning
    st.plotly_chart = st_mock.plotly_chart
    st.subheader = st_mock.subheader
    st.caption = st_mock.caption
    st.markdown = st_mock.markdown
    st.columns = st_mock.columns

    view_uncertainty(runs, run)

    # Should have rendered demo warning and CV-fold chart
    assert st_mock.warning.called or st_mock.plotly_chart.called


def test_view_uncertainty_demo_warning_emitted(st_mock) -> None:
    """Demo CV-fold path emits DEMO warning."""
    import streamlit as st
    runs = []
    run = {
        "run_id": "demo-unc2",
        "config_committed": {"sha256": "efgh"},
        "config_sig": "x1y2z3w4v5u6t7s8",
        "differential": {"mean_diff": 0.015, "ci_lo": -0.01, "ci_hi": 0.04},
        "controls": {},
    }

    # Mock streamlit functions
    st.warning = st_mock.warning
    st.plotly_chart = st_mock.plotly_chart
    st.subheader = st_mock.subheader
    st.caption = st_mock.caption
    st.markdown = st_mock.markdown
    st.columns = st_mock.columns

    view_uncertainty(runs, run)

    warnings = [call.args[0] for call in st_mock.warning.call_args_list]
    assert any("DEMO" in w and "not a research conclusion" in w for w in warnings), \
        f"Expected DEMO warning, got: {warnings}"
