# ORCH-RES-03 — Rewrite RES-03: ranking label/query contract

- 编号: ORCH-RES-03
- 标题: Rewrite RES-03 (rank-objective baseline) to define the ranking label/query contract.
- 状态: owner-authorized (2026-08-03 D5: RES restart approved). PLANNED.
- Priority: **P2**
- Size: **S** (spec rewrite only)
- Risk: **LOW** (documents only)
- 目标: Replace the defective RES-03 spec (`tasks/active/TASK-RES-03-baseline-rank.md`) whose root defect
  is "ranking label/query contract is undefined".
- 缺陷 (root cause): the spec does not define (a) the ranking label (what the model ranks — e.g., forward
  return vs rank-IC target), (b) the query structure (how cross-sections/query-months map to
  LightGBM lambdarank groups), or (c) how ties/missing are handled.
- 实施要求: The rewrite MUST define, reusing the FROZEN RD-15 decision packet
  (`reports/design/2026-08-01-rd15-rank-objective-contract.md` — objective=lambdarank, bin_count=5,
  group=query-month, per-month train-fold-only binning, ties share relevance, NaN excluded, out-of-range
  clamp+reason): the ranking label source, the query-month grouping, and the label-construction function
  — all anchored to the frozen `src/aionis/eval/ranking_contract.py` implementation.
- 允许修改: `tasks/active/TASK-RES-03-baseline-rank.md` (rewrite in place; preserve 编号/标题).
- 禁止修改: anything else.
- 前置条件: owner D5 approval; RD-15 FROZEN (2026-08-01 owner decision).
- 验收标准: the rewritten spec explicitly defines the ranking label + query-group + label function,
  cites the frozen RD-15 packet + `ranking_contract.py`, and updates 状态 to
  "REWRITTEN 2026-08-03 — rank-label contract defined; ready for owner authorization".
- 必须运行的测试: none (docs-only).
- 失败处理: if the contract cannot be fully defined from RD-15, mark BLOCKED rather than invent.
- 预期产物: one rewritten `tasks/active/TASK-RES-03-baseline-rank.md`.
- 完成后需要更新: 由 Orchestrator 更新 state/handoff.md.
