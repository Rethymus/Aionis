"""Hermetic tests for the Track LLM Phase-0 feasibility pilot.

Synthetic data only — no network, no creds, no OOS rank-IC observation. Locks the
CIK-resolution math (G1), the token-cost projection (G2), and the gate verdict
logic. The pilot itself observes no research outcome and writes no ledger.
"""

from __future__ import annotations

import pandas as pd

from scripts.track_llm_feasibility_pilot import (
    measure_cik_resolution,
    project_token_cost,
    summarize,
)


def _oos(rows: list[tuple[str, int]]) -> pd.DataFrame:
    """Minimal OOS frame: normalized ticker + year (the columns G1 consumes)."""
    return pd.DataFrame(rows, columns=["ticker_norm", "year"])


# --- G1: CIK resolution -------------------------------------------------------

# 2021: AAA BBB CCC DDD ; 2022: AAA BBB.  cmap resolves AAA/BBB/CCC (not DDD).
_FRAME = _oos(
    [("AAA", 2021), ("BBB", 2021), ("CCC", 2021), ("DDD", 2021), ("AAA", 2022), ("BBB", 2022)]
)
_CMAP = {"AAA": 1, "BBB": 2, "CCC": 3}


def test_resolution_rate_overall_and_per_year() -> None:
    res = measure_cik_resolution(_FRAME, _CMAP)
    assert res["n_distinct_tickers"] == 4
    assert res["n_resolved"] == 3
    assert res["resolution_rate"] == 0.75
    # 2021: AAA,BBB,CCC resolve = 3 ; 2022: AAA,BBB resolve = 2 → 5 ticker-years.
    assert res["ticker_years_resolved"] == 5
    by_year = {row["year"]: row for row in res["per_year"]}
    assert by_year[2021]["rate"] == 0.75
    assert by_year[2022]["rate"] == 1.0


def test_resolution_unresolved_sample_capped_at_20() -> None:
    """50 distinct unresolved tickers → sample capped at 20 (not the whole tail)."""
    res = measure_cik_resolution(_oos([(f"T{i:03d}", 2024) for i in range(50)]), cmap={})
    assert res["n_resolved"] == 0
    assert res["resolution_rate"] == 0.0
    assert len(res["unresolved_sample"]) == 20
    assert res["ticker_years_resolved"] == 0


# --- G2: token-cost projection ------------------------------------------------


def test_projection_oos_plus_train_filings_times_tokens() -> None:
    """OOS filings (from ticker-years) + train filings (universe × years), × tokens."""
    res = {"ticker_years_resolved": 2900, "n_distinct_tickers": 500}
    proj = project_token_cost(res, tokens_per_10k=2000, train_years=5, train_universe=500)
    assert proj["oos_filings"] == 2900
    assert proj["train_filings"] == 500 * 5
    assert proj["total_filings"] == 2900 + 2500
    assert proj["total_tokens"] == (2900 + 2500) * 2000
    assert proj["tokens_millions"] == round(((2900 + 2500) * 2000) / 1_000_000, 2)
    assert proj["one_time"] is True


def test_projection_train_universe_defaults_to_oos_distinct() -> None:
    """No train_universe given → assume the OOS distinct count (conservative floor)."""
    res = {"ticker_years_resolved": 100, "n_distinct_tickers": 460}
    proj = project_token_cost(res, tokens_per_10k=2100, train_years=5)
    assert proj["train_universe_assumed"] == 460
    assert proj["train_filings"] == 460 * 5


# --- summary: gate verdict ----------------------------------------------------


_RES_OK = {"resolution_rate": 1.0, "n_distinct_tickers": 500, "ticker_years_resolved": 2900}


def test_summary_green_when_both_gates_pass() -> None:
    s = summarize(_RES_OK, {"tokens_millions": 11.0})
    assert s["g1_cik_resolution"]["gate"] == "green"
    assert s["g2_token_cost"]["gate"] == "green"
    assert "FEASIBLE" in s["verdict"]


def test_summary_amber_when_coverage_below_threshold() -> None:
    res = {**_RES_OK, "resolution_rate": 0.80}
    s = summarize(res, {"tokens_millions": 11.0})
    assert s["g1_cik_resolution"]["gate"] == "amber"
    assert "REVIEW" in s["verdict"]


def test_summary_red_when_coverage_low_or_cost_high() -> None:
    low_cov = summarize({**_RES_OK, "resolution_rate": 0.50}, {"tokens_millions": 11.0})
    assert low_cov["g1_cik_resolution"]["gate"] == "red"
    high_cost = summarize(_RES_OK, {"tokens_millions": 60.0})
    assert high_cost["g2_token_cost"]["gate"] == "red"
    assert "REVIEW" in high_cost["verdict"]


def test_summary_discloses_no_oos_no_ledger() -> None:
    """The pilot must disclose it observes no OOS IC and writes no ledger."""
    s = summarize(_RES_OK, {"tokens_millions": 11.0})
    assert "No OOS rank-IC" in s["note"]
    assert "no ledger" in s["note"]
