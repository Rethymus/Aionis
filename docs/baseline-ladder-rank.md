# Baseline ladder — rank-aware objective (BASELINE-RANK-001)

**Status**: DRAFT — implementation-ready (RES-03; trial status
`pending-owner-authorization`). **Owner gate**: running the trial requires explicit
owner authorization; the frozen config must be committed (`config_committed` ledger
row) BEFORE any out-of-sample metric is observed.

## Purpose

The frozen Phase B/C/D/E1 learner optimizes squared error (`objective="regression"`),
while the primary metric is cross-sectional **Spearman rank-IC**. The research audit
(§4.2) flags this objective/metric mismatch, and §8.1 cites Poh et al. (2021)
*Building Cross-Sectional Systematic Strategies by Learning to Rank*, which shows
cross-sectional learning-to-rank can beat regress-then-rank on the same features.

**BASELINE-RANK-001** adds a `lambdarank` rung to the baseline ladder: identical
frozen Phase B features, identical purged cross-fitted CV evidence strength, only
the objective changes. Per audit §11 P2 this is a **new config / new trial** —
existing B/C/D/E1 results are never silently modified, and no confirmatory headline
is claimed from this exploratory baseline.

## Frozen contract (RD-15, 2026-08-01 owner decision)

All ranking semantics anchor to the RD-15 decision packet
(`reports/design/2026-08-01-rd15-rank-objective-contract.md`) and its frozen
implementation `src/aionis/eval/ranking_contract.py` (READ-ONLY — changes require a
new decision process).

| Contract aspect | Decision |
|---|---|
| Objective | `lambdarank` (LightGBM ≥ 4.3; enum: `lambdarank` / `rank_xendcg`) |
| Bin count | `rank_bins = 5` (quintiles, owner-chosen) |
| Fitting scope | Per-calendar-month quantiles, fitted on the **train fold only** |
| Group | One query per calendar month (`group_id = year*12 + month-1`) |
| Ties | Equal returns → same relevance (quantile binning, no special handling) |
| Missing | NaN forward return → relevance -1 → **excluded** (features: LightGBM native) |
| Out-of-range | Clamp to nearest train-fold bin edge (1 / n_bins) + reason code; **never refit** |
| Reason codes | `normal` / `return_missing` / `oor_low` / `oor_high` / `unseen_pooled` |

Label chain (only path allowed): `construct_month_groups` → `fit_monthly_bins` →
`transform_to_relevance` → `filter_valid_ranking_samples` → `get_group_sizes`.

## LightGBM `lambdarank` parameters

The frozen param table (500 rounds, LR 0.05, 31 leaves, min_child 20, reg_lambda
1.0, feature/bagging fraction 0.8, bagging_freq 1) is reused verbatim from the
frozen MSE learner, with `objective="lambdarank"` and `metric="ndcg"`. H6
determinism pins (`n_jobs=1`, `random_state` / `bagging_seed` /
`feature_fraction_seed` / `drop_seed` = 0) are preserved, so same-config reruns are
bit-identical. Relevance labels are integer bins 1..5; the learner feeds them via
LightGBM's `group` interface (query sizes, not query IDs), which the contract chain
provides with `get_group_sizes` after filtering.

## vs frozen MSE regression

| | Frozen B (regression) | BASELINE-RANK-001 (lambdarank) |
|---|---|---|
| Objective | MSE (`objective="regression"`) | NDCG-based listwise ranking (`lambdarank`) |
| Label | Continuous forward return | Ordinal relevance 1..5 (per-month train-fold quintiles) |
| Query structure | None (pointwise) | Calendar month = one query group |
| NaN label | Row dropped before fit | relevance -1 → excluded; group sizes re-derived |
| OOS extremes | Raw continuous values | Clamped to train-fold bin edges + reason code |
| Metric alignment | Indirect (MSE ≠ rank-IC) | Direct (NDCG is rank-IC-aligned) |
| Evidence level | CV-proxy / confirmatory claim | **Exploratory CV-proxy only** (no headline) |

## Where it lives

- `config/baseline_rank_001.yaml` — the frozen-config source for the trial.
- `src/aionis/eval/learner.py` — `fit_predict_rank` (rank-aware branch; validates
  the objective through `ranking_contract.validate_objective`). The frozen
  regression branch (`fit_predict`) is unchanged for B/C/D/E1.
- `src/aionis/eval/ranking_contract.py` — frozen RD-15 contract (read-only).
- `scripts/res_03_baseline_rank_run.py` — exploratory runner (purged cross-fitted
  CV; writes no ledger row, no confirmatory headline).
- `tests/test_learner_rank_objective.py` — hermetic tests; RD-15 §7 invariants
  also covered at unit level in `tests/test_ranking_contract.py`.

## References

- RD-15 decision packet: `reports/design/2026-08-01-rd15-rank-objective-contract.md`
- Audit: `reports/audits/2026-07-31-quant-llm-research-audit.md` §4.2, §8.1, §11 P2
- Poh et al. (2021), *Building Cross-Sectional Systematic Strategies by Learning to Rank*
- LightGBM ranking documentation (Advanced Topics)
