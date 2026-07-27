# 可计算现实理论（Theory of Computable Reality, TCR）

> Aionis 理论基础设计文档 · 草案 v0.1 · 2026-07-26
>
> 本文回应把 ERL 升级为 WRL、把研究目标升格为"世界状态/数字孪生/Reality
> State Engine"的方向。结论：**用户的统一洞察是对的，且应被采纳为 Aionis 的
> 理论上层**；但它目前是 *ontology*，要成为 *theory* 还需五层形式化；而且实现
> 层必须与 `docs/frontier_positioning.md` 的硬结论（learned world model 在 MVP
> 规模不可行、贡献是 leakage-aware causal event-impact）相容——TCR 给出"为什么
> 事件影响能被统一归因"的状态语义，**不授权现在就建生成式世界模型**。

---

## 0. 一句话

Aionis 的研究对象是**文明-经济系统的潜在世界状态 $S_t$**；新闻、财报、资金流、
CEO 行为、政策都是 $S_t$ 的**带噪、带选择偏差**的观测；**唯一可证伪锚点是可测的
经济后果**（收益）。ERL → WRL 是**严格泛化**（`WRL.Event ≡ ERL`）；每个阶段都可
证伪、反泄漏、与样本量 $n$ 成比例。

> 股票不是目标，是**体检报告**——用它验证"状态"对不对，而不是把"状态对不对"当
> 成不可回测的目标。

---

## 1. 为什么需要 TCR

**ERL-only 的局限**：单模态（事件文本）、event-only、小样本下 underpowered——而且头条**不是一个点，是一条分布**。同一 2018-2025 / GLM / h=1 设置，跨不同 config（PCA 范围、ERL 集合、embedding 实现）ERL/xgb `da_lift` 观测范围约 **−0.6 到 +8.7 pp**，dm_p 0.08–0.98。`+0.0124`（panel-scoped + 缓存 embedding）和 `+5.5 pp`（早期 full-cache config）都是这条分布里的点，**单独看都不可信**。每加一个数据源（财报、资金流、CEO 行为）就堆一
个模块，是结构性的——因为缺少一个把它们都映射进去的统一状态空间。

**用户的统一洞察（采纳）**：新闻/财报/资金流/CEO/政策都是**同一隐状态的不观测面**。
这在机器学习里有现成名字：**state-space model / POMDP**——观测是 latent state 的
带噪投影。这一步让"加数据源 = 加模块"的冲动停下来。

**但必须正视的张力**：`frontier_positioning.md` §2C 已论证 learned world model 在
MVP 规模不可行——ChaosAI 记录了跨截面 OOS 泄漏 $+7$ Sharpe；Tan et al. NeurIPS 2024
（`arxiv.org/abs/2406.16964`）显示 LLM 无助时序预测；JEPA/Dreamer 移植需 100M+ token。
**因此 TCR 的定位是：理论框架 + 状态语义，不是"现在就建生成式世界模型"的许可。**
每个实现阶段保持判别式/因果/反泄漏/与 $n$ 成比例——这正是 frontier doc 的立场。

---

## 2. 三条公设（Axioms）

- **A1 Latent State**：存在有限的、随时间演化的世界状态 $S_t$；可测经济后果
  $y_{t+h}$ 是 $S_t$ 的（预注册）函数。
- **A2 Observation with Selection**：每个数据源 $k$ 产生观测
  $o_t^{(k)} \sim g_k(S_t,\, b_k)$，其中 $b_k$ 是该源**固有的选择偏差**（新闻被编辑
  挑选、财报受合规约束、CEO 发言受 IR 修饰、资金流披露滞后）。不建模 $b_k$ 则状态
  推断有偏。
- **A3 Causal-Temporality（$I_t$）**：信息有严格因果时间。定义 $I_t \equiv$ 时刻 $t$
  及之前**可得**的所有观测。任何状态推断与预测**只能用 $I_t$**——这是反泄漏的形式
  化锚点。

公设之间的约束：A3 限制 A4（推断）只能用 $I_t$；A2 的 $b_k$ 决定 A4 的可识别性上
界；A1 把"状态"钉成可计算对象而非文学概念。

---

## 3. 五层形式化（从 ontology 到 theory）

ontology（Entity/State/Event/Relationship）只是词汇表。一个可计算理论必须给出下面
五层；缺任何一层，"数字孪生"就只是图，不是科学。

### 3.1 状态结构 $S_t$ —— 动态属性图

$$S_t \;\equiv\; G_t = (V,\; E,\; \text{attr},\; w)$$

- $V$ = **Entity**（苹果、美联储、黄仁勋、台积电……），每个 $v$ 带类型。
- $\text{attr}(v)$ = **State**（现金、利率、产能、DSP……），时变量。
- $E,\,w$ = **Relationship**（供应链、资金、博弈、持股……），带权有向时变。
- **Event** $= \Delta G_t$：状态在时刻 $t$ 的离散变化（一次发布、一次决策、一次冲击）。

层级：`micro`(公司) → `meso`(行业/供应链) → `macro`(国家/政策) → `global`。
**为什么是图不是张量**：实体异质、关系稀疏、结构可变；张量表示强行稠密化会注入伪信
息并放大 $n$ 不足的问题。

> **四原语到此才有了数学定义**——不再是 PPT 上的四个词。

### 3.2 转移函数 $f$

$$S_{t+1} = f(S_t,\; A_t,\; \varepsilon_t)$$

- $A_t$ = 决策主体（公司管理层、央行、政府）的行动。
- $\varepsilon_t$ = 外生冲击（地震、疫情、战争——黑天鹅）。

三类转移必须**显式区分**，否则会把"可预测"和"不可预测"混在一起：
1. **观测触发的更新**：财报发布 $\to$ 更新 `attr(corp)`（确定性规则为主）。
2. **内生演化**：状态按已知动力学推进（利率路径、订单交付）。
3. **外生冲击**：$\varepsilon_t$，**不可预测**，只能做脆弱性/暴露（见 §8）。

**博弈** = 多决策主体的耦合 $f$（OpenAI/Google/Anthropic/Meta 的反应函数互为输入）。

### 3.3 观测模型 $g_k$（含选择偏差）

每个数据源是一个 channel：$o_t^{(k)} \sim g_k(S_t, b_k)$。

| 源 $k$ | 观测 | 选择偏差 $b_k$ |
|---|---|---|
| 新闻 | 文本 | 编辑凸显性（事后"重要性"挑选） |
| 财报 | 数值/文本 | 合规框架、季度滞后、回溯修订 |
| CEO 发言 | 文本/音频 | IR 修饰、表演性 |
| 资金流 | 持仓/流向 | 披露滞后（13F 滞后 45 天）、聚合 |
| 政策 | 文本 | 谈判过程不可见、只看结果 |

**关键纪律**：$b_k$ 不建模 $\Rightarrow$ 状态估计渐近有偏。$b_k$ 的建模本身就是
research contribution（与 `frontier_positioning.md` §2B 的"parametric 记忆"并列的第
二个偏差源）。

### 3.4 推断（Filtering，严格 PIT）

$$\hat S_t = \mathbb{E}\!\left[\, S_t \;\big|\; (o_{\le t}) \cap I_t \,\right]$$

- **只能用 $I_t$**：这是反泄漏的形式化（A3）。
- 近似方法：变分推断 / 粒子滤波；**LLM-as-amortized-inference** 可做抽取器，但它的权
  重记忆了事后结果（Lopez-Lira et al. 2025，`arxiv.org/abs/2504.14765` 的
  "functional lookahead bias"）——所以**每个 channel 必须配 PiT audit**（见 §4）。

### 3.5 可检验后果（Falsifiability anchor）

$$y_{t+h} = h(\hat S_t) + \eta, \quad h\text{ 预注册}$$

**可证伪 claim**：用 $\hat S_t$ 预测 $y_{t+h}$ 是否优于预注册的 baseline。
**这一步把"世界状态"锚回可回测量**——状态不可回测，但 $y$ 可。没有这一步，整套
理论不可证伪。

---

## 4. 反泄漏纪律（贯穿五层）

泄漏是本项目第一研究风险（ERL structural-only、BLS 403、本轮刚修的 pipeline 不可
复现 bug 都是它的表现）。TCR 必须把反泄漏建成结构性约束，而非事后补丁：

1. **$I_t$ 边界硬约束**：进入 $\hat S_t$ 的任何字段必须是 $I_t$ 的可计算函数。代码层
   面每个 `.rolling/.shift/.merge_asof` 都过 alignment 断言（已有 `test_alignment.py`）。
2. **structural-only 抽取**：推广 ERL 的做法——WRL 抽取只取结构化/语义字段，**绝不
   取 `market_impact` / 事后叙述**；市场影响是 $y$，是预测目标不是输入。
3. **每个 channel 配 PiT audit**：pre/post-LLM-cutoff 的提升差 + bootstrap CI（已实
   现 `pit_audit.py`，Phase B 起覆盖每个新 channel）。
4. **选择偏差不是泄漏借口**：用"事后看起来重要的新闻"做选择 = 泄漏了未来重要性。事件
   集合必须由 $I_t$ 内的**调度/披露规则**决定（FOMC 日历、FRED release 日期），不是
   事后显著性。
5. **可复现性是反泄漏的一部分**：观测渠道的任何随机性（如 GLM embedding 抖动）必须
   缓存固化（本轮已修：`data/embedding_cache/`）。

---

## 5. WRL = ERL 的严格超集（桥）

- `WRL.Event` $\equiv$ ERL。当前整条 pipeline（extract → design_matrix → compare）
  是 TCR 的 **Event-only 特例**。
- Entity / State / Relationship 是**新增维度**，不是替换。
- 这保证**渐进升级**：Phase A 的代码、对齐规则、PiT audit、CV/DM 全部复用；新阶段只
  增不删。

> 这条桥是"不推倒重来"的形式化保证。任何 Phase $>A$ 的设计若要求重写 Phase A，即视
> 为违反 TCR。

---

## 6. 用户三件事在 TCR 里的形式化

| 用户概念 | TCR 映射 | 形式 |
|---|---|---|
| Corporate Vital Signs | Entity 的 `attr`（micro 层） | Corporate State Vector：现金流、利润率、债务率、研发、库存、订单、客户集中度、供应链健康、诉讼、审计意见……**全部 PIT 可观测**，非财报文本 |
| Decision Style Profile | 决策主体（CEO）的 `attr` | DSP = 从**公开可验证行为**（演讲、股东信、电话会、已发生决策）抽取的**可观测行为倾向**：风险偏好、创新倾向、资本配置风格、沟通稳定性、执行一致性。**输出决策分布** $p(\text{action}\mid \text{DSP}, S_t)$，**不是人格诊断** |
| Capital Flow Network | Entity 间的 $E,w$（时变） | 带权有向边：BlackRock→TSMC（买入）、Sequoia→startup（投资）。本身是图，可做网络传导 |

**CEO 人格的诚实边界**：不做 MBTI/大五贴标签（不可验证、伪科学风险）；只做"在公开行
为上可重复测量的决策风格"，且**预测的是决策分布**，不断言某人必做某事。

---

## 7. 分阶段、每阶段可证伪的路线图

每个 Phase = 一个预注册 claim + 一个反泄漏 audit + 与 $n$ 成比例的推断。**通过了才
进下一阶段。**

| Phase | 状态表示 | 可证伪 claim（预注册） | 状态 |
|---|---|---|---|
| **A** ERL-only | Event（结构化） | ERL 提升收益方向预测 > price-only；neutral/shuffled 不提升 | ⚠️ **underpowered + under-specified**：`da_lift` ∈ [−0.6, +8.7]pp 跨 config；gate 方向正确（ERL>neutral>shuffled）但 lift 对 PCA 基 / ERL 集 / embedding 实现敏感（panel vs full-cache 单独就摆 1.65 pp）。**n=44 下不可作 Phase-B 地基**——需 powered n + 冻结预注册 config |
| **B** + Entity/State | + Corporate Vital Signs（**filed-date PIT**） | filed-date 时点 > period-end+lag 时点，**横截面选股 benchmark**（A-自建 ticker-keyed；非事件窗；非 GKX——critic C1 证 GKX 不可行） | ⏳ 预注册 v0.2（critic-integrated），见 `docs/phase-b-preregistration.md` + §13 修正案 |
| **C** + Relationship | + 供应链/资金流/博弈图 | 关系结构提供**增量**提升（超过 +State） | 待 B |
| **D** Simulation | 脆弱性/暴露/情景 | **不作证伪锚**（解释层）；仍用收益证伪主链 | 待 C |
| **E** Evolution | 自演化状态转移 | stretch；defer（per frontier doc） | 远期 |

**Phase D 的定位**：simulation 是**机制解释层**，不是第二个证伪锚——因为情景模拟难
证伪（"情景没发生"是永久借口）。证伪永远走 $y_{t+h}$。这与用户"模拟是核心"的提法
**互补而非矛盾**：模拟回答"为什么/会怎样"，预测回答"对不对"。

---

## 8. 不做什么 / 诚实边界（Non-goals）

1. **不预测真正的黑天鹅**（罕见、不可外推、高影响）。只做**脆弱性 / 暴露 / 情景模拟**
   ——哪些主体对哪类冲击敏感、传导链路、条件后果。
2. **不做 CEO 人格诊断**。只做 DSP from observable public behavior，输出决策分布。
3. **不声称"世界状态正确"**。只声称"$\hat S_t \to y_{t+h}$ 的预测优于预注册 baseline"。
4. **不一次性重构**。incremental、falsifiable、WRL = ERL 超集。
5. **不在 MVP 规模建 learned generative world model**（per `frontier_positioning.md`
   §2C/§3：100M+ token、+7 Sharpe 泄漏、LLM 无助 TS）。TCR 的 simulation 层是**可解释
   的情景/网络传导**，不是需要巨量 token 的生成式模型。

---

## 9. 开放问题（必须承认，不能跳过）

- **可识别性**：$n$ 小、$S_t$ 高维 $\Rightarrow$ 状态可能恢复不出来。每加一个状态维
  度都要回答"观测模型 $g_k$ 是否足够约束它"。Phase B/C 的 claim 必须在**同样的 $n$**
  上比较，否则 richer state 只是过拟合的自由度。
- **$b_k$ 的估计**：没有无偏 ground truth 来校准选择偏差。候选：用 scheduled release
  集（无选择偏差）做对照；用多源三角验证。
- **LLM-as-inference 的记忆 audit 如何 scale**：当前 `pit_audit.py` 只覆盖 Event；多
  channel 后每个都要 pre/post-cutoff audit，成本与 token 上升。
- **simulation 的可证伪性**：情景输出的"对错"如何度量——候选：用情景隐含的
  $y_{t+h}$ 分布去做 probability integral transform / coverage 检验。

---

## 10. 与现有代码的映射

| TCR 层 | 当前 `src/aionis/` | Phase B 需新增 |
|---|---|---|
| 状态结构 | （仅 Event） | `schema/wrl.py`（ERL 的超集）；Entity/State schema |
| 观测模型 | `ingest/event_text.py`（FOMC/BLS）、`features/macro_surprise.py`（ALFRED） | Corporate Vital Signs ingest（PIT 财务/运营）；macro state vector |
| 推断（PIT） | `extraction/`、`features/alignment.py`（$I_t$ 边界断言） | 多 channel PiT audit 扩展 |
| 可检验后果 | `eval/compare.py`（收益 DA-lift + DM） | 同一 benchmark 上 +State vs Event-only 的预注册对比 |
| 反泄漏 | `pit_audit.py`、`test_alignment.py` | 每 channel 一份 audit |

**Phase B 的最小实现量**：WRL schema（继承 ERL）+ 一个 Corporate Vital Signs ingest
（PIT）+ 把 State 拼进 design_matrix 的 `extra_features`（现有机制可直接复用）+ 在
**同一收益 benchmark** 上跑 +State vs Event-only。**不需要新的训练基础设施。**

---

## 11. 与 `frontier_positioning.md` 的对齐（不一致即本文作废）

- frontier doc：推迟 learned world model；贡献 = leakage-aware causal event-impact。
- TCR：**世界状态是理论框架（解释为什么事件影响可被统一归因）；实现层每阶段保持判别
  式 / 因果 / 反泄漏 / 与 $n$ 成比例。**
- 二者**不矛盾**：TCR 提供"状态语义"，frontier doc 提供"在 $n\approx 50\text{-}600$ 怎
  么诚实估计"。SDID/Synthetic Control（frontier §2C）天然是 TCR Phase B/C 的因果估计
  器——每个 Entity 的冲击 = 一次干预，donor pool = 未受影响实体。

---

## 12. 下一步（本文通过评审后）

1. 评审本文（critic pass：形式化是否自洽、反泄漏是否可操作、每 Phase claim 是否真的
   可证伪）。
2. Phase B 设计文档：WRL schema + Corporate Vital Signs 字段清单（PIT 来源逐项标注）+
   预注册 claim + audit 计划。
3. Phase B 最小实现 + 在现有收益 benchmark 上跑 +State vs Event-only。
4. **Phase B 通过（可证伪 claim 成立或干净否定）才进 Phase C。**

> 诚实标准不变：CI 跨 0 时不得宣称正向效应；null + 紧 CI 仍是合法结论；每个 Phase 的
> 选择都进 run ledger。

---

## 13. Phase B 修正案（2026-07-27，critic-integrated）

> 本节 **supersede** §7 的 Phase B 行（已就地订正）+ §10、§12.3 中"**同一事件 benchmark /
> +State vs Event-only**"的措辞。完整理由 + 决策见 `docs/phase-b-preregistration.md`（v0.2）。

- **Phase A → pilot**（事件窗 benchmark，underpowered，保留为子结果）。
- **Phase B re-anchor 到横截面选股 benchmark**，路径 = **A-自建 ticker-keyed**（EDGAR filed-date +
  Tiingo/Alpaca，复用 `features/selection_panel.py` + `ingest/fundamentals.py`）。曾选 A-GKX，
  **critic C1 证不可行**（GKX 是 permno 键、无免费 PIT permno↔CIK 桥；`cik_map` 用今天快照 =
  look-ahead 泄漏）→ 改 A-自建。**决策进 `runs/ledger.jsonl`。**
- **控制臂**：Event-only → **period-end+lag baseline**；State claim = **filed-date vs period-end
  PIT 时点差（双尾）**。Event/ERL → Phase C。
- 理由：① 结构性解决 n=44 power（OOS ~110 月 vs 事件 ~44–131）；② State（基本面）在横截面才自然；
  ③ WRL=ERL 超集桥仍成立（复用 alignment/fundamentals/selection_panel，不重写 Phase A）。
- **不违反 §11**：实现仍判别式 / 反泄漏 / 与 n 成比例，无 learned world model。
