# AUD-05C-C4 — health_check.py disposition (owner-held: remove blocked/unapproved probes first)

- 编号: AUD-05C-C4
- Parent: AUD-05C
- 状态: **OWNER-HELD (blocked: probe inventory + shared-policy hookup decision required)**
- Priority: **P0**
- Size: **S** (inventory) → **M** (shared-policy hookup, if approved)
- Risk: **LOW** (health-check is auxiliary monitoring, not in research pipeline)
- 目标: 清理 `scripts/health_check.py` 中的 blocked/unapproved probes，然后决定是否接入共享 policy
- 依赖: Probe inventory → owner decision (keep/remove/hookup) → Engineer → Verifier → Reviewer
- Owner gate: **必须先确认** 哪些 probes 允许保留，以及是否接入 shared policy

## Scope

**Current state (FACT):**
- `scripts/health_check.py` (lines 1-197):
  - Global `MIN_GAP_S = 2.0` between any two network calls (≥2s floor ✓)
  - Probes multiple sources:
    - `DATA_SOURCES` list: EDGAR XBRL, FRED, akshare/EastMoney, GitHub raw-redirect
    - `probe_tiingo()`: Tiingo API
    - `probe_alpaca()`: Alpaca API
    - `WHEEL_REPOS`: GitHub repos (via `gh api`)
  - Has retry loops (1/2/4 exponential sleeps) separate from global 2.0s gap
  - Uses `requests.get()` directly (NO shared policy integration)
  - Exit code: 0 if all ok, 1 otherwise (for cron alerting)

**Disposition: C4 — owner-held (two-step process)**

### Step 1: Remove blocked/unapproved probes

**BLOCKED sources (per CLAUDE.md):**
- ~~akshare/EastMoney~~ (blocked: not in approved sources list)
- Keep: EDGAR, FRED, GitHub raw, Tiingo, Alpaca, GitHub repos

**Probes to REMOVE:**
- `akshare/EastMoney (prices)` - EastMoney is blocked per CLAUDE.md data-source constraints

**Probes to KEEP:**
- `EDGAR XBRL (fundamentals, PIT)` - ✓ approved
- `FRED (macro)` - ✓ approved
- `GitHub raw-redirect (reference data)` - ✓ approved
- `Tiingo (prices)` - ✓ approved
- `Alpaca (prices backup)` - ✓ approved
- GitHub wheel repos - ✓ approved (non-data, just freshness checks)

### Step 2: Decide shared-policy hookup

**Owner decision:**
- **Option A**: Keep health_check independent (current state: global 2.0s gap is sufficient)
- **Option B**: Integrate with `http_policy.py` for unified host-spacing

**Trade-offs:**
- **Option A** (keep independent):
  - Pro: Simple, health_check is auxiliary (not in research pipeline)
  - Pro: Global 2.0s gap already meets politeness floor
  - Con: Duplication with shared policy (but low risk since health_check is off-peak)
- **Option B** (integrate shared policy):
  - Pro: Unified host-spacing across all code paths
  - Con: More complex, requires importing `http_policy.py` into script

## Allowed changes (after owner decision)

**Step 1 (remove blocked probes):**
- `scripts/health_check.py`:
  - Remove `akshare/EastMoney` from `DATA_SOURCES` list
  - Update comments/docstrings if needed
- `tests/` (if any): Update or remove health_check test fixtures if they reference blocked probes

**Step 2 (shared-policy hookup, ONLY if owner APPROVE):**
- `scripts/health_check.py`:
  - Import `http_policy.py` primitive
  - Wrap EDGAR/FRED/Tiingo/Alpaca probes with shared policy
  - Keep `MIN_GAP_S = 2.0` as additional floor (redundant but harmless)
  - Keep GitHub repos probes as-is (use `gh api`, not `requests`)

## Forbidden

- Do NOT remove health_check entirely (it's useful for monitoring)
- Do NOT add blocked sources (BLS, yfinance, Stooq, etc.)
- Do NOT modify research pipeline code (this is auxiliary only)
- Do NOT remove GitHub repo freshness checks (they're non-data)

## Acceptance criteria

**Step 1 (remove blocked probes):**
- [ ] `akshare/EastMoney` removed from `DATA_SOURCES`
- [ ] Script still runs (`python scripts/health_check.py --only data`)
- [ ] Exit code 0 if remaining sources ok, 1 otherwise
- [ ] No blocked sources referenced in script

**Step 2 (shared-policy hookup, ONLY if owner APPROVE):**
- [ ] EDGAR/FRED/Tiingo/Alpaca probes use shared policy
- [ ] GitHub repo probes unchanged (use `gh api`)
- [ ] Global `MIN_GAP_S = 2.0` preserved
- [ ] Script still runs and produces valid JSON output
- [ ] `uv run pytest -q` (if any health_check tests exist)
- [ ] `uv run ruff check` clean

## Engineer → Verifier → Reviewer gate

1. **Engineer**:
   - Remove blocked probes (Step 1)
   - If owner APPROVE Step 2: integrate shared policy
   - Run script manually to verify output
   - Run pytest + ruff
2. **Verifier** (independent, read-only):
   - Confirm blocked probes removed
   - Confirm remaining probes work (if running script)
   - Confirm no blocked sources referenced
3. **Reviewer**: Approve if scope-limited, blocked probes removed

## Stop condition

- If approved probes are accidentally removed → STOP, revert
- If blocked sources are added → BLOCKED, violates CLAUDE.md

## Dependencies

- Owner decision on Step 2 (keep independent vs. integrate shared policy)
- AUD-05B APPROVED (shared policy primitive exists, if using Option B)

## Owner decision items

1. **Step 1**: Remove `akshare/EastMoney` probe? (APPROVE → proceed)
2. **Step 2**: Integrate shared policy or keep health_check independent?
   - **Option A**: Keep independent (simpler, recommended)
   - **Option B**: Integrate shared policy (more unified)

## Success metrics

- Blocked probes removed
- Approved probes still work
- Health check script still useful for monitoring
- (If Step 2 APPROVE) Shared policy integrated cleanly

## Note on risk

Health_check is **low risk** because:
- It's auxiliary monitoring, not in the research pipeline
- It runs off-peak via cron (not during real research runs)
- The global 2.0s gap already provides politeness
- Even if health_check fails, research code is unaffected
