# RD-06 — LLM 结构化抽取确定性指标

- 编号: RD-06
- 标题: 实现无需 LLM judge 的字段级抽取指标。
- 状态: **COMPLETE — Verifier PASS + Reviewer APPROVE (2026-08-01)**
- Priority: **P1**
- Size: **M**（120–180 分钟）
- Risk: **MEDIUM**
- 目标: 实现已冻结的单-edge/abstain 字段级与事件级指标；只比较已提供的 adjudicated gold 与
  prediction records。
- 背景: 仅报告总体准确率会掩盖 abstention、覆盖率和细粒度 causal link 失败。
- 允许修改: `src/aionis/extraction/eval_metrics.py`、`tests/test_extraction_eval_metrics.py`。
- 禁止修改: 模型 client/prompt/provider、data/ledger/results/config/prereg/ADR/state。
- 前置条件: RD-04 APPROVE；owner 授权 RD-06。
- 实施要求: 评估单位是 event_id；gold 必须 `adjudicated=true`。prediction 解析失败或 edge 数>1 记
  invalid，等价于 empty prediction 参与 TP/FP/FN，同时单独计 invalid。0 edge=abstain，1 edge=预测。
  edge identity 是 `(sic_sector,direction,mechanism_keyword,horizon_bucket)` 全 tuple。`TP`=gold/pred 都有且
  tuple 全等；`FP`=pred 有但 gold 无或 tuple 不等；`FN`=gold 有但 pred 无或 tuple 不等。
  `precision=TP/(TP+FP)`、`recall=TP/(TP+FN)`、`F1=2PR/(P+R)`；任一分母为 0 输出 JSON null，不填 0。
  `coverage`=valid 且非空 prediction/N；`abstention`=valid 且空/N；`invalid_schema`=invalid/N；
  `event_exact`=(prediction valid 且双方都 abstain，或 prediction valid 且 tuple 全等)/N；invalid
  prediction **永远不 exact**，即使 gold abstain。四个字段准确率只在 gold/pred 都各有一条 edge 的
  paired subset 上计算并同时报告 denominator。macro 指标按 event_type 分组后对非-null strata 等权平均，
  并列出 omitted strata。禁止 LLM-as-judge；输出纯 JSON 类型。
- 验收标准: 手算 fixture 完全吻合；双方 abstain、单边 abstain、tuple 部分错误、invalid、零分母、
  缺少 adjudication、macro omitted strata 均有确定 oracle。
- 必须运行的测试: `uv run pytest -q tests/test_extraction_eval_metrics.py`; `uv run ruff check`。
- 失败处理: 任何需要主观 judge 的字段先标 unsupported，不自行引入 judge。
- 预期产物: 指标函数、手算 oracle tests、指标定义 docstring。
- 完成后需要更新: 由 Orchestrator 更新 state/handoff。
