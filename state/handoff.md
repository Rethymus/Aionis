# state/handoff.md — current-pass handoff

- **round:** TASK-STRAT verdict + sedimentation, 2026-07-30.
- **this pass did:**
  - **Owner rendered the TASK-STRAT verdict → ADR-008** (`decisions/ADR-008-launch-e3-and-broaden-nulls.md`):
    **launch E3 forward-live** + **broaden the null family** in parallel; **E2-as-confirmatory rejected**.
    E2-as-exploratory available to de-risk E3. Two tracks because E3's dominant cost is calendar time,
    which accrues independently of the publishable-null track.
  - Closed the TASK-STRAT gate task (→ `tasks/completed/`).
  - Created `tasks/active/TASK-E3-launch.md` — the next workstream (L effort; needs plan/freeze/slice).
- **files changed:** ADR-008 (new); `decisions/index.md` (+row, next→ADR-009); `state/current.md`,
  `state/handoff.md`; `tasks/active/TASK-E3-launch.md` (new); `tasks/active/TASK-STRAT-…` → completed.
- **next precise action:** **plan the E3 forward-live implementation** per `docs/phase-e3-preregistration.md`
  + WORKFLOW.md (research → decision → freeze → slice → execute). Continue the null-broadening backlog
  in parallel (SIC vintage etc.).
- **do NOT repeat:** do NOT start E3 coding before its freeze/slice (irreversible, high-cost,
  leakage-sensitive); do NOT re-litigate E2-as-confirmatory (ADR-008 closes it absent a re-eval trigger);
  do NOT touch the 4 published nulls.
