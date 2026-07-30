# state/current.md — read first each session

- **version:** 0.1.0 (pyproject)
- **milestone:** 4 confirmatory nulls PUBLISHED (B/C/D/E1); horizon-robust at h∈{10,42} for all 4.
- **TASK-STRAT verdict (ADR-008, 2026-07-30):** launch **E3 forward-live** (commit-then-reveal, the
  only zero-leakage powered path) AND **broaden the null family** in parallel. **E2-as-confirmatory
  rejected** (futile per program §6). E2-as-exploratory remains available to de-risk E3.
- **done:** B/C/D/E1 nulls; horizon-robust all 4 phases (E1 added 2026-07-30); strategy-return lens;
  dashboard v2; TASK-STRAT brief + verdict (ADR-008); unified workflow scaffold (TASK-WF01).
- **now / next:**
  - **E3 launch** — the new primary workstream (**L** effort; pre-reg `docs/phase-e3-preregistration.md`
    exists). Needs plan/freeze/slice before any code: forward scheduler + forward ledger + commit-then-
    reveal + monthly scoring loop + forward ingest + dashboard forward-IC tab. See `tasks/active/TASK-E3-launch.md`.
  - **Null-broadening** — ongoing backlog (SIC vintage, more universes); low-risk, publishable.
  - **A1 (Phase B OOS panel)** — still blocked (benign `uv.lock` stranding; DROP recommended).
- **known issues:** Phase B OOS panel blocked by benign `uv.lock` stranding (see `blockers.md`); SIC
  current-snapshot (mild lookahead); **E3 launch is multi-year + irreversible once started**.
- **last verification:** `uv run pytest -q` green (305); `uv run ruff check` clean; A2 Verifier-PASS +
  Reviewer-APPROVE; ledger append-only; latest confirmatory sig `ef321e9e` (E1).
- **updated:** 2026-07-30.
