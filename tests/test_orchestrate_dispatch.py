"""Tests for ``scripts/orchestrate_dispatch.py`` (ADR-012 dispatch-contract emitter).

Hermetic: all task fixtures are built in ``tmp_path``; no repo task files are read or written.
The helper is loaded via ``importlib`` from its file path (scripts/ is not a package).
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "orchestrate_dispatch.py"


def _load_helper() -> object:
    spec = importlib.util.spec_from_file_location("orchestrate_dispatch", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


HELPER = _load_helper()


VALID_TASK = """\
# ORCH-TEST-01 — demo task

- 编号: ORCH-TEST-01
- 标题: Demo task for dispatch helper.
- 状态: owner-authorized via /goal 2026-08-03 (P0).
- Priority: P0
- Size: S
- Risk: LOW
- 目标: Demonstrate the dispatch-contract emitter end to end.
- 允许修改: scripts/foo.py, tests/test_foo.py.
- 禁止修改: frozen prereg/ADR/config/ledger/results/data.
- 前置条件: owner authorization recorded in the 状态 line.
- 验收标准: helper emits a 6-layer contract; pytest green.
- 必须运行的测试: uv run pytest -q tests/test_foo.py.
"""


def _write_task(tmp_path: Path, body: str) -> Path:
    task = tmp_path / "TASK-ORCH-TEST-01.md"
    task.write_text(body, encoding="utf-8")
    return task


def _run_cli(task: Path, lane: str, fmt: str) -> int:
    env = {"PYTHONDONTWRITEBYTECODE": "1", **os.environ}
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--task", str(task), "--lane", lane, "--format", fmt],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    return proc.returncode


def test_md_contract_has_all_six_layers(tmp_path):
    task = _write_task(tmp_path, VALID_TASK)
    fields, _ = HELPER.parse_task_file(task)  # type: ignore[attr-defined]
    out = HELPER.build_contract(task, "executor", fields)  # type: ignore[attr-defined]
    for marker in (
        "# Dispatch Contract",
        "## L1 — Stable rules",
        "## L2 — Role",
        "## L3 — Task",
        "## L4 — State",
        "## L5 — Relevant evidence",
        "## L6 — Output format",
    ):
        assert marker in out
    assert "ORCH-TEST-01" in out
    assert "sonnet" in out  # executor = sonnet tier
    assert "scripts/foo.py" in out  # allowed path surfaced as evidence


def test_json_contract_is_deterministic_and_supervisor_is_opus(tmp_path):
    task = _write_task(tmp_path, VALID_TASK)
    fields, _ = HELPER.parse_task_file(task)  # type: ignore[attr-defined]
    d = HELPER.build_contract_dict(task, "supervisor", fields)  # type: ignore[attr-defined]
    assert d["lane"] == "supervisor"
    assert d["model_tier"] == "opus"  # supervisor = opus (low-freq 监工)
    assert d["task_id"] == "ORCH-TEST-01"
    assert d["allowed_files"] == ["scripts/foo.py", "tests/test_foo.py."]
    # sorted-keys round-trip is stable
    serialised = json.dumps(d, ensure_ascii=False, sort_keys=True)
    assert json.loads(serialised)["task_id"] == "ORCH-TEST-01"


def test_partition_reasons_separates_blocking_from_advisory():
    reasons = [
        "MISSING_REQUIRED_FIELD:目标|x",
        "SIZE_L_FORBIDDEN|x|Size=L",
        "OWNER_GATE_DECLARED|x|owner-gated",
        "PARSE_ERROR:boom",
        "DANGEROUS_COMMAND_DECLARED|x|phase_.py",
    ]
    blocking, advisory = HELPER.partition_reasons(reasons)  # type: ignore[attr-defined]
    assert len(blocking) == 4
    assert advisory == ["DANGEROUS_COMMAND_DECLARED|x|phase_.py"]


def test_cli_clean_task_emits_contract_exit_0(tmp_path):
    task = _write_task(tmp_path, VALID_TASK)
    assert _run_cli(task, "executor", "md") == 0


def test_cli_json_format_exit_0(tmp_path):
    task = _write_task(tmp_path, VALID_TASK)
    assert _run_cli(task, "verifier", "json") == 0


def test_cli_blocking_missing_field_exit_2(tmp_path):
    body = VALID_TASK.replace(
        "- 目标: Demonstrate the dispatch-contract emitter end to end.\n", ""
    )
    task = _write_task(tmp_path, body)
    assert _run_cli(task, "executor", "md") == 2


def test_cli_blocking_size_l_exit_2(tmp_path):
    body = VALID_TASK.replace("- Size: S", "- Size: L")
    task = _write_task(tmp_path, body)
    assert _run_cli(task, "executor", "md") == 2


def test_cli_blocking_owner_gated_exit_2(tmp_path):
    body = VALID_TASK.replace(
        "- 状态: owner-authorized via /goal 2026-08-03 (P0).",
        "- 状态: owner-gated; awaiting owner GO.",
    )
    task = _write_task(tmp_path, body)
    assert _run_cli(task, "executor", "md") == 2


def test_cli_advisory_dangerous_command_still_dispatches(tmp_path):
    # 禁止修改 mentions a dangerous pattern -> DANGEROUS_COMMAND_DECLARED (advisory, not blocking).
    body = VALID_TASK.replace(
        "- 禁止修改: frozen prereg/ADR/config/ledger/results/data.",
        "- 禁止修改: do not run phase_b_run.py / strategy / forward scripts.",
    )
    task = _write_task(tmp_path, body)
    assert _run_cli(task, "executor", "md") == 0


def test_cli_is_hermetic_no_file_writes(tmp_path):
    task = _write_task(tmp_path, VALID_TASK)
    before = {p: p.stat().st_mtime for p in tmp_path.rglob("*") if p.is_file()}
    _run_cli(task, "executor", "md")
    after = {p: p.stat().st_mtime for p in tmp_path.rglob("*") if p.is_file()}
    assert before == after


def test_cli_missing_task_file_exit_2(tmp_path):
    rc = _run_cli(tmp_path / "does-not-exist.md", "executor", "md")
    assert rc == 2
