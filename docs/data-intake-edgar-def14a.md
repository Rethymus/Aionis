# 数据接入 7 门 — EDGAR DEF 14A 代理委托书申报流

> **状态**：**v0.2 · 2026-08-23** · exploratory-only display module。
> **范围**：EDGAR DEF 14A 申报数据通过 7 门强制清单，所有第三方数据集进 Aionis 前 **必须** 全部过关。
> **引用**：主 rubric 见 `docs/data-intake-rubric.md`。本文档为 EDGAR DEF 14A 流（`/executives` 面板 DEF 14A section + **v0.2 人级档案 persons section**）专用准入评估。

---

## 数据源概述

**SEC EDGAR DEF 14A**（definitive proxy statement，股东大会代理委托书）是董事会/高管治理维度的法定节点文件：董事提名、高管薪酬、受益持股表、股东大会表决事项的法定载体。与 form4/8-K 的按发行人查询不同，本模块采用 **EFTS form 级全市场查询**（无 `ciks=` 参数，与 `form_ipo` / `form_d` 同模式）。

**实测查询**（2026-08-23 live probe，窗口 2026-04-25..2026-08-23，~120 天）：

- `forms=DEF%2014A`（root form，空格 URL 编码照 `form_ipo`）：**1,387 份**，1,351 个发行人 CIK——远低于 EFTS 10,000 上限（未触发自适应切分）。
- 抽样页（`from=0` 与 `from=700`）**全部** `form == "DEF 14A"`（`root_forms == ["DEF 14A"]`）。
- **直接查 `forms=DEF 14A/A` = 0 份**：本窗口无 DEF 14A 修正件——实务中代理委托书补充/修正以 **DEFA14A**（additional proxy soliciting material，**独立 root form**，本窗口 2,278 份）提交，**不在 v1 范围**。状态映射保留 `DEF 14A/A → amendment` 纵深防御臂（照 form_d 的 D/A 臂），fetch 全量装配的 by_form（`{'DEF 14A': 1387}`）确认窗口内 0 修正件。
- 1,043/1,387 行（75%）自 `display_names` 解析出 ticker（`display_symbols` 实测恒为 null）；无代码者如实留空。

**v0.2 人级档案（person-level lane，2026-08-23）**：`aionis.ingest.def14a_persons` + `scripts/def14a_persons_fetch.py` + `export_def14a_persons()`（`def14a_persons.json`）。对面板**最新 ~150 份**逐份解析 primary document（filing `index.json` → 评分式主文档挑选，照 form8k 模式）：

- **请求账**：每份 ≤2 个 GET（索引 + 主文档），显式 `sleep 2.1s` 叠加进程级 ≥2.0s host spacing；per-accession 幂等缓存（重跑零 HTTP）；**45 分钟硬性 wall-clock 预算**——到点即停，覆盖率按已处理前缀如实计数、绝不外推。
- **解析置信分级（宁可 null 不猜测）**：① `section_age_rows`（HIGH）——经典「Name (Age) Title Since」花名册行（`Name (58)` / `Name, 58,` / `Name, age 58` / 单元格分隔 `Name 58 Title`），2-4 个首字母大写词的人名 + 独立人类年龄（30-99 边界）+ **同排职务词见证**；对逐词碎裂的 inline-XBRL 版式（Venu Holding 实测）以「年龄锚点定界」从拼接流中重建行。② `section_name_roles`（MEDIUM）——已定位董事/高管节内 `First M. Last`（中间缩写）+ 同排职务词。③ 其余 → `persons=[]` 且 `parsed=false`（诚实空值，**绝不启发式猜名**）；人名停用词表（Item/Section/月份/委员会等）拒绝「长得像名字」的标题段；职务词固定 11 词规范表（ceo/cfo/coo/cto/chairman/president/vice_president/treasurer/secretary/director/officer），「Advisor to CEO」类外部头衔经 guard 不计为 ceo。
- **诚实披露**：同一姓名跨申报合并为一人（同名不同人可能误合）；连字/撇号/首名缩写（"JW Roth"）式人名保守**漏掉**；职务为文本见证词、可能含往任或外部公司头衔；董事/高管为独立集合（CEO 兼董事两边计数）。

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
- **人级**（v0.2）：解析器为纯函数（确定性）；per-accession 索引/主文档缓存幂等（重跑零 HTTP）；契约由 `test_def14a_persons_panel_contract` + 纯函数测试 `tests/test_def14a_persons.py`（行式/碎裂两种真实版式夹具）锁定。

---

## G5 — Exploratory-only 边界

### 结论：✓ **PASS**

- **display-only / mode=exploratory**：仅进终端 `/executives` 面板 DEF 14A section、**persons section（v0.2 人级档案）**与静态数据 API（`def14a.json` / `def14a_persons.json`）。
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
- **v0.2 人级选择诚实**（`def14a_persons.json` methodology 同文披露）：
  1. **解析面 = 最新 ~150 份**（非全窗 1,387 份）——礼貌预算约束的选择，覆盖率分母如实为「已处理数」，45 分钟到点即停、不外推。
  2. **读不出 = 诚实空**：非置信分级命中的文档 `parsed=false`、`persons=[]`，面板 null 语义明示（宁可 null 不猜测）；覆盖率 KPI 与 tier 分布（age-rows/name-roles/null/errors）面板直读。
  3. 同名合并/名字形状漏检（连字、撇号、首名缩写）与职务词可能含往任/外部头衔——全部披露，display-only。

---

## G7 — Politeness（礼貌抓取）

### 结论：✓ **PASS**

- 复用 `_policy_get`（≥2s host spacing + transient-only 退避重试；经 `form4_efts._get_json`）+ **页间显式 `sleep 2.1s`**（照 form13f_dir）。
- **请求账（2026-08-23 v1 首轮）**：探测 4 个 EFTS 页 GET（DEF 14A from=0 / DEF 14A/A 直查 / DEFA14A from=0 / DEF 14A from=700）+ fetch 14 页 GET（1,387 hits ÷ 100/页）= **共 18 个请求**，纯元数据查询，无逐文档抓取。
- **请求账（2026-08-23 v0.2 人级首轮）**：~150 份 × ≤2 GET（filing `index.json` + primary doc）≈ **≤300 个请求**；每次真实 HTTP 前显式 `sleep 2.1s`（叠加 policy 的 ≥2.0s host spacing）；45 分钟硬预算即停；per-accession 幂等缓存令重跑/续跑零重复请求。
- 固定窗口锚 `START=2026-04-25`（~120 天，照 ipo 锚），`END=today` 滚动；幂等缓存使日更仅抓增量页。

---

## 附：状态推导表（行级，法定文件类型 → 状态）

| form | status | 依据 |
|---|---|---|
| `DEF 14A` | `new`（新申报） | 新的 definitive proxy statement 已提交 |
| `DEF 14A/A` | `amendment`（修正） | 纵深防御臂——修正 = 新 accession；本窗口实测 0 份（修正实走 DEFA14A，范围外） |
