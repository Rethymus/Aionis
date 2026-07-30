# Phase C — 世界状态惊喜 bundle（CPI/NFP/VIX/earnings）confirmatory run

- 编号: PHASE-C
- 标题: Phase C confirmatory run — world-state surprise bundle
- 状态: completed
- 目标: 检验双尾 differential claim——惊喜 bundle（CPI/NFP/VIX/earnings surprise）臂是否优于
  fundamentals-only 基线臂。
- 验收标准（全部已满足）:
  - [x] `config_committed` **先于**结果入 ledger。
  - [x] H6 bit-identical 确定性（verified）。
  - [x] 95% CI 跨 0。
  - [x] ci_half < 0.015（publishable-as-null 门）。
- 结果: **NULL SUPPORTED** — differential −0.0065，DM-p 0.36，ci_half 0.0130，n=125。
  判读：世界状态惊喜在月频已被有效定价，且 CI 紧到可发表 null。leave-one-out 无单一主导分量。
- ledger sig: `a7fdb48f`
- spec: [`../../docs/phase-c-preregistration.md`](../../docs/phase-c-preregistration.md)
