# Aionis

> A falsifiable, **anti-leakage** quantitative-finance research project. One
> pre-registered, two-tailed claim per phase on cross-sectional monthly rank-IC of
> S&P 500 point-in-time constituents. Null results with tight CIs are the intended,
> publishable outcome.

Aionis is **not** a cognitive system or a trading bot. It is a disciplined
experiment harness: each phase poses one falsifiable question ("does feature set X
add incremental cross-sectional predictability over fundamentals-only?"), answers
it on real PIT data with a frozen pipeline, and records the verdict — including
**null** — honestly. The **anti-leakage pipeline** below makes those claims auditable;
it does not erase their stated validation and data limitations.

---

## Headline — four historical cross-fitted results

Same S&P 500 PIT universe (588 clean tickers, 2016+), frozen nine-column baseline,
fixed LightGBM, and `PurgedGroupKFold(5, embargo=21)`. These are shared-fold,
purged cross-fitted/OOF comparisons, not strictly chronological or live OOS tests.
The treatment-minus-baseline monthly rank-IC differential is the falsifiable claim.

| phase | axis (treatment vs baseline) | differential | 95% CI | DM-p | evidence-bound verdict |
|---|---|---|---|---|---|
| **B** | fundamental *timing* (filed vs period-end+lag) | -0.000800 | **not recorded** | 0.870 | no significant positive increment; precision unknown |
| **C** | world-state *surprise* bundle (CPI/NFP/VIX/earnings) | -0.006487 | [-0.01953, 0.00656] | 0.355 | no significant positive increment; not strictly equivalent within post-hoc +/-0.015 |
| **D** | *relationship* bundle (SIC peer-mom + 13D events) | -0.002980 | [-0.01371, 0.00775] | 0.597 | no significant positive increment |
| **E1** | cross-firm *propagation* beyond own shocks | -0.002793 | [-0.01146, 0.00587] | 0.533 | no significant positive increment |

All four point estimates are negative; C/D/E1 intervals bracket zero. Phase B's
ledger row records its differential mean and DM p-value but no paired HAC SE or CI,
so its precision gate cannot be audited. None of B/C/D/E1 uses an LLM feature.
The h=10/42 sweep is exploratory, covers all four phases, and reuses the same
historical research family; it is sensitivity evidence, not independent replication.
The secondary strategy lens covers B/C only and is gross of costs with no turnover.

---

## The anti-leakage identity (what makes results auditable)

Every result is anchored by controls intended to make look-ahead and p-hacking detectable:

- **`config_committed` BEFORE result** — the frozen config's sha256 is written to
  an append-only ledger (`runs/ledger.jsonl`) *before* any outcome-bearing metric is observed.
  Same-sig reruns are bit-identical (H6 determinism, verified); a changed config is
  a new ledger row, never a silent overwrite. A headline cannot be
  "rerun-to-significance" rescued.
- **Point-in-time data** — fundamentals via `filed` date (not period-end); macro via
  ALFRED as-of vintages; VIXCLS unrevised (PIT via the no-revision contract); 13D
  via filing date; the S&P 500 universe via PIT membership (`constituents_on`).
- **PurgedGroupKFold + embargo** — group=month, embargo=21 sessions. It purges
  overlapping labels but cross-fits from the test complement, which may include
  later months; it does not establish chronological validation.
- **H6 determinism** — `n_jobs=1`, all seeds pinned, version-pinned; the IC series
  AND raw scores are bit-identical across reruns (asserted).
- **7-gate intake rubric** (`docs/data-intake-rubric.md`) — license / PIT / no-revision
  / snapshot / exploratory-only / selection-honesty / politeness. Permissive
  licenses only (MIT/Apache/BSD).
- **Controls** — bundle-shuffle placebo and leave-one-out attribution. The historical
  `ci_half < 0.015` precision flag is not a pre-registered equivalence test.

---

## Roadmap (TCR — Theory of Computable Reality)

A→E, each phase one falsifiable claim on the same benchmark:

- **A** (done) — ERL event representation pilot (underpowered).
- **B** (done; paired CI not recorded) — fundamental timing (filed vs period-end+lag).
- **C** (done; cross-fitted result) — world-state surprise bundle.
- **D** (done; cross-fitted result) — relationship/network bundle (13D + SIC peers).
- **E1** (done; cross-fitted result) — structural cross-firm shock propagation.
- **E2** (designed) — LLM macro-causal hypothesis-generator (cutoff-controlled;
  mitigates — does not eliminate — LLM hindsight leakage). *Design finding: the
  cutoff gate makes the E2 backtest underpowered (~10-18 post-cutoff months).*
- **E3** (engineering in progress; headline **NO-GO**) — forward-live accumulation.
  Commit/reveal primitives and dashboard work exist, but no scheduler, real E2E,
  shadow result, or live track record exists. Forward operation reduces outcome
  leakage only when its input and execution contracts are actually enforced.

The owner's vision — "see-through-to-essence" causal prediction (pandemic→pharma,
AI→compute→NVIDIA→power) — is the E2/E3 work. It is inherently leakage-prone if
backtested with a current LLM (it has memorized the outcomes); E3 forward-live is
the honest path.

---

## Dashboard

A near-final quant-evaluation interface (Streamlit + plotly), 10 tabs across the
five analytical dimensions (fit / volatility / curve-evolution / event-study /
uncertainty) + horizon-robustness + coverage + strategy-return + run-history:

```bash
uv run streamlit run dashboard/app.py
```

Current data demonstrates the analysis methods + interaction structure (not final
conclusions). The recorded evidence is summarized in `docs/RESULTS.md`.

---

## Install

Requires Python ≥ 3.10 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --all-extras          # base + extraction + dashboard + dev
cp .env.example .env          # fill FRED_API_KEY, TIINGO_API_KEY, ALPACA_*, REDDIT_* (LLM keys optional)
```

The LLM pool is **GLM / SiliconFlow / ModelScope only** (OpenAI-compatible); a
policy-aware multi-key router auto-fails-over on rate-limits
(`src/aionis/extraction/providers.py`).

## Reproduce a confirmatory run

```bash
# one-time data fetch (fundamentals + prices for the 588-ticker PIT universe)
uv run python scripts/phase_b_fetch.py

# a confirmatory run (e.g. Phase D): config_committed BEFORE result, H6-verified
uv run python scripts/phase_d_run.py

uv run pytest -q               # run the current hermetic suite
```

Each `scripts/phase_{b,c,d,e1}_run.py` is a thin wrapper over its testable
orchestrator (`src/aionis/eval/phase_*.py`); `scripts/strategy_eval_run.py` runs
the secondary L-S lens; `scripts/sensitivity_horizon.py` the horizon sweep.

---

## What is deliberately out of scope

A learned generative "world model" is **infeasible at this scale and leakage-prone**
(the `docs/frontier_positioning.md` + `docs/theory-of-computable-reality.md` §8.5
verdict). Aionis stays discriminative / leakage-controlled / falsifiable every
phase. The five-layer cognitive architecture and self-evolution engine are what
this experiment is meant to *justify building next* — not built speculatively.

## Operating frame (how this project is run)

Aionis uses a unified AI-workflow scaffold. The entry points for any agent or contributor:

- **`CLAUDE.md`** — stable project rules Claude Code reads natively (constraints, stack,
  commands, agent boundaries, definition-of-done, forbidden). `AGENTS.md` is a symlink to it
  for Codex portability.
- **`WORKFLOW.md`** — the operating constitution (the 11-stage pipeline, agent roster, workflow
  modes, token tiers, QA / review / stop-condition rules).
- **`state/current.md`** — live status (read first each session); `state/handoff.md`,
  `state/backlog.md`, `state/blockers.md` for continuity.
- **`decisions/`** — ADRs (point-in-time, record-once); see `decisions/index.md`.

New phases run the same anti-leakage pipeline: freeze config → `config_committed` ledger row →
PIT data → declared validation kind → frozen learner → rank-IC differential → controls → H6 →
verdict. Acceptance gates are in `docs/05-acceptance.md`.

---

## Docs

- `docs/RESULTS.md` — the falsifiable-results snapshot (the table above, expanded).
- `reports/audits/claim-reconciliation.md` — Fact/Inference/Hypothesis reconciliation
  and the evidence boundary for current public claims.
- `docs/00-vision.md` … `docs/08-lessons.md` — the numbered canonical index (vision → lessons).
- `docs/phase-{b,c,d,e1,e,e2,e3}-preregistration.md` — each phase's pre-registered
  claim + design (the discipline).
- `docs/data-intake-rubric.md` + `docs/data-license-allowlist.md` — the 7 gates.
- `docs/theory-of-computable-reality.md` — the TCR theoretical frame.
- `.omc/wiki/` — durable knowledge base (anti-leakage pipeline, phased results, PIT sources).
