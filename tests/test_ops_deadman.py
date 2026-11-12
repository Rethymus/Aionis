"""Layer-8 marker deadman tests (round 126) — healthchecks.io Period+Grace
semantics borrowed as protocol only (BSD-3-Clause, allowlisted): Period = one
working-day evening, Grace = one working day, weekend SKIP:weekend does not
tick the clock. Pure datetime/state fixtures; the log-dir side uses tmp_path;
zero network. The staleness-check.yml mirror is verified structurally here
(YAML shape + cron) — its live run is verification-pending (billing lock #2).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import pytest
import yaml

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(_SCRIPTS))

import ops_local_refresh as lane  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
NO_LOGS = Path("Z:") / "nonexistent-deadman-fixture"  # hermetic: no run logs


def _wd(y: int, m: int, d: int, hh: int = 12) -> datetime:
    return datetime(y, m, d, hh)


def test_next_working_day_skips_weekend_only() -> None:
    fri = datetime(2026, 11, 6).date()  # a Friday
    assert lane._next_working_day(fri) == datetime(2026, 11, 9).date()  # Mon
    assert lane._next_working_day(datetime(2026, 11, 9).date()) == \
        datetime(2026, 11, 10).date()


def test_working_days_between_counts_mon_fri_only() -> None:
    fri = datetime(2026, 11, 6).date()
    mon = datetime(2026, 11, 9).date()
    wed = datetime(2026, 11, 11).date()
    assert lane._working_days_between(fri, mon) == 1  # Friday itself
    assert lane._working_days_between(fri, wed) == 3  # Fri+Mon+Tue, not Wed


def test_deadman_fresh_yesterday_passes() -> None:
    # Tuesday 2026-11-10 ok; checked Wednesday 2026-11-11 morning: today is
    # the DUE evening (not yet missed) → PASS.
    ok, detail = lane.marker_deadman(
        _wd(2026, 11, 11, 2),
        {"date": "2026-11-10", "status": "ok_committed"}, log_dir=NO_LOGS)
    assert ok and "due 2026-11-11" in detail


def test_deadman_weekend_does_not_tick() -> None:
    # Friday 2026-11-06 ok; Monday 2026-11-09 morning: due Monday (weekend
    # skipped) → PASS even though the marker is 3 calendar days old.
    ok, detail = lane.marker_deadman(
        _wd(2026, 11, 9, 2),
        {"date": "2026-11-06", "status": "ok_committed"}, log_dir=NO_LOGS)
    assert ok and "due 2026-11-09" in detail


def test_deadman_grace_day_passes_then_miss_fails() -> None:
    # Friday ok: due Monday, grace Tuesday → PASS on Tuesday...
    ok, detail = lane.marker_deadman(
        _wd(2026, 11, 10, 2), {"date": "2026-11-06", "status": "ok_committed"},
        log_dir=NO_LOGS)
    assert ok and "grace until 2026-11-10" in detail
    # ...FAIL on Wednesday with a working-day miss count.
    ok, detail = lane.marker_deadman(
        _wd(2026, 11, 11, 2), {"date": "2026-11-06", "status": "ok_committed"},
        log_dir=NO_LOGS)
    assert not ok and "missed 2 working evening(s)" in detail


def test_deadman_running_lane_pacified() -> None:
    ok, detail = lane.marker_deadman(
        _wd(2026, 11, 11, 19), {"date": "2026-11-11", "status": "running",
                                "started_at_epoch": 1.0})
    assert ok and "running" in detail


def test_deadman_no_marker_fails(tmp_path: Path) -> None:
    ok, detail = lane.marker_deadman(
        _wd(2026, 11, 11), {}, log_dir=tmp_path / "missing")
    assert not ok and "no ok_committed evening found" in detail


def test_deadman_future_marker_treated_fresh(tmp_path: Path) -> None:
    ok, detail = lane.marker_deadman(
        _wd(2026, 11, 11),
        {"date": "2026-11-12", "status": "ok_committed"},
        log_dir=tmp_path / "missing")
    assert ok and "clock skew" in detail


def test_deadman_unparseable_marker_fails(tmp_path: Path) -> None:
    # A non-date marker string reports no-marker (the honest fallback);
    # the unparseable branch is reached via a regex-shaped invalid date
    # (e.g. month 13) coming from a log or the marker itself.
    ok, detail = lane.marker_deadman(
        _wd(2026, 11, 11),
        {"date": "not-a-date", "status": "ok_committed"},
        log_dir=tmp_path / "missing")
    assert not ok and "no ok_committed evening found" in detail
    ok, detail = lane.marker_deadman(
        _wd(2026, 11, 11),
        {"date": "2026-13-45", "status": "ok_committed"},
        log_dir=tmp_path / "missing")
    assert not ok and "unparseable" in detail


def _seed_log(log_dir: Path, day: str, status: str = "ok_committed") -> None:
    d = log_dir / day
    d.mkdir(parents=True)
    summary = {"date": day, "status": status}
    (d / "run.log").write_text(
        f"[21:00:00] SUMMARY {json.dumps(summary, ensure_ascii=False)}\n",
        encoding="utf-8")


def test_last_ok_from_logs_survives_later_failed_evening(
        tmp_path: Path) -> None:
    """A later FAILED evening must not hide the last success (the deadman
    measures data freshness, not attempt health — spin is layer 4's job)."""
    log_dir = tmp_path / "runs" / "ops_local_refresh"
    _seed_log(log_dir, "2026-11-06", "ok_committed")
    _seed_log(log_dir, "2026-11-09", "failed")
    ok, detail = lane.marker_deadman(
        _wd(2026, 11, 10, 2), {"date": "2026-11-09", "status": "failed"},
        log_dir=log_dir)
    assert ok and "last ok_committed 2026-11-06" in detail


def test_last_ok_falls_back_to_marker_without_logs(tmp_path: Path) -> None:
    missing = tmp_path / "runs" / "ops_local_refresh"  # does not exist
    ok, detail = lane.marker_deadman(
        _wd(2026, 11, 10, 2), {"date": "2026-11-09", "status": "ok_committed"},
        log_dir=missing)
    assert ok and "last ok_committed 2026-11-09" in detail


def test_collect_layers_carries_layer_8(monkeypatch, tmp_path: Path) -> None:
    """The layer is wired into collect_layers with the 8/9 name (layer 8 of
    9 since the round-133 layer 9 env-lock drift; mocked subprocess layers +
    fresh same-day log so every layer passes)."""
    def _ok(args, **k):
        return __import__("subprocess").CompletedProcess(args, 0, "gh ok", "")

    monkeypatch.setattr(lane, "subprocess", type("S", (), {"run": staticmethod(_ok)}))
    monkeypatch.setattr(lane, "IS_WINDOWS", False)
    # Fixture date must be TODAY-relative: the deadman compares the seeded
    # log's ok_committed evening against the real clock (Period+Grace), so a
    # hardcoded day rots once grace passes (2026-11-10 seeded rotted on
    # 2026-11-13 — caught while syncing layer-9 pins, proven pre-existing at
    # HEAD via stash).
    today = datetime.now().strftime("%Y-%m-%d")
    monkeypatch.setattr(lane, "load_state",
                        lambda: {"date": today,
                                 "status": "ok_committed"})
    log_dir = tmp_path / "logs"
    _seed_log(log_dir, today)
    monkeypatch.setattr(lane, "LOG_DIR", log_dir)
    monkeypatch.setattr(lane, "_site_repo_drift_check",
                        lambda: (True, "mocked drift layer"))
    layers = lane.collect_layers()
    assert layers[-2][0] == "8/9 evening marker deadman"
    assert layers[-2][1] is True
    assert layers[-1][0] == "9/9 env-lock drift"


# ------------------------------------------------- staleness-check.yml mirror

@pytest.fixture(scope="module")
def workflow() -> dict:
    text = (ROOT / ".github" / "workflows" / "staleness-check.yml").read_text(
        encoding="utf-8")
    return yaml.safe_load(text)


def test_workflow_daily_cron_and_deadman_job(workflow: dict) -> None:
    # YAML 1.1: bare `on:` parses as boolean True under pyyaml — accept both.
    on = workflow[True] if True in workflow else workflow["on"]
    crons = on["schedule"]
    assert crons == [{"cron": "37 2 * * *"}]  # daily, off the hour
    assert "marker-deadman" in workflow["jobs"]
    assert set(workflow["jobs"]) == {"marker-deadman", "check"}


def test_workflow_deadman_pins_ubuntu_and_token(workflow: dict) -> None:
    job = workflow["jobs"]["marker-deadman"]
    assert job["runs-on"] == "ubuntu-24.04"
    step = job["steps"][0]
    assert step["env"]["GH_TOKEN"] == "${{ secrets.GITHUB_TOKEN }}"


def test_workflow_deadman_semantics_verbatim(workflow: dict) -> None:
    """The mirror implements the SAME rule as layer 8: lane-commit grep, a
    Mon-Fri clock, next_working_day grace — pinned by source text so a
    silent semantic drift cannot slip through a YAML-only review."""
    raw = (ROOT / ".github" / "workflows" / "staleness-check.yml").read_text(
        encoding="utf-8")
    for token in ('startswith("chore(data): evening terminal refresh")',
                  "weekday() >= 5", "next_working_day(last)",
                  "VERIFICATION-PENDING", "per_page=30"):
        assert token in raw, token
