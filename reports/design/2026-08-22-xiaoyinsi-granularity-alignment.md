# 2026-08-22 — 参照站颗粒度对齐：数据呈现与 UI 设计学习（方向文件）

> 定帧：业主指令"跟参照站对齐颗粒度，学会该网站的数据呈现与 UI 设计"。基建线（部署/runner）
> 搁置，全部决策存档于 `2026-08-22-realtime-deployment-architecture.md` §10-§12，随时可回。
> 本文 = display lane 方向文件（PROPOSED），实施阶梯见 §7，待业主 GO 后按多代理纪律分片。
> 方法：参照站 18 页设计级逐页解剖（列 schema/筛选/徽章/格式/密度/交互，WebFetch 文本层；
> 颜色等纯视觉属性不可见处已标注）× Aionis 视图组件 + 已提交 JSON + 契约测试代码级盘点。

---

## 1. 参照站设计语言提炼：十个可迁移模式

| # | 模式 | 参照站实例 | 迁移价值 |
|---|------|-----------|---------|
| P1 | **页头副标题内嵌计数+时间窗** | 「高管与董事交易披露 · **24 小时交易 4,780 笔**」「STOCK Act 披露 · **近 90 天**」「共 938 只标的上榜 · 近 24 小时」 | 高——一眼锚定数据规模与新鲜度，Aionis 的 SegmentHeader 正缺这一层 |
| P2 | **KPI 统计卡前置** | congress 四卡（2,019 笔/买 916/卖 1,054/迟报 73）；insider 买卖占比条 | 高——Aionis 部分页面已有，需全站统一 |
| P3 | **侧栏聚合 widget** | congress「最活跃议员 Top10 + 热门标的 Top10（带 ↑买↓卖 分解）」；ipo「募资 Top5」 | 高——从表格配角升级为导航入口 |
| P4 | **筛选/搜索全 URL 化** | `?board=wallstreetbets` `?action=买入` `?type=13d` `?status=priced` `?cat=value` `?letter=A` `?q=MSFT` `?page=2` `?tab=changes` | 中高——可分享可收藏；Aionis 现状是零筛选（除 companies 的客户端态） |
| P5 | **分页 40-50 行/页 + 区间计数器** | 「1–40 / 34,313 笔」「1–50 / 8,741 家」 | 高——长列表的正确形态；Aionis companies 已有 Load-more 先例 |
| P6 | **数字/日期/空值三统一** | 金额 `$T/$B/$M/$K` 美式缩写（从不用亿/万）+ 千分位；日期三粒度（流页 `MM/DD HH:MM` 标时区、短 `MM/DD`、ISO 报告期）；**空值统一 `—`** | 高——Aionis 现状 toFixed/toLocaleString 散用、日期 ISO 原串直出 |
| P7 | **徽章分类学** | 方向三体系（买入/卖出；建仓/增持/减持/清仓；主动/被动/清仓/降至5%下）+ 党派 + 关系（共同/配偶）+ **⚠ 迟报（>45 天阈值 + KPI 计数，实例 485/491/498 天）** + 状态机（IPO 四态、TACO 等级 `↑↑/↑/正常/↓↓`）+ `✓/✗` 回测 | 高——Aionis 有 badge-up/down 雏形，缺体系化 |
| P8 | **行级深度交互** | 整卡 = EDGAR filing 外链（insider）；可折叠块（stakes「申报依据/联合申报」展开 ▾）；头像缩写（WB=姓名首字母） | 中高——insiders 页 Aionis 行级无 EDGAR 链 |
| P9 | **空态 = 列头先于数据渲染** | /events /quarterly /companies 空页仍渲染完整列头 + 「数据暂不可用」 | 中——schema 先行，诚实且可读 |
| P10 | **页脚方法学脚注** | 占比算法（「按前 50 大持仓市值合计」）、13F 滞后 45 天免责、IPO 计划值免责、调仓推导方法学（「相邻两季相减，非逐笔成交」） | 高——与 Aionis 方法学纪律天然同构，直接吸收 |

## 2. 三张标杆页的范式拆解（对齐基准）

**/congress（全站信息密度之王）**：KPI 窗口计数 → 热门标的标签（买/卖双数）→ 四维筛选（党/院/买卖/12 类资产）+ 标的搜索 → 40 行分页（全库 34,313）→ 侧栏双聚合（最活跃议员/热门标的带方向分解）。复合单元格范式：申报人 = 姓名+党派·州·院别+关系标记；金额 = 法定区间八档（$1K–$15K…$1M–$5M）非精确值；⚠ 迟报天数修饰。

**/insider（行卡范式）**：头像缩写+姓名+职务 → 公司代码+全名 → 买/卖徽章 → 金额（$145.6M 一位小数）→ 股数千分位 → MM/DD；**整卡 = SEC filing 外链**；同公司多高管密集卖出自然聚簇成信号。

**/stock/NVDA（模块顺序范式）**：报价头（价+当日▼+行业徽章）→ 半年日线走势（标注区间高低）→ Key stats 横条 → **机构持有者表**（前 10 大+集中度口径脚注——当前空壳「共 0 家」）→ **政客交易 join**（近 8 笔+全部出口+三院别 PDF 原文链）→ **四子分评分卡**（综合 A·81.5 同业百分位 + 盈利 97/成长 100/估值 32/健康 63，as-of 日期）→ 公司资料。

## 3. Aionis 现状与资产盘点

**颗粒度硬差距（代码级实锤）**：
- 六个流式面板**全部无筛选、无搜索、无分页**，一次性渲染导出上限：congress 100/874、events 23、ipo 150/1046、insiders 50/16,564、smart-money 60/14,475、reddit 7；上限源头在 `export_terminal_data.py` 的 `head(50)/[:60]/head(150)/head(100)`。
- 仅 **/companies** 有完整交互三件套（region 药丸 + A-Z + 搜索 + Load-more 50/页 + 计数行）——**模式已在本仓验证，缺的只是移植**。
- 无统一格式层：fmtUsd 只存在于 manager-book.tsx 局部；日期 ISO 原串；空值呈现不一致。
- insiders 行级无 EDGAR 外链；congress 无侧栏聚合（top_members 12 人是徽章行非 widget）。
- /stock 页缺机构持有者与政客交易 join（前者数据已就位可立即做，后者需交易级）。
- 文案债：insiders dict 写「近 2.5 年」但 JSON window 是 2013-03..2026-08。

**Aionis 独有资产（对齐时保留，不因学习而回退）**：SegmentHeader 论证链定位 + ProvenanceBadge（时钟/锁二分）、NullDisclaimer、出生证明（ledger #49/sha）、zh/en 双语、`--up/--down` 涨跌约定 + cn 切换、tabular-nums、WCAG AA 对比纪律、Apple HIG token 体系与毛玻璃材质、GuardBand。**参照站全站零溯源零双语零暗色——这是它的弱项，不是我们要学的东西。**

## 4. 对齐矩阵（12 模块）

| 模块 | 参照站呈现 | Aionis 现状 | 对齐动作 | 层级* |
|------|-----------|------------|---------|:--:|
| /congress | 交易级 34,313、四维筛选+搜索、40/页、⚠ 迟报、侧栏双聚合 | 申报流级 874（可见 100）、无筛选、无侧栏 | 党派筛选+分页+计数；top_members 升级侧栏；全量 874 导出；⚠ 与热门标的=**交易级数据门** | 前端+导出 |
| /events | **全市场实时流**（⚠️ 08-22 浏览器复核订正，原判"空壳"系客户端渲染前误判）：波音/诺格/微盘股全谱、分钟级时间戳、公司+类型+时间三处 EDGAR 直链、12+ 中文类目多标签 `·` 连接 | 23 事件/5 issuer，类别徽章 | 类别筛选（数据已够）；**发行人广度差距巨大 = 抓取端主攻**（非"领先"） | 前端 |
| /ipo | 67 家、状态 tab、KPI 四连、募资 Top5 侧栏 | 1,046 申报（可见 150）、无筛选、无价/募资/上市日 | status tab（对齐 by_status 口径）；全量导出+分页；侧栏诚实替代（by_form 聚合/最近定价榜）；价与募资=**不解析 prospectus（维持 v1 决策）** | 前端+导出 |
| /companies | 空壳（0 家，宣传 1700+） | 1,421 全宇宙 + 完整交互 | **已领先，无需动** | — |
| /institutions | 8,741 家、50/页、AUM T/B | 40 位策展 + 类别 chips | 现有形态保留（策展叙事 > 全量目录，§08-21 roadmap 既定）；补 A-Z/搜索可后续 | 前端（可选） |
| /manager/[cik] | 双 tab（持仓/调仓）、KPI 三卡、前 50 大、集中度 widget、Δ市值+环比复合格 | Top10 表 + changes 四态芯片 + category | 加 KPI 计数行与集中度条（数据已有）；调仓 tab 化（现 ChangesBlock）；Δ市值=导出端加字段 | 前端+导出 |
| /stock/[ticker] | 机构持有者表+政客 join+四子分评分 | 模型读数+走势+板块语境+佐证计数+live 价 | **加机构持有者模块（form13f 按 ticker 反查——参照站此模块空壳，反超点）**；政客 join=交易级门 | 前端（join） |
| /insiders | 24h 4,780 笔、头像缩写、买/卖 tab、整卡 EDGAR 链 | 16,564 笔窗口（可见 50）、5 issuer、无链无筛选 | buy/sell 筛选+分页；**导出加 doc_url（orchestrator 已缓存 accession）**；头像缩写；recent 50→200；广度=抓取端；「近 24h」窗=抓取节奏门 | 前端+导出 |
| smart-money(13D) | /stakes：13D+13G 4,417、主动/被动/清仓/降线下状态机、可折叠申报依据 | 13D only、recent 60、ticker 徽章 | 13G 流+状态机=**抓取端**；new/amendment 筛选=前端 | 前端+抓取 |
| reddit | 938 标的、24h 窗、热力图、四统计卡 | 7 picks/1 快照（RSS 无 score） | 数据深度是根本瓶颈（=抓取 cadence 门，与基建 §11 阶梯 2 合流）；前端可加板块/方向筛选 | 抓取 |
| /dashboard | Hero+双 KPI+模块卡+[更多→]出口 | Hero+裁决锚+论证链四卡+佐证 | 跨面板「模块卡+[更多→]」出口模式可吸收进 overview（低优先） | 前端（可选） |
| executives/quarterly/annual/news | executives 60 条；/quarterly 真空（0 份）；**/annual 实为 102 份实时流**（⚠️ 08-22 订正）；news SSE | 未建（executives）/M-N worktree 在途（quarterly/annual/news） | **不重复起线**；executives = form8k 加 Item 5.02 分支（roadmap 既定）；/annual 有活的竞品参照 | 抓取 |

\* 层级图例：**前端**=纯 web/src；**导出**=export_terminal_data.py+契约测试；**抓取**=新 ingest 链；**门**=数据不可得或业主门（交易级 PTR=D4）。

## 5. 取舍原则：学什么、不学什么

**学（信息设计层）**：P1-P10 全部模式——密度、格式统一、徽章分类学、分页惯例、侧栏聚合、复合单元格、头像缩写、折叠详情、⚠ 修饰、空态列头先渲染、方法学脚注。

**不学（视觉层 + 已知瑕疵）**：
1. **视觉皮肤不换**——参照站是默认 Tailwind 质感、无暗色、无双语、无对比度纪律；Aionis 保留 Apple HIG token + WCAG + `--up/--down` 约定体系。一句话：**参照站的骨架 × Aionis 的皮肤与溯源**。
2. 双视图（卡片流+同构表格双份 DOM）——SSR 朴素实现的副产物，DOM 冗余，不学。
3. KPI 窗口与列表窗口不一致（2,019 笔 90 天 vs 34,313 全库两套计数并存无标注）——Aionis 实现时**每个计数必须标注口径**。
4. 徽章中英混用（executives 上任/resigned）——Aionis 有 i18n 枚举映射先例（CATEGORY_LABEL），坚持全键化。
5. 空承诺（宣传 1700+ 实际 0 家）——Aionis 的诚实空态纪律不回退。

**叠加而非替换**：参照站 模式落在 SegmentHeader/ProvenanceBadge/NullDisclaimer 之下——页头计数窗（P1）放进 SegmentHeader 副标题位，KPI 卡（P2）接在其后，溯源徽章保持页头可见。语义色纪律（emerald=信任/rose=风险/amber=警示）不挪用方向色，方向一律走 `--up/--down`。

## 6. 全站级基建动作（一次建好，全模块复用）

1. **`web/src/lib/format.ts` 统一格式层**：`fmtUsd`（$T/B/M/K，1-2 位小数——从 manager-book 泛化）、`fmtCompact`（计数千分位）、`fmtDate`（三粒度：流页短日期、精确到分、ISO 报告期）、`fmtEmpty`（统一 `—`）。全模块接线替换散用的 toFixed/toLocaleString。
2. **流式面板交互三件套组件**：`FilterPills`（枚举筛选，含诚实计数）+ `SearchBox` + `PagedTable`（Load-more 50/页 + 「shown / total」计数行）——从 companies-view 泛化为共享组件。
3. **徽章扩展**：`⚠` 警示修饰（带阈值 title）、四态方向徽章（建仓/增持/减持/清仓已有语义）、折叠详情行（Disclosure 组件复用 Radix Collapsible——已有依赖检查：若无则用 details/summary 零依赖方案）。
4. **页头计数+窗口惯例**：SegmentHeader 增 `countHint` 槽（"874 份申报 · 2025–2026 · 申报流级"），i18n zh/en。

## 7. 实施阶梯（每片独立可验收、可分派代理）

**P0（纯前端 + 小导出改动，1-2 天/片）**：
1. §6-1 格式层 + 全模块接线（含 insiders「近 2.5 年」文案债修复）
2. §6-2 三件套移植五面板：congress（党派筛选+分页）/ insiders（买/卖+分页）/ ipo（status+分页）/ events（类别）/ smart-money（new/amendment）
3. §6-4 页头计数窗全站统一
4. **/stock 机构持有者模块**（form13f ticker 反查：持有该股的策展管理人 Top10 + 市值 + 占比 + 集中度口径脚注——参照站同位空壳，**反超点**）
5. insiders 行级 EDGAR 外链（导出加 doc_url 字段，orchestrator 缓存已有 accession）

**P1（导出扩容 + 徽章深化，2-4 天/片）**：
6. 导出上限：congress 100→874 全量（payload ~+140KB，安全）、ipo 150→1046（~+110KB）、insiders 50→200、smart-money 60→120；**契约测试同步**（smart_money `==60` 精确钉改范围钉；ipo 可见行断言改全量）
7. 徽章深化：insiders 头像缩写+职务、manager 调仓 Δ市值（导出加 delta_value）、congress top_members 升级侧栏 widget（含党派着色 mono）
8. ipo 侧栏诚实替代 widget（by_form 聚合 / 最近 424B4 定价榜）

**P2（抓取端/数据门，独立 lane）**：
9. 13G 流 + 主动/被动状态机（对齐 /stakes 形态）
10. insiders/events 发行人广度分层扩展（礼貌预算内）
11. executives 模块（form8k Item 5.02 分支）
12. reddit 深度（依赖抓取 cadence——与基建 §11 阶梯 2 合流）
13. congress 交易级 + ⚠ 迟报 + 热门标的（D4 门：`agent/politician` salvage 分支）

**边界（全阶梯不变）**：display lane；0 ledger/frozen/config/prereg/OOS；冻结面板语义不动（扩容只动日更/节奏面）；礼貌纪律继承；M/N 在途模块（news/quarterly/annual）不碰。

## 8. 契约测试影响清单（实施时必改）

| 测试 | 现钉内容 | 改动 |
|------|---------|------|
| `test_smart_money_yearly_when_present` | recent_filings **==60 精确** | 改范围钉（60→120 后更新） |
| `test_form_ipo_panel_contract` | 可见 150 行 ≤ by_status | 全量导出后改相等断言 |
| `test_politician_trades_panel_contract` | 无可见行数断言（只钉排序/字段） | 加全量可见断言 |
| `test_form4_status_and_shape` | window 非空字符串 | doc_url 加入字段集断言 |
| form13f | ticker_coverage 重算一致 | stock join 不改面板，新增消费侧 |
| 全部 | — | 格式层纯前端，零测试影响；页头计数窗需 dict key 增补 |

验证链（项目惯例）：pytest 全套 + ruff + tsc + eslint + next build 全路由 + 本地静态服务浏览器实测。

## 9. 业主 GO 请求

- **GO P0 五片**？（纯展示层 + 两个导出字段级增补；建议分两批代理派发或主线直做）
- P1 随后；P2 各片自带 7-gate/尽调流程。
- 设计定帧确认：**参照站的骨架 × Aionis 的皮肤与溯源**（§5）——若业主想要更彻底的视觉同构（连皮肤也学），请明示，那是一次独立的 token 层重构。

### 9.1 交付记录（同日，业主 GO 后主线直做）

P0-1～P0-4 全部落地 + 验证链全绿（tsc 0 / eslint 净 / build 1,491 HTML / pytest exit 0 /
IAB 实测交互三页）；P0-5 因 form4.recent 无 accession 字段降级为跟进片（导出端补 doc_url）。
§10 的浏览器复核在实施**之前**完成并订正本文档两处误判。明细见 state/handoff.md (e)。

---

## 10. 实施前浏览器复核订正（2026-08-22 晚，IAB 实测 + DOM getComputedStyle）

> 业主实施授权附带硬条件："确保真的读懂了参照站，不能因为没访问到就下判断胡说。"
> 复核方法：IAB 真实浏览器逐页 domSnapshot（客户端渲染等待 2.5-3s）+ 截图 → 视觉模型盲审
> + `getComputedStyle` 颜色/字体实测（历史既定双通道，防视觉模型幻觉）。截图存
> `runs/xys-design/`（gitignored）。

### 10.1 空壳判断订正（原文两处已改，此处留档）

| 页面 | 原判（WebFetch 文本层） | 浏览器实测真相 |
|------|----------------------|---------------|
| /events | "空壳，数据暂不可用" | **❌ 误判**——全市场 8-K 实时流：波音/诺格/Phillips 66 到微盘股全谱，分钟级时间戳（08/21 17:30 美东），公司名+事件类型+时间戳三处外链 EDGAR filing index，中文类目 12+（高管/董事变动、Reg FD披露、退市/不合规、签订重大协议、新增重大债务、完成收购/处置、股东投票结果、章程/财年变更、持有人权利变更、非公开发股、终止重大协议、其他重大事件），多标签用 `·` 连接，无 ticker 的行诚实 `—` |
| /annual | "双双空壳"（与 /quarterly 并称） | **❌ 半误判**——10-K 流 102 份实时在跑（OSI/Parker-Hannifin/Ubiquiti/Coty，EDGAR 直链）；/quarterly 确认真空（0 份） |
| /companies | "0 家空壳" | ✅ 属实（0 家 + A-Z 26 链 + 搜索框列头先渲染） |
| /stock 机构持有者 | "共 0 家" | ✅ 属实（列头+口径脚注渲染、数据暂不可用）——**反超点维持** |

**根因教训**：WebFetch 抓的是 SSR 首帧，客户端取数未完成时显示"数据暂不可用"占位——
凡"空壳"结论必须浏览器复验（本节即执行）。此前"五处空白/我们在 /events 领先"的表述作废；
真实空白 = /quarterly、/companies、势力阵营、/stock 机构持有者四处。

### 10.2 视觉层实测（此前两轮抓取不可见的部分）

- **暗色为默认**：`body` 背景 `rgb(0,0,0)`（OLED 纯黑）、正文 `rgb(237,237,237)`；此前"#fafafa
  theme-color"只是 meta 标签，非实际观感。无明暗切换、无语言切换（仅 /news 有 lang tab）。
- **字体**：GeistSans + **GeistMono**（数字等宽，Vercel 家字体自托管）。
- **党派徽章 = 美式浅底填充**（DOM 实测）：民主党 字 `rgb(71,168,255)`/底 `rgb(6,32,63)`、
  共和党 字 `rgb(255,86,95)`/底 `rgb(43,11,14)`；10px/600/圆角 4px（方角微圆，非胶囊）。
- **方向徽章**：视觉报告绿买红卖（行内），筛选 tab 为灰色 12px——注意这是"动作色"非"涨跌色"。
- 表头吸顶、无斑马纹、细分割线、行高 ~40px 高密度、KPI 大数字、侧栏圆形头像——视觉模型与
  DOM 一致的部分采信。

### 10.3 对本文件 §5-§7 的增量影响

1. /events 行动从"领先"改为"**追赶广度**"（Aionis 5 issuer vs 全市场）——抓取端优先级上调。
2. 徽章对齐增加一条具体规格：党派徽章可采纳**浅底填充式**（Aionis 现为 mono 描边 R/D），
   蓝/红取 Aionis 既有 token（--primary 系蓝 + rose 系红），4px 圆角、10-11px/600——
   纳入 P0-2 congress 片。方向徽章维持 Aionis `badge-up/down` 体系（不学其绿买红卖，
   Aionis 有 colorconv 双约定，动作色走方向色语义已定）。
3. 字体不跟（Geist 需自托管网络字体，Aionis 系统栈是既定取舍）；暗色不跟（Aionis 双主题
   已是超集）。
