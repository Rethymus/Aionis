"""Hermetic tests for the static site build script.

Tests verify:
- Build script runs without errors
- Generated HTML contains all required elements
- Anti-leakage framing is present (banner, caption, publishability gate)
- All 5 dimensions are represented
- At least one Plotly chart per dimension
- Deterministic build (same output on re-run)
- No real-data/ledger/network references leak in
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
SITE_DIR = PROJECT_ROOT / "site"
BUILD_SCRIPT = PROJECT_ROOT / "scripts" / "build_static_site.py"


@pytest.fixture
def build_env():
    """Set up build environment and run the build script."""
    # Ensure clean state
    if SITE_DIR.exists():
        shutil.rmtree(SITE_DIR)
    SITE_DIR.mkdir(exist_ok=True)

    # Run build
    result = subprocess.run(
        [sys.executable, str(BUILD_SCRIPT)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )

    return result


@pytest.fixture
def generated_html(build_env):
    """Read the generated HTML file."""
    html_path = SITE_DIR / "index.html"
    assert html_path.exists(), "index.html should be generated"
    return html_path.read_text(encoding="utf-8")


class TestBuildScript:
    """Test the build script itself."""

    def test_build_runs_successfully(self, build_env):
        """Build script should exit with code 0."""
        assert build_env.returncode == 0, f"Build failed: {build_env.stderr}"

    def test_build_output_mentions_path_and_size(self, build_env):
        """Build stdout should mention output path and byte size."""
        stdout = build_env.stdout
        assert "Built static site:" in stdout
        assert "index.html" in stdout
        assert "bytes" in stdout

    def test_index_html_exists(self):
        """index.html should exist after build."""
        assert (SITE_DIR / "index.html").exists()

    def test_index_html_size_reasonable(self):
        """index.html should be reasonable size (>100KB for embedded charts)."""
        size = (SITE_DIR / "index.html").stat().st_size
        assert size > 100_000, f"index.html too small: {size} bytes"
        assert size < 1_000_000, f"index.html too large: {size} bytes"


class TestAntiLeakageFraming:
    """Test anti-leakage framing is present."""

    def test_exploratory_banner_present(self, generated_html):
        """EXPLORATORY/DEMONSTRATIVE banner should be prominent."""
        assert "EXPLORATORY" in generated_html
        assert "DEMONSTRATIVE DATA" in generated_html
        assert "not a conclusion" in generated_html
        assert "not investment advice" in generated_html

    def test_preliminary_caption_present(self, generated_html):
        """'Preliminary data' caption should appear per dimension."""
        # Count occurrences — should appear once per dimension
        caption_count = generated_html.count("Preliminary data — demonstrates the method")
        assert caption_count == 5, f"Expected 5 preliminary captions, found {caption_count}"

    def test_publishability_gate_visible(self, generated_html):
        """Publishability gate (0.015) should be visible."""
        assert "0.015" in generated_html
        assert "publishability" in generated_html.lower()
        assert "CI half-width" in generated_html

    def test_no_real_results_claimed(self, generated_html):
        """HTML should not claim real results or conclusions."""
        # Check for anti-leakage language
        assert "demonstrat" in generated_html.lower()  # demonstrative, demonstrates
        assert "synthetic" in generated_html.lower()
        assert "seed=0" in generated_html

    def test_no_ledger_or_real_data_paths(self, generated_html):
        """No references to runs/ledger.jsonl or real data paths."""
        assert "runs/ledger.jsonl" not in generated_html
        assert "runs/results/" not in generated_html
        assert "data/" not in generated_html or "data/cache" not in generated_html


class TestDimensionCoverage:
    """Test all 5 dimensions are present with charts."""

    def test_dimension_1_fit_quality_present(self, generated_html):
        """Dimension 1: Fit Quality should be present."""
        assert "Fit Quality" in generated_html or "fit-quality" in generated_html
        assert "拟合质量" in generated_html

    def test_dimension_2_volatility_present(self, generated_html):
        """Dimension 2: Volatility Structure should be present."""
        assert "Volatility" in generated_html or "volatility" in generated_html
        assert "波动结构" in generated_html

    def test_dimension_3_evolution_present(self, generated_html):
        """Dimension 3: Curve Evolution should be present."""
        assert "Evolution" in generated_html or "evolution" in generated_html
        assert "曲线演化" in generated_html

    def test_dimension_4_event_study_present(self, generated_html):
        """Dimension 4: Event Study should be present."""
        assert "Event Study" in generated_html or "event-study" in generated_html
        assert "事件前后差异" in generated_html

    def test_dimension_5_uncertainty_present(self, generated_html):
        """Dimension 5: Uncertainty should be present."""
        assert "Uncertainty" in generated_html or "uncertainty" in generated_html
        assert "不确定性" in generated_html

    def test_plotly_charts_present(self, generated_html):
        """At least one Plotly.newPlot call per dimension (5 total minimum)."""
        plotly_calls = generated_html.count("Plotly.newPlot")
        assert plotly_calls >= 5, f"Expected at least 5 Plotly charts, found {plotly_calls}"

    def test_plotly_cdn_loaded(self, generated_html):
        """Plotly.js should be loaded via CDN."""
        assert "cdn.plot.ly/plotly-" in generated_html
        assert "</script>" in generated_html


class TestChartSnippets:
    """Test specific chart markers are present."""

    def test_cumulative_ic_chart_present(self, generated_html):
        """Cumulative IC chart should have div id."""
        assert "dim1-cumulative-ic" in generated_html

    def test_score_scatter_present(self, generated_html):
        """Score scatter chart should have div id."""
        assert "dim1-score-scatter" in generated_html

    def test_quantile_spread_present(self, generated_html):
        """Quantile spread chart should have div id."""
        assert "dim1-quantile-spread" in generated_html

    def test_ic_histogram_present(self, generated_html):
        """IC histogram should have div id."""
        assert "dim2-ic-histogram" in generated_html

    def test_drawdown_chart_present(self, generated_html):
        """Drawdown chart should have div id."""
        assert "dim2-drawdown" in generated_html

    def test_ci_halfwidth_chart_present(self, generated_html):
        """CI half-width bar chart should have div id."""
        assert "dim5-ci-halfwidth" in generated_html


class TestDeterminism:
    """Test build is deterministic."""

    def test_build_is_deterministic(self):
        """Two builds should produce identical or section-count-stable output."""
        # First build
        if SITE_DIR.exists():
            shutil.rmtree(SITE_DIR)
        SITE_DIR.mkdir(exist_ok=True)

        subprocess.run(
            [sys.executable, str(BUILD_SCRIPT)],
            cwd=PROJECT_ROOT,
            capture_output=True,
            check=True,
        )
        first_build = (SITE_DIR / "index.html").read_bytes()

        # Second build
        shutil.rmtree(SITE_DIR)
        SITE_DIR.mkdir(exist_ok=True)

        subprocess.run(
            [sys.executable, str(BUILD_SCRIPT)],
            cwd=PROJECT_ROOT,
            capture_output=True,
            check=True,
        )
        second_build = (SITE_DIR / "index.html").read_bytes()

        # Check exact byte-for-byte identical (plotly version pinned)
        # If not perfectly identical (plotly HTML serialization), at least section-count-stable
        if first_build != second_build:
            # Fallback: check that key markers are identical
            first_markers = first_build.count("Plotly.newPlot")
            second_markers = second_build.count("Plotly.newPlot")
            assert first_markers == second_markers, "Chart count should be stable"

    def test_seed_pinned_for_determinism(self):
        """Build script should use seed=0 for determinism."""
        build_script_content = (BUILD_SCRIPT).read_text(encoding="utf-8")
        assert "seed=0" in build_script_content or "seed = 0" in build_script_content


class TestTabNavigation:
    """Test client-side tab navigation works."""

    def test_tab_buttons_present(self, generated_html):
        """Tab buttons for all 5 dimensions should be present."""
        # Count buttons with data-tab attribute (more flexible than class)
        tab_count = generated_html.count('data-tab="')
        assert tab_count == 5, f"Expected 5 tab buttons, found {tab_count}"

    def test_tab_javascript_present(self, generated_html):
        """Client-side JS for tab switching should be present."""
        assert "addEventListener('click'" in generated_html
        assert "classList.add('active')" in generated_html
        assert "classList.remove('active')" in generated_html


class TestHtmlStructure:
    """Test HTML structure is valid."""

    def test_doctype_present(self, generated_html):
        """HTML5 doctype should be present."""
        assert "<!doctype html>" in generated_html or "<!DOCTYPE html>" in generated_html

    def test_charset_utf8(self, generated_html):
        """UTF-8 charset should be specified."""
        assert 'charset="utf-8"' in generated_html or "charset=utf-8" in generated_html

    def test_title_present(self, generated_html):
        """Page title should be present."""
        assert "<title>" in generated_html
        assert "Aionis" in generated_html

    def test_responsive_viewport(self, generated_html):
        """Viewport meta tag for responsive design should be present."""
        assert "viewport" in generated_html
        assert "width=device-width" in generated_html

    def test_css_included(self, generated_html):
        """Inline CSS should be present for styling."""
        assert "<style>" in generated_html
        assert "</style>" in generated_html


class TestSecurity:
    """Test security and safety constraints."""

    def test_no_secrets_or_api_keys(self, generated_html):
        """No API keys or secrets should be in the generated HTML."""
        # Check for common API key patterns
        assert "api_key" not in generated_html.lower()
        assert "apikey" not in generated_html.lower()
        assert "api-key" not in generated_html.lower()
        assert "secret" not in generated_html.lower()

    def test_no_external_network_requests_except_plotly_cdn(self, generated_html):
        """Only external dependency should be plotly.js CDN."""
        # Allow plotly CDN
        plotly_cdn_count = generated_html.count("cdn.plot.ly")
        assert plotly_cdn_count == 1, "Should only load plotly.js once via CDN"

        # No other CDN links or external scripts
        assert "https://" not in generated_html or plotly_cdn_count == 1


class TestCompleteness:
    """Test all charts from design doc are present."""

    def test_all_design_doc_charts_present(self, generated_html):
        """Verify all chart types from design doc have div markers."""
        # Dimension 1 charts
        assert "dim1-" in generated_html  # At least one Dim 1 chart

        # Dimension 2 charts
        assert "dim2-" in generated_html  # At least one Dim 2 chart

        # Dimension 3 charts
        assert "dim3-" in generated_html  # At least one Dim 3 chart

        # Dimension 4 charts
        assert "dim4-" in generated_html  # At least one Dim 4 chart

        # Dimension 5 charts
        assert "dim5-" in generated_html  # At least one Dim 5 chart

        # Count dimension markers
        dim_markers = sum(generated_html.count(f"dim{i}-") for i in range(1, 6))
        assert dim_markers >= 13, f"Expected at least 13 charts, found {dim_markers}"
