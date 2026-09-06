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


def main() -> int:
    decision = lane.guard_decision(datetime.now(), lane.load_state())
    if decision != "RUN":
        return 0  # silent: weekend / pre-window / already-done / in-progress / capped
    day_dir = lane.LOG_DIR / datetime.now().strftime("%Y-%m-%d")
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
