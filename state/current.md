# state/current.md — read first each session

- **version:** 0.1.0 (pyproject)
- **milestone:** 4 confirmatory nulls PUBLISHED (Phase B/C/D/E1), all publishable-as-null.
- **done:** Phase A pilot; B (timing) / C (surprise) / D (relationship) / E1 (propagation) — all
  NULL, CI brackets 0, ci_half<0.015; horizon-robust at h=10/42; strategy-return lens agrees (no
  L-S Sharpe survives DSR); dashboard v2 (10 tabs); README rewritten.
- **now:** TASK-WF01 — adopt the unified AI-workflow framework (CLAUDE.md + WORKFLOW.md + state/
  decisions/tasks/evals/reports/archive + docs 00-08). In progress.
- **next:** TASK-STRAT — owner decision gate: build E2 (LLM macro-causal, cutoff-controlled) vs
  launch E3 (forward-live, the only powered zero-leak path) vs other. Default HOLD.
- **known issues:** E2 backtest underpowered (cutoff → ~10-18 post-cutoff months); Phase B has no
  OOS panel (backlog); SIC is current-snapshot (mild lookahead for reclassifiers).
- **last verification:** `uv run pytest -q` green (~305); `uv run ruff check` clean; 3/4 phases
  have OOS panels (C/D/E1); ledger append-only, latest confirmatory sig `ef321e9e` (E1).
- **updated:** 2026-07-30.
