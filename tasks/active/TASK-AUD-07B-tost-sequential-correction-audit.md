# AUD-07B — TOST 与序贯等价判定纠错审查

- 编号: AUD-07B
- 标题: 在任何 E3 outcome 可见或裁决代码实现前，重新证明 ADR-010 的等价判定方向与错误率控制。
- 状态: **P0 HOLD — requires strong statistician + owner decision; do not delegate to low-reasoning model**
- Priority: **P0**
- Size: **M**
- Risk: **CRITICAL**（错误公式会把不等价误判为等价）
- 目标: outcome-blind 地核对 TOST 两个 null/p-value 拒绝方向、90% CI 等价关系，以及三次 look 下
  O'Brien-Fleming spending 与 equivalence composite null 的一致构造；输出纠错建议，不直接改 frozen ADR。
- 背景: ADR-010 amendment 当前要求两个 one-sided p-value “exceed alpha”，疑似与 TOST 拒绝规则
  反向；同时固定 90% CI + look-specific alpha 是否控制 sequential Type I error 未被实现级证明。
- 允许修改: 新增 `reports/audits/e3-tost-sequential-correction-review.md`；本任务状态；state/handoff。
- 禁止修改: `decisions/ADR-010*`、phase prereg、源码/tests、ledger/results/forward/data/config；禁止读取
  E3 outcome 或运行 score/reveal/phase/strategy/horizon/forward。
- 前置条件: 使用统计方法原文/教材与现有公开 frozen 数值；至少一名独立强 Reviewer。
- 实施要求: 明列 H01/H02、test statistic、p-value rejection direction、CI duality；比较合法的
  group-sequential equivalence construction或明确 HOLD；不得用模型共识替代数学证明。
- 验收标准: Reviewer 对每条公式给 PASS/FAIL；明确 ADR/pre-reg 是否需 owner-authorized amendment；
  在纠正前 E3 inferential verdict 与 headline 保持 HOLD；无 outcome/frozen-surface 变更。
- 必须运行的测试: prose/formula independent review；`git diff --check`；frozen-file diff 为空。
- 失败处理: 无法证明错误率控制即 HOLD，不得沿用现有文字实现。
- 预期产物: 公式核对表、反例/模拟设计建议、owner decision packet；无研究结果。
- 完成后需要更新: owner 决定是否建立新的 ADR amendment implementation task。
- see: `../../decisions/ADR-010-sesoi-tost-sequential-gate.md`
