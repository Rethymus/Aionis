"""Build script for static Aionis dashboard v2 site.

This script is DETERMINISTIC with seed=0 — same output on every run.
Imports dashboard.demo_data and dashboard.charts_v2 (read-only, no modifications).
Generates synthetic data, builds plotly figures, exports to self-contained HTML.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dashboard import charts_v2, demo_data  # noqa: E402

# Output directory
SITE_DIR = project_root / "site"
SITE_DIR.mkdir(exist_ok=True)

# Plotly CDN version (pinned for determinism)
PLOTLY_VERSION = "2.27.0"
PLOTLY_CDN = f"https://cdn.plot.ly/plotly-{PLOTLY_VERSION}.min.js"


def generate_dimension_1_fit_quality() -> list[str]:
    """Dimension 1: Fit Quality (拟合质量) — cumulative IC, score scatter, quantile spread."""
    snippets = []

    # 1. Cumulative IC chart
    ic_df = demo_data._monthly_ic_series()
    fig = charts_v2._cumulative_ic_chart(ic_df)
    snippets.append(
        fig.to_html(
            include_plotlyjs=False,
            full_html=False,
            div_id="dim1-cumulative-ic",
        )
    )

    # 2. Score scatter
    oos_df = demo_data._oos_panel()
    fig = charts_v2._score_scatter(oos_df)
    snippets.append(
        fig.to_html(
            include_plotlyjs=False,
            full_html=False,
            div_id="dim1-score-scatter",
        )
    )

    # 3. Quantile spread
    quantile_df = demo_data._quantile_aggregate(oos_df)
    fig = charts_v2._quantile_spread_chart(quantile_df)
    snippets.append(
        fig.to_html(
            include_plotlyjs=False,
            full_html=False,
            div_id="dim1-quantile-spread",
        )
    )

    return snippets


def generate_dimension_2_volatility() -> list[str]:
    """Dimension 2: Volatility Structure (波动结构) — IC histogram, rolling vol, drawdown."""
    snippets = []

    ic_df = demo_data._monthly_ic_series()

    # 1. IC histogram
    fig = charts_v2._ic_histogram(ic_df)
    snippets.append(
        fig.to_html(
            include_plotlyjs=False,
            full_html=False,
            div_id="dim2-ic-histogram",
        )
    )

    # 2. Rolling volatility
    fig = charts_v2._rolling_vol_chart(ic_df)
    snippets.append(
        fig.to_html(
            include_plotlyjs=False,
            full_html=False,
            div_id="dim2-rolling-vol",
        )
    )

    # 3. Drawdown curve
    fig = charts_v2._drawdown_chart(ic_df)
    snippets.append(
        fig.to_html(
            include_plotlyjs=False,
            full_html=False,
            div_id="dim2-drawdown",
        )
    )

    return snippets


def generate_dimension_3_evolution() -> list[str]:
    """Dimension 3: Curve Evolution (曲线演化) — cumulative L-S equity, CAR path."""
    snippets = []

    # 1. Cumulative L-S equity curve
    ls_df = demo_data._ls_returns()
    fig = charts_v2._cumulative_ls_equity(ls_df)
    snippets.append(
        fig.to_html(
            include_plotlyjs=False,
            full_html=False,
            div_id="dim3-ls-equity",
        )
    )

    # 2. CAR path (event-study demonstrative)
    car_data = demo_data._car_path()
    fig = charts_v2._car_path_chart(car_data, event_type="13D")
    snippets.append(
        fig.to_html(include_plotlyjs=False, full_html=False, div_id="dim3-car-path")
    )

    return snippets


def generate_dimension_4_event_study() -> list[str]:
    """Dimension 4: Pre/Post Event Differences (事件前后差异) — CAR paths."""
    snippets = []

    # CAR path for 13D events
    car_data = demo_data._car_path()
    fig = charts_v2._car_path_chart(car_data, event_type="13D")
    snippets.append(
        fig.to_html(include_plotlyjs=False, full_html=False, div_id="dim4-car-13d")
    )

    # Additional event types (demonstrative)
    car_data_earnings = demo_data._car_path()
    fig = charts_v2._car_path_chart(car_data_earnings, event_type="Earnings")
    snippets.append(
        fig.to_html(
            include_plotlyjs=False,
            full_html=False,
            div_id="dim4-car-earnings",
        )
    )

    return snippets


def generate_dimension_5_uncertainty() -> list[str]:
    """Dimension 5: Uncertainty (不确定性) — CI half-width, forest plot, bootstrap distribution."""
    snippets = []

    # 1. CI half-width bar vs publishability gate
    ci_df = demo_data._ci_half_by_phase()
    fig = charts_v2._ci_halfwidth_bar(ci_df)
    snippets.append(
        fig.to_html(
            include_plotlyjs=False,
            full_html=False,
            div_id="dim5-ci-halfwidth",
        )
    )

    # 2. Forest plot
    diff_df = demo_data._differential_forest_plot()
    fig = charts_v2._forest_plot(diff_df)
    snippets.append(
        fig.to_html(include_plotlyjs=False, full_html=False, div_id="dim5-forest-plot")
    )

    # 3. Bootstrap distribution
    bootstrap_samples = demo_data._bootstrap_distribution()
    observed = 0.008  # From demo_data generation
    fig = charts_v2._bootstrap_distribution(bootstrap_samples, observed)
    snippets.append(
        fig.to_html(
            include_plotlyjs=False,
            full_html=False,
            div_id="dim5-bootstrap",
        )
    )

    return snippets


def assemble_html_page(
    dim1_snippets: list[str],
    dim2_snippets: list[str],
    dim3_snippets: list[str],
    dim4_snippets: list[str],
    dim5_snippets: list[str],
) -> str:
    """Assemble the complete HTML page with all dimensions."""

    # Dimension sections (HTML for each tab)
    dim_sections = {
        "fit-quality": "\n".join(dim1_snippets),
        "volatility": "\n".join(dim2_snippets),
        "evolution": "\n".join(dim3_snippets),
        "event-study": "\n".join(dim4_snippets),
        "uncertainty": "\n".join(dim5_snippets),
    }

    html_content = f'''<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Aionis Dashboard v2 — Quant Model-Evaluation Interface</title>
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
            <p>Quant Model-Evaluation Interface — Demonstrative Analysis Methods</p>
        </div>

        <div class="publishability-reminder">
            📊 Publishability Gate: A result is "publishable" only when
            CI half-width &lt; <code>0.015</code>
            (see pre-registration §7). The charts below demonstrate the analysis
            methods on synthetic data.
        </div>

        <div class="tabs">
            <button class="tab active" data-tab="fit-quality">1. Fit Quality (拟合质量)</button>
            <button class="tab" data-tab="volatility">2. Volatility Structure (波动结构)</button>
            <button class="tab" data-tab="evolution">3. Curve Evolution (曲线演化)</button>
            <button class="tab" data-tab="event-study">4. Event Study (事件前后差异)</button>
            <button class="tab" data-tab="uncertainty">5. Uncertainty (不确定性)</button>
        </div>

        <!-- Dimension 1: Fit Quality -->
        <div id="fit-quality" class="dimension-section active">
            <h2 class="section-title">Dimension 1: Fit Quality (拟合质量)</h2>
            <p class="section-subtitle">
                How well do the OOS scores predict cross-sectional returns?
            </p>
            <div class="caption">
                Preliminary data — demonstrates the method, not a final conclusion.
            </div>
            <div class="chart">{dim_sections['fit-quality']}</div>
        </div>

        <!-- Dimension 2: Volatility -->
        <div id="volatility" class="dimension-section">
            <h2 class="section-title">Dimension 2: Volatility Structure (波动结构)</h2>
            <p class="section-subtitle">
                Is the edge stable, or clustered / fat-tailed / drawdown-prone?
            </p>
            <div class="caption">
                Preliminary data — demonstrates the method, not a final conclusion.
            </div>
            <div class="chart">{dim_sections['volatility']}</div>
        </div>

        <!-- Dimension 3: Evolution -->
        <div id="evolution" class="dimension-section">
            <h2 class="section-title">Dimension 3: Curve Evolution (曲线演化)</h2>
            <p class="section-subtitle">
                How does performance accumulate, and does it drift?
            </p>
            <div class="caption">
                Preliminary data — demonstrates the method, not a final conclusion.
            </div>
            <div class="chart">{dim_sections['evolution']}</div>
        </div>

        <!-- Dimension 4: Event Study -->
        <div id="event-study" class="dimension-section">
            <h2 class="section-title">
                Dimension 4: Pre/Post Event Differences (事件前后差异)
            </h2>
            <p class="section-subtitle">
                Do returns behave differently around real-world events?
            </p>
            <div class="caption">
                Preliminary data — demonstrates the method, not a final conclusion.
            </div>
            <div class="chart">{dim_sections['event-study']}</div>
        </div>

        <!-- Dimension 5: Uncertainty -->
        <div id="uncertainty" class="dimension-section">
            <h2 class="section-title">Dimension 5: Uncertainty (不确定性)</h2>
            <p class="section-subtitle">
                How tight is the inference — and is it publishable?
            </p>
            <div class="caption">
                Preliminary data — demonstrates the method, not a final conclusion.
            </div>
            <div class="chart">{dim_sections['uncertainty']}</div>
        </div>

        <div class="footer">
            <p>
                Aionis Quantitative Finance Research ·
                Falsifiable, Anti-Leakage Analysis Framework
            </p>
            <p>Generated from deterministic synthetic data (seed=0) · View source code on GitHub</p>
        </div>
    </div>

    <script src="{PLOTLY_CDN}"></script>
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


def build() -> Path:
    """Build the static site and return the path to index.html."""
    print("🔨 Building static Aionis dashboard v2 site...")

    # Set random seed for determinism
    np.random.seed(0)

    # Generate all dimension charts
    print("  → Generating Dimension 1: Fit Quality charts...")
    dim1_snippets = generate_dimension_1_fit_quality()

    print("  → Generating Dimension 2: Volatility Structure charts...")
    dim2_snippets = generate_dimension_2_volatility()

    print("  → Generating Dimension 3: Curve Evolution charts...")
    dim3_snippets = generate_dimension_3_evolution()

    print("  → Generating Dimension 4: Event Study charts...")
    dim4_snippets = generate_dimension_4_event_study()

    print("  → Generating Dimension 5: Uncertainty charts...")
    dim5_snippets = generate_dimension_5_uncertainty()

    # Assemble HTML
    print("  → Assembling HTML page...")
    html_content = assemble_html_page(
        dim1_snippets,
        dim2_snippets,
        dim3_snippets,
        dim4_snippets,
        dim5_snippets,
    )

    # Write to file
    output_path = SITE_DIR / "index.html"
    output_path.write_text(html_content, encoding="utf-8")

    file_size = output_path.stat().st_size
    print(f"✅ Built static site: {output_path} ({file_size:,} bytes)")

    return output_path


if __name__ == "__main__":
    build()
