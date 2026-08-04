# Track C confirmatory — Q1/Q2 owner-decision 简报（group 构造 + IC 聚合）

> 状态：**PROPOSED 决策辅助 · 2026-08-04 · opus**。这是 substantive 方法学决策（改估计量定义），非治理仪式。confirmatory 跑前须 owner 裁断。
>
> 依据：[`track-c-preregistration.md`](../../docs/track-c-preregistration.md) §1 claim、ledger #46（**未冻结 group 构造**）、[`2026-08-04-track-c-joint-fold-spec.md`](./2026-08-04-track-c-joint-fold-spec.md) D1/D2。

---

## 决策点

#46 `claim` = "dual-region cross-sectional monthly rank-IC"，但**未显式冻结** lambdarank 的 query group 如何构造。联合面板里，同一日历月同时含美股（USD 收益）+ A 股（CNY 收益）。**group 怎么定义决定"排序在谁之间发生"**——这是估计量定义，不是实现细节。

| 选项 | group 构造 | 排序范围 | 跨币种？ | 评价 |
|---|---|---|---|---|
| **(a) 统一月** | `year*12+month`（US+CN 同月同 query） | US 股与 CN 股互比 | **是**（5% USD vs 3% CNY 直接比） | 跨币种 label 污染；汇率变动混入排序 |
| **(b) 区域-月**（D1 推荐） | `(year*12+month)*2+region` | US 只与 US 比；CN 只与 CN 比 | **否** | 币种干净；模型仍联合 fit（共享参数，跨区学共性） |

**IC 聚合（Q2）**：group=(b) 时，IC 按区域内算（US IC、CN IC），联合 IC = 每月等权平均。group=(a) 时，IC 在统一横截面算（跨币种）。

---

## 推荐：(b) 区域-月 + 区域内 IC 等权联合

**理由**：
1. **币种干净**（核心）：forward_return 是本币收益；区域内排序消除汇率混淆变量。null-favored + anti-leakage 伦理偏好"消除已知混淆"。
2. **仍是联合模型**：一个 LightGBM，两区共享树结构——满足 §5"联合折叠"意图（跨区学共性 + DY spillover 跨市场信号进 regime_state）。
3. **可复现 + 可解释**：US IC / CN IC 分别报告 + 联合，诊断价值高。
4. **当前实现已用 (b)**：`track_c_joint.py:construct_region_month_groups` + combined_ic=mean(us,cn) 已是 (b)。exploratory 跑用 (b)。

**(a) 的唯一吸引力**：字面贴合"统一打分"（§1）。但"统一打分"可理解为"一个模型给所有股票打分"（(b) 也满足：一个模型，统一 score 空间），不必要求"统一排序空间"。故 (a) 的吸引力不足以抵消币种污染。

---

## 影响范围

- **代码**：`track_c_joint.py` 已实现 (b)；选 (a) 需改 `construct_region_month_groups` 为 `construct_month_groups`（复用 ranking_contract）+ 改 IC 聚合为统一横截面。改动小但改估计量定义。
- **spec**：#48 修订（meso US-only）同步加一句"group = region-month（区域内排序，币种干净）"到 §1/§4。
- **null-favored 契约**：不变（(a)/(b) 都两尾、都 null-favored；group 选择只改估计量定义，不改 SESOI/J-T 门）。

---

## owner 动作

confirmatory GO 时，在 #48 ledger 行的 config 里冻结 group 构造（`ranking_group: "region_month"` 或 `"unified_month"`）。推荐 `region_month`。exploratory 机器已用 `region_month`，故真实跑数字出来即 (b) 下的结果。

---

## 不越界声明

- `[F]` 本简报是决策辅助；未修改冻结面/ledger/prereg；未触 group 构造实现（(b) 已实现）。
- `[I]` owner 选 (a) = 改估计量定义 = 新 ledger 行冻结（与 #48 合并或独立）。
