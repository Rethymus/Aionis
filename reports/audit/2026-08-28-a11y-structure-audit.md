# 全站静态可访问性 / 文档结构首轮审计（TASK-DISP-Z）

- **日期**: 2026-08-28 · **Lane**: VERIFY（DEV-Z，零修复）
- **对象**: `web/out/` 当前构建（轮 24 产物），Next.js 16 静态导出，basePath=/Aionis
- **样本量**: 1,502 个 .html（junction `out/Aionis` 遍历前已判定：**本轮不存在**；解析失败 0）
- **方法**: python 标准库 `html.parser` 建轻量 DOM，批量全量扫描；先剥 `<script>/<style>`
  再分析；每类发现至多 10 条样例（完整清单在 `data/cache/` 临时产物，不入库）。

## 边界声明（必读）

1. **纯静态审计**：只看服务端渲染 HTML。水合后的 DOM 变化（Radix 弹层注入 aria、客户端
   补齐属性等）不在范围；凡"静态缺失但可能水合后补齐"的发现已降一档严重度并注明。
2. **对比度不做色值计算**（需真实渲染，深浅双主题）：只静态抽查 `text-muted-foreground/N`
   （N≤40）工具类的**正文性**使用；装饰性图标/分隔符合法排除。
3. `alt=""` 装饰性图片合法；本站 0 个 `<img>`，图片全部以内联 SVG 呈现。

## 执行摘要

**总体判定：结构面高度健康（5/8 项零发现 PASS），2 个 P1 集中在"标题结构 + 站点根"**。

- 六项零发现：空交互元素 0/54,769、重复 id 0、正 tabindex 0、无标签 input 0/1,424、
  `<img>` 无 alt 0（无 img）、SVG 无障碍标记缺失 0/53,123。
- 最严重 3 条：
  1. **[P1] `index.html`（站点根）是空的 `__next_error__` 错误壳**：无 SSR 内容、无 lang、
     无 landmark、无标题（F-AUD1）。
  2. **[P1] 8 个主要 hub 页完全没有任何 h1–h6**：annual/congress/events/executives/
     filers/index/ipo/quarterly，内容为样式化 div/span，标题导航对读屏不可用（F-AUD2）。
  3. **[P2] 语义 `<footer>` 全站 0/1,502**：视觉 footer 为 div 渲染，contentinfo 地标缺失
     （F-AUD3）。

## 逐审计项结果

| # | 审计项 | 样本量 | 计数 | 判定 |
|---|--------|--------|------|------|
| 1 | 图片替代文本 | 1,502 页（img=0，svg=53,123） | 缺 alt 的 img=0；无标记 svg=0（53,122 aria-hidden + 1 role="img"+aria-label） | PASS |
| 2 | 空交互元素 | a=46,856 + button=7,913 = 54,769 | 双空（无文本且无 aria-label/labelledby/title）= 0 | PASS |
| 3 | 标题层级 | 1,502 页 | 无 h1=9（其中 8 页零标题）；多 h1=0；跳级=3 页 | **FAIL（P1）** |
| 4 | 地标结构 | 1,502 页 | 缺 main=3（404/_not-found/index）；缺 nav=3；缺语义 footer=**1,502**；lang：1,501×zh-CN + index 缺失 | **FAIL（P2）** |
| 5 | 重复 id | 1,502 页 | 重复页=0，重复实例=0 | PASS |
| 6 | tabindex | 1,502 页全部 tabindex | 正值=0 | PASS |
| 7 | 表单标签 | 1,424 个非 hidden input | 无关联 label/aria-label=0 | PASS |
| 8 | 对比度线索（静态） | text-muted-foreground/40 及以下：208 处 | /40=183 全部为装饰性 SVG 图标（合法）；/30=25 全部为 picks.html 的 `—` 占位符 | PASS（1 条 P3 备注） |

`text-muted-foreground/N` 全量分布（参考）：/30=25，/40=183，/50=6，/60=1,097，/70=345，
/80=62。N≤40 之外的用法不在本轮范围。内联 style 低透明度（opacity≤0.4）文本=0。

## 发现项明细

### F-AUD1 · P1 · 站点根为空错误壳（area: root-shell / 1 页）

`web/out/index.html`（13KB）：`<html id="__next_error__">`，`<body>` 仅含
`<div hidden><!--$--><!--/$--></div>` + 7 个 script，**零服务端渲染内容**；无 `lang`、
无 main/nav/footer、无任何标题。样例：`out/index.html: <html id="__next_error__">`。
- 影响：静态形态下 SEO 抓取、no-JS 用户、水合前读屏拿到的站点根是空文档；`__next_error__`
  说明 `/` 的预渲染可能失败并回退错误壳。
- 边界：带 JS 时客户端大概率正常渲染整页（水合补齐），故定为 P1 而非 P0；水合行为不在
  本轮验证范围。
- 建议归属：display/engineer —— 排查 `/` 路由预渲染失败原因（导出日志/构建错误）。

### F-AUD2 · P1 · 8 个主要 hub 页零标题结构（area: headings / 8 页）

以下页面有完整 SSR 内容（如 annual.html 170KB）但 **0 个 h1–h6**，视觉标题全部为样式化
div/span（如 annual 首屏 `<span> Aionis`、`<div> 52`）：

`out/annual.html`、`out/congress.html`、`out/events.html`、`out/executives.html`、
`out/filers.html`、`out/index.html`（另计 F-AUD1）、`out/ipo.html`、`out/quarterly.html`

各页均有 `<title>`（如 "Aionis — 反泄漏选股研究终端"）但读屏的标题导航（heading
navigation）完全不可用。属服务端 DOM 真实缺失，与水合无关。
- 建议归属：display —— hub 页视觉标题改为语义 h1（CSS 保持现视觉），一处组件改动可覆盖
  多页（疑似共享布局）。

### F-AUD3 · P2 · 语义 footer 全站缺失（area: landmarks / 1,502 页）

全部 1,502 页无 `<footer>` 元素；视觉 footer 存在但为 div（class 含 footer，如
annual.html/picks.html 命中 5–6 处）。contentinfo 地标对读屏用户缺失。
main/nav 覆盖良好：1,499/1,502（仅 404/_not-found/index 缺失，其中 index 归入 F-AUD1）。
- 建议归属：display —— 布局组件将 div 改 `<footer>`，单点修改全站生效。

### F-AUD4 · P3 · 错误页缺 main/nav 地标（area: landmarks / 2 页）

`out/404.html`、`out/_not-found.html`：lang=zh-CN 正确，但无 main/nav。错误页内容极简，
影响有限；静态缺失、错误页交互少，定 P3（已按边界声明降档）。
- 建议归属：display（低优先，可与 F-AUD3 同批处理）。

### F-AUD5 · P3 · 标题跳级 3 页（area: headings / 3 页）

h1 之后直接更深层级，读屏标题树出现虚假深度：
- `out/market.html`：h1→h4
- `out/regime.html`：h1→h4
- `out/shelf.html`：h1→h3

疑为卡片网格标题用了 h3/h4。内容不丢失，导航体验受损，P3。
- 建议归属：display —— 卡片标题降为 h2/h3 或按 WCAG 惯例顺序化。

### F-AUD6 · P3 · force-camp.html 有 h2 无 h1（area: headings / 1 页）

`out/force-camp.html`：3 个 h2（未入画布的小微分量/共同持仓/人物共席）但无 h1。页面含
范例级图表可访问性实现（`role="img" aria-label="势力阵营 · 816 关系边"`），仅缺页级 h1。
- 建议归属：display —— 补一个视觉隐藏或可见的 h1。

### F-AUD7 · P3（备注）· /30 透明度占位符（area: contrast / 25 处 · 1 页）

`out/picks.html`：25 处 `<span class="... text-muted-foreground/30">—</span>`（空值占位
破折号）。属"无数据"标记而非正文，倾向装饰性；但破折号确实承载"无值"语义，/30 在浅色
主题下极淡。色值对比度需渲染计算，本轮边界外，仅定性列报。
- 建议归属：display（可选：提到 /50 或视为装饰性放行）。

## 通过项亮点（防回归参考）

- 53,123 个内联 SVG 全部带 aria-hidden="true" 或 role + aria-label，纪律极佳。
- 54,769 个 a/button 无一双空——轮 15 图标按钮治理成果在静态维度保持。
- 1,421 个 stock 详情页标题序列全部为干净的单 h1。
- 深浅双主题对比度全量计算需渲染，维持边界外声明（轮 15 已修 α-muted→实色）。

## 产物与纪律

- 本报告 + `2026-08-28-a11y-structure-audit-findings.json`（机器可读）入库，原子
  `docs(audit)` 提交，不 push。
- 扫描脚本与完整清单在 `data/cache/a11y_structure_audit.py` / `a11y_audit_results.json`
  （gitignored，不入库）。
- 零修复、零生产改动、零网络、0 ledger/frozen/config/prereg/OOS。
