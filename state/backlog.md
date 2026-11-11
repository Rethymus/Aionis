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
- ~~**Slice 2 review LOW×5 cleanup（advisory）。**~~ **完成清账（10-05 轮 184）**：docstring 首跑注记
  ×3、structlog `forward_persist_real_ledger` warning、`persist_snapshot` DRY 均已在早前轮落地；
  最后一项 `keyfn = str.upper` 别名化简本轮落地（行为等价，forward 电池 EXIT=0）。

- ~~**i18n 字典按语言拆块（轮 201 候选）。**~~ **完成（10-06 轮 201，375064b19）**：每路由 -95KB；dict-zh 静态/dict-en 动态；audit+3 契约适配。

- **恢复道"仅重试软败步骤"策略（反思四 §一.3）。** 23:53 恢复道在 ok_committed 时 SKIP——软败步骤的
  数据最坏陈旧 24h+（如 GDELT 源缓存夜）。变更为"软败步骤选择性重跑"影响通道核心语义（幂等性/记账/
  push 边界），需 owner 对通道策略表态后专轮设计。**M**。

## 前沿吸收（轮 127，2026-11-11；来源=reports/audits/2026-11-11-env-testpipeline-round.md §6b——两路前沿调研中 high 但 L 规模/存疑/触红线者，逐条含来源 URL）

> 实施前逐条过 7-gate（docs/data-intake-rubric.md）与许可证白名单（MIT/Apache/BSD）。

1. **哈希链账本 + 一次性 holdout 回执 + 门合取**（https://arxiv.org/abs/2611.06607；MIT 参考实现 github.com/henryzhangpku/autonomous-quant-researcher）——**触红线**：`runs/ledger.jsonl` 语义零改动、receipt 属 scripts/phase_*。
2. **动量倾斜归因预注册**（https://doi.org/10.1016/j.jfds.2026.100207；SSRN 7010050）——下一 phase 预注册，owner 研究决策。
3. **知识截止/结果感知新门**（https://www.ravenpack.com/blog/insights-and-limitations-in-stock-price-prediction-using-llms；arXiv:2401.03737）——需改 docs/data-intake-rubric.md，非运维轮可触碰面。
4. **purged-CV 第二实现一致性测试**（https://github.com/eslazarev/purged-cross-validation，MIT 64★）——**存疑**：PyPI 可安装性未验证；CPCV/PBO 仅诊断、不作主分割器。
5. **time-machine 时间桩 conftest**（https://adamj.eu/tech/2026/08/03/python-time-machine-o1-freezegun-on；MIT v3.6.0）——8 个 src 模块墙钟语义分批。
6. **pytest-randomly**（https://github.com/pytest-dev/pytest-randomly，MIT v5.1.0）——2430 用例随机序体检 + 豁免治理。
7. **pytest-xdist -n auto --dist loadfile + faulthandler_timeout=300**（https://docs.pytest.org/en/stable/explanation/flaky.html，MIT v3.8.0）——需 H6 位一致豁免组设计。
8. **抽取错误分类学人工审计**（https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6496861）——人工标注成本 L；审计集与 prompt 调整隔离。
9. **组合级 FDR 读数**（https://people.duke.edu/~charvey/Research/Published_Papers/P143_False_and_missed.pdf）——docs/RESULTS.md 报告层，不回溯改 α。
10. **DSR 试验计数通缩 + minTRL**（https://arxiv.org/html/2512.12924v1）——N 随 config 冻结，仅预注册附录。
11. **时序共形区间**（https://arxiv.org/html/2507.05470v1）——稳健性视角，不变更主检验。
12. **actionlint + zizmor 常驻静态校验**（https://github.com/rhysd/actionlint；https://github.com/zizmorcore/zizmor，均 MIT）——二进制未装未跑；如集成 doctor 需条件存在守卫，保守后置。
13. **act 本地 dry-run**（https://github.com/nektos/act，MIT）——解锁前预检工具，不入 repo 依赖。

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
