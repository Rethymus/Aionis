"""Dashboard views package — extracted from dashboard/app.py.

This package contains all view functions and their associated helpers.
The main app.py now only contains the streamlit entrypoint.
"""
from __future__ import annotations

from dashboard.views.coverage import view_coverage

# Re-export all view functions for backward compatibility
from dashboard.views.event import view_event_study
from dashboard.views.fit import view_fit_quality
from dashboard.views.forward import view_forward_ic
from dashboard.views.history import view_run_history
from dashboard.views.horizon import view_horizon_robustness
from dashboard.views.overview import view_overview
from dashboard.views.strategy import view_strategy_return
from dashboard.views.uncertainty import view_uncertainty
from dashboard.views.volatility import view_evolution, view_volatility

__all__ = [
    "view_overview",
    "view_fit_quality",
    "view_volatility",
    "view_evolution",
    "view_event_study",
    "view_uncertainty",
    "view_horizon_robustness",
    "view_strategy_return",
    "view_forward_ic",
    "view_run_history",
    "view_coverage",
]
