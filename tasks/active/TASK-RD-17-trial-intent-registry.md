# RD-17 — Trial intent registry 合约

- 编号: RD-17
- 标题: 为新研究 trial 建立结果观察前的 tracked intent manifest 与 validator。
- 状态: **COMPLETE — owner-authorized via /goal 2026-08-01 (P1, HIGH-risk); 独立 Verifier PASS (ledger byte-identical to HEAD; 无 bypass 写入代码; metric 注入被拒) + 独立 Reviewer APPROVE (0 issues 全 severity; ledger-bypass 多层防御). trial-intent manifest 明确不替代 config_committed ledger。**
- Priority: **P1**
- Size: **M**（90–180 分钟）
- Risk: **HIGH**（必须补充而不能替代 config_committed ledger）
- 目标: 定义 trial id/family/owner approval/config hash/validation kind/estimand/multiplicity/status 的
  tracked intent schema，使未来 RES task 在写 ledger 或观察结果前有可审计计划。
- 背景: 现有 RES-01..10 都要求 trial registry entry，但仓库没有独立 contract，且部分任务又禁止
  写 ledger；需要先区分“计划 manifest”与“不可替代的 ledger commit”。
- 允许修改: `src/aionis/reporting/trial_intent.py`、`tests/test_trial_intent.py`、
  `evals/trials/README.md`（可新建）。
- 禁止修改: `runs/ledger.jsonl`、真实 trial/config/result/data、phase runners、prereg/ADR/state。
- 前置条件: owner 授权 RD-17；manifest 明确声明不具备 config_committed 的效力。
- 实施要求: id 唯一、schema version、owner decision reference、parent/family、chronological/cross-fit 明示、
  planned config sha256、n_trials accounting、status transition enum；不含任何 observed metric。
- 验收标准: 无 owner reference/hash/estimand/validation kind 时 fail closed；重复 id 拒绝；schema 不允许
  IC/return/p-value/CI 字段；JSON 稳定；README 明示 ledger 仍必须先于结果 append。
- 必须运行的测试: `uv run pytest -q tests/test_trial_intent.py`; `uv run ruff check`。
- 失败处理: 若设计会绕过或替代 ledger，BLOCKED 并退回强 Reviewer。
- 预期产物: intent schema/validator、tracked registry usage contract、negative tests。
- 完成后需要更新: 由 Orchestrator 更新 state/handoff；真实 trial 仍需单独 owner/config/ledger task。
