# evals/ — Evaluation System Map

Aionis's evaluation surface is **not** a fabricated golden-case set. It is the
project's real anti-leakage discipline, composed of four artifacts that already
exist elsewhere in the repo. This directory *maps* them and reserves space for
future labeled fixtures.

## The four-part eval surface

| Part | Role | Lives at |
|---|---|---|
| **Pre-registration** | The spec — one falsifiable, two-tailed claim per phase | `../docs/phase-*-preregistration.md` |
| **Verdict log** | Append-only ledger of frozen-config sha + OOS verdict; a `config_committed` row is written **before** any out-of-sample result is observed | `../runs/ledger.jsonl` |
| **Regression suite** | Hermetic pytest suite (no network, no real keys) | `../tests/` (run via `regression/`) |
| **Reproducibility** | H6 determinism (`n_jobs=1`, all seeds=0, version-pinned → IC series AND raw scores bit-identical across reruns) **plus** `config_committed`-before-result | asserted in `../tests/test_determinism.py`, enforced via the ledger |

A headline cannot be "rerun-to-significance" rescued: a changed config is a new
ledger row, never a silent overwrite.

## 4-layer QA ladder

Every change climbs these rungs in order (the project's standard review flow):

1. **Deterministic checks** — `uv run pytest -q`, `ruff`, H6 determinism assertion.
2. **Behavioral acceptance** — the phase's pre-registered primary metric
   (differential rank-IC, DM-p, CI) computed against the frozen config.
3. **Model review** — model/feature-leakage review against the anti-leakage
   identity (PIT data, PurgedGroupKFold + embargo, bundle-shuffle placebo).
4. **Human gate** — explicit human sign-off before a phase is declared done/null.

## Subdirectory purpose

| Dir | Holds |
|---|---|
| `cases/` | Labeled inputs (fixtures) for future golden-case sets |
| `expected/` | Expected outputs paired with `cases/` |
| `results/` | Captured run outputs from eval runs |
| `regression/` | Pointer to the hermetic suite at `../tests/` |

`cases/`, `expected/`, and `results/` are **placeholders**. The first concrete
golden-case set is anticipated for **E3 forward-live** (commit-then-reveal
fixtures, where forward = no future to leak by construction).

## See also

- `../docs/phase-*-preregistration.md` — the per-phase spec
- `../runs/ledger.jsonl` — the append-only verdict + config log
- `../tests/` — the hermetic regression suite
- `../CONTRIBUTING.md` — ledger / config-lineage rules
- `../docs/05-acceptance.md` — acceptance criteria *(forward ref)*
- `../WORKFLOW.md` — review flow *(forward ref)*
