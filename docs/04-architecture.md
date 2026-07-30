# Architecture — the anti-leakage pipeline + repo map

Aionis is a **two-arm differential** experiment harness. Each phase compares a *treatment*
arm (fundamentals + the phase's feature bundle) against a *fundamentals-only* baseline
(`arm_base`, period-end+lag timing) on the **same** frozen prices / universe / folds /
learner, so the cross-sectional rank-IC **differential** isolates the bundle's incremental
signal.

## The pipeline (the discipline that makes any result trustworthy)

```
config freeze (sha256) ──► config_committed ledger row ──► PIT data ──►
PurgedGroupKFold(5, group=month, embargo=21) ──► frozen LightGBM ──►
OOS score panel (per arm) ──► monthly rank-IC + NW-HAC/MBB-DM differential ──►
controls (placebo, leave-one-out) + H6 determinism assert ──► save_run + ledger verdict
```

- **Freeze first.** The config sha256 is appended to `runs/ledger.jsonl` **before** any
  out-of-sample metric is observed. A changed config is a new row, never a silent overwrite.
- **PIT data.** `filed`-date fundamentals, ALFRED as-of vintages, unrevised VIX (PIT via the
  no-revision contract G3, not vintage tracking), filed-date 13D, PIT S&P 500 membership
  (`constituents_on`).
- **No label leakage.** PurgedGroupKFold over month-groups with a 21-session embargo.
- **Deterministic.** `n_jobs=1`, all seeds `0`, version-pinned → the IC series AND the raw OOS
  scores are bit-identical across reruns (H6, asserted).

## Repo map (top level)
- `src/aionis/ingest/` — PIT fetchers (fundamentals, prices, universe, vix, macro, stakes_13d,
  stakes_13d_efts, cik_resolver).
- `src/aionis/features/` — feature builders (peer_momentum, stakes_13d_signal, macro_surprise,
  propagation, anomaly_audit).
- `src/aionis/eval/` — phase orchestrators (`phase_{b,c,d,e1}.py`), `rank_ic.py`, `two_arm.py`,
  `learner.py` (LightGBMFrozen), `cv.py` (purged), `multiple_testing.py` (DSR/PBO/SPA/MCS),
  `strategy_returns.py`, `event_study.py`, `metrics.py` (DM-MBB), `*_controls.py`.
- `src/aionis/extraction/` — LLM client + providers (GLM / SiliconFlow / ModelScope only).
- `src/aionis/reporting/results.py` — `save_run` / `load_run` (schema-2, OOS-panel persistence).
- `scripts/` — thin runners. `dashboard/app.py` — quant-eval UI. `tests/` — hermetic.

## See also
- `theory-of-computable-reality.md` (TCR formal frame) · `05-acceptance.md` (the gates) ·
  `data-intake-rubric.md` (the 7 intake gates) · `phase-{b,c,d,e1}-preregistration.md` (the specs) ·
  `../CLAUDE.md` (directory map + commands) · `../decisions/ADR-006-no-disposable-artifacts-registry.md`.
