"""
Gold-set 确定性分层采样 manifest 生成器（离线，不含真实文本）

Frozen semantics per TASK-RD-05:
- Input records: event_id, event_type, filed_ts, sic_sector, source_text_sha256
- Caller provides as_of_ts and quota_by_stratum[(event_type, year, sic_sector)]
- Reject: filed_ts > as_of_ts, missing filed_ts, non-64-hex source_text_sha256
- Deduplicate by (event_id, source_text_sha256); hash conflict → reject
- Within stratum: rank by sha256('0|' + event_id + '|' + source_text_sha256) ASC,
  tie-break event_id ASC
- Sparse strata: take all, record shortfall
- Unrequested strata: do not sample, record keys
- Manifest sorted by (event_type, year, sic_sector, selection_hash, event_id)
- manifest_id = sha256 of UTF-8 compact JSON lines (sorted keys, no spaces,
  one per line, single trailing \\n)
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class GoldSamplerRecord:
    """Input record for gold sampling."""
    event_id: str
    event_type: str
    filed_ts: datetime | None
    sic_sector: str
    source_text_sha256: str


@dataclass
class GoldManifestRow:
    """Single row in the output manifest."""
    event_id: str
    event_type: str
    year: int
    sic_sector: str
    filed_ts: str  # ISO format string
    source_text_sha256: str
    selection_hash: str


@dataclass
class GoldSampleResult:
    """Result of gold sampling."""
    manifest: list[GoldManifestRow]
    manifest_id: str
    shortfalls: dict[tuple[str, int, str], dict[str, int]]
    unrequested: list[tuple[str, int, str]]
    rejected: list[dict[str, Any]]


def _is_legal_sha256(hex_str: str) -> bool:
    """Check if string is exactly 64 hex characters (lowercase)."""
    return (
        isinstance(hex_str, str)
        and len(hex_str) == 64
        and all(c in "0123456789abcdef" for c in hex_str)
    )


def _compute_selection_hash(event_id: str, source_text_sha256: str) -> str:
    """
    Compute selection hash per frozen formula:
    sha256('0|' + event_id + '|' + source_text_sha256).
    """
    payload = f"0|{event_id}|{source_text_sha256}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _compute_manifest_id(manifest: list[GoldManifestRow]) -> str:
    """
    Compute manifest_id per frozen semantics:
    - UTF-8 encoding
    - Sorted keys compact JSON (separators no spaces)
    - One record per line
    - Single trailing newline
    """
    lines = []
    for row in manifest:
        row_dict = {
            "event_id": row.event_id,
            "event_type": row.event_type,
            "year": row.year,
            "sic_sector": row.sic_sector,
            "filed_ts": row.filed_ts,
            "source_text_sha256": row.source_text_sha256,
            "selection_hash": row.selection_hash,
        }
        compact_json = json.dumps(row_dict, separators=(",", ":"), sort_keys=True)
        lines.append(compact_json)
    payload = "\n".join(lines) + "\n"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def sample_gold_records(
    records: list[GoldSamplerRecord],
    as_of_ts: datetime,
    quota_by_stratum: dict[tuple[str, int, str], int],
) -> GoldSampleResult:
    """
    Sample gold records deterministically per frozen semantics.

    Args:
        records: Input records with event_id, event_type, filed_ts, sic_sector, source_text_sha256
        as_of_ts: Reject records with filed_ts > as_of_ts
        quota_by_stratum: Dict mapping (event_type, year, sic_sector) → quota

    Returns:
        GoldSampleResult with manifest, manifest_id, shortfalls, unrequested, rejected
    """
    rejected: list[dict[str, Any]] = []
    valid_records: list[GoldSamplerRecord] = []

    # Step 1: Validate and reject illegal records
    for rec in records:
        # Check for missing filed_ts
        if rec.filed_ts is None:
            rejected.append({
                "reason": "missing_filed_ts",
                "event_id": rec.event_id,
                "source_text_sha256": rec.source_text_sha256,
            })
            continue

        # Check for future filed_ts
        if rec.filed_ts > as_of_ts:
            rejected.append({
                "reason": "future_filed_ts",
                "event_id": rec.event_id,
                "filed_ts": rec.filed_ts.isoformat(),
                "as_of_ts": as_of_ts.isoformat(),
            })
            continue

        # Check for illegal source_text_sha256
        if not _is_legal_sha256(rec.source_text_sha256):
            rejected.append({
                "reason": "illegal_sha256",
                "event_id": rec.event_id,
                "source_text_sha256": rec.source_text_sha256,
            })
            continue

        valid_records.append(rec)

    # Step 2: Detect hash conflicts and event_id-hash conflicts
    hash_to_event_ids: dict[str, set[str]] = defaultdict(set)
    event_id_to_hash: dict[str, str] = {}
    conflicted_hashes: set[str] = set()

    # First pass: collect all (event_id, hash) pairs and detect conflicts
    for rec in valid_records:
        hash_to_event_ids[rec.source_text_sha256].add(rec.event_id)
        if rec.event_id in event_id_to_hash:
            # Same event_id with different hash - reject both hashes
            if event_id_to_hash[rec.event_id] != rec.source_text_sha256:
                rejected.append({
                    "reason": "event_id_hash_conflict",
                    "event_id": rec.event_id,
                    "previous_hash": event_id_to_hash[rec.event_id],
                    "new_hash": rec.source_text_sha256,
                })
                conflicted_hashes.add(event_id_to_hash[rec.event_id])
                conflicted_hashes.add(rec.source_text_sha256)
        else:
            event_id_to_hash[rec.event_id] = rec.source_text_sha256

    # Second pass: identify which hashes have multiple event_ids
    for hash_val, event_ids in hash_to_event_ids.items():
        if len(event_ids) > 1 and hash_val not in conflicted_hashes:
            conflicted_hashes.add(hash_val)
            rejected.append({
                "reason": "hash_conflict",
                "source_text_sha256": hash_val,
                "event_ids": sorted(event_ids),
            })

    # Third pass: build deduped_records, rejecting conflicts
    deduped_records: list[GoldSamplerRecord] = []
    seen_pairs: set[tuple[str, str]] = set()

    for rec in valid_records:
        pair = (rec.event_id, rec.source_text_sha256)

        # Skip if hash is conflicted
        if rec.source_text_sha256 in conflicted_hashes:
            continue

        # Skip if exact duplicate
        if pair in seen_pairs:
            continue

        seen_pairs.add(pair)
        deduped_records.append(rec)

    # Step 3: Group records by stratum
    stratum_records: dict[tuple[str, int, str], list[GoldSamplerRecord]] = defaultdict(list)
    for rec in deduped_records:
        year = rec.filed_ts.year if rec.filed_ts else 0
        stratum_key = (rec.event_type, year, rec.sic_sector)
        stratum_records[stratum_key].append(rec)

    # Step 4: Sample within each stratum
    manifest: list[GoldManifestRow] = []
    shortfalls: dict[tuple[str, int, str], dict[str, int]] = {}
    unrequested: list[tuple[str, int, str]] = []

    # Record shortfalls for requested strata even if no records
    for stratum_key, quota in quota_by_stratum.items():
        if stratum_key not in stratum_records:
            # No records at all for this requested stratum
            shortfalls[stratum_key] = {"requested": quota, "selected": 0}

    # Process all strata present in data
    for stratum_key, recs in sorted(stratum_records.items()):
        if stratum_key not in quota_by_stratum:
            unrequested.append(stratum_key)
            continue

        quota = quota_by_stratum[stratum_key]

        # Sort by selection_hash ASC, tie-break by event_id ASC
        sorted_recs = sorted(
            recs,
            key=lambda r: (
                _compute_selection_hash(r.event_id, r.source_text_sha256),
                r.event_id,
            ),
        )

        # Take first quota records
        selected = sorted_recs[:quota]

        # Record shortfall if sparse
        if len(selected) < quota:
            shortfalls[stratum_key] = {
                "requested": quota,
                "selected": len(selected),
            }

        # Build manifest rows
        for rec in selected:
            row = GoldManifestRow(
                event_id=rec.event_id,
                event_type=rec.event_type,
                year=rec.filed_ts.year if rec.filed_ts else 0,
                sic_sector=rec.sic_sector,
                filed_ts=rec.filed_ts.isoformat() if rec.filed_ts else "",
                source_text_sha256=rec.source_text_sha256,
                selection_hash=_compute_selection_hash(rec.event_id, rec.source_text_sha256),
            )
            manifest.append(row)

    # Step 5: Sort manifest by (event_type, year, sic_sector, selection_hash, event_id)
    manifest.sort(key=lambda r: (r.event_type, r.year, r.sic_sector, r.selection_hash, r.event_id))

    # Step 6: Compute manifest_id
    manifest_id = _compute_manifest_id(manifest)

    return GoldSampleResult(
        manifest=manifest,
        manifest_id=manifest_id,
        shortfalls=shortfalls,
        unrequested=unrequested,
        rejected=rejected,
    )
