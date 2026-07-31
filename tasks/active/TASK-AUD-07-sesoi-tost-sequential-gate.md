# AUD-07 — Specify SESOI/TOST and sequential-monitoring gates before E3 outcomes

- 编号: AUD-07
- 标题: Define practical-equivalence and repeated-look inference before any E3 outcome-bearing metric is viewed.
- 状态: **awaiting owner steer — backlog candidate; hard gate before headline ignition**
- Priority: **P1**
- Size: **M**
- Risk: **HIGH**（inferential policy 不可在看到 forward outcomes 后倒订）
- 建议 agent role / model tier: **Researcher/Statistician / strong**；Verifier / strong；Reviewer / strong。
- 目标: 输出 owner-decision-ready 的统计规格草案，明确 SESOI、TOST、sequential monitoring、停止规则、
  multiplicity 与 shadow visibility；本任务不实现代码、不新建/修改 pre-reg、不观察 E3 outcome。
- 背景: 当前项目把 `ci_half < 0.015` 当“publishability”精度门，但 CI 跨零且较窄不等于统计上的
  practical equivalence。E3 dashboard/score runner会随月份重复查看 CI，若无预先冻结的 repeated-look
  规则，会引入 optional stopping。现有 60–120 月只是粗略 power range，不是完整 inferential contract。
- 依赖: AUD-02 factual baseline 与 AUD-03 validation terminology PASS；必须在任何 outcome-bearing
  E3 shadow reveal/IC/dashboard inspection 之前完成 owner decision。
- 允许修改: 可新增 `reports/audits/e3-equivalence-sequential-spec.md`（DRAFT decision brief）；
  本任务文件状态。owner 接受后另开任务写 ADR/config/pre-reg，不在本任务实施。
- 禁止修改: `docs/phase-*-preregistration.md`、`decisions/**`、源码/tests、ledger/results/forward artifacts、
  state headline；禁止读取 `runs/forward/**` outcome、运行 scoring/reveal、计算现有 phase 新指标。
- 前置条件: Researcher 只使用方法论文献、现有 frozen threshold 与**已公开** ledger facts；先声明
  `0.015 CI half-width` 不是自动等于 SESOI margin。owner 必须选择经济/研究上有意义的 `delta`。
- 实施要求:
  - 定义 estimand（monthly cross-sectional rank-IC differential）与四类 verdict：superiority、inferiority、
    practical equivalence、inconclusive；“fail to reject zero”不得写成 equivalence。
  - TOST 明列 `H01: Δ <= -delta`、`H02: Δ >= delta`、alpha、HAC/dependence treatment、最低 N、缺月规则；
    SESOI 要有领域/决策依据和 sensitivity range，不能从 observed effect 反推。
  - 比较至少两种 repeated-look 方案（预定 group-sequential alpha spending vs always-valid
    confidence sequence/e-process），推荐一种并冻结 look calendar、alpha family、early-stop/futility规则。
  - 规定多重性：方向双尾、TOST 两个单尾、phase/horizon/model family、任何新增 sequence 如何计数。
  - shadow visibility 明确：规格冻结前只看运行健康、schema/hash/availability，**不看 return、IC、CI、p**；
    若任何 outcome-bearing metric 已被看见，该月份只能保留 exploratory 且 headline 另起新 sequence。
  - 给出 effect-size/power 表只允许基于 pre-specified variance scenarios，不读取未公开 forward data。
  - 列出最终需写入 config/ledger schema 的字段，但本任务不得写 ledger 或点燃 sequence。
- 验收标准:
  - [ ] 草案完整覆盖 estimand、SESOI rationale/range、TOST hypotheses、alpha/dependence、look schedule、
    stopping/futility、multiplicity、missingness、shadow blinding、verdict wording、config fields。
  - [ ] 独立强模型 Reviewer 验证 TOST 方向、CI 等价关系与 sequential error control，无逻辑反转。
  - [ ] owner 对 SESOI、monitoring method、look schedule、shadow visibility 分别给出 GO/HOLD；缺一即 HOLD。
  - [ ] 没有 E3 outcome、forward artifact 或新 confirmatory statistic 被读取/生成。
  - [ ] frozen prereg/ADR/ledger diff 为空；文档显式标为 DRAFT、non-operative。
- 必须运行的测试: prose/formula independent review；`rg -n "SESOI|TOST|alpha|look|stopping|futility|missing|shadow|multiplicity" reports/audits/e3-equivalence-sequential-spec.md`；
  `uv run pytest -q`；`uv run ruff check`；`git diff --check`；frozen-file diff 必须为空。
- 失败处理: 无法就 SESOI 或 sequential method 达成可辩护决定时默认 HOLD headline；operational shadow
  必须 outcome-blind。不得沿用 naive repeated 95% CI 或 `ci_half < 0.015` 代替 equivalence test。
- 预期产物: 一份 DRAFT statistical decision brief + 明确 owner decision matrix；无代码、无新结果。
- 完成后需要更新: owner GO 后新建独立 implementation/freeze task；在此之前仅更新
  `state/current.md`、`state/handoff.md` 为 HOLD/decision pending。
- see: `docs/phase-e3-preregistration.md:57`、`:179`；`src/aionis/eval/forward_score.py:314`；
  `reports/TASK-STRAT-e2-e3-decision-brief.md:75`。
