# RD-13 — 截面特征变化与可识别性 guard

- 编号: RD-13
- 标题: 在进入 rank learner 前拒绝月内常数或近常数特征。
- 状态: **COMPLETE — owner-authorized via /goal 2026-08-01 (P1); 独立 Verifier PASS (20 tests) + 独立 Reviewer APPROVE (0 issues 全 severity)。report-only 截面变化诊断 guard（CONSTANT/NEAR_CONSTANT/ALL_MISSING/FEW_VALID/VARIATION；显式阈值；不构造 interaction）。**
- Priority: **P1**
- Size: **S**（60–90 分钟）
- Risk: **MEDIUM**
- 目标: 对 feature panel 生成逐月 unique count/std/coverage 诊断，并对没有截面变化的候选特征
  fail closed 或明确标为 macro-only interaction input。
- 背景: 原 RES-02 拟把当月 FF5/DFF 原值复制到所有股票；这种列不能直接产生截面 rank signal。
- 允许修改: `src/aionis/features/diagnostics.py`、`tests/test_feature_diagnostics.py`。
- 禁止修改: 具体 FF5/DFF ingest、learner、phase runners、data/ledger/results/config/prereg/ADR/state。
- 前置条件: owner 授权 RD-13。
- 实施要求: 诊断按 date 分组；阈值显式；缺失覆盖与常数区分；只报告，不自动构造 interaction。
- 验收标准: 月内常数、近常数、全缺、少量有效值、真实截面变化 fixtures verdict 正确且排序稳定。
- 必须运行的测试: `uv run pytest -q tests/test_feature_diagnostics.py`; `uv run ruff check`。
- 失败处理: 需要选择 beta/interaction 经济定义时 STOP，由强模型重新规划 RES-02。
- 预期产物: variation report、reason codes、手算 fixtures。
- 完成后需要更新: 由 Orchestrator 更新 state/handoff。
