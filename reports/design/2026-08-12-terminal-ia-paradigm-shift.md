# 终端 IA 第三次重组 — 从"分析师工作流"范式转向"科学效度论证"范式（PROPOSED）

> 业主诉求（2026-08-12，第三次）：把"七主题"彻底打散，连同"定调/定标/佐证/问责"等
> **所有**内容参数全部打散重分配，重组成**紧凑、自洽、科学、创新**的系统；**不再区分
> 一二三四**；用**科学的排布、前沿的经验、科技的智慧**；**深度探索所有 github 开源仓库，
> 把能复用的全利用上，不惜代价**。
>
> 这是**设计决策文档**（PROPOSED），需业主定帧后再动代码。**0 ledger / frozen surface /
> config / prereg / ADR 改动**。遵循 `aionis-owner-process-correction`（重大决定前批判性自审
> 至有据可执行）+ `aionis-owner-prefers-chinese-review-content`（审阅内容用中文）。

---

## 0. 为什么前两次都失败了 —— 范式错位（核心诊断）

我复盘了 `2026-08-09-terminal-ia-redesign.md`（6 步漏斗）与 `9d260c9`/`ed27f4f`（四枢纽
①-④），结论是：**两次都是同一个范式换了标签**，所以业主两次都拒。

| 迭代 | 结构 | 范式 | 业主反应 |
|---|---|---|---|
| 第 1 次 | 6 步漏斗 ①定调→②定向→③定标→④佐证→⑤问责→⑥边界 | **人类分析师的工作流**（看市场→选股→验证→复盘） | "生硬 / 像拼凑杂烩" |
| 第 2 次 | 四枢纽 ①-④ + L0-L4 数据漏斗 + ①-⑥ role 标签 | **同一个工作流**，只是从 6 步压到 4 步 | "还是一二三四，要彻底科学重组" |

**三套重叠的编号**同时活在 `dict.ts:12-45` 里：`nav.group` 是 ①-④ 枢纽、`themes.funnel`
是 L0-L4、各模块 `.role` 又是 ①-⑥。这正是"拼凑杂烩"的物质证据——不是数据不好看，是
**组织原则本身是人手拍的分类法**，每改一次就再拍一次。

**根因（一句话）**：我一直按"**一个选股分析师怎么思考**"来组织终端。但 CLAUDE.md 第一句
写明 Aionis 是 **"a disciplined experiment harness, NOT a cognitive system or a trading
bot"**（反泄漏研究工具，非认知系统/非交易机器人）。用分析师工作流去组织一个研究效度工具，
是**用错了骨架**——这才是业主三次都感到"不对"的真正原因。

**正确的范式**应当从 Aionis 的**真实科学身份**涌现出来：一个 **可证伪的、反泄漏的、点在时间
的**量化研究工具。它的组织原则不是"分析师怎么想"，而是"**一个数字凭什么可信 / 怎么被证伪**"
——即 **效度论证（validity argument）+ 泄漏守卫（leakage guard）+ 证据可溯（provenance）**。

---

## 1. 站在巨人肩膀上 —— 调研到的可复用范式（皆已核源）

按 `aionis-reuse-first-mandate` + 业主"深度探索所有 github 开源仓库"要求，下列是我从开源 /
学术 / 前沿实践中提取的**与 Aionis 身份契合**的结构范式（非"分析师工作流"那一类）：

### 巨人 A · 证据中心设计 ECD（Evidence-Centered Design, Messick/SRI）
- 源：`padi.sri.com/downloads/TR9_ECD.pdf`（SRI/PADI 技术报告）、ERIC ED483399、APA PsycNet。
- 核心：一切围绕一条**效度论证链** `Claim（主张）→ Evidence（证据）→ Warrant（担保，即证据为何支持主张）`。
  每个数据点都必须可追溯回它所支持的那条 claim。
- **与 Aionis 的契合**：Aionis 的 `config_committed BEFORE result`、`ledger.jsonl`、预注册 null-claim、
  rank-IC 差分——**本来就是一条 ECD 论证链**，只是终端 UI 从没让它显形。终端的"七主题/四枢纽"
  把这条链拆散成了一堆平铺卡片。

### 巨人 B · 模型卡 + 数据集说明书（Model Cards / Datasheets, Gebru/Mitchell）
- 源：`cacm.acm.org/research/datasheets-for-datasets`（Gebru et al., CACM，被引 5000+）、
  Google Model Cards（Mitchell et al.）、HuggingFace Model Cards、Data Cards（FAccT 2022）。
- 核心：不是按"用户任务"分节，而是按**责任披露**分节：`Intended Use / Training Data /
  Evaluation / Metrics / Limitations / Ethical`。固定、结构化、强制。
- **与 Aionis 的契合**：Aionis 的每个面板（picks / IC / calibration / power floor）其实都是
  同一个模型的不同**披露面**——用途、训练数据(PIT)、评估(OOS IC)、度量(ECE/Brier)、局限(power floor null)。
  按披露分节，天然把"定调/定标/佐证/问责"**消解**进"这条 claim 的证据链"，不再需要人手拍分类。

### 巨人 C · 可执行研究纲要 + 预注册（Executable Research Compendium / Registered Report）
- 源：`ropensci/rrrpkg`（GitHub）、The Turing Way `book.the-turing-way.org/reproducible-research/compendia/`、
  Nüst et al. 2017（D-Lib）、OSF Registries / Registered Reports（COS）、Leipzig 2021（metadata in RC）。
- 核心：一个研究项目 = **时间戳冻结的纲要**（code + data + 环境 + 预注册假设），结构按
  **研究生命周期**而非"分析步骤"组织：`Preregister → Freeze → Run(observe-only) → Archive → Reproduce`。
- **与 Aionis 的契合**：Aionis 的 `config_committed` ledger + H6 确定性 + uv.lock 版本钉 + 反 rerun-to-significance
  **就是这个纲要的活体实现**。终端可以按**研究生命周期的阶段**来排布，而不是按"分析师今天看什么"。

### 巨人 D · 数据/模型可观测性 + 溯源（Data & Model Observability + Provenance）
- 源：QVeris《AI Stock Research Agent》（`qveris.ai/guides/ai-stock-research-agent/`）的 5 层
  evidence-first 架构；Cohere《A Business Guide to Data Provenance》；现代 data-observability 栈
  （Monte Carlo、lakehouse 5 层）。QVeris 的金句：**"every material number has a period, unit,
  source, and observation timestamp"**——正是 Aionis 的 PIT 哲学。
- 核心：**single pane of glass 但以溯源为脊柱**——任何面板上的数字都能点开看到 `source / as-of /
  vintage / retrieval time / validation status`。
- **与 Aionis 的契合**：业主近一轮反复说"无法得知数据有效性/时点"（`snapshot_ts`、`as_of`、
  "七主题无时点"）——这恰恰是 **provenance 脊柱缺失**，而非缺一个 hub。

### 巨人 E（反例，已排除） · OpenBB / FinceptTerminal / Koyfin 的 menu/panel 平铺
- 源：OpenBB docs（menu→submenu→command）、FinceptTerminal（50+ screens）、Koyfin、quantumterminal。
- 结论：这些是**数据平台/交易终端**的 IA（按资产类/数据源平铺 menu），**与 Aionis 研究效度身份
  相悖**——上一轮 `2026-08-11 续③` 已调研并正确地"不抄 OpenBB 平铺"。本次确认排除。OpenBB 的
  `Platform` 分层（router→model→provider）可作为**后端接线**参考，但**不是 IA 骨架**。

---

## 2. 从巨人合成的候选范式（三个真正不同的骨架，请业主选一个）

> 三者**都不是**"分析师工作流 1-2-3-4"，都**消灭了编号**，都**让结构从 Aionis 的研究效度身份涌现**。
> 区别在于"脊柱"选哪条。我给推荐与理由，但**定帧权在业主**。

### 范式 α · ECD 效度论证脊柱（推荐）
**一句话**：终端 = 一条**可证伪主张的论证链**，每个面板是链上的一个证据节点。
- 脊柱：`Claim（我们要证明/证伪什么）→ Data(PIT) → Model → Estimand(rank-IC) → Validation(IC/CI/power) → Verdict(null/显著) → Discipline(为何可信)`。
- 没有"定调/定标/佐证/问责"——这些**全部消解**进论证链：
  - 旧"定调·市场制度"(regime/macro/COT/TACO) → 论证链的 **前提/语境段**（claim 的适用域）。
  - 旧"定标·选股"(picks/sectors/conviction) → 论证链的 **估计量产出段**（claim 的可观测物）。
  - 旧"佐证·另类"(smartmoney/insiders/reddit) → 论证链的 **独立佐证段**（第二个证据源）。
  - 旧"问责·诚实"(calibration/powerfloor/modelhealth) → 论证链的 **效度/局限段**（warrant 的强度）。
- 为什么推荐：这是**唯一把 Aionis 的核心贡献（反泄漏 + 预注册 null + power floor）升为一等骨架**
  的范式；与 `manuscript/` 的 power-floor 叙事、`docs/RESULTS.md` 的 falsifiable 框架**完全同构**，
  终端即论文的活体版。
- 巨人来源：A（ECD）为主，嫁接 B（披露节）、C（生命周期）。

### 范式 β · 研究生命周期脊柱
**一句话**：终端 = 一个研究纲要的**生命周期阶段**，每个面板属于一个阶段。
- 脊柱（无编号，按时间不可逆）：`Pre-register（预注册）→ Freeze（冻结）→ Observe（样本外观测，不可回看）→ Verify（独立验证）→ Archive（沉积）→ Reproduce（复现）`。
- 面板归属：picks/IC 属 Observe；calibration/powerfloor/discipline 属 Verify；evidence/ledger 属 Archive。
- 优点：最强地体现 `config_committed BEFORE result` 这一不可逆时序，"为何不能 rerun-to-significance"不言自明。
- 缺点：对"展示层/前瞻数据"（display panel、reddit、live prices）归位有点别扭——它们不是研究产物，是**展示**。
- 巨人来源：C（compendium）为主。

### 范式 γ · 溯源/可观测性脊柱
**一句话**：终端 = 一块 **single pane of glass**，但脊柱是每个数字的**溯源链**。
- 脊柱：`Source → as-of/vintage → PIT-gate → Number → Claim → Confidence`。每个面板上的数字都能
  点开看到来源、时点、是否 PIT、校准状态。
- 优点：直接解决业主近一轮"无法得知有效性/时点"的痛点；QVeris evidence-first 架构可大量复用。
- 缺点：更偏"数据可观测性平台"，对 Aionis 的**证伪科学叙事**支撑不如 α 强；可能滑回"数据展示平台"。
- 巨人来源：D（provenance）为主。

**我的推荐：范式 α（ECD 效度论证脊柱）**，理由：(1) 唯一同构于 Aionis 真实身份与论文叙事；
(2) 天然消灭"定调/定标/佐证/问责"四标签（它们变成论证链的段，而非并列分类）；(3) 把 power floor null
与反泄漏纪律升为终端的主结构而非角落，这是 Aionis 独有的差异化（OpenBB/FinceptTerminal 全都没有）。

---

## 3. 范式 α 的具象映射（如果业主选 α，骨架如下；**此节是示意，非定稿**）

当前 19 个路由 + 23 个面板，**不增不减内容**，只重组归属与导航。**消灭所有编号**。

```
论证链（脊柱，无编号，单向）：
  前提/语境  →  证据/观测  →  估计量  →  效度  →  裁决  →  守卫
  (Context)   (Evidence)   (Estimand) (Validity)(Verdict)(Guard)
```

| 脊柱段 | 当前面板（搬入，不改数据） | 段的一句话职责 |
|---|---|---|
| **语境 Context** | market / macro / regime(COT) / TACO | claim 适用的市场域（"在这个 regime 下…"） |
| **证据 Evidence** | picks / sectors / conviction / smart-money / insiders / reddit | 可观测的截面证据（含独立佐证源） |
| **估计量 Estimand** | （由 picks+IC 共同定义的 rank-IC 差分） | 我们要测量什么 |
| **效度 Validity** | calibration / power-floor / model-health / ic-monthly | 这个测量准不准、够不够 power |
| **裁决 Verdict** | evidence-wall / themes(method) / bps-sweep | 结论是什么（null + 诚实披露） |
| **守卫 Guard** | discipline(PIT/embargo/H6) + 每个面板的 provenance 角标 | 为什么这个结论可信/不可被 rerun-to-significance 污染 |

**导航**：单列 6 段（无编号、无"定调定标"中文标签，用 `Context / Evidence / Validity / Verdict / Guard`
这类科学词；中文为"语境 / 证据 / 效度 / 裁决 / 守卫"）。Overview 页 = **整条论证链的可视化**（一条
从左到右的链，每个节点可点入）。

**旧"七主题"面板**：不是删，是**拆解**——七主题本质是"特征工程特征族"，按论证链段归位：
price/macro→Context；fundamentals/momentum/risk→Evidence 的特征来源；net_cost→Verdict 的成本段；
news→Evidence 的佐证。`themes-funnel.tsx` 的 L0-L4 漏斗**正好可以重映射**成论证链段（L0=Context,
L1=Evidence 的特征层, L2=Estimand, L3=Validity, L4=Verdict 成本）——**复用而非重写**。

**每个面板强制带 provenance 角标**（as_of / source / PIT 状态）——这是巨人 D 的脊柱在 α 里的落地。

---

## 4. 待业主定帧的决策点（回答后我才动代码）

> 按 `aionis-owner-process-correction`，重大重组前必须业主裁。我只问**最小必要**问题。

1. **范式**：选 α（ECD 效度论证，我推荐）/ β（研究生命周期）/ γ（溯源可观测性）/ 其他？
2. **中文命名**：脊柱段用科学词（语境/证据/效度/裁决/守卫）OK，还是业主另有偏好？**确认彻底
   去掉"定调/定标/佐证/问责/定向/边界"这套**。
3. **是否允许我重映射而非重写** `themes-funnel` 的 5 层（L0-L4 → 论证链段），以复用现有代码？

**我不会擅自开始**：这是 IA 级重组，涉及 nav / dict.ts（846 行）/ overview / 19 个路由的标签
与归属。定帧后我会：先出**逐文件迁移清单**（哪些 key 改名/哪些面板归位/哪些路由保留软重定向）→
分批 commit（每批 tsc+build 绿）→ 每批 review。**全程 0 ledger / frozen panel / config / OOS 接触**，
纯展示层 `web/src/`。

---

## 5. 边界与诚实标注

- 本文档：纯 `reports/design/` + state，**0 ledger / frozen surface / prereg / ADR / config / data / OOS 改动**。
- 未跑任何 research / forward / strategy 脚本；未触 E3。
- 调研来源（web）：ECD（SRI PADI TR9、ERIC、APA）、Model Cards/Datasheets（CACM Gebru、HF、FAccT DataCards）、
  Research Compendium（rOpenSci rrrpkg、Turing Way、Nüst 2017、Leipzig 2021、OSF Registered Reports）、
  Provenance/Observability（QVeris、Cohere、Monte Carlo lakehouse）。**反例 OpenBB/Fincept/Koyfin 已排除**。
- 巨人调研在**主会话**完成（遵循 `aionis-model-tier-dispatch-policy`：web-using 子代理会触发 [1210] 失败）。
- 业主曾纠正（`aionis-owner-process-correction`）：私人兴趣项目勿过度仪式化。故本文**不引入**
  arXiv/署名/venue 等非决策门；唯一决策门是 §4 的范式定帧。
