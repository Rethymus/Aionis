# Superseded by the web terminal (web/src/app/(dashboard)/, real committed
# panels) on 2026-08-30 — owner-authorized retirement of the demonstrative
# v2 dashboard (display role fully covered; no production path imports this).
"""Aionis Dashboard v2 — Near-Final Quant Model-Evaluation Interface.

Five analytical dimensions:
  1. Fit Quality (拟合质量) — Do OOS scores predict returns?
  2. Volatility Structure (波动结构) — Is the edge stable or clustered?
  3. Curve Evolution (曲线演化) — How does performance accumulate and drift?
  4. Pre/Post-Event Differences (事件前后差异) — Returns around real events.
  5. Uncertainty (不确定性) — How tight is inference? Is it publishable?

**DEMONSTRATIVE DATA ONLY** — Current data shows analysis methods + interaction
structure, NOT final conclusions. Data improves later with more runs.

Launch:
    uv run streamlit run dashboard/app_v2.py
"""

from __future__ import annotations

import streamlit as st

import dashboard.charts_v2 as charts
import dashboard.demo_data as demo

# Page config
st.set_page_config(
    page_title="Aionis Dashboard v2",
    page_icon="📊",
    layout="wide",
)


def _sidebar() -> tuple[str, str, int, str]:
    """Render sidebar controls; return (phase, arm, horizon, event_type)."""
    with st.sidebar:
        st.header("📊 Aionis v2")

        st.caption("**Anti-Leakage Notice**")
        st.info(
            "This dashboard runs on DEMONSTRATIVE synthetic data only. "
            "It demonstrates the analysis methods and interaction structure, "
            "not final conclusions. Real data comes from confirmatory runs."
        )

        st.divider()

        # Phase selector
        phase = st.selectbox(
            "Phase",
            options=["B", "C", "D", "E1"],
            index=0,
            help="Pre-registered phase (maps to confirmatory:first config_sig)",
        )

        # Arm selector
        if phase == "E1":
            arm_options = ["prop (state)", "base_self"]
        else:
            arm_options = ["state (enhanced)", "base (fundamentals only)"]
        arm = st.selectbox("Arm (Signal)", options=arm_options, index=0)

        # Horizon selector
        horizon = st.selectbox(
            "Horizon (sessions)",
            options=[10, 21, 42],
            index=1,  # Default to frozen confirmatory (21)
            help="21 = frozen confirmatory; other values are EXPLORATORY",
        )

        # Exploratory badge
        if horizon != 21:
            st.warning(f"⚠️ Horizon {horizon} is EXPLORATORY (not frozen confirmatory)")

        # Event-type selector (for Event Study tab)
        event_type = st.selectbox(
            "Event Type (for Event Study)",
            options=["13D", "earnings", "macro"],
            index=0,
        )

        st.divider()
        st.caption("**Data Status**")
        st.caption("Source: Demonstrative (synthetic)")
        st.caption("Real runs: 0 (demo mode)")

        return phase, arm, horizon, event_type


def _preliminary_caption() -> None:
    """Show the standard preliminary data caption."""
    st.caption(
        "💡 **Preliminary data — demonstrates the method, not a final conclusion.** "
        "All charts use demonstrative synthetic data to show analysis patterns. "
        "Real results will come from confirmatory runs."
    )


def view_fit_quality() -> None:
    """Dimension 1: Fit Quality — Do OOS scores predict cross-sectional returns?"""
    st.header("1. Fit Quality (拟合质量)")
    _preliminary_caption()

    # Load demo data
    ic_df = demo._monthly_ic_series()
    oos_df = demo._oos_panel(months=125, n_tickers=500)
    quantile_df = demo._quantile_aggregate(oos_df, n_quantiles=5)

    # KPI tiles
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Mean IC (State)", f"{ic_df['ic_state'].mean():.3f}")
    with col2:
        st.metric("Mean IC (Base)", f"{ic_df['ic_base'].mean():.3f}")
    with col3:
        ic_ir_state = ic_df["ic_state"].mean() / ic_df["ic_state"].std()
        st.metric("IC-IR (State)", f"{ic_ir_state:.2f}")
    with col4:
        hit_rate = (ic_df["ic_state"] > 0).mean() * 100
        st.metric("Hit Rate (State)", f"{hit_rate:.0f}%")

    st.divider()

    # Charts
    tab1, tab2, tab3 = st.tabs(["Cumulative IC", "Score vs Return", "Quantile Spread"])

    with tab1:
        fig = charts._cumulative_ic_chart(ic_df)
        st.plotly_chart(fig, key="fit_cumulative_ic", width="stretch")

    with tab2:
        fig = charts._score_scatter(oos_df)
        st.plotly_chart(fig, key="fit_score_scatter", width="stretch")

    with tab3:
        fig = charts._quantile_spread_chart(quantile_df)
        st.plotly_chart(fig, key="fit_quantile_spread", width="stretch")


def view_volatility() -> None:
    """Dimension 2: Volatility Structure — Is the edge stable or clustered?"""
    st.header("2. Volatility Structure (波动结构)")
    _preliminary_caption()

    # Load demo data
    ic_df = demo._monthly_ic_series()

    # Charts
    tab1, tab2, tab3 = st.tabs(["IC Distribution", "Rolling Vol", "Drawdown"])

    with tab1:
        fig = charts._ic_histogram(ic_df)
        st.plotly_chart(fig, key="vol_ic_histogram", width="stretch")

    with tab2:
        fig = charts._rolling_vol_chart(ic_df, window=12)
        st.plotly_chart(fig, key="vol_rolling_vol", width="stretch")

    with tab3:
        fig = charts._drawdown_chart(ic_df)
        st.plotly_chart(fig, key="vol_drawdown", width="stretch")


def view_evolution() -> None:
    """Dimension 3: Curve Evolution — How does performance accumulate and drift?"""
    st.header("3. Curve Evolution (曲线演化)")
    _preliminary_caption()

    # Load demo data
    ic_df = demo._monthly_ic_series()
    ls_df = demo._ls_returns(months=125)

    # Charts
    tab1, tab2 = st.tabs(["Cumulative IC", "L-S Equity Curve"])

    with tab1:
        fig = charts._cumulative_ic_chart(ic_df)
        st.plotly_chart(fig, key="evo_cumulative_ic", width="stretch")

    with tab2:
        fig = charts._cumulative_ls_equity(ls_df)
        st.plotly_chart(fig, key="evo_ls_equity", width="stretch")


def view_event_study(event_type: str = "13D") -> None:
    """Dimension 4: Event Study — Returns around real-world events."""
    st.header("4. Event Study (事件前后差异)")
    _preliminary_caption()

    st.info(
        "**Note:** Event-study data is SYNTHETIC for demonstration. "
        "Real event analysis requires: (a) event timestamps from Phase D/E1 runs, "
        "(b) daily price data, (c) the new `eval.event_study` module (Gap 3 from design doc)."
    )

    # Load demo CAR path
    car_data = demo._car_path(window_days=60, center=20, n_events=50)

    # Chart
    fig = charts._car_path_chart(car_data, event_type=event_type)
    st.plotly_chart(fig, key="event_car_path", width="stretch")

    st.caption(
        f"**Method:** CAR(t) = cumulative abnormal return over a t−20..t+40 window "
        f"around {event_type} events. CI band via moving-block bootstrap. "
        f"**Reference:** Brown & Warner (1980, 1985), MacKinlay (1997)."
    )


def view_uncertainty() -> None:
    """Dimension 5: Uncertainty — How tight is inference? Is it publishable?"""
    st.header("5. Uncertainty (不确定性)")
    _preliminary_caption()

    # Load demo data
    differential_df = demo._differential_forest_plot()
    bootstrap_samples = demo._bootstrap_distribution()
    ci_df = demo._ci_half_by_phase()

    # Publishability gate KPI
    st.subheader("Publishability Gate (Pre-Registration §7)")
    ci_half = ci_df["ci_half"].iloc[0]  # Use Phase B as example
    badge_html = charts._publishability_badge(ci_half)
    st.markdown(badge_html, unsafe_allow_html=True)

    st.info(
        f"**Gate:** A null result is 'publishable' when CI half-width "
        f"< {charts.PUBLISHABILITY_GATE}. This reflects inference precision, "
        f"not the magnitude of the effect."
    )

    st.divider()

    # Charts
    tab1, tab2, tab3 = st.tabs(["CI Half-Width", "Forest Plot", "Bootstrap"])

    with tab1:
        fig = charts._ci_halfwidth_bar(ci_df)
        st.plotly_chart(fig, key="unc_ci_halfwidth", width="stretch")

    with tab2:
        fig = charts._forest_plot(differential_df)
        st.plotly_chart(fig, key="unc_forest_plot", width="stretch")

    with tab3:
        observed_mean = bootstrap_samples.mean()
        fig = charts._bootstrap_distribution(bootstrap_samples, observed_mean)
        st.plotly_chart(fig, key="unc_bootstrap", width="stretch")


def main() -> None:
    """Main entry point."""
    # Render sidebar
    phase, arm, horizon, event_type = _sidebar()

    # Main title
    st.title("Aionis — Quant Model-Evaluation Dashboard v2")
    st.caption(
        f"Phase: {phase} | Arm: {arm} | Horizon: {horizon} sessions | "
        f"Event Type: {event_type}"
    )

    # Tab navigation
    tabs = st.tabs([
        "Fit Quality",
        "Volatility",
        "Curve Evolution",
        "Event Study",
        "Uncertainty",
    ])

    (t_fit, t_vol, t_evol, t_ev, t_unc) = tabs

    with t_fit:
        view_fit_quality()

    with t_vol:
        view_volatility()

    with t_evol:
        view_evolution()

    with t_ev:
        view_event_study(event_type=event_type)

    with t_unc:
        view_uncertainty()


if __name__ == "__main__":  # pragma: no cover — Streamlit entrypoint
    main()
