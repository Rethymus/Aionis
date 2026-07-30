# Phase E1 — 结构化跨公司冲击传导（SIC-peer shocks, ex-self）confirmatory run

- 编号: PHASE-E1
- 标题: Phase E1 confirmatory run — structural cross-firm shock propagation (SIC-peer shocks, ex-self)
- 状态: completed
- 目标: 检验双尾 differential claim——结构化跨公司冲击传导（SIC 同业冲击，ex-self）臂是否优于
  fundamentals-only 基线臂。E 序列 umbrella 下的第一条 confirmatory。
- 验收标准（全部已满足）:
  - [x] `config_committed` **先于**结果入 ledger。
  - [x] H6 bit-identical 确定性（verified）。
  - [x] 95% CI 跨 0。
  - [x] ci_half < 0.015（publishable-as-null 门；**四阶段中最紧**）。
- 结果: **NULL SUPPORTED** — differential −0.0028，DM-p 0.53，ci_half 0.0087（四阶段最紧），n=125。
  判读：结构化跨公司冲击传导在月频已被有效定价，零泄漏路径下仍 null。
- ledger sig: `ef321e9e`
- spec: [`../../docs/phase-e-preregistration.md`](../../docs/phase-e-preregistration.md)（E 序列 umbrella）
