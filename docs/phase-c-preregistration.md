# Phase C 预注册 — 世界状态「惊喜/变化」BUNDLE 的横截面选股增量（B+C 合并）

> 状态：**v0.1 DRAFT · 2026-07-28 · 预冻结（pre-freeze）**。
> **未冻结，且 run 显式 DEFERRED**（见 §8）：freeze 发生在 `features/vix_surprise.py` +
> `features/earnings_surprise.py` 两个新转换模块**建成 + 测试**之后（Reddit 前向采集另需
> 累积足够历史），届时 config 锁定 + sha256 入 `runs/ledger.jsonl`（先于首次 OOS rank-IC
> 结果）。本稿是规划文档，**不含、不跑任何 Phase C OOS 结果**。
>
> **Durable registry（非一次性）**：与 [`phase-b-preregistration.md`](phase-b-preregistration.md) §9
> 同源——抗泄漏锚点 =「Phase C config 的 sha256 先于首次 `arm_macro` vs `arm_base` OOS rank-IC
> 结果入 ledger」的永久证据。同 config 重跑 = 预期行为（H6 确定性，Phase B 已实证
> `H6_deterministic: true`）；改 config 跑 = ledger 新行（合法迭代）。详见 §9。
>
> **B+C 合并的理由（pivot 说明）**：① 初稿把 VIX **水平值**当 ③ 风险溢价代理——但 VIX 水平
> 高度自相关、广为人知，**大概率已定价**（初稿 §10 caveat #2 已自警）→ 改用 **VIX-surprise**
> （ΔVIX 或 AR-residual，即「风险溢价的*变化*」，未定价的那部分）。② 单变量检验弱、且与
> [`market-driver-framework.md`](market-driver-framework.md) §2「严重走势是**组合 + 正反馈**、非单
> 事件」相悖 → 改测**惊喜/变化 BUNDLE 的联合增量**，而非逐变量孤立检验（也顺带把多重检验
> 负担压在 1 个联合 claim 上，见 §6）。③ earnings-surprise 用**季节性随机游走代理**（EPS_q 期望
> = EPS_{q-4}）绕开 consensus 付费墙 → 把框架 ① 现金流惊喜**纳入**本 claim（初稿列为「未来」）。

---

## 0. 与 TCR / 市场驱动框架的关系（主线归属：①③⑤）

- **TCR**（[`theory-of-computable-reality.md`](theory-of-computable-reality.md)）：Phase C 把 $G_t$ 的
  观测面从 Entity 级 `attr`（基本面）扩到**跨截面广播的宏观/风险偏好惊喜** + **per-ticker 盈利惊喜**
  ——即 TCR §3.3 观测模型 $o_t^{(k)}\sim g_k(S_t,b_k)$ 的多条 channel。仍走 §3.5 单点可证伪锚
  $y_{t+h}=h(\hat S_t)+\eta$（横截面 rank-IC）。
- **市场驱动框架**（[`market-driver-framework.md`](market-driver-framework.md) §1 的 5 线）。本 Phase C
  bundle 覆盖三条主线，**全部取变化/惊喜、非水平**（水平已定价，框架 §1 纪律 + §2 组合逻辑）：
  - **⑤ 实际 vs 预期**：`macro_surprise.py` 的 CPI/NFP `surprise_z`（ALFRED as-of）✓ 已落地。
  - **③ 风险溢价的变化**：**VIX-surprise**（ΔVIX 或 AR-residual of `vix_as_of`）——**非 VIX 水平**。
    新转换 `features/vix_surprise.py`（并行在建）。
  - **① 现金流惊喜**：**earnings-surprise 代理**（per-ticker EPS actual vs 季节性随机游走
    EPS_{q-4}，z-scored）。新转换 `features/earnings_surprise.py`（并行在建）。
  - **（未来）③/⑤ 情绪**：Reddit sentiment（`PRAW`+`FinBERT` **前向采集**，到达即快照，不
    backfill）——累积足够历史后并入 bundle。
- **与 Phase B 的关系**：复用同一 benchmark / universe / frozen LightGBM / PurgedGroupKFold。Phase B
  证「基本面**时点**无增量」（clean null：differential `−0.00080`、`dm_p_mbb=0.870`、n=125，
  config_sig `17245a75…`）；Phase C 问「**世界状态惊喜 bundle** 有无增量」。两条共同计入 §6 的 N。

---

## 1. 单一可证伪 claim（预注册，**双尾**，第 2 条 confirmatory；**联合 bundle 检验**）

> 在**同一 S&P 500 PIT universe**（Phase B 冻结的 2016+ 可解析窗，588 clean tickers）+ **同一
> frozen LightGBM** + **同一 PurgedGroupKFold(5, embargo=21, group=month)** 上，把一个**世界状态
> 惊喜/变化 BUNDLE**——{CPI/NFP `surprise_z`（ALFRED）+ VIX-surprise（Δ或 AR-residual）+
> earnings-surprise 代理（EPS vs EPS_{q-4}）}——作为特征拼进横截面（macro/VIX 走
> `build_selection_panel(macro=…)` 日期广播；earnings-surprise per-(ticker,date) 对齐），是否在 OOS
> 窗带来**横截面月 rank-IC 的显著增量**（**双尾**）超过 **fundamentals-only 基线**（Phase B
> `arm_base`：period-end+lag 时点、纯 fundamentals feature_cols）。

- **Differential** = IC(`arm_macro`) − IC(`arm_base`)。两臂同股 / 同价 / 同模型 / 同折 / **同基本面
  时点**（均 `align_on="end_lag"`）→ 增量**只**来自新增的 bundle 列。
- **联合检验（非逐变量）**：headline 是**整个 bundle** 的增量，**不**拆成 3 个孤立 claim。理由见
  pivot：组合驱动严重走势（框架 §2）→ 测 bundle；且 1 个联合 claim 把 §6 多重检验负担压在 N=2。
  逐变量归因只作 **exploratory leave-one-out**（§5，非 gate）。
- **null = betting favorite**：惊喜/变化在月频已被有效定价（efficient-markets 先验）+ Phase B 已证
  「同 universe 上基本面时点无增量」→ `arm_base` mean_ic≈0.0153 是地板线，bundle 大概率踩同一地板。
- **双尾解释**：正 = 惊喜组合的横截面定价未完全吸收（扩散滞后 / 风险补偿可提取）；null = 已定价
  （**合法且最可能**）；负 = 新增自由度过拟合压低 OOS IC（**同样合法**）。
- **可发表性 = realized σ(IC) 的函数**（§7），不先验钉 MDE。**CI 跨 0 不得宣称正向。**

---

## 2. 表示增量（每个观测打主线标签；**变化/惊喜 优先于水平**）

> **核心表示纪律**：水平（VIX 收盘、EPS 绝对值、宏观指标水平）= 广为人知、已定价；**变化/惊喜**
> （Δ、AR-residual、actual−expectation）= 未被完全吸收的新信息。框架 §1 纪律 + §2 组合逻辑都指向
> 「**取惊喜、弃水平**」。本 bundle 每个分量都是变化/惊喜。

| 分量 | 观测 $o_t^{(k)}$ | 主线 | 构造（PIT） | 选择偏差 $b_k$ |
|---|---|---|---|---|
| **macro-surprise** | CPI/NFP `surprise_z` | ⑤ | first-print − trailing-12 实际变化均值；z=raw/trailing-24 σ，clip±5（`macro_surprise.py`） | 统计期望 ≠ survey 共识（弱化信号） |
| **VIX-surprise** | ΔVIX **或** AR(p)-residual | ③ | `vix_as_of` 的差分 / 或 PIT 拟合 AR(p)（只用 ≤d vintage）的残差（`features/vix_surprise.py`，在建） | ΔVIX 含可预测漂移 → AR-residual 更干净（freeze 选一） |
| **earnings-surprise** | (EPS_q − EPS_{q-4})/\|EPS_{q-4}\|，z-scored | ①+⑤ | EPS=net_income/shares_out（EDGAR XBRL，PIT via filed）；期望=同季上年 EPS_{q-4}（季节性随机游走，Foster-Olsen-Shevlin 1984 naive benchmark）；z 窗 PIT（`features/earnings_surprise.py`，在建） | 随机游走 ≠ analyst 共识；\|EPS_{q-4}\|≈0 → NaN 丢 |
| **（未来）Reddit sentiment** | bull_ratio / score（FinBERT） | ③/⑤ | PRAW **前向**采集 + 到达即快照；**不 backfill**（Pushshift 已死） | 被讨论度 selection；仅前向 |

- **两类对齐结构（诚实）**：macro-surprise + VIX-surprise 是**日期广播**（一日期一值，
  `build_selection_panel(macro=…)` 广播到当日全部 PIT 成员）；earnings-surprise 是 **per-(ticker,date)**
  （每公司自己的 EPS 惊喜，像 fundamental 列一样按 (ticker,date) 对齐）。bundle **混合**这两类。
- **PIT 时点**：惊喜在发布/披露日 r **揭示于 r**；expectation 与 z 分母的每一项只用 **r 之前**可得
  的 vintage/filing（`shift(1)` before every `rolling` + `merge_asof(allow_exact_matches=False)`）。
  earnings-surprise 的 EPS_{q-4} 取「filed ≤ t」的那版（含可能的修订版，同 `fundamentals.py` 纪律）。

---

## 3. 数据（全部 PIT-safe 在栈内；**无新第三方历史数据**）

- **macro-surprise**：ALFRED `CPIAUCSL`/`PAYEMS` as-of vintage（`features/macro_surprise.py`）。已落地、
  已缓存（`data/cache/alfred_*.json`，sha256-pinnable）。
- **VIX-surprise**：FRED/ALFRED `VIXCLS`（`ingest/vix.py`，`fetch_vix`+`vix_as_of` 已落地）+ 新转换
  `features/vix_surprise.py`（并行在建）。G1/G2/G3 全过（vintage 不可回改）。
- **earnings-surprise**：EDGAR XBRL `net_income` + `shares_out`（**已在 `fundamentals.py:METRIC_TAGS`**，
  PIT via filed-date）+ 新转换 `features/earnings_surprise.py`（并行在建）。**不引入新数据源**——只对
  已有 PIT 基本面做派生。
- **基本面 + 价格 + universe**：Phase B 冻结产物（config_sig `17245a75…`：fund/prices/membership
  sha256 已入 ledger），原样复用。
- **Reddit（未来）**：`PRAW`(BSD) + `FinBERT`(Apache)，**仅前向采集、到达即快照、不 backfill**。未
  累积足够历史前**不进** freeze；累积后作为 bundle 的第 4 分量并入。
- **过 7 门**（[`data-intake-rubric.md`](data-intake-rubric.md)）：VIX via FRED = G1✓G2✓G3✓；CPI/NFP
  via ALFRED 同；earnings via EDGAR = 每条 fact 带 `filed`，由构造 PIT ✓。**故 Phase C 不引入任何新
  第三方历史数据集**——保持「干净 confirmatory」的关键纪律（§5 机制 ⑤⑦ 仍 open）。

---

## 4. 实验设计（复用 `eval/two_arm.py`；arm 轴 = feature-set；新转换并行在建）

- **复用，不新写训练基础设施**：
  - `two_arm.compute_shared_folds`（折 + `(date,ticker)` 行布局，由空-fundamentals panel 算出 →
    **加 bundle 列不改行布局**，折索引跨臂对齐）。
  - `two_arm.run_arm_oos`（断言 arm 行布局 == `ref_layout`，使两臂在同一组折上评估）。
  - `rank_ic.rank_ic_monthly` + `rank_ic_summary`（Spearman 月 IC + Newey-West HAC）。
- **两臂（Phase C 轴 = feature-set，非 Phase B 的 align_on 轴）**：
  - `arm_base` = Phase B 冻结 feature_cols（`mktcap/pb_ratio/roa + 6 fund_*`），`align_on="end_lag"`，
    `macro=None`。**即 Phase B arm_base**（mean_ic 0.0153）。
  - `arm_macro` = Phase B feature_cols **+ bundle**：`{macro_cpi_surprise, macro_nfp_surprise,
    vix_surprise}`（日期广播，走 `macro=`）+ `earnings_surprise`（per-(ticker,date) 对齐，作派生
    fundamental 列）。`align_on="end_lag"`（同 arm_base 时点）。Reddit 分量待累积后加入。
  - 两臂**唯一差** = bundle 列 → differential 干净隔离世界状态惊喜的贡献。
- **隔离诚实注**：Phase B 的 align_on 轴在 `run_two_arm_oos` 内写死（`_ARMS` dict）；Phase C 的
  feature-set 轴需**调用 `run_arm_oos` 两次**（各传不同 `macro`/feature_cols），共享
  `compute_shared_folds` 产出的折——**编排复用**，非改其语义。
- **新转换模块（并行在建，非本预注册范围）**：`features/vix_surprise.py`（Δ或 AR-residual）、
  `features/earnings_surprise.py`（EPS 季节性随机游走惊喜）。两者各配 hermetic PIT 测试（§5 #4）。
- **frozen LightGBM**（同 Phase B `config_sig` params，一字未改）：n_estimators=500, lr=0.05,
  num_leaves=31, min_child_samples=20, reg_lambda=1.0, feature_fraction=0.8, bagging_fraction=0.8,
  bagging_freq=1, **n_jobs=1, random_state=0**（+ bagging/feature/drop seed=0）。
- **CV**：`PurgedGroupKFold`，n_splits=5, embargo=21 sessions（=h），group=date-month（同 Phase B）。
- **primary 指标**：OOS 月 rank-IC 差，配 MBB-DM + Newey-West HAC。**secondary（exploratory）**：
  top–bottom 分位 Sharpe、IC-IR、turnover、leave-one-out 归因（§5）。

---

## 5. 控制门（必须全过）

1. **`arm_base` 即主控制**：Phase B arm_base 是 claim 的补集——bundle 增量 = 相对它的 IC 差。
2. **bundle-shuffle placebo（核心）**：同时打破 bundle 全部分量的对齐——macro/VIX-surprise **跨日期**
   打乱值（保发布时点结构、乱「日期→值」），earnings-surprise **跨 ticker 在披露期内**打乱值（保
   时点、乱「公司→值」）→ differential 必须消失。证信号来自**真实的世界状态对齐**，非任意扰动。
3. **「已知定价」sanity（校准锚）**：一个广为人知、已定价的因子（如 FF5 `Mkt-RF`）作日期广播特征
   拼进同一 arm，**应**显示**有限**增量 IC → 校准「本测试能检出已定价→无增量」，故 bundle null 与
   有效定价一致、非测试失能。校准/正控，非主 claim。
4. **joined-panel PIT 测试（新增 hermetic，冻结前先写）**：合成 panel + `label_start` 之后才发布/披露
   的惊喜/EPS → 断言不进 `t<label_start` 的特征（覆盖 §2 的事件→日期广播胶水 + EPS_{q-4} 取 filed≤t）。
5. **leave-one-out 归因（exploratory，**非 gate**）**：依次去掉 bundle 中一个分量，看 differential 跌
   幅——**仅归因报告**，不作 3 个孤立 claim（否则 inflate §6 的 N）。
6. **memorization audit**：不适用（数值 ALFRED/EDGAR，非 LLM 抽取——同 Phase B；Reddit 接入后另配
   pre/post-cutoff audit）。

---

## 6. 多重检验审计（第 2 条 confirmatory；**联合 bundle → N 仍 = 2**）

- **联合 bundle = 1 个 confirmatory claim**（Phase B 是第 1 条）→ Sharpe-based DSR/haircut 的 N = 所
  有跑过的 feature-set/config（含 Phase B + Phase C + 丢弃）≥ **2**。逐变量若被当 3 个孤立 claim
  会把 N 抬到 ≥4——**这正是选联合 bundle 的多重检验纪律理由之一**。
- Phase B ledger 已记 `n_trials_grid=[1,5,20]`、haircut=Infinity（IC-based、非 strategy-return）。Phase C
  沿用：headline = rank-IC 差（非 Sharpe）；DSR/PBO/SPA 仍是未来 strategy-return 评估的 wiring
  （`eval.multiple_testing` 已备）。
- **Hansen SPA / MCS**：在 config 集（arm_base / arm_macro / placebo / sanity / leave-one-out）上报告
  「是否有 arm beat baseline」+ arm_macro 是否存活。
- **报告规则**：每个 IC 差带 **DM-p + HAC-t + 存活指示**三联；Phase B 的 null 一并计入家族。

---

## 7. Power（条件化于 realized σ(IC)，沿用 Phase B C4）

- OOS ≈ **125 月**（Phase B 实测 n=125；同 universe → 同 n 量级）。
- **可发表性门**：differential 的 **95% CI 半宽 < 0.015**（≈ realized σ(IC差) < 0.061）才算「紧到能
  发表 null」。Phase B 单臂 ci_half ≈ 0.015–0.016（贴边）→ Phase C 报 differential 自身的 HAC SE。
- bundle 加 3 列 → 自由度略升、过拟合风险略升 → 由 embargo + purged CV + frozen params + §5 placebo
  共同护栏。粗估：σ(IC)=0.06 → 可探测月 IC 差 ≈ 0.016；σ(IC)=0.10 → ≈ 0.027（不够紧 → 报
  inconclusive）。诚实写在结果里，不先验钉 MDE。

---

## 8. 冻结清单（**DEFERRED — run deferred pending data readiness**）

### 8.0 冻结决策（**v0.1 DRAFT，未冻结；freeze 显式 DEFERRED**）

> **冻结/首跑前置条件（全部满足才 freeze）**：
> 1. `features/vix_surprise.py` 建成 + hermetic PIT 测试通过（ΔVIX 或 AR-residual 二选一定型）。
> 2. `features/earnings_surprise.py` 建成 + hermetic PIT 测试通过（EPS_{q-4} 季节性随机游走 + z 窗钉死）。
> 3. （可选）Reddit 前向采集累积足够历史（否则 bundle 暂为 3 分量，Reddit 作未来增强）。
> 4. §5 控制门全就绪 + joined-panel PIT 测试（#4）先写。
> 任一项改 → 进 ledger。**outcome pending；run deferred pending data readiness。**

| 项 | 拟冻结值（DRAFT） | 依据 |
|---|---|---|
| **arm_base** | Phase B config_sig `17245a75…` 的 feature_cols + `align_on="end_lag"` + `macro=None` | 即 Phase B arm_base（mean_ic 0.0153）；differential 零点锚 |
| **arm_macro 新增列** | `macro_cpi_surprise`, `macro_nfp_surprise`（日期广播）+ `vix_surprise`（日期广播）+ `earnings_surprise`（per-(ticker,date)） | 框架 ⑤+③+①；全部变化/惊喜、非水平 |
| **VIX-surprise 形式** | ΔVIX 或 AR(p)-residual（二选一，前置条件 1 定型） | Δ 简单 / AR-residual 去 autocorr 更干净 |
| **earnings-surprise 规则** | EPS=net_income/shares_out；期望=EPS_{q-4}（filed≤t）；raw=(act−exp)/\|exp\|；z 窗 PIT | 季节性随机游走 naive benchmark；绕 consensus 付费墙 |
| **惊喜广播规则** | d 日广播值 = `pub_date≤d` 最近一次惊喜；首次发布前 NaN | §2 胶水；PIT 由 §5 #4 守 |
| **CV / h / learner** | PurgedGroupKFold(5, embargo=21, group=month)；h=21；frozen LightGBM（同 Phase B params） | 与 Phase B 同源，保 H6 确定性 |
| **可发表性** | differential 95% CI 半宽 < 0.015 | 同 Phase B C4 |
| **版本钉** | lightgbm 4.7.0 / purgedcv 0.1.2 / arch 8.0.0（同 Phase B）+ pandas-datareader / requests | H6 确定性 + 可复现 |

- [ ] **#1 joined-panel PIT 测试（§5 #4）**：合成 panel + 晚发布惊喜/晚披露 EPS → 断言不泄漏。
- [ ] `features/vix_surprise.py` 建成 + 测试 + 形式定型。
- [ ] `features/earnings_surprise.py` 建成 + 测试 + z 窗钉死。
- [ ] （可选）Reddit 前向采集 + 到达即快照机制。
- [ ] arm_macro feature_cols = Phase B feature_cols + bundle 列（钉列名 + 顺序）。
- [ ] 控制门（§5）+ 多重检验 N=2（§6）+ primary = rank-IC 差（双尾）+ MBB-DM/HAC。
- [ ] **Phase-C 确定性测试（H6）**：两次 panel-build + rank-IC → bit-identical。
- [ ] 可发表性阈值：differential ci_half < 0.015。

> **outcome pending；run deferred pending data readiness。** 本表冻结时尚未观测任何 Phase C OOS
> rank-IC 结果。sha256 先于结果入 ledger。

---

## 9. 运行 / 账本规则（durable registry，非一次性）

- **抗泄漏锚点**：§8 冻结 config 的 sha256 必须在**首次** `arm_macro` vs `arm_base` OOS rank-IC 差
  被观测**之前**写入 `runs/ledger.jsonl`（标 `phase:"C"`, `event:"config_committed"`）。
- **首次 confirmatory run**：§8 前置条件全满足 + §5 全控制门就绪后，首次跑出 OOS rank-IC 差 → 记入
  ledger（标 `confirmatory: first`, `phase:"C"`）。Phase C headline 的唯一来源。
- **双尾判读**：正 = bundle 横截面定价未吸收；负 = 新增列压低 OOS IC（过拟合）；CI 跨 0 = null
  （CI 紧则可发表）。
- **重跑政策（durable）**：
  - **同 sha256 重跑** = 预期行为（H6 确定性，Phase B 已证 bit-identical）；入 ledger（标
    `rerun: reproducibility`），**不替换 headline**。
  - **改 config 后跑** = 合法迭代，**必须**新 ledger 行（新 sha256，标 `exploratory`/新
    `confirmatory`），**不得静默覆盖**。
  - **headline 不可被「重跑到显著」挽救**：改 config 追逐显著性 = 新探索性条目，计入 §6 N。
- **探索性跑**（调参 / 新转换 / Reddit 前向 / leave-one-out）**无限免费**，只要不冒充 confirmatory。

---

## 10. 开放风险（诚实承认）

1. **统计期望 ≠ survey 共识**：macro 惊喜用 trailing-mean、earnings 惊喜用季节性随机游走——都是付费
   墙的 PIT-safe fallback，信号比真共识更噪，**削弱**对 null 的检验力；正向 null 可能部分来自「惊喜
   测得不准」而非「已定价」。缓解：§5 #3 sanity 锚 + 未来若得 consensus 可换。
2. **~~VIX 水平已定价~~ → 已改 VIX-surprise**：本 pivot 的核心修正（见顶部 rationale）。残余风险：
   ΔVIX 含可预测漂移 → 倾向 AR-residual；freeze 选一（前置条件 1）。
3. **bundle 自由度**：3+ 分量联合 → 过拟合空间大于单变量；由 embargo + purged CV + frozen params +
   §5 placebo 共同护栏；leave-one-out 归因（§5 #5）暴露主导分量。
4. **广播前向承载是表示选择**：惊喜跨 session 承载至下次发布——承载窗口设错（太长→stale、太短→
   丢信号）differential 会摇摆。§8 钉死承载规则 + §5 #4 测试守 PIT。
5. **FOMC 无惊喜**：⑤ 经 `macro_surprise.py` 只覆盖 CPI/NFP；FOMC rate-decision surprise 留未来。
6. **幸存者 + 可解析窗**：同 Phase B —— 2016+ 588 clean tickers，headline = 保守上界（不可根除）。
7. **基线已是 null**：Phase B arm_base mean_ic≈0.0153 贴近 0；bundle 增量若也 ≈0，differential 在两个
   小数上比、对 SE 敏感 → §7 的 ci_half 门是诚实护栏，不是形式。
