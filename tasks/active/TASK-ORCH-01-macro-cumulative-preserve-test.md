# ORCH-01 — macro forward cumulative-preserve test

- 编号: ORCH-01
- 标题: Mirror the 13D cumulative-parquet-prior-rows invariant for the macro forward collector.
- 状态: owner-authorized via the 2026-08-03 "同步进行" directive (P1; first-wave validation of the ADR-012 dispatch protocol). Not yet implemented.
- Priority: P1
- Size: S
- Risk: LOW
- 目标: Add `test_macro_forward_cumulative_parquet_preserves_prior_rows` to `tests/test_forward_ingest.py`, proving a later macro snapshot appends new rows while prior rows survive in the cumulative parquet — closing the asymmetric anti-leakage invariant gap (13D and 8-K pin it; macro does not).
- 背景: The 13D collector pins "a later `snapshot_ts` preserves prior rows" at `tests/test_forward_ingest.py:205` (`test_13d_forward_cumulative_parquet_preserves_prior_rows`); the macro collector shares the same `_common.append_cumulative_parquet` helper (`src/aionis/ingest/forward/macro_forward.py:130`) but has NO equivalent test — a regression to the shared helper would silently pass macro. Filed from the Slice 2 independent review (advisory, non-blocking; listed in `state/backlog.md`).
- 允许修改: `tests/test_forward_ingest.py`.
- 禁止修改: `src/`, frozen prereg/ADR/config/ledger/results/data/forward, the existing 13D test, any other test file.
- 前置条件: owner authorization recorded in the 状态 line (the "同步进行" directive).
- 实施要求: Mirror the 13D test's structure — two `collect_macro_forward` calls at T1 then T2 (with `last_poll_ts=T1`); read the cumulative parquet (`<DATASET>.parquet`); assert prior rows survived AND new rows appended. Reuse the existing macro helpers `_alfred_obs` / `_write_alfred_cache` / `_macro_fixture_rows` and the two-series pattern (CPIAUCSL + PAYEMS). Read `src/aionis/ingest/forward/macro_forward.py` + `src/aionis/ingest/forward/_common.py:142` (`append_cumulative_parquet`) to determine the macro cumulative parquet schema (columns + how `snapshot_ts` is keyed). Place the new test immediately after `test_macro_forward_idempotent_rerun_stable_sha`. Hermetic: ALFRED cache-hit only, no network.
- 验收标准: (1) the new test passes; (2) `uv run pytest -q tests/test_forward_ingest.py` is fully green; (3) `uv run ruff check` is clean; (4) no `src/` or frozen-surface change; (5) the assertion genuinely proves prior-row survival (not a weakened/trivial assertion).
- 必须运行的测试: `uv run pytest -q tests/test_forward_ingest.py`; `uv run ruff check`.
- 失败处理: If the macro cumulative does NOT preserve prior rows (the invariant genuinely fails), report BLOCKED with the failing evidence — do NOT weaken the assertion or use `test.skip`. If the macro cumulative schema makes a faithful mirror inapplicable, report BLOCKED describing the actual behavior.
- 预期产物: one new test function in `tests/test_forward_ingest.py`.
- 完成后需要更新: 由 Orchestrator 更新 `state/handoff.md` + 本任务 `状态` 行。
