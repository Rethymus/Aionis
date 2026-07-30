# The falsifiable problem

> One pre-registered, two-tailed claim per phase on cross-sectional monthly rank-IC.

**The claim.** Each phase tests whether a treatment feature set beats a
fundamentals-only baseline on monthly cross-sectional rank-IC of S&P 500 PIT
constituents (588 clean tickers, 2016+, n=125 months). The treatment-vs-baseline
rank-IC **differential** is the falsifiable claim — never the standalone arm IC.

**The intended outcome.** Null-with-tight-95%-CI (ci_half < 0.015) is the
publishable result. A CI crossing 0 forbids claiming a positive effect; only a CI
tight enough to bound the effect counts as a settled null.

**The evaluation backbone.**
- Frozen LightGBM (`n_jobs=1`, all seeds pinned, version-pinned).
- `PurgedGroupKFold(5, group=month, embargo=21)` — shared folds across arms so the
  differential isolates only the held-out feature set.
- Newey-West HAC (maxlag=4) + moving-block-bootstrap Diebold-Mariano for the
  differential SE/CI and p-value.

**Status.** Phases B, C, D, and E1 each filed one claim; all four returned NULL
SUPPORTED with ci_half < 0.015. See RESULTS.md for the numbers.

## See also

- phase-b-preregistration.md
- phase-c-preregistration.md
- phase-d-preregistration.md
- phase-e-preregistration.md
- RESULTS.md
