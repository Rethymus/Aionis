"""Tests for E3 Slice 4e - forward score runner.

TDD: These tests FAIL before implementation, then PASS after.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from aionis.eval.forward_score_runner import main
from aionis.reporting.forward_ledger import (
    commit_forward_prediction,
)


@pytest.fixture
def tmp_runs_dir(tmp_path: Path) -> Path:
    """Hermetic runs directory for tests."""
    return tmp_path / "runs"


@pytest.fixture
def tmp_prices_parquet(tmp_path: Path) -> Path:
    """Create a minimal prices parquet for testing."""
    prices = pd.DataFrame(
        {
            "AAPL": [150.0, 152.0, 149.0, 151.0],
            "MSFT": [300.0, 305.0, 298.0, 302.0],
        },
        index=pd.to_datetime([
            "2026-01-31 20:00:00",
            "2026-02-28 20:00:00",
            "2026-03-31 20:00:00",
            "2026-04-30 20:00:00",
        ]),
    )
    prices_path = tmp_path / "prices.parquet"
    prices.to_parquet(prices_path)
    return prices_path


@pytest.fixture
def sample_config(tmp_runs_dir: Path) -> dict:
    """Sample frozen config."""
    return {
        "phase": "E3",
        "learner": "lightgbm",
        "n_estimators": 100,
        "max_depth": 6,
    }


@pytest.fixture
def config_sha256(sample_config: dict) -> str:
    """Compute config sha256 for the sample config."""
    import hashlib

    blob = json.dumps(sample_config, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()


@pytest.fixture
def three_month_ledger(
    tmp_runs_dir: Path,
    tmp_prices_parquet: Path,
    sample_config: dict,
    config_sha256: str,
) -> str:
    """Create a ledger with 3 revealed months (forward_outcome_scored rows)."""
    from aionis.eval.forward_score import reveal_and_score_forward_month

    # Create 3 months of predictions with target_t that exist in prices
    for i, (predict_ts, target_t) in enumerate([
        ("2026-01-31T20:00:00+00:00", "2026-02-28T20:00:00+00:00"),
        ("2026-02-28T20:00:00+00:00", "2026-03-31T20:00:00+00:00"),
        ("2026-03-31T20:00:00+00:00", "2026-04-30T20:00:00+00:00"),
    ]):
        # Create scores for BOTH arms in a single DataFrame (forward ledger expects this shape)
        scores = pd.DataFrame({
            "ticker": ["AAPL", "MSFT", "AAPL", "MSFT"],
            "arm": ["arm_base", "arm_base", "arm_e13", "arm_e13"],
            "score": [0.1 + i * 0.05, 0.15 + i * 0.05, 0.12 + i * 0.05, 0.17 + i * 0.05],
        })

        # Commit the prediction (both arms together)
        commit_result = commit_forward_prediction(
            predict_ts=predict_ts,
            target_t=target_t,
            scores=scores,
            config=sample_config,
            iset_sha256="abc123",
            provider="glm",
            provider_cutoff="2026-01-01T00:00:00+00:00",
            runs_dir=tmp_runs_dir,
        )
        assert commit_result["committed"]

        # Reveal and score for both arms (use now=target_t to bypass I1 gate)
        # Build commit_row from the actual commit result
        commit_row = {
            "predict_ts": predict_ts,
            "target_t": target_t,
            "config_sha256": config_sha256,
            "scores_path": commit_result["scores_path"],  # Use the actual path from commit
        }

        # Mock the now parameter to be after target_t (add 1 day)
        target_dt = pd.Timestamp(target_t)
        now_dt = target_dt + pd.Timedelta(days=1)

        reveal_result = reveal_and_score_forward_month(
            commit_row,
            prices_path=tmp_prices_parquet,
            runs_dir=tmp_runs_dir,
            now=str(now_dt),
        )

        # Should have revealed both arms and they should be successful
        assert "arm_base" in reveal_result
        assert "arm_e13" in reveal_result
        assert reveal_result["arm_base"].get("revealed") is True
        assert reveal_result["arm_e13"].get("revealed") is True

    return config_sha256


# Test 1: end-to-end on tmp ledger with 3 revealed months
def test_forward_score_runner_end_to_end(
    tmp_runs_dir: Path,
    tmp_prices_parquet: Path,
    config_sha256: str,
    three_month_ledger: str,
    capsys: pytest.CaptureFixture,
) -> None:
    """Runner processes 3 revealed months and creates forward artifacts."""
    # Run the main function
    main(
        config_sig=config_sha256,
        runs_dir=tmp_runs_dir,
        prices_path=tmp_prices_parquet,
    )

    # Check stdout for structured [E3-score] lines
    captured = capsys.readouterr()
    assert "[E3-score]" in captured.out
    assert "config_sig" in captured.out
    assert "n_months" in captured.out

    # Check that forward artifacts were created
    forward_dir = tmp_runs_dir / "forward" / config_sha256
    assert forward_dir.exists()
    assert (forward_dir / "ic_forward.parquet").exists()
    assert (forward_dir / "summary_forward.json").exists()
    assert (forward_dir / "config.json").exists()
    assert (forward_dir / "meta.json").exists()

    # Check ic_forward has 3 months
    ic_forward = pd.read_parquet(forward_dir / "ic_forward.parquet")
    assert len(ic_forward) == 3


# Test 2: H6 - re-run on same ledger is bit-identical
def test_forward_score_runner_h6_determinism(
    tmp_runs_dir: Path,
    tmp_prices_parquet: Path,
    config_sha256: str,
    three_month_ledger: str,
) -> None:
    """Re-running on the same ledger produces bit-identical ic_forward.parquet."""
    # First run
    main(
        config_sig=config_sha256,
        runs_dir=tmp_runs_dir,
        prices_path=tmp_prices_parquet,
    )

    forward_dir = tmp_runs_dir / "forward" / config_sha256
    ic_bytes1 = (forward_dir / "ic_forward.parquet").read_bytes()
    summary_text1 = (forward_dir / "summary_forward.json").read_text()

    # Second run (same ledger)
    main(
        config_sig=config_sha256,
        runs_dir=tmp_runs_dir,
        prices_path=tmp_prices_parquet,
    )

    ic_bytes2 = (forward_dir / "ic_forward.parquet").read_bytes()
    summary_text2 = (forward_dir / "summary_forward.json").read_text()

    # H6: bit-identical parquet bytes
    assert ic_bytes2 == ic_bytes1

    # Summary should be identical (meta.json ts will differ)
    assert summary_text2 == summary_text1


# Test 3: real runs/ledger.jsonl and runs/results/ untouched
def test_forward_score_runner_does_not_touch_published_results(
    tmp_runs_dir: Path,
    tmp_prices_parquet: Path,
    config_sha256: str,
    three_month_ledger: str,
) -> None:
    """Runner creates NO files under runs/results/ (I9 gate)."""
    # Create a dummy published results dir
    results_dir = tmp_runs_dir / "results" / config_sha256
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "existing.json").write_text('{"preexisting": true}')

    # Run the runner
    main(
        config_sig=config_sha256,
        runs_dir=tmp_runs_dir,
        prices_path=tmp_prices_parquet,
    )

    # Assert: runs/results/ is untouched
    assert (tmp_runs_dir / "results" / config_sha256).exists()
    existing_content = (tmp_runs_dir / "results" / config_sha256 / "existing.json").read_text()
    assert existing_content == '{"preexisting": true}'
    # No new files created
    assert len(list((tmp_runs_dir / "results").rglob("*"))) == 2  # dir + existing.json


# Test 4: --force flag allows rewrite
def test_forward_score_runner_force_rewrite(
    tmp_runs_dir: Path,
    tmp_prices_parquet: Path,
    config_sha256: str,
    three_month_ledger: str,
) -> None:
    """--force flag allows rewriting existing forward artifacts."""
    # First run
    main(
        config_sig=config_sha256,
        runs_dir=tmp_runs_dir,
        prices_path=tmp_prices_parquet,
    )

    forward_dir = tmp_runs_dir / "forward" / config_sha256
    meta_text1 = (forward_dir / "meta.json").read_text()

    # Second run with --force (should succeed and rewrite)
    main(
        config_sig=config_sha256,
        runs_dir=tmp_runs_dir,
        prices_path=tmp_prices_parquet,
        force=True,
    )

    meta_text2 = (forward_dir / "meta.json").read_text()

    # meta.json should be rewritten (same or newer timestamp)
    meta1 = json.loads(meta_text1)
    meta2 = json.loads(meta_text2)
    # Note: if both writes happen within the same second, timestamps may be identical
    # The important thing is that the rewrite succeeded and other fields are stable
    assert meta2["schema"] == meta1["schema"]
    assert meta2["phase"] == meta1["phase"]
    assert meta2["config_sig"] == meta1["config_sig"]
    assert meta2["h6_deterministic"] == meta1["h6_deterministic"]
