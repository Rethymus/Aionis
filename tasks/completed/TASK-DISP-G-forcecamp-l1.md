# TASK-DISP-G — 势力阵营 L1 增强（岛屿卡 + URL 态筛选）

**Lane**: display（纯前端）。**优先级**: P2（设计规格 §9 明列的 L1 可选项，模块已上线后增补）。
**工作目录**: worktree `F:\ZCodeData\Aionis-wg`（分支 `feat/forcecamp-l1`，junction 已挂，LF ledger 已预拷）。

## 0. 现状（实测）

`/force-camp` 已上线：KPI 146/824/36/42，三药丸（697/59/68）+ min-weight 步进。痛点 =
36 个连通分量中大量 1-2 节点小岛被力导向甩到画布边缘，信息密度低且难点选（⑱/⑲ 轮目视
一致结论）。设计规格 §9 把"岛屿卡 + URL 态筛选"列为 L1 增强非验收门——本任务就是做它。

## 1. 交付物（全部前端，零 Python/导出改动）

1. **岛屿摘要卡**：度数=0 的"孤立实体"（nodes 里 degree 三项全 0 者若有）与 1-2 边小微分量
   不再进 SVG 主画布（或主画布仅保留 ≥3 节点的分量——以实测效果定，报告说明选择），
   改为画布下方一张可折叠"小微分量摘要卡"：按分量列出成员 chips + 共享边 w，点击 chip
   打开既有抽屉卡。诚实口径：卡头写明"未入画布的 N 个小微分量"。
2. **URL 态筛选**：边类型三开关与 min-weight 反映到 query string
   （如 `?t=co_hold,co_board&w=2`），刷新/分享保态；初载读 URL。不动既有药丸交互，
   只做双向同步。用 Next useRouter 的客户端既有模式（本仓无 searchParams SSG 约束冲突时）；
   若静态导出下 useSearchParams 需要 Suspense 边界，照代码库内既有先例处理。
3. i18n zh/en 新键对称（建议 namespace `forcecamp.islands.*`）。
4. 契约不变：lineage_graph.json / 导出端零改动；`tests/test_web_terminal_data.py` 零改动。

## 2. 验证（worktree）

```bash
cd F:\ZCodeData\Aionis-wg\web && npx tsc --noEmit && npx eslint src --max-warnings 33
```
build 留主线。零 Python 改动 → 不跑 pytest（若意外动了 .py 如实说明）。

## 3. 铁律与报告

纯 display-lane；0 ledger/frozen/config/prereg/OOS；不 push；不碰 docs/code-review/；
junction 永不 rm -rf。小步 commit。
报告：(a) 岛屿画布取舍裁决 + 实测节点数；(b) URL 参数 schema；(c) 文件清单；
(d) 验证 exit codes；(e) 冲突面（预期 force-camp-view.tsx / dict.ts / 新组件）。
