# A2 — E1 horizon-robustness extension (sweep h∈{10,42} for symmetry with B/C/D)

- 编号: A2
- 标题: Extend `scripts/sensitivity_horizon.py` so the exploratory h∈{10,42} sweep also covers Phase E1 (arm_prop vs arm_base_self), writing E1 results into the same single `exploratory` ledger row.
- 状态: **DONE (2026-07-30)** — Verifier PASS (real-state), Reviewer APPROVE; +1 `event:"exploratory"`
  ledger row appended (E1 `null_holds=True` at h=10 AND h=42; correct base `arm_base_self`;
  B/C/D bit-identical / H6 holds). All 4 nulls now horizon-robust at h∈{10,42}. → `tasks/completed/`.
- 来源: `state/backlog.md` "Horizon-robustness extension" (S task).

## 目标 (Objective)
The frozen confirmatory horizon is h=21. `scripts/sensitivity_horizon.py` already
sweeps B/C/D at h∈{10,42} and appends ONE `event:"exploratory"` ledger row. Extend
it to also cover Phase E1 for symmetry, so the horizon-robustness story spans all
4 nulls. E1 is exploratory at h≠21 (changed config) → **only the `exploratory`
row is augmented; NEVER write `confirmatory:*`.**

## 背景 (verified codebase facts + the KEY structural trap)
- `scripts/sensitivity_horizon.py`:
  - `phases` dict (lines 122-128) has entries for B, C, D only.
  - The per-horizon loop (lines 131-158) computes ONE shared `arm_base`
    (`feature_cols=FEATURE_COLS`, `align_on="end_lag"`, lines 136-138) and reuses
    it as the base for every phase: `diff = differential(ic_e, base_ic)`.
  - `_null_holds(diff)` (lines 103-106) reads `ci_lo`/`ci_hi` from the diff dict.
  - `_append_ledger` (lines 181-199) writes ONE row with `event:"exploratory"`,
    `phase:"sensitivity_horizon"`, `results[<horizon>][<phase>] = {…}`.
  - `_print_table` (lines 167-178) hardcodes the `("B","C","D")` phase loop.
  - The module docstring's "Arms" list (lines 20-26) covers B/C/D only.
- **KEY STRUCTURAL TRAP — E1's base is NOT the shared `arm_base`.** In Phase E1
  (`src/aionis/eval/phase_e1.py`):
  - `arm_base_self` = `FEATURE_COLS + SELF_COLS` with `extra=self_extra`,
    `align_on="end_lag"` (lines 182-185).
  - `arm_prop` = `FEATURE_COLS + SELF_COLS + PROP_COLS` with `extra=full_extra`
    (merge of self_extra + prop_extra), `align_on="end_lag"` (lines 186-189).
  - The E1 differential = `arm_prop − arm_base_self` (line 190).
  - `SELF_COLS = ["self_earnings_surprise", "self_13d_event"]` (line 51).
  - `PROP_COLS = ["peer_earnings_surprise", "peer_13d_event"]` (line 53).
  - So E1 **CANNOT** reuse the sweep's shared plain `base_ic` — doing so would
    measure "prop vs fundamentals-only" instead of "prop vs base_self" and produce
    a scientifically meaningless differential. The `phases`-dict uniform iteration
    MUST branch for E1.
- E1's self/prop frames are built script-locally in `scripts/phase_e1_run.py`
  `_build_self_prop(px)` (lines 52-92): reads `phase_b_fundamentals.parquet` +
  `phase_d_sic_map.parquet` + `phase_d_13d_events.parquet`, builds
  `self_extra`/`prop_extra` via `earnings_surprise_long` +
  `earnings_surprise_as_of` + `stakes_13d_event_panel` + `propagate_panel`
  (`STAKES_WINDOW_DAYS=60`). This is horizon-independent (compute ONCE).
  Note: `scripts/sensitivity_horizon.py` already duplicates
  `scripts.phase_d_run._build_rel_extra` inline (lines 68-100) — the established
  pattern in this repo is to duplicate the build helper in the sweep, not import
  across scripts.
- `run_arm_oos` signature (`src/aionis/eval/two_arm.py` line 79):
  `run_arm_oos(prices, fundamentals_long, membership, horizon, feature_cols,
  align_on, folds, ref_layout, params=None, *, macro=None, extra_features=None)
  -> DataFrame[date, ticker, score, y_fwd_ret]`.
- `phase_c.differential(ic_a, ic_b)` (imported already at sweep line 45) returns
  `{mean_diff, ci_lo, ci_hi, dm_p_mbb, dm_stat, se_hac, ci_half, n_months, …}`
  (phase_c.py lines 205-227) — phase-agnostic, so it works for E1 unchanged.

## 允许修改 (Files-to-change — exact)
- `scripts/sensitivity_horizon.py` — the ONLY file modified.
  - **Edit 1 — imports:** add to the existing `from aionis.eval.phase_e1 import …`
    block (or create one): import `SELF_COLS` and `PROP_COLS`. (`FEATURE_COLS`
    is already imported from `phase_c`; `phase_e1.FEATURE_COLS` is identical — do
    not double-import.)
  - **Edit 2 — `_build_self_prop(px)` helper:** add a module-level helper that
    mirrors `scripts/phase_e1_run.py._build_self_prop` (lines 52-92) EXACTLY:
    same `STAKES_WINDOW_DAYS=60`, same PIT construction
    (`earnings_surprise_long` → `earnings_surprise_as_of`;
    `stakes_13d_event_panel`; `propagate_panel` for the peer frames; the
    `_long` + merge to produce `self_extra`/`prop_extra`). Reuse the sweep's
    existing `CACHE` / `nyse_sessions` / `pd.DatetimeIndex` assertions. Call it
    ONCE in `main()` (horizon-independent).
  - **Edit 3 — E1 branch in the per-horizon loop:** add an `"E1"` entry to the
    `phases` dict and handle it specially. Because E1's base differs, the cleanest
    shape is a branch inside the loop (NOT a uniform dict entry):
    ```python
    # after the shared base_panel/base_ic block (lines 136-138), for E1 only:
    full_extra_e1 = self_extra.merge(prop_extra, on=["date","ticker"], how="outer")
    bs_panel = run_arm_oos(px, fund, mem, horizon, FEATURE_COLS + SELF_COLS,
                           "end_lag", folds, ref, extra_features=self_extra)
    ic_bs = rank_ic_monthly(bs_panel, "score", "y_fwd_ret")
    pr_panel = run_arm_oos(px, fund, mem, horizon, FEATURE_COLS + SELF_COLS + PROP_COLS,
                           "end_lag", folds, ref, extra_features=full_extra_e1)
    ic_pr = rank_ic_monthly(pr_panel, "score", "y_fwd_ret")
    diff_e1 = differential(ic_pr, ic_bs)          # phase_c.differential (already imported)
    null_e1 = _null_holds(diff_e1)
    results[str(horizon)]["E1"] = {
        "arm_enhanced": "arm_prop", "arm_base": "arm_base_self",
        "enhanced_mean_ic": float(ic_pr.mean()), "base_mean_ic": float(ic_bs.mean()),
        **diff_e1, "null_holds": null_e1,
    }
    ```
    Keep B/C/D exactly as-is (they still share `base_ic`). Do NOT route E1
    through the shared-base `differential(ic_e, base_ic)` path.
  - **Edit 4 — `_print_table`:** add Phase E1 to the phase loop (print
    `arm_prop − arm_base_self` rows for h=10 / h=42).
  - **Edit 5 — summary line:** update the `all_robust` tally (line 162) and its
    print to span **4 phases × 2 horizons** (or report E1 separately alongside
    the B/C/D tally).
  - **Edit 6 — docstring:** add E1 to the "Arms (mirror the frozen confirmatory
    specs)" list (lines 20-26):
    `Phase E1: arm_prop (FEATURE+SELF+PROP, end_lag, extra=self+prop) vs arm_base_self (FEATURE+SELF, end_lag, extra=self)`.
  - **Edit 7 — coverage guard (degrade gracefully):** if
    `prop_extra["peer_earnings_surprise"].notna().sum() == 0` (degenerate SIC map
    / propagation produced nothing), do NOT abort the whole sweep — warn and set
    E1's `null_holds=None` with a note, so B/C/D still land. (The sweep is
    exploratory; `phase_e1_run.py` aborts on this for the confirmatory run, but
    the sweep should be lenient.)

## 禁止修改 (Must NOT change)
- `src/**`, any other `scripts/*`, `dashboard/**`, `docs/**`, `decisions/**`.
- The `event:"exploratory"` ledger semantics — do NOT introduce `confirmatory:*`
  or `config_committed` anywhere in this script.
- The frozen h=21 confirmatory runs — this task touches NO confirmatory path.

## 前置条件 (Data availability verdict)
**PRESENT — no fetch needed.** Verified in `data/cache/`:
- `phase_b_fundamentals.parquet` ✓, `phase_b_prices.parquet` ✓
  (needed by the shared base + E1 self-shocks).
- `phase_d_sic_map.parquet` ✓, `phase_d_13d_events.parquet` ✓
  (needed by E1's SIC-peer propagation + self_13d).
- `universe_pierrebrunelle.parquet` ✓.
- ALFRED/VIX bundle inputs already cached (the sweep loads them via `build_bundle`
  for Phase C — unchanged by this task).
If any is absent → BLOCKED; a fetch is a prerequisite, NOT part of this S-task.

## 实施要求 (Implementation notes / anti-leakage)
- Real PIT data + real frozen LightGBM only. No mock/synthetic.
- E1 arms use `align_on="end_lag"` for BOTH arm_base_self and arm_prop (matches
  `phase_e1.py` lines 150/164-165) — do NOT mix in `"filed"`.
- Reuse `phase_c.differential` (already imported) — do NOT import
  `phase_e1.differential`; they are functionally identical and the sweep
  standardizes on `phase_c`'s for B/C/D.
- The `exploratory` ledger row's `results` dict gains an `"E1"` key under each
  horizon (`"10"` and `"42"`); no other ledger structural change.
- `n_jobs=1`, seed=0 (enforced by the shared fold/learner path).

## 验收标准 (Acceptance criteria — testable)
- [ ] `uv run ruff check` clean; `uv run pytest -q` green (no regression).
- [ ] `uv run python scripts/sensitivity_horizon.py` completes; stdout prints a
      Phase E1 block at h=10 AND h=42 (`enhanced_IC`, `diff`, `DM p`, `CI[…]`,
      `ci_half`, `null=…`), plus an updated "horizon-robust" summary.
- [ ] The newly appended ledger row has `"event": "exploratory"`,
      `"phase": "sensitivity_horizon"`, and `results["10"]["E1"]` +
      `results["42"]["E1"]` each contain `arm_enhanced="arm_prop"`,
      `arm_base="arm_base_self"`, `mean_diff`, `ci_lo`, `ci_hi`, `dm_p_mbb`,
      `null_holds` (bool or null).
- [ ] **No confirmatory rows:** `grep -cE '"event": "confirmatory' runs/ledger.jsonl`
      is unchanged before vs after; only ONE new `"event": "exploratory"` row is
      appended.
- [ ] **Correct base:** E1's differential is computed against `ic_base_self`
      (arm_base_self), NOT the shared plain `base_ic`. Verify in source: the E1
      branch calls `differential(ic_pr, ic_bs)`, not `differential(ic_pr, base_ic)`.
- [ ] (If the degenerate-SIC guard triggers) E1 `null_holds` is `null` with a
      note, and B/C/D results still appear in the row — the sweep does not crash.

## 必须运行的测试
- `uv run ruff check`
- `uv run pytest -q`
- `uv run python scripts/sensitivity_horizon.py`
- ledger before/after: confirmatory count unchanged, +1 exploratory row with E1 keys.

## 失败处理
- If `propagate_panel` yields all-NaN `peer_earnings_surprise`: do NOT crash —
  warn, set E1 `null_holds=None`, still append the row with B/C/D intact. Report
  the degeneracy in the handoff; a re-fetch of the SIC map is out of scope.
- If `pytest`/`ruff` regress: roll back, do not force-land.

## Size + Risk
- **Size: S.** Contained to one script: ~1 import line + ~40-line `_build_self_prop`
  helper (copy-adapted) + ~15-line E1 loop branch + small print/docstring edits.
- **Risk: MEDIUM.** The single correctness trap is routing E1 against the wrong
  base (shared `base_ic` instead of `arm_base_self`). This spec bakes the branch
  into Edit 3 + an explicit acceptance check on the differential's base. A
  secondary risk is silently dropping B/C/D if E1 errors — mitigated by Edit 7's
  graceful-degradation guard.

## 预期产物
- Updated `scripts/sensitivity_horizon.py`.
- ONE new `event:"exploratory"` ledger row whose `results` now covers B/C/D **+ E1**
  at h∈{10,42}.

## 完成后需要更新
- `state/current.md`, `state/handoff.md`.
- `docs/RESULTS.md` — the horizon-robustness section currently says "3 phases";
  update to 4 (only after the sweep + acceptance checks pass).
