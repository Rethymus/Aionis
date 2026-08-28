# TASK-DISP-D3 — 研究图谱 /atlas 区块③:数据血缘三层流图(来源族 → 类别 → 新鲜度)

- Lane:**display**(纯展示层;0 ledger / 0 frozen / 0 config / 0 prereg / 0 OOS / 零新抓取 / 零新导出)
- 设计规格:`reports/design/2026-08-28-editorial-diagram-language.md`(必读)
- 你只新增文件,**不修改任何既有文件**(共享文件已由主线预接线)。

## 交付物(唯一新文件)

`web/src/components/atlas/atlas-dataflow.tsx` — 导出默认组件 `AtlasDataflow`。**组件顶层 `"use client"`(仓库既定模式:全部视图组件如此,i18n provider 是客户端方案;SSG 预渲染保证构建产物确定性)**。参考先例:`components/force-camp/force-camp-view.tsx`。

### 数据(两个面板联查,全在 barrel)

`import { aionis } from "@/data/aionis"` →
- `aionis.dataHealth`(`DataHealth`):`panels: {key, file, category:"daily"|"cadence"|"frozen", as_of, exported_at, present, rows?}[]`(实测 49 面板;summary:{n_frozen:15, n_daily:25, n_cadence:9})。
- `aionis.apiCatalog`(`ApiCatalog`):`endpoints: {key, file, source, license, freshness, as_of, ...}[]`(49 端点,source 为一句一手来源描述)。

**不要**直接 import json,一律走 barrel。以 `dataHealth.panels` 为主表,key join `apiCatalog.endpoints`(同 key);join 不上的面板来源族落 "other/派生" 桶(诚实计数,不猜)。

### 来源族归组(source → family)

`source` 是自由文本(48 种)。用**确定性关键词规则**归组(规则写成纯函数,大小写不敏感,按序首中即止),建议族(以实际数据为准,运行时落在哪个桶都诚实渲染):
- EDGAR/SEC(EFTS、EDGAR、daily index、13D/G、Form 4/8-K/D、DEF 14A、13F-HR…)
- FRED/ALFRED(FRED、ALFRED、macro)
- GDELT(新闻)
- Reddit/ApeWisdom(散户热度)
- ARK(ark-funds)
- CFTC(COT)
- House/Senate/PTR(国会)
- 冻结派生(frozen OOS、ledger、PSI、IC、scores…)
- 其他

### 视觉:三层确定性流图(桑基式)

- 层 1 来源族(左)→ 层 2 类别(daily/cadence/frozen,中)→ 层 3 新鲜度呈现(右)。
  层 3 建议按 as_of 距面板自身 snapshot 的三类呈现:直接用 category 颜色 + as_of 最早/最新跨度标注;或按 as_of 年月分桶——**以确定性可解释为准,不许伪造时间运算**(`new Date()` 禁止,用字符串比较月份)。
- 节点高度=面板数(线性比例);边宽度=流量;三色:层用 `diagram.primary`/`muted`/`border` 区分,类别色 daily/cadence/frozen 用蓝/橙/灰固定映射(不涉涨跌语义)。
- 每节点标签:族名+计数;SVG 高度 ~420-520px,宽 100% viewBox,所有坐标构建期算死。
- 标题/描述:`t("atlas.flow.title")` / `t("atlas.flow.desc")`;层标签:`t("atlas.flow.l1")` / `t("atlas.flow.l2")` / `t("atlas.flow.l3")`;计数 `t("atlas.flow.n", {n})`。

### 共用

- `DiagramFigure`(`@/components/diagram/primitives`)包装。
- 图下方**完整数据表回退**(`<table>`,表头永远渲染):面板 key/来源族/类别/as_of/license(截断)。表标题 `t("atlas.flow.table")`。
- 包在既有 `Card` 原语里;归组规则纯函数放本文件内即可。
- join 空/缺面板:诚实落桶,不伪造。

## 可消费的 i18n 键(已由主线预置,勿改 dict.ts)

`atlas.flow.title, atlas.flow.desc, atlas.flow.l1, atlas.flow.l2, atlas.flow.l3, atlas.flow.cat.daily, atlas.flow.cat.cadence, atlas.flow.cat.frozen, atlas.flow.table, atlas.flow.n`

## i18n

直接 `const { t } = useI18n()`(仓库标准模式,`useI18n` 来自 `@/i18n/provider`)。键值插值用 `t(key, {n: 5})` 形式(查 provider 的插值签名后使用)。

## 边界(违反=BLOCKED)

- 不改 `dict.ts` / `top-nav.tsx` / `command-palette.tsx` / `page.tsx` / 任何 data 模块。
- 不用 recharts;不引新依赖;不用随机数/时间(`Date.now`/`new Date()` 禁止;as_of 只做字符串比较)。
- 涨跌语义色(--up/--down)不进图;红绿方向编码禁止。
- 桑基布局必须确定性可复现(排序规则写死);不写投资建议。

## 验证(worktree 内)

```bash
cd web && node node_modules/typescript/bin/tsc --noEmit
node node_modules/eslint/bin/eslint.js src/components/atlas/atlas-dataflow.tsx
```

tsc 0 error、eslint 0 error 后原子提交(一个 commit),分支名 `agent/d3`。
build 由主线集成期执行(worktree 内 Turbopack 跨根限制,不要跑 next build)。
