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

---

## 5. 任务规格静态检查（Task Contract Linter）

`scripts/check_task_contracts.py` 是一个确定性的任务规格静态检查器，用于验证 active task 的必填字段、Size=L 禁止下发、owner gate 与危险命令声明。

### 用法

```bash
# 检查所有 active tasks
uv run python scripts/check_task_contracts.py tasks/active

# 指定其他目录
uv run python scripts/check_task_contracts.py tasks/completed
```

### 输出格式

每行一个 finding，格式：`{reason_code}|{task_file}|{detail}`

输出按文件路径和 reason code **确定性地排序**，同一文件多次运行结果一致。

### Reason Codes

- `MISSING_REQUIRED_FIELD:{field_name}` — 缺少必填字段
- `SIZE_L_FORBIDDEN` — Size = L（禁止整体下发）
- `OWNER_GATE_DECLARED` — 状态包含 owner-gate 关键词（需 owner 授权）
- `DANGEROUS_COMMAND_DECLARED` — 禁止修改部分包含危险命令（如 phase_/strategy_/horizon_/forward_ 脚本）
- `PARSE_ERROR` — 无法解析文件

### 必填字段

以下字段必须在任务文件中声明（按任务模板约定）：

- `编号` — 任务 ID（如 RD-01, RES-01, AUD-00）
- `标题` — 一句话标题
- `状态` — in progress / owner-gated / completed / rejected / awaiting 等
- `Priority` — P0 / P1 / P2
- `Size` — S / M / L（L 禁止整体下发）
- `Risk` — LOW / MEDIUM / HIGH / CRITICAL
- `目标` — 本任务要达成什么
- `允许修改` — 本任务可动的文件/模块白名单
- `禁止修改` — 绝不可动的文件/模块黑名单
- `前置条件` — 开工前必须已成立的条件
- `验收标准` — 可证伪的 checklist
- `必须运行的测试` — 验收前必须执行的命令

### 设计原则

- **仅解析 Markdown**：不执行任何代码、不调用网络、不修改现有任务文件
- **确定性输出**：同一文件多次运行结果完全一致（H6 确定性）
- **历史任务有 findings 是预期输出**：本工具报告缺陷，不自动修复
- **运行在真实 corpus 上不能崩溃**：parse error 是唯一的失败模式

### 测试

```bash
# 运行测试套件（使用 synthetic fixtures）
uv run pytest -q tests/test_task_contracts.py

# 代码检查
uv run ruff check scripts/check_task_contracts.py tests/test_task_contracts.py
```
