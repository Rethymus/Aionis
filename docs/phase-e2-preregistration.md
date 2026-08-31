# Phase E2 预注册 — LLM 宏观因果链假设生成器（cutoff 控制，缓解泄漏）

> 状态：**v0.1 DRAFT · 2026-07-29 · 规划文档 · run DEFERRED**（E1 null 已吸收；设计落定 +
> E1 被吸收后建 E2）。本稿**不含、不跑任何 Phase E2 OOS 结果**——既不抽取因果边、
> 也不跑 rank-IC。
>
> **这是泄漏陷阱阶段**：用户的宏观叙事愿景（疫情→医药、AI→算力→英伟达→电力、白酒下跌）
> 本质是「事件→受影响板块/资产」的**事后**因果推理——这正是 LLM 擅长但**必然带事后记忆泄漏**
> 的能力。E2 的全部设计重心 = **用 LLM 做因果边提取，同时把泄漏压到可审计、可缓解、且由 E3
> 前向兜底**。Phase E 程序（[`phase-e-preregistration.md`](phase-e-preregistration.md) §3）已钉死 E2 = 缓解（非消除）。

---

## 0. 与 TCR / Phase E 程序的关系 + 本阶段的泄漏红线

- **TCR**（[`theory-of-computable-reality.md`](theory-of-computable-reality.md)）：E2 把 $G_t$ 的宏观
  观测（政策/技术位移/外生冲击）沿 **LLM 提取的因果边**传播到板块含义，作为 $\hat S_t$ 的可解释推断。
  仍走 §3.5 单点可证伪锚 $y_{t+h}=h(\hat S_t)+\eta$（横截面月 rank-IC）。**LLM 在此是 amortized
  inference / 假设生成器，非生成式世界模型**（TCR §8.5/§11 + [`frontier_positioning.md`](frontier_positioning.md) §2C：
  learned world model 在 MVP 规模不可行、ChaosAI +7 Sharpe 跨截面泄漏）。
- **Phase E 程序定位**：E1 结构化传播（零泄漏，**已 null**，见 §1 脚注）、E2 LLM 宏观叙事（cutoff
  控制，缓解泄漏）、E3 前向实时（零泄漏，投产真值）。E2 的任何正向**必须 E3 前向战绩复现才可信**
  ——这是程序级硬约束（[`phase-e-preregistration.md`](phase-e-preregistration.md) §6）。
- **不可让渡的红线**（[[aionis-erl-leakage-design]] 的直接推广）：
  - **LLM 只输出因果边/schema，绝不输出市场预测**。`market_impact` 是预测目标 $y$，不是提取产物。
    这是 ERL structural-only 抗泄漏纪律（[[aionis-erl-leakage-design]]）在「事件→板块」层的同构复刻。
  - **cutoff 红线**：OOS 窗**严格后于**冻结 LLM 提供方的训练 cutoff（§2）。cutoff 前的事件**不进**
    confirmatory rank-IC。
  - **泄漏只能缓解，不可消除**——这是本阶段第一条诚实声明（§2 末 + §10 #1）。

---

## 1. 单一可证伪 claim（预注册，**双尾**，第 5 条 confirmatory；null = 强 favorite）

> 在**同一 S&P 500 PIT universe**（Phase B 冻结的 2016+ 可解析窗）+ **同一 frozen LightGBM** +
> **同一 PurgedGroupKFold(5, embargo=21, group=month)** 上，把一个 **LLM 生成的宏观因果链特征**——
> 对每个宏观事件（CPI/NFP 发布，ALFRED 调度日确定、非事后显著性），LLM 输出「事件→受影响 SIC 板块 +
> 方向 + 机制关键词」，作为**板块归属广播**特征（§3）拼进横截面——是否在 **LLM 训练 cutoff 之后**
> 的 OOS 窗带来**横截面月 rank-IC 的显著增量**（**双尾**）超过 **fundamentals-only 基线**（`arm_base`）。

- **Differential** = IC(`arm_causal`) − IC(`arm_base`)。两臂同股/同价/同模型/同折/同基本面时点
  （`align_on="end_lag"`）→ 增量**只**来自 LLM 因果链广播列。
- **null = 强 favorite**（比 E1 更强的 favorite，见 §2 功率论证 + §10 #2）：① 月频已定价 / 板块广播太粗；
  ② **cutoff 门直接砍掉 125 月 OOS 面板的绝大部分**（仅 cutoff 后月数存活，§2/§7）→ 检验力塌缩；
  ③ Lopez-Lira 2025 的非识别结论（§2）使「即便 cutoff 后微正也难以排除残留记忆」。合法且最可能。
- **双尾解释**：正 = LLM 因果链在 cutoff 后仍有未吸收的横截面定价信号（罕见、contrarian）；null = 已
  定价/过粗/检验力不足（**最可能**）；负 = 板块广播列加噪声压低 OOS IC（合法）。
- **可发表性 = realized σ(IC) 的函数**（§7），**CI 跨 0 不得宣称正向**。**E2 正向 ≠ 可信**——必须 E3 前向复现。

> **E1 已 null（吸收）**：E1 confirmatory（config_sig `ef321e9e…`，2026-07-29）differential
> mean_diff = **−0.0028**，CI [−0.0115, +0.0059]，dm_p = 0.53，ci_half = 0.0087（publishable）。
> → 纯结构化网络传播在月频零增量。**这不否定 E2**（机制不同：E1 传 firm 级冲击，E2 传 LLM 宏观
> 板块链），但巩固了 null-favorite 先验 + 证明 §4 的 E1 baseline 是干净的「无 LLM」对照臂。

---

## 2. 泄漏控制机制（**本阶段承重部分**）

> 这是 E2 的核心。泄漏控制是**四层叠加 + 诚实承认残留**，不是单点银弹。

### 2.1 cutoff 门（OOS 窗严格后于 LLM 训练 cutoff）
- **经验依据**：Lopez-Lira, Tang, Zhu 2025《The Memorization Problem》（`arxiv.org/abs/2504.14765`）实测——
  LLM 对 cutoff **前**的经济/金融结果有精确召回（recall-level accuracy），而**cutoff 后召回塌缩到零**。
  即「参数化事后记忆」是一个**cutoff 前现象**；cutoff 门把这个通道切掉。
- **承重设计**：① 冻结**单一** LLM 提供方（§5，不允路由自动切换——否则 cutoff = 所用提供方 cutoff 的
  **最小值**且不可审计）；② OOS 窗 = `[provider_cutoff + buffer, 数据末端]`（buffer≥1 月吸收 cutoff 附近的
  稀释数据）；③ cutoff 取**冻结提供方的 provider-declared cutoff**，并作为**待 LAP 审计的 claim**（§2.4），
  非假定真理。

### 2.2 structural-only 提取（同 ERL 抗泄漏，[[aionis-erl-leakage-design]]）
- LLM 输出**仅**结构化因果边：`event_type → [(sic_sector, direction, mechanism_keyword, horizon_bucket)]`
  （§3 schema）。**绝不**输出 `market_impact`/`expected_return`/`historical_similarity`/任何数值预测。
- 推理字段（mechanism 文本）置于结构化答案字段**之前**（[`frontier_positioning.md`](frontier_positioning.md) §2B：
  reasoning-before-answer），用 **strict Structured Outputs / 约束解码**（schema-by-construction）而非
  开放 JSON。
- **为什么必要但不充分**：Lopez-Lira 2025 证明**遮蔽/匿名化 provably fail**（LLM 从最小上下文重构实体+
  日期），且**记忆延伸到 embedding**——所以 schema-only 只是第一道，cutoff 门 + LAP 审计是必要的补充。

### 2.3 OOS 窗约束（与 E3 同源）
- cutoff 前 = **in-sample / 记忆区**：因果边可提取（作 exploratory / 假设池），但**不进 confirmatory
  rank-IC**。cutoff 后 = confirmatory OOS 区。
- **事件集合由 $I_t$ 内的调度规则决定**（TCR §4 #4）：CPI/NFP 由 ALFRED **发布日历**触发（已在
  `features/macro_surprise.py` PIT-safe），**非**事后显著性——否则「事后看起来重要的宏观事件」本身泄漏了
  未来重要性。

### 2.4 记忆审计（LAP test，适配现有 `eval/pit_audit.py`）
- **工具**：Lookahead Propensity（LAP）test（《Detecting Lookahead Bias in LLM Forecasts》，
  `arxiv.org/abs/2512.23847`）——一个**日期-only 召回查询**（不给实体/不给结果）估计 P(LLM 已内化该事件
  的实现结果)。LAP 在 cutoff 前显著为正、**cutoff 后塌缩到零**；LAP × 因果特征 在精度回归中的交互显著 =
  记忆污染信号。**成本极低、无需重训**——与 [`frontier_positioning.md`](frontier_positioning.md) §4 #3 的
  pre/post-cutoff audit 同源。
- **落表**：每个宏观事件附 `{lap_score, era: pre/post_cutoff}`；报告「因果特征增量在 high-LAP vs low-LAP
  事件的差」+ bootstrap CI。复用 [`eval/pit_audit.py`](../src/aionis/eval/pit_audit.py) 的 pre/post-cutoff
  bootstrap gap 框架（现为 directional-accuracy lift，E2 改为 rank-IC lift per event-month）。

### 2.5 诚实声明（mitigates, NOT eliminates）
- **非识别**（Lopez-Lira 2025 Proposition 1）：当模型见过实现值时，「真预测力」与「记忆」**观测等价**、
  不可识别。cutoff 门 + structural-only + LAP **缓解**这一通道，**不证明其消除**。
- **不可判定性**（《Look-Ahead-Freedom as Temporal Non-Interference》，`arxiv.org/abs/2607.04958`）：
  泄漏是 recursively enumerable，但**泄漏-自由不可判定**——「探测器的沉默」不证明无泄漏。
- **结论**：E2 的任何正向**最多是「cutoff-门控下的候选信号」**，可信度最终由 **E3 前向战绩**裁定
  （前向不复现 = 回测结果是泄漏伪影）。FinCAD（`arxiv.org/abs/2605.24564`，inference-time CAD，惩罚在
  OOS 衰减到零）是更前沿的缓解，但**超 MVP 范围**（重推理成本），记为未来升级路径。

---

## 3. 因果链 schema + 特征 + 数据（**结构化、可测、非叙事**）

### 3.1 schema（LLM 的唯一输出；strict Structured Outputs）
```
CausalChain := {
  event_id, event_date, event_type ∈ {cpi_release, nfp_release, ...},
  cutoff_era ∈ {pre_cutoff, post_cutoff},
  edges: [
    { sic_sector: <2-4 digit SIC>, direction ∈ {+1, -1, 0},
      mechanism_keyword ∈ {demand_pull, cost_push, rate_channel,
                            risk_off, supply_disruption, ai_capex, ...},
      horizon_bucket ∈ {immediate(≤5d), near(≤21d), far(>21d)},
      confidence ∈ [0,1] }   # confidence 仅用于 LOO 过滤，不入特征值
  ]
}
```
- **schema 依据**：CAMEF（《Causal-Augmented Event-Driven Forecasting》，`arxiv.org/abs/2502.04592`）的
  因果效应图 $\mathcal{E}\to\mathcal{X}\to\mathbf{Y}$；KAIROS（`github.com/mr-sharath/KAIROS`）的结构化
  JSON `{affected_sectors, second_order_effect}`；经济因果链搜索（Kobayashi-Murayama-Izumi 2023,
  `doi.org/10.1109/bigdata59044.2023.10386410`；Izumi-Sakaji 2020）的叙事因果链；Ready (2018) 的结构化
  冲击分解（正交 shock → 板块传导）。
- **关键纪律**：`direction`/`mechanism` 是**结构性 a-priori 字段**（同 ERL 的 actor/action/object），
  非结果衍生。`mechanism_keyword` 来自**封闭枚举**（不允许自由文本入特征），杜绝叙事嵌入泄漏。

### 3.2 特征（板块归属广播，per-(ticker,date)）
- 对每个事件 $e$ 在发布日 $t_e$：`causal_signal(ticker, t) = Σ_{e: t_e ≤ t < t_e+horizon_bucket}`
  `direction_e × 1[ticker ∈ sic_sector_e]`。
- 即「该股所属 SIC 板块在近 w 窗内被 LLM 标记为某宏观事件的利多/利空」的**加权和**。广播到该板块全部
  PIT 成员（复用 [`ingest/universe.py`](../src/aionis/ingest/universe.py) 的 PIT 成员快照，无 forward-fill）。
- **为什么不嵌入**：嵌入带参数记忆（Lopez-Lira 2025：记忆延伸到 embedding）。板块归属是**离散、可广播、
  可 placebo 打乱**的——直接对齐 §4 placebo。

### 3.3 数据（全部已过 7 门，[`data-intake-rubric.md`](data-intake-rubric.md)）
- **宏观事件触发**：ALFRED CPI/NFP 发布（已在 `features/macro_surprise.py`，vintage as-of join PIT-safe，
  G1✓G2✓G3✓ 不可回改）。**调度日触发 = 非 PIT 问题**（发布日历在 $I_t$ 内）。
- **SIC 板块归属**：EDGAR submissions 顶层 `sic`（Phase D 已用；已知局限：当前快照非逐日 vintage，
  见 phase-d §0.5——SIC 对绝大多数发行人稳定，轻度分类 lookahead，作为已知局限披露）。
- **基本面 + 价格 + universe**：Phase B 冻结产物（config_sig `17245a75…`），原样复用。
- **不用的数据**（诚实排除）：新闻/live-cache 非 PIT（[[aionis-reference-data-source]]）——**不进 E2 事件源**。
  政策/疫情/技术位移等更丰富事件类型 = **未来扩展**（需先建 PIT-safe 结构化事件表），E2 v0.1 仅 CPI/NFP。

---

## 4. 控制门（必须全过）

1. **`arm_base` 即主控制**：因果链增量 = 相对 fundamentals-only 的 IC 差。
2. **「无因果边」placebo（核心）**：保留事件时点 + 板块广播结构，但**随机重连 event→sector 边**（保度数、
   乱拓扑）→ differential 必须消失。证信号来自**真实因果对齐**，非任意板块扰动。（复用
   [`eval/phase_c_controls.py`](../src/aionis/eval/phase_c_controls.py) shuffle 模式。）
3. **E1 传播作「无 LLM」baseline**（跨阶段对照）：E1 的结构化网络传播（已 null）是「不用 LLM 的传播」；
   E2 问「LLM 宏观链是否比确定性网络传播多增量」。两臂机制不同、互不否定，但同框报告。
4. **cutoff-era 分层（记忆审计的门控）**：因果增量在 `post_cutoff` 月 vs `pre_cutoff` 月的差 + bootstrap CI
   （§2.4 LAP 框架）。**只有 post_cutoff 增量可信**；pre_cutoff 增量 = 记忆污染嫌疑。
5. **leave-one-out per event_type（exploratory，非 gate）**：依次去掉 CPI / NFP，看 differential 跌幅——
   仅归因报告。
6. **方向性 sanity**：CPI 超预期 → 利率敏感板块（如 REIT/公用）direction 应偏负（已知经济先验）→ 校准
   「LLM 因果方向非随机」。作 sanity 锚，不作孤立 claim。

---

## 5. 实验设计（复用 `eval/two_arm.py`；**冻结单一提供方**）

- **复用，不新写训练基础设施**：`two_arm.compute_shared_folds` + `run_arm_oos`（Phase C/D 的
  `extra_features=` 路径；因果链广播沿同一路径，per-(ticker,date)）。
- **两臂**：`arm_base`（Phase B/C/D/E1 冻结 feature_cols，`align_on="end_lag"`）；`arm_causal` =
  `arm_base` + 因果链广播列。两臂**唯一差** = 因果链列。
- **frozen LightGBM**（同 Phase B/C/D/E1 config，一字未改）。
- **CV**：`PurgedGroupKFold(5, embargo=21, group=month)`。**OOS 折仅在 cutoff 后月数内评估**
  confirmatory；cutoff 前月数入 in-sample 折（或排除出 confirmatory，§2.3）。
- **LLM 提供方冻结（承重）**：**PIN 单一提供方**（候选：GLM-4-flash 或 SiliconFlow Qwen2.5-7B——取
  **cutoff 最早**者，使 OOS 窗最大；ModelScope Qwen3-Next cutoff 较晚、OOS 窗过短，**不选**）。**禁止
  路由自动切换**（[`extraction/providers.py`](../src/aionis/extraction/providers.py) 的多键路由仅在 fallback；
  confirmatory run 须 `only_enabled=[pinned]`）。提供方 cutoff 钉死入 ledger（§9）。
- **primary 指标**：cutoff 后 OOS 月 rank-IC 差，MBB-DM + Newey-West HAC。**secondary（exploratory）**：
  策略回报 L-S Sharpe + DSR/Hansen-SPA、LAP 分层、LOO。

---

## 6. 多重检验审计（第 4 条 confirmatory → N=4）

- Phase B/C/D/E1 各 1 条 confirmatory claim（B/C/D null、E1 null 已落地）；**E2 = 第 5 条 → family N=5**
  （B=1, C=2, D=3, E1=4, E2=5，与 [`phase-e-preregistration.md`](phase-e-preregistration.md) §5「B/C/D 之后 N≥4 起」续涨一致）。
- 策略回报侧 DSR/Hansen-SPA 沿用 [`eval/multiple_testing`](../src/aionis/eval/multiple_testing.py) family 会计入 n_trials。
- **报告规则**：每个 IC 差带 **DM-p + HAC-t + cutoff-era 标签 + LAP 标签**四联；B/C/D/E1 null 一并计入家族。

---

## 7. Power（**cutoff 门的最痛代价**）

- 全 universe OOS ≈ 125 月（Phase B/C/D/E1 同）。**但 cutoff 门只保留 cutoff 后月数**——若冻结提供方
  cutoff ≈ 2024，则 confirmatory OOS 仅 ~10–18 月（2025+）。**这是 E2 最深的结构性风险**（§10 #2）。
- **可发表性门**：differential 95% CI 半宽 < 0.015（同家族）。cutoff 后 ~15 月 → σ(IC)≈0.06 时可探测月 IC
  差 ≈ 0.03（**不够紧** → 大概率 inconclusive，强化 null-favorite）。
- **唯一通向 powered 检验的诚实路径 = E3 前向累积**（按月/季增长 OOS 月数）。E2 回测本身在 cutoff 后样本
  上几乎注定 underpowered——这是 E2 正向必须 E3 复现的**功率层**理由，不只是泄漏层理由。

---

## 8. 冻结清单（**DEFERRED — run deferred；E1 null 已吸收**）

### 8.0 冻结决策（v0.1 DRAFT，未冻结；freeze 显式 DEFERRED）
> **前置（全部满足才 freeze）**：① 设计评审通过（本稿）；② 冻结单一 LLM 提供方 + 其 cutoff 经 LAP 审计；
> ③ structural-only 因果边提取模块 + hermetic PIT 测试；④ cutoff 后 OOS 月数确认（≥ 阈值，否则降级声明）；
> ⑤ §4 控制门全就绪。任一改 → 进 ledger。

| 项 | 拟冻结值（DRAFT） | 依据 |
|---|---|---|
| **arm_base** | Phase B/C/D/E1 `arm_base`（feature_cols + `align_on="end_lag"`） | differential 零点锚 |
| **arm_causal 新增列** | 因果链板块广播（per-(ticker,date)） | §3.2；列名待定稿 |
| **LLM 提供方** | PIN 单一（GLM-4-flash 或 Qwen2.5-7B，取 cutoff 最早）；禁路由切换 | §5 承重 |
| **cutoff + OOS 窗** | provider-declared cutoff + buffer → 数据末端；LAP 审计 | §2.1/§2.4 |
| **CV / h / learner** | PurgedGroupKFold(5, embargo=21, group=month)；h=21；frozen LightGBM | H6 确定性 |
| **可发表性** | differential 95% CI 半宽 < 0.015（cutoff 后月数） | §7 |
| **版本钉** | lightgbm/purgedcv/arch + 提供方模型版本（同 Phase B/C/D/E1） | H6 确定性 |

- [ ] LLM 因果边提取模块（strict Structured Outputs，reasoning-before-answer，封闭 mechanism 枚举）。
- [ ] LAP 审计（§2.4，适配 `eval/pit_audit.py`）+ cutoff-era 标签。
- [ ] cutoff 后 OOS 月数确认（若 < 阈值 → 降级为「仅 E3 可证」声明）。
- [ ] 因果边 placebo + joined-panel PIT 测试（§4 #2/#4）。
- [ ] **Phase-E2 确定性测试（H6）**：两次因果边提取 + panel-build + rank-IC → bit-identical（提供方固定）。

> **outcome pending；run deferred pending design freeze。** 本稿冻结时尚未抽取任何因果边、未观测任何
> Phase E2 OOS rank-IC。sha256 先于结果入 ledger。

---

## 9. 运行 / 账本规则（durable registry，非一次性）

- **抗泄漏锚点**：§8 冻结 config 的 sha256（含**冻结提供方 + cutoff 值**）必须在首次 `arm_causal` vs
  `arm_base` OOS rank-IC 差被观测**之前**入 `runs/ledger.jsonl`（标 `phase:"E2"`, `event:"config_committed"`）。
- **首次 confirmatory run**：前置全满足后，首次 cutoff 后 OOS rank-IC 差 → 入 ledger（`confirmatory: first`）。
- **重跑政策**：同 sha256 重跑 = 预期行为（H6）；改 config = 新 ledger 行。**改提供方 = 新行 + 重审 cutoff**
  （不同提供方 cutoff 不同 → 不同 OOS 窗 → 不可混比）。
- **探索性跑**（调 prompt / 换提供方 / LOO / LAP 分层）无限免费，只要不冒充 confirmatory。

---

## 10. 开放风险（诚实承认）

1. **泄漏只能缓解（本阶段核心风险）**：cutoff 门 + structural-only + LAP 不消除参数记忆（Lopez-Lira 非识别 +
   Fonseca 不可判定，§2.5）。**E2 正向必须 E3 前向复现才可信**——这是程序级硬约束，非可选。任何 cutoff 后
   微正都应默认怀疑为「cutoff 附近的稀释记忆 / provider cutoff 声明不准」。
2. **cutoff 门摧毁功率（最痛结构性代价）**：125 月 OOS 面板被砍到 cutoff 后 ~10–18 月 → E2 回测几乎注定
   underpowered（§7）。**这是 null-favorite 的功率层强化**，也意味着 E2 的诚实交付很可能是「干净 inconclusive
   或 null + E3 接力」，而非回测正向。
3. **事件提取 PIT（CPI/NFP 之外）**：E2 v0.1 仅 ALFRED CPI/NFP（调度日 = PIT-safe）。用户愿景的疫情/政策/
   技术位移事件**无 PIT-safe 结构化源**（news/live-cache 非 PIT，[[aionis-reference-data-source]]）→ v0.1 不含；
   需前向采集（E3 同源）或建结构化事件表，留作 E2 v0.2+。
4. **因果边的真实性/时变性**：LLM 链可能伪相关或时变（AI→电力在 23 成立、24 电力饱和后失效）；mechanism 封闭
   枚举 + LOO + 以数据修正（exploratory）护栏，但修正本身是 p-hacking 风险——由 durable-registry（§9）守。
5. **成本/token 控制**（[[aionis-dev-constraints]]）：每个宏观事件 × 因果链提取 = LLM 调用；用最便宜可用模型
  （glm-4-flash 优先）、小批、sha256 幂等缓存（[`extraction/extract.py`](../src/aionis/extraction/extract.py)）、
   有界单次重试、逐调用 token 日志。提供方池**仅 GLM/SiliconFlow/ModelScope**（[[aionis-dev-constraints]]；
   Gemini/TokenHub 已删、不得重加）。
6. **provider cutoff 声明的可信度**：cutoff 是 provider-declared，非审计真理——**LAP 审计（§2.4）是验证手段**，
   非「相信声明」。若 LAP 显示 cutoff 后仍有显著召回 → 该提供方 cutoff 声明失真 → OOS 窗须后移或换提供方。
