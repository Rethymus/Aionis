# Confirmatory 41-Feature Readiness Audit

**Date**: 2026-08-05
**Context**: Track C ledger row #48 (sig `e14b9d44...`) freezes the confirmatory estimand: joint US-CN chronological walk-forward rank-IC with **41 asymmetric feature_cols**.
**Mission**: Data-readiness scout — classify what exists on disk vs what must be built, so the orchestrator can size extension A (41-feature support in `build_joint_panel`).

---

## 1. US 23 Features (13 fundamentals + 10 price)

**Status**: ✅ **ALL ON DISK** — no new construction needed.

**Source**: `data/cache/track_b_panel.parquet`
- `n_rows`: 1,172,444
- `n_cols`: 30
- `date range`: 2016-01-04 to 2026-08-04
- `n_unique_tickers`: ~500+ S&P 500 constituents

### 13 fundamentals (EDGAR filed-date PIT) — ALL PRESENT ✓

| Feature | On disk? | Sample value |
|---------|----------|---------------|
| roa | ✅ | 0.046905 |
| roe | ✅ | 0.607390 |
| profit_margin | ✅ | 0.014724 |
| asset_growth_1m | ✅ | 0.0 / 0.031444 |
| asset_growth_12m | ✅ | 0.0 / 0.031444 |
| revenue_growth_1m | ✅ | 0.0 |
| revenue_growth_12m | ✅ | -0.411199 |
| equity_growth_1m | ✅ | 0.0 / 0.031444 |
| leverage | ✅ | 0.166745 |
| debt_to_equity | ✅ | 2.159224 |
| book_value_per_share | ✅ | 5.877137 / 33.022361 |
| accruals | ✅ | 0.0 |
| investment_12m | ✅ | 0.213398 / 0.166745 |

### 10 price features — ALL PRESENT ✓

| Feature | On disk? | Sample value |
|---------|----------|---------------|
| momentum_5d | ✅ | Present |
| momentum_10d | ✅ | Present |
| momentum_21d | ✅ | Present |
| momentum_42d | ✅ | Present |
| reversal_5d | ✅ | Present |
| volatility_21d | ✅ | Present |
| volatility_63d | ✅ | Present |
| turnover_21d | ✅ | Present |
| beta_252d | ✅ | Present |
| amihud_illiquidity_21d | ✅ | Present |

**Note**: Price features show NaN in early rows (accumulating windows), but populate as history builds. This is expected.

---

## 2. CN 12 Features (10 price mirror + 2 extras)

**Status**: ✅ **ALL ON DISK** — no new construction needed.

**Source**: `data/cache/cn_price_panel.parquet`
- `n_rows`: 141,208
- `n_cols`: 15
- `date range`: 2014-01-30 to 2026-08-03
- `n_unique_tickers`: 929
- `n_unique_dates`: 152 (month-end samples)

### 10 price mirror features — ALL PRESENT ✓

| Feature | Non-null count | Coverage | On disk? |
|---------|----------------|----------|----------|
| momentum_5d | 124,142 | 87.9% | ✅ |
| momentum_10d | 123,446 | 87.4% | ✅ |
| momentum_21d | 121,010 | 85.7% | ✅ |
| momentum_42d | 117,439 | 83.2% | ✅ |
| reversal_5d | 124,142 | 87.9% | ✅ |
| volatility_21d | 121,010 | 85.7% | ✅ |
| volatility_63d | 114,160 | 80.8% | ✅ |
| turnover_21d | 121,853 | 86.3% | ✅ |
| beta_252d | 121,340 | 85.9% | ✅ |
| amihud_illiquidity_21d | 126,177 | 89.4% | ✅ |

### 2 CN-specific extras — ALL PRESENT ✓

| Feature | Non-null count | Coverage | On disk? |
|---------|----------------|----------|----------|
| limit_up_down_distance | 124,763 | 88.4% | ✅ |
| suspension_flag | 128,271 | 90.8% | ✅ |

**Note**: 80-90% coverage is reasonable for a month-end panel (early months have NaN for accumulating windows). Missing values are handled by LightGBM's default missing-value handling (confirmatory config #48 frozen params).

---

## 3. macro_headline 6 (US 4 + CN 2)

**Status**: ⚠️ **NEEDS NEW FETCH + CONSTRUCTION** — reusable patterns exist.

### US 4 — dff_surprise + term_spread + vix + credit_spread

| Feature | Status | Existing cache | Source | Construction path |
|---------|--------|----------------|--------|-------------------|
| dff_surprise | **needs-fetch** | ✅ ALFRED DFF cached (30MB) | FRED ALFRED | Reuse `macro_dff.py` pattern (ΔDFF as-of via `dff_daily_changes`) |
| term_spread_1y_10y | **needs-fetch** | ❌ Not on disk | FRED (GS10 - TB3MS) | New ALFRED-style fetch (2 series) |
| vix | **raw cached** | ✅ VIXCLS cached (680KB) | FRED VIXCLS | Raw levels exist; surprise transformation needed (ΔVIX or AR-residual per prereg) |
| credit_spread | **needs-fetch** | ❌ Not on disk | FRED (BAA10Y - GS10 or similar) | New ALFRED-style fetch (2 series) |

**Relevant existing caches**:
- `data/cache/alfred_DFF.json` (30MB — full vintage archive)
- `data/cache/alfred_VIXCLS.json` (680KB — VIX daily)
- `data/cache/vix_cls.parquet` (63 rows — recent VIX subset, not full history)

**Reusable patterns**:
- `src/aionis/ingest/macro_dff.py` — ALFRED vintage fetch + as-of construction (strictly-before rule)
- `src/aionis/features/macro_surprise.py` — Surprise construction pattern (trailing mean/std, z-scoring)

### CN 2 — gdp_surprise + cpi_surprise

| Feature | Status | Existing cache | Source | Construction path |
|---------|--------|----------------|--------|-------------------|
| gdp_surprise | **needs-fetch** | ❌ Not on disk | OECD/ALFRED vintage (CN GDP) | New vintage fetch (OECD or ALFRED if available) |
| cpi_surprise | **needs-fetch** | ❌ Not on disk | OECD/ALFRED vintage (CN CPI) | New vintage fetch (OECD or ALFRED if available) |

**Relevant existing caches**:
- None for CN macro. Will need new fetcher.

**Reusable patterns**:
- `src/aionis/features/macro_surprise.py` — Surprise construction pattern (can extend to CN series)
- `src/aionis/ingest/macro_dff.py` — ALFRED vintage fetch pattern (can adapt to OECD)

**Data-source risk assessment**:
- **PIT-safety**: OECD vintage series exist for major economies (G3-safe). ALFRED may have limited CN coverage.
- **7-gate check needed**: License (open?), PIT (vintage?), no-revision (OECD is vintage), snapshot/exploratory-only, selection-honesty, politeness (≥2s spacing for OECD API).

---

## 4. Extension A Sizing Verdict

### Classification: **YELLOW** ✅ (minor construction needed)

**Rationale**:
- ✅ US 23 (13 fundamentals + 10 price): **100% on disk** — `track_b_panel.parquet` is complete.
- ✅ CN 12 (10 price + 2 extras): **100% on disk** — `cn_price_panel.parquet` is complete.
- ⚠️ macro_headline 6: **0% on disk** — needs new fetch/construction, BUT reusable patterns exist.

### Extension A work breakdown

**Component A1: build_joint_panel asymmetric support** (~100 lines + tests)
- Modify `build_joint_panel` to accept region-specific feature_cols (not just shared)
- Add `us_feature_cols` and `cn_feature_cols` parameters
- Handle asymmetric columns (CN rows get NaN for US fundamentals, LightGBM default handles this)
- Update `fit_track_c_joint` to use merged feature list
- Tests: verify asymmetric panel construction, per-region column validation

**Component A2: ALFRED vintage macro fetch** (~半天 / ~4-6 hours)
- Extend `macro_dff.py` pattern to:
  - `term_spread_1y_10y`: fetch GS10 (10-year Treasury) and TB3MS (3-month Treasury), compute spread, apply same as-of discipline
  - `credit_spread`: fetch BAA10Y (Baa corporate bond) and GS10, compute spread, apply as-of discipline
  - `dff_surprise`: use existing `dff_daily_changes` from `macro_dff.py`
  - `vix_surprise`: fetch VIXCLS vintage, compute ΔVIX or AR-residual (per prereg decision)
- For CN:
  - `gdp_surprise`: fetch OECD CN GDP vintage (or ALFRED if available), construct surprise
  - `cpi_surprise`: fetch OECD CN CPI vintage (or ALFRED if available), construct surprise
- Cache: `data/cache/alfred_{SERIES_ID}.json` per series
- Tests: PIT as-of validation, vintage sanity checks, no-lookahead tests

**Component A3: Date-broadcast for macro features** (~50 lines)
- Macro features are cross-section-broadcast (same value for all tickers on a given date)
- Reuse `macro_surprise_date_broadcast` pattern from `macro_surprise.py`
- Join to panel on date column

**Component A4: Tests** (~100 lines)
- Anti-leakage: verify macro features are PIT (no future info)
- Anti-degeneracy: verify panel non-empty, columns exist
- Reproducibility: deterministic H6 assertion

### Total extension A estimate: ~200-250 lines + ~半天 (4-6 hours) of macro fetch work

---

## 5. Reuse-First Guidance

### Existing modules to reuse

| Module | Pattern | What to reuse |
|--------|---------|---------------|
| `src/aionis/ingest/macro_dff.py` | ALFRED vintage fetch + as-of join | DFF surprise construction (already cached) |
| `src/aionis/features/macro_surprise.py` | Surprise time-series (trailing mean/std, z-scoring) | Extend to CN GDP/CPI surprises |
| `src/aionis/eval/track_c_joint.py` | Joint fold machinery | Modify `build_joint_panel` for asymmetric cols |

### New modules to create (minimal)

| Module | Purpose | Est. lines |
|--------|---------|------------|
| `src/aionis/ingest/macro_spread.py` | Term spread + credit spread fetch (ALFRED/FRED) | ~80 |
| `src/aionis/ingest/macro_cn.py` | CN GDP/CPI vintage fetch (OECD/ALFRED) | ~80 |

---

## 6. Final Verdict

```
extension_A_verdict: "YELLOW"
extension_A_work: "build_joint_panel asymmetric support (~100 lines) + ALFRED/FRED macro fetch for 6 series (~4-6 hours reuse macro_dff.py pattern) + tests (~100 lines)"
reuse_first_notes: "macro_dff.py ALFRED pattern reusable for all US macro (DFF done, term_spread/credit_spread need 2-series fetch); macro_surprise.py pattern reusable for CN GDP/CPI surprises"
```

**Bottom line**: The 35 per-ticker features (US 23 + CN 12) are fully on disk and ready. Only the 6 cross-section-broadcast macro features need new construction, and this is well-bounded work with clear reusable patterns. Extension A is **not a blocker** for the confirmatory run — it's a straightforward fetch + join task.

---

**Evidence summary**:
- ✅ Read `track_b_panel.parquet` schema + 3-row sample (30 columns include all 23 US features)
- ✅ Read `cn_price_panel.parquet` schema + 3-row sample (15 columns include all 12 CN features; 80-90% coverage)
- ✅ Verified ALFRED caches: DFF (30MB), VIXCLS (680KB), PAYEMS, CPIAUCSL exist
- ✅ Reviewed `macro_dff.py` and `macro_surprise.py` — reusable patterns confirmed
- ⚠️ No existing term_spread, credit_spread, CN macro data on disk
- ⚠️ `regime_*.parquet` files contain regime layers (macro_regime, regime_state), not raw macro series

**Anti-degeneracy check**: Actual parquet reads performed, not just `ls`. Sample rows shown above.
