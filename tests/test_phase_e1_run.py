"""Phase E1 runner — hermetic end-to-end on synthetic data (no network).

Exercises :mod:`aionis.eval.phase_e1`: config determinism, the config_committed-
BEFORE-result anchor, H6 bit-identical re-run, the bundle-shuffle placebo (prop
cols only) + leave-one-out, and the save_run round-trip — on a tiny synthetic
panel with self + propagated shock frames INJECTED directly.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from aionis.eval import phase_e1
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
    mem = pd.DataFrame([(m, t) for m in months for t in tickers], columns=["date", "ticker"])
    return px, mem, nyse_sessions(px.index.min(), px.index.max())


def _synthetic_long(sessions, tickers, seed, cols):
    rng = np.random.default_rng(seed)
    rows = [(d, t, *(float(rng.normal()) for _ in cols)) for d in sessions for t in tickers]
    return pd.DataFrame(rows, columns=["date", "ticker", *cols])


def test_build_config_is_deterministic() -> None:
    a = phase_e1.build_config({"fund_sha256": "a" * 64}, {"sic_window": "peers"})
    b = phase_e1.build_config({"fund_sha256": "a" * 64}, {"sic_window": "peers"})
    assert a == b
    assert a["phase"] == "E1"
    assert a["prop_cols"] == ["peer_earnings_surprise", "peer_13d_event"]


def test_commit_config_writes_anchor_before_result(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    sig = phase_e1.commit_config(phase_e1.build_config({"fund_sha256": "a" * 64}, {}), ledger)
    rows = [json.loads(line) for line in ledger.read_text().splitlines() if line.strip()]
    assert rows[0]["event"] == "config_committed" and rows[0]["phase"] == "E1"
    assert rows[0]["config_sig"] == sig


def test_run_confirmatory_full_pipeline_synthetic(tmp_path: Path) -> None:
    px, mem, sessions = _fixtures()
    tickers = list(px.columns)
    self_extra = _synthetic_long(sessions, tickers, 1, phase_e1.SELF_COLS)
    prop_extra = _synthetic_long(sessions, tickers, 2, phase_e1.PROP_COLS)
    config = phase_e1.build_config({"fund_sha256": "x" * 64}, {})
    ledger = tmp_path / "ledger.jsonl"
    sig = phase_e1.commit_config(config, ledger)

    result = phase_e1.run_confirmatory(
        pd.DataFrame(), px, mem, self_extra=self_extra, prop_extra=prop_extra,
        config=config, sig=sig, feature_cols=["close"],
        horizon=5, n_splits=3, embargo=3, params={"n_estimators": 40},
        ledger_path=ledger, results_base=tmp_path,
    )

    assert result["H6_deterministic"] is True
    d = result["differential_prop_minus_base_self"]
    assert np.isfinite(d["mean_diff"]) and "publishable_ci_half" in d
    assert set(result["controls"]) == {"bundle_shuffle_placebo", "leave_one_out"}
    assert set(result["controls"]["leave_one_out"]) == {"peer_earnings_surprise", "peer_13d_event"}

    rows = [json.loads(line) for line in ledger.read_text().splitlines() if line.strip()]
    assert [r["event"] for r in rows] == ["config_committed", "confirmatory:first"]
    assert rows[0]["config_sig"] == rows[1]["config_sig"] == sig

    loaded = results.load_run(sig, base=tmp_path)
    assert loaded["h6_deterministic"] is True
    assert np.isfinite(loaded["differential"]["mean_diff"])
