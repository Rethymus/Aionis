# Aionis Live-Data + Forward/Reveal + Calibration Infrastructure Report

**Date:** 2026-08-08  
**Purpose:** Map existing live-data, forward/reveal machinery, and calibration infrastructure to inform iterative live-calibration loop design (or determine if it's even feasible).  
**Scope:** READ-ONLY investigation of existing code, configuration, and workflow.

---

## Executive Summary

Aionis has **extensive forward/live infrastructure built but mostly DISABLED**. The project has engineered a sophisticated E3 forward-live prediction system with anti-leakage guards, but:

1. **E3 is NO-GO for headline** — owner-gated, scheduler disabled, shadow mode only
2. **No feedback loop exists** — frozen OOS scores are display-only; realized outcomes do NOT feed back into model training
3. **Daily refresh is display-layer only** — refreshes terminal data, never touches frozen models/OOS scores
4. **"Live-calibration" today = `score_calibration.py`** — a display utility that fits Platt scaling on HISTORICAL OOS data (walk_forward=False), NOT an iterative recalibration loop
5. **Anti-leakage anchors are structural** — `config_committed BEFORE result`, frozen LightGBM, sha256-sealed predictions, I1-I9 invariants

**Bottom line:** The system is architected for forward predictions but **intentionally lacks an iterative calibration loop**. Adding one would require navigating the anti-leakage anchors (frozen configs, no peeking at future outcomes).

---

## 1. E3 Forward/Live Machinery

### Status: **ENGINEERING COMPLETE, OWNER-GATED, DISABLED**

**Files:**
- `src/aionis/eval/forward_commit.py` (365 lines) — forward prediction commit
- `src/aionis/eval/forward_score.py` (319 lines) — reveal + scoring + accumulation
- `src/aionis/reporting/forward_ledger.py` (516 lines) — commit/reveal ledger primitives
- `config/e3_live_contracts.yaml` (59 lines) — owner-ratified contracts (FROZEN 2026-08-03 D2)
- `scripts/e3_forward_trigger.py` (100+ lines) — NYSE month-end scheduler trigger
- `tests/test_forward_e2e.py` (290 lines) — hermetic E2E chain

**Architecture — 4 Slices (commit → reveal → score → accumulate):**

#### Slice 3d: Forward Commit (`forward_commit.py:run_forward_commit`)
**Order (I1 anchor):**
```
freeze I_t (PIT panel snapshot) 
  → config_sha256(config) [BEFORE fit]
  → single fit per arm (LightGBMFrozen.fit_predict) 
  → commit_forward_prediction [sha256-sealed BEFORE target_t]
```

**Key invariants:**
- **I1 (commit-before-reveal):** `config_sha256` computed BEFORE any fit; commit seals scores BEFORE `target_t` outcome can realize
- **I4 (no lookahead):** `pit_train_test_split` ensures train block ends at `predict_date - embargo_sessions` (21 sessions)
- **I6 (pinned provider):** Only `glm` (GLM-4-Flash) allowed; provider swap = new forward sequence
- **I8 (silent-mutation guard):** `config_sha256` includes frozen_params, frozen_beta_sha256, versions, shas — ANY lever flip = new hash

#### Slice 4b: Reveal + Score (`forward_score.py:reveal_and_score_forward_month`)
**Process:**
```
load committed scores (from sealed parquet)
  → fetch_realized_forward_returns [at predict_ts AND target_t]
  → join scores with realized returns on ticker
  → compute Spearman rank-IC (ic_point)
  → reveal_forward_outcome [I1-gated: now >= target_t REQUIRED]
```

**I1 gate (lines 100-129):** Returns `revealed: False` with reason `"before_target_t"` if `wall-clock now < target_t`. The forward outcome has NOT realized yet — reveal refused.

**I2 immutability:** If scores parquet bytes differ from sealed sha256, mutation is refused (`forward_ledger.py:261-281`).

#### Slice 4c: Accumulate (`forward_score.py:accumulate_forward_ic_series`)
**Process:**
```
read scored rows (event="forward_outcome_scored")
  → build per-arm IC series (monthly, index=predict_ts month)
  → align arms on common months
  → compute differential: ic_forward = ic_e13 - ic_base
  → apply rank_ic_summary (NW-HAC) + diebold_mariano_mbb
```

**Returns:** `ic_forward` (Series), `summary` (dict with mean_diff, se_hac, ci_half, dm_stat, dm_p_mbb, n_months), `publishable_ci_half` (bool).

#### Scheduler (`e3_forward_trigger.py`)
**Trigger mechanism:**
- Uses `pandas_market_calendars` (XNYS) to find last NYSE trading day of month
- Returns early (no-op) if run_date is NOT month-end session
- Loads owner-gated contracts from `config/e3_live_contracts.yaml`
- Calls `forward_commit_runner.main()` with `enforce_live_readiness=True`

**Shadow mode (`PHASE_E3_NO_LEDGER=1`):** Computes everything but writes NO ledger rows.

### Contracts (`config/e3_live_contracts.yaml`)
**FROZEN values (owner-ratified 2026-08-03 D2):**
```yaml
membership_freshness_contract:
  max_age_sessions: 22  # ~1 month of NYSE sessions
  authoritative_refresh: null  # no standalone refresh; uses phase_b_fetch.py

provider_cutoff_policy:
  block_on_unknown: true  # fail-closed when provider cutoff unknown
```

**Status line 48-58 (from file):**
```
STATUS: FROZEN (owner ratified 2026-08-03, D2) - HEADLINE IGNITION STILL GATED

1. The values above are FROZEN. Changing any of them is a NEW contract decision.
2. The automated cron in .github/workflows/e3-forward.yml remains DISABLED.
   Headline (irreversible) forward commits still need owner's explicit GO.
3. Until then the workflow runs in shadow mode (PHASE_E3_NO_LEDGER=1):
   it computes everything but writes no ledger rows and makes no irreversible commits.
```

### Invariants (I1-I9) from `test_forward_e2e.py`
**Coverage map (lines 10-30):**
- **I1 (commit-before-reveal):** Chain tests reveal with `now < target_t` → both arms refused
- **I2 (immutability + idempotency):** Byte-stable parquet re-reads; byte-mutation flips hash; double-reveal appends no duplicate
- **I3 (forward-only ingest):** Owned by `test_forward_ingest.py` — NOT duplicated
- **I4 (no-lookahead PIT split):** Owned by `test_forward_commit_invariants.py` — NOT duplicated
- **I5 (structural-only ERL / no market impact):** Owned by ERL suites — NOT duplicated
- **I6 (single pinned glm provider):** Owned by `test_forward_commit_core.py` — NOT duplicated
- **I7 (determinism / bit-identical re-runs):** Owned by `test_forward_commit_core.py` — NOT duplicated
- **I8 (headline isolation / config-sha keying):** Owned by `test_forward_commit_core.py` — NOT duplicated
- **I9 (forward ledger vs confirmatory ledger separation):** Chain asserts E2E wrote ONLY `runs/forward/` + `runs/ledger.jsonl`, NEVER `runs/results/`

**Implication for calibration loop:** The E3 machinery is **ready to commit monthly predictions** but is **disabled by owner gate**. Even if enabled, it creates a one-way street (commit → wait 21 days → reveal). It does NOT feed outcomes back into model training.

---

## 2. Score Calibration (`src/aionis/eval/score_calibration.py`)

**Status:** **DISPLAY UTILITY ONLY — NOT AN ITERATIVE CALIBRATION LOOP**

### Purpose (lines 1-38)
**Module docstring:**
> "Display-only utility: produces honest per-region probabilities of positive forward return conditional on the OOS model score."

**Anti-leakage contract (lines 17-30):**
> "Calibration fit ONLY uses realized pairs — i.e. (date, ticker) rows whose `forward_return_h` is finite (already observed). The latest month, whose forward return is by definition unrealized, is naturally excluded by the NaN drop and is only *predicted*, never *fit on*."

> "Walk-forward refit is NOT enforced (display utility, not a research estimator). Disclosed in `CalibrationMeta.walk_forward = False`."

> "This module writes NO ledger / frozen surface / E3 outcome — it is a pure display transform, analogous to `ff5_residual`. The research verdict (combined rank-IC = −0.0088, null) is unaffected."

### Method (lines 54-72)
**Why Platt (sigmoid) is default, not isotonic:**
> "Isotonic regression is non-parametric and **overfits noise** — on a null model (rank-IC ≈ 0) it produces a wandering curve and a deceptively wide prob range, manufacturing discrimination that is not there. Platt scaling (2-parameter logistic sigmoid) is constrained, so on a null model it collapses to a near-flat curve tightly bracketing `base_rate` — the honest signal that 'the model cannot tell up from down'."

**CalibrationMeta (dataclass):**
```python
@dataclass(frozen=True)
class CalibrationMeta:
    region: str
    n_pairs: int
    base_rate: float  # mean(realized_up): empirical P(fwd_return > 0)
    ece: float  # Expected Calibration Error (lower = better calibrated)
    brier: float  # Brier score (lower = better)
    score_min: float
    score_max: float
    prob_min: float  # range of calibrated probs — tight around base_rate ⇒ null
    prob_max: float
    method: str = _DEFAULT_METHOD
    walk_forward: bool = False  # disclosed; display utility only
```

### Core Functions

**`fit_region` (lines 114-160):**
```python
def fit_region(
    scores: np.ndarray | pd.Series,
    realized_up: np.ndarray | pd.Series,
    region: str,
    method: Method = _DEFAULT_METHOD,  # "platt" (default) or "isotonic"
) -> CalibratedRegion
```
- Fits calibration: `score → P(realized_up = 1)`
- Requires ≥30 pairs (`_MIN_PAIRS`)
- Platt: `LogisticRegression(C=1e6, solver='lbfgs')` (effectively no regularization)
- Isotonic: `IsotonicRegression(out_of_bounds="clip", y_min=0.01, y_max=0.99)`

**`build_pair_frame` (lines 163-191):**
```python
def build_pair_frame(
    oos_scores: pd.DataFrame,    # [date, ticker, region, score]
    panel: pd.DataFrame,          # [date, ticker, forward_return_h, ...]
    region: str,
) -> pd.DataFrame                # [date, ticker, score, forward_return_h, realized_up]
```
- **Anti-leakage:** Rows with NaN `forward_return_h` are KEPT (indicate unrealized latest month)
- `fit_region` drops them via `np.isfinite` (latest month only predicted, never fit on)

**`calibrate_latest_month` (lines 194-252):**
```python
def calibrate_latest_month(
    oos_scores: pd.DataFrame,
    us_panel: pd.DataFrame,
    cn_panel: pd.DataFrame,
    latest_date: Any | None = None,
    method: Method = _DEFAULT_METHOD,
) -> dict[str, Any]
```
**Process:**
1. Determine per-region "latest unread month" (region's own max, US/CN may end on different dates)
2. `build_pair_frame` to join scores with realized returns
3. **Drop latest month from fit:** `history = pairs.dropna(subset=["forward_return_h"]); history = history[history["date"] < region_latest]`
4. `fit_region` on historical pairs
5. Predict latest month: `latest["prob_up"] = cr.predict_proba(latest["score"])`

**Returns:** `{latest_date, method, walk_forward=False, regions: {region: {meta, latest}}}`

### Usage in Terminal (`scripts/export_terminal_data.py:export_picks`)
**Lines 93-103:**
```python
df = pd.read_parquet("runs/track_c_confirmatory_oos_scores.parquet")
calibration = calibrate_latest_month(df, us_panel, cn_panel)

# Per-region prob_up lookup
prob_lookup: dict[tuple[str, str], float] = {}
for r, payload in calibration["regions"].items():
    if "latest" not in payload:
        continue
    for _, row in payload["latest"].iterrows():
        prob_lookup[(r, row["ticker"])] = float(row["prob_up"])
```

**Lines 137-147:** Enrich picks with `prob_up`:
```python
picks.append({
    "rank": rank_counter,
    "ticker": r["ticker"],
    "region": r["region"],
    "name": r["name"],
    "sector": r["sector"],
    "score": round(float(r["score"]), 3),
    "prob_up": round(prob_lookup.get((r["region"], r["ticker"]), 0.5), 3),
    "rank_change": (rp.get(r["ticker"]) - rank_counter) if rp.get(r["ticker"]) else None,
})
```

### Honest Signal (lines 31-35)
**From module docstring:**
> "The honest signal lives in `CalibrationMeta`:
> - `base_rate` ≈ 0.50–0.55 is the empirical 'did the market go up' rate.
> - `prob_min` / `prob_max` bracket the calibrated range. With Platt on a null model this range is tight around `base_rate` (e.g. 0.47–0.56), the visible signature of 'no discrimination'."

**Handoff 2026-08-07(a) lines 79-81:**
> "**诚实 null 的可视化**：top picks（score +2.28 海光信息）的 prob_up = **0.444**（<base_rate 0.4751）= 模型在 CN 的轻微反向信号；top 板块（Natural Gas Transmission）mean prob = 0.484 ≈ base rate。概率聚集在 base rate 附近 = NULL 的概率空间可视化。"

**Implication for calibration loop:** `score_calibration.py` is **a post-hoc display transform**, NOT an iterative recalibration mechanism. It fits a calibration curve on HISTORICAL OOS data (excluding the latest month) and applies it to the latest unread scores. It does NOT:
- Refit on rolling windows (walk_forward=False, disclosed)
- Feed predictions back into model training
- Write to the ledger or modify frozen surfaces
- Create a feedback loop

---

## 3. Daily Refresh Cron (`.github/workflows/refresh-terminal-data.yml`)

**Status:** **DISPLAY LAYER ONLY — DOES NOT TOUCH MODEL/OOS SCORES**

### Scope (lines 1-15)
**Workflow description:**
```yaml
# Daily data refresh for the Aionis fintech terminal.
# Rebuilds ticker metadata + re-exports all terminal JSON payloads, then
# commits the result. Keeps picks / sectors / track-record / calibration
# current without manual intervention.
```

**Schedule:** 22:00 UTC Mon-Fri (after US market close, before Asia open)

**Prerequisites (lines 8-11):**
- `TIINGO_API_KEY` — for US price fetches (phase_b_fetch)
- `FRED_API_KEY` — for macro data (FRED/ALFRED)
- Optional: `ALPACA_KEY_ID` / `ALPACA_SECRET_KEY` (US price fallback)

### Steps (lines 29-86)

**Step 1: Rebuild ticker metadata (lines 63-65)**
```yaml
- name: Rebuild ticker metadata (names + sectors)
  run: uv run python scripts/build_ticker_metadata.py --no-cache
  continue-on-error: true  # network may fail; old cache still works
```
- Rebuilds `data/cache/ticker_metadata.parquet` (ticker → name, sector)
- MIT sources: SEC company_tickers.json (US) + GitHub listing (CN)

**Step 2: Re-export all terminal payloads (lines 67-68)**
```yaml
- name: Re-export all terminal payloads
  run: uv run python scripts/export_terminal_data.py
  # BACKTEST_MONTHS defaults to 99 (full OOS history) in the script.
```

**What `export_terminal_data.py` does (from source, lines 81-256):**
1. `export_picks()` — reads frozen OOS scores, enriches with metadata, runs calibration
2. `export_picks_backtest()` — track record: past N months' top picks vs realized returns
3. `export_sector_breakdown()` — sector aggregation
4. Reuses `export_quarto_data.py` for shared payloads (evidence, power_floor, ic_monthly)

**Step 3: Verify JSON validity (lines 71-77)**
```yaml
- name: Verify JSON validity
  run: |
    set -e
    for f in web/src/data/aionis/*.json; do
      python3 -c "import json,sys; json.load(open('$f'))" || { echo "INVALID: $f"; exit 1; }
    done
```

**Step 4: Commit refreshed data (lines 79-86)**
```yaml
- name: Commit refreshed data
  uses: stefanzweifel/git-auto-commit-action@v5
  with:
    commit_message: "chore(data): daily terminal refresh [skip ci]"
    file_pattern: "web/src/data/aionis/*.json"
```

### What It Does NOT Touch
- **No model training** — does NOT retrain LightGBM
- **No OOS score regeneration** — reads from frozen `runs/track_c_confirmatory_oos_scores.parquet`
- **No ledger writes** — only commits terminal JSON to `web/src/data/aionis/`
- **No E3 forward predictions** — E3 is completely separate

**Implication for calibration loop:** The daily refresh is **a display layer update mechanism**. It ensures the fintech terminal shows the latest calibration, picks, and track record based on FROZEN OOS scores. It does NOT create an iterative calibration loop.

---

## 4. Forward Collectors (`src/aionis/ingest/forward/`)

**Status:** **FORWARD-ONLY SNAPSHOT MACHINERY — DISPLAY-ONLY, NOT RESEARCH-GRADE**

### Files
- `forward/__init__.py` (32 lines) — module docstring explains snapshot-on-arrival discipline
- `forward/_common.py` (337 lines) — shared persist_snapshot, I3 gate, ledger append
- `forward/stakes_13d_forward.py` (100+ lines) — SC 13D/13D-A collector
- `forward/macro_forward.py` — ALFRED macro surprise collector
- `forward/earnings_8k_forward.py` — EDGAR 8-K earnings collector

### Discipline (`forward/__init__.py` lines 1-26)
**Module docstring:**
> "Three PIT-as-of-t event-source collectors, each following the snapshot-on-arrival discipline of `aionis.ingest.reddit_sentiment` (the project's forward-collection exemplar). Together they let a month-end E3 commit FREEZE an `I_t` snapshot containing ONLY data with `filed/released <= snapshot_ts` — the data spine for E3's 'zero lookahead' guarantee."

**Forward vs existing PIT ingest (lines 18-26):**
> "Forward differs from existing PIT ingest in ONE way: forward = 'as-of now, never revised, never backfilled.' The first run starts the series at its own `snapshot_ts`; there is no historical reconstruction."

### Shared Persist Pattern (`forward/_common.py`)

**`persist_snapshot` (lines 245-284):**
```python
def persist_snapshot(
    cdir: Path,
    runs_dir: Path | str | None,
    *,
    dataset: str,
    snapshot_ts: str,
    raw_payload: dict,
    frame: pd.DataFrame,
    source: str,
    license: str,
    extra_ledger_fields: dict[str, object] | None = None,
) -> tuple[Path, str]:
```
**Process (DRY for all 3 collectors):**
1. `archive_raw(cdir, dataset, snapshot_ts, raw_payload)` — immutable sha256-pinned raw archive
2. `append_cumulative_parquet(cumulative, frame)` — concat, dedup, NEVER overwrite
3. `append_data_ingest_ledger(runs_dir, ..., forward_only=True, snapshot_ts=snapshot_ts)` — one ledger row

**I3 leakage gate (lines 292-320):**
```python
def assert_forward_clock(
    df: pd.DataFrame,
    event_ts_col: str,
    snapshot_ts: str
) -> None:
    """I3 leakage gate: every row's event_ts_col value must be <= snapshot_ts."""
```
- Called by each collector AFTER forward filter
- Raises RuntimeError if violation found (lookahead admitted to I_t)
- Empty frame trivially passes

**Idempotent ledger append (lines 191-237):**
```python
def append_data_ingest_ledger(
    runs_dir: Path | str | None,
    *,
    dataset: str,
    snapshot_ts: str,
    data_sha256: str,
    source: str,
    license: str,
    **extra: object,
) -> dict | None:
```
- Returns `None` if row already exists for `(dataset, snapshot_ts, data_sha256)` (idempotent)
- Appends new row only if first run or data changed

### Example: 13D Collector (`forward/stakes_13d_forward.py`)

**`collect_13d_forward` (lines 87-100):**
```python
def collect_13d_forward(
    ciks: dict[str, int],
    *,
    snapshot_ts: str | datetime | None = None,
    last_poll_ts: str | datetime | None = None,
    cache_dir: Path | None = None,
    runs_dir: Path | str | None = None,
) -> pd.DataFrame:
```

**Forward window (lines 45-84):**
```python
def _slice_13d_forward(
    recent: dict,
    last_poll_ts: str | datetime | None,
    snapshot_ts: str,
) -> list[dict]:
    """Filter submissions recent block to 13D filings in (last_poll_ts, snapshot_ts]."""
```
- Half-open interval: `(last_poll_ts, snapshot_ts]`
- First run: `last_poll_ts=None` → collect ALL filings filed `<= snapshot_ts`
- Subsequent runs: pass prior `snapshot_ts` → collect only net-new filings

**HIGH reuse (lines 11-19):**
- Reuses `aionis.ingest.stakes_13d.fetch_submissions` (cached submissions JSON)
- Reuses `aionis.ingest.stakes_13d._13D_FORMS` (SC 13D / SC 13D/A form set)
- Reuses `aionis.ingest.forward._common.persist_snapshot` (shared tail)

**Implication for calibration loop:** Forward collectors create **forward-only snapshots** (13D, macro, 8-K) that COULD feed into E3 forward predictions. However:
1. E3 is disabled (owner-gated)
2. These are forward-only (no historical backfill)
3. They're marked `forward_only: true` in the ledger (exploratory, not headline)
4. Even if E3 were enabled, there's NO feedback loop from realized outcomes back to the model

---

## 5. Ledger + Reveal/Score Gates

### Ledger Structure (`runs/ledger.jsonl`)
**Sample rows (50 total rows, from tail output):**

**Config committed rows (examples):**
```json
{
  "event": "config_committed",
  "phase": "track_c",
  "ts": "2026-08-05T04:19:50.785179+00:00",
  "config_sig": "e14b9d44...",
  "config": { ... full config ... },
  "amends": "#46/#47 -> #48 confirmatory GO (owner D1=A 2026-08-05)"
}
```

**Forward prediction committed row (hypothetical — not in current ledger):**
```json
{
  "event": "forward_prediction_committed",
  "phase": "E3",
  "predict_ts": "2026-07-31T20:00:00+00:00",
  "target_t": "2026-08-31T20:00:00+00:00",
  "config_sha256": "...",
  "config_sig": "...",
  "iset_sha256": "...",
  "scores_sha256": "...",
  "scores_path": "forward/.../scores_20260731T2000000000.parquet",
  "provider": "glm",
  "provider_cutoff": "2026-06-30"
}
```

**Forward outcome scored row (hypothetical — not in current ledger):**
```json
{
  "event": "forward_outcome_scored",
  "phase": "E3",
  "predict_ts": "2026-07-31T20:00:00+00:00",
  "target_t": "2026-08-31T20:00:00+00:00",
  "config_sha256": "...",
  "arm": "arm_base",
  "ic_point": 0.0123
}
```

### Commit → Reveal → Score Flow

**Step 1: Commit (`forward_ledger.py:commit_forward_prediction`, lines 209-291)**
```python
def commit_forward_prediction(
    predict_ts: str,
    target_t: str,
    scores: pd.DataFrame,
    config: dict,
    iset_sha256: str,
    provider: str,
    provider_cutoff: str,
    *,
    runs_dir: Path | str | None = None,
    mode: str = "exploratory",
) -> dict:
```
**Process:**
1. Canonicalize timestamps (`_canonical_ts`)
2. Compute `config_sha256`
3. Normalize scores (`_normalize_scores` → sort by ticker+arm)
4. Serialize to deterministic parquet bytes (`_deterministic_parquet_bytes`)
5. Compute sha256 of bytes
6. **I2 immutability check:**
   - If parquet exists with IDENTICAL bytes → idempotent return (H6)
   - If parquet exists with DIFFERENT bytes → mutation refused
   - If first commit → persist artifact + append ledger row

**I2 immutability (lines 248-281):**
```python
if path.exists():
    existing_sha = _sha256_bytes(path)
    if existing_sha == new_sha:
        # idempotent re-commit (H6): same scores -> no rewrite, no dup row
        return {**row, "committed": True, "_appended": False}
    # MUTATION of a sealed prediction -> refuse, do not overwrite (I2)
    log.warning("forward_commit_mutation_refused", ...)
    return {"committed": False, "reason": "scores_mutation_detected: ..."}
```

**Step 2: Reveal (`forward_ledger.py:reveal_forward_outcome`, lines 342-441)**
```python
def reveal_forward_outcome(
    target_t: str,
    ic_point: float,
    arm: str,
    *,
    predict_ts: str,
    config_sha256: str,
    runs_dir: Path | str | None = None,
    now: datetime | str | None = None,
    mode: str = "exploratory",
) -> dict:
```
**Process:**
1. Canonicalize timestamps
2. Read forward rows for this `config_sha256`
3. **I1 gate checks:**
   - **(a)** Must have prior `forward_prediction_committed` row for `(config_sha256, predict_ts, target_t)`
   - **(b)** Wall-clock `now >= target_t` (outcome has realized)
4. If either fails → return `{"revealed": False, "reason": "..."}`
5. Idempotency check: if already scored → return existing row
6. Append `forward_outcome_scored` row

**I1 gate enforcement (lines 376-410):**
```python
# Check (a): commit exists
commit = _find_commit(rows, predict_ts, target_t)
if commit is None:
    return {"revealed": False, "reason": "no_matching_commit: ..."}

# Check (b): wall-clock >= target_t
if now_dt < target_dt:
    return {"revealed": False, "reason": "before_target_t: wall-clock now < target_t ..."}
```

### Anti-Leakage Boundary

**The critical separation:**
1. **Commit happens BEFORE outcome is known** — `target_t` is 21 sessions in the future
2. **Reveal happens AFTER outcome is known** — wall-clock check enforces this
3. **Model never sees the outcome during training** — frozen LightGBM trained on `date <= predict_date - embargo`
4. **Scores are sha256-sealed** — any mutation flips hash and is refused
5. **No feedback loop** — realized outcomes are only scored, NOT fed back into model training

**Implication for calibration loop:** The ledger enforces **a one-way street** (predict → wait → reveal). There is NO mechanism to feed realized outcomes back into the model. This is by design — the anti-leakage anchor.

---

## 6. Picks + Track-Record Production

**Status:** **OPEN-LOOP (Frozen Model → Display)**

### Picks Export (`scripts/export_terminal_data.py:export_picks`, lines 81-221)

**Process:**
```python
def export_picks() -> tuple[str, int]:
    # 1. Load frozen OOS scores
    df = pd.read_parquet("runs/track_c_confirmatory_oos_scores.parquet")
    
    # 2. Load ticker metadata (names, sectors)
    meta = _load_ticker_metadata()
    
    # 3. Calibration on real OOS history (per-region latest, walk-forward=False)
    calibration = calibrate_latest_month(df, us_panel, cn_panel)
    
    # 4. Per-region picks: top 10 US + top 10 CN long; bottom 3 US + 2 CN short
    for region, payload in calibration["regions"].items():
        region_latest = pd.Timestamp(payload["latest_date"])
        region_df = df[(df["region"] == region) & (df["date"] == region_latest)].copy()
        region_df = _enrich_with_metadata(region_df, meta)
        
        # Top 10 long per region
        top = region_df.nlargest(10, "score")
        for _, r in top.iterrows():
            picks.append({
                "rank": rank_counter,
                "ticker": r["ticker"],
                "region": r["region"],
                "name": r["name"],
                "sector": r["sector"],
                "score": round(float(r["score"]), 3),
                "prob_up": round(prob_lookup.get((r["region"], r["ticker"]), 0.5), 3),
                "rank_change": (rp.get(r["ticker"]) - rank_counter) if rp.get(r["ticker"]) else None,
            })
        
        # Bottom 3 US / 2 CN short per region
        n_short = 3 if region == "us" else 2
        bot = region_df.nsmallest(n_short, "score")
        # ... append to shorts list
```

**Key points:**
- Reads from **frozen** `runs/track_c_confirmatory_oos_scores.parquet` (does NOT regenerate)
- Calibrates on historical OOS pairs (excluding latest month)
- **Per-region selection** — avoids dropping lagging region (US 2026-06-30, CN 2026-08-03)
- Enriches with display metadata (name, sector)
- Writes `picks.json` / `shorts.json` / `picks_meta.json` to `web/src/data/aionis/`

### Track-Record Export (`export_picks_backtest`, lines 256-349)

**Purpose (lines 256-266):**
> "Track record: past N months' top picks vs their realized forward returns. This is the honest 'prediction vs reality' audit — the soul of the anti-leakage project."

**Process:**
```python
def export_picks_backtest() -> None:
    # 1. Load frozen OOS scores + price panels (with realized forward_return_h)
    oos = pd.read_parquet("runs/track_c_confirmatory_oos_scores.parquet")
    us_panel = pd.read_parquet("data/cache/track_b_panel.parquet")
    cn_panel = pd.read_parquet("data/cache/cn_price_panel.parquet")
    
    # 2. For each region, merge scores with realized returns on (date, ticker)
    for region, panel in (("us", us_panel), ("cn", cn_panel)):
        region_oos = oos[oos["region"] == region][["date", "ticker", "score"]].copy()
        fwd = panel[["date", "ticker", "forward_return_h"]].copy()
        merged = region_oos.merge(fwd, on=["date", "ticker"], how="inner")
        merged = merged.dropna(subset=["forward_return_h", "score"])
        
        # 3. Past N_MONTHS realized months (exclude very latest if partial)
        N_MONTHS = int(os.environ.get("BACKTEST_MONTHS", "99"))  # default 99 = all history
        TOP_N = 5
        recent_months = months[-(N_MONTHS):]
        
        # 4. For each month, take top-N picks by score, compute hit rate + mean return
        for month_ts in recent_months:
            month_df = merged[merged["date"] == month_ts]
            top = month_df.nlargest(TOP_N, "score")
            top_mean_return = float(top["forward_return_h"].mean())
            base_rate_return = float(month_df["forward_return_h"].mean())
            
            # 5. Track hits (return > 0)
            for _, r in top.iterrows():
                ret = float(r["forward_return_h"])
                hit = ret > 0
                if hit:
                    n_hits += 1
                picks_list.append({
                    "ticker": r["ticker"],
                    "name": r["name"],
                    "score": round(float(r["score"]), 3),
                    "realized_return": round(ret, 4),
                    "hit": hit,
                })
```

**Output (`picks_backtest.json`):**
```json
{
  "methodology": "Past 99 realized months per region, top-5 picks by model score vs their actual forward_return_h...",
  "months": [
    {
      "month": "2026-06-30",
      "region": "us",
      "picks": [...],
      "top_mean_return": 0.0123,
      "base_mean_return": 0.0156,
      "excess": -0.0033
    },
    ...
  ],
  "summary": {
    "n_months": 131,
    "n_picks": 1310,
    "hit_rate": 0.5134,
    "avg_top_return": 0.0156,
    "avg_base_return": 0.0158,
    "avg_excess": -0.0002
  }
}
```

**Honest null disclosure (lines 331-338):**
> "If the model is NULL (rank-IC −0.0088), hit rate ≈ base rate and excess ≈ 0. This is the honest 'prediction vs reality' audit."

**Implication for calibration loop:** Both picks export and track-record export are **post-hoc display transforms** on frozen OOS scores. There is NO mechanism to:
- Adjust the model based on past performance
- Recalibrate based on realized outcomes
- Feed track-record findings back into training
- Update the frozen OOS scores

---

## 7. The Frozen-Config Anchor

**Status:** **THE CORNERSTONE OF ANTI-LEAKAGE — CONFIG_COMMITTED BEFORE RESULT**

### Mechanism (`scripts/phase_b_run.py:commit_config`, lines 100-106)

```python
def commit_config(config: dict) -> str:
    """HIGH-1: write config_committed to the ledger BEFORE any result is observed."""
    sig = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    ts = _now()
    _append({"ts": ts, "event": "config_committed", "phase": "B",
             "config_sig": sig, "config": config})
    return sig
```

**Usage (lines 172-173):**
```python
sig = commit_config(config)  # HIGH-1: BEFORE any result
print(f"[5c] config_committed sig={sig}  (logged BEFORE result)", flush=True)
```

### What Gets Frozen

**From Track C config (ledger row #48, from tail):**
```json
{
  "feature_cols": { ... },
  "horizon_confirmatory": 21,
  "embargo_sessions": 21,
  "learner": {
    "objective": "lambdarank",
    "params": {
      "n_estimators": 500,
      "learning_rate": 0.05,
      "num_leaves": 31,
      "min_child_samples": 20,
      "n_jobs": 1,
      "random_state": 0,
      ...
    }
  },
  "frozen_params": { ... },
  "versions": {
    "lightgbm": "...",
    "purgedcv": "...",
    "arch": "..."
  },
  "fund_sha256": "...",
  "prices_sha256": "...",
  "membership_sha256": "...",
  "uv_lock_sha256": "..."
}
```

**Hash covers:**
- Feature columns (what goes into the model)
- Hyperparameters (learner params)
- Data snapshots (fundamentals, prices, membership shas)
- Software versions (lightgbm, purgedcv, arch)
- Environment (uv.lock sha256)

### Anti-Leakage Guarantee

**From `CLAUDE.md` (inviolable constraints):**
> "**config_committed** BEFORE result. The frozen config's sha256 is appended to `runs/ledger.jsonl` *before* any out-of-sample metric is observed. Same-sig reruns are bit-identical (H6); a changed config is a **new ledger row**, never a silent overwrite."

**From handoff 2026-08-05(c) (lines 118-120):**
> "**config_committed ledger row BEFORE results** (config #48 frozen before dry-run → config_committed BEFORE result keeps)."

### Implication for "Live-Recalibrate the Model"

**What would break the anchors if done naively:**

1. **New config_committed row required** — Any model change (hyperparameters, features, data) = new sha256 = new ledger row
2. **New prereg required** — If changing the estimand or claim (e.g., "now we recalibrate monthly"), need new preregistration
3. **H6 determinism** — Same config must produce bit-identical results; "recalibration" implies changing the model
4. **Frozen learner** — LightGBM is frozen; "recalibrating" means retraining = new learner state
5. **No peeking at future** — Can't use outcomes after `target_t` to update the model trained before `predict_ts`

**What would be required (per project rules):**
- **Owner GO** — Significant change to experimental approach
- **New preregistration** — "Iterative live-calibration loop" is a NEW estimand, not the frozen Track C confirmatory
- **New config_committed row** — Documenting the exact model state at each calibration
- **New forward sequence** — E3 would need to commit predictions from the recalibrated model
- **Shadow mode testing** — Must prove anti-leakage before real commits

**From `CLAUDE.md` (inviolable constraints):**
> "A headline cannot be 'rerun-to-significance' rescued."

**The core tension:** A "live-calibration loop" that updates the model based on realized outcomes would violate the `config_committed BEFORE result` anchor unless it's:
1. Pre-registered as a NEW estimand
2. Documented with its own config_committed rows
3. Separated from the frozen confirmatory Track C

---

## 8. Summary: Can an Iterative Live-Calibration Loop Exist?

### What Exists Today
| Component | State | Can It Feed Calibration? |
|-----------|-------|--------------------------|
| **E3 forward predictions** | Engineering complete, OWNER-GATED, DISABLED | ❌ Disabled by owner gate; even if enabled, one-way street (commit → wait → reveal) |
| **score_calibration.py** | Active, DISPLAY utility | ❌ Post-hoc display transform; walk_forward=False; no feedback loop |
| **Daily refresh cron** | Active, DISPLAY layer only | ❌ Re-exports from frozen OOS scores; does NOT regenerate scores |
| **Forward collectors (13D/macro/8-K)** | Forward-only, exploratory | ⚠️ Could feed E3 if enabled, but still no feedback to model |
| **Picks + track-record** | Open-loop (frozen model → display) | ❌ Honest audit of null model; no mechanism to feed back |
| **Frozen config anchor** | ENFORCED | ⚠️ Any model change = new config_committed row = new sequence |

### Structural Constraints

**Anti-leakage anchors that block naive recalibration:**
1. **config_committed BEFORE result** — Model state must be frozen BEFORE outcomes observed
2. **I1 commit-before-reveal** — Forward predictions sealed before target_t
3. **I2 immutability** — Sealed scores cannot be mutated
4. **I4 no lookahead** — Train block ends at `predict_date - embargo_sessions`
5. **I8 silent-mutation guard** — Any config change flips sha256 = new sequence
6. **Frozen learner** — LightGBM params frozen; retraining = new learner
7. **No peeking** — Model cannot see outcomes from future sessions

**Display-only vs research-grade:**
- `score_calibration.py` — **Display-only** (writes no ledger, disclosed as walk_forward=False)
- Daily refresh — **Display-only** (commits only terminal JSON)
- Forward collectors — **Exploratory, forward-only** (no historical backfill, marked `forward_only: true`)
- E3 forward predictions — **Research-grade but disabled** (owner-gated, shadow mode only)

### What Would Be Required for a Live-Calibration Loop

**Option A: New pre-registered estimand (clean break)**
1. **New preregistration** — "Iterative monthly recalibration of model on realized outcomes"
2. **New config_committed rows** — One per calibration cycle
3. **New forward sequence** — Separate E3 sequence for recalibrated models
4. **Walk-forward calibration** — Document `walk_forward=True` (unlike current `walk_forward=False`)
5. **Owner GO** — Significant experimental change

**Option B: Extend E3 to include calibration (if enabled)**
1. **E3 must be owner-enabled** — Currently disabled/gated
2. **Add calibration step** — After reveal, refit calibration curve, write new calibration_meta
3. **Still open-loop** — Calibration does NOT feed back into model training
4. **Research-grade** — Would write to ledger, not display-only

**Option C: Hybrid (display-layer "recalibration")**
1. **Keep model frozen** — No config change, no new ledger rows
2. **Walk-forward calibration** — Change `score_calibration.py` to `walk_forward=True` (but NOT disclosed)
3. **Still display-only** — Does NOT affect frozen OOS scores or research verdict
4. **Minimal owner approval** — Still display layer, not research change

### Recommendation

**Given Aionis's anti-leakage discipline, the honest answer is:**

1. **E3 is the closest thing to a live-calibration loop** — It commits predictions, waits 21 days, reveals outcomes, and accumulates IC series. But it's disabled and even if enabled, does NOT feed outcomes back into model training.

2. **`score_calibration.py` is NOT a calibration loop** — It's a post-hoc display transform. It fits a calibration curve on historical OOS data (excluding the latest month) and applies it to the latest scores. It does NOT create a feedback loop.

3. **The daily refresh is display-layer only** — It re-exports terminal data from frozen OOS scores. It does NOT touch the model, OOS scores, or ledger.

4. **Any "live-recalibration of the model" would require:**
   - **New preregistration** (new estimand)
   - **New config_committed rows** (document model state at each calibration)
   - **Owner GO** (significant experimental change)
   - **Separation from frozen Track C** (to protect confirmatory results)

5. **The anti-leakage anchors are structural** — They're not accidental; they're the project's core discipline. "Recalibrating the model on live data" without respecting these anchors would violate the project's founding principles.

**If the goal is to explore "live data refresh + auto-calibration toward better predictions," the starting point is:**

- **Enable E3** (owner GO — already has contracts frozen)
- **Run in shadow mode** (PHASE_E3_NO_LEDGER=1 — compute but don't commit)
- **Observe forward IC series** (do predictions correlate with outcomes?)
- **THEN decide** if a calibration loop is even warranted (given null rank-IC −0.0088)

**The project already has the machinery to ask: "Do our forward predictions actually work?"** The answer (from the frozen confirmatory run) is: **No — rank-IC −0.0088, null.** Any calibration loop would start from that null baseline.

---

## Appendix: File Path Citations

| Area | File | Key Lines |
|------|------|-----------|
| **E3 forward** | `src/aionis/eval/forward_commit.py` | 261-350 (`run_forward_commit`) |
| **E3 forward** | `src/aionis/eval/forward_score.py` | 73-191 (`reveal_and_score_forward_month`) |
| **E3 forward** | `src/aionis/eval/forward_score.py` | 194-318 (`accumulate_forward_ic_series`) |
| **E3 ledger** | `src/aionis/reporting/forward_ledger.py` | 209-291 (`commit_forward_prediction`) |
| **E3 ledger** | `src/aionis/reporting/forward_ledger.py` | 342-441 (`reveal_forward_outcome`) |
| **E3 contracts** | `config/e3_live_contracts.yaml` | 1-59 (FROZEN values, status) |
| **E3 trigger** | `scripts/e3_forward_trigger.py` | 37-100 (contract loading, month-end detection) |
| **E3 E2E** | `tests/test_forward_e2e.py` | 10-35 (I1-I9 coverage map) |
| **Calibration** | `src/aionis/eval/score_calibration.py` | 1-38 (module docstring, anti-leakage) |
| **Calibration** | `src/aionis/eval/score_calibration.py` | 114-160 (`fit_region`) |
| **Calibration** | `src/aionis/eval/score_calibration.py` | 194-252 (`calibrate_latest_month`) |
| **Daily refresh** | `.github/workflows/refresh-terminal-data.yml` | 1-86 (workflow) |
| **Daily refresh** | `scripts/export_terminal_data.py` | 81-221 (`export_picks`) |
| **Daily refresh** | `scripts/export_terminal_data.py` | 256-349 (`export_picks_backtest`) |
| **Forward collectors** | `src/aionis/ingest/forward/__init__.py` | 1-26 (discipline) |
| **Forward collectors** | `src/aionis/ingest/forward/_common.py` | 245-284 (`persist_snapshot`) |
| **Forward collectors** | `src/aionis/ingest/forward/_common.py` | 292-320 (`assert_forward_clock` I3 gate) |
| **Forward collectors** | `src/aionis/ingest/forward/stakes_13d_forward.py` | 45-100 (`collect_13d_forward`) |
| **Config commit** | `scripts/phase_b_run.py` | 100-106 (`commit_config`) |
| **Config commit** | `scripts/phase_b_run.py` | 172-173 (usage) |
| **Ledger** | `runs/ledger.jsonl` | 50 rows (config_committed + confirmatory:first) |
| **State** | `state/current.md` | 1-974 (session protocol, E3 status) |
| **Handoff** | `state/handoff.md` | 1-1263 (daily work, calibration impl details) |
