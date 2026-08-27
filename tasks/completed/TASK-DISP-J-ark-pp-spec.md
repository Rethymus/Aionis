# TASK-DISP-J — ARK ±pp 增量面板升级：条件触发式设计规格（纯设计，零代码）

**Lane**: display / design-only。**优先级**: P2（被 H1 刷新冻结门阻塞的**前瞻规格**——规格先行，
刷新恢复后一个小任务即可启用）。
**工作目录**: 主仓 `F:\ZCodeData\Aionis`。只创建一个文件：
`reports/design/2026-08-27-ark-pp-upgrade-spec.md`。零其他改动、零网络请求。

## 0. 背景（实测约束，必须写进规格）

post-parity roadmap §1 记录：ARK 面板目前只有当日快照（官方不留历史），±pp 变化依赖本地
日快照积累。**实测 data/cache/ark_holdings/ 现仅 8 个文件、全部停在 20260821** —— Actions
计费冻结（H1 业主门）使日更 lane 停摆，快照未继续积累。因此本规格是"条件触发式"：
全部内容以"当刷新恢复且快照 ≥N 个交易日"为前置，并写明启用判据与冻结期内的行为。

## 1. 规格必须回答（缺一退回）

1. **±pp 计算定义**：从两个日期的 per-fund CSV 快照计算每个持仓的权重百分点变化；
   快照对的选择规则（最新 vs 前一可用日，跳过缺失日如实披露）；新进/退出仓位的表示
   （new position / exited，绝不显示为 ±0.00）。
2. **数据结构**：`ark_history` 派生数据从哪来——现有 `data/cache/ark_holdings/*.csv`
   日期文件直接可用还是需要新索引文件；`export_ark` 升级还是新 `export_ark_momentum`
   函数；payload 预算与 barrel 纪律（独立模块）。
3. **前端形态**：/institutions ArkSection 基金卡升级（每持仓 ±pp 色条，涨跌色约定）+
   首页"ARK 基金仓位异动"卡从"基金共振排名"升级为"±pp top movers"的精确改动清单。
4. **触发判据（自动化友好）**：快照数 <N 时导出器行为 = 维持现状输出（诚实降级，不得
   空壳）；≥N 时自动输出增量字段；N 的推荐值（建议 5-10 个交易日）与理由。
5. **契约测试清单**：pp 数学自洽（w2−w1）、缺失日披露、无历史时零行为变化——测试名与断言意图。
6. **冻结期行为承诺**：本规格在 H1 解冻前**不改任何生产行为**；启用 = 后续一个小构建任务
   （列出该任务需要的输入）。
7. **依赖的现实文件**：`src/aionis/ingest/ark_holdings.py`、`scripts/ark_holdings_fetch.py`
   （快照落盘命名 `{TICK}_{YYYYMMDD}.csv`）、`export_ark`（grep 定位）、/institutions
   ArkSection 与首页 ARK 卡组件路径——全部先读再写。

## 2. 报告格式

(a) 文件路径；(b) 现状代码事实清单（每个引用文件一句话）；(c) 计算定义与 N 推荐一句话；
(d) 冻结期承诺确认。
