# TASK-DISP-AA — 标题语义 + 语义 footer（Z 审计 F-AUD2/3/5/6 修复）

**Lane**: display / 前端结构。**工作目录**: worktree `F:/ZCodeData/Aionis-wy`
（分支 `agent-aa/heading-semantics`）。**优先级**: P1（读屏标题导航不可用）。

## 0. 背景（Z 审计发现，主线已甄别）

审计 `reports/audit/2026-08-28-a11y-structure-audit-findings.json`（先读它）。**主线甄别**：
- F-AUD1（`out/index.html` 为 `__next_error__` 空壳）= **已知非缺陷，不修**——根页
  `page.tsx` 本就是 `redirect("/dashboard")`，Next16 静态导出下重定向页即此轻量壳
  （轮 21 已裁决并记录于 `state/current.md` ㉑）。你在报告外处置，勿改它。
- F-AUD2（8 页零标题）/F-AUD5（3 页跳级）/F-AUD6（force-camp 无 h1）= **要修**。
- F-AUD3（语义 footer 0/1,502）= **要修**。F-AUD4（404/_not-found 缺 landmark）=
  顺手修（低风险才修，否则记录不做）。F-AUD7 = 不修（合法占位符）。

## 1. 修复方案（视觉零变化优先）

1. **零标题页**：找到各页现有的样式化标题元素（div/span + 标题类），把元素标签升级为
   `h1`，**类名与渲染样式原样保留**（视觉零变化）。若某页确无可见标题元素，加
   `sr-only` h1（文案取该页 nav.title 对应 dict 键值）。页面清单以 findings JSON 为准
   （annual/congress/events/executives/filers/ipo/quarterly + findings 里所指 index 页），
   逐一在 `web/src/app/(dashboard)/` 定位。
2. **跳级页**（market/regime h1→h4、shelf h1→h3）：把下游标题元素的层级改为正确的
   h2/h3，类名保留；若某处层级深改有布局风险，则只改风险为零的，其余记录不做。
3. **force-camp**：现有 h2 升级或补 sr-only h1。
4. **语义 footer**：找到共享布局里的视觉 footer（div），元素换 `footer`，类名保留。
   若 footer 在多个布局文件里，逐一换；`<footer>` 内已有 landmark 语义即可。
5. 禁止改文案、禁止改任何视觉类名/样式值、禁止新增依赖。

## 2. 测试与验证

- `node node_modules/typescript/bin/tsc --noEmit`（在 `web/`，用该命令勿用 npx）→ 0。
- `npx eslint src` 对触及文件 0 error（存量警告不管）。
- 自建快速结构校验脚本（临时，不提交）：对上述 8+3+1 页的源码确认 h1 存在、footer
  元素计数。**不需要 next build**（主线集成时重建验证）。

## 3. 边界

零网络；零 ledger/frozen/config/prereg/OOS；不 push；不碰 `docs/code-review/`、
`state/`、`tasks/`。交付 1 个原子 commit（fix+无测试文件变更时写明结构校验方式）。
收尾把"## 执行记录（DEV-AA）"追加到主仓任务书
`F:\ZCodeData\Aionis\tasks\active\TASK-DISP-AA-heading-semantics.md` 末尾。

## 执行记录（DEV-AA）

**Commit**: `917cfa1`（worktree `Aionis-wy`，分支 `agent-aa/heading-semantics`，
11 files，+42/−10，全部在 `web/src/`，未 push，树干净）。

**逐页处置清单**：
- **F-AUD2 零标题页**：
  - `annual` + `quarterly`（同一组件 `filings/fin-deadline-view.tsx`）：主卡可见页题
    CardTitle（`filings.annual/quarterly.title`）升级为 h1——1 处改动覆盖两页。
  - `filers`（`filers/filers-view.tsx`）：可见页题 CardTitle（`filers.title`）→ h1。
  - `congress` / `events` / `executives` / `ipo`：核对构建产物 DOM，ok 态**确无可见页题**
    （主卡 CardTitle 是 section 题："申报流"/"全市场申报流"/"DEF 14A"/"Form D"），按
    §1.1 加 sr-only h1，文案取 nav 键：`nav.congress`/`nav.events`/`nav.executives`/
    `nav.ipo`。各页空态可见 h1（`*.title` 键）原样保留，任何状态至多 1 个 h1。
  - 机制：`ui/card.tsx` CardTitle 增**可选用** `as` prop（默认 `"div"`，渲染/类名/
    data-slot 逐字节不变）；全仓恰好 2 处 `as="h1"` 调用点（脚本验证）。
- **F-AUD5 跳级**：`market`+`regime`（同一 `market/macro-drivers-card.tsx`）3× h4→h2；
  `shelf`（`shelf-view.tsx` DocCard）h3→h2。类名原样，页 h1 未动，无布局风险项。
- **F-AUD6**：`force-camp-view.tsx` 根部加 sr-only h1（`nav.forcecamp`），3 个 h2
  （view 2 + islands-card 1）原样保留。
- **F-AUD3 = 未改（审计前提为误报）**：逐一核查所有 layout（root + dashboard）与
  `out/*.html` DOM——**不存在共享视觉 footer div**（布局只渲染 TopNav/main/BackToTop，
  `</main>` 后无内容元素）。审计所谓 footer-classed div 实为 shadcn Card 类名里的
  `has-data-[slot=card-footer]` token（picks.html 的 5 个命中即 5 张 Card），非站点
  footer。把它们换 `<footer>` 会制造每页十几个伪 contentinfo；新增 footer 则违反
  "不改文案/视觉"。建议主线把 F-AUD3 改判为误报关闭，或另立"新增站点 footer"任务。
- **F-AUD4 顺手修（低风险部分）**：`app/not-found.tsx` 外层 div→`<main>`（类名不变，
  main 同为 block，视觉零变化）。缺 `<nav>` 未补（404 无导航内容可挂，需内容决策）。
- **F-AUD1 / F-AUD7**：按甄别未触碰。

**视觉零变化依据**：Tailwind v4 preflight 已含 `h1..h6{font-size:inherit;
font-weight:inherit}`（`out/_next/static/chunks/*.css` 实证），div/h1/h2/h4 换标签
同类名下渲染逐像素一致；sr-only h1 无盒模型。

**验证数字**：
- `node node_modules/typescript/bin/tsc --noEmit`（web/）→ **0 错误**（exit 0）。
- `npx eslint`（11 个触及文件）→ **0 error / 13 warning**，warning 全部为存量
  （exhaustive-deps、filers 未用 Badge import），所在行均非本次改动行。
- 临时结构校验脚本（stdin 直跑，未落盘未提交）：19/19 通过——7+1 页 h1 存在、
  h4/h3 跳级清零、CardTitle 默认行为不变、`as="h1"` 恰 2 处、5 个 nav.* dict 键
  zh+en 双语存在。未跑 next build（按任务书留给主线重建）。

**偏离说明**：无实质偏离。两处按现场事实微调：(1) sr-only h1 文案取 `nav.*` 键按
任务书执行（各 view 空态用的是 `*.title` 键，未改动它们）；(2) F-AUD4 只修 main
不造 nav（低风险才修的边界内）。
