"""Pre-commit guard: refuse to commit forbidden artifacts.

Enforces in one pass what CLAUDE.md/AGENTS.md declare as Forbidden:
- staged files under ``data/`` (gitignored caches + irreplaceable history);
- staged ``*.parquet`` anywhere;
- staged ``.env`` / ``*`` secret-ish files (``.env``, ``.env.*``);
- any staged file > 5 MB (catches accidental parquet/csv/data drops even
  when renamed or moved outside data/).

Exits non-zero with one line per violation. Designed to run as a local
pre-commit hook (``.pre-commit-config.yaml``) AND usable standalone::

    uv run python scripts/precommit_guard.py          # checks staged files
    uv run python scripts/precommit_guard.py --all    # checks the whole tree

Bounds: display/ops lane — read-only inspection of the git index.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MAX_STAGED_BYTES = 5 * 1024 * 1024  # 5 MB — evidence HTMLs are far below this


def _staged_files() -> list[str]:
    proc = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACR"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return [ln for ln in proc.stdout.splitlines() if ln.strip()]


def _violations(files: list[str]) -> list[str]:
    problems: list[str] = []
    for rel in files:
        path = rel.replace("\\", "/")
        lowered = path.lower()
        if lowered.startswith("data/"):
            problems.append(
                f"{rel}: 'data/' is gitignored regenerable/secret history — never commit")
        if lowered.endswith(".parquet"):
            problems.append(f"{rel}: '*.parquet' is leakage-sensitive + gitignored — never commit")
        basename = lowered.rsplit("/", 1)[-1]
        if basename == ".env" or (basename.startswith(".env.") and basename != ".env.example"):
            problems.append(f"{rel}: env file — secrets — never commit")
        target = ROOT / rel
        if target.is_file():
            size = target.stat().st_size
            if size > MAX_STAGED_BYTES:
                problems.append(f"{rel}: {size:,} bytes > {MAX_STAGED_BYTES:,} staged-size cap")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="Refuse forbidden staged artifacts.")
    parser.add_argument("--all", action="store_true",
                        help="check the whole tracked tree instead of the index")
    args = parser.parse_args()

    if args.all:
        proc = subprocess.run(
            ["git", "ls-files"], cwd=str(ROOT), capture_output=True,
            text=True, encoding="utf-8", check=True,
        )
        files = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    else:
        files = _staged_files()

    problems = _violations(files)
    if problems:
        print("precommit guard: REFUSING commit", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print(f"precommit guard: {len(files)} file(s) clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
