# state/current.md — read first each session

- **active (2026-08-16) ⑤ 用户旅程角色扮演（软件工程×人体工程学×设计学）→ cmdk 命令面板 + 模板死链清除 + 浅色修复（业主指令"扮演用户 + 学科反馈 + 复用轮子"；`1e7dd2f` 已部署）：**
  **① 旅程实测（首访视角，部署站）**：着陆 10 秒第一印象（视觉模型扮演首访者）——核心反馈 = "术语墙 + 无从下手"，缺"这是什么/从哪读起"入口；浅色模式（此前从未审计）= 二等公民；**Ctrl+K 无反应**但代码库有 command-palette.tsx；404 ✓、深链 #factors→tab 激活 ✓、图表 tooltip/双轴/事件标注 8/10 ✓、EN 切换生效（残留中文均为数据值如股票名，非 bug）。
  **② 软件工程发现——模板死链 ~1310 行**（续㉖ 清理漏网，因互相引用但无活引用者）：`command-palette.tsx`（未接线，含钱包/比特币/登录假菜单，读 seed 假数据）+ `nav-secondary.tsx`（假通知弹窗，app-sidebar 从未引用）+ `data/seed.ts`（973 行）+ `data/globe.json`（globe 删除后孤儿）。全删，grep 零活引用。
  **③ 修坏轮子（关键 bug）**：`ui/command.tsx` 的 `CommandDialog` 缺 `<Command>` 根包装 → `CommandInput` 崩 `undefined.subscribe`（cmdk context 缺失；零使用所以从未暴露，dev 服务器复现取栈后修）。按上游 shadcn 正典补 Command 根 + sr-only title 移入 DialogContent（Radix a11y 契约）。
  **④ 复用轮子（非造轮子）**：新 `CommandPalette` 全部建在**已有依赖** cmdk ^1.1.1（shadcn ui/command，GitHub/Vercel/Linear 同款）上：36 项 4 组——"从这里开始·60 秒导览"（①总览→②语境→③证据→④效度→⑤守卫 编号阅读序，直接回应首访反馈）+ 全部页面 + 深页 tab 视图（#factors 等 hash 直达）+ 设置（主题/语言/RESULTS.md 外链）。header 搜索按钮带 ⌘K 提示；Ctrl/⌘+K 监听为 cmdk 标准模式（IAB webview 宿主消费该快捷键，普通浏览器有效；按钮路径恒通）。i18n zh+en 14 键。
  **⑤ 设计修复——浅色升一等**：light `--muted-foreground` oklch 0.556→0.502（实测 4.38→5.51-5.95:1，AA 达标）、`--border` 0.922→0.895（白卡可分辨）。
  **⑥ 验证**：tsc 0 + build 23/23 + 33 契约测试 + ruff 净；dev 复现→修复→面板开/输"效度"回车→/track 导航/Esc 关全链路实测；本地静态包 + 部署站（deploy `31955414141` 绿）双验：按钮/4 组/36 项在位（EN 模式）、浅色 token lab42.23 实测上线；视觉模型复审面板（"达 GitHub/Linear 级"）与浅色（"接近一等公民"）通过。**教训**：部署站验证时 localStorage 语言偏好会改按钮 aria-label——按固定中文标签查会误报"按钮不存在"。
  **⑦ 边界**：纯 web/src 展示层（8 文件 +206/-1522）；0 ledger/frozen/config/prereg/OOS；未跑 research/forward。

- **active (2026-08-16) ④ 部署站视觉审计二轮（视觉模型+DOM 实测双通道）→ P0-P2 优化全落地（业主授权"推进到满意"）：**
  **① 审计方法**：IAB 打开部署站，桌面 1440 + 移动 375 双视口逐屏截图 → `analyze_image` 视觉模型盲审（Read→CDN 桥接；教训：CDN URL 必须原样传反斜杠路径，改正斜杠会破坏签名 → 1210）+ `getComputedStyle` 实测 lab/oklab 原始色值、Node 侧换算 WCAG 对比度（Tailwind v4 颜色非 rgb，正则匹配不到；canvas 归一化被副作用检查拒）。
  **② 硬发现（此前所有轮次未抓到）**：(a) **α 降透明 muted 文字低于 WCAG AA**——表格行首列 3.29:1（α0.6）、表头 4.02:1（α0.7）、track 脚注 4.02:1，满透明 muted 本身 6.9:1 达标，问题全在 opacity 变体；(b) **10-11px 中文小字**（th/脚注/徽章 89 处）低于 CJK 12px 可读下限；(c) **picks 页 9020px（桌面）/16461px（移动）≈10-20 屏**，全站唯一 sticky/fixed 元素是侧栏——无吸顶 tab、无返回顶部、无目录锚点；(d) 视觉模型对 6-tab/缺事件标注的两条报告为幻觉（实际 4 tab；市场图已有川普 ReferenceLine）——DOM 实测交叉核验再次证明必要。
  **③ 修复（全部展示层，0 ledger/frozen/config/prereg/OOS）**：**P0** α-muted 文字→实色（10 文件）+ 微字号规范化（`text-[10px]/[11px]`→`text-xs` 23 文件；9px 徽章→11px；保留 empty-state 装饰 svg 与 sparkline 去饱和设计）+ 审计表行 hover；**P1 人体工学** 新 `StickyTabs`（4 hub 页 tab 吸顶 `sticky top-0 z-30` + backdrop-blur）+ `BackToTop`（600px 后出现，44px 触控目标）——**关键陷阱**：`<main>` 的 `overflow-hidden` 祖先使 sticky 失效（hidden 容器成为不可滚动的最近滚动祖先），删掉后 20 路由 × 1440/375 全测无横向溢出（min-w-0 才是真根因，overflow-hidden 是冗余保险）；**P1 认知** hero 三卡→两卡（ProvenanceAnchor `embedded` 变体嵌入 VerdictAnchor 卡内）+ discipline 冻结/结果配对视觉（同 sha 相邻行：emerald 左竖条 + ↳ 箭头）+ track 页归因卡头部新增裁决速览条（复用 metrics 同源数字，零新增数据面）；**P2** `ProvenanceBadge` 增 `frozen` prop（锁=冻结面/时钟=日更面，picks/track 页头接线，i18n zh+en `provenance.frozen`）+ recharts 刻度 9/10px→11px + `fill=var(--muted-foreground)`（原默认 #666 在深色卡上仅 ~3:1）。
  **④ 验证**：tsc exit 0 + next build 23/23 路由预渲染 + 33 web 契约测试绿 + ruff 净（顺手修 5ea6649 预存的 3 个 lint 错：2 unused import + 1 长行）+ 本地静态服务（`web/Aionis` junction→out，已 gitignore）四页截图视觉模型复验全过 + 对比度复测达标（表头/行首列 3.3-4.0→6.9:1）+ sticky/top 交互实测（滚动 9071px 后 tabTop=8、点击返回顶部 scrollY→0）+ 移动端 375 四页无溢出、sticky 生效。
  **⑤ 边界**：纯 web/src 展示层 + 1 预存测试 lint 修复 + web/.gitignore（junction）；0 ledger/frozen/config/prereg/OOS 改动；未跑 research/forward。

- **active (2026-08-15) 续㉘（数据冻结根因双会话合流闭环 + 回归测试补位；业主授权"推进到满意"）：**
  **① theme_signals 46 天冻结根因链完整诊断（本会话独立完成，与 CI session 殊途同归）**：gh 日志取证最新 run `31892678348` —— 价格 fetch 已收敛（555 cached + 32 fetch = 587/587，wide 文件 15:50 写出，止于 08-14）→ materialize 崩于 `FileNotFoundError: universe_hanshof.parquet`（workflow 从未构建该缓存）→ CI session 以 `8d89aaf` 修（`_load_universe` 自填充）+ `828a007`（regime_macro build step）+ **`cfb9240`（陈旧复用修复）**。`cfb9240` 与本会话同刻在写未提交的同款修复（`reuse_prices = not args.display and ...`，两版逐字一致，我的未提交 edit 落地零 diff）——**双会话独立命中同一根因的交叉验证**。
  **② 数据已解冻（实测）**：themes price/macro/fundamentals 全 `as_of 2026-08-14`，theme_signals `2026-08-14`；auto-deploy 绿（CI session `67c1938` 验证）。
  **③ 回归测试补位（`7cf5167`）**：`cfb9240` 无测试 → 补 2 守卫：display 重建"ticker 完整但日期陈旧"的 wide 文件（per-ticker 缓存 5 天宽限内免网络）；冻结路径完整文件照旧复用（END 不动，冗余 refetch 徒增 H6 确定性风险）。5/5 相关测试绿 + ruff 净。
  **④ 并发协作机制记录**：双会话共享同一工作树，CI session 的 `pull --rebase --autostash` + push 把本会话 6 个 commit（类型加固/死代码/picks 延迟加载/Windows 测试修复 + state）一并推上 origin/main（`git log origin/main` 核验 6/6 在）。reflog 完整保留时序。
  **⑤ 边界**：本轮纯诊断 + 测试（display 链）；0 ledger/frozen/config/prereg/OOS 改动；未跑 research/forward。

- **active (2026-08-15) 续㉗（三轮扫查：picks 首屏 -22% + 集成/运行时验证 + 孤儿 key 量化）：**
  **① /picks conviction tab 延迟加载（`d3ffabb`）**：conviction 是该路由唯一 recharts 消费者（376KB）→ `next/dynamic` + Radix 非活动 tab 不挂载 = 图表库移出首屏。**picks 1890→1482KB（-22%）**，其他路由字节等量。**浏览器实测**（本地静态服务 + IAB）：点"选股确信度"tab → 异步 chunk 加载 → 分散度图完整渲染（时序轴/图例/KPI 齐）；默认 tab 数据不变。其他 hub 页默认 tab 本身有图表（regime=market/track=calibration/confirmation=smart-money），无同类收益，KISS 不改。
  **② 集成与运行时验证（全部健康）**：live-prices Worker 存活（curl 200，AAPL 305.93 实时价，display-only 边界符合）；构建 HTML 0 个 undefined/NaN/[object Object] 渲染痕迹；sidebar 6 直达项 + 外链 RESULTS.md 全有效（hub-tab 导航结构 = 设计）；发表线归档后 web/src 零死引用（prereg 的 frontier_positioning.md 链接目标仍在 docs/）；旧静态站测试 25/25 绿；pytest 全套零 skip。
  **③ 量化发现**：i18n 孤儿 key **58/476**（argument.chain.section.*/calibration hints/footer.note 等）——清理候选但需逐个排除动态组合引用（低优先）；13D 步骤 `continue-on-error: true` = smart_money 08-07 的陈旧窗口属预期（单源失败不阻塞数据提交，下轮成功即恢复）。
  **④ 边界**：纯 web 展示层性能优化 + 只读验证；0 ledger/frozen/config/prereg/OOS 改动；未跑 research/forward；未 push（本地领先 origin 7 commit，远端同期新进 1 commit 属 CI session/日更，推送+rebase 由其协调）。

- **active (2026-08-15) 续㉕（web 数据层类型加固全量落地 + 性能探索定论 + Windows 迁移测试修复；与 CI/CD session 并行不重叠）：**
  **① 类型加固（续①遗留 follow-up 闭环）**：`web/src/data/aionis/index.ts` 全部 26 面板从 `as typeof json` 字面量推断 → **显式契约类型**（Metrics/PicksMeta/SectorBreakdown/PicksBacktest/MarketContext/PowerFloor/SigmaSurvey/Taco/PickConviction/Form4/Cot/ModelHealth/Theme(s) 等），nullability 逐一对照 `export_terminal_data.py` 真实分支（taco.latest_vix/form4.shares·price/themes.signals·series·as_of/pick_conviction.latest·trailing_std_mean 等可空字段如实 `| null`；metrics.ledger_row 仅 live-ledger 分支 → optional；market_context.date_range 实为 `string[]`）。日更 JSON 形状塌缩（deploy 31869082383 reddit 先例）从此在 cast 处一次性红灯，而非散落使用点 `never` 报错。ThemeCard 内联结构类型 → 复用导出 `Theme`（单一事实来源；其运行时 null 过滤本已存在）。验证：tsc exit 0 + next build 22 路由全预渲染 + 33 web 契约测试绿 + ruff 净。
  **② 性能探索定论（实测取证，非臆断）**：(a) recharts 376KB chunk **已按路由分割**——7 个无图表页（dashboard/discipline/evidence/reddit/themes/sectors/model-health）实测不加载它（此前担忧排除）；(b) **barrel 命名导出拆分实验 → 回退**：Turbopack 静态导出对跨路由共享模块**不去重**（指纹证据：market_context 数据在同一页加载的两个 chunk 各一份拷贝），实测每页 +50-280KB（picks +277）比合并对象更差 → 保留单一合并对象（单一模块 = 单一共享 chunk 零重复），index.ts 注释记录此结论防止重蹈；(c) 本地旧 `out/` 是**过期基线**——纯 HEAD 重建与改动版逐页字节同量（evidence 1222/picks 1890），近期每页 +50-280KB 全部来自日更数据增长（macro_drivers 7 序列补齐、picks_backtest 增月）= 数据变新鲜，非回归。per-route 数据拆分需 webpack manualChunks（Turbopack 无此 API）= 换构建器涉 CI 领地，记录为后续可选项不擅动。
  **③ Windows 迁移测试修复（预存）**：`test_run_dir_sanitizes_unsafe_sig` 断言 `str(d).startswith("/tmp/...")` 在 WindowsPath 反斜杠下必挂（代码 sanitise 本身正确）→ 改 `as_posix()`。全套 pytest 在 Windows 首次全绿可期。
  **④ 数据面核查（state 旧记录订正）**：13D smart_money latest 已 **2026-08-07**（日更 lane 生效，旧"2024-12 滞后"过时）；A 股 picks 已是**板块级分类**（创业板/沪主板等，非 Unclassified）；行业级（申万/证监会）升级留后续——需新数据源（baostock 不在依赖）+ CI 协调。
  **边界**：纯 web 类型/展示层 + 1 测试断言修复；0 ledger/frozen/config/prereg/OOS 改动；未跑 research/forward；**未 push**（CI/CD session 并行验证中，推送由其协调）。

- **active (2026-08-15) 续㉖（同题扫查二轮：死代码/依赖裁剪 + lint 清零 + 数据新鲜度审计）：**
  **① 死代码清理（`6eab8a4`，-2118 行）**：模板遗留 4 组件（`globe-demo.tsx`+`ui/globe.tsx` three.js 全家链、`ui/chart.tsx`、`ui/calendar.tsx`）零引用删除 + package.json 裁 9 依赖（three/three-globe/@react-three/drei·fiber/@types/three/react-day-picker/date-fns/@dnd-kit/core·sortable），lockfile -798 行 → CI pnpm install 下载减少；运行时零变化（逐页 payload 实测等量：evidence 1222/picks 1890）。
  **② lint 清零（同 commit）**：`live-prices.ts` 冗余 `setStatus("disabled")` 删（useState 初始化已覆盖）；`i18n/provider.tsx` localStorage 水合的 setState-in-effect = SSR 安全正当模式（预渲染 HTML 必须确定性 "zh"），带理由定向 disable。`eslint src` 首次全绿。
  **③ 数据新鲜度审计（26 面板全扫）**：健康——多数 0-4 天（日更生效）。**例外**：(a) `theme_signals` + themes 的 price/fundamentals/risk/market_structure 卡 as_of **06-30（46 天）** = CI display_panel 未重建/价格收敛未完成 → 属 CI/CD session 正在端到端验证的链路（run 31878236600 含 DFF 补拉 + 契约闸门），通过后应自愈，不重叠处理；(b) smart_money 08-07（8 天，13D fetch 间歇）；(c) picks_meta/pick_conviction 08-03 = 读 gitignored 冻结 OOS parquet，设计如此（诚实陈旧）；(d) GDELT news as_of 06（增量回填滞后）；(e) reddit live 2 picks、1 条 bull_ratio null（RSS 无 score 结构限制，RedditPick 类型已防御）。
  **④ 全量 pytest（Windows 迁移后首次）**：exit 0、0 FAILED（含 as_posix 修复后 test_reporting 全绿）。
  **后续优化方案（已评估可行性，记录于 handoff (p)）**：tab 级 next/dynamic（Turbopack 兼容的每页 -376KB recharts 路径）/ BACKTEST_MONTHS 99→36（需业主显示取舍）/ webpack manualChunks（大工程涉 CI）/ A 股行业分类 baostock 源（M 任务）/ Russell COT 自愈等待 / reddit PRAW 凭证富化。研究面"提高准确率"唯一合法路径 = Track A 因子生成器（业主已授权）与 E3（AUD-06+GO），均预注册流程非擅自启动。
  **边界**：纯 web 展示层清理；0 ledger/frozen/config/prereg/OOS 改动；未跑 research/forward；未 push。

- **active (2026-08-15) 推送 + 部署验 + CI 闸门端到端验证中（业主授权 push，实时监控）：** 4 原子 commit（`c10993b` 发表线废除 / `3c5aaf8` RedditPick 类型 / `22ce0bb` CI DFF+闸门 / `c429435` state）+ 1 修复 commit（`ae83fe3`）。**rebase 冲突**：推送时远端已被日更 `fabe77a` 推进（其 macro_drivers 仍 5 序列残缺 = bug 复现的活证据）；`git pull --rebase` 冲突解决保留我方 7 序列版（ts 更新）。
  **部署两跳后绿**：首跳 8s 挂——`AGENTS.md` 在索引里仍是 **symlink 模式 120000** 携全文内容（Windows git add 沿用旧模式），Linux checkout "File name too long"（deploy `31878072392`）；`git rm --cached` + 重加显式 100644（同 blob）→ `ae83fe3` → deploy `31878129143` **success**（build 49s + deploy 8s，类型检查过 = RedditPick 修复在 CI 验证）。
  **部署站实测**（curl）：`/`、`/overview`、`/regime` "可发表/publishable" 0 命中；meta/hero = "intended outcome"；`/regime` 联邦基金利率卡 + 3.63（2026-07）+ real_rate −0.1 实显——两修复均已上线。
  **CI 新闸门端到端验证中**：手动触发 refresh run `31878236600`（含 DFF 补拉 + 契约测试闸门）——观察其 export 后 gate 是否绿 + macro_drivers 是否保持 7 序列。
  **教训（迁移后 Windows 首推）**：(1) symlink→文件替换必须核 `git ls-files -s` 模式位（Windows add 不改模式）；(2) 多文件 `git add` 带 bad pathspec 会整体失败而 commit 仍可能吃到旧暂存——add 后必须核对 status。

- **active (2026-08-16) ③ 业主观察"大量数据没有日更"全面审计 + smart_money 修复（run `31941203693` 验证绿）：** 25 面板逐一审计分类：**日更 12 个**（themes/theme_signals/market_context/macro_drivers/taco/form4/reddit/cot/smart_money/headline_provenance/ledger_audit/power_floor+evidence）；**源节奏限制**（cot 数据 CFTC 周二发布、价格类 as_of 受 5 天 grace ≈ 周推进、GDELT 月度聚合）；**冻结研究面 ~9 个**（picks/shorts/metrics/picks_meta/sector/ic_monthly/picks_backtest/pick_conviction/model_health/calibration/sigma/bps——全部派生自 gitignored 冻结 OOS 产物 ledger #49，重算 = rerun-to-significance 禁；metrics 链在 picks SKIP 后不导出 = 同因）。唯一真缺口 = **smart_money 卡 08-07**：导出硬要求本地-only 的 efts_13d_*.json（EFTS 2024-12 停索引，历史为有限封闭集，CI 重拉 25-CIK 子集会回退 3754 条全量）。**修**（`5ea6649`）：`_refresh_smart_money_recent_only`（news_sentiment 同款保留-刷新模式）——recent_filings 去重合并（date+target，top60）+ latest_date + 2025+ 年度计数从日更索引刷新，active_filers 与 2024 前聚合原样保留；主路径 DRY 到共享行构建器；3 hermetic 测试。**验证**：CI latest 08-07→**08-14**（recent top3 全为 08-14 新申报），自动部署绿。**"本地-only 工件"缺口至此四例**（universe/regime_macro/DFF/smart_money-EFTS），前三是补生产步骤，本例是历史封闭集保留——两类模式都已有结构解。
  **对业主观察的诚实回答**：冻结面约占终端可见数字的一半，它们**不会也不应**日更（反泄漏设计的核心——OOS 裁决封存，改数字 = 造假）；要让这些数字前进的唯一合法路径 = E3 forward-live（月度前瞻累计，业主 GO）。终端已有冻结披露（display-only·冻结结果 badge + ledger #49 溯源）；如业主想要更醒目的"冻结 vs 日更"面板级标识，属展示层增强，另开。

- **active (2026-08-16) ② 陈旧面板复用修复推送 + 端到端验证（业主授权 push，实时监控）：** 业主本地未提交的 `phase_b_fetch.py` 改动（我审查非我编写）已代为验证推送（`cfb9240`）：display 路径不再复用"ticker 完整但日期陈旧"的宽价格文件（该 bug 曾把 as_of 永久钉在文件构建日 = theme_signals 卡 06-30 的根因之一）；冻结路径不变（END 固定，完整即终态，H6 复用保留）。**审查要点**：33 phase_b+market 测试绿 + ruff 净；新鲜度规则 = 每 ticker 缓存距目标末日 ≤5 日历日即复用 → 日常网络尾部近零，但价格面板 **as_of 约 5-7 天推进一次**（grace=5d 的设计取舍——若业主要求更紧跟收盘，可收紧 grace 至 2-3d，代价是每周 2 次全量补拉波 ~20min）。
  **CI 验证（run `31938553596` 全绿 + 自动部署 `31939728127` 成功 + 部署站实测 08-14）**：`586 cached, 1 to fetch`（587 中仅 1 只过 grace）→ 宽表面 4 秒重建写出 → materialize → 闸门 → 提交 → 自动部署。陈旧复用类 bug 至此结构性关闭。

- **active (2026-08-16) 部署站数据自动更新全链路闭环（业主指令"确保自动更新"，已达成）：** 接 08-15 的自动部署修复后，本日把最后三个卡点逐一破掉并全程监控验证。
  **① 价格收敛完成**：手动加跑 3 轮（417→556→**587/587**，`phase_b_prices_display.parquet` 写出，价格至 08-14 收盘）——若等 cron（仅工作日）要到下周二。快照缓存持久化生效。
  **② universe 自填充修复（`8d89aaf`）**：价格收敛后 materialize 仍崩——`_load_universe()` 的存在性前置守卫废掉了 `load_hanshof_membership()` 的自抓取能力（CI 无任何步骤生产 `universe_hanshof.parquet`）。删守卫，加载器自填充，data-cache 持久化。
  **③ macro 主题双保险（`828a007`）**：universe 修复让 export_themes 的 CI 路径**首次被走到**，闸门立刻抓到真回归——macro 主题硬编码 "live" 但 `regime_macro.parquet` 在 CI 无生产步骤 → live+0 signals 必败（本地-only 工件缺口第二例）。修：workflow 加 `build_regime_macro.py` 步骤（自填充抓 BAA/AAA/DGS10/DGS1，VIX/DFF 复用 lane 既有缓存）+ export 侧 macro 无信号时诚实降级 needs_work（regime 故障不再阻塞全部数据提交）。
  **最终态（run `31927470839` 全绿 + 自动部署 `31928501528` 成功 + 部署站实测）**：themes **as_of 2026-06-30 → 2026-08-14**，7 主题全信号（price 5 / macro 1 / fundamentals 4 / news 5 / risk 4 / net_cost 3 / market_structure 1）；market_context 恢复日更；/themes 页实测显示 08-14。reddit/cot/macro_drivers 原本就日更。
  **自动更新保障结构（现行）**：cron 22:00 UTC 工作日 → fetch（COT/Form4/13D/Reddit/宏观+DFF+VIX/GDELT）→ 价格增量 → universe/regime 自填充 → materialize → 导出 25 面板 → **契约闸门**（残缺即拦）→ 数据提交 → **workflow_dispatch 自动部署**（GITHUB_TOKEN push 不触发 on:push 的结构性修复）→ Pages 上线。每个环节都有本日实证。
  **教训**：display lane 的"本地-only 工件"类缺口共三例（universe/regime_macro/曾缺的 DFF）——共同模式 = 导出依赖 data/cache 工件但 lane 无生产步骤、静默 SKIP 掩盖。闸门 + 自填充加载器是结构解。

- **active (2026-08-15) 发表线整体废除 + 主线重定（业主裁决，已执行）：** 业主明确：**项目不再有发表计划**（无 arXiv 上传、无 venue 选择、无投稿），清除所有有关发布的表述；主线 = **web 终端展示层 + GitHub Pages 实时数据更新**；并行继续：**Track A 因子生成器（新冻结面，业主已授权推进）**、**E3 forward-live（统计门已解除，剩 AUD-06 + 业主 GO）**、**glm-v4 key 有效性确认（bigmodel.cn 端点 401，待业主核实 key 或代理地址）**。
  **本轮已执行**：① 发表工件全归档（move-don't-delete → `archive/`）：`manuscript/`、`quarto-site/`、`docs/methods-and-results-draft(-en).md`、`docs/replication-availability.md`；`docs/frontier_positioning.md` **保留在 docs/**（被多个 frozen prereg/ADR 引用，move 会断引用；仅改掉其 "genuinely publishable research" 目的句）、`reports/design/2026-08-05-publishable-unit-positioning.md` + `2026-08-05-power-floor-literature-anchoring.md`；`tests/test_quarto_site_data.py` 删除（被测对象已归档）。② `export_quarto_data.py` 保留为共享载荷库（`export_terminal_data.py` import 之并重定向 OUT→`web/src/data/aionis/`；refresh CI 无 quarto 步，零纠缠）。③ web 终端用户可见"可发表/publishable"文案清除（dict.ts hero.subtitle + overview.verdict.null.note zh/en、attribution-card、layout meta、overview 注释、web/README）；sidebar"研究方法"链接 draft→`docs/RESULTS.md`。④ 静态站（site/ + build_static_site.py + test_static_site.py）同步清"可发表"文案 + draft 链接改 RESULTS.md。⑤ CLAUDE/AGENTS/README/00-vision/01-problem 的 "publishable outcome" 表述删除。⑥ .gitignore quarto 例外路径更新；AGENTS.md 由 WSL 断链 symlink 修复为 CLAUDE.md 真实副本（迁移损毁，内容一致）。
  **有意保留的 "published/publishable" 字样（非发表计划）**：`runs/ledger.jsonl`（append-only 审计日志禁改）；frozen prereg/ADR 历史记录（known-issues 既定：superseded wording 可留）；ingest docstring 数据源 "published"（PIT 语义）；dashboard（旧 streamlit 内部工具）"publishable_ci_half" schema 字段与 "PUBLISHABLE" 徽章（研究报告契约字段，改名涉 forward_results schema + 测试；如业主要求可后续 rename）。
  **边界**：纯 docs/state/web 文案 + 归档移动；0 ledger/frozen/OOS/config 改动；未跑 research/forward。

- **active (2026-08-15) 主线执行：Pages 部署失败修复 + macro_drivers 残缺根因闭环 + glm-v4 判定（同日，发表线清除之后）：**
  **① Pages 部署失败修复（deploy `31869082383` 51s 挂）**：根因 = `web/src/data/aionis/index.ts` 对 reddit 用纯 JSON 字面量类型推断（`as typeof reddit`），最新日更的 reddit.json 只剩 1 条 pick 且 `bull_ratio: null`（RSS 无 score）→ 推断类型塌缩为纯 `null` → `!== null` 收窄成 `never` → `pick.bull_ratio.toFixed` 编译错。**修**：显式 `RedditPick` 类型（`bull_ratio: number | null`，对齐 export 契约 `export_terminal_data.py:1278`）+ `{ ...reddit, picks: reddit.picks as RedditPick[] }`。本地 `tsc --noEmit` exit 0 + `next build` 全路由预渲染成功。**教训**：日更数据会改变 JSON 字面量推断类型——凡 `as typeof xxx` 的面板都有同类风险（后续可逐面板显式类型化）。
  **② macro_drivers 残缺（fedfunds/real_rate 静默丢失）根因闭环**：HEAD 上 `macro_drivers.json` 缺 `fedfunds`/`real_rate`（/regime 3 卡静默隐藏）——契约测试本地就红（`test_macro_drivers_panel_contract`）。根因链：日更 lane 内联补拉 CPIAUCSL/PAYEMS 但**从不拉 DFF** → `alfred_DFF.json` 只活在可逐出的 actions data-cache → 逐出后 `export_macro_drivers` 静默跳过两序列仍写 `status:"ok"` → 残缺面被日更 commit（c47535a 后即缺）。**修三件**：(a) workflow 内联补拉 DFF——复用 `macro_dff.fetch_dff_vintages`（年切片，绕 FRED 2000-vintage 上限；naive display fetch 会 400）；(b) workflow 新增 **Contract-test gate** 步骤（commit 前跑 `pytest tests/test_web_terminal_data.py`，残缺导出红灯拦下，不再静默落地）；(c) 本地从缓存重导出修复已提交数据（7 序列齐：fedfunds 127 点至 2026-07=3.63%，real_rate 113 点至 2026-06=−0.10%，与续⑳范围一致）。69 pytest 绿 + ruff 净 + YAML 解析过。
  **③ glm-v4 key 判定（待办可关闭）**：实测 `open.bigmodel.cn/api/paas/v4` + 现有 key（32.16 位）→ **HTTP 429 code 1305「该模型当前访问量过大」，非 401** = 鉴权通过、key 有效、endpoint 正确；glm-4.7-flash 当前限流是服务端容量（瞬时性），ProviderRouter cooldown 已覆盖。旧「401 待业主核实」状态过时（续㉔ 08-14 新 key 已修）。
  **④ 迁移损毁修复**：web/node_modules（WSL 符号链接失效）用 `CI=true npx pnpm@10 install --frozen-lockfile` 重建；`.venv` 由 uv 重建并 `uv sync --all-extras`。**边界**：display 层 + CI workflow + 类型修复；0 ledger/frozen/OOS/config 改动。

- **active (2026-08-14) 续㉔（数据日更根因链全破：today 400 → 修复生效批批 +20/20；剩 30min cap 分次续拉收敛中）：** 续㉓诊断日志（`97191ee`）在 run `31775804769` 打出决定性证据——**Tiingo/Alpaca 全返 HTTP 400 非 IP 封**（IP 假设被推翻）。追到真根因：`phase_b_fetch.py:85` `end = "today"` **字面量字符串**直接传给 `endDate` 参数 → Tiingo 400 "End date format was not correct. Must be in YYYY-MM-DD"（决定性复现实验）。冻结路径正常因 END 是真日期常量；本地测试曾"通过"因手写真日期未复现代码实参。**修**（`00a8882`）：`date.today().isoformat()`。本地端到端验证 `_from_tiingo` 返 200 + AAPL 9 bars 到 08-13。
  **CI 决定性验证**（run `31788130986`，HEAD 含修复）：`prices 2011-01-01..2026-08-14`（日志可见真日期）→ **批批 `+20/20`**（修前批批 +0）→ completed success + 数据 commit `d5199fe`。零星 429（Tiingo 限速 Alpaca 兜底）+ BF-B/BRK-B（share-class 变体，2% 容差内）均为次要。
  **剩余收敛**：30min 步骤 cap 在 ~100/587 时掐断（587 冷拉 × 2s 间距 ≈ 45-50min > cap）。**per-ticker cache 持久**（actions/cache 保存 prices/*.parquet）→ 每 run 续拉 ~100 → 2-4 个 run 全拉完 → materialize → display_panel 重建 → themes/market_context/theme_signals as_of 过 06-30。续拉 run `31794374610` 已触发（10:59）。
  **本轮判辨教训**：(1) 静默 `except: pass` 吞错让 3 轮诊断全猜错方向（secrets→IP→真相 400 字符串 bug）——诊断日志一次定位；(2) "本地测试通过"必须复现代码实参路径（我手写日期掩盖了 bug）；(3) export 的 SKIP 日志此刻反而精确诚实（runs/*.parquet 冻结研究面 CI 无，retain 旧值是设计）。
  **glm-4.7-flash**：✅ 全通（新 key + base_url 修复 `c853f66` + 项目 json_object 路径验证，reasoning 模型默认 max_tokens 足够）。


- **active (2026-08-14) 续㉓（数据日更真阻塞已修：Alpaca feed=iex；glm-v4 鉴权诊断）：** 业主加 Alpaca secrets + glm-v4 配置后请核查数据。
  **① 数据日更真阻塞已修**（`05a3b33`）：CI display-fetch 全失败（587 ticker `+0/20`）的根因**不是 secrets 缺**（业主已加 Alpaca），而是 **Alpaca 免费tier 查 SIP feed 返 403 "subscription does not permit querying recent SIP data"**，被 `except Exception: pass` 静默吞 → 每个 ticker 空。Tiingo 本地正常（AAPL 9 bars）但 CI IP 被限流返 0 → 两源都 0 → display_panel 永不重建。**修**：`_from_alpaca` + `_volume_from_alpaca` 加 `feed=iex`（免费tier IEX 数据）。实测 AAPL/MSFT 各 9 bars（修前 0），11 market 测试绿，ruff 净。display-only（非研究面）。
  **② glm-v4 base_url 修 + 鉴权诊断**（`c853f66`）：glm provider base_url 硬编码 → 改读 `settings.llm_base_url`（业主加的 LLM_BASE_URL secret 终于生效）。字段映射核验：`LLM_BASE_URL`→`llm_base_url`、`LLM_MODEL`→`llm_model`、`OPENAI_API_KEY`→`openai_api_key`、`PROVIDER`→`provider` 全部正确（pydantic-settings 自动大写映射）。业主 secret 命名无误。**鉴权诊断**：实连通测试 bearer + JWT 两种方式都 401（智谱 bigmodel.cn 端点）。业主 key 格式 `id.secret`（32.16 位）。需业主确认 key 是否智谱官方有效，或 base_url 是否应指向自建代理。
  **③ 端到端验证进行中**：触发 run `31768716742`（HEAD `05a3b33` 含 feed=iex），~30-90min 后查 themes/theme_signals/market_context 的 as_of 是否过 06-30。前次 run 22:31（`31750301639`）未含修复（HEAD `c47535a` 早于 `05a3b33`），故仍 06-30。
  **本轮**：数据日更的真根因（Alpaca SIP 403）找到并修复，非 secrets 问题。glm 配置缺口修+鉴权待业主。纯 display 层；0 frozen/ledger/config/OOS 改动。


- **active (2026-08-14) 续㉒（业主纠偏：实质尺寸重构 + 数据日更真因诊断，不再做表面改色）：** 业主明确不满——我之前改七主题卡片只改颜色（避重就轻），业主要的是**尺寸放大**；且部署站数据完全不更新。**诚实接受批评**。
  **① ThemeCard 实质尺寸重构**（`d0ee67b`）：非改色。title `text-sm`→`text-base`(16px)；signal value `text-xs`→`text-sm`(14px) font-medium（原 muted）；sparkline `h-6`→`h-12` + strokeWidth 1.5→2（趋势一眼可读）；padding `p-4`→`p-5`；header gap-1.5→gap-2；badge px-1.5/py-0→px-2/py-0.5。tsc+build+33 pytest+ruff 全绿，部署 `d0ee67b` success，`text-base:16px` 实测上线。
  **② market_context 数据源修**（同 commit）：equal-weight 市场指数读冻结 `track_b_panel`（停 06-30）→ 改读 `display_panel`（B1 日更），缺失时回退冻结面（与 export_themes 同模式，非 slop fallback）。现 VIX(2026-07) 与指数 lockstep；CI display-fetch 成功后指数自动新鲜。
  **③ 数据日更真因诊断（关键发现，交业主）**：git log 证实 cron 在跑且 commit（cot/reddit/taco/themes/macro_drivers/power_floor/headline_provenance/ledger_audit 都更新）。但**两个真阻塞**：
    - **picks/metrics/ic_monthly/evidence/calibration/conviction 结构上冻结**：读 `runs/*.parquet`（ledger #49 冻结 OOS 产物），日更 = rerun-to-significance（反泄漏禁）。这是设计，非 bug。
    - **CI display-fetch 失败**：日志 `0 cached, 587 to fetch` + 每批 `+0/20`（Tiingo 返 0）→ 30min 超时 → display_panel 不重建 → themes/market_context 卡冻结。**根因**：`gh secret list` 只有 `FRED_API_KEY`+`TIINGO_API_KEY`，**无 `ALPACA_KEY_ID`/`ALPACA_SECRET_KEY`** → Tiingo CI 返 0 时无 Alpaca fallback。**业主一次性修**：加 Alpaca secrets（免费 tier）或查 Tiingo key 为何 CI 返 0。
  **本轮闭环**：实质尺寸重构（业主直接诉求）+ market_context 数据源修 + 数据日更真因诊断（明确业主动作）。agent stale-panel-audit 在跑（交叉核验其他可修面板）。纯 display 层；0 frozen/ledger/config/OOS 改动。


- **active (2026-08-13) 续⑳（contract-audit agent 闭环：修 2 真 display 缺陷 + 契约测试加固，全部署验）：** 续⑲ contract-audit agent 回报 9 面板分析，含 **3 结构发现**——主线核验后确认 2 个是**真 display 缺陷**非仅测试 gap（[[aionis-agent-dispatch-verification]]：agent 给发现，主线核真值）：
  ① **macro_drivers 静默退化（MEDIUM-HIGH，live /regime）**：3 个消费者（macro-drivers-card + macro-stagflation-read 读 `fedfunds`；macro-mandate-tension 读 `real_rate`）读的 key **不在 committed JSON 里**。export 逻辑确实构建两者（fedfunds=alfred_DFF 月均；real_rate=DFF−CPI YoY），但一次 stale partial export（cache 缺失）静默丢了 → 3 卡静默隐藏/空。根因 = `_safe_export` partial-skip 模式，非逻辑 bug。**修**：从现有 cache 重新导出（fedfunds 127 点 0.34→3.63%；real_rate 113 点 −1.86→−0.10%，范围 sane）+ 契约测试 pin 住 7 个消费者必需 key 防再发。
  ② **ic_monthly 重复月份（dead export 但真 data bug）**：5 个月各 2 行（US-only + CN-only 共享 %Y-%m key）→ 按 month 绘图的消费者会得双点/断裂 join。**修**：export 改 group-by-month + coalesce（71 行→66 unique 升序无重）+ 契约测试加 no-duplicate-months 守卫。
  ③ reddit_meta→reddit.json 命名 trap：主线续⑲已正确排除（agent 确认）。
  **验证**：ruff 净 + 33 web terminal pytest 绿（含新 dup-guard + required-keys guard）+ next build compiled + deploy `d321125` success + puppeteer 部署站实测——/regime 7 图渲染（破卡现显真值），fedfunds~3.7% + real_rate 负值实显，无 awaiting 态。
  **本轮全闭环**：agent 审计 → 主线核验（不轻信，自读文件确认）→ 2 真缺陷修 + 守卫加。纯 display-data 层 + 测试；0 frozen/ledger/config/prereg/OOS 改动；未跑 research/forward。
  **判辨教训**：续⑲我以为"9 面板无测试"是纯覆盖 gap，agent 深挖发现其中 2 个是**真 broken display**——测试覆盖审计意外暴露了生产 defect。display-layer 三层（科学诚实 + 视觉 + 数据完整性）现全闭环。


- **active (2026-08-13) 续⑲（并行：contract-audit agent 派发 + 主线自写 8 面板契约测试，全部署绿）：** 业主"启用更多 agents 同步 + 不空转"。**判辨**：扫描发现 display-layer 9 个 export 面板**无契约测试**（evidence/power_floor/calibration_reliability/ic_monthly/bps_sweep/sigma_survey/theme_signals/macro_drivers/reddit_meta）→ 静默 shape 变更会让对应页崩溃或误导（如 evidence 丢 CONFIRMATORY climax 卡 = hero provenance 悬空引用；sigma_survey 丢 confirmatory/combined 行 = attribution-card σ 回退到手常数）。
  **并行两路**（不空转）：① 派 sonnet Explore agent（codebase-local，[1210]-safe）做 9 面板 shape/消费者脆弱性分析；② 主线**不等 agent**，自读真实 JSON shape + 消费者组件，自写 8 契约测试。
  **交付**（`6c5c800`）：8 契约测试，每条 assert 真实 JSON shape + 消费者依赖的不变式——evidence（14 行/合法 grade/CONFIRMATORY climax 存在/unique n）、power_floor（3 looks/observed σ > pure-noise 界=机制）、calibration_reliability（双 region/per-month series/reliability bins）、ic_monthly（≥24 月升序/无 NaN/combined 非全 null）、bps_sweep（bps 升序/turnover ~常/net≤gross Sharpe）、sigma_survey（confirmatory/combined 行存在=attribution 源）、theme_signals（合法方向/group 一致/display-only 披露）、macro_drivers（≥3 series/≥12 月/升序）。reddit_meta 故意排除（forward-collector 合法空）。
  **验证**：33 web terminal pytest 绿（25 前 + 8 新）+ ruff 净 + 55 broader（web+export+market）绿。纯测试增量；0 production/frozen/ledger/OOS 改动。
  **agent 角色**：contract-audit agent 做独立优先级/脆弱性交叉核验（防我漏 consumer 依赖）；主线不阻塞等待，自完成全部 8 测试（"不空转"纪律）。
  **本轮闭环**：display-layer 契约测试覆盖从 ~58% → ~96%（24 面板中 23 有测试，唯 reddit_meta 合法待激活）。科学诚实度四轴 + 视觉 P0-P3 + 契约测试加固全闭环。


- **active (2026-08-13) 续⑱（P2 NULL 视觉框架 + P3 移动端审计表，全部署验）：** 续⑰后业主再授权。续⑰的 P2/P3 优化。
  **P2（心理学框架效应，`85f7acf`）**：NULL verdict badge 用 amber（警告色）→ 与下方 null.note"非失败"语义冲突。扫视读色快于读字，amber 暗示"失败"直觉压过诚实框定。**判辨**：不"全改中性"——区分语义：NULL 本身（成功交付）→ slate（已落定色）；amber 保留给真警示（J-T 门/power-floor/ECE）。两处 NULL 表达（VerdictAnchor badge + verdict chain segment）改 slate；语义拆分非整体重涂。
  **P3（人体工学，`85f7acf`）**：移动端 7-col 审计表（632px）在 375px 卡里横滑才能到 verdict/metric 列（访客最想要的"结论"反被藏在滚动外）。**判辨**：不做卡片化大重构（/discipline 非高频页，KISS），改用最小影响 responsive 修复——phase + config-sig 两列移动端 `hidden md:table-cell` 隐藏，保留 5 关键列（#/日期/事件/估计量/裁决）首屏可见；隐藏的 sig 折进 event badge 的 title tooltip（零 provenance 丢失）。桌面 1440 仍全 7 列。
  **验证**：tsc exit 0 + next build compiled + deploy `85f7acf` success + puppeteer 部署站实测——P2 NULL badge slate 非 amber（`bg-slate-500/15`）；P3 桌面 7 列无滚动，移动 375 5 列首屏可见无页面级滚动，22 badge 带 sig tooltip。
  **本轮全闭环**：P0（MiniPicks 截断）+ P1（TrustRibbon）+ P2（NULL 框架）+ P3（移动审计表）全交付。视觉审计的 4 项优化全部上线。纯展示层；0 frozen/ledger/config/prereg/ADR/OOS 改动；未跑 research/forward。
  **视觉优化已尽基础+一轮**：基础显示确认健康（续⑰），4 跨学科优化（金融/法学信任 + 心理框架 + 人体工学移动端）上线。剩余打磨级（P4 键盘导航/hover interaction）边际收益递减，KISS 不做除非业主指定。


- **active (2026-08-13) 续⑰（视觉全审计 + MiniPicks 截断修 + TrustRibbon 信任锚，全部署验）：** 业主"用视觉能力检查所有界面，结合金融/法学/心理学/人体工学/美学 + 竞品经验；先确保基础显示再优化"。
  **视觉全审计**（puppeteer DOM 扫 6 页 × 桌面1440 + 移动375，查 NaN/undefined/溢出/截断/对比度）：基础显示**健康**——0 数据泄漏、0 水平溢出（含 7×28 审计表移动端走表内滚）、深色默认对比度 ~9.3:1（WCAG AA ✓）。**1 真缺陷**：/overview MiniPicks 股票名 `w-14`(56px) 截断不可读（`CENTERPOINT ENERGY INC`→`CENTERPOIN…`）。
  **基础修**（`ef199e0`）：MiniPicks 名 span 从 fixed `w-14` → `flex-1 min-w-0` + `title` tooltip。名 slot 56→130-144px，4/4 全显或优雅降级（CENTERPOINT 仍截但带 tooltip）。tsc+build 双绿，puppeteer 实测移动375+桌面均无溢出。
  **P1 优化**（TrustRibbon，`9edd879`）：跨学科判辨——法学+心理学：hero 有"非投资建议"免责（picks 页 `NullDisclaimer` 也已存在），但**缺肯定性信任基础**（"为何可信"非仅"别交易"）。反泄漏纪律（PIT/embargo/H6/frozen-config）是 Aionis vs 竞品（小隐寺/OpenBB）的**核心差异化**，却只在 /discipline + 页底 GuardBand 可见。新 `TrustRibbon` 接 Hero 正下方、VerdictAnchor 之上——把信任基础与裁决**同屏共置**（范式 α：主张与认知基础同见，非滚动隔开）。4 badge（PIT/embargo/H6/config）各带 title 全文 tooltip，整体链 /discipline。emerald 色调（肯定性 vs 免责的 amber）。8 zh+en i18n。页底 GuardBand 保留（横护整链）；ribbon 是一眼信任锚。
  **判辨纠偏**：原 P1 计划含"picks 免责 footer"，但审计发现 `NullDisclaimer` **已存在**（每 prob_up 上方，含 ledger #49 引用）→ 不重复添加（避免认知负荷 + 冗余）。区分"已满足"vs"缺失"。
  **验证**：tsc exit 0 + next build compiled + puppeteer 实测部署站（9edd879）— TrustRibbon 反泄漏纪律 + 4 badge + /discipline 链实显，MiniPicks 修复上线（0 legacy fixed 名），0 泄漏/溢出。
  **本轮全闭环**：基础显示确认健康 + 1 缺陷修 + 1 跨学科优化（法学/心理学信任建构）。纯展示层；0 frozen/ledger/config/prereg/ADR/OOS 改动（concurrent CI `b5b3a9b` 仅 daily data refresh，ledger sha pinned 不变实测验）；未跑 research/forward。
  **下一步**：P2（NULL verdict 视觉框架从 amber→中性完成色）+ P3（移动端审计表卡片化）。display-layer 信任 + 诚实度已尽基础 + 第一轮优化。


- **active (2026-08-13) 续⑯（themes 新鲜度诚实化 = integrity audit 最后一个 finding 闭环，display-only，全部署验）：** 续⑮交付 HIGH+MEDIUM 后重审：agent 还标了 2 个 STALE-RISK（themes 日期不一致），我在续⑭以"runtime-blocked"搁置。**判辨修正**：那是对**runtime freshness**（Tiingo 返 0）的判断，但 agent 的具体 finding 是**labeling bug 非 freshness bug**——themes.json top-level `as_of_date`=06-30（冻结 panel）vs macro 主题 per-theme `as_of`=08-04（GDELT/ALFRED 独立源）= **真实数据自洽但标签误导**（header 单日期 vs 卡片不同日期）。我能修且应修。
  **交付**（`7603430`）：`export_themes` 新增 `freshness: {earliest, latest, mixed}` 摘要（从所有 live 主题的真实 as_of 计算）。mixed 时 themes-view header 显示范围 `截至 06-30 → 08-04 · 各主题独立来源，新鲜度不一`，非单一误导日期；每卡保留各自诚实 as_of。1 新 regression 测试 pin freshness 形状 + earliest≤latest 不变式。zh+en i18n。
  **验证**：ruff 净 + tsc exit 0 + next build compiled + 25 web terminal pytest 绿 + deploy 31640960301 success + puppeteer 实测部署站 header `截至 2026-06-30 → 2026-08-04 · 各主题独立来源，新鲜度不一` 实显，macro 卡 08-04 不再矛盾。
  **本轮全闭环**：integrity audit 3 findings 全部解决（续⑮ HIGH metrics lineage + MEDIUM σ + 续⑯ STALE-RISK themes freshness）。纯展示层；0 frozen/config/prereg/ADR/OOS/ledger 改动；未跑 research/forward。
  **判辨教训**：续⑭ 把 themes STALE-RISK 和 runtime freshness 混为一谈 → 过早搁置了一个可修的 labeling bug。区分"数据不新鲜"（runtime-gated）vs"标签误导"（code-fixable）是关键。

- **active (2026-08-13) 续⑮（integrity audit agent 闭环：hero 数字的主显示源结构化可追溯 + σ 从 sigma_survey 派生；修 climax 行选择 bug；DRY 三导出共享 ledger 读）：** 业主"启用更多 agents 同步"。派 sonnet Explore agent（codebase-local，[1210]-safe）做全终端科学完整性审计 → 3 findings。**核心判辨**：续⑬交付了 ProvenanceAnchor（hero 数字**旁边**的出生证明），但 hero 数字**自身的显示源** metrics.json 仍 hardcode IC/p/CI literals 且无 ledger_row/config_sig → hero 的两处最显眼显示（VerdictAnchor + ResearchGlance）读的是**un-traced float**，provenance 系统离 desync 只差一次静默 metrics.json 编辑。agent 标 HIGH，正确。
  ① **HIGH 修**：`export_metrics` 从 hardcode → **live ledger projection**。新 `_read_ledger_rows()` + `_find_climax_row()` 共享 helper（metrics + provenance + audit 三导出 DRY 共享同一 ledger 读 = 单一事实来源，一次 ledger 编辑原子传播所有面）。metrics.json 现带 `ledger_row: 49` + `config_sig_short: e14b9d44`，与 headline_provenance.json 完全一致（实测验：row/sig/IC 三者全等）。fresh CI 无 ledger 时诚实降级回 committed literals。
  **climax 选择 bug 修**（agent 调研中我自抓）：首版 `_find_climax_row` 取第一个 `confirmatory:first` → 误取 Phase B 行 #28（非 Track C climax #49）。ledger 有 5 个 confirmatory:first（Phase B/C/D/E1 + Track C），但**只有 #49 同时有 nested `combined_ic.mean` dict + `jt_gate`**（gated 估计量签名，不可伪造）。修为要求两者 = 正确锁 #49。agent 原 spec 误导（"first confirmatory:first" 歧义），我核 ledger 真值订正。
  ② **MEDIUM 修**：`attribution-card.tsx:42` hardcode `σ≈0.10` → 从 `sigma_survey.json` 的 track_c_confirmatory/combined 行派生（实值 σ=0.106，agent 指出 N=71 纯噪声界应为 0.1195 非 0.10；现用真值 survey 非手常数）。survey 缺失诚实降级回 0.10。
  ③ **research-glance 浮点常量修**（续⑭已交 a18b80a）：COVERAGE_TALLY gaps:5 stale → testedFamilies/exploratoryFamilies 显式族级计数。
  **验证**：ruff 净 + tsc exit 0 + 25 web terminal pytest 绿（含新 `test_metrics_carries_ledger_lineage` pin 住 metrics↔provenance 同源）+ ledger sha256 三导出后不变（READ-ONLY 实测验）。三导出 DRY 共享 `_read_ledger_rows`：metrics/provenance/audit 现**原子一致**（同 #49 / 同 e14b9d44 / 同 IC -0.0088）。
  **本轮全闭环**：agent 审计 → 主线核验（不轻信 agent spec，自抓 climax 选择 bug）→ HIGH+MEDIUM 全修。纯展示层 + READ-ONLY ledger；0 frozen/config/prereg/ADR/OOS 改动；未跑 research/forward；未外发。
  **站巨人**：QVeris evidence-first 的终极形态 = 主张的**显示源本身**可追溯（非装饰性 sibling anchor），单一事实来源（ledger scan）原子传播所有面。

- **active (2026-08-12) 续⑭（并行推进：部署验 + display fetch 容差修 + 测试 harness bug 修，themes 新信号；真新鲜度 runtime-blocked 诚实披露）：** 业主"启用更多 agents 同步 + 不空转等待"。**并行 3 路**：
  ① **部署验**（deploy 31607274687 success）：puppeteer 实测 https://rethymus.github.io/Aionis/ — /overview 出生证明卡（冻结 #48 04:19 → 结果 #49 10:27 同 sha e14b9d44 + H6 PASS + J-T NOT_EQUIVALENT + 链 /discipline）实显；/evidence 卡 #15 `ledger #49 · frozen config → /discipline` 实显。续⑬部署上线确认。
  ② **display fetch 容差修**（`5b2a131`）：根因 = `phase_b_fetch --display` 共享 frozen 路径的严格 complete-prices 门 → 2/588 缺失（BF-B/BRK-B share-class 变体，Tiingo/Alpaca 覆盖差异）abort 整个新鲜度刷新。修 = 新 `_require_display_prices`（<2% 缺失容差写 panel，>2% 仍拒防 provider 宕活产误导面）；frozen 路径 `_require_complete_prices` **不动**（反泄漏契约）。
  ③ **预存测试 harness bug 修**（同 commit）：`phase_b_fetch.main()` 的 argparse 读 sys.argv → pytest CLI 参数（文件路径/-q/-k）致 3 个 `test_phase_b_main_*` 在 clean main 上 SystemExit(2) 前就死（pre-existing，非我引入）。修 = `_configure_phase_b` pin `sys.argv=["phase_b_fetch"]`。2 新 display 容差测试（小缺失通过 / 大缺失拒）。11/11 test_market 绿 + ruff 净。
  **themes.json 重导出**：补 close-only qlib 因子（rsi_21d=0.5334 / timetohigh_63d=0.3994）+ as_of 字段（PIT 透明）—— 这些已在 export 代码（`fc91fe0`）但 committed themes.json 未刷新。
  **诚实披露（runtime-blocked 非 code-blocked）**：真新鲜度（as_of 过 2026-06-30）= runtime-gated。Tiingo 本会话 batch refetch 返 0（限流/凭证），故 prices 不能过 frozen END。我一度试 date-gate 强制全量 refetch → 反而 unlink 了可用 panel + Tiingo 仍 0 = 比 stale 更糟 → **立即 revert date-gate**，从 586 cache 重建 panel 回到可用 stale 态。教训：date-gate 与 `_final_panel_is_complete` 交互会 unlink；且 runtime fail 时勿加倍下注（[[aionis-owner-process-correction]]）。
  **本轮闭环**：续⑬部署验 + 真 display 容差修 + 预存 harness bug 修 + themes 新信号。纯 display/data-refresh lane；0 frozen/config/prereg/ADR/OOS 改动；未跑 research/forward；未外发（push 触发 Pages 部署）。
  **下一步业主门**：真新鲜度需 Tiingo-healthy run（runtime，非我可控）；或 Track A 因子生成器（新冻结面 owner-GO）。display-layer 容差 + 科学诚实度三轴已尽其用。

- **active (2026-08-12) 续⑬（headline 出生证明 = hero 数字 → 冻结 config 的可追溯链，修 2 真 bug，display-only，全本地验证）：** 续⑫交付"理论锚 + 审计时间线"后业主再授权"至不可再优化"。**判辨**：续⑫让时间线可见，但 **从未把 hero 数字 `IC −0.0088` 连到它自己的账本行**——缺最后一块：每个 headline 主张在出现处携带其冻结来源。**审计中发现 2 真 bug + 1 缺失连接**：
  ① **`metrics.json:11` latest_month 是 Python bound-method repr**（`<bound method Timestamp.date of Timestamp(...)>`）—— `export_picks:194` 返回 `str(...date)`，`.date` 是 bound method 非属性。修为 `.strftime("%Y-%m-%d")` → `'2026-08-03'`。hero 载荷泄漏修。
  ② **`export_ledger_audit` climax 行 #49 verdict/metric 空**——函数只处理 flat scalar `combined_ic`，但 #49 存 IC 为 nested `combined_ic.mean` dict → metric 留空 = headline 主张在自己的审计表里**哑**。修为处理 nested dict + `jt_gate.look1_verdict` + `H6_deterministic` 三 schema shape → #49 现 `combined_IC=-0.0088 (p=0.484) | NOT_EQUIVALENT | h6=True`。
  ③ **新 `export_headline_provenance()`**（READ-ONLY，ledger sha256 导出前后不变实测验）：扫描首个 `confirmatory:first` 行（不硬编码行号）→ 配对同 sha256 的 `config_committed` 冻结行 → 产出 hero 的"出生证明"：result 行 #49 + freeze 行 #48（同 sha `e14b9d44`）+ freeze ts 04:19 → result ts 10:27（同日，冻结先于结果 6h）+ `contract.freeze_before_result: true` + H6 PASS + J-T NOT_EQUIVALENT。缺失 confirmatory 时诚实降级 `awaiting_confirmatory`。
  **前端连接**：① 新 `ProvenanceAnchor`（overview/provenance-anchor.tsx）接 hero VerdictAnchor 正下方——freeze/result 行号 + 同 sha + ts 间隔 + H6 + J-T 一目了然，链 /discipline。② evidence 卡 #15（CONFIRMATORY climax）加 `ledger #49 · frozen config → /discipline` 链——hero 数字、evidence 卡、审计时间线**三处同源**。③ AuditTimeline verdict 列对 h6=True 行显示 `H6 PASS`。11 新 zh+en i18n key。
  **站巨人**：QVeris evidence-first + ACM 2026 SuperProvenanceWidgets 的"每个主张在出现处携带证据"（scented widget at point of claim），非"单独时间线页"。这是科学诚实度的**第三轴**（续⑫理论锚+时间线；续⑬出现处可追溯）。
  **全本地验证**：ruff 净 + tsc exit 0 + next build 22/22 routes exit 0 + 81 pytest 绿（web terminal 24 含 4 新 regression + export + ledger invariants + calibration）+ ledger sha256 三次确认不变（pin 写入测试防漂移）+ puppeteer DOM 实测（hero 下 freeze-before-result badge + e14b9d44 + NOT_EQUIVALENT + #48/#49 实显；evidence #15 ledger 链实显；discipline #49 行 `combined_IC=-0.0088 (p=0.484) | NOT_EQUIVALENT` 实显）。
  **本轮全闭环**：2 真 bug 修 + 1 科学诚实度连接建。纯展示层 + READ-ONLY ledger 导出；0 frozen/config/prereg/ADR/OOS 改动；未跑 research/forward；未外发；未触 E3。
  **下一步业主门**：(a) push → 部署（外发 GitHub Pages）+ (b) /themes export 陈旧修（数据刷新 lane）+ (c) Track A 因子生成器（新冻结面）。display-layer 出现处可追溯已尽其用。

- **active (2026-08-12) 续⑫（科学诚实度升级 = 理论锚定 + 冻结审计时间线，display-only，全部署验）：** 续⑪ plateau 后业主 4× 追问"高质量科学选股研究系统"。**判辨修正**：我续⑪ plateau 判定在**IA 结构轴**成立，但在**科学深度轴**不成立——业主四次问的不是"再重排 IA"，是"让终端的科学性配得上其反泄漏纪律"。授权后交付两项 display-only 科学诚实度升级（`f2f3798`，tsc+build 22/22 双绿 + ruff 净 + 78 export/ledger/terminal pytest 绿，部署 run 31605125486 success 验）。
  **① 因子族理论锚定**（CoverageMap，/themes）：5 经典因子族（价值/动量/风险/流动/情绪）每族新增「理论锚定」行——价值→Fama-French 1993 + Novy-Marx 2013 + Sloan 1996；动量→Jegadeesh-Titman 1993 + De Bondt-Thaler 1985 + George-Hwang 2004；风险→Ang et al 2006/2009 + Bali-Cakici-Whitelaw 2011 + Frazzini-Pedersen 2014；流动→Amihud 2002 + Pastor-Stambaugh 2003 + Sadka 2006；情绪→Baker-Wurgler 2006 + Tetlock 2007 + Garcia 2013。CoverageMap 从"标签"升为"学术锚点"。部署实测 5 锚标题 + 5 经典引用全显，零 legacy。
  **② 冻结审计时间线**（AuditTimeline，/discipline）：把 Aionis 身份 = `config_committed BEFORE result` 做成**可视化时间表**。新 `export_ledger_audit()`（READ-ONLY，ledger sha256 导出前后不变，实测验）从 54 行 ledger 抽 28 承载裁决行（config_committed/confirmatory:first/oos_result/exploratory/phase_b_freeze）→ `ledger_audit.json`（row/date/event/phase/sha/metric/verdict 最小字段）。每 freeze 行显示 sha256 短哈希先于其 result 行——**反泄漏契约的活体证据**。部署实测 #53 config_committed(b7621e6b, 08-08) → #54 OOS 结果(b7621e6b, 08-09) 同 sha 前后呈现 + verdict "NULL" 实显，28 行表无溢出。
  **站巨人**：金融学（Fama-French/HLZ/Amihud 经典）× 市场研究理论（Cochrane factor zoo）× 科研软件可审计性（ERC examination + DataONE provenance + QVeris evidence-first）× Aionis 反泄漏身份——跨学科合成是前沿未探索原创领域（续⑪调研确认）。
  **AI 合规三轨不变**：B 归因✅ / C 覆盖(+理论锚)✅ display-only 已部署；A 因子生成器⏳ owner-GO；禁轨 LLM-in-OOS。
  **本轮全闭环**：科学深度轴升级到位。两项皆纯展示层，零 ledger/frozen/config/prereg/ADR/OOS 改动（ledger 导出 READ-ONLY sha256 实测验不变），未跑 research/forward，未外发，未触 E3。
  **下一步业主门**：(a) /themes export 陈旧修（数据刷新 lane，非 web/src）+ (b) Track A 因子生成器（新冻结面）。display-layer 科学诚实度已尽其用。

- **active (2026-08-12) 续⑪（全页视觉审计 + 前沿调研二轮 + display-layer plateau 判定）：** 业主第四次要求"视觉整体排查 + 前沿调研 + 金融×市场理论联动 + AI 深度贯彻 → 高质量科学选股研究系统"。按 `aionis-owner-process-correction`：不做第七轮"重设计"仪式，做诚实审计 + 定向前沿扫 + plateau 判定。
  **全页视觉审计（puppeteer live DOM，7 页）**：dashboard/regime/picks+`#factors`/confirmation/track/discipline/themes **全部无 H 溢出（1280=1280）+ 0 legacy 残留（定调/定标/问责/①-④/L0-L4/funnel/漏斗 全 0 命中）+ α 结构一致（SegmentHeader 脊柱 + provenance + AI 归因 4 点 + CoverageMap + 守卫高亮全部署验）**。续⑧ confirmation min-w-0 修复 + 续⑩ ThemeCard role-badge 重设计**部署正确无回归**。
  **唯一真实内容问题（非 IA bug）**：`/themes` `截至 2026-06-30` 比 regime 8-4 / confirmation 8-7 陈旧 6 周 = **display-panel export 层陈旧**（B1 `themes.json` 未从 `display_panel.parquet` 刷新），属数据刷新 lane 非 `web/src`。本轮 flag 不修（跨 lane）。
  **前沿调研二轮（主会话，[1210]-safe）**：① ACM 2026 SuperProvenanceWidgets（scented widgets + 聚合盒扫 gap + Gantt 时序 + ex-situ/in-situ 分离）→ Aionis SegmentHeader+CoverageMap gap 已体现可迁移洞见；② Fan 2026 防过拟合机制深挖（T_IS 分离/有界表达式/τ_econ 经济门/MHT/anti-crowding）→ **Aionis 反泄漏纪律已全覆盖且更强**（purged+embargo vs 纯 no-look-ahead）；③ HLZ 2016 + Bailey-LdP DSR 2014 → Aionis null+power-floor 是标准诚实做法非缺陷（arch DSR/SPA 已在 lock）；④ ERC (Nüst o2r) → Aionis 终端是 partial ERC（config_committed+H6+PIT 可浏览器审），"浏览器内 rerun"=hosted compute 超静态站 scope，已知边界；⑤ **跨学科合成（Toulmin×Messick×Mislevy ECD×null-honest 资产定价×科研软件 UI）= 前沿未探索原创领域** → 正面验证范式 α 科学性，**守线勿转舵**。
  **AI 合规三轨不变**：B 归因✅ / C 覆盖✅ display-only 已部署；A 因子生成器⏳ owner-GO；禁轨 LLM-in-OOS。
  **plateau 判定（display-layer IA）**：续⑤→续⑩ 已全解"七主题 UI 重设计"诉求；本轮 7 页 live 审计确认**无剩余结构性不适配**。再迭代 = 仪式非改进。真前进杠杆 = (a) 数据刷新陈旧修（运维非 IA）+ (b) Track A owner-GO（研究，新冻结面）。两者皆需业主决策，非更多展示层工作。
  **交付**：`reports/design/2026-08-12-terminal-visual-audit-frontier-synthesis.md`（审计表+前沿映射+plateau 裁决）。**边界**：0 `web/src` 代码改动（plateau 无需改）；0 ledger/frozen/config/prereg/ADR/data/OOS；未跑 research/forward；未外发；未触 E3。

- **active (2026-08-12) 续⑩（ThemeCard α 重设计 + 全视觉排查闭环）：** 业主再指"原七主题所有内容 UI 需重设计，当前位置不适配；视觉能力排查所有内容"。**根因（业主正确）**：续⑦我重设计了 ThemesFunnel→ArgumentChainDiagram，但 **ThemeCard 本体**（经 ThemeSlice 渲染于 4 hub tab：regime/picks/confirmation/track）仍带「七主题」时代 legacy——实时/partial/forward_only/needs_work 状态 badge + "源自解散后的旧「七主题」"框定，与 α 论证链不适配。
  **重设计交付**（`bd77331`，tsc+build 双绿，部署实测）：ThemeCard 从 legacy 状态卡 → **论证段卡**：role badge（语境段/证据段/独立佐证段/裁决段，镜像 argument-chain-diagram 词汇）替代 live/partial；as_of 成为唯一新鲜度信号；sparkline 去饱和（证据形状非正向信号）；删死代码 STATUS_KEY/STATUS_STYLE/StatusKey；`theme.slice.note` 重框定（"每张卡声明其在论证链中的角色"，去"源自解散后的旧"）。
  **全视觉排查（puppeteer DOM + bundle 实测）**：`/picks#factors` 4 卡 role badge=证据段 实显，legacy "实时/Live" 消失，"源自解散后的旧" 清零；`/themes` 全页（ArgumentChainDiagram 5 段+4 ∴warrant / CoverageMap 5 族 / signals grid α 组标题"证据·行情/价格"）/ 零圆圈数字 / 零定调定标佐证问责角色标签 / 零漏斗·L0-L4·七主题框架串。**代码硬扫**：5 命中全误报（注释 1 + "独立佐证"子串 4，均正确）。**视觉模型 zai 持续 401 不可用**，改 puppeteer DOM 精确文本 + bundle grep（更可靠）。
  **本轮全闭环**：七主题衍生 UI（widget + card + slice + signals grid）全部 α 化，无 legacy 残面。**边界**：纯 web/src 展示层；0 ledger/frozen/config/OOS 改动。

- **active (2026-08-12) 续⑨（AI 贯彻两轨 + 覆盖地图，全部署验）：** 在续⑧综合方案之上交付 **Track B + Track C** 两个 display-only AI 面（`feea401`+`2ff29aa`，tsc+build 双绿，部署实测渲染正确）。并行 sonnet Explore agent（codebase-local，规避 [1210]）产出**因子覆盖清单**（tested/exploratory/gaps × 5 族 + frozen-surface 边界），驱动 Track C。
  ① **AI 归因卡**（`attribution-card.tsx`，Track B）：读冻结 #49（IC/CI/p/power-floor），纯函数派生 4 条经济叙事（IC 量级、CI 跨零、power-floor 不可达、反泄漏纪律）。接 /track validity 段顶。部署实测 4 点全显（IC -0.0088 / CI[-0.034,0.016] / 半宽 0.034>>SESOI 0.01）。**display-only · 冻结结果** badge + 边界脚注（LLM 进 OOS=泄漏，禁）。确定性无外部调用。
  ② **因子覆盖地图**（`coverage-map.tsx`，Track C）：5 经典族（价值/动量/风险/流动/情绪）× tested/exploratory/gaps，每个 tested 锚冻结 ledger 行（#28/#30/#34/#41），gaps 引经典未测异常（MAX/BAB/52wk-high/coskewness/analyst/short-interest）。接 /themes。部署实测 5 族+gaps 全显。**金融学×市场研究理论**桥：每单元系研究软件工件于资产定价异常。
  **AI 三轨合规分层**（synthesis §3）：B 归因✅ / C 覆盖地图✅ / A 因子假设生成器（需新预注册+freeze，owner-GO 门，未启）。**禁轨**：LLM 特征直进 OOS（2024-26 lookahead-bias 文献群证为已知泄漏）。
  **本轮全交付链**（9 commit，全部署验）：视觉全排查→D1 4 bug 修（含 SidebarInset min-w-0 根因）→前沿调研（Fan 2026 agentic + LLM-leakage 文献 + 资产定价锚）→综合方案→D2 归因→覆盖地图。**边界**：纯 web/src 展示层 + docs + memory；0 ledger/frozen/config/OOS；未跑 research/forward；未外发（D2 fixture 版无 LLM 调用，live 版待业主门）。

- **active (2026-08-12) 续⑧（视觉全排查 + 前沿调研 + 科学系统综合方案 + D1 视觉 bug 全修）：** 业主要求"视觉整体排查 + 深入调研前沿 + 金融×市场理论联动 + AI 深度贯彻 + 高质量科学选股研究系统"。
  **视觉全排查**（puppeteer DOM，6 页 + 源码扫）：4 真问题 + 0 残留。**D1 全修**（`c0aa335`+`ec11158`，tsc+build 双绿，部署实测验）：
  ① **`/confirmation` 水平溢出**（1421px>1280px）→ 根因 = `SidebarInset` 无 `min-w-0`（flex 子不收缩到内容以下）→ 加 `min-w-0` 到 primitive（shadcn 正典修复）+ 布局 `<main>` overflow-hidden。部署实测 1421→1280px，hScroll=false。
  ② **`/discipline` 无高亮守卫段** → SegmentHeader `segment==="guard"` 时高亮 guard chip（border-primary/bg-primary）。部署实测 highlighted=true。
  ③ ArgumentChainDiagram desc `truncate` → `line-clamp-2`（移动端不截断长 warrant）。
  ④ Overview verdict 卡 title=`evidence.role`（别扭）→ 新 `overview.chain.verdict.label`（裁决/Verdict）。
  **前沿调研**（主会话，规避 [1210]）→ 记忆 `aionis-agentic-factor-investing-research` + 综合方案 `reports/design/2026-08-12-scientific-research-system-synthesis.md`：
  - Fan 2026 arXiv agentic 闭环因子发现（constrained autonomy + IS/OOS 严格分离 + economic rationale ReAct + multi-obj gate + symbolic regression）**可复用方法学**，但 Sharpe 3.11 属 overfitting 警示（与 Aionis #49 NULL 尖锐对比）→ 复用框架不追 alpha。
  - 2024-26 LLM lookahead-bias 文献群（ChronoBERT/Look-Ahead-Bench/DatedGPT）→ **LLM 特征进冻结 OOS = 已知泄漏通道，禁**。AI 贯彻须在 OOS 外。
  - 资产定价锚（HLZ t>3.0、LdP DSR、GKX LightGBM=冻结 learner、KX survey）= Aionis null+power-floor 是标准诚实做法非缺陷。
  **AI 三轨合规分层**：A 因子假设生成器(exploratory,需新预注册) / B 归因助手(display-only,读已冻结 null) / C 文献异常地图(display-only)。**禁轨**：LLM 特征直进 OOS panel。
  **下一步业主门**：D2（AI 归因卡，display-only 但需 GLM API 外发）—— 业主授权前我用 fixture 版预建组件（不外发）。本轮先交付视觉全修 + 综合方案。**边界**：纯 web/src 展示层 + docs + memory；0 ledger/frozen/config/OOS 改动；未跑 research/forward；未外发。

- **active (2026-08-12) 续⑦（七主题 widget 视觉重设计 + 全视图视觉排查）：** 业主指"原七主题所有内容 UI 需重设计，当前位置已不适配；用视觉能力排查所有内容查类似问题"。**视觉排查（puppeteer 截图 + DOM 文本提取；zai/4_5v 视觉模型服务 401/auth 不可用，改用 DOM 精确文本——更可靠）+ 源码全审计**。
  **根因（业主正确）**：`themes-funnel.tsx` 组件本身仍是 **funnel 范式**（LAYERS 顺流而下 L0→L4 + flowKey 下行箭头 + inPanel/hub 管道机制），与它新处的 α 论证链位置不适配。dict **值** 已 α 化（B1），但 **组件概念 + key 命名空间** 仍 funnel。
  **重设计交付（`2045a32`，tsc+build 双绿，deploy `31541668986` success）**：
  - 组件 `themes-funnel.tsx` → **`argument-chain-diagram.tsx`**（`ThemesFunnel` → `ArgumentChainDiagram`）；`LAYERS` → `SEGMENTS`（context/evidence/estimand/validity/verdict）。
  - **ECD warrants 替代 data-flow**：管道式 `flowKey`（"证据喂入→..."）→ 逻辑担保 `warrantKey`（**∴** 语句，"∴ 因子作为可观测物被测度，测度结果即估计量"等 4 条 zh+en）——每段为何**蕴含**下一段而非"数据往下流"。箭头 ArrowDown→ArrowRight（逻辑蕴含而非管道）。
  - dict key 命名空间 `themes.funnel.*` → `argument.chain.*`（l0..l4 → 语义段名）zh+en 全迁移；8 flow 值改 warrant 语句。
  **全视图视觉排查结论（3 页 DOM + 源码全扫）**：`/themes` 5 段 + 4 ∴ warrant 实显；`/regime` 面包屑高亮 语境 + provenance 2026-08-04 实显；`/track` 内 view role = "效度 · 模型概率可信吗？"（α 词）。**源码全扫 funnel/七主题/闭环/analyst-workflow 残留 = 0 真命中**（唯一 "佐证/定调" 命中是 `独立佐证` 子串 + `三力定调` 动词，均正确）。**系统统一**：七主题 widget 已从 funnel 升为论证链，与 SegmentHeader/Overview 同构。
  **边界**：纯 web/src/ 展示层；0 ledger/frozen/config/data/OOS 改动。**修**：根 `.next/` 加 .gitignore（stray 构建产物，防再 flag）。
  **plateau**：骨架+旗舰+每页脊柱+widget 论证链化+provenance 角标 = 无不适配残面。

- **active (2026-08-12) 续⑥（终端 IA 优化至 plateau：Overview 论证面 + SegmentHeader 脊柱 + provenance 角标，5 commit 全部署验）:** 业主授权"创建最有价值内容直至不可再优化"。在范式 α 骨架（续⑤）之上做 display-layer 深优化，4 commit（tsc+build 双绿，已 push `5a40562`，deploy `31539937611` success 验）：
  ① **Overview 重建为单一论证面**（`9688069`）：5 段拼贴（Hero/KPI/Ticker/Picks/Chain）→ **VerdictAnchor 锚定**（可证伪主张领头，IC/CI/p/n 为其背书，NULL 框定为预期结果非失败）+ ArgumentChain（语境→证据→效度→裁决 4 段，每段带代表 stat + 内嵌 mini picks/佐证）+ 佐证 ribbon（聪明钱/拥挤度，非第 5 列）+ GuardBand。12 新 overview.* i18n key（zh+en），hero 改论证链文案。
  ② **SegmentHeader 复用组件**（`97c0409`）：5 hub 页（regime/picks/confirmation/track/discipline）重复 header → 1 组件，渲染**脊柱面包屑**（语境 › 证据 › 效度 › 裁决，当前段高亮 + 尾部守卫 chip）。每页都宣告自己在论证链的位置。
  ③ **/themes 也加 SegmentHeader**（`00dce34`，verdict 段，它是全链概览页）。
  ④ **provenance 脊柱**（`f42c261`）：ProvenanceBadge 复用组件（读 snapshot_ts/as_of_date/latest_date → "截至 YYYY-MM-DD" 角标；无值则不渲染=诚实缺席非装饰破折号）接入 SegmentHeader 的 asOf prop。regime 传 cot.latest_date、confirmation 传 smart_money.latest_date（部署 JSON 经 export 注 snapshot_ts 生产环境实显）；picks/track 无干净顶层日期故诚实省略。站巨人 QVeris evidence-first。
  **审计**：metrics 字段全真值（combined_ic -0.0088/CI/p/n_months/verdict NULL/n_picks_total 25）；垃圾 latest_month 未触 UI；10 个 inner-view .role 全用 α 词（语境/证据/独立佐证/效度/守卫/裁决）与脊柱一致非矛盾；page-level SegmentHeader + in-tab 本地 title 两层架构自洽。**部署验**：deploy success sha 5a40562，bundle 实测 效度论证链×5/argument chain×7/可证伪主张×2/Guard spans×1/provenance×2。
  **plateau 判定**：骨架(nav)+旗舰(Overview)+每页(SegmentHeader)+provenance 角标+inner-view 一致 = 无 collage 残面。剩余优化（provenance 扩 15 view / 退役 /themes）依赖 export 数据注入或业主门，非 display 层。
  **边界**：纯 web/src/ 展示层；0 ledger/frozen/config/prereg/ADR/data/OOS 改动；未触 E3。

- **active (2026-08-12) 续⑤（终端 IA 第三次重组 = 范式 α ECD 效度论证链，5 批全绿）:** 业主第三次要求打散"七主题"重组，**明确不再要一二三四编号**、要"科学排布+前沿经验+科技智慧+深度复用 github"。诊断前两次失败根因 = 我一直按**分析师工作流**组织终端，但 Aionis 是研究效度工具（CLAUDE.md: "NOT a cognitive system or trading bot"）。调研巨人（主会话，规避子代理 [1210]）→ 提 3 范式（α ECD 效度论证链 / β 研究生命周期 / γ 溯源可观测性）→ 业主**定帧 α**。
  **设计文档**：`reports/design/2026-08-12-terminal-ia-paradigm-shift.md`（诊断+3 范式+巨人调研）+ `2026-08-12-terminal-ia-paradigm-alpha-migration.md`（逐文件迁移 spec）。3 执行前确认业主全选推荐：证据段合并 1 组 / 守卫横条+独立组 / 12 独立路由移出主 nav。
  **5 批全交付（tsc + next build 双绿，0 ledger/frozen/config/data/OOS 接触）**：
  - **B1 dict.ts**：59 处编号/角色词（nav.group/hub.intro/loop/各.role/themes.funnel L0-L4，zh+en 对称）弃用定调/定标/佐证/问责/定向/边界 + ①-⑥/L0-L4，改用**语境/证据/效度/裁决/守卫**。0 残留（"独立佐证"含"佐证"是正确新词）。正文 science 不变。
  - **B2 app-sidebar.tsx + 4 hub header**：nav 从 5 组 → α 链 4 组（Context / Evidence[含 corroboration 子项 picks+confirmation] / Validity / Guard）+ 总览 + 参考。4 hub page header 自动随 key 更新（无需改文件）。URL 全不变。
  - **B3 overview.tsx**：FunnelCards 从四枢纽①-④ → **论证链横向可视化**（语境→证据→效度→裁决 4 卡 + ArrowRightIcon 连接，去编号）+ 底部**守卫横条**（PIT/embargo/H6/provenance 徽章横护全链，链接 /discipline）。复用 GavelIcon/GlobeIcon/FlaskConicalIcon/GaugeCircleIcon/ShieldCheckIcon。
  - **B4 themes-funnel.tsx + theme-slice.tsx**：去 L0-L4 可视编号（`L{layer.n}` span 删，n 保留为内部 key id）；注释更新为 α 段归位。themes-view ThemeCard 信号逻辑不动（真实 signal 名无编号）。
  - **B5**：12 独立路由（calibration/.../evidence）确认 `in sidebar: 0`（B2 结构性结果），URL 保留可达，靠 hub tab 到达。
  **验证**：tsc exit 0（每批）+ `next build` exit 0（B1-B3 后 + 全完成两次，19 路由全 prerender）+ Python 扫 tsx/ts 圆圈数字 0 命中。**记忆** `aionis-terminal-ia-paradigm-ecd` 写入（范式 α 锁定 + 根因诊断，防第四次重蹈）。
  **下一步业主门**：审部署效果（push 后 GitHub Pages 部署）→ 若 OK 可考虑退役旧 /themes 独立页 + 清理 dict.ts 里 nav.group.insights/monitor 等已无引用的孤儿 key（低优先，可回退安全）。**边界**：纯 web/src/ 展示层；0 Python/ledger/frozen panel/config/prereg/ADR/data/OOS 改动；未触 E3；未跑 research/forward。

- **active (2026-08-11):** **选股策略 IA 大重构 + 纪律化自适应路线落地 + CI 可靠性持久修复（多 commit，已 push）** — 业主定帧"七主题解散进 hub 体系"+"绿 1-3"+"并行 agents 不空转"。交付链：
  ① **GDELT news_sentiment ingest**（`ee1b14f`，复用 gdeltdoc MIT Filters.query_string + 自有 5s 间距 policy，2017-04→今，display-only；增量 fetch；22 ingest 测试 + 5 接线测试）。
  ② **5 层选股漏斗 + 七主题解散**（`463136a` 漏斗组件 + `1b3fe8a` 解散：factors→定标 / news→佐证 / cost→问责，/themes 变纯漏斗总览；theme-slice 复用机制）。
  ③ **qlib/RD-Agent 复用审计**（`docs/qlib-reuse-audit.md`，`06da220`）+ **纪律化自适应 A+B 合题**（`docs/adaptive-design-research.md`，`2211e89`，读全文 NeurIPS 2025 R&D-Agent-Quant，证据化 3 纪律缺口 + 4 层嫁接 + 预注册声明骨架）。
  ④ **close-only qlib factor-pack**（`fc91fe0`，rank/rsi/cntp/range/timetohigh，显示层计算不动冻结 panel；9 hermetic 测试）。
  ⑤ **OHLCV panel 扩展计划**（`b39ed58`，opus agent 产出 + 我核验 market.py:57 确实丢 OHLCV）。
  ⑥ **Form 4 增量修复**（`6ae06ea`，opus agent + 我抓 2 真实 bug：accession-only 去重会丢 86% 数据 + schema 迁移；修 + 重写测试 import 真函数 + 多行-accession 回归）。
  ⑦ **CI timeout 45→75→150**（`06da220`+`1d75a7a`，Form 4 冷拉取 >75min；诊断恶性循环：cancel 不存 cache→每轮冷拉）。
  **并行进行中**：opus agent `form4 per-issuer checkpointing`（中途超时也保留已完成 issuer）+ `market.py OHLCV ingest carry-through`（步骤 1 安全前半，加性、H6 不变）；CI run 150min 跑旧 form4 冷拉取。**待核验**（不轻信 agent 自述，按 `aionis-agent-dispatch-verification`）。**下一步业主门**：步骤 4 自适应预注册（A+B go-signal）—— OHLCV 进冻结 panel（步骤 1 后半）+ RD-Agent 评估器接缝（步骤 3）均 phase-gated，不可擅自启。**3 新记忆**：GDELT 源 / 许可放松 / （既有 agent-dispatch-verification 再证）。
- **active (2026-08-11) 续（gloss + CI 根因）:** ① **track-hub 术语 gloss**（`a954acb`，powerfloor/modelhealth/calibration，zh+en parity 28/28，部署 HTML curl 验 tooltip 实渲染）。② **confirmation-hub 术语 gloss**（`1a62ed2`，smart-money 13D / insiders Form 4 / reddit bull_ratio；agent 遗 yearlyHeading 孤儿 → 我 2 行修；tsc+build 绿 + 部署 HTML 验 `title="13D 申报：持股超 5%..."`/`"内部人：公司高管..."`/`"多头比：提及中正面占比..."` 三 tooltip 实渲染）。③ **[skip ci] 根因修复**（`3e54d90`）：daily refresh 的 data-commit 带 `[skip ci]` → deploy-pages（trigger=push:main）不触发 → **数据进 repo 不上部署站 = "数据仍没有体现" 结构性根因**；去 `[skip ci]` 后未来 refresh 自动部署（当前 run checkout 66a3d3c 仍带旧 [skip ci] → 需手动 trigger deploy）。④ form4 per-issuer checkpointing（`05ab7b1`）+ OHLCV additive fetch（`8b0154d`）已验 landed。**CI run 31457990487**（首跑带 Form 4 step-cap 20min）将放行 GDELT+reddit+export → data commit。**下一步**：run 完成后手动 trigger deploy-pages → curl 验 deployed themes.json 含 news_sentiment + reddit.json 新鲜 → 业主报诉闭环。**dispatch-verification 本轮再证**：confirmation-hub agent 自报"全绿"但留 yearlyHeading 孤儿（我核验抓修）= 勿信 agent 自述纪律持续有效。
- **active (2026-08-12) 续④（B1 display panel + snapshot_ts baseline）:** 业主选 B（CI 重建 panel）解决"七主题无时点/市场数据不新"。实施 **B1 = display panel 分离**（非 B2 滚动研究 OOS）。两 sonnet agent 并行核证：materializer 纯特征工程（无 aionis.eval/ledger/frozen/network）+ fetch chain 无结构性 blocker（全 MIT/Public/免费 tier，≥2s 礼貌，PIT 合规）。
  **B1 实施（`c12378d`）**：`phase_b_fetch.py --display`（prices to TODAY → `phase_b_prices_display.parquet`，冻结零碰）+ `track_b_materialize_panel.py --display`（→ `display_panel.parquet`，冻结 `track_b_panel` 零碰）+ `export_themes` 优先 display_panel + workflow "Rebuild display panel" 步（CPI/PAYEMS inline + phase_b --display + materialize --display，30min cap）。本地验证：display_panel 产出 120MB + 冻结 panel **字节不变**（Aug 2 mtime）+ export 7 themes 带 as_of + 31 测试绿。
  **snapshot_ts baseline（`2afcf27`）**：`_stamp(payload)` helper 注入 16 面板顶层 `snapshot_ts`（export 时点），系统性修复业主"无法得知有效性，不止七主题"。list payload（bps_sweep/ic_monthly/evidence）跳过。前端 ThemeCard 已显示 as_of；其他面板 snapshot_ts 显示增量后补。
  **验证中**：CI run `31516057812`（B1 冷拉 display prices ~588 tickers，15-30min，可能首跑超 cap 跨 run 收敛），监控 `b325ewwuc` 查 committed themes.json 的 price theme `as_of`（B1 新鲜信号：应到 2026-08 非 6-30）。
  **反泄漏边界**：display 产物永不进 aionis.eval/ledger/OOS；冻结研究面 + config_committed 零改动。memory `aionis-display-panel-separation` 记 B1 决策。
- **active (2026-08-11) 续③（四枢纽 IA 重组 + news 3 根因链）:** 业主强反馈"news数据never show out"+ 之前的"七主题拼凑杂烩需打散重组成紧凑自洽科学创新的四枢纽系统"。两线交付：
  **A. 四枢纽研究闭环 IA 重组**（`9d260c9` + `ed27f4f`，已部署 3 deploy 全 success）：sidebar 7→5 条目（overview + ①②③④），dissolve ②themes/⑥discipline 两组，编号 ①③④⑤→连续 ①②③④。内容并入：/regime +macro tab（ThemeSlice，从 themes 并入）；/track +discipline +evidence tabs（从 ⑥ 并入）。/dashboard FunnelCards 6→4 卡，重设计为**四枢纽闭环导航**（①②③④ 编号 + "研究闭环·四问" header + "④ 问责校准回灌 ① 定调"反馈脚注 + 每卡一代表性 stat）。旧 themes/discipline 路由保留 URL 可访问（可回退，nav.group 标签改"已并入"）。tsc+build 绿。**调研巨人**：OpenBB（IA 标杆但已转数据平台）、quantumterminal（Next.js 同栈）、FinceptTerminal（密集美学）——结论：不抄 OpenBB 平铺，Aionis 强迫走研究闭环（什么市→买什么→别人怎么看→能信吗），问责枢纽把反泄漏纪律+power floor null+证据墙作一等公民 = 差异化。
  **B. news_sentiment 3 串联 silent-failure 根因全修**（`50388b2`→`4c9e7c2`→`34eacb2`）：① theme `ECON_MKT` 非法（n=0）→ `ECON_STOCKMARKET`（CI 实测 n=92-93/块，2019-04→2025-04）。② `export_themes()` 面板缺失早退连带跳过 `_build_news_theme` → 抽 `_refresh_news_sentiment_only`，面板缺失时只从 GDELT cache 刷 news，其余主题原样保留。③ **冷拉 38 块（15s+429 退避）>20min step-cap → GDELT 步超时被杀 → `collect_news_sentiment` 没跑完 → cache 从未写入**（旧设计全跑完才写）→ `continue-on-error` 让 run 假"success"。修 = **增量持久化**：`fetch_tone_series` 加 `on_chunk` 回调（每块聚合后调），`collect_news_sentiment` 回调每块 `merge_series` + `_write_cache_snapshot`。超时也保住已完成块；后续 run 增量续；首轮即部分显示 live；冷回填跨多 daily run 完成。31 GDELT+export 测试绿（含 2 新：超时幸存 + 多块 merge），ruff 净。**meta 教训（memory `aionis-gdelt-news-sentiment-source`）**：3 根因串联，每个都让 run 报 success 但数据不达终端；单个根因修复不够——**唯一权威信号是"部署的 themes.json news_sentiment.status"**，非 chunk_ok/fetch_done/run success。业主 "news never show out" 强反馈正是在我只修 #1 就宣称胜利后。
  **验证中**：CI run `31494488040`（带 #3 修复，旧 run 31493162823 已取消）跑 GDELT 步——监控 `buktiyoyx` 跟 `gdelt_chunk_checkpoint` 计数（增量持久化生效证据）+ committed themes.json news_sentiment 状态。reddit 投诉早已解决（早前会话新鲜快照）。**phase-2 待业主确认四枢纽方向后**：旧 14 独立路由重定向/清理 + 彻底退役 /themes 页 + 消除 theme UI 维度（不可逆，先确认）。
- **active (2026-08-11) 续②（CI 可靠性 + 3 审计 + 自适应复盘）:** ⑤ **CI run 31457990487 失败**：全部 fetch 步骤绿（COT/Form4/13D/reddit/macro/VIX/GDELT/export 全 ✓），但 data-commit 被 **non-fast-forward** 拒（运行期间 4 次 code/doc push 推进 origin/main，git-auto-commit 不 rebase）→ **全部 fetch 丢失**。根因修复 `ff3c0ec`：commit 前 `git pull --rebase --autostash origin main`（data JSON 不与 code/doc 路径重叠 → 无冲突）。⑥ **13D step-cap `cd239f3`**（15min，cold pull ~14min，同 Form 4 hazard class）。⑦ **重跑 `31464314965`**（带 rebase 修 + 4 次并发 push 实测中）。⑧ **3 审计交付**：ingest 反泄漏审计（`764581b`，7/7 CLEAN，我抽查 `fetch_ohlcv_panel` 分离 + display-only 边界 grep 验证）+ 终端 UX/结构审计（`0781eb0`，curl 13 路由，结构自洽，"拼凑杂烩"已被本 session IA 工作缓解）+ 自适应 A+B 深度调研（`a473673` → `b8d204e` 订正）。⑨ **自适应复盘**：深度调研撰写时误判"Step 4 pending"；核对 `runs/ledger.jsonl` 发现 **Track Adaptive**（自适应 vs 冻结两尾预注册）已 config_committed 3 次（#51 monthly-A 作废 → #52 amend1 weekly① → b7621e6b amend2）+ 跑完首次 OOS（b7621e6b，2026-08-09 03:01 UTC）= **NULL**（IC_diff −0.0037，p=0.26，CI 跨零；周扩窗重训略**差于**真·冻结基线）= **第三条独立 null**（Track C #49 + Track Adaptive + 文献共识）。Romano-Wolf × adaptive 缺口（无 landmark paper）**不削弱 null verdict**（多重检验校正保护阳性、不保护阴性）→ 缺口仅前瞻价值（未来若出现阳性 adaptive 变体才需 DSR+Romano-Wolf 双层）。⑩ **[1210] 真因更新**（memory `aionis-model-tier-dispatch-policy`）：子代理 **web-tool 路径**触发 GLM [1210]，不限模型层级——本轮 ingest-audit（opus，纯本地源码）成功，但 adaptive-research + ux-audit（opus+sonnet 各 2，需 WebSearch/WebFetch）4 个全失败 → 主会话补做（父会话 WebFetch/WebSearch 正常）。**新判据**：web-using 子代理任务 → 主会话执行，勿派子代理。**下一步**：CI run 完 GDELT → export → rebase（实测 4 并发 push）→ commit → auto-deploy → curl 验 deployed themes.json 含 news_sentiment + reddit.json 新鲜 → 业主报诉闭环。
- **active (2026-08-09):** **P3 漏斗 IA 重构已上线（commit `40f3b9d`）** — 业主授权 P3。已交付：删 13 个模板遗留组件目录（~8900 行 cruft，0 importer）+ nav 从扁平 4 组重排成 **6 步决策漏斗**（①定调→②定向→③定标→④佐证→⑤问责→⑥边界，role 由 group label 承载，zh+en）+ 扩 `refresh-terminal-data.yml` 日频 cron 加 forward collectors（cot/form4/reddit fetch，continue-on-error）= 解决 smart_money 卡 2024-12（旧 cron 只 re-export 不 fetch）。`next build` 绿，已 push。**reddit picks 表早已渲染（旧 stub 标记过期）**。**下一轮**：七主题可操作化（方向×强度×利好股）+ ⑤ risk（pyfolio/empyrical）。**再后**：④ news（forward-only LLM 管线）+ 周报（需内容 spec）。cron 频率定论：日频系统负担得起（公开仓库 Actions 无限 + 幂等缓存 + ≥2s 礼貌），叠加周报是最佳形态。详见 `state/handoff.md` §2026-08-09(n)。
- **active (2026-08-09):** **部署站仪表盘诊断 + IA 重设计提案（已 push 上线）** — 业主批部署站"数据缺/taco 空/没标川普就职/七主题生硬/像拼凑杂烩"。诊断：数据层大多 2016+ 健康（部署未刷新所致）；修 2 真凶（basePath dev 404 `e3274e3` + taco dataKey 空 `e3274e3`）+ 补川普两任就职(emerald `inauguration` 类型)。硬约束：reddit forward-only（无 2016）/ model 输出 OOS 2021+（延 2016=禁）→ 须诚实标注。**P3 漏斗 IA 提案** `reports/design/2026-08-09-terminal-ia-redesign.md`（PROPOSED）：扁平 nav → 6 步决策漏斗（定调→定向→定标→佐证→问责→边界）+ 七主题可操作化 + 删模板遗留 + P2 扩周频 cron。**已 push `27a18f3..b1d195d`**（Actions 重建部署中）。待业主：审漏斗 → 授权 P3 + cron 频率 + reddit picks + P4 主题④⑤。详见 `state/handoff.md` §2026-08-09(n)。
- **active (2026-08-09):** **Track LLM Phase-0 可行性已证 + PROPOSED 预注册** — 业主问"C+D 结合"→ 推荐 D-first 单变量（EDGAR-LLM filings-tone 作第 42 列，1 trial 干净归因；C/stacking 条件后续）。业主授权自主推进 → 交付 Phase-0：`scripts/track_llm_feasibility_pilot.py`（+8 测试绿，ruff clean）实测 **G1 CIK 解析 100%（OOS 533/533）+ G2 token ~11.71M（一次性）→ 两门 GREEN = FEASIBLE**；cik_resolver ~60% gap 仅历史全宇宙，OOS 窗口不绑定。PROPOSED 预注册 `docs/track-llm-preregistration.md`（未冻结：两尾 null-expected `IC_{41+LLM}−IC_{41-frozen}` HAC；EDGAR 10-K MD&A→GLM temp=0→scalar；n_trials=1；H6 cache-pin；US-only v1）。报告 `reports/design/2026-08-09-track-llm-feasibility-pilot.md`。**0 ledger/frozen/E3/OOS**；未跑 LLM 估计量/未调 GLM API。待业主：审预注册 + 凭证跑 `--measure-llm` 校准 G3/G4 + 裁 D1-D6 → 或弃 D。详见 `state/handoff.md` §2026-08-09(m)。
- **active (2026-08-09):** **Track A 切片 A1 全栈交付（业主授权自主推进至优化到位）** — 业主重提"实时更新+自校正参数往可观"；关键：此问题 2026-08-08 已实测 = Track B（扩窗周重训）**NULL（#54，IC_diff −0.0037，p=0.26）**。业主裁**路径甲（显示层自适应校准）**后授权全栈推进。A1 三 commit：`df34979`（feat(eval) 后端 calibrate_walk_forward + export）→ `681b7df`（docs(state)）→ `459d96e`（feat(web) `/calibration` 视图：recharts 可靠性图+ECE 折线+诚实 null 披露+i18n+nav）。tsc/eslint/`next build` 全绿；真实数据 US pooled_ece 0.037（带紧绕 base rate = 诚实 null）。**A2（漂移）/A3 后向 track record 既有完成；A3 前瞻累计 = E3 owner-GO 门（不可擅自解冻）**。Track A 优化到位。剩余业主杠杆：E3 GO / 新研究线（乙 stacking 或丙 LLM 信号）。详见 `state/handoff.md` §2026-08-09(l)。
- **active (2026-08-08):** 终端历史数据推进至 2016 — COT 全量（10 市场，2016-01..2026-08 连续；CFTC ~2022 重名 variant-union + 单调 merge 抗 cftc 超时；`comp.tail(78)`→全量 series）+ Form4 深化（fetcher `START`→2016 + merge-by-issuer checkpoint + export `yearly` 聚合；后台 fetch ~小时级深化至 2016，当前 2023-2026）。market_context/picks_backtrack/smart_money 既有 2016；ic_monthly/pick_conviction 冻结 OOS **不动**（反泄漏；延展 = rerun-to-significance）。display-only；0 frozen/ledger/E3。详见 `state/handoff.md` §2026-08-08(a)。
- **active (2026-08-08)(c):** Reddit 散户情绪**已激活（零凭证 Atom RSS）**。OAuth 被 2026 Responsible Builder 政策堵死 + 未认证 `.json` 三路全 403 → 改用 Reddit 自家公开 Atom 订阅源 `/new.rss`（ToS-clean，G7；带完整正文 `<content>`，唯一缺 `score`）。`reddit_sentiment.py` 增 `transport=auto|praw|rss`（auto=有凭证 PRAW / 无凭证 RSS）；ticker 抽取 = cashtag（任意大小写）+ 大写裸词 ≥4（WSB 约定；小写=英文散文噪声——实证于真实 WSB `/new` 拉取：真 ticker 大写 PLTR/SMCI/TTWO，英文词小写 well/tech/more）；每 subreddit 失败/畸形 XML 跳过不中断；**凭证缺失在 FinBERT 下载前即 raise**（修了我引入的 ordering bug——曾导致缺凭证时先下 438MB 权重再失败、撑爆 `/tmp`）。新 `scripts/reddit_fetch.py`（零凭证，扫 566 S&P）+ `export_reddit_meta` 读快照→live `reddit.json`。**forward-only/exploratory/不进研究管线**（无 PIT 历史 → 进不了回测；7-gate L108 判决不变）。23 reddit 测试绿 + ruff clean + 真实拉取验证（PLTR/SMCI/TSLA/UBER/TTWO/EPAM/SNDK，FinBERT 情绪合理，score=0 因 RSS）。`export_reddit_meta` 稳定 superset schema（13 key，两分支同构，`tsc --noEmit` CLEAN——修了并发 session 的 build-break：漏 `subreddits`/`collector`/`mode`）。1 行 `data_ingest` ledger（RSS）。**前端 `reddit-view.tsx` 仍为占位符**（未渲染 picks；留前端 owner 接 `status==="live"` 分支，避免与并发 session 的 web-build 管护冲突）。**未提交**（业主 COT/Form4/TACO 已提交；`export_terminal_data.py` 现 M = 我的 reddit export 增量；留业主审阅）。详见 `state/handoff.md` §2026-08-08(c)。
- **active (2026-08-06):** fintech 数据终端**已上线** + special 另类数据持续扩展：TACO（真实 VIX）+ EDGAR 13D 聪明钱 + **选股确信度（Aionis 独有模型元信号，截面分散度）** + Reddit（**已激活，零凭证 RSS；见 (c)**）。
  11 页：Overview/选股决策/证据墙/选股确信度/**多空压力**/内部人/聪明钱/TACO/Reddit/Power Floor/反泄漏。**多空压力（CFTC COT，6 市场上线；10 市场代码就绪待 cftc 恢复）+ 内部人（5 issuer，2415 txns，Jensen Huang 720 卖主导）**。散户情绪：Reddit 已激活（零凭证 RSS）；Trends alpha 仍受阻。详见 `state/handoff.md` § (b)..(j)。
  **待业主**：审 /conviction + Form 4 agent 回报后审 + 13D 刷新 + Quarto/旧站去留。
- **version:** 0.1.0 (pyproject)
- **milestone:** **CONFIRMATORY CLIMAX ACHIEVED (2026-08-05)** — first confirmatory OOS run sediments
  ledger row #49 (`confirmatory:first`, phase=track_c, sig `e14b9d44...` → frozen #48). Combined rank-IC
  = **−0.0088** (null, p_hac=0.484, n=71); J-T look-1 (n=60, RCI 99.44%) = **NOT_EQUIVALENT** (RCI
  [−0.051,+0.027] wider than ±0.010 SESOI = underpowered look-1, NOT an effect signal). H6 double-run
  bit-identical PASS on real data. draft v0.1 → **v1.0-draft** (§5 confirmatory filled). Prior: B/C/D/E1
  ledger results + h={10,42} sensitivity exist; E3 Slices 1–7 + AUD-06 contracts frozen; 2026-07-31 audit
  reclassifies historical evidence as **purged cross-fitted/CV-proxy**, not chronological/live OOS.
- **research verdict:** no B/C/D/E1 treatment arm shows reliable positive incremental rank-IC under
  the frozen nine-column baseline. Phase B has no recorded paired differential CI; Phase C is not
  strictly equivalent within post-hoc ±0.015; none of the four headline arms uses LLM features.
- **active:** `TASK-AUD-00` remediation program. AUD-01 and AUD-03 are COMPLETE after independent Verifier PASS
  and Reviewer APPROVE. AUD-04 is also COMPLETE after repair re-Verifier PASS and Reviewer APPROVE. AUD-02
  documentation reconciliation and AUD-05A are COMPLETE after independent Verifier PASS and Reviewer APPROVE.
  AUD-05B is COMPLETE after re-Verifier PASS and authorized re-Reviewer APPROVE. AUD-05C disposition
  is recorded. C1, C2 and C3 are COMPLETE after owner authorization, Engineer evidence, independent
  Verifier PASS and Reviewer APPROVE. C5 remains owner-gated. The dashboard view extraction and
  owner-authorized C4 standalone cleanup passed review and are committed in `7dede9b`.
- **E3:** engineering may continue, but headline is **NO-GO**. No scheduler, real E2E, or forward result
  exists; shadow/headline must not observe outcome-bearing metrics before AUD-07 and owner approval.
- **agents:** supervisor+worker protocol codified in `docs/orchestration-protocol.md` (ADR-012): opus
  Orchestrator + low-freq opus Supervisor (gates only) + sonnet `executor`/haiku workers (serialized,
  ≤2 concurrent) + independent `verifier`/`code-reviewer`/`qa-tester` lanes; dispatch via
  `scripts/orchestrate_dispatch.py`. One writer per file boundary still binds. Multi-agent inference
  is not part of the stock-selection signal.
- **known issues:** protected historical claims may retain superseded wording; non-chronological historical CV;
  blocked market-source fallbacks and sub-2s fetch paths; Phase B A1 lock stranding; current SIC snapshot;
  ADR-010 Amendment 2026-08-01 APPLIED (Jennison-Turnbull group-sequential equivalence; RCI 99.44/97.64/95.00%; strict-containment; double-opus AUD-07B correction; prereg §7 amended in lockstep) — **E3 statistical-gate HOLD LIFTED**. E3 still gated by AUD-06 live-input readiness + owner GO (no scheduler/real-E2E/forward result yet).
- **last verification (2026-08-01):** Wave-A complete. The full hermetic pytest suite passes (zero skips;
  only the existing forward-score warnings), `uv run --offline ruff check` is clean, `git diff --check` is
  clean, and the frozen prereg/ADR/config/ledger/results/data/forward diff is empty. C1/C2/C3 and
  RD-04/05/06/07/09/10/12 each have independent Verifier PASS + Reviewer APPROVE; committed as `6085e92`
  (Group A), `2653907` (Group B), `5f884a3` (Group C). No frozen config, preregistration, ledger/result
  artifact, or forward outcome changed; no real network/LLM/research/forward script ran.
- **planning (2026-08-01):** a planning-only low-reasoning development program was frozen as
  `reports/milestone/2026-08-01-low-reasoning-development-roadmap.md`, the Wave-A launch brief,
  `TASK-RD-00..17` and strong-only `TASK-AUD-07B`. **Wave-A has executed under the owner-provided Goal
  prompt: C1/C2/C3 + RD-04/05/06/07/09/10/12 are all COMPLETE** (independent Verifier PASS + Reviewer
  APPROVE each; RD-07 byte-stability, RD-10 window/std, and RD-12 manifest-oracle findings were fixed
  and re-gated). RD-01/02/03/08/11/13..17 remain PLANNED for future waves. No real
  network/LLM/data/trial ran; no frozen surface, ledger, result, or E3 outcome changed.
- **evidence:** `reports/audits/2026-07-31-quant-llm-research-audit.md` and `tasks/active/TASK-AUD-00-remediation-coordination.md`.
- **strategic review (2026-08-02):** deep-dive on "是否跑偏 + 七主题低成本覆盖" → `reports/2026-08-02-strategic-review-coverage-and-alignment.md`. Verdict: direction sound; two失调 (目标叙事双轨未裁断; 治理复杂度>研究产出). Produced 6 design artifacts under `reports/design/` (Track A/B slice plans, slice review, qlib-fork-vs-library POC, wheel-mount design pack, reuse-catalog v2) + `src/aionis/eval/ff5_residual.py` (挂接③ FF5 residual + Amihud, 18 tests green, ruff clean; exploratory utility, **not wired to pipeline, writes no ledger**). **Owner decision (2026-08-02):** Track B (seven-theme platform) adopted + new prereg/frozen config → `decisions/ADR-011-track-b-seven-theme-platform.md` + `docs/track-b-preregistration.md` (PROPOSED). First slice 挂接③ (FF5 residual) done. **Pending:** owner freezes Track B config sha256 before any real-data result. B/C/D/E1 frozen surfaces untouched; no real network/LLM/trial ran.
- **Wave-B (2026-08-01):** owner `/goal` authorized the priority offline RD program ("启用更多 agents 根据优先
  等级…各自推进"). 8 sonnet-tier tasks COMPLETE, each Engineer → independent Verifier PASS → independent
  Reviewer APPROVE → atomic commit: RD-01/02/03/11/13/14/16/17 (commits `97e5688`…`f397383`). Full hermetic
  pytest GREEN (only pre-existing forward-score warnings); `ruff check` clean; ledger 0 diff; no frozen
  surface touched; no real network/LLM/trial ran; E3 outcome unobserved. Writers serialized (parallel-writer
  race; see memory aionis-parallel-writer-race). `opus`/`fable` aliases blocked by `[1M]` resolver values →
  AUD-07B + RD-15 deferred; RD-08 HOLD (needs frozen rule table). Safe RD queue exhausted for sonnet tier.
  Not pushed. Detail: `state/handoff.md` § Wave-B FINAL.
- **updated:** 2026-08-05 (h). **arXiv preprint scaffold（已废除：2026-08-15 业主裁决不再发表；工件归档 `archive/manuscript/`）。**
  owner approved framing (a) + LaTeX 预制。`manuscript/` 三件套：`main.tex`（arXiv 通用 article class，仅标准宏包；
  power-floor 为 lead）+ `references.bib`（6 cited，4 WebSearch verified + 2 标准 + 5 extras）+ `README.md`（构建 +
  provenance + gaps）。结构性自查：9 begin=9 end，6 cite key 全在 .bib。**未编译**（无本地 TeX 工具链）。
  **边界**：预制非上传（发表线现已废除）；纯新建 manuscript/ + state；0 ledger/frozen surface/
  prereg/ADR/config/data/E3；未外发。**待业主**：~~首次编译 + 授权 arXiv 上传 + venue 定位~~（已随 2026-08-15 发表线废除作废）。
- **updated:** 2026-08-05 (g). **power-floor 文献锚定 + 复现声明（2 新 PROPOSED 文档；发表强化目的已随 2026-08-15 裁决废除，文档归档 archive/）。**
  owner 第二次 `/goal` 推方向 1。powerfloor sonnet agent [1210] 失败（与 positioning 同模式，§17 停重试）→ opus §8 fallback。
  ① `reports/design/2026-08-05-power-floor-literature-anchoring.md`：把 σ≈0.10 锚定到 Gu-Kelly-Xiu (2020 RFS, 月 OOS R²
  **1.08-1.80%**) + Goyal-Welch (2008 RFS) + Grinold-Kahn Fundamental Law（年化 IR **0.5="good"** → σ(IC)≈7×mean → σ≈0.10
  与 Aionis 0.106 一致）+ Schuirmann/Lakens TOST；WebSearch 验证 4 引用，诚实标注精确 σ 为间接推断（§5 ⚠️）；结论稳健
  （σ∈0.08-0.15 区间内 ±0.010 等价均不可达）；推荐强 framing (a) 升 power-floor 为一等方法学贡献。② `docs/replication-availability.md`：
  reproducible-by-conconstruction（`config_committed` ledger + H6 bit-identical + tracked fetch 脚本）+ 逐源 license 表 +
  独立方复现步骤 + cover-letter 简版；引用核验真实。**边界**：纯 docs（2 新 PROPOSED）+ state；未改已定稿 draft v1.0/v1.0-en
  （venue tailoring 时由业主决定并入引用）；0 ledger/frozen surface/prereg/ADR/config/data/E3；未外发。**待业主**：~~framing 选择 + σ 实证 + arXiv 引用并入 + 复现 package~~（已随 2026-08-15 发表线废除作废）。
- **updated:** 2026-08-05 (f). **产物化收尾（process→product）— 3 推荐 + 1 fallback 全交付（4 commit + 1 memory，push origin/main）。**
  owner `/goal` 授权"推进推荐项 + 批判性比对 + 并行 agents + 分层省 token + reuse-first"。① 静态站点 Track C climax section
  （`e94eac2`，25/25 测试绿，CI 部署成功）；② bps 敏感度 sweep（`3a3c2cf`，复用 `net_cost_summary` 0 造轮子；衰减 gross 0.149→bps=5
  0.125→bps=50 −0.088，break-even ~31 bps；8/8 测试绿）；③ 英文 v1.0-en draft（`52a3d69`，sonnet agent 忠实翻译，数字与 ledger #49
  + 中文 v1.0 交叉核对一致）；④ venue 定位 brief（`reports/design/2026-08-05-publishable-unit-positioning.md`，web search 验证：
  CFR 免费/~28 天/null-再检验 fit / RevFin null 友好 / JFEc 计量 / arXiv baseline；出版商 403 处诚实标注）。positioning agent
  [1210] 失败 → opus §8 fallback 直接写（独立性局限已披露）。分层：2 sonnet agent 并行（draft ✅ / positioning ❌）+ opus 集成。
  memory `aionis-publication-framing-option-a` 写入（锁战略约束：勿再提议拓宽 SESOI / 救 equivalence / 追新 alpha）。全套 pytest
  exit 0；ruff clean。**待业主**：~~选 venue 路径 + 授权 arXiv preprint + venue tailoring~~（已随 2026-08-15 发表线废除作废）。
  **边界**：纯 docs/scripts(state-only)/state/memory；0 ledger/frozen surface/prereg/ADR/config/data/E3 改动；未跑
  confirmatory/forward/strategy；未触 E3；未外发。
- **updated:** 2026-08-05 (e). **选项 A 定稿（accept reframing）— draft v1.0-draft → v1.0。** 业主授权"按推荐方式处理"
  = 选项 A（贡献 = null 点估计 + 反泄漏纪律 + power-limit 披露；**不**拓宽 SESOI、**不**动冻结面、**不**
  rerun-to-significance）。两份独立审计 APPROVE：① power-analysis sonnet review APPROVE（0 blocking/HIGH/MEDIUM，
  3 LOW advisory：AR(1) 近似 / block size / 舍入——不影响"结构性欠功率"结论，analytic + bootstrap 双支撑）；
  ② climax diff review APPROVE（0 CRITICAL/HIGH/MEDIUM/LOW，跨文件数字完全一致，"publish as-is"）。draft 4 处
  定稿（标题+状态、§6 选项段标记 A 已选、§7 边界行、§7 残留 v1.0-draft→v1.0）。**预存 lint 债修复**：
  `scripts/track_c_commit.py:180` E501（跨多 session 的 print 行过长，非本轮 2 commit 引入）→ 提取局部变量；
  **#46 frozen sig 精确复现**（`758ca4d7...` dry-run == ledger，证明编辑未触 config 逻辑）。**验证**：ruff clean；
  全套 hermetic pytest exit 0（仅预存 forward-score/numpy warnings）；frozen-surface diff 仅 `runs/ledger.jsonl` +1
（=#49 append-only）。下一步：commit（lint fix + draft v1.0 + state）+ push origin/main。**边界**：本轮
  docs/scripts(state-only print 行)/state；无 frozen surface / ledger / prereg / ADR / config 改动；未跑
  confirmatory/forward/strategy；未触 E3。
- **updated:** 2026-08-05 (d). **Power analysis 揭示 J-T schedule 结构性欠功率（设计级发现，业主决策待定）。**
  prospective power analysis（`scripts/track_c_power_analysis.py`，复用 #49 IC series 噪声 σ≈0.106 + ρ≈0.07）
  显示 SESOI ±0.010 + looks 60/90/120 **任何一眼都无法宣布等价**：n_min = 869/580/435 月（72/48/36 年）；
  block bootstrap P(equiv)=0.0000 at all 3 looks；look-3 (n=120) RCI half 0.019 >> SESOI 0.010。**判读**：
  look-1 NOT_EQUIVALENT 不是局部保守，是整个 schedule 的必然状态（月频 rank-IC 噪声地板 vs ±0.010 SESOI）。
  E3 forward-live 即使点火也需 ~36 年才达 look-3 等价。**贡献 reframing**：null 点估计 + 反泄漏纪律 + power-limit
  披露（非"等价已宣告"）。业主 3 选项（`reports/design/2026-08-05-track-c-power-analysis-options.md`）：
  A 接受 reframing（推荐）/ B 拓宽 SESOI ±0.025（新 amendment，post-hoc 嫌疑）/ C 延长 horizon n=435（不可行）。
  draft §5/§6 已更新（诚实披露 power floor）。sonnet review 待回报。**边界**：本轮纯新建 script + design brief
  + docs/state；**0 ledger / frozen surface 改动**；未跑 confirmatory/forward；power analysis 用 gitignored artifact。
- **updated:** 2026-08-05 (c). **CONFIRMATORY CLIMAX — 首条 confirmatory OOS 入账（ledger #49）。**
  owner D6 GO 授权后，opus 直接建 `scripts/track_c_confirmatory_run.py`（frozen #48 sig 校验 + H6 双跑
  bit-identical + J-T 门 look-reachable + `confirmatory:first` 沉积；artifact-reuse 模式避免 GO 重跑）
  + `tests/test_track_c_confirmatory_run.py`（19/19 hermetic 绿，含空/NaN/边界边缘用例 + artifact-reuse
  4 守卫）。dry-run 双跑（~46min）证明 H6 → artifact-reuse GO commit 瞬时入账。**结果**：combined rank-IC
  **−0.0088**（p_hac=0.484，CI [−0.034,+0.016] 跨零 = null）；US IC +0.005 / CN IC −0.026；cond-IC β
  −0.0076（p=0.43，regime 交互 null，multiplicity 预算 1 保持）；**J-T look-1 NOT_EQUIVALENT**（RCI 99.44%
  [−0.051,+0.027] 宽于 ±0.010 SESOI = look-1 OBF 欠功率，非效应信号；look-2/3 需 E3 forward-live）。
  **bit-identical 于 asym41 exploratory**（cross-invocation H6）。**独立性**：sonnet code-review APPROVE
  （0 CRITICAL，estimand Reading A 可辩护，H6 充分，look 截断 Type-I 正确）。draft v0.1 → **v1.0-draft**
  （§5 实填 + §4 加 #14/#15 + §0/§7 更新）。**边界**：本轮 1 行 ledger（#49 append-only）+ 新建 scripts/tests
  /docs/state；**B/C/D/E1 + Track B 冻结面 / prereg / ADR 未改**；未跑 research/forward/strategy；未触 E3。
  **climax 判读**：null 点估计 + 欠功率 look-1 = 预期结果（非"不乐观"，非 bug）；J-T 门拒绝过早等价 = 反泄漏
  纪律的活体演示 = 方法学贡献。待业主审 v1.0-draft → 定稿 + 是否 push。
- **updated:** 2026-08-05. **P1 整合（audit 3 caveat 关闭）+ P0 confirmatory-GO 业主签注包交付。**
  **P1(a)** Phase B paired HAC CI 补算 = **[−0.01057, +0.00897]**（ci_half 0.00977，p_hac 0.872，n=125，maxlag=4；
  mean bit-identical #28；orchestrator opus 直接重算，Agent A `phaseb-ci` idle-without-result → memory
  `aionis-agent-dispatch-verification` 从 repo 恢复）。**P1(c)** Track C 3-layer conditional-IC 沉积 =
  combined β=−0.0148 (p=0.21) / us β=−0.0287 (p=0.13) / cn β=+0.004 (p=0.80)（joint-fold IC × 3-layer
  composite；Agent B `trackc-3layer` 交付 + opus 核验；与 handoff culmination 的 Track-B-fitter 单区
  β=−0.001/+0.015 是不同 IC series 的 sensitivity，诚实分级）。**P1(b)** Baseline FF5/RANK 措辞校准
  （exploratory-by-design 非 ledger，audit HIGH #2）+ RESULTS.md §2 行 B 补 CI + draft §4 行 #1/#9 补数字。
  **P0**：`reports/design/2026-08-05-track-c-confirmatory-go-brief.md` 交付；**owner 签 D1=A** → 起草
  `scripts/track_c_amend2.py`（amendment #48，dry-run sig `e14b9d44...`，累积 #46+#47+#48：meso US-only +
  41 列 + Q1/D2/D3/D5 冻结 + baostock G3 raw）+ amend2 doc。ruff clean + sig 自洽；ledger 仍 47 行。
  **✅ ledger #48 已入账**（sig `e14b9d44...`，owner `--commit` 授权 2026-08-05；sha256 自洽；47→48 行）。
  **待第二个业主 GO**（d6_go：授权首次 confirmatory OOS 跑 → J-T 门 → draft v1.0 climax）。**边界**：0 ledger / frozen surface / prereg / ADR 改动；
  未跑 research/forward/strategy；未观察 confirmatory rank-IC / E3。独立性局限：A 由 orchestrator 替代
  （非独立 pass），B 单一交付 + opus 核验（非独立 verifier lane）。
- **updated:** 2026-08-04 (b). **Track C confirmatory machinery staged (joint US-CN fold).** 3 commits
  on main (unpushed): `841fee4` joint fold estimator (`src/aionis/eval/track_c_joint.py`: `fit_track_c_joint`
  + `build_joint_panel` + region-month groups + per-region chronological assert; core insight: month-end
  sampling + calendar-month boundary = auto per-region 21-session embargo, so cv.py/purgedcv 0 change) +
  9/9 anti-degeneracy tests + exploratory runner; `d2606d7` shenwan 7-gate verdict (CN meso G3 fail →
  exploratory-only; confirmatory meso = US-only = current state formalized); `f4bbab7` amendment #48
  PROPOSED (meso US-only). Full hermetic pytest exit 0; ruff clean; 0 frozen-surface/ledger change.
  **Pending**: real-data exploratory joint run (proves machinery on US 588 + CN 929 panels) + independent
  review (Lane C). Confirmatory run needs owner GO + new ledger row #48 + Q1 group-construction sign-off.
  Detail: `state/handoff.md` § 2026-08-04 联合 US-CN 折叠估计量.
- **updated:** 2026-08-03. **BASELINE-FF5-001 + BASELINE-RANK-001 EXECUTED (owner-authorized, `104b21e`).**
  FF5: mean_IC=0.0106 (ci 0.0196, t 1.059, n=125, H6 True) — 18 cols (beta_dff pair RD-13-excluded:
  42 CONSTANT months 2024-08+). RANK: mean 0.015420 (ci 0.014870, t 2.0323, p 0.0421, n=125, H6 True).
  Both EXPLORATORY CV-proxy; config_committed ledger rows BEFORE results. Fixes: RES-02 SIG_ONLY +
  2015-08 window (DFF vintage start); ff5 beta_dff NaN de-contamination; RES-03 month-end sampling +
  month-end folds (LightGBM 10k/group cap) + ledger gate. FF5 snapshot + DFF vintages acquired.
  **E3 Slice 7 E2E COMPLETE + AUD-06 contracts FROZEN (D2) — `0f94620`.** `tests/test_forward_e2e.py`
  (hermetic chain: commit → I1 gate → reveal/score → I2 idempotency + immutable sealed-scores sha256 → accumulate →
  I9 separation; I3–I8 owned by existing suites). `config/e3_live_contracts.yaml`: max_age_sessions 23 → **22** +
  authoritative_refresh null + PROPOSED → FROZEN; cron stays DISABLED (headline needs owner GO). `test_e3_forward_trigger.py`
  aligned 7×. 7 forward suites 84 passed; full hermetic suite exit 0; ruff clean; real-ledger guard PASS.
  E3 code surface COMPLETE (Slices 1–7); remaining: owner GO for shadow/headline. **Orchestration protocol + reuse-first batch all committed & pushed; full hermetic
  suite back to 1352 passed / 0 failed.** **Track B 首个 rank-IC（2026-08-02, treatment 臂, config #41）**: mean_ic 0.0055, CI (-0.021, 0.033), p=0.689 null; DM -1.78/p=0.079 边际（vs 等权）。**差分（#41 treatment - #42 price-only, headline）**: mean_diff 0.0076, CI (-0.004, 0.020) 跨零, p=0.219 → 未显著优于 price-only（null，符合 null-favored）；CI 上界 0.020 > SESOI 0.010 → 不构成严格等价（需更多样本）。
- **orchestration (2026-08-03):** `ADR-012` + `docs/orchestration-protocol.md` + `scripts/orchestrate_dispatch.py`
  (11/11 tests green, ruff clean) + dispatch-contract template landed — owner chose **local task files = issues**
  (zero GitHub surface). Lane model = opus Orchestrator + low-freq opus Supervisor (监工) + sonnet/haiku workers
  (serialized) + independent verifier/reviewer/e2e lanes; 6-layer denoised dispatch; anti-leakage guardrails binding.
  Committed `daa92e8`. **Wave validation**: ORCH-01 macro cumulative-preserve test (COMMITTED `8d19b28`) — first
  dispatch wave: executor succeeded, reviewer lane hit an idle-without-verdict harness gap → protocol §8 hardened
  (`83d9d61`); ORCH-02 REJECTED (`3ad4710`) — premise was a grep-suffix miss (8-K already covered); also found a
  `[1210]`-failed agent can leave partial work in the tree → §8 hardened again. **`/goal` reuse-first batch**:
  `f6e0536` DRY the 3 forward collectors' persist tail into `_common.persist_snapshot` (byte-identical ledger
  output); `e6c71ec` static-site tests aligned to the Track B page (was 12 failing) + hermetic `--out-dir` so
  tests never touch `site/` WIP. **Full hermetic suite: 1352 passed / 0 failed; ruff clean.** Track-B uncommitted
  WIP untouched throughout; no frozen surface / ledger / data touched; no real network/LLM/trial ran.
- **qlib dual-region POC (2026-08-03):** owner-authorized 可逆证据 POC,解决 Option A 辩论(独立批判者 REJECT;辩护/裁断 agent 因 `[1210]` 5 次失败缺失,由 orchestrator 非独立核查替代)。完整报告 `reports/2026-08-03-qlib-dualregion-poc.md`。**5 硬证据:** ①qlib 双区域特性存在(`REG_CN/US`+`LocalPITProvider`+CSI300/500 采集器[从 csindex 历史公告重建,非当日快照]+pit 采集器)→**推翻批判者 #2/#8/#10** vaporware/捏造/当日快照; ②cp313 门(pyqlib 0.9.7 无 cp313 wheel;Aionis 跑 3.13;3.11 隔离 venv `IMPORT_OK` 0.9.7 已验绕过)→部分验证 #2; ③RobustZScoreNorm 泄漏陷阱实证确认+折内钉 fit 修复有效(CLEAN train z-median 0.0000 vs LEAKY −0.3453); ④DatasetH 手术点③需 3h 真实接线; ⑤**baostock G3 结构性不可合规**(`query_profit/balance_data(code,year,quarter)` 期末键、无 as-of/vintage)→**验证并强化批判者 #1**。**Net: Option A′ 条件-sound,8 门实证背书(见报告 §3);** A 股基本面须换 filed-date 键源(cninfo/Tushare-`ann_date`/自建)或降 exploratory-only。Scratch `/home/re/code/aionis-qlib-poc/`(仓库外),合成数据,**未 commit/未触冻结面/ledger**;网络仅 GitHub+PyPI;无 baostock.com 数据调用、无 research/forward 脚本、未观察 E3。Loop cron `3219e84b` 已取消。Owner 未裁决前不构成方向变更;Option A′ 落地=新预注册+新 config+新 ledger 行。
- **Option A′ `/goal` 推进 (2026-08-03):** owner `/goal` 授权(多 agent 按优先级 + 模型分层省 token + reuse-first)。**[1210]** opus/sonnet 子代理今天执行不稳 → 分层:orchestrator 直接 opus 设计 + sonnet/haiku 后台 agent。产出(PROPOSED/docs,未触冻结面/ledger):`reports/design/2026-08-03-conditional-rank-ic-multiplicity.md`(gate 7 解决:预指定交互=1 检验非 K,复用 purgedcv/arch/YannickKae;Deflated-RankICIR 待 license)+ `reports/design/2026-08-03-track-c-prereg-skeleton.md`(Track C 预注册骨架 v0.1;§3 features/§5 折设计/§1 regime 定义 TBD)。后台 agent 运行中:`ashare-gate-research`(sonnet,P0 A 股 filed-date 源 7-gate,gate 4)+ `drankicir-check`(haiku,Deflated-RankICIR license)。下一步待 T1 回报填 Track C §3 + 定 A 股源(headline 可行 vs exploratory-only)。
