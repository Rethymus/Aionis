# state/backlog.md — candidates, not committed

> Add ideas here during a sprint; evaluate at milestone boundaries. Do NOT interrupt the current
> task. See `WORKFLOW.md` §6 (freeze rules).

- **Phase B OOS panel.** `scripts/phase_b_run.py` predates the schema-2 OOS-persistence wiring;
  pass `oos_state` / `oos_base` to `save_run` + a solo B rerun so all 4 phases demo the fit charts.
  **S** task.
- **E2 build (LLM macro-causal, cutoff-controlled).** Blocked on TASK-STRAT. If GO: implements the
  owner's "see-through-to-essence" vision with mitigated (not eliminated) LLM hindsight leakage.
  See `../docs/phase-e2-preregistration.md`, `../decisions/ADR-005-e2-underpowered-e3-forward-live.md`.
- **E3 forward-live launch.** The only POWERED zero-leak path; commit-then-reveal, PIT-safe live
  sources (13D / FRED / earnings). Takes calendar time (years) to power.
  See `../docs/phase-e3-preregistration.md`.
- **Earnings as abstain / event-study event.** The zero-LLM abstention table (RD-08) covers
  FOMC/CPI/NFP/13D but NOT earnings; `earnings_8k_forward.py` already exists, so the PIT data path
  is open. Hypothesis: earnings-filing windows may inject jump noise into the cross-sectional
  rank-IC estimand — candidate for an abstain rule or an event-study window in a NEW
  pre-registered arm. **BLOCKED until**: E3 headline HOLD lifted (AUD-06 + owner GO) AND a new
  owner-approved pre-registration/config (new event type = scope expansion; 7-gate intake; new
  ledger row). Never mutate B/C/D/E1. **M** task (eval-layer only). Source: 2026-08-02 owner-shared
  trading-report debrief — only the methodological point transferred (sector rotation / hedging /
  "beat the market" are out of scope by design).
- ~~**Horizon-robustness extension.** Sweep E1 at h=10 / h=42 (B/C/D already done) for symmetry.~~
  **DONE (discovered 2026-08-28 round ㉛ audit):** both sweeps already ran — B/C/D/E1 all
  nulls hold at h=10 AND h=42 (`runs/sensitivity_horizon.log` + `_a2.log`, gitignored;
  durable evidence = two `exploratory` `phase:"sensitivity_horizon"` rows in tracked
  `runs/ledger.jsonl`, latest = a2 amend). No rerun needed; surfacing happens via the
  `horizon_robustness` display panel (round ㉛ H1).
- **SIC vintage.** SIC is current-snapshot (mild lookahead for reclassifiers) — a vintage SIC
  would close it; low priority (effect estimated small). **M** task.
- **evals/cases golden fixtures.** Slot in once E3 forward-live produces commit/reveal fixtures.
- **E3 Slice 2 review follow-ups (Reviewer APPROVE, 2026-07-30).** Advisory, non-blocking; filed from
  the Slice 2 independent review. Priority order:
  - **[MEDIUM] macro cumulative-preserve test.** 13D + 8-K pin "a later `snapshot_ts` preserves prior
    rows"; macro does not (correct-by-shared `_common.append_cumulative_parquet`, just untested). Mirror
    `test_13d_forward_cumulative_parquet_preserves_prior_rows` for macro. **S** — closes the asymmetric
    anti-leakage invariant gap (a future regression to the shared helper would silently pass macro).
  - **[LOW ×5]** first-run `last_poll_ts=None` seeding docstring note (all 3 collectors); structlog
    `warning` when `runs_dir is None and forward_only=True` (real-ledger production path); drop the
    redundant `keyfn = str.upper` branch in `earnings_8k_forward.py:143`; optional DRY extract
    `_common.persist_snapshot(...)` for the shared archive+parquet+ledger+log tail; collector functions
    slightly >50 lines (collapses if the DRY extract lands). Batch as one **S** cleanup.

## Audit remediation candidates (not current execution)

- **[P1] SESOI/TOST + sequential-monitoring decision gate.** Produce an outcome-blind statistical
  decision brief before any E3 outcome-bearing shadow view or headline ignition; no pre-reg/ledger/code
  mutation in the brief task. **M / HIGH**. See
  `../tasks/active/TASK-AUD-07-sesoi-tost-sequential-gate.md`.
- **[P2] Strong-baseline ladder.** Evaluate momentum/reversal/volatility/liquidity, industry/size
  neutrality and a rank-aware learner only under a new owner-approved pre-registration/config; never
  mutate B/C/D/E1. **L candidate — Planner must split before assignment.**
- **[P2] Economic-validity lens.** Add next-open execution, turnover, slippage, liquidity, borrow,
  delisting and capacity after the chronological contract is accepted. **L candidate — split first.**
- **[P2] LLM extractor evaluation.** Build a licensed, timestamped human gold set and compare closed-enum
  GLM extraction against zero-LLM/rule baselines using precision, recall, coverage and abstention. **M / HIGH**.
