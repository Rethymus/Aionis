"""Monthly review collector for the evening data lane — deterministic metrics.

The 6th-of-month review (sample: reports/audits/2026-10-06-evening-lane-monthly-
review.md) was hand-assembled by an LLM session reading
`runs/ops_local_refresh/<date>/run.log` by eye. This script turns the
METRIC-GATHERING step into deterministic, re-runnable code; the verdict/decision
prose stays a human (owner) call, per the review's own framing. Reporting-only
lane: reads run logs + committed JSON, emits markdown — no research surface, no
ledger row, no frozen config (same display-only contract as ops_local_refresh).

Collects, for one calendar month:
  1. per-evening execution from run.log SUMMARY lines — each written through
     `log()` and therefore carrying a `[HH:MM:SS]` timestamp prefix before the
     JSON: status, wall_minutes, soft_fails (count + names), n_files, the ci
     conclusion pair, and how many push_only_recovery events fired. A SUMMARY's
     day is its own `date` field when present (a cross-midnight run finishes
     under the next day's date inside the previous day's directory), else the
     directory name; evenings without a SUMMARY are reported as absent, never
     fabricated. A `retry_soft` pass never clobbers the evening's primary
     SUMMARY (which carries wall_minutes) — it is noted as a residual field.
  2. the GitHub Actions publish chain via `gh run list --workflow=<wf> --limit
     60` for publish-site.yml and ci.yml (success/failure counts, month-scoped
     when createdAt allows). gh being unavailable is printed as 未能核对 and is
     NOT counted as a failure (offline tolerance — the 10-06 review's --limit-60
     sampling correction is why the window is labeled explicitly).
  3. the dashboard snapshot row from web/src/data/aionis/data_health.json
     (snapshot_ts + summary), when the file exists. The file is gate-tested by
     the lane's strict-JSON scan, so one that exists but cannot be parsed is an
     internal anomaly (exit 1), not a silent skip.

Usage:
  uv run python scripts/monthly_review.py                        # last month -> stdout
  uv run python scripts/monthly_review.py --month 2026-10        # explicit month
  uv run python scripts/monthly_review.py --month 2026-09 \\
      --out reports/audits/2026-10-06-monthly-lane-data.md       # write to file
  uv run python scripts/monthly_review.py --weekly    # Watchdog (+anchor)
  uv run python scripts/monthly_review.py --propose   # proposal cards (0 LLM)

Exit codes: 0 = at least one SUMMARY collected for the month and no internal
anomaly; 1 = zero SUMMARYs, or an internal anomaly (unreadable run.log, corrupt
SUMMARY line, unreadable existing data_health.json). gh unavailability is NOT
an exit-1 condition.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from calendar import monthrange
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_SUBDIR = Path("runs") / "ops_local_refresh"
HEALTH_JSON = Path("web") / "src" / "data" / "aionis" / "data_health.json"
GH_WORKFLOWS = ("publish-site.yml", "ci.yml")
GH_LIMIT = 60
GH_TIMEOUT_S = 30
# Printed verbatim when gh cannot be reached — reported honestly, never scored
# as a run failure (the review must stay runnable offline).
UNVERIFIED = "未能核对"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MONTH_RE = re.compile(r"^\d{4}-\d{2}$")
# Every run.log line is written through log(): "[HH:MM:SS] SUMMARY {...}".
# Anchoring on the bracketed-timestamp prefix keeps step-output tails that
# merely contain the word SUMMARY from being parsed as lane summaries.
SUMMARY_RE = re.compile(r"^\[[^\]]+\]\s+SUMMARY\s+(\{.+\})\s*$")
# The marker alone (no well-formed JSON tail) = a SUMMARY line that was
# truncated mid-write — an internal anomaly, not a silent skip.
SUMMARY_MARKER_RE = re.compile(r"^\[[^\]]+\]\s+SUMMARY\s")

CI_PUBLISH_KEY = "Publish site (gh-pages)"
CI_TESTS_KEY = "Tests"


# ------------------------------------------------------------------ collection

def default_month(today: date | None = None) -> str:
    """The month before `today`'s — the review runs on the 6th of the new
    month and looks back."""
    t = today or date.today()
    first_of_this_month = t.replace(day=1)
    prev_month_end = first_of_this_month - timedelta(days=1)
    return prev_month_end.strftime("%Y-%m")


def summary_payload(line: str) -> str | None:
    """The JSON text of a SUMMARY line, or None when the line is not one."""
    m = SUMMARY_RE.match(line)
    return m.group(1) if m else None


def _blank_day(day: str) -> dict:
    return {"date": day, "status": None, "wall_minutes": None, "n_files": None,
            "soft_fails": [], "ci": None, "persistent_soft_fails": [],
            "push_only_recovery": False, "retry_soft_residual": None}


def collect_log_days(repo: Path, month: str,
                     errors: list[str]) -> tuple[list[dict], int]:
    """Aggregate the month's run.log SUMMARY lines into one record per evening.

    Returns (per-day records sorted by date, push_only_recovery event count).
    Parse/unreadable problems land in `errors` (internal anomalies — the
    caller turns them into exit 1); they never abort the walk.
    """
    prefix = month + "-"
    per_day: dict[str, dict] = {}
    push_only = 0
    log_root = repo / LOG_SUBDIR
    if not log_root.is_dir():
        return [], 0
    for day_dir in sorted(p for p in log_root.iterdir() if p.is_dir()):
        log_file = day_dir / "run.log"
        if not log_file.is_file():
            continue
        try:
            text = log_file.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            errors.append(f"{log_file}: unreadable ({exc})")
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            payload = summary_payload(line)
            if payload is None:
                if SUMMARY_MARKER_RE.match(line):
                    errors.append(f"{log_file}:{lineno}: truncated SUMMARY "
                                  f"line: {line[:100]}")
                continue
            try:
                parsed = json.loads(payload)
            except ValueError:
                errors.append(f"{log_file}:{lineno}: corrupt SUMMARY JSON: "
                              f"{payload[:100]}")
                continue
            if not isinstance(parsed, dict):
                errors.append(f"{log_file}:{lineno}: SUMMARY is not an object")
                continue
            day = parsed.get("date")
            if not (isinstance(day, str) and DATE_RE.match(day)):
                day = day_dir.name  # fallback: retry_soft summaries carry no date
            if not day.startswith(prefix):
                continue  # cross-midnight SUMMARY dated outside the month
            rec = per_day.setdefault(day, _blank_day(day))
            if parsed.get("retry_soft"):
                if rec["status"] is not None:
                    # second pass on a finished evening — note, don't clobber
                    rec["retry_soft_residual"] = list(parsed.get("soft_fails") or [])
                else:
                    rec["status"] = parsed.get("status")
                    rec["n_files"] = parsed.get("n_files")
                    rec["soft_fails"] = list(parsed.get("soft_fails") or [])
                    rec["ci"] = parsed.get("ci")
                continue
            # Later full-run summaries win (the most recent completed attempt).
            rec["status"] = parsed.get("status")
            rec["wall_minutes"] = parsed.get("wall_minutes")
            rec["n_files"] = parsed.get("n_files")
            rec["soft_fails"] = list(parsed.get("soft_fails") or [])
            rec["ci"] = parsed.get("ci")
            rec["persistent_soft_fails"] = list(
                parsed.get("persistent_soft_fails") or [])
            if parsed.get("push_only_recovery"):
                rec["push_only_recovery"] = True
                push_only += 1
    return [per_day[d] for d in sorted(per_day)], push_only


def gh_run_list(workflow: str, repo: Path) -> tuple[int, str, str]:
    """One gh invocation, isolated here so tests can inject a fake."""
    proc = subprocess.run(
        ["gh", "run", "list", "--workflow", workflow, "--limit", str(GH_LIMIT),
         "--json", "conclusion,createdAt"],
        cwd=str(repo), capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=GH_TIMEOUT_S)
    return proc.returncode, proc.stdout, proc.stderr


def collect_gh(workflow: str, month: str, repo: Path,
               runner: None = None) -> dict:
    """Success/failure counts for one workflow. Never raises: any gh problem
    (missing CLI, auth, timeout, bad JSON) becomes ok=False + an error string,
    rendered as 未能核对 and NOT scored as a failure. `runner` is injectable
    (tests); None means the real gh CLI."""
    if runner is None:
        runner = gh_run_list
    try:
        rc, out, err = runner(workflow, repo)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if rc != 0:
        return {"ok": False, "error": (err or out).strip()[-200:]}
    try:
        rows = json.loads(out)
        if not isinstance(rows, list):
            raise ValueError("not a JSON list")
    except ValueError as exc:
        return {"ok": False, "error": f"unparseable gh JSON: {exc}"}
    counts = {"ok": True, "success": 0, "failure": 0, "other": 0,
              "month_success": 0, "month_failure": 0, "rows": len(rows)}
    for row in rows:
        conclusion = row.get("conclusion") if isinstance(row, dict) else None
        created = str(row.get("createdAt", "")) if isinstance(row, dict) else ""
        in_month = created.startswith(month)
        if conclusion == "success":
            counts["success"] += 1
            if in_month:
                counts["month_success"] += 1
        elif conclusion == "failure":
            counts["failure"] += 1
            if in_month:
                counts["month_failure"] += 1
        else:
            counts["other"] += 1
    return counts


def collect_health(repo: Path, errors: list[str]) -> dict | None:
    """The dashboard snapshot row (snapshot_ts + summary) when present."""
    path = repo / HEALTH_JSON
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        errors.append(f"{path}: exists but unreadable ({exc})")
        return None
    return {"snapshot_ts": data.get("snapshot_ts"), "summary": data.get("summary")}


# --------------------------------------------------------------------- render

def _cell(value) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _fmt_ci(ci) -> str:
    if not isinstance(ci, dict) or not ci:
        return "—"
    pub, tst = ci.get(CI_PUBLISH_KEY), ci.get(CI_TESTS_KEY)
    if pub is not None or tst is not None:
        return f"{pub or '?'}/{tst or '?'}"
    return "; ".join(f"{k}={v}" for k, v in ci.items())


def _fmt_wall(w) -> str:
    return "—" if w is None else f"{w:.1f}"


def _fmt_soft(soft: list) -> str:
    if not soft:
        return "0"
    return f"{len(soft)}: {', '.join(soft)}"


def missing_weekdays(month: str, collected: set[str]) -> list[str]:
    """Weekday (Mon–Fri) dates of the month with no SUMMARY — factual absence,
    enumerated so the execution-rate table never has to invent a row."""
    y, m = int(month[:4]), int(month[5:7])
    out: list[str] = []
    d = date(y, m, 1)
    while d.month == m:
        if d.weekday() < 5 and d.isoformat() not in collected:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def render(month: str, days: list[dict], push_only: int, gh: dict,
           health: dict | None, errors: list[str],
           generated_at: str) -> str:
    out: list[str] = []
    out.append(f"# Monthly review data collection — evening lane ({month})")
    out.append("")
    out.append(f"> Generated {generated_at} by `scripts/monthly_review.py` — "
               "deterministic collection, replaces the hand-reading LLM step.")
    out.append("> The verdict/decision prose remains the owner's call. gh rows "
               f"are a sampled window (last {GH_LIMIT} runs per workflow), not "
               "the full month — the 2026-10-09")
    out.append("> correction in the 10-06 review is why the window is labeled "
               "on every number.")
    out.append("")

    # 1. execution rate
    out.append("## 1. Execution rate (one row per evening WITH a SUMMARY; "
               "absent evenings are not fabricated)")
    out.append("")
    out.append("| Date | status | wall (min) | soft_fails | n_files | "
               "push_only_recovery | CI (publish/tests) |")
    out.append("|---|---|---|---|---|---|---|")
    for d in days:
        out.append("| {date} | {status} | {wall} | {soft} | {n} | {por} | {ci} |"
                   .format(date=_cell(d["date"]),
                           status=_cell(d["status"] if d["status"] else "—"),
                           wall=_fmt_wall(d["wall_minutes"]),
                           soft=_cell(_fmt_soft(d["soft_fails"])),
                           n="—" if d["n_files"] is None else str(d["n_files"]),
                           por="yes" if d["push_only_recovery"] else "—",
                           ci=_cell(_fmt_ci(d["ci"]))))
    if not days:
        out.append(f"(no SUMMARY rows collected for {month})")
    out.append("")
    missing = missing_weekdays(month, {d["date"] for d in days})
    out.append(f"Evenings with a SUMMARY: **{len(days)}**. Calendar days in "
               f"{month}: {monthrange_len(month)}; weekday evenings without a "
               f"SUMMARY: {len(missing)}"
               + (f" ({', '.join(missing)})" if missing else "")
               + " — weekends/holidays naturally have none; each listed "
                 "weekday-miss still needs a human reason.")
    out.append("")

    # 2. publish chain
    out.append(f"## 2. Publish chain (`gh run list --limit {GH_LIMIT}`)")
    out.append("")
    out.append("| Workflow | success (month) | failure (month) | "
               f"success (window≤{GH_LIMIT}) | failure (window≤{GH_LIMIT}) |")
    out.append("|---|---|---|---|---|")
    for wf in GH_WORKFLOWS:
        c = gh.get(wf)
        if not c or not c.get("ok"):
            reason = c.get("error", "unknown") if c else "not collected"
            out.append(f"| {_cell(wf)} | {UNVERIFIED} ({_cell(reason)}) "
                       "| | | |")
        else:
            out.append(f"| {_cell(wf)} | {c['month_success']} "
                       f"| {c['month_failure']} | {c['success']} "
                       f"| {c['failure']} |")
    for wf in GH_WORKFLOWS:
        c = gh.get(wf) or {}
        if c.get("ok") and c.get("rows") and not (c["month_success"]
                                                 or c["month_failure"]):
            out.append(f"- note: the {wf} window contains no runs from {month} "
                       "— they have aged past the sampling limit; query gh "
                       "directly for the month (the 10-06 review's "
                       "2026-10-09 correction).")
    out.append("")

    # 3. dashboard snapshot
    out.append("## 3. Dashboard snapshot (web/src/data/aionis/data_health.json)")
    out.append("")
    if health is None:
        out.append("- not present this month (nothing fabricated in its place)")
    else:
        out.append(f"- snapshot_ts: {health.get('snapshot_ts') or '—'}")
        summary = health.get("summary")
        if isinstance(summary, dict):
            out.append("- summary: " + ", ".join(
                f"{k}={v}" for k, v in sorted(summary.items())))
        else:
            out.append("- summary: —")
    out.append("")

    # 4. soft-fail trend
    out.append("## 4. Soft-fail trend")
    out.append("")
    with_soft = [d for d in days if d["soft_fails"]]
    out.append(f"- Evenings with ≥1 soft fail: {len(with_soft)}/{len(days)}.")
    name_counts: dict[str, int] = {}
    for d in days:
        for name in d["soft_fails"]:
            name_counts[name] = name_counts.get(name, 0) + 1
    for name, count in sorted(name_counts.items(), key=lambda kv: (-kv[1], kv[0])):
        out.append(f"  - {name}: {count} evening(s)")
    out.append(f"- push_only_recovery fired {push_only} time(s) this month.")
    persistent = [(d["date"], d["persistent_soft_fails"]) for d in days
                  if d["persistent_soft_fails"]]
    if persistent:
        out.append("- persistent_soft_fails flagged in SUMMARY on: "
                   + "; ".join(f"{dt} {names}" for dt, names in persistent))
    retries = [(d["date"], d["retry_soft_residual"]) for d in days
               if d["retry_soft_residual"] is not None]
    if retries:
        out.append("- retry_soft passes on: " + "; ".join(
            f"{dt} (residual: {', '.join(res) or 'none'})" for dt, res in retries))
    timed = [d["wall_minutes"] for d in days if d["wall_minutes"] is not None]
    if timed:
        out.append(f"- wall_minutes: avg {sum(timed) / len(timed):.1f}, "
                   f"max {max(timed):.1f} over {len(timed)} timed evening(s).")
    out.append("")

    if errors:
        out.append("## Internal anomalies (these make the exit code 1)")
        out.append("")
        for e in errors:
            out.append(f"- {_cell(e)}")
        out.append("")
    return "\n".join(out)


def monthrange_len(month: str) -> int:
    y, m = int(month[:4]), int(month[5:7])
    return monthrange(y, m)[1]


# ----------------------------------------------------- weekly Watchdog (126)
# External control loop, round 126 (super-agent落点三): deterministic checks
# run from OUTSIDE the lane and the Actions stack. Round 118 recorded the
# blind spot this cures — "绊网失明": staleness-check is itself an Actions
# workflow, so a billing freeze blinds every cloud tripwire and the nightly
# report became the only alarm layer. The Watchdog has zero Actions
# dependency (gh is read-only and optional). Failure classification reuses
# the Fast-Path triage rules from scripts/ops_local_refresh.py (single
# source of truth); the trigger→criteria→action modelling per
# docs/ops-local-refresh.md §失败处置矩阵与节奏.

WATCHDOG_WORKFLOWS = (
    "ci.yml", "deploy-pages.yml", "e3-forward.yml", "publish-site.yml",
    "refresh-terminal-data.yml", "staleness-check.yml", "vintage-probe.yml",
)
LEDGER_PATH = Path("runs") / "ledger.jsonl"
# Result-bearing confirmatory families: a row here MUST be preceded by a
# config_committed row with the same config_sig (the pre-registration
# "config_committed BEFORE result" invariant, spot-checked). The E3 forward
# lane uses its own forward_iset_frozen family and the pre-2026-07-28 rows
# predate the event convention — both out of scope by design (verified
# against the real 71-row ledger before pinning the rule).
RESULT_FAMILIES = frozenset({"confirmatory:first", "oos_result"})
_HARD_FAIL_STEP_RE = re.compile(r"HARD-FAIL: hard-fail step '([^']+)'")
_HARD_FAIL_GATE_RE = re.compile(r"HARD-FAIL: (strict-JSON gate)")


def _watchdog_run_rows(workflow: str, repo: Path) -> list[dict] | None:
    """Latest rows for one workflow (newest first), or None when gh is
    unreachable — unverified is reported, never scored as a failure."""
    try:
        proc = subprocess.run(
            ["gh", "run", "list", "--workflow", workflow, "--limit", "5",
             "--json",
             "databaseId,workflowName,conclusion,createdAt,updatedAt"],
            cwd=str(repo), capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=GH_TIMEOUT_S)
        if proc.returncode != 0:
            return None
        rows = json.loads(proc.stdout)
        return rows if isinstance(rows, list) else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def classify_workflow(workflow: str, repo: Path, fetcher=None,
                      jobs_sig=None) -> dict:
    """Latest-run state for one workflow; reds go through the Fast-Path
    triage rules. Injected `fetcher`/`jobs_sig` keep tests hermetic."""
    if fetcher is None:
        fetcher = _watchdog_run_rows
    if jobs_sig is None:
        import ops_local_refresh as lane
        jobs_sig = lane._gh_jobs_signature
    rows = fetcher(workflow, repo)
    if rows is None:
        return {"wf": workflow, "state": "unverified"}
    if not rows:
        return {"wf": workflow, "state": "no-runs"}
    latest = rows[0]
    conclusion = latest.get("conclusion")
    if conclusion != "failure":
        return {"wf": workflow, "state": str(conclusion or "other")}
    run_id = latest.get("databaseId")
    if jobs_sig is not None and run_id:
        try:
            jobs = jobs_sig(int(run_id))
        except (TypeError, ValueError):
            jobs = None
    else:
        jobs = None
    import ops_local_refresh as lane
    return {"wf": workflow, "state": "failure",
            "bucket": lane.classify_run_row(latest, jobs)}


def ledger_spot_check(repo: Path) -> tuple[list[str], dict]:
    """Read-only integrity spot-check of the append-only audit log:
    JSONL parses; result-family rows are preceded by a config_committed row
    with the same config_sig; config_committed rows carry a frozen config."""
    findings: list[str] = []
    path = repo / LEDGER_PATH
    if not path.is_file():
        return ([f"{LEDGER_PATH}: missing — the append-only audit log must "
                 "exist"], {})
    raw = path.read_bytes()
    if not raw.endswith(b"\n"):
        findings.append(f"{LEDGER_PATH}: file does not end with a newline")
    committed: dict[str, int] = {}
    stats = {"rows": 0, "config_committed": 0, "result_family": 0,
             "pre_convention": 0}
    for i, line in enumerate(
            raw.decode("utf-8", errors="replace").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError as exc:
            findings.append(f"{LEDGER_PATH}:{i}: unparseable JSONL ({exc})")
            continue
        if not isinstance(row, dict):
            findings.append(f"{LEDGER_PATH}:{i}: row is not an object")
            continue
        stats["rows"] += 1
        sig = row.get("config_sig")
        event = row.get("event")
        if event == "config_committed":
            stats["config_committed"] += 1
            if not row.get("config"):
                findings.append(f"{LEDGER_PATH}:{i}: config_committed row "
                                "without a frozen config object")
            if isinstance(sig, str) and sig:
                committed.setdefault(sig, i)
        elif event in RESULT_FAMILIES:
            stats["result_family"] += 1
            if not (isinstance(sig, str) and sig):
                findings.append(f"{LEDGER_PATH}:{i}: {event} row without a "
                                "config_sig")
            elif sig not in committed:
                findings.append(
                    f"{LEDGER_PATH}:{i}: {event} row has no earlier "
                    "config_committed row with its config_sig — "
                    "config_committed-BEFORE-result violated")
        elif event is None:
            stats["pre_convention"] += 1
    return findings, stats


def spin_detection(repo: Path, max_evenings: int = 14) -> tuple[list[str], int]:
    """Same failing step on >=2 consecutive LOGGED evenings = spinning in
    place (原地打转) — report to human. The 11-03..05 form8k cap self-lock
    is exactly the pattern this surfaces. Returns (findings, scanned)."""
    log_root = repo / LOG_SUBDIR
    if not log_root.is_dir():
        return [], 0
    evenings: list[tuple[str, set[str]]] = []
    scanned = 0
    for day_dir in sorted((p for p in log_root.iterdir() if p.is_dir()),
                          reverse=True):
        log_file = day_dir / "run.log"
        if not log_file.is_file():
            continue
        try:
            text = log_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        scanned += 1
        names = set(_HARD_FAIL_STEP_RE.findall(text))
        names |= set(_HARD_FAIL_GATE_RE.findall(text))
        if names:
            evenings.append((day_dir.name, names))
            if len(evenings) >= max_evenings:
                break
    findings: list[str] = []
    if len(evenings) >= 2:
        common = set(evenings[0][1])
        dates = [evenings[0][0]]
        for day, names in evenings[1:]:
            common &= names
            if not common:
                break
            dates.append(day)
        if common and len(dates) >= 2:
            findings.append(
                "spin (原地打转): " + ", ".join(sorted(common))
                + " failing on consecutive logged evenings "
                + ", ".join(reversed(dates)) + " — human disposition needed "
                "(docs/ops-local-refresh.md 处置矩阵)")
    return findings, scanned


def run_weekly(repo: Path, now: datetime | None = None, fetcher=None,
               jobs_sig=None, gate_thresholds: dict | None = None
               ) -> tuple[str, int]:
    """The --weekly mode: render the external-audit report and return
    (markdown, exit_code). 0 = clean; 1 = findings needing human attention;
    gh-unreachable checks are reported as 未能核对, never scored as failures.
    Round 14 (gate-assessment-bridge) appends the promotion-gate summary
    line at the tail — PRESENTATIONAL ONLY, never counted into findings or
    the exit code (零启用: the L2 key stays with the owner); gate_thresholds
    is the pass-through hook for the owner's future calibration (None =
    all axes honestly uncalibrated)."""
    now = now or datetime.now()
    lines: list[str] = [
        "# Weekly Watchdog — external audit (outside lane + Actions stack)",
        "",
        f"> Generated {now.isoformat(timespec='seconds')} by "
        "`scripts/monthly_review.py --weekly` — deterministic, read-only; "
        "zero Actions dependency (round 118's freeze blind-spot cure).",
        "",
    ]
    findings: list[str] = []
    infos = [classify_workflow(wf, repo, fetcher=fetcher, jobs_sig=jobs_sig)
             for wf in WATCHDOG_WORKFLOWS]
    lines += ["## 1. Workflow health (latest run, 7 workflows)", "",
              "| Workflow | latest | triage bucket |", "|---|---|---|"]
    platform_reds: list[str] = []
    for info in infos:
        bucket = info.get("bucket") or "—"
        if info["state"] == "failure" and bucket == "platform-failure":
            platform_reds.append(info["wf"])
        if info["state"] == "failure" and bucket == "code-defect":
            findings.append(f"workflow real red (code-defect): {info['wf']}")
        lines.append(f"| {info['wf']} | {info['state']} | {bucket} |")
    lines.append("")
    if len(platform_reds) >= 2:
        lines.append(
            "- billing-lock signature (≥2 workflows fast-red platform): "
            + ", ".join(platform_reds)
            + " — account-level platform failure, OWNER KEY (billing "
              "playbook); merged here, not itemized.")
        findings.append("platform-failure: billing lock — owner key needed")
    elif platform_reds:
        lines.append(f"- platform-failure red on {platform_reds[0]} — owner "
                     "key (billing playbook) if it persists.")
        findings.append(f"platform-failure: {platform_reds[0]}")
    lines.append("")

    ledger_findings, ledger_stats = ledger_spot_check(repo)
    lines += ["## 2. Ledger integrity spot-check "
              f"({LEDGER_PATH}, {ledger_stats.get('rows', 0)} rows)", ""]
    if not ledger_stats:
        lines.append("- ledger not found (see findings)")
    else:
        lines += [
            f"- rows {ledger_stats['rows']} · config_committed "
            f"{ledger_stats['config_committed']} · result-family "
            f"{ledger_stats['result_family']} · pre-convention-era "
            f"{ledger_stats['pre_convention']} (no event field — out of "
              "scope by design)",
            "- invariant: every result-family row preceded by "
              "config_committed with the same config_sig → "
              + ("**OK**" if not ledger_findings else "**VIOLATED**"),
        ]
    lines.append("")
    findings += [f"ledger: {x}" for x in ledger_findings]

    spin, scanned = spin_detection(repo)
    lines += [f"## 3. Spin detection (same hard-fail step ≥2 consecutive "
              f"logged evenings; scanned {scanned} recent evening log(s))",
              ""]
    lines += [f"- {x}" for x in spin] if spin else \
        ["- no spin detected"]
    lines.append("")
    findings += spin

    recon_findings, recon_stats = proposal_reconciliation(repo)
    lines += ["## 4. Proposal-closure reconciliation "
              "(backlog 候选 key: prop:* → tasks/ 三区一致性，只读)",
              "",
              f"- backlog 在册提案键 {recon_stats['backlog_keys']} · tasks 侧在册 "
              + " · ".join(f"{z} {recon_stats['zones'][z]}"
                          for z in TASKS_ZONES),
              "- invariants: 一个提案键至多存在于一个 tasks 区 · 已 completed "
              "的提案其 backlog 行须人工划线销项 → "
              + ("**OK**" if not recon_findings else "**DRIFT**")]
    if recon_findings:
        lines += [f"- {x}" for x in recon_findings]
    lines.append("")
    findings += [f"proposal-recon: {x}" for x in recon_findings]

    lines += [f"## Findings requiring human attention: {len(findings)}", ""]
    lines += [f"- {x}" for x in findings] if findings else \
        ["- none — walk away"]
    # Round 14 (gate-assessment-bridge): the summary line rides AFTER the
    # findings section and NEVER joins `findings` — the exit code below is
    # byte-identical to the pre-round-14 semantics (1 if findings else 0).
    lines.append("")
    backlog_file = repo / BACKLOG_PATH
    backlog_text = (backlog_file.read_text(encoding="utf-8", errors="replace")
                    if backlog_file.is_file() else "")
    lines.append(promotion_gate_summary_line(
        _collect_prediction_records(backlog_text), gate_thresholds))
    return "\n".join(lines) + "\n", (1 if findings else 0)


# -------------------------- propose engine + closure recon (gen2 item 3)
# The self-evolution engine MVP: signal -> audit -> proposal -> OWNER GATE
# (WORKFLOW §6 milestone boundary) -> dispatch (orchestrate_dispatch.py
# --task --lane, :192-199) -> build -> verify (pytest+ruff+closure recon) ->
# sediment (--append-lessons-from). This module carries the deterministic
# middle: EXISTING signals x rule table -> S/M/L proposal cards with evidence
# pointers + prop: dedup keys (thread: IDs where the registry maps one) —
# ZERO LLM, ZERO new collection, ZERO network (git pickaxe is read-only and
# injectable; unavailable = honest absence, never a guess). Guards (gen2
# report §4, tightened this round): the engine is READ-ONLY on
# state/backlog.md and tasks/ — output goes to stdout/--out for a human or
# the month-end session to paste into the backlog candidates section; a key
# already present (backlog or any tasks zone) degrades to a timestamp-
# refresh instruction, never a duplicate card and never an auto-write; any
# future research-face rule MUST set research=True so the card carries the
# forced 7-gate/prereg/ledger-row/owner-gate annotation.

BACKLOG_PATH = Path("state") / "backlog.md"
TASKS_ZONES = ("active", "completed", "rejected")
WEEKLY_ANCHOR_NAME = "weekly_watchdog.md"
PROPOSAL_KEY_RE = re.compile(r"key:\s*(prop:[0-9A-Za-z:\-_]+)")
PLATFORM_COUNT_RE = re.compile(r"(\d+)×")
BACKLOG_AGING_DAYS = 90
PERSISTENT_MIN_EVENINGS = 3
PROPOSAL_RESEARCH_GATE = ("research-gate: 7-gate 数据准入 + 预注册 + 新 ledger 行 "
                          "+ 业主研究门 —— 引擎只呈报，绝不执行")


def _slug(text: str) -> str:
    """Stable ASCII slug for dedup keys (CJK-only text falls back to a
    deterministic sha1 prefix — never an empty key)."""
    s = re.sub(r"[^0-9A-Za-z]+", "-", text).strip("-")[:40]
    return s or hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]


def scan_proposal_keys(text: str) -> set[str]:
    """Every `key: prop:...` marker present in a markdown text."""
    return set(PROPOSAL_KEY_RE.findall(text))


def backlog_open_candidates(text: str) -> list[str]:
    """First lines of OPEN candidate bullets in the 开放候选 section
    (struck-through ~~ bullets are closed history — excluded)."""
    heads: list[str] = []
    in_section = False
    for line in text.splitlines():
        if line.startswith("## "):
            in_section = "开放候选" in line
            continue
        if not in_section or not line.startswith("- "):
            continue
        head = line[2:].strip()
        if head.startswith("~~") or not head:
            continue
        heads.append(head)
    return heads


def _git_pickaxe_date(repo: Path, needle: str) -> str | None:
    """ISO date of the last commit whose state/backlog.md diff changed the
    occurrence count of `needle` (= when that candidate last moved), or None
    when git/history is unavailable — aging unknown, no card, no guess."""
    try:
        proc = subprocess.run(
            ["git", "log", "-1", "--format=%cI", f"-S{needle}", "--",
             str(BACKLOG_PATH)],
            cwd=str(repo), capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def latest_day_file(repo: Path, name: str) -> tuple[str, str] | None:
    """(date, text) of the newest runs/ops_local_refresh/<date>/<name> across
    day directories, or None. Parse failures skip to the next-newest day —
    the returned date keeps any staleness visible in the evidence line."""
    root = repo / LOG_SUBDIR
    if not root.is_dir():
        return None
    for day_dir in sorted((p for p in root.iterdir() if p.is_dir()),
                          reverse=True):
        f = day_dir / name
        if not f.is_file():
            continue
        try:
            return day_dir.name, f.read_text(encoding="utf-8",
                                             errors="replace")
        except OSError:
            continue
    return None


def _weekly_finding_lines(anchor_text: str) -> list[str]:
    """Bullet lines under '## Findings requiring human attention' in a
    persisted weekly anchor (empty when the section says none)."""
    out: list[str] = []
    in_section = False
    for line in anchor_text.splitlines():
        if line.startswith("## "):
            in_section = "Findings requiring human attention" in line
            continue
        if in_section and line.startswith("- "):
            if "none — walk away" not in line:
                out.append(line[2:].strip())
    return out


def proposal_reconciliation(repo: Path,
                            now_month: str | None = None) -> tuple[list[str], dict]:
    """Read-only closure check (the engine's verify leg, run inside --weekly):
    proposal keys pasted into state/backlog.md vs their dispatch state in
    tasks/{active,completed,rejected}/. Invariants: one key lives in at most
    ONE tasks zone; a completed proposal's backlog line must be struck
    through (~~) or gone — a still-open line for completed work is drift for
    a human to strike by hand (the engine never edits the backlog).
    Round 12 adds the overdue-outcome watch block: an INDEPENDENT stats
    section (summary + per-card listing) so overdue cards don't drown in
    the per-row findings flow (see overdue_outcome_records)."""
    stats: dict = {"backlog_keys": 0, "task_keys": 0,
                   "zones": {z: 0 for z in TASKS_ZONES}}
    findings: list[str] = []
    backlog_file = repo / BACKLOG_PATH
    backlog_text = (backlog_file.read_text(encoding="utf-8",
                                           errors="replace")
                    if backlog_file.is_file() else "")
    backlog_keys = scan_proposal_keys(backlog_text)
    stats["backlog_keys"] = len(backlog_keys)
    # Round 131: Brier-style prediction reconciliation rides the same
    # read-only sweep (RLCD prediction-error leg; zero writes, zero stats
    # beyond per-record squared error).
    pred_lines = reconcile_predictions(
        backlog_text, now_month or datetime.now().strftime("%Y-%m"))
    stats["prediction_records"] = len(pred_lines)
    findings += pred_lines
    # Round 12 (overdue-outcome-watch): INDEPENDENT stats block — summary
    # line + one listing row per overdue card. Zero overdue -> the block
    # renders NOTHING (todo_or_die: in-period cards are zero noise;
    # honest-absence precedent). Presentation only, non-blocking: outcomes
    # arrive only with real month-end data (2611.03928 zero-query-budget
    # audit), and the engine never records an outcome for a human.
    overdue = overdue_outcome_records(
        _collect_prediction_records(backlog_text),
        now_month or datetime.now().strftime("%Y-%m"))
    stats["overdue_outcomes"] = len(overdue)
    if overdue:
        findings.append(
            f"overdue outcome 统计：{len(overdue)} 张预测卡 due 已过仍未记 "
            "outcome（todo_or_die 呈报不阻断；2611.03928 零查询预算纯呈报"
            "——outcome 只随月末真实数据到；人补记，引擎只读不代记）:")
        for r in overdue:
            findings.append(
                f"  - overdue: {r['claim']}"
                f"（facts: due={r['due']}、outcome 未记；judgments: "
                f"p={r['p'] if r['p'] is not None else '待填'}）")
    zone_hits: dict[str, list[str]] = {}
    for zone in TASKS_ZONES:
        zone_dir = repo / "tasks" / zone
        if not zone_dir.is_dir():
            continue
        for task_file in sorted(zone_dir.glob("*.md")):
            try:
                text = task_file.read_text(encoding="utf-8",
                                           errors="replace")
            except OSError:
                continue
            hits = scan_proposal_keys(text)
            for key in hits:
                zone_hits.setdefault(key, []).append(zone)
            stats["zones"][zone] += len(hits)
    stats["task_keys"] = len(zone_hits)
    for key, zones in sorted(zone_hits.items()):
        if len(set(zones)) > 1:
            findings.append(f"{key} appears in multiple tasks zones: "
                            + ", ".join(sorted(set(zones))))
    for key in sorted(backlog_keys):
        if "completed" in zone_hits.get(key, []):
            for line in backlog_text.splitlines():
                if key in line and "~~" not in line:
                    findings.append(
                        f"{key} completed (tasks/completed) but its backlog "
                        "line is still open — strike it by hand (the engine "
                        "never edits the backlog)")
                    break
    return findings, stats


def _card_from_weekly_finding(line: str, day: str) -> dict:
    ev = [f"runs/ops_local_refresh/{day}/{WEEKLY_ANCHOR_NAME}: {line}"]
    m = re.match(r"workflow real red \(code-defect\): (.+)", line)
    if m:
        wf = m.group(1).strip()
        return {"key": f"prop:ci-red:{_slug(wf)}", "size": "M",
                "thread": f"thread:ci-red:{wf}",
                "title": f"修复 CI 红：{wf}",
                "action": "按处置矩阵修复并带测试钉（先例：news_feed 时间炸弹、"
                          "IPO 帽感知）",
                "evidence": ev}
    if line.startswith("platform-failure"):
        return {"key": "prop:platform-billing", "size": "S",
                "thread": "thread:platform-billing",
                "title": "billing 钥匙区（只呈报不催办）",
                "action": "业主解锁后按 runbook『解锁后一键恢复』顺序行动；"
                          "工程侧零代办",
                "evidence": ev}
    if line.startswith("spin"):
        return {"key": "prop:spin", "size": "M", "thread": "thread:spin",
                "title": "诊断连败步骤根因（spin）",
                "action": "诊断连续晚失败根因并处方修复；修复须显式提交+测试钉"
                          "（先例 5a1075f650）",
                "evidence": ev}
    if line.startswith("ledger: "):
        return {"key": "prop:ledger-anomaly", "size": "S",
                "thread": "thread:ledger-anomaly",
                "title": "账本异常呈报（业主裁决区）",
                "action": "立即呈报业主裁决——归并/弃置均不可逆，工程侧零代办"
                          "（处置矩阵）",
                "evidence": ev}
    return {"key": f"prop:weekly:{_slug(line[:40])}", "size": "S",
            "thread": None, "title": "--weekly 发现待人工处置",
            "action": "核对 weekly_watchdog.md 该发现并处方（引擎不归类=人工归类）",
            "evidence": ev}


def _collect_proposal_signals(repo: Path, month: str, now: datetime,
                              git_log=None) -> dict[str, dict]:
    """The rule table: five EXISTING signal classes -> pre-dedup cards,
    merged by prop: key (same-key signals join evidence, never duplicate)."""
    raw: list[dict] = []
    # R1 spin (local run logs; the 11-03..05 form8k shape)
    spin, _scanned = spin_detection(repo)
    for s in spin:
        raw.append({"key": "prop:spin", "size": "M", "thread": "thread:spin",
                    "title": "诊断连败步骤根因（spin）",
                    "action": "诊断连续晚失败根因并处方修复；修复须显式提交+"
                              "测试钉（先例 5a1075f650）",
                    "evidence": [s]})
    # R2 platform reds from the latest night package (folded thread line)
    pkg = latest_day_file(repo, "night_package.json")
    if pkg is not None:
        day, text = pkg
        try:
            threads = (json.loads(text).get("threads") or {})
        except ValueError:
            threads = {}
        for line in threads.get("platform-failure") or []:
            m = PLATFORM_COUNT_RE.search(line)
            ev = [f"runs/ops_local_refresh/{day}/night_package.json: {line}"]
            if m and int(m.group(1)) >= 2:
                ev.append("≥2 工作流同晚平台红 = billing 锁签名（billing "
                          "playbook）")
            raw.append({"key": "prop:platform-billing", "size": "S",
                        "thread": "thread:platform-billing",
                        "title": "billing 钥匙区（只呈报不催办）",
                        "action": "业主解锁后按 runbook『解锁后一键恢复』顺序"
                                  "行动；工程侧零代办",
                        "evidence": ev})
    # R3 persistent soft-fails on >=3 evenings of the month (SUMMARYs)
    errors: list[str] = []
    days, _push = collect_log_days(repo, month, errors)
    name_dates: dict[str, list[str]] = {}
    for d in days:
        for name in d["persistent_soft_fails"]:
            name_dates.setdefault(str(name), []).append(d["date"])
    for name, dates in sorted(name_dates.items()):
        if len(dates) >= PERSISTENT_MIN_EVENINGS:
            raw.append({"key": f"prop:persistent:{_slug(name)}", "size": "S",
                        "thread": None,
                        "title": f"persistent 软失败 ≥{PERSISTENT_MIN_EVENINGS}"
                                 f" 晚：{name}",
                        "action": "核对 docs/source-redundancy.md 对应源剧本"
                                  "（备役/帽/礼貌参数），必要时专轮处方",
                        "evidence": [f"{month} SUMMARY persistent_soft_fails: "
                                     + ", ".join(dates)]})
    # R4 backlog candidate aging (git pickaxe; unavailable = no card)
    backlog_file = repo / BACKLOG_PATH
    if backlog_file.is_file():
        text = backlog_file.read_text(encoding="utf-8", errors="replace")
        runner = git_log or _git_pickaxe_date
        for head in backlog_open_candidates(text):
            iso = runner(repo, head[:60])
            if not iso:
                continue
            try:
                moved = datetime.fromisoformat(iso)
            except ValueError:
                continue
            if moved.tzinfo is not None:  # git %cI is offset-aware
                moved = moved.astimezone().replace(tzinfo=None)
            age = (now - moved).days
            if age > BACKLOG_AGING_DAYS:
                raw.append({
                    "key": f"prop:backlog-aging:{_slug(head)}", "size": "S",
                    "thread": None,
                    "title": "backlog 候选 >"
                             f"{BACKLOG_AGING_DAYS} 天未动："
                             + head.replace("**", "")[:60],
                    "action": "里程碑边界再裁决（accept/defer/reject）或销项"
                              "——backlog deadman（治落差缺口 2）",
                    "evidence": [f"state/backlog.md『{head[:60]}』最后变更 "
                                 f"{iso[:10]}（git pickaxe，只读）"]})
    # R5 findings from the latest persisted --weekly anchor (Friday carrier)
    anchor = latest_day_file(repo, WEEKLY_ANCHOR_NAME)
    if anchor is not None:
        day, text = anchor
        raw += [_card_from_weekly_finding(line, day)
                for line in _weekly_finding_lines(text)]
    cards: dict[str, dict] = {}
    for card in raw:
        first = cards.setdefault(card["key"], card)
        if first is not card:
            first["evidence"] = first["evidence"] + card["evidence"]
    return cards


def render_card(card: dict) -> list[str]:
    """One paste-ready proposal card (the backlog candidates format)."""
    out = [f"- **[{card['size']}] {card['title']}**（key: {card['key']}）"]
    if card.get("thread"):
        out.append(f"  - thread: {card['thread']}（续写该 Thread，不新起小节）")
    out += [f"  - evidence: {e}" for e in card["evidence"]]
    out.append(f"  - proposal: {card['action']}")
    pred = card.get("prediction")
    if isinstance(pred, dict) and pred.get("claim"):
        p_val = pred.get("p")
        p_txt = f"{p_val}" if isinstance(p_val, float) else "待月末会话填写 0..1"
        out.append(f"  - prediction: {pred['claim']}"
                   f"（judgments: p={p_txt}；facts: "
                   f"due={pred.get('due_month', '—')}；"
                   "对账记法=该条目追加 → outcome: y=0|1 (YYYY-MM-DD)，"
                   "resolved 后 reconcile 记 (p−y)²；round 131 Brier 式"
                   "预测误差=改进信号，RLCD 同构——引擎绝不代填 p，诚实边界"
                   "照守；p>0.6 高带=仅自动进入对账候选呈现（代码规则门，"
                   "见 reconcile_predictions docstring，禁 n=1 拟合））")
    if card.get("research"):
        out.append(f"  - {PROPOSAL_RESEARCH_GATE}")
    out.append("  - disposition: 里程碑边界 accept → tasks/active/ + "
               "orchestrate_dispatch --lane executor · defer 留候选区 · "
               "reject → tasks/rejected/")
    return out


def reconcile_predictions(backlog_text: str,
                          now_month: str) -> list[str]:
    """Round 131 (Brier-style reconciliation, the RLCD 'prediction error =
    improvement signal' leg): read-only scan of pasted proposal entries in
    state/backlog.md. A prediction line opens a record (claim, p, due);
    a later 'outcome: y=0|1 (date)' line on the same entry closes it. Only
    records with BOTH p filled and outcome recorded score (p-y)^2 — pending
    (due passed, no outcome) and unfilled (p missing) are listed honestly;
    nothing is invented, no statistics beyond per-record squared error.

    Round 131-续 (judgments/facts split — TypeSafe 'Don't Call It a
    Decision Model' ledger discipline, presentation-level only): every
    output row separates judgments (the model's spoken p — never
    engine-filled, never recalibrated) from facts (the code-recorded
    outcome y / due month), so a mismatch reads as 'which side was wrong'
    instead of one blended line. Three-band threshold semantics live HERE
    in the code rule gate, NEVER in any LLM prompt: p>0.6 = high band
    whose ONLY meaning is auto-entry into this reconciliation candidate
    listing — no auto-disposition, no gate bypass (the three human gates
    stand: research-gate PROPOSAL_RESEARCH_GATE, the engine never fills
    p, ledger/backlog owner adjudication). Band cuts are FIXED
    presentation constants: the n=1 monthly sample forbids any threshold
    fitting (RouteLLM anchor — calibration needs a representative query
    distribution, state/backlog.md 延伸索引⑤)."""
    lines_out: list[str] = []
    records = _collect_prediction_records(backlog_text)
    resolved_ids_iter = iter(_resolved_row_id_seq(records, now_month))
    for r in records:
        band = ("；高带 p>0.6——仅自动进入对账候选呈现，无任何自动处置"
                if r["p"] is not None and r["p"] > 0.6 else "")
        if r["p"] is None:
            lines_out.append(f"prediction 未填 p（judgments: 无——诚实缺省，"
                             f"待月末会话；facts: due={r['due'] or '—'}）: "
                             f"{r['claim']}")
        elif r["y"] is None:
            overdue = (r["due"] is not None and r["due"] < now_month)
            lines_out.append(f"prediction pending outcome: {r['claim']}"
                             f"（judgments: p={r['p']}；facts: "
                             f"due={r['due'] or '—'}、outcome 未记"
                             f"{'（due 已过）' if overdue else ''}）{band}")
        else:
            brier = (r["p"] - r["y"]) ** 2
            hit = "命中" if (r["p"] >= 0.5) == (r["y"] == 1) else "未命中"
            lines_out.append(f"[{next(resolved_ids_iter)}] prediction "
                             f"resolved: {r['claim']}"
                             f"（judgments: p={r['p']}；facts: y={r['y']}；"
                             f"(p−y)²={brier:.3f}, {hit}）{band}")
    return lines_out


def _collect_prediction_records(backlog_text: str) -> list[dict]:
    """Round 137 (calibration-aggregator ring 1a, design report
    reports/design/2026-11-14-personal-training-method-and-automation-ladder.md
    §2): the reconcile_predictions parse loop lifted VERBATIM so every
    calibration consumer reads the exact same records — one parser, N
    consumers (reconciliation, bucketed aggregation, focus-feedback
    selector), zero drift between per-row and aggregated views."""
    import re as _re
    records: list[dict] = []
    cur: dict | None = None
    for line in (backlog_text or "").splitlines():
        if "prediction:" in line and "（p=" in line:
            claim = line.split("prediction:", 1)[1].split("（p=", 1)[0].strip()
            m = _re.search(r"p=([\d.]+)", line)
            due = _re.search(r"due=(\d{4}-\d{2})", line)
            cur = {"claim": claim[:80],
                   "p": float(m.group(1)) if m else None,
                   "due": due.group(1) if due else None,
                   "y": None}
            records.append(cur)
            continue
        m = _re.search(r"outcome:\s*y=([01])\s*\((\d{4}-\d{2}-\d{2})\)", line)
        if m and cur is not None:
            cur["y"] = int(m.group(1))
    return records


def overdue_outcome_records(records: list[dict],
                            now_month: str) -> list[dict]:
    """Round 12 (overdue-outcome-watch): the prediction cards whose due
    month has PASSED (due < now_month — the same strict time gate as the
    per-row '（due 已过）' marker in reconcile_predictions) with no outcome
    recorded yet. todo_or_die semantics (state/backlog.md 延伸索引㉘):
    due passed = explicit, loud, NON-BLOCKING surfacing; in-period cards
    are zero noise and a zero-overdue account renders nothing
    (honest-absence precedent). 2611.03928 (延伸索引㉚): zero query
    budget, pure presentation audit — the engine never fetches or records
    an outcome for a human (read-only red line)."""
    return [r for r in records
            if r["y"] is None and r["due"] is not None
            and r["due"] < now_month]


# Calibration band cuts are FIXED presentation constants — the same
# discipline as the three-band gate above (n=1-era monthly samples forbid
# threshold fitting; RouteLLM anchor, state/backlog.md 延伸索引⑤). Buckets
# are presentation buckets ONLY: no p adjustment, no threshold advice.
_CALIBRATION_BAND_CUTS: tuple[float, ...] = (0.5, 0.6, 0.7, 0.8, 0.9, 1.0)


def _bss_components(resolved: list[dict]) -> tuple[float, float, float, float | None] | None:
    """iterate round 12 (cross-month-evolution): the BSS math lifted VERBATIM
    from promotion_gate_assessment's X axis so the monthly snapshot and the
    gate read ONE implementation. BS = mean (p-y)^2; base = the unconditional
    base-rate climatology predictor 'always output p̄' (p̄ = historical hit
    rate); BS_base = mean (p̄-y)^2 = p̄(1-p̄); BSS = 1 - BS/BS_base. Returns
    (bs, bs_base, p_bar, bss) — bss None on the degenerate constant base
    (BS_base=0, all y identical); None on zero rows."""
    if not resolved:
        return None
    n = len(resolved)
    bs = sum((r["p"] - r["y"]) ** 2 for r in resolved) / n
    p_bar = sum(r["y"] for r in resolved) / n
    bs_base = sum((p_bar - r["y"]) ** 2 for r in resolved) / n
    bss = (1 - bs / bs_base) if bs_base != 0.0 else None
    return bs, bs_base, p_bar, bss


def calibration_bucket_summary(records: list[dict]) -> list[str]:
    """Round 137 (training-method ring 1a — calibration aggregator, design
    report §2): RECORDING-ONLY bucketed hit presentation over the records
    _collect_prediction_records returns. Resolved rows with p>=0.5 land in
    fixed buckets [0.5,0.6)/.../[0.9,1.0] (top bucket closed at p=1.0):
    per bucket n / hits / hit rate + Wilson 95% CI (statsmodels
    proportion_confint — an already-pinned project dependency, zero new)
    plus raw-p value counts (anti-clustering, arXiv:2609.32470:
    off-the-shelf verbalized confidence clusters at a few high values — a
    bucket of identical p's is NOT evidence of calibration). p<0.5
    resolved, p-missing, and pending rows are listed separately and NEVER
    bucketed. The summary mean Brier averages the same per-row (p-y)^2 the
    reconciliation scores (judgments/facts split intact — the engine never
    recalibrates p). Zero scored rows -> a single honest baseline line, no
    empty table."""
    from statsmodels.stats.proportion import proportion_confint

    resolved = [r for r in records
                if r["p"] is not None and r["y"] is not None]
    if not resolved:
        return ["none yet (baseline collection month)"]
    bucketed = [r for r in resolved if r["p"] >= _CALIBRATION_BAND_CUTS[0]]
    below = [r for r in resolved if r["p"] < _CALIBRATION_BAND_CUTS[0]]
    out_of_range = [r for r in resolved if r["p"] > 1.0]
    pending = [r for r in records if r["p"] is not None and r["y"] is None]
    missing_p = [r for r in records if r["p"] is None]
    mean_brier = sum((r["p"] - r["y"]) ** 2 for r in resolved) / len(resolved)
    lines: list[str] = [
        "calibration buckets（记录性呈现——呈现≠校准，禁据此调 p 或定阈值；"
        "桶界为固定呈现常量）:"]
    n_bands = len(_CALIBRATION_BAND_CUTS) - 1
    for i in range(n_bands):
        lo = _CALIBRATION_BAND_CUTS[i]
        hi = _CALIBRATION_BAND_CUTS[i + 1]
        last = i == n_bands - 1
        rows = [r for r in bucketed
                if lo <= r["p"] < hi or (last and r["p"] == hi)]
        if not rows:
            continue
        hits = sum(1 for r in rows if r["y"] == 1)
        ci_lo, ci_hi = proportion_confint(hits, len(rows), method="wilson")
        p_counts: dict[float, int] = {}
        for r in rows:
            p_counts[r["p"]] = p_counts.get(r["p"], 0) + 1
        counts_txt = "、".join(
            f"{p:g}×{n}" for p, n in sorted(p_counts.items(),
                                            key=lambda kv: (-kv[1], kv[0])))
        close = "]" if last else ")"
        lines.append(
            f"  - p∈[{lo:.1f},{hi:.1f}{close}: n={len(rows)}、"
            f"命中 {hits}（{hits / len(rows):.3f}）、"
            f"Wilson 95% CI ({ci_lo:.4f}, {ci_hi:.4f})、p 原值：{counts_txt}")
    lines.append(
        f"  - 分列不计桶：p<0.5 已对账 {len(below)} 条"
        f"（命中 {sum(1 for r in below if r['y'] == 0)}）、"
        f"p 未填 {len(missing_p)} 条、pending 未对账 {len(pending)} 条"
        + (f"、p>1.0 越界 {len(out_of_range)} 条（bounded 契约违例，如实呈现）"
           if out_of_range else ""))
    lines.append(f"  - 汇总 mean Brier = {mean_brier:.3f}"
                 f"（n={len(resolved)}，与逐条 (p−y)² 同口径取均值）")
    return lines


def run_propose(repo: Path, now: datetime | None = None,
                month: str | None = None,
                git_log=None) -> tuple[str, int]:
    """The --propose mode: deterministic signal x rule table -> proposal
    cards, deduped READ-ONLY against state/backlog.md and tasks/ (present
    keys degrade to refresh instructions — the engine never writes either).
    Returns (markdown, n_new_cards)."""
    now = now or datetime.now()
    month = month or now.strftime("%Y-%m")
    all_cards = _collect_proposal_signals(repo, month, now, git_log=git_log)
    backlog_file = repo / BACKLOG_PATH
    backlog_text = (backlog_file.read_text(encoding="utf-8",
                                           errors="replace")
                    if backlog_file.is_file() else "")
    present = scan_proposal_keys(backlog_text)
    dispatched: dict[str, str] = {}
    for zone in TASKS_ZONES:
        zone_dir = repo / "tasks" / zone
        if not zone_dir.is_dir():
            continue
        for task_file in sorted(zone_dir.glob("*.md")):
            try:
                text = task_file.read_text(encoding="utf-8",
                                           errors="replace")
            except OSError:
                continue
            for key in scan_proposal_keys(text):
                dispatched.setdefault(key, zone)
    new_cards, refresh = [], []
    for key in sorted(all_cards):
        if key in dispatched:
            refresh.append(f"{key} 已在 tasks/{dispatched[key]}/ 在册（已派发"
                           "）——勿重复提案")
        elif key in present:
            refresh.append(f"{key} 已在 state/backlog.md 候选区在册——请人工"
                           "更新该条时间戳/状态（引擎只读不代写）")
        else:
            new_cards.append(all_cards[key])
    lines = [
        "# Proposal cards — 确定性提案引擎（--propose，gen2 条目 3）",
        "",
        f"> Generated {now.isoformat(timespec='seconds')} by "
        "`scripts/monthly_review.py --propose` — 零 LLM、零网络（git 仅只读 "
        "pickaxe，不可用=不猜）；引擎对 state/backlog.md 与 tasks/ **只读**，"
        "产物经人工/月末会话粘贴候选区，同键在册→刷新指令，绝不自动写。",
        "",
        f"## 提案卡片（{len(new_cards)} 张）",
        "",
    ]
    for card in new_cards:
        lines += render_card(card)
    if not new_cards:
        lines.append("- 无提案——无信号或全部已在册（零提案=合法态，非失败）")
    lines += ["", f"## 刷新指令（{len(refresh)} 条，人工执行——引擎不自动写）",
              ""]
    lines += [f"- {r}" for r in refresh] if refresh else \
        ["- 无（无在册重复键）"]
    lines += ["", "## 信号面备注", "",
              f"- persistent 统计窗口：{month}（SUMMARY 晚数见月报）",
              f"- weekly 锚点：runs/ops_local_refresh/<date>/"
              f"{WEEKLY_ANCHOR_NAME}（无锚点=本周期 --weekly 未跑；固定载体="
              "每周五夜报班前置步）",
              f"- backlog 老化阈值：>{BACKLOG_AGING_DAYS} 天（git pickaxe 测得）"]
    return "\n".join(lines) + "\n", len(new_cards)


# ------------------------------------------------- Reflexion lessons (126)
# Protocol borrowed from noahshinn/reflexion (MIT, verified via gh api
# 2026-11-11): attempt → score against the pre-registered standard → textual
# lesson → inject into the next attempt. Borrowed as PROTOCOL ONLY (the repo
# is stale — unmaintained since 2025-01 per gh api, but NOT archived;
# no package, no dependency). The
# monthly review seeds the lessons deterministically; the month-end LLM
# session composes the text and writes it back via --append-lessons-from
# into state/handoff.md — where every session already reads first
# (AGENTS.md session protocol step 1), which is the "inject next cycle" leg.
# Budget: still the single 23:35 LLM session; lessons are generated only at
# month-end / on failure.

LESSON_HEADER_RE = re.compile(
    r"<!--\s*monthly-reflexion-lessons\s+month=(\d{4}-\d{2})[^>]*-->")
# gen2 item 4 (lessons contract): an entry is a bullet whose text starts with
# `event: <OP>`; the op verdicts borrow mem0's ADD/UPDATE/DELETE/NONE
# taxonomy (mem0ai/mem0, Apache-2.0, protocol-only, no package). UPDATE/
# DELETE are REFERENCE-STYLE marks — they name the id they retire
# (supersedes/voids month=YYYY-MM#n) and never rewrite old block bytes,
# isomorphic to the ledger's new-row-not-overwrite. evidence: lines are
# Inline & Spill path references (run.log / audit reports), append-only.
EVENT_OP_RE = re.compile(r"^\s*[-*]\s*event:\s*(ADD|UPDATE|DELETE|NONE)\b")
EVENT_REF_RE = re.compile(
    r"\b(supersedes|voids)\s+month=(\d{4}-\d{2})#(\d+)\b")
LESSONS_CONTRACT_NOTE = ("写回契约：每条教训 event: 四操作（ADD / "
                         "UPDATE[supersedes month=YYYY-MM#n] / DELETE[voids "
                         "month=YYYY-MM#n] / NONE）+ 计划形「下次 X 触发时做 "
                         "Y」非事件描述 + evidence: 路径引用 —— docs/"
                         "ops-local-refresh.md §lessons 块格式")
# iterate round 14 (memp-insight-lifecycle, framework ③; design spec
# reports/audits/2026-11-15-iterate-round-14.md §6.2): the deprecate×
# supersedes WRITE-READ closed loop as ONE pairing note — Memp's
# update/correct/deprecate lifecycle vocabulary over the IN-REGISTER four
# event ops (EVENT_OP_RE untouched — 轮 128-续 semantics stand). Read side
# (retire set + archive rendering) is the EXISTING active_lessons_view
# machinery, zero changes; anti-resurrection is the quality gate's
# retire-restatement criterion (framework ①) — three orthogonal gates.
# Memory-R1 outcome gating: keep/promote must cite the month's resolved
# reconciliation outcome evidence (ref=), never self-judgment;
# NOOP≡NONE aligns Memory-R1's no-op with the round-145 NONE precedent.
# Offline boundary: Memp online build, Memory-R1 PPO/GRPO training and the
# LoCoMo/MSC/LongMemEval benchmark infra are NOT adopted (steady-state
# one-session-per-evening + no-background-process red lines).
LESSON_LIFECYCLE_NOTE = ("生命周期配对（Memp update/correct/deprecate×在册四操作"
                         "；轮 14 框架③）：UPDATE[supersedes month=M#n]→retire "
                         "该 id、replacement 携教训前行；DELETE[voids month=M#n]"
                         "→同 retire 段=禁复述比对对象——两者须目标 id 真实存在"
                         "+outcome ref= 在场（Memory-R1 outcome 门控，伪 id→"
                         "quality-miss[bad-ref]）；ADD+hook/ref 信封→§6 全量呈现"
                         "+质量门三判据；NONE→旧条照旧（NOOP≡NONE，轮 145 先例）"
                         "——写侧引用式标记零回改×读侧 retire 集在册零改动×防回潮"
                         "=禁复述 retire 段，三门正交")


def _lessons_blocks(handoff_text: str) -> list[tuple[str, str]]:
    """All (month, block) lessons blocks in file order."""
    matches = list(LESSON_HEADER_RE.finditer(handoff_text))
    return [(m.group(1),
             handoff_text[m.start():matches[i + 1].start() if i + 1
                          < len(matches) else len(handoff_text)].rstrip())
            for i, m in enumerate(matches)]


def _parse_lesson_entries(block: str) -> list[dict]:
    """Contract entries of one block: bullets starting `event: <OP>` plus
    their attached (evidence:) lines. The n-th entry of a block is addressable
    as month#n — the id UPDATE/DELETE marks reference."""
    entries: list[dict] = []
    for line in block.splitlines():
        m = EVENT_OP_RE.match(line)
        if m:
            entries.append({"op": m.group(1), "lines": [line.rstrip()]})
        elif entries and line.strip():
            entries[-1]["lines"].append(line.rstrip())
    return entries


def active_lessons_view(handoff_text: str) -> tuple[str, list[str]] | None:
    """gen2 item 4: the ACTIVE lessons aggregate (replaces single-block
    lookback) — (latest_month, rendered active entry lines). Active = the
    whole latest block + every historical entry NOT retired by a later
    reference-style mark. Marks are permanent, ledger-like: the id an
    UPDATE/DELETE names stays retired even if the marking entry is itself
    superseded later (its own replacement carries the lesson forward)."""
    blocks = _lessons_blocks(handoff_text)
    if not blocks:
        return None
    retired: set[tuple[str, int]] = set()
    for _month, block in blocks:
        for entry in _parse_lesson_entries(block):
            ref = EVENT_REF_RE.search(" ".join(entry["lines"]))
            if entry["op"] in ("UPDATE", "DELETE") and ref:
                retired.add((ref.group(2), int(ref.group(3))))
    latest_month, latest_block = blocks[-1]

    def _render(month: str, idx: int, entry: dict) -> str:
        head = entry["lines"][0].lstrip().lstrip("-*").strip()
        return f"[{month}#{idx}] {head}"

    lines = [_render(month, idx, entry)
             for month, block in blocks[:-1]
             for idx, entry in enumerate(_parse_lesson_entries(block), 1)
             if (month, idx) not in retired]
    lines += [_render(latest_month, idx, entry)
              for idx, entry in enumerate(_parse_lesson_entries(latest_block),
                                          1)]
    return latest_month, lines


def latest_lessons_block(handoff_text: str) -> tuple[str, str] | None:
    """(month, block) of the most recent lessons block in the handoff, or
    None. A block runs from its header to the next header (or EOF)."""
    matches = list(LESSON_HEADER_RE.finditer(handoff_text))
    if not matches:
        return None
    last = matches[-1]
    end = matches[-1].end()
    nxt = LESSON_HEADER_RE.search(handoff_text, end)
    block = handoff_text[last.start(): nxt.start() if nxt
                         else len(handoff_text)].rstrip()
    return last.group(1), block


def append_lessons(text: str, month: str, handoff_path: Path) -> int:
    """Reflexion step-4 writeback: append this month's lesson block to
    state/handoff.md. APPEND-ONLY by construction — existing bytes are never
    rewritten (the handoff is history, not a scratchpad); one block per
    month (same-month re-append is refused: return 2).

    gen2 item 4 contract (Reflexion prompts.py:113 port, plan-form): every
    lesson must be an ACTIONABLE PLAN — 「下次 X 触发时做 Y」, never a bare
    event description — and the block must carry >=1 `event:` line in the
    four-op verdict taxonomy (ADD / UPDATE[supersedes] / DELETE[voids] /
    NONE, mem0 Apache-2.0 protocol-only) plus `evidence:` path references.
    A body with zero event: lines breaks the aggregate-view semantics and is
    refused (return 3) so the FIRST block ever written already carries the
    right contract (落差缺口 4)."""
    if not MONTH_RE.match(month):
        raise ValueError(f"bad month '{month}' (want YYYY-MM)")
    try:
        datetime.strptime(month, "%Y-%m")
    except ValueError as exc:
        raise ValueError(f"bad month '{month}' (not a real year-month)") from exc
    body = text.strip("\n")
    if not body.strip():
        raise ValueError("lesson text is empty")
    if not _parse_lesson_entries(body):
        print("refuse: no `event:` line in the lesson text — every entry "
              "needs an ADD/UPDATE/DELETE/NONE verdict line (plan-form "
              "「下次 X 触发时做 Y」 + evidence: path refs; docs/"
              "ops-local-refresh.md §lessons 块格式)",
              file=sys.stderr)
        return 3
    existing = (handoff_path.read_text(encoding="utf-8")
                if handoff_path.exists() else "")
    for m in LESSON_HEADER_RE.finditer(existing):
        if m.group(1) == month:
            print(f"refuse: handoff already carries a lessons block for "
                  f"{month} — revise next month or amend by hand",
                  file=sys.stderr)
            return 2
    header = (f"<!-- monthly-reflexion-lessons month={month} "
              "source=scripts/monthly_review.py --append-lessons-from "
              "(Reflexion protocol borrowed from noahshinn/reflexion, MIT: "
              "attempt, score vs prereg standard, textual lesson, inject "
              "next cycle; protocol-only, no dependency) "
              "contract=计划形「下次 X 触发时做 Y」非事件描述; event: "
              "ADD|UPDATE(supersedes month=YYYY-MM#n)|DELETE(voids "
              "month=YYYY-MM#n)|NONE; evidence: 路径引用 -->")
    with handoff_path.open("a", encoding="utf-8") as fh:
        if existing and not existing.endswith("\n"):
            fh.write("\n")
        fh.write(f"{header}\n{body.rstrip()}\n")
    return 0


# Round 131-续 (pre-enum, audit finding ③ angle-① final step): the question
# text carries a FIXED option set and the answer convention is label-only
# (A|B|C) — the「预先枚举+只回选项+置信度」protocol is now complete. Same
# shape as GLM's official structured-output sentiment example (three-choice
# enum + 0-1 confidence — see docs/ops-local-refresh.md「判别层/生成层分层」
# GLM json_object note, provider 池内唯一一手同形支撑) and the lessons
# event: four-choice contract (EVENT_OP_RE). parse_bounded_answer stays
# deliberately enum-agnostic: an answer outside {A,B,C} still parses and is
# recorded honestly (presentation-side tagging only); the format-miss
# fallback is unchanged. String-constant-level change, zero new call
# surface — still the existing bounded question inside the single
# month-end 23:35 session.
WATCHDOG_BOUNDED_QUESTION = (
    "spin/persistent 是否原地打转或偏离值班目标？（月末会话回答，勿展开成新会话；"
    "固定选项集 A=原地打转 / B=偏离值班目标 / C=正常——answer 只回选项标签"
    " A|B|C，不得自由文本；回答格式=单行 JSON {\"answer\": \"A\"|\"B\"|\"C\", "
    "\"p\": 0到1之间的置信度}"
    "——Jev/System One 校准概率协议的运维层同构，round 131；p 是口头置信度仅记录"
    "轨迹，禁统计显著性声称，禁再校准拟合；输出约十 token 量级）")


def parse_bounded_answer(text: str) -> dict:
    """Round 131 ({answer, p} contract): parse the month-end session's
    bounded-question reply — the FIRST JSON object carrying both keys. Zero
    LLM, pure validation; anything unparsable or out of range degrades to
    an honest format-miss marker (the plain-text reply stays on record,
    nothing is invented). p is recorded as spoken confidence only."""
    import re as _re
    for m in _re.finditer(r"\{[^{}]*\}", text or ""):
        try:
            obj = json.loads(m.group(0))
        except ValueError:
            continue
        if not isinstance(obj, dict) or "answer" not in obj or "p" not in obj:
            continue
        try:
            p = float(obj["p"])
        except (TypeError, ValueError):
            return {"ok": False, "reason": "p-not-numeric",
                    "raw": text[:120]}
        if not (0.0 <= p <= 1.0):
            return {"ok": False, "reason": "p-out-of-range",
                    "raw": text[:120]}
        return {"ok": True, "answer": obj["answer"], "p": p}
    return {"ok": False, "reason": "format-miss", "raw": (text or "")[:120]}


def lesson_seeds(month: str, repo: Path, errors: list[str],
                 now_month: str | None = None) -> dict:
    """Deterministic month-end incident facts (no LLM): the Reflexion
    'score the attempt' step reads these, never guesses. Failed evenings
    surface as weekday-misses (a hard-fail evening writes no SUMMARY — the
    existing missing-weekday enumeration is the failure signal). gen2 item 4
    adds the Watchdog's model-judgment half as a BOUNDED question key — one
    line, answered by the month-end session, zero new sessions. Ring 1b
    (round 137, design report §2) adds calibration_feedback: the ring-1a
    aggregator lines over state/backlog.md prediction records, injected as
    fact statistics only (see CALIBRATION_FEEDBACK_NOTE — never disposition
    semantics). iterate round 11 adds focus_feedback: the single worst
    bucket (max |桶均 p − 桶命中率|, n>=1) as ONE facts-only line from the
    same records (see _focus_feedback_summary). Round 12
    (overdue-outcome-watch) adds overdue_outcome_count: facts-only count of
    prediction cards past due with no outcome yet (todo_or_die 呈报不阻断;
    the engine never records an outcome — see overdue_outcome_records)."""
    days, push_only = collect_log_days(repo, month, errors)
    persistent = [(d["date"], d["persistent_soft_fails"]) for d in days
                  if d["persistent_soft_fails"]]
    spin, scanned = spin_detection(repo)
    backlog_file = repo / BACKLOG_PATH
    backlog_text = (backlog_file.read_text(encoding="utf-8",
                                           errors="replace")
                    if backlog_file.is_file() else "")
    pred_records = _collect_prediction_records(backlog_text)
    calibration = calibration_bucket_summary(pred_records)
    resolved_rows = sum(1 for r in pred_records
                        if r["p"] is not None and r["y"] is not None)
    overdue_outcomes = overdue_outcome_records(
        pred_records, now_month or datetime.now().strftime("%Y-%m"))
    snap_file = repo / "state" / "calibration-months.md"
    snap_text = (snap_file.read_text(encoding="utf-8", errors="replace")
                 if snap_file.is_file() else "")
    return {"month": month, "days_with_summary": len(days),
            "persistent_soft_fails": persistent,
            "missing_weekdays": missing_weekdays(
                month, {d["date"] for d in days}),
            "spin_findings": spin, "push_only": push_only,
            "watchdog_bounded_question": WATCHDOG_BOUNDED_QUESTION,
            "calibration_feedback": calibration,
            "focus_feedback": _focus_feedback_summary(pred_records),
            "resolved_prediction_rows": resolved_rows,
            "resolved_ids": sorted(_resolved_row_ids(pred_records, month)),
            "overdue_outcome_count": len(overdue_outcomes),
            "calibration_snapshot_line": calibration_month_snapshot(
                pred_records, month),
            "calibration_evolution": calibration_evolution_lines(
                pred_records, snap_text, month)}


# Ring 1b injection discipline (design report §2): the calibration feedback
# block may carry FACT STATISTICS ONLY. This fixed reminder is the standing
# restatement of red lines 3/4/5 — a prohibition, never disposition advice;
# threshold/disposition semantics live in the code rule gate, NEVER in any
# LLM prompt (same contract as the three-band gate docstring above).
CALIBRATION_FEEDBACK_NOTE = ("呈现≠校准：以上仅记录性事实统计，CI 宽即小样本——"
                             "禁据此调 p 或定阈值（阈值与处置语义只在代码侧"
                             "规则门，NEVER in any LLM prompt）")

# Ring 2 (ExpeL-style zero-gradient experience distillation, design report
# §2; arXiv:2308.10144 — protocol only, no Faiss / environment-training
# code): the month-end session distills 0-2 IF-THEN policy fragments from
# the resolved reconciliation rows + active lessons and writes them back
# through the EXISTING --append-lessons-from channel (append_lessons
# contract gate + EVENT_OP_RE four ops) — zero new sessions. Fragments
# express discipline, NEVER auto-adjust-p instructions (judgments/facts
# split stands, red line 4).
INSIGHT_HINT = ("月末会话请从本月 resolved 对账行 + active lessons 聚合抽 0-2 条 "
                "IF-THEN policy 片段（经 --append-lessons-from 写回）；"
                "片段禁含『自动调 p』指令（示例口径：IF 高带预测（p>0.8 表达）"
                "THEN 须附可证伪依据——表达纪律，非调 p）。envelope 契约（"
                "iterate 轮 14 质量门）：每条片段 head 行含 `hook=<可证伪依据>` "
                "与 `ref=<YYYY-MM#n>`（n=本月对账行 [YYYY-MM#n] id 前缀）+正文 "
                "IF-THEN 句式；代码侧 insight_quality_verdict 确定性判定"
                "（hook-miss/bad-ref/retire-restatement 三判据，零 LLM 零嵌入"
                "——RLSVR arXiv:2607.23802『任务变换→可验证判据』协议映射，"
                "backlog 延伸索引㉝），不合规条目由 quality-miss 行呈报拒入本月"
                "蒸馏候选池（§6 档案呈现零回改，append-only）。双路径裁决（Memp "
                "全生命周期映射+Memory-R1 outcome 门控，iterate 轮 14 框架③）："
                "新教训=event: ADD+信封；新 outcome 证据指向既有片段=UPDATE"
                "[supersedes month=M#n]（修正接替）或 DELETE[voids month=M#n]"
                "（退役）——UPDATE/DELETE 须附 outcome ref= 且目标 id 真实存在"
                "（伪 id=quality-miss）；无证据变化=event: NONE（重复已录不重写"
                "，NOOP≡NONE）")


def render_reflexion_section(seeds: dict,
                             prior: tuple[str, list[str]] | None,
                             errors: list[str]) -> str:
    out = ["## 5. Reflexion seeds (round 126 — month-end lesson candidates; "
           "facts only, the lesson PROSE is the month-end session's job)", ""]
    out.append(f"- evenings with a SUMMARY: {seeds['days_with_summary']}")
    out.append(f"- weekday evenings without a SUMMARY (includes hard-fail "
               f"evenings — each needs a human reason): "
               f"{seeds['missing_weekdays'] or 'none'}")
    out.append(f"- persistent soft-fails: "
               f"{seeds['persistent_soft_fails'] or 'none'}")
    out.append(f"- spin findings: {seeds['spin_findings'] or 'none'}")
    out.append(f"- push_only_recovery events: {seeds['push_only']}")
    out.append(f"- watchdog bounded question: "
               f"{seeds.get('watchdog_bounded_question') or '—'} "
               f"(本月 spin {len(seeds['spin_findings'])} 条 / persistent "
               f"晚 {len(seeds['persistent_soft_fails'])})")
    out.append("  - 回答请落单行 JSON（{answer, p} 契约，round 131）；不合法"
               "回答由 parse_bounded_answer 判 format-miss 原文保留——不补猜")
    out.append("- 校准事实（呈现≠校准——环 1b 注入，facts only）:")
    for ln in seeds["calibration_feedback"]:
        out.append(f"  - {ln}")
    out.append(f"  - {CALIBRATION_FEEDBACK_NOTE}")
    out.append("- 跨月校准演进（两窗口 facts-only；Hindsight ㉕ facts/beliefs 分离"
               "——p=演化中信念轨迹、outcome=事实）：")
    for ln in seeds["calibration_evolution"]:
        out.append(f"  - {ln}")
    if seeds.get("calibration_snapshot_line"):
        out.append("  - 本月快照行（月末会话人工 append 入 "
                   "state/calibration-months.md——呈报-入册分离，引擎不写 "
                   "state/ 档案，与 backlog 卡区人工维护同模式）:")
        out.append(f"    {seeds['calibration_snapshot_line']}")
    out.append(f"  - {EVOLUTION_SCOPE_NOTE}")
    dedup = feedback_dedup_verdict(
        seeds["focus_feedback"], prior[1] if prior else None)
    if dedup:
        out.append("- 重点反哺行（同桶去重命中——降级为**刷新提示**，feedback-"
                   "dedup 契约：同桶区间 key 已有 active 教训，旧条 append-only "
                   "不删不改[mem0 无等价才 ADD 的确定性半边+A-MEM 更新优于追加]）:")
        for ln in dedup:
            out.append(f"  - 已有教训：{ln}")
        out.append(f"  - {seeds['focus_feedback']}（本月事实仍呈现；写回按 "
                   "event: NONE[重复已录]/UPDATE 定档——写入方裁决，零 LLM 零"
                   "嵌入判重）")
    else:
        out.append("- 重点反哺行（最歪桶=|桶均 p−桶命中率| 最大且 n≥1，环 1b 深化，"
                   "facts only）:")
        out.append(f"  - {seeds['focus_feedback']}")
    if seeds.get("overdue_outcome_count"):
        out.append(f"- 逾期提示（facts only，todo_or_die 呈报不阻断——引擎只读"
                   f"不代记 outcome）: 本月有 {seeds['overdue_outcome_count']} 张"
                   "预测卡逾期未记 outcome（due 已过、y 未记；人补记，"
                   "2611.03928 零查询预算口径——outcome 只随月末真实数据到）")
    if seeds["resolved_prediction_rows"] and not dedup:
        out.append(f"  - {FOCUS_FEEDBACK_BUDGET_NOTE}")
    if seeds["resolved_prediction_rows"]:
        out.append(f"- insight 钩子（环 2·蒸馏）: {INSIGHT_HINT}")
    else:
        out.append("- insight 钩子（环 2·蒸馏）: 本月无 resolved 对账行，"
                   "insight 步跳过")
    insight_quality = seeds.get("insight_quality") or []
    if insight_quality:
        out.append("- insight 质量门（蒸馏前确定性判定，hook-miss/bad-ref/"
                   "retire-restatement 三判据 first-miss，零 LLM 零嵌入"
                   "——RLSVR ㉝ 任务变换→可验证判据；quality-miss 理由行"
                   "不占 INSIGHT 0-2 条额度，§6 档案呈现零回改）:")
        for ln in insight_quality:
            out.append(f"  - {ln}")
    if errors:
        out.append(f"- collection anomalies: {errors}")
    out += ["", "## 6. Active lessons carried from state/handoff.md "
               "(聚合视图=最新块+未被 supersede/void 的历史条目，gen2 条目 4；"
               "the 'inject into next cycle' leg — sessions read the handoff "
               "first per AGENTS.md)", ""]
    if prior:
        out.append(f"Latest block month={prior[0]}; active entries "
                   f"{len(prior[1])}:")
        out.append("")
        out.append("```")
        out += prior[1]
        out.append("```")
    else:
        out.append("- none yet (no monthly-reflexion-lessons block in the "
                   "handoff)")
    out += ["", f"- {LESSONS_CONTRACT_NOTE}"]
    out.append(f"- {LESSON_LIFECYCLE_NOTE}")
    out.append("")
    return "\n".join(out)


# ----------------------------------------------------------------------- main

def _month_type(text: str) -> str:
    if not MONTH_RE.match(text):
        raise argparse.ArgumentTypeError(f"bad --month '{text}' (want YYYY-MM)")
    try:
        datetime.strptime(text, "%Y-%m")
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"bad --month '{text}' (not a real "
                                         "year-month)") from exc
    return text


def run_verify_bounded(text: str, source: str) -> tuple[str, int]:
    """Round 136-续 (bounded-answer-wiring, iterate 轮 8): verify the
    bounded-answer line(s)
    in `text` via parse_bounded_answer — zero LLM, zero network, pure
    validation, read-only. An answer-shaped line = carries both key
    literals '"answer"' and '"p"' (same shape the WATCHDOG question
    prescribes). No such line anywhere -> honest 'none yet' (exit 0, not
    an alarm: the first month has no prior block to verify). Otherwise
    each hit is parsed per line: raw misses stay on record verbatim,
    nothing is invented; exit 1 if any hit fails (ok / format-miss /
    p-not-numeric / p-out-of-range). p stays spoken confidence only —
    no recalibration fitting (in-册 #15 口径)."""
    lines = text.splitlines()
    out = ["## bounded-answer 验证（--verify-bounded；零 LLM 零网络，纯校验）",
           f"- 输入：{source}（{len(lines)} 行）"]
    hits = 0
    code = 0
    for i, ln in enumerate(lines, 1):
        if '"answer"' not in ln or '"p"' not in ln:
            continue
        hits += 1
        verdict = parse_bounded_answer(ln)
        if verdict["ok"]:
            out.append(f"- L{i}: **ok** —— answer={verdict['answer']!r} "
                       f"p={verdict['p']}（口头置信度，仅记录轨迹）")
        else:
            label = {"format-miss": "format-miss（原文留档，未虚构）",
                     "p-not-numeric": "p-not-numeric（p 非数值）",
                     "p-out-of-range": "p-out-of-range（p 越界 [0,1]）"
                     }.get(verdict["reason"], verdict["reason"])
            out.append(f"- L{i}: **{label}** —— raw: {verdict.get('raw', '')}")
            code = 1
    if not hits:
        out.append("- **none yet** —— 输入无含 \\{\"answer\",\"p\"\\} 双键的 "
                   "bounded answer 行（上月块未写/未含答案），如实呈现、"
                   "不误报、不算失败。")
    else:
        out.append(f"- 候选行 {hits}，逐行判定如上（parse_bounded_answer "
                   "首个双键 JSON 契约，line 级呈现）。")
    return "\n".join(out) + "\n", code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--month", type=_month_type, default=None,
                        help="month to review, YYYY-MM (default: last month)")
    parser.add_argument("--out", default=None,
                        help="write the markdown here (default: stdout)")
    parser.add_argument("--repo", default=None,
                        help="repo root (default: this script's parent dir)")
    parser.add_argument("--weekly", action="store_true",
                        help="Watchdog external-audit mode (round 126): "
                             "7-workflow health with billing-lock triage + "
                             "ledger config_committed-before-result "
                             "spot-check + spin detection + proposal-closure "
                             "reconciliation; exit 1 on findings. Read-only, "
                             "zero Actions dependency. Default anchoring: also "
                             "writes runs/ops_local_refresh/<today>/"
                             "weekly_watchdog.md (gen2 item 3; --out replaces "
                             "the anchor).")
    parser.add_argument("--propose", action="store_true",
                        help="deterministic proposal engine (gen2 item 3): "
                             "existing signals x rule table -> S/M/L proposal "
                             "cards with evidence pointers + prop: dedup keys "
                             "(thread: IDs where mapped); zero LLM, zero "
                             "network; READ-ONLY on state/backlog.md and "
                             "tasks/ (in-flight keys degrade to refresh "
                             "instructions). Output: stdout or --out.")
    parser.add_argument("--lessons", action="store_true",
                        help="with the monthly flow: add Reflexion lesson "
                             "seeds + the ACTIVE lessons aggregate carried "
                             "from state/handoff.md (round 126 + gen2 item "
                             "4). Month-end session guidance: 写块遵循契约 "
                             "—— 每条 event: 四操作（ADD/UPDATE[supersedes]/"
                             "DELETE[voids]/NONE）+ 计划形「下次 X 触发时做 "
                             "Y」+ evidence: 路径引用（runbook §lessons 块格式）")
    parser.add_argument("--append-lessons-from", default=None, metavar="FILE",
                        help="append the lesson text in FILE to "
                             "state/handoff.md as this month's "
                             "monthly-reflexion-lessons block (append-only, "
                             "one block per month; exit 2 on duplicate, "
                             "exit 3 when no event: line — contract gate)")
    parser.add_argument("--verify-bounded", default=None, metavar="FILE",
                        help="verify the bounded-answer line(s) in FILE "
                             "(or '-' for stdin) — e.g. last month's "
                             "monthly-reflexion-lessons block excerpt — "
                             "through parse_bounded_answer: per-line "
                             "ok / format-miss / p-not-numeric / "
                             "p-out-of-range, raw preserved verbatim; "
                             "no answer-shaped line -> honest 'none yet' "
                             "(exit 0, not an alarm). Zero LLM, zero "
                             "network, read-only; exit 1 on any failed "
                             "line.")
    args = parser.parse_args(argv)
    try:  # keep CJK (未能核对) intact even on a legacy GBK console
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except (AttributeError, OSError):
        pass
    repo = Path(args.repo).resolve() if args.repo else ROOT
    month = args.month or default_month()
    if args.weekly:
        markdown, code = run_weekly(repo)
        if args.out:
            out_path = Path(args.out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(markdown, encoding="utf-8")
            print(f"wrote {out_path}", file=sys.stderr)
        else:
            print(markdown, end="")
            # gen2 item 3: the default on-disk anchor (audit trail + the
            # --propose R5 signal source). Best-effort like night_package.
            anchor = (repo / LOG_SUBDIR
                      / datetime.now().strftime("%Y-%m-%d")
                      / WEEKLY_ANCHOR_NAME)
            try:
                anchor.parent.mkdir(parents=True, exist_ok=True)
                anchor.write_text(markdown, encoding="utf-8")
                print(f"anchored {anchor}", file=sys.stderr)
            except OSError as exc:
                print(f"anchor write failed ({exc}): {anchor}",
                      file=sys.stderr)
        return code
    if args.propose:
        # The month-end carrier: cards for the month now ENDING (--month
        # overrides; unlike the review, propose looks at the current month).
        propose_month = args.month or datetime.now().strftime("%Y-%m")
        markdown, n_cards = run_propose(repo, month=propose_month)
        if args.out:
            out_path = Path(args.out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(markdown, encoding="utf-8")
            print(f"wrote {out_path}", file=sys.stderr)
        else:
            print(markdown, end="")
        return 0
    if args.append_lessons_from:
        text = Path(args.append_lessons_from).read_text(encoding="utf-8")
        return append_lessons(text, month,
                              repo / "state" / "handoff.md")
    if args.verify_bounded is not None:
        if args.verify_bounded == "-":
            text, source = sys.stdin.read(), "stdin(-)"
        else:
            path = Path(args.verify_bounded)
            text = path.read_text(encoding="utf-8", errors="replace")
            source = str(path)
        markdown, code = run_verify_bounded(text, source)
        if args.out:
            out_path = Path(args.out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(markdown, encoding="utf-8")
            print(f"wrote {out_path}", file=sys.stderr)
        else:
            print(markdown, end="")
        return code
    errors: list[str] = []
    days, push_only = collect_log_days(repo, month, errors)
    gh = {wf: collect_gh(wf, month, repo) for wf in GH_WORKFLOWS}
    health = collect_health(repo, errors)
    markdown = render(month, days, push_only, gh, health, errors,
                      datetime.now().isoformat(timespec="seconds"))
    if args.lessons:
        seeds = lesson_seeds(month, repo, errors)
        handoff_text = ((repo / "state" / "handoff.md")
                        .read_text(encoding="utf-8")
                        if (repo / "state" / "handoff.md").exists() else "")
        prior = active_lessons_view(handoff_text)
        # round 14 insight-quality-gate: the verdict layer is HERE (the
        # layer already holding the handoff text) — zero NEW file reads;
        # resolved ids ride the seeds (one parser, N consumers).
        seeds["insight_quality"] = insight_quality_report(
            handoff_text, month, seeds.get("resolved_ids") or ())
        markdown += "\n" + render_reflexion_section(seeds, prior, [])
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(markdown, encoding="utf-8")
        print(f"wrote {out_path}", file=sys.stderr)
    else:
        print(markdown, end="")
    return 0 if (days and not errors) else 1


# iterate round 11 — focus-feedback-selector (training-method ring-1b
# deepening, design report §2). Placed at the file tail per the round-139
# zero-drift placement precedent: every in-repo anchor above this block
# keeps its position except for the small interior deltas inside
# lesson_seeds / render_reflexion_section. The WORST calibration bucket
# (max |bucket-mean p − bucket hit rate|; n>=1 by construction — empty
# buckets are never candidates) is lifted into lesson_seeds as ONE
# facts-only line: bucket range / n / mean p / hit rate / deviation
# direction. Rule anchor: arXiv:2611.14465 (One Curve — the Murphy
# reliability term is exactly bucket-level |mean p − hit rate|
# information). Injection-budget anchor: LIMBO arXiv:2609.14138 (replay
# is not free — injection needs an explicit budget; the line rides and
# consumes 1 of the INSIGHT 0-2 fragment slots, runbook 步 6 同口径).
# CALIBRATION_FEEDBACK_NOTE discipline applies verbatim: FACT STATISTICS
# ONLY, never disposition (no adjust-p, no threshold advice).
FOCUS_FEEDBACK_BUDGET_NOTE = ("预算注记：本反哺行占上面 INSIGHT 0-2 条额度中 1 条"
                              "（LIMBO arXiv:2609.14138 口径锚——回放非免费，"
                              "注入须显式预算，不无限倾倒）")


def _focus_feedback_summary(records: list[dict]) -> str:
    """iterate round 11 (focus-feedback-selector): the single most-skewed
    calibration bucket as ONE facts-only line, recomputed from the SAME
    _collect_prediction_records output the bucket summary reads (one
    parser, N consumers — never a re-parse of rendered text). Bucket
    semantics mirror calibration_bucket_summary exactly (fixed
    presentation cuts, resolved p>=0.5 only, top bucket closed at 1.0);
    ties break to the LOWEST band (deterministic seeds). Zero populated
    buckets -> the honest baseline default, no fabricated bucket."""
    resolved = [r for r in records
                if r["p"] is not None and r["y"] is not None]
    bucketed = [r for r in resolved if r["p"] >= _CALIBRATION_BAND_CUTS[0]]
    n_bands = len(_CALIBRATION_BAND_CUTS) - 1
    worst: tuple[float, str] | None = None
    for i in range(n_bands):
        lo = _CALIBRATION_BAND_CUTS[i]
        hi = _CALIBRATION_BAND_CUTS[i + 1]
        last = i == n_bands - 1
        rows = [r for r in bucketed
                if lo <= r["p"] < hi or (last and r["p"] == hi)]
        if not rows:  # n>=1 constraint: empty buckets are never candidates
            continue
        mean_p = sum(r["p"] for r in rows) / len(rows)
        hit_rate = sum(1 for r in rows if r["y"] == 1) / len(rows)
        skew = abs(mean_p - hit_rate)
        if worst is None or skew > worst[0]:
            close = "]" if last else ")"
            direction = ("高估方向——桶均 p 高于命中率" if mean_p > hit_rate
                         else "低估方向——桶均 p 低于命中率" if mean_p < hit_rate
                         else "零偏差")
            worst = (skew,
                     f"最歪桶 p∈[{lo:.1f},{hi:.1f}{close}: n={len(rows)}、"
                     f"桶均 p={mean_p:.3f}、命中率 {hit_rate:.3f}、"
                     f"|偏差|={skew:.3f}（{direction}）")
    if worst is None:
        return "none yet（基线收集月——无 resolved 对账行可入桶，不造最歪桶）"
    return worst[1]


# iterate round 12 (feedback-dedup-contract) — the dedup key is the LITERAL
# bucket-interval string rendered by _focus_feedback_summary (fixed
# presentation cuts, zero LLM / zero embeddings — deterministic substring
# match, nothing semantic, nothing fitted).
_FOCUS_BUCKET_RE = re.compile(r"p∈\[(\d\.\d),(\d\.\d)[)\]]")


def feedback_dedup_verdict(focus_line: str,
                           active_lines: list[str] | None) -> list[str] | None:
    """iterate round 12 (feedback-dedup-contract): deterministic same-bucket
    pre-check of the focus-feedback line against the active-lessons entries.
    Semantics anchors — Hindsight pre-write filtering (same-bucket key ONLY:
    entries from other buckets / other lesson classes can NEVER be judged
    duplicates, which protects cross-month time-dimension records from
    mutual deletion; no-change → no-op saves budget), mem0 Algorithm 1
    'no semantic equivalent → ADD' (arXiv:2504.19413 — the deterministic
    half only), A-MEM update-over-append (arXiv:2502.12110). ZERO LLM, ZERO
    embeddings: the dedup key is the literal bucket-interval string (e.g.
    'p∈[0.8,0.9)') matched as a substring against each active entry line.
    A hit DOWNGRADES this month's focus line to a 'refresh reminder'
    carrying the owning [month#idx] references — the old lesson is never
    edited or retired by this check (append-only, reference-style marks
    only). The mem0 information-content promotion gate is NOT implemented
    (citation anchor only — owner-gated, same boundary as LatentGym A/B).
    Returns the matching entry lines, [] when nothing hits (keep the new
    line), or None when there is no bucket key to check (baseline month)
    or no active lessons — both honest no-dedup defaults."""
    m = _FOCUS_BUCKET_RE.search(focus_line or "")
    if m is None or not active_lines:
        return None
    key = m.group(0)
    return [ln for ln in active_lines if key in ln]


# iterate round 14 (insight-quality-gate, framework ①; design spec
# reports/audits/2026-11-15-iterate-round-14.md §4 — this block is the
# post-close implementation). RLSVR protocol mapping (arXiv:2607.23802,
# backlog 延伸索引㉝): task transformation -> deterministic verifiable
# criteria attached to open-ended output BEFORE consumption. Three
# deterministic criteria, first-miss stops; ZERO LLM, ZERO embeddings, ZERO
# I/O (pure inputs, same contract family as feedback_dedup_verdict above).
# The gate filters the month's distillation candidate POOL only — the §6
# archive presentation is never edited by it (append-only stands; a
# quality-miss line reports, it never deletes). Reference anchors:
# promptfoo (MIT, 27154★) deterministic-assertion layering = criteria table
# + reason vocabulary + one parser N consumers; AgentEvolver (Apache-2.0,
# 1592★) self-attributing = the miss line names the failed criterion + the
# ref — protocol anchors ONLY, the Node tooling is NOT installed (zero new
# dependencies; repo has no package.json touch).
_INSIGHT_ENTRY_RE = re.compile(r"^\s*[-*]\s*event:\s*ADD\b.*\binsight\b")
_INSIGHT_HOOK_RE = re.compile(r"\bhook=(\S[^；;|]*)")
_INSIGHT_REF_RE = re.compile(r"\bref=(\d{4}-\d{2})#(\d+)")


def _normalize_ws(text: str) -> str:
    """Whitespace-normalized literal form for substring comparison — the
    ONLY normalization the retire-restatement criterion applies (zero
    embeddings, nothing semantic)."""
    return " ".join((text or "").split())


def _resolved_row_id_seq(records: list[dict],
                         review_month: str) -> list[str]:
    """THE id assigner for resolved reconciliation rows (one parser, N
    consumers): p AND y both present -> file-order 1-based id
    `YYYY-MM#1..k` under the review month. reconcile_predictions renders
    the same ids as `[YYYY-MM#n]` row prefixes (round 14, referencable
    rows); _resolved_row_ids is the set form the insight gate checks
    against — one implementation, zero drift between row ids and the
    gate's id space."""
    out: list[str] = []
    k = 0
    for r in records:
        if r["p"] is not None and r["y"] is not None:
            k += 1
            out.append(f"{review_month}#{k}")
    return out


def _resolved_row_ids(records: list[dict], review_month: str) -> set[str]:
    """Set form of _resolved_row_id_seq (design §4.1 resolved_ids — the
    bad-ref criterion's membership universe)."""
    return set(_resolved_row_id_seq(records, review_month))


def _insight_retired_texts(handoff_text: str) -> list[str]:
    """Normalized full texts of RETIRED lesson entries — the same
    reference-mark scan as active_lessons_view (UPDATE/DELETE entries
    naming month#n via EVENT_REF_RE), mapped to the referenced entries'
    normalized (head+body) text. Comparison targets the RETIRED segment
    only: restating an ACTIVE entry is feedback_dedup_verdict's same-bucket
    jurisdiction — the two gates are orthogonal by design."""
    blocks = _lessons_blocks(handoff_text)
    entries: dict[tuple[str, int], list[str]] = {}
    retired: set[tuple[str, int]] = set()
    for month, block in blocks:
        for idx, entry in enumerate(_parse_lesson_entries(block), 1):
            entries[(month, idx)] = entry["lines"]
            ref = EVENT_REF_RE.search(" ".join(entry["lines"]))
            if entry["op"] in ("UPDATE", "DELETE") and ref:
                retired.add((ref.group(2), int(ref.group(3))))
    return [_normalize_ws("\n".join(entries[pair]))
            for pair in sorted(retired) if pair in entries]


def insight_quality_verdict(head_line: str, body_lines: list[str],
                            review_month: str, resolved_ids: set[str],
                            retired_texts: list[str]) -> dict:
    """iterate round 14 (insight-quality-gate): deterministic three-criteria
    verdict over ONE insight candidate entry — first-miss stops. Pure
    function: every input is passed in by the caller (zero file reads, zero
    network, zero embeddings — feedback_dedup_verdict contract); the verdict
    dict shape follows parse_bounded_answer (ok/reason/raw, plus the
    pass-side ref). Criteria in order:
    1. hook-miss — no/empty `hook=` token on the head line, or no IF..THEN
       skeleton in the body (keyword-structure check: the minimal
       deterministic proxy for a falsifiable hook being present; the engine
       never judges semantic truth of the claim itself);
    2. bad-ref — missing `ref=`, a month other than the review month
       (STRICTLY current-month: cross-month references never resolve — same
       boundary discipline as the dedup same-key rule, 宁严勿宽), or a
       pseudo id not in resolved_ids;
    3. retire-restatement — the whitespace-normalized full entry text
       CONTAINS any normalized retired entry's full text (literal substring
       comparison, zero embeddings; the retirement segment, not the active
       segment).
    All three pass -> {"ok": True, "ref": "<month#n>"}."""
    head = head_line or ""
    body = "\n".join(body_lines or [])
    m = _INSIGHT_HOOK_RE.search(head)
    if m is None or not m.group(1).strip() or not re.search(
            r"\bIF\b[\s\S]*\bTHEN\b", body):
        return {"ok": False, "reason": "hook-miss", "raw": head[:120]}
    rm = _INSIGHT_REF_RE.search(head)
    if (rm is None or rm.group(1) != review_month
            or f"{rm.group(1)}#{rm.group(2)}" not in resolved_ids):
        return {"ok": False, "reason": "bad-ref", "raw": head[:120]}
    whole = _normalize_ws(f"{head}\n{body}")
    if any(t and t in whole for t in retired_texts):
        return {"ok": False, "reason": "retire-restatement",
                "raw": head[:120]}
    return {"ok": True, "ref": f"{rm.group(1)}#{rm.group(2)}"}


def insight_lifecycle_verdict(entry_lines: list[str],
                              known_ids: set[tuple[str, int]]) -> dict:
    """Round 14 §6.2 (memp-insight-lifecycle): the lifecycle gate for
    UPDATE/DELETE marks written in the review-month block(s) — the
    deprecate×supersedes closed loop's write-side validation. Reuses the
    in-register scanners (EVENT_REF_RE for the supersedes/voids target,
    _INSIGHT_REF_RE for the outcome-evidence token); ZERO new reason
    vocabulary: a missing/invalid target id or a missing outcome ref=
    token both degrade to bad-ref (the semantic split lives HERE in the
    docstring, the four-state word table stands untouched — 轮 128-续
    EVENT_OP_RE semantics unchanged, this gate only VALIDATES marks)."""
    head = (entry_lines or [""])[0]
    mark = EVENT_REF_RE.search(" ".join(entry_lines or []))
    outcome_ref = _INSIGHT_REF_RE.search(head)
    if (mark is None or outcome_ref is None
            or (mark.group(2), int(mark.group(3))) not in known_ids):
        return {"ok": False, "reason": "bad-ref", "raw": head[:120]}
    return {"ok": True, "ref": f"{mark.group(2)}#{mark.group(3)}"}


def insight_quality_report(handoff_text: str, review_month: str,
                           resolved_ids) -> list[str]:
    """Presentation lines for the month's insight quality gate (the render
    §5 block): every `event: ADD ... insight` candidate in the
    review-month lessons block(s) gets ONE line — pass:
    `[month#idx] 合格 insight`; miss: `insight quality-miss[<reason>]
    [month#idx]: <head 原文截断>（拒入本月蒸馏候选池）`. A miss line does
    NOT claim an INSIGHT 0-2 budget slot (same degradation precedent as
    the round-145 refresh reminder — the budget note stays attached to the
    focus line only). Zero candidates -> [] (honest absence: nothing
    renders, zero noise). The §6 archive view is NOT touched by this
    report (engine never writes the handoff; append-only presentation
    stands). Round 14 §6.2 extends the same report to UPDATE/DELETE marks
    in the review-month block(s) (the lifecycle gate: target id must
    exist + outcome ref= present — reuse of bad-ref, zero new reason
    words); a PASSING lifecycle mark renders nothing (zero noise — the
    mark is already consumed by the archive's retire set)."""
    ids = set(resolved_ids or ())
    retired = _insight_retired_texts(handoff_text)
    known_ids: set[tuple[str, int]] = set()
    for month, block in _lessons_blocks(handoff_text):
        for idx in range(1, len(_parse_lesson_entries(block)) + 1):
            known_ids.add((month, idx))
    lines: list[str] = []
    for month, block in _lessons_blocks(handoff_text):
        if month != review_month:
            continue
        for idx, entry in enumerate(_parse_lesson_entries(block), 1):
            head = entry["lines"][0].rstrip()
            ref = f"{month}#{idx}"
            head_txt = head.lstrip().lstrip("-*").strip()
            if entry["op"] in ("UPDATE", "DELETE"):
                verdict = insight_lifecycle_verdict(entry["lines"],
                                                    known_ids)
                if not verdict["ok"]:
                    lines.append(f"insight quality-miss[{verdict['reason']}] "
                                 f"[{ref}]: {head_txt[:80]}"
                                 "（拒入本月蒸馏候选池）")
                continue
            if not _INSIGHT_ENTRY_RE.search(head):
                continue
            verdict = insight_quality_verdict(head, entry["lines"][1:],
                                              review_month, ids, retired)
            if verdict["ok"]:
                lines.append(f"[{ref}] 合格 insight")
            else:
                lines.append(f"insight quality-miss[{verdict['reason']}] "
                             f"[{ref}]: {head_txt[:80]}"
                             "（拒入本月蒸馏候选池）")
    return lines


# iterate round 12 (cross-month-evolution) — month-attribution = the
# reconciliation month (the month the outcome ARRIVES), same family as the
# reconciliation-time discipline. Presentation ONLY: two-window change
# lines, never trend fits, never slope claims, never significance, never an
# auto better/worse gate (Evidently auto-Tests explicitly NOT adopted — the
# only verdict gate is promotion_gate_assessment, compute-only, owner key).
EVOLUTION_SCOPE_NOTE = ("演进边界：仅两窗口变化呈现（方向与幅度）——禁趋势拟合/斜率"
                        "宣称/显著性；不设自动判优/劣门（判定门唯一=promotion gate "
                        "且只算不启用，钥匙在业主；Evidently auto-Tests 自动派生阈值"
                        "明确不采）")


def _bucket_stats(resolved: list[dict]) -> dict[str, tuple[int, float]]:
    """Per-bucket (n, hit rate) over the FIXED presentation cuts — the same
    bucket semantics as calibration_bucket_summary/_focus_feedback_summary
    (resolved p>=0.5 only, top bucket closed at 1.0, literal keys)."""
    bucketed = [r for r in resolved if r["p"] >= _CALIBRATION_BAND_CUTS[0]]
    n_bands = len(_CALIBRATION_BAND_CUTS) - 1
    stats: dict[str, tuple[int, float]] = {}
    for i in range(n_bands):
        lo = _CALIBRATION_BAND_CUTS[i]
        hi = _CALIBRATION_BAND_CUTS[i + 1]
        last = i == n_bands - 1
        rows = [r for r in bucketed
                if lo <= r["p"] < hi or (last and r["p"] == hi)]
        if not rows:
            continue
        key = (f"p∈[{lo:.1f},{hi:.1f}" + ("]" if last else ")"))
        hit = sum(1 for r in rows if r["y"] == 1) / len(rows)
        stats[key] = (len(rows), hit)
    return stats


def calibration_month_snapshot(records: list[dict], month: str) -> str | None:
    """One month's reconciliation snapshot line — facts-only cross-section:
    per-bucket n/hit + Brier + BSS components (the SAME math the gate's X
    axis reads, via _bss_components) + p̄. The month-end session appends this
    line BY HAND into state/calibration-months.md (report/archive separation:
    the engine renders it, it NEVER writes the state/ archive — same human
    gate as the backlog card lane). Zero resolved rows -> None (a baseline
    month archives nothing; runbook「演进视图口径」)."""
    resolved = [r for r in records
                if r["p"] is not None and r["y"] is not None]
    if not resolved:
        return None
    parts = [f"- {month}:"]
    for key, (n, hit) in _bucket_stats(resolved).items():
        parts.append(f"{key}: n={n}、hit {hit:.3f}")
    comp = _bss_components(resolved)
    bs, _, p_bar, bss = comp  # type: ignore[misc]  # resolved non-empty
    tail = (f"BSS={bss:.3f}" if bss is not None
            else f"BSS 无定义（p̄={p_bar:.3f} 退化）")
    parts.append(f"Brier={bs:.3f}、{tail}、p̄={p_bar:.3f}")
    return parts[0] + " " + " | ".join(parts[1:])


_SNAP_BUCKET_RE = re.compile(
    r"(p∈\[\d\.\d,\d\.\d[)\]]): n=(\d+)、hit ([\d.]+)")
_SNAP_TAIL_RE = re.compile(
    r"Brier=([-\d.]+)、BSS=([-\d.]+)、p̄=([\d.]+)")
_SNAP_TAIL_DEGEN_RE = re.compile(
    r"Brier=([-\d.]+)、BSS 无定义（p̄=([\d.]+) 退化）")
_SNAP_MONTH_RE = re.compile(r"^- (\d{4}-\d{2}): ")


def parse_calibration_snapshots(text: str) -> dict[str, dict]:
    """Deterministic parse of state/calibration-months.md snapshot lines
    (the append-only durable archive ADR-006 style). Malformed lines are
    SKIPPED silently-but-visibly (they stay in the file for a human to fix;
    the parser never guesses). Returns {month: {buckets, brier, bss, p_bar}}
    — bss None on the degenerate month."""
    out: dict[str, dict] = {}
    for line in (text or "").splitlines():
        m = _SNAP_MONTH_RE.match(line.strip())
        if m is None:
            continue
        month = m.group(1)
        buckets = {bm.group(1): (int(bm.group(2)), float(bm.group(3)))
                   for bm in _SNAP_BUCKET_RE.finditer(line)}
        tm = _SNAP_TAIL_RE.search(line)
        if tm:
            out[month] = {"buckets": buckets, "brier": float(tm.group(1)),
                          "bss": float(tm.group(2)),
                          "p_bar": float(tm.group(3))}
            continue
        dm = _SNAP_TAIL_DEGEN_RE.search(line)
        if dm:
            out[month] = {"buckets": buckets, "brier": float(dm.group(1)),
                          "bss": None, "p_bar": float(dm.group(2))}
    return out


def calibration_evolution_lines(records: list[dict], snapshots_text: str,
                                month: str) -> list[str]:
    """Three honest states for the cross-month evolution view (Evidently ㉙
    reference-vs-current two-window presentation anchor; Hindsight ㉕
    facts/beliefs split — p is a belief trajectory, outcomes are facts):
    zero resolved -> none yet; no prior archived month -> first month, no
    prior; else change lines (direction AND magnitude rendered as bare
    numbers — 'hit 0.600→0.667 (n 3→6)', BSS likewise; buckets only one
    side has are named as such, never extrapolated). Never a trend fit,
    never a slope claim, never significance — EVOLUTION_SCOPE_NOTE is
    rendered by the caller on every state."""
    resolved = [r for r in records
                if r["p"] is not None and r["y"] is not None]
    if not resolved:
        return ["none yet（基线收集月——零 resolved 对账行，无演进视图）"]
    snaps = parse_calibration_snapshots(snapshots_text)
    prior_months = sorted(m for m in snaps if m < month)
    if not prior_months:
        return ["first month, no prior——本月快照行待入册（runbook「演进视图口径」"
                "步：月末会话人工 append 入 state/calibration-months.md，"
                "呈报-入册分离，引擎不写 state/ 档案）"]
    prior_m = prior_months[-1]
    prior = snaps[prior_m]
    cur = _bucket_stats(resolved)
    lines = [f"上月（{prior_m}）→本月（{month}）两窗口对照（facts-only 变化呈现，"
             "Evidently ㉙ reference-vs-current 范式锚）："]
    for key in sorted(set(prior["buckets"]) | set(cur)):
        if key in prior["buckets"] and key in cur:
            pn, ph = prior["buckets"][key]
            cn, ch = cur[key]
            lines.append(f"{key} 桶命中率 {ph:.3f}→{ch:.3f}（n {pn}→{cn}）")
        elif key in cur:
            cn, ch = cur[key]
            lines.append(f"{key} 桶本月新入（n={cn}、hit {ch:.3f}；上月空桶）")
        else:
            pn, ph = prior["buckets"][key]
            lines.append(f"{key} 桶本月空（上月 n={pn}、hit {ph:.3f}）")
    comp = _bss_components(resolved)
    _, _, cur_p_bar, cur_bss = comp  # type: ignore[misc]
    if cur_bss is not None and prior["bss"] is not None:
        lines.append(f"BSS {prior['bss']:.3f}→{cur_bss:.3f}"
                     f"（p̄ {prior['p_bar']:.3f}→{cur_p_bar:.3f}）")
    else:
        lines.append("BSS 对照侧含无定义（退化基线）——如实呈现不造假分")
    return lines


# iterate round 11 — promotion-gate-function (L2 promotion gate as a
# COMPUTABLE pure function: the math form of the ladder's 晋级门槛
# X/N/Y/M, runbook 晋级门槛节). COMPUTE-ONLY, NEVER ACTIVATES: the owner
# key (e-item) stays with the owner; this gate math is an ops-lane
# promotion SELF-CHECK with ZERO relation to any OOS / research judgment.
# Zero LLM, zero new dependencies (statsmodels proportion_confint already
# pinned, same import as calibration_bucket_summary). Threshold VALUES are
# owner-calibrated INPUTS — passed as parameters, never embedded magic
# numbers; an uncalibrated axis yields a REASON LINE, never a fabricated
# boolean. X-axis math: BSS = 1 − BS/BS_base against the base-rate
# (climatology) predictor "always output p̄" (p̄ = historical hit rate,
# BS_base = mean((p̄−y)²) = p̄(1−p̄)); anchors: arXiv:2611.14465 (BSS
# weight semantics = better-than-chance) and arXiv:2610.38211 RainCheck
# (BSS-vs-climatology reporting; its temporal degradation below
# climatology = the anti-leakage stance, third-party isomorphic).
# BS_base=0 (p̄ degenerates to 0 or 1) → BSS undefined → honest reason
# line, never a fake score. Y-axis: per-bucket Wilson 95% CI UPPER bound
# (conservative; empty buckets never judged). ANYTIME caveat:
# arXiv:2610.28979 principle only — monthly repeated querying needs
# anytime correction, but at one point per month the AsympCS-style
# asymptotic guarantee does NOT hold; noted honestly, nothing copied.
ANYTIME_MONITORING_NOTE = ("anytime 注记：月度连续重复查询需 anytime 校正"
                           "（arXiv:2610.28979 只借原则）；当前每月 1 点，"
                           "AsympCS 类渐近校正不成立——局限如实注记，不照搬实现")
GATE_SCOPE_NOTE = ("只算不启用：钥匙在业主（晋级门槛 e 项语义不变）；"
                   "与 OOS 判定零关系——gate 数学仅运维面晋级自检，"
                   "不触碰任何研究面判定")
# iterate round 14 (gate-assessment-bridge, framework ②; design spec
# reports/audits/2026-11-15-iterate-round-14.md §5): the two presentation
# notes fused into one standing constant — (1) analysis produces EVIDENCE,
# promotion is a SEPARATE consumption act (Argo isomorphism: analysis
# decides rollout continue/abort/pause, never replaces the deployment);
# (2) a green gate ≠ a healthy practice (the real Argo case: analysis
# passed while the canary was still broken — metric pass ≠ delivery
# health). State vocabulary borrowed from Argo AnalysisRun completion
# states (Successful/Failed/Inconclusive ≈ ok/fail/not-enough-data;
# official docs verified verbatim). PRESENTATIONAL ONLY, zero activation —
# automatic promotion decisions are NEVER implemented, the L2 key stays
# with the owner (GATE_SCOPE_NOTE semantics unchanged).
GATE_BRIDGE_NOTE = ("分析产出证据、晋升单独消费——门绿≠实践健康（Argo 实况"
                    "案例：analysis passed 而 canary 仍 broken）；三态 "
                    "verdict 词汇沿 Argo AnalysisRun 完成态 "
                    "Successful/Failed/Inconclusive ≈ ok/fail/"
                    "not-enough-data（Inconclusive=数据不足不判，环 2 降级"
                    "+gate not-enough-data 同族）；摘要只呈现零启用——自动"
                    "晋升决策绝不实现，L2 钥匙在业主（GATE_SCOPE_NOTE 钥匙"
                    "语义不变）")


def promotion_gate_assessment(records: list[dict],
                              thresholds: dict | None = None) -> dict:
    """iterate round 11 (promotion-gate-function): three-state
    met / not-met / not-enough-data over resolved records
    (claim/p/due/y — _collect_prediction_records shape). Each X/N/Y/M
    item carries metric + threshold + verdict + reason line; uncalibrated
    thresholds (None) yield reason lines, not booleans. not-enough-data
    covers: zero rows, N<N_min or M<M_min (『学够了没有』isomorphism),
    and math-undetermined cases (BS_base=0 degenerate base, no populated
    buckets). not-met requires all axes calibrated, data sufficient, and
    a computable axis objectively failing. Pure function: no LLM, no IO,
    no activation — the L2 key stays with the owner."""
    from statsmodels.stats.proportion import proportion_confint

    th = thresholds or {}
    x_min, n_min = th.get("X_min"), th.get("N_min")
    y_max, m_min = th.get("Y_max"), th.get("M_min")
    resolved = [r for r in records
                if r["p"] is not None and r["y"] is not None]
    n = len(resolved)
    items: list[dict] = []
    notes = [GATE_SCOPE_NOTE, ANYTIME_MONITORING_NOTE]

    def _axis(axis: str, metric: str, threshold: str, verdict: str,
              reason: str) -> None:
        items.append({"axis": axis, "metric": metric,
                      "threshold": threshold, "verdict": verdict,
                      "reason": reason})

    def _th(name: str, value) -> str:
        return f"{name}={value}" if value is not None else f"{name}=未定标"

    # ---- N axis: cumulative resolved rows（『学够了没有』）----
    if n_min is None:
        _axis("N", f"n={n}", _th("N_min", n_min), "undetermined",
              "N_min 未定标——数值待业主入册，不凭空造阈值")
    elif n < n_min:
        _axis("N", f"n={n}", _th("N_min", n_min), "not-enough-data",
              f"n={n} < N_min={n_min}——学够了没有，继续基线收集")
    else:
        _axis("N", f"n={n}", _th("N_min", n_min), "pass",
              f"n={n} ≥ N_min={n_min}")

    # ---- X axis: overall BSS vs base-rate climatology（base=p̄）----
    bss: float | None = None
    if n == 0:
        _axis("X", "BSS 无定义", _th("X_min", x_min), "not-enough-data",
              "零 resolved 对账行（基线收集月）——无可算样本")
    else:
        bs, bs_base, p_bar, _gate_bss = _bss_components(resolved)
        if _gate_bss is None:
            _axis("X", "BSS 无定义", _th("X_min", x_min), "undetermined",
                  f"BS_base=0（p̄={p_bar:.3f} 退化常数基线，全部 y 同值）"
                  "——BSS 无定义，诚实降级不造假分")
        else:
            bss = _gate_bss
            metric = (f"BSS={bss:.3f}"
                      f"（BS={bs:.3f}，BS_base={bs_base:.3f}，p̄={p_bar:.3f}）")
            if x_min is None:
                _axis("X", metric, _th("X_min", x_min), "undetermined",
                      "X_min 未定标——数值待业主入册，不凭空造阈值")
            elif bss > x_min:
                _axis("X", metric, _th("X_min", x_min), "pass",
                      f"BSS={bss:.3f} > X_min={x_min}（优于 base-rate 基线）")
            else:
                _axis("X", metric, _th("X_min", x_min), "fail",
                      f"BSS={bss:.3f} ≤ X_min={x_min}（未优于 base-rate 基线）")

    # ---- Y axis: per-bucket Wilson 95% upper bounds ----
    bucketed = [r for r in resolved if r["p"] >= _CALIBRATION_BAND_CUTS[0]]
    n_bands = len(_CALIBRATION_BAND_CUTS) - 1
    worst_bound: tuple[float, str] | None = None
    for i in range(n_bands):
        lo = _CALIBRATION_BAND_CUTS[i]
        hi = _CALIBRATION_BAND_CUTS[i + 1]
        last = i == n_bands - 1
        rows = [r for r in bucketed
                if lo <= r["p"] < hi or (last and r["p"] == hi)]
        if not rows:  # empty buckets are never judged (n>=1 to bound)
            continue
        hits = sum(1 for r in rows if r["y"] == 1)
        bound = proportion_confint(hits, len(rows), method="wilson")[1]
        close = "]" if last else ")"
        tag = f"p∈[{lo:.1f},{hi:.1f}{close}: {hits}/{len(rows)}"
        if worst_bound is None or bound > worst_bound[0]:
            worst_bound = (bound, tag)
    if n == 0:
        _axis("Y", "无桶可界", _th("Y_max", y_max), "not-enough-data",
              "零 resolved 对账行（基线收集月）——无可算样本")
    elif worst_bound is None:
        _axis("Y", "无桶可界", _th("Y_max", y_max), "undetermined",
              "无 p≥0.5 可入桶行——Y 轴不可判（诚实降级）")
    elif y_max is None:
        _axis("Y", f"最宽上界（{worst_bound[1]}）Wilson 上界 "
              f"{worst_bound[0]:.4f}", _th("Y_max", y_max), "undetermined",
              "Y_max 未定标——数值待业主入册，不凭空造阈值")
    elif worst_bound[0] < y_max:
        _axis("Y", f"最宽上界（{worst_bound[1]}）Wilson 上界 "
              f"{worst_bound[0]:.4f}", _th("Y_max", y_max), "pass",
              f"全部已入桶 Wilson 上界 {worst_bound[0]:.4f} < "
              f"Y_max={y_max}（空桶不判）")
    else:
        _axis("Y", f"最宽上界（{worst_bound[1]}）Wilson 上界 "
              f"{worst_bound[0]:.4f}", _th("Y_max", y_max), "fail",
              f"桶（{worst_bound[1]}）Wilson 上界 {worst_bound[0]:.4f} ≥ "
              f"Y_max={y_max}——样本量尚不足以收窄 CI")

    # ---- M axis: consecutive months with monthly BSS > X_min ----
    if n == 0:
        _axis("M", "streak=0", _th("M_min", m_min), "not-enough-data",
              "零 resolved 对账行（基线收集月）——无可算样本")
    elif x_min is None:
        _axis("M", "streak 不可判", _th("M_min", m_min), "undetermined",
              "X_min 未定标→月度 streak 判据缺失（数值待业主入册）")
    else:
        months: dict[str, list[dict]] = {}
        for r in resolved:
            months.setdefault(r["due"] or "?", []).append(r)
        streak = 0
        for month in sorted(months, reverse=True):
            rows = months[month]
            m_bs = sum((r["p"] - r["y"]) ** 2 for r in rows) / len(rows)
            m_bar = sum(r["y"] for r in rows) / len(rows)
            m_base = sum((m_bar - r["y"]) ** 2 for r in rows) / len(rows)
            if m_base == 0.0 or 1 - m_bs / m_base <= x_min:
                break  # degenerate base or a failing month ends the run
            streak += 1
        if m_min is None:
            _axis("M", f"streak={streak}", _th("M_min", m_min),
                  "undetermined", "M_min 未定标——数值待业主入册，"
                  "不凭空造阈值")
        elif streak < m_min:
            _axis("M", f"streak={streak}", _th("M_min", m_min),
                  "not-enough-data",
                  f"streak={streak} < M_min={m_min}——连够了没有，"
                  "继续基线收集（月度基线退化月不计入 streak）")
        else:
            _axis("M", f"streak={streak}", _th("M_min", m_min), "pass",
                  f"streak={streak} ≥ M_min={m_min}")

    verdicts = {it["verdict"] for it in items}
    if "undetermined" in verdicts or "not-enough-data" in verdicts:
        state = "not-enough-data"
    elif "fail" in verdicts:
        state = "not-met"
    else:
        state = "met"
    return {"state": state, "items": items, "notes": notes}


# iterate round 14 (gate-assessment-bridge): state vocabulary mapped from
# Argo AnalysisRun completion states — official docs verbatim: "Completed
# runs are considered Successful, Failed, or Inconclusive" driving
# continue/abort/pause. BORROWED PRESENTATION WORDS ONLY: the K8s
# progressive-delivery runtime is NOT adopted (延伸索引㉞ boundary); the
# mapping is a reading aid for humans, never an activation path.
_GATE_ARGO_STATES = {"met": ("Successful", "ok"),
                     "not-met": ("Failed", "fail"),
                     "not-enough-data": ("Inconclusive", "not-enough-data")}


def promotion_gate_summary_line(records: list[dict],
                                thresholds: dict | None = None) -> str:
    """iterate round 14 (gate-assessment-bridge, framework ②): the FIRST
    consumer of promotion_gate_assessment — ONE presentational summary line
    for the --weekly tail. Zero LLM, zero IO, zero activation: the line
    renders the gate's three-state verdict (met/not-met/not-enough-data
    mapped to Argo Successful/Failed/Inconclusive ≈ ok/fail/not-enough-data)
    plus the four per-axis verdicts (N/X/Y/M, gate-internal words pass/fail/
    undetermined/not-enough-data — never re-translated) and GATE_BRIDGE_NOTE
    (both notes: evidence-vs-promotion separation, green-gate ≠ healthy
    practice). thresholds=None (the run_weekly default) keeps every axis
    honestly uncalibrated -> not-enough-data — the owner INPUTS contract,
    no embedded magic numbers, no fabricated thresholds. The line NEVER
    feeds findings or the exit code (零启用 in code, not just prose): the
    L2 promotion key stays with the owner."""
    gate = promotion_gate_assessment(records, thresholds)
    state = gate["state"]
    argo_word, gloss = _GATE_ARGO_STATES[state]
    axis_verdicts = {it["axis"]: it["verdict"] for it in gate["items"]}
    axes = " ".join(f"{a}:{axis_verdicts.get(a, 'not-enough-data')}"
                    for a in ("N", "X", "Y", "M"))
    return (f"- promotion gate assessment（round 14 桥·只呈现零启用）: "
            f"gate={state}［Argo: {argo_word}≈{gloss}］ | 轴判定 {axes} | "
            f"{GATE_BRIDGE_NOTE}")


if __name__ == "__main__":
    # GBK-console armor (flywheel-rehearsal, 2026-11-13): main() already
    # reconfigures stdout AFTER parse_args, but stderr and the argparse
    # usage path were only GBK-safe incidentally (measured: under a
    # `python -I` child with PYTHONIOENCODING/PYTHONUTF8 stripped, stdout
    # survives via main()'s reconfigure, yet stderr emits raw GBK bytes —
    # mojibake for any UTF-8 consumer, and any future non-GBK stderr
    # literal would crash the strict codec). The U+2212/U+00B2 literals
    # (:966/:1022/:1119 — iterate round 11 +1 shift) are byte-locked by the
    # ring-1a pin and are NOT
    # touched — the fix lives on the CLI output surface only: reconfigure
    # BOTH streams BEFORE main() runs (covers argparse text too).
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass
    raise SystemExit(main())
