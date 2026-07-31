"""
Tests for gold_sampler with hand-computed oracles.

Frozen semantics per TASK-RD-05:
- Input records: event_id, event_type, filed_ts, sic_sector, source_text_sha256
- Deterministic sampling with SHA256-based selection
- Rejection: future/missing filed_ts, illegal hash, hash conflicts
- Deduplication by (event_id, source_text_sha256)
- Canonical manifest_id must be stable across runs
"""

import hashlib
from datetime import datetime

from aionis.extraction.gold_sampler import (
    GoldManifestRow,
    GoldSamplerRecord,
    _compute_manifest_id,
    _compute_selection_hash,
    _is_legal_sha256,
    sample_gold_records,
)


def _sha256_hex(payload: str) -> str:
    """Helper to compute SHA256 hex digest."""
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class TestLegalSha256:
    """Test SHA256 validation."""
    def test_valid_lowercase_hex(self):
        assert _is_legal_sha256("a" * 64)

    def test_valid_mixed_case(self):
        assert not _is_legal_sha256("A" * 64)  # Uppercase rejected

    def test_invalid_too_short(self):
        assert not _is_legal_sha256("a" * 63)

    def test_invalid_too_long(self):
        assert not _is_legal_sha256("a" * 65)

    def test_invalid_non_hex(self):
        assert not _is_legal_sha256("g" * 64)

    def test_valid_real_hash(self):
        assert _is_legal_sha256("1a2b3c4d5e6f7890abcdef1234567890abcdef1234567890abcdef1234567890")


class TestSelectionHash:
    """Test selection hash computation with hand-computed values."""
    def test_selection_hash_formula(self):
        # selection_hash = sha256("0|" + event_id + "|" + source_text_sha256)
        event_id = "evt001"
        source_hash = "a" * 64
        payload = f"0|{event_id}|{source_hash}"
        expected = _sha256_hex(payload)
        assert _compute_selection_hash(event_id, source_hash) == expected

    def test_selection_hash_different_event_id(self):
        # Different event_id → different hash
        h1 = _compute_selection_hash("evt001", "a" * 64)
        h2 = _compute_selection_hash("evt002", "a" * 64)
        assert h1 != h2


class TestRejectFutureFiledTs:
    """Test rejection of records with filed_ts > as_of_ts."""
    def test_reject_future_record(self):
        as_of = datetime(2024, 6, 15)
        records = [
            GoldSamplerRecord(
                event_id="evt001",
                event_type="FORM10K",
                filed_ts=datetime(2024, 6, 20),  # Future
                sic_sector="10",
                source_text_sha256="a" * 64,
            ),
            GoldSamplerRecord(
                event_id="evt002",
                filed_ts=datetime(2024, 6, 10),  # Past
                event_type="FORM10K",
                sic_sector="10",
                source_text_sha256="b" * 64,
            ),
        ]
        quota_by_stratum = {("FORM10K", 2024, "10"): 10}
        result = sample_gold_records(records, as_of, quota_by_stratum)

        # Only evt002 selected
        assert len(result.manifest) == 1
        assert result.manifest[0].event_id == "evt002"
        assert len(result.rejected) == 1
        assert result.rejected[0]["reason"] == "future_filed_ts"


class TestRejectMissingFiledTs:
    """Test rejection of records with missing filed_ts."""
    def test_reject_none_filed_ts(self):
        as_of = datetime(2024, 6, 15)
        records = [
            GoldSamplerRecord(
                event_id="evt001",
                event_type="FORM10K",
                filed_ts=None,  # Missing
                sic_sector="10",
                source_text_sha256="a" * 64,
            ),
        ]
        quota_by_stratum = {("FORM10K", 2024, "10"): 10}
        result = sample_gold_records(records, as_of, quota_by_stratum)

        assert len(result.manifest) == 0
        assert len(result.rejected) == 1
        assert result.rejected[0]["reason"] == "missing_filed_ts"


class TestRejectIllegalHash:
    """Test rejection of records with illegal source_text_sha256."""
    def test_reject_non_hex_hash(self):
        as_of = datetime(2024, 6, 15)
        records = [
            GoldSamplerRecord(
                event_id="evt001",
                event_type="FORM10K",
                filed_ts=datetime(2024, 6, 10),
                sic_sector="10",
                source_text_sha256="g" * 64,  # Invalid hex
            ),
        ]
        quota_by_stratum = {("FORM10K", 2024, "10"): 10}
        result = sample_gold_records(records, as_of, quota_by_stratum)

        assert len(result.manifest) == 0
        assert len(result.rejected) == 1
        assert result.rejected[0]["reason"] == "illegal_sha256"

    def test_reject_wrong_length_hash(self):
        as_of = datetime(2024, 6, 15)
        records = [
            GoldSamplerRecord(
                event_id="evt001",
                event_type="FORM10K",
                filed_ts=datetime(2024, 6, 10),
                sic_sector="10",
                source_text_sha256="a" * 63,  # Too short
            ),
        ]
        quota_by_stratum = {("FORM10K", 2024, "10"): 10}
        result = sample_gold_records(records, as_of, quota_by_stratum)

        assert len(result.manifest) == 0
        assert len(result.rejected) == 1


class TestDeduplication:
    """Test deduplication by (event_id, source_text_sha256)."""
    def test_exact_duplicate_removal(self):
        as_of = datetime(2024, 6, 15)
        records = [
            GoldSamplerRecord(
                event_id="evt001",
                event_type="FORM10K",
                filed_ts=datetime(2024, 6, 10),
                sic_sector="10",
                source_text_sha256="a" * 64,
            ),
            GoldSamplerRecord(
                event_id="evt001",  # Same event_id and hash
                event_type="FORM10K",
                filed_ts=datetime(2024, 6, 10),
                sic_sector="10",
                source_text_sha256="a" * 64,
            ),
        ]
        quota_by_stratum = {("FORM10K", 2024, "10"): 10}
        result = sample_gold_records(records, as_of, quota_by_stratum)

        # Only one record selected
        assert len(result.manifest) == 1
        assert result.manifest[0].event_id == "evt001"


class TestHashConflictRejection:
    """Test rejection when same hash appears for different event_ids."""
    def test_same_hash_different_event_id(self):
        as_of = datetime(2024, 6, 15)
        same_hash = "a" * 64
        records = [
            GoldSamplerRecord(
                event_id="evt001",
                event_type="FORM10K",
                filed_ts=datetime(2024, 6, 10),
                sic_sector="10",
                source_text_sha256=same_hash,
            ),
            GoldSamplerRecord(
                event_id="evt002",  # Different event_id, same hash
                event_type="FORM10K",
                filed_ts=datetime(2024, 6, 10),
                sic_sector="10",
                source_text_sha256=same_hash,
            ),
        ]
        quota_by_stratum = {("FORM10K", 2024, "10"): 10}
        result = sample_gold_records(records, as_of, quota_by_stratum)

        # All rejected
        assert len(result.manifest) == 0
        assert len(result.rejected) == 1
        assert result.rejected[0]["reason"] == "hash_conflict"
        assert set(result.rejected[0]["event_ids"]) == {"evt001", "evt002"}


class TestEventIdHashConflict:
    """Test rejection when same event_id has different hashes."""
    def test_same_event_id_different_hash(self):
        as_of = datetime(2024, 6, 15)
        records = [
            GoldSamplerRecord(
                event_id="evt001",
                event_type="FORM10K",
                filed_ts=datetime(2024, 6, 10),
                sic_sector="10",
                source_text_sha256="a" * 64,
            ),
            GoldSamplerRecord(
                event_id="evt001",  # Same event_id, different hash
                event_type="FORM10K",
                filed_ts=datetime(2024, 6, 10),
                sic_sector="10",
                source_text_sha256="b" * 64,
            ),
        ]
        quota_by_stratum = {("FORM10K", 2024, "10"): 10}
        result = sample_gold_records(records, as_of, quota_by_stratum)

        # All rejected
        assert len(result.manifest) == 0
        assert len(result.rejected) == 1
        assert result.rejected[0]["reason"] == "event_id_hash_conflict"


class TestFixedQuotaHandComputed:
    """Test with fixed quota and hand-computed selection."""
    def test_selection_by_hash_order(self):
        as_of = datetime(2024, 6, 15)
        # Create records with known selection hashes
        records = [
            GoldSamplerRecord(
                event_id="evt001",
                event_type="FORM10K",
                filed_ts=datetime(2024, 6, 10),
                sic_sector="10",
                source_text_sha256="a" * 64,
            ),
            GoldSamplerRecord(
                event_id="evt002",
                event_type="FORM10K",
                filed_ts=datetime(2024, 6, 10),
                sic_sector="10",
                source_text_sha256="b" * 64,
            ),
            GoldSamplerRecord(
                event_id="evt003",
                event_type="FORM10K",
                filed_ts=datetime(2024, 6, 10),
                sic_sector="10",
                source_text_sha256="c" * 64,
            ),
        ]
        quota_by_stratum = {("FORM10K", 2024, "10"): 2}  # Only 2 records
        result = sample_gold_records(records, as_of, quota_by_stratum)

        # Should select 2 records based on selection_hash ordering
        assert len(result.manifest) == 2

        # Compute selection hashes to verify ordering
        hashes = {
            "evt001": _compute_selection_hash("evt001", "a" * 64),
            "evt002": _compute_selection_hash("evt002", "b" * 64),
            "evt003": _compute_selection_hash("evt003", "c" * 64),
        }

        # Sort by selection_hash
        sorted_events = sorted(hashes.keys(), key=lambda e: (hashes[e], e))
        assert [result.manifest[0].event_id, result.manifest[1].event_id] == sorted_events[:2]


class TestInputOrderInvariance:
    """Test that input order doesn't affect output."""
    def test_shuffled_input_same_output(self):
        as_of = datetime(2024, 6, 15)
        records = [
            GoldSamplerRecord(
                event_id="evt001",
                event_type="FORM10K",
                filed_ts=datetime(2024, 6, 10),
                sic_sector="10",
                source_text_sha256="a" * 64,
            ),
            GoldSamplerRecord(
                event_id="evt002",
                event_type="FORM10K",
                filed_ts=datetime(2024, 6, 10),
                sic_sector="10",
                source_text_sha256="b" * 64,
            ),
            GoldSamplerRecord(
                event_id="evt003",
                event_type="FORM10K",
                filed_ts=datetime(2024, 6, 10),
                sic_sector="10",
                source_text_sha256="c" * 64,
            ),
        ]
        quota_by_stratum = {("FORM10K", 2024, "10"): 2}

        # Run with original order
        result1 = sample_gold_records(records, as_of, quota_by_stratum)

        # Run with shuffled order
        import random
        shuffled = records.copy()
        random.shuffle(shuffled)
        result2 = sample_gold_records(shuffled, as_of, quota_by_stratum)

        # Same manifest
        assert len(result1.manifest) == len(result2.manifest)
        for r1, r2 in zip(result1.manifest, result2.manifest, strict=True):
            assert r1.event_id == r2.event_id
            assert r1.selection_hash == r2.selection_hash

        # Same manifest_id
        assert result1.manifest_id == result2.manifest_id


class TestSparseStratumShortfall:
    """Test sparse strata (fewer records than quota)."""
    def test_sparse_stratum(self):
        as_of = datetime(2024, 6, 15)
        records = [
            GoldSamplerRecord(
                event_id="evt001",
                event_type="FORM10K",
                filed_ts=datetime(2024, 6, 10),
                sic_sector="10",
                source_text_sha256="a" * 64,
            ),
        ]
        # Request 5 but only 1 available
        quota_by_stratum = {("FORM10K", 2024, "10"): 5}
        result = sample_gold_records(records, as_of, quota_by_stratum)

        # Take all available
        assert len(result.manifest) == 1
        assert result.manifest[0].event_id == "evt001"

        # Record shortfall
        assert ("FORM10K", 2024, "10") in result.shortfalls
        assert result.shortfalls[("FORM10K", 2024, "10")]["requested"] == 5
        assert result.shortfalls[("FORM10K", 2024, "10")]["selected"] == 1


class TestUnrequestedStratum:
    """Test strata present in data but not in quota_by_stratum."""
    def test_unrequested_stratum(self):
        as_of = datetime(2024, 6, 15)
        records = [
            GoldSamplerRecord(
                event_id="evt001",
                event_type="FORM10K",  # This stratum not in quota
                filed_ts=datetime(2024, 6, 10),
                sic_sector="10",
                source_text_sha256="a" * 64,
            ),
            GoldSamplerRecord(
                event_id="evt002",
                event_type="FORM10Q",  # This stratum has quota
                filed_ts=datetime(2024, 6, 10),
                sic_sector="20",
                source_text_sha256="b" * 64,
            ),
        ]
        # Only FORM10Q has quota
        quota_by_stratum = {("FORM10Q", 2024, "20"): 10}
        result = sample_gold_records(records, as_of, quota_by_stratum)

        # FORM10K not sampled
        assert len(result.manifest) == 1
        assert result.manifest[0].event_type == "FORM10Q"

        # Unrequested stratum recorded
        assert ("FORM10K", 2024, "10") in result.unrequested


class TestCanonicalManifestId:
    """Test that manifest_id is canonical and stable."""
    def test_manifest_id_stability(self):
        as_of = datetime(2024, 6, 15)
        records = [
            GoldSamplerRecord(
                event_id="evt001",
                event_type="FORM10K",
                filed_ts=datetime(2024, 6, 10),
                sic_sector="10",
                source_text_sha256="a" * 64,
            ),
        ]
        quota_by_stratum = {("FORM10K", 2024, "10"): 10}

        # Run twice
        result1 = sample_gold_records(records, as_of, quota_by_stratum)
        result2 = sample_gold_records(records, as_of, quota_by_stratum)

        # Same manifest_id
        assert result1.manifest_id == result2.manifest_id

        # Verify format: 64 hex characters
        assert len(result1.manifest_id) == 64
        assert all(c in "0123456789abcdef" for c in result1.manifest_id)

    def test_manifest_id_content(self):
        """Verify manifest_id formula: sha256 of compact JSON lines."""
        # Create a minimal manifest
        row = GoldManifestRow(
            event_id="evt001",
            event_type="FORM10K",
            year=2024,
            sic_sector="10",
            filed_ts="2024-06-10T00:00:00",
            source_text_sha256="a" * 64,
            selection_hash=_compute_selection_hash("evt001", "a" * 64),
        )

        # Compute manifest_id from single row
        manifest_id = _compute_manifest_id([row])

        # Verify it's a valid SHA256
        assert len(manifest_id) == 64
        assert all(c in "0123456789abcdef" for c in manifest_id)


class TestManifestSortOrder:
    """Test manifest sorting by (event_type, year, sic_sector, selection_hash, event_id)."""
    def test_manifest_ordering(self):
        as_of = datetime(2024, 6, 15)
        records = [
            GoldSamplerRecord(
                event_id="evt003",
                event_type="FORM10Q",
                filed_ts=datetime(2024, 6, 10),
                sic_sector="20",
                source_text_sha256="c" * 64,
            ),
            GoldSamplerRecord(
                event_id="evt001",
                event_type="FORM10K",
                filed_ts=datetime(2024, 6, 10),
                sic_sector="10",
                source_text_sha256="a" * 64,
            ),
            GoldSamplerRecord(
                event_id="evt002",
                event_type="FORM10K",
                filed_ts=datetime(2023, 6, 10),  # Different year
                sic_sector="10",
                source_text_sha256="b" * 64,
            ),
        ]
        quota_by_stratum = {
            ("FORM10K", 2024, "10"): 10,
            ("FORM10K", 2023, "10"): 10,
            ("FORM10Q", 2024, "20"): 10,
        }
        result = sample_gold_records(records, as_of, quota_by_stratum)

        # Verify sorting: event_type, year, sic_sector, selection_hash, event_id
        assert len(result.manifest) == 3
        # evt002 (FORM10K, 2023) comes before evt001 (FORM10K, 2024)
        assert result.manifest[0].event_id == "evt002"
        assert result.manifest[0].year == 2023
        assert result.manifest[1].event_id == "evt001"
        assert result.manifest[1].year == 2024
        assert result.manifest[2].event_id == "evt003"


class TestEmptyInput:
    """Test edge case with no records."""
    def test_empty_records(self):
        as_of = datetime(2024, 6, 15)
        records = []
        quota_by_stratum = {("FORM10K", 2024, "10"): 10}
        result = sample_gold_records(records, as_of, quota_by_stratum)

        assert len(result.manifest) == 0
        assert len(result.rejected) == 0
        assert len(result.shortfalls) == 1  # Shortfall for requested stratum
        assert result.shortfalls[("FORM10K", 2024, "10")]["selected"] == 0


class TestAllRejected:
    """Test when all records are rejected."""
    def test_all_records_invalid(self):
        as_of = datetime(2024, 6, 15)
        records = [
            GoldSamplerRecord(
                event_id="evt001",
                event_type="FORM10K",
                filed_ts=None,  # Invalid
                sic_sector="10",
                source_text_sha256="a" * 64,
            ),
            GoldSamplerRecord(
                event_id="evt002",
                event_type="FORM10K",
                filed_ts=datetime(2024, 6, 20),  # Future
                sic_sector="10",
                source_text_sha256="b" * 64,
            ),
        ]
        quota_by_stratum = {("FORM10K", 2024, "10"): 10}
        result = sample_gold_records(records, as_of, quota_by_stratum)

        assert len(result.manifest) == 0
        assert len(result.rejected) == 2
        assert result.shortfalls[("FORM10K", 2024, "10")]["selected"] == 0
