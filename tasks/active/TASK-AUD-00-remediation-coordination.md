# AUD-00 — Audit remediation coordination (coordination only)

- 编号: AUD-00
- 标题: Coordinate the repository-audit remediation without changing research outcomes.
- 状态: **in progress — coordination only; DO NOT dispatch as one task**
- Priority: **P0**
- Size: **L — MUST remain decomposed; L is forbidden from assignment to any single agent**
- Risk: **HIGH**（涉及公开研究结论、验证语义与 E3 不可逆前向序列）
- 建议 agent role / model tier: **Orchestrator + Planner / strong**；子任务各自使用其文件所列角色。
- 目标: 只协调 AUD-01…AUD-07 的顺序、owner gates、Verifier/Reviewer 证据与停止条件；
  本任务本身不实现代码、改结论或运行研究。
- 背景: 2026-07-31 只读审计发现公开 factual claims、chronological OOS 术语、来源/礼貌合同、
  E3 live-input readiness、测试入口以及等效性/序贯监测门均有待整改。整改不能倒推出或重算任何
  confirmatory 结果，也不能污染 E3 首次前向序列。
- 依赖: 无；它是协调节点，不是执行节点。
- 允许修改: 本任务文件中的子任务状态/证据链接；经 owner 指派后由 Orchestrator 更新
  `state/current.md`、`state/handoff.md`。不得借本任务直接修改子任务白名单外文件。
- 禁止修改: `runs/ledger.jsonl`、`runs/results/**`、`runs/forward/**`、`data/**`、
  `docs/phase-*-preregistration.md`、任何 frozen config/ADR；禁止运行 phase/strategy/horizon/
  forward commit/reveal 脚本；禁止观察、推导或生成新 confirmatory 指标。
- 前置条件: owner 明确选择要启动的**单个** S/M 子任务；未选择时默认 HOLD。
- 实施要求:
  - 一次只下发一个相互冲突的写任务；AUD-04 与 AUD-05 可在文件不重叠时并行研究，但落地需串行 review。
  - 每个子任务必须独立 Engineer → Verifier → Reviewer；最多两轮修复，之后 BLOCKED。
  - **任何新 confirmatory rerun、新 pre-registration、已冻结规格变更或 E3 headline ignition，均须单独
    owner gate；本总控任务不授予该权限。**
  - exploratory shadow 在 AUD-07 冻结可见性/序贯规则前不得观察 outcome-bearing 指标。

## 依赖图 / 执行顺序

```text
AUD-01 test entrypoint
├── AUD-02 factual claims
├── AUD-03 chronological validation contract ──> AUD-02 final terminology
└── AUD-04 approved-source contract ──> AUD-05 politeness contract ──> AUD-06 E3 live-input readiness
AUD-02 + AUD-03 ─────────────────────────> AUD-07 SESOI/TOST + sequential gate
AUD-06 + AUD-07 + owner GO ──────────────> existing E3 Slice 6/7; shadow only
existing E3 Slice 6/7 + separate owner GO ─> headline ignition
```

- 验收标准:
  - [ ] AUD-01…AUD-07 各自有独立 PASS 证据和 Reviewer APPROVE，或被明确标为 BLOCKED/REJECTED。
  - [ ] `git diff` 证明 frozen prereg、ledger、既有 result artifacts 未被整改改写。
  - [ ] 没有以此次审计为理由启动任何 confirmatory rerun、生成新 pre-reg 或点燃 E3 headline。
  - [ ] 所有公开状态只引用真实命令输出；失败不得改写成 PASS。
- 必须运行的测试: 本任务不直接运行测试；收集各子任务规定命令、Verifier verdict、Reviewer verdict；
  最终只读检查 `git diff --name-only`、`git diff -- runs/ledger.jsonl docs/phase-*-preregistration.md`。
- 失败处理: 任一高风险门失败即 HOLD 其下游；同一问题两轮未通过则 BLOCKED 并交 owner，禁止无限修复。
- 预期产物: AUD-01…AUD-07 的完成/阻塞矩阵与 owner-gate 记录；不产生研究结果。
- 完成后需要更新: `state/current.md`、`state/handoff.md`；任务完成后移入 `tasks/completed/`。
- see: `WORKFLOW.md` §7–§11；`tasks/README.md`；`tasks/active/TASK-E3-launch.md`。

## Initial agent dispatch (2026-07-31)

| Role | Scope | Status |
|---|---|---|
| Researcher | `reports/audits/2026-07-31-quant-llm-research-audit.md` + audit index | completed; evidence-only |
| Planner | AUD-00…AUD-07 task slices + backlog routing | completed; no implementation |
| Engineer | AUD-01 test entrypoint | completed; one-line pytest configuration change |
| Verifier | AUD-01 acceptance commands | PASS: 576 passed, 0 skipped; ruff clean |
| Reviewer | AUD-01 task boundary + diff | APPROVE; AUD-01 completion gate closed |
| Researcher/Planner | AUD-03 chronology preflight | completed read-only; implementation contract recorded |
| Researcher/Planner | AUD-04/05 source/politeness preflight | completed read-only; AUD-05 requires reslicing |
| Planner | AUD-05A/B/C task boundaries | completed read-only; strict AUD-04 → 05A → 05B → 05C order |
| Planner | AUD-06 owner decision packet | completed read-only; no forward/outcome action authorized |
| Engineer/Verifier/Reviewer | AUD-03 chronology contract | COMPLETE: repair round 1 re-Verifier PASS / Reviewer APPROVE |
| Engineer/Verifier/Reviewer | AUD-04 source allowlist | COMPLETE: repair round 1 re-Verifier PASS / Reviewer APPROVE |
| Documentation Engineer | AUD-02 factual claims | dispatched after AUD-03 APPROVE; state files reserved to Orchestrator |
| Planner | AUD-05A policy primitive | materialized as P0/S; 05B/05C remain dependency-held |

More agents are permitted only for context-isolated execution and independent verification. They do not
authorize additional factors, model searches, outcome inspection, frozen-config changes, or E3 ignition.
