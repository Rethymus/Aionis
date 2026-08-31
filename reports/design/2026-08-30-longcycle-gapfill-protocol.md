# 长周期查漏补缺任务协议（Gap-Fill Long-Cycle Protocol）v1

- **日期**: 2026-08-30（轮 45 首轮执行验证）
- **命题来源**: 业主 2026-08-30 —「设计一个长周期性质的查漏补缺任务，需要结合视觉能力
  探查一些代码上未能发现的问题，以及结合专业学科知识判断当前设计的潜在改进空间，
  打磨细节彰显项目的本质」
- **性质**: 超长期循环任务（与轮 ㉝ 起的"查漏补缺+视觉持续优化"系列同族），本协议把
  该系列的隐式做法**显式化为可复用协议**，供后续轮次直接执行。
- **边界铁律**（每轮开场重申）: display/docs lane 优先；**0 ledger / 0 frozen config /
  0 prereg / 0 OOS**；研究面触碰必须预注册级业主 GO；每轮收尾按正典（build→目视→删 out；
  无残留进程）。

## 0. 项目本质（所有打磨的对齐锚）

Aionis = **可证伪、反泄漏的量化研究 harness**。四相 confirmatory 零结果 + Track C 联合
confirmatory 零结果（IC −0.0088，CI 跨零）是**预期成果而非失败**。因此"打磨细节彰显本质"
的判据是：每一处修改是否让「主张—冻结—证据—不确定性」这条链更**诚实、更可核验、更难被
误读**。凡让数字更"好看"的修改都是方向错误。

## 1. 三通道方法学

### 通道 A — 视觉探查（代码看不见的问题）

代码审查/pytest 覆盖逻辑正确性，但看不见：隐形描边、布局挤压、图表空渲染、真实运行时
的框架契约失败。已验证的管线（轮 45 实战）：

1. **构建与伺服**: `node scripts/build-api.mjs && npx next build`（web/）→
   `python -m http.server <port>`（out/）。Streamlit 走 `uv run streamlit run dashboard/app.py
   --server.headless true`。
2. **截图**: Chrome headless — `chrome --headless=new --disable-gpu --hide-scrollbars
   --window-size=1440,3200 --virtual-time-budget=20000 --screenshot=out.png URL`。
   - 明色主题：先经种子页 `__light.html`（`localStorage.setItem('theme','light')` 后
     `location.replace(target)`），种子页放 out/ 内随收尾删除。
   - **Streamlit 例外**: websocket 渲染在 virtual-time 下不完成（白屏假象）——必须真实
     浏览器（`cmd /c start msedge.exe --new-window URL`）+ computer-use 截图/AX 树。
3. **像素地面真值**（对抗视觉模型幻觉的第一道防线，Python/PIL）:
   - 内容密度切片图（16 片非背景像素占比）→ 发现"页面过短=未渲染"或空洞区；
   - 描边色计数（按目标色 ± 容差数像素）→ 直接证明图表线条是否可见（轮 45 用它证明
     轮 44 navy 修复在明暗双主题成立）；
   - 文本级实测：SSG HTML 剥 script/style 后 grep 渲染垃圾（undefined/NaN/[object Object]）
     与关键统计值在墙。
4. **视觉模型审图纪律**（第二道防线）:
   - 全页开放式审查 = 幻觉温床（轮 45 两实测 + 轮 ㉔/㉖ 历史病理一致）；**只对裁剪区
     （≤1/3 页高）提问，只问二元/具体视觉判断**（"CI whisker 是否可见？"），不让它转写
     中文文本、不做开放式"找问题"。
   - 每条视觉模型主张必须交叉核验：DOM/AX 树（get_app_state 读真实元素文本）、像素
     统计、或代码回读。无核验不立项。
5. **AX 树作为 Streamlit 的"DOM 实测"**: `get_app_state` 返回全部渲染元素文本——traceback
   、caption、表格行全部可读，比截图 OCR 可靠一个量级（轮 45 靠它抓到两层运行时崩溃）。

### 通道 B — 学科知识审查（量化/统计语义）

对照 `docs/RESULTS.md` + 冻结账本逐项核对**呈现层语义**：

- **统计语言**: IC/CI/p/t 的语义链是否自洽（例：森林图 derived-t=−0.70 与 p_hac=0.484
  互证）；σ 与 SE 的区分（随机游走带用月 σ 非 SE）；ECE 分档的语境披露。
- **命名纪律**: 已废除概念的遗留词（发表线废除后的 "publishable"）在显示层的残留——
  schema 字段名冻结不动（业主门），显示文案改为当前语义（null-precision gate）。
- **指标命名精确性**: 作用于 IC 序列的 mean/σ·√12 是**年化 IC-IR**，不是 Sharpe（真正的
  Sharpe 在 strategy 面板）——凡把信号一致性指标标成策略收益指标的地方都是误导。
- **账实对账**: 显示层的计数/断言与账本实测核对（轮 45 实例：horizon 视图硬编码
  "3 confirmatory nulls" 而账本是 B/C/D/E1 四相 8 格）。
- **框架运行时契约**: pytest 从仓库根导入掩盖的启动路径差异（sys.path）、框架版本升级
  引入的新强制（Streamlit 1.59 duplicate element ID）、pandas Styler 对 None 的格式化——
  这类只有**真实启动**才暴露。

### 通道 C — 本质打磨（优先级裁决）

发现池按此排序取舍：**诚实性修正 > 可核验性增强 > 运行时可用性 > 视觉/文案一致性 >
美学**。例：修"publishable"遗留词（诚实性）优先于任何配色微调。

## 2. 轮 45 首轮执行记录（协议的验证样本）

**发现与修复**（全部 display lane，0 ledger/frozen/prereg/OOS）：

| # | 发现 | 通道 | 修复 |
|---|---|---|---|
| 1 | Streamlit v1 正典启动命令 `uv run streamlit run dashboard/app.py` **ModuleNotFoundError**——streamlit 只把脚本目录入 sys.path，`dashboard.views.*` 绝对导入不可解析；pytest 从根导入掩盖 | A(AX)+B | app.py 仓库根 sys.path 引导 + pyproject per-file-ignore E402 |
| 2 | `StreamlitDuplicateElementId`：`_cumulative_ic_chart` 在 fit/evolution 双调用同参 → Streamlit 1.59 强制拒绝 → **脚本在 Curve Evolution 崩溃，后 7 标签未渲染** | A(AX 树) | 全部 22 个 `st.plotly_chart` 调用点加唯一 key |
| 3 | 修 #2 后暴露第二层：strategy.py `df.style.format("{:.3f}")` 遇 None 单元格 `TypeError` → Strategy/Forward/Run history 三标签死 | A(AX 树) | None-guard 格式化函数（"—" 占位） |
| 4 | horizon 视图硬编码 **B/C/D 三相**："3 confirmatory nulls"、"/6 cells"——账本实测是 B/C/D/E1 四相 8 格全 null（E1 加入扫描晚于视图编写） | B(账实对账) | 四相化 + 8/8 格 + 图表加 phase E1 |
| 5 | "publishable/publishability/publishable-as-null" 显示文案 = 2026-08-15 已废除的发表线遗留语义，与 NULL-is-intended 框架相抵 | B(命名纪律)+C | 显示文案 → null-precision gate（schema 字段名不动，README 注明 legacy） |
| 6 | IC 序列上的 mean/σ·√12 被标为 "Annualized Sharpe"——量化语义上是**年化 IC-IR** | B(指标命名) | 重标 + st.metric help 披露语义边界 + caption |
| 7 | app.py 自称 "dashboard v2" 与刚退役的 v2 演示面撞名；README 停留在"Phase B/4 视图"时代（实际 11 标签 B/C/D/E1） | C | 标题/文档字符串去版本号 + README 全量重写为如实视图清单 |
| 8 | web 终端 11 研究页 × 双主题：文本级零渲染垃圾、关键统计值全在墙、轮 44 描边修复像素级成立、atlas 森林图/热力图/分差带视觉核验通过 | A(像素+视觉) | 无需修复（记录为基线） |

**验证**: dashboard 相关 73 测试全绿 + ruff dashboard lane 干净 + 全套 pytest（后台回归）
+ 真实浏览器 AX 树终验（11 标签全渲染、无 traceback、新文案上墙、horizon 四相在墙）。

**未立项（如实记录）**: 视觉模型对密集中文页的开放式报告全部判幻觉（转写错误、
重复计数、臆造元素），零采信——验证了"小裁剪+二元问题+DOM 交叉核验"纪律的必要性。

## 2b. 轮 46 执行记录（协议第二批；同日）

**通道池进度**：轮换池第 2 项（Streamlit 剩余标签走查）+ 第 3 项（i18n 术语抽查）+ 第 5 项
（导出↔类型漂移扫描）本轮完成；第 1 项（web 双主题）轮 45 已覆盖。

**发现与修复**：

| # | 发现 | 通道 | 修复 |
|---|---|---|---|
| 1 | coverage 视图为**常量背书**（705/588/0.9272/POM·SE·STI 硬编码），README 却称 "pulled from the ledger"——账本实有 `oos_resolvable_universe`(#25 系) + `universe_crosscheck`(#23 系) 载荷 | A+B(账实对账) | `_coverage()` 接线 durable registry（ADR-006 正典），常量降为 pre-registry fallback，视图新增 `source: ledger 2026-07-27` 来源披露；README 措辞随之成真 |
| 2 | 55 面板中**唯独 reddit 仍用 `{ ...redditJson }` 字面量展开**——正是 2026-08-15 部署事故的元模式（"凡 as typeof xxx 都有同类风险"教训未竟全功），信封 11 键（collector/mode/clearance/score_note 等）无契约类型 | B(漂移扫描) | 新 `RedditPanel` + `RedditPressureEntry` 显式类型（nullability 逐字段对照导出端），reddit-view 冗余本地类型/转换删除；tsc 0 |
| 3 | `powerfloor.intro` zh "非纯数学界" 可误读为"数学界(community)"，en 为 "pure math bound"（=1/√(N−1) 纯噪声界） | B(i18n 语义) | 改 "非纯 1/√(N−1) 下界"（与 power-floor 图题/panel verdict 同语言） |

**新工具沉淀**：`scripts/dev_tabwalk_apptest.py`（11 标签 headless 走查：AppTest 一次
run 覆盖全部标签代码——st.tabs 每 rerun 执行所有子块，断言 uncaught exception/标签序/
诚实标记/selectbox 交互；依赖本机工件，非 hermetic 不入 CI）；`scripts/dev_panel_type_drift.py`
（55 面板顶层键 ↔ TS 类型声明对账；只读 tracked 文件 = hermetic，可作轮守门）。

**验证**：AppTest 走查 ALL CHECKS PASS（零异常；本机缓存态的诚实降级警告逐条在册：
13D events parquet 缺失→compute-failed 警告、CV-fold DEMO 标注、forward runs 缺席 info）
+ 漂移扫描 NO DRIFT + tsc 0 + eslint 0 + dashboard/web 契约 159 passed + 全套 pytest。

## 2d. 轮 48 执行记录（周期 2 首轮；同日）——**重要：视觉管线根因缺陷修正 + 一项误报撤回**

**发现（本轮真正产出，方法论级）**：**本地截图管线自轮 45 起一直在渲染无样式页面**。
构建产物带 GitHub Pages basePath（`/Aionis/_next/...` 绝对路径）；从 `web/out/` 目录直接
起 http.server 时该前缀 404 → CSS 全部不加载；页面因 next-themes 注入的
`color-scheme: dark` 呈现 UA 暗色画布（rgb(18,18,18)），**貌似暗色主题实为无样式渲染**。
自指 junction `web/Aionis → out`（.gitignore #17 正典）正是为本地伺服此前缀而设；
轮 44 收尾删 out 时 junction 一并消失、此后未重建，轮 45 起 out/ 直服 → 全部截图无样式。

**后果与处置（诚实记账）**：
1. 轮 48 由该管线报出的"stock 评分走势图暗色隐形"P1 **经证伪撤回**：受控实验在样式完好
   页面上测原始 attr 写法 → 4,478 绿像素（图表完全正常）；此前 0 绿像素系 CSS 404 下
   `--green-fill` 不存在 → var 回退 black 所致。相应 style 化代码改动已**全部 revert**
   （零产品代码 diff）。
2. 轮 45 的主题保真结论**证据作废、结论以本轮重验为准**：corrected 管线下重验通过——
   conviction 暗色蓝 221/琥珀 116、明色蓝 407/琥珀 183（轮 44 navy→oklch 修复在真实
   双主题成立）；stock 暗色绿 4,478；power-floor 暗色正常。轮 45 的 SSG 文本级扫描
   （垃圾字符串/统计值在墙）不依赖 CSS，**继续有效**。
3. 教训升格：**截图前的 CSS-200 门禁**（curl 任一 chunk 必须 200）+ 伺服目录铁律入 §4。

**验证**：corrected 管线四页双主题像素重验全过（上表）；全套 pytest 基线 exit 0；产品代码
零改动（git status 干净）。**边界**：docs/protocol lane；0 ledger/frozen/config/prereg/OOS。



## 2c. 轮 47 执行记录（协议第三批；同日）

**通道池进度**：第 4 项（`docs/` 逐文档与账本对账）本轮完成——**轮换池五项全部至少执行一遍**，
协议完成第一个完整轮换周期。

**发现与修复**：

| # | 发现 | 通道 | 修复 |
|---|---|---|---|
| 1 | docs 引用完整性：214 条相对链接（433 个 md）中 **6 条死链**集中在两个历史设计文档——track-b slice plan 的 `../` 少一级（`../docs/`/`../reports/`/`../state/` ×4，正确为 `../../`），track-c prereg skeleton 引用同目录文件缺日期前缀（`ashare-fundamentals-source.md` ×2，实为 `2026-08-03-ashare-fundamentals-source.md`） | B(引用完整性) | 逐条修目标路径（move-don't-delete 铁律不破：文档零移动，只修链接）；1 条正则误报（`(≤10)` 数学表达式）排除 |
| 2 | （核验通过项）编号索引 00–08 完整；00-vision/07-roadmap 与现状一致（B–E1 NULL、E3 唯一有功效路径）；ADR 注册表 12/12 全登记；AGENTS.md 引用面 16/16 文件在位 | B | 无需修复（记录为基线） |
| 3 | （核验通过项）**RESULTS.md ↔ 冻结工件逐位对账**：四相 headline（B −0.0008003561696833403 / C −0.006487473568317837 / D −0.0029798406036171702 / E1 −0.0027928949986939897）与 `runs/results/<sig>/differential.json` **bit-identical**；§6 账本行号索引（#28/#30/#34/#37 confirmatory + #49 track_c）与 ledger 实际行号吻合（sensitivity #39=latest amend，与 backlog 记录一致） | B(账实对账) | 无需修复——项目的本质主张（可追溯性）经受住逐位核验 |
| 4 | （甄别不动项）adaptive-design-research.md 与 dashboard-v2-design.md 中的发表线措辞均带日期锚（"per the 2026-08-05 framing"）= 2026-08-15 裁决的历史记录保留类，不改写 | B(命名纪律) | 零触碰 |

## 2e. 轮 49 执行记录（周期 2 第 1 项收尾；同日）——修正管线全量非研究页双主题巡检：零缺陷

**背景**：轮 48 的 37 张巡检图全在坏管线（无样式）上拍，仅重验了 3-4 页；本轮用修正管线
（web/ junction 伺服 + CSS-200 门禁）补齐全量证据。

**结果**：19 页 × 明暗双主题 38+ 张截图——
1. **底色全为真实主题色**（暗 #0a0a0a/#000、明 #fff/#fafafa），样式渲染确认；
2. **零渲染缺陷**：fine 阈值（@25）下暗色内容量处处 ≥ 明色，无任何"某主题下元素缺失"；
3. **两个初报不对称均判测量伪影**：reddit（@60 明 30% vs 暗 10%）与 heatmap（@60 暗 13% vs
   明 4%）在 @25 阈值下反转/收敛（reddit 暗 48% > 明 38%）——暗色设计的 alpha 淡彩
   （10% tint over #0a0a0a）天然低于固定阈值的检出范围，非渲染缺陷；
4. **一次视觉模型顺序误报证伪**：其称明色 reddit "我们的采集"在前——JSX 源序（状态卡→
   Trending→ours）+ 头部裁剪目视双证其描述错误；
5. **一次捕获瞬时失败**（明色 manager 28KB 空图）——重拍正常，记为管线 flake。

**方法学沉淀**（入 §4）：双主题密度对账**必须双阈值**（@60 粗 + @25 细）——单一阈值在
alpha-tint 暗色设计上系统性偏向明色，会制造假"暗色缺失"信号（本轮两例实证）。

## 3. 后续轮次的轮换建议（长周期节奏）

> **周期 1 已完成**（轮 45–47：五项轮换池全部执行一遍）。周期 2 建议：① web 全路由
> （22 页非研究页）双主题复审 + 新增面板；② Streamlit AppTest 走查脚本随每次 Streamlit
> 相关改动重跑（含 event/earnings 真实数据路径——待 cache 补齐后验证 CAR 图）；
> ③ i18n 深查第二轮（其余 hub 页术语 + 英文语法级抽查）；④ docs 第二轮（preregistration
> 文档与冻结 YAML 的一致性只读核验——零改写）；⑤ 新增面板随建随扫（漂移扫描器已 hermetic
> 可守门）。

1. **每轮开场**: 读 state → git status → `uv run pytest -q` 基线 → 选 1-2 个通道深耕
   （不必三通道全开）。
2. **通道轮换池**:
   - web 研究五页（dashboard/track/atlas/power-floor/model-health）× 双主题像素+视觉复审；
   - Streamlit 其余标签逐个 AX 树走查（event/coverage/history 尚未逐标签核过）；
   - i18n 字典 zh/en 语义等价抽查（统计术语的英文对应是否学科正确）；
   - `docs/` 逐文档与账本对账（RESULTS.md 已多轮核过，优先 08 索引与 rubric 文档）;
   - 导出面板 ↔ 显示层字段语义漂移扫描（export_terminal_data 7285 行 vs web 类型契约）。
3. **停止条件**: 单轮 ≤2 个 P1 级修复；连续两轮零新发现 → 通道降频为月度巡检。
4. **升级路径**: 凡涉及研究面（ledger/frozen/config/prereg/OOS）的发现**只记录不动手**，
   进 backlog 待预注册级业主 GO。

## 4. 已知工具病理备忘（每轮重读，省重踩）

- **【头号】本地截图必须经 `web/Aionis` junction 伺服，且截图前先过 CSS-200 门禁**。
  构建产物带 basePath（`/Aionis/_next/...` 绝对路径）：从 `web/out/` 直服该前缀 404 →
  CSS 全不加载 → 页面以 `color-scheme: dark` 的 UA 画布呈现，**貌似暗色主题实为无样式
  渲染**（轮 45/48 均中招：轮 48 由此产出 stock 图"暗色隐形"误报，受控证伪后撤回）。
  正典流程：`cmd /c mklink /J web\Aionis web\out`（已 gitignore）→ `cd web && python -m
  http.server <port>` → URL 带 `/Aionis/` 前缀 → **先 curl 任一 CSS chunk 必须 200** 再截图。
  明色主题经种子页跳转时，种子页重定向目标同样必须带 `/Aionis` 前缀。
- **部署门禁：`node scripts/build-api.mjs` 必须先于 `next build`**（npx next build 不执行
  prebuild 钩子）——漏跑则 public/api 镜像停留在旧版，gh-pages 上线后公开 API 与页面数据
  劈叉（轮 51 实证：页面 v3/API v2，在墙验证抓到后补镜像重部署）。部署后在墙验证必须同时
  查页面(200)与 API 面板内容标记（如 inventory version/digest），不可只查 200。
- **截图模式按页型选择**：静态/无轮询页用 `--virtual-time-budget`（快进入场动画）；带
  实时价格轮询的页（/stock）virtual-time 永不结算会挂死 → 用 `--timeout=12000` 墙钟
  （SSG SVG 无动画安全；recharts 动画图需让动画播完，必要时 virtual-time）。recharts
  图打在动画首帧 = 假"空白图表"。
- **构建期不得让任何进程以 out/ 为 CWD**（http.server 尤甚），否则 EBUSY 使 build 静默
  失败、out/ 停留旧产物——后续"验证"全部打在过期页面上（轮 48 实证）。
- **双主题密度对账必须双阈值**（@60 粗 + @25 细）：暗色设计的 alpha 淡彩（10% tint over
  近黑）在单一 @60 阈值下系统性漏检，会制造假"暗色内容缺失"信号（轮 49 reddit/heatmap
  两例实证——@25 下反转或收敛即伪影；真缺陷在双阈值下都缺）。种子页重定向捕获偶发空图
  flake（~30KB）——对账前先查文件尺寸，异常即重拍。
- Chrome headless 相对路径截图会写失败（拒绝访问）——`--screenshot` 必须绝对路径。
- CDN 传图给视觉模型必须**原样传反斜杠路径**（改正斜杠破坏签名 → 1210 错误）。
- Streamlit 改模块后必须**重启服务进程**（sys.modules 缓存，浏览器 F5 不重载已导入模块）。
- `--virtual-time-budget` 对 websocket 应用（Streamlit）无效，白屏是假象。
- Edge 启动走 `cmd /c start`（MCP open_application 对 Windows 名称解析不稳）。
- **标签内容走查的正典工具 = `scripts/dev_tabwalk_apptest.py`（轮 46 新增）**：Streamlit
  官方 AppTest headless 执行整个 app——`st.tabs` 每次 rerun 会运行**全部**标签代码，
  故一次 `at.run()` 即覆盖 11 标签；断言 uncaught exceptions/标签序/诚实标记/selectbox
  交互。依赖本机工件（runs/results、data/cache），**非 hermetic，不入 CI**——是研究者
  本机 walk 工具。浏览器像素点击在背景 UI 动画时全屏帧易 stale——内容走查一律走 AppTest。
- **watch：`use_container_width` 已过 Streamlit 弃用截止日（2025-12-31）**，现装 1.59
  仍容忍（deprecation warning 刷屏）。未来升级 Streamlit 大版本会硬破 22 个调用点——
  届时统一迁移 `width='stretch'/'content'`；升级前每次全站走查会继续提醒。
