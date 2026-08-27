# Post-refresh full-site static consistency audit — 2026-08-28

**性质**：VERIFY 审计（零修复，只查证）。对 1ddd625 本地数据刷新（daily 面板 as_of 08-18~25 → 08-26~27）之后的 `web/out/` 全站构建产物做静态一致性扫查。本轮**未运行任何写操作命令、零网络请求、纯本地静态分析**。

## 基线

| 项 | 值 |
|---|---|
| HEAD | `370bda7`（370bda70f227281074cdedb8db1aa6fa9c0937ac，位于刷新 commit `1ddd625` 之上一个 state commit） |
| 构建产物 | `web/out/` 1,501 个 `.html`（236 MB） |
| 数据水位 | 08-27：ark / def14a / form_d / knowledge_shelf / news_feed / reddit_trending；08-26：form8k / ipo / stakes_13g / lineage_graph；08-21：filers13f / executives / theme_etfs；form4 最新申报 08-24（snapshot_ts 08-27，申报自然滞后）；13F 类为季度水位 2026-06-30（口径正常） |
| 方法 | Python 全量静态扫描：剥 `<script>/<style>/标签` 后扫可见文本；`<a href>` 内链解析对照 `out/` 扁平 route 文件；面板 JSON 数字复算与页面披露比对；i18n 键集合差集 |

## 结论概览

**P0 ×2，P1 ×0，P2 ×2。** 其余 6 项扫查（统计条调和、as_of 披露、/manager 完整性、/stock 深链、i18n 对称、诚实性抽查）全部通过。

---

## 发现项

### P0-1 内链死链：28 个唯一 `/Aionis/stock/<TICKER>` 死链，58 处链接实例（来源：刷新后的 13G 面板）

41,370 个 `<a>` 内链中，28 个唯一目标解析不到 `out/stock/` 下任何已建页（1,421 页宇宙），共 58 处实例，全部集中在两页：`smart-money.html`（29 处）与 `confirmation.html`（29 处，同一组 ticker）。

死链 ticker（28）：`CIIT VTMX LSTA WW CRCW EHGO EDSA VDTA IOTR XXII ALPX BIII BPRE CHY CHI CINT CCD CALC DFSC EQX FRFHF PNI PCQ NIXX NSAI SGLY SBDS` + 字面 `NONE.`（见 P0-2）。

**溯源**：28 个 ticker 全部存在于刷新后的 `web/src/data/aionis/stakes_13g.json`（as_of 2026-08-26）的 filings 中；渲染为 stock 链接时未过 1,421 页 stock 宇宙门。其余面板仅零星命中（filing_stream 10 个、smart_money/form_d/form13f 各 1 个），不构成完整来源。

**证据样例**：`web/out/smart-money.html` 中 `<a href="/Aionis/stock/CIIT">CIIT</a>`；`out/stock/` 下无 `CIIT.html`。抽样 ticker 均为小盘/新上市/外国私人发行人（13G 常见申报对象），落在宇宙门之外属预期，但链接照常生成不是预期。

**修复建议（一句话）**：ticker→`/stock/` 链接生成前先查 `stock_universe`，未建页降级为纯文本 ticker（与站点"诚实留空"纪律一致）。

### P0-2 字面 `"NONE."` ticker 渲染为链接（解析失败哨兵值渗入渲染层）

`web/src/data/aionis/stakes_13g.json` 的 `filings[20]`（SC 13G/A，filer "Host-Plus Pty Ltd … HOSTPLUS Pooled Superan…"）携带字面 `ticker: "NONE."`；`smart-money.html` 与 `confirmation.html` 将其渲染为 `<a href="/Aionis/stock/NONE.">NONE.</a>`。这是解析失败值未清洗直接进入渲染+链接模板的双重度缺陷，死链清单中唯一的非 ticker 值。

**修复建议（一句话）**：解析失败的 ticker 行显示为 "—" 并计入 `data_health.source_health`（同页面自身声明的方法学），绝不生成链接。

### P1 — 无

八 hub 页 as_of 披露、统计条复算、/manager 完整性、诚实性披露均无口径漂移或缺失（见下）。

### P2-1 dashboard 统计条 "Reddit 标的 297" 与面板实际行数 100 的口径差未在统计条就近披露

`reddit_trending.json`：`count_declared=297`，`n_rows=100`（ApeWisdom 分页上限）。dashboard.html 统计条显示 297（=count_declared，复算吻合）；`reddit.html` 自己显式披露 "100 / 297"。跨页无矛盾，但 dashboard 侧无就近说明 297 为 declared 而非 served。**建议**：统计条加"（已载前 100）"微披露或 tooltip。

### P2-2 `web/out/Aionis` 为指向 `web/out` 自身的 NTFS junction

`web/out/Aionis -> web/out`（2026-08-28 00:23 创建，basePath 本地预览用）。静态托管不影响，但任何目录遍历工具（含本次审计的 `rglob`）会无限递归。**建议**：构建/预览脚本内注释标注，或改用真正的资产复制，防后续自动化踩坑。

---

## 通过项（逐项证据）

1. **渲染垃圾 = 零**。剥 script 后全站 1,501 页可见文本：`[object Object]` 0、`NaN` 0、`undefined` 0。裸 `null` 可见文本 25 处逐条人工定性：全部为合法统计/方法学语义（"模型无判别力（诚实 null）"、"`a null pct never yields a status`"、data-health 图例 "null = the panel carries no observation date"、executives 解析置信分布类别计数 "age-rows 79 name-roles 25 null 46"——后者即唯一一处 `>null<` 渲染单元格，为图例类别，合法）。
2. **统计条五数调和**（out/dashboard.html ↔ 面板 JSON）：上市公司 **10,388** = `companies_dir.json n=10388`（len(companies)=10388）✓；机构申报人 **9,385** = `filers13f.json n_filers=9385`（len=9385）✓；明星投资人 **42** = `form13f-stars.json n_managers=42` ✓；政客交易 **2,812** = `politician_trades_tx.json total=2812`（len(transactions)=2812）✓；Reddit 标的 **297** = `count_declared=297` ✓（口径提示见 P2-1）。五数均可从面板复算吻合。
3. **八 hub 页 as_of 披露**：stakes 08-26 = `stakes_13g` ✓；events 08-26 = `form8k` ✓；ipo 08-26 = `ipo` ✓；executives 08-21 = `executives` ✓；institutions 08-21（+13F 季度水位 2026-06-30×43 处，口径正常）= `filers13f` ✓；smart-money 08-21 = `smart_money.latest_date` ✓；congress 08-18/08-20 = `politician_trades.as_of`/`politician_trades_tx.as_of` ✓；insiders 08-24 = `form4.recent` 最大申报日（snapshot_ts 08-27）✓。刷新后 08-26/27 水位已如实上墙。
4. **/manager 页完整性**：`out/manager/` 42 个 SSG 页 = `n_managers` 42 ✓；42 页可见文本均含非空 top-10 持仓内容（无稀疏壳页）；样例页（0000807249.html）含完整方法学披露与 top-10 + QoQ diff 语境。
5. **/stock 页宇宙门**：抽查 AAPL/NVDA/CNP/TSLA 4 页全部非壳，均含完整"模型读数"章节（ledger #49 冻结结论 "combined rank-IC = −0.0088，NULL" + 评分走势/区域排名/校准概率）。`BRK-B` 无文件，但站内 41,370 内链中亦无一处指向它（BRK 不在 1,421 宇宙，`stock_universe.json n_stocks=1421=len(stocks)` 自洽）——非死链。stock 死链已在 P0-1 单列。
6. **i18n 对称**：`web/src/i18n/dict.ts` zh/en 各 **1,094** 键，差集双向为空，无双键。
7. **诚实性抽查**：picks 页冻结披露在位（"冻结 OOS 无市值维度"、集中度方法说明）✓；data-health 三分类 **25 日更 / 9 源节奏 / 15 冻结** = `data_health.json summary {n_daily:25, n_cadence:9, n_frozen:15}`，25+9+15=49=n_panels ✓；reddit 页 "100 / 297" 分页上限披露在位 ✓。

## 零修复承诺兑现

**本轮未修改任何生产文件。** 全部操作为只读静态分析（Python 只读扫描 + git 只读命令）；本报告为唯一新建文件。未触碰 `docs/code-review/`（并发 session 领地）、`data/`，未执行 build/export/fetch，未 push。
