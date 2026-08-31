# TASK-T: manager 页与机构目录对齐

> 优先级：中高。worktree：`F:\ZCodeData\Aionis-wt`（分支 feat/manager-align，已建，junction 已挂）。基于 main ca3074f+。
> 派发背景：同 TASK-S（2026-08-23 配额团灭，本文件 = 代理 T 完整规格）。

## 铁律 #0（业主明令）
**绝不请求/爬取 参照站 或任何竞品站**——形态参照而已。

## 背景：竞品 /manager/{CIK} 形态
两 tab（当前持仓 = 前 50 大 + 集中度 widget「前 6 大占比 74% + 逐项条 + 其他桶」；调仓 = 四态 KPI + Δ市值/股数环比复合单元格"54,249,798 +204%"）+ 机构目录有搜索。Aionis 现状：/manager/[cik] = Top10 表 + ChangesBlock 芯片（Δ市值已上线）；/institutions = 40 位策展卡 + 类别 chips 无搜索。

## 任务
1. **持仓广度（先查数据可得性）**：读 src/aionis/ingest/form13f.py——聚合 cache 存的是全持仓还是只有 top10？（主仓 data/cache 的 form13f 缓存可只读查 schema，worktree 逐文件 cp 后查）。全量→export 输出 top50（payload ≤250KB 安全；契约测试 top10 钉改 topN 语义）；只有 top10→不扩（诚实报告），集中度 widget 用 top10 口径+脚注。
2. **manager-view 改造**（institutions/manager-view.tsx + manager-book.tsx）：tab 化（当前持仓/调仓，URL hash 或 state，静态导出可用性优先）；当前持仓 tab = TopN 表 + 集中度 widget（数据自查）；调仓 tab = 四态 KPI（建仓/增持/减持/清仓计数）+ 调仓表（方向徽章+标的+Δ市值 fmtUsd+股数环比复合格式）。
3. **/institutions 搜索**：40 位策展名客户端搜索（ticker/name 子串，stream-kit/companies 先例）。
4. i18n zh/en（manager.tabs.* / concentration.* / institutions.search.*）；契约测试同步。
5. 若扩了导出：worktree cp form13f cache 单文件后重导出（SKIP 守卫保护其他面板）。

## 通用铁律
同 TASK-S 标准（worktree=兄弟目录 Aionis-wt；PYTHONPATH=F:/ZCodeData/Aionis-wt/src）。交付报告：commit/任务1 结论/新形态清单/payload 变化/四项验证/i18n 新键。
