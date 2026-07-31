"""Pure chart-data helpers — testable without streamlit.

These functions are imported by dashboard tests, so they must remain
importable from dashboard.app for backward compatibility.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.stats import linregress

from dashboard.theme import COLOR_DISTRIBUTION, COLOR_NEGATIVE


def _r2(oos: pd.DataFrame) -> float:
    """Out-of-sample R² (1 - SS_res/SS_tot) of y_fwd_ret ~ score."""
    from sklearn.linear_model import LinearRegression

    df = oos.dropna(subset=["score", "y_fwd_ret"])
    if len(df) < 2:
        return float("nan")
    X = df[["score"]].values
    y = df["y_fwd_ret"].values
    model = LinearRegression().fit(X, y)
    y_pred = model.predict(X)
    ss_res = ((y - y_pred) ** 2).sum()
    ss_tot = ((y - y.mean()) ** 2).sum()
    if ss_tot == 0:
        return float("nan")
    return float(1 - ss_res / ss_tot)


def _ic_by_regime(ic: pd.Series, n_regimes: int = 4) -> pd.DataFrame:
    """IC-by-regime using rolling-σ quartiles (regime discovery)."""
    s = ic.dropna()
    if len(s) < n_regimes * 2:
        # Not enough data for regimes
        return pd.DataFrame({"ic": s, "regime": np.nan})
    rolling_std = s.rolling(12, min_periods=6).std()
    quartiles = pd.qcut(rolling_std, n_regimes, labels=False, duplicates="drop")
    return pd.DataFrame({"ic": s, "regime": quartiles}).dropna(subset=["regime"])


def _regression_line_coords(oos: pd.DataFrame) -> tuple[list[float], list[float], float]:
    """Regression line (x, y) coords + R² for score vs return."""
    df = oos.dropna(subset=["score", "y_fwd_ret"])
    if len(df) < 2:
        return [0.0, 0.0], [0.0, 0.0], float("nan")
    result = linregress(df["score"], df["y_fwd_ret"])
    x_min, x_max = df["score"].min(), df["score"].max()
    x_line = [x_min, x_max]
    y_line = [result.slope * x_min + result.intercept, result.slope * x_max + result.intercept]
    r2 = result.rvalue ** 2
    return x_line, y_line, r2


def _sharpe(returns: pd.Series) -> float:
    """Annualized Sharpe ratio (mean/std·√12 for monthly data)."""
    s = returns.dropna()
    if len(s) < 2:
        return float("nan")
    mean = float(s.mean())
    std = float(s.std(ddof=1))
    if std == 0 or not np.isfinite(std):
        return float("nan")
    return mean / std * np.sqrt(12)


def _calmar(returns: pd.Series) -> float:
    """Calmar ratio = cumulative_return / max_drawdown."""
    s = returns.dropna()
    if len(s) < 2:
        return float("nan")
    cum = s.cumsum()
    running_max = cum.cummax()
    drawdown = cum - running_max
    max_dd = -drawdown.min()  # Positive value
    if max_dd <= 0:
        return float("inf")
    total_return = cum.iloc[-1]
    return total_return / max_dd


def _downside_deviation(returns: pd.Series) -> float:
    """Downside deviation = std of negative returns only."""
    s = returns.dropna()
    neg = s[s < 0]
    if len(neg) < 2:
        return 0.0
    return float(neg.std(ddof=1))


def _vol_of_vol(returns: pd.Series, window: int = 12) -> float:
    """Vol-of-vol = std of rolling-σ."""
    s = returns.dropna()
    if len(s) < window:
        return float("nan")
    rolling_std = s.rolling(window, min_periods=max(6, window // 2)).std()
    return float(rolling_std.std())


def _monthly_heatmap(returns_or_ic: pd.Series) -> pd.DataFrame:
    """Monthly returns/IC heatmap pivot table (year×month)."""
    s = returns_or_ic.dropna()
    if s.empty:
        return pd.DataFrame()

    # Extract year and month
    df = pd.DataFrame({"value": s})
    df["year"] = df.index.year
    df["month"] = df.index.month

    # Pivot to year×month
    pivot = df.pivot_table(index="year", columns="month", values="value", aggfunc="mean")
    # Ensure all months 1-12 are present
    for m in range(1, 13):
        if m not in pivot.columns:
            pivot[m] = np.nan
    pivot = pivot[sorted(pivot.columns)]
    return pivot


def _top_drawdowns(returns: pd.Series, k: int = 5) -> pd.DataFrame:
    """Top k drawdown periods: peak date, trough date, depth, duration."""
    s = returns.dropna()
    if len(s) < 3:
        return pd.DataFrame(columns=["peak_date", "trough_date", "depth", "duration"])

    cum = s.cumsum()
    running_max = cum.cummax()

    # Find all drawdown periods
    drawdowns = []
    peak_idx = None
    peak_val = None
    trough_idx = None
    trough_val = None

    for i in range(len(cum)):
        val = cum.iloc[i]
        if val >= running_max.iloc[i]:
            # New peak
            if peak_idx is not None and trough_idx is not None:
                # Record the previous drawdown
                depth = trough_val - peak_val
                duration = (trough_idx - peak_idx)
                drawdowns.append({
                    "peak_date": s.index[peak_idx],
                    "trough_date": s.index[trough_idx],
                    "depth": depth,
                    "duration": duration,
                })
            peak_idx = i
            peak_val = val
            trough_idx = None
            trough_val = None
        else:
            # In drawdown
            if peak_idx is not None:
                if trough_idx is None or val < trough_val:
                    trough_idx = i
                    trough_val = val

    # Record the last drawdown if we're in one
    if peak_idx is not None and trough_idx is not None:
        depth = trough_val - peak_val
        duration = (trough_idx - peak_idx)
        drawdowns.append({
            "peak_date": s.index[peak_idx],
            "trough_date": s.index[trough_idx],
            "depth": depth,
            "duration": duration,
        })

    if not drawdowns:
        return pd.DataFrame(columns=["peak_date", "trough_date", "depth", "duration"])

    df = pd.DataFrame(drawdowns)
    df = df.sort_values("depth").head(k)
    return df.reset_index(drop=True)


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
