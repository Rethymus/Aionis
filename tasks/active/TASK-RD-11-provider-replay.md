# RD-11 — 小模型响应离线 replay 与解析稳定性

- 编号: RD-11
- 标题: 用合规 fixture 离线重放模型响应并检验解析稳定性。
- 状态: **PLANNED — not implementation-authorized**
- Priority: **P1**
- Size: **M**（90–150 分钟）
- Risk: **MEDIUM**
- 目标: 对已提供、明确标注为 test fixture 的 OpenAI-compatible 响应做离线 replay，测量 schema parse、
  abstain、invalid-output 与 cache-key 稳定性；不调用 GLM/SiliconFlow/ModelScope。
- 背景: 模型/API 结果具有非确定性；parser 和 cache 合同应先在固定响应上独立验证。
- 允许修改: `src/aionis/extraction/replay.py`、`tests/fixtures/llm_replay/**`、
  `tests/test_extraction_replay.py`。
- 禁止修改: provider catalog/client/router、真实 cache/data、ledger/results/config/prereg/ADR/state。
- 前置条件: RD-04、RD-06、RD-07 APPROVE；owner 授权 RD-11。
- 实施要求: fixtures 不含真实密钥/用户数据；原始响应与 parser version sha256；同输入 byte-identical；
  不修复/猜测无效 JSON。
- 验收标准: valid/invalid/truncated/extra-text/unknown-enum fixtures 均有确定 verdict；报告可由 RD-07 生成。
- 必须运行的测试: `uv run pytest -q tests/test_extraction_replay.py`; `uv run ruff check`；secret scan。
- 失败处理: 需要真实模型响应时 HOLD，等待单独预算/owner gate。
- 预期产物: replay loader、合规 fixtures、解析稳定性 tests。
- 完成后需要更新: 由 Orchestrator 更新 state/handoff。
