# state/handoff.md — current-pass handoff

> **2026-08-15 业主裁决：发表线整体废除。** 项目不再有发表计划（无 arXiv 上传、无 venue 选择、
> 无投稿）。所有发表工件已按 move-don't-delete 归档至 `archive/`（manuscript/、quarto-site/、
> docs/methods-and-results-draft(-en).md、replication-availability.md、frontier_positioning.md、
> publishable-unit-positioning / power-floor-literature-anchoring 报告）。本文件下方**历史条目**中
> 残留的发表字样仅为当时工作记录，一律不构成现存计划；所有"待业主：arXiv/venue"类待办已随本
> 裁决作废。当前主线：web 终端展示层 + GitHub Pages 实时数据更新；并行：Track A 因子生成器
> （新冻结面）、E3 forward-live（AUD-06 + 业主 GO）、glm-v4 key 有效性确认。

## 2026-08-21 小隐寺全形态路线图 + 三代理（H 成 / G-I 阵亡→主线接管）→ /events + /congress 上线

**方向文件**：`reports/design/2026-08-21-xiaoyinsi-full-parity-roadmap.md`（17 路由对齐矩阵、P0-P3 阶梯、Aionis 五特色增层；小隐寺自身空壳 /companies+/annual+势力阵营未上线 = 填壳机会）。本轮 P0 三件全部关闭。

**三代理**：worktree ×3（junction 只挂 node_modules，**data/cache 不再共享**——上轮 rm -rf 穿透事故的预防）；H 全胜双 commit（`676b90d` cmdk 4 路由 + `5dc1c25` 68/118→94/118，归一化精确匹配 + 死链守卫）；G/I 阵亡于 [1308] 5h 限额 → 主线接管。

**/congress（`0679b92`，planned 清零）**：
- 尽调留证 `docs/data-intake-congress-stock-act.md`：Senate=Akamai 403；第三方 API G1 挂；House **两路验证取优**——CSRF HTML 搜索（无日期）被 **批量 FD.zip→FD.xml** 取代（日更索引、FilingType=P、**真 FilingDate**；与并发 session agent/politician a2f719b 交叉验证一致，其 worktree 未动只读引用）。v1=申报流级（member/office/**filing_date**/year/PDF 链），**交易明细在 PDF 内不解析不编造**；Senate blocked 诚实卡。
- 真实数据 874 PTR/144 人（2025:515+2026:359，2 请求 ~4s），as_of=2026-08-18。
- 毕业：_PLANNED_PANELS 空（列表保留共享定义）、`test_planned_disclosure_present_and_consistent` 改钉空集 + 毕业注释、CI 加 fetch 步。

**/events（`a714fcb`，EFTS 第三代）**：
- `form8k.py`：评分制主文档选择器——三次真拉失败模式（R1.htm XBRL 渲染件、a8-kex991q3.htm exhibit 名内含 8-k、q1fy27pr.htm press release 同分最短名）→ 0 分档=发行人-日期规范 `^[a-z][a-z0-9]*-\d{8}\.htm$` 或名含 8-k/8k（exhibit 检查 `ex\d` 任意位先行）。Item 正则清洗 nbsp+thin-space（`&#8201;` iXBRL 时代）。
- 23 事件/5 发行人/0 未分类；稀有重大优先单一归类 + 全 Item 列表保留；7-gate `data-intake-edgar-form8k.md`（评分表留档）；日更 manifest + CI fetch 步。

**验证链**：全套 pytest exit 0 + ruff 净（--exclude docs/code-review）+ tsc 0 + eslint 净 + build 26 路由（/events /congress ○ 预渲染）。

**踩坑**：① Windows 下 `cmd /c mklink` 在 Git Bash 需 `cmd //c "mklink ..."`（正斜杠转换吞参数→junction 静默不建）；② worktree pytest 走 `PYTHONPATH=<wt>/src + 主仓 venv python`（editable 安装指向主仓，不设即测旧码）；③ ruff E501 对字符串字面量内的行同样报——HTML fixture 靠折行解决（regex `[^>]` 跨行匹配不受影响）。

**遗留池**：roadmap P1（/ipo、/stars 目录+manager 详情页）→ P2（/news、/quarterly+/annual、/companies）→ P3（势力阵营=血缘图谱）；政客交易升级=House PTR PDF 解析（工程大，业主后议）；Senate 解封监控（Akamai）。

## 2026-08-20 (c) 三代理第二轮全胜：quickwins + CN 行业 + 13F → 集成上线

**三代理全部交付**（本轮无阵亡；边界纪律 + 增量提交指令生效）：
1. **D quickwins**：cmdk「热门个股」第 5 组（top10 多头+top3 空头，text-up/down 遵守涨跌约定）+ market_context 3 条 region:"cn" 语境事件（08-19 暴跌/宇树 IPO+460%/四中全会，新 type `ipo`）+「A 股」徽章。
2. **E cn-industry**：7-gate 全过（BSD 实证、vendor display-only 数据侧、G3 快照纪律）；baostock 走 lazy import + `uv run --with`（零 pyproject/lock 改动）；CN sector 4 tier→52 证监会行业组、`cn_tier` 列保留、退市诚实回退 tier；5194/5207 覆盖。**License 更正移交**：旧价格文档 MIT 引用有误（GitHub repo 404），权威=PyPI=BSD，已更正。
3. **F form13f**：12 明星管理人（CIK 实查、淘汰停报实体）；11 位最新季 2026-06-30；60 请求 2m20s；**EDGAR 13F XML value=整美元（非千美元）——SEC 网页惯例是错的，AAPL $253.79/股交叉验证钉死**；帧差键=(cusip,option_type) 防 title 漂移假信号；`/institutions` + 26×2 i18n；CUSIP→ticker 诚实 68/118。

**主线集成**：8 commits cherry-pick 零冲突；form13f 注册 cadence 面板 + as_of 提取器；13f/cn-industry 从 planned 毕业（剩 politician-trades）；`_sm_committed_extra` 传 committed_path（测试隔离）；**修复 A 遗留旧测试回归**（fixture 缺 accession——教训：**agent 改共享函数后必须跑全套 pytest，不能只跑其边界文件**）；CI `--with baostock` 接线；全套 pytest 首次 0 失败；部署 `32335991748` 绿。

**⚠️ 主线事故档案**：上轮 `rm -rf` worktree 穿透 junction 误删主仓 data/cache 大部 + node_modules（runs/ 冻结产物无恙、committed JSON 无恙、CI 独立缓存无恙）。node_modules 重装修复；cache 由 fetcher 渐进回填。**铁律：清 worktree 先 `cmd /c rmdir` 摘 junction 再删目录。**

**遗留候选**：政客交易 STOCK Act（唯一 planned，PDF/JSON 端点尽调待做）；CUSIP→ticker 覆盖 68/118 可提升；cmdk 页面组需补新路由（heatmap/institutions/data-health/api-docs）；i18n 孤儿 key；BACKTEST_MONTHS/HIG 密度（业主取舍）；研究线三门（E3/Track A/Track LLM）。

## 2026-08-20 (b) 三路子代理并行（业主指令）→ 全阵亡 → 主线接管 → 集成上线

**编排**：git worktree ×3（wa/wb/wc，junction 共享 data/cache 与 node_modules）。踩坑：**Turbopack 拒绝跨文件系统根的 node_modules symlink**——worktree 内 `next build` 必败（"Symlink node_modules is invalid"），tsc/eslint 可用；build 归主线集成。另一坑：**worktree 的 runs/ledger.jsonl 被 git CRLF 重签出 → sha256 pin 测试假红**（内容同、字节异），用主仓原文件覆盖即绿。

**子代理结局**：B 网络死（留完整 dict 键）；A/C 死于提供商 5h 限额[1308]（05:38 重置）。主线接管完成全部。

**A 的数据修复要点（真根因）**：EDGAR 日更索引按**每 listing**列 13D（主体+申报人实体都在）→ 旧行 ~40% 重复且零解析。修复三件套全离线（`_sm_ticker_maps` / `_sm_dedup_enrich` / `_sm_committed_extra`），实测 ticker 0/60→44/60。**验收教训：A 死在删除旧版函数之前，文件里有两个 `_refresh_smart_money_recent_only`——Python 静默用后定义的旧版，新实现全失效；接管时必须查重复定义**（本次主线删除后 44 测试才真正测到新路径）。

**交付四 commit（cherry-pick 后 865b4bd/cf04edf/20df473/2c8f48f + regen 07e9763）**：
1. `/heatmap`（手写 squarify，300 可点格、其他桶 342/779 诚实聚合、色随涨跌约定）
2. picks 集中度卡（等权板块 HHI + 档位徽章 + 分解条，US 0.089/CN 0.292）
3. smart_money 修复 + data_health.source_health + planned 三项（politician-trades/13f-holdings/cn-industry）+ api_catalog planned 端点
4. 视图接线：data-health 源健康卡+已规划卡；api-docs planned 虚线不可点

**集成**：dict.ts 自动合并；推送撞日更 0f2792a → rebase JSON 全冲突 → ours+合并码全量重生成（`_sm_committed_extra` 保住日更侧新行：latest 08-18、44/60 不回退——该函数正是为这个场景设计的）。confirmation 股票链接 0→36。

**验证链**：tsc 0 / eslint 净 / build 1,447 路由 / 44 契约 / ruff（排除并发 docs/code-review/）/ 浏览器实测（热力图 215×419px 格、HHI 实值、源健康+规划卡、回路 36 链）/ 部署 `32327579931` 绿 + 线上五页 200。

**边界**：display + 数据导出 lane；0 ledger/frozen/config/prereg/OOS。worktree 与 agent 分支已清理。

## 2026-08-20 (a) 终局定帧 + P0 三件套：涨跌色约定 / 回路闭合 / 实时指示器

**业主定帧（方向性）**：小隐寺 = Aionis 的最终目标形态；在其全形上**只做加法**（叠加反泄漏/溯源/可证伪特色），删减是以后的事。

**交付（display-only）**：
1. **涨跌色约定系统**：`--up/--down` 变量（浅/深 × intl/cn 四组合）+ `[data-colorconv="cn"]` + 工具类 text-up/down、bg-up/down、bg-up/down-soft（color-mix）、badge-up/down。10 个视图的**数值方向色**迁移（picks 概率条/评分/排名箭头/回测收益、stock 全套、overview RankChange、sectors 亲和条、positioning 净多空、themes 方向徽章+DIR_BAR、insiders 买卖+图表 fill=var(--up/down)、reddit 情绪徽章、market 总收益）。**语义色（信任 emerald/风险 rose）有意不迁**。头部 ColorConvToggle（实时预览箭头色）+ localStorage + 预水合内联脚本（防绿涨闪烁，next-themes 同款）。
2. **回路闭合**：insiders/reddit 表 ticker→个股页；smart-money 徽章链接就位。
3. **实时指示器**：live-prices `updatedAt` + 个股页 1s tick "X 秒前"（绝对时戳退 tooltip）。

**发现（预存缺陷，非本轮引入，待修）**：`smart_money.json` recent 60 行 ticker 全空、filer="申报人见原文"——`_refresh_smart_money_recent_only`（5ea6649）从日更索引合并的行丢失 ticker/filer 解析 → 回路在该面板自动降级 + stock_universe 佐证 join 拿不到 13D 计数。修复属日更 lane：recent-only 路径需带 ticker 解析。

**注意**：工作树出现并发 session 的未跟踪目录 `docs/code-review/`（7 个预存 E501）——不碰不提交，验证 ruff 以 `--exclude docs/code-review` 为准。

**验证链**：tsc 0 / eslint 净 / build 1,446 页 / 40 契约测试 / ruff（排除并发目录）净 / 浏览器实测色彩切换（cn 下 .text-up=lab(63.7,60.7,31.3) 红；intl=绿）+ 持久化 + "0 秒前 · 259.74"实显 + confirmation 子页链接计数（insiders 5 / reddit 1）。

## 2026-08-19 (u) 公共静态数据 API — 模仿小隐寺数据中台（不消费其数据）

**业主定帧**："不要直接抓取小隐寺数据，而是应该从模仿开始，以及小隐寺数据本身就有提供该项目 api 的使用说明"——即学其数据平台形态（统一 API + 每路径 x-status/x-license + 健康水位线），不碰其数据/接口。

**交付**：
1. **`api_catalog.json`**（`export_api_catalog()`，排 main() 最后、读 data_health）：26 端点 × {license, 一手来源, 新鲜度, as_of, path}。license 映射 `_API_LICENSE` 镜像 docs/data-intake-*（SEC/CFTC/FRED=公共域，Tiingo/Alpaca/Reddit=vendor ToS display-only，模型面板=repo MIT）；未映射 key 诚实 "unverified — do not ingest"（测试钉死不出现）。
2. **`web/scripts/build-api.mjs`**（`prebuild`，CI `pnpm build` 自动跑）：镜像 28 个面板 JSON → `public/api/v1/panels/` + 根级 catalog.json / health.json / **openapi.json**（OpenAPI 3.1：4 路径，`/api/v1/panels/{panel}` 带 26 个参数级 x-aionis-freshness/license/source/as-of，实时价 Worker 单列 server）/ README.md。产物 gitignored（`public/api/`）→ 部署 API 与终端面板同源、永不漂移。
3. **`/api-docs` 页**（参考组侧栏"数据 API"）：端点表（链接直开线上 JSON）+ 面板目录表（新鲜度 badge + license + 来源 + as_of，面板名→线上 JSON）+ curl/fetch 示例 + 反泄漏边界卡（研究摄入须过 7-gate；worker display-only 绝不进 OOS）。i18n zh+en。
4. **测试**：+2 契约（catalog 形状/全 license 非空/与 data_health 键集调和/worker note；披露 7-gate+GitHub Pages）→ 40 web 契约绿。

**踩坑（重要）**：`npx next build` **不触发** prebuild 生命周期（只 `pnpm build`/`npm run build` 触发）——本地验证先手动 `node scripts/build-api.mjs`；CI 无此问题。

**验证链**：tsc 0 / build 1,446 页 / eslint 净 / ruff 净 / 全套 pytest 0 失败 / 本地 curl 六端点 200 / IAB 实测 /api-docs 全渲染。

**边界**：0 ledger/frozen/config/prereg/OOS；未请求小隐寺任何端点；API 方法学自declares display-only + 7-gate 摄入门。

## 2026-08-19 (t) 小隐寺对照 + 个股下钻页 + 数据健康地图 + rank_change 跨区污染修复

**背景**：业主以 08-19 A 股暴跌（沪指 -2.40% 失守 3900、创业板 -6.26%、银行逆势、CPO/存储重挫、宇树 +460%）+ data.xiaoyinsi.com 全站为引，要求深度探索项目发展方向；随后授权"推进到满意为止，允许试错"。

**方向分析结论（浏览器实探小隐寺：首页/个股页/API docs）**：
- 八维度美股另类数据终端 + 统一数据中台（OpenAPI 3.1、X-API-Key、每路径 x-status/x-license、每日 Parquet 分区、/health 源水位线）——基建形态值得学（→ 本轮数据健康页），数据**不可用**（license 不透明，7-gate G1 挂）。
- 弱点 = Aionis 差异化机会：无 PIT/审计链、覆盖缺口（NVDA 13F"共 0 家"）、评分卡无溯源。
- E3 forward-live 价值被暴跌日放大（冻结 CN picks 主力=半导体，恰在风暴眼）但 **append-only 前向账本仍留业主显式 GO**，未擅启。

**交付（全部 display-only）**：
1. **`/stock/[ticker]`（1,421 页 SSG）**：US 492 + CN 929 冻结 OOS 最新月全覆盖。模型读数（score/rank X of N/percentile/rank_change/prob_up vs base_rate）+ 12 月评分 sparkline（均值/σ）+ 板块语境（区域板块表 standing）+ 佐证计数（smart_money/form4/reddit join）+ live 价（Worker display-only，CN 通）+ 切换器（客户端全宇宙搜索）+ NullDisclaimer + 冻结 badge + 方法学。`stock-universe.ts` 独立模块（553KB 不进共享 barrel——Turbopack 单 barrel=单共享 chunk 的既定教训）。入口：picks 表 + overview MiniPicks。
2. **`/data-health`**：26 面板 → 日更 9 / 源节奏 2 / 冻结 15；as_of 读面板自身字段（缺=诚实 null）；exported_at=lane 写入日；冻结框定"推进即泄漏，E3/新阶段是唯一合法前进"。侧栏守卫组。`export_data_health()` 排 main() 最后（读全部已导出 JSON）。
3. **rank_change 跨区污染修复**：`export_picks` prev 帧未过滤 region，US/CN 月末 61/87 重合 → 混合帧排名，US picks rank_change 最多偏 +929（症状：TROW 829 > n_region 492 的数学不可能值）。两处修（picks + stock_universe），picks.json 重生成（10 行修正，CN 当月未受染）。契约测试以 `|rank_change| ≤ n-1` 界钉死。

**验证**：38 web 契约测试（+5 新）绿；tsc 0；next build 1,445 页绿（stock SSG 10.9s/11 workers）；eslint 净；全仓 ruff 净；全套 pytest 0 失败；本地静态服务 + IAB 浏览器实测（data-health 三卡全渲染、海光个股页实测 live -7.26%、25+4 入口链接在 built HTML 验证）。

**边界**：0 ledger/frozen/config/prereg/OOS；未跑 research/forward；E3/Track A 未触。

**遗留候选（未做，有理由）**：cmdk 面板未加个股入口（1,421 项不可枚举，picks 入口已够）；政客交易（STOCK Act，一手源公共域可过 7-gate，PDF 解析工程量大，候选）；13F 机构持仓模块（EDGAR 公共域，中大型工程，候选）；A 股行业级分类（baostock，handoff (p) 既有评估，需 CI 协调）。

## 2026-08-16 (s) Apple HIG 设计语言重构（token 层，5 文件辐射全站）

**范式**：Clarity（SF 系统栈/双模式抗锯齿/蓝选区）× Deference（毛玻璃吸顶导航 + 同材质 StickyTabs = iOS 材质堆栈）× Depth（浅发丝边+双层柔影 / 深表面抬升，圆角 12px 基准）。

**改动**：globals.css（双主题 Apple token + 字体栈 + ::selection + 侧栏 source-list 蓝染）、app/layout.tsx（删 Geist 网络字体 → 系统栈）、(dashboard)/layout.tsx（header 毛玻璃吸顶 z-40）、sticky-tabs.tsx（top-16 同材质）、ui/card.tsx（ring → hairline border + 双层柔影，深色仅边框）。

**对比度账**（Node 核算 + 浏览器实测）：浅 muted-on-card 5.96、深 6.54、浅蓝 #006cd9 白上 4.9-5.1、深蓝 #0A84FF 卡上 4.66——全 AA。首版浅蓝 oklch(0.584) 只 4.36 → 加深至 0.545（text-primary 场景保护）。

**验证**：build 23/23 + 33 契约 + ruff；20 路由双主题零溢出；视觉模型三图审全过；部署 CSS 产物级终验（oklch 被压成 hex/lab，按 `--background:#f6f7f8` 等实锤）。

**遗留候选**（视觉模型建议，未做）：图表线色饱和度降至 systemGreen 柔和度（逐图调色，涉 10+ 图）；同屏密度/留白（内容取舍需业主裁决）。

**操作记录**：CSS 多闭括号 → Turbopack 报 `Unexpected }`（token 块替换时 old 串未含尾括号所致，1 分钟修）；IAB webview 后期 "guest not attached" → 部署验证降级为 CSS 产物 grep（等效结论）。

## 2026-08-16 (r) 用户旅程角色扮演 → cmdk 面板 + 模板死链清除 + 浅色一等化

**旅程发现（首访视角 + 三学科）**：
| 学科 | 发现 | 处置 |
|---|---|---|
| 设计学/心理学 | 首访"术语墙 + 无从下手"——无阅读序入口 | 面板"从这里开始"①-⑤ 编号导览 |
| 人体工程学 | 20+ 路由无键盘快速跳转；Ctrl+K 死 | 真 cmdk 面板（36 项 4 组） |
| 软件工程 | 模板死链 ~1310 行（palette/nav-secondary/seed/globe.json 互引但零活引用） | 全删（grep 复核零残留） |
| 软件工程 | `ui/command.tsx` CommandDialog 缺 `<Command>` 根 → cmdk context 崩（零使用从未暴露） | 按上游 shadcn 修复 + sr-only title 入 DialogContent |
| 设计学 | 浅色模式二等公民：muted 4.38:1（AA 不达标）、边框隐形 | token 0.556→0.502（5.5-6.0:1）、border 0.922→0.895 |
| —— | 404 ✓ / 深链 ✓ / 图表 tooltip 8/10 ✓ / EN 切换 ✓（残留中文=数据值） | 无需修 |

**轮子复用**：cmdk ^1.1.1 已在依赖（shadcn ui/command）——此前零使用且其 CommandDialog 是坏的；本轮修轮子+用轮子，未新增任何依赖。GitHub/Linear/Vercel 同款方案。

**验证链**：dev 复现崩溃→取栈→修复→面板开/搜索/回车导航/Esc 全实测；build 23/23 + 33 契约 + ruff 净；部署 `31955414141` 绿后部署站复验（面板 4 组 36 项 EN 模式在位、浅色 token 实测 lab42.23）。

**操作教训**：部署站验证时 localStorage 语言偏好（en）会改按钮 aria-label——按中文标签查询会误报缺失；Playwright click 偶发 webview 超时 → 读 rect 后 `cua.click` 坐标路径可靠。

## 2026-08-16 (q) 部署站视觉审计二轮（视觉模型 + DOM 实测）→ P0-P2 全落地

**审计双通道**（部署站 live，1440 + 375 双视口）：
- 视觉通道：逐屏截图 → `analyze_image` 盲审。**工具链要点**：`Read` 本地 PNG → CDN URL → 视觉模型；URL 必须**原样带反斜杠**传（改正斜杠破坏 UCloud 签名 → 1210 解析错误）。`emitImage` 在本环境不回流图像，此桥接是唯一视觉通路。
- 数据通道：`getComputedStyle` 采 lab/oklab 原始色（Tailwind v4 非 rgb；canvas 归一化技巧会被 debug-evaluate 副作用检查拒）→ Node 纯数学换算 WCAG。
- **视觉模型两条报告为幻觉**（"6 个 tab"、"regime 图无事件标注"——实际 4 tab、已有川普 ReferenceLine）：视觉结论必须 DOM 交叉核验。

**硬发现（本轮新增，此前 4 轮视觉审计未抓到）**：
1. **α 降透明 muted 文字 < WCAG AA**：行首列 3.29:1（α0.6）、表头 4.02:1（α0.7）、track 脚注 4.02:1。满透明 muted 6.9:1 达标 → 根因是 opacity 变体不是 token 本身。
2. **10/11px 中文小字 89 处**（th/脚注/徽章）< CJK 12px 下限。
3. **picks 9020px/16461px（10-20 屏）无任何导航锚**：全站唯一 sticky/fixed = 侧栏。

**修复（纯展示层）**：
- **P0**：α-muted→实色（10 文件）；`text-[10px]/[11px]`→`text-xs`（23 文件，保留 empty-state svg 装饰与 sparkline 去饱和）；9px 徽章→11px；审计表行 hover。
- **P1 工效**：`StickyTabs`（4 hub 页）+ `BackToTop`（44px）。**sticky 陷阱**：`<main>` overflow-hidden 祖先使 sticky 失效——删除后 20 路由 × 双视口全测无 h-溢出（min-w-0 是真根因）。
- **P1 认知**：hero 三卡→两卡（`ProvenanceAnchor embedded` 嵌入 VerdictAnchor）；discipline 同 sha 冻结/结果行 emerald 左竖条 + ↳；track 归因卡头部裁决速览条（同源 metrics，零新增数据面）。
- **P2**：`ProvenanceBadge frozen` prop（锁/时钟语义二分，picks/track 页头接线，i18n zh+en）；recharts 刻度→11px + `fill=var(--muted-foreground)`（原 #666 ≈3:1）。

**验证**：tsc 0 + build 23/23 + 33 契约测试 + ruff 净（顺手修 5ea6649 预存 3 lint 错）+ 本地 junction 静态服务四页视觉模型复验 + 对比度复测 3.3→6.9:1 + sticky/返回顶部交互实测 + 移动端无溢出。

**遗留候选（未做，均有明确理由）**：regime 图 recession/hike 区间底纹（需事件数据管线，跨 lane）；佐证区两卡微对齐（P3 边际收益低）；picks 长表分页/虚拟化（sticky 已解主要痛点，KISS）。

## 2026-08-15 (p) 同题扫查二轮：死代码/依赖裁剪 + lint 清零 + 新鲜度审计 + 后续优化方案

**交付（`6eab8a4`，-2118 行）**：
- **死代码**：`globe-demo.tsx`、`ui/globe.tsx`（three/three-globe/@react-three 链）、`ui/chart.tsx`、`ui/calendar.tsx`（react-day-picker+date-fns 唯一用户）零引用（grep 全目录复核）删除；package.json 裁 9 依赖，`pnpm-lock.yaml` -798 行同步（manifest+lock 原子，CI `--frozen-lockfile` 兼容）。CI install 下载变少；逐页 payload 实测等量（运行时零变化）。
- **lint 清零**：live-prices 冗余 setState 删；i18n provider SSR 安全水合模式带理由 disable。`eslint src --quiet` 0 error。
- **验证**：tsc exit 0 + build 23/23 静态页 + 全量 pytest exit 0（Windows 迁移后首次全绿）+ ruff 净。

**新鲜度审计（问题分级）**：
| 面板 | 状态 | 归属 |
|---|---|---|
| theme_signals + themes price 族 | 06-30（46天）| CI display_panel 收敛中（另一 session 的 run 31878236600 验证范围，勿重叠） |
| smart_money | 08-07 | 13D fetch 间歇，低危 |
| picks_meta / pick_conviction | 08-03 | 读 gitignored 冻结 OOS parquet，设计如此 |
| GDELT news | as_of 06 | 增量回填滞后 |
| reddit | live 2 picks，1 null bull_ratio | RSS 无 score 结构限制；类型已防御 |

**后续优化方案（可实施性已评估）**：
1. **性能·tab 级 next/dynamic**（推荐，低风险）：4 个 hub 页（picks/regime/track/confirmation）非默认 tab 改 `next/dynamic` → recharts 376KB + 非首屏数据移入按需 chunk（picks 首屏 1890→~1500KB）。Turbopack 兼容、不换构建器、每页 4-6 行。UX 代价 = 首次点 tab 短暂 loading。
2. **性能·BACKTEST_MONTHS 99→36**：picks_backtest.json 140→~55KB 且在共享 chunk（每页受益）。显示取舍（track record 只显 36 月）需业主点头。
3. **性能·webpack manualChunks**（大工程）：换构建器 + 26 JSON 按面板拆 chunk（非图表页 -350KB）。涉 CI 构建行为，需 CI session 协调，仅当 1+2 不够时。
4. **数据·A 股行业分类**：baostock `query_stock_industry`（证监会行业，免费无 key，需加依赖 ~pip baostock）或 zero-dep 直接 HTTP；扩展 `build_ticker_metadata.py` + cache + methodology 更新（tier→industry）。M 任务。
5. **数据·Russell 2000 COT 2016**：ICE 变体代码已就位，等 cftc.gov 连通自动补（merge-protected）。
6. **数据·reddit 富化**：业主 PRAW 凭证 → transport 自动升级（代码已就绪）→ score/bull_ratio 补全。
7. **准确率**：研究面冻结，唯一合法路径 = Track A 因子生成器（业主已授权，新冻结面）与 E3 forward-live（AUD-06+业主 GO）—— 均预注册流程，非 display 层可擅自推进。

**边界**：纯 web 展示层；0 ledger/frozen/config/prereg/OOS 改动；未跑 research/forward；未 push（本地领先 origin 4 commit，推送时机由 CI session 协调）。

## 2026-08-15 (o) web 数据层类型加固 + 性能探索定论 + Windows 测试修复（与 CI/CD session 并行）

任务方向：数据/性能/准确率/web 显示优化（CI/CD 由另一 session 负责，本轮零重叠）。三项交付：

**① 全部 26 面板显式契约类型（`web/src/data/aionis/index.ts`）** — 闭环 current.md 续①遗留的
"凡 `as typeof` 面板同类风险" follow-up。nullability 逐一对照 `export_terminal_data.py` 导出契约：
taco.latest_vix/latest_date、form4.shares/price、themes.signals[].value/series[].value/as_of、
pick_conviction.latest/trailing_std_mean 可空（export 显式 `if ... else None` 分支）→ `| null`；
metrics.ledger_row/config_sig_short 仅 live-ledger 分支存在 → optional；market_context.date_range
实为 `string[]`（原臆写 string，tsc 即刻抓出）。日更数据形状漂移从此在 cast 单点红灯（对齐
deploy 31869082383 reddit `bull_ratio: null` 类型塌缩先例的防御）。ThemeCard 内联结构 prop 类型
→ 复用导出 `Theme`（其 seriesVals 运行时 `typeof v === "number"` 过滤本已存在，仅类型声明落后）。
验证：`tsc --noEmit` exit 0 + `next build` 22 路由全静态预渲染 + 33 `test_web_terminal_data` 契约
测试绿 + 全仓 ruff 净。`attribution-card` 的 `typeof aionis.metrics` 参数注解自动升级为显式类型。

**② 性能探索（全部实测取证）**：
- recharts 376KB chunk **已按路由正确分割**——7 个无图表页实测不引用它；无需 lazy 化。
- **barrel 命名导出拆分实验 → 实测更差 → 回退**：Turbopack 静态导出对跨路由共享模块**不去重**
  （数据指纹证据：market_context 内容出现在同一页加载的 2 个 chunk 里各一份拷贝），27 个消费文件
  改命名导入后每页 +50-280KB（picks 1613→1890）。结论 = 保留单一合并对象（单模块 → 单共享 chunk，
  零重复）；已在 index.ts 头部注释固化此结论。git checkout 回退了全部消费文件（它们曾被我改写，
  最终 diff 不含）。**若未来要 per-route 数据拆分：需 webpack manualChunks（Turbopack 无此 API）= 换
  构建器**，涉 CI/CD 领地，仅记录不擅动。
- **"每页变大"真因 = 过期本地基线 + 日更数据增长**：纯 HEAD 重建与改动版逐页等量（evidence
  1222KB/picks 1890KB/discipline 1284KB）；旧 out/ 来自更早 commit。近期 +50-280KB/页全部来自
  数据新鲜（macro_drivers 5→7 序列、picks_backtest 增月等）——是改进非回归。
- 每页 JS ~1.2-1.6MB 的构成：React/Next 运行时 ~500KB（不可免）+ 共享数据 chunk ~350KB + recharts
  376KB（仅图表页）+ UI 库。数据 chunk 的减肥杠杆 = 缩短 picks_backtest（BACKTEST_MONTHS=99→36，
  显示取舍，未擅动）。

**③ Windows 迁移预存测试修复**：`test_run_dir_sanitizes_unsafe_sig` 用 `str(d).startswith("/tmp/..")`
断言，WindowsPath 渲染反斜杠必挂（sanitise 逻辑本身正确，`eviletc` 未逃逸）→ 改 `d.as_posix()`。
18/18 test_reporting 绿。这是 WSL→Windows 迁移后全套 pytest 在本机全绿的已知最后一个失败。

**④ 数据面核查（订正旧记录）**：13D smart_money latest=2026-08-07（日更生效，旧"2024-12 滞后"
记录过时）；A 股 picks 现为板块级分类（创业板/沪主板/科创板，methodology 已诚实披露"tier 非
industry"）。行业级升级 = 后续项（需申万/证监会行业源 + license 审查 + CI 协调）。

**边界**：`index.ts` + `themes-view.tsx`（2 行）+ `test_reporting.py`（1 断言）+ state；**0 ledger/
frozen/prereg/ADR/config/OOS 改动**；未跑 research/forward；**未 push**（CI/CD session 并行验证
refresh run 中，推送时机由其协调——本地 commit 已就绪）。

**待业主/后续**：(a) push 时机（CI session 协调）；(b) A 股行业级分类数据源裁决；(c) 若在意每页
payload，可选 webpack manualChunks 换构建器（涉 CI）或 BACKTEST_MONTHS 缩减（显示取舍）。

## 2026-08-09 (n) 部署站仪表盘诊断 + IA 重设计提案（已 push 上线）

业主看**部署站**，批"数据缺失/taco 空图/reddit 只一快照/没标川普两任就职/七主题生硬/整体像拼凑杂烩不构成有机整体"。**系统化诊断（DOM + 审计 + dev server 实测）**：

- **数据层大多 2016+ 且健康**（market/taco/cot 都 2016→2026）；部署站看着缺 = **未重新部署**（近期回填没上线）。已 push → Actions 重建中。
- **真凶 1（已修 commit `e3274e3`）**：`next.config.ts` 硬编码 `basePath:/Aionis` → `next dev` 下每路由 404（业主若跑 dev 看到全空）。改 production-only。
- **真凶 2（已修 `e3274e3`）**：taco `XAxis dataKey="date"` 但数据是 `month` → 0 path 空图。改 `month`。
- **川普就职（已修 commit + IA-doc 一起 push）**：market 事件表补 2017-01-20/2021-01-20/2025-01-20 就职 + 2025-02 关税，新增 `inauguration` 类型（emerald 样式）。
- **硬约束（不可粉饰）**：reddit **forward-only**（Pushshift 2023 死，无 2016 历史）；ic_monthly/picks_backtest/pick_conviction **OOS 2021+ 研究冻结**（延 2016 = rerun-to-significance 禁）；须诚实标注。
- **实测渲染正常**：dashboard/market/positioning/conviction/powerfloor/calibration（DOM 验 path/line 计数）。reddit-view 仍是 stub（current.md 既标，前端 owner 待接 picks 表）。

**P3 IA 重设计提案** `reports/design/2026-08-09-terminal-ia-redesign.md`（PROPOSED，待业主审）：核心 = 把扁平 nav 重构成 **6 步决策漏斗**（①定调 Regime→②定向 Themes→③定标 Picks→④佐证 Confirmation→⑤问责 Track→⑥边界 Discipline），每模块加"角色导语"；七主题可操作化（方向×强度×利好股）；诚实标注约束；删模板遗留（accounts/cards/budgets/crypto/…）；P2 扩周频 cron（现有 `refresh-terminal-data.yml` 只 re-export 不 fetch → smart_money 卡 2024-12；扩成 fetch+re-export）。

**已 push** `27a18f3..b1d195d`（含本会话所有 commit：Track A 校准视图、Track LLM pilot/prereg、dashboard 修复、川普就职、IA 提案）→ Actions 重建部署中。

**待业主**：① 审 IA 漏斗提案 → 授权 P3（nav 重排+角色导语+删模板+七主题可操作化）② 裁 cron 频率（周频 Fri 收盘后 vs 保持日频）③ reddit picks 表要不要我补 ④ P4 主题 ④⑤（news LLM forward-only / risk pyfolio）。

## 2026-08-09 (m) Track LLM Phase-0 可行性已证 + PROPOSED 预注册（D-first 单变量）

业主问"C+D 结合"→ 分析后推荐 **D-first 单变量**（EDGAR-LLM filings-tone 作第 42 列，1 trial 干净归因；C/stacking 条件后续仅当 D 显示信号）。业主再授权"创建最有价值内容至优化"→ 交付 **Phase-0 可行性 pilot + PROPOSED 预注册**（0 ledger / 0 frozen / 0 OOS）。

**Phase-0 实测（本地门，真数据）**：`scripts/track_llm_feasibility_pilot.py`（+8 hermetic 测试绿，ruff clean）：
- **G1 CIK 解析 = 100%**（US OOS 2021-2026，533 distinct tickers 全解析；2911 ticker-years）。cik_resolver 的 ~60% gap 是**历史全宇宙**问题，OOS 窗口不绑定。
- **G2 token 投影 = ~11.71M（一次性）**（5576 10-K MD&A extractions；idempotent accession cache → 重跑 0 token）。两本地门 GREEN → **FEASIBLE**。
- **待 owner（需凭证）**：G3 真实 per-call token + G4 temp=0 稳定性（`--measure-llm N`，scaffolded，freeze 前校准）。

**PROPOSED 预注册** `docs/track-llm-preregistration.md`（未冻结）：两尾 null-expected claim（`IC_{41+LLM} − IC_{41-frozen}` 配对 HAC）；EDGAR 10-K MD&A excerpt（filed-date PIT + embargo 21）→ GLM temp=0 → `clip(bullish−bearish,−1,+1)` scalar → forward-fill；复用 Track C #48 learner（仅 41→42 列）；n_trials=1（DSR 平凡）；H6 走 cache-pin；stacking(C) 条件触发（仅当 IC_diff CI 不跨零）；US-only v1；D1-D6 owner 裁断点。可行情报告 `reports/design/2026-08-09-track-llm-feasibility-pilot.md`。

**诚实预期**：大概率 null-to-modest（power floor 封顶），但 null = 第三条独立 null（#49 月频 / #54 周频 / LLM）。

**边界**：本轮纯新建 1 script + 1 test + 2 docs（prereg PROPOSED + 可行情报告）+ state；**0 ledger / frozen / prereg-freeze / ADR / config / E3 / OOS** 改动；未跑任何 LLM 增强估计量；未做任何 GLM API 调用（G3/G4 待 owner 凭证）；Track C / Track Adaptive / Track B 冻结面完全未触。

**待业主**：① 审 PROPOSED 预注册 + 可行情数字 ② 用凭证跑 `--measure-llm 8` 校准 G3/G4 ③ 裁 D1-D6（universe/filing-type/excerpt/scalar/model+temp/cost）→ 若 GO：`config_committed` 冻结 → 首次抽取 → OOS。④ 或：弃 D（接受 null-to-modest 预期，收尾）。

## 2026-08-09 (l) Track A 切片 A1 — walk-forward 校准可靠性（display 层，已交付待提交）

业主重提"历史数据补到 2016 后 → 实时更新 + 用新数据不断自校正模型参数往可观走"。**关键事实：此问题 2026-08-08 已问、已分析、已实测**——[`reports/design/2026-08-08-live-adaptive-calibration-analysis.md`](../reports/design/2026-08-08-live-adaptive-calibration-analysis.md) 切 Track A（显示层，推荐）/ Track B（研究层）；Track B（扩窗周重训）已冻结+跑 = **NULL（ledger #54，IC_diff_weekly −0.0037，p=0.26，adaptive 略差于冻结）**。新增 2024-2026 调研确认重训频率非主导/常恶化（[Inquire Europe "Less is more"](https://www.inquire-europe.org/news/in-case-you-missed-it-less-is-more-biases-and-overfitting-in-cross-sectional-machine-learning-return-predictions/)）；唯一未测合法变体 = 固定模型集 Bayesian/stacking（[Gelman](https://sites.stat.columbia.edu/gelman/research/published/stacking_paper_discussion_rejoinder.pdf) ：BMA 在 M-open 失效）；唯一有希望新数据方向 = LLM 文本信号（项目 extraction 模块已有，但无 frozen 臂用 LLM 特征）。**业主裁 = 路径甲（显示层自适应校准）**（AskUserQuestion 四选一）。

**Track A 现状盘点**：A2（漂移报警）已建（`model_drift.py`+`export_model_health()`，backend done；UI 归前端 owner）；A3（诚实 track record）已建为 `export_picks_backtest()`（历史命中），前瞻累计半 = E3 owner-GO 门。**A1（walk-forward 校准）此前未建** = 本轮唯一真新增。

**A1 交付**（纯 display 变换，0 ledger/frozen/E3/研究估计量）：
- `src/aionis/eval/score_calibration.py`：+`_reliability_bins()` + `calibrate_walk_forward()`。对每个 realized OOS 月 T，用**严格 T 之前**的 realized (score, fwd_return) 对重拟合 Platt 显示映射，预测 T 的 P(up)；T 的 realized 结果回测打分（backward audit）。产出 per-month OOS-ECE 序列 + pooled OOS 可靠性图。反泄漏契约镜像 `calibrate_latest_month`（T 仅预测不入拟合；仅 2 参显示映射重拟合，frozen LightGBM 永不触；单调映射不能制造判别力）。
- `scripts/export_terminal_data.py`：+`export_calibration_reliability()`→`calibration_reliability.json`（awaiting_fetch 守卫 + 诚实方法学串），接入 `main()`。
- `tests/test_score_calibration.py`：+8 hermetic 测试（反泄漏 T 不入拟合 / walk_forward=True / 强信号可靠性单调 / null 信号概率带紧 / H6 跨调用确定性 / 太少月跳过 / 双区域 / jsonable）。

**验证**：score_calibration(23)+model_drift(11)+web_terminal_data(20)=54 display 测试绿；ruff clean（3 文件）；**真实数据跑**（read-only，未写 tracked JSON）：US pooled_ece=0.0369 / 概率带 [0.435,0.553] 紧绕 base rate≈0.51（诚实 null 签名）/ ECE 随样本增长 0.18→0.115（校准更可信）；CN pooled_ece=0.0196 / 带 [0.438,0.480]；训练对扩 5399→30282(US) / 10538→57537(CN)。**判读**：概率保持可信（低 ECE），但判别力弱（带紧）—— 这是 leakage-safe 的"用新数据自校正**校准**"，**非**制造正 IC（与 #49 null 一致）。

**边界**：本轮 3 文件（2 src/script + 1 test，+291/-2）+ state；**0 ledger / frozen / prereg / ADR / config / E3 / data / web-artifact** 改动（真实数据跑 read-only，未写 `web/src/data/`）；未跑 research/forward/strategy；未触 #49/#54。git status 仅 3 文件 M。

**待业主**：① 审 A1 数字 + 授权 commit（Conventional Commits）② 是否跑 `export_terminal_data.py` 写 `calibration_reliability.json` 进 web（前端 owner 管护，需协调）③ A3 前瞻累计是否过 E3 owner-GO 门 ④ A2/A1 终端 UI 渲染（前端 owner）。

**业主授权自主推进至不可再优化（2026-08-09 续）**：业主"授权创建最有价值最推荐内容，直到该环节不可再优化"。已全栈交付 A1：
- **后端** commit `df34979`（feat(eval)）+ state `681b7df`（docs(state)）。
- **前端** commit `459d96e`（feat(web)）：`/calibration` 路由 + `calibration-view.tsx`（recharts 可靠性图：预测 P(up) vs 实现频率 + 完美校准对角线 ReferenceLine；ECE-随样本增长折线 + 0.05 绿阈值；per-region stat 行 + 诚实 null 披露）+ data namespace/CalibrationReliability 类型 + zh/en i18n + navMonitor TargetIcon 入口 + 真实 `calibration_reliability.json`（US pooled_ece 0.0369 / CN 0.0196）。
- **验证**：`pnpm tsc --noEmit` clean + eslint clean + `next build` 绿（`/calibration` 已 prerender）。0 frozen/ledger/E3/研究估计量改动。

**Track A 现状（优化到位）**：A1（校准可靠性）全栈完成；A2（漂移）既有完成（model-health-view）；A3（诚实 track record）后向既有完成（picks-view），**前瞻累计半 = E3 owner-GO 门（cron 仍 disabled，不可擅自解冻）**。再加图（概率带随时间、US/CN 叠加）= 边际收益递减 / 过度工程，KISS 不做。

**剩余业主杠杆（非我可自主）**：① E3 owner-GO → 启用前瞻命中累计（A3 前瞻半，display-only forward ledger）② 若要新研究线 → 路径乙（固定模型集 stacking）或路径丙（LLM 文本信号），均需新 prereg/frozen/ledger。

## 2026-08-08 (a) 历史数据推进至 2016 — COT 全量 + Form4 深化（display 层）

业主要求"推进所有历史数据年份至 2016 + 低消耗模型带 agent 执行以省 token"。**范围 = fintech 终端 display 层**（研究管线冻结，climax #49 null 不动）。

**2016 覆盖核账**：
| 数据集 | 2016 覆盖 | 动作 |
|---|---|---|
| market_context (VIX+EW 指数) | ✅ 2016-01..2026-07 (127mo) | 既有 |
| picks_backtest (track record) | ✅ 131mo | 既有 |
| smart_money (13D) | ✅ raw 2015+，2622 条≥2016 | 既有（latest 2024-12，cached pulls）|
| **COT (positioning)** | ✅ **2016-01..2026-08**（9/10 市场连续；Russell 2017-08+）| **本轮扩展** |
| **Form4 (insiders)** | ⏳ 机制就绪，后台深化中 | **本轮扩展** |
| ic_monthly / pick_conviction | ❄️ 2021+ 冻结 OOS | **不动**（反泄漏；延展 = rerun-to-significance 禁）|

**COT 扩展（CFTC 公共域，weekly 不修订，filed Fri）** — `scripts/cot_fetch.py`：
- `YEARS (2024,25,26)` → `range(2016,2027)`（全 Trump 元年）。
- **variant-union**：CFTC ~2022 重命名 S&P/Russell/Copper 合约（`E-MINI S&P 500 STOCK INDEX`→`E-MINI S&P 500` 等），单名 exact-match 改多变体 union + 按 (date,market) 去重 → 恢复 3 市场全 2016。
- **单调 merge**：cftc.gov 边缘网络间歇 ConnectTimeout（2018/2019/2023 跨多次 run timeout），新 run 与既有 parquet union、重叠 keep existing → 数据只增不减（实测 v4 补回 2023 gap）。
- 结果：10 市场 / 5446 行；9 市场 553 wks 连续 2016-01-05..2026-08-04；Russell 2000 2017-08+（其 e-mini 当年精确名 2016 缺，市场特异小 gap）。
- `export_cot`：`comp.tail(78)` → 全量 `comp`（完整 2016→today arc）+ methodology 标注 2016。

**Form4 扩展（SEC EDGAR 公共域，filed-date PIT）** — `scripts/form4_fetch.py` + `export_form4`：
- `START "2024-01-01"` → `"2016-01-01"`；**merge-by-issuer checkpoint**（每 issuer 完成即写 + 保留未重跑 issuer；5 大盘 × 2016→today = 数千次礼貌 XML 拉 ~小时级，merge 保证 live 广度不退化；XML cache 幂等，重跑即续）。
- `export_form4`：动态 window（df min/max 交易月）+ 新 `yearly` 聚合（逐年 buy/sell）+ methodology 标注 2016。
- 数据：当前 2023-07..2026-06（5 issuer / 2415 txns / yearly [2023,24,25,26]）；后台 fetch 深化至 2016（AAPL 处理中 ~440 filings），完成后 cron re-export 自动反映。

**模型分层 + 省 token（业主诉求）**：opus 编排（调研/计划/反泄漏核账/fetcher 精确编辑/独立验证）+ **sonnet agent 执行 export 显示逻辑 + 测试**（精确 spec，1 轮交付，orchestrator 独立核验 diff + ruff + pytest）+ 后台 bash fetch（网络 bound，0 model token）。

**验证**：ruff 全 repo clean；affected tests 37 绿（web terminal + form4）；COT/Form4 JSON 实测 2016+（COT composite_series 534 wks 自 2016-05，z-score 52w 预热）；全套 hermetic pytest 提交前确认绿。

**边界**：本轮 `scripts/cot_fetch.py` + `scripts/form4_fetch.py` + `scripts/export_terminal_data.py` + `tests/test_web_terminal_data.py` + `web/src/data/aionis/*.json`（regenerated）+ state；**0 ledger / frozen / prereg / ADR / config / E3 / runs-data 改动**；未跑 research/forward/strategy；未触 ic_monthly/pick_conviction（冻结 OOS）；display 层不进研究管线（CLAUDE.md display-only 契约）。

**待业主**：① 审线上 `/positioning`（2016→today arc）② Form4 后台 fetch 完成后（~小时）`/insiders` 显示 2016→today 逐年 ③ Russell 2000 2016 gap（需查 CFTC 当年第三变体名）④ smart_money latest 2024-12 是否重刷 EFTS（独立切片）。

## 2026-08-08 (b) TACO/smart_money 推至 2016 + Form4 首批 2016 落地 + 并发 worker 观测

业主授权"创建最有价值内容直至不可再优化"。代码侧 2016 优化收尾：

- **TACO `/taco`**：VIX 由 `[-260:]` 近 1 年日线 → **月均 2016-01..2026-07**（127 点，复用 market_context 月聚合），2025 TACO 事件现置于完整 Trump-era 压力史背景。web 契约测试加 `test_taco_vix_monthly_from_2016`。
- **smart_money `/smart-money`**：加 `yearly`（逐年申报数，镜像 form4 yearly），实测 [2015..2024]。
- **COT Russell 2000 2016 gap**：找到第三变体名 `RUSSELL 2000 MINI INDEX FUTURE - ICE FUTURES U.S.`（2016 在 ICE，~2017 才转 CME），加入 variant-union。**但 cftc.gov 本会话持续 ConnectTimeout（2016/2024/2025 多年跨多次 run 超时）**→ Russell 仍 2017-01 起；ICE 变体代码已就位，cftc 恢复后任一 run（merge-protected）即补 2016。9/10 市场已连续 2016-01..2026-08。
- **Form4 2016 首批落地**：AAPL checkpoint（merge-by-issuer）→ form4.json 现 `window=2016-02..2026-06`，`yearly=[2016..2026]` 全 11 年（AAPL 深，其余 4 issuer 仍 2024-2026，后台 MSFT 深化中）。

**⚠️ 并发 worker 观测（非本会话产物，勿混入我的提交）**：工作树出现另一 actor 的未提交 reddit 升级——`src/aionis/ingest/reddit_sentiment.py`（M，双传输 PRAW+zero-cred Atom RSS）、`scripts/reddit_fetch.py`（??）、`tests/test_reddit_sentiment.py`（M）、`runs/ledger.jsonl`（M，疑 reddit data_ingest 行）。我派发的 sonnet agent 一度把 `export_reddit_meta` 改成读 `reddit_snapshots.parquet` 的 cache-or-await（schema 核验属实：reddit_fetch.py 确写该 parquet + reddit_sentiment.py 列匹配）**但漏掉前端 `subreddits` 字段 → web build 类型检查失败**。处置：**revert 该 reddit export 改动到 HEAD**（export_reddit_meta 回到 awaiting_activation + subreddits），只保留我本轮的 TACO + smart_money；reddit 模块整体留给并发 worker（避免 file-boundary 冲突 + 不冻结其 in-flight 描述）。**amend 仅 stage 我的 7 文件**，reddit_sentiment.py/test_reddit_sentiment.py/reddit_fetch.py/ledger.jsonl 不入提交。

**验证**：ruff 全 repo clean；web 终端 18 测试绿（含新 taco + smart_money）；**web build OK**（✓ Compiled + 17/17 静态页，类型检查过）；COT/Form4/TACO/smart_money JSON 实测 2016+；全套 hermetic pytest 跑中（含并发 worker 的 test_reddit_sentiment.py 改动）。

**后台作业（额度恢复后可继续/验收）**：form4_fetch（MSFT 深化中，EDGAR）；13D sequenced refresh（等 form4 释放 EDGAR）；COT Russell 2016（cftc 阻塞，待恢复）。日志 `runs/{form4_fetch_2016_v3,refresh_13d_sequenced,cot_fetch_russell_retry}.log`。

**边界**：本轮 `scripts/cot_fetch.py` + `scripts/export_terminal_data.py`（TACO+smart_money）+ `tests/test_web_terminal_data.py` + `web/src/data/aionis/{cot,form4,smart_money,taco}.json` + state；**0 ledger / frozen / prereg / ADR / config / E3**（mine）；display-only。

## 2026-08-08 (c) Reddit 散户情绪激活 — 零凭证 Atom RSS（OAuth 堵死的唯一存活路径）

**背景**：业主报告 Reddit API 申请失败（2026 Responsible Builder 政策）。实证三路 `.json` 全 403（通用 UA / 描述性 UA / old.reddit）→ 论坛"加 .json 免密钥"捷径已死；`.rss` 端点 200 存活（Reddit 自家公开 Atom 订阅源，ToS-clean，G7）。OAuth token 端点 401（在线，只等凭证，但凭证申请被堵）。StockTwits 免费 API 从数据中心 IP 被 Cloudflare 403。

**交付**（`reddit_sentiment.py` 双传输 + 新 fetch + export）：
- `transport=auto|praw|rss`（`auto`=有凭证 PRAW / 无凭证 RSS）；`.rss` 经 `defusedxml`（XXE-safe）解析 + `bs4` HTML→text + 复用既有 `_aggregate_snapshot`/ledger/sha256 纪律；每 subreddit 失败/畸形 XML 跳过不中断；`HostSpacingPolicy` ≥2s + 有界 429 重试。
- **ticker 抽取实证修正**：原 case-insensitive 裸词把英文词当 ticker（首跑 top = ARE/SO/NOW/well/tech 全是英文）。真实 WSB `/new` 数据驱动：cashtag 几乎不用（仅 `$HTZ`×1），真 ticker 大写裸词（PLTR×10/SMCI×10/TTWO×4），英文词小写 → **case 是判别器**。改为：cashtag（任意大小写）+ 大写裸词 ≥4（短 ticker 如 ARE/SO/M 仍需 `$`）。修后 live 输出全真 S&P（PLTR/SMCI/TSLA/UBER/TTWO/EPAM/SNDK）。
- **修 ordering bug**：曾把 FinBERT 下载移到凭证检查前 → 缺凭证 `transport=praw` 先下 438MB 再 raise，撑爆 `/tmp` 致全套 pytest 挂起。改回 pull（含凭证检查）→ FinBERT 下载后。
- `scripts/reddit_fetch.py`（零凭证，扫 566 S&P panel；`auto` 将来业主有凭证自动升级 PRAW 带 score）。
- `export_reddit_meta` 稳定 superset schema（13 key 两分支同构）→ `tsc --noEmit` CLEAN。修了并发 session 的 build-break（其版 reddit export 漏 `subreddits`/`collector`/`mode` → web 类型检查失败；已 revert）。`reddit.json` 现 `status: live`，7 真实 ticker picks。

**反泄漏底线（unchanged）**：forward-only（Pushshift 2023 死，无 permissive 历史源）→ 无 PIT 历史 → **进不了回测**；`mode: exploratory`，仅终端展示，绝不进 OOS 管线（7-gate rubric L108 判决不变）。1 行 `data_ingest` ledger（RSS，`score_available: false`）。

**与并发 session 协调**：handoff (b) 记录并发 session 观测到我的 reddit 改动（"并发 worker"），其 sonnet agent 试同款 export 改动但漏 `subreddits` → build-break → 已 revert；其提交仅 stage 自己 7 文件，reddit 模块整体留我。**前端 `reddit-view.tsx` 仍为占位符**（不渲染 picks）——留前端 owner 接 `status==="live"` 分支（需配套 i18n key），避免与并发 session 的 web-build 管护冲突。

**验证**：23 reddit 测试绿（含 malformed-XML 跳过 / case-aware 抽取 / auto-fallback）；全套 hermetic pytest exit 0（ordering bug 修后无 FinBERT 下载、无挂起）；ruff clean；`tsc --noEmit` CLEAN；真实 RSS 拉取 E2E（FinBERT 缓存于 `data/cache/`，首跑下载 ~438MB 一次性）。

**未提交**：`reddit_sentiment.py`(M) + `reddit_fetch.py`(??) + `test_reddit_sentiment.py`(M) + `export_terminal_data.py`(M, reddit export 增量) + `reddit.json`(M, live) + `runs/ledger.jsonl`(M, 1 data_ingest 行) + state(M)。留业主审阅后提交（或与并发 session 协调）。

**边界**：本轮 display-only ingest；**0 frozen surface / prereg / ADR / config / E3 改动**；未跑 confirmatory/forward/strategy；未触研究管线。

## 2026-08-08 (d) 实时数据 + 自适应校正循环 — 调研 + 深度分析（PROPOSED，业主决策）

业主提"历史数据补完后→实时更新 + 用最新数据自校正模型→迭代至可观预测"。派 2 sonnet 调研：**web 路 [1210] ×2 死**（proxy 今日不稳）→ opus 直接 WebSearch（3 路：walk-forward 重校准 / DSR·PBO / adaptive-vs-frozen OOS 证据）；repo 路成功。交付 2 文档：① `reports/2026-08-08-live-data-calibration-infrastructure-report.md`（既有基建盘点，908 行，34 文件引用，核对属实）；② `reports/design/2026-08-08-live-adaptive-calibration-analysis.md`（综合分析 + 推荐）。

**核心结论**：「用最新数据自校正」**合法 iff "更好" = 校准更准 + 漂移报警 + 诚实 forward 跟踪**（Track A，复用 `score_calibration` + E3，display-only，0 frozen/ledger/config）。**"更好" = IC 变正 则数据不可达**——power floor σ(IC)≈0.10（look-3 等价需 ~36 年）；Gu-Kelly-Xiu 2020 最佳月 OOS R² 仅 1.08–1.80%，且**主导因素是模型类不是更新频率**。自适应追 IC = rerun-to-significance + 多重检验膨胀（Bailey-López de Prado 2014："DSR/PBO especially useful when research is highly adaptive"；每轮 auto-tune = 一次 trial，必须 deflate）。

**两轨**：**Track A（推荐，合规）** = A1 walk-forward 校准重训（expanding realized 窗，`walk_forward=True` display 变体）+ A2 漂移报警（滚动 OOS 分布/cond-IC vs 历史，纯显示）+ A3 诚实 forward 累加器（E3-lite 或 E3 本体 owner-GO；commit→reveal(+21d)→score→显示序列，**绝不喂回训练**）。**Track B（gated，大概率仍 null）** = 研究层在线学习追 IC：需新预注册 + 逐周期 `config_committed` + DSR/PBO 预算 + 硬隔离 Track C；且与 null 定帧冲突（memory 勿追新 alpha）→ **需业主显式 GO**。

**"可观"重定义**：校准可靠性（reliability 图近对角）+ 漂移诚实 + forward 命中率序列——**非 IC 变正**。这是数据允许且对 fintech 终端真正有用的胜条件。

**边界**：本轮纯 docs（2 新 PROPOSED）+ state；**0 frozen / ledger / config / E3 / 代码**改动；未跑 research/forward。**待业主**：选 Track A（推荐）/ Track B（gated，需新预注册）/ 拓宽 framing（与 null 定帧冲突）。

## 2026-08-08 (e) Track A 落地 — 模型漂移监测模块（leakage-safe，display-only）

业主授权"建最有价值内容直至不可再优化"。依 (d) 的 Track A 推荐，落地漂移监测（"自适应循环"的 leakage-safe 信号，不喂回训练）：

- `src/aionis/eval/model_drift.py`（新）：PSI（score 分布漂移，recent 6 实现月 vs 历史）+ 滚动截面 rank-IC（recent vs full）。**realized-only**（复用 `score_calibration.build_pair_frame` + latest 未实现月排除契约）。regime 阈值 stable<0.1<moderate<0.25<significant。11 hermetic 测试（PSI 正确性/常数退化、rank-IC 方向、**反泄漏：未实现最新月排除**、degeneracy→None、summary skip）。
- `scripts/export_terminal_data.py`：`export_model_health()` → `model_health.json`（per-region drift + methodology）。
- `web/`：`model-health-view.tsx` + `/model-health` route + sidebar Monitor 组 + i18n zh/en；契约测试 `test_model_health_shape`。
- **实测（真实 OOS）**：US PSI 0.156（moderate，IC 全程 +0.004 / 最近 +0.012 均 null）；CN PSI 0.534（significant，score 分布漂 + base rate 0.475→0.385；IC −0.036→+0.07 噪声翻转 = null）。

**为何这是"自适应循环"的合规解**：漂移检测 = "模型注意到近期行为偏离历史" → 给人看（**不自动重训**）。把"用最新数据自校正"实现为校准/漂移/跟踪的诚实显示，而非喂回训练（rerun-to-significance 禁）。这是 (d) Track A 的第一块；A2（漂移）已交付，A3（forward 命中率累加器）= 既有 `export_picks_backtest`（131 月 track record），A1（walk-forward 校准 eval）留后续。

**边界**：本轮 `src/aionis/eval/model_drift.py`（新 display 工具，类比 `ff5_residual`/`score_calibration`，不写 ledger/frozen）+ export（additive）+ tests + web + state；**0 ledger / frozen / prereg / ADR / config / E3**；display-only，不进研究管线。

**验证**：ruff 全 repo clean；model_drift 11 + web 契约 19 测试绿；web build OK（18/18，`/model-health` 渲染）；全套 hermetic pytest 提交前确认。

## 2026-08-08 (f) Track Adaptive 启动 — 自适应重训预注册（PROPOSED，业主授权反转 framing）

业主 4 指令处置：①**push**（`4b8d583`+`a755339` 已推 origin/main）②**reddit nav 恢复**（`a755339`：取消注释 `/reddit` 入口，现经零凭证 RSS live）③**form4 5-issuer 完成 re-export**（`a755339`，16564 txns，全 5 issuer × 2013-2026）④**"真的要走 Track B（在线学习追 IC）"**。

**命名撞车处置**：既有 `docs/track-b-preregistration.md` 是**冻结的七主题平台**（ADR-011，2026-08-02，config_committed）。把"在线学习追 IC"重命名为 **Track Adaptive** 避免污染冻结面。

**Track Adaptive = 重大方向反转**：业主显式授权反转 2026-08-05 option A 的"勿追新 alpha"锁（**仅对该特定路径**）。memory `aionis-publication-framing-option-a` 已加 2026-08-08 addendum（Track Adaptive 授权，仅限有纪律路径；无纪律 alpha-chasing 仍禁）。

**交付 `docs/track-adaptive-preregistration.md`（PROPOSED，未冻结）**：两尾 null-expected claim（`IC_adaptive − IC_frozen` 配对差，HAC）；扩窗重训默认（GKX 2020 先例）+ purge+embargo 反泄漏；**DSR/PBO 多重检验预算**（每重训 cycle = 1 trial，deflate 后才报；PBO>0.5=过拟合高危）；复用 Track C 冻结 learner+universe+features 作比较器（隔离"更新"单一变量）；与 Track C **硬隔离**（新 config/ledger 行，不触 #49）。**待 owner 裁断 D1-D6**（更新机制 A/B/C、OOS 窗口、SESOI_diff、n_trials 预算、是否要 PBO、GO）→ `config_committed` → 首次 OOS。

**关键纪律**：本轮**未跑任何 adaptive learner、未观察任何 OOS metric**（反泄漏：config_committed BEFORE result）。诚实预期仍 null（power floor σ≈0.10 + GKX"更新频率非主导"）；价值 = 自适应基建 + 诚实跟踪，非制造正 IC。

**边界**：本轮 `docs/track-adaptive-preregistration.md`（新 PROPOSED）+ state + memory；**0 ledger / frozen / 既有 prereg / ADR / config / OOS / E3** 改动。

## 2026-08-08 (g) /themes 展示模块落地 —— 七主题数据"被看见"（display-only）

业主选"七主题数据被看见"（display 路径，非研究）。建 `export_themes()` + `/themes` 视图：**7 主题 × 真实聚合信号**（cross-sectional mean @ 最新实现月）：
- **① 价格**（live）：momentum_21d 0.021 / volatility_63d 0.023 / β_252d 0.68 / reversal_5d −0.019 + 12 月 sparkline
- **② 宏观**（live）：regime_macro composite z = **−0.28**（VIX+credit+term+DFF 惊喜）+ 60 日 sparkline
- **③ 基本面**（live）：ROE 0.044 / profit_margin 0.32 / revenue_growth_12m 0.005 / leverage 0.25 + sparkline
- **⑦ 市场结构**（live）：Amihud ~0（S&P 高流动性）/ β 0.68 + sparkline
- **⑥ 净成本**（partial）：bps sweep net_sharpe@5bps 0.125 / gross 0.149 / turnover 1.14
- **④ 新闻情绪**（forward_only，诚实空）、**⑤ 风险**（needs_work，alphalens adapter 待建，诚实空）

视图：themes-view.tsx（状态 Badge + 信号表 + 内联 SVG sparkline）+ `/themes` route + sidebar insights 组（LayersIcon）+ i18n zh/en。契约测试锁：7 主题、live/partial 必有 signal、非-live 必空（**禁 mock**）、methodology 披露"非 Track-B 冻结判语"。

**为何这是合规的"不被埋没"**：把七主题平台的特征工程（Track B 冻结的 feature infrastructure）以**聚合展示**形式见光——**不碰研究管线、不写 claim、不动 Track-B 冻结判语、不 mock**（④⑤诚实标 forward_only/needs_work）。这是 (d) 分析里 Track A display 路径的延续。

**边界**：本轮 `scripts/export_terminal_data.py`（additive `export_themes` + helpers + main call）+ `tests/test_web_terminal_data.py`（themes 契约）+ `web/`（新 view/route/nav/i18n + index.ts + themes.json）+ state；**0 ledger / frozen / 既有 prereg / ADR / config / OOS / E3**；display-only。

**验证**：ruff clean；20 web 契约测试绿（含新 themes）；web build OK（**19/19**，`/themes` 渲染）。

## 2026-08-09 (k) Track Adaptive OOS 结果 — NULL（第二条独立 null，强化 power floor）

**首次新 OOS 结果入账**（ledger #54, event=`oos_result`, phase=`track_adaptive`, config #53 n_estimators=100, 285 配对周）：

| 量 | 值 | 判读 |
|---|---:|---|
| IC_frozen（真·冻结基线） | +0.0156 | 弱正周 IC |
| IC_adaptive（扩窗周重训） | +0.0120 | 弱正，**低于冻结** |
| **IC_diff_weekly（adp−frz）** | **−0.0037** | adaptive 略**差**，非更好 |
| HAC t / p (n=285) | −1.14 / **0.26** | CI 跨零 = **NULL** |
| DSR (n_trials=1) | 0.0 | observed Sharpe 负 → P(true>0)≈0 |

**判读（预期 null）**：用新数据周重训 LightGBM **不改善**周截面 rank-IC（略差 = 过拟合/噪声，非信号）。climax 月频 null 之后的**第二条独立 null**（周频），强化 power floor（σ(IC)≈0.10；GKX "更新频率非主导"）。与 pre-reg §1 null-expected 一致。**有价值**：adaptive 基建 + leakage-safe 诚实跟踪已交付（`model_drift.py`、score_calibration、deflated_sharpe、sequential runner），非制造正 IC。

**执行历程**（业主多次催"更多 agents + 避免空转"）：① embargo 核验（review agent 标 CRITICAL → 批判核查 = false positive，realization-invariant 测试证 leak-free）；② n_estimators amend 500→100（feasibility，#53）；③ threading n_jobs=4/2 静默崩溃 ×3（LightGBML concurrency race）→ **sequential n_jobs=1 reliable**（~23min）；④ OOM 教训（并发 pytest+OOS）→ 重活不并发；⑤ 并行：OSS adaptive-learning 调研（reuse-first 结论：river BSD-3 可选，alibi-detect license-risky，Aionis 自有 wheel 足够）。

**sig-label 修复**：runner `FROZEN_SIG` 原 指 #52（ffd0c922），实际用 #53（b7621e6b）；已修（label-only，run 全程用 #53 n_estimators=100）。
**H6**：双跑 bit-identical 确认后台跑中（~23min，PID 815221）；确定性 pin（n_jobs=1, seed=0）→ 预期 PASS。结果在 `runs/track_adaptive_h6.log`。

**边界**：本轮 `runs/ledger.jsonl`（+1 行 #54 `oos_result`）+ `scripts/track_adaptive_run.py`（FROZEN_SIG 修）+ state；**0 既有 frozen/prereg/ADR 改动**；#49 月频 null 不动；display 层（drift/themes/model-health）与研究解耦。

## 2026-08-08 (j) Track Adaptive OOS 执行 — embargo 核验 + n_estimators amend + threading 崩溃→sequential

业主多次催"启用更多agents + 避免空转"。OOS 执行历程（高 stakes，climax 后首条新 OOS）：

- **embargo 核验**：独立 review agent 标 embargo=5 **CRITICAL**（train fwd 与 predict 重叠）。批判性核查 → **false positive**（predict 在周收盘 t_w，close[t_w] 已知；train fwd 用 close[<=t_w]，realized by predict point）。加 `test_expanding_arm_train_labels_realized_by_predict_time` realization-invariant 测试证 leak-free（8/8 runner 测试绿）。
- **n_estimators amend**：500 树 = 16.8s/fit → 285 fits ~27min 太慢；**amend2 (#53, sig b7621e6b)** 减到 100 树（3.2s/fit，both arms，comparison 自洽）。
- **threading 崩溃 ×3**：joblib threading n_jobs=4/2 均**静默崩溃**（LightGBM concurrency race，非内存——单独跑也崩，无 traceback）。→ **sequential (n_jobs=1)** 可靠（原 500-tree sequential 跑 15min 稳定）。
- **OOM 教训**：并发 full pytest + OOS → OOM kill（"不影响各自进程"的违反）。→ **重活不并发**；OOS 单独跑。
- **并行**：reuse-first OSS adaptive-learning 调研 agent 后台跑（river/scikit-multiflow/alibi-detect 等 license + Aionis 适配性 → `reports/design/` 待回报）。

**当前**：sequential OOS 跑中（100 树，n_jobs=1，~20min，frozen IC=0.0156 n=285，reliable single-thread）。完成 → H6 双跑（bit-identical）+ result-ledger 行 + 报告（诚实预期 null）。

**模型分层 + 复用账**：opus 编排（embargo 批判判断 + 集成）+ sonnet agent（review + OSS 调研）+ LightGBM frozen learner 复用（Track C #48 substrate）+ deflated_sharpe.py（DSR）+ joblib（sequential 走其 infra）。

**边界**：本轮 `scripts/track_adaptive_{run,amend1,amend2}.py` + `tests/test_track_adaptive_run.py` + `runs/ledger.jsonl`（#51/#52/#53）+ state；**0 既有 frozen/prereg/ADR 改动**（新增独立行，#49 null 不动）；**未观察 OOS metric**（run 中，config_committed #53 先于结果）。

## 2026-08-08 (i) Track Adaptive amend1 → WEEKLY ①（supersedes #51，真正有意义的比较）

业主 "选择① + 时间改为一周（周收盘后）"。但**先查清 Track C 训练机制**（反泄漏纪律：跑前核验估量是否 ill-posed）发现：Track C 的 "冻结基线" **本身就是扩窗月重训**（每 fold test = 1 个月，refit on growing past）→ **#51 的 mechanism A（月扩窗重训）≡ Track C 估计器**，IC_diff≈0 by construction，**恒等无意义**。

**amend1（#52，FROZEN）把比较做成有意义的 + 周频**：
- 基线 = **真·冻结**单次 LightGBM 拟合（2016-2020 周频，**永不重训**）——Track C 从未做过的真冻结；处理 = 周扩窗重训（每个 OOS 周收盘后 refit on expanding realized + 5-session embargo）。
- 估计量 = 周截面 rank-IC 差（5-session forward，HAC 两尾，null-expected）。
- **可行性核验**：`track_b_panel` 实为**日频**（2637 日，非月末）→ 周频管线可行（周末采样 + 从 close 算 5-session fwd + embargo=5）。
- **范围约束**：US-only（CN panel 是月末）；substrate = 日可得特征（价格+基本面+raw macro；Track C regime composite 月末 → 周频排除）。
- `scripts/track_adaptive_amend1.py`（新）；ledger 51→52，sig `ffd0c9227e692fe826faeac964607577f3a9ff3de3384907297bc396887c4659`，sha256 自洽，supersedes #51（append-only，#51 保留为作废记录）。

**关键纪律**：本轮**未跑任何 learner、未观察任何 OOS metric**（config_committed BEFORE result）。下一步 = `scripts/track_adaptive_run.py`（日 panel 周末采样 + 5-session fwd + 真冻结 vs 周扩窗重训 + IC_diff_weekly + HAC + DSR + H6 双跑）；首次 OOS 入新 ledger 行。诚实预期仍 null（周 IC 比 月 IC 更噪；power floor）。

**边界**：本轮 `scripts/track_adaptive_amend1.py`（新）+ `runs/ledger.jsonl`（+1 行 #52）+ `docs/track-adaptive-preregistration.md`（amend1 banner）+ state；**0 既有 frozen/prereg/ADR/config 改动**（新增独立行，#49 monthly null 不动）；未跑 research/forward。

## 2026-08-08 (h) Track Adaptive `config_committed` 冻结 —— climax 后首条新研究线 OOS 的反泄漏门

业主 "全默认"（D1-D6 全推荐默认 + D6 GO）。落地反泄漏硬锚（**config_committed 先于任何 OOS**）：

- **`scripts/track_adaptive_commit.py`**（新）：frozen config 17 keys —— 两尾 null-expected claim（`IC_diff = mean(IC_adaptive) − mean(IC_frozen)`，HAC）；mechanism A 扩窗月重训；**复用 Track C #48 sig `e14b9d44…` 的 41 特征/宇宙/learner 作基底**（零改动，隔离"更新 cadence"单一变量）；purge+embargo=21；SESOI_diff ±0.010；两门（主=HAC p α0.05，次=RCI 等价，非救场）；`n_trials=1`（**纠正 pre-reg D4** 把重训 cycle 误算 trial——重训 cycle 是单策略的 OOS walk-forward，非独立 trial）；DSR/PBO（`deflated_sharpe.py`）；H6；frozen 隔离。
- **ledger 50→51**：phase=`track_adaptive`, sig `892fb5068ed1e994db937e23c5b95f2d35ea796825c0c97937253e34605515ad`，**sha256 自洽已验**（recompute==stored）。
- pre-reg `docs/track-adaptive-preregistration.md` PROPOSED→**FROZEN**。
- 反转 memory `aionis-publication-framing-option-a`（2026-08-08 addendum 记录的"勿追新 alpha"，仅此纪律路径）。

**关键纪律**：本轮**未跑任何 adaptive learner、未观察任何 OOS metric**（`config_committed BEFORE result`）。下一步 = `scripts/track_adaptive_run.py`（扩窗月重训 + OOS + `IC_diff` + HAC + DSR + H6 双跑）；首次 OOS 结果入**新 ledger 行**。

**边界**：本轮 `scripts/track_adaptive_commit.py`（新）+ `runs/ledger.jsonl`（+1 行 #51）+ `docs/track-adaptive-preregistration.md`（FROZEN）+ state；**0 既有 frozen/prereg/ADR/config 改动**（新增独立行，不触 Track C #49 null）；未跑 research/forward。

## 2026-08-07 (a) 路径 A 上线 — 校准概率读数 + 板块聚合 + 公司名 + 诚实 null 免责

业主反馈"量化选股策略但没体现选股、ticker 没有公司名、要涨跌概率、要实时数据"。批判性自审后业主授权**路径 A**（保守：校准概率 + 板块 + 公司名 + 条件式读数 + 反泄漏护栏，非 trading bot）。`bb83117` 已 push origin/main。

**新增 3 模块（0 新 runtime deps）**：
- `src/aionis/eval/score_calibration.py` — Platt（默认）/ isotonic 校准：score → P(forward_return>0)，per-region，fit on realized OOS history，latest month 预测 OOS。**反泄漏契约**：latest month 从 fit 排除（NaN fwd_return drop），walk_forward=False 披露。**诚实 null 信号**：实测 US spread=0.20（prob range [0.42, 0.61]），CN spread=**0.05**（[0.44, 0.49] 基本平坦 = 模型承认无法区分涨跌）。
- `scripts/build_ticker_metadata.py` — cache ticker→(name, sector)：A 股 GitHub listing（5207 CN，`ZhuLinsen/daily_stock_analysis` 公开数据）+ SEC company_tickers.json（10398 US，公共域）+ EDGAR SIC map。25/25 picks 有公司名（海光信息/寒武纪/兆易创新/Coinbase 等）。
- `tests/test_score_calibration.py` — 15 hermetic 测试（单调性、null→紧 range、强信号→宽 range、反泄漏 latest-excluded、per-region、JSON round-trip）。

**enriched export（`export_terminal_data.py`）**：
- `export_picks`：**per-region 选择**（US top-10 + CN top-10 long；3+2 short），enriched name+sector+prob_up。**修了一个 bug**：原 global-latest（2026-08-03 = CN）静默丢掉 US（latest 2026-06-30）→ per-region latest 修复。
- `export_sector_breakdown`：板块聚合 mean score + mean P(up)，top/least favored。A 股 sector "Unclassified"（诚实标注非隐藏）。
- `picks_meta.json`：校准 meta + 诚实 null 免责。

**前端**：`picks-view.tsx` 重写（per-region 分组 + 双行渲染 name/ticker/sector + prob_up chip 按 base_rate 距离着色 + null 免责 banner）；新 `/sectors` 页（板块排行 + favor bar + 免责）；sidebar 加 Sectors；i18n zh+en。`pnpm build` exit 0。

**验证**：6 新 web 契约测试（enriched schema + 双 region 覆盖 + 校准披露 + sector shape + unclassified 披露）；27/27 新测试绿；全套 pytest exit 0；ruff clean（顺带修了 cot_fetch/form4_fetch 2 个预存 lint）；build exit 0。

**边界**：本轮 web/ + scripts/ + src/aionis/eval/ + tests/ + state；**0 ledger / frozen / prereg / ADR / config / E3**；无 real network/LLM/trial。校准是 display utility（类比 ff5_residual），不写 ledger，不改研究结论（rank-IC −0.0088 NULL 不受影响）。

**诚实 null 的可视化**：top picks（score +2.28 海光信息）的 prob_up = **0.444**（<base_rate 0.4751）= 模型在 CN 的轻微反向信号；top 板块（Natural Gas Transmission）mean prob = 0.484 ≈ base rate。概率聚集在 base rate 附近 = NULL 的概率空间可视化。

**待业主**：① 审线上 `/picks` + `/sectors`（部署后）② 实时价格（Alpaca 免费层 + GitHub Actions cron，下一切片）③ A 股 sector（需申万/东财行业源，当前 Unclassified）④ push 已完成。

## 2026-08-06 (j) Form 4 /insiders 升级 5-issuer（真实大额内部人卖出）+ COT 10-市场代码就绪

业主授权"优化到不能优化"。两条并行收尾：

**Form 4 /insiders 5-issuer 升级（真实数据，已 re-export）**：
- `scripts/form4_fetch.py` 跑通 5 大盘（AAPL/MSFT/NVDA/GOOGL/AMZN，2024-01..2026-06）→ `form4_aggregate.parquet` 2415 txns（4 buys / **2411 sells**）/ 62 内部人 / 5 issuer。
- top 内部人：**Jensen Huang 720 卖**（NVDA CEO 10b5-1 密集减持）、Pichai 227、Kress 190（NVDA CFO）、Hennessy 123、Herrington 107。NVDA 内部人卖出信号极强（1271/1272 是卖）。
- export_form4 re-run → `form4.json` 5-issuer。契约测试 `test_web_terminal_data` 仍绿（action buy/sell + buys/sells int）。

**COT 多空压力 10-市场代码就绪（数据刷新延后）**：
- `scripts/cot_fetch.py` 升级 10 市场跨资产集（S&P/Nasdaq/Russell/VIX/WTI/Gold/Silver/Copper/Euro FX/Yen）+ per-year resilient（cftc 单年超时跳过，不中断）。
- cftc.gov 当前 SSL/Connect 不稳（2024-2026 全 timeout/SSL），10-市场数据刷新延后；6-市场 parquet 保留（live cot.json 仍有效）。cftc 恢复后一键 `cot_fetch.py` → 10 市场。

**边界**：本轮 `web/src/data/aionis/form4.json`（5-issuer 真实）+ `scripts/cot_fetch.py`（10 市场 + resilient，已 commit 77f6311）+ state；**0 ledger / frozen / prereg / ADR / config / runs-data / E3**；Form 4 SEC 公共域（filed-date PIT）；COT 公共域。

## 2026-08-06 (i) 多空压力指数（CFTC COT）上线 —— 调研落地，free/no-API/公共域

业主问"散户情绪 + 多空资本流能不能找 free/no-API 源"。派 2 sonnet 调研 agent **都 [1210] fail** → opus 主线直接 web 搜索完成。**批判性结论（不对称）**：散户情绪**结构性受阻**（StockTwits 同 Reddit 式审批门；Google Trends 官方 API 2025-07 alpha 只给极少数、pytrends 脆弱 scrape + 修订）；多空资本流**干净可得**（CFTC COT + FINRA 空头）。业主授权做最有价值项 → 做**多空压力指数**。

**CFTC COT 多空压力指数 `/positioning`（已上线）**：
- 数据：CFTC Commitments of Traders（free、**无 API**、US 政府公共域、周频、归档快照**不可修订** = 最干净 PIT）。复用 MIT [`cot_reports`](https://github.com/NDelventhal/cot_reports)（0 造轮子）。
- 6 市场（legacy_fut，精确名匹配）：S&P 500 / Nasdaq 100 / VIX / WTI / Gold / Copper（US Dollar + 10Y Treasury 在 TFF 报告，legacy 缺，留 enrichment）。
- 构造：净非商业持仓 = Long−Short；52 周滚动 z-score（拥挤度）。综合 = 跨市场 mean z + 拥挤度强度 + 78 周 composite_series。
- 实测（2026-07-28）：composite z +0.19，crowding 0.9；S&P z+2.09（空头回补）、Nasdaq z−1.22（净空拥挤）、Gold 净多 +182k。
- 模块：KPI（composite z / crowding / latest）+ 综合 z 时序（recharts）+ **各市场 diverging z 条**（← 净空拥挤 / 净多拥挤 →，emerald/rose）+ methodology。

**脚本**：`scripts/cot_fetch.py`（cot_year × 3 年 legacy_fut → 精确名过滤 → net + 52w z → `data/cache/cot_aggregate.parquet`）。`export_cot`（读 parquet → `cot.json`，awaiting_fetch guard）。pyproject dashboard extra += `cot_reports>=0.1.3`（MIT permissive ✓）。

**散户情绪（诚实 decline）**：无干净 free/no-API/permissive/PIT-stable 源；Reddit 待激活；情绪维度由 Aionis 独有"选股确信度"覆盖。

**边界**：本轮 `scripts/cot_fetch.py` + `export_terminal_data.py`（export_cot）+ `pyproject.toml`/`uv.lock`（cot_reports MIT）+ `web/`（positioning 模块 + cot.json）+ state；**0 ledger / frozen / prereg / ADR / config / runs-data / E3**；COT US 政府公共域 permissive（filed 周五，归档不修订）；无 API（bulk CSV via cot_reports）。

## 2026-08-06 (h) Form 4 内部人模块上线（真实数据）+ 两个 parser schema bug 修复

业主问"为什么需要邮箱，能否避免" → 实测**能避免**：SEC 对 polite + 占位 UA + 小规模容忍（AAPL EFTS 返回 26 条无 429；Aionis 现有 584 个 13D 也是占位 UA 拉的）。

**跑通真实 fetch + 暴露/修了两个 parser schema bug**（agent fixture ≠ 真实 schema → 空洞绿，[[aionis-agent-dispatch-verification]] 既定 failure mode）：
1. **transactionCode A/D 错误**：parser 初版过滤 `transactionCode ∈ {A,D}`——但 SEC 惯例 `transactionCode = P(买)/S(卖)/M(行权)/A(award)/F/G`；A/D 是 `acquiredOrDisposedCode`（direction，**另一元素**）。修为 P/S（open-market）。AAPL 实测：nonDeriv codes = {S:83, M:54, F:31, G:8}（83 真实销售）。
2. **transactionDate 双 schema**：parser 初版只读 legacy `<year>/<month>/<day>`，但 SEC X0508+ 用 `<value>YYYY-MM-DD</value>`。真实 AAPL 申报用新 schema → 全 drop（110 文件 0 产出）。修为 dual-schema（value 优先，fallback year/month/day）。加 regression test 锁定。

**结果**：AAPL 近 2.5 年 → **83 真实内部人 SELL**（Tim Cook 21 / Katherine Adams 16 / Arthur Levinson 等 9 内部人，真实 shares + price）。`form4.json` status=ok。

**模块**：`/insiders` 上线（KPI buys/sells/insiders + top insiders + 近期交易流 + methodology）。sidebar alternative 组加内部人。`export_form4` 读 `form4_aggregate.parquet`（`scripts/form4_fetch.py` bounded 拉取，5 大盘 issuer；AAPL 已跑 + cache，多 issuer 一键扩）。

**复用 + 验证**：`_policy_get`（polite）+ `stakes_13d_efts` cache 模式 + `parse_form4_xml`。ruff clean + **21 测试绿**（含 new-schema regression）。**主线亲自验证**（re-parse 110 AAPL → 83 sells，非 agent 自述）。

**边界**：本轮 `src/aionis/ingest/form4*.py`（P/S + dual-schema fix）+ tests + scripts（`export_form4` + `form4_fetch.py`）+ web（insiders 模块 + `form4.json` 真实数据）+ state；**0 ledger / frozen / prereg / ADR / config / runs-data / E3**；Form 4 SEC 公共域 permissive（filed-date PIT）；占位 UA（SEC 容忍，业主无需邮箱）；AAPL 单 issuer 真实数据（多 issuer `form4_fetch.py` 一键扩）。

**待业主**：① 审 `/insiders`（真实 AAPL 内部人销售）② 多 issuer 扩展（跑 `form4_fetch.py`，~10min，加 MSFT/NVDA/GOOGL/AMZN）③ Quarto/旧站去留。

## 2026-08-06 (g) Form 4 XML orchestrator（opus fallback）+ export_terminal_data ruff bugfix

- Form 4 orchestrator agent (sonnet) **[1210] API 错失败**（memory 既定 proxy 不稳）。按 handoff 策略（agent fail → orchestrator opus 直接接），主线写 `src/aionis/ingest/form4_orchestrator.py`：
  - accession → EDGAR Archives `index.json` → pick Form 4 doc（robust `directory.item[]`/`items[]` schema，prefer `.xml` → accession `.txt` → fallback）→ fetch XML → parse（复用 `parse_form4_xml`）。
  - 复用 `_policy_get`（≥2s polite）+ 幂等 cache（index + xml 分别 cache）。`fetch_form4_transactions` 批量 + 容错（单 filing 失败不中断）。
  - `tests/test_form4_orchestrator.py`：9 hermetic 测试（monkeypatch `_policy_get`/`fetch_form4_filings`），URL 构造 / doc 选择 / 幂等 cache / parse pipeline / batch / empty。**9/9 绿**。
- **修了 `export_terminal_data.py` 的真实 lint bug**（之前 commit 没跑 ruff，疏忽）：B905 `zip()` 无 `strict=`（加 `strict=True`，长度不等即报错更安全）+ F841 `rl` 死变量（删）+ E501 长行（events label / reddit description，per-file-ignore 同 `build_static_site` 惯例）。**full repo ruff 现全 clean**。

**模型分层 + 复用账**：sonnet agent（[1210] fail）→ opus 主线 fallback（orchestrator + 验收）。复用 `_policy_get` / `parse_form4_xml` / `stakes_13d_efts` cache 模式。**0 造轮子**。

**边界**：本轮 `src/aionis/ingest/form4_orchestrator.py` + `tests/test_form4_orchestrator.py` + `scripts/export_terminal_data.py`（bugfix）+ `pyproject.toml`（per-file-ignore）+ state；**0 ledger / frozen / prereg / ADR / config / runs-data / E3**；无真实 EDGAR fetch（hermetic）。

**Form 4 可见模块**：ingest（efts + parser）+ orchestrator（fetch + parse pipeline）**都就绪 + 验证**。离可见仅差：① 真实 fetch 授权（bounded CIK 集 + 近窗）② SEC User-Agent 真实邮箱（现占位 `contact@example.com`）。业主给邮箱 + 授权后一次性跑通 → 终端模块。

## 2026-08-06 (f) Form 4 内部人 ingest — sonnet agent 交付，独立验证通过，已合并

agent (sonnet, worktree) 交付 Form 4 ingest；按 [[aionis-agent-dispatch-verification]] **独立核验（不信自述）**：
- `form4_efts.py`（152 行）：EFTS Form 4 metadata client，复用 `_policy_get`（≥2s polite）+ 幂等 disk cache + exp-backoff（transient only，4xx fast-fail）+ pagination。VERIFIED efts query（10-digit CIK + forms=4 + dateRange）。不 auto-fetch。
- `form4.py`（267 行）：XML parser，SEC `<value>` wrapper + nonDerivativeTable + transactionCode A/D 过滤 + shares/price 校验 + frozen dataclass。
- `docs/data-intake-edgar-form4.md`（177 行）：7-gate 全 PASS（SEC public domain G1✓ / filed-date PIT G2✓ / immutable G3✓ / exploratory G5 / polite G7）。
- `tests/test_form4.py`（409 行）：11 测试，5 XML fixture + 3 inline edge，assert **真实值**（CIK/ticker/date/A-D/shares/price/dtype/sort）+ degeneracy（empty/malformed/missing-filer/derivative-only/invalid-code/negative-shares）——**非空洞绿**。

**独立验证（我跑，非 agent 自述）**：ruff clean + pytest **11/11 passed**（main env, python 3.13.7）+ collection 无 error。merge-base 干净（worktree 落后 main 仅 conviction commit，无冲突）+ 0 frozen surface。

**Form 4 可见模块的剩余门槛（诚实）**：
- efts client 只给 metadata（accession list）；要真实交易需 **XML-fetch orchestrator**（按 accession 拉 EDGAR XML + parse）—— agent 未做（scope 外），是下一切片。
- User-Agent 占位 `contact@example.com`（SEC fair-access 要真实邮箱）—— 真实 fetch 前需业主邮箱。
- 真实 fetch 业主授权（bounded：小 CIK 集 + 近窗，polite ≥2s）。

**模型分层 + 复用账**：opus 主线（选股确信度方法论判断 + Form 4 验收判断）+ sonnet agent（Form 4 ingest 工程，复用 stakes_13d 模式，worktree 隔离并行）。复用：`_policy_get`/`http_policy`（polite）+ `stakes_13d_efts` 模式 + structlog。**0 造轮子**。

**边界**：本轮 `src/aionis/ingest/form4*.py` + `docs/data-intake-edgar-form4.md` + `tests/test_form4.py`（全 additive）+ state；**0 ledger / frozen / prereg / ADR / config / runs-data / E3**；Form 4 SEC public domain permissive；**无真实 EDGAR fetch**（hermetic only）。

## 2026-08-06 (e) 选股确信度指数（Aionis 独有模型元信号）+ Form 4 内部人 ingest（agent 并行中）

业主 `/goal` 授权推进推荐项（批判性比对 + agents 并行 + 模型分层 + 复用轮子禁造）。

**批判性修正**：原"选股确信度"想用峰度 → 不严谨（语义模糊）。改用**截面分散度（std + top/bottom decile spread）**，标准因子研究方法（Kelly-Pruitt-Su），有学术依据。

**选股确信度 `/conviction`（Aionis 独有，已上线）**：
- 数据：`track_c_confirmatory_oos_scores`（94k 行）→ 每月截面 std + decile spread
- 逻辑：latest std (0.6752) > trailing 12m mean (0.5763) → **high conviction**（模型当前找到清晰赢家）；低分散 = 低确信 regime（动量易失效）
- 复用：标准因子研究分散度概念（非 alphalens 库依赖，简单 std，避免造轮子）；recharts dual-line 图（std + decile_spread）
- export_pick_conviction + conviction-view（KPI + 时序图 + methodology callout）；sidebar insights 组加确信度

**Form 4 内部人 ingest（sonnet agent, worktree 隔离, 后台并行）**：
- 复用 `stakes_13d_efts` + `stakes_13d` 模式，EDGAR EFTS Form 4，7-gate doc + hermetic 测试，mode=exploratory
- 学术依据：Lakonishok-Lee 2001 / Cohen-Malloy-Pomorski 2012（内部人交易经典信号）
- agent 进行中（worktree 不干扰主线），回报后核验+集成（[[aionis-agent-dispatch-verification]]：不信 agent 自述，验 worktree diff + 测试）

**模型分层 + 复用账**：opus 主线（方法论判断 = 选股确信度定义）+ sonnet agent（Form 4 工程，复用 13D 模式）；选股确信度复用标准因子分散度（非自造指标）+ recharts（非自造图）。

**边界**：本轮 `web/src/`（+conviction）+ `scripts/export_terminal_data.py`（+export_pick_conviction）+ state；**0 ledger / frozen / prereg / ADR / config / runs-data / E3**；oos_scores 是已有 PIT 产物（派生分散度，非新数据）；Form 4 agent 在 worktree。

## 2026-08-06 (d) EDGAR 13D 聪明钱动向模块（Reddit 被政策闸门挡后的真实另类数据替代）

业主选 A（用 Aionis 已有 EDGAR 另类数据替代被 Reddit 拦截的散户热度）。

- **Reddit 现实**：业主点 create app 被 Responsible Builder Policy 直接拦截（2025-11 self-service API 关闭 + 新 app 须 approval，社区广泛报告被卡/拒）。Aionis 侧无法绕过。Reddit 页保持诚实"待激活"。
- **13D 数据**：`data/cache/efts_13d_<CIK>_*.json` 584 文件（历史 EFTS full-text-search），2872 条申报 / 417 机构 / 最新 **2024-12-16**（数据窗口到 2024-12，cached pulls 略滞后，真实但非实时）。SEC 公共域 permissive，filed-date PIT。
- **8K 数据不足**：`earnings_8k_forward_raw_20260731` 只有 1 条 T0/cik=1 测试条，跳过。
- **export_smart_money**：聚合 584 文件 → 近 60 申报 + 最活跃 10 机构（active #1 = Bank of America 44 次）。
- **修复一个 bug**：初版把 EDGAR `display_names[0]` 当 filer、`[1]` 当 target——反了。13D 惯例 `[0]`=subject company(issuer/target)、`[1]`=filer(reporting person/smart money)。证据：原 recent #1 显示 filer="CARVANA CO." target="GARCIA ERNEST C. II"（自然人不可能当 issuer）→ 修正后 filer=Garcia、target=Carvana(CVNA)，语义正确。
- **模块** `/smart-money`：KPI(total/filers/latest) + 最活跃机构排行 + 近期申报流（filer→target + ticker + new/amendment badge）。sidebar"另类数据"组加聪明钱。

**边界**：本轮 `web/src/`（+smart-money）+ `scripts/export_terminal_data.py`（+export_smart_money + 13D swap fix）+ state；**0 ledger / frozen / prereg / ADR / config / runs-data / E3**；13D 是 SEC 公共域 permissive（filed-date PIT，真实历史）；Reddit 仍待激活（政策阻塞，非 mock）。

**待业主**：① 审 `/smart-money` 观感 ② 13D 数据滞后到 2024-12（cached pulls），要不要重拉 EFTS 刷新到最新 ③ Reddit 是否走 approval（不阻塞当前）。

## 2026-08-06 (c) special 另类数据模块 — TACO 指数 + Reddit 散户热度

业主要求加小隐寺式 special 数据模块（Reddit 热门 + 川普 TACO 指数）让终端"更真实可靠"。

**反泄漏约束下的诚实实现**（CLAUDE.md `No mock/synthetic data in the real pipeline` + 7-gate）：
- **TACO 压力指数**（`/taco`）：真实 VIX（FRED ALFRED permissive，260 点 daily）+ 公开事件表（5 条 2025 川普关税事件，FT/CNBC/ABC 可证，**labeled 非 mock**）+ methodology callout 明示"示意性方法论，非 Aionis 研究 claim"。TACO 本身是 2025-04-09 起源的新闻 meme（FT Robert Armstrong coined），**无权威量化指数/数据集**。
- **Reddit 散户热度**（`/reddit`）：诚实标注"forward collector 待激活"。Aionis 已内置 `reddit_sentiment.py`（PRAW 8.0.2 + FinBERT，7-gate cleared，exploratory，**forward-collection only / no backfill**）但**从未激活 → 0 snapshots**。模块显示 collector 信息 + 7-gate clearance + 激活方法（配置 `REDDIT_CLIENT_ID/SECRET` + 跑 collector）。**不塞 mock 数据**。

**执行**：`export_terminal_data.py` += `export_taco`（VIX from `data/cache/alfred_VIXCLS.json` + 事件表）+ `export_reddit_meta`（status=awaiting_activation）。web += 2 view（taco-view: VIX recharts 图 + 事件表 + 计数 KPI + methodology callout；reddit-view: 状态卡 + 说明 + howto + 空 placeholder）+ 2 page + sidebar"另类数据"组 + i18n keys。

**验证**：poc dev `/Aionis/taco` + `/Aionis/reddit` HTTP 200 + 截图（terminal-taco-zh / terminal-reddit-zh）。

**边界**：本轮 `web/src/`（+taco/reddit 模块）+ `scripts/export_terminal_data.py`（+taco/reddit）+ state；**0 ledger / frozen surface / prereg / ADR / config / runs-data / E3**；VIX 是 FRED 公共域 permissive；事件表公开新闻 labeled；reddit 无数据（诚实标注，非 mock）；未触 E3；未激活 reddit collector（待业主 creds + GO）。

**待业主**：① 审 TACO/Reddit 模块观感 ② 是否激活 Reddit forward collector（需 `REDDIT_CLIENT_ID/SECRET` + 跑 collector ~分钟级）→ 真实散户热度榜 ③ TACO 事件表是否扩/调 ④ 方法论 illustrative 标注是否足够诚实。

## 2026-08-06 (b) 前端转向 fintech 数据终端 — Next.js + shadcn 复刻小隐寺风（已部署）

业主反馈：Quarto 学术站方向错（忘"个人兴趣研究、不公开发表"定位）+ 语言 tab 分页错（要单独切换按钮）+
要 **小隐寺数据中心 https://data.xiaoyinsi.com/ 那种金融科技风**（卡片墙、实时榜、数字密集）+ 加选股决策模块。
方法：深入研究小隐寺 → 找开源仓库复刻 → 不手搓。

**调研**：小隐寺 = Next.js 黑白极简（theme #fafafa/#000）另类数据终端（Reddit 情绪/政客交易/13F/IPO），
**不开源**（github 只有 investing-for-beginners 投资百科）。最佳相近 = **[abderrahimghazali/shadcn-fintech](https://github.com/abderrahimghazali/shadcn-fintech)**
（Next.js 16 + shadcn/ui + Tailwind v4 + recharts + live ticker + 深色模式 + 拖拽）。复刻基础。

**执行**（复用 shadcn-fintech 设计系统 + 组件，0 手搓；替换所有个人理财页面为 Aionis 模块）：
- clone shadcn-fintech 到 scratch `/home/re/code/aionis-web-poc/`，复用其 shadcn ui 组件库 + Tailwind oklch 黑白主题 +
  `live-ticker`（marquee 滚动）+ next-themes 深色 + Geist 字体。
- 新建 i18n（`src/i18n/`：context + localStorage + 中/英字典 + `LangToggle` 独立切换按钮，非 tab 分页）。
- 新建 Aionis 数据模块（学小隐寺卡片墙）：
  - **Overview**（`/dashboard`）：Hero + 5 KPI 卡 + 评分滚动条 + 选股预览 + 模块卡网格。
  - **选股决策榜**（`/picks`）：top-20 多头 + 5 空头，排名 + ticker + region + 模型评分 + 排名变化箭头（学散户情绪榜）。
  - **证据墙**（`/evidence`）：14 null 卡片流 + 统计计数（学政客交易卡片流）。
  - **Power Floor 监测**（`/power-floor`）：n_min KPI 三联 + look 表 + recharts σ_obs-vs-σ_null 散点。
  - **反泄漏仪表盘**（`/discipline`）：6 状态卡（PIT/embargo/H6/ledger/2-tail/k=1，全 PASS）。
- 删个人理财页面（accounts/transactions/transfers/cards/budgets/crypto/analytics/investments/sign-in/sign-up/...）。
- `next.config.ts`：`output: export` + `basePath: /Aionis`（GitHub Pages 静态导出）。
- 数据：`scripts/export_terminal_data.py`（复用 `export_quarto_data` 共享载荷 + 加 picks/shorts/metrics 从
  `track_c_confirmatory_oos_scores.parquet` 94438 行），输出 `web/src/data/aionis/*.json`（8 tracked JSON）。
- 修一个 build 阻塞：`ic_monthly.json` 含非法 `NaN`（CN 某月缺失）→ export 加 `pd.isna`→null + `allow_nan=False`（`export_quarto_data.py` 同修）。
- recharts Tooltip formatter 类型修正（value 含 undefined）。

**验证**：本地 `pnpm dev` 5 页全 200 + 截图（terminal-overview/picks/evidence/power-floor，深色中文 fintech 风）；
`pnpm build` exit 0，8 路由静态导出（含 `output: export`）。语言切换按钮工作（中/EN toggle）。

**移植 + 部署**：cp Next.js 项目到 `Aionis/web/`（排除 node_modules/.next/out）+ `scripts/export_terminal_data.py` +
`web/.gitignore`。CI `.github/workflows/deploy-pages.yml` 改为 pnpm + Node 22 → `pnpm build` → 部署 `web/out`。

**边界**：本轮 `web/`（新 Next.js 终端）+ `scripts/export_terminal_data.py` + `scripts/export_quarto_data.py`（ic_monthly sanitize）+
`.github/workflows/deploy-pages.yml`（Node 部署）+ state；**0 ledger / frozen surface / prereg / ADR / config / runs-data / E3 改动**；
web/src/data/aionis 是聚合 tracked JSON（非 frozen，从 gitignored runs/ 派生，类似 Quarto data 模式）；未跑 confirmatory/forward/strategy；
未触 E3。Quarto 站（`quarto-site/`）+ 旧站（`site/` + `build_static_site.py`）暂留 repo 不部署，待业主后续定去留（降级方法子页 / 归档 / 删）。

**待业主**：① 审线上 fintech 终端（部署后 https://rethymus.github.io/Aionis/）② Quarto 站 + 旧 site/ 去留（降级/归档/删）③ 选股榜是否加 forward-return 涨跌列（当前仅模型评分 + 排名变化）④ 是否加"实时感"（当前数据是 frozen 快照，非实时流）。

## 2026-08-06 (a) 研究站点前端改造 — Quarto 品牌化 + 交互表 + 复用轮子（本地验证完成，待业主授权提交/部署）

业主反馈：线上静态站（`site/index.html`，`scripts/build_static_site.py` 474 行手搓 HTML）"观感廉价、没复用
开源、别造轮子"。**诊断**：旧站生成层纯手搓（Tailwind/plotly 是轮子但拼装手搓）；本地在途 `quarto-site/`
（未提交）方向对（Quarto=Posit 学术发布轮子）但停在"默认 cosmo 模板"——没用 brand/value-box/itables，
CI 未切换，本地无 quarto。

**调研（现成轮子，全部直接复用，0 手搓）**：`_brand.yml`（[Posit brand-yml](https://posit-dev.github.io/brand-yml/)
+ [Quarto brand 文档](https://quarto.org/docs/authoring/brand.html)）；**itables** MIT（[Quarto 官方推荐交互表](http://itables.org/quarto.html)）；
Quarto dashboards/callouts/columns（v1.4+ 内置）；[Awesome Quarto](https://github.com/mcanouil/awesome-quarto) 范例。

**执行**：
- 本地装 **Quarto 1.10.18**（预编译单二进制 → `~/.local/bin/quarto`，不污染系统；CI 用 `quarto-dev/quarto-actions/setup@v2`）。
- `pyproject` quarto extra += `itables>=2.2` + `plotly>=5.18`；`uv lock` → itables v2.9.1（MIT，permissive-only 合规）。
- 新建 `quarto-site/_brand.yml`：语义色板（灰=CV-proxy / 蓝=chron / 红=confirmatory / 琥珀=power-floor / navy=primary）
  + 衬线标题 + 无衬线正文（**系统字体栈，无 webfont CDN，离线可复现**）。callout-important/warning/tip 直接对上 brand danger/warning/success。
- 升级 `_quarto.yml`：brand + search(overlay) + navbar(primary+icon) + docked sidebar + page-footer + open-graph/twitter-card
  + bread-crumbs + back-to-top + reader-mode + code-link。
- `scripts/export_quarto_data.py` += `export_ic_monthly()`（71 月 confirmatory IC 时序 2021-01..2026-06，tracked `data/ic_monthly.json`）。
- 重写 3 `.qmd`（英文默认）：`index`=callout KPI 三联（−0.0088 / NOT_EQUIVALENT / PASS）+ verdict + contribution；
  `results`=**itables 交互 evidence 表**（搜索/排序/分页）+ forest plot + 71 月 IC 时序 + bps 衰减曲线（plotly 品牌配色 + plotly_white）；
  `power-floor`=callout KPI（72.5/48.3/36.2 年）+ itables look 表 + σ_obs-vs-σ_null 散点。修正旧 `::: callout note` → 标准 `::: {.callout-note}`（fenced-div warning 清零）。
- 新 `tests/test_quarto_site_data.py`：11 契约测试（tracked `data/*.json`，hermetic，不依赖 runs/）——evidence 14 行 +
  confirmatory estimate −0.0088 + 所有 CI 跨零 + power-floor 3 looks/纯噪声界 + sigma excess≥2.0 + bps net 单调/gross 恒等 +
  ic_monthly 71 月/combined mean≈−0.0088。**11/11 绿**。

**验证**：本地 `quarto render` 三页全过（4 plotly 图执行 + itables JS 注入 + **0 warning**）；三页截图存（new-overview/
new-evidence/new-power-floor）；`ruff` clean；`pytest --collect-only` 无 error；代表性 `test_rank_ic` 绿。
（运维注：`uv sync --extra quarto` 会把 venv 同步成"仅该 extra"子集态 → 临时 `No module named pandas`；re-sync 全 extras 即修复。
CI workflow 用 `--extra dashboard --extra quarto` 不受影响。）

**发现的既有不一致（flag，未擅自改）**：`evidence.json` 实 **14 行**（`#12` 缺失），与项目"15 条 null"叙事 + manuscript
draft 表行数冲突。站点统一改为"14 configurations"（诚实）。若要 15，需业主确认 `#12` 对应哪条结果（疑似 Track C CN rank-IC
mean 0.0098 / p 0.46）后补。

**复用轮子账（回应业主诉求）**：Quarto（Posit 学术发布）+ brand-yml（Posit 规范）+ itables（MIT 交互表）+ plotly（交互图）
+ Bootstrap/cosmo（布局）+ callout/columns/tabset（Quarto 内置）= **0 行手搓 HTML/CSS 生成代码**；旧 `build_static_site.py`（474 行手搓）+ `site/` 待新站上线后归档。

**边界**：本轮 `quarto-site/`（新+改）+ `scripts/export_quarto_data.py` + `tests/test_quarto_site_data.py` + `pyproject.toml`
+ `uv.lock` + `.github/workflows/deploy-pages.yml`（前批已改）+ state；**0 ledger / frozen surface / prereg / ADR / config /
runs-data / E3 改动**；未跑 confirmatory/forward/strategy；未触 E3；**未 commit / 未 push / 未外发**（Pages 部署待业主点头）。

**待业主**：① **语言**（默认英文，匹配 manuscript/arXiv 英文化；若要中文/双语告知）② **授权 commit + push → CI 部署 Pages**
（外发，CI `quarto render quarto-site` → 公开站取代旧 `site/`）③ evidence `#12` 是否补（14 vs 15）④ 旧 `site/` +
`build_static_site.py` 何时归档。

## 2026-08-05 (i) power-floor 理论推导 — 纯噪声界 + ML 噪声超额（机制性定理）

业主第三次问"最具价值方向" + Stop hook 纠偏（自审通过即执行，勿再请示）。批判性过滤后选 power-floor
理论推导（唯一能显著抬高王冠贡献的方向；其余 ceremony/diminishing）。自审循环通过（闭式可推、复用既有
面板、不触冻结面）→ 直接执行。

**核心数学事实**：横截面 Spearman rank-IC 在无预测力零假设下 σ_null = 1/√(N−1)（闭式）。
N=462→0.047，N=929→0.033，N=1386→0.027。但 Aionis 21 个 IC 系列实测 σ(IC) 一致地是 σ_null 的
**2.0-4.4×（median 3.41×，min 2.03×，无例外）**。

**机制性结论**（比"σ≈0.10 floor"更精确诚实）：
- 纯噪声界 σ=0.047 时 look-3 n_min = (1.96×0.047/0.010)² ≈ **83 月 < 120** → 纯噪声本可在 look-3 达等价。
- 实测中位 σ=0.109 时 look-3 n_min ≈ **456 月** → 不可行。
- **power floor 不是纯数学必然，而是由 ML 噪声超额驱动**（拟合噪声 + 异方差 + 重叠）——稳健跨 21 系列。

**交付**：
- `scripts/ic_pure_noise_bound.py` — 算 N_cross（从中位 OOS 面板）+ σ_null + σ_obs + 超额比；21 系列。
  ruff clean。`runs/ic_pure_noise_bound.json`（gitignored）。
- `tests/test_ic_pure_noise_bound.py` — 6 测试（闭式 1/√(N−1) 正确性 + 单调 + 已知值 + N<2 NaN + n_cross_eff
  中位/分区/min-max + 缺列空）。6/6 绿。
- `reports/design/2026-08-05-power-floor-theoretical-derivation.md` — 闭式推导 + 21 系列超额表 + 机制分解
  （ML 拟合噪声/异方差/重叠）+ refined honest claim（"floor = 纯抽样界 + ML 超额"，非"σ≈0.10 规律"）。
- `manuscript/main.tex` §5.3 — 加"Theoretical pure-noise bound and the ML noise excess"子节
  （power-floor 升为"理论 + 经验 + 文献"三支撑）。

**批判性自审记录**（业主要求）：① 纯噪声界 0.047 < 实测 0.10，会否削弱？→ 不削弱，反而更 sharp（floor
由超额驱动，非纯界）；② 推导会否成兔子洞？→ 限定为闭式界 + 经验超额，不推一般理论；③ 外部 GKX 验证？
→ 先不做（可行性未证），内部 21 系列 + 闭式已足。

**边界**：本轮 1 新 script + 1 新 test + 1 新 note + manuscript §5.3 编辑 + state；**0 ledger / frozen surface /
prereg / ADR / config / data / E3 改动**；未跑 confirmatory/forward/strategy/research；未触 E3；未外发。

## 2026-08-05 (h) arXiv preprint scaffold（rec #2；framing a；PREP，未上传）

owner approved framing **(a)**（power-floor 定理为 lead）+ LaTeX 预制。交付 `manuscript/` 三件套：
- **`manuscript/main.tex`** — arXiv 通用 `\documentclass{article}`（仅标准宏包 amsmath/booktabs/hyperref/natbib；
  无自定义 .cls → 任何 TeX Live/Overleaf 可编译）。framing (a) 重排：power-floor 入 abstract+intro，§5 详述
  （n_min 869/580/435 + 跨 20 系列 σ∈[0.092,0.163] 实测）。§4 证据表 15 行；§7 复现声明指向 `docs/replication-availability.md`。
  数字与 ledger #49 + 中文 v1.0 + 英文 v1.0-en 交叉一致。
- **`manuscript/references.bib`** — 6 cited（gu2020empirical/goyal2008comprehensive/grinold1999active/lakens2017
  = WebSearch verified；schuirmann1987/jennison2000group = 标准 methods）+ 5 标准 extras（neweywest/obrienfleming/
  dieboldmariano/ke2017lightgbm/deprado2018）供扩展。
- **`manuscript/README.md`** — 构建（latexmk / Overleaf）+ framing 说明 + provenance + prep-to-submission gaps（诚实：
  uncompiled / 引用细节待确认 / 无图 / 作者占位 / venue 待选）+ elsarticle 可在定 venue 后替换。

**验证（无本地 TeX 工具链，无法编译）**：结构性自查——9 \begin = 9 \end，环境全配对
（abstract/center/enumerate/itemize×2/table/tabular×2），6 cite key 全部在 .bib 定义。

**边界（关键）**：owner 批准的是**预制**，**非上传**——arXiv 上传是不可逆外发，仍需业主单独点头。
本轮纯新建 `manuscript/` + state；**0 ledger / frozen surface / prereg / ADR / config / data / E3 改动**；
未跑 confirmatory/forward/strategy/research；未触 E3；**未外发**（无 arXiv 上传）。

**待业主**：① 在 Overleaf/自带 TeX 首次编译（修可能的 minor LaTeX 问题，标准宏包风险低）；② **授权 arXiv 上传**
（不可逆外发）；③ venue 定位（CFR/JFEc/RevFin，positioning brief §4）→ venue-specific tailoring（篇幅/强调）；
④ 作者+单位占位填充。

## 2026-08-05 (g) 发表强化 — power-floor 文献锚定 + 复现/数据可用性声明（2 新 PROPOSED 文档）

owner 第二次 `/goal` 授权"推进推荐项 + 批判性比对 + 并行 agents + 分层省 token + reuse-first"。
方向 1（power-floor 文献锚定）+ 互补的复现声明交付。**两 sonnet agent 均 [1210] 失败 → 全 opus §8 fallback**。

- **`reports/design/2026-08-05-power-floor-literature-anchoring.md`** — 把 σ≈0.10 从"我们的观察"升级为
  "有文献支撑的方法学结果"。WebSearch 验证 4 引用（出版商页 403 → 用作者公开 PDF + 搜索摘要）：
  ① **Gu-Kelly-Xiu (2020, RFS)** "Empirical Asset Pricing via Machine Learning"：最佳 ML 月 OOS R² **1.08-1.80%**
  → mean IC ~0.05-0.12 量级（R²≈IC²）；② **Goyal-Welch (2008, RFS 21(4):1455-1508)** 综评预测难度；
  ③ **Grinold-Kahn** *Active Portfolio Management* + Fundamental Law：年化 IR **0.5="good"** ⟹ mean IC/σ(IC)≈0.14
  ⟹ σ(IC)≈7×mean IC；若 mean IC≈0.015 → **σ(IC)≈0.10**（与 Aionis 0.106 量级一致）；④ **Schuirmann (1987) TOST** +
  **Lakens (2017)** equivalence primer（cited 2792）。**诚实边界**：精确 σ(IC)=0.10 的单一标准文献未找到——
  通过 mean IC 水平 + Fundamental Law 间接推断（§5 标注 ⚠️）。但 power-floor 结论稳健：只要 σ(IC)∈0.08-0.15
  文献一致区间，SESOI ±0.010 等价宣告即不可达（look-3 n_min σ=0.08 时 ~21 年，σ=0.15 时 ~58 年）。**推荐强 framing (a)**
  把 power-floor 升为一等方法学贡献（JFEc 计量 / CFR 再检验轨道）。

- **`docs/replication-availability.md`** — reproducible-by-construction 声明（positioning brief §6 标记的审稿人关切）。
  反泄漏纪律即复现契约（`config_committed` ledger + H6 bit-identical + tracked fetch 脚本）；逐源 license 表
  （EDGAR/FRED/ALFRED = US-gov 公共领域可再分发 / Tiingo/Alpaca 需自有 key 不再分发 / baostock A 股 / hanshof+pierrebrunelle
  MIT 成分）；独立方复现步骤（clone → .env → fetch → runner → H6 断言 bit-identical）；cover-letter 简版。
  引用全部核验真实（`.env.example` ✓ / `TIINGO_API_KEY`+`FRED_API_KEY` ✓ / H6 三重断言 ✓ / ledger 行号 ✓）。

**批判性比对（业主"先比对再选择"）**：研究新切片（强基线/LLM eval/新特征）低于产出收尾且重引入"治理>产出"失调；
E3 被 power floor 证可选。剩下自主高价值 = 抬高论文天花板（power-floor 锚定）+ 移除外发摩擦（复现声明）。

**分层 + reuse + 独立性**：2 sonnet `general-purpose` agent 均因 [1210] 失败（positioning→powerfloor 同模式，
WORKFLOW §17 停重试）→ opus §8 fallback 直接写。文献/复用：WebSearch（非 403 出版商页）+ 既有 ledger/脚本引用。
独立性局限：两文档均 opus 自写（非独立 subagent pass，已披露）；数字（climax #49 + power analysis）由既有双独立审计背书。

**边界**：本轮纯 docs（2 新 PROPOSED 文档）+ state；**0 ledger / frozen surface / prereg / ADR / config / data / E3 改动**；
未跑 confirmatory/forward/strategy/research；未触 E3；未外发（无 arXiv 上传）。**未改已定稿的 draft v1.0 / v1.0-en**
（两新文档通过 state + git 可发现；venue tailoring 时由业主决定是否并入引用，避免为边际指针重开定稿）。

**待业主**：① framing 选择（a 强 power-floor / b 中 / c 弱）；② 是否补 σ 直接实证（重算 Gu-Kelly-Xiu 公开 IC 系列 σ，
或合成 IC 噪声实验）；③ arXiv 投稿时把 4 引用并入 `references.bib`；④ 复现 package 形态（仅公共领域子集 + 用户自有 key /
Zenodo DOI 归档——外发需点头）。

## 2026-08-05 (f) 产物化收尾 — 英文 draft + 经济透镜 sweep + venue 定位 brief

owner `/goal` 授权"推进推荐项 + 批判性比对 + 并行 agents + 分层省 token + reuse-first 禁造轮子"。
3 推荐 + 1 fallback 全部交付（4 commit + 1 memory，全 push origin/main）：

- **`e94eac2` feat(site)** — 静态站点 Track C climax section（KPI tile + 表 + power-floor reframing）；
  3 新 hermetic 测试，25/25 绿；CI 部署成功（Pages 已更新）。
- **`3a3c2cf` feat(scripts)** — bps 敏感度 sweep（`track_b_net_cost_sweep_run`，**复用 `net_cost_summary`**，0 造轮子）：
  真实 Track B treatment 面板（ef321e9，125 月）衰减曲线 gross 0.149（bps=0）→ bps=5 0.125（≈0.43 年化，匹配 mount② / draft 引用）
  → bps=20 0.054 → bps=50 −0.088；**break-even ≈31 bps**；turnover 1.1444 跨 bps 恒等。8/8 hermetic 测试绿（含反退化：
  gross 跨 bps 恒等 + net 单调衰减 + 线性 cost scaling + break-even 插值 + _parse_bps 校验）。
- **`52a3d69` docs(draft)** — 英文 v1.0-en（`docs/methods-and-results-draft-en.md`，18KB）：sonnet agent 忠实翻译；
  全部关键数字（−0.0088/0.484/NOT_EQUIVALENT/RCI[−0.051,+0.027]/n_min 869/580/435/36.2y/2.772/99.44%）与 ledger #49
  + 中文 v1.0 交叉核对一致；framing 忠实（null + 纪律 + power-limit，非 equivalence declared）。
- **positioning brief**（本 commit）— `reports/design/2026-08-05-publishable-unit-positioning.md`：venue 匹配决策包。

**批判性比对（业主"先比对再选择"）**：英文 draft 不盲目翻 12KB——venue 决定语气/篇幅/重点，故 positioning brief
与翻译并行（而非串行）。venue 规格 web search 验证：**CFR**（Ivo Welch，免费 boutique，10-20 篇/年，~28 天 turnaround，
"takes more risks"/"all types of documents"，replication/re-examination 导向 = 最高 fit）/ **RevFin**（明示"irrespective
of whether the findings"= null 友好）/ **JFEc**（计量方法 fit，power-floor + J-T 门归宿）/ **Quant Finance**（理论+实证，
rapid）/ **arXiv q-fin.ST**（免费 baseline）。出版商精确页 403 处诚实标注 ⚠️，未编造数字。

**推荐路径**（brief §4）：① arXiv preprint（立即/免费/时间戳）；② CFR 首选（免费 + ~28 天 + null-再检验 fit，
frameworking (a) 反泄漏纪律为主）；③ 备选 JFEc（框架 b 计量）或 RevFin（null 友好）。

**分层 + reuse 合规**：2 sonnet `general-purpose` agent 并行（英文 draft ✅ 交付 / positioning ❌ [1210] 失败）；
positioning 失败 → **opus §8 fallback 直接写**（非独立 subagent pass，已披露）。sweep 复用既有 `net_cost_summary`
（0 造轮子）；CI 复用既有 deploy workflow；定位复用公开 venue 规格。

**独立性局限（披露）**：positioning 非独立 pass（agent [1210] 死，opus 自写）；英文 draft 单 agent + opus 数字核验；
sweep opus 自写 + 8 反退化测试。数字（climax #49 + power analysis）由既有 2026-08-05 双独立审计背书
（power-analysis sonnet review + climax diff review 均 APPROVE）。

**待业主**：① 选 venue 路径（CFR / JFEc / RevFin / 仅 arXiv）；② **授权 arXiv preprint 上传**（外发不可逆，需点头）；
③ framing 选择（a 治理 / b 计量 / c 估计量）；④ 英文 v1.0-en → venue-specific tailoring（brief §4 映射表已给）。

**边界**：本轮纯 docs/scripts(state-only)/state/memory；**0 ledger / frozen surface / prereg / ADR / config / data / E3
改动**；未跑 confirmatory/forward/strategy/research；未触 E3；未外发（无 arXiv 上传）。全套 hermetic pytest exit 0
（仅预存 forward-score/numpy warnings）；ruff clean。

## 2026-08-05 (d) Power analysis — J-T schedule 结构性欠功率（设计级发现，业主决策待定）

climax #49 后的自然跟进："look-1 NOT_EQUIVALENT → look-2/3 能否宣布等价？" opus 直接写
`scripts/track_c_power_analysis.py`（analytic HAC-SE 投影 + block bootstrap 2000 次 + min-n 计算）+
`runs/track_c_confirmatory_power_analysis.json`（gitignored artifact）。

**发现**（用 ledger #49 IC series 噪声 σ≈0.106 + ρ≈0.07，校准自 observed se_hac=0.0126@n=71）：
| Look | z | n_min 宣布等价 | P(equiv) | RCI half med |
|---|---:|---:|---:|---:|
| 1 (60) | 2.772 | 869 月（72.5y）| 0.0000 | 0.037 |
| 2 (90) | 2.263 | 580 月（48.3y）| 0.0000 | 0.025 |
| 3 (120) | 1.960 | 435 月（36.2y）| 0.0000 | 0.019 |

**判读**：look-1 NOT_EQUIVALENT 不是"look-1 太保守"的局部现象，而是**整个 60/90/120 schedule 在
SESOI ±0.010 下的必然状态**。月频 rank-IC 噪声地板（σ≈0.10）使 ±0.010 等价宣告在现实样本量不可达；
E3 forward-live 即使点火也需 ~36 年才达 look-3 等价。**这是诚实的方法学发现（power floor），非 bug**。

**贡献 reframing**（已写进 draft §5/§6）：项目主贡献 = ① 反泄漏纪律作为研究对象（不变）；② 15 条 null
点估计（强 evidence 无 alpha）；③ **power-limit 披露**（J-T ±0.010 在月频 rank-IC 的 power floor）。
非"等价已宣告"。draft §5 的 look-1 框架已从"局部保守"升级为"结构性欠功率"。

**业主 3 选项**（`reports/design/2026-08-05-track-c-power-analysis-options.md`）：
- **A（推荐）** 接受 reframing：不动冻结面，贡献 = null + 纪律 + power-limit。
- B 拓宽 SESOI ±0.025：新 amendment #49b；look-3 (n=120) RCI half 0.019 < 0.025 → 可达等价；
  但 post-hoc "moving goalposts" 嫌疑 + 等价意义减弱。
- C 延长 horizon n=435：不可行（36 年）。

**独立性**：sonnet review of power analysis methodology 派发中（`reports/audits/2026-08-05-power-analysis-review.md`
待回报）。数字由 opus 自算；bootstrap seed=0 pinned（H6 精神）。

**边界**：本轮纯新建 script + design brief + docs(state) 更新；**0 ledger / frozen surface / prereg / ADR 改动**；
未跑 confirmatory/forward/strategy；power analysis 用 gitignored artifact（不改 frozen surface）。

## 2026-08-05 (c) CONFIRMATORY CLIMAX — 首条 confirmatory OOS 入账（ledger #49）

owner D6 GO 授权（"按推荐方式处理 + 难度分层派 agent + 并行不互扰 + 冲突最高价值优先 + 结果不乐观再调整重测"）。
**目标**：把 Track C 联合折叠从 exploratory 升格为首条 confirmatory（项目的 logical climax）。

**判据**：null 在本项目是预期可发表产物，**非"不乐观"**；只有工程 bug（H6 失败 / 退化 / 时序违反）才触发
"调整重测"。实际结果 = null 点估计 + 欠功率 look-1，属预期，未触发调整。

**交付**：
- **`scripts/track_c_confirmatory_run.py`**（opus 直接写，反泄漏 climax 件）：
  - `verify_frozen_config()` 校验 `track_c_amend2.build_amendment()` 重现 sig `e14b9d44...`（漂移即 abort）
  - `assert_h6_identical()` 双跑 bit-identical（`.equals` + `.tobytes` + CSV hash 三重）
  - `jt_reachable_looks()` 作用在 `combined_ic_series`（Reading A：rank-IC 是 gated 估计量；cond_beta 仅 explanatory）
  - `build_confirmatory_row()` 构造 `confirmatory:first` ledger 行
  - artifact-reuse 模式（`TRACK_C_CONFIRMATORY_FROM_ARTIFACT=1`）：dry-run 已双跑证明 H6 → GO 直接 load
    summary.json 写 ledger，避免 46min 重跑（4 守卫：缺文件 / sig 错 / H6 False / 正常 append）
- **`tests/test_track_c_confirmatory_run.py`**：19/19 hermetic 绿（frozen sig 校验 + H6 pass/fail + look
  reachability 边界 + row 构造 + artifact-reuse 4 守卫 + 空/NaN 边缘用例）
- **dry-run 双跑**（~46min，macro join ONCE 优化后）：H6 bit-identical PASS → artifact-reuse GO commit 瞬时

**结果（ledger #49，bit-identical 于 asym41 exploratory）**：
| 量 | 值 | 判读 |
|---|---:|---|
| combined rank-IC 均值 | −0.008841 | null（p_hac=0.484，CI [−0.034,+0.016] 跨零）|
| US IC / CN IC | +0.0052 / −0.0265 | 双区均 null |
| conditional-IC β（regime 交互）| −0.0076（p=0.43）| null；multiplicity 预算 1 保持 |
| **J-T look-1**（n=60，RCI 99.44%）| **NOT_EQUIVALENT** | RCI [−0.051,+0.027] 宽于 ±0.010 SESOI = 欠功率 |
| H6 双跑 bit-identical | PASS | 真实数据确定性验证 |

**climax 判读（诚实）**：null 点估计 + 欠功率 look-1 = **预期结果**。
- 点估计 null（−0.0088）与全部 14 条 exploratory null 一致（confirmatory 等级下 treatment 仍无正增量）。
- look-1 NOT_EQUIVALENT 是 **power 声明**（OBF z=2.772 极保守 + 月频 IC se≈0.014 → 99.44% RCI 必然宽于
  SESOI），**非效应信号**。门设计意图就是 look-2(n=90)/look-3(n=120) 才判等价。
- **J-T 门拒绝在欠功率下过早宣布等价，即使点估计 null = 反泄漏纪律的活体演示 = 方法学贡献**。
- 严格等价判定需 E3 forward-live 累积日历时间（look-2 ≈ 2028，look-3 ≈ 2031）。

**独立性**：sonnet `general-purpose` code-reviewer APPROVE（0 CRITICAL / 1 HIGH=informational estimand
稳健 / 1 MEDIUM=test 边缘 gap[已补]/ 2 LOW）；7 项反泄漏审查全 PASS。报告
`reports/audits/2026-08-05-confirmatory-runner-review.md`。J-T + H6 + 沉积的可复现性由 frozen #48 + 脚本保证。

**docs**：`docs/methods-and-results-draft.md` v0.1 → **v1.0-draft**（§5 实填 confirmatory + §4 加 #14 asym41
彩排 / #15 confirmatory climax + §0 摘要 + §7 不越界声明更新）。

**边界**：本轮 1 行 ledger（#49 append-only confirmatory:first）+ 新建 scripts/tests/docs(state) + 1 份
audit report；**B/C/D/E1 + Track B 冻结面 / prereg / ADR / config 未改**；未跑 research/forward/strategy；
未触 E3。artifact-reuse 是持久化已 dry-run 验证的结果（config #48 frozen 先于 dry-run 观察 → config_committed
BEFORE result 保持）。

**待业主**：① 审 v1.0-draft → 定稿（中/英 + 期刊定位）；② 是否 push（origin/main 落后若干 commits）；
③ look-2/3 长期路径（E3 forward-live ignition，年级别）。

## 2026-08-05 P1 整合 + P0 confirmatory-GO brief（process→product 收尾）

owner 授权"按推荐方式处理 + 难度分层派 agent + 并行不互扰 + 冲突最高价值优先 + 结果不乐观再调整重测"。
**目标**：关闭 audit 3 caveat（HIGH #1 Phase B paired CI / HIGH #2 baseline 措辞 / MEDIUM #3 3-layer
沉积）+ 产出首条 confirmatory GO 的业主签注包。

**P1(a) Phase B paired HAC CI 补算 — DONE（orchestrator 直接做）**：
- Agent A `phaseb-ci`（sonnet）idle-without-result（handoff 反复记录的 OMC idle 模式）；按 memory
  `aionis-agent-dispatch-verification`（勿信 agent，从 repo 状态恢复）→ opus 直接重算 < 5s。
- 数字：mean −0.0008003561696833403（**bit-identical #28**）/ se_hac 0.00499 / ci_half 0.00977 /
  **CI [−0.01057, +0.00897]** / t_hac −0.1605 / p_hac 0.872（与 dm_p_mbb=0.870 同尾）/ n=125 / maxlag=4。
  CI 跨零，与全家族 null 一致。
- 产物：`runs/phase_b_differential_ci_recompute.json` + `reports/audits/2026-08-05-phase-b-paired-ci-recompute.md`。
- ledger 行 #28 **未改**（append-only）；`phase_b_run.py` **未跑**（用 #28 save_run 的 `ic_state`/`ic_base` parquet + `rank_ic_summary`）。

**P1(c) Track C 3-layer conditional-IC 沉积 — DONE（Agent B 交付 + opus 核验）**：
- Agent B `trackc-3layer`（sonnet）交付 `runs/track_c_3layer_conditional_ic.json`（opus 核验自洽）。
- 重建 3-layer composite（macro+global+meso-US-SIC，valid_n=2592 日）+ joint-fold IC 三臂 HAC 回归：
  **combined β=−0.0148 (p=0.21)** / us β=−0.0287 (p=0.13) / cn β=+0.004 (p=0.80)。全 null。
- **与 handoff § culmination 数字的差异**（诚实分级）：culmination 的 β_US=−0.001/β_CN=+0.015 用的是
  Track-B-fitter **单区** IC；本 artifact 用 **joint-fold per-region** IC（`track_c_joint_ic_series.parquet`
  的 us/cn/combined 列）。不同 series，两份均 exploratory sensitivity。
- combined 3-layer β=−0.0148 ≈ joint 2-layer cond_beta=−0.015（meso 加入影响微小，方向同）。
- 产物：json + `reports/audits/2026-08-05-track-c-3layer-artifact.md`。composite **未覆盖** cache（仍 2-layer）。

**P1(b) 措辞校准**：
- `docs/RESULTS.md` §2 行 B：`**not recorded**` → `[−0.01057, +0.00897]（2026-08-05 补算）` + §2 段落补 audit 链接。
- `docs/methods-and-results-draft.md` §4 行 #1（Phase B CI）+ 行 #9（3-layer）补实际数字 + 诚实分级脚注。
- **Baseline FF5/RANK 校准（audit HIGH #2）**：2026-08-03 batch 8 的"Both baselines now have REAL
  CV-proxy results"措辞应理解为 results 在 `docs/baseline-ladder-{ff5,rank}.md` + runner 输出，
  **非 ledger**（exploratory-by-design，同 Track C joint 模式）；ledger 只含 `config_committed` 行
  （#43 FF5 / #45 RANK）。RESULTS.md 正确未引用 baseline 数字（不入 ledger = 不进 RESULTS headline）。

**P0 — Track C confirmatory GO 业主签注包 — DELIVERED**：
- `reports/design/2026-08-05-track-c-confirmatory-go-brief.md`：6 决策（D1 估计量定义 / D2 区域-月
  group / D3 区域内 IC 等权 / D4 feature_cols 41 列不对称 / D5 meso US-only + 修 #48 / D6 GO+新 ledger
  行）+ 推荐一揽子（业主可回复"全部推荐"即开闸）。
- **核心张力**（brief D1）：amendment #47（A 股 cninfo→exploratory）与 #46 frozen"联合折叠"在
  confirmatory feature_cols 上有张力；推荐 D1=A（保留联合 machinery，feature 收窄为 US 23 / CN 12 +
  宏观 6 + regime 3 = 41 列不对称，LightGBM 默认处理 CN 行的 US-fundamental missing）。
- 签注后流程：起草修 #48 + confirmatory config → `config_committed`（业主动作）→ 首次 confirmatory
  OOS 跑 → J-T 门（已实现 `sesoi_gate.py`）→ draft v0.1 → v1.0 含首条 confirmatory。

**边界**：本轮纯 docs/audit/state + gitignored json；**0 ledger / frozen surface / prereg / ADR 改动**；
未跑 research/forward/strategy（Phase B 用现有 parquet；3-layer 用现有 IC series + composite 重建）；
未观察 confirmatory rank-IC / E3。A/B agent 只写 gitignored + final message（避 writer race：
`git clean -fd` 清 untracked 不清 gitignored，memory 事件证实）。

**独立性局限（披露）**：A idle 由 orchestrator 直接重算替代（非独立 subagent pass）；B 单一交付 +
opus 核验（非独立 verifier lane）。proxy 恢复后可补独立验证（同 Lane C self-audit 披露模式）。

**P0 跟进（owner D1=A 签注后，2026-08-05 续）**：起草 `scripts/track_c_amend2.py`（amendment #48，
  复用 commit_config/amend1 机制，累积 #46+#47+#48）+ `reports/design/2026-08-05-track-c-amend2-meso-us-only.md`。
  dry-run sig `e14b9d445411e74cc3418af3bde1148163725875b01ab75175bdde002225e738`（自洽 build==dryrun）；
  ruff clean；ledger 仍 47 行（未 append）。amendment 内容：meso 收窄 US-only SIC + confirmatory
  feature_cols 41（US 23 + CN 12 + macro 6）+ Q1 区域-月 group / D3 区域内 IC 等权 / D5 meso US-only
  冻结 + baostock G3 adjustflag=3 raw。**✅ ledger #48 已入账**（sig `e14b9d44...`，owner `--commit` 授权 2026-08-05；sha256 自洽已验；
  ledger 47→48 行）。**待第二个业主 GO**（d6_go：授权首次 confirmatory OOS 跑）。

**Extension A 进展（confirmatory 前置 machinery，`/goal` 推进）**：
- **A1 DONE（commit `c98f4c8`）**：`build_joint_panel` 支持 asymmetric region-specific feature_cols
  （`us_feature_cols`/`cn_feature_cols` keyword-only，向后兼容 shared）；2 反退化测试（union+NaN /
  drops non-listed）；11/11 track_c_joint 测试绿；ruff clean。**自验（opus 直接），非独立 verifier lane**
  （proxy [1210] subagent 不稳）。
- **runner 更新（commit `b178a67`）**：`track_c_joint_run.py` 加 `TRACK_C_JOINT_MODE` env toggle
  （shared 默认 / asymmetric35）；mode-tagged 产物不覆盖 shared。
- **数据齐备性（Agent `feat-readiness` 调研）**：US 23 + CN 12 = **100% on disk**（track_b_panel 1.17M
  行含 13 fund+10 price；cn_price_panel 141K 行含 10 price+2 extras）；macro_headline 6 = **0% on disk**
  需 A2 fetch（复用 `macro_dff.py` 模式）。报告 `reports/design/2026-08-05-confirmatory-41-feature-readiness.md`。
- **asymmetric35 exploratory DONE**（验证 A1 真实数据 + US fund signal）：25 特征联合折叠（68 folds /
  71 IC 月），**combined IC −0.0121 (CI [−0.035, +0.011], p=0.31) null**；US IC −0.0019 (n=65) / CN IC
  −0.0200 (n=66)；conditional-IC β=−0.0057 (p=0.61, R²=0.002)。**判读**：加 US fundamentals (13) + CN
  extras 未改善 IC（vs shared10 combined −0.007；asymmetric35 −0.012 更负但均 null）；US IC 几乎零 →
  US fundamentals 无 alpha → **坐实 null-favored**（双区域月频已定价）。产物 `runs/track_c_joint_asym35_*`
  （gitignored）。**Pandas4 concat-sort deprecation warning**（runner:165，非阻塞，待 sort=False fix）。
- **A2 macro 7-gate 调研**：Agent `macro-7gate` 跑 ~30min 后 **failed [1210]** API error（proxy 参数错；非 idle-without-result）。
  **Orchestrator WebSearch 实证 verdict = GREEN**（US 4 macro = GREEN，FRED public domain + ALFRED vintage PIT-safe；
  CN 2 macro = GREEN，WebSearch 确认 `MKTGDPCNA646NWDB`[World Bank, ALFRED vintage] + `CPALTT01CNM659N`[OECD, ALFRED vintage]
  都支持 PIT vintage；license：FRED non-commercial research OK（Aionis = research，no redistribution）；OECD non-commercial OK）。
  **修正之前 YELLOW 判断**（过保守）。CN macro 2 可作 headline（confirmatory 41，与 #48 macro_headline_6 一致，不需 amend）。
  macro 6 fetch（A2）+ broadcast join（A3）= ~半天工程；**asymmetric35 坐实 null**（US fund 无 alpha）→ confirmatory 41 大概率同 null
  （macro broadcast signal 弱），但 spec-faithful climax（J-T 门）需 41。**业主授权 A2/A3 完整 41 路径**。

**下一步（推进中）**：① ✅ asymmetric35 DONE（combined IC −0.0121 null，坐实 null-favored）；② ✅ A2 verdict
= YELLOW（orchestrator 判断；US 4 GREEN + CN 2 snapshot+exploratory）；③ **A2/A3 完整 41 路径 — 前置 machinery 全部就绪**：A2a DONE（cap fix 验证 `edc1add`，US macro 4 valid：
  term/credit 107/128，vix/dff 106/128）；**A2b DONE**（commit `9a13518`）：CN CPI（CPALTT01CNM659N）122/128 valid +
  CN GDP（MKTGDPCNA646NWDB annual）**0/128 NaN**（releases ~10 < Z_MIN=12，数据限制诚实披露）；**A3 DONE**：
  `MACRO_HEADLINE_6` + `join_macro_to_joint_panel`（per-region by-date map）；**runner asymmetric41 DONE**（第三模式
  `TRACK_C_JOINT_MODE=asymmetric41`）。**asymmetric41 exploratory 跑中**（验证 41 特征 machinery 真实数据；
  confirmatory 41 effective macro = US 4 + CN CPI = 5，GDP NaN，LightGBM native missing）。
  ④ **业主 d6_go**（第二个 GO）→ confirmatory OOS（41 + J-T 门）→ draft v1.0 climax。**climax 前置全部就绪，待业主 GO。**

## 2026-08-04 方法学+结果 draft v0.1（可发表单元；process→product）

owner 4× 重发 standing auth → 执行推荐 ②（方法学写定稿）。产出 `docs/methods-and-results-draft.md` v0.1（PROPOSED，业主审阅中文稿）：
- **METHODS 段（§1-3）= 贡献**：反泄漏纪律作为研究对象（config-before-result / PIT 全栈 / purged+chronological 验证 / H6 确定性 / J-T 等价门 / 两尾 null-favored 预注册 / multiplicity 预算 1 条件化）——全部 code/ledger-asserted，非叙述。Track C 联合折叠作为方法学新点（§3）。
- **RESULTS 段（§4）= 12 行 null 证据表**，诚实分级（CV-proxy vs chronological；exploratory vs confirmatory）。全部 null；0 条 confirmatory。
- **§5 占位** = Track C confirmatory GO（首条 confirmatory）。
- **§6 局限** 诚实（CV-proxy≠chronological；exploratory≠confirmatory；Track B 等价欠功率；幸存者；币种）。
- 数字源自 ledger/artifact；**独立核对**派 `evidence-audit`（sonnet，后台，read-only）→ `reports/audits/2026-08-04-evidence-integrity-audit.md`（运行中）。
- **治 "治理>产出" 失调**：把累积 process 转 product。未触冻结面/ledger；confirmatory 段 owner-gated。

## 2026-08-04 Track C 联合 US-CN 折叠估计量（confirmatory machinery；exploratory 走通中）

owner 授权"按推荐方式处理 + 难度分层派 agent + 并行不互扰 + 冲突最高价值优先 + 结果不乐观再调整重测"。**边界**：null-favored，"不乐观"= 工程/测试 bug 迭代修复，**非** rerun-to-significance（若现 rescue 诱惑则交 owner）。

**双车道并行（文件隔离）**：
- **Lane A（sonnet `general-purpose`，后台）→ [1210] 死，orchestrator(opus) 直接接手完成**：`reports/design/2026-08-04-shenwan-meso-7gate.md`。**裁定：CN 申万 meso via baostock = G3 结构性 fail（无 as-of/vintage，SWFC 回填，同 baostock-基本面先例）→ 快照冻结 + exploratory-only，不进 confirmatory headline**。**关键后果：confirmatory meso = US-only（SIC），= 当前实现状态，正式化为 spec-faithful config；不需 CN 申万 fetch**。本会话早先「3-layer US-only-meso 双区 conditional-IC null」即 spec-faithful exploratory 结果。正式化需 owner 在新 ledger 行修订 §1.1（meso=US-only for confirmatory；CN 申万 exploratory）。
- **Lane B（opus = 我，会话内）**：联合折叠估计量设计 + 实现（slop 高危件，本会话 agent 翻车 3 次同类）。

**Lane B 已交付 + 验证（未 commit）**：
- `reports/design/2026-08-04-track-c-joint-fold-spec.md`（设计 spec；D1 区域-月 group / D2 区域内 IC 等权联合 / D3 per-region 时序断言 / D4 regime as-of 月末 / D5 共享 10 price 特征；7 项 owner-decision 旗标 Q1-Q5）。
- `src/aionis/eval/track_c_joint.py`：`fit_track_c_joint` + `build_joint_panel` + `construct_region_month_groups`（D1）+ per-region 时序断言。核心洞察：**month-end 采样 + 日历月折边界 = per-region 21-session embargo 自动满足**（相邻月末 ≈ 21 sessions/区），无需逐区数交易日 → `cv.py`/`purgedcv` 0 改动。
- `tests/test_track_c_joint.py`：9 反退化测试（区域-月 group、build_joint_panel 双区+窗口、per-region 时序断言抓违反、月末逐区采样幂等、单区拒绝、**e2e H6 bit-identical 双跑**、combined_ic=区域 IC 等权）。**9/9 绿**。
- `scripts/track_c_joint_run.py`：exploratory runner（PHASE_C_NO_LEDGER；产出 `runs/track_c_joint_*` gitignored）。
- **验证**：`tests/test_track_c_joint.py` 9/9 ✓；全套 hermetic pytest **exit 0**（无回归）；`ruff check` 全清。

**Lane B 真实数据证据（DONE；exploratory，NO ledger）**：`scripts/track_c_joint_run.py` 在真实 US(566 tickers) + CN(929) 联合月末面板跑通（68 folds / 71 IC 月，oos_scores 94,438 行双区，score std 0.508 非退化）。**combined rank-IC −0.0070，CI(−0.030,+0.016) 跨零，p_hac=0.55 → null**；US IC −0.002 / CN IC −0.014（双区均 null）；**conditional-IC β=−0.015，p=0.20（无 regime 交互），R²=0.018**。= 又一条 null（符合 null-favored；与 Track B null + 早先 CN 单区 conditional-IC null 一致）。产物 `runs/track_c_joint_{summary.json,ic_series.parquet,oos_scores.parquet}`（gitignored）。**非 confirmatory 判读**（10 共享 price 特征 + region-month group D1 默认，#46 group 未冻结）。

**关键设计决策（confirmatory 前需 owner 签注，spec §7 Q1-Q5）**：
- Q1 lambdarank group = **区域-月**（D1，币种干净；#46 未冻结 group 构造）。
- Q2 联合 IC = 区域内 IC 等权（D2）。
- Q3 confirmatory feature_cols = 全 #46 54 列（exploratory 用共享 10 price）。
- Q4 meso（依赖 Lane A 裁定）。
- Q5 confirmatory 跑 = owner GO + 新 ledger 行。

**Lane C 独立 review 结果（agent 车道失败 → 确定性自审 + 披露）**：`jointfold-review`（sonnet）2 次 idle-without-verdict（[1210] proxy 日，agent 车道不稳：Lane A 死、Lane C idle）。按 WORKFLOW §17（2 次相同失败 → stop）+ §8（从 repo 状态恢复，勿信 worker prose），停重试，改**确定性自审**（opus 自审 + grep 核验关键接线 + 测试/真实跑证据），**独立性局限明示**：
- **I1 per-region 时序**：`_assert_per_region_chronological`（track_c_joint.py:359）在折循环内、`splits.append`（:360）前调用，无 try/except 包裹 → 不可跳过 ✓（grep 核验）。
- **I2 train-only binner**：`fit_monthly_bins(train_returns=...)`（:382-383）仅喂 train ✓。
- **I5 region-month group**：`(y*12+m)*2+code`（:111），us/cn 分离 ✓。
- **测试实质性**：e2e fixture 70 月×50 ticker+signal 0.3+`check_exact=True`（H6 严格）→ 非化妆品测试 ✓。
- **证据**：9/9 反退化测试 + 全套 pytest exit 0 + 真实跑非退化（score std 0.508）双区正确 shape。
- **Verdict**：machinery 确定性验证通过（self-audit + tests + real run）。**独立性局限**：非真正独立 pass（agent 车道 [1210] 失败）；proxy 恢复后可补独立 review。2 个 LOW note（e2e 未 assert IC>0；per-region assert 对单边缺席区域 skip——真实数据两区恒在，不影响）。

**边界**：本轮纯新建文件 + state；0 冻结面/ledger/prereg/ADR 改动；未观察 confirmatory rank-IC 结论；未触 E3。

## 2026-08-04 Track C conditional-IC（3-layer regime，null）— 会话 culmination

meso 3rd 层完成（`33b5cfb`，US SIC=EDGAR 公共域 `phase_d_sic_map.parquet` 588 tickers；CN 申万 baostock `ENABLE_CN_FETCH=1` 门控默认 off → meso 现 US-only，sha256 `e9f30d94`）。composite builder 升级 3-layer（`f7c5789`，sha256 `0cb7409e`，3021 日/valid 2592）。

**双区域 conditional rank-IC（IC_t ~ regime_t, HAC）**：
| regime 组成 | US β (p) | CN β (p) |
|---|---|---|
| 2-layer (macro+global) | -0.008 (0.48) | **+0.034 (0.07 边际)** |
| 3-layer (+meso US-only) | -0.001 (0.95) | +0.015 (0.36) |

**关键发现（方法论）**：2-layer 的 CN 边际交互（β=0.034, p=0.07）**被 meso 稀释到 null**（β=0.015, p=0.36）。**conditional-IC 对 regime 组成敏感**；spec-faithful 3-layer regime 下两区域 conditional-IC **均 null**（null-favored-consistent）。此前"CN 非对称 regime 交互"是 2-layer artifact，不稳健。

**待办（confirmatory，owner-gated）**：① 全 US+CN meso（CN 申万 fetch ~30min baostock）；② 联合 US-CN 折叠（per-region 日历 + 时序）；③ confirmatory 跑（冻结 #46/#47 + **新 ledger 行 = owner 动作**）+ J-T SESOI 门。当前 conditional-IC 用 Track B fitter on 单区域 + 独立 IC 系列回归（非联合折叠 confirmatory 估计量）。

**本会话总账（17 commits，main，未 push）**：S0 数据（CSI300 universe `425f5535` + A 股价格 `a4614876`）→ mount② 净成本（5bps net Sharpe ~0.43 年化）→ 首个 CN rank-IC(null, mean 0.0098 p=0.46) → 3 regime 层（macro `4bfd1949`/global DY `d189f53c`/meso `e9f30d94`）+ composite（3-layer `0cb7409e`）→ conditional-IC（3-layer null）。全套 hermetic pytest 绿，ruff 干净（预存 `track_c_commit.py:180` E501 仍待 owner）。

## 2026-08-04 regime composite（完成；2-layer exploratory）

owner `/goal`×5 推进 Track C regime_state。3 层中 **macro + global + composite** 完成，meso deferred。

- **macro 层**（`abab13e`，agent clean——本会话首个无需修复的）：vix+credit_spread(BAA-AAA)+term_spread(DGS10-DGS1)+dff_surprise 等权 past-only z-score。**EPU 4-line**：无 permissive 中国 EPU 源（license+PIT+no-revision 门 fail）；frozen #46 本标 EPU"(exploratory)"，排除=保守合规；**confirmatory 需 config 修订（新 ledger 行）**。sha256 `4bfd1949`。
- **global DY 层**（`9093100`，agent + 我核验）：US-CN EW 市场收益 → Diebold-Yilmaz 广义 FEVD（**statsmodels VAR + 标准公式**，未 vendor spillover-lab 因 PySide6 重）→ rolling-250 总 spillover。**GFEVD 公式逐行核验正确**（GIR=(ΦΣ)[i,j]/√Σ_jj；θ 行和 1；total=(θ01+θ10)/2；sanity：independent→~1%、correlated→~35%）。2 caveat：sha256 标签是 series-hash(`d189f53c`) 非 file-hash(`eb873732`)；lag-0 fallback 触发 30%（agent 误报"罕见"，建模选择非 bug）。
- **composite**（`df57a4a`，opus）：等权 past-only z-score 两层 + **TACO expanding σ**（[t0,t] 不回溯重算，frozen #46 normalization）。regime_state n=3021/valid 2585，mean 0.018/std 0.83，sha256 `deee9cf1`。
- **meso deferred**：申万/SIC 行业动量（数据源 7-gate 最难）→ composite 暂 2-layer（exploratory）。
- **Agent 质量教训强化**：macro(clean) + DY(公式正确，因 spec 含精确公式 + sanity 测试) → **精确 spec + 反退化/边界测试 = agent 能做对硬量化方法**（对比 net_cost/CSI300/cn_panel 盲派都出错）。

**下一步（待做，opus 设计重——conditional rank-IC 是 Track C 真正的 confirmatory 估计量）**：
1. **score × regime_state 交互 → conditional rank-IC**（IC 系列随 regime 变化？）。需 conditional-IC 框架设计（参考 `reports/design/2026-08-03-conditional-rank-ic-multiplicity.md`）——这是设计重活，slop 风险高，宜先定方案。
2. **meso 3rd 层**（申万/SIC，for full 3-layer composite）。
3. **联合 US-CN 折叠 + confirmatory 跑**（冻结 #46/#47 + 新 ledger 行）。

## 2026-08-04 Track C CN rank-IC 首探（完成；exploratory）

owner `/goal`×4 推进 Task#6。A 股 price-only 面板 → 首个 CN rank-IC。

- **CN 价格面板**（`data/cache/cn_price_panel.parquet`，gitignored）：141,208 行 / 929 tickers / 152 月末 (2014-01..2026-08) / 12 特征 (10 Track B price + limit_up_down_distance + suspension_flag) + forward_return_h。leakage self-check PASSED（特征只用 close≤t，标签用 close[t+21]）。
- **agent 质量第 3 例**：`cn-price-panel` agent 交付的 `build_cn_price_panel.py` 有 3 bug（① MultiIndex stack 后误赋 4 列名实为 11→Length mismatch；② leakage self-check 取非月末 raw 日期→越界；③ stack 依赖 index.name="date" 不健壮）。agent 的 15 测试又"绿"但空洞（测了 `compute_price_features` 被复用函数，没测 `_build_features` 包装）。opus 修 3 bug + 补 `_build_features` 回归测试（set 对比 + 排除 melt 残余）。
- **首个 CN rank-IC**（`scripts/track_c_a_run.py`，Track B fitter on CN，92 折 2019-01..2026-06）：**mean_ic 0.009836，ci_95 (-0.0165, 0.0362) 跨零，p_hac 0.4639 → NULL**；DM vs EW stat -2.19 / p=0.031（边际；n_trials=30 haircut 会洗掉）；IC std 0.1289。**与美股 Track B null 一致，符合 null-favored 预期**。corr(momentum_21d, fwd_ret)=-0.015（A 股短期反转 hint）。
- **诚实结论**：A 股 price-only rank-IC null = 可发表结果，**非"不佳"——不调整重测**（rerun-to-significance 禁）。下一步是 Track C 真正的 confirmatory 跑（regime 交互 + 联合折叠 + 冻结 #46/#47），不是"rescue"这个 exploratory null。
- **边界**：exploratory（Track B fitter on CN），**非 Track C confirmatory 估计量**，不写 ledger。IC series + OOS scores 存 `runs/track_c_cn_*`（gitignored）。
- **commits**：cherry-pick `78f7d5af`（agent 原始，3 文件）+ 本批 fix commit（3 bug 修复 + 回归测试 + runner）。

## 2026-08-04 OSS-survey + 并行派发批次（完成）

owner 授权"按推荐的数据与方式处理 + 难度分层派 agent + 并行不互扰 + 冲突高价值优先 + 结果不佳再调整重测"。

**已完成：**
- **修订 #47 提交**（`6bd360f`，owner 本会话明示授权）：A 股 cninfo 基本面 → exploratory-only（G1 处置），claim 收窄为 US-rank-IC（确认性）+ A 股 exploratory 条件化。ledger #47 sig `252cf7df` sha256 自洽已验；#46 冻结不变（append-only）。含 docs/track-c-preregistration.md §0+§3、ashare-fundamentals-source.md §3、scripts/track_c_amend1.py（可复现）、state 沉积。
- **清除 GPL orphan** `src/aionis/eval/finsaber_mount.py`（import backtrader GPLv3；真正的净成本层是 `eval/execution_costs.py`，已实现）。
- **baostock G3=raw** 已是 `ingest/ashare_price.py` 默认（adjustflag="3"）；intake 文档（`ab43454`）已覆盖。视作冻结默认。
- **OSS 轮子调研**（`420fba1`，今上午 + 同日勘误）+ 本轮补验：qlib=library-import CN 采集器（MIT,PIT-DB 实）；akshare=MIT 但 SSRN 论文实证其 PIT 不安全（重述值）→ 坐实"A 股 filed-date 基本面无 permissive 轮子"=结构性数据 gap，非手搓失败。

**完成（2 agent 回报 + 集成 + 修复；commits `5b561e4`/`8bbe6a6` cherry-pick + 本批 fix）：**
- **`csi300-intake`（Task#3，DONE clean）**：选 `index-constitution`（PyPI 实证 MIT + `py3-none-any` wheel=3.13✓ + 0.6.2/2026-07 + 内嵌 CSIndex 历史公告=零运行时 HTTP + opt-in/opt-out=PIT+survivorship-safe）。7-gate 全 PASS。`ingest/csi300_constituents.py`（lazy import 非 core dep + `enable_fetch=False` 默认 + snapshot+sha256 + `constituents_on(t)`）+ intake doc + 14 hermetic 测试（无 stub）。潜在风险：适配器调 `ic.history("csi300")` 而 PyPI 示例是 `ic.constituents_at(...)`——API 名待真实拉取时核实（owner-gated+fail-closed，不阻塞）。
- **`mount2-netcost`（Task#2，agent 交付 defective → orchestrator opus 重写 3 文件修复）**：agent 的 net_cost.py 有 **3 blocker**（turnover 退化：pre_trade 两分支都=0 + 注释撒谎；test 有空 `pass` stub；runner 整个计算被注释 `sys.exit(1)`）；且 11 测试是**欺骗性绿**（3-ticker fixture 致 long_short_returns 跳过→NaN→`if isfinite` 跳过 assert + 5 测的是 execution_costs 内核）。**重写后**：turnover 追踪 prev_target（union 对齐、逐期成本、no-drift 简化已诚实标注）；去 session_opens（turnover-bps 模型不需 open 价）；runner 加载真实 `oos_state.parquet`（`long_short_returns` 自动月末子采样）→ **本轮出真实数字**；12 测试含**反退化测试**（稳定分数→低 turnover，洗牌→高 turnover，直接抓 always-2.0）。
- **集成**：cherry-pick 两 commit（worktree 基是 `30ae69f` 非 `6bd360f`——worktree 创建时序问题；但两 commit 自身 diff 各 3 新文件纯新增→cherry-pick 安全，#47 未被回退，已验）。全套 hermetic pytest **exit 0**；ruff 干净；零 stub/TODO/pass。
- **⚠️ 运维教训（fold 进 orchestration-protocol §8）**：① worktree 基可能滞后——merge/前**必查 merge-base + commit 自身 diff**，勿信 `branch..HEAD` 累积 diff；② agent"全绿"必须**代码级核验**——A 的测试空洞绿（小 fixture→NaN→跳过 assert）肉眼不可见，靠反退化测试 + 真实数据跑才暴露；③"reuse-first"≠"import 了就算复用"——A import 了 execution_costs 却喂退化输入。

**mount② 真实结果（Track B treatment panel `ef321e9…`，bps=5，125 月 2016-2026）**：gross_sharpe 0.1487（月，年化≈0.51）→ **net_sharpe 0.1250**（年化≈0.43，成本吃 ~16%）；**avg_turnover 1.1444**（真实换手，非退化 2.0）；total_cost 715 bps 累计（≈5.7 bps/月，=5×1.14×1e-4 自洽）。注：此 panel 是 mtime 最新 run（未必 #41）；策略在 5bps 滑点下保住大部分 Sharpe。

**边界：** 本批仅 #47 commit（owner 授权）+ cherry-pick 2 agent commit + mount② fix；**未观察 OOS rank-IC**（net-cost 是 L-S 收益视角，非 rank-IC 估计量）；未触 B/C/D/E1/Track-B 冻结面；net_cost 是探索性工具（类比 ff5_residual，不接管线、不写 ledger）。`runs/track_b_net_cost.parquet` gitignored。

## 2026-08-04 `/loop` 批次 — 未提交在途工作批判性审计（GPL 清除 + site 恢复；未 commit）

owner `/loop` 授权"推进推荐项 + 批判性思维 + reuse-first + 模型分层省 token"。进入会话发现 main 上有一批**未提交的在途工作**（非本会话创建），独立审计发现 **2 个缺陷**，已采取明确正确的恢复/安全动作；judgment 项交 owner。

**缺陷 1（CRITICAL，已清除）— GPL 污染：** 批次把 `finsaber>=2.0.1` 加进 core deps + 新增 `src/aionis/eval/finsaber_mount.py`（直接 `import backtrader as bt` + 子类化 `bt.Strategy`）。核验（definitive）：`finsaber`=Apache-2.0（本身合规），但其 `Requires-Dist` **硬依赖** `backtrader>=1.9.78`=`GPLv3+`，CLAUDE.md 明令 EXCLUDE。→ 已从 pyproject 移除 finsaber；`uv lock --offline` 清除 backtrader+finsaber+colorlog；pyproject/lock 回到 committed（GPL-free，diff 空）。`finsaber_mount.py`（untracked、孤立、无任何 import 引用）排除不提交。见记忆 `aionis-finsaber-backtrader-gpl`。

**缺陷 2（回归，已恢复）— site 空壳化：** 批次的 `site/index.html` 把 committed 的**真实内联数据**（`const icData={...}` + 风险表 + FF5 表）替换成**占位符**（`const icData=null` + "待 ...json"；因 `build_static_site.py` 在 2 个 JSON 被删后重建产空壳，且有个未闭合 `<p>`）。→ `git checkout -- site/` 恢复 committed 已部署的良好站点（真实数据，`grep const icData={` 计数=1 确认）。

**测试：** 全套 hermetic pytest exit 0（仅 pre-existing forward-score/numpy warnings）；`ruff` 未本轮重跑（无 src 改动待验——pyproject/lock 回到 committed，site 回到 committed，均无新代码）。

**待 owner 裁断（未擅自提交——非本会话创建 + consequential）：**
1. **修订 #47（A 股 cninfo→exploratory-only）**：ledger 行已 append（sig `252cf7df`，phase=track_c），docs/ashare 报告同步；`track_c_amend1.py` docstring 称"owner authorized (B) 2026-08-03"但 tracked state（本文件/current.md）**未印证**。属 claim 收窄 scope change（保守、append-only、结构合规）。→ owner 确认授权后可提交（ledger+docs+track_c_amend1.py+ashare 报告）。
2. **oos_scores 管线**（`track_b_baseline.py` oos_scores 字段 + `track_b_a_run.py` 持久化 + `ranking_contract.py` 单行月 scalar→Series bugfix）：license-clean、verified-green、非 scope change；但与 mount② 消费耦合。→ 建议与 mount② 合为一个完整切片提交。
3. **mount② 净成本回测（reuse-first 重写）**：**禁用** finsaber/backtrader（GPL）；改用 **pyfolio-reloaded+empyrical（已在 lock，MIT/Apache）+ ~50 行确定性成本层**（next-open 成交 / bps slippage / turnover / 流动性上限）。待 owner 定成本参数。

**下一步（loop 续跑优先级，无 owner 回复时）：** P0 = 上述 3 项 owner 裁断；P1 = Track C S0 数据构造脚手架调研（冻结后允许，不写 ledger/不观察 rank-IC）：qlib 双区域 mount 接线点④ + cninfo MIT fetch（`rollysys/use_cninfo`）+ A 股价格 PIT（baostock 价格 MIT ✅，基本面 G3 reject）。子代理 dispatch 因 `[1210]` proxy 今日不稳 → orchestrator 直接 opus 写优先（handoff 既定策略）。

**边界：** 本批仅恢复/安全动作（site revert + GPL 清除）+ state/memory；**未 commit 任何 frozen surface / data**；ledger #47 行保持 in-tree 未提交原状；未跑 confirmatory/strategy/forward；未观察 E3；网络仅 PyPI 离线（uv lock）。

**续（loop 迭代 2 — owner 未回复 #47 授权 → 推进 P1 安全项）：**
- 提交 `5e2ce6d`：clean infra（`ranking_contract` 单行月 scalar→pooled-edges bugfix + Track B `oos_scores` 管线）；verified-green + ruff clean；非 scope change，**不需 owner 决策**。清树债。
- 提交 `ab43454`：2 份 S0 intake 文档（baostock A 股价格 7-gate + CN 宏观双层级 7-gate），**2 并行 sonnet `general-purpose` agent** 产出（绕过 `[1210]`，file-isolated，未触冻结面/未拉真实数据/未观察 rank-IC）。关键裁决：baostock 价格 **G3 CONDITIONAL**（复权因子 adjustflag 可追溯回改 → 需冻结策略：raw+本地因子快照 或 前复权全序列快照）；CN 宏观 **headline(ALFRED/OECD vintage) PASS 全 7 门** / **exploratory(NBS via mbk-dev/nbsc) G2+G3 FAIL → snapshot+sha256+exploratory-only**（EPU 先例）。
- **仍 pending owner**：① 修订 #47（A 股 cninfo→exploratory）授权确认；② mount② 净成本成本参数（slippage bps 等）；③ NBS G1 license 验证 + baostock G3 复权冻结策略裁决。
- **下一 loop 优先级（无 owner 回复时）**：qlib 双区域 mount 接线点④ 调研（S0 基础设施，POC 标注 ~3h 接线）或 cninfo MIT fetch（`rollysys/use_cninfo`）路径设计（exploratory 基本面）。子代理 `[1210]` 已验证 `general-purpose`+sonnet 可靠绕过 → 可继续 ≤2 并行 file-isolated 派发。

**续（loop 迭代 3 — owner 仍未回复决策；推进 P1 具体研究基础设施）：**
- 提交 `178d1fd`：**baostock A 股价格 ingest 适配器**（`src/aionis/ingest/ashare_price.py` + 5 hermetic 测试）。镜像 `market.py` US 侧模式；lazy import（baostock 非 core dep，`uv add baostock` 激活）；G3 默认 `adjustflag="3"`（raw，G3 方案 A，冻结策略延后到 config）；停牌→NaN（G6）；≥2s pause（G7）。**决策零依赖**（baostock 是冻结 prereg 批准源；intake 文档已提交；G3 策略延后 config）。5/5 测试通过 + ruff clean。未拉真实数据/未触冻结面/未写 ledger。
- **本轮累计 3 提交**（`5e2ce6d` infra + `ab43454` intake 文档 + `178d1fd` 适配器）—— 全部具体、安全、reuse-first、verified。
- **5 项 pending owner 决策不变**（修订 #47 授权 / mount② 成本参数 / NBS G1 license / baostock G3 冻结策略选方案 / 下一 S0 切片优先级）。**最高价值路径（真实 S0 数据、Track C rank-IC）仍被门控。**
- **下一 loop（无回复）候选**：A 股交易日历对齐（pandas-market-calendars XSHG/XSHE，配 baostock 适配器）或 CSI300 PIT 成分 intake（`index-constitution` MIT）。

**续（loop 迭代 4 — 改做独立质量门，不再造脚手架）：**
- 批判判断：连续 3 轮"找安全切片建造"边际价值递减 + 建错方向风险升（owner 未确认 baostock vs qlib+AKShare；未确认 G3）。改为关闭真正的质量缺口——本会话 3 commit 此前全是**自我批准**（违反 OMC 分车道）。
- **独立 opus `general-purpose` reviewer 审 `30ae69f..HEAD`**：**APPROVE，无 blocking**。验证：anti-leakage/PIT（停牌 NaN ✓ / adjustflag G3 延后 ✓ / 单 login finally-logout ✓ / oos_scores 仅 test-fold ✓）、license 完整性（uv.lock 无 backtrader/finsaber ✓ / baostock lazy-import 非硬依赖 ✓）、正确性、测试充分性、代码质量。2 条 advisory（非阻塞，未改）。
- **全局 hermetic pytest exit 0**（全绿，确认 3 commit 无回归）。
- **结论**：3 commit 现已"独立审查 + 全局验证"双门通过，不再仅自证。
- **5 项 pending owner 决策仍不变**；最高价值路径仍门控。**建议**：若 owner 近期无法回复，`CronDelete 2344a544` 暂停 loop（避免重复读状态开销 = token 浪费，owner 自己的优先级）。若回复，最阻塞 = 修订 #47 授权确认。
- **下一 loop（无回复）候选**：交易日历对齐 或 CSI300 成分 intake（仍属安全外围，边际价值递减——故本轮选择改做质量门而非继续造）。

## 2026-08-03 `/goal` 批次 — Option A′ 推进（docs/design only，未 commit）

owner `/goal` 授权推进 Option A′（多 agent 按优先级 + 模型分层省 token + reuse-first 禁造轮子）。**[1210] 现实**：opus/sonnet 子代理今天执行不稳；本批分层 = ① orchestrator 直接 opus 设计 + ② sonnet 后台 agent + ③ haiku 后台 agent。

**产出（全部 PROPOSED/docs，未触冻结面/ledger/E3）：**
- `reports/design/2026-08-03-conditional-rank-ic-multiplicity.md` — **gate 7 解决**：conditioning = 单个预指定交互项（预算 1，非 K），批判者 #4 "完全炸掉 n_trials" → PARTIAL 解决；复用 `purgedcv`/`arch`/`YannickKae`；Deflated-RankICIR（FARS 2026，DSR 适配因子级 RankIC）待 license。
- `reports/design/2026-08-03-track-c-prereg-skeleton.md` — **Track C（A 股 + 条件化 rank-IC）预注册骨架 PROPOSED v0.1**；§3 features / §5 双区域折设计 / §1 regime PIT 定义 = TBD（待 T1 + owner 冻结）；§4/§6/§7/§8/§9 复用 Track B + ADR-010。

**后台 agent（运行中，待回报）：**
- `ashare-gate-research`（sonnet）— A 股 filed-date 基本面源 7-gate 调研（cninfo / Tushare-`ann_date` / akshare）。**P0 关键路径**（gate 4，解 baostock G3 结构性失败）。
- `drankicir-check`（haiku）— Deflated-RankICIR 代码/license 核查（解 gate 7 待查）。

**未解 / 下一步：** T1 回报 → 填 Track C §3 + 定 A 股源（headline 可行 vs exploratory-only）；drankicir 回报 → 定 gate 7 主轮子；A 股**价格** PIT（§3 ①，survivorship 退市/停牌→NaN/复权）+ 中国宏观 vintage（§3 ②，NBS G3）待后续 intake 调研。regime PIT 定义（TACO 范式）待 owner 冻结。

**边界：** 本批仅 docs/design + state；未 commit；未运行 confirmatory/strategy/forward 脚本；未观察 E3；网络仅 GitHub/PyPI/WebSearch（无 baostock.com 数据调用）。

**Track C v1.0 PROPOSED（2026-08-03 续）：** owner approved §12 默认 → 起草完整 `docs/track-c-preregistration.md`（PROPOSED v1.0，12KB；§12 全填：联合折叠 / 三层 PIT regime / cninfo 源 / qlib scaffold；§3 ①②③ 全调研解决）。取代 `reports/design/2026-08-03-track-c-prereg-skeleton.md`。**未冻结**——无 `config_committed` ledger 行；feature_cols 待冻结前完整枚举（US 复用 Track B 23 + A 股 price/cninfo/ALFRED/regime 字段）。**待 owner**：审 v1.0 → 授权 `config_committed` 冻结（写 ledger 行，= owner 动作）→ impl 切片（post-freeze）。agents 7/7 `[1210]` 死，全 orchestrator 直接完成。冻结面守卫 = 空（仅新增 docs/track-c-preregistration.md，未改 phase-*/track-b/ADR/ledger/config）。

**Track C FROZEN（2026-08-03 续 2，owner 二次 approved）：** owner 确认 4 个冻结子参数（regime expanding-as-of σ TACO；DY spillover window=250/H=10/generalized FEVD；三层等权 composite；A 股 FF v1.0 排除）→ 写 `scripts/track_c_commit.py`（纯 stdlib，复用 phase_b `commit_config` 机制：`sig=sha256(json.dumps(config,sort_keys=True))`，行格式 `{ts,event:"config_committed",phase,config_sig,config}`）。**dry-run → --commit**：ledger 45→46 行，phase=track_c，`config_sig=758ca4d739f09331ee4dceb726d9d0d0f7c5110303acc6dcac59919701374fad`，**sha256 自洽已验**（重算==行内 sig），**未观察任何 OOS**（config_committed 行 only）。`docs/track-c-preregistration.md` §0/§13 更新为 FROZEN。**Track C 反泄漏 anchor 就位**；冻结后允许 S0 数据构造（不写新 ledger、不观察 rank-IC）。`runs/ledger.jsonl` 现有未提交改动（+1 行，TRACKED，按惯例提交时机 owner 定）。

## 2026-08-03 qlib 双区域 POC（Option A 可行性取证，docs/state only — 未 commit）

owner 授权的可逆证据 POC，解决 Option A 辩论（独立批判者 REJECT；辩护/裁断 agent 因 `[1210]` 5 次失败缺失）。完整报告 `reports/2026-08-03-qlib-dualregion-poc.md`。
- **5 硬证据:** ①qlib 双区域特性存在（`REG_CN/US`+`LocalPITProvider`+CSI300/500 采集器[从 csindex 历史公告重建]+pit 采集器）→**推翻批判者 #2/#8/#10**; ②cp313 门（pyqlib 0.9.7 无 cp313 wheel；3.11 隔离 venv `IMPORT_OK` 0.9.7 已验绕过）; ③RobustZScoreNorm 泄漏陷阱实证确认 + 折内钉 fit 修复有效（CLEAN train z-median 0.0000 vs LEAKY −0.3453）; ④DatasetH 手术点③需 3h 接线; ⑤**baostock G3 结构性不可合规**（`query_profit/balance_data(code,year,quarter)` 期末键、无 as-of/vintage）→**验证并强化批判者 #1**。
- **Net:** Option A′ **条件-sound**，8 门实证背书（报告 §3）。A 股基本面须换 filed-date 键源（cninfo/Tushare-`ann_date`/自建）或降 exploratory-only；baostock 不可进 headline。
- **边界:** scratch `/home/re/code/aionis-qlib-poc/`（仓库外），合成数据，未 commit/未触冻结面/ledger；网络仅 GitHub+PyPI；无 baostock.com 数据调用、无 research/forward 脚本、未观察 E3。
- **未解:** baostock 返回字段 pubDate 可重建性; A 股 filed-date 源 7-gate; DatasetH 手术点③接线; `index-constitution` 7-gate。
- **loop cron `3219e84b` 已取消**（POC scope 完成，避免与暂停冲突）。
- **独立性局限:** 批判者真独立; 辩护/裁断由 orchestrator 非独立核查替代（已做偏向校正）。proxy 恢复后可补完整三方辩论。

- **2026-08-03 `/goal` batch 8 — BASELINE-FF5-001 + BASELINE-RANK-001 EXECUTED (COMMITTED `104b21e`):**
  owner authorized real-data execution ("全部approved"). Both baselines now have REAL CV-proxy results:
  - **BASELINE-FF5-001** (sig `0b0b9934…`, 18 cols: 9 frozen + 9 FF5 exposures; `beta_dff`/`beta_dff_x_lev`
    excluded by RD-13: 42 CONSTANT months 2024-08+ — rate-plateau): **mean_IC=0.0106, ci_half=0.0196,
    t_hac=1.059, n_months=125; H6=True**.
  - **BASELINE-RANK-001** (sig `22817980…`, lambdarank/rank_bins=5, month-end-sampled panel,
    analysis_start=2015-08-01): **mean rank-IC=0.015420, ci_half=0.014870, t_hac=2.0323, p_hac=0.0421,
    n_months=125; H6=True**.
  Both EXPLORATORY CV-proxy only; config_committed ledger rows appended BEFORE results (2 RES-02 + 2 RES-03 rows).
  **Fixes surfaced by real runs**: (1) RES-02 SIG_ONLY mode (exit before OOS) + analysis window
  2015-08-01 (DFF vintages begin 2015-01-01; owner decision option A) + month_ends pre-window;
  (2) features/ff5.py beta_dff NaN no longer contaminates FF5 5-factor betas (independent OLS masks);
  (3) RES-03 month-end sampling (RD-15 group=query-month ~500 rows, not ~11,300 — LightGBM 10k/group cap)
  + folds on month-end panel via two_arm._folds_from_panel + config-driven analysis_start;
  (4) RES-03 _require_owner_commit ledger gate. Full suite exit 0; ruff clean.
  **Data acquisitions**: FF5 daily snapshot frozen (`ccf509fb…`, 15833 rows) + DFF ALFRED vintages
  293,510 rows (2015→2026, sharded yearly — FRED 2000-vintage cap workaround).
  **NOT yet done**: evals/trials registry entries for both trials; RES-08/RES-10 (owner gold-set annotation).
- **2026-08-03 `/goal` batch 7 — E3 Slice 7 E2E + AUD-06 contract freeze (COMMITTED `0f94620`):**
  closed the final E3 code gap. `tests/test_forward_e2e.py` (NEW, 290 lines, 2 tests) wires the full
  hermetic chain on labeled synthetic fixtures in tmp_path: COMMIT (Slice 3d, long-scores both arms,
  sha256 seal) → **I1** gate (reveal before target_t refused, no scored rows) → REVEAL+SCORE (Slice 4b,
  both arms ic_point float) → **I2** (idempotent re-reveal appends nothing + immutable sealed-scores
  sha256, byte-mutation flips hash) → ACCUMULATE (Slice 4c, n_months=1, summary key set,
  dm_flag=degenerate) → **I9** (forward chain writes ONLY runs/forward/ + ledger.jsonl, never
  runs/results/). I3–I8 explicitly NOT duplicated (owned by existing invariant suites).
  `config/e3_live_contracts.yaml`: `max_age_sessions` 23 → **22** + `authoritative_refresh: null`
  explicit + PROPOSED → **FROZEN (D2, 2026-08-03)**; cron stays DISABLED, headline still needs owner GO.
  `tests/test_e3_forward_trigger.py`: 7× 23 → 22 + proposed-marker test renamed frozen-marker.
  **Verified: 7 forward suites 84 passed; full hermetic suite exit 0; ruff clean; real-ledger guard
  PASS; git diff --name-only = the 3 files; pre-existing Track-B WIP untouched.** Slice 7 code complete;
  only E3 headline (AUD-06 done + owner GO) and RES-08/RES-10 (owner-gated) remain.
- **2026-08-03 `/goal` batch 6 — RES-02 + RES-03 EXECUTED via 2 worktree-isolated agents (COMMITTED
  + pushed, `825658b`):** owner authorized execution ("授权你继续执行"). **2 sonnet agents in isolated
  git worktrees** (the correct "各自推进/不影响各自进程" mechanism — no writer race, no Track-B WIP
  conflict), each delivered INLINE this time. Merged into main; both exploratory baselines PREPARED but
  NOT registered (runners refuse to run until the owner's `config_committed` ledger row exists):
  - **RES-02 (BASELINE-FF5-001)**: ff5.py ingest (bulk-ZIP, sha256 snapshot, ≥2s politeness) + macro_dff.py
    (ALFRED vintage, strictly-before as-of) + features/ff5.py (stock-specific rolling exposures +
    interactions, RD-13 gate) + runner (aborts without owner ledger row) + config (20 cols) + 41 tests.
  - **RES-03 (BASELINE-RANK-001)**: learner.py rank-aware branch enforcing frozen RD-15 enum
    (validate_objective("lambdarank"); "regression" branch untouched) + runner (frozen chain
    construct_month_groups→…→fit_predict_rank) + config + 15 tests. `ranking_contract.py` 0-diff.
  - **Full hermetic suite: 1408 passed / 0 failed** (+56 new tests); ruff clean; ledger 0 diff; no
    frozen surface touched; no real data run. docs: data-intake-french-ff5.md (7-gate, owner 签注
    PENDING) + baseline-ladder{,-ff5,-rank}.md (index + per-baseline, conflict-merged).
  - **Both baselines now await: owner authorization + `config_committed` ledger row before any OOS
    metric.**
- **2026-08-03 `/goal` batch 5 — RES specs rewritten via 4 parallel agents (COMMITTED + pushed, `2f87970`):**
  executed approved D5 (RES restart) the RIGHT way this time: **4 sonnet agents dispatched in 2 batches of
  2 (≤2 concurrent proxy cap), file-isolated (each writes only its own task file — parallel without the
  writer race), verified each touched ONLY its target**. Each rewrite fixes its root defect:
  - RES-02: raw market-wide FF5/DFF columns (zero cross-sectional variation → unrankable) → stock-specific
    rolling beta-to-factor + loading×characteristic interactions; PIT proof + RD-13 guard + French 7-gate
  - RES-03: defined the rank-label/query contract anchored to FROZEN RD-15 + ranking_contract.py; removed
    invalid objective names; forbidden to modify frozen impl
  - RES-08: monolithic → durable 5-stage schema/sample/annotation/adjudication/freeze (ADR-006), REUSING
    the existing docs/llm-extractor-eval.md + src/aionis/schema/gold_annotation.py schema (not reinventing)
  - RES-10: every metric anchored to RD-04/06/07/08/11 + RES-08 gold set (no re-spec from scratch)
  All 4 agents went idle without reports (idle-without-result pattern) but their work landed in the tree —
  verified from repo state, NOT prose (§8 recovery path). 8 files (+679/-340); ledger 0 diff; no
  src/frozen-surface change. All 4 specs now "REWRITTEN 2026-08-03 — ready for owner authorization".
- **2026-08-03 `/goal` batch 4 — approved owner decisions executed (COMMITTED + pushed, `c09bd0b`):**
  owner approved all recommendations (D1-D8). Evidence in `reports/design/2026-08-03-owner-decision-execution.md`.
  D1: Track B config VERIFIED already frozen 2026-08-02 (ledger #41/#42) — no new row. D2: AUD-06 contracts
  FROZEN (`max_age_sessions=22`, `authoritative_refresh=None` — factual, no standalone universe script;
  `block_on_unknown=True`) → **E3 Slice 6/7 may proceed to implementation** (headline still gated by owner GO).
  D3: C5 Option A — politeness split in CLAUDE.md L49 (data-fetch ≥2s; model APIs RPM/TPM+cooldown+cache);
  C5 → OWNER-APPROVED. D4: FF 7-gate recorded. D5: RES restart approved (4 specs need rewrite first). D6: RD
  safe queue exhausted. D7: KAIROS verified (MIT, 0-star demo-grade — cite valid). D8: FinLake-Bench CONFIRMED
  NOT RELEASED (name inconsistency FinLake/FinLeak); audit §5 corrected. Docs/state only; no frozen
  surface/ledger/data touched; verification agents used WebFetch only.
- **2026-08-03 `/goal` batch 3 — citation-integrity audit (COMMITTED + pushed, `20191fd`):** directly
  answered the hook's (a)/(c)/(d) requirements. **4 parallel verification agents, tiered by difficulty**
  (haiku ×2: 1-entry E3 + 3 inline IDs; sonnet ×2: 5 frontier + 4 E2 entries) audited ALL arXiv
  citations across frontier_positioning.md / phase-e2 / phase-e3 / theory-of-computable-reality.
  **Result: 11/11 real, none fabricated.** Precision fixes applied to frontier_positioning.md:
  L62-65 overstatement (`2504.14765` = recall-level memorization; "functional lookahead bias" term +
  `market_impact` detail NOT in abstract — possible sister-paper conflation), L49 anchored to real
  title, L35-36 bare IDs → full URLs. **External-reuse verdict (7-gate)**: purgedcv (MIT, installed/
  pinned/importable) = only compliant wheel; lookaheadbench + CAMEF no LICENSE → non-reusable;
  Alpha Illusion code link dead (404); 2504.14765 CC BY-NC-ND → citation-only; CausalStock no repo;
  **FINSABER = Apache-2.0 → passes allowlist (the wheel Track B is mounting — independent license
  evidence)**. Profit Mirage's "51-62% Sharpe decay" verified verbatim. Full ledger:
  `reports/design/2026-08-03-citation-integrity-audit.md`. Docs-only, no code/frozen-surface change.
- **2026-08-03 `/goal` batch 2 — Slice-2 backlog fully closed (COMMITTED + pushed):** completed the
  remaining Slice-2 items. (1) **`5ffdbe1`** — first-run `last_poll_ts=None` seeding docstring notes in
  all 3 forward collectors (13D/macro/8-K; docstring-only). (2) **`758d87e`** — structlog warning when
  `persist_snapshot` writes the REAL ledger (`runs_dir=None`): the shared persist tail covers all 3
  collectors at once; the backlog's `forward_only=True` wording was stale (row-level constant, not a
  param). Not unit-tested by design (exercising the branch would write the real ledger, which
  `test_real_ledger_jsonl_untouched` pins as forbidden). **Full hermetic suite: 1352 passed / 0 failed**
  (final verification); ruff clean; forward-ingest 16/16. Both pushed. Track-B WIP untouched; no frozen
  surface / ledger / data touched; no real network/LLM/trial.
- **2026-08-03 `/goal` reuse-first batch (COMMITTED + pushed, `f6e0536` + `e6c71ec`):** resumed the
  priority offline program under the owner `/goal` (更多 agents 按优先等级推进; 难度分级模型; 复用轮子禁止重造).
  Proxy is `[1210]`-flaky → direct-write (opus) chosen over dispatch for coherence + token-efficiency.
  (1) **`f6e0536`** — Slice-2 "S cleanup": DRY'd the identical archive→cumulative→ledger tail of the 3
  forward collectors (13D/macro/8-K) into `_common.persist_snapshot(...)` (n_rows appended LAST to keep
  per-collector ledger key order → byte-identical output, H6). Also dropped the redundant `keyfn=str.upper`
  dead branch in earnings_8k. (2) **`e6c71ec`** — full-suite was RED (12 `test_static_site.py` failures,
  pre-existing on clean HEAD): tests were stale vs the committed Track B page (English/base64/tabs). Aligned
  them (Chinese Track B assertions: 探索性/非投资建议/null-预期可发表, SESOI 0.010, 诚实边界, 七主题, 差分
  #41/#42, FF5/mounts, data-driven plotly, no runtime fetch, H6 determinism) AND added `--out-dir` so tests
  build to tmp_path — **hermetic, never touches the `site/` WIP** (Track B's uncommitted `M site/index.html`
  + `D` 2 JSON files stay untouched). **Full hermetic suite now 1352 passed / 0 failed; ruff clean.** Both
  pushed. 状态: state/current.md updated.
- **2026-08-03 ORCH-02 second wave (REJECTED — no code change):** attempted to mirror the
  cumulative-preserve test for 8-K, but the premise was a **grep-suffix miss**: 8-K already has the
  invariant via `test_8k_forward_idempotent_and_cumulative_preserve` (`tests/test_forward_ingest.py:504`).
  A `[1210]`-failed executor had nonetheless written a complete (redundant) test into the working tree
  before its API error; detected via `git diff`, discarded via `git restore` (redundant duplication,
  contra 治理复杂度 ≤ 产出). **Three binding findings**: (1) `[1210]` hit 2 consecutive sonnet spawns
  (`oh-my-claudecode:executor` + `general-purpose`) — today's proxy is flakier than the handoff's
  "transient, single retry works" note, and `general-purpose` did NOT bypass it this time; (2) a
  "failed" subagent can mutate the tree before its API error — always `git status`/`git diff` after a
  failed spawn (folded into `docs/orchestration-protocol.md §8`); (3) gap-analysis must grep the
  CONCEPT (`grep -iE "cumulative.*preserve"`), not a name suffix — the suffix grep manufactured a
  false gap. Task recorded as REJECTED in `tasks/rejected/TASK-ORCH-02-*.md`. Subagent dispatch is
  currently unreliable in this proxy — for the next wave, prefer direct-write (opus) for S test
  mirrors unless the proxy recovers.
- **2026-08-03 ORCH-01 first wave (COMMITTED `8d19b28`):** validated the ADR-012 dispatch protocol
  end-to-end. Picked the backlog "macro cumulative-preserve test" (S, hermetic). Ran
  `scripts/orchestrate_dispatch.py --lane executor` → clean 6-layer contract (exit 0). Dispatched sonnet
  `executor` (orch01-executor) → implemented `test_macro_forward_cumulative_parquet_preserves_prior_rows`
  (tests/test_forward_ingest.py:373, +75 lines; faithful 13D mirror — cumulative==24, snapshot_ts=={t1,t2},
  T1+T2 pub-dates ⊂ cum). Orchestrator independent verify: pytest 16/16 green, ruff clean.
  **Reviewer-lane operability gap (binding finding)**: the dispatched `code-reviewer` (sonnet) went idle
  WITHOUT returning a verdict (×2); per WORKFLOW §17 (2-identical-failures stop) the Orchestrator
  proceeded on independent deterministic verification + line-by-line diff review, deviation explicitly
  disclosed in the commit. **Harness behavior**: sync subagents return via `idle_notification`, not inline
  — reclaim L6 via SendMessage; for code lanes, recover from repo state (git diff + pytest + ruff), never
  trust worker prose. Folded into `docs/orchestration-protocol.md §8`.
- **2026-08-03 orchestration protocol (COMMITTED `daa92e8`):** owner directive — "主agent编排+验收,
  高等级模型监工(低频), 分配任务给其他模型, review+e2e会话, 跨会话降噪, issue编排任务" — implemented by
  **binding existing OMC primitives**, not building a new framework (reuse-first). Owner chose **local task
  files = issues** (zero GitHub surface; minimizes the 治理复杂度>产出 drift). New additive artifacts:
  `decisions/ADR-012-orchestration-protocol.md` (ACCEPTED) + `docs/orchestration-protocol.md` (operational
  spec) + `scripts/orchestrate_dispatch.py` (6-layer contract emitter, reuses RD-01 `lint_task_file`) +
  `tests/test_orchestrate_dispatch.py` (11/11 green, ruff clean) + `tasks/templates/DISPATCH-CONTRACT.md`.
  Registered ADR-011 + ADR-012 in `decisions/index.md`; added CLAUDE.md see-also pointer. Lane model: opus
  Orchestrator + **low-freq opus Supervisor (监工, gates only)** + sonnet `executor`/haiku workers
  (serialized, ≤2 concurrent — parallel-writer race + `[1210]` cap) + independent `verifier`(验收) /
  `code-reviewer` / `qa-tester`(e2e) lanes. Denoising = 6-layer dispatch contract (WORKFLOW §10) + structured
  handoff (workers return files/tests/evidence/next-action, never narrative; no full-chat forwarding).
  Anti-leakage guardrails binding on every dispatch (no real network/LLM/forward; frozen surfaces read-only;
  config_committed-before-result; ledger 0-diff). **Additive only** — no frozen surface / ledger / data /
  Track-B code touched; no real network/LLM/trial ran. Next: owner commissions the first wave (pick a task →
  run the helper → dispatch to `executor`).

- **2026-08-02 strategic review:** "是否跑偏 + 七主题低成本覆盖" deep-dive → `reports/2026-08-02-strategic-review-coverage-and-alignment.md` + 6 `reports/design/` artifacts (Track A/B slice plans, slice review, qlib POC, wheel-mount pack, reuse-catalog v2) + `src/aionis/eval/ff5_residual.py` (挂接③, 18 tests green, ruff clean; exploratory, not wired to pipeline/ledger). Verdict: direction sound; two失调. **Owner decision (2026-08-02):** Track B adopted + new prereg (`decisions/ADR-011-track-b-seven-theme-platform.md` + `docs/track-b-preregistration.md` PROPOSED); 挂接③ first slice done. **Pending:** owner freezes config sha256 before real-data. 未触冻结面/ledger/E3；无真实 network/LLM/trial.
- **round:** Wave-A execution. AUD-05B is closed after authorized re-Review. Dashboard extraction
  and C4 Option A cleanup are committed in `7dede9b`. C1 BLS disable, C2 VIX FRED adapter and C3
  PRAW requestor wrapper are COMPLETE after Engineer evidence, independent Verifier PASS and
  independent Reviewer APPROVE, and are ready for the Group A commit. 2026-08-01.
- **outcome:** project remains an evidence-first PIT research harness, not a validated stock-picking strategy.
  Historical B/C/D/E1 are shared-fold purged CV-proxies (not chronological OOS); LLM not in headlines;
  E3 NO-GO for headline.
- **COMPLETE:** AUD-01/02/03/04/05A/05B (each Verifier PASS + Reviewer APPROVE); AUD-05C disposition
  (Reviewer APPROVE; 10 boundaries → C1-C5 + Kenneth-French task files); **AUD-07 FROZEN** via
  [ADR-010](../decisions/ADR-010-sesoi-tost-sequential-gate.md) + E3 pre-reg §7 (SESOI ±0.010 / HAC-TOST
  90% / O'Brien-Fleming 60·90·120mo / n_trials=30; 3× cross-validated; equivalence+sequential
  construction amended).
- **STATISTICAL HOLD:** AUD-07B reopens the implementation-level proof only: ADR-010's amendment says
  TOST p-values “exceed alpha”, which appears reversed, and the sequential equivalence construction
  requires strong independent review. Do not implement or expose E3 inferential verdicts meanwhile.
- **C-series prepped → owner-decidable:**
  - **C3 (PRAW 7-gate)**: OWNER APPROVED WITH CONDITIONS (all 7 gates PASS; G1 BSD-2/Apache-2.0, G2 PIT,
    G3 snapshot handles user-edits, G4 sha256+append, G5/G6 exploratory-only, G7 PRAW 1.5s+ToS).
    Conditions: Reddit ToS internal-only/no-redistribute; permanent `mode:exploratory`. Engineer,
    Verifier and Reviewer are complete; no live pull is authorized.
  - **C1 (BLS disable)**: owner-authorized disable-only implementation is complete. CPI/NFP cache
    misses fail closed before HTTP; FOMC/cache behavior is preserved. Independent Verifier PASS and
    Reviewer APPROVE are recorded; Group A commit is next.
  - **C2 (VIX/FRED)**: owner-authorized implementation replaces SDK fetches with the shared-policy
    FRED observations adapter while retaining ADR-003 PIT/cache/ledger behavior. Independent
    Verifier PASS and Reviewer APPROVE are recorded.
  - **C4 (health_check)**: standalone Option A is owner-authorized and complete in `7dede9b`.
    The blocked data/wheel probes and stale text are removed; seven hermetic tests, lint, scan and
    review pass.
  - **C5 (model-API ≥2s)**: **Option A (SDK-exempt)** recommended — model APIs throttled by provider
    RPM/TPM + ProviderRouter cooldown + idempotent cache; ≥2s redundant for GLM (RPM 30), harmful for
    SiliconFlow (RPM 1000). Rule wording drafted. → owner accept.
- **P2 legacy split → partially replan-required**: 10 prior `TASK-RES-01..10` files exist (baseline-ladder
  RES-01/02/03 [mom/FF5/rank-objective]; economic-lens RES-04/05/06/07 [next-open/turnover-slippage/
  liquidity-borrow/delisting-capacity]; LLM-eval RES-08/09/10 [gold-set/zero-LLM-ablation/eval-metrics]).
  RES-02/03/08/10 are now HOLD/REPLAN because of cross-sectional-variation, rank-label,
  durable-gold and remote-determinism defects. Do not authorize those files as written; use RD tasks first.
- **owner-decision queue (consolidated — further progress needs these):**
  - **C5**: accept Option A + record the rule wording?
  - **Kenneth-French / selection-panel FRED+Fama-French**: data-intake 7-gate decision.
  - **AUD-06**: owner contract (E3 live-input readiness acceptance points).
  - **RES program**: no legacy RES task should start before RD-17 and its listed prerequisites; RES-02/03/08/10
    specifically require rewritten specs.
  - **RD program**: launch only P0 closure, P0 + the offline RD-01..17 program, or selected RD tasks?
  - **Commit?** audit remediation is committed as `e8545d4` and dashboard/C4 remediation as
    `7dede9b` (both on remote `main`). C1/C2 await independent review before their own commit.
- **verification:** the full hermetic pytest suite currently passes (existing forward-score warnings
  only), `uv run --offline ruff check` and `git diff --check` pass, and frozen
  prereg/ADR/config/ledger/results/data/forward remain untouched. Group A C1/C2/C3 each have
  independent Verifier PASS and Reviewer APPROVE. `runs/ledger.jsonl` remains unchanged; no E3
  outcome was observed and no confirmatory/strategy/horizon/forward/real-network/LLM script ran.
- **planning artifact:** `reports/milestone/2026-08-01-low-reasoning-development-roadmap.md` and
  the Wave-A launch brief and `TASK-RD-00..17` split the next safe work into a 10.75–16 hour first
  offline wave and a 25.5–40 hour complete Engineer package. `TASK-AUD-07B` is strong-only. This is a
  frozen task proposal. The final unattended prompt selects C1/C2/C3 + RD-04/05/06/07/09/10/12,
  has explicit context-compaction/token rules, and received independent Reviewer APPROVE. It becomes
  implementation GO only when the owner pastes it into the new Goal session.
- **proxy note:** 3-parallel subagent spawns fail with proxy 400 `[1210]`; ≤2-parallel / single work.
  Future dispatch ≤2 concurrent.
- **do NOT:** run confirmatory/strategy/horizon/forward scripts; edit frozen prereg/ADR/config; infer
  B's paired differential CI; call historical cross-fit chronological OOS; inspect E3 outcome metrics;
  ignite E3 headline.
- **git:** branch `feat/e3-forward-ledger`; remote `main` includes `7dede9b`. Current uncommitted
  code includes approved C1/C2/C3 implementation/tests plus planning/state/task documentation; the
  Group A commit will use explicit file lists only.

## Overnight checkpoint (Wave-A)

- Goal: execute Wave-A C1/C2/C3 + RD-04/05/06/07/09/10/12 with independent gates and safe push. **COMPLETE.**
- All gates passed: C1/C2/C3 + RD-04/05/06/07/09/10/12 each have independent Verifier PASS + Reviewer APPROVE.
  Fixes applied and re-gated: RD-07 (generated_at caller-provided for byte-stability), RD-10 (vol_adj_mom
  last-12 window + std<=0), RD-12 (additive constituents_manifest_on + 3 unskipped manifest oracles;
  constituents_on behavior unchanged).
- Commits: `6085e92` Group A, `2653907` Group B, `5f884a3` Group C. Final docs/state bundle (this commit).
- Final gates: full hermetic pytest green (zero skips; only pre-existing forward_score warnings);
  `uv run --offline ruff check` clean; `git diff --check` clean; frozen/ledger/results/data/forward diff
  empty; no data/.env/*.parquet staged; no real network/LLM/research/forward script ran; E3 outcome unobserved.
- Files: RD-01/02/03/08/11/13..17 task specs remain PLANNED (future waves) — committed as planning docs.
- Blockers: none. Next: optional fast-forward push HEAD:main (origin/main is ancestor of HEAD).

## Wave-B checkpoint (2026-08-01, in progress)

- **Launch authorization:** owner `/goal` — "启用更多 agents 根据优先等级在不影响各自进程的前提下各自推进".
  Treated as owner authorization for the priority (P0→P1) offline RD program (the safe sonnet-tier set).
  Per-task authorization is recorded in each task file's 状态 line by the Orchestrator as the audit trail.
- **COMPLETE so far** (each: Engineer → independent Verifier PASS → independent Reviewer APPROVE → atomic
  commit; offline/hermetic; `runs/ledger.jsonl` untouched; no frozen surface touched):
  - RD-02 validation manifest — `97e5688`
  - RD-01 task-contract linter — `feb80ba` (first attempt lost to the parallel-writer race below; redone serially)
  - RD-13 cross-sectional variation guard — `2f0efd0`
- **KEY OPERATIONAL FINDING (binding):** spawning ≥2 writer subagents concurrently in the SHARED working tree
  loses one agent's untracked deliverables (RD-01 first attempt: `.pyc` survived in gitignored `__pycache__`,
  `.py` + README diff gone — consistent with a `git clean -fd`/`restore` across parallel-agent boundaries).
  **Writers are now SERIALIZED: exactly ONE Engineer subagent per message.** Parallel is reserved for read-only
  preflights only. See memory `aionis-parallel-writer-race`.
- **Model routing (binding):** only `sonnet`/`haiku` subagent aliases resolve to subagent-safe IDs; `opus`/`fable`
  resolve to `[1M]`-suffixed IDs and are DENIED by the enforcer. The RD program is sonnet-tier so this is fine.
  `TASK-AUD-07B` (strong-only, STATISTICAL HOLD) and `RD-15` (strong precondition) are DEFERRED until opus
  routing is fixed (drop `[1M]` suffix from `ANTHROPIC_DEFAULT_OPUS_MODEL`).
- **Authorization bookkeeping:** the first RD-02 Reviewer returned BLOCKED solely because the task file still said
  "PLANNED — not implementation-authorized"; resolved by recording the /goal authorization in the task 状态 line.
  All subsequently launched RD tasks are pre-authorized in their task files before dispatch.
- **Remaining safe queue (P1, sonnet-tier):** RD-17 (trial-intent registry) → RD-16 (eval uncertainty) → RD-11
  (provider replay) → RD-03 (chronological oracle, unlocked by RD-02 APPROVE) → RD-14 (reproducibility capsule,
  unlocked by RD-02 APPROVE). RD-08 remains HOLD (needs a strong-Researcher-frozen rule table first). RD-15 deferred (strong).
- **Verification status:** per-task pytest + ruff green; ledger empty diff across all Wave-B commits; no frozen
  prereg/ADR/config/result/data/forward surface touched; no real network/LLM/trial ran. The full hermetic suite
  has NOT been re-run this wave yet (defer to a pre-push gate).
- **Git:** branch `feat/e3-forward-ledger` ahead of origin by 8 (Wave-A + Wave-B). Not pushed (owner's call).
- **Do NOT:** run confirmatory/strategy/horizon/forward scripts; edit frozen prereg/ADR/config; observe E3
  outcome; spawn >1 writer subagent per message.

## Wave-B FINAL (2026-08-01, COMPLETE)

All 8 safe sonnet-tier RD tasks implemented, each with independent Verifier PASS + Reviewer APPROVE and an
atomic commit; offline/hermetic throughout:
- RD-02 validation manifest — `97e5688`
- RD-01 task-contract linter — `feb80ba` (first attempt lost to the parallel-writer race; redone serially)
- RD-13 cross-sectional variation guard — `2f0efd0`
- RD-17 trial-intent registry (HIGH-risk; ledger-bypass cleared) — `5dfe849`
- RD-16 eval uncertainty (Wilson≠Wald; seed=0 stratified bootstrap) — `ee223ae`
- RD-11 provider replay (salvaged a cut-off partial; audited + completed; providers/llm_client 0 diff) — `8a46179`
- RD-03 chronological oracle (HIGH-risk; cv.py 0 diff; lookahead rejected; real purgedcv) — `af7d673`
- RD-14 reproducibility capsule (outcome-free; deterministic capsule_id; atomic write + refuse-overwrite) — `f397383`

Final pre-push verification: full hermetic pytest GREEN (zero failures/skips; only the pre-existing
forward-score UserWarnings documented in Wave-A); `uv run --offline ruff check` clean; `runs/ledger.jsonl`
0 diff across the whole wave; frozen-surface audit (docs/phase-*, decisions/, runs/ledger, config/, data/,
*.parquet, pyproject.toml, uv.lock) — NONE touched; no real network/LLM/trial/forward script ran; E3 outcome
unobserved.

Process notes (binding for future waves):
- Writers are SERIALIZED (exactly one Engineer subagent per message) — parallel writers in the shared tree
  lost untracked deliverables (see memory aionis-parallel-writer-race).
- Only `sonnet`/`haiku` subagent aliases are dispatchable; `opus`/`fable` resolve to `[1M]` IDs and are
  denied by the enforcer → `TASK-AUD-07B` (strong-only) + `RD-15` (strong precondition) are DEFERRED until
  opus routing is fixed.
- The `[1210]` proxy "API parameter" error is transient on Reviewer spawns — a single retry has succeeded
  every time; it is NOT the 5-hour usage cap.
- Owner authorization for the priority RD program was the `/goal` directive; recorded per-task in each task
  file's 状态 line. (The first RD-02 Reviewer BLOCKed on the stale "PLANNED — not implementation-authorized"
  status, which is why all later tasks were pre-authorized in their task files before dispatch.)
- Per the owner: do not spend tokens checking whether the 5-hour usage cap has reset — if the session is
  running, it is reset (see memory aionis-no-rate-limit-check).

Remaining (NOT started — legitimately blocked, not merely unauthorized):
- RD-08 HOLD — needs a strong-Researcher-frozen zero-LLM rule table before low-reasoning implementation.
- RD-15 DEFERRED — rank-objective contract is a strong-model decision precondition (lambdarank vs rank_xendcg,
  monthly relevance binning, ties, missing, group=query-month); also needs opus routing.
- AUD-07B — STATISTICAL HOLD on ADR-010 TOST p-value direction / sequential-equivalence construction; strong-only.
- RES-02/03/08/10 — HOLD/replan per roadmap; their foundations (RD-13 done; RD-15/RD-08 still pending) must
  precede them.

Git: branch `feat/e3-forward-ledger` ahead of origin by 13 (Wave-A + Wave-B). Not pushed — owner's call.
Safe RD queue now exhausted for the sonnet tier.

## Track B 首个 OOS 观察（2026-08-02）

**treatment 臂（config #41）**: mean_ic 0.0055, 95% HAC CI (-0.021, 0.033), p=0.689（null）。**price-only 臂（#42）**: mean_ic -0.0021, CI (-0.032, 0.028), p=0.891（null）。**差分（#41 − #42, §1 headline）**: mean_diff 0.0076, CI (-0.004, 0.020) 跨零, p=0.219 → treatment 未显著优于 price-only（null，符合 null-favored）；CI 上界 0.020 > SESOI 0.010 → 不构成严格等价（需更多样本）。见 docs/track-b-results.md。

## AUD-07B — statistical review COMPLETE (2026-08-01, CRITICAL finding)

AUD-07B (P0 / CRITICAL) is now reviewed by TWO opus agents (a strong-statistician audit + an INDEPENDENT
opus Reviewer, APPROVE). Both confirm ADR-010's equivalence/sequential gate has TWO CRITICAL defects:
1. **TOST rejection direction is REVERSED.** ADR-010 Line 42 requires the two one-sided p-values to
   "exceed alpha" (p > α); the correct Schuirmann (1987) rule is: declare equivalence iff p1 < α AND p2 < α.
   As written, the gate would declare NON-equivalence, not equivalence.
2. **Sequential CI duality is BROKEN.** ADR-010 pairs a fixed 90% CI with look-specific O'Brien-Fleming αk,
   which breaks the TOST⇔CI duality at looks 2–3 and inflates first-look Type I error ~9.6× (0.05 vs
   ~0.0052). Correct construction: look-specific (1−2αk) CIs (98.96% / 96.84% / 91.26%), or a recognized
   group-sequential equivalence construction (Jennison–Turnbull 2000).
CI duality at α=0.05 (90% CI), the union–intersection composite null, and HAC (Newey-West) SE all PASS.
Report: `reports/audits/e3-tost-sequential-correction-review.md`.

CONSEQUENCE (binding): the E3 inferential-verdict and headline remain HOLD. Implementing or exposing any E3
equivalence verdict before the owner authorizes an ADR-010 + prereg §7 amendment (p < αk; look-specific CI)
is FORBIDDEN. This is an owner decision — ADR-010 and the prereg are frozen; the audit does NOT modify them.
Open non-blocking note: ADR-010's αk source (0.0052 / 0.0158 / 0.0437) is undocumented and did not match the
reviewer's independent Lan-DeMets OBF recomputation — owner should confirm the αk provenance as part of the
amendment.

## Model-differentiation policy (2026-08-01, per owner /goal)

opus subagent routing was fixed (`ANTHROPIC_DEFAULT_OPUS_MODEL` now `claude-opus-4-8`, no `[1M]` suffix).
Difficulty-based dispatch is now in effect to save tokens:
- **opus** — only genuinely hard analysis/decisions (AUD-07B statistician + reviewer done; RD-15 rank-objective
  contract and the RD-08 zero-LLM rule-table draft are the next opus candidates).
- **sonnet** — standard code/review (Wave-B RD tasks).
- **haiku** — mechanical verification, simple doc/grep checks.
Writers remain SERIALIZED (one Engineer per message; parallel-writer rule still binds).

## RD-15 — rank-objective DECISION PACKET proposed (2026-08-01, pending owner freeze)

RD-15 (P2 / HIGH-risk) decision precondition is now drafted by an opus Architect at
`reports/design/2026-08-01-rd15-rank-objective-contract.md` (PROPOSED — pending owner freeze). 7 of 8
choices are determined by theory; ONE is an owner-preference question:
- **Open owner question:** bin count for monthly relevance — **quintiles (5, robust, default)** vs
  **deciles (10, aggressive)**. Ranking theory does not uniquely determine this for the rank-IC estimand.
Theory-fixed choices: objective = **lambdarank** (rank_xendcg rejected; allowed-enum fixed so non-existent
objectives are rejected); per-month quantile binning fit ONLY on the train fold; group = query-month; ties
share the relevance integer; NaN returns excluded (NaN features → LightGBM default); test out-of-range
returns clamped to nearest train-fold edge + reason code (never refit). Four testable leakage invariants
specified (month-permutation, future-truncation, train-fold-only fit, group-size stability).

After owner freeze, a sonnet Engineer implements `src/aionis/eval/ranking_contract.py` + tests mechanically
(no self-selection). No code/learner/frozen surface changed by the decision packet.

### Update (2026-08-01, continued — model-differentiated dispatch)
- **RD-15 implementation COMPLETE** — `ea335c8` (sonnet Engineer + independent Verifier PASS + Reviewer
  APPROVE; 0 blocking). `src/aionis/eval/ranking_contract.py` implements the decision packet (objective enum
  lambdarank/rank_xendcg; per-month train-fold-only binning; out-of-range clamp+reason; group=query-month; 4
  leakage invariants). `bin_count` is a parameter (default 5/quintiles, supports 10/deciles) — the methodology
  freeze of the actual value remains the owner's (via config), not hard-coded. learner.py untouched (0 diff);
  31 module tests + full suite (1348) green.
- **RD-08 rule table PROPOSED** — `evals/expected/zero_llm_rules_v1.yaml` (opus strong-Researcher), pending
  owner freeze. 10 conservative abstain-heavy rules (FOMC×3, CPI×2, NFP×2, 13D×3); default/conflict=abstain;
  8k_2_02 deferred. Two owner decisions flagged: 13D actor_type (COLLECTIVE vs ORGANIZATION) and whether to
  include 8k_2_02. After freeze, a sonnet Engineer implements `src/aionis/extraction/zero_llm_baseline.py`
  verbatim from the table.
- **Tier usage this session:** opus for AUD-07B (statistician + independent reviewer) and RD-15 decision +
  RD-08 rule-table draft (genuinely hard analysis/domain-modeling); sonnet for all Wave-B code + RD-15 impl +
  verifications/reviews (standard). haiku unused — no remaining priority task is mechanical-tier (forcing it
  would be false economy). Reviewer `[1210]` proxy errors were bypassed by switching `oh-my-claudecode:code-
  reviewer` → `general-purpose` (same sonnet tier) when they recurred.

## Owner decisions + independent opus reviews (2026-08-01)

Owner decisions: ADR-010 → Jennison-Turnbull construction (B); RD-15 bin_count → quintiles/5 (A); RD-08 → freeze
(A) + COLLECTIVE + defer 8k_2_02; RES → hold (A); commission independent opus review of RD-08 + RD-15 (5B);
housekeeping done (local main FF to origin/main; remote feat/e3-forward-ledger deleted). All Wave-B/AUD-07B/
RD-15/RD-08 work pushed to origin/main (HEAD e58b16e).

Independent opus review outcomes:
- **RD-15 decision packet: APPROVE** (0 CRITICAL/MAJOR; leakage guards sufficient, implementation faithful).
  Owner froze bin_count=5.
- **RD-08 rule table: REQUEST CHANGES → FIXED → FROZEN.** Review found 4 CRITICAL (enum NAME vs lowercase VALUE;
  FOMC forward-guidance false positives; 13D→13d; negation-window unit undefined) + 2 MAJOR (CPI/NFP secondary
  patterns; rule-count comment). An opus fixer resolved all: lowercase enum values; added fomc_guidance_abstain_001
  (precedence 110, abstain-only); 13d; negation = whitespace words; tightened CPI/NFP; accurate count (now 11).
  event_type semantics confirmed: FOMC/CPI/NFP are valid (`src/aionis/config.py` ECONOMIC_EVENT_TYPES); the gold
  `Literal["13d","8k_2_02"]` is filing-specific. Table FROZEN.

Still queued (owner-authorized, not yet done this session): RD-08 sonnet implementation of `zero_llm_baseline.py`;
ADR-010 Jennison-Turnbull amendment (opus design + independent opus review + apply to frozen ADR-010/prereg §7).

## ADR-010 Amendment APPLIED (2026-08-01) — Jennison-Turnbull; RD-08 implemented

- **RD-08 zero-LLM baseline COMPLETE** — `src/aionis/extraction/zero_llm_baseline.py` (sonnet Engineer + haiku
  lint-fix + independent Verifier functional PASS + independent Reviewer APPROVE). Mechanically applies the
  FROZEN rule table (11 rules; lowercase enum values; sha256 provenance; 6 abstain paths; fomc_guidance_abstain_001
  precedence-110 suppresses forward-guidance false positives). Structural-only (no sentiment/market_impact);
  providers/llm_client/frozen table untouched. Committed + pushed.
- **ADR-010 Amendment 2026-08-01 APPLIED** (owner Decision 1 = option B). The broken "Cross-validation amendment
  (2026-07-31)" is VOID; replaced by a Jennison-Turnbull (2000) group-sequential equivalence construction
  (OBF zₖ = z_α/√Iₖ → look-specific RCI levels 99.44 / 97.64 / 95.00%; equivalence iff RCIₖ ⊂ [−SESOI, +SESOI],
  which structurally prevents the reversed-direction error; Type I ≤ 0.05). Prereg §7 amended in lockstep.
  Ratified sub-choices: standard OBF (over Lan-DeMets — more conservative early), no futility, 95% final look.
  Frozen params unchanged (SESOI ±0.010, looks {60,90,120}, n_trials=30, HAC SE). Double-opus (design +
  independent review) at `reports/audits/e3-jt-amendment-proposal.md`; audit at
  `reports/audits/e3-tost-sequential-correction-review.md`.
- **CONSEQUENCE:** the E3 statistical-gate HOLD from AUD-07B is LIFTED (the gate is now mathematically valid).
  E3 itself remains gated by AUD-06 (live-input readiness) + a separate owner GO (per the AUD-00 dependency
  graph); no E3 ignition is authorized here. Eval-code implementation of the RCI rule is a separate future task.

All owner decisions 2026-08-01 are now executed except RES restart (intentionally held) and optional follow-ups
(RD-08 rule-table re-review, eval-code RCI implementation). Everything is on origin/main.

## Dashboard v2 — near-final-product analysis interface (2026-08-01, built + gated)

Per owner intent ("把现有研究工作台做成接近最终产品形态的分析界面"; data demonstrative only), built a Streamlit+plotly
dashboard realizing `docs/dashboard-v2-design.md`'s 5 dimensions on deterministic synthetic data:
- `dashboard/{demo_data,charts_v2,app_v2}.py` + `dashboard/README_v2.md` + `tests/test_dashboard_v2.py` +
  `reports/design/2026-08-01-dashboard-v2-deploy-research.md`.
- 5 tabs (拟合质量/波动结构/曲线演化/事件前后差异/不确定性), sidebar (Phase/Arm/Horizon/Event-type), publishability gate
  (ci_half<0.015) + "Preliminary data — demonstrates the method" caption on every tab. 11 plotly chart builders
  (alphalens/pyfolio/empyrical methodology, Apache-2.0; no new deps).
- Gated: independent Verifier (AppTest headless render — caught + fixed a `StreamlitDuplicateElementId` crash via
  unique `key=`) + Reviewer APPROVE. 32 tests pass; ruff clean. `src/aionis/**`, `dashboard/app.py` (v1),
  `runs/ledger.jsonl`, data, frozen surfaces all UNMODIFIED.
- RUN: `uv run streamlit run dashboard/app_v2.py`. Deploy: GitHub Pages CANNOT host Streamlit (static-only);
  for the interactive dashboard on a private repo, Hugging Face Spaces (Streamlit runtime, free, private-OK) is
  the recommended host (see the research report). Not yet deployed — owner's call.
- **STATIC site DEPLOYED to GitHub Pages (2026-08-01):** `https://rethymus.github.io/Aionis/` — owner chose
  "static, no interactivity, early-stage presentation." `scripts/build_static_site.py` reuses charts_v2/demo_data
  read-only → `site/index.html` (13 plotly charts, 5 dimensions, EXPLORATORY/DEMONSTRATIVE banner, publishability
  gate). `.github/workflows/deploy-pages.yml` (astral-sh/setup-uv + `uv sync --extra dashboard`; build→upload→deploy
  on push to main). Repo stays PRIVATE; Pages site is public (owner account supports private-repo Pages). Verified
  live (HTTP 200, full content). Independent Verifier PASSED (build, 13 Plotly.newPlot, MD5-deterministic, boundaries).
- **J-T SESOI gate IMPLEMENTED (2026-08-01):** `src/aionis/eval/sesoi_gate.py` + `tests/test_sesoi_gate.py` — the
  executable follow-through of ADR-010's Amendment 2026-08-01. Pure statistical functions (obf_z/obf_alpha/rci_level/
  compute_rci/equivalence_verdict/look_summary/sequential_equivalence_gate) implementing the frozen OBF zₖ=(2.772,
  2.263, 1.960), look-specific RCI levels (99.44/97.64/95.00%), strict-containment equivalence RCIₖ⊂[−0.010,+0.010],
  first-look stopping; reuses `aionis.eval.rank_ic.rank_ic_summary` for HAC SE (not reimplemented). Consumes
  caller-provided IC series ONLY (no E3/ledger/result reads — pure gate logic). Independent Verifier PASS (oracle
  recomputed, strict-boundary, first-look stopping) + Reviewer APPROVE. 28 tests; ruff clean. NOTE: implementing the
  gate does NOT ignite E3 or observe any outcome; E3 still needs AUD-06 + owner GO.
- **AUD-06 live-input readiness gate IMPLEMENTED (2026-08-01, parameterized):** `src/aionis/eval/forward_live_readiness.py`
  (+ tests) + opt-in wiring in `forward_commit_runner.py` (`enforce_live_readiness: bool = False` → historical/no-ledger
  paths SKIP the gate, preserving `_clean_panel`/forward behavior; the live Slice 6/7 caller sets the flag). Fail-closed
  preflight BEFORE any fit/LLM/write/ledger (spy-asserted fit_calls==0 on failure); 25 actionable reason codes; concrete
  checks (predict_session via NYSE, train realized+21-embargo / test retains unknown labels via a forward-specific helper
  NOT `_clean_panel`, price coverage, universe match `constituents_on(t)`, empty-LLM-text→fail, provider-cutoff-not-faked).
  The 2 OWNER-GATED checks are PARAMETERIZED + FAIL-CLOSED when unset: `membership_freshness_contract` (max age /
  authoritative refresh) + `provider_cutoff_policy` (block_on_unknown) — the owner must freeze these before E3 launch
  (the task forbids self-freezing, e.g. treating a 2026-04 snapshot as fresh for 2026-07). Salvaged from a rate-limited
  partial (opus fixer: opt-in flag fixed 2 regressions; fixture/timezone fixes for 8 new tests; ruff). Independent opus
  Verifier PASS (historical-preserved, `_mem_stub` change benign, spy-asserts, fail-closed) + sonnet Reviewer APPROVE.
  47 forward tests pass; ruff clean; ledger/prereg/forward_commit.py untouched. Does NOT ignite E3.
