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

v2 (2026-11-14, task anchor-guard-v2; upstream semantics: fiberplane/drift
「Bind docs to code and check for drift」, backlog 延伸索引㊸ — cite only,
pure-stdlib re-implementation, no upstream install):
- Fifth state ``semantic``: an in-bounds anchor whose HINT annotation is
  absent from the target line window is semantic drift (v1 counted it hit).
- Hint syntax: an ASCII parenthetical immediately after the anchor token —
  ``tool.py:123(render_card)`` or spans ``tool.py:1-9(def foo, return)`` —
  comma-separated symbol literals verified as plain substrings of the target
  line window (all hints must be present: AND semantics).
- Batching whitelist ``SEMANTIC_SCOPE``: only (ledger-src, target-path)
  pairs listed there consume hints; every other anchor keeps v1 behaviour
  even when a hint is present (parsed, then ignored). Migrate in batches —
  never to hit a quota (不为迁而迁). The pair keys on the RESOLVED target
  path (semantic-scope-key-fix): a short-form ``monthly_review.py:1204``
  anchor resolves via basename to ``scripts/monthly_review.py`` and
  consumes its hint — pre-fix the anchor's written spelling was compared,
  so short-form hints were decorative (a wrong symbol on them still
  judged hit).
- ``--strict`` unchanged: exits 1 on drifted/lost only; ``semantic`` stays
  fail-soft (hard-gating it remains an owner decision, 待业主区).

Batch 1 migration (2026-11-15, task anchor-batch1-migration): the runbook
first-month playbook section (:811-944 as of pre-migration HEAD) had its
29 bare ``:N`` mentions rewritten as explicit ``file:line(hint)`` anchors
(audit-counted 29 bare + 1 pre-existing explicit; guard-identical regex).
Values re-verified against live line numbers at migration time (old digits
had drifted; 7e3a6bbc7b same-shape precedent). Batch 2 (:348-395, :732-769)
and owner-gated (:488, ops_local_refresh.py pair) stay unmigrated;
handoff legacy bare stays untouched (append-only, not economical).

Batch 2 migration (2026-11-15, task anchor-batch2-migration): runbook
sections A (:348-395) and C (:732-769) had 13 bare ``:N`` mentions
rewritten as explicit ``file:line(hint)`` anchors (same-shape BARE_RE
count; mission-count discrepancies recorded honestly: A-section
6/≈11/7 three-way, ~14 vs measured 13 after excluding the owner-gated
pair). Values re-verified against live line numbers at migration time
(:2045 drifted to :2302 per 7e3a6bbc7b note; :646 re-located by literal
grep to :149 push_only_recovery; :1428-1451/:1002-1074/:986-987/:997/
:768 re-scoped to current symbol lines). Billing :488 pair (:46/:50)
stays owner-gated per round-18 report sec.3; ops_local_refresh.py
SEMANTIC_SCOPE pairing still awaits owner. The batch-1 hold note above
(“Batch 2 ... stay unmigrated”) is superseded by this migration.
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
    # v2 optional hint: ASCII parenthetical right after the anchor token;
    # CJK 全角（）glue never matches, so legacy prose stays hint-free.
    r"(?:[ \t]*\(([A-Za-z0-9_][A-Za-z0-9_ .,()/\-]{0,120})\))?"
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
STATUS_SEMANTIC = "semantic"

# v2 semantic-hint verification scope: (ledger-src, target-path) pairs.
# Only anchors inside a listed pair consume their hint annotation and can
# surface STATUS_SEMANTIC; every other anchor keeps v1 behaviour even when
# a hint is present (parsed, then ignored). Migrate in batches — each batch
# names its pair explicitly; 存量 bare/unhinted anchors are NOT force-migrated.
SEMANTIC_SCOPE = frozenset({
    ("docs/ops-local-refresh.md", "scripts/monthly_review.py"),
})


@dataclass(frozen=True)
class Anchor:
    src: str  # repo-relative source file the anchor lives in
    src_line: int  # 1-based physical line in the source
    target: str  # target path exactly as written
    start: int  # 1-based expected line
    end: int | None  # inclusive end for :N-M spans, else None
    hints: tuple[str, ...] = ()  # v2 symbol literals from the (…) annotation

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


def _parse_hints(raw: str | None) -> tuple[str, ...]:
    """Split a v2 ``(sym, sym2)`` annotation into symbol literals."""
    if not raw:
        return ()
    return tuple(tok.strip() for tok in raw.split(",") if tok.strip())


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
                    hints=_parse_hints(m.group(4)),
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


def _norm_src(src: str, repo: Path) -> str:
    """Stable repo-relative posix key for SEMANTIC_SCOPE matching."""
    p = Path(src)
    if not p.is_absolute():
        return p.as_posix()
    try:
        return p.resolve().relative_to(Path(repo).resolve()).as_posix()
    except ValueError:
        return p.as_posix()


def verify_anchor(a: Anchor, repo: Path, index: dict[str, list[str]]) -> Row:
    """Classify one anchor: hit / drifted / lost / external / semantic."""
    if a.target in EXTERNAL_TARGETS:
        return Row(a, STATUS_EXTERNAL, "citation-only upstream file (skip-list)")
    path, how = resolve_target(a.target, repo, index)
    if path is None:
        return Row(a, STATUS_LOST, how)
    lines = path.read_text(
        encoding="utf-8", errors="replace"
    ).splitlines()
    n_lines = len(lines)
    upper = a.end if a.end is not None else a.start
    if not (a.start >= 1 and upper <= n_lines):
        return Row(
            a,
            STATUS_DRIFTED,
            f"{how}, expected through line {upper}, target has {n_lines} lines",
        )
    # v2: in-bounds hint verification — semantic drift when an expected
    # symbol literal is absent from the target line window. Scoped pairs
    # only (SEMANTIC_SCOPE); everything else stays v1 "in bounds = hit".
    # semantic-scope-key-fix: the pair keys on the RESOLVED target path
    # (resolve_target basename resolution), not the anchor's written
    # spelling — short-form "monthly_review.py:1204(run_propose)" anchors
    # inside a scoped pair consume their hints (pre-fix the raw string was
    # compared, so short-form hints were decorative: a wrong symbol on
    # them still judged hit).
    if a.hints:
        try:
            tgt_key = path.relative_to(repo).as_posix()
        except ValueError:  # resolved outside repo: fall back to spelling
            tgt_key = a.target
        if (_norm_src(a.src, repo), tgt_key) in SEMANTIC_SCOPE:
            window = "\n".join(lines[a.start - 1:upper])
            missing = [h for h in a.hints if h not in window]
            if missing:
                return Row(
                    a,
                    STATUS_SEMANTIC,
                    f"{how}, in bounds but hint(s) absent from lines "
                    f"{a.start}-{upper}: {', '.join(missing)}",
                )
    return Row(a, STATUS_HIT, f"{how}, within {n_lines} lines")


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
        STATUS_SEMANTIC: 0,
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
        "external={external} semantic={semantic} bare-unverified={bare} "
        "(v2: in-bounds hint mismatch -> semantic; hints verify only "
        "SEMANTIC_SCOPE pairs; bare :N stays counted-not-verified)".format(
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
