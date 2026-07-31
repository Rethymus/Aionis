"""Tests for E3 Slice 4f - forward score invariants (consolidated gate).

TDD: These tests verify critical invariants I1, I2, I9, H6.
These should PASS based on implementations from 4d+4e.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from aionis.eval.forward_score import accumulate_forward_ic_series
from aionis.eval.forward_score_runner import main
from aionis.reporting.forward_ledger import (
    EVENT_SCORED,
    commit_forward_prediction,
    read_forward_rows,
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
def sample_config() -> dict:
    """Sample frozen config."""
    return {"phase": "E3", "learner": "lightgbm", "n_estimators": 100, "max_depth": 6}


@pytest.fixture
def config_sha256(sample_config: dict) -> str:
    """Compute config sha256 for the sample config."""
    import hashlib

    blob = json.dumps(sample_config, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()


# I1: reveal_and_score refuses when now < target_t
def test_i1_reveal_refuses_before_target(
    tmp_runs_dir: Path,
    tmp_prices_parquet: Path,
    sample_config: dict,
    config_sha256: str,
) -> None:
    """reveal_and_score_forward_month refuses when now < target_t (I1 gate)."""
    from aionis.eval.forward_score import reveal_and_score_forward_month

    # Commit a prediction
    predict_ts = "2026-01-31T20:00:00+00:00"
    target_t = "2026-02-28T20:00:00+00:00"
    scores = pd.DataFrame({
        "ticker": ["AAPL", "MSFT", "AAPL", "MSFT"],
        "arm": ["arm_base", "arm_base", "arm_e13", "arm_e13"],
        "score": [0.1, 0.15, 0.12, 0.17],
    })

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

    commit_row = {
        "predict_ts": predict_ts,
        "target_t": target_t,
        "config_sha256": config_sha256,
        "scores_path": commit_result["scores_path"],
    }

    # Attempt reveal with now < target_t (I1 gate should refuse)
    reveal_result = reveal_and_score_forward_month(
        commit_row,
        prices_path=tmp_prices_parquet,
        runs_dir=tmp_runs_dir,
        now="2026-02-01T00:00:00+00:00",  # Before target_t
    )

    # Both arms should be refused by I1 gate
    assert "arm_base" in reveal_result
    assert "arm_e13" in reveal_result
    assert reveal_result["arm_base"]["revealed"] is False
    assert reveal_result["arm_e13"]["revealed"] is False
    assert "before_target_t" in reveal_result["arm_base"]["reason"]
    assert "before_target_t" in reveal_result["arm_e13"]["reason"]

    # Verify NO forward_outcome_scored row was created
    scored_rows = read_forward_rows(
        runs_dir=tmp_runs_dir,
        config_sha256=config_sha256,
        event=EVENT_SCORED,
    )
    assert len(scored_rows) == 0


# I2: re-reveal is idempotent
def test_i2_reveal_idempotent(
    tmp_runs_dir: Path,
    tmp_prices_parquet: Path,
    sample_config: dict,
    config_sha256: str,
) -> None:
    """Re-reveal for the same (config_sha256, predict_ts, arm) is idempotent (I2)."""
    from aionis.eval.forward_score import reveal_and_score_forward_month

    # Commit and reveal
    predict_ts = "2026-01-31T20:00:00+00:00"
    target_t = "2026-02-28T20:00:00+00:00"
    scores = pd.DataFrame({
        "ticker": ["AAPL", "MSFT", "AAPL", "MSFT"],
        "arm": ["arm_base", "arm_base", "arm_e13", "arm_e13"],
        "score": [0.1, 0.15, 0.12, 0.17],
    })

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

    commit_row = {
        "predict_ts": predict_ts,
        "target_t": target_t,
        "config_sha256": config_sha256,
        "scores_path": commit_result["scores_path"],
    }

    # First reveal (after target_t)
    reveal_result1 = reveal_and_score_forward_month(
        commit_row,
        prices_path=tmp_prices_parquet,
        runs_dir=tmp_runs_dir,
        now=str(pd.Timestamp(target_t) + pd.Timedelta(days=1)),
    )

    assert reveal_result1["arm_base"]["revealed"] is True
    assert reveal_result1["arm_e13"]["revealed"] is True
    assert reveal_result1["arm_base"]["_appended"] is True
    assert reveal_result1["arm_e13"]["_appended"] is True

    # Second reveal (idempotent - should NOT append new rows)
    reveal_result2 = reveal_and_score_forward_month(
        commit_row,
        prices_path=tmp_prices_parquet,
        runs_dir=tmp_runs_dir,
        now=str(pd.Timestamp(target_t) + pd.Timedelta(days=2)),
    )

    assert reveal_result2["arm_base"]["revealed"] is True
    assert reveal_result2["arm_e13"]["revealed"] is True
    assert reveal_result2["arm_base"]["_appended"] is False  # No new append
    assert reveal_result2["arm_e13"]["_appended"] is False  # No new append

    # Verify exactly ONE forward_outcome_scored row per arm
    scored_rows = read_forward_rows(
        runs_dir=tmp_runs_dir,
        config_sha256=config_sha256,
        event=EVENT_SCORED,
    )
    assert len(scored_rows) == 2  # One per arm (arm_base, arm_e13)


# I9: forward artifacts live ONLY under runs/forward/
def test_i9_forward_artifacts_isolation(
    tmp_runs_dir: Path,
    tmp_prices_parquet: Path,
    sample_config: dict,
    config_sha256: str,
) -> None:
    """A full score→accumulate→save cycle writes ONLY under runs/forward/ (I9)."""
    from aionis.eval.forward_score import reveal_and_score_forward_month

    # Create a pre-existing published results dir
    results_dir = tmp_runs_dir / "results" / config_sha256
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "existing.json").write_text('{"preexisting": true}')

    # Commit and reveal for 3 months
    for i, (predict_ts, target_t) in enumerate([
        ("2026-01-31T20:00:00+00:00", "2026-02-28T20:00:00+00:00"),
        ("2026-02-28T20:00:00+00:00", "2026-03-31T20:00:00+00:00"),
        ("2026-03-31T20:00:00+00:00", "2026-04-30T20:00:00+00:00"),
    ]):
        scores = pd.DataFrame({
            "ticker": ["AAPL", "MSFT", "AAPL", "MSFT"],
            "arm": ["arm_base", "arm_base", "arm_e13", "arm_e13"],
            "score": [0.1 + i * 0.05, 0.15 + i * 0.05, 0.12 + i * 0.05, 0.17 + i * 0.05],
        })

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

        commit_row = {
            "predict_ts": predict_ts,
            "target_t": target_t,
            "config_sha256": config_sha256,
            "scores_path": commit_result["scores_path"],
        }

        reveal_and_score_forward_month(
            commit_row,
            prices_path=tmp_prices_parquet,
            runs_dir=tmp_runs_dir,
            now=str(pd.Timestamp(target_t) + pd.Timedelta(days=1)),
        )

    # Full score→accumulate→save cycle
    main(
        config_sig=config_sha256,
        runs_dir=tmp_runs_dir,
        prices_path=tmp_prices_parquet,
    )

    # Assert: runs/forward/ has the artifacts
    forward_dir = tmp_runs_dir / "forward" / config_sha256
    assert forward_dir.exists()
    assert (forward_dir / "ic_forward.parquet").exists()
    assert (forward_dir / "summary_forward.json").exists()

    # Assert: runs/results/ is UNTOUCHED
    assert (tmp_runs_dir / "results" / config_sha256).exists()
    existing_content = (tmp_runs_dir / "results" / config_sha256 / "existing.json").read_text()
    assert existing_content == '{"preexisting": true}'
    # No new files created under results/
    assert len(list((tmp_runs_dir / "results").rglob("*"))) == 2  # dir + existing.json


# H6: two accumulate passes produce bit-identical results
def test_h6_accumulate_determinism(
    tmp_runs_dir: Path,
    tmp_prices_parquet: Path,
    sample_config: dict,
    config_sha256: str,
) -> None:
    """Two accumulate passes over the same ledger → bit-identical ic_forward (H6)."""
    from aionis.eval.forward_score import reveal_and_score_forward_month

    # Commit and reveal for 3 months
    for i, (predict_ts, target_t) in enumerate([
        ("2026-01-31T20:00:00+00:00", "2026-02-28T20:00:00+00:00"),
        ("2026-02-28T20:00:00+00:00", "2026-03-31T20:00:00+00:00"),
        ("2026-03-31T20:00:00+00:00", "2026-04-30T20:00:00+00:00"),
    ]):
        scores = pd.DataFrame({
            "ticker": ["AAPL", "MSFT", "AAPL", "MSFT"],
            "arm": ["arm_base", "arm_base", "arm_e13", "arm_e13"],
            "score": [0.1 + i * 0.05, 0.15 + i * 0.05, 0.12 + i * 0.05, 0.17 + i * 0.05],
        })

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

        commit_row = {
            "predict_ts": predict_ts,
            "target_t": target_t,
            "config_sha256": config_sha256,
            "scores_path": commit_result["scores_path"],
        }

        reveal_and_score_forward_month(
            commit_row,
            prices_path=tmp_prices_parquet,
            runs_dir=tmp_runs_dir,
            now=str(pd.Timestamp(target_t) + pd.Timedelta(days=1)),
        )

    # First accumulate pass
    result1 = accumulate_forward_ic_series(
        config_sha256=config_sha256,
        runs_dir=tmp_runs_dir,
    )
    ic_forward_1 = result1["ic_forward"]
    summary_1 = result1["summary"]

    # Second accumulate pass (same ledger)
    result2 = accumulate_forward_ic_series(
        config_sha256=config_sha256,
        runs_dir=tmp_runs_dir,
    )
    ic_forward_2 = result2["ic_forward"]
    summary_2 = result2["summary"]

    # H6: bit-identical IC series (use equal_nan=True because test data may produce NaNs)
    assert np.array_equal(ic_forward_1.to_numpy(), ic_forward_2.to_numpy(), equal_nan=True)
    assert ic_forward_1.index.equals(ic_forward_2.index)

    # Identical summaries
    assert summary_1["mean_diff"] == summary_2["mean_diff"]
    assert summary_1["n_months"] == summary_2["n_months"]
    assert summary_1["publishable_ci_half"] == summary_2["publishable_ci_half"]
