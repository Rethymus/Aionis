# Live data refresh + iterative adaptive calibration — feasibility & disciplined path

> Owner directive (2026-08-08): historical data is now supplemented to 2016; the
> next step is (a) live data refresh and (b) using incoming data to continuously
> auto-calibrate the prediction model/algorithms in an iterative loop toward
> "impressive" (可观) prediction accuracy. This doc researches the field, maps it
> to Aionis's anti-leakage anchors, and recommends a disciplined path.
>
> Companion infra inventory: [`reports/2026-08-08-live-data-calibration-infrastructure-report.md`](../2026-08-08-live-data-calibration-infrastructure-report.md).
> Status: **PROPOSED analysis, owner-decision required**. No code/config/ledger changed.

## 0. TL;DR (the honest answer up front)

- **"Use latest data to auto-correct the model toward better predictions" is a real
  and legitimate idea — but only if "better" means sharper *calibration* + honest
  *drift/forward tracking*, NOT manufacturing a positive rank-IC.** The project's own
  null result + power floor say the latter is data-unreachable at monthly frequency.
- Aionis already has ~80% of the right machinery: `score_calibration.py` is a
  leakage-safe display calibration (Platt on realized pairs, latest month excluded),
  and E3 forward machinery is built (but owner-gated / cron-disabled).
- **Recommended path = Track A (display-layer adaptive calibration):** periodically
  refit calibration on an expanding realized window, add drift alarms, and wire an
  honest forward hit-rate accumulator. Leakage-safe, no research claim, no frozen
  surface touched.
- **Track B (research-layer online learning that chases IC)** is gated behind a new
  pre-registration + per-cycle `config_committed` + a DSR/PBO multiplicity budget,
  is likely to remain null (power floor), and conflicts with the frozen
  publication framing. Needs explicit owner GO.

## 1. The two structural tensions (resolve before any design)

**T1 — the anti-leakage / rerun-to-significance anchor.**
The frozen LightGBM, `config_committed BEFORE result`, PIT data, purged+embargo CV,
and the "no rerun-to-significance" rule are the project's core ([`CLAUDE.md`](../../CLAUDE.md)).
An "auto-correct the model on new data toward better accuracy" loop, **if it feeds
the research estimator (rank-IC)**, is the textbook definition of rerun-to-significance:
the same data is harvested repeatedly and the most favorable configuration is implicitly
selected. This is forbidden, not merely discouraged.

**T2 — the power-floor evidence.**
`scripts/ic_pure_noise_bound.py` + the 21-series survey show σ(IC) ≈ 0.10 (≈3.4× the
pure-noise bound 1/√(N−1)). `track_c_power_analysis` showed look-3 equivalence at
SESOI ±0.010 needs ~36 years of monthly data. **The data's signal-to-noise caps the
achievable IC; "calibrating the null into a positive effect" is unreachable in-sample
or out.** This is a measurement-floor fact, not an engineering deficit.

> Implication: the owner's word "impressive" (可观) must be re-grounded. If it means
> "IC turns positive / picks beat the market," T2 says no. If it means "the model's
> stated probabilities are trustworthy, drift is detected, and forward performance is
> tracked honestly," that is achievable and valuable. §5 develops this.

## 2. External research (what the field actually says)

### 2.1 Leakage-safe recalibration is a solved pattern — for *probabilities*, not IC
- **Walk-forward + past-PIT recalibration** is the disciplined standard: refit the
  calibration map on realized (score, outcome) pairs strictly *before* the prediction
  date, using a Probability Integral Transform history; explicitly designed to avoid
  look-ahead. ([arXiv 2601.07852, 2026](https://arxiv.org/html/2601.07852v1) — VERIFIED)
- **Gu-Kelly-Xiu 2020 (RFS)** — the canonical ML asset-pricing benchmark — used
  **expanding-window re-estimation** (retrain periodically as new data arrives). Trees
  + NNs best; **monthly OOS R² only 1.08–1.80%**. ([RFS](https://academic.oup.com/rfs/article/33/5/2223/5758276) — VERIFIED)
- `sklearn.isotonic` / Platt (`CalibratedClassifierCV`) are the standard tools
  ([scikit-learn](https://scikit-learn.org/stable/modules/calibration.html) — VERIFIED).

### 2.2 The adaptive/multiple-testing trap is the dominant risk
- **Deflated Sharpe Ratio** (Bailey & López de Prado, JPM 2014) corrects observed
  performance for (a) selection bias under multiple testing and (b) non-normality.
  The authors state DSR + **Probability of Backtest Overfitting (PBO)** are "especially
  useful complements when the research process is **highly adaptive**."
  ([SSRN 2460551](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551) — VERIFIED;
  [PBO PDF](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf) — VERIFIED)
- Concretely: every "auto-tune toward better IC" run is a *trial*; the apparent best is
  inflated by chance unless deflated by the **number of trials** (which must be
  recorded). A loop that quietly optimizes is exactly the failure mode DSR detects.
- Modern review: PBO/DSR "provided the statistical basis for quantifying overfitting"
  in the ML era ([ScienceDirect 2024](https://www.sciencedirect.com/science/article/abs/pii/S0950705124011110) — VERIFIED).

### 2.3 Adaptive-vs-frozen OOS evidence is sobering
- Gu-Kelly-Xiu: the dominant OOS driver was **model class (trees/NN), not update
  frequency**. (VERIFIED)
- Time-varying / online NNs ([arXiv 2003.02515](https://arxiv.org/pdf/2003.02515)) help
  under **structural breaks** but are **marginal in stable regimes** (VERIFIED).
- **Net:** retraining more often yields small, overfit-prone gains. Model choice and
  regime matter far more than refresh cadence.

> Aionis already sits *stricter* than the field standard: a frozen learner is more
  conservative than GKX's expanding window. Relaxing toward "adaptive" loosens
  anti-leakage discipline for, historically, marginal OOS benefit.

## 3. What Aionis already has (infra inventory — see companion report)

Source: [`reports/2026-08-08-live-data-calibration-infrastructure-report.md`](../2026-08-08-live-data-calibration-infrastructure-report.md) + code read.

- **`src/aionis/eval/score_calibration.py`** — *the* existing leakage-safe display
  calibration. Platt (default; constrained 2-param sigmoid — isotonic "overfits noise on
  a null model," per its own docstring). Fit on **realized** (score, fwd_return) pairs
  only; the latest unread month is naturally excluded by the NaN drop and only
  *predicted*. `CalibrationMeta.walk_forward = False` (disclosed display utility, not a
  research estimator). **This is ~80% of Track A's engine already.**
- **E3 forward machine** — built (slices 1–7; I1–I9 invariants; reveal-before-target
  gate; sha256-sealed scores; `config/e3_live_contracts.yaml` FROZEN `max_age_sessions=22`).
  **Status: NO-GO for headline, owner-gated, cron DISABLED** (`e3_live_contracts.yaml:13`).
  One-way (commit → wait 21d → reveal → score); **no feedback to training by design.**
- **Daily cron** (`refresh-terminal-data.yml`) — display-layer only: rebuilds ticker
  metadata + re-exports JSON. **Never touches the model, OOS scores, or ledger.**
- **Forward collectors** (`src/aionis/ingest/forward/` 13D/macro/8-K, + reddit RSS) —
  forward-only snapshots; `persist_snapshot` cumulative-append + `data_ingest` ledger rows.
- **Anti-leakage anchors are structural**, not accidental: `config_committed` sha256 is
  appended to `runs/ledger.jsonl` *before* any OOS metric is observed; same-sig reruns
  are bit-identical (H6); a changed config is a new ledger row, never a silent overwrite.
- **No feedback loop exists today.** Frozen OOS scores are display-only; realized
  outcomes do not feed back into anything. (This is the correct, disciplined state.)

## 4. Two-track decision

### Track A — display-layer adaptive calibration (**RECOMMENDED**, compliant)
Extend the existing `score_calibration` + E3 machinery into a leakage-safe,
**self-correcting display layer** — explicitly *not* a research estimator:

- **A1 Walk-forward calibration refit.** At each refresh, refit the Platt map on an
  expanding window of *realized* (score, fwd_return) pairs (strictly before the
  prediction date). Toggle `walk_forward=True` as a *display variant*; keep the frozen
  Track-C calibration untouched. → "The model's stated P(up) stays trustworthy as the
  sample grows."
- **A2 Drift alarms (display).** Monitor the rolling OOS score distribution / the
  conditional-IC series vs history; surface a "regime-shift / calibration-drift" flag in
  the terminal. Purely informational; never triggers a research rerun.
- **A3 Honest forward accumulator.** Wire E3 (or a lightweight display-only mimic) to
  commit current picks' scores → reveal at +21 sessions → score → accumulate a
  hit-rate/excess *display* series. **Critically: this series is never fed back into
  training.** It is the honest "how have the picks done" track record.

**Why it's compliant:** all three touch only the display layer; no `config_committed`
change, no frozen-surface edit, no IC estimator touched, no research claim. "Better
predictions" here = sharper calibration + honest tracking — the legitimate meaning.

### Track B — research-layer online learning (GATED; likely null; conflicts w/ framing)
If the owner truly wants the *model itself* to adapt toward better IC: this is a brand-
new research track, not an extension of the frozen one. Requirements:

- **New pre-registration** (new estimand; explicit adaptive/online design).
- **Per-cycle `config_committed`** ledger row (each recalibration = a new frozen config,
  sha256 before its result) — the loop's "trials" must be recorded for DSR.
- **DSR/PBO multiplicity budget** baked into the gate (§2.2): the adaptive process
  *will* inflate apparent skill; deflation is mandatory before any claim.
- **Hard separation from frozen Track C** (protect the confirmatory null).
- **Honest expectation:** per T2 (power floor) + §2.3 (adaptive gains marginal), this
  track will *probably remain null*. It also conflicts with the locked publication
  framing (memory: 勿追新 alpha / 勿救 equivalence). → **Explicit owner GO only.**

## 5. Reframing "impressive" (可观) — the crux

| Goal (colloquial) | Reachable? | Disciplined re-statement |
|---|---|---|
| Picks beat the market / IC turns positive | **No** (T2 power floor; §2.3) | Drop. The data forbids it at monthly frequency. |
| Model probabilities are trustworthy | **Yes** | Reliability diagram near the diagonal; base-rate-anchored P(up). (A1) |
| Detect when the regime shifts under the model | **Yes** | Drift alarm on rolling OOS behavior. (A2) |
| An honest, growing "how have calls done" record | **Yes** | Leakage-safe forward hit-rate/excess accumulator. (A3) |
| The model *improves itself* over time | **Dangerous** (DSR/PBO) | Only as a pre-registered Track B with multiplicity budget; expect null. |

The win condition worth engineering for is the middle three — they are genuinely
useful for a fintech terminal, fully leakage-safe, and honest. The first is a mirage
the project already disproved.

## 6. Phased plan (Track A)

| Phase | Work | Touches | Gate |
|---|---|---|---|
| **A1** | Walk-forward calibration refit (expanding realized window); `walk_forward=True` display variant; reliability-diagram export | `eval/score_calibration.py`, export, tests, terminal | none (display utility; no ledger) |
| **A2** | Drift alarm (rolling score-distribution / cond-IC vs history); terminal flag | `eval/`, export, terminal | none |
| **A3** | Honest forward accumulator (E3-lite or E3 itself, owner-GO); commit→reveal(+21d)→score→display series | `eval/forward*`, `forward` collectors, terminal | E3 owner GO if using the real forward ledger |
| **B** (only if owner GO) | New adaptive-IC track: prereg + per-cycle `config_committed` + DSR/PBO budget, separated from Track C | new phase, new ledger rows | owner GO + new frozen config |

Each phase is independently shippable and stays inside the display boundary (A1–A3) or
behind an owner gate (B).

## 7. Forbidden / hard limits (binding)

- **Never** feed realized forward outcomes back into the frozen LightGBM training.
- **Never** auto-tune hyperparameters/objective toward better IC on data that has been
  seen (DSR/PBO inflation — §2.2).
- **Never** let live/current prices enter the OOS pipeline (CLAUDE.md: live prices are
  DISPLAY ONLY; importing them = lookahead).
- Track B **must not** reuse the Track-C frozen surface; a changed estimand is a new
  ledger row, never a silent overwrite.

## 8. Bottom line

Track A is the disciplined, leakage-safe answer to "use the latest data to
self-correct": it sharpens *calibration*, surfaces *drift*, and accumulates an
*honest forward track record* — using machinery Aionis largely already has
(`score_calibration` + E3). Track B (manufacturing a better IC via online learning) is
gated behind a new pre-registration + multiplicity budget, is likely to remain null by
the power floor, and reverses the frozen publication framing — it needs explicit owner
GO. Recommend Track A and the §5 reframing of "impressive" as calibration + tracking
quality, not positive IC.

### Sources (external, VERIFIED unless flagged)
- [arXiv 2601.07852 — utility-weighted forecasting, walk-forward+PIT recalibration](https://arxiv.org/html/2601.07852v1)
- [Gu-Kelly-Xiu 2020, RFS — Empirical Asset Pricing via ML](https://academic.oup.com/rfs/article/33/5/2223/5758276)
- [Bailey & López de Prado — Deflated Sharpe Ratio (SSRN 2460551)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551)
- [Bailey/Borwein/LdP/Zhu — Probability of Backtest Overfitting](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf)
- [Backtest overfitting in the ML era (ScienceDirect 2024)](https://www.sciencedirect.com/science/article/abs/pii/S0950705124011110)
- [Time-varying NN for stock returns (arXiv 2003.02515)](https://arxiv.org/pdf/2003.02515)
- [scikit-learn — Probability Calibration](https://scikit-learn.org/stable/modules/calibration.html)
- (Inference, not re-verified this session: `river` online-learning lib = BSD-3; ADWIN/Page-Hinkley drift tests; champion-challenger MLOps.)
