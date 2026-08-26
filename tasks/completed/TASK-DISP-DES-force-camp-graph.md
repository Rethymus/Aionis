# TASK-DISP-DES — 势力阵营（force camp）血缘图谱：设计规格（纯设计，零代码）

**Lane**: display / design-only。**优先级**: P1（post-parity roadmap H5——参照站唯一未上线的 TODO 模块，
Aionis 第一个没有外部参照的原创模块）。
**授权**: 业主 2026-08-26 指令"将设计开发任务区分开来分配给不同 agents……授权直接新建任务并直接分配工作"。

## 0. 背景

`reports/design/2026-08-25-post-parity-roadmap.md` §3-H5：势力阵营 = 从既有面板派生的关系图谱
（13D/13G 联盟、13F 共同持仓、DEF14A 董事会网络）。数据大部分已在本仓 committed 面板中。
你负责把"它到底长什么样"设计清楚，产出两份文档。**你不写任何生产代码。**

## 1. 工作目录与边界

- 在 **主仓** `F:\ZCodeData\Aionis` 工作（其他 agent 在 worktree 写代码，与你零冲突）。
- 你只允许创建这两个文件：
  1. `reports/design/2026-08-26-force-camp-design.md` —— 设计规格
  2. `tasks/active/TASK-DISP-H5-lineage-build.md` —— 可直接派发的自包含构建任务规格
- 除读文件外不得修改任何代码/数据/配置。**0 ledger/frozen/config/prereg/OOS 接触。**
- 不跑任何网络抓取（设计所需数据全部在已提交面板 JSON 里）。

## 2. 设计输入（先读懂真实数据再设计——硬条件）

至少逐一实测读取以下真实 JSON 的形状（字段名、粒度、行数、覆盖率），设计必须引用实值：

- `web/src/data/aionis/form13f.json`（40 明星管理人 × positions ≤50 + changes）
- `web/src/data/aionis/def14a_persons.json`（104 份出名单 / 660 去重人物 / 董事会卡）
- `web/src/data/aionis/stakes_13g.json`（400 行可见窗口 + pct 状态）与 smart_money（13D lane）
- `web/src/data/aionis/companies_dir.json` 或 stock_universe（ticker↔名称映射源）
- `web/src/data/aionis/data_health.json`（rows/licensing 纪律）

注意路径可能是 `.ts` 数据模块（form13f.ts / filers13f.ts / stock-universe.ts 为独立模块不进 barrel）——
以实际文件为准。

## 3. 设计规格必须回答的问题（缺一退回）

1. **数据模型**：节点（人/机构/公司）、边（同持/共董/举牌联盟）各来自哪个面板哪个字段；
   join 键是什么；每类边的权重语义（禁止编造权重——计数型就明说计数）。
2. **采样与规模上限**：图谱节点全量还是 top-N？N 怎么选才诚实（披露选择口径，不凑数）？
   预估最终节点/边数量级。
3. **派生面板 schema**：`lineage_graph.json` 的完整字段级定义 + 导出函数名
   （照 export_form13f_stars 先例：导出时从已提交面板派生，零新抓取）+ 体积预算（KB 上限）+
   放共享 barrel 还是独立模块（结论必须引用 index.ts 单一 chunk 教训）。
4. **可视化形态决策**：力导向图 vs 弦图 vs 分层邻接表——给推荐 + 理由 + **表格回退态**
   （无障碍与移动端必须有非 canvas 回退）。考虑 recharts 已有依赖与"手写 squarified treemap"
   先例（不为一个模块引入重型图库的取舍要写明）。若推荐 SVG 力导向，说明是否手写模拟。
5. **交互层**：点击节点深链（/manager/[cik]、/stock/[ticker]、/executives 已有路由复用）、
   边筛选（按边类型）、空态列头先渲染（granularity 十模式之 P9）。
6. **诚实边界**：无价格无收益主张；共同持仓≠一致行动的法律措辞（照 party_index 的谨慎先例）；
   每类边的覆盖率与缺失如实披露（数据里没有的字段永远显示 "—"）。
7. **契约测试清单**：逐条列出 pytest 断言（形状/键集/覆盖率数学/禁编造守卫），照
   `tests/test_web_terminal_data.py` 现有风格写测试名与断言意图。
8. **实施阶梯**：S/M/L 切片，每片可独立验收；构建规格文件按切片给出精确到文件的改动清单。

## 4. 构建规格文件的要求

`tasks/active/TASK-DISP-H5-lineage-build.md` 要能被下一个 agent 不看本设计文档也能执行：
背景一段话 + 精确文件清单（新建/修改逐一列出）+ 导出/视图/测试/i18n（zh+en 键名逐个列出）+
验证命令全集（uv run pytest -q tests/test_web_terminal_data.py 等）+ 铁律（下节）全文复制。

## 5. 铁律（并入构建规格文件）

- 纯 display-lane：0 ledger/frozen/config/prereg/OOS；研究面零接触。
- 零新抓取（纯派生）；绝不编造边/权重/覆盖率。
- 数据模块体积纪律（独立模块不进 barrel）。
- zh/en i18n 双语键集必须对称。
- 完成定义 = 契约测试绿 + tsc 0 + eslint 净 + build 页数不减（build 由主线集成时统一跑）。

## 6. 交付报告格式

完成后报告：(a) 两份文档绝对路径；(b) 数据实测发现摘要（每个输入面板的真实形状一句话）；(c)
形态决策与一句理由；(d) 你建议的集成验收门。
