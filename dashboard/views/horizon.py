"""Horizon Robustness view — h=10/21/42 sensitivity."""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from dashboard.views.data_loading import _ledger_rows, _phase_of


def view_horizon_robustness(runs: list[dict]) -> None:
    st.subheader("Horizon Robustness")
    st.caption("The 3 confirmatory nulls re-tested at h=10 and h=42 (h=21 is the frozen "
               "confirmatory horizon). All differentials stay ≈0 with CI bracketing 0 ⇒ "
               "the nulls are horizon-robust, strengthening the publishable-as-null result.")
    sweep = _horizon_sweep()
    if not sweep:
        st.info("No horizon-sensitivity sweep yet (run scripts/sensitivity_horizon.py).")
        return
    st.plotly_chart(_horizon_robustness_chart(runs, sweep), use_container_width=True)
    sw = sweep.get("results", {})
    n_cells = sum(
        1 for h in ("10", "42") for ph in ("B", "C", "D")
        if sw.get(h, {}).get(ph, {}).get("null_holds")
    )
    st.caption(f"{n_cells}/6 exploratory cells hold NULL (CI brackets 0); plus the 3 frozen "
               f"h=21 confirmatory nulls.")


@st.cache_data(show_spinner=False)
def _horizon_sweep() -> dict | None:
    """The latest exploratory sensitivity_horizon ledger row (B/C/D at h=10, 42)."""
    rows = [r for r in _ledger_rows() if r.get("phase") == "sensitivity_horizon"]
    return max(rows, key=lambda r: r.get("ts", "")) if rows else None


def _horizon_robustness_chart(runs: list[dict], sweep: dict) -> go.Figure:
    """B/C/D differential (mean ± 95% CI) across h=10/21/42 — all NULL-robust.
    h=21 from the confirmatory runs; h=10/42 from the exploratory sweep."""
    h21 = {}
    for r in runs:
        p, _ = _phase_of(r)
        d = r["differential"]
        h21[p] = (d.get("mean_diff", float("nan")),
                  d.get("ci_lo", float("nan")), d.get("ci_hi", float("nan")))
    phases = ["B", "C", "D"]
    horizons = [10, 21, 42]
    sw = (sweep or {}).get("results", {})
    fig = go.Figure()
    for ph in phases:
        ys, lo_err, hi_err = [], [], []
        for h in horizons:
            if h == 21:
                m, lo, hi = h21.get(ph, (float("nan"),) * 3)
            else:
                e = sw.get(str(h), {}).get(ph, {})
                m = e.get("mean_diff", float("nan"))
                lo = e.get("ci_lo", float("nan"))
                hi = e.get("ci_hi", float("nan"))
            ys.append(m)
            lo_err.append(m - lo if np.isfinite(m) and np.isfinite(lo) else 0)
            hi_err.append(hi - m if np.isfinite(m) and np.isfinite(hi) else 0)
        fig.add_trace(go.Scatter(
            x=horizons, y=ys, mode="lines+markers", name=f"phase {ph}",
            error_y={"type": "data", "array": hi_err, "arrayminus": lo_err, "thickness": 1}))
    fig.add_hline(y=0, line_dash="dot", line_color="grey")
    fig.update_layout(xaxis_title="horizon (sessions)",
                      yaxis_title="differential (treatment − base) rank-IC",
                      height=380, legend=dict(orientation="h", y=-0.2),
                      margin=dict(l=10, r=10, t=45, b=10),
                      title="horizon robustness — B/C/D across h=10/21/42 "
                            "(CI brackets 0 ⇒ NULL)")
    return fig
