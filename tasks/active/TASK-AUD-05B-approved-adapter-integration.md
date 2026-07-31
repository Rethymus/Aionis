# AUD-05B — Integrate the shared policy into approved direct-request adapters

- 编号: AUD-05B
- 状态: **Repair round 1 independent re-Verifier PASS; awaiting re-Reviewer**
- Priority: **P0**
- Size: **M**
- Risk: **HIGH**（跨多个数据 adapter，但不改变数据/特征语义）
- 目标: 将 `src/aionis/ingest/http_policy.py` 接入 approved direct `requests` sites，保持缓存、解析、PIT
  和公开函数签名不变；cache hit 必须在 policy acquisition 前返回。
- 禁止: 修改 policy primitive、BLS/SDK/model/health-check、forward collectors、config/features/labels、
  ledger/results/data/frozen prereg/ADR；禁止网络、真实 sleep、phase/strategy/forward 运行。
- 允许生产文件: `ingest/market.py`, `fundamentals.py`, `stakes_13d.py`, `stakes_13d_efts.py`,
  `cik_resolver.py`, `events.py`, `features/macro_surprise.py`, `ingest/event_text.py`（仅 FOMC 分支）、
  `ingest/universe.py`。允许修改对应 hermetic tests，并新增 `tests/test_http_policy_adapters.py`。
- 非重叠边界: BLS、VIX/FRED pandas-datareader、selection-panel FRED/Fama-French、PRAW、LLM SDK、
  `scripts/health_check.py` 全部留给 AUD-05C；`http_policy.py` 视为冻结。
- E3: forward SEC/ALFRED collectors 必须通过现有 adapter 复用获得 policy；不得修改 forward 文件、
  scheduler、commit/reveal、outcome artifacts 或新增 limiter。
- 验收:
  - 所有 inventory 中 14 个 approved direct-request sites 使用共享 policy；无 `sleep(0.15/0.4/0.5/1.0)`。
  - cache hit 不调用 policy/request/sleep；分页每页只包裹实际 HTTP。
  - 保持 parsing/cache/PIT/signature；同 host 跨模块间隔和 bounded retry 有 fake-clock tests。
  - 无 blocked source、SDK/model/health-check 接入；frozen/ledger/results/data 无变化。
- 必须运行: 定向 adapter tests、`uv run pytest -q`、`uv run ruff check`、精确 sleep 扫描、`git diff --check`、
  frozen-surface diff。只读，不运行任何研究脚本。
- 完成顺序: Engineer → 独立 Verifier → Reviewer；最多两轮修复。05C 必须等待本任务 APPROVE。

## 2026-07-31 Engineer execution evidence

- Integrated the shared host-scoped policy across the exact 14 approved direct-request sites. Cache
  reads remain before policy acquisition, and each ALFRED/EFTS page wraps only its actual HTTP call.
- Added hermetic fake-clock coverage for the 14-site allowlist, cache short-circuiting, same-host
  FRED/ALFRED spacing across modules, and the bounded four-attempt retry limit. Existing SEC adapter
  retry tests now inject the shared policy with fake time.
- Confirmed E3 reuse without forward-file edits: SEC forward collectors call
  `stakes_13d.fetch_submissions`; the macro collector calls `fetch_alfred_vintages`.
- Engineer checks PASS: 94 targeted owned-adapter tests; full `pytest -q`; repository-wide ruff;
  exact prohibited-sleep scan; direct-request boundary scan; `git diff --check`; and pre/post
  frozen-surface checksums. All commands used `UV_CACHE_DIR=/tmp/aionis-uv-cache-aud05b` where
  applicable. No network, real sleep, or research script was run.

## 2026-07-31 independent Verifier evidence

- Verdict: **PASS**. Read-only review confirmed the exact 14 approved direct-request sites route
  through the shared host-scoped policy while cache reads remain ahead of policy acquisition.
- Relevant adapter tests and the full hermetic pytest suite passed from the installed virtualenv;
  repository-wide ruff, prohibited-sleep/direct-request scans, `git diff --check`, and the frozen-
  surface diff check also passed.
- FOMC is covered; BLS, SDK-owned transports, PRAW, model clients, and `scripts/health_check.py`
  remain explicitly deferred to AUD-05C. No forward file or outcome-bearing surface changed.
- Environment note: the read-only verifier could not open the normal uv cache, so it used
  `.venv/bin/python` with `TMPDIR=/dev/shm`; the only warning was pytest's expected inability to
  write its cache in the read-only worktree.

## 2026-07-31 Reviewer round 1

- Verdict: **REQUEST CHANGES**. The integration retained caller-facing `retries` and `backoff`
  parameters but routed those adapters through a fixed global retry policy, so non-default values
  were ignored and market defaults changed from three total attempts to four.
- Required repair: preserve each adapter's total-attempt and backoff semantics while retaining
  process-wide host spacing; add adapter tests proving values such as `retries=1` are honored.
- No other blocker was found. Cache/PIT/pagination/FOMC/E3/frozen boundaries remain acceptable;
  AUD-05C stays closed until repair re-verification and re-review.

## 2026-07-31 Engineer repair round 1 evidence

- Added a per-request `RetryPolicy` override to the shared process-wide `HttpRequestPolicy`; the
  override changes only retry bounds/backoff while retaining the same host-spacing state and the
  same injected sleeper.
- Restored each configurable adapter's existing semantics: `retries` is total attempts;
  Tiingo/Alpaca, fundamentals and both 13D adapters use their prior linear `backoff * n`
  schedule; CIK resolver uses its prior exponential `backoff * 2**(n-1)` schedule. Market's
  default is again three total attempts rather than the shared default's four.
- Added hermetic coverage for `retries=1` and custom `backoff=3` across Tiingo, Alpaca,
  fundamentals, 13D submissions, 13D EFTS and CIK resolver, plus a primitive-level per-request
  override test. The tests use a fake clock and make no network calls or real sleeps.
- Engineer checks passed: 60 core retry/policy tests; 122 expanded adapter/PIT/forward-ingest
  regression tests; the full 620-test hermetic suite; repository-wide ruff; `git diff --check`;
  direct-request/prohibited-sleep scans; and frozen-boundary inspection. Full-suite warnings were
  the existing `forward_score` timezone/constant-input warnings only.
- No BLS/SDK/PRAW/model/health-check, forward, config, feature/label, ledger/result/data,
  preregistration or ADR surface was changed by this repair. Verdict remains reserved for the
  independent re-Verifier and re-Reviewer; AUD-05C remains closed.

## 2026-07-31 independent re-Verifier evidence

- Verdict: **PASS**. Static review confirmed per-request retry overrides retain the single shared
  `HostSpacingPolicy` and injected sleeper while restoring each adapter's total-attempt and backoff
  semantics.
- The Reviewer counterexample is covered across all six configurable paths: `retries=1` makes one
  request with no sleep; custom `backoff=3` yields `[3, 6, 9]` for linear adapters and
  `[3, 6, 12]` for CIK.
- 75 targeted hermetic tests and the full 620-test suite passed. Ruff, `git diff --check`, approved
  direct-request/prohibited-sleep scans, and frozen-surface checks passed. No network, research,
  forward script, or outcome inspection occurred.
- Residual non-blocker: the shared private transport entry point remains housed in `universe.py`;
  this coupling is reserved for a future non-functional cleanup, not this repair.
