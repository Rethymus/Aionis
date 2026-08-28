# 编辑级图表语言(Editorial Diagram Language)— Aionis 研究图谱设计规格

- 日期:2026-08-28
- 状态:APPROVED(本轮实施 R0;R1-R3 为前瞻路线,待后续轮次)
- Lane:display(纯展示层;0 ledger / 0 frozen / 0 config / 0 prereg / 0 OOS)
- 触发源:业主 /goal —— 研读 diagram-design 文章(mp.weixin.qq.com/s/JJKkzrrf9Rmr62YMkchykQ),结合金融学知识与数据透视/BI 视角,为"量化选股策略研究"赋予多样化、更可靠的可视化呈现;设计开发任务分离,分配给不同 agents。

---

## 1. 源文章研读结论(diagram-design)

文章介绍 `diagram-design` Agent Skill(github.com/cathrynlavery/diagram-design),核心特性:

1. **39 种编辑级质感图表**——架构图、流程图、时序图、状态机、ER 图、时间线、泳道图、象限图、雷达图、飞轮图、树状图、组织架构图、甘特图、散点图、桑基图、鱼骨图、Wardley 地图、看板、用户旅程图、部署图、依赖关系图、UML 类图、数据库表结构图等。
2. **自包含产物**——每图输出单文件 HTML/SVG,零 JS 依赖、零外部图片、零构建步骤,浏览器直开。
3. **品牌风格适配**——读取目标网站的配色与字体,映射为语义角色;全程 WCAG 对比度检查,不足时主动提示。
4. **三种静态变体**——简约浅色 / 简约深色 / 完整编辑样式。
5. **重绘既有图**——Mermaid/Draw.io 源文件以同一设计系统重绘;输出格式(HTML/SVG/PNG)× 尺寸 × 细节程度(保真/平衡/简化)× 目标受众(工程师/高管)四维可调。

## 2. 概念移植:为什么这与 Aionis 哲学同构

| diagram-design 特性 | Aionis 对应物 | 结论 |
| --- | --- | --- |
| 零 JS 自包含 SVG | H6 确定性(同输入逐字节同输出)、静态导出 1,502 页 | **服务端渲染确定性 SVG** 是本项目图表的正确形态——构建期布局固定、运行时零水合、字节稳定 |
| 品牌风格适配(WCAG 检查) | Apple HIG 设计系统(oklch token、已做过 WCAG 全站审计、双主题) | 图表 token 绑定 CSS 变量,双主题自动同步;对比度沿用既有审计结论 |
| 39 种图类型 | quant 研究传播只需要一个精选子集 | 不照单全收;按"每张图必须承载一个可证伪主张"的原则筛选 |
| 细节程度 × 目标受众 | 双语(zh/en)+ 方法学脚注传统 | 每图带表格回退(无障碍/降级/移动端)+ 方法学披露 |

**红线**:
- 涨跌方向语义色(`--up/--down` 与 colorconv 约定)**不进入**本图表语言——研究图谱编码的是类别与围绕零的发散幅度,不是价格方向;用蓝↔橙发散色标(色盲安全,亦与编辑风格默认的橙色强调一致)。
- 展示层红线:任何图不得暗示"该买什么";IC/校准/分差图呈现的是**测量可信度**,包括不好看的月份与 NULL 判定——诚实呈现零结果正是本项目的立身之本。

## 3. 真实数据核查(2026-08-28 实测,可行性证据)

| 面板 | 实测内容 | 支撑图 |
| --- | --- | --- |
| `metrics.json` | combined_ic=-0.0088, p=0.484, 95% CI [-0.0336, 0.0159], verdict=NULL, sesoi=0.01, n_months=71, H6=PASS, ledger_row=49 | 森林图(主张区间) |
| `ic_monthly.json` | 66 条月度记录 × {month, us, cn, combined} rank-IC | 月×区域热力透视图 |
| `calibration_reliability.json` | regions.us/cn 各 53 个月:{month, n_pred, ece_oos, base_rate, prob_min, prob_max};method=platt, walk_forward=true | 预测—实现分差带 + ECE 分差 |
| `data_health.json` | 49 面板 × {category(frozen 15/daily 25/cadence 9), as_of, exported_at, rows};summary 五数 | 血缘流图第 2-3 层 |
| `api_catalog.json` | 49 端点 × {source(48 种一手来源描述), license, freshness} | 血缘流图第 1 层(按来源族归组) |

结论:**全部素材已在已提交面板内,零新抓取、零新导出即可成图**(与 force-camp 同款纯派生 display lane)。

## 4. R0 架构决策(本轮实施)

1. **单一路由 `/atlas`**(研究图谱),置于 `校验(nav.group.verify)` 导航组;/track(测量可信度)、/discipline(纪律)、/data-health(水位线)之后的第四件套——前三者回答"守不守纪律",atlas 回答"研究说了什么、说得多可信"。
2. **确定性渲染(仓库既定模式)**:视图组件顶层 `"use client"`(i18n provider 是客户端方案,全部既有视图如此),但经 Next 静态导出 **SSG 预渲染**——布局与坐标在构建期由已提交面板算死,构建产物字节确定;运行时零数据请求、零水合差异。`<figure>/<figcaption>` + sr-only 描述 + **完整数据表格回退**(force-camp 先例:表列头永远渲染,诚实空态)。零客户端 JS 的纯服务端 SVG 记为 R 系列演进项(需先解决 i18n 服务端化,见 §6)。
3. **共享设计系统** `web/src/components/diagram/`:
   - `tokens.ts`——语义色角色(绑定 CSS 变量的 ink/muted/border/card/primary)+ 主题无关的蓝↔橙发散色标(围绕零居中)+ 色盲安全声明;
   - `primitives.tsx`——极简服务端原语:`scaleLinear`、`niceTicks`、`DiagramFigure`(无障碍包装)。
4. **三个区块组件,三个 agents 分仓开发**(文件集互不相交,共享文件全部由主线预接线):
   - D1 `components/atlas/atlas-claims.tsx`——月度 rank-IC 热力透视(66 月 × US/CN/合并)+ 结论森林图(CI vs SESOI vs 零线);
   - D2 `components/atlas/atlas-divergence.tsx`——预测—实现分差带(prob_min–prob_max 带 vs 实现 base_rate,US/CN 双栏)+ 月度 ECE 分差条;
   - D3 `components/atlas/atlas-dataflow.tsx`——数据血缘三层流图(一手来源族 → 面板类别 → 新鲜度;节点面积=面板数,分层确定性布局,桑基式)。
5. **i18n 全部由主线预置**(dict.ts 单点写入,消除三分支 cherry-pick 冲突面);agents 只消费 `t()` 键。
6. 验证:tsc 0 / eslint 0 error / 全套 pytest / build 页数 +1(1,503)/ 三区块目视终验 + 色标在双主题下的可读性抽检。

## 5. 金融学叙事:每张图回答什么问题

- **热力透视**:预注册主张的横截面 rank-IC 是否在时间与区域上稳定?——呈现完整 OOS 序列(66 月),包括失效月份;NULL 结论的"分布语境"一眼可读。
- **森林图**:点估计落在哪、区间多窄、相对实际显著域(SESOI ±0.01)处于何处?——把"零结果 + 窄区间 = 有信息量的结论"这个方法论立场变成一张图。
- **分差带**:模型预测概率带是否诚实覆盖当月实现基准率?"蝴蝶效应"语境下,预测的意义不在点命中而在**区间校准与分差度量**(带内覆盖率、ECE)。
- **血缘流图**:每个数字从哪来、什么节奏、什么 license?——反泄漏纪律的可视化:冻结面板为何不日更、日更面板从哪个一手源来,在图上一目了然。

## 6. 前瞻路线(R1-R3,记录不实施)

- **R1 BI 透视图(探索层)——R1-lite 已于轮㉗落地**:分数面诊断透视图(月×区域的 score σ/IQR/宇宙宽度/月度秩自相关),纯派生自冻结 `runs/track_c_confirmatory_oos_scores.parquet`(94,438 行),零收益口径风险;面板 `score_diagnostics.json` + 契约测试 + /atlas 第四区块。
- **R1-full(decile 收益单调性)——业主门**:金标准诊断需要全样本前向收益(94,438 行 × 价格 join)。`picks_backtest` 只有 top picks 收益、`strategy_returns` 是组合级;在展示层重算收益需与冻结 run 的收益口径(next-open vs close 等)逐一对齐,否则呈现的"分差"是口径伪影。归属研究相邻 lane 决策,不擅启。
- **R2 独立图表工件**:构建期生成自包含 HTML/SVG 研究图表文件(文章的完整形态),如 `runs/` 附带的 phase 报告插图;Mermaid/Draw.io 源重绘通道。
- **R3 品牌适配器**:从任意品牌 URL 提取配色/字体并映射为语义角色 + WCAG 核验(文章的 brand-adapter 概念),服务于未来多皮肤部署。
- 每一期都保持 display/派生 lane 与"每图承载一个可证伪主张"原则。

## 7. 任务拆分与边界

| 任务 | Agent | 产出 | 共享文件 |
| --- | --- | --- | --- |
| 基础设施+接线 | 主线 | tokens/primitives、dict 全量键、nav/cmdk 接线、任务书×3、本规格 | dict.ts, top-nav.tsx, command-palette.tsx |
| D1 主张透视 | agent-d1(worktree) | `components/atlas/atlas-claims.tsx` | 无(只新增文件) |
| D2 分差带 | agent-d2(worktree) | `components/atlas/atlas-divergence.tsx` | 无(只新增文件) |
| D3 血缘流图 | agent-d3(worktree) | `components/atlas/atlas-dataflow.tsx` | 无(只新增文件) |
| 路由组合+集成验证 | 主线 | `app/(dashboard)/atlas/page.tsx` + cherry-pick ×3 + 全套验证 | page.tsx |

风险与缓解:三分支零共享文件 → cherry-pick 预期零冲突;worktree 内无法 next build(Turbopack 跨根限制,先例)→ build 归主线集成期执行;node_modules 以 junction 共享(清理铁律:junction 先摘再删,主线统一执行)。
