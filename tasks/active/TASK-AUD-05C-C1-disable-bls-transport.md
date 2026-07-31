# AUD-05C-C1 — Disable BLS live transport (BLOCKED source)

- 编号: AUD-05C-C1
- Parent: AUD-05C
- 状态: **COMPLETE — Engineer evidence; independent Verifier PASS; Reviewer APPROVE**
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

- [x] `_fetch_text(event_type="CPI", ...)` raises RuntimeError with clear "BLS blocked" message
- [x] `_fetch_text(event_type="NFP", ...)` raises RuntimeError with clear "BLS blocked" message
- [x] `_fetch_text(event_type="FOMC", ...)` still works (unaffected)
- [x] Hermetic test `tests/test_event_text.py::test_bls_blocked` passes
- [x] `uv run pytest -q` (all tests pass)
- [x] `uv run ruff check` clean
- [x] No direct `requests.get()` calls to `www.bls.gov` remain in codebase

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

## 2026-08-01 owner authorization + Engineer evidence

- Owner authorized the already-decided disable-only disposition. CPI/NFP cache misses now raise a
  clear BLS-blocked error before URL construction or any HTTP attempt; existing cache hits remain
  readable and the FOMC shared-policy path is unchanged.
- Updated hermetic event-text tests to exercise FOMC for live/fallback behavior and added separate
  CPI/NFP fail-closed assertions that reject any attempted HTTP call.
- Engineer checks PASS: targeted event-text/policy tests, repository ruff, diff check, exact BLS
  direct-request scan, and the full hermetic pytest suite. No network, BLS adapter, frozen research
  surface, ledger, data, or outcome-bearing workflow changed.
- Required next gate: independent read-only Verifier, then Reviewer. Do not commit this task until
  those gates approve it.

## 2026-08-01 independent Verifier evidence

- Verifier: **PASS** (fresh read-only session; mirrored to `/dev/shm/c1-verifier.txt`)
- Commands:
  - `TMPDIR=/dev/shm UV_CACHE_DIR=/dev/shm/uv-cache uv run --offline pytest -q tests/test_event_text.py tests/test_http_policy_adapters.py` -> 29 passed
  - `TMPDIR=/dev/shm UV_CACHE_DIR=/dev/shm/uv-cache uv run --offline ruff check` -> clean
- direct BLS `requests.get` scan -> no matches
- frozen-surface `git diff --name-only` -> empty
- Required next gate: independent Reviewer.

## 2026-08-01 Reviewer round 1 + repair + re-Verifier evidence

- Reviewer round 1: **REQUEST CHANGES** (blocking finding: FOMC cache round-trip test did not
  explicitly patch `event_text._policy_get`, so the claimed hermeticity was not robust).
- Repair: `test_cache_roundtrip_first_call_writes_second_call_reads` now patches
  `event_text._policy_get` to the fake HTTP responder and uses a single FOMC event.
- Re-Verifier: **PASS** (fresh read-only session; mirrored to `/dev/shm/c1-verifier2.txt`);
  targeted event-text/policy pytest 29 passed, scoped ruff clean, diff check clean, direct BLS
  `requests.get` scan no matches, C1-relevant diff limited to the two allowed files.
- Required next gate: Reviewer re-review.

## 2026-08-01 Reviewer round 2 evidence

- Reviewer: **APPROVE** (fresh read-only session; mirrored to `/dev/shm/c1-reviewer3.txt`)
- No blocking findings. The diff is scoped to the two allowed files; CPI/NFP fail before URL
  construction or any HTTP call; cache hits remain readable; FOMC continues through `_policy_get`;
  tests patch `event_text._policy_get` so they are hermetic.
- Advisory only: BLS URL constants and the generic `requests.get` helper remain unreachable for
  BLS and may be future cleanup; direct BLS live transport is gone.
- Group A full gate: `uv run --offline pytest -q`, `uv run --offline ruff check`,
  `git diff --check`, and the frozen-surface diff all passed.
