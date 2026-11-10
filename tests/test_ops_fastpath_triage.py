"""Fast-Path failure triage (round 126): deterministic three-bucket rules.

Hermetic: no network, no gh — gh probes are injected/monkeypatched. The rules
must classify conservatively (unmeasurable -> code-defect), merge billing-lock
noise into one platform line, and route the retry-soft surface to
infra-transient — the 11-05 billing lock (#2) is the motivating case.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = ROOT / "scripts"
for _p in (_SCRIPTS,):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import ops_evening_hook as hook  # noqa: E402
import ops_local_refresh as lane  # noqa: E402


def _row(created: str, updated: str, workflow: str = "Tests",
         run_id: int = 1) -> dict:
    return {"createdAt": created, "updatedAt": updated,
            "workflowName": workflow, "databaseId": run_id,
            "conclusion": "failure"}


FAST_BILLING = _row("2026-11-05T15:54:51Z", "2026-11-05T15:54:55Z")
SLOW_RED = _row("2026-11-10T11:27:48Z", "2026-11-10T11:31:00Z")


def test_fast_red_with_billing_annotation_is_platform_failure() -> None:
    jobs = {"n_steps_defined": 3, "billing_annotation": True}
    assert lane.classify_run_row(FAST_BILLING, jobs) == "platform-failure"


def test_fast_red_with_zero_steps_is_platform_failure() -> None:
    """The billing-lock signature measured on gh api: job never starts."""
    jobs = {"n_steps_defined": 0, "billing_annotation": False}
    assert lane.classify_run_row(FAST_BILLING, jobs) == "platform-failure"


def test_fast_red_unconfirmed_is_code_defect() -> None:
    """Conservative: a fast red with no platform signature gets human eyes."""
    assert lane.classify_run_row(
        FAST_BILLING, {"n_steps_defined": 4, "billing_annotation": False}
    ) == "code-defect"
    assert lane.classify_run_row(FAST_BILLING, None) == "code-defect"


def test_slow_red_is_code_defect_even_with_billing_word() -> None:
    jobs = {"n_steps_defined": 0, "billing_annotation": True}
    assert lane.classify_run_row(SLOW_RED, jobs) == "code-defect"


def test_unmeasurable_row_is_code_defect() -> None:
    assert lane.classify_run_row({}, {"n_steps_defined": 0}) == "code-defect"
    assert lane.classify_run_row({"createdAt": "garbage",
                                  "updatedAt": "garbage"}, None) == "code-defect"


def test_triage_state_soft_and_persistent_are_infra_transient() -> None:
    t = lane.triage_state({"soft_fails": ["news_feed_fetch [local superset]"],
                           "persistent_soft_fails": ["filing_stream"]})
    assert "news_feed_fetch [local superset]" in t[lane.TRIAGE_INFRA]
    assert "persistent:filing_stream" in t[lane.TRIAGE_INFRA]


def test_triage_state_push_transient_vs_contract_gate() -> None:
    t_push = lane.triage_state({"error": "push failed: HTTP/2 disconnect"})
    assert "lane-error:push-transient" in t_push[lane.TRIAGE_INFRA]
    t_gate = lane.triage_state({"error": "hard-fail step 'json validity + "
                                          "contract gate': AssertionError"})
    assert t_gate[lane.TRIAGE_CODE] and "contract gate" in \
        t_gate[lane.TRIAGE_CODE][0]


def test_triage_state_routes_ci_buckets() -> None:
    t = lane.triage_state({"ci_triage": {"Tests": "platform-failure",
                                         "Publish site (gh-pages)":
                                             "code-defect"}})
    assert t[lane.TRIAGE_PLATFORM] == ["ci:Tests"]
    assert "ci:Publish site (gh-pages)" in t[lane.TRIAGE_CODE]


def test_triage_ci_skips_gh_without_reds(monkeypatch) -> None:
    """No red conclusions -> zero gh calls (steady-state cost is zero)."""

    def _boom(*a, **k):  # pragma: no cover - must never be called
        raise AssertionError("gh probe called without a red run")

    monkeypatch.setattr(lane, "_gh_run_rows", _boom)
    monkeypatch.setattr(lane, "_gh_jobs_signature", _boom)
    assert lane.triage_ci({"Tests": "success",
                           "Publish site (gh-pages)": "success"}, "abc") == {}
    assert lane.triage_ci({"note": "no push"}, None) == {}


def test_triage_ci_enriches_reds_and_stays_conservative(monkeypatch) -> None:
    rows = {"Tests": FAST_BILLING, "Publish site (gh-pages)": SLOW_RED}
    monkeypatch.setattr(lane, "_gh_run_rows", lambda sha: rows)
    monkeypatch.setattr(lane, "_gh_jobs_signature",
                        lambda run_id: {"n_steps_defined": 0,
                                        "billing_annotation": False})
    out = lane.triage_ci({"Tests": "failure",
                          "Publish site (gh-pages)": "failure"}, "abc123")
    assert out == {"Tests": "platform-failure",
                   "Publish site (gh-pages)": "code-defect"}


def test_triage_ci_gh_unavailable_is_code_defect(monkeypatch) -> None:
    monkeypatch.setattr(lane, "_gh_run_rows", lambda sha: {})
    monkeypatch.setattr(lane, "_gh_jobs_signature", lambda run_id: None)
    out = lane.triage_ci({"Tests": "failure"}, "abc123")
    assert out == {"Tests": "code-defect"}


def test_package_inlines_today_and_spills_history(monkeypatch) -> None:
    """Success-marker shape: do_run pops stale errors on success, so a clean
    package carries no error key; a present error IS shown (failed path)."""
    state = {"date": "2026-11-11", "status": "ok_committed",
             "commit": "a" * 40, "pushed": True, "n_files": 58,
             "soft_fails": [], "ci": {"Tests": "success"},
             "ci_triage": {}, "backup": "ok"}
    pkg = lane.build_night_package(state, datetime(2026, 11, 11, 23, 35))
    assert pkg["lane"]["status"] == "ok_committed"
    assert "error" not in pkg["lane"]
    assert pkg["threads"] == {"platform-failure": [], "infra-transient": [],
                              "code-defect": []}
    failed = lane.build_night_package(
        {"date": "2026-11-11", "status": "failed",
         "error": "hard-fail step 'x': boom", "ci_triage": {}},
        datetime(2026, 11, 11, 23, 35))
    assert failed["lane"]["error"].startswith("hard-fail")
    # Inline & Spill: refs are PATHS, never inlined document bodies.
    for ref in pkg["refs"].values():
        assert ref.endswith((".md", ".py", "/")) or "§" in ref


def test_write_night_package_best_effort(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(lane, "LOG_DIR", tmp_path)
    monkeypatch.setattr(lane, "load_state",
                        lambda: {"date": "2026-11-11", "status": "failed",
                                 "error": "hard-fail step 'x': boom",
                                 "ci_triage": {}})
    pkg = lane.write_night_package(datetime(2026, 11, 11, 23, 40))
    out = tmp_path / "2026-11-11" / "night_package.json"
    assert out.exists()
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["threads"][lane.TRIAGE_CODE] == ["lane-error:hard-fail "
                                                   "step 'x': boom"]
    assert pkg["date"] == "2026-11-11"


def test_write_night_package_state_override_matches_triage_printout(
        monkeypatch, tmp_path) -> None:
    """--triage enriches an untriaged marker in memory; the persisted package
    must carry that enrichment (regression: the first live smoke printed
    platform-failure threads while writing an empty-threaded file)."""
    monkeypatch.setattr(lane, "LOG_DIR", tmp_path)
    monkeypatch.setattr(lane, "load_state",
                        lambda: {"date": "2026-11-10", "status": "ok_committed",
                                 "ci": {"Tests": "failure"}})  # no ci_triage
    state = lane.load_state()
    state["ci_triage"] = {"Tests": "platform-failure"}
    lane.write_night_package(datetime(2026, 11, 11, 23, 45), state)
    loaded = json.loads(
        (tmp_path / "2026-11-10" / "night_package.json").read_text(
            encoding="utf-8"))
    assert loaded["threads"][lane.TRIAGE_PLATFORM] == ["ci:Tests"]


def test_hook_skip_path_refreshes_package(monkeypatch, tmp_path, capsys) -> None:
    """The 23:35 report session triggers the hook on a SKIP decision; the
    package must be refreshed there — silently (empty stdout) and without
    spawning anything. datetime is pinned INTO the evening window (the
    hook is inert outside 18:00-24:00 by design)."""
    monkeypatch.setattr(hook, "datetime",
                        type("D", (), {"now": staticmethod(
                            lambda: datetime(2026, 11, 11, 23, 35))}))
    monkeypatch.setattr(hook.lane, "guard_decision",
                        lambda now, state: "SKIP:already-done")
    monkeypatch.setattr(hook.lane, "LOG_DIR", tmp_path)
    monkeypatch.setattr(hook.lane, "load_state",
                        lambda: {"date": "2026-11-11",
                                 "status": "ok_committed"})
    spawned: list = []
    monkeypatch.setattr(hook.subprocess, "Popen",
                        lambda *a, **k: spawned.append(a))
    assert hook.main() == 0
    assert capsys.readouterr().out == ""
    assert spawned == []
    assert (tmp_path / "2026-11-11" / "night_package.json").exists()


def test_note_pop_leaves_no_stale_note_marker() -> None:
    """begin_attempt must overwrite the stale round-99-era note (the --status
    residue: 'lane redundant ... killed by round-99')."""
    state = {"date": "2026-11-10", "status": "ok_committed",
             "note": "lane redundant (23:53 recovery lane had already "
                     "completed da15bb70d); killed by round-99 session"}
    lane.begin_attempt(state, "2026-11-11", 1, False)
    assert "note" not in state
    assert state["status"] == "running" and state["attempts"] == 1


def test_stale_note_residue_is_real_marker_fact() -> None:
    """The motivating residue exists on this machine's real marker (P0 发现④);
    the fix pops it on the next attempt start. Read-only, skipped if absent."""
    marker = ROOT / "data" / "ops" / "local_refresh_state.json"
    if not marker.exists():
        pytest.skip("local marker not present in this checkout")
    live = json.loads(marker.read_text(encoding="utf-8"))
    if "note" not in live:
        pytest.skip("marker already note-free (fix has taken effect)")
    assert "round-99" in str(live["note"])
