# Lessons learned

> Distilled findings that changed how the project runs.

1. **The efficient-markets prior holds at monthly frequency** across timing,
   surprise, relationship, and propagation axes — the four confirmatory nulls
   (B/C/D/E1), all publishable (ci_half < 0.015).
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

## See also

- RESULTS.md
