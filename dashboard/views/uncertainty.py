"""Uncertainty view — differential forest + CV-fold stability."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.theme import apply_theme
from dashboard.views.charts import _ci_half_bar, _differential_forest


def view_uncertainty(runs: list[dict], run: dict) -> None:
    """Uncertainty: differential forest + CI precision + CV-fold stability."""
    st.subheader("Uncertainty")
    st.markdown("**Differential forest plot** (all phases) — CI brackets 0 ⇒ NULL")
    if runs:
        st.plotly_chart(_differential_forest(runs), use_container_width=True, key="unc-forest")
        st.plotly_chart(_ci_half_bar(runs), use_container_width=True, key="unc-cihalf")

    st.markdown(f"**Selected run** `{run['config_sig'][:12]}…` · H6 deterministic: "
                f"{run.get('h6_deterministic')}")
    diff = run["differential"]
    c1, c2, c3 = st.columns(3)
    c1.metric("differential mean", f"{diff.get('mean_diff', float('nan')):+.4f}")
    c2.metric("95% CI", f"[{diff.get('ci_lo', float('nan')):+.4f}, "
              f"{diff.get('ci_hi', float('nan')):+.4f}]")
    c3.metric("DM-p (MBB)", f"{diff.get('dm_p_mbb', float('nan')):.3f}")
    ctrls = run.get("controls", {})
    pl = ctrls.get("bundle_shuffle_placebo", {})
    if pl:
        st.caption(f"bundle-shuffle placebo: mean {pl.get('mean_diff', 0):+.4f} "
                   f"(DM-p {pl.get('dm_p_mbb', 0):.3f}) — must vanish if the signal is real.")

    # CV-fold stability section (demo-capable)
    st.markdown("**CV-fold stability** (per-arm IC distribution across folds)")
    fold_data = run.get("fold_ics")  # Real path: persist fold ICs in run artifact
    if fold_data is None or not isinstance(fold_data, pd.DataFrame) or fold_data.empty:
        # Demo path
        st.warning(
            "DEMO: synthetic data — illustrates method/interaction, "
            "not a research conclusion."
        )
        demo_folds = _demo_fold_ics(n_folds=5, n_repeats=3, rng=None)  # Uses default rng=7
        st.plotly_chart(_cv_fold_box(demo_folds), use_container_width=True, key="unc-cvfold-demo")
        st.caption("Demo: synthetic fold ICs (rng=7) illustrate CV stability visualization. "
                   "Real CV-fold data requires fold-level IC persistence in run artifacts.")
    else:
        st.plotly_chart(_cv_fold_box(fold_data), use_container_width=True, key="unc-cvfold-real")
        n_folds = fold_data["fold"].nunique()
        st.caption(f"CV stability across {n_folds} folds — IC spread by arm.")

    st.caption("Multiple-testing deflation (DSR / haircut across the strategy family) is in "
               "the **Strategy Return** tab.")


def _cv_fold_box(fold_ics: pd.DataFrame) -> go.Figure:
    """Box plot of per-fold IC values (CV stability visualization).

    Args:
        fold_ics: DataFrame with columns [fold, repeat, arm, ic].

    Returns:
        Plotly Figure with box traces per arm.
    """
    fig = go.Figure()

    for arm in fold_ics["arm"].unique():
        arm_data = fold_ics[fold_ics["arm"] == arm]["ic"]
        fig.add_trace(go.Box(
            x=arm_data.values,
            name=arm,
            boxpoints="outliers",
        ))

    fig.add_vline(x=0, line_dash="dot", line_color="grey")
    fig.update_layout(
        xaxis_title="cross-sectional rank-IC",
        yaxis_title="arm",
        height=320,
        margin=dict(l=10, r=10, t=20, b=10),
        title="CV-fold stability (per-arm IC distribution across folds)",
        showlegend=False,
    )
    fig = apply_theme(fig)
    return fig


def _demo_fold_ics(
    n_folds: int = 5,
    n_repeats: int = 3,
    rng: np.random.Generator | None = None,
) -> pd.DataFrame:
    """Generate reproducible demo CV-fold IC data for uncertainty visualization.

    Args:
        n_folds: Number of CV folds.
        n_repeats: Number of repeats per fold.
        rng: Random number generator (if None, uses seeded default_rng(7) for reproducibility).

    Returns:
        DataFrame with columns [fold, repeat, arm, ic].
    """
    if rng is None:
        rng = np.random.default_rng(7)  # Fixed seed for reproducible demo

    rows = []
    arms = ["treatment", "base"]

    for fold in range(1, n_folds + 1):
        for repeat in range(1, n_repeats + 1):
            for arm in arms:
                # Demo: treatment has slightly higher mean IC than base
                if arm == "treatment":
                    ic = rng.normal(0.05, 0.02)  # Mean 0.05, vol 0.02
                else:
                    ic = rng.normal(0.03, 0.02)  # Mean 0.03, vol 0.02
                rows.append({
                    "fold": fold,
                    "repeat": repeat,
                    "arm": arm,
                    "ic": ic,
                })

    return pd.DataFrame(rows)
