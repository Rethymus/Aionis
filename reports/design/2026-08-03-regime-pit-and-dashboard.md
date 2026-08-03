# 条件化 regime PIT 定义 + 入手/跑路仪表盘层（Option A′ gate 7 regime + gate 8）

> 日期：2026-08-03
> 类型：设计笔记（**PROPOSED**，非 ADR、非冻结）
> 目标：把 owner 原始愿景（板块走向 + 整体趋势 + 跨市场传染 + 入手/跑路）在 Aionis 的 PIT / 可证伪纪律内落地。
> 关联：[`market-driver-framework.md`](../../docs/market-driver-framework.md) §2/§6.1/§8、[`theory-of-computable-reality.md`](../../docs/theory-of-computable-reality.md) §3.1（micro→meso→macro→global）、[`2026-08-03-conditional-rank-ic-multiplicity.md`](2026-08-03-conditional-rank-ic-multiplicity.md)、[`2026-08-03-track-c-prereg-skeleton.md`](2026-08-03-track-c-prereg-skeleton.md) §1/§11/§12。

## 0. 定位

owner 的"板块 / 整体趋势 / 跨市场传染 / 入手跑路"= TCR 的 **meso / macro / global 层** + 一个决策辅助显示。
在 Aionis 纪律里它们分两处落：
- **regime 特征**（meso/macro/global）→ 喂 rank-IC 的**条件化交互**（gate 7），**不作第二证伪锚**（`market-driver-framework.md:70-74,216`）。
- **"入手/跑路"仪表盘** → **非主张探索层**（gate 8），不进 headline / 不进 ledger 确认行。

## 1. 三层 regime（micro 之上，全 PIT 构造）

| 层 | 经济含义 | PIT 指标（**复用轮子**） |
|---|---|---|
| **meso 板块** | 行业相对强弱 | 板块动量：美股复用 Phase D SIC-peer momentum；A 股待申万（SWFC）行业映射 |
| **macro 市场** | 整体风险偏好/状态 | `market-driver-framework.md` §3 **5 线**：VIX-via-FRED + credit spread + term spread + DFF surprise + EPU（EPU 已 G3 标记 exploratory）。部分已落地（FRED/ALFRED），部分 gap |
| **global 跨市场传染** | US↔CN 溢出 | **Diebold-Yilmaz spillover**：`connectedness`（PyPI，`franrolotti/connectedness`）或 `diebold-yilmaz`（PyPI，MIT）— US↔CN 收益率面板的 total/directional/net spillover。POC §2.1 已查证存在 |

**PIT 铁律（防批判者 M1 regime 定义泄漏）：** 每个 regime 指标的 σ-归一化 / 分档在**每个 t 冻结的 expanding-as-of 窗**上算，**绝不追溯重算**（`market-driver-framework.md:178-181` TACO 教训：xiaoyinsi TACO 因 σ 分档在增长历史上重算 → 过去分数漂移 = G3 违反）。

⚠️ **命名碰撞**：`connectedness` 的 "PIT normality transform" = **概率积分变换**（copula 统计），**非** point-in-time。别误以为它解决时点泄漏——它没有。

## 2. 入手/跑路仪表盘层（gate 8，**非主张**）

- 三层 regime 状态 → 一个 0–100 综合温度（PIT 安全版，类比 TACO 但 as-of 固定窗）→ "入手/跑路"提示。
- **非主张纪律**：
  - 明确标注"**探索性 / 非投资建议**"（与现有 Pages 站 banner 一致）。
  - 轻量 PIT 合同：指标全 PIT + snapshot+sha256 冻结（G4）。
  - **不作证伪 claim、不进 headline、不进 ledger 确认行**。
- **若 owner 要问责**（批判者 #5/#9）→ 单独的**二级 timing 预注册**（自己的 estimand/SESOI/ledger）；但默认非主张，避免与 rank-IC 主张混淆。

## 3. 与 rank-IC 的接驳（gate 7）

三层 regime 作为**单个预指定交互项** `treatment × regime_state` 喂 rank-IC（multiplicity 笔记 §1：预算 1，非 K）。
`regime_state` = 三层 PIT 指标的**预指定组合**（owner 冻结前定，非事后挑），服从 TACO as-of 固定窗构造。

## 4. owner-decision 点（PROPOSED，待冻结）

1. meso 板块定义（美股 SIC vs A 股申万）。
2. macro 5 线权重 + 哪些进 regime_state（VIX/credit/term 已 PIT-safe；EPU exploratory）。
3. global spillover 的资产集（US 指数 + A 股指数 + 板块 ETF？）+ 滚动窗长。
4. regime_state 组合函数（线性加权 vs 分档）+ TACO as-of 窗参数。
5. 仪表盘是否升级为二级 timing 预注册（问责 vs 非主张）。

## 5. 不越界声明

- PROPOSED 设计；未触冻结面 / ledger / prereg / ADR / config / 结果 / E3。
- 未运行脚本；未观察 outcome。
- regime 具体阈值 / 组合待 owner 冻结；仪表盘默认非主张。
- Diebold-Yilmaz 轮子的最终选型（`connectedness` vs `diebold-yilmaz`）待集成时定（均 permissive，POC 已查）。
