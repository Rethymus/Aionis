# TASK-DISP-D2 — 研究图谱 /atlas 区块②:预测—实现分差带(校准带 + ECE 分差)

- Lane:**display**(纯展示层;0 ledger / 0 frozen / 0 config / 0 prereg / 0 OOS / 零新抓取 / 零新导出)
- 设计规格:`reports/design/2026-08-28-editorial-diagram-language.md`(必读)
- 你只新增文件,**不修改任何既有文件**(共享文件已由主线预接线)。

## 交付物(唯一新文件)

`web/src/components/atlas/atlas-divergence.tsx` — 导出默认组件 `AtlasDivergence`。**组件顶层 `"use client"`(仓库既定模式:全部视图组件如此,i18n provider 是客户端方案;SSG 预渲染保证构建产物确定性)**。参考先例:`components/force-camp/force-camp-view.tsx`。

### 数据

`import { aionis } from "@/data/aionis"` → `aionis.calibrationReliability`(类型 `CalibrationReliability`)。**不要**直接 import json,一律走 barrel。
结构:`regions["us"]` 与 `regions["cn"]` 各有 `series: {month, n_train_pairs, n_pred, ece_oos, base_rate, prob_min, prob_max}[]`(实测各 53 个月,2022-01 起)与 `pooled_ece`。method=platt、walk_forward=true(可在描述里引用 `calibrationReliability.methodology`)。

### 区块 A:预测—实现分差带(US / CN 两个并列面板)

- 每月:竖向概率带矩形(y 从 `prob_min` 到 `prob_max`,半透明 primary 色)+ 该月 `base_rate` 圆点(in-band 用 primary 实心、out-of-band 用警示描边,不用红绿语义)。
- y 轴固定 [0,1] 概率;x 轴月份稀疏标注(每 6 个月);带内覆盖率统计:`t("atlas.div.coverage", {n, m, pct})`(n=base_rate∈[prob_min,prob_max] 的月数,四舍五入整数百分比)。
- 面板小标题用 region 名("US"/"CN" 直接字面量,不进 dict)。
- 标题/描述:`t("atlas.div.title")` / `t("atlas.div.desc")`;图例:`t("atlas.div.band")` / `t("atlas.div.realized")`;计数行 `t("atlas.div.n", {n, start, end})`。
- SVG 高度两个面板各 ~180-220px,宽 100% viewBox,确定性布局(月序升序,构建期算死)。

### 区块 B:月度 ECE 分差条

- 同样的两区域:每月一竖条,高度=`ece_oos`(y 轴 [0, max(0.5, 实测max) 取 nice 刻度]);用 `niceTicks`(`@/components/diagram/primitives`)。
- pooled_ece 用参考横线标注。
- 标题/描述:`t("atlas.div.ece.title")` / `t("atlas.div.ece.desc")`。

### 共用

- `DiagramFigure`(`@/components/diagram/primitives`)包装(含 sr-only 描述)。
- 每图下方**完整数据表回退**(`<table>`,表头永远渲染):月/带下界/带下上界/实现基准率/是否带内(或 ECE)。表标题 `t("atlas.div.table")`。
- 包在既有 `Card` 原语里,区块结构与 atlas-claims 一致。
- 缺数据/空 series:如实渲染空表与空图(不伪造)。

## 可消费的 i18n 键(已由主线预置,勿改 dict.ts)

`atlas.div.title, atlas.div.desc, atlas.div.band, atlas.div.realized, atlas.div.coverage, atlas.div.ece.title, atlas.div.ece.desc, atlas.div.table, atlas.div.n`

## i18n

直接 `const { t } = useI18n()`(仓库标准模式,`useI18n` 来自 `@/i18n/provider`)。键值插值用 `t(key, {n: 5})` 形式(查 provider 的插值签名后使用)。

## 边界(违反=BLOCKED)

- 不改 `dict.ts` / `top-nav.tsx` / `command-palette.tsx` / `page.tsx` / 任何 data 模块。
- 不用 recharts;不引新依赖;不用随机数/时间(`Date.now`/`new Date()` 禁止)。
- 涨跌语义色(--up/--down)不进图;红绿方向编码禁止。
- 不写"建议买入/卖出"类措辞;呈现测量,不给投资建议。

## 验证(worktree 内)

```bash
cd web && node node_modules/typescript/bin/tsc --noEmit
node node_modules/eslint/bin/eslint.js src/components/atlas/atlas-divergence.tsx
```

tsc 0 error、eslint 0 error 后原子提交(一个 commit),分支名 `agent/d2`。
build 由主线集成期执行(worktree 内 Turbopack 跨根限制,不要跑 next build)。
