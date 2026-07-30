# state/blockers.md — what is blocking and why

- **E2 is underpowered as a backtest.** The cutoff gate collapses the 125-month OOS window to
  ~10-18 post-cutoff months → no statistical power. Resolution path = E3 forward-live (the only
  powered zero-leak route). This blocks the E-sequence's *primary confirmatory claim*; it does NOT
  block E2 as a design / hypothesis-generator. **Owner decision (TASK-STRAT) required.**
  See `../decisions/ADR-005-e2-underpowered-e3-forward-live.md`.
- **GLM 5-hour usage limit (429, recurring).** Provider quota; resets on a rolling window.
  Mitigation: model tiering (opus for high-stakes), bounded single retry, patience. Not a code
  blocker.
- **Phase B has no OOS panel.** `phase_b_run.py` predates the wiring → the dashboard shows the
  "re-run to enable" notice for B. Backlog **S** task (not a blocker for the 4-null headline).
