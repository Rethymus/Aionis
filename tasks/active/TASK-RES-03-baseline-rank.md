# RES-03 — Strong baseline ladder: rank-aware objective (S; owner-gated)

- 编号: RES-03
- 状态: **REWRITTEN 2026-08-03 — rank-label contract defined; ready for owner authorization**
- Priority: **P2**（审计 §11 P2 后续研究方向；§4.2 目标函数错配）
- Size: **S**（单目标函数替换；2 周工作量）
- Risk: **MEDIUM**（目标函数变更但仅探索性；不触碰 frozen B/C/D/E1 结果）
- 建议 agent role / model tier: **Engineer (Sonnet) → Verifier (Sonnet) → Reviewer (Opus)**

## 目标 + 为什么重要

> 2026-08-03 rewrite（ORCH-RES-03）：本任务原因 "ranking label/query contract is undefined"
> 被 HOLD。2026-08-01 owner 已冻结 RD-15 决策包
> （`reports/design/2026-08-01-rd15-rank-objective-contract.md`），Engineer 已将其落地为
> 冻结实现 `src/aionis/eval/ranking_contract.py`。本文件按 ORCH-RES-03 契约重写，显式定义
> 排序标签来源、query-month 分组与标签构造函数（见下节「Ranking label/query 合约」），
> 恢复为可执行任务。合约内容以 RD-15 决策包 + `ranking_contract.py` 为准；日后如需修改
> 合约，走新决策流程（ADR），不在此任务内变更。

**目标**：在 Aionis 现有 MSE LightGBM 基线基础上，增加 **rank-aware objective**（LightGBM
内置 `lambdarank`），形成一个新的 baseline config，注册为 **BASELINE-RANK-001**。

**为什么重要**（审计发现）：
- 审计 §4.2：[learner.py](../../src/aionis/eval/learner.py) 使用 `objective="regression"`，而 primary 指标是 **Spearman rank-IC**。目标函数与评估指标**错配**。
- 审计 §8.1：Poh et al. (2021) "learning-to-rank" 显示横截面排序目标可优于回归后排序。
- 审计 §11 P2："[D] 新 config/new ledger row 才可加入强数值基线或 rank-aware objective；不静默修改旧结果。"

## Ranking label/query 合约（已冻结 — 权威来源：RD-15 决策包 + ranking_contract.py）

本任务的全部排序语义由以下冻结决策锚定。Engineer 实现**必须逐项调用**
`src/aionis/eval/ranking_contract.py` 的冻结 API，不得另起炉灶，也不得修改该文件。

### (a) 排序标签来源：前向收益 → 序数 relevance（非 rank-IC 目标）

- 训练标签 = **连续前向收益经序数转换后的 relevance 整数（1..5）**。rank-IC 只是评估指标，
  **不进入训练目标**。
- **Objective**（RD-15 决策 #1）：LightGBM 内置 `lambdarank`（lightgbm ≥ 4.3）。
  合法 objective 仅 `lambdarank` / `rank_xendcg`（`LightGBMRankingObjective` 枚举）；
  `rank_net` / `rank_pairwise` 不是合法 objective 名。本任务固定 `lambdarank`。
- **Bin count**（RD-15 决策 #2；owner 选定 quintiles）：`n_bins = 5`（五分位）。
  `ranking_contract.py` 校验 `n_bins ∈ {5, 10}`；本任务固定 5。
- **拟合范围**（RD-15 决策 #3）：**每个日历月在 train 折内单独**拟合分位 bin 边界
  （`fit_monthly_bins`），保留月内横截面排序并适应波动率体制；train 折无样本/无有效收益的
  月份回退 pooled 边界。
- **Ties**（RD-15 决策 #5）：相同收益 → 相同 relevance（分位分箱天然并列共享；无特殊处理）。
- **Missing**（RD-15 决策 #6）：前向收益 NaN 的样本 → relevance = -1 并**排除**
  （`filter_valid_ranking_samples`）；特征 NaN 由 LightGBM 默认处理。
- **Out-of-range**（RD-15 决策 #7）：test 折收益超出 train 折 [min, max] → **clamp 到最近
  bin（1 或 n_bins）+ 记录 reason code**（`oor_low` / `oor_high`）；**绝不重拟合 bin 边界**。
- **Reason codes**（RD-15 §5）：`NORMAL` / `RETURN_MISSING` / `OUT_OF_RANGE_LOW` /
  `OUT_OF_RANGE_HIGH` / `UNSEEN_MONTH_POOLED`，逐样本记录，供事后审计。

### (b) query-month 分组：每日历月 = 一个 query group

- **Group 定义**（RD-15 决策 #4）：每个日历月为一个 query group，`group_id = year * 12 +
  (month - 1)`（`construct_month_groups`），与「横截面月度 rank-IC」estimand 对齐；
  group 边界稳定，group 大小 == 该月行数。
- **LightGBM 接口**：`LGBMRanker` 需要 group sizes 而非 group ID（`get_group_sizes`，
  要求 group ID 有序）；过滤 NaN 样本后 **group sizes 必须同步更新**，否则训练失败。
- **Leakage 不变量**（RD-15 §7，须有单元测试）：month-permutation invariance、
  future-truncation invariance、train-fold-only fitting、group-size stability。

### (c) 标签构造函数（冻结实现逐项对应）

| 合约环节 | 冻结 API（`src/aionis/eval/ranking_contract.py`） | 行为 |
|---|---|---|
| train 折内每月分位边界 | `fit_monthly_bins(train_returns, train_groups, n_bins=5)` | 每月 `np.quantile(q=linspace(0, 1, 6))`；无有效样本/单行月份回退 pooled 边界；输入校验（非空、长度一致、n_bins ∈ {5,10}） |
| 冻结边界 → relevance | `transform_to_relevance(returns, groups, fitted_bins, n_bins=5)` | NaN → -1 / `return_missing`；越界 → clamp 到 1 或 5 + `oor_low`/`oor_high`；未见月份 → pooled 边界（各月拟合边界的均值）+ `unseen_pooled`；正常 → digitize 后 clip 到 [1, 5]；**绝不重拟合** |
| 排除无效样本 | `filter_valid_ranking_samples(returns, relevance, groups)` | 剔除 `relevance == -1` / NaN 收益样本，返回过滤后的 returns/relevance/groups；无有效样本时抛错 |
| objective 校验 | `validate_objective("lambdarank")` | 枚举白名单校验，非法 objective 名抛 ValueError |

Engineer 在 `learner.py` 中做 rank-aware 分支时，标签/分组构造只允许经过上述 API 链路：
`construct_month_groups` → `fit_monthly_bins` → `transform_to_relevance` →
`filter_valid_ranking_samples` → `get_group_sizes`。

## 必须注册的新 trial

此任务完成后必须创建一个新的 trial registry entry：

```yaml
trial_id: BASELINE-RANK-001
trial_family: baseline-ladder
type: exploratory-baseline-enhancement
primary_parent: "frozen Phase B (numeric fundamentals)"
config_sig: <sha256 of the new config file>
feature_change: null（特征列与 frozen B 相同）
objective_change:
  from: "regression (MSE)"
  to: "lambdarank"
rank_label_contract:  # RD-15 冻结合约（2026-08-01 owner decision）
  label_source: "forward return → ordinal relevance (quintiles, n_bins=5)"
  binning: "per-month quantiles, train-fold-only fitting"
  group: "query-month (group_id = year*12 + month-1)"
  ties: "share relevance"
  missing: "NaN forward return excluded"
  out_of_range: "clamp to nearest train-fold bin edge + reason code"
primary_metric: "Spearman rank-IC"（与 B/C/D/E1 一致）
universe: "588 clean ticker PIT"
n_jobs: 1
random_seed: 0
h6_determinism: true
status: "pending-owner-authorization"
registered_at: <timestamp of owner GO>
```

## 允许修改的文件

仅限以下文件的新增或修改：
- `src/aionis/eval/learner.py`（新增 rank-aware objective 选项；**不删除** frozen `"regression"` 分支；rank-aware 分支仅调用 `ranking_contract.py` 冻结 API）
- `config/baseline_rank_001.yaml`（新建配置文件，指定 `objective="lambdarank"`、`rank_bins: 5`）
- `scripts/res_03_baseline_rank_run.py`（新建 RES-03 专用 runner）
- `tests/test_learner_rank_objective.py`（新建单元测试；不变量测试见 `tests/test_ranking_contract.py`，本文件测试引用之）
- `docs/baseline-ladder.md`（新建/更新 rank-aware objective 说明）
- `.omc/plans/plan-res-03.md`（可选：实施计划草稿）

## 禁止修改的文件

- `runs/ledger.jsonl`
- `docs/phase-*-preregistration.md`
- `decisions/ADR-*.md`
- `scripts/phase_{b,c,d,e1}_run.py`（禁止修改 frozen runner）
- `src/aionis/eval/ranking_contract.py`（RD-15 **冻结实现**；修改需走新决策流程）
- `data/**`、`runs/results/**`
- `state/current.md`、`state/handoff.md`

## 前置条件（owner gate）

1. **Owner 明确书面授权**：允许启动 BASELINE-RANK-001 trial。
2. **RD-15 决策包已冻结**（2026-08-01 owner decision；`ranking_contract.py` 为其冻结落地实现）。
3. **ADR-010 冻结已生效**。
4. **AUD-00 全部 P0 任务 COMPLETE**。
5. **RES-01/RES-02 可并行**：不依赖其他 RES 任务。

## 实施要求

### Engineer 职责（S 长度；2 周）
1. **Objective 扩展**：
   - 在 `src/aionis/eval/learner.py` 中新增 `objective="lambdarank"` 分支（LightGBM `LGBMRanker`）。
   - **保留** `objective="regression"` 分支（frozen B/C/D/E1 仍使用此分支）。
   - 标签/分组构造走冻结 API 链路（见上节），并调用 `validate_objective("lambdarank")` 校验。
2. **配置文件**：创建 `config/baseline_rank_001.yaml`：
   - `objective: "lambdarank"`
   - `rank_bins: 5`（quintiles；RD-15 owner 选择）
   - `feature_cols`：与 frozen B **完全相同**（mktcap/pb_ratio/roa + 六项基本面）。
3. **Runner 脚本**：`scripts/res_03_baseline_rank_run.py`：
   - 使用 `config/baseline_rank_001.yaml`。
   - 只运行 **purged cross-fitted CV**（与 frozen B/C/D/E1 同等证据强度）。
   - **禁止**运行 confirmatory headline（仅 exploratory）。
4. **单元测试**：`tests/test_learner_rank_objective.py` 至少包含：
   - `objective="lambdarank"` 模型初始化测试。
   - 输出 shape 正确性测试（ranking 模型输出 query/group 结构；group sizes 与行数一致）。
   - H6 确定性测试（seed=0 下结果可复现）。
   - 标签合约测试：relevance ∈ 1..5、NaN 样本被剔除、越界样本 clamp + reason code 正确。
   - 引用/复用 `tests/test_ranking_contract.py` 中的 RD-15 §7 四个不变量（month-permutation /
     future-truncation / train-fold-only / group-size stability）。
5. **文档**：`docs/baseline-ladder.md` 新建/更新：
   - rank-aware objective 理论依据（Poh et al. 2021）。
   - LightGBM `lambdarank` 参数说明。
   - 与 frozen MSE 回归的区别。
   - 指向 RD-15 决策包与 `ranking_contract.py`。

### Verifier 职责
1. **Objective 正确性**：审查 `learner.py` 的 `lambdarank` 实现 → 确认使用 LightGBM 内置 ranking API。
2. **合约对齐**：确认 `n_bins=5`、group=query-month、train 折内拟合、clamp/reason code 与 RD-15 决策包及 `ranking_contract.py` 一致。
3. **Frozen 分支保留**：确认 `objective="regression"` 分支**未被删除或修改**。
4. **冻结实现未动**：`git diff -- src/aionis/eval/ranking_contract.py` → 为空。
5. **配置隔离**：确认 `config/baseline_rank_001.yaml` 是**新文件**。
6. **H6 确定性**：运行 `uv run pytest tests/test_learner_rank_objective.py -v` → **PASS**。
7. **禁用确认**：`git diff --name-only` → **禁止**出现 frozen 文件。

### Reviewer 职责
1. **Ranking 文献对齐**：核实 `lambdarank` 定义是否与 LightGBM 官方文档一致。
2. **不碰结果**：确认没有任何代码读取或写入 `runs/results/**`。
3. **owner gate 检查**：确认 owner 已明确授权 BASELINE-RANK-001 trial。
4. **trial registry 准备**：验收时必须准备 YAML trial entry。
5. **反泄漏复核**：relevance 构造严格 train-fold-only，无 test 折信息混入（含 bin 边界与 clamp 阈值）。

## 验收标准

- [ ] `uv run pytest tests/test_learner_rank_objective.py -v` → **PASS**。
- [ ] `uv run ruff check src/aionis/eval/learner.py` → **clean**。
- [ ] `git diff --name-only` → **仅**出现允许修改的文件。
- [ ] `git diff -- src/aionis/eval/ranking_contract.py` → 为空（冻结实现未被修改）。
- [ ] `config/baseline_rank_001.yaml` 指定 `objective="lambdarank"`、`rank_bins: 5` 且 `feature_cols` 与 frozen B 相同。
- [ ] 标签合约与 RD-15 决策包 + `ranking_contract.py` 逐项对应（label = 前向收益五分位 relevance；group = 日历月；ties 共享；NaN 排除；越界 clamp）。
- [ ] `docs/baseline-ladder.md` 新建/更新 rank-aware objective 说明。
- [ ] **owner 已明确授权** BASELINE-RANK-001 trial。
- [ ] **trial registry YAML 已准备**。

## 失败处理

（同 RES-01；略。补充：若实现过程中发现合约无法从 RD-15 决策包 / `ranking_contract.py`
完整落地，标记 **BLOCKED** 并回到决策流程，不得自行发明新合约。）

## 必须运行的测试

- `uv run pytest tests/test_learner_rank_objective.py -v`
- `uv run pytest tests/test_ranking_contract.py -v`（RD-15 §7 不变量）
- `uv run ruff check`（相关文件）
- `git diff --name-only`
- `git diff -- runs/ledger.jsonl docs/phase-*-preregistration.md decisions/ADR-*.md src/aionis/eval/ranking_contract.py`（必须为空）

## 预期产物

1. **代码文件**：`src/aionis/eval/learner.py`（新增 `lambdarank` 分支）
2. **配置文件**：`config/baseline_rank_001.yaml`
3. **Runner 脚本**：`scripts/res_03_baseline_rank_run.py`
4. **单元测试**：`tests/test_learner_rank_objective.py`
5. **文档**：`docs/baseline-ladder.md`（新建/更新 ranking objective 说明）
6. **Trial registry YAML**（准备但**不写入 ledger**）

## 完成后需要更新

1. 本文件头部 `状态` 更新为 "completed"（owner 授权并实施完成后）。
2. Orchestrator 更新 `state/handoff.md`，记录 BASELINE-RANK-001 trial 准备完成。
3. 任务完成后移入 `tasks/completed/TASK-RES-03-baseline-rank.md`。

## 依赖顺序

```text
RD-15 FROZEN (2026-08-01 owner decision; ranking_contract.py landed)
AUD-00 COMPLETE
├── AUD-01~05A COMPLETE
├── RES-01 (baseline momentum) → owner GO → Engineer → Verifier → Reviewer → COMPLETE
├── RES-02 (baseline FF5) → owner GO → Engineer → Verifier → Reviewer → COMPLETE（与 RES-01 并行）
└── RES-03 (baseline rank) → owner GO → Engineer → Verifier → Reviewer → COMPLETE（与 RES-01/02 并行）
```

## See also

- `reports/design/2026-08-01-rd15-rank-objective-contract.md`（RD-15 冻结决策包 — 本任务合约权威来源）
- `src/aionis/eval/ranking_contract.py`（冻结实现）
- `reports/audits/2026-07-31-quant-llm-research-audit.md` §4.2, §8.1, §11 P2
- `decisions/ADR-010-sesoi-tost-sequential-gate.md`
- Poh et al. (2021) — Building Cross-Sectional Systematic Strategies by Learning to Rank
- LightGBM Ranking Documentation — [https://lightgbm.readthedocs.io/en/latest/Advanced-Topics.html](https://lightgbm.readthedocs.io/en/latest/Advanced-Topics.html)
