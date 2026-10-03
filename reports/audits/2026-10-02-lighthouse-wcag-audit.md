# Lighthouse + WCAG 审计与修复 — 轮 112（2026-10-02）

> 方法：Edge headless + Lighthouse（移动端默认口径）审计线上站 4 代表页 → 病根定位 →
> display lane 修复 → 本地 basePath-junction 伺服 A/B 复测 → 发布后线上复测。
> 本地 A/B：同 commit 两构建 × 各 2 跑；线上为单跑（网络噪声计入解读）。

## 基线（修复前，线上）

| 页面 | perf | a11y | best-practices | seo | 关键指标 |
|---|---|---|---|---|---|
| / （redirect→/dashboard） | 54 | 100* | 96 | 100 | LCP 5.8s / TBT 740ms |
| /atlas.html | 56 | **89** | 93 | 100 | TBT 4,820ms / DOM 7,162 / 主线程 7.2s |
| /dashboard.html | 61 | 100* | 96 | 100 | TBT 2,200ms |
| /market.html | 70 | 100 | 96 | 100 | LCP 2.4s / TBT 1,390ms |

*100 分页仍各带 1 条零权重 label-content-name-mismatch（见修复 3）。

## 发现与修复（severity 排序）

1. **[a11y-critical] aria-required-attr（atlas 全部滚动区）** — frost 滑条覆盖层带
   `role="scrollbar"` 却无 aria-valuenow（axe 硬失败）。修复：纯装饰化
   （aria-hidden + 去 role/tabIndex/aria-*）——原生滚动区本就是键盘/滚轮接口，
   伪造 JS 不追踪的 aria 值比隐藏装饰更糟；顺带消除每个滚动区的 tab 噪声。
2. **[a11y-high] color-contrast 4.36:1 < 4.5（浅色主题）** — `--muted-foreground`
   #6f6f6f 全透明度过 AA，但 `/80` alpha 小文本跌穿。修复：令牌 → **#555555**
   （全透明 7.2:1、/80 仍 ~4.6:1）；`--mute`/`--faint` #757575/#747474 → **#6f6f6f**
   （4.85:1）；10 处真实小文本 alpha 摘除（装饰性 fill/border 不动）。深色令牌零改动。
3. **[a11y-low] label-content-name-mismatch（trust-ribbon）** — aria-label 覆盖可见
   文本；拼入可见标签后 axe 仍要求包含全部徽章文本（PIT/embargo/H6/config）。
   终解：**去掉 aria-label，内容即无障碍名**（自维护，天然合规）。
4. **[perf-high] /atlas TBT 4.8s / DOM 7,162 / 主线程 7.2s** — 后三重下折叠区块
   （diagnostics/deciles/dataflow）挂 `.cv-auto`（content-visibility:auto +
   contain-intrinsic-size:auto 640px）。
   **A/B 实测（本地，各 2 跑）**：TBT 5.2~5.7s → 2.5~3.1s（**-45%**）、主线程
   7.9~8.8s → 5.0~5.5s（**-37%**）、SI 5.0~5.3 → 4.8~4.9。
   **视觉闭环（协议 §4）**：16,000px 全视口捕获，全部区块/表格/Sankey/散点/柱状
   渲染完整，零吞内容——轮 88/95 的隐藏子树病理是"捕获"伪影，与 paint-skipping
   不同类，本轮实测证实无复发。

## 修复后（线上复测，同日发布后）

| 页面 | perf | a11y | 变化 |
|---|---|---|---|
| /atlas.html | **60** | **100** | perf +4、a11y +11、TBT 4,820→**3,280ms（-32%）**、主线程 7.2→6.4s、LCP 3.5→3.3s |

## 查过不修（如实）

- **home LCP 5.8s**：`/` 是 redirect 壳→/dashboard（静态托管无法服务端跳转），
  跳转链路承担了 ~2.4s；hero h1 无 Reveal/opacity 门（原假设证伪）。根治=让 `/`
  成为真实落地页（产品决策，非缺陷修复），记 backlog。
- **深色主题单独成像失败**：Edge headless `--force-dark-mode` 无效（两次捕获字节
  相同）；但本轮深色令牌零改动，构造上无回归面。
- **3 条存量 eslint warning**（layout.tsx 冗余 disable/api-docs 未用 import/
  colorconv 未用 cn）：非本轮引入（行号均未触碰），留待专项清理。
- **cv-auto 工具类随 a11y 批次入库**（globals.css 同文件两改）：原子性小瑕疵，
  两笔提交同推送，语义边界在提交信息中已分明。

## 工件

- 基线 JSON：`runs/lh_{home,atlas.html,dashboard.html,market.html}.json`（gitignored）
- A/B：`runs/lhA_atlas_{1,2}.json`（基线）/ `runs/lhB_atlas_{1,2}.json`（cv）
- 全页捕获+主题目检：`reports/audits/2026-10-02-lighthouse-evidence/`（lhB_fullpage.png /
  r112_light.png / r112_dark.png——最后者为 force-dark 无效的同字节重复，留作方法注记）
- 线上复测：`runs/lhLIVE_atlas.json`

边界：display lane；0 ledger / 0 frozen / 0 prereg / 0 OOS。


## 轮 113 追加（2026-10-02）：cv 扩展实验——dashboard 前置 null、market 实测 null（均如实）

- **dashboard**：本地基线 TBT 仅 **220ms**（线上 2,200ms 是 redirect 链路+网络的
  放大，直连页本身健康）——无有意义天花板，未改动（null by precondition）。
- **market**：尾部宏区块（KoreaProxy→methodology）整段包裹 .cv-auto，同款
  A/B 双跑（本地）：TBT 1,500~1,710ms → **1,930~2,090ms（+~20%）**、主线程
  10.0~10.1s → 10.3~10.6s（持平）、SI 5.3~5.4 → 4.2、perf 分 41~43 → 42~43
  （不动）。**结论：market 的成本中心是 recharts 脚本执行（cv 不可及），
  containment 自身的布置/估值开销反而轻微加负**。改动已回滚，数据留档防止
  重蹈。与 atlas 的对照（其重头是 7k DOM 的布局/绘制，cv 收益 -45%）精确划出
  该技术的适用边界：**布局/绘制密集页有效，脚本密集页无效甚至微害**。

工件：`runs/lhA_{dashboard,market}_{1,2}.json` / `runs/lhB_market_{1,2}.json`
（gitignored）。边界：display lane；0 ledger / 0 frozen / 0 OOS。


## 轮 114（2026-10-02）：脚本侧追击——lazy-mount 四张下折 recharts 卡，TBT -42%（本地）/ -38%（线上中位）

轮 113 的 profile 解剖把"脚本成本"落到实体：**4.68s 集中在 react-dom 框架 chunk
的执行**（水合），recharts bundle 本体仅 0.31s 求值——content-visibility 管不到
水合，正解是**延迟挂载**。实施：`ui/lazy-mount.tsx`（IO 400px once-门控 +
minHeight 占位保 CLS）+ 四张图表卡（Drivers/Dollar/YieldCurve/MandateTension）
改 `next/dynamic(ssr:false)`；StagflationRead 无图保持 eager（内容优先）。

| 指标 | A（基线） | C（lazy） | Δ |
|---|---|---|---|
| 本地 TBT | 1,500~1,710ms | 900~910ms | **-42%** |
| 本地主线程 | 10.0~10.1s | 7.5~7.8s | **-24%** |
| 本地 perf | 41~43 | 50~51 | +8 |
| CLS | 0 | **0** | 占位高度守住 |
| 线上 TBT（中位 3 跑） | 1,390ms | 790~910ms | **-38%** |
| 线上 perf | 70 | 75~77（中位） | +5~7 |

协议 §4 闭环：16,000px 全视口捕获四卡全挂载、图表完整
（r114_market_fullpage.png）；零控制台错误（无水合失配）。**方法论注记**：
线上单跑 run1 的 perf 50/LCP 4.6s 是网络慢窗伪影（其 FCP 同步劣化至 3.3s；
run2/3 恢复 1.3~1.7s）——跨日线上对比必须多跑取中位，TBT 才是网络无关的
稳定指标；本地同 commit A/B 是设计上的裁决仪器。

工件：`runs/lhC_market_{1,2}.json`、`runs/lhLIVE_market{,_2,_3}.json`（gitignored）。

边界：display lane；0 ledger / 0 frozen / 0 OOS。


## 轮 115（2026-10-02）：LazyMount 扩展三页裁决——heatmap/dashboard 前置 null、atlas 天花板实测后按内容优先否决

- **heatmap**（手写 squarify 树图，US 492+CN 929 格）：本地 TBT 仅 **270~290ms**
  ——前置 null，未改动（8s 主线程是大块非阻塞离屏工作，TBT 才是体验指标）。
- **dashboard**：4 跑分布 200/270/330/**1,620**ms——1.6s 为**一次性离群**，归因
  **宿主并发**（当晚数据通道正在本机抓取/解析，测量窗撞其 CPU 突发）。方法注记：
  在跑通道的机器上做 Lighthouse 会引入此噪声；中位数报告+离群归因。
- **atlas 天花板实验**（测完即回滚）：三个下折区块 LazyMount（替换 cv）→
  TBT 中位 2,110~2,740→2,160~2,270ms（**仅 -10%**）、perf 34~35→40~41、主线程
  -17%。**裁决：否决**——atlas 区块是研究叙事/表格（本仓的内容本体），为 -10%
  把它们移出 SSR HTML 违反内容优先；cv（轮 112）保留为 atlas 的终态方案。
  数字留档：atlas 剩余 TBT 的大头在**上折区块+页面框架**的水合，非下折三区块。

### `/` 落地页决策简报

见 `reports/design/2026-10-02-root-landing-page-brief.md`（三选项含实测数据，
建议 B：`/` 直接渲染 dashboard 内容，LCP 预计 5.8→~3.4s，一个文件+canonical）。

工件：`runs/lhA_{heatmap,dashboard,atlas}_r115_*.json`、`runs/lhEXP_atlas_{1,2}.json`
（gitignored）。边界：display lane；0 ledger / 0 frozen / 0 OOS。


## 轮 116（2026-10-02）：水合构成消融（框架级=null）+ 选项 B 落地（/ 直渲，线上验证）

**消融份额表**（临时空内容页 + NEXT_PUBLIC_ABLATION env 门控，测毕全撤）：

| 层 | TBT | 说明 |
|---|---|---|
| 共享壳层（导航+⌘K+Provider 栈+BackToTop） | **230~310ms** | 全站地板 |
| ┼ ⌘K 面板消融（nopalette 构建） | 230~310ms | **份额≈0（噪声内）** |
| dashboard 内容（Overview 全量−壳层） | ≈0~80ms | 内容几乎免费 |
| heatmap 内容 | ≈0~50ms | 同 |
| atlas 内容（−壳层） | ~1,800~2,500ms | 唯一重页（已各自处置：cv 落地/LazyMount 内容优先否决） |

**裁决：共享组件级优化=null**——壳层地板就是 React+导航的真实成本，⌘K 懒挂载
无收益；~2s 残余是 atlas 专属而非"report/dashboard 类页面"通病（修正本轮前提）。

**选项 B 落地**（df0729f25）：壳层自 (dashboard) 组 layout 上提至根 layout（全部
路由含 404 获得导航），`/` 直渲 `<Overview/>`+canonical→dashboard.html，redirect
壳退役。**线上验证（含一次事故与更正，如实）**：df0729f25 的 `git add` 因陈旧 pathspec
整条原子失败，该提交只含组 layout 删除——**线上短暂（约 15 分钟）全站无导航且
/ 仍跳转**；cadd5122a 补齐后三路由（//market/404）导航探针全在墙、`/` hero h1
在墙、canonical 在墙。**更正一**：df0729f25 窗口内的"线上验证 410ms"极可能测的
是 Pages 重建延迟期的旧部署，不作为本轮证据。**更正二**：先前"本地双峰=python
http.server 目录 URL 伪影"的归因不成立——修复后部署上 `/` 与 /dashboard **双双
双峰**（860/3,020 vs 320/1,530ms），真实机制是 **TBT 对交付交错的测量敏感性**
（慢网窗脚本执行被网络等待摊薄→TBT 反低；快网窗任务叠峰→TBT 高）；与轮 114
"跨日线上必须多跑取中位"注记同源。结论维持：`/` ≡ /dashboard（同树同字节级
近同构），redirect 链路税结构性消除；perf 单跑波动 41~72 不作为判据。视觉闭环
（r116_root_live.png）有效。

**外部对照**：web.dev content-visibility 一手指南确证轮 112/113 边界结论（渲染
优化不跳过脚本/水合；`contain-intrinsic-size: auto <px>` 记忆策略=我们所用）；
Interop 2026 页 404（web.dev 文档重组期，如实注记）。搜索配额 2026-10-03 18:50
UTC 恢复（今日两次尝试均 429 如实记录）。

工件：`runs/lhABL_empty_*.json`、`runs/lhB_root_*.json`、`runs/lhCTRL_dash_now*.json`、
`runs/lhLIVE116_*.json`（gitignored）。边界：display lane；0 ledger/0 frozen/0 OOS。


## 轮 117（2026-10-02）：atlas 上折细剖（份额表）+ Speculation Rules 落地

**上折消融**（env 门控，测毕还原；基线=轮 116 构建 TBT 2,110/2,740ms）：

| 消融变体 | TBT | 份额推算 |
|---|---|---|
| −AtlasClaims | 1,410~1,620ms | claims ≈ 500~1,200ms |
| −AtlasDivergence | 970~1,280ms | **divergence ≈ 830~1,770ms（更大）** |

两区块均内容密集（18~20 表行+SVG）→ 内容优先约束下整块懒挂载不可行（轮 115
同裁决）。**手术式出路已识别但本轮不实施**：仅图表子块 dynamic ssr:false、表格
留 SSR（market 卡先例；divergence 的 BandPanel SVG 是干净边界）——估算可再省
~0.8~1.7s atlas TBT，留独立一轮从容做（轮 116 staging 事故教训：勿赶工）。

**Speculation Rules 落地**（f6357f665）：根 layout 内联规则块——`prerender:
where href_matches /Aionis/*, eagerness moderate`（hover~200ms/pointerdown，
Chrome 并发帽 2 FIFO+Save-Data/Preload-Off 自动禁用=构造性礼貌；外链模式永不
匹配；non-Chrome 视为惰性 JSON 忽略）。**Chrome 官方原文："静态多页站是理想
用例"**——正对 1500 页全页导航的本站。验证：三代表性页规则在墙+JSON 解析
合法+lighthouse 控制台 0 错误+a11y 100 不变；线上在墙（初次 0 读数=CDN 边缘
传播延迟，90 秒后 650,420 字节新版 grep=1，如实入册）。**如实注记**：
activationStart>0 的预渲染命中实测需脚本化 UI 轮，标记 pending 不宣称。

**外部对照补充**：developer.chrome.com 一手页确认 Speculation Rules 非 Baseline
（Chrome/Edge 121+）；无 CSP 阻碍（GitHub Pages 无 CSP 头）。搜索配额
2026-10-03 18:50 UTC 恢复（今日确认仍未到窗口）。

工件：`runs/lh117_{noclaims,nodiv}_{1,2}.json`、`runs/lh117_speca_sanity.json`
（gitignored）。边界：display lane；0 ledger / 0 frozen / 0 OOS。


## 轮 118（2026-10-02）：divergence 手术式拆分落地——TBT 中位 -21%（本地）/ -43%（线上 vs 轮 112）

执行轮 117 方案：SVG 面板（PanelFrame/BandPanel/EcePanel+几何常量）移入
`atlas-divergence-charts.tsx`，两处 `dynamic(ssr:false)` 共享一个异步 chunk，
minHeight 骨架占位保 CLS；纯数据 prep（prepRegion/REGIONS/fmtTpl）独立模块——
SSR 表格计算不拉 SVG 代码入首屏包。**PanelFrame 逐字拷贝**（首次凭记忆重写被
逐字 diff 抓出网格线型/刻度裁剪/x 定位三处偏差，构建前替换——图表字节稳定
纪律的又一次实战拦截）。

| 指标 | 基线（r117 构建） | 拆分后 | Δ |
|---|---|---|---|
| 本地 TBT | 2,110~2,740ms | 1,560~1,950ms | **中位 -21%** |
| 本地主线程 | 5.3~5.5s | 4.4~4.9s | -14% |
| CLS / a11y / console | 0 / 100 / 0 | **0 / 100 / 0** | 全保持 |
| 线上 TBT（3 跑） | 3,280（轮 112 基线） | **1,879 中位**（1,762~2,017） | **-43%** |

**诚实注记**：实际收益 ~0.5s 低于估算上限 0.8~1.7s——异步 chunk 仍在 trace 窗口
内执行；估算上限把整个 divergence 份额当成了可迁移量。§4 闭环：16,000px 全页
捕获两区块全渲染（r118_atlas_split.png）。atlas 累计（轮 112 起）：线上 TBT
4,820→1,879（**-61%**）、a11y 89→100。

工件：`runs/lh118_split_{1..4}.json`、`runs/lhLIVE118_atlas_{1,2,3}.json`。
边界：display lane；0 ledger / 0 frozen / 0 OOS。


## 轮 119（2026-10-02）：claims 手术式拆分落地——atlas 线上 TBT 中位 1,349ms，战役累计 -59%/-68%

轮 118 配方复制到 claims 区块：两 SVG 体（IC pivot 热图 66 月×3 序列、森林图）
**程序化逐行切片**入 `atlas-claims-charts.tsx`（零转录），两处 dynamic(ssr:false)
共享异步 chunk+骨架；isNum/fmt/tf 入共享 prep 模块（SSR 包裹器不拉 SVG 入首屏包）；
几何常量与 tokens 导入随图表走，主文件留 SYM_MAX/P_SERIES（halves 条消费）。

| 指标 | r118 终版 | claims 拆分后 | Δ |
|---|---|---|---|
| 本地 TBT（3 跑） | 1,910~1,950ms | **1,450~1,510ms** | **中位 -24%** |
| 本地主线程 | 4.5~4.7s | 4.1~4.3s | -7% |
| CLS / a11y / console | 0 / 100 / 0 | **0 / 100 / 0** | 全保持 |
| 线上 TBT（3 跑中位） | 1,879ms | **1,349ms** | **-28%** |

**§4 闭环改用 DOM 证据**（比截图更强）：水合后 DOM 含 **198 个 pivot 单元格
（66×3 精确吻合）**、SESOI 虚线带、9 桶图例、文献语境行、**零残留骨架**。
**atlas 战役终账（轮 112 起）**：线上 TBT 4,820 → **1,349ms（-72%）**、
a11y 89→100；本地 2,110~2,740 → 1,450~1,510。

搜索配额 10-03 18:50 UTC（本轮仍 12:50 UTC，未到窗口如实注记）；activationStart
实测仍 pending（脚本化 UI 轮）。

工件：`runs/lh119_claims_{1,2,3}.json`、`runs/lhLIVE119_atlas_{1,2,3}.json`、
`runs/r119_dom.html`。边界：display lane；0 ledger / 0 frozen / 0 OOS。


## 轮 120（2026-10-02）：其余页面残余水合普查——11 页筛选表入册；picks cv 实验 null 偏害回滚

**普查（本地单跑筛选，TBT 降序）**：

| 页 | TBT | DOM | 主线程 | 构成判读 |
|---|---|---|---|---|
| picks | **1,747ms** | 2,345 | 4.0s | 水合脚本 1.3s+布局 1.1s，无图表 |
| track | 1,082ms | 1,057 | **6.6s** | 脚本密集（疑重图表）|
| regime | 878ms | 825 | **6.7s** | 脚本密集（宏观卡 recharts）|
| confirmation | 874ms | 1,136 | 4.0s | 中等 |
| calibration | 759ms | 995 | 6.2s | 脚本密集 |
| model-health | 506ms | 941 | 3.3s | 健康缘 |
| shelf/power-floor/discipline/quarterly/evidence | 181~400ms | — | — | 健康（≈壳层地板）|

**picks cv 实验（下折尾部包裹，测毕回滚）**：TBT 1,840~2,190 vs 基线 1,747——
**null 偏害**（containment 记账＞布局节省；与 market 轮 113 同型）。边界再收敛：
**cv 的适用阈值约为万级 DOM 的布局密集页**（atlas 7,162 有效；picks 2,345 无效）。
picks 的真实杠杆=行级水合拆分（TrackRecord/浓度卡），但它们是数据内容——
内容优先约束下收益/张力比不佳，标记为"评估过不修"呈后续轮裁量。

**下一轮候选**：track/regime/calibration 三页（主线程 6.2~6.7s 脚本密集）的
图表构成解剖——若为 recharts 则 LazyMount 配方（market 轮 114 先例）。
搜索配额 10-03 18:50 UTC 未到窗口；activationStart pending。

工件：`runs/lh120_screen_*.json`、`runs/lh120_picks_cv_{1,2}.json`（gitignored）。
边界：display lane；0 ledger / 0 frozen / 0 OOS。


## 轮 121（2026-10-02）：/track、/regime 每 tab dynamic 拆分——两页 TBT 各 -11%（温和真实，天花板如实）

**机制发现**：两页为 Radix Tabs 多标签页——仅活动 tab 进 DOM，但全部 tab 视图的
模块图都打进首屏。**实施**：默认 tab（calibration/market）保持静态导入（SSR 内容
零损失——非默认 tab 本无 SSR 输出）；track 其余 5 视图+regime 其余 3 视图改
`next/dynamic` 每 tab chunk。

| 页 | 基线（单跑） | 拆分后（双跑） | 线上中位（3 跑） |
|---|---|---|---|
| track | 1,082ms | 950~970ms（-11%） | **858ms** |
| regime | 878ms | 740~810ms（-11%） | **753ms** |

**诚实天花板注记**：transfer（~4.4MB）与主线程（6.5~6.7s）**不变**——Next 静态
导出会预载路由全部动态 chunk，模块仍全部求值；收益纯来自执行时序移出 TBT 窗口。
温和（-11%）但两页×两跑一致、零内容损失。**闭环**：SSR HTML 载默认 tab（48 SVG+
6 tabs）；水合 DOM 54 SVG+4 recharts 面板。calibration 独立页（759ms，recharts
确证）留候选——需图表级 LazyMount（下轮裁量）。配额/activationStart 仍未到窗口。

工件：`runs/lh121_{track,regime}_{1,2}.json`、`runs/lhLIVE121_*.json`。
边界：display lane；0 ledger / 0 frozen / 0 OOS。


## 轮 122（2026-10-02）：/calibration 图表级拆分——TBT -40%（本地）/ 中位 425ms（线上）

market 轮 114 配方应用到独立 /calibration 页（759ms，recharts 确证）：两图表块
（可靠性散点+ECE 线）逐字切片入 `calibration-charts.tsx`（dynamic ssr:false+420px
骨架）；统计网格/徽章留 SSR；下折 CN 卡+horizon 卡加 LazyMount。

| 指标 | 基线 | 拆分后 |
|---|---|---|
| 本地 TBT（双跑） | 759ms | **450~480ms（-40%）** |
| 线上 TBT（3 跑中位） | — | **425ms**（324~563） |
| CLS | 0 | **0** |

主线程 ~6s 不变（静态导出预载天花板，轮 121 注记同源）。DOM 闭环：US 卡两
recharts 面板挂载、恰好 2 骨架残留（=LazyMount 下折占位，设计内）。过程如实：
切片边界两次语法错（孤儿 div/外层未闭合）被 tsc 即时拦截即修。

工件：`runs/lh122_calib_{1,2}.json`、`runs/lhLIVE122_calib_{1,2,3}.json`。
边界：display lane；0 ledger / 0 frozen / 0 OOS。


## 轮 123（2026-10-02）：/track 免费获益——组件复用使轮 122 拆分自动生效，线上中位 858→333ms（-61%）

零新代码：/track 默认 calibration tab 静态导入的正是轮 122 拆分的
`CalibrationView`——图表级 dynamic 拆分随组件复用自动惠及该路由（发布链已在
轮 122 完成）。本轮仅验证+量化：

| 指标 | 轮 121（仅 per-tab split） | +图表拆分（继承） | Δ |
|---|---|---|---|
| 本地 TBT（3 跑） | 950~970ms | **450~460ms** | **-53%** |
| 线上 TBT（3 跑中位） | 858ms | **333ms**（331~375） | **-61%** |
| CLS | 0 | **0** | — |

DOM 闭环：6 tabs+2 recharts 面板+2 设计内骨架。SSR：calibration 统计网格在墙、
recharts 零入 SSR。**方法论注记**：组件级拆分的复用红利——一次改动多路由受益，
先查复用面再排队新工程（本轮原计划的"增量拆分"被证明已在轮 122 隐式完成）。
搜索配额 10-03 18:50 UTC（现 13:56，未到窗口）；activationStart pending。

工件：`runs/lh123_track_{1,2,3}.json`、`runs/lhLIVE123_track_{1,2,3}.json`。
边界：display lane；0 ledger / 0 frozen / 0 OOS。


## 轮 124（2026-10-02）：/confirmation per-tab dynamic——本地 -28%、线上未复现（保留，如实分野）

最后一个 Tabs 页（874ms）套轮 121 配方：默认 smart-money 保静态，insiders/
reddit/theme-slice per-tab dynamic。**本地 A/B**：874→540~720ms（中位 ~-28%）、
CLS 0、DOM 闭环（4 tabs+smart-money 行在墙）。**线上 3 跑：699~908ms 中位 899——
未复现本地收益**：时序型收益（预载天花板下）被线上网络窗方差吸收（轮 121/123
的线上大幅收益均伴随图表级结构性拆分，本页无）。**裁决：保留**——零内容损失、
零回归（CLS 0）、与全站 Tabs 页一致性；如实记录"本地有效/线上未证"分野。
regime 内 positioning/taco 经查已在轮 121 per-tab dynamic 中结构性解决，无需
重复处置。配额 10-03 18:50 UTC 未到窗口；activationStart pending。

工件：`runs/lh124_conf_{1,2}.json`、`runs/lhLIVE124_conf_{1,2,3}.json`。
边界：display lane；0 ledger / 0 frozen / 0 OOS。


## 轮 125（2026-10-02）：smart-money 13D 图拆分——实测净害回滚；图表级拆分的第二边界入册

confirmation 默认 tab 的单块 recharts 卡（13D 年度柱状，180px）按轮 114 配方切片
（逐字+dynamic ssr:false+LazyMount）。**实测（4 跑）**：TBT 540~720 → **800~1,040ms
（净害 ~+300ms）**；同窗对照 evidence 页 190ms≈基线（宿主无争用，测量可信）；
DOM 闭环本身通过（高窗 1 surface+13 bars+零骨架）。

**机理**：表格主导页上，异步小图 chunk 在 TBT 窗口内到达并求值+挂载 recharts，
反而把原本被首批 bundle 一次吸收的成本摊进了窗口。**边界入册（图表级拆分第二
定律）**：拆分仅在**图表为页面主导成本**时获益（calibration 两图+recharts 主导
=-40%；market 四卡=-42%）；表格主导页上的单小图=净害。与 cv 阈值（万级 DOM）、
预载天花板、本地/线上分野并列为本战役第四条实测边界。**改动已回滚**。

值守：今晚通道 19:23 已提交 0b3a9a98e（soft_fail 仅 build_ticker_metadata），健康。
配额 10-03 18:50 UTC 未到窗口；activationStart pending。

工件：`runs/lh125_conf_{1..4}.json`、`runs/lh125_ctrl_evidence.json`。
边界：display lane；0 ledger / 0 frozen / 0 OOS。


## 轮 127（2026-10-02）：activationStart 预渲染命中实测——合成探针未证实（0），如实入册

**方法**：puppeteer-core 驱动本机 Edge（headless+headful 各一轮）——载入线上 `/`
→确认 speculationrules 在墙→hover 内链 700ms（moderate 阈 ~200ms）→点击→读
`performance.getEntriesByType('navigation')[0].activationStart`。

**结果（两轮）**：`activationStart=0`，type=navigate——**预渲染未激活**。

**诚实归因（未定论，二候选）**：
① CDP 合成鼠标事件可能不触发 Chrome 的 hover 启发式（headless 模式本身禁用
speculation 是已知行为，headful 亦 0 故不能排除合成事件根因）；
② 站内链接全部是 clean path（`/Aionis/dashboard`），GitHub Pages 301 到
`.html`——预渲染跟随 301 的行为未证，可能取消。
**裁决**：合成探针能力到此为止；**呈业主一项 30 秒人工验证**（真实鼠标悬停任一
导航链接 ~0.5s 后点击，如近乎瞬时呈现即为命中）。若人工亦未命中，候选修法=
nav 链接改 `.html` 后缀（或 trailingSlash 构建），挂起待证不盲改。
探针脚本已按无驻留纪律清理。

工件：无保留（临时 harness 已删；两轮输出如上）。边界：display lane；
0 ledger / 0 frozen / 0 OOS。


## 轮 128（2026-10-02）：Baseline 外部对照（WebFetch 已知源，配额仍余 ~28h）——情报 null 如实入册

**值守**：通道 ok_committed（0b3a9a98e）；staleness 周检按期（09-28 success，下次
10-05）；CI 绿；零未决 Issue。

**对照面**（web.dev/baseline 一手）：Popover/:has()/CSS nesting/inert/`<search>`/
Subgrid 等 Baseline 状态到手；Interop 2026 页持续 404（web.dev 文档重组期，第三
次如实注记）。逐项对本仓判定：
- **`<search>` 地标**：候选拦截在"已存在"——HomeSearch 的 form 已带
  `role="search"`（ARIA 地标等效，双写反而违规）。null-by-precondition。
- **Popover API**：可替代导航下拉/⌘K 的手写 top-layer+焦点管理，但现实现经 98
  轮验证且 a11y 100——无实测需求支撑的重写=风险/收益倒置。否决。
- **:has()/nesting/inert**：无具体痛点对映（frost 钉头是 overflow 祖先问题非
  选择器问题；模态焦点已由 Radix 处理）。否决。
**结论：Baseline 面无可落地新特性**——本仓相关能力（cv/Speculation Rules/语义
地标）反而先行于 Baseline。null 入册；配额恢复后的全量搜索扫描仍保留为候选。

边界：docs/ops lane；0 ledger / 0 frozen / 0 OOS。


## 轮 132（2026-10-02）：axe-errored 三页根因坐实——axe-core midpoint 工具级 bug，如实归档

复现取证（discipline）：a11y score=None 的唯一原因 =
`color-contrast: axe-core Error: Element midpoint exceeds the grid bounds`
（控制台零错误、其余审计正常）。congress/filers/discipline 三页共有
FrostedScrollArea 的大表+transform/裁剪容器模式（轮 66~73 视觉体系）——axe 的
色对比中点网格计算在该容器几何上崩溃，是 **axe-core 已知工具级缺陷类**，非页面
缺陷指示：对比度本身已由全站令牌级审计覆盖（轮 112 令牌 + 轮 131 三修，
24 路由实测 100）。

**裁决**：不改久经考验的 frost 视觉去迁就工具 bug（98 轮验证体系 > linter 类
工具的单点报错）；如实归档为 audit-errored-by-tool。

### 全站 a11y 终板（轮 112+131+132，33 路由）

- **24×100**（含 stock 全系 ~1460 页 92→100、shelf 96→100）
- **4×95~96 target-size 按设计不修**（heatmap 树图数据格/密表 ticker——理由在册）
- **3×axe-errored-by-tool**（midpoint bug，对比度经令牌级覆盖）

工件：`runs/lh132_discipline.json`。边界：display lane；0 ledger/0 frozen/0 OOS。


## 轮 134（2026-10-03）：Interop 2026 全量扫描（配额恢复）——VT 采纳+潜伏透镜 404 修复；两开放缺陷发现入册

**情报面**（搜索配额恢复；权威源=web-platform-tests/interop 2026 README 一手）：
20 焦点区（15 新+5 承继）+4 调研区。逐项对四边界裁决：**跨文档 View Transitions**
=唯一可落地（多页静态站渐进增强，~10 行+reduced-motion 守卫）；scroll-driven
animations/popover/anchor 等无痛点对映（轮 128 同判）；**Speculation Rules 不在
Interop 2026 清单**——本仓第三项先行于生态的能力（cv/SpecRules/VT）。

**落地两项**（7ad89d1d4，线上双验）：①`@view-transition{navigation:auto}`+
reduced-motion 禁动画守卫——同源导航获平台级 cross-fade（Chrome 126+，未支持
者零影响）；②**潜伏缺陷修复**：LiquidGlassFilter 引用 `/liquid-glass-map.png`
缺 basePath——**自部署起每页 404**，Chrome 透镜折射静默降级为纯 blur（轮 71
仅在 dev 验证的教训）；href 镜像 next.config 的 isProd 条件。线上：新路径 200、
VT 规则在 CSS chunk（首次 0 读数=CDN 边缘延迟，120s 后收敛——轮 117 教训复现）。

**两开放缺陷（发现即入册，留专门轮不仓促）**：
1. **React #418 水合失配**（overview 页）：本地静态+线上间歇出现、dev 不现——
   时序依赖；双载文本 diff 定位到 ColorConvToggle 的 mounted 分支，但
   useSyncExternalStore 语义理论上不应失配——需 React dev 复现精修。
2. **`__next.*.txt?_rsc=` 预取 404 风暴**：Next 客户端路由预取的 RSC payload
   全部 404（轮 116 曾误读为慢网络——实为 404）；导航经全页加载仍工作，但全部
   预取浪费。疑静态导出与 RSC 预取的交互缺陷，待专门诊断。

边界：display lane；0 ledger / 0 frozen / 0 OOS。


## 轮 135（2026-10-03）：双缺陷专门轮——RSC 预取 404 根因坐实（上游）；#418 toggles 假设经对照实验消除

**RSC 预取 404（根因坐实，上游缺陷）**：payload 文件**存在**但被 Turbopack 导出
嵌套在路由目录（`out/ipo/__next.!KGRhc2hib2FyZCk.ipo.txt`），而客户端路由按根
路径请求（`/Aionis/__next.!KGRhc2hib2FyZCk.ipo.txt`）——路由组 `(dashboard)` 页
的预取布局错位；根页的 `_tree.txt` 在根位置故其预取正常。**Next 16.3.8 静态导出
上游缺陷**：本地不可修（发布期拷贝 hack/全站 prefetch=false 皆不值——导航经全页
加载无损工作，代价仅 ~50 次/页的废请求）。入册为 upstream，升 Next 版本时复查。

**#418（对照实验，假设消除）**：三个 nav toggles（ColorConv/Lang/Theme）的
uSES-mounted 模式替换为经典 useState/useEffect → 静态构建复测：#418 在
root/dashboard 依旧、market 依旧无——**toggles 非源**（实验补丁已回滚）。
outerHTML 双载 diff 法被序列化伪影污染（input type=源码即有；文本分段为
序列化差异非 DOM 差异）。**已确定范围**：真源在 Overview 内容（dashboard 页特有，
非壳层组件）；market 无→非全局 Provider。**下一仪器明确**：非压缩客户端构建
（React dev bundle 对静态导出水合）拿完整 mismatch 栈——留专门轮执行。

边界：display lane；0 ledger / 0 frozen / 0 OOS。


## 轮 136（2026-10-03）：#418 终局——八构建受控二分锁定 ArgumentChain 网格，根因=嵌套锚点，修复后本地+线上四页全零

**方法链**（全部消融门控构建后还原）：heroOnly=0 → noTail=0/noFirst=1（后半含源）
→ noTailA=0/noTailB=1（TrustRibbon/Verdict/ArgChain 段）→ noArgChain=0（锁定
ArgumentChain）→ noSegs=0/noCorrob=1（四卡网格）→ 错误签名解码
`args=("HTML","")`=客户端空串 vs 服务端文本 → 网格子树定向 diff **当场抓获**：
SSR 串中 `<a href=/picks></a><div card>` 是**兄弟**而客户端 vDOM 中卡在锚**内**。

**根因**：MiniPicks 的四个逐股 `<Link>` 行嵌套在 ChainSegment 的卡级 `<Link>`
内——**嵌套 `<a>` 是无效 HTML**，浏览器解析器在预渲染串上强制闭合外层锚点，
SSR 解析 DOM 与客户端 vDOM 结构必然相撞→每次加载必发 #418（root/dashboard）；
/picks 段是唯一 detail 含链接的 segment——精确解释页面分布（market/track 恒净）。
轮 134 的 ColorConvToggle 定位实为良性后水合状态（首个可见差异非首处失配）。

**修复**：四行改 span（卡本身链至 /picks，逐股页一跳可达）。**验证**：本地
root/dashboard/market/track 四页 #418=0；构建 1506 EXIT 0；tsc/eslint 净；
**线上 root/dashboard 双页 #418=0**（954dfcd78 发布后实测）。

10-06 满月评估倒计时 3 天（夜报自动化捆绑就绪，统计命令已预演）；业主三项
待反馈（悬停验证/campaign 裁决/选项 B 追认）无新输入。
边界：display lane；0 ledger / 0 frozen / 0 OOS。
