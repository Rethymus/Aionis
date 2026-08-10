# Disciplined adaptive stock-picking: A+B synthesis (research-grounded)

**Date:** 2026-08-11. **Author:** orchestrator.
**Status:** design proposal — awaits owner confirmation before any frozen-config /
ledger-row change. Grounded in the R&D-Agent-Quant NeurIPS 2025 paper (arXiv
2505.15155, read in full) + Aionis's existing anti-leakage contract + de Prado's
backtesting-overfitting discipline.

## 1. The reframe: A vs B was a false dichotomy

The "Reading A (disciplined) vs Reading B (predictor pivot)" fork I framed
earlier is **wrong**. The real distinction is not "disciplined vs adaptive" — it
is **undisciplined adaptation vs disciplined adaptation**:

- **Undisciplined adaptation** (tuning model weights against the OOS test set,
  maximizing accuracy without purge/embargo/pre-reg/multiplicity correction) =
  rerun-to-significance. **Forbidden** by CLAUDE.md.
- **Disciplined adaptation** (a pre-registered *adaptive model class* — e.g. an
  online-refitting LightGBM with a specified update rule — tested OOS through
  PurgedGroupKFold+embargo, two-tailed, with the static frozen model as control)
  = a **legitimate falsifiable claim**. Fully within the contract.

The anti-leakage contract forbids *undisciplined tuning*, not *adaptation per
se*. An adaptive algorithm that is itself the pre-registered hypothesis under
test is no different from any other treatment. **The owner's "do A+B" instinct is
correct; the synthesis is a pre-registerable adaptive-vs-static comparison, not
two parallel systems.**

## 2. Evidence: what R&D-Agent(Q) actually does (NeurIPS 2025)

Read in full (arXiv 2505.15155v2, 42pp). Key facts:

**What it does well (reusable):**
- Multi-agent loop: Specification → Synthesis (LLM hypotheses from a knowledge
  forest) → Implementation (Co-STEER code-gen agent) → Validation (qlib
  backtest) → Analysis (contextual Thompson-sampling 2-armed bandit picks
  factor- vs model-branch each round).
- **LLM-memorization mitigation (Appendix D.1):** "the LLM is never exposed to
  raw market data or explicit temporal splits, but only to schema-level
  information." This prevents the LLM from memorizing test-period outcomes → no
  look-ahead via the LLM. **Aligns with Aionis's ERL design** (structural-only,
  no market_impact, for the same reason — see `aionis-erl-leakage-design`).
- OOS strength on US large-caps (NASDAQ-100, test 2024–2025, post-LLM-cutoff):
  RD-Agent(Q) o4-mini IC=0.0162, Rank-IC=0.0083, ARR=28.4%, IR=1.77, MDD=−6.3%
  vs LightGBM baseline IC=0.008, ARR=−2.9%. (Caveat: 2024–25 was a strong NASDAQ
  bull market → long-biased strategies benefited; and see the gaps below.)

**The 3 discipline gaps (exactly what Aionis was built to fill):**
1. **No purge, no embargo.** "Model training follows a walk-forward validation
   procedure" (Appendix B) — but walk-forward alone does NOT purge the
   train/test overlap at the fold boundary nor embargo the post-split test band.
   Label-horizon straddling the split leaks. Aionis's `PurgedGroupKFold(group=
   month, embargo=21)` is the missing guard.
2. **No multiple-testing correction.** The bandit loop runs 30–44 iterations ×
   multiple candidates each = **hundreds of factor candidates tried**, and the
   paper reports the SOTA with **no deflated-Sharpe / SPA / Romano-Wolf
   correction** for the multiplicity of trials. This is the structural
   definition of rerun-to-significance: search enough candidates, some look good
   by chance. Aionis's `arch` DSR/SPA + the ledger's "config_committed BEFORE
   result" rule close this.
3. **Median-over-CI.** "Rather than reporting standard error bars or confidence
   intervals, we report the median annualized return across these runs"
   (Appendix C.1). A weaker statistical standard than Aionis's pre-registered
   two-tailed rank-IC + CI.

**Implication:** RD-Agent(Q) is a powerful *candidate generator* with a *weaker
statistical shell* than Aionis. The synthesis is a 4-layer graft, not a parallel
build.

## 3. The synthesis: RD-Agent search + Aionis discipline (4-layer graft)

```
┌── RD-Agent(Q) layer (MIT, reuse) ──────────────────────────────────┐
│ 1. LLM hypothesis → Co-STEER factor/model code                     │  candidate
│    (LLM fed SCHEMA ONLY — no raw data, no splits; matches ERL)     │  generation
│ 2.qlib backtest of each candidate (raw IC)                         │
└────────────────────────┬───────────────────────────────────────────┘
                         │  candidate factor/model expressions
                         ▼
┌── Aionis discipline shell (the graft) ─────────────────────────────┐
│ 3. Compute candidate on PIT panel (filed-date, ALFRED vintages,    │  anti-leakage
│    PIT S&P membership) — NOT qlib's today-snapshot defaults        │  data layer
│ 4. PurgedGroupKFold(group=month, embargo=21) CV → OOS rank-IC + CI │  the gate
│    + multiple-testing correction across ALL candidates tried       │
│    (arch DSR/SPA; Romano-Wolf step-down) — NOT raw-IC SOTA         │
│ 5. config_committed ledger row BEFORE any OOS metric is observed   │  the anchor
│ 6. pre-registered two-tailed verdict (publishable null or not)     │  the claim
└────────────────────────────────────────────────────────────────────┘
```

The LLM never sees raw IC; it sees the **discipline-corrected** verdict (corrected
p-value, CI). Most candidates will be null after correction — the honest,
publishable outcome per the 2026-08-05 framing.

## 4. The pre-registered claim (adaptive-vs-static, two-tailed)

> *Pre-registered, two-tailed:* An adaptively-updating LightGBM (online refit
> with a pre-specified decay + update-trigger rule, candidates proposed by
> RD-Agent's LLM loop), tested OOS on PIT S&P 500 constituents via
> `PurgedGroupKFold(group=month, embargo=21)`, has cross-sectional monthly
> rank-IC whose differential vs the **static frozen LightGBM baseline** (Track-B
> climax, ledger #49 = null) is statistically distinguishable from zero at the
> pre-registered SESOI, after Romano-Wolf correction across all adaptive
> variants + factor candidates tried.

- **Null outcome** (most likely, given the climax was null): "disciplined
  adaptation does NOT beat the static frozen model OOS, after correction." =
  publishable, **preserves the 2026-08-05 framing.**
- **Non-null**: "adaptation helps OOS under discipline" = genuine discovery
  (rare, and the correction makes it trustworthy).

This IS Aionis's existing methodology (treatment-vs-control rank-IC differential)
applied to the adaptive-vs-static question. It fits the project exactly.

## 5. Why "trial and error" is safe here

The owner: "项目允许试错，这本身也是研究的一部分." Agreed — **because the trial-and-
error happens INSIDE the gate**, not instead of it. Each adaptive variant the LLM
proposes = one frozen config + one ledger row + one OOS verdict under purge/
embargo/correction. We can run dozens of variants (trial-and-error); what we
CANNOT do is let the variants tune themselves against the test set without the
gate. The gate is what makes the trial-and-error *research* rather than
*overfitting*.

## 6. Build steps (each is a separate pre-registered phase; order matters)

| # | Step | Effort | New frozen config? | Needs owner OK? |
|---|---|---|---|---|
| 1 | Extend panel to carry OHLCV (unlocks qlib K-Bar + volume factors) | M | yes (new panel) | yes |
| 2 | Wire close-only factor-pack (done) + OHLCV factors into the frozen feature pool | M | yes | yes |
| 3 | Build the RD-Agent → Aionis evaluator seam (`evaluate_factor(expr) → {rank_ic, ci, corrected_p}`) | L | no (infra) | yes |
| 4 | Pre-register the adaptive-vs-static claim (SESOI, correction procedure) | S | yes (new phase) | **yes — this is the A+B go-signal** |
| 5 | Run the adaptive variants (online-refit LightGBM) through the gate vs static baseline | L (compute) | per-variant | no (covered by #4) |
| 6 | Verdict → RESULTS.md + ledger (null or discovery, honestly) | S | yes | no |

**Step 4 is the actual A+B decision point.** Steps 1–3 are safe infrastructure
that serve EITHER reading (they enrich the factor pool + build the evaluator
seam); they don't commit to the adaptive claim. Step 4 is where the owner
formally pre-registers the adaptive-vs-static claim — that's the conscious
"project identity" decision.

## 7. What I recommend the owner decide

Greenlight **steps 1–3 now** (safe infrastructure: OHLCV panel + factor wiring +
evaluator seam). These are reusable under any reading and unblock the real work.
**Defer step 4** (the adaptive pre-registration) until the infrastructure lands
and the owner has seen the audit + this design doc — then make the formal
pre-registration decision with full information.

This is **A+B done right**: not a pivot to a predictor, not a refusal to adapt —
a disciplined build-up to a pre-registered adaptive-vs-static verdict, grounded
in the NeurIPS-2025 state of the art + Aionis's anti-leakage shell.

## Sources

- R&D-Agent-Quant (NeurIPS 2025): arXiv 2505.15155v2 — read in full. Key sections:
  §2.4 Validation Unit (qlib backtest, IC de-duplication ≥0.99), §2.5 Analysis
  (Thompson-sampling bandit), Appendix B (walk-forward, no purge/embargo),
  Appendix C.1 ("median, not CI"), Appendix D.1 (schema-only LLM, OOS on
  CSI500/NASDAQ100 2024-25 post-cutoff).
- `docs/qlib-reuse-audit.md` (this session) — alpha158 overlap matrix, model_rolling
  purge/embargo gap, RD-Agent gating seam.
- Aionis `CLAUDE.md` — anti-leakage anchors (config_committed BEFORE result, PIT,
  PurgedGroupKFold+embargo, H6, two-tailed pre-registered).
- de Prado, *Advances in Financial Machine Learning* — deflated Sharpe ratio,
  PBO, purged CV + embargo (the discipline RD-Agent lacks).
- `aionis-publication-framing-option-a` memory — 2026-08-05 null+discipline framing.
