"""Causal-edge schema — the minimal closed-enum LLM edge for arm_e13 (Slice 3a).

DESIGN (ADR-009): the E3 event channel uses a *minimal closed-enum LLM edge* to
sign the 13D / 8-K self-shock and tag its mechanism, while the macro channel is
frozen sign-only β (zero-LLM) — see :mod:`aionis.features.frozen_beta`. This
closes the free-text gap left by :class:`aionis.schema.erl.CausalLink` (which
carries free-text ``cause`` / ``effect``) WITHOUT reopening the I5 leakage
surface: the edge is a closed enum over (sector, direction, mechanism,
horizon), never an LLM-filled impact / return / similarity field.

I5 (structural-only) is enforced two ways:
  * ``model_config = ConfigDict(extra="forbid")`` on every model — a stray
    ``market_impact`` / ``expected_return`` / ``historical_similarity`` key
    raises at parse time; AND
  * :func:`assert_no_forbidden` — a belt-and-suspenders pre-parse guard so a
    caller can reject a forbidden field BEFORE handing the dict to the LLM
    client / pydantic.

Sector taxonomy = the unified **FF-12** industries (Ken French's canonical 12
industry portfolios, *including* ``Durbl`` / Consumer Durables). The SIC->FF-12
reducer (:func:`sic_to_ff12`) hardcodes Ken French's published SIC ranges; it is
a frozen lookup table (no estimation DOF), so it adds no leakage and no
rerun-to-significance lever.

This module does NOT modify :mod:`aionis.schema.erl` — it is a net-new contract
that rides the ERL extraction cache (:mod:`aionis.extraction.extract`) at the
caller layer (Slice 3b).
"""

from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# frozen version + I5 forbidden fields
# ---------------------------------------------------------------------------

CAUSAL_SCHEMA_VERSION = "e3-causal-v1"
"""Immutable version stamp for the causal-edge contract (frozen for arm_e13)."""

FORBIDDEN_FIELDS = frozenset(
    {
        "market_impact",
        "expected_return",
        "historical_similarity",
    }
)
"""The three I5 leakage vectors an LLM must NEVER fill on a causal edge.

Mirrors the ERL architectural rule (:mod:`aionis.schema.erl`): an LLM-filled
impact/return/similarity field is a leakage vector (the model has memorized
macro-event outcomes), so the causal edge rejects them structurally.
"""


def assert_no_forbidden(raw: dict) -> None:
    """Raise ``ValueError`` if any I5 forbidden field is present in ``raw``.

    Belt-and-suspenders pre-parse guard: call this on the raw LLM JSON BEFORE
    handing it to :class:`ForwardCausalExtraction`, so a forbidden field is
    rejected even if the surrounding parse path is permissive.
    """
    leaked = FORBIDDEN_FIELDS.intersection(raw.keys())
    if leaked:
        raise ValueError(
            f"I5 leakage: causal edge must not carry outcome fields {sorted(leaked)} "
            f"(forbidden: {sorted(FORBIDDEN_FIELDS)})"
        )


# ---------------------------------------------------------------------------
# enums — all closed (no free text on the edge)
# ---------------------------------------------------------------------------


class SicSector(str, Enum):
    """The unified sector taxonomy = Ken French's canonical 12 industry portfolios.

    Source: Kenneth R. French data library, "12 Industry Portfolios" /
    ``Siccodes12``. The canonical 12 include ``Durbl`` (Consumer Durables), which
    is distinct from ``Manuf`` (Manufacturing) and ``Shops`` (Wholesale/Retail).
    """

    NODUR = "NoDur"   # Consumer Nondurables
    DURBL = "Durbl"   # Consumer Durables
    MANUF = "Manuf"   # Manufacturing
    ENRGY = "Enrgy"   # Energy (oil/gas/coal extraction + products)
    CHEMS = "Chems"   # Chemicals (SIC 2830-2839 — pharma preparations)
    BUSEQ = "BusEq"   # Business Equipment (computers / software / electronics)
    TELCM = "Telcm"   # Telecommunications
    UTILS = "Utils"   # Utilities
    SHOPS = "Shops"   # Wholesale / Retail
    HLTH = "Hlth"     # Healthcare / Medical Equipment / Drugs (services)
    MONEY = "Money"   # Finance / Banking / Insurance / Real Estate
    OTHER = "Other"   # residual


class Direction(str, Enum):
    """The sign the LLM assigns to the event's self-shock."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"   # signs to NaN (no directional view -> no signal)


class MechanismKeyword(str, Enum):
    """Closed enum of event mechanisms (low-N, event-structural, learnable)."""

    EARNINGS_SIGNAL = "earnings_signal"
    OWNERSHIP_CHANGE = "ownership_change"
    GUIDANCE = "guidance"
    OTHER = "other"


class HorizonBucket(str, Enum):
    """A-priori expected horizon of the edge's influence (mirrors ERL TemporalClass).

    Values deliberately match :class:`aionis.schema.erl.TemporalClass`
    (instant/short/medium/long) so the LLM prompt and the ERL vocabulary stay
    unified; this is a mirror, not a reuse, so the causal-edge contract is
    self-contained (the I5 ``extra=forbid`` boundary is on THIS model).
    """

    INSTANT = "instant"
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"


def direction_sign(d: Direction) -> float:
    """Map a :class:`Direction` to its numeric sign (+1 / -1 / NaN).

    ``NEUTRAL`` -> NaN so that ``self_shock * direction_sign`` vanishes (NaN) for
    an event with no directional view — the signed self-shock carries signal ONLY
    when the LLM commits to a direction.
    """
    if d is Direction.POSITIVE:
        return 1.0
    if d is Direction.NEGATIVE:
        return -1.0
    return float("nan")


# ---------------------------------------------------------------------------
# frozen SIC -> FF-12 concordance (Ken French Siccodes12, first-match)
# ---------------------------------------------------------------------------

# The canonical Ken French 12-industry SIC ranges (mba.tuck.dartmouth.edu /
# pages/faculty/ken.french, "12 Industry Portfolios" -> Siccodes12). These are
# mutually exclusive by construction, so first-match is unambiguous. This is a
# FROZEN lookup table — no estimation DOF, no rerun-to-significance surface.
_SIC_FF12_RANGES: list[tuple[SicSector, list[tuple[int, int]]]] = [
    (SicSector.NODUR, [(100, 999), (2000, 2399), (2700, 2749), (2770, 2799),
                       (3100, 3199), (3940, 3989)]),
    (SicSector.DURBL, [(2500, 2519), (3630, 3659), (3710, 3711), (3714, 3714),
                       (3716, 3716), (3750, 3751), (3792, 3792), (3900, 3939),
                       (3990, 3999)]),
    (SicSector.MANUF, [(2520, 2589), (2600, 2699), (2750, 2769), (2800, 2829),
                       (2840, 2899), (3000, 3099), (3200, 3569), (3580, 3629),
                       (3700, 3709), (3712, 3713), (3754, 3791), (3793, 3799),
                       (3830, 3839), (3860, 3899)]),
    (SicSector.ENRGY, [(1200, 1399), (2900, 2999)]),
    (SicSector.CHEMS, [(2830, 2839)]),
    (SicSector.BUSEQ, [(3570, 3579), (3660, 3692), (3694, 3699), (3810, 3829),
                       (7370, 7379)]),
    (SicSector.TELCM, [(4800, 4899)]),
    (SicSector.UTILS, [(4900, 4949)]),
    (SicSector.SHOPS, [(5000, 5999), (7200, 7299), (7600, 7699)]),
    (SicSector.HLTH, [(3693, 3693), (3840, 3859), (8000, 8099)]),
    (SicSector.MONEY, [(6000, 6999)]),
    # Other is the residual — handled in sic_to_ff12, not listed here.
]


def sic_to_ff12(sic_code: str) -> SicSector:
    """Reduce a raw SIC code to its FF-12 :class:`SicSector`.

    Takes the leading integer run of ``sic_code`` (so ``"7372-Prepackaged
    Software"`` -> 7372 -> ``BusEq``) and finds the first FF-12 range containing
    it. A non-numeric / empty / unmatched code maps to :attr:`SicSector.OTHER`
    (the residual bucket) — it never raises, so the reducer is total.

    Source: Ken French's published ``Siccodes12`` (frozen; no estimation DOF).
    """
    m = re.match(r"\s*(\d+)", str(sic_code))
    if not m:
        return SicSector.OTHER
    code = int(m.group(1))
    for sector, ranges in _SIC_FF12_RANGES:
        for lo, hi in ranges:
            if lo <= code <= hi:
                return sector
    return SicSector.OTHER


# ---------------------------------------------------------------------------
# the closed-enum causal edge + its extraction wrapper
# ---------------------------------------------------------------------------


class CausalEdge(BaseModel):
    """One closed-enum causal edge for a forward event (13D / 8-K).

    Every field is a closed enum; ``extra="forbid"`` rejects any other field
    (notably the I5 forbidden trio — see :data:`FORBIDDEN_FIELDS`). There is NO
    impact / return / similarity / magnitude field: this is a structural sign +
    mechanism tag, not an outcome.
    """

    model_config = ConfigDict(extra="forbid")

    sic_sector: SicSector
    direction: Direction
    mechanism_keyword: MechanismKeyword
    horizon_bucket: HorizonBucket


class ForwardCausalExtraction(BaseModel):
    """The LLM extraction product for one forward event (Slice 3 event channel).

    Carries ONLY ``event_id`` + ``causal_edges`` — never an impact / return /
    similarity field (I5). The edge list may be empty (the LLM found no
    defensible mechanism); a non-empty list drives both the direction-sign on the
    self-shock and the mechanism-keyword one-hot in
    :mod:`aionis.features.causal_broadcast`.
    """

    model_config = ConfigDict(extra="forbid")

    event_id: str
    causal_edges: list[CausalEdge]


__all__ = [
    "CAUSAL_SCHEMA_VERSION",
    "FORBIDDEN_FIELDS",
    "assert_no_forbidden",
    "SicSector",
    "Direction",
    "MechanismKeyword",
    "HorizonBucket",
    "direction_sign",
    "sic_to_ff12",
    "CausalEdge",
    "ForwardCausalExtraction",
]
