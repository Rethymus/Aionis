# RD-03 — Chronological split 合成 oracle 与回归矩阵

- 编号: RD-03
- 标题: 用合成数据固定 chronological split 的合法边界。
- 状态: **COMPLETE — owner-authorized via /goal 2026-08-01 (P1, HIGH-risk); 独立 Verifier PASS (cv.py 0 diff; 36 tests = 15 cv + 21 oracle; lookahead 拒绝; 无 IC 计算) + 独立 Reviewer APPROVE (0 issues; lookahead 构造+拒绝经独立核实; 真 purgedcv 非 stub)。chronological oracle 747 行；cv.py 未改。**
- Priority: **P1**
- Size: **M**（90–150 分钟）
- Risk: **HIGH**（方法学 load-bearing，但仅测试）
- 目标: 用带明确 prediction/evaluation time 的合成 panel，固定 walk-forward 的合法与非法边界。
- 背景: AUD-03 已建立术语合同，但后续低推理开发仍需可运行的时间边界 oracle。
- 允许修改: `tests/test_chronological_oracle.py`；必要时仅修复 `src/aionis/eval/cv.py` 的明确缺陷。
- 禁止修改: phase runners、learner/features、config/prereg/ADR、ledger/data/results/forward、state。
- 前置条件: RD-02 APPROVE；owner 授权 RD-03。
- 实施要求: 覆盖 unresolved label、overlap、embargo、同月 group、空 fold、乱序输入、未来训练样本；
  不计算 IC/收益。
- 验收标准: 每个非法 split 有稳定 reason；合法 split 满足 train evaluation time <= test start；
  manifest 与 split 一致。
- 必须运行的测试: `uv run pytest -q tests/test_cv.py tests/test_chronological_oracle.py`；
  `uv run ruff check`; `git diff --check`。
- 失败处理: 若 purgedcv 本身语义不满足合同，BLOCKED 并提交最小复现，不自行替换依赖。
- 预期产物: 合成 oracle、边界矩阵、可审计失败证据。
- 完成后需要更新: 由 Orchestrator 更新 state/handoff。
