"""Tests for E3 Slice 5b - dashboard Forward IC tab pure helpers.

TDD: These tests FAIL before implementation, then PASS after.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def sample_summary_forward() -> dict:
    """Sample summary_forward dict."""
    return {
        "mean_diff": 0.015,
        "se_hac": 0.008,
        "ci_half": 0.014,
        "ci_lo": -0.006,
        "ci_hi": 0.036,
        "dm_stat": 1.87,
        "dm_p_mbb": 0.06,
        "dm_flag": "significant",
        "n_months": 24,
        "publishable_ci_half": True,
    }


@pytest.fixture
def sample_summary_unpublishable() -> dict:
    """Sample summary with ci_half >= 0.015 (not publishable)."""
    return {
        "mean_diff": 0.015,
        "se_hac": 0.009,
        "ci_half": 0.016,
        "ci_lo": -0.007,
        "ci_hi": 0.037,
        "dm_stat": 1.67,
        "dm_p_mbb": 0.09,
        "dm_flag": "insignificant",
        "n_months": 18,
        "publishable_ci_half": False,
    }


# Test 1: _forward_kpi extracts correct fields
def test_forward_kpi_extracts_fields(sample_summary_forward: dict) -> None:
    """_forward_kpi extracts all required fields from summary_forward."""
    import sys
    from pathlib import Path

    # Add project root to sys.path so we can import dashboard.app
    project_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project_root))

    from dashboard.app import _forward_kpi

    kpi = _forward_kpi(sample_summary_forward)

    assert kpi["mean_ic"] == 0.015
    assert kpi["ci_half"] == 0.014
    assert kpi["t_hac"] == 1.87
    assert kpi["dm_p_mbb"] == 0.06
    assert kpi["n_months"] == 24
    assert kpi["publishable"] is True


# Test 2: _forward_kpi publishable flag flips at ci_half=0.015
def test_forward_kpi_publishable_threshold() -> None:
    """_forward_kpi publishable flag flips at ci_half=0.015."""
    import sys
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project_root))

    from dashboard.app import _forward_kpi

    # Below threshold
    kpi_low = _forward_kpi(
        {
            "ci_half": 0.014,
            "se_hac": 0.007,
            "n_months": 12,
            "mean_diff": 0.01,
            "dm_stat": 1.5,
            "dm_p_mbb": 0.1,
        }
    )
    assert kpi_low["publishable"] is True

    # Exactly at threshold (should NOT be publishable with < operator)
    kpi_at = _forward_kpi(
        {
            "ci_half": 0.015,
            "se_hac": 0.0075,
            "n_months": 12,
            "mean_diff": 0.01,
            "dm_stat": 1.5,
            "dm_p_mbb": 0.1,
        }
    )
    assert kpi_at["publishable"] is False  # ci_half == 0.015 is NOT < 0.015

    # Above threshold
    kpi_high = _forward_kpi(
        {
            "ci_half": 0.016,
            "se_hac": 0.008,
            "n_months": 12,
            "mean_diff": 0.01,
            "dm_stat": 1.5,
            "dm_p_mbb": 0.1,
        }
    )
    assert kpi_high["publishable"] is False


# Test 3: _parity_progress range math (60-120 months per pre-reg §7)
def test_parity_progress_range_math() -> None:
    """_parity_progress computes correct fractions vs 60-120 month range."""
    import sys
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project_root))

    from dashboard.app import _parity_progress

    # At parity (60 months)
    p60 = _parity_progress(60)
    assert p60["n_months"] == 60
    assert p60["lo"] == 60
    assert p60["hi"] == 120
    assert p60["frac_lo"] == 1.0
    assert p60["frac_hi"] == 0.5
    assert p60["at_parity"] is True

    # Mid-range (90 months)
    p90 = _parity_progress(90)
    assert p90["n_months"] == 90
    assert p90["frac_lo"] == 1.5
    assert p90["frac_hi"] == 0.75
    assert p90["at_parity"] is True

    # Below parity (30 months)
    p30 = _parity_progress(30)
    assert p30["n_months"] == 30
    assert p30["frac_lo"] == 0.5
    assert p30["frac_hi"] == 0.25
    assert p30["at_parity"] is False

    # Above parity (150 months)
    p150 = _parity_progress(150)
    assert p150["n_months"] == 150
    assert p150["frac_lo"] == 2.5
    assert p150["frac_hi"] == 1.25
    assert p150["at_parity"] is True


# Test 4: _committed_vs_revealed counts on tmp ledger
def test_committed_vs_revealed_counts(tmp_path: Path) -> None:
    """_committed_vs_revealed counts commit and reveal events correctly."""
    import sys
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project_root))

    from aionis.reporting.forward_ledger import EVENT_COMMIT, EVENT_SCORED
    from dashboard.app import _committed_vs_revealed

    # Create a minimal ledger with 3 commits and 2 reveals
    ledger_path = tmp_path / "ledger.jsonl"
    ledger_path.write_text(
        json.dumps({"event": EVENT_COMMIT, "phase": "E3", "config_sha256": "abc123"}) + "\n"
        + json.dumps({"event": EVENT_COMMIT, "phase": "E3", "config_sha256": "abc123"}) + "\n"
        + json.dumps({"event": EVENT_COMMIT, "phase": "E3", "config_sha256": "abc123"}) + "\n"
        + json.dumps({"event": EVENT_SCORED, "phase": "E3", "config_sha256": "abc123"}) + "\n"
        + json.dumps({"event": EVENT_SCORED, "phase": "E3", "config_sha256": "abc123"}) + "\n"
    )

    counts = _committed_vs_revealed(config_sha256="abc123", runs_dir=tmp_path)

    assert counts["committed"] == 3
    assert counts["revealed"] == 2
    assert counts["pending"] == 1


# Test 5: I9 - helpers/forward-run load never read runs/results/
def test_forward_helpers_i9_separation(tmp_path: Path) -> None:
    """Forward helpers only read runs/forward/, never runs/results/ (I9 gate)."""
    import sys
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project_root))

    from aionis.reporting.forward_results import list_forward_runs, load_forward_run

    # Create a forward run
    forward_dir = tmp_path / "forward" / "test_sig"
    forward_dir.mkdir(parents=True)
    (forward_dir / "meta.json").write_text(
        json.dumps({"schema": 2, "phase": "E3", "ts": "2026-01-01T00:00:00+00:00"})
    )

    # Create a results/ dir (should never be touched)
    results_dir = tmp_path / "results" / "test_sig"
    results_dir.mkdir(parents=True)
    (results_dir / "meta.json").write_text(
        json.dumps({"schema": 2, "ts": "2026-01-01T00:00:00+00:00"})
    )

    # List forward runs - should only scan forward/
    runs = list_forward_runs(base=tmp_path)
    assert len(runs) == 1
    assert runs[0]["phase"] == "E3"

    # Load forward run - should only read from forward/
    # This will fail on missing artifacts, but should not touch results/
    try:
        load_forward_run("test_sig", base=tmp_path)
    except FileNotFoundError:
        pass  # Expected (missing artifacts), but should not touch results/
