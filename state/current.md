# state/current.md — read first each session

- **version:** 0.1.0 (pyproject)
- **milestone:** 4 confirmatory nulls PUBLISHED (Phase B/C/D/E1), all publishable-as-null.
- **done:** Phase A pilot; B/C/D/E1 confirmatory nulls (CI brackets 0, ci_half<0.015);
  horizon-robust at h=10/42 for **all 4 phases** (E1 added 2026-07-30); strategy-return lens
  agrees (no L-S Sharpe survives DSR); dashboard v2 (10 tabs); README rewritten; unified
  workflow scaffold adopted (TASK-WF01).
- **now:** backlog robustness pass (2026-07-30) — **A2 (E1 horizon-robustness) DONE**: Verifier
  PASS, Reviewer APPROVE, +1 exploratory ledger row (E1 null holds at h=10 & h=42). TASK-STRAT
  decision brief **FILED** (`reports/TASK-STRAT-e2-e3-decision-brief.md`) — awaits owner verdict.
- **next:** (1) owner **TASK-STRAT verdict** (E2 vs E3 vs HOLD) per the brief's 3-dial framework;
  (2) **commit** the working-tree changes (A2 + retained A1 + brief + specs); (3) **A1 resolution**.
- **known issues:** E2 backtest underpowered (cutoff → ~10-18 post-cutoff months); Phase B OOS
  panel blocked by benign `uv.lock` stranding (only B frozen under old lock `e045a023…`; PRAW-stack
  drift, non-load-bearing — see `state/blockers.md`); SIC is current-snapshot (mild lookahead).
- **last verification:** `uv run pytest -q` green (305); `uv run ruff check` clean; A2 independently
  Verifier-PASS + Reviewer-APPROVE; ledger append-only (+1 exploratory, confirmatory unchanged=4);
  latest confirmatory sig `ef321e9e` (E1).
- **updated:** 2026-07-30.
