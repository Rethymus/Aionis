# ADR-001 — TCR (Theory of Computable Reality) as the theoretical frame

- **date:** 2026-07-26
- **status:** accepted

## Background
Aionis needed a *theoretical foundation* (not more modules). The owner directed elevating the
event-representation layer (ERL) to a **World Representation Language** (WRL) with four primitives
(Entity / State / Event / Relationship), and reframing the research object as the **latent world
state** of a civilizational-economic system (news / financials / capital-flow / CEO-behavior /
policy = noisy, selection-biased observations of that state).

## Candidates considered
1. Keep ERL-only, pragmatic (no formal frame).
2. A learned generative world model as the cognitive core.
3. A formal **TCR** frame: state = dynamic attributed graph $G_t$; transition
   $S_{t+1}=f(S_t,A_t,\varepsilon_t)$; observation $o_t^{(k)}\sim g_k(S_t,b_k)$ with selection bias;
   PIT filtering using only information $I_t$; falsifiable anchor $y_{t+h}=h(\hat S_t)+\eta$.

## Chosen
**(3) TCR** (`../docs/theory-of-computable-reality.md`, v0.1). `WRL.Event ≡ ERL` (strict superset
→ incremental, no rewrite). Phased roadmap A→E, each phase **one** pre-registered two-tailed claim
on the **same** return benchmark.

## Evidence / cost / bounds
- **Hard constraint (the doc's §8.5 / §11, "inconsistency invalidates this doc"):** TCR must NOT
  contradict `../docs/frontier_positioning.md` — learned world models are **infeasible at MVP scale
  and leakage-prone** (the ChaosAI +7-Sharpe leak; Tan NeurIPS 2024; 100M+ tokens). TCR's simulation
  layer is **interpretable scenario / network-propagation, NOT a learned generative model.**
- **Honesty boundaries:** no predicting black swans (only vulnerability / exposure / scenarios); no
  CEO-personality diagnosis (only observable-behavior decision-style); **returns stay the
  falsifiability anchor** (state is mechanism, returns are the checkup); simulation is an
  interpretive layer, NOT a second falsifiability hook.
- **Cost:** theoretical overhead; the simulation layer must stay discriminative / leakage-controlled.
- **Applicability:** the whole A→E roadmap.

## Re-evaluation trigger
A sub-MVP-scale learned-model result that beats the leakage-free baseline **without** leakage; OR a
TCR ↔ `frontier_positioning.md` contradiction that cannot be reconciled.
