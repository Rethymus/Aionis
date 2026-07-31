"""Overview view — headline table + forest plot."""
from __future__ import annotations

import streamlit as st

from dashboard.views.charts import _ci_half_bar, _differential_forest, _headline_table


def view_overview(runs: list[dict]) -> None:
    st.subheader("Headline — confirmatory findings")
    st.caption("Each phase = one pre-registered two-tailed claim on cross-sectional monthly "
               "rank-IC (treatment vs fundamentals-only base). Verdict: NULL SUPPORTED when "
               "the differential CI brackets 0.")
    _headline_table_impl(runs)
    st.markdown("**Differential forest plot** — mean ± 95% CI per phase (CI brackets 0 ⇒ NULL)")
    if runs:
        st.plotly_chart(_differential_forest(runs), use_container_width=True)
        st.markdown("**CI precision per phase** — green = publishable-as-null (ci_half < 0.015)")
        st.plotly_chart(_ci_half_bar(runs), use_container_width=True)


def _headline_table_impl(runs: list[dict]) -> None:
    """Overview: the per-phase verdict table (the falsifiable findings)."""
    df = _headline_table(runs)
    if df.empty:
        st.info("No real result dirs yet — synthetic demo only.")
        return
    show = df.drop(columns=["_ci_lo", "_ci_hi"])
    st.dataframe(show.style.format({k: "{:+.4f}" for k in
                                    ["treat mean IC", "base mean IC", "differential",
                                     "ci_half"]} | {"DM-p": "{:.3f}"}),
                 use_container_width=True, hide_index=True)
    n_pub = int(df["publishable"].sum())
    # NULL = the differential 95% CI brackets 0 (the project's actual criterion),
    # NOT |mean_diff| < 0.015 (that's the precision gate on ci_half).
    n_null = int(((df["_ci_lo"] <= 0) & (df["_ci_hi"] >= 0)).sum())
    st.caption(f"{len(df)} confirmatory claims · "
               f"{n_null}/{len(df)} NULL (95% CI brackets 0) · "
               f"{n_pub}/{len(df)} publishable (ci_half < 0.015) · "
               f"all H6 deterministic: {bool(df['H6'].all())}")
