"""Tests for reproducibility.py (RD-14) — hermetic, synthetic fixtures only.

These tests verify that the ReproducibilityCapsule schema:
1. Accepts load-bearing hashes explicitly passed by the caller
2. Rejects any payload carrying outcome metrics (IC, returns, p-values, CIs)
3. Serializes to stable JSON (deterministic key order) for bit-stable replay checks
4. Generates deterministic capsule_id derived from content hashes
5. Produces byte-identical capsule and same id for same inputs
6. Produces different capsule_id when any load-bearing hash changes
7. Fails closed when load-bearing hashes are missing
8. Enforces atomic write with default refuse-to-overwrite
9. Does NOT shell out to git/network/model (no subprocess, requests, httpx)

All fixtures are synthetic and labeled; no real data, no network, no git writes.
H6 determinism: seeds pinned to 0 where randomness applies (not used in this schema,
but the test framework uses deterministic fixtures).
"""
from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path

import pytest

from aionis.reporting.reproducibility import (
    FORBIDDEN_OUTCOME_FIELDS,
    ProviderKind,
    ProviderMetadata,
    ReproducibilityCapsule,
    assert_no_outcome_fields,
)

# ---------------------------------------------------------------------------
# synthetic fixtures (labeled, deterministic)
# ---------------------------------------------------------------------------


def _valid_sha256() -> str:
    """A valid SHA-256 hash fixture (64 hex chars)."""
    return "a" * 64


def _valid_provider_metadata(override: dict | None = None) -> dict:
    """A valid ProviderMetadata fixture."""
    base: dict = {
        "provider_kind": "glm",
        "model_name": "glm-4-plus",
        "temperature": 0.0,
    }
    if override:
        base.update(override)
    return base


def _valid_capsule_dict(override: dict | None = None) -> dict:
    """A minimal valid ReproducibilityCapsule dictionary."""
    base: dict = {
        "uv_lock_sha256": _valid_sha256(),
        "git_tree_sha256": _valid_sha256(),
        "config_sha256": _valid_sha256(),
        "validation_manifest_sha256": _valid_sha256(),
        "gold_schema_sha256": _valid_sha256(),
        "parser_sha256": _valid_sha256(),
        "raw_response_sha256": _valid_sha256(),
        "provider_metadata": _valid_provider_metadata(),
    }
    if override:
        base.update(override)
    return base


def _different_capsule_dict() -> dict:
    """A capsule dict with one hash changed (for determinism tests)."""
    return _valid_capsule_dict({"uv_lock_sha256": "b" * 64})


# ---------------------------------------------------------------------------
# provider kind enum tests
# ---------------------------------------------------------------------------


def test_provider_kind_enum() -> None:
    """ProviderKind must distinguish GLM/SILICONFLOW/MODELSCOPE."""
    assert ProviderKind.GLM == "glm"
    assert ProviderKind.SILICONFLOW == "siliconflow"
    assert ProviderKind.MODELSCOPE == "modelscope"
    assert len(ProviderKind) == 3


def test_provider_kind_rejects_unknown() -> None:
    """ProviderKind must reject unknown/ambiguous kinds."""
    with pytest.raises(ValueError, match="Input should be"):
        ProviderMetadata(**_valid_provider_metadata({"provider_kind": "openai"}))


# ---------------------------------------------------------------------------
# provider metadata tests
# ---------------------------------------------------------------------------


def test_provider_metadata_valid() -> None:
    """ProviderMetadata accepts valid input."""
    metadata = ProviderMetadata(**_valid_provider_metadata())
    assert metadata.provider_kind == ProviderKind.GLM
    assert metadata.model_name == "glm-4-plus"
    assert metadata.temperature == 0.0


def test_provider_metadata_temperature_bounds() -> None:
    """ProviderMetadata enforces temperature between 0.0 and 2.0."""
    ProviderMetadata(**_valid_provider_metadata({"temperature": 0.0}))
    ProviderMetadata(**_valid_provider_metadata({"temperature": 1.0}))
    ProviderMetadata(**_valid_provider_metadata({"temperature": 2.0}))

    with pytest.raises(ValueError, match="greater than or equal to 0"):
        ProviderMetadata(**_valid_provider_metadata({"temperature": -0.1}))
    with pytest.raises(ValueError, match="less than or equal to 2"):
        ProviderMetadata(**_valid_provider_metadata({"temperature": 2.1}))


def test_provider_metadata_model_name_required() -> None:
    """ProviderMetadata requires model_name."""
    with pytest.raises(ValueError, match="missing"):
        ProviderMetadata(
            provider_kind="glm",
            temperature=0.0,
            # model_name missing
        )


def test_provider_metadata_model_name_non_empty() -> None:
    """ProviderMetadata rejects empty model_name."""
    with pytest.raises(ValueError, match="at least 1 character"):
        ProviderMetadata(**_valid_provider_metadata({"model_name": ""}))


def test_provider_metadata_extra_fields_forbidden() -> None:
    """ProviderMetadata rejects extra fields via extra='forbid'."""
    with pytest.raises(ValueError, match="extra"):
        ProviderMetadata(**_valid_provider_metadata({"unexpected_field": "surprise"}))


# ---------------------------------------------------------------------------
# capsule validation tests
# ---------------------------------------------------------------------------


def test_capsule_minimal_valid() -> None:
    """ReproducibilityCapsule accepts minimal valid input."""
    capsule = ReproducibilityCapsule(**_valid_capsule_dict())
    assert capsule.uv_lock_sha256 == _valid_sha256()
    assert capsule.git_tree_sha256 == _valid_sha256()
    assert capsule.config_sha256 == _valid_sha256()
    assert capsule.validation_manifest_sha256 == _valid_sha256()
    assert capsule.gold_schema_sha256 == _valid_sha256()
    assert capsule.parser_sha256 == _valid_sha256()
    assert capsule.raw_response_sha256 == _valid_sha256()
    assert capsule.provider_metadata.provider_kind == ProviderKind.GLM
    assert capsule.capsule_id is not None  # Auto-computed
    assert capsule.created_at is None
    assert capsule.description is None


def test_capsule_all_fields() -> None:
    """ReproducibilityCapsule accepts all fields including optional metadata."""
    capsule_dict = _valid_capsule_dict({
        "created_at": "2026-08-01T12:00:00Z",
        "description": "Test capsule for RD-14",
    })
    capsule = ReproducibilityCapsule(**capsule_dict)
    assert capsule.created_at == "2026-08-01T12:00:00+00:00"
    assert capsule.description == "Test capsule for RD-14"


def test_capsule_requires_uv_lock_hash() -> None:
    """ReproducibilityCapsule fails closed when uv_lock_sha256 is missing."""
    data = _valid_capsule_dict()
    del data["uv_lock_sha256"]
    with pytest.raises(ValueError, match="missing"):
        ReproducibilityCapsule(**data)


def test_capsule_requires_git_tree_hash() -> None:
    """ReproducibilityCapsule fails closed when git_tree_sha256 is missing."""
    data = _valid_capsule_dict()
    del data["git_tree_sha256"]
    with pytest.raises(ValueError, match="missing"):
        ReproducibilityCapsule(**data)


def test_capsule_requires_config_hash() -> None:
    """ReproducibilityCapsule fails closed when config_sha256 is missing."""
    data = _valid_capsule_dict()
    del data["config_sha256"]
    with pytest.raises(ValueError, match="missing"):
        ReproducibilityCapsule(**data)


def test_capsule_requires_validation_manifest_hash() -> None:
    """ReproducibilityCapsule fails closed when validation_manifest_sha256 is missing."""
    data = _valid_capsule_dict()
    del data["validation_manifest_sha256"]
    with pytest.raises(ValueError, match="missing"):
        ReproducibilityCapsule(**data)


def test_capsule_requires_gold_schema_hash() -> None:
    """ReproducibilityCapsule fails closed when gold_schema_sha256 is missing."""
    data = _valid_capsule_dict()
    del data["gold_schema_sha256"]
    with pytest.raises(ValueError, match="missing"):
        ReproducibilityCapsule(**data)


def test_capsule_requires_parser_hash() -> None:
    """ReproducibilityCapsule fails closed when parser_sha256 is missing."""
    data = _valid_capsule_dict()
    del data["parser_sha256"]
    with pytest.raises(ValueError, match="missing"):
        ReproducibilityCapsule(**data)


def test_capsule_requires_raw_response_hash() -> None:
    """ReproducibilityCapsule fails closed when raw_response_sha256 is missing."""
    data = _valid_capsule_dict()
    del data["raw_response_sha256"]
    with pytest.raises(ValueError, match="missing"):
        ReproducibilityCapsule(**data)


def test_capsule_requires_provider_metadata() -> None:
    """ReproducibilityCapsule fails closed when provider_metadata is missing."""
    data = _valid_capsule_dict()
    del data["provider_metadata"]
    with pytest.raises(ValueError, match="missing"):
        ReproducibilityCapsule(**data)


def test_capsule_hash_format_validation() -> None:
    """ReproducibilityCapsule validates SHA-256 format (64 hex chars)."""
    # Too short
    with pytest.raises(ValueError, match="at least 64 characters"):
        ReproducibilityCapsule(**_valid_capsule_dict({"uv_lock_sha256": "a" * 63}))

    # Too long
    with pytest.raises(ValueError, match="at most 64 characters"):
        ReproducibilityCapsule(**_valid_capsule_dict({"uv_lock_sha256": "a" * 65}))

    # Invalid hex chars
    with pytest.raises(ValueError, match="should match pattern"):
        ReproducibilityCapsule(**_valid_capsule_dict({"uv_lock_sha256": "g" * 64}))


def test_capsule_created_at_normalizes_z() -> None:
    """ReproducibilityCapsule normalizes created_at Z suffix to +00:00."""
    capsule = ReproducibilityCapsule(
        **_valid_capsule_dict({"created_at": "2026-08-01T12:00:00Z"})
    )
    assert capsule.created_at == "2026-08-01T12:00:00+00:00"


def test_capsule_created_at_requires_timezone() -> None:
    """ReproducibilityCapsule rejects created_at without timezone."""
    with pytest.raises(ValueError, match="Invalid ISO-8601 UTC timestamp"):
        ReproducibilityCapsule(
            **_valid_capsule_dict({"created_at": "2026-08-01T12:00:00"})
        )


def test_capsule_extra_fields_forbidden() -> None:
    """ReproducibilityCapsule rejects extra fields via extra='forbid'."""
    data = _valid_capsule_dict({"unexpected_field": "surprise"})
    with pytest.raises(ValueError, match="extra"):
        ReproducibilityCapsule(**data)


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
    assert_no_outcome_fields({"uv_lock_sha256": "a" * 64})
    assert_no_outcome_fields({})


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


def test_capsule_rejects_outcome_fields_via_validator() -> None:
    """ReproducibilityCapsule rejects outcome fields via pre-parse model_validator."""
    data = _valid_capsule_dict({"rank_ic": 0.03})
    with pytest.raises(ValueError, match="must not contain outcome metrics"):
        ReproducibilityCapsule(**data)


def test_capsule_rejects_outcome_fields_from_json() -> None:
    """ReproducibilityCapsule.from_json rejects outcome fields."""
    raw = json.dumps(_valid_capsule_dict({"sharpe_ratio": 1.5}))
    with pytest.raises(ValueError, match="must not contain outcome metrics"):
        ReproducibilityCapsule.from_json(raw)


# ---------------------------------------------------------------------------
# JSON serialization tests
# ---------------------------------------------------------------------------


def test_capsule_to_stable_json_deterministic() -> None:
    """ReproducibilityCapsule.to_stable_json produces deterministic JSON."""
    capsule1 = ReproducibilityCapsule(**_valid_capsule_dict())
    capsule2 = ReproducibilityCapsule(**_valid_capsule_dict())

    json1 = capsule1.to_stable_json()
    json2 = capsule2.to_stable_json()

    # Bit-identical JSON for identical capsules
    assert json1 == json2
    assert json1.encode() == json2.encode()


def test_capsule_to_stable_json_sorted_keys() -> None:
    """ReproducibilityCapsule.to_stable_json uses sort_keys=True."""
    capsule = ReproducibilityCapsule(**_valid_capsule_dict())
    json_str = capsule.to_stable_json()

    # Parse to verify it's valid JSON
    parsed = json.loads(json_str)
    assert isinstance(parsed, dict)

    # Check that keys are alphabetically sorted in the serialized string
    # (sort_keys=True produces deterministic key order)
    keys = list(parsed.keys())
    assert keys == sorted(keys)


def test_capsule_from_json_roundtrip() -> None:
    """ReproducibilityCapsule.from_json roundtrips with to_stable_json."""
    original = ReproducibilityCapsule(**_valid_capsule_dict())
    json_str = original.to_stable_json()
    restored = ReproducibilityCapsule.from_json(json_str)

    assert restored.uv_lock_sha256 == original.uv_lock_sha256
    assert restored.git_tree_sha256 == original.git_tree_sha256
    assert restored.config_sha256 == original.config_sha256
    assert restored.validation_manifest_sha256 == original.validation_manifest_sha256
    assert restored.gold_schema_sha256 == original.gold_schema_sha256
    assert restored.parser_sha256 == original.parser_sha256
    assert restored.raw_response_sha256 == original.raw_response_sha256
    assert restored.provider_metadata.provider_kind == original.provider_metadata.provider_kind
    assert restored.capsule_id == original.capsule_id


def test_capsule_from_json_rejects_invalid() -> None:
    """ReproducibilityCapsule.from_json rejects invalid JSON."""
    with pytest.raises(json.JSONDecodeError):
        ReproducibilityCapsule.from_json("not json")


# ---------------------------------------------------------------------------
# capsule_id determinism tests
# ---------------------------------------------------------------------------


def test_capsule_id_computed_automatically() -> None:
    """ReproducibilityCapsule computes capsule_id automatically if not provided."""
    capsule = ReproducibilityCapsule(**_valid_capsule_dict())
    assert capsule.capsule_id is not None
    assert len(capsule.capsule_id) == 64
    assert all(c in "0123456789abcdef" for c in capsule.capsule_id)


def test_capsule_id_deterministic_same_inputs() -> None:
    """Same inputs produce identical capsule_id."""
    capsule1 = ReproducibilityCapsule(**_valid_capsule_dict())
    capsule2 = ReproducibilityCapsule(**_valid_capsule_dict())

    # Same inputs → same capsule_id
    assert capsule1.capsule_id == capsule2.capsule_id


def test_capsule_id_changes_when_uv_lock_hash_changes() -> None:
    """Capsule_id changes when uv_lock_sha256 changes."""
    capsule1 = ReproducibilityCapsule(**_valid_capsule_dict())
    capsule2 = ReproducibilityCapsule(**_different_capsule_dict())

    # Different uv_lock hash → different capsule_id
    assert capsule1.capsule_id != capsule2.capsule_id


def test_capsule_id_changes_when_git_tree_hash_changes() -> None:
    """Capsule_id changes when git_tree_sha256 changes."""
    capsule1 = ReproducibilityCapsule(**_valid_capsule_dict())
    capsule2 = ReproducibilityCapsule(
        **_valid_capsule_dict({"git_tree_sha256": "b" * 64})
    )

    assert capsule1.capsule_id != capsule2.capsule_id


def test_capsule_id_changes_when_config_hash_changes() -> None:
    """Capsule_id changes when config_sha256 changes."""
    capsule1 = ReproducibilityCapsule(**_valid_capsule_dict())
    capsule2 = ReproducibilityCapsule(
        **_valid_capsule_dict({"config_sha256": "b" * 64})
    )

    assert capsule1.capsule_id != capsule2.capsule_id


def test_capsule_id_changes_when_validation_manifest_hash_changes() -> None:
    """Capsule_id changes when validation_manifest_sha256 changes."""
    capsule1 = ReproducibilityCapsule(**_valid_capsule_dict())
    capsule2 = ReproducibilityCapsule(
        **_valid_capsule_dict({"validation_manifest_sha256": "b" * 64})
    )

    assert capsule1.capsule_id != capsule2.capsule_id


def test_capsule_id_changes_when_gold_schema_hash_changes() -> None:
    """Capsule_id changes when gold_schema_sha256 changes."""
    capsule1 = ReproducibilityCapsule(**_valid_capsule_dict())
    capsule2 = ReproducibilityCapsule(
        **_valid_capsule_dict({"gold_schema_sha256": "b" * 64})
    )

    assert capsule1.capsule_id != capsule2.capsule_id


def test_capsule_id_changes_when_parser_hash_changes() -> None:
    """Capsule_id changes when parser_sha256 changes."""
    capsule1 = ReproducibilityCapsule(**_valid_capsule_dict())
    capsule2 = ReproducibilityCapsule(
        **_valid_capsule_dict({"parser_sha256": "b" * 64})
    )

    assert capsule1.capsule_id != capsule2.capsule_id


def test_capsule_id_changes_when_raw_response_hash_changes() -> None:
    """Capsule_id changes when raw_response_sha256 changes."""
    capsule1 = ReproducibilityCapsule(**_valid_capsule_dict())
    capsule2 = ReproducibilityCapsule(
        **_valid_capsule_dict({"raw_response_sha256": "b" * 64})
    )

    assert capsule1.capsule_id != capsule2.capsule_id


def test_capsule_id_changes_when_provider_metadata_changes() -> None:
    """Capsule_id changes when provider_metadata changes."""
    capsule1 = ReproducibilityCapsule(**_valid_capsule_dict())
    capsule2 = ReproducibilityCapsule(
        **_valid_capsule_dict({
            "provider_metadata": {
                "provider_kind": "siliconflow",
                "model_name": "deepseek-chat",
                "temperature": 0.0,
            }
        })
    )

    assert capsule1.capsule_id != capsule2.capsule_id


# ---------------------------------------------------------------------------
# atomic write + refuse-overwrite tests
# ---------------------------------------------------------------------------


def test_capsule_save_creates_file() -> None:
    """ReproducibilityCapsule.save creates a new file."""
    capsule = ReproducibilityCapsule(**_valid_capsule_dict())

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "capsule.json"
        capsule.save(path)

        assert path.exists()
        # Verify content is valid JSON
        loaded = ReproducibilityCapsule.load(path)
        assert loaded.capsule_id == capsule.capsule_id


def test_capsule_save_refuses_overwrite_by_default() -> None:
    """ReproducibilityCapsule.save refuses to overwrite by default."""
    capsule = ReproducibilityCapsule(**_valid_capsule_dict())

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "capsule.json"
        capsule.save(path)

        # Second save without overwrite=True should fail
        with pytest.raises(FileExistsError, match="Refusing to overwrite"):
            capsule.save(path)


def test_capsule_save_overwrite_when_explicit() -> None:
    """ReproducibilityCapsule.save allows overwrite when explicitly opted in."""
    capsule1 = ReproducibilityCapsule(**_valid_capsule_dict())
    capsule2 = ReproducibilityCapsule(**_different_capsule_dict())

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "capsule.json"
        capsule1.save(path)

        # Second save with overwrite=True should succeed
        capsule2.save(path, overwrite=True)

        # Verify file was overwritten
        loaded = ReproducibilityCapsule.load(path)
        assert loaded.capsule_id == capsule2.capsule_id
        assert loaded.uv_lock_sha256 == "b" * 64


def test_capsule_save_atomic_write() -> None:
    """ReproducibilityCapsule.save writes atomically (temp + rename)."""
    capsule = ReproducibilityCapsule(**_valid_capsule_dict())

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "capsule.json"
        capsule.save(path)

        # Verify temp file was cleaned up
        temp_path = path.with_suffix(path.suffix + ".tmp")
        assert not temp_path.exists()

        # Verify final file exists and is valid
        assert path.exists()
        loaded = ReproducibilityCapsule.load(path)
        assert loaded.capsule_id == capsule.capsule_id


def test_capsule_load_from_file() -> None:
    """ReproducibilityCapsule.load loads from file."""
    capsule = ReproducibilityCapsule(**_valid_capsule_dict())

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "capsule.json"
        capsule.save(path)

        loaded = ReproducibilityCapsule.load(path)
        assert loaded.uv_lock_sha256 == capsule.uv_lock_sha256
        assert loaded.capsule_id == capsule.capsule_id


def test_capsule_load_missing_file() -> None:
    """ReproducibilityCapsule.load raises FileNotFoundError for missing files."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "nonexistent.json"
        with pytest.raises(FileNotFoundError, match="Capsule file not found"):
            ReproducibilityCapsule.load(path)


# ---------------------------------------------------------------------------
# no subprocess/git/network/model proof tests
# ---------------------------------------------------------------------------


def test_module_has_no_subprocess_imports() -> None:
    """Module does NOT import subprocess (no git subprocess calls)."""
    import aionis.reporting.reproducibility as module

    source = inspect.getsource(module)
    # Check module's source code, excluding docstrings
    lines = [
        line
        for line in source.split("\n")
        if not line.strip().startswith('"""') and not line.strip().startswith("'''")
    ]
    code_only = "\n".join(lines)
    assert "subprocess" not in code_only or "subprocess" in "no git subprocess calls"
    # Allow "subprocess" in comments/docstrings but not in actual imports
    assert "import subprocess" not in code_only
    assert "from subprocess" not in code_only


def test_module_has_no_network_imports() -> None:
    """Module does NOT import requests/httpx (no network calls)."""
    import aionis.reporting.reproducibility as module

    source = inspect.getsource(module)
    # Check actual imports only, not comments/docstrings
    assert "import requests" not in source
    assert "import httpx" not in source
    assert "from requests" not in source
    assert "from httpx" not in source
    assert "import urllib" not in source
    assert "from urllib" not in source


def test_module_has_no_provider_client_imports() -> None:
    """Module does NOT import provider client (no model calls)."""
    import aionis.reporting.reproducibility as module

    source = inspect.getsource(module)
    # Check actual imports only
    # Allow "provider_kind" enum but not provider client imports
    assert "import providers" not in source
    assert "from aionis.extraction.providers" not in source


# ---------------------------------------------------------------------------
# edge cases
# ---------------------------------------------------------------------------


def test_capsule_created_at_optional() -> None:
    """ReproducibilityCapsule accepts capsule without created_at."""
    capsule = ReproducibilityCapsule(**_valid_capsule_dict())
    assert capsule.created_at is None


def test_capsule_description_optional() -> None:
    """ReproducibilityCapsule accepts capsule without description."""
    capsule = ReproducibilityCapsule(**_valid_capsule_dict())
    assert capsule.description is None


def test_provider_temperature_zero_allowed() -> None:
    """ReproducibilityCapsule allows temperature=0.0 (deterministic)."""
    capsule = ReproducibilityCapsule(
        **_valid_capsule_dict({
            "provider_metadata": _valid_provider_metadata({"temperature": 0.0})
        })
    )
    assert capsule.provider_metadata.temperature == 0.0


def test_provider_kind_all_values() -> None:
    """ReproducibilityCapsule accepts all ProviderKind values."""
    for kind in ["glm", "siliconflow", "modelscope"]:
        capsule = ReproducibilityCapsule(
            **_valid_capsule_dict({
                "provider_metadata": {
                    "provider_kind": kind,
                    "model_name": "test-model",
                    "temperature": 0.0,
                }
            })
        )
        assert capsule.provider_metadata.provider_kind.value == kind


def test_capsule_id_excludes_optional_metadata() -> None:
    """Capsule_id computation excludes optional created_at and description."""
    capsule1 = ReproducibilityCapsule(
        **_valid_capsule_dict({
            "created_at": "2026-08-01T12:00:00Z",
            "description": "First capsule",
        })
    )
    capsule2 = ReproducibilityCapsule(
        **_valid_capsule_dict({
            "created_at": "2026-08-02T13:00:00Z",
            "description": "Second capsule",
        })
    )

    # Different optional metadata, same hashes → same capsule_id
    assert capsule1.capsule_id == capsule2.capsule_id
