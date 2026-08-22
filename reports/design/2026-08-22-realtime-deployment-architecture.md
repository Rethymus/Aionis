# 2026-08-22 — 实时数据部署架构方案（GitHub Pages 增强/替代）+ 小隐寺终局形态战略复核

> 定位：**基建 lane 方向文件**（PROPOSED，待业主 GO）。与 `2026-08-21-xiaoyinsi-full-parity-roadmap.md`
> （feature lane）互补：那一份管"补齐哪些页面"，这一份管"数据如何不再被构建冻结"。
> 业主定帧（08-20）不变：小隐寺 = 最终目标形态，只增不删，Aionis 增层五特色。
> 本文 0 代码改动；所有迁移步骤均为 display lane，0 ledger/frozen/config/prereg/OOS。

---

## 1. 问题定义：为什么"无法实时更新数据"

全站实探小隐寺（22 个页面 + sitemap/robots，2026-08-22 抓取）与本仓现状对照后，根因可拆成
五层，**只有第一层是 GitHub Pages 本身**：

| # | 根因 | 现状证据 | 性质 |
|---|------|---------|------|
| R1 | 静态宿主无服务端运行时 | `web/next.config.ts` `output:"export"`，Pages 只回静态文件 | 架构（可绕开） |
| R2 | **数据被烧进构建产物** | 30 个面板 JSON 以 `import xxx from "./xxx.json"` 进 bundle 与预渲染 HTML，部署即固化 | **核心根因** |
| R3 | 数据更新必须走"fetch→export→commit→全量重建 1,480 页→部署"长链 | 日更 cron 一次/工作日 22:00 UTC；价格面板 as_of 受 5 天缓存宽限实际 5-7 天推进一次 | 流程 |
| R4 | 单点依赖 GitHub Actions | 计费故障 08-20 起日更+部署**全部停摆**（blockers.md 首条）；GITHUB_TOKEN 不触发 on:push 的结构性修复也在 Actions 内 | 可用性 |
| R5 | 并发 session 反复在日更 JSON 上 rebase 冲突 | handoff 多轮记录（08-20 "rebase JSON 全冲突"、08-22 双代理协调） | 工程摩擦 |

**关键判断**：R2 才是"数据无法实时"的核心。只要面板数据改成**运行时拉取**，即使继续托管在
GitHub Pages，数据新鲜度也与"重新构建"彻底解耦——浏览器每次加载拉最新 JSON 即可。R1 只有在
需要服务端分页/搜索/海量动态详情页时才真正构成约束（34K 笔政客交易那类规模）。

另外两条**不是**根因、且不可"修复"的：
- 15 个冻结面板（picks/metrics/calibration/ic_monthly…）**设计上永不更新**——反泄漏核心，
  重算 = rerun-to-significance（造假）。唯一合法前进 = E3 forward-live（业主 GO 门）。
- 礼貌抓取纪律（≥2s 间距 + 指数退避）约束了抓取吞吐上限——这不是要绕开的障碍，是项目身份。

---

## 2. 小隐寺技术形态还原（实探结论，补充 08-21 roadmap）

- **部署**：Vercel（资源 URL 带 `?dpl=` 部署 ID）；Next.js App Router + RSC（`?_rsc=` 参数）、
  `next/image` 按需优化、`next/font` 自托管、每页动态 OG 图路由、sitemap 带 hourly/daily
  changefreq → 大量使用 ISR（增量再验证）+ 按需渲染。
- **实时通道**：`/news` 显示"连接中…" = WebSocket/SSE 长连接 7×24 推送；TACO 盘中实时
  （含 Windward 卫星 AIS 霍尔木兹通行量——**采购商业数据源**）。
- **规模**：政客交易 34,307 笔全库分页+7 类筛选+搜索；机构目录 8,741 家；13F 申报流 7,894 份；
  内部人 24h 窗口 4,586 笔；Reddit 榜 963 只标的；举牌 13D 549 + 13G 3,842。
- **产品化**：`/api-docs` = Scalar 动态加载 OpenAPI（端点未公开）；全站页脚"SEC 及其他第三方
  非公开数据库"——**license 不透明**（G1 不可消费，08-19 已裁决）。
- **成熟度参差（对 Aionis 最重要的情报）**：`/events`（8-K 流）、`/quarterly`、`/annual`、
  `/companies` 四页"空壳"（"数据暂不可用"/0 家——**08-22 浏览器复核订正：/events 实为全市场
  实时流、/annual 有 102 份，真空白只有 /quarterly /companies**）；「势力阵营」导航占位未上线。骨架先行、
  管道分批填充——它也在追赶自己的产品承诺。
- **商业模式**：当前零付费墙；免费内容换流量 → 导流主站社区（课程/直播/券商返佣）；
  API 产品化是明确的未来变现线。

---

## 3. 方案选型

四个候选（评估维度：实时上限 / 迁移成本 / 运行成本 / 与现有资产兼容 / 风险）：

| 方案 | 实时上限 | 成本 | 结论 |
|------|---------|------|------|
| A. 留 GH Pages + 运行时数据 API | 分钟级（轮询） | $0 | **有效但留单点**：实时性修复了，R4（Actions 计费单点）仍在——部署与日更管线仍全押 GitHub |
| **B. CF Pages（shell）+ data-gateway Worker（R2/KV + Cron）** | 秒级轮询 / 分钟级面板 / 可选 SSE | **$0（免费档内）** | **推荐**。部署 CI 换成 Cloudflare 自建 git 集成（与 GH Actions 计费解耦）；数据平面统一到边缘；复用既有 CF 账号与 prices Worker 模式；`pnpm build` 原样可跑（顺带消灭 `npx next build` 不触发 prebuild 的坑） |
| C. 全面 SSR 迁移（Vercel 或 OpenNext-on-CF） | 秒级 + 服务端渲染 | Vercel Hobby **禁商用**（条款风险）+ 大重构 | 否决：1,421 SSG + basePath + Turbopack barrel 教训全是静态导出特化；SSR 换来的能力（按需渲染）用"客户端渲染 + Worker 数据"同样可得 |
| D. 自托管 VPS | 无上限 | $-$$ + 运维 | 否决：单机可用性反而更低，运维负担与"无遗留后台进程"纪律冲突 |

**B 的本质**：不换框架、不换渲染模式、不重写页面——只把**数据平面**（panels + 滚动窗流）从
构建产物里抽出来放到边缘，把**部署平面**从 GH Actions 换成 CF Pages git 集成。展示层代码的
改动收敛为一个 `usePanel()` hook。

### 3.1 与反泄漏纪律的语义对齐（本方案的一个额外收益）

**冻结面板继续构建期内嵌 bundle（15 个）**——不可变性物理化：冻结数字 literally 烧进工件，
任何运行时都改不了它；**日更/节奏面板改运行时拉取（12+3 个）**——新鲜度与部署解耦。
架构分层与数据纪律同构，这是小隐寺（全部动态、来源不透明）在结构上学不去的。

---

## 4. 目标架构（双平面）

```
┌────────────────────────── GitHub 仓库 ──────────────────────────┐
│  代码 push ──► Cloudflare Pages CI ──► next build ──► 静态 shell │
│  （冻结 15 面板 + 兜底快照内嵌；1,421 个股页 SSG 不变）           │
│                                                                  │
│  日更 Python 管线（GH Actions cron 暂留，P5 可迁移）              │
│    fetch → export_terminal_data → PUT /admin/panels/{name} ──┐   │
└───────────────────────────────────────────────────────────────┘  │
                                                    │ Bearer token  ▼
读者浏览器                                     data-gateway Worker（新）
  │ ① 静态 shell（Pages）                     ├─ GET /api/v1/panels/:name   ← R2
  │ ② usePanel() 60s 轮询 ───────────────────►├─ GET /api/v1/streams/:kind  ← R2
  │ ③ prices 60s 轮询（现有 worker 不动）─────►├─ GET /api/prices/us|cn（现状）
  └──────────────────────────────────────────►└─ GET /api/v1/health（合并 data_health）
                                                   ▲
                              Cron Triggers（免费档）：EDGAR EFTS 5min（盘中）/
                              Reddit RSS 30min / house.gov 1d → 解析 → 写 R2 streams
```

### 4.1 data-gateway Worker 端点清单

| 端点 | 数据 | 新鲜度 | 缓存 |
|------|------|--------|------|
| `GET /api/v1/panels/:panel` | 日更面板 JSON（与现静态 API 同 schema） | 随 PUT 即时 | `max-age=60, swr=300` + 内容哈希 ETag |
| `GET /api/v1/streams/{filings\|form4\|stakes\|ipo\|reddit\|news}` | 滚动窗口流（分钟级） | 1-5min | `max-age=30` |
| `PUT /admin/panels/:panel` | 管线上传（Bearer secret） | — | 写 R2 + 清边缘缓存 |
| `GET /api/v1/health` | 线上数据健康（data_health 实时化） | 5min | `max-age=300` |

存储：**R2**（免费档 10GB / 每月 1M 写 / 10M 读，当前面板总量几 MB 绰绰有余；写配额远宽于 KV
的 1K 写/天）。CORS 读 `*`（公共数据不变）；写仅 token。prices Worker 保持独立（热路径语义
不同），网关是新 Worker（`workers/data-gateway/`），复用现有 wrangler 账号与 secret 管理模式。

### 4.2 前端唯一实质改动：`usePanel(name)`

- SWR 风格：`revalidateOnFocus` + 60s 轮询；**初始值 = 构建期内嵌快照**（渐进增强：预渲染
  HTML 含数据 → 水合后升级为最新值）。
- **降级契约**：Worker 不可达/5xx → 渲染内嵌快照 + 诚实 `as_of` 徽章（"构建时快照"）。
  站点**永不劣化到今天的行为之下**——worker 挂了 = 现状，worker 活着 = 实时。
- 冻结面板不走 hook（继续静态 import）——语义即边界。
- 契约测试拆两层：导出层 shape 测试不变（测 PUT 载荷）；新增 hook 降级测试（mock 断网）。

### 4.3 新鲜度分级（达成后）

| 层级 | 新鲜度 | 载体 | 覆盖 |
|------|--------|------|------|
| 秒级 | 30-60s | prices Worker（现有）+ 轮询 | US（Tiingo 免费档 15min 延迟，诚实标注）/ CN（新浪实时） |
| 分钟级 | 1-5min | gateway Cron + streams | 8-K 事件流、Form4 内部人流、13D/13G 举牌流、IPO 流 |
| 小时级 | 30-60min | gateway Cron | Reddit 提及榜、新闻聚合 |
| 日级 | T+1 | Python 管线 → PUT | themes/market_context/taco/cot/macro_drivers 等 12 面 |
| 季度 | 源节奏 | 同上 | 13F 调仓（45 天申报滞后，诚实披露） |
| 冻结 | 永不 | 构建期内嵌 | 15 面（反泄漏，E3 是唯一合法前进） |

**礼貌账**（纪律不松）：EDGAR EFTS 盘中 1 req/5min ≈ 78 req/交易日（SEC fair access 限 10/s，
余量四个数量级；≥2s 间距平凡满足）；Reddit RSS 3 feed/30min；house.gov FD.zip 1 req/日。
全部低于现行日更管线的请求量级。EDGAR 对数据中心 IP 的容忍度是已知风险（见 §7）。

---

## 5. 迁移阶梯（每步独立可交付、可回退）

| 阶段 | 内容 | 验收标准 |
|------|------|---------|
| **P0** | 修 GH Actions 计费（业主动作）；或授权本地 runner 兜底（Windows 计划任务跑 `uv run` 管线 + PUT） | 日更链路恢复任一路径 |
| **P1** | data-gateway Worker + R2 + `PUT /admin/panels`；exporter 双写（git commit 照旧 + PUT） | PUT 后 60s 内 GET 到新 `as_of`；无 token 401；R2 用量仪表在免费档 |
| **P2** | 前端逐面板切 `usePanel`（先 1 个试点面板如 market_context → 12 日更面全切；冻结 15 面不动） | 屏蔽 Worker URL 页面仍完整渲染快照；恢复后自动新鲜；契约测试全绿 |
| **P3** | 宿主切换：CF Pages 并行部署（同 `output:"export"` 产物）→ 全站 1,480 页校验 → 切主；GH Pages 保留重定向期 | **暂停全部 GH workflows 后，代码 push 仍能上线**（R4 解耦实证）；basePath 移除 |
| **P4** | 分钟级 ingestion Crons 上线：/events /insider /stakes /ipo 从"日更"升"分钟级流"；data-health 增实时源健康 | EDGAR 新 filing → 面板可见 ≤10min；礼貌账进 data-health 面板 |
| **P5** | **停止日更 JSON git 提交**（R5 冲突类问题根除；仓库瘦身）；可选：日更管线去 Actions 化（本地任务 + R2 私有桶做 parquet 缓存）；可选：SSE 新闻流（Durable Objects）；可选：D1 搜索/实体库 | 日更面不再产生 commit；`git log` 无日更噪声 |

P1-P2 交付后"数据实时"即达成（不依赖 P3）；P3 解决的是部署单点与宿主能力天花板；P4-P5 是
锦上添花与工程卫生。**若业主希望最小改动**：只做 P1-P2，宿主留 GH Pages，实时性问题已解。

---

## 6. 与 feature roadmap（08-21）的耦合：17 路由差距复核

以 2026-08-22 实探数据更新对齐矩阵（仅列**有变化或需行动**的行；完整版见 08-21 roadmap）：

| 路由 | 小隐寺现状 | Aionis 现状 | 行动（依赖本基建？） |
|------|-----------|------------|---------------------|
| /events 8-K 流 | **全市场实时流**（08-22 浏览器复核订正，原"空壳"系 SSR 首帧误判：波音/微盘股全谱、分钟级、三处 EDGAR 直链） | ✅ 23 事件/5 发行人 | P4 升分钟级流 + **扩发行人广度是主攻方向**（差距巨大，非"先发优势"） |
| /quarterly /annual | /quarterly 真空（0 份）；**/annual 实为 102 份实时流**（08-22 订正） | 未建 | /quarterly 仍是最便宜填壳（EFTS form-level，form8k/ipo 模式已验证）；/annual 竞品已在跑 |
| /companies | **0 家空壳** | ✅ 1,421 冻结宇宙 A-Z | **领先**；无需追 |
| /executives 高管变动 | 60 条（8-K 衍生） | 未建 | **近零成本**：现有 form8k 解析管线加 Item 5.02 分支即可（不依赖） |
| /news 7×24 流 | SSE 长连接 | 未建（GDELT 月聚合已有） | 依赖 P4（cron 聚合 GDELT/RSS → 滚动窗）；SSE 属 P5 可选 |
| /congress 政客交易 | 34,307 笔**交易级** | 874 份**申报流级** + 党派 join | 交易级 = PTR PDF 解析；**salvage 分支 `agent/politician` 已有 813 笔/42 议员解析器**（业主门已记录"后议"）——建议解封评估 |
| /insider 内部人 | 4,586 笔/24h 全市场 | 5 issuer / 2016+ | 广度差距最大项：按市值分层渐进扩 issuer（礼貌约束下是大工程，P4 的流式形态是前置） |
| /stakes 举牌 | 13D 549 + 13G 3,842 + 状态机 | 13D top60 窗口 + 历史封闭集 | 加 13G 流与 4 状态分类（P4 受益） |
| /institutions 机构目录 | 8,741 家分页 | 40 位明星 + 分类目录 | **建议不追全量**：8.7K 无增值叙事；注册表按 editorial 节奏扩（40→100 量级），全量目录等真有消费者再说（那是 treadmill） |
| /stock/{ticker} | 评分卡+机构持有者+政客交易 join | 模型读数+佐证计数+live 价+溯源 | 差距=两个 join（form13f/politician_trades 按 ticker 聚合，数据已有，纯展示层） |
| /api-docs | Scalar 动态 OpenAPI（端点未公开） | 静态 OpenAPI + 28 文件 panels API | P1 后静态 API 升级为**真活数据 API**（license 标注齐全 = 它的 opaque 第三方做不到） |
| 势力阵营关系图谱 | **未上线** | P3 规划（血缘图谱） | 开放赛道；D1（免费档 5M 行读/日）是天然的实体-关系存储，P5 可选项 |

**填壳优先序（成本/价值排序，建议；前两项 M/N 已有半成品在 worktree——
`tasks/active/TASK-P2-M-news-feed.md`、`TASK-P2-N-financial-stream.md`，续作按其接手协议，勿重复起线）**：
1. /quarterly + /annual（一个 EFTS 端点模式，两天级）— **N 半成品在 Aionis-n worktree**
2. /executives（现有管线加分支）— 无人在做，可新起
3. /stock 页两个 join（数据已在库）
4. /news（依赖 P4）— **M 半成品在 Aionis-m worktree（news_feed_fetch.py + 7-gate 文档已有）**
5. /congress 交易级（解封 salvage 分支评估）
6. /stakes 13G + /insider 广度（渐进）
7. **不追**：卫星 TACO（采购商业数据，违反 license 纪律与成本纪律）、实时 US 行情（付费）、
   8.7K 全量机构目录（无叙事价值）。

---

## 7. 风险与缓解

| 风险 | 缓解 |
|------|------|
| Worker 不可达 → 站点退化 | 内嵌快照兜底（降级契约 §4.2）：最坏 = 现状，永不更差 |
| EDGAR 拒数据中心 IP（CF 出口） | 降级路径：EDGAR 抓取留 GH Actions/本地 runner，Worker 只做服务端（P4 分两步走：先服务后抓取） |
| 运行时拉取伤首屏/SEO | 冻结面/目录壳仍预渲染含数据；日更面预渲染含快照（渐进增强）；个人研究终端 SEO 非目标 |
| CF 免费档配额 | 当前流量下余量 2-3 个数量级；配额仪表 + `data-health` 加配额水位；真超限时再谈付费（$5/月级） |
| 双 CI（CF Pages + GH Actions）复杂度 | 职责清晰分离：Pages 只管 shell 构建，Actions 只管数据管线；P5 后 Actions 可整体退役 |
| 日更管线对 GH Actions 的残留依赖 | P5 可选迁移路径已写明（本地 runner + R2 私有桶缓存；parquet 缓存桶必须私有——gitignored 数据的同等保护） |
| 与并发 session 的 lane 冲突 | 本方案全为新增工件（workers/data-gateway/、web hook），不碰 export_terminal_data 主路径（P1 只加一个可选上传步骤） |

---

## 8. 战略层：发展方向决策（深度探索结论)

1. **竞争定位一句话**：小隐寺卖"数据速度"（采购源 + SSE + 全市场广度）；Aionis 的护城河是
   "**每个数字带出生证明**"（PIT/冻结账本/license 标注/诚实 null + US/CN 双区域）。速度可以
   用边缘架构追平（本方案），**认识论完整性它结构上追不了**（第三方非公开源 = 无法溯源）。
2. **它的空白就是我们的路线图**（08-22 复核修订）：真实空白 = /quarterly、/companies、
   势力阵营、/stock 机构持有者四处；Aionis 在 /companies 领先，/events 则相反（对方全市场
   实时流 vs 我方 5 发行人）——填空白、追广度，两条腿；
3. **E3 forward-live 的战略权重上升**：小隐寺没有模型、没有可证伪主张。E3（append-only 前向
   账本）上线后，Aionis 成为唯一"模型读数可实时追踪、且不可回改"的终端——这是数据聚合类
   产品无法复制的差异化，比任何单页面 parity 都值钱。仍守业主 GO 门，不擅自启动。
4. **仓库卫生红利**：P5 停止日更 JSON 提交后，"rebase JSON 全冲突"这一类并发事故（handoff
   多轮记录）从结构上消失；`git log` 回归纯代码叙事。
5. **不做的清单同样重要**（防 treadmill）：不追付费行情/卫星数据/全量目录；不上 SSR 重构；
   不为速度牺牲礼貌纪律与 display-only 边界。

---

## 9. 业主决策清单

| # | 决策 | 建议 |
|---|------|------|
| D1 | GO P1-P2（gateway + 运行时面板）？ | **建议 GO**——display lane，零研究面影响，实时性即修复 |
| D2 | 宿主迁 CF Pages（P3）？ | 建议 GO（摆脱 Actions 计费单点）；若求最小改动可暂缓，实时性不依赖此项 |
| D3 | GH Actions 计费修复（P0，仍需）或授权本地 runner 兜底 | 二选一或双轨 |
| D4 | /congress 交易级：解封 `agent/politician` salvage 分支评估？ | 建议解封评估（813 笔解析器已存在） |
| D5 | E3 forward-live GO？ | 独立门，建议尽早排期（战略权重见 §8.3） |
| D6 | 自定义域名？ | 可选（CF Pages 免费绑定；与 GH Pages 并存期不影响） |

## 10. 同日晚间补充：免费方案全景矩阵——适配任意仓库可见性（业主命题"再研究其他合适且免费的方案"）

> 触发：08-22 计费停摆确诊（账户级，run `32514609482` 官方注解；仓库实核 PRIVATE）+
> 业主指令暂停 deploy/refresh 两 workflow 后重新研究。本节所有配额/政策均为 2026-08-22
> 官方文档 + 社区实证双源核实（来源清单见 §10.6）。

### 10.1 三条已核实的载重事实（其中一条修正 §9）

1. **【修正】账单封锁是账户级的，连公开仓库也挡。** 社区实证：免费层 + 公开仓库用户同样
   报 "The job was not started because recent account payments have failed…"，根因是账户里
   有失效付款方式或隐性 billing lock。⇒ **"转 Public 免修账单"不成立**；修 Billing 是
   一切方案的前置。转 Public 的价值（Actions 无限免费分钟 + Pages 免费）只在计费健康后兑现。
2. **Cloudflare 静态资产请求免费且无上限（官方文档，free/paid 皆然）**——Workers 与 Pages
   的静态资产请求不计入任何配额。⇒ shell 托管的流量成本恒为零，与仓库可见性无关
   （`wrangler` 部署甚至不需要仓库访问权）。
3. **self-hosted runner 不消耗计费分钟**（官方计费文档），spending-limit 型停摆下历史上
   仍可运行；但 2025-12 官宣 2026-03 起 $0.002/min 平台费（社区反弹后**延期中**，状态待跟）。
   付款失败型账户锁下行为未证实。⇒ 可用但带政策风险，不作唯一依赖。

**停摆根因二分法**（业主在 Billing & plans 一眼可辨，解法不同）：
- **A. spending limit 触顶**（用量超免费分钟 + $0 限额）：解法 = 转公开（分钟无限）/ self-hosted
  （0 分钟）/ 提额 / 等月初重置，四选一；
- **B. 付款方式失败/账户锁**：解法只有修卡/清锁——此前任何架构调整都不生效。
- 旁证假设待业主确认：私有仓库 + Pages 一直在工作 ⇒ 账户是 Pro，或仓库近期才转私有
  （若是后者，转私有那一刻就是停摆诱因：Actions 从免费变计量，叠加多 agent 高频 push 的
  deploy 构建 + 日更管线，月度分钟耗尽）。

### 10.2 免费方案全景矩阵（三平面 × 可见性免疫性）

**Shell 托管平面**

| 平台 | 免费额度 | 私有仓库 | 商用 | 判定 |
|------|---------|:---:|:---:|------|
| CF Worker + Static Assets | 静态请求**无限免费**；构建不限 | ✅（wrangler 直传，无需仓库权） | ✅ | **通用首选**——可见性/CI/账本三重解耦 |
| CF Pages（git 集成） | 500 构建/月（账户级）、单构建 ≤20min、2 万文件、带宽无限 | ✅（官方支持私有仓库） | ✅ | 便利层（push 自动构建）；我方构建 ~2-5min、~1,500 文件，余量充足 |
| GitHub Pages | 公开仓库免费；Free 计划私有仓库**不可用** | ⚠️ 需 Pro | ✅ | 仅场景 A（公开） |
| Netlify Free | 300 构建 min/月、100GB 带宽、硬上限无意外账单 | ✅ | ✅（官方确认，仅禁转售） | 备胎（比 CF 少生态协同，构建额度更紧） |
| Vercel Hobby | 100GB 带宽 | ✅ | **❌ 禁商用** | 否决不变 |
| Deno Deploy Free | 100 万请求/**月**（静态也计数）、100GB 出站、50ms CPU | ✅ | ✅ | 备胎（无静态免费 carve-out，仅作 gateway 备选） |

**CI / 构建平面**

| 方式 | 免费额度 | 可见性 | 判定 |
|------|---------|--------|------|
| **本地 `next build` + `wrangler deploy`** | 无限（自己机器） | 免疫 | **保底路径**：部署与 CI、仓库、账单全部解耦；代价 = 依赖开发机在线 |
| CF Pages git CI | 500 构建/月 | 免疫 | 便利层（零 CI 维护） |
| GH Actions 托管 | 公开=无限；私有=Free 2,000 / Pro 3,000 min/月 | 分化 | 现状问题源头；仅场景 A 保留 |
| GH self-hosted runner（本机） | 0 计费分钟 | 免疫* | *spending-limit 型停摆下可用；2026-03 平台费延期中，政策风险 |
| Netlify CI | 300 min/月 | 免疫 | 备胎 |

**数据平面（runtime API）**

| 平台 | 免费额度 | 判定 |
|------|---------|------|
| CF Worker + R2/KV/Cron | 10 万请求/日（静态走 assets 不计）、R2 10GB/月写 100 万次、Cron 免费 | **沿用 §4 设计**，已验证 |
| Deno Deploy | 100 万请求/月、KV 1GiB | gateway 备胎（JS 同构可迁） |
| Oracle Always Free（ARM A1） | 2 OCPU/12GB/200GB 盘，真·永久免费（**08-18 起执行新减半配额**） | 全栈兜底位：可跑 Python 管线 + cron + Caddy 自托管一切；代价=注册门槛/容量/运维 |

**Python 日更管线 runner（四个可互换，皆免费）**
1. **本地 Windows 计划任务/手动脚本**（保底，PC 在线为前提）
2. **self-hosted runner**（复用现有 workflow YAML，体验最优；政策风险见上）
3. **Oracle ARM VM**（去 PC 依赖的云端常驻位；刚减配但 12GB 跑 pandas 绰绰有余）
4. **GH Actions 托管**（仅当仓库公开且计费健康——回到现状最优）

### 10.3 通用推荐栈（对"私有还是公开"完全免疫）

```
部署：开发机 next build → wrangler deploy（CF Worker+静态资产）   ← 可见性/CI/账单三解耦
      （可选便利层：CF Pages git 集成自动构建，500/月）
数据：data-gateway Worker + R2 + Cron（§4 不变）                 ← 实时性修复的主体
管线：本地任务(保底) ⇄ self-hosted runner(体验) ⇄ Oracle VM(常驻)  ← 四 runner 可互换
研究面：完全不动（冻结面板继续构建期内嵌，§3.1 语义不变）
```

要点：
- **`wrangler` 直部让"部署"不再依赖任何 CI**——GH Actions 从基础设施降级为可选便利。
  这是与 §5 阶梯 P3 的差异：P3 用 CF Pages git CI 替换 Actions；本节补充了更彻底的
  "零 CI"路径（本地直部），两者可叠加（Pages 自动 + 本地兜底）。
- 场景化最优组合：**公开仓库** = GH Pages+Actions（现状即最优，$0 无限）+ CF gateway；
  **私有仓库（本仓现状）** = CF 托管 shell + gateway + 本地/self-hosted/Oracle runner；
  **极端去依赖** = Oracle VM 全自托管（灾备位，运维负担最大，不推荐为正选）。
- Netlify/Deno 为双备胎，不进正选（CF 生态协同 + 静态请求免费 carve-out 无可替代）。

### 10.4 对 §9 决策清单的修订

- **新增 D0（一切之前）**：Billing & plans 修付款/清锁 + 辨根因（A 触顶 vs B 付款失败）。
  若为 B：修卡即全解，随后再选长期栈；若为 A：通用栈（10.3）直接绕开计量问题。
- **D3 重述**：可见性决策与成本决策**解耦**——通用栈对两种可见性同价（$0）。转 Public 的
  真正权衡回归其本义（代码/方法论公开意愿 + 项目"可证伪/公开账本"身份契合度，前置一次
  历史 secret 扫描），而不再是省钱开关。
- D1/D2/D4-D6 不变。

### 10.5 本节结论一句话

**存在一个对仓库可见性、CI 平台、GitHub 账单状态全部免疫的免费栈**：本地构建 + wrangler
直部 CF（静态请求无限免费）+ data-gateway（R2/Cron）+ 可互换的管线 runner。GitHub 的账单
问题从"基础设施故障"降级为"便利性选项"——修不修、何时修，都不再阻塞任何事。

### 10.6 来源（2026-08-22 核实）

- CF 静态资产免费无限：[Workers Pricing](https://developers.cloudflare.com/workers/platform/pricing/) ·
  [Static Assets Billing](https://developers.cloudflare.com/workers/static-assets/billing-and-limitations/) ·
  [Pages Functions Pricing](https://developers.cloudflare.com/pages/functions/pricing/)
- CF Pages 限额/私有仓库：[Pages Limits](https://developers.cloudflare.com/pages/platform/limits/) ·
  [Pages Pricing](https://pages.cloudflare.com/)
- self-hosted 0 计费分钟：[GitHub Actions billing](https://docs.github.com/billing/managing-billing-for-github-actions/about-billing-for-github-actions)；
  平台费官宣与延期：[changelog](https://github.blog/changelog/2025-12-16-coming-soon-simpler-pricing-and-a-better-experience-for-github-actions/) ·
  [community #182186](https://github.com/orgs/community/discussions/182186)
- 账户级锁连公开仓库也挡：[community #165506](https://github.com/orgs/community/discussions/165506) ·
  [#162032](https://github.com/orgs/community/discussions/162032) ·
  [#184077](https://github.com/orgs/community/discussions/184077) ·
  [#182634](https://github.org/orgs/community/discussions/182634)
- Netlify 免费档商用许可：[pricing](https://www.netlify.com/pricing/) ·
  [官方论坛](https://answers.netlify.com/t/can-we-use-netlify-free-plan-for-commercial-purposes/41545)
- Deno Deploy 免费档：[pricing](https://deno.com/deploy/pricing)
- Oracle Always Free 减配（2026-08-18 生效）：[oracle.com/cloud/free](https://www.oracle.com/cloud/free/) ·
  [terminalbytes](https://terminalbytes.com/oracle-cloud-free-tier-changes-2026/)

### 10.7 同日追加：Vercel 专论（业主问"能不能参考小隐寺用 Vercel"）

**结论：能用，且是复刻小隐寺形态最平滑的宿主路径；唯一的根本性分岔是商用意图，其余约束
（cron、配额）都有免费解法。** 定位：Vercel 替换的是本方案的 **shell 宿主**（§5 P3 的
替代选项），**数据平面（gateway + R2 + 抓取 cron）在任何宿主下都不变**——Vercel serverless
无持久存储，其自家 Storage 产品按用量计费，所以数据层照样外置 CF R2。

**Hobby 档核实数字**（vercel.com/pricing 直抓，2026-08-22）：

| 项 | Hobby（$0） | 判读 |
|---|---|---|
| 商用 | ❌ FAQ 原文 "for personal, non-commercial use" | **唯一根本性约束**（见裁决） |
| Fast Data Transfer | 100 GB/月 | 当前流量级远够；CF 静态则无限 |
| Edge Requests / Function Invocations | 各 100 万/月 | 远够 |
| **Fluid Active CPU** | **4 小时/月** | SSR/ISR 动态渲染的真实天花板（静态资产不占） |
| ISR Reads / Writes | 100 万 / 20 万/月 | 够 |
| Image Optimization | 5K transforms/月 | 小隐寺式 OG/裁图需节制或保持 unoptimized |
| 超额政策 | **硬上限，不可加购**（无意外账单，超了停服） | 与 Netlify 同款安全模型 |
| Cron Jobs | **2 个/账户、仅每日精度**（docs 既定；可延迟 ~15min；Pro=40 个/分钟级）* | 分钟级抓取在 Vercel 免费档**不可能**——抓取留 CF |

*本行来自 Vercel docs 训练知识（定价页未列）；WebSearch 当时限流未能二次 live 验证，实施前核对
vercel.com/docs/cron-jobs/limits。

**三阶段路径（V2 才是真正的"小隐寺形态"）**：
- **V0（零改动，半天）**：静态导出产物原样上 Vercel（CLI `vercel deploy --prod` 或 git 集成，
  Hobby 支持个人私有仓库）；去 `basePath:"/Aionis"` 用根路径。立即恢复上线能力（与 GH 账单
  解耦）——效果等同 wrangler 直部 CF，两者可并行验证后择一。
- **V1（实时化）**：gateway + `usePanel()`——与 CF 栈完全同构，宿主无关。
- **V2（形态复刻，可选渐进）**：去掉 `output:"export"`，逐路由开 ISR/RSC（1,421 个股页转
  ISR 或按需渲染；目录页服务端分页）；数据落 R2 后由 **CF Cron ping Vercel revalidate
  端点**触发 ISR 刷新（on-demand revalidation，函数调用量极小）。**这是 Vercel 相对 CF 的
  真优势**：CF 走 SSR 需 OpenNext 适配层，Vercel 是 Next.js 原生主场。

**对 小隐寺 本身的诚实推断**：盘中实时 TACO + 7×24 SSE 新闻流 + 卫星数据管线，与 Hobby 的
4 CPU 小时/月 + 2×每日 cron 不匹配——它几乎肯定在 Pro（$20/月）或自有后端混合。"参考小隐寺"
应参考其**形态**（ISR/动态目录/OG 图），不必假设其宿主账单是 $0。

**裁决（决策轴 = 商用意图，一条）**：
- **可预见未来无商业变现**（个人研究终端维持免费公开）→ Vercel Hobby 合规，
  **推荐混合栈：Vercel（shell + 渐进 SSR/ISR）+ CF（gateway + R2 + 抓取 cron）**，$0；
- **有变现意图**（终局形态分析 §2 的 API 产品化/导流路线）→ 要么接受 Pro $20/月
  （1TB 带宽 + 40 cron 分钟级），要么回 CF 栈（$0 恒定）；
- **关键性质：先 Vercel 后决不是单向门**——V0/V1 两阶段平台无关（静态导出 + gateway），
  商用化那天迁回 CF 的成本仍然极低。可以今天就上 Vercel，把分岔决策推迟到真有收入动机那天。

**对 D2 的修订**：宿主决策从二选一变三选——GH Pages（公开仓库时）/ CF Pages 或 Workers
（私有+免疫优先）/ **Vercel（形态优先，商用分岔后置）**。

---

## 11. 同日再补充：极简 $0 阶梯（业主定帧"只求部署 + 自动爬取更新，日更可接受"）

> 定帧变化：需求从"全站实时架构"收敛为"**部署在线 + 数据自动更新，$0**"。§4-§5 的双平面
> 架构降级为**可选升级路线**，不再是前置。本节方案不依赖 D1/D2 任何决策，可独立先行。

### 11.1 关键机制解锁（为什么可以这么便宜）

1. **GitHub Pages 有两种发布模式**：现在的 `deploy-pages.yml` 走 "GitHub Actions" 模式
   （吃计费分钟，账单锁死即停）；但 Pages 设置里可切回经典的 **"Deploy from a branch"** 模式
   ——`git push` 一个 `gh-pages` 分支即发布，**完全不经过 Actions，0 分钟消耗**。切换是
   仓库 Settings 里的一个单选钮（业主动作 ~1 分钟）。唯一未知数：账户级账单锁是否连
   Pages 服务本身也拦（社区报告主要针对 Actions）——**5 分钟实测即知**；若被拦，
   fallback 就是下面第 2 条。
2. **`wrangler pages deploy out`（CF Pages 直传）与 GitHub 账单完全无关**：本地构建产物
   直接上传，不需要仓库访问权、不需要任何 CI、私有仓库无所谓、免费档静态请求无限
   （§10 已核实）。代价只是 URL 换成 `*.pages.dev`（可与旧 URL 并存过渡）。
3. **Windows 计划任务支持"错过补跑"**（StartWhenAvailable）：夜里定点任务在关机错过后的
   下一次开机会自动补跑——开发机每天开机的场景下，本地自动化比想象中可靠。
4. **爬取命令序列已经存在**：`refresh-terminal-data.yml` 的 YAML 就是完整配方
   （fetch 各源 → 价格增量 → universe/regime 自填充 → materialize → 导出 → 契约闸门 →
   提交），且每条命令都在本地验证过——转写成一个本地脚本即可，零新逻辑。

### 11.2 三层阶梯（全部 $0，从上到下增量添加）

**阶梯 1：日更自动化（半天工作量，零新基建，零新账户）**
```
Windows 计划任务（每日 08:00 本地时间 + 错过补跑；另附桌面"立即更新"快捷方式）
  → scripts/update_and_deploy.sh（新，~100 行，YAML 的本地转写）
    1. uv run …（各 fetcher，礼貌纪律原样继承）
    2. uv run scripts/export_terminal_data.py（30 面板 JSON）
    3. cd web && pnpm build（本地 ~2-5 分钟）
    4a. git push gh-pages 分支（Pages branch 模式，保旧 URL）   ← 主路
    4b. 或 npx wrangler pages deploy out（CF 直传，免疫一切）     ← 兜底/并行
```
效果：**数据 T+0 日更 + 站点自动上线**，与 GitHub Actions 计费彻底无关。研究面冻结语义
不变（导出器原样）；日更 JSON 是否照旧 commit 进 git 可选（建议保留，审计连续性）。

**阶梯 2：分钟级爬取（+1 个免费资源，服务 EDGAR 族面板）**
- CF Worker Cron（免费档）每 5-30 分钟抓 EDGAR EFTS（8-K / Form4 / 13D/13G / IPO /
  congress house.gov 批量索引）+ Reddit RSS，规范化后写 R2，前端对应页面改 fetch。
- 这才是"实时爬取"的本体：**$0（10 万请求/日内）**，且只动 5-6 个流式面板，不动全站。
- 诚实上限：**爬取频率的天花板是源的节奏**——COT 周更、13F 季更（45 天申报窗）、FRED 宏观
  日更；任何基建都不能让 CFTC 提前发布。分钟级只对 EDGAR 族 + Reddit + 价格有意义。

**阶梯 3（可选）：去 PC 依赖**
- 同一脚本跑在 Oracle Always Free ARM VM（2 OCPU/12GB，云端常驻 cron）；或 D0 账单修复后
  回 GH Actions（公开仓库则无限）。阶梯 1 的脚本是平台无关的 bash，三处通用。

### 11.3 决策影响

D1（gateway）/D2（宿主）**全部解阻塞、可无限期推迟**——阶梯 1 不依赖它们。先跑起来，
真实流量与真实痛点出来后再决定要不要上 §4 双平面。成本表：三阶梯合计 **$0**（阶梯 3 的
Oracle 也免费，仅需注册门槛）。

---

## 12. 深度调研：去 PC 依赖的 $0 云端 runner（业主指令"去掉对 PC 开机的依赖"）

> 范围澄清：PC 依赖只存在于**重 Python 日更管线**（fetch→export→build，30-45 分钟/天）。
> §11 阶梯 2 的分钟级 EDGAR 抓取本来就设计在 CF Worker Cron 上（天然无 PC 依赖，随时可上）。
> 本节回答：哪块**免费云端算力**能接管这条管线。核实方式：官方文档直抓（2026-08-22；
> WebSearch 限流中，CF Containers 一项见注）。

### 12.1 已核实的三条关键事实

1. **Oracle 闲置回收的精确判据（官方文档原文）**：7 天窗口内，若 ①CPU p95 < 20%
   ②网络 < 20% ③内存 < 20%（A1 形状三条全中）→ 判定 idle 可回收。**反之任一条不满足即安全**。
   官方文档自己给出的免疫法：A1 上驻留一个占 >20% 内存（12GB × 20% ≈ **2.5GB**）的服务
   即永不判 idle。我们的天然优势：把分钟级 EDGAR cron 也放这台 VM 上跑，CPU/网络/内存
   三项都会周期性活跃——防回收与阶梯 2 合流，一份算力两用。
2. **GCP Cloud Run Jobs 免费档（官方定价页 + 官方算例）**：**240,000 vCPU 秒 + 450,000 GiB 秒/月**。
   按最坏情况算（2 vCPU / 1 GiB / 45min × 30 天）：162,000 vCPU-s + 81,000 GiB-s → **$0.00，
   余量 1.5-5 倍**。Jobs 按 container 整生命周期计费（礼貌 sleep 也计内存秒），但额度仍覆盖。
   注意两点：egress 仅 1GiB/月免费（我方是"拉入为主"，日推送 MB 级，够）；**镜像存储是 $0
   唯一漏洞**——Artifact Registry 免费 0.5GB，需 slim 多阶段镜像（pandas+pyarrow 压缩层
   ~200-300MB，可控）。Cloud Scheduler 免费 3 个 job（只需 1）。Secret Manager 免费 6 个
   secret 版本（4 个 API key 够用）。
3. **GitHub Codespaces 免费配额不受账单锁影响**（官方 billing 文档）：个人账户 120 核时/月
   （2 核基准）+ 15GB 存储；**"配额内使用不需要付款方式；仅配额耗尽后才要求有效付款方式"**
   ——即当前 GitHub 账单停摆状态下，Codespaces 免费配额**照常可用**。需求测算：2 核 ×
   45min × 22 天 = 33 核时/月 ≤ 120，余量 3.6 倍。

### 12.2 候选全景矩阵（按推荐序）

| # | 方案 | 形态 | 免费额度（核实值） | $0 可信度 | 关键代价/风险 | 管线改造 |
|---|------|------|-------------------|:---:|------|------|
| 1 | **Oracle Always Free ARM** ⭐正选 | 常驻 VM | 2 OCPU/12GB/200GB 盘（1500 OCPU-h+9000 GB-h/月）；出站 10TB/月 | 高 | 注册需卡（有时被拒）；A1 热门区容量紧张（重试脚本/换 AD 解决）；home region 限定；**闲置回收用 §12.1-1 判据免疫** | **零改造**（cron + git + uv，缓存落本地盘） |
| 2 | **GCP Cloud Run Jobs** ⭐次选 | Serverless 批处理 | 240k vCPU-s + 450k GiB-s/月（需求 162k/81k） | 高 | 需绑卡 + 预算告警护栏（防意外扣费）；镜像存储 0.5GB 免费需 slim 镜像纪律 | 缓存外置 R2（无本地盘；与 §4 gateway 设计合流） |
| 3 | **GitHub Codespaces + 外部 cron 编排**（即刻可用） | 按需容器 | 120 核时/月 + 15GB（需求 33 核时） | 中高 | 编排复杂（cron-job.org/CF Cron → GitHub API 建码 space → 跑脚本 → 停删）；非为 cron 设计；cleanup 不净会积占存储 | 缓存走 R2 或 codespace 持久卷 |
| 4 | GCP e2-micro VM | 常驻 VM | 0.25 核共享/1GB/30GB（always-free 老牌） | 高 | 1GB RAM 跑 pandas 紧（需 swap 兜底）；需卡 | 零改造 |
| 5 | GH Actions（D0 修复后） | CI | 私有 2-3k min/月；公开无限 | 条件解 | 就是现在坏的那个；账单修复是前置 | 零改造（现成 YAML） |
| 6 | Render 免费容器 + 自 ping + APScheduler | 常驻容器 | 512MB/750h 月 | 中低 | 512MB 紧张；盘临时（缓存须 R2）；保活 ping 灰色 | 需改造 |
| 7 | HF Space + ping | 常驻容器 | 2 vCPU/**16GB**（最肥） | 中 | 48h 无访问即睡（可 ping 续）；ToS 灰（非 demo 用途）；盘临时 | 需改造 |
| 8 | AWS Lambda + Step Functions 分片 | 函数 | 400k GB-s 永久免费 | 中 | Lambda 15min 上限 → 管线拆 3-4 段链式；工程量大 | 需大改 |
| 9 | CF Containers | 容器 | 按公告需 Workers Paid $5/月（官方页抓取被内容过滤拦，实施前复核） | 低 | 收费 → **排除** | — |
| 10 | Serv00 等社区免费主机 | BSD jail | ~3GB RAM | 低 | FreeBSD 无 pandas/pyarrow wheel → 源码编译地狱 | 不推荐 |

### 12.3 架构含义：runner 是可插槽，其余全部不动

§11 的脚本与部署目标**与 runner 解耦**：`update_and_deploy.sh` 在 Oracle/GCP VM（cron 调度）、
Cloud Run Jobs（容器 entrypoint）、Codespaces（startup 命令）上跑的是**同一份 bash**。切换
runner = 换调度器，管线零改动。推荐组合：

```
正选（稳）：Oracle ARM VM ── cron 每日 ──> update_and_deploy.sh ──> gh-pages 直推 / wrangler 直传
                                       └── cron 每 5-30min ──> EDGAR 分钟级抓取（兼防闲置回收）
次选（Oracle 注册受阻）：GCP Cloud Run Jobs + Scheduler（缓存改 R2，顺带完成 gateway 前置）
过渡（今天就跑）：Codespaces 编排；或先 PC 手动，正选就绪即切
```

### 12.4 对决策清单的最终影响

- **D3 实质作废**：去 PC 依赖不靠修 GitHub 账单——正选/次选都与 D0 无关。D0（修账单）
  只影响"要不要顺手恢复 Actions 这条便利线"。
- **新增 D7（runner 选型）**：Oracle（正选，一次性 ~1-2h 设置）/ Cloud Run（次选）/ Codespaces
  （过渡）三选。设置内容由我出（安装脚本 + cron 注册 + 防回收驻留服务 + 验证清单）。

---

*实探方法：22 页面逐页抓取（含 /manager/0001067983?tab=changes、/stock/NVDA、sitemap.xml），
2026-08-22；本仓现状由代码级勘察（next.config.ts / deploy-pages.yml / refresh-terminal-data.yml /
workers/prices / export_terminal_data.py / data_health.json）交叉验证。*
Vercel 配额：vercel.com/pricing 直抓 2026-08-22（cron 行除外，见 §10.7 注）。
