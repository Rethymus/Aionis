# qlib + RD-Agent reuse-audit for Aionis

**Date:** 2026-08-11. **Author:** orchestrator (reuse-first mandate, owner direction).
**Scope:** what to reuse from `microsoft/qlib` (MIT, 47k★) and `microsoft/RD-Agent`
(MIT, 14k★, NeurIPS 2025 "R&D-Agent-Quant") into Aionis's falsifiable anti-leakage
harness — and where naive reuse would break the project's defining contract.

## TL;DR

Aionis and qlib alpha158 are **complementary, not subset**. Aionis is stronger on
fundamentals / risk / macro / sentiment (qlib alpha158 has **none** of these);
qlib is stronger on price-technical micro-structure (candlestick shape, quantile
position, volume micro-structure). The highest-value reuse is a **close-only
factor-pack** (~7 factor families Aionis lacks, addable from the existing `close`
column) + **RD-Agent as a candidate-generator behind Aionis's pre-registration
gate** (NOT as a runtime self-tuner). The adaptive-self-tuning framing is the
one collision with the 2026-08-05 null+discipline framing — flagged in §4.

## 1. Factor overlap matrix (qlib alpha158 vs Aionis)

Aionis's frozen panel (`track_b_panel.parquet`) carries: `close`, `momentum_{5,10,21,42}d`,
`reversal_5d`, `volatility_{21,63}d`, `beta_252d`, `amihud_illiquidity_21d`,
`turnover_21d`, `roe/roa/profit_margin/revenue_growth_{1m,12m}/asset_growth/leverage/
debt_to_equity/book_value_per_share/accruals/investment_12m`, `vix/cpi/payems` (macro),
+ computed risk factors (downside_beta, idiosyncratic_vol, skew, drawdown) + ff5 +
earnings_surprise + macro_regime + stakes_13d_signal. **OHLCV is fetched at ingest
but only `close` is carried into the panel.**

qlib alpha158 (158 factors, windows [5,10,20,30,60]) breakdown:

| qlib family | Aionis status | Verdict |
|---|---|---|
| ROC5/20/60 (rate of change) | ≈ `momentum_{5,21}d`, `reversal_5d` | **ALREADY** |
| STD5/20/60 (price vol) | ≈ `volatility_{21,63}d` | **ALREADY** |
| MA5/20/60 (moving avg) | ≈ momentum family | **REDUNDANT** (low marginal value) |
| BETA5/60 (price slope) | ≈ `beta_252d` (different window) | **PARTIAL** |
| **QTLU/QTLD** (80%/20% quantile pos) | absent | **NEW · close-only · PIT-safe** |
| **RSV** (stochastic oscillator) | absent | **NEW · close-only · PIT-safe** |
| **RANK** (percentile rank) | absent | **NEW · close-only · PIT-safe** |
| **MAX/MIN** (rolling extremes) | absent | **NEW · close-only · PIT-safe** |
| **CNTP/CNTN/CNTD** (up/down-day %) | absent | **NEW · close-only · PIT-safe** |
| **SUMP/SUMN/SUMD** (RSI-family) | absent | **NEW · close-only · PIT-safe** |
| **IMAX/IMIN/IMXD** (time-since-high/low) | absent | **NEW · close-only · PIT-safe** |
| KMID/KLEN/KUP/KLOW (K-Bar, candlestick) | absent (needs `open/high/low`) | **BLOCKED** (panel lacks OHLC) |
| VMA/VSTD/VSUMP/CORR/CORD (volume) | `turnover_21d` only | **BLOCKED** (panel lacks `volume`) |
| WVMA (volume-weighted vol) | absent | **BLOCKED** (needs `volume`) |
| RSQR/RESI (regression R²/residual) | absent | **NEW · close-only · PIT-safe** (niche) |

**qlib alpha158 LACKS that Aionis has:** fundamentals (ROE/margin/growth/leverage/
accruals/investment), FF5, earnings_surprise, macro_regime, risk factors
(downside_beta/idio/skew/drawdown), news sentiment, 13D signal. → Aionis is NOT a
subset; it is the broader factor set on the non-price side.

## 2. Anti-leakage gap (qlib `model_rolling` vs PurgedGroupKFold+embargo)

qlib's `model_rolling` (walk-forward retraining) is PIT-safe in the **training
direction** (past trains, future tests, roll forward) — no future data enters
training. **But it lacks two guards Aionis requires:**

1. **No purge at the fold boundary.** When the label horizon (e.g. forward 21d
   return) straddles the train/test split, labels near the boundary leak.
   Aionis's `PurgedGroupKFold(group=month)` drops the overlap.
2. **No embargo.** A test sample immediately after the train window has a label
   window that overlaps the train period → leakage. Aionis's `embargo=21`
   sessions drops the post-split test band.

qlib also **does not enforce PIT data** — it will happily train on today-snapshot
fundamentals if you feed them. Aionis's PIT layer (filed-date, ALFRED as-of
vintages, PIT S&P membership) is the additive shell qlib assumes but does not
provide.

**Where naive adoption leaks:** importing qlib's `model_rolling` + alpha158 handler
on Aionis's PIT data WITHOUT wrapping the CV in PurgedGroupKFold+embargo would
reintroduce the label-overlap leakage the project was built to prevent. The seam:
use qlib's **factor definitions** (loader expressions) + **signal-eval IC**, but
keep Aionis's `purgedcv.PurgedGroupKFold` as the CV, not qlib's rolling.

## 3. RD-Agent gating (the adaptive-loop collision + its disciplined seam)

RD-Agent's quant factor loop = **LLM proposes a factor expression (qlib syntax) →
qlib backtests → IC measured → loop iterates to maximize IC.** This is
rerun-to-significance **by construction** — it searches until it finds high-IC
factors, which is exactly the multiplicity trap that produces false discoveries.

**Disciplined integration (Reading A):** RD-Agent becomes a **candidate
generator** behind Aionis's pre-registration gate:

```
RD-Agent LLM proposes factor expr  →  Aionis computes on PIT data
  →  PurgedGroupKFold+embargo CV  →  OOS rank-IC + CI
  →  multiple-testing correction across ALL candidates tried (arch DSR/SPA)
  →  pre-registered verdict (two-tailed)  →  ledger row (config_committed BEFORE result)
```

The LLM's "this factor has high raw IC" does **not** auto-promote it. RD-Agent
optimizes against the **corrected** metric (penalizes multiplicity), not raw IC.
Most candidates will be null after correction — **which is the honest, publishable
outcome per the 2026-08-05 framing.** RD-Agent calls into Aionis via a single
evaluator interface: `evaluate_factor(expr) -> {rank_ic, ci_lo, ci_hi,
corrected_p}`. The LLM never sees raw IC; it sees the discipline-corrected
verdict.

**Reading B (forbidden):** RD-Agent's loop directly tuning model weights at
runtime on prediction-vs-actual feedback = rerun-to-significance + overfitting.
CLAUDE.md explicitly bans this.

## 4. Integration recommendations (prioritized)

| # | Action | Effort | Leakage risk | Needs A/B decision? | 2026-08-05 framing |
|---|---|---|---|---|---|
| 1 | **Bump CI timeout 45→75** (done) — breaks Form-4 cold-pull vicious cycle | S | zero | no | preserves |
| 2 | **Close-only factor-pack**: add QTLU/QTLD, RSV, RANK, MAX/MIN, CNTP/CNTN, SUMP/SUMN (RSI), IMAX/IMIN to Aionis's feature builder (all from existing `close`) | M | low (PIT close only) | no | preserves (more features for the frozen learner) |
| 3 | **qlib signal-eval IC as cross-check** of Aionis's rank-IC | S | zero (validation only) | no | preserves |
| 4 | **Extend panel to carry OHLCV** → unlocks K-Bar + volume factors | M | low (PIT OHLCV) | no | preserves |
| 5 | **Adopt qlib portfolio backtest** for L4 cost-layer validation (net sharpe) | M | low | no | preserves |
| 6 | **RD-Agent as candidate-generator** behind the pre-reg gate (Reading A) | L | medium (must enforce the gate) | **YES** | preserves IF strictly gated; reverses if used as self-tuner |
| 7 | **OHLCV K-Bar + volume factors** (after #4) | M | low | no | preserves |

## 5. The A/B decision (the one item that needs the owner)

The owner's vision ("自适应校准进而逐步提高准确率") has two readings; #6 is the
collision point:

- **Reading A (disciplined):** RD-Agent proposes factors; Aionis's freeze→
  pre-register→purge→embargo→ledger gate decides what's real. "Adaptive" =
  across-phase, honest. Preserves the null+discipline framing. The LLM is a
  candidate source, not a decision-maker.
- **Reading B (predictor pivot):** runtime self-tuning of weights on feedback.
  Maximizes accuracy = overfits = reverses the 2026-08-05 framing. Changes the
  project's identity from "falsifiable harness" to "adaptive predictor."

**Recommendation:** Reading A. It captures the owner's intent (LLM-assisted,
iterative, accuracy-improvement *when real*) without surrendering the anti-leakage
contract that makes Aionis's results worth anything. The honest path is: the LLM
proposes many factors, the discipline rejects most (null with tight CI — publishable),
and the few that survive ARE genuine discoveries.

## License note

qlib + RD-Agent are MIT (clean for Aionis). `qusong0627/QuantMind` (qlib-based
platform, conceptually closest to the owner's vision) is **AGPL-3.0** — excluded
as a dependency (network-use disclosure trigger), usable only as a concept
reference per the owner's license-relaxation (private non-commercial study).

## Sources

- `microsoft/qlib` `qlib/contrib/data/loader.py` Alpha158DL (158 factors, windows [5,10,20,30,60])
- `microsoft/qlib` `examples/model_rolling/` (walk-forward; no purge/embargo)
- `microsoft/RD-Agent` `rdagent/scenarios/qlib/` + NeurIPS 2025 "R&D-Agent-Quant"
- Aionis `data/cache/track_b_panel.parquet` columns (panel carries `close` only)
- Aionis `CLAUDE.md` anti-leakage anchors
