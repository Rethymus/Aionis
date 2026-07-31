"""Dashboard design system — theme constants and plotly styling.

Provides a consistent visual identity across all dashboard charts using a stable
color palette and layout template.
"""
from __future__ import annotations

import plotly.graph_objects as go

# ----------------------------------------------------------------------------
# color palette (stable, named constants)
# ----------------------------------------------------------------------------

COLOR_TREATMENT = "#1f77b4"      # primary treatment arm
COLOR_BENCHMARK = "#7f7f7f"     # benchmark/reference
COLOR_NEGATIVE = "#d62728"       # negative values/drawdowns
COLOR_POSITIVE = "#2ca02c"       # positive values/passes
COLOR_DISTRIBUTION = "#9467bd"   # distributions/histograms
COLOR_CI_BAND = "rgba(100,150,255,0.15)"  # 95% CI bands


# ----------------------------------------------------------------------------
# plotly layout template (system-ui font, tight margins, horizontal legend)
# ----------------------------------------------------------------------------

AIONIS_TEMPLATE: dict = {
    "layout": {
        "font": {"family": "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"},
        "margin": {"l": 10, "r": 10, "t": 20, "b": 10},
        "legend": {"orientation": "h", "y": -0.2},
        "xaxis": {"showgrid": True, "gridcolor": "rgba(0,0,0,0.05)"},
        "yaxis": {"showgrid": True, "gridcolor": "rgba(0,0,0,0.05)"},
    },
}


# ----------------------------------------------------------------------------
# theme application
# ----------------------------------------------------------------------------


def apply_theme(fig: go.Figure) -> go.Figure:
    """Apply the Aionis design system to a plotly figure.

    Mutates the figure in-place and returns it for convenience.

    Args:
        fig: A plotly Figure to theme.

    Returns:
        The same Figure object (now themed).
    """
    fig.update_layout(
        font=AIONIS_TEMPLATE["layout"]["font"],
        margin=AIONIS_TEMPLATE["layout"]["margin"],
        legend=AIONIS_TEMPLATE["layout"]["legend"],
        xaxis=AIONIS_TEMPLATE["layout"]["xaxis"],
        yaxis=AIONIS_TEMPLATE["layout"]["yaxis"],
    )
    return fig
