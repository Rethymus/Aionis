# RD-01 — 任务规格静态检查器

- 编号: RD-01
- 标题: 为 active task 建立确定性规格静态检查器。
- 状态: **PLANNED — not implementation-authorized**
- Priority: **P0**
- Size: **S**（60–90 分钟）
- Risk: **LOW**
- 目标: 用确定性脚本检查 active task 的必填字段、Size=L 禁止下发、owner gate 与危险命令声明。
- 背景: 现有 RES 任务名义为 S/M，但部分同时包含 intake、代码、runner、配置和 trial；弱模型需要
  机器可读的越界提示。
- 允许修改: `scripts/check_task_contracts.py`、`tests/test_task_contracts.py`、`tasks/README.md`。
- 禁止修改: 既有 task 内容、state、src、docs、ledger/data/results/config/ADR。
- 前置条件: owner 授权 RD-01。
- 实施要求: 仅解析 Markdown；输出逐文件 reason code；默认不因历史任务缺陷自动改文件。
- 验收标准: 可识别缺字段、L task、owner-held、禁止运行声明缺失；本仓库输出稳定且排序确定。
- 必须运行的测试: `uv run pytest -q tests/test_task_contracts.py`; `uv run ruff check`；
  `uv run python scripts/check_task_contracts.py tasks/active`。
- 失败处理: 无法可靠解析时仅报告 UNKNOWN，不得猜测或改写任务。
- 预期产物: 检查器、fixtures/tests、文档用法。
- 完成后需要更新: 由 Orchestrator 更新 state/handoff。
