# 数据接入 7 门 — EDGAR 13G 被动持仓申报流（SC 13G / SC 13G/A）

> **状态**：**v0.2 · 2026-08-23** · exploratory-only display module。v0.2 增补：持股比例**第二阶段有界文档解析**（`stakes_pct`，13G/13D 两面板可见行）+ 13D cache 重建请求账（见文末"第二阶段"与"请求账"）。
> **范围**：EDGAR SC 13G 被动持仓数据通过 7 门强制清单，所有第三方数据集进 Aionis 前 **必须** 全部过关。
> **引用**：主 rubric 见 `docs/data-intake-rubric.md`。本文档为 EDGAR 13G 流（`/smart-money` 面板"13G 被动流"卡）专用准入评估；13D（smart_money 主卡）的 daily-index 重建与两面板共用的解析阶段一并在此记账。

---

## 数据源概述

**SEC EDGAR SC 13G / SC 13G/A** 是 §13(d) 持股超 5% 时的**被动**申报（申报人声明无控制/激进意图——指数基金、安静机构；13D 则为主动/激进申报）。与 form4/8-K/IPO 的 EFTS 路径不同，本模块走 **EDGAR daily crawler index**（`crawler.{YYYYMMDD}.idx`）：

**为何不是 EFTS**（2026-08-22 live probe，勿重推导）：

- `forms=SC 13G`（root form，引擎同 `SC 13D`，展开含 `SC 13G/A`）对 **2025/2026 全部窗口返回 0 hits**（含 2026-04-25..08-22 整窗）。
- 同查询对 2024-01-01..2024-12-17 返回 >10,000 hits，`file_date` 封顶 **2024-12-17**——EFTS `search-index` 对整个 Schedule 13 家族冻结（`aionis-edgar-efts-sc13d-frozen`；13D 面板撞的是同一堵墙，先例解法即 daily index）。
- EFTS 无法提供近期 13G 窗口；daily crawler index 是现行 dissemination feed，每营业日一份全量清单。

**daily index 结构**（按公司名组织，一 filing 列于**每个**关联公司名下——标的与申报人实体都入索引；实测 accession `0000919574-26-005663` 同时列于 Catheter Precision, Inc.（标的）与 C/M CAPITAL PARTNERS, LP（申报人））。导出层按 accession 分组、离线解析标的/申报人（与 13D daily 路径同一启发式，见 G6）。

**实测拉取**（2026-08-22 首轮，窗口 ~120 天）：见 `stakes_13g.json`（约 3,000+ filings / ~2,000+ accessions 量级，仅 ~85 个每营业日请求）。

**13D 侧 cache 重建**（2026-08-23）：主仓 smart_money 的 13D cache（`efts_13d_*.json` / `sc13d_daily_aggregate.json`）丢失后，以同一 daily-index 路径重建 trailing 120 天（`stakes_13d_daily_index`）：82 个营业日请求重建出 3,402 行 / 1,701 distinct accessions（SC 13D 702 行 + SC 13D/A 2,700 行），面板 recent 重导出至 120 行上限。请求账见文末。

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
- 解析（`parse_daily_13g`）为纯函数，hermetic 测试锁定（`tests/test_stakes_13g.py`）；持股比例解析（`parse`/`extract_pct_now`/`extract_pct_prev`/`pick_primary_doc`）为纯函数 + 幂等 per-accession cache，锁定于 `tests/test_stakes_pct.py`；导出契约（pct ∈ [0,100]、prev 仅修正件、null 容错）锁定于 `tests/test_web_terminal_data.py`。

---

## G5 — Exploratory-only 边界

### 结论：✓ **PASS**

- **display-only / mode=exploratory**：仅进终端 `/smart-money` 面板"13G 被动流"卡与静态数据 API（`stakes_13g.json`）。
- **绝不进研究管线**（features/eval/OOS）；无 frozen claim 依赖此数据。

---

## G6 — Selection honesty（选择诚实）

### 结论：✓ **PASS（披露限制）**

- **v1 诚实降级**（面板 methodology 明示，不编造）：
  1. **持股比例（pct_now / pct_prev）与清仓/降至5%下状态：v0.2 起对两面板可见行（13G 前 150 + 13D 前 120）做有界文档解析**（见文末"第二阶段"），可见窗口之外的行**不解析**（诚实 null，非全窗可得）；**股数与事件日期仍在申报文档内部、不提取**；主动/被动轴由 form 类型零解析推导（SC 13D*→主动 / SC 13G*→被动）。每行链至该 filing 的 EDGAR index 页。
  2. **标的/申报人解析为离线启发式**：一 accession 组内恰有一个可解析 ticker 的上市公司 → 它是标的，其余入索引名为申报人；零个或多个 → 全部成员诚实保留（占位申报人 / null ticker，计入 `data_health.source_health`）。
  3. **ticker 自缓存 SEC company_tickers 快照离线回填**（当前快照 display label，非 as-of-filing——仅供展示与股票页跳转，绝不作研究输入）；解析不了如实 null。
  4. 计数为 **filing 计数**非持有人计数（被动机构常一标的多份 13G/A）。
  5. daily index 将 13G 列于每个关联公司名下——原始行数为 (accession × 公司) 计数；面板按 accession 分组去重，**双方上市公司/无法判别的组按成员诚实保留**（行数可略超 distinct-accession 数，methodology 明示）。

---

## G7 — Politeness（礼貌抓取）

### 结论：✓ **PASS**

- 复用 `_policy_get`（≥2s host spacing + transient-only 退避重试，经 `stakes_13d_daily_index.fetch_daily_crawler_index`）；与 13D cron **共享**每营业日缓存（`daily_idx_*.txt`），双面板零重复请求。
- 实测首轮冷拉：~120 天 ≈ 85 个营业日 = **85 个请求**（纯元数据索引，无逐文档抓取）；每失败日跳过不重试轰炸（cron 次日补洞）。
- 窗口为 trailing ~120 天滚动锚，幂等缓存使日增仅抓 1 个新营业日。
- **第二阶段文档解析**（v0.2）：同样全程 `_policy_get`（≥2s + transient-only 有界重试，`total_attempts=2`）；per-accession 幂等 cache 使 `ok` 行永不重抓；45 分钟硬上限随时中断可续跑。请求账见下节。

---

## 第二阶段：持股比例有界文档解析（stakes_pct，v0.2 · 2026-08-23）

竞品 /stakes 签名特性（"40.5%（前 12.2%）"+ 主动/被动/清仓/降至5%下状态机）的数值**不在任何索引里，只在申报文档内部**。本阶段对**两面板可见行**（13G 前 150 + 13D 前 120，从已提交的 web JSON 读取——解析集永远等于展示集）做有界解析：

- **每行 ≤2 请求**：filing `index.json`（1）→ 选主文档（`primary_doc.xml` 优先，次选传统 `sc13d/sc13g*.htm`，绝不取 EDGAR 生成的 index/exhibit 页）→ 抓主文档（1）。
- **pct_now** 三级优先：结构化封面标签（13D `percentOfClass` / 13G `classPercent`，取第一申报人封面）→ HTML 封面 "Percent of class" 标签 → 正文 "X.X% of the … class/outstanding shares" 语句；[0,100] 外拒绝。
- **pct_prev 仅修正件**（`/A`）：来自 "previous 5.2%" / "previously reported …" / "increased from X% to Y%" 类语句；原始件在任何层都拒绝 prev（解析器 + 导出双层强制）。
- **幂等 cache**：`data/cache/stakes_pct_parsed.json` per-accession 一条；`ok` 行（含诚实抽取 miss）永不重抓，失败行下次重试；45 分钟硬墙钟上限，中断即续。
- **失败诚实计数**：抽不到 = 诚实 null（绝不猜默认值）；fetch 失败按异常类计数；null 率入 `data_health.source_health.pct_now_null`。
- **pct_status 仅由解析值推导**：解析得 0 → `exited`（清仓）；解析得 <5 → `below_5`（降至线下）；null pct → null 状态（无解析就无状态机）。主动/被动徽章由 form 类型直接推导，零解析依赖。
- 覆盖实测（2026-08-23 轮）：13D 面板 **119/120** pct_now 解析（1 个诚实 miss：主文档已取到但无匹配语句）；13G 面板 **150/150**；pct_prev 全轮仅 **1** 行抽到（"previous 20%" 语句；多数修正件用 "from X% to Y%" 变体落在 now 优先级里，如实计数不粉饰）。

## 请求账（2026-08-23 重建 + 解析轮，从 cache 文件数与脚本计数器如实记账）

| 阶段 | 请求 | 依据 |
|---|---|---|
| 13D cache 重建（`sc13d_daily_aggregate` 丢失后 trailing 120 天重建） | **82** 个 daily-index 请求 | `data/cache/daily_idx_*.txt` 共 82 文件（2026-04-27 → 2026-08-21，82 个营业日），全部 mtime 2026-08-23；与 13G 共享缓存零重复 |
| 持股比例解析（两面板可见行） | **≈494**（247 accessions × 2） | `stakes_pct_parsed.json` 247 条全部 `ok`、主文档全部 `primary_doc.xml`；脚本计数器 `n_req += 2 if ok` 同口径 |
| **合计** | **≈576** | 全程 `_policy_get` ≥2s spacing + transient-only 退避（≤1 次重试/请求，未单独计数）；15,982 份 13G 全窗 form 级流、3,402 行 13D aggregate 离线自缓存，零额外请求 |

> 诚实边界：上表为**本轮可核验**的请求数（cache 文件数 + 计数器口径）。前一配额中断的代理轮可能发出过未入 cache 的请求，无法归属核验，不计入。可见窗口（270 行 / 247 distinct accessions）之外的申报**未解析**——全窗逐文档解析需数千请求，明确不做。

---

## 附：与 13D（smart_money 主卡）的关系

| | 13D（已有） | 13G（本模块） |
|---|---|---|
| 意图 | 主动/激进（§13(d) + 控制计划） | **被动**（无控制意图声明） |
| 量级 | ~570 笔/120天（xiaoyinsi 口径） | ~3,860 笔/120天（被动为主） |
| 来源 | EFTS 历史 + daily index 近期 | **daily index**（EFTS 对 Schedule 13 冻结） |
| 解析深度 | filing 级 + filer 解析 | filing 级 + filer 解析（同一启发式） |
| 持股比例 | **可见行有界解析**（v0.2，`stakes_pct`，119/120） | **可见行有界解析**（v0.2，150/150） |
| 状态机 | exited/below_5 仅由解析值推导（12+17 行）；主动/被动由 form 推导 | exited/below_5 仅由解析值推导（9+31 行）；被动由 form 推导 |
