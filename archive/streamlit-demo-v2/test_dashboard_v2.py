# Superseded by the web terminal (web/src/app/(dashboard)/, real committed
# panels) on 2026-08-30 — owner-authorized retirement of the demonstrative
# v2 dashboard (display role fully covered; no production path imports this).
# The tests moved with the code they cover; dashboard demo-discipline coverage
# for the v1 app remains in tests/test_dashboard_demo_discipline.py.
"""Tests for Aionis dashboard v2 (demonstrative data + chart builders)."""

import numpy as np
import pandas as pd

import dashboard.charts_v2 as charts
import dashboard.demo_data as demo


class TestDemoData:
    """Test that demo data generators are deterministic and well-formed."""

    def test_monthly_ic_series_deterministic(self):
        """Same seed → identical output."""
        df1 = demo._monthly_ic_series()
        df2 = demo._monthly_ic_series()
        pd.testing.assert_frame_equal(df1, df2)

    def test_monthly_ic_series_shape(self):
        """Check expected columns and shape."""
        df = demo._monthly_ic_series(months=125)
        assert len(df) == 125
        assert list(df.columns) == ["date", "ic_state", "ic_base"]

    def test_oos_panel_deterministic(self):
        """Same seed → identical output."""
        df1 = demo._oos_panel(months=125, n_tickers=500)
        df2 = demo._oos_panel(months=125, n_tickers=500)
        pd.testing.assert_frame_equal(df1, df2)

    def test_oos_panel_shape(self):
        """Check expected columns and approximate size."""
        df = demo._oos_panel(months=125, n_tickers=500)
        assert "date" in df.columns
        assert "ticker" in df.columns
        assert "score" in df.columns
        assert "y_fwd_ret" in df.columns
        # Approximate size (some months may have slight variation)
        assert len(df) > 60000  # 125 months * 500 tickers

    def test_quantile_aggregate_deterministic(self):
        """Same seed → identical output."""
        oos_df = demo._oos_panel(months=12, n_tickers=100)
        agg1 = demo._quantile_aggregate(oos_df, n_quantiles=5)
        agg2 = demo._quantile_aggregate(oos_df, n_quantiles=5)
        pd.testing.assert_frame_equal(agg1, agg2)

    def test_quantile_aggregate_shape(self):
        """Check expected columns."""
        oos_df = demo._oos_panel(months=12, n_tickers=100)
        agg = demo._quantile_aggregate(oos_df, n_quantiles=5)
        assert list(agg.columns) == ["date", "quantile", "mean_score", "mean_ret", "n"]

    def test_ls_returns_deterministic(self):
        """Same seed → identical output."""
        df1 = demo._ls_returns(months=125)
        df2 = demo._ls_returns(months=125)
        pd.testing.assert_frame_equal(df1, df2)

    def test_ls_returns_shape(self):
        """Check expected columns."""
        df = demo._ls_returns(months=125)
        assert "date" in df.columns
        assert "state" in df.columns
        assert "base" in df.columns

    def test_car_path_deterministic(self):
        """Same seed → identical output."""
        car1 = demo._car_path()
        car2 = demo._car_path()
        assert car1["window"] == car2["window"]
        np.testing.assert_array_equal(car1["t"], car2["t"])
        np.testing.assert_array_equal(car1["car"], car2["car"])

    def test_car_path_structure(self):
        """Check expected keys."""
        car = demo._car_path()
        assert "window" in car
        assert "t" in car
        assert "car" in car
        assert "ci_lo" in car
        assert "ci_hi" in car
        assert "n_events" in car

    def test_differential_forest_plot_deterministic(self):
        """Same seed → identical output."""
        df1 = demo._differential_forest_plot()
        df2 = demo._differential_forest_plot()
        pd.testing.assert_frame_equal(df1, df2)

    def test_bootstrap_distribution_deterministic(self):
        """Same seed → identical output."""
        arr1 = demo._bootstrap_distribution()
        arr2 = demo._bootstrap_distribution()
        np.testing.assert_array_equal(arr1, arr2)

    def test_ci_half_by_phase_deterministic(self):
        """Same seed → identical output."""
        df1 = demo._ci_half_by_phase()
        df2 = demo._ci_half_by_phase()
        pd.testing.assert_frame_equal(df1, df2)


class TestChartBuilders:
    """Test that chart builders return valid plotly figures."""

    def test_cumulative_ic_chart(self):
        """Returns a go.Figure with expected traces."""
        ic_df = demo._monthly_ic_series()
        fig = charts._cumulative_ic_chart(ic_df)
        assert fig is not None
        assert len(fig.data) >= 2  # At least state and base lines
        assert fig.layout.title.text == "Cumulative Rank-IC"

    def test_quantile_spread_chart(self):
        """Returns a go.Figure with bar trace."""
        oos_df = demo._oos_panel(months=12, n_tickers=100)
        quantile_df = demo._quantile_aggregate(oos_df, n_quantiles=5)
        fig = charts._quantile_spread_chart(quantile_df)
        assert fig is not None
        assert len(fig.data) >= 1  # Bar trace

    def test_score_scatter(self):
        """Returns a go.Figure with scatter trace."""
        oos_df = demo._oos_panel(months=12, n_tickers=100)
        fig = charts._score_scatter(oos_df)
        assert fig is not None
        assert len(fig.data) >= 1  # Scatter trace

    def test_ic_histogram(self):
        """Returns a go.Figure with histogram traces."""
        ic_df = demo._monthly_ic_series()
        fig = charts._ic_histogram(ic_df)
        assert fig is not None
        assert len(fig.data) >= 2  # State and base histograms

    def test_rolling_vol_chart(self):
        """Returns a go.Figure with line traces."""
        ic_df = demo._monthly_ic_series()
        fig = charts._rolling_vol_chart(ic_df, window=12)
        assert fig is not None
        assert len(fig.data) >= 2  # State and base rolling vol

    def test_drawdown_chart(self):
        """Returns a go.Figure with filled area."""
        ic_df = demo._monthly_ic_series()
        fig = charts._drawdown_chart(ic_df)
        assert fig is not None
        assert len(fig.data) >= 1  # Drawdown curve

    def test_cumulative_ls_equity(self):
        """Returns a go.Figure with line traces."""
        ls_df = demo._ls_returns(months=125)
        fig = charts._cumulative_ls_equity(ls_df)
        assert fig is not None
        assert len(fig.data) >= 2  # At least state and base

    def test_car_path_chart(self):
        """Returns a go.Figure with CI ribbon."""
        car_data = demo._car_path()
        fig = charts._car_path_chart(car_data, event_type="13D")
        assert fig is not None
        assert len(fig.data) >= 1  # CAR path

    def test_ci_halfwidth_bar(self):
        """Returns a go.Figure with bar trace and gate line."""
        ci_df = demo._ci_half_by_phase()
        fig = charts._ci_halfwidth_bar(ci_df)
        assert fig is not None
        assert len(fig.data) >= 1  # Bar trace
        # Check for gate reference (appears as shape or annotation)
        assert "CI Half-Width by Phase" in fig.layout.title.text

    def test_forest_plot(self):
        """Returns a go.Figure with error bars."""
        diff_df = demo._differential_forest_plot()
        fig = charts._forest_plot(diff_df)
        assert fig is not None
        assert len(fig.data) >= 1  # At least one control

    def test_bootstrap_distribution(self):
        """Returns a go.Figure with histogram."""
        bootstrap = demo._bootstrap_distribution()
        observed = bootstrap.mean()
        fig = charts._bootstrap_distribution(bootstrap, observed)
        assert fig is not None
        assert len(fig.data) >= 1  # Histogram trace

    def test_publishability_badge(self):
        """Returns HTML badge string."""
        # Below gate (publishable)
        badge_publishable = charts._publishability_badge(0.012)
        assert "PUBLISHABLE" in badge_publishable
        assert "green" in badge_publishable or "#16a34a" in badge_publishable

        # Above gate (not publishable)
        badge_not = charts._publishability_badge(0.018)
        assert "NOT PUBLISHABLE" in badge_not
        assert "red" in badge_not or "#dc2626" in badge_not


class TestAntiLeakage:
    """Test anti-leakage: no real-data/ledger/network calls."""

    def test_no_real_data_imports(self):
        """Demo data should NOT import from aionis.reporting or aionis.eval."""
        import inspect

        import dashboard.demo_data as demo_module

        source = inspect.getsource(demo_module)
        # Should not import these
        assert "aionis.reporting" not in source
        assert "aionis.eval" not in source
        assert "results." not in source
        assert "ledger" not in source.lower()

    def test_no_network_calls(self):
        """Demo generators should not make network calls."""
        # All generators use only numpy/pandas with fixed seed
        # No requests, no http, no external APIs
        import inspect

        import dashboard.demo_data as demo_module

        source = inspect.getsource(demo_module)
        assert "requests" not in source
        assert "urllib" not in source
        assert "http" not in source.lower()
        assert "api" not in source.lower()

    def test_synthetic_labels_present(self):
        """Data and charts should be labeled DEMONSTRATIVE/SYNTHETIC."""
        import inspect

        import dashboard.demo_data as demo_module

        demo_source = inspect.getsource(demo_module)

        # Check for DEMONSTRATIVE or SYNTHETIC in docstrings
        assert "DEMONSTRATIVE" in demo_source or "synthetic" in demo_source.lower()


class TestChartFunctionSizes:
    """Test that chart functions follow coding-style rules (<50 lines)."""

    def test_chart_functions_under_50_lines(self):
        """All chart builder functions should be <50 lines."""
        import inspect

        import dashboard.charts_v2 as charts_module

        chart_functions = [
            name for name in dir(charts_module)
            if name.startswith("_") and not name.startswith("__")
        ]

        for func_name in chart_functions:
            func = getattr(charts_module, func_name)
            if callable(func) and not func_name.startswith("__"):
                source_lines = len(inspect.getsourcelines(func)[0])  # Count actual lines
                assert source_lines < 50, f"{func_name} is {source_lines} lines (>= 50)"


class TestImportsWork:
    """Test that imports work without errors."""

    def test_import_demo_data(self):
        """Should import without errors."""
        import dashboard.demo_data
        assert dashboard.demo_data is not None

    def test_import_charts_v2(self):
        """Should import without errors."""
        import dashboard.charts_v2
        assert dashboard.charts_v2 is not None

    def test_import_app_v2(self):
        """Should import without errors."""
        import dashboard.app_v2
        assert dashboard.app_v2 is not None
