# A 股基本面源 7-gate 裁决（Option A′ gate 4）

> 日期：2026-08-03
> 类型：设计笔记（**PROPOSED**，非 ADR、非冻结）
> 解决：Option A′ **gate 4**（A 股 filed-date 基本面源）—— baostock 已证 G3 结构性不可合规（POC §2.5）。
> 方法：3 个后台研究 agent 因 `[1210]` 全失败（opus/sonnet/haiku 子代理今天不可用）；orchestrator 直接 exa 调研。
> 关联：[`2026-08-03-qlib-dualregion-poc.md`](../2026-08-03-qlib-dualregion-poc.md) §2.5、[`data-intake-rubric.md`](../../docs/data-intake-rubric.md)、[`data-license-allowlist.md`](../../docs/data-license-allowlist.md)、[`2026-08-03-track-c-prereg-skeleton.md`](2026-08-03-track-c-prereg-skeleton.md) §3 ③。

## 0. 裁决（PROPOSED）

**cninfo.com.cn（巨潮，证监会指定官方披露平台 = A 股 EDGAR 等价物）是 G2/G3 合规的 A 股基本面源**——
披露日（`ann_date`）原生、as-filed PDF（原始申报值）、修订以**新公告**形式存在（更正公告单独保留）→
天然 revision-transparent。通过 OSS 爬虫（license 待验）+ Aionis PIT 对齐适配，**gate 4 可解**。

baostock = reject（G3 结构性失败，已证）；Tushare = fallback（PIT 可重建但 G1 付费/ToS 风险）。

## 1. 三候选 7-gate 对比

| 源 | G1 license | G2 PIT(申报日) | G3 no-revision | G7 politeness | 裁决 |
|---|---|---|---|---|---|
| **baostock** | MIT（包）✅ | ✗ 期末键，无 as-of | ✗ **结构性失败**（POC §2.5） | baostock.com login | **reject（headline）** / exploratory-only（EPU 先例） |
| **Tushare** | ⚠️ 付费服务 + ToS（**非 permissive**） | ✅ `ann_date`+`f_ann_date`+`report_type=5`(as-filed) | ✅ `disclosure_date.modify_date` 修订追踪 | 120/min(免费)/200+/min(付费) | **PIT 可重建但 G1 风险** → fallback / 仅 exploratory |
| **cninfo（巨潮）** | ⚠️ 爬虫 license 待验；cninfo 数据 = CSRC 指定公开披露 | ✅ **申报日原生**（公告 `ann_date`） | ✅ **修订=新公告**（更正公告单独存在，as-filed PDF 保留） | ⚠️ 有反爬（JA3/TLS 指纹），需 ≥2s + backoff | **G2/G3 合规**（A 股 EDGAR 等价）→ **headline 可行**（待 G1/G7 落实） |

## 2. cninfo 路径的复用轮子（reuse-first，不重造）

| 轮子 | 提供 | leakage gotcha |
|---|---|---|
| `alicexl/a-share-financials` | cninfo PDF → 结构化财报 → SQLite + 杜邦/Altman-Z/TTM 排雷 | PDF 解析覆盖 95%+；老报告/特殊行业可能缺字段；**license 待验** |
| `rollysys/use_cninfo` | cninfo 公告抓取（`hisAnnouncement/query`）+ PyMuPDF markdown + `ann_date` + 缓存 + Claude Code skill | pageSize 服务端硬限 30；部分老 PDF URL 404；扫描件无 OCR；**license 待验** |
| `tr1st7an/CnInfoReports` / `531014023/Giant_Tide_Announcement_Download` / `Shih-yenh-suan/scrape-cop-reports-CnInfo` | 批量公告下载 + 分页 + 断点续爬 | 多线程需控速（G7）；**license 待验** |

**适配点（Aionis 化）**：把爬虫的 as-filed PDF/结构化值接入 `features/fundamentals.py:pit_align`（`align_on="filed"`，与美股 EDGAR 同范式）+ snapshot+sha256（G4）+ ≥2s politeness（G7）+ exploratory 标记直至 G1 落实。

## 3. 待落实（进入 Track C headline 前）

1. **G1（已验 2026-08-03）**：`rollysys/use_cninfo` = **MIT ✅（fetch + PyMuPDF markdown 轮子可用）**；`alicexl/a-share-financials` **无 LICENSE（main + master 均 404）→ G1 fail，不可采用**。→ PDF→结构化数值解析须 **Aionis 自建**（复用 PyMuPDF MIT 工具 + 项目特定解析逻辑，属"适配"非"造轮子"）或 intake 时另找 permissive 轮子。**cninfo 数据 ToS 已验（2026-08-03 S0 前置）**：cninfo = **CSRC 指定官方披露门户**（深圳证券信息有限公司/SZSE 子公司）；公告 = 法定公开 filing；但**数据"产品"需授权**（"合法信息提供商" license，`szsi.cn/cpfw/fwsq/hq/xxsj/jcxx.htm`）；`robots.txt`=404（无）；爬虫生态用 `curl_cffi` JA3 指纹规避反爬（CNInfoHedgeCrawler）→ **Aionis 不越线**。⇒ **G1/G6 处置 = exploratory-only + 禁再分发**（Reddit/PRAW 先例），礼貌抓取 ≥2s（G7），**禁反爬规避**。**⚠️ owner G1 严格度判断（冻结 Track C 后的新信息）**：「CSRC 公开 filing + 个人研究 + 禁再分发」是否过 G1 进 **headline**，还是 **A 股基本面降 exploratory-only**（→ Track C headline 收窄为「US-rank-IC + A 股 exploratory 条件化」，**可能需 config 修订 = 新 ledger 行 #47**）。
2. **G7**：礼貌抓取（≥2s + 指数 backoff；爬虫自带 delay 配置）；反爬规避用合规手段（不要 JA3 伪造越线）。
3. **G4**：每次抓取 snapshot+sha256 入 `data/cache/`（与 EDGAR/ALFRED 同），rerun 零 HTTP。
4. **解析覆盖**：PDF→结构化的字段覆盖（尤其老报告/金融业）需评估；缺失字段 fail-closed。
5. **历史深度**：cninfo 公告历史可达性（2000+？2010+？）决定 A 股 headline 窗口。

## 4. 对 Option A′ 的净影响

- **gate 4 可解**：A 股 headline 基本面**可行**（cninfo 路径），**不需要**把 A 股整体降为 exploratory-only。
- 这**进一步削弱批判者 REJECT**（其 #1 baostock G3 指控对 baostock 成立，但 Option A′ 换 cninfo 即解）。
- Track C §3 ③ 从 "🚨 关键 TBD" 升级为 "✅ 解决方向：cninfo（待 G1/G7 落实）"。

## 5. 不越界声明

- PROPOSED 设计；未触冻结面/ledger/prereg/ADR/config/结果/E3。
- 未连 cninfo.com.cn（仅 exa 调研爬虫/docs）；未跑抓取脚本。
- 爬虫 license 未验前，不主张采用，只作候选 + 适配方向。
- 进入 Track C headline 前须落实 §3 的 G1/G7/G4/解析/历史深度。
