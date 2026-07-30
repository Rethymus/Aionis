# 否决 — 把 E2 (LLM macro-causal) 回测当作 primary confirmatory claim

- 编号: REJECT-e2-primary
- 标题: Treat the E2 (LLM macro-causal) backtest as the primary confirmatory claim
- 状态: rejected
- 目标: 判定 E2 回测是否可作为项目的 primary confirmatory claim（结论：不可）。
- 背景: E2 被设计为一个 LLM macro-causal 假设生成器，带 cutoff 控制（缓解而非消除
  current-LLM hindsight 泄漏）。
- 否决理由: (1) **cutoff 门摧毁统计功率**——125 个月 OOS 窗在 cutoff 后坍缩到约 10–18 个月，
  即便存在信号也极可能检不出 → underpowered；(2) current-LLM hindsight 泄漏只是**缓解**，
  未消除。故 E2 回测不满足 primary confirmatory 的「有功率 + 零泄漏」双重门槛。
- 替代方案: **E3 forward-live 积累**是唯一**有功率且零泄漏**的路径——向前运行不存在「未来」可泄漏
  （no future to leak, by construction）。代价是需要日历时间（年级别）积累功率。见
  active 决策门禁 `TASK-STRAT-e2-vs-e3-decision.md`。
- see: [`../../decisions/ADR-005-e2-underpowered-e3-forward-live.md`](../../decisions/ADR-005-e2-underpowered-e3-forward-live.md),
  [`../../docs/phase-e2-preregistration.md`](../../docs/phase-e2-preregistration.md),
  [`../../docs/phase-e3-preregistration.md`](../../docs/phase-e3-preregistration.md)
