"""Hermetic schema tests for RD-04 gold records."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from aionis.schema.causal_edge import (
    Direction,
    HorizonBucket,
    MechanismKeyword,
    SicSector,
)
from aionis.schema.gold_annotation import GoldCausalAnnotationV1


def _edge() -> dict:
    return {
        "sic_sector": "Money",
        "direction": "negative",
        "mechanism_keyword": "ownership_change",
        "horizon_bucket": "short",
    }


def _valid(edge: bool = True) -> dict:
    record = {
        "schema_version": "e3-causal-gold-v1",
        "event_id": "13D_0001213900-24-012345",
        "event_type": "13d",
        "filed_ts": "2024-01-15T10:30:00Z",
        "source_text_sha256": "ab" * 32,
        "source_span_start": 10,
        "source_span_end": 120,
        "causal_edges": [_edge()] if edge else [],
        "abstention_reason": None if edge else "insufficient_text",
        "annotator_ids": ["annotator-a", "annotator-b"],
        "adjudicated": True,
    }
    return record


def test_valid_one_edge_reuses_causal_enums() -> None:
    gold = GoldCausalAnnotationV1.model_validate(_valid())
    assert gold.schema_version == "e3-causal-gold-v1"
    assert gold.event_type == "13d"
    assert gold.causal_edges[0].sic_sector == SicSector.MONEY
    assert gold.causal_edges[0].direction == Direction.NEGATIVE
    assert gold.causal_edges[0].mechanism_keyword == MechanismKeyword.OWNERSHIP_CHANGE
    assert gold.causal_edges[0].horizon_bucket == HorizonBucket.SHORT
    assert gold.abstention_reason is None
    assert gold.adjudicated is True


def test_valid_abstention_requires_reason_and_can_be_pending() -> None:
    pending = GoldCausalAnnotationV1.model_validate(_valid(edge=False))
    assert pending.causal_edges == []
    assert pending.abstention_reason == "insufficient_text"
    assert pending.adjudicated is True

    record = _valid(edge=False)
    record["abstention_reason"] = "adjudication_pending"
    record["adjudicated"] = False
    pending = GoldCausalAnnotationV1.model_validate(record)
    assert pending.abstention_reason == "adjudication_pending"
    assert pending.adjudicated is False


def test_schema_is_strict_and_contains_no_errored_fields() -> None:
    schema = GoldCausalAnnotationV1.model_json_schema()
    assert schema["additionalProperties"] is False
    props = set(schema["properties"])
    assert props == {
        "schema_version",
        "event_id",
        "event_type",
        "filed_ts",
        "source_text_sha256",
        "source_span_start",
        "source_span_end",
        "causal_edges",
        "abstention_reason",
        "annotator_ids",
        "adjudicated",
    }
    assert "market_impact" not in props
    assert "expected_return" not in props
    assert "causal_structure" not in props


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("event_type", "8-K"),
        ("source_text_sha256", "not-a-sha256"),
        ("source_text_sha256", "ab" * 31 + "zz"),
        ("source_span_start", -1),
        ("source_span_end", -1),
        ("annotator_ids", []),
        ("annotator_ids", ["a", "a"]),
        ("annotator_ids", ["b", "a"]),
        ("abstention_reason", "model_uncertainty"),
    ],
)
def test_illegal_field_values_are_rejected(field: str, bad_value: object) -> None:
    record = _valid()
    record[field] = bad_value
    with pytest.raises(ValidationError):
        GoldCausalAnnotationV1.model_validate(record)


def test_zero_length_or_reversed_span_is_rejected() -> None:
    for start, end in [(10, 10), (120, 10)]:
        record = _valid()
        record["source_span_start"] = start
        record["source_span_end"] = end
        with pytest.raises(ValidationError):
            GoldCausalAnnotationV1.model_validate(record)


def test_more_than_one_edge_is_rejected() -> None:
    record = _valid()
    record["causal_edges"] = [_edge(), _edge()]
    with pytest.raises(ValidationError):
        GoldCausalAnnotationV1.model_validate(record)


def test_edge_and_abstention_reason_are_mutually_exclusive() -> None:
    record = _valid()
    record["abstention_reason"] = "no_defensible_edge"
    with pytest.raises(ValidationError):
        GoldCausalAnnotationV1.model_validate(record)

    record = _valid(edge=False)
    record["abstention_reason"] = None
    with pytest.raises(ValidationError):
        GoldCausalAnnotationV1.model_validate(record)


@pytest.mark.parametrize(
    ("reason", "adjudicated"),
    [
        ("adjudication_pending", True),
        ("no_defensible_edge", False),
        ("insufficient_text", False),
        ("not_applicable", False),
    ],
)
def test_adjudication_flag_must_match_reason(reason: str, adjudicated: bool) -> None:
    record = _valid(edge=False)
    record["abstention_reason"] = reason
    record["adjudicated"] = adjudicated
    with pytest.raises(ValidationError):
        GoldCausalAnnotationV1.model_validate(record)


def test_extra_forbidden_fields_are_rejected() -> None:
    for forbidden in ("market_impact", "expected_return", "model_prediction"):
        record = _valid()
        record[forbidden] = "anything"
        with pytest.raises(ValidationError):
            GoldCausalAnnotationV1.model_validate(record)


def test_pending_records_are_marked_not_adjudicated() -> None:
    record = _valid(edge=False)
    record["abstention_reason"] = "adjudication_pending"
    record["adjudicated"] = False
    gold = GoldCausalAnnotationV1.model_validate(record)
    assert gold.adjudicated is False


def test_round_trip_preserves_filed_ts_and_edges() -> None:
    original = GoldCausalAnnotationV1.model_validate(_valid())
    restored = GoldCausalAnnotationV1.model_validate_json(original.model_dump_json())
    assert restored == original
    assert restored.filed_ts == datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
