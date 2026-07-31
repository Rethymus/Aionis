# RD-04 — LLM 抽取 gold-set schema

- 编号: RD-04
- 标题: 实现已冻结的 E3 causal-edge 人工 gold record schema。
- 状态: **COMPLETE — Verifier PASS + Reviewer APPROVE (2026-08-01)**
- Priority: **P1**
- Size: **S**（60–90 分钟）
- Risk: **MEDIUM**
- 目标: 在不创建真实标注数据的前提下，实现直接复用 `ForwardCausalExtraction` / `CausalEdge`
  闭集枚举的 gold record；每条记录只能有 0 或 1 条 causal edge。
- 背景: 现有 RES-08 把真实样本、人工标注、裁决和冻结混成一个 M task；schema 必须先独立完成。
- 允许修改: `src/aionis/schema/gold_annotation.py`、`tests/test_gold_annotation_schema.py`、
  `docs/llm-extractor-eval.md`（仅 schema/定义段；可新建）。
- 禁止修改: `data/**`、模型 prompt/provider、ERL frozen semantics、ledger/results/config/prereg/ADR/state。
- 前置条件: owner 授权 RD-04；对齐现有 `src/aionis/schema/erl.py`。
- 实施要求: 固定模型 `GoldCausalAnnotationV1`，字段仅为：`schema_version="e3-causal-gold-v1"`、
  `event_id`、`event_type`（仅 `13d`/`8k_2_02`）、`filed_ts`、64-hex `source_text_sha256`、
  `source_span_start`/`source_span_end`（非负且 end>start）、`causal_edges`（长度 0 或 1，元素直接复用
  `CausalEdge`）、`abstention_reason`（仅 `no_defensible_edge`/`insufficient_text`/`not_applicable`/
  `adjudication_pending`）、`annotator_ids`（非空、排序去重）、`adjudicated`。非空 edge 时 reason 必须
  为 null；空 edge 时 reason 必填。`adjudication_pending` 时 `adjudicated=false`，其余冻结记录必须 true。
  `extra=forbid`；禁止 ERL free-text、market impact、未来收益或模型预测字段。
- 验收标准: 上述互斥/枚举/范围全部有合法与非法 fixture；直接加载现有 causal enum；schema 只需用
  `adjudication_pending` 标记“存在未解决分歧”，不保存逐标注者标签；未裁决记录不得被 evaluator 当 gold。
- 必须运行的测试: `uv run pytest -q tests/test_gold_annotation_schema.py tests/test_schema.py`；
  `uv run ruff check`。
- 失败处理: 需要改变 ERL 含义则 BLOCKED，由强模型做 ADR 判断。
- 预期产物: gold schema、示例 fixtures、字段说明。
- 完成后需要更新: 由 Orchestrator 更新 state/handoff。
