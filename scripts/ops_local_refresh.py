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
  uv run python scripts/ops_local_refresh.py --status --json  # marker as machine JSON
  uv run python scripts/ops_local_refresh.py --doctor --json  # preflight as machine JSON

Exit codes: 0 = done (committed / no-change / clean skip), 1 = failed this
attempt (cron retries on the next fire; 3 failures per evening self-lock).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_FILE = ROOT / "data" / "ops" / "local_refresh_state.json"
LOG_DIR = ROOT / "runs" / "ops_local_refresh"
LEDGER = ROOT / "runs" / "ledger.jsonl"
ALLOWED_COMMIT_PATHS = ("web/src/data/aionis", "reports/evidence")
GATE_TEST = "tests/test_web_terminal_data.py"
# The knowledge-shelf contract pins evidence-artifact sha256s against the repo
# (the drift alarm). The first live run proved the gate must cover it: the
# shelf re-export lived in the step that crashed on the matrix ImportError,
# the narrow gate passed, and CI's full suite correctly went red.
GATE_TEST_2 = "tests/test_knowledge_shelf_panel_contract.py"
# Round 190: the lane re-renders the evidence chain (dossier -> shelf ->
# matrix + web mirror), so the gate must verify that chain BEFORE push —
# otherwise a partial re-render ships and only CI's full suite goes red
# (round 182's live lesson: the lane commits, then discovers).
GATE_TEST_3 = "tests/test_research_dossier_pipeline.py"
GATE_TESTS_EV = (
    "tests/test_evidence_matrix_manifest.py",
    "tests/test_evidence_matrix_panel_contract.py",
)
GATE_DESELECT = f"{GATE_TEST}::test_ledger_append_only_not_mutated_by_export"

# Guard policy (host-local time == the owner's Beijing evening).
WINDOW_OPEN_HOUR = 18
MAX_ATTEMPTS_PER_EVENING = 3
RUNNING_STALE_MINUTES = 90

IS_WINDOWS = sys.platform.startswith("win")


def _us_holiday_today(now: datetime) -> bool:
    """True when the NYSE calendar (canonical project wrapper) says the US
    trading day corresponding to this Beijing evening is a holiday. In the
    18:00-23:59 Beijing window the US calendar date equals the local date.
    Fail-open (-> False, treat as trading day): freshness outranks energy
    savings whenever the calendar is unavailable."""
    try:
        import pandas as pd

        from aionis.features.alignment import nyse_sessions

        day = pd.Timestamp(now.date())
        return len(nyse_sessions(day, day)) == 0
    except Exception:  # noqa: BLE001 — fail-open by design
        return False

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
     # Round 138: dropped --no-cache — the nightly lane burned its full 10m
     # cap on a whole-universe baostock refetch (query_stock_industry) that
     # timed out EVERY night (soft-fail since at least 2026-10-01) while
     # stock_universe is a FROZEN panel by design and CSRC industry data
     # changes at an annual pace. Cached mode rebuilds in seconds; the
     # manual --no-cache refetch stays available for industry-data bumps
     # (see the script docstring).
     "uv_argv": ["--with", "baostock", "python",
                 "scripts/build_ticker_metadata.py"],
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
    {"name": "data snapshot audit (history-rewrite tripwire, round 225)",
     **_py("scripts/data_snapshot_audit.py"), "cap": 5, "soft": True},
    {"name": "json validity + contract gate",
     "uv_argv": ["pytest", "-q", GATE_TEST, GATE_TEST_2, GATE_TEST_3,
                 *GATE_TESTS_EV,
                 "--deselect", GATE_DESELECT],
     "cap": 45, "soft": False},
]


def strict_json_scan() -> list[str]:
    """STRICT-parse every committed panel: reject NaN/Infinity tokens.

    Python's json both writes and reads bare NaN, so pytest contract tests
    tolerate what strict consumers (Turbopack/browsers) reject — the 09-11
    publish-site outage shipped exactly that. Returns problem descriptions;
    empty = clean. Runs pre-commit in the gate step (hard-fail).
    """
    problems: list[str] = []

    def _reject(tok: str):
        raise ValueError(f"non-strict JSON token: {tok}")

    for f in sorted((ROOT / "web/src/data/aionis").glob("*.json")):
        try:
            json.loads(f.read_text(encoding="utf-8"), parse_constant=_reject)
        except ValueError as exc:
            problems.append(f"{f.name}: {exc}")
    return problems


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
    # Energy-saving holiday skip — ONLY when no catch-up work is pending
    # (soft-fails from the last run, e.g. a partially-parsed pct set or a
    # rate-limited price convergence). On a holiday with pending catch-up the
    # lane still runs: EDGAR archives stay reachable, GDELT/macro advance.
    if not state.get("soft_fails") and _us_holiday_today(now):
        return ("SKIP:holiday-us (NYSE closed and no catch-up pending — "
                "energy-saving skip; --force overrides)")
    # Liveness is date-independent (2026-09-21 round 99): a lane started before
    # midnight is STILL RUNNING when its marker says "yesterday" — the old
    # date-scoped check let a second lane start next to it (the 00:56 near
    # miss). Any running marker younger than the stale cap blocks a new run.
    if state.get("status") == "running":
        started = state.get("started_at_epoch", 0)
        age_min = (time.time() - started) / 60 if started else RUNNING_STALE_MINUTES
        if age_min < RUNNING_STALE_MINUTES:
            return (f"SKIP:in-progress (started {age_min:.0f}min ago, "
                    f"stale cap {RUNNING_STALE_MINUTES}min — "
                    f"marker date {state.get('date')})")
    if state.get("date") == today:
        status = state.get("status")
        if status in ("ok_committed", "ok_nochange"):
            # Evening-completion rule (2026-09-28 round 102): only a run that
            # STARTED at/after 18:00 local counts as "the evening lane ran".
            # A morning/midday catch-up (e.g. the 09-21 00:56 recovery) fetches
            # the PREVIOUS session's data and misses that day's daytime
            # filings/macro/news — it must not suppress the evening run.
            started = state.get("started_at_epoch", 0)
            evening_started = (
                not started  # legacy marker without epoch: keep old semantics
                or datetime.fromtimestamp(started).hour >= WINDOW_OPEN_HOUR)
            if evening_started:
                return f"SKIP:already-done ({status}, commit={state.get('commit')})"
            # Pre-18:00 completion (morning/midday catch-up): does NOT cover
            # the evening data window — fall through to RUN so the evening
            # Task Scheduler/hook fire refreshes the day's daytime deltas.
            pass
        if status == "running":
            return "RUN"  # stale 'running' marker = crashed run; retry allowed
        if (status not in ("ok_committed", "ok_nochange")
                and int(state.get("attempts", 0)) >= MAX_ATTEMPTS_PER_EVENING):
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
    # Force UTF-8 mode for every child (PEP 540): the 2026-09-10/11 outage was
    # GBK locale crashes on Windows — bare read_text() on a panel JSON with a
    # curly quote (byte 0x94), a bare write_text() on Reddit posts with emoji,
    # and print() of a ✓ checkmark; PYTHONUTF8 fixes all three classes at once
    # for every current and future bare-I/O site in the chain.
    kwargs["env"] = {"PYTHONUTF8": "1", **os.environ}
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


def _actions_paused() -> bool | None:
    """Round 129 (owner pause order 2026-11-11): True when BOTH lane-relevant
    workflows (Tests + Publish site) are non-active (disabled_manually &c) —
    the own-commit poll below would then never see a run for our sha and burn
    its full bounded window every evening. False = at least one active
    (unlock-transition: keep the honest poll for whichever still runs).
    None = state unreadable — fail-open to the poll exactly as before."""
    try:
        nwo = subprocess.run(
            ["gh", "repo", "view", "--json", "nameWithOwner",
             "-q", ".nameWithOwner"],
            cwd=ROOT, capture_output=True, text=True, timeout=20)
        if nwo.returncode != 0 or not nwo.stdout.strip():
            return None
        repo = nwo.stdout.strip()
        states: list[str] = []
        for wf_file in ("ci.yml", "publish-site.yml"):
            out = subprocess.run(
                ["gh", "api",
                 f"repos/{repo}/actions/workflows/{wf_file}", "-q", ".state"],
                cwd=ROOT, capture_output=True, text=True, timeout=20)
            if out.returncode != 0:
                return None
            states.append(out.stdout.strip())
        return all(s and s != "active" for s in states)
    except (OSError, subprocess.TimeoutExpired):
        return None


def verify_own_commit_ci(sha: str, max_wait_s: int = 360) -> dict:
    """Zero-token red-card detection (round 107): poll OUR commit's CI runs.

    The nightly LLM report checks the LATEST runs, which may belong to
    another session's push in this multi-session repo; this polls exactly
    the runs for the sha THIS lane pushed (publish-site + Tests), bounded,
    non-fatal on gh failure. Returns {"publish_site": ..., "tests": ...}
    with per-workflow conclusions or a not-verified marker."""

    def _runs_for(commit: str) -> dict:
        out = subprocess.run(
            ["gh", "run", "list", "--commit", commit, "--limit", "10",
             "--json", "workflowName,status,conclusion"],
            cwd=ROOT, capture_output=True, text=True, timeout=20)
        if out.returncode != 0:
            return {}
        try:
            return {r["workflowName"]: r for r in json.loads(out.stdout)}
        except (ValueError, KeyError):
            return {}

    deadline = time.time() + max_wait_s
    wanted = ("Publish site (gh-pages)", "Tests")
    if _actions_paused():
        # Owner pause order 2026-11-11: no run can ever appear for our sha —
        # record the pause instead of burning the bounded window nightly.
        return {k: "paused(actions-disabled)" for k in wanted}
    while time.time() < deadline:
        runs = _runs_for(sha)
        done = {k: runs[k].get("conclusion") for k in wanted if k in runs}
        if len(done) == len(wanted) and all(
                v in ("success", "failure") for v in done.values()):
            return done  # both concluded
        time.sleep(45)
    final = _runs_for(sha)
    return {k: (final.get(k) or {}).get("conclusion", "not-observed")
            for k in wanted}


# ------------------------------------------------- Fast-Path failure triage
# Round 126 (super-agent落点二): deterministic pre-LLM noise filter. The 11-05
# billing lock (#2) kept every Actions workflow instantly red for days —
# unclassified, that noise would burn the 23:35 report + duty attention every
# evening. Three buckets: platform-failure (owner key), infra-transient
# (existing retry-soft surface), code-defect (report + disposition). The
# trigger→criteria→action modelling per docs/ops-local-refresh.md
# §失败处置矩阵与节奏; pattern borrowed from StackStorm (Apache-2.0), no platform.

TRIAGE_PLATFORM = "platform-failure"
TRIAGE_INFRA = "infra-transient"
TRIAGE_CODE = "code-defect"

# Billing-locked runs die in ~3-4s (measured 2026-11-05/11: gh run list);
# real Tests/publish-site runs take minutes. Fast reds need a *confirmed*
# platform signature — an unconfirmed fast red stays code-defect (human eyes;
# conservative by design, never guess).
TRIAGE_PLATFORM_MAX_S = 60
_TRIAGE_BILLING_RE = re.compile(r"billing", re.IGNORECASE)
_PUSH_TRANSIENT_RE = re.compile(r"push failed", re.IGNORECASE)
# gen2 item 2 (night-package-threading): contract-gate hard-fails carry the
# step name in this shape (do_run raises f"hard-fail step '{name}': {detail}").
_HARDFAIL_STEP_RE = re.compile(r"hard-fail step '([^']+)'")


def classify_run_row(row: dict, jobs: dict | None) -> str:
    """Pure rule: one gh run row + optional jobs probe -> triage bucket.

    platform-failure requires BOTH a fast failure (<TRIAGE_PLATFORM_MAX_S)
    and a platform signature from the jobs probe (billing annotation, or
    zero defined steps — the billing-lock signature: the job never starts).
    Missing/unmeasurable anything -> code-defect."""
    try:
        t0 = datetime.fromisoformat(str(row["createdAt"]).replace("Z", "+00:00"))
        t1 = datetime.fromisoformat(str(row["updatedAt"]).replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError):
        return TRIAGE_CODE
    if (t1 - t0).total_seconds() >= TRIAGE_PLATFORM_MAX_S:
        return TRIAGE_CODE
    if jobs is None:
        return TRIAGE_CODE
    if jobs.get("billing_annotation") or jobs.get("n_steps_defined") == 0:
        return TRIAGE_PLATFORM
    return TRIAGE_CODE


def _gh_repo_slug() -> str | None:
    try:
        out = subprocess.run(
            ["gh", "repo", "view", "--json", "nameWithOwner",
             "--jq", ".nameWithOwner"],
            cwd=ROOT, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    slug = out.stdout.strip()
    return slug if out.returncode == 0 and slug else None


def _gh_run_rows(sha: str) -> dict:
    """gh run list rows with timing, scoped to OUR commit (read-only; {}
    on any gh failure — triage must never break the lane or guess)."""
    try:
        out = subprocess.run(
            ["gh", "run", "list", "--commit", sha, "--limit", "10",
             "--json",
             "databaseId,workflowName,conclusion,createdAt,updatedAt"],
            cwd=ROOT, capture_output=True, text=True, timeout=20)
        if out.returncode != 0:
            return {}
        return {r["workflowName"]: r for r in json.loads(out.stdout)}
    except (OSError, ValueError, subprocess.TimeoutExpired, KeyError):
        return {}


def _gh_jobs_signature(run_id: int) -> dict | None:
    """Read-only probe of one run's jobs: defined-step count + billing
    annotation. None when gh is unavailable (caller stays conservative)."""
    slug = _gh_repo_slug()
    if slug is None:
        return None
    try:
        out = subprocess.run(
            ["gh", "api", f"repos/{slug}/actions/runs/{run_id}/jobs",
             "--jq", "[.jobs[] | {id, steps: (.steps // [] | length)}]"],
            cwd=ROOT, capture_output=True, text=True, timeout=20)
        if out.returncode != 0:
            return None
        jobs = json.loads(out.stdout)
        # Defensive parse (gh/jq shape drift must degrade to None, not crash):
        n_steps = sum(
            int(s[0]) if isinstance(s := j.get("steps"), list) and s
            else int(s or 0)
            for j in jobs)
    except (OSError, ValueError, subprocess.TimeoutExpired,
            KeyError, TypeError):
        return None
    billing = False
    for job in jobs:
        try:
            ann = subprocess.run(
                ["gh", "api",
                 f"repos/{slug}/check-runs/{job['id']}/annotations",
                 "--jq", "[.[].message]"],
                cwd=ROOT, capture_output=True, text=True, timeout=20)
            if ann.returncode == 0 and any(
                    _TRIAGE_BILLING_RE.search(str(m))
                    for m in json.loads(ann.stdout)):
                billing = True
                break
        except (OSError, ValueError, subprocess.TimeoutExpired,
                KeyError, TypeError):
            continue
    return {"n_steps_defined": n_steps, "billing_annotation": billing}


def triage_ci(ci: dict, sha: str | None) -> dict:
    """Classify the lane's own red CI conclusions (round 126). gh probes are
    read-only and non-fatal; runs once per evening after verify_own_commit_ci.
    Returns {"<workflow>": bucket} for failure conclusions only."""
    out: dict[str, str] = {}
    if not isinstance(ci, dict):
        return out
    has_red = any(v == "failure" for v in ci.values())
    rows = _gh_run_rows(sha) if (sha and has_red) else {}
    for workflow, conclusion in ci.items():
        if conclusion != "failure":
            continue
        row = rows.get(workflow) or {}
        run_id = row.get("databaseId")
        jobs = _gh_jobs_signature(int(run_id)) if run_id else None
        out[workflow] = classify_run_row(row, jobs)
    return out


def triage_state(state: dict) -> dict:
    """Three-bucket triage of the whole marker (gh-free, instant): the
    pre-computed per-workflow buckets from state['ci_triage'], soft/persistent
    soft-fails and push-transient errors -> infra-transient (the existing
    --retry-soft / push-only recovery surface), everything else -> code-defect.

    gen2 item 2 (night-package-threading): entries carry Thread stable IDs
    (the registry in docs/ops-local-refresh.md §值班协议行为准则) so
    handoff round entries and the --propose engine dedup keys can reference
    them — platform reds FOLD into one counted line (batching: N workflows
    -> 1 line, a steady-state token cut; owner-key area, never itemized),
    code-bucket CI reds become thread:ci-red:<workflow>, and contract-gate
    hard-fail lane errors become thread:guard-fail:<step>. Unshaped lane
    errors keep the conservative lane-error:<text> line (never guessed)."""
    infra: list[str] = [str(x) for x in (state.get("soft_fails") or [])]
    infra += [f"persistent:{x}"
              for x in (state.get("persistent_soft_fails") or [])]
    code: list[str] = []
    platform: list[str] = []
    err = str(state.get("error") or "")
    if err:
        if _PUSH_TRANSIENT_RE.search(err):
            infra.append("lane-error:push-transient")
        else:
            step = _HARDFAIL_STEP_RE.search(err)
            code.append(f"thread:guard-fail:{step.group(1)}" if step
                        else f"lane-error:{err[:120]}")
    for workflow, bucket in (state.get("ci_triage") or {}).items():
        if bucket == TRIAGE_PLATFORM:
            platform.append(workflow)
        elif bucket == TRIAGE_CODE:
            code.append(f"thread:ci-red:{workflow}")
    if platform:
        platform = [f"thread:platform-billing: {len(platform)}× "
                    f"{TRIAGE_PLATFORM} → §5 钥匙区"]
    return {TRIAGE_PLATFORM: platform, TRIAGE_INFRA: infra,
            TRIAGE_CODE: code}


def _monthly_reports_ref() -> dict:
    """One-hop summary (chain of recall, gen2 item 2) for the monthly-review
    reports: newest *monthly-review*.md by name + its H1 as the one-line
    state — the month-end session learns "which report is latest" without a
    tool round-trip. Bounded local IO (dir glob + first ~40 lines of ONE
    file), network-free, honest absence when none exist yet."""
    audits = ROOT / "reports" / "audits"
    reports = sorted(audits.glob("*monthly-review*.md")) if audits.is_dir() \
        else []
    if not reports:
        return {"path": "reports/audits/", "status": "尚无月报在册"}
    latest = reports[-1]
    title = ""
    try:
        with latest.open("r", encoding="utf-8") as fh:
            for _, line in zip(range(40), fh, strict=False):
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
    except OSError:
        title = ""
    status = f"最新月报 {latest.name}"
    if title:
        status += f"：{title}"
    return {"path": "reports/audits/", "status": status}


def build_night_package(state: dict, now: datetime) -> dict:
    """Inline & Spill night-report context package (round 126): today's lane
    facts inline, historical depth as path references only. Pure-local and
    network-free so the SessionStart hook can refresh it in milliseconds.

    gen2 item 2: refs upgraded from bare paths to {path, status} one-hop
    summaries (chain of recall) — path + ONE line of latest state, still
    never an inlined document body."""
    return {
        "date": state.get("date"),
        "generated_at": now.isoformat(timespec="seconds"),
        "lane": {k: state.get(k) for k in (
            "status", "commit", "pushed", "n_files", "soft_fails",
            "persistent_soft_fails", "ci", "ci_triage", "backup", "error",
            "push_only_recovery") if state.get(k)},
        "threads": triage_state(state),
        "refs": {
            "runbook": {
                "path": "docs/ops-local-refresh.md",
                "status": "晚间通道 runbook：失败处置矩阵/四档节奏/thread "
                          "稳定 ID 登记表/lessons 契约在册",
            },
            "failure_matrix": {
                "path": "docs/ops-local-refresh.md (§失败处置矩阵与节奏)",
                "status": "trigger→criteria→action 处置矩阵 + Fast Path "
                          "三分类（platform/infra/code）",
            },
            "monthly_review": {
                "path": "scripts/monthly_review.py",
                "status": "月评 CLI：--weekly 看门狗 / --lessons 月度复盘 / "
                          "--append-lessons-from 教训写回",
            },
            "monthly_reports": _monthly_reports_ref(),
            "design_report": {
                "path":
                    "reports/design/2026-11-11-super-agent-integration.md",
                "status": "super-agent 整合报告（P0 laneFailing=false；"
                          "钥匙区 §5）；续作 gen2 施工清单="
                          "reports/design/2026-11-11-super-agent-gen2.md",
            },
        },
    }


def write_night_package(now: datetime, state: dict | None = None) -> dict:
    """Refresh runs/ops_local_refresh/<date>/night_package.json (best-effort,
    local-only; failure never breaks a caller). `state` overrides the marker —
    --triage passes its gh-enriched copy so the persisted package matches what
    was printed; the hook omits it (pure-local marker projection)."""
    package = build_night_package(state if state is not None else load_state(),
                                  now)
    try:
        day_dir = LOG_DIR / (package["date"] or now.strftime("%Y-%m-%d"))
        day_dir.mkdir(parents=True, exist_ok=True)
        (day_dir / "night_package.json").write_text(
            json.dumps(package, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
    except OSError:
        pass
    return package


# ------------------------------------------------------------------------- main

LANE_COMMIT_PREFIX = "chore(data): evening terminal refresh"


def _unpushed_lane_commits() -> list[str]:
    """Local commits on main not on origin/main that are ALL lane commits."""
    lines = [ln.strip() for ln in git(
        ["log", "--oneline", "origin/main..HEAD"], check=False).stdout.splitlines()
        if ln.strip()]
    ok = [ln for ln in lines if ln.split(" ", 1)[-1].startswith(LANE_COMMIT_PREFIX)]
    return ok if len(ok) == len(lines) and ok else []


def try_push_only_recovery(prev_status: str, prev_error: str, fh):
    """When the previous attempt failed ONLY at push (transient network, e.g.
    the 2026-09-25 HTTP/2 disconnect) and its commit is still unpushed, a full
    pipeline retry wastes ~an hour re-fetching what is already committed and
    gate-verified — recover by pushing the existing commit(s).

    Returns 'ok_committed' on success, 'failed' on push failure (do_run's
    normal failure path applies), or None when not applicable (fall through
    to the full pipeline)."""
    if prev_status != "failed" or "push failed" not in prev_error:
        return None
    unpushed = _unpushed_lane_commits()
    if not unpushed:
        return None
    log(f"push-only recovery: {len(unpushed)} committed-but-unpushed lane "
        "commit(s) from the previous attempt — retrying push only", fh)
    pull = git(["pull", "--rebase", "--autostash", "origin", "main"], check=False)
    if pull.returncode != 0:
        log(f"push-only recovery: pull --rebase failed "
            f"({(pull.stdout + pull.stderr)[-200:]}) — falling back to full run",
            fh)
        return None
    push = git(["push", "origin", "main"], check=False)
    if push.returncode != 0:
        raise RuntimeError(
            f"push failed: {(push.stdout + push.stderr)[-500:]}")
    sha = git(["rev-parse", "HEAD"]).stdout.strip()
    log(f"push-only recovery: pushed {sha[:9]} — no re-fetch needed", fh)
    return "ok_committed"


# Round 246 (owner-authorized): selective soft-fail retry. The recovery hook
# SKIPs when the evening is ok_committed, so a soft-failed fetch's data stays
# stale until the NEXT evening (~24h worst case; the 10-05..09 GDELT episodes
# demonstrated it). --retry-soft reruns ONLY the soft-failed steps plus the
# export/gate/commit tail — a small pass, never a second full lane.
RETRY_SOFT_AFTER_HOUR = 20  # never before the main lane's window closes in


def do_retry_soft() -> int:
    state = load_state()
    now = datetime.now()
    soft = [x for x in (state.get("soft_fails") or [])
            if not str(x).startswith("push_only")]
    if state.get("date") != now.strftime("%Y-%m-%d") or state.get("status") != "ok_committed":
        print("RETRY-SOFT-SKIP: no same-day ok_committed evening run")
        return 0
    if not soft:
        print("RETRY-SOFT-SKIP: evening had zero soft fails")
        return 0
    if now.hour < RETRY_SOFT_AFTER_HOUR:
        print(f"RETRY-SOFT-SKIP: before {RETRY_SOFT_AFTER_HOUR}:00 (main-lane window)")
        return 0
    # Map soft-failed names to their STEPS entries; keep every export/gate/
    # commit tail step so the retry's commit passes the same guards.
    names = set(soft)
    head = [st for st in STEPS if st["name"] in names]
    tail_names = ("export_terminal_data", "stakes_pct_parse",
                  "export pass 2", "export_evidence_html",
                  "export_research_dossier", "export_phase_dossier_meta",
                  "export shelf + evidence matrix", "json validity")
    tail = [st for st in STEPS if st["name"].startswith(tail_names)]
    pipeline = head + tail
    if not head:
        print(f"RETRY-SOFT-SKIP: soft-failed steps not in STEPS: {sorted(names)}")
        return 0
    print(f"RETRY-SOFT: rerunning {len(head)} soft-failed step(s) "
          f"{sorted(names)} + {len(tail)} export/gate/commit tail", flush=True)
    day_dir = LOG_DIR / now.strftime("%Y-%m-%d")
    day_dir.mkdir(parents=True, exist_ok=True)
    with (day_dir / "run.log").open("a", encoding="utf-8") as fh:
        log(f"=== retry-soft pass {datetime.now().isoformat()} ===", fh)
        soft_fails: list[str] = []
        for step in pipeline:
            if step["name"].startswith("json validity"):
                problems = strict_json_scan()
                if problems:
                    raise RuntimeError(f"strict-JSON gate: {problems[:3]}")
            ok, detail = run_step(step, fh)
            if not ok:
                if step["soft"]:
                    soft_fails.append(step["name"])
                else:
                    raise RuntimeError(
                        f"hard-fail step '{step['name']}': {detail}")
        ledger_note = tidy_ledger(fh)
        status, sha, pushed, n_files = commit_and_push(fh)
        try:
            r = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "backup_audit_chain.py")],
                cwd=ROOT, capture_output=True, text=True, timeout=120)
            backup_note = "ok" if r.returncode == 0 else f"warn:{r.stderr.strip()[-60:]}"
        except Exception as exc:  # noqa: BLE001 — non-fatal by design
            backup_note = f"warn:{str(exc)[:60]}"
        ci = (verify_own_commit_ci(sha) if pushed else {"note": "no push"})
        state.update({"retry_soft": {"at": now.isoformat(), "steps": sorted(names),
                                     "residual_soft_fails": soft_fails,
                                     "commit": sha, "pushed": pushed,
                                     "n_files": n_files, "backup": backup_note}})
        save_state(state)
        summary = {"retry_soft": True, "steps": sorted(names),
                   "status": status, "commit": sha, "pushed": pushed,
                   "n_files": n_files, "soft_fails": soft_fails,
                   "ledger": ledger_note, "ci": ci, "backup": backup_note}
        log(f"SUMMARY {json.dumps(summary, ensure_ascii=False)}", fh)
        print(f"SUMMARY {json.dumps(summary, ensure_ascii=False)}")
        return 0


def begin_attempt(state: dict, today: str, attempts: int, force: bool) -> None:
    """Attempt-start marker update (round 126): a `note` belongs to the
    attempt that wrote it — the round-99-era note ('lane redundant … killed
    by round-99') survived into 2026-11 markers because nothing ever cleared
    it. Clearing here means any new attempt supersedes old explanations."""
    state.update({"date": today, "attempts": attempts, "status": "running",
                  "started_at_epoch": time.time(), "force": force})
    state.pop("note", None)


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
    prev_status, prev_error = state.get("status"), str(state.get("error", ""))
    attempts = state.get("attempts", 0) + 1 if state.get("date") == today else 1
    day_dir = LOG_DIR / today
    day_dir.mkdir(parents=True, exist_ok=True)
    with (day_dir / "run.log").open("a", encoding="utf-8") as fh:
        begin_attempt(state, today, attempts, force)
        save_state(state)
        log(f"=== evening lane start {datetime.now().isoformat()} "
            f"(attempt {attempts}/{MAX_ATTEMPTS_PER_EVENING}) ===", fh)
        t0 = time.time()
        soft_fails: list[str] = []
        try:
            recovered = try_push_only_recovery(prev_status, prev_error, fh)
            if recovered == "ok_committed":
                sha = git(["rev-parse", "HEAD"]).stdout.strip()
                state.update({"status": "ok_committed", "commit": sha,
                              "pushed": True, "n_files": None,
                              "push_only_recovery": True,
                              "soft_fails": [],
                              "finished_at": datetime.now().isoformat()})
                save_state(state)
                summary = {"date": today, "status": "ok_committed",
                           "commit": sha, "pushed": True,
                           "push_only_recovery": True, "soft_fails": [],
                           "wall_minutes": round((time.time() - t0) / 60, 1)}
                log(f"SUMMARY {json.dumps(summary, ensure_ascii=False)}", fh)
                print(f"SUMMARY {json.dumps(summary, ensure_ascii=False)}")
                return 0
            for step in STEPS:
                if step["name"].startswith("json validity"):
                    problems = strict_json_scan()
                    if problems:
                        raise RuntimeError(
                            f"strict-JSON gate: {problems[:3]}")
                ok, detail = run_step(step, fh)
                if not ok:
                    if step["soft"]:
                        soft_fails.append(step["name"])
                    else:
                        raise RuntimeError(
                            f"hard-fail step '{step['name']}': {detail}")
            ledger_note = tidy_ledger(fh)
            # Persistent soft-fail alarm (round 208, reflection-3 §一.1): the
            # recovery lane fires on HARD failures only, so a step that soft-
            # fails night after night (e.g. a source rate-limiting us into
            # permanent staleness) would otherwise stay silent forever. Scan
            # the recent run logs: a step soft-failing >= 3 of the last <= 5
            # logged evenings is PERSISTENT and gets flagged in the SUMMARY —
            # freshness debt made visible instead of discovered by accident.
            persistent: list[str] = []
            try:
                log_dirs = sorted(
                    (p for p in (ROOT / "runs/ops_local_refresh").iterdir()
                     if p.is_dir()),
                )[-5:]
                counts: dict[str, int] = {}
                for d in log_dirs:
                    lg = d / "run.log"
                    if not lg.exists():
                        continue
                    txt = lg.read_text(encoding="utf-8", errors="ignore")
                    m = re.search(r"SUMMARY (\{.*\})$", txt, re.M)
                    if not m:
                        continue
                    try:
                        prev = json.loads(m.group(1))
                    except json.JSONDecodeError:
                        continue
                    for name in prev.get("soft_fails") or []:
                        counts[name] = counts.get(name, 0) + 1
                persistent = sorted(n2 for n2, c in counts.items() if c >= 3)
            except Exception:  # noqa: BLE001 — alarm must never break the lane
                persistent = []
            if persistent:
                log(f"PERSISTENT-SOFT-FAILS (>=3 of last ~5 evenings): "
                    f"{persistent}", fh)
            status, sha, pushed, n_files = commit_and_push(fh)
            # Audit-chain backup (round 172): after any lane push, snapshot
            # the ledger + full bundle to data/backups/. Non-fatal: a backup
            # failure must never mark the lane run as failed.
            try:
                r = subprocess.run(
                    [sys.executable, str(ROOT / "scripts" / "backup_audit_chain.py")],
                    cwd=ROOT, capture_output=True, text=True, timeout=120)
                backup_note = ("ok" if r.returncode == 0
                               else f"warn:{r.stderr.strip()[-60:]}")
            except Exception as exc:  # noqa: BLE001 — non-fatal by design
                backup_note = f"warn:{str(exc)[:60]}"
            log(f"audit-chain backup: {backup_note}", fh)
            ci = (verify_own_commit_ci(sha) if pushed
                  else {"note": "no push"})
            ci_triage = triage_ci(ci, sha) if pushed else {}
            state.pop("error", None)  # stale failure text must not survive a success
            state.update({"status": status, "commit": sha, "pushed": pushed,
                          "n_files": n_files, "soft_fails": soft_fails,
                          "ci": ci, "ci_triage": ci_triage,
                          "backup": backup_note,
                          "persistent_soft_fails": persistent,
                          "finished_at": datetime.now().isoformat()})
            save_state(state)
            summary = {
                "date": today, "status": status, "commit": sha, "pushed": pushed,
                "n_files": n_files, "soft_fails": soft_fails,
                "ledger": ledger_note, "ci": ci, "ci_triage": ci_triage,
                "backup": backup_note,
                "persistent_soft_fails": persistent,
                "wall_minutes": round((time.time() - t0) / 60, 1),
            }
            log(f"SUMMARY {json.dumps(summary, ensure_ascii=False)}", fh)
            print(f"SUMMARY {json.dumps(summary, ensure_ascii=False)}")
            write_night_package(datetime.now())
            return 0
        except Exception as exc:  # noqa: BLE001 — unattended lane: always mark + report
            state.update({"status": "failed", "error": str(exc)[:800],
                          "finished_at": datetime.now().isoformat()})
            save_state(state)
            log(f"HARD-FAIL: {exc}", fh)
            print(f"FAILED: {exc}")
            write_night_package(datetime.now())
            return 1


def _emit_json(payload: object) -> None:
    """Machine-readable stdout contract (--status --json / --doctor --json):
    exactly one JSON document on stdout, UTF-8 bytes, ensure_ascii=False.
    The bytes go to sys.stdout.buffer directly — a GBK Windows text layer
    would mojibake/raise on non-ASCII marker content (the 2026-09-10/11
    outage class); captured stdout without .buffer (pytest capsys) falls
    back to print()."""
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    buf = getattr(sys.stdout, "buffer", None)
    if buf is not None:
        buf.write(text.encode("utf-8") + b"\n")
        buf.flush()
    else:
        print(text)


# L7 — site-repo drift (the billing-freeze blind spot, added 2026-11-06).
# When GitHub is billing-locked EVERY Actions run dies in ~4s (lock #2,
# 2026-11-05: Tests + Publish site both red in 3-4s) — including the weekly
# staleness tripwire itself, which is an Actions workflow. Nothing cloud-side
# can observe the freeze: the live Pages site keeps serving its last deploy
# while origin/main advances every evening (git push needs no Actions
# minutes). The only surviving signal is a LOCAL probe of the deployed site.
SITE_DATA_HEALTH_URL = ("https://rethymus.github.io/Aionis/"
                        "api/v1/panels/data_health.json")
SITE_DRIFT_LAG_HOURS = 48  # live lags repo beyond this => deploy frozen


def _fetch_live_snapshot() -> str:
    """Fetch the LIVE site's data_health payload via curl (subprocess, 15s
    cap). Injectable seam: tests monkeypatch this instead of shelling out."""
    out = subprocess.run(
        ["curl", "-fsS", "--max-time", "15", SITE_DATA_HEALTH_URL],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=20)
    if out.returncode != 0:
        raise RuntimeError(f"curl exit {out.returncode}: "
                           f"{(out.stderr or '').strip()[-120:]}")
    return out.stdout


def _parse_snapshot_ts(payload: str) -> datetime | None:
    """snapshot_ts from a data_health JSON payload; None when the payload is
    unparseable or lacks the field (an honest FAIL downstream, never a
    crash). Naive stamps are read as UTC (the lane's export convention)."""
    try:
        data = json.loads(payload)
    except ValueError:
        return None
    raw = data.get("snapshot_ts") if isinstance(data, dict) else None
    if not raw:
        return None
    try:
        ts = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


def _site_repo_drift_check() -> tuple[bool, str]:
    """Layer 7 logic: the LIVE deployed site's snapshot_ts must not lag the
    repo's committed one beyond SITE_DRIFT_LAG_HOURS. Every failure mode
    (network unreachable, invalid payload, missing repo file) returns a FAIL
    tuple carrying the reason — an honest red beats a crashed doctor, so all
    exceptions are caught by design."""
    try:
        repo_ts = _parse_snapshot_ts(
            (ROOT / "web/src/data/aionis" / "data_health.json")
            .read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        return False, f"repo data_health unreadable: {exc}"
    if repo_ts is None:
        return False, "repo data_health has no parseable snapshot_ts"
    try:
        live_ts = _parse_snapshot_ts(_fetch_live_snapshot())
    except Exception as exc:  # noqa: BLE001 — unreachable network is a FAIL
        return False, ("live site unreachable or invalid — deploy may be "
                       f"frozen (billing?): {exc}")
    if live_ts is None:
        return False, ("live site unreachable or invalid — deploy may be "
                       "frozen (billing?): no parseable snapshot_ts")
    lag_h = (repo_ts - live_ts).total_seconds() / 3600
    if lag_h > SITE_DRIFT_LAG_HOURS:
        return False, (f"live site lags repo by {lag_h / 24:.1f} days — "
                       f"deploy frozen? (live={live_ts.isoformat()} "
                       f"repo={repo_ts.isoformat()})")
    if lag_h < -0.01:
        return True, f"live is {-lag_h:.1f}h newer than repo"
    if lag_h < 0.01:
        return True, f"live matches repo (snapshot_ts={live_ts.isoformat()})"
    return True, (f"live lags repo by {lag_h:.1f}h "
                  f"(within {SITE_DRIFT_LAG_HOURS}h tolerance)")


# ------------------------------------------------ layer 8: marker deadman
# Round 126 (super-agent落点三收尾): the owner's "定时任务失效" worry is at
# bottom "the lane silently died". Layers 1-7 check the stack's PARTS; layer 8
# checks the OUTCOME — the ok_committed marker must keep arriving per working
# evening. Period+Grace semantics borrowed from healthchecks/healthchecks
# (BSD-3-Clause, docs/data-license-allowlist.md:20; ping protocol semantics
# only — no self-hosted Django, no background process, no pings leaving the
# machine). Local layer: verifiable immediately, immune to the billing lock.
DEADMAN_GRACE_WORKING_DAYS = 1
_DEADMAN_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _next_working_day(d: date) -> date:
    """Next Mon-Fri day after `d`. US holidays deliberately NOT excluded:
    the lane's holiday skip is conditional (guard skips only with zero
    pending catch-up), and a single-day holiday absence is absorbed by the
    Grace day — paging on a holiday cluster is the honest false-positive
    trade for a deadman."""
    d += timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def _working_days_between(start: date, end: date) -> int:
    """Mon-Fri count in [start, end) — start counts, end doesn't."""
    days = (end - start).days
    if days <= 0:
        return 0
    weeks, rem = divmod(days, 7)
    return weeks * 5 + sum(
        1 for i in range(rem) if (start.weekday() + i) % 7 < 5)


def _last_ok_committed_date(log_dir: Path, state: dict) -> str | None:
    """Newest ok_committed evening date from the run logs (a later failed
    evening must not hide the last success), falling back to the marker
    when it is itself ok_committed."""
    if log_dir.is_dir():
        for day_dir in sorted((p for p in log_dir.iterdir() if p.is_dir()),
                              reverse=True):
            log_file = day_dir / "run.log"
            if not log_file.is_file():
                continue
            try:
                text = log_file.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for line in reversed(text.splitlines()):
                if "SUMMARY" not in line:
                    continue
                try:
                    payload = json.loads(line.split("SUMMARY", 1)[1])
                except ValueError:
                    continue
                if (isinstance(payload, dict)
                        and payload.get("status") == "ok_committed"
                        and isinstance(payload.get("date"), str)
                        and _DEADMAN_DATE_RE.match(payload["date"])):
                    return payload["date"]
    if (state.get("status") == "ok_committed"
            and isinstance(state.get("date"), str)
            and _DEADMAN_DATE_RE.match(state["date"])):
        return state["date"]
    return None


def marker_deadman(now: datetime, state: dict,
                   log_dir: Path | None = None) -> tuple[bool, str]:
    """Layer 8 (round 126): deadman switch over the ok_committed marker.

    healthchecks.io Period+Grace semantics (BSD-3-Clause; protocol borrow
    only): Period = one working-day evening (the lane's Mon-Fri schedule),
    Grace = DEADMAN_GRACE_WORKING_DAYS working day(s). Weekend
    SKIP:weekend is design behavior and does not tick the clock; a
    conditional holiday skip is absorbed by Grace. A currently-RUNNING lane
    pacifies the deadman (alive right now)."""
    if state.get("status") == "running":
        return True, ("lane running now (alive) — deadman pacified "
                      f"(started_at_epoch={state.get('started_at_epoch')})")
    last_ok = _last_ok_committed_date(
        log_dir if log_dir is not None else LOG_DIR, state)
    if last_ok is None:
        return False, ("no ok_committed evening found (marker + run logs) "
                       "— lane never succeeded or state lost")
    try:
        last = datetime.strptime(last_ok, "%Y-%m-%d").date()
    except ValueError:
        return False, f"marker date unparseable: {last_ok!r}"
    today = now.date()
    if last > today:
        return True, (f"last ok_committed {last_ok} is in the future "
                      "(host clock skew) — treated as fresh")
    due = _next_working_day(last)
    grace = _next_working_day(due)
    if today > grace:
        missed = _working_days_between(due, today)
        return False, (f"last ok_committed {last_ok} — due {due}, grace "
                       f"until {grace}; missed {missed} working evening(s) "
                       "(deadman: Period+Grace exceeded — lane silently "
                       "dead?)")
    return True, (f"last ok_committed {last_ok}; due {due}; grace until "
                  f"{grace} (within Period+Grace)")


def collect_layers() -> list[tuple[str, bool, str]]:
    """The eight read-only preflight checks (round 109; layer 7 site-repo
    drift added 2026-11-06; layer 8 marker deadman added 2026-11-11) as
    data — one (name, ok, detail) tuple per layer, in order. Pure
    collection, no printing: doctor() renders the human PASS/FAIL text from
    these tuples and --doctor --json renders the machine document from the
    same source, so the two surfaces can never disagree."""
    checks: list[tuple[str, bool, str]] = []

    # L1 marker + guard sanity (pure logic, no side effects)
    state = load_state()
    decision = guard_decision(datetime.now(), state)
    checks.append((
        "1/8 guard+marker", state.get("date") is not None,
        f"marker date={state.get('date')} status={state.get('status')} "
        f"guard-now={decision.split(':')[0]}"))

    # L2 Windows Task Scheduler (the zero-token heartbeat)
    if IS_WINDOWS:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-ScheduledTask -TaskName 'Aionis evening data lane' "
             "-ErrorAction SilentlyContinue) -ne $null"],
            capture_output=True, text=True, timeout=30)
        ok2 = out.returncode == 0 and "True" in out.stdout
        checks.append(("2/8 task scheduler", ok2,
                       "registered" if ok2 else "NOT registered"))
    else:
        checks.append(
            ("2/8 task scheduler", False, "non-Windows host (manual cron?)"))

    # L3 SessionStart hook config (committed file, correct event+matcher)
    try:
        hook_cfg = ROOT / ".zcode" / "config.json"
        cfg = json.loads(hook_cfg.read_text(encoding="utf-8"))
        ev = cfg.get("hooks", {}).get("events", {}).get("SessionStart", [])
        ok3 = (cfg.get("hooks", {}).get("enabled") is True and bool(ev)
               and "startup" in ev[0].get("matcher", ""))
        checks.append((
            "3/8 sessionstart hook", ok3,
            f"enabled={cfg.get('hooks', {}).get('enabled')} "
            f"matcher={ev[0].get('matcher') if ev else 'none'}"))
    except (OSError, ValueError, IndexError) as exc:
        checks.append(("3/8 sessionstart hook", False, f"{exc}"))

    # L4 git push credential (read-only ls-remote with the stored cred)
    out = subprocess.run(["git", "ls-remote", "--heads", "origin", "main"],
                         cwd=ROOT, capture_output=True, text=True, timeout=30)
    ok4 = out.returncode == 0
    checks.append((
        "4/8 push credential",
        ok4 and out.stdout.startswith(tuple("0123456789abcdef")),
        "ls-remote ok" if ok4 else out.stderr.strip()[-80:]))

    # L5 gh CLI auth + repo visibility
    out = subprocess.run(["gh", "run", "list", "--limit", "1"],
                         cwd=ROOT, capture_output=True, text=True, timeout=30)
    ok5 = out.returncode == 0
    checks.append(("5/8 gh auth", ok5,
                   "gh ok" if ok5 else out.stderr.strip()[-80:]))

    # L6 runtime env: .env keys present (names only, never values)
    env_path = ROOT / ".env"
    names: set[str] = set()
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                names.add(line.split("=", 1)[0].strip())
    except OSError:
        pass
    need = {"TIINGO_API_KEY", "FRED_API_KEY"}
    checks.append(("6/8 api env", need <= names,
                   f"present={sorted(need & names)} "
                   f"missing={sorted(need - names)}"))

    # L7 site-repo drift (the billing-freeze blind spot): the only layer that
    # reaches OUT to the deployed site — see _site_repo_drift_check.
    ok7, detail7 = _site_repo_drift_check()
    checks.append(("7/8 site-repo drift", ok7, detail7))

    # L8 marker deadman (round 126): the OUTCOME check — the ok_committed
    # marker must keep arriving per working evening (healthchecks Period+
    # Grace semantics; weekend SKIP:weekend doesn't tick). Catches "the lane
    # silently died" regardless of which part broke. See marker_deadman.
    ok8, detail8 = marker_deadman(datetime.now(), state)
    checks.append(("8/8 evening marker deadman", ok8, detail8))
    return checks


def doctor(as_json: bool = False) -> int:
    """Read-only eight-layer preflight (round 109; layer 7 site-repo drift
    added 2026-11-06, layer 8 marker deadman added 2026-11-11): one command
    the owner (or any future session) runs to
    verify the whole lane stack after machine changes, credential renewals,
    or before a renewal decision. Human mode prints PASS/FAIL per layer;
    --json emits exactly one machine document ({"layers":
    [{name, ok, detail}...], "passed": N, "total": 8}) instead. Exit 0 only
    if every layer passes (both modes)."""
    checks = collect_layers()
    failed = [n for n, ok, _ in checks if not ok]
    if as_json:
        _emit_json({
            "layers": [{"name": name, "ok": ok, "detail": detail}
                       for name, ok, detail in checks],
            "passed": len(checks) - len(failed),
            "total": len(checks),
        })
    else:
        for name, ok, detail in checks:
            print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
        print(f"doctor: {len(checks) - len(failed)}/{len(checks)} layers pass"
              + (f" — FAILED: {failed}" if failed else ""))
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--retry-soft", action="store_true",
                        help="selective soft-fail retry: rerun only today's "
                             "soft-failed steps + export/gate/commit tail "
                             "(owner-authorized round 246)")
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument("--guard", action="store_true",
                       help="print RUN or SKIP:<reason>")
    group.add_argument("--run", action="store_true", help="run the evening lane")
    group.add_argument("--status", action="store_true", help="print marker state")
    group.add_argument("--doctor", action="store_true",
                       help="read-only eight-layer lane preflight")
    group.add_argument("--triage", action="store_true",
                       help="read-only Fast-Path failure triage: three-bucket "
                            "classification + night-report context package "
                            "(gh probes red CI runs; refreshes night_package.json)")
    parser.add_argument("--json", action="store_true",
                        help="with --status/--doctor/--triage: emit "
                             "machine-readable JSON (UTF-8, ensure_ascii=False) "
                             "to stdout")
    parser.add_argument("--force", action="store_true",
                        help="with --run: bypass the guard (human use only)")
    args = parser.parse_args()
    if args.retry_soft:
        return do_retry_soft()
    if not (args.guard or args.run or args.status or args.doctor
            or args.triage):
        parser.error("one of the arguments --guard --run --status --doctor "
                     "--triage is required (or --retry-soft)")
    if args.json and not (args.status or args.doctor or args.triage):
        parser.error("--json is only meaningful with --status, --doctor "
                     "or --triage")
    if args.guard:
        print(guard_decision(datetime.now(), load_state()))
        return 0
    if args.doctor:
        return doctor(as_json=args.json)
    if args.triage:
        state = load_state()
        ci = state.get("ci")
        if isinstance(ci, dict) and any(v == "failure" for v in ci.values()):
            # fresh read-only gh enrichment; unmeasurable reds stay code-defect
            state["ci_triage"] = triage_ci(ci, state.get("commit"))
        package = build_night_package(state, datetime.now())
        if args.json:
            _emit_json(package)
        else:
            print(json.dumps(package, ensure_ascii=False, indent=2))
        write_night_package(datetime.now(), state)
        return 0
    if args.status:
        if args.json:
            _emit_json(load_state())
        else:
            print(json.dumps(load_state(), ensure_ascii=False, indent=2))
        return 0
    return do_run(args.force)


if __name__ == "__main__":
    raise SystemExit(main())
