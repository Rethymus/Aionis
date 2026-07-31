# AUD-05C-C3 — PRAW wrapper (owner-authorized with 7-gate conditions)

- 编号: AUD-05C-C3
- Parent: AUD-05C
- 状态: **COMPLETE — owner-authorized; Engineer complete; independent Verifier PASS; Reviewer APPROVE**
- Priority: **P0**
- Size: **S** (if approved) / **BLOCKED** (if rejected)
- Risk: **MEDIUM** (Reddit/PRAW has license/ToS/politeness considerations)
- 目标: 为 PRAW (Reddit) 构建共享 policy wrapper，前提是 source/API terms 通过 7-gate 数据摄入审查（`docs/data-intake-rubric.md`）
- 依赖: 7-gate clearance (G1: license, G2: PIT, G3: no-revision, G4: snapshot, G5: exploratory-only, G6: selection-honesty, G7: politeness) → owner GO → Engineer → Verifier → Reviewer
- Owner gate: **必须先通过** 7-gate 审查（G1-G7），才能批准 wrapper task

## Scope

**Current state (FACT):**
- `ingest/reddit_sentiment.py:collect_reddit_sentiment()` (lines 312-396):
  - Uses PRAW SDK (BSD-2-Clause, per G1 already on allowlist)
  - Politeness: 1.5s sleep between subreddit pulls (G7: `time.sleep(_SUB_SLEEP)` where `_SUB_SLEEP = 1.5`)
  - Has cache layer (`data/cache/reddit_snapshots.parquet`, `reddit_raw_<ts>.json`)
  - Forward-collection ONLY (no historical backfill)
  - Appends `data_ingest` ledger row
- `ingest/reddit_sentiment.py:_pull_posts()` (lines 276-306):
  - PRAW makes its own HTTP calls (SDK-owned, no shared host policy)
  - PRAW honors Reddit's 100 QPM + ToS internally

**Disposition: C3 — owner-approved with conditions.** The earlier partial-clearance review is resolved
by the recorded decision below. Implementation remains bounded to transport policy + hermetic tests.

## 7-Gate clearance checklist (OWNER decision)

- [x] **G1 — License**: PRAW is BSD-2-Clause ✓ (already on allowlist)
- [x] **G2 — PIT**: Every snapshot has UTC `snapshot_ts` ✓ (forward-collection by construction)
- [x] **G3 — No-revision**: Raw pulls are sha256-archived, immutable ✓
- [x] **G4 — Snapshot**: Cache-pinned, ledger row records sha256 ✓
- [x] **G5 — Exploratory-only**: `mode: exploratory` ✓ (does NOT enter confirmatory)
- [x] **G6 — Selection-honesty**: Owner accepts the declared retail-attention selection bias only as a
  permanent exploratory scope limit.
- [x] **G7 — Politeness**: PRAW honors 100 QPM + ToS; 1.5s sleep remains and the shared host floor is
  the implementation target.

**Owner decision:**
- If ALL 7 gates pass → APPROVE wrapper task
- If ANY gate fails → BLOCKED, disable PRAW live transport

**Recorded decision (2026-08-01): APPROVE WITH CONDITIONS.** Reddit/PRAW material is internal research
only, must not be redistributed, and remains permanently `mode: exploratory`. This authorizes the
bounded wrapper task but not a live pull, confirmatory use, or research run.

## Allowed changes (ONLY after 7-gate APPROVE)

- `src/aionis/ingest/http_policy.py`: Add PRAW-specific adapter or helper (if needed)
- `ingest/reddit_sentiment.py`:
  - Integrate with shared host-spacing policy (≥2s floor) through a custom PRAW
    `requestor_class`, so every token/oauth/pagination HTTP request reserves a host slot
  - Preserve PRAW's internal 100 QPM + ToS
  - Keep 1.5s subreddit-level politeness (can coexist with ≥2s floor)
  - Preserve cache/ledger/forward-only discipline
- `tests/test_reddit_sentiment.py`:
  - Add hermetic tests for shared policy integration
  - Preserve existing cache/ledger tests

## Forbidden

- The historical pre-approval prohibition is satisfied by the recorded owner decision; do not expand it
  into live collection or research execution
- Do NOT modify frozen specs, ledger, results, data
- Do NOT change forward-collection-only discipline
- Do NOT remove cache/ledger discipline
- Do NOT run actual PRAW calls in tests (use mocks/fakes)

## Acceptance criteria (AFTER 7-gate APPROVE)

- [x] 7-gate checklist signed by owner
- [x] `collect_reddit_sentiment()` uses shared host-spacing policy
- [x] PRAW's internal politeness (100 QPM) preserved
- [x] Subreddit-level 1.5s sleep preserved (or increased to ≥2s if policy requires)
- [x] Cache/ledger discipline unchanged
- [x] Forward-collection-only discipline unchanged
- [x] Hermetic tests pass
- [x] `uv run pytest -q` all tests pass
- [x] `uv run ruff check` clean

## Engineer → Verifier → Reviewer gate (AFTER 7-gate APPROVE)

1. **Engineer**:
   - Subclass/wrap `prawcore.Requestor.request()` and pass it through
     `praw.Reddit(requestor_class=...)`; call the shared spacing primitive on the actual request URL
     immediately before delegating. PRAW retains retry/rate-limit ownership.
   - Add hermetic tests (fake clock, mock Requestor) covering token host, oauth host and multiple
     pagination requests. A single wait before each subreddit is insufficient for `_PULL_LIMIT=1000`.
   - Run pytest + ruff + frozen-surface checks
2. **Verifier** (independent, read-only):
   - Confirm shared policy integrated
   - Confirm PRAW internal politeness preserved
   - Run tests from clean virtualenv
3. **Reviewer**: Approve if scope-limited, no blocking issues

## Stop condition

- **Historical pre-approval state**: implementation was BLOCKED; approval is now recorded above
- **AFTER 7-gate APPROVE**: If cache/ledger discipline changes → STOP, revert

## Dependencies

- 7-gate owner clearance (G1-G7)
- AUD-05B APPROVED (shared policy primitive exists)

## Resolved owner decision items

1. **G6 — Selection-honesty**: accepted only as a declared exploratory scope limit.
2. **Reddit ToS/content**: internal research/display only; no resale or redistribution.
3. **Outcome**: wrapper engineering may proceed; live collection and confirmatory use remain unauthorized.

## If BLOCKED (7-gate fails)

- Disable `collect_reddit_sentiment()` live PRAW calls
- Cache miss → fail-closed (raise clear error)
- Keep cached data available for historical analysis (read-only)
- No new PRAW fetches allowed

## Success metrics (if APPROVE)

- PRAW integrated with shared host-spacing policy
- Every SDK-owned HTTP request (including pagination), not merely every subreddit loop, is covered
- PRAW internal politeness (100 QPM) preserved
- Cache/ledger/forward-only discipline 100% preserved
- No regressions in existing PRAW tests

## 2026-08-01 Engineer + independent Verifier evidence

- Engineer implementation is complete per the approved bounded scope: `praw.Reddit` receives a
  custom `requestor_class`; the requestor mixin reserves a shared host-spacing slot from the real
  request URL before delegating to `super().request()`, so token, OAuth and pagination requests are
  covered. PRAW retry/rate-limit ownership, `_SUB_SLEEP=1.5`, cache, ledger and forward-only
  semantics are unchanged.
- Verifier: **PASS** (fresh read-only session; mirrored to `/dev/shm/c3-verifier.txt`)
- Commands:
  - `TMPDIR=/dev/shm UV_CACHE_DIR=/dev/shm/uv-cache uv run --offline pytest -q tests/test_reddit_sentiment.py tests/test_http_policy_adapters.py` -> 30 passed
  - `TMPDIR=/dev/shm UV_CACHE_DIR=/dev/shm/uv-cache uv run --offline ruff check` -> clean
  - no direct `requests.get`, `urlopen`, or `http.client` in `reddit_sentiment.py` -> no matches
  - frozen-surface `git diff --name-only` -> empty
- Required next gate: independent Reviewer.

## 2026-08-01 independent Reviewer evidence

- Reviewer: **APPROVE** (fresh read-only session; mirrored to `/dev/shm/c3-reviewer2.txt`)
- No blocking findings. `praw.Reddit` receives the custom `requestor_class`; the requestor calls
  `HostSpacingPolicy.wait(url)` before `super().request()`, covering token, OAuth and pagination
  requests. PRAW retry/rate-limit ownership, `_SUB_SLEEP=1.5`, cache, ledger and forward-only
  semantics are unchanged.
- Advisory only: the recorded C3 test evidence was a targeted 30-test pass before the final Group A
  full-suite gate; the full suite has now passed.
- Group A full gate: `uv run --offline pytest -q`, `uv run --offline ruff check`,
  `git diff --check`, and the frozen-surface diff all passed.
