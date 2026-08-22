# 数据接入 7 门 — EDGAR Form 8-K（重大事件申报）

> **状态**：**v0.1 · 2026-08-21** · exploratory-only display module。
> **范围**：EDGAR Form 8-K 重大事件数据通过 7 门强制清单，所有第三方数据集进 Aionis 前 **必须** 全部过关。
> **引用**：主 rubric 见 `docs/data-intake-rubric.md`。本文档为 Form 8-K 专用准入评估。

---

## 数据源概述

**EDGAR Form 8-K**（Current Report）是美国 SEC 要求上市公司在发生重大事件（material events）后 **4 个工作日内** 必须提交的当期报告。法定的 Item 分类体系即事件本体论：`2.01` 完成收购/处置、`2.02` 业绩公告、`3.01` 退市/摘牌通知、`5.02` 董事/高管变动、`4.02` 财报不可依赖（重述）等。本模块 = EFTS 近窗检索 + 主文档抓取 + Item 正则分类（分类是法定申报结构的机械映射，非主观判断）。

---

## G1 — License allowlist（许可协议白名单）

### 结论：✓ **PASS**

- **规则**：仅 MIT / Apache-2.0 / BSD-2/3-Clause / CC0 / CC-BY-4.0（数据）。
- **来源**：SEC EDGAR 数据为 **US Government public domain**（17 U.S.C. §105），无版权限制。
- **通过**：Form 8-K = US federal government data → public domain ✓（同 form4/13D/13F 判例）。

---

## G2 — PIT / as-of 时点（point-in-time）

### 结论：✓ **PASS**

- **机制**：EDGAR EFTS `file_date`（申报日）为市场实际可得时点；Item 内容虽描述既往事件，市场仅在 `file_date` 后才可知。
- **实现**：`form8k.py:fetch_form8k_events()` 返回 `filing_date` 作为 PIT anchor（与 form4/13D 同一纪律）。

---

## G3 — No-revision contract（无回改契约）

### 结论：✓ **PASS**

- **机制**：8-K 申报不可回改；修正（Form 8-K/A）为 **新 accession** 的新 filing，绝不静默覆盖。
- **实现**：`efts_form8k_<cik>_<start>_<end>.json` 缓存 raw hit list，可 sha256 复现。

---

## G4 — Reproducibility / snapshot discipline（可复现）

### 结论：✓ **PASS**

- EFTS + per-accession（index.json / 主文档）三层幂等缓存，重跑零 HTTP。
- 分类器（`extract_8k_items` / `classify_8k`）为纯函数，hermetic 测试锁定（`tests/test_form8k.py`）。

---

## G5 — Exploratory-only 边界

### 结论：✓ **PASS**

- **display-only / mode=exploratory**：仅进终端 `/events` 面板与静态数据 API。
- **绝不进研究管线**（features/eval/OOS）；无 frozen claim 依赖此数据。

---

## G6 — Selection honesty（选择诚实）

### 结论：✓ **PASS（披露限制）**

- v1 宇宙 = 与 form4 相同的 5 大盘发行人（AAPL/MSFT/NVDA/GOOGL/AMZN），面板 methodology 与 data-health 明示。
- **v2 广度扩展（2026-08-22，浏览器实探驱动）**：5 → 25 家高流动性大盘（新 20：JPM/BRK-B/V/MA/UNH/JNJ/PFE/MRK/LLY/WMT/HD/KO/PG/CVX/BA/AVGO/CSCO/META/TSLA/XOM）。**仍是有界宇宙非全市场**——与竞品 /events 的全市场流的差距如实保留在 methodology。XOM 双 CIK 特例：Exxon Mobil Corp (34088) 至 2026-07-01 持股公司继承，之后由 ExxonMobil Holdings Corp (2115436，经 8-K12B 注册) 续报——两条都保留（accession 全局唯一，去重不碰撞），已对 submissions 实查验证。CIK 来自 SEC company_tickers.json 快照（cik_resolver 机制）。
- 分类覆盖诚实计数：`unclassified`（无法抽取 Item 的文档）与 `other`（Item 存在但未映射）显式计数，不隐藏不猜测。

---

## G7 — Politeness（礼貌抓取）

### 结论：✓ **PASS**

- 复用 `_policy_get`（≥2s host spacing + 指数退避，transient-only 重试）。
- 实测首轮冷拉：23 份 filing ≈ 51 请求（5 EFTS + 23 index + 23 doc），约 2 分钟。
- **v2 礼貌账**：26 CIK 条目 × 1 EFTS 查询 + 每新 filing 2 请求（index.json + 主文档）。冷拉全量估算 ≈ 26 EFTS + 2×N filings（N ≈ 数百）× ≥2s 间距 ≈ 15-30 分钟；per-accession 缓存令重跑近零请求。断点续存（逐发行人 checkpoint 落盘）。
- 主文档选择器为评分制（exhibit/XBRL 渲染件排除），曾抓错 R1.htm/ex991/q1fy27pr.htm 的三次迭代均有缓存作废重拉验证。

---

## 附：主文档选择器（评分制）

| 分 | 判定 | 例 |
|---|---|---|
| 0 | 主文档规范：发行人-日期命名 或 名含 8-k/8k | `nvda-20260818.htm`、`d171253d8k.htm` |
| 1 | 其他非 exhibit .htm | `q1fy27pr.htm`（仍可能是 press release，仅在无 0 分时兜底） |
| 2 | XBRL 渲染件 `R\d+` | `R1.htm`（IDEA render，无 Item 文本） |
| 3 | exhibit（名含 `ex<digits>`） | `ex991.htm`、`a8-kex991q3.htm`（名内 8-k 骗不过 exhibit 检查） |

Item 抽取同时清洗 nbsp（`&#160;`/`&nbsp;`）与 thin-space（`&#8201;`/`&#8202;`/`&#8203;`）实体——SEC iXBRL 时代渲染用 thin space 分隔 `Item 2.01`。
