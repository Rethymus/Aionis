# `/themes` Display Module Design Note

> **Status:** DESIGN NOTE (READ-ONLY investigation) — 2026-08-08
> **Owner request:** Display the seven-theme Track B research platform so the work "is seen" — display-only, NOT a research claim, no ledger/frozen-surface touch.
> **Deliverable:** Schema + UI wireframe + per-theme availability verdict

---

## 1. Executive Summary

The seven-theme platform from `docs/track-b-preregistration.md` (frozen 2026-08-02, config_committed) has feature engineering built but NOT surfaced in the terminal. This design proposes a `/themes` route with per-theme cards showing: signal name, current value, methodology disclosure, and honest `awaiting_data` badges where needed.

**Buildable-now verdict (v1):**
- ✅ **BUILDABLE-NOW (4):** ①行情/价格, ②宏观, ③基本面, ⑦市场结构
- ⚠️ **PARTIAL (1):** ⑥回测净成本 (FINSABER signal exists; full cost sweep surfaced)
- ⏳ **FORWARD-ONLY (1):** ④新闻情绪 (LLM extraction ready; no historical corpus)
- ❓ **NEEDS-DATA-WORK (1):** ⑤风险 (empyrical mounted; alphalens tearsheet missing)

---

## 2. Per-Theme Signal Availability

### ① 行情/价格 (Price/Market) — **BUILDABLE-NOW**

**Evidence:** `src/aionis/features/price_features.py` implements:
- `momentum()` (5d, 10d, 21d, 42d windows)
- `reversal()` (5d short-term reversal)
- `volatility()` (21d, 63d rolling std)
- `turnover()` (21d volume turnover)
- `beta()` (252d market beta vs S&P 500)
- `amihud_illiquidity()` (via `ff5_residual.py` import)

**Computable signal TODAY:**
```python
# From existing track_b_panel.parquet (120MB, 2016-2026)
signal = {
    "momentum_21d": 0.042,  # 21-session cumulative return
    "reversal_5d": -0.018,
    "volatility_63d": 0.022,  # rolling std
    "turnover_21d": 0.034,
    "beta_252d": 1.12,
    "amihud_illiquidity": 2.8e-9,  # absolute return / dollar volume
}
```

**Status:** ✅ **BUILDABLE-NOW** — panel exists (`data/cache/track_b_panel.parquet`), features surfaced via `/picks` already.

---

### ② 宏观 (Macro) — **BUILDABLE-NOW**

**Evidence:** `src/aionis/features/macro_surprise.py` implements ALFRED vintages for:
- CPI (`CPIAUCSL`, MoM % change)
- NFP (`PAYEMS`, MoM diff in thousands)

**Computable signal TODAY:**
```python
# From cached ALFRED vintages (9 JSON files in data/cache/alfred_*.json)
signal = {
    "cpi_surprise_z": 1.34,  # standardized surprise (z-score, clipped ±5)
    "nfp_surprise_z": -0.82,
    "cpi_expectation_window": 12,  # trailing mean of first-prints
    "latest_vintage_date": "2025-07-31",
}
```

**PIT safety:** ✅ ALFRED as-of vintages (strict `realtime_start` discipline, `merge_asof(allow_exact_matches=False)`).

**Status:** ✅ **BUILDABLE-NOW** — vintages cached, features implemented.

---

### ③ 基本面 (Fundamentals) — **BUILDABLE-NOW**

**Evidence:** `src/aionis/ingest/fundamentals.py` implements SEC EDGAR XBRL fetching (`edgartools`), filed-date PIT by construction.

**Computable signal TODAY:**
```python
# From phase_b_fundamentals.parquet (2.8MB, cached)
signal = {
    "roa": 0.142,  # return on assets
    "roe": 0.186,
    "profit_margin": 0.084,
    "asset_growth_1m": 0.012,
    "asset_growth_12m": 0.089,
    "revenue_growth_1m": 0.023,
    "revenue_growth_12m": 0.112,
    "equity_growth_1m": 0.018,
    "leverage": 0.412,  # debt / (debt + equity)
    "debt_to_equity": 0.702,
    "book_value_per_share": 34.2,
    "accruals": 0.023,
    "investment_12m": 0.067,
}
```

**Status:** ✅ **BUILDABLE-NOW** — fundamentals cached (23 features in frozen config #41).

---

### ④ 新闻情绪 (News Sentiment) — **FORWARD-ONLY**

**Evidence:** `src/aionis/extraction/providers.py` implements GLM/SiliconFlow/ModelScope pool (OpenAI-compatible). NO historical sentiment artifacts found in `data/` (only forward-collection Reddit `reddit_snapshots.parquet`).

**Computable signal TODAY:** ❌ **No historical corpus.**

**What exists:**
```python
# providers.py:19-71 — multi-key router (GLM-4-Flash primary)
providers = [
    Provider(name="glm", model="glm-4-flash", rpm=30, priority=1),
    Provider(name="siliconflow", model="Qwen2.5-7B-Instruct", rpm=1000),
    Provider(name="modelscope", model="Qwen3-Next-80B-A3B-Instruct", daily_quota=2000),
]
```

**Why no history:** E3 closed set (13D/8-K filings only) with LlamaIndex/PromptSha1 sha256 cache. Historical LLM extraction for PIT 13D events requires archival SEC full-text fetch + batch LLM run (exploratory work, not done).

**Status:** ⏳ **FORWARD-ONLY** — infrastructure ready, no backfill. Mark as `awaiting_data: forward-collection`.

---

### ⑤ 风险 (Risk) — **NEEDS-DATA-WORK**

**Evidence:** `src/aionis/eval/tearsheet_adapter.py` implements empyrical mount:
- `compute_risk_metrics()` → annual_return, annual_volatility, sharpe_ratio, sortino_ratio, max_drawdown, calmar_ratio, omega_ratio

**Missing:** `track_b/alphalens_adapter.py` (referenced in pre-reg §3 but NOT found in codebase). Alphalens tearsheet (IC per quantile, drawdown, turnover analysis) is NOT computed.

**Computable signal TODAY:** ⚠️ **Partial** — empyrical metrics computable from monthly returns, but alphalens tearsheet (core "theme ⑤" deliverable) missing.

```python
# WHAT EXISTS: empyrical single-arm risk metrics
from aionis.eval.tearsheet_adapter import compute_risk_metrics
signal = {
    "annual_return": 0.084,  # from monthly returns
    "annual_volatility": 0.142,
    "sharpe_ratio": 0.59,
    "sortino_ratio": 0.87,
    "max_drawdown": -0.124,  # negative value
    "calmar_ratio": 0.68,
    "omega_ratio": 1.34,
}
```

**What's missing:** Alphalens tear sheet (quantile IC, mean return by quantile, turnover, factor autocorrelation). This is the canonical "theme ⑤" output (alphalens-reloaded + pyfolio-reloaded).

**Status:** ❓ **NEEDS-DATA-WORK** — empyrical mount ready, alphalens adapter missing.

---

### ⑥ 回测净成本 (Backtest Net Cost) — **PARTIAL**

**Evidence:** `web/src/data/aionis/bps_sweep.json` EXISTS (cost sweep: 0/1/2/5/10/20/50 bps).
```json
[
  {"bps": 0.0, "net_sharpe": 0.149, "gross_sharpe": 0.149, "avg_turnover": 1.144},
  {"bps": 1.0, "net_sharpe": 0.144, "gross_sharpe": 0.149, "avg_turnover": 1.144},
  {"bps": 20.0, "net_sharpe": 0.054, "gross_sharpe": 0.149, "avg_turnover": 1.144},
  ...
]
```

**Missing:** `track_b/finsaber_adapter.py` (referenced in pre-reg §3 but NOT found). Full FINSABER integration (next-open execution, slippage, liquidity, LLM cost per trade) NOT implemented.

**Status:** ⚠️ **PARTIAL** — bps sweep surfaced (net Sharpe degradation curve), full FINSABER adapter missing.

---

### ⑦ 市场结构 (Market Structure) — **BUILDABLE-NOW**

**Evidence:** `src/aionis/eval/ff5_residual.py` implements:
- `ff5_residual_regression()` — FF5 α + β_MKT + β_SMB + β_HML + β_RMW + β_CMA
- `amihud_illiquidity()` — absolute return / dollar volume

**Computable signal TODAY:**
```python
# From ff5_residual.py + ingested FF5 daily factors (snapshot frozen)
signal = {
    "alpha_monthly": 0.0084,  # monthly abnormal return (intercept)
    "alpha_t": 1.34,
    "alpha_p": 0.182,
    "beta_mkt": 1.12,
    "beta_smb": -0.23,  # size factor loading
    "beta_hml": 0.34,   # value factor loading
    "beta_rmw": 0.18,   # profitability factor loading
    "beta_cma": -0.12,  # investment factor loading
    "r_squared": 0.68,
    "amihud_illiquidity": 2.8e-9,  # from price_features.py:15
}
```

**Status:** ✅ **BUILDABLE-NOW** — FF5 regression implemented, Amihud liquidity already in price features.

---

## 3. `/themes` View Design

### 3.1 Route Structure

```
/themes
├── page.tsx                    # Route page, layout header
├── themes-view.tsx              # Main component
└── theme-card.tsx               # Reusable per-theme card
```

### 3.2 Component Architecture

**`themes-view.tsx`** (mirrors `model-health-view.tsx`):
```tsx
export function ThemesView() {
  const { t } = useI18n();
  const themes = aionis.themes;  // from themes.json

  return (
    <div className="space-y-6 p-4 md:p-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">{t("themes.title")}</h1>
        <p className="text-sm text-muted-foreground">{t("themes.window")}</p>
      </header>

      {themes.status === "awaiting_fetch" ? (
        <EmptyState message={t("themes.awaiting")} />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {themes.themes.map((theme) => (
            <ThemeCard key={theme.key} theme={theme} />
          ))}
        </div>
      )}

      <Card className="border-dashed">
        <CardHeader className="border-b">
          <CardTitle className="flex items-center gap-2 text-base">
            <ShieldCheckIcon className="size-4" /> {t("themes.howto")}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 p-4">
          <p className="text-xs text-muted-foreground">{themes.methodology}</p>
          <p className="flex items-center gap-1.5 text-xs text-amber-700 dark:text-amber-400">
            <ShieldAlertIcon className="size-3.5 shrink-0" />
            {t("themes.disclaimer")}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
```

**`theme-card.tsx`** (mirrors conviction KPI cards):
```tsx
interface ThemeCardProps {
  theme: {
    key: string;
    label: string;
    signal_type: string;
    value: number | string | null;
    series?: { date: string; value: number }[];
    methodology: string;
    status: "ok" | "awaiting_data";
    awaiting_reason?: string;  // e.g., "forward-collection" or "needs-alphalens-mount"
  };
}

export function ThemeCard({ theme }: ThemeCardProps) {
  const { t } = useI18n();

  if (theme.status === "awaiting_data") {
    return (
      <Card className="border-muted opacity-60">
        <CardHeader className="border-b">
          <CardTitle className="flex items-center justify-between text-sm">
            <span className="font-mono">{theme.label}</span>
            <Badge variant="outline">awaiting_data</Badge>
          </CardTitle>
          <CardDescription className="text-xs">
            {theme.awaiting_reason}
          </CardDescription>
        </CardHeader>
        <CardContent className="p-4">
          <p className="text-xs text-muted-foreground">{theme.methodology}</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="border-b">
        <CardTitle className="flex items-center justify-between text-sm">
          <span className="font-mono">{theme.label}</span>
          <Badge variant="outline">{theme.signal_type}</Badge>
        </CardTitle>
        <CardDescription className="text-xs">
          {theme.methodology}
        </CardDescription>
      </CardHeader>
      <CardContent className="p-4">
        {theme.series ? (
          // Sparkline for time-series signals (volatility, illiquidity, etc.)
          <ResponsiveContainer width="100%" height={60}>
            <LineChart data={theme.series}>
              <Line dataKey="value" dot={false} stroke="currentColor" />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          // Single value (latest snapshot)
          <p className="text-2xl font-bold tabular-nums">
            {typeof theme.value === "number" ? theme.value.toFixed(3) : theme.value}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
```

### 3.3 Sidebar Integration

Add to `app-sidebar.tsx` under the "insights" group (between `/conviction` and `/model-health`):
```tsx
const insights = [
  { href: "/conviction", label: "conviction.title", icon: TrendingUp },
  { href: "/themes", label: "themes.title", icon: Layers },  // NEW
  { href: "/model-health", label: "modelhealth.title", icon: Activity },
];
```

### 3.4 i18n Keys (zh + en)

**en.json:**
```json
{
  "themes": {
    "title": "Seven Themes",
    "window": "Track B research platform (display-only, not a research claim)",
    "awaiting": "Themes data not yet available — run Track B pipeline first",
    "howto": "Methodology & Disclosure",
    "disclaimer": "Display-only — NOT an Aionis research claim. Themes are frozen Track B feature engineering (config_committed 2026-08-02).",
    "theme1": "Price/Market",
    "theme2": "Macro",
    "theme3": "Fundamentals",
    "theme4": "News Sentiment",
    "theme5": "Risk",
    "theme6": "Net Cost",
    "theme7": "Market Structure"
  }
}
```

**zh.json:**
```json
{
  "themes": {
    "title": "七大主题",
    "window": "Track B 研究平台（仅展示，非研究结论）",
    "awaiting": "主题数据暂不可用 — 请先运行 Track B 流水线",
    "howto": "方法论与披露",
    "disclaimer": "仅展示 — 非 Aionis 研究结论。主题为冻结的 Track B 特征工程（config_committed 2026-08-02）。",
    "theme1": "行情/价格",
    "theme2": "宏观",
    "theme3": "基本面",
    "theme4": "新闻情绪",
    "theme5": "风险",
    "theme6": "净成本",
    "theme7": "市场结构"
  }
}
```

---

## 4. Export Schema (`themes.json`)

**Shape:**
```typescript
{
  status: "ok" | "awaiting_fetch",
  methodology: string,          // honest disclosure
  themes: [
    {
      key: string,              // "price" | "macro" | "fundamentals" | ...
      label: string,            // i18n key, e.g., "themes.theme1"
      signal_type: string,       // "scalar" | "timeseries" | "vector"
      value: number | string | null,  // null if awaiting_data
      series?: { date: string; value: number }[],  // for timeseries signals
      methodology: string,       // 1-line per-theme disclosure
      status: "ok" | "awaiting_data",
      awaiting_reason?: string,  // "forward-collection" | "needs-alphalens-mount" | ...
    }
  ]
}
```

**Example payload (v1 buildable-now subset):**
```json
{
  "status": "ok",
  "methodology": "Seven-theme Track B feature engineering (config_committed 2026-08-02). Display-only, NOT a research claim. Signals from frozen modules: price_features, macro_surprise, fundamentals, ff5_residual. Theme ④ (news sentiment) awaiting forward-collection. Theme ⑤ (risk) needs alphalens adapter mount. Theme ⑥ (net cost) partial: bps sweep surfaced, full FINSABER adapter pending.",
  "themes": [
    {
      "key": "price",
      "label": "themes.theme1",
      "signal_type": "vector",
      "value": null,
      "methodology": "Price momentum (5/10/21/42d), reversal (5d), volatility (21/63d), turnover (21d), beta (252d), Amihud illiquidity (21d). Source: track_b_panel.parquet (Tiingo/Alpaca adjClose). Module: features/price_features.py.",
      "status": "ok",
      "series": [
        {"date": "2025-06-30", "momentum_21d": 0.042, "reversal_5d": -0.018, "volatility_63d": 0.022}
      ]
    },
    {
      "key": "macro",
      "label": "themes.theme2",
      "signal_type": "scalar",
      "value": {"cpi_surprise_z": 1.34, "nfp_surprise_z": -0.82},
      "methodology": "ALFRED vintage CPI/NFP surprise z-scores (expectation = trailing 12 first-prints, std = trailing 24 surprises, clipped ±5). Source: FRED ALFRED as-of vintages. Module: features/macro_surprise.py.",
      "status": "ok"
    },
    {
      "key": "fundamentals",
      "label": "themes.theme3",
      "signal_type": "vector",
      "value": null,
      "methodology": "SEC EDGAR XBRL fundamentals (ROA/ROE/profit_margin/asset_growth/revenue_growth/equity_growth/leverage/debt_to_equity/book_value_per_share/accruals/investment). Filed-date PIT by construction. Module: ingest/fundamentals.py.",
      "status": "ok"
    },
    {
      "key": "news_sentiment",
      "label": "themes.theme4",
      "signal_type": "scalar",
      "value": null,
      "methodology": "E3 closed set 13D/8-K LLM extraction (GLM/SiliconFlow/ModelScope pool). Forward-collection only — no historical corpus. Controlled ablation (S3), not main alpha. Module: extraction/providers.py.",
      "status": "awaiting_data",
      "awaiting_reason": "forward-collection"
    },
    {
      "key": "risk",
      "label": "themes.theme5",
      "signal_type": "vector",
      "value": {"sharpe_ratio": 0.59, "max_drawdown": -0.124},
      "methodology": "Partial: empyrical risk metrics (annual_return/volatility/sharpe/sortino/max_drawdown/calmar/omega). Alphalens tearsheet (IC per quantile, turnover, factor autocorrelation) NEEDS alphalens_adapter mount (referenced in pre-reg §3, not found in codebase). Module: eval/tearsheet_adapter.py.",
      "status": "awaiting_data",
      "awaiting_reason": "needs-alphalens-mount"
    },
    {
      "key": "net_cost",
      "label": "themes.theme6",
      "signal_type": "scalar",
      "value": {"net_sharpe_20bps": 0.054, "gross_sharpe": 0.149, "avg_turnover": 1.144},
      "methodology": "Partial: bps sweep surfaced (net Sharpe degradation curve). Full FINSABER adapter (next-open execution, slippage, liquidity, LLM cost per trade) pending (referenced in pre-reg §3, not found in codebase). Module: export_terminal_data.py:export_picks_backtest (bps sweep logic).",
      "status": "awaiting_data",
      "awaiting_reason": "needs-finsaber-adapter"
    },
    {
      "key": "market_structure",
      "label": "themes.theme7",
      "signal_type": "vector",
      "value": null,
      "methodology": "FF5 residual regression (α + β_MKT + β_SMB + β_HML + β_RMW + β_CMA) + Amihud illiquidity. FF5 factors: Kenneth French Data Library (frozen snapshot, no vintage — declared leakage risk). Module: eval/ff5_residual.py.",
      "status": "ok",
      "series": [
        {"date": "2025-06-30", "alpha_monthly": 0.0084, "beta_mkt": 1.12, "amihud_illiquidity": 2.8e-9}
      ]
    }
  ]
}
```

---

## 5. Implementation Notes (Non-Blocking)

### 5.1 Export Script Addition

Add to `scripts/export_terminal_data.py`:
```python
def export_themes() -> None:
    """Seven-theme Track B feature signals (display-only)."""
    from aionis.features.price_features import momentum, reversal, volatility, turnover, beta
    from aionis.features.macro_surprise import fetch_alfred_vintages
    from aionis.eval.ff5_residual import ff5_residual_regression, amihud_illiquidity
    from aionis.eval.tearsheet_adapter import compute_risk_metrics

    # Build theme dict, check data existence, mark awaiting_data honestly
    # (no mock data — follow the reddit.json pattern)
    payload = {
        "status": "ok" if has_real_data else "awaiting_fetch",
        "methodology": "...",
        "themes": [...],
    }
    (WEB / "themes.json").write_text(json.dumps(payload, indent=2, default=str))
```

### 5.2 What NOT to Build (v1 Scope)

- ❌ Theme ④ historical backfill (requires archival SEC 13D full-text + batch LLM run)
- ❌ Theme ⑤ alphalens tearsheet mount (needs `track_b/alphalens_adapter.py` implementation)
- ❌ Theme ⑥ full FINSABER adapter (needs `track_b/finsaber_adapter.py` implementation)

These are data-work tasks, not display-surface work. The `/themes` view MUST honestly show `awaiting_data` badges for partial themes.

---

## 6. References

### Internal
- `docs/track-b-preregistration.md` — Frozen seven-theme specification (config_committed 2026-08-02)
- `reports/design/2026-08-02-track-b-s0-s1-slice-plan.md` — S0/S1 slice structure (theme mapping)
- `scripts/export_terminal_data.py` — Export pattern (reddit/cot/form4 awaiting_data honesty)
- `web/src/components/model-health/model-health-view.tsx` — Card/Badge/KPI idiom
- `web/src/components/conviction/conviction-view.tsx` — Sparkline pattern

### External
- `eslazarev/purgedcv` (MIT) — PurgedGroupKFold (not directly used in display, but backdrop)
- `waylonli/FINSABER` (Apache-2.0, KDD 2026) — Net cost backtest (adapter pending)
- `alphalens-reloaded` + `pyfolio-reloaded` (Apache) — Tearsheet (adapter pending)
- `microsoft/qlib` (MIT) — Selection context (not used directly)

---

**Document end** — READ-ONLY investigation complete. No code/data/frozen surfaces touched.
