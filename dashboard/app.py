"""Aionis Phase B research dashboard (Streamlit).

Launch::

    uv run streamlit run dashboard/app.py

Reuses:
  * **Streamlit** (Apache-2.0, verified) as the app scaffold.
  * **plotly** (MIT, verified) for the rank-IC / differential charts.
  * ``aionis.reporting.results`` as the results reader and the
    ``runs/ledger.jsonl`` parser (read-only).

Four tabs:
  1. Run history   — ledger table (ts, config_sig, event, verdict).
  2. Selected run  — monthly rank-IC (arm_state vs arm_base) + differential with
                     CI band, ±0.015 publishability gate (pre-reg §7) and the 0 line.
  3. Coverage      — OOS universe 588/705, Jaccard ~0.93, dropped reuses {POM,SE,STI}.
  4. Robustness    — H6 determinism, lag_shift + placebo control differentials,
                     Harvey-Liu haircut sensitivity (pre-reg §5/§6).

Runs on synthetic data when no real result dir exists yet, so the dashboard is
demoable before the first confirmatory run lands (see :func:`_synthetic_run`).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from aionis.reporting import results as R

PUBLISHABILITY_GATE = 0.015  # pre-reg §7: 95% CI half-width < 0.015 to "publish a null"

# Coverage constants (pre-reg §3/§8; realized outcomes ledger #23/#25). Used as
# fallbacks when the ledger events are absent.
_COV_TOTAL = 705          # pierrebrunelle 2016+ tickers
_COV_CLEAN = 588          # OOS-resolvable, reuse-dropped
_JACCARD_MEAN = 0.9272    # hanshof vs pierrebrunelle, 2016+
_DROPPED_REUSE = ("POM", "SE", "STI")


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
def _ledger_rows() -> list[dict]:
    return R.read_ledger()


@st.cache_data(show_spinner=False)
def _coverage() -> dict:
    """Pull realized coverage numbers from the ledger (fallback to spec pins)."""
    cov = {
        "total": _COV_TOTAL,
        "clean": _COV_CLEAN,
        "jaccard_mean": _JACCARD_MEAN,
        "jaccard_min": None,
        "dropped_reuse": list(_DROPPED_REUSE),
        "source": "spec fallback (ledger event absent)",
    }
    for row in _ledger_rows():
        if row.get("event") == "universe_crosscheck":
            jac = row.get("jaccard_2016plus", {})
            if jac:
                cov["jaccard_mean"] = jac.get("mean", cov["jaccard_mean"])
                cov["jaccard_min"] = jac.get("min")
                cov["source"] = f"ledger (universe_crosscheck, n_months={jac.get('n_months')})"
        if row.get("event") == "oos_resolvable_universe":
            uni = row.get("universe", {})
            cov["total"] = uni.get("pb_2016plus_tickers", cov["total"])
            cov["clean"] = uni.get("clean", cov["clean"])
            cr = row.get("confirmed_reuse", {})
            if cr:
                cov["dropped_reuse"] = sorted(cr.keys())
                cov["source"] = "ledger (oos_resolvable_universe)"
    return cov


def _synthetic_run() -> dict:
    """A demo run when no real result dir exists. Clearly labelled in the UI."""
    rng = np.random.default_rng(42)
    months = pd.date_range("2017-01-31", periods=110, freq="ME")
    # arm_state modestly above arm_base; small positive differential.
    ic_state = pd.Series(rng.normal(0.022, 0.055, len(months)), index=months, name="ic")
    ic_state.index.name = "date"
    ic_base = pd.Series(rng.normal(0.008, 0.055, len(months)), index=months, name="ic")
    ic_base.index.name = "date"
    diff_series = ic_state - ic_base
    se = float(diff_series.std(ddof=1) / np.sqrt(len(diff_series)))
    return {
        "config_sig": "demo_synthetic",
        "ts": "2026-07-27T00:00:00+00:00 (DEMO)",
        "h6_deterministic": True,
        "ic_state": ic_state,
        "ic_base": ic_base,
        "summary_state": {"mean_ic": float(ic_state.mean()), "ci_half": 1.96 * se, "n": 110},
        "summary_base": {"mean_ic": float(ic_base.mean()), "ci_half": 1.96 * se, "n": 110},
        "differential": {
            "mean_diff": float(diff_series.mean()),
            "ci_lo": float(diff_series.mean() - 1.96 * se),
            "ci_hi": float(diff_series.mean() + 1.96 * se),
            "se": se,
            "n": 110,
        },
        "controls": {
            "lag_shift": {"mean_diff": 0.002, "ci_lo": -0.010, "ci_hi": 0.014, "n": 110},
            "placebo": {"mean_diff": -0.001, "ci_lo": -0.013, "ci_hi": 0.011, "n": 110},
        },
        "config": {"note": "synthetic demo data — no real confirmatory run yet"},
    }


def _pick_run() -> tuple[dict, bool]:
    """Return (run_dict, is_synthetic). Prefers a real result dir; else synthetic."""
    runs = _list_runs()
    if runs:
        return _load_run(runs[0]["config_sig"]), False
    return _synthetic_run(), True


# ----------------------------------------------------------------------------
# views
# ----------------------------------------------------------------------------


def _publishability_badge(diff: dict, summary_state: dict) -> None:
    """Pre-reg §7 verdict chip: CI half-width vs the 0.015 gate."""
    half = summary_state.get("ci_half")
    if half is None or not np.isfinite(half):
        st.caption("publishability: CI half-width unavailable")
        return
    if half < PUBLISHABILITY_GATE:
        st.success(f"publishable: arm_state CI half-width {half:.4f} < {PUBLISHABILITY_GATE}")
    else:
        st.warning(
            f"not tight enough: arm_state CI half-width {half:.4f} >= {PUBLISHABILITY_GATE} "
            "(report inconclusive, not null)"
        )


def view_run_history() -> None:
    st.subheader("Run history (runs/ledger.jsonl)")
    rows = _ledger_rows()
    if not rows:
        st.info("No ledger entries yet.")
        return
    table = []
    for r in rows:
        ev = r.get("event", "eval (phase A)")
        sig = r.get("config_sig") or r.get("sha256_prereg", "")[:12] or "—"
        verdict = _verdict(r)
        table.append({"ts": r.get("ts", ""), "config_sig": sig, "event": ev, "verdict": verdict})
    df = pd.DataFrame(table).sort_values("ts", ascending=False)
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption(
        f"{len(df)} ledger rows. Phase A rows = DA-lift evals; Phase B rows = freeze / "
        "reframe / universe / coverage annotations (durable registry, pre-reg §9)."
    )


def _verdict(row: dict) -> str:
    """Compact verdict/mean-IC string for one ledger row (heterogeneous shapes)."""
    ev = row.get("event")
    if ev == "phase_b_freeze":
        return "frozen (sha256 registered)"
    if ev == "prereg_reframe":
        return f"reframe -> {row.get('version', '?')}"
    if ev == "universe_crosscheck":
        jac = row.get("jaccard_2016plus", {})
        return f"Jaccard min {jac.get('min', '?')}, mean {jac.get('mean', '?')}"
    if ev == "oos_resolvable_universe":
        uni = row.get("universe", {})
        return f"clean {uni.get('clean', '?')}/{uni.get('pb_2016plus_tickers', '?')}"
    if ev in {"prereg_outcome_annotation"}:
        return f"annotate ({row.get('version', '?')})"
    # Phase A eval rows: primary = ERL/xgb mean da_lift.
    results = row.get("results") or []
    primary = next(
        (x for x in results if x.get("treatment") == "ERL" and x.get("learner") == "xgb"), None
    )
    if primary is not None:
        return f"DA-lift {primary.get('da_lift', float('nan')):+.4f} (n={primary.get('n', '?')})"
    return "—"


def view_selected_run(run: dict, is_synthetic: bool) -> None:
    sig = run["config_sig"]
    if is_synthetic:
        st.warning("DEMO: no real result dir yet — showing synthetic data.")
    st.subheader(f"Selected run: `{sig}`")
    st.caption(f"artifact ts: {run.get('ts')}  |  H6 deterministic: {run.get('h6_deterministic')}")

    diff = run["differential"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Δ mean rank-IC (state−base)", f"{diff.get('mean_diff', float('nan')):+.4f}")
    c2.metric("95% CI low", f"{diff.get('ci_lo', float('nan')):+.4f}")
    c3.metric("95% CI high", f"{diff.get('ci_hi', float('nan')):+.4f}")
    c4.metric("months (n)", diff.get("n", "—"))
    _publishability_badge(diff, run["summary_state"])

    st.markdown("**Monthly rank-IC — arm_state (filed) vs arm_base (period-end+lag)**")
    ic_fig = _ic_chart(run)
    st.plotly_chart(ic_fig, use_container_width=True)

    st.markdown("**Differential (state − base) with 95% CI**")
    diff_fig = _diff_chart(run)
    st.plotly_chart(diff_fig, use_container_width=True)


def _ic_chart(run: dict) -> go.Figure:
    ic_s = run["ic_state"]
    ic_b = run["ic_base"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ic_s.index, y=ic_s.values, name="arm_state (filed)", mode="lines"))
    fig.add_trace(go.Scatter(x=ic_b.index, y=ic_b.values, name="arm_base (end+lag)", mode="lines"))
    fig.add_hline(y=0, line_dash="dot", line_color="grey")
    fig.update_layout(
        xaxis_title="month", yaxis_title="cross-sectional rank-IC",
        height=360, legend=dict(orientation="h", y=-0.2), margin=dict(l=10, r=10, t=20, b=10),
    )
    return fig


def _diff_chart(run: dict) -> go.Figure:
    diff_series = run["ic_state"] - run["ic_base"]
    d = run["differential"]
    mean_d = d.get("mean_diff", float(np.nan))
    lo = d.get("ci_lo", float(np.nan))
    hi = d.get("ci_hi", float(np.nan))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=diff_series.index, y=diff_series.values, name="monthly ΔIC",
                             mode="lines", opacity=0.5))
    fig.add_hline(y=0, line_dash="dot", line_color="grey")
    fig.add_hline(y=mean_d, line_color="blue", annotation_text=f"mean Δ {mean_d:+.4f}")
    # pre-reg §7 publishability gate (±0.015) as the significance reference band.
    fig.add_hline(y=PUBLISHABILITY_GATE, line_dash="dash", line_color="red",
                  annotation_text=f"+{PUBLISHABILITY_GATE} gate")
    fig.add_hline(y=-PUBLISHABILITY_GATE, line_dash="dash", line_color="red",
                  annotation_text=f"−{PUBLISHABILITY_GATE}")
    # mean CI as a shaded band (constant across months — it's on the mean).
    fig.add_hrect(y0=lo, y1=hi, fillcolor="blue", opacity=0.10,
                  annotation_text=f"95% CI [{lo:+.4f}, {hi:+.4f}]")
    fig.update_layout(
        xaxis_title="month", yaxis_title="Δ rank-IC (state − base)",
        height=360, legend=dict(orientation="h", y=-0.2), margin=dict(l=10, r=10, t=20, b=10),
    )
    return fig


def view_coverage() -> None:
    st.subheader("OOS universe coverage")
    cov = _coverage()
    c1, c2, c3 = st.columns(3)
    c1.metric("OOS-resolvable tickers", f"{cov['clean']} / {cov['total']}")
    c2.metric("Jaccard (hanshof vs pierrebrunelle, 2016+)", f"{cov['jaccard_mean']:.3f}")
    c3.metric("dropped wrong-entity reuses", ", ".join(cov["dropped_reuse"]))
    if cov.get("jaccard_min") is not None:
        st.caption(f"Jaccard min month: {cov['jaccard_min']:.4f} (<0.95 fires; OOS in window)")
    st.caption(f"source: {cov['source']}")
    st.markdown(
        "Both Phase B arms use the **same** clean set → the rank-IC differential isolates "
        "fundamental-timing. Coverage reduction (114 unresolved renamed/merged) is a scope "
        "limit, not a bias (pre-reg §3; ledger `oos_resolvable_universe`)."
    )


def view_robustness(run: dict) -> None:
    st.subheader("Robustness & control gates")
    c1, c2 = st.columns(2)
    h6 = "PASS" if run.get("h6_deterministic") else "FAIL"
    c1.metric("H6 deterministic (bit-identical re-run)", h6)
    half = run["summary_state"].get("ci_half", float("nan"))
    c2.metric("arm_state CI half-width (gate < 0.015)", f"{half:.4f}")

    st.markdown("**Control differentials (pre-reg §5)** — the headline ΔIC must shrink/vanish.")
    controls = run.get("controls") or {}
    rows = []
    d = run["differential"]
    rows.append({"control": "headline (state−base)", "mean_diff": d.get("mean_diff"),
                 "ci_lo": d.get("ci_lo"), "ci_hi": d.get("ci_hi"), "n": d.get("n")})
    for name in ("lag_shift", "placebo"):
        c = controls.get(name)
        if c:
            rows.append({"control": name, "mean_diff": c.get("mean_diff"),
                         "ci_lo": c.get("ci_lo"), "ci_hi": c.get("ci_hi"), "n": c.get("n")})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.markdown("**Harvey-Liu haircut sensitivity (pre-reg §6)**")
    st.plotly_chart(_haircut_chart(run), use_container_width=True)


def _haircut_chart(run: dict) -> go.Figure:
    """Haircut sensitivity over n_trials, fed by the IC information ratio.

    Reuses ``aionis.eval.multiple_testing.harvey_liu_haircut`` (Bonferroni/Holm
    shrinkage). The IC-IR (|mean_ic|/SE_HAC) is the Sharpe-analog; n_obs = months.
    """
    from aionis.eval.multiple_testing import harvey_liu_haircut

    summary = run["summary_state"]
    mean_ic = abs(float(summary.get("mean_ic", 0.0)))
    se = float(summary.get("se_hac") or summary.get("ci_half", 0.0) / 1.96 or 0.0)
    n_obs = int(summary.get("n", 110))
    ir = mean_ic / se if se > 0 else 0.0
    trials = [1, 2, 5, 10, 20, 50, 100]
    ys = []
    for n_tr in trials:
        try:
            ys.append(harvey_liu_haircut(ir, n_tr, n_obs)["haircut_sharpe"])
        except ValueError:
            ys.append(0.0)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=trials, y=ys, name="haircut IC-IR", mode="lines+markers"))
    fig.add_trace(go.Scatter(x=trials, y=[ir] * len(trials), name="observed IC-IR",
                             line=dict(dash="dot")))
    fig.add_hline(y=0, line_color="grey")
    fig.update_layout(
        title=f"IC-IR {ir:.3f} surviving Harvey-Liu Bonferroni haircut (n_obs={n_obs})",
        xaxis_title="n_trials (independent configs searched)", yaxis_title="haircut IC-IR",
        height=340, legend=dict(orientation="h", y=-0.2), margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


# ----------------------------------------------------------------------------
# layout
# ----------------------------------------------------------------------------


def main() -> None:
    st.set_page_config(page_title="Aionis Phase B", page_icon="📊", layout="wide")
    st.title("Aionis — Phase B Research Dashboard")
    st.caption(
        "filed-date (arm_state) vs period-end+lag (arm_base) rank-IC differential · "
        "pre-reg §1/§7 (publishability gate 95% CI ½ < 0.015)"
    )

    runs = _list_runs()
    options = [r["config_sig"] for r in runs] if runs else []
    with st.sidebar:
        st.header("Run")
        if options:
            chosen = st.selectbox("result dir", options, index=0)
            run, is_syn = _load_run(chosen), False
        else:
            st.warning("No result dirs yet — using synthetic demo data.")
            st.caption("Wire `results.save_run(...)` into phase_b_run.py to land a real run.")
            run, is_syn = _synthetic_run(), True
        st.divider()
        st.caption(f"results root: `{R.results_dir()}`")
        st.caption(f"runs scanned: {len(runs)}")

    tabs = st.tabs(["Run history", "Selected run", "Coverage", "Robustness"])
    tab_hist, tab_run, tab_cov, tab_rob = tabs
    with tab_hist:
        view_run_history()
    with tab_run:
        view_selected_run(run, is_syn)
    with tab_cov:
        view_coverage()
    with tab_rob:
        view_robustness(run)


if __name__ == "__main__":  # pragma: no cover — Streamlit entrypoint
    main()
