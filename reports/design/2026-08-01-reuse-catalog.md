# Aionis Reuse Catalog — License-Verified OSS for Dashboard v2 & RES

**Date:** 2026-08-01  
**Purpose:** License-verified catalog of permissive OSS libraries to replace hand-rolled plotly charts in the Aionis dashboard v2 (5 evaluation dimensions) and support future RES development.  
**Verification method:** `gh api repos/.../license` (SPDX IDs) for all recommendations.  
**Allowed licenses:** MIT / Apache-2.0 / BSD variants ONLY. Non-permissive libraries explicitly rejected.

---

## §A. Dashboard Tearsheet/Factor-Analysis Reuse (PRIORITY)

### Key Finding
All major quant factor-analysis libraries are **Apache-2.0** (permissive). However, they are **matplotlib-based** and do not directly compose with Streamlit/plotly. The recommended approach is:

1. **Reuse the METHODOLOGY and chart shapes** — adopt their proven chart patterns, metric definitions, and data transformations
2. **Implement in native plotly** — leverage Streamlit's existing plotly integration for seamless composition
3. **Generate static output via `to_html()`** — for GitHub Pages static mirror, export plotly figures as standalone HTML

### Dimension → OSS Mapping Table

| Dashboard Dimension | OSS Library | Exact API Entry Points | Static-Output Method | License | Notes |
|---------------------|-------------|------------------------|---------------------|---------|--------|
| **Dim 1: Fit Quality** (拟合质量) | **alphalens-reloaded** (stefan-jansen) | `create_information_tear_sheet(factor_data, prices)`<br>`create_returns_tear_sheet(factor_data, prices)`<br>`performance.cumulative_returns` | Matplotlib figures → export as PNG/SVG for static site<br>OR re-implement shapes in plotly + `fig.write_html()` | **Apache-2.0** ✓ | IC by quantile, quantile spread bars, IC time series, IC-IR — *the* factor-analysis template. **Reuse methodology, implement in plotly.** |
| **Dim 2: Volatility Structure** (波动结构) | **pyfolio-reloaded** (stefan-jansen) | `create_returns_tear_sheet(returns)`<br>`create_drawdown_tear_sheet(returns)`<br>`plot_rolling_sharpe(returns, window=12)` | Matplotlib figures → export as PNG/SVG<br>OR re-implement in plotly + `fig.write_html()` | **Apache-2.0** ✓ | Drawdown (underwater plot), return distribution, rolling vol metrics. **Reuse chart shapes in plotly.** |
| **Dim 3: Curve Evolution** (曲线演化) | **quantstats** (ranaroussi) | `qs.reports.html(returns, output='report.html', title='Tearsheet')` | **Direct standalone HTML output** — ideal for GitHub Pages! | **Apache-2.0** ✓ | Full HTML tearsheet with embedded plotly charts. **Best for static site generation.** |
| **Dim 2/3: Risk Metrics** | **empyrical** (quantopian) | `max_drawdown(returns)`<br>`annual_volatility(returns)`<br>`sortino(returns)`<br>`calmar(returns)` | N/A (metrics library) | **Apache-2.0** ✓ | Pure-python risk metrics. **Optional dep** — implement directly (~20 lines each) or add for battle-tested math. |
| **All Dimensions** | **Current hand-rolled plotly** (`dashboard/charts_v2.py`) | `_cumulative_ic_chart()`, `_quantile_spread_chart()`, etc. | `fig.write_html("chart.html", include_plotlyjs='cdn')` | N/A (in-house) | **Retain for Streamlit** — already native plotly. For static site, export via `write_html()`. |

### Concrete Implementation Plan (Replace Hand-Rolled Plotly)

**Phase 1: Swap quantstats for static HTML generation (highest ROI)**
```python
# Replace dashboard/charts_v2.py hand-rolled figures with quantstats
import quantstats as qs

# Generate standalone HTML tearsheet (for GitHub Pages static site)
qs.reports.html(
    returns=ls_returns,  # Long-short return series
    output='reports/dashboard-v2-tearsheet.html',
    title='Aionis Model Evaluation Tearsheet',
    download=False,
)
```

**Phase 2: Adopt alphalens/pyfolio METHODOLOGY for plotly shapes**
```python
# Re-implement alphalens quantile-spread chart in plotly
def _alphalens_style_quantile_spread(quantile_df: pd.DataFrame) -> go.Figure:
    """Adapt alphalens.create_returns_tear_sheet quantile spread to plotly."""
    # Alphalens methodology: group by quantile, compute mean return per period
    spread = quantile_df.groupby('quantile')['mean_ret'].mean()
    
    fig = go.Figure(go.Bar(
        x=spread.index,
        y=spread.values,
        marker_color=['#dc2626' if i == 0 else '#2563eb' if i == len(spread)-1 else '#94a3b8' 
                     for i in range(len(spread))],
    ))
    fig.update_layout(title='Quantile Spread (Alphalens Method)', ...)
    return fig
```

### Static Output Strategy (GitHub Pages + Streamlit Dual-Format)

**For Streamlit:** Keep native plotly (already works).  
**For GitHub Pages static site:**
```python
# Export each plotly figure as standalone HTML
fig = _cumulative_ic_chart(ic_data)
fig.write_html("reports/static/cumulative-ic.html", include_plotlyjs='cdn', full_html=False)

# Or use quantstats for full tearsheet
qs.reports.html(ls_returns, output='reports/static/tearsheet.html')
```

---

## §B. Event-Study Reuse (Dimension 4 — Gap 3)

### Recommended Library: **None Suitable** → Implement from Methodology Papers

**Candidate Search Results:**

| Library | License | Verdict | Reason |
|---------|----------|---------|--------|
| **eventstudy** (LemaireJean-Baptiste) | **GPL-3.0** ✗ | **REJECTED** | Non-permissive (viral) |
| **eventstudy** (sipemu) | **AGPL-3.0** ✗ | **REJECTED** | Non-permissive (network copyleft) |
| **eventStudy** (setzler) | **MIT** ✓ | NOT SUITABLE | R package (not Python), heterogeneous dynamic effects focus |
| **EventStudyInteract** (lsun20) | **MIT** ✓ | NOT SUITABLE | Interactive tool focus, unclear API for programmatic use |
| **eventstudy** (codedthinking) | **MIT** ✓ | NOT SUITABLE | Insufficient documentation, unclear CAR methodology |

**Recommendation:** Implement minimal CAR pipeline from cited papers (Brown & Warner 1980/1985; Boehmer et al. 1991; MacKinlay 1997).

**Fallback Implementation** (from methodology):
```python
# New module: src/aionis/eval/event_study.py
def car_path(event_dates: pd.DatetimeIndex, prices: pd.DataFrame, 
             benchmark: pd.Series, window: tuple = (-20, +40)) -> dict:
    """
    Compute cumulative abnormal returns around events.
    
    Methodology: Brown & Warner (1980/1985) market model.
    - Align daily returns around each event date over window
    - AR = realized_ret - benchmark_ret (market model via Mkt-RF)
    - CAR(t) = cumsum of mean AR across events up to t
    - CI band via block_bootstrap over event residuals
    
    Returns: {window, car: [...], ci_lo, ci_hi, n_events}
    """
```

---

## §C. E3 Scheduler Reuse (Slice 6 — NYSE Month-End Trigger)

### Recommended Approach: **pandas_market_calendars + GitHub Actions Cron**

| Library | License | API Entry Point | Use Case |
|---------|----------|----------------|----------|
| **pandas_market_calendars** (rsheftel) | **MIT** ✓ | `get_trading_days(start, end)`<br>`valid_days('NYSE')` | NYSE session calendar, month-end date calculation |
| **APScheduler** (agronholm) | **MIT** ✓ | `BackgroundScheduler(jobstores=...)`<br>`add_job(run_monthly, 'cron', day='last', ...)` | Local trigger (if needed, not recommended for cloud) |
| **GitHub Actions cron** | N/A (platform) | `.github/workflows/monthly.yml` → `on: schedule: - cron: '0 8 28-31 * *'` | **Recommended** — cloud-native, no dep, PIT-safe |

### Implementation Recommendation

**Use GitHub Actions cron (no dependency):**
```yaml
# .github/workflows/e3-monthly-commit.yml
name: E3 Forward Commit (Monthly NYSE Month-End)
on:
  schedule:
    - cron: '0 8 28-31 * *'  # 8AM ET on month-end days
  workflow_dispatch:  # Manual trigger for testing

jobs:
  monthly_commit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run E3 forward commit
        run: |
          # Check if today is NYSE month-end
          python -c "
          from pandas_market_calendars import get_calendar
          nyse = get_calendar('NYSE')
          today = pd.Timestamp.now(tz='UTC').normalize()
          if today in nyse.valid_days(start=today, end=today):
              # Run E3 forward commit
              uv run python scripts/e3_forward_commit.py
          "
```

**Alternative (if local scheduler needed):** `pandas_market_calendars` + `APScheduler` (both MIT).

---

## §D. RES/Factor/Backtest Reuse (Future RES Development)

| Library | License | One-Line Reuse Guidance |
|---------|----------|-------------------------|
| **qlib** (Microsoft) | **MIT** ✓ | Adopt interface/reporting ideas (not runtime dep) — portfolio construction, backtesting scaffolding, risk metrics |
| **alphalens-reloaded** (stefan-jansen) | **Apache-2.0** ✓ | Factor analysis API patterns — IC/IR computation, quantile spread, turnover metrics |
| **empyrical** (quantopian) | **Apache-2.0** ✓ | Risk metrics library — `max_drawdown`, `annual_volatility`, `sortino`, `calmar` (optional dep) |
| **pyfolio-reloaded** (stefan-jansen) | **Apache-2.0** ✓ | Returns tearsheet patterns — drawdown curves, return distributions, rolling metrics |

**Key Principle:** Reuse METHODOLOGY and INTERFACE patterns, not necessarily runtime dependencies. Adapt the proven APIs to Aionis's data contracts and anti-leakage constraints.

---

## §E. License Blockers (Non-Permissive Rejections)

| Library | License | Reason for Rejection |
|---------|----------|---------------------|
| **mlfinlab** (hudson-and-thames) | **NOASSERTION / "Other"** | Non-permissive (custom/restrictive) — **BLOCKED** per Aionis permissive-only policy |
| **eventstudy** (LemaireJean-Baptiste) | **GPL-3.0** | Viral copyleft — **BLOCKED** |
| **eventstudy** (sipemu) | **AGPL-3.0** | Network copyleft — **BLOCKED** |
| **vectorbt** (polakowo) | **Commons Clause** | Non-permissive (historical restriction, even if removed later) — **BLOCKED** per design doc §4 |
| **backtrader** (mementum) | **GPL-3.0** | Viral copyleft — **BLOCKED** |

**Status:** All recommended OSS in this catalog is permissive (MIT/Apache-2.0/BSD). No license blockers for the proposed implementations.

---

## §F. Concrete First Implementation Step (Dashboard v2)

**Priority Action:** Swap in `quantstats` for the static HTML tearsheet (highest immediate impact for GitHub Pages deployment).

**Step 1: Add quantstats dependency (already Apache-2.0 verified)**
```bash
# pyproject.toml (dependencies section)
quantstats = "^0.0.62"  # Apache-2.0 verified
```

**Step 2: Generate standalone HTML tearsheet for GitHub Pages**
```python
# scripts/generate_dashboard_static.py
import quantstats as qs
from aionis.reporting.results import load_ls_returns

def generate_static_tearsheet(config_sig: str, output_path: str):
    """Generate standalone HTML tearsheet for GitHub Pages."""
    ls_returns = load_ls_returns(config_sig)
    
    # Quantstats generates a complete, standalone HTML file
    qs.reports.html(
        returns=ls_returns['state'],  # L-S state arm returns
        benchmark=ls_returns['base'],  # Baseline returns
        output=output_path,
        title=f'Aionis Model Evaluation Tearsheet ({config_sig})',
        download=False,
        grayscale=True,
    )

if __name__ == '__main__':
    generate_static_tearsheet('17245a75', 'reports/static/dashboard-v2.html')
```

**Step 3: Update GitHub Actions to deploy static tearsheet**
```yaml
# .github/workflows/deploy-dashboard.yml
- name: Generate static dashboard
  run: |
    uv run python scripts/generate_dashboard_static.py
- name: Deploy to GitHub Pages
  uses: peaceiris/actions-gh-pages@v3
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    publish_dir: ./reports/static
```

**Result:** A fully interactive, publication-quality HTML tearsheet served on GitHub Pages, powered by Apache-2.0 quantstats, with zero hand-rolled plotly code for the static site.

---

## Summary

**✓ All dashboard libraries (alphalens-reloaded, pyfolio-reloaded, quantstats, empyrical) are Apache-2.0 (permissive).**  
**✓ Scheduler libraries (pandas_market_calendars, APScheduler) are MIT (permissive).**  
**✗ Event-study libraries:** No suitable permissive Python libs found — implement from methodology papers.  
**✓ RES libraries (qlib, alphalens, empyrical) are MIT/Apache-2.0 (permissive).**  

**Next Actions:**
1. Add `quantstats` dependency → generate static HTML tearsheet for GitHub Pages
2. Adopt alphalens/pyfactor METHODOLOGY for plotly chart shapes in Streamlit dashboard
3. Implement CAR pipeline from Brown & Warner papers for Dimension 4 (event study)
4. Use GitHub Actions cron + pandas_market_calendars for E3 monthly trigger

**End of Catalog**
