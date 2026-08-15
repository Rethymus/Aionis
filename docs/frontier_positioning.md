# Aionis Frontier Positioning & Next Steps

> Synthesis of a 2026-07 frontier scan (3 parallel research passes) + the scaled
> real-data run. Purpose: locate Aionis in the field and define the shortest path
> from "complex system design" to disciplined, falsifiable research.

---

## 1. Scaled empirical result (this session, real data only)

- **Data**: 53 real FOMC-statement ERLs (GLM-4-flash extraction, structural-only),
  11 US sector ETFs + SPY, 2019-01 → 2025-09, h=1, real yfinance prices
  (retry/backoff-recovered), real GLM `embedding-3` → PCA-16.
- **XGBoost (primary learner)**: ERL lift **+5.5 pp** directional accuracy
  (CI [−4.2, +15.2] pp, DM_p ≈ 0.12). **Control gates pass cleanly**: neutral-text
  −1.9 pp, shuffled-date −1.9 pp (both ≈ 0). This is the discriminating pattern —
  real ERL lifts, controls do not.
- **MLP**: noisy; DM p-values fire on controls too → small-n over-rejection
  (see §2A). Inconclusive.
- **Honest read**: no longer a clean null — a **promising, gate-passing,
  underpowered positive** on the primary learner. CI still crosses 0 at n=43
  event-clusters. Total research token spend ≈ 72K (glm-4-flash) — economical.

---

## 2. How the frontier solves the core problems

### A. Event-driven forecasting & leakage-free inference
- **Signal exists but forward-predictability is weak.** Scheduled macro news causes
  *contemporaneous* price jumps (ABDV 2007; Bauer-Swanson 2023 `nber.org/w29939`;
  FRBSF USMPD 2025 `frbsf.org/wp2025-30`). Forward return predictability *beyond a
  price-only baseline* is the harder question, and the 2025-26 LLM-trading
  replications show most reported alpha is look-ahead leakage / multiple-testing /
  pre-cost fantasy: **Look-Ahead-Bench** (`arxiv.org/abs/2601.13770`),
  **Profit Mirage** (`arxiv.org/abs/2510.07920`, 51-62% Sharpe decay past
  cutoff), **Alpha Illusion** (`arxiv.org/abs/2605.16895`), **Can LLMs
  outperform long-run** (`arxiv.org/abs/2505.07078`).
  ⇒ **Pre-register the null as the betting favorite**; a clean positive is a
  *contrarian* finding worth publishing. Aionis's honest underpowered-positive is
  exactly what the field predicts.
- **Methodology wheels to adopt (all replace hand-rolled code)**:
  - **`purgedcv`** (`github.com/eslazarev/purged-cross-validation`) — Combinatorial
    Purged CV + path reconstruction + Deflated Sharpe + PBO; the audited sklearn
    reference for AFML chs.7/12.
  - **Fixed-smoothing / moving-block-bootstrap DM** (Coroneo-Iacone;
    Zhou-Li-Zhong 2021 `10.1016/j.econlet.2021.110028`) — vanilla HLN over-rejects
    at small n; this is the publishable default for clustered event panels.
  - **Harvey-Liu haircut** (`ssrn.com/abstract_id=2249314`) — t > 3.0 hurdle for any
    surviving sector×horizon result.
  - **One-switch decision-time-leakage audit** ("When Alpha Disappears: A One-Switch
    Benchmark for Decision-Time Leakage in Financial Backtests"
    `arxiv.org/abs/2605.23959`).

### B. Event representation & LLM extraction (the ERL question)
- **Representation**: FinGPT/BloombergGPT dominate domain NLP; **FinDKG** (KDD 2024,
  LLM→dynamic KG) and **central-bank text embeddings** (BIS WP 1253, 2025
  `bis.org/publ/work1253.pdf`) show text adds info *beyond* numeric expectations.
- **For data releases (CPI/NFP), the standardized surprise is the PRIMARY predictor**:
  `surprise = (actual − consensus)/σ` (Scotti 2013; Bauer-Swanson; "Caught by
  Surprise" `ssrn.com/abstract_id=4059314`). Text embedding is **complementary**,
  not a substitute. ⇒ Aionis's text-only path for CPI/NFP is suboptimal.
- **Extraction**: prefer **strict Structured Outputs** (constrained decoding,
  schema-by-construction) over open JSON prompting; place a reasoning field before
  answer fields. Benchmark against **FinBen-FOMC / OP-FED** (LLM zero-shot F1 ≈ 0.57).
- **The deep leakage is parametric, not schema-level.** Lopez-Lira et al. 2025
  (`arxiv.org/abs/2504.14765`) show LLMs memorize realized economic/financial
  data up to the cutoff (recall-level, extending into the embedding layer);
  instruction-based boundary respect fails, and entity anonymization leaks
  (entities/dates recoverable from minimal context). (The abstract's own wording
  is recall-level memorization, not "functional lookahead bias".) ⇒ Aionis's
  structural-only ERL is **necessary but
  insufficient**; it must be paired with point-in-time discipline + a memorization
  audit (PiT models like ChronoGPT for pre-cutoff history; FinCAD / MemGuard-Alpha).

### C. Causal forecasting & financial world models
- **Causal (realistic at n≈50-600)**: **Synthetic DiD / Synthetic Control**
  (Arkhangelsky et al. AER 2021 `10.1257/aer.20190159`; `pysynthdid`) — each event
  is an intervention, a donor pool of unaffected assets forms the counterfactual;
  scales gracefully with small n. Pair with a **pre-specified domain DAG +
  López de Prado's factor-mirage protocol** (`ssrn.com/abstract_id=4205613`) for
  feature selection. NOTEARS / CausalStock (`arxiv.org/abs/2411.06391`) need long
  stationary series — aspirational, not MVP-scope.
- **Learned world models are NOT feasible at MVP scale**: JEPA/Dreamer ports
  (Fin-JEPA; **ChaosAI** `github.com/ElMonstroDelBrest/ChaosAI`) need 100M+ tokens,
  and ChaosAI documents the standard cross-sectional OOS protocol leaking **+7
  Sharpe**. Tan et al. NeurIPS 2024 (`arxiv.org/abs/2406.16964`): LLMs don't help
  TS forecasting. **Defer the world-model claim**; keep a discriminative encoder;
  optionally use a frozen TSFM (Chronos/Moirai) only as a representation prior.

---

## 3. Aionis positioning

- **The contribution is leakage-aware causal event-impact attribution — explicitly
  NOT a learned world model.** That framing aligns with the 2025-26 factor-mirage /
  look-ahead-bias movement, survives TSFM skepticism, and keeps claims proportional
  to n.
- **The ERL structural-only design is a recognized best-practice rule (drop
  label-derived fields) — marginally novel as a stated design, but incomplete**
  against parametric memorization. The differentiator must be the *controls +
  PiT audit + causal estimates*, not the schema alone.

---

## 4. Next steps (reuse wheels; priority order)

1. **`purgedcv`** for CPCV + DSR + PBO + path reconstruction (replace hand-rolled
   `eval/cv.py`). Report a *distribution* of OOS paths, not one Sharpe.
2. **Fixed-smoothing / MBB DM** (`arch`/`statsmodels`) — replace vanilla HLN.
3. **Memorization + PiT audit**: pre/post-cutoff accuracy gap on famous events
   (FOMC 2020-03, CPI 2021-05); consider ChronoGPT for pre-cutoff embeddings.
4. **Add CPI/NFP numeric-surprise feature** (FRED realtime values + Bloomberg/Blue-Chip consensus) as first-class; text embedding becomes complementary. Requires the FRED key (already in `.env`).
5. **SDID causal event-impact estimates** (`pysynthsid`) as the headline causal
   result; discriminative ERL model as secondary.
6. Re-run powered (≥10 years, all three event types); benchmark ERL stance vs FinBen-FOMC.

All steps use existing libraries — no net-new infrastructure.
