# AUD-02 public-claim reconciliation

> Reconciled: 2026-07-31. Scope: mutable public documentation only. No phase,
> strategy, horizon, forward, network, or metric-producing command was run. Missing
> fields remain `not recorded` or `unknown`; frozen pre-registrations, ADRs, ledger
> rows, result artifacts, state files, and task files were not changed.

## Evidence policy

Ledger event rows are authoritative for recorded research results. The repository
audit/task documents named by AUD-02 provide method and verification history.
Historical public documents may establish what was previously reported but do not override the ledger.
`runs/extract_scaled.log` and `runs/compare_scaled.log` exist locally but are gitignored;
the durable source for the Phase A log observation is therefore the dated audit that
records it, not an assertion that those logs are tracked artifacts.

`observed-at` means the event timestamp for ledger facts and the dated audit or
verification record for repository facts. It is not a newly computed timestamp.

## Facts

| ID | Fact | Source | observed-at | Public wording |
|---|---|---|---|---|
| F01 | Phase B has `n=125`, mean differential `-0.0008003561696833403`, and DM p `0.8695652173913043`; its paired differential HAC SE/CI fields are **not recorded**. | `runs/ledger.jsonl:28` | 2026-07-28T04:27:39Z | Report the mean and DM p; say paired CI not recorded. Never substitute either single-arm CI. |
| F02 | Phase C has `n=125`, mean differential `-0.006487473568317837`, 95% CI `[-0.019530768568940524, 0.006555821432304851]`, and DM p `0.3553223388305847`. | `runs/ledger.jsonl:30` | 2026-07-28T12:21:21Z | No significant positive increment observed. The interval is not contained in post-hoc `[-0.015, 0.015]`. |
| F03 | Phase D has `n=125`, mean differential `-0.0029798406036171702`, 95% CI `[-0.013714495699179569, 0.007754814491945227]`, and DM p `0.5972013993003499`. | `runs/ledger.jsonl:34` | 2026-07-29T02:43:23Z | No significant positive increment observed; the interval lies within a post-hoc +/-0.015 band, not a pre-registered equivalence test. |
| F04 | Phase E1 has `n=125`, mean differential `-0.0027928949986939897`, 95% CI `[-0.01145659242594545, 0.005870802428557472]`, and DM p `0.5332333833083458`. | `runs/ledger.jsonl:37` | 2026-07-29T03:43:41Z | Same boundary as F03; E1 is included in the current snapshot. |
| F05 | B/C/D/E1 use shared-fold purged cross-fitting. `PurgedGroupKFold` can use later observations in the candidate training complement; it is not strictly chronological OOS. | `tasks/active/TASK-AUD-03-chronological-validation-contract.md`, execution evidence; `reports/audits/2026-07-31-quant-llm-research-audit.md` §5.2 | 2026-07-31 | Use “purged cross-fitted/OOF differential” or “CV-proxy,” not unqualified chronological/live OOS. |
| F06 | None of the B/C/D/E1 headline feature sets uses an LLM. | `reports/audits/2026-07-31-quant-llm-research-audit.md` §§1, 7.1; frozen feature/config fields referenced there | 2026-07-31 | Say “zero-LLM headline”; do not attribute these results to small-model extraction. |
| F07 | The scaled Phase A pilot records 53 real FOMC ERLs and about 43 event clusters; XGBoost DA-lift is +5.5pp with CI `[-4.2pp, +15.2pp]`. | `docs/frontier_positioning.md:11`, `:14`, `:21` | historical scaled run; reconciled 2026-07-31 | Underpowered sector-ETF pilot; not a monthly stock-selection headline. |
| F08 | The Phase A extraction log observation is 41,689 prompt + 8,636 completion = 50,325 tokens. The historical approximately 72K figure is a broader research-token estimate; the two scopes are not reconciled. | `reports/audits/2026-07-31-quant-llm-research-audit.md` §7.1; `docs/frontier_positioning.md:22` | log 2026-07-26; audit 2026-07-31 | Keep observed extraction tokens separate from the approximate total estimate. Neither is paid cost. |
| F09 | Paid API cost, monthly E3 cost, cost per effective event, and human-review cost are not tracked. | `reports/cost/README.md`; audit §7.1 | 2026-07-31 | Use `not tracked`; do not estimate currency cost from tokens. |
| F10 | The h=10/42 results cover B/C/D/E1, are labeled `exploratory`, and all eight 95% CIs bracket zero. | `runs/ledger.jsonl:39` | 2026-07-30T05:29:47Z | Call a horizon sensitivity sweep, not confirmation or independent replication. |
| F11 | The strategy-return row covers B/C plus placebo/sanity, not D/E1. It is secondary/exploratory and gross of costs; no turnover is recorded. | `runs/ledger.jsonl:38`; audit §4.3 | 2026-07-29T18:03:13Z | No net, tradability, capacity, or D/E1 strategy claim. |
| F12 | E3 has no scheduler, real E2E, shadow/headline result, or live track record; headline readiness is NO-GO. | audit §§6.1-6.2; `state/current.md` | 2026-07-31 | Describe implemented primitives as engineering progress only. |
| F13 | AUD-03's repair record reports 589 tests; after concurrent AUD-05A additions, the Orchestrator's integrated `UV_CACHE_DIR=/tmp/aionis-full-verify-cache uv run --offline pytest -q` run collected and passed 603 tests. | `tasks/active/TASK-AUD-03-chronological-validation-contract.md`, `state/current.md`, current execution record | 2026-07-31 | Treat 589 as the AUD-03 historical checkpoint and 603 as the current integrated checkpoint; do not hard-code either in public setup instructions. |

## Inferences

| ID | Inference | Fact basis | Allowed boundary |
|---|---|---|---|
| I01 | The four frozen treatment bundles did not demonstrate reliable positive incremental rank-IC in this implementation. | F01-F04 | Limited to the frozen universe, features, learner, horizon, and cross-fitted validation. |
| I02 | Existing evidence is stronger for Aionis as an evidence-first research harness than as a validated stock-picking strategy. | F05, F09-F12 | A project-positioning judgment, not a statistical result. |
| I03 | D/E1 are more precisely bounded than C under a post-hoc +/-0.015 lens. | F02-F04 | Sensitivity description only; not confirmatory equivalence. |
| I04 | The horizon sweep is compatible with no detected differential across the tested horizons. | F10 | Not robustness “confirmation,” replication, or proof of no effect. |

## Hypotheses

| ID | Unresolved hypothesis | Required new evidence |
|---|---|---|
| H01 | The historical differential directions and intervals persist under strictly chronological validation. | New owner-approved, registered chronological study; not an AUD-02 recomputation. |
| H02 | A stronger numerical baseline or rank-aware learner changes treatment complementarity. | New frozen config, ledger row, and registered trial-family accounting. |
| H03 | Closed-set LLM event extraction adds incremental forward stock-selection information. | Gold-set extractor evaluation, zero-LLM ablation, and unknown-label forward evidence. |
| H04 | Any resulting portfolio has positive net economic value. | Turnover, next-open execution, costs, impact, borrow, delisting, liquidity, and capacity evidence. |

## Unknowns and blockers

| Item | Status | Consequence |
|---|---|---|
| Phase B paired differential HAC SE/CI | **not recorded** | B precision/equivalence cannot be audited; no four-phase tight-CI claim. |
| Pre-registered economic SESOI/TOST for B/C/D/E1 | **not recorded** | CI crossing zero cannot be upgraded to equivalence. |
| Phase A 50,325 vs approximately 72K scope reconciliation | **unknown** | Report separately; do not combine or convert to cost. |
| Paid and human-review costs | **not tracked** | No production/monthly/per-event cost claim. |
| Strict chronological B/C/D/E1 result | **not run** | Historical evidence remains cross-fitted/OOF only. |
| Net strategy performance and D/E1 strategy lens | **not recorded** | No tradability conclusion. |
| E3 live result | **does not exist** | Headline remains NO-GO. |

These unknowns block stronger research claims, but they do not block the documentation
reconciliation. Resolving them requires separately authorized research or governance work.

## Corrections applied

| Prior public claim | Reconciled claim |
|---|---|
| A numeric Phase B paired `ci_half` | Paired differential CI **not recorded**; no numeric value may be supplied. |
| Four publishable/equivalent nulls | Four negative point estimates; no significant positive increment; equivalence not established. |
| B-E1 are chronological OOS | Historical purged cross-fitted/OOF CV-proxies. |
| Horizon sweep confirms B/C/D | Exploratory h=10/42 sensitivity covering B/C/D/E1; not independent replication. |
| Strategy lens supports the four-phase headline | Exploratory B/C-only gross lens, no turnover or net-cost evidence. |
| LLM supports the four headline results | B/C/D/E1 are zero-LLM; Phase A is a separate underpowered pilot. |
| Token count implies low production cost | Logged tokens and broader estimate are distinct; paid cost is not tracked. |
| E3 is a live zero-leak track record | Engineering is incomplete and no live result exists; headline NO-GO. |

## Historical conflict and concurrent-scope record

The claim scan intentionally retains one historical wording in
`reports/TASK-STRAT-e2-e3-decision-brief.md:169`: “Phases B/C/D/E1 are four publishable
nulls.” That protected historical brief is outside the AUD-02 allowlist and was not
edited. Current mutable surfaces above supersede it for present status; the exact
conflict is recorded here rather than silently hidden.

The shared worktree also contains concurrent, separately scoped remediation changes.
AUD-02 owns only these changed paths: `README.md`, `docs/RESULTS.md`,
`docs/01-problem.md`, `docs/03-spec.md`, `docs/05-acceptance.md`, `docs/08-lessons.md`,
`reports/milestone/README.md`, `reports/cost/README.md`, and this evidence table.
Source, test, state, lockfile, and task changes belong to other AUD tasks and are not
attributed to AUD-02.
