"""Hermetic tests for trial-intent manifest (RD-17).

All tests use synthetic/labeled fixtures only. No real data, no network,
no LLM, no git writes, no ledger writes. H6 determinism: seeds pinned to 0.
"""
import json.decoder

import pytest
from pydantic import ValidationError

from aionis.reporting.trial_intent import (
    FORBIDDEN_OUTCOME_FIELDS,
    TRIAL_INTENT_SCHEMA_VERSION,
    Estimand,
    Multiplicity,
    TrialIntent,
    TrialStatus,
    ValidationKind,
    assert_no_outcome_fields,
    clear_trial_id_registry,
    is_trial_id_registered,
    register_trial_id,
)

# ---------------------------------------------------------------------------
# test fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_config_hash() -> str:
    """A valid SHA-256 config hash (synthetic)."""
    return "a" * 64  # 64 hex chars = 256 bits


@pytest.fixture
def minimal_trial_data(sample_config_hash: str) -> dict:
    """Minimal valid trial-intent data (synthetic)."""
    return {
        "trial_id": "test-trial-001",
        "owner_decision_ref": "RD-17",
        "planned_config_sha256": sample_config_hash,
        "validation_kind": "chronological",
        "estimand": "rank_ic",
        "multiplicity": {
            "n_trials": 1,
            "n_completed": 0,
            "n_superseded": 0,
            "n_failed": 0,
        },
        "status": "planned",
    }


@pytest.fixture
def full_trial_data(sample_config_hash: str) -> dict:
    """Full trial-intent data with all optional fields (synthetic)."""
    return {
        "trial_id": "test-trial-002",
        "owner_decision_ref": "ADR-001",
        "planned_config_sha256": sample_config_hash,
        "validation_kind": "purged_cross_fit",
        "estimand": "long_short_return",
        "family_id": "family-alpha",
        "parent_trial_id": "test-trial-001",
        "multiplicity": {
            "n_trials": 5,
            "n_completed": 2,
            "n_superseded": 1,
            "n_failed": 0,
        },
        "status": "active",
        "previous_status": "approved",
        "created_at": "2026-08-01T12:00:00+00:00",
        "updated_at": "2026-08-01T14:30:00+00:00",
        "description": "A test trial for phase D forward evaluation.",
    }


# ---------------------------------------------------------------------------
# test schema version and basic validation
# ---------------------------------------------------------------------------


def test_schema_version_constant() -> None:
    """Test that schema version constant is defined correctly."""
    assert TRIAL_INTENT_SCHEMA_VERSION == "trial-intent-v1"


def test_minimal_trial_creation(minimal_trial_data: dict) -> None:
    """Test creating a minimal valid TrialIntent."""
    trial = TrialIntent(**minimal_trial_data)
    assert trial.trial_id == "test-trial-001"
    assert trial.owner_decision_ref == "RD-17"
    assert trial.validation_kind == ValidationKind.CHRONOLOGICAL
    assert trial.estimand == Estimand.RANK_IC
    assert trial.status == TrialStatus.PLANNED
    assert trial.schema_version == "trial-intent-v1"


def test_full_trial_creation(full_trial_data: dict) -> None:
    """Test creating a full TrialIntent with all optional fields."""
    trial = TrialIntent(**full_trial_data)
    assert trial.trial_id == "test-trial-002"
    assert trial.family_id == "family-alpha"
    assert trial.parent_trial_id == "test-trial-001"
    assert trial.multiplicity.n_trials == 5
    assert trial.multiplicity.n_completed == 2
    assert trial.status == TrialStatus.ACTIVE
    assert trial.previous_status == TrialStatus.APPROVED
    assert trial.description is not None


# ---------------------------------------------------------------------------
# test fail-closed behavior (missing required fields)
# ---------------------------------------------------------------------------


def test_fail_closed_missing_owner_ref(sample_config_hash: str) -> None:
    """Test that missing owner_decision_ref raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        TrialIntent(
            trial_id="test-trial",
            planned_config_sha256=sample_config_hash,
            validation_kind="chronological",
            estimand="rank_ic",
            multiplicity={"n_trials": 1, "n_completed": 0, "n_superseded": 0, "n_failed": 0},
        )
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("owner_decision_ref",) for e in errors)


def test_fail_closed_missing_config_hash() -> None:
    """Test that missing planned_config_sha256 raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        TrialIntent(
            trial_id="test-trial",
            owner_decision_ref="RD-17",
            validation_kind="chronological",
            estimand="rank_ic",
            multiplicity={"n_trials": 1, "n_completed": 0, "n_superseded": 0, "n_failed": 0},
        )
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("planned_config_sha256",) for e in errors)


def test_fail_closed_missing_validation_kind(sample_config_hash: str) -> None:
    """Test that missing validation_kind raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        TrialIntent(
            trial_id="test-trial",
            owner_decision_ref="RD-17",
            planned_config_sha256=sample_config_hash,
            estimand="rank_ic",
            multiplicity={"n_trials": 1, "n_completed": 0, "n_superseded": 0, "n_failed": 0},
        )
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("validation_kind",) for e in errors)


def test_fail_closed_missing_estimand(sample_config_hash: str) -> None:
    """Test that missing estimand raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        TrialIntent(
            trial_id="test-trial",
            owner_decision_ref="RD-17",
            planned_config_sha256=sample_config_hash,
            validation_kind="chronological",
            multiplicity={"n_trials": 1, "n_completed": 0, "n_superseded": 0, "n_failed": 0},
        )
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("estimand",) for e in errors)


# ---------------------------------------------------------------------------
# test forbidden outcome fields enforcement
# ---------------------------------------------------------------------------


def test_forbidden_outcome_fields_list() -> None:
    """Test that forbidden outcome fields are properly defined."""
    assert "ic" in FORBIDDEN_OUTCOME_FIELDS
    assert "rank_ic" in FORBIDDEN_OUTCOME_FIELDS
    assert "p_value" in FORBIDDEN_OUTCOME_FIELDS
    assert "sharpe_ratio" in FORBIDDEN_OUTCOME_FIELDS
    assert "total_return" in FORBIDDEN_OUTCOME_FIELDS
    assert "accuracy" in FORBIDDEN_OUTCOME_FIELDS
    assert "f1_score" in FORBIDDEN_OUTCOME_FIELDS


def test_assert_no_outcome_fields_passes_on_clean_data() -> None:
    """Test that assert_no_outcome_fields passes on clean data."""
    clean_data = {"trial_id": "test", "owner_decision_ref": "RD-17"}
    # Should not raise
    assert_no_outcome_fields(clean_data)


def test_assert_no_outcome_fields_raises_on_metrics() -> None:
    """Test that assert_no_outcome_fields raises on outcome metrics."""
    dirty_data = {"trial_id": "test", "rank_ic": 0.05, "p_value": 0.01}
    with pytest.raises(ValueError) as exc_info:
        assert_no_outcome_fields(dirty_data)
    assert "observed metrics" in str(exc_info.value).lower()
    assert "rank_ic" in str(exc_info.value)


def test_trial_intent_rejects_forbidden_fields_in_raw_json(sample_config_hash: str) -> None:
    """Test that TrialIntent.from_json rejects forbidden outcome fields."""
    dirty_json = f"""{{
        "trial_id": "test-trial",
        "owner_decision_ref": "RD-17",
        "planned_config_sha256": "{sample_config_hash}",
        "validation_kind": "chronological",
        "estimand": "rank_ic",
        "multiplicity": {{
            "n_trials": 1,
            "n_completed": 0,
            "n_superseded": 0,
            "n_failed": 0
        }},
        "rank_ic": 0.05
    }}"""
    with pytest.raises(ValueError) as exc_info:
        TrialIntent.from_json(dirty_json)
    assert "observed metrics" in str(exc_info.value).lower()


def test_trial_intent_rejects_all_forbidden_fields(sample_config_hash: str) -> None:
    """Test that all forbidden fields are rejected."""
    base_data = {
        "trial_id": "test",
        "owner_decision_ref": "RD-17",
        "planned_config_sha256": sample_config_hash,
        "validation_kind": "chronological",
        "estimand": "rank_ic",
        "multiplicity": {"n_trials": 1, "n_completed": 0, "n_superseded": 0, "n_failed": 0},
    }

    for field in FORBIDDEN_OUTCOME_FIELDS:
        dirty_data = {**base_data, field: 0.5}
        with pytest.raises((ValueError, ValidationError), match=r"observed metrics"):
            TrialIntent(**dirty_data)


def test_trial_intent_extra_forbid_unknown_fields(sample_config_hash: str) -> None:
    """Test that extra='forbid' rejects unknown fields."""
    with pytest.raises(ValidationError) as exc_info:
        TrialIntent(
            trial_id="test-trial",
            owner_decision_ref="RD-17",
            planned_config_sha256=sample_config_hash,
            validation_kind="chronological",
            estimand="rank_ic",
            multiplicity={"n_trials": 1, "n_completed": 0, "n_superseded": 0, "n_failed": 0},
            unknown_field="should_be_rejected",
        )
    errors = exc_info.value.errors()
    assert any("extra" in str(e).lower() for e in errors)


# ---------------------------------------------------------------------------
# test trial-id registry (duplicate rejection)
# ---------------------------------------------------------------------------


def test_register_trial_id_success() -> None:
    """Test that register_trial_id succeeds on first use."""
    clear_trial_id_registry()
    register_trial_id("test-trial-001")
    assert is_trial_id_registered("test-trial-001")


def test_register_trial_id_duplicate_rejection() -> None:
    """Test that duplicate trial IDs are rejected."""
    clear_trial_id_registry()
    register_trial_id("test-trial-001")

    with pytest.raises(ValueError) as exc_info:
        register_trial_id("test-trial-001")
    assert "duplicate" in str(exc_info.value).lower()
    assert "test-trial-001" in str(exc_info.value)


def test_is_trial_id_registered() -> None:
    """Test is_trial_id_registered check."""
    clear_trial_id_registry()
    assert not is_trial_id_registered("test-trial-001")
    register_trial_id("test-trial-001")
    assert is_trial_id_registered("test-trial-001")


def test_clear_trial_id_registry() -> None:
    """Test that clear_trial_id_registry clears the registry."""
    clear_trial_id_registry()
    register_trial_id("test-trial-001")
    assert is_trial_id_registered("test-trial-001")
    clear_trial_id_registry()
    assert not is_trial_id_registered("test-trial-001")


# ---------------------------------------------------------------------------
# test status transition validation
# ---------------------------------------------------------------------------


def test_status_enum_values() -> None:
    """Test that TrialStatus enum has all expected values."""
    assert TrialStatus.PLANNED.value == "planned"
    assert TrialStatus.APPROVED.value == "approved"
    assert TrialStatus.ACTIVE.value == "active"
    assert TrialStatus.SUPERSEDED.value == "superseded"
    assert TrialStatus.CLOSED.value == "closed"
    assert TrialStatus.FAILED.value == "failed"
    assert TrialStatus.REJECTED.value == "rejected"
    assert TrialStatus.BLOCKED.value == "blocked"


def test_valid_status_transitions() -> None:
    """Test that valid status transitions are accepted."""
    assert TrialStatus.PLANNED.can_transition_to(TrialStatus.APPROVED)
    assert TrialStatus.PLANNED.can_transition_to(TrialStatus.REJECTED)
    assert TrialStatus.APPROVED.can_transition_to(TrialStatus.ACTIVE)
    assert TrialStatus.ACTIVE.can_transition_to(TrialStatus.SUPERSEDED)
    assert TrialStatus.ACTIVE.can_transition_to(TrialStatus.CLOSED)
    assert TrialStatus.ACTIVE.can_transition_to(TrialStatus.FAILED)


def test_invalid_status_transitions() -> None:
    """Test that invalid status transitions are rejected."""
    assert not TrialStatus.ACTIVE.can_transition_to(TrialStatus.PLANNED)
    assert not TrialStatus.CLOSED.can_transition_to(TrialStatus.ACTIVE)
    assert not TrialStatus.SUPERSEDED.can_transition_to(TrialStatus.ACTIVE)
    assert not TrialStatus.REJECTED.can_transition_to(TrialStatus.APPROVED)


def test_transition_to_method_success(sample_config_hash: str) -> None:
    """Test successful status transition via transition_to method."""
    trial = TrialIntent(
        trial_id="test-trial",
        owner_decision_ref="RD-17",
        planned_config_sha256=sample_config_hash,
        validation_kind="chronological",
        estimand="rank_ic",
        multiplicity={"n_trials": 1, "n_completed": 0, "n_superseded": 0, "n_failed": 0},
        status=TrialStatus.PLANNED,
    )

    updated_trial = trial.transition_to(TrialStatus.APPROVED)
    assert updated_trial.status == TrialStatus.APPROVED
    assert updated_trial.previous_status == TrialStatus.PLANNED
    assert updated_trial.updated_at is not None


def test_transition_to_method_invalid(sample_config_hash: str) -> None:
    """Test that invalid status transition raises ValueError."""
    trial = TrialIntent(
        trial_id="test-trial",
        owner_decision_ref="RD-17",
        planned_config_sha256=sample_config_hash,
        validation_kind="chronological",
        estimand="rank_ic",
        multiplicity={"n_trials": 1, "n_completed": 0, "n_superseded": 0, "n_failed": 0},
        status=TrialStatus.ACTIVE,
    )

    with pytest.raises(ValueError) as exc_info:
        trial.transition_to(TrialStatus.PLANNED)
    assert "Invalid status transition" in str(exc_info.value)


def test_invalid_status_transition_in_construction(full_trial_data: dict) -> None:
    """Test that invalid status transition is rejected at construction."""
    # INVALID: CLOSED → ACTIVE is not allowed
    full_trial_data["previous_status"] = "closed"
    full_trial_data["status"] = "active"

    with pytest.raises((ValidationError, ValueError)) as exc_info:
        TrialIntent(**full_trial_data)
    assert "Invalid status transition" in str(exc_info.value)


# ---------------------------------------------------------------------------
# test multiplicity accounting
# ---------------------------------------------------------------------------


def test_multiplicity_validation() -> None:
    """Test that Multiplicity enforces consistency."""
    # Valid
    mult = Multiplicity(n_trials=5, n_completed=2, n_superseded=1, n_failed=0)
    assert mult.n_trials == 5
    assert mult.n_completed + mult.n_superseded + mult.n_failed <= mult.n_trials


def test_multiplicity_inconsistency_rejection() -> None:
    """Test that inconsistent multiplicity is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        Multiplicity(n_trials=5, n_completed=3, n_superseded=3, n_failed=0)
    assert "inconsistency" in str(exc_info.value).lower()
    assert "exceeds" in str(exc_info.value).lower()


def test_multiplicity_negative_rejection() -> None:
    """Test that negative counts are rejected."""
    with pytest.raises(ValidationError):
        Multiplicity(n_trials=5, n_completed=-1, n_superseded=0, n_failed=0)


# ---------------------------------------------------------------------------
# test family consistency (no self-reference)
# ------------------------------------------------------------------


def test_parent_trial_id_no_self_reference(sample_config_hash: str) -> None:
    """Test that parent_trial_id cannot be the same as trial_id."""
    with pytest.raises(ValidationError) as exc_info:
        TrialIntent(
            trial_id="test-trial",
            owner_decision_ref="RD-17",
            planned_config_sha256=sample_config_hash,
            validation_kind="chronological",
            estimand="rank_ic",
            multiplicity={"n_trials": 1, "n_completed": 0, "n_superseded": 0, "n_failed": 0},
            parent_trial_id="test-trial",  # SELF-REFERENCE
        )
    assert "self-reference" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# test stable JSON serialization
# ---------------------------------------------------------------------------


def test_stable_json_deterministic(minimal_trial_data: dict) -> None:
    """Test that to_stable_json produces deterministic output."""
    trial1 = TrialIntent(**minimal_trial_data)
    trial2 = TrialIntent(**minimal_trial_data)

    json1 = trial1.to_stable_json()
    json2 = trial2.to_stable_json()

    assert json1 == json2
    # Verify it's valid JSON
    import json
    parsed = json.loads(json1)
    assert parsed["trial_id"] == "test-trial-001"


def test_stable_json_sort_keys(minimal_trial_data: dict) -> None:
    """Test that to_stable_json uses sorted key order."""
    trial = TrialIntent(**minimal_trial_data)
    json_str = trial.to_stable_json()

    # Parse and check keys are in order (sorted)
    import json
    parsed = json.loads(json_str)
    keys = list(parsed.keys())
    assert keys == sorted(keys)


def test_from_json_roundtrip(minimal_trial_data: dict) -> None:
    """Test that from_json/to_stable_json roundtrip preserves data."""
    trial = TrialIntent(**minimal_trial_data)
    json_str = trial.to_stable_json()
    restored = TrialIntent.from_json(json_str)

    assert restored.trial_id == trial.trial_id
    assert restored.owner_decision_ref == trial.owner_decision_ref
    assert restored.planned_config_sha256 == trial.planned_config_sha256
    assert restored.validation_kind == trial.validation_kind
    assert restored.estimand == trial.estimand


def test_from_json_rejects_invalid_json() -> None:
    """Test that from_json rejects invalid JSON."""
    with pytest.raises(json.decoder.JSONDecodeError):
        TrialIntent.from_json("not valid json {bad}")


# ---------------------------------------------------------------------------
# test timestamp normalization
# ---------------------------------------------------------------------------


def test_timestamp_normalization_utc(sample_config_hash: str) -> None:
    """Test that timestamps are normalized to UTC."""
    trial = TrialIntent(
        trial_id="test-trial",
        owner_decision_ref="RD-17",
        planned_config_sha256=sample_config_hash,
        validation_kind="chronological",
        estimand="rank_ic",
        multiplicity={"n_trials": 1, "n_completed": 0, "n_superseded": 0, "n_failed": 0},
        created_at="2026-08-01T12:00:00Z",  # Z suffix
    )
    assert trial.created_at == "2026-08-01T12:00:00+00:00"


def test_timestamp_rejection_no_timezone(sample_config_hash: str) -> None:
    """Test that timestamps without timezone are rejected."""
    with pytest.raises(ValidationError) as exc_info:
        TrialIntent(
            trial_id="test-trial",
            owner_decision_ref="RD-17",
            planned_config_sha256=sample_config_hash,
            validation_kind="chronological",
            estimand="rank_ic",
            multiplicity={"n_trials": 1, "n_completed": 0, "n_superseded": 0, "n_failed": 0},
            created_at="2026-08-01T12:00:00",  # NO TIMEZONE
        )
    assert "invalid iso-8601 utc timestamp" in str(exc_info.value).lower()


def test_timestamp_rejection_invalid_format(sample_config_hash: str) -> None:
    """Test that invalid timestamp formats are rejected."""
    with pytest.raises(ValidationError):
        TrialIntent(
            trial_id="test-trial",
            owner_decision_ref="RD-17",
            planned_config_sha256=sample_config_hash,
            validation_kind="chronological",
            estimand="rank_ic",
            multiplicity={"n_trials": 1, "n_completed": 0, "n_superseded": 0, "n_failed": 0},
            created_at="not-a-timestamp",
        )


# ---------------------------------------------------------------------------
# test config hash validation
# ---------------------------------------------------------------------------


def test_config_hash_validation(sample_config_hash: str) -> None:
    """Test that config hash must be 64 hex characters."""
    # Valid
    trial = TrialIntent(
        trial_id="test-trial",
        owner_decision_ref="RD-17",
        planned_config_sha256=sample_config_hash,
        validation_kind="chronological",
        estimand="rank_ic",
        multiplicity={"n_trials": 1, "n_completed": 0, "n_superseded": 0, "n_failed": 0},
    )
    assert len(trial.planned_config_sha256) == 64


def test_config_hash_too_short(sample_config_hash: str) -> None:
    """Test that config hash < 64 chars is rejected."""
    with pytest.raises(ValidationError):
        TrialIntent(
            trial_id="test-trial",
            owner_decision_ref="RD-17",
            planned_config_sha256="a" * 63,  # TOO SHORT
            validation_kind="chronological",
            estimand="rank_ic",
            multiplicity={"n_trials": 1, "n_completed": 0, "n_superseded": 0, "n_failed": 0},
        )


def test_config_hash_non_hex(sample_config_hash: str) -> None:
    """Test that non-hex config hash is rejected."""
    with pytest.raises(ValidationError):
        TrialIntent(
            trial_id="test-trial",
            owner_decision_ref="RD-17",
            planned_config_sha256="g" * 64,  # NOT HEX
            validation_kind="chronological",
            estimand="rank_ic",
            multiplicity={"n_trials": 1, "n_completed": 0, "n_superseded": 0, "n_failed": 0},
        )


# ---------------------------------------------------------------------------
# test trial_id validation
# ---------------------------------------------------------------------------


def test_trial_id_validation(sample_config_hash: str) -> None:
    """Test that trial_id allows alphanumeric, underscore, hyphen."""
    # Valid IDs
    for valid_id in ["test-trial-001", "trial_123", "TRIAL-ABC_123"]:
        trial = TrialIntent(
            trial_id=valid_id,
            owner_decision_ref="RD-17",
            planned_config_sha256=sample_config_hash,
            validation_kind="chronological",
            estimand="rank_ic",
            multiplicity={"n_trials": 1, "n_completed": 0, "n_superseded": 0, "n_failed": 0},
        )
        assert trial.trial_id == valid_id


def test_trial_id_rejects_invalid_chars(sample_config_hash: str) -> None:
    """Test that trial_id rejects invalid characters."""
    with pytest.raises(ValidationError):
        TrialIntent(
            trial_id="trial.001",  # DOT NOT ALLOWED
            owner_decision_ref="RD-17",
            planned_config_sha256=sample_config_hash,
            validation_kind="chronological",
            estimand="rank_ic",
            multiplicity={"n_trials": 1, "n_completed": 0, "n_superseded": 0, "n_failed": 0},
        )


def test_trial_id_empty_rejection(sample_config_hash: str) -> None:
    """Test that empty trial_id is rejected."""
    with pytest.raises(ValidationError):
        TrialIntent(
            trial_id="",
            owner_decision_ref="RD-17",
            planned_config_sha256=sample_config_hash,
            validation_kind="chronological",
            estimand="rank_ic",
            multiplicity={"n_trials": 1, "n_completed": 0, "n_superseded": 0, "n_failed": 0},
        )


# ---------------------------------------------------------------------------
# test validation_kind and estimand enums
# ---------------------------------------------------------------------------


def test_validation_kind_enum() -> None:
    """Test ValidationKind enum values."""
    assert ValidationKind.CHRONOLOGICAL.value == "chronological"
    assert ValidationKind.PURGED_CROSS_FIT.value == "purged_cross_fit"


def test_estimand_enum() -> None:
    """Test Estimand enum values."""
    assert Estimand.RANK_IC.value == "rank_ic"
    assert Estimand.IC.value == "ic"
    assert Estimand.LONG_SHORT_RETURN.value == "long_short_return"
    assert Estimand.CLASSIFICATION_ACCURACY.value == "classification_accuracy"
    assert Estimand.OTHER.value == "other"


# ---------------------------------------------------------------------------
# test H6 determinism (seed pinning not applicable here, but stable JSON)
# ---------------------------------------------------------------------------


def test_h6_determinism_stable_json(minimal_trial_data: dict) -> None:
    """Test that identical inputs produce byte-identical JSON (H6)."""
    import json

    trial1 = TrialIntent(**minimal_trial_data)
    trial2 = TrialIntent(**minimal_trial_data)

    json1_bytes = trial1.to_stable_json().encode("utf-8")
    json2_bytes = trial2.to_stable_json().encode("utf-8")

    # Byte-identical
    assert json1_bytes == json2_bytes

    # Parse and verify content
    parsed1 = json.loads(json1_bytes)
    parsed2 = json.loads(json2_bytes)
    assert parsed1 == parsed2
