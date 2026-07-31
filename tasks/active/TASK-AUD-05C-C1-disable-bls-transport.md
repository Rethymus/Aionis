# AUD-05C-C1 — Disable BLS live transport (BLOCKED source)

- 编号: AUD-05C-C1
- Parent: AUD-05C
- 状态: **READY (awaiting owner GO after AUD-05C disposition-complete)**
- Priority: **P0**
- Size: **S**
- Risk: **LOW** (disable-only, no new code)
- 目标: 禁用 BLS CPI/NFP live transport，使 cache miss fail-closed；不得构建 BLS polite adapter。
- 依赖: AUD-05C disposition-marked-complete → owner GO → Engineer → Verifier → Reviewer
- Owner gate: **必须确认** BLS 明确 blocked（per CLAUDE.md data-source constraints："Blocked: yfinance/Yahoo, BLS, Stooq"）

## Scope

**Current state (FACT):**
- `ingest/event_text.py:_fetch_text()` (lines ~114-134) has two branches:
  - FOMC: `www.federalreserve.gov` → AUD-05B integrated shared policy ✓
  - CPI/NFP: `www.bls.gov` → direct `requests` with 0.5s spacing, NO shared policy
- CPI/NFP path: makes `requests.get(url, headers=UA, timeout=20)` twice, with 0.5s between attempts
- NO cache layer (unlike FOMC cache at `data/cache/fomc Statements/`)

**Disposition: BLOCKED + disable**
- BLS is BLOCKED per CLAUDE.md data-source constraints: "Blocked: yfinance/Yahoo, BLS, Stooq"
- NO polite adapter allowed (per AUD-05C task spec: "do not build a transport while BLS is blocked")
- Cache miss → fail-closed (raise clear error, never silently skip or fall back)

## Allowed changes

- `ingest/event_text.py:_fetch_text()` CPI/NFP branch ONLY:
  - Remove the two `requests.get()` calls to `www.bls.gov`
  - Replace with `raise RuntimeError("BLS is blocked per data-source constraints; use cached data only")`
  - Preserve the FOMC branch unchanged (AUD-05B already integrated shared policy)
- Add/update hermetic test in `tests/test_event_text.py`:
  - Test that `_fetch_text(event_type="CPI", ...)` raises RuntimeError
  - Test that `_fetch_text(event_type="NFP", ...)` raises RuntimeError
  - Test that FOMC branch still works (with cached fixture or mock)

## Forbidden

- Do NOT add BLS to `http_policy.py` or any allowlist
- Do NOT create a BLS adapter or polite wrapper
- Do NOT modify FOMC branch (already AUD-05B-compliant)
- Do NOT modify frozen specs, ledger, results, data, or any other ingest modules

## Acceptance criteria

- [ ] `_fetch_text(event_type="CPI", ...)` raises RuntimeError with clear "BLS blocked" message
- [ ] `_fetch_text(event_type="NFP", ...)` raises RuntimeError with clear "BLS blocked" message
- [ ] `_fetch_text(event_type="FOMC", ...)` still works (unaffected)
- [ ] Hermetic test `tests/test_event_text.py::test_bls_blocked` passes
- [ ] `uv run pytest -q` (all tests pass)
- [ ] `uv run ruff check` clean
- [ ] No direct `requests.get()` calls to `www.bls.gov` remain in codebase

## Engineer → Verifier → Reviewer gate

1. **Engineer**: Implement disable-only change + hermetic test; run pytest + ruff; record evidence
2. **Verifier** (independent, read-only):
   - Confirm BLS calls removed, FOMC untouched
   - Run tests from clean virtualenv
   - Scan for any remaining BLS references
3. **Reviewer**: Approve if scope-limited, no adapter added, FOMC unaffected

## Success metrics

- Zero live BLS fetch paths remain
- Cache miss fails closed (no silent skip)
- FOMC unaffected
- No new dependencies or adapters

## Stop condition

- If FOMC branch is accidentally modified → STOP, revert, re-do
- If BLS adapter is created → BLOCKED, violates spec

## Dependencies

- None (disposition is already decided; owner GO is the only gate)
