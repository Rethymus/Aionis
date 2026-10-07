"""Hermetic tests for scripts/precommit_guard.py (rule logic only — no git)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "precommit_guard.py"


def _load():
    spec = importlib.util.spec_from_file_location("precommit_guard", SCRIPT)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_data_dir_parquet_env_flagged(tmp_path, monkeypatch) -> None:
    g = _load()
    monkeypatch.chdir(tmp_path)
    problems = g._violations([
        "data/cache/AAA.parquet",       # data/ AND parquet — two rules
        "results/scores.parquet",       # parquet anywhere
        ".env",                         # secrets
        "src/aionis/cli.py",
    ])
    joined = "\n".join(problems)
    assert "data/" in joined
    assert "*.parquet" in joined
    assert ".env" in joined
    assert "src/aionis/cli.py" not in joined  # clean file stays unflagged


def test_size_cap_only_for_existing_files(tmp_path, monkeypatch) -> None:
    g = _load()
    # the guard resolves paths against its module ROOT — repoint it at the sandbox
    monkeypatch.setattr(g, "ROOT", tmp_path)
    big = tmp_path / "reports" / "big.bin"
    big.parent.mkdir()
    big.write_bytes(b"x" * (g.MAX_STAGED_BYTES + 1))
    problems = g._violations(["reports/big.bin", "runs/missing.parquet"])
    assert any("staged-size cap" in p for p in problems)
    # missing files must not crash the guard (rename/move in the same commit)
    assert any("parquet" in p for p in problems)


def test_env_example_template_is_allowed(tmp_path, monkeypatch) -> None:
    g = _load()
    monkeypatch.setattr(g, "ROOT", tmp_path)
    problems = g._violations([".env.example", ".env.production"])
    assert problems == [".env.production: env file — secrets — never commit"]


def test_staged_filter_includes_modified(tmp_path, monkeypatch) -> None:
    """--diff-filter must keep M: modifications (e.g. un-ignoring data/,
    editing a tracked large file) are as dangerous as additions."""
    g = _load()
    captured: dict[str, list[str]] = {}

    class _FakeRun:
        def __init__(self, stdout=""): self.stdout = stdout
        def run(self, cmd, **k):
            captured["cmd"] = cmd
            return _FakeRun(stdout="src/aionis/cli.py\n")

    fake = _FakeRun()
    monkeypatch.setattr(g.subprocess, "run", fake.run)
    files = g._staged_files()
    assert files == ["src/aionis/cli.py"]
    assert "--diff-filter=ACMR" in captured["cmd"], (
        "staged filter must include M (modified) — the ACR variant silently "
        "skips edits to tracked files"
    )
