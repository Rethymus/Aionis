"""Workflow YAML hygiene guard (round 127) — the pytest gate for the seven
.github/workflows files, replacing the rejected scripts/check_ci_yaml.py
second entry point (ADR-006: no one-shot ceremony scripts; pyyaml is already
a base dependency, pyproject.toml pyyaml>=6.0).

Five assertion families, motivated by the 2026-11-11 environment/test-pipeline
audit (reports/audits/2026-11-11-env-testpipeline-round.md):
1. every workflow safe_loads (a YAML typo currently surfaces only as a red
   Actions run AFTER push — billing lock #2 made that feedback loop free);
2. every `uses:` is a 40-hex SHA pin — TAG refs banned (the audit found 3
   unpinned TAGs; Node 20 runner removal turned old node20 SHA pins into
   hard start failures, so pin hygiene is also runtime correctness);
3. every job runs on the deliberately pinned ubuntu-24.04 (rounds 107/108b
   ubuntu-latest→26.04 migration pin);
4. top-level permissions are explicit everywhere (no repo-default grant);
5. every schedule cron sits OFF the top-of-hour load window, and the
   staleness cron mirrors the value test_ops_deadman.py pins ('37 2 * * *').

Adding an 8th workflow updates the count pin below — the tripwire is
intentional so new files cannot bypass this gate.
"""
from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WF_DIR = ROOT / ".github" / "workflows"
WORKFLOWS = sorted(WF_DIR.glob("*.yml"))
EXPECTED_COUNT = 7

_USES_RE = re.compile(r"^[A-Za-z0-9_./-]+@[0-9a-f]{40}$")


def _load(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _on(workflow: dict[str, Any]) -> dict[str, Any]:
    # YAML 1.1: a bare `on:` parses as boolean True under pyyaml — accept
    # both spellings (same handling as test_ops_deadman.py).
    on = workflow[True] if True in workflow else workflow.get("on")
    return on or {}


def _walk_uses(node: Any) -> Iterator[str]:
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "uses" and isinstance(value, str):
                yield value
            else:
                yield from _walk_uses(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_uses(item)


def test_workflow_inventory_and_parse() -> None:
    assert len(WORKFLOWS) == EXPECTED_COUNT, (
        f"expected {EXPECTED_COUNT} workflows, found "
        f"{[p.name for p in WORKFLOWS]} — update EXPECTED_COUNT and make "
        "the new file pass the hygiene families below")
    for path in WORKFLOWS:
        assert isinstance(_load(path), dict), f"{path.name} did not parse"


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_uses_are_sha_pinned(path: Path) -> None:
    for ref in _walk_uses(_load(path)):
        assert _USES_RE.match(ref), (
            f"{path.name}: uses '{ref}' is not a 40-hex SHA pin — TAG and "
            "branch refs are banned (supply-chain + node-runtime drift)")


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_runs_on_is_pinned_ubuntu_2404(path: Path) -> None:
    for job_id, job in _load(path).get("jobs", {}).items():
        assert job.get("runs-on") == "ubuntu-24.04", (
            f"{path.name}: job '{job_id}' runs on '{job.get('runs-on')}' — "
            "pin deliberately (ubuntu-latest migrates to 26.04)")


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_permissions_are_explicit(path: Path) -> None:
    wf = _load(path)
    assert wf.get("permissions"), (
        f"{path.name}: top-level permissions missing — the implicit "
        "repo-default grant is broader than any job needs")


def test_crons_off_the_hour_and_staleness_mirror() -> None:
    seen: dict[str, str] = {}
    for path in WORKFLOWS:
        for entry in _on(_load(path)).get("schedule") or []:
            cron = str(entry["cron"]).strip()
            seen[path.name] = cron
            minute = int(cron.split()[0])
            assert minute != 0, (
                f"{path.name}: cron '{cron}' fires on the hour — GitHub "
                "docs put the highest load at the top of the hour "
                "(scikit-learn nightly runs :30 for the same reason)")
    # The staleness绊网 must stay in lockstep with the deadman test's pin.
    assert seen.get("staleness-check.yml") == "37 2 * * *", (
        "staleness-check.yml cron drifted from the test_ops_deadman.py pin "
        "'37 2 * * *' — update both together (daily 02:37 UTC, round 126)")
