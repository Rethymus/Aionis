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

Exit codes: 0 = at least one SUMMARY collected for the month and no internal
anomaly; 1 = zero SUMMARYs, or an internal anomaly (unreadable run.log, corrupt
SUMMARY line, unreadable existing data_health.json). gh unavailability is NOT
an exit-1 condition.
"""
from __future__ import annotations

import argparse
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
               jobs_sig=None) -> tuple[str, int]:
    """The --weekly mode: render the external-audit report and return
    (markdown, exit_code). 0 = clean; 1 = findings needing human attention;
    gh-unreachable checks are reported as 未能核对, never scored as failures."""
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

    lines += [f"## Findings requiring human attention: {len(findings)}", ""]
    lines += [f"- {x}" for x in findings] if findings else \
        ["- none — walk away"]
    return "\n".join(lines) + "\n", (1 if findings else 0)


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
    month (same-month re-append is refused: return 2)."""
    if not MONTH_RE.match(month):
        raise ValueError(f"bad month '{month}' (want YYYY-MM)")
    try:
        datetime.strptime(month, "%Y-%m")
    except ValueError as exc:
        raise ValueError(f"bad month '{month}' (not a real year-month)") from exc
    body = text.strip("\n")
    if not body.strip():
        raise ValueError("lesson text is empty")
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
              "next cycle; protocol-only, no dependency) -->")
    with handoff_path.open("a", encoding="utf-8") as fh:
        if existing and not existing.endswith("\n"):
            fh.write("\n")
        fh.write(f"{header}\n{body.rstrip()}\n")
    return 0


def lesson_seeds(month: str, repo: Path, errors: list[str]) -> dict:
    """Deterministic month-end incident facts (no LLM): the Reflexion
    'score the attempt' step reads these, never guesses. Failed evenings
    surface as weekday-misses (a hard-fail evening writes no SUMMARY — the
    existing missing-weekday enumeration is the failure signal)."""
    days, push_only = collect_log_days(repo, month, errors)
    persistent = [(d["date"], d["persistent_soft_fails"]) for d in days
                  if d["persistent_soft_fails"]]
    spin, scanned = spin_detection(repo)
    return {"month": month, "days_with_summary": len(days),
            "persistent_soft_fails": persistent,
            "missing_weekdays": missing_weekdays(
                month, {d["date"] for d in days}),
            "spin_findings": spin, "push_only": push_only}


def render_reflexion_section(seeds: dict, prior: tuple[str, str] | None,
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
    if errors:
        out.append(f"- collection anomalies: {errors}")
    out += ["", "## 6. Lessons carried from state/handoff.md (the 'inject "
               "into next cycle' leg — sessions read the handoff first per "
               "AGENTS.md)", ""]
    if prior:
        out.append(f"Latest block: month={prior[0]}")
        out.append("")
        out.append("```")
        out += prior[1].splitlines()
        out.append("```")
    else:
        out.append("- none yet (no monthly-reflexion-lessons block in the "
                   "handoff)")
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
                             "spot-check + spin detection; exit 1 on "
                             "findings. Read-only, zero Actions dependency.")
    parser.add_argument("--lessons", action="store_true",
                        help="with the monthly flow: add Reflexion lesson "
                             "seeds + the latest lessons block carried from "
                             "state/handoff.md (round 126)")
    parser.add_argument("--append-lessons-from", default=None, metavar="FILE",
                        help="append the lesson text in FILE to "
                             "state/handoff.md as this month's "
                             "monthly-reflexion-lessons block (append-only, "
                             "one block per month; exit 2 on duplicate)")
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
        return code
    if args.append_lessons_from:
        text = Path(args.append_lessons_from).read_text(encoding="utf-8")
        return append_lessons(text, month,
                              repo / "state" / "handoff.md")
    errors: list[str] = []
    days, push_only = collect_log_days(repo, month, errors)
    gh = {wf: collect_gh(wf, month, repo) for wf in GH_WORKFLOWS}
    health = collect_health(repo, errors)
    markdown = render(month, days, push_only, gh, health, errors,
                      datetime.now().isoformat(timespec="seconds"))
    if args.lessons:
        seeds = lesson_seeds(month, repo, errors)
        prior = latest_lessons_block(
            (repo / "state" / "handoff.md").read_text(encoding="utf-8")
            if (repo / "state" / "handoff.md").exists() else "")
        markdown += "\n" + render_reflexion_section(seeds, prior, [])
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(markdown, encoding="utf-8")
        print(f"wrote {out_path}", file=sys.stderr)
    else:
        print(markdown, end="")
    return 0 if (days and not errors) else 1


if __name__ == "__main__":
    raise SystemExit(main())
