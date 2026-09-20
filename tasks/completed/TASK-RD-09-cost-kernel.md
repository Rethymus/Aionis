# RD-09 — Next-open、turnover 与 slippage 纯函数内核

- 编号: RD-09
- 标题: 固定 next-open、turnover 与线性 slippage 的纯函数语义。
- 状态: **COMPLETE — Verifier PASS + Reviewer APPROVE (2026-08-01)**
- Priority: **P1**
- Size: **M**（120–180 分钟）
- Risk: **MEDIUM**
- 目标: 用 synthetic panel 实现经济有效性所需的 next-open execution、one-way turnover、线性 bps
  slippage 纯函数；不运行策略、不读真实价格。
- 背景: 当前 rank-IC 证据不能自动转化为可交易收益；先建立手算可核验的摩擦内核。
- 允许修改: `src/aionis/eval/execution_costs.py`、`tests/test_execution_costs.py`。
- 禁止修改: `strategy_returns.py` 集成、phase runners、data/ledger/results/config/prereg/ADR/state。
- 前置条件: owner 授权 RD-09；公式由任务固定，不由 Engineer选择替代模型。
- 实施要求: 明确 close signal -> next session open；缺 open/停牌 fail closed；turnover 使用“资产回报漂移后
  的 pre-trade 权重”到目标权重的 traded notional，long/short 分开；bps 参数显式且非负，并标注为
  scenario assumption，不得称为真实成本估计。
- 验收标准: 手算 fixture 一致；成本只按 traded notional 收取；同日执行被拒绝；排序/重复 ticker/
  缺价格边界确定；无网络 I/O。
- 必须运行的测试: `uv run pytest -q tests/test_execution_costs.py`; `uv run ruff check`。
- 失败处理: 借券、冲击、容量、退市不在本任务；需要时另开任务。
- 预期产物: 三个纯函数、手算 oracle tests、公式 docstring。
- 完成后需要更新: 由 Orchestrator 更新 state/handoff。
