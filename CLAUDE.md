<!--
  CLAUDE.md — Aionis project instructions for Claude Code.
  Claude Code reads this file NATIVELY (docs.anthropic.com/en/docs/claude-code/memory).
  `AGENTS.md` is a symlink to THIS file for OpenAI Codex portability — edit HERE, not there.
  Keep this file <200 lines (longer files reduce adherence). Put long procedures in
  WORKFLOW.md (referenced, NOT @import-ed, so it loads on-demand). Put git conventions in
  CONTRIBUTING.md. This HTML comment is stripped before injection into context.
-->

# Aionis — Claude Code project instructions

## Project goal
Aionis is a **falsifiable, anti-leakage** quantitative-finance research project. One
pre-registered **two-tailed** claim per phase on the **cross-sectional monthly rank-IC** of
S&P 500 **point-in-time** constituents. **Null results with tight CIs are the intended,
publishable outcome** — not a failure. Aionis is a disciplined experiment harness, NOT a
cognitive system or a trading bot.

## Inviolable constraints (anti-leakage anchors — never violate)
- **`config_committed` BEFORE result.** The frozen config's sha256 is appended to
  `runs/ledger.jsonl` *before* any out-of-sample metric is observed. Same-sig reruns are
  bit-identical (H6); a changed config is a **new ledger row**, never a silent overwrite.
  A headline cannot be "rerun-to-significance" rescued.
- **Point-in-time (PIT) data.** Fundamentals via `filed` date (not period-end); macro via
  ALFRED as-of vintages; VIXCLS unrevised (PIT via the **no-revision** contract, NOT vintage
  tracking); 13D via filing date; the S&P 500 universe via PIT membership
  (`constituents_on`), never a today-snapshot.
- **PurgedGroupKFold + embargo.** `group=month`, `embargo=21` sessions, no label leakage.
- **H6 determinism.** `n_jobs=1`, all seeds pinned to `0`, version-pinned (`uv.lock`); the
  IC series AND raw scores must be bit-identical across reruns (asserted).
- **Two-tailed, pre-registered.** Each phase has its own pre-reg (`docs/phase-*-preregistration.md`).
  The treatment-vs-fundamentals-only rank-IC **differential** is the claim.
- **7-gate data intake** (`docs/data-intake-rubric.md`): license / PIT / no-revision /
  snapshot / exploratory-only / selection-honesty / politeness.
- **Permissive licenses ONLY** (`docs/data-license-allowlist.md`): MIT / Apache / BSD.
  EXCLUDE vectorbt (Commons Clause), backtrader (GPL), mlfinlab (paid), pypbo (AGPL),
  nautilus_trader (LGPL).
- **No disposable artifacts** — durable registry, not one-shot ceremony
  (`decisions/ADR-006-no-disposable-artifacts-registry.md`).

## Provider / data-source constraints
- **LLM pool = GLM / SiliconFlow / ModelScope ONLY** (OpenAI-compatible, policy-aware
  multi-key router at `src/aionis/extraction/providers.py`). Google Gemini and Tencent
  TokenHub configs were deleted (auth blocked) — do NOT re-add or re-attempt.
- **No mock/synthetic data in the research pipeline.** The real CLI path runs on real data
  + real models. Mock/synthetic are allowed ONLY as labeled unit-test fixtures.
- **Strict token + memory control.** Cheapest model that works; bounded single retry; log
  per-call token usage. No lingering background processes.
- **Politeness is binding:** ≥2s spacing + exponential backoff on all fetches.
- **Working sources:** FRED/ALFRED, Tiingo, Alpaca, EDGAR. **Blocked:** yfinance/Yahoo, BLS,
  Stooq. 13D via EDGAR submissions (filed-date PIT).

## Tech stack
Python ≥3.10, `uv`. pandas/numpy/pyarrow, scikit-learn, **lightgbm≥4.3** (the frozen
learner), xgboost, statsmodels, **purgedcv** (PurgedGroupKFold), **arch≥8.0** (DSR/SPA),
pandas-market-calendars, pydantic(+settings), structlog, requests/bs4, praw. Dashboard:
streamlit + plotly. See `pyproject.toml`.

## Directory map
- `src/aionis/` — library: `ingest/` (PIT fetchers), `features/`, `eval/` (phase
  orchestrators + rank-IC + multiple-testing + strategy-returns + event-study + propagation),
  `extraction/` (LLM), `reporting/` (save_run/load_run), `config.py`, `cli.py`.
- `scripts/` — thin runners (`phase_{b,c,d,e1}_run.py`, `strategy_eval_run.py`,
  `sensitivity_horizon.py`, `*_fetch.py`). Most have a `PHASE_X_NO_LEDGER=1` reproducibility mode.
- `tests/` — hermetic pytest suite. `dashboard/app.py` — quant-eval UI.
- `docs/` — pre-registrations, `RESULTS.md`, theory, rubrics, numbered index (00–08).
- `decisions/` — ADRs (point-in-time, record-once). `tasks/` — active/completed/rejected.
- `evals/` `reports/` `archive/` — eval map, milestone/audit/cost reports, superseded items.
- `state/` — **tracked** operating state: `current.md` (read first each session), `handoff.md`,
  `backlog.md`, `blockers.md`.
- `runs/ledger.jsonl` — the append-only audit log (**TRACKED**). `runs/results/`, `runs/*.log`,
  `runs/*.parquet` — gitignored regenerable artifacts.
- `data/`, `*.parquet`, `.env` — **GITIGNORED** (secrets + regenerable/leakage-sensitive data).
- `.omc/` — gitignored OMC runtime store (NOT the durable handoff; use `state/`).

## Commands
```bash
uv sync --all-extras                          # install (base + extraction + dashboard + dev)
uv run pytest -q                              # hermetic tests (target: green)
uv run ruff check                             # lint (must be clean)
uv run python scripts/phase_d_run.py          # a confirmatory run (config_committed BEFORE result)
uv run python scripts/strategy_eval_run.py    # secondary L-S lens
uv run streamlit run dashboard/app.py         # the quant-eval dashboard
```
Data fetchers: `scripts/phase_b_fetch.py`, `scripts/phase_d_fetch.py` (resumable, polite).

## Session protocol (do this at the start of every session)
1. Read `state/current.md` → `state/handoff.md` → the active task in `tasks/active/`.
2. `git status --short --branch` — confirm branch + no surprises.
3. Run the lightest verification that proves the world is as described (e.g. `uv run pytest -q -x`).
4. Only then begin work.
Full pipeline (opportunity → problem → research → decision → freeze → slice → execute → verify →
review → sediment → stage-decision): see `WORKFLOW.md`.

## Agent permission boundaries (single Orchestrator + on-demand specialists)
- **Orchestrator** — reads state, picks the next step, controls budget/stop-conditions,
  updates `state/handoff.md`. Does NOT write large code or change project direction.
- **Researcher** — finds evidence, maintains an evidence table, separates Fact/Inference/
  Hypothesis. Does NOT mutate the spec.
- **Planner** — slices frozen specs into verifiable tasks (S/M/L). Does NOT implement.
- **Engineer** — implements one task, runs its tests, records evidence, updates handoff. Does
  NOT expand scope, rewrite unrelated modules, or skip tests.
- **Verifier** — independently runs tests + checks acceptance against REAL state (code/logs/
  data, not prose). Returns PASS / FAIL / BLOCKED.
- **Reviewer** — reviews only the diff (task spec + relevant code + test results + handoff).
  Returns APPROVE / REQUEST CHANGES / BLOCKED.
Model tiers by **RISK**: light (haiku) mechanical; medium (sonnet) standard code/review;
strong (opus) architecture/hard bugs/high-risk review/decisions. Reversible→light,
irreversible/high-impact→strong.

## Definition of done (a task is NOT done until ALL hold)
- Acceptance criteria met; specified tests pass; `state/current.md` + `state/handoff.md` updated.
- No placeholder / `TODO` / `test.skip` / stub / unimplemented branches left (these are blockers).
- A `config_committed` ledger row exists for any frozen-config change.
- Diff reviewed; no secrets/data staged; commit is atomic + Conventional Commits.

## Forbidden
- Re-adding Gemini/TokenHub providers; mocking data in the real pipeline; `git add -f` past
  `.gitignore`; committing `.env` / `data/` / `*.parquet`; rewriting `main` history; force-pushing.
- Silently mutating a frozen config. Renaming/moving existing tracked docs (breaks refs).
- "Rerun-to-significance." Fabricating anti-leakage facts. Committing without verification.
- Infinite review loops — after 2 failed fix rounds, escalate (BLOCKED), don't keep iterating.

## See also
- `WORKFLOW.md` — the full 11-stage operating pipeline + 5 modes + stop-conditions (constitution).
- `docs/orchestration-protocol.md` — supervisor + worker dispatch protocol (ADR-012); binds OMC agents to Aionis anti-leakage guardrails.
- `CONTRIBUTING.md` — git conventions (Conventional Commits, ledger rule, secrets/data policy).
- `state/current.md` — live status (read first).
- `docs/RESULTS.md` — the falsifiable-results snapshot. `decisions/index.md` — the ADR registry.
