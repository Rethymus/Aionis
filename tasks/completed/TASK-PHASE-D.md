# Phase D — 关系 bundle（SIC 同业动量 + 13D 事件）confirmatory run

- 编号: PHASE-D
- 标题: Phase D confirmatory run — relationship bundle (SIC peer-momentum + 13D events)
- 状态: completed
- 目标: 检验双尾 differential claim——关系 bundle（`peer_mom` + `stakes_13d_event`）臂是否优于
  fundamentals-only 基线臂。
- 验收标准（全部已满足）:
  - [x] `config_committed` **先于**结果入 ledger。
  - [x] H6 bit-identical 确定性（verified）。
  - [x] 95% CI 跨 0。
  - [x] ci_half < 0.015（publishable-as-null 门；三阶段中最紧）。
- 结果: **NULL SUPPORTED** — differential −0.0030，DM-p 0.60，ci_half 0.0107，n=125。
  判读：同业关系与维权持仓信号在月频已被有效定价。bundle-shuffle placebo 增量消失（DM-p 0.538）。
- ledger sig: `d3158063`
- spec: [`../../docs/phase-d-preregistration.md`](../../docs/phase-d-preregistration.md)
