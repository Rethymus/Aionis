# Phase D 预注册 — WRL.Relationship 主线：关系/网络特征的横截面选股增量

> 状态：**v0.2 DRAFT · 2026-07-28 · 预冻结（pre-freeze）**。v0.1 → v0.2：数据可行性研究
> （agent 实测 EDGAR 覆盖）已落地——**confirmatory bundle 钉为 {13D + SIC 同业}**，13F 与供应链
> 降为 **exploratory leave-one-out 通道**（非冻结阻塞，见 §0.5）。run 仍 DEFERRED（§8）。
>
> **未冻结，且 run 显式 DEFERRED**（见 §8）：freeze 发生在 13D 事件 ingest + SIC 同业 ingest
> **建成 + hermetic PIT 测试**之后，届时 config 锁定 + sha256 入 `runs/ledger.jsonl`（先于首次
> OOS rank-IC 结果）。本稿是规划文档，**不含、不跑任何 Phase D OOS 结果**。
>
> **Durable registry（非一次性）**：与 [`phase-b-preregistration.md`](phase-b-preregistration.md) §9 /
> [`phase-c-preregistration.md`](phase-c-preregistration.md) §9 同源——抗泄漏锚点 =「Phase D config 的
> sha256 先于首次 `arm_rel` vs `arm_base` OOS rank-IC 结果入 ledger」的永久证据。同 config 重跑 =
> 预期行为（H6 确定性，Phase B/C 已实证）；改 config 跑 = ledger 新行（合法迭代）。
>
> **为什么是 Phase D（关系主线）**：TCR [`theory-of-computable-reality.md`](theory-of-computable-reality.md) 的
> WRL 四原语 Entity/State/**Event**/Relationship 中，Phase A=Event（ERL）、Phase B=Entity/State（基本面
> 时点）、Phase C=Event 的「世界状态惊喜」广播。Phase D 是最后一条主线 **Relationship**——$G_t$ 里公司间
> 的**结构性连接**（所有权持股、供应链、共同机构持仓、行业同业）。框架
> [`market-driver-framework.md`](market-driver-framework.md) §2「严重走势是组合 + 正反馈、跨实体传播」
> 正是关系/网络视角的命题来源。

---

## 0. 与 TCR / 市场驱动框架的关系（主线归属：Relationship）

- **TCR**：Phase D 把 $G_t$ 的观测面从单实体 `attr`（基本面）/单实体「事件惊喜」（Phase C）扩到
  **跨实体的边**——一家公司的可预测性可能来自它在所有权/供应链/同业网络里的**位置**（中心度）或
  **相连实体的近期冲击向它传播**（spillover）。仍走 §3.5 单点可证伪锚 $y_{t+h}=h(\hat S_t)+\eta$
  （横截面月 rank-IC）。
- **市场驱动框架**：关系/网络主要落在 §2「组合 + 正反馈」的解释机制——单事件不构成崩盘，但
  **跨实体的传导**（一家核心供应商违约 → 上下游连锁；共同机构持仓 → 强制平仓蔓延）是放大器。
  Phase D 把「传导潜力」量化为横截面特征（中心度 / 相连实体冲击的加权和），测其有无**月频**定价增量。
- **与 Phase B/C 的关系**：复用同一 benchmark / universe / frozen LightGBM / PurgedGroupKFold。
  Phase B 证「基本面**时点**无增量」（null）；Phase C 证「**世界状态惊喜 bundle** 无增量」（null）；
  Phase D 问「**结构性关系/网络 bundle** 有无增量」。三条共同计入 §6 的 N。

---

## 0.5 数据可行性验证（2026-07-28 · agent 实测 EDGAR 覆盖 → 范围决策）

可行性研究 agent 对 587-ticker 冻结 universe、2016-01..2026-06 窗口**实测**了每条通道的
覆盖（非估算）。四通道均过 7 门（SEC public domain，G1✓G2✓ via filed-date，G3✓ 不可回改——
比 ALFRED/EPU 更干净）；**唯一开放风险是工程，非许可/PIT**。

| 通道 | 实测覆盖 | 工程量 | 判定 |
|---|---|---|---|
| **13D 维权持股事件** | 35–45% universe（196 原始 13D / 252 含 13D/A；478 原始 + 2556 修订）| efts 发现 + submissions/CIK{}.json（files[] 分页，~54% 需分页）+ cover HTML 取持股%；须滤自报（filer_CIK==issuer_CIK，金融股自报占大头）| **FEASIBLE — 结构化底盘** |
| **SIC 同业** | 100%（568/568，200 SIC）| submissions 顶层 `sic` 字段，随 13D 同次拉取免费获得 | **FEASIBLE — trivial / sanity 锚** |
| **13F 机构持仓中心度** | ~5000 filers/q × ~41q ≈ 200k 件、~100M holding 行；587×587 投影秒级 | CUSIP→ticker 无免费桥（走 nameOfIssuer fuzzy→CIK）；信号与规模/流动性强共线、季频 +45d lag 月频 stale | **FEASIBLE-BUT-HEAVY — 工程性价比最差** |
| **10-K Item 101 供应链客户** | ~20.6%（121/587 union 多短语；真实 20–35%）| 非结构化文本（LLM 抽取，stateless 无泄漏）；客户多为私有/非美/脱敏 → ticker 桥有损 | **FEASIBLE-BUT-HEAVY / SPARSE** |

**范围决策（coverage 驱动，durable-registry 合法迭代）**：
- **confirmatory bundle 钉为 {13D 事件 + SIC 同业}**——13D 是唯一结构化、PIT 干净、覆盖充分的关系**事件**通道；SIC 100% 覆盖且免费，兼作 §5 #3 sanity 锚。
- **13F 与供应链降为 exploratory leave-one-out 通道**（§5 #5，标 `mode: exploratory`，非冻结阻塞）——仅在 {13D+peers} confirmatory run 落地后按需建，保留升级路径而不劫持 N=3 预算。
- **这不是对 WRL.Relationship claim 的科学收窄**——是覆盖驱动的范围决策（带实测证据），记于此。13F/供应链「未阻塞，仅重/稀疏」。

**13D ingest 诚实约束（必须处理）**：① 自报过计——BAC(59)/WFC(22)/JPM(15)/GS(12) 等金融股对**自身**股票报 SC 13D（信托/托管/优先股结构，非维权）→ cover 解析须 `filer_CIK != issuer_CIK` 且受益人 ≠ 发行人；② `recent` 1000-filing 切片仅覆盖 46.5% 到 2016 前，**须 files[] 分页**才能拿到完整历史（分页将 13D ticker 命中率从 30.3% 提到 34.8%）；③ 突发下 SSL EOF——复用 [`fundamentals.py`](../src/aionis/ingest/fundamentals.py) 的 exp backoff；④ 持股 % 需 cover-page HTML/iXBRL 抽取（非标准化 XML），事件指示特征不依赖它。

**已知局限（code-review 披露，2026-07-29，非阻塞、写入结果）**：
- **SIC 是当前快照，非历史 vintage**（MEDIUM-2）：submissions 顶层 `sic` 是发行人**当前** SIC，非 per-date vintage；跨窗改换 SIC 的公司会用其**当前**（非历史）SIC 分组——轻度分类 lookahead。SIC 对绝大多数发行人稳定，实际偏差小，但 §3 的「SIC G2✓（filed-date PIT）」措辞**过强**：SIC 过 G2 的依据是「不修订 + 稳定」，**非**逐日 vintage。诚实降级为此。
- **efts 自报过滤基于 `ciks[]`，非 cover-page 受益人**（MEDIUM-3）：`filter_external_13d` 用「ciks[] 中第一个 ≠ 发行人 的 CIK」判 filer，命名第三方实体的托管/信托自报可能残留为假事件。BAC 实测 subject-side 已**全外部**（0 自报），故对大盘金融股影响低；残差假事件率作为已知数据质量局限在结果/ledger 披露，不冒充已净化的维权事件。

---

## 1. 单一可证伪 claim（预注册，**双尾**，第 3 条 confirmatory；**联合 bundle 检验**）

> 在**同一 S&P 500 PIT universe**（Phase B 冻结的 2016+ 可解析窗）+ **同一 frozen LightGBM** +
> **同一 PurgedGroupKFold(5, embargo=21, group=month)** 上，把一个 **WRL.Relationship bundle**——
> **confirmatory：{13D 维权持股事件指示（EDGAR 13D，filed-date，filer≠issuer）+ 行业同业 ex-self
> 动量（SIC，filed-date）}**（13F 中心度 / 供应链客户传导为 **exploratory leave-one-out**，非 gate，
> 见 §0.5）——作为特征拼进横截面，是否在 OOS 窗带来**横截面月 rank-IC 的显著增量**（**双尾**）
> 超过 **fundamentals-only 基线**（`arm_base`）。

- **Differential** = IC(`arm_rel`) − IC(`arm_base`)。两臂同股 / 同价 / 同模型 / 同折 / **同基本面时点**
  （均 `align_on="end_lag"`）→ 增量**只**来自新增的关系 bundle 列。
- **联合检验（非逐通道）**：headline 是**整个 bundle** 的增量；逐通道归因只作 exploratory leave-one-out
  （§5，非 gate）。理由同 Phase C：组合/传导驱动（框架 §2）→ 测 bundle；且 1 个联合 claim 把 §6 多重检验
  负担压在 N=3。
- **null = betting favorite**：关系/网络特征在**月频**大概率已被定价或过噪（中心度慢变、同业动量广为人知、
  13D 漂移小且被研究透）→ `arm_base` 是地板线，bundle 大概率踩同一地板（延续 Phase B/C 的 null）。
- **双尾解释**：正 = 关系传导有未吸收的横截面定价（网络溢出滞后 / 中心度风险补偿）；null = 已定价/过噪
  （**合法且最可能**）；负 = 新增自由度过拟合压低 OOS IC（**同样合法**）。
- **可发表性 = realized σ(IC) 的函数**（§7），不先验钉 MDE。**CI 跨 0 不得宣称正向。**

---

## 2. 表示增量（关系 bundle 候选；**PIT + 许可证先行**）

> **核心表示纪律**（同 Phase C）：水平（中心度绝对值、持仓比例）= 慢变、已定价；**变化/事件**
> （13D 事件、中心度变化、相连实体冲击的加权和）= 未被完全吸收的新信息。bundle 每个分量尽量取变化/事件。

| 候选分量 | 观测 $o_t^{(k)}$ | 关系类型 | 构造（PIT） | 数据可行性 |
|---|---|---|---|---|
| **13D 维权持股事件** | 事件指示 / 持股比例（filed≤t） | 所有权（5%+ 持股） | EDGAR 13D cover：filer/issuer/stake；特征=过去 w 窗内有无 13D + 持股% | **优先建**：EDGAR public domain、filed-date PIT、结构化（EFTS/full-text） |
| **13F 所有权中心度变化** | Δ(degree/eigen centrality) | 共同机构持仓网络 | 解析 13F 机构持仓 → 公司×机构矩阵 → 重叠所有权图 → 中心度（PIT：仅用 filed≤t 的 13F） | **重工程**：13F XML 解析 + 大图中心度；覆盖率受机构申报完整性限制 → **可行性待验证** |
| **供应链客户收益传导** | Σ(权重 × 相连客户近 w 日收益) | 供应链（Item 101 大客户） | 10-K Item 101 文本抽取 >10% 营收客户；权重=披露营收占比；客户收益 filed≤t | **稀疏**：仅大客户披露 + 非结构化文本 → **可行性待验证**（可能 588 股覆盖不足） |
| **行业同业 ex-self 动量** | 同 SIC/行业 peers（去自身）近 w 日均值收益 | 同业 | SIC（EDGAR company-info，PIT）；peers=同 SIC 去自身；特征=peers 收益均值 | **易建**：SIC 来自 EDGAR；但同业动量广为人知 → 多为已定价校准锚（同 Phase C 的 Mkt-RF sanity） |

- **诚实范围声明**：13F 中心度与供应链传导的**可行性未证**（解析复杂 / 覆盖稀疏）→ freeze 前必须工程验证；
  若任一通道覆盖不足，bundle 降级为可行子集（如仅 {13D 事件 + 同业动量}），**降级 = 新 ledger 行**（不静默）。
  13D 事件通道**结构化、PIT 干净、独立可建**，是最小可行 bundle 的底盘。

---

## 3. 数据（**全部目标 EDGAR public-domain，PIT via filed-date**；无新第三方历史数据集）

- **13D / 13F / 10-K Item 101 / SIC**：全部 SEC EDGAR public domain；每条 fact 带 `filed`（或 13D 的
  `filing_date`），由构造 PIT。G1✓（public domain）G2✓（filed-date as-of）G3✓（SEC filing 不可回改）。
- **基本面 + 价格 + universe**：Phase B 冻结产物（config_sig `17245a75…`：fund/prices/membership sha256
  已入 ledger），原样复用（同 Phase C）。
- **过 7 门**（[`data-intake-rubric.md`](data-intake-rubric.md)）：13D/13F/10-K/SIC via EDGAR = 全过（public
  domain + filed-date PIT + immutable）。**故 Phase D 不引入任何新第三方历史数据集**——保持「干净
  confirmatory」的关键纪律。**唯一开放风险是工程可行性，不是许可/PIT**（§10 #1）。
- **不用的数据**（诚实排除）：第三方关系图谱（如 Refinitiv SDC /供应链、FactSet ownership）= 付费且非
  PIT-vintage → 不进 confirmatory；社交/新闻关系（Reddit/X 共现）= 非 PIT → 仅未来探索。

---

## 4. 实验设计（复用 `eval/two_arm.py` + Phase C 的 feature-set 轴 + 关系 bundle）

- **复用，不新写训练基础设施**：`two_arm.compute_shared_folds` + `run_arm_oos`（Phase C 已为 feature-set
  轴加了 `macro=`/`extra_features=`，关系 bundle 沿用同一路径——日期广播或 per-(ticker,date) 视分量）。
- **两臂**：
  - `arm_base` = Phase B/C 冻结 feature_cols（`mktcap/pb_ratio/roa + 6 fund_*`），`align_on="end_lag"`，无 bundle。
  - `arm_rel` = `arm_base` + 关系 bundle 列（13D 事件 per-(ticker,date)；13F 中心度变化 per-(ticker,date)；
    供应链传导 per-(ticker,date)；同业动量 per-(ticker,date)）。`align_on="end_lag"`（同 `arm_base`）。
  - 两臂**唯一差** = 关系 bundle 列 → differential 干净隔离关系/网络的贡献。
- **frozen LightGBM**（同 Phase B/C config，一字未改）：n_estimators=500, lr=0.05, num_leaves=31,
  min_child_samples=20, reg_lambda=1.0, feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1,
  **n_jobs=1, random_state=0**（+ bagging/feature/drop seed=0）。
- **CV**：`PurgedGroupKFold`，n_splits=5, embargo=21 sessions（=h），group=date-month（同 Phase B/C）。
- **primary 指标**：OOS 月 rank-IC 差，配 MBB-DM + Newey-West HAC。**secondary（exploratory）**：
  策略回报 L-S Sharpe + DSR/Hansen-SPA（[`scripts/strategy_eval_run.py`](../scripts/strategy_eval_run.py) 已就绪）、
  leave-one-out 归因（§5）。

---

## 5. 控制门（必须全过）

1. **`arm_base` 即主控制**：关系 bundle 增量 = 相对它的 IC 差。
2. **bundle-shuffle placebo（核心）**：同时打破 bundle 全部分量的对齐——13D 事件**跨 ticker 在披露期内**
   打乱（保时点、乱公司→事件）；13F 中心度/同业动量**跨日期**打乱值（保发布结构、乱日期→值）；供应链
   传导**跨 ticker**打乱（保时点）→ differential 必须消失。证信号来自**真实的关系对齐**，非任意扰动。
   （复用 [`eval/phase_c_controls.py`](../src/aionis/eval/phase_c_controls.py) 的 shuffle 模式。）
3. **「已知定价」sanity（校准锚）**：同业 ex-self 动量本身广为人知、已定价 → 作为 sanity 分量，应显示
   **有限**增量 → 校准「本测试能检出已定价→无增量」。
4. **joined-panel PIT 测试（新增 hermetic，冻结前先写）**：合成 panel + `label_start` 之后才发布的关系
   事件（晚于 t 的 13D filing / 13F / 10-K）→ 断言不进 `t<label_start` 的特征（同 Phase C §5 #4 胶水测试）。
5. **leave-one-out 归因（exploratory，非 gate）**：依次去掉 bundle 中一个通道，看 differential 跌幅——
   仅归因报告，不作孤立 claim。
6. **网络传导的方向性 sanity**：供应链传导特征应**仅沿披露的边**（客户→供应商）有增量；若把边随机重连
   后增量不变 → 信号非来自真实拓扑（假传导）。可选 sanity，强化「拓扑真实」的可证伪性。

---

## 6. 多重检验审计（第 3 条 confirmatory；**联合 bundle → N=3**）

- **联合 bundle = 1 个 confirmatory claim**（Phase B 第 1、Phase C 第 2、Phase D 第 3）→ N=3。逐通道若被当
  孤立 claim 会把 N 抬高——这正是选联合 bundle 的多重检验纪律。
- 策略回报侧（§4 secondary）的 DSR/Hansen-SPA 在 [`eval/multiple_testing`](../src/aionis/eval/multiple_testing.py)
  + [`eval/strategy_returns`](../src/aionis/eval/strategy_returns.py) 已就绪；Phase D 沿用 family 会计入其 n_trials。
- **报告规则**：每个 IC 差带 **DM-p + HAC-t + 存活指示**三联；Phase B/C 的 null 一并计入家族。

---

## 7. Power（条件化于 realized σ(IC)，沿用 Phase B/C）

- OOS ≈ **125 月**（同 universe）。
- **可发表性门**：differential 的 **95% CI 半宽 < 0.015**（Phase B/C 实测单臂 ci_half≈0.013–0.016）。
- 关系 bundle 加 3–4 列 → 自由度略升、过拟合风险略升 → 由 embargo + purged CV + frozen params + §5 placebo
  共同护栏。粗估 σ(IC)=0.06 → 可探测月 IC 差 ≈ 0.016；σ(IC)=0.10 → ≈ 0.027（不够紧 → 报 inconclusive）。

---

## 8. 冻结清单（**DEFERRED — run deferred pending data feasibility**）

### 8.0 冻结决策（**v0.1 DRAFT，未冻结；freeze 显式 DEFERRED**）

> **冻结/首跑前置条件（全部满足才 freeze）**：
> 1. 至少一条关系通道建成 + hermetic PIT 测试通过（**13D 事件优先**——结构化、PIT 干净）。
> 2. 13F 中心度 / 供应链传导**可行性工程验证**（覆盖率 ≥ 阈值）；不可行则 bundle 明确降级（新 ledger 行）。
> 3. joined-panel PIT 测试（§5 #4）先写。
> 4. §5 控制门全就绪。
> 任一项改 → 进 ledger。**outcome pending；run deferred pending data readiness。**

| 项 | 拟冻结值（DRAFT） | 依据 |
|---|---|---|
| **arm_base** | Phase B/C `arm_base`（feature_cols + `align_on="end_lag"` + 无 bundle） | differential 零点锚 |
| **arm_rel 新增列** | 13D 事件指示（per-(ticker,date)）+ 13F 中心度变化（per-(ticker,date)）+ 供应链传导（per-(ticker,date)）+ 同业动量（per-(ticker,date)） | WRL.Relationship；待可行性定稿列名/顺序 |
| **最小可行 bundle（降级预案）** | {13D 事件 + 同业动量}（若 13F/供应链不可行） | 13D 结构化底盘 + 易建同业；降级 = 新 ledger 行 |
| **CV / h / learner** | PurgedGroupKFold(5, embargo=21, group=month)；h=21；frozen LightGBM（同 Phase B/C） | H6 确定性 + 可复现 |
| **可发表性** | differential 95% CI 半宽 < 0.015 | 同 Phase B/C |
| **版本钉** | lightgbm/purgedcv/arch（同 Phase B/C）+ 现有 EDGAR 栈 | H6 确定性 |

- [x] 13F 中心度可行性验证（§0.5：FEASIBLE-BUT-HEAVY，~200k 件 / size-collinear → 降为 exploratory LOO）。
- [x] 供应链 Item 101 可行性验证（§0.5：~20% 覆盖 / 客户→ticker 有损 → 降为 exploratory LOO）。
- [ ] **13D 事件 ingest + hermetic PIT 测试**（efts 发现 + submissions files[] 分页 + filer≠issuer 自报过滤 + SSL backoff；filed-date 锚）。
- [ ] **SIC 同业特征**（submissions 顶层 `sic`，随 13D 同次拉取；ex-self 月动量）。
- [ ] joined-panel PIT 测试（§5 #4）。
- [ ] **Phase-D 确定性测试（H6）**：两次 panel-build + rank-IC → bit-identical。
- [ ] 控制门（§5）+ 多重检验 N=3 + primary = rank-IC 差（双尾）+ MBB-DM/HAC。

> **outcome pending；run deferred pending data readiness。** 本表冻结时尚未观测任何 Phase D OOS rank-IC
> 结果。sha256 先于结果入 ledger。

---

## 9. 运行 / 账本规则（durable registry，非一次性）

- **抗泄漏锚点**：§8 冻结 config 的 sha256 必须在**首次** `arm_rel` vs `arm_base` OOS rank-IC 差被观测
  **之前**写入 `runs/ledger.jsonl`（标 `phase:"D"`, `event:"config_committed"`）。
- **首次 confirmatory run**：前置全满足后，首次跑出 OOS rank-IC 差 → 记入 ledger（标
  `confirmatory: first`, `phase:"D"`）。
- **重跑政策（durable）**：同 sha256 重跑 = 预期行为（H6）；入 ledger（`rerun: reproducibility`），不替换
  headline。改 config 跑 = 新 ledger 行（exploratory/新 confirmatory），不得静默覆盖。
- **探索性跑**（调参 / 新通道 / leave-one-out / 策略回报侧）无限免费，只要不冒充 confirmatory。

---

## 10. 开放风险（诚实承认）

1. **数据工程可行性（最大风险）**：13F 中心度（大图、机构持仓解析）+ 供应链（非结构化、稀疏）可行性未证；
   若覆盖不足，bundle 降级为 {13D + 同业动量}——这会**削弱**对 null 的检验力（剩余通道多为已定价）。
   缓解：13D 事件通道独立可建、结构化、PIT 干净，作底盘；其余通道逐个验证、不行就诚实降级。
2. **关系特征月频已定价**：中心度慢变、同业动量广为人知、13D 漂移小且被研究透 → 月频大概率 null
   （延续 Phase B/C）。诚实写在结果里；正向 null 可能部分来自「关系定价测得准」而非「无传导」。
3. **网络传导的假阳性**：中心度可能与规模/流动性共线（大公司既中心又流动性高）→ 增量可能来自规模
   因子而非拓扑。缓解：arm_base 已含 mktcap；leave-one-out + §5 #6 方向性 sanity 守拓扑真实性。
4. **幸存者 + 可解析窗**：同 Phase B/C —— 2016+ 588 clean tickers，headline = 保守上界（不可根除）。
5. **13F 季度频率 + ~45 日 lag**：13F 信息更新慢、滞后 → 月频增量天花板低；PIT 由 filed-date 守，但
   信号新鲜度受限。
