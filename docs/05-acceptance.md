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
   out-of-sample metric was computed (the freeze is witnessed).
2. **H6 determinism** passes — the IC series AND the raw OOS scores are bit-identical on a
   same-config rerun (`np.array_equal`, `_scores_equal`).
3. The rank-IC **differential** (treatment − fundamentals-only) 95% CI **brackets 0**.
4. `ci_half < 0.015` (the publishability gate; a null with a tight CI is the intended result).
5. The **bundle-shuffle placebo** differential is not significant (the invented alignment carries
   no signal), and **leave-one-out** shows no single dominant driver.
6. The orchestrator `save_run`s artifacts **unconditionally** (no `if results_base is not None:`
   save-skip) and writes the `confirmatory:first` ledger verdict.
7. `uv run pytest -q` is green and `uv run ruff check` is clean; no `.env` / `data/` / `*.parquet`
   is staged.

## The harness / repo (non-phase changes)
- `uv run pytest -q` green; `uv run ruff check` clean.
- `runs/ledger.jsonl` stays append-only; any frozen-config change ships a new `config_committed`
  row in the **same** commit.
- No secrets or data committed (`.gitignore` honored; never `git add -f`).

## Verdict semantics
**NULL SUPPORTED** (CI brackets 0, publishable) is a **success**, not a failure — it is the
efficient-markets-prior outcome the pre-registration names as the betting favorite.

## See also
- `../CLAUDE.md` (definition of done, forbidden) · `04-architecture.md` (the pipeline) ·
  `phase-{b,c,d,e1}-preregistration.md` (per-phase claims) · `../runs/ledger.jsonl` (the log) ·
  `06-risks.md` · `08-lessons.md`.
