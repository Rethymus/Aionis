# state/handoff.md — current-pass handoff

- **round:** Wave-A execution. AUD-05B is closed after authorized re-Review. Dashboard extraction
  and C4 Option A cleanup are committed in `7dede9b`. C1 BLS disable, C2 VIX FRED adapter and C3
  PRAW requestor wrapper are COMPLETE after Engineer evidence, independent Verifier PASS and
  independent Reviewer APPROVE, and are ready for the Group A commit. 2026-08-01.
- **outcome:** project remains an evidence-first PIT research harness, not a validated stock-picking strategy.
  Historical B/C/D/E1 are shared-fold purged CV-proxies (not chronological OOS); LLM not in headlines;
  E3 NO-GO for headline.
- **COMPLETE:** AUD-01/02/03/04/05A/05B (each Verifier PASS + Reviewer APPROVE); AUD-05C disposition
  (Reviewer APPROVE; 10 boundaries → C1-C5 + Kenneth-French task files); **AUD-07 FROZEN** via
  [ADR-010](../decisions/ADR-010-sesoi-tost-sequential-gate.md) + E3 pre-reg §7 (SESOI ±0.010 / HAC-TOST
  90% / O'Brien-Fleming 60·90·120mo / n_trials=30; 3× cross-validated; equivalence+sequential
  construction amended).
- **STATISTICAL HOLD:** AUD-07B reopens the implementation-level proof only: ADR-010's amendment says
  TOST p-values “exceed alpha”, which appears reversed, and the sequential equivalence construction
  requires strong independent review. Do not implement or expose E3 inferential verdicts meanwhile.
- **C-series prepped → owner-decidable:**
  - **C3 (PRAW 7-gate)**: OWNER APPROVED WITH CONDITIONS (all 7 gates PASS; G1 BSD-2/Apache-2.0, G2 PIT,
    G3 snapshot handles user-edits, G4 sha256+append, G5/G6 exploratory-only, G7 PRAW 1.5s+ToS).
    Conditions: Reddit ToS internal-only/no-redistribute; permanent `mode:exploratory`. Engineer,
    Verifier and Reviewer are complete; no live pull is authorized.
  - **C1 (BLS disable)**: owner-authorized disable-only implementation is complete. CPI/NFP cache
    misses fail closed before HTTP; FOMC/cache behavior is preserved. Independent Verifier PASS and
    Reviewer APPROVE are recorded; Group A commit is next.
  - **C2 (VIX/FRED)**: owner-authorized implementation replaces SDK fetches with the shared-policy
    FRED observations adapter while retaining ADR-003 PIT/cache/ledger behavior. Independent
    Verifier PASS and Reviewer APPROVE are recorded.
  - **C4 (health_check)**: standalone Option A is owner-authorized and complete in `7dede9b`.
    The blocked data/wheel probes and stale text are removed; seven hermetic tests, lint, scan and
    review pass.
  - **C5 (model-API ≥2s)**: **Option A (SDK-exempt)** recommended — model APIs throttled by provider
    RPM/TPM + ProviderRouter cooldown + idempotent cache; ≥2s redundant for GLM (RPM 30), harmful for
    SiliconFlow (RPM 1000). Rule wording drafted. → owner accept.
- **P2 legacy split → partially replan-required**: 10 prior `TASK-RES-01..10` files exist (baseline-ladder
  RES-01/02/03 [mom/FF5/rank-objective]; economic-lens RES-04/05/06/07 [next-open/turnover-slippage/
  liquidity-borrow/delisting-capacity]; LLM-eval RES-08/09/10 [gold-set/zero-LLM-ablation/eval-metrics]).
  RES-02/03/08/10 are now HOLD/REPLAN because of cross-sectional-variation, rank-label,
  durable-gold and remote-determinism defects. Do not authorize those files as written; use RD tasks first.
- **owner-decision queue (consolidated — further progress needs these):**
  - **C5**: accept Option A + record the rule wording?
  - **Kenneth-French / selection-panel FRED+Fama-French**: data-intake 7-gate decision.
  - **AUD-06**: owner contract (E3 live-input readiness acceptance points).
  - **RES program**: no legacy RES task should start before RD-17 and its listed prerequisites; RES-02/03/08/10
    specifically require rewritten specs.
  - **RD program**: launch only P0 closure, P0 + the offline RD-01..17 program, or selected RD tasks?
  - **Commit?** audit remediation is committed as `e8545d4` and dashboard/C4 remediation as
    `7dede9b` (both on remote `main`). C1/C2 await independent review before their own commit.
- **verification:** the full hermetic pytest suite currently passes (existing forward-score warnings
  only), `uv run --offline ruff check` and `git diff --check` pass, and frozen
  prereg/ADR/config/ledger/results/data/forward remain untouched. Group A C1/C2/C3 each have
  independent Verifier PASS and Reviewer APPROVE. `runs/ledger.jsonl` remains unchanged; no E3
  outcome was observed and no confirmatory/strategy/horizon/forward/real-network/LLM script ran.
- **planning artifact:** `reports/milestone/2026-08-01-low-reasoning-development-roadmap.md` and
  the Wave-A launch brief and `TASK-RD-00..17` split the next safe work into a 10.75–16 hour first
  offline wave and a 25.5–40 hour complete Engineer package. `TASK-AUD-07B` is strong-only. This is a
  frozen task proposal. The final unattended prompt selects C1/C2/C3 + RD-04/05/06/07/09/10/12,
  has explicit context-compaction/token rules, and received independent Reviewer APPROVE. It becomes
  implementation GO only when the owner pastes it into the new Goal session.
- **proxy note:** 3-parallel subagent spawns fail with proxy 400 `[1210]`; ≤2-parallel / single work.
  Future dispatch ≤2 concurrent.
- **do NOT:** run confirmatory/strategy/horizon/forward scripts; edit frozen prereg/ADR/config; infer
  B's paired differential CI; call historical cross-fit chronological OOS; inspect E3 outcome metrics;
  ignite E3 headline.
- **git:** branch `feat/e3-forward-ledger`; remote `main` includes `7dede9b`. Current uncommitted
  code includes approved C1/C2/C3 implementation/tests plus planning/state/task documentation; the
  Group A commit will use explicit file lists only.

## Overnight checkpoint (Wave-A)

- Goal: execute Wave-A C1/C2/C3 + RD-04/05/06/07/09/10/12 with independent gates and safe push. **COMPLETE.**
- All gates passed: C1/C2/C3 + RD-04/05/06/07/09/10/12 each have independent Verifier PASS + Reviewer APPROVE.
  Fixes applied and re-gated: RD-07 (generated_at caller-provided for byte-stability), RD-10 (vol_adj_mom
  last-12 window + std<=0), RD-12 (additive constituents_manifest_on + 3 unskipped manifest oracles;
  constituents_on behavior unchanged).
- Commits: `6085e92` Group A, `2653907` Group B, `5f884a3` Group C. Final docs/state bundle (this commit).
- Final gates: full hermetic pytest green (zero skips; only pre-existing forward_score warnings);
  `uv run --offline ruff check` clean; `git diff --check` clean; frozen/ledger/results/data/forward diff
  empty; no data/.env/*.parquet staged; no real network/LLM/research/forward script ran; E3 outcome unobserved.
- Files: RD-01/02/03/08/11/13..17 task specs remain PLANNED (future waves) — committed as planning docs.
- Blockers: none. Next: optional fast-forward push HEAD:main (origin/main is ancestor of HEAD).

## Wave-B checkpoint (2026-08-01, in progress)

- **Launch authorization:** owner `/goal` — "启用更多 agents 根据优先等级在不影响各自进程的前提下各自推进".
  Treated as owner authorization for the priority (P0→P1) offline RD program (the safe sonnet-tier set).
  Per-task authorization is recorded in each task file's 状态 line by the Orchestrator as the audit trail.
- **COMPLETE so far** (each: Engineer → independent Verifier PASS → independent Reviewer APPROVE → atomic
  commit; offline/hermetic; `runs/ledger.jsonl` untouched; no frozen surface touched):
  - RD-02 validation manifest — `97e5688`
  - RD-01 task-contract linter — `feb80ba` (first attempt lost to the parallel-writer race below; redone serially)
  - RD-13 cross-sectional variation guard — `2f0efd0`
- **KEY OPERATIONAL FINDING (binding):** spawning ≥2 writer subagents concurrently in the SHARED working tree
  loses one agent's untracked deliverables (RD-01 first attempt: `.pyc` survived in gitignored `__pycache__`,
  `.py` + README diff gone — consistent with a `git clean -fd`/`restore` across parallel-agent boundaries).
  **Writers are now SERIALIZED: exactly ONE Engineer subagent per message.** Parallel is reserved for read-only
  preflights only. See memory `aionis-parallel-writer-race`.
- **Model routing (binding):** only `sonnet`/`haiku` subagent aliases resolve to subagent-safe IDs; `opus`/`fable`
  resolve to `[1M]`-suffixed IDs and are DENIED by the enforcer. The RD program is sonnet-tier so this is fine.
  `TASK-AUD-07B` (strong-only, STATISTICAL HOLD) and `RD-15` (strong precondition) are DEFERRED until opus
  routing is fixed (drop `[1M]` suffix from `ANTHROPIC_DEFAULT_OPUS_MODEL`).
- **Authorization bookkeeping:** the first RD-02 Reviewer returned BLOCKED solely because the task file still said
  "PLANNED — not implementation-authorized"; resolved by recording the /goal authorization in the task 状态 line.
  All subsequently launched RD tasks are pre-authorized in their task files before dispatch.
- **Remaining safe queue (P1, sonnet-tier):** RD-17 (trial-intent registry) → RD-16 (eval uncertainty) → RD-11
  (provider replay) → RD-03 (chronological oracle, unlocked by RD-02 APPROVE) → RD-14 (reproducibility capsule,
  unlocked by RD-02 APPROVE). RD-08 remains HOLD (needs a strong-Researcher-frozen rule table first). RD-15 deferred (strong).
- **Verification status:** per-task pytest + ruff green; ledger empty diff across all Wave-B commits; no frozen
  prereg/ADR/config/result/data/forward surface touched; no real network/LLM/trial ran. The full hermetic suite
  has NOT been re-run this wave yet (defer to a pre-push gate).
- **Git:** branch `feat/e3-forward-ledger` ahead of origin by 8 (Wave-A + Wave-B). Not pushed (owner's call).
- **Do NOT:** run confirmatory/strategy/horizon/forward scripts; edit frozen prereg/ADR/config; observe E3
  outcome; spawn >1 writer subagent per message.

## Wave-B FINAL (2026-08-01, COMPLETE)

All 8 safe sonnet-tier RD tasks implemented, each with independent Verifier PASS + Reviewer APPROVE and an
atomic commit; offline/hermetic throughout:
- RD-02 validation manifest — `97e5688`
- RD-01 task-contract linter — `feb80ba` (first attempt lost to the parallel-writer race; redone serially)
- RD-13 cross-sectional variation guard — `2f0efd0`
- RD-17 trial-intent registry (HIGH-risk; ledger-bypass cleared) — `5dfe849`
- RD-16 eval uncertainty (Wilson≠Wald; seed=0 stratified bootstrap) — `ee223ae`
- RD-11 provider replay (salvaged a cut-off partial; audited + completed; providers/llm_client 0 diff) — `8a46179`
- RD-03 chronological oracle (HIGH-risk; cv.py 0 diff; lookahead rejected; real purgedcv) — `af7d673`
- RD-14 reproducibility capsule (outcome-free; deterministic capsule_id; atomic write + refuse-overwrite) — `f397383`

Final pre-push verification: full hermetic pytest GREEN (zero failures/skips; only the pre-existing
forward-score UserWarnings documented in Wave-A); `uv run --offline ruff check` clean; `runs/ledger.jsonl`
0 diff across the whole wave; frozen-surface audit (docs/phase-*, decisions/, runs/ledger, config/, data/,
*.parquet, pyproject.toml, uv.lock) — NONE touched; no real network/LLM/trial/forward script ran; E3 outcome
unobserved.

Process notes (binding for future waves):
- Writers are SERIALIZED (exactly one Engineer subagent per message) — parallel writers in the shared tree
  lost untracked deliverables (see memory aionis-parallel-writer-race).
- Only `sonnet`/`haiku` subagent aliases are dispatchable; `opus`/`fable` resolve to `[1M]` IDs and are
  denied by the enforcer → `TASK-AUD-07B` (strong-only) + `RD-15` (strong precondition) are DEFERRED until
  opus routing is fixed.
- The `[1210]` proxy "API parameter" error is transient on Reviewer spawns — a single retry has succeeded
  every time; it is NOT the 5-hour usage cap.
- Owner authorization for the priority RD program was the `/goal` directive; recorded per-task in each task
  file's 状态 line. (The first RD-02 Reviewer BLOCKed on the stale "PLANNED — not implementation-authorized"
  status, which is why all later tasks were pre-authorized in their task files before dispatch.)
- Per the owner: do not spend tokens checking whether the 5-hour usage cap has reset — if the session is
  running, it is reset (see memory aionis-no-rate-limit-check).

Remaining (NOT started — legitimately blocked, not merely unauthorized):
- RD-08 HOLD — needs a strong-Researcher-frozen zero-LLM rule table before low-reasoning implementation.
- RD-15 DEFERRED — rank-objective contract is a strong-model decision precondition (lambdarank vs rank_xendcg,
  monthly relevance binning, ties, missing, group=query-month); also needs opus routing.
- AUD-07B — STATISTICAL HOLD on ADR-010 TOST p-value direction / sequential-equivalence construction; strong-only.
- RES-02/03/08/10 — HOLD/replan per roadmap; their foundations (RD-13 done; RD-15/RD-08 still pending) must
  precede them.

Git: branch `feat/e3-forward-ledger` ahead of origin by 13 (Wave-A + Wave-B). Not pushed — owner's call.
Safe RD queue now exhausted for the sonnet tier.

## AUD-07B — statistical review COMPLETE (2026-08-01, CRITICAL finding)

AUD-07B (P0 / CRITICAL) is now reviewed by TWO opus agents (a strong-statistician audit + an INDEPENDENT
opus Reviewer, APPROVE). Both confirm ADR-010's equivalence/sequential gate has TWO CRITICAL defects:
1. **TOST rejection direction is REVERSED.** ADR-010 Line 42 requires the two one-sided p-values to
   "exceed alpha" (p > α); the correct Schuirmann (1987) rule is: declare equivalence iff p1 < α AND p2 < α.
   As written, the gate would declare NON-equivalence, not equivalence.
2. **Sequential CI duality is BROKEN.** ADR-010 pairs a fixed 90% CI with look-specific O'Brien-Fleming αk,
   which breaks the TOST⇔CI duality at looks 2–3 and inflates first-look Type I error ~9.6× (0.05 vs
   ~0.0052). Correct construction: look-specific (1−2αk) CIs (98.96% / 96.84% / 91.26%), or a recognized
   group-sequential equivalence construction (Jennison–Turnbull 2000).
CI duality at α=0.05 (90% CI), the union–intersection composite null, and HAC (Newey-West) SE all PASS.
Report: `reports/audits/e3-tost-sequential-correction-review.md`.

CONSEQUENCE (binding): the E3 inferential-verdict and headline remain HOLD. Implementing or exposing any E3
equivalence verdict before the owner authorizes an ADR-010 + prereg §7 amendment (p < αk; look-specific CI)
is FORBIDDEN. This is an owner decision — ADR-010 and the prereg are frozen; the audit does NOT modify them.
Open non-blocking note: ADR-010's αk source (0.0052 / 0.0158 / 0.0437) is undocumented and did not match the
reviewer's independent Lan-DeMets OBF recomputation — owner should confirm the αk provenance as part of the
amendment.

## Model-differentiation policy (2026-08-01, per owner /goal)

opus subagent routing was fixed (`ANTHROPIC_DEFAULT_OPUS_MODEL` now `claude-opus-4-8`, no `[1M]` suffix).
Difficulty-based dispatch is now in effect to save tokens:
- **opus** — only genuinely hard analysis/decisions (AUD-07B statistician + reviewer done; RD-15 rank-objective
  contract and the RD-08 zero-LLM rule-table draft are the next opus candidates).
- **sonnet** — standard code/review (Wave-B RD tasks).
- **haiku** — mechanical verification, simple doc/grep checks.
Writers remain SERIALIZED (one Engineer per message; parallel-writer rule still binds).

## RD-15 — rank-objective DECISION PACKET proposed (2026-08-01, pending owner freeze)

RD-15 (P2 / HIGH-risk) decision precondition is now drafted by an opus Architect at
`reports/design/2026-08-01-rd15-rank-objective-contract.md` (PROPOSED — pending owner freeze). 7 of 8
choices are determined by theory; ONE is an owner-preference question:
- **Open owner question:** bin count for monthly relevance — **quintiles (5, robust, default)** vs
  **deciles (10, aggressive)**. Ranking theory does not uniquely determine this for the rank-IC estimand.
Theory-fixed choices: objective = **lambdarank** (rank_xendcg rejected; allowed-enum fixed so non-existent
objectives are rejected); per-month quantile binning fit ONLY on the train fold; group = query-month; ties
share the relevance integer; NaN returns excluded (NaN features → LightGBM default); test out-of-range
returns clamped to nearest train-fold edge + reason code (never refit). Four testable leakage invariants
specified (month-permutation, future-truncation, train-fold-only fit, group-size stability).

After owner freeze, a sonnet Engineer implements `src/aionis/eval/ranking_contract.py` + tests mechanically
(no self-selection). No code/learner/frozen surface changed by the decision packet.

### Update (2026-08-01, continued — model-differentiated dispatch)
- **RD-15 implementation COMPLETE** — `ea335c8` (sonnet Engineer + independent Verifier PASS + Reviewer
  APPROVE; 0 blocking). `src/aionis/eval/ranking_contract.py` implements the decision packet (objective enum
  lambdarank/rank_xendcg; per-month train-fold-only binning; out-of-range clamp+reason; group=query-month; 4
  leakage invariants). `bin_count` is a parameter (default 5/quintiles, supports 10/deciles) — the methodology
  freeze of the actual value remains the owner's (via config), not hard-coded. learner.py untouched (0 diff);
  31 module tests + full suite (1348) green.
- **RD-08 rule table PROPOSED** — `evals/expected/zero_llm_rules_v1.yaml` (opus strong-Researcher), pending
  owner freeze. 10 conservative abstain-heavy rules (FOMC×3, CPI×2, NFP×2, 13D×3); default/conflict=abstain;
  8k_2_02 deferred. Two owner decisions flagged: 13D actor_type (COLLECTIVE vs ORGANIZATION) and whether to
  include 8k_2_02. After freeze, a sonnet Engineer implements `src/aionis/extraction/zero_llm_baseline.py`
  verbatim from the table.
- **Tier usage this session:** opus for AUD-07B (statistician + independent reviewer) and RD-15 decision +
  RD-08 rule-table draft (genuinely hard analysis/domain-modeling); sonnet for all Wave-B code + RD-15 impl +
  verifications/reviews (standard). haiku unused — no remaining priority task is mechanical-tier (forcing it
  would be false economy). Reviewer `[1210]` proxy errors were bypassed by switching `oh-my-claudecode:code-
  reviewer` → `general-purpose` (same sonnet tier) when they recurred.

## Owner decisions + independent opus reviews (2026-08-01)

Owner decisions: ADR-010 → Jennison-Turnbull construction (B); RD-15 bin_count → quintiles/5 (A); RD-08 → freeze
(A) + COLLECTIVE + defer 8k_2_02; RES → hold (A); commission independent opus review of RD-08 + RD-15 (5B);
housekeeping done (local main FF to origin/main; remote feat/e3-forward-ledger deleted). All Wave-B/AUD-07B/
RD-15/RD-08 work pushed to origin/main (HEAD e58b16e).

Independent opus review outcomes:
- **RD-15 decision packet: APPROVE** (0 CRITICAL/MAJOR; leakage guards sufficient, implementation faithful).
  Owner froze bin_count=5.
- **RD-08 rule table: REQUEST CHANGES → FIXED → FROZEN.** Review found 4 CRITICAL (enum NAME vs lowercase VALUE;
  FOMC forward-guidance false positives; 13D→13d; negation-window unit undefined) + 2 MAJOR (CPI/NFP secondary
  patterns; rule-count comment). An opus fixer resolved all: lowercase enum values; added fomc_guidance_abstain_001
  (precedence 110, abstain-only); 13d; negation = whitespace words; tightened CPI/NFP; accurate count (now 11).
  event_type semantics confirmed: FOMC/CPI/NFP are valid (`src/aionis/config.py` ECONOMIC_EVENT_TYPES); the gold
  `Literal["13d","8k_2_02"]` is filing-specific. Table FROZEN.

Still queued (owner-authorized, not yet done this session): RD-08 sonnet implementation of `zero_llm_baseline.py`;
ADR-010 Jennison-Turnbull amendment (opus design + independent opus review + apply to frozen ADR-010/prereg §7).

## ADR-010 Amendment APPLIED (2026-08-01) — Jennison-Turnbull; RD-08 implemented

- **RD-08 zero-LLM baseline COMPLETE** — `src/aionis/extraction/zero_llm_baseline.py` (sonnet Engineer + haiku
  lint-fix + independent Verifier functional PASS + independent Reviewer APPROVE). Mechanically applies the
  FROZEN rule table (11 rules; lowercase enum values; sha256 provenance; 6 abstain paths; fomc_guidance_abstain_001
  precedence-110 suppresses forward-guidance false positives). Structural-only (no sentiment/market_impact);
  providers/llm_client/frozen table untouched. Committed + pushed.
- **ADR-010 Amendment 2026-08-01 APPLIED** (owner Decision 1 = option B). The broken "Cross-validation amendment
  (2026-07-31)" is VOID; replaced by a Jennison-Turnbull (2000) group-sequential equivalence construction
  (OBF zₖ = z_α/√Iₖ → look-specific RCI levels 99.44 / 97.64 / 95.00%; equivalence iff RCIₖ ⊂ [−SESOI, +SESOI],
  which structurally prevents the reversed-direction error; Type I ≤ 0.05). Prereg §7 amended in lockstep.
  Ratified sub-choices: standard OBF (over Lan-DeMets — more conservative early), no futility, 95% final look.
  Frozen params unchanged (SESOI ±0.010, looks {60,90,120}, n_trials=30, HAC SE). Double-opus (design +
  independent review) at `reports/audits/e3-jt-amendment-proposal.md`; audit at
  `reports/audits/e3-tost-sequential-correction-review.md`.
- **CONSEQUENCE:** the E3 statistical-gate HOLD from AUD-07B is LIFTED (the gate is now mathematically valid).
  E3 itself remains gated by AUD-06 (live-input readiness) + a separate owner GO (per the AUD-00 dependency
  graph); no E3 ignition is authorized here. Eval-code implementation of the RCI rule is a separate future task.

All owner decisions 2026-08-01 are now executed except RES restart (intentionally held) and optional follow-ups
(RD-08 rule-table re-review, eval-code RCI implementation). Everything is on origin/main.
