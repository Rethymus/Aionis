# 轨道 A 可执行切片计划（把现有 null 做扎实并发表）

> **日期**：2026-08-02  
> **类型**：可执行切片计划（由编排者落盘至 `reports/design/2026-08-02-track-a-slice-plan.md`）  
> **状态**：规划建议；不修改任何冻结面/ledger；owner 决断后执行  
> **证据截止**：仓库 HEAD（commit `162702d`）

---

## 1. 目标与边界

### 1.1 轨道 A 的定位

轨道 A 是**近端、低成本、可发表**路径，与轨道 B（宽平台覆盖，90–140h）对照。核心价值：把"未完成的宽平台"转化为"已完成的窄贡献"。

**两大步**：
1. **chronological 再验证**：用已完成的 RD-03 chronological oracle，把 B/C/D/E1 从"shared-fold purged CV-proxy"升级到"expanding/rolling walk-forward"（train 严格早于 test）。不重跑、不改 ledger，只补一层更强证据。
2. **诚实写 null**：四条负 differential + CV-proxy 诚实措辞 + 治理方法论（config-before-result ledger / PIT / purged CV / H6），定位为"可复现 null benchmark + 反泄漏方法论"。

### 1.2 硬约束（反泄漏铁律）

- **不污染 B/C/D/E1**：新增 walk-forward 证据层作为**独立研究线**，新 config = 新 ledger row，绝不静默覆盖历史。
- **不改 frozen config/ledger**：所有 historical headline 保持原样；新增结果有独立 config/行。
- **复用优先**：RD-03（chronological oracle）、RD-14（reproducibility capsule）、RD-16（eval uncertainty）已就绪，直接复用。
- **H6 不变**：n_jobs=1，seed=0，version-pinned；walk-forward 的 IC 系列必须是 bit-identical。

### 1.3 不做什么

- 不跑 E3（STATISTICAL HOLD 已解除，但 live-input readiness 仍需 AUD-06 owner 决断）
- 不改 learner（仍用 MSE LightGBM；rank-objective 是轨道 B 的 S1）
- 不加量价特征（强基线 ladder 是轨道 B 的 S1）
- 不跑回测净成本（FINSABER 挂载是轨道 B 的 S1）

---

## 2. 切片计划

### 切片 A1：Chronological 再验证脚本（M，6–10h）

**目标**：用 RD-03 oracle 把 B/C/D/E1 重跑为 expanding/rolling walk-forward，产出 **train < test** 的更强证据层。

| 属性 | 说明 |
|---|---|
| **Size** | M（中等） |
| **工时估算** | 6–10h |
| **要创建的文件** | `scripts/track_a_chronological_revalidation.py`（新 runner）<br>`reports/results/track-a-walk-forward-evidence.md`（结果报告） |
| **要修改的文件** | 无（不改任何 frozen 面或 historical runner） |
| **复用的现有模块** | `src/aionis/eval/cv.py`（RD-03 已有 chronological oracle）<br>`src/aionis/eval/rank_ic.py`（IC 计算）<br>`src/aionis/eval/learner.py`（frozen LightGBM）<br>`src/aionis/reporting/save_run.py`（ledger append） |
| **验收标准** | ① 每条 phase 的 walk-forward IC 系列 bit-identical 两次（H6 验证）<br>② train 严格早于 test（max(train_idx) < min(test_idx)，由 RD-03 oracle 保证）<br>③ 新 ledger 行与 historical 隔离（新 config_sha256）<br>④ 四条 walk-forward differential 的点估计 + 95% HAC CI 报告<br>⑤ 不触发任何 E3/forward/real-network 路径 |
| **前置依赖** | RD-03 COMPLETE（commit `af7d673` 已就绪）<br>RD-14 COMPLETE（commit `f397383` 已就绪，用于 reproducibility capsule）<br>RD-16 COMPLETE（commit `ee223ae` 已就绪，用于 Wilson SE） |
| **反泄漏不变量** | ① config_committed BEFORE result（新 config 行先写）<br>② PurgedGroupKFold 替换为 walk-forward split（无 train-test 时间交叉）<br>③ group=month, embargo=21 保持不变<br>④ n_jobs=1, seed=0, version-pinned |

**实现要点**（由 Engineer 执行）：
```python
# 脚本骨架（示意；函数名已对齐 src/aionis/ 真实签名 2026-08-02）
from aionis.eval.cv import purged_walk_forward_splits, assert_chronological_split  # RD-03 oracle
from aionis.eval.learner import LightGBMFrozen
from aionis.eval.rank_ic import rank_ic_summary  # HAC SE/CI
from aionis.eval.two_arm import differential  # paired differential(ic_a, ic_b)（导入路径实施前核实）
from aionis.reporting.save_run import commit_config  # config_committed BEFORE result

# 1. 加载 frozen config（B/C/D/E1 各自的 historical config）
# 2. purged_walk_forward_splits(...)（expanding；assert_chronological_split 断言 max(train)<min(test)）
# 3. 对每个 walk-forward fold：train < test 严格保证
# 4. rank_ic_summary 算 HAC SE + 95% CI
# 5. commit_config 写新 ledger 行（独立 config_sha256，不污染历史）
```

**输出示例**（新 ledger 行）：
```json
{
  "config_sha256": "walk-forward-b-revalidation-v1",
  "phase": "B",
  "validation_method": "expanding_walk_forward",
  "min_train_months": 60,
  "n_walk_forward_folds": 65,
  "mean_differential": -0.000912,
  "hac_se": 0.0068,
  "ci_95": [-0.0143, 0.0125],
  "train_test_strict": true
}
```

---

### 切片 A2：Null 写作 + 治理方法论论文（L，12–20h）

**目标**：把四条 null differential + CV-proxy 诚实措辞 + anti-leakage 治理写成可发表文章，定位为"可复现 null benchmark + 方法论贡献"。

| 属性 | 说明 |
|---|---|
| **Size** | L（大） |
| **工时估算** | 12–20h |
| **要创建的文件** | `docs/track-a-null-methodology-paper.md`（主论文）<br>`docs/track-a-author-response.md`（潜在评审回应）<br>`reports/audits/track-a-chronological-evidence.md`（A1 结果审计） |
| **要修改的文件** | `docs/RESULTS.md`（添加 walk-forward 证据层摘要）<br>`README.md`（更新 abstract） |
| **复用的现有模块** | `docs/phase-*-preregistration.md`（四条 pre-reg）<br>`docs/RESULTS.md`（四条 historical differential）<br>`reports/audits/2026-07-31-quant-llm-research-audit.md`（审计证据）<br>`decisions/ADR-010-sesoi-tost-sequential-gate.md`（统计门，已修） |
| **验收标准** | ① 四条 historical differential 诚实表述（CV-proxy，非 chronological OOS）<br>② 治理方法论完整（config-before-result / PIT / purged CV / H6）<br>③ walk-forward 证据层作为"更强但仍未显著"的独立结果<br>④ 不夸大为"市场有效"或"严格等价"（遵守审计 §10.1 允许结论）<br>⑤ 引用格式完整（Pérignon et al. 复现率 / FINSABER / Alpha Illusion） |
| **前置依赖** | A1 COMPLETE（walk-forward 证据就绪）<br>审计 §11 P2 后续第 2 条（定位为 harness + null benchmark） |
| **反泄漏不变量** | ① Historical 结果不改写（只增加新证据层）<br>② 术语诚实（CV-proxy vs chronological OOS）<br>③ 不外推到"完整 S&P 500 / 可交易 / 无幸存者偏差" |

**论文结构**（由 Writer agent 起草）：
1. **Abstract**：null-first、可证伪、PIT-aware harness；四条 negative differential；治理方法论贡献。
2. **Introduction**：个人开发者约束；LLM-trading alpha 多为泄漏 artifact（引用 Look-Ahead-Bench / Profit Mirage）。
3. **Methods**：
   - 3.1 PIT contracts（EDGAR filed-date / ALFRED vintage / S&P constituents_on）
   - 3.2 PurgedGroupKFold（CV-proxy 设计，承认局限性）
   - 3.3 Walk-forward re-validation（A1 的新证据层）
   - 3.4 H6 determinism（n_jobs=1, seed=0, version-pinned）
   - 3.5 Config-before-result ledger（反静默覆盖）
4. **Results**：
   - 4.1 Historical CV-proxy results（四条负 differential，诚实措辞）
   - 4.2 Walk-forward re-validation（A1 的新证据，仍负但 train<test）
   - 4.3 Null 不是失败（引用 Altman & Bland / Lakens TOST）
5. **Discussion**：
   - 5.1 治理机器的成本与收益（ADR-010 Jennison-Turnbull 修正）
   - 5.2 与 Qlib/FINSABER 的生态定位（harness vs 策略）
   - 5.3 可复现 null 的价值（Pérignon et al. 复现率有限）
6. **Conclusion**：null 即成果；anti-leakage 方法论可迁移。

**关键词句模板**（遵守审计 §10.1）：
- ✅ 可写："在 frozen universe、九列基线、固定 MSE LightGBM、shared 5-fold purged grouped cross-fitting 下，B/C/D/E1 没有观察到显著正增量。"
- ✅ 可写："walk-forward re-validation（train 严格早于 test）仍未改变方向。"
- ❌ 禁写："市场已被证明有效"、"四条均通过严格等价检验"、"LLM 改善了四条 headline"。

---

### 切片 A3：SESOI/TOST 诚实化附录（S，3–5h）

**目标**：把 ADR-010 修正后的 Jennison-Turnbull 等价检验作为附录，展示"诚实但无必要地精修"的方法论态度。

| 属性 | 说明 |
|---|---|
| **Size** | S（小） |
| **工时估算** | 3–5h |
| **要创建的文件** | `docs/track-a-appendix-tost-jennison-turnbull.md`（附录） |
| **要修改的文件** | 无（只追加，不改 historical） |
| **复用的现有模块** | `decisions/ADR-010-sesoi-tost-sequential-gate.md`（已修正的 J-T 构造）<br>`src/aionis/eval/sesoi_gate.py`（已实现）<br>`reports/audits/e3-jt-amendment-proposal.md`（双 opus 审计） |
| **验收标准** | ① 解释 ADR-010 的 CRITICAL 修正（TOST p < αk 方向反了）<br>② 引入 Jennison-Turnbull 2000 理论（OBF zₖ, look-specific RCI）<br>③ 展示 RCIₖ ⊂ [−SESOI, +SESOI] 的严格包含判定<br>④ 说明这是"方法论附录"，不影响四条 historical differential |
| **前置依赖** | ADR-010 Amendment 2026-08-01（commit `12751c2`）<br>AUD-07B COMPLETE（双 opus 审计） |
| **反泄漏不变量** | ① 不用 TOST 结果重写 historical differential<br>② 承认 SESOI ±0.010 是事后选择，非原始预注册 |

**附录结构**：
1. 背景：为何要做等价检验（Altman & Bland："非显著 ≠ 无差异"）。
2. 原始 ADR-010 的 CRITICAL 缺陷（AUD-07B 发现的两点）。
3. Jennison-Turnbull 修正：
   - O'Brien-Fleming αₖ：zₖ = z_α/√Iₖ → (0.0052, 0.0158, 0.0437)
   - Look-specific RCI：(99.44%, 97.64%, 95.00%)
   - 严格包含判定：RCIₖ ⊂ [−SESOI, +SESOI]
4. 代码实现（`sesoi_gate.py` 的单元测试覆盖）。
5. 四条 differential 的 TOST 判定（演示，不改变结论）。

---

### 切片 A4：Dashboard 扩展（展示 walk-forward 证据）（S，2–4h）

**目标**：在现有 dashboard v2（commit `145f9b6`）基础上，增加 walk-forward 证据层的可视化。

| 属性 | 说明 |
|---|---|
| **Size** | S（小） |
| **工时估算** | 2–4h |
| **要创建的文件** | `dashboard/walk_forward_charts.py`（新 chart builder）<br>`dashboard/app_walk_forward.py`（独立 Streamlit 应用） |
| **要修改的文件** | 无（不修改 `dashboard/app_v2.py`） |
| **复用的现有模块** | `dashboard/charts_v2.py`（现有 plotly builders）<br>`dashboard/demo_data.py`（deterministic synthetic data） |
| **验收标准** | ① walk-forward IC 系列（时间序列，train-test 分界标记）<br>② expanding vs rolling window 对比<br>③ 四条 phase 的 walk-forward differential 条形图<br>④ 所有图表 deterministic（复用 demo_data 模式）<br>⑤ 独立应用（不污染现有 dashboard） |
| **前置依赖** | dashboard v2 COMPLETE（commit `145f9b6`）<br>A1 COMPLETE（walk-forward 数据就绪） |
| **反泄漏不变量** | ① 所有数据 deterministic（synthetic 或 historical frozen）<br>② 不触发任何 forward/real-network 路径 |

**实现要点**：
```python
# 新增 chart builder（示意）
def plot_walk_forward_ic(ic_series: pd.Series, train_test_splits: List[Tuple]):
    """绘制 walk-forward IC 系列，标记 train-test 分界"""

def plot_expanding_vs_rolling(df_ic: pd.DataFrame):
    """对比 expanding vs rolling window 的 IC 分布"""

def plot_four_phases_differential(df_results: pd.DataFrame):
    """四条 phase 的 walk-forward differential 条形图"""
```

---

## 3. 工时估算汇总

| 切片 | Size | 工时（h） | 依赖 | 优先级 |
|---|---|---|---|---|
| **A1** Chronological 再验证 | M | 6–10 | RD-03/14/16 COMPLETE | P0 |
| **A2** Null 写作 + 治理方法论 | L | 12–20 | A1 | P0 |
| **A3** SESOI/TOST 附录 | S | 3–5 | ADR-010 修正 | P1 |
| **A4** Dashboard 扩展 | S | 2–4 | A1 + dashboard v2 | P1 |
| **总计** | — | **23–39h** | — | — |

**与轨道 B 对比**（90–140h）：
- 轨道 A：23–39h（个位数到低双位数工时）
- 轨道 B：90–140h（S0 数据脊柱 + S1 强基线 + FINSABER 挂载 + 新闻情绪）

---

## 4. 与轨道 B 的对照表

| 维度 | 轨道 A（近端） | 轨道 B（宽覆盖） |
|---|---|---|
| **核心目标** | 把现有 null 做扎实并发表 | 覆盖七大主题（行情/宏观/基本面/新闻情绪/风险/回测/市场结构） |
| **主要产出** | 可复现 null benchmark + 反泄漏方法论 | 宽平台选股系统（S0→S1→S2） |
| **工时** | 23–39h | 90–140h |
| **可发表性** | 高（null + 方法论是稀缺贡献） | 中（需多期实验才能发表） |
| **风险** | 低（复用现有模块，不改历史） | 中高（新预注册线、数据合同、LLM 归因） |
| **复用程度** | 高（RD-03/14/16 直接复用） | 中（需 fork qlib、挂 FINSABER、建强基线） |
| **E3 参与** | 否（STATISTICAL HOLD 已解除但 live-input 仍需决断） | 是（E3 是 LLM 归因的唯一入口） |
| **数据源变更** | 否 | 是（S0 数据脊柱需完整验证） |
| **LLM 归因** | 否（四条 headline 是 zero-LLM） | 是（E3 闭集抽取 + zero-LLM ablation） |
| **回测净成本** | 否 | 是（FINSABER next-open / slippage / liquidity / capacity） |

---

## 5. 需 Owner 裁断的点

### 5.1 优先级排序

**问题**：轨道 A 与轨道 B 的启动顺序？
- 选项 A：先轨道 A（发表 null，建立方法论声誉），再轨道 B（宽平台）
- 选项 B：轨道 A 与轨道 B 并行（A2 写作与 B 的 S0 数据准备可并行）
- 选项 C：只轨道 A（暂停轨道 B，直到轨道 A 发表）

**建议**：选项 A（先发表，再宽平台）。理由：轨道 A 是"已完成窄贡献"，轨道 B 是"未完成宽平台"；先发表可降低机会成本。

### 5.2 Walk-forward 参数

**问题**：A1 的 walk-forward 参数选择？
- expanding window（每期加入新训练样本）vs rolling window（固定训练窗）
- min_train_months：60（5 年）vs 48（4 年）vs 72（6 年）
- 是否需要 sensitivity sweep（多种参数组合）

**建议**：expanding window + min_train_months=60（保守、与审计一致）；sensitivity 可选（P1）。

### 5.3 发表目标

**问题**：投稿目标？
- 选项 A：方法论文（Journal of Financial Econometrics / Quantitative Finance）
- 选项 B：复现期刊（Reprocibility @ ICML / NeurIPS）
- 选项 C：预印本
- 选项 D：GitHub README + tech blog

**建议**：先预印本 + README 扩展，再根据审稿反馈决定方法论文。Pérignon et al. 复现率有限是强动机。

### 5.4 SESOI/TOST 的必要声明

**问题**：是否在论文中声明 SESOI ±0.010 是"事后选择"（post-hoc）？
- 选项 A：明确声明（诚实但削弱"等价"主张）
- 选项 B：作为 sensitivity 分析（不作为主 claim）

**建议**：选项 A。审计 §5.1 已明确：预注册未钉 SESOI/TOST。诚实声明可避免审稿质疑。

---

## 6. 不越界声明

- 本计划**未运行任何 confirmatory/forward 脚本、未观察 E3 outcome、未改任何冻结面或 ledger**——符合当前 STATISTICAL/E3 HOLD（`state/handoff.md`）。
- 本计划是**切片建议**；owner 未裁决前，不构成项目方向变更。
- 轨道 A 的任何落地都是**新预注册 + 新 config + 新 ledger row**，绝不静默修改 B/C/D/E1。
- "可缓解不可根除"的幸存者偏差（无免费 Russell/退市 PIT 数据）依然成立（`docs/quant-selection-research.md` v0.2 §8.4）。

---

## 7. 引用

### 内部一手来源
- `reports/2026-08-02-strategic-review-coverage-and-alignment.md` — 轨道 A/B 双轨设计
- `reports/audits/2026-07-31-quant-llm-research-audit.md` — §5 统计与时间外推、§11 P0/P1 决策
- `docs/RESULTS.md` — 四条 null differential 现状
- `state/current.md` + `state/handoff.md` — RD-03/14/16 完成状态、AUD-07B CRITICAL 修正
- `decisions/ADR-010-sesoi-tost-sequential-gate.md` — Jennison-Turnbull 修正
- `docs/quant-selection-research.md` v0.2 — 轨道 B 蓝图

### 外部（引自审计 §14.2，不重复列全）
- Lakens et al. — 等价检验（TOST）
- Altman & Bland — "非显著不等于无差异"
- Jennison & Turnbull 2000 — Group-sequential equivalence
- Pérignon et al. — 复现率有限
- FINSABER — LLM-trading alpha 泄漏 artifact
