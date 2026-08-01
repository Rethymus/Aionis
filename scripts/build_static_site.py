"""Build script for static Aionis dashboard v2 site using OSS tearsheet libraries.

This script is DETERMINISTIC with seed=0 — same output on every run.
Imports dashboard.demo_data (read-only) and uses permissive OSS libraries:
- quantstats (Apache-2.0): standalone HTML tearsheet
- alphalens-reloaded (Apache-2.0): factor analysis tearsheets
- pyfolio-reloaded (Apache-2.0): drawdown/rolling tearsheets
- empyrical (Apache-2.0): KPI metrics

Event-study (Dim 4): Minimal Brown & Warner (1980/1985) implementation.
"""

from __future__ import annotations

import sys
from io import BytesIO
from pathlib import Path

import matplotlib
import numpy as np

# Configure matplotlib for deterministic non-interactive output
matplotlib.use("Agg")
import base64

import matplotlib.pyplot as plt

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import OSS libraries (will be installed via uv sync)
import pyfolio  # noqa: E402
import quantstats as qs  # noqa: E402
from alphalens import utils as alphalens_utils  # noqa: E402

# Import demo data
from dashboard import demo_data  # noqa: E402

# Output directory
SITE_DIR = project_root / "site"
SITE_DIR.mkdir(exist_ok=True)

# Temporary directory for OSS library outputs
TMP_DIR = SITE_DIR / "_tmp"
TMP_DIR.mkdir(exist_ok=True)


def _setup_determinism() -> None:
    """Set up deterministic environment for reproducible builds."""
    np.random.seed(0)
    # Use deterministic matplotlib settings
    plt.rcParams["figure.dpi"] = 100
    plt.rcParams["savefig.dpi"] = 100
    # Disable interactive mode
    plt.ioff()


def _fig_to_base64(fig: plt.Figure) -> str:
    """Convert matplotlib figure to base64-encoded data URL."""
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    data_uri = base64.b64encode(buf.read()).decode("utf-8")
    return f"data:image/png;base64,{data_uri}"
    """Convert matplotlib figure to base64-encoded data URL."""
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    data_uri = base64.b64encode(buf.read()).decode("utf-8")
    return f"data:image/png;base64,{data_uri}"


def _generate_dimension_1_fit_quality() -> dict[str, str]:
    """Dimension 1: Fit Quality (拟合质量) — alphalens tearsheets.

    Returns:
        Dict with keys: 'title', 'charts' (list of base64 PNG data URLs)
    """
    print("  → Generating Dimension 1: Fit Quality (alphalens tearsheets)...")

    _setup_determinism()

    # Get factor data and prices from demo_data
    factor_data, prices = demo_data._factor_data_and_prices()

    # Align factor data with forward returns (alphalens format)
    # Use a 1-month forward period for demonstrative analysis
    factor_data_clean = alphalens_utils.get_clean_factor_and_forward_returns(
        factor_data,
        prices,
        periods=[1],
        max_loss=0.35,
        quantiles=5,
    )

    # Generate alphalens-style figures using lower-level plotting functions
    from alphalens import performance, plotting

    charts_html = []

    # IC time series chart
    fig = plt.figure(figsize=(14, 6))
    ic = performance.factor_information_coefficient(factor_data_clean)
    plotting.plot_ic_ts(ic)
    plt.title("Information Coefficient (IC) Time Series", fontsize=14, fontweight="bold")
    plt.tight_layout()
    charts_html.append(_fig_to_base64(fig))

    # Quantile returns chart
    fig = plt.figure(figsize=(14, 6))
    mean_ret = performance.mean_return_by_quantile(factor_data_clean)[0]
    plotting.plot_quantile_returns_bar(mean_ret)
    plt.title("Mean Return by Quantile", fontsize=14, fontweight="bold")
    plt.tight_layout()
    charts_html.append(_fig_to_base64(fig))

    return {"title": "Fit Quality (拟合质量)", "charts": charts_html}


def _generate_dimension_2_volatility() -> dict[str, str]:
    """Dimension 2: Volatility Structure (波动结构) — pyfolio tearsheets.

    Returns:
        Dict with keys: 'title', 'charts'
    """
    print("  → Generating Dimension 2: Volatility Structure (OSS tearsheets)...")

    _setup_determinism()

    # Get L-S returns from demo_data
    ls_returns = demo_data._ls_returns()
    ls_series = ls_returns.set_index("date")["state"]

    # Generate OSS tearsheet figures
    charts_html = []

    # Drawdown chart using pyfolio's plotting function
    fig = plt.figure(figsize=(14, 6))
    ax = fig.add_subplot(111)
    pyfolio.plotting.plot_drawdown_underwater(ls_series, ax=ax)
    plt.title("Drawdown (Underwater Plot)", fontsize=14, fontweight="bold")
    plt.tight_layout()
    charts_html.append(_fig_to_base64(fig))

    # Rolling Sharpe using quantstats (OSS library)
    fig = plt.figure(figsize=(14, 6))
    rolling_sharpe = qs.stats.rolling_sharpe(ls_series)
    plt.plot(rolling_sharpe.index, rolling_sharpe.values, color="#2563eb", linewidth=2)
    plt.title("Rolling Sharpe Ratio (12-Month Window)", fontsize=14, fontweight="bold")
    plt.xlabel("Date")
    plt.ylabel("Sharpe Ratio")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    charts_html.append(_fig_to_base64(fig))

    return {"title": "Volatility Structure (波动结构)", "charts": charts_html}


def _generate_dimension_3_evolution() -> dict[str, str]:
    """Dimension 3: Curve Evolution (曲线演化) — quantstats tearsheet.

    Returns:
        Dict with keys: 'title', 'tearsheet_html' (embedded HTML)
    """
    print("  → Generating Dimension 3: Curve Evolution (quantstats tearsheet)...")

    _setup_determinism()

    # Get L-S returns from demo_data
    ls_returns = demo_data._ls_returns()
    ls_series = ls_returns.set_index("date")["state"]

    # Generate quantstats tearsheet HTML
    tearsheet_path = TMP_DIR / "quantstats_tearsheet.html"
    qs.reports.html(
        ls_series,
        output=str(tearsheet_path),
        title="Aionis — Demonstrative L-S Tearsheet",
        download=False,
        grayscale=True,
    )

    # Read the generated HTML and extract the body content
    tearsheet_html = tearsheet_path.read_text(encoding="utf-8")

    # Extract just the tearsheet body (not the full HTML doc)
    # Quantstats generates a full HTML doc, we'll embed the body content
    body_start = tearsheet_html.find("<body>")
    body_end = tearsheet_html.find("</body>")
    if body_start != -1 and body_end != -1:
        body_content = tearsheet_html[body_start + 7 : body_end]
    else:
        body_content = tearsheet_html  # Fallback

    return {
        "title": "Curve Evolution (曲线演化)",
        "tearsheet_html": body_content,
    }


def _generate_dimension_4_event_study() -> dict[str, str]:
    """Dimension 4: Event Study (事件前后差异) — Brown & Warner CAR.

    Implements minimal Brown & Warner (1980/1985) market-model CAR with bootstrap CI.

    Returns:
        Dict with keys: 'title', 'charts_html'
    """
    print("  → Generating Dimension 4: Event Study (Brown & Warner CAR)...")

    _setup_determinism()

    # Get CAR path data from demo_data
    car_data = demo_data._car_path()

    # Generate CAR plot with bootstrap CI band
    fig = plt.figure(figsize=(14, 6))

    t = np.array(car_data["t"])
    car = np.array(car_data["car"])
    ci_lo = np.array(car_data["ci_lo"])
    ci_hi = np.array(car_data["ci_hi"])

    # Plot CAR path
    plt.plot(t, car, color="#2563eb", linewidth=2, label="CAR")
    plt.fill_between(t, ci_lo, ci_hi, color="#2563eb", alpha=0.2, label="95% CI")

    # Add event day marker
    plt.axvline(x=0, color="#dc2626", linestyle="--", linewidth=1.5, label="Event Day")
    plt.axhline(y=0, color="black", linestyle="-", linewidth=0.5, alpha=0.5)

    plt.title(
        f"Cumulative Abnormal Returns (CAR) — {car_data['n_events']} Events",
        fontsize=14,
        fontweight="bold",
    )
    plt.xlabel("Days Relative to Event")
    plt.ylabel("CAR (%)")
    plt.legend(loc="best")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    chart_html = _fig_to_base64(fig)

    # Add methodology citation
    citation_html = """
    <div class="methodology-note">
        <p><strong>Methodology:</strong> Brown & Warner (1980/1985) market-model CAR
        with bootstrap confidence bands. This is a minimal implementation of the
        published event-study methodology — not a reinvention of a wheel.</p>
    </div>
    """

    return {
        "title": "Pre/Post Event Differences (事件前后差异)",
        "charts": [chart_html],
        "citation": citation_html,
    }


def _generate_dimension_5_uncertainty() -> dict[str, str]:
    """Dimension 5: Uncertainty (不确定性) — CI half-width + forest plot.

    Returns:
        Dict with keys: 'title', 'kpi_html', 'charts'
    """
    print("  → Generating Dimension 5: Uncertainty (CI analysis + forest plot)...")

    _setup_determinism()

    # Get uncertainty data from demo_data
    ci_df = demo_data._ci_half_by_phase()
    diff_df = demo_data._differential_forest_plot()
    bootstrap_samples = demo_data._bootstrap_distribution()
    observed_ic = 0.008  # From demo_data generation

    # Compute KPI metrics using quantstats.stats (OSS library)
    ls_returns = demo_data._ls_returns()
    ls_series = ls_returns.set_index("date")["state"]

    # Extract scalar values from quantstats (may return Series for some metrics)
    sharpe_val = qs.stats.sharpe(ls_series)
    sharpe_val = sharpe_val.iloc[-1] if hasattr(sharpe_val, "iloc") else sharpe_val
    sortino_val = qs.stats.sortino(ls_series)
    sortino_val = sortino_val.iloc[-1] if hasattr(sortino_val, "iloc") else sortino_val

    kpi_metrics = {
        "Max Drawdown": f"{qs.stats.max_drawdown(ls_series):.2%}",
        "Annual Volatility": f"{qs.stats.volatility(ls_series):.2%}",
        "Sharpe Ratio": f"{sharpe_val:.2f}",
        "Sortino Ratio": f"{sortino_val:.2f}",
        "Calmar Ratio": f"{qs.stats.calmar(ls_series):.2f}",
    }

    # Generate KPI tile row HTML
    kpi_html = '<div class="kpi-tiles">'
    for metric, value in kpi_metrics.items():
        kpi_html += f"""
        <div class="kpi-tile">
            <div class="kpi-label">{metric}</div>
            <div class="kpi-value">{value}</div>
        </div>
        """
    kpi_html += "</div>"

    # Generate CI half-width bar chart
    charts_html = []

    fig = plt.figure(figsize=(12, 6))
    colors = ["#dc2626" if ci > 0.015 else "#16a34a" for ci in ci_df["ci_half"]]
    plt.bar(ci_df["phase"], ci_df["ci_half"], color=colors, alpha=0.7)
    plt.axhline(y=0.015, color="black", linestyle="--", linewidth=2, label="Publishability Gate")
    plt.title("CI Half-Width by Phase", fontsize=14, fontweight="bold")
    plt.xlabel("Phase")
    plt.ylabel("CI Half-Width")
    plt.legend()
    plt.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()

    charts_html.append(_fig_to_base64(fig))

    # Forest plot
    fig = plt.figure(figsize=(10, 6))
    y_pos = np.arange(len(diff_df))
    plt.errorbar(
        diff_df["mean_diff"],
        y_pos,
        xerr=[diff_df["mean_diff"] - diff_df["ci_lo"], diff_df["ci_hi"] - diff_df["mean_diff"]],
        fmt="o",
        color="#2563eb",
        ecolor="#2563eb",
        elinewidth=2,
        capsize=5,
    )
    plt.axvline(x=0, color="black", linestyle="--", linewidth=1)
    plt.yticks(y_pos, diff_df["label"])
    plt.title("Forest Plot — Differential vs Controls", fontsize=14, fontweight="bold")
    plt.xlabel("Mean Differential")
    plt.grid(True, alpha=0.3, axis="x")
    plt.tight_layout()

    charts_html.append(_fig_to_base64(fig))

    # Bootstrap distribution
    fig = plt.figure(figsize=(12, 6))
    plt.hist(bootstrap_samples, bins=50, color="#2563eb", alpha=0.5, edgecolor="black")
    plt.axvline(
        x=observed_ic,
        color="#dc2626",
        linestyle="--",
        linewidth=2,
        label=f"Observed ({observed_ic:.3f})",
    )
    plt.axvline(x=0, color="black", linestyle="-", linewidth=1, label="Null (0)")
    plt.title("Bootstrap Distribution — Mean Differential", fontsize=14, fontweight="bold")
    plt.xlabel("Bootstrap Mean Differential")
    plt.ylabel("Frequency")
    plt.legend()
    plt.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()

    charts_html.append(_fig_to_base64(fig))

    return {
        "title": "Uncertainty (不确定性)",
        "kpi_html": kpi_html,
        "charts": charts_html,
    }


def assemble_html_page(dim_data: list[dict]) -> str:
    """Assemble the complete HTML page with all dimensions."""

    # Generate dimension section HTML
    dim_sections_html = ""
    for i, dim in enumerate(dim_data, 1):
        section_id = ["fit-quality", "volatility", "evolution", "event-study", "uncertainty"][i - 1]

        charts_html = ""
        if "charts" in dim:
            for chart_data_url in dim["charts"]:
                charts_html += (
                    f'<img src="{chart_data_url}" class="chart-image" '
                    f'alt="{dim["title"]}">'
                )

        tearsheet_html = dim.get("tearsheet_html", "")
        citation_html = dim.get("citation", "")
        kpi_html = dim.get("kpi_html", "")

        dim_sections_html += f'''
        <!-- Dimension {i}: {dim["title"]} -->
        <div id="{section_id}" class="dimension-section{' active' if i == 1 else ''}">
            <h2 class="section-title">Dimension {i}: {dim["title"]}</h2>
            <p class="section-subtitle">
                {get_dimension_subtitle(i)}
            </p>
            <div class="caption">
                Preliminary data — demonstrates the method, not a final conclusion.
            </div>
            {kpi_html if i == 5 else ''}
            {charts_html}
            {f'<div class="tearsheet-container">{tearsheet_html}</div>' if tearsheet_html else ''}
            {citation_html}
        </div>
        '''

    html_content = f'''<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Aionis Dashboard v2 — Quant Model-Evaluation Interface (OSS-Powered)</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
                Roboto, "Helvetica Neue", Arial, sans-serif;
            background-color: #f8fafc;
            color: #1e293b;
            line-height: 1.6;
        }}

        /* Banner styles */
        .banner {{
            background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
            color: white;
            text-align: center;
            padding: 1.5rem 2rem;
            font-weight: 600;
            font-size: 1.1rem;
            letter-spacing: 0.5px;
            border-bottom: 4px solid #991b1b;
        }}

        /* Main container */
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }}

        /* Header */
        .header {{
            text-align: center;
            margin-bottom: 2rem;
            padding-bottom: 2rem;
            border-bottom: 1px solid #e2e8f0;
        }}

        .header h1 {{
            font-size: 2.5rem;
            color: #0f172a;
            margin-bottom: 0.5rem;
        }}

        .header p {{
            color: #64748b;
            font-size: 1.1rem;
        }}

        /* Tab navigation */
        .tabs {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-bottom: 2rem;
            border-bottom: 2px solid #e2e8f0;
        }}

        .tab {{
            background: none;
            border: none;
            padding: 1rem 1.5rem;
            font-size: 1rem;
            font-weight: 500;
            color: #64748b;
            cursor: pointer;
            transition: all 0.2s ease;
            border-bottom: 3px solid transparent;
            font-family: inherit;
        }}

        .tab:hover {{
            color: #2563eb;
            background-color: #eff6ff;
        }}

        .tab.active {{
            color: #2563eb;
            border-bottom-color: #2563eb;
            font-weight: 600;
        }}

        /* Dimension sections */
        .dimension-section {{
            display: none;
        }}

        .dimension-section.active {{
            display: block;
        }}

        .section-title {{
            font-size: 1.8rem;
            color: #0f172a;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid #e2e8f0;
        }}

        .section-subtitle {{
            font-size: 1.2rem;
            color: #64748b;
            margin-bottom: 1.5rem;
            font-weight: 500;
        }}

        /* Chart containers */
        .chart {{
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }}

        .chart-image {{
            width: 100%;
            height: auto;
            border-radius: 4px;
            margin-bottom: 1.5rem;
        }}

        .tearsheet-container {{
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }}

        /* Caption styling */
        .caption {{
            text-align: center;
            color: #dc2626;
            font-weight: 600;
            font-size: 0.95rem;
            padding: 1rem;
            background-color: #fef2f2;
            border-radius: 4px;
            margin-bottom: 1.5rem;
            border-left: 4px solid #dc2626;
        }}

        /* Methodology note */
        .methodology-note {{
            background-color: #f0f9ff;
            border-left: 4px solid #0284c7;
            padding: 1rem;
            margin-top: 1rem;
            border-radius: 4px;
            font-size: 0.9rem;
        }}

        /* Publishability gate reminder */
        .publishability-reminder {{
            background-color: #fef3c7;
            border: 2px solid #f59e0b;
            border-radius: 8px;
            padding: 1rem 1.5rem;
            margin-bottom: 2rem;
            font-weight: 500;
            color: #92400e;
        }}

        .publishability-reminder code {{
            background-color: #fffbeb;
            padding: 0.2rem 0.5rem;
            border-radius: 3px;
            font-family: monospace;
            font-weight: 600;
        }}

        /* KPI tiles */
        .kpi-tiles {{
            display: flex;
            flex-wrap: wrap;
            gap: 1rem;
            margin-bottom: 2rem;
        }}

        .kpi-tile {{
            flex: 1;
            min-width: 150px;
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            text-align: center;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }}

        .kpi-label {{
            font-size: 0.9rem;
            color: #64748b;
            font-weight: 500;
            margin-bottom: 0.5rem;
        }}

        .kpi-value {{
            font-size: 1.5rem;
            color: #0f172a;
            font-weight: 700;
        }}

        /* Footer */
        .footer {{
            text-align: center;
            margin-top: 3rem;
            padding-top: 2rem;
            border-top: 1px solid #e2e8f0;
            color: #94a3b8;
            font-size: 0.9rem;
        }}

        /* Responsive */
        @media (max-width: 768px) {{
            .container {{
                padding: 1rem;
            }}

            .header h1 {{
                font-size: 1.8rem;
            }}

            .tabs {{
                flex-direction: column;
            }}

            .tab {{
                width: 100%;
                text-align: left;
            }}
        }}
    </style>
</head>
<body>
    <div class="banner">
        ⚠️ EXPLORATORY · DEMONSTRATIVE DATA · not a conclusion · not investment advice
    </div>

    <div class="container">
        <div class="header">
            <h1>Aionis Dashboard v2</h1>
            <p>Quant Model-Evaluation Interface — Demonstrative Analysis Methods (OSS-Powered)</p>
        </div>

        <div class="publishability-reminder">
            📊 Publishability Gate: A result is "publishable" only when
            CI half-width &lt; <code>0.015</code>
            (see pre-registration §7). The charts below demonstrate the analysis
            methods on synthetic data using permissive OSS libraries.
        </div>

        <div class="tabs">
            <button class="tab active" data-tab="fit-quality">1. Fit Quality (拟合质量)</button>
            <button class="tab" data-tab="volatility">2. Volatility Structure (波动结构)</button>
            <button class="tab" data-tab="evolution">3. Curve Evolution (曲线演化)</button>
            <button class="tab" data-tab="event-study">4. Event Study (事件前后差异)</button>
            <button class="tab" data-tab="uncertainty">5. Uncertainty (不确定性)</button>
        </div>

        {dim_sections_html}

        <div class="footer">
            <p>
                Aionis Quantitative Finance Research ·
                Falsifiable, Anti-Leakage Analysis Framework
            </p>
            <p>
                Generated from deterministic synthetic data (seed=0) ·
                Powered by permissive OSS: quantstats, alphalens-reloaded,
                pyfolio-reloaded
            </p>
        </div>
    </div>

    <script>
        // Tab switching logic
        document.addEventListener('DOMContentLoaded', function() {{
            const tabs = document.querySelectorAll('.tab');
            const sections = document.querySelectorAll('.dimension-section');

            tabs.forEach(tab => {{
                tab.addEventListener('click', function() {{
                    const targetTab = this.getAttribute('data-tab');

                    // Remove active class from all tabs and sections
                    tabs.forEach(t => t.classList.remove('active'));
                    sections.forEach(s => s.classList.remove('active'));

                    // Add active class to clicked tab and target section
                    this.classList.add('active');
                    document.getElementById(targetTab).classList.add('active');
                }});
            }});
        }});
    </script>
</body>
</html>'''

    return html_content


def get_dimension_subtitle(dim_num: int) -> str:
    """Get subtitle for each dimension."""
    subtitles = {
        1: "How well do the OOS scores predict cross-sectional returns?",
        2: "Is the edge stable, or clustered / fat-tailed / drawdown-prone?",
        3: "How does performance accumulate, and does it drift?",
        4: "Do returns behave differently around real-world events?",
        5: "How tight is the inference — and is it publishable?",
    }
    return subtitles.get(dim_num, "")


def build() -> Path:
    """Build the static site and return the path to index.html."""
    print("🔨 Building static Aionis dashboard v2 site (OSS-Powered)...")

    # Set up determinism
    _setup_determinism()

    # Generate all dimension data using OSS libraries
    print("  → Calling OSS libraries for each dimension...")
    dim1_data = _generate_dimension_1_fit_quality()
    dim2_data = _generate_dimension_2_volatility()
    dim3_data = _generate_dimension_3_evolution()
    dim4_data = _generate_dimension_4_event_study()
    dim5_data = _generate_dimension_5_uncertainty()

    dim_data = [dim1_data, dim2_data, dim3_data, dim4_data, dim5_data]

    # Assemble HTML
    print("  → Assembling HTML page with OSS output...")
    html_content = assemble_html_page(dim_data)

    # Write to file
    output_path = SITE_DIR / "index.html"
    output_path.write_text(html_content, encoding="utf-8")

    # Clean up temporary directory
    if TMP_DIR.exists():
        import shutil
        shutil.rmtree(TMP_DIR)

    file_size = output_path.stat().st_size
    print(f"✅ Built static site: {output_path} ({file_size:,} bytes)")

    return output_path


if __name__ == "__main__":
    build()
