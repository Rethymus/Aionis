"""Hermetic tests for the static site build script (Track B results page).

Tests verify:
- Build runs and emits a deterministic HTML file (byte-identical on re-run)
- Output path/size are reported on stdout
- Anti-leakage framing is present (EXPLORATORY banner, SESOI gate, 诚实边界)
- Track B content is present (七主题 / 差分结果 / FF5 / risk metrics)
- Plotly charts are data-driven via embedded JSON — no runtime network fetch
- No real-data/ledger paths leak in
- Hermetic: builds go to a temp out-dir via ``--out-dir``; the real ``site/``
  working tree is NEVER touched (Track B WIP must not be disturbed).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
BUILD_SCRIPT = PROJECT_ROOT / "scripts" / "build_static_site.py"


def _run_build(out_dir: Path) -> subprocess.CompletedProcess:
    """Run the build script into ``out_dir`` (never the real site/)."""
    return subprocess.run(
        ["uv", "run", "python", str(BUILD_SCRIPT), "--out-dir", str(out_dir)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def build_env(tmp_path):
    """Build the site into tmp_path and return the subprocess result."""
    return _run_build(tmp_path)


@pytest.fixture
def generated_html(tmp_path, build_env):
    """Read the generated HTML from tmp_path (never site/)."""
    html_path = tmp_path / "index.html"
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
        assert "index.html" in stdout
        assert "bytes" in stdout

    def test_index_html_size_reasonable(self, tmp_path, generated_html):
        """index.html should be a reasonable size (new Track B page is ~17 KB)."""
        size = (tmp_path / "index.html").stat().st_size
        assert 5_000 < size < 2_000_000, f"index.html unexpected size: {size} bytes"


class TestAntiLeakageFraming:
    """Test anti-leakage framing is present."""

    def test_exploratory_banner_present(self, generated_html):
        """EXPLORATORY banner should be prominent."""
        assert "探索性" in generated_html
        assert "非投资建议" in generated_html
        assert "null 是预期可发表成果" in generated_html

    def test_sesoi_gate_present(self, generated_html):
        """SESOI / publishability gate should be visible."""
        assert "SESOI" in generated_html
        assert "0.010" in generated_html
        assert "不构成严格等价" in generated_html

    def test_no_real_results_claimed(self, generated_html):
        """HTML should not claim real conclusions — 诚实边界 marks what is NOT proven."""
        assert "不证明" in generated_html
        assert "可写" in generated_html

    def test_no_ledger_or_real_data_paths(self, generated_html):
        """No references to runs/ledger.jsonl or real data paths."""
        assert "runs/ledger.jsonl" not in generated_html
        assert "runs/results/" not in generated_html
        assert "data/cache" not in generated_html


class TestTrackBContent:
    """Test the Track B results page content is present."""

    def test_seven_themes_matrix_present(self, generated_html):
        """Seven-theme coverage matrix should be present."""
        assert "七主题覆盖矩阵" in generated_html
        assert "新闻情绪" in generated_html
        assert "FINSABER" in generated_html

    def test_differential_result_present(self, generated_html):
        """The first headline differential (treatment − price-only) should be shown."""
        assert "差分" in generated_html
        assert "treatment" in generated_html
        assert "price-only" in generated_html
        assert "#41" in generated_html
        assert "#42" in generated_html

    def test_anti_leakage_discipline_present(self, generated_html):
        """Anti-leakage discipline items should be listed."""
        assert "config_committed" in generated_html
        assert "PIT 数据" in generated_html
        assert "chronological walk-forward" in generated_html
        assert "H6 确定性" in generated_html

    def test_ff5_and_risk_metrics_sections(self, generated_html):
        """FF5 residual + risk-metrics sections (mount placeholders) should be present."""
        assert "FF5" in generated_html
        assert "mount_metrics.json" in generated_html

    def test_honest_boundary_present(self, generated_html):
        """The honest-boundary section should be present."""
        assert "诚实边界" in generated_html

    def test_data_driven_plotly_charts(self, generated_html):
        """Plotly charts should be data-driven via embedded JSON (no static PNGs)."""
        assert "Plotly.newPlot" in generated_html
        assert "icData" in generated_html


class TestDeterminism:
    """Test build is deterministic (H6)."""

    def test_build_is_deterministic(self, tmp_path):
        """Two builds into the same out-dir should be byte-identical."""
        _run_build(tmp_path)
        first_build = (tmp_path / "index.html").read_bytes()
        _run_build(tmp_path)
        second_build = (tmp_path / "index.html").read_bytes()
        assert first_build == second_build

    def test_no_randomness_sources(self):
        """Build script must not use randomness or wall-clock time."""
        content = (BUILD_SCRIPT).read_text(encoding="utf-8")
        assert "seed=0" in content or "seed = 0" in content
        assert "import random" not in content
        assert "import datetime" not in content


class TestChartsAndScripts:
    """Test chart libraries and the no-network-fetch discipline."""

    def test_plotly_and_tailwind_cdn_present(self, generated_html):
        """Tailwind (styling) + plotly (charts) are loaded via CDN scripts."""
        assert "https://cdn.tailwindcss.com" in generated_html
        assert "https://cdn.plot.ly/plotly-2.35.2.min.js" in generated_html

    def test_no_runtime_network_fetch(self, generated_html):
        """No runtime network fetch — all data is embedded at build time."""
        assert "fetch(" not in generated_html
        assert "XMLHttpRequest" not in generated_html
        assert "axios" not in generated_html

    def test_no_secrets_or_api_keys(self, generated_html):
        """No API keys or secrets should be in the generated HTML."""
        assert "api_key" not in generated_html.lower()
        assert "apikey" not in generated_html.lower()
        assert "api-key" not in generated_html.lower()
        assert "secret" not in generated_html.lower()


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
