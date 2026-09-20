# AUD-04 — Enforce the market-data source allowlist

- 编号: AUD-04
- 标题: Remove blocked Yahoo/yfinance and Stooq runtime paths and fail closed to Tiingo/Alpaca.
- 状态: **COMPLETE — repair round 1 re-Verifier PASS; Reviewer APPROVE**
- Priority: **P0**
- Size: **M**
- Risk: **MEDIUM**（可逆代码/依赖清理，但会改变无 key 或 provider 缺失时的 fetch 行为）
- 建议 agent role / model tier: **Engineer / medium**；Verifier / medium；Reviewer / strong。
- 目标: 让市场数据真实 CLI 路径只使用项目已批准的 Tiingo/Alpaca，并在两者不可用或不完整时
  明确 fail closed，绝不静默触发 blocked source。
- 背景: `CLAUDE.md` 明确 Yahoo/yfinance、Stooq blocked；但 `ingest/market.py` 仍实现并调用
  yfinance→Stooq fallback，`pyproject.toml` 仍直接依赖 yfinance，模块 docstring 也称其 primary。
- 依赖: AUD-01 PASS；在 AUD-06 E3 live-input readiness 前完成。
- 允许修改: `src/aionis/ingest/market.py`、`scripts/phase_b_fetch.py`、`pyproject.toml`、`uv.lock`；
  可新增/修改仅针对 market source selection 的 hermetic test（优先 `tests/test_market.py`）。
- 禁止修改: price/fundamental caches、phase config、adjustment/label/feature semantics、frozen prereg/ADR、
  ledger/results、其他 provider allowlist；禁止网络 fetch、真实数据刷新或 phase rerun。
- 前置条件: 保存依赖变更前后的 direct dependency 与 lock diff；确认移除 yfinance 不会删除其他
  load-bearing research dependency。
- 实施要求:
  - source order 只能是 Tiingo → Alpaca；两者缺 key、返回缺失或失败时抛出可行动错误，列出缺失 symbols。
  - 删除 blocked-source imports/functions/calls和误导 docstrings，不保留“portable fallback”死路径。
  - tests 用 monkeypatch/stub response；不得发真实 HTTP，不得用 synthetic fixture 冒充 research result。
  - adjusted-price PIT/corporate-action 语义不在本任务暗改；需要另行审计时登记 backlog。
- 验收标准:
  - [ ] 精确静态扫描无 yfinance import/dependency、Yahoo host 或 Stooq host/runtime 调用；说明性注释
    命中单独人工审计，不以宽泛字符串零命中作为验收。
  - [ ] 无 Tiingo/Alpaca key 时 fail closed；部分缺失时不会尝试 blocked host。
  - [ ] Tiingo 优先、Alpaca 只补缺失 symbols 的行为有 hermetic tests。
  - [ ] `uv.lock` 只出现预期的依赖移除；核心 frozen learner/数据栈版本不漂移。
  - [ ] ledger、data cache、既有 result artifacts 未变化。
- 必须运行的测试: `uv lock --check`；market 定向测试；`uv run pytest -q`；`uv run ruff check`；
  精确 blocked-runtime 静态扫描；`git diff -- uv.lock pyproject.toml` 人工审计。
- 失败处理: 若移除 yfinance 导致非市场依赖被 lock resolver 升级，STOP 并缩小 lock diff；若批准源均
  无法覆盖 live universe，则 BLOCKED 交 owner 选择新的**经 7-gate 审核**来源，禁止恢复 blocked fallback。
- 预期产物: approved-only market adapter、可行动 fail-closed error、hermetic source-selection tests、最小 lock diff。
- 完成后需要更新: `state/current.md`、`state/handoff.md`；完成后从 backlog 删除本候选。
- see: `CLAUDE.md` Provider/data-source constraints；`src/aionis/ingest/market.py:126`、`:177`、`:207`；
  `pyproject.toml:23`。

## 2026-07-31 read-only preflight

- Runtime violations are localized to `ingest/market.py`; yfinance is a direct dependency and Stooq uses a
  direct URL path. Tiingo and Alpaca are the only approved market providers.
- The real Phase B CLI bypasses `fetch_prices()` and can persist a partial panel, so
  `scripts/phase_b_fetch.py` is explicitly in scope for fail-closed behavior.
- AUD-04 and AUD-05 both touch `market.py` and `tests/test_market.py`; implementation must remain serial.

## 2026-07-31 execution evidence

- Engineer removed Yahoo/yfinance and Stooq runtime paths, made provider order Tiingo then Alpaca for unresolved
  symbols, added actionable fail-closed errors, removed the direct dependency, and added hermetic adapter tests.
- Independent Verifier PASS: four market tests, lock consistency, scoped ruff, blocked-runtime scans, provider
  order, Phase B completeness guard, minimal lock/core-stack diff, and unchanged frozen preregistration/ledger.
- Reviewer round 1 confirmed the approved-provider work but found that a pre-existing incomplete final Phase B
  cache could bypass the guard and that the persistence-order test did not exercise `main()`. Repair round 1 is
  limited to rejecting/rebuilding that cache and adding hermetic `main()` persistence-order coverage.
- The `pythonpath = ["."]` hunk belongs to completed AUD-01 and is not attributed to AUD-04.
- Repair Engineer added final-panel reuse validation and hermetic `main()` tests for missing/all-null cached
  columns and partial-provider failure. Independent re-Verifier PASS: 7 targeted tests and the full 589-test
  suite pass; ruff, lock, blocked-runtime scan, diff and frozen-surface checks pass. It noted date-range coverage
  validation as a separate residual data-completeness risk, not a source-allowlist blocker.
- Reviewer re-review APPROVE: approved-provider ordering, stale-cache rejection, final-write fail-closed behavior,
  dependency removal, test evidence and task attribution all satisfy AUD-04. Date-range coverage remains a
  separately tracked data-completeness risk.
