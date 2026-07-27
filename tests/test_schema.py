"""ERL schema + extraction: strict-schema compatibility, round-trip, idempotent cache."""

from __future__ import annotations

from pathlib import Path

import pytest

from aionis.extraction.extract import extract_erls, load_erl_cache
from aionis.extraction.llm_client import MockLLMClient, text_hash
from aionis.features.alignment import nyse_sessions
from aionis.schema.erl import ERL, ActionType
from aionis.synthetic import make_synthetic_event_text, make_synthetic_events

PRICE_WORDS = ("rose", "fell", "rallied", "plunged", "surged", "dropped", "gained", "declined")


def _sample_erl(event_id: str = "FOMC_20230322") -> ERL:
    return ERL.model_validate(
        {
            "event_id": event_id,
            "event_type": "FOMC",
            "actor": {
                "name": "Federal Reserve",
                "type": "central_bank",
                "influence_scope": "global",
            },
            "action": "increase",
            "action_detail": "raised target range",
            "object": {"name": "policy interest rate", "type": "macro", "sector": "macro"},
            "summary": "The Committee raised the target range; no market outcome described.",
            "temporal": "medium",
            "causal_structure": [{"cause": "policy rate", "effect": "borrowing cost"}],
            "uncertainty": 0.3,
            "source_text_hash": "deadbeefdeadbeef",
        }
    )


def test_schema_is_strict_no_additional_properties() -> None:
    """OpenAI strict mode requires additionalProperties:false on every object."""
    schema = ERL.model_json_schema()
    assert schema.get("additionalProperties") is False
    for name, node in schema.get("$defs", {}).items():
        if node.get("type") == "object":
            assert node.get("additionalProperties") is False, f"{name} allows extra props"


def test_schema_has_no_market_impact_field() -> None:
    schema = ERL.model_json_schema()
    props = set(schema["properties"])
    assert "market_impact" not in props
    assert "historical_similarity" not in props
    # structural fields are present
    assert {"actor", "action", "object", "temporal", "causal_structure", "uncertainty"} <= props


def test_erl_round_trip() -> None:
    erl = _sample_erl()
    js = erl.model_dump_json()
    again = ERL.model_validate_json(js)
    assert again.event_id == erl.event_id
    assert again.action == ActionType.INCREASE
    assert again.uncertainty == pytest.approx(0.3)
    assert again.canonical_text().startswith("The Committee raised")


def test_mock_client_produces_valid_outcome_free_erl() -> None:
    client = MockLLMClient()
    text = "The FOMC release on 2023-03-22: the committee voted to raise its policy stance."
    erl = client.extract(text, event_id="FOMC_20230322", event_type="FOMC")
    assert isinstance(erl, ERL)
    assert erl.event_id == "FOMC_20230322"
    assert erl.actor.type.value == "central_bank"
    assert erl.action == ActionType.INCREASE
    assert erl.source_text_hash == text_hash(text)
    canon = erl.canonical_text().lower()
    assert not any(w in canon for w in PRICE_WORDS), "canonical text leaked an outcome word"


def test_extract_is_idempotent_and_cached(tmp_path: Path) -> None:
    sessions = nyse_sessions("2022-01-03", "2023-06-30")
    events = make_synthetic_events(sessions, n=12, seed=4)
    text_df = make_synthetic_event_text(events, seed=9)

    calls = {"n": 0}

    class Counting(MockLLMClient):
        def extract(self, text, event_id, event_type):
            calls["n"] += 1
            return super().extract(text, event_id, event_type)

    cache = tmp_path / "erl"
    erls1 = extract_erls(events, text_df, Counting(), cache)
    assert calls["n"] == len(erls1) == len(events)
    assert len(list(cache.glob("*.json"))) == len(events)

    # Second pass must be fully cache-served (no new extractions).
    calls["n"] = 0
    erls2 = extract_erls(events, text_df, Counting(), cache)
    assert calls["n"] == 0
    assert set(erls2) == set(erls1)

    # load_erl_cache recovers the same set.
    cached = load_erl_cache(cache)
    assert set(cached) == set(erls1)
