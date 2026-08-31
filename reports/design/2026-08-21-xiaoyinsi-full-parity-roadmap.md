# 参照站全形态对齐路线图 — 第三轮深挖 + 发展方向决策（2026-08-21）

> 状态：ACTIVE（业主定帧文件）。取代散落在 state 里的方向性判断，作为后续数轮开发的优先级依据。
> 业主定帧（2026-08-20 ① 原话精神）：**参照站 = Aionis 追求的最终目标形态；在其全形之上叠加项目特色（反泄漏/溯源/可证伪），只增不删，删减是以后才考虑的事项。**
>
> **P0 执行记录（2026-08-21 当日全部关闭）**：G 政客交易 → `/congress` 上线（House PTR 申报流级，planned 清零，commit `0679b92`）；I 8-K → `/events` 上线（23 事件 0 未分类，`a714fcb`）；H 快赢组 → cmdk 4 路由 + 13F 覆盖 94/118（`676b90d`+`5dc1c25`）。G/I 由主线接管完成（子代理阵亡于提供商限额）。下一步从 §5 P1 起跳。

---

## 1. 本轮实探摘要（2026-08-21，sitemap + 逐页）

参照站 = Next.js 静态生成的**美股另类数据终端**，17 个顶级路由 + 57 个 /stock/ 个股页，robots 全开，数据每 6 小时更新。完整导航分类（六组）：

| 分组 | 模块 |
|---|---|
| 概览 | 首页、新闻 /news |
| 情绪 | 川普TACO指数 /taco、Reddit /reddit |
| 机构 | 机构目录 /institutions、机构持仓 /managers |
| 事件 | 新股 /ipo、内部人买卖 /insider、重大事件 /events、举牌 /stakes |
| 财务 | 季报 10-Q /quarterly、年报 10-K /annual |
| 公司 | 公司目录 /companies、势力阵营（**"即将上线"**） |
| 人物 | 明星投资人 /stars（43 位，八分类 tab，/manager/CIK 详情页）、政客交易 /congress |

**关键情报（实探实证）**：
1. **它自己也有空壳**：/companies「0 家 · 数据暂不可用」、/annual「近期 0 份」——全形态对齐不等于追一个完成品；Aionis 用真实一手公共源**填壳**反而是超越机会。
2. **「势力阵营」未上线**（alumni/资本关系图谱）——它还在规划中的方向，恰好是 Aionis 溯源/血缘思维的强项领域。
3. 数据来源自述"SEC 及其他第三方**非公开**数据库"——license 不透明，**不可消费其数据/接口**（7-gate G1 挂，业主亦明示"从模仿开始"）；正确姿势 = 产品形态对齐 + 一手公共源自建。
4. 其覆盖有缺口（前轮已证：NVDA 13F"共 0 家"）——Aionis 的契约闸门 + 诚实回退（"待解析/明细见原文"它也有）是同级能力。

## 2. 对齐矩阵（17 路由逐一裁决）

| 参照站路由 | Aionis 现状 | 裁决 | 数据可得性（一手源） |
|---|---|---|---|
| / 首页 | dashboard ✓ | **已对齐** | — |
| /news 新闻流 | GDELT 主题信号（themes 内），无独立页 | P2 补独立页 | GDELT 已有管线 |
| /taco | /taco ✓（2016→今月均 VIX 背景） | **已对齐+超越** | FRED |
| /reddit | /reddit ✓（RSS 零凭证） | **已对齐** | Reddit RSS |
| /institutions 机构目录 | /institutions ✓（12 明星管理人） | 部分对齐→P1 扩目录 | EDGAR 13F |
| /managers 机构持仓申报流 | 无（有 13F 但无申报流视图） | P2 | EDGAR EFTS |
| /ipo 新股日历 | market_context CN 事件含 ipo 类型；无美股 IPO 页 | P1 | EDGAR（S-1/424B4/上市） |
| /insider | /insiders ✓（Form4 2016→今） | **已对齐** | SEC 公共域 |
| /events 重大事件 | 无（8-K 未建） | **P0（本轮）** | EDGAR EFTS form=8-K |
| /stakes 举牌 | /smart-money ✓（13D 2015→今，日更） | **已对齐** | SEC EFTS |
| /quarterly 10-Q 流 | 无 | P2 | EDGAR（全量索引） |
| /annual 10-K 流 | 无（参照站自己也是空壳） | P2 | EDGAR |
| /companies 公司目录 | stock_universe 1421 页但无目录索引页 | P2 | 已有（SEC+CN 元数据） |
| /stars 明星投资人 | 12 位内嵌于 /institutions；无 43 位目录+分类+详情页 | P1 | EDGAR 13F |
| /manager/CIK 详情 | 无 | P1（随 stars） | EDGAR |
| /congress 政客交易 | **唯一剩 planned**（api_catalog + data_health 虚线卡） | **P0（本轮）** | 官方披露源（见 §4） |
| /stock/[ticker] | /stock/[ticker] ✓（1,421 页，**US+CN 双区域 = 超越**） | **已对齐+超越** | 冻结 OOS 宇宙 |

裁决原则：**先关闭 planned 缺口（congress）→ 再补事件族（events）→ 再扩人物/机构生态（stars/managers 详情）→ 最后财务流与目录页**。每一步都走 display + 数据导出 lane，0 ledger/frozen/config/prereg/OOS。

## 3. Aionis 增层特色（叠加，不是删减）

对齐的是**形态**，超越的是**纪律**。每个对齐模块都强制携带 Aionis 四件套：
1. **每数字溯源**：面板级 as_of + provenance badge +（涉研究面时）ledger 行号/config sig。
2. **license 透明**：api_catalog x-license + 7-gate 摄入事实（参照站"非公开数据库"做不到）。
3. **冻结 vs 日更诚实二分**：data-health 水位线 + ProvenanceBadge frozen/clock 语义。
4. **双区域 US+CN**：参照站美股 only；Aionis 个股页/热力图/行业已双区域，新模块凡有 CN 对等数据（如 A 股公告/大宗）即为增层点。
5. **诚实回退**：覆盖缺口显式计数（CUSIP→ticker 68/118、退市回退），不静默填充。

## 4. P0：政客交易（STOCK Act）数据源尽调结论（委派代理 G 实施）

参照站 /congress 字段模型（实探）：议员卡（照片/党派/州/议院/配偶·共同标记）+ 动作徽章（买入/卖出部分/卖出全部/**待解析**）+ ticker+资产名 + 资产类型 + 金额区间（$1K–$15K 档）+ 推算价格 + **迟报天数（>45 天 ⚠）** + 交易日期；聚合：最活跃议员榜/热门标的/迟报统计；"官方三源聚合"。

Aionis 实施纪律：
- **一手公共源 only**：House Clerk PTG（disclosures-clerk.house.gov）、Senate eFD（efdsearch.senate.gov）、行政官员披露。第三方聚合站（capitoltrades/unusual-whales 类）license 不透明 = G1 挂，禁用。
- **PDF 是已知风险**：交易明细常以 PDF 载体存在。代理 G 必须先**尽调端点**（真探针、记录证据），机器可读则实现，纯 PDF 则诚实降级为"申报流级"（议员+日期+文档链接，无交易明细）并在 methodology 披露——**不做 PDF 强解、不引入付费/不清 license 的解析服务**。
- 7-gate 文档（docs/data-intake-*）先行，mode=exploratory，display-only。

## 5. 优先级阶梯（后续数轮的总谱）

| 级 | 项 | 理由 |
|---|---|---|
| **P0（本轮）** | G 政客交易模块；H 快赢组（cmdk 4 新路由 + CUSIP→ticker 提升）；I 8-K 重大事件流 | 关闭唯一 planned；导航完整度；事件族补齐（复用 EFTS 三代先例） |
| P1 | /ipo 美股新股日历；/stars 目录扩展（12→40+ 位，八分类，/manager/CIK 详情页） | EDGAR 公共域；参照站人物生态是其特色 |
| P2 | /news 独立页（GDELT）；/quarterly+/annual 财务流；/companies 目录（字母索引）；/managers 申报流 | 它自己的 annual/companies 也是空壳，低紧迫 |
| P3 | 「势力阵营」对等物 = **关系图谱的 Aionis 版：因子→证据→裁决血缘图**（把 provenance 链可视化为图谱） | 它未上线；Aionis 溯源思维的主场 |
| 业主门 | E3 forward-live（AUD-06+GO）、Track A 因子生成器、Track LLM | 研究线，非 display lane，**不随对齐工程自动推进** |

## 6. 本轮代理调度（2026-08-21，三路 worktree 隔离）

- **G（politician-trades）**：尽调官方端点 → ingest（http_policy ≥2s + 幂等 cache）→ export 面板 + data_health/api_catalog 毕业 → /congress 视图 + i18n + 契约测试。
- **H（quickwins）**：cmdk 补 heatmap/institutions/data-health/api-docs 四路由；form13f CUSIP→ticker 有界提升（EDGAR 快照精确名匹配，诚实上限披露）。
- **I（8-K events）**：EFTS form=8-K 近窗流（复用 form4/13D 模式）→ Item 分类（primary doc 正则，诚实"未分类"）→ /events 视图。

集成纪律（历轮教训固化）：worktree 不跑 next build（Turbopack 拒跨根 node_modules）；agent 交 tsc/eslint + 边界 pytest；**主线集成时全套 pytest（agent 改共享函数后只跑边界文件曾漏回归）**；清理 worktree 先 `cmd /c rmdir` 摘 junction 再删目录；dict.ts 增量 key 靠自动合并。

## 7. 边界声明

本路线图 = display + 数据导出 lane 的方向文件。0 ledger / 0 frozen / 0 config / 0 prereg / 0 OOS 改动；不消费参照站任何数据/接口；研究线推进仍需业主显式 GO。
