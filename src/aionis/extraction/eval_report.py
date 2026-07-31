"""Versioned JSON evaluation report for E3 extraction metrics.

This module renders RD-06 OverallMetrics with provider/model/prompt/schema/
cache/token/latency metadata into a byte-stable JSON report.

Frozen semantics (RD-07 task):
- Report output path is passed EXPLICITLY by caller (no default path)
- ATOMIC write: write to temp file then os.replace
- Existing target file ⇒ FAIL CLOSED (reject overwrite by default)
- Empty evaluation set (no events) ⇒ REJECT (raise)
- BYTE-STABLE JSON: schema_version, input_sha256, sorted keys + compact separators
- token counts and cost fields may be UNKNOWN (null)
- NO model calls, NO ledger writes, NO network I/O
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from aionis.extraction.eval_metrics import OverallMetrics

SCHEMA_VERSION = "1.0.0"


@dataclass(frozen=True)
class ProviderMetadata:
    """Provider and model metadata."""

    provider: str
    model: str
    prompt_version: str | None
    schema_version: str | None


@dataclass(frozen=True)
class ExecutionMetadata:
    """Execution and cost metadata (all fields optional)."""

    cache_hit_rate: float | None
    total_tokens: int | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_cost_usd: float | None
    avg_latency_ms: float | None


@dataclass(frozen=True)
class EvalReport:
    """Complete evaluation report."""

    schema_version: str
    generated_at: str | None
    input_sha256: str
    provider: ProviderMetadata
    execution: ExecutionMetadata
    metrics: OverallMetrics


def compute_input_sha256(
    provider: ProviderMetadata,
    execution: ExecutionMetadata,
    metrics: OverallMetrics,
    generated_at: str | None = None,
) -> str:
    """Compute canonical SHA-256 hash of inputs for byte-stability.

    Args:
        provider: Provider metadata
        execution: Execution metadata
        metrics: Overall metrics from RD-06
        generated_at: Optional timestamp (included in hash if provided)

    Returns:
        Hex-encoded SHA-256 hash of canonical JSON representation
    """
    # Create canonical representation with sorted keys
    canonical = {
        "provider": {
            "provider": provider.provider,
            "model": provider.model,
            "prompt_version": provider.prompt_version,
            "schema_version": provider.schema_version,
        },
        "execution": {
            "cache_hit_rate": execution.cache_hit_rate,
            "total_tokens": execution.total_tokens,
            "prompt_tokens": execution.prompt_tokens,
            "completion_tokens": execution.completion_tokens,
            "total_cost_usd": execution.total_cost_usd,
            "avg_latency_ms": execution.avg_latency_ms,
        },
        "metrics": {
            "n": metrics.n,
            "tp": metrics.tp,
            "fp": metrics.fp,
            "fn": metrics.fn,
            "precision": metrics.precision,
            "recall": metrics.recall,
            "f1": metrics.f1,
            "coverage": metrics.coverage,
            "abstention": metrics.abstention,
            "invalid_schema": metrics.invalid_schema,
            "event_exact": metrics.event_exact,
            "per_field_accuracy": metrics.per_field_accuracy,
            "macro_by_event_type": metrics.macro_by_event_type,
        },
    }

    # Include generated_at in hash if provided
    if generated_at is not None:
        canonical["generated_at"] = generated_at

    # Sort all nested dictionaries recursively
    def sort_dict(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: sort_dict(v) for k, v in sorted(obj.items())}
        elif isinstance(obj, list):
            return [sort_dict(item) for item in obj]
        elif isinstance(obj, float):
            # Normalize floats for consistent serialization
            return round(obj, 10)
        return obj

    sorted_canonical = sort_dict(canonical)
    json_bytes = json.dumps(sorted_canonical, separators=(",", ":")).encode("utf-8")
    return sha256(json_bytes).hexdigest()


def build_report(
    provider: ProviderMetadata,
    execution: ExecutionMetadata,
    metrics: OverallMetrics,
    generated_at: datetime | str | None = None,
) -> EvalReport:
    """Build an evaluation report.

    Args:
        provider: Provider and model metadata
        execution: Execution metadata (tokens/cost may be null)
        metrics: Overall metrics from RD-06
        generated_at: Optional timestamp (datetime, ISO string, or None to omit)

    Returns:
        EvalReport ready for serialization

    Raises:
        ValueError: If metrics.n == 0 (empty evaluation set)
    """
    if metrics.n == 0:
        raise ValueError("Cannot generate report for empty evaluation set (metrics.n == 0)")

    # Normalize generated_at to ISO string if provided as datetime
    generated_at_str: str | None
    if generated_at is None:
        generated_at_str = None
    elif isinstance(generated_at, datetime):
        generated_at_str = generated_at.isoformat()
    else:
        generated_at_str = generated_at

    input_hash = compute_input_sha256(provider, execution, metrics, generated_at_str)

    return EvalReport(
        schema_version=SCHEMA_VERSION,
        generated_at=generated_at_str,
        input_sha256=input_hash,
        provider=provider,
        execution=execution,
        metrics=metrics,
    )


def write_report(
    report: EvalReport,
    output_path: Path | str,
    *,
    overwrite: bool = False,
) -> None:
    """Write evaluation report to file with atomic semantics.

    Args:
        report: EvalReport to write
        output_path: Target file path (EXPLICIT, no default)
        overwrite: If False, reject existing file (fail closed)

    Raises:
        FileExistsError: If output_path exists and overwrite=False
        ValueError: If output_path is empty string or invalid
    """
    output_str = str(output_path) if output_path else ""
    if not output_str or output_str.strip() == "":
        raise ValueError("output_path cannot be empty")

    output = Path(output_path)

    if output.exists() and not overwrite:
        raise FileExistsError(f"Target file exists (overwrite=False): {output}")

    # Ensure parent directory exists
    output.parent.mkdir(parents=True, exist_ok=True)

    # Serialize to JSON with sorted keys and compact separators
    # Use default=str to handle datetime and other non-serializable types
    report_dict = asdict(report)
    json_bytes = json.dumps(
        report_dict,
        separators=(",", ":"),
        sort_keys=True,
        default=str,
    ).encode("utf-8")

    # Atomic write: temp file + os.replace
    output_dir = output.parent
    with tempfile.NamedTemporaryFile(mode="wb", dir=output_dir, delete=False) as tmp:
        tmp.write(json_bytes)
        tmp_path = Path(tmp.name)

    try:
        os.replace(tmp_path, output)
    except BaseException:
        # Clean up temp file if replace fails
        try:
            tmp_path.unlink()
        except BaseException:
            pass
        raise


__all__ = [
    "SCHEMA_VERSION",
    "ProviderMetadata",
    "ExecutionMetadata",
    "EvalReport",
    "compute_input_sha256",
    "build_report",
    "write_report",
]
