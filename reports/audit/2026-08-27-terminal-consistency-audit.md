# 终端全站静态一致性审计 — 2026-08-27

**任务**: TASK-DISP-VERIFY（只查证，零修复）。**基线**: `web/out/` 当前构建，1,501 页
（Next 16 静态导出，basePath=`/Aionis`，扁平 route.html 布局；`/stock/[t]`、`/manager/[cik]`
目录式）。**动机**: ⑰–⑲ 三轮 ~25 commits 合入后的首次全站扫查。
**配套机器可读发现项**: `reports/audit/2026-08-27-terminal-consistency-findings.json`。

---

## 1. 执行摘要

| # | 审计项 | 结论 | 发现数 |
|---|--------|------|--------|
| 1 | 渲染垃圾全站扫 | **发现 1 处**（stakes.html 可见 `[object Object]`）；undefined / NaN / Infinity / 0月NaN日 可见文本 0 处 | 1 |
| 2 | 内链完整性 | **失败** — 死链 54 个 distinct / 1,536 实例（其中 `/Aionis/manager` 占 1,421） | 2 |
| 3 | i18n 对称性 | **PASS** — zh/en 各 1,189 键，差集双向为空，无重复键 | 0 |
| 4 | StatBand 数据调和 | **PASS** — 五数字全部与承诺面板对账一致（含 +2 后明星投资人 = 42） | 0 |
| 5 | 新鲜度披露（10 页样本） | **9/10 PASS**；insiders.html 无页级 as_of 披露；theme_signals 2026-06-30 属 H1 冻结门、显式披露 → PASS | 3 (P3) |
| 6 | basePath 前缀完整性 | **PASS** — 全站 `src=`/`href=` 绝对路径违规 0 条 | 0 |

合计：**P0 × 0 · P1 × 2 · P2 × 1 · P3 × 4**（P3 含一条源码注释漂移附注）。

---

## 2. 方法与样本量

- 扫描器：临时脚本 `data/cache/audit_tmp/scan.py` + `freshness.py`（gitignored，
  本审计专用、随本报告一并声明；零改动被审计文件）。逐文件读文本、正则扫描；
  `<script>`/`<style>`/HTML 注释先剥离再扫**可见文本**，脚本载荷单独计数不作为发现。
- 样本量：**全量 1,501 HTML**（项 1/2/6 无抽样）；i18n 全量键集比对；项 5 为 10 页
  定向样本（覆盖 daily 面板展示页）+ dashboard/stakes 等附带观察。
- 死链判定含**大小写敏感复核**（GitHub Pages 部署区分大小写；Windows 本地默认
  不敏感，已用精确文件名集合二次验证，54 个死链在 case-sensitive 下仍然全灭）。
- 外链只做格式校验（scheme/host 结构），未发起网络访问（politeness + 边界约束）。

---

## 3. 逐审计项结果

### 3.1 渲染垃圾全站扫 — 1,501 页全量

| 模式 | 可见文本命中 | 脚本/JSON 载荷内命中（非发现） |
|------|--------------|-------------------------------|
| `undefined` | 0 | 89,529（RSC flight payload / 内联脚本序列化，属数据通道非渲染层） |
| `NaN` | 0 | （含于上述载荷环境） |
| `[object Object]` | **1** ← 见 AUD-T2 | 0 |
| `Infinity` | 0 | 0 |
| `0月NaN日` | 0 | 0 |

唯一可见命中人工裁定：

```
web/out/stakes.html（单行压缩，byte offset≈首屏 hero）：… SC 13D 主动举牌与 SC 13G 被动大额持股披露 · 15,982 13G · [object Object]
```

非法文案（"undefined behaviour" 类）排除：无可疑合法用法——唯一命中即真缺陷。

### 3.2 内链完整性 — 全量 674 distinct 内链 / 50,489 实例

解析规则：`href="/Aionis/x"` → 依次尝试 `out/x`、`out/x.html`、`out/x/index.html`
（strip basePath、去 query/fragment），case-sensitive 存在性判定。**死链全列**：

**(a) `/Aionis/manager` × 1,421 —— 每一张 stock 页各 1 次（stock 页共 1,421 张，覆盖率 100%）**

```
web/out/stock/AAPL.html: <a … href="/Aionis/insiders">内部人交易</a>
                          <a … href="/Aionis/manager">明星基金经理</a>   ← 目标不存在
```

根因（仅定位、未修复）：`web/src/components/stock/stock-view.tsx:147` 硬编码
`<Link href="/manager">`，而路由树只有
`web/src/app/(dashboard)/manager/[cik]/page.tsx`，无 index `page.tsx`，
静态导出因此不产出 `out/manager.html`（仅有 42 张 `out/manager/<cik>.html` 深页）。

**(b) 死亡股票深链 `/Aionis/stock/<T>` — 53 个 distinct / 115 实例，分布于 6 个 hub 页**

| 载体页 | 实例数 | 代表 tickers |
|--------|--------|--------------|
| confirmation.html | 48 | ADVB CALC CATO CDT CDTG CLGN CUE DGNX DXST GPUS GRNT HHS IMMR INLF IOTR JCTC LBRDA LNC LONA MANE MCRP MED NCI NNDM NRDY PALX PHG RMCO SCOR SDEV SLMT UUU VTAK WATR XXII ZJYL |
| smart-money.html | 48 | 同上集合（每 ticker 双载体） |
| congress.html | 16 | BRK.B BWXT DEO ESAB FMAO FWONK GOOGN LPLA LTH OGN PINS SPCX VSNT 等 |
| events.html / executives.html | 各 1 | BRK-B |
| reddit.html | 1 | SNDK |

机制：hub 页按面板行生成跨链，但目标 ticker 不在 1,421 页的 stock 导出宇宙
（`api/v1/panels/stock_universe.json` n_stocks=1421 与导出页数精确一致）。特别注意
BRK 家族（BRK-B / BRK.B 两种拼写均无页面）与 SNDK（已更名）这类真实世界变更用例。
53 个 ticker 清单与逐链载体见 JSON 附档 `dead_stock_links` 字段。

**(c) 外链格式抽查**：全站 2,532 条外链（github.com 1,566 / sec.gov 753 /
disclosures-clerk.house.gov 150 / wallstreetcn 55 / 其余官方源各 1），格式全部合法
（http(s)/mailto 且 mailto 均含 @），0 malformed。未发起网络访问。

### 3.3 i18n 对称性 — PASS

`web/src/i18n/dict.ts`（2,486 行）：zh 段 1,189 键 / en 段 1,189 键；
`zh−en = ∅`、`en−zh = ∅`；两段各自无重复键。通过。

### 3.4 StatBand 五数字调和 — PASS

`web/out/dashboard.html` StatBand（labels per dict.ts `overview.stat.*`）逐一回对
`web/out/api/v1/panels/` 下承诺面板原始长度（非仅 data_health 二手值）：

| StatBand 数字 | 页面显示 | data_health.rows | 源列表实测 | 判定 |
|---------------|----------|------------------|-----------|------|
| 上市公司 companies_dir | 10,387 | rows=10,387 | companies_dir.json `companies[]` len=10,387 | ✅ |
| 机构申报人 filers13f | 9,385 | rows=9,385 | filers13f.json `filers[]` len=9,385 | ✅ |
| 明星投资人 form13f-stars | **42** | form13f_stars rows=8（curated 表） | form13f-stars.json `n_managers`=42；form13f.json `managers[]` len=42 | ✅（+2 Corvex/GAMCO 已入数） |
| 政客交易 politician_trades_tx | 2,812 | rows=2,812 | transactions[] len=2,812；买入 785+539+132=1,456 / 卖出 315+390+137+331+142+41=1,356 / 迟报 379 —— 与页面 "1,456 / 1,356 / 379" 三分项一致 | ✅ |
| Reddit 标的 reddit_trending | 290 | rows=100 | count_declared=290（ApeWisdom 信封申报值；n_rows=100 为实际可得首屏，页面方法学卡如实披露 "46/100 · 2026-08-23"，无补齐伪造） | ✅ |

代码契约注解（overview.tsx:385-393）自述其数据通路并有
`test_data_health_rows_reconcile_with_source_lists` 锚定——与本审计独立复算一致。

### 3.5 新鲜度披露 — 10 页定向样本

对照 `data_health.json` category=daily 面板 as_of（news_feed 2026-08-25、form4
2026-08-20、form8k/filing_stream/form_d/def14a/executives 2026-08-21、ipo 2026-08-26、
politician_trades 2026-08-18、politician_trades_tx 2026-08-20、reddit_trending
2026-08-23、korea_proxy(cadence) 2026-08-14、theme_signals(cadence) 2026-06-30 等）：

| 样本页 | 页面可见新鲜度锚点 | 与 data_health 一致？ | 判定 |
|--------|--------------------|-----------------------|------|
| news.html | 页级锚 `2026-08-25`（守卫带） | = news_feed as_of | PASS |
| market.html | 韩国代理卡 `1414.29 · 2026-08-14` | = korea_proxy as_of | PASS |
| reddit.html | `最新快照 2026-08-08`（诚实陈旧）+ 热度墙 `2026-08-23` | = reddit.latest_snapshot_ts / reddit_trending as_of | PASS |
| congress.html | 页级锚 `2026-08-18`（v1 PTR 流） | = politician_trades as_of；tx 卡自身年份粒度见 AUD-T6 | PASS（带注） |
| ipo.html | 页级锚 `2026-08-26`；Form D 窗口 `→ 2026-08-21` | = ipo / form_d as_of | PASS |
| executives.html | 页级锚 `2026-08-21`；DEF14A 窗口 `2026-04-27 → 2026-08-21` | ✓ | PASS |
| themes.html | **theme_signals 显式披露 `截至 2026-06-30`** + 注明"各主题独立来源，新鲜度不一（见每张卡的 as_of）" | = theme_signals as_of_date 2026-06-30，H1 冻结门诚实陈旧 | PASS |
| smart-money.html | 卡片窗口 `2026-04-27 → 2026-08-21`、`latest 2026-08-21` | = smart_money / stakes_13g as_of | PASS |
| insiders.html | **无任何页级日期披露**：仅月域 `2013-03..2026-08` 与行级 `MM/DD`；全文件 0 个 ISO 日期 | form4 as_of=2026-08-20 未展示 | **FAIL → AUD-T4** |
| events.html | 页级锚 `2026-08-21`；8-K 窗口 `2026-05-01 → 2026-08-21` | = form8k / filing_stream as_of | PASS |

附带观察：dashboard.html 卡片级 as_of 齐全（聪明钱 08-21 / 多空压力 08-04 / 最新举牌
08-21 / 近期 IPO 1,077·2026-08-26）；annual/quarterly/filers/force-camp 页级锚均为
2026-08-21 与各自 daily 面板一致；**stakes.html 无窗口/as_of 披露**（仅行级 MM/DD）→ AUD-T5。

### 3.6 basePath `/Aionis/` 前缀完整性 — PASS

全量扫描所有 `href="…"` / `src="…"` 中以 `/` 开头且不以 `/Aionis` 开头的绝对路径：
**0 条**（协议相对 `//` 同样为 0）。资源引用（/_next/* 链）均经 basePath 正确改写。

---

## 4. 发现项（严重度 / 证据 / 建议 lane）

### AUD-T2 · P1 — stakes.html 首屏副标题渲染出 `[object Object]`
- 证据：`web/out/stakes.html` 可见文本 `…13D 主动举牌与 SC 13G 被动大额持股披露 · 15,982 13G · [object Object]`（全站唯一渲染垃圾命中）。
- 影响：旗舰级 hub 页标题出现程序化垃圾串，损害终端可信度叙事。
- 建议 lane：display-integration（查 stakes 视图把对象直接插进模板串的位置；
  与本轮合入的举牌相关 commit 关联度高）。

### AUD-T1 · P1 — `/Aionis/manager` 站级死链 × 1,421（每张 stock 页）
- 证据：`web/out/stock/<ANY>.html` 导航 chip `明星基金经理 href="/Aionis/manager"`；
  `out/manager.html` 不存在；根因 `web/src/components/stock/stock-view.tsx:147` +
  缺失 `(dashboard)/manager/page.tsx` 索引路由。
- 影响：核心交叉导航 100% 断裂（点击必 404），是本轮最大绝对量缺陷。
- 建议 lane：display-routes —— 补 manager 索引页（或 chip 改指 `/Aionis/filers`
  / 最近的 stock 页管理器锚点）；一行级修复即可消 1,421 个实例。

### AUD-T3 · P2 — 53 个死亡股票深链 × 115 实例（6 个 hub 页）
- 证据：confirmation/smart-money 各 48、congress 16、events/executives/reddit 各 1；
  全清单（ticker × count × 载体位置）见 JSON `dead_stock_links`。
- 机制：跨面板 ticker ∈ 面板行但 ∉ stock 导出宇宙（1421 页）——BRK-B/BRK.B/SNDK
  等命名/存续变尤为代表性。
- 建议 lane：display-integration —— 渲染跨链前以 stock_universe 成员集过滤或降级为
  非链接文本；或在导出侧为外部热门 ticker 出占位诚实页（遵守"不猜测"边界）。

### AUD-T4 · P3 — insiders.html 缺页级 as_of 披露
- 证据：全页 0 个 ISO 日期/截至字样；data_health 有 form4 as_of=2026-08-20 可显示而未显示。
- 影响：daily 面板页违背兄弟页（其余样本页均有守卫锚）的新鲜度一致性约定。
- 建议 lane：display-i18n/views —— 补 ProvenanceAnchor 式日期锚。

### AUD-T5 · P3 — stakes.html 缺窗口/as_of 披露
- 证据：仅 EFTS 冻结说明（2024-12-17）与行级 MM/DD；15,982 条 13G 的采集窗口不可见。
- 建议 lane：同 AUD-T4，与 AUD-T2 同文件可一次处理。

### AUD-T6 · P3 — congress.html tx 卡时间粒度仅为年份
- 证据：`2,812 · 94 · 2026`；politician_trades_tx 的 as_of=2026-08-20 未在卡上呈现
  （页级锚 2026-08-18 是 v1 面板的日期，非 v2 的）。
- 影响：轻微——行级交易日仍可见；但双版本面板并存时锚点归属易误读。
- 建议 lane：display-views —— tx 卡加自属 as_of 微标。

### AUD-T7 · P3（附注，构建产物外）— overview.tsx 注释漂移
- 证据：`web/src/components/overview/overview.tsx:604` 注释 "40 in the committed panel"
  与现值 n_managers=42 不符（+2 后未同步文档性注释；运行时取的是 digest 数，数字正确）。
- 建议 lane：i18n-cleanup 任务顺手改注释；不影响产物正确性。

---

## 5. 方法可信度自评

**可信度较高处**
- 项 1/2/3/6 为全量扫描（1,501 页、674 distinct 内链 / 50,489 实例、两段全部键集），
  无抽样外推；死链经大小写敏感二次核验，贴合 GitHub Pages 实际部署语义。
- 调和用的是承诺面板**原始列表长度**而非 data_health 二手转述，五数三分项（买卖/
  迟报、party 计数）交叉求和全对上，出现巧合一致的概率极低。
- 垃圾扫按"剥 `<script>` 后可⾒文本"界定，规避 RSC flight payload 大量
  `undefined`/`NaN` 序列化噪声的假阳性（89,529 处脚本命中全部排除在裁定之外并留痕计数）。

**盲点 / 边界（如实列报）**
1. 静态导出的客户端 hydration 行为不在静态审计范围：理论上存在"SSR 文本干净、
   hydrate 后出错"的动态期垃圾，本次无法覆盖（需浏览器侧复核，超出 verify-only 边界）。
2. 外链只做格式校验、零网络访问——URL 真实可达性（如 SEC 链接的 DocID 有效性）未验。
3. 逐条人工裁定的段落里，我对每个非零命中做了判定，但对"零命中模式"只能保证
   正则模式的完备性，不能排除其他形式的垃圾串（仅限规格点名的五类模式）。
4. 新鲜度项为 10 页定向样本（覆盖 25 个 daily 面板中的主要展示页），非全量；
   stakes/company 目录等 cadence 页的陈旧披露依赖伴随观察补强。
5. Windows 文件系统大小写不敏感——虽已用精确名字集合复核，极端 NTFS 保留名冲突
   类假阴性理论残留概率极低但不为零。

---

## 6. 边界确认

零修复：被审计文件无一改动；本轮仅新建本报告 + 配套 JSON 两份文件 +
`data/cache/audit_tmp/` 下两个 gitignored 临时脚本。ledger / frozen config /
preregistration / OOS 管线：0 接触。不 push。
