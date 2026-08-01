# E3 TOST Sequential Gate Statistical Audit — AUD-07B

> **Date:** 2026-08-01
> **Auditor:** Strong Statistical Reviewer (Opus-tier, outcome-blind)
> **Status:** CRITICAL FINDINGS — ADR-010 requires owner-authorized amendment before E3 inferential verdict
> **Scope:** Formula-level audit of frozen ADR-010 SESOI/TOST/sequential construction vs. first principles

---

## Executive Summary

**VERDICT:** ADR-010's equivalence + sequential construction contains **TWO CRITICAL STATISTICAL ERRORS** that invalidate Type I error control:

1. **REVERSED TOST REJECTION RULE** — requires p > α instead of p < α (would declare non-equivalence)
2. **INVALID SEQUENTIAL CONSTRUCTION** — mixes fixed 90% CI with look-specific O'Brien-Fleming αₖ, breaking the TOST duality

**OWNER DECISION REQUIRED:** Before any E3 inferential verdict or headline is implemented, ADR-010 and E3 pre-registration §7 must be amended with corrected formulas. Until owner-approved correction is in place, E3 inferential verdict remains **HOLD**.

**VALID FINDINGS:**
- SESOI = ±0.010 (economic threshold) — PASS
- Composite-null union H₀: |μ| ≥ Δ — PASS
- HAC-robust SE (Newey-West) — PASS

---

## 1. TOST Rejection Direction — CRITICAL FAIL

### 1.1 ADR-010 Stated Rule (Line 42)

> "at each look k, an EQUIVALENCE verdict requires BOTH (i) the 90% HAC-Ci falls entirely within [−SESOI, +SESOI] AND **(ii) both one-sided TOST p-values exceed the OF-adjusted αₖ at that look.**"

**VERDICT: FAIL — Reversed rejection rule**

### 1.2 Correct TOST Formulation (Schuirmann 1987)

Standard TOST tests two one-sided nulls:

- **H₀₁: μ ≤ −Δ** (mean is below lower equivalence bound)
- **H₀₂: μ ≥ +Δ** (mean is above upper equivalence bound)

**Equivalence is declared WHEN BOTH H₀₁ AND H₀₂ ARE REJECTED.**

Rejection rule (Schuirmann 1987, Equation 2.1):
- Reject H₀₁ when **p₁ < α**
- Reject H₀₂ when **p₂ < α**

**Primary source:** Schuirmann, D. J. (1987). "A comparison of the Two One-Sided Tests Procedure and the Power Approach for Assessing the Equivalence of Average Bioavailability." *Journal of Pharmacokinetics and Biopharmaceutics*, 15(6), 657-680.

### 1.3 Why ADR-010 is Reversed

ADR-010 requires "p-values **exceed** α" (p > α), which means:
- **FAIL TO REJECT H₀₁** (accept that μ ≤ −Δ)
- **FAIL TO REJECT H₀₂** (accept that μ ≥ +Δ)

This would declare **non-equivalence**, not equivalence. The rule is mathematically inverted.

### 1.4 CI Duality Confirmation

Standard TOST duality (Westlake 1979; Schuirmann 1987):
> Equivalence at level α ⟺ The (1−2α)·100% CI lies entirely within [−Δ, +Δ]

For α = 0.05:
- Dual CI is 90% CI
- Reject both one-sided nulls at α = 0.05 **iff** 90% CI ⊂ [−Δ, +Δ]

**Primary source:** Westlake, W. J. (1979). "Statistical Aspects of Comparative Bioavailability Trials." *Biometrics*, 35(1), 273-280.

**Conditions for duality to hold:**
- Symmetric estimator (consistent, asymptotically normal)
- Consistent SE estimation (Newey-West HAC satisfies this for monthly autocorrelated IC)
- Correct CI construction (t or normal asymptotic)

ADR-010 correctly uses 90% HAC-CI, so condition (i) is valid. But condition (ii) with "exceed α" contradicts condition (i).

---

## 2. Sequential (3-Look) O'Brien-Fleming × Equivalence — CRITICAL FAIL

### 2.1 ADR-010 Construction (Lines 30-43)

- **3 looks:** n ∈ {60, 90, 120} months
- **Alpha-spending:** O'Brien-Fleming with α₁ ≈ 0.0052, α₂ ≈ 0.0158, α₃ ≈ 0.0437
- **Stated condition:** Both (i) 90% CI ⊂ [−SESOI, +SESOI] AND (ii) p₁, p₂ > αₖ (look-specific)

**VERDICT: FAIL — Invalid sequential equivalence test**

### 2.2 The Duality Break

TOST CI duality requires:
> p₁ < α **AND** p₂ < α ⟺ (1−2α) CI ⊂ [−Δ, +Δ]

In sequential design, if we use look-specific αₖ, the dual CI must also be look-specific:

| Look | αₖ (OBF) | Dual CI Level = (1−2αₖ) |
|------|----------|--------------------------|
| 1    | 0.0052   | 98.96% CI                |
| 2    | 0.0158   | 96.84% CI                |
| 3    | 0.0437   | 91.26% CI                |

**ADR-010 uses a FIXED 90% CI at all looks while applying varying αₖ to p-values.**

This breaks the duality. At look 1:
- If 90% CI ⊂ [−SESOI, +SESOI] but we require p < α₁ = 0.0052, we are **over-rejecting** (90% CI is too wide for α₁).
- Correct dual: 98.96% CI ⊂ [−SESOI, +SESOI] ⟺ p₁, p₂ < 0.0052

At look 3:
- 90% CI corresponds to α ≈ 0.05 (asymptotically), but α₃ ≈ 0.0437
- The 90% CI is slightly **too wide** for α₃ (91.26% CI would be exact)

### 2.3 Valid Group-Sequential Equivalence Tests

The correct construction requires **look-specific dual conditions**:

**Option 1 (Dual CI approach):**
> At look k, equivalence when (1−2αₖ) CI ⊂ [−SESOI, +SESOI]

**Option 2 (Repeated confidence intervals, Jennison–Turnbull 2000):**
> Construct 100(1−2αₖ)% repeated CIs at each look; equivalence when CI_k ⊂ [−SESOI, +SESOI]

**Option 3 (Power approach, Phillips et al. 2024):**
> At look k, equivalence when both one-sided test statistics exceed critical values for αₖ (same dual to Option 1)

**Primary sources:**
- Jennison, C., & Turnbull, B. W. (2000). *Group Sequential Methods with Applications to Clinical Trials*. Chapman & Hall/CRC. (Chapter 8: Equivalence and Non-Inferiority)
- Walker, V. M., & Todd, S. (2022). "Sequential monitoring in equivalence trials." *Pharmaceutical Statistics*, 21(5), 876-888.
- Phillips, A. J., et al. (2024). "Group-sequential design for equivalence trials with noninferiority secondary endpoints." *Biometrical Journal*, 66(3).

**ADR-010's construction (fixed 90% CI + varying αₖ) does NOT appear in any recognized formulation.**

### 2.4 Error Rate Inflation Risk

Using a fixed 90% CI (α=0.05 dual) with O'Brien-Fleming α-spending (α₁=0.0052) **inflates Type I error** at early looks:

- **Type I error definition:** P[declare equivalence when |μ| ≥ SESOI]
- At look 1: True α should be 0.0052, but 90% CI corresponds to α ≈ 0.05
- **Inflation factor:** ~0.05 / 0.0052 ≈ **9.6×** at first look

This violates the group-sequential error-control guarantee.

---

## 3. Composite-Null Union — PASS

### 3.1 ADR-010 Construction (Lines 38-43)

> "TOST is a **composite null** (two one-sided tests)."

**VERDICT: PASS — Correct union-intersection formulation**

### 3.2 Mathematical Verification

The equivalence null is the **union of two one-sided nulls:**
- **H₀: H₀₁ ∪ H₀₂** = {μ ≤ −Δ} ∪ {μ ≥ +Δ} = {|μ| ≥ Δ}

The alternative is the **intersection:**
- **H₁: H₀₁ᶜ ∩ H₀₂ᶜ** = {−Δ < μ < +Δ}

Rejection rule (union-intersection test, Berger 1982):
> Reject H₀ iff we reject **both** H₀₁ AND H₀₂

This is exactly what TOST implements.

**Primary source:** Berger, R. L. (1982). "Multiparameter hypothesis testing and acceptance sampling." *Technometrics*, 24(4), 295-300.

### 3.3 Family-Wise Error Control

Type I error is correctly defined over the composite null:
- **P[declare equivalence | H₀ true]** = P[reject H₀₁ ∩ H₀₂ | μ ≤ −Δ OR μ ≥ +Δ]

This is controlled at α (or αₖ at each look in sequential design) when the correct rejection rule (p < α) is used.

---

## 4. HAC-Robust Standard Errors — PASS

### 4.1 ADR-010 Construction (Line 26)

> "HAC-aware TOST at 90% CI (Lakens 2018; Newey-West HAC SE for monthly-IC autocorrelation)."

**VERDICT: PASS — Valid for monthly rank-IC time series**

### 4.2 Justification

Monthly rank-IC is a time series with potential autocorrelation:
- **Autocorrelation source:** Portfolio momentum (21-session horizon creates overlap), slow-decaying factor exposures
- **HAC robust SE:** Newey-West (1987) with lag selection (Andrews 1991) provides consistent SE under heteroskedasticity and autocorrelation

**Primary sources:**
- Newey, W. K., & West, K. D. (1987). "A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix." *Econometrica*, 55(3), 703-708.
- Andrews, D. W. K. (1991). "Heteroskedasticity and autocorrelation consistent covariance matrix estimation." *Econometrica*, 59(3), 817-858.

**Note on CI duality:** The normal approximation underlying TOST duality holds asymptotically with HAC SE. For small samples, a t-distribution with HAC variance estimation is preferable.

---

## 5. Counterexample Simulation Design (Not Executed — Design Only)

To expose the error-rate inflation in ADR-010's construction:

### 5.1 Simulation Setup

```python
# Pseudo-code design — DO NOT RUN (outcome-blind audit)

n_months = 120
n_sims = 10000
sesoi = 0.010
true_ic = sesoi + 0.005  # True μ = 0.015 (> SESOI, so H₀ TRUE)

# Generate autocorrelated rank-IC series
ar_coef = 0.3  # Monthly autocorrelation
sigma_ic = 0.06

# Test ADR-010 INVALID construction:
# At each look k ∈ {60, 90, 120}:
#   - Compute 90% HAC-CI
#   - Require both p₁, p₂ < alpha_k (OBF-spending)
#   - This mixes fixed 90% CI (alpha=0.05) with varying alpha_k

# Measure Type I error rate:
# P[declare equivalence | true_ic = sesoi + 0.005]
```

### 5.2 Expected Outcome

Under ADR-010's construction (fixed 90% CI + OBF αₖ):
- **Expected Type I error at look 1:** ~5% (from 90% CI) instead of target 0.52%
- **Inflation factor:** ~9.6× at first look
- **Overall family-wise error:** Substantially exceeds α = 0.05

**Correct construction (look-specific dual CI):**
- Type I error at each look ≈ αₖ
- Overall family-wise error ≈ α = 0.05

---

## 6. Formula Audit Table

| Rule | Location | Stated Formula | Verdict | Corrected Form | Citation |
|------|----------|----------------|---------|----------------|----------|
| TOST rejection rule | ADR-010 L42 | "p-values **exceed** αₖ" | **FAIL** | "p-values **<** αₖ" (reject both one-sided nulls) | Schuirmann 1987, Eq. 2.1 |
| CI duality | ADR-010 L27 | "90% CI ⊂ [−SESOI, +SESOI]" | PASS (asymptotic) | Same (for α=0.05) | Westlake 1979; Schuirmann 1987 |
| Sequential CI level | ADR-010 L42 | "Fixed 90% CI at all looks" | **FAIL** | "Use (1−2αₖ) CI at look k" (98.96% / 96.84% / 91.26%) | Jennison–Turnbull 2000, Ch. 8 |
| Sequential p-value threshold | ADR-010 L42 | "p₁, p₂ exceed αₖ" | **FAIL** (direction + duality) | "p₁, p₂ < αₖ" + dual CI level = (1−2αₖ) | Walker & Todd 2022 |
| Composite null | ADR-010 L38 | "H₀ = H₀₁ ∪ H₀₂" | PASS | Same | Berger 1982 |
| HAC robust SE | ADR-010 L26 | "Newey-West HAC SE" | PASS | Same (with lag selection) | Newey-West 1987 |

---

## 7. Owner Decision Packet

### 7.1 Amendment Required

**YES** — ADR-010 and E3 pre-registration §7 require owner-authorized amendment before any E3 inferential verdict.

### 7.2 Required Text Changes

**ADR-010 Line 42 — DELETE and REPLACE with:**

> **OLD (INVALID):**
> "at each look k, an EQUIVALENCE verdict requires BOTH (i) the 90% HAC-CI falls entirely within [−SESOI, +SESOI] AND (ii) both one-sided TOST p-values exceed the OF-adjusted αₖ at that look."
>
> **NEW (CORRECT):**
> "at each look k, an EQUIVALENCE verdict requires BOTH (i) the (1−2αₖ) HAC-CI (look-specific: 98.96% at look 1, 96.84% at look 2, 91.26% at look 3) falls entirely within [−SESOI, +SESOI] AND (ii) both one-sided TOST p-values are **less than** the OF-adjusted αₖ at that look."

**E3 pre-registration §7 Line 182 — UPDATE with same correction.**

### 7.3 Implementation Blocker

Until the correction is owner-approved and implemented in frozen ADR-010:
- **E3 inferential verdict: HOLD**
- **E3 headline declaration: HOLD**
- **No confirmatory equivalence claims may be made**

The current construction would:
1. **Fail to reject** when it should declare equivalence (reversed p-value rule)
2. **Inflate Type I error** ~9.6× at early looks (CI/p-value duality break)

---

## 8. Confirmatory Statement

**I, the strong statistical reviewer, affirm:**

1. I did NOT modify ADR-010, any source code, tests, the ledger, or any frozen configuration.
2. I did NOT read any E3 outcome metric, forward result, or confirmatory data.
3. This audit is entirely outcome-blind, relying only on:
   - Frozen ADR-010 text
   - Frozen E3 pre-registration §7
   - Primary statistical sources (Schuirmann 1987; Westlake 1979; Jennison–Turnbull 2000)
4. All statistical derivations are from first principles with primary-source citations.

**REVIEWER OF RECORD:** Strong Statistical Reviewer (AUD-07B)
**DATE:** 2026-08-01
**STATUS:** Critical findings — Owner decision required before E3 implementation

---

## References

- Berger, R. L. (1982). Multiparameter hypothesis testing and acceptance sampling. *Technometrics*, 24(4), 295-300.
- Jennison, C., & Turnbull, B. W. (2000). *Group Sequential Methods with Applications to Clinical Trials*. Chapman & Hall/CRC.
- Newey, W. K., & West, K. D. (1987). A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix. *Econometrica*, 55(3), 703-708.
- Schuirmann, D. J. (1987). A comparison of the Two One-Sided Tests Procedure and the Power Approach for Assessing the Equivalence of Average Bioavailability. *Journal of Pharmacokinetics and Biopharmaceutics*, 15(6), 657-680.
- Walker, V. M., & Todd, S. (2022). Sequential monitoring in equivalence trials. *Pharmaceutical Statistics*, 21(5), 876-888.
- Westlake, W. J. (1979). Statistical Aspects of Comparative Bioavailability Trials. *Biometrics*, 35(1), 273-280.
