# TASK-DISP-J — ARK ±pp 增量面板升级：条件触发式设计规格

**Lane**: display / design-only（纯设计，零代码）。日期 2026-08-27。
**状态**: 前瞻规格 —— 被 H1（GitHub Actions 计费冻结，见 `state/blockers.md` 08-21/08-22 条目）
阻塞。本文全部内容以「**刷新恢复且本地快照 ≥ N 个不同交易日**」为前置；在此之前不改任何
生产行为（§6 承诺）。启用只需一个后续小构建任务，输入清单见 §6。

---

## 0. 实测背景（本规格的地基）

- 参照站 roadmap §1 记录（`reports/design/2026-08-25-post-parity-roadmap.md` L49/L54）：
  参照终端有「ARK 异动 ±pp 30d」，Aionis 只有当日快照——ARK 官方不留 CSV 历史，本地日期
  快照积累后才可计算。
- **实测 `data/cache/ark_holdings/`（2026-08-27）：恰好 8 个 CSV、全部 `{TICK}_20260821.csv`
  同一天**（ARKK/ARKQ/ARKW/ARKG/ARKF/ARKX/PRNT/IZRL × 20260821）。Actions 计费冻结使
  refresh-terminal-data workflow 停摆，快照自 08-21 起未继续积累。
- 因此本规格是**条件触发式**：计算逻辑与前端形态现在定死（避免将来临场设计），但导出器
  内全部增量路径置于统一门槛之后；门槛未达时代码路径不可达、产物 schema 与今天逐字段一致。

## 1. 七问逐一回答

### Q1 ±pp 计算定义（权重基准、快照对选择、new/exited 表示）

**权重基准**：同一基金内、ARK 官方 CSV `weight (%)` 列的原样发布值（`parse_csv` 已解析为
浮点百分位点，如 `"9.24%"` → `9.24`）。**绝不**从 `market value ($)` 或 shares 重算权重
（那会混合口径）；两侧使用完全相同的已发布口径。

**匹配键**：单基金内按 `ticker` 字符串精确相等连接两个日的持仓簿。不用 CUSIP 作主键
（warrant/unit 行存在 dummy ticker，如 ARKK 书内实测 BREADUMMY 行）；若某标的换 ticker，
如实呈现为一对 exited + new（被计数、被披露），绝不猜测合并。

**数学定义（一句话版）**：
> Δpp(ticker, F) = w₂ − w₁ ，其中 w₁、w₂ 为同一基金 F 在 D₁（前一可用快照日）、
> D₂（最新可用快照日）两日官方公布的该标的权重百分位点；结果经 Decimal ROUND_HALF_UP
> 量化到两位小数后入库。

精度规则：
- 计算顺序：先浮点减法 `w2 - w1`，再 `Decimal(str(raw)).quantize(Decimal("0.01"),
  ROUND_HALF_UP)`。选 ROUND_HALF_UP（而非 Python 默认银行家舍入）因为展示契约要求
  与人类直觉一致且可被测试精确复现（Q5-3）。
- `-0.0` 归一：`abs(delta) < 0.005 → 0.0`（消除浮点残差伪 `-0.00`）。
- 连续持有且四舍五入后未变的仓位 Δ=0.00 允许出现（真实事实，中性色调渲染）；
  被禁止的是把 new/exited 显示成 ±0.00（下述表示规则 + Q5-4 测试双重封死）。

**快照对选择规则（缺失日跳过、如实披露）**：每基金独立执行——
1. 枚举 `{TICK}_{YYYYMMDD}.csv`（沿用 `export_ark` 现有 regex 枚举）；以 **CSV 内部解析出的
   `as_of`** 为权威日期键分组（fetch 脚本按同字段命名落盘，二者构造性一致；不一致的文件
   跳过并计数披露，防御手改缓存）。
2. 升序排列该基金可得的不同日期；取 D₂ = 最大值，D₁ = 严格小于 D₂ 的最大可得日
   （**最新 vs 前一可得日**）。中间缺席的交易日直接跳过，**绝不插值、绝不虚构缺失日**；
   缺席通过暴露两个端点日期诚实呈现（UI 一眼可见实际跨度），payload 另带
   `gap_days`（D₂−D₁ 自然日差）与全库 `n_distinct_days` 计数。
3. 两日内同日重复文件（若有）任取其一并计数披露。

**new / exited 表示（绝不显示为 ±0.00）**：
- 连续持有：`change_kind:"continued"`，`delta_pp:数值`，另带 `weight_prev_pct`（上一日权重，
  供对账测试闭环验证，成本可忽略）。
- 新进（在 D₂ 簿、不在 D₁ 簿）：`change_kind:"new"`，**`delta_pp:null`**，
  `weight_prev_pct:null`；展示为琥珀色「新进/NEW」徽章 + 当前权重。不编造「+w₂.00」。
- 清仓（在 D₁ 簿、不在 D₂ 簿）：不进 per-position 行；进基金级 `exited:[{ticker, company,
  weight_prev_pct}]` 披露行（delta 字段在该结构中根本不存在）。动量卡可收录清仓为
  `change_kind:"exited"` 行，但同样 **无合成负 pp 数字**——排序量按清仓规模
  `weight_prev_pct`。理由与仓库反伪造文化一致：±pp 只对可比状态（连续持有的两日权重）有
  定义；非连续状态的「幅度」用其真实规模表达并打标签。

### Q2 数据结构：来源、函数归属、payload 预算与 barrel 纪律

**历史数据来源：现有 `data/cache/ark_holdings/*.csv` 日期文件直接可用，不需要新索引文件。**
论据：`export_ark` 已经每次运行枚举该目录（regex 过滤 + 最新日选择），增量仅是「再多留一列
次新日」；数月积累也只是数百个小 CSV（每个 ~5-8KB），glob 成本可忽略。新增索引文件反而
引入第二真相源（需维护索引与目录的一致性 = 违背 record-once 精神）。

**函数归属：升级现有 `export_ark`（加法式扩展 schema），不新建 `export_ark_momentum`。**
论据：
1. 快照视图与异动视图必须共享同一 `as_of` 与同一份 fund 解析结果——拆成两个 JSON 会引入
   双面板 as_of 漂移风险（每次刷新各自的 SKIP 守卫独立失败时）；
2. 实测体积：现 `web/src/data/aionis/ark.json` = **19,658 B**。加法项上限估算：
   top 行加三标量字段（8 基金 × 10 行 × ~45B ≈ 3.6KB）+ exited 列表（稀有）+
   `top_movers` ≤8 行（~1.2KB）→ 总量 ~24KB，仍属小面板；
3. barrel 纪律实测结论（`web/src/data/aionis/index.ts` L8-14 注释）：合并 barrel 是**默认正解**
   （Turbopack 对单一模块去重进共享 chunk；具名再导出会使每页 chunk 复制数据，实测每页
   +50-280KB）。专用模块是**大 payload 特例**：form13f.ts（~650KB）、filers13f.json（1.6MB）、
   form13f-stars.ts（首页摘要 ~2KB 先例）。
4. **边界写明（防将来越界）**：若未来建「全簿 deep-diff / 多窗口滚动历史表」（随快照数
   无界增长的内容），那才是新的 `ark_history.json` + 专用 `web/src/data/aionis/ark-history.ts`
   模块（照 form13f-stars.ts 先例）——明确不在本规格范围。
5. `_safe_export("ark", export_ark)` 注册链零改动；panel 目录/catalog 无新条目。

**纯计算函数落位**：快照对选择与 Δ 计算写成纯函数、放在 `src/aionis/ingest/ark_holdings.py`
（`parse_csv` 旁）。理由：该模块本就是 display-lane 注明的模块，exporter 已从此导入
`FUND_CSV_URLS, parse_csv` 且注释承诺「cache 与 JSON 对行语义永不分歧」——计算逻辑同理
必须与解析器同居一处；纯函数也让 Q5 的数学测试可以脱离网络、用标注 mock 的合成 fixture
hermetically 钉死（仓库允许 mock 仅作单测 fixture）。

**schema 加法（开启时的完整形态）**：
```jsonc
{
  // …现有字段原样保留…
  "momentum_on": true,
  "window": {                       // 全库窗口元数据
    "curr_as_of": "2026-09-05",
    "prev_as_of":  "2026-08-28",    // 全库最大前一可得日（各基金可为更早，见 fund.momentum）
    "gap_days": 8,
    "n_distinct_days": 7,           // 触发判据的如实读数（全库不同日期并集）
    "min_days_required": 5,
    "pair_selection": "latest_two_available"
  },
  "top_movers": [                   // ≤8 行；家族级去重后的 top 异动
    { "ticker": "TSLA", "company": "TESLA INC",
      "fund": "ARKK",               // Δ 归属的那只基金（具体可溯源，拒绝合成跨基金复合数）
      "funds": ["ARKK","ARKW"],     // 该标的当前被哪些基金持有（保留家族共振信息）
      "weight_pct": 9.24,           // 归属基金的当日官方权重
      "delta_pp": 0.83,             // 数值 | null（new/exited 时 null）
      "change_kind": "moved",       // "moved" | "new" | "exited"
      "weight_prev_pct": 8.41 }     // moved/new 时为其对应端权重；exited 时为清仓前权重
  ],
  "funds[i]": {
    "momentum": { "prev_as_of": "2026-08-28" } | null,   // null = 该基金不足两日（罕见：连续同日失败）
    "exited": [ { "ticker": "…", "company": "…", "weight_prev_pct": 4.91 } ],  // 可为 []
    "top[j]": { /* 现有四字段外新增 */ 
      "delta_pp": 0.83 | null,
      "change_kind": "continued" | "new",
      "weight_prev_pct": 8.41 | null }
  }
}
```

**关闭时（`n_distinct_days < N`）这些键整体不存在**——不是空数组/null 壳，而是 schema 回到
今天的逐字节形状（诚实降级的强形式，见 Q4/Q5-1）。

**movers 排序量定义（防歧义）**：salience = moved→`|delta_pp|`；new→当日权重 `weight_pct`；
exited→`weight_prev_pct`（清仓规模）。降序，并列以 (ticker, fund) 字典序稳定化。
家族级去重：按 (fund, ticker) 对排序后，每 ticker 只保留 salience 最高的一对；其余持有基金
进 `funds[]` chips，多基金各自 Δ 写入行 `title` 提示文本。方法论字符串写明：卡片展示的是
某一具体基金账本的 Δ（可溯源），不做跨基金加权合成（那是发明数字）。

### Q3 前端形态（精确改动清单）

**涨跌色约定（先行约束）**：方向色**只能**用 `globals.css` 的 `--up/--down` 体系工具类
（`.text-up/.text-down/.bg-up/.bg-down`），即 `[data-colorconv="cn"]` 红涨绿跌切换自动生效；
禁止硬编码 emerald/red 作方向色（globals.css 注释明文：numeric direction sites 只许用这组）。
中性 Δ=0.00 用 `text-mute`。

**(A) `/institutions` ArkSection** — `web/src/components/institutions/institutions-view.tsx`
L36-145（组件内改动，签名不动）：
1. 类型扩展在 `web/src/data/aionis/index.ts`（ArkPosition / ArkFund / Ark 三型加可选字段，
   显式类型契约含真实可空性——遵守该文件头「never `as typeof json`」红线）。
2. 头部 meta 行：`momentum_on` 时追加窗口徽章 `{as_of} · vs {window.prev_as_of}`（新 i18n 键，
   保留现有 as_of 主位）。
3. 每持仓行右列在权重后追加：符号化 Δ 文本（`+0.83` / `-1.20` 显式正负号、tabular-nums、
   `.text-up/.text-down` 上色）+ **40px 迷你幅度色条**（`bg-muted` 轨道，填充长度 =
   |Δ|/maxAbsΔ(fund)，填充类 `.bg-up/.bg-down` 按符号——长度编码幅度、颜色编码方向，
   不做居中基线双臂条，因行高仅 ~20px 不容纳）。行尾布局：bar 的 `flex-1` 相应缩短，
   `xl:grid-cols-4` 卡片宽度足够（实测空间余量）。
4. new 行：Δ 文本与色条整体替换为琥珀 outline Badge「新进/NEW」（`text-[10px]`），
   `title` 注明入场权重。
5. exited 披露行：卡片底部追加一行小字「本期清仓 k：TICK1（原 4.91%）、… 」，
   k>4 折叠为「及另外 n 只」；仅当 `exited.length>0` 渲染（新 i18n 键）。
6. **零行为变化分支**：`!momentum_on` 时走与今天逐 DOM 节点一致的早退常量渲染（不得引入
   条件 wrapper/类名切换）——像素级不变。

**(B) 首页 ARK 卡 ArkCard** — `web/src/components/overview/overview.tsx` L670-728：
1. `momentum_on && top_movers.length>0` 时：
   - 数据源 `family_overlap.slice(0,6)` → `top_movers.slice(0,6)`；
   - 行解剖替换：`[ticker][company][funds[] chips][64px 幅度色条 bg-up/bg-down][符号 Δ 文本]`
     （原「N 基金同持」计数条与单基金最高权重列退役于该模式）；
   - 标题换新 i18n 键 `overview.ark.title_moves`（zh「ARK 基金仓位异动」/ en "ARK position
     moves"——对齐参照站模块名）；meta 追加 vs 窗口；行 `title` 含多基金明细 Δ。
2. 否则**精确保持现行共振卡**渲染（同源同解剖），含兜底：`momentum_on` 但 movers 空
   （病态全零场景）→ 回退共振路径，绝不出空白卡。
3. 「全部 →」链接目标 `/institutions` 不变。

**(C) `web/src/i18n/dict.ts`** 新增键（zh+en 双语各一处）：`overview.ark.title_moves`、
`overview.ark.moved_note`（一行口径披露「较前一可得快照日」）、`institutions.ark.vs`、
`institutions.ark.new_pos`、`institutions.ark.exited_line`、`institutions.ark.exited_more`。
删除/改名既有键：**零**（旧文案继续服务关闭态）。

### Q4 触发判据（自动化友好）

**推荐 N = 5 个不同交易日（全库并集口径），且各基金独立要求 ≥2 日配对。**

自动化判定（exporter 每次运行自检，无需人工）：
```
distinct_dates = ⋃_{tick∈FUND_CSV_URLS} {parse_csv(f).as_of : f ∈ cache/{tick}_*.csv}
momentum_on = (len(distinct_dates) >= 5)
per-fund 配对独立成立（该基金自身不同日 ≥2），否则该 fund.momentum=null 单独降级
```
**推荐 5（而非 2 或 30）的理由**：
- 下限 2 数学上即可计算，但 2–4 日窗口噪声主导：ARK 权重日间漂移混入被动价格波动
  （TSLA/COIN 级波动股单日被动漂移可达 ±0.2-0.5pp），短窗「异动」多为价格噪声，误读风险高；
  ≥5 个交易日（≈一周）真调仓信号才开始盖过漂移。
- **鲁棒性**：本次计费冻结恰好证明「缺日」会发生（节假日/fetch 失败同理）；5 给了冗余，
  启用状态不会被单日缺失反复翻转（防抖）。
- **解锁延迟**：H1 解冻后约 1 个交易周即可启用（对照 30 日需 ~6 周）——小构建任务能在
  上下文冷却前落地。
- 为什么不是 30：roadmap 的「~30 snapshots」指复刻参照站的 rolling-30d 口径；本规格有意改发
  「最新两可得日」统计（标签如实、不算复刻失败）。日后 distinct ≥21/31 天时，可加第二个
  窗口对象做 rolling-30d 加法扩展——schema 无需返工（additive）。

**<N 时导出器行为 = 维持现状输出**：整个增量代码块置于 `if momentum_on:` 之后（不可达），
tracked `ark.json` 保持今天 schema 与内容语义；绝不是空壳页面/空数组占位。

### Q5 契约测试清单（tests/test_web_terminal_data.py 风格：只读 committed JSON）

| # | 测试名 | 断言意图 |
|---|--------|----------|
| 1 | `test_ark_panel_without_momentum_keeps_legacy_shape` | `momentum_on` 缺失或假时：顶层无 `momentum_on/window/top_movers` 键；任何 fund 无 `momentum/exited` 键；任何 top 行无 `delta_pp/change_kind/weight_prev_pct` 键（深扫）。意图：门槛前输出与今天 schema 逐字段一致 → 旧消费者/页面零影响的结构性证明。 |
| 2 | `test_ark_momentum_enabled_requires_threshold_truth` | 开启时：`window.n_distinct_days >= window.min_days_required == 5`、`pair_selection=="latest_two_available"`、`prev_as_of < curr_as_of == x["as_of"]`。意图：触发不可手翻——开关开着就必须携带诚实的数字证据。 |
| 3 | `test_ark_momentum_math_self_consistent` | 每个 `change_kind=="continued"` 行：`Decimal ROUND_HALF_UP(weight_pct - weight_prev_pct, 2) == delta_pp` 精确成立，且 `weight_prev_pct>0`。意图：钉死舍入规则与权重基准（两侧同为官方发布 %），杜绝口径漂移。 |
| 4 | `test_ark_entries_and_exits_never_signed_zero` | `kind=="new"` ⟺ `delta_pp is None and weight_prev_pct is None`；所有 exited 行 `weight_prev_pct>0` 且结构上不含 delta 字段；任何位置不存在「new/exited 却显示 ±0.00」。意图：任务书红线。 |
| 5 | `test_ark_top_movers_shape_and_ordering` | 开启时：1..8 行、ticker 去重、按隐含 salience 严格降序、`row.fund ∈ funds ⊆ 导出基金集`；关闭时键不存在。意图：首页可盲渲染 + 家族去重契约。 |
| 6 | `test_ark_momentum_window_discloses_gaps` | 每个有配对的 fund `momentum.prev_as_of <= window.prev_as_of`、`window.gap_days>=1`；方法论含「previous available / 前一可得」「no interpolation / 不插值」语义且保留 no-prices/no-returns 条款。意图：缺失日跳过永远可见、展示层边界不回退。 |
| 7 | `test_weight_deltas_rounding_half_up`（新 hermetic 单测，合成 mock fixture） | 纯函数边界：0.005→0.01、-0.005→-0.01、|raw|<0.005→0.0（无 -0.0）、两位小数量化逐例钉死。 |
| 8 | `test_snapshot_pair_skips_missing_dates`（同文件） | 可得日 [d1,d3,d4] → 配对 (d4,d3)；内部 as_of 与文件名不一致的文件被跳过并计数；gap 经两端点+gap_days 披露。意图：缺日处理与防御性校验不回归。 |

约束：#1-#6 加入后，既有 85 个契约测试（尤其 `test_ark_panel_contract` L711 的子集断言
`<= set(x)` 结构）**零修改**仍然全绿——这是「加法式演进」的自我证明。

### Q6 冻结期行为承诺 + 启用任务输入

**承诺**：H1 解冻且快照 ≥5 个不同交易日前，本规格不改任何生产行为——不改
`export_terminal_data.py`、不改任何 `web/src` 文件、不改 ingest 模块；`ark.json` 的提交形态
维持今日 schema。本文件本身是 `reports/design/` 下唯一新增文档。展示链路无需
`config_committed` 台账行（runs/ledger.jsonl 管研究管线，终端导出不在其域），但接受
Definition-of-done 全量检查（测试/评审/原子提交）。

**启用 = 一个后续 S/M 级构建任务**，所需输入（清单齐全即可开工，无需再做调研）：
1. 本规格（计算定义、schema、触发判据、测试名——§1-§5）；
2. 代码触点（均已实地核实，见 §2 汇总）：`src/aionis/ingest/ark_holdings.py`（新增两个纯
   函数位）、`scripts/export_terminal_data.py::export_ark`（L5497 起，注册点 L6271）、
   `web/src/data/aionis/index.ts`（类型 L866-900）、
   `web/src/components/institutions/institutions-view.tsx::ArkSection`、
   `web/src/components/overview/overview.tsx::ArkCard`、`web/src/i18n/dict.ts`（键位
   L924-928 / L341-344 / L2164-2168 附近）、`tests/test_web_terminal_data.py`；
3. 方向色规范：只用 `.text-up/.text-down/.bg-up/.bg-down`（`[data-colorconv="cn"]` 自动
   适配红涨绿跌，globals.css L129-146）；中性= muted；
4. 运行时前置核查命令：`ls data/cache/ark_holdings/ | grep -oE '_[0-9]{8}' | sort -u | wc -l`
   ≥5（或由新增纯函数在同口径上读数）；
5. 验收标准：pytest 全绿（含 #1-#8 新测试与既有 85 项免改通过）、tsc/eslint/next build 绿、
   关闭态页面像素级不变（视觉 diff 对照 `runs/ui-iter/` 基线流程）、commits 符合
   Conventional Commits。

## 2. 现状代码事实清单（全部先读后写）

- `src/aionis/ingest/ark_holdings.py`：display-only 模块；8 条浏览器实证钉死的基金 CSV URL
  （FUND_CSV_URLS）；`parse_csv(text)→(as_of, rows[fund/company/ticker/cusip/shares/
  market_value/weight_pct], skipped)`（跳过免责声明脚注、无 ticker 行、CASHX 并计数）；
  `fetch_all` ≥2s 礼貌间隔、单基金故障隔离。
- `scripts/ark_holdings_fetch.py`：薄 runner；幂等落盘 `data/cache/ark_holdings/
  {TICK}_{YYYYMMDD}.csv`（gitignored）；注释明示「cache 即时间序列」。
- `data/cache/ark_holdings/`（实测）：8 个 CSV 全部 `*_20260821.csv`；CSV 格式首行 header、
  权重形如 `9.24%`、尾部 DISCLAIMER 整段脚注。
- `scripts/export_terminal_data.py::export_ark`（L5497，注册于 `main()` L6271
  `_safe_export("ark", …)`）：枚举 cache 取每基金最新快照（regex `([A-Z]+)_([0-9]{8}).csv`，
  字符串序比较 ymd）、复用 parse_csv、每基金 top-10（按权重降序、capped 10）、family overlap
  （≥2 基金同持、top-20、按基金数/最大权重排序）、methodology 披露浏览器实证 URL 与
  no-prices/no-returns 边界；缓存缺失时 SKIP 打日志、tracked JSON 保住上次提交值
  （`_safe_export` 仅吞 FileNotFoundError）。
- `web/src/data/aionis/index.ts`：合并 barrel 是刻意设计（头部注释实测依据：Turbopack 共享
  chunk 去重 vs 具名导出每页复制 +50-280KB）；显式 per-panel TS 契约、禁 `as typeof json`；
  `ArkPosition/ArkFund/ArkOverlap/Ark` 类型在 L866-900。
- `web/src/data/aionis/ark.json`：19,658 B；status ok、as_of 2026-08-21、8/8 基金
  （n_positions=44 for ARKK 等）、family_overlap 已就位。
- `web/src/components/institutions/institutions-view.tsx`：`ArkSection` L42-145 —— 基金卡
  （每卡 top-5 行：ticker 链接 / 权重条 bg-primary/50 / `toFixed(2)%`）+ 家族共振表
  （chips + max_weight_pct）；STOCK_PAGE_TICKERS 守卫静态页链接。
- `web/src/components/overview/overview.tsx`：`ArkCard` L676-728 —— 首页「ARK 持仓共振」
  卡（family_overlap.slice(0,6)、基金计数比例条、中性色调）；L670-675 注释明文「snapshot
  NOT deltas: no ±pp exists and none is invented」「no 近30天 label because data does not
  support one」——正是本规格要条件解除的诚实降级。
- `web/src/i18n/dict.ts`：`overview.ark.*`（L341-344「ARK 持仓共振/基金同持/单基金最高权重/
  全部」）、`institutions.ark.*`（L924-928 zh、L2164-2168 en）、`colorconv.*`（L1162-1165
  红涨绿跌切换）。
- `web/src/app/globals.css`（L120-146）：`--up:#107d32 / --down:#d8001b` 国际惯例默认，
  `[data-colorconv="cn"]` 整体互换；注释规定数值方向场景只用 `.text-up/.text-down/.bg-up/
  .bg-down`，语义色不受切换影响。
- `web/src/data/aionis/form13f-stars.ts`：大 payload 走专用模块的在库先例（首页摘要 ~2KB，
  全量 650KB 书留在 form13f.ts 专用模块）——本规格引用它划定「何时才需要独立模块」的边界。
- `state/blockers.md`：H1 = GitHub Actions 计费失败（业主门），deploy-pages.yml +
  refresh-terminal-data.yml 已手动停用——快照停摆的直接原因，本规格的条件前置。
- `reports/design/2026-08-25-post-parity-roadmap.md`：§1 内容深度台账「ARK 异动 ±pp 30d vs
  today-snapshot only … time will close it」+ backlog「~30 daily snapshots accumulate」——
  本规格将其细化为「latest-two-available × N=5」的可执行判据。

---
*零网络请求、除本文件外零文件改动。本规格全文贯彻：冻结期内生产行为零变化；一切增量
仅在 H1 解冻且 distinct-days ≥ 5 后由一个小构建任务激活。*
