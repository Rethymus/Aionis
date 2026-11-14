"""Hermetic tests for the anchor guard (scripts/anchor_guard.py).

anchor-guard 拦截钉 (iterate 轮 13, handoff 轮 147 批): ledger file:line
anchors were chased by hand across rounds (round 12 alone re-pointed 92);
this locks the deterministic guard that flips that debt to interception.

Fixtures are tmp_path anchor-list COPIES — zero network, zero repo mutation.
One live pin (test_repo_anchor_baseline) runs the REAL guard against the
REAL ledgers and freezes the known-bad set: the two stale anchors below
live in the append-only handoff (旧条目零回改 red line) so they are frozen
as reported debt, never edited away. Any NEW drifted/lost anchor — or a
baseline anchor changing state — fails the pin: that is the contract
「新提交移动行号时测试红」. Hard-gating beyond this pin stays an owner
decision (fail-soft red line); --fix refusing to write is pinned too.
"""
from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(_SCRIPTS))

import anchor_guard as ag  # noqa: E402

_REPO = Path(__file__).resolve().parents[1]

# (src, src_line, target, start, end, status) — append-only handoff debt,
# frozen 2026-11-14: prompts.py exists nowhere in the tree (renamed away
# before the ledger entry); iterate-round-2.md is a shorthand for
# reports/audits/2026-11-12-iterate-round-2.md (basename mismatch).
KNOWN_BAD = (
    ("state/handoff.md", 2922, "prompts.py", 113, None, "lost"),
    ("state/handoff.md", 2936, "iterate-round-2.md", 79, 83, "lost"),
)


def _mini_repo(tmp_path: Path) -> Path:
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "tool.py").write_text("\n" * 30, encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "note.md").write_text("l1\nl2\nl3\n", encoding="utf-8")
    src = tmp_path / "ledger.md"
    src.write_text(
        "ok `scripts/tool.py:10` exact\n"
        "bare-filename tool.py:31 drifted\n"
        "range scripts/tool.py:1-3 ok\n"
        "missing nope.py:5 lost\n"
        "external PATCHES.md:28 skip\n"
        "url https://host/x.py:99 not-an-anchor\n"
        "cjk-glue ④docs/note.md:2 resolves\n"
        "bare :77 token counted not verified\n",
        encoding="utf-8",
    )
    return src


def _statuses(rows: list[ag.Row]) -> dict[str, str]:
    return {r.anchor.span: r.status for r in rows}


def test_parse_and_verdicts(tmp_path: Path) -> None:
    src = _mini_repo(tmp_path)
    summary, rows = ag.run((str(src),), tmp_path)
    st = _statuses(rows)
    assert st["scripts/tool.py:10"] == ag.STATUS_HIT
    assert st["tool.py:31"] == ag.STATUS_DRIFTED  # basename->scripts/tool.py, 31>30
    assert st["scripts/tool.py:1-3"] == ag.STATUS_HIT
    assert st["nope.py:5"] == ag.STATUS_LOST
    assert st["PATCHES.md:28"] == ag.STATUS_EXTERNAL
    assert st["docs/note.md:2"] == ag.STATUS_HIT  # ④ glue not in path
    assert "x.py:99" not in st  # URL tail never an anchor
    assert summary["anchors"] == 6
    assert summary[ag.STATUS_HIT] == 3
    assert summary[ag.STATUS_DRIFTED] == 1
    assert summary[ag.STATUS_LOST] == 1
    assert summary[ag.STATUS_EXTERNAL] == 1
    assert summary["bare"] == 1  # ':77' counted, never verified


def test_ambiguous_basename_is_lost(tmp_path: Path) -> None:
    for sub in ("a", "b"):
        (tmp_path / sub).mkdir()
        (tmp_path / sub / "dup.py").write_text("x\n", encoding="utf-8")
    src = tmp_path / "ledger.md"
    src.write_text("cite dup.py:1\n", encoding="utf-8")
    summary, rows = ag.run((str(src),), tmp_path)
    assert summary[ag.STATUS_LOST] == 1
    assert "ambiguous" in rows[0].detail


def test_fix_diagnose_only_writes_nothing(tmp_path: Path, capsys) -> None:
    src = _mini_repo(tmp_path)
    before = src.read_bytes()
    rc = ag.main(["--fix", "--src", str(src)], repo=tmp_path)
    assert rc == 0  # fail-soft: --fix never escalates, never writes
    assert src.read_bytes() == before
    out = capsys.readouterr().out
    assert "diagnose-only" in out


def test_strict_exit_codes(tmp_path: Path) -> None:
    src = _mini_repo(tmp_path)
    assert ag.main(["--src", str(src)], repo=tmp_path) == 0  # drifted, soft
    assert ag.main(["--strict", "--src", str(src)], repo=tmp_path) == 1
    clean = tmp_path / "clean.md"
    clean.write_text("fine scripts/tool.py:5\n", encoding="utf-8")
    assert ag.main(["--strict", "--src", str(clean)], repo=tmp_path) == 0


def test_repo_anchor_baseline() -> None:
    """Live pin: real ledgers — no drift, lost set == frozen baseline."""
    summary, rows = ag.run(ag.DEFAULT_SOURCES, _REPO)
    bad = tuple(
        sorted(
            (
                r.anchor.src,
                r.anchor.src_line,
                r.anchor.target,
                r.anchor.start,
                r.anchor.end,
                r.status,
            )
            for r in rows
            if r.status in (ag.STATUS_DRIFTED, ag.STATUS_LOST)
        )
    )
    assert bad == KNOWN_BAD
    assert summary[ag.STATUS_DRIFTED] == 0
    assert summary["anchors"] >= len(KNOWN_BAD) + 80  # measured 84 on 2026-11-14
