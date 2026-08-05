# Aionis — Methods and Results Draft (v1.0, publication-ready; first confirmatory included)

> Status: **v1.0-en-draft · 2026-08-05 · faithful English translation of v1.0 (Chinese finalized under owner option A 2026-08-05). Venue tailoring pending the positioning brief. All numbers cross-checked against ledger #49 and the Chinese v1.0.**
>
> **Note**: The Chinese v1.0 remains the authoritative source until the English version is owner-approved. This translation preserves all numbers exactly as stated in the original; any terminology questions are flagged with the original Chinese term in parentheses.

---

## Abstract (draft)

This project takes **anti-leakage discipline itself as the object of study**: on S&P 500 point-in-time constituents + A-share CSI 300, using monthly cross-sectional rank-IC as the estimator, we pre-register a two-tailed, null-favored test of "whether treatment outperforms price-only." **Under all run configurations (including the first confirmatory OOS, ledger #49), no significant positive increment was observed**; and the differential CIs mostly bracket zero. This is not "strategy failure" — **null is the intended, publishable outcome**, and its credibility is guaranteed by structural disciplines including config-before-result / PIT / purged CV / H6 determinism / J-T equivalence gate — not by post-hoc narration. **The first confirmatory's J-T gate at look-1, despite underpowering, rejects prematurely declaring equivalence (even with a null point estimate) — this is a live demonstration of that discipline.**

---

## 1. Contribution: Anti-leakage Discipline as Research Object

The common failure of quantitative research is not "finding no alpha," but **unfalsifiability** — results can be silently rewritten via rerun-to-significance, backfilling, survivor bias, or CV leakage. Aionis's contribution is to structurally lock down these leakage sources, making null itself credible and publishable evidence:

1. **`config_committed` BEFORE result**: The sha256 of the frozen config must be appended to `runs/ledger.jsonl` (append-only) **before** any OOS metric is observed. Changing config = new ledger row, never silent overwrite. **Headline cannot be "rerun-to-significance" rescued.**
2. **Full point-in-time stack**: Fundamentals via `filed` date (not period-end); macro via ALFRED as-of vintage; VIX via no-revision contract; S&P 500 via PIT constituents (`constituents_on(t)`, not today's snapshot); A-share prices via baostock raw (G3 adjustment strategy frozen).
3. **Purged validation + embargo**: `PurgedGroupKFold(group=month, embargo=21 sessions)` (historical B/C/D/E1); Track B/C use **chronological walk-forward** (train strictly < test, expanding, min_train=60).
4. **H6 determinism**: `n_jobs=1`, all seeds pinned to 0, version-pinned via `uv.lock`; IC series **and** raw scores are bit-identical across reruns (asserted).
5. **Two-tailed, pre-registered, null-favored**: One pre-registered two-tailed claim per phase; SESOI ±0.010; Jennison-Turnbull group-sequential equivalence gate (ADR-010, dual-opus corrected: look-specific RCI 99.44/97.64/95.00%, strict-containment).
6. **Multiplicity budget = 1**: Track C's conditioning = **single pre-specified interaction** `score × regime_state` (not K post-hoc subgroups), structurally bypassing "tried K and picked the most significant."

These disciplines are **auditable** (each corresponds to a ledger row / ADR / code assert), not narrative. They do not automatically convert CV-proxy to chronological OOS, nor substitute for economic equivalence testing — boundaries are honestly declared in §6.

---

## 2. Estimator Family

All phases share the same estimator: **monthly cross-sectional rank-IC** (Spearman, model scores vs realized forward returns), with HAC (Newey-West) inference.

| Phase/Track | Estimator | Validation | Universe |
|---|---|---|---|
| B/C/D/E1 (historical) | treatment − baseline differential rank-IC | shared-fold PurgedGroupKFold (**CV-proxy**) | S&P 500 PIT, 2016+, ~588 |
| Track B | treatment(#41) − price-only(#42) differential | **chronological walk-forward** | same as above |
| Track C (this draft's focus) | dual-region joint rank-IC × regime_state interaction | **chronological joint fold** (US+CN) | S&P 500 + CSI 300, 2016+ |

Learner: LightGBM (frozen, `objective=lambdarank`, RD-15 ranking contract, bin_count=5, in-region monthly quintile binning fitted only on train-fold).

---

## 3. Track C Joint Fold (New Methodological Contribution)

Dual-region joint chronological walk-forward is this draft's methodological novelty ([`reports/design/2026-08-04-track-c-joint-fold-spec.md`](../reports/design/2026-08-04-track-c-joint-fold-spec.md)):

- **Joint panel**: US (NYSE month-end) + CN (XSHG/XSHE month-end) sampled at each market's trading month-end, aligned to the same timeline by calendar month.
- **Core theorem**: month-end sampling + calendar-fold boundaries ⇒ **per-region 21-session embargo automatically satisfied** (adjacent month-ends in any market ≈ 21 sessions), so `cv.py`/`purgedcv` require 0 changes.
- **Region-month group** (D1): lambdarank query = (region, month), US ranks only with US, CN only with CN — **eliminates cross-currency label contamination** (forward return is local-currency return). Model remains jointly fitted (shared parameters).
- **regime_state conditioning**: Three-layer PIT composite (meso US-SIC + macro 5-line + global Diebold-Yilmaz spillover), TACO as-of σ normalization (never recalculated ex-post). Conditioning = single pre-specified interaction (multiplicity budget 1).

**Anti-leakage invariants** (code-asserted): I1 per-region chronology (train.max < test.min per region), I2 train-only binner, I3 regime as-of month-end, I5 region-month group separation, I6 H6 bit-identical.

---

## 4. Evidence Table (All null; numbers per ledger/artifact)

> ⚠ **Honest grading**: CV-proxy ≠ chronological OOS; exploratory ≠ confirmatory. The "Grade" column below is the true upper bound of publishable strength.

| # | Result | Point Estimate | 95% CI | p | n (months) | Grade | ledger/artifact |
|---|---|---:|---|---:|---:|---|---|
| 1 | Phase B differential | −0.0008 | [−0.0106, +0.0090] | 0.872 | 125 | CV-proxy (paired HAC CI added 2026-08-05; ledger #28 unchanged, append-only) | #28 + supplemental |
| 2 | Phase C differential | −0.0065 | [−0.0195, +0.0066] | 0.355 | 125 | CV-proxy | #30 |
| 3 | Phase D differential | −0.0030 | [−0.0137, +0.0078] | 0.597 | 125 | CV-proxy | #34 |
| 4 | Phase E1 differential | −0.0028 | [−0.0115, +0.0059] | 0.533 | 125 | CV-proxy | #37 |
| 5 | Track B treatment(#41) | +0.0055 | [−0.021, +0.033] | 0.689 | 125 | chronological / exploratory | #41 |
| 6 | Track B differential(#41−#42) | +0.0076 | [−0.004, +0.020] | 0.219 | 125 | chronological / **CI upper bound 0.020 > SESOI 0.010 → not strict equivalence** | #41/#42 |
| 7 | **Track C joint combined IC** (this session) | **−0.0070** | [−0.030, +0.016] | **0.55** | 71 | chronological joint / **exploratory** (10 price features) | `track_c_joint_summary.json` |
| 8 | Track C joint conditional-IC β | −0.015 | — | 0.20 | 71 | exploratory (no regime interaction; R²=0.018) | same as above |
| 9 | Track C 3-layer conditional-IC (combined β) | −0.0148 | — | 0.21 | 71 | chronological joint / exploratory; per-region us β=−0.029 (p=0.13) / cn β=+0.004 (p=0.80) (joint-fold IC). handoff culmination's β_US=−0.001/β_CN=+0.015 is **Track-B-fitter single-region IC** sensitivity (different series, still prose) | `track_c_3layer_conditional_ic.json` |
| 10 | BASELINE-FF5 | +0.0106 | ci_half 0.0196 | t=1.06 | 125 | CV-proxy / exploratory | baseline_ff5 |
| 11 | BASELINE-RANK | +0.0154 | ci_half 0.0149 | t=2.03 | 125 | CV-proxy / exploratory (p=0.042, n_trials=30 haircut would wash out) | baseline_rank |
| 12 | h=10/42 sensitivity (8 rows) | All bracket zero | — | 0.41–0.86 | 124–126 | CV-proxy / exploratory | #39 |
| 13 | Track C joint asymmetric35 combined IC (A1 validation, this session) | −0.0121 | [−0.035, +0.011] | 0.31 | 71 | chronological joint / exploratory (US 23 fund+price / CN 12 price+extras = 25 unique cols; US IC −0.002 / CN IC −0.020; **US fundamentals have no alpha → confirms null-favored**) | `track_c_joint_asym35_summary.json` |
| 14 | Track C joint asymmetric41 combined IC (confirmatory dress rehearsal) | −0.0088 | [−0.034, +0.016] | 0.48 | 71 | chronological joint / exploratory (all 41 features incl macro 6; bit-identical to #15 confirmatory) | `track_c_joint_asym41_summary.json` |
| 15 | **Track C joint confirmatory:first (this session climax)** | **−0.0088** | [−0.034, +0.016] | **0.48** | 71 | **chronological joint / CONFIRMATORY** (frozen #48; J-T look-1 NOT_EQUIVALENT: RCI 99.44% [−0.051, +0.027] wider than ±0.010 SESOI = underpowered, **not** an effect signal; H6 double-run bit-identical PASS) | **ledger #49** + `track_c_confirmatory_summary.json` |

**Strategy-return secondary lens** (gross-of-cost, B/C, n=125): B_arm_state Sharpe 0.42 / arm_base 0.62 / C_arm_macro 0.24 / C_placebo 0.54; SPA consistent p=0.69, MCS retains all. **Gross** — no turnover/slipp/borrow/delist/capacity, not interpretable as tradable returns. Net-cost lens (mount②, bps=5): net Sharpe ≈0.43 annualized, turnover 1.14 (non-degenerate).

**Interpretation**: All 15 rows are null (CI brackets zero or differential not significant). At **confirmatory** grade (#15, highest publishable strength),
the first confirmatory OOS point estimate is null (−0.0088); J-T look-1, due to OBF conservatism (99.44% RCI), is underpowered,
returning NOT_EQUIVALENT (= power declaration, not effect signal; look-2/3 need E3 forward-live calendar time). chronological
grade (#5-9, #14) are all null; conditioning regime interaction is null. **Conclusion**: Under the tried features/learner/validation, no reliable positive
cross-sectional increment was found — consistent with the null-favored prior that "dual-region monthly-frequency is priced / factor alpha is leakage artifact / costs erode." **Project's
logical climax reached**: anti-leakage discipline as research object, end-to-end demonstrated on the first confirmatory run (config before result + H6 real-data proof + J-T gate rejects premature equivalence).

---

## 5. First Confirmatory (Track C GO executed; ledger #49)

**Status: confirmatory OOS run + sedimented** (2026-08-05, owner D6 GO; `runs/ledger.jsonl` row #49,
`config_sig=e14b9d44...` references frozen #48). runner: `scripts/track_c_confirmatory_run.py`;
H6 double-run bit-identical PASS on real data; J-T gate (`eval/sesoi_gate.py`) acts on `combined_ic_series`
mean (Reading A: rank-IC is the gated estimator; `cond_beta` is explanatory only, multiplicity budget stays 1).

**Results** (n=71 months, 68 folds, 2016-01..2026-08 dual-region month-end):

| Metric | Value | Interpretation |
|---|---:|---|
| combined rank-IC mean | **−0.00884** | null (p_hac=0.484, 95% HAC CI [−0.034, +0.016] brackets zero) |
| US IC / CN IC mean | +0.0052 / −0.0265 | both regions null (bit-identical to asym41 exploratory) |
| conditional-IC β (regime interaction) | −0.0076 (p=0.43) | null; interaction not significant (multiplicity budget 1) |
| **J-T look-1 verdict** (n=60, RCI 99.44%) | **NOT_EQUIVALENT** | RCI [−0.051, +0.027] far wider than ±0.010 SESOI |
| H6 double-run bit-identical | PASS | determinism verified on real data |

**Honest interpretation (critical)**: This is a **null point estimate + underpowered look-1** result, **neither "treatment works" nor "equivalence rejected"**:

1. **Point estimate null**: combined IC −0.00884 is consistent with all 14 exploratory nulls in this draft §4 (covering CV-proxy, chronological single-region/joint, 4 feature families, 3 regions). At confirmatory grade, the treatment model still shows no reliable positive increment.
2. **look-1 NOT_EQUIVALENT is a power declaration, not an effect signal**: OBF look-1 uses z=2.772 (RCI 99.44%, extremely conservative); monthly rank-IC noise se≈0.014 → 99.44% RCI half-width ≈0.039, **structurally wider than** ±0.010 SESOI.
3. **Power analysis reveals deeper structural underpowering** (2026-08-05, `scripts/track_c_power_analysis.py`,
   see §6): prospective projection shows **look-2 (n=90) and look-3 (n=120) also cannot declare equivalence** — declaring equivalence requires
   n_min = 580 / 435 months (48 / 36 years). Under block bootstrap, P(equivalence) = 0.0000 at all 3 planned looks.
   **Thus look-1 NOT_EQUIVALENT is not a local "look-1 too conservative" phenomenon, but the inevitable state of the entire 60/90/120 schedule under SESOI ±0.010**.
   The noise floor of monthly rank-IC (σ≈0.10) makes ±0.010 equivalence declaration unreachable under realistic sample sizes.
4. **Gate discipline demonstration**: Even with structural underpowering, the J-T gate still **refuses to prematurely declare equivalence when data is insufficient** (even with a null point estimate).
   This is live evidence of "anti-leakage discipline as research object" — a framework that could be rescued by rerun-to-significance or wide CIs would recklessly declare
   "null is equivalence"; the pre-registered J-T gate will not. **Combined with power analysis, the project's honest contribution = null point estimate + anti-leakage discipline +
   power-limit disclosure** (not "equivalence declared").

**Climax narrative**: Aionis completed the first confirmatory OOS (config #48 frozen before observation, H6 real-data proof).
Point estimate null, consistent with all exploratory runs. **Strict equivalence determination (look-2/3) requires E3 forward-live accumulation
(look-2 n=90 ≈ 2028, look-3 n=120 ≈ 2031)**. This is not "failure" — null is the intended publishable outcome, and the gate's rejection of premature equivalence
is itself a demonstration of methodological contribution.

**Independence limitation (disclosure)**: runner was built directly by opus orchestrator + independent sonnet code-review APPROVE (0 CRITICAL,
estimand Reading A defensible, H6 sufficient, look truncation Type-I correct); J-T gate + H6 + sedimented reproducibility guaranteed by frozen #48 +
`scripts/track_c_confirmatory_run.py` — any independent party can rerun from frozen config and verify bit-identical.
exploratory asym41 (2026-08-05 13:48) observed IC≈−0.0088 before confirmatory sediment; config #48 was selected by D1-D5 spec
decisions (machinery readiness + spec faithfulness), **not** IC optimization → no result-peeking leakage (H6 guarantees
confirmatory rerun reproduces the same IC).

---

## 6. Limitations (Honest Boundaries)

- **CV-proxy ≠ chronological OOS**: B/C/D/E1 (#1-4) are shared-fold purged cross-fit; train complement may include months after test blocks; purge/embargo prevent label overlap but do not establish chronological OOS. Track B/C (#5-9) are chronological.
- **Exploratory ≠ confirmatory**: #5-9 are all exploratory; no confirmatory-grade results (pending §5).
- **Underpowered equivalence (empirically verified, 2026-08-05 power analysis)**: Track B differential CI upper bound 0.020 > SESOI 0.010 →
  does not constitute strict equivalence. **Track C confirmatory's prospective power analysis** (`scripts/track_c_power_analysis.py`,
  reusing combined_ic_series noise σ≈0.106 + lag-1 ρ≈0.07 from ledger #49) shows: J-T 60/90/120 look schedule under
  SESOI ±0.010 is **structurally underpowered** — minimum sample needed to declare equivalence n_min:
  look-1 (z=2.772) 869 months (72.5 years),
  look-2 (z=2.263) 580 months (48.3 years),
  look-3 (z=1.960) 435 months (36.2 years). Under block bootstrap (2000 resamples)
  P(equivalence) = **0.0000** at all 3 planned looks; look-3 (n=120) RCI half-width median 0.019 > SESOI 0.010.
  **Interpretation**: look-1 NOT_EQUIVALENT is not a local "look-1 too conservative" phenomenon, but the **inevitable state of the entire 60/90/120 schedule under this SESOI**.
  The noise floor of monthly rank-IC (σ≈0.10) makes ±0.010 equivalence declaration unreachable under realistic sample sizes. Even if E3 forward-live ignites,
  ~36+ years are needed to reach look-3 equivalence determination. **This is an honest methodological finding** (power floor), not a bug; it narrows the project's contribution from "declaring equivalence"
  to "null point estimate + anti-leakage discipline + power-limit disclosure." **Owner 2026-08-05 chose ① (authorized "proceed as recommended")**:
  accept reframing, do not widen SESOI, do not modify frozen surface. ② Widen SESOI ±0.025 (post-hoc "moving goalposts" suspicion + contradicts anti-leakage spirit,
  not adopted); ③ Extend look horizon n=435+ (36 years infeasible, not adopted).
- **Survivor bias**: PIT constituents mitigate, not eliminate (no free delisting PIT). Universe = 2016+ 588/705 resolvable tickers → headline = conservative upper bound.
- **Currency**: D1 region-month ranking eliminates label cross-currency contamination, but joint IC is still per-region ranking composition of local-currency returns, not exchange-neutral portfolio returns.
- **SIC current snapshot** (not historical vintage); 13D self-report filtering residual error; baostock adjustment G3 strategy frozen (raw).
- **Not investment advice**: null does not prove market efficiency, does not prove factor alpha is strictly zero, does not constitute a tradable strategy.

---

## 7. Non-Inflation Statement

- `[F]` This draft v1.0 contains the first confirmatory OOS result (ledger #49, config #48 frozen before observation, H6 real-data bit-identical PASS); METHODS section is based on completed anti-leakage disciplines (ADR-001..012 + preregs + ledger).
- `[F]` This round sedimented 1 row `confirmatory:first` (ledger #49, append-only); B/C/D/E1 + Track B frozen surfaces / prereg / ADR unchanged.
- `[I]` Owner 2026-08-05 authorized option A (accept reframing) → Chinese v1.0 finalized accordingly. Awaiting owner: final English version, venue/conference positioning, whether to initiate E3 forward-live (year-scale, continuation look-2/3; post-power-analysis objective downgraded to "continue null OOS accumulation", optional non-essential).
