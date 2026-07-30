# E3 forward-live — implementation plan

> **Status:** DRAFT planning artifact (produced by the Architect role, 2026-07-30; read-only).
> Implements [ADR-008](../decisions/ADR-008-launch-e3-and-broaden-nulls.md) against the frozen
> research pre-reg `docs/phase-e3-preregistration.md`. **No code yet** — the owner must resolve the
> blocking questions in §3 (Q1/Q2/Q3/Q6) before Slice 1 freeze. Changing the pre-reg requires a new ADR.
> **Branch note:** E3 is net-new; branch from `main` (or the current branch if PR #1 is not yet merged).

## 1. Architecture overview

E3 is a forward-live **commit-then-reveal** process that extends the project's "sha256-before-result"
anti-leakage anchor from **per-run** granularity (`scripts/phase_e1_run.py:130-134`) to **per-prediction**.
It reuses, not reinvents: the append-only ledger (`runs/ledger.jsonl`), the forward-discipline exemplar
(`src/aionis/ingest/reddit_sentiment.py`), the two-arm scoring seam (`src/aionis/eval/two_arm.py:79`),
the idempotent LLM cache (`src/aionis/extraction/extract.py`), and the pinned-provider router
(`src/aionis/extraction/providers.py:52`). The keystone is a new forward-ledger core enforcing
commit-before-reveal; everything downstream is reversible if that keystone is right.

### 1.1 The six load-bearing pieces

**(1) Commit-then-reveal forward ledger.** Each month-end prediction is sealed by a sha256 commitment
**before** its t+21 outcome realizes. Pre-reg §9 (`docs/phase-e3-preregistration.md:214-222`): forward
rows reuse `runs/ledger.jsonl` with new `phase:"E3"` + `event:"forward_*"` types:
- `forward_iset_frozen` — PIT I_t snapshot manifest: `{predict_ts, iset_sha256, snapshot_manifest}` (§3 step 1).
- `forward_prediction_committed` — sealed prediction: `{predict_ts, target_t(=t+21), config_sha256, iset_sha256, scores_sha256, provider, provider_cutoff}` (§5).
- `forward_outcome_scored` — the reveal: `{target_t, ic_point, arm}` appended only after realization (§3 step 5).

The per-ticker score vector is NOT inlined into JSONL; it is written to an immutable artifact
`runs/forward/<config_sig>/scores_<predict_ts>.parquet` and referenced by `scores_sha256` — mirroring
how `save_run` writes parquet IC series under `runs/results/<sig>/` (`src/aionis/reporting/results.py:153-169`).
Append primitive = existing `reporting/run_log.log_run`.

**(2) Forward scheduler.** Cadence = month-end; trigger = NYSE last trading session's close of each
calendar month (pre-reg §3 "严格交易月末日收盘后"). `predict_ts` = that session's close. Fires
`scripts/forward_commit.py` at t and `scripts/forward_score.py` at t+21. Politeness + bounded retry
carry over verbatim from `src/aionis/ingest/stakes_13d.py:48-86`. No-lookahead is structural: only data
with `filed/released ≤ predict_ts` enters the snapshot.

**(3) Monthly scoring loop.** As `target_t` outcomes realize, `forward_score` reveals each committed
prediction, computes the month's cross-sectional rank-IC (reusing `eval/rank_ic.rank_ic_monthly`),
appends `forward_outcome_scored`, and accumulates the forward differential IC series (arm_e13 − arm_base)
with MBB-DM + Newey-West HAC (§3 step 5). Writes `runs/forward/<sig>/ic_forward.parquet` + `summary_forward.json`
in the same additive-schema shape as `save_run` so the dashboard's random-walk-band renderer
(`dashboard/app.py:539`) is reusable.

**(4) Forward ingest.** Differs from existing PIT ingest in one way: forward = "as-of now, never revised,
never backfilled." Three sources, each a snapshot-on-arrival collector following `reddit_sentiment.py`:
- **13D/13D-A** — poll `submissions_{cik}.json` for `filing_date` in `(last_poll_ts, t]` (reuse `stakes_13d.py:152-186`).
- **FRED macro (CPI/NFP)** — ALFRED scheduled-release surprise, vintage as-of join (reuse `features/macro_surprise.py`).
- **8-K earnings (Item 2.02)** — NEW: form-type filter on EDGAR submissions, reusing the `ingest/fundamentals.py` EDGAR stack (§4).

**(5) Dashboard Forward-IC tab.** New `st.tabs` entry reading ONLY `phase:"E3"` + `event:"forward_*"`.
Shows: accrued forward differential IC + CI, committed-vs-revealed count, months-to-parity progress
(vs ~42-month parity, brief §3), random-walk 95% band. Labeled **EXPLORATORY until the calendar gate is met** (§1).

**(6) LLM extraction.** Structural-only, inherited unchanged from E2: live call outputs only causal edges
`{sic_sector, direction, mechanism_keyword, horizon_bucket}` — never `market_impact`/`expected_return`/
`historical_similarity`. Rides the idempotent sha256 cache (`extract.py:21-56`) so re-runs make no token
spend and are bit-identical (H6). Provider pinned via `build_providers(only_enabled=...)`; pool = GLM/
SiliconFlow/ModelScope only.

### 1.2 Data/control flow (one month-end cycle)

```
month-end session close t ──►
  1. FREEZE  forward ingest (3 srcs) snapshot-on-arrival → I_t manifest → iset_sha256   (forward_iset_frozen)      [Slice 2]
  2. FIT     frozen LightGBM on PIT rows (date ≤ t−21, label realizable);
             E1 propagation + E2 causal-broadcast as extra_features; single-fit (NOT CV) → ŷ_t          [Slice 3]
  3. COMMIT  scores_<t>.parquet + {predict_ts,target_t,config_sha256,iset_sha256,scores_sha256,provider}
             → ledger (forward_prediction_committed)   ◄── BEFORE any outcome            [Slice 1]
  ── 21 sessions later (t+21) ──
  4. REVEAL  realized r_{t→t+21} (Tiingo/Alpaca) → rank-IC contribution (forward_outcome_scored) — append, never overwrite   [Slice 4]
  5. ACCUM   forward differential IC series + NW-HAC + random-walk band → runs/forward/<sig>/ic_forward.parquet             [Slice 4]
  6. RENDER  dashboard Forward-IC tab (E3 rows only)                                                                            [Slice 5]
```

**Key distinction vs the backtest path:** E3 does NOT reuse `eval/cv.py:purged_group_kfold_splits` for
scoring. At prediction time t there is no future test block — the model is **fit once on all PIT-as-of-t
rows** (date ≤ t−21 so labels are realizable) and predicts the single cross-section at t. Leakage
protection is not CV overlap; it is that the t+21 label is physically unknown at t. Reusable seams:
`_clean_panel` + `build_selection_panel` + `LightGBMFrozen.fit_predict` (`two_arm.py:26-43,102-120`),
single-fit mode, and the `extra_features=` path (`two_arm.py:94-101`).

## 2. Zero-leakage invariants (the acceptance gates)

What "zero by construction" reduces to. Each is testable.

| # | Invariant | Mechanism | Test |
|---|---|---|---|
| **I1** | Commit-before-reveal (per-prediction) | `forward_prediction_committed` appended with `predict_ts < target_t`; reveal guard refuses `forward_outcome_scored` until wall-clock ≥ target_t | reveal at t<target → REJECTED; reveal at t≥target → appended; no scored row without its commit |
| **I2** | Immutability of committed predictions | `scores_sha256` frozen at commit; re-scoring only APPENDS; re-score idempotent (H6) | re-run scoring → identical `ic_point`; commit row's `scores_sha256` unchanged; mutated scores → hash mismatch detected |
| **I3** | Forward-only ingest, no backfill | each collector asserts `event_ts ≤ snapshot_ts` (monotonic forward clock); raw archives immutable; cumulative parquet concat never overwrites | no row with `filed/released > snapshot_ts`; raw sha256 stable; prior rows preserved on append |
| **I4** | PIT-as-of-t training (no lookahead) | fit set excludes `date > t−21` (label embargo); every feature resolves to data with `as-of ≤ t`; no forward-fill of universe (`constituents_on(t)`) | assert `max(train_date) ≤ t−embargo`; no feature references `as-of > t` |
| **I5** | Structural-only LLM extraction | schema validation rejects any extraction carrying `market_impact`/`expected_return`/`historical_similarity`; closed `mechanism_keyword` enumeration | malformed extraction with forbidden field → rejected |
| **I6** | Single pinned provider | confirmatory forward uses `build_providers(only_enabled=[pinned])`; provider change = new `config_sha256` = new sequence | every commit row records `provider`+`provider_cutoff`; a swap yields a distinct sig |
| **I7** | H6 determinism | `n_jobs=1`, seeds `0`, version-pinned (`uv.lock`), LLM idempotent cache → bit-identical scores on re-run over frozen I_t | re-run `forward-commit` on frozen snapshot → identical `scores_sha256` |
| **I8** | Headline isolation | the frozen headline `config_sig`'s commit rows all share one `config_sha256`; refinements = new sig = parallel sequence (§5) | headline sig's rows share one config hash; refined config has a distinct sig |
| **I9** | Separation from confirmatory ledger | forward rows (`phase:"E3"`) never touch the 4 `confirmatory:first` nulls | dashboard forward tab queries ONLY `forward_*`; published-null table queries ONLY `confirmatory:first`; no path mixes them |

## 3. Open questions — OWNER DECISIONS (2026-07-30)

**Resolved (unblock Slice 1 freeze):**
- **Q1 provider → GLM** (pinned; longevity/cost basis; E2 cutoff rationale N/A). *A prior memory
  flagged GLM as test-only; the 1–2 mo shadow validates GLM's production-readiness before the
  irreversible headline — if it proves unstable during shadow, switch before ignition.*
- **Q6 launch → shadow 1–2 months first** (exploratory `mode:exploratory` forward commits), then headline ignition.
- **Q2 trigger → NYSE month-end session, 16:00 ET close** (default adopted).
- **Q3 universe → PIT S&P 500 `constituents_on(t)`** (default adopted; matches Phase B).
- **Q4 writer → new `reporting/forward_results.py` sibling** (default adopted).
- **Q7 cadence → monthly** (default adopted).

**Deferred (do not block Slice 1):** Q5 (placebo day-1 vs deferred), Q8 (scheduler host).

*Original framing of each question retained below for context.*

---

### Original questions

**🔴 BLOCKS Slice 1 freeze (determine the irreversible headline `config_sig`):**

1. **Which single provider to pin — and on what basis?** Pre-reg §8.0 freezes "单一 LLM 提供方" but does
   not name it. **E2's cutoff-earliest rationale does NOT transfer to E3** (§2.2 dissolves the cutoff gate
   — the forward event hasn't occurred). So the E3 pinning criterion is **provider longevity/stability +
   cost** (will it still serve in 5 years? §10 #5), not cutoff. Genuine gap — needs an owner decision.
2. **Exact cadence + trigger timestamp.** Confirm: trigger = NYSE last trading session of the calendar
   month, `predict_ts` = that session's 16:00 ET close. Resolve via `pandas_market_calendars` (already a dep).
   Load-bearing for reproducibility.
3. **Universe confirmation.** Confirm forward universe = PIT S&P 500 `constituents_on(t)` at each month-end
   (no forward-fill, no today-snapshot), same as Phase B. Load-bearing for cross-sectional comparability.
4. *(writer)* Forward-result writer: reuse `save_run` or a new sibling `reporting/forward_results.py`?
   **Recommend the new sibling** for clean separation (technical — Orchestrator can adopt).
6. **Shadow/dry-run period before headline ignition?** Once the headline `config_sig` is committed it
   cannot be tuned without starting a new sequence (§5; ADR-008 irreversibility). A 1–2 month
   **exploratory forward window** (commits labeled `mode:exploratory`) could de-risk the frozen causal
   schema before the irrevocable headline starts. Owner decides.

**🟡 Can resolve later (do not block Slice 1):**

5. **Placebo as a launch-day third sequence?** §6 lists a no-edge placebo forward control — roughly
   **doubles LLM cost** from launch. Day-1 or deferred until the headline has traction?
7. **Cadence vs calendar-to-power.** ~42 months to parity at monthly (brief §3). §7 hints weekly (if
   PIT-safe) accelerates N but freezes monthly. Confirm monthly at launch; do not over-engineer weekly now.
8. **Operational host for the scheduler.** CLAUDE.md mandates "no lingering background processes." A
   monthly cron / scheduled CI Action firing the two scripts is the natural fit — needs a host decision.
   Data-rot risk (§10 #6) is the dominant long-term operational risk.

## 4. Work-breakdown (S/M/L, dependency-ordered)

| Slice | Objective | Size / Risk | Anti-leakage | Depends on |
|---|---|---|---|---|
| **1 — Forward-ledger commit-reveal core** | append-only forward ledger primitives + per-prediction commit/reveal row types + sha256 commitments. **The keystone.** Net-new `src/aionis/reporting/forward_ledger.py` + `runs/forward/<sig>/scores_<ts>.parquet`; reuse `run_log.log_run`. | S–M / **HIGH** | I1, I2 | — (first to freeze, TDD with Slice 7 ledger tests) |
| **2 — Forward PIT-as-of-t ingest (3 srcs)** | snapshot-on-arrival collectors (13D poll / FRED-ALFRED / 8-K earnings). Net-new `src/aionis/ingest/forward/` pkg. | M / MEDIUM | I3 | 1 |
| **3 — Forward commit step (fit-on-I_t → commit)** | at month-end t, FREEZE I_t, fit frozen LightGBM on PIT rows (date ≤ t−21), run E1 propagation + E2 causal-broadcast as `extra_features`, produce arm_base + arm_e13 scores, COMMIT. Net-new `src/aionis/eval/forward_commit.py` + `scripts/forward_commit.py` + CLI; `PHASE_E3_NO_LEDGER=1` dry-run. | M–L / **HIGH** | I4, I5, I6, I7 | 1, 2 |
| **4 — Forward scoring + accumulation** | reveal as `target_t` realizes, month rank-IC, accumulate forward differential IC + MBB-DM + NW-HAC + random-walk band. Net-new `src/aionis/eval/forward_score.py` + `scripts/forward_score.py`; writes `ic_forward.parquet` + `summary_forward.json`. | M / MEDIUM | I1, I2, I9 | 1, 3 |
| **5 — Dashboard Forward-IC tab** | new `st.tabs` entry (accrued IC+CI, committed-vs-revealed, months-to-parity, random-walk band, EXPLORATORY banner). Extends `dashboard/app.py`. | S–M / LOW | I9 | 1, 4 |
| **6 — Forward scheduler (monthly wiring)** | deterministic NYSE month-end trigger; politeness+retry inherited; `--dry-run` resolves next trigger. Net-new `scripts/forward_tick.py`; host = Q8. | S / MEDIUM (operational) | trigger tied to PIT session | 3, 4 |
| **7 — E2E smoke + invariant test suite** | hermetic E2E (commit → fast-forward 21 → score → accumulate) + full I1–I9 gate suite. **Write alongside Slice 1 (TDD).** Net-new `tests/test_forward_e2e.py`, `tests/test_forward_ledger_invariants.py`. | M / LOW | IS the gate suite | all (ledger-portion lands with Slice 1) |

## 5. What E3 must NOT touch

- **The 4 published nulls** — the `confirmatory:first` rows + their `runs/results/<sig>/` dirs. Forward rows carry `phase:"E3"` (I9).
- **The frozen backtest configs** — Phase B `arm_base` (sig `17245a75…`) etc. E3 *references* arm_base as the forward base arm but never mutates it.
- **The frozen pre-reg** (`docs/phase-e3-preregistration.md`) — changing it requires a new ADR.
- **The structural-only extraction schema** (ERL / causal-edge) — inherited, not relaxed.
- **The provider allowlist** — GLM/SiliconFlow/ModelScope only; Gemini/TokenHub never re-added.
- **The append-only ledger's existing rows** — forward_* rows are APPENDED; no edit/overwrite of any prior row.

## 6. Recommendation — implementation ORDER + first slice

Build the keystone first: **Slice 1 (forward-ledger commit-reveal core) together with the ledger-portion
of Slice 7's invariant tests, TDD-style.** That pairing encodes the per-prediction sha256-before-result
invariant — the single architectural commitment that makes E3 "zero by construction," and the one thing
expensive to change later. Once Slice 1 + its gates are green, run Slices 2 (forward ingest) and 3
(forward commit) in parallel, then Slice 4 (scoring), then Slices 5 (dashboard) and 6 (scheduler),
closing with the full Slice 7 E2E.

**Do NOT freeze Slice 1 until the owner resolves Open Questions 1 (pinned provider + rationale),
2 (trigger timestamp), 3 (universe), and 6 (shadow vs headline-ignition)** — those four determine the
irreversible headline `config_sig` and cannot be retroactively tuned without starting a new forward
sequence (pre-reg §5).
