"""Hermetic tests for the Phase B results interface (aionis.reporting.results).

Covers the save/load/list contract the dashboard and the (future) run-script
wiring depend on. All tests use ``tmp_path`` so nothing touches the real
``runs/results`` dir or the real ledger.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from aionis.reporting import results as R

# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


def _ic(seed: int = 0, n: int = 24) -> pd.Series:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2017-01-31", periods=n, freq="ME")
    s = pd.Series(rng.normal(0.02, 0.05, n), index=idx, name="ic")
    s.index.name = "date"
    return s


def _run_payload(**overrides) -> dict:
    payload = dict(
        ic_state=_ic(0),
        ic_base=_ic(1),
        summary_state={"mean_ic": 0.021, "ci_half": 0.014, "n": 24},
        summary_base={"mean_ic": 0.008, "ci_half": 0.020, "n": 24},
        differential={"mean_diff": 0.013, "ci_lo": -0.002, "ci_hi": 0.028, "n": 24},
        controls={"lag_shift": {"mean_diff": 0.001}, "placebo": {"mean_diff": 0.0}},
        config={"horizon_sessions": 21, "note": "test"},
        h6_deterministic=True,
    )
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# run_dir / results_dir
# ---------------------------------------------------------------------------


def test_run_dir_under_base() -> None:
    d = R.run_dir("abc123", base="/tmp/aionis-x")
    assert d == Path("/tmp/aionis-x/results/abc123")


def test_run_dir_rejects_empty_sig() -> None:
    with pytest.raises(ValueError):
        R.run_dir("")


def test_run_dir_sanitizes_unsafe_sig() -> None:
    # a path-traversal-y sig must not escape the results root.
    d = R.run_dir("..evil/../etc", base="/tmp/aionis-y")
    # as_posix(): the assertion is about path STRUCTURE, not the OS separator
    # (WindowsPath renders backslashes and broke the raw str comparison).
    assert d.as_posix().startswith("/tmp/aionis-y/results/")
    assert ".." not in d.parts


# ---------------------------------------------------------------------------
# save / load round-trip
# ---------------------------------------------------------------------------


def test_save_run_creates_artifacts_and_returns_dir(tmp_path: Path) -> None:
    d = R.save_run("sig01", base=tmp_path, **_run_payload())
    assert d == tmp_path / "results" / "sig01"
    for name in (
        "ic_state.parquet", "ic_base.parquet", "summary_state.json",
        "summary_base.json", "differential.json", "controls.json",
        "config.json", "meta.json",
    ):
        assert (d / name).exists(), f"missing artifact {name}"


def test_load_run_round_trips_series_and_dicts(tmp_path: Path) -> None:
    payload = _run_payload()
    R.save_run("sig02", base=tmp_path, **payload)
    loaded = R.load_run("sig02", base=tmp_path)
    # IC series survive bit-for-bit (same index + values). parquet does not
    # preserve the index ``freq`` metadata, so compare on dates/values only.
    pd.testing.assert_series_equal(
        loaded["ic_state"], payload["ic_state"], check_names=False, check_freq=False
    )
    pd.testing.assert_series_equal(
        loaded["ic_base"], payload["ic_base"], check_names=False, check_freq=False
    )
    # dicts survive verbatim.
    assert loaded["summary_state"] == payload["summary_state"]
    assert loaded["differential"] == payload["differential"]
    assert loaded["controls"] == payload["controls"]
    assert loaded["config"] == payload["config"]
    # meta is populated.
    assert loaded["config_sig"] == "sig02"
    assert loaded["h6_deterministic"] is True
    assert loaded["ts"]


def test_load_run_preserves_date_index_name(tmp_path: Path) -> None:
    R.save_run("sig_idx", base=tmp_path, **_run_payload())
    loaded = R.load_run("sig_idx", base=tmp_path)
    assert loaded["ic_state"].index.name == "date"
    assert isinstance(loaded["ic_state"].index, pd.DatetimeIndex)


def test_load_run_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        R.load_run("does_not_exist", base=tmp_path)


def test_h6_flag_round_trips_false(tmp_path: Path) -> None:
    R.save_run("sig03", base=tmp_path, **_run_payload(h6_deterministic=False))
    assert R.load_run("sig03", base=tmp_path)["h6_deterministic"] is False


def test_save_ic_rejects_non_series(tmp_path: Path) -> None:
    with pytest.raises(TypeError):
        R.save_run("sig_bad", base=tmp_path, **_run_payload(ic_state=[1, 2, 3]))


# ---------------------------------------------------------------------------
# schema-2 additive OOS score panels
# ---------------------------------------------------------------------------


def _oos_panel(seed: int = 0) -> pd.DataFrame:
    # 3 tickers x 8 month-end dates -> a realistic [date, ticker, score, y_fwd_ret]
    # panel (the exact columns run_arm_oos emits).
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2017-01-31", periods=8, freq="ME")
    grid = pd.MultiIndex.from_product([dates, ["AAA", "BBB", "CCC"]]).to_frame(index=False)
    grid.columns = ["date", "ticker"]
    return grid.assign(
        score=rng.normal(0.0, 1.0, len(grid)),
        y_fwd_ret=rng.normal(0.0, 0.02, len(grid)),
    )


def test_save_run_with_oos_panels_round_trips(tmp_path: Path) -> None:
    panel_state = _oos_panel(seed=0)
    panel_base = _oos_panel(seed=1)
    R.save_run(
        "sig_oos", base=tmp_path,
        **_run_payload(oos_state=panel_state, oos_base=panel_base),
    )
    loaded = R.load_run("sig_oos", base=tmp_path)
    assert loaded["oos_state"] is not None
    assert loaded["oos_base"] is not None
    # the OOS score panels survive a parquet round-trip (cols + dtypes + values).
    pd.testing.assert_frame_equal(loaded["oos_state"], panel_state)
    pd.testing.assert_frame_equal(loaded["oos_base"], panel_base)
    # the additive schema-2 files exist on disk.
    d = tmp_path / "results" / "sig_oos"
    assert (d / "oos_state.parquet").exists()
    assert (d / "oos_base.parquet").exists()


def test_load_run_returns_none_when_oos_panels_absent(tmp_path: Path) -> None:
    # a schema-1 style save (no oos args) must still load, with None for the
    # additive keys -- old runs degrade gracefully, no crash.
    R.save_run("sig_no_oos", base=tmp_path, **_run_payload())
    loaded = R.load_run("sig_no_oos", base=tmp_path)
    assert loaded["oos_state"] is None
    assert loaded["oos_base"] is None
    assert loaded["ls_returns"] is None


# ---------------------------------------------------------------------------
# list_runs — scan + ledger reconciliation
# ---------------------------------------------------------------------------


def test_list_runs_empty_when_no_results(tmp_path: Path) -> None:
    assert R.list_runs(base=tmp_path) == []


def test_list_runs_picks_up_dirs_newest_first(tmp_path: Path) -> None:
    R.save_run("a", base=tmp_path, **_run_payload())
    # mutate meta ts so ordering is deterministic and newest-first.
    meta_a = json.loads((tmp_path / "results" / "a" / "meta.json").read_text())
    meta_a["ts"] = "2026-01-01T00:00:00+00:00"
    (tmp_path / "results" / "a" / "meta.json").write_text(json.dumps(meta_a))
    R.save_run("b", base=tmp_path, **_run_payload())
    meta_b = json.loads((tmp_path / "results" / "b" / "meta.json").read_text())
    meta_b["ts"] = "2026-02-01T00:00:00+00:00"
    (tmp_path / "results" / "b" / "meta.json").write_text(json.dumps(meta_b))

    runs = R.list_runs(base=tmp_path)
    assert [r["config_sig"] for r in runs] == ["b", "a"]
    assert runs[0]["mean_diff"] == pytest.approx(0.013)
    assert runs[0]["n_ic_state"] == 24
    assert runs[0]["h6_deterministic"] is True


def test_list_runs_reconciles_with_ledger(tmp_path: Path) -> None:
    R.save_run("match", base=tmp_path, **_run_payload())
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text(
        json.dumps({"ts": "2026-01-01T00:00:00+00:00", "config_sig": "match",
                    "event": "eval", "results": []}) + "\n"
        + json.dumps({"ts": "2026-02-01T00:00:00+00:00", "config_sig": "match",
                      "event": "rerun"}) + "\n"
        + json.dumps({"ts": "2026-03-01T00:00:00+00:00", "config_sig": "other",
                      "event": "eval"}) + "\n"
    )
    runs = R.list_runs(base=tmp_path, ledger=ledger)
    hit = next(r for r in runs if r["config_sig"] == "match")
    assert hit["ledger"]["n_entries"] == 2
    assert hit["ledger"]["latest_event"] == "rerun"
    assert hit["ledger"]["latest_ts"] == "2026-02-01T00:00:00+00:00"


# ---------------------------------------------------------------------------
# read_ledger — defensive parsing of the heterogeneous ledger
# ---------------------------------------------------------------------------


def test_read_ledger_skips_malformed_lines(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text(
        json.dumps({"ts": "t1", "event": "phase_b_freeze"}) + "\n"
        + "this is not json\n"
        + "\n"  # blank line
        + json.dumps({"ts": "t2", "config_sig": "abc", "results": []}) + "\n"
    )
    rows = R.read_ledger(ledger)
    assert len(rows) == 2
    assert rows[0]["event"] == "phase_b_freeze"
    assert rows[1]["config_sig"] == "abc"


def test_read_ledger_missing_file_returns_empty(tmp_path: Path) -> None:
    assert R.read_ledger(tmp_path / "nope.jsonl") == []


def test_read_ledger_reads_real_ledger_shape() -> None:
    # the project's real ledger is heterogeneous (Phase A + Phase B rows);
    # reading it must not raise and must return >0 rows.
    rows = R.read_ledger()
    assert len(rows) > 0
    # at least one Phase B event row and one Phase A eval row exist.
    assert any(r.get("event") for r in rows)
    assert any(r.get("config_sig") and r.get("results") for r in rows)


# ---------------------------------------------------------------------------
# self_test — the documented tiny smoke
# ---------------------------------------------------------------------------


def test_self_test_round_trips(tmp_path: Path) -> None:
    loaded = R.self_test(base=tmp_path)
    assert loaded["config_sig"] == "selftest0001"
    assert len(loaded["ic_state"]) == 24
    assert loaded["h6_deterministic"] is True
    assert R.list_runs(base=tmp_path)[0]["config_sig"] == "selftest0001"
