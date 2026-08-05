# Track C Power Analysis — Statistical Review

**Date**: 2026-08-05
**Reviewer**: Independent Verifier (READ-ONLY)
**Script**: `/home/re/code/Aionis/scripts/track_c_power_analysis.py`
**Output**: `/home/re/code/Aionis/runs/track_c_confirmatory_power_analysis.json`
**Ledger Row**: #49 (confirmatory:first)

---

## Verdict: **APPROVE**

The power analysis is statistically sound and the conclusion that the frozen J-T look schedule is structurally underpowered for SESOI ±0.010 at monthly rank-IC noise σ≈0.10 is supported by both analytic projection and bootstrap evidence.

---

## Findings by Severity

### BLOCKING ISSUES
**None**

### HIGH-SEVERITY ISSUES
**None**

### MEDIUM-SEVERITY ISSUES
**None**

### LOW-SEVERITY ISSUES (Advisory)

1. **AR(1) approximation in analytic projection**
   - The script uses `se(n) = sigma_eff * sqrt((1+rho)/(1-rho)) / sqrt(n)` as an AR(1)-style approximation for HAC SE scaling.
   - This is a reasonable simplification for projection purposes, but it's worth noting that real-world monthly rank-IC autocorrelation may deviate from pure AR(1) structure.
   - The bootstrap method (which does not rely on this approximation) provides validation — both methods agree on the conclusion.
   - **Recommendation**: Document this approximation limitation in comments; consider noting that empirical bootstrap is the more reliable inference method.

2. **Rounding precision in calibration constant**
   - Script hard-codes `OBSERVED_SE_HAC = 0.012625`
   - Ledger #49 actual value: `0.012625171801804603`
   - Difference is negligible (0.000171), but using the full precision would be more rigorous.
   - **Impact**: Minimal — the rounding error is orders of magnitude smaller than the SESOI margin.
   - **Recommendation**: Use full precision from ledger in production code; rounding is acceptable for exploratory analysis.

3. **Block size choice**
   - Script uses `BLOCK_MONTHS = 12` (circular block bootstrap).
   - For monthly financial time series, a 12-month block size is a reasonable default to capture annual seasonality.
   - However, the optimal block size depends on the true autocorrelation structure of rank-IC series.
   - **Recommendation**: Consider sensitivity analysis with block sizes {6, 12, 18} to verify robustness.

---

## Detailed Question Responses

### 1. HAC SE Scaling — Is the AR(1) approximation sound?

**Answer**: **YES** — The AR(1)-style approximation `se(n) = sigma_eff * sqrt((1+rho)/(1-rho)) / sqrt(n)` is a statistically reasonable approach for projecting HAC SE under autocorrelation.

**Statistical justification**:
- The formula derives from the variance of the mean under AR(1) correlation: Var(x̄) = (σ²/n) × [(1+ρ)/(1-ρ)]
- Calibrating `sigma_eff` from the observed `se_hac` at n=71 is sound: you solve for the implicit sigma that reproduces the empirical HAC SE, then project forward.
- This is standard practice in power analysis when you need to project SE to unobserved sample sizes.

**Caveat**: The true autocorrelation structure may not be pure AR(1), but the bootstrap validation (which doesn't assume AR(1)) confirms the conclusion holds empirically.

---

### 2. Block Bootstrap Correctness

**Answer**: **YES** — The circular block bootstrap implementation is correct.

**Verification**:
- **Circular block bootstrap**: Correctly implemented with block size = 12 months (lines 94-97). This preserves autocorrelation structure better than i.i.d. resampling.
- **Newey-West SE** (`_nw_se` function): Correctly implements the standard NW formula with Bartlett kernel weights `1 - lag/(maxlag+1)`.
- **Maxlag selection**: Uses the standard Newey-West automatic rule `maxlag = int(4 * (n/100)^(2/9))`, which is appropriate.
- **Strict-containment check**: Correctly implemented as `|mean| + rci_half < sesoi` (line 107). This is the proper condition for RCI ⊂ [-SESOI, +SESOI].

---

### 3. Min-n Computation — Is the formula correct?

**Answer**: **YES** — The derivation is mathematically sound.

**Verification**:
- Target condition: RCI half-width < SESOI
- RCI half-width = z_k × SE(n) = z_k × [sigma_eff × ar1_factor / sqrt(n)]
- Set z_k × sigma_eff × ar1_factor / sqrt(n) < SESOI
- Solve for n: n > (z_k × sigma_eff × ar1_factor / SESOI)²

The code implements this correctly (lines 132-136):
```python
return float((z_k * sigma_eff * ar1_factor / sesoi) ** 2)
```

---

### 4. The Finding Itself — Is "structurally underpowered" statistically sound?

**Answer**: **YES** — The conclusion is robust and supported by multiple lines of evidence.

**Evidence**:

**Analytic projection** (assuming true mean = 0):
- Look-1 (n=60, z=2.772): RCI_half = 0.03807 ≫ SESOI 0.010 → **infeasible**
- Look-2 (n=90, z=2.263): RCI_half = 0.02538 ≫ SESOI 0.010 → **infeasible**
- Look-3 (n=120, z=1.960): RCI_half = 0.01903 ≫ SESOI 0.010 → **infeasible**

**Bootstrap empirical validation** (2000 samples, actual IC distribution):
- Look-1 (n=60): P(equivalence) = 0.0000
- Look-2 (n=90): P(equivalence) = 0.0000
- Look-3 (n=120): P(equivalence) = 0.0000

**Extended horizon** (even at n=360 months = 30 years):
- At 30 years, RCI_half = 0.01099 ≥ SESOI 0.010 → still not feasible
- Equivalence only becomes feasible at n ≈ 435 months (36 years) for look-3's z=1.960

**Conclusion**: The frozen look schedule (60/90/120 months) is fundamentally incompatible with declaring equivalence at SESOI ±0.010 given the observed noise level σ≈0.10. This is a **design constraint**, not a statistical artifact.

---

### 5. Honesty Check — Does the script overstate findings?

**Answer**: **NO** — The script is appropriately conservative and honest about limitations.

**Evidence**:
- The script explicitly states its assumption: "true mean=0" is a **conservative** benchmark (worst case for equivalence).
- The bootstrap method **embeds the observed mean** (-0.0088), not assuming zero — yet P(equivalence) remains 0.
- The interpretation section (lines 224-231) correctly states: "If analytic RCI half-width at a look exceeds SESOI (with true mean=0), equivalence is structurally infeasible at that look regardless of the observed mean."
- The script does not claim equivalence is impossible in principle — only infeasible **within the frozen look schedule**.
- Extended horizon analysis shows the timeline to feasibility (36+ years), which is honest about what would be required.

**No overstatement detected** — the conclusion "equivalence declaration is infeasible within 120 months" is supported by **both** analytic and bootstrap evidence.

---

### 6. Calibration Constant — Is `OBSERVED_SE_HAC = 0.012625` correct?

**Answer**: **YES** — The value is correct within rounding precision.

**Verification**:
- Ledger #49 shows: `"se_hac": 0.012625171801804603`
- Script uses: `OBSERVED_SE_HAC = 0.012625`
- Difference: 0.000000171801804603 (≈ 0.0014% relative error)

**Impact**: Negligible. This rounding error is orders of magnitude smaller than:
- The SESOI margin (0.010)
- The RCI half-widths (0.019–0.038)
- The observed mean (-0.0088)

**Recommendation**: For maximum rigor, consider using full precision in production code, but this rounding is acceptable for exploratory analysis.

---

## Cross-Reference Verification

### `obf_z` function (`src/aionis/eval/sesoi_gate.py`)
- **OBF formula**: z_k = z_α / √I_k where I_k = looks[k-1] / looks[-1] (information fraction)
- **Verification**:
  - For 3-look design (60, 90, 120) with α=0.05:
  - z_α = Φ⁻¹(1 - 0.05/2) = Φ⁻¹(0.975) = 1.96
  - Look-1: z_1 = 1.96 / √(60/120) = 1.96 / √0.5 = 2.772 ✓
  - Look-2: z_2 = 1.96 / √(90/120) = 1.96 / √0.75 = 2.263 ✓
  - Look-3: z_3 = 1.96 / √(120/120) = 1.96 / 1 = 1.960 ✓
- The script uses this function correctly (line 37 import, lines 165, 183, 190 calls).

### Ledger Row #49
- **Observed se_hac**: 0.012625171801804603 ✓
- **Observed mean_ic**: -0.008840749458819833 ✓
- **n_observed**: 71 months ✓
- **lag1_autocorrelation**: Script computes -0.0282 from the IC series ✓

All cross-references verified.

---

## Reproducibility Check

Re-ran the script successfully:
```bash
$ uv run python scripts/track_c_power_analysis.py
[power] loaded combined_ic: n=71 mean=-0.008841 sigma=0.105841 lag1_rho=-0.0282
[power] calibrated sigma_eff=0.109426 (from observed se_hac=0.012625 at n=71)
...
[power] saved -> runs/track_c_confirmatory_power_analysis.json
```

**Determinism verified**: The script uses `RNG_SEED = 0` (line 47), ensuring reproducible bootstrap results.

---

## Summary

### What the analysis shows
Given the observed monthly rank-IC noise (σ≈0.106) and lag-1 autocorrelation (ρ≈-0.028), the frozen J-T look schedule (60/90/120 months) at SESOI ±0.010 is **structurally underpowered**:

1. **Analytic projection**: Even assuming the most favorable condition (true mean=0), the RCI half-width exceeds SESOI at all three looks.
2. **Bootstrap validation**: Empirical resampling shows P(equivalence) = 0 at all looks under the actual observed IC distribution.
3. **Timeline to feasibility**: Equivalence declaration would require 36-72 years of data, far beyond the 10-year frozen horizon.

### Statistical correctness
- **HAC SE scaling**: AR(1) approximation is reasonable for projection; bootstrap confirms validity.
- **Block bootstrap**: Implementation is correct; circular block bootstrap preserves autocorrelation appropriately.
- **Min-n formula**: Derivation is mathematically sound.
- **Calibration**: The observed se_hac = 0.012625 is correctly sourced from ledger #49.
- **Conclusion**: The "structurally underpowered" finding is statistically sound and supported by multiple independent methods.

### Recommendation
**APPROVE** — The analysis is statistically sound and its conclusions are supported by the evidence. The low-severity advisory notes (AR(1) approximation, rounding precision, block size) do not affect the validity of the main finding.

This power analysis provides a solid statistical basis for design decisions about whether to:
- Extend the look horizon (requires 36+ years for equivalence)
- Widen the SESOI margin (would reduce the required n)
- Accept that equivalence is infeasible under current constraints

---

**Reviewed by**: Independent Statistical Verifier
**Review mode**: READ-ONLY (no code modifications)
**Reproduction**: Successful — output matches `runs/track_c_confirmatory_power_analysis.json`
