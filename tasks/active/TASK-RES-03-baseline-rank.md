# RES-03 — Strong baseline ladder: rank-aware objective (S; owner-gated)

- 编号: RES-03
- 状态: **owner-gated — awaiting explicit authorization; DO NOT start without owner GO**
- Priority: **P2**（审计 §11 P2 后续研究方向；§4.2 目标函数错配）
- Size: **S**（单目标函数替换；2 周工作量）
- Risk: **MEDIUM**（目标函数变更但仅探索性；不触碰 frozen B/C/D/E1 结果）
- 建议 agent role / model tier: **Engineer (Sonnet) → Verifier (Sonnet) → Reviewer (Opus)**

## 目标 + 为什么重要

**目标**：在 Aionis 现有 MSE LightGBM 基线基础上，增加 **rank-aware objective**（如 `lambdarank`、`rank_net` 或 `rank_pairwise`），形成一个新的 baseline config，注册为 **BASELINE-RANK-001**。

**为什么重要**（审计发现）：
- 审计 §4.2：[learner.py](../../src/aionis/eval/learner.py) 使用 `objective="regression"`，而 primary 指标是 **Spearman rank-IC**。目标函数与评估指标**错配**。
- 审计 §8.1：Poh et al. (2021) "learning-to-rank" 显示横截面排序目标可优于回归后排序。
- 审计 §11 P2："[D] 新 config/new ledger row 才可加入强数值基线或 rank-aware objective；不静默修改旧结果。"

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
  to: "lambdarank"（或 "rank_net" / "rank_pairwise"）
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
- `src/aionis/eval/learner.py`（新增 rank-aware objective 选项；**不删除** frozen `"regression"` 分支）
- `config/baseline_rank_001.yaml`（新建配置文件，指定 `objective="lambdarank"`）
- `scripts/res_03_baseline_rank_run.py`（新建 RES-03 专用 runner）
- `tests/test_learner_rank_objective.py`（新建单元测试）
- `docs/baseline-ladder.md`（更新 rank-aware objective 说明）
- `.omc/plans/plan-res-03.md`（可选：实施计划草稿）

## 禁止修改的文件

- `runs/ledger.jsonl`
- `docs/phase-*-preregistration.md`
- `decisions/ADR-*.md`
- `scripts/phase_{b,c,d,e1}_run.py`（禁止修改 frozen runner）
- `data/**`、`runs/results/**`
- `state/current.md`、`state/handoff.md`

## 前置条件（owner gate）

1. **Owner 明确书面授权**：允许启动 BASELINE-RANK-001 trial。
2. **ADR-010 冻结已生效**。
3. **AUD-00 全部 P0 任务 COMPLETE**。
4. **RES-01/RES-02 可并行**：不依赖其他 RES 任务。

## 实施要求

### Engineer 职责（S 长度；2 周）
1. **Objective 扩展**：
   - 在 `src/aionis/eval/learner.py` 中新增 `objective="lambdarank"` 分支。
   - **保留** `objective="regression"` 分支（frozen B/C/D/E1 仍使用此分支）。
   - 确保 `lambdarank` 使用 **LightGBM 内置 ranking objective**（参考 [LightGBM ranking 文档](https://lightgbm.readthedocs.io/en/latest/Advanced-Topics.html)）。
2. **配置文件**：创建 `config/baseline_rank_001.yaml`：
   - `objective: "lambdarank"`
   - `feature_cols`：与 frozen B **完全相同**（mktcap/pb_ratio/roa + 六项基本面）。
3. **Runner 脚本**：`scripts/res_03_baseline_rank_run.py`：
   - 使用 `config/baseline_rank_001.yaml`。
   - 只运行 **purged cross-fitted CV**（与 frozen B/C/D/E1 同等证据强度）。
   - **禁止**运行 confirmatory headline（仅 exploratory）。
4. **单元测试**：`tests/test_learner_rank_objective.py` 至少包含：
   - `objective="lambdarank"` 模型初始化测试。
   - 输出 shape 正确性测试（ranking 模型输出 query/group 结构）。
   - H6 确定性测试（seed=0 下结果可复现）。
5. **文档**：`docs/baseline-ladder.md` 更新：
   - rank-aware objective 理论依据（Poh et al. 2021）。
   - LightGBM `lambdarank` 参数说明。
   - 与 frozen MSE 回归的区别。

### Verifier 职责
1. **Objective 正确性**：审查 `learner.py` 的 `lambdarank` 实现 → 确认使用 LightGBM 内置 ranking API。
2. **Frozen 分支保留**：确认 `objective="regression"` 分支**未被删除或修改**。
3. **配置隔离**：确认 `config/baseline_rank_001.yaml` 是**新文件**。
4. **H6 确定性**：运行 `uv run pytest tests/test_learner_rank_objective.py -v` → **PASS**。
5. **禁用确认**：`git diff --name-only` → **禁止**出现 frozen 文件。

### Reviewer 职责
1. **Ranking 文献对齐**：核实 `lambdarank` 定义是否与 LightGBM 官方文档一致。
2. **不碰结果**：确认没有任何代码读取或写入 `runs/results/**`。
3. **owner gate 检查**：确认 owner 已明确授权 BASELINE-RANK-001 trial。
4. **trial registry 准备**：验收时必须准备 YAML trial entry。

## 验收标准

- [ ] `uv run pytest tests/test_learner_rank_objective.py -v` → **PASS**。
- [ ] `uv run ruff check src/aionis/eval/learner.py` → **clean**。
- [ ] `git diff --name-only` → **仅**出现允许修改的文件。
- [ ] `config/baseline_rank_001.yaml` 指定 `objective="lambdarank"` 且 `feature_cols` 与 frozen B 相同。
- [ ] `docs/baseline-ladder.md` 更新 rank-aware objective 说明。
- [ ] **owner 已明确授权** BASELINE-RANK-001 trial。
- [ ] **trial registry YAML 已准备**。

## 失败处理

（同 RES-01；略）

## 必须运行的测试

- `uv run pytest tests/test_learner_rank_objective.py -v`
- `uv run ruff check`（相关文件）
- `git diff --name-only`
- `git diff -- runs/ledger.jsonl docs/phase-*-preregistration.md decisions/ADR-*.md`（必须为空）

## 预期产物

1. **代码文件**：`src/aionis/eval/learner.py`（新增 `lambdarank` 分支）
2. **配置文件**：`config/baseline_rank_001.yaml`
3. **Runner 脚本**：`scripts/res_03_baseline_rank_run.py`
4. **单元测试**：`tests/test_learner_rank_objective.py`
5. **文档**：`docs/baseline-ladder.md`（更新 ranking objective 说明）
6. **Trial registry YAML**（准备但**不写入 ledger**）

## 完成后需要更新

1. 本文件头部 `状态` 从 "owner-gated" 更新为 "completed"。
2. Orchestrator 更新 `state/handoff.md`，记录 BASELINE-RANK-001 trial 准备完成。
3. 任务完成后移入 `tasks/completed/TASK-RES-03-baseline-rank.md`。

## 依赖顺序

```text
AUD-00 COMPLETE
├── AUD-01~05A COMPLETE
├── RES-01 (baseline momentum) → owner GO → Engineer → Verifier → Reviewer → COMPLETE
├── RES-02 (baseline FF5) → owner GO → Engineer → Verifier → Reviewer → COMPLETE（与 RES-01 并行）
└── RES-03 (baseline rank) → owner GO → Engineer → Verifier → Reviewer → COMPLETE（与 RES-01/02 并行）
```

## See also

- `reports/audits/2026-07-31-quant-llm-research-audit.md` §4.2, §8.1, §11 P2
- `decisions/ADR-010-sesoi-tost-sequential-gate.md`
- Poh et al. (2021) — Building Cross-Sectional Systematic Strategies by Learning to Rank
- LightGBM Ranking Documentation — [https://lightgbm.readthedocs.io/en/latest/Advanced-Topics.html](https://lightgbm.readthedocs.io/en/latest/Advanced-Topics.html)
