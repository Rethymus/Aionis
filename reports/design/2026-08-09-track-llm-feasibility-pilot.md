# Track LLM Phase-0 feasibility pilot — coverage + projected-cost verdict

> Owner directive (2026-08-09): after the C+D combined analysis, build the most
> valuable Track-LLM content to optimization. This is **Phase 0** — the
> de-risking gate that converts "is D worth a frozen prereg?" from speculation to
> evidence. **Status: EXECUTED (local gates); PROPOSED analysis, owner-decision
> required.** No code/config/ledger/frozen surface changed; no OOS rank-IC observed.
>
> Tool: `scripts/track_llm_feasibility_pilot.py` (reproducible). Tests: `tests/test_track_llm_feasibility_pilot.py` (8 hermetic, green).

## 0. TL;DR

- **Both local gates are GREEN → Track LLM is feasible on PIT-coverage + projected cost.**
- **G1 (CIK resolution): 100%** of the actual US OOS universe (2021-2026, 533 distinct tickers) resolves to a SEC CIK. The cik_resolver's known "~60% gap" is a *historical-universe* (1996-2025) concern; for the OOS window it is **not** binding.
- **G2 (projected token cost): ~11.71M tokens, one-time** (5576 10-K MD&A extractions; idempotent accession-keyed cache → re-runs cost zero LLM tokens). Tractable under the project's token discipline.
- **Remaining gate (needs creds): G3/G4** — real per-call token cost + temp=0 stability calibration on a sampled 10-K excerpt. Projection is encouraging; the owner runs this before `config_committed`.
- **Recommendation:** proceed to the **PROPOSED prereg** (`docs/track-llm-preregistration.md`); owner calibrates G3/G4 with creds, then decides freeze vs scope-down.

## 1. What was measured (and how)

| Gate | Question | Method | Needs |
|---|---|---|---|
| **G1** | Can OOS-universe tickers map to SEC filers (10-K coverage proxy)? | CIK resolution rate over the cached SEC snapshot, per year, for the real `runs/track_c_confirmatory_oos_scores.parquet` US universe | local (no network/creds) |
| **G2** | Is the one-time extraction backfill affordable? | ticker-years (resolved) × per-call token estimate (10-K MD&A excerpt ≤2000 tok in + ~100 out) | local |
| G3 | Real per-call token cost (calibrate G2's estimate) | sample N CIKs, fetch one 10-K MD&A excerpt, real GLM call, measure usage | creds + network |
| G4 | temp=0 extraction determinism | same excerpt twice → agreement | creds + network |

G1 + G2 are **executed** (local, reproducible via the pilot). G3/G4 are scaffolded (`--measure-llm N`) and run at freeze time.

## 2. Results (real, from `uv run python scripts/track_llm_feasibility_pilot.py`)

### G1 — CIK resolution (US OOS universe)
- Window: **2021-2026**. Distinct US tickers: **533**. Resolved: **533 → 100.0%**.
- Per-year: 2021 (462, 100%) · 2022 (472, 100%) · 2023 (490, 100%) · 2024 (499, 100%) · 2025 (496, 100%) · 2026 (492, 100%).
- Ticker-years resolved: **2911** (each ≈ one annual 10-K in the OOS window).
- Unresolved sample: **none**.

> **Why this contradicts the cik_resolver "~60% gap" docstring:** that gap is measured over the *full historical* S&P universe (1996-2025, ~1126 tickers incl. long-delisted FB/BBT/ANTM/EKDKQ). The OOS window is 2021-2026 large-cap — current-ish firms that the SEC's current snapshot covers. Renamed-but-existing firms (FB→META) share a stable CIK and resolve correctly. The gap binds only for the deep-historical tail, not the OOS window.

### G2 — projected one-time token cost
- Tokens/10-K (MD&A excerpt ≤2000 in + ~100 JSON out): **2100**.
- OOS filings (from ticker-years): **2911**. Train filings (533 × 5 yr, conservative floor): **2665**.
- **Total filings: 5576 → ~11.71M tokens, one-time.**
- Idempotent accession-keyed cache ⇒ the research phase (OOS IC) reads only cache; **re-runs cost zero LLM tokens**.

### Verdict
```
G1 (coverage): GREEN (rate 1.00 ≥ 0.90)
G2 (cost):     GREEN (11.71M < 20M)
→ FEASIBLE — proceed to PROPOSED prereg + owner GO.
```

## 3. Caveats (honest)

1. **Resolution ≠ verified filing dates.** A resolved CIK means the company files 10-Ks (near-universal for S&P 500 large-cap over 2016-2026), but the pilot does not spot-check actual `filed_date` coverage per ticker. This is a freeze-time check (G3 sample fetches real 10-Ks, confirming dates).
2. **G2 is a projection, not a measurement.** The 2100 tok/call estimate assumes a truncated MD&A excerpt. Real per-call cost (G3) could differ ±30%; the green band (<20M) has headroom.
3. **temp=0 determinism unconfirmed.** G4 (same excerpt twice → agreement) runs at freeze; until then H6 relies on the cache-pin contract (research phase = cache reads = bit-identical; extraction phase = one-time).
4. **Universe scope is US-only for v1.** CN filings (different regime, 16-K-equivalent) are out of scope; the CN OOS arm is not extended by Track LLM v1.

## 4. Recommendation

1. **Proceed to the PROPOSED prereg** (`docs/track-llm-preregistration.md`) — the disciplined spec is now evidence-backed.
2. **Owner calibrates G3/G4** with creds before any freeze: `uv run python scripts/track_llm_feasibility_pilot.py --measure-llm 8`. If real per-call cost > ~2× projection or temp=0 unstable → scope down (excerpt length / universe) before `config_committed`.
3. **No OOS rank-IC, no ledger, no frozen surface touched.** Track LLM remains PROPOSED until owner GO + `config_committed`.

## 5. Boundary

This pilot + report are pure feasibility analysis: `scripts/track_llm_feasibility_pilot.py` (+ tests) + this doc + the PROPOSED prereg + state. **0 ledger / frozen config / prereg-freeze / ADR / E3 / OOS outcome** changed. Track C climax (#49 null) and Track Adaptive (#54 null) stand unchanged.
