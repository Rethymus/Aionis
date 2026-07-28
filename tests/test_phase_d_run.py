"""Phase D runner — hermetic end-to-end on synthetic data (no network).

Exercises :mod:`aionis.eval.phase_d`: config determinism, the config_committed-
BEFORE-result anchor, H6 bit-identical re-run, the bundle-shuffle placebo +
leave-one-out, and the save_run round-trip — all on a tiny synthetic panel with
the relationship bundle INJECTED directly (no 13D / SIC / prices fetch).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from aionis.eval import phase_d
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


def _synthetic_rel(sessions: pd.DatetimeIndex, tickers: list[str], seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = [
        (d, t, float(rng.normal()), float(rng.choice([0.0, 1.0], p=[0.95, 0.05])))
        for d in sessions for t in tickers
    ]
    return pd.DataFrame(rows, columns=["date", "ticker", "peer_mom", "stakes_13d_event"])


# --- config + ledger anchor --------------------------------------------------


def test_build_config_is_deterministic() -> None:
    a = phase_d.build_config({"fund_sha256": "a" * 64}, {"rel_window": 21})
    b = phase_d.build_config({"fund_sha256": "a" * 64}, {"rel_window": 21})
    assert a == b
    sig_a = hashlib.sha256(json.dumps(a, sort_keys=True).encode()).hexdigest()
    sig_b = hashlib.sha256(json.dumps(b, sort_keys=True).encode()).hexdigest()
    assert sig_a == sig_b
    assert a["phase"] == "D" and a["rel_cols"] == ["peer_mom", "stakes_13d_event"]


def test_commit_config_writes_anchor_before_result(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    config = phase_d.build_config({"fund_sha256": "a" * 64}, {})
    sig = phase_d.commit_config(config, ledger)
    rows = [json.loads(line) for line in ledger.read_text().splitlines() if line.strip()]
    assert rows[0]["event"] == "config_committed" and rows[0]["phase"] == "D"
    assert rows[0]["config_sig"] == sig


# --- full pipeline (synthetic, no network) ----------------------------------


def test_run_confirmatory_full_pipeline_synthetic(tmp_path: Path) -> None:
    px, mem, sessions = _fixtures()
    tickers = list(px.columns)
    rel_extra = _synthetic_rel(sessions, tickers, seed=1)
    config = phase_d.build_config({"fund_sha256": "x" * 64}, {"rel_window": 21})
    ledger = tmp_path / "ledger.jsonl"
    sig = phase_d.commit_config(config, ledger)

    result = phase_d.run_confirmatory(
        pd.DataFrame(), px, mem, rel_extra=rel_extra, config=config, sig=sig,
        feature_cols=["close"], rel_cols=["peer_mom", "stakes_13d_event"],
        horizon=5, n_splits=3, embargo=3, params={"n_estimators": 40},
        ledger_path=ledger, results_base=tmp_path,
    )

    assert result["H6_deterministic"] is True
    d = result["differential_rel_minus_base"]
    assert np.isfinite(d["mean_diff"]) and "publishable_ci_half" in d
    assert set(result["controls"]) == {"bundle_shuffle_placebo", "leave_one_out"}
    assert set(result["controls"]["leave_one_out"]) == {"peer_mom", "stakes_13d_event"}

    # ledger order: config_committed BEFORE confirmatory:first, same sig
    rows = [json.loads(line) for line in ledger.read_text().splitlines() if line.strip()]
    assert [r["event"] for r in rows] == ["config_committed", "confirmatory:first"]
    assert rows[0]["config_sig"] == rows[1]["config_sig"] == sig

    loaded = results.load_run(sig, base=tmp_path)
    assert loaded["h6_deterministic"] is True
    assert np.isfinite(loaded["differential"]["mean_diff"])
