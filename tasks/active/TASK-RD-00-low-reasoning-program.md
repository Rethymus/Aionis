# RD-00 — 低推理模型 8+ 小时研究开发总控（不得整体下发）

- 编号: RD-00
- 标题: 协调低推理模型的离线研究基础设施任务包。
- 状态: **PLANNED — awaiting owner launch choice**
- Priority: **P1**
- Size: **L — coordination only; MUST remain decomposed**
- Risk: **HIGH**（错误调度可能越过研究/owner gate）
- 目标: 协调 RD-01…RD-17 的离线基础设施开发，使后续小模型研究可被确定性评估。
- 背景: 完整主包约 25.5–40 Engineer 小时；第一波 RD-01/02/03/04/05/06/07/12 已超过 8 小时，
  必须分任务、分 gate，而不能整体交给一个 agent。
- 允许修改: 本任务状态、`state/current.md`、`state/handoff.md`；子任务只按各自白名单修改。
- 禁止修改: frozen prereg/config/ADR、`runs/ledger.jsonl`、`runs/results/**`、`runs/forward/**`、
  `data/**`；禁止真实 network/LLM、phase/strategy/horizon/forward 运行。
- 前置条件: owner 明确选择启动 P0、P0+P1 或某个单独 RD task。
- 实施要求: 单写者；独立 Verifier/Reviewer；最多两轮；每次最多两个无文件冲突的 worker。
- 验收标准: RD-01…RD-17 均为 APPROVE、明确 HOLD 或 BLOCKED；无越权文件；全套 pytest/ruff 通过。
- 必须运行的测试: 汇总各子任务证据；最终 `git diff --check` 与 frozen-surface diff 必须为空。
- 失败处理: 任一 owner gate/真实结果/数据许可问题立即 HOLD；不得以降级验证继续。
- 预期产物: 任务完成矩阵、验证证据、精确下一决策点。
- 完成后需要更新: `state/current.md`、`state/handoff.md`。
- see: `../../reports/milestone/2026-08-01-low-reasoning-development-roadmap.md`
