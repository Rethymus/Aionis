# 深度反思与前瞻分析（第二轮）— 呈业主

> 第一轮（轮 155）已覆盖六个疏漏、六个低把握、六个断裂点、四个功能提案（全部落地）。
> 本轮更深一层：覆盖第一轮**未展开**的盲区 + 已上线新功能自身的缺口 + 2026-10-04 外部情报刷新。

---

## 一、第一轮未展开的盲区

### 1. Watchlist 功能的自身缺口

已上线（轮 156-158）但有三个未做的配套：
- **无管理界面**：用户无法查看完整自选列表（只能逐页看星标）；没有"清空全部"或批量操作。
- **无导出**：localStorage 数据在浏览器清缓存后丢失——没有导入/导出机制。
- **CN 实时价格显示 `¥` 但价格来源是新浪**（人民币计价正确，但用户可能期待 HKD/USD 换算选项）。

**建议**：WatchlistStrip 加"展开全部" popover（含移除按钮）+ settings 导出/导入 JSON。

### 2. FreshnessBadge 的静态导出限制

badge 依赖 `Date.now()` 客户端计算——在**长时间打开的标签页**中不会自动刷新（用户看到的是打开时计算的"Xh ago"，可能过时）。

**建议**：60s `setInterval` 重算（轻量，一个 state tick）。

### 3. 交叉链接密度（第一轮提案，未实施）

**stock→picks 排名回链**：stock 页 KPI 区有 score/rank 但无 "在 Top 10 Picks 中排第 N" 的醒目标记——用户发现某股后想看排名，当前需手动回 /picks 页。stock_universe 已有 `rank` 字段。

**建议**：stock 页 KPI 行加 rank badge（Link 到 /picks）。

### 4. 移动端体验（从未审计）

全部 33 路由的 a11y/perf 审计都在桌面 viewport。移动端：
- top-nav 的 `hidden md:flex` 控件区在移动端**不可见**（Watchlist/Freshness/Lang/Theme toggle 全部消失）
- 长表在 FrostedScrollArea 的 380px 帽在移动端可能太低

**建议**：移动端 top-nav 加 overflow 菜单（现有 StickyTabs 或 hamburger）。

### 5. 静态导出的 404 处理边界

`/Aionis/nonexistent` 在 GitHub Pages 上会走自定义 404.html——但 URL **不重定向**，用户地址栏保持错误 URL。这是 Pages 静态托管的固有行为，无法改善，但 404 页的 Back to Dashboard 已提供出路。

### 6. i18n 的 9 个 prefix-only "suspicious" 键

第一轮清了 3 个确认孤儿；9 个动态前缀构造键（`atlas.flow.cat.*` 等）标记为 suspicious。这些是 `t(\`prefix.${x}\`)` 模式的合法使用——**确认无风险**，但审计工具每次运行都报告（噪音）。可加白名单注释。

---

## 二、已上线功能的低把握项

| 项 | 不确定什么 |
|---|---|
| Watchlist 在 ~1460 stock 页的 a11y | star button 的 aria-pressed 已加但未跑 axe 复测 |
| WatchlistStrip 的 Worker 调用频率 | 每次 dashboard 加载触发一次 fetch（30s TTL）——高频刷新可能被 Worker 限流 |
| FreshnessBadge 在移动端 | top-nav 控件区 `hidden md:flex`——移动端看不到 badge |
| CopyProvenance 的 citation 格式 | markdown 链接指向 GitHub blob 页面——在纯文本粘贴场景可能不渲染 |

---

## 三、方案失效断裂点（第二轮——聚焦新上线功能）

| # | 断裂点 | 概率 | 影响 |
|---|---|---|---|
| 1 | **Worker 端点失效**（Cloudflare 免费层变更/误删） | 低 | WatchlistStrip/stock 页实时价格静默降级——graceful 已设计 |
| 2 | **localStorage 在隐私模式下不可用** | 中 | Watchlist 不保存——catch 已设计（in-memory only） |
| 3 | **clipboard API 在非 HTTPS 环境** | 低 | CopyProvenance 按钮无响应——catch 已设计 |
| 4 | **SVG `<title>` 在触屏设备** | 中 | 无 hover——原生降级为无 tooltip（数据仍可见） |

---

## 四、亮眼功能（第二轮——递进于已上线四功能）

### A. Watchlist 排名变动通知（最高粘性递进）

**现有**：Watchlist star + Strip + 实时价格。
**做法**：localStorage 存上次访问时的 rank；本次访问时对比，Strip 上显示 `↑2`/`↓1` 排名变动徽标。
**为什么**：用户回访的核心动力——"我的股票排名变了"。
**成本**：~半天（localStorage 对比逻辑 + badge UI）。

### B. 键盘导航增强（tab 页快捷键）

/track /regime /confirmation 的 tab 切换无快捷键。`1-9` 数字键或 `[` `]` 前后切换。
**成本**：~2 小时（useEffect keydown listener）。

### C. 命令面板增强（⌘K 加 Watchlist 跳转）

⌘K 已有页面搜索；加"★ Watchlist"分组显示星标 ticker。
**成本**：~2 小时（filter 逻辑）。

---

## 五、全流程效率（第二轮）

第一轮已覆盖导航优化。第二轮瓶颈：
- **stock→picks 回链**（上面 §一.3）——最高性价比
- **atlas→track 深链**：atlas verdict 卡已有链接；divergence 卡可加 `/track#calibration`
- **stock 页相关股票**：同 sector 的 top-scored 股票横滑条（数据在 stock_universe 已有）——一跳发现同板块标的

---

## 六、外部情报刷新（2026-10-04）

| 源 | 发现 | 行动 |
|---|---|---|
| **UX 趋势 2026**（Quantummetric/Usermaven 等） | cohort-based retention + personalized alerting 是 2026 核心留存杠杆 | Watchlist 排名通知（提案 A）正是此方向 |
| **"Talk to Your Data"**（Clarista） | 对话式数据访问正替代传统仪表盘 | 本仓 i18n ⌘K 已有基础——远期候选，非本轮 |
| **canary.59** | 仍无 RSC 404 修复 | 观察项维持 |
| **PR #99058** | blocked 状态（1 review comment） | 观察项维持 |

---

## 七、本轮实施优先级

1. **stock→picks rank 回链**（§一.3）——最高性价比，数据已有
2. **FreshnessBadge 定时重算**（§一.2）——一行修复
3. **WatchlistStrip 展开/管理**（§一.1）——用户粘性递进

*边界：本轮分析读+搜+写文档+实施。docs/display lane；0 ledger/0 frozen/0 OOS。*
