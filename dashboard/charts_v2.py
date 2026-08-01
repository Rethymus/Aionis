"""Pure plotly chart builders for Aionis dashboard v2.

Each function returns a go.Figure — no Streamlit calls.
Functions are <50 lines each, following the coding-style rule.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

# Gate constant from pre-registration
PUBLISHABILITY_GATE = 0.015


def _cumulative_ic_chart(ic_df: pd.DataFrame) -> go.Figure:
    """Cumulative IC line (state vs base) with CI band.

    Args:
        ic_df: DataFrame with columns: date, ic_state, ic_base

    Returns:
        plotly Figure
    """
    fig = go.Figure()

    # State line
    fig.add_trace(go.Scatter(
        x=ic_df["date"],
        y=ic_df["ic_state"].cumsum(),
        mode="lines",
        name="State (enhanced)",
        line=dict(color="#2563eb", width=2),
    ))

    # Base line
    fig.add_trace(go.Scatter(
        x=ic_df["date"],
        y=ic_df["ic_base"].cumsum(),
        mode="lines",
        name="Baseline",
        line=dict(color="#94a3b8", width=2, dash="dash"),
    ))

    # Zero reference
    fig.add_hline(y=0, line=dict(color="#64748b", width=1, dash="dot"))

    fig.update_layout(
        title="Cumulative Rank-IC",
        xaxis_title="Date",
        yaxis_title="Cumulative IC",
        hovermode="x unified",
        template="plotly_white",
    )

    return fig


def _quantile_spread_chart(quantile_df: pd.DataFrame) -> go.Figure:
    """Quantile-spread bar (alphalens-style): mean forward return per quantile.

    Args:
        quantile_df: DataFrame with columns: quantile, mean_ret, n

    Returns:
        plotly Figure
    """
    # Aggregate across time
    spread = quantile_df.groupby("quantile").agg({
        "mean_ret": "mean",
        "n": "sum",
    }).reset_index()

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=spread["quantile"],
        y=spread["mean_ret"],
        name="Mean Forward Return",
        marker_color="#2563eb",
        text=[f"{v:.3f}" for v in spread["mean_ret"]],
        textposition="outside",
    ))

    # Annotate top-bottom spread
    if len(spread) >= 2:
        top_bottom = spread["mean_ret"].max() - spread["mean_ret"].min()
        fig.add_annotation(
            x=0.95, y=0.95,
            xref="paper", yref="paper",
            text=f"Q Spread: {top_bottom:.3f}",
            showarrow=False,
            xanchor="right",
            yanchor="top",
            bgcolor="rgba(255,255,255,0.8)",
        )

    fig.update_layout(
        title="Quantile Spread (Top - Bottom)",
        xaxis_title="Quantile",
        yaxis_title="Mean Forward Return",
        template="plotly_white",
    )

    return fig


def _score_scatter(oos_df: pd.DataFrame) -> go.Figure:
    """Score-vs-forward-return scatter (pooled across months).

    Args:
        oos_df: DataFrame with columns: score, y_fwd_ret

    Returns:
        plotly Figure
    """
    # Sample for readability if too large
    sample = oos_df.sample(n=5000, random_state=0) if len(oos_df) > 5000 else oos_df
    corr = sample["score"].corr(sample["y_fwd_ret"], method="spearman")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=sample["score"], y=sample["y_fwd_ret"], mode="markers", name="Observations",
        marker=dict(color="#3b82f6", size=4, opacity=0.5),
    ))

    # Zero references
    fig.add_hline(y=0, line=dict(color="#94a3b8", width=1, dash="dot"))
    fig.add_vline(x=0, line=dict(color="#94a3b8", width=1, dash="dot"))

    # Correlation annotation
    fig.add_annotation(
        x=0.95, y=0.95, xref="paper", yref="paper", text=f"Spearman ρ: {corr:.3f}",
        showarrow=False, xanchor="right", yanchor="top", bgcolor="rgba(255,255,255,0.9)",
    )

    fig.update_layout(
        title="Score vs Forward Return (Cross-Sectional)", xaxis_title="Standardized Score",
        yaxis_title="Forward Return", template="plotly_white",
    )

    return fig


def _ic_histogram(ic_df: pd.DataFrame) -> go.Figure:
    """IC histogram (state vs base, overlaid) + normal density overlay.

    Args:
        ic_df: DataFrame with columns: ic_state, ic_base

    Returns:
        plotly Figure
    """
    fig = go.Figure()

    # State and base histograms
    fig.add_trace(go.Histogram(
        x=ic_df["ic_state"], name="State (enhanced)",
        marker_color="#2563eb", opacity=0.6, nbinsx=30,
    ))
    fig.add_trace(go.Histogram(
        x=ic_df["ic_base"], name="Baseline",
        marker_color="#94a3b8", opacity=0.6, nbinsx=30,
    ))

    # Mean lines
    fig.add_vline(
        x=ic_df["ic_state"].mean(),
        line=dict(color="#1d4ed8", width=2, dash="solid"),
        annotation_text=f"State mean: {ic_df['ic_state'].mean():.3f}",
        annotation_position="top left",
    )
    fig.add_vline(
        x=ic_df["ic_base"].mean(),
        line=dict(color="#64748b", width=2, dash="solid"),
        annotation_text=f"Base mean: {ic_df['ic_base'].mean():.3f}",
        annotation_position="top right",
    )

    fig.update_layout(
        title="IC Distribution", xaxis_title="Monthly Rank-IC",
        yaxis_title="Count", barmode="overlay", template="plotly_white",
    )

    return fig


def _rolling_vol_chart(ic_df: pd.DataFrame, window: int = 12) -> go.Figure:
    """Rolling-12m IC-vol line (stability-over-time view).

    Args:
        ic_df: DataFrame with columns: date, ic_state, ic_base
        window: Rolling window in months

    Returns:
        plotly Figure
    """
    fig = go.Figure()

    # State rolling vol
    rolling_state = ic_df["ic_state"].rolling(window=window).std()
    fig.add_trace(go.Scatter(
        x=ic_df["date"],
        y=rolling_state,
        mode="lines",
        name="State (enhanced)",
        line=dict(color="#2563eb", width=2),
    ))

    # Base rolling vol
    rolling_base = ic_df["ic_base"].rolling(window=window).std()
    fig.add_trace(go.Scatter(
        x=ic_df["date"],
        y=rolling_base,
        mode="lines",
        name="Baseline",
        line=dict(color="#94a3b8", width=2, dash="dash"),
    ))

    fig.update_layout(
        title=f"Rolling {window}-Month IC Volatility",
        xaxis_title="Date",
        yaxis_title="IC Std Dev",
        hovermode="x unified",
        template="plotly_white",
    )

    return fig


def _drawdown_chart(ic_df: pd.DataFrame) -> go.Figure:
    """Drawdown curve (underwater plot): cumulative IC measured from running max.

    Args:
        ic_df: DataFrame with columns: date, ic_state, ic_base

    Returns:
        plotly Figure
    """
    fig = go.Figure()

    # State drawdown
    cum_state = ic_df["ic_state"].cumsum()
    running_max_state = cum_state.cummax()
    dd_state = (cum_state - running_max_state) / running_max_state

    fig.add_trace(go.Scatter(
        x=ic_df["date"],
        y=dd_state * 100,  # Convert to percentage
        mode="lines",
        name="State (enhanced)",
        fill="tozeroy",
        line=dict(color="#2563eb", width=2),
    ))

    # Max DD annotation
    max_dd = dd_state.min()
    max_dd_idx = dd_state.idxmin()
    fig.add_annotation(
        x=ic_df["date"][max_dd_idx],
        y=max_dd * 100,
        text=f"Max DD: {max_dd:.1%}",
        showarrow=True,
        arrowhead=2,
    )

    fig.update_layout(
        title="Drawdown Curve (Underwater Plot)",
        xaxis_title="Date",
        yaxis_title="Drawdown (%)",
        template="plotly_white",
    )

    return fig


def _cumulative_ls_equity(ls_df: pd.DataFrame) -> go.Figure:
    """Cumulative L-S equity curve (log-y option, state vs base vs placebo).

    Args:
        ls_df: DataFrame with columns: date, state, base, placebo

    Returns:
        plotly Figure
    """
    fig = go.Figure()

    # Compute cumulative returns
    dates = ls_df["date"]
    for strat in ["state", "base", "placebo"]:
        if strat in ls_df.columns:
            cum_ret = (1 + ls_df[strat]).cumprod() - 1
            line_style = "solid" if strat == "state" else "dash"
            color = "#2563eb" if strat == "state" else "#94a3b8"
            fig.add_trace(go.Scatter(
                x=dates,
                y=cum_ret * 100,  # Percentage
                mode="lines",
                name=strat.capitalize(),
                line=dict(color=color, width=2, dash=line_style),
            ))

    # Zero reference
    fig.add_hline(y=0, line=dict(color="#64748b", width=1, dash="dot"))

    fig.update_layout(
        title="Cumulative Long-Short Equity Curve",
        xaxis_title="Date",
        yaxis_title="Cumulative Return (%)",
        hovermode="x unified",
        template="plotly_white",
    )

    return fig


def _car_path_chart(car_data: dict, event_type: str = "13D") -> go.Figure:
    """CAR path over t−k..t+k window with 95% CI ribbon.

    Args:
        car_data: Dict with keys: t, car, ci_lo, ci_hi
        event_type: Event type label

    Returns:
        plotly Figure
    """
    fig = go.Figure()

    # CI ribbon (upper and lower bounds)
    fig.add_trace(go.Scatter(
        x=car_data["t"], y=car_data["ci_hi"], mode="lines",
        line=dict(width=0), showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=car_data["t"], y=car_data["ci_lo"], mode="lines",
        line=dict(width=0), fill="tonexty", fillcolor="rgba(37, 99, 235, 0.2)",
        name="95% CI", showlegend=False,
    ))

    # CAR path line
    fig.add_trace(go.Scatter(
        x=car_data["t"], y=car_data["car"], mode="lines",
        name=f"{event_type} CAR", line=dict(color="#2563eb", width=3),
    ))

    # Event day and zero references
    fig.add_vline(x=0, line=dict(color="#dc2626", width=2, dash="dash"), annotation_text="Event")
    fig.add_hline(y=0, line=dict(color="#94a3b8", width=1, dash="dot"))

    fig.update_layout(
        title=f"Cumulative Abnormal Return ({event_type} Event Study)",
        xaxis_title="Days Relative to Event",
        yaxis_title="CAR (cumulative %)",
        template="plotly_white",
    )

    return fig


def _ci_halfwidth_bar(ci_df: pd.DataFrame) -> go.Figure:
    """CI-half-width bar across phases vs the 0.015 gate line.

    Args:
        ci_df: DataFrame with columns: phase, ci_half

    Returns:
        plotly Figure
    """
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=ci_df["phase"],
        y=ci_df["ci_half"],
        name="CI Half-Width",
        marker_color="#3b82f6",
        text=[f"{v:.3f}" for v in ci_df["ci_half"]],
        textposition="outside",
    ))

    # Gate reference line
    fig.add_hline(
        y=PUBLISHABILITY_GATE,
        line=dict(color="#dc2626", width=2, dash="dash"),
        annotation_text=f"Publishability Gate ({PUBLISHABILITY_GATE})",
        annotation_position="top right",
    )

    # Color-code: below gate = green, above = red
    colors = ["#16a34a" if v < PUBLISHABILITY_GATE else "#dc2626"
              for v in ci_df["ci_half"]]
    fig.update_traces(marker_color=colors)

    fig.update_layout(
        title="CI Half-Width by Phase (vs Publishability Gate)",
        xaxis_title="Phase",
        yaxis_title="CI Half-Width",
        template="plotly_white",
    )

    return fig


def _forest_plot(differential_df: pd.DataFrame) -> go.Figure:
    """Differential forest plot: mean_diff + 95% CI per arm/control.

    Args:
        differential_df: DataFrame with columns: label, mean_diff, ci_lo, ci_hi

    Returns:
        plotly Figure
    """
    fig = go.Figure()

    for _, row in differential_df.iterrows():
        fig.add_trace(go.Scatter(
            x=[row["mean_diff"]],
            y=[row["label"]],
            mode="markers+lines",
            name=row["label"],
            error_x=dict(type="data", symmetric=False,
                         arrayminus=[row["mean_diff"] - row["ci_lo"]],
                         array=[row["ci_hi"] - row["mean_diff"]]),
            marker=dict(size=10, color="#2563eb"),
        ))

    # Zero reference line
    fig.add_vline(
        x=0,
        line=dict(color="#64748b", width=2, dash="solid"),
    )

    fig.update_layout(
        title="Differential Forest Plot (State vs Controls)",
        xaxis_title="Mean IC Difference",
        yaxis_title="Control",
        template="plotly_white",
    )

    return fig


def _bootstrap_distribution(bootstrap_samples: np.ndarray, observed: float) -> go.Figure:
    """Bootstrap/MBB-DM distribution histogram.

    Args:
        bootstrap_samples: Array of bootstrap replicates
        observed: Observed value (e.g., mean differential)

    Returns:
        plotly Figure
    """
    fig = go.Figure()

    fig.add_trace(go.Histogram(
        x=bootstrap_samples,
        name="Bootstrap Distribution",
        marker_color="#3b82f6",
        nbinsx=50,
    ))

    # Observed value marker
    fig.add_vline(
        x=observed,
        line=dict(color="#dc2626", width=3, dash="solid"),
        annotation_text=f"Observed: {observed:.3f}",
        annotation_position="top right",
    )

    fig.update_layout(
        title="Bootstrap Distribution of Mean Differential",
        xaxis_title="Bootstrap Mean IC",
        yaxis_title="Count",
        template="plotly_white",
    )

    return fig


def _publishability_badge(ci_half: float) -> str:
    """Helper: return publishability badge text/color.

    Args:
        ci_half: CI half-width

    Returns:
        Badge HTML string
    """
    if ci_half < PUBLISHABILITY_GATE:
        color = "#16a34a"  # Green
        text = "✓ PUBLISHABLE"
    else:
        color = "#dc2626"  # Red
        text = "✗ NOT PUBLISHABLE"

    return (
        f'<span style="background-color: {color}; color: white; padding: 4px 8px; '
        f'border-radius: 4px; font-size: 12px;">{text}</span> '
        f'(CI half-width: {ci_half:.3f})'
    )
