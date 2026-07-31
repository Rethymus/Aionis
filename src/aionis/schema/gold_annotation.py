"""Adjudicated gold records for E3 causal-edge extraction.

The gold schema is deliberately separate from ERL: a gold record must be a
human-authored answer to a closed-enum extraction question, not a model output.
It reuses :class:`aionis.schema.causal_edge.CausalEdge` directly so the frozen
sector/direction/mechanism/horizon enums cannot drift between the live LLM
contract and the evaluation target.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from aionis.schema.causal_edge import CausalEdge

GOLD_SCHEMA_VERSION = "e3-causal-gold-v1"

AbstentionReason = Literal[
    "no_defensible_edge",
    "insufficient_text",
    "not_applicable",
    "adjudication_pending",
]


class GoldCausalAnnotationV1(BaseModel):
    """One adjudicated or pending human gold record for an event.

    ``causal_edges`` holds zero or one frozen :class:`CausalEdge`. A non-empty
    edge is mutually exclusive with ``abstention_reason``. Pending records are
    represented with ``abstention_reason="adjudication_pending"`` and
    ``adjudicated=false``; evaluators must not treat them as gold.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["e3-causal-gold-v1"] = "e3-causal-gold-v1"
    event_id: str
    event_type: Literal["13d", "8k_2_02"]
    filed_ts: datetime
    source_text_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    source_span_start: int = Field(ge=0)
    source_span_end: int = Field(ge=0)
    causal_edges: list[CausalEdge] = Field(default_factory=list, max_length=1)
    abstention_reason: AbstentionReason | None = None
    annotator_ids: list[str] = Field(min_length=1)
    adjudicated: bool

    @field_validator("annotator_ids")
    @classmethod
    def _annotator_ids_are_sorted_unique(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("annotator_ids must not contain duplicates")
        if value != sorted(value):
            raise ValueError("annotator_ids must be sorted")
        return value

    @model_validator(mode="after")
    def _source_span_has_positive_length(self) -> GoldCausalAnnotationV1:
        if self.source_span_end <= self.source_span_start:
            raise ValueError("source_span_end must be greater than source_span_start")
        return self

    @model_validator(mode="after")
    def _edge_and_abstention_are_mutually_exclusive(self) -> GoldCausalAnnotationV1:
        has_edge = len(self.causal_edges) == 1
        if has_edge and self.abstention_reason is not None:
            raise ValueError("abstention_reason must be null when a causal edge is present")
        if not has_edge and self.abstention_reason is None:
            raise ValueError("abstention_reason is required when causal_edges is empty")
        return self

    @model_validator(mode="after")
    def _adjudication_is_consistent(self) -> GoldCausalAnnotationV1:
        if self.abstention_reason == "adjudication_pending":
            if self.adjudicated:
                raise ValueError("adjudication_pending requires adjudicated=false")
            return self
        if not self.adjudicated:
            raise ValueError("non-pending records must set adjudicated=true")
        return self


__all__ = [
    "GOLD_SCHEMA_VERSION",
    "AbstentionReason",
    "GoldCausalAnnotationV1",
]
