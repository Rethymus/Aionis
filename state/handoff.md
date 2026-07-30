# state/handoff.md — current-pass handoff

- **round:** TASK-WF01 (unified workflow adoption), 2026-07-30.
- **this pass did:** created `CLAUDE.md` (Claude Code native entry, <200 lines) + `WORKFLOW.md`
  (constitution) + `AGENTS.md` (symlink → CLAUDE.md); scaffolded `state/` `decisions/` `tasks/`
  `evals/` `reports/` `archive/`; added `docs/00-08` numbered canonicals (existing 14 docs
  untouched); wired README "Operating frame" + .gitignore clarity.
- **files changed:** new files only (no existing tracked file renamed / moved / deleted). README +
  .gitignore edited additively.
- **tests:** no code touched → `uv run pytest -q` green, `uv run ruff check` clean (sanity).
- **assumptions:** `AGENTS.md` as a symlink is safe on Linux/WSL2 (a native-Windows clone would
  need a plain copy); docs numbered canonicals LINK to existing docs (no duplication, no broken
  refs).
- **next precise action:** finish `state/` (`backlog.md`, `blockers.md`) + `decisions/` (index +
  7 ADRs) → grep no-secrets → link check → `code-reviewer` pass → atomic commit + push
  origin/main → `MEMORY.md` pointer. Then await owner steer on TASK-STRAT (E2 vs E3).
- **do NOT repeat:** do not re-derive the workflow framework (it is preserved verbatim in
  `WORKFLOW.md`); do not rename existing docs (breaks README / ledger / memory refs).
