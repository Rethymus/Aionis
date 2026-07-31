# The falsifiable problem

> One pre-registered, two-tailed claim per phase on cross-sectional monthly rank-IC.

**The claim.** Each phase tests whether a treatment feature set beats a
fundamentals-only baseline on monthly cross-sectional rank-IC of S&P 500 PIT
constituents (588 clean tickers, 2016+, n=125 months). The treatment-vs-baseline
rank-IC **differential** is the falsifiable claim — never the standalone arm IC.

**The intended outcome.** A precisely estimated null is useful and publishable,
but a CI crossing zero is only a failure to detect a differential, not proof of
equivalence. The historical `ci_half < 0.015` flag is a precision rule; no economic
SESOI or TOST was pre-registered for B/C/D/E1.

**The evaluation backbone.**
- Frozen LightGBM (`n_jobs=1`, all seeds pinned, version-pinned).
- `PurgedGroupKFold(5, group=month, embargo=21)` — shared purged cross-fitting
  across arms. Candidate training rows can include later months, so this is not
  strictly chronological validation.
- Newey-West HAC (maxlag=4) + moving-block-bootstrap Diebold-Mariano for the
  differential SE/CI and p-value.

**Status.** B/C/D/E1 produced four negative point estimates and no significant
positive incremental rank-IC under the frozen implementation. B has no recorded
paired differential CI; C/D/E1 CIs cross zero, and C extends outside a post-hoc
+/-0.015 equivalence band. All four headline feature sets are zero-LLM. See
RESULTS.md for the evidence boundary.

## See also

- phase-b-preregistration.md
- phase-c-preregistration.md
- phase-d-preregistration.md
- phase-e-preregistration.md
- RESULTS.md
