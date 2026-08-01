"""Offline replay harness for extraction parser stability testing.

This module loads synthetic OpenAI-compatible response fixtures from a directory
and deterministically measures parser behavior: schema parse success/failure,
abstain detection, invalid-output detection, and cache-key stability.

All fixtures MUST be synthetic and clearly labeled. No real API keys, user data,
filing text, or tokens. Fixtures mimic the SHAPE of OpenAI chat-completion
responses (choices[].message.content, etc.) with controlled malformations.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import structlog

from aionis.extraction.llm_client import _parse_and_validate, text_hash
from aionis.schema.erl import ERL

log = structlog.get_logger()


class Verdict(str, Enum):
    """Deterministic parser verdicts for fixture replay."""

    VALID = "valid"
    INVALID_JSON = "invalid_json"
    TRUNCATED = "truncated"
    EXTRA_TEXT = "extra_text"
    UNKNOWN_ENUM = "unknown_enum"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ReplayResult:
    """Per-fixture replay result with H6 determinism guarantees."""

    fixture_name: str
    verdict: Verdict
    raw_response_sha256: str
    parser_version_sha256: str
    erl: ERL | None = None
    error_summary: str | None = None


def _parser_version_sha256() -> str:
    """Derive parser version from the parser module's source bytes."""
    # Hash the _parse_and_validate function's source code for versioning
    import inspect

    source = inspect.getsource(_parse_and_validate)
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _detect_extra_text(content: str) -> bool:
    """Detect if JSON is surrounded by extra text (before or after).

    This checks if there's non-whitespace text before the first { or after the last }.
    """
    stripped = content.strip()
    if not stripped:
        return False

    # Find the first { and last }
    json_start = stripped.find("{")
    json_end = stripped.rfind("}")

    if json_start == -1 or json_end == -1:
        return False  # No JSON structure at all

    # Check if there's non-whitespace text before the first {
    before = stripped[:json_start].strip()
    if before:
        return True

    # Check if there's non-whitespace text after the last }
    after = stripped[json_end + 1:].strip()
    if after:
        return True

    return False


def _detect_truncated(content: str) -> bool:
    """Detect if JSON appears truncated (missing closing braces/brackets)."""
    stripped = content.strip()
    if not stripped:
        return False

    # Count braces
    open_braces = stripped.count("{")
    close_braces = stripped.count("}")
    open_brackets = stripped.count("[")
    close_brackets = stripped.count("]")

    # If more opens than closes, likely truncated
    return open_braces > close_braces or open_brackets > close_brackets


def _detect_unknown_enum_values(erl: ERL) -> list[str]:
    """Detect enum values that don't match known schema values."""
    unknown_fields = []

    from aionis.schema.erl import ActionType, ActorType, ObjectType, TemporalClass

    # Check action enum
    if erl.action.value not in [e.value for e in ActionType]:
        unknown_fields.append(f"action={erl.action.value}")

    # Check actor type enum
    if erl.actor.type.value not in [e.value for e in ActorType]:
        unknown_fields.append(f"actor.type={erl.actor.type.value}")

    # Check object type enum
    if erl.object.type.value not in [e.value for e in ObjectType]:
        unknown_fields.append(f"object.type={erl.object.type.value}")

    # Check temporal enum
    if erl.temporal.value not in [e.value for e in TemporalClass]:
        unknown_fields.append(f"temporal={erl.temporal.value}")

    return unknown_fields


def replay_fixture(
    fixture_path: Path,
    event_id: str = "test_event_001",
    event_type: str = "FOMC",
    source_text: str = "dummy source text for replay",
) -> ReplayResult:
    """Replay a single fixture and return deterministic result.

    Args:
        fixture_path: Path to JSON fixture file (OpenAI-compatible response)
        event_id: Event ID to use for parsing
        event_type: Event type to use for parsing
        source_text: Source text to use for hashing

    Returns:
        ReplayResult with verdict, hashes, and optionally parsed ERL
    """
    from pydantic import ValidationError

    fixture_name = fixture_path.name
    raw_content = fixture_path.read_text()
    raw_sha256 = hashlib.sha256(raw_content.encode("utf-8")).hexdigest()
    parser_sha256 = _parser_version_sha256()

    try:
        fixture = json.loads(raw_content)

        # Extract response content from OpenAI-compatible format
        # Expected format: {"choices": [{"message": {"content": "..."}}]}
        if "choices" in fixture and len(fixture["choices"]) > 0:
            message = fixture["choices"][0].get("message", {})
            llm_content = message.get("content", "")
        else:
            # Fallback: fixture IS the content directly
            llm_content = raw_content

        if not llm_content or not isinstance(llm_content, str):
            return ReplayResult(
                fixture_name=fixture_name,
                verdict=Verdict.INVALID_JSON,
                raw_response_sha256=raw_sha256,
                parser_version_sha256=parser_sha256,
                error_summary="Empty or invalid content format",
            )

        # Try to parse JSON and classify the result
        # First, try parsing the whole content as-is
        try:
            json.loads(llm_content)
            json_parse_error = None
        except json.JSONDecodeError as e:
            json_parse_error = e

        # If JSON parsing failed, classify the error
        if json_parse_error is not None:
            # Check if this looks like extra text around valid JSON
            # by checking if there's text before the first {
            json_start = llm_content.find("{")
            if json_start > 0 and llm_content[:json_start].strip():
                # Text before JSON - this is extra text
                return ReplayResult(
                    fixture_name=fixture_name,
                    verdict=Verdict.EXTRA_TEXT,
                    raw_response_sha256=raw_sha256,
                    parser_version_sha256=parser_sha256,
                    error_summary="Extra text detected before JSON",
                )

            # No text before JSON - classify as truncated or invalid
            if _detect_truncated(llm_content):
                return ReplayResult(
                    fixture_name=fixture_name,
                    verdict=Verdict.TRUNCATED,
                    raw_response_sha256=raw_sha256,
                    parser_version_sha256=parser_sha256,
                    error_summary=f"Truncated JSON detected: {str(json_parse_error)}",
                )
            else:
                return ReplayResult(
                    fixture_name=fixture_name,
                    verdict=Verdict.INVALID_JSON,
                    raw_response_sha256=raw_sha256,
                    parser_version_sha256=parser_sha256,
                    error_summary=f"JSON decode error: {str(json_parse_error)}",
                )

        # JSON parsed successfully - now check for extra text around valid JSON
        if _detect_extra_text(llm_content):
            return ReplayResult(
                fixture_name=fixture_name,
                verdict=Verdict.EXTRA_TEXT,
                raw_response_sha256=raw_sha256,
                parser_version_sha256=parser_sha256,
                error_summary="Extra text detected around valid JSON",
            )

        # No extra text - proceed with schema validation
        try:
            erl = _parse_and_validate(llm_content, event_id, event_type, source_text)
        except ValidationError as e:
            # Schema validation failed - check if it's due to unknown enum values
            error_str = str(e).lower()
            # Pydantic enum validation error mentions the field and valid values
            if "action" in error_str and "enum" in error_str:
                # Extract the invalid value for better reporting
                if "input_value=" in str(e):
                    # Parse the invalid value from the error message
                    import re
                    match = re.search(r"input_value='([^']+)'", str(e))
                    if match:
                        invalid_value = match.group(1)
                        return ReplayResult(
                            fixture_name=fixture_name,
                            verdict=Verdict.UNKNOWN_ENUM,
                            raw_response_sha256=raw_sha256,
                            parser_version_sha256=parser_sha256,
                            error_summary=f"Unknown enum value: action={invalid_value}",
                        )
                return ReplayResult(
                    fixture_name=fixture_name,
                    verdict=Verdict.UNKNOWN_ENUM,
                    raw_response_sha256=raw_sha256,
                    parser_version_sha256=parser_sha256,
                    error_summary=f"Schema validation failed (enum error): {str(e)[:100]}",
                )
            else:
                # Other validation error
                return ReplayResult(
                    fixture_name=fixture_name,
                    verdict=Verdict.UNKNOWN,
                    raw_response_sha256=raw_sha256,
                    parser_version_sha256=parser_sha256,
                    error_summary=f"Schema validation failed: {str(e)[:100]}",
                )

        # Check for unknown enum values in the parsed ERL
        unknown_enums = _detect_unknown_enum_values(erl)
        if unknown_enums:
            return ReplayResult(
                fixture_name=fixture_name,
                verdict=Verdict.UNKNOWN_ENUM,
                raw_response_sha256=raw_sha256,
                parser_version_sha256=parser_sha256,
                error_summary=f"Unknown enum values: {', '.join(unknown_enums)}",
            )

        # Valid parse
        return ReplayResult(
            fixture_name=fixture_name,
            verdict=Verdict.VALID,
            raw_response_sha256=raw_sha256,
            parser_version_sha256=parser_sha256,
            erl=erl,
        )

    except json.JSONDecodeError as e:
        return ReplayResult(
            fixture_name=fixture_name,
            verdict=Verdict.INVALID_JSON,
            raw_response_sha256=raw_sha256,
            parser_version_sha256=parser_sha256,
            error_summary=f"Fixture JSON decode error: {str(e)}",
        )
    except Exception as e:
        return ReplayResult(
            fixture_name=fixture_name,
            verdict=Verdict.UNKNOWN,
            raw_response_sha256=raw_sha256,
            parser_version_sha256=parser_sha256,
            error_summary=f"Unexpected error: {type(e).__name__}: {str(e)}",
        )


def replay_directory(
    fixtures_dir: Path,
    event_id: str = "test_event_001",
    event_type: str = "FOMC",
    source_text: str = "dummy source text for replay",
) -> dict[str, ReplayResult]:
    """Replay all fixtures in a directory.

    Returns results keyed by fixture filename for deterministic ordering.
    """
    fixtures_dir = Path(fixtures_dir)
    if not fixtures_dir.exists():
        log.warning("fixtures_dir_not_found", path=str(fixtures_dir))
        return {}

    results: dict[str, ReplayResult] = {}
    for fixture_path in sorted(fixtures_dir.glob("*.json")):
        result = replay_fixture(fixture_path, event_id, event_type, source_text)
        results[fixture_path.name] = result

    log.info("replay_complete", n=len(results), dir=str(fixtures_dir))
    return results


def cache_key_stability_check(result: ReplayResult, event_id: str, source_text: str) -> bool:
    """Verify cache key stability: same input produces identical cache key.

    For VALID results, verify that the ERL's source_text_hash matches the
    expected hash of the source text.
    """
    if result.verdict != Verdict.VALID or result.erl is None:
        return True  # Not applicable for non-valid results

    expected_hash = text_hash(source_text)
    return result.erl.source_text_hash == expected_hash
