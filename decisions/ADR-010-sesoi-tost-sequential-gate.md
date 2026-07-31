# ADR-010 — E3 statistical gate: SESOI / HAC-TOST / O'Brien-Fleming sequential (freeze before outcome inspection)

- **date:** 2026-07-31
- **status:** accepted
- **extends:** [ADR-008](ADR-008-launch-e3-and-broaden-nulls.md), [ADR-009](ADR-009-e3-hybrid-causal-layer.md); the 2026-07-31 research audit (`reports/audits/2026-07-31-quant-llm-research-audit.md` §5.1, §5.3)
- **decision owner:** Rethymus

## Background
The 2026-07-31 audit found E3's publishability rule ("differential 95% CI crosses 0 AND ci_half<0.015")
controls precision but is **not** a pre-registered equivalence test (no SESOI/TOST; "non-significant ≠
equivalent" — Altman & Bland; Lakens 2018), and that monthly accrual + a "first-time-CI-gate-met" verdict
invites optional stopping (inflates Type I error). AUD-07 = freeze the statistical gate **before** any
outcome-bearing E3 inspection (audit P1; owner decisions 2026-07-31).

## Candidates considered
- **SESOI ±0.005** (very strict) — ~94 years to 80% power → infeasible for a personal multi-decade track.
- **SESOI ±0.015** (the old precision-only gate) — not pre-registered; allows sub-cost marginal effects.
- **Fixed-N verdict month** — simple, but inflexible (must wait even given strong early evidence).
- **Time-uniform confidence sequences** (Howard et al. 2021) — always-valid at any stopping time, but wider
  early and unfamiliar to finance audiences.

## Chosen — owner decisions 2026-07-31
1. **SESOI = ±0.010** (rank-IC half-width). Below ±0.010 is economically equivalent to zero after transaction
   costs (turnover / slippage / implementation delay). At σ(IC)≈0.06 → ~283 months to 80% power (≈24 y) —
   **expected** for anti-leakage research; the null remains the likely and publishable outcome.
2. **Equivalence test = HAC-aware TOST at 90% CI** (Lakens 2018; Newey-West HAC SE for monthly-IC
   autocorrelation). The 90% CI must fall **entirely within [−SESOI, +SESOI]** for an equivalence verdict.
   Replaces the precision-only 95% rule (which conflated "non-significant" with "equivalent").
3. **Sequential / optional-stopping control = O'Brien-Fleming group-sequential**, 3 looks at
   n ∈ {60, 90, 120} months; alpha-spending (α₁ ≈ 0.0052 / α₂ ≈ 0.0158 / α₃ ≈ 0.0437) — early looks
   conservative, final ≈ nominal. Between looks the forward track stays **EXPLORATORY** (not confirmatory).
4. **Trial registry n_trials = 30** for DSR / Hansen-SPA / Hansen-MCS deflation (historical B/C/D/E1 +
   horizon sweeps + placebo + prospective E3 / provider / schema variants).

### Cross-validation amendment (2026-07-31) — equivalence + sequential construction
Independent read-only cross-check (3 parallel researchers) CONFIRMED the SESOI, the HAC-TOST @ 90% CI, and
the O'Brien-Fleming alpha-spending values — but **FLAGGED** that OF boundaries were designed for
**superiority** testing, whereas TOST is a **composite null** (two one-sided tests). Directly applying OF
alpha-spending to the 90% CI does **not** by itself control the equivalence Type I error at each look.
The required construction (per Walker & Todd 2022; Phillips et al. 2024 — sequential equivalence /
non-inferiority): **at each look k, an EQUIVALENCE verdict requires BOTH (i) the 90% HAC-CI falls entirely
within [−SESOI, +SESOI] AND (ii) both one-sided TOST p-values exceed the OF-adjusted αₖ at that look.**
A more complex alternative (full equivalence-specific repeated confidence intervals) is deferred unless
this dual condition proves insufficient at AUD-07 implementation.

## Cost
$0 (statistical methodology; no runtime/data cost).

## Applicability bounds
- **The OLD B/C/D/E1 ledger is NOT rewritten.** Their public language is updated per the audit (purged
  cross-fitted / CV-proxy, not chronological OOS; B has no paired CI; C not strict equivalence) but the
  ledger rows stand. The new gate governs **forward** E3 + any new config.
- **No E3 outcome-bearing inspection before this freeze** — met (frozen here). Exploratory shadow does not
  observe outcome-bearing metrics as confirmatory.
- The 4 frozen values are registry-level; changing any one = a new forward sequence (pre-reg §5) + a new ADR.
- This ADR does **not** ignite E3 (still needs AUD-06 + a separate owner GO) and does **not** add factors,
  agents, or providers.

## Re-evaluation trigger
Re-open if **any** of:
1. An owner economic re-analysis changes the post-cost SESOI.
2. Provider/data drift forces a new E3 sequence where a different sequential design is warranted.
3. Time-uniform confidence sequences become the low-frequency-finance standard (then consider switching from
   group-sequential).
4. The trial-registry scope changes materially (e.g., a licensed factor library is added → n_trials re-baselined).
