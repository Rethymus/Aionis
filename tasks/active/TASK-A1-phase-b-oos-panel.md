# A1 — Phase B OOS panel (pass `oos_state`/`oos_base` to `save_run` + same-sig solo rerun)

- 编号: A1
- 标题: Wire Phase B's schema-2 OOS panels into `save_run` and rerun solo (no-ledger) so all 4 phases demo the dashboard Fit Quality tab.
- 状态: **BLOCKED (2026-07-30)** — sig-mismatch guard fired **by design**: Phase B's frozen sig
  `17245a75…` was computed under the pre-Phase-C `uv.lock` (`e045a023…`); current tree uses
  `ee985437…` (PRAW-stack drift only — non-load-bearing; Phase B IC still bit-reproducible).
  Code edits retained (fail closed via `SystemExit`, zero leakage; ruff/305-tests clean).
  Awaiting owner decision — **DROP recommended**. See `state/blockers.md`.
- 来源: `state/backlog.md` "Phase B OOS panel" (S task).

## 目标 (Objective)
`scripts/phase_b_run.py` predates the schema-2 OOS-persistence wiring: its
`results.save_run(...)` call omits `oos_state` / `oos_base`, so the dashboard's
Fit Quality tab for Phase B shows the `st.info` placeholder instead of the
score-vs-return scatter + quantile spread that C/D/E1 already render. Pass the
two already-computed OOS panels through to `save_run`, then perform a
**same-config, no-ledger** solo rerun so the Phase B run dir is upgraded to
schema 2 without writing any new ledger row.

## 背景 (verified codebase facts)
- `scripts/phase_b_run.py` lines 195-200 — the `save_run(...)` call has NO
  `oos_state`/`oos_base` kwargs.
- The two panels are **already in scope** at that call site:
  - `pan_s` (arm_state, align_on="filed") and `pan_b` (arm_base, align_on="end_lag")
    are the 3rd return value of `arm_ic(...)` at lines 160-161.
  - `run_arm_oos` (`src/aionis/eval/two_arm.py` line 79) returns a panel with
    exactly the columns `save_run` expects: `[date, ticker, score, y_fwd_ret]`.
- Reference template (the exact wiring to copy): `src/aionis/eval/phase_d.py`
  lines 237-242 and `src/aionis/eval/phase_e1.py` lines 229-234, both call
  `results.save_run(..., oos_state=pan_X, oos_base=pan_Y)`.
- `save_run` (`src/aionis/reporting/results.py` lines 112-187) persists
  `oos_state.parquet` / `oos_base.parquet` only when those kwargs are non-None
  (schema-2 additive); the `config_sig` does NOT depend on them.
- Dashboard: `dashboard/app.py` `view_fit_quality` (line 531) reads
  `run.get("oos_state")` (line 544); when present it renders
  `_score_vs_return_scatter` + `_quantile_spread_chart`, else `st.info(...)`.
- **CRITICAL — Phase B has NO no-ledger gate today.** `scripts/phase_b_run.py`
  `main()` ALWAYS calls `commit_config(...)` (line 153, writes `config_committed`)
  AND ALWAYS appends `confirmatory:first` (line 204). Phase C/D/E1 all have an
  artifacts-only gate (`PHASE_{C,D,E1}_NO_LEDGER=1`); phase_d's pattern is at
  `scripts/phase_d_run.py` lines 87-89 + 135-140. **A same-sig Phase B rerun
  WITHOUT this gate would write a spurious 2nd `confirmatory:first` — a direct
  violation of H6 / the "no rerun-to-significance" rule.** Adding the gate is
  therefore part of this task, not optional.
- Frozen Phase B `config_sig` (from `runs/ledger.jsonl`): **`17245a75d2d4cd17c68f36a9d0f4b4f7f3baf1db31b33b87be79e6e4a11400da`**.
  The ledger currently has exactly 2 rows for this sig
  (`config_committed` + `confirmatory:first`); the rerun must leave that count at 2.
- The Phase B config (`build_config()` lines 86-97) hashes byte-stable fields
  only: frozen params + versions + `fund_sha256`/`prices_sha256`/
  `membership_sha256`/`uv_lock_sha256`. Since the rerun runs on the same machine
  against the same parquet bytes + `uv.lock`, the recomputed sig **WILL match**
  the frozen one (H6 bit-identical) — the spec requires the Engineer to verify
  this before observing any metric.

## 允许修改 (Files-to-change — exact)
- `scripts/phase_b_run.py` — the ONLY file modified in this task.
  - **Edit 1 (the wiring):** in the `results.save_run(...)` call (lines 195-200),
    add two kwargs so it mirrors `phase_d.py` lines 237-242:
    ```python
    run_path = results.save_run(
        sig, ic_state=ic_s, ic_base=ic_b,
        summary_state=sum_s, summary_base=sum_b,
        differential=diff, controls=ctrl, config=config,
        h6_deterministic=det_ok,
        oos_state=pan_s, oos_base=pan_b,   # <-- ADD (schema 2)
    )
    ```
    (`pan_s`/`pan_b` already exist; no new computation needed.)
  - **Edit 2 (the no-ledger gate):** add `PHASE_B_NO_LEDGER` artifacts-only mode
    to `main()`, mirroring `scripts/phase_d_run.py` lines 87-89 + 135-140 exactly:
    - At the top of `main()`, read `import os; artifacts_only = os.environ.get("PHASE_B_NO_LEDGER") == "1"`.
    - Branch the config commit: when `artifacts_only`, compute
      `sig = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()`
      and print `[5c] ARTIFACTS-ONLY rerun (no ledger write); sig={sig}` — do NOT
      call `commit_config` (no `config_committed` row).
    - When `artifacts_only`, SKIP the `confirmatory:first` `_append(...)` at
      lines 204-216 (guard it with `if not artifacts_only:`).
    - Add `import os` at module top (phase_d does this inside `main()`; either is fine).
  - **Edit 3 (sig-match guard):** when `artifacts_only`, after computing `sig`,
    assert it equals the frozen ledger sig before any metric is observed / any
    artifact written. Print both and abort on mismatch:
    ```python
    if artifacts_only:
        sig = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
        FROZEN = "17245a75d2d4cd17c68f36a9d0f4b4f7f3baf1db31b33b87be79e6e4a11400da"
        if sig != FROZEN:
            raise SystemExit(
                f"[B] ABORT: rerun sig {sig} != frozen ledger sig {FROZEN} — "
                "fund/prices/membership bytes, uv.lock, or lib versions drifted. "
                "Do NOT write artifacts or a ledger row."
            )
        print(f"[B] sig matches frozen ledger sig ({sig}); proceeding artifacts-only", flush=True)
    ```
    (Hardcoding the frozen sig here is intentional — it is a one-shot reproducibility
    sentinel for this single rerun, not a config param. If it feels brittle, the
    Engineer may instead read it from `runs/ledger.jsonl`'s Phase B `config_committed`
    row at runtime; either satisfies the guard.)

## 禁止修改 (Must NOT change)
- `src/**`, `dashboard/**`, `docs/**`, `decisions/**`, any other `scripts/*`.
- `runs/ledger.jsonl` — NO new row of ANY event for phase B (the rerun is
  artifacts-only; H6 bit-identical to the existing row).
- The Phase B `config` contents / `FEATURE_COLS` / `HORIZON` / `N_SPLITS` /
  `EMBARGO` / `CV_SCHEME` — the sig must not move.
- Do NOT add `ls_returns` (out of scope; the Fit Quality tab needs only `oos_state`).

## 前置条件 (Data availability verdict)
**PRESENT — no fetch needed.** Verified in `data/cache/`:
- `phase_b_fundamentals.parquet` ✓
- `phase_b_prices.parquet` ✓
- `universe_pierrebrunelle.parquet` ✓
If any is absent on the run machine → BLOCKED; a fetch (`scripts/phase_b_fetch.py`)
is a prerequisite, NOT part of this S-task.

## 实施要求 (Implementation notes)
- Real data + real frozen LightGBM only. No mock/synthetic in this path.
- `n_jobs=1`, seed pinned to 0 (already enforced by `FROZEN_PARAMS`).
- The rerun is `config_committed`-free: same config → same sig → same artifacts
  (H6). The dashboard upgrade is purely additive (`oos_state.parquet` +
  `oos_base.parquet` appear in the existing run dir; no other file changes).

## 验收标准 (Acceptance criteria — testable)
- [ ] `uv run ruff check` clean; `uv run pytest -q` green (no regression).
- [ ] `PHASE_B_NO_LEDGER=1 uv run python scripts/phase_b_run.py` completes;
      stdout contains `[B] ARTIFACTS-ONLY rerun` and `sig matches frozen ledger sig`.
- [ ] **Ledger untouched:** `grep -c '"phase": "B"' runs/ledger.jsonl` is unchanged
      before vs after (still 2 rows for sig `17245a75…`); no new `confirmatory:*`
      or `config_committed` row.
- [ ] `runs/results/17245a75d2d4cd17c68f36a9d0f4b4f7f3baf1db31b33b87be79e6e4a11400da/oos_state.parquet`
      AND `…/oos_base.parquet` now exist.
- [ ] `uv run python -c "from aionis.reporting.results import load_run; r=load_run('17245a75d2d4cd17c68f36a9d0f4b4f7f3baf1db31b33b87be79e6e4a11400da'); print(r['oos_state'].columns.tolist())"`
      prints a list containing `date, ticker, score, y_fwd_ret` (non-None).
- [ ] `uv run streamlit run dashboard/app.py` → select the Phase B run (`17245a75…`)
      → **Fit Quality tab renders the score-vs-return scatter + quantile spread**
      (NOT the `st.info` "needs the per-ticker OOS panel" placeholder).
- [ ] H6 still holds: the rerun's `ic_state` / `ic_base` parquet bytes are
      unchanged from the prior run (the only new files are `oos_*.parquet`).

## 必须运行的测试
- `uv run ruff check`
- `uv run pytest -q`
- `PHASE_B_NO_LEDGER=1 uv run python scripts/phase_b_run.py`
- ledger before/after: `grep -c '"phase": "B"' runs/ledger.jsonl` (must be unchanged)
- `load_run(...)` column check (above)
- manual: dashboard Fit Quality tab for the Phase B run

## 失败处理
- If the recomputed sig != frozen `17245a75…`: **STOP immediately.** Do NOT write
  artifacts, do NOT write a ledger row. Report BLOCKED — something in
  `fund/prices/membership` parquet bytes, `uv.lock`, or lib versions drifted since
  the frozen run. Resolution is out of scope for this S-task (likely a re-fetch or
  a version pin fix).
- If `pytest`/`ruff` regress: roll back the edit, do not force-land.

## Size + Risk
- **Size: S.** Net delta ≈ 2 lines in `save_run` + ~12 lines for the no-ledger gate
  + sig-match guard (all copy-adapted from `phase_d_run.py`).
- **Risk: LOW** (reversible — adds 2 parquet files to one run dir; ledger is
  untouched). The only correctness trap is forgetting the no-ledger gate, which
  this spec bakes in as Edit 2 + an acceptance check.

## 预期产物
- Updated `scripts/phase_b_run.py` (3 edits above).
- `runs/results/17245a75…/oos_state.parquet` + `oos_base.parquet` (schema 2).
- NO new ledger row.

## 完成后需要更新
- `state/current.md`, `state/handoff.md`.
- (Optional) `docs/RESULTS.md` if it claims "all 4 phases demo fit charts" — only
  after the dashboard check passes.
