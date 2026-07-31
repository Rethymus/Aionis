"""Tests for dashboard/theme.py design system."""
import plotly.graph_objects as go

from dashboard.theme import (
    AIONIS_TEMPLATE,
    COLOR_BENCHMARK,
    COLOR_CI_BAND,
    COLOR_DISTRIBUTION,
    COLOR_NEGATIVE,
    COLOR_POSITIVE,
    COLOR_TREATMENT,
    apply_theme,
)


def test_palette_constants_are_stable() -> None:
    """Palette constants should be stable string values."""
    assert isinstance(COLOR_TREATMENT, str)
    assert isinstance(COLOR_BENCHMARK, str)
    assert isinstance(COLOR_NEGATIVE, str)
    assert isinstance(COLOR_POSITIVE, str)
    assert isinstance(COLOR_DISTRIBUTION, str)
    assert isinstance(COLOR_CI_BAND, str)

    # Known values from the spec
    assert COLOR_TREATMENT == "#1f77b4"
    assert COLOR_BENCHMARK == "#7f7f7f"
    assert COLOR_NEGATIVE == "#d62728"
    assert COLOR_POSITIVE == "#2ca02c"
    assert COLOR_DISTRIBUTION == "#9467bd"
    assert COLOR_CI_BAND == "rgba(100,150,255,0.15)"


def test_aionis_template_is_dict() -> None:
    """AIONIS_TEMPLATE should be a layout template dict."""
    assert isinstance(AIONIS_TEMPLATE, dict)
    # Should have layout keys
    assert "layout" in AIONIS_TEMPLATE or "font" in AIONIS_TEMPLATE or "margin" in AIONIS_TEMPLATE


def test_apply_theme_sets_template() -> None:
    """apply_theme should apply the template and return the fig."""
    fig = go.Figure()

    themed_fig = apply_theme(fig)

    # Should return the same figure object (mutated)
    assert themed_fig is fig
    # Layout should be modified (font should be set)
    assert themed_fig.layout.font is not None


def test_apply_theme_preserves_data() -> None:
    """apply_theme should preserve existing traces."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[1, 2, 3], y=[4, 5, 6], name="test"))

    themed_fig = apply_theme(fig)

    # Should have the same number of traces
    assert len(themed_fig.data) == 1
    assert themed_fig.data[0].name == "test"


def test_apply_theme_returns_figure() -> None:
    """apply_theme should return a plotly.graph_objects.Figure."""
    fig = go.Figure()
    result = apply_theme(fig)
    assert isinstance(result, go.Figure)
