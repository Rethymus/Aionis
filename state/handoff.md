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
