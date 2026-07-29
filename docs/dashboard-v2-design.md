# Aionis Dashboard v2 — Quant Model-Evaluation Interface (DESIGN DOC)

> Status: **design only — not built.** Research + interaction-design deliverable for
> turning `dashboard/app.py` (a 5-tab Streamlit+plotly research dashboard) into a
> near-final-product **quant model-evaluation** interface organized around **5
> evaluation dimensions**.
> Owner intent: the current data **demos the analysis methods**, not final
> conclusions. Every chart must (a) render on the preliminary/null data we have
> today and (b) scale unchanged to richer data later. No chart may *imply* a
> result the data does not support.

The 5 dimensions the owner wants to judge (with their Chinese framing):

| # | Dimension | 中文 | One-line question |
|---|---|---|---|
| 1 | **Fit quality** | 拟合质量 | Do the OOS scores predict cross-sectional returns? |
| 2 | **Volatility structure** | 波动结构 | Is the edge stable or clustered/lumpy? |
| 3 | **Curve evolution** | 曲线演化 | How does performance accumulate + drift over time? |
| 4 | **Pre/post-event differences** | 事件前后差异 | Do returns behave differently around real events (13D / earnings / macro)? |
| 5 | **Uncertainty** | 不确定性 | How tight is the inference, and is it publishable? |

---

## 0. Current state (what we build on)

**`dashboard/app.py`** is already a clean Streamlit+plotly app with 5 tabs
(Run history, Selected run, Coverage, Robustness, Strategy Return). It already:
- reuses `aionis.reporting.results` (`list_runs`, `load_run`, `read_ledger`),
- draws the monthly rank-IC for the two arms + the differential with a 95% CI band,
- draws the `±0.015` publishability gate (pre-reg §7) as horizontal reference lines,
- pulls a Harvey-Liu haircut sensitivity (reusing `eval.multiple_testing.harvey_liu_haircut`),
- reads the `phase:"strategy_return"` ledger row for the L-S Sharpe / DSR / SPA-MCS lens,
- runs on synthetic data when no result dir exists (demoable now).

**Data interface (`src/aionis/reporting/results.py`)** — the stable read surface:
`save_run` / `load_run` / `list_runs` / `read_ledger`. Per-run artifact layout
under `runs/results/<config_sig>/`:

```
ic_state.parquet   ic_base.parquet     # monthly rank-IC series per arm (idx=date, col=ic, n≈125)
summary_state.json summary_base.json   # rank_ic_summary dicts: mean_ic, t_hac, p_hac, se_hac, ci_half, n, maxlag
differential.json                       # mean_diff, se_hac, ci_half, ci_lo, ci_hi, dm_stat, dm_p_mbb, publishable_ci_half
controls.json                           # lag_shift / placebo / leave-one-out control differentials
config.json  meta.json                  # frozen config + ts / H6 flag
```

**Eval machinery already implemented and reusable** (no reimplementation):
- `eval.rank_ic` — `rank_ic_by_date`, `rank_ic_monthly`, `rank_ic_summary`
  (Newey-West HAC t/SE on the IC series).
- `eval.metrics` — `diebold_mariano` (HLN-corrected), `diebold_mariano_mbb`
  (moving-block-bootstrap DM), `block_bootstrap` (MBB CI on any stat),
  `directional_accuracy`, `up_baseline`.
- `eval.multiple_testing` — `deflated_sharpe`, `deflated_sharpe_from_returns`,
  `pbo`, `hansen_spa`, `hansen_mcs`, `harvey_liu_haircut`.
- `eval.strategy_returns` — `long_short_returns`, `strategy_eval`, `sharpe_monthly`.

**Confirmatory runs landed** (ledger `confirmatory:first`): Phase B (`17245a75…`),
C (`a7fdb48f…`), D (`d3158063…`), E1 (`ef321e9e…`) — all NULL SUPPORTED. A
`phase:"sensitivity_horizon"` ledger row sweeps h ∈ {10, 21, 42}. A
`phase:"strategy_return"` row carries the L-S Sharpe / DSR / SPA / MCS grid.

---

## 1. The critical finding: a 3-artifact data gap

Three of the five dimensions need data that is **computed but not persisted**
today. The dashboard cannot show them without a small, additive change to
`save_run` + one new event-study module.

### Gap 1 — the per-ticker OOS panel is discarded

`eval.two_arm.run_arm_oos()` returns the panel
`[date, ticker, score, y_fwd_ret]` — exactly what a factor-analysis / event-study
needs — but it is dropped the moment the monthly IC is computed. Only the
aggregated monthly IC series survives in `ic_*.parquet`.

**Blocks:** Dimension 1 (score-vs-return scatter, quantile/decile spread, R²),
Dimension 2 (per-quantile return volatility), Dimension 3 (turnover).

**Minimal fix (recommended):** extend `save_run` to also write two lean parquets
per arm in the same per-run dir:

```
oos_state.parquet  oos_base.parquet   # [date, ticker, score, y_fwd_ret] — the full OOS panel
# OR, to keep artifacts small (≈ n_months × n_quantiles rows instead of n_months × n_tickers):
quantile_state.parquet  quantile_base.parquet   # [date, quantile, mean_score, mean_ret, n]
```

Prefer persisting the **full panel** (`oos_*.parquet`): it is the single artifact
that unlocks the most charts (scatter, quantile spread, per-quantile vol,
turnover, and event-study alignment), and at ~125 months × ~500 tickers × 4 cols
it is only a few MB of parquet. Persisting **quantile aggregates** as well is a
cheap cache for the quantile-spread bar. The full panel is PIT-safe by
construction (it is the OOS output of a purged-CV run) — no new leakage risk.

### Gap 2 — the monthly L-S return *series* is not stored

The `phase:"strategy_return"` ledger row stores only **scalars** per strategy
(`sharpe_annualized`, `dsr_by_trials`, `n_months`). The monthly return vector is
dropped.

**Blocks:** Dimension 3 (cumulative L-S equity curve), Dimension 2 (strategy
max-drawdown / drawdown curve).

**Minimal fix:** when the strategy-return eval runs, persist
`runs/results/<sig>/ls_returns.parquet` (wide `[date, <strategy>…]` monthly
returns) alongside the ledger row, and add a `results.load_ls_returns()` reader.
This is the same parquet pattern `ic_*.parquet` already uses.

### Gap 3 — no event-study artifacts exist

Nothing computes or persists cumulative abnormal returns (CAR) around events.
13D filings (`data/cache/phase_d/<ticker>.json`, PIT via `filing_date`),
earnings-release dates (from `features.earnings_surprise`), and macro-surprise
dates (CPI/NFP via ALFRED, VIX via FRED) are all available as event timestamps,
and daily prices live in `data/cache/prices` — but the CAR pipeline that joins
them does not exist yet.

**Blocks:** Dimension 4 entirely.

**Minimal fix:** a new `eval/event_study.py` (see §6) that, for each event type,
aligns a `t−k..t+k` window of daily returns around each event, estimates a
"normal" return benchmark, computes CAR(t) = Σ AR, and bootstraps a CI band;
persist `car_<event_type>.json` per run (or as its own `phase:"event_study"`
ledger row, mirroring `strategy_return`).

> All three fixes are **additive** — they add artifacts + readers; they do not
> change any existing confirmatory result or its sha256. The existing IC-based
> claims and the ledger are untouched.

---

## 2. The five dimensions

Each dimension below lists: the **metrics** (with a one-line economics meaning),
the **chart type(s)** (all native plotly — no new viz dep), the **data source**
(artifact + eval function), and the **standard reference**.

### Dimension 1 — Fit quality (拟合质量)

*How well do the OOS scores predict cross-sectional returns?*

| Metric | Economics meaning (one line) | Source |
|---|---|---|
| **Cumulative IC** | cumsum of monthly rank-IC — a steady upward ramp = a consistently predictive signal | `ic_state`/`ic_base` series |
| **Mean IC + Newey-West t** | average cross-sectional rank correlation of score vs forward return, HAC-corrected for autocorrelation | `summary_*.json` (`mean_ic`, `t_hac`) |
| **IC-IR** (information ratio) | `mean(IC) / std(IC)` — Sharpe-analog for a signal; the Grinold-Kahn skill gauge | compute from IC series (or `|mean_ic|/se_hac`) |
| **IC hit-rate** | `%` of months with `IC > 0` — directional consistency, sign-only robustness | compute from IC series |
| **Score-vs-forward-return scatter + Spearman ρ** | the cross-sectional relationship itself; Spearman ρ = the per-month IC pooled | `oos_*.parquet` (Gap 1) |
| **Quantile/decile spread** (top − bottom mean return) | the tradeable long-short edge per quantile bucket; monotone ramp = a real signal | `oos_*.parquet` / `quantile_*.parquet` (Gap 1) |
| **R²-ish** (linear fit score→return) | share of cross-sectional return variance the score linearly explains | `oos_*.parquet` (Gap 1) |

**Charts (plotly):**
1. **Cumulative-IC line** (state vs base, dual line) with the `0` reference — the headline "is it predictive" ramp.
2. **KPI tile row**: mean IC, NW t, IC-IR, hit-rate (per arm), with the publishability CI-half gate as a tile-color cue.
3. **Score-vs-forward-return scatter** (pooled across OOS months, alpha-blended; optional per-month facet) + a LOESS/Spearman annotation.
4. **Quantile-spread bar** (alphalens-style): mean forward return per quantile bucket (Q1…Q5/decile), top−bottom spread annotated — *the* factor-analysis chart.

**Reference:** Grinold & Kahn, *Active Portfolio Management* (IC, IR, Fundamental Law); **alphalens** `create_returns_tear_sheet` / `create_information_tear_sheet` (IC by quantile, quantile spread — the direct template for chart 4).

### Dimension 2 — Volatility structure (波动结构)

*Is the edge stable, or clustered / fat-tailed / drawdown-prone?*

| Metric | Economics meaning (one line) | Source |
|---|---|---|
| **Rolling IC volatility** | 12-month rolling std(IC) — whether predictive stability decays over time | IC series |
| **IC distribution / histogram** | shape of the monthly IC — symmetric/narrow vs fat-tailed/skewed | IC series |
| **Return volatility per quantile** | does risk concentrate in the long/short legs? does vol line up with the spread? | `oos_*.parquet` / `quantile_*.parquet` (Gap 1) |
| **Max drawdown + drawdown curve** | peak-to-trough decline of cumulative IC (or the L-S equity curve) | IC series or `ls_returns.parquet` (Gap 2) |
| **Vol clustering** | rolling-vol of IC — periods of calm vs turmoil (GARCH-like persistence, eyeballed) | IC series |

**Charts (plotly):**
1. **IC histogram** (state vs base, overlaid) + a normal-density overlay and the mean line.
2. **Rolling-12m IC-vol line** (state vs base) — stability-over-time view.
3. **Per-quantile return-volatility bar** (vol of forward return within each quantile bucket).
4. **Drawdown curve** (underwater plot): cumulative IC (or L-S equity) measured from its running max; max-DD annotated.

**Reference:** **pyfolio** `create_drawdown_tear_sheet` (underwater plot) + `create_returns_tear_sheet` (return distribution). Drawdown/vol formulas per **empyrical** (`max_drawdown`, `annual_volatility`).

### Dimension 3 — Curve evolution (曲线演化)

*How does performance accumulate, and does it drift?*

| Metric | Economics meaning (one line) | Source |
|---|---|---|
| **Cumulative IC curve + CI band** | the running sum of IC with a bootstrap CI ribbon — the "equity curve of the signal" | IC series + `block_bootstrap` |
| **Cumulative long-short equity curve** | compounding of the tradeable L-S portfolio — money curve | `ls_returns.parquet` (Gap 2) |
| **Rolling (12-m) IC + rolling IC-IR over time** | whether recent performance is fading or strengthening | IC series |
| **Turnover** | period-over-period quantile/rank migration — the trading-cost exposure | `oos_*.parquet` (Gap 1) |

**Charts (plotly):**
1. **Cumulative IC + CI band**: line with a shaded MBB-bootstrap 95% ribbon; `0` reference.
2. **Cumulative L-S equity curve** (log-y option), state vs base vs placebo — the tradeable counterpart to chart 1.
3. **Rolling IC + rolling IC-IR** (dual-axis, 12-m window) — drift/fade detector.
4. **Turnover line**: average quantile-migration (or rank-correlation of consecutive month scores) over time.

**Reference:** **pyfolio** returns tearsheet; **quantstats** equity-curve framing.

### Dimension 4 — Pre/post-event differences — EVENT STUDY (事件前后差异)

*Do returns behave differently around real-world events?*

This is the **new build** (Gap 3). Event types (selectable in the UI):
- **13D activist filings** — `data/cache/phase_d/<ticker>.json`, PIT via `filing_date` (the Phase D relationship event).
- **Earnings releases** — dates from `features.earnings_surprise` (earnings-surprise non-zero dates).
- **Macro surprises** — CPI/NFP release dates (ALFRED) + VIX-surprise dates (FRED).

| Metric | Economics meaning (one line) | Source |
|---|---|---|
| **CAR(t)** = Σ_{τ=t0−k}^{t} AR(τ) | cumulative abnormal return over a `t−k..t+k` event window; the post-event drift | new `eval/event_study.py` |
| **Abnormal return AR** = R_realized − R_normal | return above a benchmark ("normal" return) — market model or simple mean | daily prices `data/cache/prices` + event timestamps |
| **CAR CI band** | bootstrap (or cross-event) 95% interval on the CAR path | `block_bootstrap` over event residuals |
| **Event vs non-event CAR** | does the CAR path of event firms differ from a matched non-event control? | same, with a control set |

**Charts (plotly):**
1. **CAR path** over `t−k..t+k` (e.g. t−20..t+40 sessions) with a 95% CI ribbon; `0` at `t=0`; vertical line at the event date. **Event-type selector drives this chart.**
2. **Event vs non-event overlay**: two CAR paths ± CI on the same axes.
3. **Per-event-type CAR summary bar**: end-of-window CAR ± CI for 13D / earnings / macro side by side.

**Methodology / references:** Brown & Warner (1980, 1985) — market-model event study; Boehmer, Musumeci & Poulsen (1991) — standardized-abnormal-return inference; MacKinlay (1997) — event-study survey. Use the simple **market model** (or constant-mean) benchmark on daily returns; the project already fetches Mkt-RF via `features.selection_panel.fama_french_daily`.

> PIT note: events are anchored on immutable filing/release dates (13D `filing_date`, ALFRED vintage date, FRED release date) — strictly G3-safe. The event-study is **exploratory** (a methods demo), not a confirmatory claim, until registered.

### Dimension 5 — Uncertainty (不确定性)

*How tight is the inference — and is it publishable?*

| Metric | Economics meaning (one line) | Source |
|---|---|---|
| **Newey-West HAC CI on IC + differential** | the 95% interval on the mean, robust to serial correlation | `summary_*.json`, `differential.json` (`se_hac`, `ci_half`, `ci_lo`, `ci_hi`) |
| **Bootstrap CIs (MBB-DM)** | non-parametric CI on the IC mean / the two-arm differential, robust at small n | `diebold_mariano_mbb`, `block_bootstrap` |
| **Prediction / forecast interval** | MBB interval for "next-period" IC / differential | `block_bootstrap` on the IC series |
| **Publishability CI-half-width gate** | pre-reg §7: a null is "publishable" only when `ci_half < 0.015` | `differential.publishable_ci_half` / `ci_half` |
| **DSR / haircut sensitivity** | does the Sharpe survive deflation by the # of trials searched? | `deflated_sharpe`, `harvey_liu_haircut` (already drawn in current Robustness tab) |

**Charts (plotly):**
1. **CI-half-width bar across phases** (B/C/D/E1) vs the `0.015` gate line — the at-a-glance "what is publishable" chart.
2. **Differential forest plot**: mean_diff + 95% CI per arm/control (headline, lag_shift, placebo, leave-one-out), sorted; `0` reference. This generalizes the current differential chart into a multi-row forest plot.
3. **Bootstrap/MBB-DM distribution**: histogram of the bootstrap differential mean with the observed value + the HAC-CI overlay.
4. **DSR / haircut sensitivity** (carried over from the current Robustness tab): haircut-Sharpe vs `n_trials`.

**References:** Newey & West (1987) HAC; Künsch (1989) moving-block bootstrap; Politis & White (2004) block-length rule (both already coded in `eval.metrics`); Bailey & Lopez de Prado (2014) DSR (already in `eval.multiple_testing`); Harvey & Liu haircut.

---

## 3. Chart suite + interaction structure

### Global sidebar (cross-cutting filters)

```
Phase       : [B | C | D | E1]      -> maps to the phase's confirmatory:first config_sig
Arm (signal): [state/enhanced | base] (Phase E1: prop vs base_self)
Horizon     : [10 | 21 | 42]        -> sensitivity_horizon ledger row (21 = frozen confirmatory)
Event type  : [13D | earnings | macro] (drives the Event Study tab only)
```

- **Phase selector** picks the run dir (`results.load_run(config_sig)`); the
  phase→sig map comes from the ledger `confirmatory:first` rows. E1 renames
  arms (`arm_prop` vs `arm_base_self`) — the arm selector labels adapt.
- **Horizon selector** default = `21` (the frozen confirmatory horizon); `10`/`42`
  read the `sensitivity_horizon` ledger row and clearly badge the view
  **EXPLORATORY** (h≠21 = changed config, not a confirmatory result).
- **Event-type selector** only affects the Event Study tab.

### Tab layout (8 tabs)

Retain the two supporting tabs; add the five dimension tabs.

| Tab | Status | Drives |
|---|---|---|
| **Fit Quality** | NEW | Dimension 1 |
| **Volatility** | NEW | Dimension 2 |
| **Evolution** | NEW | Dimension 3 |
| **Event Study** | NEW | Dimension 4 |
| **Uncertainty** | NEW (extends current "Selected run" + "Robustness") | Dimension 5 |
| Run history | retained | ledger table |
| Coverage | retained | universe / Jaccard |
| Strategy Return | retained | L-S Sharpe / DSR / SPA-MCS (now also feeds Evolution's L-S curve) |

Every dimension tab carries a persistent caption:
*"Preliminary data — demonstrates the method, not a final conclusion."*
and surfaces the publishability gate (`ci_half < 0.015`) as a recurring visual cue.

---

## 4. OSS recommendation (license-verified)

The project is **permissive-only** (MIT / Apache-2.0 / BSD / CC0). Licenses
verified via `gh api repos/.../license` (SPDX IDs), not assumed.

| Library | License | Visualizes | **Decision** |
|---|---|---|---|
| **alphalens / alphalens-reloaded** (`quantopian` / `stefan-jansen`) | **Apache-2.0** ✓ | factor analysis: IC by quantile, quantile spread, IC time series, turnover, IC-IR — *the* template for Dimension 1 | **Reuse the methodology, implement in plotly.** matplotlib-based → its figures do not compose into Streamlit/plotly tabs. |
| **pyfolio-reloaded** (`stefan-jansen`) | **Apache-2.0** ✓ | tearsheet: returns, drawdown (underwater), rolling Sharpe/vol, return distribution | **Reuse the chart shapes, implement in plotly** (Dim 2/3). Same matplotlib-mismatch reason. |
| **quantstats** (`ranaroussi`) | **Apache-2.0** ✓ (current default branch; the historical Commons-Clause overlay is gone) | headline-KPI + tearsheet HTML report | **Reuse the KPI-framing concept only.** The README already notes residual license ambiguity → do not add as runtime dep. |
| **empyrical** (`quantopian`) | **Apache-2.0** ✓ | pure-python risk metrics: `max_drawdown`, `annual_volatility`, `sortino`, `calmar`, `omega`, `tail_ratio` | **Optional lightweight dep.** These are ~20 lines of numpy each; implement directly and cite empyrical formulas (KISS/YAGNI). Add the dep only if the builder prefers battle-tested implementations. |
| **zipline-reloaded** (`stefan-jansen`) | **Apache-2.0** ✓ | backtesting engine | **Not relevant** (we have OOS panels, not a live backtester). Skip. |
| **mlfinlab** (`hudson-and-thames`) | **NOASSERTION / "Other"** ✗ | DSR, PBO, backtesting | **REJECT.** Non-permissive (custom/restrictive license). The project already ports the needed DSR/haircut/PBO math from `purgedcv` (Apache-2.0-equivalent NCSA) + its own CC0 ports. |

**Bottom line — add ZERO new runtime deps by default.** Streamlit + plotly
(both already deps) + the existing `eval/*` machinery cover all 5 dimensions.
Implement the charts in native plotly, using alphalens/pyfolio/empyrical as the
**methodological templates** (chart shapes + metric definitions). The only
candidate dep is `empyrical` (Apache-2.0), and only if the builder wants
battle-tested drawdown/Sortino instead of ~20 lines of numpy.

This matches the existing project philosophy (the v1 dashboard README evaluates
these libs "for patterns, not installs, to keep the runtime dependency footprint
minimal, per KISS/YAGNI").

---

## 5. Build plan

### 5.1 Data layer (do first — unblocks Dims 1–4)

**`src/aionis/reporting/results.py`** — extend `save_run` + `load_run`:
- Add optional `oos_state` / `oos_base` (`pd.DataFrame[date, ticker, score, y_fwd_ret]`)
  → write `oos_state.parquet` / `oos_base.parquet`; load them back in `load_run`.
- Add optional `quantile_state` / `quantile_base` (lean aggregate
  `[date, quantile, mean_score, mean_ret, n]`) → `quantile_*.parquet`.
- Add `load_ls_returns(config_sig)` reading a new `ls_returns.parquet`
  (wide `[date, <strategy>…]`), written by the strategy-return runner.

Keep everything optional + backward-compatible (existing runs without these
artifacts simply disable the dependent charts with an honest "data not persisted
for this run" notice — no crash).

**`scripts/phase_*_run.py`** — when calling `save_run`, also pass the `oos_*`
panels the orchestrator already builds (Phase C `_arm_ic` already returns the
panel; Phase D/E1 similarly). No recomputation — just don't drop it.

**NEW `src/aionis/eval/event_study.py`** — the CAR pipeline (Gap 3):
```python
def car_path(event_dates, prices, benchmark, window=(-20, +40), ...) -> dict
#   - align daily returns around each event date over `window`
#   - AR = realized_ret - benchmark_ret (market model via fama_french_daily Mkt-RF,
#     or constant-mean)
#   - CAR(t) = cumsum of mean AR across events up to t
#   - CI band via block_bootstrap over event-residuals (or cross-event SE)
#   - optional non-event control set (matched tickers, same window) -> comparison path
```
Outputs `car_<event_type>.json` (`{window, car: [...], ci_lo, ci_hi, n_events}`)
per run, or a `phase:"event_study"` ledger row (mirrors `strategy_return`).

### 5.2 Dashboard layer — `dashboard/app.py`

- **Sidebar**: replace the single "result dir" selectbox with the **Phase / Arm /
  Horizon / Event-type** filter cluster (§3). Phase→sig map from the ledger.
- **Five dimension views** (`view_fit_quality`, `view_volatility`, `view_evolution`,
  `view_event_study`, `view_uncertainty`), each a composition of plotly figures
  built from the loaded run + the new artifacts. Reuse the existing
  `_publishability_badge` + the `±0.015` gate overlay as a shared helper.
- **Chart helpers** (new, all plotly `go.Figure`): `_cumulative_ic_chart`,
  `_quantile_spread_chart`, `_score_scatter`, `_ic_histogram`,
  `_rolling_vol_chart`, `_drawdown_chart`, `_cumulative_ls_equity`,
  `_car_path_chart`, `_ci_halfwidth_bar`, `_forest_plot`,
  `_bootstrap_distribution`. Keep each <50 lines (coding-style rule).
- **Reuse, don't rewrite**: all inference flows through `eval.rank_ic`,
  `eval.metrics`, `eval.multiple_testing`, `eval.strategy_returns`,
  `eval.event_study`. The dashboard is a *reader + plotter*, never a recompute
  engine (preserves H6 determinism + the anti-leakage discipline).
- **Honest-no-data guards**: every chart that needs a Gap-1/2/3 artifact must
  check for its presence and show an actionable notice ("run the v2 artifact
  writer for this phase") instead of a broken chart — so the dashboard still
  renders on today's preliminary data.

### 5.3 Build order (each slice demoable on current data)

1. **Sidebar filter cluster** + Phase→sig mapping (no new data needed; works on existing IC series).
2. **Uncertainty tab** (mostly reuses existing JSON; forest plot + CI-half-width bar across phases). Fully works today.
3. **Volatility tab** (IC histogram + rolling vol + drawdown from IC series). Fully works today.
4. **Evolution tab** (cumulative IC + CI band from IC series; L-S equity + turnover gated on Gaps 1–2). Partial today, full after Gaps 1–2.
5. **Fit Quality tab** (cumulative IC + KPIs work today; scatter + quantile spread gated on Gap 1). Partial today, full after Gap 1.
6. **Event Study tab** (gated on Gap 3). Add `eval/event_study.py` first.
7. Data-layer artifacts (Gaps 1–3) can land in parallel with slices 4–6.

---

## 6. References

**Methodology**
- Grinold, R. & Kahn, R. — *Active Portfolio Management* (IC, IR, Fundamental Law).
- Newey, W. & West, K. (1987) — HAC covariance (already in `eval.rank_ic.rank_ic_summary`).
- Künsch, H. (1989) — moving-block bootstrap; Politis & White (2004) — block-length rule (both in `eval.metrics`).
- Bailey, D. & Lopez de Prado, M. (2014) — Deflated Sharpe Ratio (in `eval.multiple_testing`).
- Harvey, C. & Liu, Y. — haircut Sharpe (Bonferroni/Holm; in `eval.multiple_testing`).
- Brown, S. & Warner, J. (1980, 1985); Boehmer, Musumeci & Poulsen (1991); MacKinlay (1997) — event-study methodology (for the new `eval/event_study.py`).

**OSS (license-verified via `gh api`, 2026-07-29)**
- alphalens / alphalens-reloaded — Apache-2.0 (factor-analysis template, Dim 1).
- pyfolio-reloaded — Apache-2.0 (tearsheet shapes, Dim 2/3).
- quantstats (ranaroussi) — Apache-2.0 (KPI framing; Commons-Clause overlay gone).
- empyrical (quantopian) — Apache-2.0 (drawdown/Sortino formulas, Dim 2).
- zipline-reloaded — Apache-2.0 (not relevant here).
- mlfinlab (hudson-and-thames) — NOASSERTION/"Other" → **rejected** (non-permissive).

**Project-internal (reuse surface)**
- `dashboard/app.py` (current 5-tab app), `dashboard/README.md` (reuse accounting).
- `src/aionis/reporting/results.py` (`save_run`/`load_run`/`list_runs`/`read_ledger`).
- `src/aionis/eval/{rank_ic,metrics,multiple_testing,strategy_returns,two_arm}.py`.
- `docs/RESULTS.md` (the metrics in use), `docs/phase-{b,c,d,e}-preregistration.md`.
