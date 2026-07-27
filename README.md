# Aionis MVP

> **Autonomous Intelligence for Financial World Evolution** — but this repo is a
> single, honest experiment, not a cognitive system.

Aionis as a vision is a five-layer financial world model. This MVP does not
build that. It builds **one falsifiable test of its foundation**:

> **Does a structured event representation (ERL) extracted from scheduled macro
> events (FOMC / CPI / NFP) carry information that improves sector-ETF return
> prediction beyond a price-only baseline?**

If structured events carry no price-independent signal here, the later layers
(causal reasoning, self-evolution) have nothing to stand on. If they do, the
foundation is worth building upward from.

---

## The alignment rule (the whole experiment's validity hinges on this)

For each event with timestamp `event_ts` (NYSE-localized):

```
t_info      = the last NYSE close STRICTLY BEFORE event_ts
label_start = the first NYSE close AT OR AFTER event_ts   (reaction embedded)
label_end   = the NYSE close h trading sessions after label_start
target      = close[label_end] / close[label_start] - 1
```

**Every feature column must be a function of closes ≤ `t_info`.** A single
feature that touches a close ≥ `label_start` is a look-ahead leak and
invalidates the with-vs-without comparison. `tests/test_alignment.py` asserts
this invariant and is the most important test in the repo.

## Pre-registered primary metric (frozen before unblinding)

- **Pooled directional-accuracy lift** of `with-ERL` minus `price-only` at
  **h = 1** — "pooled" = over all (event, symbol) rows; the headline is reported
  **per learner** (XGBoost is the primary, MLP the secondary). Cluster-robust
  bootstrap CI on the per-event-date lift mean, and a **Diebold-Mariano** test on
  the squared-error loss differential (Newey–West HAC bandwidth h−1, Harvey–
  Leybourne–Newbold small-sample correction, Student-t reference), clustered by
  **event-date** (not by row).
- Mandatory control gates must pass: **neutral-text** extraction and
  **shuffled-date** pairing must show *no* lift. If lift survives a control, the
  result is an artifact and the claim is killed.
- A null result with a tight CI is a legitimate, publishable outcome.

---

## Why ERL is structural-only (important deviation from the vision doc)

The original ERL design put `market_impact {direction, magnitude, confidence}` in
the LLM-extracted event object. That is an **architectural leak**: the LLM has
memorized macro-event outcomes, and post-hoc source text bakes in the move. With
`market_impact` present, ERL "wins" by echoing the answer, not by carrying
signal.

This MVP therefore restricts the LLM-extracted ERL to **structural / semantic
fields only** (who did what, to whom, why, expected temporal class, extraction
uncertainty). **Market impact is the downstream model's prediction target**, not
an extraction product. `historical_similarity` is likewise excluded from
extraction (deferred to controlled retrieval over the event store).

---

## Install

Requires Python ≥ 3.10 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync                              # light base (Phases 0–1 + tests)
uv sync --extra extraction           # + OpenAI / FRED / embeddings (Phases 2–3)
cp .env.example .env                 # fill OPENAI_API_KEY, FRED_API_KEY
```

## Quickstart

```bash
# Phase 0 — data spine (needs FRED_API_KEY)
uv run aionis ingest --start 2010-01-01 --end 2025-12-31
uv run pytest tests/test_alignment.py      # leakage invariants (most critical)

# Phase 1 — the number ERL must beat (no LLM, no keys beyond FRED)
uv run aionis eval-priceonly

# Phase 2 — ERL extraction (needs OPENAI_API_KEY)
uv run aionis extract

# Phase 3 — the decisive comparison
uv run aionis compare
```

A synthetic end-to-end smoke test runs without any keys:

```bash
uv run pytest tests/test_pipeline_smoke.py
```

---

## Multi-key provider router (auto key switching by policy)

ERL extraction runs through a **policy-aware multi-key router** (`PROVIDER=router`
in `.env`, the default). It holds a pool of OpenAI-compatible providers, each with
its policy terms (RPM / TPM / daily quota), and auto-switches keys on rate-limit
(429 → 60 s cooldown) or invalid output — so a free-tier limit on one provider
transparently fails over to the next. Per-provider token/call accounting is logged.

- **Provider catalog**: `src/aionis/extraction/providers.py` (add a provider = one
  entry + its key in `.env`).
- **Wheel**: the `openai` SDK with per-provider `base_url` (universal for
  GLM / SiliconFlow / ModelScope OpenAI-compat).
- **Select a single provider**: `uv run aionis extract --provider modelscope`.

| provider | status | note |
|---|---|---|
| GLM (`glm-4-flash`) | ✅ priority 1 | free, concurrency-limited |
| SiliconFlow (`Qwen2.5-7B`) | ⚠️ priority 2 | small model → invalid ERL → auto-failover |
| ModelScope (`Qwen3-Next-80B`) | ✅ priority 3 | 2000 calls/day, failover backstop |

---

## Status

| Phase | Scope | Status |
|-------|-------|--------|
| 0 | Data spine + leakage tests | implemented |
| 1 | Price-only baseline + eval harness | implemented |
| 2 | ERL schema + offline extraction | implemented |
| 3 | Decisive comparison + control gates | implemented |
| 4 | Robustness (CPCV, per-type, post-cutoff) | deferred |
| 5 | GDELT scale-up (BigQuery only — REST is 3-month rolling) | deferred |

## What is deliberately out of scope

The five-layer cognitive architecture, causal-graph layer, and self-evolution
engine are **not** in this MVP. They are the things this experiment is meant to
justify building next.
