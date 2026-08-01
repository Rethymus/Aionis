#!/usr/bin/env python
"""
Deterministic task contract linter for Aionis active tasks.

This script parses markdown task files in tasks/active/ and reports per-file
reason codes for contract violations. It is a static checker only—no execution,
no network calls, no modifications to existing task files.

Required fields (derived from task conventions):
  - 编号 (Task ID, e.g., RD-01, RES-01, AUD-00)
  - 标题 (Title)
  - 状态 (Status)
  - Priority (P0, P1, P2)
  - Size (S, M, L)
  - Risk (LOW, MEDIUM, HIGH, CRITICAL)
  - 目标 (Objective)
  - 允许修改 (Allowed modifications whitelist)
  - 禁止修改 (Forbidden modifications blacklist)
  - 前置条件 (Prerequisites)
  - 验收标准 (Acceptance criteria)
  - 必须运行的测试 (Required tests)

Reason codes (deterministic; sorted by code then path):
  - MISSING_REQUIRED_FIELD:{field_name}
  - SIZE_L_FORBIDDEN
  - OWNER_GATE_DECLARED
  - DANGEROUS_COMMAND_DECLARED
  - PARSE_ERROR

Output format: per-file lines with stable sorting (path, then reason code).
Each line: {reason_code}|{task_file}|{detail}

Historical tasks having findings is EXPECTED output—this tool reports
defects, it does not auto-fix them. Running on the real corpus must not crash.
"""

import argparse
import re
import sys
from pathlib import Path

# Required fields observed from task conventions
REQUIRED_FIELDS = {
    "编号",
    "标题",
    "状态",
    "Priority",
    "Size",
    "Risk",
    "目标",
    "允许修改",
    "禁止修改",
    "前置条件",
    "验收标准",
    "必须运行的测试",
}

# Dangerous command patterns (from 禁止修改 sections and task contracts)
DANGEROUS_PATTERNS = [
    r"phase.*\.py",
    r"strategy.*\.py",
    r"horizon.*\.py",
    r"forward.*\.py",
    r"phase_",
    r"strategy_",
    r"horizon_",
    r"forward_",
]


def parse_task_file(file_path: Path) -> tuple[dict[str, str], list[str]]:
    """
    Parse a task markdown file into structured fields.

    Returns:
        (fields_dict, parse_errors)
        - fields_dict: mapping of field name to value (stripped)
        - parse_errors: list of PARSE_ERROR reason strings if parsing fails
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return {}, [f"PARSE_ERROR:Cannot read file: {e}"]

    fields = {}
    lines = content.split("\n")

    # Parse frontmatter-like fields: "- field: value" format
    # This captures the task metadata at the top of each file
    for line in lines:
        line = line.strip()
        if not line.startswith("- "):
            continue
        # Match "- key: value" pattern
        match = re.match(r"-\s*([^:]+):\s*(.+)", line)
        if match:
            key = match.group(1).strip()
            value = match.group(2).strip()
            fields[key] = value

    return fields, []


def check_missing_fields(
    fields: dict[str, str], file_path: Path
) -> list[str]:
    """Check for missing required fields."""
    missing = REQUIRED_FIELDS - set(fields.keys())
    reasons = []
    for field in sorted(missing):  # Sort for determinism
        reasons.append(f"MISSING_REQUIRED_FIELD:{field}|{file_path}")
    return reasons


def check_size_l(fields: dict[str, str], file_path: Path) -> list[str]:
    """Check if Size = L (forbidden to dispatch to single agent)."""
    reasons = []
    size_value = fields.get("Size", fields.get("大小", ""))
    if size_value.upper() == "L":
        reasons.append(f"SIZE_L_FORBIDDEN|{file_path}|Size=L cannot be dispatched to single agent")
    return reasons


def check_owner_gate(fields: dict[str, str], file_path: Path) -> list[str]:
    """Check if task has owner-gate status."""
    reasons = []
    status_value = fields.get("状态", fields.get("状态", ""))
    # Look for owner-gate keywords in status
    owner_gate_indicators = ["owner-gated", "owner-gate", "owner GO", "OWNER GO"]
    if any(indicator.lower() in status_value.lower() for indicator in owner_gate_indicators):
        reasons.append(f"OWNER_GATE_DECLARED|{file_path}|Requires owner authorization")
    return reasons


def check_dangerous_commands(
    fields: dict[str, str], file_path: Path, content: str
) -> list[str]:
    """Check if dangerous commands are declared in forbidden modifications."""
    reasons = []
    forbidden = fields.get("禁止修改", fields.get("禁止修改", ""))

    # Check if dangerous patterns are mentioned in forbidden section
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, forbidden, re.IGNORECASE):
            reasons.append(f"DANGEROUS_COMMAND_DECLARED|{file_path}|Forbidden: {pattern}")
            break  # Only report once per file

    return reasons


def lint_task_file(file_path: Path) -> list[str]:
    """
    Lint a single task file and return reason codes.

    Returns:
        List of reason strings, each format: "{reason_code}|{file_path}|{detail}"
        Sorted deterministically by reason code then file path.
    """
    all_reasons = []

    # Parse the file
    fields, parse_errors = parse_task_file(file_path)
    all_reasons.extend(parse_errors)

    if parse_errors:
        # If we can't parse, don't guess—return early
        return sorted(all_reasons)

    # Read full content for dangerous command check
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception:
        content = ""

    # Run all checks
    all_reasons.extend(check_missing_fields(fields, file_path))
    all_reasons.extend(check_size_l(fields, file_path))
    all_reasons.extend(check_owner_gate(fields, file_path))
    all_reasons.extend(check_dangerous_commands(fields, file_path, content))

    # Sort for deterministic output (by reason code, then file path for stability)
    return sorted(all_reasons)


def main():
    parser = argparse.ArgumentParser(
        description="Deterministic task contract linter for Aionis active tasks"
    )
    parser.add_argument(
        "task_dir",
        type=Path,
        help="Path to tasks directory (e.g., tasks/active/)",
    )
    parser.add_argument(
        "--output-format",
        choices=["text", "csv"],
        default="text",
        help="Output format (default: text)",
    )
    args = parser.parse_args()

    if not args.task_dir.exists():
        print(f"Error: Task directory {args.task_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    # Find all .md files in the directory
    task_files = sorted(args.task_dir.glob("*.md"))

    if not task_files:
        print(f"No .md files found in {args.task_dir}")
        sys.exit(0)

    # Lint each file and collect all reasons
    all_reasons = []
    for task_file in task_files:
        reasons = lint_task_file(task_file)
        all_reasons.extend(reasons)

    # Output results
    if args.output_format == "text":
        for reason in all_reasons:
            print(reason)
    elif args.output_format == "csv":
        print("reason_code,file_path,detail")
        for reason in all_reasons:
            parts = reason.split("|", 2)
            if len(parts) == 3:
                print(f"{parts[0]},{parts[1]},{parts[2]}")
            elif len(parts) == 2:
                print(f"{parts[0]},{parts[1]},")
            else:
                print(f"{parts[0]},,")

    # Exit with non-zero if any findings (but not if parse errors only)
    # Historical findings are expected; crash is the only failure mode
    sys.exit(0)


if __name__ == "__main__":
    main()
