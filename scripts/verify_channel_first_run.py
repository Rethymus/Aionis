"""One-shot verifier for the Monday-evening channel first run (round 191 prep).

The 2026-10-05 18:05 Beijing channel run is the FIRST live run with two new
wirings: (a) build_ticker_metadata in cached mode (round 138 — the no-cache
whole-universe refetch soft-failed every night, e.g. 2026-10-02) and (b) the
post-push audit-chain backup with its SUMMARY `backup` field (round 172).
This script turns the checkpoint into one command so a later session (or the
ops runbook) verifies REAL state, not memory:

    uv run python scripts/verify_channel_first_run.py [--date 2026-10-05]

Checks (read-only):
  1. the done-marker's date matches --date and status is ok_committed;
  2. build_ticker_metadata is ABSENT from soft_fails (cache-mode fix live);
  3. the SUMMARY carries a `backup` field of ok / warn:<note> (never absent);
  4. push succeeded and both CI workflows report success;
  5. the run's panel as_of advanced vs the prior evening (news_feed probe).

Exit 0 only if every check passes; each failure prints CHECK-FAIL with the
observed value. Read-only: touches no lane state, writes no ledger.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# The channel's once-per-evening marker (gitignored; see ops_local_refresh.py).
STATE = ROOT / "data" / "ops" / "local_refresh_state.json"
PANEL_NEWS = ROOT / "web" / "src" / "data" / "aionis" / "news_feed.json"


def _fail(name: str, expected: str, observed: object) -> None:
    print(f"CHECK-FAIL {name}: expected {expected}, observed {observed!r}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=date.today().isoformat())
    args = ap.parse_args()

    failures = 0

    def check(name: str, ok: bool, expected: str, observed: object) -> None:
        nonlocal failures
        if ok:
            print(f"CHECK-PASS {name}")
        else:
            failures += 1
            _fail(name, expected, observed)

    if not STATE.exists():
        print(f"CHECK-FAIL state-file: {STATE} missing — did the channel run?")
        return 1
    st = json.loads(STATE.read_text(encoding="utf-8"))

    check("date", st.get("date") == args.date, args.date, st.get("date"))
    check("status", st.get("status") == "ok_committed", "ok_committed", st.get("status"))
    soft = st.get("soft_fails") or []
    check(
        "ticker_metadata cache mode (no soft-fail)",
        "build_ticker_metadata" not in soft,
        "absent from soft_fails",
        soft,
    )
    # Backup field: state.json carries it from round 197 on; the FIRST live
    # run (2026-10-05) predates that wiring — its backup verdict lives in the
    # evening's log line ("audit-chain backup: ok"), so fall back to the log.
    backup = st.get("backup")
    backup_via_log = False
    if not isinstance(backup, str):
        log_dir = ROOT / "runs" / "ops_local_refresh" / args.date
        for lg in sorted(log_dir.glob("*.log")) if log_dir.exists() else []:
            m = re.search(r"audit-chain backup: (ok|warn:\S+)", lg.read_text(
                encoding="utf-8", errors="ignore"))
            if m:
                backup, backup_via_log = m.group(1), True
                break
    check(
        "backup automation ran" + (" (via log)" if backup_via_log else ""),
        isinstance(backup, str) and (backup == "ok" or backup.startswith("warn:")),
        "ok | warn:<note>",
        backup,
    )
    check("pushed", st.get("pushed") is True, True, st.get("pushed"))
    ci = st.get("ci") or {}
    check(
        "CI both workflows",
        ci.get("Tests") == "success"
        and ci.get("Publish site (gh-pages)") == "success",
        "Tests=success, Publish=success",
        ci,
    )

    # Freshness probe: the news panel should carry the new evening's as_of.
    # Honest exception: when the news_feed fetch step soft-failed (e.g. GDELT
    # 429), the retain guard keeps the prior panel BY DESIGN and the recovery
    # lane retries later — stale as_of + a recorded soft-fail is a pass; stale
    # as_of with NO accounting is the real drift this probe exists to catch.
    try:
        news = json.loads(PANEL_NEWS.read_text(encoding="utf-8"))
        as_of = str(news.get("as_of", ""))
        news_retained = any("news_feed" in s for s in soft)
        if as_of.startswith(args.date):
            check("news_feed as_of advanced", True, args.date, as_of)
        elif news_retained:
            check("news_feed as_of advanced", True,
                  f"{args.date} OR honest retain (soft-fail recorded)",
                  f"{as_of} (retained; soft_fails={soft})")
        else:
            check("news_feed as_of advanced", False, args.date,
                  f"{as_of} and news_fetch not in soft_fails — unaccounted drift")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        failures += 1
        _fail("news_feed as_of advanced", args.date, f"read error: {e}")

    print(f"\n{'ALL CHECKS PASS' if failures == 0 else f'{failures} CHECK(S) FAILED'}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
