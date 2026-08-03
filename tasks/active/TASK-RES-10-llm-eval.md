# RES-10 — LLM-extractor eval: precision/recall/coverage/abstention reporting (S; owner-gated)

- 编号: RES-10
- 状态: **REWRITTEN 2026-08-03 — anchored to RD-04/06/07/08/11; ready for owner authorization**
- Priority: **P2**（审计 §11 P2 后续研究方向；§7 LLM 贡献与成本审计）
- Size: **S**（runner + 报告 + 测试装配；指标/报告/基线/回放全部复用已完成 RD 产物）
- Risk: **MEDIUM**（评估指标但仅探索性；不触碰 frozen B/C/D/E1 结果）
- 建议 agent role / model tier: **Engineer (Sonnet) → Verifier (Sonnet) → Reviewer (Opus)**

## 目标 + 为什么重要

> 2026-08-01 planning correction（继续有效）：`temperature=0` 不使远程模型 API 位确定性。
> 可复现性必须用不可变原始响应 hash/cache + 冻结 parser/schema 的离线 replay（RD-11）承载。
> 本任务只消费 RD 产物与 ORCH-RES-08 的 gold set；不再从零 spec 任何指标或 schema。

**目标**：将 **LLM 抽取评估**（precision / recall / coverage / abstention）装配为可运行的探索性评估
EVAL-LLM-001：复用 RD-06 指标模块计分、RD-07 报告模块落盘、RD-08 zero-LLM 规则基线作对照、
RD-11 replay 作为上线前的解析稳定性闸门，gold 全部来自 ORCH-RES-08（RES-08 重写）的 5 阶段 gold set。

**为什么重要**（审计发现，与旧版一致）：
- 审计 §7.1：当前四条 headline **没有 LLM feature**；唯一真实 LLM 经验来自 Phase A（53 个 FOMC statement、GLM-4-flash）。
- 审计 §7.2：LLM 适合的职责包括 "闭集事件抽取：从明确 as-of 的 13D/8-K 原文提取实体、方向、机制和期限；**允许 abstain**"。
- 审计 §11 P2："[D] 建立人工 gold set 和 zero-LLM ablation；LLM 只处理新增闭集事件。"
- 审计 §13 尚未解决的问题："E3 中有效、非空 13D/8-K 文本的月度覆盖、tie rate 和 abstention rate 是多少？"
- **无评估指标无法判断 LLM 质量**：precision/recall 决定 LLM 抽取是否可用；coverage 决定 LLM 的适用范围；abstention rate 决定 LLM 的诚实性。

## 锚定图（binding）：每个指标/工件锚到已完成 RD 产物

本任务**不重新 spec 指标公式、schema、报告格式或规则**。一切以已 APPROVE/COMPLETE 的 RD 产物为准；
下表中任何一项无法锚定 ⇒ 该子项按「失败处理」标 **BLOCKED**，不得自行发明。

| 需求 | 锚定产物（均 COMPLETE） | 用法（只调用，不修改） |
|---|---|---|
| Gold record schema | **RD-04** `src/aionis/schema/gold_annotation.py` — `GoldCausalAnnotationV1`（`event_id`、`event_type`∈{13d,8k_2_02}、`filed_ts`、`source_text_sha256`、`causal_edges` 0/1、`abstention_reason`、`adjudicated`） | 只评估 `adjudicated=true` 记录；未裁决记录不得当 gold |
| Gold set 数据 | **ORCH-RES-08**（RES-08 5 阶段重写：schema→sample→annotation→adjudication→freeze）| 消费 freeze 阶段产物：tracked `evals/cases/` 标注（按 accession/source sha256 键控）+ 不可变快照 + sha256 + registry entry；**不用** `data/gold_set/**` |
| 指标计算 | **RD-06** `src/aionis/extraction/eval_metrics.py` — `evaluate_event` / `compute_metrics` / `evaluate_extraction`（`OverallMetrics`：n/tp/fp/fn/precision/recall/f1/coverage/abstention/invalid_schema/event_exact/per_field_accuracy/macro_by_event_type） | 唯一计分入口；edge identity = `(sic_sector, direction, mechanism_keyword, horizon_bucket)` 全 tuple；零分母输出 JSON null |
| 报告落盘 | **RD-07** `src/aionis/extraction/eval_report.py` — `build_report` / `write_report`（显式路径、原子写、默认拒绝覆盖、versioned JSON、provider/execution 元数据、输入 sha256） | 输出为不可静默覆盖的评估工件；**不写** `runs/ledger.jsonl` |
| Zero-LLM 对照 | **RD-08** `src/aionis/extraction/zero_llm_baseline.py` — `extract(text, event_id, event_type, ...)` 机械应用冻结规则表 `evals/expected/zero_llm_rules_v1.yaml`（rule id/provenance 溯源、表 sha256 写入输出、无 sentiment/market impact） | 与 LLM 臂同文本、同 gold 计分，形成对照臂 |
| 解析/回放稳定性 | **RD-11** `src/aionis/extraction/replay.py` — `replay_fixture` / `replay_directory` / `cache_key_stability_check`（合规 fixtures 离线回放；valid/invalid/truncated/extra-text/unknown-enum 确定 verdict；同输入 byte-identical） | 任何真实 provider 调用前先跑 replay 闸门；原始响应与 parser version sha256 进报告 |
| Trial 注册 | **RD-17** `src/aionis/reporting/trial_intent.py` + `evals/trials/README.md`（manifest 不含任何 observed metric；fail closed；**不替代** config_committed ledger） | EVAL-LLM-001 manifest 经 RD-17 validator 注册 |

**指标协议（对比协议，binding）**：同一 gold set、同一原文文本，两个臂各计分一次——
1. **LLM 臂**：frozen E3 provider（GLM-4-flash；`src/aionis/extraction/providers.py`）抽取 → RD-06 `evaluate_extraction`。
2. **Zero-LLM 臂**：RD-08 `extract()` 同文本抽取 → 同一 RD-06 计分。
3. 报告出两臂并列指标（precision / recall / F1 / coverage / abstention / invalid_schema / event_exact / per-field accuracy / macro-by-event_type），差异只以 `Δ = LLM − zero-LLM` 表述，**不允许**把 LLM 臂单点数值写成有效性结论。
4. 全程**禁止 LLM-as-judge**；abstain 策略即 RD-04 闭集 `abstention_reason` 枚举。
5. 每个指标分母/定义以 RD-06 docstring 为准，本文件不再复制公式。

## 必须注册的新 trial（经 RD-17，非自造格式）

`evals/trials/EVAL-LLM-001.yaml`（新建 manifest，经 `register_trial_id()`/validator 校验）：

```yaml
trial_id: EVAL-LLM-001
trial_family: llm-extractor-eval
type: exploratory-evaluation
owner_decision_ref: "RES-10 rewrite 2026-08-03 (owner-authorized)"
planned_config_sha256: <sha256 of config/eval_llm_001.yaml>
validation_kind: <见下方 BLOCKED 项 — RD-17 仅有 chronological/purged_cross_fit>
estimand: other        # extraction quality, not IC; 描述放 metadata
n_trials_accounting: 1
status: planned
```

- manifest 只声明意图与 hash，**不得携带任何 observed metric 字段**（RD-17 fail-closed 强制）。
- 本任务不产生 confirmatory 结果 ⇒ **不写** `runs/ledger.jsonl`；RD-17 manifest 不构成 config_committed。
- **BLOCKED 子项（注册前需决策）**：RD-17 `ValidationKind` 枚举仅 `chronological`/`purged_cross_fit`，
  探索性抽取评估两者皆非。注册 EVAL-LLM-001 前需 owner 决策：扩展 RD-17 枚举（新增 exploratory 类，
  另开 owner-gated task）或经 owner 书面豁免并用 `other` 注明。**此子项 BLOCKED，不阻塞指标装配，只阻塞 registry 写盘**。

## 允许修改的文件

- `scripts/res_10_eval_llm_run.py`（新建 runner：replay 闸门 → 加载 gold → 双臂抽取 → RD-06 计分 → RD-07 双报告）
- `config/eval_llm_001.yaml`（新建评估配置：gold set 路径、provider=GLM-4-flash、指标键表、报告路径）
- `tests/test_res_10_eval_llm.py`（新建测试；**只用** labeled fixtures，不调真实模型）
- `docs/llm-extractor-eval.md`（更新：指标锚定到 RD-06、对照协议、EVAL-LLM-001 说明；RD-04 已在此维护 schema 段）
- `evals/trials/EVAL-LLM-001.yaml`（新建 trial-intent manifest，见上）
- `.omc/plans/plan-res-10.md`（可选：实施计划草稿）

## 禁止修改的文件

- RD 产物本身：`src/aionis/extraction/eval_metrics.py`、`eval_report.py`、`zero_llm_baseline.py`、
  `replay.py`、`src/aionis/schema/gold_annotation.py`、`src/aionis/reporting/trial_intent.py`
  （已 COMPLETE；本任务只调用，改它们需新 owner-gated task）
- `evals/expected/zero_llm_rules_v1.yaml`（frozen 规则表；Engineer 无权新增/改规则）
- `src/aionis/extraction/providers.py`（frozen provider catalog/client/router）
- `runs/ledger.jsonl`、`docs/phase-*-preregistration.md`、`decisions/ADR-*.md`
- `scripts/phase_{b,c,d,e1,e3}_run.py`（frozen runner）
- `data/**`、`runs/results/**`、`state/current.md`、`state/handoff.md`

## 前置条件（owner gate）

1. **Owner 明确书面授权**：允许启动 EVAL-LLM-001 trial。
2. **ADR-010 冻结已生效**。
3. **ORCH-RES-08（RES-08 5 阶段重写）执行完成**：gold set freeze 产物（`evals/cases/` 标注 +
   不可变快照 + sha256）存在且 `adjudicated=true` 记录可加载。**RES-10 依赖此**（无 gold 无法评估）。
4. **RD-17 ValidationKind 扩展决策**（上节 BLOCKED 子项）——不阻塞装配，阻塞 registry 写盘。
5. 不依赖 RES-09（zero-LLM ablation 已由 RD-08 基线承载，本任务即其对照臂）。

## 实施要求

### Engineer 职责（S 长度）
1. **Runner 装配**（`scripts/res_10_eval_llm_run.py`）：
   - 先跑 **RD-11 replay 闸门**（`replay_directory` + `cache_key_stability_check`）→ 全 PASS 才允许真实 provider 调用；
     失败则中止并输出 replay 报告，不进入抽取。
   - 加载 ORCH-RES-08 gold set（仅 `adjudicated=true`；schema 校验走 RD-04 `GoldCausalAnnotationV1`）。
   - **LLM 臂**：frozen E3 provider（GLM-4-flash；providers.py）对相同原文抽取 → RD-06 `evaluate_extraction`。
   - **Zero-LLM 臂**：RD-08 `extract()` 对相同原文抽取 → 同一 RD-06 计分。
   - **报告**：两臂各经 RD-07 `build_report` / `write_report` 落盘（显式路径、拒绝覆盖、含 provider/execution
     元数据与输入 sha256）；LLM 臂另含原始响应 hash 与 parser version。
   - **禁止**运行 confirmatory headline（仅 exploratory evaluation）；不写 ledger。
2. **配置文件**：`config/eval_llm_001.yaml` 只引用冻结值：`gold_set_path`（ORCH-RES-08 freeze 产物）、
   `llm_provider: "GLM-4-flash"`、`llm_temperature: 0.0`、`metrics: [precision, recall, f1, coverage,
   abstention, invalid_schema, event_exact, per_field_accuracy, macro_by_event_type]`、报告路径。
3. **单元测试**：`tests/test_res_10_eval_llm.py` 至少包含（labeled fixtures only，零真实网络/密钥）：
   - 双臂装配正确性：同一 gold 集上 RD-06 输出与手算 fixture 一致（锚 RD-06 已有 oracle tests，此处验证传递正确）。
   - 对照协议正确性：LLM 臂与 zero-LLM 臂并列字段齐全、`Δ` 计算正确。
   - 只评估 adjudicated：未裁决 gold 不参与计数。
   - replay 闸门失败 ⇒ runner 中止（fixture 驱动）。
4. **文档**：`docs/llm-extractor-eval.md` 更新：指标定义全部指向 RD-06；对照协议；
   局限性（LLM 非确定性的处理 = RD-11 replay + 不可变原始响应 hash，非 temperature 承诺）。

### Verifier 职责
1. **指标正确性**：确认 runner 只经 RD-06 `evaluate_extraction` 计分（不重写公式）→ 与
   `tests/test_extraction_eval_metrics.py` 的 oracle 一致。
2. **Gold 依赖**：确认 gold 来自 ORCH-RES-08 freeze 产物且过滤 `adjudicated=true`。
3. **Provider Frozen**：确认 GLM-4-flash（E3 frozen）；replay 闸门在真实调用前执行。
4. **报告隔离**：确认 RD-07 输出为显式路径新文件（拒绝覆盖）；**无** ledger/results 写入。
5. **H6 确定性**：`uv run pytest -q tests/test_res_10_eval_llm.py tests/test_extraction_eval_metrics.py
   tests/test_zero_llm_baseline.py tests/test_extraction_replay.py -v` → **PASS**。
6. **禁用确认**：`git diff --name-only` → 只出现允许文件；frozen 文件（RD 产物/providers/规则表）0 diff。

### Reviewer 职责
1. **对照协议**：核实 Δ 表述无单点结论化、无 LLM-as-judge。
2. **LLM 非确定性处理**：确认可复现性由 RD-11 replay + 响应 hash 承载，而非 temperature 承诺。
3. **不碰结果**：确认无代码读写 `runs/results/**` 或 `runs/ledger.jsonl`。
4. **owner gate**：确认 owner 已授权 EVAL-LLM-001；trial manifest 合规（无 observed metric、fail-closed 字段齐）。
5. **BLOCKED 子项复核**：确认 ValidationKind 决策记录在案（扩展或豁免），registry 写盘已按决策执行。

## 验收标准

- [ ] `uv run pytest -q tests/test_res_10_eval_llm.py tests/test_extraction_eval_metrics.py tests/test_zero_llm_baseline.py tests/test_extraction_replay.py -v` → **PASS**。
- [ ] `uv run ruff check` → **clean**。
- [ ] `git diff --name-only` → **仅**出现允许修改的文件；RD 产物/providers/规则表 0 diff。
- [ ] `config/eval_llm_001.yaml` 只引用冻结值；gold set 路径指向 ORCH-RES-08 freeze 产物。
- [ ] runner 输出两臂并列报告（RD-07 格式；显式路径；拒绝覆盖）；replay 闸门先于真实调用。
- [ ] `evals/trials/EVAL-LLM-001.yaml` manifest 经 RD-17 validator 通过（或按 owner 决策豁免并注明）。
- [ ] **ORCH-RES-08 gold set freeze 产物存在且 `adjudicated=true` 记录可加载**。
- [ ] **owner 已明确授权** EVAL-LLM-001 trial。
- [ ] 无 TODO / placeholder / test.skip / stub。

## 失败处理

1. **Gold set 未 freeze（ORCH-RES-08 未完成）**：**HOLD**；等待 RES-08 5 阶段 freeze 产物。
2. **某指标无法锚定到 RD-06 字段**：该指标标 **BLOCKED**，退回 RD-06 owner-gated 扩展，不在本任务自造公式。
3. **replay 闸门失败**：**BLOCKED**（解析合同未稳定）；修复 parser 属 RD-11 范围，另开 task。
4. **Provider 非 Frozen / 规则表被改**：**BLOCKED**。
5. **RD-17 ValidationKind 无决策**：registry 写盘 **BLOCKED**（指标装配可先行）。
6. **禁用文件出现在 diff**：**BLOCKED**。
7. 无限 review 循环：2 轮修复失败后上报 **BLOCKED**，不继续迭代。

## 必须运行的测试

- `uv run pytest -q tests/test_res_10_eval_llm.py tests/test_extraction_eval_metrics.py tests/test_zero_llm_baseline.py tests/test_extraction_replay.py tests/test_gold_annotation_schema.py -v`
- `uv run ruff check`
- `git diff --name-only`
- `git diff -- runs/ledger.jsonl docs/phase-*-preregistration.md decisions/ADR-*.md src/aionis/extraction/eval_metrics.py src/aionis/extraction/eval_report.py src/aionis/extraction/zero_llm_baseline.py src/aionis/extraction/replay.py src/aionis/extraction/providers.py src/aionis/schema/gold_annotation.py evals/expected/zero_llm_rules_v1.yaml`（必须为空）
- **Gold set 加载测试**：ORCH-RES-08 freeze 快照可加载且 schema 校验通过（RD-04 契约）。

## 预期产物

1. **Runner**：`scripts/res_10_eval_llm_run.py`（replay 闸门 → 双臂抽取 → RD-06 计分 → RD-07 双报告）
2. **配置**：`config/eval_llm_001.yaml`
3. **测试**：`tests/test_res_10_eval_llm.py`
4. **文档**：`docs/llm-extractor-eval.md`（指标锚定 + 对照协议更新）
5. **评估报告**：两臂 JSON（RD-07 格式；显式路径；**非 confirmatory**；仅 exploratory）
6. **Trial manifest**：`evals/trials/EVAL-LLM-001.yaml`（RD-17 校验；按 owner 决策处理 ValidationKind）
7. **Reproducibility**：原始响应 hash + parser version sha256 入报告（RD-11/RD-07 契约）

## 完成后需要更新

1. 本文件头部 `状态` 更新为 "completed"（owner 授权并执行后）。
2. Orchestrator 更新 `state/handoff.md`，记录 EVAL-LLM-001 报告产出与 trial manifest 状态。
3. 任务完成后移入 `tasks/completed/TASK-RES-10-llm-eval.md`。

## 依赖顺序

```text
RD-04/06/07/08/11/17 COMPLETE（锚定对象，只调用不修改）
└── ORCH-RES-08（RES-08 重写：schema→sample→annotation→adjudication→freeze）→ owner GO → 执行
    └── RES-10（LLM eval；S）→ owner GO → Engineer → Verifier → Reviewer → COMPLETE（依赖 gold set freeze）
```

## See also

- `tasks/active/TASK-ORCH-RES-10-rewrite-llm-eval.md`（本文件的重写契约）
- `tasks/active/TASK-RD-04-llm-gold-schema.md`、`TASK-RD-06-llm-eval-metrics.md`、
  `TASK-RD-07-eval-report.md`、`TASK-RD-08-zero-llm-baseline.md`、`TASK-RD-11-provider-replay.md`、
  `TASK-RD-17-trial-intent-registry.md`
- `evals/expected/zero_llm_rules_v1.yaml`（RD-08 frozen 规则表；Engineer 无权改动）
- `evals/trials/README.md`（RD-17 registry usage contract；manifest 不替代 ledger）
- `tasks/active/TASK-ORCH-RES-08-rewrite-gold.md`、`TASK-RES-08-gold-set.md`（gold set 依赖）
- `docs/llm-extractor-eval.md`（schema/指标定义维护处）
- `reports/audits/2026-07-31-quant-llm-research-audit.md` §7, §11 P2, §13
- `decisions/ADR-010-sesoi-tost-sequential-gate.md`；`docs/phase-e3-preregistration.md`（E3 LLM edge 抽取参考）
- FinTagging — LLM-ready XBRL Concept Tagging Benchmark；FinBen — Financial NLP Benchmark（仅文献参考）
