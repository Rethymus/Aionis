# ADR-004 — LLM extraction is structural-only (no `market_impact`)

- **date:** 2026-07-26
- **status:** accepted

## Background
LLM extraction of events could plausibly include a `market_impact` field (the model's reading of
how the market reacted).

## Candidates considered
1. **Full extraction** including `market_impact`.
2. **Structural-only** — event type, entities, dates, magnitudes; **NO `market_impact`.**

## Chosen
**(2) structural-only.** `WRL.Event` / ERL carries structure only.

## Evidence
- Including `market_impact` lets the LLM's **memorized price reaction leak into the feature**
  (the López-Lila memorization non-identification problem): the model has seen the outcome and would
  encode it, contaminating the label (forward returns).
- Structural-only keeps the label **independent** of the LLM's price knowledge. See
  `../docs/theory-of-computable-reality.md`.

## Cost / applicability
- **Cost:** discards a potentially signal-rich (but leakage-prone) field.
- **Applicability:** all LLM extraction (ERL / WRL.Event), backtested phases.

## Re-evaluation trigger
In **E3 forward-live** (where the LLM cannot have memorized future outcomes) `market_impact` may be
reconsidered — still under cutoff control, and recorded as a new ADR.
