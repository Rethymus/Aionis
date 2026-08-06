"""Contract tests for the tracked Quarto site data payloads.

The ``quarto-site/data/*.json`` files are the ONLY thing CI renders against
(``runs/`` is gitignored), so a silent change to ``export_quarto_data.py`` or to
the underlying results must surface here. These are pure checks on tracked
artifacts — hermetic, no network, no ``runs/`` dependency — and they encode the
public-facing numerical claims (null point estimate, power-floor infeasibility,
ML noise excess), so drifting them is a deliberate, review-visible act.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

DATA = Path("quarto-site/data")


def _load(name: str) -> list | dict:
    return json.loads((DATA / name).read_text())


# --- evidence table (the 15-row headline) -------------------------------------


def test_evidence_has_14_rows() -> None:
    # 14 rows: the table is numbered to n=15 but #12 is absent (export omits it);
    # the count is asserted so a future addition/removal is review-visible.
    assert len(_load("evidence.json")) == 14


def test_evidence_confirmatory_matches_climax() -> None:
    ev = _load("evidence.json")
    conf = [r for r in ev if r["grade"] == "CONFIRMATORY"]
    assert len(conf) == 1
    assert conf[0]["estimate"] == pytest.approx(-0.0088, abs=1e-4)
    # 95% HAC CI must bracket zero (null), matching ledger row #49.
    assert conf[0]["ci_lo"] < 0 < conf[0]["ci_hi"]


def test_evidence_all_differentials_bracket_zero() -> None:
    """Every reported CI brackets zero — the null-favored family claim."""
    for r in _load("evidence.json"):
        lo, hi = r.get("ci_lo"), r.get("ci_hi")
        if lo is None or hi is None:
            continue
        assert lo <= 0 <= hi, f"{r['result']} CI [{lo}, {hi}] does not bracket zero"


def test_evidence_grades_are_known() -> None:
    grades = {r["grade"] for r in _load("evidence.json")}
    assert grades <= {"CV-proxy", "chron./explor.", "explor.", "CONFIRMATORY"}


# --- power floor --------------------------------------------------------------


def test_power_floor_three_looks() -> None:
    looks = _load("power_floor.json")["looks"]
    assert [look["look"] for look in looks] == [1, 2, 3]
    assert [look["n"] for look in looks] == [60, 90, 120]
    # infeasibility: every look needs decades at the observed sigma.
    assert all(look["n_min_years"] > 30 for look in looks)


def test_power_floor_pure_noise_look3_feasible() -> None:
    """The mechanistic claim: the pure-noise bound would make look-3 feasible,
    so the floor binds via the ML noise excess, not the math bound."""
    pf = _load("power_floor.json")
    assert pf["n_min_at_pure_noise_look3_months"] < 120
    assert pf["n_min_at_observed_look3_months"] > 120


# --- sigma survey (the ML noise excess) ---------------------------------------


def test_sigma_survey_excess_is_real() -> None:
    s = _load("sigma_survey.json")
    rows = s["rows"]
    assert len(rows) >= 10
    # every series exceeds the pure-noise bound (the core mechanistic claim).
    assert all(r["excess_ratio"] >= 2.0 for r in rows), (
        "some IC series does not exceed the 2x pure-noise bound"
    )
    assert s["summary"]["excess_median"] >= 3.0


# --- bps sweep (economic lens) ------------------------------------------------


def test_bps_sweep_net_decays_monotonically() -> None:
    """Net Sharpe decays as slippage rises; gross and turnover are cost-independent."""
    bps = _load("bps_sweep.json")
    net = [r["net_sharpe"] for r in bps]
    assert net == sorted(net, reverse=True), "net Sharpe must decay as bps rises"
    gross = {round(r["gross_sharpe"], 6) for r in bps}
    assert len(gross) == 1, "gross Sharpe must be invariant to bps"
    turnover = {round(r["avg_turnover"], 6) for r in bps}
    assert len(turnover) == 1, "turnover must be invariant to bps"


def test_bps_sweep_has_break_even() -> None:
    bps = _load("bps_sweep.json")
    assert any(r["net_sharpe"] <= 0 for r in bps), "a break-even bps must exist"


# --- ic monthly (the time-series view) ----------------------------------------


def test_ic_monthly_is_71_months() -> None:
    icm = _load("ic_monthly.json")
    assert len(icm) == 71
    assert icm[0]["month"] == "2021-01"
    assert icm[-1]["month"] == "2026-06"


def test_ic_monthly_combined_mean_matches_climax() -> None:
    """The per-month combined IC mean must reproduce the confirmatory climax
    point estimate (ledger #49 ~ -0.0088) — cross-consistency between the
    time-series payload and the headline number."""
    icm = _load("ic_monthly.json")
    combined = [r["combined"] for r in icm]
    assert sum(combined) / len(combined) == pytest.approx(-0.0088, abs=0.004)
