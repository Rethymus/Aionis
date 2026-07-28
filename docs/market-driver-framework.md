# 市场驱动因素框架（Market Driver Framework）— TCR 潜在世界状态的 5 线特征分类法

> 状态：**v0.1 · 2026-07-28 · 治理文档（durable taxonomy，非一次性）**。
> 范围：把 [`theory-of-computable-reality.md`](theory-of-computable-reality.md)（TCR）§3.1
> 里抽象的潜在世界状态 $G_t=(V,E,\text{attr},w)$ **分解成 5 条可测、可审计的"市场驱动主线"**，
> 作为 Aionis 的**特征分类法（feature taxonomy）**：每一个特征/列被打上恰好一条主线的标签
> （或崩盘组合交互层）。这让 TCR 的 $\text{attr}$（State）从 PPT 词汇变成可逐项追溯的审计对象。
> 与 [`phase-b-preregistration.md`](phase-b-preregistration.md) §9（durable registry）、
> [`data-intake-rubric.md`](data-intake-rubric.md)（7 门）同源——分类法本身也是 durable 的：
> 新增一类特征 = 同一 benchmark 上的新预注册对比，**不是**新实验。
>
> 本框架是**表示 + 复用 + 可靠性**的落点切片，不是新理论、不碰任何代码。

---

## 0. 为什么需要这个框架（TCR 的 $G_t$ 怎么变得可测）

TCR §3.1 把世界状态定义成动态属性图 $G_t$，其中 $\text{attr}(v)$ 是各 Entity 的时变 State。
但「State」太抽象——它必须被**分解成一组互斥、可穷举、每个都能落到一个 PIT 数据列**的维度，
否则「世界状态」退化为文学概念（TCR §2 已警告）。本框架给出这个分解：

- **5 条主线**（§1）= $\text{attr}$ 的正交面，覆盖「基本面 × 折现率 × 风险偏好 × 资金/流动性 × 预期差」。
- **崩盘组合**（§2）= TCR §3.2 转移函数 $S_{t+1}=f(S_t,A_t,\varepsilon_t)$ 里的**反馈机制层**
  （非单事件→价格表）。
- **当前特征映射**（§3）= 逐项核对 Aionis 现有列落在哪条线、缺什么——gap 即未来 phase 的增量预注册 claim。
- **OSS 复用**（§4）= 哪些已审计的 permissive 轮子能补 gap，license-filtered。
- **可靠性机制状态**（§5）= 10 项反泄漏/反腐烂机制里 done vs gap 的账。

> 一句话：**5 线让 $G_t$ 可测；崩盘组合让 $f$ 可建模；§3-§5 让「每条线靠不靠得住」可审计。**
> 与 [`quant-selection-research.md`](quant-selection-research.md) §3（TCR→选股映射）互补——
> 那份讲 Entity/State/Event/Relationship 四原语；本份把 State 进一步切成 5 条可定价主线。

---

## 1. 移动股市的 5 条主线（特征分类法）

Aionis 采纳以下 5 线为**特征 taxonomy**。每个特征列归属**恰好一条**（或崩盘组合交互层）：

| # | 主线 | 经济直觉 | 典型可观测代理（PIT） |
|---|---|---|---|
| **①** | **企业未来现金流是否改变** | 股价 = 未来现金流的折现；现金流预期变了，价才动 | earnings、revenue、盈利惊喜（actual vs consensus） |
| **②** | **无风险利率是否改变** | 折现率的基准锚；利率↑→久期长的资产折现更深 | DFF、T-bills、term structure（1y/2y/10y） |
| **③** | **投资者要求的风险溢价是否改变** | 市场整体的风险偏好/补偿要求 | VIX、credit spread、EPU |
| **④** | **市场资金和流动性是否改变** | 谁在买、能买多少、被迫卖多少 | fund flows、margin、breadth、Fed 资产负债表 |
| **⑤** | **实际结果是否显著偏离既有预期** | 已定价的「预期」被「现实」打破的那一瞬 | macro surprises、earnings surprises、revision momentum |

**纪律约束**（贯穿 §3-§5）：

1. 每条线的每个代理**必须 PIT**——t 时刻的值不得依赖 >t 的信息（TCR §4 反泄漏纪律第 1 条；
   [`data-intake-rubric.md`](data-intake-rubric.md) G2）。
2. 不透明指标（EPU、Reddit sentiment 这类「被构造的指数」）**不得静默接入**——过 G3 无回改契约，
   否则快照 + sha256 冻结 + exploratory（G5）。
3. **选择偏差不是泄漏借口**：第 ⑤ 线的「事件集合」必须由 $I_t$ 内的**调度/披露规则**决定
   （FOMC 日历、FRED release 日期），不是事后显著性（TCR §4 第 4 条）。

---

## 2. 崩盘组合（Interaction / regime 层——**非**单事件→价格表）

严重下跌/暴涨**几乎从不是单一事件触发的线性映射**，而是**多条线同时恶化并正反馈**的组合：

> **高估值或拥挤仓位　＋　意外信息　＋　杠杆和保证金压力　＋　流动性不足　＋　被迫平仓或机械交易**

这五要素任意单看都解释不了崩盘；**组合 + 正反馈回路**才解释得了（被迫平仓砸低价格→
margin call→更多被迫平仓→流动性蒸发→机械策略触发→……）。在 TCR 里这对应 §3.2 转移函数
$S_{t+1}=f(S_t,A_t,\varepsilon_t)$ 的**反馈机制建模**，而非 §3.5 的单点可证伪锚 $y_{t+h}=h(\hat S_t)+\eta$。

**落点与边界**：

- **归属**：崩盘组合属于 TCR §7 的**关系（Phase C）+ 情景（Phase D）层**——网络传导、regime 切换、
  脆弱性/暴露，**不是** Phase B 横截面选股的 headline claim（Phase B 是 §3.5 那种 $y_{t+h}$ 单点锚）。
- **未来「stress-regime classifier」**：一个 regime 探测器（拥挤度 × 杠杆 × 流动性 的交互特征）是
  §3 表中 ③④ gap 兑现后的自然产物，但**它本身不作第二个证伪锚**——TCR §8 已定：情景难证伪
  （"情景没发生"是永久借口），证伪永远走 $y_{t+h}$。
- **明确不做**：把崩盘当成「单事件→价格跌幅」的查找表——那是过拟合的伪结构，不是机制建模。

---

## 3. Aionis 当前特征 → 5 线映射（含 gap）

> 「当前」列已逐项核对源码：`features/selection_panel.py`、`ingest/fundamentals.py`、
> `features/macro_surprise.py`、`ingest/market.py`。Gap = 未来 phase 的增量预注册 claim。

| 线 | Aionis 当前（已落地） | Gap（未来 phase） |
|---|---|---|
| **① 现金流** | `fundamentals.py:METRIC_TAGS`（assets/equity/revenue/net_income/shares_out/long_term_debt）+ Phase B `fundamentals.py:pit_align`（`align_on="filed"`，filed-date 时点） | **earnings SURPRISES**（actual vs consensus；consensus 需付费或统计代理——见 §6 启示） |
| **② 无风险利率** | DFF via FRED 宏观广播机制（`selection_panel.py:fred_series` → `build_selection_panel` 跨截面 broadcast）✓ | **term structure**（1y/2y/10y，同走 FRED `fred_series`，一行配置） |
| **③ 风险溢价** | FF5 部分代理（`selection_panel.py:fama_french_daily` 的 HML/SMB/Mkt-RF） | **VIX via FRED**（PIT-safe、已在栈内路径）、**credit spread**（ICE BofA via FRED）、**EPU**（**G3 ✗ 回改历史 → 快照强制 + exploratory**，见 [`data-intake-rubric.md`](data-intake-rubric.md) G3） |
| **④ 资金/流动性** | FF5 部分代理（RMW/CMA——盈利/投资因子，资金配置的粗代理） | **fund flows**（ARK/13F via EDGAR）、**margin**、**breadth**、**Fed 资产负债表**（FRED `WALCL`） |
| **⑤ 实际 vs 预期** | `macro_surprise.py`（CPI/NFP via ALFRED as-of，`merge_asof(..., allow_exact_matches=False)` 钉 vintage；FOMC 无数据惊喜）✓ | **earnings surprise**、**revision momentum**（analyst 修订动量） |

**两点诚实注**：

- FF5 因子是**因子模拟组合收益**（portfolio returns），用作 ③④ 的代理是**粗的**——真正的风险偏好/流动性
  信号在 gap 列（VIX、credit spread、fund flows）。Phase B 两臂**同享** FF5，故 FF5 不进入 filed-date 增量
  claim 的隔离（[`phase-b-preregistration.md`](phase-b-preregistration.md) §2）。
- 第 ⑤ 线的 `macro_surprise.py` 用**统计期望**（trailing mean）替代 survey consensus——因为 Bloomberg/Blue
  Chip 付费。这是公告效应文献认可的 fallback（Pearce-Roley 1985、Scotti 2016；见 `macro_surprise.py` 模块
  docstring），但 earnings surprise 的 consensus 同样面临付费墙 → §6 启示适用。

---

## 4. OSS 复用（license-filtered）

> Aionis 是 permissive-only（见 [`data-license-allowlist.md`](data-license-allowlist.md)）。
> 复用原则（**xiaoyinsi 教训**，§6）：**借方法论，留 PIT-safe 数据源**——不借不透明数据层。

**REUSABLE（license OK）**：

| 项目 | License | 角色 |
|---|---|---|
| **`microsoft/qlib`** | MIT | **脚手架**（已选，见 [`quant-selection-research.md`](quant-selection-research.md) §6 层 0）；4 个手术点把 PIT-DB 时间戳钉 filed-date |
| **`akfamily/akshare`** | MIT | 中国宏观数据 |
| **`ranaroussi/yfinance`** | Apache | 价格（**本环境 IP-blocked**；保留可移植性，见 `market.py:_from_yfinance`） |
| **`JerBouma/FinanceToolkit`** | MIT | **公式透明度**：Piotroski-F / Altman-Z / Beneish-M 的**可审计定义**；**借公式不借 FMP 付费数据层**（数据仍走 EDGAR） |
| **`ranaroussi/quantstats`** | Apache | 风险报告 tear-sheet **framing**（`dashboard/` 已按 pattern 借用「headline metric + gate」框架，见 `dashboard/README.md` 复用核算） |
| **`AI4Finance-Foundation/FinGPT`** | MIT | 文本→结构化事件（Phase C ERL 候选骨干） |
| **`AI4Finance-Foundation/FinRL`** | MIT | 基建（换掉其 yfinance provider） |

**EXCLUDED（license 墙）**：

| 项目 | License | 拒因 |
|---|---|---|
| `OpenBB` | AGPL-3.0 | 网络使用触发开源义务 → 传染 MIT 栈 |
| `polakowo/vectorbt` | Commons-Clause | 非 OSI 自由；禁商用出售 |
| `mementum/backtrader` | GPL-3.0 | Copyleft 传染 |
| `freqtrade/freqtrade` | GPL-3.0 | Copyleft 传染 |
| `quantopian/zipline` | Apache（**2020 起停更**） | 维护性雷（`zipline-reloaded` 为其活跃 fork，已在 [`quant-selection-research.md`](quant-selection-research.md) §6 备选） |

**关键定位**：Aionis **不试图**变成 OpenBB / qlib——它是一个**聚焦的反泄漏研究 pipeline**，把这些
（license-OK 的）项目当**组件**复用。FinanceToolkit 的价值是**公式透明度**（复杂指标的**可审计**定义，
数据仍来自 EDGAR），正是 xiaoyinsi 教训的镜像：借方法论，留 PIT-safe 数据源。

---

## 5. 数据可靠性机制状态（10 项——done vs gap）

> 反泄漏不只在「用未来标签训模型」；**数据本身**就会泄漏（[`data-intake-rubric.md`](data-intake-rubric.md) §0）。
> 以下是 10 项机制的当前账：

**DONE（6/10）**：

| # | 机制 | 落点 |
|---|---|---|
| ④ | **PIT 时点** | `fundamentals.py:pit_align`（`merge_asof(direction='backward')` on filed）；`universe.py:constituents_on`（`≤ date` 最新成员，无 forward-fill）；`universe.py:mask_panel_to_pit`（截面 = 当时的 PIT 成员，**非**今天的 500） |
| ③ | **revision-versioning** | `universe.py:_sha256`（raw cache 哈希）；`macro_surprise.py` 的 ALFRED as-of vintage join（钉发布时刻） |
| ⑧ | **survivorship 诚实** | hanshof/pierrebrunelle PIT universe（[`quant-selection-research.md`](quant-selection-research.md) §8.4：可缓解不可根除；headline = 保守上界） |
| ⑨ | **license** | [`data-license-allowlist.md`](data-license-allowlist.md)（G1 落表） |
| ⑩ | **raw archival** | `data/cache/`（EDGAR facts / ALFRED JSON / hanshof CSV / pierrebrunelle tar.gz 全 sha256-pinnable，rerun 零 HTTP） |
| ① | **source-field provenance** | XBRL fact 带可审计来源字段（`form` 10-K/10-Q、`fy`/`fp` 财年期间、`unit`、`filed`/`end`——见 `fundamentals.py:_extract`），非不透明单值 |

**GAPS（4/10，roadmap）**：

| # | 机制 | 状态 / 计划 |
|---|---|---|
| ⑤ | **multi-source cross-validation** | 目前 2-source 只在 universe（hanshof vs pierrebrunelle Jaccard）+ 价格（Tiingo vs Alpaca 同值交叉）做；**基本面/宏观的 2-source 比较未系统化** |
| ⑥ | **anomaly detection** | 价格 interior-NaN 已断言（`market.py:fetch_prices` 的 gap 校验），但**adj-error / 跳变 / split 异常的自动检测**未做 |
| ⑦ | **corporate-actions** | splits/dividends/M&A 当前**委托**给 Tiingo/Alpaca 的 `adjustment='all'`（`market.py:_from_alpaca`、`_from_tiingo` 的 adjClose），**未独立审计** |
| ② | **fetch-vs-publish-time** | 部分（ALFRED `realtime_start` 钉发布时刻），但**未系统化**为全源统一字段 |

> ⑤⑦ 是 §3 gap 兑现时最易暴露的可靠性弱项：补 fund flows（④）/ earnings surprise（①⑤）时，
> 必须同步把 2-source 校验 + corporate-action 审计补上，否则新数据带新腐烂。

---

## 6. xiaoyinsi 构造方法论（**参考价值，非数据集成**）

> xiaoyinsi **不是 PIT-safe**（见 [`data-intake-rubric.md`](data-intake-rubric.md) 接入决策表 +
> aionis-xiaoyinsi memory）。本节取其**构造方法论**，**不**集成其数据。这是「借方法论，留 PIT-safe 源」
> 原则的活样本。

### 6.1 Trump TACO 指数构造

**其构造**：Brent / 美国 10Y（TNX）/ Hormuz 通航阻断指示 / S&P 500 的复合；各分量 σ-归一化 → 加权 →
`score = 原始σ / 2.9 * 100`（约 2.9σ → 100），5 级分档，锚=100；压力越高 → 越可能让步 → 缓和/看多。

**泄漏根**：σ 分档在**不断增长的历史**上重算 → **过去的分数被追溯漂移**（典型 G3 违反）。

**Aionis PIT-safe 类比**：用 FRED 序列（VIX + credit spread + term spread + DFF surprises）构造一个
**「政策压力复合指标」**，σ-归一化在**每个 t 冻结的窗口**上算（expanding-but-as-of-fixed，
**绝不追溯重算**）——即把 TACO 的「复合思路」嫁接到 PIT-safe 的 FRED 源上。

### 6.2 Reddit sentiment 时序构造

**其构造**：逐 ticker 逐日的 mentions/sentiment/bull_ratio/score_sum/users，跨 subreddit 聚合；
打分器 = 不透明 NLP。

**Aionis PIT-safe 类比**：`PRAW`（BSD）**前向采集** + `FinBERT`（Apache）打分，**到达即快照**（snapshot-on-arrival）。
**不做历史 backfill**——Pushshift 已死，无 permissive 历史源（[`data-intake-rubric.md`](data-intake-rubric.md)
接入决策表：Reddit/StockTwits 仅前向采集）。

> 共同教训：**不透明指数 = 选择偏差 + 回改风险双重雷**（TCR §3.3 的 $b_k$ + §4 的 G3）。
> 借其「怎么构造」的思路，数据走 PIT-safe 源、打分器用可审计模型、到达即冻结。

---

## 7. 与现有文档的关系

| 文档 | 本框架的交叉点 |
|---|---|
| [`theory-of-computable-reality.md`](theory-of-computable-reality.md) | §1 的 5 线 = TCR §3.1 $G_t$ 的 $\text{attr}$ 分解；§2 崩盘组合 = TCR §3.2 转移 $f$ 的反馈层；§1 纪律 = TCR §4 反泄漏纪律 |
| [`phase-b-preregistration.md`](phase-b-preregistration.md) | §3 的「① 现金流 filed-date」= Phase B `arm_state` vs `arm_base` 的核心 claim；FF5 跨两臂共享故不进隔离（§2） |
| [`data-intake-rubric.md`](data-intake-rubric.md) | §1 纪律 = G2（PIT）/ G3（无回改）；§3 EPU 的 G3 ✗ → 快照强制 + exploratory；§6 xiaoyinsi 的 G2 ✗ |
| [`quant-selection-research.md`](quant-selection-research.md) | §4 qlib 脚手架 + 4 手术点；§3 的「可证伪锚 = $y_{t+h}$」与本框架「崩盘组合不作第二锚」一致 |
| [`data-license-allowlist.md`](data-license-allowlist.md) | §4 OSS 复用的 license 判据（ACCEPTED/REJECTED）；FinanceToolkit「借公式不借数据层」的合规基础 |

---

## 8. 下一步（本框架通过评审后）

1. 评审本框架（critic pass：5 线是否正交可穷举、§3 当前列是否与源码一致、§5 done/gap 是否诚实）。
2. 把 §3 gap 里的**优先项**排进 phase 路线：② term structure（一行 FRED 配置，最低成本）→
   ③ VIX via FRED（已 PIT-safe 路径）→ ④ fund flows via EDGAR（成本高，需同步补 §5 ⑤⑦）。
3. 每个 gap 兑现 = 同一 benchmark 上的**增量预注册对比**（非新实验），config sha256 先于 OOS 结果
   入 `runs/ledger.jsonl`（[`phase-b-preregistration.md`](phase-b-preregistration.md) §9）。
4. §2 崩盘组合的「stress-regime classifier」在 ③④ gap 兑现后立项，**始终不作第二证伪锚**。

> 诚实标准不变：本框架是分类法，不产生可发表 claim；任何 claim 仍走 $y_{t+h}$、CI 跨 0 不得宣称正向、
> 每个 phase 的选择都进 run ledger。
