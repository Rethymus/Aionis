"""Reproducibility capsule schema (RD-14) — versioned, outcome-free provenance hashes.

This capsule aggregates NON-outcome provenance hashes for offline replay audit:
uv.lock hash, git tree/config hash(es), validation-manifest hash (RD-02), gold-schema
hash (RD-04), parser hash, provider metadata, and raw-response hash. It explicitly
excludes ANY observed metrics (no IC, rank-IC, return, p-value, CI, Sharpe, DSR).

The schema is designed to:
- Accept hashes explicitly passed by the caller (no git/network/model subprocess calls)
- Reject any payload carrying outcome metrics via ``extra="forbid"`` and pre-parse guards
- Serialize to stable JSON (deterministic key order) for bit-stable replay checks
- Generate a deterministic capsule_id derived from content hashes (not timestamps)
- Fail closed when load-bearing hashes are missing
- Support atomic write with default refuse-to-overwrite

CRITICAL: This capsule does NOT record observed metrics. It records ONLY the
provenance of code, data, and configuration needed to reproduce a run. The
caller must still append the config_committed ledger row BEFORE observing any
out-of-sample result.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# version stamp (frozen for this RD-14 implementation)
# ---------------------------------------------------------------------------

REPRODUCIBILITY_CAPSULE_SCHEMA_VERSION = "reproducibility-capsule-v1"
"""Immutable version stamp for the reproducibility capsule schema."""


# ---------------------------------------------------------------------------
# enums — provider kind (must match extraction/providers.py)
# ---------------------------------------------------------------------------


class ProviderKind(str, Enum):
    """The LLM provider kind — MUST match extraction/providers.py routing.

    ``GLM``: GLM (Zhipu AI) provider — the default E3 forward provider.
    ``SILICONFLOW``: SiliconFlow provider.
    ``MODELSCOPE``: ModelScope provider.

    This enum is load-bearing for provider routing and must be kept in sync
    with the provider registry in ``extraction/providers.py``.
    """

    GLM = "glm"
    SILICONFLOW = "siliconflow"
    MODELSCOPE = "modelscope"


# ---------------------------------------------------------------------------
# forbidden fields — outcome metrics are NEVER allowed
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
"""Outcome metric fields that MUST NOT appear in a reproducibility capsule.

A capsule records ONLY provenance (code, data, config hashes). It never carries
results. This enforced separation prevents outcome leakage into the provenance record.
"""


def assert_no_outcome_fields(raw: dict) -> None:
    """Raise ``ValueError`` if any outcome metric field is present in ``raw``.

    Belt-and-suspenders pre-parse guard: call this on raw JSON BEFORE handing to
    :class:`ReproducibilityCapsule`, so outcome leakage is rejected even if a permissive
    parse path exists elsewhere.
    """
    leaked = FORBIDDEN_OUTCOME_FIELDS.intersection(raw.keys())
    if leaked:
        raise ValueError(
            f"Reproducibility capsule must not contain outcome metrics {sorted(leaked)} "
            f"(forbidden: {sorted(FORBIDDEN_OUTCOME_FIELDS)})"
        )


# ---------------------------------------------------------------------------
# provider metadata — minimal, outcome-free provider info
# ---------------------------------------------------------------------------


class ProviderMetadata(BaseModel):
    """Minimal, outcome-free provider metadata.

    Tracks:
    - ``provider_kind``: Which provider was used (GLM/SILICONFLOW/MODELSCOPE).
    - ``model_name``: The specific model invoked (e.g., "glm-4-plus").
    - ``temperature``: Sampling temperature (for determinism tracking).

    This metadata does NOT include any observed outputs, tokens used, or response
    content — only the minimal configuration needed to identify the provider/model.
    """

    model_config = ConfigDict(extra="forbid")

    provider_kind: ProviderKind = Field(
        ...,
        description="The provider kind used (GLM/SILICONFLOW/MODELSCOPE).",
    )
    model_name: str = Field(
        ...,
        min_length=1,
        description="The specific model invoked (e.g., 'glm-4-plus').",
    )
    temperature: float = Field(
        ...,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0.0-2.0, for determinism tracking).",
    )

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        """Ensure temperature is within valid API range."""
        if not (0.0 <= v <= 2.0):
            raise ValueError(f"Temperature must be between 0.0 and 2.0, got {v}.")
        return v


# ---------------------------------------------------------------------------
# the reproducibility capsule
# ---------------------------------------------------------------------------


class ReproducibilityCapsule(BaseModel):
    """Reproducibility capsule — versioned, outcome-free provenance hashes.

    This schema stores the NON-outcome provenance of a run: uv.lock hash,
    git tree/config hashes, validation-manifest hash (RD-02), gold-schema hash (RD-04),
    parser hash, provider metadata, and raw-response hash. It explicitly rejects any
    outcome metrics (IC, returns, p-values, CIs) via ``extra="forbid"`` and the
    pre-parse guard :func:`assert_no_outcome_fields`.

    The capsule is JSON-serializable with stable key order (``sort_keys=True``) for
    bit-stable replay checks. H6 determinism requires that identical inputs produce
    identical capsule JSON bytes and the same capsule_id.

    The capsule_id is a deterministic SHA-256 hash of the canonical JSON representation,
    NOT a timestamp or random value. Any change to load-bearing hashes produces a new
    capsule_id.
    """

    model_config = ConfigDict(extra="forbid")

    # Schema version
    schema_version: Literal["reproducibility-capsule-v1"] = Field(
        default="reproducibility-capsule-v1",
        description="Schema version stamp (must be 'reproducibility-capsule-v1').",
    )

    # Load-bearing hashes (REQUIRED — fail closed if missing)
    uv_lock_sha256: str = Field(
        ...,
        min_length=64,
        max_length=64,
        pattern="^[a-f0-9]{64}$",
        description="SHA-256 hash of uv.lock (hex, 64 chars). REQUIRED.",
    )
    git_tree_sha256: str = Field(
        ...,
        min_length=64,
        max_length=64,
        pattern="^[a-f0-9]{64}$",
        description="SHA-256 hash of git tree (hex, 64 chars). REQUIRED.",
    )
    config_sha256: str = Field(
        ...,
        min_length=64,
        max_length=64,
        pattern="^[a-f0-9]{64}$",
        description="SHA-256 hash of frozen config (hex, 64 chars). REQUIRED.",
    )
    validation_manifest_sha256: str = Field(
        ...,
        min_length=64,
        max_length=64,
        pattern="^[a-f0-9]{64}$",
        description="SHA-256 hash of validation manifest (RD-02, hex, 64 chars). REQUIRED.",
    )
    gold_schema_sha256: str = Field(
        ...,
        min_length=64,
        max_length=64,
        pattern="^[a-f0-9]{64}$",
        description="SHA-256 hash of gold schema (RD-04, hex, 64 chars). REQUIRED.",
    )
    parser_sha256: str = Field(
        ...,
        min_length=64,
        max_length=64,
        pattern="^[a-f0-9]{64}$",
        description="SHA-256 hash of parser code (hex, 64 chars). REQUIRED.",
    )
    raw_response_sha256: str = Field(
        ...,
        min_length=64,
        max_length=64,
        pattern="^[a-f0-9]{64}$",
        description="SHA-256 hash of raw LLM response (hex, 64 chars). REQUIRED.",
    )

    # Provider metadata (REQUIRED — fail closed if missing)
    provider_metadata: ProviderMetadata = Field(
        ...,
        description="Minimal, outcome-free provider metadata. REQUIRED.",
    )

    # Optional provenance metadata (for audit trail)
    capsule_id: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
        pattern="^[a-f0-9]{64}$",
        description="Deterministic capsule ID (SHA-256 of canonical JSON, hex, 64 chars). "
        "Computed automatically if not provided.",
    )
    created_at: str | None = Field(
        default=None,
        description="ISO-8601 UTC timestamp when this capsule was created.",
    )
    description: str | None = Field(
        default=None,
        description="Human-readable description of this capsule (optional).",
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
    def compute_capsule_id(self) -> ReproducibilityCapsule:
        """Compute deterministic capsule_id from canonical JSON if not provided."""
        if self.capsule_id is None:
            # Serialize to canonical JSON (sorted keys, no extra whitespace for hash)
            canonical = json.dumps(
                self.model_dump(mode="json", exclude={"capsule_id", "created_at", "description"}),
                sort_keys=True,
                default=str,
                separators=(",", ":"),
            )
            # Compute SHA-256 of canonical JSON
            import hashlib

            capsule_id = hashlib.sha256(canonical.encode()).hexdigest()
            # Use model_copy to set capsule_id (immutable pattern)
            object.__setattr__(self, "capsule_id", capsule_id)
        return self

    def to_stable_json(self) -> str:
        """Serialize to stable JSON with deterministic key order (sort_keys=True).

        Returns JSON string suitable for bit-stable replay checks — identical
        capsule objects produce byte-identical JSON.

        Uses ``default=str`` to handle non-JSON-native types (e.g., enums).
        """
        return json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            default=str,
            indent=2,
        )

    @classmethod
    def from_json(cls, raw: str) -> ReproducibilityCapsule:
        """Parse ReproducibilityCapsule from JSON string.

        Args:
            raw: JSON string containing the reproducibility capsule.

        Returns:
            Parsed ReproducibilityCapsule object.

        Raises:
            ValidationError: If JSON is invalid or violates schema constraints.
            ValueError: If JSON contains forbidden outcome metric fields.
        """
        data = json.loads(raw)
        assert_no_outcome_fields(data)
        return cls(**data)

    def save(self, path: Path | str, *, overwrite: bool = False) -> None:
        """Atomically save capsule to file, refusing to overwrite by default.

        Args:
            path: Destination path for the capsule file.
            overwrite: If False (default), raise FileExistsError if path exists.
                      If True, allow overwriting existing file.

        Raises:
            FileExistsError: If path exists and overwrite=False.
            OSError: If atomic write fails (e.g., permission denied).
        """
        dest_path = Path(path)
        if dest_path.exists() and not overwrite:
            raise FileExistsError(
                f"Refusing to overwrite existing capsule file: {dest_path}. "
                "Pass overwrite=True to explicitly allow overwriting."
            )

        # Atomic write: write to temp file, then replace
        temp_path = dest_path.with_suffix(dest_path.suffix + ".tmp")
        try:
            temp_path.write_text(self.to_stable_json(), encoding="utf-8")
            # Atomic replace (rename is atomic on POSIX)
            os.replace(temp_path, dest_path)
        except Exception:
            # Clean up temp file on failure
            temp_path.unlink(missing_ok=True)
            raise

    @classmethod
    def load(cls, path: Path | str) -> ReproducibilityCapsule:
        """Load capsule from file.

        Args:
            path: Path to the capsule file.

        Returns:
            Loaded ReproducibilityCapsule object.

        Raises:
            FileNotFoundError: If path does not exist.
            ValidationError: If JSON is invalid or violates schema constraints.
            ValueError: If JSON contains forbidden outcome metric fields.
        """
        source_path = Path(path)
        if not source_path.exists():
            raise FileNotFoundError(f"Capsule file not found: {source_path}")
        raw = source_path.read_text(encoding="utf-8")
        return cls.from_json(raw)


__all__ = [
    "REPRODUCIBILITY_CAPSULE_SCHEMA_VERSION",
    "ProviderKind",
    "FORBIDDEN_OUTCOME_FIELDS",
    "assert_no_outcome_fields",
    "ProviderMetadata",
    "ReproducibilityCapsule",
]
