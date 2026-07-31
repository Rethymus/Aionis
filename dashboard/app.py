"""Aionis research dashboard v2 — near-final quant-evaluation interface.

Five analytical dimensions (the owner judges: 拟合质量/波动结构/曲线演化/事件前后
差异/不确定性), where the current data only DEMONSTRATES the analysis methods +
interaction structure (not final conclusions):

  1. Overview        — the headline (4 confirmatory claims → 4 publishable nulls).
  2. Fit Quality     — cumulative IC + KPI (mean / NW-t / IC-IR / hit-rate) +
                       (score-vs-return scatter + quantile spread when the OOS
                        panel is persisted).
  3. Volatility      — IC histogram + rolling-12m IC-vol + underwater drawdown.
  4. Curve Evolution — cumulative IC with random-walk CI band + rolling IC/IC-IR.
  5. Event Study     — CAR around 13D / earnings / macro (when event_study lands).
  6. Uncertainty     — ci_half vs the 0.015 publishability gate + differential
                       forest plot + H6/controls/haircut.
  + Coverage + Strategy Return (retained).

Launch::

    uv run streamlit run dashboard/app.py

Reuses Streamlit (Apache-2.0) + plotly (MIT) + ``aionis.reporting.results`` +
``aionis.eval.rank_ic`` (NW-HAC). Charts degrade gracefully to a synthetic demo
when no real result dir exists, and to a "data not persisted" notice for charts
that need artifacts the older runs lack.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from aionis.eval.rank_ic import rank_ic_summary
from aionis.reporting import results as R
from aionis.reporting.forward_ledger import EVENT_COMMIT, EVENT_SCORED, read_forward_rows
from aionis.reporting.forward_results import list_forward_runs as list_forward_runs_impl
from aionis.reporting.forward_results import load_forward_run as load_forward_run_impl

PUBLISHABILITY_GATE = 0.015  # pre-reg §7: 95% CI half-width < 0.015 to "publish a null"
Z95 = 1.959963985

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


# ----------------------------------------------------------------------------
# data loading (cached)
# ----------------------------------------------------------------------------


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


def _synthetic_run() -> dict:
    """Demo run when no real result dir exists yet (dashboard is demoable first)."""
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


# ----------------------------------------------------------------------------
# analytics (computed from the monthly IC series) — the dimension metrics
# ----------------------------------------------------------------------------


def _ic_kpi(ic: pd.Series) -> dict:
    """Fit-quality KPIs from a monthly rank-IC series."""
    s = ic.dropna()
    n = int(len(s))
    if n < 2:
        return {"mean": float("nan"), "std": float("nan"), "ir": float("nan"),
                "hit_rate": float("nan"), "n": n, "t_hac": float("nan"),
                "ci_half": float("nan")}
    sd = float(s.std(ddof=1))
    summ = rank_ic_summary(s)
    return {
        "mean": float(s.mean()), "std": sd,
        "ir": float(s.mean() / sd) if sd > 0 else float("nan"),
        "hit_rate": float((s > 0).mean()),
        "n": n, "t_hac": float(summ["t_hac"]), "ci_half": float(summ["ci_half"]),
    }


def _cumulative_ic(ic: pd.Series) -> pd.Series:
    return ic.dropna().cumsum()


def _rolling_ic(ic: pd.Series, window: int = 12) -> pd.DataFrame:
    s = ic.dropna()
    return pd.DataFrame({"mean": s.rolling(window, min_periods=max(6, window // 2)).mean(),
                         "std": s.rolling(window, min_periods=max(6, window // 2)).std(ddof=1)})


def _drawdown(cum_ic: pd.Series) -> pd.Series:
    """Underwater curve: cumulative IC minus its running max (≤ 0)."""
    return cum_ic - cum_ic.cummax()


def _cum_ic_ci_band(cum_ic: pd.Series, monthly_se: float) -> pd.DataFrame:
    """Random-walk no-skill band AROUND ZERO: ±Z95·monthly_se·√i. The cumulative IC
    is plotted against this band — exceeding it means the cumulative IC is
    distinguishable from a no-skill random walk (i.e. the arm has detectable, if
    small, predictive power); staying inside means indistinguishable from 0."""
    i = np.arange(1, len(cum_ic) + 1)
    half = Z95 * float(monthly_se) * np.sqrt(i)
    return pd.DataFrame({"lo": -half, "hi": +half}, index=cum_ic.index)


# ----------------------------------------------------------------------------
# chart builders
# ----------------------------------------------------------------------------


def _headline_table(runs: list[dict]) -> None:
    """Overview: the per-phase verdict table (the falsifiable findings)."""
    rows = []
    for r in runs:
        phase, treat = _phase_of(r)
        d = r["differential"]
        mean_diff = d.get("mean_diff", d.get("mean_ic_diff_state_minus_base", float("nan")))
        ci_lo = d.get("ci_lo", float("nan"))
        ci_hi = d.get("ci_hi", float("nan"))
        rows.append({
            "phase": phase, "claim (treatment)": treat,
            "treat mean IC": r["summary_state"].get("mean_ic", float("nan")),
            "base mean IC": r["summary_base"].get("mean_ic", float("nan")),
            "differential": mean_diff,
            "DM-p": d.get("dm_p_mbb", float("nan")),
            "ci_half": d.get("ci_half", float("nan")),
            "publishable": d.get("publishable_ci_half", False),
            "H6": r.get("h6_deterministic"),
            "_ci_lo": ci_lo, "_ci_hi": ci_hi,
        })
    df = pd.DataFrame(rows)
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


def _cumulative_ic_chart(ic: pd.Series, label: str, monthly_se: float) -> go.Figure:
    cum = _cumulative_ic(ic)
    band = _cum_ic_ci_band(cum, monthly_se)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=list(band.index), y=list(band["hi"]), name="95% CI",
                             mode="lines", line={"width": 0}, hoverinfo="skip",
                             showlegend=False))
    fig.add_trace(go.Scatter(x=list(band.index), y=list(band["lo"]), name="95% CI",
                             mode="lines", fill="tonexty",
                             fillcolor="rgba(100,150,255,0.15)", line={"width": 0},
                             hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=list(cum.index), y=list(cum.values), name=f"cum IC ({label})",
                             mode="lines", line={"color": "#1f77b4"}))
    fig.add_hline(y=0, line_dash="dot", line_color="grey")
    fig.update_layout(xaxis_title="month", yaxis_title="cumulative rank-IC",
                      height=380, legend=dict(orientation="h", y=-0.2),
                      margin=dict(l=10, r=10, t=20, b=10),
                      title="cumulative IC vs random-walk 95% band "
                            "(stays in band ⇒ indistinguishable from no-skill)")
    return fig


def _kpi_row(ic: pd.Series, label: str) -> None:
    k = _ic_kpi(ic)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"mean IC ({label})", f"{k['mean']:+.4f}")
    c2.metric("NW-HAC t", f"{k['t_hac']:.2f}")
    c3.metric("IC-IR (mean/std)", f"{k['ir']:+.2f}")
    c4.metric("hit-rate (IC>0)", f"{k['hit_rate']:.0%}")
    st.caption(f"n={k['n']} months · monthly HAC SE ≈ {k['ci_half']/Z95:.4f} "
               f"· ci_half (95%) {k['ci_half']:.4f}")


def _ic_histogram(ic: pd.Series) -> go.Figure:
    s = ic.dropna()
    fig = go.Figure(go.Histogram(x=s.values, nbinsx=25, marker_color="#9467bd"))
    fig.add_vline(x=0, line_dash="dot", line_color="grey")
    fig.add_vline(x=float(s.mean()), line_color="red", annotation_text=f"mean {s.mean():+.4f}")
    fig.update_layout(xaxis_title="monthly rank-IC", yaxis_title="months", height=320,
                      margin=dict(l=10, r=10, t=20, b=10),
                      title="IC distribution (spread ⇒ volatility structure)")
    return fig


def _rolling_ic_chart(ic: pd.Series, window: int = 12) -> go.Figure:
    r = _rolling_ic(ic, window)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=r.index, y=r["mean"], name=f"rolling-{window}m mean IC",
                             mode="lines", line={"color": "#1f77b4"}))
    fig.add_trace(go.Scatter(x=r.index, y=r["std"], name=f"rolling-{window}m IC vol",
                             mode="lines", line={"color": "#d62728"}, yaxis="y2"))
    fig.add_hline(y=0, line_dash="dot", line_color="grey", yref="y1")
    fig.update_layout(xaxis_title="month", yaxis_title="rolling mean IC",
                      yaxis2={"title": "rolling IC vol", "overlaying": "y", "side": "right"},
                      height=340, legend=dict(orientation="h", y=-0.2),
                      margin=dict(l=10, r=10, t=20, b=10),
                      title=f"rolling {window}-month IC + IC-vol (curve evolution)")
    return fig


def _drawdown_chart(cum_ic: pd.Series) -> go.Figure:
    dd = _drawdown(cum_ic)
    fig = go.Figure(go.Scatter(x=dd.index, y=dd.values, name="underwater (cum IC drawdown)",
                               mode="lines", fill="tozeroy", fillcolor="rgba(214,39,40,0.2)",
                               line={"color": "#d62728"}))
    fig.add_hline(y=0, line_color="grey")
    fig.update_layout(xaxis_title="month", yaxis_title="cumulative IC − running max",
                      height=320, margin=dict(l=10, r=10, t=20, b=10),
                      title="underwater curve (how far cumulative IC is below its peak)")
    return fig


def _ci_half_bar(runs: list[dict]) -> go.Figure:
    """Uncertainty: ci_half per phase vs the 0.015 publishability gate."""
    phases, cis = [], []
    for r in runs:
        p, _ = _phase_of(r)
        phases.append(p)
        cis.append(r["differential"].get("ci_half", float("nan")))
    fig = go.Figure(go.Bar(x=phases, y=cis, name="differential ci_half",
                           marker_color=["#2ca02c" if (c < PUBLISHABILITY_GATE) else "#d62728"
                                         for c in cis],
                           text=[f"{c:.4f}" for c in cis], textposition="outside"))
    fig.add_hline(y=PUBLISHABILITY_GATE, line_dash="dash", line_color="black",
                  annotation_text=f"publishability gate {PUBLISHABILITY_GATE}")
    fig.update_layout(xaxis_title="phase", yaxis_title="95% CI half-width",
                      height=340, margin=dict(l=10, r=10, t=20, b=10),
                      title="differential CI precision per phase (green = publishable-as-null)")
    return fig


def _differential_forest(runs: list[dict]) -> go.Figure:
    """Uncertainty: differential mean ± 95% CI per phase (forest plot)."""
    rows = []
    for r in runs:
        p, _ = _phase_of(r)
        d = r["differential"]
        rows.append((p, d.get("mean_diff", float("nan")),
                     d.get("ci_lo", float("nan")), d.get("ci_hi", float("nan"))))
    rows.sort(key=lambda x: x[0])
    fig = go.Figure()
    for p, m, lo, hi in rows:
        fig.add_trace(go.Scatter(x=[lo, hi], y=[p, p], mode="lines",
                                 line={"color": "#1f77b4"}, showlegend=False))
        fig.add_trace(go.Scatter(x=[m], y=[p], mode="markers",
                                 marker={"size": 12, "color": "#1f77b4"}, showlegend=False))
    fig.add_vline(x=0, line_dash="dot", line_color="grey")
    fig.update_layout(xaxis_title="differential (treatment − base) rank-IC, mean ± 95% CI",
                      yaxis_title="phase", height=320,
                      margin=dict(l=10, r=10, t=20, b=10),
                      title="differential forest plot (CI brackets 0 ⇒ NULL)")
    return fig


def _equity_curve_chart(ls_wide: pd.DataFrame) -> go.Figure:
    """Cumulative long-short equity curve: one ``cumsum`` line per strategy —
    the tradeable evolution of each arm's L-S spread. The benchmark
    (``arm_base``) is rendered dashed + grey so it reads as a reference
    line distinct from the treatment arms."""
    bench = "arm_base"
    fig = go.Figure()
    for col in ls_wide.columns:
        s = ls_wide[col].dropna()
        if s.empty:
            continue
        cum = s.cumsum()
        is_bench = str(col) == bench
        fig.add_trace(go.Scatter(
            x=cum.index, y=cum.values,
            name=f"{col} (benchmark)" if is_bench else str(col),
            mode="lines",
            line={"dash": "dash" if is_bench else "solid",
                  "color": "#7f7f7f" if is_bench else None},
        ))
    fig.add_hline(y=0, line_dash="dot", line_color="grey")
    fig.update_layout(
        xaxis_title="month", yaxis_title="cumulative L-S return",
        height=380, legend=dict(orientation="h", y=-0.2),
        margin=dict(l=10, r=10, t=40, b=10),
        title="cumulative long-short equity curve (strategy curve evolution)",
    )
    return fig


def _ic_chart(run: dict) -> go.Figure:
    ic_s, ic_b = run["ic_state"], run["ic_base"]
    _, treat = _phase_of(run)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ic_s.index, y=ic_s.values, name=treat, mode="lines"))
    fig.add_trace(go.Scatter(x=ic_b.index, y=ic_b.values, name="arm_base", mode="lines"))
    fig.add_hline(y=0, line_dash="dot", line_color="grey")
    fig.update_layout(xaxis_title="month", yaxis_title="cross-sectional rank-IC",
                      height=360, legend=dict(orientation="h", y=-0.2),
                      margin=dict(l=10, r=10, t=20, b=10))
    return fig


def _haircut_chart(run: dict) -> go.Figure:
    mt = run.get("multiple_testing_haircut") or {}
    if "arm_state" in mt or "arm_macro" in mt or "arm_rel" in mt or "arm_prop" in mt:
        arm = next(iter(mt.values()))  # any arm's grid
    else:
        return go.Figure()
    trials = sorted(int(t) for t in arm.keys()) if arm else []
    ys = [arm[t]["haircut_sharpe"] for t in trials]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=trials, y=ys, name="haircut IC-IR", mode="lines+markers"))
    fig.update_layout(xaxis_title="n_trials", yaxis_title="haircut Sharpe",
                      height=320, margin=dict(l=10, r=10, t=20, b=10))
    return fig


# ----------------------------------------------------------------------------
# OOS-panel + event-study charts (dashboard v2 enablers)
# ----------------------------------------------------------------------------


@st.cache_data(show_spinner=False)
def _prices() -> pd.DataFrame:
    """The daily price panel (event-study CAR + benchmark)."""
    from aionis.config import settings
    return pd.read_parquet(settings.data_dir / "cache" / "phase_b_prices.parquet")


def _score_vs_return_scatter(oos: pd.DataFrame) -> go.Figure:
    """Fit: score vs forward-return (subsampled) + the full-data Spearman rank-corr."""
    df = oos.dropna(subset=["score", "y_fwd_ret"])
    rho = df["score"].corr(df["y_fwd_ret"], method="spearman")
    n = len(df)
    sub = df.sample(min(10_000, n), random_state=0) if n else df
    fig = go.Figure(go.Scatter(x=sub["score"], y=sub["y_fwd_ret"], mode="markers",
                               marker={"size": 3, "opacity": 0.2, "color": "#1f77b4"},
                               showlegend=False))
    fig.add_hline(y=0, line_dash="dot", line_color="grey")
    fig.add_vline(x=0, line_dash="dot", line_color="grey")
    fig.update_layout(xaxis_title="OOS score", yaxis_title="forward return",
                      height=340, margin=dict(l=10, r=10, t=40, b=10),
                      title=f"score vs forward-return (Spearman {rho:+.4f}; n={n}; "
                            f"{len(sub)} plotted)")
    return fig


def _quantile_spread_chart(oos: pd.DataFrame) -> go.Figure:
    """Fit: mean forward-return per score decile (alphalens-style monotonicity check).
    Only dates that form exactly 10 clean deciles are pooled, so D1..D10 mean the
    same thing across dates (ties-collapse dates are dropped, not mis-binned)."""
    df = oos.dropna(subset=["score", "y_fwd_ret"]).copy()

    def _decile(s: pd.Series):
        try:
            return pd.qcut(s, 10, labels=False, duplicates="raise")
        except ValueError:
            return pd.Series(np.nan, index=s.index)  # <10 clean bins -> drop this date

    df["q"] = df.groupby("date")["score"].transform(_decile)
    df = df.dropna(subset=["q"])
    spread = df.groupby("q")["y_fwd_ret"].mean()
    labels = [f"D{int(q) + 1}" for q in spread.index]
    fig = go.Figure(go.Bar(x=labels, y=spread.values, marker_color="#2ca02c",
                           text=[f"{v:+.4f}" for v in spread.values], textposition="outside"))
    fig.add_hline(y=0, line_dash="dot", line_color="grey")
    fig.update_layout(xaxis_title="score decile (1=low, 10=high)",
                      yaxis_title="mean forward return", height=340,
                      margin=dict(l=10, r=10, t=40, b=10),
                      title="quantile spread (monotonic ⇒ score discriminates)")
    return fig


@st.cache_data(show_spinner=False)
def _car_summary(prices: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """Cached CAR compute (events × iterrows is ~seconds; cache by data hash)."""
    from aionis.eval.event_study import cumulative_abnormal_return
    summary, _ = cumulative_abnormal_return(prices, events, k_before=10, k_after=20)
    return summary


def _car_chart(prices: pd.DataFrame, events: pd.DataFrame) -> go.Figure:
    """Event study: cumulative abnormal return over offset with 95% CI band."""
    summary = _car_summary(prices, events)
    etype = events["event_type"].iloc[0] if len(events) else "?"
    n_ev = int(summary["n_events"].iloc[0]) if len(summary) else 0
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=summary["offset"], y=summary["car_ci_hi"],
                             line={"width": 0}, showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=summary["offset"], y=summary["car_ci_lo"],
                             fill="tonexty", fillcolor="rgba(100,150,255,0.15)",
                             line={"width": 0}, showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=summary["offset"], y=summary["car"], mode="lines",
                             line={"color": "#1f77b4"}, name="CAR"))
    fig.add_vline(x=0, line_dash="dash", line_color="red")
    fig.add_hline(y=0, line_dash="dot", line_color="grey")
    fig.update_layout(xaxis_title="sessions from event (0 = event)",
                      yaxis_title="cumulative abnormal return",
                      height=380, margin=dict(l=10, r=10, t=40, b=10),
                      title=f"CAR ({etype}, {n_ev} events) ±95% CI — "
                            "descriptive realized drift")
    return fig


# ----------------------------------------------------------------------------
# views (tabs)
# ----------------------------------------------------------------------------


def view_overview(runs: list[dict]) -> None:
    st.subheader("Headline — confirmatory findings")
    st.caption("Each phase = one pre-registered two-tailed claim on cross-sectional monthly "
               "rank-IC (treatment vs fundamentals-only base). Verdict: NULL SUPPORTED when "
               "the differential CI brackets 0.")
    _headline_table(runs)
    st.markdown("**Differential forest plot** — mean ± 95% CI per phase (CI brackets 0 ⇒ NULL)")
    if runs:
        st.plotly_chart(_differential_forest(runs), use_container_width=True)
        st.markdown("**CI precision per phase** — green = publishable-as-null (ci_half < 0.015)")
        st.plotly_chart(_ci_half_bar(runs), use_container_width=True)


def view_fit_quality(run: dict, is_syn: bool) -> None:
    phase, treat = _phase_of(run)
    st.subheader(f"Fit Quality — phase {phase} ({treat})")
    if is_syn:
        st.warning("DEMO: synthetic data.")
    st.markdown("**KPI row** — does the score predict cross-sectional returns?")
    _kpi_row(run["ic_state"], treat)
    _kpi_row(run["ic_base"], "base")
    st.markdown("**Cumulative IC vs random-walk 95% band** — stays in band ⇒ no detectable skill")
    se = _ic_kpi(run["ic_state"])["std"]  # monthly σ (not se_hac=σ/√n) for the band
    st.plotly_chart(_cumulative_ic_chart(run["ic_state"], treat, se), use_container_width=True)
    st.markdown("**Monthly rank-IC — treatment vs base**")
    st.plotly_chart(_ic_chart(run), use_container_width=True)
    oos = run.get("oos_state")
    if oos is not None and len(oos):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Score vs forward-return**")
            st.plotly_chart(_score_vs_return_scatter(oos), use_container_width=True)
        with c2:
            st.markdown("**Quantile spread** (decile)")
            st.plotly_chart(_quantile_spread_chart(oos), use_container_width=True)
    else:
        st.info("Score-vs-return scatter / quantile spread / R² need the per-ticker OOS panel, "
                "which this run didn't persist (pre-schema-2). A re-run enables them.")


def view_volatility(run: dict) -> None:
    phase, treat = _phase_of(run)
    st.subheader(f"Volatility Structure — phase {phase}")
    st.markdown("**IC distribution** (spread ⇒ how volatile the monthly signal is)")
    st.plotly_chart(_ic_histogram(run["ic_state"]), use_container_width=True)
    st.markdown("**Underwater curve** — cumulative IC drawdown (how far below its peak)")
    st.plotly_chart(_drawdown_chart(_cumulative_ic(run["ic_state"])), use_container_width=True)


def view_evolution(run: dict) -> None:
    phase, treat = _phase_of(run)
    st.subheader(f"Curve Evolution — phase {phase}")
    se = _ic_kpi(run["ic_state"])["std"]  # monthly σ (not se_hac=σ/√n) for the band
    st.markdown("**Cumulative IC with random-walk CI band** (evolution of the signal over time)")
    st.plotly_chart(_cumulative_ic_chart(run["ic_state"], treat, se), use_container_width=True)
    st.markdown("**Rolling 12-month IC + IC-vol** (trend + changing volatility)")
    st.plotly_chart(_rolling_ic_chart(run["ic_state"], 12), use_container_width=True)


def view_event_study(run: dict) -> None:
    st.subheader("Event Study — pre/post-event differences (CAR)")
    try:
        from aionis.eval import event_study  # noqa: F401
    except Exception:  # noqa: BLE001
        st.info("Event-study (CAR around 13D/earnings/macro) needs the `event_study` module.")
        return
    st.caption("Cumulative abnormal return around events (descriptive realized post-event "
               "drift — uses forward returns by design, like the strategy-return lens; NOT a "
               "PIT feature, so no leakage).")
    etype = st.selectbox("event type", ["13D", "earnings"], key="event_type")
    try:
        from aionis.config import settings
        cache = settings.data_dir / "cache"
        if etype == "13D":
            events = event_study.events_13d(cache / "phase_d_13d_events.parquet")
        else:
            events = event_study.events_earnings(cache / "phase_b_fundamentals.parquet")
        if events.empty:
            st.warning(f"no {etype} events to study.")
            return
        prices = _prices()
        st.plotly_chart(_car_chart(prices, events), use_container_width=True)
        n_surv = int(_car_summary(prices, events)["n_events"].iloc[0])
        st.caption(f"{n_surv} of {len(events)} {etype} events survived the session/window "
                   "filter; CAR = mean across survivors of the per-event cumulative abnormal "
                   "return (equal-weight cross-section benchmark).")
    except Exception as e:  # noqa: BLE001
        st.warning(f"event-study compute failed: {e}")


def view_uncertainty(runs: list[dict], run: dict) -> None:
    st.subheader("Uncertainty")
    st.markdown("**Differential forest plot** (all phases) — CI brackets 0 ⇒ NULL")
    if runs:
        st.plotly_chart(_differential_forest(runs), use_container_width=True)
        st.plotly_chart(_ci_half_bar(runs), use_container_width=True)
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
    st.caption("Multiple-testing deflation (DSR / haircut across the strategy family) is in "
               "the **Strategy Return** tab.")


def view_run_history() -> None:
    st.subheader("Run history (ledger)")
    rows = _ledger_rows()
    if not rows:
        st.info("Ledger empty.")
        return
    show = [{"ts": r.get("ts", "")[:19], "event": r.get("event"),
             "phase": r.get("phase"), "sig": str(r.get("config_sig", ""))[:12]}
            for r in rows[-30:]]
    st.dataframe(pd.DataFrame(show[::-1]), use_container_width=True, hide_index=True)


def view_coverage() -> None:
    cov = _coverage()
    st.subheader("Coverage")
    c1, c2, c3 = st.columns(3)
    c1.metric("S&P 500 PIT universe (clean)", cov["clean"])
    c2.metric("resolvable superset", cov["total"])
    c3.metric("monthly Jaccard (hanshof vs pierrebrunelle)", f"{cov['jaccard']:.3f}")
    st.caption(f"reuse-dropped tickers: {cov['dropped']}")


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
    fmt = {"sharpe_ann": "{:+.3f}", "dsr_p_conservative": "{:.3f}"}
    for nt in grid:
        fmt[f"p@n{nt}"] = "{:.3f}"
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
        st.plotly_chart(_equity_curve_chart(ls_wide), use_container_width=True)
        st.caption("Cumulative sum of each strategy's monthly long-short return "
                   "(secondary/exploratory lens; gross-of-costs). Dashed grey = "
                   f"{row.get('benchmark', 'arm_base')} benchmark. The rank-IC "
                   "differentials remain the confirmatory claims.")


# ----------------------------------------------------------------------------
# entrypoint
# ----------------------------------------------------------------------------


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
        if sw.get(h, {}).get(ph, {}).get("null_holds"))
    st.caption(f"{n_cells}/6 exploratory cells hold NULL (CI brackets 0); plus the 3 frozen "
               "h=21 confirmatory nulls.")


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
        f"Publishable (ci_half < {PUBLISHABILITY_GATE}): {kpi['publishable']} · "
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
    ic_forward = forward_run.get("ic_forward")
    if ic_forward is not None and len(ic_forward) > 0:
        monthly_se = summary.get("se_hac", 0.0)
        st.plotly_chart(
            _cumulative_ic_chart(ic_forward, "forward differential IC", monthly_se=monthly_se),
            use_container_width=True,
        )
    else:
        st.info("No forward IC data yet (accumulate via scripts/forward_score.py).")


def main() -> None:
    st.set_page_config(page_title="Aionis", page_icon="📊", layout="wide")
    st.title("Aionis — Research Dashboard v2")
    st.caption("Near-final quant-evaluation interface · 5 dimensions "
               "(fit / volatility / evolution / event-study / uncertainty) · "
               "current data demonstrates the methods, not final conclusions.")

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
            run, is_syn = _synthetic_run(), True
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
        view_event_study(run)
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
