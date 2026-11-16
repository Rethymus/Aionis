"""Hermetic tests for scripts/backup_audit_chain.py (prune helper).

Owner mission bundle-keep2-rolling (2026-11-16): bundle retention keep=2
(automates the 2026-11-16 evening manual cleanup 29 bundles 2.4G -> 2 / 410M);
ledger retention keep=30 unchanged. tmp-isolated: zero network, zero git.
"""
from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(_SCRIPTS))

import backup_audit_chain as bac  # noqa: E402


def _mk(path: Path) -> None:
    path.write_bytes(b"x")


def test_prune_sorted_keeps_newest_two(tmp_path: Path) -> None:
    names = [
        "repo-bundle-20260101-000001.bundle",
        "repo-bundle-20260102-000002.bundle",
        "repo-bundle-20260103-000003.bundle",
    ]
    for name in names:
        _mk(tmp_path / name)
    doomed = bac.prune_sorted(tmp_path, "repo-bundle-*.bundle", keep=2)
    assert [p.name for p in doomed] == [names[0]]
    remaining = sorted(p.name for p in tmp_path.glob("repo-bundle-*.bundle"))
    assert remaining == names[1:]


def test_prune_sorted_noop_when_at_or_under_keep(tmp_path: Path) -> None:
    pair = ["repo-bundle-20260101-000001.bundle", "repo-bundle-20260102-000002.bundle"]
    for name in pair:
        _mk(tmp_path / name)
    assert bac.prune_sorted(tmp_path, "repo-bundle-*.bundle", keep=2) == []
    assert sorted(p.name for p in tmp_path.iterdir()) == pair


def test_prune_sorted_pattern_scoped(tmp_path: Path) -> None:
    _mk(tmp_path / "repo-bundle-20260101-000001.bundle")
    _mk(tmp_path / "ledger-20260101-000001.jsonl")
    assert bac.prune_sorted(tmp_path, "repo-bundle-*.bundle", keep=2) == []
    assert len(list(tmp_path.iterdir())) == 2  # the other pattern stays untouched


def test_prune_sorted_keep_zero_deletes_all(tmp_path: Path) -> None:
    _mk(tmp_path / "repo-bundle-20260101-000001.bundle")
    doomed = bac.prune_sorted(tmp_path, "repo-bundle-*.bundle", keep=0)
    assert len(doomed) == 1
    assert not list(tmp_path.iterdir())
