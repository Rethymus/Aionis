# 决策门禁 — E2 (LLM macro-causal, cutoff-controlled) vs 启动 E3 (forward-live) vs 其他

- 编号: STRAT
- 标题: Decision gate — build E2 (LLM macro-causal, cutoff-controlled) vs launch E3 (forward-live) vs 其他
- 状态: awaiting owner steer（决策门禁 — HOLD）
- 目标: 产出一项**记录在案**的 GO / PIVOT / HOLD 决策（落在 `decisions/` 的一篇 ADR），
  决定 TCR 路线图在 E2 与 E3 之间的下一步投入方向。
- 背景: E2 的回测**欠功率**——cutoff 门把 125 个月的 OOS 窗压缩到约 10–18 个 cutoff 后月份，
  即便有信号也极可能检不出。E3 forward-live 是**唯一零泄漏且有功率**的路径，但需要日历时间
  （年级别）积累 OOS 样本。两条路都非「立即出结果」，故设此门禁由 owner 裁决。
- 允许修改: `decisions/**`（新建 ADR）、`state/current.md`、`state/handoff.md`、
  本任务文件状态字段。**不得**改动 confirmatory 流水线源码或 ledger。
- 禁止修改: `runs/ledger.jsonl`、`docs/phase-*-preregistration.md`、`src/**`、`scripts/**`。
- 前置条件: owner 已审阅 `docs/phase-e2-preregistration.md` 与 `docs/phase-e3-preregistration.md`。
- 实施要求: 决策必须为**书面 verdict + 再评估触发条件**（如「E3 累计满 N 个月或出现 X 事件后重评」）。
  不得在无 owner 裁决下 speculative 地开工 E2 或 E3 实现。
- 验收标准:
  - [ ] `decisions/` 下存在一篇 ADR 记录 verdict（GO / PIVOT / HOLD 之一）。
  - [ ] ADR 含明确的**再评估触发条件**与日期。
  - [ ] `state/current.md` / `state/handoff.md` 同步本决策。
- 失败处理: 默认 **HOLD**（两条 spec build 都不开工），等待 owner steer。
- 预期产物: 一篇 ADR（如 `decisions/ADR-00X-e2-vs-e3-verdict.md`）+ state 同步。
- 完成后需要更新: `state/current.md`、`state/handoff.md`、`docs/RESULTS.md`（若 verdict 改路线图叙述）。
