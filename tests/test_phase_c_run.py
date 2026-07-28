"""Phase C runner — hermetic end-to-end on synthetic data (no network).

Exercises the real :mod:`aionis.eval.phase_c` orchestration: config determinism,
the config_committed-BEFORE-result ledger anchor, the H6 bit-identical re-run,
the bundle-shuffle placebo + sanity + leave-one-out controls, the publishability
CI gate, and the ``save_run`` artifact layout — all on a tiny synthetic panel
with the bundle INJECTED directly (so no ALFRED / FRED / EDGAR fetch is needed).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from aionis.eval import phase_c
from aionis.features.alignment import nyse_sessions
from aionis.reporting import results


def _fixtures(seed: int = 0, n_sess: int = 200,
              tickers: tuple[str, ...] = ("A", "B", "C", "D", "E", "F"),
              ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DatetimeIndex]:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2023-01-02", periods=n_sess)
    px = pd.DataFrame(
        100 + np.cumsum(rng.normal(size=(n_sess, len(tickers))), axis=0),
        index=dates, columns=list(tickers),
    )
    months = pd.date_range(dates[0], dates[-1], freq="MS")
    mem = pd.DataFrame(
        [(m, t) for m in months for t in tickers], columns=["date", "ticker"],
    )
    sessions = nyse_sessions(px.index.min(), px.index.max())
    return px, mem, sessions


def _synthetic_bundle(sessions: pd.DatetimeIndex, tickers: list[str], seed: int):
    rng = np.random.default_rng(seed)
    bundle_broadcast = pd.DataFrame(
        rng.normal(size=(len(sessions), 3)),
        index=sessions,
        columns=["macro_cpi_surprise", "macro_nfp_surprise", "vix_surprise"],
    )
    # punch some NaN to exercise native handling
    bundle_broadcast.iloc[:5, :] = np.nan
    rows = [
        (d, t, float(rng.normal()))
        for i, d in enumerate(sessions) for t in tickers
    ]
    earnings_long = pd.DataFrame(rows, columns=["date", "ticker", "earnings_surprise"])
    sanity_broadcast = pd.DataFrame(
        {"ff_mkt_rf": rng.normal(size=len(sessions))}, index=sessions,
    )
    return bundle_broadcast, earnings_long, sanity_broadcast


# --- config + ledger anchor --------------------------------------------------


def test_build_config_is_deterministic() -> None:
    shas = {"fund_sha256": "a" * 64, "prices_sha256": "b" * 64}
    meta = {"vix_surprise_kind": "ar"}

    a = phase_c.build_config(shas, meta)
    b = phase_c.build_config(shas, meta)

    assert a == b
    # the configSig is the sha256 of the canonical JSON -> stable
    import hashlib

    sig = hashlib.sha256(json.dumps(a, sort_keys=True).encode()).hexdigest()
    assert sig == hashlib.sha256(json.dumps(b, sort_keys=True).encode()).hexdigest()


def test_commit_config_writes_anchor_before_result(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    config = phase_c.build_config({"fund_sha256": "a" * 64}, {"vix_surprise_kind": "ar"})

    sig = phase_c.commit_config(config, ledger)

    rows = [json.loads(line) for line in ledger.read_text().splitlines() if line.strip()]
    assert len(rows) == 1
    assert rows[0]["event"] == "config_committed"
    assert rows[0]["phase"] == "C"
    assert rows[0]["config_sig"] == sig


# --- differential -----------------------------------------------------------


def test_differential_ci_brackets_mean_and_dm_finite() -> None:
    idx = pd.date_range("2017-01-31", periods=40, freq="ME")
    rng = np.random.default_rng(0)
    ic_a = pd.Series(rng.normal(0.02, 0.05, 40), index=idx)
    ic_b = pd.Series(rng.normal(0.01, 0.05, 40), index=idx)

    d = phase_c.differential(ic_a, ic_b)

    assert d["n_months"] == 40
    assert np.isfinite(d["mean_diff"])
    assert d["ci_lo"] < d["mean_diff"] < d["ci_hi"]
    assert np.isfinite(d["dm_p_mbb"])
    assert d["dm_p_mbb"] >= 0.0


# --- full pipeline (synthetic, no network) ----------------------------------


def test_run_confirmatory_full_pipeline_synthetic(tmp_path: Path) -> None:
    px, mem, sessions = _fixtures()
    tickers = list(px.columns)
    bundle_broadcast, earnings_long, sanity_broadcast = _synthetic_bundle(
        sessions, tickers, seed=1,
    )
    feature_cols = ["close"]
    bundle_cols = ["macro_cpi_surprise", "macro_nfp_surprise", "vix_surprise",
                   "earnings_surprise"]
    config = phase_c.build_config(
        {"fund_sha256": "x" * 64}, {"vix_surprise_kind": "ar"},
    )
    ledger = tmp_path / "ledger.jsonl"
    sig = phase_c.commit_config(config, ledger)

    result = phase_c.run_confirmatory(
        pd.DataFrame(), px, mem,
        bundle_broadcast=bundle_broadcast, earnings_long=earnings_long,
        sanity_broadcast=sanity_broadcast, config=config, sig=sig,
        feature_cols=feature_cols, bundle_cols=bundle_cols,
        horizon=5, n_splits=3, embargo=3, params={"n_estimators": 40},
        ledger_path=ledger, results_base=tmp_path,
    )

    # H6 must hold (deterministic re-run, IC + raw scores)
    assert result["H6_deterministic"] is True
    # differential computed and finite
    d = result["differential_macro_minus_base"]
    assert np.isfinite(d["mean_diff"])
    assert "publishable_ci_half" in d
    # all three control families present
    ctrls = result["controls"]
    assert set(ctrls) == {"bundle_shuffle_placebo", "sanity_mkt_rf", "leave_one_out"}
    assert set(ctrls["leave_one_out"]) == set(bundle_cols)
    # multiple-testing haircut grid echoed
    assert set(result["multiple_testing_haircut"]) == {"arm_macro", "arm_base"}

    # ledger order: config_committed BEFORE confirmatory:first, same sig
    rows = [json.loads(line) for line in ledger.read_text().splitlines() if line.strip()]
    assert len(rows) == 2
    assert rows[0]["event"] == "config_committed"
    assert rows[1]["event"] == "confirmatory:first"
    assert rows[0]["config_sig"] == rows[1]["config_sig"] == sig

    # save_run wrote the artifact layout
    loaded = results.load_run(sig, base=tmp_path)
    assert loaded["h6_deterministic"] is True
    assert loaded["config_sig"] == sig
    assert np.isfinite(loaded["differential"]["mean_diff"])
