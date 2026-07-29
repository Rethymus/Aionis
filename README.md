# Aionis

> A falsifiable, **anti-leakage** quantitative-finance research project. One
> pre-registered, two-tailed claim per phase on cross-sectional monthly rank-IC of
> S&P 500 point-in-time constituents. Null results with tight CIs are the intended,
> publishable outcome.

Aionis is **not** a cognitive system or a trading bot. It is a disciplined
experiment harness: each phase poses one falsifiable question ("does feature set X
add incremental cross-sectional predictability over fundamentals-only?"), answers
it on real PIT data with a frozen pipeline, and records the verdict — including
**null** — honestly. The discipline that makes any result trustworthy is the
**anti-leakage pipeline** below.

---

## Headline — four confirmatory claims, four publishable nulls

Same S&P 500 PIT universe (588 clean tickers, 2016+), same frozen LightGBM, same
`PurgedGroupKFold(5, embargo=21)`. Each phase's treatment arm is compared to a
fundamentals-only baseline; the rank-IC **differential** is the falsifiable claim.

| phase | axis (treatment vs fundamentals-only) | differential | DM-p | ci_half | verdict |
|---|---|---|---|---|---|
| **B** | fundamental *timing* (filed vs period-end+lag) | −0.0008 | 0.87 | 0.0098 | NULL |
| **C** | world-state *surprise* bundle (CPI/NFP/VIX/earnings) | −0.0065 | 0.36 | 0.0130 | NULL |
| **D** | *relationship* bundle (SIC peer-mom + 13D events) | −0.0030 | 0.60 | 0.0107 | NULL |
| **E1** | cross-firm *propagation* (SIC-peer shocks) | −0.0028 | 0.53 | 0.0087 | NULL |

All four differentials have 95% CIs bracketing 0 (NULL SUPPORTED); all are
publishable-as-null (ci_half < 0.015). A horizon-robustness sweep confirms B/C/D
hold at h=10 and h=42. The efficient-markets prior holds across timing / surprise /
relationship / propagation axes at monthly frequency. The strategy-return
(secondary) lens agrees: no long-short Sharpe survives the project-family DSR
deflation.

---

## The anti-leakage identity (why any result here is trustworthy)

Every result is anchored by a discipline that makes look-ahead/p-hacking detectable:

- **`config_committed` BEFORE result** — the frozen config's sha256 is written to
  an append-only ledger (`runs/ledger.jsonl`) *before* any OOS metric is observed.
  Same-sig reruns are bit-identical (H6 determinism, verified); a changed config is
  a new ledger row, never a silent overwrite. A headline cannot be
  "rerun-to-significance" rescued.
- **Point-in-time data** — fundamentals via `filed` date (not period-end); macro via
  ALFRED as-of vintages; VIXCLS unrevised (PIT via the no-revision contract); 13D
  via filing date; the S&P 500 universe via PIT membership (`constituents_on`).
- **PurgedGroupKFold + embargo** — group=month, embargo=21 sessions, no label leakage.
- **H6 determinism** — `n_jobs=1`, all seeds pinned, version-pinned; the IC series
  AND raw scores are bit-identical across reruns (asserted).
- **7-gate intake rubric** (`docs/data-intake-rubric.md`) — license / PIT / no-revision
  / snapshot / exploratory-only / selection-honesty / politeness. Permissive
  licenses only (MIT/Apache/BSD).
- **Controls** — bundle-shuffle placebo (must vanish), leave-one-out attribution,
  publishability gate (differential ci_half < 0.015).

---

## Roadmap (TCR — Theory of Computable Reality)

A→E, each phase one falsifiable claim on the same benchmark:

- **A** (done) — ERL event representation pilot (underpowered).
- **B** (done, null) — fundamental timing (filed vs period-end+lag).
- **C** (done, null) — world-state surprise bundle.
- **D** (done, null) — relationship/network bundle (13D + SIC peers).
- **E1** (done, null) — structural cross-firm shock propagation (zero-leakage).
- **E2** (designed) — LLM macro-causal hypothesis-generator (cutoff-controlled;
  mitigates — does not eliminate — LLM hindsight leakage). *Design finding: the
  cutoff gate makes the E2 backtest underpowered (~10-18 post-cutoff months).*
- **E3** (designed) — **forward-live** accumulation: run E1+E2 forward from launch,
  accumulate a real-time OOS track record. Forward = no future to leak *by
  construction*; the only **powered** path for the causal-prediction vision.
  Honest tradeoff: it takes calendar time (years) to power.

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
conclusions). The confirmed findings are summarized in `docs/RESULTS.md`.

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

uv run pytest -q               # 305 hermetic tests, ruff clean
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

## Docs

- `docs/RESULTS.md` — the falsifiable-results snapshot (the table above, expanded).
- `docs/phase-{b,c,d,e1,e,e2,e3}-preregistration.md` — each phase's pre-registered
  claim + design (the discipline).
- `docs/data-intake-rubric.md` + `docs/data-license-allowlist.md` — the 7 gates.
- `docs/theory-of-computable-reality.md` — the TCR theoretical frame.
- `.omc/wiki/` — durable knowledge base (anti-leakage pipeline, phased results, PIT sources).
