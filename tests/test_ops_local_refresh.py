"""Hermetic tests for the local evening refresh lane (scripts/ops_local_refresh.py).

Guards the unattended lane's decision logic and step table — the automation
fires nightly, so a regression here silently stale-dates the deployed terminal.
Pure functions only: no network, no git, no data/cache dependency.
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(_SCRIPTS))

import ops_evening_hook as hook  # noqa: E402
import ops_local_refresh as lane  # noqa: E402


def _monday(hour: int = 19) -> datetime:
    # 2026-09-14 is a REGULAR trading Monday (09-07 is Labor Day — reserved
    # for the holiday-branch tests below).
    return datetime(2026, 9, 14, hour, 5)


# --- guard decisions ----------------------------------------------------------


def test_guard_runs_on_fresh_evening() -> None:
    assert lane.guard_decision(_monday(19), {}) == "RUN"


def test_guard_skips_weekend() -> None:
    sat = datetime(2026, 9, 12, 19, 5)  # Saturday
    assert lane.guard_decision(sat, {}).startswith("SKIP:weekend")


def test_guard_skips_before_window_opens() -> None:
    assert lane.guard_decision(_monday(9), {}).startswith("SKIP:window-not-open")


def test_guard_skips_after_successful_run_same_day() -> None:
    state = {"date": "2026-09-14", "status": "ok_committed",
             "attempts": 1, "commit": "abc1234"}
    decision = lane.guard_decision(_monday(21), state)
    assert decision.startswith("SKIP:already-done")
    assert "ok_committed" in decision


def test_guard_skips_while_in_progress_and_recovers_stale_running() -> None:
    import time as _time
    fresh = {"date": "2026-09-14", "status": "running",
             "started_at_epoch": _time.time() - 10 * 60}
    assert lane.guard_decision(_monday(21), fresh).startswith("SKIP:in-progress")
    stale = {"date": "2026-09-14", "status": "running",
             "started_at_epoch": _time.time() - 10_000 * 60}
    assert lane.guard_decision(_monday(21), stale) == "RUN"


def test_guard_locks_after_attempt_cap() -> None:
    state = {"date": "2026-09-14", "status": "failed", "attempts": 3}
    assert lane.guard_decision(_monday(22), state).startswith("SKIP:attempt-cap")


def test_guard_running_is_liveness_checked_across_midnight() -> None:
    """2026-09-21 round 99: the 09-20 23:53 lane was still running at 00:56 on
    09-21 — a date-scoped in-progress check let a second lane start beside it.
    A running marker younger than the stale cap blocks a new run regardless of
    which date the marker carries; past the cap it is a crashed run (RUN)."""
    import time as _time
    alive_from_yesterday = {"date": "2026-09-14", "status": "running",
                            "started_at_epoch": _time.time() - 10 * 60}
    decision = lane.guard_decision(_monday(21), alive_from_yesterday)
    assert decision.startswith("SKIP:in-progress"), decision
    crashed_from_yesterday = {"date": "2026-09-14", "status": "running",
                              "started_at_epoch": _time.time() - 10_000 * 60}
    assert lane.guard_decision(_monday(21), crashed_from_yesterday) == "RUN"


def test_guard_resets_on_new_day() -> None:
    state = {"date": "2026-09-04", "status": "failed", "attempts": 3}
    assert lane.guard_decision(_monday(22), state) == "RUN"


# --- US-holiday energy skip ----------------------------------------------------


def test_holiday_skips_only_without_catchup(monkeypatch) -> None:
    """2026-09-07 is Labor Day (NYSE closed). With a clean prior run the guard
    skips (energy); with pending catch-up (soft_fails) it still runs."""
    monkeypatch.setattr(lane, "_us_holiday_today", lambda now: True)
    clean = {"date": "2026-09-05", "status": "ok_committed", "soft_fails": []}
    assert lane.guard_decision(_monday(19), clean).startswith("SKIP:holiday-us")
    pending = {"date": "2026-09-06", "status": "ok_committed",
               "soft_fails": ["stakes_pct_parse (visible 13G/13D rows) [local superset]"]}
    assert lane.guard_decision(_monday(19), pending) == "RUN"


def test_holiday_check_fails_open(monkeypatch) -> None:
    """Calendar unavailable => _us_holiday_today returns False (treat as
    trading day — freshness outranks energy savings)."""
    import aionis.features.alignment as align

    def _boom(start, end):
        raise RuntimeError("calendar unavailable")

    monkeypatch.setattr(align, "nyse_sessions", _boom)
    assert lane._us_holiday_today(datetime(2026, 9, 7, 19)) is False


def test_labor_day_2026_is_really_a_holiday() -> None:
    """Integration: the real NYSE calendar says 2026-09-07 (Labor Day) closed,
    2026-09-08 open. Guards the guard against calendar-usage regressions."""
    assert lane._us_holiday_today(datetime(2026, 9, 7, 19)) is True
    assert lane._us_holiday_today(datetime(2026, 9, 8, 19)) is False


# --- ledger append classifier -------------------------------------------------


def test_ledger_classifier_accepts_display_ingest_rows_only() -> None:
    reddit = ('{"ts": "2026-09-07T11:00:00+00:00", "event": "data_ingest", '
              '"dataset": "reddit_sentiment", "source": "RSS-atom"}')
    news = ('{"ts": "2026-09-07T11:00:00+00:00", "event": "data_ingest", '
            '"dataset": "news_feed", "source": "GDELT"}')
    assert lane.ledger_display_appends_only([reddit, news])
    assert not lane.ledger_display_appends_only([])
    assert not lane.ledger_display_appends_only(["not json"])
    research = ('{"ts": "2026-09-07T11:00:00+00:00", "event": "config_committed", '
                '"dataset": "x"}')
    assert not lane.ledger_display_appends_only([reddit, research])


# --- step table integrity -------------------------------------------------------


def test_step_table_covers_ci_lane_backbone() -> None:
    names = [s["name"] for s in lane.STEPS]
    for backbone in ("cot_fetch", "form4_fetch", "stakes_13d_daily_fetch",
                     "form8k_fetch", "form_ipo_fetch", "form_ipo_price_parse",
                     "politician_trades_fetch", "reddit_fetch",
                     "fetch_macro_display", "market_prices_fetch (VIX)",
                     "news_sentiment_gdelt_fetch",
                     "phase_b_fetch prices (display, budget 24m)",
                     "track_b_materialize_panel (display)",
                     "build_ticker_metadata", "build_regime_macro",
                     "export_terminal_data", "json validity + contract gate"):
        assert backbone in names, f"missing CI backbone step: {backbone}"
    # Round-91 completeness audit: panels whose fetchers were in NO lane
    # (form13f family, pct parse) must now be present — "update ALL data".
    for completeness in ("form13f_fetch (star managers) [local superset]",
                         "form13f_dir_fetch (filer directory) [local superset]",
                         "stakes_pct_parse (visible 13G/13D rows) [local superset]",
                         "export pass 2 (pick up parsed pct)"):
        assert completeness in names, f"missing completeness step: {completeness}"
    # pct parse MUST sit between the two export passes (it reads the just-
    # exported visible-row set; pass 2 folds the parsed values in).
    assert names.index("export_terminal_data") < \
        names.index("stakes_pct_parse (visible 13G/13D rows) [local superset]") < \
        names.index("export pass 2 (pick up parsed pct)")


def test_step_table_hard_steps_and_script_paths() -> None:
    hard = [s for s in lane.STEPS if not s["soft"]]
    assert [s["name"] for s in hard] == ["export_terminal_data",
                                         "json validity + contract gate"]
    for step in lane.STEPS:
        argv = step["uv_argv"]
        assert 1 <= step["cap"] <= 45
        for token in argv:
            if token.startswith("scripts/") or token.startswith("tests/"):
                path = token.split("::", 1)[0]  # pytest --deselect node ids
                assert (lane.ROOT / path).exists(), \
                    f"{step['name']}: {path} not found"


def test_lane_commits_only_allowlisted_paths() -> None:
    assert lane.ALLOWED_COMMIT_PATHS == ("web/src/data/aionis",
                                         "reports/evidence")
    # The frozen research surfaces must never appear in the lane's commit set.
    joined = "/".join(lane.ALLOWED_COMMIT_PATHS)
    for forbidden in ("runs/ledger", "config/", "src/aionis/eval"):
        assert forbidden not in joined


# --- SessionStart hook launcher -----------------------------------------------


def test_hook_silent_noop_when_guard_skips(monkeypatch, tmp_path) -> None:
    """The launcher must exit 0 and NEVER spawn a process on a SKIP decision."""
    spawned = []
    monkeypatch.setattr(hook.lane, "guard_decision", lambda now, state: "SKIP:already-done")
    monkeypatch.setattr(hook.subprocess, "Popen", lambda *a, **k: spawned.append(a))
    monkeypatch.setattr(hook.lane, "LOG_DIR", tmp_path)
    assert hook.main() == 0
    assert spawned == []


def test_hook_spawns_detached_run_when_guard_runs(monkeypatch, tmp_path) -> None:
    """On RUN the launcher spawns exactly one detached --run process."""
    spawned = {}

    class _FakeProc:  # noqa: D401 - minimal stand-in
        pass

    monkeypatch.setattr(hook.lane, "guard_decision", lambda now, state: "RUN")
    monkeypatch.setattr(hook.lane, "LOG_DIR", tmp_path)
    monkeypatch.setattr(hook, "datetime",
                        type("D", (), {"now": staticmethod(
                            lambda: datetime(2026, 9, 9, 19, 0))}))

    def _spawn(*a, **k):
        spawned["argv"] = a
        spawned["kwargs"] = k
        return _FakeProc()

    monkeypatch.setattr(hook.subprocess, "Popen", _spawn)
    assert hook.main() == 0
    argv = spawned["argv"][0]
    assert argv[0] == "uv" and argv[-1] == "--run"
    assert "ops_local_refresh.py" in " ".join(argv)
    # Detachment flags are platform-appropriate (survives the hook + session).
    if hook.IS_WINDOWS:
        assert spawned["kwargs"]["creationflags"] & subprocess.DETACHED_PROCESS
    else:
        assert spawned["kwargs"]["start_new_session"] is True


def test_hook_spawn_failure_never_fails_session(monkeypatch, tmp_path) -> None:
    """A spawn OSError is swallowed (logged) — exit 0, cron backstop retries."""
    def _boom(*a, **k):
        raise OSError("spawn denied")

    monkeypatch.setattr(hook.lane, "guard_decision", lambda now, state: "RUN")
    monkeypatch.setattr(hook.subprocess, "Popen", _boom)
    monkeypatch.setattr(hook.lane, "LOG_DIR", tmp_path)
    monkeypatch.setattr(hook, "datetime",
                        type("D", (), {"now": staticmethod(
                            lambda: datetime(2026, 9, 9, 19, 0))}))
    assert hook.main() == 0


# --- owner design correction (2026-09-08): hook window + restart inertia -------


def test_hook_outside_window_does_nothing_at_all(monkeypatch, tmp_path) -> None:
    """A session start before 18:00 (or at/after midnight) must not even
    evaluate the guard — no state reads, no spawn, no log. Restarting ZCode
    during the day is observably inert."""
    def _forbidden(*a, **k):  # any guard/state touch fails the test
        raise AssertionError("guard must not run outside the evening window")

    monkeypatch.setattr(hook.lane, "guard_decision", _forbidden)
    monkeypatch.setattr(hook.lane, "load_state", _forbidden)
    monkeypatch.setattr(hook.subprocess, "Popen", _forbidden)
    monkeypatch.setattr(hook.lane, "LOG_DIR", tmp_path)
    for hour in (0, 9, 12, 17):
        monkeypatch.setattr(hook, "datetime",
                            type("D", (), {"now": staticmethod(
                                lambda h=hour: datetime(2026, 9, 9, h))}))
        assert hook.main() == 0, f"hour {hour}"
    assert list(tmp_path.rglob("*")) == []  # zero files written all day


def test_hook_restart_same_evening_after_done_skips_with_trace(
        monkeypatch, tmp_path) -> None:
    """Restarting ZCode inside the window after a completed run: no spawn, and
    one audit line proving the check happened (once-per-day held)."""
    spawned = []
    monkeypatch.setattr(hook.lane, "guard_decision",
                        lambda now, state: "SKIP:already-done (ok_committed)")
    monkeypatch.setattr(hook.subprocess, "Popen",
                        lambda *a, **k: spawned.append(a))
    monkeypatch.setattr(hook.lane, "LOG_DIR", tmp_path)
    monkeypatch.setattr(hook, "datetime",
                        type("D", (), {"now": staticmethod(
                            lambda: datetime(2026, 9, 9, 20, 0))}))
    assert hook.main() == 0
    assert spawned == []  # never a second run
    trace = (tmp_path / "2026-09-09" / "hook-spawn.log").read_text("utf-8")
    assert "hook skip: SKIP:already-done" in trace


# --- GBK-outage regression (2026-09-10/11): UTF-8 forced for lane children -----


def test_run_step_forces_utf8_env(monkeypatch, tmp_path) -> None:
    """Every lane child must run with PYTHONUTF8=1 — the 09-10/11 outage was
    three GBK-locale crash classes (bare read_text on a curly quote, bare
    write_text on emoji, print() of a checkmark) fixed at once at the env
    layer; this pins the injection so it cannot silently regress."""
    captured = {}

    class _FakeProc:
        returncode = 0

        def communicate(self, timeout=None):
            return "ok", None

    def _spawn(cmd, **kwargs):
        captured["env"] = kwargs.get("env")
        return _FakeProc()

    monkeypatch.setattr(hook.lane.subprocess, "Popen", _spawn)
    step = {"name": "env probe", "uv_argv": ["python", "-c", "pass"],
            "cap": 1, "soft": True}
    fh = open(tmp_path / "x.log", "w", encoding="utf-8")
    try:
        ok, _ = lane.run_step(step, fh)
    finally:
        fh.close()
    assert ok
    assert captured["env"]["PYTHONUTF8"] == "1"


# --- strict-JSON gate (2026-09-11 publish-site outage: bare NaN shipped) -------


def test_strict_json_scan_flags_nan_and_passes_clean(tmp_path, monkeypatch) -> None:
    """Python's json both writes and reads bare NaN — the gate must reject it
    (Turbopack/browsers do) while accepting ordinary strict panels."""

    data_dir = tmp_path / "aionis"
    data_dir.mkdir()
    (data_dir / "good.json").write_text('{"a": 1.5, "b": null}', encoding="utf-8")
    (data_dir / "bad.json").write_text(
        '{"strength": NaN, "mean": 0.0}', encoding="utf-8")
    monkeypatch.setattr(lane, "ROOT", tmp_path)
    # lane.ROOT/web/src/data/aionis must map onto the fixtures above.
    (tmp_path / "web/src/data").mkdir(parents=True, exist_ok=True)
    data_dir.rename(tmp_path / "web/src/data/aionis")
    problems = lane.strict_json_scan()
    names = [p.split(":")[0] for p in problems]
    assert names == ["bad.json"]


# --- evening-completion rule (round 102): morning catch-up must not suppress
#     the evening lane (the 09-21 one-day gap) -----------------------------------


def _state_for(hour_started: int, status: str = "ok_committed",
               attempts: int = 1) -> dict:
    d = datetime(2026, 9, 21, hour_started, 0)
    return {"date": "2026-09-21", "status": status, "attempts": attempts,
            "commit": "abc", "n_files": 50, "soft_fails": [],
            "started_at_epoch": d.timestamp()}


def test_morning_catchup_does_not_suppress_evening_lane() -> None:
    """The 09-21 incident: a 00:56 recovery marked the day done; the Monday
    evening lane then skipped and the day's daytime filings went unfetched.
    A pre-18:00 completion must fall through to RUN."""
    evening = datetime(2026, 9, 21, 21, 0)
    assert lane.guard_decision(evening, _state_for(0)) == "RUN"  # 00:56 start
    assert lane.guard_decision(evening, _state_for(14)) == "RUN"  # midday


def test_evening_start_counts_as_done() -> None:
    evening = datetime(2026, 9, 21, 21, 0)
    assert lane.guard_decision(evening, _state_for(18)) \
        .startswith("SKIP:already-done")
    assert lane.guard_decision(datetime(2026, 9, 21, 23, 59),
                               _state_for(23)) \
        .startswith("SKIP:already-done")  # late-evening start, same date


def test_forced_premeighteen_start_reruns_in_evening() -> None:
    """A 17:55 --force run predates the evening data window — the evening
    lane must still run (its fetches supersede)."""
    assert lane.guard_decision(datetime(2026, 9, 21, 20, 0),
                               _state_for(17)) == "RUN"


def test_attempt_cap_never_fires_on_successful_catchup() -> None:
    """A catch-up that needed 4 attempts but SUCCEEDED (09-11 pattern) must
    not trip the attempt cap when the evening falls through."""
    state = _state_for(0, status="ok_committed", attempts=4)
    assert lane.guard_decision(datetime(2026, 9, 21, 21, 0), state) == "RUN"
    failed = _state_for(0, status="failed", attempts=3)
    assert lane.guard_decision(datetime(2026, 9, 21, 21, 0),
                               failed).startswith("SKIP:attempt-cap")


# --- push-only recovery (round 104; 09-25 incident evidence) ---------------------


def test_push_only_recovery_pushes_existing_commit(monkeypatch) -> None:
    """Previous attempt committed but its push hit a transient network error:
    the retry must push the EXISTING commit instead of re-running the
    pipeline (the 09-25 incident wasted a full hour re-fetching)."""
    calls = []

    def _git(args, check=True):
        calls.append(args[0])
        if args[:2] == ["log", "--oneline"]:
            return subprocess.CompletedProcess(
                args, 0,
                "abc1234 chore(data): evening terminal refresh — 2026-10-01", "")
        if args[0] == "rev-parse":
            return subprocess.CompletedProcess(args, 0, "abc1234" * 8, "")
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(lane, "git", _git)
    fh = None
    assert lane.try_push_only_recovery(
        "failed", "push failed: RPC failed; curl 16", fh) == "ok_committed"
    assert ["log", "pull", "push", "rev-parse"] == calls


def test_push_only_recovery_not_applicable_variants(monkeypatch) -> None:
    def _git(args, check=True):
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(lane, "git", _git)
    # different failure class -> full pipeline
    assert lane.try_push_only_recovery(
        "failed", "hard-fail step 'export_terminal_data'", None) is None
    # no unpushed commits -> full pipeline
    assert lane.try_push_only_recovery(
        "failed", "push failed: whatever", None) is None
    # unpushed commits must ALL be lane commits (mixed tree -> full pipeline)
    mixed = "abc1 chore(data): evening terminal refresh — x\ndef2 feat(other): y"

    def _git_mixed(args, check=True):
        return subprocess.CompletedProcess(args, 0, mixed, "")

    monkeypatch.setattr(lane, "git", _git_mixed)
    assert lane.try_push_only_recovery(
        "failed", "push failed: whatever", None) is None


def test_push_only_recovery_push_failure_raises(monkeypatch) -> None:
    class _R:
        returncode = 1
        stdout = ""
        stderr = "boom"

    def _git(args, check=True):
        if args[0] == "push":
            return _R()
        if args[:2] == ["log", "--oneline"]:
            return subprocess.CompletedProcess(
                args, 0, "abc1234 chore(data): evening terminal refresh — d", "")
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(lane, "git", _git)
    import pytest as _pytest
    with _pytest.raises(RuntimeError):
        lane.try_push_only_recovery("failed", "push failed: net", None)


# --- --doctor preflight (round 109) ---------------------------------------------

_FROZEN_NOW: datetime | None = None  # set by _fresh_ok_evening (round 127)


class _SharedClock(datetime):
    """Real datetime except now(), which returns _FROZEN_NOW. _fresh_ok_evening
    monkeypatches this onto lane.datetime so the doctor fixture (log-dir date)
    and doctor layer 8 (marker_deadman's injected clock,
    scripts/ops_local_refresh.py:1250) share ONE clock read — a midnight
    crossing between fixture write and layer read can no longer desynchronize
    the two surfaces (round 127 flaky-risk fix). Only the doctor tests patch
    this; the only other clock consumer under collect_layers is layer 1's
    guard_decision (detail text, not the pass/fail bit)."""

    @classmethod
    def now(cls, tz=None):  # type: ignore[override]
        assert _FROZEN_NOW is not None, "_fresh_ok_evening must run first"
        return _FROZEN_NOW


def _fresh_ok_evening(tmp_path: Path, monkeypatch) -> str:
    """A same-day ok_committed run.log so doctor layer 8 (marker deadman,
    round 126) passes under mocks — a real freshness check would honestly
    fail on the old stale-date fixture. Round 127: the log-dir date comes
    from a single clock read shared with the lane via _SharedClock, so
    fixture and layer cannot disagree across midnight."""
    import json as _json
    global _FROZEN_NOW
    _FROZEN_NOW = datetime.now().replace(hour=21, minute=0, second=0,
                                         microsecond=0)
    monkeypatch.setattr(lane, "datetime", _SharedClock)
    today = _FROZEN_NOW.strftime("%Y-%m-%d")
    log_dir = tmp_path / "runs" / "ops_local_refresh" / today
    log_dir.mkdir(parents=True)
    summary = {"date": today, "status": "ok_committed", "commit": "a" * 40}
    (log_dir / "run.log").write_text(
        f"[21:00:00] SUMMARY {_json.dumps(summary, ensure_ascii=False)}\n",
        encoding="utf-8")
    monkeypatch.setattr(lane, "LOG_DIR",
                        tmp_path / "runs" / "ops_local_refresh")
    return today


def test_doctor_all_layers_pass(monkeypatch, tmp_path) -> None:
    """Mocked eight-layer stack: exit 0 (the 8/8 deadman gets a fresh
    same-day ok evening via _fresh_ok_evening)."""
    def _ok(args, **k):
        s = "True" if "ScheduledTask" in str(args) else (
            "abc123 main" if "ls-remote" in args else "gh ok")
        return subprocess.CompletedProcess(args, 0, s, "")

    monkeypatch.setattr(lane.subprocess, "run", _ok)
    monkeypatch.setattr(lane, "IS_WINDOWS", True)  # CI runs Linux: force the
    # scheduler branch so the mocked powershell query is what executes
    monkeypatch.setattr(lane, "load_state",
                        lambda: {"date": "2026-10-01", "status": "ok_committed"})
    _fresh_ok_evening(tmp_path, monkeypatch)
    import json as _json
    real_root = lane.ROOT
    fake = tmp_path
    (fake / ".zcode").mkdir()
    (fake / ".zcode" / "config.json").write_text(_json.dumps({
        "hooks": {"enabled": True, "events": {"SessionStart": [
            {"matcher": "startup|resume", "hooks": []}]}}}), encoding="utf-8")
    (fake / ".env").write_text(
        "TIINGO_API_KEY=x" + chr(10) + "FRED_API_KEY=y" + chr(10),
        encoding="utf-8")
    _repo_data_health(fake, _FIXED_SNAPSHOT)
    monkeypatch.setattr(lane, "_fetch_live_snapshot",
                        lambda: _live_payload(_FIXED_SNAPSHOT))
    monkeypatch.setattr(lane, "ROOT", fake)
    try:
        assert lane.doctor() == 0
    finally:
        monkeypatch.setattr(lane, "ROOT", real_root)


def test_do_run_state_persists_backup_field() -> None:
    """Round 197 lesson, pinned: backup_note reached the SUMMARY log but not
    the state.update that persists state.json — the field the post-run
    verifier reads. do_run is not hermetically runnable (real fetches), so
    pin the wiring at AST level: the state.update call inside do_run must
    carry "backup" alongside "soft_fails" and "ci".
    """

    import ast

    src = Path(lane.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    do_run = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                  and n.name == "do_run")
    updates: set[str] = set()
    for n in ast.walk(do_run):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "update"
                and isinstance(n.func.value, ast.Name)
                and n.func.value.id == "state"):
            for arg in n.args:  # state.update({...}) passes the dict positionally
                if isinstance(arg, ast.Dict):
                    for k in arg.keys:
                        if isinstance(k, ast.Constant):
                            updates.add(k.value)
            updates.update(kw.arg for kw in n.keywords)
    assert updates, "do_run must persist its outcome via state.update(...)"
    assert "backup" in updates, (
        "state.update lost the 'backup' key — the post-run verifier reads "
        "state.json, not the SUMMARY log (2026-10-05 first-run lesson)"
    )
    for required in ("soft_fails", "ci", "finished_at"):
        assert required in updates, f"state.update lost '{required}'"


def test_do_run_state_persists_persistent_soft_fails() -> None:
    """Round 208 companion to the round-197 AST pin: the persistent-soft-fail
    alarm must reach BOTH the persisted state and the SUMMARY (the recovery
    lane fires on hard failures only — a nightly soft-failing step's
    freshness debt must be visible, not silent)."""

    import ast

    src = Path(lane.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    do_run = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                  and n.name == "do_run")
    state_keys: set[str] = set()
    summary_keys: set[str] = set()
    for n in ast.walk(do_run):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "update"
                and isinstance(n.func.value, ast.Name)
                and n.func.value.id == "state"):
            for arg in n.args:
                if isinstance(arg, ast.Dict):
                    for k in arg.keys:
                        if isinstance(k, ast.Constant):
                            state_keys.add(k.value)
        if (isinstance(n, ast.Assign) and n.targets
                and isinstance(n.targets[0], ast.Name)
                and n.targets[0].id == "summary"):
            if isinstance(n.value, ast.Dict):
                for k in n.value.keys:
                    if isinstance(k, ast.Constant):
                        summary_keys.add(k.value)
    assert "persistent_soft_fails" in state_keys, (
        "state.update lost 'persistent_soft_fails' (round-207 lesson class)"
    )
    assert "persistent_soft_fails" in summary_keys, (
        "SUMMARY lost 'persistent_soft_fails' — the alarm must reach the log"
    )


# --- machine-readable output: --status --json / --doctor --json (2026-10-29) ----


def _fake_marker(tmp_path: Path) -> dict:
    """A realistic once-per-evening marker in tmp, with a non-ASCII field —
    that byte proves the ensure_ascii=False contract end-to-end. STATE_FILE
    is bound from ROOT at import time, so the fixture patches STATE_FILE
    itself (same module-global seam the other tests use for ROOT/LOG_DIR)."""
    import json as _json

    state = {"date": "2026-10-28", "status": "ok_committed", "attempts": 1,
             "commit": "abc1234", "n_files": 7, "soft_fails": [],
             "ci": {"Publish site (gh-pages)": "success", "Tests": "success"},
             "note": "晚间 lane ✓"}
    path = tmp_path / "data" / "ops" / "local_refresh_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json.dumps(state, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    return state


_FIXED_SNAPSHOT = "2026-11-05T13:20:58.252918+00:00"  # real repo format


def _repo_data_health(tmp_path: Path, ts: str) -> None:
    """Write a data_health.json carrying `ts` under tmp ROOT (doctor layer 7
    reads ROOT/web/src/data/aionis/data_health.json)."""
    import json as _json

    d = tmp_path / "web" / "src" / "data" / "aionis"
    d.mkdir(parents=True, exist_ok=True)
    (d / "data_health.json").write_text(
        _json.dumps({"status": "ok", "snapshot_ts": ts}), encoding="utf-8")


def _live_payload(ts: str) -> str:
    import json as _json

    return _json.dumps({"status": "ok", "snapshot_ts": ts})


def _mock_preflight_stack(monkeypatch, tmp_path) -> None:
    """All-pass eight-layer stack: mocked subprocesses, forced Windows branch,
    tmp ROOT carrying a valid hook config + the two required .env keys, a
    layer-7 live fetch that matches the repo snapshot, and a fresh same-day
    ok evening for the layer-8 deadman."""
    import json as _json

    def _ok(args, **k):
        s = "True" if "ScheduledTask" in str(args) else (
            "abc123 main" if "ls-remote" in args else "gh ok")
        return subprocess.CompletedProcess(args, 0, s, "")

    monkeypatch.setattr(lane.subprocess, "run", _ok)
    monkeypatch.setattr(lane, "IS_WINDOWS", True)  # CI runs Linux: force the
    # scheduler branch so the mocked powershell query is what executes
    monkeypatch.setattr(lane, "load_state",
                        lambda: {"date": "2026-10-01", "status": "ok_committed"})
    _fresh_ok_evening(tmp_path, monkeypatch)
    (tmp_path / ".zcode").mkdir()
    (tmp_path / ".zcode" / "config.json").write_text(_json.dumps({
        "hooks": {"enabled": True, "events": {"SessionStart": [
            {"matcher": "startup|resume", "hooks": []}]}}}), encoding="utf-8")
    (tmp_path / ".env").write_text(
        "TIINGO_API_KEY=x" + chr(10) + "FRED_API_KEY=y" + chr(10),
        encoding="utf-8")
    _repo_data_health(tmp_path, _FIXED_SNAPSHOT)
    monkeypatch.setattr(lane, "_fetch_live_snapshot",
                        lambda: _live_payload(_FIXED_SNAPSHOT))
    monkeypatch.setattr(lane, "ROOT", tmp_path)


def test_status_json_stdout_parses_and_carries_marker_keys(
        monkeypatch, tmp_path, capsys) -> None:
    """--status --json prints exactly one JSON document (the whole marker
    dict) on stdout: json.loads-able, carrying the ci/date keys the post-run
    verifier reads, with non-ASCII emitted raw (ensure_ascii=False)."""
    import json as _json

    state = _fake_marker(tmp_path)
    monkeypatch.setattr(
        lane, "STATE_FILE",
        tmp_path / "data" / "ops" / "local_refresh_state.json")
    monkeypatch.setattr(sys, "argv",
                        ["ops_local_refresh.py", "--status", "--json"])
    assert lane.main() == 0
    out = capsys.readouterr().out
    payload = _json.loads(out)  # any stray non-JSON line would fail here
    assert payload["date"] == state["date"]
    assert payload["ci"] == state["ci"]
    assert "✓" in out  # ensure_ascii=False — not \uXXXX-escaped


def test_collect_layers_seven_json_serializable_layers(
        monkeypatch, tmp_path) -> None:
    """collect_layers (the doctor() refactor seam) returns the eight preflight
    layers as (name, ok, detail) tuples under mocked subprocesses, and the
    tuples survive a JSON round-trip."""
    import json as _json

    _mock_preflight_stack(monkeypatch, tmp_path)
    layers = lane.collect_layers()
    assert len(layers) == 8
    for name, ok, detail in layers:
        assert isinstance(name, str)
        assert isinstance(ok, bool)
        assert isinstance(detail, str)
    doc = _json.loads(_json.dumps(
        [{"name": n, "ok": o, "detail": d} for n, o, d in layers],
        ensure_ascii=False))
    assert [row["name"] for row in doc] == [n for n, _, _ in layers]


def test_doctor_json_stdout_shape(monkeypatch, tmp_path, capsys) -> None:
    """--doctor --json prints ONLY the machine document {"layers":
    [{name, ok, detail}...], "passed": N, "total": 8} — no human [PASS]/
    [FAIL] lines interleaved, so stdout stays json.loads-able; exit code is
    still 0 only when every layer passes."""
    import json as _json

    _mock_preflight_stack(monkeypatch, tmp_path)
    monkeypatch.setattr(sys, "argv",
                        ["ops_local_refresh.py", "--doctor", "--json"])
    assert lane.main() == 0
    out = capsys.readouterr().out
    payload = _json.loads(out)
    assert payload["total"] == 8
    assert payload["passed"] == 8
    assert len(payload["layers"]) == 8
    assert payload["layers"][-1]["name"] == "8/8 evening marker deadman"
    for layer in payload["layers"]:
        assert set(layer) == {"name", "ok", "detail"}
        assert layer["ok"] is True


# --- doctor layer 7: site-repo drift (the billing-freeze blind spot) ------------


def test_layer7_fails_when_live_lags_repo_beyond_48h(
        monkeypatch, tmp_path) -> None:
    """The freeze signature: origin/main advances nightly (repo snapshot
    fresh) while the deployed site stays on its last pre-freeze snapshot.
    Lag beyond 48h must FAIL with the 'deploy frozen?' message (the real
    2026-11-05 gap was ~3.1 days)."""
    _repo_data_health(tmp_path, "2026-11-05T13:20:58.252918+00:00")
    monkeypatch.setattr(lane, "ROOT", tmp_path)
    monkeypatch.setattr(
        lane, "_fetch_live_snapshot",
        lambda: _live_payload("2026-11-02T11:32:33.889178+00:00"))
    ok, detail = lane._site_repo_drift_check()
    assert not ok
    assert "live site lags repo by" in detail
    assert "deploy frozen?" in detail


def test_layer7_passes_when_live_matches_or_newer(
        monkeypatch, tmp_path) -> None:
    """Normal operation: the Pages deploy carries tonight's snapshot (equal)
    or raced past the commit (newer) — both PASS."""
    _repo_data_health(tmp_path, _FIXED_SNAPSHOT)
    monkeypatch.setattr(lane, "ROOT", tmp_path)
    monkeypatch.setattr(lane, "_fetch_live_snapshot",
                        lambda: _live_payload(_FIXED_SNAPSHOT))
    ok, detail = lane._site_repo_drift_check()
    assert ok
    assert "live matches repo" in detail
    monkeypatch.setattr(
        lane, "_fetch_live_snapshot",
        lambda: _live_payload("2026-11-06T01:00:00+00:00"))
    ok, detail = lane._site_repo_drift_check()
    assert ok
    assert "newer" in detail


def test_layer7_tolerates_sub_48h_deploy_lag(monkeypatch, tmp_path) -> None:
    """A fresh commit against a Pages deploy that has not caught up yet (or a
    weekend) is normal: lag inside the 48h window must NOT fail."""
    _repo_data_health(tmp_path, _FIXED_SNAPSHOT)
    monkeypatch.setattr(lane, "ROOT", tmp_path)
    monkeypatch.setattr(  # 36h behind the repo snapshot
        lane, "_fetch_live_snapshot",
        lambda: _live_payload("2026-11-04T01:20:58.252918+00:00"))
    ok, detail = lane._site_repo_drift_check()
    assert ok
    assert "within 48h tolerance" in detail


def test_layer7_fails_honestly_when_live_unreachable(
        monkeypatch, tmp_path) -> None:
    """Network unreachable is a FAIL with the reason (honest signal first) —
    the exception is caught inside the layer, never escapes."""
    _repo_data_health(tmp_path, _FIXED_SNAPSHOT)
    monkeypatch.setattr(lane, "ROOT", tmp_path)

    def _boom():
        raise RuntimeError("curl exit 7: Failed to connect")

    monkeypatch.setattr(lane, "_fetch_live_snapshot", _boom)
    ok, detail = lane._site_repo_drift_check()
    assert not ok
    assert ("live site unreachable or invalid — deploy may be frozen "
            "(billing?)") in detail
    assert "curl exit 7" in detail


def test_layer7_fails_on_invalid_live_payload(monkeypatch, tmp_path) -> None:
    """A reachable URL serving garbage (or JSON without snapshot_ts) is the
    same honest FAIL class as unreachable — no crash, no PASS."""
    _repo_data_health(tmp_path, _FIXED_SNAPSHOT)
    monkeypatch.setattr(lane, "ROOT", tmp_path)
    monkeypatch.setattr(lane, "_fetch_live_snapshot",
                        lambda: "<html>404 Not Found</html>")
    ok, detail = lane._site_repo_drift_check()
    assert not ok
    assert "live site unreachable or invalid" in detail
    # Valid JSON but the snapshot_ts field is absent — same honest FAIL.
    monkeypatch.setattr(
        lane, "_fetch_live_snapshot",
        lambda: '{"status": "ok", "data_date": "2026-11-05"}')
    ok, detail = lane._site_repo_drift_check()
    assert not ok
    assert "live site unreachable or invalid" in detail
    assert "no parseable snapshot_ts" in detail


# --------------------------------------------------------------- round 129
# Owner pause order 2026-11-11: GitHub Actions fully disabled (billing lock)
# — the own-commit poll must short-circuit to paused() instead of burning
# its bounded window nightly, and stay fail-open when the state is unreadable.

def test_own_commit_ci_paused_short_circuit(monkeypatch) -> None:
    """Both lane workflows non-active -> paused marker, zero run-list polls."""
    calls: list[list[str]] = []

    def _fake_run(args, **_kw):
        calls.append(list(args))
        if args[1:3] == ["repo", "view"]:
            return subprocess.CompletedProcess(
                args, 0, "Rethymus/Aionis\n", "")
        return subprocess.CompletedProcess(
            args, 0, "disabled_manually\n", "")

    monkeypatch.setattr(lane.subprocess, "run", _fake_run)
    out = lane.verify_own_commit_ci("deadbeef", max_wait_s=0)
    assert out == {"Publish site (gh-pages)": "paused(actions-disabled)",
                   "Tests": "paused(actions-disabled)"}
    # state probed (repo view + 2x workflow api), never the run list
    assert any(a[1:3] == ["repo", "view"] for a in calls)
    assert sum(a[1] == "api" for a in calls) == 2
    assert not any(a[1] == "run" for a in calls)


def test_own_commit_ci_partial_reenable_keeps_honest_poll(
        monkeypatch) -> None:
    """Unlock-transition: one workflow re-enabled -> poll still runs (False
    from _actions_paused) and lands on the existing not-observed fail-open."""
    seen_api = {"n": 0}

    def _fake_run(args, **_kw):
        if args[1:3] == ["repo", "view"]:
            return subprocess.CompletedProcess(
                args, 0, "Rethymus/Aionis\n", "")
        if args[1] == "api":
            seen_api["n"] += 1
            state = "active" if seen_api["n"] == 1 else "disabled_manually"
            return subprocess.CompletedProcess(args, 0, state + "\n", "")
        return subprocess.CompletedProcess(args, 1, "", "gh down")

    monkeypatch.setattr(lane.subprocess, "run", _fake_run)
    out = lane.verify_own_commit_ci("deadbeef", max_wait_s=0)
    assert out == {"Publish site (gh-pages)": "not-observed",
                   "Tests": "not-observed"}


def test_own_commit_ci_state_unreadable_fails_open(monkeypatch) -> None:
    """gh repo view failing -> _actions_paused() is None -> pre-129 poll
    behaviour (bounded miss -> not-observed), never a paused marker."""
    monkeypatch.setattr(
        lane.subprocess, "run",
        lambda args, **_kw: subprocess.CompletedProcess(args, 1, "", "boom"))
    assert lane._actions_paused() is None
    out = lane.verify_own_commit_ci("deadbeef", max_wait_s=0)
    assert out == {"Publish site (gh-pages)": "not-observed",
                   "Tests": "not-observed"}
