# Phase B 预注册 — Filed-Date PIT 时点的横截面选股增量

> 状态：**v0.3 · 2026-07-27 · 预注册（critic-integrated + durable-registry 修订）**。
> **Durable registry（非一次性）**：§8 冻结 config 的 sha256 入 `runs/ledger.jsonl` **先于**
> 任何 OOS 结果被观测——该 (ts, sha256) 对是永久抗泄漏证据，**永不被消耗**。同 config 重跑
> = 预期行为（H6 确定性保证 bit-identical）；改 config 跑 = ledger 新行（合法迭代）。详见 §9。
> **S0 进行中**：slices 1-2 已落地（period-end 臂 `pit_align(align_on="end_lag")` + rank-IC eval，
> 86 tests 绿，ruff clean）；slices 3-5 待做。
>
> **v0.1 → v0.2 关键变更**：① 路径 **A-GKX → A-自建 ticker-keyed**（critic C1 证 A-GKX 不可行：
> GKX 是 permno 键、无免费 PIT permno↔CIK 桥；`cik_map` 用今天快照 = look-ahead 泄漏）；
> ② C1+C2 由路径切换解决；③ C3-C5 / H1-H7 / M2 / M4 全部 integrate；④ 双尾 + 可发表性条件化。
> critic 认可并保留：filed-date PIT 层扎实（VERIFIED）、null-as-favorite 诚实、冻结纪律正确、
> 数值 as-filed State 替 LLM embedding 消除 GLM-jitter 非确定性。
>
> **v0.2 → v0.3 关键变更**（方法论措辞，**非**实验改动）：把 "freeze → 单次 unblind → 预注册耗尽 →
> no re-runs" 的一次性仪式框，重写成 **durable registry**——抗泄漏锚点 =「config sha256 先于首次
> OOS 结果入 ledger」的永久证据，同 config 可无限重跑（H6 确定性），改 config = 新 ledger 行。
> 冻结的 `frozen_config` **一字未改**；sha256 变更记录在 append-only `runs/ledger.jsonl`
> （`prereg_reframe` 条目，supersede 冻结时 #20 的哈希）。**文档不自载哈希**——哈希只活在 ledger。

---

## 0. 与 Phase A / TCR 的关系（基准迁移 + 修正案）

- **Phase A**（ERL-only 事件冲击，sector-ETF h=1 DA-lift）= n≈44–131，underpowered → **pilot**，保留为子结果。
- **Phase B** 把 benchmark 从"事件窗" **re-anchor 到横截面选股**。**路径 = A-自建 ticker-keyed**
  （EDGAR filed-date + Tiingo/Alpaca 价，复用 `features/selection_panel.py` + `ingest/fundamentals.py`），
  **非 GKX**（理由见 §13 + critic C1）。
- **WRL=ERL 超集桥**：State 是新增维度，复用 alignment/fundamentals/selection_panel（不重写 Phase A → 满足 TCR §5）。Event/ERL → Phase C，Relationship → Phase D。
- 与 selection-doc（v0.2）映射：本 Phase B ≈ **Stage S2**，但 baseline 臂 = **period-end 时点**（自建），filed-date 臂 = 现有 fundamentals.py 的 filed PIT。

---

## 1. 单一可证伪 claim（预注册，**双尾**，首次 confirmatory run 入 ledger）

> 在**同一 ticker PIT universe**（S&P 500 PIT，hanshof 缓解幸存者）上，把 6 核心基本面从
> **period-end + 保守 lag 时点**（`arm_base`，自建、PIT-safe）换成 **EDGAR as-filed 的精确
> filed-date 时点**（`arm_state`，复用 `fundamentals.py`），两臂**同股 / 同价特征 / 同模型 / 同 purged 折**，
> 是否在 OOS 窗带来**横截面 rank-IC 的显著增量**（**双尾**）；增量过 DSR / haircut，在 lag-shift 控制门下消失。

- **null = betting favorite**：保守 lag 已足够，filed-date 时点无边际（基本面在月频已被有效定时/定价）。
- **双尾解释（M2）**：
  - **正**增量 = filed-date 时效性赢（保守 lag 太 stale）。
  - **null** = 无差（保守 lag 够用）。
  - **负**增量 = filed-date 反而更差（精度无益 / 引入修订噪声）——**同样合法**。
- **可发表性 = realized σ(IC) 的函数**（§7），不先验钉 MDE（C4）。

---

## 2. 表示增量（两臂时点对照，PIT 逐项）

- **Entity = ticker**（EDGAR CIK↔ticker + Tiingo ticker **天然对齐，无 permno 桥**——C1 由路径消解）。
- **两臂的 6 基本面**（assets/equity/revenue/net_income/shares_out/long_term_debt，XBRL multi-tag fallback，**与 `fundamentals.py` 对齐**——M1）：
  - **`arm_base`（period-end + 保守 lag）**：基本面值钉 fiscal period-end，再 + 文献保守 lag（仿 GKX/Compustat 约定；lag 月数钉在冻结 §8）。PIT-safe，但可能 stale。这是"被对照的标准做法"。
  - **`arm_state`（filed-date）**：复用 `fundamentals.py` 的 `pit_align`（`merge_asof backward on filed`、NaN-before-first-filing、修订处理）——**critic VERIFIED 扎实**。
  - 派生 `mktcap/P_B/ROA` 用**各自臂**的 shares 时点（period-end 臂用 period-end shares；filed 臂用 filed shares）。
- **两臂共用**：价特征（momentum/reversal/vol，`close ≤ t_info`）、FF5 因子、DFF 宏观（broadcast）。
- **关键**：两臂**同 universe、同价特征、同模型** → 增量**只**来自基本面时点。这比 GKX 版干净（C2 消解：两种时点都由我们自建定义，无需反推 GKX 约定）。

---

## 3. 数据（A-自建 ticker-keyed，无 permno / 无付费）

- **价**：Tiingo（主）→ Alpaca（备），已接入 `ingest/market.py:fetch_prices`；数据到 ~2026。
- **基本面 PIT**：SEC EDGAR XBRL（as-filed），`edgartools`；filed-date 由构造 PIT。
- **universe**：S&P 500 PIT —— `hanshof/sp500_constituents`（日频 1996+，**fork + 审行数**）为主，`pierrebrunelle`（月频 2016+ 可复现）交叉校验；**分歧大则限 2016 后**。
- **切分（预注册）**：训练 2011–2016（EDGAR XBRL 2011 起密集），**OOS 2017-01 → 最新（~2026-06，≈110 月）**。
- **幸存者**：经 hanshof PIT 成分缓解，**不可根除**——headline = 保守上界（selection-doc v0.2 §8.4）。无付费数据下任何路径都躲不掉。
- **不需要** GKX / permno / 付费 CRSP / qlib（自建 spine 已够）。

---

## 4. 实验设计

- **标签 y**：未来 h=21 session（≈1 月）收益，严格 future-only（`features/alignment.py` 不变量保留）。
- **两臂同 LightGBM**（`n_jobs=1, random_state=0` 确定性；XGBoost mirror secondary），**只改基本面时点** → 隔离时点增量。
- **CV（新代码，H1）**：`purgedcv.PurgedKFold`，group=date-month，embargo ≥ h，`n_splits` 钉冻结。**两臂共用同一组折**。（现 `eval/cv.py` 用 `WalkForwardSplit`——Phase B 引入新 panel-CV 路径，不复用。）
- **primary 指标**：OOS cross-sectional rank-IC（Spearman，逐月）→ 时序均值 + **Newey-West HAC / moving-block-bootstrap DM**（M4，frontier §2A 默认，**非** vanilla 月聚类——小 n 过拒绝）。
- **secondary（exploratory）**：top–bottom 分位组合 Sharpe、quantile spread、IC-IR、turnover。
- **Double-ML（exploratory，不当 gate——H3/H4）**：filed-date State 当候选因子，价 + period-end 当高维 nuisance，测 SDF 增量（`DoubleML`/`econml`，折**必须**包 `PurgedKFold`）。**与 rank-IC 不一致 → 报 mixed，不宣称正向。**

---

## 5. 控制门（必须全过）

1. **period-end 臂即主控制（C3）**：`arm_base`(period-end+lag) 本身是 claim 的补集——filed-date 增量就是相对它的 IC 差。最锐对照。
2. **lag-shift 控制（C3 secondary，替代 ill-defined shuffle）**：把 filed-date 按**公司**随机平移一个 lag（取自经验 filing-lag 分布，**保序**——不破坏值→披露先后），增量必须消失。证增量来自**精确 filed 时点**而非任意时点扰动。
3. **placebo（M5 强化）**：**月内置换 filed-date 值**（保时点、乱值）→ 增量 ≈ 0（比 iid 噪声更锐，专测公司级对齐）。
4. **lookahead audit（C5，新 hermetic 测试）**：合成 ticker panel + 一个 **label_start 之后才 filed** 的 fact → 断言它不进 t < label_start 的特征。**冻结前先写**（§8 #1）。
5. **memorization audit**：不适用（数值 as-filed，非 LLM 抽取）。

---

## 6. 多重检验审计

- **Deflated Sharpe**：N = 计**所有**试过的 feature set / config（含丢弃）→ `mnemox-ai/deflated-sharpe`。
- **PBO**：`purgedcv` CPCV + `reconstruct_paths` → 报告 path 分布，非单一 Sharpe。
- **Hansen SPA / MCS**：`arch.bootstrap.multiple_comparison` → filed-date 臂是否在 config 集存活 + "是否有什么 beat baseline"。
- **Harvey-Liu haircut**：兜底 horizon × spec（`YannickKae/Evaluating-Investment-Strategies` CC0 端口）。
- **报告规则**：每个 Sharpe 带 **deflated + haircut + PBO 三联**。

---

## 7. Power（条件化于 realized σ(IC)，C4）

- OOS ≈ 110 月（2017-01→2026-06）→ headline 簇数 ≈ 110。
- **可发表性 = realized σ(IC) 的函数**：`arm_base` OOS 跑出 σ(IC) 后，**95% CI 半宽 < 0.015**（≈ σ(IC) < 0.061）才算"紧到能发表 null"。**先验不钉 MDE。**
- 粗估：σ(IC)=0.06 → 可探测月 IC ≈ 0.016；σ(IC)=0.10 → ≈ 0.027（此时 null 不够紧 → 报 inconclusive）。诚实写在结果里。
- vs Phase A（簇 44–131）**数量级提升**；比 GKX 的 53 月也更强（~110 月）。

---

## 8. 冻结清单（commit config → sha256 → ledger，先于首次 OOS 结果）

### 8.0 冻结决策（pinned 2026-07-27；**veto window 到 S0 开工前**——任一项可改，改则进 ledger）

| 项 | 冻结值 | 依据 |
|---|---|---|
| **period-end 臂 lag** | 10-K(年) **+6 月**；10-Q(季) **+4 月**（加在 `end` 上） | Fama-French / Compustat 标准"信息可得"约定（学界最常用）→ "filed-date 优于标准做法"才可发表。**注意**：slow-filer（filed > end+lag）使 period-end 臂对这些公司略 leaky-optimistic → **偏向 against filed-date**，故 filed-date 赢=robust，filed-date 输=ambiguous。**敏感性**：另报"准时申报"子集（filed ≤ end+lag，此时 period-end 臂 PIT-safe）上的对比，消除混淆。 |
| **universe 分歧阈值** | hanshof vs pierrebrunelle 在 2016+ 月度重叠 **Jaccard ≥ 0.95**；<0.95 → headline OOS 限到 **2016+**（pierrebrunelle 可复现窗）；两种都报为敏感性 | **outcome 已定（ledger #23 `universe_crosscheck`）**：实测 min **0.8544** / mean **0.9272** / median 0.9310（106 月，2016+）→ **< 0.95，规则触发**。但 OOS 2017-2026 本就在 2016+ 可复现窗内 → **窗口不变**。残差经诊断是 **ticker 改名**（`FB`/`META`、`BLL`/`BALL`）**非公司级分歧**；分隔符（`BRK/B`/`BRK-B`）已归一。hanshof 用历史正确 ticker（PIT 取数正确）→ **定为主源**，pierrebrunelle 作公司级交叉校验。 |
| **CV** | `PurgedKFold`，**n_splits=5**，**embargo=21 sessions（=h）**，**group=date-month** | 训练窗 ~72 月（2011–2016），5 折标准；embargo=标签窗防泄漏；按月聚类做 robust 推断 |
| **可发表性** | **95% CI 半宽 < 0.015**（≈ realized σ(IC) < 0.061）才算"紧到能发表 null" | 探测月 IC ≈ 0.02；σ(IC) 是 realized、非先验 |
| **h / 切分 / universe** | h=21 sessions；train **2011–2016** / OOS **2017–2026**；S&P 500 PIT（hanshof 主 + pierrebrunelle 校验） | EDGAR XBRL 2011 起密集；Tiingo 到 2026 |
| **LightGBM 超参（冻结，headline 外不调）** | n_estimators=500, lr=0.05, num_leaves=31, min_child_samples=20, reg_lambda=1.0, feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1, **n_jobs=1, random_state=0**（待入 pyproject） | 保守默认；feature_fraction/bagging 抗 PBO；确定性优先。任何调参只在 purged CV 内、且计入 DSR 的 N |
| **H6 确定性测试** | **留作 post-build 项**（需 rank-IC eval 代码先存在）；冻结时钉版本：`lightgbm`/`doubleml`/`econml`/`arch`/`alphalens-reloaded` 入 `pyproject.toml` | critic H6 |

- [ ] **#1 joined-panel PIT 测试（C5）**：先写 hermetic test（合成 panel + 晚 filed fact → 断言不泄漏）。建立在现有 `test_fundamentals.py`/`test_selection_panel.py` 之上，补 panel 级。
- [ ] **period-end 臂的 lag 定义**（文献/经验 filing-lag 分布；钉月数 + 依据）。
- [ ] 6 基本面 + XBRL tag fallback（与 `fundamentals.py` 对齐，M1）。
- [x] universe：hanshof（cache+sha256 快照 pinned）+ pierrebrunelle 行数审计 + 2016+ Jaccard（done — ledger #23：min 0.854 < 0.95 触发，OOS 窗不变，残差=ticker 改名非公司分歧）。
- [ ] 切分（train 2011–2016 / OOS 2017–2026）+ h=21。
- [ ] LightGBM 超参 + XGBoost mirror + **版本钉**（`lightgbm`/`doubleml`/`econml`/`arch`/`alphalens-reloaded` 入 `pyproject.toml`，H6）。
- [ ] CV：`PurgedKFold`，`n_splits`、group、embargo（H1）。
- [ ] 控制门（§5）+ 多重检验集（§6）+ primary=rank-IC（**双尾**，M2）+ NW-HAC/MBB-DM（M4）。
- [ ] **Phase-B 确定性测试（H6）**：两次 panel-build + rank-IC → bit-identical。
- [ ] 可发表性阈值：CI 半宽 < 0.015（C4）。

---

## 9. 运行 / 账本规则（durable registry，非一次性）

- **抗泄漏锚点**：§8 冻结 config 的 sha256 必须在**首次** `arm_state` vs `arm_base` OOS rank-IC
  结果被观测**之前**写入 `runs/ledger.jsonl`。该 (ts, sha256) 对一旦写入即**永久证据**。
- **首次 confirmatory run**：冻结 config + 全控制门就绪后，首次跑出 OOS rank-IC 差 → 记入 ledger
  （标 `confirmatory: first`）。这是 headline 的唯一来源。
- **双尾判读**：正 = filed-date 时效赢；负 = filed-date 更差（精度无益/噪声）；CI 跨 0 = null（CI 紧则可发表）。
- **CI 跨 0 不得宣称正向。**
- **重跑政策（durable，可无限重跑）**：
  - **同 sha256 重跑** = 预期行为，H6 确定性保证 bit-identical；结果入 ledger（标 `rerun: reproducibility`），**不替换 headline**。
  - **改 config 后跑** = 合法迭代，**必须**记为新 ledger 行（新 sha256，标 `exploratory` 或新的 `confirmatory`），**不得静默覆盖**旧行。
  - **headline 不可被"重跑到显著"挽救**：改 config 追逐显著性 = 新的探索性条目，不复用首次 confirmatory 的资格；该次试验计入 §6 DSR 的 N。
- **探索性跑**（调参 / debug / 新想法 / 新数据）**无限免费**，只要不冒充 confirmatory。项目是长期迭代研究，不是单次实验。

---

## 10. 与 `frontier_positioning.md` / TCR §8.5/§11 一致性

- 判别式（LightGBM / Double-ML）+ PIT + 反泄漏 + 与 n 成比例。**无 learned generative world model**。
- State = **as-filed 数值观测**，非 LLM 填充 → 不涉 parametric 记忆泄漏（frontier §2B）。
- period-end 臂用**保守 lag**（非 raw period-end）→ 两臂**都 PIT-safe**，比的是"保守 lag 近似 vs 精确 filed"——**不**靠留泄漏当对照（不违反反泄漏身份）。
- ✓ 不违反 TCR §11。

---

## 11. 实现量（最小，复用优先）

- **复用**：`ingest/market.py:fetch_prices`（Tiingo/Alpaca）、`ingest/fundamentals.py`（filed-date PIT）、`features/selection_panel.py`（panel，已 done）、`features/alignment.py`、`eval/metrics.py`、`purgedcv`、`arch`、`alphalens-reloaded`。
- **新增**：period-end 臂（`pit_align` 加 period-end+lag flag）、`PurgedKFold` panel-CV 路径、rank-IC eval（`alphalens-reloaded`）、hanshof universe ingest、**C5 joined-panel PIT test**、**H6 确定性 test**。
- 不用 qlib / GKX / permno。PIT 安全靠 hand-rolled `merge_asof` + hermetic test（L1 记此 tradeoff）。

---

## 12. 开放风险（诚实承认）

1. **period-end lag 选不准** → filed-date 增量可能是"lag 差"而非"filed 精度"。预注册 lag 选择依据（文献 filing-lag 分布）。
2. **hanshof 幸存者** → headline 是上界。
3. **EDGAR 2011 前稀疏** → 训练窗起 2011。
4. **两臂同 EDGAR 源** → tag/fallback 须一致（M1 已对齐）。
5. **rank-IC vs Double-ML 分歧（H3）** → mixed 报告，不宣称正向。
6. **（可选正控制子实验）raw-period-end 臂**：若加一个无 lag 的 period-end 臂且其 IC > 保守-lag 臂，则**证明 raw period-end 泄漏**——一个验证 PIT 纪律的 meta-finding。非主 claim，结果仅作正控制。

---

## 13. TCR §7 修正案（H7 扩展，落到 `theory-of-computable-reality.md` §13）

> **supersede** TCR §7 的 Phase B 行（已就地订正）+ §10、§12.3 中"**同一事件 benchmark / +State vs Event-only**"措辞。

- **Phase A → pilot**（事件窗 benchmark，underpowered）。
- **Phase B re-anchor 到横截面选股 benchmark**，路径 = **A-自建 ticker-keyed**。曾选 A-GKX，**critic C1 证不可行**（permno 键无免费 PIT 桥；`cik_map` today-snapshot = look-ahead）→ 改 A-自建。**决策进 ledger。**
- **控制臂**：Event-only → **period-end+lag baseline**；State claim = **filed-date vs period-end 时点差（双尾）**。Event/ERL → Phase C。
- 理由：① 结构性解决 n=44 power（OOS ~110 月 vs 事件 44–131）；② State 在横截面才自然；③ WRL=ERL 超集桥仍成立（复用 alignment/fundamentals/selection_panel）。
- **不违反 §11**：仍判别式 / 反泄漏 / 与 n 成比例，无 learned world model。

---

> 下一步：评审本 v0.2 → 落 §13 TCR 修正案 → 冻结 §8（先写 C5 PIT test + H6 确定性 test）→ 才进 S0 实现
> （scale selection_panel 到 S&P500 PIT + period-end 臂 + rank-IC eval）。**未冻结前不动手。**
