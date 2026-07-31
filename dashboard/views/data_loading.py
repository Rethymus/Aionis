"""Data loading functions — cached streamlit data loaders.

These are the @st.cache_data functions that load run data.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from aionis.eval.rank_ic import rank_ic_summary
from aionis.reporting import results as R
from aionis.reporting.forward_results import list_forward_runs as list_forward_runs_impl
from aionis.reporting.forward_results import load_forward_run as load_forward_run_impl

# Coverage constants (pre-reg §3/§8; realized outcomes ledger #23/#25). Fallbacks.
_COV_TOTAL = 705
_COV_CLEAN = 588
_JACCARD_MEAN = 0.9272
_DROPPED_REUSE = ("POM", "SE", "STI")

# sig -> (phase, treatment-arm label) for the dimension views
_TREATMENT_LABEL = {
    "17245a75": ("B", "arm_state (filed)"),
    "a7fdb48f": ("C", "arm_macro (bundle)"),
    "d3158063": ("D", "arm_rel (relationship)"),
    "ef321e9e": ("E1", "arm_prop (propagation)"),
}


@st.cache_data(show_spinner=False)
def _list_runs() -> list[dict]:
    return R.list_runs()


@st.cache_data(show_spinner=False)
def _load_run(config_sig: str) -> dict:
    return R.load_run(config_sig)


@st.cache_data(show_spinner=False)
def _load_run_meta(config_sig: str) -> dict:
    """Lightweight run (JSON only — no IC/OOS parquet) for the multi-run views
    (Overview / Uncertainty / Horizon). Loading 4 full runs (each ~1.2M-row OOS
    panel) would be heavy + memory-hostile; the multi-run views only need the
    differential / summaries / controls / config, all small JSONs."""
    d = R.run_dir(config_sig)
    if not (d / "meta.json").exists():
        return None  # type: ignore[return-value]
    meta = R._read_json(d / "meta.json")
    return {
        "config_sig": config_sig,
        "ts": meta.get("ts"),
        "h6_deterministic": bool(meta.get("h6_deterministic", False)),
        "differential": R._read_json(d / "differential.json"),
        "summary_state": R._read_json(d / "summary_state.json"),
        "summary_base": R._read_json(d / "summary_base.json"),
        "controls": R._read_json(d / "controls.json"),
        "config": R._read_json(d / "config.json"),
    }


@st.cache_data(show_spinner=False)
def _ledger_rows() -> list[dict]:
    return R.read_ledger()


@st.cache_data(show_spinner=False)
def _coverage() -> dict:
    return {"total": _COV_TOTAL, "clean": _COV_CLEAN, "jaccard": _JACCARD_MEAN,
            "dropped": _DROPPED_REUSE}


@st.cache_data(show_spinner=False)
def _latest_strategy_return() -> dict | None:
    rows = [r for r in _ledger_rows() if r.get("phase") == "strategy_return"]
    if not rows:
        return None
    return max(rows, key=lambda r: r.get("ts", ""))


@st.cache_data(show_spinner=False)
def _ls_returns() -> pd.DataFrame | None:
    """The monthly long-short returns wide frame written by
    ``scripts/strategy_eval_run.py`` (``runs/strategy_returns.parquet``):
    month-end ``DatetimeIndex`` (name ``date``), one column per strategy
    (``B_arm_state``, ``arm_base``, ``C_arm_macro``, ``C_placebo``,
    ``C_sanity``), values = monthly L-S return. Returns ``None`` when the
    artifact is absent so the view can degrade to a graceful notice."""
    path = R.results_dir().parent / "strategy_returns.parquet"
    if not path.exists():
        return None
    return pd.read_parquet(path)


@st.cache_data(show_spinner=False)
def _list_forward_runs() -> list[dict]:
    """Scan runs/forward/ for E3 forward artifacts (I9: never touches results/)."""
    return list_forward_runs_impl()


@st.cache_data(show_spinner=False)
def _load_forward_run(config_sig: str) -> dict:
    """Load a forward run from runs/forward/<config_sig>/ (I9: never touches results/)."""
    return load_forward_run_impl(config_sig)


@st.cache_data(show_spinner=False)
def _prices() -> pd.DataFrame:
    """The daily price panel (event-study CAR + benchmark)."""
    from aionis.config import settings
    return pd.read_parquet(settings.data_dir / "cache" / "phase_b_prices.parquet")


@st.cache_data(show_spinner=False)
def _car_summary(prices: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """Cached CAR compute (events × iterrows is ~seconds; cache by data hash)."""
    from aionis.eval.event_study import cumulative_abnormal_return
    summary, _ = cumulative_abnormal_return(prices, events, k_before=10, k_after=20)
    return summary


def _synthetic_run() -> dict:
    """Demo run when no real result dir exists yet (dashboard is demoable first)."""
    import numpy as np

    rng = np.random.default_rng(7)
    months = pd.date_range("2017-01-31", periods=125, freq="ME")
    ic_s = pd.Series(rng.normal(0.014, 0.05, 125), index=months, name="ic")
    ic_s.index.name = "date"
    ic_b = pd.Series(rng.normal(0.015, 0.05, 125), index=months, name="ic")
    ic_b.index.name = "date"
    return {
        "config_sig": "demo_synthetic", "ts": None, "h6_deterministic": True,
        "ic_state": ic_s, "ic_base": ic_b,
        "summary_state": rank_ic_summary(ic_s), "summary_base": rank_ic_summary(ic_b),
        "differential": {"n_months": 125, "mean_diff": -0.001, "se_hac": 0.005,
                         "ci_half": 0.010, "ci_lo": -0.011, "ci_hi": 0.009,
                         "dm_p_mbb": 0.84, "publishable_ci_half": True},
        "controls": {"bundle_shuffle_placebo": {"mean_diff": 0.0, "dm_p_mbb": 0.9}},
        "config": {"phase": "demo"},
        "oos_state": None, "oos_base": None,
    }


def _pick_run() -> tuple[dict, bool]:
    runs = _list_runs()
    if runs:
        return _load_run(runs[0]["config_sig"]), False
    return _synthetic_run(), True


def _phase_of(run: dict) -> tuple[str, str]:
    sig = run.get("config_sig", "")
    for prefix, lab in _TREATMENT_LABEL.items():
        if sig.startswith(prefix):
            return lab
    cfg_phase = run.get("config", {}).get("phase", "?")
    return (cfg_phase.upper(), "treatment")
