# ADR-005 — E2 backtest underpowered → E3 forward-live is the powered path

- **date:** 2026-07-29
- **status:** accepted

## Background
The owner's "see-through-to-essence" causal-prediction vision (pandemic→pharma, AI→NVIDIA→power) is
the E2/E3 work. E2 = an LLM macro-causal hypothesis-generator with **cutoff control** (mitigates,
does not eliminate, LLM hindsight leakage).

## Candidates considered
1. Treat the **E2 backtest as the primary confirmatory claim**.
2. E2 as a **hypothesis-generator only**; **E3 forward-live** as the powered path.
3. Skip E2.

## Chosen
**(2)** — E2 is a hypothesis-generator (cutoff-controlled, mitigated leak); **E3 forward-live is the
only powered, zero-leak path.** See `../docs/phase-e2-preregistration.md`, `../docs/phase-e3-preregistration.md`.

## Evidence
- **The cutoff gate destroys power:** the 125-month OOS window collapses to **~10-18 post-cutoff
  months** → the E2 backtest is near-certainly underpowered.
- A current LLM has **memorized** the outcomes it would predict; cutoff gating mitigates but does
  not eliminate this. **E3 forward-live has no future to leak BY CONSTRUCTION** (commit-then-reveal:
  freeze $I_t$ → predict → commit sha256 → score at $t+h$ → append the forward ledger).

## Cost / applicability
- **Cost:** E3 takes **calendar time (years)** to reach power; the vision's confirmation is slow.
- **Applicability:** the E-sequence (E2 / E3). E1's null does NOT preclude E2/E3 (different mechanism).

## Re-evaluation trigger
A cutoff-control method that restores power without reintroducing leakage; OR enough forward-live
E3 accumulation reaches power.
