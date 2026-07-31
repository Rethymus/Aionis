# RD-16 — 抽取评估不确定性区间

- 编号: RD-16
- 标题: 为 coverage、schema failure 与字段质量增加确定性不确定性报告。
- 状态: **PLANNED — not implementation-authorized**
- Priority: **P1**
- Size: **M**（90–150 分钟）
- Risk: **MEDIUM**
- 目标: 对二项指标实现 Wilson interval，并对 filing/event strata 的 macro-F1 实现 seed=0 分层 bootstrap；
  不使用 LLM judge、不调用模型。
- 背景: 小 gold set 的点估计容易被过度解读；模型比较需要样本量与区间，而不只是单一分数。
- 允许修改: `src/aionis/extraction/eval_uncertainty.py`、`tests/test_extraction_eval_uncertainty.py`。
- 禁止修改: RD-06 核心定义、provider/client/prompt、真实 annotations/data、ledger/results/config/
  prereg/ADR/state。
- 前置条件: RD-06 APPROVE；owner 授权 RD-16。
- 实施要求: 置信水平显式；strata 与 seed 固定；空/单样本/全成功/全失败有定义；输出纯 JSON 类型。
- 验收标准: Wilson 手算边界一致；bootstrap 同输入 byte-identical；strata 缺失/极小样本返回 warning
  metadata，不伪造精度。
- 必须运行的测试: `uv run pytest -q tests/test_extraction_eval_uncertainty.py`; `uv run ruff check`。
- 失败处理: 需要主观 judge 或真实模型输出时 HOLD；不在本任务扩大指标族。
- 预期产物: interval/bootstrap helper、手算 fixtures、稳定报告结构。
- 完成后需要更新: 由 Orchestrator 更新 state/handoff。
