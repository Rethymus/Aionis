# 数据接入 7 门 — 国会政客交易（STOCK Act · House PTR 申报流）

> **状态**：**v0.1 · 2026-08-21** · exploratory-only display module · **申报流级（filing-stream）**。
> **范围**：STOCK Act 政客交易数据通过 7 门强制清单。
> **引用**：主 rubric 见 `docs/data-intake-rubric.md`。本文档为政客交易专用准入评估 + 端点尽调记录。

---

## 端点尽调（2026-08-21 真实探针留证）

| 源 | 探针结果 | 机器可读度 |
|---|---|---|
| **House Clerk** `disclosures-clerk.house.gov` | `ViewSearch` 为 ASP.NET 表单（`__RequestVerificationToken` + 会话 cookie）；POST `ViewMemberSearchResult` 返回 **HTML 表格**（Name+PDF 链 / Office 州选区 / Filing Year / Filing 类型） | **申报流级可解析**（本模块 v1）；交易明细（资产/金额/日期）仅存于 **PDF 内**，列表无申报日字段（仅年粒度） |
| **Senate eFD** `efdsearch.senate.gov` | 普通 GET 即 **Akamai `Access Denied`（403）** | **blocked**——诚实披露，不引入第三方绕过 |
| 第三方 API（FMP/EODHD/Parse.bot/capitoltrades 等） | 提供 JSON 化政客交易 | **G1 挂**（付费/闭源 license），禁用 |

**结论**：v1 = House PTR 申报流（议员/选区/类型/年/PDF 原文链），**不解析 PDF、不编造金额/ticker/交易日期**；迟报天数（>45 天法定线）在列表级数据下不可计算，如实不展示。对照小隐寺 /congress 的交易级字段（金额区间/动作/迟报 ⚠），其数据来自"SEC 及其他第三方非公开数据库"——Aionis 以一手公共源诚实降级为申报流级，这是 license 纪律的代价，也是差异化。

---

## G1 — License allowlist（许可协议白名单）

### 结论：✓ **PASS**

- House Clerk = **U.S. federal public domain**（政府作品，同 SEC EDGAR 判例）。
- 不消费任何第三方聚合站/API（其 license 不透明或付费）。

---

## G2 — PIT / as-of 时点（point-in-time）

### 结论：⚠ **PASS（弱化披露）**

- 列表级仅有 **Filing Year** 粒度（无 filed-date 字段）——弱于本项目惯用的 filed-date PIT。
- PDF 内有真实申报日，但 v1 不解析 PDF。methodology 与面板均明示"年粒度"。
- 交易明细不可得 → 无任何 t 时刻可用的交易级信息被展示。

---

## G3 — No-revision contract（无回改契约）

### 结论：✓ **PASS**

- PTR PDF 为永久存档（`public_disc/ptr-pdfs/<year>/<id>.pdf` 路径不可变）。
- 修正案（PTR Amendment）为**新 PDF 新条目**，不静默覆盖。

---

## G4 — Reproducibility / snapshot discipline（可复现）

### 结论：✓ **PASS**

- 每年 2 个礼貌请求（GET token → POST 结果），结果按年缓存 parquet，重跑零 HTTP。
- HTML 行解析为纯函数（`parse_house_ptr_html`），hermetic fixture 锁定（含真实 2026-08-21 响应形状）。

---

## G5 — Exploratory-only 边界

### 结论：✓ **PASS**

- display-only / mode=exploratory；仅进终端 `/congress` 面板与静态数据 API；绝不进研究管线（features/eval/OOS）。

---

## G6 — Selection honesty（选择诚实）

### 结论：✓ **PASS（披露限制）**

- 覆盖 = **House only**（Senate Akamai-blocked 如实标注于面板）；窗口 = 2025-2026 两年。
- 窗口与单院覆盖在 methodology、data-health、api-catalog 三处一致披露。

---

## G7 — Politeness（礼貌抓取）

### 结论：✓ **PASS**

- GET/POST 均过 `HttpRequestPolicy`（≥2s host spacing + 线性退避 transient-only 重试）。
- 实测冷拉：4 请求（2 年 × GET+POST）约 5 秒。CSRF token 与 cookie 绑定单 `requests.Session`。

---

## 升级路径（后议，非本轮）

1. **PDF 解析**：House PTR PDF 的文本层解析（资产/金额档/交易日期/迟报天数）——工程量大，且纯官方源；待业主裁决是否投入。
2. **Senate 解封**：Akamai 403 需不同网络出口或官方替代端点出现；持续监控，不绕过。
3. 行政官员披露（第三源）未探针，留待需要时。
