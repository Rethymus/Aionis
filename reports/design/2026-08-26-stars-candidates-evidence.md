# TASK-DISP-E — 明星投资人 "+3" 候选考察：EDGAR 证据报告

- **Lane**: display / 数据核查（纯调查，零策展裁决、零生产代码改动）
- **执行日期**: 2026-08-27（文件名按任务书固定为 2026-08-26）
- **工作树**: `F:\ZCodeData\Aionis-we`（branch `feat/stars-evidence` @ 38c287c）
- **判据框架**: 并行 DESIGN 文档 `reports/design/*stars-curation-bar*` 截至 2026-08-27 **未落盘**——按任务书 §3 字段表自建表格。若 DESIGN 版本后到，以 DESIGN 判据为准复核本报告结论（字段口径一致，可直接映射）。
- **机器可读版**: 同目录 `2026-08-26-stars-candidates-evidence.json`（同内容同结论）。

---

## (a) 现役 40 确认与策展配置落点

**现役名单确认**: `web/src/data/aionis/form13f.json` → `managers` = **40 条**，快照 as_of（最新 reportDate）= 2026-06-30。
类别计数: quant 6 / value 9 / activist 6 / growth 8 / macro 5 / china_background 4 / other 2（合计 40）。

40 家 CIK 明细见 JSON 的 `active_registry` 与源数据本身；与策展注册字典逐一一致。

**策展配置真实落点**:

1. `scripts/form13f_fetch.py` 第 62–109 行 `MANAGERS: dict[int, tuple[str, str | None, str]]`
   —— `CIK -> (EDGAR verbatim 名, zh_name(可 null), category)`，即策展的唯一事实源；
   附 `_assert_registry_sane()` 契约校验（category 枚举 / zh_name 类型 / EDGAR 名唯一）。
2. 导出链: `form13f_fetch.py` 把 zh_name/category 写进 `data/cache/form13f_aggregate.parquet`，
   `scripts/export_terminal_data.py` 透传成 `web/src/data/aionis/form13f.json`（前端只读该 JSON）。

**新增一位 = 动 4 个数据点**: `{cik, edgar_verbatim_name, zh_name(nullable), category}`，
在 `MANAGERS` 字典加一行 + 重跑 form13f_fetch + export。没有其它散落配置点。

**5 个停报实体档案**（来源: `git show 4405724` 提交注释原文）:

> "Candidates not verifiable as actively filing were honestly dropped:
> **Scion, Greenlight (last 13F-HR 2024-02), Omega Advisors, Pabrai, Glenpoint.**"

即 Burry/Einhorn/Pabrai 属上轮已诚实排除，本轮不重查、不复活。

---

## (b) 考察范围与请求账

**协调人起点池去重（7 人全部已在册）**:

| 起点 | 在册实体 | CIK |
|---|---|---|
| Bill Ackman | Pershing Square Capital Management, L.P. | 0001336528 |
| Seth Klarman | BAUPOST GROUP LLC/MA/ | 0001061768 |
| Chase Coleman | TIGER GLOBAL MANAGEMENT LLC | 0001167483 |
| Andreas Halvorsen（=Ole Andreas Halvorsen，同人勿重） | VIKING GLOBAL INVESTORS LP | 0001103804 |
| Steve Mandel | LONE PINE CAPITAL LLC | 0001061165 |
| David Tepper | Appaloosa LP（"是否已停?" 答: **未停**，快照含 Q2 HR filed 2026-08-14） | 0001656456 |
| Larry Robbins | GLENVIEW CAPITAL MANAGEMENT, LLC（lineage 大写节点 i:0001138995 即同一实体） | 0001138995 |

Ryan Israel = Pershing 同壳同人体系（CIK 1336528），防重复不入考察。
lineage_graph 机构节点与在册 40 的 CIK 全对齐，未发现需新防重的独立壳。

**本轮实际考察**: 10 个候选身份 + 1 个在册观察项（Pershing Q2 异常）。其中 5 条拿到
完整申报史证据，4 条部分取证，3 条因预算/瞬时网络故障止步 UNVERIFIED（如实呈现）。

**请求账（礼貌铁律全程满足）**:

| 项 | 值 |
|---|---|
| 预算上限 | 60 |
| 实际累计网络往返（含失败尝试+退避重试，逐条记账） | **58** |
| 最小间隔 | 2.25 s（≥2.1 铁律） |
| 退避序列 | 8s → 16s（SSL UNEXPECTED_EOF 瞬时故障率约四成） |
| 端点 | browse-edgar atom（公司检索）+ data.sec.gov submissions（单 CIK 全史） |
| UA | `AionisResearch owner-reachable@example.com`（首轮 403 后改 SEC 要求的联系式 UA 后全通） |

逐条明细（时间序: n、tag、url、status、bytes、耗时、退避）存于会话侧
`request_ledger`；分相摘要嵌入 JSON `request_ledger_digest`。失败尝试一律计入账目。

---

## (c) 证据主表与 PASS/FAIL/BORDERLINE 清单

判定口径（任务书 §3）: CIK 可核验 + 最新 HR ≥2026-Q2 正常申报 + 近 8 季无断报 → PASS 候选；
断报/清盘 → FAIL；实体活跃但数据形态不可用或证据中断 → BORDERLINE；预算内未完成取证 → UNVERIFIED。

| # | 候选 | 人 | CIK | EDGAR verbatim | 最新 HR (报告期/filed) | 近 8 季 | 结论 |
|---|---|---|---|---|---|---|---|
| 1 | Corvex Management LP | Keith Meister | 0001535472 | Corvex Management LP | 2026-06-30 / 2026-08-14 | 连续 ≥13 季 HR | **PASS** |
| 2 | GAMCO Investors Inc Et Al | Mario Gabelli | 0000807249 | GAMCO INVESTORS, INC. ET AL（前身 Gabelli Funds 改名链） | 2026-06-30 / 2026-08-12 | 连续 ≥13 季 HR | **PASS** |
| 3 | Southpoint Capital Advisors LLC | Rob Citrone | 0001378377（第二壳 0001319998 未验成） | Southpoint Capital Advisors LLC | 无 HR——最近 ≥12 季全部 13F-NT（最新 NT 2026-06-30 filed 2026-08-14） | 活跃但零持仓行 | **BORDERLINE** |
| 4 | JANA Partners LLC | Barry Rosenstein | 0001159159 | JANA PARTNERS LLC | 末次 13F 行为 13F-NT（2023-09-30 / 2023-11-14），其后 ≥11 季空窗 | 断报 | **FAIL** |
| 5 | Tudor Investment Corp | Paul Tudor Jones II | 0001080384 | TUDOR INVESTMENT CORP | 全窗无任何 13F* 形式申报（现存 X-17A/40-6B 类） | 断报 | **FAIL** |
| 6 | Blue Ridge Capital | John Griffin | 未复证（检索仅命中 CIK 0002023701，其 submissions 核验被预算闸截断） | — | — | 清盘 | **EXCLUDED/FAIL** |
| 7 | Icahn 各壳 | Carl Icahn | 已验两壳均非 13F 主载体（49578 经纪商壳 / 813762 上市合伙 IEP）；个人申报壳未定位 | — | — | — | **UNVERIFIED** |
| 8 | Baron Capital | Ron Baron | 检索两次均 SSL EOF/预算闸 | — | — | — | **UNVERIFIED** |
| 9 | DoubleLine | Jeffrey Gundlach | 检索未能在预算内落地 | — | — | — | **UNVERIFIED** |
| 10 | Key Square Group | Scott Bessent | 检索失败；公开事实方向提示 FAIL（2025 年起任财长、外部资管收缩）但无工具级证据 | — | — | — | **UNVERIFIED** |

每格一句话证据链:

- **Corvex PASS**: atom 单命中给 conformed-name=Corvex Management LP + submissions 历史
  2023-Q2→2026-Q2 季季 HR（含一次 2024-12-31 的 HR/A 修订）无断档。
- **GAMCO PASS**: icahn/gamco 多命中列表里经 submissions 定位 entity=GAMCO INVESTORS, INC. ET AL，
  35 行 13F 史 2023-06-30→2026-06-30 无断档，Q2 filed 2026-08-12。
- **Southpoint BORDERLINE**: 双壳命中同址同电话；主壳每季准时申报但近 ≥12 季全是
  13F-NT（通知"无可自行申报持仓"）→ 面板管线吃不到持仓行，入册即空壳行；第二壳核验
  差最后一步被预算硬闸截断。
- **JANA FAIL**: submissions 顶格行 = NT(2023-09-30)，此后至近窗结束连续空窗 ≥11 季。
- **Tudor FAIL**: 实体存在（1382B 小型档案）但 submissions recent 全窗过滤 `13F*` 为空。
- **Blue Ridge EXCLUDED**: 清盘为广泛报道的公开事实（2021 收缩清盘）；工具侧历史 CIK 未在
  预算内重新取证 → 如实记"清盘成立、历史壳 CIK 本轮未复证"。
- **Icahn UNVERIFIED**: 四个 Icahn 关键词命中里两个验明非 13F 申报主载体，剩余壳验证被
  预算耗尽截断——绝不猜 CIK，停在 UNVERIFIED。
- **Baron/DoubleLine/KeySquare UNVERIFIED**: 对应检索请求遇持续瞬时故障，预算达 58/60 上限。

**汇总**: PASS 2 ／ FAIL(or EXCLUDED) 3 ／ BORDERLINE 1 ／ UNVERIFIED 4（预算诚实止损）。
净潜在增量 +2（差距 "-3" 缩至 "-1"；仍不满数，符合"绝不凑数"原则）。

---

## (d) 中文名 / 类别建议摘要（供集成采纳，非裁决）

| 候选 | 建议 zh_name | 出处依据 | 置信 | 建议类别 | 一句归类理由 |
|---|---|---|---|---|---|
| Corvex | `Corvex（迈斯特）` | 沿用在册惯例"英文品牌+（中文姓氏）"（Point72（科恩）/TCI 基金（霍恩）式）；迈斯特为 Keith Meister 中文媒体惯用音译 | medium | activist | 集中持仓推动治理变革的激进投资人 |
| GAMCO | `GAMCO（加贝利）` | 加贝利为 Gabelli 长期沿用的中文译名；公司名保留原文符合 Appaloosa（泰珀）式惯例 | high | value | 经典基本面价值/私有市场价值路线 |

- 公司名一律**不生造中文直译**（铁律）；拿不准就置 `null`（视图容忍 zh_name=null，如 Sands/Appaloosa 先例用英文品牌 + 人名括注即可）。
- FAIL/BORDERLINE/UNVERIFIED 行不出中文名建议（避免为落选项背书直译）。
- 若 Southpoint 第二壳未来证实承载 HR：建议类别 macro，zh 建议届时按人名权威译名另行评估（本轮不给）。

## (e) 在册观察项（情报，不改状态）

**Pershing Square（CIK 1336528）2026-Q2 只报了 13F-NT（filed 2026-08-14），无 HR** ——本地快照
把它显示为最新 HR=2026-03-31 是对 EDGAR 现状的忠实反映，**不是抓取 bug**。这是其在册以来
首次 NT-only 季。两个含义:

1. 集成时不得把它当缺报错误去"补数"（那会变成编造数据）;
2. 若后续继续 NT-only，其面板行会自然老化滑退——主线的 "+3 计划" 需意识到现役 40 里存在
   一个潜在自然减员位（影响总盘可能是 -1 再 -1，而非 +3 尽收）。

---

## (f) 诚实边界（Honest limitations）

- 以下身份/壳未能实证即止，全部显式标 UNVERIFIED，不接受任何推测性 CIK 或申报期：
  Carl Icahn 个人申报壳、Southpoint 第二壳（0001319998）、Blue Ridge 历史 CIK 复证、
  Ron Baron、DoubleLine、Key Square。
- EDGAR 浏览端 atom 输出的 `<conformed-name>` 字段存在其自身的 Perl bug（输出 `ARRAY(0x…)`），
  故所有实体名以 `data.sec.gov/submissions` 的 `entity_name` 为权威 verbatim 来源。
- 知名度论断均为一般知识层面（任务书 §3 允许："公众知名度证据 | 一般知识+官方页 | 无需抓媒体"）。

---

### 交付物

1. 本文件: `reports/design/2026-08-26-stars-candidates-evidence.md`
2. 机器可读版: `reports/design/2026-08-26-stars-candidates-evidence.json`（候选→字段→证据→判定）

纯调查 lane 声明: 本轮零 ledger/frozen/config/prereg/OOS 接触; 未修改任何生产代码/导出/前端;
commit 仅含上述两文件。
