# ORCH-RES-02 — Rewrite RES-02: FF5/DFF cross-sectional baseline

- 编号: ORCH-RES-02
- 标题: Rewrite RES-02 (baseline FF5+DFF) into a cross-sectional-valid spec.
- 状态: owner-authorized (2026-08-03 D5: RES restart approved). PLANNED.
- Priority: **P2**
- Size: **S** (spec rewrite only)
- Risk: **LOW** (documents only; no code/frozen-surface touch)
- 目标: Replace the defective RES-02 spec (`tasks/active/TASK-RES-02-baseline-ff5.md`) with one that fixes
  its root defect: raw monthly FF5/DFF values are common to every security in a month and cannot directly
  rank the cross-section.
- 缺陷 (root cause, from the 2026-08-01 planning correction): the current spec adds raw monthly
  MKTRF/SMB/HML/RMW/CMA/DFF as feature columns, but these are time-series (market-wide) factors —
  identical for every stock in a month → zero cross-sectional discrimination → cannot rank-IC.
- 实施要求: The rewrite MUST define stock-specific rolling exposures/interactions (e.g., rolling
  beta-to-factor, factor-loading interactions with stock-level characteristics) as the actual feature
  columns, so the baseline is cross-sectionally rankable. It MUST also:
  - prove no same-month future use (PIT: factors known at t via release-date/vintage discipline),
  - pass `TASK-RD-13` (cross-sectional variation guard),
  - separately clear French-data license/release/PIT intake (7-gate).
- 允许修改: `tasks/active/TASK-RES-02-baseline-ff5.md` (rewrite in place; preserve 编号/标题).
- 禁止修改: anything else — no src/, no config, no ledger, no docs/, no other task files.
- 前置条件: owner D5 approval (2026-08-03).
- 验收标准: the rewritten spec's 目标/实施要求/验收标准 sections all define cross-sectionally rankable
  stock-specific features (not raw market-wide factor columns); PIT + RD-13 + 7-gate intake requirements
  are explicit; the 状态 line is updated to "REWRITTEN 2026-08-03 — cross-sectional-valid; ready for owner
  authorization".
- 必须运行的测试: none (docs-only task).
- 失败处理: if the rewrite cannot produce a cross-sectionally valid design, mark 状态 as
  "REWRITE BLOCKED — needs owner design input" instead of inventing one.
- 预期产物: one rewritten `tasks/active/TASK-RES-02-baseline-ff5.md`.
- 完成后需要更新: 由 Orchestrator 更新 state/handoff.md.
