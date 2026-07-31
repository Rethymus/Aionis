# Phase E3 预注册 — 前向实时累积（投产真值，零泄漏）

> 状态：**v0.1 DRAFT · 2026-07-30 · 规划文档 · run DEFERRED — E3 是 LIVE PROCESS，启动而非回测**。
>
> **修订 v0.2 · 2026-07-31 · [ADR-009](../decisions/ADR-009-e3-hybrid-causal-layer.md)**：因果层由「E2 LLM causal-broadcast」改为**混合方案**——宏观=冻结β sign-only（零-LLM）；事件(13D/8-K)=极简闭集 LLM 因果边；板块统一 FF-12。§1/§2.2/§3 已同步。pre-reg 仍 DRAFT（headline 未 ignite；shadow 1–2 月先行）。
> 本稿**不含、不跑任何 Phase E3 OOS 结果**——既不产出前向预测，也不计任何前向 rank-IC。
>
> **来源**：E2 设计（[`phase-e2-preregistration.md`](phase-e2-preregistration.md) §7）揭示一个结构性事实——
> **E2 的回测近确定 underpowered**：cutoff 门把 125 月 OOS 面板砍到冻结提供方 cutoff 之后约
> **10–18 月**（§2.1），在 σ(IC)≈0.06 下探测月 IC 差 ≈ 0.03 远不够 publishability 门（ci_half<0.015）。
> 即「用户的宏观因果预测愿景（疫情→医药、AI→算力→英伟达→电力）」在**回测**里几乎注定 inconclusive。
> **唯一通向 powered 检验的诚实路径 = E3 前向累积**（按月增长 OOS 月数，无回测泄漏）——这是 E3 的战略身份。
>
> **Phase E 程序定位**（[`phase-e-preregistration.md`](phase-e-preregistration.md) §1）：E1 结构化传播（**已 null**，
> 零泄漏基线）→ E2 LLM 宏观叙事（cutoff 控制，**缓解**泄漏，回测 underpowered）→ **E3 前向实时**
> （**零泄漏 by construction**，投产真值）。E3 = E1+E2 的推理**只在「今天」live 事件上跑**，累积实时战绩。
> **E2 的任何正向必须 E3 前向复现才可信**（[`phase-e-preregistration.md`](phase-e-preregistration.md) §6 程序级硬约束）。

---

## 0. 与 TCR / Phase E 程序的关系 + 本阶段不可让渡的红线

- **TCR**（[`theory-of-computable-reality.md`](theory-of-computable-reality.md)）：E3 仍是 §3.5 单点可证伪锚
  $y_{t+h}=h(\hat S_t)+\eta$（横截面月 rank-IC）。$\hat S_t$ 的推断**只用 $I_t$**（A3）——E3 把这一约束推到
  最强形式：**$I_t$ = 今天及之前**，预测的是**真实的未来** $y_{t+h}$（$t+h=21$ sessions 后才实现）。
- **不可让渡的红线**（E3 的身份）：
  - **commit-then-reveal**：每个前向预测**在结果可知之前** sha256 入 forward ledger（§9）。这是项目核心
    抗泄漏锚点（config/预测 sha256 先于结果）在 live 层的等价物——比回测更强：**没有未来可泄漏**。
  - **forward-only，到达即快照，不 backfill**（同 [`reddit_sentiment.py`](../src/aionis/ingest/reddit_sentiment.py)）：
    前向采集 = 一条单向时间流；任何「回去补采集」= 构造未来可见性 = 泄漏，被结构性禁止。
  - **headline 永不 retroactively 改进**：前向战绩是冻结预注册 config 的累积产出；重跑到「更显著」是 p-hacking，
    由 durable-registry（§5/§9）与 multiple-testing 家族（`eval/multiple_testing.py`）守。

> **与 E2 的承重区别**：E2 的泄漏只能**缓解**（Lopez-Lira 非识别 + Fonseca 不可判定，E2 §2.5）；E3 的泄漏
> **by construction 为零**——预测所用的 $I_t$ 里，结果 $y_{t+h}$ **尚未发生**，无「记忆的对象」。E3 不需要
> cutoff 门（§2.2），也不需要 LAP 记忆审计：LLM 的训练 cutoff **始终 < 今天**（任何模型的 cutoff 都不可能
> ≥ live 当下），故被预测的 forward 事件对 LLM 而言是**真未知**。E2 的记忆风险在 E3 里被结构性溶解，而非缓解。

---

## 1. 单一可证伪 claim（前向累积 OOS rank-IC；与 B/C/D/E1/E2 同锚，但 character = 累积非单发）

> 把 **E1 结构化传播 + E2 LLM 宏观因果链**的推理 bundle，**从 launch 日起按月前向运行**：每月末 rebalance，
> 在今天的 PIT $I_t$ 上跑模型 → 产出 per-ticker forward score → sha256 冻结（预测 + config）→ $t{+}h=21$ sessions
> 后结果实现 → 计分，追加到 forward ledger。**累积的前向 OOS 横截面月 rank-IC 是否随月数增长，与 0
> （与 random-walk 95% 带）可区分？**（双尾）

- **Differential** = 前向 IC(`arm_e13`) − 前向 IC(`arm_base`)。`arm_base` = **fundamentals-only，同月前向跑**（冻结
  Phase B `arm_base`，`align_on="end_lag"`）；`arm_e13` = `arm_base` + E1 传播列(`propagate_panel`，FF-12 分组，零-LLM) + E2-宏观(冻结β sign-only，FF-12，CPI+NFP，零-LLM) + E2-事件(13D/8-K 极简闭集 LLM 因果边：`direction` 定号 + `mechanism_keyword` one-hot)，全部在
  live $I_t$ 上前向计算。两臂唯一差 = E1+E2 的因果推理 bundle（同 E1/E2 differential 结构，只是 OOS 区从历史回测
  改为前向累积）。
- **这是 powered 检验**（E2 §7 的诚实续论）：E2 回测被 cutoff 门砍到 ~15 月 → underpowered；E3 **按月累积**，
  N 随日历增长，是这条因果推理假设**唯一**能攒到 publishability 门（ci_half<0.015）的路径。
- **null = 合法且最可能**（沿用 B/C/D/E1/E2 的 efficient-markets 先验）：月频已定价 / 因果链广播太粗 / 月 rank-IC
  被噪音主导。合法结论 = 「干净 inconclusive（攒不够月）」或「前向 null（攒够月仍 CI 跨 0）」，二者都诚实可发表。
- **character 诚实声明（与单发 claim 的关键差异）**：E3 **不是一次跑完的 confirmatory run**，而是一个**累积过程**。
  verdict **由日历时间 gate**：当累积前向月数 ≥ 预注册阈值（§7）、且 ci_half<0.015 时才作 confirmatory 裁定。
  在此之前，dashboard 的前向 IC 带 = exploratory 累积视图，**不得**当作 confirmatory 信号宣告。

---

## 2. 零回测泄漏框架（E3 的核心论证：为什么 forward by construction 无泄漏）

> 回测泄漏的本质 = 「模型在 $t$ 时刻可见了 $>t$ 的信息」。前向框架**让 $>t$ 的信息在 $t$ 时刻物理上不存在**。

### 2.1 forward = 没有未来可泄漏
- 前向预测在 $t$ 作出，结果 $y_{t+h}$ 在 $t{+}21$ sessions（≈ 1 交易月）后才**真实实现**。不存在「隐藏的未来标签」
  可被 feature 构造、target 对齐、或样本选择泄漏——因为预测作出时，未来尚未发生。
- 这是「paper trading / forward track record 作为唯一无 lookahead 测试」的方法论共识的严格形式化：walk-forward 的
  极限就是 forward-only——**当 IS 窗不存在、OOS 窗就是真实未来时，lookahead 的攻击面归零**。

### 2.2 cutoff 门在 E3 里 moot（E2 记忆风险的溶解）
- E2 的承重风险：LLM 参数化记忆了 cutoff 前的已实现结果（Lopez-Lira et al. 2025，`arxiv.org/abs/2504.14765` 的
  functional lookahead bias）→ E2 用 cutoff 门把 OOS 窗推到 cutoff 之后（只能缓解，不能证明消除）。
- **E3 里被预测的 forward 事件尚未发生** → LLM 无「已实现结果」可记忆 → 记忆通道**结构性消失**。LLM 的 cutoff
  始终 < 今天（live 当下），故每个 forward 事件对当前 LLM 都是 post-cutoff 的新事件——E2 的 cutoff 门在 E3 里
  **自动满足，无需单独施加**。
- **仍继承 E2 的 structural-only 提取纪律**：live LLM 调用只输出因果边/schema（`event→[(sic_sector, direction,
  mechanism_keyword, horizon_bucket)]`），**绝不**输出 `market_impact`/`expected_return`/`historical_similarity`
  （同 E2 §2.2，[[aionis-erl-leakage-design]] 抗泄漏）。forward 不可泄漏 ≠ LLM 可输出预测——structural-only 是独立
  的护栏，防止 LLM 把其叙事先验伪装成结构信号。
- **[ADR-009 修订]**：混合方案下，**宏观×板块通道零-LLM**（冻结β sign-only 表，无文本输入 → I5 泄漏面消失）；**事件通道(13D/8-K) 极简闭集 LLM 边**：`{sic_sector(FF-12), direction, mechanism_keyword, horizon_bucket}`，`extra="forbid"`，GLM-4-Flash 免费额度，幂等 sha256 缓存。`mechanism_keyword` = `{earnings_signal, ownership_change, guidance, other}`（4 词，事件机制向，低 N 可学）。

### 2.3 commit-then-reveal = live 层的「sha256 先于结果」
- 项目核心抗泄漏锚点（[`data-intake-rubric.md`](data-intake-rubric.md) + [`phase-b-preregistration.md`](phase-b-preregistration.md)
  §9）是「config / data sha256 先于 OOS 结果入 ledger」。E3 把它推到**逐预测粒度**：每条前向预测的
  `{predict_ts, target_t, scores_vector, frozen_config_sha256}` 在结果实现**之前** sha256 入 forward ledger
  （§9）。事后无法篡改——结果到来只是「揭示」已承诺的预测。

---

## 3. 前向架构（month-end rebalance 闭环；复用 E1+E2 推理 + 现有 two_arm 机制）

```
每月末 rebalance t（严格交易月末日收盘后）:
  1. FREEZE   live I_t 快照: 截至 t 可知的全部 PIT 数据（filed ≤ t 的 filings、released ≤ t 的 macro、
              universe constituents-on(t)、当日 SIC、已提交 13D）→ sha256 快照入 forward ledger
              （event:"forward_iset_frozen", iset_sha256）。
  2. RUN      E1 传播（features/propagation.py，ex-self **FF-12** peer 冲击传播，零-LLM）+ E2-宏观（冻结β
              sign-only × surprise_z，CPI+NFP，零-LLM）+ E2-事件（13D/8-K 极简闭集 LLM 因果边，GLM-4-Flash）
              [ADR-009]，全部 on I_t → per-ticker forward score ŷ_t。
              LLM 调用幂等缓存（extraction/extract.py sha256 cache）；token/成本控制（[[aionis-dev-constraints]]）。
  3. COMMIT   预测向量 + 冻结 config sha256 入 forward ledger（event:"forward_prediction_committed",
              commit_ts, target_t = t + 21 sessions, scores_sha256）。← 结果可知之前，不可篡改。
  ── 21 sessions 后 ──
  4. SCORE    拉取 realized forward return r_{t→t+21}（Tiingo/Alpaca，同 Phase B 价格源）→
              计该月 rank-IC 贡献 → append（event:"forward_outcome_scored", target_t, ic_point）。
  5. APPEND   累积前向 IC = 全部已 scored 月的 rank-IC 序列；MBB-DM + Newey-West HAC；
              dashboard 前向带更新。
```

- **复用，不新写推理/训练基础设施**：E1（`features/propagation.py` + `eval/phase_e1.py`）+ E2（因果链广播沿
  `selection_panel.extra_features` + `two_arm.run_arm_oos`）原样复用；E3 新增的只是**前向调度环 + forward ledger +
  commit-then-reveal 时序**（§9）。`eval/cv.py:purged_walk_forward_splits` 已存在，作前向切分锚点。
- **frozen LightGBM**（同 Phase B/C/D/E1/E2 config，一字未改）；**frozen LLM 提供方**（E2 §5 钉死的单一提供方）。
- **h=21 sessions**（同全家族 embargo/h），月频 rebalance。结果 horizon 与 E1/E2 一致，跨阶段可比。

---

## 4. live 事件源（PIT-safe，已过 7 门；E3 只跑这些）

> E3 的 forward 只在 **PIT-safe AS-THEY-HAPPEN** 的事件源上跑。news/social（rubric-fail）**不进 confirmatory**。

| 源 | live 机制 | PIT-safe 依据 | 现有模块 |
|---|---|---|---|
| **13D / 13D/A** | 每月 poll EDGAR `submissions_{cik}.json`，快照 t 之后新 filed 的 SC 13D | 「SEC EDGAR public domain（17 U.S.C. §105）；**filed-date PIT**；immutable（amendments = 新行）」+「as-filed」 | [`ingest/stakes_13d.py`](../src/aionis/ingest/stakes_13d.py)（Phase D 已用，filed-date PIT）+ `stakes_13d_efts.py` |
| **FRED 宏观（CPI/NFP）** | 每个 ALFRED 调度发布日触发：发布到达即算 surprise | 「the surprise for the release at time r is **REVEALED AT r**」+ ALFRED vintage as-of join（不可回改） | [`features/macro_surprise.py`](../src/aionis/features/macro_surprise.py)（Phase C 已用，scheduled release） |
| **earnings 发布** | 8-K Item 2.02（SEC 强制 material earnings release 披露）到达即采；发布日历 scheduled | 8-K as-filed = filed-date PIT（同 13D 构造）；release calendar 在 $I_t$ 内 | 待建（复用 `ingest/fundamentals.py` EDGAR 栈；8-K form-type 过滤） |
| **universe + 价格 + 基本面** | Phase B 冻结产物前向延伸 | constituents-on(t) PIT（无 forward-fill）；价格 Tiingo/Alpaca | [`ingest/universe.py`](../src/aionis/ingest/universe.py) + `fundamentals.py` |

- **不用的源（诚实排除）**：**news / live-cache / social 历史** = rubric-fail（G2 非 PIT / G3 回改 / G6 selection），
  见 [[aionis-xiaoyinsi-data-source]]、[`data-intake-rubric.md`](data-intake-rubric.md) 接入决策表。
- **reddit_sentiment 的角色**：[`reddit_sentiment.py`](../src/aionis/ingest/reddit_sentiment.py) 的前向采集纪律
  （snapshot-on-arrival、UTC `snapshot_ts`、sha256 不可变 raw、append-only parquet、ledger `forward_only:true`）是
  **E3 的数据纪律范本**；但 retail-attention 是 G6 selection-biased → `mode: exploratory`，**可前向并行采集**，
  **不进** confirmatory 前向 rank-IC。E3 confirmatory 只跑上表四源。
- **用户愿景事件的诚实映射**：疫情/政策/技术位移这类「叙事事件」**无 PIT-safe 结构化 live 源**（E2 §10 #3 同结论）。
  E3 v0.1 的 confirmatory 事件 = 13D + macro + earnings（有 PIT-safe live 源者）；更丰富的叙事事件 = E3 v0.2+
  （需先建 PIT-safe 结构化事件表，或接受其仅作 exploratory 叙事层）。

---

## 5. 自演化纪律（持续自我进化，但不 p-hacking）

> 用户的「持续自我进化」愿景在 E3 里有诚实落点：**validated 前向预测可精化因果图，但精化 = 新 exploratory 行，
> headline 永不 retroactively 改进**。这是 durable-registry（[[aionis-no-disposable-research-artifacts]]）在 live 环上的应用。

- **精化 = 新 config = 新 ledger 行**：从前向战绩中发现「某 mechanism_keyword 在 high-IC 月过表征、低-IC 月欠表征」
  → 修订因果链 schema/广播权重 → 产出一个**新 frozen config（新 sha256）** → 从该日起**另起一条前向预测序列**
  （旧的冻结序列原样保留）。绝不把新 config 套回旧预测重算（那 = 用后见信息改前向战绩 = 泄漏 + p-hacking）。
- **headline 永远是冻结预注册 config 的累积 IC**：可被「重跑到显著」挽救的不是 headline；headline 是 launch 日冻结、
  从不改 config 的那条前向序列。任何「改进版」是平行 exploratory 序列，直到它自己也攒够独立前向月数。
- **multiple-testing 守全家**：`eval/multiple_testing.py` 的 `deflated_sharpe` / `hansen_spa` / `hansen_mcs` /
  `pbo` / `harvey_liu_haircut` 已就位（Phase B 起家族会计）。每条精化 = n_trials +1；前向 L-S Sharpe 须经 DSR/Hansen-SPA
  deflation，与 Phase D strategy-return lens 同源。exploratory 精化无限免费，只要不冒充 confirmatory。
- **因果图时变性（E2 §10 #4 的 forward 解）**：AI→电力在 23 成立、24 饱和后失效——回测里这是 leakage-prone 的时变，
  前向里这是**自然演化**：模型在每个 rebalance 用**当日 $I_t$** 重新跑 LLM 因果链，链本身随 live 事件流变。
  时变性在前向里不是 bug 是 feature——但仍受 structural-only + 新行纪律约束。

---

## 6. 控制门（前向随机走带 + 冻结 arm_base 同前向 + placebo 同前向）

1. **forward random-walk 95% 带（核心控制）**：零技能 null 下，累积前向 IC 应在 random-walk 带内（dashboard 已有
   「Cumulative IC vs random-walk 95% band」视图，[`dashboard/app.py`](../dashboard/app.py) §tabs.Curve Evolution）。
   前向 IC **持续出带** = 信号；带内游走 = 与零技能不可区分。这条带就是 E3 的「可区分于 0」判据的 live 形式。
2. **冻结 `arm_base` 同月前向跑**：fundamentals-only 也按月前向累积，differential 隔离 E1+E2 bundle 的因果推理增量。
3. **「无因果边」placebo 同前向**（E2 §4 #2 的 forward 版）：保留事件时点 + 板块广播结构，随机重连 event→sector 边，
   **同样按月前向累积** → placebo 前向 IC 应在零附近游走。证信号来自**真实因果对齐**，非任意板块扰动。
4. **horizon sanity（exploratory，非 gate）**：h=21 主锚；可平行累积 h=10 / h=42 前向序列作 robustness 报告
   （复用 E1 horizon sweep 框架）。

---

## 7. Power（前向累积是 powered 路径——但 calendar-time 慢，这是最痛的诚实代价）

- **powered 的来源**：E3 的 N = 累积前向月数，**按日历线性增长**（≈ +1 月 / 月）。E2 回测被 cutoff 门锁死在 ~15 月；
  E3 从 launch 日起逐月累积，无上限——**这是因果推理假设唯一能攒到 publishability 的路径**。
- **publishability 门**（同家族）**〔[ADR-010](../decisions/ADR-010-sesoi-tost-sequential-gate.md) 修订 2026-07-31〕**：
  不再是"95% CI 跨零 + ci_half<0.015"的精度门，而是**预注册等价 + 序贯** —— (a) **SESOI = ±0.010**（事后成本门槛）；
  (b) **HAC-aware TOST @ 90% CI** 整体落入 [−0.010, +0.010] 才算等价（Lakens 2018；Newey-West HAC）；
  (c) **O'Brien-Fleming 序贯**，n ∈ {60, 90, 120} 月 alpha-spending 三 look（早期保守，末 look≈nominal；look 间仍 EXPLORATORY）；
  (d) **n_trials = 30** 多重校正（DSR/SPA/MCS）。粗算：σ(IC)≈0.06 下 80% power 需 ~283 月 → **E3 的 verdict 以年计，不以周/月计**。
  "非等价" ≠ "市场有效"，只 = "此 bundle 在此实现下未达 SESOI"。旧 B/C/D/E1 ledger 不改写（语言更新为 CV-proxy）。
- **诚实代价**：E3 **不能「现在跑出 verdict」**——它启动一个 live process，verdict 由日历 gate。这是用「回测的速度（可泄漏）」
  换「前向的诚实（不可泄漏）」。任何「快速验证因果预测」的诉求，E3 的诚实回答是「不行，只能等」。
- **可发表性 = realized σ(IC) 的函数**（同 E2 §7）：CI 跨 0 不得宣称正向；攒不够月 = 干净 inconclusive（合法、可发表）。

---

## 8. 冻结清单（DEFERRED — E3 是 LIVE PROCESS；冻结 = 启动条件，不是回测前置）

### 8.0 启动条件（全部满足才 launch；任一改 → 进 ledger）

> 前置：① E2 冻结落地（cutoff 钉死 + structural-only 因果边模块 + cutoff 后 OOS 窗确认，即便 underpowered）；
> ② live 事件管道（13D poll + FRED scheduled + 8-K earnings）前向采集模块 + 到达即快照 + hermetic PIT 测试；
> ③ forward ledger（commit-then-reveal，§9）+ 逐月计分闭环；④ dashboard 前向 IC 带 tab；
> ⑤ frozen config（learner + LLM 提供方 + 因果 schema）sha256 钉死。

| 项 | 拟冻结值（DRAFT） | 依据 |
|---|---|---|
| **frozen config（headline 序列）** | Phase B `arm_base` + E1 传播 + E2 因果链广播；frozen LightGBM；frozen 单一 LLM 提供方 | §3；H6 确定性 |
| **h / rebalance** | h=21 sessions；月末 rebalance | 同家族 |
| **live 事件源** | 13D（EDGAR submissions）+ CPI/NFP（ALFRED）+ earnings（8-K）；**禁** news/social confirmatory | §4 |
| **forward ledger 字段** | `{predict_ts, target_t, iset_sha256, scores_sha256, config_sha256}` commit；`{target_t, ic_point}` score | §9 commit-then-reveal |
| **publishability** | 累积前向 differential ci_half < 0.015（累积月数 ≥ 阈值后） | §7 |
| **版本钉** | lightgbm/purgedcv/arch + LLM 提供方模型版本（同 E2） | H6 确定性 |

- [ ] live 事件前向采集模块（13D poll / FRED scheduled / 8-K），到达即快照、不 backfill、G7 礼貌（SEC ≤10 req/s）。
- [ ] forward ledger（append-only，commit-then-reveal 时序）+ 结果揭示幂等性测试。
- [ ] 逐月计分闭环 + 累积 IC MBB-DM/NW-HAC + random-walk 带计算。
- [ ] dashboard 前向 IC 带 tab（扩展现有 Curve Evolution 视图）。
- [ ] **Phase-E3 确定性测试（H6）**：同 $I_t$ 快照 + 同 config 两次前向 → bit-identical scores（LLM 提供方固定 + 幂等缓存）。

> **outcome pending；launch deferred pending freeze。** 本稿冻结时尚未产出任何前向预测、未观测任何前向 rank-IC。
> headline frozen config sha256 先于首条前向预测入 forward ledger。

---

## 9. 运行 / 账本规则（forward ledger = append-only；commit-then-reveal）

- **抗泄漏锚点（逐预测粒度）**：每条前向预测的 `{predict_ts, target_t, iset_sha256, scores_sha256, config_sha256}`
  必须在对应 `target_t` 的结果可知**之前**入 forward ledger（标 `phase:"E3"`, `event:"forward_prediction_committed"`）。
  这是 §0 commit-then-reveal 红线的账本落点——比 B/C/D/E1/E2 的「config sha256 先于结果」更细：**逐预测、逐月**。
- **结果揭示 = append，绝不覆盖**：`event:"forward_outcome_scored"` 追加 realized IC 贡献；结果到来只是揭示已承诺预测，
  不改预测。重算/重揭示 = 预期（H6），改预测/改 config = 新 ledger 行（新前向序列）。
- **durable registry（非一次性）**：同 E2 §9——同 sha256 重跑免费（H6）；改 config（含 LLM 提供方、因果 schema、广播权重）
  = 新前向序列；exploratory 精化无限免费，不冒充 confirmatory headline。
- **与 B/C/D/E1/E2 ledger 同栈**：复用 `runs/ledger.jsonl` append-only 结构（`{ts, config_sig, config, results, notes}`），
  新增 `phase:"E3"` + `event:"forward_*"` 行类型；`reporting/results.py:save_run`（schema_version 2 additive）原样复用。

---

## 10. 开放风险（诚实承认）

1. **慢（最痛、最结构性）**：verdict 以年计。E3 启动即沉没——持续采集/计分成本（LLM 调用 + EDGAR poll + dashboard），
   换取「不可泄漏」的唯一性。中途若放弃 = 累积月数归零、不可恢复。**这是用诚实换速度的不可逆代价。**
2. **E2 underpowered → E3 是单点押注**：因果推理假设的 powered 检验**全部**压在 E3 前向。若 E2 回测 inconclusive（最可能），
   E3 是唯一兜底；若 E3 也攒够月仍 null，则因果推理愿景在月频横截面上被诚实否定（合法、可发表，但终结此线）。
3. **事件源覆盖 vs 愿景**：用户愿景的叙事事件（疫情/政策/技术位移）无 PIT-safe 结构化 live 源 → E3 v0.1 confirmatory
   只覆盖 13D/macro/earnings（PIT-safe live 源者）。愿景的「完整」叙事验证需 v0.2+ 建结构化事件表，或接受叙事仅作
   exploratory 解释层。
4. **launch 即冻结的 config 风险**：headline 序列的 frozen config（learner + LLM 提供方 + 因果 schema）在 launch 日钉死，
   之后即使发现 schema 缺陷也只能另起新序列（§5）。launch 前的 schema 评审（E2 §3.1 封闭 mechanism 枚举）是承重前置。
5. **LLM 提供方漂移**：若 frozen 提供方停服/改 cutoff/改权重 → 前向序列「断链」。预案：提供方冻结 + sha256 幂等缓存
   覆盖可复现的历史部分；断链后只能新序列（换提供方 = 新 cutoff = 新行，同 E2 §9）。仅 GLM/SiliconFlow/ModelScope 池
   （[[aionis-dev-constraints]]）。
6. **live 数据腐烂**：EDGAR/Tiingo/Alpaca 任一断供 → 前向采集中断 → 累积月数暂停（不可伪造缺失月）。G7 礼貌（限速、
   User-Agent）是防封 = 防数据腐烂（[`data-intake-rubric.md`](data-intake-rubric.md) G7）。
