# AUD-02 — Reconcile public factual claims to the tracked evidence

- 编号: AUD-02
- 标题: Make every current public/status claim match the ledger, artifacts, code semantics, and real verification output.
- 状态: **COMPLETE — independent Verifier PASS; Reviewer APPROVE**
- Priority: **P0**
- Size: **M**
- Risk: **HIGH**（更改公开研究表述；不得补算缺失指标或反向美化结论）
- 建议 agent role / model tier: **Researcher / strong → documentation Engineer / medium**；
  Verifier / strong；Reviewer / strong。
- 目标: 建立一张 Fact/Inference/Hypothesis 对账表，并只修正 mutable public surfaces；所有数字直接
  来自已跟踪 ledger/log，不生成新统计量。
- 背景: 当前 README 把 Phase B differential `ci_half` 写成 `0.0098`，但 ledger #28 未记录 B 的
  differential HAC SE/CI；多个页面称“四条均可发表”；`docs/RESULTS.md` 仍只列 B/C/D；OOS、策略、
  LLM 成本与测试绿色声明也存在范围或时效漂移。
- 依赖: AUD-01 PASS；AUD-03 至少先交付术语 verdict，最终文本须与 AUD-03 合同一致。
- 允许修改: `README.md`、`docs/RESULTS.md`、`docs/01-problem.md`、`docs/03-spec.md`、
  `docs/05-acceptance.md`、`docs/08-lessons.md`、`reports/milestone/README.md`、
  `reports/cost/README.md`、`state/current.md`、`state/handoff.md`；可新增
  `reports/audits/claim-reconciliation.md` 作为 durable evidence table。
- 禁止修改: `runs/ledger.jsonl`、`runs/results/**`、`runs/forward/**`、`data/**`、
  `docs/phase-*-preregistration.md`、`decisions/**`、历史 TASK-STRAT brief、任何源码/测试；禁止
  重算 B differential CI、运行 phase/strategy/horizon/forward 脚本或观察新 outcome。
- 前置条件: 将 ledger #28/#30/#34/#37/#38/#39、现有 Phase-A logs 与真实 pytest/ruff 输出逐项
  录入 evidence table，明确 source line 与 observed-at；缺字段写 `not recorded`，不得估算。
- 实施要求:
  - Fact / Inference / Hypothesis 分栏；事实与解释不得混写。
  - B 只能报告 `mean_diff=-0.000800...`、DM-p 与“differential CI 未记录”；不得称 B 已通过
    `ci_half < 0.015`，也不得用单臂 CI 或 README 数字替代。
  - C/D/E1、h=10/42、strategy lens 均保留其 confirmatory/exploratory 标签；策略只覆盖 B/C，
    gross-of-costs、无 turnover；horizon sweep 不是独立复制。
  - B/C/D/E1 headline 明确 zero-LLM；Phase A 是 53 ERL / 43 cluster 的 underpowered pilot；
    已记录 token 与约 72K 文档估算分开，未追踪 paid cost 必须明示。
  - 结果术语使用“purged cross-fitted/OOF differential”；不得把 B–E1 称为严格 chronological OOS。
  - 不改 frozen prereg/ADR；若历史文件与当前事实冲突，在 current surfaces 指明其历史状态。
- 验收标准:
  - [ ] 当前页面不再出现 Phase B `ci_half=0.0098` 或“四条均已由 differential CI 证明可发表”。
  - [ ] C/D/E1 值与 ledger 精确一致；E1 和四阶段 horizon sweep 出现在 current results snapshot。
  - [ ] OOF/chronological、confirmatory/exploratory、gross/net、LLM/no-LLM、actual/estimated cost 边界明确。
  - [ ] `state/current.md`/`handoff.md` 的测试数和 verdict 来自本次真实命令，不保留已失败的绿色声明。
  - [ ] evidence table 的每项 Fact 有文件/ledger 行；无法核实即降为 unknown，而非推断成事实。
  - [ ] frozen prereg、ADR、ledger、result artifacts diff 为空。
- 必须运行的测试: `uv run pytest -q`；`uv run ruff check`；
  `rg -n "0\.0098|four publishable nulls|四.*可发表" README.md docs state reports`（命中须逐项解释/清除）；
  `git diff --check`；`git diff -- runs/ledger.jsonl 'docs/phase-*-preregistration.md' decisions/`（空）。
- 失败处理: 任一数字在两个 tracked sources 冲突时标注 BLOCKED/unknown，并保留 ledger 为最高层
  observed source；禁止通过计算缺失 CI、重跑或修改 ledger 解决。
- 预期产物: durable claim-reconciliation evidence table + 已校正的 current public/status surfaces。
- 完成后需要更新: `state/current.md`、`state/handoff.md`，由独立 Reviewer 给出 APPROVE 后才关闭。
- see: `runs/ledger.jsonl:28`、`:30`、`:34`、`:37`、`:38`、`:39`；`docs/RESULTS.md`；
  `runs/extract_scaled.log`；`runs/compare_scaled.log`。

## 2026-07-31 execution evidence

- Documentation Engineer changed only the public mutable surfaces and new reconciliation table allowed by
  this task. No source, test, state, task, frozen, ledger, result, or data file was changed by AUD-02.
- Independent Verifier substantive checks PASS: no current `0.0098` claim; B paired CI remains unknown;
  C/D/E1 values match ledger; OOF/chronological, gross/net, zero-LLM, cost, and E3 NO-GO boundaries are
  explicit; ruff and diff/frozen checks pass.
- Orchestrator integrated verification after the documentation and concurrent remediation changes:
  `UV_CACHE_DIR=/tmp/aionis-full-verify-cache uv run --offline pytest -q` passed; `603 tests collected`.
  AUD-02 itself did not run a metric-producing or separate test command because it is documentation-only.
- Verifier requested the exact protected historical conflict and concurrent-scope attribution be recorded.
  The reconciliation table now names `reports/TASK-STRAT-e2-e3-decision-brief.md:169` and lists the AUD-02
  owned paths. Independent re-Verifier PASS confirms the repair; Reviewer APPROVE confirms no remaining blocker.
