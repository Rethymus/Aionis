"""SessionStart hook launcher for the local evening refresh lane.

Wired in `.zcode/config.json` (workspace scope) under
`hooks.events.SessionStart` — this is what makes the lane literal
"update as soon as ZCode connects" on trading-day evenings: opening or
resuming any ZCode session in this workspace after 18:00 local triggers the
refresh IMMEDIATELY, with zero LLM tokens (the heavy work is a detached shell
process; the recurring cron automation stays as backstop + reporter).

Hook contract (zcode-guide/diagnosing-hooks):
  - runs INLINE, so this launcher must return within seconds: it only makes
    the guard decision and spawns `ops_local_refresh.py --run` DETACHED
    (self-daemonized child that survives the session);
  - stdout must stay EMPTY (strict JSON hook-output schema) and exit code 0
    ALWAYS — a launcher failure must never block a session start; diagnostics
    go to the day's run log instead;
  - the guard logic is imported from ops_local_refresh (single source of
    truth): outside Mon-Fri, before 18:00, already done today, in progress,
    or attempt-capped => silent no-op.

Run standalone for testing:
  uv run python scripts/ops_evening_hook.py   # prints nothing on no-op days
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import ops_local_refresh as lane  # noqa: E402

IS_WINDOWS = sys.platform.startswith("win")

# The hook EXISTS only inside the owner's evening window (Beijing 18:00-23:59;
# before 18:00 is coding-plan peak and not post-close). Outside the window a
# session start does NOTHING AT ALL — no guard evaluation, no state reads, no
# log lines — so restarting ZCode during the day is observably inert, not
# merely a silent skip. (Owner design correction, 2026-09-08.)
WINDOW_OPEN_HOUR = 18
WINDOW_CLOSE_HOUR = 24


def _in_evening_window(now: datetime) -> bool:
    return WINDOW_OPEN_HOUR <= now.hour < WINDOW_CLOSE_HOUR


def main() -> int:
    now = datetime.now()
    if not _in_evening_window(now):
        return 0  # outside 18:00-23:59: the lane does not exist for this session
    decision = lane.guard_decision(now, lane.load_state())
    if decision != "RUN":
        # In-window restart/second session: checked, skipped, nothing ran.
        # One audit line proves the once-per-day semantics held (marker is the
        # actual gate; this trace only makes it visible).
        day_dir = lane.LOG_DIR / now.strftime("%Y-%m-%d")
        day_dir.mkdir(parents=True, exist_ok=True)
        with (day_dir / "hook-spawn.log").open("a", encoding="utf-8") as fh:
            fh.write(f"[{now.isoformat()}] hook skip: {decision}\n")
        return 0
    day_dir = lane.LOG_DIR / now.strftime("%Y-%m-%d")
    day_dir.mkdir(parents=True, exist_ok=True)
    log_path = day_dir / "hook-spawn.log"
    cmd = ["uv", "run", "--project", str(ROOT), "python",
           str(ROOT / "scripts" / "ops_local_refresh.py"), "--run"]
    kwargs: dict = {}
    if IS_WINDOWS:
        # DETACHED_PROCESS: own console-less session, survives the hook and the
        # ZCode process; CREATE_NEW_PROCESS_GROUP: no Ctrl-C coupling.
        kwargs["creationflags"] = (
            subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
    else:
        kwargs["start_new_session"] = True
    try:
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(f"[{datetime.now().isoformat()}] hook spawn: {decision}\n")
            fh.flush()
            subprocess.Popen(
                cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, text=True, **kwargs)
    except OSError as exc:
        # Never fail the session start; the cron backstop retries later.
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(f"[{datetime.now().isoformat()}] hook spawn FAILED: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
