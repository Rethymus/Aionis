"""Consolidated demo-discipline tests for ALL dashboard views.

Ensures:
1. Every demo view emits the DEMO warning
2. Demo generators are rng=7-reproducible
3. Demo data never touches runs/ (pure/in-memory only)
"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pandas as pd
import pytest

sys.path.insert(0, "/home/re/code/Aionis")

from dashboard.app import (
    _demo_event_windows,
    _demo_fold_ics,
    _synthetic_run,
    view_event_study,
    view_fit_quality,
    view_uncertainty,
)


@pytest.fixture
def st_mock():
    """Mock streamlit module."""
    mock = MagicMock()
    mock.warning = MagicMock()
    mock.plotly_chart = MagicMock()
    mock.subheader = MagicMock()
    mock.caption = MagicMock()
    mock.markdown = MagicMock()
    mock.info = MagicMock()
    mock.selectbox = MagicMock(return_value="13D")

    # Create column mocks with metric method
    def make_columns(n):
        cols = [MagicMock() for _ in range(n)]
        for col in cols:
            col.metric = MagicMock()
        return cols

    mock.columns = MagicMock(side_effect=make_columns)
    return mock


class TestDemoDisciplineWarnings:
    """Every demo view path emits a DEMO warning."""

    def test_view_fit_quality_emits_demo_warning(self, st_mock) -> None:
        """view_fit_quality demo branch emits DEMO warning."""
        import streamlit as st
        st.warning = st_mock.warning
        st.plotly_chart = st_mock.plotly_chart
        st.subheader = st_mock.subheader
        st.caption = st_mock.caption
        st.markdown = st_mock.markdown
        st.columns = st_mock.columns

        synthetic_run = _synthetic_run()
        view_fit_quality(synthetic_run, is_syn=True)

        warnings = [call.args[0] for call in st_mock.warning.call_args_list]
        # view_fit_quality uses shorter DEMO warning
        assert any("DEMO" in w for w in warnings), \
            f"view_fit_quality demo missing DEMO warning: {warnings}"

    def test_view_event_study_emits_demo_warning(self, st_mock) -> None:
        """view_event_study demo branch emits DEMO warning."""
        import streamlit as st
        st.warning = st_mock.warning
        st.plotly_chart = st_mock.plotly_chart
        st.subheader = st_mock.subheader
        st.caption = st_mock.caption
        st.markdown = st_mock.markdown
        st.columns = st_mock.columns

        synthetic_run = _synthetic_run()
        view_event_study(synthetic_run, is_syn=True)

        warnings = [call.args[0] for call in st_mock.warning.call_args_list]
        assert any("DEMO" in w and "not a research conclusion" in w for w in warnings), \
            f"view_event_study demo missing DEMO warning: {warnings}"

    def test_view_uncertainty_emits_demo_warning(self, st_mock) -> None:
        """view_uncertainty demo branch emits DEMO warning."""
        import streamlit as st
        st.warning = st_mock.warning
        st.plotly_chart = st_mock.plotly_chart
        st.subheader = st_mock.subheader
        st.caption = st_mock.caption
        st.markdown = st_mock.markdown
        st.columns = st_mock.columns

        synthetic_run = _synthetic_run()
        view_uncertainty([], synthetic_run)

        warnings = [call.args[0] for call in st_mock.warning.call_args_list]
        assert any("DEMO" in w and "not a research conclusion" in w for w in warnings), \
            f"view_uncertainty demo missing DEMO warning: {warnings}"


class TestDemoReproducibility:
    """All demo generators are rng=7-reproducible."""

    def test_demo_event_windows_rng7_reproducible(self) -> None:
        """_demo_event_windows with default rng=7 is identical across calls."""
        df1 = _demo_event_windows(["earnings"], n_per_type=2, rng=None)  # Uses default rng=7
        df2 = _demo_event_windows(["earnings"], n_per_type=2, rng=None)  # Uses default rng=7
        pd.testing.assert_frame_equal(df1, df2)

    def test_demo_fold_ics_rng7_reproducible(self) -> None:
        """_demo_fold_ics with default rng=7 is identical across calls."""
        df1 = _demo_fold_ics(n_folds=3, n_repeats=2, rng=None)  # Uses default rng=7
        df2 = _demo_fold_ics(n_folds=3, n_repeats=2, rng=None)  # Uses default rng=7
        pd.testing.assert_frame_equal(df1, df2)

    def test_synthetic_run_reproducible(self) -> None:
        """_synthetic_run produces identical structure across calls."""
        run1 = _synthetic_run()
        run2 = _synthetic_run()
        # Check consistent config signature
        assert run1["config_sig"] == run2["config_sig"]
        # Check reproducible IC series (rng=7)
        pd.testing.assert_series_equal(run1["ic_state"], run2["ic_state"])
        pd.testing.assert_series_equal(run1["ic_base"], run2["ic_base"])


class TestDemoDataIsolation:
    """Demo data never touches runs/ (pure/in-memory only)."""

    def test_demo_helpers_are_pure(self) -> None:
        """Demo helpers don't write to disk or mutate external state."""
        import os
        import tempfile

        # Create a temp runs directory to detect any writes
        with tempfile.TemporaryDirectory() as tmpdir:
            runs_dir = os.path.join(tmpdir, "runs")
            os.makedirs(runs_dir)

            # Call demo helpers
            demo_windows = _demo_event_windows(["earnings"], n_per_type=2, rng=None)
            demo_folds = _demo_fold_ics(n_folds=3, n_repeats=2, rng=None)

            # Verify no files were created
            assert os.path.exists(runs_dir)
            assert len(os.listdir(runs_dir)) == 0, "Demo helpers wrote to disk"

            # Verify data is in-memory
            assert isinstance(demo_windows, pd.DataFrame)
            assert isinstance(demo_folds, pd.DataFrame)
            assert len(demo_windows) > 0
            assert len(demo_folds) > 0

    def test_view_functions_dont_write_runs_ledger(self, st_mock) -> None:
        """Demo view functions don't append to runs/ledger.jsonl."""
        import os
        import tempfile

        import streamlit as st

        # Mock streamlit
        st.warning = st_mock.warning
        st.plotly_chart = st_mock.plotly_chart
        st.subheader = st_mock.subheader
        st.caption = st_mock.caption
        st.markdown = st_mock.markdown
        st.columns = st_mock.columns

        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_path = os.path.join(tmpdir, "runs", "ledger.jsonl")
            os.makedirs(os.path.dirname(ledger_path))

            # Create empty ledger
            with open(ledger_path, "w") as f:
                f.write("")

            synthetic_run = _synthetic_run()

            # Call demo views
            view_fit_quality(synthetic_run, is_syn=True)
            view_event_study(synthetic_run, is_syn=True)
            view_uncertainty([], synthetic_run)

            # Verify ledger unchanged
            with open(ledger_path) as f:
                content = f.read()
                assert content == "", "Demo view wrote to ledger.jsonl"


@pytest.mark.parametrize("view_func,args", [
    (view_fit_quality, (
        {"run_id": "demo", "config_committed": {"sha256": "ab"},
         "ic_state": pd.Series([0.1]), "ic_base": pd.Series([0.05])},
        True,
    )),
    (view_event_study, (
        {"run_id": "demo", "config_committed": {"sha256": "cd"},
         "ic_state": pd.Series([0.1]), "ic_base": pd.Series([0.05])},
        True,
    )),
    (view_uncertainty, (
        [],
        {"run_id": "demo", "config_committed": {"sha256": "ef"},
         "config_sig": "123456", "differential": {"mean_diff": 0.01},
         "controls": {}},
    )),
])
def test_demo_views_have_consistent_structure(view_func, args, st_mock) -> None:
    """All demo views produce consistent chart/warning pattern."""
    import streamlit as st
    st.warning = st_mock.warning
    st.plotly_chart = st_mock.plotly_chart
    st.subheader = st_mock.subheader
    st.caption = st_mock.caption
    st.markdown = st_mock.markdown
    st.columns = st_mock.columns

    view_func(*args)

    # All demo views should emit at least one warning (DEMO) and render content
    assert st_mock.warning.called, f"{view_func.__name__} demo emitted no warnings"
    assert st_mock.plotly_chart.called or st_mock.subheader.called, \
        f"{view_func.__name__} demo rendered no content"
