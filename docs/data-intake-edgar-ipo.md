# 数据接入 7 门 — EDGAR IPO 申报/定价流（S-1 家族 + 424B4）

> **状态**：**v0.1 · 2026-08-22** · exploratory-only display module。
> **范围**：EDGAR IPO 注册/定价申报数据通过 7 门强制清单，所有第三方数据集进 Aionis 前 **必须** 全部过关。
> **引用**：主 rubric 见 `docs/data-intake-rubric.md`。本文档为 EDGAR IPO 流（`/ipo` 面板）专用准入评估。

---

## 数据源概述

**SEC EDGAR S-1 / S-1/A / 424B4** 是美国证券法注册发行的两类法定节点文件：**S-1 / S-1/A**（注册说明书及其修正）= 发行人已向 SEC 提交上市注册申请（**已申报**）；**424B4**（Rule 424(b)(4) 法定最终招股书）= 定价完成后提交的最终条款文件（**已定价**）。与 form4/8-K 的按发行人查询不同，IPO 是**全市场**问题——申报人在查询时并非已知宇宙——本模块采用 **EFTS form 级查询**（无 `ciks=` 参数，与 `stakes_13d_efts` 的无 CIK 模式同源）。

**实测查询**（2026-08-22 live probe，窗口 119 天）：

- `forms=S-1`（root form）自动展开含 `S-1/A`：**827 份**（S-1 335 + S-1/A 492）。
- `forms=424B4`：**219 份**（无修正家族）。
- 合计 1,046 份 / 484 个发行人 CIK，仅 ~12 个 EFTS 分页请求（页大小 100）。

---

## G1 — License allowlist（许可协议白名单）

### 结论：✓ **PASS**

- **规则**：仅 MIT / Apache-2.0 / BSD-2/3-Clause / CC0 / CC-BY-4.0（数据）。
- **来源**：SEC EDGAR 数据为 **US Government public domain**（17 U.S.C. §105），无版权限制。
- **通过**：S-1 / 424B4 = US federal government data → public domain ✓（同 form4/13D/13F/8-K 判例）。

---

## G2 — PIT / as-of 时点（point-in-time）

### 结论：✓ **PASS**

- **机制**：EDGAR EFTS `file_date`（申报日）为市场实际可得时点；市场仅在 `file_date` 后才可知该注册/定价事件。
- **实现**：`form_ipo.py:fetch_ipo_filings()` 返回 `filed_date` 作为 PIT anchor（与 form4/13D/8-K 同一纪律）。

---

## G3 — No-revision contract（无回改契约）

### 结论：✓ **PASS**

- **机制**：S-1 注册说明书不可回改；修正（S-1/A）为 **新 accession** 的新 filing，绝不静默覆盖；424B4 一次性提交。
- **实现**：`efts_ipo_{form}_{start}_{end}.json` 缓存 raw hit list，可复现；accession 去重防御跨查询重复。

---

## G4 — Reproducibility / snapshot discipline（可复现）

### 结论：✓ **PASS**

- 每个 root-form × 窗口一层幂等 EFTS 缓存，重跑零 HTTP；`form_ipo_aggregate.parquet` accession 去重后写出。
- 状态推导（`ipo_status`）与 display 解析（`_parse_company` / `parse_ticker`）为纯函数，hermetic 测试锁定（`tests/test_form_ipo.py`）。

---

## G5 — Exploratory-only 边界

### 结论：✓ **PASS**

- **display-only / mode=exploratory**：仅进终端 `/ipo` 面板与静态数据 API（`ipo.json`）。
- **绝不进研究管线**（features/eval/OOS）；无 frozen claim 依赖此数据。

---

## G6 — Selection honesty（选择诚实）

### 结论：✓ **PASS（披露限制）**

- **v1 诚实降级**（面板 methodology 明示，不编造）：
  1. **发行价 / 募资额 / 预期上市日在招股书文档内，v1 不提取**——每行链至该 filing 的 EDGAR index 页（列出全部文档）；逐 filing 解析主文档需 ~1,000 个额外 `index.json` 请求（全窗），为保持日更 lane 礼貌而降级。
  2. **424B4 form 级捕获含已上市公司定价增发**（如 S-3 shelf 下架以 424(b)(4) 定价）——本面板是**注册/定价申报流**，非精选 IPO 名单；不做公司级状态机（行级状态：`filed` | `priced`）。
  3. **ticker 自 display_names 解析**（EFTS `display_symbols` 实测恒为 null）；未有代码的 S-1 申报人如实留空（实测 673/1,046 有 ticker，priced 子集 186/219），绝不猜测。
  4. 计数为 **filing 计数**非公司计数（一个 S-1 常伴多份 S-1/A）。

---

## G7 — Politeness（礼貌抓取）

### 结论：✓ **PASS**

- 复用 `_policy_get`（≥2s host spacing + transient-only 退避重试；经 `form4_efts._get_json`）。
- 实测首轮冷拉：**1,046 份 filing 仅 12 个请求**（9 页 S-1 + 3 页 424B4）——纯元数据查询，无逐文档抓取，天然最礼貌。
- 固定窗口锚 `START=2026-04-25`（~120 天），`END=today` 滚动；幂等缓存使日更仅抓增量页。

---

## 附：状态推导表（行级，法定文件类型 → 状态）

| form | status | 依据 |
|---|---|---|
| `S-1` | `filed`（已申报） | 注册说明书已在案 |
| `S-1/A` | `filed`（已申报） | 修正 = 新 accession 的新申报 |
| `424B4` | `priced`（已定价） | Rule 424(b)(4) 法定最终招股书于定价后提交 |
