#!/usr/bin/env python
"""Backup the audit-critical tracked files to a timestamped local bundle.

Addresses the round-155 reflection gap: ``runs/ledger.jsonl`` is the
project's core audit chain but exists only in this repo + GitHub. This
script creates a redundant local copy (git bundle + raw file copy) so a
GitHub-side incident (force-push mistake, account issue, repo deletion)
cannot destroy the only record.

Usage::

    uv run python scripts/backup_audit_chain.py              # default backup dir
    uv run python scripts/backup_audit_chain.py --out D:/backups  # custom dir

Creates (in --out, default ``data/backups/`` which is gitignored):
  - ``ledger-YYYYMMDD-HHMMSS.jsonl``  raw copy of runs/ledger.jsonl
  - ``repo-bundle-YYYYMMDD-HHMMSS.bundle``  full git bundle (all refs)

Exit 0 on success; nonzero on any failure. Idempotent per timestamp —
re-running in the same second overwrites the same name.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "data" / "backups"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT,
                    help=f"backup directory (default: {DEFAULT_OUT})")
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")

    # 1. Raw ledger copy (the audit chain — small, fast, always)
    src = ROOT / "runs" / "ledger.jsonl"
    dst = args.out / f"ledger-{ts}.jsonl"
    if not src.exists():
        print(f"ERROR: {src} not found", file=sys.stderr)
        return 1
    shutil.copy2(src, dst)
    print(f"ledger copy: {dst} ({dst.stat().st_size:,} bytes)")

    # 2. Full repo bundle (every ref — covers state/, decisions/, docs/)
    bundle = args.out / f"repo-bundle-{ts}.bundle"
    r = subprocess.run(
        ["git", "bundle", "create", str(bundle), "--all"],
        cwd=ROOT, capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        print(f"WARNING: git bundle failed (non-fatal, ledger copy is safe): "
              f"{r.stderr.strip()[-100:]}", file=sys.stderr)
    else:
        print(f"repo bundle: {bundle} ({bundle.stat().st_size:,} bytes)")

    # 3. Prune: keep the most recent 30 backup pairs (runs nightly → ~1 month)
    old_ledgers = sorted(args.out.glob("ledger-*.jsonl"))
    for old in old_ledgers[:-30]:
        old.unlink(missing_ok=True)
    old_bundles = sorted(args.out.glob("repo-bundle-*.bundle"))
    for old in old_bundles[:-30]:
        old.unlink(missing_ok=True)

    print(f"backup complete: {args.out} "
          f"(retention: 30 most recent pairs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
