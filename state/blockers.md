# state/blockers.md — what is blocking and why

- **E2 is underpowered as a backtest.** The cutoff gate collapses the 125-month OOS window to
  ~10-18 post-cutoff months → no statistical power. Resolution path = E3 forward-live (the only
  powered zero-leak route). This blocks the E-sequence's *primary confirmatory claim*; it does NOT
  block E2 as a design / hypothesis-generator. **Owner decision (TASK-STRAT) required.**
  See `../decisions/ADR-005-e2-underpowered-e3-forward-live.md`.
- **GLM 5-hour usage limit (429, recurring).** Provider quota; resets on a rolling window.
  Mitigation: model tiering (opus for high-stakes), bounded single retry, patience. Not a code
  blocker.
- **Phase B OOS panel blocked by `uv.lock` stranding (benign).** The A1 same-sig guard
  fired as designed: Phase B's frozen sig `17245a75…` was computed under the pre-Phase-C
  `uv.lock` (`e045a023…`), while C/D/E1 + the current tree use `ee985437…` (the lock was
  updated in commit `1e57335` for the Reddit/PRAW stack). The drift is **non-load-bearing** —
  only `praw` / `prawcore` / `websocket-client` / `update-checker` / `defusedxml` were added;
  `lightgbm`/`pandas`/`numpy`/`pyarrow`/`scikit-learn`/`purgedcv` versions are unchanged →
  **Phase B's IC series is still bit-identically reproducible**; only the sig string moved (the
  blanket `uv_lock_sha256` guard caught it). `phase_b_run.py` already carries the correct
  `PHASE_B_NO_LEDGER` gate + additive oos wiring (uncommitted, ruff/305-tests clean). Resolution
  is an **owner decision**: DROP (cosmetic; **recommended**) · restore `e045a023…` lock for one
  rerun · re-freeze B under current lock (2nd baseline → needs ADR) · narrow the config sig to
  load-bearing versions only (architectural, affects all phases). Not a blocker for the 4-null headline.
