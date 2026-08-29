"""Forward IC view — exploratory E3 forward predictions."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from aionis.reporting.forward_ledger import EVENT_COMMIT, EVENT_SCORED, read_forward_rows

# Constants
PUBLISHABILITY_GATE = 0.015  # pre-reg §7: 95% CI half-width < 0.015 to "publish a null"


def view_forward_ic(
    forward_run: dict,
    *,
    config_sha256: str | None = None,
    runs_dir: Path | str | None = None,
) -> None:
    """Forward IC tab view — EXPLORATORY banner, KPIs, parity progress,
    committed-vs-revealed, cumulative IC chart."""
    st.subheader("Forward IC — Exploratory (E3)")

    # EXPLORATORY banner
    st.warning(
        "EXPLORATORY — forward IC; not a confirmatory signal until the calendar gate "
        "(pre-reg §7). The accumulated forward differential IC is shown for transparency, "
        "but statistical conclusions require the full 60–120 month horizon."
    )

    # Extract config_sha256 from the forward_run if not provided
    if config_sha256 is None:
        config_sha256 = forward_run.get("config", {}).get("config_sha256", "unknown")

    # KPI columns
    summary = forward_run.get("summary", {})
    kpi = _forward_kpi(summary)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("mean diff IC", f"{kpi['mean_ic']:+.4f}")
    c2.metric("CI half-width", f"{kpi['ci_half']:.4f}")
    c3.metric("n months", f"{kpi['n_months']}")
    c4.metric("DM p-value (MBB)", f"{kpi['dm_p_mbb']:.3f}")
    st.caption(
        f"Precision gate (ci_half < {PUBLISHABILITY_GATE}): {kpi['publishable']} · "
        f"DM t-stat: {kpi['t_hac']:.2f}"
    )

    # Parity progress
    n_months = kpi["n_months"]
    parity = _parity_progress(n_months)
    st.subheader("Months-to-Parity Progress")
    st.caption(
        f"{n_months} months accumulated · Parity range: {parity['lo']}–{parity['hi']} months "
        f"(pre-reg §7) · At lower parity gate: {parity['at_parity']}"
    )
    if parity["at_parity"]:
        st.success(f"✓ Reached lower parity gate ({parity['lo']} months)")
    else:
        st.info(f"⏳ {parity['lo'] - n_months} months to lower parity gate")
    # Progress bar (0 to 2x the lower gate)
    prog_frac = min(parity["frac_lo"] * 2, 1.0)  # Cap at 100%
    st.progress(prog_frac)
    st.caption(
        f"Progress to {parity['lo']} months: {parity['frac_lo']:.1%} · "
        f"to {parity['hi']} months: {parity['frac_hi']:.1%}"
    )

    # Committed vs revealed
    st.subheader("Committed vs Revealed Predictions")
    counts = _committed_vs_revealed(config_sha256=config_sha256, runs_dir=runs_dir)
    c1, c2, c3 = st.columns(3)
    c1.metric("Committed", f"{counts['committed']}")
    c2.metric("Revealed", f"{counts['revealed']}")
    c3.metric("Pending", f"{counts['pending']}")
    st.caption("Pending = committed but not yet revealed (waiting for target_t wall-clock)")

    # Cumulative forward IC chart
    from dashboard.views.charts import _cumulative_ic_chart

    ic_forward = forward_run.get("ic_forward")
    if ic_forward is not None and len(ic_forward) > 0:
        monthly_se = summary.get("se_hac", 0.0)
        st.plotly_chart(
            _cumulative_ic_chart(ic_forward, "forward differential IC", monthly_se=monthly_se),
            use_container_width=True,
            key="fwd-cum-ic",
        )
    else:
        st.info("No forward IC data yet (accumulate via scripts/forward_score.py).")


def _forward_kpi(summary_forward: dict) -> dict:
    """Extract KPI fields from a summary_forward dict (pure helper, testable without streamlit)."""
    return {
        "mean_ic": summary_forward.get("mean_diff", float("nan")),
        "ci_half": summary_forward.get("ci_half", float("nan")),
        "t_hac": summary_forward.get("dm_stat", float("nan")),
        "dm_p_mbb": summary_forward.get("dm_p_mbb", float("nan")),
        "n_months": summary_forward.get("n_months", 0),
        "publishable": summary_forward.get("ci_half", 1.0) < PUBLISHABILITY_GATE,
    }


def _parity_progress(n_months: int) -> dict:
    """Compute progress toward the 60–120 month parity range (pre-reg §7)."""
    lo = 60
    hi = 120
    return {
        "n_months": n_months,
        "lo": lo,
        "hi": hi,
        "frac_lo": n_months / lo if lo > 0 else float("nan"),
        "frac_hi": n_months / hi if hi > 0 else float("nan"),
        "at_parity": n_months >= lo,
    }


def _committed_vs_revealed(*, config_sha256: str, runs_dir: Path | str | None = None) -> dict:
    """Count committed vs revealed forward predictions for a config (pure helper)."""
    rows = read_forward_rows(runs_dir=runs_dir, config_sha256=config_sha256)
    committed = len([r for r in rows if r.get("event") == EVENT_COMMIT])
    revealed = len([r for r in rows if r.get("event") == EVENT_SCORED])
    return {
        "committed": committed,
        "revealed": revealed,
        "pending": committed - revealed,
    }
