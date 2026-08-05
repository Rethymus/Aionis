# Track C 首条 confirmatory GO — 业主签注包（PROPOSED v0.1，中文审阅稿）

> 状态：**PROPOSED · 2026-08-05 · opus Orchestrator 起草 · 业主审阅**。本包把 Track C 联合折叠从 exploratory 升格为 **首条 confirmatory** 所需的全部业主决策，收敛成一次性签注。**不写 ledger、不触冻结面、不跑 confirmatory**——这些都是签注后的业主动作或业主授权后的执行动作。
>
> 关联：prereg v1.0 [`docs/track-c-preregistration.md`](../../docs/track-c-preregistration.md)（FROZEN #46）+ 修 #47（cninfo→exploratory）+ 修 #48 PROPOSED（meso→US-only，[`2026-08-04-track-c-joint-fold-spec.md`](2026-08-04-track-c-joint-fold-spec.md) Lane A 裁定）+ joint-fold spec §7 Q1-Q5 + [`reports/audits/2026-08-04-evidence-integrity-audit.md`](../audits/2026-08-04-evidence-integrity-audit.md)（确认 0 confirmatory）。
>
> 取代：无（首版决策包）。修 #48 文本尚未起草，待 D5 签注后由我起草。

---

## 摘要

项目当前梯度：反泄漏纪律完备 ✅ / exploratory null 饱和 ✅ / chronological null 已达 ✅ / **confirmatory = 0** ❌。**唯一缺口 = 把 Track C 联合折叠 exploratory（combined IC −0.007, p=0.55，已在 gitignored artifact）升格为首条 confirmatory**。machinery 已建 + 9/9 反退化测试 + 真实双区面板跑通。升格 = 业主一次性签注 6 个决策 → 写修 #48 + 新 confirmatory config → `config_committed` ledger 行 → 跑 → J-T 等价门作用在交互项 rank-IC 差分序列。

**这是项目的 logical climax**：把"反泄漏纪律作为研究对象"从叙述变成一锤定音的可投稿 confirmatory 结果（null 或 reject 都可发表，因 null-favored + 两尾）。

---

## 1. 已就位（不需业主再决策）

| 项 | 状态 | 证据 |
|---|---|---|
| 联合折叠估计量代码 | ✅ COMMITTED `841fee4` | `src/aionis/eval/track_c_joint.py`（`fit_track_c_joint` + `build_joint_panel` + 区域-月 group + per-region 时序断言） |
| 反退化测试 | ✅ 9/9 绿 | `tests/test_track_c_joint.py`（H6 bit-identical 双跑、per-region 时序抓违反、区域-月 group 分离、单区拒绝） |
| 真实双区 exploratory 跑 | ✅ null | `runs/track_c_joint_summary.json`：combined IC −0.0070, CI [−0.030,+0.016], p_hac=0.55, n=71 月；US IC −0.002 / CN IC −0.014；conditional-IC β=−0.015 (p=0.20, R²=0.018) |
| meso Lane A 裁定 | ✅ CN 申万 G3 fail | [`2026-08-04-shenwan-meso-7gate.md`](2026-08-04-shenwan-meso-7gate.md)：baostock 无 as-of/vintage，SWFC 回填 → exploratory-only；**confirmatory meso = US-SIC only** |
| 治理 | ✅ ADR-012 + dispatch 协议 | 独立 verifier/reviewer 车道就位 |

**结论**：技术上没有任何阻塞；缺的只是业主对 6 个 spec 决策的签注。

---

## 2. 业主需签注的 6 个决策

### D1 — confirmatory 估计量定义（**核心歧义，必须先定**）

修 #47 把 claim 收窄为"US-rank-IC（确认性）+ A 股 exploratory 条件化"，但 #46 frozen 的估计量是"联合双区域折叠"。两者在 confirmatory 落地上有张力。**请选一：**

| 选项 | 定义 | 代价 / 收益 |
|---|---|---|
| **A（推荐）** | **保留联合折叠 machinery**；confirmatory claim = 双区域联合 rank-IC（null-favored 两尾）；A 股 fundamentals 因 #47 不进 confirmatory feature_cols（用 price + 宏观对称子集）；联合 IC = 区域内 IC 等权（D2 spec） | 收益：复用已建 machinery + 9/9 测试 + 已有 exploratory baseline；联合 = 更强检验（双区域数据）。代价：feature 不对称（US 23 / CN 12），需在 §6 边界诚实标注 |
| B | **claim 收窄为 US-only confirmatory**；joint-fold 降 exploratory；confirmatory 跑复用 Track B machinery on US 全特征（23 列） | 收益：claim 干净、feature 对称、power 更集中。代价：放弃已建 joint machinery + DY spillover 跨市场信号（regime global 层失去意义）；与 #46 frozen §5"联合折叠"冲突 → 需更大 spec 修订 |
| C | **延迟 confirmatory** 直到 cninfo fetch 实装，恢复全 54 列对称联合 | 收益：spec-faithful 全特征。代价：cninfo 实装 = 多周工程（反爬 + PDF 解析）；项目 climax 推迟；且 baostock 价格 G3 策略仍未冻结 |

**我推荐 A**：machinery 已沉没成本 + exploratory null 已知 + null-favored 下联合检验更强；feature 不对称是可披露的边界，非阻塞。B 的"放弃联合"与 frozen §5 冲突更大；C 的 cninfo 是独立大工程不应阻塞 climax。

### D2 — lambdarank group 构造（Q1）

- **推荐：区域-月**（`(year*12+month-1)*2 + region_code`，US 只与 US 排序、CN 只与 CN）。币种干净（区域内 label 同币种），模型仍联合 fit 共享参数。
- 否决替代：统一 calendar-month（跨币种 label 污染，方法学更弱）。
- 依据：joint-fold spec §3 D1 + §4 I5。

### D3 — 联合 rank-IC 聚合（Q2）

- **推荐：区域内 IC 等权联合**（每月 IC = mean(us_ic_t, cn_ic_t)）。避免统一横截面 IC 的跨币种相关。
- 依据：joint-fold spec §3 D2；exploratory 跑已用此式。

### D4 — confirmatory feature_cols（Q3，**含 #47 张力**）

因 #47（A 股 cninfo→exploratory），全 54 列落不齐。**confirmatory feature_cols 推荐收窄为双区域各自最大可得 spec-faithful 子集：**

| 类 | 列 | 来源 / PIT | 状态 |
|---|---|---|---|
| 美股基本面 (13) | roa, roe, profit_margin, asset_growth_{1m,12m}, revenue_growth_{1m,12m}, equity_growth_1m, leverage, debt_to_equity, book_value_per_share, accruals, investment_12m | EDGAR filed-date PIT | confirmatory ✅ |
| 美股价格 (10) | momentum_{5,10,21,42}d, reversal_5d, volatility_{21,63}d, turnover_21d, beta_252d, amihud_illiquidity_21d | Tiingo/Alpaca | confirmatory ✅ |
| A 股价格 (12) | 同美股 10 + limit_up_down_distance + suspension_flag | baostock raw（G3 策略 frozen 前提） | confirmatory ✅（价格交易所定→G3 低危） |
| A 股基本面 (13) | 镜像美股 13 | cninfo | **exploratory-only（#47）**，不进 confirmatory |
| 宏观 headline (6) | US: dff_surprise, term_spread, vix, credit_spread；CN: gdp_surprise, cpi_surprise | ALFRED/OECD vintage | confirmatory ✅ |
| regime 条件变量 (3) | meso_composite(US-SIC only) + macro_5line + global_dy_spillover | TACO as-of | confirmatory ✅（meso 已 US-only per D5） |

**per-stock confirmatory 列 = US 23 + CN 12 + 宏观 6 = 41**（+ 3 regime 条件化交互项，预算 1）。不对称（US 23 vs CN 12）—— LightGBM 默认处理缺失，CN 行的 US-fundamental 列 = missing。**替代**：双区域对称 price-only 10 列（更干净但丢弃 US fundamental signal，弱化检验）。**推荐 41 列不对称版**（保留 US fundamental 是 Track B 已验证的非泄漏信号）。

### D5 — meso 收窄 + 修 #48（Q4）

- **推荐：confirmatory meso = US-SIC only**（Lane A 裁定 CN 申万 G3 fail）；CN 申万降 exploratory。
- = 起草修 #48（prereg §1.1 meso 行改为"US-SIC headline + CN 申万 exploratory"）+ 新 ledger 行。
- spec §1.1 已留口（"EPU G3→exploratory"先例）。

### D6 — GO + 新 ledger 行（Q5）

- confirmatory 跑 = **业主 GO + 新 `config_committed` ledger 行**（= 业主动作，CLAUDE.md 惯例：我不擅自写 ledger 行或观察 confirmatory OOS）。
- 流程：业主签 D1-D5 → 我起草修 #48 文本 + 新 confirmatory config（41 列 + regime 3 + meso US-only）→ 业主授权 `config_committed` → 我执行首次 confirmatory OOS 跑 → J-T 门 → 沉积。

---

## 3. 签注后的执行流程（一次闭环，预计 1-2 个会话）

1. **我起草**（不需业主）：修 #48 文本（meso US-only + feature_cols 41 列）+ `scripts/track_c_confirmatory_commit.py`（复用 `track_c_commit.py` 的 `commit_config` 机制，纯 stdlib）。
2. **业主授权写 ledger 行**（业主动作）：`config_committed` phase=track_c，含 41 列 + regime 3 + meso US-only + Q1/Q2/Q3 冻结。sha256 自洽。
3. **我执行首次 confirmatory 跑**：`scripts/track_c_joint_run.py` 在全特征 41 列上（解除 exploratory 的 10 列限制）+ J-T 门（`eval/sesoi_gate.py`，已实现 `8/1`）作用在 `score × regime_state` 交互项的 rank-IC 差分序列。H6 双跑 bit-identical assert。
4. **沉积**：confirmatory 结果进 ledger `confirmatory:first` 行 + `docs/methods-and-results-draft.md` §5 占位升格为实填 + RESULTS.md。draft v0.1 → **v1.0 含首条 confirmatory**。

---

## 4. 风险与边界（诚实）

- **Power 风险**：双区域月末对齐窗 n=71 月；J-T looks {60,90,120} → 首次 look 60 月刚到，**第 2/3 look 需日历时间积累**（E3 forward-live 才能续）。首条 confirmatory 可能只达 look-1 等价判定（99.44% RCI）。这不是 bug，是月频研究的固有节奏，但 brief 应预期管理。
- **Feature 不对称**（D4 推荐版）：US 有 fundamental signal，CN 只有 price → 模型可能偏 US；联合 IC 的 CN 分量可能系统性弱。**缓解**：在 §6 边界明确 + 报告 per-region IC（exploratory 已显示 CN −0.014 vs US −0.002，差距小）。
- **baostock G3 复权策略未冻结**：D4 的 CN 价格列依赖 raw（adjustflag="3"，当前默认），但 confirmatory 前应在 config 显式冻结 G3 策略（raw + 本地因子快照）——**这是 D6 config 的必备字段，我会在起草时列入**。
- **null 仍是热门**：exploratory combined IC −0.007 + conditional-IC β=−0.015 (p=0.20) 均 null → confirmatory 大概率也是 null（= 可发表，符合 null-favored）。"结果不乐观再调整重测"在这里 = **null 不是"不乐观"**（null 是预期可发表产物）；只有工程 bug（H6 失败、per-region 时序违反、退化）才触发调整。

---

## 5. 不签注的代价（维持现状）

- 继续堆 exploratory 配置 = 边际信息增量零（handoff 8/4 已自判"饱和"）。
- draft v0.1 §5 confirmatory 占位永远空着 → 项目停在"反泄漏纪律完备 + 全 null 但 0 confirmatory"，可发表性 = 描述性（"我们试了一堆都 null"）而非推断性（"我们在预注册 J-T 门下确认等价"）。
- 17 commits 继续未 push，"治理 > 产出"失调持续。

---

## 6. 推荐一揽子（业主可回复"全部推荐"即开闸）

> **D1=A**（保留联合折叠）+ **D2=区域-月** + **D3=区域内 IC 等权** + **D4=41 列不对称** + **D5=meso US-only + 修 #48** + **D6=GO**。
>
> 或业主逐条修改任一项；我据反馈重起草修 #48 + config。

---

## 7. 不越界声明（PROPOSED）

- `[F]` 本包是决策文档；未写 ledger；未起草修 #48 文本（待 D5 签注）；未跑 confirmatory；未触 B/C/D/E1 + Track B 冻结面 / prereg / ADR / config。
- `[F]` 修 #48 + 新 config + `config_committed` ledger 行 = 签注后业主动作（D6）或业主授权后的执行动作。
- `[I]` D4 的 baostock G3 复权策略冻结、cninfo 实装时间表（若业主选 D1=C 延迟）、是否同步 push 17 commits，待业主指示。
