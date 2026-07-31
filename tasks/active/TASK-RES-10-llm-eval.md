# RES-10 — LLM-extractor eval: precision/recall/coverage/abstention reporting (S; owner-gated)

- 编号: RES-10
- 状态: **owner-gated — awaiting explicit authorization; DO NOT start without owner GO**
- Priority: **P2**（审计 §11 P2 后续研究方向；§7 LLM 贡献与成本审计）
- Size: **S**（评估指标实现；2-3 周工作量）
- Risk: **MEDIUM**（评估指标但仅探索性；不触碰 frozen B/C/D/E1 结果）
- 建议 agent role / model tier: **Engineer (Sonnet) → Verifier (Sonnet) → Reviewer (Opus)**

## 目标 + 为什么重要

**目标**：实现 **LLM 抽取评估指标**（precision、recall、coverage、abstention rate），使用 RES-08 的 gold set，形成一个新的 eval config，注册为 **EVAL-LLM-001**。

**为什么重要**（审计发现）：
- 审计 §7.1：当前四条 headline **没有 LLM feature**；唯一真实 LLM 经验来自 Phase A（53 个 FOMC statement、GLM-4-flash）。
- 审计 §7.2：LLM 适合的职责包括 "闭集事件抽取：从明确 as-of 的 13D/8-K 原文提取实体、方向、机制和期限；**允许 abstain**"。
- 审计 §11 P2："[D] 建立人工 gold set 和 zero-LLM ablation；LLM 只处理新增闭集事件。"
- 审计 §13 尚未解决的问题："E3 中有效、非空 13D/8-K 文本的月度覆盖、tie rate 和 abstention rate 是多少？"
- **无评估指标无法判断 LLM 质量**：precision/recall 决定 LLM 抽取是否可用；coverage 决定 LLM 的适用范围；abstention rate 决定 LLM 的诚实性。

## 必须注册的新 trial

此任务完成后必须创建一个新的 trial registry entry：

```yaml
trial_id: EVAL-LLM-001
trial_family: llm-extractor-eval
type: exploratory-evaluation
primary_parent: "RES-08 (gold set) + RES-09 (zero-LLM ablation)"
config_sig: <sha256 of the new config file>
evaluation_metrics:
  - precision_at_k: "LLM 抽取结果与 gold set 的一致性"
  - recall_at_k: "gold set 被 LLM 正确抽取的比例"
  - coverage: "LLM 对 13D/8-K 样本的非 abstain 比例"
  - abstention_rate: "LLM 返回 abstain 的比例"
  - schema_failure_rate: "LLM 返回超出闭集 schema 的比例"
gold_set_version: "LLM-GOLDSET-001"
llm_model: "GLM-4-flash（与 E3 frozen provider 相同）"
universe: "gold set samples（13D + 8-K）"
n_jobs: 1
random_seed: 0
h6_determinism: true（LLM 输出非确定性；但评估脚本确定性地调用 frozen LLM）
status: "pending-owner-authorization"
registered_at: <timestamp of owner GO>
```

## 允许修改的文件

仅限以下文件的新增或修改：
- `src/aionis/extraction/llm_evaluator.py`（新建 LLM 抽取评估模块）
- `config/eval_llm_001.yaml`（新建配置文件，指定评估参数）
- `scripts/res_10_eval_llm_run.py`（新建 RES-10 专用 runner）
- `tests/test_llm_evaluator.py`（新建单元测试）
- `docs/llm-extractor-eval.md`（更新评估指标说明）
- `.omc/plans/plan-res-10.md`（可选：实施计划草稿）

## 禁止修改的文件

- `runs/ledger.jsonl`
- `docs/phase-*-preregistration.md`
- `decisions/ADR-*.md`
- `scripts/phase_{b,c,d,e1,e3}_run.py`（禁止修改 frozen runner）
- `data/**`（除了 `data/gold_set/**` 已由 RES-08 创建）
- `runs/results/**`
- `state/current.md`、`state/handoff.md`

## 前置条件（owner gate）

1. **Owner 明确书面授权**：允许启动 EVAL-LLM-001 trial。
2. **ADR-010 冻结已生效**。
3. **AUD-00 全部 P0 任务 COMPLETE**。
4. **RES-08 (gold set) COMPLETE**：RES-10 **依赖** gold set（无 gold set 无法评估）。
5. **RES-09 (zero-LLM ablation) 不阻塞**：可并行。

## 实施要求

### Engineer 职责（S 长度；2-3 周）
1. **LLM Evaluator 模块**：
   - 在 `src/aionis/extraction/llm_evaluator.py` 中新建 `LLMEvaluator` 类。
   - **功能**：
     - 加载 RES-08 的 gold set（`data/gold_set/13d_annotations.jsonl` + `8k_annotations.jsonl`）。
     - 调用 frozen E3 的 LLM provider（GLM-4-flash；`src/aionis/extraction/providers.py`）对相同文本进行抽取。
     - 对比 LLM 输出与 gold set 标注。
2. **评估指标实现**：
   - **Precision@K**：`precision = (LLM 正确抽取数) / (LLM 非 abstain 抽取数)`。
     - "正确"定义：LLM 输出的 `direction` 和 `mechanism_keyword` 与 gold set **完全一致**。
   - **Recall@K**：`recall = (LLM 正确抽取数) / (gold set 非 abstain 样本数)`。
   - **Coverage**：`coverage = (LLM 非 abstain 抽取数) / (总样本数)`。
   - **Abstention Rate**：`abstention_rate = (LLM abstain 数) / (总样本数)`。
   - **Schema Failure Rate**：`schema_failure_rate = (LLM 返回超出闭集 schema 的数) / (总样本数)`。
3. **配置文件**：创建 `config/eval_llm_001.yaml`：
   - `gold_set_path: "data/gold_set"`
   - `llm_provider: "GLM-4-flash"`（与 E3 frozen 相同）
   - `llm_temperature: 0.0`（确定性；与 E3 frozen 相同）
   - `evaluation_metrics: ["precision", "recall", "coverage", "abstention_rate", "schema_failure_rate"]`
4. **Runner 脚本**：`scripts/res_10_eval_llm_run.py`：
   - 使用 `config/eval_llm_001.yaml`。
   - 加载 gold set → 调用 LLM → 计算指标 → 输出 JSON 报告。
   - **禁止**运行 confirmatory headline（仅 exploratory evaluation）。
5. **单元测试**：`tests/test_llm_evaluator.py` 至少包含：
   - precision/recall 计算正确性测试（已知 LLM 输出 + gold set → 验证指标）。
   - coverage/abstention_rate 计算正确性测试。
   - schema failure 检测测试（LLM 返回超出闭集 → 标记为 schema failure）。
6. **文档**：`docs/llm-extractor-eval.md` 更新：
   - 评估指标定义（precision、recall、coverage、abstention_rate、schema_failure_rate）。
   - 与 FinTagging/FinBen 基准的对齐说明。
   - 局限性：LLM 输出非确定性；但评估脚本使用 frozen provider/temperature 确保可复现。

### Verifier 职责
1. **评估指标正确性**：审查 `llm_evaluator.py` 的 precision/recall/coverage/abstention_rate 计算 → 确认公式正确。
2. **Gold Set 依赖检查**：确认 RES-08 的 gold set 文件存在（`data/gold_set/*.jsonl`）。
3. **LLM Provider Frozen**：确认使用 frozen E3 的 GLM-4-flash provider；**禁止**切换模型或参数。
4. **配置隔离**：确认 `config/eval_llm_001.yaml` 是**新文件**。
5. **H6 确定性**：运行 `uv run pytest tests/test_llm_evaluator.py -v` → **PASS**。
6. **禁用确认**：`git diff --name-only` → **禁止**出现 frozen 文件。

### Reviewer 职责
1. **评估文献对齐**：核实 precision/recall 定义是否与 FinTagging、FinBen 等 NLP 抽取基准一致。
2. **LLM 非确定性处理**：确认评估脚本使用 `temperature=0.0` 确保 LLM 输出可复现。
3. **不碰结果**：确认没有任何代码读取或写入 `runs/results/**`。
4. **owner gate 检查**：确认 owner 已明确授权 EVAL-LLM-001 trial。
5. **trial registry 准备**：验收时必须准备 YAML trial entry。

## 验收标准

- [ ] `uv run pytest tests/test_llm_evaluator.py -v` → **PASS**。
- [ ] `uv run ruff check src/aionis/extraction/llm_evaluator.py` → **clean**。
- [ ] `git diff --name-only` → **仅**出现允许修改的文件。
- [ ] `config/eval_llm_001.yaml` 指定评估参数 + gold set 路径。
- [ ] `docs/llm-extractor-eval.md` 更新评估指标说明 + 局限性。
- [ ] **RES-08 (gold set) COMPLETE**：gold set 文件存在且可加载。
- [ ] **owner 已明确授权** EVAL-LLM-001 trial。
- [ ] **trial registry YAML 已准备**。

## 失败处理

1. **RES-08 未 COMPLETE**：**HOLD**；等待 gold set 完成。
2. **Gold Set 无法加载**：**BLOCKED**；退回 RES-08 修复 gold set schema。
3. **LLM Provider 非 Frozen**：**BLOCKED**；禁止切换模型或参数。
4. **评估指标公式错误**：**REQUEST CHANGES**；Engineer 修复后重新 Verifier。
5. **禁用文件出现在 diff**：**BLOCKED**。

## 必须运行的测试

- `uv run pytest tests/test_llm_evaluator.py -v`
- `uv run ruff check`（相关文件）
- `git diff --name-only`
- `git diff -- runs/ledger.jsonl docs/phase-*-preregistration.md decisions/ADR-*.md`（必须为空）
- **Gold Set 加载测试**：`python -c "import json; json.load(open('data/gold_set/13d_annotations.jsonl'))"`（确保 RES-08 完成）

## 预期产物

1. **代码文件**：`src/aionis/extraction/llm_evaluator.py`（评估模块）
2. **配置文件**：`config/eval_llm_001.yaml`
3. **Runner 脚本**：`scripts/res_10_eval_llm_run.py`
4. **单元测试**：`tests/test_llm_evaluator.py`
5. **文档**：`docs/llm-extractor-eval.md`（更新评估指标）
6. **评估报告**（JSON 格式；`runs/eval/eval_llm_001.jsonl`；**非 confirmatory**；仅 exploratory）
7. **Trial registry YAML**（准备但**不写入 ledger**）

## 完成后需要更新

1. 本文件头部 `状态` 从 "owner-gated" 更新为 "completed"。
2. Orchestrator 更新 `state/handoff.md`，记录 EVAL-LLM-001 trial 准备完成。
3. 任务完成后移入 `tasks/completed/TASK-RES-10-llm-eval.md`。

## 依赖顺序

```text
AUD-00 COMPLETE
├── AUD-01~05A COMPLETE
├── RES-01~03 (baseline ladder; S) → owner GO → COMPLETE（并行）
├── RES-04~07 (economic lens; S/M) → owner GO → COMPLETE（并行）
├── RES-08 (gold set; M) → owner 亲自参与 → COMPLETE（RES-10 依赖此）
├── RES-09 (zero-LLM ablation; S) → owner GO → COMPLETE（与 RES-08 并行）
└── RES-10 (LLM eval; S) → owner GO → Engineer → Verifier → Reviewer → COMPLETE（依赖 RES-08）
```

## See also

- `reports/audits/2026-07-31-quant-llm-research-audit.md` §7, §11 P2, §13
- `decisions/ADR-010-sesoi-tost-sequential-gate.md`
- `docs/phase-e3-preregistration.md`（E3 LLM edge extraction 参考）
- FinTagging — LLM-ready XBRL Concept Tagging Benchmark（precision/recall 参考）
- FinBen — Financial NLP Benchmark（evaluation metrics 参考）
- `tasks/active/TASK-RES-08-gold-set.md`（gold set 依赖）
