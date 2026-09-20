# RD-10 — Momentum/reversal 特征纯函数内核

- 编号: RD-10
- 标题: 实现 outcome-blind 的 momentum/reversal 纯特征内核。
- 状态: **COMPLETE — Verifier FAIL (vol_adj_mom window + std threshold) → fixed → re-Verifier PASS + Reviewer APPROVE (2026-08-01)**
- Priority: **P1**
- Size: **M**（120–180 分钟）
- Risk: **MEDIUM**
- 目标: 只实现 monthly price panel 上的 12-1 momentum、1-month reversal 和 volatility-adjusted
  momentum，作为 RES-01 的前置基础件；不创建 config/runner/trial。
- 背景: RES-01 当前把特征、数据、配置、runner 和 trial 混在一起；先隔离可手算的纯特征定义。
- 允许修改: `src/aionis/features/momentum.py`、`tests/test_momentum_features.py`。
- 禁止修改: fetchers、phase runners、config、ledger/data/results/prereg/ADR/state。
- 前置条件: owner 授权 RD-10；价格输入已经是 PIT-adjusted monthly series 的假设写入函数契约。
- 实施要求: 输入是每 ticker、每月月末已复权 total-return adjusted close（source/PIT/corporate-action
  合同由上游保证，本任务不获取）。在预测月 t：`momentum_12_1 = close[t-1]/close[t-12]-1`，要求
  t-12..t-1 的 12 个连续月末 close 均存在且正；`reversal_1m = -(close[t]/close[t-1]-1)`，要求 t-1/t；
  `vol_adj_mom = momentum_12_1 / std(r[t-11],...,r[t-1], ddof=1)`，其中
  `r[m]=close[m]/close[m-1]-1`，恰好 11 个收益、`min_periods=11`。每 ticker 独立；任一所需值缺失/
  非正/非有限或 std<=0 均返回 NaN；禁止填补月份、winsorize、rank、future shift。
- 验收标准: 三个公式的手算 fixture、连续月份缺口、截断未来数据不改变过去输出、输入排列不敏感、
  非正价格/无穷/零波动边界全部固定。
- 必须运行的测试: `uv run pytest -q tests/test_momentum_features.py`; `uv run ruff check`。
- 失败处理: 价格复权/退市/PIT source 不在本任务；不得自行引入数据源。
- 预期产物: 纯函数与 PIT 截断 oracle tests。
- 完成后需要更新: 由 Orchestrator 更新 state/handoff。
