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
