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
- **Citation anchor (2026-11-13, frontier-citation-anchors — citation-only, no package,
  no integration):** arXiv:2611.03985 *Thinking Fast, Trading Late: System One Decision
  Models vs the Market* (OLIVIA protocol, cs.AI 2026-11-02; abstract first-hand
  re-checked this session) — commercial decision models identify **masked** companies
  in 62–74% of cases against a 28% baseline ("masking hides names, not companies",
  掩码 ≠ 匿名：掩码防不住记忆化价格反应), and no pre-registered strategy survives costs
  + deflated Sharpe. External support for keeping LLM extraction structural-only (no
  `market_impact`). NewsAction repo license MIT (per research-side verification; not
  installed, not introduced).

## Cost / applicability
- **Cost:** discards a potentially signal-rich (but leakage-prone) field.
- **Applicability:** all LLM extraction (ERL / WRL.Event), backtested phases.

## Re-evaluation trigger
In **E3 forward-live** (where the LLM cannot have memorized future outcomes) `market_impact` may be
reconsidered — still under cutoff control, and recorded as a new ADR.
