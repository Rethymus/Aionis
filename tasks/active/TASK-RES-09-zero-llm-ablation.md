# RES-09 — LLM-extractor eval: zero-LLM ablation (S; owner-gated)

- 编号: RES-09
- 状态: **owner-gated — awaiting explicit authorization; DO NOT start without owner GO**
- Priority: **P2**（审计 §11 P2 后续研究方向；§7 LLM 贡献与成本审计）
- Size: **S**（零 LLM 基线实现；2-3 周工作量）
- Risk: **MEDIUM**（零 LLM 基线但仅探索性；不触碰 frozen B/C/D/E1 结果）
- 建议 agent role / model tier: **Engineer (Sonnet) → Verifier (Sonnet) → Reviewer (Opus)**

## 目标 + 为什么重要

**目标**：实现 **zero-LLM ablation 基线**（不使用 LLM 提取 13D/8-K 事件特征），形成一个新的 config，注册为 **ABL-ZEROLLM-001**。

**为什么重要**（审计发现）：
- 审计 §7.1：当前四条 headline **没有 LLM feature**；唯一真实 LLM 经验来自 Phase A（53 个 FOMC statement、GLM-4-flash）。
- 审计 §11 P2："[D] 建立人工 gold set 和 **zero-LLM ablation**；LLM 只处理新增闭集事件。"
- **无 ablation 无法归因**：若不对比 zero-LLM 基线，无法证明 LLM 是否真正贡献增量信息。

## 必须注册的新 trial

此任务完成后必须创建一个新的 trial registry entry：

```yaml
trial_id: ABL-ZEROLLM-001
trial_family: llm-extractor-eval
type: exploratory-ablation
primary_parent: "E3 forward LLM edge extraction (Phase A pilot)"
config_sig: <sha256 of the new config file>
ablation_type: "zero-LLM"
feature_change:
  from: "LLM-extracted 13D/8-K direction + mechanism_keyword"
  to: "no LLM features（仅 frozen 基线特征）"
primary_metric: "rank-IC differential (zero-LLM vs frozen baseline)"
universe: "588 clean ticker PIT"
n_jobs: 1
random_seed: 0
h6_determinism: true
status: "pending-owner-authorization"
registered_at: <timestamp of owner GO>
```

## 允许修改的文件

仅限以下文件的新增或修改：
- `src/aionis/features/events.py`（新增 `zero_llm_features` 函数；**不删除**现有 LLM 分支）
- `config/abl_zerollm_001.yaml`（新建配置文件，指定 `use_llm=false`）
- `scripts/res_09_abl_zerollm_run.py`（新建 RES-09 专用 runner）
- `tests/test_zero_llm_ablation.py`（新建单元测试）
- `docs/llm-extractor-eval.md`（更新 zero-LLM ablation 说明）
- `.omc/plans/plan-res-09.md`（可选：实施计划草稿）

## 禁止修改的文件

- `runs/ledger.jsonl`
- `docs/phase-*-preregistration.md`
- `decisions/ADR-*.md`
- `scripts/phase_{b,c,d,e1,e3}_run.py`（禁止修改 frozen runner）
- `data/**`、`runs/results/**`
- `state/current.md`、`state/handoff.md`

## 前置条件（owner gate）

1. **Owner 明确书面授权**：允许启动 ABL-ZEROLLM-001 trial。
2. **ADR-010 冻结已生效**。
3. **AUD-00 全部 P0 任务 COMPLETE**。
4. **RES-08 (gold set) 不阻塞**：RES-09 不依赖 gold set；可并行（但 gold set 完成后可进一步评估 precision/recall）。

## 实施要求

### Engineer 职责（S 长度；2-3 周）
1. **Zero-LLM 特征**：
   - 在 `src/aionis/features/events.py` 中新增 `zero_llm_features` 函数。
   - **逻辑**：返回空的 13D/8-K 特征（`direction=None`, `mechanism_keyword=None`）或完全不调用 LLM。
   - **保留**现有 LLM 分支（frozen E3 仍使用 LLM；不做删除）。
2. **配置文件**：创建 `config/abl_zerollm_001.yaml`：
   - `use_llm: false`
   - `feature_cols`：与 frozen B/C/D/E1 **完全相同**（mktcap/pb_ratio/roa + 六项基本面；无 LLM 特征）。
3. **Runner 脚本**：`scripts/res_09_abl_zerollm_run.py`：
   - 使用 `config/abl_zerollm_001.yaml`。
   - 只运行 **purged cross-fitted CV**（与 frozen B/C/D/E1 同等证据强度）。
   - **禁止**运行 confirmatory headline（仅 exploratory）。
4. **单元测试**：`tests/test_zero_llm_ablation.py` 至少包含：
   - zero-LLM 特征正确性测试（确认不调用 LLM；特征为空或 None）。
   - H6 确定性测试（seed=0 下结果可复现）。
5. **文档**：`docs/llm-extractor-eval.md` 更新：
   - zero-LLM ablation 定义（不使用 LLM 提取特征）。
     - 与 frozen B/C/D/E1 的区别（B/C/D/E1 本身就没有 LLM；zero-LLM ablation 是更明确的"不调用 LLM"对照）。

### Verifier 职责
1. **Zero-LLM 逻辑正确性**：审查 `events.py` 的 `zero_llm_features` 实现 → 确认不调用 LLM。
2. **Frozen 分支保留**：确认现有 LLM 分支**未被删除或修改**。
3. **配置隔离**：确认 `config/abl_zerollm_001.yaml` 是**新文件**。
4. **H6 确定性**：运行 `uv run pytest tests/test_zero_llm_ablation.py -v` → **PASS**。
5. **禁用确认**：`git diff --name-only` → **禁止**出现 frozen 文件。

### Reviewer 职责
1. **Ablation 设计合理性**：核实 zero-LLM ablation 是否能有效对比 LLM 贡献（zero-LLM vs frozen baseline vs LLM-augmented）。
2. **不碰结果**：确认没有任何代码读取或写入 `runs/results/**`。
3. **owner gate 检查**：确认 owner 已明确授权 ABL-ZEROLLM-001 trial。
4. **trial registry 准备**：验收时必须准备 YAML trial entry。

## 验收标准

- [ ] `uv run pytest tests/test_zero_llm_ablation.py -v` → **PASS**。
- [ ] `uv run ruff check src/aionis/features/events.py` → **clean**。
- [ ] `git diff --name-only` → **仅**出现允许修改的文件。
- [ ] `config/abl_zerollm_001.yaml` 指定 `use_llm=false`。
- [ ] `docs/llm-extractor-eval.md` 更新 zero-LLM ablation 说明。
- [ ] **owner 已明确授权** ABL-ZEROLLM-001 trial。
- [ ] **trial registry YAML 已准备**。

## 失败处理

（同 RES-01；略）

## 必须运行的测试

- `uv run pytest tests/test_zero_llm_ablation.py -v`
- `uv run ruff check`（相关文件）
- `git diff --name-only`
- `git diff -- runs/ledger.jsonl docs/phase-*-preregistration.md decisions/ADR-*.md`（必须为空）

## 预期产物

1. **代码文件**：`src/aionis/features/events.py`（新增 `zero_llm_features` 函数）
2. **配置文件**：`config/abl_zerollm_001.yaml`
3. **Runner 脚本**：`scripts/res_09_abl_zerollm_run.py`
4. **单元测试**：`tests/test_zero_llm_ablation.py`
5. **文档**：`docs/llm-extractor-eval.md`（更新 zero-LLM ablation）
6. **Trial registry YAML**（准备但**不写入 ledger**）

## 完成后需要更新

1. 本文件头部 `状态` 从 "owner-gated" 更新为 "completed"。
2. Orchestrator 更新 `state/handoff.md`，记录 ABL-ZEROLLM-001 trial 准备完成。
3. 任务完成后移入 `tasks/completed/TASK-RES-09-zero-llm-ablation.md`。

## 依赖顺序

```text
AUD-00 COMPLETE
├── AUD-01~05A COMPLETE
├── RES-01~03 (baseline ladder; S) → owner GO → COMPLETE（并行）
├── RES-04~07 (economic lens; S/M) → owner GO → COMPLETE（并行）
├── RES-08 (gold set; M) → owner 亲自参与 → COMPLETE（高优先级）
└── RES-09 (zero-LLM ablation; S) → owner GO → COMPLETE（与 RES-08 并行）
```

## See also

- `reports/audits/2026-07-31-quant-llm-research-audit.md` §7, §11 P2
- `decisions/ADR-010-sesoi-tost-sequential-gate.md`
- `docs/phase-e3-preregistration.md`（E3 LLM edge extraction 参考）
- FinBen — Financial NLP Benchmark（LLM ablation 参考）
