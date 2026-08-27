# TASK-DISP-S — 明星证据轮 2：UNVERIFIED 四人 + Southpoint 二壳（data.sec.gov 单源）

**Lane**: 调查（只产证据，零生产改动）。**优先级**: P2。
**工作目录**: worktree `F:\ZCodeData\Aionis-wk`（分支 `feat/stars-evidence-2`）。

## 0. 背景与约束（重要）

第一轮证据（`reports/design/2026-08-26-stars-candidates-evidence.md`）留下 4 个 UNVERIFIED
（Icahn 主申报壳 / Baron / Gundlach(DoubleLine) / Bessent(Key Square)）+ 1 个 BORDERLINE
（Southpoint/Citrone，第二壳 CIK 0001319998 被预算闸截断）。
**本轮硬约束：只准访问 `data.sec.gov`**（submissions JSON API，无需 key）——另一 agent 正在
并行刷新 efts/www.sec.gov 车道，跨主机并行礼貌安全、同主机禁止。预算 ≤20 请求、≥2.5s 间隔，
逐条记账。礼貌红线违反 = FAIL。

## 1. 方法

`https://data.sec.gov/submissions/CIK{10位}.json` 返回 recent filings（form/type/filingDate）。
- 每个对象实体：定位其申报壳 CIK（第一轮报告/公开常识给起点，如 Icahn 企业族需找准其 13F
  申报壳），拉 submissions，看近 8 个报告季的 13F-HR 出现情况 → 判 PASS（活跃连续）/
  FAIL（停报/无 13F）。
- Southpoint 二壳 0001319998：同法，确认其是否 13F-HR 活跃壳（若仍是纯 NT 或空窗 →
  BORDERLINE 维持；若活跃 HR → 升级候选待规格闸门重验）。
- 需要 CIK 发现时用 data.sec.gov 的 company_tickers.json（同主机，1 次请求）或已知起点。

## 2. 交付

更新证据文件（同目录新文件，不覆盖轮 1）：
- `reports/design/2026-08-27-stars-candidates-evidence-round2.md`
- `reports/design/2026-08-27-stars-candidates-evidence-round2.json`
每对象：CIK/壳判定/近 8 季 13F-HR 序列/verdict（PASS|FAIL|STILL-UNVERIFIED，附证据字符串）/
是否改变轮 1 结论。诚实空结果合法。一个原子 commit。

## 3. 铁律与报告

零生产代码/导出/前端改动；0 ledger/frozen/config/prereg/OOS；不 push；不动主仓与 wj。
报告：(a) 请求数记账；(b) 五对象 verdict 表（含对轮 1 的修订）；(c) 若出现新 PASS 候选 →
只列证据，**不做准入**（准入仍走规格 §2-4 裁决）。
