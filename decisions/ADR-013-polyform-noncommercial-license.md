# ADR-013: Aionis 自身代码许可由 MIT 变更为 PolyForm-Noncommercial-1.0.0（仅限非商用）

**Status**: ACCEPTED (owner decision, 2026-09-09)
**Date**: 2026-09-09
**Supersedes**: 部分 ADR-007（ADR-007 管**入栈物**须宽松许可，该原则不变；本 ADR 只改**自有代码**的对外处分）

## Background（业主诉求）

- Aionis 是公开仓库（GitHub Pages 终端 + README 展示）。MIT 允许任何人**商用、转售、
  闭源包装**；若被有心人包装成"AI 选股神器"卖给对金融一窍不通的普通人，MIT 授权下
  **无追责抓手**——这正是业主明确要防的场景（2026-09-09 业主指令原话：很可能被拿出去
  包装卖给对金融一窍不通的普通人，造成极其恶劣的影响；不授权才能在事后追责挽回、
  避免更多人上当）。
- 触发契机：README 许可一致性核查（同日）发现 README ⑧ 窄化了白名单的 8 类 ACCEPTED，
  顺带把"项目自身该用什么许可"摆上了台面。

## Candidates considered

| 候选 | 结论 |
|---|---|
| **PolyForm-Noncommercial-1.0.0**（SPDX 收录） | ✅ **采纳**。专为软件设计的"仅限非商用"标准许可：个人学习/研究/实验、非营利组织、政府与教育机构可用；一切商业目的需另行授权。未授权商用 = 明确违约/侵权 → 下架通知与索赔的法律抓手。 |
| AGPL-3.0-only | ❌ 不禁止"出售"本身（只强制售卖者开源），防不住包装转售场景；且与本项目白名单对 AGPL 的拒收立场互别扭。 |
| CC-BY-NC-SA-4.0 | ❌ CC 官方不建议用于软件（无源码/专利条款）；且是本项目白名单 REJECTED 表中的类型。 |
| MIT + 禁售附加条款（Commons Clause 式） | ❌ 正是本项目拒绝 vectorbt 的许可形态，与自身立场冲突；自定义条款判例少、执行不确定性高。 |

## Chosen（已实施，2026-09-09）

- `LICENSE` = 版权行（Copyright 2026 The Aionis Authors）+ PolyForm Noncommercial 1.0.0
  官方原文（逐字取自 polyformproject 官方仓库）。
- `pyproject.toml:7` → `license = { text = "PolyForm-Noncommercial-1.0.0" }`；
  `CITATION.cff` → `license: PolyForm-Noncommercial-1.0.0`。
- 双语 README ⑫ 与页脚、web 终端 shelf 页 i18n（zh/en）与相关代码注释同步改称
  PolyForm-NC；`docs/data-license-allowlist.md` 升 v0.2（锚点原则改为"自有代码
  PolyForm-NC，入栈物仍须 MIT-compatible"，CC-BY-NC 拒收理由同步改写）。

## Evidence / 边界与诚实披露

1. **不可撤回的既有授权**：2026-09-09 之前已按 MIT 获取副本者，其 MIT 授权不可撤回
   （MIT 授予是永久的）。本变更只约束**未来**获取者。项目公开时间短、无已知下游
   分发者，实际暴露有限。
2. **入栈物策略不变**：依赖/数据仍只收 MIT-compatible 宽松许可（ADR-007 与白名单
   ACCEPTED 列不变）——宽松许可允许合法并入非商用项目，法律栈自洽（MIT 依赖保持
   MIT 并保留声明，Aionis 自有文件按 PolyForm-NC 分发）。
3. **许可不是护身符**：骗子本就违法。PolyForm-NC 提供的是**合同/版权违约的明确
   请求权基础**（停止使用、下架、损害赔偿），不等于免疫；配合免责声明与（如需要）
   商标保护共同使用。
4. **非 OSI**：PolyForm-NC 不是 OSI 认证的开源许可。本项目定位为研究展示项目，
   业主明确接受该代价以换取禁商用授权。
5. GitHub 许可识别：licensee 支持 PolyForm 家族，仓库侧栏将正确显示。

## Cost

- 失去"一键商用"的友善度；公司内部研究使用（营利实体）技术上需另行授权——按
  业主意图这正是要收紧的范围。
- 未来若想商业化或再转回宽松许可，由版权持有人（The Aionis Authors / 业主）再行
  决定即可（自有版权可随时对后续版本改许可；已发布版本按其发布时许可）。

## Applicability bounds

- 只约束**代码仓库**（`src/`、`scripts/`、`dashboard/`、`web/`、`workers/` 等自有代码）。
- 第三方数据源许可照旧走 `docs/data-license-allowlist.md`（数据本身的权利属于数据方）。
- 文档（docs/、decisions/）作为代码仓库的组成部分随仓库许可分发。

## Re-evaluation trigger

- 出现诚实的非商用机构（大学/公益研究方）被许可条款误伤、且业主认为值得放开；
- 或项目决定正式商业化（届时按商业模式重选许可）；
- 或法律顾问对 PolyForm-NC 在目标司法辖区的可执行性提出实质异议。
