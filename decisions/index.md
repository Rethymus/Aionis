# decisions/index.md — ADR registry

Architecture Decision Records: **point-in-time, record-once.** Status: proposed / accepted /
deprecated / superseded. Re-open an ADR **only** on its re-evaluation trigger (never re-litigate
without new evidence — see `../WORKFLOW.md` §5).

| ADR | title | status | date |
|-----|-------|--------|------|
| [ADR-001](ADR-001-tcr-theoretical-frame.md) | TCR (Theory of Computable Reality) as the theoretical frame | accepted | 2026-07-26 |
| [ADR-002](ADR-002-gkx-excluded-ticker-keyed.md) | Exclude GKX; self-built ticker-keyed PIT universe | accepted | 2026-07-27 |
| [ADR-003](ADR-003-vix-g3-not-vintage.md) | VIXCLS is unrevised → PIT via no-revision (G3), not vintage tracking | accepted | 2026-07-28 |
| [ADR-004](ADR-004-llm-structural-only-no-market-impact.md) | LLM extraction is structural-only (no `market_impact`) | accepted | 2026-07-26 |
| [ADR-005](ADR-005-e2-underpowered-e3-forward-live.md) | E2 backtest underpowered → E3 forward-live is the powered path | accepted | 2026-07-29 |
| [ADR-006](ADR-006-no-disposable-artifacts-registry.md) | Durable registry, not disposable one-shot artifacts | accepted | 2026-07-27 |
| [ADR-007](ADR-007-permissive-licenses-only.md) | Permissive licenses only (MIT / Apache / BSD) | accepted | 2026-07-26 |
| [ADR-008](ADR-008-launch-e3-and-broaden-nulls.md) | TASK-STRAT verdict: launch E3 forward-live + broaden nulls in parallel (reject E2-as-confirmatory) | accepted | 2026-07-30 |
| [ADR-009](ADR-009-e3-hybrid-causal-layer.md) | E3 causal-layer design: hybrid (zero-LLM frozen-β macro + minimal closed-enum LLM event edge); FF-12 unified taxonomy | accepted | 2026-07-31 |
| [ADR-010](ADR-010-sesoi-tost-sequential-gate.md) | E3 statistical gate: SESOI ±0.010 / HAC-TOST 90% / O'Brien-Fleming sequential / n_trials=30 (freeze before outcome inspection) | accepted | 2026-07-31 |

## How to add an ADR
Number it next (`ADR-011-…`), write it **before** the decision is reversed, never delete (supersede
with a new ADR that points back). Fields (per `../WORKFLOW.md` §1):

```
title / date / status / background / candidates considered / chosen / evidence /
cost / applicability bounds / re-evaluation trigger
```

Each ADR MUST end with a **re-evaluation trigger**: the concrete new evidence that would re-open it.
