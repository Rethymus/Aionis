# state/backlog.md — candidates, not committed

> Add ideas here during a sprint; evaluate at milestone boundaries. Do NOT interrupt the current
> task. See `WORKFLOW.md` §6 (freeze rules).

- **Phase B OOS panel.** `scripts/phase_b_run.py` predates the schema-2 OOS-persistence wiring;
  pass `oos_state` / `oos_base` to `save_run` + a solo B rerun so all 4 phases demo the fit charts.
  **S** task.
- **E2 build (LLM macro-causal, cutoff-controlled).** Blocked on TASK-STRAT. If GO: implements the
  owner's "see-through-to-essence" vision with mitigated (not eliminated) LLM hindsight leakage.
  See `../docs/phase-e2-preregistration.md`, `../decisions/ADR-005-e2-underpowered-e3-forward-live.md`.
- **E3 forward-live launch.** The only POWERED zero-leak path; commit-then-reveal, PIT-safe live
  sources (13D / FRED / earnings). Takes calendar time (years) to power.
  See `../docs/phase-e3-preregistration.md`.
- **Horizon-robustness extension.** Sweep E1 at h=10 / h=42 (B/C/D already done) for symmetry.
  **S** task.
- **SIC vintage.** SIC is current-snapshot (mild lookahead for reclassifiers) — a vintage SIC
  would close it; low priority (effect estimated small). **M** task.
- **evals/cases golden fixtures.** Slot in once E3 forward-live produces commit/reveal fixtures.
