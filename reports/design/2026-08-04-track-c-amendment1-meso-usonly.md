# Track C 预注册 修订 #48（PROPOSED）— meso 层收窄为 US-only（confirmatory）

> 状态：**PROPOSED · 2026-08-04 · 待 owner GO（= 新 ledger 行 #48 = 冻结）**。本文件**不修改**冻结的 `docs/track-c-preregistration.md`（#46）；正式化 = owner 授权写 `config_committed` ledger 行 #48 + 同步 prereg §1.1。
>
> 依据：[`2026-08-04-shenwan-meso-7gate.md`](./2026-08-04-shenwan-meso-7gate.md)（CN 申万 via baostock G3 结构性 fail → exploratory-only）。
> 先例：修订 #47（cninfo 基本面 → exploratory）同构处置。

---

## 0. 动机

7-gate 核验裁定：**baostock 申万行业分类 G3 不可证**（无 as-of/vintage；SWFC-2014→2021 回填污染 pre-2021；同 baostock-基本面先例）。按数据接入 rubric 判定矩阵（G1+G2 过+**G3 不可证** → 快照冻结 + exploratory-only），CN 申万 meso **不得进 confirmatory headline**。

故 Track C 的 meso 层须从「US SIC + CN 申万 等权」收窄为 **US SIC only**（EDGAR 公共域，PIT）。

**关键**：这**正好是当前实现**（`regime_meso.py` 默认 `enable_cn_fetch=False`）。本修订 = **正式化现有状态为 spec-faithful confirmatory config**，非新方向、非重测。本会话早先「3-layer US-only-meso 双区 conditional-IC null」（β_US=-0.001 p=0.95；β_CN=+0.015 p=0.36）即 spec-faithful exploratory 结果。

---

## 1. §1.1 delta（meso 层）

| 项 | #46（现行 FROZEN） | 修订 #48（PROPOSED） |
|---|---|---|
| meso 层组成 | US SIC-peer 动量 + CN 申万（SWFC）行业动量，等权 | **US SIC-peer 动量 only**（EDGAR 公共域 PIT） |
| CN 申万 | headline | **exploratory-only**（快照 + sha256，作 meso 诊断层；不进 headline/不进 confirmatory regime_state） |
| 其余两层（macro / global DY spillover） | 不变 | 不变 |

**对其余 §段零改动**：§1 claim、§2 universe、§3 features（A 股 cninfo 基本面已于 #47 降 exploratory）、§4 learner、§5 联合折叠、§6 horizon、§7 J-T 门、§8 multiplicity、§9 baseline — 全部沿用 #46。

---

## 2. 对 confirmatory 估计量的净影响

- **regime_state composite**：三层 → meso 现为 US-only（macro + global DY + meso_us）；CN 侧不贡献 meso。**这正是已实现的 `regime_composite.parquet`**（sha256 `0cb7409e`，3-layer with US-only meso）。
- **联合折叠**（`src/aionis/eval/track_c_joint.py`，commit `841fee4`）：不依赖 meso 的 CN 侧——regime_state 是任意外生 PIT 序列。**0 改动**。
- **claim 措辞**：双区域"对称"只在**价格层**对称（US+CN 共享 10 price 特征 + 联合折叠）；基本面（#47）+ meso（本修订）的 CN 侧均 exploratory。confirmatory claim 实际 = **「US-led 双区域价格条件化 rank-IC，CN 作价格侧条件化样本 + 跨市场传染（DY spillover）信号源」**。

---

## 3. 仍是 null-favored，仍是双尾

收窄不改变统计契约：单预指定交互 `score × regime_state`（multiplicity 预算 1）；SESOI ±0.010；J-T 等价门（looks 60/90/120，RCI levels 99.44/97.64/95.00%）。null = 下注热门 = 可发表。收窄是**保守合规**（A 股 G3-fail 数据降级），非"rescue"。

---

## 4. owner 动作（正式化 = 冻结 #48）

1. owner 审本 PROPOSED → 认可收窄方向。
2. owner 授权写 `config_committed` ledger 行 **#48**（phase=track_c；config = #46 的浅拷贝 + meso 字段改 US-only-only + amendment 引用本文件 + 7-gate 报告 sha256）。复用 `scripts/track_c_commit.py`（append-only，sha256 自洽）。
3. 同步 `docs/track-c-preregistration.md` §1.1（meso = US-only for confirmatory；CN 申万 exploratory 标注）+ §13 不越界声明更新为 #48 FROZEN。
4. 冻结后允许 confirmatory 跑（仍需 Q1 group 构造签注 + Q5 GO）。

---

## 5. 不越界声明（PROPOSED）

- `[F]` 本文件是 PROPOSED 修订草案；**未修改** `docs/track-c-preregistration.md`（#46 冻结）；未写 ledger；未触 B/C/D/E1 + Track B 冻结面。
- `[F]` 依据（7-gate G3 fail）来自 doc/代码推理（Lane A agent [1210] 死，opus 接手）；保守 fail-safe。
- `[I]` 正式化 = owner GO + 新 ledger 行 #48；CN 申万若日后有 permissive PIT 源（自建/Tushare），可再 amend（新行）升格。
