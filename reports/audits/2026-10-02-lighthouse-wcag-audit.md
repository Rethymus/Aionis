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
