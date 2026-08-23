# 数据接入 7 门 — 国会政客交易（STOCK Act · House PTR 申报流）

> **状态**：**v0.1 · 2026-08-21** · exploratory-only display module · **申报流级（filing-stream）**。
> **范围**：STOCK Act 政客交易数据通过 7 门强制清单。
> **引用**：主 rubric 见 `docs/data-intake-rubric.md`。本文档为政客交易专用准入评估 + 端点尽调记录。

---

## 端点尽调（2026-08-21 真实探针留证）

| 源 | 探针结果 | 机器可读度 |
|---|---|---|
| **House Clerk 批量索引（v1 数据路径）** `public_disc/financial-pdfs/{YYYY}FD.zip` | 日更重发的全年申报索引 ZIP（2026 实测 56KB），内含 `{YYYY}FD.xml`：Prefix/Last/First/Suffix/FilingType/StateDst/Year/**FilingDate**/DocID；`FilingType=P` 即 PTR（2026 年 359 件） | **申报流级 + 真实申报日**（1 请求/年） |
| House 搜索 UI（备用，已验证不用） | CSRF-token POST 返 HTML 行（无申报日字段） | 逊于批量索引 |
| （交叉验证）并发 session 尽调 `agent/politician` a2f719b 独立探得同批端点 + house.gov 议员目录（党派 join 一手源） | — | 两路独立探针结论一致 |
| **Senate eFD** `efdsearch.senate.gov` | 普通 GET 即 **Akamai `Access Denied`（403）** | **blocked**——诚实披露，不引入第三方绕过 |
| 第三方 API（FMP/EODHD/Parse.bot/capitoltrades 等） | 提供 JSON 化政客交易 | **G1 挂**（付费/闭源 license），禁用 |

**结论**：v1 = House PTR 申报流（议员/选区/**申报日**/年/PDF 原文链，来自批量 FD.xml），**不解析 PDF、不编造金额/ticker/交易日期**；迟报天数（>45 天法定线）需交易日期，不可计算，如实不展示。对照小隐寺 /congress 的交易级字段（金额区间/动作/迟报 ⚠），其数据来自"SEC 及其他第三方非公开数据库"——Aionis 以一手公共源诚实降级为申报流级，这是 license 纪律的代价，也是差异化。

---

## G1 — License allowlist（许可协议白名单）

### 结论：✓ **PASS**

- House Clerk = **U.S. federal public domain**（政府作品，同 SEC EDGAR 判例）。
- 不消费任何第三方聚合站/API（其 license 不透明或付费）。

---

## G2 — PIT / as-of 时点（point-in-time）

### 结论：✓ **PASS**

- 批量 FD.xml 携带 **FilingDate（as-filed 申报日）**——与 form4/13D/8-K 同一 filed-date 纪律。
- 交易明细不可得 → 无任何 t 时刻可用的交易级信息被展示。

---

## G3 — No-revision contract（无回改契约）

### 结论：✓ **PASS**

- PTR PDF 为永久存档（`public_disc/ptr-pdfs/<year>/<id>.pdf` 路径不可变）。
- 修正案（PTR Amendment）为**新 PDF 新条目**，不静默覆盖。

---

## G4 — Reproducibility / snapshot discipline（可复现）

### 结论：✓ **PASS**

- 每年 **1 个礼貌请求**（FD.zip），按年缓存 parquet，重跑零 HTTP。
- XML 解析为纯函数（`parse_fd_xml`），hermetic fixture 锁定（含真实 2026-08-21 响应形状：P/C/X/W/D/A/T/H 类型码实测分布）。

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

- FD.zip 下载过 `HttpRequestPolicy`（≥2s host spacing + 线性退避 transient-only 重试）。
- 实测冷拉：2 请求（2 年各 1）约 4 秒。

---

## 升级路径（后议，非本轮）

1. **PDF 解析**：House PTR PDF 的文本层解析（资产/金额档/交易日期/迟报天数）——工程量大，且纯官方源；待业主裁决是否投入。（并发 session 尽调称 PDF 为 stdlib 可解文本层，未验证。）
1b. **党派 join**：house.gov/representatives 目录（姓名/州选区/党派）——官方一手源，把 /congress 升级为带党派徽章。
2. **Senate 解封**：Akamai 403 需不同网络出口或官方替代端点出现；持续监控，不绕过。
3. 行政官员披露（第三源）未探针，留待需要时。


---

## 附 2：党派 join 源（house.gov 议员目录，2026-08-22 增补）

- **源**：`https://www.house.gov/representatives`（全体现任议员 HTML 目录，公共域，1 请求缓存为 `data/cache/house_directory.parquet`）。
- **解析**：页面存在**两种行序**（姓名在前含全称选区 "Alabama 4th" / 序数在前 "4th"），双正则并集按 (office, name) 去重；州名取表 caption，序数取选区末 token，At-Large → `00`。
- **join 键 = 选区码 + 姓氏双重佐证**：FD 索引含候选人/前议员申报人，仅按选区 join 会把现任党派错配给他们——姓氏不一致即诚实 null。精确字符串匹配（casefold），无模糊。
- **实测**（2026-08-22）：目录 430 席（218 R / 211 D / 1 I）→ 874 份申报 join 上 806 份；未链接 68 = 前议员/补选过渡（如 McCormick GA06、Menefee TX18）——按设计诚实留空。
- **7-gate 快评**：G1 公共域 ✓；G2 快照语义（当前目录 vs 历史申报，姓氏双键消除错配）✓；G7 单请求 ✓。

---

## 交易级增补（2026-08-23，TASK-S / D4 业主指令"彻底对齐颗粒度"）

**数据链**：申报流面板的 DocID → `disclosures-clerk.house.gov/public_disc/ptr-pdfs/{YYYY}/{DocID}.pdf`
→ 纯 stdlib 解密（ISO 32000 Algorithms 3.2/3.4 RC4 + ToUnicode CMap 文本恢复，右锚定行解析）
→ `data/cache/politician_trades_tx.parquet`（幂等 per-DocID PDF cache）。

**诚实覆盖（2026 全量实测）**：361 份 PDF = 299 可解析（**2,812 笔交易 / 94 议员**）+ 43 no-text
（扫描件，列出 DocID）+ 33 exchange 类排除 + 54 解析失败（候选−行−排除，披露不静默丢）。
金额为法定 $ 区间非精确值；`days_late = 申报日 − 交易日`（45 天法定钟，>45 标 ⚠；实测 379 笔迟报）。

**礼貌账**：PDF 逐份 ≥2s 间距（共享 policy）；--minutes 硬预算断点续存；361 份全量一轮 ≈ 12 分钟
（PDF cache 命中后 0 请求）。无第三方库、无竞品站请求（一手公共域）。
