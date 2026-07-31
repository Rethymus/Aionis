"""Tests for LLM evaluation metrics (RD-06) — hermetic, hand-computed oracles.

All oracles are computed by hand and documented in comments. No LLM/judge calls.
"""

from datetime import datetime

import pytest

from aionis.extraction.eval_metrics import (
    EdgeTuple,
    compute_metrics,
    evaluate_event,
    evaluate_extraction,
)
from aionis.schema.causal_edge import (
    CausalEdge,
    Direction,
    HorizonBucket,
    MechanismKeyword,
    SicSector,
)
from aionis.schema.gold_annotation import GoldCausalAnnotationV1


def test_both_abstain() -> None:
    """Both gold and prediction abstain (0 edges).

    Expected: exact=True, TP/FP/FN all False, abstention counted.
    """
    # Gold: abstained (no edges)
    gold = GoldCausalAnnotationV1(
        schema_version="e3-causal-gold-v1",
        event_id="evt-001",
        event_type="13d",
        filed_ts=datetime(2024, 1, 1, 12, 0, 0),
        source_text_sha256="a" * 64,
        source_span_start=0,
        source_span_end=100,
        causal_edges=[],
        abstention_reason="no_defensible_edge",
        annotator_ids=["alice"],
        adjudicated=True,
    )

    # Prediction: abstained (empty edges)
    pred = {"causal_edges": []}

    result = evaluate_event(gold, pred)

    # Oracle: both abstain → exact match, no TP/FP/FN
    assert result.is_exact is True
    assert result.is_tp is False
    assert result.is_fp is False
    assert result.is_fn is False
    assert result.gold_abstained is True
    assert result.pred_abstained is True
    assert result.prediction_valid is True


def test_one_side_abstain() -> None:
    """Gold has edge, prediction abstains.

    Expected: FN=True, FP/TP=False, exact=False.
    """
    gold = GoldCausalAnnotationV1(
        schema_version="e3-causal-gold-v1",
        event_id="evt-002",
        event_type="13d",
        filed_ts=datetime(2024, 1, 1, 12, 0, 0),
        source_text_sha256="a" * 64,
        source_span_start=0,
        source_span_end=100,
        causal_edges=[
            CausalEdge(
                sic_sector=SicSector.HLTH,
                direction=Direction.POSITIVE,
                mechanism_keyword=MechanismKeyword.EARNINGS_SIGNAL,
                horizon_bucket=HorizonBucket.SHORT,
            )
        ],
        abstention_reason=None,
        annotator_ids=["alice"],
        adjudicated=True,
    )

    pred = {"causal_edges": []}

    result = evaluate_event(gold, pred)

    # Oracle: gold has edge, pred abstains → FN only
    assert result.is_exact is False
    assert result.is_tp is False
    assert result.is_fp is False
    assert result.is_fn is True
    assert result.gold_abstained is False
    assert result.pred_abstained is True


def test_tuple_exact_match() -> None:
    """Both have edge and tuples are equal.

    Expected: TP=True, FN/FP=False, exact=True.
    """
    gold = GoldCausalAnnotationV1(
        schema_version="e3-causal-gold-v1",
        event_id="evt-003",
        event_type="13d",
        filed_ts=datetime(2024, 1, 1, 12, 0, 0),
        source_text_sha256="a" * 64,
        source_span_start=0,
        source_span_end=100,
        causal_edges=[
            CausalEdge(
                sic_sector=SicSector.MONEY,
                direction=Direction.NEGATIVE,
                mechanism_keyword=MechanismKeyword.OWNERSHIP_CHANGE,
                horizon_bucket=HorizonBucket.MEDIUM,
            )
        ],
        abstention_reason=None,
        annotator_ids=["alice"],
        adjudicated=True,
    )

    pred = {
        "causal_edges": [
            {
                "sic_sector": "Money",
                "direction": "negative",
                "mechanism_keyword": "ownership_change",
                "horizon_bucket": "medium",
            }
        ]
    }

    result = evaluate_event(gold, pred)

    # Oracle: exact tuple match → TP + exact, no FN
    assert result.is_exact is True
    assert result.is_tp is True
    assert result.is_fp is False
    assert result.is_fn is False


def test_partial_tuple_mismatch() -> None:
    """Both have edge but tuples differ in one field.

    Expected: FP=True, FN=True, TP=False, exact=False.
    Oracle: mismatch in horizon_bucket (short vs medium).
    """
    gold = GoldCausalAnnotationV1(
        schema_version="e3-causal-gold-v1",
        event_id="evt-004",
        event_type="8k_2_02",
        filed_ts=datetime(2024, 1, 1, 12, 0, 0),
        source_text_sha256="a" * 64,
        source_span_start=0,
        source_span_end=100,
        causal_edges=[
            CausalEdge(
                sic_sector=SicSector.BUSEQ,
                direction=Direction.POSITIVE,
                mechanism_keyword=MechanismKeyword.GUIDANCE,
                horizon_bucket=HorizonBucket.SHORT,
            )
        ],
        abstention_reason=None,
        annotator_ids=["alice"],
        adjudicated=True,
    )

    # Prediction differs in horizon_bucket (medium vs short)
    pred = {
        "causal_edges": [
            {
                "sic_sector": "BusEq",
                "direction": "positive",
                "mechanism_keyword": "guidance",
                "horizon_bucket": "medium",  # MISMATCH
            }
        ]
    }

    result = evaluate_event(gold, pred)

    # Oracle: partial mismatch → both FP and FN
    assert result.is_exact is False
    assert result.is_tp is False
    assert result.is_fp is True
    assert result.is_fn is True


def test_invalid_prediction_too_many_edges() -> None:
    """Prediction has >1 edge → invalid.

    Expected: prediction_valid=False, treated as empty for TP/FP/FN (so FN=True
    when gold has edge), exact=False, invalid_schema counted.
    """
    gold = GoldCausalAnnotationV1(
        schema_version="e3-causal-gold-v1",
        event_id="evt-005",
        event_type="13d",
        filed_ts=datetime(2024, 1, 1, 12, 0, 0),
        source_text_sha256="a" * 64,
        source_span_start=0,
        source_span_end=100,
        causal_edges=[
            CausalEdge(
                sic_sector=SicSector.UTILS,
                direction=Direction.NEGATIVE,
                mechanism_keyword=MechanismKeyword.OTHER,
                horizon_bucket=HorizonBucket.LONG,
            )
        ],
        abstention_reason=None,
        annotator_ids=["alice"],
        adjudicated=True,
    )

    # Invalid: 2 edges
    pred = {
        "causal_edges": [
            {
                "sic_sector": "Utils",
                "direction": "negative",
                "mechanism_keyword": "other",
                "horizon_bucket": "long",
            },
            {
                "sic_sector": "Money",
                "direction": "positive",
                "mechanism_keyword": "ownership_change",
                "horizon_bucket": "medium",
            },
        ]
    }

    result = evaluate_event(gold, pred)

    # Oracle: too many edges → invalid, treated as empty → FN when gold has edge
    assert result.prediction_valid is False
    assert result.is_exact is False  # Invalid predictions are NEVER exact
    assert result.is_tp is False
    assert result.is_fp is False
    assert result.is_fn is True  # Invalid ≡ empty → FN when gold has edge


def test_invalid_prediction_parse_error() -> None:
    """Prediction fails to parse → invalid.

    Expected: prediction_valid=False, treated as empty for TP/FP/FN (so FN=True
    when gold has edge), exact=False.
    """
    gold = GoldCausalAnnotationV1(
        schema_version="e3-causal-gold-v1",
        event_id="evt-006",
        event_type="13d",
        filed_ts=datetime(2024, 1, 1, 12, 0, 0),
        source_text_sha256="a" * 64,
        source_span_start=0,
        source_span_end=100,
        causal_edges=[
            CausalEdge(
                sic_sector=SicSector.TELCM,
                direction=Direction.POSITIVE,
                mechanism_keyword=MechanismKeyword.EARNINGS_SIGNAL,
                horizon_bucket=HorizonBucket.INSTANT,
            )
        ],
        abstention_reason=None,
        annotator_ids=["alice"],
        adjudicated=True,
    )

    # Invalid: malformed edge dict
    pred = {"causal_edges": [{"invalid_field": "value"}]}

    result = evaluate_event(gold, pred)

    # Oracle: parse error → invalid, treated as empty → FN when gold has edge
    assert result.prediction_valid is False
    assert result.is_exact is False
    assert result.is_tp is False
    assert result.is_fp is False
    assert result.is_fn is True  # Invalid ≡ empty → FN when gold has edge


def test_non_adjudicated_gold_skipped() -> None:
    """Non-adjudicated gold is skipped from metrics.

    Expected: has_gold=False, all metric flags False.
    """
    gold = GoldCausalAnnotationV1(
        schema_version="e3-causal-gold-v1",
        event_id="evt-007",
        event_type="13d",
        filed_ts=datetime(2024, 1, 1, 12, 0, 0),
        source_text_sha256="a" * 64,
        source_span_start=0,
        source_span_end=100,
        causal_edges=[],  # No edges when pending
        abstention_reason="adjudication_pending",
        annotator_ids=["alice"],
        adjudicated=False,  # NOT adjudicated
    )

    pred = {
        "causal_edges": [
            {
                "sic_sector": "Shops",
                "direction": "positive",
                "mechanism_keyword": "guidance",
                "horizon_bucket": "short",
            }
        ]
    }

    result = evaluate_event(gold, pred)

    # Oracle: non-adjudicated → skipped
    assert result.has_gold is False
    assert result.is_exact is False
    assert result.is_tp is False
    assert result.is_fp is False
    assert result.is_fn is False


def test_overall_zero_denominator_precision() -> None:
    """Overall metrics: precision denominator=0 → null.

    Oracle: TP=0, FP=0, FN=1 → precision = 0/(0+0) = None (zero denominator).
    """
    # One event: gold has edge, pred abstains → FN only
    gold = GoldCausalAnnotationV1(
        schema_version="e3-causal-gold-v1",
        event_id="evt-008",
        event_type="13d",
        filed_ts=datetime(2024, 1, 1, 12, 0, 0),
        source_text_sha256="a" * 64,
        source_span_start=0,
        source_span_end=100,
        causal_edges=[
            CausalEdge(
                sic_sector=SicSector.HLTH,
                direction=Direction.POSITIVE,
                mechanism_keyword=MechanismKeyword.EARNINGS_SIGNAL,
                horizon_bucket=HorizonBucket.SHORT,
            )
        ],
        abstention_reason=None,
        annotator_ids=["alice"],
        adjudicated=True,
    )

    pred = {"causal_edges": []}

    event_metrics = [evaluate_event(gold, pred)]
    overall = compute_metrics(event_metrics)

    # Oracle: TP=0, FP=0, FN=1
    assert overall.n == 1
    assert overall.tp == 0
    assert overall.fp == 0
    assert overall.fn == 1
    assert overall.precision is None  # Zero denominator → null
    assert overall.recall == pytest.approx(0.0)  # 0/(0+1) = 0.0
    assert overall.f1 is None  # F1 depends on precision
    assert overall.abstention == pytest.approx(1.0)  # 1 abstain / 1 total
    assert overall.coverage == pytest.approx(0.0)  # 0 covered / 1 total
    assert overall.invalid_schema == pytest.approx(0.0)  # 0 invalid / 1 total


def test_overall_zero_denominator_recall() -> None:
    """Overall metrics: recall denominator=0 → null.

    Oracle: TP=0, FP=1, FN=0 → recall = 0/(0+0) = None.
    """
    # One event: gold abstains, pred has edge → FP only
    gold = GoldCausalAnnotationV1(
        schema_version="e3-causal-gold-v1",
        event_id="evt-009",
        event_type="13d",
        filed_ts=datetime(2024, 1, 1, 12, 0, 0),
        source_text_sha256="a" * 64,
        source_span_start=0,
        source_span_end=100,
        causal_edges=[],
        abstention_reason="no_defensible_edge",
        annotator_ids=["alice"],
        adjudicated=True,
    )

    pred = {
        "causal_edges": [
            {
                "sic_sector": "Money",
                "direction": "negative",
                "mechanism_keyword": "ownership_change",
                "horizon_bucket": "medium",
            }
        ]
    }

    event_metrics = [evaluate_event(gold, pred)]
    overall = compute_metrics(event_metrics)

    # Oracle: TP=0, FP=1, FN=0
    assert overall.n == 1
    assert overall.tp == 0
    assert overall.fp == 1
    assert overall.fn == 0
    assert overall.precision == pytest.approx(0.0)  # 0/(0+1) = 0.0
    assert overall.recall is None  # Zero denominator → null
    assert overall.f1 is None  # F1 depends on recall


def test_overall_perfect_match() -> None:
    """Overall metrics: perfect match (TP=1, FP=0, FN=0).

    Oracle: precision=1.0, recall=1.0, F1=1.0, event_exact=1.0.
    """
    gold = GoldCausalAnnotationV1(
        schema_version="e3-causal-gold-v1",
        event_id="evt-010",
        event_type="13d",
        filed_ts=datetime(2024, 1, 1, 12, 0, 0),
        source_text_sha256="a" * 64,
        source_span_start=0,
        source_span_end=100,
        causal_edges=[
            CausalEdge(
                sic_sector=SicSector.NODUR,
                direction=Direction.POSITIVE,
                mechanism_keyword=MechanismKeyword.EARNINGS_SIGNAL,
                horizon_bucket=HorizonBucket.SHORT,
            )
        ],
        abstention_reason=None,
        annotator_ids=["alice"],
        adjudicated=True,
    )

    pred = {
        "causal_edges": [
            {
                "sic_sector": "NoDur",
                "direction": "positive",
                "mechanism_keyword": "earnings_signal",
                "horizon_bucket": "short",
            }
        ]
    }

    event_metrics = [evaluate_event(gold, pred)]
    overall = compute_metrics(event_metrics)

    # Oracle: TP=1, FP=0, FN=0 → perfect metrics
    assert overall.n == 1
    assert overall.tp == 1
    assert overall.fp == 0
    assert overall.fn == 0
    assert overall.precision == pytest.approx(1.0)
    assert overall.recall == pytest.approx(1.0)
    assert overall.f1 == pytest.approx(1.0)
    assert overall.event_exact == pytest.approx(1.0)
    assert overall.coverage == pytest.approx(1.0)
    assert overall.abstention == pytest.approx(0.0)
    assert overall.invalid_schema == pytest.approx(0.0)


def test_per_field_accuracy() -> None:
    """Per-field accuracy computed on paired subset.

    Oracle: 3 paired events, field accuracy rates computed manually.
    """
    # Event 1: all fields match
    gold1 = GoldCausalAnnotationV1(
        schema_version="e3-causal-gold-v1",
        event_id="evt-011a",
        event_type="13d",
        filed_ts=datetime(2024, 1, 1, 12, 0, 0),
        source_text_sha256="a" * 64,
        source_span_start=0,
        source_span_end=100,
        causal_edges=[
            CausalEdge(
                sic_sector=SicSector.MONEY,
                direction=Direction.NEGATIVE,
                mechanism_keyword=MechanismKeyword.OWNERSHIP_CHANGE,
                horizon_bucket=HorizonBucket.MEDIUM,
            )
        ],
        abstention_reason=None,
        annotator_ids=["alice"],
        adjudicated=True,
    )

    # Event 2: direction differs
    gold2 = GoldCausalAnnotationV1(
        schema_version="e3-causal-gold-v1",
        event_id="evt-011b",
        event_type="13d",
        filed_ts=datetime(2024, 1, 1, 12, 0, 0),
        source_text_sha256="a" * 64,
        source_span_start=0,
        source_span_end=100,
        causal_edges=[
            CausalEdge(
                sic_sector=SicSector.HLTH,
                direction=Direction.POSITIVE,
                mechanism_keyword=MechanismKeyword.GUIDANCE,
                horizon_bucket=HorizonBucket.SHORT,
            )
        ],
        abstention_reason=None,
        annotator_ids=["alice"],
        adjudicated=True,
    )

    # Event 3: mechanism and horizon differ
    gold3 = GoldCausalAnnotationV1(
        schema_version="e3-causal-gold-v1",
        event_id="evt-011c",
        event_type="13d",
        filed_ts=datetime(2024, 1, 1, 12, 0, 0),
        source_text_sha256="a" * 64,
        source_span_start=0,
        source_span_end=100,
        causal_edges=[
            CausalEdge(
                sic_sector=SicSector.BUSEQ,
                direction=Direction.POSITIVE,
                mechanism_keyword=MechanismKeyword.EARNINGS_SIGNAL,
                horizon_bucket=HorizonBucket.LONG,
            )
        ],
        abstention_reason=None,
        annotator_ids=["alice"],
        adjudicated=True,
    )

    preds = {
        "evt-011a": {
            "causal_edges": [
                {
                    "sic_sector": "Money",
                    "direction": "negative",
                    "mechanism_keyword": "ownership_change",
                    "horizon_bucket": "medium",
                }
            ]
        },
        "evt-011b": {
            "causal_edges": [
                {
                    "sic_sector": "Hlth",
                    "direction": "negative",  # MISMATCH
                    "mechanism_keyword": "guidance",
                    "horizon_bucket": "short",
                }
            ]
        },
        "evt-011c": {
            "causal_edges": [
                {
                    "sic_sector": "BusEq",
                    "direction": "positive",
                    "mechanism_keyword": "other",  # MISMATCH
                    "horizon_bucket": "instant",  # MISMATCH
                }
            ]
        },
    }

    overall = evaluate_extraction([gold1, gold2, gold3], preds)

    # Oracle: paired_n=3
    # sic_sector: 3/3 correct → 1.0
    # direction: 2/3 correct → 0.667
    # mechanism_keyword: 2/3 correct → 0.667
    # horizon_bucket: 2/3 correct → 0.667
    assert overall.per_field_accuracy["sic_sector"]["accuracy"] == pytest.approx(1.0)
    assert overall.per_field_accuracy["sic_sector"]["denominator"] == 3
    assert overall.per_field_accuracy["direction"]["accuracy"] == pytest.approx(2.0 / 3.0)
    assert overall.per_field_accuracy["direction"]["denominator"] == 3
    assert overall.per_field_accuracy["mechanism_keyword"]["accuracy"] == pytest.approx(2.0 / 3.0)
    assert overall.per_field_accuracy["mechanism_keyword"]["denominator"] == 3
    assert overall.per_field_accuracy["horizon_bucket"]["accuracy"] == pytest.approx(2.0 / 3.0)
    assert overall.per_field_accuracy["horizon_bucket"]["denominator"] == 3


def test_macro_by_event_type() -> None:
    """Macro metrics grouped by event_type with omitted strata.

    Oracle: 2 event types, one stratum has zero denominator (omitted).
    """
    # 13d events: 1 TP, 1 FP, 0 FN
    gold1 = GoldCausalAnnotationV1(
        schema_version="e3-causal-gold-v1",
        event_id="evt-012a",
        event_type="13d",
        filed_ts=datetime(2024, 1, 1, 12, 0, 0),
        source_text_sha256="a" * 64,
        source_span_start=0,
        source_span_end=100,
        causal_edges=[
            CausalEdge(
                sic_sector=SicSector.UTILS,
                direction=Direction.NEGATIVE,
                mechanism_keyword=MechanismKeyword.OTHER,
                horizon_bucket=HorizonBucket.LONG,
            )
        ],
        abstention_reason=None,
        annotator_ids=["alice"],
        adjudicated=True,
    )

    gold2 = GoldCausalAnnotationV1(
        schema_version="e3-causal-gold-v1",
        event_id="evt-012b",
        event_type="13d",
        filed_ts=datetime(2024, 1, 1, 12, 0, 0),
        source_text_sha256="a" * 64,
        source_span_start=0,
        source_span_end=100,
        causal_edges=[],
        abstention_reason="no_defensible_edge",
        annotator_ids=["alice"],
        adjudicated=True,
    )

    # 8k_2_02 events: 0 TP, 0 FP, 1 FN (gold has edge, pred abstains)
    gold3 = GoldCausalAnnotationV1(
        schema_version="e3-causal-gold-v1",
        event_id="evt-012c",
        event_type="8k_2_02",
        filed_ts=datetime(2024, 1, 1, 12, 0, 0),
        source_text_sha256="a" * 64,
        source_span_start=0,
        source_span_end=100,
        causal_edges=[
            CausalEdge(
                sic_sector=SicSector.CHEMS,
                direction=Direction.POSITIVE,
                mechanism_keyword=MechanismKeyword.EARNINGS_SIGNAL,
                horizon_bucket=HorizonBucket.SHORT,
            )
        ],
        abstention_reason=None,
        annotator_ids=["alice"],
        adjudicated=True,
    )

    preds = {
        "evt-012a": {
            "causal_edges": [
                {
                    "sic_sector": "Utils",
                    "direction": "negative",
                    "mechanism_keyword": "other",
                    "horizon_bucket": "long",
                }
            ]
        },
        "evt-012b": {
            "causal_edges": [
                {
                    "sic_sector": "Money",
                    "direction": "positive",
                    "mechanism_keyword": "guidance",
                    "horizon_bucket": "medium",
                }
            ]
        },
        "evt-012c": {"causal_edges": []},  # Abstain
    }

    overall = evaluate_extraction([gold1, gold2, gold3], preds)

    # Oracle for 13d: TP=1, FP=1, FN=0
    # precision = 1/(1+1) = 0.5
    # recall = 1/(1+0) = 1.0
    # f1 = 2*0.5*1.0/(0.5+1.0) = 1.0/1.5 = 0.667
    assert overall.macro_by_event_type["13d"]["n"] == 2
    assert overall.macro_by_event_type["13d"]["precision"] == pytest.approx(0.5)
    assert overall.macro_by_event_type["13d"]["recall"] == pytest.approx(1.0)
    assert overall.macro_by_event_type["13d"]["f1"] == pytest.approx(2.0 / 3.0)

    # Oracle for 8k_2_02: TP=0, FP=0, FN=1
    # precision = 0/(0+0) = None (zero denominator)
    # recall = 0/(0+1) = 0.0
    # f1 = None (precision is None)
    assert overall.macro_by_event_type["8k_2_02"]["n"] == 1
    assert overall.macro_by_event_type["8k_2_02"]["precision"] is None
    assert overall.macro_by_event_type["8k_2_02"]["recall"] == pytest.approx(0.0)
    assert overall.macro_by_event_type["8k_2_02"]["f1"] is None

    # Macro averages (only over non-null strata)
    # Only 13d contributes to macro precision/f1
    # Both contribute to recall (8k_2_02 has 0.0, which is non-null)


def test_coverage_abstention_invalid_rates() -> None:
    """Coverage, abstention, invalid_schema rates.

    Oracle: 4 events: 1 covered, 1 abstained, 2 invalid.
    """
    golds = [
        GoldCausalAnnotationV1(
            schema_version="e3-causal-gold-v1",
            event_id=f"evt-013-{i}",
            event_type="13d",
            filed_ts=datetime(2024, 1, 1, 12, 0, 0),
            source_text_sha256="a" * 64,
            source_span_start=0,
            source_span_end=100,
            causal_edges=[
                CausalEdge(
                    sic_sector=SicSector.MONEY,
                    direction=Direction.POSITIVE,
                    mechanism_keyword=MechanismKeyword.OWNERSHIP_CHANGE,
                    horizon_bucket=HorizonBucket.MEDIUM,
                )
            ],
            abstention_reason=None,
            annotator_ids=["alice"],
            adjudicated=True,
        )
        for i in range(4)
    ]

    preds = {
        "evt-013-0": {
            "causal_edges": [
                {
                    "sic_sector": "Money",
                    "direction": "positive",
                    "mechanism_keyword": "ownership_change",
                    "horizon_bucket": "medium",
                }
            ]
        },  # Valid, covered
        "evt-013-1": {"causal_edges": []},  # Valid, abstained
        "evt-013-2": {"causal_edges": [{"invalid": "data"}]},  # Invalid (parse error)
        "evt-013-3": {
            "causal_edges": [
                {"sic_sector": "A", "direction": "b"},
                {"sic_sector": "C", "direction": "d"},
            ]
        },  # Invalid (too many edges)
    }

    overall = evaluate_extraction(golds, preds)

    # Oracle: N=4, coverage=1/4=0.25, abstention=1/4=0.25, invalid=2/4=0.5
    assert overall.n == 4
    assert overall.coverage == pytest.approx(0.25)
    assert overall.abstention == pytest.approx(0.25)
    assert overall.invalid_schema == pytest.approx(0.5)


def test_edge_tuple_identity() -> None:
    """EdgeTuple identity matches full tuple semantics."""
    edge1 = CausalEdge(
        sic_sector=SicSector.HLTH,
        direction=Direction.POSITIVE,
        mechanism_keyword=MechanismKeyword.EARNINGS_SIGNAL,
        horizon_bucket=HorizonBucket.SHORT,
    )

    edge2 = CausalEdge(
        sic_sector=SicSector.HLTH,
        direction=Direction.POSITIVE,
        mechanism_keyword=MechanismKeyword.EARNINGS_SIGNAL,
        horizon_bucket=HorizonBucket.SHORT,
    )

    edge3 = CausalEdge(
        sic_sector=SicSector.HLTH,
        direction=Direction.NEGATIVE,  # Differs
        mechanism_keyword=MechanismKeyword.EARNINGS_SIGNAL,
        horizon_bucket=HorizonBucket.SHORT,
    )

    tuple1 = EdgeTuple.from_edge(edge1)
    tuple2 = EdgeTuple.from_edge(edge2)
    tuple3 = EdgeTuple.from_edge(edge3)

    # Oracle: identical edges produce identical tuples
    assert tuple1 == tuple2
    assert tuple1 != tuple3


def test_f1_formula() -> None:
    """F1 formula: 2*P*R / (P+R).

    Oracle: P=0.75, R=0.50 → F1 = 2*0.75*0.5 / (0.75+0.5) = 0.75 / 1.25 = 0.6
    """
    # Create events to achieve P=0.75, R=0.5
    # Need: TP/(TP+FP) = 0.75 and TP/(TP+FN) = 0.5
    # Let TP=3, FP=1 → P=3/4=0.75
    # Let TP=3, FN=3 → R=3/6=0.5
    # Total: TP=3, FP=1, FN=3
    events = []

    # 3 TP events
    for i in range(3):
        gold = GoldCausalAnnotationV1(
            schema_version="e3-causal-gold-v1",
            event_id=f"evt-014-tp-{i}",
            event_type="13d",
            filed_ts=datetime(2024, 1, 1, 12, 0, 0),
            source_text_sha256="a" * 64,
            source_span_start=0,
            source_span_end=100,
            causal_edges=[
                CausalEdge(
                    sic_sector=SicSector.MONEY,
                    direction=Direction.POSITIVE,
                    mechanism_keyword=MechanismKeyword.OWNERSHIP_CHANGE,
                    horizon_bucket=HorizonBucket.MEDIUM,
                )
            ],
            abstention_reason=None,
            annotator_ids=["alice"],
            adjudicated=True,
        )
        events.append(gold)

    # 1 FP event
    gold_fp = GoldCausalAnnotationV1(
        schema_version="e3-causal-gold-v1",
        event_id="evt-014-fp",
        event_type="13d",
        filed_ts=datetime(2024, 1, 1, 12, 0, 0),
        source_text_sha256="a" * 64,
        source_span_start=0,
        source_span_end=100,
        causal_edges=[],
        abstention_reason="no_defensible_edge",
        annotator_ids=["alice"],
        adjudicated=True,
    )
    events.append(gold_fp)

    # 3 FN events
    for i in range(3):
        gold_fn = GoldCausalAnnotationV1(
            schema_version="e3-causal-gold-v1",
            event_id=f"evt-014-fn-{i}",
            event_type="13d",
            filed_ts=datetime(2024, 1, 1, 12, 0, 0),
            source_text_sha256="a" * 64,
            source_span_start=0,
            source_span_end=100,
            causal_edges=[
                CausalEdge(
                    sic_sector=SicSector.HLTH,
                    direction=Direction.POSITIVE,
                    mechanism_keyword=MechanismKeyword.EARNINGS_SIGNAL,
                    horizon_bucket=HorizonBucket.SHORT,
                )
            ],
            abstention_reason=None,
            annotator_ids=["alice"],
            adjudicated=True,
        )
        events.append(gold_fn)

    # Build predictions
    preds = {}
    # 3 TP predictions
    for i in range(3):
        preds[f"evt-014-tp-{i}"] = {
            "causal_edges": [
                {
                    "sic_sector": "Money",
                    "direction": "positive",
                    "mechanism_keyword": "ownership_change",
                    "horizon_bucket": "medium",
                }
            ]
        }
    # 1 FP prediction
    preds["evt-014-fp"] = {
        "causal_edges": [
            {
                "sic_sector": "Shops",
                "direction": "positive",
                "mechanism_keyword": "guidance",
                "horizon_bucket": "short",
            }
        ]
    }
    # 3 FN predictions (all abstain)
    for i in range(3):
        preds[f"evt-014-fn-{i}"] = {"causal_edges": []}

    overall = evaluate_extraction(events, preds)

    # Oracle: P=0.75, R=0.5, F1=0.6
    assert overall.tp == 3
    assert overall.fp == 1
    assert overall.fn == 3
    assert overall.precision == pytest.approx(0.75)
    assert overall.recall == pytest.approx(0.5)
    assert overall.f1 == pytest.approx(0.6)


def test_empty_evaluation() -> None:
    """Empty evaluation (no adjudicated gold).

    Expected: all metrics zero/null, no errors.
    """
    overall = evaluate_extraction([], {})

    assert overall.n == 0
    assert overall.tp == 0
    assert overall.fp == 0
    assert overall.fn == 0
    assert overall.precision is None
    assert overall.recall is None
    assert overall.f1 is None
    assert overall.coverage == pytest.approx(0.0)
    assert overall.abstention == pytest.approx(0.0)
    assert overall.invalid_schema == pytest.approx(0.0)
    assert overall.event_exact == pytest.approx(0.0)
