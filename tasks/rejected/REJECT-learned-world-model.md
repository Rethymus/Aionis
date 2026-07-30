# 否决 — 构建一个学习型生成式「世界模型」

- 编号: REJECT-world-model
- 标题: Build a learned generative world model
- 状态: rejected
- 目标: 为 Aionis 选定认知内核形态（学习型生成式世界模型曾是候选）。
- 背景: 学习型生成式「世界模型」曾被考虑作为项目的认知内核。
- 否决理由: 在 MVP 规模下**不可行且易泄漏**——典型案例：+7-Sharpe 的 ChaosAI 泄漏；
  Tan NeurIPS 2024；所需训练量达 100M+ tokens。学习型生成模型与本项目
  「反泄漏 / 可证伪」的内核冲突。
- 替代方案: TCR 保持 **discriminative / leakage-controlled / falsifiable**——采用
  **可解释的 scenario + network-propagation**，而非学习型生成模型。
- see: [`../../docs/frontier_positioning.md`](../../docs/frontier_positioning.md),
  [`../../docs/theory-of-computable-reality.md`](../../docs/theory-of-computable-reality.md),
  [`../../decisions/ADR-001-tcr-theoretical-frame.md`](../../decisions/ADR-001-tcr-theoretical-frame.md)
