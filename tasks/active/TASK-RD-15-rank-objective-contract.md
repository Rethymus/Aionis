# RD-15 — Rank objective 数据与 query 合约

- 编号: RD-15
- 标题: 在 learner 集成前固定按月 ranking labels、groups 与合法 objective。
- 状态: **IMPLEMENTATION COMPLETE (sonnet Engineer) — 独立 Verifier PASS (31 模块 + 全套 1348 tests; learner.py 0 diff; 4 条 leakage 不变量) + 独立 Reviewer APPROVE (0 阻塞; 2 非阻塞：transform_to_relevance 72 行、Literal[5,10] 略窄)。按 opus 决策包实现 ranking_contract.py：lambdarank/rank_xendcg enum、per-month train-fold 分箱、out-of-range clamp+reason、group=query-month、4 条 leakage 不变量。bin_count 为参数（默认 5），实际冻结值待 owner 在 config 设定。决策包 reports/design/2026-08-01-rd15-rank-objective-contract.md。learner.py/frozen 未改。**
- Priority: **P2**
- Size: **M**（120–180 分钟，实现时间；不含强模型决策）
- Risk: **HIGH**
- 目标: 定义 schema/helper，使每个 month 是一个 query group，连续 forward returns 只在 train fold 内
  转为整数 ordinal relevance，并固定 bin/tie/missing policy 与允许的 LightGBM objective enum。
- 背景: 原 RES-03 把连续收益直接交给 ranking objective，并列出不存在的 objective；这会产生 API
  错误或 fold/global label leakage。
- 允许修改: `src/aionis/eval/ranking_contract.py`、`tests/test_ranking_contract.py`。
- 禁止修改: `learner.py`、phase/RES runners、真实 panel/data、ledger/results/config/prereg/ADR/state。
- 前置条件: strong-method/owner 先书面选择 `lambdarank` 或 `rank_xendcg`、bin 数、ties、missing 与
  out-of-range policy；低推理 Engineer 只能按该决定实现。
- 实施要求: label thresholds 只由当前 train fold 拟合；month group 边界稳定；test label transformation
  不可影响训练阈值；输出整数且 group size 与行数一致。
- 验收标准: 手算月度 fixtures、月份排列不变性、截断未来月份不改变过去阈值、missing/tie reason 明确；
  非法 objective 拒绝。
- 必须运行的测试: `uv run pytest -q tests/test_ranking_contract.py`; `uv run ruff check`。
- 失败处理: 未有强模型决策即 HOLD；不得让 Engineer 自选 objective/分箱。
- 预期产物: ranking contract、纯 helper、leakage oracle tests；无模型训练。
- 完成后需要更新: 由 Orchestrator 更新 state/handoff；另开 learner integration task。
