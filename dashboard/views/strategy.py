"""Strategy return view — secondary/exploratory lens."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.views.charts import _equity_curve_chart
from dashboard.views.data_loading import _latest_strategy_return, _ls_returns


def view_strategy_return() -> None:
    st.subheader("Strategy Return (secondary/exploratory lens)")
    row = _latest_strategy_return()
    if not row:
        st.info("No strategy-return eval run yet.")
        return
    strategies = row.get("strategies", {})
    if not strategies:
        st.warning("strategy_return row has no strategies.")
        return
    st.caption(f"ts {row.get('ts', '')[:19]} · benchmark {row.get('benchmark')} · "
               f"n_trials_grid {row.get('n_trials_grid')}")
    # per-strategy Sharpe + DSR grid table
    grid = row.get("n_trials_grid", [1, 2, 5, 20])
    bench = row.get("benchmark", "")
    recs = []
    for name, m in strategies.items():
        dbt = m.get("dsr_by_trials", {})
        rec = {"strategy": name, "sharpe_ann": m.get("sharpe_annualized"),
               "dsr_p_conservative": m.get("dsr_p_conservative"),
               "n_months": m.get("n_months")}
        for nt in grid:
            rec[f"p@n{nt}"] = (dbt.get(nt) or {}).get("p_value") if dbt else None
        recs.append(rec)
    df = pd.DataFrame(recs)
    # Ledger rows legitimately carry None cells (e.g. a strategy without the
    # DSR grid); .style.format spec strings can't format None — guard per cell.
    def _num(spec: str):
        def f(v):
            if v is None or (isinstance(v, float) and pd.isna(v)):
                return "—"
            return format(v, spec)
        return f

    fmt = {"sharpe_ann": _num("+.3f"), "dsr_p_conservative": _num(".3f")}
    for nt in grid:
        fmt[f"p@n{nt}"] = _num(".3f")
    st.dataframe(df.style.format({k: v for k, v in fmt.items() if k in df.columns}),
                 use_container_width=True, hide_index=True)
    spa = row.get("spa", {})
    if isinstance(spa, dict) and "consistent_pvalue" in spa:
        st.caption(f"Hansen-SPA consistent_p = {spa['consistent_pvalue']:.3f} "
                   f"(H0: nothing beats {bench}). "
                   f"MCS includes all → statistically indistinguishable.")
    st.caption("No L-S Sharpe survives the project-family DSR deflation; the placebo at "
               "n=1 ≈ 0.057 is the under-deflation cautionary tale.")

    # curve evolution — the tradeable cumulative L-S equity curve per strategy
    ls_wide = _ls_returns()
    st.markdown("**Cumulative long-short equity curve** — strategy curve evolution")
    if ls_wide is None or ls_wide.empty:
        st.info("Equity curve needs ``runs/strategy_returns.parquet`` "
                "(written by ``scripts/strategy_eval_run.py``); not found.")
    else:
        st.plotly_chart(_equity_curve_chart(ls_wide),
                       use_container_width=True, key="strategy-equity")
        st.caption("Cumulative sum of each strategy's monthly long-short return "
                   "(secondary/exploratory lens; gross-of-costs). Dashed grey = "
                   f"{row.get('benchmark', 'arm_base')} benchmark. The rank-IC "
                   "differentials remain the confirmatory claims.")
