# Dispatch Contract — `<TASK-ID>` → `<lane>`

> Fill ONE contract per dispatched lane. This is the **only** context the worker receives
> (WORKFLOW §10; ADR-012 §3). Denoise: no full chat, no stale rejected options, no repo dump.
> Generate the skeleton with:
> `uv run python scripts/orchestrate_dispatch.py --task tasks/active/<TASK-ID>-*.md --lane <lane>`

## L1 — Stable rules (anti-leakage, binding)

- Offline / hermetic ONLY. No real network / LLM / forward / confirmatory / strategy / horizon scripts.
- Frozen surfaces are read-only: prereg / ADR / config / `runs/ledger.jsonl` / results / data / forward.
- `config_committed` BEFORE result. `runs/ledger.jsonl` 0-diff unless this task is a ledger-write.
- Stay within the task's `允许修改`. Do NOT expand scope, rewrite unrelated modules, or skip tests.
- No `TODO` / `test.skip` / `.only` / stub / unimplemented branch — these are blockers, not progress.

## L2 — Role

You are the **`<lane>`** (`executor` | `verifier` | `code-reviewer` | `qa-tester` | `supervisor`).
Model tier: **`<opus|sonnet|haiku>`**. Do only this lane's job. Stop when `<lane stop condition>`.

## L3 — Task

- File: `tasks/active/<TASK-ID>-*.md`
- Acceptance (`验收标准`): `<paste>`
- Required tests (`必须运行的测试`): `<paste>`

## L4 — State

- `state/current.md` (read pointer — do not load full body into the worker).
- Relevant `state/handoff.md` slice (current round only): `<paste slice>`

## L5 — Relevant evidence (by `path:lines`, not repo dump)

- `<file:path:lines>` — `<why relevant>`
- `<file:path:lines>` — `<why relevant>`

## L6 — Output format (structured, no narrative)

Return EXACTLY this shape:

```
files changed: <list>
tests:         <command + pass/fail counts>
evidence:      <deterministic proof — command output / assertion / artifact path>
risks:         <list, or none>
blockers:      <list, or none>
next action:   <one line>
```
