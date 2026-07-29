# Aionis 结果快照（RESULTS）— 可证伪结果的事实摘要

> 状态：**v0.1 · 2026-07-29 · 事实快照（factual snapshot）**。
> 本文件**只**汇总已入 `runs/ledger.jsonl` 的可证伪结果。每个数字都可追溯到 ledger 行 +
> `runs/results/<config_sig>/` 下的 parquet/JSON 产物。**无任何数字为臆测或估算。**
> 与 [`phase-b`](phase-b-preregistration.md) / [`phase-c`](phase-c-preregistration.md) /
> [`phase-d`](phase-d-preregistration.md) 预注册同源——预注册说「要测什么」，本文件说「数据说了什么」。

---

## 0. 这是什么（framing）

**Aionis** 是一个 anti-leakage（反泄漏）、可证伪的量化金融研究项目。它不构建「金融世界模型」，
而是用一串**预注册、双尾、以 null 为押注热门**的可证伪 claim，逐条检验「结构化世界状态观测能否
在月频横截面选股上击败有效市场先验」。

- **理论框架 = TCR**（[`theory-of-computable-reality.md`](theory-of-computable-reality.md)）：世界是
  latent state $S_t$；我们只观测其含噪投影 $o_t^{(k)}\sim g_k(S_t,b_k)$；单点可证伪锚 =
  未来收益 $y_{t+h}=h(\hat S_t)+\eta$，用横截面 rank-IC 度量。
- **分阶段路线（A→E）**，每阶段 = **一条** confirmatory claim：
  - **A** = Event（ERL 事件冲击，sector-ETF）→ **pilot**（underpowered）。
  - **B** = Entity/State（基本面 **filed-date vs period-end+lag** 时点）→ **confirmatory #1**。
  - **C** = Event 的「世界状态惊喜 bundle」（CPI/NFP/VIX/earnings surprise）→ **confirmatory #2**。
  - **D** = Relationship（13D 维权持股 + SIC 同业）→ **confirmatory #3**（**NULL SUPPORTED，可发表**）。
  - **E** = （未来）组合/集成。
- **null = betting favorite**（efficient-markets 先验）。CI 跨 0 **不得**宣称正向；只有当 CI **紧到
  半宽 < 0.015** 时，null 才算「可发表」。
- **抗泄漏锚点 = durable registry**：每条 confirmatory config 的 sha256 **先于**首次 OOS 结果入
  `runs/ledger.jsonl`；同 config 重跑免费（H6 确定性），改 config = 新 ledger 行（绝不静默覆盖）。

**一句话结论**：截至 2026-07-29，三条 confirmatory claim（B、C、D）**均判 NULL SUPPORTED 且全部可发表**；
其中 Phase D 的 differential **最紧**（CI 半宽 0.0107 < 0.015 且跨 0，三阶段最小）。策略回报侧
（exploratory）无任何策略在项目族 deflation 下存活。

---

## 1. Confirmatory 结果总表

> 全部 rank-IC 为 Spearman 月度横截面 IC，OOS 窗 = 2016+ 可解析 universe（**n = 125 月**）。
> 两臂共用同一组 `PurgedGroupKFold(5, embargo=21, group=month)` 折 → differential 只来自被隔离的
> 特征集。DM-p = moving-block-bootstrap Diebold-Mariano；HAC = Newey-West(maxlag=4)。

### Phase A — ERL 事件冲击（pilot，underpowered）

> 不是 rank-IC confirmatory claim；保留为 pilot 子结果。预注册 primary = pooled DA-lift（h=1，
> sector-ETF，per learner）。n≈44 事件簇，**数量级欠功率**。

| 指标（ERL / XGBoost，real data） | 值 |
|---|---|
| DA-lift（with-ERL − price-only） | **0.0868** |
| cluster-robust CI | [−0.0083, 0.1798]（**跨 0**） |
| DM-p | 0.1349 |
| Sharpe / DSR / PBO | 2.50 / 0.29 / 0.0765 |
| neutral 控制 DA-lift | 0.0083 |
| shuffled 控制 DA-lift | −0.0331 |
| n（事件簇） | 44 |

**判读**：ERL 名义 DA-lift 为正且高于两个控制臂，但 **CI 跨 0、DM-p=0.13** → 在预注册门槛下
**不显著**。结合 n=44 的欠功率，Phase A 定性为 pilot，不作为 confirmatory headline。后续阶段把
benchmark 从「事件窗 DA-lift」re-anchor 到「横截面月 rank-IC」（数量级提升到 n=125）。

### Phase B / C / D — 横截面 rank-IC confirmatory

| 字段 | **Phase B**（filed-date 时点） | **Phase C**（惊喜 bundle） | **Phase D**（关系 bundle） |
|---|---|---|---|
| config_sig | `17245a75…` | `a7fdb48f…` | `d3158063…` |
| ledger event | `confirmatory:first` | `confirmatory:first` | `confirmatory:first` |
| claim（双尾） | filed-date 臂是否优于 period-end+lag 臂 | 惊喜 bundle 是否优于 fundamentals-only | 13D+SIC 关系 bundle 是否优于 fundamentals-only |
| 处理臂 mean IC | 0.01450（arm_state，filed） | 0.00882（arm_macro，bundle） | 0.01233（arm_rel，关系 bundle） |
| 基线臂 mean IC | 0.01531（arm_base） | 0.01531（arm_base，同 B） | 0.01531（arm_base，同 B/C） |
| sanity 臂 mean IC | — | 0.02087（Mkt-RF，已定价锚） | — |
| **differential**（处理 − 基线） | **−0.00080** | **−0.00649** | **−0.00298** |
| DM-p（MBB） | **0.870** | **0.355** | **0.597** |
| differential CI | （单臂 ci_half 见下） | [−0.01953, 0.00656] | [−0.01371, 0.00775] |
| differential ci_half | —（B 未单列；见注） | **0.01304** | **0.01073** |
| 处理臂 ci_half | 0.01599 | 0.01752 | 0.01734 |
| 基线臂 ci_half | 0.01499 | 0.01499 | 0.01499 |
| **publishable**（ci_half < 0.015） | 单臂贴边；differential CI 见注 | **是**（differential ci_half=0.0130） | **是**（differential ci_half=0.0107，三阶段最紧） |
| H6 deterministic | **true** | **true** | **true** |
| 控制：placebo / shuffle | placebo DM-p=0.080；lag-shift DM-p=0.270 | bundle-shuffle DM-p=0.555；sanity DM-p=0.157 | bundle-shuffle DM-p=0.538 |
| **verdict** | **NULL SUPPORTED** | **NULL SUPPORTED（可发表）** | **NULL SUPPORTED（可发表）** |

**注（Phase B differential CI）**：Phase B 的 ledger 行只单列了各臂 ci_half（0.0150–0.0160，贴边）
与 differential 的 DM-p（0.870），**未**单列 differential 自身的 HAC SE/CI。该 differential CI 在
Phase C 的 ledger schema 中正式化（`se_hac` / `ci_half` / `publishable_ci_half`）。两臂 IC 均为
CV-proxy（5 折，非 forward-OOS），故单臂可发表性门偏乐观——**§1 的 differential 才是 OOS claim**，
在共享折 CV 下有效（见 ledger `notes`）。

**Phase B 判读**：filed-date 时点相对 period-end+lag 的增量 = **−0.0008**（DM-p=0.87，几乎完全重叠
的零线）→「保守 lag 已足够，filed-date 精度无边际」。null 被支持。控制门一致（placebo DM-p=0.080，
lag-shift DM-p=0.270，扰动后增量消失）。

**Phase C 判读**：惊喜 bundle 增量 = **−0.0065**（DM-p=0.355），CI [−0.0195, 0.0066] **跨 0 但紧到
可发表**（ci_half=0.0130 < 0.015）→「世界状态惊喜在月频已被有效定价」，且这次**紧到能发表 null**。
leave-one-out 归因（exploratory，非 gate）：去掉任一单分量（CPI/NFP/VIX/earnings）differential 均不
显著（DM-p 0.33–0.80），无单一主导分量。sanity 锚 Mkt-RF 显示**有限**增量（mean_diff=0.0056，
DM-p=0.157），校准「本测试能检出已定价→无增量」。

**Phase D 判读**：关系 bundle（SIC 同业动量 `peer_mom` + 13D 维权持股事件 `stakes_13d_event`）相对
fundamentals-only 的增量 = **−0.0030**（DM-p=0.597），CI [−0.0137, 0.0078] **跨 0 且为三阶段最紧**
（ci_half=0.0107 < 0.015）→「同业关系与维权持仓信号在月频已被有效定价」。bundle-shuffle placebo
增量 ≈ 0（DM-p=0.538，扰动后增量消失）。leave-one-out 归因（exploratory，非 gate）：去掉 `peer_mom`
增量 +0.0022（DM-p=0.369），去掉 `stakes_13d_event` 增量 −0.0062（DM-p=0.307）——均不显著，无单一
主导分量。13F 机构中心度 / 供应链客户传导按覆盖降为 exploratory leave-one-out（见
[`phase-d-preregistration.md`](phase-d-preregistration.md) §0.5）。

---

## 2. Strategy-return 次级透镜（exploratory，非 confirmatory）

> 次级、探索性。Confirmatory claim 仍是 §1 的 rank-IC differential。L-S 分位组合年化 Sharpe，
> n=125 月，benchmark = `arm_base`。DSR = Deflated Sharpe Ratio；SPA/MCS = Hansen
> Superior Predictive Ability / Model Confidence Set。

| 策略 | 年化 Sharpe | DSR p（n_trials=1） | DSR p（n_trials=20，conservative） |
|---|---|---|---|
| B_arm_state（filed） | 0.42 | 0.106 | 0.743 |
| **arm_base**（benchmark） | 0.62 | 0.029 | 0.504 |
| C_arm_macro（bundle） | 0.24 | 0.236 | 0.881 |
| C_placebo（shuffle） | 0.54 | **0.057** | 0.626 |
| C_sanity（Mkt-RF） | 0.66 | 0.025 | 0.474 |

- **Hansen SPA**（n_models=5, n_obs=125, reps=1000, seed=0）：consistent p = **0.692**，
  lower = 0.504，upper = 0.692。
- **MCS**：5 个模型**全部**纳入置信集（`mcs_included=[0,1,2,3,4]`）——无一显著优于 benchmark。

**判读**：**无任何策略在项目族 deflation 下存活。** 项目诚实的 family 是 ≥10 条试验，故取
n_trials=20 的 conservative 列：所有 p ≥ 0.47。**Placebo 在 n=1 时 p=0.057** 是警示案例
（cautionary tale）——一个**完全打乱对齐**的 placebo 组合在单次检验下几乎摸到 0.05 显著线，
正说明「不做项目族多重检验校正就会被噪声骗」；deflation 后它跌回 0.626。这与 §1 的 rank-IC null
互相印证：月频横截面没有可提取的结构性 alpha。

---

## 3. Anti-leakage 流水线（rigor 来自纪律，非单次仪式）

Aionis 的可信度不靠「单次 unblind」的仪式，而靠**结构性的、可审计的**抗泄漏工程（durable registry）：

- **Config 先于结果入 ledger**：每条 confirmatory config 的 sha256 **必须先于**首次 OOS rank-IC
  结果写入 `runs/ledger.jsonl`（`event:"config_committed"` → `event:"confirmatory:first"`）。
  该 (ts, sha256) 对是**永久证据，永不被消耗**；同 sha256 重跑 = 预期行为，改 config = 新行。
- **PurgedGroupKFold + embargo**：`PurgedKFold`（group=date-month，embargo=21 sessions = h）防止
  标签泄漏到训练折；两臂**共享同一组折**，differential 只来自被隔离的特征集。
- **H6 bit-identical 确定性**：冻结 LightGBM（`n_jobs=1, random_state=0`，bagging/feature/drop
  seed 全 0）+ 版本钉（lightgbm 4.7.0 / purgedcv 0.1.2 / arch 8.0.0）。两次 panel-build + rank-IC
  产出**位级相同**——Phase B/C/D 均实证 `H6_deterministic: true`。
- **数据接入 7 门**（[`data-intake-rubric.md`](data-intake-rubric.md)）：任何第三方数据集进栈前须过
  G1 license / G2 PIT / G3 no-revision / G4 reproducibility / G5 exploratory-only / G6 selection /
  G7 politeness。判定矩阵：**G1+G2 过 + G3 已验证 → confirmatory**；G3 不可证 → 快照冻结 +
  exploratory（如 EPU、VIX-via-FRED）。**Phase B/C/D 均不引入任何新第三方历史数据集**——全部
  SEC EDGAR（filed-date PIT、不可回改）+ ALFRED vintage + FRED。
- **Permissive-license-only**：仅 MIT / Apache-2.0 / BSD / CC0 / CC-BY-4.0（项目自身 MIT）；
  拒绝 Commons-Clause / GPL / AGPL / CC-BY-NC-SA（如 Financial PhraseBank 即因此被排除）。

---

## 4. 诚实的范围限制（scope limits）

1. **幸存者偏差（不可根除）**：OOS universe = 2016+ **588 clean tickers**（pierrebrunelle 705 中
   resolved-SEC-CIK 后确认 588；114 unresolved 为改名/并购，fundamentals 在后继 CIK 下、免费
   ticker→CIK 反查不可达）。hanshof PIT 成分缓解但不根除幸存者 → **headline = 保守上界**
   （[`quant-selection-research.md`](quant-selection-research.md) §8.4）。两臂用**同一** set，
   故 coverage 缩减是 scope 限制、**非**偏差。
2. **策略回报 gross-of-costs**：§2 的 L-S Sharpe **未扣交易成本、未扣 turnover**——扣费后只会更低，
   不改变「无策略存活」的结论。
3. **SIC 是当前快照，非历史 vintage**（Phase D 已知局限）：submissions 顶层 `sic` 是发行人**当前**
   SIC，跨窗改换 SIC 的公司会用其当前（非历史）SIC 分组——轻度分类 lookahead。SIC 对绝大多数发行人
   稳定，实际偏差小；诚实降级「SIC 过 G2 的依据是不修订+稳定，**非**逐日 vintage」。
4. **13D 自报过滤基于 `ciks[]`**（Phase D 已知局限）：`filer≠issuer` 过滤基于 submissions 的
   `ciks[]` 而非 cover-page 受益人，命名第三方实体的托管/信托自报可能残留为假事件；大盘金融股
   实测 subject-side 已全外部，影响低，残差假事件率作为数据质量局限披露（见
   [`phase-d-preregistration.md`](phase-d-preregistration.md) §0.5）。
5. **efts 分页**：13D `recent` 1000-filing 切片仅覆盖 46.5% 到 2016 前，**须 `files[]` 分页**才能拿
   完整历史（分页将 ticker 命中率从 30.3% 提到 34.8%）。
6. **CV-proxy vs forward-OOS**：单臂 IC 是 5 折 CV-proxy（非 forward-OOS），其可发表性门偏乐观；
   §1 的 **differential** 才是有效 OOS claim（共享折 CV 下成立）。

---

## 5. 指向（ledger 行号供审计）

| 结果 | ledger 行 | 产物路径 |
|---|---|---|
| Phase B freeze + config | #20, #21–22（reframe）, #27（`config_committed`） | `runs/results/17245a75…/` |
| Phase B confirmatory:first | #28 | `runs/results/17245a75…/{ic_state,ic_base}.parquet` + `differential.json` |
| universe crosscheck（Jaccard） | #23 | min 0.8544 / mean 0.9272（<0.95 触发，OOS 窗不变） |
| resolvable universe（588 clean） | #25 | 588/705 = 83.4% of pierrebrunelle 2016+ |
| Phase C config_committed | #29 | — |
| Phase C confirmatory:first | #30 | `runs/results/a7fdb48f…/{ic_state,ic_base}.parquet` + `differential.json` |
| Phase D config_committed | #33 | — |
| Phase D confirmatory:first | #34 | `runs/results/d3158063…/{ic_state,ic_base}.parquet` + `differential.json` |
| strategy-return（exploratory） | #31, #32 | DSR grid [1,2,5,20] + SPA + MCS（仅 B/C 策略；无 Phase D 策略行） |

> 本快照随新 confirmatory 结果入 ledger 而更新。
