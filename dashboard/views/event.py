"""Event Study view — CAR curves with demo capability."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.theme import apply_theme
from dashboard.views.data_loading import _prices


def view_event_study(run: dict, is_syn: bool = False) -> None:
    """Event Study: CAR (cumulative abnormal return) around events.

    Demo-capable: when is_syn=True or real event_study module unavailable,
    renders reproducible demo CAR curves with synthetic event windows.
    """
    st.subheader("Event Study — pre/post-event differences (CAR)")
    st.caption("Cumulative abnormal return around events (descriptive realized post-event "
               "drift — uses forward returns by design, like the strategy-return lens; NOT a "
               "PIT feature, so no leakage).")

    # Try real path first (only when not synthetic and module exists)
    if not is_syn:
        try:
            from aionis.config import settings
            from aionis.eval import event_study  # noqa: F401

            cache = settings.data_dir / "cache"
            etype = st.selectbox("event type", ["13D", "earnings"], key="event_type_real")
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
            return
        except ImportError:
            pass  # Fall through to demo
        except Exception as e:  # noqa: BLE001
            st.warning(f"event-study compute failed: {e}")
            return

    # Demo path (is_syn=True or module missing)
    st.warning("DEMO: synthetic data — illustrates method/interaction, not a research conclusion.")

    event_types = ["earnings", "13D", "macro"]
    demo_windows = _demo_event_windows(event_types, n_per_type=3, rng=None)  # Uses default rng=7

    for etype in event_types:
        st.markdown(f"**{etype}**")
        subset = demo_windows[demo_windows["event_type"] == etype]
        if subset.empty:
            continue

        # Compute CAR curve and CI band
        car_result = _car_ci(subset, t_pre=10, t_post=21)

        # Build Plotly figure
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=car_result.index,
            y=car_result["hi"],
            line={"width": 0},
            showlegend=False,
            hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=car_result.index,
            y=car_result["lo"],
            fill="tonexty",
            fillcolor="rgba(100,150,255,0.15)",
            line={"width": 0},
            showlegend=False,
            hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=car_result.index,
            y=car_result["mean"],
            mode="lines",
            line={"color": "#1f77b4"},
            name="CAR",
        ))
        fig.add_vline(x=0, line_dash="dash", line_color="red")
        fig.add_hline(y=0, line_dash="dot", line_color="grey")
        fig.update_layout(
            xaxis_title="sessions from event (0 = event)",
            yaxis_title="cumulative abnormal return",
            height=380,
            margin=dict(l=10, r=10, t=40, b=10),
            title=f"CAR ({etype}, {subset['event_id'].nunique()} events) ±95% CI — demo data",
        )
        fig = apply_theme(fig)
        st.plotly_chart(fig, use_container_width=True)

    st.caption("Demo: synthetic event windows (rng=7) illustrate CAR computation. "
               "Real event-study requires the event_study module + cached event parquet files.")


# ----------------------------------------------------------------------------
# event-study CAR helpers (demo-capable, no external module dependency)
# ----------------------------------------------------------------------------


def _car_curve(event_windows: pd.DataFrame, t_pre: int = 10, t_post: int = 21) -> pd.Series:
    """Compute mean CAR (cumulative abnormal return) curve across events.

    CAR(τ) = cumulative mean across events of Σ_{s=-t_pre}^{τ} abnormal_return_{event,s}.
    Baseline: CAR(-t_pre) = 0 by construction.

    Args:
        event_windows: DataFrame with columns [event_type, event_id, tau, abnormal_return].
        t_pre: Sessions before event to include (window starts at τ=-t_pre).
        t_post: Sessions after event to include (window ends at τ=+t_post).

    Returns:
        Series indexed by τ (int) with mean CAR across events at each τ.
    """
    # Filter to window
    window = event_windows[
        (event_windows["tau"] >= -t_pre) & (event_windows["tau"] <= t_post)
    ].copy()

    if window.empty:
        return pd.Series(dtype=float)

    # Compute per-event cumulative abnormal returns
    # For each event, compute cumulative sum from baseline (τ=-t_pre)
    event_cars = []
    for event_id in window["event_id"].unique():
        ev = window[window["event_id"] == event_id].sort_values("tau")
        car = ev.set_index("tau")["abnormal_return"].cumsum()
        # Subtract baseline (first value) to set CAR(-t_pre) = 0
        car = car - car.iloc[0]
        event_cars.append(car)

    # Stack and compute mean across events at each τ
    stacked = pd.concat(event_cars, axis=1)
    mean_car = stacked.mean(axis=1)

    # Reindex to full window range (fill missing with NaN)
    full_index = pd.RangeIndex(-t_pre, t_post + 1, name="tau")
    result = mean_car.reindex(full_index)
    result.index.name = None  # Remove index name to match test expectations
    return result


def _car_ci(
    event_windows: pd.DataFrame,
    t_pre: int = 10,
    t_post: int = 21,
    z: float = 1.96,
) -> pd.DataFrame:
    """Compute 95% CI band for CAR curve across events.

    CI = mean_CAR ± z * (std_across_events / sqrt(n_events)).

    Args:
        event_windows: DataFrame with columns [event_type, event_id, tau, abnormal_return].
        t_pre: Sessions before event to include.
        t_post: Sessions after event to include.
        z: Z-score for CI (1.96 → 95%, default).

    Returns:
        DataFrame with columns [mean, lo, hi] indexed by τ.
    """
    window = event_windows[
        (event_windows["tau"] >= -t_pre) & (event_windows["tau"] <= t_post)
    ].copy()

    if window.empty:
        return pd.DataFrame(columns=["mean", "lo", "hi"])

    # Compute per-event CAR series
    event_cars = []
    for event_id in window["event_id"].unique():
        ev = window[window["event_id"] == event_id].sort_values("tau")
        car = ev.set_index("tau")["abnormal_return"].cumsum()
        # Subtract baseline (first value) to set CAR(-t_pre) = 0
        car = car - car.iloc[0]
        event_cars.append(car)

    stacked = pd.concat(event_cars, axis=1)
    mean_car = stacked.mean(axis=1)
    n_events = stacked.shape[1]

    # Handle single-event case: use time-series volatility as CI proxy
    if n_events == 1:
        # For a single event, use the event's CAR range as uncertainty proxy
        car_series = stacked.iloc[:, 0]
        ci_half = pd.Series(index=car_series.index, dtype=float)
        # Use half the range as a rough CI estimate (wider than multi-event CI)
        car_range = car_series.max() - car_series.min()
        ci_half[:] = car_range / 2 if car_range > 0 else 0.01  # Fallback to 1% if flat
    else:
        std_car = stacked.std(axis=1, ddof=1)  # sample std across events
        se = std_car / np.sqrt(n_events)
        ci_half = z * se

    full_index = pd.RangeIndex(-t_pre, t_post + 1, name="tau")
    result = pd.DataFrame({
        "mean": mean_car.reindex(full_index),
        "lo": (mean_car - ci_half).reindex(full_index),
        "hi": (mean_car + ci_half).reindex(full_index),
    })
    result.index.name = None  # Remove index name to match test expectations
    return result


def _demo_event_windows(
    event_types: list[str],
    n_per_type: int = 3,
    rng: np.random.Generator | None = None,
) -> pd.DataFrame:
    """Generate reproducible demo event-window data for CAR visualization.

    Args:
        event_types: List of event types (e.g., ["earnings", "13D", "macro"]).
        n_per_type: Number of synthetic events per type.
        rng: Random number generator (if None, uses seeded default_rng(7) for reproducibility).

    Returns:
        DataFrame with columns [event_type, event_id, tau, abnormal_return].
    """
    if rng is None:
        rng = np.random.default_rng(7)  # Fixed seed for reproducible demo

    t_pre, t_post = 10, 20
    rows = []

    for etype in event_types:
        for i in range(n_per_type):
            event_id = f"{etype}_demo_{i}"
            # Create small post-event drift patterns (demo only)
            for tau in range(-t_pre, t_post + 1):
                # Baseline noise
                ar = rng.normal(0, 0.001)

                # Add small post-event drift for earnings/13D (demo pattern)
                if tau > 0 and etype in ("earnings", "13D"):
                    ar += rng.normal(0.0005, 0.0005)  # Tiny drift
                # Add reaction for macro (demo pattern)
                elif tau == 0 and etype == "macro":
                    ar += rng.normal(-0.002, 0.001)  # Immediate reaction

                rows.append({
                    "event_type": etype,
                    "event_id": event_id,
                    "tau": tau,
                    "abnormal_return": ar,
                })

    return pd.DataFrame(rows)


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
