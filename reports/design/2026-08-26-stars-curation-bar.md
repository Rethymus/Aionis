# 明星投资人诚实策展门槛规格（13F 星管理人准入 / 剔除 / 证据 / 裁决）

- **日期**: 2026-08-26
- **Lane**: display / design-only（零代码改动，本文档只定义规则与改动点）
- **任务书**: `tasks/active/TASK-DISP-DES-stars-curation-bar.md`
- **并行材料**: `tasks/active/TASK-DISP-E-stars-evidence.md`（证据考察 agent 的字段表）；其交付物
  `reports/design/2026-08-26-stars-candidates-evidence.md/.json` 在本文撰写时尚未落盘（见 §12 冲突调和点）。
- **目标差距**: post-parity roadmap §1（`reports/design/2026-08-25-post-parity-roadmap.md` L42/L55-57）：
  参照站宣称 43 位 vs 本终端 40 位（5 位停报实体如实剔除），"honest −3"；**+3 仅当有真实活跃管理人
  通过本规格的诚实策展门槛——绝不凑数对齐数字**。

---

## 0. 本文回答任务书 §2 的六个问题（审计索引）

| 任务书 §2 问题 | 本文档章节 |
|---|---|
| 1. 准入判据 admission bar | §5 |
| 2. 排除判据 revocation/exclusion | §6 |
| 3. 证据要求 evidence schema + 集成核对清单 + BORDERLINE 处置 | §7 |
| 4. 裁决程序（谁拍板、主线代裁条件） | §8 |
| 5. 落地改动清单（精确到路径） | §9 |
| 6. 反目标重申（绝不凑数到 43） | §11 |

隐含标准提炼（40+5 档案）在 §2；七分类既有边界反推在 §3；zh_name 惯例在 §4。

---

## 1. 现状事实基线（全部来自本仓实读，零网络）

### 1.1 策展配置的真实落点

- **唯一策展点**: `scripts/form13f_fetch.py` 的 `MANAGERS: dict[int, tuple[str, str | None, str]]`
  （第 62–109 行），键 = CIK int，值 = `(EDGAR verbatim 实体名, zh_name 或 None, category)`。现役 **40 位**
  （原始 12 位 2026-08-20 验证 + 28 位 2026-08-22 FTS 验证，均为 commit `4405724`）。
- **类别枚举**: 同文件 `CATEGORIES` 元组（第 48–56 行）：`value / growth / activist / macro / quant /
  china_background / other`，共 7 类。注册表断言 `_assert_registry_sane()`（第 115–120 行）：
  category 必须在枚举内（fail-fast "unknown category"）、zh_name 必须 `str|None`、EDGAR 名不得重复。
- **导出链路**: `form13f_fetch.py` → `data/cache/form13f_aggregate.parquet`（gitignored、per-manager
  checkpoint 幂等）→ `scripts/export_terminal_data.py::export_form13f` 写 `web/src/data/aionis/form13f.json`
  （含 methodology 与 `category_counts`）→ `export_form13f_stars`（同文件 L3558–3598）从已提交的
  form13f.json 派生 `form13f-stars.json`：按 `total_value` 取 top-8、字段 verbatim、`n_managers = 全体花名册数`
  （首页卡计数因此自动诚实跟随）。
- **当前面板事实**（`web/src/data/aionis/form13f.json` 实测）: status ok，as_of `2026-06-30`，40 位；
  类别分布 value 9 / growth 8 / activist 6 / quant 6 / macro 5 / china_background 4 / other 2；
  zh_name 无一为 null（但契约允许 null）；可见书极差 ~$10M（Duquesne/Baupost 最新季可见书仅 ~$0.01B，
  因 13F 只覆盖美股权益）到 $875B（Citadel，含指数/互换口径庞大持仓）。
- **活体边界案例**: Pershing Square（CIK 1336528）面板中最新季停在 `2026-03-31`（filed 2026-05-15），
  其余 39 位均已覆盖 `2026-06-30` —— 即截至抓取快照，它在册但落后目标季一季。该案例是 §6 观察级
  判据的现实标本（维持展示真实最新季，不因滞后一季即静默除名）。

### 1.2 五个停报剔除档案（以实际代码为准）

剔除记录现存于四处：commit `4405724` 提交信息、`scripts/form13f_fetch.py` 模块 docstring 第 10–13 行、
`state/current.md` L80、`state/handoff.md` L317。逐个：

| 剔除实体 | 已记录口径 |
|---|---|
| Scion Asset Management (Burry) | 无法实证仍在正常申报（active-filing 验证失败） |
| Greenlight Capital (Einhorn) | 明确记载末次 13F-HR 为 2024-02（覆盖 2023-Q4）——距 2026-08-22 实查约 10 个报告季无申报 |
| Omega Advisors (Cooperman) | 无法实证仍在正常申报 |
| Pabrai Investment Funds | 无法实证仍在正常申报 |
| Glenpoint | 无法实证仍在正常申报 |

**先例的可执行口径不是"断档 N 年"，而是二元的**：在策展实查日，EDGAR 上查不到覆盖当期报告季的
13F-HR ⇒ 即视为停报嫌疑剔除，名气大小不构成豁免（Scion/Burry 名气极大仍被弃）。Greenlight 档案进一步
表明：历史辉煌 + 多年陈旧申报救不了一个停报者。由此推导出 §6 的可数化计时器（连续 2 季缺报出局），
并保证五先例全部落在同一判据下被复判为 FAIL。

---

## 2. 从 40+5 档案提炼的隐含标准清单（曾被实际执行的规则）

- **S1 申报活性是硬门且逐一实证**: 每个 CIK 都经 EDGAR full-text-search + submissions JSON 实查
  （docstring: verified live on 2026-08-22/2026-08-20）；"无法实证活跃" 直接弃选，不做推测性收录。
- **S2 剔除留痕，公开点名**: 五位被剔者在 commit message/docstring/state 三处留名并给出原因——诚实
  记录优于静默消失，也优于含糊地说"我们审查过"。
- **S3 注册对象是管理实体，人格绑定放括注**: 花名册键是基金管理公司 CIK/verbatim 名，人物身份编码进
  `zh_name` 括注（巴菲特/达利欧/伍德……）。个人户不入册。
- **S4 一人一席（同人勿重）**: 同批候选里点名防重（Viking 的 Halvorsen、Tiger Global 的 Coleman 各只占
  一席）；集团继任壳取当期活跃代表壳（高瓴系在册的是 HHLR ADVISORS 这一新壳 CIK 1762304，旧 Hillhouse
  壳不并存）。
- **S5 可归类，类别封闭**: 七类 enum 由断言锁定；归类是人工策展披露（methodology 自述 HUMAN-CURATED，
  非 SEC 字段）；宁可落入 `other` 不生造第八类。
- **S6 类别分布不追求均衡**: 测试明文 "no minimum per category … a large other share is acceptable
  honesty"（`tests/test_web_terminal_data.py::test_form13f_category_counts_honest`）；现实分布 9/8/6/6/5/4/2。
- **S7 中文名有惯例才写、无惯例可为空**: 契约允许 `str|None` 且视图容忍 null；但 40/40 全有译名——因为
  这些管理人都有中文财经媒体长期形成的通行叫法（文艺复兴科技、城堡投资、千禧管理、橡树资本等），而非机翻。
- **S8 知名度可替代规模**: Duquesne/H&H 可见书极小仍入册（德鲁肯米勒/段永平公众身份使然）；规模门槛若做
  硬性下限会错杀先例，故必为双轨或并列条件（§5 G2 形式化）。
- **S9 展示层与研究层隔离**: 整个面板自披露 display-only、NOT part of any OOS pipeline（methodology +
  测试双重锚定 license/units/dislosure）；策展永不触碰 ledger/frozen config/prereg。
- **S10 数字目标是非法输入**: roster 大小只能是产出不能是目标（roadmap: "+3 only if three active filers
  pass the honest-curation bar (never pad to match a number)"；首页卡 count=full roster 的测试
  `test_form13f_stars_digest_reconciles_with_panel` 断言 "count = full roster, not top-8"、
  "never a number invented to match an external reference"）。
- **S11 新增必须经同一套验证重演**: 28 人扩充轮（4405724）对每位新人都重做了 S1 级实证，而非沿用名单
  印象——说明"门槛"一直存在，只是没有成文；本文档的作用就是把它固化。

---

## 3. 七分类既有边界（按现役 40 人归属反推）

类别标签刻画的是**管理人的公众投资方法认同**（approach identity），不是法律结构、不是持仓统计特征。
每类给成员、正例边界与反例警示：

| 类别 | 现役成员（40 人全分布） | 边界要点（从实例反推） |
|---|---|---|
| `value` (9) | Berkshire, Appaloosa, Ruane Cunniff(红杉), First Eagle, Diamond Hill, Miller Value, Baupost, Fairholme, Southeastern | 经典基本面价值/深度价值/特殊情形均可（Baupost 含困境债也在 value）。上限约束：不因涉足信用而外溢 |
| `growth` (8) | ARK, Tiger Global, Coatue, Viking, Lone Pine, Maverick, Sands, Glenview | 长仓成长股/"Tiger cub" 系谱一网打尽；成长≠动量量化 |
| `activist` (6) | Pershing Square, TCI, Third Point, ValueAct, Elliott, Starboard | 以股东行动/代理战为公众标识；Third Point 兼做多基金仍归此类 |
| `macro` (5) | Bridgewater, Soros, Duquesne, Caxton, Moore | 全球宏观/自上而下认同优先于载体形态：Duquesne 持仓高度个股集中，仍因德鲁肯米勒的宏观身份归 macro |
| `quant` (6) | Renaissance, Two Sigma, D.E. Shaw, AQR, Millennium, Citadel | 系统化/量化驱动（含大型多经理平台的多数量化认知）；Citadel/Millennium 归此而不归 other，是因其平台模式的公众标签即系统化大规模运作 |
| `china_background` (4) | H&H(段永平), Himalaya(李录), HHLR(张磊), Greenwoods(蒋锦志) | 中国背景创始团队/大中华 franchise 专属；不是"持仓里有中国股票"就归此 |
| `other` (2) | Oaktree（信用/困境资产旗舰）, Point72（多经理平台但科恩公众形象是个股_select 多空） | **合法兜底类**：主导公众认同落不进前六类时使用；Oaktree 证明非股票策略不必硬塞 value，Point72 证明同类结构（对比 Citadel/Millennium）可以因认同差异落 different tag |

**归类决策树（供 G3 执行）**: ① 该管理人公众报道中被一致描述的投资方法是什么？→ 方法词直接命中
value/growth/activist/macro/quant 六类的定义句则归之；② 中国背景创始人且 franchise 围绕大中华 →
china_background；③ 命中不了任何定义句（信用专精、混合平台、多策略杂糅）→ other。④ 一句话 rationale
必须点名至少一位同类现役先例（如 "同 Citadel/Millennium 的多经理平台模式"）——写不出先例对照即视为
归类失败（BORDERLINE）。

---

## 4. zh_name 编码规范与出处规则（从 40 条实例反推）

已出现的三种合规模式（互不强制统一，均为诚实表达）:

1. **机构中文通行名（人名通行名）**: `伯克希尔·哈撒韦（巴菲特）`、`桥水基金（达利欧）`、`文艺复兴科技（西蒙斯）`、
   `城堡投资（格里芬）`、`千禧管理（英格兰）`——机构与人名都有成熟中文译法。
2. **保留拉丁品牌 + 人名括注**: `Appaloosa（泰珀）`、`D.E. Shaw（肖）`、`Point72（科恩）`、`Baupost（克拉曼）`、
   `高瓴 HHLR（张磊）`——品牌无通行中文译名时保留原文，仅对有名之人加注。
3. **品牌意译/约定俗成、无人名括注**: `蔻图资本`、`钻石山资本`、`Sands 资本`、`天鹰资本（First Eagle）`——
   依媒体惯例意译即可，不强加人物。

规则:
- **出处白名单**（三选一，写得出名字才算）: (a) 官方自发布中文资料（官网/官方公众号/官方募集材料）;
  (b) 主流权威中文财经媒体的既定用法（华尔街日报中文网、财新、新浪财经/彭博中文等惯例译名）;
  (c) 项目内已确立的前例延续（如 def14a/stakes 等 panel 中已有的同一人物译名）。
- **禁止**: 拼音机翻生造（如把生僻机构名直译成从未见过的中文）、为凑对称硬造人名中文。
- **null 政策**: 查无惯例译名时 `zh_name=None` 是合法且诚实的 PASS 结果（契约与视图都容忍 null）;
  但对显然有通行名的机构写 null 属偷懒，抵消 G4 得分改为 BORDERLINE。

---

## 5. 准入判据（admission bar）— 问题一

六道闸门 G0–G5，**全部 PASS 才准**。判据逐条机械可判定，判定材料由 §7 证据 schema 提供。

**G0 身份可核验（identity）**
- 判据: EDGAR 上存在该 CIK，其 submissions JSON 的实体 verbatim 名与候选所指同一管理实体；CIK 为 10 位
  零填充串。
- PASS: 名称逐字符匹配 filings 头；FAIL: 只能靠别称/俗称对上、或多个同名实体无法排歧（参照 ticker-link
  处 "ambiguous multi-entity names dropped" 先例）。

**G1 申报活性（activity）**
- 定义: R = 实查日之前最近的、缴报期（季末+45 天）已过的完整报告季。例如实查日 2026-08-26 ⇒ R =
  2026-06-30（缴报期 2026-08-14 已过）。
- G1a 最新性: 候选最新 13F-HR 报告季 == R ⇒ PASS；== R−1 且有书面在途解释（宽限期内迟报/壳迁移继任链）
  ⇒ BORDERLINE；≤ R−2 或查不到 ⇒ FAIL。
- G1b 连续性: R−7..R 共 **8 个报告季每季至少一份 13F-HR 原始申报**（HR 原件计覆盖；HR/A 修订不补位）。
  零断口 ⇒ PASS；存在 1 个断口且断口恰能被 CIK 继任链证据完全解释 ⇒ BORDERLINE；≥2 个断口，或近 4 季内
  出现任一断口 ⇒ FAIL。
- 校准依据: 任务书 E §3 以"近 8 季连续性、断报=停报嫌疑"为采集口径；五剔除先例中唯一有定量档案的
  Greenlight 缺口 ≈10 季，远越 FAIL 线，说明 8 季窗口不冤枉任何人。

**G2 规模或知名度（prominence，双轨 OR 门）**
- PASS 当且仅当以下任一成立:
  - **规模轨**: 最新季 13F 可见书总市值 ≥ US$50 亿（`total_value_usd ≥ 5_000_000_000`，单一数值阈值，
    取自 form13f.json 口径；这是 proxy 下限不是美誉度排名）;
  - **知名度轨**: 主理人有通行中文译名，且证据报告 fame.media_sources 给出 ≥1 家主流中文财经媒体的
    长期报道条目（来源名非空）。
- 两轨都没有 ⇒ FAIL。
- 校准依据: Duquesne/Baupost 可见书 <$0.05B 但凭德鲁肯米勒/克拉曼的知名度轨毫无争议通过；Citadel 级
  规模即使低调也过规模轨——双轨完整覆盖现役 40 人（反证：单规模轨会错杀两位先例成员）。

**G3 七分类可归类（categorizable，且不生造类）**
- PASS: 归入现有七类之一，rationale 依 §3 决策树写成一句话且点名 ≥1 位同类现役先例；
  落入 `other` 同样合法（S6）。
- BORDERLINE: rationale 写不出先例对照、或两类之间摇摆不定。
- FAIL: 建议新增第八类（`CATEGORIES` 元组扩容牵动 i18n `CATEGORY_LABEL`/`CATEGORY_ORDER`/
  `FORM13F_CATEGORIES` 三处 enum 锚点，超出本规格授权，须业主另行批准设计变更）。

**G4 中文名可得性（zh_name reliability）**
- PASS: zh_name 建议值符合 §4 出处白名单之一并附来源名；人名括注仅当该人物确有通行中文译名。
  `null` 且查明"确无惯例译名"亦是 PASS。
- BORDERLINE: 有译名但只能找到低权威来源（自媒体/百科孤证）。
- FAIL: 仅能以机器音译/直译生造支撑（宁 null 勿造）。

**G5 重复防护（dup guard，详见 §6-R2）**
- PASS: CIK 不在 `MANAGERS` 键集 && EDGAR verbatim 名不在册内（`_assert_registry_sane` duplicate-name
  断言底线）&& 同人异壳检索零命中（核心主理人/名称词干未被我方在册其他席位占据）。
- FAIL: 任一命中。"one person, one seat"——同一著名投资人已有席位时，其关联新壳永远不能再开席
  （Hillhouse→HHLR 式继任只认当期活跃代表壳一个位子）。

---

## 6. 排除 / 撤销判据（revocation / exclusion）— 问题二

**R1 断档计时器（复用五剔除先例的实际口径并离散化）**
- **观察态（watch）**: 全量重抓循环发现在册者最新可得季 < R（落后 1 季）→ 保留在册、面板如实显示其真实
  最新季（Pershing 现状即为该态的既有行为），同时在 `state/handoff.md` 记一行待复核。
- **撤销线（revoke）**: 连续 **2 个报告季**（R 与 R−1 双双缺失，约为错过两个缴报窗口 ≈ 半年）无 13F-HR
  ⇒ 出局。核对先例: Greenlight（≈10 季缺口）、Scion/Omega/Pabrai/Glenpoint（实查日无当期申报 ≥2 季）
  全部落在线外，无一误伤；亦无一先例因 ≤1 季缺口被剔。
- 撤销执行: 从 `MANAGERS` 移除一行 + 在模块 docstring 的剔除句尾追加名字（延续 "…were honestly dropped"
  既有文风）+ state 双文件各一行留档。

**R2 同实体不同壳的重复防护（CIK/名称双查）**
- **CIK 查**: 候选 CIK ∉ `MANAGERS` 键集（dict 键天然去重 + 测试 "one manager row per CIK" 底线）。
- **名称查**: EDGAR verbatim 名全册唯一（fail-fast 断言）; 若 EDGAR former-names 里暴露曾用名与我方在册者
  相同实体 ⇒ 并壳处理。
- **同人异壳查（超越机械键查的人格层防线）**: 用 §3 的 zh_name 人名括注 + 名称词干做交叉检索——著名
  主理人姓氏命中任何在册席位 ⇒ 拒绝新席，指向"关联壳合并"情形: 取当前承担主要申报义务、名称承载公认
  franchise 的那个 CIK 为唯一代表壳（高瓴系只认 HHLR 先例）。
- BORDERLINE 处置: 疑似关联但证据不足（家族字号同名不同团队之类）⇒ 默认不进，交业主。

**R3 特殊情形即时出局（不等计时器）**
- 注销投资顾问注册、清盘公告、返还外部资本转家族办公室等公告进入我方视野时，直接走 R1 撤销程序，
  不管季度计数（Omega 先例的精神: 结构性停报不等窗口证明）。

**R4 复活条款**: 曾出局者如恢复合规申报满 4 个报告季，可重新从 §5 零起走一遍准入——历史星级不做捷径。
（Ghost of Greenlight clause: 复活必须赢回数据，而非念旧情。）

---

## 7. 证据 schema 与集成核对清单 — 问题三

### 7.1 字段表（与 TASK-DISP-E-stars-evidence.md §3 表格一一对应）

并行 agent 在 worktree `Aionis-we` 分支 `feat/stars-evidence` 工作；其 json 尚未落盘时按下表独立采集，
集成时按键名核对（冲突调和见 §12）。

| 规格 key | 对应 E 任务 §3 列 | 类型 / 约束 |
|---|---|---|
| `candidate.name` | 候选名（人/机构常用称） | string |
| `candidate.cik` | CIK（EDGAR search） | string, `^\d{10}$` |
| `filings.latest_quarter` | 最新 13F-HR 申报期 | ISO 季末日 `"YYYY-MM-DD"` |
| `filings.latest_filed` | 对应 filed 日 | ISO `"YYYY-MM-DD"` |
| `filings.continuity_window` | 近 8 季连续性 | int = 8 |
| `filings.gaps` | 断报季列表 | array of `"YYYY-MM-DD"`（空数组=零断口） |
| `entity.name_verbatim` | 实体名 verbatim | string（filings 头逐字符） |
| `entity.type` | 实体类型 | string |
| `fame.track` | 公众知名度证据 + G2 判轨 | `"size"` \| `"media"` |
| `fame.total_value_usd` | 规模轨数值 | number（最新季 total_value） |
| `fame.media_sources` | 知名度轨出处 | array of `{name: string}`（≥1 即满足 G2 知名度轨） |
| `zh_name.proposed` | 中文名建议 | string \| null |
| `zh_name.person_anchor` | 括注人名建议 | string \| null |
| `zh_name.source_type` | 出处 | `"official"` \| `"major-zh-media"` \| `"project-precedent"` \| `"none"` |
| `zh_name.source_ref` | 来源名 | string \| null（type≠none 时必填） |
| `category.value` | 建议类别 | ∈ 七枚举 |
| `category.rationale` | 归类理由一句话 | string，须引用 ≥1 位同类现役先例 |
| `dup_check.cik_absent` | — | bool |
| `dup_check.name_unique` | — | bool |
| `dup_check.sibling_hits` | 同人异壳检索结果 | array of `{matched_member: string, basis: string}` |
| `verdict` | PASS/FAIL/BORDERLINE 建议 | 枚举 |
| `failed_gates` | 未过闸门 | array of `"G0".."G5"`（verdict 派生量，需自洽） |
| `meta.request_log` | 礼貌记账（E 任务铁律 ≤60 请求、≥2.1s 间隔） | object（总数+分站计数），集成时核验预算合规 |

### 7.2 集成核对清单（哪几条必须 PASS 才准入）

1. 打开 evidence JSON，逐候选校验 `verdict` 与 `failed_gates` 自洽（`verdict=PASS ⇔ failed_gates=[]`）。
2. 核对 `meta.request_log` 总请求 ≤60——超预算的报告整份降级为不可采信（礼貌契约是 binding 约束）。
3. 六闸门复核: G0–G5 依 §5 逐条由主线独立重验（用该 JSON 提供的字段值判定，不盲签 `verdict` 建议）。
4. G1a==PASS 且 G1b==PASS 且 G2/G3/G4/G5 全 PASS ⇒ 可准入（走 §8 代裁或业主程序）。
5. **任一闸门 BORDERLINE ⇒ 默认不进**——宁可少一位，不留一处存疑展示。业主仍可在了解存疑点后明确 GO,
   但 GO 必须写入 state 记录（记名担责），不允许静默带病入册。
6. 任一闸门 FAIL ⇒ 拒绝并在 state 一行留痕拒绝理由（即使数字上"差几个才到 43"——见 §11）。
7. 通过者按 §9 清单落地; 落地后必须跑通 `uv run pytest -q tests/test_web_terminal_data.py`（contract
   测试族）确认派生锚全部自洽。

---

## 8. 裁决程序 — 问题四

- **主线代裁（无需业主出场）的适用条件——当且仅当**: 某候选六闸门全项 PASS（G0–G5 无一 BORDERLINE/FAIL）,
  evidence 文件齐备、request_log 合规、且 dup_check 零命中。此时主线可直接采纳并落地 §9 清单，
  同时在 `state/handoff.md` + `state/current.md` 各记一行: 引用本规格文件与 evidence 文件路径、候选人、
  裁决日期、"六闸门全 PASS"字样。
- **必须业主拍板（GO gate）的情形**: ① 任一闸门 BORDERLINE（哪怕主观上"感觉没问题"）; ② 涉及 `CATEGORIES`
  枚举扩容（新类别 = 设计变更）; ③ 需要 R4 复活条款; ④ 同批准入人数会影响首页卡观感的边缘判断
  （一次集成超过 3 位新人时）——数量异常本身就是需要人看一眼的信号。
- **永久禁止**: 为让 candidates 通过而回改判据阈值（本规格如需修订须业主批准并留版本说明）;
  在 evidence 文件缺位时代替取证（"我记得他还报"不算证据）。
- 裁决动作的验证命令: `uv run pytest -q tests/test_web_terminal_data.py`（准入后必须绿）。

---

## 9. 落地改动清单（精确到路径，供下一轮构建任务书引用）— 问题五

**必须人工改动（唯一策展点 + 导出物 + state）**

| # | 路径 | 动作 |
|---|---|---|
| 1 | `scripts/form13f_fetch.py` | `MANAGERS` 追加一条 `<CIK_int>: ("<EDGAR VERBATIM NAME>", "<zh_name 或 None>", "<category>")`；同轮更新模块 docstring 验证日期句与剔除句；**`CATEGORIES` 不动**（除非业主批的新类别） |
| 2 | （数据重建，命令非文件） | `uv run python scripts/form13f_fetch.py` → 重生成 `data/cache/form13f_aggregate.parquet`（per-manager checkpoint，缓存幂等零重复 HTTP） |
| 3 | （导出重跑，命令非文件） | `uv run python scripts/export_terminal_data.py` → 触发 `_safe_export("form13f", …)` 与 `_safe_export("form13f_stars", …)`，连带 `api_catalog/data_health` 的 rows 重算 |
| 4 | `scripts/export_terminal_data.py` | `export_form13f` 内 methodology 文案的 `"~40 star managers"` 句与剔除举例句更新为新实数与新档案（写实数、不做整数美化） |
| 5 | `state/current.md` + `state/handoff.md` | 各一行：裁决结论、依据（本规格 + evidence 文件路径）、Pass/Fail 计数、与最终 roster 数 |

**自动跟随、明令禁止手工同步（防两处漂移）**

| 产物 | 自动机制 |
|---|---|
| 首页明星卡计数与列表 | `web/src/components/overview/overview.tsx` L604–619 读 `form13fStars.n_managers`/top-8 digest——roster 变即自动变，count=full roster 由契约测试锁定 |
| 分类目录 chips 与计数 | `web/src/components/institutions/institutions-view.tsx` 用 export 的 `category_counts` 自动渲染 |
| `/manager/[cik]` 静态页 | `web/src/app/(dashboard)/manager/[cik]/page.tsx::generateStaticParams` 枚举 `form13f.managers` 自动扩页（构建页数随之 +N） |
| TS 类型 | `web/src/data/aionis/form13f.ts` / `form13f-stars.ts` 字段形状固定，roster 数变化不需编辑（不加新类别时零改动） |
| 契约测试 | `tests/test_web_terminal_data.py` 全部为派生锚: `len(ms) >= 12` 下限、`n_managers == len(f["managers"])`、category recount、digest reconcile——**设计上无须随人数编辑**; 唯一需要对齐点是 `FORM13F_CATEGORIES` 枚举（不加新类别则不动） |
| digest top-8 重排 | 按 `total_value` 自动重算——新人挤入 top8 会自然替换老人，属预期行为，不做人工保席 |

**提交纪律**: display lane 原子 commit（参照 4405724 先例），Conventional Commits；不触 ledger/frozen
config/prereg/OOS；禁 `git add -f`。

---

## 10. 季度复核契约（防止门槛退化为一锤子买卖）

每次 form13f 全量重抓周期顺带执行一次 R1 检测: 重抓后若某在册者的 `quarter < 面板 as_of`（现状由抓取逻辑
自然暴露为"只拉到最近 2 季中的旧季"），即产生一条 watch 记录。当前代码已在面板层容忍该滞后
（`test_form13f_changes_enum_when_ok` 断言 `m["quarter"] <= as_of`），故检测本身零新代码——但建议下一轮
构建任务书在 fetch 收尾输出中加一行显式提醒（列出 lagging managers），把 watch 态从"隐式可见"升级为
"主动上报"。连续两季滞后者按 §6-R1 撤销程序处理。

---

## 11. 反目标重申 — 问题六

- **绝不凑数到 43。** 43 是别人宣称的数字，不是我们的目标。roster 大小只能是【活跃且全 PASS 的人数】
  这个量的输出；把 43 设为目标再回头找三个"差不多能过"的人，是对本项目诚宪法则的直接违反。
- 诚实空结果是合法结果: 如果证据考察结束时零人全 PASS，面板保持 40，roadmap 的 "honest −3" 就作为
  长期诚实缺口披露——与 DSR 研究线"窄置信区间原假设也是好结果"同一精神。
- 任何环节发现自己在想"他已经够有名了，差一季就算了吧"——那就是 BORDERLINE 默认不进的时刻。

---

## 12. 冲突调和点（并行证据报告状态）

截至本文撰写（2026-08-26），`reports/design/2026-08-26-stars-candidates-evidence.md/.json` 在主仓
`reports/design/` 下不存在（该 agent 在 worktree `Aionis-we` 分支 `feat/stars-evidence` 作业）。本文 §7
schema 按 `TASK-DISP-E-stars-evidence.md` §3 字段表独立成文。集成时的调和点预留:

1. **键名差异**: 若对方 JSON 使用 §7.1 之外的字段名（如 `latest_13f_quarter` vs `filings.latest_quarter`）,
   以在先落盘且更贴近 E 任务表头措辞的一方为准做映射补丁，不重采集。
2. **口径分歧**: R 取值（对方写 "≥2026-Q2 正常申报"）vs 本文的季末+45 天窗口推导式——两者在 2026-08 当月
   解析结果相同（R=2026-06-30），不构成实质冲突。
3. **verdict 不一致**: 对方建议 vs 本规格六闸门重验结论不一致时，以本规格闸门判定为准（E 任务自声明
   "不做策展决定"）; 但偏差必须写进 state 记录，不许悄悄忽略。
4. **请求记账缺失**: 对方报告若无 request_log，整个证据包降为参考件，候选人须重新取证后才可进入 §8 程序。
