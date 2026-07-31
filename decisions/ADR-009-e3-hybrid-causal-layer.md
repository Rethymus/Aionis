# ADR-009 — E3 causal-layer design: hybrid (zero-LLM frozen-β macro + minimal closed-enum LLM event edge); FF-12 unified taxonomy

- **date:** 2026-07-31
- **status:** accepted
- **extends:** [ADR-008](ADR-008-launch-e3-and-broaden-nulls.md), [ADR-004](ADR-004-llm-structural-only-no-market-impact.md), [ADR-006](ADR-006-no-disposable-artifacts-registry.md)
- **decision owner:** Rethymus
- **brief / crystallized spec:** `.omc/specs/deep-interview-e3-causal-schema.md` (deep-interview, 4 rounds, ambiguity→18%)

## Background
ADR-008 launched E3 forward-live. The implementation plan (`docs/phase-e3-implementation-plan.md`) assumed
`arm_e13 = arm_base + E1 propagation + E2 LLM causal-broadcast`, reusing an E2-causal module. Research
(2026-07-30/31) verified that **the E2-causal module does not exist** (`schema/erl.py` has free-form
`CausalLink{cause,effect}`, not the pre-reg's named tuple; no `phase_e2.py`/`causal_broadcast`). The owner
re-evaluated cost-benefit and rejected the heavy LLM causal-graph approach as **收支不平衡** for a
zero-cost, vibe-coded personal research project. A structured deep-interview (4 rounds, ambiguity 100%→18%)
crystallized a hybrid high-性价比 design, falsifying 5 assumptions along the way.

## Candidates considered
- **(a) Heavy LLM causal-graph / multi-hop chain** — **REJECTED.** Owner: 收支不平衡. Research: no
  MIT/Apache library exists; production-network (Acemoglu IO) needs BEA Input-Output tables we lack +
  PIT-hostile annual revisions; RL-IC-reward "structured news" (OpenReview) is a leakage trap (optimized
  toward realized returns).
- **(b) Pure zero-LLM** (frozen-β macro + `propagate_panel` event, no LLM) — viable, maximum
  cost-effectiveness, I5 trivially satisfied; deviates furthest from pre-reg §2.2.
- **(c) Minimal-LLM only** (tighten `CausalLink` to closed enum, keep LLM on both channels) — closest to
  pre-reg §2.2; keeps full LLM dependence + leakage surface.
- **(d) Hybrid: zero-LLM macro (frozen-β) + minimal closed-enum LLM event edge** — **CHOSEN.**

## Chosen — hybrid
```
arm_e13 = arm_base
        + E1 event propagation (propagate_panel, FF-12 grouping, ZERO-LLM)
        + E2-macro (frozen sign-only β, FF-12, CPI+NFP, ZERO-LLM)
        + E2-event (13D/8-K minimal closed-enum LLM edge: direction signs shock + mechanism one-hot)
```

Frozen decisions (all freeze into `config_sha256`; any change = a new forward sequence per pre-reg §5):
- **Sector taxonomy = FF-12 industries**, unified across all three channels. `propagate_panel(sic_map)`
  is sector-agnostic (the `sic_map` arg is really a `ticker→group` dict) → feeding FF-12 grouping is a
  **zero-code-change** swap. A frozen **SIC→FF-12 concordance** (Ken French publishes one) is committed
  as a PIT-stable a-priori map.
- **Macro-β**: source = **Boudt–Neely–Sercu (Fed WP 2017-020)** sector×announcement table; **sign-only
  (±)**; shocks = **CPI + NFP** (already have `surprise_z`). Zero estimation degrees of freedom → most
  falsifiable (no "you mined the β" critique). Regime-fragility (Springer 2025: sectoral betas unstable
  when inflation >4–5%) is a *feature* — a frozen-prior failure out-of-sample IS the publishable null.
- **Event LLM edge**: closed enum `{sic_sector, direction, mechanism_keyword, horizon_bucket}`;
  `extra="forbid"`; **GLM-4-Flash free tier** (priority-1, RPM 30); idempotent sha256 cache (re-runs =
  zero tokens). Tightens the existing free-text `CausalLink`.
- **`mechanism_keyword` = `{earnings_signal, ownership_change, guidance, other}`** — event-mechanism-aligned
  (13D→`ownership_change`, 8-K→`earnings_signal`/`guidance`), 4 super-orthogonal words, low-N learnable.
- **`direction` = `{POSITIVE(+1), NEGATIVE(-1), NEUTRAL(NaN)}`**; **`horizon_bucket` reuses ERL
  `TemporalClass`** (zero new schema).
- **Edge function**: `direction × event_indicator` signs the event shock before `propagate_panel`;
  `mechanism_keyword` is a **load-bearing one-hot feature** (the LLM's unique value = mechanism
  classification, not direction, which is mostly statistically computable).

## Evidence
- **R1 (zero-LLM research):** `propagate_panel` already shipped; `statsmodels.RollingOLS` (BSD) +
  `pandas-datareader` FF industry (BSD) already in deps and already used (`fama_french_daily`);
  Boudt–Neely–Sercu publishes sector×announcement signs; production-network IO propagation has no
  MIT/Apache lib + needs BEA IO (SKIP); EPU G3-fails (SKIP).
- **R2 (minimal-LLM research):** ~85% of the structural-only stack exists (`ERL` `extra="forbid"` +
  closed enums, idempotent sha256 cache, GLM-4-Flash free priority-1); the only leakage gap is the
  free-text `CausalLink`; ~13K tok/month → **$0/month** on GLM free tier; no adoptable external repo
  (CAMEF license-NONE, etc.); RL-IC-reward = leakage trap (SKIP).
- **Deep-interview (4 rounds):** 5 assumptions falsified — heavy LLM chain → hybrid; "unify taxonomy is
  expensive" → zero-code-change (sic_map sector-agnostic); 8–12 word enum → 4 words (low-N sparsity);
  β magnitude → sign-only; LLM value = mechanism classification (not direction).

## Cost
- **$0 ongoing** (GLM free tier for event edges; zero-LLM macro arm). **$0 new deps** (reuse
  `propagate_panel` + statsmodels/pandas-datareader already in deps). **$0 data** (FRED/ALFRED + EDGAR
  already used).
- **Engineering:** moderate — frozen-β table (hardcode Boudt–Neely signs), `CausalLink` enum closure +
  I5 validator, `propagate_panel` FF-12 grouping map, forward-commit plumbing (Slice 3).
- **Reversibility:** exploratory/shadow mode (`mode:exploratory`); schema refinements = a new forward
  sequence (pre-reg §5). Headline freeze deferred until the 1–2 mo shadow validates GLM (ADR-008 Q6).

## Applicability bounds
- **Amends the E3 pre-reg** (`docs/phase-e3-preregistration.md`) §1 (`arm_e13` definition), §2.2
  (extraction), §3 (architecture): the phrase "E2 LLM causal-broadcast" becomes the hybrid definition
  above. The pre-reg is DRAFT v0.1 (not headline-frozen); this ADR records the amendment before ignition.
- **I5 (structural-only) holds:** macro arm is zero-LLM (no text-in leakage surface); event arm is
  closed-enum `extra="forbid"` rejecting `market_impact`/`expected_return`/`historical_similarity`.
- **The 4 published nulls + frozen confirmatory configs are untouched.** Forward rows carry `phase:"E3"`.
- **Provider pool = GLM/SiliconFlow/ModelScope only**; Gemini/TokenHub never re-added (CLAUDE.md).
- **The frozen-β table is a frozen a-priori hyperparameter** (ADR-006 durable registry): committed to
  `config_sha256` BEFORE any OOS metric is observed; changing it = a new forward sequence.
- **8-K uses indicator only** in Slice 3 (no surprise-magnitude via fundamentals join — out of scope).

## Re-evaluation trigger
Re-open this ADR if **any** of:
1. The 1–2 mo shadow shows GLM-4-Flash unstable/unavailable → swap pinned provider (new sequence) or fall
   back to pure zero-LLM (candidate b).
2. The 4-word `mechanism_keyword` enum proves too coarse or too fine after N months of accrual → a new
   enum = a new forward sequence (pre-reg §5).
3. A permissively-licensed (MIT/Apache) lightweight causal library appears that beats the frozen-β prior
   out-of-sample → adopt it + new sequence.
4. The Boudt–Neely sign table proves non-PIT-reproducible or is retracted → source an alternative sign
   table (new sequence).
5. E3 accrues ~42 months and the hybrid-arm differential is null indistinguishable from a large effect →
   decide continue-accruing vs publish a tight null (overlaps ADR-008 trigger 2).
