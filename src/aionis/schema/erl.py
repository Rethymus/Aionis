"""ERL — Event Representation Language (structural-only Pydantic contract).

DESIGN DECISION (see README / plan): the LLM-extracted ERL carries ONLY
structural / semantic fields. ``market_impact`` and ``historical_similarity`` are
deliberately absent — an LLM-filled impact field is an architectural leakage
vector (the model has memorized macro-event outcomes), and market impact is the
downstream world model's *prediction target*, not an extraction product.

The schema is OpenAI strict-structured-output compatible: every field is a
primitive, an enum, or a list of nested models (no free-form dict / Union), so
``client.chat.completions.parse(..., response_format=ERL)`` enforces it.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ActorType(str, Enum):
    GOVERNMENT = "government"
    CENTRAL_BANK = "central_bank"
    COMPANY = "company"
    ORGANIZATION = "organization"
    INDIVIDUAL = "individual"
    COLLECTIVE = "collective"


class ActionType(str, Enum):
    INCREASE = "increase"
    DECREASE = "decrease"
    RESTRICT = "restrict"
    ENCOURAGE = "encourage"
    DELAY = "delay"
    REMOVE = "remove"
    REPLACE = "replace"
    CREATE = "create"
    DESTROY = "destroy"
    ANNOUNCE = "announce"  # scheduled releases: FOMC statement, CPI/NFP print
    HOLD = "hold"  # e.g. unchanged policy rate


class ObjectType(str, Enum):
    MACRO = "macro"
    INDUSTRY = "industry"
    ENTITY = "entity"


class TemporalClass(str, Enum):
    """A-priori expected duration of the event's influence (never realized outcome)."""

    INSTANT = "instant"
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"


class Actor(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    type: ActorType
    influence_scope: str = "unknown"


class ERLObject(BaseModel):
    """The thing acted upon."""

    model_config = ConfigDict(extra="forbid")
    name: str
    type: ObjectType
    sector: str = "unknown"


class CausalLink(BaseModel):
    """One hypothesized cause->effect edge in the event's mechanism (no outcomes)."""

    model_config = ConfigDict(extra="forbid")
    cause: str
    effect: str


class ERL(BaseModel):
    """A structured event representation. No market-impact / outcome fields."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    event_type: str
    actor: Actor
    action: ActionType
    action_detail: str
    object: ERLObject
    summary: str = Field(
        description="One-sentence structural summary. "
        "Must NOT mention any market price move or outcome."
    )
    temporal: TemporalClass
    causal_structure: list[CausalLink]
    uncertainty: float = Field(ge=0.0, le=1.0, description="A-priori extraction confidence, 0..1.")
    source_text_hash: str

    def canonical_text(self) -> str:
        """Stable outcome-free serialization for embedding / similarity."""
        causal = "; ".join(f"{c.cause} -> {c.effect}" for c in self.causal_structure)
        return (
            f"{self.summary} "
            f"actor={self.actor.name}({self.actor.type.value}) "
            f"action={self.action.value} ({self.action_detail}) "
            f"object={self.object.name}({self.object.sector}) "
            f"temporal={self.temporal.value} uncertainty={self.uncertainty:.2f} "
            f"causal: {causal}"
        )
