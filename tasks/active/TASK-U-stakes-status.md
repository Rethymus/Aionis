# TASK-U: 举牌状态机（持股比例）+ 13D cache 重建

> 优先级：中。worktree：`F:\ZCodeData\Aionis-wu`（分支 feat/stakes-status，已建，junction 已挂）。基于 main ca3074f+。
> 派发背景：同 TASK-S（2026-08-23 配额团灭，本文件 = 代理 U 完整规格）。
> 注意：若主线已完成 13D 重建（查 state/handoff 最新条目），跳过任务 1。

## 铁律 #0（业主明令）
**绝不请求/爬取 data.xiaoyinsi.com 或任何竞品站**。数据一律一手公共源（SEC EDGAR）。

## 背景
竞品 /stakes 签名特性 = 持股比例（"40.5%(前 12.2%)"）+ 状态机（主动 13D/被动 13G/清仓/降至5%下）。Aionis：13G 有 15,982 份 form 级流（无比例无状态）；13D 侧 smart_money 的 cache（efts_13d_*.json / sc13d_daily_aggregate.json）在主仓丢失，导出 SKIP 保留旧 60 行。

## 任务
1. **13D cache 重建**：src/aionis/ingest/stakes_13d_daily_index.py（13D daily-index 爬取器）+ stakes_13g.py（同门 13G 版）——照 13G 模式给 13D 跑 trailing 120 天，重建 sc13d_daily_aggregate，smart_money 重导出后 recent 到 120 行（上限 J 已改）。礼貌 ≥2s。
2. **状态机 bounded 解析**：两面板可见行（13G 前 150 + 13D 前 120）做有界文档解析：filing index → 主文档 → 正则抽 "X.X% of the ... class"（现值）+ 修正件前次值（"previous 5.2%" 类句式，抽不到诚实 null）。~2 请求/行 × 2s ≈ 20-30 分钟，45 分钟硬上限，cache 幂等。失败诚实计数。
3. **导出**：行加 `pct_now`/`pct_prev`（null 容错）；状态不猜——pct_now==0→清仓、<5→降至线下（仅解析值驱动；null 则状态 null）。methodology 增补。契约测试：pct∈[0,100]、prev 仅修正件可有、null 率入 source_health。
4. **前端**：smart-money-view（13D recent + 13G 卡）加持股比例徽章（"40.5%"，prev 有则"(前 12.2%)"次级）、主动/被动类型徽章（form 类型直接推导，零解析依赖）、清仓/降至线下（仅解析值驱动）。i18n（stakes.pct.* / stakes.status.*）。
5. **7-gate**：docs/data-intake-edgar-13g.md（及 13D 文档）增补文档解析段与请求账。

## 通用铁律
同 TASK-S 标准（worktree=兄弟目录 Aionis-wu；主仓 cache 只读逐文件 cp，禁 junction/rm -rf；PYTHONPATH=F:/ZCodeData/Aionis-wu/src）。交付报告：commit/13D 重建结果/解析覆盖率（pct_now/prev 抽到率/失败计数）/前端新形态/请求账/四项验证。
