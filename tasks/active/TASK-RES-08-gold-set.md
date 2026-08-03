# RES-08 — LLM-extractor eval: human gold-set construction (M; owner-gated)

- 编号: RES-08
- 状态: **REWRITTEN 2026-08-03 — 5-stage durable gold-set; ready for owner authorization**
- Priority: **P2**（审计 §11 P2 后续研究方向；§7 LLM 贡献与成本审计）
- Size: **M**（人工标注数据集构建；4-6 周工作量；需 owner 亲自参与）
- Risk: **HIGH**（人工标注质量决定 LLM ablation 可信度；无 gold set 无法评估）
- 建议 agent role / model tier: **Owner（亲自标注）→ Engineer（数据管理）→ Verifier（质量检查）→ Reviewer（文献对齐）**

## 目标 + 为什么重要

> 2026-08-01 planning correction: do not store durable annotations under gitignored `data/**`.
> The replacement design uses tracked `evals/cases/` records keyed by accession/source sha256 and
> text offsets, without redistributing filing text. RD-04/RD-05 must land before human annotation.
>
> **2026-08-03 rewrite (ORCH-RES-08)**：本任务原为单一 monolithic 任务，无法作为可验证工件分步落地
> （root defect）。已重写为 5 个独立可验证阶段：schema → sample → annotation → adjudication →
> freeze（ADR-006 no-disposable-artifacts）。RD-04/RD-05 已落地：gold schema 已由
> `src/aionis/schema/gold_annotation.py`（`GoldCausalAnnotationV1`, `GOLD_SCHEMA_VERSION =
> "e3-causal-gold-v1"`）冻结，定义见 `docs/llm-extractor-eval.md` — **本任务直接复用该 schema，
> 不新建 schema 文件**。

**目标**：构建**人工标注的 13D/8-K 事件抽取 gold set**（至少 100 个 13D + 100 个 8-K 样本），每个样本包含**事件文本引用（sha256 + span）、人工标注的 direction、mechanism_keyword、abstention 标记**，作为 LLM ablation 的评估基准。

**为什么重要**（审计发现）：
- 审计 §7.1：当前四条 headline **没有 LLM feature**；唯一真实 LLM 经验来自 Phase A（53 个 FOMC statement、GLM-4-flash）。
- 审计 §7.2：LLM 适合的职责包括 "闭集事件抽取：从明确 as-of 的 13D/8-K 原文提取实体、方向、机制和期限；允许 abstain"。
- 审计 §11 P2："[D] 建立人工 gold set 和 zero-LLM ablation；LLM 只处理新增闭集事件。"
- **无 gold set 无法评估**：precision、recall、coverage、abstention 均无法计算；LLM 贡献无法归因。

## 结构（ADR-006：no-disposable-artifacts）

gold set 必须按 5 阶段分步构建，**每阶段独立可验证**，禁止跨阶段一次性交付。每阶段各自声明
**允许修改 / 禁止修改 / 验收标准 / 必须运行的测试**。

**全局禁止修改基线**（所有阶段适用，不再逐阶段重复）：`runs/ledger.jsonl`、
`docs/phase-*-preregistration.md`、`decisions/ADR-*.md`、`scripts/phase_{b,c,d,e1,e3}_run.py`
（frozen runner）、`runs/results/**`、`state/current.md`、`state/handoff.md`、`data/**`
（gitignored；gold 工件一律走 tracked `evals/cases/`，见 2026-08-01 planning correction）。

---

### 阶段 1: schema — 字段契约（版本化）

- **目标**：事件 / 来源 / 时间戳 / 标注字段的契约，版本化冻结。
- **复用（不新建）**：`docs/llm-extractor-eval.md` 已定义 gold schema — `GoldCausalAnnotationV1`
  （`src/aionis/schema/gold_annotation.py`, `GOLD_SCHEMA_VERSION = "e3-causal-gold-v1"`）。
  字段契约：`CausalEdge`（sector/direction/mechanism/horizon 闭集枚举，与 live LLM 契约共享防漂移）
  + `source_text_sha256`（64 位 hex）+ `source_span_start/end`（end > start）+ `filing_date`
  （EDGAR filed-date, **PIT**）+ `annotator_ids`（非空 / 有序 / 去重）+ `abstention_reason`
  （闭集：no_defensible_edge / insufficient_text / not_applicable / adjudication_pending）
  + `adjudicated`。**禁止字段**：ERL 自由文本、market impact、未来收益、模型预测。
  每条记录恰好两种状态之一：`CausalEdge` + `adjudicated=true`；或无边 + 非空 `abstention_reason`。
- **允许修改**：`src/aionis/schema/gold_annotation.py`（仅修契约缺口；已冻结字段变更 =
  **新版本号**，禁止静默修改）；`docs/llm-extractor-eval.md`（文档）。
- **禁止修改**：全局基线 + 其余一切文件。
- **验收标准**：版本号显式；字段契约完整覆盖 event / source / PIT timestamp / annotation；
  闭集枚举与 `CausalEdge` 一致；状态机（两种状态）唯一且由 schema 校验强制。
- **必须运行的测试**：`uv run pytest tests/test_gold_annotation_schema.py -v` → **PASS**；
  `uv run ruff check src/aionis/schema/`。
- **失败处理**：契约缺口需进一步研究 → 本阶段标记 **BLOCKED**；不允许带缺口进入阶段 2。

### 阶段 2: sample — 样本选择

- **目标**：选择准则；labeled-fixture 与 real 严格分区；PIT 时间戳；无结果泄漏。
- **选择准则**：13D + 8-K（Item 1.01/2.01/5.01），2016-2024，EDGAR filed-date **PIT**
  （不用未来修订）；每类 ≥200 候选 → ≥100 可用（目标 200+）。样本记录 = 引用
  （CIK + accession + `source_text_sha256` + span）；**不重分发文本**（SEC 公共领域
  17 U.S.C. §105 见 `docs/data-license-allowlist.md`，但最小化仍是最优）。
  **labeled-fixture**：合成 / 模拟样本仅作为带标签的单元测试 fixture（`tests/` 内，标注
  "fixture"），**永不进入 gold 集**（CLAUDE.md：mock 仅限 labeled unit-test fixtures）。
- **复用 RD-05**：`tests/test_gold_sampler.py` 已落地；sampler 实现在
  `src/aionis/extraction/gold_set_loader.py`（或 RD-05 指定模块）。
- **允许修改**：`src/aionis/extraction/gold_set_loader.py`（sampler 函数）、
  `tests/test_gold_sampler.py`、`evals/cases/`（样本 manifest，tracked）。
- **禁止修改**：全局基线；schema 文件（样本选择不得改变字段契约）。
- **验收标准**：manifest 含 accession + filed_date，全部 PIT（filed_date ≤ 标注日期）；
  无任何 future 数据；fixture / real 分区明确；Owner 审批样本池（代表性、无 bias）。
- **必须运行的测试**：`uv run pytest tests/test_gold_sampler.py -v` → **PASS**；
  PIT 断言；`git diff --name-only` → 仅允许范围。
- **失败处理**：PIT 泄漏发现 → 立即 **HOLD**，重选样本；准则需新研究 → 本阶段 **BLOCKED**。

### 阶段 3: annotation — 双标注协议

- **目标**：双标注协议 + 标注指南；inter-annotator agreement（IAA）目标。
- **协议**：每个样本由 **Owner 主标注**（按 `docs/llm-extractor-eval.md` 指南：direction 判定、
  mechanism 闭集选择、何时 abstain）；**≥20% 样本由第二 annotator 独立盲标**。
  **IAA 目标**：双标注子集上 direction / mechanism 的 Cohen's kappa **≥ 0.70**；
  abstention rate 预期 10-30%。
- **允许修改**：`evals/cases/13d_annotations.jsonl`、`evals/cases/8k_annotations.jsonl`
  （人工录入，tracked）、`docs/llm-extractor-eval.md`（指南修订）。
- **禁止修改**：schema 文件（标注数据必须通过 `GoldCausalAnnotationV1` 校验；
  **禁止为迁就数据改 schema**）；全局基线。
- **验收标准**：≥100 个 13D + ≥100 个 8-K 完整标注；每条记录通过 schema 校验；
  双标注子集 ≥20% 且已独立完成；进度由 Orchestrator 记入 `state/handoff.md`（已完成 / 总目标）。
- **必须运行的测试**：加载 + 全量校验（JSONL → `GoldCausalAnnotationV1`，0 失败）；
  IAA 计算；abstention rate 统计。
- **失败处理**：质量不合格（abstention <5% 或 >50%）→ **REQUEST CHANGES**，修订指南后重标。

### 阶段 4: adjudication — 分歧裁决

- **目标**：分歧解决；gold-verdict 规则。
- **规则**：双标注**一致** → 直接 gold；**不一致** → 独立第三人裁决（Owner 不裁决自己标注的
  样本）；裁决中 → `abstention_reason="adjudication_pending"` + `adjudicated=false`
  （**不可评估**，loader 不得输出为 gold）；裁决后 → `adjudicated=true`。
  裁决日志：`evals/cases/adjudication_log.jsonl`（分歧记录、裁决人、理由、日期）。
- **允许修改**：`evals/cases/adjudication_log.jsonl`、`evals/cases/*_annotations.jsonl`
  （仅状态 / 裁决字段翻转）。
- **禁止修改**：schema；已裁决记录的 direction / mechanism（裁决错误 = 新记录 + 勘误链，
  **禁止静默改写**）；全局基线。
- **验收标准**：冻结子集 **100% `adjudicated=true`**；无 `adjudication_pending` 残留；
  每项裁决可追溯（日志）。
- **必须运行的测试**：状态机测试（pending → resolved；pending 记录不得被 loader 输出为 gold）；
  全量无 pending 断言。
- **失败处理**：分歧率 >30% → 指南修订，该子集重标；裁决规则不可定 → 本阶段 **BLOCKED**。

### 阶段 5: freeze — 不可变快照

- **目标**：不可变快照 + sha256 + registry entry + H6。
- **步骤**：
  1. 生成不可变快照 `evals/gold_sets/goldset-e3-causal-gold-v1-<sha8>/`（含 manifest：
     每记录 `source_text_sha256` + 文件级 sha256）。
  2. 快照整体 sha256 = **config_sig**。
  3. **registry entry**：在 `evals/trials/` 注册 trial-intent manifest（RD-17 契约，
     `trial_id: LLM-GOLDSET-001`，`planned_config_sha256 = config_sig`，
     结果观察**前**注册；manifest 是规划工件，**不替代** config_committed ledger）。
  4. **H6**：同一快照两次加载位一致（断言）；任何变更 = **新快照版本**，已冻结快照只读。
- **允许修改**：`evals/gold_sets/`（仅新建快照）、`evals/trials/LLM-GOLDSET-001.json`
  （registry 条目）。
- **禁止修改**：已冻结快照文件（只读，不可变）；`runs/ledger.jsonl`（下游消费 gold 的 eval
  仍需在观察结果前按 config_committed 规则入 ledger）；全局基线。
- **验收标准**：快照含 sha256 manifest；registry 条目含 config_sig；加载器对同一快照
  双加载位一致。
- **必须运行的测试**：快照校验测试（sha256 全匹配）；H6 确定性断言（双加载位一致）；
  `git diff --name-only` → 仅允许范围。
- **失败处理**：sha256 不匹配 → 重建快照，**禁止带病冻结**。

---

## 必须注册的 trial（LLM-GOLDSET-001）

阶段 5 完成时向 `evals/trials/` 注册（RD-17 契约；结果观察前）：

```yaml
trial_id: LLM-GOLDSET-001
trial_family: llm-extractor-eval
type: exploratory-gold-set-construction
primary_parent: "E3 forward LLM edge extraction (Phase A pilot)"
config_sig: <sha256 of frozen gold snapshot (阶段 5)>
gold_set_spec:
  num_13d_samples: 100（最少；目标是 200+）
  num_8k_samples: 100（最少；目标是 200+）
  annotation_schema: "GoldCausalAnnotationV1 (e3-causal-gold-v1) — docs/llm-extractor-eval.md"
  quality_control: "双标注 ≥20% + IAA kappa ≥ 0.70 + adjudication"
  storage: "tracked evals/cases/ 记录（accession + source_text_sha256 + span）；不重分发文本"
annotator: "owner（亲自标注）"
universe: "13D filings + 8-K filings（PIT；2016-2024）"
n_jobs: N/A（人工标注）
random_seed: N/A
h6_determinism: "人工标注非确定性；冻结快照确定性（双加载位一致断言）"
status: "pending-owner-authorization"
registered_at: <timestamp of owner GO>
```

## 前置条件（owner gate）

此任务在以下条件**全部满足**前必须保持 HOLD：
1. **Owner 明确书面承诺亲自标注**（state/handoff 或单独决策文档）：gold set 需要 owner 亲自参与标注或审核。
2. **ADR-010 冻结已生效**（已满足）。
3. **AUD-00 全部 P0 任务 COMPLETE**。
4. **RD-04/RD-05 已落地**（gold schema 冻结 + gold sampler 测试 — **当前已满足**）；
   RD-04/RD-05 未落地前禁止进入阶段 3。
5. **E3 commit-reveal 原语已完成**（Slice 1-5 已完成；当前满足）。
6. **可与其他 RES 并行**：不依赖其他 RES 任务（但优先级高于 S 任务）。

## 失败处理

1. **Owner 无法亲自标注**：**BLOCKED**；此任务依赖 owner 参与；无替代方案。
2. **Gold set 质量不合格**（如 abstention rate < 5% 或 > 50%，或 IAA kappa < 0.70）：
   **REQUEST CHANGES**；重新调整标注指南。
3. **PIT leakage 发现**：立即 **HOLD**；重新选择样本。
4. **禁用文件出现在 diff**：**BLOCKED**。
5. **任一阶段无法在现有研究下定义 / 完成**：该阶段单独标记 **BLOCKED**，不阻塞其他阶段。

## 完成后需要更新

1. 本文件头部 `状态` 从 "REWRITTEN ..." 更新为 "completed"（全部 5 阶段验收通过后）。
2. Orchestrator 更新 `state/handoff.md`，记录 gold set 构建完成。
3. 任务完成后移入 `tasks/completed/TASK-RES-08-gold-set.md`。

## 依赖顺序

```text
AUD-00 COMPLETE
├── AUD-01~05A COMPLETE
├── RD-04 (gold schema 冻结) — 已落地 → 阶段 1 复用
├── RD-05 (gold sampler) — 已落地 → 阶段 2 复用
├── RES-08 阶段 1 (schema) → 阶段 2 (sample) → 阶段 3 (annotation, owner)
│   → 阶段 4 (adjudication) → 阶段 5 (freeze) → COMPLETE（高优先级）
└── 下游: LLM ablation eval（消费冻结 gold set，config_committed-before-result）
```

## See also

- `reports/audits/2026-07-31-quant-llm-research-audit.md` §7, §11 P2
- `decisions/ADR-006-no-disposable-artifacts-registry.md`（5 阶段结构的依据）
- `decisions/ADR-010-sesoi-tost-sequential-gate.md`
- `docs/llm-extractor-eval.md`（**gold schema 定义 + 标注指南入口**；阶段 1 复用）
- `src/aionis/schema/gold_annotation.py`（`GoldCausalAnnotationV1`, `e3-causal-gold-v1`）
- `tasks/active/TASK-RD-04-llm-gold-schema.md`、`tasks/active/TASK-RD-05-gold-sampler.md`
- `evals/trials/README.md`（RD-17 trial-intent registry 契约；阶段 5 注册）
- `docs/data-license-allowlist.md`（SEC 公共领域；annotations 为原创作品）
- `docs/phase-e3-preregistration.md`（E3 edge schema 参考）
- FinTagging — LLM-ready XBRL Concept Tagging Benchmark
- FinBen — Financial NLP Benchmark
