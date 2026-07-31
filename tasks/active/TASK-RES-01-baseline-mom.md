# RES-01 — Strong baseline ladder: characteristics expansion (S; owner-gated)

- 编号: RES-01
- 状态: **owner-gated — awaiting explicit authorization; DO NOT start without owner GO**
- Priority: **P2**（审计 §11 P2 后续研究方向；§4.2 基线不足）
- Size: **S**（单个特征族添加；2-3 周工作量）
- Risk: **MEDIUM**（新增特征但仅探索性；不触碰 frozen B/C/D/E1 结果）
- 建议 agent role / model tier: **Engineer (Sonnet) → Verifier (Sonnet) → Reviewer (Opus)**

## 目标 + 为什么重要

**目标**：在 Aionis 现有九列基本面基线基础上，增加 **momentum/reversal 特征族**（12 个月动量、1 个月反转、波动率调整动量），形成一个新的 baseline config，注册为 **BASELINE-MOM-001**。

**为什么重要**（审计发现）：
- 审计 §4.2：frozen `feature_cols` 只有 mktcap/pb_ratio/roa 和六项基本面，但 [phase-b-preregistration.md](../../docs/phase-b-preregistration.md) §2 描述两臂应共享 momentum/reversal/vol、FF5 和 DFF 宏观 — **这些特征从未进入 headline config**。
- 审计 §8.1：Gu, Kelly, Xiu (2018) GKX-94 特征包括 momentum、liquidity、volatility；当前弱基线使 differential 结论**无法外推到强基线环境**。
- 审计 §11 P2："[D] 新 config/new ledger row 才可加入强数值基线；不静默修改旧结果。"

## 必须注册的新 trial

此任务完成后必须创建一个新的 trial registry entry：

```yaml
trial_id: BASELINE-MOM-001
trial_family: baseline-ladder
type: exploratory-baseline-enhancement
primary_parent: "frozen Phase B (numeric fundamentals)"
config_sig: <sha256 of the new config file>
feature_addition:
  - momentum_12m: 12-month price momentum (累计回报)
  - reversal_1m: 1-month price reversal (短期反转)
  - vol_adj_mom: volatility-adjusted momentum (波动率调整动量)
objective: "regression" (保持与 B/C/D/E1 一致)
universe: "588 clean ticker PIT" (与 frozen 相同)
n_jobs: 1
random_seed: 0
h6_determinism: true
status: "pending-owner-authorization"
registered_at: <timestamp of owner GO>
```

**关键约束**：此 trial 是**新的 exploratory 基线增强**，必须由 owner 明确授权后才可写入 `runs/ledger.jsonl`。不得使用此 trial 静默修改 B/C/D/E1 的任何结果。

## 允许修改的文件

仅限以下文件的新增或修改：
- `src/aionis/features/momentum.py`（新建 momentum 特征计算模块）
- `src/aionis/features/volatility.py`（如需要，新建波动率计算）
- `scripts/phase_b_fetch.py`（如需添加新数据源 fetch，保持 politeness ≥2s）
- `scripts/res_01_baseline_mom_run.py`（新建 RES-01 专用 runner）
- `tests/test_momentum_features.py`（新建单元测试）
- `config/baseline_mom_001.yaml`（新建配置文件，记录特征列）
- `.omc/plans/plan-res-01.md`（可选：实施计划草稿）

## 禁止修改的文件（绝对禁止）

- `runs/ledger.jsonl`（禁止写入；必须由 owner 在授权后独立写入新 trial row）
- `docs/phase-*-preregistration.md`（禁止修改 frozen pre-registration）
- `decisions/ADR-*.md`（禁止修改 ADR）
- `src/aionis/eval/learner.py`（禁止修改 frozen LightGBM 配置）
- `scripts/phase_{b,c,d,e1}_run.py`（禁止修改 frozen runner）
- `data/**`、`runs/results/**`（禁止触碰任何数据或结果）
- `state/current.md`、`state/handoff.md`（仅 Orchestrator 可更新；本任务不触碰）

## 前置条件（owner gate）

此任务在以下条件**全部满足**前必须保持 HOLD：
1. **Owner 明确书面授权**（state/handoff 或单独决策文档）：允许启动 BASELINE-MOM-001 trial。
2. **ADR-010 冻结已生效**：SESOI/TOST/sequential gate 已冻结（已满足，ADR-010 2026-07-31 accepted）。
3. **AUD-00 全部 P0 任务 COMPLETE**：test entrypoint、chronology contract、source allowlist、factual reconciliation、HTTP policy primitive 均已 APPROVE（当前部分完成；需等 AUD-01~05A APPROVE）。

## 实施要求

### Engineer 职责（S 长度；2-3 周）
1. **特征实现**：在 `src/aionis/features/momentum.py` 中实现三个特征：
   - `momentum_12m`：过去 12 个月（不含当月）累计回报
   - `reversal_1m`：过去 1 个月回报（负值预期反转）
   - `vol_adj_mom`：momentum_12m / 过去 12 月回报标准差
2. **PIT 合规**：确保所有计算使用 **point-in-time 价格**（Tiingo next-open 或 Alpaca daily close；不得使用 yfinance/Stooq）。
3. **配置文件**：创建 `config/baseline_mom_001.yaml`，继承 frozen B 的 mktcap/pb_ratio/roa + 六项基本面，**新增**上述三列。
4. **Runner 脚本**：`scripts/res_01_baseline_mom_run.py` 只运行 **purged cross-fitted CV**（与 frozen B/C/D/E1 同等证据强度；不尝试 chronological walk-forward）。
5. **单元测试**：`tests/test_momentum_features.py` 至少包含：
   - 空值处理（缺失价格 → NaN）
   - PIT 边界测试（确保不使用未来数据）
   - 确定性测试（seed=0 下结果可复现）
6. **文档**：在 `docs/baseline-ladder.md`（新建）中记录特征定义、数据源、计算公式。

### Verifier 职责（只读证据收集）
1. **特征正确性**：运行 `uv run pytest tests/test_momentum_features.py -v` → 必须 **PASS**。
2. **PIT 不变性**：检查代码中的价格索引 → 确认无 `future leakage`（如使用 `shift(-1)` 或未来日期的 data）。
3. **配置隔离**：确认 `config/baseline_mom_001.yaml` 是**新文件**，未修改任何 frozen config。
4. **禁用确认**：`git diff --name-only` → **禁止**出现 `runs/ledger.jsonl`、`docs/phase-*-preregistration.md`、`decisions/ADR-*.md`。

### Reviewer 职责（diff + 风险评估）
1. **特征文献对齐**：核实 momentum/reversal 定义是否与 Gu, Kelly, Xiu (2018) 或经典因子文献一致。
2. **数据源合规**：确认只使用 Tiingo/Alpaca/EDGAR/FRED/ALFRED；**禁止** yfinance/Stooq/BLS。
3. **不碰结果**：确认没有任何代码读取或写入 `runs/results/**`、`data/**`。
4. **owner gate 检查**：确认 owner 已明确授权 BASELINE-MOM-001 trial（查阅 `state/handoff.md` 或 owner 决策文档）。
5. **trial registry 准备**：验收时必须准备上述 YAML trial entry，但**不写入 ledger**；写入是 owner 后续独立操作。

## 验收标准

- [ ] `uv run pytest tests/test_momentum_features.py -v` → **PASS**（所有单元测试通过）。
- [ ] `uv run ruff check src/aionis/features/momentum.py` → **clean**（无 lint 错误）。
- [ ] `git diff --name-only` → **仅**出现允许修改的文件；**禁止**出现 frozen 文件。
- [ ] `config/baseline_mom_001.yaml` 包含完整的特征列定义 + frozen 基线继承。
- [ ] `docs/baseline-ladder.md` 至少包含：特征定义、数据源、计算公式、PIT 合规说明。
- [ ] **owner 已明确授权** BASELINE-MOM-001 trial（授权记录在 `state/handoff.md` 或独立决策文档）。
- [ ] **trial registry YAML 已准备**（但不写入 ledger；写入由 owner 独立完成）。

## 失败处理

1. **单元测试 FAIL**：Engineer 修复；最多 2 轮；第 3 轮仍 FAIL → **BLOCKED**，交 owner 决策。
2. **PIT leakage 发现**：立即 **HOLD**；由 Architect 重新设计特征计算；禁止写入任何 runner 脚本。
3. **触碰 frozen 文件**：立即 **ROLLBACK** 所有改动；退回任务起点；重新冻结允许文件列表。
4. **Verifier 发现禁用文件在 diff 中**：**BLOCKED**；不得进入 Reviewer 环节。
5. **Reviewer 未发现 owner 授权**：**REQUEST CHANGES**；等待 owner 明确授权后重新 Review。

## 必须运行的测试

- `uv run pytest tests/test_momentum_features.py -v`（单元测试）
- `uv run ruff check src/aionis/features/momentum.py`（lint 检查）
- `git diff --name-only`（文件白名单检查）
- `git diff -- runs/ledger.jsonl docs/phase-*-preregistration.md decisions/ADR-*.md`（必须为空）

## 预期产物

1. **代码文件**：`src/aionis/features/momentum.py`（含三个特征函数）
2. **配置文件**：`config/baseline_mom_001.yaml`（新基线配置）
3. **Runner 脚本**：`scripts/res_01_baseline_mom_run.py`（仅 CV，不运行 confirmatory）
4. **单元测试**：`tests/test_momentum_features.py`（≥5 个测试用例）
5. **文档**：`docs/baseline-ladder.md`（特征定义 + PIT 合规）
6. **Trial registry YAML**（准备但**不写入 ledger**；写入由 owner 独立完成）

## 完成后需要更新

1. **任务状态**：本文件头部 `状态` 从 "owner-gated" 更新为 "completed"。
2. **Handoff**：Orchestrator 更新 `state/handoff.md`，记录：
   - BASELINE-MOM-001 trial 准备完成
   - 等待 owner 独立写入 ledger row
   - 下一步：RES-02（FF5 + 宏观特征）可并行启动
3. **移档**：任务完成后移入 `tasks/completed/TASK-RES-01-baseline-mom.md`。

## 依赖顺序

```text
AUD-00 (P0 coordination) COMPLETE
├── AUD-01~05A (P0 remediation) COMPLETE
└── RES-01 (baseline momentum) → owner GO → Engineer → Verifier → Reviewer → COMPLETE
```

## See also

- `reports/audits/2026-07-31-quant-llm-research-audit.md` §4.2, §8.1, §11 P2
- `docs/phase-b-preregistration.md` §2（应共享但未实现的特征）
- `decisions/ADR-010-sesoi-tost-sequential-gate.md`（statistical gate）
- Gu, Kelly, Xiu (2018) — Empirical Asset Pricing via ML (GKX-94 特征参考)
