"""Trial-intent manifest schema (RD-17) — records trial intent BEFORE observing results.

This manifest prevents silent trial expansion and provides audit-trail for research
governance by explicitly recording the trial identity, owner approval, planned config,
validation kind, estimand, multiplicity accounting, and status WITHOUT any observed
metric fields (no IC, rank-IC, return, p-value, CI, Sharpe, DSR, accuracy, F1).

The schema is designed to:
- Require owner-decision reference, planned config hash, estimand, and validation kind
- Track trial families and parent-child relationships
- Account for multiplicity (n_trials, n_completed, n_superseded)
- Validate status transitions (PLANNED → APPROVED → ACTIVE → SUPERSEDED/CLOSED)
- Serialize to stable JSON (deterministic key order) for bit-stable replay checks
- Reject any payload carrying observed metrics (forbidden fields enforced at parse time)

CRITICAL: This manifest does NOT replace or bypass the config_committed ledger.
The ledger (runs/ledger.jsonl) MUST still be appended BEFORE any out-of-sample
result is observed. This manifest is a planning artifact only, not a ledger substitute.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# version stamp (frozen for this RD-17 implementation)
# ---------------------------------------------------------------------------

TRIAL_INTENT_SCHEMA_VERSION = "trial-intent-v1"
"""Immutable version stamp for the trial-intent manifest schema."""


# ---------------------------------------------------------------------------
# enums — validation kind, estimand, and status transitions
# ---------------------------------------------------------------------------


class ValidationKind(str, Enum):
    """The validation kind for this trial — MUST distinguish chronological from cross-fit.

    ``CHRONOLOGICAL``: Train is strictly before test (expanding window), no test
    sample is trained on data later than its evaluation time.

    ``PURGED_CROSS_FIT``: Cross-validation with purging/embargo, but NOT
    chronological — the test set may contain observations with prediction/evaluation
    times earlier than some training samples.

    This distinction is load-bearing for leakage prevention and must be explicit.
    """

    CHRONOLOGICAL = "chronological"
    PURGED_CROSS_FIT = "purged_cross_fit"


class Estimand(str, Enum):
    """The estimand (target quantity) this trial aims to estimate.

    ``RANK_IC``: Spearman rank correlation between predicted and actual ranks.
    ``IC``: Pearson correlation between predicted and actual values.
    ``LONG_SHORT_RETURN``: Return of a long-short portfolio strategy.
    ``CLASSIFICATION_ACCURACY``: Classification accuracy (binary or multi-class).
    ``OTHER``: Any other estimand (must be described in metadata).

    The estimand defines the success metric and MUST be declared before results.
    """

    RANK_IC = "rank_ic"
    IC = "ic"
    LONG_SHORT_RETURN = "long_short_return"
    CLASSIFICATION_ACCURACY = "classification_accuracy"
    OTHER = "other"


class TrialStatus(str, Enum):
    """The status of a trial — supports valid transitions only.

    Status progression:
    - ``PLANNED`` → ``APPROVED`` → ``ACTIVE`` → (``SUPERSEDED`` | ``CLOSED`` | ``FAILED``)
    - ``PLANNED`` → ``REJECTED``
    - ``APPROVED`` → ``REJECTED`` (before ACTIVE)
    - Any → ``BLOCKED`` (irrecoverable error or policy violation)

    Illegal transitions (e.g., ACTIVE → PLANNED, CLOSED → ACTIVE) are rejected.
    """

    PLANNED = "planned"
    APPROVED = "approved"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    CLOSED = "closed"
    FAILED = "failed"
    REJECTED = "rejected"
    BLOCKED = "blocked"

    def can_transition_to(self, target: TrialStatus) -> bool:
        """Check if transition from self to target is valid.

        Args:
            target: The target status to transition to.

        Returns:
            True if the transition is valid, False otherwise.
        """
        valid_transitions = {
            TrialStatus.PLANNED: {
                TrialStatus.APPROVED,
                TrialStatus.REJECTED,
                TrialStatus.BLOCKED,
            },
            TrialStatus.APPROVED: {
                TrialStatus.ACTIVE,
                TrialStatus.REJECTED,
                TrialStatus.BLOCKED,
            },
            TrialStatus.ACTIVE: {
                TrialStatus.SUPERSEDED,
                TrialStatus.CLOSED,
                TrialStatus.FAILED,
                TrialStatus.BLOCKED,
            },
            TrialStatus.SUPERSEDED: set(),
            TrialStatus.CLOSED: set(),
            TrialStatus.FAILED: set(),
            TrialStatus.REJECTED: set(),
            TrialStatus.BLOCKED: set(),
        }
        return target in valid_transitions.get(self, set())


# ---------------------------------------------------------------------------
# forbidden fields — observed metrics are NEVER allowed
# ---------------------------------------------------------------------------

FORBIDDEN_OUTCOME_FIELDS = frozenset(
    {
        "ic",
        "rank_ic",
        "mean_ic",
        "median_ic",
        "t_stat",
        "p_value",
        "ci_half",
        "ci_lower",
        "ci_upper",
        "sharpe_ratio",
        "total_return",
        "annual_return",
        "volatility",
        "max_drawdown",
        "hit_rate",
        "accuracy",
        "f1_score",
        "precision",
        "recall",
        "auc",
        "dsr_p_value",
        "spa_p_value",
        "stepwise_p_value",
    }
)
"""Observed metric fields that MUST NOT appear in a trial-intent manifest.

A manifest records ONLY INTENT (identity, approval, config, estimand, validation setup,
multiplicity, status). It never carries results. This enforced separation prevents
outcome leakage into the planning record.
"""


def assert_no_outcome_fields(raw: dict) -> None:
    """Raise ``ValueError`` if any observed metric field is present in ``raw``.

    Belt-and-suspenders pre-parse guard: call this on raw JSON BEFORE handing to
    :class:`TrialIntent`, so outcome leakage is rejected even if a permissive
    parse path exists elsewhere.
    """
    leaked = FORBIDDEN_OUTCOME_FIELDS.intersection(raw.keys())
    if leaked:
        raise ValueError(
            f"Trial-intent manifest must not contain observed metrics {sorted(leaked)} "
            f"(forbidden: {sorted(FORBIDDEN_OUTCOME_FIELDS)})"
        )


# ---------------------------------------------------------------------------
# multiplicity accounting — track trials in families
# ---------------------------------------------------------------------------


class Multiplicity(BaseModel):
    """Multiplicity accounting for trial families (prevents p-hacking via silent trials).

    Tracks:
    - ``n_trials``: Total planned trials in this family.
    - ``n_completed``: Trials completed with results.
    - ``n_superseded``: Trials superseded by newer versions.
    - ``n_failed``: Trials that failed to complete.

    The sum of completed + superseded + failed MUST NOT exceed n_trials (enforced
    by the validator). This invariant prevents hidden trial inflation.
    """

    model_config = ConfigDict(extra="forbid")

    n_trials: int = Field(
        ...,
        ge=1,
        description="Total planned trials in this family (>=1).",
    )
    n_completed: int = Field(
        ...,
        ge=0,
        description="Trials completed with results (>=0).",
    )
    n_superseded: int = Field(
        ...,
        ge=0,
        description="Trials superseded by newer versions (>=0).",
    )
    n_failed: int = Field(
        ...,
        ge=0,
        description="Trials that failed to complete (>=0).",
    )

    @field_validator("*")
    @classmethod
    def validate_non_negative(cls, v: int) -> int:
        """Ensure all counts are non-negative."""
        if v < 0:
            raise ValueError("Multiplicity counts must be non-negative.")
        return v

    @model_validator(mode="after")
    def validate_consistency(self) -> Multiplicity:
        """Ensure completed + superseded + failed <= n_trials."""
        total_accounted = self.n_completed + self.n_superseded + self.n_failed
        if total_accounted > self.n_trials:
            raise ValueError(
                f"Multiplicity inconsistency: "
                f"completed ({self.n_completed}) + superseded ({self.n_superseded}) "
                f"+ failed ({self.n_failed}) = {total_accounted} "
                f"exceeds n_trials ({self.n_trials})"
            )
        return self


# ---------------------------------------------------------------------------
# the trial-intent manifest
# ---------------------------------------------------------------------------


class TrialIntent(BaseModel):
    """Trial-intent manifest — records trial intent WITHOUT observed results.

    This schema stores the planning artifact for a research trial: trial identity,
    owner approval reference, family relationships, planned config hash, validation kind,
    estimand, multiplicity accounting, and status. It explicitly rejects any observed
    metrics (IC, returns, p-values, CIs) via ``extra="forbid"`` and the pre-parse guard
    :func:`assert_no_outcome_fields`.

    CRITICAL: This manifest does NOT satisfy the config_committed-before-result rule.
    The ledger (runs/ledger.jsonl) MUST still be appended BEFORE any out-of-sample result
    is observed. This manifest is a planning artifact only.

    The manifest is JSON-serializable with stable key order (``sort_keys=True``) for
    bit-stable replay checks. H6 determinism requires that identical inputs produce
    identical manifest JSON bytes.
    """

    model_config = ConfigDict(extra="forbid")

    # Schema version
    schema_version: Literal["trial-intent-v1"] = Field(
        default="trial-intent-v1",
        description="Schema version stamp (must be 'trial-intent-v1').",
    )

    # Core trial identity
    trial_id: str = Field(
        ...,
        min_length=1,
        pattern="^[a-zA-Z0-9_-]+$",
        description="Unique trial identifier (alphanumeric, underscore, hyphen only).",
    )

    # Owner approval reference (REQUIRED — fail closed if missing)
    owner_decision_ref: str = Field(
        ...,
        min_length=1,
        description="Reference to owner decision (e.g., 'RD-17' or ADR ID). REQUIRED.",
    )

    # Planned config hash (REQUIRED — fail closed if missing)
    planned_config_sha256: str = Field(
        ...,
        min_length=64,
        max_length=64,
        pattern="^[a-f0-9]{64}$",
        description="SHA-256 hash of the frozen config for this trial (hex, 64 chars). REQUIRED.",
    )

    # Validation kind (REQUIRED — fail closed if missing)
    validation_kind: ValidationKind = Field(
        ...,
        description="The validation kind — 'chronological' or 'purged_cross_fit'. REQUIRED.",
    )

    # Estimand (REQUIRED — fail closed if missing)
    estimand: Estimand = Field(
        ...,
        description="The estimand this trial aims to estimate. REQUIRED.",
    )

    # Family relationships
    family_id: str | None = Field(
        default=None,
        description="Family ID for grouping related trials (optional).",
    )
    parent_trial_id: str | None = Field(
        default=None,
        description="Parent trial ID if this is a follow-up trial (optional).",
    )

    # Multiplicity accounting
    multiplicity: Multiplicity = Field(
        ...,
        description="Multiplicity accounting for this trial family.",
    )

    # Status (with transition validation)
    status: TrialStatus = Field(
        default=TrialStatus.PLANNED,
        description="Current status of this trial (default: PLANNED).",
    )

    previous_status: TrialStatus | None = Field(
        default=None,
        description="Previous status before transition (for audit trail).",
    )

    # Metadata (optional, for audit trail)
    created_at: str | None = Field(
        default=None,
        description="ISO-8601 UTC timestamp when this manifest was created.",
    )
    updated_at: str | None = Field(
        default=None,
        description="ISO-8601 UTC timestamp when this manifest was last updated.",
    )
    description: str | None = Field(
        default=None,
        description="Human-readable description of this trial (optional).",
    )
    estimand_description: str | None = Field(
        default=None,
        description="Description of the estimand if estimand=OTHER (optional).",
    )

    @model_validator(mode="before")
    @classmethod
    def reject_outcome_fields(cls, data: object) -> object:
        """Pre-parse guard: reject any forbidden observed metric fields."""
        if not isinstance(data, dict):
            return data
        assert_no_outcome_fields(data)
        return data

    @field_validator("created_at", "updated_at")
    @classmethod
    def normalize_timestamp(cls, v: str | None) -> str | None:
        """Normalize timestamp to canonical ISO-8601 UTC if present."""
        if v is None:
            return None
        try:
            parsed = datetime.fromisoformat(v.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                raise ValueError("Timestamp must include timezone (UTC).")
            return parsed.astimezone(timezone.utc).isoformat()
        except (ValueError, AttributeError) as exc:
            raise ValueError(
                f"Invalid ISO-8601 UTC timestamp: {v!r}"
            ) from exc

    @model_validator(mode="after")
    def validate_status_transition(self) -> TrialIntent:
        """Validate status transition if previous_status is provided."""
        if self.previous_status is not None:
            if not self.previous_status.can_transition_to(self.status):
                raise ValueError(
                    f"Invalid status transition: {self.previous_status.value} → "
                    f"{self.status.value}. Valid transitions from "
                    f"{self.previous_status.value}: "
                    f"{[s.value for s in TrialStatus if self.previous_status.can_transition_to(s)]}"
                )
        return self

    @model_validator(mode="after")
    def validate_family_consistency(self) -> TrialIntent:
        """Ensure parent_trial_id is not the same as trial_id (no self-reference)."""
        if self.parent_trial_id is not None and self.parent_trial_id == self.trial_id:
            raise ValueError("parent_trial_id cannot be the same as trial_id (no self-reference).")
        return self

    def to_stable_json(self) -> str:
        """Serialize to stable JSON with deterministic key order (sort_keys=True).

        Returns JSON string suitable for bit-stable replay checks — identical
        manifest objects produce byte-identical JSON.

        Uses ``default=str`` to handle non-JSON-native types (e.g., enums).
        """
        return json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            default=str,
            indent=2,
        )

    @classmethod
    def from_json(cls, raw: str) -> TrialIntent:
        """Parse TrialIntent from JSON string.

        Args:
            raw: JSON string containing the trial-intent manifest.

        Returns:
            Parsed TrialIntent object.

        Raises:
            ValidationError: If JSON is invalid or violates schema constraints.
            ValueError: If JSON contains forbidden observed metric fields.
        """
        data = json.loads(raw)
        assert_no_outcome_fields(data)
        return cls(**data)

    def transition_to(self, new_status: TrialStatus) -> TrialIntent:
        """Create a new TrialIntent with status transitioned to new_status.

        Args:
            new_status: The target status to transition to.

        Returns:
            A new TrialIntent instance with updated status and previous_status.

        Raises:
            ValueError: If the transition is invalid.
        """
        if not self.status.can_transition_to(new_status):
            raise ValueError(
                f"Invalid status transition: {self.status.value} → {new_status.value}. "
                f"Valid transitions from {self.status.value}: "
                f"{[s.value for s in TrialStatus if self.status.can_transition_to(s)]}"
            )

        updated = self.model_copy(
            update={
                "status": new_status,
                "previous_status": self.status,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        return updated


# ---------------------------------------------------------------------------
# trial-id registry (prevents duplicates)
# ---------------------------------------------------------------------------

_trial_id_registry: set[str] = set()


def register_trial_id(trial_id: str) -> None:
    """Register a trial ID to prevent duplicates.

    Args:
        trial_id: The trial ID to register.

    Raises:
        ValueError: If trial_id is already registered.
    """
    if trial_id in _trial_id_registry:
        raise ValueError(
            f"Trial ID {trial_id!r} is already registered "
            "(duplicate IDs are forbidden)."
        )
    _trial_id_registry.add(trial_id)


def is_trial_id_registered(trial_id: str) -> bool:
    """Check if a trial ID is already registered.

    Args:
        trial_id: The trial ID to check.

    Returns:
        True if the trial ID is registered, False otherwise.
    """
    return trial_id in _trial_id_registry


def clear_trial_id_registry() -> None:
    """Clear the trial-ID registry (for testing only).

    WARNING: This function is for testing purposes only. Do NOT use in production.
    """
    _trial_id_registry.clear()


__all__ = [
    "TRIAL_INTENT_SCHEMA_VERSION",
    "ValidationKind",
    "Estimand",
    "TrialStatus",
    "FORBIDDEN_OUTCOME_FIELDS",
    "assert_no_outcome_fields",
    "Multiplicity",
    "TrialIntent",
    "register_trial_id",
    "is_trial_id_registered",
    "clear_trial_id_registry",
]
