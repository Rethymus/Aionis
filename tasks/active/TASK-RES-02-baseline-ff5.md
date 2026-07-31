# RES-02 — Strong baseline ladder: FF5 + DFF macro features (S; owner-gated)

- 编号: RES-02
- 状态: **HOLD — REPLAN REQUIRED; raw monthly FF5/DFF lacks cross-sectional variation and intake is unresolved**
- Priority: **P2**（审计 §11 P2 后续研究方向；§4.2 基线不足）
- Size: **S**（单个特征族添加；2-3 周工作量）
- Risk: **MEDIUM**（新增特征但仅探索性；不触碰 frozen B/C/D/E1 结果）
- 建议 agent role / model tier: **Engineer (Sonnet) → Verifier (Sonnet) → Reviewer (Opus)**

## 目标 + 为什么重要

> 2026-08-01 planning correction: this task must not be executed as written. Raw monthly FF5/DFF
> values are common to every security in a month and therefore cannot directly rank the cross-section.
> A replacement task must first define stock-specific rolling exposures/interactions, prove no
> same-month future use, pass `TASK-RD-13`, and separately clear French-data license/release/PIT intake.

**目标**：在 Aionis 现有九列基本面基线基础上，增加 **Fama-French 5 因子 + DFF 宏观特征**（MKTRF、SMB、HML、RMW、CMA + DFF 利差），形成一个新的 baseline config，注册为 **BASELINE-FF5-001**。

**为什么重要**（审计发现）：
- 审计 §4.2：frozen `feature_cols` 只有 mktcap/pb_ratio/roa 和六项基本面，但 [phase-b-preregistration.md](../../docs/phase-b-preregistration.md) §2 描述两臂应共享 momentum/reversal/vol、**FF5 和 DFF 宏观** — **这些特征从未进入 headline config**。
- 审计 §8.1：Gu, Kelly, Xiu (2018) GKX-94 特征包含 FF5；当前弱基线使 differential 结论**无法外推到包含 FF5 的环境**。
- 审计 §11 P2："[D] 新 config/new ledger row 才可加入强数值基线；不静默修改旧结果。"

## 必须注册的新 trial

此任务完成后必须创建一个新的 trial registry entry：

```yaml
trial_id: BASELINE-FF5-001
trial_family: baseline-ladder
type: exploratory-baseline-enhancement
primary_parent: "frozen Phase B (numeric fundamentals)"
config_sig: <sha256 of the new config file>
feature_addition:
  - MKTRF: Fama-French 5 因子 - 市场超额回报
  - SMB: Small Minus Big（规模因子）
  - HML: High Minus Low（价值因子）
  - RMW: Robust Minus Weak（盈利因子）
  - CMA: Conservative Minus Aggressive（投资因子）
  - DFF: DFF 利差（期限结构宏观数据）
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
- `src/aionis/ingest/ff5.py`（新建 FF5 数据获取模块）
- `src/aionis/ingest/macro_dff.py`（新建 DFF 宏观数据获取模块；或扩展现有 macro_surprise.py）
- `src/aionis/features/ff5.py`（新建 FF5 特征映射模块）
- `scripts/phase_b_fetch.py`（如需添加 FF5/DFF fetch；保持 politeness ≥2s）
- `scripts/res_02_baseline_ff5_run.py`（新建 RES-02 专用 runner）
- `tests/test_ff5_ingest.py`、`tests/test_macro_dff.py`（新建单元测试）
- `config/baseline_ff5_001.yaml`（新建配置文件，记录特征列）
- `.omc/plans/plan-res-02.md`（可选：实施计划草稿）

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
1. **Owner 明确书面授权**（state/handoff 或单独决策文档）：允许启动 BASELINE-FF5-001 trial。
2. **ADR-010 冻结已生效**（已满足，ADR-010 2026-07-31 accepted）。
3. **AUD-00 全部 P0 任务 COMPLETE**（当前部分完成；需等 AUD-01~05A APPROVE）。
4. **RES-01 可并行**：RES-01 和 RES-02 可并行启动（文件不重叠）。

## 实施要求

### Engineer 职责（S 长度；2-3 周）
1. **FF5 数据获取**：
   - 从 **French 数据库官方**（[http://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html](http://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html)）获取 FF5 日频数据。
   - **Politeness**：强制 `≥2s` 间隔；有界退避；失败时 fail closed。
   - **PIT 合规**：FF5 是发布日期（release date）而非 factor 形成日期；需使用 **as-of vintage** 或确保不使用未来数据。
2. **DFF 宏观获取**：
   - 从 **FRED**（ALFRED）获取 `DFF` 序列（联邦基金有效利率）。
   - 使用 **ALFRED vintages** 确保 point-in-time（参考 `src/aionis/ingest/macro_surprise.py` 的 ALFRED 模式）。
3. **特征映射**：在 `src/aionis/features/ff5.py` 中实现：
   - 按 CIK/ticker 将 FF5 日频映射到月频（月末值或月均值）。
   - 按 filing date 将 DFF 映射到月频（确保 PIT）。
4. **配置文件**：创建 `config/baseline_ff5_001.yaml`，继承 frozen B 的 mktcap/pb_ratio/roa + 六项基本面，**新增** MKTRF/SMB/HML/RMW/CMA/DFF 六列。
5. **Runner 脚本**：`scripts/res_02_baseline_ff5_run.py` 只运行 **purged cross-fitted CV**（与 frozen B/C/D/E1 同等证据强度）。
6. **单元测试**：
   - `tests/test_ff5_ingest.py`：验证 FF5 fetch 礼貌性、PIT 不变、无 future leakage。
   - `tests/test_macro_dff.py`：验证 DFF ALFRED vintage 正确性、PIT 合规。
7. **文档**：在 `docs/baseline-ladder.md` 中更新 FF5/DFF 数据源、PIT 合规说明。

### Verifier 职责（只读证据收集）
1. **数据源合规**：确认 FF5 来自 French 官方；DFF 来自 FRED/ALFRED；**禁止** yfinance/Stooq/BLS。
2. **Politeness 检查**：审查 fetch 代码是否强制 `≥2s` 间隔；是否有退避机制。
3. **PIT 不变性**：
   - FF5：确认使用 release date 而非 formation date；或使用 ALFRED vintage。
   - DFF：确认使用 ALFRED vintages；禁止使用当前修订后的序列。
4. **配置隔离**：确认 `config/baseline_ff5_001.yaml` 是**新文件**。
5. **禁用确认**：`git diff --name-only` → **禁止**出现 `runs/ledger.jsonl`、frozen 文件。

### Reviewer 职责（diff + 风险评估）
1. **FF5 文献对齐**：核实 FF5 定义是否与 Fama-French (2015) 一致。
2. **DFF PIT 合规**：确认 DFF 使用 ALFRED vintages；**禁止**使用当前修订序列（leakage）。
3. **数据源许可**：French 数据库是 **免费学术使用**；确认符合项目 permissive-only 规则。
4. **不碰结果**：确认没有任何代码读取或写入 `runs/results/**`、`data/**`。
5. **owner gate 检查**：确认 owner 已明确授权 BASELINE-FF5-001 trial。
6. **trial registry 准备**：验收时必须准备 YAML trial entry，但**不写入 ledger**。

## 验收标准

- [ ] `uv run pytest tests/test_ff5_ingest.py tests/test_macro_dff.py -v` → **PASS**。
- [ ] `uv run ruff check src/aionis/ingest/ff5.py src/aionis/features/ff5.py` → **clean**。
- [ ] `git diff --name-only` → **仅**出现允许修改的文件。
- [ ] `config/baseline_ff5_001.yaml` 包含完整的 FF5+DFF 特征列定义。
- [ ] `docs/baseline-ladder.md` 更新 FF5/DFF 数据源 + PIT 合规说明。
- [ ] **owner 已明确授权** BASELINE-FF5-001 trial。
- [ ] **trial registry YAML 已准备**（但不写入 ledger）。

## 失败处理

（同 RES-01；略）

## 必须运行的测试

- `uv run pytest tests/test_ff5_ingest.py tests/test_macro_dff.py -v`
- `uv run ruff check`（相关文件）
- `git diff --name-only`
- `git diff -- runs/ledger.jsonl docs/phase-*-preregistration.md decisions/ADR-*.md`（必须为空）

## 预期产物

1. **代码文件**：`src/aionis/ingest/ff5.py`、`src/aionis/ingest/macro_dff.py`、`src/aionis/features/ff5.py`
2. **配置文件**：`config/baseline_ff5_001.yaml`
3. **Runner 脚本**：`scripts/res_02_baseline_ff5_run.py`
4. **单元测试**：`tests/test_ff5_ingest.py`、`tests/test_macro_dff.py`
5. **文档**：`docs/baseline-ladder.md`（更新 FF5/DFF 部分）
6. **Trial registry YAML**（准备但**不写入 ledger**）

## 完成后需要更新

1. 本文件头部 `状态` 从 "owner-gated" 更新为 "completed"。
2. Orchestrator 更新 `state/handoff.md`，记录 BASELINE-FF5-001 trial 准备完成。
3. 任务完成后移入 `tasks/completed/TASK-RES-02-baseline-ff5.md`。

## 依赖顺序

```text
AUD-00 COMPLETE
├── AUD-01~05A COMPLETE
├── RES-01 (baseline momentum) → owner GO → Engineer → Verifier → Reviewer → COMPLETE
└── RES-02 (baseline FF5) → owner GO → Engineer → Verifier → Reviewer → COMPLETE（可与 RES-01 并行）
```

## See also

- `reports/audits/2026-07-31-quant-llm-research-audit.md` §4.2, §8.1, §11 P2
- `docs/phase-b-preregistration.md` §2（应共享但未实现的 FF5/DFF）
- `decisions/ADR-010-sesoi-tost-sequential-gate.md`
- Fama-French (2015) — A Five-Factor Asset Pricing Model
- French Data Library — [http://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html](http://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html)
