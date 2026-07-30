# ADR-008 — TASK-STRAT verdict: launch E3 (forward-live) + broaden the null family in parallel; reject E2-as-confirmatory

- **date:** 2026-07-30
- **status:** accepted
- **extends:** [ADR-005](ADR-005-e2-underpowered-e3-forward-live.md)
- **decision owner:** Rethymus
- **brief:** `reports/TASK-STRAT-e2-e3-decision-brief.md`

## Background
TASK-STRAT owner gate (`tasks/active/TASK-STRAT-e2-vs-e3-decision.md`): with B/C/D/E1 all null and
publishable, choose the next direction for the causal-prediction (event→sector) vision. The
decision-support brief established:
- **E2-as-backtest is underpowered** — the cutoff gate collapses the 125-month OOS window to ~15
  post-cutoff months → `ci_half ≈ 0.025`, ~1.7× the `0.015` publishability gate; near-certainly
  inconclusive (brief §3).
- **E2-as-confirmatory is architecturally futile** — program §6 (`docs/phase-e-preregistration.md`)
  requires any E2 positive to be E3-forward-reproduced to be credible (brief F7).
- **E3 is the only zero-leakage, powered path to a credible positive**; it costs calendar years and
  is irreversible once launched (brief §4–§5).

## Candidates considered
- **(a) E2-now-as-confirmatory** — **rejected.** Futile per §6 + underpowered.
- **(b) E3-launch-now** — **CHOSEN (track 1).** Begin the multi-year zero-leakage accrual now.
- **(c) E2-as-hypothesis-generator-only** — available as a future cheap E3-de-risker; **not committed** here.
- **(d) HOLD-and-broaden-the-null** — **CHOSEN (track 2, parallel).** Publishable now, zero new leakage.

## Chosen — two parallel tracks
1. **Launch E3 (forward-live, commit-then-reveal) now.** Begin accruing OOS samples the only way a
   credible positive can be earned (or, failing that, converge to a tight publishable null). Starting
   now minimizes the calendar cost — the dominant cost is time, and it accrues independently of track 2.
2. **Continue broadening the null family.** The publishable-now, zero-new-leakage track (horizon-
   robustness now established for all 4 phases; further robustness / universes / SIC-vintage remain
   backlog). This remains the project's publishable output while E3 accrues.

**E2-as-confirmatory is rejected.** E2-as-exploratory (c) remains available to de-risk E3 cheaply and
may be picked up later; it is not part of this verdict.

## Evidence
- 4 confirmatory nulls published (B/C/D/E1); horizon-robust at h∈{10,42} for all 4 (PR #1).
- E2 power math (brief §3): n≈15 post-cutoff → ci_half≈0.025.
- Program §6 hard constraint (brief F7): an E2 positive needs E3 reproduction to be credible.
- E3 leakage is zero-by-construction (brief F4); E2 leakage is non-identifiable (brief F3).
- E3 calendar: ~42–62 months to publishability parity; ~7–16 years to detect a medium effect (brief §3).

## Cost
- **E3 launch = high engineering cost** (forward scheduler + forward ledger + commit-then-reveal +
  monthly scoring loop + 8-K/earnings forward ingest + dashboard forward-IC tab) **+ multi-year
  calendar accrual. Irreversible once launched** — dropping mid-way zeros accrued months.
- **Null-broadening = low/medium cost**, ongoing, reversible.

## Applicability bounds
- The anti-leakage anchors (config-before-result, PurgedGroupKFold+embargo, H6 determinism, PIT data)
  remain inviolable for **both** tracks.
- E3's commit-then-reveal contract extends the project's "sha256-before-result" anchor to
  **per-prediction** granularity.
- The 4 published nulls are **final and untouched** by this verdict.
- E3 implementation must follow its pre-registration (`docs/phase-e3-preregistration.md`); changing
  that pre-reg requires a new ADR.

## Re-evaluation trigger
Re-open this ADR if **any** of:
1. An allowed-pool provider (GLM/SiliconFlow/ModelScope) with cutoff ≲ 2015 appears → E2-as-
   confirmatory becomes viable (per ADR-005's trigger).
2. E3 accrues ~42 months and the result is a null indistinguishable from a large effect → decide
   whether to continue accruing or publish a tight null.
3. A positive E3 result (commit-then-reveal) survives family deflation → transition to a positive-
   claim headline (new ADR).
4. E3 launch engineering cost proves prohibitive → re-scope or defer track 1.
