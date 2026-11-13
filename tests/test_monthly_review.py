"""Hermetic tests for the monthly-review collector (scripts/monthly_review.py).

The 6th-of-month review used to be gathered by an LLM reading run logs by
eye; this locks the deterministic replacement. Pure tmp_path fixtures for the
run.log/markers side; the gh CLI is injected as a fake runner — zero network.
One exception (flywheel-rehearsal, 2026-11-13): a single subprocess-based pin
re-runs THIS CLI under a GBK child environment (python -I, PYTHONIOENCODING/
PYTHONUTF8 stripped) to lock the __main__ stdout+stderr reconfigure — the
U+2212/U+00B2 literals it must survive are byte-locked elsewhere in this file.
"""
from __future__ import annotations

import json
import os
import subprocess
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


# ---------------------------------------------------------------------------
# Round 137 — calibration aggregator (training-method ring 1a; design report
# reports/design/2026-11-14-personal-training-method-and-automation-ladder.md
# §2). All fixtures below are HERMETIC TEST FIXTURES (labeled synthetic text —
# never a real backlog file, per the no-mock-data-in-pipeline rule; this is
# the ops presentation lane, and these pin rendering, not research data).
# ---------------------------------------------------------------------------


def _prediction_backlog_text() -> str:
    """Synthetic backlog text covering every reconcile row type: resolved
    p>0.6 (band marker), resolved boundary p=0.6/p=0.5, resolved p<0.5,
    p-missing, pending not-yet-due, pending overdue."""
    return "\n".join([
        "- A（prediction: 通道零软败（p=0.8）due=2026-10）",
        "  - outcome: y=1 (2026-10-31)",
        "- B（prediction: 高带测试（p=0.9）due=2026-10）",
        "  - outcome: y=0 (2026-10-30)",
        "- C（prediction: 中带（p=0.6）due=2026-10）",
        "  - outcome: y=1 (2026-10-29)",
        "- D（prediction: 半带（p=0.5）due=2026-10）",
        "  - outcome: y=0 (2026-10-28)",
        "- E（prediction: 反带（p=0.3）due=2026-10）",
        "  - outcome: y=0 (2026-10-27)",
        "- F（prediction: 待填（p=待月末）due=2026-10）",
        "  - outcome: y=1 (2026-10-26)",
        "- G（prediction: 未到对账（p=0.7）due=2026-11）",
        "- H（prediction: 已过期未记（p=0.65）due=2026-09）",
    ])


def test_reconcile_rendering_byte_identical_after_ring1a_lift() -> None:
    """Ring 1a lifted the parse loop into _collect_prediction_records; the
    per-row reconciliation output is pinned BYTE-FOR-BYTE to the pre-refactor
    rendering (captured from HEAD 9c498a54cb before the edit — this is the
    FIRST reconcile pin; none existed before ring 1a)."""
    expected = [
        "prediction resolved: 通道零软败（judgments: p=0.8；facts: y=1；"
        "(p−y)²=0.040, 命中）；高带 p>0.6——仅自动进入对账候选呈现，无任何自动处置",
        "prediction resolved: 高带测试（judgments: p=0.9；facts: y=0；"
        "(p−y)²=0.810, 未命中）；高带 p>0.6——仅自动进入对账候选呈现，无任何自动处置",
        "prediction resolved: 中带（judgments: p=0.6；facts: y=1；(p−y)²=0.160, 命中）",
        "prediction resolved: 半带（judgments: p=0.5；facts: y=0；(p−y)²=0.250, 未命中）",
        "prediction resolved: 反带（judgments: p=0.3；facts: y=0；(p−y)²=0.090, 命中）",
        "prediction 未填 p（judgments: 无——诚实缺省，待月末会话；facts: due=2026-10）: 待填",
        "prediction pending outcome: 未到对账（judgments: p=0.7；facts: "
        "due=2026-11、outcome 未记）；高带 p>0.6——仅自动进入对账候选呈现，无任何自动处置",
        "prediction pending outcome: 已过期未记（judgments: p=0.65；facts: "
        "due=2026-09、outcome 未记（due 已过））；高带 "
        "p>0.6——仅自动进入对账候选呈现，无任何自动处置",
    ]
    assert mr.reconcile_predictions(_prediction_backlog_text(),
                                    "2026-10") == expected


def test_calibration_summary_empty_account_is_single_honest_line() -> None:
    assert mr.calibration_bucket_summary([]) == [
        "none yet (baseline collection month)"]
    pending_only = mr._collect_prediction_records(
        "- G（prediction: 未到对账（p=0.7）due=2026-11）")
    assert mr.calibration_bucket_summary(pending_only) == [
        "none yet (baseline collection month)"]


def test_calibration_summary_one_of_one_wide_wilson_ci() -> None:
    """n=1 → Wilson 95% CI (0.2065, 1.0000): the wide CI IS the
    'small-sample forbids threshold fitting' anchor made quantitative
    (statsmodels proportion_confint(1, 1, method='wilson'))."""
    records = mr._collect_prediction_records(
        "- Z（prediction: 单条（p=0.8）due=2026-10）\n"
        "  - outcome: y=1 (2026-10-31)")
    out = "\n".join(mr.calibration_bucket_summary(records))
    assert "p∈[0.8,0.9): n=1、命中 1（1.000）、Wilson 95% CI (0.2065, 1.0000)" in out
    assert "汇总 mean Brier = 0.040（n=1" in out


def test_calibration_summary_bucket_edges_and_separation() -> None:
    """0.5 ∈ [0.5,0.6); 0.6 ∈ [0.6,0.7) (left-closed half-open — the design
    pinned boundary); p=0.7 pending and 0.65 pending NEVER bucket; p<0.5 /
    p-missing listed separately; summary mean Brier = per-row mean over all
    resolved rows (0.04+0.81+0.16+0.25+0.09)/5 = 0.270."""
    records = mr._collect_prediction_records(_prediction_backlog_text())
    out = "\n".join(mr.calibration_bucket_summary(records))
    assert "p∈[0.5,0.6): n=1、命中 0（0.000）" in out
    assert "p∈[0.6,0.7): n=1、命中 1（1.000）" in out
    assert "p∈[0.8,0.9): n=1" in out
    assert "p∈[0.9,1.0]: n=1、命中 0（0.000）" in out
    assert "p∈[0.7,0.8)" not in out  # the only p=0.7 row is pending
    assert "分列不计桶：p<0.5 已对账 1 条（命中 1）、p 未填 1 条、pending 未对账 2 条" in out
    assert "汇总 mean Brier = 0.270（n=5，与逐条 (p−y)² 同口径取均值）" in out


def test_calibration_summary_top_bucket_closed_at_one() -> None:
    records = mr._collect_prediction_records(
        "- Z（prediction: 满格（p=1.0）due=2026-10）\n"
        "  - outcome: y=1 (2026-10-31)")
    out = "\n".join(mr.calibration_bucket_summary(records))
    assert "p∈[0.9,1.0]: n=1、命中 1（1.000）、Wilson 95% CI (0.2065, 1.0000)" in out


def test_calibration_summary_three_of_five_wilson_anchor() -> None:
    """3/5 → Wilson 95% CI (0.2307, 0.8824) — pins the design-report §1
    statsmodels anchor into the rendered bucket line."""
    ys = [1, 1, 1, 0, 0]
    text = "\n".join(
        f"- R{i}（prediction: 第{i}条（p=0.7）due=2026-10）\n"
        f"  - outcome: y={y} (2026-10-2{i})" for i, y in enumerate(ys))
    out = "\n".join(mr.calibration_bucket_summary(
        mr._collect_prediction_records(text)))
    assert ("p∈[0.7,0.8): n=5、命中 3（0.600）、"
            "Wilson 95% CI (0.2307, 0.8824)") in out


def test_calibration_summary_anti_clustering_p_value_counts() -> None:
    """arXiv:2609.32470 anti-clustering: a bucket of repeated identical p's
    renders the raw-p multiplicity so clustering can't read as calibration."""
    text = "\n".join([
        "- A（prediction: 同值一（p=0.8）due=2026-10）",
        "  - outcome: y=1 (2026-10-31)",
        "- B（prediction: 同值二（p=0.8）due=2026-10）",
        "  - outcome: y=1 (2026-10-30)",
        "- C（prediction: 异值（p=0.85）due=2026-10）",
        "  - outcome: y=0 (2026-10-29)",
    ])
    out = "\n".join(mr.calibration_bucket_summary(
        mr._collect_prediction_records(text)))
    assert "p 原值：0.8×2、0.85×1" in out


def test_lessons_calibration_feedback_empty_backlog_none_yet(
        tmp_path: Path) -> None:
    """Ring 1b: an account with zero resolved rows injects the honest
    baseline line — no fabricated buckets, no invented baseline."""
    repo = tmp_path / "repo"
    repo.mkdir()
    seeds = mr.lesson_seeds("2026-10", repo, [])
    assert seeds["calibration_feedback"] == [
        "none yet (baseline collection month)"]
    text = mr.render_reflexion_section(seeds, None, [])
    assert "- 校准事实（呈现≠校准——环 1b 注入，facts only）:" in text
    assert "  - none yet (baseline collection month)" in text
    assert f"  - {mr.CALIBRATION_FEEDBACK_NOTE}" in text


def test_lessons_calibration_feedback_with_data_renders_fact_stats(
        tmp_path: Path) -> None:
    """Ring 1b: with resolved rows the injected block carries ONLY the
    ring-1a aggregator lines (bucket facts + mean Brier) plus the fixed
    reminder literal."""
    repo = tmp_path / "repo"
    (repo / "state").mkdir(parents=True)
    (repo / "state" / "backlog.md").write_text("\n".join([
        "- A（prediction: 注入甲（p=0.8）due=2026-10）",
        "  - outcome: y=1 (2026-10-31)",
        "- B（prediction: 注入乙（p=0.7）due=2026-10）",
        "  - outcome: y=0 (2026-10-30)",
    ]), encoding="utf-8")
    seeds = mr.lesson_seeds("2026-10", repo, [])
    text = mr.render_reflexion_section(seeds, None, [])
    assert ("  - p∈[0.8,0.9): n=1、命中 1（1.000）、"
            "Wilson 95% CI (0.2065, 1.0000)、p 原值：0.8×1") in text
    assert ("  - p∈[0.7,0.8): n=1、命中 0（0.000）、"
            "Wilson 95% CI (0.0000, 0.7935)、p 原值：0.7×1") in text
    assert "汇总 mean Brier = 0.265（n=2，与逐条 (p−y)² 同口径取均值）" in text
    assert f"  - {mr.CALIBRATION_FEEDBACK_NOTE}" in text


def test_lessons_calibration_feedback_carries_no_disposition_semantics(
        tmp_path: Path) -> None:
    """Ring 1b red line: the injected text must contain NO imperative
    disposition semantics (adjust-p-to / suggested-threshold wording). The
    fixed reminder is a prohibition restatement, which the banned patterns
    are chosen not to match."""
    empty_repo = tmp_path / "empty"
    empty_repo.mkdir()
    data_repo = tmp_path / "data"
    (data_repo / "state").mkdir(parents=True)
    (data_repo / "state" / "backlog.md").write_text(
        "- A（prediction: 注入甲（p=0.8）due=2026-10）\n"
        "  - outcome: y=1 (2026-10-31)", encoding="utf-8")
    for repo in (empty_repo, data_repo):
        text = mr.render_reflexion_section(
            mr.lesson_seeds("2026-10", repo, []), None, [])
        for banned in ("调 p 至", "建议阈值取", "应调 p", "重标 p", "校准 p 至"):
            assert banned not in text, f"{banned!r} leaked into {repo.name}"


def test_lessons_insight_hook_hint_with_resolved_rows(
        tmp_path: Path) -> None:
    """Ring 2: with resolved rows present the bounded one-line hint renders,
    carrying the prohibition literal (fragments must never contain
    auto-adjust-p instructions — judgments/facts split stands)."""
    repo = tmp_path / "repo"
    (repo / "state").mkdir(parents=True)
    (repo / "state" / "backlog.md").write_text(
        "- A（prediction: 蒸馏甲（p=0.8）due=2026-10）\n"
        "  - outcome: y=1 (2026-10-31)", encoding="utf-8")
    seeds = mr.lesson_seeds("2026-10", repo, [])
    assert seeds["resolved_prediction_rows"] == 1
    text = mr.render_reflexion_section(seeds, None, [])
    assert f"- insight 钩子（环 2·蒸馏）: {mr.INSIGHT_HINT}" in text
    assert "片段禁含『自动调 p』指令" in text


def test_lessons_insight_hook_skips_without_resolved_rows(
        tmp_path: Path) -> None:
    """Ring 2 degradation: zero resolved rows (empty account or pending-only)
    -> the honest skip line; no hint, no fabricated inputs."""
    empty = tmp_path / "empty"
    empty.mkdir()
    pending = tmp_path / "pending"
    (pending / "state").mkdir(parents=True)
    (pending / "state" / "backlog.md").write_text(
        "- G（prediction: 未到对账（p=0.7）due=2026-11）", encoding="utf-8")
    for repo in (empty, pending):
        seeds = mr.lesson_seeds("2026-10", repo, [])
        assert seeds["resolved_prediction_rows"] == 0
        text = mr.render_reflexion_section(seeds, None, [])
        assert ("- insight 钩子（环 2·蒸馏）: 本月无 resolved 对账行，"
                "insight 步跳过") in text
        assert mr.INSIGHT_HINT not in text


def test_cli_survives_gbk_child_environment(tmp_path: Path) -> None:
    """flywheel-rehearsal pin (2026-11-13): under a GBK child — python -I
    ignores PYTHONIOENCODING/PYTHONUTF8, so a stripped-env piped child gets
    cp936 streams with strict errors — the CLI must still (a) render the
    --lessons face carrying the U+2212/U+00B2 mean-Brier literal with
    rc==0 and valid UTF-8 stdout, and (b) emit the --append-lessons-from
    contract-gate refusal (rc==3) as valid UTF-8 stderr. Measured pre-fix:
    stdout already survived via main()'s post-parse reconfigure, but stderr
    carried raw GBK bytes (mojibake to a UTF-8 consumer, and any future
    non-GBK stderr literal would crash the strict codec); post-fix the
    __main__ tail reconfigures BOTH streams before main() runs. A bare
    `python -I -c "print('（p−y）²')"` child crashes first-hand — the
    environment class is real, the CLI armor is what this pin locks.
    """
    repo = tmp_path / "repo"
    _write_day(repo, "2026-11-05", [_summary_line(date="2026-11-05")])
    (repo / "state").mkdir()
    (repo / "state" / "backlog.md").write_text(
        # canonical pasted-entry shape (see _prediction_backlog_text):
        # the parser needs "prediction:" + "（p=" on one line
        "- 甲（prediction: 演练预测甲（p=0.8）due=2026-11）synthetic\n"
        "  - outcome: y=1 (2026-11-30)\n", encoding="utf-8")
    (repo / "state" / "handoff.md").write_text("# tmp handoff\n",
                                               encoding="utf-8")
    env = {k: v for k, v in os.environ.items()
           if k.upper() not in ("PYTHONIOENCODING", "PYTHONUTF8",
                                "PYTHONLEGACYWINDOWSSTDIO")}
    script = _SCRIPTS / "monthly_review.py"
    proc = subprocess.run(
        [sys.executable, "-I", str(script), "--month", "2026-11",
         "--lessons", "--repo", str(repo)],
        capture_output=True, env=env, timeout=180)
    assert proc.returncode == 0
    out = proc.stdout.decode("utf-8")  # strict: pre-armor GBK bytes would
    # decode to mojibake, not the literal below
    assert "(p−y)² 同口径取均值" in out
    bad = tmp_path / "no-event.md"
    bad.write_text("无 event 行的教训文本（synthetic）\n", encoding="utf-8")
    refused = subprocess.run(
        [sys.executable, "-I", str(script), "--append-lessons-from",
         str(bad), "--month", "2026-11", "--repo", str(repo)],
        capture_output=True, env=env, timeout=180)
    assert refused.returncode == 3
    refused.stderr.decode("utf-8")  # strict: GBK bytes raise pre-armor
