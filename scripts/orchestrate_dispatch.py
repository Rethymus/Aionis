#!/usr/bin/env python
"""Emit a denoised 6-layer dispatch contract for an Aionis task file.

Turns ``tasks/active/<TASK-ID>-*.md`` into a ready-to-paste dispatch context for one lane
(``executor`` / ``verifier`` / ``code-reviewer`` / ``qa-tester`` / ``supervisor``), per
ADR-012 and ``docs/orchestration-protocol.md`` §3.

Reuse, not reimplementation: task validation delegates to the RD-01 contract checker
``scripts/check_task_contracts.lint_task_file`` (single source of truth for the task contract).

Hermetic: no network, no writes (stdout only). ``--dry-run`` is the default and only
behaviour — the flag exists so the intent is explicit in logs; redirect stdout to capture.

Exit codes
---------
0  contract emitted (advisory reasons, if any, printed to stderr).
2  BLOCKING lint reason — do NOT dispatch (missing field / Size=L / owner-gated / parse error).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# scripts/ are thin runners, not a package — add this dir to sys.path so the RD-01
# checker can be imported. Inline on purpose (this is a runner, not a library).
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from check_task_contracts import lint_task_file, parse_task_file  # noqa: E402, I001


# Lane -> (model tier, role text, stop condition). Mirrors docs/orchestration-protocol.md §1.
LANE_ROLES: dict[str, dict[str, str]] = {
    "executor": {
        "tier": "sonnet",
        "role": "Worker (Engineer) — implement the task's minimal necessary change.",
        "stop": "task acceptance met + specified tests green + handoff updated",
    },
    "verifier": {
        "tier": "sonnet",
        "role": "Verifier (验收) — independently run the acceptance gate against real state.",
        "stop": "objective PASS / FAIL / BLOCKED verdict with deterministic evidence",
    },
    "reviewer": {
        "tier": "sonnet",
        "role": "Code Reviewer — inspect the diff only (WORKFLOW §16).",
        "stop": "APPROVE / REQUEST CHANGES / BLOCKED with blocking issues listed",
    },
    "e2e": {
        "tier": "sonnet",
        "role": "E2E — full hermetic suite + frozen-surface audit.",
        "stop": "green pytest + ruff clean + ledger 0-diff + frozen-surface empty",
    },
    "supervisor": {
        "tier": "opus",
        "role": "Supervisor (监工) — low-frequency decision / escalation gate only.",
        "stop": "decision packet or review verdict emitted",
    },
}

# Reason-code prefixes that forbid dispatch. DANGEROUS_COMMAND_DECLARED is advisory —
# the task merely *mentions* dangerous commands in its forbidden list (informational).
BLOCKING_PREFIXES: tuple[str, ...] = (
    "MISSING_REQUIRED_FIELD",
    "SIZE_L_FORBIDDEN",
    "PARSE_ERROR",
    "OWNER_GATE_DECLARED",
)

_STABLE_GUARDRAILS = (
    "- Offline / hermetic ONLY. No real network / LLM / forward / confirmatory / "
    "strategy / horizon scripts.\n"
    "- Frozen surfaces are read-only: prereg / ADR / config / runs/ledger.jsonl / "
    "results / data / forward.\n"
    "- config_committed BEFORE result. runs/ledger.jsonl 0-diff unless this task is a "
    "ledger-write.\n"
    "- Stay within the task's 允许修改. Do NOT expand scope, rewrite unrelated modules, "
    "or skip tests.\n"
    "- No TODO / test.skip / .only / stub / unimplemented branch — blockers, not progress."
)

_OUTPUT_FORMAT = (
    "files changed: <list>\n"
    "tests:         <command + pass/fail counts>\n"
    "evidence:      <deterministic proof — command output / assertion / artifact path>\n"
    "risks:         <list, or none>\n"
    "blockers:      <list, or none>\n"
    "next action:   <one line>"
)


def partition_reasons(reasons: list[str]) -> tuple[list[str], list[str]]:
    """Split lint reasons into (blocking, advisory). Input order preserved."""
    blocking: list[str] = []
    advisory: list[str] = []
    for reason in reasons:
        prefix = reason.split(":", 1)[0].split("|", 1)[0]
        (blocking if prefix in BLOCKING_PREFIXES else advisory).append(reason)
    return blocking, advisory


def _split_paths(text: str) -> list[str]:
    """Split a 允许修改/禁止修改-style field into clean path tokens (backticks stripped)."""
    tokens: list[str] = []
    for raw in re.split(r"[,、\n]", text):
        clean = raw.strip().strip("`").strip()
        if clean:
            tokens.append(clean)
    return tokens


def _bullets(paths: list[str]) -> str:
    if not paths:
        return "  - (none declared)\n"
    return "".join(f"  - {p}\n" for p in paths)


def build_contract(task_path: Path, lane: str, fields: dict[str, str]) -> str:
    """Build the 6-layer markdown dispatch contract from parsed task fields."""
    role = LANE_ROLES[lane]
    task_id = fields.get("编号", task_path.stem)
    title = fields.get("标题", "")
    acceptance = fields.get("验收标准", "<missing 验收标准>")
    tests = fields.get("必须运行的测试", "<missing 必须运行的测试>")
    allowed = _bullets(_split_paths(fields.get("允许修改", "")))
    forbidden = fields.get("禁止修改", "<missing 禁止修改>")

    return (
        f"# Dispatch Contract — {task_id} → {lane}\n\n"
        "## L1 — Stable rules (anti-leakage, binding)\n"
        f"{_STABLE_GUARDRAILS}\n\n"
        "## L2 — Role\n"
        f"You are the **{lane}**. Model tier: **{role['tier']}**.\n"
        f"{role['role']}\n"
        f"Stop when: {role['stop']}.\n\n"
        "## L3 — Task\n"
        f"- File: `{task_path}`\n"
        f"- Title: {title}\n"
        f"- Acceptance (验收标准): {acceptance}\n"
        f"- Required tests (必须运行的测试): {tests}\n\n"
        "## L4 — State\n"
        "- `state/current.md` (read pointer — do not load full body into the worker).\n"
        "- Relevant `state/handoff.md` slice (current round only): "
        "<!-- Orchestrator: paste the current-round slice -->\n\n"
        "## L5 — Relevant evidence (by path:lines, not repo dump)\n"
        "- Allowed files (允许修改) — candidate paths:\n"
        f"{allowed}"
        "  <!-- Orchestrator: add the specific path:lines the worker actually needs -->\n"
        f"- Forbidden (禁止修改): {forbidden}\n\n"
        "## L6 — Output format (structured, no narrative)\n"
        "Return EXACTLY this shape:\n\n"
        "```\n"
        f"{_OUTPUT_FORMAT}\n"
        "```\n"
    )


def build_contract_dict(task_path: Path, lane: str, fields: dict[str, str]) -> dict[str, object]:
    """Build the contract as a deterministic, JSON-serialisable dict."""
    role = LANE_ROLES[lane]
    return {
        "task_id": fields.get("编号", task_path.stem),
        "task_file": str(task_path),
        "lane": lane,
        "model_tier": role["tier"],
        "role": role["role"],
        "stop": role["stop"],
        "acceptance": fields.get("验收标准", ""),
        "required_tests": fields.get("必须运行的测试", ""),
        "allowed_files": _split_paths(fields.get("允许修改", "")),
        "forbidden_files": fields.get("禁止修改", ""),
        "layers": {
            "L1_stable_rules": "anti-leakage guardrails (docs/orchestration-protocol.md §4)",
            "L2_role": f"{role['role']} tier={role['tier']} stop={role['stop']}",
            "L3_task": f"{task_path} + 验收标准 + 必须运行的测试",
            "L4_state": "state/current.md pointer + state/handoff.md current-round slice",
            "L5_evidence": "path:lines the worker actually needs (Orchestrator-filled)",
            "L6_output": "structured result (files/tests/evidence/risks/blockers/next)",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Emit a denoised 6-layer dispatch contract for an Aionis task file.",
    )
    parser.add_argument("--task", type=Path, required=True, help="Path to tasks/active/<TASK>.md.")
    parser.add_argument(
        "--lane",
        choices=list(LANE_ROLES),
        default="executor",
        help="Target lane (default: executor).",
    )
    parser.add_argument(
        "--format",
        choices=["md", "json"],
        default="md",
        help="Output format (default: md).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="No-op flag: the helper never writes files (stdout only); exists for log intent.",
    )
    args = parser.parse_args()

    task_path: Path = args.task
    if not task_path.exists():
        print(f"Error: task file not found: {task_path}", file=sys.stderr)
        return 2

    # Reuse RD-01 validation — DRY, single source of truth for the task contract.
    blocking, advisory = partition_reasons(lint_task_file(task_path))
    if blocking:
        print("BLOCKING — dispatch refused:", file=sys.stderr)
        for reason in blocking:
            print(f"  {reason}", file=sys.stderr)
        return 2
    for reason in advisory:
        print(f"advisory: {reason}", file=sys.stderr)

    fields, parse_errors = parse_task_file(task_path)
    if parse_errors:
        print(f"BLOCKING — parse error: {parse_errors}", file=sys.stderr)
        return 2

    if args.format == "json":
        contract = build_contract_dict(task_path, args.lane, fields)
        print(json.dumps(contract, ensure_ascii=False, sort_keys=True))
    else:
        print(build_contract(task_path, args.lane, fields))
    return 0


if __name__ == "__main__":
    sys.exit(main())
