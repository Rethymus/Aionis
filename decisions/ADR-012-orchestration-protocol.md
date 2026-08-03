# ADR-012: Aionis multi-agent orchestration protocol (supervisor + worker lanes, denoised handoff, task-file-as-issue)

**Status**: ACCEPTED (owner decision, 2026-08-03)
**Date**: 2026-08-03
**Supersedes**: none (operationalizes `../WORKFLOW.md` §8/§10; resolves the 2026-08-03 owner directive on orchestration)

## Context

- 2026-08-03 owner directive: implement a main-agent orchestration + acceptance harness with
  (a) a high-tier model as **low-frequency supervisor** (监工), (b) **task dispatch to other
  (cheaper) models**, (c) dedicated **review** and **e2e** sessions, (d) **denoised** cross-session
  information transfer, (e) **issue-based** task orchestration.
- Existing primitives already cover the conceptual model — this ADR binds them, it does not invent:
  - `../WORKFLOW.md` §8 defines the single-Orchestrator + on-demand specialist topology
    (Researcher / Planner / Engineer / Verifier / Reviewer); §10 defines the 6-layer context
    assembly; §16 the review scope.
  - OMC ships the agent pool (`executor` sonnet, `verifier`, `code-reviewer`, `architect`/`critic`
    opus, `qa-tester`/`test-engineer`, `general-purpose` haiku) and the `team` / `ultrawork` skills.
  - Aionis already uses local `tasks/active/*.md` files with a machine-checkable contract (RD-01
    `../scripts/check_task_contracts.py`) and `state/{current,handoff}.md` for cross-session handoff.
- Binding operational lessons (Wave-A/B + memory):
  - **Parallel-writer race** (memory `aionis-parallel-writer-race`): ≥2 concurrent writer subagents
    in the shared tree lose untracked deliverables. Writers MUST be serialized, or run in isolated
    git worktrees (OMC `TEAM-WORKTREE-MODE`).
  - **`[1210]` proxy cap**: 3-parallel spawns fail; dispatch ≤2 concurrent. A single retry recovers
    transient `[1210]` Reviewer errors — it is NOT the 5h cap (memory `aionis-no-rate-limit-check`).
  - **Model-tier dispatch** (memory `aionis-model-tier-dispatch-policy`): opus = hard
    analysis/decision/review; sonnet = standard code; haiku = mechanical. Routing is fixed
    (`ANTHROPIC_DEFAULT_OPUS_MODEL=claude-opus-4-8`, no `[1M]` suffix). The session carries `[1m]`,
    so every Agent call MUST pass a tier alias (`opus`/`sonnet`/`haiku`).
  - **No-disposable artifacts** (ADR-006): durable registry + append-only ledger + H6 determinism,
    not single-run ceremony — the orchestration protocol is itself a durable, tracked artifact.

## Decision

Codify the **Aionis Orchestration Protocol** — operational spec:
[`../docs/orchestration-protocol.md`](../docs/orchestration-protocol.md) — that binds the above
primitives into a reproducible supervisor-worker pattern, with Aionis's anti-leakage guardrails
injected into every worker dispatch.

**Local task files ARE the issues** (owner decision 2026-08-03: zero GitHub surface). This minimizes
the "治理复杂度 > 产出" drift flagged in the 2026-08-02 strategic review and keeps the durable local
convention (`tasks/*.md` already carries ID / status / priority / size / risk / acceptance /
allowed+forbidden files / required tests — full ticket semantics).

### Lane model

| Lane | Agent / model | Frequency | Writes | Stop condition |
|------|---------------|-----------|--------|----------------|
| Orchestrator | opus (this session) | per wave | `state/handoff.md`, task `状态` line, dispatch contracts | wave acceptance gate passed |
| Supervisor (监工) | opus — `architect` / `critic` | **low-freq, gates only** | decision packet, review verdict | verdict emitted |
| Worker | sonnet `executor` / haiku `general-purpose` | per task | only the task's `允许修改` files | task acceptance met |
| Verifier (验收) | sonnet/haiku `verifier` | per task, independent | `PASS`/`FAIL`/`BLOCKED` + evidence | objective verdict |
| Reviewer | sonnet `code-reviewer` | per task, diff-only | `APPROVE`/`REQUEST CHANGES`/`BLOCKED` | blocking issues listed |
| E2E | sonnet `qa-tester`/`test-engineer` | pre-push / real wave | e2e report | green suite + ledger 0-diff |

> Orchestrator and Supervisor are both opus but **different roles**: the Orchestrator runs the wave
> (read state → slice → dispatch → gate); the Supervisor is invoked **only at decision/escalation
> gates** — that is the "low-frequency monitoring". Routing every worker step through the Supervisor
> would defeat the token economy (WORKFLOW §11).

### Denoising (cross-session information transfer)

- Every dispatch carries ONLY the WORKFLOW §10 **6 layers** (stable rules / role / task / state /
  relevant evidence / output format). **Forbidden in a dispatch**: full chat, stale rejected
  options, whole repo, unfiltered logs, completed-task bodies, repeated rule text (§13 anti-drift).
- Workers return a **structured result** (files changed / tests / evidence / risks / next-action),
  never a narrative. The Orchestrator writes the structured summary into `state/handoff.md` + the
  task `状态` line via **incremental update** (not re-summarization — §11.5 anti-collapse).
- Helper: [`../scripts/orchestrate_dispatch.py`](../scripts/orchestrate_dispatch.py) turns a task
  file into a ready dispatch contract (reuses RD-01 `check_task_contracts.lint_task_file` for
  validation). Hermetic: no network, no writes, `--dry-run` is the default behavior.

### Anti-leakage guardrails (binding on every worker dispatch)

- Workers MUST NOT run real network / LLM / forward / confirmatory / strategy / horizon scripts.
- Workers MUST NOT touch frozen surfaces: prereg / ADR / config / `runs/ledger.jsonl` / results /
  data / forward are read-only to workers.
- `config_committed` BEFORE result; `runs/ledger.jsonl` 0-diff is a hard acceptance gate.
- Writers are SERIALIZED (one Engineer per dispatch) or worktree-isolated.
- Dispatch ≤2 concurrent (proxy cap); single retry on transient `[1210]`.

## Candidates considered

1. **Bind existing OMC primitives + Aionis guardrails (chosen).** Reuse WORKFLOW §8/§10, RD-01
   checker, OMC agents/skills, existing `state/`+`tasks/` convention. Zero new framework, zero new
   dependency, zero new external surface.
2. Build a bespoke orchestration runner (rejected — violates reuse-first mandate, memory
   `aionis-reuse-first-mandate`; duplicates `team`/`ultrawork`/`epic-*`).
3. Adopt GitHub Issues as the task backbone via OMC `epic-sync` (rejected by owner 2026-08-03 —
   adds sync governance overhead contra the "治理复杂度 ≤ 产出" invariant; local files already carry
   full ticket semantics).

## Evidence / cost

- Reuses WORKFLOW.md, RD-01 checker, OMC agents/skills, existing state/ + tasks/ convention.
- Cost: ~5 new tracked files (this ADR, protocol doc, dispatch template, helper + test) + 2 registry
  edits (ADR index, CLAUDE.md see-also). No frozen surface touched; no real network/LLM/data/trial.

## Applicability bounds

- Applies to all multi-agent waves on Aionis. Single-trivial ops (typo, one-line read) stay
  direct-write per the OMC allow-list. The Supervisor lane is opus-only because this session is
  opus; sonnet-tier sessions downgrade "supervisor" to the strongest available tier at gate points.
- This protocol governs the *research-harness engineering workflow*, NOT the stock-selection signal
  itself (multi-agent inference is not part of the headline — `../state/current.md`).

## Re-evaluation trigger

Re-open this ADR if ANY of:
- A wave run under this protocol reproduces a parallel-writer loss → enforce worktree isolation
  unconditionally (demote "serialized" to fallback).
- The `[1210]` proxy limit or the `[1m]` subagent resolver constraint changes.
- The owner decides to add cross-session GitHub visibility → adopt the `epic-sync` hybrid; this
  ADR's "local-only" choice is then superseded (pointed back), not silently reversed.
- A lane is observed to add governance overhead without quality gain for two consecutive waves →
  trim per the "治理复杂度 ≤ 产出" invariant.
