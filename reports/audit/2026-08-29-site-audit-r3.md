# 全站静态审计轮③(r3,post-㉕ 增量面优先)— 2026-08-29

**性质**：AUD-08 VERIFY 审计（单进程纪律下本轮唯一 audit agent；**零修复、只查证**——发现项仅开列，由主线/后续 dev 处理）。任务书：`tasks/active/TASK-AUD-08-site-audit-r3.md`。

**运行位置说明（透明披露）**：审计 agent 的写工作区为 git worktree `F:\ZCodeData\Aionis-wa1`（分支 `agent/aud8`）。任务书（主仓未跟踪文件）与 `web/out/` 构建产物（`web/.gitignore:6` 忽略 `out/`，不随 worktree 共享）实际位于主仓 `F:\ZCodeData\Aionis` 同名路径；两 checkout 位于**同一 commit `0633dab`**，故 `out/` 产物与本轮审计的源数据完全一致。本轮对上述输入**全程只读、零写、零网络**；全部写操作（本报告 + 原子 commit）仅落在 `agent/aud8`。

## 基线

| 项 | 值 |
|---|---|
| HEAD（审计时） | `0633dab`（`agent/aud8`；主仓 main 同点）——`chore(data): local refresh sweep — PTR tx complete (2811 tx/94 members), 13F dir re-window, derived panels re-exported` |
| 构建产物 | `web/out/` **1,503** 个 `.html`（= 根级 39 + `stock/` 1,421 + `manager/` 43）；全文件宇宙 **15,129** 个文件（html+txt+json+svg）；`out/` 内部 **0** junction/reparse point（全程带 reparse-point 守卫遍历） |
| 数据水位 | PTR 2,811 笔 / 94 议员（`politician_trades_tx.json`，as_of 2026-08-18）；13F 目录重开窗 `2025-09-03 → 2026-08-21`（`filers13f.json`）；派生面板重导出 executives / party_index / def14a_persons（as_of 08-21，def14a 08-27）；`data_health.json` snapshot **2026-08-28T17:55Z** |
| 宇宙 | `stock_universe.json` n_stocks=**1,421**（us 492 / cn 929）＝`out/stock/` 页数 1,421，**双向集合相等**（pages−universe=∅，universe−pages=∅） |
| 方法 | Python 一次性全量扫描（1,503 页）：剥 `<script>/<style>/注释` 后取可见文本；8 项清单全查；`dict.ts` 全键集合差（含多行值）；面板 JSON 数字复算与页面披露逐字比对；8 页 as_of 抽样。脚本摘要见附录 |

## 结论概览

**8/8 审计项 PASS。发现 P0×0、P1×0、P2×0、P3×3（2 项新观察 + 1 项自轮㉒顺延，均非失真/无超claim）。**
增量面（/atlas、/track HorizonRobustnessCard、/dashboard、8 个刷新数据页）全部通过调和复算；本轮刷新带入的新 ticker 链接**未产生任何宇宙外死链**（DEV-K 回归形态 0 复现）；轮㉒ 修复项保持修复态；轮㉒ P3-1（institutions 页头缺 filed-envelope as_of）**本轮已在页面上修复**。

---

## 逐审计项结果（8 项清单）

| # | 审计项 | 结果 | 关键数字 |
|---|---|---|---|
| 1 | 渲染垃圾（body 剥 script 后可见 `undefined`/`NaN`/`[object Object]`/`Infinity`） | **PASS** | 全站 1,503 页可见命中 **0/0/0/0**。非空转证明：原始 HTML `undefined` 出现均值 **59.66 次/页**（300 页抽样），全部位于 `<script>`（RSC flight payload）内，剥脚本后可见 **0**；`track.html` 原始 51 次（与甄别规则基线 ~51 一致），可见 0 |
| 2 | 标题语义（每页恰一 h1、无跳级；/atlas 与 /track 新面重点） | **PASS** | 1,503 页中 **1,502 页恰一 h1、0 页多 h1、0 跳级**；唯一例外 `index.html` 无 h1＝客户端重定向桩（见 P3-1，非内容页）。/atlas h1 唯一（sr-only 模式，可见标题"研究图谱"为其伴奏结构，合法 a11y 模式）；/track h1 唯一 |
| 3 | 死内链 + ticker 宇宙门（DEV-K 回归形态） | **PASS** | 48,329 个 `<a href>`：内链可解析 **42,958**、**死链 0**（对照 out/ 全文件宇宙逐一解析）；外链 2,498（github.com 1,568 / sec.gov 748 / house clerk 150 / 新闻源等）；锚点/其它 2,873。`/Aionis/stock/<TICKER>` 链接 **1,407** 个、唯一 ticker 全部 ∈ 宇宙 1,421，**宇宙外 0**；/atlas 与 /track 新卡唯一内链各 30 条，全部可解析（含 `track#evidence` 锚） |
| 4 | img alt | **PASS** | 全站 `<img>` 缺 `alt` **0** |
| 5 | 空交互元素 | **PASS** | `<a href>`/`<button>` 无文本、无 aria-label/title、无图标子元素 **0** |
| 6 | 重复 id | **PASS** | 1,503 页中页内重复 id **0** |
| 7 | tabindex | **PASS** | 正 tabindex / 非数值 tabindex **0** |
| 8 | 表单标签 | **PASS** | 表单控件 1,424 个（stock 页搜索框 ×1,421 + 导航搜索等），缺关联 label/aria **0**（hidden/submit 类按钮豁免口径） |

## i18n 对称性（dict.ts 全量，含多行值）

| 项 | 结果 |
|---|---|
| zh / en 键数 | **1,162 / 1,162**（轮㉒ 为 1,095/1,095，本轮 +67） |
| 双向差集 | zh−en = ∅，en−zh = ∅ |
| 值非空 | 3 处空值，全部为"空前缀/后缀"设计模式（见 P3-2）：`stock.live.updated.prefix`（zh=""、en="updated "）、`stock.live.chart.samples.prefix`（两侧均=""）、`overview.cockpit.heat.count_pre`（zh="共"、en=""）——渲染层面均成立（前缀拼接数字），仅任务书"值非空"字面口径未达，定级 P3 |
| atlas*/track.* 新键族 | **63 键**，zh/en 双语齐全且非空，**0 缺失** |
| track.horizon.* | **12 键**全覆盖（title/desc/note/asof/allholds/6 列头/2 verdict），双语逐键在位 |

## as_of 披露抽样（8 个刷新数据页，页头计数窗/水位线 ↔ 面板 JSON）

| 页 | 页面披露 | 面板 JSON | 判定 |
|---|---|---|---|
| congress | "2,811 · 94 · 2026-08-18"；党派 共和 1,006 / 民主 1,490 / 无党派未知 315（和=2,811）；旧值 2,812 已无残留 | `politician_trades_tx.json` total=2811、n_members=94、as_of=2026-08-18、by_party R1006/D1490/unknown315 | **PASS** |
| executives | 2026-08-21 与 def14a 2026-08-27 同时披露 | `executives.json` as_of=2026-08-21；def14a 08-27 | **PASS** |
| stakes | 窗口 2026-04-30→2026-08-26 | `stakes_13g.json` window{start,end} 逐字 | **PASS** |
| filers | filed envelope 2026-08-21；重开窗起点 2025-09-03 在位；9,385 | `filers13f.json` as_of=2026-08-21、window 2025-09-03→2026-08-21、n_filers=9385 | **PASS** |
| ipo | "发行价已解析 63 / 227 · 最新 ≤80 份已定价 · 有界封面解析 · 27.8%"；as_of 08-27 | `ipo.json` offer_price_parsed=63、priced_filings=227、coverage_pct_of_priced=27.8、as_of=2026-08-27；不变量 `confidence.exact(63)=offer_price_parsed(63)` 成立 | **PASS** |
| smart-money | "14,878 · latest 2026-08-27" | `smart_money.json` total_filings/latest_date | **PASS** |
| reddit | 322 / 100 / 2026-08-28 | `reddit_trending.json` count_declared=322、n_rows=100、as_of=2026-08-28 | **PASS** |
| data-health | snapshot 2026-08-28；三类 25 日更/9 源节奏/17 冻结 | `data_health.json` snapshot_ts 2026-08-28T17:55Z；summary 25/9/17 | **PASS** |

## 数据-呈现调和（复算记录）

**1. /track HorizonRobustnessCard 四相数字 ↔ `horizon_robustness.json` 逐字 — 24/24 全对**
渲染（4dp 差分/CI、3dp DM p，舍入口径一致）：B arm_state `+0.0008 [-0.0078,0.0094] 0.856 | -0.0047 [-0.0157,0.0064] 0.407`；C arm_macro `-0.0021 [-0.0162,0.0119] 0.777 | +0.0019 [-0.0121,0.0158] 0.810`；D arm_rel `-0.0018 [-0.0129,0.0094] 0.771 | -0.0048 [-0.0164,0.0068] 0.419`；E1 arm_prop−arm_base_self `+0.0016 [-0.0088,0.0121] 0.778 | -0.0020 [-0.0107,0.0067] 0.629`。JSON 逐字段（mean_diff/ci_lo/ci_hi/dm_p_mbb ×4 phase ×2 horizon）舍入后逐一吻合；判定徽标 h10/h42 全"null 保持"＝JSON `null_holds` 全 true；页脚"全部 phase × 两个 horizon：null 保持"＝`horizon_robust_all:true`；"数据日期 2026-07-30"＝`source_ts`。表头文案 h=10/h=42 与 JSON `horizons:[10,42]`、冻结 h=21 与 `frozen_confirmatory_horizon:21` 一致。

**2. /atlas 稳定条 Δ 复算 — 9/9 精确复现**
由 `ic_monthly.json`（66 行）按页面口径（前半 2021-01→2023-09 / 后半 2023-10→2026-06，均值仅计有数据月份）复算：US 前半 -0.0157、后半 +0.0267、**Δ +0.0424**（后半 32 个数据月，2026-06 US 为 null，页面"均值仅计有数据月份"注记如实覆盖）；CN -0.0584 / +0.0054 / **Δ +0.0638**；US+CN -0.0347 / +0.0218 / **Δ +0.0565**。与渲染三行六数逐字一致。

**3. /atlas 语境行 t≈-0.70 复算 — 成立**
页面披露点估计 -0.0088、95% CI [-0.0336, 0.0159]（＝`metrics.json` combined_ic/ci_lo/ci_hi/p 0.484/n 71 逐字）。由 CI 反推：全宽 (0.0159−(−0.0336))=0.0495，SE≈0.0495/3.92=0.012628，t=−0.0088/0.012628=**−0.6969 ≈ −0.70** ✓，且页面明示"展示性推导……非模型输出"——口径诚实。同期披露 Harvey-Liu-Zhu t>3.0 阈值对照，NULL 结论未因对照改变。

**4. data_health summary 复算 — 4/4 数 + 51/51 行**
由 `panels[]` 的 `category` 字段直接重算：frozen **17** / daily **25** / cadence **9**，25+9+17=**51**=n_panels，与 summary 及页面三块（25 日更 / 9 源节奏 / 17 冻结）逐字一致；51 个面板的 **file+as_of+exported_at 在页面 51/51 全部可对**（rows 计数列本轮未在该表渲染，披露范围＝新鲜度/水位，见"边界注记"）；三类分区成员归属逐一核对：25/9/17 各自段内无错置。/atlas 页头 "51 panels · 25 daily / 9 cadence / 17 frozen" 同步一致。

**附加抽查**：/atlas 月度热力数据表（无障碍降级）66 行＝len(ic_monthly)=66，抽 5 行（2021-01/2023-06/2025-05/2026-03/2026-06）4dp 逐字吻合（含 2026-06 US 诚实 "—"）；图例在位（"|IC| 色标：≤0.05 弱 → ≥0.30 强（围绕零对称）"+"蓝=负、橙=正，色盲安全"）；页脚 "66 个月 · 2021-01 → 2026-06"。/dashboard StatBand 五数 10,391 / 9,385 / 43 / 2,811 / 322（+"已载 100"）＝companies_dir n / filers13f n_filers / form13f-stars n_managers / politician_trades_tx total / reddit count_declared 全对。

## 附加核查

- **index.html（站点根 `/`）**：0 可见字符、无 h1 的 `__next_error__` 壳，flight 内含 `NEXT_REDIRECT;replace;/dashboard;307`——这是 `src/app/page.tsx` `redirect("/dashboard")` 在 `output:export` 下的标准产物：带 JS 访问 `/Aionis/` 由客户端路由 replace 落 /dashboard；无 meta-refresh 兜底 → 无 JS 场景白屏。源码自建站初始 commit `c80838a` 未变，**非本轮回归**，定级 P3-1。
- **stock_universe 自洽**：n_stocks=1,421=len(stocks)=out/stock 页数 1,421，集合双向相等；构成本轮 us 492 / cn 929。
- **轮㉒ 修复回归复验**：① stock 宇宙门 0 死链（保持）；② 哨兵 ticker 0 命中、可见 NULL 均为诚实 null 语义（保持）；③ Reddit 就近披露 "已载 100" 在位（保持）。
- **轮㉒ P3-1 状态**：`institutions.html` 现同时披露季度水位 2026-06-30（×44）**与** filed-envelope 2026-08-21（@char 36195）——**已修复**。
- **轮㉒ P3-2 状态**：`ipo.offer_price_meta.requests` 本轮 {task_budget:170, cumulative_walk:171, walk_cap:156, last_walk:0}，终值仍 0；契约不变量 `last_walk(0) ≤ walk_cap(156)` 成立、`confidence.exact(63)=offer_price_parsed(63)` 成立——构建忠实，数据 lane 确认项**顺延**（P3-3）。

---

## 发现项

### P3-1 站点根 `index.html` 为无 JS 兜底的客户端重定向桩（无 meta-refresh、无 h1、0 可见字符）

**证据**：`web/out/index.html` body 可见文本 0 字符；`<html id="__next_error__">`；flight payload `index.html @11335: NEXT_REDIRECT;replace;/dashboard;307`；head 保留根 layout 的 title/og（"Aionis — 反泄漏选股研究终端"）。源 `web/src/app/page.tsx` = `redirect("/dashboard")`（自初始 commit `c80838a` 未变）。全站唯一"无 h1 + 空壳"页。

**定性**：`output:export` 对 `redirect()` 的标准产物，带 JS 一切正常；无 JS/爬虫场景下落地页空白且无静态跳转兜底。非失真、非回归、非增量面缺陷。

**建议（一句话）**：将根页改为静态 `<meta http-equiv="refresh" content="0;url=/Aionis/dashboard">` + 可见链接的极简落地页（或 canonical 指向 /dashboard），消除无 JS 白屏与根路径 SEO 空转。

### P3-2 i18n 三处空值键（空前缀/后缀设计模式），任务书"值非空"字面口径未达

**证据**：`web/src/i18n/dict.ts` — L1043 `stock.live.updated.prefix: ""`（en L2274 "updated "）；L1048 `stock.live.chart.samples.prefix: ""`（en 同空）；L1577 `overview.cockpit.heat.count_pre: ""`（zh L346 "共"）。用法均为数字前后缀拼接（`stock-view.tsx:469`、`live-price-chart.tsx:145`、`overview.tsx:1032-1033`），空串渲染成立、无占位符外泄。

**定性**：键集合 1,162/1,162 完全对称，双语渲染无缺陷；属"空 affix 是否允许"的口径问题，非功能/可访问性缺陷。

**建议（一句话）**：若希望审计口径"值非空"可机检，给三键填入中性空格占位符或在 i18n lint 中白名单 `*.prefix/*.pre/*.suf` 类 affix 键。

### P3-3（自轮㉒ P3-2 顺延）`ipo.offer_price_meta.requests.last_walk` 导出终值仍为 0

**证据**：本轮面板值 {task_budget:170, cumulative_walk:171, walk_cap:156, last_walk:0}；页面披露与契约不变量均成立（last_walk 0 ≤ walk_cap 156；confidence.exact=offer_price_parsed=63）。

**定性**：非构建缺陷；最可能为末次整走 cache-hit（未发生新请求）。属数据 lane 待确认项，维持登记备查。

**建议（一句话）**：数据 lane 确认末轮 ipo/13G 重跑是否整走 cache-hit（`requests_this_walk=0` 合法）；若是，关闭该项。

---

## 通过项明细（证据样例）

抽样引用格式 `路径 @字符偏移: 原始 HTML 片段`（构建产物为单行压缩；偏移为本轮 raw HTML 实测）：

- `web/out/index.html @11335: NEXT_REDIRECT;replace;/dashboard;307`（P3-1）
- `web/out/track.html @64327: Horizon 稳健性` ＋ `@67022: +0.0008`（调和 1）
- `web/out/atlas.html @35855: 51 panels` ＋ `@123139: 样本期稳定性` ＋ `@128550: t ≈ -0.70`（调和 2/3）
- `web/out/data-health.html @33516: 2026-08-28`（as_of 抽样；51/51 行对账）
- `web/out/dashboard.html @36456: 10,391`（StatBand 五数）
- `web/out/ipo.html @41153: 发行价已解析`（63/227/27.8 与面板逐字）
- `web/out/institutions.html @36195: 2026-08-21`（轮㉒ P3-1 修复在位）
- `web/out/congress.html`（剥标签可见文本）："2,811 · 94 · 2026 2026-08-18"；"共和 1,006 民主 1,490 无党派/未知 315"（和=2,811）

## 边界注记

- `data-health.html` 面板表的 rows 计数列本轮未渲染（披露粒度=每面板 as_of/exported_at/分类）；rows 值仍经 JSON 侧 len() 抽查（如 politician_trades_tx 2,811、stock_universe 1,421）与页面他处披露吻合，不计缺陷。
- 本轮页面计数 1,503（较轮㉒ 1,502 +1，根级 38→39）；构成 39 根级 + stock 1,421 + manager 43，stock/manager 与轮㉒ 相同。
- 审计零修复：未改任何生产文件、未跑 next build、零网络、未动测试；报告单文件原子提交于 `agent/aud8`。

## 附录：扫描脚本摘要（未提交，工作于临时目录）

- `scan_r3.py` — reparse-point 守卫 `os.walk` 全文件宇宙（15,129）；逐页取 `<body>`，剥 `<script>/<style>/注释` 得可见文本与结构 HTML；8 项检查：字面量垃圾（词边界、大小写敏感）、h1 计数与标题层级序列、`<a href>` 全量解析（候选：精确/`+.html`/`+index.html`/`+.txt`/`+.json`；base 前缀 `/Aionis/` 剥除）、`/Aionis/stock/<T>` 宇宙门（`stock_universe.json` 1,421）、img alt、空交互元素（文本+图标+aria 三重豁免）、页内 id 重复、tabindex、表单标签（aria/label-for/包裹三路豁免）；另抽 300 页统计原始 `undefined` 均值作非空转证明。
- `i18n_full.py` — `dict.ts` 按 zh/en 块偏移 + `"k":"v"` 全文正则（含多行值）解析，双向差集 + 空值 + atlas/track 键族覆盖。
- `recompute1.py`/`dh_rows*.py`/`asof_check.py`/`carryover.py`/`ipo_fields.py` — ic_monthly 半样本均值与 Δ 复算、metrics CI→t 反推、data_health categories 重算与 51 行/分区成员对账、8 页 as_of 抽样、r23 顺延项状态。
