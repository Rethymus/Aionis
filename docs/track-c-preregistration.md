# Track C 预注册 — 双区域条件化 rank-IC（A 股 + 美股，chronological walk-forward）

> **状态：FROZEN v1.0 · 2026-08-03 · `config_committed` 已入 ledger（行 #46，sig `758ca4d7…`，先于任何 OOS）。**
>
> **config_sig**：`758ca4d739f09331ee4dceb726d9d0d0f7c5110303acc6dcac59919701374fad`（`runs/ledger.jsonl` 行 #46，phase=track_c；sha256 自洽已验）。
> **冻结后允许**：S0 数据构造（不写新 ledger、不观察 rank-IC/收益）；首次 OOS rank-IC 前须有 frozen config（已满足）。
>
> **修订 #47（2026-08-03，sig `252cf7df1df875e7…`）**：A 股 cninfo 基本面 → **exploratory-only**（G1：cninfo 反爬 + 商业数据产品授权 ≠ EDGAR 开放 API；保守处置）；claim 收窄为 **US-rank-IC（确认性）+ A 股 exploratory 条件化**。#46 冻结不变（append-only / durable-registry）。详见 [`ashare-fundamentals-source.md`](../reports/design/2026-08-03-ashare-fundamentals-source.md) §3 G1。
> **owner §12 裁断（2026-08-03）**：① 双区域 = **联合折叠**；② regime = **三层 PIT 复合**（meso+macro+global，等权，TACO as-of）；③ A 股源 = **cninfo**（MIT fetch + 自建解析）；④ scaffold = **qlib 双区域挂载**。
>
> **关联**：[`track-b-preregistration.md`](track-b-preregistration.md)（文体 + 共享统计门）、[`ADR-010`](../decisions/ADR-010-sesoi-tost-sequential-gate.md)（J-T 等价门）、[`theory-of-computable-reality.md`](theory-of-computable-reality.md) §3.1、[`market-driver-framework.md`](market-driver-framework.md) §2/§6.1/§8。
> **证据**：[`reports/2026-08-03-qlib-dualregion-poc.md`](../reports/2026-08-03-qlib-dualregion-poc.md)（可行性+8门）、[`reports/design/2026-08-03-conditional-rank-ic-multiplicity.md`](../reports/design/2026-08-03-conditional-rank-ic-multiplicity.md)（gate 7）、[`reports/design/2026-08-03-regime-pit-and-dashboard.md`](../reports/design/2026-08-03-regime-pit-and-dashboard.md)（gate 7 regime+gate 8）、[`reports/design/2026-08-03-ashare-fundamentals-source.md`](../reports/design/2026-08-03-ashare-fundamentals-source.md)（gate 4）。
> **取代**：`reports/design/2026-08-03-track-c-prereg-skeleton.md`（v0.1 骨架 → 本 v1.0）。

---

## 0. 与 B/C/D/E1 + Track B 的关系（新预注册线，绝不污染）

Track C 是**全新预注册线**，与 B/C/D/E1 + Track B 冻结面完全隔离（同 Track B §0 铁律）：
- **新 config = 新 ledger 行**；绝不静默覆盖历史（ADR-006 durable-registry）。
- **不重写历史**：B/C/D/E1 + Track B 的 ledger 行不变。
- **null-favored**：前沿共识（Profit Mirage / Alpha Illusion / Lopez-Lira 2025）+ 战略复盘 → null 是下注热门。
- **chronological walk-forward**（非 shared-fold CV-proxy）。

---

## 1. 单一可证伪 claim（两尾、预注册、null-favored）

> 把"美股 S&P 500 + A 股 CSI 300/500"双区域统一打分后的 top-quantile 组合，在 **联合 chronological walk-forward** 月频横截面 rank-IC 上，**是否显著优于** price-only baseline？
> **conditioning = 单个预指定交互项** `treatment × regime_state`（**1 个假设，multiplicity 预算 = 1**，非 K 个事后子组——见 §8 + multiplicity 笔记 §1）。
>
> - **null = 下注热门**：双区域月频已定价 / 因子 alpha 为泄漏 artifact / 跨市场传染已被定价 / 成本侵蚀 → null 预期成立且可发表。
> - **双尾**：正 = 双区域条件化增量有效；负 = 更差（过拟合/噪声）；CI 跨 0 = null（紧则可发表）。
> - **等价门（J-T，复用 ADR-010）**：RCIₖ ⊂ [−SESOI,+SESOI] → 等价。**等价 ≠ 市场有效**，只 = "此 bundle 在此实现下未达 SESOI"。

### 1.1 regime_state 定义（三层 PIT 复合，owner 已裁断）

`regime_state` = 以下三层 PIT 指标的**等权合成**（0–100 温度），每个按 **TACO as-of 固定窗** σ-归一化（`market-driver-framework.md:178-181`，**绝不追溯重算**，防批判者 M1 regime 泄漏）：

| 层 | PIT 指标（复用轮子） |
|---|---|
| **meso 板块** | 美股 SIC-peer 动量（Phase D 复用）+ A 股申万（SWFC）行业动量 |
| **macro 市场** | 5 线（`market-driver-framework.md` §3）：VIX-via-FRED + credit spread + term spread + DFF surprise + EPU（EPU G3 → exploratory） |
| **global 跨市场传染** | **Diebold-Yilmaz spillover**（`diebold-yilmaz` PyPI MIT 或 `connectedness` PyPI），US↔CN 指数收益率面板的 total/directional spillover，滚动 as-of 窗 |

⚠️ 命名碰撞：`connectedness` 的 "PIT normality transform" = **概率积分变换**（copula），**非** point-in-time——它不解决时点泄漏。

### 1.2 "入手/跑路"仪表盘（gate 8，**非主张**）

regime_state → 0–100 综合温度 → "入手/跑路"提示，作**非主张探索层**：明确"探索性/非投资建议"banner（与现有 Pages 站一致）+ 轻量 PIT 合同（全 PIT + snapshot+sha256）+ **不进 headline / 不进 ledger 确认行**。若 owner 要问责 → 单独二级 timing 预注册（默认非主张）。

---

## 2. Universe（双区域 PIT）

- **美股**：S&P 500 PIT（`hanshof/sp500_constituents` MIT 主 + `pierrebrunelle` 校验），2016+（沿用 Track B §2 实测 min Jaccard 0.8544 → headline 限 2016+）。
- **A 股**：CSI 300/500 PIT（`index-constitution` MIT，`constituents_at(date)`/`is_member()`）。⚠️ 进 headline 前完成 7-gate（G2 成分重建 PIT 性、G4 snapshot、G7 politeness）——已查 MIT + 历史 constituents API。
- **幸存者偏差**：PIT 成分缓解，**不可根除**（无免费退市 PIT）。headline = 保守上界。

---

## 3. Features（七大主题映射 — 全部已调研解决）

| 主题 | 美股（复用 Track B） | A 股（调研裁决） |
|---|---|---|
| ① 行情/价格 | Tiingo+Alpaca ✅ | **baostock 价格**（MIT，`tradestatus`停牌+`adjustflag`/`query_adjust_factor`复权因子+`query_all_stock`历史含退市；价格交易所定→G3 低危）或 **qlib+AKShare 采集器**（MIT，commit `83d089b`，补 survivorship） |
| ② 宏观 | ALFRED vintage ✅ | **ALFRED/OECD 中国序列**（`CHNGDPNQDSMEI` 等，vintage-safe）= headline；**NBS-only**（M2/社融，GDP/CPI 实证大幅回改、无 vintage API）→ snapshot+exploratory（EPU 先例）。复用 `mbk-dev/nbsc`（latest-only） |
| ③ 基本面 | EDGAR filed-date PIT ✅ | **⚠️ 修订 #47：cninfo → exploratory-only**（G1：cninfo 反爬 + 商业数据产品授权 ≠ EDGAR 开放 API；保守处置）。仍 = A 股 EDGAR 等价（申报日 + as-filed + 修订透明），`rollysys/use_cninfo` MIT ✅ fetch + Aionis 自建 PyMuPDF 解析；但 **A 股基本面降 exploratory，不进 confirmatory headline**（claim 收窄为 US-rank-IC + A 股 exploratory 条件化）。baostock reject（G3 结构性失败）；Tushare fallback（G1 付费/ToS）。见 [`ashare-fundamentals-source.md`](../reports/design/2026-08-03-ashare-fundamentals-source.md) §3 G1 |
| ④ 新闻情绪 | E3 闭集 13D/8-K（受控 ablation） | 仅 exploratory（不作主 alpha，同 Track B §3.4） |
| ⑤ 风险 | alphalens/pyfolio ✅ | 复用 |
| ⑥ 回测净成本 | FINSABER ✅ | 复用 |
| ⑦ 市场结构 | FF5 + Amihud ✅ | A 股 FF 等价（CH3/CH4 因子）可得性待 intake |

---

## 4. Learner（复用，零改动）

LightGBM frozen（同全家族）+ `lambdarank`（RD-15，`ranking_contract.py`，bin_count=5）。

---

## 5. Validation（**联合** chronological walk-forward — owner 已裁断）

> **联合折叠**（非分区域独立）：双区域同一时间窗同时含美股+A 股，使 Diebold-Yilmaz 跨市场传染信号可进 regime_state。

- **函数**：`eval/cv.py:purged_walk_forward_splits(expanding=True, min_train_months=60, embargo=21)` + `assert_chronological_split`（RD-03）。
- **联合面板对齐**：按**各区域自身交易日历**对齐（A 股 T+1、涨跌停、停牌；美股 T+0），月末日截面采样；embargo=21 sessions（按区域各自交易日）防标签泄漏。
- **泄漏防线**：regime_state 的 spillover/动量指标用 as-of 固定窗（TACO）；跨市场 spillover 计算只用 ≤t 数据（Diebold-Yilmaz generalized FEVD 是向前 H 步，PIT 安全）。
- 与 B/C/D/E1 + Track B 区别：严格 train < test（chronological），非 shared-fold CV-proxy。

---

## 6. Horizon
h=21 sessions（≈1 月）confirmatory；h=10/42 exploratory。同 Track B §6。

---

## 7. SESOI / 等价门（复用 ADR-010 Jennison-Turnbull）
SESOI ±0.010；looks {60,90,120} 月；RCI levels 99.44/97.64/95.00%；zₖ=(2.772,2.263,1.960)；n_trials=30；HAC Newey-West SE；strict-containment RCIₖ⊂[−0.010,+0.010]→等价。**应用于交互项 `treatment × regime_state` 的 rank-IC 差分序列**。

---

## 8. Multiplicity（单预指定交互，预算 1）

- conditioning = **单个预指定交互项**（非 K 事后子组）→ multiplicity 预算 = **1**（multiplicity 笔记 §1）。
- **n_trials=30** 沿用 Track B §8：DSR（`purgedcv`）+ PBO（CPCV）+ Hansen-SPA/MCS（`arch`）+ Harvey-Liu haircut（`YannickKae` CC0），喂**全部试过**的 config（含丢弃）。
- 候选升级：**Deflated-RankICIR**（FARS 2026，DSR 适配因子级 RankIC）—— license 待查（`drankicir-check` agent [1210] 失败，未验），未验前不采用。

---

## 9. Baseline（复用）
price-only S1（momentum/reversal/vol/liquidity）+ 等权。DM 检验对象 = **组合收益 loss**（H-1 复审纠正），cluster-robust SE（按 month）。

---

## 10. frozen config（**待 owner `config_committed` 冻结**）

| 键 | PROPOSED 值 | 依据 |
|---|---|---|
| universe_source | S&P 500 PIT（hanshof）+ CSI 300/500 PIT（index-constitution） | §2 |
| feature_cols | **~54 预指定 per-stock 列（双区域对称）+ 3 regime_state 条件变量**，见 §10.1；**无 outcome-based 选择** | §3 + §10.1 |
| learner_objective | `lambdarank`（RD-15） | §4 |
| validation_method | `joint_chronological_walk_forward` | §5 |
| regime_state | 三层 PIT 等权复合（meso+macro+global DY-spillover），TACO as-of 窗 | §1.1 |
| horizon | 21（confirmatory） | §6 |
| embargo | 21 sessions（按区域交易日） | §5 |
| sesoi | 0.010 | §7 |
| looks | (60,90,120) | §7 |
| n_trials | 30 | §8 |
| bin_count | 5（quintiles） | §4 |
| scaffold | qlib 双区域挂载（≤3.12 隔离 venv） | POC gate 1/2/3 |

### 10.1 feature_cols 完整枚举（预指定，冻结前定，无 outcome 选择）

| 类 | 列 | 来源 / PIT |
|---|---|---|
| **美股基本面 (13, 复用 Track B §10.1)** | roa, roe, profit_margin, asset_growth_{1m,12m}, revenue_growth_{1m,12m}, equity_growth_1m, leverage, debt_to_equity, book_value_per_share, accruals, investment_12m | EDGAR filed-date PIT |
| **美股价格 (10, 复用 Track B)** | momentum_{5,10,21,42}d, reversal_5d, volatility_{21,63}d, turnover_21d, beta_252d, amihud_illiquidity_21d | Tiingo / Alpaca |
| **A 股基本面 (13, 对称镜像)** | 同美股 13 字段 | **cninfo as-filed PDF → Aionis 自建解析**（PyMuPDF MIT），filed-date PIT |
| **A 股价格 (12)** | 同美股 10 + `limit_up_down_distance`（涨跌停距，A 股特有）+ `suspension_flag`（tradestatus 派生） | baostock / qlib+AKShare（MIT） |
| **宏观 headline (6, vintage-safe)** | US: dff_surprise, term_spread(1y/10y), vix, credit_spread；CN: gdp_surprise, cpi_surprise | ALFRED / OECD（vintage 跟踪） |
| **宏观 exploratory (2, 非headline)** | CN: `m2_yoy`, `社会融资`（`exploratory_flag=True`） | NBS via `mbk-dev/nbsc`（snapshot+sha256，latest-only） |
| **regime_state 条件变量 (3)** | `meso_composite`（US SIC-peer + A 股申万 动量等权）、`macro_5line_composite`（market-driver §3 五线）、`global_dy_spillover`（US↔CN total spillover，`diebold-yilmaz`/`connectedness`） | **TACO as-of 固定窗 σ-归一化，绝不追溯重算** |

- **per-stock feature_cols = 54**（US 23 + A 股 25 + 宏观 headline 6）；regime_state 3 列作**条件化交互** `score × regime_state`（§1，预算 1）；宏观 exploratory 2 列单独标记、**不进 confirmatory headline**。
- **新闻情绪不入 feature_cols**（§3 ④，仅 S3 受控 ablation）。
- **A 股 FF 等价（CH3/CH4 因子）**：⑦ 市场结构如需，挂 FF5 残差（美）+ CH 因子（A 股）作 risk 控制列，**冻结前定**（不事后加）。

**config_committed BEFORE result**：frozen config 的 sha256 必须在首次 OOS rank-IC **之前**写入 `runs/ledger.jsonl`（复用 `reporting.save_run.commit_config`）。**改 config = 新 ledger 行**（durable-registry）。H6 bit-identical。

---

## 11. 显式 non-goals
- 不做日内/衍生品/加密；只月频横截面选股（双区域 PIT）。
- 不做 learned world model（判别式 LightGBM + structural-only LLM）。
- **regime/timing 不作第二证伪锚**（`market-driver-framework.md` §2/§8）——只作条件/情景层。
- 新闻情绪不作主 alpha（只受控 ablation）。
- "入手/跑路"仪表盘 = 非主张探索层（不进 headline/ledger 确认行）。
- 不宣称可交易性：净成本（FINSABER）是 exploratory 次级透镜。

---

## 12. owner-decision 点（**2026-08-03 已裁断**）

| # | 决策 | 裁断 |
|---|---|---|
| 1 | 双区域折设计 | **联合折叠**（传染信号需要联合面板） |
| 2 | regime 定义 | **三层 PIT 等权复合**（meso+macro+global DY-spillover，TACO as-of） |
| 3 | A 股源 | **cninfo**（MIT fetch + 自建解析）；baostock reject、Tushare fallback |
| 4 | scaffold | **qlib 双区域挂载**（gate 1/2/3 POC 已验） |

**仍待 owner（冻结前）**：feature_cols 完整枚举（§3 ⑦ + cninfo 解析字段 finalize）；`config_committed` ledger 行授权（= 冻结）。

---

## 13. 不越界声明（PROPOSED，未冻结）
- `[F]` **`config_committed` 已入 ledger**（行 #46，sig `758ca4d739f09331ee4dceb726d9d0d0f7c5110303acc6dcac59919701374fad`，2026-08-03，先于任何 OOS；sha256 自洽已验）；未运行 confirmatory/strategy/horizon/forward 脚本；未观察任何 outcome/E3（S0 尚未执行）。
- `[F]` 未触 B/C/D/E1 + Track B 冻结面 / prereg / ADR / config / 结果 / data。
- `[F]` 本预注册 PROPOSED；owner 写 `config_committed` ledger 行 = 冻结（= 授权我执行首次 OOS 前的 config 哈希入账）。
- `[I]` 任何落地 = 新预注册 + 新 config + 新 ledger 行，绝不静默修改历史。

---

## 14. 引用
- 内部：`track-b-preregistration.md`、`ADR-010`、`theory-of-computable-reality.md` §3.1、`market-driver-framework.md` §2/§6.1/§8、`data-intake-rubric.md`、`reports/2026-08-03-qlib-dualregion-poc.md`、`reports/design/2026-08-03-{conditional-rank-ic-multiplicity,regime-pit-and-dashboard,ashare-fundamentals-source}.md`。
- 外部（permissive）：`microsoft/qlib`（MIT）、`diebold-yilmaz`（PyPI MIT）/`connectedness`（PyPI）、`index-constitution`（MIT）、`rollysys/use_cninfo`（MIT）、`eslazarev/purgedcv`（MIT）、`arch`（BSD）、FINSABER（Apache）、alphalens/pyfolio-reloaded（Apache）。
