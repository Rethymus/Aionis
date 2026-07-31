"""Chart builder functions — pure plotly figure construction.

These functions build plotly figures without streamlit dependencies.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from aionis.eval.rank_ic import rank_ic_summary
from dashboard.theme import (
    COLOR_BENCHMARK,
    COLOR_CI_BAND,
    COLOR_DISTRIBUTION,
    COLOR_NEGATIVE,
    COLOR_POSITIVE,
    COLOR_TREATMENT,
)

# Constants
Z95 = 1.959963985
PUBLISHABILITY_GATE = 0.015


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
    """Random-walk no-skill band AROUND ZERO: ±Z95·monthly_se·√i."""
    i = np.arange(1, len(cum_ic) + 1)
    half = Z95 * float(monthly_se) * np.sqrt(i)
    return pd.DataFrame({"lo": -half, "hi": +half}, index=cum_ic.index)


def _return_distribution(returns: pd.Series) -> go.Figure:
    """Return distribution histogram with normal PDF overlay."""
    s = returns.dropna()
    fig = go.Figure()

    if len(s) == 0:
        fig.update_layout(title="No returns data")
        return fig

    # Histogram
    fig.add_trace(go.Histogram(x=s.values, nbinsx=30, name="returns",
                               marker_color=COLOR_DISTRIBUTION, showlegend=False))

    # Normal overlay
    mu, sigma = float(s.mean()), float(s.std(ddof=1))
    if sigma > 0:
        x_norm = np.linspace(s.min(), s.max(), 100)
        scale_factor = ((s.max() - s.min()) / 30) * len(s)
        y_norm = scale_factor * (1 / (sigma * np.sqrt(2 * np.pi))) * np.exp(
            -0.5 * ((x_norm - mu) / sigma) ** 2
        )
        fig.add_trace(go.Scatter(x=x_norm, y=y_norm, mode="lines",
                                 line={"color": COLOR_NEGATIVE, "width": 2},
                                 name=f"normal (μ={mu:.3f}, σ={sigma:.3f})", showlegend=True))

    fig.add_vline(x=0, line_dash="dot", line_color="grey")
    fig.update_layout(xaxis_title="return", yaxis_title="frequency",
                      height=340, margin=dict(l=10, r=10, t=40, b=10),
                      title="return distribution vs normal overlay")
    return fig


def _cumulative_ic_chart(ic: pd.Series, label: str, monthly_se: float) -> go.Figure:
    cum = _cumulative_ic(ic)
    band = _cum_ic_ci_band(cum, monthly_se)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=list(band.index), y=list(band["hi"]), name="95% CI",
                             mode="lines", line={"width": 0}, hoverinfo="skip",
                             showlegend=False))
    fig.add_trace(go.Scatter(x=list(band.index), y=list(band["lo"]), name="95% CI",
                             mode="lines", fill="tonexty",
                             fillcolor=COLOR_CI_BAND, line={"width": 0},
                             hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=list(cum.index), y=list(cum.values), name=f"cum IC ({label})",
                             mode="lines", line={"color": COLOR_TREATMENT}))
    fig.add_hline(y=0, line_dash="dot", line_color="grey")
    fig.update_layout(xaxis_title="month", yaxis_title="cumulative rank-IC",
                      height=380, legend=dict(orientation="h", y=-0.2),
                      margin=dict(l=10, r=10, t=20, b=10),
                      title="cumulative IC vs random-walk 95% band "
                            "(stays in band ⇒ indistinguishable from no-skill)")
    return fig


def _ic_histogram(ic: pd.Series) -> go.Figure:
    s = ic.dropna()
    fig = go.Figure(go.Histogram(x=s.values, nbinsx=25, marker_color=COLOR_DISTRIBUTION))
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
                             mode="lines", line={"color": COLOR_TREATMENT}))
    fig.add_trace(go.Scatter(x=r.index, y=r["std"], name=f"rolling-{window}m IC vol",
                             mode="lines", line={"color": COLOR_NEGATIVE}, yaxis="y2"))
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
                               line={"color": COLOR_NEGATIVE}))
    fig.add_hline(y=0, line_color="grey")
    fig.update_layout(xaxis_title="month", yaxis_title="cumulative IC − running max",
                      height=320, margin=dict(l=10, r=10, t=20, b=10),
                      title="underwater curve (how far cumulative IC is below its peak)")
    return fig


def _ci_half_bar(runs: list[dict]) -> go.Figure:
    """Uncertainty: ci_half per phase vs the 0.015 publishability gate."""
    from dashboard.views.data_loading import _phase_of

    phases, cis = [], []
    for r in runs:
        p, _ = _phase_of(r)
        phases.append(p)
        cis.append(r["differential"].get("ci_half", float("nan")))
    fig = go.Figure(
        go.Bar(
            x=phases,
            y=cis,
            name="differential ci_half",
            marker_color=[
                COLOR_POSITIVE if c < PUBLISHABILITY_GATE else COLOR_NEGATIVE for c in cis
            ],
            text=[f"{c:.4f}" for c in cis],
            textposition="outside",
        )
    )
    fig.add_hline(y=PUBLISHABILITY_GATE, line_dash="dash", line_color="black",
                  annotation_text=f"publishability gate {PUBLISHABILITY_GATE}")
    fig.update_layout(xaxis_title="phase", yaxis_title="95% CI half-width",
                      height=340, margin=dict(l=10, r=10, t=20, b=10),
                      title="differential CI precision per phase (green = publishable-as-null)")
    return fig


def _differential_forest(runs: list[dict]) -> go.Figure:
    """Uncertainty: differential mean ± 95% CI per phase (forest plot)."""
    from dashboard.views.data_loading import _phase_of

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
                                 line={"color": COLOR_TREATMENT}, showlegend=False))
        fig.add_trace(go.Scatter(x=[m], y=[p], mode="markers",
                                 marker={"size": 12, "color": COLOR_TREATMENT}, showlegend=False))
    fig.add_vline(x=0, line_dash="dot", line_color="grey")
    fig.update_layout(xaxis_title="differential (treatment − base) rank-IC, mean ± 95% CI",
                      yaxis_title="phase", height=320,
                      margin=dict(l=10, r=10, t=20, b=10),
                      title="differential forest plot (CI brackets 0 ⇒ NULL)")
    return fig


def _score_vs_return_scatter(oos: pd.DataFrame) -> go.Figure:
    """Fit: score vs forward-return (subsampled) + the full-data Spearman rank-corr."""
    df = oos.dropna(subset=["score", "y_fwd_ret"])
    rho = df["score"].corr(df["y_fwd_ret"], method="spearman")
    n = len(df)
    sub = df.sample(min(10_000, n), random_state=0) if n else df
    fig = go.Figure(go.Scatter(x=sub["score"], y=sub["y_fwd_ret"], mode="markers",
                               marker={"size": 3, "opacity": 0.2, "color": COLOR_TREATMENT},
                               showlegend=False))
    fig.add_hline(y=0, line_dash="dot", line_color="grey")
    fig.add_vline(x=0, line_dash="dot", line_color="grey")
    fig.update_layout(xaxis_title="OOS score", yaxis_title="forward return",
                      height=340, margin=dict(l=10, r=10, t=40, b=10),
                      title=f"score vs forward-return (Spearman {rho:+.4f}; n={n}; "
                            f"{len(sub)} plotted)")
    return fig


def _score_vs_return_scatter_with_fit(oos: pd.DataFrame) -> go.Figure:
    """Fit: score vs forward-return with regression line + R² annotation."""
    from dashboard.views.helpers import _regression_line_coords

    df = oos.dropna(subset=["score", "y_fwd_ret"])
    rho = df["score"].corr(df["y_fwd_ret"], method="spearman")
    n = len(df)
    sub = df.sample(min(10_000, n), random_state=0) if n else df

    # Get regression line and R²
    x_line, y_line, r2 = _regression_line_coords(df)

    fig = go.Figure(go.Scatter(x=sub["score"], y=sub["y_fwd_ret"], mode="markers",
                               marker={"size": 3, "opacity": 0.2, "color": COLOR_TREATMENT},
                               showlegend=False, name="observations"))

    # Add regression line
    if not np.isnan(r2):
        fig.add_trace(go.Scatter(x=x_line, y=y_line, mode="lines",
                                line={"color": COLOR_NEGATIVE, "width": 2},
                                name=f"regression (R²={r2:.3f})", showlegend=True))

    fig.add_hline(y=0, line_dash="dot", line_color="grey")
    fig.add_vline(x=0, line_dash="dot", line_color="grey")
    fig.update_layout(xaxis_title="OOS score", yaxis_title="forward return",
                      height=340, margin=dict(l=10, r=10, t=40, b=10),
                      title=f"score vs forward-return (Spearman {rho:+.4f}; n={n}; "
                            f"{len(sub)} plotted)")
    return fig


def _ic_by_regime_box(ic: pd.Series) -> go.Figure:
    """Fit: IC distribution by volatility regime (box plot)."""
    from dashboard.views.helpers import _ic_by_regime

    regimes = _ic_by_regime(ic, n_regimes=4)
    if regimes.empty:
        return go.Figure()

    # Create box traces for each regime
    fig = go.Figure()
    for regime_id in sorted(regimes["regime"].unique()):
        regime_data = regimes[regimes["regime"] == regime_id]["ic"]
        fig.add_trace(go.Box(y=regime_data, name=f"Regime {int(regime_id)}",
                            marker_color=COLOR_DISTRIBUTION, showlegend=False))

    fig.add_hline(y=0, line_dash="dot", line_color="grey")
    fig.update_layout(xaxis_title="volatility regime (rolling-σ quartile)",
                      yaxis_title="monthly rank-IC", height=340,
                      margin=dict(l=10, r=10, t=40, b=10),
                      title="IC by volatility regime (regime discovery)")
    return fig


def _quantile_spread_chart(oos: pd.DataFrame) -> go.Figure:
    """Fit: mean forward-return per score decile (alphalens-style monotonicity check)."""
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
    fig = go.Figure(go.Bar(x=labels, y=spread.values, marker_color=COLOR_POSITIVE,
                           text=[f"{v:+.4f}" for v in spread.values], textposition="outside"))
    fig.add_hline(y=0, line_dash="dot", line_color="grey")
    fig.update_layout(xaxis_title="score decile (1=low, 10=high)",
                      yaxis_title="mean forward return", height=340,
                      margin=dict(l=10, r=10, t=40, b=10),
                      title="quantile spread (monotonic ⇒ score discriminates)")
    return fig


def _equity_curve_chart(ls_wide: pd.DataFrame) -> go.Figure:
    """Cumulative long-short equity curve: one cumsum line per strategy."""
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
                  "color": COLOR_BENCHMARK if is_bench else None},
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
    from dashboard.views.data_loading import _phase_of

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


def _headline_table(runs: list[dict]) -> pd.DataFrame:
    """Overview: the per-phase verdict table (the falsifiable findings)."""
    from dashboard.views.data_loading import _phase_of

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
    return pd.DataFrame(rows)
