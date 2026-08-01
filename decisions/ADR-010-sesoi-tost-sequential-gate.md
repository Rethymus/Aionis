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

### Amendment 2026-08-01 (AUD-07B correction: Jennison-Turnbull group-sequential equivalence)

**The "Cross-validation amendment (2026-07-31)" above is VOID.** An independent double-opus audit
(`reports/audits/e3-tost-sequential-correction-review.md`, AUD-07B) confirmed it had two CRITICAL defects:
(i) the TOST rejection direction was reversed ("p-values exceed αₖ" — TOST rejects each one-sided null when
p < α, per Schuirmann 1987); (ii) a fixed 90% CI paired with look-specific αₖ breaks the TOST⇔CI duality at
looks 2–3 (first-look Type I inflation ~9.6×). Owner decision 2026-08-01 (option B) replaces it with a
recognized Jennison-Turnbull (2000) group-sequential equivalence construction. Frozen params UNCHANGED:
SESOI ±0.010, looks n ∈ {60,90,120}, n_trials = 30, Newey-West HAC SE, forward track EXPLORATORY between looks.

**Construction (Jennison-Turnbull group-sequential equivalence; O'Brien-Fleming boundaries; repeated CIs):**
At each look k (k=1,2,3; nₖ ∈ {60,90,120}) compute the repeated confidence interval
RCIₖ = [μ̂ − zₖ·σ̂, μ̂ + zₖ·σ̂], where μ̂ = observed cross-sectional rank-IC (HAC), σ̂ = Newey-West HAC SE,
zₖ = z_α/√Iₖ with z_α = Φ⁻¹(1−0.05/2) = 1.960 and Iₖ = nₖ/120.

| Look k | n (months) | Iₖ | zₖ | αₖ (one-sided) | RCI level (1−2αₖ) |
|---|---|---|---|---|---|
| 1 | 60  | 0.50 | 2.772 | 0.0028 | 99.44% |
| 2 | 90  | 0.75 | 2.263 | 0.0118 | 97.64% |
| 3 | 120 | 1.00 | 1.960 | 0.0250 | 95.00% |

αₖ = 1−Φ(zₖ) is the one-sided marginal Type I error at look k; the RCI level varies with k (NOT a fixed 90%),
which restores the TOST⇔CI duality at every look.

**Equivalence verdict at look k:** declare EQUIVALENCE iff RCIₖ ⊂ [−SESOI, +SESOI]
(i.e., μ̂ − zₖ·σ̂ > −0.010 AND μ̂ + zₖ·σ̂ < +0.010). This union–intersection rule is dual to rejecting both
one-sided nulls (Berger 1982) and **structurally prevents the reversed-direction error** (no "p exceed α" clause).

**Type I error control:** P(declare equivalence at or before look K | |μ| ≥ SESOI) ≤ 0.05 under the OBF
group-sequential boundary, even under optional stopping (Jennison & Turnbull 2000, Thm. 8.1 / §8.3;
O'Brien & Fleming 1979).

**Sub-choices ratified 2026-08-01 (owner):** standard OBF zₖ = z_α/√Iₖ (over Lan-DeMets OBF — more conservative
early, appropriate since false-positive equivalence is the cardinal sin); **no futility boundaries**; exactly
95% RCI at the final look. Reopen via the re-evaluation trigger if a different spending function or futility is
later warranted. Design + independent opus review: `reports/audits/e3-jt-amendment-proposal.md`.

**Primary sources:** Jennison & Turnbull, *Group Sequential Methods with Applications to Clinical Trials* (2000),
Ch. 3/4/8; Jennison & Turnbull (1989) Biometrika 76(3) (repeated CIs); O'Brien & Fleming (1979) Biometrics 35(3);
Berger (1982) Technometrics 24(4) (union–intersection); Walker & Todd (2022) Pharm. Stat. 21(5) (sequential equivalence).

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
