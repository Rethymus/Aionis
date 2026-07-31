# RD-02 — 验证证据 manifest 数据结构

- 编号: RD-02
- 标题: 定义不含 outcome 的验证证据 manifest。
- 状态: **PLANNED — not implementation-authorized**
- Priority: **P1**
- Size: **S**（60–90 分钟）
- Risk: **MEDIUM**
- 目标: 定义一个不含指标值的 validation manifest，记录 validation_kind、split 时间边界、embargo、
  universe/hash、label availability 与代码版本，供 chronological/cross-fit 报告共用。
- 背景: 历史结果曾把 cross-fit 与 OOS 混称；需要结构化证据阻止术语再次漂移。
- 允许修改: `src/aionis/eval/validation_manifest.py`、`tests/test_validation_manifest.py`。
- 禁止修改: 现有 CV/runner、config/prereg/ADR、ledger/data/results/forward、state。
- 前置条件: owner 授权 RD-02。
- 实施要求: Pydantic/dataclass 均可，但 schema 必须稳定、JSON 可序列化、拒绝含糊 validation kind。
- 验收标准: chronological 与 purged_cross_fit 明确区分；缺时间/hash/label 状态 fail closed；无指标字段。
- 必须运行的测试: `uv run pytest -q tests/test_validation_manifest.py`; `uv run ruff check`。
- 失败处理: 若需要改变现有 runner 接口则 BLOCKED，另开 integration task。
- 预期产物: schema、序列化与拒绝路径 tests。
- 完成后需要更新: 由 Orchestrator 更新 state/handoff。
