# Baseline Ladder — 索引

> 强基线阶梯（RES 系列）：在 frozen Phase B/C/D/E1 九列数值基本面基线之上，逐步增加
> **横截面可排名**的股票特定特征与 rank-aware learner。所有基线均为**新 config + 新 ledger
> 行**（ADR-006），绝不静默修改 B/C/D/E1 结果。

## 已准备的基线（准备完成，owner 授权前不注册、不写 ledger）

| 基线 | 任务 | 特征设计 | 文档 | 状态 |
|---|---|---|---|---|
| **BASELINE-FF5-001** | RES-02 | 股票特定 FF5 滚动暴露 + 因子载荷×特征交互（原始市场级因子列被 RD-13 结构性排除） | [`baseline-ladder-ff5.md`](baseline-ladder-ff5.md) + [`data-intake-french-ff5.md`](data-intake-french-ff5.md) | **prepared** — owner 签注 + trial 授权 + ledger `config_committed` 行待 owner |
| **BASELINE-RANK-001** | RES-03 | rank-aware lambdarank learner（锚定冻结 RD-15 `ranking_contract.py`），特征同 frozen B | [`baseline-ladder-rank.md`](baseline-ladder-rank.md) | **prepared** — owner 授权 + ledger `config_committed` 行待 owner |

## 共同约束（所有基线）

- **横截面可排名**：特征必须股票特定、月内可变（RD-13 非-常量护栏；原始市场-wide 因子列禁用）。
- **PIT**：release-date/vintage discipline；无同月未来使用。
- **config_committed 先于 result**：runner 在 owner 的 `config_committed` ledger 行存在前
  **拒绝运行**（`RES_02_NO_LEDGER=1` 仅用于 H6 检查）。
- **H6 确定性**：n_jobs=1 / seed=0 / version-pinned / bit-identical 重跑。
- 不触碰 frozen B/C/D/E1 结果、冻结 prereg/ADR/config。
