# Super-Agent 整合设计报告——P0 核验判定 + 四篇文章/轮子取舍固化（2026-11-11，轮 126）

> 性质：业主「Super-Agent 整合与 P0 核验」专项的设计报告。方法：P0 现状实证诊断
> （全部只读）+ 四篇文章精读 + 两路开源轮子调研（许可证逐仓 `gh api` 核验）→
> 整合落点与取舍固化。**边界**：研究管线（src/aionis、scripts/phase_*、runs/ledger.jsonl
> 语义）零触碰；本报告不设任何「修复代码缺陷」条目——P0 诊断判定 laneFailing=false
> （§1）。机制类整合条目按同轮施工清单落地，逐条记录以 `state/handoff.md` 轮 126+ 为准。
> 文章抓取与轮子许可证核验为本轮（2026-11-11）实测，非转述。

## 1. P0 判定：「定时任务频繁失效」不成立（laneFailing=false）

**判定原文**（P0 诊断结论）：「定时更新数据任务频繁失效」经实证**不成立**。近 30 天
22 个工作日晚中 19 晚 `ok_committed`，仅 11-03/04/05 三个失败晚——系 form8k 聚合突破
cap 300 后契约门**按设计自锁**（防泄漏纪律的胜利，非平台/代码事故），`5a1075f650`
（raise cap + dedicated module）修复后 11-06 起连续恢复；GitHub Actions 红牌全部为
平台侧计费锁定（billing issue，秒级红）或测量仪布线缺陷（vintage 探针，已修复待复验）。
**无真实代码缺陷待修。**（本轮 11-11 复测：Tests 连红实测 13 条，判定原文记 14——
差 1 条见 §1.3 口径注记，不改变分类与判定。）

### 1.1 本地通道健康（本轮实测）

- `uv run python scripts/ops_local_refresh.py --status`（2026-11-11 00:5x 实跑）：
  `date=2026-11-10 / status=ok_committed / commit=57691cc8a6 / pushed=true / n_files=58
  / backup=ok / soft_fails=[]`——11-10 晚通道全绿。
- 运行日志目录 `runs/ops_local_refresh/` 近 30 天 30 个尝试日（周末按 SKIP 设计自然缺席）；
  11-03/04/05 三个失败晚与判定完全吻合。
- 恢复链实证：`runs/ops_local_refresh/2026-11-06/run.log` SUMMARY =
  `ok_committed 7e69c3bc17 / 58 文件 / backup ok`；11-09（287ad2f5cd）、11-10（57691cc8a6）
  连续 `ok_committed`。

### 1.2 三失败晚根因链：form8k cap 300 → 契约门按设计自锁（已根治类）

- 根因证据（`runs/ops_local_refresh/2026-11-03/run.log`）：form8k 聚合当日
  `[form8k-fetch] seeded aggregate: 300 filings` 触帽，晚班重跑时严格 JSON 门
  `test_form8k_panel_contract` 断言失败——
  `by_category[officer_changes] disagrees with event list: assert 59 == 61`
  → `HARD-FAIL: hard-fail step 'json validity + contract gate'`（21:46:16）。
  11-04/11-05 filings 308/312 继续越帽，同门连晚自锁。
- **语义**：这不是数据通道失效，是**契约门在数据越界时拒绝放行**——与 9-30
  影子 fail-closed（`predict_session_not_in_panel`）同构：门按设计工作。
- 修复：`5a1075f650 fix(export,web): form8k growth guard fires — raise cap + dedicated
  module`（cap 300→600 + form8k 专模块 + 三日数据）；修后首个工作晚 11-06 即恢复
  `ok_committed`（§1.1），11-06 当日 filings=316 在新帽 600 内。

### 1.3 Actions 红牌分类：全部为平台侧计费锁定（钥匙在业主）

本轮 `gh run list` 实测（2026-11-11）：

| 工作流 | 连红段 | 连红数（本轮实测） | 末次绿 | 分类 |
|---|---|---|---|---|
| Tests | 11-05T15:54 → 11-10T11:27 | **13 连红** | 11-02T11:33 | billing-lock |
| Publish site (gh-pages) | 11-05T15:54 → 11-10T11:27 | **4 连红** | 11-02T11:33 | billing-lock |
| staleness-check | 11-05T17:24、11-09T09:48 | **2 红** | 11-02T09:31 | billing-lock |

> 口径注记：判定原文（诊断时点 11-10）记「Tests 14 连红」，本轮 11-11 复测
> `gh run list --workflow=Tests -L 25` 逐条清点为 **13**（11-02T11:33 success 之后
> 全 failure）。差 1 条不改变分类（全 billing-lock）与 laneFailing=false 判定，
> 按 handoff 轮 121 同款「以复测为准」惯例如实并记。

- 计费锁定签名（本轮 `gh api .../runs/<id>/jobs` 实测）：最新红 Tests 的 job
  `pytest + ruff (hermetic)` **steps=[]（零步执行即 failure）**——job 根本没启动，
  与 handoff 轮 118 现场记录的注解 `account locked due to billing issue`（4 秒级红）
  一致。计费锁定 #2 的观察与影响面（publish-site 停更、绊网失明、本地通道不受影响）
  见 handoff 轮 118（提交 `18001a804d`）。
- **vintage 探针**（红牌中唯一非计费类）＝测量仪布线缺陷，已修复：handoff 轮 121
  **定性撤销**轮 112 的「模型不再可靠识别冻结截止锚点」研究信号判定——三次月度 CI
  探针问的是陈默认模型 glm-4-flash 而非冻结边界实测的 glm-4.7-flash；修复
  （vintage-probe.yml:70 注入 `LLM_MODEL: ${{ vars.LLM_MODEL || 'glm-4.7-flash' }}`
  + probe/providers fail-closed，本轮文件级复核在案）已推送。**复验安排**：billing
  解锁 + 修复在远端 main 后，按 docs/ops-local-refresh.md 恢复 runbook 于 **12-03 首跑**
  workflow_dispatch 重跑核对（新 artifact model=glm-4.7-flash 且 status=stable）。

### 1.4 判定对整合的约束

诊断结论**决定报告与施工清单的形态**：不设任何「修复代码缺陷」条目；P0 的三个
未决项全部是**业主钥匙**（§5），工程侧无可代办项。

## 2. 四篇文章精读：引用与取舍

> 抓取方式：r.jina.ai 代理全文抓取（2026-11-11 实测）。第 4 篇（微信公众号）被
> 微信「环境异常」验证拦截页阻断（直抓/代理均仅返回点赞壳文本），**正文不可读，
> 不引用任何未读到的内容**，如实标记 partial。

### 文章 1（full）：DeepSeek Harness《Super-agent 设计探索：迈向更自主的 Agent 系统》

- URL：https://zhuanlan.zhihu.com/p/2099987320443237060
- 主题与立场：把计算机系统经典设计思想（Fast/Slow Path、批处理、存算分离、投机执行）
  迁移到 Agent 构建；四大特征＝连续/高效/主动/持久。部分设计已开源
  （dsh-superagent-prototype）。
- 关键机制与数字（引用备查）：双层架构（常驻 Router 只分发、Worker 上下文隔离执行）；
  事件驱动 Trigger（程序层 Fast Path + 语义层 Slow Path 两级过滤）+ Worker 直通订阅；
  Inline & Spill（上下文窗口当 Cache，低频信息留引用按需召回）；Watchdog（主系统外的
  独立 Control Loop，用模型判断任务死循环/目标偏离）。消融：Super-agent 任务完成
  p50/p95=12.4/15.7 分钟 vs 单 Session+Subagent p95=29.5 分钟（中性提示 5 次运行 0 次
  委派）；去掉直通后完成时间不变但 Router 决定数 +30%、读缓存 token +37%
  （2323 万→3177 万）；Router 压测 Trigger 1→40 条/分，单决定分摊推理 6.4s→1.6s。
- **取舍：采纳**——Router/Worker 分工、事件驱动两级过滤、Watchdog 独立回路、
  Inline/Spill 四个概念成为 §4 落点的引用锚；**不采纳**——其云端存算分离/BYOM 与
  投机执行全量形态（Aionis 单机本地栈已满足状态存放，投机执行违背 token 经济，
  §3/§4 详）。

### 文章 2（full）：linux.do《通了个宵，终于把 Super-Agent 架构玩明白了。》

- URL：https://linux.do/t/topic/3109398
- 主题与立场：对 DSH 文章（即文章 1）的解读与消化，高度认同其「从计算机底层出发」
  路线；补充问题起点论证——个人注意力只能覆盖约 3-5 个 Session，多任务上限取决于
  人的注意力。
- 增量要点：Inline/Spill 的「编译优化/内存换页」类比；投机执行＝用算力换人的等待时间；
  异步 ReAct Loop（阻塞式一问一答 → 全双工）；Watchdog 专门捕捉「进程级监控看不到的
  LLM 死循环/目标偏离」。
- **取舍：采纳**——「注意力上限」论证用于校准 Aionis 整合尺度（少而实，宁缺毋滥）；
  Watchdog 的「监控看不见的异常」定义写进 §4 落点。**不采纳**——无独立新增机制。

### 文章 3（full）：linux.do《从底层逻辑聊聊 super-agent 到底怎么实现的》（Wxh_Hugo，2026-11-05）

- URL：https://linux.do/t/topic/3126653
- 主题与立场：剥掉名词包装的机制性讨论——双层架构、事件驱动、多信道交互
  「本质上是同一套机制的三个侧面」＝异步执行任务 → 产生新消息 → 投递到对应
  session → 继续运行。
- 增量要点：子 agent loop 封装成工具；异步工具调用立即返回「已启动」；消息投递
  两时机（run 中入队 steer / run 后追加发起新 run）；与 swarm（handoff=换提示词）
  的区别。
- **取舍：采纳**——「三个名词一条链路」的机制观支持 Aionis 的复用优先判断：本项目
  既有自动化已实现该链路（§4.2），**无需引入任何新框架**。**不采纳**——为其复刻
  消息路由基础设施。

### 文章 4（partial，正文不可读）：微信公众号文章

- URL：https://mp.weixin.qq.com/s/lcIkBMOKHSvkRYELgkduMg
- 抓取状态：**partial/blocked**——微信反爬「环境异常，完成验证后即可继续访问」
  拦截页（直抓与代理各一次均如此；fox_fetch 二次实测仅返回点赞/在看壳文本）。
- **取舍：不引用**——按「禁止编造未读内容」纪律，本文不参与任何采纳/不采纳判定；
  其在专项中的定位（super-agent/智能体设计类文章）仅由工作流分组设定，本报告
  不据此作任何实质性引用。

## 3. 两路轮子调研：采纳/不采纳清单

> 许可证与星数为本轮 `gh api repos/<owner>/<repo>` 逐仓实测（2026-11-11），非转述。
> 决策准则：许可证仅 MIT/Apache/BSD；「只借鉴协议/模式而不引入依赖」优先级最高；
> token 经济不恶化；禁止后台长驻进程；研究管线零触碰。

### 3.1 路线 A：智能体编排 / 记忆 / 自进化

| 候选 | 许可证（实测） | stars | 判定 | 理由 |
|---|---|---|---|---|
| langchain-ai/langgraph | MIT | ~44.8k | 不引入依赖 | 重框架；编排需求已被 ZCode workflow runtime + AGENTS.md 角色分工满足 |
| crewAIInc/crewAI | MIT | ~60.7k | 不引入依赖 | 同上；多 agent 角色体系与现有 Orchestrator+specialist 重复 |
| FoundationAgents/MetaGPT | MIT | ~71.2k | 不引入依赖 | SOP 驱动软件公司隐喻重；借鉴其「角色边界」思想即可（已内建于 AGENTS.md） |
| OpenHands/OpenHands | MIT | ~93.1k | 不引入依赖 | 全功能 agent 平台需常驻服务化环境，违「无后台长驻进程」与 token 经济 |
| microsoft/autogen | **CC-BY-4.0（仓级）** | ~61.8k | **排除** | 仓级许可证不在 allowlist（MIT/Apache/BSD）；即使包级 MIT 也不采 |
| mem0ai/mem0 | Apache-2.0 | ~68.8k | 不采纳 | 外置记忆库＝独立状态存储+服务化，与 ADR-006 durable registry、账本纪律冲突 |
| letta-ai/letta | Apache-2.0 | ~25.4k | 不采纳 | 同上（常驻 agent 服务器） |
| SEAL/Reflexion/Voyager（思路类） | —（论文/思路） | — | 仅借鉴不实现 | 自我进化循环与「冻结先于结果、禁止 rerun-to-significance」的证伪纪律冲突 |

### 3.2 路线 B：运维自愈 / 定时任务可靠性 / 自审闭环

| 候选 | 许可证（实测） | stars | 判定 | 理由 |
|---|---|---|---|---|
| jd/tenacity | Apache-2.0 | ~8.8k | 不引入依赖（现阶段） | 现有 fetcher 的 ≥2s 礼貌间隔+指数退避已在 `src/aionis/ingest` 实现且属研究管线面（零触碰红线）；仅当未来 **ops 层脚本**需要标准化重试时按需评估 |
| 自愈管线/看门狗模式（self-healing、watchdog、nightly-audit 类项目） | —（模式） | — | 采纳模式不采代码 | 对应物已存在且更贴合：--doctor 七层预检、夜报班、data snapshot 绊网、verify_claim 一键验证器、Windows 计划任务兜底 |

### 3.3 采纳清单（零依赖、模式级）

1. **Router/Worker 分工纪律**（文章 1/3）→ 即 AGENTS.md「Orchestrator 不写大代码、
   specialist 各管一段」的既有边界；整合期间继续以「Router 分发、Worker 施工」执行。
2. **事件驱动 + 两级过滤**（文章 1）→ 既有触发面（SessionStart 钩子 18:00-24:00、
   Windows 计划任务 6 档 18:05-23:05、Actions 事件驱动 CI）已覆盖；未来新增触发器
   一律走「程序层 Fast Path 筛噪音 + 语义层 Slow Path 判断」两级，不把 LLM 放在
   噪音路径上。
3. **Watchdog 独立回路**（文章 1/2）→ 原则「看门狗必须在被监控系统之外」已满足
   （Windows 调度器独立于 ZCode/钩子）；保持 --doctor/夜报班/绊网三层的独立性，
   不合并进被监控通道本体。
4. **Inline/Spill 上下文卫生**（文章 1/2）→ 对应 state 读取纪律：`state/current.md`
   只读首条、handoff 按需检索；大块信息留引用（本报告即按此固化，不内联进 state）。

## 4. Super-agent 概念落点（Aionis 运维/开发层映射）

**结论先行：Aionis 不需要引入任何 super-agent 框架——它的三条核心机制已存在，
整合＝按上述取舍继续加固既有机制，而非新建系统。**

| 文章概念 | Aionis 已有对应物 | 整合动作 |
|---|---|---|
| Router/Worker 双层 | AGENTS.md 单 Orchestrator + on-demand specialists；ZCode workflow runtime（本轮七路子代理并行采集即实例） | 维持边界；Router 不亲自执行 |
| 事件驱动 Trigger/Thread | SessionStart 钩子 + Windows 计划任务 + own-commit CI 自核验 | 新触发器两级过滤原则入册 |
| Watchdog | --doctor 七层预检、23:35 夜报班、data snapshot 绊网、verify_claim | 独立性不合并 |
| Inline/Spill + 链式召回 | state/current.md read-first、handoff/设计报告按需引用 | 报告固化于 reports/design/ 而非内联 state |
| 存算分离/BYOM、投机执行、记忆库（mem0/letta 类） | 仓库+git+ledger 即持久层 | **不采纳**（§3 理由） |

**长周期维护安排**（决策框架第 4 点）：整合不新增稳态 token 消耗——不新建任何
常驻或每晚新班次；节奏复用既有四层：晚间通道（fetch→守卫→门→提交，18:05-23:05
计划任务兜底）、周检（staleness/发布链健康步）、月度（`scripts/monthly_review.py`
复盘）、事件门（12-03 vintage 首跑复验、billing 解锁日操作顺序）。本轮机制类施工
条目的落地记录以 `state/handoff.md` 轮 126+ 为准，其与上表落点一一对应。

## 5. 待业主钥匙区（工程侧无可代办，等待钥匙）

| # | 钥匙 | 现状 | 解锁后动作 |
|---|---|---|---|
| 1 | **GitHub billing 解锁 #2** | 11-05 起账户级计费锁（handoff 轮 118，`18001a804d`）：publish-site 停更 11-02 版、Tests/staleness 秒级红、vintage-probe 无法 dispatch；本地通道与 push（PAT）不受影响 | 按 handoff 轮 125 解锁日操作顺序：核对 staleness 解锁后首个周一误红风险；按 docs/ops-local-refresh.md 恢复 runbook 重跑 vintage-probe（12-03 首跑复验 model=glm-4.7-flash + status=stable） |
| 2 | **publish-site 冻结通道真推许可** | `scripts/ops_freeze_deploy.py`（`5f02da58f8`，6 层预检/数据回退守卫/robocopy 镜像/--dry-run；tests/test_ops_freeze_deploy.py 20 测试）已就绪，dry-run 全过（handoff 轮 120） | 业主点头后执行 `uv run python scripts/ops_freeze_deploy.py` 真推 gh-pages（站点从 11-02 版前移至当前） |
| 3 | **-wj 账本孤儿 2 行裁决** | handoff 轮 120 升级呈报；worktree `F:/ZCodeData/Aionis-wj`（branch `feat/local-refresh-sweep` @ `5475f6d1a2`，本轮 `git worktree list` 实测） | 归并或弃置（**均不可逆**），业主一次裁决 |

## 6. 本轮核验清单（改到哪证到哪）

- 通道状态：`uv run python scripts/ops_local_refresh.py --status` 实跑（§1.1 输出）。
- 三失败晚：`runs/ops_local_refresh/2026-11-03/run.log`（cap 300 seeded + 契约门
  HARD-FAIL 全文）、11-04/05 同门、11-06 SUMMARY ok_committed 全文引用（§1.1/1.2）。
- Actions：`gh run list --workflow=Tests -L 16`、`--workflow=publish-site.yml -L 6`、
  staleness-check `-L 4`；最新红 run `gh api .../jobs` 零步签名（§1.3 表）。
- vintage 修复：`.github/workflows/vintage-probe.yml:70` 文件级复核（§1.3）。
- 轮子许可证：`gh api repos/...` 八仓逐仓实测（§3 两表）。
- 文章：四 URL 中三篇经 r.jina.ai 全文抓取；微信篇两次抓取均被验证拦截页阻断，
  如实标 partial（§2 文章 4）。
- 本报告自身未触研究管线：`git status` 干净树起始，改动仅本报告 +
  `state/handoff.md`（轮 126 指引行）。
