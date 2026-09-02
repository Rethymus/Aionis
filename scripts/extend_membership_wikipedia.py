"""Extend the pierrebrunelle S&P 500 monthly membership series from Wikipedia.

Thin CLI over :func:`aionis.ingest.universe_ext.extend_membership`: the
deterministic extender that parses the Wikipedia "Historical components of the
S&P 500" changes table and appends months past the upstream 2026-04 end. The
100%-overlap reconcile gate (rebuild EVERY existing month from the first
snapshot + the parsed change log; require exact ticker-set equality) runs
FIRST — if it fails, nothing is written and the exit code is 1.

Usage::

    uv run python scripts/extend_membership_wikipedia.py              # gate + extend
    uv run python scripts/extend_membership_wikipedia.py --dry-run    # gate only, write nothing
    uv run python scripts/extend_membership_wikipedia.py --force-fetch  # refetch HTML

Prints a JSON summary. Exit 0 on success (including a passing dry run),
1 when the reconcile gate fails or no changes could be parsed.
"""
from __future__ import annotations

import argparse
import json
import sys

from aionis.ingest.universe_ext import extend_membership


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--force-fetch", action="store_true",
        help="re-fetch the Wikipedia HTML even if a cached copy exists",
    )
    ap.add_argument(
        "--dry-run", action="store_true",
        help="reconcile-only: run the overlap gate, write nothing",
    )
    args = ap.parse_args()

    summary = extend_membership(force_fetch=args.force_fetch, dry_run=args.dry_run)
    print(json.dumps(summary, indent=2, default=str))
    return 0 if summary.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
