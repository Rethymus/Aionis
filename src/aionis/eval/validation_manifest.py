"""Validation-evidence manifest schema (RD-02) — records NON-outcome validation evidence.

This manifest prevents chronological and purged cross-fit validation from ever being
conflated again by explicitly recording the validation kind, split time boundaries,
embargo, universe hash, label availability, and code version WITHOUT any metric
fields (no IC, returns, p-values, or CIs).

The schema is designed to:
- Distinguish ``chronological`` from ``purged_cross_fit`` via ``validation_kind``
- Fail closed when time boundaries, hash, or label availability are missing
- Serialize to stable JSON (deterministic key order) for bit-stable replay checks
- Reject any payload carrying outcome metrics (forbidden fields enforced at parse time)

This module does NOT touch existing CV/runner code — it only provides a shared
data structure for validation evidence recording.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# version stamp (frozen for this RD-02 implementation)
# ---------------------------------------------------------------------------

VALIDATION_MANIFEST_SCHEMA_VERSION = "validation-manifest-v1"
"""Immutable version stamp for the validation manifest schema."""


# ---------------------------------------------------------------------------
# enums — closed validation kinds and label availability
# ---------------------------------------------------------------------------


class ValidationKind(str, Enum):
    """The validation kind — MUST distinguish chronological from cross-fit.

    ``CHRONOLOGICAL``: Train is strictly before test (expanding window), no test
    sample is trained on data later than its evaluation time. Used by
    :func:`aionis.eval.cv.purged_walk_forward_splits`.

    ``PURGED_CROSS_FIT``: Cross-validation with purging/embargo, but NOT
    chronological — the test set may contain observations with prediction/evaluation
    times earlier than some training samples (train is the test complement, not
    a temporal prefix). Used by :func:`aionis.eval.cv.purged_group_kfold_splits`.

    This distinction is load-bearing: conflating the two was the historical bug
    that drove RD-02.
    """

    CHRONOLOGICAL = "chronological"
    PURGED_CROSS_FIT = "purged_cross_fit"


class LabelAvailability(str, Enum):
    """Label (outcome) availability status for the validation split.

    ``AVAILABLE``: All train/test samples have their labels (evaluation_time outcomes).
    ``PARTIAL``: Some labels are missing (e.g., forward-looking labels not yet realized).
    ``MISSING``: No labels are available (unlabeled inference only).

    This field is required so manifest consumers can distinguish between validated
    (labels exist) and unvalidated (prediction-only) splits.
    """

    AVAILABLE = "available"
    PARTIAL = "partial"
    MISSING = "missing"


# ---------------------------------------------------------------------------
# forbidden fields — outcome metrics are NEVER allowed
# ---------------------------------------------------------------------------

FORBIDDEN_OUTCOME_FIELDS = frozenset(
    {
        "ic",
        "rank_ic",
        "mean_ic",
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
    }
)
"""Outcome metric fields that MUST NOT appear in a validation manifest.

A manifest records ONLY the validation setup (kind, boundaries, embargo, universe,
labels, code version). It never carries results. This enforced separation prevents
outcome leakage into the validation evidence record.
"""


def assert_no_outcome_fields(raw: dict) -> None:
    """Raise ``ValueError`` if any outcome metric field is present in ``raw``.

    Belt-and-suspenders pre-parse guard: call this on raw JSON BEFORE handing to
    :class:`ValidationManifest`, so outcome leakage is rejected even if a permissive
    parse path exists elsewhere.
    """
    leaked = FORBIDDEN_OUTCOME_FIELDS.intersection(raw.keys())
    if leaked:
        raise ValueError(
            f"Validation manifest must not contain outcome metrics {sorted(leaked)} "
            f"(forbidden: {sorted(FORBIDDEN_OUTCOME_FIELDS)})"
        )


# ---------------------------------------------------------------------------
# split time boundaries — train/test evaluation-time anchors
# ---------------------------------------------------------------------------


class SplitTimeBoundaries(BaseModel):
    """Time boundaries for one validation split (train/test evaluation-time anchors).

    All timestamps are ISO-8601 UTC strings with timezone (``+00:00`` or ``Z``).
    These are the times when labels (outcomes) are evaluated, NOT prediction times.

    The ``train_end`` is the latest evaluation_time in the training set. The
    ``test_start`` is the earliest evaluation_time in the test set. For chronological
    validation, ``train_end < test_start`` must hold (enforced by the caller, not
    here — the manifest records, does not validate, temporal ordering).

    All fields are required — fail closed if any boundary is missing.
    """

    model_config = ConfigDict(extra="forbid")

    train_start: str = Field(
        ...,
        description="Earliest evaluation_time in the training set (ISO-8601 UTC).",
    )
    train_end: str = Field(
        ...,
        description="Latest evaluation_time in the training set (ISO-8601 UTC).",
    )
    test_start: str = Field(
        ...,
        description="Earliest evaluation_time in the test set (ISO-8601 UTC).",
    )
    test_end: str = Field(
        ...,
        description="Latest evaluation_time in the test set (ISO-8601 UTC).",
    )

    @field_validator("*")
    @classmethod
    def validate_iso8601(cls, v: str) -> str:
        """Ensure all timestamps are valid ISO-8601 UTC strings."""
        try:
            parsed = datetime.fromisoformat(v.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                raise ValueError("Timestamp must include timezone (UTC).")
            # Re-emit canonical form to normalize Z/+00:00 differences
            return parsed.astimezone(timezone.utc).isoformat()
        except (ValueError, AttributeError) as exc:
            raise ValueError(
                f"Invalid ISO-8601 UTC timestamp: {v!r}"
            ) from exc


# ---------------------------------------------------------------------------
# the validation manifest
# ---------------------------------------------------------------------------


class ValidationManifest(BaseModel):
    """Validation-evidence manifest — records validation setup WITHOUT outcomes.

    This schema stores the non-outcome evidence of a validation split: what kind
    of validation was run, the time boundaries, embargo duration, universe hash,
    label availability, and code version. It explicitly rejects any outcome metrics
    (IC, returns, p-values, CIs) via ``extra="forbid"`` and the pre-parse guard
    :func:`assert_no_outcome_fields`.

    The manifest is JSON-serializable with stable key order (``sort_keys=True``) for
    bit-stable replay checks. H6 determinism requires that identical inputs produce
    identical manifest JSON bytes.
    """

    model_config = ConfigDict(extra="forbid")

    # Core validation identity
    validation_kind: ValidationKind = Field(
        ...,
        description="The validation kind — MUST be 'chronological' or 'purged_cross_fit'.",
    )

    # Split time boundaries (train/test evaluation-time anchors)
    time_boundaries: SplitTimeBoundaries = Field(
        ...,
        description="Train/test evaluation-time boundaries for this split.",
    )

    # Embargo (purging buffer after each test block)
    embargo_sessions: int = Field(
        ...,
        ge=0,
        description="Number of embargo sessions after each test block (>=0).",
    )

    # Universe fingerprint
    universe_hash: str = Field(
        ...,
        min_length=1,
        description="Hash of the universe (tickers, constituents) used in this split.",
    )

    # Label availability
    label_availability: LabelAvailability = Field(
        ...,
        description="Whether labels (outcomes) are available for this split.",
    )

    # Code version (for reproducibility)
    code_version: str = Field(
        ...,
        min_length=1,
        description="Code version identifier (e.g., git sha or version tag).",
    )

    # Metadata (optional, for audit trail)
    created_at: str | None = Field(
        default=None,
        description="ISO-8601 UTC timestamp when this manifest was created.",
    )
    fold_index: int | None = Field(
        default=None,
        ge=1,
        description="Fold index (1-based) if this is part of a K-fold split.",
    )

    @model_validator(mode="before")
    @classmethod
    def reject_outcome_fields(cls, data: object) -> object:
        """Pre-parse guard: reject any forbidden outcome metric fields."""
        if not isinstance(data, dict):
            return data
        assert_no_outcome_fields(data)
        return data

    @field_validator("created_at")
    @classmethod
    def normalize_created_at(cls, v: str | None) -> str | None:
        """Normalize created_at to canonical ISO-8601 UTC if present."""
        if v is None:
            return None
        try:
            parsed = datetime.fromisoformat(v.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                raise ValueError("created_at must include timezone (UTC).")
            return parsed.astimezone(timezone.utc).isoformat()
        except (ValueError, AttributeError) as exc:
            raise ValueError(
                f"Invalid ISO-8601 UTC created_at: {v!r}"
            ) from exc

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
    def from_json(cls, raw: str) -> ValidationManifest:
        """Parse ValidationManifest from JSON string.

        Raises:
            ValidationError: If JSON is invalid or violates schema constraints.
            ValueError: If JSON contains forbidden outcome metric fields.
        """
        data = json.loads(raw)
        assert_no_outcome_fields(data)
        return cls(**data)


__all__ = [
    "VALIDATION_MANIFEST_SCHEMA_VERSION",
    "ValidationKind",
    "LabelAvailability",
    "FORBIDDEN_OUTCOME_FIELDS",
    "assert_no_outcome_fields",
    "SplitTimeBoundaries",
    "ValidationManifest",
]
