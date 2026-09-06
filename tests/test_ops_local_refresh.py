"""Hermetic tests for the local evening refresh lane (scripts/ops_local_refresh.py).

Guards the unattended lane's decision logic and step table — the automation
fires nightly, so a regression here silently stale-dates the deployed terminal.
Pure functions only: no network, no git, no data/cache dependency.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(_SCRIPTS))

import ops_local_refresh as lane  # noqa: E402


def _monday(hour: int = 19) -> datetime:
    # 2026-09-07 is a Monday (the lane's first scheduled evening).
    return datetime(2026, 9, 7, hour, 5)


# --- guard decisions ----------------------------------------------------------


def test_guard_runs_on_fresh_evening() -> None:
    assert lane.guard_decision(_monday(19), {}) == "RUN"


def test_guard_skips_weekend() -> None:
    sat = datetime(2026, 9, 12, 19, 5)  # Saturday
    assert lane.guard_decision(sat, {}).startswith("SKIP:weekend")


def test_guard_skips_before_window_opens() -> None:
    assert lane.guard_decision(_monday(9), {}).startswith("SKIP:window-not-open")


def test_guard_skips_after_successful_run_same_day() -> None:
    state = {"date": "2026-09-07", "status": "ok_committed",
             "attempts": 1, "commit": "abc1234"}
    decision = lane.guard_decision(_monday(21), state)
    assert decision.startswith("SKIP:already-done")
    assert "ok_committed" in decision


def test_guard_skips_while_in_progress_and_recovers_stale_running() -> None:
    import time as _time
    fresh = {"date": "2026-09-07", "status": "running",
             "started_at_epoch": _time.time() - 10 * 60}
    assert lane.guard_decision(_monday(21), fresh).startswith("SKIP:in-progress")
    stale = {"date": "2026-09-07", "status": "running",
             "started_at_epoch": _time.time() - 10_000 * 60}
    assert lane.guard_decision(_monday(21), stale) == "RUN"


def test_guard_locks_after_attempt_cap() -> None:
    state = {"date": "2026-09-07", "status": "failed", "attempts": 3}
    assert lane.guard_decision(_monday(22), state).startswith("SKIP:attempt-cap")


def test_guard_resets_on_new_day() -> None:
    state = {"date": "2026-09-04", "status": "failed", "attempts": 3}
    assert lane.guard_decision(_monday(22), state) == "RUN"


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
