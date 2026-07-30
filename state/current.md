# state/current.md — read first each session

- **version:** 0.1.0 (pyproject)
- **milestone:** 4 confirmatory nulls PUBLISHED (B/C/D/E1); horizon-robust at h∈{10,42} for all 4.
- **TASK-STRAT verdict (ADR-008, 2026-07-30):** launch **E3 forward-live** (commit-then-reveal, the
  only zero-leakage powered path) AND **broaden the null family** in parallel. **E2-as-confirmatory
  rejected** (futile per program §6). E2-as-exploratory remains available to de-risk E3.
- **done:** B/C/D/E1 nulls; horizon-robust all 4 phases; strategy-return lens; dashboard v2;
  TASK-STRAT brief + verdict (ADR-008); unified workflow scaffold (TASK-WF01); PR #1 merged to main.
- **now / next:**
  - **E3 launch** — primary workstream. **Slice 1 (forward-ledger commit-reveal keystone) DONE**
    (commit `7ce7f08`, branch `feat/e3-forward-ledger`; 23 invariant tests, Reviewer APPROVE, pytest 328).
    Next: Slice 2 (forward PIT-as-of-t ingest) → Slice 3 (forward commit) → 4/5/6. See
    `docs/phase-e3-implementation-plan.md` + `tasks/active/TASK-E3-launch.md`.
  - **Null-broadening** — ongoing backlog (SIC vintage, more universes); low-risk, publishable.
  - **A1 (Phase B OOS panel)** — still blocked (benign `uv.lock` stranding; DROP recommended).
- **known issues:** Phase B OOS panel blocked by benign `uv.lock` stranding (see `blockers.md`); SIC
  current-snapshot (mild lookahead); **E3 launch is multi-year + irreversible once the headline
  ignites** (shadow 1–2 mo first); GLM 5h quota can throttle agent throughput.
- **last verification:** `uv run pytest -q` green (328); `uv run ruff check` clean; E3 Slice 1
  Reviewer-APPROVE (keystone I1/I2/I7); ledger append-only (+1 exploratory [A2]; E3 forward rows in
  temp test dirs only); real ledger 39 lines; latest confirmatory sig `ef321e9e` (E1).
- **updated:** 2026-07-30.
