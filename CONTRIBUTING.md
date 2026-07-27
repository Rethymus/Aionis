# Contributing to Aionis

Aionis is a personal anti-leakage quantitative-finance research project. These
conventions keep the git history readable, bisectable, and free of secrets or
regenerable data.

## 1. Commit message format — Conventional Commits

Every commit message MUST follow Conventional Commits:

```
<type>(<optional scope>): <description>

<optional body — wrap at ~72 chars>

<optional footer>
```

### Allowed types

| Type       | Use for |
|------------|---------|
| `feat`     | A new feature or capability |
| `fix`      | A bug fix |
| `refactor` | Code restructuring with no behavior change |
| `docs`     | Documentation only |
| `test`     | Adding or correcting tests |
| `chore`    | Tooling, config, repo housekeeping |
| `perf`     | Performance improvement |
| `ci`       | CI/CD pipeline changes |

### Rules

- The `<description>` is lowercase, imperative mood, no trailing period
  (e.g. `add tiingo price fetcher`, not `Added tiingo price fetcher.`).
- `scope` is optional and names the affected module
  (e.g. `feat(erl): add structural-only label builder`).
- Keep commits **atomic** — one logical change per commit. If a change spans
  multiple concerns (config vs logic vs tests vs docs), split it into multiple
  commits in dependency order.
- Reference issues or design docs in the footer when relevant
  (e.g. `Refs: docs/pre-registration.md`).

### Examples

```
feat(erl): add structural-only label builder

Builds the Evaluation Result Layer from filings events only; market_impact
columns are intentionally excluded to prevent LLM-memorization leakage.

Refs: docs/erl-design.md
```

## 2. Pre-registration discipline (anti-leakage)

This project's integrity depends on frozen experiment configs. **Never silently
mutate a frozen experiment config.**

- When a commit changes a frozen experiment config, that commit MUST also append
  a row to `runs/ledger.jsonl` referencing the **new config sha** (and the
  previous one). The ledger is the append-only audit log of config lineage.
- Treat `runs/ledger.jsonl` as the source of truth for what was pre-registered
  and when. It is the only file under `runs/` that is tracked by git.
- If you are changing a *non-frozen* / exploratory config, say so in the body
  (e.g. `mode: pre-freeze`) so reviewers know the ledger rule does not apply.

Ledger row shape (one JSON object per line):

```json
{"ts": "2026-07-27T19:18:00Z", "config": "configs/exp_tcr_v02.yaml", "prev_sha": "<old>", "new_sha": "<new>", "mode": "freeze", "note": "lock WRL feature set pre-S0"}
```

## 3. NEVER commit secrets or data

These are gitignored and must stay out of history:

- `.env` and any `.env.*.local` — real API keys (GLM, Tiingo, Alpaca) live here.
- All of `data/` — cached API responses, EDGAR facts, ticker dumps, parquet
  snapshots, embedding caches. Regenerable and/or leakage-sensitive.
- `*.parquet`, `*.tar.gz`, `*.cache.json` anywhere in the tree.
- Run artifacts under `runs/` except `runs/ledger.jsonl`
  (`runs/results/`, `runs/*.log`, `runs/health_*.json` are gitignored).
- `.venv/`, `.benchmarks/`, `.pytest_cache/`, `.ruff_cache/`, `htmlcov/`,
  `.coverage`.

If you accidentally stage a secret, **stop**, unstage it, and rotate the key
before continuing. Never `git add -f` past the `.gitignore`.

## 4. Co-author trailer for Claude-authored work

Commits authored or co-authored by Claude include the trailer:

```
Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
```

## 5. Branching and history safety

- Default branch is `main`.
- Never rewrite `main` history. Use `--force-with-lease` (never `--force`) on
  feature branches only.
- Stash dirty work before rebasing.

## 6. Pre-commit checklist

- [ ] No secrets staged (`git status --porcelain | grep -E '\.env|secret|key'` is empty).
- [ ] No `data/` or `*.parquet` staged.
- [ ] Commit message follows Conventional Commits.
- [ ] If a frozen config changed, `runs/ledger.jsonl` was appended in the same commit.
- [ ] Change is atomic and independently revertable.
