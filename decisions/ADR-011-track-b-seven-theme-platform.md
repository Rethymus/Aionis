# ADR-011: Adopt Track B (seven-theme selection platform) as a new isolated research line

**Status**: ACCEPTED (owner decision, 2026-08-02)
**Date**: 2026-08-02
**Supersedes**: none (resolves the dual goal-narrative flagged in the 2026-08-02 strategic review)

## Context

- The 2026-07-31 independent audit and the 2026-08-02 strategic review
  ([`reports/2026-08-02-strategic-review-coverage-and-alignment.md`](../reports/2026-08-02-strategic-review-coverage-and-alignment.md))
  identified three things:
  1. B/C/D/E1 historical results are shared-fold **purged CV-proxy**, not
     chronological OOS — a validity caveat.
  2. Seven-theme coverage gaps: 新闻情绪 / 风险 / 回测净成本 / 市场结构 are
     essentially unbuilt.
  3. A dual goal-narrative (narrow null-harness vs the v0.2 broad selection
     platform in [`docs/quant-selection-research.md`](../docs/quant-selection-research.md))
     was unresolved — the largest hidden cost.
- [`docs/quant-selection-research.md`](../docs/quant-selection-research.md) v0.2 already
  mapped the seven themes to a reuse-first OSS scaffold (qlib / alphalens-reloaded /
  pyfolio-reloaded / FINSABER / purgedcv / empyrical / statsmodels).

## Decision

Adopt **Track B** — the seven-theme cross-sectional selection platform — as a **new,
isolated research line**:

- **New pre-registration** ([`docs/track-b-preregistration.md`](../docs/track-b-preregistration.md),
  PROPOSED) + **new frozen config** + **new ledger row**.
- **B/C/D/E1 frozen surfaces are untouched.** Anti-leakage rule (ADR-006): a new
  config is a new ledger row, never a silent overwrite.
- **Validation = chronological walk-forward** (`purged_walk_forward_splits`,
  `assert_chronological_split`), NOT shared-fold CV-proxy — directly fixes the
  B/C/D/E1 weakness identified by the audit.
- **Null-favored claim** (frontier consensus — Look-Ahead-Bench / Profit Mirage /
  FINSABER / Alpha Illusion: LLM-trading alpha is mostly leakage artifact).
- **SESOI / equivalence gate reuse ADR-010** (Jennison-Turnbull, look-specific RCI).
- **config_committed BEFORE result** — the frozen config's sha256 is appended to
  `runs/ledger.jsonl` before any out-of-sample metric is observed.

## Consequences

- Estimated **~90–140h** execution (S0 data spine → S1 price-only baseline +
  wheel-mounts → S2+ features). See
  [`reports/design/2026-08-02-track-b-s0-s1-slice-plan.md`](../reports/design/2026-08-02-track-b-s0-s1-slice-plan.md).
- **First slice already done**: mount ③ (market-structure) —
  `src/aionis/eval/ff5_residual.py` (FF5 residual + Amihud illiquidity, reusing
  statsmodels + pandas-datareader; 18 tests green, ruff clean; exploratory utility,
  not wired to pipeline, writes no ledger).
- **Pending**: owner must **freeze the Track B config sha256** (after reviewing the
  PROPOSED pre-registration) before any real-data run. Until then: no OOS results,
  no ledger writes for Track B.

## Alternatives considered

- **Track A only** (chronological re-validation of B/C/D/E1 + null writeup, ~23–39h):
  rejected — insufficient seven-theme coverage; owner wants full coverage.
- **Dual-track (A + B)**: deferred. Track A's null writeup can still proceed in
  parallel later if desired; it does not block Track B.

## Compliance

- Permissive licenses only ([ADR-007](ADR-007-permissive-licenses-only.md)): all
  Track B OSS wheels are MIT / Apache-2.0 / BSD (verified in
  [`reports/design/2026-08-02-reuse-catalog-v2.md`](../reports/design/2026-08-02-reuse-catalog-v2.md)).
- No disposable artifacts ([ADR-006](ADR-006-no-disposable-artifacts-registry.md)):
  Track B uses a durable registry + append-only ledger + H6 determinism.

## Links

- [ADR-006](ADR-006-no-disposable-artifacts-registry.md) (no disposable artifacts),
  [ADR-007](ADR-007-permissive-licenses-only.md) (permissive licenses),
  [ADR-010](ADR-010-sesoi-tost-sequential-gate.md) (SESOI / J-T gate, reused).
- [`docs/track-b-preregistration.md`](../docs/track-b-preregistration.md) (PROPOSED),
  [`reports/design/2026-08-02-track-b-s0-s1-slice-plan.md`](../reports/design/2026-08-02-track-b-s0-s1-slice-plan.md),
  [`reports/2026-08-02-strategic-review-coverage-and-alignment.md`](../reports/2026-08-02-strategic-review-coverage-and-alignment.md).
