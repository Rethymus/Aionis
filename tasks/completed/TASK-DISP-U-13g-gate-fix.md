# TASK-DISP-U — 13G 视图宇宙门补课 + "NONE." 哨兵清洗 + Reddit 统计就近披露

**Lane**: display（web/src 修复）。**优先级**: P0（审计实锤死链 58 处 + 渲染哨兵泄漏）。
**工作目录**: worktree `F:\ZCodeData\Aionis-wu`（分支 `feat/13g-gate-fix`，基线 = 派发时 main HEAD）。
**审计依据**: `reports/audit/2026-08-28-post-refresh-audit.md`（P0-1/P0-2/P2-1，含证据与计数）。

## 背景（为什么"修过的东西"又坏了）

⑳ 轮 DEV-K 给六视图上过 STOCK_PAGE_TICKERS 宇宙门（含 smart-money）。但 08-27 刷新后
`stakes_13g.json`（as_of 08-26）带入 **27 个新 13G ticker**（CIIT/VTMX/LSTA/WW…），
在 smart-money.html 与 confirmation.html 各产生 29 处 `/stock/` 死链（58 处）——
说明 13G 数据到这两页的**某条渲染路径绕过了既有门**（新申报行/修正行/卡片分区可能各有
一条 ticker→Link 的代码路径）。本任务 = 找到绕行路径并全部上门，杜绝同类第三犯。

## 1. 修复项

1. **P0-1 宇宙门**：定位 smart-money 页与 confirmation 页所有把 stakes_13g ticker 渲染成
   `/stock/[ticker]` Link 的代码路径（含卡片分区/分栏/摘要），全部接上与 DEV-K 同款
   STOCK_PAGE_TICKERS 门——未收录 ticker 降级纯文本（保留 ticker 字面，不发链）。
   验收口径：`grep -c "/Aionis/stock/" web/out/smart-money.html confirmation.html`（集成后主线跑）
   中只允许出现在宇宙内的 ticker；审计的 28 个 ticker 全部降级为文本。
2. **P0-2 哨兵清洗**：`stakes_13g.json` 的 `filings[20]` 携带解析失败哨兵 `ticker:"NONE."`。
   在导出端（scripts/export_terminal_data.py 的 13G 导出函数）清洗：哨兵值 → null（视图显示
   "—"），并计入该面板的 source_health 缺口计数（先例：sm 16/60 空）。视图端再加一道防御
   （ticker 含 "." 或等于哨兵样式 → 不发链）。**零编造**：解析失败必须诚实可见（缺口计数），
   不是悄悄美化。
3. **P2-1 Reddit 就近披露**：dashboard 统计条"Reddit 标的 297"（count_declared）与面板实际
   100 行的差异，在 dashboard 卡上加就近说明（如 "声明 297 · 载入 100"），i18n zh/en 各新增
   需要的键并保持对称（当前各 1,094 键）。

## 2. 边界与闸门

- 纯 display/导出层：0 ledger/frozen/config/prereg/OOS；零网络抓取；不碰 docs/code-review/。
- 不跑 next build（Turbopack worktree 限制——build 归主线集成）。
- 闸门：`npx tsc --noEmit` 0 错；`npx eslint src` 0 error（33 存量 warning 不要求清）；
  `uv run pytest -q tests/test_web_terminal_data.py` 全绿（若你在导出端清洗哨兵，13G 相关
  契约断言如受影响须同步更新并说明）；i18n 对称自检（键数 zh==en）。
- commit 计划：每修复项一笔（3 笔），只提交 gitignored 之外变更。**不 push**。
- 可加一个小契约测试钉死 P0-2（13G 导出不得含 "NONE." 哨兵）——鼓励，非强制。

## 3. 报告

(a) 绕行路径根因（哪条代码路径漏了门，为什么 ⑳ 的门没盖住它）；(b) 三修复项 diff 摘要；
(c) 闸门结果（tsc/eslint/pytest 实际输出摘要）；(d) commit 清单；(e) 主线集成后预期
（out/ 两页死链 58→0、"NONE." 不再出现、dashboard 披露文案）。
