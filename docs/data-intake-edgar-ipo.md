# 数据接入 7 门 — EDGAR IPO 申报/定价流（S-1 家族 + 424B4）

> **状态**：**v0.2 · 2026-08-26**（TASK-DISP-H3 有界发行价解析；v0.1 · 2026-08-22 原始接入）· exploratory-only display module。
> **范围**：EDGAR IPO 注册/定价申报数据通过 7 门强制清单，所有第三方数据集进 Aionis 前 **必须** 全部过关。
> **引用**：主 rubric 见 `docs/data-intake-rubric.md`。本文档为 EDGAR IPO 流（`/ipo` 面板）专用准入评估。

---

## 数据源概述

**SEC EDGAR S-1 / S-1/A / 424B4** 是美国证券法注册发行的两类法定节点文件：**S-1 / S-1/A**（注册说明书及其修正）= 发行人已向 SEC 提交上市注册申请（**已申报**）；**424B4**（Rule 424(b)(4) 法定最终招股书）= 定价完成后提交的最终条款文件（**已定价**）。与 form4/8-K 的按发行人查询不同，IPO 是**全市场**问题——申报人在查询时并非已知宇宙——本模块采用 **EFTS form 级查询**（无 `ciks=` 参数，与 `stakes_13d_efts` 的无 CIK 模式同源）。

**实测查询**（2026-08-22 live probe，窗口 119 天）：

- `forms=S-1`（root form）自动展开含 `S-1/A`：**827 份**（S-1 335 + S-1/A 492）。
- `forms=424B4`：**219 份**（无修正家族）。
- 合计 1,046 份 / 484 个发行人 CIK，仅 ~12 个 EFTS 分页请求（页大小 100）。

**v0.2 窗口刷新实测**（2026-08-26，TASK-DISP-H3，`scripts/form_ipo_fetch.py`）：

- 窗口滚至 `2026-04-25..2026-08-27`：S-1 家族 **856**、424B4 **221**，合计 **1,077 份 / 496 发行人**。
- EFTS 分页：9 页（S-1 家族）+ 3 页（424B4）= **12 个请求**。

---

## 附 B — 发行价有界解析（v0.2，TASK-DISP-H3）

### 设计一句话

镜像 `src/aionis/ingest/stakes_pct.py` 的分级置信度先例：仅对**最新 ≤80 份
priced（424B4）申报**，每份 ≤2 次礼貌请求（filing `index.json` → 主文档），
封面价正则解析分级为 **exact**（唯一最终价格 → 导出）/ **low**（草稿/区间措辞，
如 "proposed … price range between"→ 永不出值、只计数）/ **none**（无匹配）；
低置信与未匹配一律如实留空，**绝不猜测，绝不放宽正则凑覆盖率**；假设性语句
（"若发行价高 $1…"情景测算）整句跳过，不作为任何层级证据。

### 实测分级计数（2026-08-26 真实抓取，目标集 80）

| 层级 | 计数 | 说明 |
|---|---|---|
| **exact**（出值） | **63** | 封面唯一最终价成功导出（实样：ALH $23.50、LYNX $17.50、SPAC $10.00、penny $0.79） |
| low（留空计数） | **0** | 本窗口集未命中草稿/区间措辞——层级保留为防线，不为覆盖率而放宽 |
| none | **15** | 14 例无匹配 + 1 例 `no_primary_doc`（索引无可用主文档，终局诚实空） |
| fetch-failed | **1** | `0001193125-26-297648` index.json 返回 503×2 次——非终局，下次运行自动重试 |
| 未走查（预算截断） | **1** | 第 80 名止步于请求预算，保持 null 并披露 |

attempted = 63+0+15+1 = **79 / 目标 80**；对全 priced（221 份）覆盖率 = 63/221 =
**28.5%**（精确口径披露于面板 `offer_price_meta.coverage_pct_of_priced`）。

### 请求账（逐级记账，2026-08-26 实测）

| 阶段 | 请求数 |
|---|---|
| EFTS 窗口刷新（S-1 9 页 + 424B4 3 页，form 级元数据分页） | 12 |
| 试跑通路验证（最新 2 份 × ≤2 请求） | 4 |
| 主走查（78 目标 × ≤2；末行失败计 1，154 封顶触发于 77/78） | 153 |
| **合并总计** | **169 / 任务预算 170 ✅** |

礼貌实现：走查启动时显式抬高端到端 host 间隔至 **≥2.1s**（高于项目底线 2.0s）
+ bounded transient-only 重试；重试内部增发次数无法从外层观测、未入账本
（2.1s 斜坡下罕见）；累计账本持久化于缓存 `_meta.requests_cumulative = 157`
（= 试跑 4 + 主走查 153）。

### 幂等与缓存（accession 键）

- 缓存 `data/cache/form_ipo_price_parsed.json`：一 accession 一条目；
  `ok:true` 条目**永不再抓取** → 复跑 0 新请求。
  **实测证据（2026-08-26）**：获取完成后以 `--max-requests 0` 验证跑复跑，
  输出 `cached-ok=78 to-fetch=2 → REQUEST CAP 0 reached after 0/2`——
  即在触网之前截断，78 条 ok 条目零请求 ✔（to-fetch=2 为 1 条 503 失败行
  按契约保留重试资格 + 1 条预算未达行；两者均未发请求）。
  单元层另有 hermetic 断言钉死同一契约（`tests/test_form_ipo_price.py::
  test_parse_flow_two_requests_then_cached_zero`）。
  `ok:false` 行下次运行重试；null 提取为终局诚实值并缓存（同 stakes_pct 契约）。

### 诚实边界段

- **预算截断即如实截断**：目标 ≤80 份为本任务上限；之外的历史 priced 申报保持
  null + EDGAR 链接，覆盖率为精确口径披露，绝非全量。
- **任何层级都不提取股数/募资额/上市日**（范围远大于正则可诚实锚定的字段）。
- 主文档选择器只认文件名带 `424b4` 的非 exhibit 文档，退化为任意非索引 htm；
  选不中时记 `no_primary_doc` 终局（none 层级），不做第二跳猜测。

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
  1. **发行价——v0.2 起有界提取**（附 B）：仅最新 ≤80 份 priced（424B4）申报做封面价
     分级解析（exact 出值 / low 留空计数 / none 无匹配；绝不猜测），其余层级残余如实 null；
     募资额/股数/预期上市日仍不提取——每行链至该 filing 的 EDGAR index 页。
  2. **424B4 form 级捕获含已上市公司定价增发**（如 S-3 shelf 下架以 424(b)(4) 定价）——本面板是**注册/定价申报流**，非精选 IPO 名单；不做公司级状态机（行级状态：`filed` | `priced`）。
  3. **ticker 自 display_names 解析**（EFTS `display_symbols` 实测恒为 null）；未有代码的 S-1 申报人如实留空（实测 673/1,046 有 ticker，priced 子集 186/219），绝不猜测。
  4. 计数为 **filing 计数**非公司计数（一个 S-1 常伴多份 S-1/A）。

---

## G7 — Politeness（礼貌抓取）

### 结论：✓ **PASS**

- 复用 `_policy_get`（≥2s host spacing + transient-only 退避重试；经 `form4_efts._get_json`）。
- 实测首轮冷拉：**1,046 份 filing 仅 12 个请求**（9 页 S-1 + 3 页 424B4）——纯元数据查询，无逐文档抓取，天然最礼貌。
- 固定窗口锚 `START=2026-04-25`（~120 天），`END=today` 滚动；幂等缓存使日更仅抓增量页。
- **v0.2 有界价格走查**（附 B）：目标 ≤80 × ≤2 请求、间隔抬升至 **≥2.1s** + 预算封顶
  （任务账 ≤170，实测合并 169——见附 B 请求账）；accession 幂等缓存使复跑零请求。

---

## 附：状态推导表（行级，法定文件类型 → 状态）

| form | status | 依据 |
|---|---|---|
| `S-1` | `filed`（已申报） | 注册说明书已在案 |
| `S-1/A` | `filed`（已申报） | 修正 = 新 accession 的新申报 |
| `424B4` | `priced`（已定价） | Rule 424(b)(4) 法定最终招股书于定价后提交 |
