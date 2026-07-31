# RD-07 — LLM evaluator 报告与成本工件

- 编号: RD-07
- 标题: 生成不可静默覆盖的抽取评估与成本报告。
- 状态: **COMPLETE — Verifier FAIL (generated_at runtime clock) → fixed (caller-provided) → re-Verifier PASS + Reviewer APPROVE (2026-08-01)**
- Priority: **P1**
- Size: **S**（75–120 分钟）
- Risk: **LOW**
- 目标: 把 RD-06 指标与 provider/model/prompt/schema/cache/token/latency metadata 渲染成 versioned JSON
  报告；不调用模型、不写研究 ledger。
- 背景: 后续模型比较需要把质量、成本、缓存和版本放在同一可审计工件中。
- 允许修改: `src/aionis/extraction/eval_report.py`、`tests/test_extraction_eval_report.py`、
  `reports/cost/README.md`。
- 禁止修改: provider/client、data/ledger/results/forward/config/prereg/ADR/state。
- 前置条件: RD-06 APPROVE；owner 授权 RD-07。
- 实施要求: 报告路径由调用者显式传入；原子写入；已有文件默认拒绝覆盖；tokens/cost 可 unknown。
- 验收标准: byte-stable JSON、schema version、输入 sha256、overwrite fail closed、空评估集拒绝。
- 必须运行的测试: `uv run pytest -q tests/test_extraction_eval_report.py`; `uv run ruff check`。
- 失败处理: 若需写 `runs/ledger.jsonl`，BLOCKED 并另开 owner-gated integration task。
- 预期产物: report builder、原子写 tests、cost metadata contract。
- 完成后需要更新: 由 Orchestrator 更新 state/handoff。
