# 数据接入 7 门 — EDGAR DEF 14A 代理委托书申报流

> **状态**：**v0.1 · 2026-08-23** · exploratory-only display module。
> **范围**：EDGAR DEF 14A 申报数据通过 7 门强制清单，所有第三方数据集进 Aionis 前 **必须** 全部过关。
> **引用**：主 rubric 见 `docs/data-intake-rubric.md`。本文档为 EDGAR DEF 14A 流（`/executives` 面板 DEF 14A section）专用准入评估。

---

## 数据源概述

**SEC EDGAR DEF 14A**（definitive proxy statement，股东大会代理委托书）是董事会/高管治理维度的法定节点文件：董事提名、高管薪酬、受益持股表、股东大会表决事项的法定载体。与 form4/8-K 的按发行人查询不同，本模块采用 **EFTS form 级全市场查询**（无 `ciks=` 参数，与 `form_ipo` / `form_d` 同模式）。

**实测查询**（2026-08-23 live probe，窗口 2026-04-25..2026-08-23，~120 天）：

- `forms=DEF%2014A`（root form，空格 URL 编码照 `form_ipo`）：**1,387 份**，1,351 个发行人 CIK——远低于 EFTS 10,000 上限（未触发自适应切分）。
- 抽样页（`from=0` 与 `from=700`）**全部** `form == "DEF 14A"`（`root_forms == ["DEF 14A"]`）。
- **直接查 `forms=DEF 14A/A` = 0 份**：本窗口无 DEF 14A 修正件——实务中代理委托书补充/修正以 **DEFA14A**（additional proxy soliciting material，**独立 root form**，本窗口 2,278 份）提交，**不在 v1 范围**。状态映射保留 `DEF 14A/A → amendment` 纵深防御臂（照 form_d 的 D/A 臂），fetch 全量装配的 by_form（`{'DEF 14A': 1387}`）确认窗口内 0 修正件。
- 1,043/1,387 行（75%）自 `display_names` 解析出 ticker（`display_symbols` 实测恒为 null）；无代码者如实留空。

---

## G1 — License allowlist（许可协议白名单）

### 结论：✓ **PASS**

- **规则**：仅 MIT / Apache-2.0 / BSD-2/3-Clause / CC0 / CC-BY-4.0（数据）。
- **来源**：SEC EDGAR 数据为 **US Government public domain**（17 U.S.C. §105），无版权限制。
- **通过**：DEF 14A = US federal government data → public domain ✓（同 form4/13D/13F/8-K/Form D 判例）。

---

## G2 — PIT / as-of 时点（point-in-time）

### 结论：✓ **PASS**

- **机制**：EDGAR EFTS `file_date`（申报日）为市场实际可得时点；市场仅在 `file_date` 后才可知该代理委托书已提交。
- **实现**：`form_def14a.py:fetch_form_def14a_filings()` 返回 `filed_date` 作为 PIT anchor（与 form4/13D/8-K/Form D 同一纪律）。

---

## G3 — No-revision contract（无回改契约）

### 结论：✓ **PASS**

- **机制**：代理委托书一经提交不可回改；修正为 **新 accession** 的新 filing（DEF 14A/A 或 DEFA14A），绝不静默覆盖。
- **实现**：`efts_def14a_{start}_{end}.json` 缓存 raw hit list，可复现；accession 去重防御跨页/跨切分半窗重复。

---

## G4 — Reproducibility / snapshot discipline（可复现）

### 结论：✓ **PASS**

- 每窗口一层幂等 EFTS 缓存，重跑零 HTTP；`form_def14a_aggregate.parquet` accession 去重后写出（fetcher 种子合并照 `form_ipo_fetch`）。
- 状态推导（`def14a_status`）与 display 解析（`_parse_company` / `parse_ticker`，复用 form_ipo 纯函数）为纯函数；面板契约由 `tests/test_web_terminal_data.py::test_form_def14a_panel_contract` 锁定。

---

## G5 — Exploratory-only 边界

### 结论：✓ **PASS**

- **display-only / mode=exploratory**：仅进终端 `/executives` 面板 DEF 14A section 与静态数据 API（`def14a.json`）。
- **绝不进研究管线**（features/eval/OOS）；无 frozen claim 依赖此数据。绝不请求/爬取任何竞品站——数据一律一手公共源（SEC EDGAR）。

---

## G6 — Selection honesty（选择诚实）

### 结论：✓ **PASS（披露限制）**

- **v1 诚实降级**（面板 methodology 明示，不编造）：
  1. **董事/高管姓名、薪酬、受益持股在委托书正文 HTML 内（每份数千行），v1 不解析不提取**——人级解析 DEFERRED；逐份解析需 ~1,400 个额外请求（全窗），为保持礼貌而降级。每行链至该 filing 的 EDGAR index 页（列出全部文档）。
  2. **修正件为 0 是事实非猜测**：直接探测 `DEF 14A/A` = 0，修正实为 DEFA14A（2,278 份，独立 root form）——**范围外披露**，不混入。
  3. **ticker 自 display_names 解析**；~25% 发行人 EDGAR 名称不含代码，如实留空，绝不猜测。
  4. 计数为 **filing 计数**非公司计数；DEF 14A 体量强季节性（Jan-Apr 代理季），固定锚窗口只增不减，终将逼近 10k 上限——fetch 已内置 form13f_dir 式自适应切分（当日探测未触发）。
  5. 可见行 cap 600 最新（载荷上限），`total`/`by_form` 计全窗（1,387）——cap 在面板 limit_note 披露。

---

## G7 — Politeness（礼貌抓取）

### 结论：✓ **PASS**

- 复用 `_policy_get`（≥2s host spacing + transient-only 退避重试；经 `form4_efts._get_json`）+ **页间显式 `sleep 2.1s`**（照 form13f_dir）。
- **请求账（2026-08-23 v1 首轮）**：探测 4 个 EFTS 页 GET（DEF 14A from=0 / DEF 14A/A 直查 / DEFA14A from=0 / DEF 14A from=700）+ fetch 14 页 GET（1,387 hits ÷ 100/页）= **共 18 个请求**，纯元数据查询，无逐文档抓取。
- 固定窗口锚 `START=2026-04-25`（~120 天，照 ipo 锚），`END=today` 滚动；幂等缓存使日更仅抓增量页。

---

## 附：状态推导表（行级，法定文件类型 → 状态）

| form | status | 依据 |
|---|---|---|
| `DEF 14A` | `new`（新申报） | 新的 definitive proxy statement 已提交 |
| `DEF 14A/A` | `amendment`（修正） | 纵深防御臂——修正 = 新 accession；本窗口实测 0 份（修正实走 DEFA14A，范围外） |
