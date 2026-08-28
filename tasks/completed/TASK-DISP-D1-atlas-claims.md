# TASK-DISP-D1 — 研究图谱 /atlas 区块①:核心主张透视图(IC 热力透视 + 结论森林图)

- Lane:**display**(纯展示层;0 ledger / 0 frozen / 0 config / 0 prereg / 0 OOS / 零新抓取 / 零新导出)
- 设计规格:`reports/design/2026-08-28-editorial-diagram-language.md`(必读)
- 你只新增文件,**不修改任何既有文件**(共享文件已由主线预接线)。

## 交付物(唯一新文件)

`web/src/components/atlas/atlas-claims.tsx` — 导出默认组件 `AtlasClaims`,含两个区块。**组件顶层 `"use client"`(仓库既定模式:全部视图组件如此,i18n provider 是客户端方案;SSG 预渲染保证构建产物确定性)**。参考先例:`components/force-camp/force-camp-view.tsx` 的结构(卡片+SVG+表格回退+方法学脚注)。

### 区块 A:月度 rank-IC 热力透视图

- 数据:`import { aionis } from "@/data/aionis"` → `aionis.icMonthly`(类型已钉死:`{month:string; us:number; cn:number; combined:number}[]`)。**不要**直接 import json,一律走 barrel(单一共享 chunk 惯例)。
- 视觉:每行一个月,三列 cell(US/CN/合并),cell 底色用 `divergingColor(v, 0.30)`(来自 `@/components/diagram/tokens`,symMax=0.30);cell 内数值文本用 tabular-nums,颜色按底色亮度取黑/白保证对比度;零值区(第 4 桶)配 muted 文字。
- 布局:66 行太长 → SVG 高度可分栏(如 2 列各 33 行)或行高压缩到 18-20px;保持**确定性布局**(月序升序,构建期算死)。宽 100% viewBox。
- 图例:蓝↔橙 8 档色带 + `t("atlas.icpivot.legend")`;计数行 `t("atlas.icpivot.n", {n,start,end})`。
- 标题/描述:`t("atlas.icpivot.title")` / `t("atlas.icpivot.desc")`。

### 区块 B:结论森林图

- 数据:`aionis.metrics`(类型 `Metrics`):combined_ic, ci_lo, ci_hi, sesoi, verdict, p, n_months(以面板实际值为准,不要硬编码;实测 combined_ic=-0.0088 / CI[-0.0336, 0.0159] / sesoi=0.01 / verdict="NULL")。
- 视觉:横向森林图——x 轴区间取 [-0.06, +0.06];CI 横条 + 点估计圆点;SESOI ±0.01 画半透明等价域带;零线粗线 + 标签 `t("atlas.forest.zeroLine")`;判定行 `t("atlas.forest.verdict", {v,p,n})`。
- 标题/描述:`t("atlas.forest.title")` / `t("atlas.forest.desc")`。

### 两个区块共用

- 用 `DiagramFigure`(`@/components/diagram/primitives`)包装(含 sr-only 描述)。
- 每个图下方给**完整数据表回退**(`<table>`,表头永远渲染):A=月/US/CN/合并;B=指标/值。表标题 `t("atlas.claims.table")`。
- 区块头:`t("atlas.claims.title")` / `t("atlas.claims.desc")`,包在既有 `Card` 原语里(参考其他 view 的用法;服务端组件可直接用 Card,不需交互件)。
- 空态/缺数据:如实渲染空表(不伪造)。

## 可消费的 i18n 键(已由主线预置,勿改 dict.ts)

`atlas.claims.title, atlas.claims.desc, atlas.claims.table, atlas.icpivot.title, atlas.icpivot.desc, atlas.icpivot.legend, atlas.icpivot.n, atlas.forest.title, atlas.forest.desc, atlas.forest.point, atlas.forest.ci, atlas.forest.sesoi, atlas.forest.zeroLine, atlas.forest.verdict`

## i18n

直接 `const { t } = useI18n()`(仓库标准模式,`useI18n` 来自 `@/i18n/provider`,force-camp 同款)。键值插值用 `t(key, {n: 5})` 形式(查 provider 的插值签名后使用)。

## 边界(违反=BLOCKED)

- 不改 `dict.ts` / `top-nav.tsx` / `command-palette.tsx` / `page.tsx` / 任何 data 模块。
- 不用 recharts;不引新依赖;不用随机数/时间(`Date.now`/`new Date()` 禁止)。
- 涨跌语义色(--up/--down)不进图;红绿方向编码禁止。
- 不写"建议买入/卖出"类措辞;呈现测量,不给投资建议。

## 验证(worktree 内)

```bash
# worktree 根目录下(web/node_modules 已由主线 junction 共享)
cd web && node node_modules/typescript/bin/tsc --noEmit
node node_modules/eslint/bin/eslint.js src/components/atlas/atlas-claims.tsx
```

tsc 0 error、eslint 0 error 后原子提交(一个 commit),分支名 `agent/d1`。
build 由主线集成期执行(worktree 内 Turbopack 跨根限制,不要跑 next build)。
