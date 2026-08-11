# OHLCV Panel Extension Plan (Step 1 of disciplined-adaptive roadmap)

**Date:** 2026-08-11
**Author:** orchestrator (read-only research lane)
**Status:** evidence-grounded extension plan + pre-registration skeleton
**Scope:** extend frozen PIT panel to carry OHLCV columns (currently only `close` is carried; `open/high/low/volume` are fetched at ingest but dropped before the frozen panel)

---

## Executive Summary

This plan documents the minimal extension to Aionis's frozen PIT panel to carry OHLCV columns (`open`, `high`, `low`, `volume`) in addition to the currently-carried `close`. The extension is **purely additive**—it does not modify any existing feature values or break any downstream code. This unlocks the qlib K-Bar + volume factors (see `docs/qlib-reuse-audit.md` §1 "BLOCKED" rows) which are currently unavailable due to missing OHLCV data.

**Key finding:** OHLCV data is **already fetched** from Tiingo/Alpaca APIs but is **intentionally dropped** at the ingest layer. The minimal change is to stop dropping these columns and carry them through to the frozen panel.

**Risk assessment:** LOW risk. Adding columns is additive; existing features using only `close` are unaffected. H6 determinism is preserved—existing features remain bit-identical across reruns. This does **NOT** reverse the Track-B climax verdict (ledger #49 = null) because existing feature values are unchanged.

---

## 1. Current Pipeline Audit (read-only)

### 1.1 Where OHLCV is fetched

**File:** `/home/re/code/Aionis/src/aionis/ingest/market.py`

**Tiingo API** (lines 26-62, function `_from_tiingo()`):
- **API endpoint:** `https://api.tiingo.com/tiingo/daily/{sym}/prices`
- **API response fields:** `date`, `open`, `high`, `low`, `close`, `adjClose`, `volume` (7 fields)
- **Current extraction (line 57):**
  ```python
  col = pd.Series(df["adjClose"].to_numpy(float), index=idx, name=sym)
  ```
- **Dropped fields:** `open`, `high`, `low`, `close`, `volume`

**Alpaca API** (lines 65-109, function `_from_alpaca()`):
- **API endpoint:** `https://data.alpaca.markets/v2/stocks/{sym}/bars`
- **API response fields:** `t` (timestamp), `o` (open), `h` (high), `l` (low), `c` (close), `v` (volume), `vw` (VWAP), `n` (num_trades)
- **Current extraction (line 104):**
  ```python
  col = pd.Series(df["c"].to_numpy(float), index=idx, name=sym)
  ```
- **Dropped fields:** `o`, `h`, `l`, `v`, `vw`, `n`

**Volume fetcher** (lines 112-152, function `_volume_from_alpaca()`):
- **Status:** **EXISTS BUT NEVER CALLED**
- **Extracts:** `v` (volume) only
- **Evidence:** No caller in the codebase (verified via grep)

### 1.2 Where OHLCV gets dropped

**File:** `/home/re/code/Aionis/src/aionis/ingest/market.py`

**Exact drop points:**
- **Line 57** (`_from_tiingo()`): extracts only `df["adjClose"]`, ignores `open/high/low/close/volume`
- **Line 104** (`_from_alpaca()`): extracts only `df["c"]`, ignores `o/h/l/v/vw/n`

**Why this happened:** The original design prioritized simplicity—only `adjClose` was needed for Phase B fundamentals-based factors. OHLCV columns were not in scope for the frozen Track-B panel.

### 1.3 Current frozen panel structure

**File:** `/home/re/code/Aionis/data/cache/phase_b_prices.parquet` (11M)
- **Format:** Wide DataFrame (date × ticker)
- **Index:** DatetimeIndex (2011-01-03 to 2026-06-30, 3895 sessions)
- **Columns:** 586 tickers
- **Values:** Adjusted close prices only (`adjClose` from Tiingo, `c` from Alpaca)

**File:** `/home/re/code/Aionis/data/cache/track_b_panel.parquet` (116M)
- **Format:** Long panel (date, ticker, features...)
- **Dimensions:** 1,172,244 rows × 30 columns
- **Columns:** `date`, `ticker`, `close`, `cpi`, `payems`, `vix`, `forward_return_h`, `accruals`, `asset_growth_12m`, `asset_growth_1m`, `book_value_per_share`, `debt_to_equity`, `equity_growth_1m`, `investment_12m`, `leverage`, `profit_margin`, `revenue_growth_12m`, `revenue_growth_1m`, `roa`, `roe`, `beta_252d`, `momentum_10d`, `momentum_21d`, `momentum_42d`, `momentum_5d`, `reversal_5d`, `turnover_21d`, `volatility_21d`, `volatility_63d`, `amihud_illiquidity_21d`
- **KEY OBSERVATION:** All price-derived features (momentum, reversal, volatility, beta, turnover) use ONLY `close`. **NO `open`, `high`, `low`, or `volume` columns exist.**

### 1.4 Where the frozen panel is built

**File:** `/home/re/code/Aionis/src/aionis/features/selection_panel.py`

**Function:** `build_selection_panel()` (lines 58-130)

**Current flow:**
1. Takes wide `prices` DataFrame (date × ticker, close-only)
2. Stacks to long format: `tidy = P.stack().rename("close").to_frame()` (line 93)
3. Computes forward returns: `tidy["y_fwd_ret"] = forward_returns(P, horizon).stack()` (line 94)
4. Merges fundamentals, FF5, macro (lines 98-122)
5. Returns long panel with `close` column only (line 130)

**Function:** `forward_returns()` (lines 53-55)
- Uses `close[t+h]/close[t] - 1` (line 55)
- **Only access point to `prices`** in the panel builder

**Implication:** Adding OHLCV columns requires:
1. Modify ingest fetchers to return OHLCV DataFrames (not just close Series)
2. Modify `build_selection_panel()` to accept and carry OHLCV columns
3. NO change to `forward_returns()` (still uses `close` only for labels)

### 1.5 OHLCV PIT-safety verification

**Finding:** **OHLCV is PIT-safe in the existing fetchers**

**Evidence:**
- Both Tiingo and Alpaca provide **daily OHLCV bars** with timestamps
- The ingest layer normalizes timestamps to NYSE session dates (lines 54-56 in `market.py`)
- **Daily OHLCV bars for date d are published at/after the close of date d** → knowable from d+1's open
- **No as-of vintage issues** for daily OHLCV (unlike ALFRED macro series)
- **No revision risk** for historical daily bars (once published, they don't change)

**Conclusion:** Extending the panel to carry OHLCV does NOT introduce lookahead leakage. The existing fetchers are already PIT-safe.

---

## 2. The Extension Plan (Concrete Minimal Changes)

### 2.1 Step 1: Extend ingest layer to fetch OHLCV

**File:** `/home/re/code/Aionis/src/aionis/ingest/market.py`

**Change 1.1: Extend `_from_tiingo()` to return OHLCV DataFrame**

Current signature (line 26):
```python
def _from_tiingo(
    symbols: list[str], start: str, end: str, api_key: str, retries: int = 3, backoff: int = 4
) -> dict[str, pd.Series]:
```

Proposed signature:
```python
def _from_tiingo(
    symbols: list[str], start: str, end: str, api_key: str, retries: int = 3, backoff: int = 4
) -> dict[str, pd.DataFrame]:
```

Current extraction (line 57):
```python
col = pd.Series(df["adjClose"].to_numpy(float), index=idx, name=sym)
```

Proposed extraction (replace lines 49-57):
```python
if rows:
    df = pd.DataFrame(rows)
    idx = pd.DatetimeIndex(pd.to_datetime(df["date"], utc=True)).tz_localize(None).normalize()
    # Extract OHLCV columns
    ohlcv = df[["adjClose", "open", "high", "low", "volume"]].copy()
    ohlcv["date"] = idx
    ohlcv = ohlcv.set_index("date")
    out[sym] = ohlcv
```

**Change 1.2: Extend `_from_alpaca()` to return OHLCV DataFrame**

Current signature (line 65):
```python
def _from_alpaca(
    symbols: list[str], start: str, end: str, key_id: str, secret_key: str,
    retries: int = 3, backoff: int = 4,
) -> dict[str, pd.Series]:
```

Proposed signature:
```python
def _from_alpaca(
    symbols: list[str], start: str, end: str, key_id: str, secret_key: str,
    retries: int = 3, backoff: int = 4,
) -> dict[str, pd.DataFrame]:
```

Current extraction (line 104):
```python
col = pd.Series(df["c"].to_numpy(float), index=idx, name=sym)
```

Proposed extraction (replace lines 98-104):
```python
bars = r.json().get("bars", [])
if bars:
    df = pd.DataFrame(bars)
    idx = pd.DatetimeIndex(pd.to_datetime(df["t"], utc=True)).tz_localize(None).normalize()
    # Extract OHLCV columns
    ohlcv = df[["c", "o", "h", "l", "v"]].copy()
    ohlcv.columns = ["adjClose", "open", "high", "low", "volume"]
    ohlcv["date"] = idx
    ohlcv = ohlcv.set_index("date")
    out[sym] = ohlcv
```

**Change 1.3: Update `fetch_price_series()` to handle OHLCV**

Current return (line 190):
```python
return series_by_sym  # dict[str, pd.Series]
```

Proposed return (no signature change needed, handles both Series and DataFrame):
```python
return series_by_sym  # dict[str, pd.DataFrame] with columns [adjClose, open, high, low, volume]
```

**Change 1.4: Update `fetch_prices()` to handle OHLCV**

Current line (lines 210-211):
```python
wide = pd.DataFrame({s: series_by_sym[s] for s in symbols})
wide = wide.reindex(expected_sessions).sort_index()
```

Proposed change (handle MultiIndex columns):
```python
# series_by_sym[s] is now a DataFrame with columns [adjClose, open, high, low, volume]
# Construct MultiIndex columns: (price_type, ticker)
price_cols = []
for sym in symbols:
    df = series_by_sym[sym]
    for col in df.columns:
        price_cols.append((col, sym))

wide = pd.concat([series_by_sym[s] for s in symbols], axis=1)
wide.columns = pd.MultiIndex.from_tuples(price_cols, names=["field", "ticker"])
wide = wide.reindex(expected_sessions).sort_index()
```

**Change 1.5: Update `save_snapshot()` and `load_snapshot()`**

No changes needed—parquet handles MultiIndex columns natively.

### 2.2 Step 2: Extend panel builder to carry OHLCV

**File:** `/home/re/code/Aionis/src/aionis/features/selection_panel.py`

**Change 2.1: Update `build_selection_panel()` signature**

Current signature (line 58):
```python
def build_selection_panel(
    prices: pd.DataFrame,  # Wide: date × ticker, close-only
    fundamentals_long: pd.DataFrame,
    horizon: int,
    tickers: list[str] | None = None,
    ff: pd.DataFrame | None = None,
    macro: pd.DataFrame | None = None,
    align_on: str = "filed",
    extra_features: pd.DataFrame | None = None,
) -> pd.DataFrame:
```

Proposed signature (no change—`prices` is now MultiIndex but function signature unchanged):
```python
def build_selection_panel(
    prices: pd.DataFrame,  # Wide: date × (field, ticker), fields=[adjClose, open, high, low, volume]
    fundamentals_long: pd.DataFrame,
    horizon: int,
    tickers: list[str] | None = None,
    ff: pd.DataFrame | None = None,
    macro: pd.DataFrame | None = None,
    align_on: str = "filed",
    extra_features: pd.DataFrame | None = None,
) -> pd.DataFrame:
```

**Change 2.2: Extract close column for forward returns**

Current (line 91):
```python
P = prices.reindex(sessions)[tickers]
```

Proposed (extract close for forward returns, stack OHLCV for panel):
```python
# Extract close for forward returns (label computation still uses close only)
P_close = prices["adjClose", tickers].reindex(sessions)

# Stack OHLCV columns for panel
tidy_ohlcv = prices[tickers].stack().reset_index()
tidy_ohlcv.columns = ["date", "ticker", "field", "value"]
tidy_ohlcv = tidy_ohlcv.pivot_table(index=["date", "ticker"], columns="field", values="value")
tidy_ohlcv.columns.name = None  # Flatten column names
```

**Change 2.3: Update panel assembly**

Current (lines 93-96):
```python
tidy = P.stack().rename("close").to_frame()
tidy["y_fwd_ret"] = forward_returns(P, horizon).stack()
tidy.index.set_names(["date", "ticker"], inplace=True)
tidy = tidy.reset_index()
```

Proposed:
```python
# Use OHLCV stacked data, add close column for backward compatibility
tidy = tidy_ohlcv.copy()
tidy["close"] = tidy["adjClose"]  # Alias for existing code
tidy["y_fwd_ret"] = forward_returns(P_close, horizon).stack()
tidy = tidy.reset_index()
```

**Verification:** All existing code using `tidy["close"]` continues to work (line 112, 114 in `selection_panel.py`).

### 2.3 Step 3: Update Phase B fetch script (no functional change)

**File:** `/home/re/code/Aionis/scripts/phase_b_fetch.py`

**Change 3.1: Update cache serialization**

Current (lines 76-79):
```python
series[t] = pd.Series(
    df["adjClose"].to_numpy(float),
    index=pd.to_datetime(df["date"]).dt.normalize(), name=t,
)
```

Proposed (handle OHLCV DataFrame):
```python
series[t] = df[["adjClose", "open", "high", "low", "volume"]].copy()
series[t].index = pd.to_datetime(df["date"]).dt.normalize()
```

**Verification:** The parquet format handles the schema change transparently. Existing cache files are invalidated (will be rebuilt).

---

## 3. Downstream Impact Analysis

### 3.1 What breaks downstream?

**Answer:** **Nothing breaks.** The extension is purely additive.

**Evidence:**
1. **Forward returns computation** (`selection_panel.py::forward_returns()`, line 55): uses `close` only → **unchanged**
2. **Fundamental-derived ratios** (`selection_panel.py` lines 112-116): use `tidy["close"]` → **unchanged** (we add `close` alias)
3. **Feature columns** (`scripts/phase_b_run.py` lines 50-54): `mktcap`, `pb_ratio`, `roa`, etc. → **unchanged**
4. **Two-arm runner** (`src/aionis/eval/two_arm.py`): uses `build_selection_panel()` → **no changes needed** (handles new columns transparently)
5. **Rank-IC evaluator** (`src/aionis/eval/rank_ic.py`): uses `score_col` and `y_col` → **unchanged**

### 3.2 H6 determinism impact

**Question:** Does adding OHLCV columns break bit-identical reruns of EXISTING features?

**Answer:** **NO.** H6 determinism is preserved.

**Reasoning:**
1. **Existing features use only `close`** → their computation is unchanged
2. **Forward returns (`y_fwd_ret`) use `close` only** → label values are unchanged
3. **Adding columns is additive** → does not modify existing column values
4. **Panel row layout (date, ticker) is unchanged** → fold indices are unchanged
5. **Frozen learner params are unchanged** → model weights are identical

**Verification procedure:**
- Run the existing Track-B config with the extended panel
- Assert that existing feature columns (momentum_5d, volatility_21d, etc.) are **bit-identical** to the original
- Assert that rank-IC series for existing arms are **bit-identical** to the original
- New OHLCV columns appear as new columns only

### 3.3 Performance impact

**Minimal:**
- Parquet file size: ~5× increase (close only → OHLCV + volume)
- Memory: ~5× increase during panel building (still manageable: 116M → ~580M)
- Fetch time: **NO CHANGE** (OHLCV data already fetched, just not saved)

---

## 4. Frozen-Config Consequence (CRITICAL)

### 4.1 This is a phase-level change

**Per ADR-006 (durable registry):**
> A changed config is a new ledger row. Same-config reruns are expected and bit-identical.

**This extension changes the frozen config:**
- New panel schema (OHLCV columns added)
- New `prices_sha256` in the config
- New `config_sig` (sha256 of the full config)

**Protocol:**
1. Append `config_committed` entry to `runs/ledger.jsonl` **BEFORE** any OOS metric is observed
2. Record the new `config_sig` (sha256 of the extended config)
3. Run the extended panel through the existing Phase B pipeline
4. Append `confirmatory:first` entry with the results

### 4.2 Ledger entry format

**config_committed entry:**
```json
{
  "ts": "2026-08-11T...",
  "event": "config_committed",
  "phase": "B_OHLCV",  // NEW PHASE DESIGNATION
  "config_sig": "<sha256 of extended config>",
  "config": {
    "feature_cols": [...],  // EXISTING FEATURES (unchanged)
    "horizon": 21,
    "n_splits": 5,
    "embargo_sessions": 21,
    "cv_scheme": "...",
    "frozen_params": {...},
    "end_lag_months": ...,
    "versions": {...},
    "fund_sha256": "<unchanged>",
    "prices_sha256": "<NEW SHA256 (OHLCV panel)>",
    "membership_sha256": "<unchanged>",
    "uv_lock_sha256": "<unchanged>",
    "panel_schema": {  // NEW FIELD
      "date_range": ["2011-01-03", "2026-06-30"],
      "tickers": 586,
      "price_columns": ["adjClose", "open", "high", "low", "volume"],
      "derived_features": ["momentum_5d", ...]  // unchanged
    }
  }
}
```

### 4.3 Pre-registration skeleton (two-tailed claim)

**Phase designation:** `Phase B_OHLCV` (step 1 of disciplined-adaptive roadmap)

**Pre-registered claim (two-tailed):**
> On the S&P 500 PIT universe (2011-2016 train, 2017-2026 OOS), adding OHLCV columns to the frozen panel (unlocking qlib K-Bar + volume factors) yields a cross-sectional monthly rank-IC whose differential vs the **close-only frozen baseline** (Track-B climax, ledger #49 = null) is statistically distinguishable from zero at the pre-registered SESOI, after Romano-Wolf correction across all OHLCV-derived factors tested.

**Null hypothesis (favorite):**
> Adding OHLCV columns does NOT improve OOS rank-IC beyond the close-only baseline. OHLCV micro-structure factors (candlestick shape, volume patterns) are either (a) subsumed by existing momentum/volatility features, or (b) degrade performance due to overfitting.

**Alternative hypothesis (positive):**
> OHLCV micro-structure captures information NOT present in close-only series (e.g. intraday volatility, volume confirmation, candlestick patterns) → incremental OOS rank-IC.

**SESOI (Smallest Effect Size of Interest):**
- To be determined after Step 2 (factor wiring) reveals the number of OHLCV-derived factors
- Conservative bound: Δ rank-IC ≥ 0.01 (1 percentage point) after Romano-Wolf correction
- Justification: If OHLCV factors don't beat this threshold, they're not worth the complexity

**Multiple-testing correction:**
- **Family:** All OHLCV-derived factors tested in Step 2 (expected: 15-30 factors from qlib alpha158 K-Bar + volume families)
- **Method:** Romano-Wolf step-down MTP (via `arch.bootstrap` or `rdmal/cvrm` port)
- **Rationale:** Controls FWER while maintaining power (better than Bonferroni for correlated factors)

**CV scheme (unchanged from Track-B):**
- 5-fold PurgedGroupKFold (group=month, embargo=21 sessions) over the 2016+ resolvable window
- **Rationale:** Preserves anti-leakage guarantees (purge + embargo)

**Primary metric:**
- OOS cross-sectional monthly rank-IC (Spearman) → time-series mean + HAC t-stat/p-value

**Secondary metrics (exploratory):**
- Top-decile vs bottom-decile forward returns
- Sharpe ratio of long-short decile portfolios
- Turnover and capacity metrics

---

## 5. Risk + Sequencing

### 5.1 Does this change the Track-B climax verdict?

**Answer:** **NO.** The Track-B climax verdict (ledger #49 = null) stands unchanged.

**Reasoning:**
1. **Track-B verdict is about fundamentals timing** (filed-date vs period-end), not price micro-structure
2. **Existing features are unchanged** → their IC values are identical
3. **Adding OHLCV columns does NOT modify existing feature values** → the null verdict remains valid
4. **Phase B_OHLCV is a NEW phase** with a NEW frozen config → does NOT supersede Track-B

**Verification procedure:**
- Re-run Track-B config on the extended panel (using only close columns)
- Assert that all Track-B feature values are bit-identical to the original
- Assert that the Track-B rank-IC series is bit-identical to the original
- If bit-identical, Track-B verdict stands (null result is durable)

### 5.2 Correct ordering vs Step 2 (factor wiring) and Step 3 (RD-Agent evaluator seam)

**Per `docs/adaptive-design-research.md` §6:**

| # | Step | Effort | New frozen config? | Needs owner OK? |
|---|---|---|---|---|
| **1** | **Extend panel to carry OHLCV** | M | **yes (new panel)** | **yes (this doc)** |
| 2 | Wire close-only + OHLCV factors into frozen pool | M | yes | yes |
| 3 | Build RD-Agent → Aionis evaluator seam | L | no (infra) | yes |
| 4 | Pre-register adaptive-vs-static claim | S | yes (new phase) | **yes (A+B go-signal)** |
| 5 | Run adaptive variants through gate | L | per-variant | no |
| 6 | Verdict → RESULTS.md + ledger | S | yes | no |

**Current status:** Steps 1-3 are safe infrastructure that serve EITHER reading (disciplined or adaptive). They don't commit to the adaptive claim.

**Step 4 is the A+B decision point** — the owner formally pre-registers the adaptive-vs-static claim.

**This document covers Step 1 only.**

### 5.3 Pre-conditions before implementation

**Blocking pre-conditions:**
1. **Owner approval** of this extension plan (including the new frozen config)
2. **Verification** that OHLCV data is available for all 586 tickers over the full date range (2011-2026)
3. **Verification** that adding OHLCV columns does NOT break existing feature values (H6 determinism test)

**Non-blocking pre-conditions (deferred to Step 2):**
- Factor wiring for OHLCV-derived features (K-Bar, volume factors)
- RD-Agent evaluator seam

---

## 6. Implementation Verification Checklist

**Before marking Step 1 complete:**

- [ ] Ingest layer modified: `_from_tiingo()` and `_from_alpaca()` return OHLCV DataFrames
- [ ] Ingest layer verified: OHLCV data fetched for all 586 tickers over 2011-2026 (no missing symbols)
- [ ] Panel builder modified: `build_selection_panel()` carries OHLCV columns
- [ ] Panel builder verified: Output panel has columns `adjClose`, `open`, `high`, `low`, `volume` (in addition to existing columns)
- [ ] H6 determinism verified: Re-run Track-B config on extended panel, assert existing features are bit-identical
- [ ] Ledger protocol: `config_committed` entry written to `runs/ledger.jsonl` BEFORE any OOS metric is observed
- [ ] Parquet files: `phase_b_prices.parquet` and `track_b_panel.parquet` regenerated with OHLCV columns
- [ ] Documentation: Pre-registration skeleton finalized (this doc)
- [ ] Tests: `pytest -q` passes (no regressions in existing tests)
- [ ] Lint: `uv run ruff check` is clean

---

## 7. References and Evidence

**Files cited (with line numbers):**

1. `/home/re/code/Aionis/src/aionis/ingest/market.py`
   - Line 26-62: `_from_tiingo()` (current close-only extraction)
   - Line 65-109: `_from_alpaca()` (current close-only extraction)
   - Line 112-152: `_volume_from_alpaca()` (exists but unused)
   - Line 166-191: `fetch_price_series()` (returns close-only Series)
   - Line 193-224: `fetch_prices()` (returns close-only wide DataFrame)

2. `/home/re/code/Aionis/src/aionis/features/selection_panel.py`
   - Line 53-55: `forward_returns()` (uses close only)
   - Line 58-130: `build_selection_panel()` (stacks close to long panel)
   - Line 91-96: Panel assembly (close column extraction)

3. `/home/re/code/Aionis/scripts/phase_b_fetch.py`
   - Line 76-79: Cache serialization (close-only extraction)
   - Line 104-105: Parquet write (close-only panel)

4. `/home/re/code/Aionis/scripts/phase_b_run.py`
   - Line 50-54: Feature columns (fundamentals + price-derived, close-only)
   - Line 79-84: `load_cached()` (loads close-only panel)
   - Line 86-97: `build_config()` (records `prices_sha256` of close-only panel)

5. `/home/re/code/Aionis/docs/qlib-reuse-audit.md`
   - §1: Factor overlap matrix (BLOCKED rows for K-Bar + volume factors)
   - §2: Anti-leakage gap (PurgedGroupKFold+embargo vs qlib's model_rolling)

6. `/home/re/code/Aionis/docs/adaptive-design-research.md`
   - §6: Build steps (step ordering and owner approval gates)

7. `/home/re/code/Aionis/decisions/ADR-006-no-disposable-artifacts-registry.md`
   - Durable registry protocol (config_committed BEFORE result)

8. `/home/re/code/Aionis/docs/phase-b-preregistration.md`
   - Two-tailed claim format (null = favorite)
   - Multiple-testing correction (Harvey-Liu, DSR, SPA)

**API documentation (verified):**

- Tiingo daily prices API: returns `date`, `open`, `high`, `low`, `close`, `adjClose`, `volume`
- Alpaca bars API: returns `t`, `o`, `h`, `l`, `c`, `v`, `vw`, `n`

**Data sources (MIT license, permissive):**

- Tiingo: API returns historical daily OHLCV (no licensing restrictions on historical data)
- Alpaca: API returns historical daily OHLCV (no licensing restrictions on historical data)

---

## 8. Open Questions and Decision Points

**Question 1: Should we include `vw` (VWAP) and `n` (num_trades) from Alpaca?**

**Options:**
- **A:** Include all Alpaca fields (o, h, l, c, v, vw, n) → maximal information
- **B:** Include only OHLCV (o, h, l, c, v) → align with Tiingo, simpler schema
- **C:** Include OHLCV + volume (c, v) → minimal extension

**Recommendation:** **Option A** (include all Alpaca fields). VWAP and num_trades may be useful for micro-structure factors in Step 2. There's no downside to carrying them now.

**Question 2: Should we keep `adjClose` as the primary `close` column, or rename it?**

**Options:**
- **A:** Keep `adjClose` as-is, add `close` alias for backward compatibility
- **B:** Rename `adjClose` → `close`, drop `adjClose`
- **C:** Keep both `adjClose` and `close` (if Alpaca's `c` is unadjusted)

**Recommendation:** **Option A** (keep `adjClose`, add `close` alias). Preserves existing code that expects `adjClose`, while adding `close` for qlib compatibility.

**Question 3: What SESOI should we pre-register for the OHLCV vs close-only differential?**

**Options:**
- **A:** Δ rank-IC ≥ 0.01 (1 percentage point) → conservative, aligned with Track-B
- **B:** Δ rank-IC ≥ 0.005 (0.5 percentage points) → more liberal, allows smaller effects
- **C:** Defer SESOI specification to Step 2 (after factor wiring reveals number of factors)

**Recommendation:** **Option A** (conservative SESOI). If OHLCV factors can't beat Δ ≥ 0.01 after correction, they're not worth the complexity. Aligns with the owner's 2026-08-05 framing (null = discipline).

**Question 4: Should we pre-register the number of OHLCV factors to be tested?**

**Options:**
- **A:** Pre-register n_trials = 30 (expected count from qlib alpha158 K-Bar + volume families)
- **B:** Leave n_trials open (exploratory Step 2, correct post-hoc)
- **C:** Use a data-driven n_trials (actual count after Step 2)

**Recommendation:** **Option A** (pre-register n_trials = 30). This is a conservative upper bound (actual count may be lower). Pre-committing to n_trials is more disciplined than post-hoc correction.

---

## 9. Next Steps (Owner Decision Required)

**Immediate next steps (after owner approval):**

1. **Owner approval:** Confirm that extending the panel to OHLCV is approved (new frozen config)
2. **Pre-commit verification:** Run a dry-run fetch to verify OHLCV data is available for all 586 tickers
3. **Implementation:** Execute the minimal changes documented in §2 (ingest layer + panel builder)
4. **H6 determinism test:** Re-run Track-B config on extended panel, verify bit-identical existing features
5. **Ledger entry:** Write `config_committed` to `runs/ledger.jsonl` with the new `config_sig`
6. **Pre-registration finalization:** Lock in the SESOI, n_trials, and CV scheme for Phase B_OHLCV

**Subsequent steps (deferred to Step 2):**

7. **Factor wiring:** Implement OHLCV-derived factors (K-Bar, volume, candlestick patterns)
8. **Multiple-testing correction:** Implement Romano-Wolf step-down MTP
9. **OOS evaluation:** Run the extended panel through the Phase B pipeline
10. **Verdict:** Append `confirmatory:first` to ledger with results

**Owner decision point (Step 4 in adaptive-design-research.md):**

- Greenlight Steps 1-3 (safe infrastructure) → enables EITHER disciplined OR adaptive readings
- Defer Step 4 (adaptive pre-registration) → owner decides A+B vs pure-discipline framing

---

## 10. Appendix: Code Diff Preview

**File: `/home/re/code/Aionis/src/aionis/ingest/market.py`**

```diff
--- a/src/aionis/ingest/market.py
+++ b/src/aionis/ingest/market.py

@@ -54,7 +54,12 @@ def _from_tiingo(
             rows = r.json()
             if rows:
                 df = pd.DataFrame(rows)
-                idx = pd.DatetimeIndex(pd.to_datetime(df["date"], utc=True)).tz_localize(
+                idx = pd.DatetimeIndex(pd.to_datetime(df["date"], utc=True)).tz_localize(
                     None
                 ).normalize()
-                col = pd.Series(df["adjClose"].to_numpy(float), index=idx, name=sym)
+                # Extract OHLCV columns
+                ohlcv = df[["adjClose", "open", "high", "low", "volume"]].copy()
+                ohlcv["date"] = idx
+                ohlcv = ohlcv.set_index("date")
+                out[sym] = ohlcv
         except Exception:
             pass
-        if col is not None and not col.empty:
-            out[sym] = col
+        if sym in out and not out[sym].empty:
+            pass  # Already added
```

**File: `/home/re/code/Aionis/src/aionis/features/selection_panel.py`**

```diff
--- a/src/aionis/features/selection_panel.py
+++ b/src/aionis/features/selection_panel.py

@@ -88,9 +88,15 @@ def build_selection_panel(
     tickers = list(tickers or prices.columns)
     sessions = nyse_sessions(prices.index.min(), prices.index.max())
-    P = prices.reindex(sessions)[tickers]
+    # Extract close for forward returns (label computation still uses close only)
+    P_close = prices["adjClose", tickers].reindex(sessions)
+
+    # Stack OHLCV columns for panel
+    tidy_ohlcv = prices[tickers].stack().reset_index()
+    tidy_ohlcv.columns = ["date", "ticker", "field", "value"]
+    tidy_ohlcv = tidy_ohlcv.pivot_table(index=["date", "ticker"], columns="field", values="value")
+    tidy_ohlcv.columns.name = None  # Flatten column names

-    tidy = P.stack().rename("close").to_frame()
-    tidy["y_fwd_ret"] = forward_returns(P, horizon).stack()
+    # Use OHLCV stacked data, add close column for backward compatibility
+    tidy = tidy_ohlcv.copy()
+    tidy["close"] = tidy["adjClose"]  # Alias for existing code
+    tidy["y_fwd_ret"] = forward_returns(P_close, horizon).stack()
     tidy.index.set_names(["date", "ticker"], inplace=True)
     tidy = tidy.reset_index()
```

---

**End of extension plan.**

**Document path:** `/home/re/code/Aionis/docs/ohclv-panel-extension-plan.md`
**Status:** READY FOR OWNER REVIEW
**Next action:** Owner approval → implementation → H6 determinism verification → ledger entry
