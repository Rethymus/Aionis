"""Hermetic tests for the weekly Watchdog + Reflexion lesson loop
(scripts/monthly_review.py --weekly / --lessons / --append-lessons-from).

Round 126: the Watchdog is the EXTERNAL control loop (zero Actions
dependency — round 118's freeze blind-spot cure); failure classification
reuses the Fast-Path triage rules from ops_local_refresh. Reflexion is
borrowed as protocol only (noahshinn/reflexion, MIT): lesson blocks are
APPEND-ONLY into state/handoff.md, one per month. Zero network: gh fetchers
and jobs probes are injected fakes.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(_SCRIPTS))

import monthly_review as mr  # noqa: E402
import ops_local_refresh as lane  # noqa: E402


def _row(created: str, updated: str, run_id: int = 1,
         conclusion: str = "failure") -> dict:
    return {"databaseId": run_id, "workflowName": "wf",
            "conclusion": conclusion, "createdAt": created,
            "updatedAt": updated}


FAST_BILLING = _row("2026-11-05T15:54:51Z", "2026-11-05T15:54:55Z")
SLOW_RED = _row("2026-11-10T11:27:48Z", "2026-11-10T11:31:00Z")


def _ok_jobs(run_id: int) -> dict:  # billing signature present
    return {"n_steps_defined": 0, "billing_annotation": False}


# ----------------------------------------------------------- workflow health

def test_workflow_fast_red_with_platform_signature_is_platform_failure() -> None:
    info = mr.classify_workflow(
        "ci.yml", Path("."), fetcher=lambda wf, repo: [FAST_BILLING],
        jobs_sig=_ok_jobs)
    assert info == {"wf": "ci.yml", "state": "failure",
                    "bucket": "platform-failure"}
    # single source of truth: the Watchdog bucket IS the Fast-Path rule's
    # verdict (item-3 triage reuse, not a re-implementation)
    assert info["bucket"] == lane.classify_run_row(FAST_BILLING, _ok_jobs(1))


def test_workflow_slow_red_is_code_defect() -> None:
    info = mr.classify_workflow(
        "ci.yml", Path("."), fetcher=lambda wf, repo: [SLOW_RED],
        jobs_sig=_ok_jobs)
    assert info["bucket"] == "code-defect"


def test_workflow_gh_unreachable_is_unverified_not_failure() -> None:
    info = mr.classify_workflow("ci.yml", Path("."), fetcher=lambda *a: None)
    assert info == {"wf": "ci.yml", "state": "unverified"}


def test_weekly_merges_billing_locks_and_exits_one(tmp_path: Path) -> None:
    """The motivating case: a billing lock makes every workflow fast-red;
    the Watchdog merges them into one owner-key line (not itemized noise)."""
    def fetcher(wf: str, repo: Path) -> list[dict]:
        return [FAST_BILLING]
    report, code = mr.run_weekly(tmp_path, datetime(2026, 11, 11, 9, 0),
                                 fetcher=fetcher, jobs_sig=_ok_jobs)
    assert code == 1  # human (owner) attention required
    assert "billing-lock signature (≥2 workflows" in report
    assert report.count("platform-failure |") == 7  # one merged row each
    # ledger missing in tmp repo is itself a finding
    assert "ledger: " in report


def test_weekly_clean_repo_exits_zero(tmp_path: Path) -> None:
    def fetcher(wf: str, repo: Path) -> list[dict]:
        return [_row("2026-11-10T11:00:00Z", "2026-11-10T11:04:00Z",
                     conclusion="success")]
    (tmp_path / "runs").mkdir()
    ledger = tmp_path / "runs" / "ledger.jsonl"
    committed = json.dumps({"ts": "2026-07-28T04:15:16+00:00",
                            "event": "config_committed",
                            "config_sig": "c" * 64,
                            "config": {"horizon": 1}})
    result = json.dumps({"ts": "2026-08-01T00:00:00+00:00",
                         "event": "confirmatory:first",
                         "config_sig": "c" * 64})
    ledger.write_text(committed + "\n" + result + "\n", encoding="utf-8")
    report, code = mr.run_weekly(tmp_path, datetime(2026, 11, 11, 9, 0),
                                 fetcher=fetcher, jobs_sig=_ok_jobs)
    assert code == 0
    assert "walk away" in report
    assert "config_committed with the same config_sig → **OK**" in report


# ---------------------------------------------------------- ledger spot check

def _write_ledger(tmp_path: Path, *rows: dict) -> Path:
    ledger = tmp_path / "runs" / "ledger.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text("".join(json.dumps(r) + "\n" for r in rows),
                      encoding="utf-8")
    return ledger


def test_ledger_result_before_config_committed_is_flagged(
        tmp_path: Path) -> None:
    _write_ledger(tmp_path,
                  {"ts": "t1", "event": "confirmatory:first",
                   "config_sig": "c" * 64})
    findings, stats = mr.ledger_spot_check(tmp_path)
    assert any("config_committed-BEFORE-result violated" in f
               for f in findings)
    assert stats["result_family"] == 1


def test_ledger_result_after_config_committed_passes(tmp_path: Path) -> None:
    _write_ledger(tmp_path,
                  {"ts": "t1", "event": "config_committed",
                   "config_sig": "c" * 64, "config": {"horizon": 1}},
                  {"ts": "t2", "event": "oos_result", "config_sig": "c" * 64})
    findings, stats = mr.ledger_spot_check(tmp_path)
    assert findings == []
    assert stats == {"rows": 2, "config_committed": 1, "result_family": 1,
                     "pre_convention": 0}


def test_ledger_pre_convention_rows_are_out_of_scope(tmp_path: Path) -> None:
    """Rows before the event convention (event=None) carry sigs with no
    config_committed — exempt by design (verified against the real 71-row
    ledger; flagging them would be noise)."""
    _write_ledger(tmp_path,
                  {"ts": "t0", "config_sig": "d" * 64},
                  {"ts": "t1", "event": "config_committed",
                   "config_sig": "c" * 64, "config": {"horizon": 1}})
    findings, stats = mr.ledger_spot_check(tmp_path)
    assert findings == []
    assert stats["pre_convention"] == 1


def test_ledger_forward_family_out_of_scope(tmp_path: Path) -> None:
    """The E3 forward lane uses forward_iset_frozen/forward_prediction_committed
    (its own freeze semantics) — not flagged by the confirmatory rule."""
    _write_ledger(tmp_path,
                  {"ts": "t1", "event": "forward_prediction_committed",
                   "config_sig": "e" * 64})
    findings, _ = mr.ledger_spot_check(tmp_path)
    assert findings == []


def test_ledger_config_committed_without_config_object_is_flagged(
        tmp_path: Path) -> None:
    _write_ledger(tmp_path, {"ts": "t1", "event": "config_committed",
                             "config_sig": "c" * 64})
    findings, _ = mr.ledger_spot_check(tmp_path)
    assert any("without a frozen config object" in f for f in findings)


def test_ledger_unparseable_line_and_missing_trailing_newline(
        tmp_path: Path) -> None:
    ledger = _write_ledger(tmp_path, {"ts": "t1", "event": "config_committed",
                                      "config_sig": "c" * 64,
                                      "config": {"x": 1}})
    with ledger.open("a", encoding="utf-8") as fh:
        fh.write("{not json}\n")  # corrupt line
    text = ledger.read_text(encoding="utf-8")
    ledger.write_text(text.rstrip("\n"), encoding="utf-8")  # drop final \n
    findings, _ = mr.ledger_spot_check(tmp_path)
    assert any("unparseable JSONL" in f for f in findings)
    assert any("does not end with a newline" in f for f in findings)


def test_ledger_missing_file_is_finding(tmp_path: Path) -> None:
    findings, stats = mr.ledger_spot_check(tmp_path)
    assert findings and "must exist" in findings[0]
    assert stats == {}


# --------------------------------------------------------------- spin detection

def _evening_log(tmp_path: Path, day: str, failed_step: str | None) -> None:
    """Realistic evening log: a hard-fail evening writes NO SUMMARY (do_run
    only prints SUMMARY on the ok_committed paths) — just the HARD-FAIL line."""
    d = tmp_path / "runs" / "ops_local_refresh" / day
    d.mkdir(parents=True, exist_ok=True)
    if failed_step is None:
        ok = ("[21:38:59] SUMMARY " + json.dumps(
            {"date": day, "status": "ok_committed"}, ensure_ascii=False))
        (d / "run.log").write_text(ok + "\n", encoding="utf-8")
    else:
        hard = f"[21:38:59] HARD-FAIL: hard-fail step '{failed_step}': boom"
        (d / "run.log").write_text(hard + "\n", encoding="utf-8")


def test_spin_two_consecutive_evenings_same_step_is_flagged(
        tmp_path: Path) -> None:
    _evening_log(tmp_path, "2026-11-04", "json validity + contract gate")
    _evening_log(tmp_path, "2026-11-05", "json validity + contract gate")
    findings, scanned = mr.spin_detection(tmp_path)
    assert scanned == 2
    assert findings and findings[0].startswith("spin (原地打转)")
    assert "json validity + contract gate" in findings[0]
    assert "2026-11-04, 2026-11-05" in findings[0]


def test_spin_broken_streak_is_not_flagged(tmp_path: Path) -> None:
    _evening_log(tmp_path, "2026-11-03", "step_a")
    _evening_log(tmp_path, "2026-11-04", "step_b")
    _evening_log(tmp_path, "2026-11-05", "step_a")
    findings, _ = mr.spin_detection(tmp_path)
    assert findings == []


def test_spin_single_failure_is_not_flagged(tmp_path: Path) -> None:
    _evening_log(tmp_path, "2026-11-05", "step_a")
    findings, scanned = mr.spin_detection(tmp_path)
    assert findings == [] and scanned == 1


# ----------------------------------------------------------- reflexion lessons

def test_lessons_append_creates_block_and_is_append_only(tmp_path: Path) -> None:
    handoff = tmp_path / "handoff.md"
    handoff.write_text("existing history line\n", encoding="utf-8")
    before = handoff.read_bytes()
    code = mr.append_lessons("- lesson one\n- lesson two", "2026-11", handoff)
    assert code == 0
    after = handoff.read_bytes()
    assert after.startswith(before)  # APPEND-ONLY: prefix bytes untouched
    text = after.decode("utf-8")
    assert "month=2026-11" in text and "lesson one" in text
    # file still ends with a newline (handoff hygiene)
    assert text.endswith("\n")


def test_lessons_same_month_duplicate_refused(tmp_path: Path) -> None:
    handoff = tmp_path / "handoff.md"
    handoff.write_text("history\n", encoding="utf-8")
    assert mr.append_lessons("first", "2026-11", handoff) == 0
    before = handoff.read_bytes()
    assert mr.append_lessons("second", "2026-11", handoff) == 2
    assert handoff.read_bytes() == before  # refusal wrote nothing


def test_lessons_different_month_appends(tmp_path: Path) -> None:
    handoff = tmp_path / "handoff.md"
    handoff.write_text("history\n", encoding="utf-8")
    assert mr.append_lessons("nov lessons", "2026-11", handoff) == 0
    assert mr.append_lessons("dec lessons", "2026-12", handoff) == 0
    month, block = mr.latest_lessons_block(handoff.read_text(encoding="utf-8"))
    assert month == "2026-12" and "dec lessons" in block


def test_lessons_empty_text_and_bad_month_rejected(tmp_path: Path) -> None:
    handoff = tmp_path / "handoff.md"
    handoff.write_text("history\n", encoding="utf-8")
    with pytest.raises(ValueError):
        mr.append_lessons("   \n", "2026-11", handoff)
    with pytest.raises(ValueError):
        mr.append_lessons("text", "2026-13", handoff)


def test_latest_lessons_block_none_when_absent() -> None:
    assert mr.latest_lessons_block("no blocks here\n") is None


def test_reflexion_seeds_and_render(tmp_path: Path) -> None:
    _evening_log(tmp_path, "2026-11-04", None)  # ok evening
    _evening_log(tmp_path, "2026-11-05", "step_a")  # hard-fail evening
    errors: list[str] = []
    seeds = mr.lesson_seeds("2026-11", tmp_path, errors)
    assert seeds["month"] == "2026-11"
    assert seeds["days_with_summary"] == 1  # the hard-fail evening has none
    assert "2026-11-05" in seeds["missing_weekdays"]  # the failure signal
    section = mr.render_reflexion_section(
        seeds, ("2026-10", "<!-- header -->\n- prior lesson"), [])
    assert "Reflexion seeds" in section and "spin findings: none" in section
    assert "month=2026-10" in section and "prior lesson" in section
    empty = mr.render_reflexion_section(seeds, None, [])
    assert "none yet" in empty


def test_cli_append_lessons_from_end_to_end(tmp_path: Path) -> None:
    repo = tmp_path
    (repo / "state").mkdir()
    lesson_file = tmp_path / "lesson.txt"
    lesson_file.write_text("- the 11-05 lock taught: raise the cap early\n",
                           encoding="utf-8")
    rc = mr.main(["--append-lessons-from", str(lesson_file),
                  "--month", "2026-11", "--repo", str(repo)])
    assert rc == 0
    text = (repo / "state" / "handoff.md").read_text(encoding="utf-8")
    assert "month=2026-11" in text and "raise the cap early" in text
    # duplicate refusal surfaces as exit 2
    rc2 = mr.main(["--append-lessons-from", str(lesson_file),
                   "--month", "2026-11", "--repo", str(repo)])
    assert rc2 == 2


def test_cli_weekly_end_to_end_on_tmp_repo(tmp_path: Path) -> None:
    (tmp_path / "runs").mkdir()
    # run via main(): ledger missing → exit 1, report printed to stdout
    import io
    from contextlib import redirect_stdout
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = mr.main(["--weekly", "--repo", str(tmp_path)])
    assert rc == 1
    assert "Weekly Watchdog" in buf.getvalue()
