# TASK-DISP-H5 — 势力阵营（force camp）血缘图谱：构建（显示 lane）

**Lane**: display。**优先级**: P1（post-parity roadmap H5，`reports/design/2026-08-25-post-parity-roadmap.md`
§3-H5；业主决策清单"势力阵营 GO"——派发前应已取得业主 GO）。
**设计依据**: `reports/design/2026-08-26-force-camp-design.md`（本文件自包含，可不读设计文档执行；
两者冲突时以本文为准并回报差异）。

## 0. 背景一段话

势力阵营 = 从**已提交面板**在导出期派生的关系图谱：40 位受策展管理人的 13F 可见书目投影出
"共同持仓"边（实测 636 对）、DEF 14A top_persons 的公司席重叠投影出"共席"边（68 对）、
13D/13G 可见申报窗投影出"同目标聚集"边（53 对）。零新抓取、零研究面接触。体量 ~150 节点 /
~760 边，前端用手写确定性 SVG 力导向 + 常驻表格回退态呈现，不引入任何图库。
派生函数照 `export_form13f_stars` / `export_party_index` 先例：读 `web/src/data/aionis/`
已提交 JSON，缺失即 SKIP-and-retain，绝不产出空壳。

## 1. 铁律（全文并入，违反任一即 FAIL）

- 纯 display-lane：0 ledger/frozen/config/prereg/OOS；研究面零接触。
- 零新抓取（纯派生）；绝不编造边/权重/覆盖率。
- 数据模块体积纪律（独立模块不进 barrel）。
- zh/en i18n 双语键集必须对称。
- 完成定义 = 契约测试绿 + tsc 0 + eslint 净 + build 页数不减（build 由主线集成时统一跑）。

补充红线（来自设计 §7，测试会钉住）：共同持仓/同目标聚集**不构成一致行动主张**——源面板中
联合申报未按成员拆解（可见 520 行 doc_url 全部唯一），故第三类边语义只能是"independently
filed stakes converging on the same target"，界面与文案禁用"联盟/consortium"。无价格、无收益、
无业绩主张；live 价格 Worker 绝不进场。缺失一律 "—"。

## 2. 文件清单（新建 / 修改逐一列出）

### 新建

| # | 文件 | 内容 |
|---|---|---|
| N1 | `web/src/data/aionis/lineage_graph.json` | 导出产物（tracked）；schema 见 §3 |
| N2 | `web/src/data/aionis/lineage-graph.ts` | 独立数据模块（mirror `form13f.ts` 头注释：说明 ~130KB 体量、不进 barrel 的 chunk 教训、契约对应 `scripts/export_terminal_data.py::export_lineage_graph`）。显式 per-field 类型 + `as LineageGraph` 断言；仅 `/(dashboard)/force-camp` 导入 |
| N3 | `web/src/app/(dashboard)/force-camp/page.tsx` | server component：SegmentHeader(segment="institution", introKey="forcecamp.intro", asOf, countHint="…边 · 13F Q 书目 + MM-DD→MM-DD 申报窗") + `<ForceCampView />` |
| N4 | `web/src/components/force-camp/force-camp-view.tsx` | KPI 带 → 边类型过滤药丸(+min-weight) → SVG 力导向画布 → 常驻四分区表（三类边 + 跨域共同标的桥接表）→ 方法学脚注。点击节点抽屉卡（badge lanes/度数分解/shared 样例/门控深链）|
| N5 | `web/src/components/force-camp/layout.ts` | 纯函数力导向布局：种子=0 mulberry32 PRNG、Fruchterman-Reingold 弹簧迭代 ~300 次冻结、输出 {id,x,y}[]；无 requestAnimationFrame 循环、无新依赖 |

### 修改

| # | 文件 | 改动 |
|---|---|---|
| M1 | `scripts/export_terminal_data.py` | ① 新增 `export_lineage_graph()`（算法 §4）② `main()` 注册 ③ `export_data_health()` 的 `_dh_rows` 映射增加 lineage_graph 行（category="daily"，mirror party_index）④ `export_api_catalog()` 目录登记 mirror freight_taco 先例 |
| M2 | `tests/test_web_terminal_data.py` | 追加 §5 的 11 个契约测试 |
| M3 | `web/src/i18n/dict.ts` | zh/en 对称追加 §6 全部键 |
| M4 | `web/src/components/top-nav.tsx` | `nav.group.institution` 组内加 `{ title: t("nav.forcecamp"), sub: t("nav.sub.forcecamp"), url: "/force-camp" }`（icon 用 lucide Network/Share2 系，不新增依赖包） |
| M5 | `web/src/components/command-palette.tsx` | items 数组加 `/force-camp` 条目（labelKey="nav.forcecamp"） |
| M6 | `web/src/components/overview/overview.tsx` | explore grid 加 force-camp 卡（t("overview.explore.t_forcecamp") / t("overview.explore.forcecamp")） |

不改任何其他文件；不改 form13f/filers13f/stock-universe/companies-dir 各 `.ts` 模块与其 JSON。

## 3. 面板 schema（固定契约，N1/N2 都必须精确实现）

顶层键（缺一不可，多余键禁止）：
`status, as_of, source_panels, n_nodes, n_edges, nodes[], edges[], bridges[], components,
windows, coverage, methodology, snapshot_ts`

```jsonc
{
  "status": "ok",
  "as_of": "<form13f/def14a_persons/stakes_13g/smart_money 四面板 as_of 字符串最大值>",
  "source_panels": ["form13f","def14a_persons","stakes_13g","smart_money"],
  "n_nodes": "<int>", "n_edges": "<int>",
  "nodes": [{
    "id": "i:<cik> | p:<norm-name> | s:<norm-name>",   // 类型前缀 id
    "type": "institution|person|staker",
    "label": "<name verbatim>", "zh_label": "<zh_name|null>",
    "lanes": ["13f","def14a","13dg"],                  // 该实体实际被边牵到的源
    "cik": "<10位CIK|null>",                            // 仅 institution
    "manager_routable": true,                           // cik ∈ form13f.managers
    "degree": {"co_hold": int, "co_board": int, "co_target": int}
  }],
  "edges": [{
    "a": "<node.id>", "b": "<node.id>",                // 构建期校验存在性
    "type": "co_hold|co_board|co_target",
    "w": "<正整数计数>",                                 // == len(shared)；禁止 float
    "shared": [ /* ≤8 条，超出截断 */ ],
    "truncated": false
  }],
  // shared 元素三形态（按边类型）:
  // co_hold  : {"k":"T:TICKER|C:CUSIP", "tk":"TICKER|null", "issuer":"verbatim"}
  // co_board : {"company":"verbatim boards[].company", "tk":"TICKER|null"}
  // co_target: {"target":"verbatim", "tk":"TICKER|null", "forms":"13D|SC 13G|SC 13G/A"}
  "bridges": [{                       // ticker 出现在 ≥2 个 lane 才收录
    "tk": "CALM", "name": "<boards[].company 或 companies_dir verbatim>",
    "in": ["13f","def14a","13dg"],
    "counts": {"managers": int, "persons": int, "stakers": int}
  }],
  "components": {"n": int, "largest": int},
  "windows": {
    "form13f_quarter": "<as_of verbatim>",
    "stakes_visible_dates": {"start":"<min date>","end":"<max date>"},
    "smart_money_visible_dates": {"start":"<min date>","end":"<max date>"}
  },
  "coverage": {
    "13f": {"basis":"visible books: <n> curated managers x <=50 positions",
             "full_books_larger": true, "isolated_managers": int},
    "def14a": {"basis":"top_persons export: <50> most-seated of <660> upstream persons; "
                        "<104>/<150> filings with persons (<69.3>%)",
               "same_name_merges_possible": true},
    "13dg": {"basis":"visible windows only (<400> + <120> latest rows)",
              "joint_filing_members_not_decomposed": true}
  },
  "methodology": "<长文，必含 §5-T9 测试要求的措辞要素>",
  "snapshot_ts": "<_stamp>"
}
```

## 4. 导出算法（export_lineage_graph，全部 _dh_read 已提交面板）

0. 任一输入缺失/status≠ok ⇒ `_skip_retain("lineage_graph", ...)` 并 return（N1 不写空壳）。
1. **归一化函数** `_lg_norm(s)` = strip().upper()（不做 fuzzy；样式 mirror `_sm_norm_name`）。
2. **co_hold**：遍历 `form13f.managers` 的 `positions`（不动 changes），持仓键
   `k = "T:"+ticker if ticker else "C:"+cusip`；按 manager cik 收集键集合；两两交集非空 ⇒
   一条边（pair 按字典序定向），w=交集大小，shared 取前 8 个键的明细
   （issuer verbatim、tk=ticker or null）。confined to 可见书目——methodology 写明。
3. **co_board**：取 `def14a_persons.top_persons`，人 id=`p:_lg_norm(name)`；对每人 companies[]
   与 `boards[].company` 精确匹配解出 ticker（41/41 实测命中，未命中 tk=null）；同一公司的
   人两两连边，w=共同公司数，shared={company,tk}。person 节点仅保留参与 ≥1 边者。
4. **co_target**：合并 `stakes_13g.filings`(400) ∪ `smart_money.recent_filings`(120)，
   按 `_lg_norm(target)` 分组；组内不同 filer 两两连边，w=组内涉及申报行共同出现的计数，
   shared={target,tk,forms}（一目标多形式时 forms 记"|"拼接去重）。
   filer 默认建 `s:` 节点；**唯一身份合并规则**：`_lg_norm(filer) == _lg_norm(manager.name)`
   时该边的端点改挂 `i:` 节点、lanes 补 "13dg"、该 staker 不再单建节点（实测恰好并入
   AQR / ARK / GLENVIEW / MILLENNIUM / POINT72 五家——但代码只写规则不写名单）。
5. **bridges**：三个 ticker 集（13F positions 的 ticker 集 / def14a boards ticker 集 /
   13D∪G 窗口 ticker 集）两两以上交集 ⇒ bridge 行；counts=各 lane 内涉及的不同实体数。
6. **components**：无向连通分量计数 + 最大分量节点数。
7. 序列化 `json.dumps(_stamp(payload), indent=1, default=str)`；打印规模行（mirror 其他
   exporter 的 `[export-terminal] lineage_graph: …`）；**断言 payload 字节数 ≤200*1024**
   （超限抛错视为编码 bug）。
8. Node 属性：nodes[].id/type/label/zh_label/lanes/cik/manager_routable/degree；
   manager_routable 由 `form13f.managers` CIK 集判定；ledger/aioos 无关字段永不出现。

## 5. 契约测试（M2，风格=从源面板重算逐项比对，参考 test_party_index_panel_contract）

命名与断言意图（数量上限值等**绝不钉死**，只钉一致性与可重算性）：

1. `test_lineage_graph_panel_contract` —— 键集 == §3 全集；source_panels 有序；status∈{ok}；
   n_nodes==len(nodes)、n_edges==len(edges)；payload ≤200KB。
2. `test_lineage_graph_co_hold_recompute_agrees_with_panel` —— 从 form13f.json 以相同键规则
   重算 pair→w→shared 三元组全集，与面板逐条相等。
3. `test_lineage_graph_co_board_recompute_agrees_with_panel` —— 同法重算 top_persons×boards。
4. `test_lineage_graph_co_target_recompute_agrees_with_windows` —— 同法重算双窗并集。
5. `test_lineage_graph_weights_are_integer_counts` —— w 正整数且（未截断时）==len(shared)、
   截断时 == 重算完整数；truncated ⇔ len(shared)==8 且 w>8。
6. `test_lineage_graph_edges_reference_existing_nodes_and_lanes` —— a/b ∈ nodes；type 与两端
   lanes 一致（co_board⇒两端含"def14a"；co_hold⇒"13f"；co_target⇒含"13dg"）。
7. `test_lineage_graph_identity_merge_only_by_exact_name` —— 图中不存在名实不符的合并：
   每个 institution.lanes 含 "13dg" 的节点，其名称 `_lg_norm` 后必能同时在 13D/G 窗口
   filer 名集合中找到（防规则外漂移）；person/staker 节点互不换型。
8. `test_lineage_graph_stock_routable_flags_match_stock_universe` —— bridges[].tk 及 shared.tk
   仅要求存在性于源面板；而 view 用的 stock_routable 判定必须在**导出期**完成：若 schema 中
   存在该标志，则每个 true 的 ticker ∈ stock_universe.json tickers 集（false 无约束）。
9. `test_lineage_graph_bridges_consistent_with_sources` —— 每 bridge.in ⊆{13f,def14a,13dg}
   且该 tk 确实出现在 in 中所列 lane 的对应 ticker 集合；counts 能重算。
10. `test_lineage_graph_disclosures_present` —— methodology.lower() 同时包含：
    "separately filed" 或 "joint filing"；"not decomposed" 或 "independently"；
    "coordination"（伴随否定语义）；"no prices" 或 "no returns"；coverage 三 basis 非空且
    def14a.basis 内含源面板 coverage_pct 数值字符串镜像。
11. `test_lineage_graph_registered_in_health_and_catalog` —— data_health.panels 有
    key=lineage_graph（category=daily、present=True）；api_catalog 条目与 panel 一致
    （freight_taco 注册测试的镜像）。

## 6. i18n（M3，zh 在 zh 块、en 在 en 块，键集严格对称，key 数一致由对称检查习惯保证）

```
nav.forcecamp            势力阵营                    Force Camps
nav.sub.forcecamp        机构·人物·大额持股关系图     Institutions · people · stake networks
forcecamp.intro          关系图谱……(方法学一句)       Relationship graph derived from committed panels…
forcecamp.kpi.nodes      实体                         Entities
forcecamp.kpi.edges      关系边                      Relations
forcecamp.kpi.components 连通分量                     Components
forcecamp.kpi.holders    机构（13F 策展）             Institutions (curated 13F)
forcecamp.type.co_hold   共同持仓                     Co-holdings
forcecamp.type.co_board  人物共席                     Shared board seats
forcecamp.type.co_target 同目标申报聚集               Same-target stake clusters
forcecamp.min_weight     最少共同标的                 Min shared items
forcecamp.legend.institution  机构                    Institution
forcecamp.legend.person  人物                         Person
forcecamp.legend.staker  外部申报人                   External filer
forcecamp.bridge.title   跨域共同标的                 Cross-lane shared issuers
forcecamp.table.edge_a / .edge_b / .weight / .shared   当事方A / 当事方B / 共同标的数 / 明细（en 同构）
forcecamp.drawer.roles   角色清单                     Roles
forcecamp.drawer.seats   关联席位                     Board seats
forcecamp.disclaimer.coordination   共同持仓与同目标申报均为各自独立申报的事实重合，不构成一致行动或联盟主张。
                                    Co-holding and same-target filing overlaps are factual coincidences of separate filings — neither coordination nor a consortium claim.
forcecamp.disclaimer.window         本页仅反映导出期可见书目与最近申报窗（日期见各表头）。数据为 SEC 公开披露的转述，无价格、无收益、无业绩主张。
                                    Visible books and the latest filing windows only (dates on each table). A restatement of public SEC disclosures — no prices, no returns, no performance claims.
forcecamp.empty          数据暂不可用                 Data temporarily unavailable
overview.explore.t_forcecamp  势力阵营                Force Camps
overview.explore.forcecamp    13F 共同持仓 × DEF 14A 共席 × 13D/13G 目标聚集
                              13F co-holdings x DEF 14A seats x 13D/13G same-target clusters
```

（页面文案若需增减键，两侧同步；上表为最低完整集。格式化统一走 `lib/format.ts`
fmtInt/fmtUsd/fmtEmpty—"；暗色主题 token / `--up/--down` 不涉方向色滥用。）

## 7. 视图行为要点（N3–N5）

- 过滤药丸三类开关默认全开 + min-weight 步进 {1..5}；某类边数为 0 时药丸自动隐藏（诚实空态：
  表格分区仍渲染列头 + NullDisclaimer，P9）。
- SVG：<svg viewBox> + <g class nodes/edges>；边 stroke-width ∝ w（cap 到 1–4px 线性映射）；
  节点 r 按 type 固定三档；title/aria-label 写 label+w。布局一次算定（layout.ts 冻结位置），
  窗口 resize 只缩放 viewBox 不重跑模拟。prefers-reduced-motion 下不做过渡动画。
- 抽屉卡深链门控：institution 且 manager_routable ⇒ Link /manager/[cik]；bridge/shared 里
  stock_universe 命中的 ticker ⇒ /stock/[ticker]（判定在导出期 stock_routable 落盘优先，
  否则客户端用 stockUniverse 内存判定亦可，两种都不得给未收录 ticker 发链）；
  person/staker 无内部路由，给 EDGAR doc_url 外链（rel=noopener）或 "—"。
- 页脚：ProvenanceBadge + methodology 缩引 + 两句 disclaimer（i18n 完整键）。

## 8. 验证命令全集（完成定义逐条运行）

```bash
uv run pytest -q tests/test_web_terminal_data.py        # S1 门：11 个新测试绿
uv run pytest -q                                        # 全套 hermetic 绿
uv run python scripts/export_terminal_data.py           # 本地导出演练（SKIP-and-retain 生效则如实记录）
uv run ruff check                                       # lint 净
cd web && pnpm exec tsc --noEmit && pnpm lint           # tsc 0 + eslint 净
cd web && pnpm build                                    # 主线集成时统一跑：静态页数 ≥ 原 40 页 +1(/force-camp)
uv run streamlit run dashboard/app.py                   # 无关面板——不需要跑，列出仅为完整性排除
```

本地无法完整 build 时如实记录（display lane 惯例：build 由主线集成时统一验证）。

## 9. 边界与非目标（防 scope 膨胀）

- 不做全史 13D/G 回溯（cadence lane 自然积累后再说）；不消费 gitignored 上游缓存
  （660 人导出是上游结构升级，另立任务）；不做 canvas/WebGL、不装 d3/cytoscape/sigma；
  不做 URL 态筛选与"岛屿"卡（L1 增强可选，非验收门）；不触碰 ledger/frozen/研究目录任何文件；
  不改四个既有 `.ts` 数据模块。
