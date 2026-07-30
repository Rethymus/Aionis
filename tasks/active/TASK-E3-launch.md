# TASK-E3 — Launch E3 forward-live (commit-then-reveal)

- 编号: E3
- 标题: Build + launch the E3 forward-live track (the only zero-leakage, powered path to a credible positive).
- 状态: **IN PROGRESS — Slice 1 + Slice 2 DONE** (spec `docs/phase-e3-implementation-plan.md` done;
  owner decisions 2026-07-30: **GLM** pinned + **shadow 1–2 mo** + defaults adopted.
  Slice 1 = forward-ledger commit-reveal core (`7ce7f08`). Slice 2 = forward PIT-as-of-t ingest
  (3 collectors + I3 monotonic-forward clock; Verifier PASS pytest 343 / Reviewer APPROVE 0 CRITICAL·HIGH).
  Next: Slice 3 = forward commit (fit-on-I_t → commit-before-reveal, reuses `two_arm` single-fit + `extra_features`).)
- 来源: [ADR-008](../../decisions/ADR-008-launch-e3-and-broaden-nulls.md) (TASK-STRAT verdict, 2026-07-30);
  `docs/phase-e3-preregistration.md`; **实施 spec**：`docs/phase-e3-implementation-plan.md`（架构 + 9 条零泄漏不变量 + 7 切片）。

## 目标 (Objective)
Per ADR-008 + `docs/phase-e3-preregistration.md`: implement the forward-live, commit-then-reveal
pipeline so monthly forward predictions begin accruing OOS samples — the multi-year path to either a
credible positive OR a tight publishable null.

## 范围 (scope — from the brief §5 + pre-reg)
- **Forward scheduler** — monthly, PIT-safe triggers (13D filings / FRED-ALFRED releases / earnings).
- **Forward ledger (commit-then-reveal)** — prediction sha256 committed BEFORE the t+21 outcome realizes.
- **Monthly scoring loop** — reveal + score past predictions as outcomes realize.
- **Forward ingest** — 8-K earnings, 13D (EDGAR filed-date), FRED/ALFRED as-of vintages.
- **Dashboard forward-IC tab.**
- Zero-leakage by construction (no backtest; the predicted event hasn't occurred at prediction time).

## 约束 (constraints)
- Inviolable anti-leakage anchors hold; commit-then-reveal extends "sha256-before-result" to
  **per-prediction** granularity.
- LLM pool = GLM/SiliconFlow/ModelScope only; structural-only extraction (no `market_impact`).
- **Irreversible once launched** — dropping mid-way zeros accrued months (sunk-cost rule, pre-reg §8).
- Pre-reg `docs/phase-e3-preregistration.md` is the frozen spec; changing it requires a new ADR.

## 大小 + 风险
- **Size: L** (multi-module; new forward infra). **Risk: HIGH** (irreversible calendar commitment;
  leakage-sensitive). Must run the full WORKFLOW.md pipeline (research → decision → freeze → slice →
  execute → verify → review) before any code.

## 前置条件
- [x] ADR-008 accepted.
- [x] E3 pre-reg exists (`docs/phase-e3-preregistration.md`).
- [ ] Planner slices this into verifiable sub-tasks (scheduler / forward-ledger / scoring / ingest / dashboard).

## 完成后需要更新
- `state/current.md`, `state/handoff.md`; `docs/RESULTS.md` (once forward predictions begin accruing).
