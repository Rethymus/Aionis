"""Anchor guard — structural drift detector for in-ledger file:line anchors.

iterate 轮 13 / anchor-guard (round 147 批). The two ledgers
(docs/ops-local-refresh.md + state/handoff.md) carry dozens of explicit
``path/to/file.py:123`` anchors; rounds 12/143 chased 92+ stale ones by hand
AFTER they drifted. This tool flips anchor debt from passive errata to
active interception: parse every explicit file:line anchor, verify the
target file exists and the line is in bounds, report hits vs drift.

Owner red lines (2026-11-14, task anchor-guard):
- Pure stdlib, zero new dependencies (ast-grep/markdownlint/comby not used).
- Diagnose only, never repair: ``--fix`` is accepted and explicitly refuses
  to write anything (呈报-入册分离, round 146 precedent — engines never edit
  the ledgers; a human appends errata).
- Fail-soft by default: a plain run always exits 0 with the full report;
  ``--strict`` exits 1 on drifted/lost (hard-gating stays an owner decision).
- Not the research pipeline: reads the two ledger files only; ``src/aionis``
  untouched; creates no anchors.

Stated coverage gaps (v1, honest boundaries — extend only if owner names it):
- Bare ``:123`` anchors (no filename) cannot be resolved to a target file
  without symbol hints; they are COUNTED (summary "bare") but not verified.
- Semantic misalignment (line in bounds but wrong content — the runbook
  :845/:846 disease fixed in round 147) needs symbol hints; out of scope.
- Citation-only anchors into upstream repos (e.g. PATCHES.md of
  Cyrene963/hermes-patches, backlog 延伸索引㉜) are skip-listed as
  "external", not reported lost.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCES = ("docs/ops-local-refresh.md", "state/handoff.md")

# Explicit anchors only: repo-relative path with a known extension, then
# :line or :line-line. The lookbehind kills URLs (the char before a path
# segment of "https://host/x.py" is "/" or "."). Path charset is ASCII so
# CJK glue (e.g. "④docs/x.md:1", "注记/current.md:9") never becomes part
# of the target. Bare :line anchors have no filename and are counted
# separately (BARE_RE), never verified. Bare-FILENAME anchors (the ledgers
# often write "monthly_review.py:678" without the scripts/ prefix) are
# resolved deterministically: exact repo-relative path first, then a UNIQUE
# basename match in the pruned tree walk; ambiguous or absent -> lost.
ANCHOR_RE = re.compile(
    r"(?<![A-Za-z0-9_/.-])"
    r"((?:[A-Za-z0-9_@.-]+/)*[A-Za-z0-9_@.-]+\."
    r"(?:py|md|yml|yaml|json|toml|ts|tsx|sh|cfg|ini|txt))"
    r":(\d{1,5})(?:-(\d{1,5}))?(?!\d)"
)
BARE_RE = re.compile(r"(?<![\w.:-])(?<!\d):(\d{1,5})(?:-(\d{1,5}))?(?!\d)")

# Upstream files that legitimately appear as citation anchors in the ledgers
# (they document other repos, not this tree). Listed explicitly so "lost"
# stays meaningful for genuinely missing repo files.
EXTERNAL_TARGETS = frozenset({"PATCHES.md"})

STATUS_HIT = "hit"
STATUS_DRIFTED = "drifted"
STATUS_LOST = "lost"
STATUS_EXTERNAL = "external"


@dataclass(frozen=True)
class Anchor:
    src: str  # repo-relative source file the anchor lives in
    src_line: int  # 1-based physical line in the source
    target: str  # target path exactly as written
    start: int  # 1-based expected line
    end: int | None  # inclusive end for :N-M spans, else None

    @property
    def span(self) -> str:
        return f"{self.target}:{self.start}" + (
            f"-{self.end}" if self.end is not None else ""
        )


@dataclass(frozen=True)
class Row:
    anchor: Anchor
    status: str
    detail: str


def parse_anchors(text: str, src: str) -> list[Anchor]:
    """Extract explicit file:line anchors from one ledger source."""
    out: list[Anchor] = []
    for i, line in enumerate(text.splitlines(), 1):
        for m in ANCHOR_RE.finditer(line):
            path, start, end = m.group(1), int(m.group(2)), m.group(3)
            out.append(
                Anchor(
                    src=src,
                    src_line=i,
                    target=path,
                    start=start,
                    end=int(end) if end is not None else None,
                )
            )
    return out


def count_bare(text: str) -> int:
    """Count bare ``:N`` tokens (diagnostic only — unverifiable in v1)."""
    return sum(len(BARE_RE.findall(line)) for line in text.splitlines())


_PRUNE_DIRS = frozenset(
    {".git", "node_modules", "__pycache__", ".venv", ".next", "dist", "data", "runs"}
)


def index_repo(repo: Path) -> dict[str, list[str]]:
    """Deterministic basename -> repo-relative paths map (pruned tree walk)."""
    index: dict[str, list[str]] = {}
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = [d for d in dirnames if d not in _PRUNE_DIRS]
        for f in filenames:
            rel = (Path(dirpath) / f).relative_to(repo).as_posix()
            index.setdefault(f, []).append(rel)
    return index


def resolve_target(
    target: str, repo: Path, index: dict[str, list[str]]
) -> tuple[Path | None, str]:
    """Exact repo-relative path first; then unique basename match."""
    direct = repo / target
    if direct.is_file():
        return direct, "exact"
    cands = index.get(Path(target).name, [])
    if len(cands) == 1:
        return repo / cands[0], f"basename->{cands[0]}"
    if len(cands) > 1:
        return None, "ambiguous basename: " + ", ".join(sorted(cands))
    return None, "target file not found in repo"


def verify_anchor(a: Anchor, repo: Path, index: dict[str, list[str]]) -> Row:
    """Classify one anchor: hit / drifted / lost / external."""
    if a.target in EXTERNAL_TARGETS:
        return Row(a, STATUS_EXTERNAL, "citation-only upstream file (skip-list)")
    path, how = resolve_target(a.target, repo, index)
    if path is None:
        return Row(a, STATUS_LOST, how)
    n_lines = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
    upper = a.end if a.end is not None else a.start
    if a.start >= 1 and upper <= n_lines:
        return Row(a, STATUS_HIT, f"{how}, within {n_lines} lines")
    return Row(
        a,
        STATUS_DRIFTED,
        f"{how}, expected through line {upper}, target has {n_lines} lines",
    )


def run(sources: tuple[str, ...], repo: Path) -> tuple[dict[str, int], list[Row]]:
    """Verify every explicit anchor in the given ledger sources.

    Returns (summary, rows); summary counts anchors by status plus the
    unverified bare-token population. Read-only: writes nothing anywhere.
    """
    rows: list[Row] = []
    summary = {
        "anchors": 0,
        STATUS_HIT: 0,
        STATUS_DRIFTED: 0,
        STATUS_LOST: 0,
        STATUS_EXTERNAL: 0,
        "bare": 0,
    }
    index = index_repo(repo)
    for src in sources:
        p = Path(src) if Path(src).is_absolute() else repo / src
        if not p.is_file():
            print(f"warning: source not found, skipped: {src}", file=sys.stderr)
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        summary["bare"] += count_bare(text)
        for a in parse_anchors(text, src):
            row = verify_anchor(a, repo, index)
            rows.append(row)
            summary["anchors"] += 1
            summary[row.status] += 1
    return summary, rows


def _report(summary: dict[str, int], rows: list[Row]) -> None:
    for row in sorted(rows, key=lambda r: (r.status, r.anchor.src, r.anchor.src_line)):
        a = row.anchor
        print(f"{row.status:8s} {a.src}:{a.src_line}  {a.span}  ({row.detail})")
    print(
        "summary: explicit={anchors} hit={hit} drifted={drifted} lost={lost} "
        "external={external} bare-unverified={bare} "
        "(bare :N anchors and in-bounds semantic drift are stated v1 gaps)".format(
            **summary
        )
    )


def main(argv: list[str] | None = None, repo: Path = REPO_ROOT) -> int:
    parser = argparse.ArgumentParser(
        description="Structural drift guard for ledger file:line anchors "
        "(diagnose-only; zero writes by design)."
    )
    parser.add_argument(
        "--src",
        action="append",
        default=None,
        metavar="FILE",
        help="ledger source to scan (repo-relative; default: "
        + " + ".join(DEFAULT_SOURCES)
        + ")",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 when drifted/lost > 0 (fail-soft is the default; "
        "hard-gating the suite is an owner decision)",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="accepted for discoverability, REFUSES to act: repairs are "
        "human errata, the engine never edits the ledgers",
    )
    args = parser.parse_args(argv)
    if args.fix:
        print(
            "--fix: diagnose-only by design (owner red line, round 147); "
            "no files written — repair stale anchors via human errata batches"
        )
    sources = tuple(args.src) if args.src else DEFAULT_SOURCES
    summary, rows = run(sources, repo)
    _report(summary, rows)
    if args.strict and (summary[STATUS_DRIFTED] or summary[STATUS_LOST]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
