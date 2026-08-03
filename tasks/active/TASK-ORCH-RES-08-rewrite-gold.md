# ORCH-RES-08 — Rewrite RES-08: gold-set into schema/sample/annotation/adjudication/freeze tasks

- 编号: ORCH-RES-08
- 标题: Rewrite RES-08 (LLM extraction gold set) into the 5-stage durable structure.
- 状态: owner-authorized (2026-08-03 D5: RES restart approved). PLANNED.
- Priority: **P2**
- Size: **S** (spec rewrite only)
- Risk: **LOW** (documents only)
- 目标: Replace the defective RES-08 spec (`tasks/active/TASK-RES-08-gold-set.md`) whose root defect is
  that it is a single monolithic task, not the required durable 5-stage structure.
- 缺陷 (root cause): a durable gold set cannot be built as one task; it needs schema → sample →
  annotation → adjudication → freeze stages (each independently verifiable, per ADR-006
  no-disposable-artifacts).
- 实施要求: The rewrite MUST split into the 5 stages, each with its own acceptance criteria:
  1. schema (event/source/timestamp/annotation field contract, versioned),
  2. sample (selection criteria; labeled-fixture vs real; PIT timestamps; no outcome leakage),
  3. annotation (double-annotation protocol + instructions; inter-annotator agreement target),
  4. adjudication (disagreement resolution; gold-verdict rules),
  5. freeze (immutable snapshot + sha256 + registry entry; H6).
  Each stage lists its 允许修改 / 禁止修改 / 验收标准 / 必须运行的测试, and the task explicitly notes
  the reuse of `docs/llm-extractor-eval.md` if it defines the gold schema.
- 允许修改: `tasks/active/TASK-RES-08-gold-set.md` (rewrite in place; preserve 编号/标题).
- 禁止修改: anything else.
- 前置条件: owner D5 approval.
- 验收标准: the rewritten spec contains 5 explicit stages each with acceptance + tests + file scope,
  and updates 状态 to "REWRITTEN 2026-08-03 — 5-stage durable gold-set; ready for owner authorization".
- 必须运行的测试: none (docs-only).
- 失败处理: if a stage cannot be defined without further research, mark BLOCKED for that stage.
- 预期产物: one rewritten `tasks/active/TASK-RES-08-gold-set.md`.
- 完成后需要更新: 由 Orchestrator 更新 state/handoff.md.
