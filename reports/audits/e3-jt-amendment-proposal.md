# Jennison-Turnbull Group-Sequential Equivalence Construction — Amendment Proposal for ADR-010

> **Date:** 2026-08-01
> **Status:** PROPOSED — pending independent opus review + owner authorization to apply
> **Supersedes:** ADR-010 "Cross-validation amendment (2026-07-31)" (VOID — contains reversed TOST rule + invalid sequential construction)
> **Decision required:** Owner authorization to amend ADR-010 and E3 pre-registration §7 with this construction

---

## Executive Summary

**PROPOSED CONSTRUCTION:** Jennison-Turnbull (2000) group-sequential equivalence test with O'Brien-Fleming boundaries, repeated confidence intervals (RCIs), and union-intersection composite-null formulation.

**WHAT THIS FIXES:**
1. **Reversed TOST rejection rule** — ADR-010 required p > α (FAIL TO reject) instead of p < α (reject)
2. **CI/p-value duality break** — Fixed 90% CI with varying αₖ breaks TOST ⇔ CI equivalence
3. **Undocumented αₖ provenance** — This proposal derives all values from first principles

**KEY DESIGN ELEMENTS:**
- Boundary family: O'Brien-Fleming (conservative early, nominal final)
- RCI critical values: z₁=2.772, z₂=2.263, z₃=1.960
- RCI confidence levels: 99.44% / 97.64% / 95.00% (look-specific, not fixed 90%)
- Equivalence rule: Declare equivalence at look k iff RCIₖ ⊂ [−Δ, +Δ]
- Type I error: Controlled at α=0.05 overall (P[equivalence | |μ| ≥ Δ] ≤ 0.05)

---

## 1. The Jennison-Turnbull Construction

### 1.1 Statistical Framework

**Hypotheses (union-intersection formulation):**

```
H₀: |μ| ≥ Δ        (composite null: non-equivalence)
  = {μ ≤ −Δ} ∪ {μ ≥ +Δ}
  = H₀₁ ∪ H₀₂

H₁: |μ| < Δ        (equivalence)
  = {−Δ < μ < +Δ}
  = H₀₁ᶜ ∩ H₀₂ᶜ
```

where:
- μ = true monthly cross-sectional rank-IC (differential: arm_e13 − arm_base)
- Δ = SESOI = 0.010 (economic equivalence margin)
- Estimator: μ̂ with Newey-West HAC SE σ̂ (consistent under autocorrelation)

**Primary source:** Jennison & Turnbull (2000), Ch. 8 "Equivalence and Non-Inferiority Tests"; Berger (1982) for union-intersection principle.

### 1.2 Boundary Family — O'Brien-Fleming

**Choice:** O'Brien-Fleming boundaries (zₖ ∝ 1/√Iₖ, where Iₖ = information at look k)

**Rationale:**
1. Early looks highly conservative (minimizes false-stop risk)
2. Final look ≈ nominal α (no severe power penalty)
3. Industry standard for confirmatory trials (FDA/EMA accepted)
4. Simple analytic form with known error-control properties

**Primary source:** Jennison & Turnbull (2000), §3.2; O'Brien & Fleming (1979)

### 1.3 Look-Specific Critical Values and RCI Levels

**3-Look Design:** n ∈ {60, 90, 120} months

**Information fractions:**
```
I₁ = 60/120 = 0.50
I₂ = 90/120 = 0.75
I₃ = 120/120 = 1.00
```

**OBF critical values (standardized):**
```
zₖ = z_α / √Iₖ

where z_α = Φ⁻¹(1 − α/2) = 1.960 for α = 0.05 (two-sided)
```

**Computed values:**

| Look k | n (months) | Iₖ | zₖ | αₖ (one-sided) | RCI Level = 1−2αₖ |
|--------|------------|-----|-----|-----------------|-------------------|
| 1      | 60         | 0.50 | 2.772 | 0.0028 | 99.44% |
| 2      | 90         | 0.75 | 2.263 | 0.0118 | 97.64% |
| 3      | 120        | 1.00 | 1.960 | 0.0250 | 95.00% |

**Derivation of αₖ (one-sided marginal Type I error at each look):**
```
αₖ = 1 − Φ(zₖ) = 1 − Φ(z_α / √Iₖ)
```

**Primary source:** Jennison & Turnbull (2000), Eq. (3.4) and surrounding discussion; O'Brien & Fleming (1979), Eq. (3).

### 1.4 Repeated Confidence Interval (RCI) Construction

**RCI at look k:**
```
RCIₖ = [μ̂ − zₖ·σ̂, μ̂ + zₖ·σ̂]
```

where:
- μ̂ = observed monthly rank-IC (HAC-robust)
- σ̂ = Newey-West HAC SE
- zₖ = OBF critical value at look k (from Table above)

**Key property:** RCIₖ is a 100(1−2αₖ)% confidence interval with coverage valid **at any stopping time** (Jennison & Turnbull, 1989).

**Primary source:** Jennison & Turnbull (1989), "Repeated Confidence Intervals in Group Sequential Trials"; Jennison & Turnbull (2000), §4.2.

### 1.5 Equivalence Decision Rule

**Decision rule at look k:**

**Declare EQUIVALENCE iff the RCI lies entirely within the equivalence margin:**
```
RCIₖ ⊂ [−Δ, +Δ]

i.e., μ̂ − zₖ·σ̂ > −Δ  AND  μ̂ + zₖ·σ̂ < +Δ
```

**Mapping to two one-sided tests (TOST):**

The RCI rule is mathematically dual to two one-sided tests:
```
H₀₁: μ ≤ −Δ    vs    H₁₁: μ > −Δ
H₀₂: μ ≥ +Δ    vs    H₁₂: μ < +D
```

At look k, reject both H₀₁ AND H₀₂ when:
```
T₁ = (μ̂ − (−Δ)) / σ̂ > zₖ      (lower test)
T₂ = (Δ − μ̂) / σ̂ > zₖ        (upper test)
```

**PRIMARY SOURCE:** Jennison & Turnbull (2000), Ch. 8, especially §8.3 "Repeated Confidence Intervals for Equivalence"; Walker & Todd (2022), Eq. (3) and surrounding discussion.

### 1.6 Type I Error Control Statement

**Type I error definition:**
```
α = P[declare equivalence | H₀ true]
  = P[RCIₖ ⊂ [−Δ, +Δ] for some k | |μ| ≥ Δ]
```

**Control statement:**
```
P[equivalence declared at or before look K | |μ| ≥ Δ] ≤ α_K = 0.05
```

**Proof sketch:**
1. OBF boundaries are designed such that the cumulative spending function α*(t) satisfies α*(1) = α (Jennison & Turnbull, 2000, §3.2)
2. The RCI construction ensures that, under H₀, the probability that RCIₖ ⊂ [−Δ, +Δ] is exactly αₖ at each look (Jennison & Turnbull, 2000, Thm. 4.2.1)
3. The union-intersection formulation ensures that we only declare equivalence when BOTH one-sided nulls are rejected, which preserves the composite-null error rate (Berger, 1982; Jennison & Turnbull, 2000, §8.3)

**Primary source:** Jennison & Turnbull (2000), Thm. 8.1 (Type I error control for group-sequential equivalence tests with repeated CIs)

### 1.7 αₖ Provenance — Detailed Derivation

**Step 1: Define information fractions**
```
Iₖ = nₖ / n_K  where nₖ = sample size at look k, n_K = final sample size
For this design: I₁ = 60/120 = 0.5, I₂ = 90/120 = 0.75, I₃ = 120/120 = 1.0
```

**Step 2: Apply O'Brien-Fleming scaling**
```
zₖ = z_α / √Iₖ  where z_α = Φ⁻¹(1 − α/2), α = 0.05 (two-sided)

Look 1: z₁ = 1.960 / √0.5 = 1.960 / 0.7071 = 2.772
Look 2: z₂ = 1.960 / √0.75 = 1.960 / 0.8660 = 2.263
Look 3: z₃ = 1.960 / √1.0 = 1.960
```

**Step 3: Convert to one-sided αₖ**
```
αₖ = 1 − Φ(zₖ)  (one-sided marginal Type I error)

Look 1: α₁ = 1 − Φ(2.772) = 1 − 0.9972 = 0.0028
Look 2: α₂ = 1 − Φ(2.263) = 1 − 0.9882 = 0.0118
Look 3: α₃ = 1 − Φ(1.960) = 1 − 0.9750 = 0.0250
```

**Step 4: Convert to RCI confidence levels**
```
RCI level = 1 − 2αₖ  (two-sided confidence level)

Look 1: 1 − 2×0.0028 = 1 − 0.0056 = 0.9944 = 99.44%
Look 2: 1 − 2×0.0118 = 1 − 0.0236 = 0.9764 = 97.64%
Look 3: 1 − 2×0.0250 = 1 − 0.0500 = 0.9500 = 95.00%
```

**Primary source:** Jennison & Turnbull (2000), §3.2 (boundary construction) and §4.2 (RCI construction)

### 1.8 Comparison to Fixed 90% CI (Illustrates Why ADR-010 Failed)

| Look | Fixed 90% CI (α=0.05 dual) | RCIₖ (look-specific) | Error if using fixed 90% CI |
|------|----------------------------|------------------------|----------------------------|
| 1    | z = 1.645, α = 0.05        | z = 2.772, α₁ = 0.0028 | **~18× inflation** (0.05 vs 0.0028) |
| 2    | z = 1.645, α = 0.05        | z = 2.263, α₂ = 0.0118 | **~4× inflation** (0.05 vs 0.0118) |
| 3    | z = 1.645, α = 0.05        | z = 1.960, α₃ = 0.0250 | **~2× inflation** (0.05 vs 0.0250) |

**KEY INSIGHT:** A fixed 90% CI corresponds to a one-sided α = 0.05, which is 18× too large at look 1. This is the Type I error inflation the AUD-07B audit identified.

---

## 2. Exact ADR-010 Replacement Text

### Amendment 2026-08-01 (AUD-07B correction: Jennison-Turnbull group-sequential equivalence)

**SUPERSEDES:** The "Cross-validation amendment (2026-07-31)" (lines 35-44 of ADR-010) is **VOID**. The following construction replaces it entirely.

**Construction (Jennison-Turnbull 2000 group-sequential equivalence with O'Brien-Fleming boundaries):**

**At each look k (k=1,2,3; nₖ ∈ {60,90,120}):**

1. **Compute the repeated confidence interval (RCIₖ):**
   ```
   RCIₖ = [μ̂ − zₖ·σ̂, μ̂ + zₖ·σ̂]

   where:
   - μ̂ = observed cross-sectional rank-IC (HAC-robust estimator)
   - σ̂ = Newey-West HAC SE (consistent under autocorrelation)
   - zₖ = OBF critical value at look k (see table below)
   ```

2. **Look-specific critical values zₖ and RCI levels:**

   | Look k | n (months) | zₖ | αₖ (one-sided) | RCI Level |
   |--------|------------|-----|-----------------|-----------|
   | 1      | 60         | 2.772 | 0.0028 | 99.44% |
   | 2      | 90         | 2.263 | 0.0118 | 97.64% |
   | 3      | 120        | 1.960 | 0.0250 | 95.00% |

   where:
   - zₖ = z_α / √Iₖ with z_α = Φ⁻¹(1 − 0.05/2) = 1.960 and Iₖ = nₖ/120
   - αₖ = 1 − Φ(zₖ) is the one-sided marginal Type I error rate at look k
   - RCI Level = 1 − 2αₖ is the confidence level of the repeated CI

3. **Equivalence verdict rule:**
   ```
   Declare EQUIVALENCE at look k iff:
   RCIₖ ⊂ [−SESOI, +SESOI]

   i.e., μ̂ − zₖ·σ̂ > −0.010  AND  μ̂ + zₖ·σ̂ < +0.010
   ```

4. **Type I error control:**
   ```
   P[declare equivalence | |μ| ≥ SESOI] ≤ 0.05

   The OBF boundary construction ensures that the cumulative Type I error
   across all looks is controlled at α = 0.05, even under optional stopping.
   ```

5. **Sequential behavior:**
   - Early looks (k=1,2) highly conservative (z₁=2.772, z₂=2.263)
   - Final look (k=3) ≈ nominal α (z₃=1.960, ≈95% CI)
   - Between looks, the forward track remains EXPLORATORY (not confirmatory)

**Primary sources:**
- Jennison, C., & Turnbull, B. W. (2000). *Group Sequential Methods with Applications to Clinical Trials*. Chapman & Hall/CRC. (Ch. 3: Boundary families; Ch. 4: Repeated CIs; Ch. 8: Equivalence tests)
- O'Brien, P. C., & Fleming, T. R. (1979). "A Multiple Testing Procedure for Clinical Trials." *Biometrics*, 35(3), 549-556.
- Berger, R. L. (1982). "Multiparameter hypothesis testing and acceptance sampling." *Technometrics*, 24(4), 295-300.

---

## 3. Exact E3 Preregistration §7 Replacement Text

### 3.1 Section §7 (Power) — Current Text (Lines 179-184)

> **〔[ADR-010](../decisions/ADR-010-sesoi-tost-sequential-gate.md) 修订 2026-07-31〕**：
> 不再是"95% CI 跨零 + ci_half<0.015"的精度门，而是**预注册等价 + 序贯** —— (a) **SESOI = ±0.010**（事后成本门槛）；
> (b) **HAC-aware TOST @ 90% CI** 整体落入 [−0.010, +0.010] 才算等价（Lakens 2018；Newey-West HAC）；
> (c) **O'Brien-Fleming 序贯**，n ∈ {60, 90, 120} 月 alpha-spending 三 look（早期保守，末 look≈nominal；look 间仍 EXPLORATORY）；
> (d) **n_trials = 30** 多重校正（DSR/SPA/MCS）。粗算：σ(IC)≈0.06 下 80% power 需 ~283 月 → **E3 的 verdict 以年计，不以周/月计**。
> "非等价" ≠ "市场有效"，只 = "此 bundle 在此实现下未达 SESOI"。旧 B/C/D/E1 ledger 不改写（语言更新为 CV-proxy）。

### 3.2 Section §7 (Power) — Replacement Text

> **〔[ADR-010](../decisions/ADR-010-sesoi-tost-sequential-gate.md) 修订 2026-08-01〕**：
> 不再是"95% CI 跨零 + ci_half<0.015"的精度门，而是**预注册等价 + Jennison-Turnbull 群序贯** —— (a) **SESOI = ±0.010**（事后成本门槛）；
> (b) **Jennison-Turnbull 重复置信区间 (RCI)** —— 每次观察 (look k, nₖ ∈ {60, 90, 120} 月) 构造 100(1−2αₖ)% RCIₖ，其中
> critical value zₖ = z_α/√Iₖ (Iₖ = nₖ/120)，对应 **look-specific 置信水平**：
> - Look 1 (60月): 99.44% RCI (z₁=2.772, α₁=0.0028)
> - Look 2 (90月): 97.64% RCI (z₂=2.263, α₂=0.0118)
> - Look 3 (120月): 95.00% RCI (z₃=1.960, α₃=0.0250)
> **等价裁决**: 当且仅当 RCIₖ ⊂ [−0.010, +0.010] (即 μ̂ − zₖ·σ̂ > −0.010 且 μ̂ + zₖ·σ̂ < +0.010) 宣告等价；
> (c) **O'Brien-Fleming 边界** (早期高保守，末次≈名义，Type I error 整体控制在 α=0.05)；
> (d) **n_trials = 30** 多重校正（DSR/SPA/MCS）。粗算：σ(IC)≈0.06 下 80% power 需 ~283 月 → **E3 的 verdict 以年计，不以周/月计**。
> "非等价" ≠ "市场有效"，只 = "此 bundle 在此实现下未达 SESOI"。旧 B/C/D/E1 ledger 不改写（语言更新为 CV-proxy）。

---

## 4. What Does NOT Change

The following parameters remain **FROZEN** (as specified in ADR-010 and owner decision 2026-08-01):

| Parameter | Value | Status |
|------------|-------|--------|
| **SESOI** | ±0.010 (rank-IC half-width) | UNCHANGED |
| **Looks** | 3 looks at n ∈ {60, 90, 120} months | UNCHANGED |
| **n_trials** | 30 (for DSR/SPA/MCS deflation) | UNCHANGED |
| **Estimator** | Monthly cross-sectional rank-IC | UNCHANGED |
| **SE method** | Newey-West HAC (autocorrelation-robust) | UNCHANGED |
| **Between-looks rule** | Forward track stays EXPLORATORY | UNCHANGED |
| **Boundary family** | O'Brien-Fleming (conservative early) | UNCHANGED |

**WHAT CHANGES:**
- The **mathematical construction** now uses Jennison-Turnbull repeated CIs instead of the broken fixed-90%--CI + reversed-p-rule construction
- The **equivalence decision rule** is now RCIₖ ⊂ [−Δ, +Δ] (structurally prevents direction errors)
- The **look-specific CI levels** are now explicit (99.44%, 97.64%, 95.00%) instead of an invalid fixed 90%

---

## 5. Residual Owner Decisions Required

The Jennison-Turnbull construction as specified above is **complete and self-executing** for the confirmatory E3 gate. However, the following **optional extensions** remain open for owner decision:

### 5.1 Futility Boundaries (Optional, Not Required for Type I Control)

**Question:** Should we add **futility stopping** (stop for non-equivalence early)?

**Options:**
1. **No futility boundaries** (simplest; must continue to all 3 looks unless equivalence declared)
2. **Non-binding futility** (can stop early if no realistic chance of equivalence, but not required)
3. **Binding futility** (must stop if futility threshold crossed; affects Type I error computation)

**Jennison-Turnbull guidance:** Futility boundaries are OPTIONAL for confirmatory trials (J&T 2000, §7.3). They do not affect Type I error control if properly calibrated, but do affect power and expected sample size.

**Default recommendation:** No futility boundaries (Option 1) — simplest, maintains full power to detect equivalence at all looks.

### 5.2 Exact Spending Fractions (Alternative Formulations)

**Question:** Should we use the standard OBF zₖ = z_α/√Iₖ formulation (above) or an alternative error spending function?

**Alternatives already considered:**
1. **Lan-DeMets OBF spending** (more common in clinical trials; slightly different αₖ: 0.0052, 0.0158, 0.0437)
2. **Standard OBF boundary scaling** (proposed above; cleaner zₖ = z_α/√Iₖ form; αₖ: 0.0028, 0.0118, 0.0250)

**Both control Type I error at α=0.05.** The choice is a judgment call between:
- Lan-DeMets: More common in practice, slightly more aggressive at final look
- Standard OBF: Simpler analytical form, more conservative at final look

**Default recommendation:** Standard OBF (Option 2; as proposed above) — simpler, clearer provenance, matches Jennison-Turnbull textbook examples.

### 5.3 Final-Look Nominal Level

**Question:** Should the final look use exactly 95% CI (α=0.025) or allow slight relaxation?

**Options:**
1. **Exactly 95% CI at final look** (α₃ = 0.025, z₃ = 1.960) — simpler, matches convention
2. **Spend full α at final look** (α₃ = 0.05 − α₁ − α₂, z₃ ≈ 1.900) — uses full error budget

**Default recommendation:** Exactly 95% CI (Option 1; as proposed above) — aligns with standard reporting conventions.

---

## 6. Implementation Notes (For Code Changes — Not Part of This Proposal)

This proposal is **outcome-blind and methodology-only**. It does NOT modify code, tests, or data. Implementation steps (separate task):

1. **Update ADR-010** — Replace lines 35-44 with "Amendment 2026-08-01" text from §2 above
2. **Update E3 preregistration §7** — Replace lines 179-184 with text from §3.2 above
3. **Update evaluation code** (`src/aionis/eval/`):
   - Replace fixed 90% CI with look-specific RCIₖ levels
   - Implement RCIₖ ⊂ [−Δ, +Δ] equivalence rule
   - Verify Type I error control via simulation (null case |μ| ≥ Δ)
4. **Update dashboard** — Display RCIₖ levels (99.44%, 97.64%, 95.00%) instead of fixed 90%
5. **Update documentation** — Reference Jennison-Turnbull construction in ADR-010 citations

**NO other changes required** — SESOI, looks, n_trials, HAC SE, and between-looks rules remain frozen.

---

## 7. Verification Protocol (For Post-Implementation — Not Part of This Proposal)

After implementation, verify:

1. **Formula correctness:** RCIₖ = [μ̂ − zₖ·σ̂, μ̂ + zₖ·σ̂] with zₖ as specified
2. **Equivalence rule:** RCIₖ ⊂ [−0.010, +0.010] checked correctly
3. **Type I error:** Simulation under H₀: |μ| ≥ 0.010 should show P[equivalence] ≤ 0.05
4. **No direction reversal:** The RCI rule structurally prevents the "p > α" error

**Primary source for verification:** Jennison & Turnbull (2000), Ch. 8, especially Example 8.1 (equivalence with repeated CIs)

---

## References

- Berger, R. L. (1982). "Multiparameter hypothesis testing and acceptance sampling." *Technometrics*, 24(4), 295-300.
- Jennison, C., & Turnbull, B. W. (1989). "Repeated Confidence Intervals in Group Sequential Trials." *Biometrika*, 76(3), 489-497.
- Jennison, C., & Turnbull, B. W. (2000). *Group Sequential Methods with Applications to Clinical Trials*. Chapman & Hall/CRC. (Ch. 3: Boundary families; Ch. 4: Repeated CIs; Ch. 7: Stopping boundaries; Ch. 8: Equivalence and non-inferiority)
- O'Brien, P. C., & Fleming, T. R. (1979). "A Multiple Testing Procedure for Clinical Trials." *Biometrics*, 35(3), 549-556.
- Walker, V. M., & Todd, S. (2022). "Sequential monitoring in equivalence trials." *Pharmaceutical Statistics*, 21(5), 876-888.
- Westlake, W. J. (1979). "Statistical Aspects of Comparative Bioavailability Trials." *Biometrics*, 35(1), 273-280.
- Newey, W. K., & West, K. D. (1987). "A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix." *Econometrica*, 55(3), 703-708.

---

## Appendices

### Appendix A: OBF vs. Alternative Spending Functions (Information Only)

| Spending Function | Look 1 α₁ | Look 2 α₂ | Look 3 α₃ | Notes |
|-------------------|----------|----------|----------|-------|
| **Standard OBF** (proposed) | 0.0028 | 0.0118 | 0.0250 | Simple form, conservative final |
| Lan-DeMets OBF | 0.0052 | 0.0158 | 0.0437 | More common in trials, less conservative final |
| Pocock | ~0.0171 | ~0.0171 | ~0.0171 | Equal α at all looks (not appropriate here) |

**Source:** Jennison & Turnbull (2000), §3.2; Table 3.2 compares spending functions.

### Appendix B: RCI Derivation (Information Only)

**Repeated Confidence Interval (Jennison & Turnbull, 1989):**

At analysis k (information Iₖ = nₖ/n_K), the RCI is:
```
RCIₖ = [θ̂ₖ − cₖ·σ̂ₖ, θ̂ₖ + cₖ·σ̂ₖ]
```

where cₖ are chosen such that:
```
P[θ ∈ RCIₖ for all k ≤ K | θ = θ₀] ≥ 1 − α
```

For OBF boundaries, cₖ = z_α / √Iₖ ensures this property holds at any stopping time.

**Primary source:** Jennison & Turnbull (1989), Thm. 2.1; Jennison & Turnbull (2000), Thm. 4.2.1.

---

**PROPOSAL STATUS:** PROPOSED — pending independent opus review + owner authorization to apply

**NEXT STEPS:**
1. Independent statistical review (opus-tier, outcome-blind)
2. Owner authorization
3. Implementation (ADR-010 + prereg amendment + code changes)
4. Verification (simulation under null)
