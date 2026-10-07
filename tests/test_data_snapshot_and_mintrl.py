"""Hermetic tests for scripts/data_snapshot_audit.py and mintrl_diagnostic.py.

snapshot: synthetic parquet tree — baseline, then append (tolerated), history
mutation (ALARM), truncation (ALARM) — against a monkeypatched CACHE root.
mintrl: TRACKED integrity + strict-JSON guard on the committed payload (the
09-11 bare-Infinity lesson).
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture()
def snap(tmp_path, monkeypatch):
    m = _load("data_snapshot_audit", "scripts/data_snapshot_audit.py")
    cache = tmp_path / "cache"
    cache.mkdir()
    monkeypatch.setattr(m, "CACHE", cache)
    monkeypatch.setattr(m, "BASELINE", tmp_path / "baseline.json")
    monkeypatch.setattr(m, "LEDGER", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(m, "TRACKED", [
        {"name": "hist", "date_col": "date", "kind": "parquet"},
        {"name": "map", "date_col": None, "kind": "parquet"},
    ])
    return m, cache


def _write_hist(cache: Path, rows: list[tuple[str, float]]) -> None:
    df = pd.DataFrame(rows, columns=["date", "v"])
    df.to_parquet(cache / "hist.parquet", index=False)


def _write_map(cache: Path) -> None:
    pd.DataFrame({"k": ["a", "b"], "v": [1.0, 2.0]}).to_parquet(
        cache / "map.parquet", index=False)


def _run(m, argv: list[str]) -> int:
    old = sys.argv
    try:
        sys.argv = ["data_snapshot_audit.py", *argv]
        return m.main()
    finally:
        sys.argv = old


def test_snapshot_append_tolerated_history_rewrite_alarms(snap) -> None:
    m, cache = snap
    _write_hist(cache, [("2026-01-01", 1.0), ("2026-02-01", 2.0)])
    _write_map(cache)
    assert _run(m, ["--baseline"]) == 0

    # pure append -> OK (exit 0), appended rows reported
    _write_hist(cache, [("2026-01-01", 1.0), ("2026-02-01", 2.0),
                        ("2026-03-01", 3.0)])
    assert _run(m, []) == 0

    # history mutation under the baseline max date -> ALARM (exit 1)
    _write_hist(cache, [("2026-01-01", 99.0), ("2026-02-01", 2.0),
                        ("2026-03-01", 3.0)])
    assert _run(m, []) == 1

    # truncation -> ALARM
    _write_hist(cache, [("2026-01-01", 99.0)])
    assert _run(m, []) == 1


def test_mintrl_payload_is_strict_json() -> None:
    payload = ROOT / "reports" / "exploratory" / "mintrl-diagnostic.json"
    if not payload.exists():  # research-machine artifact; skip on fresh CI
        pytest.skip("mintrl payload not present on this checkout")
    raw = payload.read_text(encoding="utf-8")
    for bad in ("Infinity", "NaN", "-Infinity"):
        assert bad not in raw, f"non-strict JSON token {bad} in committed payload"
    json.loads(raw)  # standard parser accepts


def test_pbo_and_mintrl_tracked_shapes() -> None:
    m = _load("data_snapshot_audit", "scripts/data_snapshot_audit.py")
    names = [s["name"] for s in m.TRACKED]
    assert len(names) == len(set(names)), "duplicate tracked file"
    assert "phase_b_fundamentals" in names and "gdelt_news_sentiment" in names
