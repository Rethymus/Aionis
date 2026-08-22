# 数据接入 7 门 — EDGAR 13G 被动持仓申报流（SC 13G / SC 13G/A）

> **状态**：**v0.1 · 2026-08-22** · exploratory-only display module。
> **范围**：EDGAR SC 13G 被动持仓申报数据通过 7 门强制清单，所有第三方数据集进 Aionis 前 **必须** 全部过关。
> **引用**：主 rubric 见 `docs/data-intake-rubric.md`。本文档为 EDGAR 13G 流（`/smart-money` 面板"13G 被动流"卡）专用准入评估。

---

## 数据源概述

**SEC EDGAR SC 13G / SC 13G/A** 是 §13(d) 持股超 5% 时的**被动**申报（申报人声明无控制/激进意图——指数基金、安静机构；13D 则为主动/激进申报）。与 form4/8-K/IPO 的 EFTS 路径不同，本模块走 **EDGAR daily crawler index**（`crawler.{YYYYMMDD}.idx`）：

**为何不是 EFTS**（2026-08-22 live probe，勿重推导）：

- `forms=SC 13G`（root form，引擎同 `SC 13D`，展开含 `SC 13G/A`）对 **2025/2026 全部窗口返回 0 hits**（含 2026-04-25..08-22 整窗）。
- 同查询对 2024-01-01..2024-12-17 返回 >10,000 hits，`file_date` 封顶 **2024-12-17**——EFTS `search-index` 对整个 Schedule 13 家族冻结（`aionis-edgar-efts-sc13d-frozen`；13D 面板撞的是同一堵墙，先例解法即 daily index）。
- EFTS 无法提供近期 13G 窗口；daily crawler index 是现行 dissemination feed，每营业日一份全量清单。

**daily index 结构**（按公司名组织，一 filing 列于**每个**关联公司名下——标的与申报人实体都入索引；实测 accession `0000919574-26-005663` 同时列于 Catheter Precision, Inc.（标的）与 C/M CAPITAL PARTNERS, LP（申报人））。导出层按 accession 分组、离线解析标的/申报人（与 13D daily 路径同一启发式，见 G6）。

**实测拉取**（2026-08-22 首轮，窗口 ~120 天）：见 `stakes_13g.json`（约 3,000+ filings / ~2,000+ accessions 量级，仅 ~85 个每营业日请求）。

---

## G1 — License allowlist（许可协议白名单）

### 结论：✓ **PASS**

- **规则**：仅 MIT / Apache-2.0 / BSD-2/3-Clause / CC0 / CC-BY-4.0（数据）。
- **来源**：SEC EDGAR 数据为 **US Government public domain**（17 U.S.C. §105），无版权限制。
- **通过**：SC 13G/G-A = US federal government data → public domain ✓（同 form4/13D/13F/8-K/IPO 判例）。

---

## G2 — PIT / as-of 时点（point-in-time）

### 结论：✓ **PASS**

- **机制**：daily crawler index 的 dissemination `date`（申报日）为市场实际可得时点；市场仅在申报日 disseminate 后才可知该事件。
- **实现**：`stakes_13g.py:parse_daily_13g()` 返回 `date`（YYYY-MM-DD）作为 PIT anchor（与 13D daily 路径同一纪律）。

---

## G3 — No-revision contract（无回改契约）

### 结论：✓ **PASS**

- **机制**：13G 申报不可回改；修正（SC 13G/A）为 **新 accession** 的新 filing，绝不静默覆盖。
- **实现**：`daily_idx_{yyyymmdd}.txt` 每日幂等缓存 raw index 文本（与 13D cron 共享）；`sc13g_daily_aggregate.json` 可再derive；export 按 accession 分组天然去重。

---

## G4 — Reproducibility / snapshot discipline（可复现）

### 结论：✓ **PASS**

- 每营业日一层幂等缓存（`daily_idx_*.txt`），重跑零 HTTP；fetch 脚本有界（trailing ~120 天窗口）、可续（只抓未缓存日）。
- 解析（`parse_daily_13g`）为纯函数，hermetic 测试锁定（`tests/test_stakes_13g.py`）；导出契约锁定于 `tests/test_web_terminal_data.py`。

---

## G5 — Exploratory-only 边界

### 结论：✓ **PASS**

- **display-only / mode=exploratory**：仅进终端 `/smart-money` 面板"13G 被动流"卡与静态数据 API（`stakes_13g.json`）。
- **绝不进研究管线**（features/eval/OOS）；无 frozen claim 依赖此数据。

---

## G6 — Selection honesty（选择诚实）

### 结论：✓ **PASS（披露限制）**

- **v1 诚实降级**（面板 methodology 明示，不编造）：
  1. **持股比例 / 股数 / 事件日期 / 被动-主动-清仓状态机在申报文档内部，v1 不提取**——逐 accession 解析需数千个额外 `index.json` 请求（全窗），为保持日更 lane 礼貌而 **明确 deferred**（写进 methodology）；每行链至该 filing 的 EDGAR index 页（列出全部文档并载明申报人）。
  2. **标的/申报人解析为离线启发式**：一 accession 组内恰有一个可解析 ticker 的上市公司 → 它是标的，其余入索引名为申报人；零个或多个 → 全部成员诚实保留（占位申报人 / null ticker，计入 `data_health.source_health`）。
  3. **ticker 自缓存 SEC company_tickers 快照离线回填**（当前快照 display label，非 as-of-filing——仅供展示与股票页跳转，绝不作研究输入）；解析不了如实 null。
  4. 计数为 **filing 计数**非持有人计数（被动机构常一标的多份 13G/A）。
  5. daily index 将 13G 列于每个关联公司名下——原始行数为 (accession × 公司) 计数；面板按 accession 分组去重，**双方上市公司/无法判别的组按成员诚实保留**（行数可略超 distinct-accession 数，methodology 明示）。

---

## G7 — Politeness（礼貌抓取）

### 结论：✓ **PASS**

- 复用 `_policy_get`（≥2s host spacing + transient-only 退避重试，经 `stakes_13d_daily_index.fetch_daily_crawler_index`）；与 13D cron **共享**每营业日缓存（`daily_idx_*.txt`），双面板零重复请求。
- 实测首轮冷拉：~120 天 ≈ 85 个营业日 = **85 个请求**（纯元数据索引，无逐文档抓取）；每失败日跳过不重试轰炸（cron 次日补洞）。
- 窗口为 trailing ~120 天滚动锚，幂等缓存使日更仅抓 1 个新营业日。

---

## 附：与 13D（smart_money 主卡）的关系

| | 13D（已有） | 13G（本模块） |
|---|---|---|
| 意图 | 主动/激进（§13(d) + 控制计划） | **被动**（无控制意图声明） |
| 量级 | ~570 笔/120天（xiaoyinsi 口径） | ~3,860 笔/120天（被动为主） |
| 来源 | EFTS 历史 + daily index 近期 | **daily index**（EFTS 对 Schedule 13 冻结） |
| 解析深度 | filing 级 + filer 解析 | filing 级 + filer 解析（同一启发式） |
| 状态机 | 无 | 无（**deferred**，需逐文档解析） |
