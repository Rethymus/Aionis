# 势力阵营（force camp）血缘图谱 — 设计规格（TASK-DISP-DES，纯设计零代码）

> Lane: display / design-only。post-parity roadmap **H5**（`reports/design/2026-08-25-post-parity-roadmap.md`
> §3-H5）：参照站导航里写了"即将上线"却从未上线的模块，也是 Aionis 第一个没有外部参照的原创模块。
> 本文所有数据论断均来自 2026-08-26 对 `web/src/data/aionis/` 已提交面板的逐一实测（快照
> snapshot_ts 均为 2026-08-25）；实施规格见姊妹文件 `tasks/active/TASK-DISP-H5-lineage-build.md`。
>
> **一处勘误**：授权任务里写的导出端路径 `src/aionis/reporting/export_terminal_data.py` 不存在；
> 导出端的真实位置是 **`scripts/export_terminal_data.py`**（5757 行，`export_form13f_stars` /
> `export_party_index` 都在其中）。`.ts` 数据模块头部注释里的契约引用也指向该路径。

---

## 0. 一句话结论

三类诚实的关系边全部可以从**已提交面板**派生，无需任何新抓取：机构共同持仓（13F，
636 对）、人物共席（DEF 14A，68 对）、同目标申报聚集（13D/13G，53 对）；实体节点数百量级，
一张手写 SVG 力导向图 + 常驻表格回退态即可承载，无需引入任何图库。**最大的一条诚实红线**：
已提交面板中 13D/13G 的联合申报没有按成员拆解（实测 520 行内每条 doc_url 唯一）——所以
本模块的第三类边只能叫"同目标聚集"，**绝不能叫"举牌联盟/一致行动"**。

## 1. 设计输入实录（硬条件：先读懂真实数据）

### 1.1 六个输入面板实测（快照 2026-08-25）

| 面板 | 实测形状（关键值均为实查） |
|---|---|
| `form13f.json` (638KB) | `status ok`, `as_of=2026-06-30`；`managers[40]`，字段 `{cik,name,zh_name,category,quarter,filed,n_positions,total_value,positions,changes}`。**全书规模 vs 可见切片**：`n_positions` 真实 8–13,575（Citadel 13,575 只占位），但 `positions[]` 导出上限 ≤50（最小 8 条）、`changes[]` 8–20 条（合计 738 行，其中 527 行带 ticker）。持仓行 `{cusip,issuer,title,option,value,shares,pct,ticker}`，**ticker 可为 null**（需 cusip 兜底）；change 行另有 `direction ∈ {new,increased,reduced,exited}, delta_pct, delta_value`。`ticker_coverage="1181/1580"`；`category_counts`: quant 6 / value 9 / other 2 / activist 6 / growth 8 / macro 5 / china_background 4。可见切片去重后 **808 个持仓键**（ticker 或 cusip 兜底）。契约在独立模块 `form13f.ts`（注释自述 ~650KB、不进 barrel）。 |
| `def14a_persons.json` (49KB) | 150 份流处理 / **104 份出名单** / 覆盖率 69.3% / 上游去重 **660 人**，但提交面板**只导出 `top_persons[:50]`**（多席优先）。top_person 行 `{name,roles[],n_companies,n_director_seats,companies[](≤10)}`；top-50 中 **23 人跨 ≥2 家公司**，产生 **76 条人企双部关系**。`boards[104]`（issuer_cik 104/104、ticker 85/104）。**join 命中率极好**：top_person 的 41 个公司名串与 `boards[].company` 精确匹配 **41/41**，其中 38/41 带 ticker。`by_role` 最高 director=498；`confidence`: age_rows 79 / name_roles 25 / unparsed 43 / errors 3（诚实分层已在面板内披露）。 |
| `stakes_13g.json` (144KB) | `total=15,982`（SC 13G 7,419 + SC 13G/A 8,563）；可见 `filings[400]`。⚠️ 声明窗口 ~120 天（window.start=2026-04-27），但 400 行实际日期只有 **2026-08-14 → 08-21 约 7 天**——排最前的周切片，派生时必须按可见日期如实标注。行 `{date,doc_url,filer,form,pct_now,pct_prev,pct_status,target,ticker}`；ticker 366/400；`pct_status`: null 360 / exited 9 / below_5 31。distinct target 332；**≥2 个不同 filer 的 target 19 个**；**520 行内 doc_url 零共享** ⇒ 联合申报未被拆解成成员对。 |
| `smart_money.json` (48KB) | 13D lane：`recent_filings[120]`（日期 **2026-08-17 → 08-21，仅 5 个交易日**）、`active_filers[10]`、`yearly[12]`（2015–2026，年笔数 319–522）、`total_filings=12,744 / n_filers=3,071`。distinct target 93，**≥2 filer 的 target 12 个**；同样 **url 零共享**。filer 字段可能是自然人名（实例：Brera Holdings PLC ← Almheiri Alyazi / Maimon Keren Kalima / Sade Ron）⇒ 第三类边的节点多数不是受策展机构。 |
| `companies_dir.json` (824KB) + `stock_universe.json` (580KB) | 均以独立 `.ts` 模块形态在场（`companies-dir.ts` {ticker,name}×10,387；`stock-universe.ts` 1,421 stocks 含 frozen score 序列）。全图谱 ticker 并集实测 **1,015** 个，落在 `stock_universe`（可路由 `/stock/[ticker]`）内的只有 **227** ⇒ 深链必须门控。 |
| `data_health.json` (12KB) | `panels[48]`，每行 `{key,file,category(frozen/daily/cadence),present,rows,as_of,exported_at}`；`source_health` 含 smart_money/stakes_13g 子计数；`planned[]`。`party_index` 以 category=`daily` 注册——lineage_graph 应同法注册。 |

### 1.2 派生先例（导出端，`scripts/export_terminal_data.py`）

- **`export_form13f_stars`（L3545）**："derived from the COMMITTED form13f.json at export time
  (idempotent, zero network, zero parquet deps)"——首页只付 2KB digest、不背 650KB 全书。这就是
  lineage_graph 的模板：**从已提交面板在导出期派生，零抓取零 parquet 依赖**。
- **`export_party_index`（L4783）**：明确"reads the committed politician_trades_tx.json payload
  …(never the gitignored cache parquet)"；methodology 写下"dollar-weighting would be fabricated
  precision""no prices, no returns, no performance claim"。措辞基调逐句继承。
- `_dh_read(name)` + `_skip_retain(panel, reason)`：输入缺失时不产出空壳，保留上一提交值。
- `export_def14a_persons`（L3925）的上游缓存里有完整 660 人 seats 明细，但其导出物只交了 top50——
  本设计**严守"从已提交面板派生"边界，不回头消费 gitignored 缓存**；全 660 人扩容属上游
  结构升级，另立任务，不在 v1。

### 1.3 前端资产

`heatmap-view.tsx` 手写 squarified treemap（Bruls/Dik/Huizing，注释原文 "Hand-rolled layout
(no new deps): deterministic SSR-friendly divs"）；`lib/format.ts` 五件套（fmtUsd/fmtShares/
fmtInt/fmtDateShort/fmtEmpty"—"）；`@/i18n/provider` 的 `useI18n` + `dict.ts`（zh L4–1202 /
en L1203–2312 对称）；依赖表仅 recharts 3.8.0（图表库，无非网格图能力）；包管理器 pnpm
（pnpm-lock.yaml）。40 条路由中没有 force-camp。

## 2. 数据模型（问题 §3-1）

四类节点、三类边，一切取自既有面板既有字段；权重一律**整数计数**，不发明相似度分数。

### 2.1 节点

| 类型 | 来源面板与字段 | 键（join 键） | 实测规模 | 诚实注记 |
|---|---|---|---|---|
| `institution` 机构 | form13f.managers{cik,name,zh_name,category,total_value} | 10 位零填充 CIK | 40（全部策展管理人） | category 是编辑标签非 SEC 字段（沿 form13f.ts 注释原话） |
| `person` 人物 | def14a_persons.top_persons{name,roles,n_companies,n_director_seats,companies[]} | 归一化全名（继承面板 `_norm_name` 同名合并披露） | 50（面板导出的正是这 50 人；660 人在上游不可见于显示层——覆盖率块必须写明） | 角色是文本见证提示；同名合并/漏报已由上游 methodology 披露 |
| `staker` 外部申报人 | stakes_13g.filings[].filer ∪ smart_money.recent_filings[].filer | 归一化（trim+upper）名称字符串 | 两窗合计 224 个不同 filer，但**只保留参与 ≥1 条边者 ≈ 67** | 多数为自然人；无稳定 CIK，不给内部路由 |
| 发行人桥接 | 见 §2.3 跨域共同标的表 | ticker | 实测跨 lane 重叠去重 ≈45 个 ticker | 不是图的第四类画布节点（见 §4 决策），落表 |

**身份合并规则（唯一的跨 lane 实体归并，v1）**：`normalize(staker.filer) == normalize(manager.name)`
（trim + 大写）时，该 staker 的边挂到对应 institution 节点上，节点带双 lane 徽章。
实测命中 **5 个**：AQR CAPITAL MANAGEMENT LLC / ARK INVESTMENT MANAGEMENT LLC /
GLENVIEW CAPITAL MANAGEMENT, LLC / MILLENNIUM MANAGEMENT LLC / POINT72 ASSET MANAGEMENT, L.P.
除此之外不做任何模糊匹配（姓氏大写变形、逗号差异不做 fuzzy——宁可少连不错连）。

### 2.2 三类边（实体—实体投影）

| 边类型 | 定义（分子/分母都是计数） | 源面板·字段 | 实测量 | 权重语义 |
|---|---|---|---|---|
| `co_hold` 共同持仓 | 同一季度两只受策展管理人可见书目中出现同一持仓键（ticker，缺则 cusip） | form13f.managers[].positions[]{ticker,cusip,issuer,value} | **636 对**；weight 1–20（D.E.Shaw×Millennium、Millennium×Citadel 各 20）；40/40 无孤立 | **共同持有的标的个数**（可分享明细含 verbatim value，13F 法定精确值非区间） |
| `co_board` 共席 | top_persons 中两人同坐至少一家公司（公司名精确匹配 boards[].company 解析 ticker） | def14a_persons.top_persons[].companies × boards[].company/ticker | **68 对**；牵涉 10 家有 ≥2 位已知人物的公司；76 条双部关系落到 41 家公司 | **共同董事会席位数** |
| `co_target` 同目标聚集 | 同一目标 issuer 上出现 ≥2 个不同申报人的**各自独立申报**（13G 可见 400 行 ∪ 13D 可见 120 行，target 名 trim+upper 匹配） | stakes_13g.filings[]{filer,target,ticker,form} ∪ smart_money.recent_filings[] | **53 对**、67 名 filer、53 对全部带 ticker；基准日期跨度 13G 2026-08-14→21 / 13D 08-17→21 必须随覆盖率披露 | **在同一目标上申报的不同来源行共同出现的次数（计数）** |

三边合计 **757 对**；参与实体 ≤40+50+67−5(合并) ≈ **152 节点上限**。

### 2.3 跨域共同标的（bridges，表格层而非画布层）

实测某 ticker 同时出现在 ≥2 个 lane：boards∩13F = **10**（AVAV/CALM/DAKT/FDX/FOSL/GIS/HHH/LW/MDT/ROIV）、
13G∩13F = **24**、13D∩13F = **14**、boards∩(13D∪13G) = **4**（AMC/CALM/CRMT/VIVS），去重 ≈45。
这是"势力交汇"最有叙事价值的发现（如 CALM 与 ROIV 同时刻被管理人持有、被外部人申报、有人物共席），
但它**只证明公司层面的巧合，不建立任何人—持有人之间的法律关系** ⇒ 落在常驻表格"跨域共同标的"
里呈现，不制造跨 lane 边。

## 3. 采样与规模上限（§3-2）——选择口径就是诚实本身

- **包含规则统一为一句话：一个节点/一条边进入面板，当且仅当它参与了至少一条由源面板字段
  推出的边。** 不做"凑数式"补点：未参与任何边的 35 个 staker（224−~67−20 边缘重叠由导出端
  精确计）、以及只在双部关系里出现过一次的人物，全部留在源面板可查但不进图。
- 13F 侧固定口径 = **受策展 40 家 × 可见书目 ≤50 持仓**。这不是全书（Citadel 13,575 只进可见
  50 条）——`coverage` 块明确写 "visible-books basis, full books larger"，绝不暗示全谱共同持仓。
- DEF 14A 侧固定口径 = **top_persons 导出的 50 人 × 104 份已解析申报**（150 份处理、69.3% 出名单、
  43 份诚实 unparsed）——覆盖率数字逐字镜像面板，不重算不再解释。
- 13D/G 侧固定口径 = **可见切片**（400+120 行，分别覆盖 7 天和 5 个交易日）——滚动窗口会自然
  积累历史（每日导出迁移），v1 不追全史（总库 15,982+12,744 属于 cadence lane，不是本模块的债）。
- **最终体量预估**：节点 ~120–160，边 700–800（以上实测值为当前快照；每次日更会漂移，
  因此契约测试一律从源面板重算比对，不钉死具体数）。

## 4. 派生面板 schema（§3-3）

输出 `web/src/data/aionis/lineage_graph.json`，由新增导出函数
**`export_lineage_graph()`** 生成（追加在 `scripts/export_terminal_data.py`，`main()` 注册，
mirror `export_form13f_stars`/`export_party_index` 的 SKIP-and-retain 卫兵）。字段级定义：

```jsonc
{
  "status": "ok",                       // ok | awaiting_fetch（任一源面板缺失即 SKIP 不写空壳）
  "as_of": "<四个源面板 as_of 的最大值>",
  "source_panels": ["form13f","def14a_persons","stakes_13g","smart_money"],
  "n_nodes": 152,                        // 数字为示例，非承诺值
  "n_edges": 757,
  "nodes": [{
     "id": "i:0001423053 | p:<norm-name> | s:<norm-name>",
     "type": "institution | person | staker",
     "label": "CITADEL ADVISORS LLC",  "zh_label": "城堡投资（格里芬）| null",
     "lanes": ["13f","def14a","13dg"], // 该实体实际被哪些源的边牵到
     "cik": "0001423053 | null",       // 仅 institution（或并入 institution 的原 staker）
     "manager_routable": true,         // cik ∈ form13f.managers 才 true（→ /manager/[cik]）
     "degree": {"co_hold": 39, "co_board": 0, "co_target": 2}
  }],
  "edges": [{
     "a": "id", "b": "id",             // 指向 nodes[].id；构建期校验必须存在
     "type": "co_hold | co_board | co_target",
     "w": 20,                          // 整数计数；== len(shared)，测试强制
     "shared": [                       // ≤8 条，超出打 truncated 标志
        {"k":"T:AAPL","tk":"AAPL|null","issuer":"APPLE INC"}          // co_hold
        // {"company":"Roivant Sciences Ltd.","tk":"ROIV"}            // co_board
        // {"target":"Brera Holdings PLC","tk":"BRRA","forms":"13D"}  // co_target
     ],
     "truncated": false
  }],
  "bridges": [{                          // 跨域共同标的（表格层，非画布节点）
     "tk": "CALM", "name":"CAL-MAINE FOODS|<来自 companies_dir/boards 的 verbatim 名称>",
     "in": ["13f","def14a","13dg"],      // 证据 lane（≤3，来自集合交集计算）
     "counts": {"managers": 3, "persons": 2, "stakers": 1}
  }],
  "components": {"n": 3, "largest": 141},   // 连通分量数与最大分量（人数），诚实展示多岛
  "windows": {                              // 逐字镜像各源窗口（含上面的真实日期跨度）
     "form13f_quarter": "2026-06-30",
     "stakes_visible_dates": {"start":"2026-08-14","end":"2026-08-21"},
     "smart_money_visible_dates": {"start":"2026-08-17","end":"2026-08-21"}
  },
  "coverage": {
     "13f":      {"basis":"visible books: 40 curated managers x <=50 positions", "full_books_larger": true, "isolated_managers": 0},
     "def14a":   {"basis":"top_persons export: 50 most-seated of 660 upstream persons; 104/150 filings with persons (69.3%)", "same_name_merges_possible": true},
     "13dg":     {"basis":"visible windows only (400 + 120 latest rows)", "joint_filing_members_not_decomposed": true}
  },
  "methodology": "<照 party_index 语气的长文，必含 §7 四句话>",
  "snapshot_ts": "<_stamp 自动>"
}
```

**体积预算**：紧凑编码（shared 截断 ≤8、缩进=1）估算 ~110–140KB，**硬上限 200KB**——超过即
视为编码 bug 而非调参空间；构建测试断言字节数。**barrel 决策**：独立模块
`web/src/data/aionis/lineage-graph.ts`（消费者仅 `/(dashboard)/force-camp`），**坚决不进 index.ts**
——理由引 barrel 头注释的原案卷教训（deploy 31869082383）：单一 merged barrel 会被 Turbopack
去重成一份共享 chunk，而命名再导出会按页 chunk **复制**数据（实测每页 +50–280KB）。本文档
本身就是 ~130KB 体量的数据集，进 barrel 意味着全部 40+ 页每页都背它。

**运行时注册（M 片）**：`data_health.panels` 增 `{key:"lineage_graph", category:"daily"}`
（mirror party_index）；api_catalog 登记沿 freight_taco 先例（有契约测试钉住登记一致性）。

## 5. 可视化形态决策（§3-4）

| 形态 | 适配度判断 |
|---|---|
| **力导向 node-link（推荐）** | 三个实体类 + 加权关系是天然的节点-链接叙事；合并的双 lane 节点会把三个星簇自然拉近，视觉直接回答"势力交汇在哪"；~152 节点在 SVG 无压力 |
| 弦图 | 强于环形双边流量，但在人/机构混排的异质节点上身份歧义大，weight 相差 1–20 时弧长失真放大误差感；移动端几乎不可读 |
| 邻接矩阵 | 最诚实可审计，但讲不出"谁抱团"；与现有 40 页体系（表格+卡）重复度高，作为**回退态的一部分**而非主视图 |

**推荐**：手写确定性 SVG 力导向（Fruchterman-Reingold 型弹簧迭代，种子=0 的伪随机初值，
`useMemo` 内跑 ~300 次迭代后冻结布局；**不用 requestAnimationFrame 持续模拟**）。逐条理由：

1. **体积**：152 节点/757 边不需要 canvas/WebGL/图库；recharts 3.8.0 是时间序列/分类图表库，
   没有网络图能力——为一个模块引入 d3-force/cytoscape 违反本仓"不为一个模块引入重型依赖"
   取舍（heatmap 注释原文 "Hand-rolled layout (no new deps)" 即判例）。
2. **确定性**：种子化 + 固定迭代次数 ⇒ 每次加载、SSR/客户端 hydration 一致，静态导出下可
   快照对比（把 H6 的精神当作 display-lane 工艺品味带到前端，不是研究规则）。
3. **可回退**：SVG `<g>/<line>/<circle>` 天然可访问性包装（title/aria-label），且下方常驻
   HTML 表格回退态对移动端、读屏器与 reduced-motion 用户完备。

**表格回退态（P9：列头永远先渲染）**：三条分区表（共同持仓 Top-N / 人物共席 / 同目标聚集）
+ 跨域共同标的表，全部来自同一份 JSON 的同一批边对象——canvas 挂了、JS 关了、移动端窄屏、
读屏器都拿到同一数据的不同投影。空态 = SegmentHeader + NullDisclaimer + 表格列头 + "数据暂不可用"。

## 6. 交互层（§3-5）

- **筛选药丸**：三类边 × 开关 + `min-weight ∈ {1..5}` 步进（纯客户端态；URL 参数同步
  ?types=&min= 作为 L 片增强）。每个药丸带诚实计数（P1 副标题内嵌计数+时间窗惯例：
  "757 边 · 13F Q2-2026 书目 + 08-14→21 申报窗"）。
- **点击节点 → 抽屉卡**：lane 徽章、类别标签、度数分解、样例 shared 明细（表格复述）
  与深链——**深链一律门控**：`manager_routable=true` 才给 `/manager/[cik]`（受策展才有书页）；
  issuer/shared.ticker 只有在导出期确认 `∈ stock_universe.json tickers` 才标记 `stock_routable`
  （实测全图 1,015 ticker 中仅 227 可路由，其余显示 "—" 文本）；人物**没有**单人流路由
  （/executives 是申报流级），抽屉就老实展示角色清单与关联 boards[].doc_url 外链（EDGAR 原文）。
  staker 同理只有申报外链，无内部页。
- **悬停高亮邻域**：CSS class 切换（无 JS 动画循环，尊重 prefers-reduced-motion）。
- **KPI 统计带（P2）**：n_nodes / n_edges / 最大连通分量 / 三类边各自计数 + 窗口副标题。
- **组件小地图（L 片可选）**：多连通分量诚实展示为"岛屿"卡片列表，默认滚动画布主体。

## 7. 诚实边界（§3-6）——项目签名的措辞，逐条写入 methodology 与页面脚注

1. **共同持仓 ≠ 一致行动**：“co-holding is a factual same-quarter filing overlap between two
   curators over the same issuers; it implies neither coordination nor conspiracy.”
   （中文页脚同步：共同持仓仅为同季各自申报的事实重合，不构成一致行动主张。）
2. **同目标聚集 ≠ 联合申报联盟**（本设计最重要的红线）：已提交面板中 520 行 13D/G 的
   doc_url 全部唯一——联合申报的成员名单没有被拆解。边语义只能是"independently-filed
   stakes converging on the same issuer in the visible window"；界面上禁止出现"联盟/consortium/
   一致行动"字样，brera 例子（三名自然人各自申报同一目标）要在 methodology 里作为反例锚定。
3. **无价格、无收益、无业绩主张**：照 party_index 措辞谱系（"no prices, no returns, no
   performance claim; display lane, never a research signal"）。live 价格 Worker 绝不进场。
4. **覆盖率逐类披露 + 空≠错**：三类的 basis 字符串逐字来自 §2.2 表；任何缺失维度渲染 "—"
   （fmtEmpty）：人物无 ticker 语义、staker 无 CIK 无内部路由等，一律显式缺席而非兜造。

## 8. 契约测试清单（§3-7，`tests/test_web_terminal_data.py` 追加，风格 = `test_party_index_panel_contract` 的源重算比对）

1. `test_lineage_graph_panel_contract` —— schema 钉死：status/as_of/source_panels/n_nodes/
   n_edges/nodes/edges/bridges/components/windows/coverage/methodology/snapshot_ts 键集齐；
   status!=ok 时允许整个面板缺位于保留旧值（retain-guard 语义）。
2. `test_lineage_graph_co_hold_recompute_agrees_with_panel` —— 从 committed form13f.json 用
   相同键规则（ticker else cusip）重算 636 对边集合，**逐边相等**（a,b,w,shared 内容）。
3. `test_lineage_graph_co_board_recompute_agrees_with_panel` —— 从 def14a_persons.json 重算
   人企映射 → 投影 68 对共席边，逐边相等；同名合并规则与面板 `_norm_name` 一致。
4. `test_lineage_graph_co_target_recompute_agrees_with_windows` —— 从 stakes_13g + smart_money
   可见窗重算 53 对，逐边相等；shared.forms 忠实于源 form 字段。
5. `test_lineage_graph_weights_are_integer_counts` —— 每条边 w 为正整数且 == len(shared) 或
   truncated 时 == 完整重算数；float 权重即 fail（禁编造相似度的守卫化表达）。
6. `test_lineage_graph_edges_reference_existing_nodes_and_lanes` —— 引用完整性：每条边的
   a/b 都在 nodes；边类型蕴含两端点的 lanes 成员（co_board ⇒ 两端都有 "def14a"）。
7. `test_lineage_graph_identity_merge_only_by_exact_name` —— 断言不存在除 5 个精确名匹配外
   的跨 lane 并入；staker 未合并节点的 id 不出现在 institution 集合（防模糊归属漂移）。
8. `test_lineage_graph_stock_routable_flags_match_stock_universe` —— 每个 stock_routable=true
   的 ticker ∈ stock_universe.json 的 ticker 集（防造深链）；false 无此约束。
9. `test_lineage_graph_bridges_consistent_with_sources` —— 每个 bridge 的 in/counts 能从四个
   源面板 ticker 集合交集重算（这是巧合呈现，不是关系发明，必须有重算门）。
10. `test_lineage_graph_disclosures_present` —— methodology 小写包含："separately filed"（或
    "not decomposed"/"joint filings" caveat）、"coordination"否定句、("no prices" 或 "no returns")、
    三类 coverage.basis 非空；payload 字节数 ≤200*1024。
11. `test_lineage_graph_registered_in_health_and_catalog` —— data_health.panels 有
    key=lineage_graph 且 category=daily；api_catalog 有对应条目（freight_taco 先例）。

## 9. 实施阶梯（§3-8，细节展开在构建规格 TASK-DISP-H5-lineage-build.md）

- **S1（导出端 + 数据 + 类型 + 契约测试，可独立验收）**
  `scripts/export_terminal_data.py`(+`export_lineage_graph`+main 注册+_dh_rows/api_catalog 登记)、
  `web/src/data/aionis/lineage_graph.json`(产物)、`web/src/data/aionis/lineage-graph.ts`(新模块)、
  `tests/test_web_terminal_data.py`(+11 测试)。验收：pytest 全绿 + ruff 净。
- **M1（视图 + i18n + 导航接线，可独立验收）**
  `web/src/app/(dashboard)/force-camp/page.tsx`、`web/src/components/force-camp/force-camp-view.tsx`
  (+ 纯函数 layout.ts 力导向布局)、`web/src/i18n/dict.ts`(zh/en 键全量对称)、
  `web/src/components/top-nav.tsx` + `command-palette.tsx` + `overview.tsx` explore grid。
  验收：tsc 0 + eslint 净 + build 页数 +1 不减。
- **L1（增强，非验收门）**：URL 态筛选、分量"岛屿"卡、bridge 表排序交互。

前置门：本设计属 roadmap §3-H5，业主决策清单含"势力阵营 GO"——派发构建前应取得业主 GO。

## 10. 风险与降级预案（如实记录）

- **v1 可行性判定：可行，无需整体降级**——三类边都有充足的实测量且全部可重算。
- 若未来 form13f/def14a 的上游导出扩面（13F 全书、660 人导出），重算型测试自动让边集长大，
  但**上方三条诚实口径（visible-books/top-50/visible-windows）必须同步改写 coverage 文案**，
  防止口径陈旧漂移成隐性夸大——这是本模块唯一的长期维护债。
- 若某日可见 13D/G 窗口过窄导致 co_target=0：诚实空态（P9 列头 + NullDisclaimer），三边类
  过滤器自动隐藏 zero 类，page 不隐藏。502 无锁仍可发布——**空图谱也是诚实结果**。
