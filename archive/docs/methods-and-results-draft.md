> Superseded by owner decision (publication track retired) on 2026-08-15.
# Aionis — 方法学与结果 draft（v1.0，可发表稿；首条 confirmatory 已含）

> 状态：**v1.0 · 2026-08-05 · 业主授权选项 A 定稿（中文）**。本稿把累积的反泄漏纪律 + 全部 null 证据 +
> **首条 confirmatory OOS 结果（ledger #49）** 组织成可发表单元。METHODS 段完备（= 贡献）；
> RESULTS §5 confirmatory 已实填（点估计 null + J-T look-1 欠功率 NOT_EQUIVALENT，诚实分级）。
> v1.0-draft → v1.0：业主 2026-08-05 授权"按推荐方式处理"= 选项 A（accept reframing：贡献 = null 点估计 + 反泄漏纪律 + power-limit 披露，**不**拓宽 SESOI、**不**动冻结面）。最终英文版 + 期刊定位仍待业主。
> 独立验证：power-analysis sonnet review APPROVE（0 blocking/HIGH/MEDIUM，3 LOW advisory）+ climax diff review APPROVE（0 CRITICAL/HIGH/MEDIUM/LOW，跨文件一致，"publish as-is"）。
>
> 取代关系：本稿最终将取代 `docs/RESULTS.md`（v0.1 factual snapshot）作为项目的结果叙述；RESULTS.md 在此之前保留为底层 factual 快照。证据数字以 [`runs/ledger.jsonl`](../runs/ledger.jsonl)（权威，含行 #49 confirmatory:first）+ `runs/track_c_confirmatory_summary.json` 为准；本稿数字经 [`reports/audits/2026-08-04-evidence-integrity-audit.md`](../reports/audits/2026-08-04-evidence-integrity-audit.md) + [`reports/audits/2026-08-05-confirmatory-runner-review.md`](../reports/audits/2026-08-05-confirmatory-runner-review.md)（sonnet APPROVE）独立核对。

---

## 摘要（draft）

本项目把**反泄漏纪律本身作为研究对象**：在 S&P 500 point-in-time 成分 + A 股 CSI 300 上，以每月横截面 rank-IC 为估计量，预注册、两尾、null-favored 地检验"treatment 是否优于 price-only"。**在所有已跑配置下（含首条 confirmatory OOS，ledger #49），未观察到显著正增量**；且其中差分 CI 多跨零。这不是"策略失败"——**null 是预期可发表结果**，且其可信度由 config-before-result / PIT / purged CV / H6 确定性 / J-T 等价门等结构性纪律保证，而非靠事后叙述。**首条 confirmatory 的 J-T 门在 look-1 欠功率下拒绝过早宣布等价（即使点估计 null）——这正是该纪律的活体演示。**

---

## 1. 贡献：反泄漏纪律作为研究对象

量化研究的常见失败不是"没找到 alpha"，而是**不可证伪**——结果可被 rerun-to-significance、回填、幸存者偏差、CV 泄漏悄悄改写。Aionis 的贡献是把这些泄漏源**结构性地锁死**，使 null 本身成为可信、可发表的证据：

1. **`config_committed` 先于结果**：冻结 config 的 sha256 必须在**任何** OOS 指标观察之前 append 进 `runs/ledger.jsonl`（append-only）。改 config = 新 ledger 行，绝不静默覆盖。**headline 无法被 rerun-to-significance 救回**。
2. **Point-in-time 全栈**：基本面按 `filed` 日期（非 period-end）；宏观用 ALFRED as-of vintage；VIX 用 no-revision 合同；S&P 500 用 PIT 成分（`constituents_on(t)`，非今日快照）；A 股价格 baostock raw（G3 复权策略冻结）。
3. **Purged 验证 + embargo**：`PurgedGroupKFold(group=month, embargo=21 sessions)`（历史 B/C/D/E1）；Track B/C 用 **chronological walk-forward**（train 严格 < test，expanding，min_train=60）。
4. **H6 确定性**：`n_jobs=1`、所有 seed=0、`uv.lock` 版本钉死；IC 系列 **and** 原始 score 跨重跑 bit-identical（asserted）。
5. **两尾、预注册、null-favored**：每相位一条预注册两尾 claim；SESOI ±0.010；J-T group-sequential 等价门（ADR-010，双 opus 修正：look-specific RCI 99.44/97.64/95.00%，strict-containment）。
6. **多重检验预算 = 1**：Track C 的条件化 = **单个预指定交互项** `score × regime_state`（非 K 个事后子组），结构性绕开"试了 K 个挑最显著的"。

这些纪律是**可审计的**（每条对应 ledger 行 / ADR / 代码 assert），而非叙述。它们不把 CV-proxy 自动变成 chronological OOS，也不替代经济等价检验——边界在 §6 诚实声明。

---

## 2. 估计量族

所有相位共享同一估计量：**每月横截面 rank-IC**（Spearman，模型分数 vs 实现前瞻收益），HAC (Newey-West) 推断。

| 相位/track | 估计量 | 验证 | universe |
|---|---|---|---|
| B/C/D/E1（历史） | treatment − baseline 差分 rank-IC | shared-fold PurgedGroupKFold（**CV-proxy**） | S&P 500 PIT, 2016+, ~588 |
| Track B | treatment(#41) − price-only(#42) 差分 | **chronological walk-forward** | 同上 |
| Track C（本 draft 重点） | 双区域联合 rank-IC × regime_state 交互 | **chronological 联合折叠**（US+CN） | S&P 500 + CSI 300, 2016+ |

Learner：LightGBM（frozen，`objective=lambdarank`，RD-15 ranking contract，bin_count=5，区域内月 quintile 分箱仅 train-fold fit）。

---

## 3. Track C 联合折叠（新贡献的方法学）

双区域联合 chronological walk-forward 是本 draft 的方法学新点（[`reports/design/2026-08-04-track-c-joint-fold-spec.md`](../reports/design/2026-08-04-track-c-joint-fold-spec.md)）：

- **联合面板**：US（NYSE 月末）+ CN（XSHG/XSHE 月末）按各自交易日历月末采样，按日历月对齐到同一时间轴。
- **核心定理**：month-end 采样 + 日历月折边界 ⇒ **per-region 21-session embargo 自动满足**（相邻月末在任何市场 ≈ 21 sessions），故 `cv.py`/`purgedcv` 0 改动。
- **区域-月 group**（D1）：lambdarank query = (region, month)，US 只与 US 排序、CN 只与 CN——**消除跨币种 label 污染**（forward return 是本币收益）。模型仍联合 fit（共享参数）。
- **regime_state 条件化**：三层 PIT 复合（meso US-SIC + macro 5 线 + global Diebold-Yilmaz spillover），TACO as-of σ 归一化（绝不追溯重算）。条件化 = 单预指定交互（multiplicity 预算 1）。

**反泄漏不变量**（code-asserted）：I1 per-region 时序（train.max < test.min 逐区）、I2 train-only binner、I3 regime as-of 月末、I5 region-month group 分离、I6 H6 bit-identical。

---

## 4. 证据表（全部 null；数字以 ledger/artifact 为准）

> ⚠ **诚实分级**：CV-proxy ≠ chronological OOS；exploratory ≠ confirmatory。下表"等级"列是可发表强度的真实上限。

| # | 结果 | 点估计 | 95% CI | p | n（月） | 等级 | ledger/artifact |
|---|---|---:|---|---:|---:|---|---|
| 1 | Phase B 差分 | −0.0008 | [−0.0106, +0.0090] | 0.872 | 125 | CV-proxy（2026-08-05 补 paired HAC CI；ledger #28 未改，append-only） | #28 + 补算 |
| 2 | Phase C 差分 | −0.0065 | [−0.0195, +0.0066] | 0.355 | 125 | CV-proxy | #30 |
| 3 | Phase D 差分 | −0.0030 | [−0.0137, +0.0078] | 0.597 | 125 | CV-proxy | #34 |
| 4 | Phase E1 差分 | −0.0028 | [−0.0115, +0.0059] | 0.533 | 125 | CV-proxy | #37 |
| 5 | Track B treatment(#41) | +0.0055 | [−0.021, +0.033] | 0.689 | 125 | chronological / exploratory | #41 |
| 6 | Track B 差分(#41−#42) | +0.0076 | [−0.004, +0.020] | 0.219 | 125 | chronological / **CI 上界 0.020 > SESOI 0.010 → 非严格等价** | #41/#42 |
| 7 | **Track C 联合 combined IC**（本 session） | **−0.0070** | [−0.030, +0.016] | **0.55** | 71 | chronological 联合 / **exploratory**（10 price 特征） | `track_c_joint_summary.json` |
| 8 | Track C 联合 conditional-IC β | −0.015 | — | 0.20 | 71 | exploratory（无 regime 交互；R²=0.018） | 同上 |
| 9 | Track C 3-layer conditional-IC（combined β） | −0.0148 | — | 0.21 | 71 | chronological 联合 / exploratory；per-region us β=−0.029 (p=0.13) / cn β=+0.004 (p=0.80)（joint-fold IC）。handoff culmination 的 β_US=−0.001/β_CN=+0.015 是 **Track-B-fitter 单区 IC** 的 sensitivity（不同 series，仍 prose） | `track_c_3layer_conditional_ic.json` |
| 10 | BASELINE-FF5 | +0.0106 | ci_half 0.0196 | t=1.06 | 125 | CV-proxy / exploratory | baseline_ff5 |
| 11 | BASELINE-RANK | +0.0154 | ci_half 0.0149 | t=2.03 | 125 | CV-proxy / exploratory（p=0.042，n_trials=30 haircut 会洗掉） | baseline_rank |
| 12 | h=10/42 sensitivity（8 行） | 全跨零 | — | 0.41–0.86 | 124–126 | CV-proxy / exploratory | #39 |
| 13 | Track C 联合 asymmetric35 combined IC（A1 验证，本 session） | −0.0121 | [−0.035, +0.011] | 0.31 | 71 | chronological 联合 / exploratory（US 23 fund+price / CN 12 price+extras = 25 unique 列；US IC −0.002 / CN IC −0.020；**US fundamentals 无 alpha → 坐实 null-favored**） | `track_c_joint_asym35_summary.json` |
| 14 | Track C 联合 asymmetric41 combined IC（confirmatory 彩排） | −0.0088 | [−0.034, +0.016] | 0.48 | 71 | chronological 联合 / exploratory（全 41 特征含 macro 6；bit-identical 于 #15 confirmatory） | `track_c_joint_asym41_summary.json` |
| 15 | **Track C 联合 confirmatory:first（本 session climax）** | **−0.0088** | [−0.034, +0.016] | **0.48** | 71 | **chronological 联合 / CONFIRMATORY**（frozen #48；J-T look-1 NOT_EQUIVALENT：RCI 99.44% [−0.051, +0.027] 宽于 ±0.010 SESOI = 欠功率，**非**效应信号；H6 双跑 bit-identical PASS） | **ledger #49** + `track_c_confirmatory_summary.json` |

**策略收益次级透镜**（gross-of-cost，B/C，n=125）：B_arm_state Sharpe 0.42 / arm_base 0.62 / C_arm_macro 0.24 / C_placebo 0.54；SPA consistent p=0.69，MCS 保留全部。**gross**——无 turnover/滑点/借券/退市/capacity，不可解释为可交易收益。净成本透镜（mount②，bps=5）：net Sharpe ≈0.43 年化，turnover 1.14（非退化）。bps 敏感度（mount② 姐妹脚本 `track_b_net_cost_sweep_run`，exploratory，2026-08-05）：per-period Sharpe 从 gross 0.149（bps=0）线性衰减至 bps=50 时 −0.088；break-even ≈31 bps（turnover 1.14 跨 bps 恒等）→ 即便经济透镜也无稳健可交易 edge。

**判读**：15 行全部 null（CI 跨零或差分不显著）。在 **confirmatory** 等级（#15，最高可发表强度），
首条 confirmatory OOS 点估计 null（−0.0088）；J-T look-1 因 OBF 保守性（99.44% RCI）欠功率，
返回 NOT_EQUIVALENT（= power 声明，非效应信号；look-2/3 需 E3 forward-live 日历时间）。chronological
等级（#5-9, #14）均 null；条件化 regime 交互 null。**结论**：在所试特征/learner/验证下，未发现可靠的正向
横截面增量——这与"双区域月频已定价/因子 alpha 为泄漏 artifact/成本侵蚀"的 null-favored 先验一致。**项目
logical climax 已达**：反泄漏纪律作为研究对象，在首条 confirmatory 上端到端演示（config 先于结果 + H6 真实
数据证明 + J-T 门拒绝过早等价）。

---

## 5. 首条 confirmatory（Track C GO 已执行；ledger #49）

**状态：confirmatory OOS 已跑 + 沉积**（2026-08-05，owner D6 GO；`runs/ledger.jsonl` 行 #49，
`config_sig=e14b9d44...` 引用 frozen #48）。runner `scripts/track_c_confirmatory_run.py`；
H6 双跑 bit-identical 在真实数据上 PASS；J-T 门（`eval/sesoi_gate.py`）作用在 `combined_ic_series`
均值（Reading A：rank-IC 是 gated 估计量；`cond_beta` 仅 explanatory，multiplicity 预算保持 1）。

**结果**（n=71 月，68 折，2016-01..2026-08 双区域月末）：

| 量 | 值 | 判读 |
|---|---:|---|
| combined rank-IC 均值 | **−0.00884** | null（p_hac=0.484，95% HAC CI [−0.034, +0.016] 跨零）|
| US IC / CN IC 均值 | +0.0052 / −0.0265 | 双区均 null（与 asym41 exploratory bit-identical）|
| conditional-IC β（regime 交互）| −0.0076（p=0.43）| null；交互项不显著（multiplicity 预算 1）|
| **J-T look-1 判定**（n=60，RCI 99.44%）| **NOT_EQUIVALENT** | RCI [−0.051, +0.027] 远宽于 ±0.010 SESOI |
| H6 双跑 bit-identical | PASS | 真实数据上确定性验证 |

**诚实判读（关键）**：这是一条 **null 点估计 + 欠功率 look-1** 的结果，**不是"treatment 有效"也非"等价被拒"**：

1. **点估计 null**：combined IC −0.00884 与本 draft §4 全部 14 条 exploratory null 一致（覆盖 CV-proxy、
   chronological 单区/联合、4 个特征族、3 个区域）。confirmatory 等级下，treatment 模型仍未显示可靠正增量。
2. **look-1 NOT_EQUIVALENT 是 power 声明，非效应信号**：OBF look-1 用 z=2.772（RCI 99.44%，极保守）；
   月频 rank-IC 噪声 se≈0.014 → 99.44% RCI 半宽 ≈0.039，**结构性宽于** ±0.010 SESOI。
3. **power analysis 揭示更深层的结构性欠功率**（2026-08-05，`scripts/track_c_power_analysis.py`，
   详见 §6）：prospective 投影显示**look-2 (n=90) 与 look-3 (n=120) 也无法宣布等价** —— 宣布等价需
   n_min = 580 / 435 月（48 / 36 年）。block bootstrap 下 P(equivalence) = 0.0000 at all 3 planned looks。
   **因此 look-1 NOT_EQUIVALENT 不是"look-1 太保守"的局部现象，而是整个 60/90/120 schedule 在 SESOI ±0.010
   下的必然状态**。月频 rank-IC 的噪声地板（σ≈0.10）使 ±0.010 等价宣告在现实样本量下不可达。
4. **门的纪律演示**：即使结构性欠功率，J-T 门仍**拒绝在数据不足时过早宣布等价**（即使点估计 null）。
   这正是"反泄漏纪律作为研究对象"的活体证据——一个可被 rerun-to-significance 或宽 CI 救回的框架会草率宣布
   "null 即等价"；预注册的 J-T 门不会。**结合 power analysis，项目的诚实贡献 = null 点估计 + 反泄漏纪律 +
   power-limit 披露**（而非"等价已宣告"）。

**climax 叙事**：Aionis 完成了首条 confirmatory OOS（config #48 frozen 先于观察，H6 真实数据证明）。
点估计 null，与全部 exploratory 一致。**严格等价判定（look-2/3）需 E3 forward-live 累积日历时间
（look-2 n=90 ≈ 2028，look-3 n=120 ≈ 2031）**。这不是"失败"——null 是预期可发表产物，且门的拒绝过早等价
本身就是方法学贡献的演示。

**独立性局限（披露）**：runner 由 opus orchestrator 直接构建 + 独立 sonnet code-review APPROVE（0 CRITICAL，
estimand Reading A 可辩护，H6 充分，look 截断 Type-I 正确）；J-T 门 + H6 + 沉积的可复现性由 frozen #48 +
`scripts/track_c_confirmatory_run.py` 保证——任何独立方可从 frozen config 重跑验证 bit-identical。
exploratory asym41（2026-08-05 13:48）在 confirmatory 沉积前已观察 IC≈−0.0088；config #48 由 D1-D5 spec
决策选定（machinery readiness + spec faithfulness），**非** IC 优化 → 无 result-peeking 泄漏（H6 保证
confirmatory 重现同一 IC）。

---

## 6. 局限（诚实边界）

- **CV-proxy ≠ chronological OOS**：B/C/D/E1（#1-4）是 shared-fold purged cross-fit，train 补集可含测试块之后月份；purge/embargo 防标签重叠但不等于时序 OOS。Track B/C（#5-9）才是 chronological。
- **exploratory ≠ confirmatory**：#5-9 均 exploratory；无 confirmatory 级结果（待 §5）。
- **欠功率的等价性（已实测，2026-08-05 power analysis）**：Track B 差分 CI 上界 0.020 > SESOI 0.010 →
  不构成严格等价。**Track C confirmatory 的 prospective power analysis**（`scripts/track_c_power_analysis.py`，
  复用 ledger #49 的 combined_ic_series 噪声 σ≈0.106 + lag-1 ρ≈0.07）显示：J-T 60/90/120 look schedule 在
  SESOI ±0.010 下**结构性欠功率** —— 宣布等价所需的最小样本 n_min：look-1 (z=2.772) 869 月(72.5 年)、
  look-2 (z=2.263) 580 月(48.3 年)、look-3 (z=1.960) 435 月(36.2 年)。block bootstrap（2000 次重采样）
  下 P(equivalence) = **0.0000** at all 3 planned looks；look-3 (n=120) 的 RCI half-width 中位数 0.019 > SESOI 0.010。
  **判读**：look-1 NOT_EQUIVALENT 不是"look-1 太保守"的局部现象，而是**整个 60/90/120 schedule 在该 SESOI 下的
  必然状态**。月频 rank-IC 的噪声地板（σ≈0.10）使 ±0.010 等价宣告在现实样本量下不可达。E3 forward-live 即使点火，
  也需 ~36+ 年才能达 look-3 等价判定。**这是诚实的方法学发现**（power floor），非 bug；它把项目贡献从"宣布等价"
  收窄为"null 点估计 + 反泄漏纪律 + power-limit 披露"。**业主 2026-08-05 已选 ①（授权"按推荐方式处理"）**：接受
  reframing，不拓宽 SESOI、不动冻结面。② 拓宽 SESOI ±0.025（post-hoc "moving goalposts" 嫌疑 + 与反泄漏精神相悖，
  不采纳）；③ 延长 look horizon n=435+（36 年不可行，不采纳）。
- **幸存者偏差**：PIT 成分缓解，不可根除（无免费退市 PIT）。universe = 2016+ 588/705 可解析 ticker → headline = 保守上界。
- **币种**：D1 区域-月排序消除 label 跨币种污染，但联合 IC 仍是本币收益的区域内排序合成，非汇率中性组合收益。
- **SIC 当前快照**（非 historical vintage）；13D self-report filtering 残余误差；baostock 复权 G3 策略冻结（raw）。
- **非投资建议**：null 不证明市场有效，不证明因子 alpha 严格为零，不构成可交易策略。

---

## 7. 不越界声明

- `[F]` 本 draft v1.0 含首条 confirmatory OOS 结果（ledger #49，config #48 frozen 先于观察，H6 真实数据 bit-identical PASS）；METHODS 段基于已建完备的反泄漏纪律（ADR-001..012 + preregs + ledger）。
- `[F]` 本轮 sediment 了 1 行 `confirmatory:first`（ledger #49，append-only）；B/C/D/E1 + Track B 冻结面 / prereg / ADR 未改。
- `[I]` 业主 2026-08-05 已授权选项 A（accept reframing）→ 中文 v1.0 据此定稿。仍待业主：最终英文版、期刊/会议定位、是否启动 E3 forward-live（年级别，续作 look-2/3；power analysis 后目的降级为"延续 null OOS 积累"，可选非必需）。
