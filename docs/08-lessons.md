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
10. **Nested `<a>` guarantees hydration mismatch (#418).** A card-level `<Link>`
    wrapping rows that are themselves `<Link>`s parses differently as a string
    (browser force-closes the outer anchor) than as a vDOM — every load throws
    React #418. Found by controlled ablation builds + targeted subtree diff,
    not by reading the code.
11. **content-visibility has a DOM-size threshold (~10k elements).** It paid
    -45% TBT on a 7k-DOM page and cost +20% on a 1.5k-DOM one — containment
    bookkeeping exceeds the layout savings below the threshold. Chart-heavy
    pages need deferred *mounts* (dynamic ssr:false) instead: hydration is not
    skipped by paint containment.
12. **A chart-level async split pays only when charts dominate page cost.**
    Same recipe: -40% on a chart-led page, +300ms net-harmful on a
    table-led page with one small chart (measured 4 runs, control page).
13. **TBT is sensitive to delivery interleaving.** The same build measures
    differently across network windows (slow windows spread long tasks);
    single live runs mislead — take medians, and treat local A/B as the
    deciding instrument.
14. **Never trust a saved marker's stale fields.** A marker mixing last
    night's `finished_at` with this run's `status: running` read as "crashed";
    it was mid-run. Verify against process liveness before acting.
15. **Multi-pathspec `git add` fails atomically.** One stale pathspec aborts
    the whole staging — a commit then shipped only part of the change. Check
    `git diff --cached` after every staged add.

## See also

- [RESULTS.md](RESULTS.md)
- [the display-era campaign report](../reports/design/2026-10-02-performance-campaign.md)
  (12 wins, 11 nulls, the four measured boundaries behind lessons 10-13)
