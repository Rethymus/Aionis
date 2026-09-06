"""Local evening refresh lane — the ZCode-cron "temporary server" for the terminal.

Replaces the scheduled (cron) leg of `.github/workflows/refresh-terminal-data.yml`
(which cost 1,300-1,700 GitHub Actions minutes/month on this PRIVATE repo, nearly
exhausting the 2,000 free minutes) with a local run driven by a ZCode workspace
automation (see `docs/ops-local-refresh.md`). The CI workflow keeps its
`workflow_dispatch` trigger as an out-of-band fallback for multi-day outages.

Semantics mirror the CI lane exactly (step order, per-step caps,
continue-on-error, contract gate before commit, pull --rebase before push), with
two local-only additions:
  1. a SUPERSET of fetchers — the warm local cache lets us also refresh the
     panels the CI runner never fetched (def14a/form_d/filing_stream/news_feed/
     ark/theme_etfs/13g/ape_wisdom/ptr_tx/bts/korea), which CI could only
     retain from stale caches. Round-91 completeness audit added three that
     were in NO lane at all: form13f star-manager holdings + the 13F filer
     directory (the filers13f panel had been drifting since 08-21), and
     stakes_pct_parse — the pct_now/pct_prev second stage for the visible
     13G/13D rows (live smart_money showed 120/120 null pct before this),
     followed by a second export pass that folds the parsed values in.
     Deliberately EXCLUDED (research surfaces, not display): the A-share
     CSI300 fetch/panel builders (ic_deciles CN lineage) and the regime
     global/composite/meso layer builders (no terminal panel reads them);
  2. a once-per-evening marker (`data/ops/local_refresh_state.json`, gitignored)
     so the recurring ZCode automation can fire every 20 minutes and no-op
     cheaply after the day's successful run.

Anti-leakage contract (inherited, non-negotiable):
  - DISPLAY-ONLY lane. No frozen config, no ledger commits, no research/OOS
    surface. Commits exactly `web/src/data/aionis/` + `reports/evidence/`.
  - The reddit/news collectors legitimately append `data_ingest` rows to
    `runs/ledger.jsonl` during fetches; this lane discards those display-only
    appends (exactly what the CI ephemeral runner did implicitly) and NEVER
    commits or discards anything else in the ledger.

Usage:
  uv run python scripts/ops_local_refresh.py --guard   # cron entry: RUN | SKIP:<reason>
  uv run python scripts/ops_local_refresh.py --run     # full evening lane
  uv run python scripts/ops_local_refresh.py --run --force   # bypass guard (human)
  uv run python scripts/ops_local_refresh.py --status  # print marker state

Exit codes: 0 = done (committed / no-change / clean skip), 1 = failed this
attempt (cron retries on the next fire; 3 failures per evening self-lock).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_FILE = ROOT / "data" / "ops" / "local_refresh_state.json"
LOG_DIR = ROOT / "runs" / "ops_local_refresh"
LEDGER = ROOT / "runs" / "ledger.jsonl"
ALLOWED_COMMIT_PATHS = ("web/src/data/aionis", "reports/evidence")
GATE_TEST = "tests/test_web_terminal_data.py"
GATE_DESELECT = f"{GATE_TEST}::test_ledger_append_only_not_mutated_by_export"

# Guard policy (host-local time == the owner's Beijing evening).
WINDOW_OPEN_HOUR = 18
MAX_ATTEMPTS_PER_EVENING = 3
RUNNING_STALE_MINUTES = 90

IS_WINDOWS = sys.platform.startswith("win")

# Step = dict(name, uv_argv after "uv run", cap minutes, soft=continue-on-error).
# Order mirrors the CI lane; [local superset] steps are the warm-cache additions.
MACRO_INLINE = (
    "from aionis.ingest.macro_display import fetch_display_series; "
    "from aionis.ingest.macro_dff import fetch_dff_vintages; "
    "from aionis.config import settings; from pathlib import Path; "
    "c=Path('data/cache'); [fetch_display_series(settings.fred_api_key, c, s, "
    "force=True) for s in ('CPIAUCSL','PAYEMS')]; "
    "fetch_dff_vintages(settings.fred_api_key, c)"
)
DOSSIER_META = (
    "import sys; sys.path.insert(0, 'scripts'); "
    "from export_research_dossier import export_phase_dossier_meta; "
    "export_phase_dossier_meta()"
)
SHELF_MATRIX = (
    "import sys; sys.path.insert(0, 'scripts'); "
    "from export_terminal_data import export_knowledge_shelf; "
    "from export_evidence_html import export_evidence_matrix_manifest; "
    "export_knowledge_shelf(); export_evidence_matrix_manifest()"
)


def _py(script: str, *args: str) -> dict:
    return {"uv_argv": ["python", script, *args]}


STEPS: list[dict] = [
    {"name": "cot_fetch", **_py("scripts/cot_fetch.py"), "cap": 10, "soft": True},
    {"name": "form4_fetch", **_py("scripts/form4_fetch.py"), "cap": 20, "soft": True},
    {"name": "stakes_13d_daily_fetch",
     **_py("scripts/stakes_13d_daily_fetch.py"), "cap": 40, "soft": True},
    {"name": "form8k_fetch", **_py("scripts/form8k_fetch.py"), "cap": 10, "soft": True},
    {"name": "form_ipo_fetch",
     **_py("scripts/form_ipo_fetch.py"), "cap": 10, "soft": True},
    {"name": "form_ipo_price_parse",
     **_py("scripts/form_ipo_price_parse.py"), "cap": 10, "soft": True},
    {"name": "def14a_fetch [local superset]",
     **_py("scripts/def14a_fetch.py"), "cap": 10, "soft": True},
    {"name": "def14a_persons_fetch [local superset]",
     **_py("scripts/def14a_persons_fetch.py"), "cap": 10, "soft": True},
    {"name": "form_d_fetch [local superset]",
     **_py("scripts/form_d_fetch.py"), "cap": 10, "soft": True},
    {"name": "filing_stream_fetch [local superset]",
     **_py("scripts/filing_stream_fetch.py"), "cap": 15, "soft": True},
    {"name": "news_feed_fetch [local superset]",
     **_py("scripts/news_feed_fetch.py"), "cap": 10, "soft": True},
    {"name": "ark_holdings_fetch [local superset]",
     **_py("scripts/ark_holdings_fetch.py"), "cap": 10, "soft": True},
    {"name": "theme_etfs_fetch [local superset]",
     **_py("scripts/theme_etfs_fetch.py"), "cap": 10, "soft": True},
    {"name": "stakes13g_fetch [local superset]",
     **_py("scripts/stakes13g_fetch.py"), "cap": 15, "soft": True},
    {"name": "form13f_fetch (star managers) [local superset]",
     **_py("scripts/form13f_fetch.py"), "cap": 15, "soft": True},
    {"name": "form13f_dir_fetch (filer directory) [local superset]",
     **_py("scripts/form13f_dir_fetch.py"), "cap": 20, "soft": True},
    {"name": "ape_wisdom_fetch [local superset]",
     **_py("scripts/ape_wisdom_fetch.py"), "cap": 5, "soft": True},
    {"name": "politician_trades_fetch",
     **_py("scripts/politician_trades_fetch.py"), "cap": 10, "soft": True},
    {"name": "politician_trades_tx_fetch [local superset]",
     **_py("scripts/politician_trades_tx_fetch.py"), "cap": 10, "soft": True},
    {"name": "reddit_fetch", **_py("scripts/reddit_fetch.py"), "cap": 10, "soft": True},
    {"name": "bts_tsi_fetch [local superset]",
     **_py("scripts/bts_tsi_fetch.py"), "cap": 10, "soft": True},
    {"name": "korea_proxy_fetch [local superset]",
     **_py("scripts/korea_proxy_fetch.py"), "cap": 10, "soft": True},
    {"name": "fetch_macro_display",
     **_py("scripts/fetch_macro_display.py", "--force"), "cap": 10, "soft": True},
    {"name": "market_prices_fetch (VIX)",
     **_py("scripts/market_prices_fetch.py"), "cap": 10, "soft": True},
    {"name": "news_sentiment_gdelt_fetch",
     **_py("scripts/news_sentiment_gdelt_fetch.py"), "cap": 20, "soft": True},
    {"name": "macro panel inputs (CPIAUCSL/PAYEMS/DFF)",
     "uv_argv": ["python", "-c", MACRO_INLINE], "cap": 10, "soft": True},
    {"name": "phase_b_fetch fundamentals (display)",
     **_py("scripts/phase_b_fetch.py", "--display", "--fundamentals-only"),
     "cap": 25, "soft": True},
    {"name": "phase_b_fetch prices (display, budget 24m)",
     **_py("scripts/phase_b_fetch.py", "--display", "--budget-minutes", "24"),
     "cap": 27, "soft": True},
    {"name": "track_b_materialize_panel (display)",
     **_py("scripts/track_b_materialize_panel.py", "--display"), "cap": 15,
     "soft": True},
    {"name": "build_ticker_metadata",
     "uv_argv": ["--with", "baostock", "python",
                 "scripts/build_ticker_metadata.py", "--no-cache"],
     "cap": 10, "soft": True},
    {"name": "build_regime_macro",
     **_py("scripts/build_regime_macro.py"), "cap": 10, "soft": True},
    {"name": "export_terminal_data",
     **_py("scripts/export_terminal_data.py"), "cap": 30, "soft": False},
    {"name": "stakes_pct_parse (visible 13G/13D rows) [local superset]",
     **_py("scripts/stakes_pct_parse.py"), "cap": 35, "soft": True},
    {"name": "export pass 2 (pick up parsed pct)",
     **_py("scripts/export_terminal_data.py"), "cap": 30, "soft": True},
    {"name": "export_evidence_html",
     **_py("scripts/export_evidence_html.py"), "cap": 10, "soft": True},
    {"name": "export_research_dossier",
     **_py("scripts/export_research_dossier.py"), "cap": 10, "soft": True},
    {"name": "export_phase_dossier_meta",
     "uv_argv": ["python", "-c", DOSSIER_META], "cap": 10, "soft": True},
    {"name": "export shelf + evidence matrix",
     "uv_argv": ["python", "-c", SHELF_MATRIX], "cap": 10, "soft": True},
    {"name": "json validity + contract gate",
     "uv_argv": ["pytest", "-q", GATE_TEST, "--deselect", GATE_DESELECT],
     "cap": 45, "soft": False},
]


def log(line: str, fh=None) -> None:
    stamp = datetime.now().strftime("%H:%M:%S")
    text = f"[{stamp}] {line}"
    print(text, flush=True)
    if fh is not None:
        fh.write(text + "\n")
        fh.flush()


# ---------------------------------------------------------------- guard / state

def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def guard_decision(now: datetime, state: dict) -> str:
    """Pure guard: return 'RUN' or 'SKIP:<reason>'. Host-local time is the
    owner's evening clock (the ZCode cron schedules in the same clock)."""
    today = now.strftime("%Y-%m-%d")
    if now.weekday() >= 5:
        return f"SKIP:weekend ({now.strftime('%a')} — no US weekday session to refresh)"
    if now.hour < WINDOW_OPEN_HOUR:
        return (f"SKIP:window-not-open (before {WINDOW_OPEN_HOUR}:00 local — "
                "coding-plan peak hours and not post-close)")
    if state.get("date") == today:
        status = state.get("status")
        if status in ("ok_committed", "ok_nochange"):
            return f"SKIP:already-done ({status}, commit={state.get('commit')})"
        if status == "running":
            started = state.get("started_at_epoch", 0)
            age_min = (time.time() - started) / 60 if started else RUNNING_STALE_MINUTES
            if age_min < RUNNING_STALE_MINUTES:
                return (f"SKIP:in-progress (started {age_min:.0f}min ago, "
                        f"stale cap {RUNNING_STALE_MINUTES}min)")
            return "RUN"  # stale 'running' marker = crashed run; retry allowed
        if int(state.get("attempts", 0)) >= MAX_ATTEMPTS_PER_EVENING:
            return (f"SKIP:attempt-cap ({state.get('attempts')} failures today — "
                    "human review needed: runs/ops_local_refresh log")
    return "RUN"


# ------------------------------------------------------------------- subprocess

def kill_tree(proc: subprocess.Popen) -> None:
    if IS_WINDOWS:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                       capture_output=True, check=False)
    else:
        import os
        import signal
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except OSError:
            pass


def run_step(step: dict, fh) -> tuple[bool, str]:
    """Run one step; returns (ok, detail). Timeout kills the whole process tree
    (CI postmortem: orphan writers corrupt the fetch caches)."""
    name = step["name"]
    cmd = ["uv", "run", *step["uv_argv"]]
    kwargs: dict = {}
    if IS_WINDOWS:
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    log(f"STEP {name} (cap {step['cap']}m)", fh)
    t0 = time.time()
    try:
        proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True,
                                encoding="utf-8", errors="replace", **kwargs)
    except OSError as exc:
        log(f"STEP {name}: SPAWN-FAIL {exc}", fh)
        return False, f"spawn-fail: {exc}"
    try:
        out, _ = proc.communicate(timeout=step["cap"] * 60)
        rc = proc.returncode
    except subprocess.TimeoutExpired:
        kill_tree(proc)
        try:
            out, _ = proc.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            out = ""
        detail = f"timeout after {step['cap']}m (tree-killed)"
        _log_step_end(fh, name, False, (time.time() - t0) / 60, detail, out)
        return False, detail
    if out and fh is not None:
        fh.write(out + ("\n" if not out.endswith("\n") else ""))
    ok = rc == 0
    detail = "" if ok else f"exit {rc}"
    _log_step_end(fh, name, ok, (time.time() - t0) / 60, detail, out)
    return ok, detail


def _log_step_end(fh, name: str, ok: bool, minutes: float, detail: str,
                  out: str) -> None:
    tail = [ln for ln in (out or "").splitlines() if ln.strip()][-3:]
    if tail:
        detail = f"{detail}; tail: {' | '.join(tail)}" if detail else \
            f"tail: {' | '.join(tail)}"
    log(f"STEP {name}: {'OK' if ok else 'FAIL'} ({minutes:.1f}m) {detail}", fh)


# ------------------------------------------------------------------------ git

def git(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git"] + args, cwd=ROOT, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", check=check)


def ledger_display_appends_only(added_lines: list[str]) -> bool:
    """True iff every added ledger line is a display-lane data_ingest row
    (reddit/news_feed collectors) — the only appends this lane may discard."""
    if not added_lines:
        return False
    for line in added_lines:
        try:
            row = json.loads(line)
        except ValueError:
            return False
        if row.get("event") != "data_ingest":
            return False
        if row.get("dataset") not in ("reddit_sentiment", "news_feed"):
            return False
    return True


def tidy_ledger(fh) -> str:
    """Discard display-only ledger appends (CI ephemeral-runner semantics).
    Anything else is left untouched and reported — never committed here."""
    diff = git(["diff", "--", "runs/ledger.jsonl"], check=False).stdout
    added = [ln[1:] for ln in diff.splitlines()
             if ln.startswith("+") and not ln.startswith("+++")]
    if not added:
        return "clean"
    if ledger_display_appends_only(added):
        git(["restore", "--", "runs/ledger.jsonl"], check=False)
        log(f"ledger: discarded {len(added)} display-only data_ingest append(s) "
            "(reddit/news_feed; CI-runner semantics)", fh)
        return "discarded-display-appends"
    log(f"ledger: NON-DISPLAY changes present ({len(added)} line(s)) — left "
        "untouched, NOT committed by this lane", fh)
    return "foreign-changes-left-dirty"


def commit_and_push(fh) -> tuple[str, str | None, bool, int]:
    """Returns (status, commit_sha, pushed, n_files). Pull-rebase before push —
    the CI lane once lost a whole run to a non-ff rejection; same medicine."""
    branch = git(["rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
    if branch != "main":
        raise RuntimeError(f"refusing to run the data lane on branch '{branch}'")
    for path in ALLOWED_COMMIT_PATHS:
        git(["add", path], check=False)
    staged = [ln for ln in git(["diff", "--cached", "--name-only"])
              .stdout.splitlines() if ln.strip()]
    if not staged:
        return "ok_nochange", None, False, 0
    msg = ("chore(data): evening terminal refresh (local ops lane) — "
           f"{datetime.now().strftime('%Y-%m-%d')}")
    git(["commit", "-m", msg])
    sha = git(["rev-parse", "HEAD"]).stdout.strip()
    pull = git(["pull", "--rebase", "--autostash", "origin", "main"], check=False)
    if pull.returncode != 0:
        raise RuntimeError(
            f"pull --rebase failed: {(pull.stdout + pull.stderr)[-500:]}")
    push = git(["push", "origin", "main"], check=False)
    if push.returncode != 0:
        raise RuntimeError(f"push failed: {(push.stdout + push.stderr)[-500:]}")
    log(f"git: committed {sha[:9]} ({len(staged)} files) + pushed to origin/main",
        fh)
    return "ok_committed", sha, True, len(staged)


def verify_publish_triggered() -> str:
    """Best-effort: our push (user PAT, not GITHUB_TOKEN) fires publish-site.yml,
    which builds + publishes gh-pages. Failure here is non-fatal."""
    try:
        out = subprocess.run(
            ["gh", "run", "list", "--workflow=publish-site.yml", "-L", "1",
             "--json", "status,createdAt,conclusion"],
            cwd=ROOT, capture_output=True, text=True, timeout=20)
        if out.returncode == 0:
            return out.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return "not-verified (gh unavailable)"


# ------------------------------------------------------------------------- main

def do_run(force: bool) -> int:
    now = datetime.now()
    state = load_state()
    decision = guard_decision(now, state)
    if decision != "RUN" and not force:
        print(decision)
        return 0
    if force and decision != "RUN":
        log(f"--force: overriding guard decision '{decision}'", None)

    today = now.strftime("%Y-%m-%d")
    attempts = state.get("attempts", 0) + 1 if state.get("date") == today else 1
    day_dir = LOG_DIR / today
    day_dir.mkdir(parents=True, exist_ok=True)
    with (day_dir / "run.log").open("a", encoding="utf-8") as fh:
        state.update({"date": today, "attempts": attempts, "status": "running",
                      "started_at_epoch": time.time(), "force": force})
        save_state(state)
        log(f"=== evening lane start {datetime.now().isoformat()} "
            f"(attempt {attempts}/{MAX_ATTEMPTS_PER_EVENING}) ===", fh)
        t0 = time.time()
        soft_fails: list[str] = []
        try:
            for step in STEPS:
                ok, detail = run_step(step, fh)
                if not ok:
                    if step["soft"]:
                        soft_fails.append(step["name"])
                    else:
                        raise RuntimeError(
                            f"hard-fail step '{step['name']}': {detail}")
            ledger_note = tidy_ledger(fh)
            status, sha, pushed, n_files = commit_and_push(fh)
            publish = verify_publish_triggered() if pushed else "skipped (no push)"
            state.update({"status": status, "commit": sha, "pushed": pushed,
                          "n_files": n_files,
                          "finished_at": datetime.now().isoformat()})
            save_state(state)
            summary = {
                "date": today, "status": status, "commit": sha, "pushed": pushed,
                "n_files": n_files, "soft_fails": soft_fails,
                "ledger": ledger_note, "publish_site": publish,
                "wall_minutes": round((time.time() - t0) / 60, 1),
            }
            log(f"SUMMARY {json.dumps(summary, ensure_ascii=False)}", fh)
            print(f"SUMMARY {json.dumps(summary, ensure_ascii=False)}")
            return 0
        except Exception as exc:  # noqa: BLE001 — unattended lane: always mark + report
            state.update({"status": "failed", "error": str(exc)[:800],
                          "finished_at": datetime.now().isoformat()})
            save_state(state)
            log(f"HARD-FAIL: {exc}", fh)
            print(f"FAILED: {exc}")
            return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--guard", action="store_true",
                       help="print RUN or SKIP:<reason>")
    group.add_argument("--run", action="store_true", help="run the evening lane")
    group.add_argument("--status", action="store_true", help="print marker state")
    parser.add_argument("--force", action="store_true",
                        help="with --run: bypass the guard (human use only)")
    args = parser.parse_args()
    if args.guard:
        print(guard_decision(datetime.now(), load_state()))
        return 0
    if args.status:
        print(json.dumps(load_state(), ensure_ascii=False, indent=2))
        return 0
    return do_run(args.force)


if __name__ == "__main__":
    raise SystemExit(main())
