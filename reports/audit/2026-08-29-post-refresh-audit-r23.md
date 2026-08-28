# Post-refresh full-site static consistency audit (r23) — 2026-08-29

**性质**：VERIFY 审计（DEV-V，零修复，只查证）。对轮 23 数据补跑（daily 面板 → 08-27/28）+
`web/out/` 重建后的全站构建产物做静态一致性扫查。本轮**零写操作、零网络请求、零生产文件改动**，
纯本地静态分析。任务书：`tasks/active/TASK-DISP-V-post-refresh-audit.md`。

## 基线

| 项 | 值 |
|---|---|
| HEAD（审计时） | `43ffa25`（main，位于刷新 commit `9e8d21f` 之上；`main...origin/main [ahead 21]`） |
| 构建产物 | `web/out/` **1,502** 个 `.html`（junction 安全遍历实测；`out/manager/` 43 页；`out/stock/` 1,421 页） |
| 面板 | `web/out/api/v1/panels/` 51 个 JSON（api_catalog 记 49 endpoints + catalog + ledger_audit） |
| 数据水位 | 08-28：news_feed / reddit_trending / form4 snapshot；08-27：ark / def14a / form_d / filing_stream / knowledge_shelf / ipo / lineage_graph / smart_money(latest_date) / theme_etfs；08-26：form8k / stakes_13g；08-21：executives / filers13f；13F 季度水位 2026-06-30；cot latest 08-18（CFTC 周五盘后节奏）、korea_proxy 08-14（FRED 周度）＝源节奏诚实值 |
| Junction 陷阱 | `web/Aionis -> web/out` junction **存在**（web 层，2026-08-24 22:51）；`out/` 内部本轮**无** junction（轮 22 P2-2 所述 `out/Aionis` 未复现）。扫描器一律先判 reparse point 再入目录 |
| 方法 | Python 全量静态扫描（脚本存 `data/cache/audit_r23/`，未提交）：junction 守卫目录遍历；剥 `<script>/<style>/注释/标签` 后扫可见文本；全部 `<a href>` 解析对照 `out/` 全文件宇宙（html+json+txt）；面板 JSON 数字复算与页面披露比对；i18n 键集合差集 |

## 结论概览

**8/8 审计项 PASS。发现 P0×0、P1×0、P2×0、P3×2（均为披露口径观察，无失真/无超claim）。**
轮 22 三个修复项（stock 宇宙门、哨兵清洗、Reddit 就近披露）在 08-28 新数据下**全部保持修复态**——
本轮刷新带入的新 13G/filing ticker 未再产生任何宇宙外死链。def14a persons " Age" 脏尾巴全站清零保持。

---

## 逐审计项结果

| # | 审计项 | 结果 | 关键数字 |
|---|---|---|---|
| 1a | /stock/ 内链宇宙门（轮 22 P0-1 回归复验） | **PASS** | 41,483 内链中 `/Aionis/stock/*` 503 个唯一 ticker，**0 死链**；全部可解析到 `out/stock/` 1,421 页 |
| 1b | 哨兵 ticker 清洗（轮 22 P0-2 回归复验） | **PASS** | 链接/可点文本哨兵 **0** 命中；`NONE.` 残留 0；可见文本 NULL×2,881 逐类定性均为诚实 null 语义；`stakes_13g.json` 400 filings 中 0 哨兵、37 null ticker ＝ `data_health.source_health.ticker_null=37` 精确入账 |
| 1c | Reddit 统计条就近披露（轮 22 P2-1 / ee6ea16） | **PASS** | dashboard 统计条 "Reddit 标的 322" 旁 **"已载 100"** 就近披露在位（dashboard.html @char 36285/36448）＝`reddit_trending.json count_declared=322 / n_rows=100` |
| 2 | 渲染垃圾全站扫 | **PASS** | 剥 script 后全站 1,502 页可见文本：`undefined` / `NaN` / `[object Object]` / `0月NaN日` / `Infinity` 全部 **0**；非空转证明：`undefined` 在原始 HTML 出现 17,470 次（300 页抽样），剥脚本后可见 0 |
| 3 | 内链完整性 | **PASS** | 46,856 `<a href>`，41,483 个 `/Aionis/*` 内链对照 out/ 全文件宇宙（15,116 文件）逐一解析，**0 死链** |
| 4 | i18n 对称性 | **PASS** | `web/src/i18n/dict.ts` zh **1,095** / en **1,095** 键，双向差集均为空 |
| 5 | StatBand 五数调和 | **PASS** | 上市公司 **10,391**＝`companies_dir.json n=10391=len(companies)`；机构申报人 **9,385**＝`filers13f.json n_filers=9385`；明星投资人 **43**＝`form13f-stars.json n_managers=43`（`stars` 数组为 top-8 卡片摘要，methodology 明示 "count = the full curated roster"，口径自洽）；政客交易 **2,812**＝`politician_trades_tx.json total=2812=len(transactions)`；Reddit 标的 **322**＝`count_declared` |
| 6 | 八 hub 页 as_of 披露 | **PASS**（1 项 P3 观察） | stakes 08-26＝`stakes_13g.as_of` ✓；events 08-26＝`form8k` ✓；ipo 08-27＝`ipo` ✓；executives 08-21＝`executives` ✓（另披露 def14a 08-27）✓；institutions 季度 2026-06-30×44＋ARK/主题 ETF 08-27＝面板 ✓（P3-1）；smart-money "14,878 · latest 2026-08-27"＝`smart_money.latest_date` ✓；congress 08-18/08-20＝`politician_trades(.tx).as_of` ✓；insiders 08-25＝`form4.recent` 最大申报日 2026-08-25 ✓（snapshot_ts 08-28，申报滞后属正常口径）。cot latest 08-18、korea_proxy 08-14 按源节奏诚实披露。filers13f 的 filed envelope as_of 08-21 在 `data-health.html`（"filers13f / filers13f.json / 2026-08-21 / 2026-08-28"）与 `filers.html` 在位 |
| 7 | /manager 页完整性 | **PASS** | `out/manager/` 43 页 ＝ roster 43，**双向集合相等**（roster−pages=∅，pages−roster=∅）；最短页可见文本 3,997 字符（无稀疏壳页）；Southpoint 抽查：`out/manager/0001319998.html` 非壳（可见 5,252 字符，含 Southpoint Capital Advisors LP、33 仓位 top 表 CIRCLE/DOORDASH/COINBASE…、$4.40B、filed 2026-08-14、13F/EDGAR 方法学披露），与 `form13f.json` roster 记录一致（macro 类，n_positions=33，total_value=4,395,933,780） |
| 8 | 诚实性抽查 5 页 | **PASS** | data-health：三类 **25 日更 / 9 源节奏 / 15 冻结** ＝ `data_health.json summary {n_daily:25, n_cadence:9, n_frozen:15}`，25+9+15=49=n_panels ✓，"推进冻结即泄漏"文案在位；api-docs：reserved-path 诚实文案（"status=planned are NOT built … no payload is served, as_of is null"）在位，`api_catalog.json` 49 endpoints ✓；ipo：**"发行价已解析 63 / 227 · 最新 ≤80 份已定价 · 有界封面解析 · 27.8%"** 与面板复算吻合（`offer_price_parsed=63`、`priced_filings=227`、`coverage_pct_of_priced=27.8`），**本轮修复的不变量 `confidence.exact(63) = offer_price_parsed(63)` 成立**；walk 契约 `last_walk(0) ≤ walk_cap(156)` 成立（源码注释明确 cap 为单走预算、`cumulative_walk=171` 为终身台账）；congress：党派分布 共和 1,007 / 民主 1,490 / 无党派未知 315（和=2,812）＝`politician_trades_tx.by_party` 精确吻合，"金额为法定披露区间，非精确值"＋"office-only, no name corroboration → null" 披露在位；market：korea_proxy 08-14 周度水位如实上墙 |

## 附加核查（任务上下文指定）

- **def14a persons " Age" 脏尾巴（本轮清零项，若复现即 P0）**：全站 1,502 页可见文本 `xxx Age` 模式 **0 命中**；`lineage_graph.json` 135 节点 / 840 边与声明一致（len=n_field），节点 label 以 " Age" 结尾 **0**，面板 as_of 2026-08-27。清零态保持。
- **stock_universe 自洽**：`n_stocks=1421=len(stocks)=out/stock/ 页数`。
- **轮 22 P2-2 junction 现状**：junction 现位于 `web/Aionis -> F:\ZCodeData\Aionis\web\out`（web 层），`out/` 内部无 junction；本轮扫描全程带 reparse-point 守卫。

---

## 发现项

### P3-1 institutions hub 页头未披露 filers13f 的 filed-envelope as_of（2026-08-21），以季度水位 2026-06-30 替代（带"季度"标签）

**证据**：`web/out/institutions.html` @char 35125 可见文本："覆盖管理人 43 · 申报总市值 $2.72T · **2026-06-30** · SEC 13F-HR · EDGAR · filed-date PIT · **季度** · 公共域"；全页检索 `2026-08-21` **不命中**。而 `filers13f.json as_of=2026-08-21`、`window.end=2026-08-21`；轮 22 报告曾记录"institutions 08-21 = filers13f ✓"。

**定性**：非失真、无超claim——页面明示"季度"并以 quarter 水位（2026-06-30，×44 处）披露，ARK/主题 ETF 子面板各自如实披露 08-27，CIK 核查日 08-22 如实标注；filed envelope as_of 在 `data-health.html` / `filers.html` 仍在位。属**披露元素跨轮漂移**（轮 22 页面曾含 08-21，轮 23 该元素不在 institutions hub 上），信息在站点其它层可得。

**建议（一句话）**：institutions hub 页头 KPI 行补一枚 filed-envelope as_of 徽标（如 `截至 2026-08-21（filed）`），与 data-health 层口径对齐，消除跨页口径二义。

### P3-2 ipo 面板 `offer_price_meta.requests.last_walk` 导出终值为 0（轮内过程记录为 14）

**证据**：`web/out/api/v1/panels/ipo.json` → `offer_price_meta.requests = {task_budget:170, cumulative_walk:171, walk_cap:156, last_walk:0}`；页面 `ipo.html` 明示 "最新 ≤80 份已定价 · 有界封面解析 · 27.8%" 并指引预算披露至 `offer_price_meta.requests`。源码 `scripts/export_terminal_data.py:3814-3819` 明确 `last_walk = requests_this_walk`（单走计数）、`walk_cap` 为单走预算、`cumulative_walk` 为终身台账；`scripts/form_ipo_price_parse.py:19` 契约为 `last_walk <= walk_cap`。

**定性**：构建忠实镜像面板，契约不变量（`last_walk ≤ walk_cap`：0 ≤ 156 ✓；`confidence.exact = offer_price_parsed = 63` ✓）全部成立——**非构建缺陷**。终值 0 与轮内过程值 14 的差异最可能为末次 cache-hit 走（未发生新请求），属数据 lane 需确认的面板状态项，仅登记备查。

**建议（一句话）**：数据 lane 确认末轮 13G/ipo 重跑是否整走 cache-hit（`requests_this_walk=0` 合法）；若是，无需任何改动。

---

## 通过项明细（证据样例）

抽样引用格式 `路径 @字符偏移: 片段`（构建 HTML 为单行压缩产物，行号恒为 1，故以字符偏移定位）：

- `web/out/dashboard.html @36285: Reddit 标的||322|` ＋ `@36448: 已载 100|`（1c）
- `web/out/ipo.html @40213: 发行价已解析|…` ＋ `@40532: 27.8|%|`（8）
- `web/out/stakes.html @31921: 2026-04-30→2026-08-26|`（6，窗口端点=面板 as_of）
- `web/out/institutions.html @35125: 覆盖管理人| |43| ·| |申报总市值| |$2.72T| · |2026-06-30|`（6/P3-1）
- `web/out/data-health.html @55321: filers13f||filers13f.json||… 2026-08-21 … 2026-08-28`（6）
- `web/out/api-docs.html @115662: reserved future location, no payload is served, as_of is null`（8）
- `web/out/smart-money.html`（剥标签可见文本）："14,878 · latest 2026-08-27"（6）
- `web/out/congress.html`（剥标签可见文本）："2,812 · 94 · 2026 2026-08-20"；"共和 1,007 民主 1,490 无党派/未知 315"（8）
- `web/out/manager/0001319998.html`（剥标签可见文本 5,252 字符）："Southpoint … CIRCLE INTERNET GROUP INC … COINBASE GLOBAL INC …"（7）

## 零修复承诺兑现

本轮未修改任何生产文件。全部操作为只读静态分析（Python 只读扫描脚本存放于 `data/cache/audit_r23/`，
gitignored 不提交 + git 只读命令）；本报告与 findings.json 为仅有的两个新建文件。未触碰
`docs/code-review/`（并发 session 领地）、`state/`、`data/`（除只读缓存目录）、ledger/frozen/config/prereg/OOS；
未执行 fetch/build/export，未 push。
