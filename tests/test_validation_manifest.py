"""Tests for validation_manifest.py (RD-02) — hermetic, synthetic fixtures only.

These tests verify that the ValidationManifest schema:
1. Distinguishes chronological from purged_cross_fit validation kinds
2. Fails closed when time boundaries, hash, or label availability are missing
3. Rejects any payload carrying outcome metrics (IC, returns, p-values, CIs)
4. Serializes to stable JSON (deterministic key order) for bit-stable replay checks
5. Enforces ISO-8601 UTC timestamps with timezone

All fixtures are synthetic and labeled; no real data, no network, no git writes.
H6 determinism: seeds pinned to 0 where randomness applies (not used in this schema,
but the test framework uses deterministic fixtures).
"""
from __future__ import annotations

import json

import pytest

from aionis.eval.validation_manifest import (
    FORBIDDEN_OUTCOME_FIELDS,
    LabelAvailability,
    SplitTimeBoundaries,
    ValidationKind,
    ValidationManifest,
    assert_no_outcome_fields,
)

# ---------------------------------------------------------------------------
# synthetic fixtures (labeled, deterministic)
# ---------------------------------------------------------------------------


def _valid_boundaries() -> dict:
    """A valid SplitTimeBoundaries fixture."""
    return {
        "train_start": "2026-01-05T00:00:00+00:00",
        "train_end": "2026-06-30T00:00:00+00:00",
        "test_start": "2026-07-01T00:00:00+00:00",
        "test_end": "2026-07-31T00:00:00+00:00",
    }


def _valid_manifest_dict(override: dict | None = None) -> dict:
    """A minimal valid ValidationManifest dictionary."""
    base: dict = {
        "validation_kind": "chronological",
        "time_boundaries": _valid_boundaries(),
        "embargo_sessions": 21,
        "universe_hash": "abc123def456",
        "label_availability": "available",
        "code_version": "v1.0.0",
    }
    if override:
        base.update(override)
    return base


# ---------------------------------------------------------------------------
# validation_kind enum tests
# ---------------------------------------------------------------------------


def test_validation_kind_enum() -> None:
    """ValidationKind must distinguish chronological from purged_cross_fit."""
    assert ValidationKind.CHRONOLOGICAL == "chronological"
    assert ValidationKind.PURGED_CROSS_FIT == "purged_cross_fit"
    assert len(ValidationKind) == 2


def test_validation_kind_rejects_unknown() -> None:
    """ValidationKind must reject unknown/ambiguous kinds."""
    with pytest.raises(ValueError, match="Input should be"):
        ValidationManifest(**_valid_manifest_dict({"validation_kind": "unknown"}))


# ---------------------------------------------------------------------------
# label availability enum tests
# ---------------------------------------------------------------------------


def test_label_availability_enum() -> None:
    """LabelAvailability must distinguish available/partial/missing."""
    assert LabelAvailability.AVAILABLE == "available"
    assert LabelAvailability.PARTIAL == "partial"
    assert LabelAvailability.MISSING == "missing"
    assert len(LabelAvailability) == 3


# ---------------------------------------------------------------------------
# time boundaries tests
# ---------------------------------------------------------------------------


def test_split_time_boundaries_valid() -> None:
    """SplitTimeBoundaries accepts valid ISO-8601 UTC timestamps."""
    boundaries = SplitTimeBoundaries(**_valid_boundaries())
    assert boundaries.train_start == "2026-01-05T00:00:00+00:00"
    assert boundaries.train_end == "2026-06-30T00:00:00+00:00"
    assert boundaries.test_start == "2026-07-01T00:00:00+00:00"
    assert boundaries.test_end == "2026-07-31T00:00:00+00:00"


def test_split_time_boundaries_normalizes_z_suffix() -> None:
    """SplitTimeBoundaries normalizes Z suffix to +00:00."""
    boundaries = SplitTimeBoundaries(
        train_start="2026-01-05T00:00:00Z",
        train_end="2026-06-30T00:00:00Z",
        test_start="2026-07-01T00:00:00Z",
        test_end="2026-07-31T00:00:00Z",
    )
    assert boundaries.train_start == "2026-01-05T00:00:00+00:00"
    assert boundaries.test_start == "2026-07-01T00:00:00+00:00"


def test_split_time_boundaries_requires_timezone() -> None:
    """SplitTimeBoundaries rejects timestamps without timezone."""
    with pytest.raises(ValueError, match="Invalid ISO-8601 UTC timestamp"):
        SplitTimeBoundaries(
            train_start="2026-01-05T00:00:00",
            train_end="2026-06-30T00:00:00",
            test_start="2026-07-01T00:00:00",
            test_end="2026-07-31T00:00:00",
        )


def test_split_time_boundaries_requires_all_fields() -> None:
    """SplitTimeBoundaries fails closed when any field is missing."""
    with pytest.raises(ValueError, match="missing"):
        SplitTimeBoundaries(
            train_start="2026-01-05T00:00:00+00:00",
            train_end="2026-06-30T00:00:00+00:00",
            # test_start and test_end missing
        )


def test_split_time_boundaries_rejects_invalid_format() -> None:
    """SplitTimeBoundaries rejects invalid ISO-8601 timestamps."""
    with pytest.raises(ValueError, match="Invalid ISO-8601"):
        SplitTimeBoundaries(
            train_start="not-a-date",
            train_end="2026-06-30T00:00:00+00:00",
            test_start="2026-07-01T00:00:00+00:00",
            test_end="2026-07-31T00:00:00+00:00",
        )


# ---------------------------------------------------------------------------
# manifest validation tests
# ---------------------------------------------------------------------------


def test_manifest_minimal_valid() -> None:
    """ValidationManifest accepts minimal valid input."""
    manifest = ValidationManifest(**_valid_manifest_dict())
    assert manifest.validation_kind == ValidationKind.CHRONOLOGICAL
    assert manifest.embargo_sessions == 21
    assert manifest.universe_hash == "abc123def456"
    assert manifest.label_availability == LabelAvailability.AVAILABLE
    assert manifest.code_version == "v1.0.0"
    assert manifest.created_at is None
    assert manifest.fold_index is None


def test_manifest_all_fields() -> None:
    """ValidationManifest accepts all fields including optional metadata."""
    manifest_dict = _valid_manifest_dict({
        "created_at": "2026-08-01T12:00:00Z",
        "fold_index": 1,
    })
    manifest = ValidationManifest(**manifest_dict)
    assert manifest.created_at == "2026-08-01T12:00:00+00:00"
    assert manifest.fold_index == 1


def test_manifest_requires_time_boundaries() -> None:
    """ValidationManifest fails closed when time_boundaries is missing."""
    data = _valid_manifest_dict()
    del data["time_boundaries"]
    with pytest.raises(ValueError, match="missing"):
        ValidationManifest(**data)


def test_manifest_requires_embargo() -> None:
    """ValidationManifest fails closed when embargo_sessions is missing."""
    data = _valid_manifest_dict()
    del data["embargo_sessions"]
    with pytest.raises(ValueError, match="missing"):
        ValidationManifest(**data)


def test_manifest_requires_universe_hash() -> None:
    """ValidationManifest fails closed when universe_hash is missing."""
    data = _valid_manifest_dict()
    del data["universe_hash"]
    with pytest.raises(ValueError, match="missing"):
        ValidationManifest(**data)


def test_manifest_requires_label_availability() -> None:
    """ValidationManifest fails closed when label_availability is missing."""
    data = _valid_manifest_dict()
    del data["label_availability"]
    with pytest.raises(ValueError, match="missing"):
        ValidationManifest(**data)


def test_manifest_requires_code_version() -> None:
    """ValidationManifest fails closed when code_version is missing."""
    data = _valid_manifest_dict()
    del data["code_version"]
    with pytest.raises(ValueError, match="missing"):
        ValidationManifest(**data)


def test_manifest_embargo_non_negative() -> None:
    """ValidationManifest enforces embargo_sessions >= 0."""
    with pytest.raises(ValueError, match="greater than or equal to 0"):
        ValidationManifest(**_valid_manifest_dict({"embargo_sessions": -1}))


def test_manifest_fold_index_positive() -> None:
    """ValidationManifest enforces fold_index >= 1 when provided."""
    with pytest.raises(ValueError, match="greater than or equal to 1"):
        ValidationManifest(**_valid_manifest_dict({"fold_index": 0}))


def test_manifest_universe_hash_non_empty() -> None:
    """ValidationManifest rejects empty universe_hash."""
    with pytest.raises(ValueError, match="at least 1 character"):
        ValidationManifest(**_valid_manifest_dict({"universe_hash": ""}))


def test_manifest_code_version_non_empty() -> None:
    """ValidationManifest rejects empty code_version."""
    with pytest.raises(ValueError, match="at least 1 character"):
        ValidationManifest(**_valid_manifest_dict({"code_version": ""}))


def test_manifest_created_at_normalizes_z() -> None:
    """ValidationManifest normalizes created_at Z suffix to +00:00."""
    manifest = ValidationManifest(
        **_valid_manifest_dict({"created_at": "2026-08-01T12:00:00Z"})
    )
    assert manifest.created_at == "2026-08-01T12:00:00+00:00"


def test_manifest_created_at_requires_timezone() -> None:
    """ValidationManifest rejects created_at without timezone."""
    with pytest.raises(ValueError, match="Invalid ISO-8601 UTC created_at"):
        ValidationManifest(
            **_valid_manifest_dict({"created_at": "2026-08-01T12:00:00"})
        )


# ---------------------------------------------------------------------------
# outcome metric rejection tests
# ---------------------------------------------------------------------------


def test_forbidden_outcome_fields_defined() -> None:
    """FORBIDDEN_OUTCOME_FIELDS must include IC, returns, p-values, CIs."""
    assert "ic" in FORBIDDEN_OUTCOME_FIELDS
    assert "rank_ic" in FORBIDDEN_OUTCOME_FIELDS
    assert "mean_ic" in FORBIDDEN_OUTCOME_FIELDS
    assert "t_stat" in FORBIDDEN_OUTCOME_FIELDS
    assert "p_value" in FORBIDDEN_OUTCOME_FIELDS
    assert "ci_half" in FORBIDDEN_OUTCOME_FIELDS
    assert "ci_lower" in FORBIDDEN_OUTCOME_FIELDS
    assert "ci_upper" in FORBIDDEN_OUTCOME_FIELDS
    assert "sharpe_ratio" in FORBIDDEN_OUTCOME_FIELDS
    assert "total_return" in FORBIDDEN_OUTCOME_FIELDS
    assert "annual_return" in FORBIDDEN_OUTCOME_FIELDS
    assert "volatility" in FORBIDDEN_OUTCOME_FIELDS
    assert "max_drawdown" in FORBIDDEN_OUTCOME_FIELDS
    assert "hit_rate" in FORBIDDEN_OUTCOME_FIELDS


def test_assert_no_outcome_fields_passes_clean() -> None:
    """assert_no_outcome_fields passes clean dictionaries."""
    assert_no_outcome_fields({"validation_kind": "chronological"})
    assert_no_outcome_fields({})


def test_assert_no_outcome_fields_rejects_ic() -> None:
    """assert_no_outcome_fields rejects IC fields."""
    with pytest.raises(ValueError, match="must not contain outcome metrics"):
        assert_no_outcome_fields({"ic": 0.05})


def test_assert_no_outcome_fields_rejects_rank_ic() -> None:
    """assert_no_outcome_fields rejects rank_ic fields."""
    with pytest.raises(ValueError, match="must not contain outcome metrics"):
        assert_no_outcome_fields({"rank_ic": 0.03})


def test_assert_no_outcome_fields_rejects_return() -> None:
    """assert_no_outcome_fields rejects return fields."""
    with pytest.raises(ValueError, match="must not contain outcome metrics"):
        assert_no_outcome_fields({"total_return": 0.15})


def test_assert_no_outcome_fields_rejects_p_value() -> None:
    """assert_no_outcome_fields rejects p_value fields."""
    with pytest.raises(ValueError, match="must not contain outcome metrics"):
        assert_no_outcome_fields({"p_value": 0.01})


def test_assert_no_outcome_fields_rejects_ci() -> None:
    """assert_no_outcome_fields rejects CI fields."""
    with pytest.raises(ValueError, match="must not contain outcome metrics"):
        assert_no_outcome_fields({"ci_half": 0.02})
    with pytest.raises(ValueError, match="must not contain outcome metrics"):
        assert_no_outcome_fields({"ci_lower": -0.05})
    with pytest.raises(ValueError, match="must not contain outcome metrics"):
        assert_no_outcome_fields({"ci_upper": 0.15})


def test_manifest_rejects_outcome_fields_via_validator() -> None:
    """ValidationManifest rejects outcome fields via pre-parse model_validator."""
    data = _valid_manifest_dict({"mean_ic": 0.05})
    with pytest.raises(ValueError, match="must not contain outcome metrics"):
        ValidationManifest(**data)


def test_manifest_rejects_outcome_fields_from_json() -> None:
    """ValidationManifest.from_json rejects outcome fields."""
    raw = json.dumps(_valid_manifest_dict({"sharpe_ratio": 1.5}))
    with pytest.raises(ValueError, match="must not contain outcome metrics"):
        ValidationManifest.from_json(raw)


# ---------------------------------------------------------------------------
# JSON serialization tests
# ---------------------------------------------------------------------------


def test_manifest_to_stable_json_deterministic() -> None:
    """ValidationManifest.to_stable_json produces deterministic JSON."""
    manifest1 = ValidationManifest(**_valid_manifest_dict())
    manifest2 = ValidationManifest(**_valid_manifest_dict())

    json1 = manifest1.to_stable_json()
    json2 = manifest2.to_stable_json()

    # Bit-identical JSON for identical manifests
    assert json1 == json2
    assert json1.encode() == json2.encode()


def test_manifest_to_stable_json_sorted_keys() -> None:
    """ValidationManifest.to_stable_json uses sort_keys=True."""
    manifest = ValidationManifest(**_valid_manifest_dict())
    json_str = manifest.to_stable_json()

    # Parse to verify it's valid JSON
    parsed = json.loads(json_str)
    assert isinstance(parsed, dict)

    # Check that keys are alphabetically sorted in the serialized string
    # (sort_keys=True produces deterministic key order)
    keys = list(parsed.keys())
    assert keys == sorted(keys)


def test_manifest_from_json_roundtrip() -> None:
    """ValidationManifest.from_json roundtrips with to_stable_json."""
    original = ValidationManifest(**_valid_manifest_dict())
    json_str = original.to_stable_json()
    restored = ValidationManifest.from_json(json_str)

    assert restored.validation_kind == original.validation_kind
    assert restored.embargo_sessions == original.embargo_sessions
    assert restored.universe_hash == original.universe_hash
    assert restored.label_availability == original.label_availability
    assert restored.code_version == original.code_version


def test_manifest_from_json_rejects_invalid() -> None:
    """ValidationManifest.from_json rejects invalid JSON."""
    with pytest.raises(json.JSONDecodeError):
        ValidationManifest.from_json("not json")


def test_manifest_extra_fields_forbidden() -> None:
    """ValidationManifest rejects extra fields via extra='forbid'."""
    data = _valid_manifest_dict({"unexpected_field": "surprise"})
    with pytest.raises(ValueError, match="extra"):
        ValidationManifest(**data)


# ---------------------------------------------------------------------------
# validation kind distinction tests
# ---------------------------------------------------------------------------


def test_chronological_manifest() -> None:
    """ValidationManifest accepts chronological validation kind."""
    manifest = ValidationManifest(
        **_valid_manifest_dict({"validation_kind": "chronological"})
    )
    assert manifest.validation_kind == ValidationKind.CHRONOLOGICAL


def test_purged_cross_fit_manifest() -> None:
    """ValidationManifest accepts purged_cross_fit validation kind."""
    manifest = ValidationManifest(
        **_valid_manifest_dict({"validation_kind": "purged_cross_fit"})
    )
    assert manifest.validation_kind == ValidationKind.PURGED_CROSS_FIT


def test_validation_kind_explicit_distinction() -> None:
    """ValidationKind enum ensures explicit distinction between the two kinds."""
    chronological = ValidationManifest(
        **_valid_manifest_dict({"validation_kind": "chronological"})
    )
    cross_fit = ValidationManifest(
        **_valid_manifest_dict({"validation_kind": "purged_cross_fit"})
    )

    # They are different validation kinds
    assert chronological.validation_kind != cross_fit.validation_kind

    # Both serialize to distinct values
    chrono_json = chronological.to_stable_json()
    cross_fit_json = cross_fit.to_stable_json()

    assert "chronological" in chrono_json
    assert "purged_cross_fit" in cross_fit_json
    assert chrono_json != cross_fit_json


# ---------------------------------------------------------------------------
# edge cases
# ---------------------------------------------------------------------------


def test_manifest_fold_index_optional() -> None:
    """ValidationManifest accepts manifest without fold_index."""
    manifest = ValidationManifest(**_valid_manifest_dict())
    assert manifest.fold_index is None


def test_manifest_created_at_optional() -> None:
    """ValidationManifest accepts manifest without created_at."""
    manifest = ValidationManifest(**_valid_manifest_dict())
    assert manifest.created_at is None


def test_embargo_zero_allowed() -> None:
    """ValidationManifest allows embargo_sessions=0 (no embargo)."""
    manifest = ValidationManifest(
        **_valid_manifest_dict({"embargo_sessions": 0})
    )
    assert manifest.embargo_sessions == 0


def test_label_availability_all_values() -> None:
    """ValidationManifest accepts all LabelAvailability values."""
    for availability in ["available", "partial", "missing"]:
        manifest = ValidationManifest(
            **_valid_manifest_dict({"label_availability": availability})
        )
        assert manifest.label_availability.value == availability
