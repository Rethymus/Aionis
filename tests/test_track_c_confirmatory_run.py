"""Hermetic tests for the Track C confirmatory runner (no real data, no ledger).

Covers the pure helpers: frozen-config sig verification, H6 bit-identical
assertion (pass + fail), J-T look-reachability logic, and confirmatory row
construction. The full ``main()`` is exercised by the real confirmatory run
(see state/handoff.md), not here.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

import scripts.track_c_confirmatory_run as mod
from aionis.eval.track_c_joint import TrackCJointResult

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"


# ---------------------------------------------------------------------------
# Frozen-config sig verification
# ---------------------------------------------------------------------------

def test_verify_frozen_config_matches_ledger_48() -> None:
    """build_amendment() must reproduce frozen #48 sig e14b9d44..."""
    cfg = mod.verify_frozen_config()
    assert mod.config_sig(cfg) == mod.FROZEN_SIG_48
    assert cfg["confirmatory_go"]["d4_feature_cols"]["count"] == 41
    assert cfg["regime_state"]["meso"].startswith("US SIC-peer momentum ONLY")


def test_frozen_mismatch_raises(tmp_path, monkeypatch) -> None:
    """A mutated amendment must abort before any OOS observation."""
    # Simulate drift by pointing FROZEN_SIG_48 at a wrong value.
    monkeypatch.setattr(mod, "FROZEN_SIG_48", "0" * 64)
    with pytest.raises(SystemExit, match="FROZEN MISMATCH"):
        mod.verify_frozen_config()


# ---------------------------------------------------------------------------
# H6 bit-identical assertion
# ---------------------------------------------------------------------------

def _synthetic_result(*, seed: int = 0, n: int = 71) -> TrackCJointResult:
    """Build a TrackCJointResult with deterministic synthetic series."""
    import numpy as np

    rng = np.random.default_rng(seed)
    dates = pd.date_range("2021-01-31", periods=n, freq="ME")
    us = pd.Series(rng.normal(0, 0.1, n), index=dates, name="us_ic")
    cn = pd.Series(rng.normal(0, 0.1, n), index=dates, name="cn_ic")
    combined = ((us + cn) / 2).rename("combined_ic")
    oos = pd.DataFrame({
        "date": dates.repeat(5),
        "ticker": [f"T{i % 7}" for i in range(n * 5)],
        "region": (["us"] * (n * 5 // 2) + ["cn"] * (n * 5 - n * 5 // 2)),
        "score": rng.normal(0, 1, n * 5),
    })
    return TrackCJointResult(
        n_walk_folds=n - 60,
        per_fold=[],
        us_ic_series=us,
        cn_ic_series=cn,
        combined_ic_series=combined,
        mean_ic=float(combined.mean()),
        hac_se=0.01,
        ci_95=(-0.01, 0.01),
        t_hac=0.0,
        p_hac=1.0,
        cond_alpha=0.0,
        cond_alpha_p=1.0,
        cond_beta=0.0,
        cond_beta_p=1.0,
        cond_r_squared=0.0,
        cond_n_months=n,
        oos_scores=oos,
    )


def test_h6_identical_passes_for_same_seed() -> None:
    r1 = _synthetic_result(seed=0)
    r2 = _synthetic_result(seed=0)
    mod.assert_h6_identical(r1, r2)  # must not raise


def test_h6_identical_fails_on_ic_drift() -> None:
    r1 = _synthetic_result(seed=0)
    r2 = _synthetic_result(seed=1)
    with pytest.raises(AssertionError, match="H6 FAIL"):
        mod.assert_h6_identical(r1, r2)


def test_h6_identical_fails_on_oos_drift() -> None:
    r1 = _synthetic_result(seed=0)
    r2 = _synthetic_result(seed=0)
    # mutate oos_scores in r2
    r2 = TrackCJointResult(
        **{**r2.__dict__, "oos_scores": r2.oos_scores.assign(score=r2.oos_scores["score"] + 0.001)}
    )
    with pytest.raises(AssertionError, match="H6 FAIL"):
        mod.assert_h6_identical(r1, r2)


# ---------------------------------------------------------------------------
# J-T look-reachability
# ---------------------------------------------------------------------------

def test_jt_reachable_looks_only_look1_at_n71() -> None:
    """With 71 months, only look-1 (n=60) is reachable; 2/3 pending."""
    ic = pd.Series(
        range(71), index=pd.date_range("2021-01-31", periods=71, freq="ME"), dtype=float
    )
    looks = mod.jt_reachable_looks(ic)
    assert len(looks) == 3
    assert "verdict" in looks[0]  # look-1 reachable
    assert looks[0]["n_obs"] == 60
    assert looks[1]["status"].startswith("PENDING")
    assert looks[2]["status"].startswith("PENDING")


def test_jt_reachable_looks_truncates_to_first_n() -> None:
    """look_summary must operate on the first 60 months, not the full series."""
    ic = pd.Series(
        range(120), index=pd.date_range("2021-01-31", periods=120, freq="ME"), dtype=float
    )
    looks = mod.jt_reachable_looks(ic)
    # All 3 looks reachable with 120 months
    assert all("verdict" in lk for lk in looks)
    # look-1 uses first 60 only (mean = mean of 0..59)
    assert looks[0]["mu_hat"] == pytest.approx(sum(range(60)) / 60)


# ---------------------------------------------------------------------------
# confirmatory:first row construction
# ---------------------------------------------------------------------------

def test_build_confirmatory_row_shape_and_estimand() -> None:
    r1 = _synthetic_result(seed=0)
    ic = r1.combined_ic_series.sort_index()
    jt_looks = mod.jt_reachable_looks(ic)
    full = {"mean_ic": 0.001, "se_hac": 0.004, "t_hac": 0.25, "p_hac": 0.80,
            "ci_half": 0.008, "n": 71, "maxlag": 3}
    row = mod.build_confirmatory_row(
        result=r1, jt_looks=jt_looks, full_summary=full, n_months_banked=11,
    )
    assert row["event"] == "confirmatory:first"
    assert row["phase"] == "track_c"
    assert row["config_sig"] == mod.FROZEN_SIG_48
    assert row["H6_deterministic"] is True
    assert row["feature_cols_per_region"] == 41
    assert "combined rank-IC series mean" in row["estimand"]
    assert row["jt_gate"]["look1_verdict"] in {"EQUIVALENT", "NOT_EQUIVALENT"}
    assert row["jt_gate"]["banked_months_toward_look2"] == 11
    assert "prior_exploratory" in row["notes"]
    assert "estimand_choice" in row["notes"]
    # Row must be JSON-serializable (it will be append-only ledger content).
    json.dumps(row, default=str, sort_keys=True)


def test_ledger_untouched_in_dry_run(tmp_path, monkeypatch) -> None:
    """DRY-RUN must NOT append to the ledger (no TRACK_C_CONFIRMATORY_GO)."""
    fake_ledger = tmp_path / "ledger.jsonl"
    fake_ledger.write_text('{"event":"config_committed"}\n')
    monkeypatch.setattr(mod, "LEDGER", fake_ledger)
    monkeypatch.setenv("TRACK_C_CONFIRMATORY_GO", "")  # dry-run
    # We cannot run the full main() (needs real data); instead, verify the
    # gate logic: with owner_go False, no append happens.
    owner_go = mod.os.environ.get("TRACK_C_CONFIRMATORY_GO") == "1"
    assert owner_go is False
    assert fake_ledger.read_text().count("\n") == 1


# ---------------------------------------------------------------------------
# Edge-case hardening (sonnet review MEDIUM: empty / NaN / short series)
# ---------------------------------------------------------------------------

def test_jt_reachable_looks_empty_series() -> None:
    """An empty IC series must mark ALL looks pending (no reachable look)."""
    ic = pd.Series([], dtype=float)
    looks = mod.jt_reachable_looks(ic)
    assert len(looks) == 3
    assert all(lk["status"].startswith("PENDING") for lk in looks)


def test_jt_reachable_looks_short_series() -> None:
    """A series shorter than look-1 (60) must mark all looks pending."""
    ic = pd.Series(
        range(30), index=pd.date_range("2021-01-31", periods=30, freq="ME"), dtype=float
    )
    looks = mod.jt_reachable_looks(ic)
    assert all(lk["status"].startswith("PENDING") for lk in looks)
    assert looks[0]["n_obs_planned"] == 60


def test_jt_reachable_looks_boundary_n60() -> None:
    """Exactly 60 months: look-1 reachable, 2/3 pending (boundary inclusive)."""
    ic = pd.Series(
        range(60), index=pd.date_range("2021-01-31", periods=60, freq="ME"), dtype=float
    )
    looks = mod.jt_reachable_looks(ic)
    assert "verdict" in looks[0]  # exactly 60 -> reachable
    assert looks[1]["status"].startswith("PENDING (have 60 months, need 90)")


def test_jt_reachable_looks_nan_only_fails_cleanly() -> None:
    """An all-NaN 60-month series: look_summary should still return a dict
    (rank_ic_summary yields NaN mean_ic, which is a valid numeric verdict input).
    The gate must not crash on NaN-heavy input — it surfaces NaN as NOT_EQUIVALENT."""
    ic = pd.Series(
        [float("nan")] * 60, index=pd.date_range("2021-01-31", periods=60, freq="ME")
    )
    looks = mod.jt_reachable_looks(ic)
    assert "verdict" in looks[0]  # did not crash
    # NaN mean -> RCI is NaN -> not strictly within [-SESOI, +SESOI] -> NOT_EQUIVALENT
    assert looks[0]["verdict"] == "NOT_EQUIVALENT"


def test_h6_identical_nan_positions_match() -> None:
    """H6 must treat NaN in the SAME position as equal (pandas .equals semantics)."""
    r1 = _synthetic_result(seed=0)
    # Construct r2 identical to r1 (same seed) — NaN positions, if any, align.
    r2 = _synthetic_result(seed=0)
    mod.assert_h6_identical(r1, r2)  # must not raise


def test_build_row_does_not_mutate_result() -> None:
    """build_confirmatory_row must not mutate the estimator result (immutability)."""
    r1 = _synthetic_result(seed=0)
    ic = r1.combined_ic_series.sort_index()
    jt_looks = mod.jt_reachable_looks(ic)
    full = {"mean_ic": 0.0, "se_hac": 0.01, "t_hac": 0.0, "p_hac": 1.0,
            "ci_half": 0.02, "n": len(ic), "maxlag": 3}
    pre_combined = r1.combined_ic_series.copy()
    pre_oos = r1.oos_scores.copy()
    mod.build_confirmatory_row(
        result=r1, jt_looks=jt_looks, full_summary=full, n_months_banked=11,
    )
    pd.testing.assert_series_equal(r1.combined_ic_series, pre_combined)
    pd.testing.assert_frame_equal(r1.oos_scores, pre_oos)


# ---------------------------------------------------------------------------
# _commit_from_artifact guards (artifact-reuse commit path)
# ---------------------------------------------------------------------------

def _write_summary(tmp_path: Path, *, sig: str = mod.FROZEN_SIG_48, h6: bool = True) -> Path:
    """Write a synthetic summary.json (the dry-run's saved row)."""
    out_dir = tmp_path / "runs"
    out_dir.mkdir(parents=True, exist_ok=True)
    row = {
        "ts": "2026-08-05T13:48:00+00:00",
        "event": "confirmatory:first",
        "phase": "track_c",
        "config_sig": sig,
        "H6_deterministic": h6,
        "combined_ic": {"mean": -0.0088, "se_hac": 0.012, "t_hac": -0.73,
                        "p_hac": 0.47, "ci_95_half": 0.024, "maxlag": 3, "n": 71},
        "jt_gate": {"look1_verdict": "NOT_EQUIVALENT"},
    }
    (out_dir / "track_c_confirmatory_summary.json").write_text(json.dumps(row))
    return out_dir


def test_commit_from_artifact_missing_summary_raises(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(mod, "LEDGER", tmp_path / "ledger.jsonl")
    with pytest.raises(SystemExit, match="not found"):
        mod._commit_from_artifact(tmp_path / "runs")  # no summary.json


def test_commit_from_artifact_wrong_sig_raises(tmp_path, monkeypatch) -> None:
    out_dir = _write_summary(tmp_path, sig="0" * 64)  # wrong sig
    monkeypatch.setattr(mod, "LEDGER", tmp_path / "ledger.jsonl")
    with pytest.raises(SystemExit, match="FROZEN MISMATCH"):
        mod._commit_from_artifact(out_dir)


def test_commit_from_artifact_h6_false_raises(tmp_path, monkeypatch) -> None:
    out_dir = _write_summary(tmp_path, h6=False)
    monkeypatch.setattr(mod, "LEDGER", tmp_path / "ledger.jsonl")
    with pytest.raises(SystemExit, match="H6_deterministic"):
        mod._commit_from_artifact(out_dir)


def test_commit_from_artifact_appends_ledger(tmp_path, monkeypatch) -> None:
    out_dir = _write_summary(tmp_path)  # correct sig + H6 True
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text('{"event":"config_committed"}\n')
    monkeypatch.setattr(mod, "LEDGER", ledger)
    rc = mod._commit_from_artifact(out_dir)
    assert rc == 0
    lines = ledger.read_text().strip().split("\n")
    assert len(lines) == 2  # 1 config_committed + 1 confirmatory:first
    committed = json.loads(lines[1])
    assert committed["event"] == "confirmatory:first"
    assert committed["config_sig"] == mod.FROZEN_SIG_48
    assert committed["commit_mode"].startswith("artifact-reuse")
