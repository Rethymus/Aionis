# Lessons learned

> Distilled findings that changed how the project runs.

1. **Evidence boundaries matter.** B/C/D/E1 show no significant positive increment
   under one frozen, purged cross-fitted implementation. B has no paired CI; C is
   outside a post-hoc +/-0.015 equivalence band; none proves market efficiency.
2. **Recurring orchestrator save-skip bug.** An `if results_base is not None:`
   guard skips artifact writes when the main passes `None`. Orchestrators must
   **always** `save_run` — never gate persistence on a caller-supplied path.
3. **VIXCLS is unrevised** → PIT via the no-revision contract (G3), *not* via
   ALFRED-style vintage tracking.
4. **pandas >= 3.0 `transform("size")`** counts NaN-inclusive groups; use
   `transform("count")` for NaN-aware group sizes.
5. **The cumulative-IC random-walk band uses sigma**, not `se_hac`. sigma/sqrt(n)
   is ~11x too narrow and falsely shows "skill" for a null IC.
6. **Durable registry beats disposable artifacts.** `config_committed` sha256
   BEFORE the result: same-sig reruns are reproducibility, a changed config is a
   new ledger row — never a silent overwrite.
7. **Purged cross-fitting is not chronological OOS.** Purge and embargo prevent
   label overlap, while complement-based folds may still train on later months.
8. **LLM attribution must be explicit.** B/C/D/E1 are zero-LLM; Phase A is an
   underpowered 53-ERL/43-cluster pilot, not evidence of stock-selection alpha.
9. **Economic claims need economic inputs.** The B/C strategy lens is exploratory,
   gross of costs and lacks turnover; it cannot establish net tradability.

## See also

- RESULTS.md
