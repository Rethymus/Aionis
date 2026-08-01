# Trial Intent Registry — Usage Contract (RD-17)

This registry tracks trial-intent manifests for research governance and audit trails. The manifest records trial intent BEFORE any out-of-sample result is observed, serving as a planning artifact that supplements, NOT replaces, the `config_committed` ledger.

## Purpose

The trial-intent manifest provides:
- Trial identity and family relationships
- Owner-decision reference (required)
- Planned config SHA-256 hash (required)
- Explicit validation kind (`chronological` or `purged_cross_fit`)
- Declared estimand (`rank_ic`, `ic`, `long_short_return`, etc.)
- Multiplicity accounting (prevents p-hacking via silent trials)
- Status transition tracking (PLANNED → APPROVED → ACTIVE → CLOSED/SUPERSEDED/FAILED)

## What This Manifest Does NOT Do

**CRITICAL: The trial-intent manifest does NOT satisfy the `config_committed` rule.**

The append-only ledger at `runs/ledger.jsonl` MUST still be written BEFORE any out-of-sample result is observed. This manifest is a planning artifact only and has NO ledger效力. It does not bypass, substitute for, or replace the config_committed-before-result invariant.

If a trial-intent exists but no ledger row has been appended for the trial's config hash, the trial is NOT yet properly registered for result observation. The ledger remains the single source of truth for config commitment.

## Forbidden Fields

The manifest explicitly rejects ANY observed metric fields:
- Correlation metrics: `ic`, `rank_ic`, `mean_ic`, `median_ic`
- Statistical tests: `t_stat`, `p_value`, `ci_half`, `ci_lower`, `ci_upper`
- Performance metrics: `sharpe_ratio`, `total_return`, `annual_return`, `volatility`, `max_drawdown`, `hit_rate`
- Classification metrics: `accuracy`, `f1_score`, `precision`, `recall`, `auc`
- Multiple-testing corrections: `dsr_p_value`, `spa_p_value`, `stepwise_p_value`

These fields are enforced at parse time via `extra="forbid"` and a pre-parse guard. Any payload carrying observed metrics is rejected outright.

## Fail-Closed Validation

The manifest fails closed when required fields are missing:
- `owner_decision_ref` — REQUIRED (e.g., "RD-17" or ADR ID)
- `planned_config_sha256` — REQUIRED (64-character hex SHA-256 hash)
- `validation_kind` — REQUIRED (`chronological` or `purged_cross_fit`)
- `estimand` — REQUIRED (`rank_ic`, `ic`, `long_short_return`, etc.)

Duplicate trial IDs are rejected via the `register_trial_id()` function.

Status transitions are validated:
- PLANNED → APPROVED → ACTIVE → SUPERSEDED/CLOSED/FAILED
- PLANNED → REJECTED
- APPROVED → REJECTED (before ACTIVE only)
- Any → BLOCKED (irrecoverable error)

Invalid transitions (e.g., ACTIVE → PLANNED, CLOSED → ACTIVE) raise `ValueError`.

## Usage Example

```python
from aionis.reporting.trial_intent import (
    TrialIntent,
    ValidationKind,
    Estimand,
    TrialStatus,
    Multiplicity,
    register_trial_id,
)

# 1. Create trial intent
trial = TrialIntent(
    trial_id="phase-e1-forward-001",
    owner_decision_ref="RD-17",
    planned_config_sha256="a" * 64,  # SHA-256 of frozen config
    validation_kind=ValidationKind.CHRONOLOGICAL,
    estimand=Estimand.RANK_IC,
    multiplicity=Multiplicity(n_trials=1, n_completed=0, n_superseded=0, n_failed=0),
    status=TrialStatus.PLANNED,
    description="Forward evaluation for Phase E1 (claim: two-tailed rank-IC)",
)

# 2. Register trial ID (prevents duplicates)
register_trial_id(trial.trial_id)

# 3. Serialize to stable JSON
manifest_json = trial.to_stable_json()
with open("evals/trials/phase-e1-forward-001.json", "w") as f:
    f.write(manifest_json)

# 4. Transition status as trial progresses
trial_approved = trial.transition_to(TrialStatus.APPROVED)
trial_active = trial_approved.transition_to(TrialStatus.ACTIVE)

# 5. After results are observed, update multiplicity and close
trial_completed = trial_active.model_copy(
    update={
        "multiplicity": Multiplicity(n_trials=1, n_completed=1, n_superseded=0, n_failed=0),
        "status": TrialStatus.CLOSED,
        "updated_at": "2026-08-01T18:00:00+00:00",
    }
)
```

## Integration with Ledger Workflow

The trial-intent manifest fits into the existing workflow as a pre-step:

1. **Freeze config** → compute SHA-256 hash
2. **Create trial-intent manifest** → record intent (owner, hash, estimand, validation kind)
3. **Register trial ID** → prevent duplicates
4. **Append to ledger** → `runs/ledger.jsonl` with `config_committed=true` (BEFORE observing results)
5. **Run trial** → execute training and evaluation
6. **Observe results** → record metrics (IC, returns, p-values, etc.)
7. **Update manifest** → transition status, update multiplicity

Step 4 (ledger append) is REQUIRED and cannot be skipped. The manifest does NOT replace this step.

## File Location

Trial-intent manifests are stored in `evals/trials/{trial_id}.json`. This directory is git-tracked and serves as the permanent registry for research trial planning.

## Version

Schema version: `trial-intent-v1` (frozen for RD-17 implementation).

## See Also

- `src/aionis/reporting/trial_intent.py` — Implementation
- `tests/test_trial_intent.py` — Hermetic test suite
- `tasks/active/TASK-RD-17-trial-intent-registry.md` — Task specification
- `decisions/ADR-006-no-disposable-artifacts-registry.md` — Durable registry principle
