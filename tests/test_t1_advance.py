"""Hermetic tests for the T1 月级推进器 (scripts/t1_advance.py).

Pure-function pins per the t1-advance-formalize task: plan generation /
plan parsing / progress scanning (advance 目录月记录 vs 计划) / breakpoint
(next-pending) determination / semantic exit codes of the advance core with
an INJECTED engine invoker (zero network, zero subprocess). The tmp advance
roots hold labeled fixtures shaped like real run dirs — never research data.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(_SCRIPTS))

import t1_advance as ta  # noqa: E402

# ---------------------------------------------------------------------------
# plan generation / parsing
# ---------------------------------------------------------------------------

def test_plan_months_generation_including_year_rollover():
    months = ta.plan_months("2016-01", "2017-03")
    assert months[0] == "2016-01" and months[-1] == "2017-03"
    assert len(months) == 15
    assert months[11] == "2016-12" and months[12] == "2017-01"
    assert ta.plan_months("2016-01", "2016-01") == ["2016-01"]


def test_plan_months_rejects_bad_window():
    with pytest.raises(ta.AdvanceError) as ei:
        ta.plan_months("2016-1", "2016-12")
    assert ei.value.exit_code == ta.EXIT_USAGE
    with pytest.raises(ta.AdvanceError):
        ta.plan_months("2016-03", "2016-01")  # reversed


def test_parse_plan_tolerates_blank_lines_and_validates():
    text = "2016-01\n\n2016-02\n  2016-03  \n\n"
    assert ta.parse_plan(text) == ["2016-01", "2016-02", "2016-03"]


@pytest.mark.parametrize("text", [
    "2016-01\n2016-01\n",        # duplicate months
    "2016-02\n2016-01\n",        # unsorted
    "2016-01\nFeb-2016\n",       # non-month line
    "\n \n",                     # empty
])
def test_parse_plan_rejects_invalid(text):
    with pytest.raises(ta.AdvanceError) as ei:
        ta.parse_plan(text)
    assert ei.value.exit_code == ta.EXIT_USAGE


def test_check_plan_against_config_mismatch(tmp_path: Path):
    cfg = tmp_path / "config-frozen.json"
    cfg.write_text(json.dumps({
        "kind": "replay-blackbox-config-frozen", "exploratory": True,
        "windows": {"training": {"from": "2016-01", "to": "2016-02"}},
    }), encoding="utf-8")
    ta.check_plan_against_config(["2016-01", "2016-02"], cfg)  # match → ok
    with pytest.raises(ta.AdvanceError) as ei:
        ta.check_plan_against_config(["2016-01", "2016-02", "2016-03"], cfg)
    assert ei.value.exit_code == ta.EXIT_PLAN_MISMATCH


# ---------------------------------------------------------------------------
# progress scanning + breakpoint determination
# ---------------------------------------------------------------------------

def _mk_run_dir(root: Path, name: str, months: list[str] | None) -> Path:
    d = root / name
    d.mkdir(parents=True)
    lines = [json.dumps({"_header": {"kind": "replay-month-records"}})]
    for m in months or []:
        lines.append(json.dumps({"month": m, "tier": "t1", "p": 0.5, "y": 0}))
    (d / "month-records.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return d


def test_scan_progress_counts_only_dirs_with_month_records(tmp_path: Path):
    root = tmp_path / "t1-monthly-advance"
    _mk_run_dir(root, "20261117-100000-t1", ["2016-01"])
    _mk_run_dir(root, "20261117-100100-t1", None)   # header-only honest breakpoint
    _mk_run_dir(root, "20261117-100200-t1", ["2016-02"])
    (root / "not-a-run-dir").mkdir()                # ignored by name
    progress = ta.scan_progress(root)
    assert set(progress) == {"2016-01", "2016-02"}
    assert progress["2016-01"] == ["20261117-100000-t1"]


def test_scan_progress_missing_root_and_corrupt_lines(tmp_path: Path):
    assert ta.scan_progress(tmp_path / "absent") == {}
    root = tmp_path / "adv"
    d = root / "20261117-100000-t1"
    d.mkdir(parents=True)
    (d / "month-records.jsonl").write_text(
        "{not json}\n" + json.dumps({"month": "2016-01"}) + "\n", encoding="utf-8")
    assert ta.scan_progress(root) == {"2016-01": ["20261117-100000-t1"]}


def test_next_pending_keeps_plan_order_and_picks_first_gap():
    plan = ["2016-01", "2016-02", "2016-03", "2016-04"]
    progress = {"2016-01": ["a-t1"], "2016-04": ["b-t1"]}
    assert ta.next_pending(plan, progress) == ["2016-02", "2016-03"]
    assert not ta.is_complete(plan, progress)
    assert ta.is_complete(plan, {"2016-01": ["a"], "2016-02": ["b"],
                                 "2016-03": ["c"], "2016-04": ["d"]})


def test_next_pending_duplicate_successes_listed_not_deduped(tmp_path: Path):
    root = tmp_path / "adv"
    _mk_run_dir(root, "20261117-100000-t1", ["2016-01"])
    _mk_run_dir(root, "20261117-100500-t1", ["2016-01"])
    progress = ta.scan_progress(root)
    assert progress["2016-01"] == ["20261117-100000-t1", "20261117-100500-t1"]
    assert ta.next_pending(["2016-01", "2016-02"], progress) == ["2016-02"]


# ---------------------------------------------------------------------------
# advance core exit-code semantics (injected invoker — zero subprocess)
# ---------------------------------------------------------------------------

def test_run_advance_all_success_exit0():
    result = ta.run_advance(["2016-01", "2016-02"], lambda m: 0)
    assert result["exit_code"] == ta.EXIT_OK
    assert result["advanced"] == ["2016-01", "2016-02"]
    assert result["failed"] is None


def test_run_advance_immediate_failure_exit2_zero_progress():
    calls: list[str] = []

    def invoke(m):
        calls.append(m)
        return 6  # engine exit 6 (contract failure) — window exhausted

    result = ta.run_advance(["2016-01", "2016-02"], invoke)
    assert result["exit_code"] == ta.EXIT_WINDOW
    assert result["advanced"] == [] and result["failed"] == "2016-01"
    assert result["engine_exit"] == 6 and calls == ["2016-01"]  # stopped at once


def test_run_advance_progress_then_failure_exit2_with_partial_note():
    def invoke(m):
        return 0 if m == "2016-01" else 1

    result = ta.run_advance(["2016-01", "2016-02", "2016-03"], invoke)
    assert result["exit_code"] == ta.EXIT_WINDOW
    assert result["advanced"] == ["2016-01"]
    assert result["failed"] == "2016-02" and result["engine_exit"] == 1


def test_run_advance_stop_after_budget_exit1():
    result = ta.run_advance(["2016-01", "2016-02", "2016-03"], lambda m: 0,
                            stop_after=2)
    assert result["exit_code"] == ta.EXIT_PARTIAL
    assert result["advanced"] == ["2016-01", "2016-02"]
    assert result["stop_reason"] == "stop-after budget"


# ---------------------------------------------------------------------------
# main() read-only paths (tmp plan + fake frozen config + fake advance root)
# ---------------------------------------------------------------------------

def _fake_env(tmp_path: Path, plan_months_list: list[str], done: list[str]):
    plan = tmp_path / "plan.txt"
    plan.write_text("\n".join(plan_months_list) + "\n", encoding="utf-8")
    cfg = tmp_path / "config-frozen.json"
    cfg.write_text(json.dumps({
        "kind": "replay-blackbox-config-frozen", "exploratory": True,
        "windows": {"training": {"from": plan_months_list[0],
                                 "to": plan_months_list[-1]}},
    }), encoding="utf-8")
    adv = tmp_path / "advance"
    if done:
        _mk_run_dir(adv, "20261117-100000-t1", done)
    return plan, cfg, adv


def test_main_status_readonly_counts_and_breakpoint(tmp_path, capsys):
    plan, cfg, adv = _fake_env(tmp_path, ["2016-01", "2016-02", "2016-03"],
                               done=["2016-01"])
    rc = ta.main(["--status", "--plan", str(plan), "--config", str(cfg),
                  "--advance-root", str(adv)])
    out = capsys.readouterr().out
    assert rc == ta.EXIT_OK
    assert "1/3 months have records" in out
    assert "next month (breakpoint): 2016-02" in out
    assert ta.EXPLORATORY_LABEL in out


def test_main_status_complete_plan(tmp_path, capsys):
    plan, cfg, adv = _fake_env(tmp_path, ["2016-01", "2016-02"],
                               done=["2016-01", "2016-02"])
    rc = ta.main(["--status", "--plan", str(plan), "--config", str(cfg),
                  "--advance-root", str(adv)])
    out = capsys.readouterr().out
    assert rc == ta.EXIT_OK
    assert "COMPLETE" in out and "2/2 months" in out


def test_main_rejects_missing_plan_exit3(tmp_path):
    rc = ta.main(["--status", "--plan", str(tmp_path / "nope.txt"),
                  "--config", str(tmp_path / "c.json")])
    assert rc == ta.EXIT_USAGE
