# Acceptance criteria — what "done" means for a confirmatory run

A confirmatory phase run is NOT complete until every gate below passes. Each is falsifiable and
checked against real artifacts (ledger rows, parquet panels, test output) — not prose.

## A confirmatory phase run
**Given** a frozen config (feature set + `N_SPLITS` / `EMBARGO` / `HORIZON` + `FROZEN_PARAMS` +
universe + dependency versions) and its sha256:
**When** the phase orchestrator builds both arms on shared folds and computes the rank-IC
differential + controls:
**Then**
1. A `config_committed` row with that sha256 exists in `runs/ledger.jsonl` **before** any
   outcome-bearing metric was computed (the freeze is witnessed).
2. **H6 determinism** passes — the IC series AND raw scores are bit-identical on a
   same-config rerun (`np.array_equal`, `_scores_equal`).
3. The validation kind is explicit. `purged_cross_fit` results may be called cross-fitted/OOF;
   a chronological claim additionally requires the repository chronology contract to pass.
4. The rank-IC **differential** (treatment - baseline) point estimate, paired SE/CI and p-value
   are recorded. A missing paired CI is `not recorded`, never inferred from single-arm CIs.
5. Any precision or equivalence claim names its pre-registered rule. CI-crossing-zero alone is
   not equivalence; historical `ci_half < 0.015` flags are not TOST/SESOI evidence.
6. The **bundle-shuffle placebo** differential is not significant (the invented alignment carries
   no signal), and **leave-one-out** shows no single dominant driver.
7. The orchestrator `save_run`s artifacts **unconditionally** (no `if results_base is not None:`
   save-skip) and writes the `confirmatory:first` ledger verdict.
8. `uv run pytest -q` is green and `uv run ruff check` is clean; no `.env` / `data/` / `*.parquet`
   is staged.

## The harness / repo (non-phase changes)
- `uv run pytest -q` green; `uv run ruff check` clean.
- `runs/ledger.jsonl` stays append-only; any frozen-config change ships a new `config_committed`
  row in the **same** commit.
- No secrets or data committed (`.gitignore` honored; never `git add -f`).

## Verdict semantics
A null or negative result is a **successful research outcome** when reported within its evidence
boundary. Use “no significant positive increment observed” unless a pre-registered equivalence
rule was actually satisfied; do not infer market efficiency or economic equivalence from p > 0.05.

## See also
- `../CLAUDE.md` (definition of done, forbidden) · `04-architecture.md` (the pipeline) ·
  `phase-{b,c,d,e1}-preregistration.md` (per-phase claims) · `../runs/ledger.jsonl` (the log) ·
  `06-risks.md` · `08-lessons.md`.
