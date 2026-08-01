"""Tests for extraction replay harness (RD-11).

These tests verify that the offline replay system:
1. Produces deterministic verdicts for each fixture type
2. Achieves byte-identical replay (same input → same output)
3. Maintains cache-key stability
4. Does not repair or mutate invalid inputs
5. Handles directory replay in sorted order
6. Uses only synthetic, secret-clean fixtures
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from aionis.extraction.replay import (
    Verdict,
    cache_key_stability_check,
    replay_directory,
    replay_fixture,
)


class TestFixtureVerdicts:
    """Verify each fixture type produces the expected stable verdict."""

    def test_valid_fixture_parses_successfully(self, fixtures_dir: Path) -> None:
        """Valid fixture should parse successfully and return ERL."""
        result = replay_fixture(fixtures_dir / "valid_fomc_hold.json")
        assert result.verdict == Verdict.VALID
        assert result.erl is not None
        assert result.erl.actor.name == "Federal Reserve"
        assert result.erl.action.value == "hold"
        assert result.error_summary is None

    def test_invalid_json_fixture_detected(self, fixtures_dir: Path) -> None:
        """Malformed JSON should be detected without repair."""
        result = replay_fixture(fixtures_dir / "invalid_json_malformed.json")
        assert result.verdict == Verdict.INVALID_JSON
        assert result.erl is None
        assert (
            "JSON decode error" in result.error_summary
            or "invalid" in result.error_summary.lower()
        )

    def test_truncated_fixture_detected(self, fixtures_dir: Path) -> None:
        """Truncated JSON should be detected without repair."""
        result = replay_fixture(fixtures_dir / "truncated_incomplete.json")
        assert result.verdict == Verdict.TRUNCATED
        assert result.erl is None
        assert "Truncated" in result.error_summary

    def test_extra_text_fixture_detected(self, fixtures_dir: Path) -> None:
        """JSON surrounded by extra text should be detected without repair."""
        result = replay_fixture(fixtures_dir / "extra_text_surrounding.json")
        assert result.verdict == Verdict.EXTRA_TEXT
        assert result.erl is None
        assert "Extra text" in result.error_summary

    def test_unknown_enum_fixture_detected(self, fixtures_dir: Path) -> None:
        """Unknown enum values should be detected without repair."""
        result = replay_fixture(fixtures_dir / "unknown_enum_action.json")
        assert result.verdict == Verdict.UNKNOWN_ENUM
        assert result.erl is None
        assert "Unknown enum" in result.error_summary or "action=" in result.error_summary


class TestDeterminism:
    """Verify H6 determinism: same input produces byte-identical output."""

    def test_byte_identical_replay_single_fixture(self, fixtures_dir: Path) -> None:
        """Two runs of the same fixture must produce byte-identical results."""
        fixture_path = fixtures_dir / "valid_fomc_hold.json"

        result1 = replay_fixture(fixture_path)
        result2 = replay_fixture(fixture_path)

        # All fields must match exactly
        assert result1.fixture_name == result2.fixture_name
        assert result1.verdict == result2.verdict
        assert result1.raw_response_sha256 == result2.raw_response_sha256
        assert result1.parser_version_sha256 == result2.parser_version_sha256

        # For valid results, ERL must be byte-identical
        if result1.verdict == Verdict.VALID:
            assert result1.erl is not None and result2.erl is not None
            assert result1.erl.model_dump_json() == result2.erl.model_dump_json()

    def test_byte_identical_directory_replay(self, fixtures_dir: Path) -> None:
        """Two runs of the same directory must produce byte-identical results."""
        results1 = replay_directory(fixtures_dir)
        results2 = replay_directory(fixtures_dir)

        # Same fixtures in both results (sorted order guaranteed)
        assert set(results1.keys()) == set(results2.keys())
        assert list(results1.keys()) == list(results2.keys())  # Check order

        # Each result must be byte-identical
        for fixture_name in results1:
            r1 = results1[fixture_name]
            r2 = results2[fixture_name]
            assert r1.verdict == r2.verdict
            assert r1.raw_response_sha256 == r2.raw_response_sha256
            assert r1.parser_version_sha256 == r2.parser_version_sha256

            if r1.verdict == Verdict.VALID:
                assert r1.erl is not None and r2.erl is not None
                assert r1.erl.model_dump_json() == r2.erl.model_dump_json()


class TestCacheKeyStability:
    """Verify cache-key stability for valid results."""

    def test_cache_key_stability_valid_fixture(self, fixtures_dir: Path) -> None:
        """Valid fixtures should have stable cache keys."""
        result = replay_fixture(
            fixtures_dir / "valid_fomc_hold.json",
            event_id="test_event_001",
            source_text="dummy source text for replay",
        )

        assert result.verdict == Verdict.VALID
        assert cache_key_stability_check(
            result,
            event_id="test_event_001",
            source_text="dummy source text for replay",
        )

    def test_cache_key_stability_non_valid_always_passes(self, fixtures_dir: Path) -> None:
        """Non-valid fixtures should always pass cache-key check (not applicable)."""
        for fixture_name in [
            "invalid_json_malformed.json",
            "truncated_incomplete.json",
            "extra_text_surrounding.json",
            "unknown_enum_action.json",
        ]:
            result = replay_fixture(fixtures_dir / fixture_name)
            # Should return True for non-valid results
            assert cache_key_stability_check(result, "test_event", "source text")


class TestInputImmutability:
    """Verify that fixtures are never mutated or repaired."""

    def test_invalid_fixtures_not_mutated(self, fixtures_dir: Path) -> None:
        """Invalid/truncated fixtures should return error verdicts without modification."""
        original_content = (fixtures_dir / "invalid_json_malformed.json").read_text()

        result = replay_fixture(fixtures_dir / "invalid_json_malformed.json")

        # Verify fixture unchanged
        assert (fixtures_dir / "invalid_json_malformed.json").read_text() == original_content

        # Verify error verdict (not a repair attempt)
        assert result.verdict in {Verdict.INVALID_JSON, Verdict.TRUNCATED, Verdict.EXTRA_TEXT}
        assert result.erl is None

    def test_all_fixture_verdicts_distinct(self, fixtures_dir: Path) -> None:
        """Each fixture type should yield a distinct verdict."""
        fixtures_to_verdicts = {
            "valid_fomc_hold.json": Verdict.VALID,
            "invalid_json_malformed.json": Verdict.INVALID_JSON,
            "truncated_incomplete.json": Verdict.TRUNCATED,
            "extra_text_surrounding.json": Verdict.EXTRA_TEXT,
            "unknown_enum_action.json": Verdict.UNKNOWN_ENUM,
        }

        for fixture_name, expected_verdict in fixtures_to_verdicts.items():
            result = replay_fixture(fixtures_dir / fixture_name)
            assert (
                result.verdict == expected_verdict
            ), f"{fixture_name}: expected {expected_verdict}, got {result.verdict}"


class TestSha256Recording:
    """Verify that raw-response and parser-version SHA256 are recorded."""

    def test_raw_response_sha256_recorded(self, fixtures_dir: Path) -> None:
        """Each result should record the SHA256 of the raw fixture."""
        fixture_path = fixtures_dir / "valid_fomc_hold.json"
        raw_content = fixture_path.read_text()
        expected_sha256 = hashlib.sha256(raw_content.encode("utf-8")).hexdigest()

        result = replay_fixture(fixture_path)
        assert result.raw_response_sha256 == expected_sha256

    def test_parser_version_sha256_recorded(self, fixtures_dir: Path) -> None:
        """Each result should record the SHA256 of the parser version."""
        result1 = replay_fixture(fixtures_dir / "valid_fomc_hold.json")
        result2 = replay_fixture(fixtures_dir / "invalid_json_malformed.json")

        # Parser version must be the same across all results in a run
        assert result1.parser_version_sha256 == result2.parser_version_sha256

        # Must be a valid SHA256 hex string
        assert len(result1.parser_version_sha256) == 64
        assert all(c in "0123456789abcdef" for c in result1.parser_version_sha256)


class TestDirectoryReplay:
    """Test directory-level replay functionality."""

    def test_directory_replay_sorted_and_deterministic(self, fixtures_dir: Path) -> None:
        """Directory replay should process fixtures in sorted order."""
        results = replay_directory(fixtures_dir)

        # Check that keys are sorted
        fixture_names = list(results.keys())
        assert fixture_names == sorted(fixture_names)

        # Check that all fixtures were processed
        assert len(results) == 5  # We have 5 fixtures

    def test_directory_replay_handles_missing_directory(self, tmp_path: Path) -> None:
        """Missing directory should return empty dict (not error)."""
        results = replay_directory(tmp_path / "nonexistent_dir")
        assert results == {}


class TestSecretCleanFixtures:
    """Verify fixtures contain no real secrets or sensitive data."""

    def test_fixtures_contain_no_api_keys(self, fixtures_dir: Path) -> None:
        """Fixtures should not contain real API keys or access tokens."""
        forbidden_patterns = ["sk-", "api_key", "Bearer ", "access_token", "secret"]

        for fixture_path in fixtures_dir.glob("*.json"):
            content = fixture_path.read_text()
            for pattern in forbidden_patterns:
                assert (
                    pattern.lower() not in content.lower()
                ), f"{fixture_path}: contains forbidden pattern '{pattern}'"

    def test_fixtures_marked_synthetic(self, fixtures_dir: Path) -> None:
        """All fixtures should use obviously synthetic placeholder content."""
        synthetic_markers = ["EXAMPLE CORP", "dummy", "test_event", "placeholder"]

        for fixture_path in fixtures_dir.glob("*.json"):
            content = fixture_path.read_text()
            # At least one synthetic marker should be present
            assert any(
                marker in content for marker in synthetic_markers
            ), f"{fixture_path}: missing synthetic marker"

    def test_fixtures_labeled_readme_exists(self, fixtures_dir: Path) -> None:
        """Fixtures directory should have a README explaining synthetic nature."""
        readme_path = fixtures_dir / "README.md"
        assert readme_path.exists()
        content = readme_path.read_text()
        assert "synthetic" in content.lower() or "test fixture" in content.lower()


class TestVerdictDistinctness:
    """Verify that all verdict types produce stable, distinct outcomes."""

    def test_all_verdicts_represented(self, fixtures_dir: Path) -> None:
        """All required verdict types should be represented by fixtures."""
        results = replay_directory(fixtures_dir)
        verdicts = {r.verdict for r in results.values()}

        # Should have at least the 5 required verdicts
        required_verdicts = {
            Verdict.VALID,
            Verdict.INVALID_JSON,
            Verdict.TRUNCATED,
            Verdict.EXTRA_TEXT,
            Verdict.UNKNOWN_ENUM,
        }
        assert required_verdicts <= verdicts, f"Missing verdicts: {required_verdicts - verdicts}"


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the path to the LLM replay fixtures directory."""
    return Path(__file__).parent / "fixtures" / "llm_replay"
