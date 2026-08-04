# Track C 联合 US-CN chronological 折叠估计量 — 设计 spec（PROPOSED，owner 审阅）

> 状态：**PROPOSED · 2026-08-04 · opus 设计（Lane B 交付物）**。本 spec 只设计估计量；**不写 ledger、不观察 OOS rank-IC、不触冻结面**。confirmatory 跑需 owner GO + 新 ledger 行（= owner 动作）。
>
> 关联：[`track-c-preregistration.md`](../../docs/track-c-preregistration.md) §5（联合折叠）、ledger #46 `validation` 段、[`track-b-preregistration.md`](../../docs/track-b-preregistration.md)、`src/aionis/eval/track_b_baseline.py`（镜像源）、`src/aionis/eval/cv.py`、`src/aionis/eval/ranking_contract.py`。
>
> 取代：无（首版）。`track_c_conditional_ic.py` 是其 CN-only exploratory 前身（2-layer regime + Track B fitter on 单区）。

---

## 0. 目标与边界

**目标**：实现 Track C 的 **confirmatory 估计量**——双区域（US S&P500 + CN CSI300）**联合 chronological walk-forward** 月频 rank-IC，条件化于 `regime_state`（单预指定交互 `score × regime_state`，multiplicity 预算 1）。

**为什么需要它**：当前 `track_c_conditional_ic.py` 是 **exploratory**——Track B fitter on **CN 单区** + 独立 IC 回归 + 2-layer（或 3-layer US-only meso）regime。它**不是** §5 的联合折叠 confirmatory 估计量。confirmatory 需要：① 一个模型在 US+CN 联合面板上 fit；② 双区域同一时间窗同时含美股+A 股（让 DY spillover 跨市场信号进 regime_state）；③ per-region 时序断言；④ J-T 等价门作用在交互项的 rank-IC 差分序列。

**本 spec 产出（无需 owner GO，S0/估计量代码）**：
- 联合面板构造器（US `track_b_panel.parquet` + CN `cn_price_panel.parquet` → 带 `region` 列的联合月末面板）。
- 联合折叠 fitter（镜像 `fit_track_b_baseline` 折逻辑，加 per-region 断言 + 区域-月 group）。
- 联合条件化 IC 回归（扩展 `track_c_conditional_ic.py`：联合 IC 系列 + 3-layer regime）。
- 反退化测试（抓 agent slop；本会话 net_cost/CSI300/cn_panel 3 例翻车的同类风险）。

**不产出（边界）**：
- ❌ 不写 ledger 行（confirmatory OOS 观察前需 owner 授权新 ledger 行）。
- ❌ 不观察 OOS rank-IC 作为结论（exploratory 机器走通 = OK；confirmatory 判读 = owner GO 后）。
- ❌ 不触 B/C/D/E1 + Track B 冻结面 / prereg / ADR / config。
- ❌ 不替换 `fit_track_b_baseline`（Track B 冻结 #41 路径 0 diff；新建 `track_c_joint.py`）。

---

## 1. 架构 / 数据流

```
data/cache/track_b_panel.parquet   (US, 月末, 2016+, ~588 tickers, 23 features)
data/cache/cn_price_panel.parquet  (CN, 月末, 2014+, ~929 tickers, 12 features)
        │                                  │
        └──────────┐        ┌──────────────┘
                   ▼        ▼
        build_joint_panel()  → joint_panel [date, ticker, region, *shared_features, forward_return_h]
        (per-region 各自已完成月末采样；按 YYYY-MM 对齐到同一时间轴；
         shared_features = 两区域共有的 price 特征子集；region="us"|"cn")
                   │
                   ▼
        fit_track_c_joint(joint_panel, regime_state, feature_cols, ...)
          ├─ 折：calendar-month walk-forward（train 严格 < test 月；min_train=60）
          ├─ group = region-month（D1，区域内排序，避免跨币种污染）
          ├─ per-region chronological assert（train.max < test.min，逐区）
          ├─ LightGBM lambdarank（#46 learner；bin_count=5；train-only binner fit）
          └─ 输出：oos_scores（含 region）+ per-region IC 系列 + 联合 IC 系列
                   │
                   ▼
        conditional_ic_joint(ic_series=联合IC, regime=regime_state as-of 月末)
          └─ IC_t ~ regime_t (HAC) → alpha/beta(interaction)/R²；high/low regime 分割
          └─ （confirmatory 时）J-T 门作用在 beta 驱动的 rank-IC 差分序列
```

**regime_state as-of 月末**：`regime_composite.parquet` 是日频 PIT 序列；在条件化回归里按 IC 月末日期 `reindex(method="ffill")`（PIT 安全——regime 只用 ≤ 月末数据；与 `track_c_conditional_ic.py:45` 一致）。

---

## 2. 联合折叠机制（核心洞察）

**关键定理**：month-end 采样 + calendar-month 折边界 ⇒ **per-region 21-session embargo 自动满足**，无需逐区数交易日。

证明（直觉）：相邻月末在任何市场都相隔 ≈ 1 个日历月 ≈ 21–23 个交易日。train 严格在 `< test_calendar_month` 的月份里，test 在 `test_calendar_month`。故在**每个区域各自交易日历**里，最后一个 train 月末 → 第一个 test 月末的间距 ≥ 21 sessions（US 用 NYSE 日历满足；CN 用 XSHG/XSHE 日历满足）。`#46 validation.alignment = "per-region trading calendar; month-end cross-section sampling"` 与 `embargo_sessions=21` 同时成立。

**实践后果**：`fit_track_b_baseline` 的折逻辑（按 `_year_month` Period 切，train `< test 月`）**可直接复用于联合面板**——把 US+CN 月末行拼成一个 panel，同一 `YYYY-MM` Period 把两区同月行归入同一折。**不需要**改 `cv.py` 或 `purgedcv` 的单一-Timedelta embargo 语义。

**注意（保留 `fit_track_b_baseline` 中的发现）**：原 fitter L230-238 计算了 `embargo_td` 后被 L240 `< test_calendar_month` 覆盖——这是**有意为之的冗余**（月边界即 embargo），不是 bug。联合版同理：月边界即 per-region embargo；`embargo_td` 保留为 sanity assert 的注释，不进 train_mask 逻辑。

---

## 3. 设计决策（D1–D5）

### D1 — lambdarank group = **region-month**（区域内排序）【推荐；owner-decision】

**问题**：`construct_month_groups` 给 `year*12+(month-1)`，会把 US+CN 同月股票放同一 query。`forward_return_h` 是**本币**收益（US=USD，CN=CNY）。统一排序会让 "5% USD 收益 > 3% CNY 收益" 跨币种比较——汇率变动会污染 label 排序。

**推荐**：group = **region-month**（US 股票只和 US 比排名；CN 只和 CN 比；两区域是**独立 query group**，但模型**联合 fit 共享参数**）。group_id 构造：`(year*12 + month-1) * 2 + region_code`（US=0, CN=1）→ 唯一且单调可排序，兼容 `get_group_sizes` 的"sorted group ids"要求。

**理由**：① 币种干净（区域内 label 同币种）；② 仍是"联合模型"（一个 LightGBM，两区共享树结构，跨区学共性）——满足 §5"联合折叠"意图；③ 与 null-favored + anti-leakage 一致（消除汇率混淆变量）。

**否决的替代**：group = calendar-month（US+CN 同 query）——跨币种 label 污染，方法学更弱。

**⚠ owner-decision**：#46 `claim` 说"dual-region cross-sectional monthly rank-IC"但**未显式冻结 group 构造**。本 spec 推荐区域内排序（D1），但 confirmatory 跑前需 owner 签注。exploratory 机器走通用 D1。

### D2 — 联合 rank-IC = **区域内 IC 的联合序列**（币种干净）

rank-IC = spearman(score, forward_return) **在区域内**计算（US IC per month；CN IC per month）。**联合 IC 系列** = 每月两区 IC 的等权平均（`mean(us_ic_t, cn_ic_t)`）。这避免统一横截面 IC 的跨币种相关。

**对照**：`track_c_conditional_ic.py` 当前用 CN 单区 IC。联合版换成 D2 的联合 IC 系列。

### D3 — **per-region chronological assert**（#46 validation.chronological_assert 要求）

每个 fold、每个区域分别断言：`train_dates[region].max() < test_dates[region].min()`。原 fitter 只在整 panel 断言一次；联合版**逐区**断言（US train.max < US test.min **且** CN train.max < CN test.min）。这比全局断言更严，直接对齐 #46。

### D4 — regime_state 条件化 = **PIT as-of 月末**（ffill，无追溯）

`regime_state`（日频）在 IC 月末日期 `reindex(method="ffill")`——只取 ≤ 月末的值。TACO 归一化已在 `regime_composite.py` 保证 regime_t 只用 [t0,t] 数据（无未来泄漏）。与现有 `track_c_conditional_ic.py:45` 一致。

**meso 层依赖 Lane A 裁定**：若申万 7-gate PASS → meso 进 3-layer composite（spec-faithful）；若 G3 FAIL → meso 保持 US-only 或降 exploratory，本估计量仍跑（regime_state 用可得的最 spec-faithful 版本），但 confirmatory 需配套 spec 修订（新 ledger 行）。

### D5 — 共享特征子集 = **两区域共有列**

US `track_b_panel` 有 23 列（13 fundamentals + 10 price）；CN `cn_price_panel` 有 12 列（10 price + 2 A 股 extras）。**共有** = 10 price 特征（`TRACK_B_PRICE_FEATURE_COLS`）。联合 fit 的 `feature_cols` 用这 10 列（区域对称、币种无关的价格技术特征）。

**注**：这是 exploratory 机器的最小可行特征集。confirmatory 的完整 54 列（含 US fundamentals 13 + CN cninfo 镜像 13 + 宏观）需 cninfo fetch + 真实接线（高成本，#47 已降 exploratory）。**confirmatory 跑前 feature_cols 由 owner 在新 ledger 行冻结**——本 spec 不预冻结。

---

## 4. 反泄漏不变量（assert 规格）

| # | 不变量 | 实现 |
|---|---|---|
| I1 | 每 fold 每区域 train.max < test.min | D3 per-region assert |
| I2 | binner 只在 train fold fit；test 用冻结 edges | 复用 `fit_monthly_bins`/`transform_to_relevance`（ranking_contract，已验证） |
| I3 | regime_state as-of 月末只用 ≤ 月末数据 | `reindex(method="ffill")`；TACO 在 composite 已保证 |
| I4 | forward_return label 不进特征 | shared_features 仅 10 price 列；`forward_return_h` 仅作 label |
| I5 | 区域-月 group 不跨币种 | D1 group = region-month |
| I6 | H6 确定性 | seed=0, n_jobs=1（#46 learner.params 已冻结） |

---

## 5. 反退化测试（抓 agent slop —— 本会话 3 例翻车的同类）

> 教训（handoff §2026-08-04）：net_cost turnover 退化两分支都=0、CSI300 NaT、cn_panel MultiIndex 命名——agent 测试"绿"但空洞（小 fixture→NaN→跳过 assert；测被复用函数而非包装）。下列测试**直接抓退化**：

| 测试 | 抓什么 |
|---|---|
| `test_joint_panel_has_both_regions` | 拼接后 US+CN 行数都 > 0（抓"一区被 drop"） |
| `test_group_is_region_month_not_unified` | 同一 calendar-month 的 US 行与 CN 行 group_id **不同**（抓 D1 退化为统一 group） |
| `test_chronological_assert_is_per_region` | 构造一个 US train 末 = CN test 始的对抗 fixture，断言仍 PASS（抓全局断言冒充 per-region） |
| `test_embargo_holds_when_cn_monthend_after_us` | CN 月末日 > US 月末日时，CN train 月末仍 < CN test 月末（抓跨区日期混淆） |
| `test_shuffle_regime_neutralizes_interaction` | 随机打乱 regime → beta_interaction ≈ 0（抓 beta 恒非零的硬编码/退化） |
| `test_ic_series_currency_clean` | US IC 和 CN IC 分别计算后联合（抓"统一横截面 IC"跨币种污染） |
| `test_no_future_leakage_in_joint_fold` | 突变未来 close → 某 fold 的 test score 不变（复用 `build_cn_price_panel._leakage_self_check` 模式） |
| `test_determinism_same_sig_rerun` | 同输入两次跑 → oos_scores + IC 系列 bit-identical（H6） |

**强制**：每个测试用**真实结构对抗 fixture**（非小到触发 NaN-skip），且测**包装函数**（非仅被复用内核）。

---

## 6. 复用图（reuse-first；禁造轮子）

| 复用 | 新建 |
|---|---|
| `fit_track_b_baseline` 折逻辑（镜像，不 import 改） | `src/aionis/eval/track_c_joint.py`（`fit_track_c_joint` + `build_joint_panel`） |
| `ranking_contract.{fit_monthly_bins, transform_to_relevance, filter_valid_ranking_samples, get_group_sizes}` | 区域-月 group 构造（D1；新 helper，复用排序契约） |
| `rank_ic.{rank_ic_monthly, rank_ic_summary}` | per-region IC + 联合 IC（D2） |
| `regime_composite.regime_composite`（读 `regime_composite.parquet`） | conditional-IC 联合版（扩展逻辑，新 runner） |
| `cv.CVSplit` / `assert_chronological_split`（per-region 调用） | per-region chronological assert 包装 |
| `learner.LightGBMFrozen.fit_predict_rank`（#46 learner） | — |
| `metrics.diebold_mariano`（DM vs EW，H-1） | per-region DM（次要） |

**0 改动**：`track_b_baseline.py`、`cv.py`、`ranking_contract.py`、`learner.py`、`rank_ic.py`、frozen config/prereg/ADR/ledger。

---

## 7. owner-decision 旗标（confirmatory 前须签注）

| # | 决策 | 本 spec 推荐 | 为何需 owner |
|---|---|---|---|
| Q1 | lambdarank group 构造 | **区域-月**（D1） | #46 未冻结；影响估计量定义 |
| Q2 | 联合 rank-IC 聚合 | **区域内 IC 等权联合**（D2） | 同上 |
| Q3 | feature_cols（confirmatory） | 10 price（exploratory）；54 列 confirmatory | 需 cninfo + 新 ledger 行冻结 |
| Q4 | meso 层（依赖 Lane A） | 申万 PASS→3-layer；FAIL→US-only + spec 修订 | spec-faithful 性 |
| Q5 | confirmatory 跑（新 ledger 行 + GO） | 机器走通后 | OOS 观察 = owner 动作 |

**exploratory 机器走通（本 spec 范围）不触 Q1-Q5**——只用 D1/D2/D5 推荐默认 + 可得 regime，证明联合折叠 machinery 正确。confirmatory 判读交 owner。

---

## 8. 文件计划（新建，无冻结面改动）

```
src/aionis/eval/track_c_joint.py          # fit_track_c_joint + build_joint_panel + 区域-月 group
tests/test_track_c_joint.py               # 反退化测试（§5 全套）+ hermetic
scripts/track_c_joint_run.py              # exploratory runner（NO_LEDGER；产出 runs/track_c_joint_*）
（可选）scripts/track_c_conditional_ic_joint.py  # 联合 IC + 3-layer regime 条件化回归
```

全部新建；`gitignored` 产物进 `runs/`（不进 ledger）。`reports/design/2026-08-04-track-c-joint-fold-spec.md`（本文件）。

---

## 9. 验收（exploratory 机器走通 = done）

- [ ] `tests/test_track_c_joint.py` 全套反退化测试 PASS（§5 八项）。
- [ ] 全套 hermetic pytest 绿（零新增 skip/stub/TODO）；`ruff check` 干净。
- [ ] `fit_track_c_joint` 在真实 `track_b_panel` + `cn_price_panel` 上跑通（exploratory，NO_LEDGER），产出联合 IC 系列 + 条件化回归 beta/p（**作为机器正确性证据，非 confirmatory 判读**）。
- [ ] H6 两次跑 bit-identical。
- [ ] 0 冻结面/ledger/prereg/ADR 改动；0 真实网络（仅读本地 parquet）。
- [ ] 边界声明：未观察 confirmatory rank-IC 结论；未写 ledger；未触 E3。

---

## 10. 不越界声明（PROPOSED）

- `[F]` 本 spec 是设计文档；未运行 confirmatory/strategy/forward 脚本；未观察 E3；未写 ledger；未触 B/C/D/E1 + Track B 冻结面。
- `[F]` 估计量实现 = 新文件（`track_c_joint.py` + 测试 + runner），0 改动 frozen surface。
- `[I]` confirmatory 判读 = owner GO + 新 ledger 行（Q5）；spec 修订（meso / group 构造）= 新 prereg 段 + 新 ledger 行。
