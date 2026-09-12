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
