"""Aionis research dashboard — quant-evaluation interface over real frozen runs.

Six analytical dimensions (the owner judges: 拟合质量/波动结构/曲线演化/事件前后
差异/不确定性), rendering whatever artifacts the selected runs/ result dir
persisted (real frozen confirmatory results; no rerun-to-significance):

  1. Overview        — the headline (4 confirmatory claims → 4 nulls).
  2. Fit Quality     — cumulative IC + KPI (mean / NW-t / IC-IR / hit-rate) +
                       (score-vs-return scatter + quantile spread when the OOS
                        panel is persisted).
  3. Volatility      — IC histogram + rolling-12m IC-vol + underwater drawdown.
  4. Curve Evolution — cumulative IC with random-walk CI band + rolling IC/IC-IR.
  5. Event Study     — CAR around 13D / earnings / macro (when event_study lands).
  6. Uncertainty     — ci_half vs the 0.015 publishability gate + differential
                       forest plot + H6/controls/haircut.
  + Coverage + Strategy Return + Forward IC + Run history (retained).

Launch::

    uv run streamlit run dashboard/app.py

Reuses Streamlit (Apache-2.0) + plotly (MIT) + ``aionis.reporting.results`` +
``aionis.eval.rank_ic`` (NW-HAC). Charts degrade gracefully to a labeled
synthetic demo when no real result dir exists, and to a "data not persisted"
notice for charts that need artifacts the older runs lack.

View functions and helpers live in the dashboard/views/ submodule (backward
compatibility with existing test imports is preserved via re-exports).
"""
from __future__ import annotations

import sys
from pathlib import Path

# `streamlit run dashboard/app.py` puts the SCRIPT's folder (dashboard/) on
# sys.path, not the repo root — so the absolute `dashboard.views.*` imports
# below only resolve under pytest (which imports from the root). Bootstrap the
# repo root so the documented launch command works as written.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

from aionis.reporting import results as R

# Re-export chart helpers that tests import
from dashboard.views.charts import (
    _cumulative_ic_chart,
    _ic_histogram,
    _rolling_ic_chart,
)
from dashboard.views.coverage import view_coverage

# Re-export demo run generator that tests import
# Import data loading functions for main()
from dashboard.views.data_loading import (
    _coverage,
    _latest_strategy_return,
    _list_forward_runs,
    _list_runs,
    _load_forward_run,
    _load_run,
    _load_run_meta,
    _ls_returns,
    _pick_run,
    _synthetic_run,
)

# Re-export event study helpers that tests import
# Re-export all view functions
from dashboard.views.event import (
    _car_ci,
    _car_curve,
    _demo_event_windows,
    view_event_study,
)
from dashboard.views.fit import view_fit_quality

# Re-export forward helpers that tests import
from dashboard.views.forward import (
    _committed_vs_revealed,
    _forward_kpi,
    _parity_progress,
    view_forward_ic,
)

# Re-export all helpers for backward compatibility with tests
from dashboard.views.helpers import (
    _calmar,
    _downside_deviation,
    _ic_by_regime,
    _monthly_heatmap,
    _r2,
    _regression_line_coords,
    _return_distribution,
    _sharpe,
    _top_drawdowns,
    _vol_of_vol,
)
from dashboard.views.history import view_run_history
from dashboard.views.horizon import view_horizon_robustness
from dashboard.views.overview import view_overview
from dashboard.views.strategy import view_strategy_return

# Re-export uncertainty helpers that tests import
from dashboard.views.uncertainty import (
    _cv_fold_box,
    _demo_fold_ics,
    view_uncertainty,
)
from dashboard.views.volatility import view_evolution, view_volatility

__all__ = [
    "_calmar",
    "_car_ci",
    "_car_curve",
    "_committed_vs_revealed",
    "_coverage",
    "_cumulative_ic_chart",
    "_cv_fold_box",
    "_demo_event_windows",
    "_demo_fold_ics",
    "_downside_deviation",
    "_forward_kpi",
    "_ic_by_regime",
    "_ic_histogram",
    "_latest_strategy_return",
    "_list_forward_runs",
    "_list_runs",
    "_load_forward_run",
    "_load_run",
    "_load_run_meta",
    "_ls_returns",
    "_monthly_heatmap",
    "_parity_progress",
    "_pick_run",
    "_r2",
    "_regression_line_coords",
    "_return_distribution",
    "_rolling_ic_chart",
    "_sharpe",
    "_synthetic_run",
    "_top_drawdowns",
    "_vol_of_vol",
    "main",
    "view_coverage",
    "view_event_study",
    "view_fit_quality",
    "view_forward_ic",
    "view_horizon_robustness",
    "view_overview",
    "view_run_history",
    "view_strategy_return",
    "view_uncertainty",
    "view_evolution",
    "view_volatility",
]


def main() -> None:
    st.set_page_config(page_title="Aionis", page_icon="📊", layout="wide")
    st.title("Aionis — Research Dashboard")
    st.caption("Quant-evaluation over runs/ frozen artifacts · 6 dimensions "
               "(fit / volatility / evolution / event-study / uncertainty / "
               "horizon) · synthetic demo only when no result dir exists.")

    runs = _list_runs()
    options = [r["config_sig"] for r in runs] if runs else []
    meta_runs = [m for s in options if (m := _load_run_meta(s))]  # JSON-only, multi-run views
    with st.sidebar:
        st.header("Run")
        if options:
            chosen = st.selectbox("result dir (phase)", options, index=0)
            run, is_syn = _load_run(chosen), False
        else:
            st.warning("No result dirs — synthetic demo.")
            run, is_syn = _pick_run()
        st.divider()
        st.caption(f"results root: `{R.results_dir()}`")
        st.caption(f"runs scanned: {len(runs)}")

    tabs = st.tabs(["Overview", "Fit Quality", "Volatility", "Curve Evolution",
                    "Event Study", "Uncertainty", "Horizon Robustness", "Coverage",
                    "Strategy Return", "Forward IC", "Run history"])
    (t_over, t_fit, t_vol, t_evol, t_ev, t_unc, t_hr, t_cov, t_sr, t_fwd, t_hist) = tabs
    with t_over:
        view_overview(meta_runs)
    with t_fit:
        view_fit_quality(run, is_syn)
    with t_vol:
        view_volatility(run)
    with t_evol:
        view_evolution(run)
    with t_ev:
        view_event_study(run, is_syn)
    with t_unc:
        view_uncertainty(meta_runs, run)
    with t_hr:
        view_horizon_robustness(meta_runs)
    with t_cov:
        view_coverage()
    with t_sr:
        view_strategy_return()
    with t_fwd:
        # Forward-run selector
        forward_runs = _list_forward_runs()
        forward_options = [fr["config_sig"] for fr in forward_runs] if forward_runs else []
        if forward_options:
            chosen_forward = st.selectbox("forward run (E3)", forward_options, index=0)
            forward_run = _load_forward_run(chosen_forward)
            # Extract config_sha256 for committed-vs-revealed counts
            config_sha256 = forward_run.get("config", {}).get("config_sha256", chosen_forward)
            view_forward_ic(forward_run, config_sha256=config_sha256, runs_dir=R.DEFAULT_RUNS_DIR)
        else:
            st.info("No forward runs yet — accumulate via scripts/forward_score.py.")
    with t_hist:
        view_run_history()


if __name__ == "__main__":  # pragma: no cover — Streamlit entrypoint
    main()
