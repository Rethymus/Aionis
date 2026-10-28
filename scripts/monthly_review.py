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
    args = parser.parse_args(argv)
    try:  # keep CJK (未能核对) intact even on a legacy GBK console
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except (AttributeError, OSError):
        pass
    repo = Path(args.repo).resolve() if args.repo else ROOT
    month = args.month or default_month()
    errors: list[str] = []
    days, push_only = collect_log_days(repo, month, errors)
    gh = {wf: collect_gh(wf, month, repo) for wf in GH_WORKFLOWS}
    health = collect_health(repo, errors)
    markdown = render(month, days, push_only, gh, health, errors,
                      datetime.now().isoformat(timespec="seconds"))
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
