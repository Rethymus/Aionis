# Track B 首个 OOS 结果快照（chronological walk-forward）

> **状态：v0.1 · 2026-08-02 · Track B 首个 OOS 观察（treatment 臂）**
>
> **绑定 config**：#41（sig `bf620bdf756810d5aab4db639b70856613885ce48e11e6a198884ab4c32ba4f9`）
>
> **validation 方法**：chronological walk-forward（expanding，min_train=60，embargo=21）
>
> **horizon**：h=21 sessions（≈1 月，confirmatory）
>
> **learner**：LightGBM lambdarank（23 预指定特征，frozen）

---

## 0. 结论（诚实，边界明确）

**treatment 臂独立 rank-IC 未显著为正**。在 2021-01 至 2026-06 的 chronological walk-forward 样本下：

- **mean rank-IC**：0.005511（95% HAC CI：-0.021441 至 0.032463）→ **CI 跨零**
- **HAC t 统计量**：0.4007，p = 0.6886 → **无法拒绝 null**
- **DM 检验**（top-quantile 组合 vs 等权组合收益）：dm_stat = -1.7848，dm_p = 0.0790 → **边际但非显著**（p > 0.05）
- **差分（treatment - price-only baseline，预注册 §1 headline）**：mean_diff = 0.007572（95% HAC CI：-0.004492 至 0.019636），p = 0.2186 → **CI 跨零，treatment 未显著优于 price-only**（null，符合 null-favored 预注册）。但 CI 上界 0.0196 > SESOI 0.010 → **不构成严格等价**（差分可能高达 ~0.020，需更多样本才能宣称等价）。

此结论**仅适用于**上述实现、样本和特征集。不证明市场有效、七主题无效已证、或策略可交易。

---

## 1. 适用边界（关键）

### 1.1 这是 **treatment 臂独立 IC**，非完整 claim

- **预注册 claim 是 treatment vs price-only baseline 的差分**（DM 检验应对 price-only 组合，非等权）。
- **price-only 臂（config #42）+ 差分 = 已完成**（2026-08-02）。price-only mean_ic = -0.002062（CI -0.0316..0.0275，p=0.891，null）；差分 0.0076（CI -0.0045..0.0196，p=0.219）→ treatment 未显著优于 price-only。
- 预注册 baseline（price-only S1, #42）已执行：mean_ic -0.0021（null，略负）。

### 1.2 幸存者偏差"可缓解不可根除"

- PIT S&P 500 成分（hanshof 主源 + pierrebrunelle 校验）缓解了幸存者偏差。
- **无免费 Russell 退市 PIT 数据**→ 幸存者偏差不可根除。headline 是**保守上界**。
- 2016+ Jaccard 实测 min 0.8544（@ 2016-01-01），mean 0.9272 → 106 月中 71 月 < 0.95 → 已触发 2016+ 限制规则。

### 1.3 不允许的外推

- 不外推到完整 S&P 500/可交易/无幸存者偏差。
- 不宣称"市场有效"/"七主题无效已证"/"可交易"。
- 可写"在此实现/样本下未观察到显著正 rank-IC"。

---

## 2. 结果表

| 指标 | 值 |
|------|------|
| **mean_ic** | 0.005511 |
| **hac_se** | 0.013751 |
| **ci_95_lower** | -0.021441 |
| **ci_95_upper** | 0.032463 |
| **t_hac** | 0.4007 |
| **p_hac** | 0.6886 |
| **dm_stat** | -1.7848 |
| **dm_p** | 0.0790 |
| **n_walk_folds** | 66 |
| **n_test_obs** | 31266 |
| **ic_series_start** | 2021-01-29 |
| **ic_series_end** | 2026-06 |
| **horizon** | 21 sessions（≈1 月） |
| **min_train_months** | 60 |
| **validation_method** | chronological walk-forward（expanding） |
| **embargo** | 21 sessions |
| **learner_objective** | lambdarank |
| **bin_count** | 5（quintiles） |
| **n_features** | 23（13 基本面 + 10 价格） |

### 2.1 price-only baseline 臂（config #42，10 价格特征）

| 指标 | 值 |
|------|------|
| **mean_ic** | -0.002062 |
| **ci_95** | (-0.031623, 0.027500) |
| **p_hac** | 0.8913 |
| **dm_stat**（vs 等权） | -1.2131 |
| **dm_p** | 0.2296 |
| **n_features** | 10（价格） |
| **ic_series_start** | 2021-01-29 |

### 2.2 差分（treatment #41 − price-only #42，预注册 §1 headline）

| 指标 | 值 |
|------|------|
| **mean_diff** | 0.007572 |
| **hac_se** | 0.006155 |
| **ci_95** | (-0.004492, 0.019636) |
| **t_hac** | 1.2302 |
| **p_hac** | 0.2186 |
| **n_months** | 65 |
| **SESOI 等价裁决** | **未达**（CI 上界 0.0196 > SESOI 0.010；RCI ⊄ [-0.010,+0.010]）|

---

## 3. 方法概要

### 3.1 切分方法

- **函数**：手动 expanding walk-forward（`purged_walk_forward_splits` 仅支持 n_splits、不支持 min_train；故手动构造折：`for month_idx in range(60, n_months)`，train = 所有先前月末行，test = 月末 t，embargo=21 sessions 防标签窗口重叠）
- **chronological oracle**：`assert_chronological_split` 确保 `max(train) < min(test)`
- **expanding window**：训练窗随时间扩展（不固定宽度）
- **IC 系列起点**：2021-01-29（由 min_train=60 强制）

### 3.2 特征集（frozen，23 列）

- **基本面（13 列）**：roa、roe、profit_margin、asset_growth_1m、asset_growth_12m、revenue_growth_1m、revenue_growth_12m、equity_growth_1m、leverage、debt_to_equity、book_value_per_share、accruals、investment_12m
- **价格（10 列）**：momentum_{5,10,21,42}d、reversal_5d、volatility_{21,63}d、turnover_21d、beta_252d、amihud_illiquidity_21d

### 3.3 Learner

- **LightGBM frozen**：n_jobs=1, random_state=0（H6 确定性）
- **objective**：lambdarank（rank-aware）
- **bin_count**：5（quintiles）
- **超参冻结**：n_estimators=500, lr=0.05, num_leaves=31, min_child_samples=20, reg_lambda=1.0, feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1

---

## 4. 与预注册的对应

### 4.1 符合预注册（track-b-preregistration.md）

- **§1 claim**：treatment vs price-only baseline 的差分（price-only 臂 pending）
- **§5 validation**：chronological walk-forward（expanding，min_train=60，embargo=21）
- **§6 horizon**：h=21 sessions（confirmatory）
- **§7 SESOI**：±0.010（等价门，待 price-only 臂完成后评估）
- **§9 baseline**：price-only S1（pending）

### 4.2 尚未完成

- **price-only 臂（config #42）**：已完成（mean_ic -0.0021，null）
- **差分（§1 headline）**：已完成（0.0076，CI -0.0045..0.0196 跨零，p=0.219 → treatment 未显著优于 price-only）
- **SESOI 等价裁决**：**未达**——差分 CI 上界 0.0196 > SESOI 0.010，RCI ⊄ [-0.010,+0.010]；需更多样本才能宣称严格等价
- **DM（treatment 组合 vs price-only 组合）**：仍 pending（当前 DM 是各臂 vs 等权；组合间 DM 需两臂月度组合收益序列）

---

## 5. 引用

- **ledger**：#41（runs/ledger.jsonl）
- **预注册**：docs/track-b-preregistration.md（FROZEN）
- **全局结果**：docs/RESULTS.md（B/C/D/E1 CV-proxy 教训）
- **ADR-010**：decisions/ADR-010-sesoi-tost-sequential-gate.md（Jennison-Turnbull 等价门）

---

**文档结束**
