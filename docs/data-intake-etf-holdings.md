# 数据接入 7 门 — 主题 ETF 官方持仓（theme_etfs / /institutions 板块）

> **状态**：**v0.1 · 2026-08-23** · exploratory-only display module。
> **范围**：10 只主题 ETF 的发行商官方日度持仓文件（iShares/BlackRock + Global X/Mirae Asset）通过 7 门强制清单；所有第三方数据集进 Aionis 前 **必须** 全部过关。
> **引用**：主 rubric 见 `docs/data-intake-rubric.md`；同构先例 = ARK 官方 CSV 面板（`src/aionis/ingest/ark_holdings.py`，`docs/` 内 methodology 披露）。
> **铁律 #0**：全程未请求 参照站 或任何竞品站；数据一律发行商官网公开文件。

---

## 数据源概述

**发行商官方每日全持仓文件**（免费、公开、无需登录；每逢交易日发布，发行商不留历史——本地带日期快照即时间序列，同 ARK 模式）：

| 代码 | 主题 | 发行商 | 官方基金名 | 文件类型 | 已验证 URL 模式（2026-08-23 逐一实下载） |
|------|------|--------|-----------|----------|------------------------------------------|
| SOXX | 半导体 | iShares (BlackRock) | iShares Semiconductor ETF | CSV 直链 | `https://www.ishares.com/us/products/239705/ishares-semiconductor-etf/latest-holdings.csv` |
| ICLN | 清洁能源 | iShares (BlackRock) | iShares Global Clean Energy ETF | CSV 直链 | `https://www.ishares.com/us/products/239738/ishares-global-clean-energy-etf/latest-holdings.csv` |
| ARTY | AI（指数） | iShares (BlackRock) | iShares Future AI & Tech ETF | CSV 直链 | `https://www.ishares.com/us/products/297905/ishares-future-ai-tech-etf/latest-holdings.csv` |
| BAI | AI（主动） | iShares (BlackRock) | iShares A.I. Innovation and Tech Active ETF | CSV 直链 | `https://www.ishares.com/us/products/339081/ishares-a-i-innovation-and-tech-active-etf/latest-holdings.csv` |
| AIQ | AI（广义） | Global X (Mirae Asset) | Global X Artificial Intelligence & Technology ETF | CSV（日期入文件名） | 基金页 `https://www.globalxetfs.com/funds/aiq/` → `https://assets.globalxetfs.com/funds/holdings/aiq_full-holdings_YYYYMMDD.csv` |
| CLOU | 云计算 | Global X (Mirae Asset) | Global X Cloud Computing ETF | 同上 | `.../funds/clou/` → `.../holdings/clou_full-holdings_YYYYMMDD.csv` |
| BKCH | 区块链 | Global X (Mirae Asset) | Global X Blockchain ETF | 同上 | `.../funds/bkch/` → `.../holdings/bkch_full-holdings_YYYYMMDD.csv` |
| LIT | 锂电池 | Global X (Mirae Asset) | Global X Lithium & Battery Tech ETF | 同上 | `.../funds/lit/` → `.../holdings/lit_full-holdings_YYYYMMDD.csv` |
| BOTZ | 机器人 | Global X (Mirae Asset) | Global X Robotics & Artificial Intelligence ETF | 同上 | `.../funds/botz/` → `.../holdings/botz_full-holdings_YYYYMMDD.csv` |
| BUG | 网络安全 | Global X (Mirae Asset) | Global X Cybersecurity ETF | 同上 | `.../funds/bug/` → `.../holdings/bug_full-holdings_YYYYMMDD.csv` |

**链接结构 = API 配置**（同 ARK 先例）：iShares 直链稳定钉死；Global X 日期入文件名，ingest 每次 fetch 基金页并从其 HTML 提取当日 CSV href——重命名/改版表现为诚实的单基金 FAIL，绝不静默。两发行商的列名按名解析（ICLN 比 SOXX 多一列 `Type`），绝不按位置取列。

---

## G1 — License allowlist（许可协议白名单）

### 结论：✓ **PASS（沿用 ARK 先例）**

- **规则**：仅 MIT / Apache-2.0 / BSD / CC0 / CC-BY-4.0（数据）或等价开放数据。
- **来源**：发行商在其官网**主动公开分发**的营销/披露用每日持仓文件（任何人可无条件下载）。持仓明细（ticker、股数、市值、权重）是**事实（facts）**；文件由发行商自愿发布供公众自由使用。
- **边界（诚实）**：基金名称/品牌归发行商所有——面板 methodology 明示归属（issuer 字段逐基金披露），不重新分发原始文件（快照 gitignored），只导出 top-10 聚合 + 计数。

---

## G2 — PIT / as-of 时点（point-in-time）

### 结论：✓ **PASS**

- **机制**：每个官方文件自带 as-of 行（iShares：`Fund Holdings as of,"Aug 20, 2026"`；Global X：`Fund Holdings Data as of 08/21/2026`），解析进每行/面板 `as_of`；快照另带 `snapshot_ts`（ISO-UTC）。
- **实现**：`theme_etfs.py` 的 `parse_ishares` / `parse_globalx` 原样转 ISO；无 as-of 行 = 单基金 FAIL，绝不猜测。

---

## G3 — No-revision contract（无回改契约）

### 结论：✓ **PASS（带如实披露）**

- **机制**：两发行商每日发布新文件、**不留历史**——同 ARK 模式，带日期的本地快照（`data/cache/theme_etfs/<TICK>_<YYYYMMDD>.csv`，gitignored）就是唯一时间序列；同日重跑幂等（同 as-of 覆盖同名快照）。
- **披露**：发行商理论上可对同日文件就地更正（iShares "latest-holdings" 语义即"当前版"）——快照纪律覆盖此风险：本地留存即冻结真相，重拉 = 新快照文件，绝不回改既有日期文件。

---

## G4 — Reproducibility / snapshot discipline（可复现）

### 结论：✓ **PASS**

- 幂等缓存：每基金+日期一快照；重跑 = 16 次礼貌 GET + 覆盖当日文件，网络成本恒定。
- 解析全为纯函数（`parse_ishares` / `parse_globalx` / `parse_any`），fetcher 与导出器共用同一解析器——缓存与 JSON 不会出现行语义分歧；hermetic 契约测试（`tests/test_web_terminal_data.py::test_theme_etfs_panel_contract`）锁定 schema。

---

## G5 — Exploratory-only 边界

### 结论：✓ **PASS**

- **display-only / mode=exploratory**：仅进终端 `/institutions` 页 ThemeEtfsSection 与静态数据 API（`theme_etfs.json`）。
- **绝不进研究管线**（features/eval/ingest of research data/OOS）；无 frozen claim 依赖此数据。今日/昨日快照绝不 PIT、绝不作信号。

---

## G6 — Selection honesty（选择诚实）

### 结论：✓ **PASS（剔除如实记录）**

- **基金选择**：10 只钉死在 `FUND_DEFS`（覆盖半导体/清洁能源/AI×3/云/区块链/锂电/机器人/网络安全；ARK 面板之外的维度，BOTZ/BKCH 为不同发行商的互补项）。`n_funds_expected = 10`；单基金抓取失败 = 诚实缺席（n_funds < 10），绝不补数。
- **剔除记录（找不到免费官方文件的候选，宁缺毋滥）**：

| 候选 | 主题 | 发行商 | 剔除原因（2026-08-23 实测） |
|------|------|--------|------------------------------|
| BLOK | 区块链 | Amplify | 持仓页表格为 JS 渲染，页面源无官方文件直链可提取 |
| PHO / TAN | 水 / 太阳能 | Invesco | 官网改版为 JS SPA，旧持仓端点重定向到产品列表页；无服务端渲染直链 |
| SMH | 半导体 | VanEck | 本网络 TLS 连接被拒（两次，curl exit 35） |
| CIBR / FIW / SKYY | 网络安全 / 水 / 云 | First Trust | 基金页服务端取回为门户首页/不可达，无持仓文件链接可提取 |
| XITK 等 | 创新科技 | SPDR (SSGA) | 仅发布 XLS；钉死 venv 无 openpyxl（本面板约束 CSV-only） |
| QTUM | 量子 | Defiance | 无已知免费官方持仓文件端点（未纳入验证） |

- **行级诚实**：iShares 仅保留 `Asset Class == Equity` 行（期货/现金/FX 腿跳过并计数）；Global X 无 ticker 的现金/FX 记账行跳过并计数；带 ticker 的小额期货腿（如 `NQU6 Index`）按官方权重保留、绝手删。skipped_rows 逐基金披露。

---

## G7 — Politeness / rate limit（礼貌抓取）

### 结论：✓ **PASS**

- **≥2.1s 请求间隔**（fetch_all 每请求间 sleep；另由 `HttpRequestPolicy` 的 `HostSpacingPolicy(min_interval=2.0)` 按主机强制串行）。
- **有界重试**：`RetryPolicy(max_retries=2, backoff_base=2.0)`，仅 429/5xx/网络异常；UA 带 Aionis-Research 联系方式（iShares 端点要求浏览器 UA，故 UA 为浏览器串 + 联系后缀，已实测可用）。
- **稳态请求账**：每 run 共 **16 GET**（iShares 4 文件 ×1 + Global X 6 基金页 ×1 + Global X 6 日期文件 ×1），日更 CI 一次。
- **源考古请求账（2026-08-23，一次性）**：ishares.com ≈13 GET（产品页×7、端点验证×4、失败探测×2）；globalxetfs.com 6 GET（基金页）；assets.globalxetfs.com 5 GET（含 1 次 dateless 404 探测）；invesco.com 1；vaneck.com 2（连接失败）；amplifyetfs.com 2；firsttrust/ftportfolios 2。全部带间隔。

---

## 结论

**7/7 PASS（G1 事实性数据 + 归属披露；G6 剔除记录在案）** — 准入为 **display-only / exploratory**。违反任一门（如把该数据接入研究管线、或静默改 FUND_DEFS 不更新本文档）即失效。
