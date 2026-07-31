# reports/milestone/ — Milestone Audit Reports

One audit report per milestone. The **current** milestone snapshot lives at
`../../docs/RESULTS.md`: four historical purged cross-fitted/OOF differentials
(B/C/D/E1) show no significant positive increment under the frozen implementation.
Phase B has no recorded paired CI, so no four-phase precision/equivalence claim is valid.

This directory holds **future** milestone-audit reports — one file per milestone,
written at the close of each phase.

## Milestone-audit checklist (per milestone)

- [ ] 目标是否完成 (Were the objectives met?)
- [ ] 用户价值是否被验证 (Was the user value validated?)
- [ ] 架构是否仍适用 (Is the architecture still fit for purpose?)
- [ ] 质量指标 (Quality metrics — exact command, date, exit status, test count, H6 scope)
- [ ] 成本 (Cost — separate logged tokens, estimates, paid API, compute, and human review)
- [ ] 验证语义 (Validation kind — cross-fitted/OOF vs strictly chronological vs live)
- [ ] 经济边界 (Gross/net, turnover, execution, slippage, borrow, delisting, capacity)
- [ ] LLM 归因 (Which headline features actually use an LLM; zero-LLM ablation if applicable)
- [ ] 技术债务 (Tech debt incurred or paid down)
- [ ] 风险 (Risks — leakage, reproducibility, scope creep)
- [ ] 决策: 继续 / 暂停 / 转向 / 停止 (Decision: continue / pause / pivot / stop)

## See also

- `../../docs/RESULTS.md` — the current falsifiable-results snapshot
- `../audits/claim-reconciliation.md` — public-claim evidence table
