# AUD-05C-C5 — Model API transport disposition (owner decision: ≥2s host-spacing rule scope)

- 编号: AUD-05C-C5
- Parent: AUD-05C
- 状态: **OWNER-HELD (blocked: clarify if ≥2s rule applies to GLM/SiliconFlow/ModelScope model APIs)**
- Priority: **P0**
- Size: **S** (decision-only) → **M** (if implementation needed)
- Risk: **MEDIUM** (model APIs are core to E3 extraction; token/cost control is critical)
- 目标: 明确 ≥2s host-spacing rule是否适用于 GLM/SiliconFlow/ModelScope 等 model API transports；保持 provider set 不变（不添加/删除 providers）
- 依赖: Owner decision on ≥2s scope → (if needed) Engineer → Verifier → Reviewer
- Owner gate: **必须明确** model API 的 politeness 规则是否与 data-fetch sites 一致

## Scope

**Current state (FACT):**

**Model API transports (SDK-owned, NOT data-fetch):**
1. **`features/event_vector.py:GLMEmbedder`** (lines 65-141):
   - Uses `OpenAI` SDK with `max_retries=3`
   - API endpoint: GLM embedding-3 (configurable `base_url`)
   - Has DISK CACHE by text hash (cache hit → no API call)
   - No explicit sleep between calls (SDK retries handle errors)

2. **`features/causal_broadcast.py:GLMCausalEdgeClient`** (lines 103-162):
   - Uses `OpenAI` SDK with `max_retries=0`
   - API endpoint: GLM-4-Flash (configurable `base_url`)
   - Has sha256-keyed cache (`causal_edge_<hash>.json`)
   - No explicit sleep between calls (caller owns retries)

3. **`extraction/llm_client.py:OpenAICompatClient`** (lines 106-151):
   - Uses `OpenAI` SDK with `max_retries=0`
   - API endpoint: Configurable (GLM, SiliconFlow, ModelScope, etc.)
   - Has sha256-keyed cache
   - No explicit sleep between calls

4. **`extraction/llm_client.py:ProviderRouter`** (lines 157-225):
   - Multi-key failover router
   - Cooldown on 429 (rate limit)
   - Token/call accounting per provider
   - No explicit sleep between provider switches

**Current politeness discipline:**
- SDK-level retries (OpenAI SDK has built-in retry with exponential backoff)
- Cache hits → no API call (zero network traffic)
- Cache misses → one API call per text (no batching delays)
- Provider-level cooldown on 429 (router manages this)

**DISPOSITION QUESTION:**
Does the project-wide ≥2.0-second host-spacing rule (from `http_policy.py`) apply to **model API endpoints**?

**Rationale for the question:**
- `http_policy.py` was designed for **data-fetch sites** (FRED, EDGAR, Tiingo, etc.)
- Model APIs (GLM, SiliconFlow, ModelScope) are **different category**:
  - They're LLM inference endpoints, not public data portals
  - They have their own rate-limiting (tokens per minute, not requests per second)
  - The OpenAI SDK already has retry logic
  - Cache hits are common (same text → same embedding)
- BUT: They still make HTTP calls, and the politeness principle might apply

**Two interpretations:**

### Interpretation A: ≥2s rule applies ONLY to data-fetch sites
- Model APIs are exempt (they're SDK-managed, cache-heavy, token-metered)
- Current implementation is compliant
- No changes needed

### Interpretation B: ≥2s rule applies to ALL HTTP calls
- Model APIs must also respect ≥2s spacing
- Need to add sleep/cooldown between API calls
- Potential impact: slower E3 extraction (but safer)

**Provider set constraint (INVARIABLE):**
- GLM, SiliconFlow, ModelScope are the PINNED provider set (per CLAUDE.md)
- Do NOT add/remove providers (e.g., no OpenAI, no Gemini, no others)
- This task is ONLY about politeness/sleep, not provider selection

## Owner decision items

1. **Scope of ≥2s rule**: Does it apply to model API endpoints?
   - **Option A**: No, model APIs are exempt (SDK-managed, cache-heavy, token-metered)
   - **Option B**: Yes, all HTTP calls must respect ≥2s spacing

2. **If Option B (≥2s applies)**: How to implement?
   - **Option B1**: Add sleep in `GLMEmbedder`, `GLMCausalEdgeClient`, `OpenAICompatClient`
   - **Option B2**: Add router-level cooldown in `ProviderRouter`
   - **Option B3**: Create a model-API-specific policy (separate from `http_policy.py`)

## Allowed changes (ONLY after owner decision)

**If Option A (model APIs exempt):**
- Document this decision in `docs/` or as inline comments
- No code changes needed

**If Option B (≥2s applies):**
- Add sleep/cooldown to model API clients
- Preserve cache discipline (cache hit → no sleep, no API call)
- Preserve provider set (GLM, SiliconFlow, ModelScope only)
- Add tests for sleep/cooldown behavior

## Forbidden

- Do NOT add/remove providers (GLM, SiliconFlow, ModelScope are pinned)
- Do NOT change cache discipline
- Do NOT modify frozen specs, ledger, results, data
- Do NOT run actual model API calls in tests (use mocks/fakes)

## Acceptance criteria (if Option B implementation needed)

- [ ] Model API calls respect ≥2s spacing (between cache misses)
- [ ] Cache hits → no sleep, no API call (unchanged)
- [ ] Provider set unchanged (GLM, SiliconFlow, ModelScope only)
- [ ] Router cooldown logic preserved (if using ProviderRouter)
- [ ] Hermetic tests pass (fake clock, no network)
- [ ] `uv run pytest -q` all tests pass
- [ ] `uv run ruff check` clean

## Engineer → Verifier → Reviewer gate (if Option B implementation needed)

1. **Engineer**:
   - Implement sleep/cooldown per owner decision (B1/B2/B3)
   - Add hermetic tests (fake clock, mock model API)
   - Run pytest + ruff + frozen-surface checks
2. **Verifier** (independent, read-only):
   - Confirm ≥2s spacing enforced
   - Confirm cache discipline unchanged
   - Confirm provider set unchanged
3. **Reviewer**: Approve if scope-limited, no blocking issues

## Stop condition

- If provider set changes → BLOCKED, violates CLAUDE.md
- If cache discipline changes → STOP, revert

## Dependencies

- Owner decision on ≥2s scope (Option A or B)
- (If Option B) AUD-05B APPROVED (may need to reference `http_policy.py` design)

## Success metrics

- (If Option A) Decision documented, no code changes
- (If Option B) ≥2s spacing enforced, cache/provider-set preserved

## Note on risk

Model APIs are **MEDIUM risk** because:
- They're core to E3 extraction (causal edges, event vectors)
- Token/cost control is critical (E3 budget is limited)
- But: Cache hits are common, so actual API calls are sparse
- SDK retry logic already handles transient errors

## Recommended decision (for owner consideration)

**Option A (exempt model APIs)** seems appropriate because:
1. Model APIs are fundamentally different from data-fetch sites
2. The OpenAI SDK already has retry/backoff logic
3. Cache hits eliminate most API calls
4. Provider routers already manage cooldowns on 429
5. Adding ≥2s sleep would slow E3 extraction without clear benefit

But the owner should decide based on project politeness principles.
