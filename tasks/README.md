# `tasks/` — 任务切片与记录规范

本目录存放 Aionis 的**任务记录**（tracked prose only，无密钥/数据/代码）。每条任务一个
markdown 文件，单目标、可独立回滚、可审计。

---

## 1. 任务大小分级（size tiers）

下发任务给 agent 前必须先判定大小；**L 禁止整体下发**。

### S — 小任务（单文件 / 极少文件，明确缺陷，无架构变更）
- 修复一个点击处理 / 加一道输入校验 / 改一个 API 字段 / 修一处 typo / 改一行配置。
- 单一目标，输入输出清晰，通常一个 context window 内完成。
- 可直接下发单个 executor。

### M — 中任务（一个完整子功能，多文件，需 unit + integration 测试）
- 实现 PDF 解析 fallback / 新增邻居查询接口 / 实现一组卡牌效果 / 落地一个 dashboard tab。
- 有明确的子功能边界与验收方法；需要拆 2–5 个原子步骤。
- 下发单个 executor，配合 TodoWrite 跟踪。

### L — 大任务（**必须进一步拆分，绝不整体下发给单个 agent**）
- 例：「构建整个后端」「重构整个项目」「实现完整 Phase E2」。
- 凡无法在一个 context window 内、由单一 agent 可靠完成的，都是 L。
- 处理方式：由 planner 拆成多个 M/S 子任务，再分别下发。

---

## 2. 任务文件字段模板（field headers，按此顺序，中文）

```markdown
# 标题

- 编号: <ID>
- 标题: <一句话标题>
- 状态: in progress | awaiting owner steer | completed | rejected | ...
- 目标: <本任务要达成什么>
- 背景: <为什么做、上下文、约束>
- 允许修改: <本任务可动的文件/模块白名单>
- 禁止修改: <绝不可动的文件/模块黑名单>
- 前置条件: <开工前必须已成立的条件>
- 实施要求: <必须遵守的实施纪律，如 H6 确定性、PIT、config 先于结果>
- 验收标准: <可证伪的 checklist，全部满足才算完成>
- 必须运行的测试: <验收前必须执行的命令与期望>
- 失败处理: <失败时的默认动作（如 default HOLD）>
- 预期产物: <产物路径与形态>
- 完成后需要更新: <收尾时要同步更新的索引/state/ADR>

- 结果: <已完成/否决时填，实际数字或 verdict>
- 理由: <否决时填，否决依据>
- see: <相关 ADR / 预注册 / 文档相对路径>
```

> completed / rejected 记录可省略与「实施」相关的字段，**必填**：标题 / 状态 / 目标 / 结果 /
> 理由（rejected）。in progress / awaiting 记录用完整模板（N/A 字段可省）。

---

## 3. 目录语义（folder semantics）

- `active/` — 进行中或待决策的任务（in progress / awaiting owner steer）。
- `completed/` — 已完成且**经验收**的任务（completed + verified）。
- `rejected/` — 经论证后**否决**的方案（含否决理由与替代方案）。

文件命名：`TASK-<DOMAIN>-<NN>-<slug>.md`（active/completed）或
`REJECT-<slug>.md`（rejected）。

---

## 4. 一条好任务的特征（definition of done）

- 单一目标（一个 task = 一件事）。
- 清晰的输入 / 输出 / 范围（允许修改 + 禁止修改白名单化）。
- 清晰的验收方法（可证伪 checklist + 必跑测试）。
- 可独立回滚（改一个 config = 新 ledger 行，绝不静默覆盖）。
- 理想情况下能在**一个 context window** 内由单一 agent 完成；不能 → 先拆。
