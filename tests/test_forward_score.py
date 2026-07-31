"""Tests for E3 Slice 4a - realized forward return fetcher.

TDD: failing tests FIRST, then implementation.
"""
from __future__ import annotations

import pandas as pd
import pytest


def test_fetch_realized_forward_returns_three_tickers(tmp_path):
    """Correct y_fwd_ret for 3 tickers with known prices."""
    # Create a wide price parquet (index=sessions, columns=tickers)
    prices = pd.DataFrame(
        {
            "AAPL": {pd.Timestamp("2026-07-01"): 150.0, pd.Timestamp("2026-07-22"): 153.0},
            "MSFT": {pd.Timestamp("2026-07-01"): 300.0, pd.Timestamp("2026-07-22"): 306.0},
            "GOOGL": {pd.Timestamp("2026-07-01"): 120.0, pd.Timestamp("2026-07-22"): 117.6},
        }
    )
    prices.index.name = "date"
    prices_path = tmp_path / "prices.parquet"
    prices.to_parquet(prices_path)

    from aionis.eval.forward_score import fetch_realized_forward_returns

    result = fetch_realized_forward_returns(
        predict_ts="2026-07-01",
        target_t="2026-07-22",
        tickers=["AAPL", "MSFT", "GOOGL"],
        prices_path=prices_path,
    )

    # Expected: (153/150 - 1) = 0.02, (306/300 - 1) = 0.02, (117.6/120 - 1) = -0.02
    assert len(result) == 3
    assert result.columns.tolist() == ["ticker", "y_fwd_ret"]
    result_dict = dict(zip(result["ticker"], result["y_fwd_ret"], strict=True))
    assert result_dict["AAPL"] == pytest.approx(0.02, abs=1e-6)
    assert result_dict["MSFT"] == pytest.approx(0.02, abs=1e-6)
    assert result_dict["GOOGL"] == pytest.approx(-0.02, abs=1e-6)


def test_fetch_realized_forward_returns_missing_ticker_at_target(tmp_path):
    """Missing ticker at target_t → excluded, no exception."""
    prices = pd.DataFrame(
        {
            "AAPL": {pd.Timestamp("2026-07-01"): 150.0, pd.Timestamp("2026-07-22"): 153.0},
            "MSFT": {pd.Timestamp("2026-07-01"): 300.0, pd.Timestamp("2026-07-22"): pd.NA},
            "GOOGL": {pd.Timestamp("2026-07-01"): 120.0, pd.Timestamp("2026-07-22"): 117.6},
        }
    )
    prices.index.name = "date"
    prices_path = tmp_path / "prices.parquet"
    prices.to_parquet(prices_path)

    from aionis.eval.forward_score import fetch_realized_forward_returns

    result = fetch_realized_forward_returns(
        predict_ts="2026-07-01",
        target_t="2026-07-22",
        tickers=["AAPL", "MSFT", "GOOGL"],
        prices_path=prices_path,
    )

    # MSFT excluded because missing at target_t
    assert len(result) == 2
    assert set(result["ticker"]) == {"AAPL", "GOOGL"}


def test_fetch_realized_forward_returns_empty_data(tmp_path):
    """Empty/missing data → empty frame, no crash."""
    # Create empty price parquet
    prices = pd.DataFrame({"date": []}).set_index("date")
    prices_path = tmp_path / "prices.parquet"
    prices.to_parquet(prices_path)

    from aionis.eval.forward_score import fetch_realized_forward_returns

    result = fetch_realized_forward_returns(
        predict_ts="2026-07-01",
        target_t="2026-07-22",
        tickers=["AAPL", "MSFT"],
        prices_path=prices_path,
    )

    assert len(result) == 0
    assert result.columns.tolist() == ["ticker", "y_fwd_ret"]


def test_fetch_realized_forward_returns_missing_at_predict_ts(tmp_path):
    """Missing ticker at predict_ts → excluded (symmetric to missing at target)."""
    prices = pd.DataFrame(
        {
            "AAPL": {pd.Timestamp("2026-07-01"): 150.0, pd.Timestamp("2026-07-22"): 153.0},
            "MSFT": {pd.Timestamp("2026-07-01"): pd.NA, pd.Timestamp("2026-07-22"): 306.0},
            "GOOGL": {pd.Timestamp("2026-07-01"): 120.0, pd.Timestamp("2026-07-22"): 117.6},
        }
    )
    prices.index.name = "date"
    prices_path = tmp_path / "prices.parquet"
    prices.to_parquet(prices_path)

    from aionis.eval.forward_score import fetch_realized_forward_returns

    result = fetch_realized_forward_returns(
        predict_ts="2026-07-01",
        target_t="2026-07-22",
        tickers=["AAPL", "MSFT", "GOOGL"],
        prices_path=prices_path,
    )

    # MSFT excluded because missing at predict_ts
    assert len(result) == 2
    assert set(result["ticker"]) == {"AAPL", "GOOGL"}


def test_fetch_realized_forward_returns_pit_note():
    """PIT: uses only prices at predict_ts and target_t (no lookahead beyond target_t)."""
    # This is a documentation test - the function should not use any data beyond target_t
    # The implementation should only slice the price parquet at the two timestamps
    pass


# ---------------------------------------------------------------------------
# 4b - reveal_and_score_forward_month tests
# ---------------------------------------------------------------------------


def test_reveal_and_score_forward_month_i1_gate_before_target(tmp_path):
    """I1 gate: now < target_t → both arms return {revealed: False}, NO rows appended."""
    from aionis.eval.forward_score import reveal_and_score_forward_month
    from aionis.reporting import forward_ledger as FL

    # Setup: create a minimal commit row
    commit_row = {
        "event": FL.EVENT_COMMIT,
        "predict_ts": "2026-07-01T00:00:00+00:00",
        "target_t": "2026-07-22T00:00:00+00:00",
        "config_sha256": "test" * 16,  # 64 chars
        "scores_path": "scores/test_scores.parquet",  # Relative path within runs_dir
    }

    # Create tmp runs_dir structure
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    scores_dir = runs_dir / "scores"
    scores_dir.mkdir()

    # Create a minimal scores parquet in the correct location
    scores = pd.DataFrame({
        "ticker": ["AAPL", "MSFT", "GOOGL"] * 2,
        "arm": ["arm_base"] * 3 + ["arm_e13"] * 3,
        "score": [0.5, 0.6, 0.4, 0.55, 0.65, 0.45],
    })
    scores_path = scores_dir / "test_scores.parquet"
    scores.to_parquet(scores_path, index=False)

    # Create a minimal price parquet
    prices = pd.DataFrame(
        {
            "AAPL": {pd.Timestamp("2026-07-01"): 150.0, pd.Timestamp("2026-07-22"): 153.0},
            "MSFT": {pd.Timestamp("2026-07-01"): 300.0, pd.Timestamp("2026-07-22"): 306.0},
            "GOOGL": {pd.Timestamp("2026-07-01"): 120.0, pd.Timestamp("2026-07-22"): 117.6},
        }
    )
    prices.index.name = "date"
    prices_path = tmp_path / "prices.parquet"
    prices.to_parquet(prices_path)

    # Create ledger
    ledger_path = runs_dir / "ledger.jsonl"

    # Write the commit row to ledger
    with open(ledger_path, "a") as f:
        import json
        json.dump({**commit_row, "ts": "2026-07-01T00:00:00+00:00", "phase": "E3"}, f)
        f.write("\n")

    # Call with now < target_t (before target)
    now = "2026-07-15T00:00:00+00:00"  # Before target_t

    result = reveal_and_score_forward_month(
        commit_row,
        prices_path=prices_path,
        runs_dir=runs_dir,
        now=now,
    )

    # Both arms should return {revealed: False} with I1 gate reason
    assert "arm_base" in result
    assert "arm_e13" in result
    assert result["arm_base"]["revealed"] is False
    assert result["arm_e13"]["revealed"] is False
    assert "before_target_t" in result["arm_base"]["reason"]
    assert "before_target_t" in result["arm_e13"]["reason"]

    # Verify NO forward_outcome_scored rows were appended
    with open(ledger_path) as f:
        scored_rows = [line for line in f if FL.EVENT_SCORED in line]
    assert len(scored_rows) == 0


def test_reveal_and_score_forward_month_after_target(tmp_path):
    """now >= target_t → both arms {revealed: True, ic_point: <float>}, exactly 2 rows appended."""
    from aionis.eval.forward_score import reveal_and_score_forward_month
    from aionis.reporting import forward_ledger as FL

    # Setup: create commit row + scores + prices
    commit_row = {
        "event": FL.EVENT_COMMIT,
        "predict_ts": "2026-07-01T00:00:00+00:00",
        "target_t": "2026-07-22T00:00:00+00:00",
        "config_sha256": "test" * 16,
        "scores_path": "scores/test_scores.parquet",
    }

    # Create tmp runs_dir structure
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    scores_dir = runs_dir / "scores"
    scores_dir.mkdir()

    # Scores: create perfect monotonic relationship for easy IC calculation
    scores = pd.DataFrame({
        "ticker": ["AAPL", "MSFT", "GOOGL"] * 2,
        "arm": ["arm_base"] * 3 + ["arm_e13"] * 3,
        "score": [1.0, 2.0, 3.0, 1.0, 2.0, 3.0],  # Perfect rank order
    })
    scores_path = scores_dir / "test_scores.parquet"
    scores.to_parquet(scores_path, index=False)

    # Prices: create perfect monotonic returns matching score order
    prices = pd.DataFrame(
        {
            "AAPL": {pd.Timestamp("2026-07-01"): 100.0, pd.Timestamp("2026-07-22"): 105.0},  # +5%
            "MSFT": {pd.Timestamp("2026-07-01"): 100.0, pd.Timestamp("2026-07-22"): 110.0},  # +10%
            "GOOGL": {pd.Timestamp("2026-07-01"): 100.0, pd.Timestamp("2026-07-22"): 115.0},  # +15%
        }
    )
    prices.index.name = "date"
    prices_path = tmp_path / "prices.parquet"
    prices.to_parquet(prices_path)

    # Create ledger
    ledger_path = runs_dir / "ledger.jsonl"

    # Write commit row
    with open(ledger_path, "a") as f:
        import json
        json.dump({**commit_row, "ts": "2026-07-01T00:00:00+00:00", "phase": "E3"}, f)
        f.write("\n")

    # Call with now >= target_t
    now = "2026-07-23T00:00:00+00:00"  # After target_t

    result = reveal_and_score_forward_month(
        commit_row,
        prices_path=prices_path,
        runs_dir=runs_dir,
        now=now,
    )

    # Should have revealed both arms successfully
    assert isinstance(result, dict)
    assert "arm_base" in result
    assert "arm_e13" in result
    assert result["arm_base"]["revealed"] is True
    assert result["arm_e13"]["revealed"] is True
    assert "ic_point" in result["arm_base"]
    assert "ic_point" in result["arm_e13"]

    # Verify exactly 2 forward_outcome_scored rows were appended
    with open(ledger_path) as f:
        scored_rows = [line for line in f if FL.EVENT_SCORED in line]
    assert len(scored_rows) == 2


def test_reveal_and_score_forward_month_idempotent(tmp_path):
    """I2 idempotency: re-call → no duplicate rows (reveal_forward_outcome handles it)."""
    from aionis.eval.forward_score import reveal_and_score_forward_month
    from aionis.reporting import forward_ledger as FL

    # Setup same as after_target test
    commit_row = {
        "event": FL.EVENT_COMMIT,
        "predict_ts": "2026-07-01T00:00:00+00:00",
        "target_t": "2026-07-22T00:00:00+00:00",
        "config_sha256": "test" * 16,
        "scores_path": "scores/test_scores.parquet",
    }

    # Create tmp runs_dir structure
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    scores_dir = runs_dir / "scores"
    scores_dir.mkdir()

    scores = pd.DataFrame({
        "ticker": ["AAPL", "MSFT", "GOOGL"] * 2,
        "arm": ["arm_base"] * 3 + ["arm_e13"] * 3,
        "score": [1.0, 2.0, 3.0, 1.0, 2.0, 3.0],
    })
    scores_path = scores_dir / "test_scores.parquet"
    scores.to_parquet(scores_path, index=False)

    prices = pd.DataFrame(
        {
            "AAPL": {pd.Timestamp("2026-07-01"): 100.0, pd.Timestamp("2026-07-22"): 105.0},
            "MSFT": {pd.Timestamp("2026-07-01"): 100.0, pd.Timestamp("2026-07-22"): 110.0},
            "GOOGL": {pd.Timestamp("2026-07-01"): 100.0, pd.Timestamp("2026-07-22"): 115.0},
        }
    )
    prices.index.name = "date"
    prices_path = tmp_path / "prices.parquet"
    prices.to_parquet(prices_path)

    ledger_path = runs_dir / "ledger.jsonl"

    with open(ledger_path, "a") as f:
        import json
        json.dump({**commit_row, "ts": "2026-07-01T00:00:00+00:00", "phase": "E3"}, f)
        f.write("\n")

    now = "2026-07-23T00:00:00+00:00"

    # First call (side effect: appends scored rows)
    reveal_and_score_forward_month(
        commit_row,
        prices_path=prices_path,
        runs_dir=runs_dir,
        now=now,
    )

    # Count scored rows after first call
    with open(ledger_path) as f:
        scored_count_1 = sum(1 for line in f if FL.EVENT_SCORED in line)

    # Second call (should be idempotent)
    reveal_and_score_forward_month(
        commit_row,
        prices_path=prices_path,
        runs_dir=runs_dir,
        now=now,
    )

    # Count scored rows after second call
    with open(ledger_path) as f:
        scored_count_2 = sum(1 for line in f if FL.EVENT_SCORED in line)

    # Should have same number of scored rows (no duplicates)
    assert scored_count_1 == scored_count_2


def test_reveal_and_score_forward_month_ic_point_correct(tmp_path):
    """ic_point is the correct Spearman of scores vs realized returns on a tiny fixture."""
    from aionis.eval.forward_score import reveal_and_score_forward_month
    from aionis.reporting import forward_ledger as FL

    # Setup with known scores and returns
    commit_row = {
        "event": FL.EVENT_COMMIT,
        "predict_ts": "2026-07-01T00:00:00+00:00",
        "target_t": "2026-07-22T00:00:00+00:00",
        "config_sha256": "test" * 16,
        "scores_path": "scores/test_scores.parquet",
    }

    # Create tmp runs_dir structure
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    scores_dir = runs_dir / "scores"
    scores_dir.mkdir()

    # Create scores with known rank order
    scores = pd.DataFrame({
        "ticker": ["AAPL", "MSFT", "GOOGL"] * 2,
        "arm": ["arm_base"] * 3 + ["arm_e13"] * 3,
        "score": [1.0, 2.0, 3.0, 3.0, 2.0, 1.0],  # base: ascending, e13: descending
    })
    scores_path = scores_dir / "test_scores.parquet"
    scores.to_parquet(scores_path, index=False)

    # Create returns with known rank order (ascending)
    prices = pd.DataFrame(
        {
            "AAPL": {pd.Timestamp("2026-07-01"): 100.0, pd.Timestamp("2026-07-22"): 105.0},  # +5%
            "MSFT": {pd.Timestamp("2026-07-01"): 100.0, pd.Timestamp("2026-07-22"): 110.0},  # +10%
            "GOOGL": {pd.Timestamp("2026-07-01"): 100.0, pd.Timestamp("2026-07-22"): 115.0},  # +15%
        }
    )
    prices.index.name = "date"
    prices_path = tmp_path / "prices.parquet"
    prices.to_parquet(prices_path)

    ledger_path = runs_dir / "ledger.jsonl"

    with open(ledger_path, "a") as f:
        import json
        json.dump({**commit_row, "ts": "2026-07-01T00:00:00+00:00", "phase": "E3"}, f)
        f.write("\n")

    now = "2026-07-23T00:00:00+00:00"

    # Call reveal_and_score_forward_month (side effect: appends scored rows)
    reveal_and_score_forward_month(
        commit_row,
        prices_path=prices_path,
        runs_dir=runs_dir,
        now=now,
    )

    # Expected ICs:
    # arm_base: scores [1,2,3] vs returns [5,10,15] -> perfect positive correlation -> IC = 1.0
    # arm_e13: scores [3,2,1] vs returns [5,10,15] -> perfect negative correlation -> IC = -1.0

    # The result should contain the ic_point values
    # We'll verify by reading back from ledger
    with open(ledger_path) as f:
        scored_rows = [json.loads(line) for line in f if FL.EVENT_SCORED in line]

    assert len(scored_rows) == 2

    # Find arm_base and arm_e13 rows
    base_row = next(r for r in scored_rows if r.get("arm") == "arm_base")
    e13_row = next(r for r in scored_rows if r.get("arm") == "arm_e13")

    # Verify IC points
    assert base_row["ic_point"] == pytest.approx(1.0, abs=0.01)
    assert e13_row["ic_point"] == pytest.approx(-1.0, abs=0.01)


# ---------------------------------------------------------------------------
# 4c - accumulate_forward_ic_series tests
# ---------------------------------------------------------------------------


def test_accumulate_forward_ic_series_differential_correct(tmp_path):
    """Differential correct on 3 months (ic_e13 − ic_base)."""

    from aionis.eval.forward_score import accumulate_forward_ic_series
    from aionis.reporting import forward_ledger as FL

    # Setup: create 3 months of scored data
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    ledger_path = runs_dir / "ledger.jsonl"

    config_sha256 = "test" * 16

    # Month 1: base IC = 0.5, e13 IC = 0.7 → diff = 0.2
    month1_data = [
        {
            "event": FL.EVENT_SCORED,
            "phase": "E3",
            "predict_ts": "2026-01-31T00:00:00+00:00",
            "target_t": "2026-02-21T00:00:00+00:00",
            "config_sha256": config_sha256,
            "arm": "arm_base",
            "ic_point": 0.5,
            "ts": "2026-02-22T00:00:00+00:00",
        },
        {
            "event": FL.EVENT_SCORED,
            "phase": "E3",
            "predict_ts": "2026-01-31T00:00:00+00:00",
            "target_t": "2026-02-21T00:00:00+00:00",
            "config_sha256": config_sha256,
            "arm": "arm_e13",
            "ic_point": 0.7,
            "ts": "2026-02-22T00:00:00+00:00",
        },
    ]

    # Month 2: base IC = 0.3, e13 IC = 0.4 → diff = 0.1
    month2_data = [
        {
            "event": FL.EVENT_SCORED,
            "phase": "E3",
            "predict_ts": "2026-02-28T00:00:00+00:00",
            "target_t": "2026-03-21T00:00:00+00:00",
            "config_sha256": config_sha256,
            "arm": "arm_base",
            "ic_point": 0.3,
            "ts": "2026-03-22T00:00:00+00:00",
        },
        {
            "event": FL.EVENT_SCORED,
            "phase": "E3",
            "predict_ts": "2026-02-28T00:00:00+00:00",
            "target_t": "2026-03-21T00:00:00+00:00",
            "config_sha256": config_sha256,
            "arm": "arm_e13",
            "ic_point": 0.4,
            "ts": "2026-03-22T00:00:00+00:00",
        },
    ]

    # Month 3: base IC = -0.2, e13 IC = 0.1 → diff = 0.3
    month3_data = [
        {
            "event": FL.EVENT_SCORED,
            "phase": "E3",
            "predict_ts": "2026-03-31T00:00:00+00:00",
            "target_t": "2026-04-21T00:00:00+00:00",
            "config_sha256": config_sha256,
            "arm": "arm_base",
            "ic_point": -0.2,
            "ts": "2026-04-22T00:00:00+00:00",
        },
        {
            "event": FL.EVENT_SCORED,
            "phase": "E3",
            "predict_ts": "2026-03-31T00:00:00+00:00",
            "target_t": "2026-04-21T00:00:00+00:00",
            "config_sha256": config_sha256,
            "arm": "arm_e13",
            "ic_point": 0.1,
            "ts": "2026-04-22T00:00:00+00:00",
        },
    ]

    # Write all to ledger
    import json
    for row in month1_data + month2_data + month3_data:
        with open(ledger_path, "a") as f:
            json.dump(row, f)
            f.write("\n")

    # Call accumulator
    result = accumulate_forward_ic_series(
        config_sha256=config_sha256,
        runs_dir=runs_dir,
    )

    # Verify differential series
    ic_forward = result["ic_forward"]
    assert len(ic_forward) == 3
    assert ic_forward.iloc[0] == pytest.approx(0.2, abs=1e-6)  # 0.7 - 0.5
    assert ic_forward.iloc[1] == pytest.approx(0.1, abs=1e-6)  # 0.4 - 0.3
    assert ic_forward.iloc[2] == pytest.approx(0.3, abs=1e-6)  # 0.1 - (-0.2)

    # Verify summary has expected keys
    summary = result["summary"]
    expected_keys = {
        "mean_diff", "se_hac", "ci_half", "ci_lo", "ci_hi",
        "dm_stat", "dm_p_mbb", "dm_flag", "n_months",
    }
    assert expected_keys.issubset(summary.keys())

    # Verify n_months
    assert result["n_months"] == 3


def test_accumulate_forward_ic_series_summary_keys(tmp_path):
    """Summary has the E1 differential() keys."""
    import json

    from aionis.eval.forward_score import accumulate_forward_ic_series
    from aionis.reporting import forward_ledger as FL

    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    ledger_path = runs_dir / "ledger.jsonl"

    config_sha256 = "test" * 16

    # Create 2 months of scored data
    for i in range(2):
        predict_ts = f"2026-{i+1:02d}-15T00:00:00+00:00"
        for arm in ("arm_base", "arm_e13"):
            row = {
                "event": FL.EVENT_SCORED,
                "phase": "E3",
                "predict_ts": predict_ts,
                "target_t": f"2026-{i+1:02d}-25T00:00:00+00:00",
                "config_sha256": config_sha256,
                "arm": arm,
                "ic_point": 0.1 if arm == "arm_base" else 0.2,
                "ts": f"2026-{i+1:02d}-26T00:00:00+00:00",
            }
            with open(ledger_path, "a") as f:
                json.dump(row, f)
                f.write("\n")

    result = accumulate_forward_ic_series(
        config_sha256=config_sha256,
        runs_dir=runs_dir,
    )

    summary = result["summary"]
    expected_keys = {
        "mean_diff", "se_hac", "ci_half", "ci_lo", "ci_hi",
        "dm_stat", "dm_p_mbb", "dm_flag", "n_months",
    }
    assert expected_keys.issubset(summary.keys())


def test_accumulate_forward_ic_series_h6_determinism(tmp_path):
    """H6 determinism: accumulate twice on identical rows → identical output."""
    import json

    import numpy as np

    from aionis.eval.forward_score import accumulate_forward_ic_series
    from aionis.reporting import forward_ledger as FL

    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    ledger_path = runs_dir / "ledger.jsonl"

    config_sha256 = "test" * 16

    # Create 2 months of scored data
    for i in range(2):
        predict_ts = f"2026-0{i+1}-15T00:00:00+00:00"
        for arm in ("arm_base", "arm_e13"):
            row = {
                "event": FL.EVENT_SCORED,
                "phase": "E3",
                "predict_ts": predict_ts,
                "target_t": f"2026-0{i+1}-25T00:00:00+00:00",
                "config_sha256": config_sha256,
                "arm": arm,
                "ic_point": 0.1 if arm == "arm_base" else 0.2,
                "ts": f"2026-0{i+1}-26T00:00:00+00:00",
            }
            with open(ledger_path, "a") as f:
                json.dump(row, f)
                f.write("\n")

    # First accumulation
    result1 = accumulate_forward_ic_series(
        config_sha256=config_sha256,
        runs_dir=runs_dir,
    )

    # Second accumulation (should be identical)
    result2 = accumulate_forward_ic_series(
        config_sha256=config_sha256,
        runs_dir=runs_dir,
    )

    # Verify identical output
    assert np.array_equal(result1["ic_forward"].values, result2["ic_forward"].values)

    # For summary, check each key (handling NaN properly)
    summary1 = result1["summary"]
    summary2 = result2["summary"]
    for key in summary1.keys():
        val1 = summary1[key]
        val2 = summary2[key]
        if isinstance(val1, float):
            if np.isnan(val1) and np.isnan(val2):
                continue  # Both NaN is OK
            elif np.isnan(val1) or np.isnan(val2):
                raise AssertionError(f"Summary key {key}: one is NaN, the other is not")
            else:
                assert val1 == pytest.approx(val2), f"Summary key {key} differs"
        else:
            assert val1 == val2, f"Summary key {key} differs"

    assert result1["n_months"] == result2["n_months"]


def test_accumulate_forward_ic_series_skips_unscored(tmp_path):
    """Skips commits with no scored row (only accumulates revealed)."""
    import json

    from aionis.eval.forward_score import accumulate_forward_ic_series
    from aionis.reporting import forward_ledger as FL

    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    ledger_path = runs_dir / "ledger.jsonl"

    config_sha256 = "test" * 16

    # Add one scored row
    scored_row = {
        "event": FL.EVENT_SCORED,
        "phase": "E3",
        "predict_ts": "2026-01-15T00:00:00+00:00",
        "target_t": "2026-02-05T00:00:00+00:00",
        "config_sha256": config_sha256,
        "arm": "arm_base",
        "ic_point": 0.1,
        "ts": "2026-02-06T00:00:00+00:00",
    }
    with open(ledger_path, "a") as f:
        json.dump(scored_row, f)
        f.write("\n")

    # Add a commit row (not scored) - should be skipped
    commit_row = {
        "event": FL.EVENT_COMMIT,
        "phase": "E3",
        "predict_ts": "2026-02-15T00:00:00+00:00",
        "target_t": "2026-03-08T00:00:00+00:00",
        "config_sha256": config_sha256,
        "scores_path": "scores/test.parquet",
        "ts": "2026-02-15T00:00:00+00:00",
    }
    with open(ledger_path, "a") as f:
        json.dump(commit_row, f)
        f.write("\n")

    result = accumulate_forward_ic_series(
        config_sha256=config_sha256,
        runs_dir=runs_dir,
    )

    # Should have 0 months (need both arms for differential)
    assert result["n_months"] == 0

