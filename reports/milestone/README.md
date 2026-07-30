# reports/milestone/ — Milestone Audit Reports

One audit report per milestone. The **current** milestone snapshot lives at
`../docs/RESULTS.md`: four confirmatory nulls (B / C / D / E1), all
publishable-as-null (95% CI brackets 0, `ci_half < 0.015`).

This directory holds **future** milestone-audit reports — one file per milestone,
written at the close of each phase.

## Milestone-audit checklist (per milestone)

- [ ] 目标是否完成 (Were the objectives met?)
- [ ] 用户价值是否被验证 (Was the user value validated?)
- [ ] 架构是否仍适用 (Is the architecture still fit for purpose?)
- [ ] 质量指标 (Quality metrics — tests green, ruff clean, H6 deterministic)
- [ ] 成本 (Cost — tokens / compute / API)
- [ ] 技术债务 (Tech debt incurred or paid down)
- [ ] 风险 (Risks — leakage, reproducibility, scope creep)
- [ ] 决策: 继续 / 暂停 / 转向 / 停止 (Decision: continue / pause / pivot / stop)

## See also

- `../docs/RESULTS.md` — the current falsifiable-results snapshot
