"""Fit Quality view — KPI row + charts."""
from __future__ import annotations

import numpy as np
import streamlit as st

from dashboard.views.charts import (
    _cumulative_ic_chart,
    _ic_by_regime_box,
    _ic_chart,
    _ic_kpi,
    _quantile_spread_chart,
    _score_vs_return_scatter_with_fit,
)
from dashboard.views.data_loading import _phase_of
from dashboard.views.helpers import _r2


def view_fit_quality(run: dict, is_syn: bool) -> None:
    phase, treat = _phase_of(run)
    st.subheader(f"Fit Quality — phase {phase} ({treat})")
    if is_syn:
        st.warning("DEMO: synthetic data.")

    st.markdown("**KPI row** — does the score predict cross-sectional returns?")
    _kpi_row(run["ic_state"], treat)
    _kpi_row(run["ic_base"], "base")

    # Add R² KPI when OOS data is available
    oos = run.get("oos_state")
    if oos is not None and len(oos):
        r2 = _r2(oos)
        st.metric("Out-of-sample R² (y ~ score)", f"{r2:.3f}" if not np.isnan(r2) else "N/A")

    st.markdown("**Cumulative IC vs random-walk 95% band** — stays in band ⇒ no detectable skill")
    se = _ic_kpi(run["ic_state"])["std"]  # monthly σ (not se_hac=σ/√n) for the band
    st.plotly_chart(_cumulative_ic_chart(run["ic_state"], treat, se),
                    use_container_width=True, key="fit-cum-ic")

    st.markdown("**Monthly rank-IC — treatment vs base**")
    st.plotly_chart(_ic_chart(run), use_container_width=True, key="fit-ic-monthly")

    if oos is not None and len(oos):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Score vs forward-return with regression line**")
            st.plotly_chart(_score_vs_return_scatter_with_fit(oos),
                               use_container_width=True, key="fit-scatter")
        with c2:
            st.markdown("**Quantile spread** (decile)")
            st.plotly_chart(_quantile_spread_chart(oos),
                                  use_container_width=True, key="fit-quantile")

        # Add IC-by-regime box plot
        st.markdown("**IC by volatility regime** (rolling-σ quartiles)")
        st.plotly_chart(_ic_by_regime_box(run["ic_state"]),
                    use_container_width=True, key="fit-regime-box")
    else:
        st.info("Score-vs-return scatter / quantile spread / R² need the per-ticker OOS panel, "
                "which this run didn't persist (pre-schema-2). A re-run enables them.")


def _kpi_row(ic, label: str) -> None:
    k = _ic_kpi(ic)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"mean IC ({label})", f"{k['mean']:+.4f}")
    c2.metric("NW-HAC t", f"{k['t_hac']:.2f}")
    c3.metric("IC-IR (mean/std)", f"{k['ir']:+.2f}")
    c4.metric("hit-rate (IC>0)", f"{k['hit_rate']:.0%}")
    st.caption(f"n={k['n']} months · monthly HAC SE ≈ {k['ci_half']/1.959963985:.4f} "
               f"· ci_half (95%) {k['ci_half']:.4f}")
