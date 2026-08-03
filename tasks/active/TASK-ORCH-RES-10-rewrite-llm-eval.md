# ORCH-RES-10 — Rewrite RES-10: LLM-eval metrics anchored to RD-04/06/07/08/11

- 编号: ORCH-RES-10
- 标题: Rewrite RES-10 (LLM extraction eval metrics) anchored to the completed RD-04/06/07/08/11 tools.
- 状态: owner-authorized (2026-08-03 D5: RES restart approved). PLANNED.
- Priority: **P2**
- Size: **S** (spec rewrite only)
- Risk: **LOW** (documents only)
- 目标: Replace the defective RES-10 spec (`tasks/active/TASK-RES-10-llm-eval.md`) whose root defect is
  that it was written before the RD tooling existed and therefore lacks an anchor.
- 缺陷 (root cause): the spec predates RD-04 (LLM gold schema), RD-06 (eval metrics), RD-07 (eval
  report), RD-08 (zero-LLM baseline), RD-11 (provider replay) — all now COMPLETE; the rewrite must
  anchor to them instead of re-specifying from scratch.
- 实施要求: The rewrite MUST anchor each eval metric to the existing RD implementation
  (RD-06 metrics module, RD-07 report writer, RD-08 zero-LLM baseline table `evals/expected/
  zero_llm_rules_v1.yaml`, RD-11 provider replay), and define the comparison protocol (precision /
  recall / coverage / abstention vs the zero-LLM/rule baseline), reusing the gold set from ORCH-RES-08.
- 允许修改: `tasks/active/TASK-RES-10-llm-eval.md` (rewrite in place; preserve 编号/标题).
- 禁止修改: anything else.
- 前置条件: owner D5 approval; RD-04/06/07/08/11 COMPLETE.
- 验收标准: the rewritten spec cites each RD artifact it anchors to, defines the metric protocol
  (precision/recall/coverage/abstention vs baseline), reuses the ORCH-RES-08 gold set, and updates
  状态 to "REWRITTEN 2026-08-03 — anchored to RD-04/06/07/08/11; ready for owner authorization".
- 必须运行的测试: none (docs-only).
- 失败处理: if a metric cannot be anchored to an existing RD artifact, mark BLOCKED for that metric.
- 预期产物: one rewritten `tasks/active/TASK-RES-10-llm-eval.md`.
- 完成后需要更新: 由 Orchestrator 更新 state/handoff.md.
