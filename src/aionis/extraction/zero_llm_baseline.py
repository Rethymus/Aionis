"""Zero-LLM baseline extractor — mechanical rule application from frozen table.

This module implements a conservative, abstain-by-default baseline that applies
keyword/regex rules WITHOUT any LLM judgment. It loads the frozen rule table at
runtime, computes its sha256 for provenance, and mechanically applies rules
per the table's specification.

Abstain cases:
- No rules match for the event_type
- Pattern matches but negation_window contains opposing keywords
- Multiple rules with same precedence match (conflict)
- An abstain-only rule matches (e.g., FOMC forward-guidance language)

H6 determinism: same input → identical output (no randomness, seeded execution).
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import structlog
from pydantic import BaseModel

from aionis.schema.erl import (
    ERL,
    ActionType,
    Actor,
    ActorType,
    CausalLink,
    ERLObject,
    ObjectType,
    TemporalClass,
)

log = structlog.get_logger()


class RuleEdge(BaseModel):
    """The ERL edge tuple a rule produces (all lowercase enum VALUES)."""

    action: str
    actor_type: str
    object_type: str
    temporal_class: str


class Rule(BaseModel):
    """One rule from the frozen rule table."""

    rule_id: str
    event_type: str
    edge: RuleEdge | None
    pattern: str
    negation_window: dict[str, int]
    negation_keywords: list[str]
    precedence: int
    on_conflict: str
    conservative_rationale: str


class RuleTable(BaseModel):
    """The frozen rule table structure."""

    schema_version: str
    provenance: str
    frozen_at: str
    frozen_by: str
    freeze_notes: str
    default_policy: str
    conflict_policy: str
    event_types_covered: list[str]
    rules: list[Rule]


class ZeroLLMResult(BaseModel):
    """Result from zero-LLM baseline extraction."""

    erl: ERL | None
    rule_id: str | None
    table_sha256: str
    parser_version: str
    abstain_reason: str | None


PARSER_VERSION = "zero-llm-v1"
RULE_TABLE_PATH = (
    Path(__file__).parent.parent.parent.parent / "evals" / "expected" / "zero_llm_rules_v1.yaml"
)


def _load_rule_table() -> RuleTable:
    """Load the frozen rule table from YAML."""
    import yaml

    if not RULE_TABLE_PATH.exists():
        raise RuntimeError(f"Rule table not found: {RULE_TABLE_PATH}")

    with open(RULE_TABLE_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return RuleTable.model_validate(data)


def _compute_table_sha256(table: RuleTable) -> str:
    """Compute sha256 of the rule table for provenance."""
    import yaml

    # Serialize deterministically (sorted keys)
    content = yaml.dump(table.model_dump(), sort_keys=True)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def _whitespace_word_count(
    text: str,
    before: int,
    after: int,
    match_start: int,
    match_end: int,
) -> list[str]:
    """Extract words within negation window (whitespace-separated)."""
    # Get text before match
    before_text = text[:match_start].strip()
    after_text = text[match_end:].strip()

    # Split on whitespace and take last N words from before, first M from after
    before_words = before_text.split() if before_text else []
    after_words = after_text.split() if after_text else []

    window_words = []
    if before > 0 and before_words:
        window_words.extend(before_words[-before:] if len(before_words) >= before else before_words)
    if after > 0 and after_words:
        window_words.extend(after_words[:after] if len(after_words) >= after else after_words)

    return window_words


def _check_negation(text: str, match_start: int, match_end: int, rule: Rule) -> bool:
    """Check if negation keywords appear in the negation window."""
    if not rule.negation_keywords:
        return False

    before = rule.negation_window.get("before", 0)
    after = rule.negation_window.get("after", 0)

    if before == 0 and after == 0:
        return False

    window_words = _whitespace_word_count(text, before, after, match_start, match_end)
    window_text_lower = " ".join(window_words).lower()

    for keyword in rule.negation_keywords:
        if keyword.lower() in window_text_lower:
            log.debug("negation_found", rule_id=rule.rule_id, keyword=keyword)
            return True

    return False


def _apply_rule(text: str, event_id: str, event_type: str, rule: Rule) -> tuple[ERL | None, str]:
    """Apply one rule to text. Returns (ERL or None, reason)."""
    # Compile pattern
    pattern = re.compile(rule.pattern, re.IGNORECASE | re.DOTALL)

    # Search for match
    match = pattern.search(text)
    if not match:
        return None, "no_pattern_match"

    log.debug("rule_matched", rule_id=rule.rule_id, event_type=event_type)

    # Check negation
    if _check_negation(text, match.start(), match.end(), rule):
        return None, "negation_keywords_in_window"

    # Abstain-only rule (edge is None)
    if rule.edge is None:
        return None, f"abstain_only_rule:{rule.rule_id}"

    # Construct ERL from edge tuple
    edge = rule.edge
    try:
        actor = Actor(
            name=_actor_name_for_type(edge.actor_type),
            type=ActorType(edge.actor_type),
            influence_scope="unknown",
        )
        obj = ERLObject(
            name=_object_name_for_type(edge.object_type, event_type),
            type=ObjectType(edge.object_type),
            sector=_sector_for_type(event_type),
        )
        causal = _default_causal_links(event_type)

        erl = ERL(
            event_id=event_id,
            event_type=event_type,
            actor=actor,
            action=ActionType(edge.action),
            action_detail=f"{event_type} event (structural only, zero-LLM baseline)",
            object=obj,
            summary=(
                f"{' '.join(actor.name.split())} {edge.action} regarding {obj.name}; "
                f"structural only, no outcome."
            ),
            temporal=TemporalClass(edge.temporal_class),
            causal_structure=causal,
            uncertainty=0.5,  # Fixed baseline uncertainty
            source_text_hash=hashlib.sha256(text.encode("utf-8")).hexdigest()[:16],
        )
        return erl, "success"
    except Exception as e:
        log.error("erl_construction_failed", rule_id=rule.rule_id, error=str(e))
        return None, f"erl_construction_failed:{str(e)[:80]}"


def _actor_name_for_type(actor_type: str) -> str:
    """Map actor type to conservative actor name."""
    names = {
        "central_bank": "Federal Reserve",
        "organization": "Bureau of Labor Statistics",
        "collective": "Reporting Persons",
    }
    return names.get(actor_type, "Unknown Actor")


def _object_name_for_type(object_type: str, event_type: str) -> str:
    """Map object type + event_type to conservative object name."""
    if event_type == "FOMC":
        return "policy interest rate"
    elif event_type == "CPI":
        return "consumer price index"
    elif event_type == "NFP":
        return "employment situation"
    elif event_type == "13d":
        return "beneficial ownership"
    return "unspecified"


def _sector_for_type(event_type: str) -> str:
    """Map event_type to sector."""
    if event_type in ("FOMC", "CPI", "NFP"):
        return "macro"
    elif event_type == "13d":
        return "entity"
    return "unknown"


def _default_causal_links(event_type: str) -> list[CausalLink]:
    """Provide minimal conservative causal links."""
    if event_type == "FOMC":
        return [
            CausalLink(cause="policy rate", effect="borrowing cost"),
            CausalLink(cause="borrowing cost", effect="economic activity"),
        ]
    elif event_type == "CPI":
        return [CausalLink(cause="price level", effect="purchasing power")]
    elif event_type == "NFP":
        return [CausalLink(cause="payroll employment", effect="labor income")]
    elif event_type == "13d":
        return [CausalLink(cause="ownership change", effect="corporate control")]
    return [CausalLink(cause="event", effect="economic condition")]


def extract(
    text: str,
    event_id: str,
    event_type: str,
    rule_table_path: Path | None = None,
) -> ZeroLLMResult:
    """Extract ERL from text using frozen mechanical rules.

    Args:
        text: Source text to extract from
        event_id: Event identifier
        event_type: Event type (FOMC, CPI, NFP, 13d)
        rule_table_path: Optional override path for rule table (for testing)

    Returns:
        ZeroLLMResult with ERL (or None if abstain) + provenance
    """
    # Load frozen rule table
    load_path = rule_table_path or RULE_TABLE_PATH
    try:
        table = _load_rule_table()
    except Exception as e:
        log.error("rule_table_load_failed", path=str(load_path), error=str(e))
        return ZeroLLMResult(
            erl=None,
            rule_id=None,
            table_sha256="unknown",
            parser_version=PARSER_VERSION,
            abstain_reason=f"rule_table_load_failed:{str(e)[:80]}",
        )

    table_sha256 = _compute_table_sha256(table)

    # Input validation at boundaries
    if not text or not text.strip():
        return ZeroLLMResult(
            erl=None,
            rule_id=None,
            table_sha256=table_sha256,
            parser_version=PARSER_VERSION,
            abstain_reason="empty_text",
        )

    # Unknown event_type → abstain
    if event_type not in table.event_types_covered:
        log.warning("unknown_event_type", event_type=event_type, covered=table.event_types_covered)
        return ZeroLLMResult(
            erl=None,
            rule_id=None,
            table_sha256=table_sha256,
            parser_version=PARSER_VERSION,
            abstain_reason=f"unknown_event_type:{event_type}",
        )

    # Filter rules by event_type
    matching_rules = [r for r in table.rules if r.event_type == event_type]

    # Apply all matching rules and collect results
    rule_matches: list[tuple[ERL, Rule, str]] = []
    abstains: list[tuple[Rule, str]] = []

    for rule in matching_rules:
        erl, reason = _apply_rule(text, event_id, event_type, rule)
        if erl:
            rule_matches.append((erl, rule, reason))
        else:
            abstains.append((rule, reason))

    # Check for abstain-only rule matches first (highest precedence, e.g., 110)
    # Only consider rules that actually matched their pattern (not "no_pattern_match")
    abstain_only_matches = [
        (r, reason) for r, reason in abstains
        if r.edge is None and reason != "no_pattern_match"
    ]
    if abstain_only_matches:
        # Abstain-only rules suppress action rules
        rule = abstain_only_matches[0][0]
        return ZeroLLMResult(
            erl=None,
            rule_id=rule.rule_id,
            table_sha256=table_sha256,
            parser_version=PARSER_VERSION,
            abstain_reason=f"abstain_only_rule:{rule.rule_id}",
        )

    # No rules produced an ERL → abstain
    if not rule_matches:
        first_abstain = abstains[0] if abstains else (None, "no_rules_matched")
        return ZeroLLMResult(
            erl=None,
            rule_id=first_abstain[0].rule_id if first_abstain[0] else None,
            table_sha256=table_sha256,
            parser_version=PARSER_VERSION,
            abstain_reason=first_abstain[1],
        )

    # Conflict resolution: highest precedence wins
    # Sort by precedence descending
    rule_matches.sort(key=lambda x: x[1].precedence, reverse=True)

    # Check for conflicts (same highest precedence)
    if len(rule_matches) > 1:
        highest_prec = rule_matches[0][1].precedence
        tied_matches = [m for m in rule_matches if m[1].precedence == highest_prec]
        if len(tied_matches) > 1:
            tied_rule_ids = [m[1].rule_id for m in tied_matches]
            log.warning("conflict_detected", tied_rules=tied_rule_ids, precedence=highest_prec)
            return ZeroLLMResult(
                erl=None,
                rule_id=None,
                table_sha256=table_sha256,
                parser_version=PARSER_VERSION,
                abstain_reason=f"conflict:tied_rules:{','.join(tied_rule_ids)}",
            )

    # Single winner
    erl, rule, reason = rule_matches[0]
    return ZeroLLMResult(
        erl=erl,
        rule_id=rule.rule_id,
        table_sha256=table_sha256,
        parser_version=PARSER_VERSION,
        abstain_reason=None,
    )
