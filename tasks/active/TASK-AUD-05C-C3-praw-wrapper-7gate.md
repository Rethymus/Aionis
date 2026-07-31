# AUD-05C-C3 — PRAW wrapper (owner-held: 7-gate clearance first)

- 编号: AUD-05C-C3
- Parent: AUD-05C
- 状态: **OWNER-HELD (blocked: 7-gate data-intake clearance required)**
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

**Disposition: C3 — owner-held (7-gate clearance first)**
- PRAW is PARTIALLY cleared (G1: BSD-2 ✓, G7: politeness ✓, G5: exploratory-only ✓)
- BUT: Reddit ToS, content license, and selection bias (G6) need owner review
- `docs/data-intake-rubric.md` 7-gate MUST be explicitly cleared before wrapper integration
- If 7-gate fails → BLOCKED, disable PRAW live transport

## 7-Gate clearance checklist (OWNER decision)

- [ ] **G1 — License**: PRAW is BSD-2-Clause ✓ (already on allowlist)
- [ ] **G2 — PIT**: Every snapshot has UTC `snapshot_ts` ✓ (forward-collection by construction)
- [ ] **G3 — No-revision**: Raw pulls are sha256-archived, immutable ✓
- [ ] **G4 — Snapshot**: Cache-pinned, ledger row records sha256 ✓
- [ ] **G5 — Exploratory-only**: `mode: exploratory` ✓ (does NOT enter confirmatory)
- [ ] **G6 — Selection-honesty**: Retail-attention is selection-biased (declared as scope limit) — **OWNER CONFIRM**
- [ ] **G7 — Politeness**: PRAW honors 100 QPM + ToS; 1.5s sleep between subreddits ✓

**Owner decision:**
- If ALL 7 gates pass → APPROVE wrapper task
- If ANY gate fails → BLOCKED, disable PRAW live transport

## Allowed changes (ONLY after 7-gate APPROVE)

- `src/aionis/ingest/http_policy.py`: Add PRAW-specific adapter or helper (if needed)
- `ingest/reddit_sentiment.py`:
  - Integrate with shared host-spacing policy (≥2s floor)
  - Preserve PRAW's internal 100 QPM + ToS
  - Keep 1.5s subreddit-level politeness (can coexist with ≥2s floor)
  - Preserve cache/ledger/forward-only discipline
- `tests/test_reddit_sentiment.py`:
  - Add hermetic tests for shared policy integration
  - Preserve existing cache/ledger tests

## Forbidden

- Do NOT integrate wrapper BEFORE 7-gate owner APPROVE
- Do NOT modify frozen specs, ledger, results, data
- Do NOT change forward-collection-only discipline
- Do NOT remove cache/ledger discipline
- Do NOT run actual PRAW calls in tests (use mocks/fakes)

## Acceptance criteria (AFTER 7-gate APPROVE)

- [ ] 7-gate checklist signed by owner
- [ ] `collect_reddit_sentiment()` uses shared host-spacing policy
- [ ] PRAW's internal politeness (100 QPM) preserved
- [ ] Subreddit-level 1.5s sleep preserved (or increased to ≥2s if policy requires)
- [ ] Cache/ledger discipline unchanged
- [ ] Forward-collection-only discipline unchanged
- [ ] Hermetic tests pass
- [ ] `uv run pytest -q` all tests pass
- [ ] `uv run ruff check` clean

## Engineer → Verifier → Reviewer gate (AFTER 7-gate APPROVE)

1. **Engineer**:
   - Integrate shared policy (leverage `http_policy.py` primitive)
   - Add hermetic tests (fake clock, mock PRAW)
   - Run pytest + ruff + frozen-surface checks
2. **Verifier** (independent, read-only):
   - Confirm shared policy integrated
   - Confirm PRAW internal politeness preserved
   - Run tests from clean virtualenv
3. **Reviewer**: Approve if scope-limited, no blocking issues

## Stop condition

- **BEFORE 7-gate APPROVE**: Do NOT implement wrapper (BLOCKED)
- **AFTER 7-gate APPROVE**: If cache/ledger discipline changes → STOP, revert

## Dependencies

- 7-gate owner clearance (G1-G7)
- AUD-05B APPROVED (shared policy primitive exists)

## Owner decision items

1. **G6 — Selection-honesty**: Is Reddit/StockTwits retail-attention selection bias acceptable as "exploratory-only, declared scope limit"?
2. **Reddit ToS**: Does Reddit's ToS allow programmatic collection for research (display, no-resale)?
3. **Content license**: Is Reddit user-generated content licensable for research use?
4. **Outcome**: APPROVE wrapper → C3 task proceeds; REJECT → disable PRAW live transport

## If BLOCKED (7-gate fails)

- Disable `collect_reddit_sentiment()` live PRAW calls
- Cache miss → fail-closed (raise clear error)
- Keep cached data available for historical analysis (read-only)
- No new PRAW fetches allowed

## Success metrics (if APPROVE)

- PRAW integrated with shared host-spacing policy
- PRAW internal politeness (100 QPM) preserved
- Cache/ledger/forward-only discipline 100% preserved
- No regressions in existing PRAW tests
