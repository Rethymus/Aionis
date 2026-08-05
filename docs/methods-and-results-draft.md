# Aionis — 方法学与结果 draft（v0.1，PROPOSED 可发表稿骨架）

> 状态：**v0.1 draft · 2026-08-04 · 业主审阅稿（中文）**。本稿把累积的反泄漏纪律 + 全部 null 证据组织成可发表单元。METHODS 段已完备（= 贡献）；RESULTS 段的 confirmatory 行占位待 owner GO。最终英文版待 owner 定发表语言后转写。
>
> 取代关系：本稿最终将取代 `docs/RESULTS.md`（v0.1 factual snapshot）作为项目的结果叙述；RESULTS.md 在此之前保留为底层 factual 快照。证据数字以 [`runs/ledger.jsonl`](../runs/ledger.jsonl)（权威）+ `runs/track_c_joint_summary.json` 为准；本稿数字经 [`reports/audits/2026-08-04-evidence-integrity-audit.md`](../reports/audits/2026-08-04-evidence-integrity-audit.md)（若 agent 完成）独立核对。

---

## 摘要（draft）

本项目把**反泄漏纪律本身作为研究对象**：在 S&P 500 point-in-time 成分 + A 股 CSI 300 上，以每月横截面 rank-IC 为估计量，预注册、两尾、null-favored 地检验"treatment 是否优于 price-only"。**在所有已跑配置下，未观察到显著正增量**；且其中差分 CI 多跨零。这不是"策略失败"——**null 是预期可发表结果**，且其可信度由 config-before-result / PIT / purged CV / H6 确定性 / J-T 等价门等结构性纪律保证，而非靠事后叙述。

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

**策略收益次级透镜**（gross-of-cost，B/C，n=125）：B_arm_state Sharpe 0.42 / arm_base 0.62 / C_arm_macro 0.24 / C_placebo 0.54；SPA consistent p=0.69，MCS 保留全部。**gross**——无 turnover/滑点/借券/退市/capacity，不可解释为可交易收益。净成本透镜（mount②，bps=5）：net Sharpe ≈0.43 年化，turnover 1.14（非退化）。

**判读**：12 行全部 null（CI 跨零或差分不显著）。在**chronological** 等级（#5-9，最高可发表强度），Track B 与 Track C 联合均 null；条件化 regime 交互 null。**无一条 confirmatory**（#7-9 是 exploratory；#5-6 差分 CI 上界 > SESOI）。结论：**在所试特征/learner/验证下，未发现可靠的正向横截面增量**——这与"双区域月频已定价/因子 alpha 为泄漏 artifact/成本侵蚀"的 null-favored 先验一致。

---

## 5. 待补：首条 confirmatory（Track C GO）

唯一缺口 = 把 #7（Track C 联合 exploratory null）升格为 **confirmatory**：冻结全特征 #46 config（54 列）+ 修订 #48（meso US-only，G3-fail 收窄）+ Q1 group 构造签注（推荐 region-month）→ 写 `config_committed` ledger 行 #48 → 跑 → J-T 等价门作用在交互项 rank-IC 差分序列。**= owner GO**（写 ledger 行 + 观察 confirmatory OOS = 业主动作，我不擅自触发）。

---

## 6. 局限（诚实边界）

- **CV-proxy ≠ chronological OOS**：B/C/D/E1（#1-4）是 shared-fold purged cross-fit，train 补集可含测试块之后月份；purge/embargo 防标签重叠但不等于时序 OOS。Track B/C（#5-9）才是 chronological。
- **exploratory ≠ confirmatory**：#5-9 均 exploratory；无 confirmatory 级结果（待 §5）。
- **欠功率的等价性**：Track B 差分 CI 上界 0.020 > SESOI 0.010 → 不构成严格等价，需更多样本（= 日历时间，E3 forward-live）。
- **幸存者偏差**：PIT 成分缓解，不可根除（无免费退市 PIT）。universe = 2016+ 588/705 可解析 ticker → headline = 保守上界。
- **币种**：D1 区域-月排序消除 label 跨币种污染，但联合 IC 仍是本币收益的区域内排序合成，非汇率中性组合收益。
- **SIC 当前快照**（非 historical vintage）；13D self-report filtering 残余误差；baostock 复权 G3 策略冻结（raw）。
- **非投资建议**：null 不证明市场有效，不证明因子 alpha 严格为零，不构成可交易策略。

---

## 7. 不越界声明

- `[F]` 本 draft 是 PROPOSED 可发表骨架；METHODS 段基于已建完备的反泄漏纪律（ADR-001..012 + preregs + ledger）；RESULTS 数字源自 ledger/artifact（待 evidence-audit 独立核对）。
- `[F]` 未触冻结面/ledger/prereg/ADR；confirmatory 段（§5）占位，= owner GO。
- `[I]` 最终发表语言（中/英）、期刊定位、是否含 E3 forward-live（年级别）待 owner 裁断。
