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
    backup = st.get("backup")
    check(
        "backup automation SUMMARY field",
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
    try:
        news = json.loads(PANEL_NEWS.read_text(encoding="utf-8"))
        as_of = str(news.get("as_of", ""))
        check("news_feed as_of advanced", as_of.startswith(args.date), args.date, as_of)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        failures += 1
        _fail("news_feed as_of advanced", args.date, f"read error: {e}")

    print(f"\n{'ALL CHECKS PASS' if failures == 0 else f'{failures} CHECK(S) FAILED'}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
