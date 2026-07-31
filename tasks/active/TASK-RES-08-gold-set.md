# RES-08 — LLM-extractor eval: human gold-set construction (M; owner-gated)

- 编号: RES-08
- 状态: **HOLD — REPLAN REQUIRED into schema/sample/annotation/adjudication/freeze tasks**
- Priority: **P2**（审计 §11 P2 后续研究方向；§7 LLM 贡献与成本审计）
- Size: **M**（人工标注数据集构建；4-6 周工作量；需 owner 亲自参与）
- Risk: **HIGH**（人工标注质量决定 LLM ablation 可信度；无 gold set 无法评估）
- 建议 agent role / model tier: **Owner（亲自标注）→ Engineer（数据管理）→ Verifier（质量检查）→ Reviewer（文献对齐）**

## 目标 + 为什么重要

> 2026-08-01 planning correction: do not store durable annotations under gitignored `data/**`.
> The replacement design uses tracked `evals/cases/` records keyed by accession/source sha256 and
> text offsets, without redistributing filing text. RD-04/RD-05 must land before human annotation.

**目标**：构建 **人工标注的 13D/8-K 事件抽取 gold set**（至少 100 个 13D + 100 个 8-K 样本），每个样本包含 **事件文本、人工标注的 direction、mechanism_keyword、abstention 标记**，作为 LLM ablation 的评估基准。

**为什么重要**（审计发现）：
- 审计 §7.1：当前四条 headline **没有 LLM feature**；唯一真实 LLM 经验来自 Phase A（53 个 FOMC statement、GLM-4-flash）。
- 审计 §7.2：LLM 适合的职责包括 "闭集事件抽取：从明确 as-of 的 13D/8-K 原文提取实体、方向、机制和期限；允许 abstain"。
- 审计 §11 P2："[D] 建立人工 gold set 和 zero-LLM ablation；LLM 只处理新增闭集事件。"
- **无 gold set 无法评估**：precision、recall、coverage、abstention 均无法计算；LLM 贡献无法归因。

## 必须注册的新 trial

此任务完成后必须创建一个新的 trial registry entry：

```yaml
trial_id: LLM-GOLDSET-001
trial_family: llm-extractor-eval
type: exploratory-gold-set-construction
primary_parent: "E3 forward LLM edge extraction (Phase A pilot)"
config_sig: <sha256 of the gold set schema>
gold_set_spec:
  num_13d_samples: 100（最少；目标是 200+）
  num_8k_samples: 100（最少；目标是 200+）
  annotation_schema:
    - direction: {"positive", "negative", "neutral", "abstain"}
    - mechanism_keyword: <闭集关键词；如 "acquisition", "divestiture", "restructuring">
    - abstention_reason: null | "unclear" | "irrelevant" | "out_of_schema"
  annotator: "owner（亲自标注）"
  quality_control: "double-blind spot check（至少 20% 样本由第二 annotator 复核）"
universe: "13D filings + 8-K filings（PIT；2016-2024）"
n_jobs: N/A（人工标注）
random_seed: N/A
h6_determinism: N/A（人工标注非确定性；但最终 gold set 确定性）
status: "pending-owner-authorization"
registered_at: <timestamp of owner GO>
```

## 允许修改的文件

仅限以下文件的新增或修改：
- `data/gold_set/gold_set_schema.yaml`（新建 gold set schema 定义）
- `data/gold_set/13d_annotations.jsonl`（新建 13D 人工标注数据；**人工录入**）
- `data/gold_set/8k_annotations.jsonl`（新建 8-K 人工标注数据；**人工录入**）
- `src/aionis/extraction/gold_set_loader.py`（新建 gold set 加载模块）
- `tests/test_gold_set_loader.py`（新建单元测试；验证 schema 正确性）
- `docs/llm-extractor-eval.md`（新建文档；记录 gold set 构建 protocol）
- `.omc/plans/plan-res-08.md`（可选：实施计划草稿）

## 禁止修改的文件

- `runs/ledger.jsonl`
- `docs/phase-*-preregistration.md`
- `decisions/ADR-*.md`
- `scripts/phase_{b,c,d,e1,e3}_run.py`（禁止修改 frozen runner）
- `data/**`（除了 `data/gold_set/**` 子目录）
- `runs/results/**`
- `state/current.md`、`state/handoff.md`

## 前置条件（owner gate）

此任务在以下条件**全部满足**前必须保持 HOLD：
1. **Owner 明确书面承诺亲自标注**（state/handoff 或单独决策文档）：gold set 需要 owner 亲自参与标注或审核。
2. **ADR-010 冻结已生效**（已满足）。
3. **AUD-00 全部 P0 任务 COMPLETE**（当前部分完成；需等 AUD-01~05A APPROVE）。
4. **E3 commit-reveal 原语已完成**（Slice 1-5 已完成；当前满足）。
5. **可与其他 RES 并行**：不依赖其他 RES 任务（但优先级高于 S 任务）。

## 实施要求

### Phase 1: Schema 设计（1 周；Engineer）
1. **Gold Set Schema**：
   - 在 `data/gold_set/gold_set_schema.yaml` 中定义标注 schema。
   - **字段**：
     - `filing_id`: 唯一标识（CIK + accession_number）
     - `filing_type`: "13D" | "8-K"
     - `filing_date`: PIT filed date
     - `text`: 原始文本（截取 relevant sections；如 13D Item 4, 8-K Item 1.01/2.01/5.01）
     - `direction`: 人工标注 {"positive", "negative", "neutral", "abstain"}
     - `mechanism_keyword`: 人工标注 <闭集关键词>
     - `abstention_reason`: null | "unclear" | "irrelevant" | "out_of_schema"
     - `annotator`: "owner" 或其他 annotator ID
     - `annotation_date`: 标注日期
     - `quality_check`: boolean（是否经过第二 annotator 复核）
2. **闭集关键词定义**：
   - 参考 `docs/phase-e3-preregistration.md` 的 E3 edge schema。
   - **候选关键词**：acquisition, divestiture, restructuring, spinoff, buyback, guidance_change, management_change, etc.
3. **文档**：`docs/llm-extractor-eval.md` 记录：
   - gold set schema 定义。
   - 标注指南（如何判断 direction、如何选择 mechanism_keyword、何时 abstain）。
   - 质量控制流程（20% spot check + adjudication）。

### Phase 2: 样本选择（1 周；Engineer + Owner）
1. **样本池构建**：
   - 在 `src/aionis/extraction/gold_set_loader.py` 中实现 `select_gold_set_samples` 函数。
   - **13D 样本池**：从 2016-2024 的 13D filings 中随机抽取 200+ 候选（确保覆盖 diverse events）。
   - **8-K 样本池**：从 2016-2024 的 8-K filings 中随机抽取 200+ 候选（Item 1.01/2.01/5.01）。
   - **PIT 合规**：确保使用 EDGAR filed-date PIT；不使用未来修订。
2. **Owner 审批**：Owner 审批样本池（确保代表性；无 bias）。

### Phase 3: 人工标注（3-4 周；Owner 主导）
1. **标注工具**（简化；可手动编辑 JSONL）：
   - `data/gold_set/13d_annotations.jsonl`（新建；owner 逐行编辑）。
   - `data/gold_set/8k_annotations.jsonl`（新建；owner 逐行编辑）。
2. **标注流程**：
   - Owner 按照 `docs/llm-extractor-eval.md` 的指南标注。
   - **目标**：至少 100 个 13D + 100 个 8-K（更多更好）。
   - **质量控制**：20% 样本由第二 annotator（可由 owner 指定）复核；不一致 → adjudication。
3. **进度追踪**：Orchestrator 在 `state/handoff.md` 中记录标注进度（已完成 / 总目标）。

### Phase 4: Gold Set Loader（1 周；Engineer）
1. **加载模块**：
   - 在 `src/aionis/extraction/gold_set_loader.py` 中实现 `load_gold_set` 函数。
   - **输出**：pandas DataFrame（filing_id, text, direction, mechanism_keyword, abstention_reason）。
2. **单元测试**：`tests/test_gold_set_loader.py` 至少包含：
   - schema 验证测试（所有字段存在；direction/mechanism_keyword 在闭集内）。
   - abstention 统计测试（计算 abstention rate）。
   - 加载正确性测试（JSONL → DataFrame）。

### Verifier 职责
1. **Schema 正确性**：审查 `gold_set_schema.yaml` → 确认所有字段定义完整。
2. **PIT 合规**：确认样本池使用 EDGAR filed-date PIT；无 future leakage。
3. **质量控制**：确认 20% spot check 已完成；不一致已 adjudication。
4. **加载正确性**：运行 `uv run pytest tests/test_gold_set_loader.py -v` → **PASS**。
5. **禁用确认**：`git diff --name-only` → **禁止**出现 frozen 文件。

### Reviewer 职责
1. **Gold Set 文献对齐**：核实标注 schema 是否与 FinTagging、FinBen 等 LLM 抽取基准一致。
2. **标注质量合理性**：确认 abstention rate（预期 10-30%）、direction 分布（不应全部 positive）合理。
3. **不碰结果**：确认没有任何代码读取或写入 `runs/results/**`。
4. **owner gate 检查**：确认 owner 已亲自参与标注或审核。
5. **trial registry 准备**：验收时必须准备 YAML trial entry。

## 验收标准

- [ ] `docs/llm-extractor-eval.md` 包含完整的标注指南 + 质量控制流程。
- [ ] `data/gold_set/gold_set_schema.yaml` 定义完整；所有字段在闭集内。
- [ ] `data/gold_set/13d_annotations.jsonl` 包含 ≥100 个 13D 样本；每个样本有完整标注。
- [ ] `data/gold_set/8k_annotations.jsonl` 包含 ≥100 个 8-K 样本；每个样本有完整标注。
- [ ] **20% spot check 已完成**；不一致已 adjudication（记录在 `docs/llm-extractor-eval.md`）。
- [ ] `uv run pytest tests/test_gold_set_loader.py -v` → **PASS**。
- [ ] `git diff --name-only` → **仅**出现允许修改的文件。
- [ ] **owner 已亲自参与标注或审核**（handoff 记录）。
- [ ] **trial registry YAML 已准备**。

## 失败处理

1. **Owner 无法亲自标注**：**BLOCKED**；此任务依赖 owner 参与；无替代方案。
2. **Gold set 质量不合格**（如 abstention rate < 5% 或 > 50%）：**REQUEST CHANGES**；重新调整标注指南。
3. **PIT leakage 发现**：立即 **HOLD**；重新选择样本。
4. **禁用文件出现在 diff**：**BLOCKED**。

## 必须运行的测试

- `uv run pytest tests/test_gold_set_loader.py -v`
- `git diff --name-only`
- `git diff -- runs/ledger.jsonl docs/phase-*-preregistration.md decisions/ADR-*.md`（必须为空）

## 预期产物

1. **文档**：`docs/llm-extractor-eval.md`（标注指南 + 质量控制流程）
2. **Schema**：`data/gold_set/gold_set_schema.yaml`
3. **Gold set 数据**：
   - `data/gold_set/13d_annotations.jsonl`（≥100 个样本）
   - `data/gold_set/8k_annotations.jsonl`（≥100 个样本）
4. **代码**：`src/aionis/extraction/gold_set_loader.py`（加载模块）
5. **测试**：`tests/test_gold_set_loader.py`
6. **Trial registry YAML**（准备但**不写入 ledger**）

## 完成后需要更新

1. 本文件头部 `状态` 从 "owner-gated" 更新为 "completed"。
2. Orchestrator 更新 `state/handoff.md`，记录 gold set 构建完成。
3. 任务完成后移入 `tasks/completed/TASK-RES-08-gold-set.md`。

## 依赖顺序

```text
AUD-00 COMPLETE
├── AUD-01~05A COMPLETE
├── RES-01~03 (baseline ladder; S) → owner GO → COMPLETE（并行）
├── RES-04~07 (economic lens; S/M) → owner GO → COMPLETE（并行）
└── RES-08 (gold set; M) → owner 亲自参与 → Engineer → Verifier → Reviewer → COMPLETE（高优先级）
```

## See also

- `reports/audits/2026-07-31-quant-llm-research-audit.md` §7, §11 P2
- `decisions/ADR-010-sesoi-tost-sequential-gate.md`
- `docs/phase-e3-preregistration.md`（E3 edge schema 参考）
- FinTagging — LLM-ready XBRL Concept Tagging Benchmark
- FinBen — Financial NLP Benchmark
