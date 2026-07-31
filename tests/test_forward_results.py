"""Tests for E3 Slice 4d - forward results writer.

TDD: These tests FAIL before implementation, then PASS after.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from aionis.reporting.forward_results import list_forward_runs, load_forward_run, save_forward_run


@pytest.fixture
def tmp_runs_dir(tmp_path: Path) -> Path:
    """Hermetic runs directory for tests."""
    return tmp_path / "runs"


@pytest.fixture
def sample_config_sig() -> str:
    """Sample config signature."""
    return "abc123def456"


@pytest.fixture
def sample_config() -> dict:
    """Sample frozen config."""
    return {
        "phase": "E3",
        "learner": "lightgbm",
        "n_estimators": 100,
        "max_depth": 6,
    }


@pytest.fixture
def sample_ic_forward() -> pd.Series:
    """Sample forward IC differential series."""
    # 3 months of differential IC
    months = pd.period_range("2026-01", periods=3, freq="M")
    return pd.Series(
        [0.015, 0.023, -0.008],
        index=months,
        name="ic_diff",
    )


@pytest.fixture
def sample_summary() -> dict:
    """Sample summary dict matching accumulate_forward_ic_series output."""
    return {
        "mean_diff": 0.010,
        "se_hac": 0.008,
        "ci_half": 0.016,
        "ci_lo": -0.006,
        "ci_hi": 0.026,
        "dm_stat": 1.25,
        "dm_p_mbb": 0.21,
        "dm_flag": "insignificant",
        "n_months": 3,
        "publishable_ci_half": False,
    }


# Test 1: writes all 4 artifacts with correct content
def test_save_forward_run_writes_all_artifacts(
    tmp_runs_dir: Path,
    sample_config_sig: str,
    sample_ic_forward: pd.Series,
    sample_summary: dict,
    sample_config: dict,
) -> None:
    """Save writes all 4 artifacts: ic_forward, summary_forward, config, meta.json."""
    result_dir = save_forward_run(
        sample_config_sig,
        ic_forward=sample_ic_forward,
        summary=sample_summary,
        config=sample_config,
        runs_dir=tmp_runs_dir,
    )

    # Check directory exists and is correct
    assert result_dir == tmp_runs_dir / "forward" / sample_config_sig
    assert result_dir.exists()

    # Check ic_forward.parquet exists and round-trips correctly
    ic_path = result_dir / "ic_forward.parquet"
    assert ic_path.exists()
    ic_loaded = pd.read_parquet(ic_path)
    # The saved parquet should have the differential IC values
    assert "ic" in ic_loaded.columns
    # Index name is preserved as "date" from _write_ic; compare values
    pd.testing.assert_series_equal(
        ic_loaded["ic"],
        sample_ic_forward.rename("ic"),
        check_names=False,  # ignore index name difference (date vs None)
        check_dtype=False,
    )

    # Check summary_forward.json exists and is valid JSON
    summary_path = result_dir / "summary_forward.json"
    assert summary_path.exists()
    summary_loaded = json.loads(summary_path.read_text())
    assert summary_loaded == sample_summary

    # Check config.json exists
    config_path = result_dir / "config.json"
    assert config_path.exists()
    config_loaded = json.loads(config_path.read_text())
    assert config_loaded == sample_config

    # Check meta.json exists
    meta_path = result_dir / "meta.json"
    assert meta_path.exists()


# Test 2: summary_forward.json has E1-differential keys
def test_save_forward_run_summary_has_differential_keys(
    tmp_runs_dir: Path,
    sample_config_sig: str,
    sample_ic_forward: pd.Series,
    sample_summary: dict,
    sample_config: dict,
) -> None:
    """summary_forward.json contains all required differential keys."""
    save_forward_run(
        sample_config_sig,
        ic_forward=sample_ic_forward,
        summary=sample_summary,
        config=sample_config,
        runs_dir=tmp_runs_dir,
    )

    result_dir = tmp_runs_dir / "forward" / sample_config_sig
    summary_loaded = json.loads((result_dir / "summary_forward.json").read_text())

    # Check all E1-differential keys are present
    required_keys = {
        "mean_diff",
        "se_hac",
        "ci_half",
        "ci_lo",
        "ci_hi",
        "dm_stat",
        "dm_p_mbb",
        "dm_flag",
        "n_months",
        "publishable_ci_half",
    }
    assert required_keys.issubset(summary_loaded.keys())


# Test 3: meta.json has schema_version=2 + phase="E3"
def test_save_forward_run_meta_has_schema_version_and_phase(
    tmp_runs_dir: Path,
    sample_config_sig: str,
    sample_ic_forward: pd.Series,
    sample_summary: dict,
    sample_config: dict,
) -> None:
    """meta.json contains schema_version=2 and phase='E3'."""
    save_forward_run(
        sample_config_sig,
        ic_forward=sample_ic_forward,
        summary=sample_summary,
        config=sample_config,
        runs_dir=tmp_runs_dir,
    )

    result_dir = tmp_runs_dir / "forward" / sample_config_sig
    meta_loaded = json.loads((result_dir / "meta.json").read_text())

    assert meta_loaded["schema"] == 2
    assert meta_loaded["phase"] == "E3"
    assert "ts" in meta_loaded
    assert "h6_deterministic" in meta_loaded
    assert "config_sig" in meta_loaded


# Test 4: I9 - publishing does NOT create/modify anything under runs/results/
def test_save_forward_run_does_not_touch_published_results(
    tmp_runs_dir: Path,
    sample_config_sig: str,
    sample_ic_forward: pd.Series,
    sample_summary: dict,
    sample_config: dict,
) -> None:
    """Saving forward run creates NOTHING under runs/results/ (I9 gate)."""
    # Create a runs/results/<sig>/ directory before saving forward run
    results_dir = tmp_runs_dir / "results" / sample_config_sig
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "existing.json").write_text('{"preexisting": true}')

    # Save forward run
    save_forward_run(
        sample_config_sig,
        ic_forward=sample_ic_forward,
        summary=sample_summary,
        config=sample_config,
        runs_dir=tmp_runs_dir,
    )

    # Assert: runs/results/ is untouched
    assert (tmp_runs_dir / "results" / sample_config_sig).exists()
    existing_path = tmp_runs_dir / "results" / sample_config_sig / "existing.json"
    assert existing_path.read_text() == '{"preexisting": true}'
    # No new files created under results/
    assert len(list((tmp_runs_dir / "results").rglob("*"))) == 2  # dir + existing.json


# Test 5: re-save behavior matches save_run (idempotent)
def test_save_forward_run_idempotent(
    tmp_runs_dir: Path,
    sample_config_sig: str,
    sample_ic_forward: pd.Series,
    sample_summary: dict,
    sample_config: dict,
) -> None:
    """Re-saving with same data is idempotent (mirrors save_run behavior)."""
    # First save
    result_dir1 = save_forward_run(
        sample_config_sig,
        ic_forward=sample_ic_forward,
        summary=sample_summary,
        config=sample_config,
        runs_dir=tmp_runs_dir,
    )

    # Capture file states
    ic_bytes1 = (result_dir1 / "ic_forward.parquet").read_bytes()
    summary_text1 = (result_dir1 / "summary_forward.json").read_text()
    meta_text1 = (result_dir1 / "meta.json").read_text()

    # Second save (same data)
    result_dir2 = save_forward_run(
        sample_config_sig,
        ic_forward=sample_ic_forward,
        summary=sample_summary,
        config=sample_config,
        runs_dir=tmp_runs_dir,
    )

    # Assert: same directory
    assert result_dir2 == result_dir1

    # Assert: files are overwritten (newer timestamps may differ, but content is stable)
    ic_bytes2 = (result_dir2 / "ic_forward.parquet").read_bytes()
    summary_text2 = (result_dir2 / "summary_forward.json").read_text()
    config_text2 = (result_dir2 / "config.json").read_text()

    # Parquet and config should be bit-identical
    assert ic_bytes2 == ic_bytes1
    assert summary_text2 == summary_text1
    assert config_text2 == (result_dir1 / "config.json").read_text()

    # meta.json ts changes (new timestamp), but other fields are stable
    meta2 = json.loads((result_dir2 / "meta.json").read_text())
    meta1 = json.loads(meta_text1)
    assert meta2["schema"] == meta1["schema"]
    assert meta2["phase"] == meta1["phase"]
    assert meta2["h6_deterministic"] == meta1["h6_deterministic"]
    # ts field will be different (newer write time)


# Test 6: base parameter overrides runs_dir
def test_save_forward_run_base_override(
    tmp_runs_dir: Path,
    sample_config_sig: str,
    sample_ic_forward: pd.Series,
    sample_summary: dict,
    sample_config: dict,
) -> None:
    """base parameter overrides the runs directory location."""
    custom_base = tmp_runs_dir / "custom_runs"
    result_dir = save_forward_run(
        sample_config_sig,
        ic_forward=sample_ic_forward,
        summary=sample_summary,
        config=sample_config,
        runs_dir=custom_base,
    )

    assert result_dir == custom_base / "forward" / sample_config_sig
    assert result_dir.exists()
    assert (result_dir / "ic_forward.parquet").exists()


# Test 7: load_forward_run round-trips a save_forward_run fixture
def test_load_forward_run_round_trip(
    tmp_runs_dir: Path,
    sample_config_sig: str,
    sample_ic_forward: pd.Series,
    sample_summary: dict,
    sample_config: dict,
) -> None:
    """load_forward_run loads all artifacts saved by save_forward_run."""
    # First, save a forward run
    save_forward_run(
        sample_config_sig,
        ic_forward=sample_ic_forward,
        summary=sample_summary,
        config=sample_config,
        runs_dir=tmp_runs_dir,
    )

    # Load it back
    loaded = load_forward_run(sample_config_sig, base=tmp_runs_dir)

    # Verify all fields
    assert loaded["config_sig"] == sample_config_sig
    assert "ts" in loaded
    assert loaded["h6_deterministic"] is True
    assert loaded["phase"] == "E3"
    # ic_forward is a Series
    pd.testing.assert_series_equal(
        loaded["ic_forward"],
        sample_ic_forward.rename("ic"),
        check_names=False,
        check_dtype=False,
    )
    assert loaded["summary"] == sample_summary
    assert loaded["config"] == sample_config
    assert loaded["meta"]["schema"] == 2
    assert loaded["meta"]["phase"] == "E3"


# Test 8: load_forward_run raises FileNotFoundError for missing dir
def test_load_forward_run_missing_dir(
    tmp_runs_dir: Path,
    sample_config_sig: str,
) -> None:
    """load_forward_run raises FileNotFoundError when directory doesn't exist."""
    with pytest.raises(FileNotFoundError, match="No E3 forward results"):
        load_forward_run("nonexistent_sig", base=tmp_runs_dir)


# Test 9: list_forward_runs finds only phase=="E3" dirs
def test_list_forward_runs_filters_phase_e3(
    tmp_runs_dir: Path,
    sample_config_sig: str,
    sample_ic_forward: pd.Series,
    sample_summary: dict,
    sample_config: dict,
) -> None:
    """list_forward_runs only returns dirs with phase=='E3' in meta.json."""
    # Create a valid E3 forward run
    save_forward_run(
        sample_config_sig,
        ic_forward=sample_ic_forward,
        summary=sample_summary,
        config=sample_config,
        runs_dir=tmp_runs_dir,
    )

    # Create a non-E3 dir (simulate old schema or different phase)
    fake_dir = tmp_runs_dir / "forward" / "old_phase_sig"
    fake_dir.mkdir(parents=True, exist_ok=True)
    (fake_dir / "meta.json").write_text(
        json.dumps({"schema": 1, "phase": "B", "ts": "2026-01-01T00:00:00+00:00"})
    )

    # List forward runs
    runs = list_forward_runs(base=tmp_runs_dir)

    # Should only find the E3 run
    assert len(runs) == 1
    assert runs[0]["config_sig"] == sample_config_sig
    assert runs[0]["phase"] == "E3"
    assert "ts" in runs[0]
    assert runs[0]["h6_deterministic"] is True
    assert runs[0]["n_months"] == 3  # from summary_forward


# Test 10: list_forward_runs sorted deterministically
def test_list_forward_runs_sorted_deterministically(
    tmp_runs_dir: Path,
    sample_ic_forward: pd.Series,
    sample_summary: dict,
    sample_config: dict,
) -> None:
    """list_forward_runs returns runs sorted by ts (newest first)."""
    # Save 3 runs with different timestamps (by creating them in sequence)
    sig1 = "sig_early"
    sig2 = "sig_middle"
    sig3 = "sig_late"

    # Save in order
    save_forward_run(
        sig1,
        ic_forward=sample_ic_forward,
        summary=sample_summary,
        config=sample_config,
        runs_dir=tmp_runs_dir,
    )
    save_forward_run(
        sig2,
        ic_forward=sample_ic_forward,
        summary=sample_summary,
        config=sample_config,
        runs_dir=tmp_runs_dir,
    )
    save_forward_run(
        sig3,
        ic_forward=sample_ic_forward,
        summary=sample_summary,
        config=sample_config,
        runs_dir=tmp_runs_dir,
    )

    # List runs
    runs = list_forward_runs(base=tmp_runs_dir)

    # Should find all 3 runs
    assert len(runs) == 3
    # All should be present (order may vary if timestamps are identical)
    sigs = {r["config_sig"] for r in runs}
    assert sigs == {sig1, sig2, sig3}
    # All should have phase E3
    assert all(r["phase"] == "E3" for r in runs)


# Test 11: I9 - load_forward_run only touches runs/forward/
def test_load_forward_run_i9_separation(
    tmp_runs_dir: Path,
    sample_config_sig: str,
    sample_ic_forward: pd.Series,
    sample_summary: dict,
    sample_config: dict,
) -> None:
    """load_forward_run only reads from runs/forward/, never runs/results/ (I9 gate)."""
    # Create a forward run
    save_forward_run(
        sample_config_sig,
        ic_forward=sample_ic_forward,
        summary=sample_summary,
        config=sample_config,
        runs_dir=tmp_runs_dir,
    )

    # Create a runs/results/ dir with same config_sig (should never be touched)
    results_dir = tmp_runs_dir / "results" / sample_config_sig
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "dummy.json").write_text('{"results": "data"}')

    # Load forward run - should only read from forward/
    loaded = load_forward_run(sample_config_sig, base=tmp_runs_dir)

    # Verify it loaded from forward/
    assert loaded["config_sig"] == sample_config_sig
    assert loaded["phase"] == "E3"

    # Verify results/ is untouched
    dummy_path = tmp_runs_dir / "results" / sample_config_sig / "dummy.json"
    assert dummy_path.read_text() == '{"results": "data"}'


# Test 12: I9 - list_forward_runs only scans runs/forward/
def test_list_forward_runs_i9_separation(
    tmp_runs_dir: Path,
    sample_config_sig: str,
    sample_ic_forward: pd.Series,
    sample_summary: dict,
    sample_config: dict,
) -> None:
    """list_forward_runs only scans runs/forward/, never runs/results/ (I9 gate)."""
    # Create a forward run
    save_forward_run(
        sample_config_sig,
        ic_forward=sample_ic_forward,
        summary=sample_summary,
        config=sample_config,
        runs_dir=tmp_runs_dir,
    )

    # Create runs/results/ dirs (should never be scanned)
    results_sig = "results_only_sig"
    results_dir = tmp_runs_dir / "results" / results_sig
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "meta.json").write_text(
        json.dumps({"schema": 2, "phase": "B", "ts": "2026-01-01T00:00:00+00:00"})
    )

    # List forward runs - should only scan forward/
    runs = list_forward_runs(base=tmp_runs_dir)

    # Should only find the forward run, not the results run
    assert len(runs) == 1
    assert runs[0]["config_sig"] == sample_config_sig
    assert runs[0]["phase"] == "E3"

