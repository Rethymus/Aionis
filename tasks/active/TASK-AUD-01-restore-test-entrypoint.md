# AUD-01 — Restore the documented hermetic test entrypoint

- 编号: AUD-01
- 标题: Make `uv run pytest -q` collect and run the dashboard tests from a clean project invocation.
- 状态: **COMPLETE — Engineer complete; Verifier PASS; Reviewer APPROVE**
- Priority: **P0**
- Size: **S**
- Risk: **MEDIUM**（验证声明当前与真实命令冲突，但修复应仅限 import/test 配置）
- 建议 agent role / model tier: **Engineer / medium**；Verifier / medium；Reviewer / medium。
- 目标: 修复 dashboard package 的 pytest import/packaging 路径，使项目文档指定的测试命令成为可信门禁。
- 背景: 只读审计在 commit `87af583` 上运行 `uv run pytest -q`，collection 于
  `tests/test_dashboard_curve.py:7` 失败：`ModuleNotFoundError: No module named 'dashboard'`；同时
  `uv run python -c 'import dashboard'` 成功。`pyproject.toml` 当前 wheel 仅列 `src/aionis`，而
  `state/current.md`/`state/handoff.md` 声称 576 tests green。
- 依赖: 无；AUD-02…AUD-07 的完整回归验收依赖本任务。
- 允许修改: `pyproject.toml`；仅在证据证明配置不足时可最小修改 `tests/conftest.py` 或
  build-package 声明。优先修复配置，不改 dashboard 业务逻辑。
- 禁止修改: `dashboard/app.py`、研究源码、测试断言、`state/**` 之外的结果陈述、frozen docs、
  `runs/**`、`data/**`；禁止删除/skip/xfail dashboard tests 来制造绿色。
- 前置条件: 在未改代码的基线上保存上述 collection failure；确认不是缺依赖或脏工作树导致。
- 实施要求: 选择能从仓库根目录和文档命令稳定复现的最小修复；不得依赖用户 shell 的临时
  `PYTHONPATH`。
- 验收标准:
  - [ ] `uv run pytest --collect-only -q` 无 collection error，并收集全部既有测试。
  - [ ] `uv run pytest -q` exit 0、0 skipped；实际通过数写入验证证据，不预写假数字。
  - [ ] `uv run ruff check` clean。
  - [ ] 不修改任何测试断言，不减少测试数量，不改变 dashboard 运行行为。
  - [ ] 只在命令真实通过后，才允许下游 AUD-02 更新 state 中的测试声明。
- 必须运行的测试: `uv run pytest --collect-only -q`；`uv run pytest -q`；`uv run ruff check`；
  `uv run python -c "import dashboard; print(dashboard.__file__)"`。
- 失败处理: 若最小配置修复会改变发布包边界或 Streamlit 启动方式，STOP/BLOCKED，交 owner 选择
  “pytest root path”或“正式打包 dashboard”；不得用环境变量掩盖。
- 预期产物: 一个可审计的最小 test/import 配置修复及真实测试输出。
- 完成后需要更新: `state/current.md`、`state/handoff.md` 的 last verification；不得改 ledger。
- see: `pyproject.toml:53`；`tests/test_dashboard_curve.py:7`；`CLAUDE.md` Commands。

## 2026-07-31 execution evidence

- Engineer: added only `pythonpath = ["."]` under pytest configuration in `pyproject.toml`.
- Verifier: **PASS** — 576 tests collected; 576 passed, 0 skipped; ruff clean; dashboard import succeeds;
  `git diff --check` clean.
- Reviewer: **APPROVE** — the one-line pytest-path change stays within scope, does not alter the
  package/dashboard runtime boundary, and is supported by the recorded verification evidence.
