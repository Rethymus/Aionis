# state/current.md — read first each session

- **version:** 0.1.0 (pyproject)
- **milestone:** 4 confirmatory nulls PUBLISHED (B/C/D/E1); horizon-robust at h∈{10,42} for all 4.
- **TASK-STRAT verdict (ADR-008, 2026-07-30):** launch **E3 forward-live** (commit-then-reveal, the
  only zero-leakage powered path) AND **broaden the null family** in parallel. **E2-as-confirmatory
  rejected** (futile per program §6). E2-as-exploratory remains available to de-risk E3.
- **done:** B/C/D/E1 nulls; horizon-robust all 4 phases; strategy-return lens; dashboard v2;
  TASK-STRAT brief + verdict (ADR-008); unified workflow scaffold (TASK-WF01); PR #1 merged to main.
- **now / next:**
  - **E3 launch** — primary workstream. **Slice 1 (forward-ledger keystone) + Slice 2 (forward
    PIT-as-of-t ingest) DONE** on `feat/e3-forward-ledger`. Slice 2 = 3 snapshot-on-arrival collectors
    (13D poll / FRED-ALFRED macro / 8-K Item 2.02) + the I3 monotonic-forward clock; Verifier PASS
    (pytest 343, 0 skip) + Reviewer APPROVE (0 CRITICAL/HIGH; 6 advisory → backlog). Next: Slice 3
    (forward commit: fit-on-I_t → commit-before-reveal, reuses `two_arm` single-fit + `extra_features`)
    → 4/5/6. See `docs/phase-e3-implementation-plan.md` + `tasks/active/TASK-E3-launch.md`.
  - **Null-broadening** — ongoing backlog (SIC vintage, more universes); low-risk, publishable.
  - **A1 (Phase B OOS panel)** — still blocked (benign `uv.lock` stranding; DROP recommended).
- **known issues:** Phase B OOS panel blocked by benign `uv.lock` stranding (see `blockers.md`); SIC
  current-snapshot (mild lookahead); **E3 launch is multi-year + irreversible once the headline
  ignites** (shadow 1–2 mo first); GLM 5h quota can throttle agent throughput.
- **last verification:** `uv run pytest -q` green (343, 0 skip); `uv run ruff check` clean; E3 Slice 2
  Verifier-PASS + Reviewer-APPROVE (I3 gate raises incl. NaT, called by all 3 collectors BEFORE any
  side-effect; 8-K `\b2\.02\b` regex proven 7/7; idempotency 3-layered); real `runs/ledger.jsonl`
  pinned at 39 lines across the run (forward rows in temp test dirs only); latest confirmatory sig `ef321e9e` (E1).
- **updated:** 2026-07-30.
