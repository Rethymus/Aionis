# state/handoff.md — current-pass handoff

- **round:** AUD remediation SATURATED — all autonomous priority work done; everything remaining owner-gated. 2026-07-31.
- **outcome:** project remains an evidence-first PIT research harness, not a validated stock-picking strategy.
  Historical B/C/D/E1 are shared-fold purged CV-proxies (not chronological OOS); LLM not in headlines;
  E3 NO-GO for headline.
- **COMPLETE:** AUD-01/02/03/04/05A/05B (each Verifier PASS + Reviewer APPROVE); AUD-05C disposition
  (Reviewer APPROVE; 10 boundaries → C1-C5 + Kenneth-French task files); **AUD-07 FROZEN** via
  [ADR-010](../decisions/ADR-010-sesoi-tost-sequential-gate.md) + E3 pre-reg §7 (SESOI ±0.010 / HAC-TOST
  90% / O'Brien-Fleming 60·90·120mo / n_trials=30; 3× cross-validated; equivalence+sequential
  construction amended).
- **C-series prepped → owner-decidable:**
  - **C3 (PRAW 7-gate)**: CLEAR-WITH-CONDITIONS (all 7 gates PASS; G1 BSD-2/Apache-2.0, G2 PIT,
    G3 snapshot handles user-edits, G4 sha256+append, G5/G6 exploratory-only, G7 PRAW 1.5s+ToS).
    Conditions: Reddit ToS internal-only/no-redistribute; permanent `mode:exploratory`. → owner GO/REJECT.
  - **C4 (health_check)**: remove `akshare/EastMoney` (BLOCKED); keep EDGAR/FRED/Tiingo/Alpaca/gh;
    **standalone (Option A)** recommended (auxiliary monitor, own 2.0s gap+retry, off-peak cron).
    → owner GO.
  - **C5 (model-API ≥2s)**: **Option A (SDK-exempt)** recommended — model APIs throttled by provider
    RPM/TPM + ProviderRouter cooldown + idempotent cache; ≥2s redundant for GLM (RPM 30), harmful for
    SiliconFlow (RPM 1000). Rule wording drafted. → owner accept.
- **P2 split → owner-authorizable**: 10 S/M OWNER-GATED `TASK-RES-01..10` created (baseline-ladder
  RES-01/02/03 [mom/FF5/rank-objective]; economic-lens RES-04/05/06/07 [next-open/turnover-slippage/
  liquidity-borrow/delisting-capacity]; LLM-eval RES-08/09/10 [gold-set/zero-LLM-ablation/eval-metrics]).
  Each registers a NEW trial, respects ADR-010, touches only `tasks/active/`. RES-08 (gold-set) is
  highest-leverage + owner-participatory.
- **owner-decision queue (consolidated — further progress needs these):**
  - **C1/C2**: held or GO? (BLS-disable S/LOW; VIX-FRED-wrapper M/MED, preserves ADR-003).
  - **C3**: accept CLEAR-with-conditions (GO wrapper) or reject (disable PRAW live)?
  - **C4**: GO remove akshare + standalone health_check?
  - **C5**: accept Option A + record the rule wording?
  - **Kenneth-French / selection-panel FRED+Fama-French**: data-intake 7-gate decision.
  - **AUD-06**: owner contract (E3 live-input readiness acceptance points).
  - **RES-01..10**: which to authorize first? (RES-08 gold-set highest-leverage).
  - **Commit?** large uncommitted set (prior audit pass + AUD-01..05C + ADR-009/010 + RES tasks);
    HEAD `87af583`, ahead 4.
- **verification:** 620 hermetic tests green; ruff clean; `runs/ledger.jsonl` 39; frozen prereg/ADR/
  config/ledger/results/data untouched across ALL AUD/RES-prep work; no E3 outcome observed; no
  confirmatory/strategy/horizon/forward script run.
- **proxy note:** 3-parallel subagent spawns fail with proxy 400 `[1210]`; ≤2-parallel / single work.
  Future dispatch ≤2 concurrent.
- **do NOT:** run confirmatory/strategy/horizon/forward scripts; edit frozen prereg/ADR/config; infer
  B's paired differential CI; call historical cross-fit chronological OOS; inspect E3 outcome metrics;
  ignite E3 headline.
- **git:** branch `feat/e3-forward-ledger`, HEAD `87af583`, ahead 4; + large uncommitted AUD-01..05C
  + ADR-009/010 + RES-01..10 + prior-audit doc/code pass.
