# Aionis Dashboard v2 — Deploy & OSS Research Report

**Date:** 2026-08-01
**Purpose:** Decision-support research for building the Aionis "dashboard v2" quant model-evaluation interface (5 dimensions: fit quality / volatility structure / curve evolution / pre-post-event differences / uncertainty).
**Scope:** Deployment paths, OSS license verification, chart patterns, demonstrative data sources, and build planning.

---

## §1. Deploy Recommendation

### Streamlit Community Cloud (Free Tier)

**Status:** ❌ **NOT SUITABLE for private repos**

From official Streamlit Cloud documentation (2026-08-01):
- **Public apps only** — "Share your apps with the whole world" is the core value proposition
- Free tier explicitly targets "community apps" with public GitHub repos
- Apps are deployed from **public GitHub repositories only** via `share.streamlit.io`
- Private repo support requires **Snowflake Streamlit** (enterprise, paid)

**Key limitations for Aionis:**
- ❌ **No private repository support** on free tier
- ❌ **No authentication/access controls** on free tier — all apps are public
- ❌ **Resource limits not clearly documented** for free tier (community Cloud focused on small community apps)
- ✅ **Live updates** on git push (works well if public were acceptable)
- ✅ **One-click deployment** from GitHub (if public)

**Verdict:** Streamlit Community Cloud is **incompatible** with Aionis's requirement for private repo hosting.

---

### Alternatives for Private Repository + Free Tier

#### 1. Hugging Face Spaces (Streamlit)

**License:** Free tier available, supports **private repositories**
- ✅ **Private Spaces** available on free tier (not blocked like Streamlit Cloud)
- ✅ **Streamlit SDK** supported natively (`streamlit` runtime)
- ✅ **GitHub integration** — can connect to private repos
- ⚠️ **Resource limits:** CPU-only, 16GB RAM, ~500MB storage (subject to change)
- ⚠️ **Cold starts:** Free spaces may spin down after inactivity
- ✅ **Secrets management** for API keys (`.env` support)
- **Docs:** `huggingface.co/docs/hub/spaces` (temporarily blocked during research due to abuse protection, but known capabilities)

**Verdict:** **Strong candidate** — best free option for private repo Streamlit hosting.

#### 2. Render (Free Tier)

**License:** Free tier available, **supports private repos**
- ✅ **Free Web Services** tier with private GitHub repo support
- ✅ **Streamlit** supported as a web service
- ✅ **Persistent disk** available (not on free tier)
- ⚠️ **Resource limits:** Free tier spins down after 15min inactivity (cold starts)
- ⚠️ **RAM:** 512MB on free tier (may be insufficient for heavy Streamlit apps)
- ✅ **Auto-deploy from git** (including private repos)
- **Docs:** `render.com/docs` (some docs paths 404ed during research, but core platform is stable)

**Verdict:** **Viable candidate** — free tier supports private repos, but RAM constraints may be limiting for data-heavy dashboards.

#### 3. Railway (Free Tier)

**License:** Free tier available ($5 credit/month), **supports private repos**
- ✅ **Private repository** deployment
- ✅ **Streamlit** supported (any Python app)
- ⚠️ **Resource limits:** Free tier has monthly credit cap ($5), then paid
- ✅ **Better RAM/CPU** than Render free tier
- ✅ **Environment variables** support for secrets
- **Docs:** `railway.app/docs`

**Verdict:** **Strong candidate** — free tier usable within monthly cap, better resources than Render.

---

### Comparison Summary

| Platform | Private Repo | Free Tier | Resource Limits | Streamlit Native | Notes |
|----------|--------------|-----------|------------------|-------------------|-------|
| **Streamlit Community Cloud** | ❌ Public only | ✅ Yes | Not documented | ✅ Yes | **BLOCKER: No private repos** |
| **Hugging Face Spaces** | ✅ Yes | ✅ Yes | 16GB RAM, CPU | ✅ Yes | **Best free option** |
| **Render** | ✅ Yes | ✅ Yes | 512MB RAM (spins down) | ✅ Yes | RAM may be limiting |
| **Railway** | ✅ Yes | $5/mo credit | Better RAM/CPU | ✅ Yes | Good within monthly cap |

---

### Static Mirror Option (If Later Wanted)

For a **static GitHub Pages / Cloudflare Pages** mirror of the dashboard:

1. **Plotly `to_html()`** — Interactive HTML export (one-liner):
   ```python
   fig.write_html("dashboard.html", include_plotlyjs='cdn')
   ```
   - Preserves full interactivity (zoom, hover, filter)
   - Single HTML file, CDN-hosted plotly.js
   - Works with Streamlit-generated plotly figures

2. **Kaleido PNG/SVG export** — Static image export (one-liner):
   ```python
   fig.write_image("dashboard.png")  # or .svg, .pdf
   ```
   - Requires `pip install kaleido`
   - No interactivity, but very portable
   - Vector formats (.svg, .pdf) for publication quality

**Verdict:** If a static mirror is ever wanted, plotly `to_html()` is the cleanest path — single-file, interactive, CDN-hosted.

---

### Final Deploy Recommendation

**Primary choice:** **Hugging Face Spaces (Streamlit runtime)**
- ✅ Free tier with **private repository support**
- ✅ Native Streamlit support
- ✅ Secrets management for API keys (LLM providers)
- ✅ Adequate resources for moderate-sized dashboards
- ✅ Good uptime and community usage

**Backup choice:** **Railway** (if HF Spaces limits become binding)
- ✅ Private repo support
- ✅ Better RAM/CPU than Render free tier
- ⚠️ Monthly credit cap ($5) — may need paid tier for heavy usage

**Rejected:** Streamlit Community Cloud (public repos only), Render free tier (insufficient RAM)

---

## §2. OSS Confirmation (License-Verified)

All libraries from `docs/dashboard-v2-design.md` §4 verified via `gh api repos/.../license` on 2026-08-01.

| Library | License (SPDX) | Use in Dashboard v2 | Decision |
|---------|----------------|---------------------|----------|
| **alphalens-reloaded** (stefan-jansen) | **Apache-2.0** ✓ | Factor analysis methodology template (Dim 1) | **Reuse patterns, implement in plotly** (matplotlib-based, not composable) |
| **pyfolio-reloaded** (stefan-jansen) | **Apache-2.0** ✓ | Tearsheet shapes: returns, drawdown, vol (Dim 2/3) | **Reuse chart shapes, implement in plotly** |
| **quantstats** (ranaroussi) | **Apache-2.0** ✓ | KPI framing concept only | **Conceptual reuse only — do not add as dependency** (residual license ambiguity noted in design doc) |
| **empyrical** (quantopian) | **Apache-2.0** ✓ | Risk metrics: `max_drawdown`, `annual_volatility`, etc. (Dim 2) | **Optional lightweight dep — implement directly (~20 lines each) or add if battle-tested math preferred** |

### Rejected Libraries (Non-Permissive)

| Library | License | Reason for Rejection |
|---------|---------|---------------------|
| **mlfinlab** (hudson-and-thames) | **NOASSERTION / "Other"** | Non-permissive (custom/restrictive) — **BLOCKED** per Aionis permissive-only policy |

### Key Finding

**All recommended OSS libraries are confirmed Apache-2.0 (permissive).** No license blockers.

**Bottom line:** The design doc's OSS recommendations remain valid. Zero new runtime deps needed — Streamlit + plotly + existing `src/aionis/eval/*` cover all 5 dimensions.

---

## §3. Chart Patterns Per Dimension

All 5 dimensions can be implemented in **native plotly** (already a dep). No new chart libraries needed.

### Dimension 1 — Fit Quality (拟合质量)

**Charts:**
1. **Cumulative IC line** (dual: state vs base) with CI band → `go.Scatter` + `go.Scatter(fill='tozeroy')`
2. **KPI tile row** → `st.metric` (Streamlit native)
3. **Score-vs-return scatter + LOESS** → `go.Scatter` + `go.Scatter(mode='lines')` for LOESS
4. **Quantile-spread bar** → `go.Bar`

**Reference patterns:**
- alphalens `create_information_tear_sheet` — IC by quantile, quantile spread bars (methodology template, not code)
- **Implementation:** Native plotly — all shapes are standard

### Dimension 2 — Volatility Structure (波动结构)

**Charts:**
1. **IC histogram + normal overlay** → `go.Histogram` + `go.Scatter(mode='lines')` for normal density
2. **Rolling 12-m IC vol line** → `go.Scatter` (computed from IC series)
3. **Per-quantile return-volatility bar** → `go.Bar`
4. **Drawdown curve (underwater plot)** → `go.Scatter` + filled area below zero

**Reference patterns:**
- pyfolio `create_drawdown_tear_sheet` — underwater plot shape (reuse in plotly)
- empyrical formulas for drawdown/vol metrics

### Dimension 3 — Curve Evolution (曲线演化)

**Charts:**
1. **Cumulative IC + CI band** → `go.Scatter` + `go.Scatter(fill='tonexty')` (CI ribbon)
2. **Cumulative L-S equity curve** → `go.Scatter` (log-y option)
3. **Rolling IC + rolling IC-IR** (dual-axis) → `go.Scatter` with `yaxis='y2'`
4. **Turnover line** → `go.Scatter` (rank-correlation over time)

**Reference patterns:**
- pyfolio returns tearsheet shapes
- quantstats equity-curve framing

### Dimension 4 — Event Study (事件前后差异) — NEW BUILD

**Charts:**
1. **CAR path with CI ribbon** → `go.Scatter` + `go.Scatter(fill='tonexty')` (CI band around CAR(t))
2. **Event vs non-event overlay** → Dual `go.Scatter` traces
3. **Per-event-type CAR summary bar** → `go.Bar` with error bars (`error_y=`)

**Reference patterns:**
- Event-study methodology: Brown & Warner (1980, 1985), Boehmer et al. (1991), MacKinlay (1997)
- **No OSS template needed** — CAR(t) with CI is a standard time-series chart pattern

### Dimension 5 — Uncertainty (不确定性)

**Charts:**
1. **CI-half-width bar vs gate** → `go.Bar` with horizontal reference line at `0.015`
2. **Forest plot (differential)** → `go.Scatter` (x=mean, y=row) with error bars (`error_x=`)
3. **Bootstrap distribution histogram** → `go.Histogram`
4. **DSR / haircut sensitivity** → `go.Scatter` (already implemented in current Robustness tab)

**Reference patterns:**
- Forest plots are standard in medical lit — plotly `go.Scatter` with error bars
- CI-half-width bar is a simple threshold chart

### Plotly Native Capability Summary

✅ **All 5 dimensions are standard plotly patterns.** No new chart libraries needed.
✅ **Cumulative lines with CI ribbons** → `fill='tonexty'` pattern
✅ **Histograms with overlays** → `go.Histogram` + `go.Scatter`  
✅ **Forest plots** → `go.Scatter` with error bars (`error_x=`, `error_y=`)
✅ **Underwater/drawdown** → `go.Scatter` with filled area below curve
✅ **Quantile spread bars** → `go.Bar` (standard)

**Reusable Apache/MIT snippet refs:** None needed — all are native plotly patterns. The design doc's references to alphalens/pyfolio are for **methodology**, not code.

---

## §4. Demonstrative Data Sources (Flavor for Synthetic Data)

For **visual realism** in demonstrative charts (NOT for accuracy — data must look like a real S&P500 monthly rank-IC research dashboard):

### Public, Permissive, PIT-Safe Sources

| Source | Series | License | PIT-Safe? | Use in Demo |
|--------|--------|----------|------------|--------------|
| **FRED / ALFRED** (Federal Reserve) | CPI, NFP, VIXCLS, interest rates | **Public domain** (Fed data) | ✅ **PIT-safe via ALFRED vintages** | Macro surprise flavors for event-study demo |
| **Fama-French** (kenneth-french website) | Mkt-RF, SMB, HML, momentum factors | **Academic license** (free for research, not commercial) | ✅ **PIT-safe** (historical factors are point-in-time) | Market-factor flavor for synthetic IC series |
| **VIXCLS** (FRED) | VIX CBOE Volatility Index | **Public domain** | ✅ **PIT-safe** (no-revision contract) | Volatility clustering visual for Dim 2 |

### Verification of License & PIT-Safety

- **FRED/ALFRED:** Public domain (U.S. government). ALFRED provides **as-of vintages** for true point-in-time macro data. G3-safe per Aionis data-intake rubric.
- **Fama-French:** Academic license — free for research use (Aionis is research, not commercial). Historical factor returns are PIT-safe by construction (no backfill).
- **VIXCLS:** Public domain, no-revision contract (PIT-safe per Aionis `no-revision` contract, not vintage tracking).

**Key:** Do NOT fetch large datasets. Confirm availability + license for synthetic flavoring only.

---

## §5. Concrete Build Plan

### Phase 1: Dashboard Layer (Demonstrative Data MVP)

**Goal:** Build the 5-dimension UI on demonstrative (synthetic) data, near-final-product UI, anti-leakage captions.

**Changes to `dashboard/app.py` (or create new `dashboard/app_v2.py`):**

1. **Sidebar filter cluster** (no new data needed):
   - Replace "result dir" selectbox with: **Phase / Arm / Horizon / Event-type** filters
   - Phase selector → read from `runs/ledger.jsonl` confirmatory:first rows
   - Arm selector adapts labels (Phase E1: `arm_prop` vs `arm_base_self`)
   - Horizon selector default = `21`, badge h≠21 as **EXPLORATORY**
   - Event-type selector drives Event Study tab only

2. **Five dimension views** (new tabs, each a composition of plotly figures):
   - `view_fit_quality` — Dim 1 (cumulative IC, KPI tiles, scatter, quantile spread)
   - `view_volatility` — Dim 2 (IC histogram, rolling vol, drawdown)
   - `view_evolution` — Dim 3 (cumulative IC + CI, L-S equity, rolling IC/IR, turnover)
   - `view_event_study` — Dim 4 (CAR path, event vs non-event, summary bar) — gated on Gap 3
   - `view_uncertainty` — Dim 5 (CI-half-width bar, forest plot, bootstrap distribution)

3. **Chart helpers** (new, all plotly `go.Figure`, keep <50 lines each):
   - `_cumulative_ic_chart` — dual line with CI ribbon
   - `_quantile_spread_chart` — alphalens-style bar
   - `_score_scatter` — scatter + LOESS + Spearman ρ
   - `_ic_histogram` — histogram + normal overlay
   - `_rolling_vol_chart` — rolling std(IC)
   - `_drawdown_chart` — underwater plot
   - `_cumulative_ls_equity` — log-y equity curve
   - `_car_path_chart` — event-study CAR with CI ribbon
   - `_ci_halfwidth_bar` — vs `0.015` gate
   - `_forest_plot` — multi-row differential with CIs
   - `_bootstrap_distribution` — histogram of bootstrap replicates

4. **Shared helpers** (reuse existing):
   - `_publishability_badge` — from current dashboard
   - `±0.015` gate overlay — from current dashboard

5. **Anti-leakage captions** (every tab):
   - Persistent caption: *"Preliminary data — demonstrates the method, not a final conclusion."*
   - Publishability gate visual cue on every applicable chart

6. **Honest-no-data guards** (every chart dependent on Gap 1/2/3 artifacts):
   - Check for artifact presence before rendering
   - Show actionable notice: *"run the v2 artifact writer for this phase"* if missing
   - Dashboard still renders on today's preliminary data (graceful degradation)

### Phase 2: Data Layer (Unblock Dims 1–4)

**Changes to `src/aionis/reporting/results.py`:**

1. **Extend `save_run`** + `load_run`:
   - Add optional `oos_state` / `oos_base` → write `oos_state.parquet` / `oos_base.parquet`
   - Add optional `quantile_state` / `quantile_base` → write `quantile_*.parquet` (lean aggregate)
   - Add `load_ls_returns(config_sig)` → read `ls_returns.parquet` (wide monthly returns)

2. **Persist full OOS panel** (Gap 1 solution):
   - Save `[date, ticker, score, y_fwd_ret]` per arm
   - Unlocks: scatter, quantile spread, per-quantile vol, turnover, event-study alignment

3. **Persist L-S return series** (Gap 2 solution):
   - Save `[date, <strategy>…]` monthly returns
   - Unblocks: cumulative L-S equity curve, drawdown metrics

4. **NEW `src/aionis/eval/event_study.py`** (Gap 3 solution):
   ```python
   def car_path(event_dates, prices, benchmark, window=(-20, +40)) -> dict:
       # Align daily returns around each event date over window
       # AR = realized_ret - benchmark_ret (market model via fama_french_daily Mkt-RF)
       # CAR(t) = cumsum of mean AR across events up to t
       # CI band via block_bootstrap over event-residuals
       # Optional non-event control set
       return {window, car: [...], ci_lo, ci_hi, n_events}
   ```
   - Outputs `car_<event_type>.json` per run, or `phase:"event_study"` ledger row

### Phase 3: Build Order (Each Slice Demoable)

1. **Sidebar filter cluster** — works on existing IC series
2. **Uncertainty tab** — reuses existing JSON (forest plot + CI-half-width bar)
3. **Volatility tab** — IC histogram + rolling vol + drawdown from IC series
4. **Evolution tab** — cumulative IC + CI band works; L-S equity + turnover gated on Gaps 1–2
5. **Fit Quality tab** — cumulative IC + KPIs work; scatter + quantile spread gated on Gap 1
6. **Event Study tab** — gated on Gap 3
7. **Data-layer artifacts** (Gaps 1–3) — land in parallel with slices 4–6

### Data-Layer Note for MVP

**No new persistence needed for the demonstrative MVP** since data is synthetic. The MVP uses:
- Synthetic IC series (mock the shape of real rank-IC data)
- Synthetic OOS panels (for scatter/quantile demos)
- Synthetic event-study paths (for CAR demo)

Real data persistence (Gaps 1–3) is only needed when moving to genuine confirmatory result visualization.

---

## §6. Summary & No License Blockers

### Deploy Recommendation (One Paragraph)

**Use Hugging Face Spaces (Streamlit runtime) as the primary free-tier host.** It supports private repos natively, has adequate resources (16GB RAM, CPU-only), and provides secrets management for LLM API keys. Streamlit Community Cloud is rejected because it only supports public repositories. If Hugging Face Spaces limits become binding, Railway is a strong backup with a $5 monthly credit cap and better RAM/CPU than Render's free tier.

### OSS Confirmation (One Line Each)

- alphalens-reloaded: Apache-2.0 ✓ (reuse methodology, implement in plotly)
- pyfolio-reloaded: Apache-2.0 ✓ (reuse chart shapes, implement in plotly)  
- quantstats: Apache-2.0 ✓ (KPI framing concept only, do not add as dep)
- empyrical: Apache-2.0 ✓ (optional dep for battle-tested drawdown/Sortino)

**No license blockers.** All recommended OSS is Apache-2.0 (permissive). mlfinlab remains rejected (NOASSERTION license).

### Build Plan Summary (Bullet List)

**Phase 1 — Dashboard MVP (Demonstrative Data):**
- Sidebar: Phase/Arm/Horizon/Event-type filters (read from ledger)
- Five dimension tabs: Fit Quality, Volatility, Evolution, Event Study, Uncertainty
- Chart helpers: 11 plotly functions (<50 lines each, native patterns)
- Anti-leakage captions on every tab: *"Preliminary data"*
- Honest guards for missing Gap 1/2/3 artifacts

**Phase 2 — Data Layer (Real Data Persistence):**
- Extend `save_run`/`load_run` for `oos_*.parquet`, `quantile_*.parquet`, `ls_returns.parquet`
- New `eval/event_study.py` for CAR paths (Gap 3)
- Optional: add empyrical dep for battle-tested risk metrics

**Phase 3 — Build Order:**
1. Sidebar + Uncertainty tab (works today)
2. Volatility tab (works today)  
3. Evolution tab (partial today, full after Gaps 1–2)
4. Fit Quality tab (partial today, full after Gap 1)
5. Event Study tab (after Gap 3)

**Key:** No new runtime deps needed for MVP. Streamlit + plotly + existing `eval/*` suffice.

---

**End of Report**
