# ORCH-02 — 8-K forward cumulative-preserve test (REJECTED)

- 编号: ORCH-02
- 标题: Mirror the 13D/macro cumulative-parquet-prior-rows invariant for the 8-K forward collector.
- 状态: **REJECTED (2026-08-03)** — the premise was a grep-suffix miss. The 8-K collector ALREADY has
  cumulative-preserve coverage via `test_8k_forward_idempotent_and_cumulative_preserve`
  (`tests/test_forward_ingest.py:504` in HEAD), which tests the identical T1→T2 prior-row-survival
  invariant (`len(cum)==2`, `snapshot_ts=={t1,t2}`, new filing appended at T2). A standalone mirror
  would be redundant duplication, contra the 治理复杂度 ≤ 产出 invariant (ADR-012). NO code change
  landed; the wave's partial worker deliverable was discarded via `git restore`.
- Priority: P1 (was)
- Size: S (was)
- Risk: LOW (was)
- 目标: (rejected — see 状态)
- 背景: The original (mistaken) premise: the backlog said "13D + 8-K pin it" but the gap-analysis grep
  (`_cumulative_parquet_preserves_prior_rows`) returned only 13D + macro, so ORCH-02 was created to
  "fill the 8-K gap." The grep's name-suffix did not match the 8-K combined test
  (`_idempotent_and_cumulative_preserve`). The backlog wording was in fact correct.
- 允许修改: — (rejected)
- 禁止修改: —
- 前置条件: —
- 实施要求: —
- 验收标准: —
- 必须运行的测试: —
- 失败处理: —
- 预期产物: none (rejected).
- 完成后需要更新: —

## Findings from the wave-2 attempt (binding for future waves)

1. **`[1210]` subagent flakiness (2026-08-03):** two consecutive sonnet spawns
   (`oh-my-claudecode:executor`, then `general-purpose`) BOTH failed with `[1210]` API-parameter
   errors → the protocol's 2-identical-failures stop-condition was reached. Today's proxy is more
   flaky than the handoff's "transient, single retry works" note; `general-purpose` did NOT bypass
   it this time.
2. **A "failed" subagent may have already mutated the working tree** before its API error: one
   `[1210]`-failed executor wrote a complete, correct test into `tests/test_forward_ingest.py`
   *before* the failure surfaced. Binding rule: after ANY subagent `idle_reason="failed"`, run
   `git status` + `git diff` to detect partial work — never assume "failed = no changes." Folded
   into `docs/orchestration-protocol.md §8`.
3. **Gap-analysis hygiene:** when asserting "feature X is missing," grep for the CONCEPT
   (`grep -iE "cumulative.*preserve"`), not a specific name suffix — the suffix grep missed the
   8-K combined test and manufactured a false gap.
