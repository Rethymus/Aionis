"""Hermetic tests for scripts/verify_claim.py — fixture tree, no repo state.

Builds a minimal fake ROOT (ledger rows, evidence_matrix.json, prereg docs,
runs/results dirs) and drives all four link checks through pass/skip/fail.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "verify_claim.py"


def _load():
    spec = importlib.util.spec_from_file_location("verify_claim", SCRIPT)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture()
def fx(tmp_path, monkeypatch):
    m = _load()
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "phase-b-preregistration.md").write_text(
        "prereg", encoding="utf-8")
    ledger = [
        {"ts": "2026-07-27T00:00:00+00:00", "event": "other", "config_sig": ""},
        {"ts": "2026-07-28T04:27:39+00:00", "event": "confirmatory:first",
         "config_sig": "a" * 64},
    ]
    (tmp_path / "runs").mkdir()
    (tmp_path / "runs" / "ledger.jsonl").write_text(
        "\n".join(json.dumps(r) for r in ledger) + "\n", encoding="utf-8")
    matrix = {"claims": {
        "B": {"ledger_row": 2, "prereg_doc": "docs/phase-b-preregistration.md",
              "results_sig": "a" * 64},
        "track_c": {"ledger_row": 2, "prereg_doc": "docs/track-c-preregistration.md"},
    }}
    datadir = tmp_path / "web" / "src" / "data" / "aionis"
    datadir.mkdir(parents=True)
    (datadir / "evidence_matrix.json").write_text(
        json.dumps(matrix), encoding="utf-8")
    monkeypatch.setattr(m, "ROOT", tmp_path)
    monkeypatch.setattr(m, "LEDGER", tmp_path / "runs" / "ledger.jsonl")
    monkeypatch.setattr(m, "MATRIX", datadir / "evidence_matrix.json")
    monkeypatch.setattr(m, "RESULTS", tmp_path / "runs" / "results")
    # make the sandbox a git repo so the `git ls-files` tracking check works
    subprocess.run(["git", "init", "-q"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "add", "docs/phase-b-preregistration.md"],
                   cwd=str(tmp_path), check=True)
    monkeypatch.setattr(m, "CLAIMS", {
        "B": {"prereg": "docs/phase-b-preregistration.md", "row": 2},
        "track_c": {"prereg": "docs/track-c-preregistration.md", "row": 2},
    })
    return m, tmp_path


def test_all_links_pass_with_results_dir(fx) -> None:
    m, tmp = fx
    (tmp / "runs" / "results").mkdir()
    (tmp / "runs" / "results" / ("a" * 64)).mkdir()
    rc = m.main(["B"])
    assert rc == 0


def test_walk_forward_skips_frozen(fx, capsys) -> None:
    m, tmp = fx
    doc = tmp / "docs" / "track-c-preregistration.md"
    doc.write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "docs/track-c-preregistration.md"],
                   cwd=str(tmp), check=True)
    rc = m.main(["track_c"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "walk-forward" in out and "SKIP" in out


def test_missing_results_dir_fails_for_sig_claim(fx) -> None:
    m, tmp = fx
    (tmp / "runs" / "results").mkdir()
    (tmp / "runs" / "results" / ("b" * 64)).mkdir()  # wrong sig present
    rc = m.main(["B"])
    assert rc == 1  # frozen link FAIL


def test_wrong_row_event_fails(fx) -> None:
    m, tmp = fx
    ledger = [
        {"ts": "t", "event": "exploratory", "config_sig": "a" * 64},
    ]
    (tmp / "runs" / "ledger.jsonl").write_text(
        json.dumps(ledger[0]) + "\n", encoding="utf-8")
    m.CLAIMS = {"B": {"prereg": "docs/phase-b-preregistration.md", "row": 1}}
    rc = m.main(["B"])
    assert rc >= 1
