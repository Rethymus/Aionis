# Phase E 预注册 — 因果推理 / 仿真传播层（「透过现象求本质」）

> 状态：**v0.1 DRAFT · 2026-07-29 · 程序级（三阶段 E1→E2→E3）· 全部 run DEFERRED**。
> 这是规划文档，**不含、不跑任何 Phase E OOS 结果**。E1 build 在 Phase D 落地后启动。
>
> **来源**：用户方向（2026-07-29）——项目需要「规划预测、透过现象求本质」的能力：事件 → 行业/
> 资产含义的因果推理（例：20 疫情→医药增势；21 白酒下跌←打击劝酒文化/腐败 + 老一代退场 + 疫情
> 健康观念；22-23 AI→算力→英伟达→电力，电力趋饱和后回落），并「不断佐以数据修正预测准确率」。
>
> **决策（用户选「三者序列推进」）**：E1 结构化传播（纯抗泄漏）→ E2 LLM 宏观叙事假设生成器
> （cutoff 控制，缓解泄漏）→ E3 前向实时（投产真值）。本稿钉死程序结构 + 每阶段的泄漏处理。

---

## 0. 与 TCR 的关系 + 不可让渡的泄漏红线

- **TCR**（[`theory-of-computable-reality.md`](theory-of-computable-reality.md)）：Phase E = WRL 的**仿真/传播层**——把 $G_t$
  的观测（事件/政策/基本面/关系）沿因果/拓扑结构**传播**到含义，作为 $\hat S_t$ 的可解释推断。仍走 §3.5
  单点可证伪锚 $y_{t+h}=h(\hat S_t)+\eta$（横截面月 rank-IC）。
- **不可让渡的红线**（TCR §8.5/§11，[`frontier_positioning.md`](frontier_positioning.md)，[[aionis-tcr-theory-pivot]]）：
  - **learned generative world model 不可行**（MVP 规模：ChaosAI +7 Sharpe leak；Tan NeurIPS 2024；
    100M+ tokens）。Phase E 的传播层是**可解释的规则/网络传播 + LLM 作假设生成器（受控）**，**非**学习型生成模型。
  - **LLM 事后记忆 = 泄漏**：用 2024 训练的 LLM 去「预测」2020 事件（疫情→医药）= 它记忆了医药确实涨，
    非预测。这是项目身份明确排除的失败模式。E2 必须 cutoff/holdout 控制；E1/E3 零泄漏。
- **「以数据修正」的纪律**：推理输出是**特征/假设**，由现有可证伪 rank-IC 流水线 OOS 检验；根据哪些
  假设被验证来精化因果图/传播规则，**记为 exploratory**（绝不 fit-to-label = p-hacking）；headline 永远是
  OOS 可证伪差。与 durable-registry（[[aionis-no-disposable-research-artifacts]]）一致。

---

## 1. 三阶段程序（每阶段一条可证伪 claim，逐级叠加）

| 阶段 | 机制 | 泄漏处理 | 交付 | 状态 |
|---|---|---|---|---|
| **E1 结构化传播** | firm 级冲击沿 Phase D PIT 关系图（供应链客户 + SIC 同业 + 13D 持股人，ex-self）按可解释规则传播 | **零泄漏**（确定性规则 on PIT 数据） | 「相连实体的近期冲击」预测该 firm——网络溢出基线 | 待建（Phase D 后） |
| **E2 LLM 宏观叙事假设生成器** | LLM 枚举事件→行业/板块因果链（政策/人口/技术位移），作**待测特征**（日期广播或板块归属） | **缓解（非消除）**：LLM 训练 cutoff **之后**的数据才进 OOS；structural-only 提取（同 ERL 抗泄漏，[[aionis-erl-leakage-design]]） | 你要的「疫情→医药、AI→算力→英伟达→电力」式宏观叙事推理 | E1 后 |
| **E3 前向实时** | E1+E2 的推理**只在当前 live 事件**上跑，累积实时 OOS 战绩（无历史回测） | **零泄漏**（无未来可泄漏） | 投产真值——实时因果推理战绩 | E2 后 |

- **序列理由**：E1 是纯抗泄漏基线（复用 Phase D 图，零泄漏，可立即回测验证「网络溢出有无增量」）；
  E2 在 E1 之上叠加你要的宏观叙事（cutoff 控制缓解泄漏）；E3 是投产路径（前向累积，绕开回测泄漏）。
  每阶段独立可证伪，逐步逼近你的愿景，**任一阶段的 null 不否定其它**（机制不同）。

---

## 2. E1 可证伪 claim（结构化传播，纯抗泄漏基线）

> 在**同一 S&P 500 PIT universe** + frozen LightGBM + PurgedGroupKFold(5, embargo=21) 上，把一个
> **网络传播 bundle**——{相连同业的近期盈利惊喜传播（SIC 边）+ 供应链客户的近期收益传播（10-K Item 101
> 边，若 E1 范围内可建）+ 13D 持股人的近期动作传播（13D 边）}，作为 per-(ticker,date) 特征拼进横截面，
> 是否带来**横截面月 rank-IC 的显著增量**（**双尾**）超过「fundamentals-only + 该 firm 自身特征」基线？

- **Differential** = IC(`arm_prop`) − IC(`arm_base_self`)。arm_base_self = fundamentals + 该 firm 自身的
  earnings/13D/return（Phase B/C/D 的 self 特征）；arm_prop = arm_base_self + **相连实体**的同类冲击传播。
  两臂唯一差 = 「相连 vs 自身」→ differential 隔离**网络溢出**。
- **null = betting favorite**：Phase D 的同业动量（一种传播）已 null；更丰富的传播大概率也 null（月频已定价
  /关系传导太慢/噪音）。合法且最可能。
- **传播规则（可解释，非学习）**：相连实体冲击 = 按边类型加权（披露营收占比 / 同业等权 / 13D 持股权重）
  的相连实体近 w 日**惊喜/收益**；PIT 由「相连实体的冲击在 t 可知」+「边在 t 已披露」保证（复用 Phase D
  的 filed-date PIT）。

---

## 3. E2 设计（LLM 宏观叙事假设生成器，缓解泄漏）

- **机制**：LLM 在每个宏观事件（政策/疫情/技术位移，由 ERL/news 提取）上枚举「事件→受影响板块/资产」
  因果链 + 机制（例：AI 爆发 → 算力需求 ↑ → GPU 厂商 + 电力板块；机制：训练/推理算力 + 数据中心耗电）。
  输出 = **板块归属特征**（该事件利多/利空哪些 SIC 板块），日期广播到该板块全部 PIT 成员。
- **cutoff 控制（泄漏缓解，非消除）**：OOS 窗必须 > LLM 训练 cutoff（如用 GLM-2024，OOS 只测 2025+）；
  或用 cutoff 早于事件的老模型对历史事件生成假设。**诚实**：这只能缓解（LLM 可能记住宏观历史），不能
  像数值数据那样保证零泄漏；E2 的任何正向必须在 E3 前向战绩复现才算可信。
- **structural-only 提取**：LLM 只输出结构化因果边（事件→板块 + 方向 + 机制关键词），**不**输出市场预测
  （同 ERL 的 market_impact 抗泄漏设计，[[aionis-erl-leakage-design]]）。
- **claim**：E2 的板块归属特征是否在 cutoff 后 OOS 窗带来 rank-IC 增量？双尾，null favorite。

---

## 4. E3 设计（前向实时，投产真值）

- **机制**：E1+E2 的推理**只在「今天」的 live 事件**上跑，产出**今天**的板块/资产含义预测，**累积实时战绩**
  （每月/季的 OOS rank-IC + 策略回报）。无历史回测 → 无 LLM 事后记忆可泄漏。
- **与 reddit_sentiment 同源**（[[aionis-third-party-data-intake-rubric]]）：前向采集、到达即快照、不 backfill。
- **诚实**：战绩只能实时积累（慢，按月/季），不能立即验证；这是绕开回测泄漏的代价。E3 是 E1/E2 正向结果
  的**最终可信度检验**（前向不复现 = 回测结果是泄漏伪影）。

---

## 5. 共享纪律（三阶段统一）

- **可证伪**：每阶段 primary = OOS 月 rank-IC 差（双尾，MBB-DM + Newey-West HAC），publishability 门
  ci_half < 0.015。复用 `eval/phase_c`/`phase_d` 的 two-arm 框架。
- **抗泄漏锚点**：每阶段 config sha256 先于结果入 ledger（`phase:"E1"/"E2"/"E3"`）。
- **迭代修正**：精化因果图/传播规则 = 新 exploratory ledger 行（不 fit-to-label；headline 不可被「重跑到显著」挽救）。
- **多重检验**：E1/E2/E3 各 1 条 confirmatory claim → family N 续涨（Phase B/C/D 之后 = N≥4 起）。
- **许可**：仅 permissive（LLM 走 GLM/SiliconFlow/ModelScope 池，[[aionis-dev-constraints]]）；无新第三方历史数据。

---

## 6. 序列与冻结清单（DEFERRED）

- **前置**：Phase D 落地（fetch + run + headline）。
- **E1 冻结前置**：Phase D 关系图产物（SIC/13D；供应链若 E1 范围）+ 传播规则模块 + hermetic PIT 测试
  （相连实体冲击在 t 可知、边在 t 已披露）+ joined-panel PIT 测试。任一改 → 进 ledger。
- **E2 冻结前置**：LLM cutoff 钉死 + structural-only 因果边提取 + cutoff 后 OOS 窗确认 + 泄漏审计（LLM 是否
  输出市场预测）。**E2 的正向必须 E3 前向复现才可信。**
- **E3 冻结前置**：live 事件管道（news/政策/财报到达即推理）+ 实时战绩累积 + ledger。

> **outcome pending；全部 run deferred。** 本稿冻结时尚未观测任何 Phase E OOS 结果。

---

## 7. 开放风险（诚实承认）

1. **E1 与 Phase D 传播重叠**：Phase D 的同业动量已是一种传播（且 null）。E1 加更多边 + 传惊喜（非收益）
   可能仍 null——这是 null favorite 的体现，非失败，但意味着 E1 可能**不交付**你想要的宏观叙事（那是 E2）。
2. **E2 泄漏只能缓解**：cutoff 控制不能消除 LLM 对宏观历史的参数记忆；E2 正向必须 E3 复现。**这是整个
   Phase E 的核心风险**——你的丰富叙事愿景（E2）天然带泄漏，只能以前向（E3）兜底。
3. **宏观事件提取**：E2 需要 PIT 的事件源（政策/疫情/技术位移）——news/live-cache 非 PIT（[[aionis-xiaoyinsi-data-source]]）；
   需前向采集（E3 同源）或结构化事件表（FOMC/CPI 已有；政策/疫情需建）。
4. **因果边的真实性**：LLM 生成的因果链可能伪相关或时变（AI→电力在 23 成立、24 电力饱和后失效）；
   传播规则须时变 + 以数据修正（exploratory），但修正本身是 p-hacking 风险——由 durable-registry 守。
5. **规模**：E2 的 LLM 调用成本（每个宏观事件 × 因果链枚举）+ token 控制（[[aionis-dev-constraints]]）；
   需最便宜可用模型 + 受控重试。
