"""Tests for eval_report module (RD-07).

Hermetic oracles for byte-stability, schema versioning, overwrite protection,
empty set rejection, and null token/cost serialization.
"""

from __future__ import annotations

import json
import re
from datetime import datetime

import pytest

from aionis.extraction.eval_metrics import OverallMetrics
from aionis.extraction.eval_report import (
    SCHEMA_VERSION,
    ExecutionMetadata,
    ProviderMetadata,
    build_report,
    compute_input_sha256,
    write_report,
)


class TestNoRuntimeClock:
    """Tests to verify module does not call runtime clocks."""

    def test_no_datetime_now_or_time_calls(self):
        """Module must NOT call datetime.now(), datetime.today(), or time.time()."""
        import inspect

        import aionis.extraction.eval_report as eval_report_module

        source = inspect.getsource(eval_report_module)

        # Check for forbidden patterns
        forbidden_patterns = [
            r"datetime\.now\(",
            r"datetime\.today\(",
            r"time\.time\(\)",
        ]

        for pattern in forbidden_patterns:
            matches = re.findall(pattern, source)
            assert len(matches) == 0, f"Found {len(matches)} forbidden call(s) to {pattern}"


@pytest.fixture
def sample_provider() -> ProviderMetadata:
    """Sample provider metadata."""
    return ProviderMetadata(
        provider="glm",
        model="glm-4-flash",
        prompt_version="v1.0",
        schema_version="1.0.0",
    )


@pytest.fixture
def sample_execution() -> ExecutionMetadata:
    """Sample execution metadata with unknown tokens/cost."""
    return ExecutionMetadata(
        cache_hit_rate=0.35,
        total_tokens=None,
        prompt_tokens=None,
        completion_tokens=None,
        total_cost_usd=None,
        avg_latency_ms=245.5,
    )


@pytest.fixture
def sample_metrics() -> OverallMetrics:
    """Sample overall metrics from RD-06."""
    return OverallMetrics(
        n=100,
        tp=45,
        fp=10,
        fn=30,
        precision=0.8181818181818182,
        recall=0.6,
        f1=0.6923076923076923,
        coverage=0.55,
        abstention=0.05,
        invalid_schema=0.15,
        event_exact=0.5,
        per_field_accuracy={
            "sic_sector": {"accuracy": 0.85, "denominator": 80},
            "direction": {"accuracy": 0.9, "denominator": 80},
            "mechanism_keyword": {"accuracy": 0.75, "denominator": 80},
            "horizon_bucket": {"accuracy": 0.8, "denominator": 80},
        },
        macro_by_event_type={
            "earnings": {
                "n": 50,
                "precision": 0.75,
                "recall": 0.55,
                "f1": 0.6341463414634146,
            },
            "guidance": {
                "n": 30,
                "precision": 0.85,
                "recall": 0.65,
                "f1": 0.7368421052631579,
            },
        },
    )


@pytest.fixture
def sample_execution_with_tokens() -> ExecutionMetadata:
    """Sample execution metadata with known tokens/cost."""
    return ExecutionMetadata(
        cache_hit_rate=0.35,
        total_tokens=15000,
        prompt_tokens=12000,
        completion_tokens=3000,
        total_cost_usd=0.045,
        avg_latency_ms=245.5,
    )


class TestComputeInputSha256:
    """Tests for compute_input_sha256 function."""

    def test_sha256_deterministic_for_same_inputs(
        self,
        sample_provider,
        sample_execution,
        sample_metrics,
    ):
        """Same inputs must produce identical SHA-256 hash."""
        hash1 = compute_input_sha256(sample_provider, sample_execution, sample_metrics)
        hash2 = compute_input_sha256(sample_provider, sample_execution, sample_metrics)
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex length

    def test_sha256_changes_when_provider_changes(
        self,
        sample_provider,
        sample_execution,
        sample_metrics,
    ):
        """Different provider must produce different hash."""
        hash1 = compute_input_sha256(sample_provider, sample_execution, sample_metrics)

        different_provider = ProviderMetadata(
            provider="different",
            model="glm-4-flash",
            prompt_version="v1.0",
            schema_version="1.0.0",
        )
        hash2 = compute_input_sha256(different_provider, sample_execution, sample_metrics)

        assert hash1 != hash2

    def test_sha256_changes_when_metrics_change(
        self,
        sample_provider,
        sample_execution,
        sample_metrics,
    ):
        """Different metrics must produce different hash."""
        hash1 = compute_input_sha256(sample_provider, sample_execution, sample_metrics)

        different_metrics = OverallMetrics(
            n=99,  # Different n
            tp=44,
            fp=11,
            fn=29,
            precision=0.8,
            recall=0.6,
            f1=0.6875,
            coverage=0.55,
            abstention=0.05,
            invalid_schema=0.15,
            event_exact=0.5,
            per_field_accuracy=sample_metrics.per_field_accuracy,
            macro_by_event_type=sample_metrics.macro_by_event_type,
        )
        hash2 = compute_input_sha256(sample_provider, sample_execution, different_metrics)

        assert hash1 != hash2

    def test_sha256_stable_after_reordering_equivalent_inputs(
        self,
        sample_provider,
        sample_execution,
        sample_metrics,
    ):
        """Reordering equivalent inputs (e.g., dict keys) must not change hash."""
        # Create metrics with different key order in nested dicts
        metrics_reordered = OverallMetrics(
            n=sample_metrics.n,
            tp=sample_metrics.tp,
            fp=sample_metrics.fp,
            fn=sample_metrics.fn,
            precision=sample_metrics.precision,
            recall=sample_metrics.recall,
            f1=sample_metrics.f1,
            coverage=sample_metrics.coverage,
            abstention=sample_metrics.abstention,
            invalid_schema=sample_metrics.invalid_schema,
            event_exact=sample_metrics.event_exact,
            # Create dict with reverse key order
            per_field_accuracy=dict(reversed(list(sample_metrics.per_field_accuracy.items()))),
            macro_by_event_type=dict(reversed(list(sample_metrics.macro_by_event_type.items()))),
        )

        hash1 = compute_input_sha256(sample_provider, sample_execution, sample_metrics)
        hash2 = compute_input_sha256(sample_provider, sample_execution, metrics_reordered)

        assert hash1 == hash2, "Hash must be stable after reordering equivalent inputs"


class TestBuildReport:
    """Tests for build_report function."""

    def test_report_has_schema_version(
        self,
        sample_provider,
        sample_execution,
        sample_metrics,
    ):
        """Report must include schema_version field."""
        report = build_report(sample_provider, sample_execution, sample_metrics)
        assert report.schema_version == SCHEMA_VERSION

    def test_report_has_input_sha256(
        self,
        sample_provider,
        sample_execution,
        sample_metrics,
    ):
        """Report must include input_sha256 field."""
        report = build_report(sample_provider, sample_execution, sample_metrics)
        assert report.input_sha256 is not None
        assert len(report.input_sha256) == 64

    def test_report_omits_generated_at_when_none(
        self,
        sample_provider,
        sample_execution,
        sample_metrics,
    ):
        """Report must omit generated_at field when None."""
        report = build_report(sample_provider, sample_execution, sample_metrics, generated_at=None)
        assert report.generated_at is None

    def test_report_includes_generated_at_when_provided_as_string(
        self,
        sample_provider,
        sample_execution,
        sample_metrics,
    ):
        """Report must include generated_at when provided as string."""
        timestamp = "2026-08-01T12:34:56.789Z"
        report = build_report(
            sample_provider,
            sample_execution,
            sample_metrics,
            generated_at=timestamp,
        )
        assert report.generated_at == timestamp

    def test_report_converts_datetime_to_iso_string(
        self,
        sample_provider,
        sample_execution,
        sample_metrics,
    ):
        """Report must convert datetime to ISO string."""
        timestamp = datetime(2026, 8, 1, 12, 34, 56, 789000)
        report = build_report(
            sample_provider,
            sample_execution,
            sample_metrics,
            generated_at=timestamp,
        )
        assert report.generated_at == "2026-08-01T12:34:56.789000"

    def test_byte_stability_with_identical_generated_at(
        self,
        sample_provider,
        sample_execution,
        sample_metrics,
    ):
        """Two build_report calls with identical inputs produce byte-identical JSON."""
        timestamp = "2026-08-01T12:34:56.789Z"

        report1 = build_report(
            sample_provider,
            sample_execution,
            sample_metrics,
            generated_at=timestamp,
        )
        report2 = build_report(
            sample_provider,
            sample_execution,
            sample_metrics,
            generated_at=timestamp,
        )

        # Convert to dicts
        dict1 = {
            "schema_version": report1.schema_version,
            "generated_at": report1.generated_at,
            "input_sha256": report1.input_sha256,
            "provider": {
                "provider": report1.provider.provider,
                "model": report1.provider.model,
                "prompt_version": report1.provider.prompt_version,
                "schema_version": report1.provider.schema_version,
            },
            "execution": {
                "cache_hit_rate": report1.execution.cache_hit_rate,
                "total_tokens": report1.execution.total_tokens,
                "prompt_tokens": report1.execution.prompt_tokens,
                "completion_tokens": report1.execution.completion_tokens,
                "total_cost_usd": report1.execution.total_cost_usd,
                "avg_latency_ms": report1.execution.avg_latency_ms,
            },
        }
        dict2 = {
            "schema_version": report2.schema_version,
            "generated_at": report2.generated_at,
            "input_sha256": report2.input_sha256,
            "provider": {
                "provider": report2.provider.provider,
                "model": report2.provider.model,
                "prompt_version": report2.provider.prompt_version,
                "schema_version": report2.provider.schema_version,
            },
            "execution": {
                "cache_hit_rate": report2.execution.cache_hit_rate,
                "total_tokens": report2.execution.total_tokens,
                "prompt_tokens": report2.execution.prompt_tokens,
                "completion_tokens": report2.execution.completion_tokens,
                "total_cost_usd": report2.execution.total_cost_usd,
                "avg_latency_ms": report2.execution.avg_latency_ms,
            },
        }

        # Verify byte-identical JSON
        json1 = json.dumps(dict1, sort_keys=True, separators=(",", ":"))
        json2 = json.dumps(dict2, sort_keys=True, separators=(",", ":"))

        assert json1 == json2, "Identical inputs must produce byte-identical JSON"
        assert (
            report1.input_sha256 == report2.input_sha256
        ), "Identical inputs must produce identical SHA-256"

    def test_byte_stability_with_none_generated_at(
        self,
        sample_provider,
        sample_execution,
        sample_metrics,
    ):
        """Two build_report calls with generated_at=None must produce byte-identical JSON."""
        report1 = build_report(
            sample_provider,
            sample_execution,
            sample_metrics,
            generated_at=None,
        )
        report2 = build_report(
            sample_provider,
            sample_execution,
            sample_metrics,
            generated_at=None,
        )

        # Convert to dicts (both have generated_at=None)
        dict1 = {
            "schema_version": report1.schema_version,
            "generated_at": report1.generated_at,
            "input_sha256": report1.input_sha256,
        }
        dict2 = {
            "schema_version": report2.schema_version,
            "generated_at": report2.generated_at,
            "input_sha256": report2.input_sha256,
        }

        # Verify byte-identical JSON
        json1 = json.dumps(dict1, sort_keys=True, separators=(",", ":"))
        json2 = json.dumps(dict2, sort_keys=True, separators=(",", ":"))

        assert json1 == json2, "Identical inputs with None must produce byte-identical JSON"
        assert (
            report1.input_sha256 == report2.input_sha256
        ), "Identical inputs with None must produce identical SHA-256"

    def test_different_generated_at_produces_different_hash(
        self,
        sample_provider,
        sample_execution,
        sample_metrics,
    ):
        """Different generated_at values must produce different input_sha256."""
        report1 = build_report(
            sample_provider,
            sample_execution,
            sample_metrics,
            generated_at="2026-08-01T12:34:56.789Z",
        )
        report2 = build_report(
            sample_provider,
            sample_execution,
            sample_metrics,
            generated_at="2026-08-01T12:35:00.000Z",
        )

        assert (
            report1.input_sha256 != report2.input_sha256
        ), "Different generated_at must produce different SHA-256"

    def test_report_rejects_empty_evaluation_set(
        self,
        sample_provider,
        sample_execution,
    ):
        """Empty evaluation set (n=0) must raise ValueError."""
        empty_metrics = OverallMetrics(
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

        with pytest.raises(ValueError, match="empty evaluation set"):
            build_report(sample_provider, sample_execution, empty_metrics)

    def test_report_serializes_null_tokens_and_cost(
        self,
        sample_provider,
        sample_metrics,
    ):
        """Report must serialize null token/cost fields as JSON null."""
        execution = ExecutionMetadata(
            cache_hit_rate=0.35,
            total_tokens=None,
            prompt_tokens=None,
            completion_tokens=None,
            total_cost_usd=None,
            avg_latency_ms=None,
        )

        report = build_report(sample_provider, execution, sample_metrics)

        # Convert to dict and verify nulls
        report_dict = {
            "provider": {
                "provider": report.provider.provider,
                "model": report.provider.model,
                "prompt_version": report.provider.prompt_version,
                "schema_version": report.provider.schema_version,
            },
            "execution": {
                "cache_hit_rate": report.execution.cache_hit_rate,
                "total_tokens": report.execution.total_tokens,
                "prompt_tokens": report.execution.prompt_tokens,
                "completion_tokens": report.execution.completion_tokens,
                "total_cost_usd": report.execution.total_cost_usd,
                "avg_latency_ms": report.execution.avg_latency_ms,
            },
        }

        # Verify nulls are preserved
        assert report_dict["execution"]["total_tokens"] is None
        assert report_dict["execution"]["prompt_tokens"] is None
        assert report_dict["execution"]["completion_tokens"] is None
        assert report_dict["execution"]["total_cost_usd"] is None
        assert report_dict["execution"]["avg_latency_ms"] is None


class TestWriteReport:
    """Tests for write_report function."""

    def test_write_creates_file(
        self,
        sample_provider,
        sample_execution,
        sample_metrics,
        tmp_path,
    ):
        """Write must create the output file."""
        report = build_report(sample_provider, sample_execution, sample_metrics)
        output_path = tmp_path / "report.json"

        write_report(report, output_path)

        assert output_path.exists()
        assert output_path.is_file()

    def test_write_rejects_existing_file_by_default(
        self,
        sample_provider,
        sample_execution,
        sample_metrics,
        tmp_path,
    ):
        """Write must fail if target file exists (overwrite=False)."""
        report = build_report(sample_provider, sample_execution, sample_metrics)
        output_path = tmp_path / "report.json"

        # Create file first
        output_path.write_text("existing")

        with pytest.raises(FileExistsError, match="exists.*overwrite=False"):
            write_report(report, output_path, overwrite=False)

    def test_write_allows_overwrite_when_explicit(
        self,
        sample_provider,
        sample_execution,
        sample_metrics,
        tmp_path,
    ):
        """Write must succeed with overwrite=True."""
        report = build_report(sample_provider, sample_execution, sample_metrics)
        output_path = tmp_path / "report.json"

        # Create file first
        output_path.write_text("existing")

        # Should not raise
        write_report(report, output_path, overwrite=True)

        # Verify overwritten
        content = output_path.read_text()
        assert content != "existing"

    def test_write_creates_parent_directory(
        self,
        sample_provider,
        sample_execution,
        sample_metrics,
        tmp_path,
    ):
        """Write must create parent directories if needed."""
        report = build_report(sample_provider, sample_execution, sample_metrics)
        output_path = tmp_path / "subdir" / "nested" / "report.json"

        write_report(report, output_path)

        assert output_path.exists()
        assert output_path.is_file()

    def test_write_rejects_empty_path(
        self,
        sample_provider,
        sample_execution,
        sample_metrics,
    ):
        """Write must reject empty output path."""
        report = build_report(sample_provider, sample_execution, sample_metrics)

        with pytest.raises(ValueError, match="cannot be empty"):
            write_report(report, "")

    def test_write_creates_byte_stable_json(
        self,
        sample_provider,
        sample_execution,
        sample_metrics,
        tmp_path,
    ):
        """Same inputs must produce byte-identical JSON output."""
        report = build_report(sample_provider, sample_execution, sample_metrics)
        output_path1 = tmp_path / "report1.json"
        output_path2 = tmp_path / "report2.json"

        write_report(report, output_path1)
        write_report(report, output_path2)

        bytes1 = output_path1.read_bytes()
        bytes2 = output_path2.read_bytes()

        assert bytes1 == bytes2, "Same inputs must produce identical bytes"

    def test_write_produces_sorted_keys_json(
        self,
        sample_provider,
        sample_execution,
        sample_metrics,
        tmp_path,
    ):
        """JSON output must have sorted keys for byte-stability."""
        report = build_report(sample_provider, sample_execution, sample_metrics)
        output_path = tmp_path / "report.json"

        write_report(report, output_path)
        content = output_path.read_text()

        # Parse and re-dump with sorted keys to verify
        data = json.loads(content)
        sorted_dump = json.dumps(data, sort_keys=True, separators=(",", ":"))

        # Content should match sorted version
        assert content == sorted_dump

    def test_write_includes_schema_version_in_json(
        self,
        sample_provider,
        sample_execution,
        sample_metrics,
        tmp_path,
    ):
        """JSON output must include schema_version field."""
        report = build_report(sample_provider, sample_execution, sample_metrics)
        output_path = tmp_path / "report.json"

        write_report(report, output_path)
        content = output_path.read_text()

        data = json.loads(content)
        assert "schema_version" in data
        assert data["schema_version"] == SCHEMA_VERSION

    def test_write_includes_input_sha256_in_json(
        self,
        sample_provider,
        sample_execution,
        sample_metrics,
        tmp_path,
    ):
        """JSON output must include input_sha256 field."""
        report = build_report(sample_provider, sample_execution, sample_metrics)
        output_path = tmp_path / "report.json"

        write_report(report, output_path)
        content = output_path.read_text()

        data = json.loads(content)
        assert "input_sha256" in data
        assert len(data["input_sha256"]) == 64

    def test_atomic_write_no_partial_file_on_interruption(
        self,
        sample_provider,
        sample_execution,
        sample_metrics,
        tmp_path,
        monkeypatch,
    ):
        """Atomic write must not leave partial file if interrupted during replace."""
        report = build_report(sample_provider, sample_execution, sample_metrics)
        output_path = tmp_path / "report.json"

        # Mock os.replace to raise an error
        def mock_replace(src, dst):
            raise OSError("Simulated failure")

        monkeypatch.setattr("os.replace", mock_replace)

        with pytest.raises(OSError):
            write_report(report, output_path)

        # Verify temp file was cleaned up
        temp_files = list(tmp_path.glob("tmp*"))
        assert len(temp_files) == 0, "Temp file must be cleaned up after failed replace"

        # Verify target file not created
        assert not output_path.exists(), "Target file must not exist after failed write"

    def test_null_tokens_serialize_to_json_null(
        self,
        sample_provider,
        sample_metrics,
        tmp_path,
    ):
        """Null token/cost fields must serialize to JSON null."""
        execution = ExecutionMetadata(
            cache_hit_rate=0.35,
            total_tokens=None,
            prompt_tokens=None,
            completion_tokens=None,
            total_cost_usd=None,
            avg_latency_ms=None,
        )

        report = build_report(sample_provider, execution, sample_metrics)
        output_path = tmp_path / "report.json"

        write_report(report, output_path)
        content = output_path.read_text()

        # Verify nulls in JSON
        data = json.loads(content)
        assert data["execution"]["total_tokens"] is None
        assert data["execution"]["prompt_tokens"] is None
        assert data["execution"]["completion_tokens"] is None
        assert data["execution"]["total_cost_usd"] is None
        assert data["execution"]["avg_latency_ms"] is None

        # Verify literal "null" in JSON content
        assert '"total_tokens":null' in content
        assert '"prompt_tokens":null' in content
        assert '"completion_tokens":null' in content
        assert '"total_cost_usd":null' in content
        assert '"avg_latency_ms":null' in content

    def test_known_tokens_serialize_correctly(
        self,
        sample_provider,
        sample_metrics,
        sample_execution_with_tokens,
        tmp_path,
    ):
        """Known token/cost fields must serialize to numbers."""
        report = build_report(sample_provider, sample_execution_with_tokens, sample_metrics)
        output_path = tmp_path / "report.json"

        write_report(report, output_path)
        content = output_path.read_text()

        data = json.loads(content)
        assert data["execution"]["total_tokens"] == 15000
        assert data["execution"]["prompt_tokens"] == 12000
        assert data["execution"]["completion_tokens"] == 3000
        assert data["execution"]["total_cost_usd"] == 0.045
        assert data["execution"]["avg_latency_ms"] == 245.5
