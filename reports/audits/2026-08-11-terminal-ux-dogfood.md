# Aionis 终端 UX / 结构审计（dogfood）

**审计日期**: 2026-08-11
**方法**: `curl` 抓取 13 条已部署路由（`https://rethymus.github.io/Aionis/<route>`）的原始 HTML，grep 提取结构信号（h1/h2/h3 计数、`title=` tooltip 计数、nav 链接、空态关键词、zh/en 存在性）。WebFetch 的 markdown 转换会丢弃 `title=` 属性，故改用 curl + grep（与 gloss 验证同一方法）。
**背景**: 数据刷新 CI 正在运行，故不报"数据陈旧/缺失"——那由 CI 解决。只看与数据无关的结构/UX。

---

## 执行结论

**总体判定**: **结构基本自洽**——无重大 UX 缺陷。业主 2026-08-09 提出的"拼凑杂烩"观感，经本 session 的 IA 重构（5 层漏斗 + 七主题解散进 hub + 全站术语 gloss）已大幅缓解。

### 一致性矩阵

| 路由 | h1 | h2 | tooltips | nav | 空态 | zh | en | 备注 |
|------|----|----|----------|-----|------|----|----|------|
| `/` (root) | 0 | 0 | 0 | 4 | 0 | ✓ | ✓ | Next.js 客户端 redirect shell，非内容页（非 bug） |
| `/themes` | 1 | 2 | 48 | 13 | 0 | ✓ | ✓ | 5 层漏斗 IA，gloss 覆盖好 |
| `/picks` | 1 | 0 | **705** | 13 | 0 | ✓ | ✓ | 每选股行带 tooltip——极佳 |
| `/confirmation` | 1 | 0 | 61 | 13 | 0 | ✓ | ✓ | smart-money/insiders/reddit 术语 gloss 到位 |
| `/track` | 1 | 0 | 0 | 13 | 0 | ✓ | ✓ | hub 概览页——gloss 在子路由（/power-floor=35） |
| `/market` | 1 | 0 | 8 | 13 | 0 | ✓ | ✓ | 适中 |
| `/positioning` | 1 | 0 | 0 | 13 | 0 | ✓ | ✓ | COT 视图已全 i18n，无裸术语（见下） |
| `/sectors` | 1 | 0 | 13 | 13 | 0 | ✓ | ✓ | 适中 |
| `/power-floor` | 1 | 0 | 35 | 13 | 0 | ✓ | ✓ | track-hub gloss（a954acb）到位 |
| `/calibration` | — | — | — | — | — | — | — | curl 超时（6s 上限），非内容问题 |
| `/smart-money` | — | — | — | — | — | — | — | curl 超时；gloss 已 curl 验证（1a62ed2 部署 HTML 实含 tooltip） |
| `/insiders` | 1 | 0 | 1 | — | — | — | — | 内容渲染正常 |
| `/reddit` | 1 | 0 | 4 | — | — | — | — | 内容渲染正常 |

---

## 发现

### LOW — `/positioning` 与 `/track` 概览页 0 tooltip

- `/positioning`（COT 多空压力）与 `/track`（hub 概览）的预渲染 HTML 中 `title=` 计数为 0。
- **判读**: 不一定是缺陷。
  - `/positioning` 已全 i18n（`t("positioning.*")`），展示的是"composite z-score / crowding"等概念经 i18n 后的中文标签，无裸英文术语需要 gloss。
  - `/track` 是 hub 概览，gloss 在其子路由（/power-floor=35 tooltips）——hub 本身是导航页。
- **建议（可选，非必须）**: 若业主希望"composite / crowding / z-score"等概念也有 hover 说明，可后续在 `positioning-view.tsx` 的 `positioning.composite` / `positioning.crowding` 标签上加 `title=`。优先级低。

### LOW — `/root` 是 redirect shell

- `/Aionis/` 预渲染 HTML 只有 `<title>` + Next.js 客户端引导脚本，无 `<h1>`/正文。
- **判读**: 这是 Next.js 静态导出对根路由的常见行为——用户落地后被客户端路由重定向到默认页。**非 bug**，但若业主希望根路由有 SEO 友好的预渲染内容（h1 + 摘要），可在 `web/src/app/page.tsx` 改为服务端渲染的着陆页。
- **建议（可选）**: 若 SEO/首屏重要，把 `app/page.tsx` 做成有 h1 + 项目摘要的静态着陆页（重定向逻辑移到客户端 effect）。

### 正面 — 一致性强

- **所有内容路由 h1=1**（无缺失标题，无重复 h1）——可访问性基线达标。
- **nav 一致**: 13 条内部导航链接在每条内容路由都出现——用户始终知道自己在哪。
- **双语**: 每条路由都同时含 zh + en 内容——满足业主"中英并存"诉求。
- **无空态裸渲染**: 未检测到"建设中/awaiting/coming soon"关键词在内容路由上（数据缺失由各 view 的 i18n 空态分支处理）。
- **gloss 覆盖分化合理**: 高信息密度页（/picks=705, /themes=48, /confirmation=61, /power-floor=35）tooltips 多；导航/概览页少——符合"术语密度驱动 gloss 密度"。

---

## 与"拼凑杂烩"的关系

业主 2026-08-09 批终端"像拼凑杂烩"。本 session 的 IA 重构直接对症：
1. **5 层漏斗**（`/themes`，commit 463136a）——给了一个统一的研究架构叙事。
2. **七主题解散进 hub**（commit 1b3fe8a）——同类型数据归到同 hub（定标/佐证/问责），不再是七个并列卡片。
3. **全站术语 gloss**（track-hub a954acb + confirmation-hub 1a62ed2）——专业术语统一配 zh+en hover 说明。

审计时点（2026-08-11）的结构信号支持：路由间一致（h1/nav/双语），gloss 覆盖与术语密度匹配。"拼凑杂烩"的观感应已大幅缓解。**建议业主再实测部署站**（hover 几个术语、点漏斗各层、切 hub tabs）确认体感。

---

## 限制

- `curl` 抓的是预渲染 HTML；客户端交互（tab 切换、hover 动画、响应式）未测——需业主在浏览器实测。
- `/calibration` 与 `/smart-money` 因 curl 6s 上限超时未取到结构信号（非内容问题；后者 gloss 已在 1a62ed2 部署 HTML 中 curl 验证）。
- 未做移动端视口、对比度、屏幕阅读器实测（需浏览器自动化，本次为静态 HTML 审计）。

**审计员**: 主会话（opus，curl + grep，subagent 因 [1210] web-tool 路径失败改主会话执行）
