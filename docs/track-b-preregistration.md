# Track B 预注册 — 七主题选股平台（chronological walk-forward）

> **状态：FROZEN — config_committed 2026-08-02（owner 裁断 5 KEEP）**
>
> **config_sig**：`7a13579eb0ad4db0d5d04489bd8bc6eb7c36b74b0157ea302b2d5449cb708436`（`runs/ledger.jsonl` 行 #40, phase=track_b）。
> **owner 冻结决议**：5 点全 KEEP — SESOI ±0.010 / horizon h=21 / bin_count 5 / 新闻情绪=S3 ablation / universe 2016+（S0-S① 实测 min Jaccard 0.8544 已确认）。
> **feature_cols 修订**：S0-S② 构造后，精确特征列作为 config 修订（新 ledger 行）冻结于首次模型拟合前；无 outcome-based 选择。
> **约束**：config_committed 已先于任何 OOS 结果；此后可跑 S0 数据构造（不写新 ledger、不观察 rank-IC）。
>
> **修订历史**：v0.1 PROPOSED · 2026-08-02 · 初稿 → v1.0 FROZEN · 2026-08-02 · config_committed（sig 7a1357…08436）

---

## 0. 与 B/C/D/E1 的关系（新预注册线，绝不污染历史）

Track B 是**全新的预注册线**，与现有 B/C/D/E1 冻结面完全隔离：

- **新 config = 新 ledger row**：任何配置变更都产生新的 ledger 行，绝不静默覆盖历史（ADR-006 durable-registry 原则）。
- **不重写历史**：B/C/D/E1 的 ledger 行保留不变；其 CV-proxy 分类（RESULTS.md §0）不影响 Track B 的 chronological OOS 身份。
- **null-favored**：前沿共识（Profit Mirage / Alpha Illusion / Lopez-Lira 2025）+ 战略复盘（`2026-08-02-strategic-review-coverage-and-alignment.md`）强烈警告：**LLM-trading alpha 多为泄漏 artifact**。null 是下注热门。
- **chronological walk-forward**：B/C/D/E1 的教训（RESULTS.md §5：shared-fold CV-proxy 可能泄漏）→ Track B 明确使用 **chronological walk-forward**（`purged_walk_forward_splits`），而非 shared-fold CV-proxy。

---

## 1. 单一可证伪 claim（两尾、预注册、null-favored）

> 把七大主题特征（行情/宏观/基本面/新闻情绪/风险/回测/市场结构）统一打分后的 top-quantile 组合，在 **chronological walk-forward** 月频横截面 rank-IC 上，**是否显著优于** price-only S1 baseline？
>
> - **null = betting favorite**：月频已定价 / 因子 alpha 为泄漏 artifact / 组合收益被交易成本侵蚀 → null 预期成立且可发表。
> - **双尾判读**：正 = 七主题增量有效；负 = 七主题反而更差（过拟合/噪声占主导）；CI 跨 0 = null（CI 紧则可发表）。
> - **等价门（J-T）**：复用 ADR-010 的 Jennison-Turnbull 群序贯等价构造——当 RCIₖ ⊂ [−SESOI,+SESOI] 时裁定等价（SESOI = ±0.010）。**等价 ≠ 市场有效**，只 = "此 bundle 在此实现下未达 SESOI"。

---

## 2. Universe（PIT S&P 500，2016+ 可复现窗口）

- **主源**：`hanshof/sp500_constituents`（MIT，日频 1996+）—— PIT 成分，按 `constituents_on(date)` 查询。
- **交叉校验**：`pierrebrunelle/sp500-historical-constituents`（MIT，月频 2016+）—— 可复现窗口。
- **分歧规则**（同 Phase B 预注册规则）：2016+ 月度 Jaccard < 0.95 → headline 限 2016+；1996–2016 只作敏感性。**S0-S① 实测（2026-08-02，已由编排者独立复跑核验）**：min Jaccard **0.8544** @ 2016-01-01、mean 0.9272、106 月中 71 月 < 0.95 → headline 自动限 2016+（verdict: agreement=False）。见 [`reports/audits/track-b-universe-audit.md`](../reports/audits/track-b-universe-audit.md)。
- **幸存者偏差**：经 hanshof PIT 成分缓解，**不可根除**（无免费 Russell/退市 PIT 数据）。headline = 保守上界（v0.2 §8.4 措辞保留）。
- **可复现性**：2016+ 窗口可用 pierrebrunelle 交叉验证；1996–2016 部分依赖 hanshof 历史来源（透明度声明）。

---

## 3. Features（七大主题映射）

| 主题 | 数据源 | PIT 安全性 | 实现模块 |
|------|--------|-----------|----------|
| **① 行情/价格** | Tiingo（主）→ Alpaca（备） | adjClose 已复权；退市价缺失（结构性） | `ingest/market.py:fetch_prices` |
| **② 宏观** | ALFRED vintage（FRED） | as-of 纪律；macro 会修订 → 必须 vintage | `features/macro_surprise.py` |
| **③ 基本面** | SEC EDGAR XBRL（`edgartools`） | filed-date PIT by construction | `ingest/fundamentals.py` |
| **④ 新闻情绪** | E3 闭集 13D/8-K LLM 抽取 + FinGPT embedding | 只受控 ablation；不作主 alpha；LlamaIndex/PromptSha1 sha256 缓存 | `extraction/providers.py`（GLM 池） |
| **⑤ 风险** | `alphalens-reloaded` + `pyfolio-reloaded` | tearsheet/IC/drawdown；`prices` 不含当日因子值 | `track_b/alphalens_adapter.py`（见 wheel-mount-design-pack §1） |
| **⑥ 回测净成本** | `FINSABER`（Apache-2.0，KDD 2026） | next-open 执行；slippage/liquidity/LLM-cost | `track_b/finsaber_adapter.py`（见 wheel-mount-design-pack §2） |
| **⑦ 市场结构** | FF5（Kenneth-French）+ Amihud 流动性 | FF 无 vintage（声明潜在轻微泄漏）；Amihud PIT 窗口 | `track_b/ff5_residual.py`（见 wheel-mount-design-pack §3） |

**主题④ 新闻情绪的特殊处理**（见 `2026-08-02-track-b-s0-s1-slice-plan.md` §4）：
- **不作主 alpha**：只作为 S3 的增量检验，不进 S0/S1。
- **受控 ablation**：通过 neutral-text / shuffled-date 控制门验证提升是否消失。
- **E3 闭集抽取**：仅限有 filing-date PIT 的事件类型（13D/8-K）；PiT 记忆审计。

---

## 4. Learner（LightGBM frozen + lambdarank）

- **LightGBM frozen**（同全家族，一字未改）：
  - `n_jobs=1, random_state=0`（H6 确定性；bit-identical 重跑）。
  - 版本钉死（`pyproject.toml`）。
  - 超参冻结（Phase B §8）：n_estimators=500, lr=0.05, num_leaves=31, min_child_samples=20, reg_lambda=1.0, feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1。
- **rank objective = lambdarank**（RD-15，`eval/ranking_contract.py`）：
  - `objective="lambdarank"`（取代 MSE）。
  - `bin_count=5`（quintiles 分档）。
  - rank-aware 损失，更适合 top-quantile 组合优化。

---

## 5. Validation（chronological walk-forward，非 shared-fold CV-proxy）

> **明确声明**：Track B 使用 **chronological walk-forward**，**不是** B/C/D/E1 的 shared-fold CV-proxy。

### 5.1 切分方法

- **函数**：`eval/cv.py:purged_walk_forward_splits(expanding=True, min_train_months=60, embargo=21)`
- **断言**：`assert_chronological_split(split, pt, et)` 确保 `max(train) < min(test)`（chronological oracle，RD-03）。
- **expanding window**：训练窗随时间扩展（不固定宽度）。
- **min_train_months=60**：最少 5 年训练数据（2016+ 窗口下约 60 月）。
- **embargo=21 sessions**：与 h=21 一致，防标签泄漏。

### 5.2 与 B/C/D/E1 的区别

| 维度 | B/C/D/E1 | Track B |
|------|----------|---------|
| CV 方法 | `PurgedGroupKFold(5, shared folds)` | `purged_walk_forward_splits(expanding)` |
| 训练/测试时序 | 候选训练补集可含测试块之后月份 | **严格 train < test**（chronological） |
| 身份 | CV-proxy / purged cross-fitted | **chronological OOS** |
| 泄漏风险 | 折间样本泄露（已认明） | 最小（时序严格） |

---

## 6. Horizon（h=21 confirmatory；h=10/42 exploratory）

- **h=21 sessions**（≈1 月）— **confirmatory**，计入预注册 claim。
- **h=10 / h=42** — **exploratory sensitivity**，**不计入** confirmatory verdict。
- **h 选择的依据**：21 sessions ≈ 月频 rebalance 周期（同全家族）。

---

## 7. SESOI / 等价门（复用 ADR-010 Jennison-Turnbull）

> **复用 Phase E3 的统计门**（ADR-010，2026-08-01 修订版）——Jennison-Turnbull 群序贯等价构造。

### 7.1 参数（冻结值）

| 参数 | 冻结值 | 依据 |
|------|--------|------|
| **SESOI** | ±0.010（rank-IC 半宽） | ADR-010：经济等价门槛（交易成本后） |
| **Looks** | nₖ ∈ {60, 90, 120} 月 | O'Brien-Fleming 边界（早期保守） |
| **RCI level** | 99.44% (Look1) / 97.64% (Look2) / 95.00% (Look3) | zₖ = z_α/√Iₖ (z_α=1.960, Iₖ=nₖ/120) |
| **zₖ** | (2.772, 2.263, 1.960) | OBF spending |
| **n_trials** | 30 | DSR / Hansen-SPA / Hansen-MCS deflation |
| **HAC SE** | Newey-West | 月频 IC 自相关 |
| **strict-containment** | RCIₖ ⊂ [−0.010, +0.010] → 等价 | 等价裁决条件 |

### 7.2 等价裁决

- **宣布 EQUIVALENCE** 当且仅当 RCIₖ ⊂ [−SESOI, +SESOI]
  （即 μ̂ − zₖσ̂ > −0.010 **且** μ̂ + zₖσ̂ < +0.010）。
- **Type I error 控制**：P(declare equivalence at or before look K \| |μ| ≥ SESOI) ≤ 0.05（OBF 群序贯）。
- **optional stopping**：即使提前停止，Type I 仍 ≤ 0.05（Jennison & Turnbull 2000）。

### 7.3 与非等价的区别

- **非等价 ≠ 市场有效**：只 = "此 bundle 在此实现下未达 SESOI"。
- **旧 B/C/D/E1 ledger 不改写**：只更新语言（CV-proxy），不重跑数值。

---

## 8. Multiplicity（trial registry + DSR/PBO + haircut）

- **trial registry = 30**（RD-17，`eval/multiple_testing.py`）：
  - 包含：所有探索性 config / horizon sweep / placebo / sensitivity / provider / schema 变体。
  - 任何改 config = n_trials +1。
- **DSR**（Deflated Sharpe Ratio，`purgedcv`）：喂**全部试过**的 Sharpe（含丢弃）。
- **PBO**（Probability of Backtest Overfitting，`purgedcv CPCV`）：报告 path 分布。
- **Hansen-SPA / Hansen-MCS**（`arch.bootstrap`）：检验 config 集存活。
- **Harvey-Liu haircut**：兜底 horizon × spec（`YannickKae/Evaluating-Investment-Strategies` CC0 端口）。

---

## 9. Baseline（price-only S1 — "要 beat 的数"）

- **price-only S1**：momentum/reversal/volatility/liquidity 特征（`features/price_features.py`）。
- **等权 baseline**：PIT universe 等权组合 → forward_return 序列（复用 `strategy_returns.long_short_returns`）。
- **DM 检验对象**：**组合收益损失**（loss），**非 rank-IC**（H-1 复审 2026-08-02 已纠正）。
  - `loss(price-only 组合收益) - loss(等权组合收益)`
  - cluster-robust SE（按 month 分组）。
  - HLN 小样本修正应用。

---

## 10. frozen config（关键节：config_committed BEFORE result）

### 10.1 冻结 config 键

| 键 | 冻结值（PROPOSED） | 依据 |
|---|-------------------|------|
| **universe_source** | S&P 500 PIT（hanshof 主 + pierrebrunelle 校验） | §2 |
| **feature_cols** | 七主题特征列（见 S0/S1 实施后清单） | §3 |
| **learner_objective** | `lambdarank`（RD-15） | §4 |
| **learner_params** | LightGBM frozen（同 Phase B §8） | §4 |
| **validation_method** | `chronological_walk_forward` | §5 |
| **min_train_months** | 60 | §5 |
| **horizon** | 21（confirmatory） | §6 |
| **embargo** | 21 sessions | §5 |
| **sesoi** | 0.010 | §7 |
| **looks** | (60, 90, 120) | §7 |
| **n_trials** | 30 | §8 |
| **bin_count** | 5（quintiles） | §4 |

### 10.2 config_committed BEFORE result 机制

- **复用** `reporting.save_run.commit_config`（同 Phase B §9）。
- **sha256 先写 ledger**：frozen config 的 sha256 必须在**首次** OOS rank-IC 结果被观测**之前**写入 `runs/ledger.jsonl`。
- **H6 bit-identical**：同 config 重跑 = 预期行为（bit-identical 输出）。
- **改 config = 新 ledger 行**：绝不静默覆盖历史（durable-registry）。

---

## 11. 显式 non-goals

- **不做日内/衍生品/加密**：只月频横截面选股（S&P 500 PIT）。
- **不做 learned world model**：判别式 LightGBM + structural-only LLM 抽取（E3），非生成式模型。
- **新闻情绪不作主 alpha**：只受控 ablation（S3），不作 S0/S1 主特征（§3.4）。
- **不外推到完整 S&P 500**：无免费 Russell/退市 PIT 数据 → 结果是保守上界。
- **不宣称可交易性**：净成本（FINSABER）是 exploratory 次级透镜；不构成投资建议。

---

## 12. owner-decision 点（flagged，待冻结前裁断）

1. **SESOI 是否沿用 ±0.010**？— ADR-010 的经济门槛；若需调整 → 新 ADR。
2. **horizon 是否钉 h=21**？— h=10/42 已声明 exploratory；confirmatory 需钉单一值。
3. **bin_count quintiles(5)** — RD-15 已选；owner 最终确认？
4. **新闻情绪是否进 S3**？— 还是留作 exploratory ablation？
5. **universe 分歧阈值** — S0-S① 实测 min Jaccard **0.8544 < 0.95**（@2016-01-01，已独立复跑核验）→ 已触发 2016+ 限制规则。owner 确认接受？

---

## 13. 不越界声明（FROZEN 状态，2026-08-02）

- `[F]` **config_committed 已入 ledger**（行 #40, sig `7a1357…08436`），先于任何 OOS 结果。
- `[F]` 冻结后允许：S0 数据构造（不写新 ledger、不观察 rank-IC/收益）。
- `[F]` 首次模型拟合前需 feature_cols 修订行（新 ledger row）。
- `[F]` 本文档 FROZEN 前未运行 confirmatory/strategy/forward 脚本、未观察任何 outcome。
- `[F]` Track B 的任何落地都是**新预注册 + 新 config + 新 ledger row**，绝不静默修改 B/C/D/E1。
- `[F]` "可缓解不可根除"的幸存者偏差（无免费 Russell/退市 PIT 数据）依然成立（v0.2 §8.4）。

---

## 14. 引用

### 内部来源
- [`phase-b-preregistration.md`](phase-b-preregistration.md) — 预注册文体范式（durable registry）。
- [`phase-e3-preregistration.md`](phase-e3-preregistration.md) — 预注册文体范式（forward commitment）。
- [`ADR-010-sesoi-tost-sequential-gate.md`](../decisions/ADR-010-sesoi-tost-sequential-gate.md) — Jennison-Turnbull 群序贯等价门。
- [`2026-08-02-track-b-s0-s1-slice-plan.md`](../reports/design/2026-08-02-track-b-s0-s1-slice-plan.md) — S0/S1 切片结构（七主题映射）。
- [`2026-08-02-strategic-review-coverage-and-alignment.md`](../reports/2026-08-02-strategic-review-coverage-and-alignment.md) — 为何 Track B、null-favored。
- [`RESULTS.md`](RESULTS.md) — B/C/D/E1 的 CV-proxy 教训（Track B 必须用 chronological）。
- [`2026-08-02-wheel-mount-design-pack.md`](../reports/design/2026-08-02-wheel-mount-design-pack.md) — 七主题 OSS 轮子映射。
- [`2026-08-02-reuse-catalog-v2.md`](../reports/design/2026-08-02-reuse-catalog-v2.md) — OSS 许可证 + 泄漏 gotcha。

### 外部（OSS 轮子）
- `eslazarev/purgedcv`（MIT）— PurgedGroupKFold / DSR / PBO。
- `waylonli/FINSABER`（Apache-2.0，KDD 2026）— 净成本回测。
- `alphalens-reloaded` + `pyfolio-reloaded`（Apache）— IC/tearsheet。
- `stefan-jansen/machine-learning-for-trading`（MIT）— `ml4t-diagnostic` 诊断库。
- `microsoft/qlib`（MIT）— 选股脚手架候选。
- `statsmodels`（BSD）— OLS + HAC；`arch`（BSD）— SPA/MCS。
- `pandas-datareader`（BSD）— FRED/ALFRED / Kenneth-French FF5。

---

**文档结束**
