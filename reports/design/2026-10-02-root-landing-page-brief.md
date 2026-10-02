# 决策简报：`/` 根路径——redirect 壳 vs 真实落地页（呈业主）

**日期**：2026-10-02（轮 115）· **性质**：产品决策（display lane 之上有内容取舍）· **现状**：`/Aionis/` 是 `redirect("/dashboard")` 的客户端跳转壳。

## 为什么现在提

Lighthouse 移动端实测（轮 112）：`/` 的 **LCP 5.8s**，其中 ~2.4s 是 redirect 链路自身
（FCP 1.8s 先画壳，正文要等跳转+二次加载+水合）。这是全站性能分数的最大单点
拖累，且每次首访都付这笔税。

## 三个选项（含实测数据）

### A. 保持现状（redirect 壳）
- 优点：零工作量；`/dashboard` URL 语义清晰。
- 代价：首访 LCP 5.8s 恒定税；SEO 上 `/` 无自有内容（sitemap 已用 `/dashboard.html`，
  无碍抓取，但社交分享/收藏 `/` 时 Open Graph 落在壳上）。

### B. `/` 直接渲染 dashboard 内容（去掉跳转）
- 做法：`app/page.tsx` 改为渲染 overview（与 `/dashboard` 同组件），`/dashboard`
  保留为别名（或 301 语义由 sitemap/内链自然转移）。
- 效果（估算基线=dashboard 直连：LCP 3.4s 线上/本地健康）：**省掉整段 redirect 税，
  LCP 预计 5.8→~3.4s**。
- 代价：两个 URL 同内容（canonical 需指明其一）；改动小（一个文件+canonical 声明）。

### C. `/` 做独立轻量落地页（hero+导航+核心读数，非全量 dashboard）
- 效果：LCP 最优（轻页+首屏即内容）；对首次访客的叙事最完整（品牌+一句话主张+
  三读数卡+进入按钮）。
- 代价：新页面工程（半天~一天）+ 与 dashboard 首屏内容重复度的取舍。

## 本仓数据补充（相关实测，供权衡）

- dashboard 直连本地 TBT 200~330ms（健康；线上 2.2s 是 redirect+网络放大）——
  选项 B/C 都不引入新的性能问题。
- 轮 115 atlas 实验佐证"内容优先"代价意识：LazyMount atlas 的 TBT 天花板收益仅
  -10%（中位 2.4→2.2s）对 SSR 内容损失，已按内容优先原则否决——选项 B/C 若做，
  全部内容保持 SSR，无此权衡。

## 建议（供裁决，非决定）

**B**：性价比最高（一个文件+canonical，LCP 立省 ~2.4s），且不动信息架构。
若未来想要品牌叙事落地页，B 可平滑升级到 C（C 是 B 的超集）。

## 红线

无论选哪项：0 ledger / 0 frozen / 0 prereg / 0 OOS；不动 `/dashboard` 组件本身；
canonical 方案需在 sitemap.ts 同步（轮 111 的 1501 条 URL 结构相应调整）。
