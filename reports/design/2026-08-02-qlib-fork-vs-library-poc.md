# qlib fork vs 纯 library 拼装 — 最小 POC 设计

> **日期**：2026-08-02
> **状态**：POC 设计文档（未执行，待 owner 裁断）
> **类型**：技术选型 POC 设计
> **约束**：只设计不执行；不触 ledger/冻结面/E3；无网络请求

---

## 1. 决策问题与背景

### 1.1 核心决策问题

轨道 B（v0.2 七主题选股平台）需要在「整项目脚手架」和「纯 library 拼装」之间做选择：

**选项 A**：fork `microsoft/qlib` 当脚手架，执行 4 个手术点
**选项 B**：纯 library 拼装（`bt` + `alphalens-reloaded` + `pyfolio-reloaded` + `purgedcv` + 现有 `src/aionis/` 模块）

### 1.2 背景

#### 来源文档
- `docs/quant-selection-research.md` v0.2 §6（层 0 整项目层 qlib + 4 改造点；层 1 library 层）
- `reports/design/2026-08-02-track-b-s0-s1-slice-plan.md` §7.2（已列出这个 owner 决策点）
- `reports/2026-08-02-strategic-review-coverage-and-alignment.md`（轨道 B 上下文）

#### qlib 的 4 个手术点（来自 v0.2 §6 层 0）

| 手术点 | 改造内容 | 泄漏风险 |
|---|---|---|
| **① dump_bin 钉 filed-date** | 用 `edgartools` as-filed 数据写入 qlib PIT-DB 二进制布局；时间戳钉 filed-date（非 period-end） | PIT-DB 保证算子层读不到未申报值 |
| **② ERL 挂 static field** | ERL structural-only 事件表挂申报日当 static field；key 在 filed-date → 不漏市场反应 | ERL 时间戳必须与 filed-date 对齐 |
| **③ DatasetH 注入 purgedcv 折** | 子类化 `qlib.data.dataset.DatasetH`，把默认纯时间 `segments` 换成 `purgedcv` 折索引；逐折训练 → 折级预测喂 HLN-DM/MBB | 必须用同一折生成器，避免折泄漏 |
| **④ RecordTemp 链插 ControlGateRecord** | `SignalRecord→SigAnaRecord→PortAnaRecord` 链插自定义 `ControlGateRecord`（neutral/shuffled + 确定性 + DSR/PBO） | 控制门必须真正起作用 |
| **致命陷阱** | `RobustZScoreNorm`/`CSZScoreNorm`/`Fillna` 的 `fit_start_time`/`fit_end_time` 必须钉在折内训练段 | 漏配 = 全面板 fit = **静默泄漏** |

#### 纯 library 拼装的零件清单（来自 v0.2 §6 层 1 + 现有模块）

| 角色 | 轮子 | 现有 Aionis 对应 |
|---|---|---|
| 回测（横截面） | `bt`（MIT） | 需新建 `src/aionis/track_b/bt_adapter.py` |
| 因子/IC 诊断 | `alphalens-reloaded` + `pyfolio-reloaded`（Apache） | 需新建 `src/aionis/track_b/alphalens_adapter.py` |
| CV + 多重检验 | `purgedcv`（MIT，eslazarev） | ✅ `eval/cv.py` 已封装 |
| PIT 基本面 | `edgartools`（MIT） | ✅ `ingest/fundamentals.py` 已用 |
| 价格数据 | Tiingo/Alpaca | ✅ `ingest/market.py` 已接 |
| PIT 对齐 | — | ✅ `features/alignment.py` 已有断言 |
| rank-IC 计算 | — | ✅ `eval/rank_ic.py` 已实现 |
| 学习器 | LightGBM（MIT） | ✅ `eval/learner.py` frozen |
| 控制门 | — | ✅ `eval/controls.py` 已有 neutral/shuffled |

### 1.3 决策重要性

这是轨道 B S0/S1 的**地基性选择**：
- 选 A（fork qlib）：获得统一 PIT-DB + Alpha158/360 特征库 + YAML 流，但承担 fork 维护成本 + 4 个手术点复杂度
- 选 B（纯 library）：保留轻量、避免 qlib 依赖，但需要手工拼装数据流 + 自建特征工程

**本轮只设计 POC，不执行。** 目标是设计一个 ≤2 天的 POC，低成本判定两条路真实工时与契合度。

---

## 2. 最小 POC 设计（≤2 天工作量）

### 2.1 POC 目标

用一个**最小可运行示例**，同时验证：
1. qlib fork 后 4 个手术点的真实工时
2. 纯 library 拼装达到同等能力的真实工时
3. 两条路在「反泄漏纪律契合度」上的实际体验

### 2.2 POC 约束

- **数据范围**：只用 10 只股票 × 3 个月（2024-01-01 ~ 2024-03-31）的 synthetic 数据
- **特征**：只用 5 个简单价格特征（momentum_5d/10d/21d、reversal、volatility）
- **标签**：forward_return_10d
- **CV**：PurgedGroupKFold(n_splits=3, group=month, embargo=5)
- **输出**：月度 rank-IC（3 个 IC 值）

### 2.3 POC-A：qlib fork 路线（预计 1 天）

#### 输入
- 10 只 ticker 的 synthetic 价格数据（已构造 DataFrame）
- 5 个价格特征（已计算）

#### 步骤
1. **clone qlib + 创建最小 fork**（0.5h）
   - `git clone https://github.com/microsoft/qlib.git`
   - 创建 `aionis_qlib` fork 目录
   - 移除 bundled Yahoo 数据

2. **手术点 ①：dump_bin 钉 filed-date**（2h）
   - 用 synthetic 数据写最小 `dump_bin` 脚本
   - 验证生成的 `.bin` 文件时间戳正确
   - **验收**：能从二进制文件读回 synthetic 数据，时间戳一致

3. **手术点 ③：DatasetH 注入 purgedcv 折**（3h）
   - 子类化 `qlib.data.dataset.DatasetH`
   - 把 `segments` 换成 purgedcv 生成的折索引
   - 验证每折训练段不包含测试段数据
   - **验收**：打印折边界，确认无时间泄漏

4. **跑通 Alpha158 链**（2h，跳过 ①②④ 的完整实现）
   - 用 qlib 内置 Alpha158 特征（不完全改造，只验证数据流）
   - 跑一次训练 + IC 输出
   - **验收**：输出 3 个 rank-IC 值

#### 产出
- `poc/qlib_fork/` 目录：最小 qlib fork 代码
- `poc/qlib_fork/NOTE.md`：4 个手术点的实际工时记录
- `poc/qlib_fork/ic_output.json`：3 个 IC 值

#### 判定标准
- **能跑通**：成功输出 IC 值
- **工时记录**：每个手术点的实际耗时
- **泄漏检查**：折边界无时间重叠

### 2.4 POC-B：纯 library 拼装路线（预计 1 天）

#### 输入
- 同样的 10 只 synthetic 价格数据
- 同样的 5 个价格特征

#### 步骤
1. **用 `purgedcv` 生成折**（0.5h）
   - 复用 `eval/cv.py` 的 `PurgedGroupKFold`
   - 生成 3 折索引
   - **验收**：打印折边界，确认无时间泄漏

2. **用 LightGBM 训练**（1.5h）
   - 复用 `eval/learner.py`
   - 逐折训练，输出预测分数
   - **验收**：输出 3 个折的预测结果

3. **用 `alphalens-reloaded` 计算 IC**（2h）
   - 安装 `alphalens-reloaded`
   - 写最小 adapter：格式化数据 → `factor_data` / `prices`
   - 跑 `create_summary_tear_sheet`
   - **验收**：输出 3 个 IC 值

4. **用 `bt` 回测分位数组合**（2h）
   - 安装 `bt`
   - 写最小 adapter：根据预测分数构建 top/bottom 分位数组合
   - 跑一次再平衡回测
   - **验收**：输出组合收益序列

#### 产出
- `poc/library拼装/` 目录：最小拼装代码
- `poc/library拼装/NOTE.md`：每个零件的实际工时记录
- `poc/library拼装/ic_output.json`：3 个 IC 值

#### 判定标准
- **能跑通**：成功输出 IC 值
- **工时记录**：每个零件的实际耗时
- **复用度**：现有 Aionis 模块复用比例

### 2.5 POC 执行计划（总计 2 天）

| 任务 | POC-A | POC-B | 责任 |
|---|---|---|---|
| Day 1 上午 | clone qlib + 手术点① | purgedcv 折 + LightGBM | Engineer A |
| Day 1 下午 | 手术点③（核心） | alphalens IC 计算 | Engineer A |
| Day 2 上午 | Alpha158 链跑通 | bt 回测 | Engineer A |
| Day 2 下午 | 整理工时记录 + 对比表 | 整理工时记录 + 对比表 | Verifier |

### 2.6 POC 验收标准（双轨必须同时满足）

| 标准 | 阈值 |
|---|---|
| **功能完整性** | 两条路都输出 3 个 IC 值 |
| **工时记录** | 每个步骤记录实际耗时（精确到 0.5h） |
| **泄漏检查** | 折边界无时间重叠（断言测试） |
| **复用度** | POC-B 标注现有模块复用比例 |
| **判定表** | 输出工时/风险/契合度三列对比表 |

---

## 3. 两条路的工时/风险/契合度对照表（预测版，POC 后更新）

### 3.1 工时对照（S0/S1 全量，非 POC）

| 维度 | qlib fork（A） | 纯 library 拼装（B） | 备注 |
|---|---|---|---|
| **数据 ingest** | 8h（替换 bundled 数据源） | 4h（复用 `ingest/market.py` + `fundamentals.py`） | B 有先发优势 |
| **PIT 对齐** | 12h（适配 qlib PIT-DB） | 8h（复用 `features/alignment.py`） | B 有先发优势 |
| **特征工程** | 6h（Alpha158 开箱即用） | 16h（需手写价格特征 + 量价特征） | A 有先发优势 |
| **CV 训练** | 12h（手术点③ DatasetH） | 6h（复用 `eval/cv.py` + `learner.py`） | B 有先发优势 |
| **IC/回测** | 8h（手术点④ RecordTemp） | 12h（挂 alphalens + bt） | A 有先发优势 |
| **控制门** | 6h（手术点② ERL 挂） | 4h（复用 `eval/controls.py`） | B 有先发优势 |
| **调试验证** | 16h（qlib 复杂度高） | 8h（模块独立易调试） | B 有先发优势 |
| **总计** | **68h** | **58h** | B 略优，但 A 在特征工程有长期优势 |

### 3.2 风险对照

| 风险 | qlib fork（A） | 纯 library 拼装（B） | 缓解 |
|---|---|---|---|
| **fork 维护成本** | 高：qlib 更新需 rebase | 低：library 独立升级 | A 需 pin qlib 版本 |
| **PIT 泄漏风险** | 中：PIT-DB 架构安全，但需验证手术点 | 高：手工拼装易错 | A 架构更安全 |
| **调试复杂度** | 高：qlib 内部模块耦合多 | 低：模块独立易调试 | B 更透明 |
| **升级路径** | 中：qlib 社区活跃（46.9k★） | 高：各 library 独立升级 | A 依赖单点 |
| **License 风险** | 低：qlib MIT | 低：全部 permissive | 两者无差异 |
| **学习曲线** | 高：需理解 qlib 架构 | 中：library 文档独立 | B 更友好 |
| **与现有代码契合** | 低：需大改现有模块 | 高：复用现有 `eval/` | B 有先发优势 |

### 3.3 契合度对照（反泄漏纪律）

| 维度 | qlib fork（A） | 纯 library 拼装（B） | 判定 |
|---|---|---|---|
| **PIT 纪律** | PIT-DB 架构级保证 | 需手工维护断言 | A 更优 |
| **purged CV** | 手术点③需改造 | 已有 `eval/cv.py` 封装 | B 更优 |
| **控制门** | 手术点②/④需改造 | 已有 `eval/controls.py` | B 更优 |
| **确定性** | qlib 有随机性（需钉 seed） | 已有 H6 确定性测试 | B 更优 |
| **config-before-result** | 需适配 qlib config | 已有 `runs/ledger.jsonl` | B 更优 |
| **整体契合** | **中**（架构优但改造多） | **高**（复用现有纪律） | B 更优 |

---

## 4. 建议的判定规则（POC 满足什么条件选哪条路）

### 4.1 选 qlib fork（A）的条件（满足 **2 条以上**）

1. **工时阈值**：POC-A 总工时 ≤ POC-B × 1.2（允许 20% 的长期收益溢价）
2. **特征工程优势**：Alpha158/360 的特征覆盖度显著 > 手工特征（POC 后评估）
3. **PIT 安全性**：POC 证明 PIT-DB 架构显著降低泄漏风险（需通过审计）
4. **长期维护性**：qlib 社区活跃度 > 预期（46.9k★ 已验证）

**一句话判定**：如果 POC 证明 qlib fork 的工时溢价 ≤ 20% 且 PIT 安全性显著更优，选 A。

### 4.2 选纯 library 拼装（B）的条件（满足 **2 条以上**）

1. **工时阈值**：POC-B 总工时 < POC-A × 0.8（B 有明显优势）
2. **现有模块复用度**：> 60% 的现有 `eval/` 模块可直接复用
3. **调试透明度**：POC 证明 B 的调试复杂度显著低于 A
4. **反泄漏契合度**：现有纪律（purgedcv / 控制门 / ledger）零改造即可用

**一句话判定**：如果 POC 证明 library 拼装的工时优势 > 20% 且现有模块复用度 > 60%，选 B。

### 4.3 判定规则简化表

| 指标 | 选 A（qlib fork） | 选 B（library 拼装） |
|---|---|---|
| **工时** | POC-A ≤ 1.2 × POC-B | POC-B < 0.8 × POC-A |
| **特征** | Alpha158/360 显著更优 | 手工特征够用 |
| **复用** | — | 现有模块复用度 > 60% |
| **PIT 安全** | PIT-DB 显著更安全 | 手工断言够用 |
| **维护** | qlib 活跃度可持续 | library 独立升级 |
| **反泄漏** | 改造后契合 | 现有纪律零改造 |

---

## 5. 需 owner 裁断的点

### 5.1 预算与时间

**问题**：轨道 B S0/S1 的总工时预算是多少？
- **选项 A**：> 80h（允许 qlib fork 的溢价）
- **选项 B**：< 60h（要求 library 拼装的高效）

**建议**：等 POC 实际工时数据再裁断。

### 5.2 长期维护意愿

**问题**：是否愿意承担 qlib fork 的长期维护成本？
- **选项 A**：愿意（如果 qlib 提供显著长期收益）
- **选项 B**：不愿意（优先轻量和透明）

**建议**：如果 POC 证明 B 的工时优势 > 20%，倾向 B。

### 5.3 特征工程优先级

**问题**：Alpha158/360 特征库的优先级有多高？
- **选项 A**：高（选股的核心竞争力，值得为此 fork）
- **选项 B**：中/低（手工特征 + 后期迭代够用）

**建议**：如果 POC 证明手工特征能覆盖 S0/S1 的 80% 需求，倾向 B。

### 5.4 反泄漏纪律优先级

**问题**：PIT 纪律的架构级保证有多重要？
- **选项 A**：关键（qlib PIT-DB 是不可妥协的优势）
- **选项 B**：重要但不必须（手工断言够用）

**建议**：如果 POC 证明 B 的断言测试覆盖所有泄漏路径，选 B。

### 5.5 最终判定流程

```
Step 1: POC 执行 → 获得实际工时 + 风险评估
Step 2: 填写判定表（工时/风险/契合度三列）
Step 3: 应用判定规则（§4.1/4.2）
Step 4: Owner 裁断 §5.1-5.4 四个优先级问题
Step 5: 输出最终决策 + 冻结到 `decisions/ADR-XXX-qlib-vs-library.md`
```

---

## 6. 附录：待 POC 验证的问题清单

| 问题 | qlib fork | library 拼装 | 验证方式 |
|---|---|---|---|
| dump_bin 实际工时 | 预估 2h | — | POC-A Step 2 |
| DatasetH 改造工时 | 预估 3h | — | POC-A Step 3 |
| alphalens 接入工时 | — | 预估 2h | POC-B Step 3 |
| bt 回测接入工时 | — | 预估 2h | POC-B Step 4 |
| PIT-DB vs 手工断言安全差 | 待验证 | 待验证 | 泄漏审计 |
| 现有模块复用度 | ~30% | ~70% | 代码清单 |
| 长期维护成本 | 待评估 | 待评估 | 社区活跃度追踪 |

---

## 7. 不越界声明

- `[F]` 本设计文档**未运行任何 confirmatory/strategy/horizon/forward 脚本、未观察任何 outcome、未改任何冻结面或 ledger**。
- `[I]` 本 POC 设计是研究建议；owner 未裁决前，不构成技术选型决策。
- `[F]` 本轮只设计 POC，不执行 POC（不写代码、不 clone qlib、不运行任何脚本、不做网络请求）。
- `[F]` POC 执行后，任何轨道 B 的落地都是**新预注册 + 新 config + 新 ledger row**，绝不静默修改 B/C/D/E1。

---

**文档结束**
