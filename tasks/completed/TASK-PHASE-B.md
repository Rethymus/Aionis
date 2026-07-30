# Phase B — 基本面时点（filed vs period-end+lag）confirmatory run

- 编号: PHASE-B
- 标题: Phase B confirmatory run — fundamental timing (filed vs period-end+lag)
- 状态: completed
- 目标: 在 S&P500 PIT rank-IC 上检验双尾 differential claim——filed-date 时点臂是否优于
  period-end+lag 臂。
- 验收标准（全部已满足）:
  - [x] `config_committed` **先于**结果入 ledger。
  - [x] H6 bit-identical 确定性（verified）。
  - [x] 95% CI 跨 0。
  - [x] ci_half < 0.015（publishable-as-null 门）。
- 结果: **NULL SUPPORTED** — differential −0.0008，DM-p 0.87，ci_half 0.0098，n=125。
  判读：保守 lag 已足够，filed-date 精度无边际。
- ledger sig: `17245a75`
- spec: [`../../docs/phase-b-preregistration.md`](../../docs/phase-b-preregistration.md)
