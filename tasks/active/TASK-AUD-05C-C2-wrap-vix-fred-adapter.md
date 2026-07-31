# AUD-05C-C2 — Wrap VIX FRED SDK with approved adapter

- 编号: AUD-05C-C2
- Parent: AUD-05C
- 状态: **READY (awaiting owner GO after AUD-05C disposition-complete)**
- Priority: **P0**
- Size: **M**
- Risk: **MEDIUM** (VIX is critical risk-premium feature; must preserve PIT/no-revision/cache/ledger semantics)
- 目标: 为 VIX `fetch_vix` / `_download_vix_vintages` 构建 approved FRED SDK wrapper，保持 ADR-003 VIX PIT/no-revision/cache/ledger 语义
- 依赖: AUD-05C disposition-complete → owner GO → Engineer → Verifier → Reviewer
- Owner gate: **必须确认** VIX 是核心特征（CBOE VIX daily close = first risk-premium main-line feature）且允许继续使用 FRED

## Scope

**Current state (FACT):**
- `ingest/vix.py:fetch_vix()` (lines 96-152):
  - Uses `pandas_datareader.get_data_fred("VIXCLS", ...)` (SDK-owned HTTP, no shared policy)
  - Has cache layer at `data/cache/vix_cls.parquet`
  - Appends `data_ingest` ledger row on actual fetch
  - Seeded `FRED_API_KEY` from `settings.fred_api_key` before call
- `ingest/vix.py:_download_vix_vintages()` (lines 158-195):
  - Uses `pandas_datareader.get_data_fred("VIXCLS", ...)` (SDK-owned HTTP, no shared policy)
  - Synthesizes self-dated vintages (VIXCLS is NOT vintage-tracked on ALFRED)
  - Called by `fetch_vix_vintages()` → `vix_as_of()` (PIT-safe accessor)

**Disposition: C2 — approved FRED SDK wrapper task**
- VIX is CRITICAL (CBOE VIX = first risk-premium main-line feature per module docstring)
- FRED is ALLOWED source (per CLAUDE.md: "Working sources: FRED/ALFRED, Tiingo, Alpaca, EDGAR")
- Must preserve ADR-003 VIX semantics: PIT via no-revision contract (G3), cache + ledger discipline
- Wrapper should integrate with shared `http_policy.py` (AUD-05B primitive) for host-spacing

## Allowed changes

- `src/aionis/ingest/http_policy.py` (if needed): Add FRED-specific adapter or helper
- `ingest/vix.py`:
  - Modify `fetch_vix()` to use approved FRED adapter instead of raw `pandas_datareader`
  - Modify `_download_vix_vintages()` to use approved FRED adapter
  - Preserve ALL existing semantics:
    - Cache layer at `data/cache/vix_cls.parquet`
    - Ledger row append on actual fetch
    - Self-dated vintage synthesis
    - Function signatures unchanged
    - PIT discipline via no-revision contract (G3)
- `tests/test_vix.py`:
  - Add hermetic tests for FRED adapter integration (fake clock, no network)
  - Preserve existing cache/ledger/vintage tests

## Forbidden

- Do NOT change VIX PIT semantics (no-revision contract G3)
- Do NOT remove or bypass cache layer
- Do NOT alter ledger append discipline
- Do NOT change function signatures (backward compatibility)
- Do NOT modify ADR-003 or frozen VIX config
- Do NOT run actual FRED fetches in tests (use mocks/fakes)

## Acceptance criteria

- [ ] `fetch_vix()` uses approved FRED adapter with shared host-spacing policy
- [ ] `_download_vix_vintages()` uses approved FRED adapter
- [ ] Cache hit → no HTTP call (same as before)
- [ ] Cache miss → HTTP call through shared policy (≥2s spacing, retry discipline)
- [ ] Ledger row appended on actual fetch (same as before)
- [ ] Self-dated vintage synthesis unchanged
- [ ] PIT as-of join (`vix_as_of()`) produces identical results to current implementation
- [ ] Hermetic tests pass (fake clock, no network)
- [ ] `uv run pytest -q` all tests pass
- [ ] `uv run ruff check` clean
- [ ] No direct `pandas_datareader` HTTP calls remain in `vix.py`

## Engineer → Verifier → Reviewer gate

1. **Engineer**:
   - Implement FRED adapter integration (leverage `http_policy.py` primitive)
   - Add hermetic tests (fake clock, mock FRED responses)
   - Run pytest + ruff + frozen-surface checks
   - Record evidence of identical cache/ledger/vintage behavior
2. **Verifier** (independent, read-only):
   - Confirm no raw `pandas_datareader` HTTP calls remain
   - Confirm cache/ledger discipline unchanged
   - Run tests from clean virtualenv
   - Verify VIX outputs identical to baseline (using cached fixtures)
3. **Reviewer**: Approve if FRED adapter integrated, semantics preserved, no blocking issues

## Success metrics

- VIX fetch through approved FRED adapter with shared host-spacing
- Cache/ledger/vintage semantics 100% preserved
- PIT outputs identical to current implementation
- No regressions in existing VIX tests

## Stop condition

- If cache/ledger discipline changes → STOP, revert, re-do
- If PIT semantics change → BLOCKED, violates ADR-003
- If frozen spec/ADR modified → BLOCKED, out of scope

## Dependencies

- AUD-05B must be APPROVED (shared policy primitive exists and is frozen)
- Owner GO confirming VIX is critical and FRED is approved source

## Technical notes

- VIXCLS is NOT vintage-tracked on ALFRED (single current vintage; realtime endpoint returns 400)
- PIT safety comes from NO-REVISION contract (G3), NOT revision tracking
- Self-dated vintages (realtime_start == date) are the honest representation of an unrevised series
- The wrapper should use the same `http_policy.py` primitive as AUD-05B adapters
