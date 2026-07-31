"""Deterministic evaluation metrics for E3 causal-edge extraction.

This module implements field-level and event-level metrics WITHOUT LLM-as-judge.
The metrics are frozen by the task RD-06 specification and must not be modified.

Key frozen semantics:
- Evaluation unit = event_id
- Only adjudicated gold (adjudicated=true) is compared; non-adjudicated gold is skipped
- A prediction is INVALID if it fails to parse OR has edge count >1
- Invalid predictions are treated as empty for TP/FP/FN AND counted separately as invalid_schema
- 0 edges = abstain; 1 edge = a prediction
- Edge identity = FULL tuple (sic_sector, direction, mechanism_keyword, horizon_bucket)
- Zero denominator ⇒ JSON null (never 0)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aionis.schema.causal_edge import CausalEdge
from aionis.schema.gold_annotation import GoldCausalAnnotationV1


@dataclass(frozen=True)
class EdgeTuple:
    """The full identity tuple for a causal edge."""

    sic_sector: str
    direction: str
    mechanism_keyword: str
    horizon_bucket: str

    @classmethod
    def from_edge(cls, edge: CausalEdge) -> EdgeTuple:
        return cls(
            sic_sector=edge.sic_sector.value,
            direction=edge.direction.value,
            mechanism_keyword=edge.mechanism_keyword.value,
            horizon_bucket=edge.horizon_bucket.value,
        )


@dataclass(frozen=True)
class EventMetrics:
    """Metrics for a single event."""

    event_id: str
    event_type: str
    has_gold: bool
    has_prediction: bool
    prediction_valid: bool
    gold_abstained: bool
    pred_abstained: bool
    gold_tuple: EdgeTuple | None
    pred_tuple: EdgeTuple | None
    is_tp: bool
    is_fp: bool
    is_fn: bool
    is_exact: bool


def evaluate_event(
    gold: GoldCausalAnnotationV1 | None,
    prediction: dict[str, Any] | None,
) -> EventMetrics:
    """Evaluate a single event against gold.

    Args:
        gold: Gold annotation (may be None if non-adjudicated)
        prediction: Raw prediction dict (may be None or malformed)

    Returns:
        EventMetrics with all evaluation flags
    """
    # Skip non-adjudicated gold
    if gold is None or not gold.adjudicated:
        # Return a placeholder that will be filtered out
        return EventMetrics(
            event_id=gold.event_id if gold else "unknown",
            event_type=gold.event_type if gold else "unknown",
            has_gold=False,
            has_prediction=False,
            prediction_valid=False,
            gold_abstained=False,
            pred_abstained=False,
            gold_tuple=None,
            pred_tuple=None,
            is_tp=False,
            is_fp=False,
            is_fn=False,
            is_exact=False,
        )

    # Parse prediction
    prediction_valid = True
    pred_abstained = False
    pred_tuple: EdgeTuple | None = None

    if prediction is None:
        prediction_valid = False
    else:
        try:
            # Check for required fields
            if "causal_edges" not in prediction:
                prediction_valid = False
            else:
                edges = prediction["causal_edges"]
                if not isinstance(edges, list):
                    prediction_valid = False
                elif len(edges) > 1:
                    # More than 1 edge = invalid
                    prediction_valid = False
                elif len(edges) == 0:
                    pred_abstained = True
                else:
                    # Exactly 1 edge - parse it
                    edge_dict = edges[0]
                    if not isinstance(edge_dict, dict):
                        prediction_valid = False
                    else:
                        # Parse as CausalEdge
                        edge = CausalEdge(**edge_dict)
                        pred_tuple = EdgeTuple.from_edge(edge)
        except Exception:
            # Any parse error = invalid
            prediction_valid = False

    # Extract gold
    gold_abstained = len(gold.causal_edges) == 0
    gold_tuple: EdgeTuple | None = None
    if not gold_abstained:
        gold_tuple = EdgeTuple.from_edge(gold.causal_edges[0])

    # Determine TP/FP/FN
    # Invalid predictions are treated as empty (no edge) for TP/FP/FN
    # TP: both have edge and tuples equal
    # FP: pred has edge but (gold abstained OR tuples differ)
    # FN: gold has edge but (pred abstained/invalid OR tuples differ)
    effective_pred_tuple = pred_tuple if prediction_valid else None
    is_tp = (
        gold_tuple is not None
        and effective_pred_tuple is not None
        and gold_tuple == effective_pred_tuple
    )
    is_fp = effective_pred_tuple is not None and (
        gold_tuple is None or gold_tuple != effective_pred_tuple
    )
    is_fn = gold_tuple is not None and (
        effective_pred_tuple is None or gold_tuple != effective_pred_tuple
    )

    # Determine exact match
    # Exact if: (valid prediction AND both abstain) OR (valid prediction AND tuples equal)
    # Invalid predictions are NEVER exact, even if gold abstains
    is_exact = prediction_valid and (
        (gold_abstained and pred_abstained)
        or (
            gold_tuple is not None
            and pred_tuple is not None
            and gold_tuple == pred_tuple
        )
    )

    return EventMetrics(
        event_id=gold.event_id,
        event_type=gold.event_type,
        has_gold=True,
        has_prediction=prediction is not None,
        prediction_valid=prediction_valid,
        gold_abstained=gold_abstained,
        pred_abstained=pred_abstained,
        gold_tuple=gold_tuple,
        pred_tuple=pred_tuple,
        is_tp=is_tp,
        is_fp=is_fp,
        is_fn=is_fn,
        is_exact=is_exact,
    )


@dataclass(frozen=True)
class OverallMetrics:
    """Overall metrics across all evaluated events."""

    n: int
    tp: int
    fp: int
    fn: int
    precision: float | None
    recall: float | None
    f1: float | None
    coverage: float
    abstention: float
    invalid_schema: float
    event_exact: float
    per_field_accuracy: dict[str, dict[str, Any]]
    macro_by_event_type: dict[str, dict[str, Any]]


def compute_metrics(
    event_metrics: list[EventMetrics],
) -> OverallMetrics:
    """Compute overall metrics from event-level evaluations.

    Args:
        event_metrics: List of EventMetrics from evaluate_event

    Returns:
        OverallMetrics with all aggregated metrics
    """
    # Filter to only adjudicated gold events
    evaluated = [em for em in event_metrics if em.has_gold]
    n = len(evaluated)

    if n == 0:
        return OverallMetrics(
            n=0,
            tp=0,
            fp=0,
            fn=0,
            precision=None,
            recall=None,
            f1=None,
            coverage=0.0,
            abstention=0.0,
            invalid_schema=0.0,
            event_exact=0.0,
            per_field_accuracy={},
            macro_by_event_type={},
        )

    # Count TP/FP/FN
    tp = sum(1 for em in evaluated if em.is_tp)
    fp = sum(1 for em in evaluated if em.is_fp)
    fn = sum(1 for em in evaluated if em.is_fn)

    # Compute precision/recall/F1 with zero-denominator ⇒ null
    precision: float | None = None
    if tp + fp > 0:
        precision = tp / (tp + fp)

    recall: float | None = None
    if tp + fn > 0:
        recall = tp / (tp + fn)

    f1: float | None = None
    if precision is not None and recall is not None and (precision + recall) > 0:
        f1 = 2 * precision * recall / (precision + recall)

    # Coverage, abstention, invalid_schema
    coverage = sum(1 for em in evaluated if em.prediction_valid and not em.pred_abstained) / n
    abstention = sum(1 for em in evaluated if em.prediction_valid and em.pred_abstained) / n
    invalid_schema = sum(1 for em in evaluated if not em.prediction_valid) / n

    # Event exact
    event_exact = sum(1 for em in evaluated if em.is_exact) / n

    # Per-field accuracy (only on paired subset where both have exactly one edge)
    paired = [em for em in evaluated if em.gold_tuple is not None and em.pred_tuple is not None]
    paired_n = len(paired)

    per_field_accuracy: dict[str, dict[str, Any]] = {}
    if paired_n > 0:
        fields = ["sic_sector", "direction", "mechanism_keyword", "horizon_bucket"]
        for field in fields:
            correct = sum(
                1 for em in paired
                if getattr(em.gold_tuple, field) == getattr(em.pred_tuple, field)
            )
            per_field_accuracy[field] = {
                "accuracy": correct / paired_n,
                "denominator": paired_n,
            }
    else:
        for field in ["sic_sector", "direction", "mechanism_keyword", "horizon_bucket"]:
            per_field_accuracy[field] = {
                "accuracy": None,
                "denominator": 0,
            }

    # Macro metrics by event_type
    event_types = set(em.event_type for em in evaluated)
    macro_by_event_type: dict[str, dict[str, Any]] = {}

    for event_type in sorted(event_types):
        stratum = [em for em in evaluated if em.event_type == event_type]
        stratum_n = len(stratum)

        if stratum_n == 0:
            continue

        stratum_tp = sum(1 for em in stratum if em.is_tp)
        stratum_fp = sum(1 for em in stratum if em.is_fp)
        stratum_fn = sum(1 for em in stratum if em.is_fn)

        stratum_precision: float | None = None
        if stratum_tp + stratum_fp > 0:
            stratum_precision = stratum_tp / (stratum_tp + stratum_fp)

        stratum_recall: float | None = None
        if stratum_tp + stratum_fn > 0:
            stratum_recall = stratum_tp / (stratum_tp + stratum_fn)

        stratum_f1: float | None = None
        if (
            stratum_precision is not None
            and stratum_recall is not None
            and (stratum_precision + stratum_recall) > 0
        ):
            stratum_f1 = (
                2 * stratum_precision * stratum_recall
                / (stratum_precision + stratum_recall)
            )

        macro_by_event_type[event_type] = {
            "n": stratum_n,
            "precision": stratum_precision,
            "recall": stratum_recall,
            "f1": stratum_f1,
        }

    # Compute macro averages (equal-weight over non-null strata)
    macro_precision: float | None = None
    macro_recall: float | None = None
    macro_f1: float | None = None

    # Collect non-null values
    valid_precisions = [
        m["precision"] for m in macro_by_event_type.values() if m["precision"] is not None
    ]
    valid_recalls = [
        m["recall"] for m in macro_by_event_type.values() if m["recall"] is not None
    ]
    valid_f1s = [
        m["f1"] for m in macro_by_event_type.values() if m["f1"] is not None
    ]

    omitted_strata = sorted(
        set(macro_by_event_type.keys())
        - {
            et
            for et, metrics in macro_by_event_type.items()
            if metrics["precision"] is not None
            or metrics["recall"] is not None
            or metrics["f1"] is not None
        }
    )

    if valid_precisions:
        macro_precision = sum(valid_precisions) / len(valid_precisions)
    if valid_recalls:
        macro_recall = sum(valid_recalls) / len(valid_recalls)
    if valid_f1s:
        macro_f1 = sum(valid_f1s) / len(valid_f1s)

    macro_result = {
        "precision": macro_precision,
        "recall": macro_recall,
        "f1": macro_f1,
    }
    if omitted_strata:
        macro_result["omitted_strata"] = omitted_strata

    return OverallMetrics(
        n=n,
        tp=tp,
        fp=fp,
        fn=fn,
        precision=precision,
        recall=recall,
        f1=f1,
        coverage=coverage,
        abstention=abstention,
        invalid_schema=invalid_schema,
        event_exact=event_exact,
        per_field_accuracy=per_field_accuracy,
        macro_by_event_type=macro_by_event_type,
    )


def evaluate_extraction(
    gold_records: list[GoldCausalAnnotationV1],
    predictions: dict[str, dict[str, Any]],
) -> OverallMetrics:
    """Evaluate extraction predictions against gold records.

    Args:
        gold_records: List of gold annotations (may include non-adjudicated)
        predictions: Dict mapping event_id to prediction dict

    Returns:
        OverallMetrics with all evaluation metrics
    """
    # Build lookup for predictions
    event_metrics: list[EventMetrics] = []

    for gold in gold_records:
        prediction = predictions.get(gold.event_id)
        event_metrics.append(evaluate_event(gold, prediction))

    return compute_metrics(event_metrics)


__all__ = [
    "EdgeTuple",
    "EventMetrics",
    "OverallMetrics",
    "evaluate_event",
    "compute_metrics",
    "evaluate_extraction",
]
