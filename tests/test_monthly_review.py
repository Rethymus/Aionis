"""Hermetic tests for the monthly-review collector (scripts/monthly_review.py).

The 6th-of-month review used to be gathered by an LLM reading run logs by
eye; this locks the deterministic replacement. Pure tmp_path fixtures for the
run.log/markers side; the gh CLI is injected as a fake runner — zero network,
zero subprocess.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(_SCRIPTS))

import monthly_review as mr  # noqa: E402


def _summary_line(**kw) -> str:
    """A run.log SUMMARY line exactly as ops_local_refresh.log() writes it."""
    base = {"date": "2026-09-10", "status": "ok_committed", "commit": "a" * 40,
            "pushed": True, "n_files": 58, "soft_fails": [],
            "ledger": "discarded-display-appends",
            "ci": {"Publish site (gh-pages)": "success", "Tests": "success"},
            "backup": "ok", "persistent_soft_fails": [], "wall_minutes": 84.2}
    base.update(kw)
    return f"[21:38:59] SUMMARY {json.dumps(base, ensure_ascii=False)}"


def _write_day(repo: Path, day: str, lines: list[str]) -> None:
    d = repo / "runs" / "ops_local_refresh" / day
    d.mkdir(parents=True)
    (d / "run.log").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _fake_gh(rows_by_wf: dict[str, list[dict]], fail: str | None = None):
    """Injectable gh runner: per-workflow rows, optional broken workflow."""
    def runner(workflow: str, repo: Path) -> tuple[int, str, str]:
        if workflow == fail:
            return 1, "", "gh: auth error"
        return 0, json.dumps(rows_by_wf.get(workflow, [])), ""
    return runner


# --- summary parsing ------------------------------------------------------------


def test_summary_payload_parses_timestamp_prefixed_line() -> None:
    payload = mr.summary_payload(_summary_line())
    assert payload is not None
    assert json.loads(payload)["status"] == "ok_committed"


def test_summary_payload_rejects_non_summary_lines() -> None:
    assert mr.summary_payload("[19:04:55] HARD-FAIL: boom") is None
    assert mr.summary_payload("STEP cot_fetch: OK (3.2m)") is None
    # a step-output tail that merely CONTAINS the word SUMMARY must not parse
    assert mr.summary_payload(
        "[19:04:55] STEP x: FAIL tail: SUMMARY {not real json}") is None


def test_default_month_is_previous_month() -> None:
    from datetime import date

    assert mr.default_month(date(2026, 10, 6)) == "2026-09"
    assert mr.default_month(date(2026, 1, 15)) == "2025-12"
    assert mr.default_month(date(2026, 10, 29)) == "2026-09"


# --- collection 1: run.log aggregation -------------------------------------------


def test_collect_filters_month_and_aggregates_fields(tmp_path: Path) -> None:
    repo = tmp_path
    _write_day(repo, "2026-09-10", [
        "[19:04:55] STEP cot_fetch: FAIL (9.9m) timeout",
        _summary_line(status="ok_committed", wall_minutes=91.5, n_files=57,
                      soft_fails=["news_feed_fetch [local superset]",
                                  "reddit_fetch"]),
    ])
    _write_day(repo, "2026-09-11", [_summary_line(date="2026-09-11",
                                                  wall_minutes=60.0)])
    _write_day(repo, "2026-10-01", [_summary_line(date="2026-10-01")])  # other month
    errors: list[str] = []
    days, push_only = mr.collect_log_days(repo, "2026-09", errors)
    assert [d["date"] for d in days] == ["2026-09-10", "2026-09-11"]
    assert push_only == 0
    assert errors == []
    d10 = days[0]
    assert d10["status"] == "ok_committed"
    assert d10["wall_minutes"] == 91.5
    assert d10["n_files"] == 57
    assert d10["soft_fails"] == ["news_feed_fetch [local superset]", "reddit_fetch"]
    assert d10["ci"] == {"Publish site (gh-pages)": "success", "Tests": "success"}
    assert days[1]["wall_minutes"] == 60.0


def test_collect_counts_push_only_recovery_and_flags_day(tmp_path: Path) -> None:
    repo = tmp_path
    # real-shape recovery summary: no n_files / no ci
    _write_day(repo, "2026-09-25", [_summary_line(
        date="2026-09-25", status="ok_committed", push_only_recovery=True,
        n_files=None, ci=None, soft_fails=[], wall_minutes=0.1)])
    _write_day(repo, "2026-09-26", [_summary_line(date="2026-09-26")])
    errors: list[str] = []
    days, push_only = mr.collect_log_days(repo, "2026-09", errors)
    assert push_only == 1
    assert days[0]["push_only_recovery"] is True
    assert days[0]["n_files"] is None
    assert days[0]["ci"] is None
    assert days[1]["push_only_recovery"] is False


def test_collect_retry_soft_never_clobbers_primary_summary(tmp_path: Path) -> None:
    repo = tmp_path
    _write_day(repo, "2026-09-27", [
        _summary_line(date="2026-09-27", wall_minutes=88.0, soft_fails=["bts_tsi_fetch"]),
        # retry-soft pass later that evening: no date, no wall_minutes
        _summary_line(date=None, retry_soft=True, status="ok_committed",
                      wall_minutes=None, soft_fails=[], n_files=58),
    ])
    errors: list[str] = []
    days, _ = mr.collect_log_days(repo, "2026-09", errors)
    assert len(days) == 1
    assert days[0]["wall_minutes"] == 88.0  # primary kept
    assert days[0]["soft_fails"] == ["bts_tsi_fetch"]
    assert days[0]["retry_soft_residual"] == []


def test_collect_date_falls_back_to_directory_name(tmp_path: Path) -> None:
    repo = tmp_path
    # a retry-soft-only day (no date field in its SUMMARY)
    _write_day(repo, "2026-09-28", [_summary_line(
        date=None, retry_soft=True, status="ok_committed", n_files=12,
        soft_fails=["cot_fetch"])])
    errors: list[str] = []
    days, _ = mr.collect_log_days(repo, "2026-09", errors)
    assert [d["date"] for d in days] == ["2026-09-28"]
    assert days[0]["status"] == "ok_committed"
    assert days[0]["n_files"] == 12


def test_collect_cross_midnight_summary_belongs_to_its_own_date(tmp_path: Path) -> None:
    repo = tmp_path
    # run started 09-30, finished after midnight: SUMMARY dated 10-01 lives in
    # the 09-30 directory and must aggregate under 10-01, not 09-30
    _write_day(repo, "2026-09-30", [_summary_line(date="2026-10-01")])
    sep_errors: list[str] = []
    oct_errors: list[str] = []
    sep_days, _ = mr.collect_log_days(repo, "2026-09", sep_errors)
    oct_days, _ = mr.collect_log_days(repo, "2026-10", oct_errors)
    assert sep_days == []
    assert [d["date"] for d in oct_days] == ["2026-10-01"]


def test_collect_records_corrupt_summary_as_anomaly(tmp_path: Path) -> None:
    repo = tmp_path
    _write_day(repo, "2026-09-15", [
        _summary_line(date="2026-09-15"),
        "[20:00:00] SUMMARY {truncated json",
    ])
    errors: list[str] = []
    days, _ = mr.collect_log_days(repo, "2026-09", errors)
    assert len(days) == 1  # the good summary still aggregates
    assert len(errors) == 1
    assert "truncated SUMMARY" in errors[0]


def test_collect_tolerates_missing_log_root(tmp_path: Path) -> None:
    errors: list[str] = []
    days, push_only = mr.collect_log_days(tmp_path, "2026-09", errors)
    assert days == [] and push_only == 0 and errors == []


def test_missing_weekdays_enumerates_only_missing_weekdays() -> None:
    # 2026-09: 09-07 (Mon) collected; 09-10 (Thu) missed; weekends never listed
    got = mr.missing_weekdays("2026-09", {"2026-09-07"})
    assert "2026-09-10" in got
    assert "2026-09-12" not in got and "2026-09-13" not in got  # Sat/Sun
    assert all(got.count(d) == 1 for d in got)


# --- collection 2: gh (injected runner, no subprocess) ----------------------------


def test_collect_gh_counts_success_failure_and_month_scopes(tmp_path: Path) -> None:
    rows = [
        {"conclusion": "success", "createdAt": "2026-09-15T13:04:55Z"},
        {"conclusion": "failure", "createdAt": "2026-09-11T13:04:55Z"},
        {"conclusion": "success", "createdAt": "2026-10-02T13:04:55Z"},  # next month
        {"conclusion": "cancelled", "createdAt": "2026-09-20T13:04:55Z"},
    ]
    counts = mr.collect_gh("publish-site.yml", "2026-09", tmp_path,
                           runner=_fake_gh({"publish-site.yml": rows}))
    assert counts["ok"] is True
    assert counts["month_success"] == 1
    assert counts["month_failure"] == 1
    assert counts["success"] == 2
    assert counts["failure"] == 1
    assert counts["other"] == 1


def test_collect_gh_offline_is_reported_not_raised(tmp_path: Path) -> None:
    def runner(workflow: str, repo: Path) -> tuple[int, str, str]:
        raise FileNotFoundError("gh not installed")

    counts = mr.collect_gh("ci.yml", "2026-09", tmp_path, runner=runner)
    assert counts["ok"] is False
    assert "gh not installed" in counts["error"]
    assert counts.get("success", 0) == 0


def test_collect_gh_nonzero_exit_is_reported_not_counted(tmp_path: Path) -> None:
    counts = mr.collect_gh("ci.yml", "2026-09", tmp_path,
                           runner=_fake_gh({}, fail="ci.yml"))
    assert counts["ok"] is False
    assert "auth error" in counts["error"]


def test_collect_gh_unparseable_json_is_reported(tmp_path: Path) -> None:
    def runner(workflow: str, repo: Path) -> tuple[int, str, str]:
        return 0, "<html>not json</html>", ""

    counts = mr.collect_gh("publish-site.yml", "2026-09", tmp_path, runner=runner)
    assert counts["ok"] is False
    assert "unparseable" in counts["error"]


# --- collection 3: data_health.json -----------------------------------------------


def test_collect_health_present_and_absent(tmp_path: Path) -> None:
    errors: list[str] = []
    assert mr.collect_health(tmp_path, errors) is None
    assert errors == []
    health_dir = tmp_path / "web" / "src" / "data" / "aionis"
    health_dir.mkdir(parents=True)
    (health_dir / "data_health.json").write_text(json.dumps({
        "status": "ok", "snapshot_ts": "2026-10-28T12:07:59+00:00",
        "summary": {"n_panels": 56, "n_frozen": 20, "n_daily": 25,
                    "n_cadence": 11}}), encoding="utf-8")
    health = mr.collect_health(tmp_path, errors)
    assert health is not None
    assert health["snapshot_ts"] == "2026-10-28T12:07:59+00:00"
    assert health["summary"]["n_panels"] == 56
    assert errors == []


def test_collect_health_corrupt_existing_file_is_anomaly(tmp_path: Path) -> None:
    health_dir = tmp_path / "web" / "src" / "data" / "aionis"
    health_dir.mkdir(parents=True)
    (health_dir / "data_health.json").write_text("{not json", encoding="utf-8")
    errors: list[str] = []
    assert mr.collect_health(tmp_path, errors) is None
    assert len(errors) == 1 and "unreadable" in errors[0]


# --- markdown rendering -----------------------------------------------------------


def _sample_days() -> list[dict]:
    return [
        mr._blank_day("2026-09-10") | {
            "status": "ok_committed", "wall_minutes": 91.5, "n_files": 57,
            "soft_fails": ["news_feed_fetch [local superset]"],
            "ci": {"Publish site (gh-pages)": "success", "Tests": "success"}},
        mr._blank_day("2026-09-25") | {
            "status": "ok_committed", "wall_minutes": 0.1, "n_files": None,
            "push_only_recovery": True, "ci": None},
    ]


def test_render_execution_table_and_no_fabricated_rows() -> None:
    md = mr.render("2026-09", _sample_days(), 1, {}, None, [], "2026-10-06T23:00")
    assert ("| 2026-09-10 | ok_committed | 91.5 | 1: news_feed_fetch "
            "[local superset] | 57 | — | success/success |" in md)
    # recovery row: no n_files, no ci — dashes, never invented values
    assert "| 2026-09-25 | ok_committed | 0.1 | 0 | — | yes | — |" in md
    assert "Evenings with a SUMMARY: **2**" in md
    assert "2026-09-11" in md  # a missing weekday is enumerated as absent


def test_render_gh_unverified_verbatim() -> None:
    gh = {"publish-site.yml": {"ok": True, "success": 30, "failure": 2,
                               "month_success": 12, "month_failure": 0,
                               "other": 0, "rows": 32},
          "ci.yml": {"ok": False, "error": "gh: auth error"}}
    md = mr.render("2026-09", _sample_days(), 1, gh, None, [], "t")
    assert "| publish-site.yml | 12 | 0 | 30 | 2 |" in md
    assert "未能核对" in md
    assert "gh: auth error" in md
    assert "aged past the sampling limit" not in md  # month IS in the window


def test_render_flags_aged_out_gh_window() -> None:
    gh = {"publish-site.yml": {"ok": True, "success": 60, "failure": 0,
                               "month_success": 0, "month_failure": 0,
                               "other": 0, "rows": 60},
          "ci.yml": {"ok": True, "success": 58, "failure": 2,
                     "month_success": 0, "month_failure": 0,
                     "other": 0, "rows": 60}}
    md = mr.render("2026-09", _sample_days(), 0, gh, None, [], "t")
    # both windows hold rows but none from the month — must be said, not
    # silently read as "the month had zero runs"
    assert md.count("aged past the sampling limit") == 2


def test_render_health_and_trend_sections() -> None:
    health = {"snapshot_ts": "2026-09-30T12:00:00+00:00",
              "summary": {"n_panels": 55, "n_frozen": 20}}
    md = mr.render("2026-09", _sample_days(), 1, {}, health, [], "t")
    assert "snapshot_ts: 2026-09-30T12:00:00+00:00" in md
    assert "n_frozen=20, n_panels=55" in md
    assert "push_only_recovery fired 1 time(s)" in md
    assert "news_feed_fetch [local superset]: 1 evening(s)" in md
    assert "avg 45.8" in md  # (91.5 + 0.1) / 2


def test_render_internal_anomalies_section() -> None:
    md = mr.render("2026-09", _sample_days(), 0, {}, None,
                   ["x/run.log:2: corrupt SUMMARY JSON: {}"], "t")
    assert "## Internal anomalies" in md
    assert "corrupt SUMMARY JSON" in md


# --- main wiring (exit codes + --out; gh injected) --------------------------------


def test_main_exit_zero_with_data_and_writes_out(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_day(repo, "2026-09-10", [_summary_line(date="2026-09-10")])
    monkeypatch.setattr(mr, "gh_run_list",
                        lambda wf, r: (0, json.dumps([
                            {"conclusion": "success",
                             "createdAt": "2026-09-10T13:00:00Z"}]), ""))
    out = tmp_path / "report.md"
    rc = mr.main(["--month", "2026-09", "--repo", str(repo), "--out", str(out)])
    assert rc == 0
    md = out.read_text(encoding="utf-8")
    assert "# Monthly review data collection — evening lane (2026-09)" in md
    assert "| 2026-09-10 |" in md
    assert "| publish-site.yml | 1 | 0 | 1 | 0 |" in md
    # stdout stays clean when --out is used
    assert "wrote" in capsys.readouterr().err


def test_main_exit_one_when_no_summaries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "empty"
    repo.mkdir()
    monkeypatch.setattr(mr, "gh_run_list", lambda wf, r: (0, "[]", ""))
    assert mr.main(["--month", "2026-09", "--repo", str(repo)]) == 1


def test_main_exit_one_on_internal_anomaly_despite_good_summary(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_day(repo, "2026-09-10", [
        _summary_line(date="2026-09-10"),
        "[20:00:00] SUMMARY {broken",
    ])
    health_dir = repo / "web" / "src" / "data" / "aionis"
    health_dir.mkdir(parents=True)
    (health_dir / "data_health.json").write_text("{oops", encoding="utf-8")
    monkeypatch.setattr(mr, "gh_run_list", lambda wf, r: (0, "[]", ""))
    # gh being broken must NOT cause exit 1; the two real anomalies must
    rc = mr.main(["--month", "2026-09", "--repo", str(repo),
                  "--out", str(tmp_path / "r.md")])
    assert rc == 1
    md = (tmp_path / "r.md").read_text(encoding="utf-8")
    assert "truncated SUMMARY" in md
    assert "unreadable" in md


def test_main_gh_offline_still_exits_zero_with_data(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_day(repo, "2026-09-10", [_summary_line(date="2026-09-10")])

    def offline(wf: str, r: Path) -> tuple[int, str, str]:
        raise FileNotFoundError("no gh")

    monkeypatch.setattr(mr, "gh_run_list", offline)
    rc = mr.main(["--month", "2026-09", "--repo", str(repo),
                  "--out", str(tmp_path / "r.md")])
    assert rc == 0
    assert "未能核对" in (tmp_path / "r.md").read_text(encoding="utf-8")


def test_main_rejects_bad_month(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc:
        mr.main(["--month", "2026-13", "--repo", str(tmp_path)])
    assert exc.value.code == 2  # argparse error
