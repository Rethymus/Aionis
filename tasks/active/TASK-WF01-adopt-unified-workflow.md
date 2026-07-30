# Adopt the unified AI-workflow framework (Claude Code edition)

- 编号: WF01
- 标题: Adopt the unified AI-workflow framework (Claude Code edition)
- 状态: in progress
- 目标: 搭起统一的 AI 操作框架——`CLAUDE.md` + `WORKFLOW.md` + `AGENTS.md`（符号链接）+
  `state/` + `decisions/` + `tasks/` + `evals/` + `reports/` + `archive/` + `docs` 编号索引。
- 背景: 用户指令要求标准化 AI 工作流。`AGENTS.md` 是 Codex 惯例，本项目跑 Claude Code，
  其原生文件是 `CLAUDE.md`（故 CLAUDE.md 为主体，AGENTS.md 以符号链接指向，避免双源漂移）。
  本目录 `tasks/` 即该框架的组成部分。
- 允许修改: 仅本框架文件——`CLAUDE.md`、`WORKFLOW.md`、`AGENTS.md`(symlink)、
  `state/*.md`、`decisions/index.md`、`tasks/**`、`evals/**`、`reports/**`、`archive/**`、
  `docs/` 的编号索引（README/总览层）。
- 禁止修改: 任何研究/流水线源码（`src/**`、`scripts/**`）、`runs/ledger.jsonl`、
  `docs/phase-*-preregistration.md`、`.omc/`、现有 confirmatory 产物。
- 前置条件: 当前 4 条 confirmatory claim（B/C/D/E1）已入 ledger 且 NULL SUPPORTED；
  本任务为纯框架脚手架，不触及结果。
- 实施要求: (1) 框架文件**只含 tracked prose**，无密钥/数据/代码；(2) 所有目录各带 README
  或 index 说明语义；(3) `docs/` 加编号索引（如 `NN-slug.md` 映射）；(4) `AGENTS.md` 用
  symlink 指向 `CLAUDE.md`，二者不得分叉。
- 验收标准:
  - [ ] 全部目录存在且各带 README/index。
  - [ ] `CLAUDE.md` < 200 行。
  - [ ] `grep -rniE '(api[_-]?key|secret|token|password)=' tasks/ state/ decisions/ docs/` 无命中（无密钥）。
  - [ ] `uv run ruff check` clean。
  - [ ] `uv run pytest -q` 仍全绿（不回归，框架层不动测试代码）。
  - [ ] README 与 docs 互链已接好（wired）。
- 必须运行的测试: `uv run ruff check`；`uv run pytest -q`；`wc -l CLAUDE.md`；
  上述 grep 密钥扫描。
- 失败处理: 若测试回归，立即回滚框架改动，不强行落地；pytest/ruff 失败不算完成。
- 预期产物: 上述目录树 + `CLAUDE.md` + `WORKFLOW.md` + `AGENTS.md`(symlink) + 各目录 README/index。
- 完成后需要更新: `state/current.md`、`state/handoff.md`、`decisions/index.md`（若有新 ADR）。
