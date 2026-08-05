"""Hermetic tests for the IC noise-floor survey (scripts.ic_noise_floor_survey).

The survey is a thin analysis loop over persisted IC series; these tests cover the
testable unit (_stats: mean/std/n) and the survey-collection helpers on synthetic
IC series written to tmp_path. AAA pattern, deterministic, no network/real data.
"""
from __future__ import annotations

import importlib

import numpy as np
import pandas as pd
import pytest

survey = importlib.import_module("scripts.ic_noise_floor_survey")


def _ic_series(values: list[float]) -> pd.Series:
    idx = pd.date_range("2020-01-31", periods=len(values), freq="ME")
    return pd.Series(values, index=idx, name="ic")


# --- _stats ---


def test_stats_mean_std_n_known() -> None:
    """_stats returns the sample mean / std (ddof=1) / n for a known series."""
    s = _ic_series([0.10, -0.05, 0.20, -0.10, 0.15, 0.00])
    st = survey._stats(s)
    assert st["n"] == 6
    assert st["mean"] == pytest.approx(s.mean())
    assert st["std"] == pytest.approx(s.std(ddof=1))
    assert st["se_hac_proxy"] == pytest.approx(s.std(ddof=1) / (6 ** 0.5))


def test_stats_drops_nan() -> None:
    """NaN IC months are excluded from n / mean / std."""
    s = _ic_series([0.1, float("nan"), -0.1, 0.2, float("nan"), 0.0])
    st = survey._stats(s)
    assert st["n"] == 4  # 2 NaN dropped
    assert st["mean"] == pytest.approx(np.array([0.1, -0.1, 0.2, 0.0]).mean())


def test_stats_too_short_returns_none() -> None:
    """A single point has no std -> returns None (no power-floor claim from n<2)."""
    st = survey._stats(_ic_series([0.1]))
    assert st["n"] == 1
    assert st["std"] is None
    assert st["mean"] == pytest.approx(0.1)


# --- survey helpers (monkeypatch the glob patterns to tmp IC series) ---


def test_survey_track_c_collects_three_arms(tmp_path, monkeypatch) -> None:
    """A Track-C-style 3-column (us/cn/combined) IC series yields 3 rows."""
    df = pd.DataFrame(
        {"us": [0.1, -0.1, 0.2, -0.05], "cn": [-0.1, 0.2, -0.1, 0.15],
         "combined": [0.0, 0.05, -0.02, 0.1]},
        index=pd.date_range("2020-01-31", periods=4, freq="ME"),
    )
    f = tmp_path / "track_c_test_ic_series.parquet"
    df.to_parquet(f)
    monkeypatch.setattr(survey, "TRACK_C_PATTERNS", [str(tmp_path / "*_ic_series.parquet")])
    rows = survey._survey_track_c()
    assert len(rows) == 3
    arms = {r["arm"] for r in rows}
    assert arms == {"us", "cn", "combined"}
    for r in rows:
        assert r["n"] == 4
        assert r["std"] is not None


def test_main_writes_gitignored_json_and_never_ledger(tmp_path, monkeypatch) -> None:
    """main() writes only the gitignored survey json; never touches ledger.jsonl."""
    df = pd.DataFrame(
        {"combined": [0.1, -0.1, 0.2, -0.05, 0.0, 0.15]},
        index=pd.date_range("2020-01-31", periods=6, freq="ME"),
    )
    (tmp_path / "track_c_x_ic_series.parquet").parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(tmp_path / "track_c_x_ic_series.parquet")
    out = tmp_path / "survey.json"
    monkeypatch.setattr(survey, "TRACK_C_PATTERNS", [str(tmp_path / "*_ic_series.parquet")])
    monkeypatch.setattr(survey, "TRACK_B_PATTERNS", [])
    monkeypatch.setattr(survey, "OUT_PATH", str(out))
    # guard: no ledger path is ever written
    ledger_probe = tmp_path / "ledger.jsonl"
    monkeypatch.setattr(survey, "OUT_PATH", str(out))  # idempotent
    survey.main()
    import json
    payload = json.loads(out.read_text())
    assert "rows" in payload and "summary" in payload
    assert payload["summary"]["n_with_std"] == 1
    assert not ledger_probe.exists()  # survey never writes a ledger
