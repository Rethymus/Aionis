# state/backlog.md — candidates, not committed

> Add ideas here during a sprint; evaluate at milestone boundaries. Do NOT interrupt the current
> task. See `WORKFLOW.md` §6 (freeze rules).
>
> 2026-09-21 轮 99 刷新：已完成项移入文末"已完成"区。owner-gated 研究项的权威清单在
> `tasks/active/TASK-RES-*.md`，此处只留指针。

## 开放候选

- **Phase B OOS panel.** `scripts/phase_b_run.py` predates the schema-2 OOS-persistence wiring;
  pass `oos_state` / `oos_base` to `save_run` + a solo B rerun so all 4 phases demo the fit charts.
  **S** task.（与 blockers 的 uv.lock sig 处置联动——先裁 sig 再跑 rerun。）
- **E2 build (LLM macro-causal, cutoff-controlled).** Blocked on TASK-STRAT owner decision.
  See `../docs/phase-e2-preregistration.md`, `../decisions/ADR-005-e2-underpowered-e3-forward-live.md`.
- **E3 forward-live launch.** The only POWERED zero-leak path; calendar-gated（9-30/10-31 影子窗，
  10-01 04:05 自动化已武装）。See `../docs/phase-e3-preregistration.md`.
- **Earnings as abstain / event-study event.** Zero-LLM abstention table (RD-08) covers
  FOMC/CPI/NFP/13D but NOT earnings; `earnings_8k_forward.py` exists so the PIT path is open.
  **BLOCKED until**: E3 headline HOLD lifted AND new owner-approved pre-registration/config
  (new event type = scope expansion; 7-gate; new ledger row). Never mutate B/C/D/E1. **M**.
- **SIC vintage.** SIC is current-snapshot (mild lookahead for reclassifiers); low priority
  (small effect). **M** task.
- **evals/cases golden fixtures.** Slot in once E3 forward-live produces commit/reveal fixtures.
- **Slice 2 review LOW×5 cleanup（advisory）。** first-run `last_poll_ts=None` docstring notes（3
  collectors）; structlog `warning` when `runs_dir is None and forward_only=True`;
  `earnings_8k_forward.py` 冗余 `keyfn = str.upper` 分支; `_common.persist_snapshot(...)` DRY 提取。
  一个 **S** cleanup 打包。

## Owner-gated（预注册级 GO 才可动；权威 spec 在 tasks/active/）

- **Strong-baseline ladder.** RES-01/02/03/10（momentum/FF5-cross-sectional/rank-label/LLM-eval）。
  FF5 另需数据准入（docs/data-intake-french-ff5.md）。
- **Economic-validity lens.** RES-04 next-open / RES-05 turnover-slippage / RES-06 liquidity-borrow /
  RES-07 delisting-capacity。
- **Zero-LLM ablation 扩展.** RES-09。
- **Gold set 后续阶段.** RES-08（stage 1 已冻结 e3-causal-gold-v1）。
- **P1-4 Track A 因子生成器.** 轮 59 裁决 DEFER 至 10 月末（单焦点纪律）。

## 已完成（自本清单销项，证据在 tasks/completed/ 或 state/current.md）

- ~~Horizon-robustness extension（h=10/h=42 已跑，B/C/D/E1 全 null 保持）~~（轮 ㉛ 审计发现已 DONE）。
- ~~SESOI/TOST + sequential gate~~ → AUD-07 + AUD-07B 完成（ADR-010 Amendment）。
- ~~Macro cumulative-preserve test [MEDIUM]~~ → ORCH-01 COMPLETE（8d19b28）。
- ~~LLM extractor evaluation 基建~~ → RD-04/05/06/07/08/11 + RES-10 rewrite 完成。
- ~~本地刷新通道/晚班 token 经济/GBK+NaN 修复~~ → 轮 89/96/97/98 运营化。
