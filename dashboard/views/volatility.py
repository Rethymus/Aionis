"""Volatility Structure view — IC distribution + metrics."""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from dashboard.views.charts import (
    _cumulative_ic,
    _drawdown_chart,
    _ic_histogram,
    _rolling_ic_chart,
)
from dashboard.views.data_loading import _phase_of
from dashboard.views.helpers import (
    _calmar,
    _downside_deviation,
    _monthly_heatmap,
    _return_distribution,
    _sharpe,
    _top_drawdowns,
    _vol_of_vol,
)


def view_volatility(run: dict) -> None:
    phase, treat = _phase_of(run)
    st.subheader(f"Volatility Structure — phase {phase}")

    # Use IC series as a proxy for returns in volatility metrics
    ic = run["ic_state"]

    # New KPI tiles
    st.markdown("**Volatility metrics**")
    sharpe_val = _sharpe(ic)
    calmar_val = _calmar(ic)
    downside_val = _downside_deviation(ic)
    vov_val = _vol_of_vol(ic)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Annualized IC-IR", f"{sharpe_val:+.3f}" if np.isfinite(sharpe_val) else "N/A",
              help="mean(monthly IC)/σ(IC)·√12 — signal consistency on the IC series, "
                   "NOT a strategy Sharpe (see Strategy Return tab for that).")
    c2.metric("Calmar (cum IC / max DD)", f"{calmar_val:+.3f}" if np.isfinite(calmar_val) else "∞",
              help="Cumulative-IC path over its max drawdown — descriptive on the signal "
                   "path, not a return metric.")
    c3.metric("Downside deviation", f"{downside_val:.4f}")
    c4.metric("Vol-of-vol", f"{vov_val:.4f}" if np.isfinite(vov_val) else "N/A")
    st.caption("Volatility metrics are computed on the monthly rank-IC series "
               "(signal consistency), not on strategy returns.")

    st.markdown("**IC distribution** (spread ⇒ how volatile the monthly signal is)")
    st.plotly_chart(_ic_histogram(run["ic_state"]), use_container_width=True, key="vol-ic-hist")

    st.markdown("**Return distribution** vs normal overlay")
    st.plotly_chart(_return_distribution(ic), use_container_width=True, key="vol-ret-dist")

    st.markdown("**Underwater curve** — cumulative IC drawdown (how far below its peak)")
    st.plotly_chart(_drawdown_chart(_cumulative_ic(run["ic_state"])),
        use_container_width=True, key="vol-drawdown")


def view_evolution(run: dict) -> None:
    phase, treat = _phase_of(run)
    st.subheader(f"Curve Evolution — phase {phase}")

    # Use IC series as the primary metric for evolution analysis
    ic = run["ic_state"]

    # Monthly returns heatmap
    st.markdown("**Monthly IC heatmap** (year×month)")
    pivot = _monthly_heatmap(ic)
    if not pivot.empty:
        fig = go.Figure(data=go.Heatmap(
            z=pivot.values,
            x=[f"{m:02d}" for m in pivot.columns],  # Month columns "01"-"12"
            y=[str(y) for y in pivot.index],  # Year rows
            colorscale="RdBu",
            zmid=0,
            colorbar={"title": "IC"},
        ))
        fig.update_layout(
            xaxis_title="month",
            yaxis_title="year",
            height=400,
            margin=dict(l=10, r=10, t=20, b=10),
            title="monthly IC (red=negative, blue=positive)"
        )
        st.plotly_chart(fig, use_container_width=True, key="evol-heatmap")
    else:
        st.info("Not enough data for monthly heatmap.")

    # Top drawdown periods table
    st.markdown("**Top drawdown periods**")
    drawdowns = _top_drawdowns(ic, k=5)
    if not drawdowns.empty:
        show = drawdowns.copy()
        show["peak_date"] = show["peak_date"].dt.strftime("%Y-%m-%d")
        show["trough_date"] = show["trough_date"].dt.strftime("%Y-%m-%d")
        show["depth"] = show["depth"].apply(lambda x: f"{x:.3f}")
        show["duration"] = show["duration"].apply(lambda x: f"{int(x)}m")
        st.dataframe(show, use_container_width=True, hide_index=True)
    else:
        st.info("No significant drawdowns detected.")

    # Existing cumulative IC and rolling IC charts
    from dashboard.views.charts import _cumulative_ic_chart, _ic_kpi

    se = _ic_kpi(ic)["std"]  # monthly σ (not se_hac=σ/√n) for the band
    st.markdown("**Cumulative IC with random-walk CI band** (evolution of the signal over time)")
    st.plotly_chart(_cumulative_ic_chart(ic, treat, se),
                   use_container_width=True, key="evol-cum-ic")

    st.markdown("**Rolling 12-month IC + IC-vol** (trend + changing volatility)")
    st.plotly_chart(_rolling_ic_chart(ic, 12), use_container_width=True, key="evol-rolling")
