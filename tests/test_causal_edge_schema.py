"""E3 Slice 3a — closed-enum causal-edge schema (hermetic).

Pins :mod:`aionis.schema.causal_edge`: the minimal closed-enum LLM edge for
arm_e13 (``ForwardCausalExtraction``) that closes the free-text gap left by
``ERL.CausalLink`` while preserving the I5 anti-leakage contract (structural-
only: ``extra="forbid"`` + ``FORBIDDEN_FIELDS`` rejects ``market_impact`` /
``expected_return`` / ``historical_similarity``). Sector taxonomy is the unified
FF-12 industries (Ken French's canonical 12, including Durbl), and the SIC
reducer pins well-known canonical SIC->sector mappings.
"""
from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from aionis.schema.causal_edge import (
    CAUSAL_SCHEMA_VERSION,
    FORBIDDEN_FIELDS,
    CausalEdge,
    Direction,
    ForwardCausalExtraction,
    HorizonBucket,
    MechanismKeyword,
    SicSector,
    assert_no_forbidden,
    direction_sign,
    sic_to_ff12,
)

# ---------------------------------------------------------------------------
# round-trip
# ---------------------------------------------------------------------------


def _sample_edge(**overrides: object) -> CausalEdge:
    base: dict[str, object] = {
        "sic_sector": "Hlth",
        "direction": "positive",
        "mechanism_keyword": "ownership_change",
        "horizon_bucket": "short",
    }
    base.update(overrides)
    return CausalEdge.model_validate(base)


def _sample_extraction(event_id: str = "13D_ACME_20240115") -> ForwardCausalExtraction:
    return ForwardCausalExtraction.model_validate(
        {
            "event_id": event_id,
            "causal_edges": [
                {
                    "sic_sector": "BusEq",
                    "direction": "negative",
                    "mechanism_keyword": "guidance",
                    "horizon_bucket": "medium",
                }
            ],
        }
    )


def test_round_trip_causal_edge() -> None:
    edge = _sample_edge()
    js = edge.model_dump_json()
    restored = CausalEdge.model_validate_json(js)
    assert restored == edge


def test_round_trip_forward_causal_extraction() -> None:
    ext = _sample_extraction()
    js = ext.model_dump_json()
    restored = ForwardCausalExtraction.model_validate_json(js)
    assert restored == ext
    assert restored.causal_edges[0].sic_sector is SicSector.BUSEQ
    assert restored.causal_edges[0].direction is Direction.NEGATIVE
    assert restored.causal_edges[0].mechanism_keyword is MechanismKeyword.GUIDANCE


def test_forward_causal_extraction_no_impact_or_return_field() -> None:
    """The top-level extraction carries ONLY event_id + causal_edges (I5)."""
    fields = set(ForwardCausalExtraction.model_fields.keys())
    assert fields == {"event_id", "causal_edges"}


# ---------------------------------------------------------------------------
# I5: forbidden fields rejected (parametrized over the 3 leakage vectors)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field", sorted(FORBIDDEN_FIELDS))
def test_reject_forbidden_field_in_causal_edge(field: str) -> None:
    """Pydantic extra=forbid rejects every I5 forbidden field by name."""
    bad: dict[str, object] = {
        "sic_sector": "Hlth",
        "direction": "positive",
        "mechanism_keyword": "other",
        "horizon_bucket": "short",
        field: 0.5,
    }
    with pytest.raises(ValidationError):
        CausalEdge.model_validate(bad)


@pytest.mark.parametrize("field", sorted(FORBIDDEN_FIELDS))
def test_reject_forbidden_field_in_extraction(field: str) -> None:
    bad: dict[str, object] = {
        "event_id": "E1",
        "causal_edges": [],
        field: "lookahead",
    }
    with pytest.raises(ValidationError):
        ForwardCausalExtraction.model_validate(bad)


@pytest.mark.parametrize("field", sorted(FORBIDDEN_FIELDS))
def test_assert_no_forbidden_raises_on_each(field: str) -> None:
    with pytest.raises(ValueError):
        assert_no_forbidden({"event_id": "E1", field: "leak"})


def test_assert_no_forbidden_passes_clean() -> None:
    # does not raise
    assert_no_forbidden({"event_id": "E1", "causal_edges": []})


def test_assert_no_forbidden_raises_if_any_present() -> None:
    with pytest.raises(ValueError):
        assert_no_forbidden(
            {"event_id": "E1", "market_impact": 1.0, "expected_return": 0.2}
        )


def test_forbidden_fields_is_frozenset_of_three() -> None:
    assert FORBIDDEN_FIELDS == frozenset(
        {"market_impact", "expected_return", "historical_similarity"}
    )


# ---------------------------------------------------------------------------
# extra=forbid (unknown field rejected)
# ---------------------------------------------------------------------------


def test_causal_edge_extra_forbid() -> None:
    with pytest.raises(ValidationError):
        CausalEdge.model_validate(
            {
                "sic_sector": "Hlth",
                "direction": "positive",
                "mechanism_keyword": "other",
                "horizon_bucket": "short",
                "rogue_field": True,
            }
        )


def test_forward_causal_extraction_extra_forbid() -> None:
    with pytest.raises(ValidationError):
        ForwardCausalExtraction.model_validate(
            {"event_id": "E1", "causal_edges": [], "rogue_field": True}
        )


# ---------------------------------------------------------------------------
# closed-enum enforcement (out-of-enum raises)
# ---------------------------------------------------------------------------


def test_direction_closed_enum() -> None:
    with pytest.raises(ValidationError):
        CausalEdge.model_validate(
            {
                "sic_sector": "Hlth",
                "direction": "bullish",  # not in enum
                "mechanism_keyword": "other",
                "horizon_bucket": "short",
            }
        )


def test_mechanism_keyword_closed_enum() -> None:
    with pytest.raises(ValidationError):
        CausalEdge.model_validate(
            {
                "sic_sector": "Hlth",
                "direction": "positive",
                "mechanism_keyword": "fraud_investigation",  # not in enum
                "horizon_bucket": "short",
            }
        )


def test_sic_sector_closed_enum() -> None:
    with pytest.raises(ValidationError):
        CausalEdge.model_validate(
            {
                "sic_sector": "FakeSector",  # not in the FF-12 enum
                "direction": "positive",
                "mechanism_keyword": "other",
                "horizon_bucket": "short",
            }
        )


def test_horizon_bucket_closed_enum() -> None:
    with pytest.raises(ValidationError):
        CausalEdge.model_validate(
            {
                "sic_sector": "Hlth",
                "direction": "positive",
                "mechanism_keyword": "other",
                "horizon_bucket": "decade",  # not in enum
            }
        )


# ---------------------------------------------------------------------------
# enums cover the spec
# ---------------------------------------------------------------------------


def test_sic_sector_is_canonical_ff12() -> None:
    """The sector taxonomy is Ken French's canonical 12 industries (incl. Durbl)."""
    labels = {s.value for s in SicSector}
    assert labels == {
        "NoDur",
        "Durbl",
        "Manuf",
        "Enrgy",
        "Chems",
        "BusEq",
        "Telcm",
        "Utils",
        "Shops",
        "Hlth",
        "Money",
        "Other",
    }


def test_direction_enum_values() -> None:
    assert Direction.POSITIVE.value == "positive"
    assert Direction.NEGATIVE.value == "negative"
    assert Direction.NEUTRAL.value == "neutral"


def test_mechanism_keyword_enum_values() -> None:
    assert {m.value for m in MechanismKeyword} == {
        "earnings_signal",
        "ownership_change",
        "guidance",
        "other",
    }


def test_horizon_bucket_mirrors_temporal_class() -> None:
    """horizon_bucket reuses ERL TemporalClass vocabulary (instant/short/medium/long)."""
    assert {h.value for h in HorizonBucket} == {"instant", "short", "medium", "long"}


# ---------------------------------------------------------------------------
# direction_sign mapping (POSITIVE=+1, NEGATIVE=-1, NEUTRAL=NaN)
# ---------------------------------------------------------------------------


def test_direction_sign_mapping() -> None:
    assert direction_sign(Direction.POSITIVE) == 1.0
    assert direction_sign(Direction.NEGATIVE) == -1.0
    assert math.isnan(direction_sign(Direction.NEUTRAL))


# ---------------------------------------------------------------------------
# CAUSAL_SCHEMA_VERSION stable
# ---------------------------------------------------------------------------


def test_causal_schema_version_stable() -> None:
    assert CAUSAL_SCHEMA_VERSION == "e3-causal-v1"


# ---------------------------------------------------------------------------
# sic_to_ff12 reducer — canonical SIC -> FF-12 mappings
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "sic, expected",
    [
        ("2080", SicSector.NODUR),   # Beverages -> NoDur (2000-2399)
        ("2834", SicSector.CHEMS),   # Pharma preparations -> Chems (2830-2839)
        ("3711", SicSector.DURBL),   # Motor vehicles -> Durbl (3710-3711)
        ("1311", SicSector.ENRGY),   # Crude petroleum & natgas -> Enrgy (1200-1399)
        ("4813", SicSector.TELCM),   # Telephone comms -> Telcm (4800-4899)
        ("4911", SicSector.UTILS),   # Electric services -> Utils (4900-4949)
        ("5411", SicSector.SHOPS),   # Grocery stores -> Shops (5000-5999)
        ("8000", SicSector.HLTH),    # Health services -> Hlth (8000-8099)
        ("6022", SicSector.MONEY),   # National commercial banks -> Money (6000-6999)
        ("7372", SicSector.BUSEQ),   # Prepackaged software -> BusEq (7370-7379)
        ("3500", SicSector.MANUF),   # Industrial machinery -> Manuf (3200-3569)
        ("9999", SicSector.OTHER),   # unassigned -> Other
        ("8711", SicSector.OTHER),   # Engineering services -> Other
    ],
)
def test_sic_to_ff12_canonical(sic: str, expected: SicSector) -> None:
    assert sic_to_ff12(sic) is expected


def test_sic_to_ff12_handles_non_numeric_and_garbage() -> None:
    """A non-parseable SIC maps to Other (the residual bucket), never raises."""
    assert sic_to_ff12("") is SicSector.OTHER
    assert sic_to_ff12("N/A") is SicSector.OTHER


def test_sic_to_ff12_takes_leading_digits() -> None:
    """A SIC string with trailing text still resolves on the leading code."""
    assert sic_to_ff12("7372-Prepackaged Software") is SicSector.BUSEQ


def test_empty_causal_edges_list_allowed() -> None:
    """An extraction may carry zero edges (the LLM found no defensible mechanism)."""
    ext = ForwardCausalExtraction(event_id="E1", causal_edges=[])
    assert ext.causal_edges == []
