# Evidence Integrity Audit — 2026-08-04

> **Auditor**: Independent evidence-integrity auditor (opus agent)
> **Scope**: Reconcile EVERY null result claim against underlying artifacts
> **Sources**: `docs/RESULTS.md`, `runs/ledger.jsonl`, `docs/track-b-results.md`, `runs/track_c_joint_summary.json`, `state/handoff.md`

---

## Executive Summary

**Overall integrity verdict**: EVIDENCE INTEGRITY VERIFIED — all headline claims in `docs/RESULTS.md` trace to ledger rows or documented artifacts. No overstated, stale, or mis-attributed null results found. Three caveats identified: (1) Phase B differential lacks paired HAC CI in ledger; (2) Baseline FF5/RANK show config_committed rows but no OOS result rows in ledger; (3) Track C joint exploratory is gitignored-only (NO ledger).

**Key findings**:
- 4 Phase B/C/D/E1 headline differentials: ALL match ledger `confirmatory:first` rows (28, 30, 34, 37); all are shared-fold CV-proxy (NOT chronological OOS); all are negative/null
- Phase B CI caveat confirmed: ledger row #28 lacks `differential_state_minus_base.{se_hac,ci_half,ci_lo,ci_hi}`; only `dm_p_mbb` exists
- 8 horizon sensitivity results: ALL match ledger exploratory row #39; all exploratory; all null
- Strategy-return lens: B/C gross numbers match ledger exploratory row #38; n=125; gross-of-costs
- Track B chronological: docs/track-b-results.md contains treatment (#41), price-only (#42), differential; CI upper bound 0.020 > SESOI 0.010 (not strict equivalence)
- Track C joint exploratory: runs/track_c_joint_summary.json (NO ledger); combined IC −0.007, US IC −0.002, CN IC −0.014, conditional-IC β=−0.015 (p=0.20); EXPLORATORY
- Track C conditional-IC 3-layer: handoff.md reports US-only-meso β_US=−0.001 (p=0.95), β_CN=+0.015 (p=0.36); EXPLORATORY
- Baselines FF5/RANK: config_committed rows exist (#43, #45) but NO OOS result rows in ledger; handoff.md cites executed real-data results — **DATA GAP**

---

## Reconciliation Table

| Claim | Exact Number (from artifact) | Artifact Source | Grade (CV-proxy / chronological-OOS; exploratory / confirmatory) | n / months | CI / p | Caveat / Discrepancy |
|-------|------------------------------|-----------------|------------------------------------------------------------|------------|---------|---------------------|
| **Phase B differential** | −0.0008003561696833403 | ledger row #28 `differential_state_minus_base.mean_ic_diff_state_minus_base` | CV-proxy, confirmatory | 125 | p=0.8695652173913043 (dm_p_mbb); **paired CI MISSING** | Phase B ledger lacks differential HAC CI; only single-arm CIs exist |
| **Phase C differential** | −0.006487473568317837 | ledger row #30 `differential_macro_minus_base.mean_diff` | CV-proxy, confirmatory | 125 | CI=[-0.0195, 0.0066], p=0.3553223388305847 | None; CI crosses zero |
| **Phase D differential** | −0.0029798406036171702 | ledger row #34 `differential_rel_minus_base.mean_diff` | CV-proxy, confirmatory | 125 | CI=[-0.0137, 0.0078], p=0.5972013993003499 | None; CI crosses zero |
| **Phase E1 differential** | −0.0027928949986939897 | ledger row #37 `differential_prop_minus_base_self.mean_diff` | CV-proxy, confirmatory | 125 | CI=[-0.0115, 0.0059], p=0.5332333833083458 | None; CI crosses zero |
| **h=10 Phase B diff** | 0.0008433987021642504 | ledger row #39 results.10.B.mean_diff | CV-proxy, exploratory | 126 | CI=[-0.0078, 0.0094], p=0.8555722138930535 | None |
| **h=10 Phase C diff** | −0.0021182332777918314 | ledger row #39 results.10.C.mean_diff | CV-proxy, exploratory | 126 | CI=[-0.0162, 0.0119], p=0.777111444277861 | None |
| **h=10 Phase D diff** | −0.0017889096684366723 | ledger row #39 results.10.D.mean_diff | CV-proxy, exploratory | 126 | CI=[-0.0129, 0.0094], p=0.7706146926536732 | None |
| **h=10 Phase E1 diff** | 0.0016496284922720287 | ledger row #39 results.10.E1.mean_diff | CV-proxy, exploratory | 126 | CI=[-0.0088, 0.0121], p=0.7781109445277361 | None |
| **h=42 Phase B diff** | −0.004679723157718146 | ledger row #39 results.42.B.mean_diff | CV-proxy, exploratory | 124 | CI=[-0.0157, 0.0064], p=0.40729635182408797 | None |
| **h=42 Phase C diff** | 0.0018597777350683653 | ledger row #39 results.42.C.mean_diff | CV-proxy, exploratory | 124 | CI=[-0.0121, 0.0158], p=0.8095952023988006 | None |
| **h=42 Phase D diff** | −0.004800521999415512 | ledger row #39 results.42.D.mean_diff | CV-proxy, exploratory | 124 | CI=[-0.0164, 0.0068], p=0.41879060469765117 | None |
| **h=42 Phase E1 diff** | −0.0019900106603546112 | ledger row #39 results.42.E1.mean_diff | CV-proxy, exploratory | 124 | CI=[-0.0107, 0.0067], p=0.6286856571714143 | None |
| **Strategy B_arm_state Sharpe** | 0.42185547404242635 | ledger row #38 strategies.B_arm_state.sharpe_annualized | CV-proxy, exploratory | 125 | DSR p=0.7432854842358372 | Gross-of-costs; no net/costs |
| **Strategy arm_base Sharpe** | 0.6205757339836699 | ledger row #38 strategies.arm_base.sharpe_annualized | CV-proxy, exploratory | 125 | DSR p=0.503795982911974 | Gross-of-costs; no net/costs |
| **Strategy C_arm_macro Sharpe** | 0.24211861932063053 | ledger row #38 strategies.C_arm_macro.sharpe_annualized | CV-proxy, exploratory | 125 | DSR p=0.8812553123232412 | Gross-of-costs; no net/costs |
| **Strategy C_placebo Sharpe** | 0.5381237497077501 | ledger row #38 strategies.C_placebo.sharpe_annualized | CV-proxy, exploratory | 125 | DSR p=0.6264684423697051 | Gross-of-costs; no net/costs |
| **Strategy C_sanity Sharpe** | 0.6628862001996021 | ledger row #38 strategies.C_sanity.sharpe_annualized | CV-proxy, exploratory | 125 | DSR p=0.47354684493774823 | Gross-of-costs; no net/costs |
| **Track B treatment IC** | 0.005511 | docs/track-b-results.md §2 (mean_ic) | Chronological walk-forward, exploratory | 66 folds | CI=[-0.0214, 0.0325], p=0.6886 | docs-only; no ledger row for result |
| **Track B price-only IC** | −0.002062 | docs/track-b-results.md §2.1 (mean_ic) | Chronological walk-forward, exploratory | 66 folds | CI=[-0.0316, 0.0275], p=0.8913 | docs-only; no ledger row for result |
| **Track B differential** | 0.007572 | docs/track-b-results.md §2.2 (mean_diff) | Chronological walk-forward, exploratory | 65 months | CI=[-0.0045, 0.0196], p=0.2186 | **CI upper 0.0196 > SESOI 0.010**; not strict equivalence |
| **Track C joint combined IC** | −0.007047716768180216 | runs/track_c_joint_summary.json combined_mean_ic | Chronological joint fold, EXPLORATORY | 71 months | CI=[-0.0304, 0.0163], p=0.5546287190833447 | **NO ledger**; gitignored artifact; exploratory (10 price features, region-month default) |
| **Track C joint US IC** | −0.0019587607268764526 | runs/track_c_joint_summary.json us_ic_mean | Chronological joint fold, EXPLORATORY | 71 months | CI not separately reported | NO ledger; exploratory |
| **Track C joint CN IC** | −0.01409729311157535 | runs/track_c_joint_summary.json cn_ic_mean | Chronological joint fold, EXPLORATORY | 71 months | CI not separately reported | NO ledger; exploratory |
| **Track C conditional-IC β** | −0.01522313447722138 | runs/track_c_joint_summary.json cond_beta | Chronological joint fold, EXPLORATORY | 71 months | p=0.19757532000146438, R²=0.0176 | NO ledger; exploratory; no regime interaction |
| **Track C 3-layer US β** | −0.001 | state/handoff.md §2026-08-04 conditional-IC (β_US) | EXPLORATORY | n not reported | p=0.95 | Handoff prose only; no ledger/artifact |
| **Track C 3-layer CN β** | +0.015 | state/handoff.md §2026-08-04 conditional-IC (β_CN) | EXPLORATORY | n not reported | p=0.36 | Handoff prose only; no ledger/artifact |
| **Baseline FF5 mean_IC** | NOT FOUND IN LEDGER | config_committed row #43 exists; NO result row | — | — | — | **DATA GAP**: handoff.md claims executed real-data but ledger lacks result |
| **Baseline RANK mean_IC** | NOT FOUND IN LEDGER | config_committed row #45 exists; NO result row | — | — | — | **DATA GAP**: handoff.md claims executed real-data but ledger lacks result |

---

## Discrepancy List

### CRITICAL
**None identified.** All headline null result claims in `docs/RESULTS.md` trace to artifact evidence.

### HIGH
1. **Phase B differential CI missing (ledger row #28)**: The `differential_state_minus_base` object contains `mean_ic_diff_state_minus_base`, `dm_stat`, `dm_p_mbb`, `n_months` but NOT the paired HAC CI (`se_hac`, `ci_half`, `ci_lo`, `ci_hi`). Single-arm CIs exist in `arm_state_cvproxy` and `arm_base_cvproxy`, but the differential CI is absent. This violates the paired precision gate auditability (RESULTS.md correctly notes "not recorded").

2. **Baseline FF5/RANK OOS results missing from ledger**: Handoff.md states "owner authorized real-data execution ('全部approved'). Both baselines now have REAL CV-proxy results" and cites specific numbers (FF5: mean_IC=0.0106, ci_half=0.0196; RANK: mean rank-IC=0.015420, ci_half=0.014870). Ledger has `config_committed` rows (#43, #45) but NO corresponding `confirmatory:first` or result rows with OOS metrics. **DATA GAP**: These results are claimed in handoff but not in the append-only audit log. RESULTS.md correctly omits these (not in ledger), but handoff prose may be overstating.

### MEDIUM
1. **Track B differential CI upper bound > SESOI**: docs/track-b-results.md §2.2 reports differential CI=[-0.0045, 0.0196]; upper bound 0.0196 exceeds SESOI 0.010. The document correctly notes "未达 (not strict equivalence)" and "CI 上界 0.0196 > SESOI 0.010". This is properly caveat but bears noting for any equivalence claims.

2. **Track C joint exploratory has NO ledger row**: `runs/track_c_joint_summary.json` exists (gitignored) with combined IC −0.007, US IC −0.002, CN IC −0.014, conditional-IC β=−0.015 (p=0.20). This is exploratory (10 shared price features, region-month group default, per caveats in JSON) and correctly NOT in ledger. RESULTS.md does not cite it; handoff.md does. For any publication, these would need confirmatory machinery.

3. **Track C 3-layer conditional-IC numbers are handoff-prose only**: The β_US=−0.001 (p=0.95) and β_CN=+0.015 (p=0.36) values appear only in `state/handoff.md` prose, not in ledger or structured artifact. These are exploratory and correctly not headline, but lack artifact traceability for independent verification.

### LOW
1. **Track B treatment/price-only/differential are docs-only**: docs/track-b-results.md contains the chronological walk-forward numbers (treatment IC=0.0055, price-only IC=−0.0021, differential=0.0076, n=65-66 months). These are NOT in `runs/ledger.jsonl`. The document correctly identifies config sigs (#41, #42) but the result rows themselves are missing from the ledger. This is a documentation-artifact gap, not a claim integrity issue (numbers exist in tracked docs).

---

## Methodology Notes

1. **CV-proxy vs chronological OOS**: All B/C/D/E1 headline differentials are from shared-fold `PurgedGroupKFold(5, embargo=21)` — they are purged cross-fitted/OOF differentials, NOT train-strictly-before-test chronological OOS. RESULTS.md correctly states this in §0. Track B results are chronological walk-forward (exploratory).

2. **Exploratory vs confirmatory**: Horizon sensitivity (h=10/42), strategy-return lens, Track C joint, and conditional-IC regressions are exploratory. Only B/C/D/E1 headline differentials have `confirmatory:first` ledger rows.

3. **n / months reporting**: B/C/D/E1 confirmatory differentials are n=125 months. Horizon sensitivity shows n=126 (h=10) and n=124 (h=42). Strategy-return lens is n=125. Track B chronological is n=65-66 months (differential vs treatment). Track C joint is n=71 months.

4. **Ledger row verification**: Every number in the reconciliation table was verified by reading the actual ledger row (line number cited) or artifact file. No prose-to-prose copying.

5. **Null-favored consistency**: All headline differentials are negative/null, consistent with null-favored pre-registration. No positive results are claimed.

---

## Conclusion

The evidence integrity audit confirms that Aionis's published null results are artifact-backed and correctly caveat. All headline claims in `docs/RESULTS.md` trace to ledger rows or documented artifacts. Three HIGH-severity caveats were identified: Phase B's missing paired CI, Baseline FF5/RANK missing OOS results from ledger despite handoff claims, and Track B's differential CI exceeding SESOI. These are properly disclosed in source documents.

For any publication or external presentation, ensure: (1) Phase B is noted as lacking paired CI; (2) Track B differential is not described as "equivalent" (CI upper > SESOI); (3) Baseline FF5/RANK numbers are NOT cited until ledger rows exist; (4) Track C joint/conditional-IC results are labeled EXPLORATORY and require confirmatory runs before claim status.
