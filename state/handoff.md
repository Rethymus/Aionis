# state/handoff.md — current-pass handoff

> **2026-08-15 业主裁决：发表线整体废除。** 项目不再有发表计划（无 arXiv 上传、无 venue 选择、
> 无投稿）。所有发表工件已按 move-don't-delete 归档至 `archive/`（manuscript/、quarto-site/、
> docs/methods-and-results-draft(-en).md、replication-availability.md、frontier_positioning.md、
> publishable-unit-positioning / power-floor-literature-anchoring 报告）。本文件下方**历史条目**中
> 残留的发表字样仅为当时工作记录，一律不构成现存计划；所有"待业主：arXiv/venue"类待办已随本
> 裁决作废。当前主线：web 终端展示层 + GitHub Pages 实时数据更新；并行：Track A 因子生成器
> （新冻结面）、E3 forward-live（AUD-06 + 业主 GO）、glm-v4 key 有效性确认。

## 2026-08-29 (zzz) 轮㊲：E3 cutoff 阻塞解决——经验探针 v1 实测边界(2023-03, 2024-11];冻结 YAML amendment(业主授权直接决策;单进程)

**编排**：业主授权直接决策 → 按 advisory(report 2026-08-29-e3-cutoff-advisory.md)决策树执行：方案 A(供应商声明)→ **前提不成立**(GLM-4.5 技术报告 arXiv 2508.06471 全文实检,§2.2 Pre-Training Data 无截止日声明,全文无任何数据截止日期)→ 落 **方案 B(经验探针为主)**。

- **探针工具落地**(`scripts/probe_provider_cutoff.py`):双盲日期事件阶梯(5 个 2023-25 公共事件+面板一手 2026 事件+虚假对照测捏造)+ KNOWN/UNKNOWN 分类;Mimosa SSRF 拦截→按其清单加固(https+host 白名单+DNS 解析公网校验+禁重定向+代理 fake-IP 段 198.18.0.0/15 放行);GLM thinking 通道禁用(前 3 问空答案的根因)+429 退避重试。
- **实测结果**(9/9 完成闭环):**模型 KNOWS 2023-03-10(SVB);UNKNOWN 2024-11-06 及以后(选举/DeepSeek/关税);虚假对照零捏造** → 边界 ∈ (2023-03, 2024-11] → 对 E3 前向窗口(2026-08+)**训练数据泄漏结构性排除**。
- **冻结 YAML amendment(conservative 下界 2023-03-10,provenance=empirical-probe-v1,非厂商声明,措辞如实)**:`provider_cutoff_policy.provider_cutoff` 填入+逐条出处注释;探针产物 `runs/provider_cutoff_probe.json` 提交副本入 `reports/evidence/`。
- **shadow 重跑推进**:cutoff 过守卫(新阻塞=Phase4 面板未物化);Phase4 缓存续跑 570/587(tiingo 间歇 429,会话间自愈)——shadow 重跑下轮续。**教训追加**:nohup 后台链在本机病理窗口静默失败(日志空)→ 重型链一律走 TaskOutput 后台+日志文件双确认。
- **验证**：探针 9/9+触发器/清单契约测试 exit 0+ruff 净;临时文件 glm45_tmp/pg.html 清理。**边界**：E3 lane;shadow 零写;headline GO 仍业主门。**待业主(唯一不变)**：headline GO;GLM cutoff 若厂商日后声明,以 vendor 声明覆盖 probe 值(provenance 升级)。

## 2026-08-29 (yyy) 轮㊱：E3 shadow 触发预演 + provider_cutoff 接线（业主授权直接决策；单进程；全套绿）

**编排**：业主授权"结合调研结论直接决策,非必要不再业主决策"→ 主线账实核查 → 决策与执行 → 精确阻塞定位 + 接线。

- **账实更正（重要）**：handoff 历轮"待业主冻结 E3 契约"为**过时记账**——`config/e3_live_contracts.yaml` 早已 **FROZEN（业主 2026-08-03 D2 批准：max_age_sessions=22、authoritative_refresh=null、block_on_unknown=true）**,带冻结标记测试。
- **决策执行（被授权）**：Phase4 预备（phase_b_fetch --display 按预算诚实退出 396 票缓存续跑+materialize）→ **2026-08-31 月末 shadow 触发本地预演**（PHASE_E3_NO_LEDGER=1,零 ledger 写）——**全链路验证成功**:月末检测→FROZEN 契约加载（max_age_sessions=22 生效可见）→ 轮㊟ fail-closed 守卫正确拒绝伪造 cutoff（"Supply the provider's real knowledge cutoff"）→ 零不可逆写。**唯一精确阻塞**:GLM 的真实知识截止值需供应商一手来源查证（docs.z.ai/bigmodel 页均为 JS 壳,静态抓取不可得;本轮配额尽）——**绝不捏造日期**。
- **接线落地**：`e3_forward_trigger.py` 新增 `_load_provider_cutoff()`（从冻结 YAML 可选字段 `provider_cutoff_policy.provider_cutoff` 读取,缺省 None→守卫照常 fire）——剩余阻塞收敛为"**填一个已查证的值**"。14 触发器测试全过。
- **教训**：pytest 管道 tail 吞退出码再犯并漏判（H4 轮同款）——本轮起 pytest 一律重定向后 echo exit。
- **验证**：触发器 14 测试过+全套 pytest exit 0+ruff 净。**边界**：research/E3 lane;shadow 零 ledger 写;headline 非影子点火仍业主门（ADR-010/文件状态块明文）。**待业主（唯一）**：headline GO（影子积满后）;GLM cutoff 值的供应商一手出处若业主可得可加速。

## 2026-08-29 (xx) 轮㊳：例行新鲜度扫荡 + 导出中止缺陷修复（model_card 严格模式误伤日常 lane;全套绿）

**编排**：业主授权继续 → 主线漂移探针(多数 1-2 天,form8k/13G 3d)→ 全套扫荡链(Phase1 十步+Phase2 十步含 form4 重步+衍生+全量导出,单进程串行 ~50min)→ **两闸门发现+修复** → 下游正典重生成+全套验证。

- **扫荡成果**:13D/13G 推进至 08-28(新申报 AH Bio Fund II/AGARWAL AMIT MOHAN 入库)、form4 1,525 笔(+61)、PTR 全量复核一致(2,811/94)、form8k 209/def14a 1,430/form_d 11,163/ipo 1,105、全量导出 55 文件。
- **闸门发现①(model_card 中止 main())**:全量导出在 model_card 处 ValueError 中止(uv_lock 合法漂移 × 严格模式),而 `_safe_export` 只吞 FileNotFoundError——**7251 行之后的全部导出静默跳过**(lineage/knowledge_shelf/data_health/api_catalog 等),契约测试随即拦下 lineage bridges 与新面板的失配(多 7 桥=旧缓存状态残影)。修复:main() 的 model_card 调用改**披露模式**(allow_uv_lock_drift=True,H4 裁决的日常 lane 语义;严格模式保留给独立校验调用),注释记录本次事故;完整重跑导出 55 文件全成功,lineage 新鲜(153 节点/859 边/34 桥)且契约通过。
- **闸门发现②(ledger append-only 重钉)**:抓取器追加 1 行 data_ingest → 摘要 83fa2778→8136b09f;git diff 复核纯追加(+1/0 删改)后按协议重钉测试锚。
- **下游正典重生成**:atlas-claim `51755c92`(metrics latest_month 推进)/dossier `aab73c4a`(data_health/api_catalog/账本行更新)/shelf 重钉。**验证**:契约 13 过 + 全套 pytest **exit 0(无管道)** + ruff 净 + tsc 0 + build 1,503 页(模型清单/谱系/模型卡三新面全在墙)。**工具链注记**:Mimosa 钩子对 gitignored web/out 构建产物的 SSRF 误报转为确定性拦截(build 后哈希变化)——**新收尾定律:build→目视→摘 web/Aionis 链接→删 out→commit**(本轮执行;out 可随时 pnpm build 再生)。
- **内务**：任务书无(本轮无 agent);runs/ledger 纯追加已复核重钉;冻结产物零触碰。**边界**：data/display lane。待业主：E3 契约冻结+GO;下轮候选=谱系 v3/vintage 探针(需门)。


## 2026-08-29 (ww) 轮㊲：建模决策谱系图——显式取代链解析 + 账本序演化的诚实区分（单进程；全套绿）

**编排**：业主授权继续 → 选点=H5 清单的 11 条 config-only 背后的**决策链**(ledger amendment 原文实测锚点:#52 "Supersedes #51 (monthly-A, redundant with Track C)";#53 "n_estimators 500→100 (feasibility ~5min vs ~27min)")→ H6 任务书(`cd54419`)→ 单 agent 交付(`13cb648`)→ cherry-pick+主线重生成+全套验证。

- **H6（`13cb648`,6 文件 +679/−81)**:`export_model_inventory()` 增 `chains` 计算——按 phase 分组账本序,组内非首行须声明指向同组更早行的引用(`Supersedes\s+#(\d+)` IGNORECASE 或顶层 amends 含 `#NN`)→ `explicit-supersede`(理由原文 200ch 摘录)与 `ledger-sequence`(推断性排列,诚实标注)两种 kind;单行组无链;`MODEL_INVENTORY_VERSION` 升 v2。真实面板 chains 恰 2 块:**track_adaptive explicit**(原因原文全上墙:WEEKLY 化因 monthly-A 与 Track C 冗余;n_estimators 500→100 因可行性 ~5min vs ~27min)+ **track_c ledger-sequence**(双区域→拆分→确认 GO,#48 resulted=true);track_b 臂变体/baselines 诚实不出现。渲染:链式行 `#46 → #47 → #48`+kind 徽章(sky=显式/amber=推断警示)+reason blockquote 挂被取代行下;`inventory.genealogy.*` 6 键对称;契约测试 31 个(新增 4 chains)零 skip;双跑 sha `87c19c3a…` 一致。
- **集成口径**:wh6 无 runs/(任务书误判纯 ledger 即可)→ 其重生成 JSON 的 local-dir 字段诚实转 null → **主线重生成即恢复对账**(B/C/D/E1 true),14 测试过;agent 全套失败经 stash 对照确认为 wh6 环境性(dossier 缺 runs 哈希),非引入。
- **验证**：主线全套 pytest **exit 0(无管道)**+ruff 净+tsc 0+build 1,503 页+目视终验(谱系节:#52/#53 reason 原文"redundant with Track C"/"n_estimators 500→100"上墙)。**内务**：wh6 清(真 node_modules 验证后随树删)、分支 cherry 全 `-` 删、任务书归档。**边界**：display/export 派生;runs/ 只读。待业主：E3 契约冻结+GO;谱系 v3(链上挂 diff 数字与档案互链)与 vintage 探针。


## 2026-08-29 (vv) 轮㊙：SR 11-7 模型清单全集——ledger×冻结目录对账 + /model-health 清单表（单进程；全套绿）

**编排**：业主授权继续 → 选点=模型卡设计的 SR 11-7 延伸("文档"已有,补"**清单**")→ 主线先核实映射(4 目录恰为 B/C/D/E1 confirmatory;11 条 config-only 无目录)→ H5 任务书(`15ad203`)→ 单 agent 交付(`5db5918`)→ cherry-pick+正典重生成+全套验证。

- **H5（`5db5918`,9 文件 +1310）**:`export_model_inventory()`——扫描 tracked ledger:**5 条 confirmatory:first**(B 27/28、C 29/30、D 33/34、E1 35/37、track_c 48/49)+ **11 条 config_only 诚实列示**(track_b×3/baselines×3/track_c 被取代×2/track_adaptive×3);local_dir_present 恰 4 true(track_c 无本地目录→h6/version/diff 全 null);diff 字段自各目录 differential.json 重读(B −0.0008 [−0.0106,+0.0090] p=0.870 / C −0.0065 p=0.355 / D −0.0030 p=0.597 / E1 −0.0028 p=0.533——**四相 h=21 冻结差分全 CI 跨零**);differential.json 实无 null_holds 键 → summary.all_null_holds 如实 null。四注册点+barrel+dict 18 键+/model-health 清单节(确认 run 表+config-only 折叠+空态表头)+H2 EXPECTED_PANELS 同步+1;9 契约测试零 skip;双跑 sha `96243fdf…` 一致。
- **正典下游重生成**:H5 改 data_health/api_catalog → dossier 重生成(`b0825c19`)/shelf 重钉——闭包闭环照常工作。
- **验证**：主线全套 pytest **exit 0(无管道确证)**+ruff 净+tsc 0+build 1,503 页+目视终验(模型清单节:phase/sig/freeze 行号/config-only 折叠全在墙)。**内务**：wh5 双 junction 先摘(runs+node_modules)、分支 cherry 全 `-` 删、任务书归档。**边界**：display/export 派生;runs/ 只读。待业主：E3 契约冻结+GO;模型卡 v2 深化(被取代配置的谱系图)与 vintage 探针。


## 2026-08-29 (tt) 轮㊟：可追溯金融建模落地——model_card 机器可读卡片(文献印证;单进程;全套绿)

**编排**：业主命题"实现真正可追溯可溯源的金融建模,调研大量资料印证而非凭空想象"→ 主线 arXiv API 实检三面(**Model Cards** 2018 Mitchell/32K 卡系统分析 2024/OWFM 治理 2026;**Datasheets** 2018 Gebru;**NeurIPS 复现程序** 2020 Pineau;**AI-BOM 完整性测量** 2026/LLM 血统追踪 2026/FAIR-HEP 2022)+B 级领域知识(SR 11-7/FAIR 2016/Tactical Investment Algorithms 2019,分级声明)→ 冻结产物实测(config.json 全字段恰为卡片所需)→ 设计文档+H4 任务书(`f8ceff7`)→ 单 agent 垂直切片。

- **H4（`945f458`→`0b44b70`,9 文件 +1734）**:`export_model_card()` 七节机器可读卡(identity/intended_use/data/model/evaluation_protocol/results/governance/provenance)——全部机器读自工件零手写:冻结 config.json(9 特征列/horizon=21/n_splits=5/embargo=21/PurgedGroupKFold scheme/frozen_params 全超参含 seeds 全 0+n_jobs=1/end_lag/versions lightgbm 4.7.0+purgedcv 0.1.2+arch 8.0.0/输入 sha×4+uv_lock)+meta.json(config_sig/h6=true/aionis_version)+ledger freeze→result 行(行号+行 sha)+metrics 实值逐字(results 节)+预注册文档 sha;uv_lock 双 sha+match 标志;四注册点+barrel+dict `modelcard.*`+/model-health 新节(空态表头仍渲染);11 契约测试零 skip;双跑 sha 一致 `78f9563a…`。
- **两处裁决(主线采信,均有实测证据)**:① 任务书写 track_c,但 **track_c 结果行 #49 无本地 runs/results 目录**;设计稿实测的 schema 唯一匹配 Phase B run(17245a75,ledger #27→#28)→ 实现为 **ledger confirmatory 行时间序扫描、首个可本地解析者**(零目录名硬编码),results 节仍逐字嵌 track_c 头条+trace 标签。② **uv_lock 合法漂移**(冻结 e045a023→当前 5c5cff1c,08-11 blob)→ 默认严格 raise(测试钉死)+ `allow_uv_lock_drift=True` 显式披露路径,卡片双 sha+match=false 上墙。**主线验证时严格路径当场 raise=自校验按设计工作**;已提交面板为披露模式产物(正确状态)。
- **教训(工具链)**:`pytest | tail` 管道吞真实退出码——本轮由此漏判一次失败;改用无管道重跑确证。下游工件因 H4 面板变更按正典重生成(atlas 不变 dc2101e6/dossier `0e2e9232`/shelf 重钉)。
- **验证**：主线全套 pytest exit 0(无管道确证)+ ruff 净 + tsc/eslint 0 + build 1,503 页 + 目视终验(/model-health 模型卡节:模型卡/17245a75/lightgbm 4.7.0/e14b9d44/NULL/PurgedGroupKFold/uv_lock 全在墙,h1=1,零垃圾)。**内务**：wh4 清(runs junction 先摘+真 node_modules 随树删)、主仓冻结产物完好(4 目录/内容未动)、分支 cherry 全 `-` 删、任务书归档。**边界**：display/export 派生;runs/ 只读;冻结产物零触碰。文献证据:`reports/design/2026-08-29-model-card-design.md`(A/B 分级)。待业主：E3 契约冻结+GO;模型卡 v2(多 run 清单化=SR 11-7 inventory 全集)。


## 2026-08-29 (uu) 轮㉞：证据工件上架 /shelf + 循环哈希依赖打破（单进程；全套绿）

**编排**：业主确认超长期任务+单进程纪律 → 选点=溯源链最后一公里(两证据工件终端不可发现)→ H3 任务书(`2ad5a5d`)→ 单 agent 交付(`a71e1e3`→cherry)→ **集成接缝两连修(主线正典)**。

- **H3（shelf 工件上架,`a71e1e3`）**：`_KS_EVIDENCE_ARTIFACTS` 固定字面量层+导出时现算 sha/字节 → `knowledge_shelf.json` 第三层 → /shelf 新"证据工件"卡(双语名/描述/sha 前 12 位 mono/字节/GitHub link-out)+dict 3 键+契约测试(恰 2 条/sha 与仓内重算一致/零外部资源)。偏离如实:wh3 无 junction,pnpm --offline 零网络装机。
- **接缝修①(检出环境漂移)**：H3 在 wh3 检出(CRLF)上算 sha → dossier 条目钉了 `fc7b53ff`/47,057(CRLF 膨胀),而 git blob/GitHub raw 是 LF `f1db9600`/46,768——**目录 sha 随检出环境漂移=校验闭环失效**。主线修:导出器与测试双侧改 **LF 规范化**(=git blob 形态),docstring 记录实测案例。
- **接缝修②(循环哈希依赖,架构级)**：dossier 内嵌 knowledge_shelf 内容 sha,而 shelf(H3 后)内嵌 dossier sha → **互嵌无收敛点**。主线正典解法=**单一事实来源**:书签字面量抽至 `scripts/ks_sources.py`(stdlib-only),exporter 与 dossier 各自导入;dossier 从 PANEL_FILES 移除 knowledge_shelf(不再哈希生成物);渲染节每书签改自身 [S#] 引用。**闭包硬门当场拦截我新写行的未引用数字("共 8 条")**——修正措辞后过。测试对账:sources 18→23(组成注释更新)、defang 断言改真实书签 scheme-stripped+fixture shelf 不泄漏、降级测试改 calibration 载荷。
- **重生成次序定律确立**：工件先行→目录次之(shelf 哈希工件);同轮上游面板变更则全部下游重生成。终值:atlas-claim `dc2101e6`/24,240、dossier `01bcbe36`/46,549、shelf 目录双侧吻合。
- **验证**：主线全套 pytest exit 0 + ruff 净 + tsc/eslint 0 + build 1,503 页 + 目视终验(/shelf 证据工件层双语渲染、双 sha/字节在墙)。**内务**：wh3 清(真 node_modules 目录,验证非 junction 后整体删除)、分支 cherry 全 `-` 删、任务书归档。**边界**：display/export lane;零网络(pnpm --offline 先例)。待业主：E3 契约冻结+GO;档案 v1 扩展与 vintage 探针(下一轮单进程候选)。


## 2026-08-29 (ss) 轮㉝：超长期任务开局——数据补漏扫荡 + 全站审计 r3 全 PASS（单进程纪律；全套绿）

**编排**：业主定帧"超长期查漏补缺+视觉持续优化;**agent 派发改单进程串行**(速率限制,质量优先)"→ 主线新鲜度探针 → 定向补漏抓取(runbook=轮㉑ TASK-DISP-R 实测协议) → 全量导出 → 单 agent 全站审计。

- **新鲜度探针**(53 面板逐一 as_of 实测):28 ok / 23 "stale" 中甄别——frozen 设计使然 10(metrics/picks 族/evidence/bps_sweep/calibration/model_health/score_diagnostics 等)+源节奏诚实 5(13F 季节奏/cot 周更/korea 源停)→ **真正可补 8**:politician_trades(08-18)/party_index/executives/filers13f/def14a_persons(08-21)/picks_backtest/sector_breakdown/stock_universe(08-20)。
- **定向补漏**(单进程串行,礼貌间隔):politician_trades 874 份(无新增=源节奏)、**PTR tx 全量 359/359→2,811 笔/94 人**(parse 54 失败+33 exchange 诚实计数)、form13f_dir 重开窗 9,385 filers(latest 08-21);全量导出 53 文件(衍生面板重算;stock_universe 走 retain 守卫=设计;executives 停 08-21=8-K 缓存内无新 5.02,诚实)→ 契约测试全过 → commit `0633dab`。
- **AUD-08 全站审计 r3**(单 agent 零修复,`55c758b`→`d2b460e`):**8/8 项 PASS,P0/P1/P2 全零,P3×3**(index redirect 桩=轮㉑已裁决非缺陷;i18n 空串=设计模式;ipo last_walk=0=守望)。通过:可见垃圾 0/死内链 0(42,958 内链)/ticker 宇宙门 1,407 链接零回归(DEV-K)/h1 1,502 页恰一/五项结构全零/i18n 1,162 对称/as_of 抽样 8/8。**数据-呈现调和 4/4 复算全过**(horizon 卡 24 数逐字/稳定条 Δ 9 值精确复现含 null 诚实口径/语境行 t 反推成立/data_health 51 行三分区对账)。轮㉒ P3-1 修复确认在位。
- **内务**：wa1 清(无 junction)、分支 cherry 全 `-` 删、任务书归档(注:AUD-08 任务书未预提交,agent 从主仓未跟踪路径读取——如实披露)。**边界**：data/display/audit lane;runs/ledger 零触碰;0 frozen/config/prereg/OOS。**单进程纪律生效**:本轮全程串行(抓取链→导出→审计),无并发 agent。待业主：E3 契约冻结+GO;下轮候选=P3 处置与档案 v1 扩展。


## 2026-08-28 (rr) 轮㉜：溯源研究档案管线——来源研究→报告生成→建模分析全流程贯通（[S#] 引用闭包硬门；三 agent 并行+集成对账，全套绿）

**编排**：业主新命题"实现覆盖基于来源的金融研究、报告生成到金融建模与分析的完整流程,全程可追溯可溯源"→ 主线设计三阶段架构写入任务书 → 三 dev agent 并行（wh1/wh2/wk1;D 首派死于并发限额,续派成功）→ cherry-pick + 集成接缝对账。

- **D（档案管线,`efa9d29`→`7fdfcbf`）**：`scripts/export_research_dossier.py` + `reports/evidence/research-dossier-v1.html`(46.7KB,字节稳定双跑 sha 一致)。**S-registry 24 条来源**(panel×9 内容 sha256 现算 / ledger×2 行号+行 sha[horizon sweep line39 + config_committed line48] / doc×3 预注册+intake-rubric sha / artifact×1 / external×9 如实 self-declared),正文引用 141 处;**闭包硬门**=孤儿引用/未引用来源/含数字无引用行三类违反 raise(开发中真实拦截 2 处);七章节全 committed 实值(头条卡/设计门禁/50 端点×license 分组/冻结链 row48→row49→snapshot+森林图+IC 条形+校准+score 诊断+horizon 稳健性/evidence 表+HLZ 语境+8 书签/局限/自检);16 契约测试零 skip。
- **H1（horizon 面板,`d1bd888`→`9897d90`）**：`export_horizon_robustness()` 读 tracked ledger latest 行(ts 2026-07-30,a2 版含 E1)→ 面板+四注册点+barrel 显式类型+dict 12 键+**/track calibration tab 尾部 HorizonRobustnessCard**(四相×h10/h42 diff+CI+DM p,emerald verdict 徽章,EXPLORATORY note);**四相 8 格全 null 保持**(B/C/D/E1 CI 全跨零)——冻结零结果对 horizon 不敏感的实证上墙。
- **H2（覆盖契约,`e9b6df8`→`7cd787b`）**：`tests/test_data_health_coverage_contract.py` 7 测试——50 key(barrel 44+模块 6)↔manifest 双向精确闭合+反幽灵行+barrel 运行时解析护栏+atlas 六面板 dated 专项;**KNOWN-GAP 1 项按 protocol 写死实况**:calibration_reliability as_of=None(可标注而未标注)。
- **集成接缝(主线正典处置)**：① H1 给 manifest 加第 51 行 ↔ H2 硬编码表按 50 行基线写 → 按"合同与测试同步改"把 horizon_robustness 行补进 EXPECTED_PANELS(51 行);② **KNOWN-GAP 主线直修**:`_dh_as_of` 补 calibration_reliability 分支(as_of=各 region series 末月 max=2026-06)+翻转断言为严格;③ **闭包硬门当场生效**:data_health 重导出后 sha 变化 → D 档案完整性失配被测试拦下 → 重生成档案(51 面板 17/25/9 新计数,双跑 sha `f1db9600…` 一致)——溯源体系自我修正闭环实证。
- **验证**：三 worktree 各自全净(H1 全套 exit 0/2123+;H2 93 passed/全仓 2156 exit 0;D 25 passed)+ 主线全套 pytest exit 0 + ruff 全净 + tsc/eslint 0 + build 1,503 页 + 目视终验(track 卡片 Horizon 稳健性/arm_state/arm_prop/null 保持 全在墙)。**内务**：wh1-2/wk1 清(wh1 junction 先摘)、三分支 cherry 全 `-` 删、三任务书归档。**边界**：display/export 派生 lane;runs/ 只读;冻结产物零触碰。待业主：E3 契约冻结+GO;档案 v1 扩展(多 claim/版本化/CI 挂钩)与 LLM vintage 探针(R1-2)。


## 2026-08-28 (qq) 轮㉚：P0-3②+P3-2 lite+P2-1 lite 执行轮——atlas 文献语境线/样本期稳定条 + 自包含证据工件 + CSI300 半开语义落盘（全套绿）

**编排**：业主授权"继续最优处理，部署仍冻结"→ 主线快探（CSI300 抓取器=本地嵌入包非网络；中途遇本机 0xC0並0142 坏窗口，按轮㉑预案 Write 工具先行+shell 恢复后重试）→ 两份任务书（`0318212`）→ 两 dev agent 分 lane 并行（wg1 junction/wg2）→ cherry-pick+全套验证。

- **G1（web lane，`2e6af47`→`6236c12`）**：① 森林图"文献语境"行——从 metrics 推导 t 值（se≈(ci_hi−ci_lo)/3.92=0.0126 → **t≈−0.70**），并列 Harvey-Liu-Zhu (2016 RFS) t>3.0 阈值；纯语境并列，明示"展示性推导、非模型输出、NULL 不因对照改变"；无 CI 诚实不渲染。② IC 样本期稳定性描述条——前/后半分样本（33/33，规则写死）：US −0.0157→+0.0267（Δ+0.0424）、CN −0.0584→+0.0054（Δ+0.0638）、合并 −0.0347→+0.0218（Δ+0.0565）；注明"描述性,非检验"，半样本<12 月不渲染，null 月份不计入并在注脚披露。7 个新 i18n 键对称。
- **G2（scripts lane，`edf2cca`→`f1d7b4d`）**：**R2-lite 自包含证据工件** `reports/evidence/atlas-claim-v1.html`（24KB,零 JS/零外部资源/零字体,浏览器直开）——七区块（主张/头条读数卡/SVG 森林图含 evidence 10 条有 CI 记录/66 月 IC 条形/逐月表/方法学含 E3 现状如实/溯源链 freeze48→result49）；**字节稳定契约**（零时钟、排序写死、双算 sha 一致 `c44cba3e…`、测试钉"与当前面板新鲜渲染逐字节相等"）+ 11 契约测试零 skip；数字全部 metrics 实值逐字嵌入（IC=-0.0088/CI/p=0.484/n=71/NULL/SESOI±0.01/config e14b9d44）。external verifiability 的文献支撑=OpenPM 可审计评估+TS-Arena 预注册工件。
- **主线**：CSI300 成员缓存 force 重拉成功（本地嵌入包 `--with index-constitution`,零网络）——**max date=2026-08-27=今日−1,半开语义落盘实锤**（2,349,460 行/949 票）；CN 面板本身未重建（研究输入变更留待有意的专项运行）。
- **验证**：两 worktree 内 tsc/eslint/pytest 全净（G2:95 passed,11 新测试）；主线 cherry-pick 零冲突 + 全套 pytest exit 0 + build 1,503 页 + 目视终验（Harvey 语境行 t≈-0.70 在墙、稳定条 Δ+0.0638 在墙、h1=1/h2=2、零渲染垃圾）。**内务**：wg1-2 清（junction 先摘）、g1/g2 分支 cherry 全 `-` 删、任务书归档。**边界**：display/scripts lane;冻结产物零触碰;未 push（随本 state 提交一并推）。待业主：E3 契约冻结+GO;CN 面板重建专项时机;R2-full（多工件/格式矩阵）。


## 2026-08-28 (pp) 轮㉙：P0-2 执行轮——code-review P1 逐条核实 + 三 agent 分 lane 修复 7 条（E3 硬前置清障）

**编排**：业主授权"继续根据调研结论最优处理，部署仍冻结"→ 主线**先核查再派工**（15 条 P1 逐条对照当前 HEAD：P1-3/P1-10 已被后续修复；P1-5/P1-12 archived-lane/疑被 _safe_export 守卫取代不派；**7 条确认存活**；3 条标注需 agent 追踪裁定）→ 三份任务书（`0c3f58d`）→ 三 dev agent 分 lane 并行（wf1/wf2/wf3）→ 主线 cherry-pick+全套验证。

- **F1（eval/forward lane，`deb0b6e`→`f175357`）全胜 3 条**：① P1-1 haircut 下溢——实测 `sf(38)=0.0` 下溢 → `ppf(0)=+inf` 且 survives=true；修为 `p_raw==0` 时返回 `haircut_sharpe=None`+`p_raw_underflow=True`（诚实呈现绝不 ±Infinity），phase_c/phase_b 的 haircut_table 透传 None 防中途崩溃，饱和分支语义测试钉住。② **P1-2 判非误报**：VIX surprise 实际输入链追踪到 `data/cache/alfred_VIXCLS.json`（`vix_cls.parquet` 只被检查路径读写）→ 新增 `vix_vintages_sha256` 钉真实输入，只增不删；**诚实后果=未来 Phase C run 的 config sig 改变（按 ledger 契约是新 ledger 行非静默变更，冻结产物零触碰）**。③ P1-4 判外层未强制：`_check_provider_cutoff` 只认字面量 "unknown"，`provider_cutoff_faked` 从未 raise，且 **e3_forward_trigger 真实 live 路径正在踩此洞**（enforce=True+policy+None cutoff）→ `main()` 在 freeze/ledger 写/LLM 调用前 fail-closed ValueError；legacy 无 policy 路径保留回退（复现模式不受影响）。
- **F2（ingest/data lane，前任死于提供商限流留下半成品，续作 agent 逐行审查后保留+修正 3 处+补齐文档，`28b1b11`→`f498ff4`）**：① P1-8 闭区间→半开 [opt_in, opt_out)——**决定性证据=仓内 intake 契约文档早已钉死半开语义（`opt-in <= date < opt_out`），代码是对自身契约的偏离**；消费方核查零依赖旧语义。② P1-9 判非误报：949 历史成员 ever-member 池全历史拉价、下游（track_c_a/joint/confirmatory/export）确无任何成员过滤 → builder 源头加 (date,ticker) 级 PIT 过滤+fail-closed；诚实残余=现存成员缓存 parquet 仍是旧闭区间产物需 force 重拉（真实抓取超范围），面板有效终点被成员快照日封顶（已 docstring 钉明）。
- **F3（features/scripts/tests lane，`930b098`→`3e7c096`）全胜 3 条**：① **P1-6（最重，反泄漏核心）**——"PIT 过滤"实为恒真式（`filed_date <= ticker全局max` 对每行恒真）+ 断言被自己的列排除短路成死代码 → 真 PIT（merge_asof backward by ticker，stable sort H6 级确定）+ 断言合并前复活 + NaT 豁免；**影响面核实：唯一生产调用点以 fundamentals=None 调用，行为修复不触及任何既有研究产物路径**。② P1-7 track_b 运行时 config_sha256（特征集+面板字节）写输出。③ P1-11 9 个 skip 全部替换 hermetic 真断言（预写 alfred 缓存+sleep 补丁，零网络）——目标文件 skip 9→0。
- **验证**：各 agent worktree 全套 pytest exit 0（F1 2103 passed / F2 exit0+2115 collected / F3 2123 passed、skip 净 -9）+ ruff 全净；主线 cherry-pick 零冲突 + 全套 pytest + ruff 全净。**内务**：wf1-3 清（无 junction）、f1-f3 分支 cherry 全 `-` 删、三任务书归档。**裁定总结**：15 条 P1 → 修复 7（F1×3+F2×2+F3×3 中 P1-6/7/8/9/11 + P1-1 + P1-2）+ P1-4 fail-closed 加固 = **8 条处理**；已修 2、archived-lane 不派 2、误报 0。**边界**：研究/eval/ingest 代码修复 lane；冻结产物零触碰；未来 run 的 config sig 变化已按契约声明；未 push（等全套绿后随 state 一起推）。待业主：E3 契约冻结+GO（P0-1 剩余全部是业主门）；成员缓存 force 重拉时机。


## 2026-08-28 (oo) 轮㉘：远程同步 + AI harness/金融计量深度调研 + 未来方向优先级路线图

**编排**：业主指令①未提交部分原子 commit 同步远程 ②网络深调经济学/金融学 × AI harness 概念 ③未实施项优先级细致排列。

- **远程同步**：唯一未提交项=并发 session 的 `docs/code-review/` 全历史审查工作库（286/439 commits 已审；有效发现 P0=0/P1=15/P2=109/P3=323，均分 8.28/10）→ 原子 commit `8187c0b` 前身 + **push 成功 `5475f6d..8187c0b main->main`，本地与 origin 完全同步（0 领先）**——08-22 以来的 44 commit（含轮㉖/㉗全部 display 交付）首次上远程。
- **调研通道（诚实披露）**：WebSearch 后端周配额尽（09-03 重置）→ **arXiv API 一手检索三路**（LLM alpha mining / agent harness / LLM 收益预测，20 篇 2024-2026 文献）+ 计量金融领域知识。三线结论：① LLM 因子挖掘闭环自动化成主流（AlphaSchema/CogAlpha/TreEvo/AlphaEval/AlphaAgent 等）但**评估纪律缺位**（回测内优化=overfitting 工厂；例外可移植：AlphaEval 五维免回测、AlphaAgent 抗 decay 三件套）；② 2026 harness 科学显式化"**external verifiability**"为稀缺分化轴——Aionis 的 ledger/sha256/commit-then-reveal 已站在该轴上，应显式化输出；③ **DatedGPT 实测 lookahead premium 26.4bp/σ** = Aionis 反泄漏立场的外部定量佐证；factor zoo 复制危机（HLY t>3.0/HXZ 65% 失败/McLean-Pontiff 衰减）是本项目存在理由的文献注脚。
- **交付**：`reports/design/2026-08-28-future-roadmap-research.md` —— P0（E3 forward-live 发射准备=业主命题正统锚定 Slice1-7 已毕仅差契约冻结+GO / code-review 15 条 P1 修复其中 forward 线三条为 E3 硬前置 / 传播层收尾 h10-h42+haircut 语境线）/ P1（Track A 因子生成器=RD 系列任务单即地基+AlphaAgent 三件套 Aionis 化 / LLM vintage 纪律=provider cutoff 入 ledger+探针检验 / R1-full）/ P2（R2 图表工件、CI 恢复迁移+cron 修正、评估层小升级、旧豁免升级）/ P3（harness 自指演进、decay 监测面板、earnings 臂）。排列原则=证据强度>反泄漏纯度>门状态；"若只做三件事"已写明。0 代码改动。
- **深挖互证（业主"要更多真实研究互相印证"指令的第二轮）**：WebFetch 工具配额亦尽 → **curl 直连 arXiv API（HTTPS+UA+限速，12 次实检索）再获 22 篇**，`reports/design/2026-08-28-evidence-corroboration.md` 把路线图主张逐条对账到 ≥3 独立研究：① look-ahead=LLM 金融评估第一问题（DatedGPT 26.4bp/σ、**Look-Ahead-Freedom as Temporal Non-Interference=可验证正确性属性**、Look-Ahead-Bench、OpenPM 可审计 PIT、From Knowing to Doing、Can LLMs Be Constrained to the Past——6 篇独立）；② 静态回测不可信/活体协议唯一强证据（**TS-Arena 活体预注册平台=与 E3 跨域同构**、LiveHouse-TS live 协议下排名剧烈洗牌、CLQT 表观 alpha 溶解、Fin-Analyst 缺 live 证据）；③ 校准>点命中（FinBench confidence-competence gap 时间门控）；④ 试验次数须入账（MinervaScore"不记录试过多少候选"+本仓 multiple_testing P1 内部实证）；⑤ alpha 衰减有函数形式（**Not All Factors Crowd Equally 双曲律 α(t)=K/(1+λt)**，8 FF 因子 1963-2024；Financial Epiplexity=有界计算可学习性理论）；⑥ LLM 研究产物需 PIT 溯源（Trust-Tiered Librarian）；⑦ 智能成本 vs 交易价值（Agentic Viability）。**证据分级 A（API 实检 22 篇）/B（领域知识 HLY/HXZ/McLean-Pontiff 待 OpenAlex 配额恢复核验）如实声明**。定位增补：各设计要素已有孤立镜像但无单框架集成——空位真实且有时间窗。路线图 §1 已挂接证据文档。

## 2026-08-28 (nn) 轮㉗：调研结论最优处理轮——/atlas h1 修复 + R1-lite 分数面诊断透视图上线（单 agent 垂直切片，1,503 页全套绿）

**编排**：业主授权"继续根据调研结论最优处理，部署仍冻结"→ 主线快探（/atlas 零 h1 坐实=轮㉕标准 P1 回归；R1 可行性核查：decile 收益单调性需全样本前向收益=展示层重算收益有口径漂移风险→**业主门**；改 R1-lite=纯分数面派生）→ 主线直修+任务书（`156ec72`）→ **单 dev agent 全栈垂直切片**（wr1，真实 parquet 拷入 worktree）→ 主线 cherry-pick+确定性复核+全套验证。

- **主线直修**：/atlas 页壳翻 client（shelf 先例）+ sr-only h1（`nav.atlas` 既有键）——轮㉕"每页恰一 h1"标准在新页回归的修复。
- **R1 决策入档**（设计规格 §6 改写）：R1-full（decile 收益单调性，金标准）需要 94,438 行 × 价格 join,与冻结 run 收益口径（next-open vs close）不对齐则"分差"成口径伪影→不擅启,业主门；**R1-lite 落地**=`score_diagnostics.json`（月×区域 → n/score_mean/std/IQR/月度秩自相关,重叠<30 诚实 null）,纯读冻结 `track_c_confirmatory_oos_scores.parquet`,零收益口径风险。
- **R1 agent 交付**（`993d9d7`→cherry `8085d1a`,10 文件 +2280）：export_quarto_data 新函数（export_ic_monthly 同区同风格,round 6 字节稳定）+ export_terminal_data 四注册点（_safe_export/data_health frozen 行/as_of 分支/api_catalog source）+ 10 个 hermetic 契约测试（合成 parquet 夹具+numpy/scipy-free 双算交叉验证钉死精确值,零 skip）+ barrel 显式类型 ScoreDiagnosticsRow + dict 9 组键 + atlas-diagnostics.tsx 三面板（离散度带/宇宙宽度条/惯性折线,CardTitle as="h2",表格回退全渲染）+ page.tsx 插入第四区块。**agent 合理自裁三件**（主线采信）：再生 data_health/api_catalog（注册一致性,n_panels 49→50）、退化截面 NaN 守卫（allow_nan=False 下防崩）、atlas.intro/nav.sub.atlas 文案三→四区块同步。**数据事实勘误**：US 19 个月含错峰打分日,已验证 (month,region,ticker) 全局唯一,按月分组语义无损。
- **实测数字上墙**：134 (month,region) 组/68 月（2021-01→2026-08,CN 68 月 n=929、US 66 月 n≈446-492）;rank_autocorr 132 非空,范围 0.194→0.939（null 恰两区域首月）;离散度最大月 2021-11 US（std 1.0015）、IQR 最大 2025-02 US。
- **验证**：worktree 内 96 passed（10 新+86 契约）+ ruff 净 + tsc/eslint 0;主线 cherry-pick 后**主仓 parquet 重导出 score_diagnostics.json 逐字节一致**（确定性证明）+ 全套 pytest exit 0 + tsc/eslint 0 + build 1,503 页 + 目视终验（h1=1、h2×2、53 SVG/10 表、0.938698/1.001488 在墙）。**内务**：wr1 清（junction 先摘）、agent/r1 cherry 全 `-` 删、任务书归档。**边界**：display/export 派生 lane;只读冻结产物;0 ledger/frozen 写/config/prereg/OOS 计算;未 push。待业主：H1 部署门不变;R1-full（decile 收益）业主门;R2/R3 待后裁。

## 2026-08-28 (mm) 轮㉖：编辑级图表语言 /atlas 研究图谱上线（diagram-design 文章移植；1,503 页，全套验证绿）

**编排**：业主 /goal（研读 diagram-design 文章→结合金融学+数据透视/BI 视角→多样化呈现→设计/开发分离多 agent）→ 主线调研+设计+基础设施 → 三 dev agent 分仓并行（worktree wd1/wd2/wd3）→ 主线 cherry-pick 集成+全套验证+收口。部署冻结不触碰；0 ledger/frozen/config/prereg/OOS。

- **文章研读**（mp.weixin.qq.com/s/JJKkzrrf9Rmr62YMkchykQ，curl+UA 破验证页直抓 3.3MB HTML）：文章**不是金融文**，介绍 `diagram-design` Agent Skill——39 种编辑级图表、自包含零 JS SVG/HTML、品牌风格适配（配色/字体提取+WCAG 核验）、Mermaid/Draw.io 重绘。移植判断：**零 JS 确定性 SVG ≈ H6 确定性哲学**、品牌适配 ≈ 既有 Apple token 体系；涨跌语义色红线不进研究图（蓝↔橙发散色标，色盲安全）。规格：`reports/design/2026-08-28-editorial-diagram-language.md`（含 39 型→Aionis 相关性筛选、R1 BI 透视/R2 独立图表工件/R3 品牌适配器前瞻路线）。
- **真实数据核查先行**（可行性证据，全在已提交面板、零新抓取）：metrics（combined_ic=-0.0088/CI[-0.0336,0.0159]/sesoi=0.01/verdict NULL）、ic_monthly 66 月×US/CN/合并、calibration_reliability regions.us 53 月+cn 54 月（prob_min/prob_max/base_rate/ece_oos）、data_health 49 面板（25 daily/9 cadence/15 frozen）、api_catalog 49 端点 source/license。
- **基础设施主线先建**（`685fab8`）：`components/diagram/tokens.ts`（CSS 变量语义角色+9 档 oklch 蓝橙发散色标+divergingColor）+ `primitives.tsx`（scaleLinear/niceTicks/DiagramFigure a11y 包装）+ **dict.ts 全量 35 组键 zh/en 预置**（消除三分支同锚冲突面）+ top-nav 校验组第 4 项+cmdk 接线 + 三份自包含任务书 `tasks/active/TASK-DISP-D{1,2,3}-atlas-*.md`。
- **三 agent 分仓全胜**（各只新增一个文件、零共享文件触碰、tsc/eslint 双零、原子提交）：
  - **D1**（`3121b26`，atlas-claims.tsx 515 行）：66 月 IC 热力透视（2 栏×33 行、9 档色带、格子文字亮度确定性映射）+ 结论森林图（CI 条+SESOI 等价域带+零线+判定行）。诚实发现：ic_monthly 有 `2026-06 us:null`，按缺失渲染。
  - **D2**（`6096e99`，atlas-divergence.tsx 559 行）：预测概率带 vs 实现基准率 US/CN 双面板+带内覆盖率+月度 ECE 条+pooled_ece 参考线。**实测覆盖率 US 7/53=13%、CN 7/54=13%**（诚实数字上墙；任务书"各 53 月"偏差=CN 实为 54，按真实数据渲染）。
  - **D3**（`ea49f2b`，atlas-dataflow.tsx 510 行）：来源族→类别→新鲜度三层桑基式流图（节点高=面板数、确定性关键词归组 Σ=49、join 率 49/49、as_of 字符串比较禁 Date）。归组表：Aionis derived/frozen 22、EDGAR/SEC 13、Other 4、FRED 3、Congress 2、Reddit 2、GDELT/CFTC/ARK 各 1；派生族关键词前置防 lineage_graph 误归 EDGAR。
- **架构事实修正**：任务书初稿写"服务端组件"，主线核查发现 i18n provider 是客户端方案、全部既有视图均 "use client"+SSG 预渲染 → 三任务书统一改为仓库既定模式（确定性不变：布局坐标构建期算死、零 Date/random、SSG 字节确定）；零客户端 JS 纯服务端 SVG 记为 R 系列演进项。
- **路由组合**（`fded756`）：`app/(dashboard)/atlas/page.tsx` 服务端壳（SegmentHeader segment=validity + countHint 从 dataHealth.summary 组合：49 panels · 25/9/15）+ 三区块依序。插曲：首推导入写成具名（agents 均默认导出），tsc 即时抓正。
- **验证**：tsc 0 + eslint 0（本轮全部新文件）+ 全套 pytest **exit 0** + build **1,503 页**（+1 = /atlas）+ 产物目视终验（44 SVG/7 回退表；真实数字全在墙：0.0088/0.0336/0.0159/SESOI/7/53/7/54/13%；zh 渲染正常；`undefined`×48 经甄别=Next RSC payload `"$undefined"` 内部标记，与 track.html 51 处同类，**非渲染垃圾**）。
- **Mimosa 钩子插曲**：page.tsx 提交首次被拦（9"高危 SSRF"全位于 gitignored `web/out/_next/static/chunks/*.js` 第三方压缩 bundle——客户端静态 chunk 的 fetch 模式不构成 SSRF，本项目无 MongoDB；staged 面仅 page.tsx 一个文件）→ 复核后重试提交通过。
- **内务**：wd1/wd2/wd3 清（junction 先摘铁律执行）、agent/d1-d3 分支 `git cherry` 全 `-` 后 -D；三任务书归档 completed/。**边界**：display lane；未 push。待业主：H1 部署门不变；R1（BI 透视 decile 维度）/R2（独立图表工件）/R3（品牌适配器）待后裁。

## 2026-08-28 (ll) 轮⑤：13D 检查点可续跑化（实战验证）+ 全站 a11y 首轮审计 + 标题语义修复

**编排**：主线快探（负载均值 73KB 无巨页；CI yml 语法验证）→ 三 agent 并行（Y dev=13D 检查点/wz、Z 审计=a11y 结构/主仓只读、AA dev=标题语义/wy）→ 主线集成/甄别/重建/收口。

- **Y（13D 按日检查点，`a3393e1`/`08145d1`）**：指纹版检查点 `sc13d_daily_checkpoint.json`——前提核查证明日索引不可变（URL=日期纯函数+Last-Data-Received 钉死头），诚实例外=当天文件在传播窗口会增长 → 每日行带原文 sha256，重跑磁盘比对零请求零解析、漂移只重算当日；6 新测试（中断续跑逐字节等价）+172 存量绿。**集成实战**：真网络首跑死于 WinError 5（Defender 瞬锁 tmp.replace）→ 主线热修 `ba89153`（3 次退避重试+直写兜底+永不外抛）→ 重跑复用崩溃遗留 27 天检查点、只补 592 天完成——续跑当场实战验证。遗留：CI cron 22:00 UTC 处传播窗口中段（指纹自愈；根治=调 cron，业主门）。
- **Z（a11y/结构首轮审计，`3a3d7bd`）**：1,502 页 8 项，5/8 干净（img-alt 0 缺/空交互 0/重复 id 0/正 tabindex 0/表单标签 0）；发现 8 hub 页零标题（P1）、footer 0/1,502（P2）、跳级 3 页、index 空壳（P1→甄别=轮 21 已裁决 redirect 非缺陷勿修）。
- **AA（标题语义，`b9ea8b7`）**：7 页 CardTitle→h1（`as` prop 可选升级、默认逐字节不变）、4 页 sr-only h1（既有键零新增 i18n）、跳级 3 页消除、force-camp h1、not-found `<main>`；tsc 0/eslint 0/19-19 校验；Tailwind v4 preflight h 继承实证=视觉零变化。**F-AUD3 改判误报**：站点无共享视觉 footer（命中=shadcn Card 类名 token），换 footer 会造伪 landmark → 关闭。
- **验证**：全套 pytest exit 0 + 重建 1,502 页 + 结构复验（7 页 h1=1、跳级消除）。wz/wy 清（junction 先摘、cherry 全 `-`）；Y/Z/AA 任务书归档。

## 2026-08-28 (kk) 轮③：契约闸门双拦真回归（ipo 价格窗口 / def14a 缓存脏行潜伏两轮）+ 审计 8/8 PASS + CI 13D 步预算修正

**编排**：主线核查（窗口探针 OK → 50 面板水位 → 16 步 fetch 族）→ 契约闸门拦截 → W/W2+X dev agent（worktree wx/wy）→ 集成/重建 → V 审计 agent → P3-1 主线直修 → 收口。业主授权继续，部署仍冻结。

- **fetch 族**：15/16 步收尾行验证；**13D 日更抓取被 900s 帽静默杀**（本地 18.5min 实证；脚本结尾一次写、无中间检查点，超时=零产出）——**这就是 smart_money 停 08-21 两轮的真根因**；2400s 重跑成功（18,668 行→08-27）。水位：news/reddit→08-28；ark/def14a(+2)/form_d/filing_stream/smart_money→08-27；cot 08-18 / korea 08-14 = 源节奏诚实（FRED DEXKOUS 08-28 复查仍停 08-14）；ARK distinct-days 仍 2（±pp ≥5 日门槛继续门控）。CI 侧同款病理已修：`refresh-terminal-data.yml` 13D 步 timeout 15→40min + 失实注释（"per-day cache 可续跑"）改正，8-K 步名 5→50 issuers。
- **W（ipo 价格窗口不变量，`9366fc5`）**：walker 不裁剪滑出"最新 80 priced"窗口的缓存条目 → priced 219→227 后带价 63 vs 窗口内 exact 58。W agent 代码完成后死于提供商网络错误，**W2 续作**补 5 测试（36 passed）。重跑暴露第二层：cumulative_walk(171)>task_budget(170) 一次性预算 vs 常态化每轮 walk 结构冲突 → 主线改造 per-walk bound（`requests_this_walk`/`last_walk` 字段 + 契约改写，`b9bbf4d`/`3365e4a`）。
- **X（def14a 缓存脏行，`1604be0`）**：全套 pytest 抓到轮 19 已修的 " Age" 尾三人组回归——轮 21 刷新把**修复前的脏解析缓存行**重新带入，潜伏两轮（21/22 只跑契约子集）。X agent 实证缓存行无 age 字段（任务书前提错→诚实偏离）：净名双胞胎见证谓词（19/25 命中含 trio；6 条无见证保守保留不进 lineage）+ 解析层单身份不变量；装配点在 `export_def14a_persons` → 重导出即净（644 人/co_board 59）。
- **ledger**：reddit data_ingest +1 行 append-only 复核重钉（LF 正典化 `83fa2778`）。
- **V 审计（`b799d06`）**：8/8 PASS，P0-P2 零；轮 22 修复全保持（死链 0/41,483、哨兵 0、Reddit 披露在位）；StatBand 10,391/9,385/43/2,812/322 复算吻合；i18n 1,095。P3-1 institutions 页头缺 filed 水位徽标 → 主线直修（SegmentHeader `extra` 槽 + 双徽标 + 1,096 对称，`8e87236`）；P3-2 ipo last_walk=0 为自愈伪影（下轮 walk 自动带真值）。
- **executives 方法学失真修正**：文本硬编码 "bounded 5-issuer universe and 2026-05 window" 而实际继承 50 发行人宇宙（/events 扩容漂移）→ 改动态插值（宇宙数+窗口起止），导出验证 "bounded 50-issuer universe and its 2026-05-01..2026-08-21 window"。
- **环境**：本地 pnpm 降为 9.15.1（`web/pnpm-workspace.yaml` 无 packages 字段：CI pnpm v10 合法、v9 报错）→ 本地构建 `pnpm --ignore-workspace build`；node_modules 再次损坏 → 清空重装 37.6s。全套 pytest 绿 + 重建 1,502 页。wx/wy 清（junction 先摘、cherry 全 `-`）；V/W/X 任务书归档。

## 2026-08-28 (jj) 查漏补缺+视觉持续优化轮②：审计抓新数据 P0×2→修复 + Southpoint 准入（明星 43）+ 缺口补跑 + worktree 内务

**编排**：长周期循环第二轮（业主定帧"查漏补缺+视觉持续优化"超长期任务）。主线先行（窗口探针 → 缺口补跑 → 视觉巡检）→ 双 agent 并行（审计 0 网络 / T 准入 efts+www 车道）→ 审计产出即派 U 修复 agent → 主线集成/重建/视觉终验。**"审计→修复→重建→复验"四步全在本轮闭环。**

- **主线缺口补跑**：filing_stream 加预算 890s 成功（**08-21→08-27**）；cot/politician 幂等无新（源节奏，诚实）；export + 85 契约绿；提交在案。视觉巡检 /news（665 条·198 源）与 /institutions（42 管理人）：零 P0/P1。
- **审计 agent（零网络静态扫查，`46edbaf`）**：新数据引爆 2×P0——(1) **13G 死链 58 处**（刷新带入 27 个宇宙外 ticker；根因：smart-money-view.tsx 的 13G 卡是 ⑳ DEV-K 未盖到的**第二条 ticker→Link 路径**，confirmation 复用组件 ×2）；(2) **`"NONE."` 解析哨兵**被渲染成链接（stakes_13g filings[20] Host-Plus）。P2×2：Reddit 统计条 count_declared(297) vs 载入 100 无就近披露；out/Aionis junction 令目录遍历递归（预览产物特性，记录在案）。**通过项**：统计条五数可复算、八 hub as_of 披露一致（08-26/27 水位上墙）、i18n 1,094 对称、诚实披露全部在位。**方法论确认**：每次数据刷新后跑一轮全站静态审计是本仓库的正确循环——新数据就是新死链/新垃圾的最大来源。
- **T agent（Southpoint 准入，wt）**：六闸门全 PASS（G2 知名度轨：$4.40B<$5B 但 Citrone 公开评论人身份，Corvex 口径；G3 macro 按 round-1 条件规则；G4 zh=null；G5 仅入 LP 壳 0001319998，LLC 主壳 NT-only 排除；5 请求记账）。**明星 42→43**。集成遇 cherry-pick JSON 冲突（agent 基线早于 08-27 刷新）→ 按正典处置：**中止 cherry-pick、只取 MANAGERS +1 代码行、主仓全量缓存统一重生成**（`d633e54`）；顺带三处 "~40/40" 过时计数措辞改中性。
- **U agent（P0 修复，wu，三 commit `8e25c31`/`54abc43`/`ee6ea16`）**：13G 卡接 DEV-K 同款 STOCK_PAGE_TICKERS 门（未收录→mono 纯文本，文件顶注"本文件所有 ticker→Link 必须过门"防第三犯）；导出端 `_cleanse_ticker()` 哨兵集合清洗（NONE/N-A/NULL/NIL/UNKNOWN/NAN→null、BRK.B 不误伤、11 边界用例、计数入 source_health 37/400、新增契约测试钉死）；Reddit StatBand 就近披露（zh/en 1,095 对称）。闸门：tsc 0 / eslint 0 error（33 存量不变）/ pytest 86/86。
- **重建终验（1,502 页 = +1 新 manager 页）**：哨兵 0、CIIT/VTMX/LSTA/WW 链接 0、python 复核存量 /stock 链接全在宇宙内、manager 页 129=43×3、StatBand 明星 43、"已载 100"披露上墙、smart-money 页视觉干净。tsc 真闸门用 `node node_modules/typescript/bin/tsc --noEmit`（**`npx tsc` 会命中 npm 假 tsc 包**）。
- **环境事故**：web/node_modules .pnpm 虚拟库损坏（@babel 系 dangling，`.bin/next` 消失）→ 清空重装 14.9s 修复。**教训：junction 共享的 node_modules 上禁跑 pnpm store/repair 类操作（会损坏本体）**；worktree 共享 node_modules 只读消费（tsc/eslint/next bin）安全。
- **内务**：旧 worktree m/n/wr/ws 物理目录全清（rd /s /q，不跟随 reparse point；0 junction 已核）。分支处置：agent-n/feat/ptr-transactions cherry 全 `-` → 删；agent-m（news salvaged WIP）/feat/insiders-breadth（form4 v2 WIP）**保留**（已回收进主线的演化前史，非补丁等价）。
- **边界**：display/data lane；0 ledger/frozen/config/prereg/OOS；未 push。**待业主**：H1 部署门不变。**循环续跑清单（下轮候选）**：eslint 33 warning 清理（低价值可排队）；ARK ±pp distinct-days 计数（每轮 +1 快照累积中）；Reddit/ApeWisdom 源分页死（源端限制）；smart_money 13D 族 08-21 水位（需 13D 日常增量窗口）。

## 2026-08-27 (ii) 视觉+真实数据核查轮：S 证据轮 2 全胜集成 / R 宿主病理确诊后续跑全胜集成（数据刷新到 08-27）

**编排**：业主 /goal 授权"视觉+真实数据核查进展 → 设计/开发任务区分 → 多 agent 分派"。主线先核查再派工（三度实证有效）：51 面板 as_of 扫描证实 ~24 日更面板停 08-18~25（→ R 派发正当）；全套 pytest exit 0；`next build`（pnpm@10——PATH 里 pnpm 9 会对 web/pnpm-workspace.yaml 的 config-only workspace 报 "packages field missing" 误障）1,501 页；IAB 视觉复验着陆页 + /data-health 全绿、零渲染垃圾。**首页误报排除（重要防再犯）**：`out/index.html` 为 13KB `__next_error__` 壳 = **正常**——`web/src/app/page.tsx` 本就是 `redirect("/dashboard")`，Next16 静态导出下重定向页即此形态（有 /dashboard 标记与 RSC payload）；"回归"假象由本地裸 `python -m http.server` 触发（basePath /Aionis + 无扩展名 URL 不解析 + 缺 out/Aionis junction——已按仓内先例建 `out/Aionis→out` junction 后正确复验）。部署冻结期无人看本地构建首页，故此形态从未被质疑。

- **S（INVESTIGATOR，wk，data.sec.gov 单源）全胜**：7/20 请求、最小间隔 2.65s、逐条记账；交付 `reports/design/2026-08-27-stars-candidates-evidence-round2.{md,json}`（主线 cherry-pick `a49698b`；worktree 已清、分支已删、git cherry 0 `+`）。核心改判：**Southpoint 二壳 CIK 0001319998 = Southpoint Capital Advisors LP，近 8 报告季 8/8 连续 13F-HR（壳级 PASS）**——轮 1 "BORDERLINE/二壳空窗疑云"被推翻，Citrone 体系持仓一直由 LP 壳承载，NT-only 只属 LLC 壳；net 潜在 +1，**准入未做**（留规格 §2-4 裁决：双壳 CIK 归属/去重语义/zh 名）。Icahn/Baron/Gundlach/Bessent = STILL-UNVERIFIED（结构性边界：data.sec.gov 无名称→CIK 发现手段；company_tickers.json 权威副本在 www.sec.gov 属禁访域；Icahn 族新增排除两实体 + 证伪两个记忆假设 CIK）。
- **R（DEV 数据刷新，wj）部分完成 + 重大环境确诊**：Phase 1 **4/10 成功**（ark +2026-08-27 8/8 基金 / reddit 08-27 43 帖 / ape_wisdom 08-27 100 tickers / news_feed 08-27 双语道 / korea 周度在位），bts 部分 JSON 校验 VALID；Phase 2 前三步挂死、后六步未达，Phase 3-5 未达。**根因不是网络**：`import pandas` 间歇性被系统层阻塞（挂点 pandas._libs 的 .pyd 加载；user-CPU≈0 纯等待；socket/ssl/numpy 单测全通 + curl 逐源全通；高度疑似杀软实时扫描锁文件）。窗口特征：好窗口 18:20-19:05 / 21:11-21:13 / 22:47-（数分钟级），坏窗口 19:10-21:10 / 21:14-22:47（0.5-2h）；**GNU timeout 的 KILL 在坏窗口内失灵**（GDELT 组 30min 杀不死，需 PowerShell Stop-Process）。此前所有"网络挂起"表象（COT/FRED/BTS/13D）多半为此故——**判据：banner 前零输出 + user-CPU≈0 = import 层挂，勿再误诊为源故障**。agent 自研两工具（留 wj 未提交）：`refresh_sweep.sh`（逐条 timeout 批量驱动）+ `window_retry.sh`（pandas 探针每 2min，窗口开即重跑 sweep，≤3 轮）。
- **保全与续跑（已收口）**：wj 增量缓存按"worktree 缓存必须拷回主仓"铁律（**第三次实证**，J/K/O 轮同款）robocopy /XO 回主仓（6,428 文件 / 4.2GB / 15s，含 ark 0827 八 CSV、reddit/ape/news_feed/korea、cot_aggregate 部分聚合、form8k cik_names、13D daily_idx 暖启动文件）；零 tracked 变更 → 轮 1 零空提交（准则：不制造空 commit）。**窗口重开（22:47）主线在主仓直接续跑并全胜集成（`1ddd625`）**：VIX/宏观 `--force` 在好窗口秒胜（= "网络挂起"假象的反证实录）；Phase 2-5 全链跑通——13D/13G/8K/DEF14A/FormD/IPO/PTR 全部刷新、form4 35 分钟窗内完成、价格收敛 585 只（+20/20 健康批次，Tiingo 429 由 Alpaca 兜底）、materialize、全量导出 51 面板。**契约闸门当场拦下真回归（闸门设计目的首次本地实战）**：`test_macro_drivers_panel_contract` 红——主仓本就缺 `alfred_CPIAUCSL/PAYEMS.json`（"本地-only 工件"类缺口**第三例**，CI-only 工件本地无生产步骤），且 `alfred_DFF.json` 的 vintage 形状被 `fetch_macro_display --force` 朴素单序列写覆盖（{"observations":...} 覆写多年切片）；按 workflow 第 197 行正典补拉（CPIAUCSL+PAYEMS force + `fetch_dff_vintages` 重建 293,536 行切片）后重导出，85/85 契约测试全绿。**刷新成效**：ark/reddit/form4/def14a/form_d/news_feed→08-27、form8k/13G/ipo→08-26、macro_drivers/market_context/theme_signals snapshot→08-27；38 文件 +9,681/−9,530；tsc 0。**诚实残余**（记录于任务书状态块）：filing_stream（步预算帽 290s 截断）、cot（CFTC 不可达，周更源）、politician_trades/smart_money/themes（无新源数据，源节奏）。**视觉终验双页过**：/data-health 日更面板大面积 08-27 + 散户热度缺口 3/7→0/6 + COT 缺口 3 周→1 周；首页新闻 08-27·190 源（原 08-25·107）、VIX 15.3（原 16.8）、等权指数 406.16 +3.13%（2026-08，原 2026-06）、Reddit 标的 290→297、公司 10,387→10,388、明星 42 在位、零渲染垃圾；重建 1,501 页绿。wk 清+分支删（git cherry 0 `+`）；**wj 留作续跑基地**（含 refresh_sweep.sh / window_retry.sh 未提交工具）；R 任务书已提交并带续跑协议状态块（探针先行 → 窗口开跑 → 幂等暖启动 → 完成后分阶段 commit）。
- **边界**：display/data lane；0 ledger/frozen/config/prereg/OOS（append-only 守卫测试全绿；wj ledger 保持预拷原样未提交）；未 push；密钥零暴露（报告只记 key=有/无）。待业主：H1 部署门不变；Southpoint 准入裁决可选（证据已备）。

## 2026-08-27 (hh) 全站审计驱动轮：P1×2 修复 + 死链全清 + i18n -96 + L1（1,501 页）

**编排**：四 agent（VERIFY 全站审计（零修复）+ DEV-G force-camp L1 + DEV-H i18n 清理 + DESIGN-J ARK 条件规格）。**先核查再派工**再次生效：ARK 快照实测停在 08-21（H1 冻结连带）——原拟的 ±pp 实施任务降级为条件触发式规格 `reports/design/2026-08-27-ark-pp-upgrade-spec.md`（Δpp=w2−w1 双端点+gap 披露、new/exited 标签 delta 恒 null、N=5 distinct-days 触发、冻结期零行为变化、启用构建任务输入清单 §6 全列）。

- **审计（commit 39c3aa0，两文件入 reports/audit/）**：全量 1,501 页、674 distinct 内链逐一核验、剥 <script> 后扫渲染文本。发现 **AUD-T1(P1) ×1,421 死链**（stock 页 managers chip→/manager 索引不存在——路由只有 [cik]）、**AUD-T2(P1)** stakes 副标题 `[object Object]`（window {start,end} 对象直插模板，tsc 拦不住）、T3(P2) 53 死链×115（BRK-B 双拼写/SNDK 更名未过宇宙门）、T4/5/6(P3) insiders·stakes·congress-tx 缺 as_of 披露、T7(P3) overview 注释写死 40。渲染垃圾全站唯一命中=T2；StatBand 五数调和全过（42✓）；i18n 对称 PASS。
- **主线直修 P1 对**（b0d12f2）：chip 目标改 /institutions（语义正确：策展明星目录在彼处）；stakes 窗口渲染 start→end（顺带覆盖 T5 窗口披露）。
- **DEV-K 修复批**（cf42785+3ecb459）：T3 六视图（smart-money 48/congress 16/events 1/executives 1/reddit 1 首屏死链→0）——门控源经 bundle 实证选择：universe 553KB 已是共享 chunk 且五个 hub 页本就加载，smart-money/events 新增该缓存 chunk 为对齐代价（如实记录）；降级=纯文本保留 ticker 不发链（站内 reddit/congress 先例）。T4/5/6 复用 ProvenanceBadge + provenance.asof 既有键零新增 i18n；badge 对 null 不渲染无伪造新鲜度。T7 改动态表述。85 契约测试绿。
- **DEV-G L1**（dbe6045+8996599）：主画布留 ≥3 节点分量（23 个 2 节点微分量全为"2 实体+单条 w=1 边"，无中间态可选）→ 折叠摘要卡 + chips 复用抽屉卡；入画子图重排冻结布局（layout.ts 零改动仍 seed-0 纯函数），近触对 86→31（↓64%）、保留边权 99.3%；URL 态 `?t=&w=` 照仓内"确定性 SSR + mount 客户端读"惯例（40 组往返用例），replaceState 写。i18n +4 键对称。
- **DEV-H i18n**（b15fdf4+c16112d）：扫描器覆盖 DictKey props 暗面（全域字符串字面量匹配）+ 前缀模板通配 → 确证孤儿 **96 删**（zh=en=1,093；纯删 198 行；零误判零回滚，tsc 类型守卫未触发）；6 存疑（forcecamp.legend/type 前缀）保留；历史 58/476 与本轮口径不可比已注明。
- **验证**：pytest 全套 0 FAILED + ruff 净 + tsc 0 + eslint 0 error/33 存量 + build **1,501 页**。三页联动目视复验（本地 junction 服务）：stakes 无 [object Object] 且日期区间渲染、force-camp 岛屿卡在位、stock 死链消失 + /institutions 链在场。worktree wg/wh/wi 三清（junction 先摘）、三分支 git cherry 全 `-` 后 -D、任务书五份归档 completed/、本地服务已停。

**边界**：display-lane；审计零修复承诺兑现（修复全部走独立任务/主线裁决）；0 ledger/frozen/config/prereg/OOS。**未 push**。**待办交接**：(1) H1 部署门（ARK ±pp、theme_signals 06-30、全站数据新鲜度都被它门着）；(2) Southpoint 二壳（CIK 0001319998）证据轮可选；(3) universe 模块头注释过时（"only /stock imports it"）供后续 lane 顺手改。

## 2026-08-27 (gg) 双轨轮：def14a 人名降噪 + 明星投资人诚实 +2（Corvex/GAMCO 准入）

**编排**：继续设计/开发分离多 agent 模式。DESIGN（主仓，纯文档）+ INVESTIGATOR-E（worktree we，只查证据不做裁决）+ DEV-D（worktree wd，修复）先并行；证据落盘后按规格 §2-4 裁决程序由主线代裁（全 PASS 才代裁，BORDERLINE 留业主），再派 DEV-F（worktree wf）落地。任务书四份 TASK-DISP-{DES-stars-curation-bar,D-def14a-name-denoise,E-stars-evidence,F-stars-admission}.md 全部归档 completed/。

- **策展门槛规格**：`reports/design/2026-08-26-stars-curation-bar.md`——从现役 40+5 剔除档案提炼 11 条隐含标准（S1-S11），固化为六闸门 G0-G5 与 watch/出局规则（落后一季=watch 展示、连缺两季出局、复活须重赢 4 季）。契约测试均为派生锚：roster 变化无须编辑测试，唯一枚举对齐点 = FORM13F_CATEGORIES（新增第八类定为超权限留业主）。**Pershing Square 面板停在 2026-03-31** = watch 态活体案例（Q2 只报 NT 是忠实 EDGAR 行为非 bug），集成时明令 F 不触碰。
- **证据报告**（INVESTIGATOR-E，commit 3be1432 → cherry-pick 0b4daa4）：`reports/design/2026-08-26-stars-candidates-evidence.{md,json}`，请求账 58/60（≥2.25s、SSL 瞬时退避、403 后换 SEC 式 UA 全通；实体名以 data.sec.gov submissions 为权威——EDGAR atom conformed-name 有 Perl bug 的实测情报）。判定：PASS=Corvex(0001535472, ≥13 季)+GAMCO(0000807249, 改名链核验)；FAIL=JANA/Tudor/Blue Ridge；BORDERLINE=Southpoint（第二壳被预算闸截断）；UNVERIFIED=Icahn 主壳/Baron/Gundlach/Bessent。**净潜在增量 +2 而非 −3 归零**。起点池七人中 Ackman/Klarman/Coleman/Halvorsen/Mandel/Tepper 均已在册（诚实记录避免重复考察）；GLENVIEW/Point72 大写节点已与在册 CIK 对齐无重复壳。
- **人名降噪**（DEV-D，3 commits）：根因 = `src/aionis/ingest/def14a_persons.py` HIGH 层三年龄锚点正则的 `_NAME_CORE` 贪婪把行内 "Age" 吸作名字尾部 token；既有 `_NAME_STOPWORDS`/`_TITLE_PREFIX_WORDS` 两道防线都够不到尾部。修 = 字面枚举正则 `_AGE_STRUCT_TAIL_RE`（"Age"+2-3 位数字才剥；无数字见证的裸 Age 可能是姓氏→不剥不猜）；残渣 span 整体丢弃。有界重抓恰 4 份脏文档（8 GET 入 request_accounting，repair_log 记录 before→after）。结果：distinct 660→644（25 行脏身份并回）、roles 取并集（有测试钉死）、lineage 幻影自并边清除（772→763、co_board 68→59、144 节点）——是边数收缩而非权重膨胀形态，同样正确。
- **准入落地**（DEV-F，2 commits f9c4763+ccb4012）：`MANAGERS` 字典 +2 行 verbatim（Corvex zh=null/activist——medium 置信中文宁缺毋滥照 S7；GAMCO（加贝利）/value high 置信采纳）。抓取插曲如实入档：首派同任务中断调用的缓存已在 worktree，F 探测后零请求复用（212 文件 mtime 金丝雀证明幂等），代价推算 ≤10 polite GET 远低于预算但无第一方账目——诚实声明处理。连锁：明星 **40→42**、ticker 覆盖 1181/1580→1242/1655、co_hold 636→697（+61 全经新人）、bridges 46→51、largest 分量 44→46、首页统计条自动跟随、/manager/[cik] SSG +2。
- **集成教训二次实证**：主线首轮内联重生成曾回退到 40 管理人旧态——form13f 抓取缓存（212 文件 + aggregate/dir parquet）在 worktree 未同步主仓；从 wf 拷回后重生成与 agent 版逐字一致仅 snapshot_ts 差（本轮第四确定性复现）。J/K/O 轮"聚合缓存拷回主仓"惯例再次必要，凡新数据 lane 记住这条。
- **验证**：pytest 全套 0 FAILED（新增 test_def14a_person_names.py 11 测试全绿；定向 97 passed）+ ruff 本 lane 净（新发现记录：ruff format --check 对 scripts/ 72 文件报基线漂移系存量惯例外，仓库只跑 ruff check，未做格式 churn）+ tsc 0 + eslint 0 error/33 存量 + build **1,501 页**（manager/[cik] SSG +2 实证）。四页联动目视复验全过：dashboard 明星投资人=42 / institutions GAMCO·Corvex 卡在册 / executives "Age" 噪声清零且 Chiappone 干净名在场 / force-camp KPI 146-824 与共同持仓 697、共席 59 及干净人名全部一致。worktree wd/we/wf 三清（junction 先摘铁律）、三分支 git cherry 全 `-` 后 -D；本地服务已停。

**边界**：display-lane；在册 40 人零触碰、不凑数不新类别；真实 EDGAR 请求全部礼貌记账；0 ledger/frozen/config/prereg/OOS。**未 push**。**待业主**：H1 部署门不变；BORDERLINE（Southpoint）与 UNVERIFIED 四人如需再查另派证据轮。



## 2026-08-26 (ff) H5 势力阵营 GO 轮：设计规格单 agent 构建 → 集成上线（1,499 页）

**业主裁决**："授权你处理，部署部分暂时仍不做安排"——即 (ee) 待办清单第 1 项 GO、第 2 项（H1 部署/计费）维持冻结。单构建 agent 派发（worktree wc，junction+LF ledger 预置），规格 = (dd) DESIGN 轮产出的 `tasks/active/TASK-DISP-H5-lineage-build.md`（自包含，agent 未读设计文档亦能执行）。

**交付**（3 commits：34d86f9 面板导出 / 1729885 契约测试 / 5df18c8 页面视图）：文件清单与规格 §2 逐项一致（5 新建 + 8 修改，零越界）。

- **主线审查裁定的偏差七处**（报告完整披露，逐一采信）：① 唯一实质项 = **体积门 200KB→512KB**——实测 co_hold 平均 w=4.61（max 20，与设计期 D.E.Shaw×Millennium/Millennium×Citadel 双 20 吻合）×2,553 条 shared 明细 ≈ 本征 412KB，"不改 lied 数据的任何编码都不可达 200KB"；照 form4 cap 先例提升 + 导出器注释写明推导 + T1 测试同值。② SegmentHeader 无 segment="institution"（联合类型仅 context/evidence/validity/verdict/guard）→ 用 evidence（与 /institutions 同款）。③ co_target 权重语义统一到全局不变式 w==len(shared)（T5 钉死）：w=不同共同目标数。④ bridges 行落 `stock_routable` 布尔（§7 导出期判定路径），shared 形状零增项。⑤⑥⑦ 环境类（内联三函数导出/PYTHONPATH venv/npx 等价命令/build 留主线）。
- **规模对账**：co_hold 636 / co_board 68 与设计精确吻合；co_target **68 vs 预估 53**——agent 穷举自然过滤候选（修正案/ticker 过滤/跨 lane 配对）均推不出 53，定性为**同窗口径差而非数据漂移**（可见日期跨度逐日一致、四面板 as_of 同为 2026-08-21），实现在字面规则上冻结并全文重算钉死。146 节点/46 bridges（CALM 唯一三 lane）/components {36, largest 44}/truncated 边 103 全自洽。payload 412.1KB。
- **身份合并诚实性**：实际并入仅 ARK/GLENVIEW/Point72 三家——设计预估五家中 AQR/Millennium 在当前可见窗是**单申报人组**（无 pair 无边则不建节点）。代码只写 `_lg_norm(filer)==_lg_norm(manager.name)` 规则绝不写名单，T7 反漂移测试验证。
- **红线落实**：methodology 与界面双 disclaimer 完整（joint filings NOT DECOMPOSED / INDEPENDENTLY / no COORDINATION implied / NO PRICES NO RETURNS）；grep 复查 "consortium|联盟" 仅否定语境注释命中；深链门控实测。

**集成与验证**：3 commits cherry-pick 进 main 零冲突；主线重生成 lineage_graph/data_health/api_catalog——与 agent 版**逐字一致仅 snapshot_ts 差**（本轮第二次确定性复现证明）。pytest 全套 exit 0（11 新契约测试含三个逐边重算比对类）；ruff 本 lane 净；tsc 0；eslint 0 error；build **1,499 页（+/force-camp ○ 静态预渲染）**。目视终验（本地 junction 服务 + IAB 截图/DOM 双通道）：KPI 带 146/772/36/40、三药丸计数吻合、SVG 冻结布局主簇居中、边级 a11y 标签 "A ↔ B · w=N" 齐、min-weight 步进器在位；抽屉卡点击实测（COATUE MANAGEMENT LLC/蔻图资本双语名 + 13F 徽章 + 度数分解 共同持仓37 + 关联席位 ticker 门控深链 PYPL/AMD/ENPH 可点·TSMC/SpaceX 纯文本 + /manager/0001135730 深链 + close 按钮）；四分区表列头先渲染（P9）。worktree wc 清（junction 先摘）、分支删（git cherry 三补丁全 `-` 后 -D）、任务书归档 completed/、本地服务已停。

**记录的残留（非本 lane，未处理）**：(a) co_board 人名含 "…Age"/"Insider Participation" 类噪声 = def14a_persons 上游解析分级输出的 verbatim 投影（人级解析红线域）；(b) 图谱外围 36 个小微分量的信息密度低（"岛屿卡"列为 L1 可选增强非验收门）。

**边界**：display-lane；零新抓取（纯派生四 committed 面板）；0 ledger/frozen/config/prereg/OOS 接触。**未 push**（计费阻断持续，部署冻结中）。**下一步候选**：ARK ±pp 待快照累积 ~30 日；势力阵营 L1 增强（岛屿卡/URL 态筛选）另议；H1 部署门等业主。



## 2026-08-26 (ee) 多 agent 分工轮：视觉/数据核查 → H2 实时价图 + H3 IPO 发行价 + H5 设计规格

**编排（业主授权"设计开发任务区分、分配给不同 agents，避免单 agent 上下文/token 膨胀"）**：主线先完成业主要的**视觉+真实数据核查**再派工。核查结论：构建产物健康（本地静态服务需经 `web/Aionis` junction 以 basePath `/Aionis` 服务——直服 out/ 会全 404 黑屏，本次踩到并即修）；首页/新闻/AAPL 页逐项核验通过；24 日更面板 as_of 冻结在 08-18~21 = Actions 计费门实证（H1 未触碰）。两处方法论记录：截图管线间歇超时 → DOM 实测等效替代（handoff (l) 先例）；"首页内容横向重复"视觉报告被 DOM 反证（scrollWidth==clientWidth、VIX 叶节点唯一）→ 截图合成伪影。

**三 agent 并行布局**：DESIGN 主仓直做（纯文档零冲突）+ DEV-A worktree wa/feat/stock-live-chart + DEV-B worktree wb/feat/ipo-offer-price；任务规格三份自包含文件先落 `tasks/active/TASK-DISP-{DES-force-camp-graph,H2-stock-live-chart,H3-ipo-offer-price}.md`（完成后前两者与 DES 已归档 tasks/completed/，H5 构建规格留 active）。junction 预挂 node_modules、ledger LF 预拷（CRLF pin 假阳性预防）、form_ipo 缓存预播种。

- **DESIGN 全胜**：`reports/design/2026-08-26-force-camp-design.md`（数据模型/采样口径/派生 schema/可视化决策/契约测试清单/实施阶梯全答）+ `tasks/active/TASK-DISP-H5-lineage-build.md`（可直接派发的构建规格）。实测基础扎实：三条边规模（13F 共同持仓 636 对 / DEF14A 人物共席 68 对 / 13D/G 同目标聚集 53 对）、ticker 并集 1,015 中仅 227 在 stock_universe（深链必须门控）。**关键诚实发现**：可见 520 行 13D/G doc_url 全唯一——联合申报未被按成员拆解，边只能叫"同目标聚集"，绝不能叫"联盟"。形态推荐手写确定性 SVG 力导向（种子 0 固定布局，照 heatmap 手写 squarified 判例）+ 常驻四分区表格回退态。跨域共同标的只落桥接表不画布（公司级巧合≠法律关系）。**勘误入档**：导出端真实路径是 `scripts/export_terminal_data.py`（非 src/aionis/reporting/）。**留业主 GO 门**（roadmap H5 即业主决策项），GO 后直接派发构建规格。
- **DEV-A（H2）3 commits**（2ed8327/7a19fde/5bc1275）：前置核查实证 workers/prices 三端点（us=Tiingo IEX ~15min 延迟/cn=新浪 hq.sinajs.cn/health）均**无序列端点** → 按任务书三选一裁决取 (b) 本页累计采样（诚实口径：60s 轮询累加、stepAfter 忠实恒定段、环形上限 240≈4h、刷新清零明示）；复用父级 useLivePrices 零新网络回路；render 期派生状态（避开 effect 同步 setState lint error 的实战修复）；组件顶 display-only 反泄漏注释；Worker 失败整组件返 null 静默退化 header pill。i18n stock.live.chart.* zh/en 各 8 键对称（node 脚本验证 1082=1082）。文件：components/stock/live-price-chart.tsx 新建 + stock-view.tsx 挂载（统计瓦片之下双栏主体之上）+ dict.ts。
- **DEV-B（H3）真抓取落地**：bounded-parse 照 stakes_pct 先例镜像——`src/aionis/ingest/form_ipo_price.py` + `scripts/form_ipo_price_parse.py` + `tests/test_form_ipo_price.py` 三件套。最新 ≤80 priced(424B4) 逐份 index.json→主文档封面价分级解析：**exact=63（28.5% of priced）/ low=0 / none=15（14 no-match + 1 no_primary_doc）/ fetch 失败 1 保留重试资格**；草稿区间措辞与假设语句整句跳过绝不猜值。请求账 **169/≤170**（EFTS 窗口刷新 12→聚合升至 1,077 filings/priced 221 + 试跑 4 + 主走查 153，cap 154 于 77/78 触发截断如实披露）、≥2.1s 显式抬高。幂等实证：--max-requests 0 复跑 78 条 ok 零请求 + hermetic 测试钉死。导出 offer_price 可空 per-row + offer_price_parsed/meta 汇总（覆盖数学与可见行同源选择规则调和）、ipo-view 第 5 KPI 卡 + 价格列 + 披露行、dict ipo.price.* 四键对称并修正过时"v1 不解析"文案、7-gate 文档 v0.2 附请求账。

**集成与验证**：五 commits cherry-pick 进 main 零冲突（双方 dict.ts 改动不同区域自动合并；B 初版未 commit 由主线审查后代提交为两个原子 commit）；缓存同步主仓后统一重生成 form_ipo/data_health/api_catalog——重导出与 agent 版逐字一致仅 snapshot_ts 差 = **确定性复现证明**。pytest 全套 exit 0（agent 侧全量 2046 passed/10 skip）；ruff 本 lane 净（全仓 20 存量错全他方：docs/code-review/_sync.py 8、scripts/bts_tsi_fetch.py 3 [A3 salvaged caef736]、archive/krx-probes/* 9 [探针档案不改写]）；tsc 0；eslint 0 error/33 存量警告；build **1,498 页**。运行时目视双验：/stock/AAPL 六要素（标题「实时走势（本次访问）」/口径注记/display-only 徽章/采集中态/Tiingo 来源行/recharts SVG 挂载）；/ipo KPI「发行价已解析」+ 列头「申报日 公司 状态 发行价 文件类型 原文」+ $23.50(ALH)/$17.50(LYNX) 与解析账吻合 + 无渲染垃圾。worktree wa/wb 双清（junction 先摘铁律，主仓 node_modules 完好性实测）、分支双删（`git cherry` 五补丁全 `-` 等价核验后 -D）；本地服务已停。

**边界**：display-lane 全程；0 ledger/frozen/config/prereg/OOS 接触；真实抓取仅 DEV-B 预算内 EDGAR/EFTS 礼貌请求。**未 push**（计费阻断持续）。**待办交接**：(1) 势力阵营 GO 后派发 `tasks/active/TASK-DISP-H5-lineage-build.md`；(2) H1 部署门（D0 计费/阶梯 1 本地 runner）不变；(3) ARK 快照按日累积中，~30 日后首页卡可升 ±pp 真增量。

## 2026-08-25 (dd) Tier-7 视觉多轮迭代：首页模块全齐 + 双语新闻流 + 全页目视终验 + 后 parity 规划

**参照态复查**：data.xiaoyinsi.com / app.xiaoyinsi.com 仍 NXDOMAIN（DoH 1.1.1.1，08-25 实证；根域存活无终端）→ `runs/ui-iter/` 冻结基线（12 PNG + 10 HTML + 编译 CSS）为唯一合法参照。**视觉通道本 session 重建**：Read→CDN→analyze_image 三连可用（CDN URL 须原样含反斜杠路径——上轮 1210 阻断已消，环境差异）。

**首页 15 模块全齐（T7A 代理全胜 + 主线两处裁决）**：对方首页完整解剖（hero 目录规模统计条 / 指数三卡 / 中文快讯 / 最新举牌 / 近期 IPO / 机构申报 / 情绪榜 / 政客环形 / 明星投资人 / ARK 异动 / 重大事件 / 高管变动 / 探索全部模块页脚）vs 我方原 6 模块 → 补齐 7 新模块 + 情绪榜/政客卡全解剖升级 + 统计条切目录规模（10,387 公司 / 9,385 申报人 / 40 明星 / 2,812 政客交易 / 290 Reddit——全部实数，data_health 新增全 47 面板 `rows` 字段为源 + 对账契约测试）。诚实降级七处入代码注释：IPO 用 ipo 面板（formD 是 Reg-D 无法映射状态）；高管变动按公司级（人名/方向解析 = 既有红线）；ARK 无 ±pp（无历史）→ 基金共振排名；Reddit Δ 显示 24h 提及变化非价格；机构申报无时间字段只显 MM/DD；举牌 chips 是 13G 家族；明星计数 40 非 43（诚实策展）。**主线裁决一**：明星卡不进 650KB 全量书 → `export_form13f_stars`（导出时从已提交面板派生 top-8，~2.4KB）+ form13f-stars.ts 专用小模块 + 摘要/全量对账测试（top1 = 全量最大书、字段逐项 verbatim、n_managers = 全名单）。**主线裁决二**：CATEGORY_LABEL 从 events-view 导出（首页与 /events 单一事实源）。

**双语新闻流（T7B 代理证据先行全胜 + 主线接线）**：Phase-1 探针（10 礼貌槽）——`sourcelang:zho domainis:wallstreetcn.com` **200/200 满帽真中文财经快讯**（API language 字段全 "Chinese"）；财联社 cls.cn 零 GDELT 覆盖；CJK 短语查询被 API 拒（"phrase too short"）→ 域锚定是唯一证明形态。Phase-2 ingest：`_LANES` 双车道（eng 查询原样 + zho 域锚定）、`lang_code()`（API language 优先 → 请求车道兜底 → 绝不从标题字节猜）、legacy 缓存回填 eng、单车道失败诚实降级（存活车道合并 + 失败车道自然老化）+ 10 测试。真实抓取 400 条（200 中 fresh 至 08-25T10:00Z + 200 英缓存保留——eng 撞 429 降级路径实战验证，次日自愈）。**主线接线**：export_news_feed 增 lang/n_zho 字段 + query 双车道 verbatim + 方法学双语披露（财联社零覆盖/CJK 被拒入档）+ 契约测试扩展（lang∈{eng,zho}、与 language 字段一致、n_zho 窗口口径）；前端 NewsFeed 类型 + 双语计数芯片（中文 200 / EN 200，琥珀/brand 双色）+ 前缀色调改读 lang 字段；`docs/data-intake-gdelt-news-feed.md` v0.2 探针证据表。

**视觉轮抓到真 bug（正是多轮目视的价值）**：news-view `groupByDate` 仍按 GDELT 紧凑格式 `slice(0,8)` 切早已 ISO 化的 seendate → 日期头渲染 **"0月NaN日"**（此前像素通道量不出来——分组头存在但内容错）。修为 ISO 切片，产物实证 8月25日/8月24日 分组降序正确。

**8 无基线页目视终验**（taco/stakes/market/annual/executives/manager/api-docs/filers——Tier-4/5 只做过 proxy 家族对照）：逐页 PASS/FAIL 清单式目视（页头计数/统计带/面积图签名/日期分组流/行对齐/渲染缺陷）**全部 PASS**；market 一条"图例重叠"报告经 DOM 反证为视觉幻觉（无 Legend 元素）——幻觉交叉核验铁律再次生效。

**内容深度终审（对方首页声明口径 vs 我方面板实深）**：公司 10,387 > 6,517；申报人 9,385 > 8,741；政客 2,812 交易级 > 2,778 申报级；明星 40 vs 43（诚实策展差 3）；Reddit 290/100 vs 681（源分页死，披露）；举牌 15,982 vs 流；IPO 1,046 无价格（v1 边界）；高管公司级（人级红线）；ARK 快照（历史累积中）。诚实残余四项全部记入规划文档 backlog，不为凑数编造。

**后 parity 规划（`reports/design/2026-08-25-post-parity-roadmap.md`）**：战略判定 = 参照站已被运营者删除，**Aionis web = 终局形态的唯一存活实现**（且多三层对方没有的：溯源优先/可证伪研究层/双语+颜色约定）。优先级阶梯：H1 终端重新上线（Actions 计费冻结中；realtime-architecture 文档阶梯 1 半天可解）；H2 /stock 实时价图（display-only Worker 已有）；H3 深度残余（IPO 价格解析 S/M、ARK 历史自动累积、明星诚实 +3）；H4 E3 前瞻账本收敛（驾驶舱变 E3 观测台，AUD-06+GO 门不变）；H5 势力阵营（对方 TODO = 我方血缘图谱原始模块）；H6 API 目录随面板深化。反目标三条入档（不凑数/研究面零接触/不复活抓取已删参照）。

**验证**：pytest **2,028 passed**/9 skip（+12：rows 对账、stars 摘要对账、news 双语 ×10）+ ruff 净（本 lane 全部）+ tsc 0 + eslint 0 错（33 警告全存量）+ build **1,496 页** + 目视验收（首页 10 模块/统计条/无渲染错误；新闻双语混排/多日分组/无 NaN）+ 像素复核（首页 8.78 vs 9.73、新闻 10.25 vs 13.89，残余=语言构成数据属性；rail 1363=1361、margins 77/79 一致）。**未 push**（计费阻断持续，业主指示后面解决）。

## 2026-08-24 (cc) UI 遗留精化三件收官——计数窗全站对齐

核验修正：congress/events **本已有 countHint 计数窗**（审计时漏记）；/filers /companies 行密度**已达标**（50 行 mono 单元格+truncate 实证）。真缺口仅 /taco /market 两页——各在页头加 mono 计数轨（taco：N VIX 月·N 事件·窗口；market：N 月·最新 VIX·窗口，与韩国代理卡共存）。IAB 三页验证 + build 1,498 页 + 数据测试绿。**UI 颗粒度对齐轮（审计→基座→页面组→精化）全链闭环。**

## 2026-08-24 (bb) UI 颗粒度对齐轮：审计 + 基座 + 四组页面升级（业主"UI 过于简陋"判定响应）

**审计方法论修正（业主硬条件重申后）**：浏览器逐页实测部署端——**关键发现：data.xiaoyinsi.com = 本仓库的部署皮肤**（其 /institutions 载本仓 40 位明星策展+中文别名+七分类按钮原样；侧栏"语境/效度/可证伪主张/守卫"= 本仓 IA；⌘K/颜色约定切换/语言/主题四件套同款）→ **同数据两套皮肤，对齐 = 1:1 可映射**。审计文档 `reports/design/2026-08-24-ui-granularity-audit.md`（token 差距表/导航壳差距/逐页版式差距/可复算验证记录）。

**基座（db44089，全部页面继承）**：dark 画布 → **纯黑 #000**（卡片/弹层/次级面同降为更平的 OLED 阶梯，hairline 分隔取代大面阶梯）；**Geist** latin 面（next/font 构建期自托管，CJK 回退原生栈）；**(dashboard) 统一 max-w-[1320px] 内容轨**；侧栏数据路由 **双行项**（标题+描述副行，nav.sub.* 14 键 zh/en）。编译产物实证：`--background:#000` + Geist + 1320px 均在 CSS chunk。

**页面组（主线直做——cron 被"会话已是计划任务子"限制，且配额 02:38 才重置，不等待）**：U1 /congress **热门标的芯片行**（tx 面板客户端聚合 top10、诚实计数、宇宙守卫链接）；U4 /dashboard **数据驾驶舱**开页（新闻快讯 top5/散户情绪榜 top10/政客交易 top5 三卡，零新导出；效度叙事保留其下）；U2 /stock **锚点芯片导航条**（持仓机构/政客平滑滚动锚 + 内部人/明星基金经理路由链接——诚实：本页只有 f4 KPI）；U3 /institutions 机构卡**双名两行排版**。+13 i18n 键。

**验证**：tsc 0 + eslint 净 + build **1,498 页** + SSR grep（1320px/热门标的/散户情绪榜/持仓机构锚）+ **IAB 三页终验**（驾驶舱三卡+效度链共存+44 双行副标；congress 芯片行+78 链接+政党指数；stock 锚点+id）+ 全套 **2,016 passed**。/news 语言分段**主动放弃**（我们的 GDELT 源 sourcelang:eng 全英文，分段=空中文的假开关——记档）。**遗留精化项**（下轮代理或主线）：congress 页头"共 N"前置统一、events/taco/market 页头计数窗、filers/companies 行密度微调。

## 2026-08-24 (aa) 韩国杠杆维度闭环：业主方案 C 自主执行——USD/KRW 降级代理卡上线

业主三选一问询未获答复 → 按常设指令（"抛弃边界全力推动" + TACO→BTS 先例 + C 为"最快路径选定即建"）**主线自主执行 C**：FRED DEXKOUS 周频（2,904 行 2015→2026-08-14，最新 1,414.29，52 周压力位 3%——韩元处年内平静端）→ /market KoreaProxyCard（KPI 三格 + 104 周条带 + 口径披露行）。**诚实降级三处明示**：卡上 note、方法学（"NOT margin financing"、六路线封锁+付费市场证据链指针）、契约测试钉死措辞。复用 macro_display FRED 模式（≥2s/幂等缓存）。IAB 实测（标题/1,414.29×2/104 条/披露行）。插曲：market-view 插入首落 awaiting 分支（SSR grep 空发现）→ 移主返回区重建。**全套 2,016 passed / build 1,498 页**。**至此小隐寺全部维度（含原豁免三件）均有面板**：韩杠杆为 C 降级位（业主 A/B 随时可替换为真实数据）。

## 2026-08-24 (z) KRX 性质终审更正：付费市场而非注册 key

openapi.krx.co.kr 主机**可达**（此前只测过 data. 子域）→ 读到官方구입안내原文：**付费数据市场**（결제→심사→이메일/网页下载；银行转账、汇款人=订购人、学术半价需证明）——**不存在免费注册 key**，交付为文件式非 API 端点。韩国杠杆维度终态 = 6 条免费路线实证封锁 + 官方唯一路线为付费购买（业主三选：A 付费购买文件摄取 / B 提供韩国网络出口重测 / C 指定降级等价物）。归档 README 已更正。

## 2026-08-24 (y) KRX 终审：六路线（终审补 FRED 无此序列 + BOK ECOS TLS 地域封锁两路线，共 26 探测）全封锁实证 + 续接指南归档

**追加三探**（08-24 深夜，接 verifier 判定）：① pykrx 源码路径 GitHub 全 404（仓库迁移，放弃依赖）；② **OTP 下载流**（老门户第二端点族，此前未试）：`GenerateOTP` 成功发出 320 字符 token，但 `download.cmd` http 变体引至公告页、**https 变体返回 `서비스 에러`（服务端内部错误）**——token 与浏览器 JS 建立的会话状态绑定，非参数问题；③ 公告页文本解析确认为通用错误页非海外提示。**四条自动化路线（getJsonData LOGOUT/400、download http、download https、真浏览器渲染挂起）全部实证封锁，共 24 次探测**。归档补全 `archive/krx-probes/README.md`：证据表 + 续接指南（openapi.krx.co.kr 注册 key = 唯一业主步骤；已验证 screen ID MDCSTAT01501/menuId MDC0201020101 与查询参数；EUC-KR 编码注意）。**韩国杠杆面板 = 全项目唯一待业主输入项**。

## 2026-08-23 (x) 边界废除轮收官：四 lane 三成一阻（2,015 passed / 1,498 页）

**四代理 23:23 齐灭于配额 [1308]（重置 08-24 02:38）→ 主线回收接管（第五次 WIP 裁决回收，零浪费）**：

- **A1 人级档案（3f723c4→e2d5db3）**：死亡前抓取已完整跑完（150/150、293 请求）但导出跑在抓取前（U 先例同款缺口）→ 主线重导出修复：**104/150 份出名单（69.3% 覆盖率披露）、660 去重人物、104 董事会卡**；解析方法分级诚实计数（section+age 79 / name+role 25 / unparsed 43 / no-doc 3）。/executives PersonsSection。
- **A3 货运 TACO 等价物（5501616→caef736）**：BTS TSI 公共域月频（2026-06 = 134.9，MoM -0.3/YoY -1.75%）+24 月序列；**降级口径面板内明示**（"非卫星数据"）。/taco FreightProxySection。冲突教训：api_catalog/data_health 不可取 side——统一再生。
- **A4 方法书架（2ff6cac→b534faf）**：零网络双层——自有文档架（prereg/ADR/理论/rubric 导出时索引+GitHub 外链）+ 公共域研究策展链出（BIS/FEDS/IMF/NBER editorial 标注）。/shelf 新路由。
- **A2 韩国杠杆 = 诚实 BLOCKED**：21 探针证据链（getJsonData.cmd 对复刻浏览器序列回 LOGOUT/400；真浏览器数据区永不完成渲染快照超时；openapi.krx.co.kr 需韩国注册 key）。探针归档 archive/krx-probes/（含 screen ID MDCSTAT01501/menuId MDC0201020101），**业主提供 KRX Open API key 即可续接**。

**合体验证**：pytest **2,015 passed**/9 skip + ruff 净 + tsc 0 + build **1,498 页（+/shelf）** + IAB 三面实测。worktree 四清。**覆盖终态：全部 17 路由 + API 分类学全部可自动化维度；唯一阻断 = KRX（需业主 key）**；部署暂缓。

## 2026-08-23 (v) 终态后增补轮：Z1 主题 ETF + Z2 统一流表单补全（业主持续指令）——**双集成收官，API 分类学维度全清**

**Z1 已集成（1dae5b9→main）**：主题 ETF 面板 = 小隐寺 API 分类学**最后一个数据维度**。10/10 基金发行商官方 CSV（iShares 4：SOXX/ICLN/ARTY/BAI + Global X 6：AIQ/CLOU/BKCH/LIT/BOTZ/BUG——日期入文件名者每次从基金页 HTML 提取当日 href），523 持仓/97 跳行披露，跨基金共振（NVDA×5 基金，MU/AMD/AVGO/SNOW×4）；**诚实剔除 9 只**（BLOK JS 渲染无直链/PHO/TAN SPA 改版/SMH TLS 拒连/CIBR/FIW/SKYY 不可达/SPDR 仅 XLS/QTUM 无端点——量子/水/元宇宙为诚实缺口，全部记档 7-gate G6）。稳态 16 GET/run。验证：68 数据测试 + 全套 **1,985 passed** + tsc 0 + build 1,497 页 + IAB（主题 ETF 板块与 ARK 家族共存）。wz1 已清。

**Z2 已集成（6586f87→main）**：DEF 14A 80 + DEFA14A 166 + 424B4 21 并入（total_merged 16,597→**16,864**，19 表单族窗表）；幂等缓存使存量 16 表单零请求、仅 4 页新请求。**契约诚实性**：by_form 只计可见 newest-800（sum==n_visible 固定契约）——424B4 的 21 行全在截止外，计入 total_merged 不入 by_form，agent 保留契约不为凑键扭曲（正确裁决）。验证：67 数据测试 + tsc + build 1,497 页；wz2 已清。Z1 主题 ETF 运行中（源考古为长杆）。

**范围裁决**：终态审计后业主再推"多 agents 同步推进"——剩余真实可并行维度两枚：Z1 = 主题 ETF 面板（小隐寺"12 主题 ETF"维度；发行商官方公开持仓文件，照 ARK 已验证模式；源考古须浏览器逐基金验证直链，宁缺毋滥 6-12 只）；Z2 = 统一流 v2 补 DEF 14A/DEFA14A/424B4 三表单（当时划界排除项，现并入；增量缓存幂等只发新表单请求）。**DEF14A 人级解析维持 DEFERRED 并升格为红线记录**：代理书 HTML 人名正则抽取的编造风险与"不猜测不编造"质量红线冲突——除非找到结构化一方源（如 EDGAR XBRL 化的委托书数据未来可用），否则不做。worktree wz1/wz2 已建。

## 2026-08-23 (u) X/Y 收尾集成 + 17 路由终态（1,984 passed / 1,497 页）

**Y（/quarterly+/annual）**：aca668b→`71f2df2`。深切必要性被数据证实——800-newest 可见流中 10-K/10-Q 行数 **0**（财报季挤压）→ 导出深切 annual 76/76、quarterly 400/2,115（cap 披露+全量计数 KPI）；共享 fin-deadline-view（variant 参数）+ 两路由 + sidebar/palette + i18n 23×2。cherry-pick 零冲突；IAB 实测 /quarterly（KPI 2,115/筛选/50 EDGAR 链）。**N 后端不引入**（W v2 覆盖）。

**X（/news）**：ab55f39→`17c4c10`。**抓出并修复 M 回收代码的阻塞级 bug**：normalize_seendate 长度检查 15 应为 16（GDELT `YYYYMMDDTHHMMSSZ`）——不修则 feed 永远为空（已提交测试抓到，X 修复后 8/8 绿）。fetch：GDELT IP 节流 429×2（6 请求退避）→ 冷却 5 分钟后单请求成功 = **200 篇/106 源/2 天窗**。前端：4 KPI+流表（标题仅链出原文，版权在出版方）+150 截断披露；i18n 键名偏离规格 nav.newsfeed（nav.news 已被新闻情绪 tab 占用——tsc TS1117 暴露，合理）。集成 3 冲突（图标×2 并存 + 双测试函数并存，其中一处 ======= 残留经语法检查修复后 amend）。

**终态**：17/17 路由在构建产物实证（含 /manager /stock SSG 目录）；news_feed.parquet 缓存拷主仓；data_health/api_catalog 统一再生。**三豁免维度业主裁决待定**（TACO 卫星/韩杠杆/书架）。worktree wx/wy 已清；M/N worktree 原样保留（并发领地）。

## 2026-08-23 (t) 并发 lane M/N 裁决 + 17 路由收尾轮（X/Y 代理）

**裁决依据**：M/N worktree 均为 08-22 02:2x 的两天前死亡 WIP（并发 session 早已离场）——并发纪律让位于 U 先例的回收裁决。**两者都有 `M runs/ledger.jsonl`**（旧基点 CRLF 假差异，基点早于 .gitattributes 修复）——回收时 `git checkout --` 还原，**绝不集成**。

**M（/news）**：WIP = GDELT artlist 文章流后端（news_feed.py 232 行——**复用而非重复** main 已有的 news_sentiment_gdelt.py：import 其端点/UA 常量，15s host 间隔）+ fetcher + export_news_feed + 17 测试 + 7-gate 文档；无前端。回收：ledger/workflow 还原后 salvage-commit `893fa6b`；cherry-pick 因函数体与 main 40+ 提交交错（6 冲突区含两个函数体交错）**不可行** → 改**外科手术**：函数体从 worktree 摘出 + 四处注册手工插入 = `09ee00a`。前端交代理 X（wx worktree，feat/news-frontend）。

**N（/quarterly+/annual）**：WIP 的后端（form_filing_stream.py 直查 10-K/10-Q）**已被 W 的 v2 统一流覆盖**（同机制同数据），路由壳 page.tsx 概念可借鉴（其 FilingStreamView 未实现）——**后端不引入**（避免双实现），改由代理 Y 在 main v2 面板上做导出深切（annual_filings/quarterly_filings cap 400）+ 两路由（wy worktree，feat/quarterly-annual）。N worktree 原样保留（并发 session 领地，仅读不改）。

**目标**：X+Y 集成后 17 条路由全部在线（news/quarterly/annual 补齐）→ 业主确认 TACO/韩杠杆/书架三豁免维度 → 差距地图即终态。

## 2026-08-23 (s) 三代理并行轮集成收官：U/V/W 全上 main（1974 passed / 1,494 页）

**U（举牌状态机，竞品王牌）**：死亡代理 WIP 裁决回收（c949061）+ 续作 ccdb8ed。**续作关键发现**：回收 JSON 里 pct 字段全 null——上轮解析跑在导出之后从未合并 → 离线重导出后 **13D 119/120、13G 150/150 真实比例**（12 清仓+17 降至线下 13D / 9+31 13G）。前端三类徽章（比例/主动被动/清仓降线，null 不渲染无占位）+ i18n 7×2 键 + 7-gate v0.2（请求账：13D 重建 82 + pct 解析 ~494，全 ≥2s）。集成：两 cherry-pick（8 JSON 冲突按惯例 theirs/ours 分治）+ **`git add -A` 误扫并发方 docs/code-review 一次，amend 剔除（6a448d2 教训再现，文件磁盘完好）** + 缓存拷主仓统一重导出（pct 在 main 复现一致）。

**V（DEF 14A 申报流，差距地图最后一项）**：b24b088。1,387 份/1,351 发行人/120 天（18 页 EFTS）；**修正实务发现**：DEF 14A/A 不存在（0 条），修正走 DEFA14A 独立 root form（2,278 条，v1 范围外披露）；75% 行解析出 ticker；600 可见/174KB；/executives Def14aSection + 契约测试 + 7-gate 文档；人级解析 DEFERRED（v1 边界）。集成零代码冲突（调用序一行合并）。

**W（统一申报流 v2）**：105f8ac。v1 派生合并 2,259 行/11 表单/4 天 → **v2 直查 EFTS 16,597 行/16 表单/12 天**（+10-K/10-Q 族）；表单 4 切分实录（2,769+3,427=6,196 去重验证）；**Schedule 13 冻结兜底**（EFTS 0 hits 复证 → 13D/13G 走每日索引线 3,182 行，探针保留测自愈）；140 页请求账；幂等复跑零请求。集成零冲突。

**三轮合体验证**：pytest **1974 passed**/9 skip + ruff 净 + tsc 0 + eslint 0 错 + build **1,494 页** + IAB：/smart-money 徽章实测（主动 30/被动 33/清仓 12/降至线下 7/(前值) 1/比例元素 101）、/executives DEF 14A 区（52 徽章）、/events v2 pills（10-Q/4/A）。**差距地图：P0/P1/P2/P3 全部维度已上线**；仅剩并发 lane /news /quarterly /annual（他 session 领地）。worktree 三清+任务文件归档随后。

## 2026-08-23 (r) 20:10 cron U 重派执行：死亡代理 WIP 裁决回收 + 三代理并行轮

**U 重派（cron automation-3684bc83 触发）**：前置核实——form4 已由主线收官（30 发行人 1,464 笔）；**13D cache 未重建**（主仓仅余旧 forward 文件）→ U 任务 1 有效。wu worktree 发现上一轮配额死亡 U 的**未提交真实 WIP**：`sc13d_daily_aggregate.json` 已重建 + `stakes_pct_parsed.json`（有界持股比例解析）+ `stakes_pct.py/runner/17 测试全绿` + 导出接线（pct_now/pct_prev/stake_status，19 处）+ barrel 类型——**任务 1-3 实为已完成**。裁决：WIP 整体提交 `c949061`（分支 feat/stakes-status），续作代理只做任务 4-5（smart-money-view 徽章三类 + i18n stakes.pct/status.* + 7-gate 文档）。

**并行布局**：V（DEF14A 流，wv/feat/def14a，规格 TASK-V）+ W（统一流 v2 直查 EFTS，ww/feat/filing-stream-v2，规格 TASK-W）已于 20:0x 派发。**三方冲突面**（export_terminal_data.py / test_web_terminal_data.py / dict.ts）已划界，集成顺序：U → V → W（主线逐个 cherry-pick 解冲突 + 全套验证）。规格两文件已提交 main（48bfa7b 后续）。

## 2026-08-23 (q) P2 收官：13F 申报人目录 /filers 上线（9,385 家 = 竞品同量级）

**路径考古**：browse-edgar **无法**无 CIK 按表单枚举（实测 `getcompany&type=13F-HR` 空 atom feed；裸 UA 403）→ 目录走 EFTS 季度窗（`forms=13F-HR` 扩展 +A，Q2-2026 单季 9,625 逼近 10k 上限）→ **自适应切分**（声明 total ≥ 9,500 即对半拆至 ~3 周地板；Form D 教训直接复用；本次四窗实际均未触发）。爬取 ~33 分钟（4 窗 × ~86 页 × ≥2.1s，幂等缓存）。

**数据**：**9,385 申报人 / 37,348 份申报 / 692 带修正 / latest 2026-08-21**（小隐寺 ~9k 同量级）。导出全量目录（1.6MB JSON）走**专用模块** `filers13f.ts`（form13f.ts 先例——绝不进共享 barrel，仅 /filers 页加载）。

**页面**：`/filers` 新路由（sidebar evidence 组 + 命令面板）——KPI（9,385/37,348/窗口）+ 名称/CIK 搜索 + 排序 pills（最新/申报数/名称）+ newest-first 表 + LoadMore；**明星 CIK 深链 /manager 详情页**（BERKSHIRE HATHAWAY 0001067983 双侧验证命中），其余链 EDGAR 13F 历史（browse-edgar 带 CIK 可用——无 CIK 枚举才不行）。13F-NT 排除披露（无持仓报告不算持仓申报人行）。契约测试：CIK 唯一/零填充 10 位/计数求和=total/窗口界内/newest-first。

**验证**：ruff 净 + pytest 数据契约绿 + tsc 0 + build **1,494 页（+1 = /filers）** + SSR grep（9,385×2/标题×3）+ IAB 结构（KPI/排序 pills/首行 Ashford/50 EDGAR 链/搜索框）。**IAB 输入桥本会话失效**（三种 type 签名均未触发 React 状态——同款搜索组件已在 /institutions 先前会话 IAB 验证过；数据与逻辑侧已静态证实，如实记录）。**差距地图 P2 全关；剩 P3 DEF14A + 并发 lane 三页**。

## 2026-08-23 (p) P2 统一申报流上线（六面板纯派生合并，零新抓取）

**交付**：`export_filing_stream()` 合并已提交六面板（4 / 8-K/A / S-1 族 / 424B4 / D/A / SC 13D/A / SC 13G）→ `filing_stream.json`（800 可见 / 2,259 合并 / 11 表单，newest-first）+ /events 页 StreamSection（表单 FilterPills + 分页，位于 8-K 深度流之上）。**合并卫生**：str(None) ticker、"申报人见原文"占位申报人、smart_money 的 http:// 链接——三者在 add() 源头归一化（占位申报人降级为目标公司；无主体行丢弃不留 "—" 占位行）；契约测试钉死三者不泄漏。13F-HR v1 排除（季度管理人持仓非公司事件，/institutions 已载）+ 源面板上限继承披露。**验证**：ruff 净 + tsc 0 + eslint 净 + build 1,493 页 + IAB（板块/表单 chips/下方 8-K 流共存/100 EDGAR 链）。

## 2026-08-23 (o) P2 Form D 一级市场流上线（EFTS 10k 上限发现 + 滚动窗累积模式）

**EFTS 上限考古（关键）**：首次 90 天探测（2026-05-25..08-23）请求到的命中被 EFTS **硬上限 10,000 截断**——恰好 10,000 份 = 仅最新 41 天（~244 份/天；`forms=D` 扩展 D 6,533 + D/A 3,467，9,400 发行人），旧约一月被截（非静默：日志与载荷双双披露）。修正架构：**滚动 30 天查询**（~7,300 < 上限留余量）+ parquet 聚合**跨运行累积**（accession 去重，stakes13g recent-stream 先例）；今日 capped 探测的 10k 行天然成为聚合的种子历史。

**交付**：`ingest/form_d.py`（复用 form_ipo 的 `_get_json`/`_parse_company`/`parse_ticker`/`_filing_index_url`；form→status：D=新申报/D/A=修正，不可变表单类型推导）+ `scripts/form_d_fetch.py`（滚动 30 天）+ `export_form_d()`（可见 600 最新 + by_form 计全量 + 方法学含 10k-cap 四号披露）+ /ipo 页 FormDSection（公司/表单徽章/申报日/EDGAR 链 + 新申报|修正 FilterPills + 分页；发行人多为私营 → ticker 空为常态）+ 契约测试（status-form 一致/newest-first/by_form 求和=total/methodology 含 not-extracted+display-only）。**v1 诚实边界**：募资金额/行业/关联人在主 XML 内不解析（~4,300 额外请求 deferred，每行链接 EDGAR 文件页）。

**验证**：ruff 净 + tsc 0 + eslint 0 错（2 警告皆 IPO 存量段）+ build 1,493 页 + IAB 抽查（板块/10,000·9,400 计数/筛选 pills/ImpactMatrix 首行/原 IPO 流 424B4 共存）。

## 2026-08-23 (n) P1 ApeWisdom Reddit 热议榜上线（复测修正两处误判 + 分页失效如实披露）

**复测修正（业主指令"工作日复测后开建"——同日即完成）**：① 上一轮"周日 count=0 属诚实空窗"的推断**半错**：`filter/all-posts`/`filter/crypto` 空是**口径**（今日仍 0），而 **`filter/stocks` 实时有数据**（NVDA 居首，envelope 声明 count:290/pages:3）——正确端点一旦命中即为真实榜单，无需等工作日；② 首版 fetcher 跑出 300 行/200 重复 rank 的"漂移"诊断也**错**——真相是**免费 API 分页已死**：`?page=N` 与路径 `/N` 全部回 `current_page:1`（浏览器逐一验证），300=3×第 1 页。

**诚实架构**：ingest 信封 `current_page` 回显检测（请求页≠回显页 ⇒ 翻页失效即停）+ `(rank,ticker)` 跨页去重 + `served_pages`/`pagination_ok` 字段 → 面板头"100/290" + 尾注披露"声明 290 仅服务第 1 页，如实呈现不补全"。**交付**：`ingest/ape_wisdom.py` + `scripts/ape_wisdom_fetch.py`（≥2s）+ `reddit_trending.json`（第一方字段 verbatim：rank/ticker/name/mentions/upvotes/24h 双滞后可 null）+ /reddit TrendingSection（rank/提及/24hΔ 上色，**与自有 Atom 采集面板独立共存**——不依赖其 live 状态）+ i18n zh/en + 契约测试（rank 严格升序/无重复 (rank,ticker)/pagination_ok=False ⇒ n_rows<count_declared 且方法学含 "page 1"/display-only+never-PIT 边界）。

**验证**：ruff 净 + tsc 0 + eslint 净 + build 1,493 页 + IAB 抽查（标题/NVDA+NVIDIA/IONQ/100/290 计数/采集状态卡共存）+ 数据测试全绿。差距地图 V1/V2 已更新为"管道已建"，P2 下一项 = Form D。

## 2026-08-23 (m) P1 ARK 家族面板上线（官方 CSV ingest + /institutions 板块）

**端点考古（关键）**：ark-funds.com 基金页是 **JS 壳**——requests 拿到的原始 HTML 无 CSV href（全 "--" 占位）→ 8 只 ETF 的官方直链经**真浏览器逐页提取 live DOM** 后钉入 `src/aionis/ingest/ark_holdings.py::FUND_CSV_URLS`（链接结构=API 配置读一次固定；**数据永远来自 ARK 自己的 CSV 端点**）。名字含不可猜标点（`TECH._&_ROBOTICS`）+ 两处 2025 更名（ARKF→Blockchain & Fintech、ARKX→Space & Defense）——若再改名将以 per-fund FAIL 如实暴露。旧 `wp-content/uploads` 模式已 301 废弃。

**管道**：`ingest/ark_holdings.py`（parse_csv + fetch_all，进程级 HttpRequestPolicy ≥2s）→ `scripts/ark_holdings_fetch.py`（薄 runner；快照落 `data/cache/ark_holdings/<TICK>_<YYYYMMDD>.csv`——**ARK 官方不留历史，本地日快照=时间序列**）→ `export_ark()`（最新快照/基金；top10 权重 + family overlap ≥2 基金同持）。**诚实跳过已计数**：尾部免责声明 footer 行（整段落进 date 字段——首版 fetcher 全 8 基金 ValueError 的根因，改 `_DATE_RE.fullmatch` 守卫）、无 ticker 的 warrant/unit 行、CASHX 现金行。

**实测（2026-08-21 盘后快照）**：8/8 基金 331 仓位（ARKK 44/IZRL 65…）；家族共振 top：AMD/PLTR/AMZN/NVDA 各 5 基金同持，TSLA 单基金最高权重 10.05%（ARKK 9.24% 居其 top1）。视图 `/institutions` ArkSection：8 基金卡（top5+权重条）+ 共振表；ticker 仅在 STOCK_PAGE_TICKERS 内链接（该守卫自 manager-book 导出共享）。

**验证**：ruff 净 + pytest 契约绿（权重降序/overlap≥2 基金且基金集=导出集/跳行披露）+ tsc 0 + eslint 净 + build 1,493 页 + IAB 结构抽查（标题/共振卡/8 卡/9.24%/AMD ×3/伯克希尔卡共存）。

## 2026-08-23 (l) 复刻差距地图 + 政党对立指数上线 + R form4 收官

**源验证（IAB 一手实测，三网页工具当日配额尽的替代路）**：ApeWisdom 免费无鉴权 JSON API = **apewisdom.io**（`.com` 域名连不通是此前 403/超时根因；`/api/v1.0/filter/all-posts` 周日实测 count=0 属诚实空窗，**工作日首测真实数据后才建管道**）；ARK 8 基金日度持仓 CSV 官方直链 = **assets.ark-funds.com/fund-documents/funds-etf-csv/{FUND}_{TICKER}_HOLDINGS.csv**（自 ARK 页 "Full Holdings CSV" href 提取；旧 wp-content 模式已 301）。差距地图 `reports/design/2026-08-23-replication-gap-map.md` 定优先级：P1 = ARK 面板 + ApeWisdom Reddit 榜（源已验证待建）、P2 = Form D / 统一申报流 / 13F filer 目录（EDGAR）、P3 = DEF14A 人级档案；不追 TACO/韩杠杆/书架（已记决策）。

**政党对立指数 + 两党跟单组合（P0，纯派生 0 新抓取）**：`party_index.json` ← politician_trades_tx.json（executives 同款 _dh_read derived 模式）。月度序列 26 个月：每 ticker 双方净方向（买−卖计数）反号占比（分母=双方均有净方向的共同标的，无则 null；**计数加权**——PTR 仅法定金额区间，美元加权=编造精度）；headline 月取最新非 null 月（稀疏当月诚实 null 不删行）。近 90 天两党净买 top10 = 信号清单（ticker/asset/n_buy/n_sell/net_buy/n_members，**无价格无收益**，方法学明示 display lane）。视图 `/congress` PartyIndexSection：近 12 月表（D/R 买占比+对立条形+分数值）+ 最新对立/共识 chips（D/R 净向带党色）+ 两党组合双卡（PartyBadge+KPI+top10 行）——置于申报流之上（分析层在原始层之上）。契约测试 = **全量重算对账**（月度计数/分式上下界与重算值 5e-4/opposed 反号/consensus 同号/top10 逐 ticker 与 (net_buy↓, n_buy↓, ticker↑) 排序键一致/窗口 90 天锚定 max transaction_date）。

**R form4 收官**：后台 fetch 跑满 **30 发行人 1,464 笔 2026 交易**（intc 收尾），export：recent 200（23 ticker 全带 doc_url）+ 14 年 yearly 逐字保留（合计 16,636 笔）+ window 2013..2026；**披露修复**：宇宙同宽时输出 "unchanged at 30 issuers"（原逻辑无脑拼 "widened from X to Y" 产出 "30 to 30" 谬文）。data_health/api_catalog 同步再生（party_index 入册 _DH_DAILY + _API_LICENSE）。

**验证**：pytest 全绿 + ruff 净 + tsc 0 + eslint 0 错（6 警告全为存量 TxSection/CongressView 段，非本轮引入）+ build **1,493 页** + SSR grep（两卡标题/条宽 25–50% 与月值吻合）+ IAB 客户端元素计数（两卡×1/2026-06 行/0.67/PANW×2）。截图子系统本轮超时不可用（结构性验证替代，已如实记录）。**未 push**（Actions 计费阻断，业主指示后面解决）。

**待办**：U 20:10 cron 自动重派（单代理，监督即可）；P1 ARK/ApeWisdom 管道（工作日首测）；M/N 并发 lane 未动。

## 2026-08-23 (k) S 收官：并发实现合流裁决 + 交易级面板上线 main（a9071cb）

**并发合流**：并发 session 于 15:14 在 ws 分支提交右锚定 PTR 实现（`4e4eb11`：salvage 移植 + 右锚定行解析重写 + fetcher/export 全接线/前端视图为共享工作树 WIP）。20 份样本对垒：**并发 218 笔/97.8% vs 主线左锚定 45 笔/60%**（并发版还修复自报行丢失）→ 主线撤回重复实现（`79902e7`），并发版胜出（08-22 H 先例纪律）。**注意**：主线 6a448d2 "style" 提交曾用 `git add -u` 把并发方的 WIP（views+export 接线）误扫入 commit——内容真实、标签错位，已在 state 记档不改史。

**主线推进的共享状态**：跑并发 fetcher 2026 全量（**361 PDF = 299 可解析 → 2,812 笔/94 议员/379 迟报>45 天** + 43 no-text + 33 exchange + 54 失败，全诚实计数；361 PDF 全部复用主线批跑下载的缓存——主线网络工作未白费）→ export 再生 → i18n 缺键补齐（congress.tx.* 16 键 + stock.politician.* 4 键，zh/en）→ 契约测试（方向枚举/days_late 一致性/by_party 求和）→ 7-gate 交易级段 → **merge 进 main 零冲突**（P 侧栏与 S 交易区共存）。

**验证（全绿）**：pytest 全套 0 失败 + ruff 净 + tsc 0 + eslint 净 + build 1,492 页 + IAB 抽检 7/7（/congress 交易区 2,812 计数/方向 pills/⚠ 迟报/侧栏共存；/stock/T 政客卡+交易行+全部出口）。本地服务已停。

**进行中/待办**：R form4 fetch @ ~21/30（XOM，1,230 笔）——完成通知唤醒后收尾导出；U 由 20:10 cron 重派（已改为仅 U）；TASK-S 已标记完成存档。

## 2026-08-23 (j) S 主线预跑：salvage PDF 栈复活 + 20 份真 PDF 验证 + 2026 全量批启动

**S 的最高风险部分已由主线完成**（ws worktree，feat/ptr-transactions 分支）：salvage `agent/politician` 的 PDF 栈提取为独立模块 `src/aionis/ingest/ptr_pdf.py`（纯 stdlib：ISO 32000 RC4 密钥派生 + ToUnicode CMap 文本恢复 + 流式行正则）+ runner `scripts/ptr_transactions_fetch.py`（年份分批、幂等 DocID cache、三分类计数）。**20 份真 PDF 抽样：12 ok（45 交易行，PFE/OGN/ABT/GOOGM 等真 ticker）**；6 no_rows = 2 字节 CID 字体部分 cmap 缺映射（NUL 损失，`$200?` 残迹——NUL 剥离验证不可救，诚实计数不猜）；2 no_text = 扫描件。**2026 全量批（359 份）后台 fetch 中**（house.gov，与 sec.gov 的 form4 fetch 不同 host 并行礼貌安全）。修复插曲：一次批量改名误伤 fonts_from 循环变量导致提取退化（45→5 行），从首个 commit 重置后行号级外科修（E501+B007），ruff 净 + 抽样复验 20/20@45。TASK-S 文件已更新（接手者只剩任务 4-7：导出面/前端/测试/7-gate）。

**并行状态**：form4 fetch @ ~17/30 发行人（968 笔）；T 已完成；U 待 20:10 cron。

## 2026-08-23 (i) 主线接管 T 完成（配额未重置期的第二块主线工作）

**T（manager 页对齐，`f0fbc9c`）**：① **数据可得性通过**——form13f_aggregate.parquet 实为全持仓（131,020 行；BRK 单管理人 179 行跨季），非只有 top10；② 导出 `top10`→**`positions` ≤50**（可见持仓簿）+ changes ≤20，coverage **285/398 → 1,181/1,580**；③ **form13f 移出共享 barrel**（form13f.json 100KB→653KB，照 stock-universe 先例独立模块 `web/src/data/aionis/form13f.ts`，五消费方改导入——+550KB 不再摊到每个页面）；④ manager-view 双 tab（当前持仓=PositionsTable+**前 6 大集中度条形 widget**（按可见持仓合计口径+脚注）/ 调仓=四态 KPI 计数+Δ市值芯片）；⑤ institutions 管理人搜索（name/中文别名/CIK 子串，诚实空态）。验证：pytest 全套 0 失败 + ruff 净 + tsc 0 + eslint 净（build 留待与 R 收尾同批跑）。wt worktree 清、分支删。

**进行中**：R 的 form4 fetch 后台运行（763 笔 @ MRK≈第 15/30 家）；S/U 由 20:10 cron 重派（已更新为只派 S+U）。

## 2026-08-23 (h) 第三轮四代理配额团灭 → 主线接管 R + S/T/U 定时重派

**四代理齐死 [1308]**（15:21 派发即灭，重置 19:55:48）：R insiders 广度 / S PTR 交易级 / T manager 对齐 / U 状态机。worktree wr/ws/wt/wu 已建（junction 已挂）。

**主线接管 R（已提交 `6fa0e95`）**：form4_fetch ISSUERS 5→30（CIK 全部复用 form8k v2/v3 已核实条目）+ `--start YYYY-MM-DD` 有界窗参数；export_form4 **retain-merge**（smart_money 先例：已提交 2013-2025 yearly 逐字保留、2026 由新 parquet 重算、宇宙差异 methodology 披露 "universe widened from 5 to 30"、buys/sells 与合并 yearly 自洽）；2 回归测试（14 年保留断言 + 无 committed 时全新写）；7-gate form4 文档 v2 账。**fetch 后台运行中**（runs/form4_fetch_v2.log，2026-01-01 窗口、逐发行人 checkpoint；完成后主线被任务通知唤醒做导出验证收尾——form4.json 将得到 recent 200 行 + doc_url 全生效 + window 2013-03..2026-08）。

**S/T/U 定时重派**：规格文件 `tasks/active/TASK-{S-ptr-transactions,T-manager-align,U-stakes-status}.md`（自包含，含铁律 #0 绝不爬小隐站）；CronCreate automation-3684bc83 定时 2026-08-23 20:10 自动重派三代理并集成。**S 是最高优先**（PTR 交易级 = 竞品王牌，salvage 分支 agent/politician 解析器复活）。

**注意**：13D cache 重建（TASK-U 任务1）未做——若主线在 fetch 完成后有空档可串行跑（与 form4 fetch 同 host 需串行礼貌）。R 的 fetch 预计数小时（Form 4 每份 XML ≥2s）。

## 2026-08-22 (g) 守卫加固 + P/Q 代理第二轮：events 50 发行人 + 展示快赢四件 + CRLF 根治

**主线守卫片（`60ee8b0`）**：五导出器退化守卫（picks 三件套/sector 两级[model-empty 不再写 awaiting 覆盖 + 覆盖坍缩 <50% 保留]/model_health/calibration_reliability/stock_universe）+ 共享 `_committed_json`/`_skip_retain` + 5 hermetic 回归测试。**实战验证**：同一缺 cache 条件重跑导出，08-22 曾清空的 7 面板全部保住（20/1421/111/2/2/2）。export_picks 守卫返回 None 连带 main 跳过 export_metrics（防止降级 hero）。

**代理 P（展示快赢，4 commits 全成）**：① insiders/top_insiders 头像缩写（新共享件 `stream/avatar-initials.tsx`，姓名首字母 ≤3，项目 token 无硬编码色）② ipo 侧栏诚实替代 widget（by_form 徽章 + 最近定价 Top5 + "v1 不解析募资额"注记；lg 断点防 5 列表被挤）③ congress top_members 侧栏卡（头像缩写+office+×count；**party 字段数据里没有——诚实不加**）④ manager 调仓 Δ市值：`compute_changes` 帧差本就保留两侧 value——补 `delta_value` 输出+导出+类型（暂可选字段，重导出后可收紧）+ ChangesBlock fmtUsd 芯片 + 契约测试（只在可证处断言；价格漂移可反号不硬钉）。

**代理 Q（events v3，3 commits 全成）**：25→**50 发行人/51 CIK**（新 25 家全经 cik_resolver 快照实解+实体名核对；DD=DuPont de Nemours、GE=GE Aerospace 披露）；真拉取 **203 份申报/0 跳过/0 错误**（v2 缓存 0 请求重放 + 新增 225 礼貌请求 ~13min）；executives 联动 **44 份/29 发行人**；AXP 5 份 unclassified 诚实入账。7-gate v3 账。

**主线集成**：7 commit 零冲突 cherry-pick；补 Q 遗留（form8k methodology "25"→"50" + 注释）；Q 的 form8k cache 拷回主仓重导出（203/50 + delta_value **395/395** 全量生效）；**`.gitattributes` 钉 `runs/*.jsonl eol=lf`**——根治两个代理都撞上的 worktree CRLF→ledger pin 假阳性（M 误诊同源）。

**验证（全绿）**：pytest 0 失败 + ruff 净 + tsc 0 + eslint 净 + build 1,492 页 + IAB 抽检 5/5（头像缩写渲染 `generic "AJ"`、ipo 侧栏、congress 侧栏、events 203+ORCL/COST、manager +$ 芯片）。worktree wp/wq 清理（junction 先摘）、分支删、服务停。

**遗留池更新**：form4_fetch 重跑（doc_url+200 行）与 13D cache 重建仍待（等 Actions 或长跑）；13G 状态机/events 更广/executives 人级/congress 交易级（D4 门）；M/N 在途不碰。**未 push**（计费阻断）。

## 2026-08-22 (f) 四代理军团轮（业主指令"按优先级驱动子代理"）：J/K/M 全交付 + L 死而复生 + 主线集成上线

**编排**：P0 提交为干净基线（`8357c28`）后，四 worktree 并行（兄弟目录 Aionis-wj/wk/wl/wm，junction 只挂 node_modules）。优先级 = J 导出扩容 > K executives > L events 广度 > M 13G。

**四代理结局**：
- **J（导出扩容）全胜**（`d927bec`）：congress 100→**874 全量**（+240KB）、ipo 150→**1046 全量**（+257KB）、form4/smart_money 上限 200/120（**JSON 未再生成——主仓无 form4_aggregate/efts_13d cache**，下次 fetch 后自动生效，测试用范围钉兼容）；**insiders doc_url 数据可得性通过**（parquet schema 实查含 accession+filer_cik，代码+类型+UI 已就绪，同因缺 cache 待再生效）；顺手修 `export_macro_drivers` 缺 cache 时静默覆写 live 面板的隐性回退 bug（retain-on-absent 守卫）。
- **K（executives）全胜**（`7661fd5`+`d413d7f`）：8-K Item 5.02 officer_changes 派生面板 + /executives 路由 + 公司筛选 pills + 侧栏入口 + zh/en i18n + 契约测试；诚实边界 = 申报流级（person-level extraction DEFERRED 写进 methodology）。
- **L（events 广度）死于配额但代码幸存**：17:09 [1308] 阵亡、报告丢失，但 16:25 已提交 `f4de1da`（5→25 发行人 + XOM 双 CIK 特例处置 + 导出上限 300 + 一致性测试）——**分支对象在共享 .git 幸存，主线 cherry-pick 后接管剩余**：7-gate 文档补 v2 礼貌账、真跑 25 发行人有界 fetch（**103 份申报/25 发行人/0 跳过**，~30min），executives 联动增长至 **20 条/15 发行人**。
- **M（13G 流）全胜但有一处误诊**（4 commits）：**关键发现 = EFTS 对 SC 13 家族冻结于 2024-12-17**（13G 同 13D 的墙），改走 EDGAR daily crawler index（`stakes_13g.py` + 7-gate 文档三处披露）；真拉取 120 天窗口 **15,982 份**（13G 7,419 + 13G/A 8,563）、ticker 解析 134/150、真实 filer 128/150；smart-money 加 13G 被动流卡（FilterPills+分页）；状态机（持股比例/清仓）deferred。**误诊**：M 把自己 worktree 的 ledger CRLF 检出假阳性误诊为"stale pin"并错误重钉（`082b8f1`）——主线用 `git cat-file blob` 字节级裁决（HEAD blob = `44157b5b…` = 现行 pin，2e2ab30 是 08-09 历史提交），**该 commit 剔除未集成**。

**主线集成**：J→K→M×3→L 六 commit cherry-pick（api_catalog/data_health 两处生成物冲突取侧后统一重导出）→ 统一 export → **降级审计揪出 7 个受害面板**（stock_universe 1421→0、calibration/model_health/picks_meta regions→0、sector_breakdown 111→53、picks 20→0、shorts 5→0——本地缺研究侧 cache 且这些导出器**无 retain-on-absent 守卫**，J 只补过 macro_drivers 一个）→ 全部从 HEAD 还原 + 只重跑 data_health/api_catalog 两个汇总器（32 面板/32 端点一致）→ **守卫缺口记为跟进片**（stock_universe/calibration/model_health/picks_meta/sector_breakdown/picks/shorts 七处补 J 的同款守卫）。

**验证链（全绿）**：pytest exit 0 + ruff 净（--exclude docs/code-review）+ tsc 0 + eslint 净 + build **1,492 页**（+/executives）+ IAB 抽检三页（executives 20/KPI/pills、events 103+JPM+META+全部103 pills、smart-money 13G 卡 15,982 + 13G·A pills）。本地服务已停；四 worktree 按"先摘 junction 再删目录"铁律清理、四分支删除（M 的错误重钉随分支消亡）。

**未提交状态**：`108ff22` 已 commit（集成数据 + 7-gate 文档）；**未 push**（部署仍停摆中——GitHub Actions 计费阻断未解，blockers.md 首条）。

**遗留池**：(a) 七导出器 retain 守卫跟进片；(b) form4_fetch 重跑（doc_url + 200 行生效）+ 13D cache 重建（smart_money 120 行生效）；(c) M/N 在途（news/quarterly/annual）不碰；(d) P2：13G 状态机、events 更广宇宙、congress 交易级（D4 门）。



## 2026-08-22 (e) 小隐寺对齐 P0 实施交付（业主 GO + 硬条件"必须真的读懂"）——先复核订正再动手

**浏览器复核（业主要求的前提）**：IAB 实测 18 页中的存疑页 + 截图→视觉模型 + getComputedStyle DOM 实测。**订正两处误判**（此前 WebFetch 抓的是 SSR 首帧，"数据暂不可用"是客户端取数前占位）：① **/events 实为全市场 8-K 实时流**（波音/诺格/微盘股全谱、分钟级时间戳、公司+类型+时间三处 EDGAR 直链、12+ 中文类目多标签 `·` 连接）——非空壳，"Aionis 领先"表述作废，改为"追赶广度"；② **/annual 有 102 份 10-K 流**。真空白 = /quarterly /companies /势力阵营 /stock 机构持有者 四处。视觉实测：暗色 OLED 黑底（body rgb(0,0,0)）、GeistSans/GeistMono、党派徽章 = 美式浅底填充（D 蓝字 `rgb(71,168,255)`/蓝底、R 红字 `rgb(255,86,95)`/红底、10px/600/4px）、方向徽章绿买红卖、吸顶表头、行高 ~40px。两份方向文件（realtime-deployment §6/§8 + granularity-alignment §4/§10）与 state 旧条目已同步订正留档。

**P0 交付（全部 display 层，0 ledger/frozen/OOS）**：
1. **`web/src/lib/format.ts`（新）**：fmtUsd/fmtShares/fmtInt/fmtDateShort/fmtEmpty 统一格式层（$T/B/M/K、MM/DD 短日期、空值 —）；manager-book 改 import+re-export（单一事实来源）。
2. **`web/src/components/stream/stream-kit.tsx`（新）**：FilterPills（枚举筛选+诚实计数）+ LoadMoreFooter（"shown / total" 计数行）+ usePaged（筛选变更自动重置分页）——/companies 交互模式泛化为共享件。
3. **五面板接线**：congress（党派筛选 全部100/共和56/民主39 + 浅底党派徽章 PartyBadge 蓝/红 tint + 50/页分页）、insiders（买/卖筛选+分页+计数头 "16,564 · 2013-03..2026-08"）、ipo（状态筛选+分页）、events（类别筛选按 by_category 排序）、smart-money（新持仓/修正筛选+分页）；流式行日期全部 MM/DD 化（title 悬停保留 ISO）。
4. **SegmentHeader `countHint` 槽**（xiaoyinsi P1 页头计数+窗口惯例）：congress/events/ipo page.tsx 接真实面板数据组合串。
5. **/stock 机构持有者模块（反超点落地）**：form13f 40 管理人 top10 按 ticker 反查 →AAPL 实测 8 家（伯克希尔 $66.0B/227.9M 股/81.8% 居首 → 段永平 $7.8B → AQR/Two Sigma/Caxton/索罗斯），Link /manager/{cik}，pct 按本页合计口径+脚注，空态诚实（"不在任何策展管理人前十大"）；**小隐寺同位是空壳"共 0 家"**。
6. **文案债修复**：insiders.window 去掉硬编码"近 2.5 年"（实际 2013 起），窗口改由计数头动态呈现。
7. i18n：zh/en 各 +27 键（stream.*/congress.party.*/insiders.filter.*/ipo.filter.*/events.filter.*/smartmoney.filter.*/stock.holders.*）。

**P0-5（insiders 行级 EDGAR 外链）降级为跟进项**：form4.recent 行无 accession/doc_url 字段（实测 JSON），需导出端从 orchestrator 缓存补 doc_url + 契约测试字段集更新 + 本地重导出——单独小片，未混入本轮。

**验证链（全绿）**：tsc exit 0 + eslint 0 error + `pnpm build` 1,491 HTML 全导出（Next 16 扁平 `<route>.html` 布局，非 `<route>/index.html`——本地静态服务要用 .html URL）+ 全套 pytest exit 0 + IAB 浏览器实测三页（党派点击 → "50 / 56" 计数实时变化、AAPL 持有者卡全渲染、insiders 全部50/买0/卖50 诚实计数）。本地 http.server 已停（端口 8765 双进程均已 kill）。

**边界与未提交**：纯 web/src display 层 + state + .gitignore（runs/xys-design/ 截图证据目录）；0 ledger/frozen/config/prereg/OOS；0 导出端改动（纯前端+既有 JSON）；**未 push 未 commit**（工作树另有并发 session 的 docs/code-review/ 不碰；提交时机由业主/并发 session 协调）。M/N 在途模块未触碰。

**遗留（对齐阶梯后续）**：P1 导出扩容（congress 100→874 全量、ipo 150→1046、insiders 50→200、smart-money 60→120 + 契约测试同步：`==60` 精确钉改范围钉）；P1 党派浅底徽章已随本轮落地；P2 抓取端（/events 广度追赶、13G、executives、交易级 D4 门）；insiders doc_url 跟进片。

## 2026-08-22 (d) 小隐寺颗粒度对齐方向文件（display lane 主线回归；基建线按业主指令搁置）

**业主定帧**："先暂时不要管这些（基建），先去跟小隐寺对齐颗粒度，学会该网站的数据呈现与 UI 设计。"

**交付**：`reports/design/2026-08-22-xiaoyinsi-granularity-alignment.md`（双代理深研合成：小隐寺 18 页设计级逐页解剖 × Aionis 视图/JSON/契约测试代码级盘点）。
1. **小隐寺十模式提炼**（P1-P10）：页头副标题内嵌计数+时间窗、KPI 前置、侧栏聚合 widget、筛选全 URL 化、40-50 行分页+区间计数器、数字/日期/空值三统一（$T/B/M/K + 三粒度日期 + 空值 —）、徽章分类学（三套方向体系 + ⚠ 迟报>45天 + 状态机）、行级深度交互（整卡 EDGAR 链/折叠块/头像缩写）、空态列头先渲染、方法学脚注。
2. **Aionis 硬差距实锤**：六个流式面板全部无筛选/无搜索/无分页（可见行 = 导出上限：congress 100/874、ipo 150/1046、insiders 50/16,564、smart-money 60、events 23、reddit 7；上限源头 export head()）；仅 /companies 有完整交互三件套（模式已验证，缺移植）；无统一格式层；insiders 行级无 EDGAR 链；/stock 缺机构持有者 join（form13f 数据已就位，小隐寺同位空壳=**反超点**）。
3. **设计定帧**：**小隐寺的骨架 × Aionis 的皮肤与溯源**——学信息设计（P1-P10），保 Apple HIG token/WCAG/--up-down 约定/双语/ProvenanceBadge/NullDisclaimer；不学其已知瑕疵（双视图 DOM 冗余、KPI 与列表窗口口径不一致、徽章中英混用、空承诺、零溯源零暗色）。
4. **实施阶梯**：P0 五片（格式层 lib/format.ts + 三件套移植五面板 + 页头计数窗 + stock 机构持有者 join + insiders EDGAR 链）→ P1（导出扩容 congress 874/ipo 1046/insiders 200 + 契约测试同步【smart_money ==60 精确钉改范围钉】+ 徽章深化）→ P2 抓取端（13G+状态机、广度、executives、reddit 深度、congress 交易级=D4 门）。M/N 在途模块不碰。
5. **文案债顺手修**：insiders dict「近 2.5 年」vs JSON window 2013-03..2026-08 不一致（P0-1 片内）。

**待业主**：GO P0（建议两批代理或主线直做）；设计定帧确认（若要连皮肤也同构=独立 token 重构，需明示）。

**边界**：纯方向文件 + state；0 代码改动；display lane。

## 2026-08-22 (c) 实时化部署架构方向文件（基建 lane，PROPOSED）— 未实施，待业主 D1-D6

**业主命题**：重新设计方案优化/替代 GitHub Pages（实时数据更新不可达）+ 以 data.xiaoyinsi.com 为终局形态深探发展方向。与 feature lane（08-21 roadmap、(a)(b) 两轮模块）互补：本文件管"数据如何不再被构建冻结"。

**交付**：`reports/design/2026-08-22-realtime-deployment-architecture.md`。核心结论：
1. **根因不是静态宿主，是数据-构建耦合**——30 面板 JSON `import` 进 bundle，部署即固化；日更面改运行时拉取后，留 GH Pages 也能实时。五层根因（R2 核心 + R4 Actions 计费单点 + R5 日更 JSON rebase 冲突）一并被方案吸收。
2. **推荐架构 = 双平面**：CF Pages 托管静态 shell（git 集成自有 CI，与 GH Actions 计费解耦）+ 新 `workers/data-gateway`（R2 存 panels/streams + Cron 分钟级抓取 EDGAR/Reddit/house.gov + `PUT /admin/panels` 供 Python 管线上传，Bearer token）。前端唯一实质改动 = `usePanel()` hook（60s 轮询 + 内嵌快照兜底，Worker 挂 = 降级到现状永不更差）。**冻结 15 面板故意留 bundle**（不可变语义物理化）；prices Worker 原样不动。否决 Vercel SSR 重构（Hobby 禁商用 + 1,421 SSG 特化损失）与自托管 VPS。
3. **迁移阶梯 P0-P5**：P0 修计费/本地 runner → P1 gateway 双写 → P2 逐面板切 hook → P3 宿主切 CF Pages（验收 = 暂停全部 GH workflows 后 push 仍上线）→ P4 分钟级流（/events /insider /stakes /ipo）→ P5 停日更 JSON git 提交（rebase 冲突根除）。**最小改动 = 只做 P1-P2 即解实时性**。
4. **17 路由复核**（22 页实探；⚠️ 08-22 晚 IAB 浏览器复核订正：/events 实为全市场 8-K 实时流、/annual 有 102 份——WebFetch 抓的是 SSR 首帧，"数据暂不可用"是客户端取数前占位；**真空白仅 /quarterly /companies /势力阵营 /stock 机构持有者四处**）；填壳优先序已按 M/N 半成品（Aionis-m/Aionis-n worktree）校准——executives（form8k 加 Item 5.02 分支，无人做可新起）与 /stock 页 join 是仅剩的两个零依赖快赢；/events 转为"追赶广度"（对方全市场 vs 我方 5 发行人）；/congress 交易级 = 解封 `agent/politician` salvage（813 笔解析器）；**不追**：卫星 TACO / 付费行情 / 8.7K 全量目录。
5. **战略**：小隐寺卖数据速度（Vercel/RSC/SSE/采购源），Aionis 护城河 = 每个数字带出生证明 + US/CN 双区 + 可证伪；速度可追平、认识论完整性它结构上追不了；**E3 forward-live 战略权重上升**（唯一"模型读数实时且不可回改"的差异化，仍守 GO 门）。

**业主决策 D1-D6**（文档 §9，§10.4 修订）：D0 修账单辨根因（新增前置）｜D1 GO P1-P2？D2 迁 CF Pages？D3 可见性与成本解耦（重述）｜D4 解封 politician salvage？D5 E3 GO？D6 自定义域名？

**同日进展（暂停 + 免费方案全景 + Vercel 专论）**：① 业主指令"先暂停相关的 GitHub Action"→ 已停用 `Deploy Static Site to GitHub Pages` + `Refresh terminal data`（`disabled_manually` 实证；`E3 Forward Commit Trigger` 0 runs 保留 active；处置与恢复命令记 blockers.md 首条）；② 文档 §10 新增免费方案全景矩阵（官方+社区双源核实，2026-08-22）——**关键修正：账单封锁是账户级的，连公开仓库也挡（社区多帖实证），"转 Public 免修账单"不成立，修 Billing 是一切方案的前置（D0）**；CF 静态资产请求免费无限 + CF Pages/Netlify/Deno 私有仓库全兼容 → **通用推荐栈 = 本地 `next build` + `wrangler deploy`（CF Worker+静态资产）+ data-gateway（R2/Cron）+ 四个可互换免费 runner（本地任务/self-hosted/Oracle Always Free ARM 2C12G/公开仓库 Actions）**，对仓库可见性、CI 平台、GitHub 账单状态三重免疫；self-hosted runner 有 2026-03 平台费官宣（延期中）政策风险，不作唯一依赖。③ 业主问"参考小隐寺用 Vercel"→ §10.7 专论（vercel.com/pricing 直抓核实）：**能用**——Hobby 禁商用是唯一根本约束（Aionis 当前个人研究合规）；Hobby cron 仅 2×每日精度（分钟级抓取不可能，留 CF）；4 CPU 小时/月是 SSR 天花板；硬上限不可加购（无意外账单）。**三阶段路径 V0 静态直部（零改动半天）→ V1 gateway 实时（宿主无关）→ V2 去 export 渐进 ISR/RSC 复刻形态（Vercel 独有优势，CF 需 OpenNext）**；数据层仍外置 CF R2；"先 Vercel 后决"非单向门（V0/V1 平台无关）。D2 修订为三选：GH Pages（公开）/ CF（免疫优先）/ Vercel（形态优先，商用分岔后置）。④ 业主再定帧"只求部署 + 数据自动爬取更新，$0，日更可接受"→ **§11 极简三阶梯**：阶梯 1 = 本地 Windows 计划任务（StartWhenAvailable 错过补跑）跑 `update_and_deploy.sh`（refresh YAML 的本地转写：fetch→export→build→部署），部署主路 = **Pages 切 "Deploy from a branch" 模式（gh-pages 直推，0 Actions 分钟，绕开计费锁）**、兜底 = `wrangler pages deploy out`（与 GitHub 无关）——半天工作量、零新账户、与 D0-D2 全解耦；阶梯 2 = CF Worker Cron 分钟级抓 EDGAR 族+Reddit 写 R2（$0，只动 5-6 个流面板）；阶梯 3（可选）= Oracle 免费 VM 去 PC 依赖。**爬取实时性上限 = 源节奏**（COT 周更/13F 季更/宏观日更，基建无法改变）。⑤ 业主指令"去掉对 PC 开机的依赖，深度调研"→ **§12 十方案矩阵**（官方文档直抓核实）：⭐正选 **Oracle Always Free ARM VM**（2C/12GB/200GB，零管线改造；**闲置回收判据已取得原文** = 7 天窗口 p95 CPU<20% 且 网络<20% 且 内存<20%，任一不满足即安全——驻留 ~2.5GB 内存服务或把分钟级 EDGAR cron 放同机即免疫）；⭐次选 **GCP Cloud Run Jobs**（免费档 240k vCPU-s + 450k GiB-s/月 vs 需求 162k/81k = $0.00 有余量；需绑卡+预算告警；镜像须 slim 防 Artifact Registry 超 0.5GB 免费档；缓存外置 R2）；**Codespaces 免费配额不受账单锁影响**（官方：仅配额耗尽后才需有效付款方式；120 核时/月 vs 需求 33）= 即刻可用的过渡位。CF Containers 需 Workers Paid $5/月（公告记忆，官方页抓取被内容过滤拦，复核前按排除处理）；Serv00 等 BSD 免费主机因无 pandas wheel 排除。**D3 实质作废**（去 PC 依赖不靠修 GitHub 账单）；新增 **D7 runner 选型**（Oracle/Cloud Run/Codespaces 三选，设置件由我出）。runner 是可插槽：`update_and_deploy.sh` 三处同一份 bash，切换零管线改动。

**边界**：纯方向文件 + state；0 代码 / 0 ledger / 0 frozen / 0 OOS；未实施任何迁移（每阶段均需业主 GO）。工作树四 JSON（api_catalog/data_health/form13f/ipo）未提交修改属并发 session，未触碰；未 push。

## 2026-08-22 (b) 五代理军团轮：J/K/O 三模块集成上线，M/N 移交新 session

**五路并行**（J=/ipo、K=/stars、M=/news、N=/quarterly+annual、O=/companies；M/N 各自创建了自己的 worktree 后被取消）。J/K/O 全胜：10 commits cherry-pick 到 main（5c99422..4e481d2 + d15bd9b 重生成），冲突 3 处全按既定解法（生成物 JSON ours+统一重生成、侧栏 import 双保留）。

- **/ipo**：EFTS form 级（无 ciks）S-1 族+424B4 流；1,046 filings/484 issuers（12 请求）；status=filed|priced 由文件类型推导；诚实缺口：价格/募资/上市日不提取（省 ~1000 请求）、424B4 含已上市公司增发（申报流非精选名单）、计数为 filing 非公司。
- **/stars 生态**：40 位管理人（剔除 Scion/Greenlight/Omega/Pabrai/Glenpoint——停报诚实记录）；七分类（人工策展披露）；/institutions 目录化 + /manager/[cik] 40 页 SSG（共享 manager-book 组件）；重生成覆盖 285/398（主仓 cik_resolver 快照层生效，K 报告 188 是其 worktree 无该缓存之故）。
- **/companies**：冻结宇宙目录（三重过滤；CN 代码首位 6/0/3 诚实归 0-9 组）；评分/rank_change 用项目涨跌色约定（rank_change=prev-current 已向 export 求证）。
- **重生成**：30 面板/30 端点/0 planned；form_ipo/form13f 聚合缓存已从 worktree 拷回主仓 data/cache。
- **验证链**：全套 pytest exit 0 + ruff/tsc/eslint 净 + build 1,492 页（/ipo、/companies、/manager/[cik] 全预渲染）。

**M/N 移交**：半成品在 worktree Aionis-m/Aionis-n（未提交：M 有 news_feed_fetch.py+7gate 文档+export 接线；N 有 export/侧栏/index 接线）——**新 session 接手协议写在 `tasks/active/TASK-P2-M-news-feed.md` 与 `TASK-P2-N-financial-stream.md`**（含"审查他人半成品"纪律、worktree 重建建议、验证命令、集成协议、junction 清理铁律）。**注意两 worktree 基 b1f991a，main 已在 d15bd9b——续作先 rebase 或重建**。

**遗留**：GitHub Actions 计费阻断（blockers.md 首条，日更+部署停摆）；P3 势力阵营；业主门研究线。

## 2026-08-22 (a) 党派 join 上线 + 配额阻断下的代理调度策略

**党派 join（`9aea9e0`，P1 第三件）**：house.gov/representatives 议员目录（公共域，1 请求缓存）双行序解析（姓名在前含全称选区 / 序数在前，At-Large→00，430 席 218R/211D/1I）→ **选区码+姓氏双重佐证 join**（仅按选区会把现任党派错配给候选人/前议员——姓氏不一致诚实 null）。实测 806/874 链接，未链接 68 = 前议员/补选过渡（McCormick GA06 等）。视图中性 mono 徽章（语义色不挪用）；契约钉 party 枚举 + party_coverage 记账。

**代理调度现状**：三 worktree（j=/ipo、k=/stars、l=党派）已建；l 任务被主线接管完成并清理；**j/k 代理派发双双阵亡于 [1308] 5h 限额（04:18:38 重置）** → 已建定时调度在配额恢复后自动派发 j/k 两代理并按门集成（见 workspace automation）。**剩余优先级**：P1=J /ipo + K /stars 目录扩展+manager 详情页（本轮调度）；P2=/news、/quarterly+/annual、/companies；P3=势力阵营（血缘图谱）；业主门=PTR PDF 交易级解析、E3/Track A/Track LLM。

**注意**：GitHub Actions 计费阻断未解（blockers.md 首条）——日更与部署停摆中，代码推送正常。

## 2026-08-21 小隐寺全形态路线图 + 三代理（H 成 / G-I 阵亡→主线接管）→ /events + /congress 上线

**方向文件**：`reports/design/2026-08-21-xiaoyinsi-full-parity-roadmap.md`（17 路由对齐矩阵、P0-P3 阶梯、Aionis 五特色增层；小隐寺自身空壳 /companies+/annual+势力阵营未上线 = 填壳机会）。本轮 P0 三件全部关闭。

**三代理**：worktree ×3（junction 只挂 node_modules，**data/cache 不再共享**——上轮 rm -rf 穿透事故的预防）；H 全胜双 commit（`676b90d` cmdk 4 路由 + `5dc1c25` 68/118→94/118，归一化精确匹配 + 死链守卫）；G/I 阵亡于 [1308] 5h 限额 → 主线接管。

**/congress（`0679b92`，planned 清零）**：
- 尽调留证 `docs/data-intake-congress-stock-act.md`：Senate=Akamai 403；第三方 API G1 挂；House **两路验证取优**——CSRF HTML 搜索（无日期）被 **批量 FD.zip→FD.xml** 取代（日更索引、FilingType=P、**真 FilingDate**；与并发 session agent/politician a2f719b 交叉验证一致，其 worktree 未动只读引用）。v1=申报流级（member/office/**filing_date**/year/PDF 链），**交易明细在 PDF 内不解析不编造**；Senate blocked 诚实卡。
- 真实数据 874 PTR/144 人（2025:515+2026:359，2 请求 ~4s），as_of=2026-08-18。
- 毕业：_PLANNED_PANELS 空（列表保留共享定义）、`test_planned_disclosure_present_and_consistent` 改钉空集 + 毕业注释、CI 加 fetch 步。

**/events（`a714fcb`，EFTS 第三代）**：
- `form8k.py`：评分制主文档选择器——三次真拉失败模式（R1.htm XBRL 渲染件、a8-kex991q3.htm exhibit 名内含 8-k、q1fy27pr.htm press release 同分最短名）→ 0 分档=发行人-日期规范 `^[a-z][a-z0-9]*-\d{8}\.htm$` 或名含 8-k/8k（exhibit 检查 `ex\d` 任意位先行）。Item 正则清洗 nbsp+thin-space（`&#8201;` iXBRL 时代）。
- 23 事件/5 发行人/0 未分类；稀有重大优先单一归类 + 全 Item 列表保留；7-gate `data-intake-edgar-form8k.md`（评分表留档）；日更 manifest + CI fetch 步。

**验证链**：全套 pytest exit 0 + ruff 净（--exclude docs/code-review）+ tsc 0 + eslint 净 + build 26 路由（/events /congress ○ 预渲染）。

**踩坑**：① Windows 下 `cmd /c mklink` 在 Git Bash 需 `cmd //c "mklink ..."`（正斜杠转换吞参数→junction 静默不建）；② worktree pytest 走 `PYTHONPATH=<wt>/src + 主仓 venv python`（editable 安装指向主仓，不设即测旧码）；③ ruff E501 对字符串字面量内的行同样报——HTML fixture 靠折行解决（regex `[^>]` 跨行匹配不受影响）。

**遗留池**：roadmap P1（/ipo、/stars 目录+manager 详情页）→ P2（/news、/quarterly+/annual、/companies）→ P3（势力阵营=血缘图谱）；政客交易升级=House PTR PDF 解析（工程大，业主后议）；Senate 解封监控（Akamai）。

## 2026-08-20 (c) 三代理第二轮全胜：quickwins + CN 行业 + 13F → 集成上线

**三代理全部交付**（本轮无阵亡；边界纪律 + 增量提交指令生效）：
1. **D quickwins**：cmdk「热门个股」第 5 组（top10 多头+top3 空头，text-up/down 遵守涨跌约定）+ market_context 3 条 region:"cn" 语境事件（08-19 暴跌/宇树 IPO+460%/四中全会，新 type `ipo`）+「A 股」徽章。
2. **E cn-industry**：7-gate 全过（BSD 实证、vendor display-only 数据侧、G3 快照纪律）；baostock 走 lazy import + `uv run --with`（零 pyproject/lock 改动）；CN sector 4 tier→52 证监会行业组、`cn_tier` 列保留、退市诚实回退 tier；5194/5207 覆盖。**License 更正移交**：旧价格文档 MIT 引用有误（GitHub repo 404），权威=PyPI=BSD，已更正。
3. **F form13f**：12 明星管理人（CIK 实查、淘汰停报实体）；11 位最新季 2026-06-30；60 请求 2m20s；**EDGAR 13F XML value=整美元（非千美元）——SEC 网页惯例是错的，AAPL $253.79/股交叉验证钉死**；帧差键=(cusip,option_type) 防 title 漂移假信号；`/institutions` + 26×2 i18n；CUSIP→ticker 诚实 68/118。

**主线集成**：8 commits cherry-pick 零冲突；form13f 注册 cadence 面板 + as_of 提取器；13f/cn-industry 从 planned 毕业（剩 politician-trades）；`_sm_committed_extra` 传 committed_path（测试隔离）；**修复 A 遗留旧测试回归**（fixture 缺 accession——教训：**agent 改共享函数后必须跑全套 pytest，不能只跑其边界文件**）；CI `--with baostock` 接线；全套 pytest 首次 0 失败；部署 `32335991748` 绿。

**⚠️ 主线事故档案**：上轮 `rm -rf` worktree 穿透 junction 误删主仓 data/cache 大部 + node_modules（runs/ 冻结产物无恙、committed JSON 无恙、CI 独立缓存无恙）。node_modules 重装修复；cache 由 fetcher 渐进回填。**铁律：清 worktree 先 `cmd /c rmdir` 摘 junction 再删目录。**

**遗留候选**：政客交易 STOCK Act（唯一 planned，PDF/JSON 端点尽调待做）；CUSIP→ticker 覆盖 68/118 可提升；cmdk 页面组需补新路由（heatmap/institutions/data-health/api-docs）；i18n 孤儿 key；BACKTEST_MONTHS/HIG 密度（业主取舍）；研究线三门（E3/Track A/Track LLM）。

## 2026-08-20 (b) 三路子代理并行（业主指令）→ 全阵亡 → 主线接管 → 集成上线

**编排**：git worktree ×3（wa/wb/wc，junction 共享 data/cache 与 node_modules）。踩坑：**Turbopack 拒绝跨文件系统根的 node_modules symlink**——worktree 内 `next build` 必败（"Symlink node_modules is invalid"），tsc/eslint 可用；build 归主线集成。另一坑：**worktree 的 runs/ledger.jsonl 被 git CRLF 重签出 → sha256 pin 测试假红**（内容同、字节异），用主仓原文件覆盖即绿。

**子代理结局**：B 网络死（留完整 dict 键）；A/C 死于提供商 5h 限额[1308]（05:38 重置）。主线接管完成全部。

**A 的数据修复要点（真根因）**：EDGAR 日更索引按**每 listing**列 13D（主体+申报人实体都在）→ 旧行 ~40% 重复且零解析。修复三件套全离线（`_sm_ticker_maps` / `_sm_dedup_enrich` / `_sm_committed_extra`），实测 ticker 0/60→44/60。**验收教训：A 死在删除旧版函数之前，文件里有两个 `_refresh_smart_money_recent_only`——Python 静默用后定义的旧版，新实现全失效；接管时必须查重复定义**（本次主线删除后 44 测试才真正测到新路径）。

**交付四 commit（cherry-pick 后 865b4bd/cf04edf/20df473/2c8f48f + regen 07e9763）**：
1. `/heatmap`（手写 squarify，300 可点格、其他桶 342/779 诚实聚合、色随涨跌约定）
2. picks 集中度卡（等权板块 HHI + 档位徽章 + 分解条，US 0.089/CN 0.292）
3. smart_money 修复 + data_health.source_health + planned 三项（politician-trades/13f-holdings/cn-industry）+ api_catalog planned 端点
4. 视图接线：data-health 源健康卡+已规划卡；api-docs planned 虚线不可点

**集成**：dict.ts 自动合并；推送撞日更 0f2792a → rebase JSON 全冲突 → ours+合并码全量重生成（`_sm_committed_extra` 保住日更侧新行：latest 08-18、44/60 不回退——该函数正是为这个场景设计的）。confirmation 股票链接 0→36。

**验证链**：tsc 0 / eslint 净 / build 1,447 路由 / 44 契约 / ruff（排除并发 docs/code-review/）/ 浏览器实测（热力图 215×419px 格、HHI 实值、源健康+规划卡、回路 36 链）/ 部署 `32327579931` 绿 + 线上五页 200。

**边界**：display + 数据导出 lane；0 ledger/frozen/config/prereg/OOS。worktree 与 agent 分支已清理。

## 2026-08-20 (a) 终局定帧 + P0 三件套：涨跌色约定 / 回路闭合 / 实时指示器

**业主定帧（方向性）**：小隐寺 = Aionis 的最终目标形态；在其全形上**只做加法**（叠加反泄漏/溯源/可证伪特色），删减是以后的事。

**交付（display-only）**：
1. **涨跌色约定系统**：`--up/--down` 变量（浅/深 × intl/cn 四组合）+ `[data-colorconv="cn"]` + 工具类 text-up/down、bg-up/down、bg-up/down-soft（color-mix）、badge-up/down。10 个视图的**数值方向色**迁移（picks 概率条/评分/排名箭头/回测收益、stock 全套、overview RankChange、sectors 亲和条、positioning 净多空、themes 方向徽章+DIR_BAR、insiders 买卖+图表 fill=var(--up/down)、reddit 情绪徽章、market 总收益）。**语义色（信任 emerald/风险 rose）有意不迁**。头部 ColorConvToggle（实时预览箭头色）+ localStorage + 预水合内联脚本（防绿涨闪烁，next-themes 同款）。
2. **回路闭合**：insiders/reddit 表 ticker→个股页；smart-money 徽章链接就位。
3. **实时指示器**：live-prices `updatedAt` + 个股页 1s tick "X 秒前"（绝对时戳退 tooltip）。

**发现（预存缺陷，非本轮引入，待修）**：`smart_money.json` recent 60 行 ticker 全空、filer="申报人见原文"——`_refresh_smart_money_recent_only`（5ea6649）从日更索引合并的行丢失 ticker/filer 解析 → 回路在该面板自动降级 + stock_universe 佐证 join 拿不到 13D 计数。修复属日更 lane：recent-only 路径需带 ticker 解析。

**注意**：工作树出现并发 session 的未跟踪目录 `docs/code-review/`（7 个预存 E501）——不碰不提交，验证 ruff 以 `--exclude docs/code-review` 为准。

**验证链**：tsc 0 / eslint 净 / build 1,446 页 / 40 契约测试 / ruff（排除并发目录）净 / 浏览器实测色彩切换（cn 下 .text-up=lab(63.7,60.7,31.3) 红；intl=绿）+ 持久化 + "0 秒前 · 259.74"实显 + confirmation 子页链接计数（insiders 5 / reddit 1）。

## 2026-08-19 (u) 公共静态数据 API — 模仿小隐寺数据中台（不消费其数据）

**业主定帧**："不要直接抓取小隐寺数据，而是应该从模仿开始，以及小隐寺数据本身就有提供该项目 api 的使用说明"——即学其数据平台形态（统一 API + 每路径 x-status/x-license + 健康水位线），不碰其数据/接口。

**交付**：
1. **`api_catalog.json`**（`export_api_catalog()`，排 main() 最后、读 data_health）：26 端点 × {license, 一手来源, 新鲜度, as_of, path}。license 映射 `_API_LICENSE` 镜像 docs/data-intake-*（SEC/CFTC/FRED=公共域，Tiingo/Alpaca/Reddit=vendor ToS display-only，模型面板=repo MIT）；未映射 key 诚实 "unverified — do not ingest"（测试钉死不出现）。
2. **`web/scripts/build-api.mjs`**（`prebuild`，CI `pnpm build` 自动跑）：镜像 28 个面板 JSON → `public/api/v1/panels/` + 根级 catalog.json / health.json / **openapi.json**（OpenAPI 3.1：4 路径，`/api/v1/panels/{panel}` 带 26 个参数级 x-aionis-freshness/license/source/as-of，实时价 Worker 单列 server）/ README.md。产物 gitignored（`public/api/`）→ 部署 API 与终端面板同源、永不漂移。
3. **`/api-docs` 页**（参考组侧栏"数据 API"）：端点表（链接直开线上 JSON）+ 面板目录表（新鲜度 badge + license + 来源 + as_of，面板名→线上 JSON）+ curl/fetch 示例 + 反泄漏边界卡（研究摄入须过 7-gate；worker display-only 绝不进 OOS）。i18n zh+en。
4. **测试**：+2 契约（catalog 形状/全 license 非空/与 data_health 键集调和/worker note；披露 7-gate+GitHub Pages）→ 40 web 契约绿。

**踩坑（重要）**：`npx next build` **不触发** prebuild 生命周期（只 `pnpm build`/`npm run build` 触发）——本地验证先手动 `node scripts/build-api.mjs`；CI 无此问题。

**验证链**：tsc 0 / build 1,446 页 / eslint 净 / ruff 净 / 全套 pytest 0 失败 / 本地 curl 六端点 200 / IAB 实测 /api-docs 全渲染。

**边界**：0 ledger/frozen/config/prereg/OOS；未请求小隐寺任何端点；API 方法学自declares display-only + 7-gate 摄入门。

## 2026-08-19 (t) 小隐寺对照 + 个股下钻页 + 数据健康地图 + rank_change 跨区污染修复

**背景**：业主以 08-19 A 股暴跌（沪指 -2.40% 失守 3900、创业板 -6.26%、银行逆势、CPO/存储重挫、宇树 +460%）+ data.xiaoyinsi.com 全站为引，要求深度探索项目发展方向；随后授权"推进到满意为止，允许试错"。

**方向分析结论（浏览器实探小隐寺：首页/个股页/API docs）**：
- 八维度美股另类数据终端 + 统一数据中台（OpenAPI 3.1、X-API-Key、每路径 x-status/x-license、每日 Parquet 分区、/health 源水位线）——基建形态值得学（→ 本轮数据健康页），数据**不可用**（license 不透明，7-gate G1 挂）。
- 弱点 = Aionis 差异化机会：无 PIT/审计链、覆盖缺口（NVDA 13F"共 0 家"）、评分卡无溯源。
- E3 forward-live 价值被暴跌日放大（冻结 CN picks 主力=半导体，恰在风暴眼）但 **append-only 前向账本仍留业主显式 GO**，未擅启。

**交付（全部 display-only）**：
1. **`/stock/[ticker]`（1,421 页 SSG）**：US 492 + CN 929 冻结 OOS 最新月全覆盖。模型读数（score/rank X of N/percentile/rank_change/prob_up vs base_rate）+ 12 月评分 sparkline（均值/σ）+ 板块语境（区域板块表 standing）+ 佐证计数（smart_money/form4/reddit join）+ live 价（Worker display-only，CN 通）+ 切换器（客户端全宇宙搜索）+ NullDisclaimer + 冻结 badge + 方法学。`stock-universe.ts` 独立模块（553KB 不进共享 barrel——Turbopack 单 barrel=单共享 chunk 的既定教训）。入口：picks 表 + overview MiniPicks。
2. **`/data-health`**：26 面板 → 日更 9 / 源节奏 2 / 冻结 15；as_of 读面板自身字段（缺=诚实 null）；exported_at=lane 写入日；冻结框定"推进即泄漏，E3/新阶段是唯一合法前进"。侧栏守卫组。`export_data_health()` 排 main() 最后（读全部已导出 JSON）。
3. **rank_change 跨区污染修复**：`export_picks` prev 帧未过滤 region，US/CN 月末 61/87 重合 → 混合帧排名，US picks rank_change 最多偏 +929（症状：TROW 829 > n_region 492 的数学不可能值）。两处修（picks + stock_universe），picks.json 重生成（10 行修正，CN 当月未受染）。契约测试以 `|rank_change| ≤ n-1` 界钉死。

**验证**：38 web 契约测试（+5 新）绿；tsc 0；next build 1,445 页绿（stock SSG 10.9s/11 workers）；eslint 净；全仓 ruff 净；全套 pytest 0 失败；本地静态服务 + IAB 浏览器实测（data-health 三卡全渲染、海光个股页实测 live -7.26%、25+4 入口链接在 built HTML 验证）。

**边界**：0 ledger/frozen/config/prereg/OOS；未跑 research/forward；E3/Track A 未触。

**遗留候选（未做，有理由）**：cmdk 面板未加个股入口（1,421 项不可枚举，picks 入口已够）；政客交易（STOCK Act，一手源公共域可过 7-gate，PDF 解析工程量大，候选）；13F 机构持仓模块（EDGAR 公共域，中大型工程，候选）；A 股行业级分类（baostock，handoff (p) 既有评估，需 CI 协调）。

## 2026-08-16 (s) Apple HIG 设计语言重构（token 层，5 文件辐射全站）

**范式**：Clarity（SF 系统栈/双模式抗锯齿/蓝选区）× Deference（毛玻璃吸顶导航 + 同材质 StickyTabs = iOS 材质堆栈）× Depth（浅发丝边+双层柔影 / 深表面抬升，圆角 12px 基准）。

**改动**：globals.css（双主题 Apple token + 字体栈 + ::selection + 侧栏 source-list 蓝染）、app/layout.tsx（删 Geist 网络字体 → 系统栈）、(dashboard)/layout.tsx（header 毛玻璃吸顶 z-40）、sticky-tabs.tsx（top-16 同材质）、ui/card.tsx（ring → hairline border + 双层柔影，深色仅边框）。

**对比度账**（Node 核算 + 浏览器实测）：浅 muted-on-card 5.96、深 6.54、浅蓝 #006cd9 白上 4.9-5.1、深蓝 #0A84FF 卡上 4.66——全 AA。首版浅蓝 oklch(0.584) 只 4.36 → 加深至 0.545（text-primary 场景保护）。

**验证**：build 23/23 + 33 契约 + ruff；20 路由双主题零溢出；视觉模型三图审全过；部署 CSS 产物级终验（oklch 被压成 hex/lab，按 `--background:#f6f7f8` 等实锤）。

**遗留候选**（视觉模型建议，未做）：图表线色饱和度降至 systemGreen 柔和度（逐图调色，涉 10+ 图）；同屏密度/留白（内容取舍需业主裁决）。

**操作记录**：CSS 多闭括号 → Turbopack 报 `Unexpected }`（token 块替换时 old 串未含尾括号所致，1 分钟修）；IAB webview 后期 "guest not attached" → 部署验证降级为 CSS 产物 grep（等效结论）。

## 2026-08-16 (r) 用户旅程角色扮演 → cmdk 面板 + 模板死链清除 + 浅色一等化

**旅程发现（首访视角 + 三学科）**：
| 学科 | 发现 | 处置 |
|---|---|---|
| 设计学/心理学 | 首访"术语墙 + 无从下手"——无阅读序入口 | 面板"从这里开始"①-⑤ 编号导览 |
| 人体工程学 | 20+ 路由无键盘快速跳转；Ctrl+K 死 | 真 cmdk 面板（36 项 4 组） |
| 软件工程 | 模板死链 ~1310 行（palette/nav-secondary/seed/globe.json 互引但零活引用） | 全删（grep 复核零残留） |
| 软件工程 | `ui/command.tsx` CommandDialog 缺 `<Command>` 根 → cmdk context 崩（零使用从未暴露） | 按上游 shadcn 修复 + sr-only title 入 DialogContent |
| 设计学 | 浅色模式二等公民：muted 4.38:1（AA 不达标）、边框隐形 | token 0.556→0.502（5.5-6.0:1）、border 0.922→0.895 |
| —— | 404 ✓ / 深链 ✓ / 图表 tooltip 8/10 ✓ / EN 切换 ✓（残留中文=数据值） | 无需修 |

**轮子复用**：cmdk ^1.1.1 已在依赖（shadcn ui/command）——此前零使用且其 CommandDialog 是坏的；本轮修轮子+用轮子，未新增任何依赖。GitHub/Linear/Vercel 同款方案。

**验证链**：dev 复现崩溃→取栈→修复→面板开/搜索/回车导航/Esc 全实测；build 23/23 + 33 契约 + ruff 净；部署 `31955414141` 绿后部署站复验（面板 4 组 36 项 EN 模式在位、浅色 token 实测 lab42.23）。

**操作教训**：部署站验证时 localStorage 语言偏好（en）会改按钮 aria-label——按中文标签查询会误报缺失；Playwright click 偶发 webview 超时 → 读 rect 后 `cua.click` 坐标路径可靠。

## 2026-08-16 (q) 部署站视觉审计二轮（视觉模型 + DOM 实测）→ P0-P2 全落地

**审计双通道**（部署站 live，1440 + 375 双视口）：
- 视觉通道：逐屏截图 → `analyze_image` 盲审。**工具链要点**：`Read` 本地 PNG → CDN URL → 视觉模型；URL 必须**原样带反斜杠**传（改正斜杠破坏 UCloud 签名 → 1210 解析错误）。`emitImage` 在本环境不回流图像，此桥接是唯一视觉通路。
- 数据通道：`getComputedStyle` 采 lab/oklab 原始色（Tailwind v4 非 rgb；canvas 归一化技巧会被 debug-evaluate 副作用检查拒）→ Node 纯数学换算 WCAG。
- **视觉模型两条报告为幻觉**（"6 个 tab"、"regime 图无事件标注"——实际 4 tab、已有川普 ReferenceLine）：视觉结论必须 DOM 交叉核验。

**硬发现（本轮新增，此前 4 轮视觉审计未抓到）**：
1. **α 降透明 muted 文字 < WCAG AA**：行首列 3.29:1（α0.6）、表头 4.02:1（α0.7）、track 脚注 4.02:1。满透明 muted 6.9:1 达标 → 根因是 opacity 变体不是 token 本身。
2. **10/11px 中文小字 89 处**（th/脚注/徽章）< CJK 12px 下限。
3. **picks 9020px/16461px（10-20 屏）无任何导航锚**：全站唯一 sticky/fixed = 侧栏。

**修复（纯展示层）**：
- **P0**：α-muted→实色（10 文件）；`text-[10px]/[11px]`→`text-xs`（23 文件，保留 empty-state svg 装饰与 sparkline 去饱和）；9px 徽章→11px；审计表行 hover。
- **P1 工效**：`StickyTabs`（4 hub 页）+ `BackToTop`（44px）。**sticky 陷阱**：`<main>` overflow-hidden 祖先使 sticky 失效——删除后 20 路由 × 双视口全测无 h-溢出（min-w-0 是真根因）。
- **P1 认知**：hero 三卡→两卡（`ProvenanceAnchor embedded` 嵌入 VerdictAnchor）；discipline 同 sha 冻结/结果行 emerald 左竖条 + ↳；track 归因卡头部裁决速览条（同源 metrics，零新增数据面）。
- **P2**：`ProvenanceBadge frozen` prop（锁/时钟语义二分，picks/track 页头接线，i18n zh+en）；recharts 刻度→11px + `fill=var(--muted-foreground)`（原 #666 ≈3:1）。

**验证**：tsc 0 + build 23/23 + 33 契约测试 + ruff 净（顺手修 5ea6649 预存 3 lint 错）+ 本地 junction 静态服务四页视觉模型复验 + 对比度复测 3.3→6.9:1 + sticky/返回顶部交互实测 + 移动端无溢出。

**遗留候选（未做，均有明确理由）**：regime 图 recession/hike 区间底纹（需事件数据管线，跨 lane）；佐证区两卡微对齐（P3 边际收益低）；picks 长表分页/虚拟化（sticky 已解主要痛点，KISS）。

## 2026-08-15 (p) 同题扫查二轮：死代码/依赖裁剪 + lint 清零 + 新鲜度审计 + 后续优化方案

**交付（`6eab8a4`，-2118 行）**：
- **死代码**：`globe-demo.tsx`、`ui/globe.tsx`（three/three-globe/@react-three 链）、`ui/chart.tsx`、`ui/calendar.tsx`（react-day-picker+date-fns 唯一用户）零引用（grep 全目录复核）删除；package.json 裁 9 依赖，`pnpm-lock.yaml` -798 行同步（manifest+lock 原子，CI `--frozen-lockfile` 兼容）。CI install 下载变少；逐页 payload 实测等量（运行时零变化）。
- **lint 清零**：live-prices 冗余 setState 删；i18n provider SSR 安全水合模式带理由 disable。`eslint src --quiet` 0 error。
- **验证**：tsc exit 0 + build 23/23 静态页 + 全量 pytest exit 0（Windows 迁移后首次全绿）+ ruff 净。

**新鲜度审计（问题分级）**：
| 面板 | 状态 | 归属 |
|---|---|---|
| theme_signals + themes price 族 | 06-30（46天）| CI display_panel 收敛中（另一 session 的 run 31878236600 验证范围，勿重叠） |
| smart_money | 08-07 | 13D fetch 间歇，低危 |
| picks_meta / pick_conviction | 08-03 | 读 gitignored 冻结 OOS parquet，设计如此 |
| GDELT news | as_of 06 | 增量回填滞后 |
| reddit | live 2 picks，1 null bull_ratio | RSS 无 score 结构限制；类型已防御 |

**后续优化方案（可实施性已评估）**：
1. **性能·tab 级 next/dynamic**（推荐，低风险）：4 个 hub 页（picks/regime/track/confirmation）非默认 tab 改 `next/dynamic` → recharts 376KB + 非首屏数据移入按需 chunk（picks 首屏 1890→~1500KB）。Turbopack 兼容、不换构建器、每页 4-6 行。UX 代价 = 首次点 tab 短暂 loading。
2. **性能·BACKTEST_MONTHS 99→36**：picks_backtest.json 140→~55KB 且在共享 chunk（每页受益）。显示取舍（track record 只显 36 月）需业主点头。
3. **性能·webpack manualChunks**（大工程）：换构建器 + 26 JSON 按面板拆 chunk（非图表页 -350KB）。涉 CI 构建行为，需 CI session 协调，仅当 1+2 不够时。
4. **数据·A 股行业分类**：baostock `query_stock_industry`（证监会行业，免费无 key，需加依赖 ~pip baostock）或 zero-dep 直接 HTTP；扩展 `build_ticker_metadata.py` + cache + methodology 更新（tier→industry）。M 任务。
5. **数据·Russell 2000 COT 2016**：ICE 变体代码已就位，等 cftc.gov 连通自动补（merge-protected）。
6. **数据·reddit 富化**：业主 PRAW 凭证 → transport 自动升级（代码已就绪）→ score/bull_ratio 补全。
7. **准确率**：研究面冻结，唯一合法路径 = Track A 因子生成器（业主已授权，新冻结面）与 E3 forward-live（AUD-06+业主 GO）—— 均预注册流程，非 display 层可擅自推进。

**边界**：纯 web 展示层；0 ledger/frozen/config/prereg/OOS 改动；未跑 research/forward；未 push（本地领先 origin 4 commit，推送时机由 CI session 协调）。

## 2026-08-15 (o) web 数据层类型加固 + 性能探索定论 + Windows 测试修复（与 CI/CD session 并行）

任务方向：数据/性能/准确率/web 显示优化（CI/CD 由另一 session 负责，本轮零重叠）。三项交付：

**① 全部 26 面板显式契约类型（`web/src/data/aionis/index.ts`）** — 闭环 current.md 续①遗留的
"凡 `as typeof` 面板同类风险" follow-up。nullability 逐一对照 `export_terminal_data.py` 导出契约：
taco.latest_vix/latest_date、form4.shares/price、themes.signals[].value/series[].value/as_of、
pick_conviction.latest/trailing_std_mean 可空（export 显式 `if ... else None` 分支）→ `| null`；
metrics.ledger_row/config_sig_short 仅 live-ledger 分支存在 → optional；market_context.date_range
实为 `string[]`（原臆写 string，tsc 即刻抓出）。日更数据形状漂移从此在 cast 单点红灯（对齐
deploy 31869082383 reddit `bull_ratio: null` 类型塌缩先例的防御）。ThemeCard 内联结构 prop 类型
→ 复用导出 `Theme`（其 seriesVals 运行时 `typeof v === "number"` 过滤本已存在，仅类型声明落后）。
验证：`tsc --noEmit` exit 0 + `next build` 22 路由全静态预渲染 + 33 `test_web_terminal_data` 契约
测试绿 + 全仓 ruff 净。`attribution-card` 的 `typeof aionis.metrics` 参数注解自动升级为显式类型。

**② 性能探索（全部实测取证）**：
- recharts 376KB chunk **已按路由正确分割**——7 个无图表页实测不引用它；无需 lazy 化。
- **barrel 命名导出拆分实验 → 实测更差 → 回退**：Turbopack 静态导出对跨路由共享模块**不去重**
  （数据指纹证据：market_context 内容出现在同一页加载的 2 个 chunk 里各一份拷贝），27 个消费文件
  改命名导入后每页 +50-280KB（picks 1613→1890）。结论 = 保留单一合并对象（单模块 → 单共享 chunk，
  零重复）；已在 index.ts 头部注释固化此结论。git checkout 回退了全部消费文件（它们曾被我改写，
  最终 diff 不含）。**若未来要 per-route 数据拆分：需 webpack manualChunks（Turbopack 无此 API）= 换
  构建器**，涉 CI/CD 领地，仅记录不擅动。
- **"每页变大"真因 = 过期本地基线 + 日更数据增长**：纯 HEAD 重建与改动版逐页等量（evidence
  1222KB/picks 1890KB/discipline 1284KB）；旧 out/ 来自更早 commit。近期 +50-280KB/页全部来自
  数据新鲜（macro_drivers 5→7 序列、picks_backtest 增月等）——是改进非回归。
- 每页 JS ~1.2-1.6MB 的构成：React/Next 运行时 ~500KB（不可免）+ 共享数据 chunk ~350KB + recharts
  376KB（仅图表页）+ UI 库。数据 chunk 的减肥杠杆 = 缩短 picks_backtest（BACKTEST_MONTHS=99→36，
  显示取舍，未擅动）。

**③ Windows 迁移预存测试修复**：`test_run_dir_sanitizes_unsafe_sig` 用 `str(d).startswith("/tmp/..")`
断言，WindowsPath 渲染反斜杠必挂（sanitise 逻辑本身正确，`eviletc` 未逃逸）→ 改 `d.as_posix()`。
18/18 test_reporting 绿。这是 WSL→Windows 迁移后全套 pytest 在本机全绿的已知最后一个失败。

**④ 数据面核查（订正旧记录）**：13D smart_money latest=2026-08-07（日更生效，旧"2024-12 滞后"
记录过时）；A 股 picks 现为板块级分类（创业板/沪主板/科创板，methodology 已诚实披露"tier 非
industry"）。行业级升级 = 后续项（需申万/证监会行业源 + license 审查 + CI 协调）。

**边界**：`index.ts` + `themes-view.tsx`（2 行）+ `test_reporting.py`（1 断言）+ state；**0 ledger/
frozen/prereg/ADR/config/OOS 改动**；未跑 research/forward；**未 push**（CI/CD session 并行验证
refresh run 中，推送时机由其协调——本地 commit 已就绪）。

**待业主/后续**：(a) push 时机（CI session 协调）；(b) A 股行业级分类数据源裁决；(c) 若在意每页
payload，可选 webpack manualChunks 换构建器（涉 CI）或 BACKTEST_MONTHS 缩减（显示取舍）。

## 2026-08-09 (n) 部署站仪表盘诊断 + IA 重设计提案（已 push 上线）

业主看**部署站**，批"数据缺失/taco 空图/reddit 只一快照/没标川普两任就职/七主题生硬/整体像拼凑杂烩不构成有机整体"。**系统化诊断（DOM + 审计 + dev server 实测）**：

- **数据层大多 2016+ 且健康**（market/taco/cot 都 2016→2026）；部署站看着缺 = **未重新部署**（近期回填没上线）。已 push → Actions 重建中。
- **真凶 1（已修 commit `e3274e3`）**：`next.config.ts` 硬编码 `basePath:/Aionis` → `next dev` 下每路由 404（业主若跑 dev 看到全空）。改 production-only。
- **真凶 2（已修 `e3274e3`）**：taco `XAxis dataKey="date"` 但数据是 `month` → 0 path 空图。改 `month`。
- **川普就职（已修 commit + IA-doc 一起 push）**：market 事件表补 2017-01-20/2021-01-20/2025-01-20 就职 + 2025-02 关税，新增 `inauguration` 类型（emerald 样式）。
- **硬约束（不可粉饰）**：reddit **forward-only**（Pushshift 2023 死，无 2016 历史）；ic_monthly/picks_backtest/pick_conviction **OOS 2021+ 研究冻结**（延 2016 = rerun-to-significance 禁）；须诚实标注。
- **实测渲染正常**：dashboard/market/positioning/conviction/powerfloor/calibration（DOM 验 path/line 计数）。reddit-view 仍是 stub（current.md 既标，前端 owner 待接 picks 表）。

**P3 IA 重设计提案** `reports/design/2026-08-09-terminal-ia-redesign.md`（PROPOSED，待业主审）：核心 = 把扁平 nav 重构成 **6 步决策漏斗**（①定调 Regime→②定向 Themes→③定标 Picks→④佐证 Confirmation→⑤问责 Track→⑥边界 Discipline），每模块加"角色导语"；七主题可操作化（方向×强度×利好股）；诚实标注约束；删模板遗留（accounts/cards/budgets/crypto/…）；P2 扩周频 cron（现有 `refresh-terminal-data.yml` 只 re-export 不 fetch → smart_money 卡 2024-12；扩成 fetch+re-export）。

**已 push** `27a18f3..b1d195d`（含本会话所有 commit：Track A 校准视图、Track LLM pilot/prereg、dashboard 修复、川普就职、IA 提案）→ Actions 重建部署中。

**待业主**：① 审 IA 漏斗提案 → 授权 P3（nav 重排+角色导语+删模板+七主题可操作化）② 裁 cron 频率（周频 Fri 收盘后 vs 保持日频）③ reddit picks 表要不要我补 ④ P4 主题 ④⑤（news LLM forward-only / risk pyfolio）。

## 2026-08-09 (m) Track LLM Phase-0 可行性已证 + PROPOSED 预注册（D-first 单变量）

业主问"C+D 结合"→ 分析后推荐 **D-first 单变量**（EDGAR-LLM filings-tone 作第 42 列，1 trial 干净归因；C/stacking 条件后续仅当 D 显示信号）。业主再授权"创建最有价值内容至优化"→ 交付 **Phase-0 可行性 pilot + PROPOSED 预注册**（0 ledger / 0 frozen / 0 OOS）。

**Phase-0 实测（本地门，真数据）**：`scripts/track_llm_feasibility_pilot.py`（+8 hermetic 测试绿，ruff clean）：
- **G1 CIK 解析 = 100%**（US OOS 2021-2026，533 distinct tickers 全解析；2911 ticker-years）。cik_resolver 的 ~60% gap 是**历史全宇宙**问题，OOS 窗口不绑定。
- **G2 token 投影 = ~11.71M（一次性）**（5576 10-K MD&A extractions；idempotent accession cache → 重跑 0 token）。两本地门 GREEN → **FEASIBLE**。
- **待 owner（需凭证）**：G3 真实 per-call token + G4 temp=0 稳定性（`--measure-llm N`，scaffolded，freeze 前校准）。

**PROPOSED 预注册** `docs/track-llm-preregistration.md`（未冻结）：两尾 null-expected claim（`IC_{41+LLM} − IC_{41-frozen}` 配对 HAC）；EDGAR 10-K MD&A excerpt（filed-date PIT + embargo 21）→ GLM temp=0 → `clip(bullish−bearish,−1,+1)` scalar → forward-fill；复用 Track C #48 learner（仅 41→42 列）；n_trials=1（DSR 平凡）；H6 走 cache-pin；stacking(C) 条件触发（仅当 IC_diff CI 不跨零）；US-only v1；D1-D6 owner 裁断点。可行情报告 `reports/design/2026-08-09-track-llm-feasibility-pilot.md`。

**诚实预期**：大概率 null-to-modest（power floor 封顶），但 null = 第三条独立 null（#49 月频 / #54 周频 / LLM）。

**边界**：本轮纯新建 1 script + 1 test + 2 docs（prereg PROPOSED + 可行情报告）+ state；**0 ledger / frozen / prereg-freeze / ADR / config / E3 / OOS** 改动；未跑任何 LLM 增强估计量；未做任何 GLM API 调用（G3/G4 待 owner 凭证）；Track C / Track Adaptive / Track B 冻结面完全未触。

**待业主**：① 审 PROPOSED 预注册 + 可行情数字 ② 用凭证跑 `--measure-llm 8` 校准 G3/G4 ③ 裁 D1-D6（universe/filing-type/excerpt/scalar/model+temp/cost）→ 若 GO：`config_committed` 冻结 → 首次抽取 → OOS。④ 或：弃 D（接受 null-to-modest 预期，收尾）。

## 2026-08-09 (l) Track A 切片 A1 — walk-forward 校准可靠性（display 层，已交付待提交）

业主重提"历史数据补到 2016 后 → 实时更新 + 用新数据不断自校正模型参数往可观走"。**关键事实：此问题 2026-08-08 已问、已分析、已实测**——[`reports/design/2026-08-08-live-adaptive-calibration-analysis.md`](../reports/design/2026-08-08-live-adaptive-calibration-analysis.md) 切 Track A（显示层，推荐）/ Track B（研究层）；Track B（扩窗周重训）已冻结+跑 = **NULL（ledger #54，IC_diff_weekly −0.0037，p=0.26，adaptive 略差于冻结）**。新增 2024-2026 调研确认重训频率非主导/常恶化（[Inquire Europe "Less is more"](https://www.inquire-europe.org/news/in-case-you-missed-it-less-is-more-biases-and-overfitting-in-cross-sectional-machine-learning-return-predictions/)）；唯一未测合法变体 = 固定模型集 Bayesian/stacking（[Gelman](https://sites.stat.columbia.edu/gelman/research/published/stacking_paper_discussion_rejoinder.pdf) ：BMA 在 M-open 失效）；唯一有希望新数据方向 = LLM 文本信号（项目 extraction 模块已有，但无 frozen 臂用 LLM 特征）。**业主裁 = 路径甲（显示层自适应校准）**（AskUserQuestion 四选一）。

**Track A 现状盘点**：A2（漂移报警）已建（`model_drift.py`+`export_model_health()`，backend done；UI 归前端 owner）；A3（诚实 track record）已建为 `export_picks_backtest()`（历史命中），前瞻累计半 = E3 owner-GO 门。**A1（walk-forward 校准）此前未建** = 本轮唯一真新增。

**A1 交付**（纯 display 变换，0 ledger/frozen/E3/研究估计量）：
- `src/aionis/eval/score_calibration.py`：+`_reliability_bins()` + `calibrate_walk_forward()`。对每个 realized OOS 月 T，用**严格 T 之前**的 realized (score, fwd_return) 对重拟合 Platt 显示映射，预测 T 的 P(up)；T 的 realized 结果回测打分（backward audit）。产出 per-month OOS-ECE 序列 + pooled OOS 可靠性图。反泄漏契约镜像 `calibrate_latest_month`（T 仅预测不入拟合；仅 2 参显示映射重拟合，frozen LightGBM 永不触；单调映射不能制造判别力）。
- `scripts/export_terminal_data.py`：+`export_calibration_reliability()`→`calibration_reliability.json`（awaiting_fetch 守卫 + 诚实方法学串），接入 `main()`。
- `tests/test_score_calibration.py`：+8 hermetic 测试（反泄漏 T 不入拟合 / walk_forward=True / 强信号可靠性单调 / null 信号概率带紧 / H6 跨调用确定性 / 太少月跳过 / 双区域 / jsonable）。

**验证**：score_calibration(23)+model_drift(11)+web_terminal_data(20)=54 display 测试绿；ruff clean（3 文件）；**真实数据跑**（read-only，未写 tracked JSON）：US pooled_ece=0.0369 / 概率带 [0.435,0.553] 紧绕 base rate≈0.51（诚实 null 签名）/ ECE 随样本增长 0.18→0.115（校准更可信）；CN pooled_ece=0.0196 / 带 [0.438,0.480]；训练对扩 5399→30282(US) / 10538→57537(CN)。**判读**：概率保持可信（低 ECE），但判别力弱（带紧）—— 这是 leakage-safe 的"用新数据自校正**校准**"，**非**制造正 IC（与 #49 null 一致）。

**边界**：本轮 3 文件（2 src/script + 1 test，+291/-2）+ state；**0 ledger / frozen / prereg / ADR / config / E3 / data / web-artifact** 改动（真实数据跑 read-only，未写 `web/src/data/`）；未跑 research/forward/strategy；未触 #49/#54。git status 仅 3 文件 M。

**待业主**：① 审 A1 数字 + 授权 commit（Conventional Commits）② 是否跑 `export_terminal_data.py` 写 `calibration_reliability.json` 进 web（前端 owner 管护，需协调）③ A3 前瞻累计是否过 E3 owner-GO 门 ④ A2/A1 终端 UI 渲染（前端 owner）。

**业主授权自主推进至不可再优化（2026-08-09 续）**：业主"授权创建最有价值最推荐内容，直到该环节不可再优化"。已全栈交付 A1：
- **后端** commit `df34979`（feat(eval)）+ state `681b7df`（docs(state)）。
- **前端** commit `459d96e`（feat(web)）：`/calibration` 路由 + `calibration-view.tsx`（recharts 可靠性图：预测 P(up) vs 实现频率 + 完美校准对角线 ReferenceLine；ECE-随样本增长折线 + 0.05 绿阈值；per-region stat 行 + 诚实 null 披露）+ data namespace/CalibrationReliability 类型 + zh/en i18n + navMonitor TargetIcon 入口 + 真实 `calibration_reliability.json`（US pooled_ece 0.0369 / CN 0.0196）。
- **验证**：`pnpm tsc --noEmit` clean + eslint clean + `next build` 绿（`/calibration` 已 prerender）。0 frozen/ledger/E3/研究估计量改动。

**Track A 现状（优化到位）**：A1（校准可靠性）全栈完成；A2（漂移）既有完成（model-health-view）；A3（诚实 track record）后向既有完成（picks-view），**前瞻累计半 = E3 owner-GO 门（cron 仍 disabled，不可擅自解冻）**。再加图（概率带随时间、US/CN 叠加）= 边际收益递减 / 过度工程，KISS 不做。

**剩余业主杠杆（非我可自主）**：① E3 owner-GO → 启用前瞻命中累计（A3 前瞻半，display-only forward ledger）② 若要新研究线 → 路径乙（固定模型集 stacking）或路径丙（LLM 文本信号），均需新 prereg/frozen/ledger。

## 2026-08-08 (a) 历史数据推进至 2016 — COT 全量 + Form4 深化（display 层）

业主要求"推进所有历史数据年份至 2016 + 低消耗模型带 agent 执行以省 token"。**范围 = fintech 终端 display 层**（研究管线冻结，climax #49 null 不动）。

**2016 覆盖核账**：
| 数据集 | 2016 覆盖 | 动作 |
|---|---|---|
| market_context (VIX+EW 指数) | ✅ 2016-01..2026-07 (127mo) | 既有 |
| picks_backtest (track record) | ✅ 131mo | 既有 |
| smart_money (13D) | ✅ raw 2015+，2622 条≥2016 | 既有（latest 2024-12，cached pulls）|
| **COT (positioning)** | ✅ **2016-01..2026-08**（9/10 市场连续；Russell 2017-08+）| **本轮扩展** |
| **Form4 (insiders)** | ⏳ 机制就绪，后台深化中 | **本轮扩展** |
| ic_monthly / pick_conviction | ❄️ 2021+ 冻结 OOS | **不动**（反泄漏；延展 = rerun-to-significance 禁）|

**COT 扩展（CFTC 公共域，weekly 不修订，filed Fri）** — `scripts/cot_fetch.py`：
- `YEARS (2024,25,26)` → `range(2016,2027)`（全 Trump 元年）。
- **variant-union**：CFTC ~2022 重命名 S&P/Russell/Copper 合约（`E-MINI S&P 500 STOCK INDEX`→`E-MINI S&P 500` 等），单名 exact-match 改多变体 union + 按 (date,market) 去重 → 恢复 3 市场全 2016。
- **单调 merge**：cftc.gov 边缘网络间歇 ConnectTimeout（2018/2019/2023 跨多次 run timeout），新 run 与既有 parquet union、重叠 keep existing → 数据只增不减（实测 v4 补回 2023 gap）。
- 结果：10 市场 / 5446 行；9 市场 553 wks 连续 2016-01-05..2026-08-04；Russell 2000 2017-08+（其 e-mini 当年精确名 2016 缺，市场特异小 gap）。
- `export_cot`：`comp.tail(78)` → 全量 `comp`（完整 2016→today arc）+ methodology 标注 2016。

**Form4 扩展（SEC EDGAR 公共域，filed-date PIT）** — `scripts/form4_fetch.py` + `export_form4`：
- `START "2024-01-01"` → `"2016-01-01"`；**merge-by-issuer checkpoint**（每 issuer 完成即写 + 保留未重跑 issuer；5 大盘 × 2016→today = 数千次礼貌 XML 拉 ~小时级，merge 保证 live 广度不退化；XML cache 幂等，重跑即续）。
- `export_form4`：动态 window（df min/max 交易月）+ 新 `yearly` 聚合（逐年 buy/sell）+ methodology 标注 2016。
- 数据：当前 2023-07..2026-06（5 issuer / 2415 txns / yearly [2023,24,25,26]）；后台 fetch 深化至 2016（AAPL 处理中 ~440 filings），完成后 cron re-export 自动反映。

**模型分层 + 省 token（业主诉求）**：opus 编排（调研/计划/反泄漏核账/fetcher 精确编辑/独立验证）+ **sonnet agent 执行 export 显示逻辑 + 测试**（精确 spec，1 轮交付，orchestrator 独立核验 diff + ruff + pytest）+ 后台 bash fetch（网络 bound，0 model token）。

**验证**：ruff 全 repo clean；affected tests 37 绿（web terminal + form4）；COT/Form4 JSON 实测 2016+（COT composite_series 534 wks 自 2016-05，z-score 52w 预热）；全套 hermetic pytest 提交前确认绿。

**边界**：本轮 `scripts/cot_fetch.py` + `scripts/form4_fetch.py` + `scripts/export_terminal_data.py` + `tests/test_web_terminal_data.py` + `web/src/data/aionis/*.json`（regenerated）+ state；**0 ledger / frozen / prereg / ADR / config / E3 / runs-data 改动**；未跑 research/forward/strategy；未触 ic_monthly/pick_conviction（冻结 OOS）；display 层不进研究管线（CLAUDE.md display-only 契约）。

**待业主**：① 审线上 `/positioning`（2016→today arc）② Form4 后台 fetch 完成后（~小时）`/insiders` 显示 2016→today 逐年 ③ Russell 2000 2016 gap（需查 CFTC 当年第三变体名）④ smart_money latest 2024-12 是否重刷 EFTS（独立切片）。

## 2026-08-08 (b) TACO/smart_money 推至 2016 + Form4 首批 2016 落地 + 并发 worker 观测

业主授权"创建最有价值内容直至不可再优化"。代码侧 2016 优化收尾：

- **TACO `/taco`**：VIX 由 `[-260:]` 近 1 年日线 → **月均 2016-01..2026-07**（127 点，复用 market_context 月聚合），2025 TACO 事件现置于完整 Trump-era 压力史背景。web 契约测试加 `test_taco_vix_monthly_from_2016`。
- **smart_money `/smart-money`**：加 `yearly`（逐年申报数，镜像 form4 yearly），实测 [2015..2024]。
- **COT Russell 2000 2016 gap**：找到第三变体名 `RUSSELL 2000 MINI INDEX FUTURE - ICE FUTURES U.S.`（2016 在 ICE，~2017 才转 CME），加入 variant-union。**但 cftc.gov 本会话持续 ConnectTimeout（2016/2024/2025 多年跨多次 run 超时）**→ Russell 仍 2017-01 起；ICE 变体代码已就位，cftc 恢复后任一 run（merge-protected）即补 2016。9/10 市场已连续 2016-01..2026-08。
- **Form4 2016 首批落地**：AAPL checkpoint（merge-by-issuer）→ form4.json 现 `window=2016-02..2026-06`，`yearly=[2016..2026]` 全 11 年（AAPL 深，其余 4 issuer 仍 2024-2026，后台 MSFT 深化中）。

**⚠️ 并发 worker 观测（非本会话产物，勿混入我的提交）**：工作树出现另一 actor 的未提交 reddit 升级——`src/aionis/ingest/reddit_sentiment.py`（M，双传输 PRAW+zero-cred Atom RSS）、`scripts/reddit_fetch.py`（??）、`tests/test_reddit_sentiment.py`（M）、`runs/ledger.jsonl`（M，疑 reddit data_ingest 行）。我派发的 sonnet agent 一度把 `export_reddit_meta` 改成读 `reddit_snapshots.parquet` 的 cache-or-await（schema 核验属实：reddit_fetch.py 确写该 parquet + reddit_sentiment.py 列匹配）**但漏掉前端 `subreddits` 字段 → web build 类型检查失败**。处置：**revert 该 reddit export 改动到 HEAD**（export_reddit_meta 回到 awaiting_activation + subreddits），只保留我本轮的 TACO + smart_money；reddit 模块整体留给并发 worker（避免 file-boundary 冲突 + 不冻结其 in-flight 描述）。**amend 仅 stage 我的 7 文件**，reddit_sentiment.py/test_reddit_sentiment.py/reddit_fetch.py/ledger.jsonl 不入提交。

**验证**：ruff 全 repo clean；web 终端 18 测试绿（含新 taco + smart_money）；**web build OK**（✓ Compiled + 17/17 静态页，类型检查过）；COT/Form4/TACO/smart_money JSON 实测 2016+；全套 hermetic pytest 跑中（含并发 worker 的 test_reddit_sentiment.py 改动）。

**后台作业（额度恢复后可继续/验收）**：form4_fetch（MSFT 深化中，EDGAR）；13D sequenced refresh（等 form4 释放 EDGAR）；COT Russell 2016（cftc 阻塞，待恢复）。日志 `runs/{form4_fetch_2016_v3,refresh_13d_sequenced,cot_fetch_russell_retry}.log`。

**边界**：本轮 `scripts/cot_fetch.py` + `scripts/export_terminal_data.py`（TACO+smart_money）+ `tests/test_web_terminal_data.py` + `web/src/data/aionis/{cot,form4,smart_money,taco}.json` + state；**0 ledger / frozen / prereg / ADR / config / E3**（mine）；display-only。

## 2026-08-08 (c) Reddit 散户情绪激活 — 零凭证 Atom RSS（OAuth 堵死的唯一存活路径）

**背景**：业主报告 Reddit API 申请失败（2026 Responsible Builder 政策）。实证三路 `.json` 全 403（通用 UA / 描述性 UA / old.reddit）→ 论坛"加 .json 免密钥"捷径已死；`.rss` 端点 200 存活（Reddit 自家公开 Atom 订阅源，ToS-clean，G7）。OAuth token 端点 401（在线，只等凭证，但凭证申请被堵）。StockTwits 免费 API 从数据中心 IP 被 Cloudflare 403。

**交付**（`reddit_sentiment.py` 双传输 + 新 fetch + export）：
- `transport=auto|praw|rss`（`auto`=有凭证 PRAW / 无凭证 RSS）；`.rss` 经 `defusedxml`（XXE-safe）解析 + `bs4` HTML→text + 复用既有 `_aggregate_snapshot`/ledger/sha256 纪律；每 subreddit 失败/畸形 XML 跳过不中断；`HostSpacingPolicy` ≥2s + 有界 429 重试。
- **ticker 抽取实证修正**：原 case-insensitive 裸词把英文词当 ticker（首跑 top = ARE/SO/NOW/well/tech 全是英文）。真实 WSB `/new` 数据驱动：cashtag 几乎不用（仅 `$HTZ`×1），真 ticker 大写裸词（PLTR×10/SMCI×10/TTWO×4），英文词小写 → **case 是判别器**。改为：cashtag（任意大小写）+ 大写裸词 ≥4（短 ticker 如 ARE/SO/M 仍需 `$`）。修后 live 输出全真 S&P（PLTR/SMCI/TSLA/UBER/TTWO/EPAM/SNDK）。
- **修 ordering bug**：曾把 FinBERT 下载移到凭证检查前 → 缺凭证 `transport=praw` 先下 438MB 再 raise，撑爆 `/tmp` 致全套 pytest 挂起。改回 pull（含凭证检查）→ FinBERT 下载后。
- `scripts/reddit_fetch.py`（零凭证，扫 566 S&P panel；`auto` 将来业主有凭证自动升级 PRAW 带 score）。
- `export_reddit_meta` 稳定 superset schema（13 key 两分支同构）→ `tsc --noEmit` CLEAN。修了并发 session 的 build-break（其版 reddit export 漏 `subreddits`/`collector`/`mode` → web 类型检查失败；已 revert）。`reddit.json` 现 `status: live`，7 真实 ticker picks。

**反泄漏底线（unchanged）**：forward-only（Pushshift 2023 死，无 permissive 历史源）→ 无 PIT 历史 → **进不了回测**；`mode: exploratory`，仅终端展示，绝不进 OOS 管线（7-gate rubric L108 判决不变）。1 行 `data_ingest` ledger（RSS，`score_available: false`）。

**与并发 session 协调**：handoff (b) 记录并发 session 观测到我的 reddit 改动（"并发 worker"），其 sonnet agent 试同款 export 改动但漏 `subreddits` → build-break → 已 revert；其提交仅 stage 自己 7 文件，reddit 模块整体留我。**前端 `reddit-view.tsx` 仍为占位符**（不渲染 picks）——留前端 owner 接 `status==="live"` 分支（需配套 i18n key），避免与并发 session 的 web-build 管护冲突。

**验证**：23 reddit 测试绿（含 malformed-XML 跳过 / case-aware 抽取 / auto-fallback）；全套 hermetic pytest exit 0（ordering bug 修后无 FinBERT 下载、无挂起）；ruff clean；`tsc --noEmit` CLEAN；真实 RSS 拉取 E2E（FinBERT 缓存于 `data/cache/`，首跑下载 ~438MB 一次性）。

**未提交**：`reddit_sentiment.py`(M) + `reddit_fetch.py`(??) + `test_reddit_sentiment.py`(M) + `export_terminal_data.py`(M, reddit export 增量) + `reddit.json`(M, live) + `runs/ledger.jsonl`(M, 1 data_ingest 行) + state(M)。留业主审阅后提交（或与并发 session 协调）。

**边界**：本轮 display-only ingest；**0 frozen surface / prereg / ADR / config / E3 改动**；未跑 confirmatory/forward/strategy；未触研究管线。

## 2026-08-08 (d) 实时数据 + 自适应校正循环 — 调研 + 深度分析（PROPOSED，业主决策）

业主提"历史数据补完后→实时更新 + 用最新数据自校正模型→迭代至可观预测"。派 2 sonnet 调研：**web 路 [1210] ×2 死**（proxy 今日不稳）→ opus 直接 WebSearch（3 路：walk-forward 重校准 / DSR·PBO / adaptive-vs-frozen OOS 证据）；repo 路成功。交付 2 文档：① `reports/2026-08-08-live-data-calibration-infrastructure-report.md`（既有基建盘点，908 行，34 文件引用，核对属实）；② `reports/design/2026-08-08-live-adaptive-calibration-analysis.md`（综合分析 + 推荐）。

**核心结论**：「用最新数据自校正」**合法 iff "更好" = 校准更准 + 漂移报警 + 诚实 forward 跟踪**（Track A，复用 `score_calibration` + E3，display-only，0 frozen/ledger/config）。**"更好" = IC 变正 则数据不可达**——power floor σ(IC)≈0.10（look-3 等价需 ~36 年）；Gu-Kelly-Xiu 2020 最佳月 OOS R² 仅 1.08–1.80%，且**主导因素是模型类不是更新频率**。自适应追 IC = rerun-to-significance + 多重检验膨胀（Bailey-López de Prado 2014："DSR/PBO especially useful when research is highly adaptive"；每轮 auto-tune = 一次 trial，必须 deflate）。

**两轨**：**Track A（推荐，合规）** = A1 walk-forward 校准重训（expanding realized 窗，`walk_forward=True` display 变体）+ A2 漂移报警（滚动 OOS 分布/cond-IC vs 历史，纯显示）+ A3 诚实 forward 累加器（E3-lite 或 E3 本体 owner-GO；commit→reveal(+21d)→score→显示序列，**绝不喂回训练**）。**Track B（gated，大概率仍 null）** = 研究层在线学习追 IC：需新预注册 + 逐周期 `config_committed` + DSR/PBO 预算 + 硬隔离 Track C；且与 null 定帧冲突（memory 勿追新 alpha）→ **需业主显式 GO**。

**"可观"重定义**：校准可靠性（reliability 图近对角）+ 漂移诚实 + forward 命中率序列——**非 IC 变正**。这是数据允许且对 fintech 终端真正有用的胜条件。

**边界**：本轮纯 docs（2 新 PROPOSED）+ state；**0 frozen / ledger / config / E3 / 代码**改动；未跑 research/forward。**待业主**：选 Track A（推荐）/ Track B（gated，需新预注册）/ 拓宽 framing（与 null 定帧冲突）。

## 2026-08-08 (e) Track A 落地 — 模型漂移监测模块（leakage-safe，display-only）

业主授权"建最有价值内容直至不可再优化"。依 (d) 的 Track A 推荐，落地漂移监测（"自适应循环"的 leakage-safe 信号，不喂回训练）：

- `src/aionis/eval/model_drift.py`（新）：PSI（score 分布漂移，recent 6 实现月 vs 历史）+ 滚动截面 rank-IC（recent vs full）。**realized-only**（复用 `score_calibration.build_pair_frame` + latest 未实现月排除契约）。regime 阈值 stable<0.1<moderate<0.25<significant。11 hermetic 测试（PSI 正确性/常数退化、rank-IC 方向、**反泄漏：未实现最新月排除**、degeneracy→None、summary skip）。
- `scripts/export_terminal_data.py`：`export_model_health()` → `model_health.json`（per-region drift + methodology）。
- `web/`：`model-health-view.tsx` + `/model-health` route + sidebar Monitor 组 + i18n zh/en；契约测试 `test_model_health_shape`。
- **实测（真实 OOS）**：US PSI 0.156（moderate，IC 全程 +0.004 / 最近 +0.012 均 null）；CN PSI 0.534（significant，score 分布漂 + base rate 0.475→0.385；IC −0.036→+0.07 噪声翻转 = null）。

**为何这是"自适应循环"的合规解**：漂移检测 = "模型注意到近期行为偏离历史" → 给人看（**不自动重训**）。把"用最新数据自校正"实现为校准/漂移/跟踪的诚实显示，而非喂回训练（rerun-to-significance 禁）。这是 (d) Track A 的第一块；A2（漂移）已交付，A3（forward 命中率累加器）= 既有 `export_picks_backtest`（131 月 track record），A1（walk-forward 校准 eval）留后续。

**边界**：本轮 `src/aionis/eval/model_drift.py`（新 display 工具，类比 `ff5_residual`/`score_calibration`，不写 ledger/frozen）+ export（additive）+ tests + web + state；**0 ledger / frozen / prereg / ADR / config / E3**；display-only，不进研究管线。

**验证**：ruff 全 repo clean；model_drift 11 + web 契约 19 测试绿；web build OK（18/18，`/model-health` 渲染）；全套 hermetic pytest 提交前确认。

## 2026-08-08 (f) Track Adaptive 启动 — 自适应重训预注册（PROPOSED，业主授权反转 framing）

业主 4 指令处置：①**push**（`4b8d583`+`a755339` 已推 origin/main）②**reddit nav 恢复**（`a755339`：取消注释 `/reddit` 入口，现经零凭证 RSS live）③**form4 5-issuer 完成 re-export**（`a755339`，16564 txns，全 5 issuer × 2013-2026）④**"真的要走 Track B（在线学习追 IC）"**。

**命名撞车处置**：既有 `docs/track-b-preregistration.md` 是**冻结的七主题平台**（ADR-011，2026-08-02，config_committed）。把"在线学习追 IC"重命名为 **Track Adaptive** 避免污染冻结面。

**Track Adaptive = 重大方向反转**：业主显式授权反转 2026-08-05 option A 的"勿追新 alpha"锁（**仅对该特定路径**）。memory `aionis-publication-framing-option-a` 已加 2026-08-08 addendum（Track Adaptive 授权，仅限有纪律路径；无纪律 alpha-chasing 仍禁）。

**交付 `docs/track-adaptive-preregistration.md`（PROPOSED，未冻结）**：两尾 null-expected claim（`IC_adaptive − IC_frozen` 配对差，HAC）；扩窗重训默认（GKX 2020 先例）+ purge+embargo 反泄漏；**DSR/PBO 多重检验预算**（每重训 cycle = 1 trial，deflate 后才报；PBO>0.5=过拟合高危）；复用 Track C 冻结 learner+universe+features 作比较器（隔离"更新"单一变量）；与 Track C **硬隔离**（新 config/ledger 行，不触 #49）。**待 owner 裁断 D1-D6**（更新机制 A/B/C、OOS 窗口、SESOI_diff、n_trials 预算、是否要 PBO、GO）→ `config_committed` → 首次 OOS。

**关键纪律**：本轮**未跑任何 adaptive learner、未观察任何 OOS metric**（反泄漏：config_committed BEFORE result）。诚实预期仍 null（power floor σ≈0.10 + GKX"更新频率非主导"）；价值 = 自适应基建 + 诚实跟踪，非制造正 IC。

**边界**：本轮 `docs/track-adaptive-preregistration.md`（新 PROPOSED）+ state + memory；**0 ledger / frozen / 既有 prereg / ADR / config / OOS / E3** 改动。

## 2026-08-08 (g) /themes 展示模块落地 —— 七主题数据"被看见"（display-only）

业主选"七主题数据被看见"（display 路径，非研究）。建 `export_themes()` + `/themes` 视图：**7 主题 × 真实聚合信号**（cross-sectional mean @ 最新实现月）：
- **① 价格**（live）：momentum_21d 0.021 / volatility_63d 0.023 / β_252d 0.68 / reversal_5d −0.019 + 12 月 sparkline
- **② 宏观**（live）：regime_macro composite z = **−0.28**（VIX+credit+term+DFF 惊喜）+ 60 日 sparkline
- **③ 基本面**（live）：ROE 0.044 / profit_margin 0.32 / revenue_growth_12m 0.005 / leverage 0.25 + sparkline
- **⑦ 市场结构**（live）：Amihud ~0（S&P 高流动性）/ β 0.68 + sparkline
- **⑥ 净成本**（partial）：bps sweep net_sharpe@5bps 0.125 / gross 0.149 / turnover 1.14
- **④ 新闻情绪**（forward_only，诚实空）、**⑤ 风险**（needs_work，alphalens adapter 待建，诚实空）

视图：themes-view.tsx（状态 Badge + 信号表 + 内联 SVG sparkline）+ `/themes` route + sidebar insights 组（LayersIcon）+ i18n zh/en。契约测试锁：7 主题、live/partial 必有 signal、非-live 必空（**禁 mock**）、methodology 披露"非 Track-B 冻结判语"。

**为何这是合规的"不被埋没"**：把七主题平台的特征工程（Track B 冻结的 feature infrastructure）以**聚合展示**形式见光——**不碰研究管线、不写 claim、不动 Track-B 冻结判语、不 mock**（④⑤诚实标 forward_only/needs_work）。这是 (d) 分析里 Track A display 路径的延续。

**边界**：本轮 `scripts/export_terminal_data.py`（additive `export_themes` + helpers + main call）+ `tests/test_web_terminal_data.py`（themes 契约）+ `web/`（新 view/route/nav/i18n + index.ts + themes.json）+ state；**0 ledger / frozen / 既有 prereg / ADR / config / OOS / E3**；display-only。

**验证**：ruff clean；20 web 契约测试绿（含新 themes）；web build OK（**19/19**，`/themes` 渲染）。

## 2026-08-09 (k) Track Adaptive OOS 结果 — NULL（第二条独立 null，强化 power floor）

**首次新 OOS 结果入账**（ledger #54, event=`oos_result`, phase=`track_adaptive`, config #53 n_estimators=100, 285 配对周）：

| 量 | 值 | 判读 |
|---|---:|---|
| IC_frozen（真·冻结基线） | +0.0156 | 弱正周 IC |
| IC_adaptive（扩窗周重训） | +0.0120 | 弱正，**低于冻结** |
| **IC_diff_weekly（adp−frz）** | **−0.0037** | adaptive 略**差**，非更好 |
| HAC t / p (n=285) | −1.14 / **0.26** | CI 跨零 = **NULL** |
| DSR (n_trials=1) | 0.0 | observed Sharpe 负 → P(true>0)≈0 |

**判读（预期 null）**：用新数据周重训 LightGBM **不改善**周截面 rank-IC（略差 = 过拟合/噪声，非信号）。climax 月频 null 之后的**第二条独立 null**（周频），强化 power floor（σ(IC)≈0.10；GKX "更新频率非主导"）。与 pre-reg §1 null-expected 一致。**有价值**：adaptive 基建 + leakage-safe 诚实跟踪已交付（`model_drift.py`、score_calibration、deflated_sharpe、sequential runner），非制造正 IC。

**执行历程**（业主多次催"更多 agents + 避免空转"）：① embargo 核验（review agent 标 CRITICAL → 批判核查 = false positive，realization-invariant 测试证 leak-free）；② n_estimators amend 500→100（feasibility，#53）；③ threading n_jobs=4/2 静默崩溃 ×3（LightGBML concurrency race）→ **sequential n_jobs=1 reliable**（~23min）；④ OOM 教训（并发 pytest+OOS）→ 重活不并发；⑤ 并行：OSS adaptive-learning 调研（reuse-first 结论：river BSD-3 可选，alibi-detect license-risky，Aionis 自有 wheel 足够）。

**sig-label 修复**：runner `FROZEN_SIG` 原 指 #52（ffd0c922），实际用 #53（b7621e6b）；已修（label-only，run 全程用 #53 n_estimators=100）。
**H6**：双跑 bit-identical 确认后台跑中（~23min，PID 815221）；确定性 pin（n_jobs=1, seed=0）→ 预期 PASS。结果在 `runs/track_adaptive_h6.log`。

**边界**：本轮 `runs/ledger.jsonl`（+1 行 #54 `oos_result`）+ `scripts/track_adaptive_run.py`（FROZEN_SIG 修）+ state；**0 既有 frozen/prereg/ADR 改动**；#49 月频 null 不动；display 层（drift/themes/model-health）与研究解耦。

## 2026-08-08 (j) Track Adaptive OOS 执行 — embargo 核验 + n_estimators amend + threading 崩溃→sequential

业主多次催"启用更多agents + 避免空转"。OOS 执行历程（高 stakes，climax 后首条新 OOS）：

- **embargo 核验**：独立 review agent 标 embargo=5 **CRITICAL**（train fwd 与 predict 重叠）。批判性核查 → **false positive**（predict 在周收盘 t_w，close[t_w] 已知；train fwd 用 close[<=t_w]，realized by predict point）。加 `test_expanding_arm_train_labels_realized_by_predict_time` realization-invariant 测试证 leak-free（8/8 runner 测试绿）。
- **n_estimators amend**：500 树 = 16.8s/fit → 285 fits ~27min 太慢；**amend2 (#53, sig b7621e6b)** 减到 100 树（3.2s/fit，both arms，comparison 自洽）。
- **threading 崩溃 ×3**：joblib threading n_jobs=4/2 均**静默崩溃**（LightGBM concurrency race，非内存——单独跑也崩，无 traceback）。→ **sequential (n_jobs=1)** 可靠（原 500-tree sequential 跑 15min 稳定）。
- **OOM 教训**：并发 full pytest + OOS → OOM kill（"不影响各自进程"的违反）。→ **重活不并发**；OOS 单独跑。
- **并行**：reuse-first OSS adaptive-learning 调研 agent 后台跑（river/scikit-multiflow/alibi-detect 等 license + Aionis 适配性 → `reports/design/` 待回报）。

**当前**：sequential OOS 跑中（100 树，n_jobs=1，~20min，frozen IC=0.0156 n=285，reliable single-thread）。完成 → H6 双跑（bit-identical）+ result-ledger 行 + 报告（诚实预期 null）。

**模型分层 + 复用账**：opus 编排（embargo 批判判断 + 集成）+ sonnet agent（review + OSS 调研）+ LightGBM frozen learner 复用（Track C #48 substrate）+ deflated_sharpe.py（DSR）+ joblib（sequential 走其 infra）。

**边界**：本轮 `scripts/track_adaptive_{run,amend1,amend2}.py` + `tests/test_track_adaptive_run.py` + `runs/ledger.jsonl`（#51/#52/#53）+ state；**0 既有 frozen/prereg/ADR 改动**（新增独立行，#49 null 不动）；**未观察 OOS metric**（run 中，config_committed #53 先于结果）。

## 2026-08-08 (i) Track Adaptive amend1 → WEEKLY ①（supersedes #51，真正有意义的比较）

业主 "选择① + 时间改为一周（周收盘后）"。但**先查清 Track C 训练机制**（反泄漏纪律：跑前核验估量是否 ill-posed）发现：Track C 的 "冻结基线" **本身就是扩窗月重训**（每 fold test = 1 个月，refit on growing past）→ **#51 的 mechanism A（月扩窗重训）≡ Track C 估计器**，IC_diff≈0 by construction，**恒等无意义**。

**amend1（#52，FROZEN）把比较做成有意义的 + 周频**：
- 基线 = **真·冻结**单次 LightGBM 拟合（2016-2020 周频，**永不重训**）——Track C 从未做过的真冻结；处理 = 周扩窗重训（每个 OOS 周收盘后 refit on expanding realized + 5-session embargo）。
- 估计量 = 周截面 rank-IC 差（5-session forward，HAC 两尾，null-expected）。
- **可行性核验**：`track_b_panel` 实为**日频**（2637 日，非月末）→ 周频管线可行（周末采样 + 从 close 算 5-session fwd + embargo=5）。
- **范围约束**：US-only（CN panel 是月末）；substrate = 日可得特征（价格+基本面+raw macro；Track C regime composite 月末 → 周频排除）。
- `scripts/track_adaptive_amend1.py`（新）；ledger 51→52，sig `ffd0c9227e692fe826faeac964607577f3a9ff3de3384907297bc396887c4659`，sha256 自洽，supersedes #51（append-only，#51 保留为作废记录）。

**关键纪律**：本轮**未跑任何 learner、未观察任何 OOS metric**（config_committed BEFORE result）。下一步 = `scripts/track_adaptive_run.py`（日 panel 周末采样 + 5-session fwd + 真冻结 vs 周扩窗重训 + IC_diff_weekly + HAC + DSR + H6 双跑）；首次 OOS 入新 ledger 行。诚实预期仍 null（周 IC 比 月 IC 更噪；power floor）。

**边界**：本轮 `scripts/track_adaptive_amend1.py`（新）+ `runs/ledger.jsonl`（+1 行 #52）+ `docs/track-adaptive-preregistration.md`（amend1 banner）+ state；**0 既有 frozen/prereg/ADR/config 改动**（新增独立行，#49 monthly null 不动）；未跑 research/forward。

## 2026-08-08 (h) Track Adaptive `config_committed` 冻结 —— climax 后首条新研究线 OOS 的反泄漏门

业主 "全默认"（D1-D6 全推荐默认 + D6 GO）。落地反泄漏硬锚（**config_committed 先于任何 OOS**）：

- **`scripts/track_adaptive_commit.py`**（新）：frozen config 17 keys —— 两尾 null-expected claim（`IC_diff = mean(IC_adaptive) − mean(IC_frozen)`，HAC）；mechanism A 扩窗月重训；**复用 Track C #48 sig `e14b9d44…` 的 41 特征/宇宙/learner 作基底**（零改动，隔离"更新 cadence"单一变量）；purge+embargo=21；SESOI_diff ±0.010；两门（主=HAC p α0.05，次=RCI 等价，非救场）；`n_trials=1`（**纠正 pre-reg D4** 把重训 cycle 误算 trial——重训 cycle 是单策略的 OOS walk-forward，非独立 trial）；DSR/PBO（`deflated_sharpe.py`）；H6；frozen 隔离。
- **ledger 50→51**：phase=`track_adaptive`, sig `892fb5068ed1e994db937e23c5b95f2d35ea796825c0c97937253e34605515ad`，**sha256 自洽已验**（recompute==stored）。
- pre-reg `docs/track-adaptive-preregistration.md` PROPOSED→**FROZEN**。
- 反转 memory `aionis-publication-framing-option-a`（2026-08-08 addendum 记录的"勿追新 alpha"，仅此纪律路径）。

**关键纪律**：本轮**未跑任何 adaptive learner、未观察任何 OOS metric**（`config_committed BEFORE result`）。下一步 = `scripts/track_adaptive_run.py`（扩窗月重训 + OOS + `IC_diff` + HAC + DSR + H6 双跑）；首次 OOS 结果入**新 ledger 行**。

**边界**：本轮 `scripts/track_adaptive_commit.py`（新）+ `runs/ledger.jsonl`（+1 行 #51）+ `docs/track-adaptive-preregistration.md`（FROZEN）+ state；**0 既有 frozen/prereg/ADR/config 改动**（新增独立行，不触 Track C #49 null）；未跑 research/forward。

## 2026-08-07 (a) 路径 A 上线 — 校准概率读数 + 板块聚合 + 公司名 + 诚实 null 免责

业主反馈"量化选股策略但没体现选股、ticker 没有公司名、要涨跌概率、要实时数据"。批判性自审后业主授权**路径 A**（保守：校准概率 + 板块 + 公司名 + 条件式读数 + 反泄漏护栏，非 trading bot）。`bb83117` 已 push origin/main。

**新增 3 模块（0 新 runtime deps）**：
- `src/aionis/eval/score_calibration.py` — Platt（默认）/ isotonic 校准：score → P(forward_return>0)，per-region，fit on realized OOS history，latest month 预测 OOS。**反泄漏契约**：latest month 从 fit 排除（NaN fwd_return drop），walk_forward=False 披露。**诚实 null 信号**：实测 US spread=0.20（prob range [0.42, 0.61]），CN spread=**0.05**（[0.44, 0.49] 基本平坦 = 模型承认无法区分涨跌）。
- `scripts/build_ticker_metadata.py` — cache ticker→(name, sector)：A 股 GitHub listing（5207 CN，`ZhuLinsen/daily_stock_analysis` 公开数据）+ SEC company_tickers.json（10398 US，公共域）+ EDGAR SIC map。25/25 picks 有公司名（海光信息/寒武纪/兆易创新/Coinbase 等）。
- `tests/test_score_calibration.py` — 15 hermetic 测试（单调性、null→紧 range、强信号→宽 range、反泄漏 latest-excluded、per-region、JSON round-trip）。

**enriched export（`export_terminal_data.py`）**：
- `export_picks`：**per-region 选择**（US top-10 + CN top-10 long；3+2 short），enriched name+sector+prob_up。**修了一个 bug**：原 global-latest（2026-08-03 = CN）静默丢掉 US（latest 2026-06-30）→ per-region latest 修复。
- `export_sector_breakdown`：板块聚合 mean score + mean P(up)，top/least favored。A 股 sector "Unclassified"（诚实标注非隐藏）。
- `picks_meta.json`：校准 meta + 诚实 null 免责。

**前端**：`picks-view.tsx` 重写（per-region 分组 + 双行渲染 name/ticker/sector + prob_up chip 按 base_rate 距离着色 + null 免责 banner）；新 `/sectors` 页（板块排行 + favor bar + 免责）；sidebar 加 Sectors；i18n zh+en。`pnpm build` exit 0。

**验证**：6 新 web 契约测试（enriched schema + 双 region 覆盖 + 校准披露 + sector shape + unclassified 披露）；27/27 新测试绿；全套 pytest exit 0；ruff clean（顺带修了 cot_fetch/form4_fetch 2 个预存 lint）；build exit 0。

**边界**：本轮 web/ + scripts/ + src/aionis/eval/ + tests/ + state；**0 ledger / frozen / prereg / ADR / config / E3**；无 real network/LLM/trial。校准是 display utility（类比 ff5_residual），不写 ledger，不改研究结论（rank-IC −0.0088 NULL 不受影响）。

**诚实 null 的可视化**：top picks（score +2.28 海光信息）的 prob_up = **0.444**（<base_rate 0.4751）= 模型在 CN 的轻微反向信号；top 板块（Natural Gas Transmission）mean prob = 0.484 ≈ base rate。概率聚集在 base rate 附近 = NULL 的概率空间可视化。

**待业主**：① 审线上 `/picks` + `/sectors`（部署后）② 实时价格（Alpaca 免费层 + GitHub Actions cron，下一切片）③ A 股 sector（需申万/东财行业源，当前 Unclassified）④ push 已完成。

## 2026-08-06 (j) Form 4 /insiders 升级 5-issuer（真实大额内部人卖出）+ COT 10-市场代码就绪

业主授权"优化到不能优化"。两条并行收尾：

**Form 4 /insiders 5-issuer 升级（真实数据，已 re-export）**：
- `scripts/form4_fetch.py` 跑通 5 大盘（AAPL/MSFT/NVDA/GOOGL/AMZN，2024-01..2026-06）→ `form4_aggregate.parquet` 2415 txns（4 buys / **2411 sells**）/ 62 内部人 / 5 issuer。
- top 内部人：**Jensen Huang 720 卖**（NVDA CEO 10b5-1 密集减持）、Pichai 227、Kress 190（NVDA CFO）、Hennessy 123、Herrington 107。NVDA 内部人卖出信号极强（1271/1272 是卖）。
- export_form4 re-run → `form4.json` 5-issuer。契约测试 `test_web_terminal_data` 仍绿（action buy/sell + buys/sells int）。

**COT 多空压力 10-市场代码就绪（数据刷新延后）**：
- `scripts/cot_fetch.py` 升级 10 市场跨资产集（S&P/Nasdaq/Russell/VIX/WTI/Gold/Silver/Copper/Euro FX/Yen）+ per-year resilient（cftc 单年超时跳过，不中断）。
- cftc.gov 当前 SSL/Connect 不稳（2024-2026 全 timeout/SSL），10-市场数据刷新延后；6-市场 parquet 保留（live cot.json 仍有效）。cftc 恢复后一键 `cot_fetch.py` → 10 市场。

**边界**：本轮 `web/src/data/aionis/form4.json`（5-issuer 真实）+ `scripts/cot_fetch.py`（10 市场 + resilient，已 commit 77f6311）+ state；**0 ledger / frozen / prereg / ADR / config / runs-data / E3**；Form 4 SEC 公共域（filed-date PIT）；COT 公共域。

## 2026-08-06 (i) 多空压力指数（CFTC COT）上线 —— 调研落地，free/no-API/公共域

业主问"散户情绪 + 多空资本流能不能找 free/no-API 源"。派 2 sonnet 调研 agent **都 [1210] fail** → opus 主线直接 web 搜索完成。**批判性结论（不对称）**：散户情绪**结构性受阻**（StockTwits 同 Reddit 式审批门；Google Trends 官方 API 2025-07 alpha 只给极少数、pytrends 脆弱 scrape + 修订）；多空资本流**干净可得**（CFTC COT + FINRA 空头）。业主授权做最有价值项 → 做**多空压力指数**。

**CFTC COT 多空压力指数 `/positioning`（已上线）**：
- 数据：CFTC Commitments of Traders（free、**无 API**、US 政府公共域、周频、归档快照**不可修订** = 最干净 PIT）。复用 MIT [`cot_reports`](https://github.com/NDelventhal/cot_reports)（0 造轮子）。
- 6 市场（legacy_fut，精确名匹配）：S&P 500 / Nasdaq 100 / VIX / WTI / Gold / Copper（US Dollar + 10Y Treasury 在 TFF 报告，legacy 缺，留 enrichment）。
- 构造：净非商业持仓 = Long−Short；52 周滚动 z-score（拥挤度）。综合 = 跨市场 mean z + 拥挤度强度 + 78 周 composite_series。
- 实测（2026-07-28）：composite z +0.19，crowding 0.9；S&P z+2.09（空头回补）、Nasdaq z−1.22（净空拥挤）、Gold 净多 +182k。
- 模块：KPI（composite z / crowding / latest）+ 综合 z 时序（recharts）+ **各市场 diverging z 条**（← 净空拥挤 / 净多拥挤 →，emerald/rose）+ methodology。

**脚本**：`scripts/cot_fetch.py`（cot_year × 3 年 legacy_fut → 精确名过滤 → net + 52w z → `data/cache/cot_aggregate.parquet`）。`export_cot`（读 parquet → `cot.json`，awaiting_fetch guard）。pyproject dashboard extra += `cot_reports>=0.1.3`（MIT permissive ✓）。

**散户情绪（诚实 decline）**：无干净 free/no-API/permissive/PIT-stable 源；Reddit 待激活；情绪维度由 Aionis 独有"选股确信度"覆盖。

**边界**：本轮 `scripts/cot_fetch.py` + `export_terminal_data.py`（export_cot）+ `pyproject.toml`/`uv.lock`（cot_reports MIT）+ `web/`（positioning 模块 + cot.json）+ state；**0 ledger / frozen / prereg / ADR / config / runs-data / E3**；COT US 政府公共域 permissive（filed 周五，归档不修订）；无 API（bulk CSV via cot_reports）。

## 2026-08-06 (h) Form 4 内部人模块上线（真实数据）+ 两个 parser schema bug 修复

业主问"为什么需要邮箱，能否避免" → 实测**能避免**：SEC 对 polite + 占位 UA + 小规模容忍（AAPL EFTS 返回 26 条无 429；Aionis 现有 584 个 13D 也是占位 UA 拉的）。

**跑通真实 fetch + 暴露/修了两个 parser schema bug**（agent fixture ≠ 真实 schema → 空洞绿，[[aionis-agent-dispatch-verification]] 既定 failure mode）：
1. **transactionCode A/D 错误**：parser 初版过滤 `transactionCode ∈ {A,D}`——但 SEC 惯例 `transactionCode = P(买)/S(卖)/M(行权)/A(award)/F/G`；A/D 是 `acquiredOrDisposedCode`（direction，**另一元素**）。修为 P/S（open-market）。AAPL 实测：nonDeriv codes = {S:83, M:54, F:31, G:8}（83 真实销售）。
2. **transactionDate 双 schema**：parser 初版只读 legacy `<year>/<month>/<day>`，但 SEC X0508+ 用 `<value>YYYY-MM-DD</value>`。真实 AAPL 申报用新 schema → 全 drop（110 文件 0 产出）。修为 dual-schema（value 优先，fallback year/month/day）。加 regression test 锁定。

**结果**：AAPL 近 2.5 年 → **83 真实内部人 SELL**（Tim Cook 21 / Katherine Adams 16 / Arthur Levinson 等 9 内部人，真实 shares + price）。`form4.json` status=ok。

**模块**：`/insiders` 上线（KPI buys/sells/insiders + top insiders + 近期交易流 + methodology）。sidebar alternative 组加内部人。`export_form4` 读 `form4_aggregate.parquet`（`scripts/form4_fetch.py` bounded 拉取，5 大盘 issuer；AAPL 已跑 + cache，多 issuer 一键扩）。

**复用 + 验证**：`_policy_get`（polite）+ `stakes_13d_efts` cache 模式 + `parse_form4_xml`。ruff clean + **21 测试绿**（含 new-schema regression）。**主线亲自验证**（re-parse 110 AAPL → 83 sells，非 agent 自述）。

**边界**：本轮 `src/aionis/ingest/form4*.py`（P/S + dual-schema fix）+ tests + scripts（`export_form4` + `form4_fetch.py`）+ web（insiders 模块 + `form4.json` 真实数据）+ state；**0 ledger / frozen / prereg / ADR / config / runs-data / E3**；Form 4 SEC 公共域 permissive（filed-date PIT）；占位 UA（SEC 容忍，业主无需邮箱）；AAPL 单 issuer 真实数据（多 issuer `form4_fetch.py` 一键扩）。

**待业主**：① 审 `/insiders`（真实 AAPL 内部人销售）② 多 issuer 扩展（跑 `form4_fetch.py`，~10min，加 MSFT/NVDA/GOOGL/AMZN）③ Quarto/旧站去留。

## 2026-08-06 (g) Form 4 XML orchestrator（opus fallback）+ export_terminal_data ruff bugfix

- Form 4 orchestrator agent (sonnet) **[1210] API 错失败**（memory 既定 proxy 不稳）。按 handoff 策略（agent fail → orchestrator opus 直接接），主线写 `src/aionis/ingest/form4_orchestrator.py`：
  - accession → EDGAR Archives `index.json` → pick Form 4 doc（robust `directory.item[]`/`items[]` schema，prefer `.xml` → accession `.txt` → fallback）→ fetch XML → parse（复用 `parse_form4_xml`）。
  - 复用 `_policy_get`（≥2s polite）+ 幂等 cache（index + xml 分别 cache）。`fetch_form4_transactions` 批量 + 容错（单 filing 失败不中断）。
  - `tests/test_form4_orchestrator.py`：9 hermetic 测试（monkeypatch `_policy_get`/`fetch_form4_filings`），URL 构造 / doc 选择 / 幂等 cache / parse pipeline / batch / empty。**9/9 绿**。
- **修了 `export_terminal_data.py` 的真实 lint bug**（之前 commit 没跑 ruff，疏忽）：B905 `zip()` 无 `strict=`（加 `strict=True`，长度不等即报错更安全）+ F841 `rl` 死变量（删）+ E501 长行（events label / reddit description，per-file-ignore 同 `build_static_site` 惯例）。**full repo ruff 现全 clean**。

**模型分层 + 复用账**：sonnet agent（[1210] fail）→ opus 主线 fallback（orchestrator + 验收）。复用 `_policy_get` / `parse_form4_xml` / `stakes_13d_efts` cache 模式。**0 造轮子**。

**边界**：本轮 `src/aionis/ingest/form4_orchestrator.py` + `tests/test_form4_orchestrator.py` + `scripts/export_terminal_data.py`（bugfix）+ `pyproject.toml`（per-file-ignore）+ state；**0 ledger / frozen / prereg / ADR / config / runs-data / E3**；无真实 EDGAR fetch（hermetic）。

**Form 4 可见模块**：ingest（efts + parser）+ orchestrator（fetch + parse pipeline）**都就绪 + 验证**。离可见仅差：① 真实 fetch 授权（bounded CIK 集 + 近窗）② SEC User-Agent 真实邮箱（现占位 `contact@example.com`）。业主给邮箱 + 授权后一次性跑通 → 终端模块。

## 2026-08-06 (f) Form 4 内部人 ingest — sonnet agent 交付，独立验证通过，已合并

agent (sonnet, worktree) 交付 Form 4 ingest；按 [[aionis-agent-dispatch-verification]] **独立核验（不信自述）**：
- `form4_efts.py`（152 行）：EFTS Form 4 metadata client，复用 `_policy_get`（≥2s polite）+ 幂等 disk cache + exp-backoff（transient only，4xx fast-fail）+ pagination。VERIFIED efts query（10-digit CIK + forms=4 + dateRange）。不 auto-fetch。
- `form4.py`（267 行）：XML parser，SEC `<value>` wrapper + nonDerivativeTable + transactionCode A/D 过滤 + shares/price 校验 + frozen dataclass。
- `docs/data-intake-edgar-form4.md`（177 行）：7-gate 全 PASS（SEC public domain G1✓ / filed-date PIT G2✓ / immutable G3✓ / exploratory G5 / polite G7）。
- `tests/test_form4.py`（409 行）：11 测试，5 XML fixture + 3 inline edge，assert **真实值**（CIK/ticker/date/A-D/shares/price/dtype/sort）+ degeneracy（empty/malformed/missing-filer/derivative-only/invalid-code/negative-shares）——**非空洞绿**。

**独立验证（我跑，非 agent 自述）**：ruff clean + pytest **11/11 passed**（main env, python 3.13.7）+ collection 无 error。merge-base 干净（worktree 落后 main 仅 conviction commit，无冲突）+ 0 frozen surface。

**Form 4 可见模块的剩余门槛（诚实）**：
- efts client 只给 metadata（accession list）；要真实交易需 **XML-fetch orchestrator**（按 accession 拉 EDGAR XML + parse）—— agent 未做（scope 外），是下一切片。
- User-Agent 占位 `contact@example.com`（SEC fair-access 要真实邮箱）—— 真实 fetch 前需业主邮箱。
- 真实 fetch 业主授权（bounded：小 CIK 集 + 近窗，polite ≥2s）。

**模型分层 + 复用账**：opus 主线（选股确信度方法论判断 + Form 4 验收判断）+ sonnet agent（Form 4 ingest 工程，复用 stakes_13d 模式，worktree 隔离并行）。复用：`_policy_get`/`http_policy`（polite）+ `stakes_13d_efts` 模式 + structlog。**0 造轮子**。

**边界**：本轮 `src/aionis/ingest/form4*.py` + `docs/data-intake-edgar-form4.md` + `tests/test_form4.py`（全 additive）+ state；**0 ledger / frozen / prereg / ADR / config / runs-data / E3**；Form 4 SEC public domain permissive；**无真实 EDGAR fetch**（hermetic only）。

## 2026-08-06 (e) 选股确信度指数（Aionis 独有模型元信号）+ Form 4 内部人 ingest（agent 并行中）

业主 `/goal` 授权推进推荐项（批判性比对 + agents 并行 + 模型分层 + 复用轮子禁造）。

**批判性修正**：原"选股确信度"想用峰度 → 不严谨（语义模糊）。改用**截面分散度（std + top/bottom decile spread）**，标准因子研究方法（Kelly-Pruitt-Su），有学术依据。

**选股确信度 `/conviction`（Aionis 独有，已上线）**：
- 数据：`track_c_confirmatory_oos_scores`（94k 行）→ 每月截面 std + decile spread
- 逻辑：latest std (0.6752) > trailing 12m mean (0.5763) → **high conviction**（模型当前找到清晰赢家）；低分散 = 低确信 regime（动量易失效）
- 复用：标准因子研究分散度概念（非 alphalens 库依赖，简单 std，避免造轮子）；recharts dual-line 图（std + decile_spread）
- export_pick_conviction + conviction-view（KPI + 时序图 + methodology callout）；sidebar insights 组加确信度

**Form 4 内部人 ingest（sonnet agent, worktree 隔离, 后台并行）**：
- 复用 `stakes_13d_efts` + `stakes_13d` 模式，EDGAR EFTS Form 4，7-gate doc + hermetic 测试，mode=exploratory
- 学术依据：Lakonishok-Lee 2001 / Cohen-Malloy-Pomorski 2012（内部人交易经典信号）
- agent 进行中（worktree 不干扰主线），回报后核验+集成（[[aionis-agent-dispatch-verification]]：不信 agent 自述，验 worktree diff + 测试）

**模型分层 + 复用账**：opus 主线（方法论判断 = 选股确信度定义）+ sonnet agent（Form 4 工程，复用 13D 模式）；选股确信度复用标准因子分散度（非自造指标）+ recharts（非自造图）。

**边界**：本轮 `web/src/`（+conviction）+ `scripts/export_terminal_data.py`（+export_pick_conviction）+ state；**0 ledger / frozen / prereg / ADR / config / runs-data / E3**；oos_scores 是已有 PIT 产物（派生分散度，非新数据）；Form 4 agent 在 worktree。

## 2026-08-06 (d) EDGAR 13D 聪明钱动向模块（Reddit 被政策闸门挡后的真实另类数据替代）

业主选 A（用 Aionis 已有 EDGAR 另类数据替代被 Reddit 拦截的散户热度）。

- **Reddit 现实**：业主点 create app 被 Responsible Builder Policy 直接拦截（2025-11 self-service API 关闭 + 新 app 须 approval，社区广泛报告被卡/拒）。Aionis 侧无法绕过。Reddit 页保持诚实"待激活"。
- **13D 数据**：`data/cache/efts_13d_<CIK>_*.json` 584 文件（历史 EFTS full-text-search），2872 条申报 / 417 机构 / 最新 **2024-12-16**（数据窗口到 2024-12，cached pulls 略滞后，真实但非实时）。SEC 公共域 permissive，filed-date PIT。
- **8K 数据不足**：`earnings_8k_forward_raw_20260731` 只有 1 条 T0/cik=1 测试条，跳过。
- **export_smart_money**：聚合 584 文件 → 近 60 申报 + 最活跃 10 机构（active #1 = Bank of America 44 次）。
- **修复一个 bug**：初版把 EDGAR `display_names[0]` 当 filer、`[1]` 当 target——反了。13D 惯例 `[0]`=subject company(issuer/target)、`[1]`=filer(reporting person/smart money)。证据：原 recent #1 显示 filer="CARVANA CO." target="GARCIA ERNEST C. II"（自然人不可能当 issuer）→ 修正后 filer=Garcia、target=Carvana(CVNA)，语义正确。
- **模块** `/smart-money`：KPI(total/filers/latest) + 最活跃机构排行 + 近期申报流（filer→target + ticker + new/amendment badge）。sidebar"另类数据"组加聪明钱。

**边界**：本轮 `web/src/`（+smart-money）+ `scripts/export_terminal_data.py`（+export_smart_money + 13D swap fix）+ state；**0 ledger / frozen / prereg / ADR / config / runs-data / E3**；13D 是 SEC 公共域 permissive（filed-date PIT，真实历史）；Reddit 仍待激活（政策阻塞，非 mock）。

**待业主**：① 审 `/smart-money` 观感 ② 13D 数据滞后到 2024-12（cached pulls），要不要重拉 EFTS 刷新到最新 ③ Reddit 是否走 approval（不阻塞当前）。

## 2026-08-06 (c) special 另类数据模块 — TACO 指数 + Reddit 散户热度

业主要求加小隐寺式 special 数据模块（Reddit 热门 + 川普 TACO 指数）让终端"更真实可靠"。

**反泄漏约束下的诚实实现**（CLAUDE.md `No mock/synthetic data in the real pipeline` + 7-gate）：
- **TACO 压力指数**（`/taco`）：真实 VIX（FRED ALFRED permissive，260 点 daily）+ 公开事件表（5 条 2025 川普关税事件，FT/CNBC/ABC 可证，**labeled 非 mock**）+ methodology callout 明示"示意性方法论，非 Aionis 研究 claim"。TACO 本身是 2025-04-09 起源的新闻 meme（FT Robert Armstrong coined），**无权威量化指数/数据集**。
- **Reddit 散户热度**（`/reddit`）：诚实标注"forward collector 待激活"。Aionis 已内置 `reddit_sentiment.py`（PRAW 8.0.2 + FinBERT，7-gate cleared，exploratory，**forward-collection only / no backfill**）但**从未激活 → 0 snapshots**。模块显示 collector 信息 + 7-gate clearance + 激活方法（配置 `REDDIT_CLIENT_ID/SECRET` + 跑 collector）。**不塞 mock 数据**。

**执行**：`export_terminal_data.py` += `export_taco`（VIX from `data/cache/alfred_VIXCLS.json` + 事件表）+ `export_reddit_meta`（status=awaiting_activation）。web += 2 view（taco-view: VIX recharts 图 + 事件表 + 计数 KPI + methodology callout；reddit-view: 状态卡 + 说明 + howto + 空 placeholder）+ 2 page + sidebar"另类数据"组 + i18n keys。

**验证**：poc dev `/Aionis/taco` + `/Aionis/reddit` HTTP 200 + 截图（terminal-taco-zh / terminal-reddit-zh）。

**边界**：本轮 `web/src/`（+taco/reddit 模块）+ `scripts/export_terminal_data.py`（+taco/reddit）+ state；**0 ledger / frozen surface / prereg / ADR / config / runs-data / E3**；VIX 是 FRED 公共域 permissive；事件表公开新闻 labeled；reddit 无数据（诚实标注，非 mock）；未触 E3；未激活 reddit collector（待业主 creds + GO）。

**待业主**：① 审 TACO/Reddit 模块观感 ② 是否激活 Reddit forward collector（需 `REDDIT_CLIENT_ID/SECRET` + 跑 collector ~分钟级）→ 真实散户热度榜 ③ TACO 事件表是否扩/调 ④ 方法论 illustrative 标注是否足够诚实。

## 2026-08-06 (b) 前端转向 fintech 数据终端 — Next.js + shadcn 复刻小隐寺风（已部署）

业主反馈：Quarto 学术站方向错（忘"个人兴趣研究、不公开发表"定位）+ 语言 tab 分页错（要单独切换按钮）+
要 **小隐寺数据中心 https://data.xiaoyinsi.com/ 那种金融科技风**（卡片墙、实时榜、数字密集）+ 加选股决策模块。
方法：深入研究小隐寺 → 找开源仓库复刻 → 不手搓。

**调研**：小隐寺 = Next.js 黑白极简（theme #fafafa/#000）另类数据终端（Reddit 情绪/政客交易/13F/IPO），
**不开源**（github 只有 investing-for-beginners 投资百科）。最佳相近 = **[abderrahimghazali/shadcn-fintech](https://github.com/abderrahimghazali/shadcn-fintech)**
（Next.js 16 + shadcn/ui + Tailwind v4 + recharts + live ticker + 深色模式 + 拖拽）。复刻基础。

**执行**（复用 shadcn-fintech 设计系统 + 组件，0 手搓；替换所有个人理财页面为 Aionis 模块）：
- clone shadcn-fintech 到 scratch `/home/re/code/aionis-web-poc/`，复用其 shadcn ui 组件库 + Tailwind oklch 黑白主题 +
  `live-ticker`（marquee 滚动）+ next-themes 深色 + Geist 字体。
- 新建 i18n（`src/i18n/`：context + localStorage + 中/英字典 + `LangToggle` 独立切换按钮，非 tab 分页）。
- 新建 Aionis 数据模块（学小隐寺卡片墙）：
  - **Overview**（`/dashboard`）：Hero + 5 KPI 卡 + 评分滚动条 + 选股预览 + 模块卡网格。
  - **选股决策榜**（`/picks`）：top-20 多头 + 5 空头，排名 + ticker + region + 模型评分 + 排名变化箭头（学散户情绪榜）。
  - **证据墙**（`/evidence`）：14 null 卡片流 + 统计计数（学政客交易卡片流）。
  - **Power Floor 监测**（`/power-floor`）：n_min KPI 三联 + look 表 + recharts σ_obs-vs-σ_null 散点。
  - **反泄漏仪表盘**（`/discipline`）：6 状态卡（PIT/embargo/H6/ledger/2-tail/k=1，全 PASS）。
- 删个人理财页面（accounts/transactions/transfers/cards/budgets/crypto/analytics/investments/sign-in/sign-up/...）。
- `next.config.ts`：`output: export` + `basePath: /Aionis`（GitHub Pages 静态导出）。
- 数据：`scripts/export_terminal_data.py`（复用 `export_quarto_data` 共享载荷 + 加 picks/shorts/metrics 从
  `track_c_confirmatory_oos_scores.parquet` 94438 行），输出 `web/src/data/aionis/*.json`（8 tracked JSON）。
- 修一个 build 阻塞：`ic_monthly.json` 含非法 `NaN`（CN 某月缺失）→ export 加 `pd.isna`→null + `allow_nan=False`（`export_quarto_data.py` 同修）。
- recharts Tooltip formatter 类型修正（value 含 undefined）。

**验证**：本地 `pnpm dev` 5 页全 200 + 截图（terminal-overview/picks/evidence/power-floor，深色中文 fintech 风）；
`pnpm build` exit 0，8 路由静态导出（含 `output: export`）。语言切换按钮工作（中/EN toggle）。

**移植 + 部署**：cp Next.js 项目到 `Aionis/web/`（排除 node_modules/.next/out）+ `scripts/export_terminal_data.py` +
`web/.gitignore`。CI `.github/workflows/deploy-pages.yml` 改为 pnpm + Node 22 → `pnpm build` → 部署 `web/out`。

**边界**：本轮 `web/`（新 Next.js 终端）+ `scripts/export_terminal_data.py` + `scripts/export_quarto_data.py`（ic_monthly sanitize）+
`.github/workflows/deploy-pages.yml`（Node 部署）+ state；**0 ledger / frozen surface / prereg / ADR / config / runs-data / E3 改动**；
web/src/data/aionis 是聚合 tracked JSON（非 frozen，从 gitignored runs/ 派生，类似 Quarto data 模式）；未跑 confirmatory/forward/strategy；
未触 E3。Quarto 站（`quarto-site/`）+ 旧站（`site/` + `build_static_site.py`）暂留 repo 不部署，待业主后续定去留（降级方法子页 / 归档 / 删）。

**待业主**：① 审线上 fintech 终端（部署后 https://rethymus.github.io/Aionis/）② Quarto 站 + 旧 site/ 去留（降级/归档/删）③ 选股榜是否加 forward-return 涨跌列（当前仅模型评分 + 排名变化）④ 是否加"实时感"（当前数据是 frozen 快照，非实时流）。

## 2026-08-06 (a) 研究站点前端改造 — Quarto 品牌化 + 交互表 + 复用轮子（本地验证完成，待业主授权提交/部署）

业主反馈：线上静态站（`site/index.html`，`scripts/build_static_site.py` 474 行手搓 HTML）"观感廉价、没复用
开源、别造轮子"。**诊断**：旧站生成层纯手搓（Tailwind/plotly 是轮子但拼装手搓）；本地在途 `quarto-site/`
（未提交）方向对（Quarto=Posit 学术发布轮子）但停在"默认 cosmo 模板"——没用 brand/value-box/itables，
CI 未切换，本地无 quarto。

**调研（现成轮子，全部直接复用，0 手搓）**：`_brand.yml`（[Posit brand-yml](https://posit-dev.github.io/brand-yml/)
+ [Quarto brand 文档](https://quarto.org/docs/authoring/brand.html)）；**itables** MIT（[Quarto 官方推荐交互表](http://itables.org/quarto.html)）；
Quarto dashboards/callouts/columns（v1.4+ 内置）；[Awesome Quarto](https://github.com/mcanouil/awesome-quarto) 范例。

**执行**：
- 本地装 **Quarto 1.10.18**（预编译单二进制 → `~/.local/bin/quarto`，不污染系统；CI 用 `quarto-dev/quarto-actions/setup@v2`）。
- `pyproject` quarto extra += `itables>=2.2` + `plotly>=5.18`；`uv lock` → itables v2.9.1（MIT，permissive-only 合规）。
- 新建 `quarto-site/_brand.yml`：语义色板（灰=CV-proxy / 蓝=chron / 红=confirmatory / 琥珀=power-floor / navy=primary）
  + 衬线标题 + 无衬线正文（**系统字体栈，无 webfont CDN，离线可复现**）。callout-important/warning/tip 直接对上 brand danger/warning/success。
- 升级 `_quarto.yml`：brand + search(overlay) + navbar(primary+icon) + docked sidebar + page-footer + open-graph/twitter-card
  + bread-crumbs + back-to-top + reader-mode + code-link。
- `scripts/export_quarto_data.py` += `export_ic_monthly()`（71 月 confirmatory IC 时序 2021-01..2026-06，tracked `data/ic_monthly.json`）。
- 重写 3 `.qmd`（英文默认）：`index`=callout KPI 三联（−0.0088 / NOT_EQUIVALENT / PASS）+ verdict + contribution；
  `results`=**itables 交互 evidence 表**（搜索/排序/分页）+ forest plot + 71 月 IC 时序 + bps 衰减曲线（plotly 品牌配色 + plotly_white）；
  `power-floor`=callout KPI（72.5/48.3/36.2 年）+ itables look 表 + σ_obs-vs-σ_null 散点。修正旧 `::: callout note` → 标准 `::: {.callout-note}`（fenced-div warning 清零）。
- 新 `tests/test_quarto_site_data.py`：11 契约测试（tracked `data/*.json`，hermetic，不依赖 runs/）——evidence 14 行 +
  confirmatory estimate −0.0088 + 所有 CI 跨零 + power-floor 3 looks/纯噪声界 + sigma excess≥2.0 + bps net 单调/gross 恒等 +
  ic_monthly 71 月/combined mean≈−0.0088。**11/11 绿**。

**验证**：本地 `quarto render` 三页全过（4 plotly 图执行 + itables JS 注入 + **0 warning**）；三页截图存（new-overview/
new-evidence/new-power-floor）；`ruff` clean；`pytest --collect-only` 无 error；代表性 `test_rank_ic` 绿。
（运维注：`uv sync --extra quarto` 会把 venv 同步成"仅该 extra"子集态 → 临时 `No module named pandas`；re-sync 全 extras 即修复。
CI workflow 用 `--extra dashboard --extra quarto` 不受影响。）

**发现的既有不一致（flag，未擅自改）**：`evidence.json` 实 **14 行**（`#12` 缺失），与项目"15 条 null"叙事 + manuscript
draft 表行数冲突。站点统一改为"14 configurations"（诚实）。若要 15，需业主确认 `#12` 对应哪条结果（疑似 Track C CN rank-IC
mean 0.0098 / p 0.46）后补。

**复用轮子账（回应业主诉求）**：Quarto（Posit 学术发布）+ brand-yml（Posit 规范）+ itables（MIT 交互表）+ plotly（交互图）
+ Bootstrap/cosmo（布局）+ callout/columns/tabset（Quarto 内置）= **0 行手搓 HTML/CSS 生成代码**；旧 `build_static_site.py`（474 行手搓）+ `site/` 待新站上线后归档。

**边界**：本轮 `quarto-site/`（新+改）+ `scripts/export_quarto_data.py` + `tests/test_quarto_site_data.py` + `pyproject.toml`
+ `uv.lock` + `.github/workflows/deploy-pages.yml`（前批已改）+ state；**0 ledger / frozen surface / prereg / ADR / config /
runs-data / E3 改动**；未跑 confirmatory/forward/strategy；未触 E3；**未 commit / 未 push / 未外发**（Pages 部署待业主点头）。

**待业主**：① **语言**（默认英文，匹配 manuscript/arXiv 英文化；若要中文/双语告知）② **授权 commit + push → CI 部署 Pages**
（外发，CI `quarto render quarto-site` → 公开站取代旧 `site/`）③ evidence `#12` 是否补（14 vs 15）④ 旧 `site/` +
`build_static_site.py` 何时归档。

## 2026-08-05 (i) power-floor 理论推导 — 纯噪声界 + ML 噪声超额（机制性定理）

业主第三次问"最具价值方向" + Stop hook 纠偏（自审通过即执行，勿再请示）。批判性过滤后选 power-floor
理论推导（唯一能显著抬高王冠贡献的方向；其余 ceremony/diminishing）。自审循环通过（闭式可推、复用既有
面板、不触冻结面）→ 直接执行。

**核心数学事实**：横截面 Spearman rank-IC 在无预测力零假设下 σ_null = 1/√(N−1)（闭式）。
N=462→0.047，N=929→0.033，N=1386→0.027。但 Aionis 21 个 IC 系列实测 σ(IC) 一致地是 σ_null 的
**2.0-4.4×（median 3.41×，min 2.03×，无例外）**。

**机制性结论**（比"σ≈0.10 floor"更精确诚实）：
- 纯噪声界 σ=0.047 时 look-3 n_min = (1.96×0.047/0.010)² ≈ **83 月 < 120** → 纯噪声本可在 look-3 达等价。
- 实测中位 σ=0.109 时 look-3 n_min ≈ **456 月** → 不可行。
- **power floor 不是纯数学必然，而是由 ML 噪声超额驱动**（拟合噪声 + 异方差 + 重叠）——稳健跨 21 系列。

**交付**：
- `scripts/ic_pure_noise_bound.py` — 算 N_cross（从中位 OOS 面板）+ σ_null + σ_obs + 超额比；21 系列。
  ruff clean。`runs/ic_pure_noise_bound.json`（gitignored）。
- `tests/test_ic_pure_noise_bound.py` — 6 测试（闭式 1/√(N−1) 正确性 + 单调 + 已知值 + N<2 NaN + n_cross_eff
  中位/分区/min-max + 缺列空）。6/6 绿。
- `reports/design/2026-08-05-power-floor-theoretical-derivation.md` — 闭式推导 + 21 系列超额表 + 机制分解
  （ML 拟合噪声/异方差/重叠）+ refined honest claim（"floor = 纯抽样界 + ML 超额"，非"σ≈0.10 规律"）。
- `manuscript/main.tex` §5.3 — 加"Theoretical pure-noise bound and the ML noise excess"子节
  （power-floor 升为"理论 + 经验 + 文献"三支撑）。

**批判性自审记录**（业主要求）：① 纯噪声界 0.047 < 实测 0.10，会否削弱？→ 不削弱，反而更 sharp（floor
由超额驱动，非纯界）；② 推导会否成兔子洞？→ 限定为闭式界 + 经验超额，不推一般理论；③ 外部 GKX 验证？
→ 先不做（可行性未证），内部 21 系列 + 闭式已足。

**边界**：本轮 1 新 script + 1 新 test + 1 新 note + manuscript §5.3 编辑 + state；**0 ledger / frozen surface /
prereg / ADR / config / data / E3 改动**；未跑 confirmatory/forward/strategy/research；未触 E3；未外发。

## 2026-08-05 (h) arXiv preprint scaffold（rec #2；framing a；PREP，未上传）

owner approved framing **(a)**（power-floor 定理为 lead）+ LaTeX 预制。交付 `manuscript/` 三件套：
- **`manuscript/main.tex`** — arXiv 通用 `\documentclass{article}`（仅标准宏包 amsmath/booktabs/hyperref/natbib；
  无自定义 .cls → 任何 TeX Live/Overleaf 可编译）。framing (a) 重排：power-floor 入 abstract+intro，§5 详述
  （n_min 869/580/435 + 跨 20 系列 σ∈[0.092,0.163] 实测）。§4 证据表 15 行；§7 复现声明指向 `docs/replication-availability.md`。
  数字与 ledger #49 + 中文 v1.0 + 英文 v1.0-en 交叉一致。
- **`manuscript/references.bib`** — 6 cited（gu2020empirical/goyal2008comprehensive/grinold1999active/lakens2017
  = WebSearch verified；schuirmann1987/jennison2000group = 标准 methods）+ 5 标准 extras（neweywest/obrienfleming/
  dieboldmariano/ke2017lightgbm/deprado2018）供扩展。
- **`manuscript/README.md`** — 构建（latexmk / Overleaf）+ framing 说明 + provenance + prep-to-submission gaps（诚实：
  uncompiled / 引用细节待确认 / 无图 / 作者占位 / venue 待选）+ elsarticle 可在定 venue 后替换。

**验证（无本地 TeX 工具链，无法编译）**：结构性自查——9 \begin = 9 \end，环境全配对
（abstract/center/enumerate/itemize×2/table/tabular×2），6 cite key 全部在 .bib 定义。

**边界（关键）**：owner 批准的是**预制**，**非上传**——arXiv 上传是不可逆外发，仍需业主单独点头。
本轮纯新建 `manuscript/` + state；**0 ledger / frozen surface / prereg / ADR / config / data / E3 改动**；
未跑 confirmatory/forward/strategy/research；未触 E3；**未外发**（无 arXiv 上传）。

**待业主**：① 在 Overleaf/自带 TeX 首次编译（修可能的 minor LaTeX 问题，标准宏包风险低）；② **授权 arXiv 上传**
（不可逆外发）；③ venue 定位（CFR/JFEc/RevFin，positioning brief §4）→ venue-specific tailoring（篇幅/强调）；
④ 作者+单位占位填充。

## 2026-08-05 (g) 发表强化 — power-floor 文献锚定 + 复现/数据可用性声明（2 新 PROPOSED 文档）

owner 第二次 `/goal` 授权"推进推荐项 + 批判性比对 + 并行 agents + 分层省 token + reuse-first"。
方向 1（power-floor 文献锚定）+ 互补的复现声明交付。**两 sonnet agent 均 [1210] 失败 → 全 opus §8 fallback**。

- **`reports/design/2026-08-05-power-floor-literature-anchoring.md`** — 把 σ≈0.10 从"我们的观察"升级为
  "有文献支撑的方法学结果"。WebSearch 验证 4 引用（出版商页 403 → 用作者公开 PDF + 搜索摘要）：
  ① **Gu-Kelly-Xiu (2020, RFS)** "Empirical Asset Pricing via Machine Learning"：最佳 ML 月 OOS R² **1.08-1.80%**
  → mean IC ~0.05-0.12 量级（R²≈IC²）；② **Goyal-Welch (2008, RFS 21(4):1455-1508)** 综评预测难度；
  ③ **Grinold-Kahn** *Active Portfolio Management* + Fundamental Law：年化 IR **0.5="good"** ⟹ mean IC/σ(IC)≈0.14
  ⟹ σ(IC)≈7×mean IC；若 mean IC≈0.015 → **σ(IC)≈0.10**（与 Aionis 0.106 量级一致）；④ **Schuirmann (1987) TOST** +
  **Lakens (2017)** equivalence primer（cited 2792）。**诚实边界**：精确 σ(IC)=0.10 的单一标准文献未找到——
  通过 mean IC 水平 + Fundamental Law 间接推断（§5 标注 ⚠️）。但 power-floor 结论稳健：只要 σ(IC)∈0.08-0.15
  文献一致区间，SESOI ±0.010 等价宣告即不可达（look-3 n_min σ=0.08 时 ~21 年，σ=0.15 时 ~58 年）。**推荐强 framing (a)**
  把 power-floor 升为一等方法学贡献（JFEc 计量 / CFR 再检验轨道）。

- **`docs/replication-availability.md`** — reproducible-by-construction 声明（positioning brief §6 标记的审稿人关切）。
  反泄漏纪律即复现契约（`config_committed` ledger + H6 bit-identical + tracked fetch 脚本）；逐源 license 表
  （EDGAR/FRED/ALFRED = US-gov 公共领域可再分发 / Tiingo/Alpaca 需自有 key 不再分发 / baostock A 股 / hanshof+pierrebrunelle
  MIT 成分）；独立方复现步骤（clone → .env → fetch → runner → H6 断言 bit-identical）；cover-letter 简版。
  引用全部核验真实（`.env.example` ✓ / `TIINGO_API_KEY`+`FRED_API_KEY` ✓ / H6 三重断言 ✓ / ledger 行号 ✓）。

**批判性比对（业主"先比对再选择"）**：研究新切片（强基线/LLM eval/新特征）低于产出收尾且重引入"治理>产出"失调；
E3 被 power floor 证可选。剩下自主高价值 = 抬高论文天花板（power-floor 锚定）+ 移除外发摩擦（复现声明）。

**分层 + reuse + 独立性**：2 sonnet `general-purpose` agent 均因 [1210] 失败（positioning→powerfloor 同模式，
WORKFLOW §17 停重试）→ opus §8 fallback 直接写。文献/复用：WebSearch（非 403 出版商页）+ 既有 ledger/脚本引用。
独立性局限：两文档均 opus 自写（非独立 subagent pass，已披露）；数字（climax #49 + power analysis）由既有双独立审计背书。

**边界**：本轮纯 docs（2 新 PROPOSED 文档）+ state；**0 ledger / frozen surface / prereg / ADR / config / data / E3 改动**；
未跑 confirmatory/forward/strategy/research；未触 E3；未外发（无 arXiv 上传）。**未改已定稿的 draft v1.0 / v1.0-en**
（两新文档通过 state + git 可发现；venue tailoring 时由业主决定是否并入引用，避免为边际指针重开定稿）。

**待业主**：① framing 选择（a 强 power-floor / b 中 / c 弱）；② 是否补 σ 直接实证（重算 Gu-Kelly-Xiu 公开 IC 系列 σ，
或合成 IC 噪声实验）；③ arXiv 投稿时把 4 引用并入 `references.bib`；④ 复现 package 形态（仅公共领域子集 + 用户自有 key /
Zenodo DOI 归档——外发需点头）。

## 2026-08-05 (f) 产物化收尾 — 英文 draft + 经济透镜 sweep + venue 定位 brief

owner `/goal` 授权"推进推荐项 + 批判性比对 + 并行 agents + 分层省 token + reuse-first 禁造轮子"。
3 推荐 + 1 fallback 全部交付（4 commit + 1 memory，全 push origin/main）：

- **`e94eac2` feat(site)** — 静态站点 Track C climax section（KPI tile + 表 + power-floor reframing）；
  3 新 hermetic 测试，25/25 绿；CI 部署成功（Pages 已更新）。
- **`3a3c2cf` feat(scripts)** — bps 敏感度 sweep（`track_b_net_cost_sweep_run`，**复用 `net_cost_summary`**，0 造轮子）：
  真实 Track B treatment 面板（ef321e9，125 月）衰减曲线 gross 0.149（bps=0）→ bps=5 0.125（≈0.43 年化，匹配 mount② / draft 引用）
  → bps=20 0.054 → bps=50 −0.088；**break-even ≈31 bps**；turnover 1.1444 跨 bps 恒等。8/8 hermetic 测试绿（含反退化：
  gross 跨 bps 恒等 + net 单调衰减 + 线性 cost scaling + break-even 插值 + _parse_bps 校验）。
- **`52a3d69` docs(draft)** — 英文 v1.0-en（`docs/methods-and-results-draft-en.md`，18KB）：sonnet agent 忠实翻译；
  全部关键数字（−0.0088/0.484/NOT_EQUIVALENT/RCI[−0.051,+0.027]/n_min 869/580/435/36.2y/2.772/99.44%）与 ledger #49
  + 中文 v1.0 交叉核对一致；framing 忠实（null + 纪律 + power-limit，非 equivalence declared）。
- **positioning brief**（本 commit）— `reports/design/2026-08-05-publishable-unit-positioning.md`：venue 匹配决策包。

**批判性比对（业主"先比对再选择"）**：英文 draft 不盲目翻 12KB——venue 决定语气/篇幅/重点，故 positioning brief
与翻译并行（而非串行）。venue 规格 web search 验证：**CFR**（Ivo Welch，免费 boutique，10-20 篇/年，~28 天 turnaround，
"takes more risks"/"all types of documents"，replication/re-examination 导向 = 最高 fit）/ **RevFin**（明示"irrespective
of whether the findings"= null 友好）/ **JFEc**（计量方法 fit，power-floor + J-T 门归宿）/ **Quant Finance**（理论+实证，
rapid）/ **arXiv q-fin.ST**（免费 baseline）。出版商精确页 403 处诚实标注 ⚠️，未编造数字。

**推荐路径**（brief §4）：① arXiv preprint（立即/免费/时间戳）；② CFR 首选（免费 + ~28 天 + null-再检验 fit，
frameworking (a) 反泄漏纪律为主）；③ 备选 JFEc（框架 b 计量）或 RevFin（null 友好）。

**分层 + reuse 合规**：2 sonnet `general-purpose` agent 并行（英文 draft ✅ 交付 / positioning ❌ [1210] 失败）；
positioning 失败 → **opus §8 fallback 直接写**（非独立 subagent pass，已披露）。sweep 复用既有 `net_cost_summary`
（0 造轮子）；CI 复用既有 deploy workflow；定位复用公开 venue 规格。

**独立性局限（披露）**：positioning 非独立 pass（agent [1210] 死，opus 自写）；英文 draft 单 agent + opus 数字核验；
sweep opus 自写 + 8 反退化测试。数字（climax #49 + power analysis）由既有 2026-08-05 双独立审计背书
（power-analysis sonnet review + climax diff review 均 APPROVE）。

**待业主**：① 选 venue 路径（CFR / JFEc / RevFin / 仅 arXiv）；② **授权 arXiv preprint 上传**（外发不可逆，需点头）；
③ framing 选择（a 治理 / b 计量 / c 估计量）；④ 英文 v1.0-en → venue-specific tailoring（brief §4 映射表已给）。

**边界**：本轮纯 docs/scripts(state-only)/state/memory；**0 ledger / frozen surface / prereg / ADR / config / data / E3
改动**；未跑 confirmatory/forward/strategy/research；未触 E3；未外发（无 arXiv 上传）。全套 hermetic pytest exit 0
（仅预存 forward-score/numpy warnings）；ruff clean。

## 2026-08-05 (d) Power analysis — J-T schedule 结构性欠功率（设计级发现，业主决策待定）

climax #49 后的自然跟进："look-1 NOT_EQUIVALENT → look-2/3 能否宣布等价？" opus 直接写
`scripts/track_c_power_analysis.py`（analytic HAC-SE 投影 + block bootstrap 2000 次 + min-n 计算）+
`runs/track_c_confirmatory_power_analysis.json`（gitignored artifact）。

**发现**（用 ledger #49 IC series 噪声 σ≈0.106 + ρ≈0.07，校准自 observed se_hac=0.0126@n=71）：
| Look | z | n_min 宣布等价 | P(equiv) | RCI half med |
|---|---:|---:|---:|---:|
| 1 (60) | 2.772 | 869 月（72.5y）| 0.0000 | 0.037 |
| 2 (90) | 2.263 | 580 月（48.3y）| 0.0000 | 0.025 |
| 3 (120) | 1.960 | 435 月（36.2y）| 0.0000 | 0.019 |

**判读**：look-1 NOT_EQUIVALENT 不是"look-1 太保守"的局部现象，而是**整个 60/90/120 schedule 在
SESOI ±0.010 下的必然状态**。月频 rank-IC 噪声地板（σ≈0.10）使 ±0.010 等价宣告在现实样本量不可达；
E3 forward-live 即使点火也需 ~36 年才达 look-3 等价。**这是诚实的方法学发现（power floor），非 bug**。

**贡献 reframing**（已写进 draft §5/§6）：项目主贡献 = ① 反泄漏纪律作为研究对象（不变）；② 15 条 null
点估计（强 evidence 无 alpha）；③ **power-limit 披露**（J-T ±0.010 在月频 rank-IC 的 power floor）。
非"等价已宣告"。draft §5 的 look-1 框架已从"局部保守"升级为"结构性欠功率"。

**业主 3 选项**（`reports/design/2026-08-05-track-c-power-analysis-options.md`）：
- **A（推荐）** 接受 reframing：不动冻结面，贡献 = null + 纪律 + power-limit。
- B 拓宽 SESOI ±0.025：新 amendment #49b；look-3 (n=120) RCI half 0.019 < 0.025 → 可达等价；
  但 post-hoc "moving goalposts" 嫌疑 + 等价意义减弱。
- C 延长 horizon n=435：不可行（36 年）。

**独立性**：sonnet review of power analysis methodology 派发中（`reports/audits/2026-08-05-power-analysis-review.md`
待回报）。数字由 opus 自算；bootstrap seed=0 pinned（H6 精神）。

**边界**：本轮纯新建 script + design brief + docs(state) 更新；**0 ledger / frozen surface / prereg / ADR 改动**；
未跑 confirmatory/forward/strategy；power analysis 用 gitignored artifact（不改 frozen surface）。

## 2026-08-05 (c) CONFIRMATORY CLIMAX — 首条 confirmatory OOS 入账（ledger #49）

owner D6 GO 授权（"按推荐方式处理 + 难度分层派 agent + 并行不互扰 + 冲突最高价值优先 + 结果不乐观再调整重测"）。
**目标**：把 Track C 联合折叠从 exploratory 升格为首条 confirmatory（项目的 logical climax）。

**判据**：null 在本项目是预期可发表产物，**非"不乐观"**；只有工程 bug（H6 失败 / 退化 / 时序违反）才触发
"调整重测"。实际结果 = null 点估计 + 欠功率 look-1，属预期，未触发调整。

**交付**：
- **`scripts/track_c_confirmatory_run.py`**（opus 直接写，反泄漏 climax 件）：
  - `verify_frozen_config()` 校验 `track_c_amend2.build_amendment()` 重现 sig `e14b9d44...`（漂移即 abort）
  - `assert_h6_identical()` 双跑 bit-identical（`.equals` + `.tobytes` + CSV hash 三重）
  - `jt_reachable_looks()` 作用在 `combined_ic_series`（Reading A：rank-IC 是 gated 估计量；cond_beta 仅 explanatory）
  - `build_confirmatory_row()` 构造 `confirmatory:first` ledger 行
  - artifact-reuse 模式（`TRACK_C_CONFIRMATORY_FROM_ARTIFACT=1`）：dry-run 已双跑证明 H6 → GO 直接 load
    summary.json 写 ledger，避免 46min 重跑（4 守卫：缺文件 / sig 错 / H6 False / 正常 append）
- **`tests/test_track_c_confirmatory_run.py`**：19/19 hermetic 绿（frozen sig 校验 + H6 pass/fail + look
  reachability 边界 + row 构造 + artifact-reuse 4 守卫 + 空/NaN 边缘用例）
- **dry-run 双跑**（~46min，macro join ONCE 优化后）：H6 bit-identical PASS → artifact-reuse GO commit 瞬时

**结果（ledger #49，bit-identical 于 asym41 exploratory）**：
| 量 | 值 | 判读 |
|---|---:|---|
| combined rank-IC 均值 | −0.008841 | null（p_hac=0.484，CI [−0.034,+0.016] 跨零）|
| US IC / CN IC | +0.0052 / −0.0265 | 双区均 null |
| conditional-IC β（regime 交互）| −0.0076（p=0.43）| null；multiplicity 预算 1 保持 |
| **J-T look-1**（n=60，RCI 99.44%）| **NOT_EQUIVALENT** | RCI [−0.051,+0.027] 宽于 ±0.010 SESOI = 欠功率 |
| H6 双跑 bit-identical | PASS | 真实数据确定性验证 |

**climax 判读（诚实）**：null 点估计 + 欠功率 look-1 = **预期结果**。
- 点估计 null（−0.0088）与全部 14 条 exploratory null 一致（confirmatory 等级下 treatment 仍无正增量）。
- look-1 NOT_EQUIVALENT 是 **power 声明**（OBF z=2.772 极保守 + 月频 IC se≈0.014 → 99.44% RCI 必然宽于
  SESOI），**非效应信号**。门设计意图就是 look-2(n=90)/look-3(n=120) 才判等价。
- **J-T 门拒绝在欠功率下过早宣布等价，即使点估计 null = 反泄漏纪律的活体演示 = 方法学贡献**。
- 严格等价判定需 E3 forward-live 累积日历时间（look-2 ≈ 2028，look-3 ≈ 2031）。

**独立性**：sonnet `general-purpose` code-reviewer APPROVE（0 CRITICAL / 1 HIGH=informational estimand
稳健 / 1 MEDIUM=test 边缘 gap[已补]/ 2 LOW）；7 项反泄漏审查全 PASS。报告
`reports/audits/2026-08-05-confirmatory-runner-review.md`。J-T + H6 + 沉积的可复现性由 frozen #48 + 脚本保证。

**docs**：`docs/methods-and-results-draft.md` v0.1 → **v1.0-draft**（§5 实填 confirmatory + §4 加 #14 asym41
彩排 / #15 confirmatory climax + §0 摘要 + §7 不越界声明更新）。

**边界**：本轮 1 行 ledger（#49 append-only confirmatory:first）+ 新建 scripts/tests/docs(state) + 1 份
audit report；**B/C/D/E1 + Track B 冻结面 / prereg / ADR / config 未改**；未跑 research/forward/strategy；
未触 E3。artifact-reuse 是持久化已 dry-run 验证的结果（config #48 frozen 先于 dry-run 观察 → config_committed
BEFORE result 保持）。

**待业主**：① 审 v1.0-draft → 定稿（中/英 + 期刊定位）；② 是否 push（origin/main 落后若干 commits）；
③ look-2/3 长期路径（E3 forward-live ignition，年级别）。

## 2026-08-05 P1 整合 + P0 confirmatory-GO brief（process→product 收尾）

owner 授权"按推荐方式处理 + 难度分层派 agent + 并行不互扰 + 冲突最高价值优先 + 结果不乐观再调整重测"。
**目标**：关闭 audit 3 caveat（HIGH #1 Phase B paired CI / HIGH #2 baseline 措辞 / MEDIUM #3 3-layer
沉积）+ 产出首条 confirmatory GO 的业主签注包。

**P1(a) Phase B paired HAC CI 补算 — DONE（orchestrator 直接做）**：
- Agent A `phaseb-ci`（sonnet）idle-without-result（handoff 反复记录的 OMC idle 模式）；按 memory
  `aionis-agent-dispatch-verification`（勿信 agent，从 repo 状态恢复）→ opus 直接重算 < 5s。
- 数字：mean −0.0008003561696833403（**bit-identical #28**）/ se_hac 0.00499 / ci_half 0.00977 /
  **CI [−0.01057, +0.00897]** / t_hac −0.1605 / p_hac 0.872（与 dm_p_mbb=0.870 同尾）/ n=125 / maxlag=4。
  CI 跨零，与全家族 null 一致。
- 产物：`runs/phase_b_differential_ci_recompute.json` + `reports/audits/2026-08-05-phase-b-paired-ci-recompute.md`。
- ledger 行 #28 **未改**（append-only）；`phase_b_run.py` **未跑**（用 #28 save_run 的 `ic_state`/`ic_base` parquet + `rank_ic_summary`）。

**P1(c) Track C 3-layer conditional-IC 沉积 — DONE（Agent B 交付 + opus 核验）**：
- Agent B `trackc-3layer`（sonnet）交付 `runs/track_c_3layer_conditional_ic.json`（opus 核验自洽）。
- 重建 3-layer composite（macro+global+meso-US-SIC，valid_n=2592 日）+ joint-fold IC 三臂 HAC 回归：
  **combined β=−0.0148 (p=0.21)** / us β=−0.0287 (p=0.13) / cn β=+0.004 (p=0.80)。全 null。
- **与 handoff § culmination 数字的差异**（诚实分级）：culmination 的 β_US=−0.001/β_CN=+0.015 用的是
  Track-B-fitter **单区** IC；本 artifact 用 **joint-fold per-region** IC（`track_c_joint_ic_series.parquet`
  的 us/cn/combined 列）。不同 series，两份均 exploratory sensitivity。
- combined 3-layer β=−0.0148 ≈ joint 2-layer cond_beta=−0.015（meso 加入影响微小，方向同）。
- 产物：json + `reports/audits/2026-08-05-track-c-3layer-artifact.md`。composite **未覆盖** cache（仍 2-layer）。

**P1(b) 措辞校准**：
- `docs/RESULTS.md` §2 行 B：`**not recorded**` → `[−0.01057, +0.00897]（2026-08-05 补算）` + §2 段落补 audit 链接。
- `docs/methods-and-results-draft.md` §4 行 #1（Phase B CI）+ 行 #9（3-layer）补实际数字 + 诚实分级脚注。
- **Baseline FF5/RANK 校准（audit HIGH #2）**：2026-08-03 batch 8 的"Both baselines now have REAL
  CV-proxy results"措辞应理解为 results 在 `docs/baseline-ladder-{ff5,rank}.md` + runner 输出，
  **非 ledger**（exploratory-by-design，同 Track C joint 模式）；ledger 只含 `config_committed` 行
  （#43 FF5 / #45 RANK）。RESULTS.md 正确未引用 baseline 数字（不入 ledger = 不进 RESULTS headline）。

**P0 — Track C confirmatory GO 业主签注包 — DELIVERED**：
- `reports/design/2026-08-05-track-c-confirmatory-go-brief.md`：6 决策（D1 估计量定义 / D2 区域-月
  group / D3 区域内 IC 等权 / D4 feature_cols 41 列不对称 / D5 meso US-only + 修 #48 / D6 GO+新 ledger
  行）+ 推荐一揽子（业主可回复"全部推荐"即开闸）。
- **核心张力**（brief D1）：amendment #47（A 股 cninfo→exploratory）与 #46 frozen"联合折叠"在
  confirmatory feature_cols 上有张力；推荐 D1=A（保留联合 machinery，feature 收窄为 US 23 / CN 12 +
  宏观 6 + regime 3 = 41 列不对称，LightGBM 默认处理 CN 行的 US-fundamental missing）。
- 签注后流程：起草修 #48 + confirmatory config → `config_committed`（业主动作）→ 首次 confirmatory
  OOS 跑 → J-T 门（已实现 `sesoi_gate.py`）→ draft v0.1 → v1.0 含首条 confirmatory。

**边界**：本轮纯 docs/audit/state + gitignored json；**0 ledger / frozen surface / prereg / ADR 改动**；
未跑 research/forward/strategy（Phase B 用现有 parquet；3-layer 用现有 IC series + composite 重建）；
未观察 confirmatory rank-IC / E3。A/B agent 只写 gitignored + final message（避 writer race：
`git clean -fd` 清 untracked 不清 gitignored，memory 事件证实）。

**独立性局限（披露）**：A idle 由 orchestrator 直接重算替代（非独立 subagent pass）；B 单一交付 +
opus 核验（非独立 verifier lane）。proxy 恢复后可补独立验证（同 Lane C self-audit 披露模式）。

**P0 跟进（owner D1=A 签注后，2026-08-05 续）**：起草 `scripts/track_c_amend2.py`（amendment #48，
  复用 commit_config/amend1 机制，累积 #46+#47+#48）+ `reports/design/2026-08-05-track-c-amend2-meso-us-only.md`。
  dry-run sig `e14b9d445411e74cc3418af3bde1148163725875b01ab75175bdde002225e738`（自洽 build==dryrun）；
  ruff clean；ledger 仍 47 行（未 append）。amendment 内容：meso 收窄 US-only SIC + confirmatory
  feature_cols 41（US 23 + CN 12 + macro 6）+ Q1 区域-月 group / D3 区域内 IC 等权 / D5 meso US-only
  冻结 + baostock G3 adjustflag=3 raw。**✅ ledger #48 已入账**（sig `e14b9d44...`，owner `--commit` 授权 2026-08-05；sha256 自洽已验；
  ledger 47→48 行）。**待第二个业主 GO**（d6_go：授权首次 confirmatory OOS 跑）。

**Extension A 进展（confirmatory 前置 machinery，`/goal` 推进）**：
- **A1 DONE（commit `c98f4c8`）**：`build_joint_panel` 支持 asymmetric region-specific feature_cols
  （`us_feature_cols`/`cn_feature_cols` keyword-only，向后兼容 shared）；2 反退化测试（union+NaN /
  drops non-listed）；11/11 track_c_joint 测试绿；ruff clean。**自验（opus 直接），非独立 verifier lane**
  （proxy [1210] subagent 不稳）。
- **runner 更新（commit `b178a67`）**：`track_c_joint_run.py` 加 `TRACK_C_JOINT_MODE` env toggle
  （shared 默认 / asymmetric35）；mode-tagged 产物不覆盖 shared。
- **数据齐备性（Agent `feat-readiness` 调研）**：US 23 + CN 12 = **100% on disk**（track_b_panel 1.17M
  行含 13 fund+10 price；cn_price_panel 141K 行含 10 price+2 extras）；macro_headline 6 = **0% on disk**
  需 A2 fetch（复用 `macro_dff.py` 模式）。报告 `reports/design/2026-08-05-confirmatory-41-feature-readiness.md`。
- **asymmetric35 exploratory DONE**（验证 A1 真实数据 + US fund signal）：25 特征联合折叠（68 folds /
  71 IC 月），**combined IC −0.0121 (CI [−0.035, +0.011], p=0.31) null**；US IC −0.0019 (n=65) / CN IC
  −0.0200 (n=66)；conditional-IC β=−0.0057 (p=0.61, R²=0.002)。**判读**：加 US fundamentals (13) + CN
  extras 未改善 IC（vs shared10 combined −0.007；asymmetric35 −0.012 更负但均 null）；US IC 几乎零 →
  US fundamentals 无 alpha → **坐实 null-favored**（双区域月频已定价）。产物 `runs/track_c_joint_asym35_*`
  （gitignored）。**Pandas4 concat-sort deprecation warning**（runner:165，非阻塞，待 sort=False fix）。
- **A2 macro 7-gate 调研**：Agent `macro-7gate` 跑 ~30min 后 **failed [1210]** API error（proxy 参数错；非 idle-without-result）。
  **Orchestrator WebSearch 实证 verdict = GREEN**（US 4 macro = GREEN，FRED public domain + ALFRED vintage PIT-safe；
  CN 2 macro = GREEN，WebSearch 确认 `MKTGDPCNA646NWDB`[World Bank, ALFRED vintage] + `CPALTT01CNM659N`[OECD, ALFRED vintage]
  都支持 PIT vintage；license：FRED non-commercial research OK（Aionis = research，no redistribution）；OECD non-commercial OK）。
  **修正之前 YELLOW 判断**（过保守）。CN macro 2 可作 headline（confirmatory 41，与 #48 macro_headline_6 一致，不需 amend）。
  macro 6 fetch（A2）+ broadcast join（A3）= ~半天工程；**asymmetric35 坐实 null**（US fund 无 alpha）→ confirmatory 41 大概率同 null
  （macro broadcast signal 弱），但 spec-faithful climax（J-T 门）需 41。**业主授权 A2/A3 完整 41 路径**。

**下一步（推进中）**：① ✅ asymmetric35 DONE（combined IC −0.0121 null，坐实 null-favored）；② ✅ A2 verdict
= YELLOW（orchestrator 判断；US 4 GREEN + CN 2 snapshot+exploratory）；③ **A2/A3 完整 41 路径 — 前置 machinery 全部就绪**：A2a DONE（cap fix 验证 `edc1add`，US macro 4 valid：
  term/credit 107/128，vix/dff 106/128）；**A2b DONE**（commit `9a13518`）：CN CPI（CPALTT01CNM659N）122/128 valid +
  CN GDP（MKTGDPCNA646NWDB annual）**0/128 NaN**（releases ~10 < Z_MIN=12，数据限制诚实披露）；**A3 DONE**：
  `MACRO_HEADLINE_6` + `join_macro_to_joint_panel`（per-region by-date map）；**runner asymmetric41 DONE**（第三模式
  `TRACK_C_JOINT_MODE=asymmetric41`）。**asymmetric41 exploratory 跑中**（验证 41 特征 machinery 真实数据；
  confirmatory 41 effective macro = US 4 + CN CPI = 5，GDP NaN，LightGBM native missing）。
  ④ **业主 d6_go**（第二个 GO）→ confirmatory OOS（41 + J-T 门）→ draft v1.0 climax。**climax 前置全部就绪，待业主 GO。**

## 2026-08-04 方法学+结果 draft v0.1（可发表单元；process→product）

owner 4× 重发 standing auth → 执行推荐 ②（方法学写定稿）。产出 `docs/methods-and-results-draft.md` v0.1（PROPOSED，业主审阅中文稿）：
- **METHODS 段（§1-3）= 贡献**：反泄漏纪律作为研究对象（config-before-result / PIT 全栈 / purged+chronological 验证 / H6 确定性 / J-T 等价门 / 两尾 null-favored 预注册 / multiplicity 预算 1 条件化）——全部 code/ledger-asserted，非叙述。Track C 联合折叠作为方法学新点（§3）。
- **RESULTS 段（§4）= 12 行 null 证据表**，诚实分级（CV-proxy vs chronological；exploratory vs confirmatory）。全部 null；0 条 confirmatory。
- **§5 占位** = Track C confirmatory GO（首条 confirmatory）。
- **§6 局限** 诚实（CV-proxy≠chronological；exploratory≠confirmatory；Track B 等价欠功率；幸存者；币种）。
- 数字源自 ledger/artifact；**独立核对**派 `evidence-audit`（sonnet，后台，read-only）→ `reports/audits/2026-08-04-evidence-integrity-audit.md`（运行中）。
- **治 "治理>产出" 失调**：把累积 process 转 product。未触冻结面/ledger；confirmatory 段 owner-gated。

## 2026-08-04 Track C 联合 US-CN 折叠估计量（confirmatory machinery；exploratory 走通中）

owner 授权"按推荐方式处理 + 难度分层派 agent + 并行不互扰 + 冲突最高价值优先 + 结果不乐观再调整重测"。**边界**：null-favored，"不乐观"= 工程/测试 bug 迭代修复，**非** rerun-to-significance（若现 rescue 诱惑则交 owner）。

**双车道并行（文件隔离）**：
- **Lane A（sonnet `general-purpose`，后台）→ [1210] 死，orchestrator(opus) 直接接手完成**：`reports/design/2026-08-04-shenwan-meso-7gate.md`。**裁定：CN 申万 meso via baostock = G3 结构性 fail（无 as-of/vintage，SWFC 回填，同 baostock-基本面先例）→ 快照冻结 + exploratory-only，不进 confirmatory headline**。**关键后果：confirmatory meso = US-only（SIC），= 当前实现状态，正式化为 spec-faithful config；不需 CN 申万 fetch**。本会话早先「3-layer US-only-meso 双区 conditional-IC null」即 spec-faithful exploratory 结果。正式化需 owner 在新 ledger 行修订 §1.1（meso=US-only for confirmatory；CN 申万 exploratory）。
- **Lane B（opus = 我，会话内）**：联合折叠估计量设计 + 实现（slop 高危件，本会话 agent 翻车 3 次同类）。

**Lane B 已交付 + 验证（未 commit）**：
- `reports/design/2026-08-04-track-c-joint-fold-spec.md`（设计 spec；D1 区域-月 group / D2 区域内 IC 等权联合 / D3 per-region 时序断言 / D4 regime as-of 月末 / D5 共享 10 price 特征；7 项 owner-decision 旗标 Q1-Q5）。
- `src/aionis/eval/track_c_joint.py`：`fit_track_c_joint` + `build_joint_panel` + `construct_region_month_groups`（D1）+ per-region 时序断言。核心洞察：**month-end 采样 + 日历月折边界 = per-region 21-session embargo 自动满足**（相邻月末 ≈ 21 sessions/区），无需逐区数交易日 → `cv.py`/`purgedcv` 0 改动。
- `tests/test_track_c_joint.py`：9 反退化测试（区域-月 group、build_joint_panel 双区+窗口、per-region 时序断言抓违反、月末逐区采样幂等、单区拒绝、**e2e H6 bit-identical 双跑**、combined_ic=区域 IC 等权）。**9/9 绿**。
- `scripts/track_c_joint_run.py`：exploratory runner（PHASE_C_NO_LEDGER；产出 `runs/track_c_joint_*` gitignored）。
- **验证**：`tests/test_track_c_joint.py` 9/9 ✓；全套 hermetic pytest **exit 0**（无回归）；`ruff check` 全清。

**Lane B 真实数据证据（DONE；exploratory，NO ledger）**：`scripts/track_c_joint_run.py` 在真实 US(566 tickers) + CN(929) 联合月末面板跑通（68 folds / 71 IC 月，oos_scores 94,438 行双区，score std 0.508 非退化）。**combined rank-IC −0.0070，CI(−0.030,+0.016) 跨零，p_hac=0.55 → null**；US IC −0.002 / CN IC −0.014（双区均 null）；**conditional-IC β=−0.015，p=0.20（无 regime 交互），R²=0.018**。= 又一条 null（符合 null-favored；与 Track B null + 早先 CN 单区 conditional-IC null 一致）。产物 `runs/track_c_joint_{summary.json,ic_series.parquet,oos_scores.parquet}`（gitignored）。**非 confirmatory 判读**（10 共享 price 特征 + region-month group D1 默认，#46 group 未冻结）。

**关键设计决策（confirmatory 前需 owner 签注，spec §7 Q1-Q5）**：
- Q1 lambdarank group = **区域-月**（D1，币种干净；#46 未冻结 group 构造）。
- Q2 联合 IC = 区域内 IC 等权（D2）。
- Q3 confirmatory feature_cols = 全 #46 54 列（exploratory 用共享 10 price）。
- Q4 meso（依赖 Lane A 裁定）。
- Q5 confirmatory 跑 = owner GO + 新 ledger 行。

**Lane C 独立 review 结果（agent 车道失败 → 确定性自审 + 披露）**：`jointfold-review`（sonnet）2 次 idle-without-verdict（[1210] proxy 日，agent 车道不稳：Lane A 死、Lane C idle）。按 WORKFLOW §17（2 次相同失败 → stop）+ §8（从 repo 状态恢复，勿信 worker prose），停重试，改**确定性自审**（opus 自审 + grep 核验关键接线 + 测试/真实跑证据），**独立性局限明示**：
- **I1 per-region 时序**：`_assert_per_region_chronological`（track_c_joint.py:359）在折循环内、`splits.append`（:360）前调用，无 try/except 包裹 → 不可跳过 ✓（grep 核验）。
- **I2 train-only binner**：`fit_monthly_bins(train_returns=...)`（:382-383）仅喂 train ✓。
- **I5 region-month group**：`(y*12+m)*2+code`（:111），us/cn 分离 ✓。
- **测试实质性**：e2e fixture 70 月×50 ticker+signal 0.3+`check_exact=True`（H6 严格）→ 非化妆品测试 ✓。
- **证据**：9/9 反退化测试 + 全套 pytest exit 0 + 真实跑非退化（score std 0.508）双区正确 shape。
- **Verdict**：machinery 确定性验证通过（self-audit + tests + real run）。**独立性局限**：非真正独立 pass（agent 车道 [1210] 失败）；proxy 恢复后可补独立 review。2 个 LOW note（e2e 未 assert IC>0；per-region assert 对单边缺席区域 skip——真实数据两区恒在，不影响）。

**边界**：本轮纯新建文件 + state；0 冻结面/ledger/prereg/ADR 改动；未观察 confirmatory rank-IC 结论；未触 E3。

## 2026-08-04 Track C conditional-IC（3-layer regime，null）— 会话 culmination

meso 3rd 层完成（`33b5cfb`，US SIC=EDGAR 公共域 `phase_d_sic_map.parquet` 588 tickers；CN 申万 baostock `ENABLE_CN_FETCH=1` 门控默认 off → meso 现 US-only，sha256 `e9f30d94`）。composite builder 升级 3-layer（`f7c5789`，sha256 `0cb7409e`，3021 日/valid 2592）。

**双区域 conditional rank-IC（IC_t ~ regime_t, HAC）**：
| regime 组成 | US β (p) | CN β (p) |
|---|---|---|
| 2-layer (macro+global) | -0.008 (0.48) | **+0.034 (0.07 边际)** |
| 3-layer (+meso US-only) | -0.001 (0.95) | +0.015 (0.36) |

**关键发现（方法论）**：2-layer 的 CN 边际交互（β=0.034, p=0.07）**被 meso 稀释到 null**（β=0.015, p=0.36）。**conditional-IC 对 regime 组成敏感**；spec-faithful 3-layer regime 下两区域 conditional-IC **均 null**（null-favored-consistent）。此前"CN 非对称 regime 交互"是 2-layer artifact，不稳健。

**待办（confirmatory，owner-gated）**：① 全 US+CN meso（CN 申万 fetch ~30min baostock）；② 联合 US-CN 折叠（per-region 日历 + 时序）；③ confirmatory 跑（冻结 #46/#47 + **新 ledger 行 = owner 动作**）+ J-T SESOI 门。当前 conditional-IC 用 Track B fitter on 单区域 + 独立 IC 系列回归（非联合折叠 confirmatory 估计量）。

**本会话总账（17 commits，main，未 push）**：S0 数据（CSI300 universe `425f5535` + A 股价格 `a4614876`）→ mount② 净成本（5bps net Sharpe ~0.43 年化）→ 首个 CN rank-IC(null, mean 0.0098 p=0.46) → 3 regime 层（macro `4bfd1949`/global DY `d189f53c`/meso `e9f30d94`）+ composite（3-layer `0cb7409e`）→ conditional-IC（3-layer null）。全套 hermetic pytest 绿，ruff 干净（预存 `track_c_commit.py:180` E501 仍待 owner）。

## 2026-08-04 regime composite（完成；2-layer exploratory）

owner `/goal`×5 推进 Track C regime_state。3 层中 **macro + global + composite** 完成，meso deferred。

- **macro 层**（`abab13e`，agent clean——本会话首个无需修复的）：vix+credit_spread(BAA-AAA)+term_spread(DGS10-DGS1)+dff_surprise 等权 past-only z-score。**EPU 4-line**：无 permissive 中国 EPU 源（license+PIT+no-revision 门 fail）；frozen #46 本标 EPU"(exploratory)"，排除=保守合规；**confirmatory 需 config 修订（新 ledger 行）**。sha256 `4bfd1949`。
- **global DY 层**（`9093100`，agent + 我核验）：US-CN EW 市场收益 → Diebold-Yilmaz 广义 FEVD（**statsmodels VAR + 标准公式**，未 vendor spillover-lab 因 PySide6 重）→ rolling-250 总 spillover。**GFEVD 公式逐行核验正确**（GIR=(ΦΣ)[i,j]/√Σ_jj；θ 行和 1；total=(θ01+θ10)/2；sanity：independent→~1%、correlated→~35%）。2 caveat：sha256 标签是 series-hash(`d189f53c`) 非 file-hash(`eb873732`)；lag-0 fallback 触发 30%（agent 误报"罕见"，建模选择非 bug）。
- **composite**（`df57a4a`，opus）：等权 past-only z-score 两层 + **TACO expanding σ**（[t0,t] 不回溯重算，frozen #46 normalization）。regime_state n=3021/valid 2585，mean 0.018/std 0.83，sha256 `deee9cf1`。
- **meso deferred**：申万/SIC 行业动量（数据源 7-gate 最难）→ composite 暂 2-layer（exploratory）。
- **Agent 质量教训强化**：macro(clean) + DY(公式正确，因 spec 含精确公式 + sanity 测试) → **精确 spec + 反退化/边界测试 = agent 能做对硬量化方法**（对比 net_cost/CSI300/cn_panel 盲派都出错）。

**下一步（待做，opus 设计重——conditional rank-IC 是 Track C 真正的 confirmatory 估计量）**：
1. **score × regime_state 交互 → conditional rank-IC**（IC 系列随 regime 变化？）。需 conditional-IC 框架设计（参考 `reports/design/2026-08-03-conditional-rank-ic-multiplicity.md`）——这是设计重活，slop 风险高，宜先定方案。
2. **meso 3rd 层**（申万/SIC，for full 3-layer composite）。
3. **联合 US-CN 折叠 + confirmatory 跑**（冻结 #46/#47 + 新 ledger 行）。

## 2026-08-04 Track C CN rank-IC 首探（完成；exploratory）

owner `/goal`×4 推进 Task#6。A 股 price-only 面板 → 首个 CN rank-IC。

- **CN 价格面板**（`data/cache/cn_price_panel.parquet`，gitignored）：141,208 行 / 929 tickers / 152 月末 (2014-01..2026-08) / 12 特征 (10 Track B price + limit_up_down_distance + suspension_flag) + forward_return_h。leakage self-check PASSED（特征只用 close≤t，标签用 close[t+21]）。
- **agent 质量第 3 例**：`cn-price-panel` agent 交付的 `build_cn_price_panel.py` 有 3 bug（① MultiIndex stack 后误赋 4 列名实为 11→Length mismatch；② leakage self-check 取非月末 raw 日期→越界；③ stack 依赖 index.name="date" 不健壮）。agent 的 15 测试又"绿"但空洞（测了 `compute_price_features` 被复用函数，没测 `_build_features` 包装）。opus 修 3 bug + 补 `_build_features` 回归测试（set 对比 + 排除 melt 残余）。
- **首个 CN rank-IC**（`scripts/track_c_a_run.py`，Track B fitter on CN，92 折 2019-01..2026-06）：**mean_ic 0.009836，ci_95 (-0.0165, 0.0362) 跨零，p_hac 0.4639 → NULL**；DM vs EW stat -2.19 / p=0.031（边际；n_trials=30 haircut 会洗掉）；IC std 0.1289。**与美股 Track B null 一致，符合 null-favored 预期**。corr(momentum_21d, fwd_ret)=-0.015（A 股短期反转 hint）。
- **诚实结论**：A 股 price-only rank-IC null = 可发表结果，**非"不佳"——不调整重测**（rerun-to-significance 禁）。下一步是 Track C 真正的 confirmatory 跑（regime 交互 + 联合折叠 + 冻结 #46/#47），不是"rescue"这个 exploratory null。
- **边界**：exploratory（Track B fitter on CN），**非 Track C confirmatory 估计量**，不写 ledger。IC series + OOS scores 存 `runs/track_c_cn_*`（gitignored）。
- **commits**：cherry-pick `78f7d5af`（agent 原始，3 文件）+ 本批 fix commit（3 bug 修复 + 回归测试 + runner）。

## 2026-08-04 OSS-survey + 并行派发批次（完成）

owner 授权"按推荐的数据与方式处理 + 难度分层派 agent + 并行不互扰 + 冲突高价值优先 + 结果不佳再调整重测"。

**已完成：**
- **修订 #47 提交**（`6bd360f`，owner 本会话明示授权）：A 股 cninfo 基本面 → exploratory-only（G1 处置），claim 收窄为 US-rank-IC（确认性）+ A 股 exploratory 条件化。ledger #47 sig `252cf7df` sha256 自洽已验；#46 冻结不变（append-only）。含 docs/track-c-preregistration.md §0+§3、ashare-fundamentals-source.md §3、scripts/track_c_amend1.py（可复现）、state 沉积。
- **清除 GPL orphan** `src/aionis/eval/finsaber_mount.py`（import backtrader GPLv3；真正的净成本层是 `eval/execution_costs.py`，已实现）。
- **baostock G3=raw** 已是 `ingest/ashare_price.py` 默认（adjustflag="3"）；intake 文档（`ab43454`）已覆盖。视作冻结默认。
- **OSS 轮子调研**（`420fba1`，今上午 + 同日勘误）+ 本轮补验：qlib=library-import CN 采集器（MIT,PIT-DB 实）；akshare=MIT 但 SSRN 论文实证其 PIT 不安全（重述值）→ 坐实"A 股 filed-date 基本面无 permissive 轮子"=结构性数据 gap，非手搓失败。

**完成（2 agent 回报 + 集成 + 修复；commits `5b561e4`/`8bbe6a6` cherry-pick + 本批 fix）：**
- **`csi300-intake`（Task#3，DONE clean）**：选 `index-constitution`（PyPI 实证 MIT + `py3-none-any` wheel=3.13✓ + 0.6.2/2026-07 + 内嵌 CSIndex 历史公告=零运行时 HTTP + opt-in/opt-out=PIT+survivorship-safe）。7-gate 全 PASS。`ingest/csi300_constituents.py`（lazy import 非 core dep + `enable_fetch=False` 默认 + snapshot+sha256 + `constituents_on(t)`）+ intake doc + 14 hermetic 测试（无 stub）。潜在风险：适配器调 `ic.history("csi300")` 而 PyPI 示例是 `ic.constituents_at(...)`——API 名待真实拉取时核实（owner-gated+fail-closed，不阻塞）。
- **`mount2-netcost`（Task#2，agent 交付 defective → orchestrator opus 重写 3 文件修复）**：agent 的 net_cost.py 有 **3 blocker**（turnover 退化：pre_trade 两分支都=0 + 注释撒谎；test 有空 `pass` stub；runner 整个计算被注释 `sys.exit(1)`）；且 11 测试是**欺骗性绿**（3-ticker fixture 致 long_short_returns 跳过→NaN→`if isfinite` 跳过 assert + 5 测的是 execution_costs 内核）。**重写后**：turnover 追踪 prev_target（union 对齐、逐期成本、no-drift 简化已诚实标注）；去 session_opens（turnover-bps 模型不需 open 价）；runner 加载真实 `oos_state.parquet`（`long_short_returns` 自动月末子采样）→ **本轮出真实数字**；12 测试含**反退化测试**（稳定分数→低 turnover，洗牌→高 turnover，直接抓 always-2.0）。
- **集成**：cherry-pick 两 commit（worktree 基是 `30ae69f` 非 `6bd360f`——worktree 创建时序问题；但两 commit 自身 diff 各 3 新文件纯新增→cherry-pick 安全，#47 未被回退，已验）。全套 hermetic pytest **exit 0**；ruff 干净；零 stub/TODO/pass。
- **⚠️ 运维教训（fold 进 orchestration-protocol §8）**：① worktree 基可能滞后——merge/前**必查 merge-base + commit 自身 diff**，勿信 `branch..HEAD` 累积 diff；② agent"全绿"必须**代码级核验**——A 的测试空洞绿（小 fixture→NaN→跳过 assert）肉眼不可见，靠反退化测试 + 真实数据跑才暴露；③"reuse-first"≠"import 了就算复用"——A import 了 execution_costs 却喂退化输入。

**mount② 真实结果（Track B treatment panel `ef321e9…`，bps=5，125 月 2016-2026）**：gross_sharpe 0.1487（月，年化≈0.51）→ **net_sharpe 0.1250**（年化≈0.43，成本吃 ~16%）；**avg_turnover 1.1444**（真实换手，非退化 2.0）；total_cost 715 bps 累计（≈5.7 bps/月，=5×1.14×1e-4 自洽）。注：此 panel 是 mtime 最新 run（未必 #41）；策略在 5bps 滑点下保住大部分 Sharpe。

**边界：** 本批仅 #47 commit（owner 授权）+ cherry-pick 2 agent commit + mount② fix；**未观察 OOS rank-IC**（net-cost 是 L-S 收益视角，非 rank-IC 估计量）；未触 B/C/D/E1/Track-B 冻结面；net_cost 是探索性工具（类比 ff5_residual，不接管线、不写 ledger）。`runs/track_b_net_cost.parquet` gitignored。

## 2026-08-04 `/loop` 批次 — 未提交在途工作批判性审计（GPL 清除 + site 恢复；未 commit）

owner `/loop` 授权"推进推荐项 + 批判性思维 + reuse-first + 模型分层省 token"。进入会话发现 main 上有一批**未提交的在途工作**（非本会话创建），独立审计发现 **2 个缺陷**，已采取明确正确的恢复/安全动作；judgment 项交 owner。

**缺陷 1（CRITICAL，已清除）— GPL 污染：** 批次把 `finsaber>=2.0.1` 加进 core deps + 新增 `src/aionis/eval/finsaber_mount.py`（直接 `import backtrader as bt` + 子类化 `bt.Strategy`）。核验（definitive）：`finsaber`=Apache-2.0（本身合规），但其 `Requires-Dist` **硬依赖** `backtrader>=1.9.78`=`GPLv3+`，CLAUDE.md 明令 EXCLUDE。→ 已从 pyproject 移除 finsaber；`uv lock --offline` 清除 backtrader+finsaber+colorlog；pyproject/lock 回到 committed（GPL-free，diff 空）。`finsaber_mount.py`（untracked、孤立、无任何 import 引用）排除不提交。见记忆 `aionis-finsaber-backtrader-gpl`。

**缺陷 2（回归，已恢复）— site 空壳化：** 批次的 `site/index.html` 把 committed 的**真实内联数据**（`const icData={...}` + 风险表 + FF5 表）替换成**占位符**（`const icData=null` + "待 ...json"；因 `build_static_site.py` 在 2 个 JSON 被删后重建产空壳，且有个未闭合 `<p>`）。→ `git checkout -- site/` 恢复 committed 已部署的良好站点（真实数据，`grep const icData={` 计数=1 确认）。

**测试：** 全套 hermetic pytest exit 0（仅 pre-existing forward-score/numpy warnings）；`ruff` 未本轮重跑（无 src 改动待验——pyproject/lock 回到 committed，site 回到 committed，均无新代码）。

**待 owner 裁断（未擅自提交——非本会话创建 + consequential）：**
1. **修订 #47（A 股 cninfo→exploratory-only）**：ledger 行已 append（sig `252cf7df`，phase=track_c），docs/ashare 报告同步；`track_c_amend1.py` docstring 称"owner authorized (B) 2026-08-03"但 tracked state（本文件/current.md）**未印证**。属 claim 收窄 scope change（保守、append-only、结构合规）。→ owner 确认授权后可提交（ledger+docs+track_c_amend1.py+ashare 报告）。
2. **oos_scores 管线**（`track_b_baseline.py` oos_scores 字段 + `track_b_a_run.py` 持久化 + `ranking_contract.py` 单行月 scalar→Series bugfix）：license-clean、verified-green、非 scope change；但与 mount② 消费耦合。→ 建议与 mount② 合为一个完整切片提交。
3. **mount② 净成本回测（reuse-first 重写）**：**禁用** finsaber/backtrader（GPL）；改用 **pyfolio-reloaded+empyrical（已在 lock，MIT/Apache）+ ~50 行确定性成本层**（next-open 成交 / bps slippage / turnover / 流动性上限）。待 owner 定成本参数。

**下一步（loop 续跑优先级，无 owner 回复时）：** P0 = 上述 3 项 owner 裁断；P1 = Track C S0 数据构造脚手架调研（冻结后允许，不写 ledger/不观察 rank-IC）：qlib 双区域 mount 接线点④ + cninfo MIT fetch（`rollysys/use_cninfo`）+ A 股价格 PIT（baostock 价格 MIT ✅，基本面 G3 reject）。子代理 dispatch 因 `[1210]` proxy 今日不稳 → orchestrator 直接 opus 写优先（handoff 既定策略）。

**边界：** 本批仅恢复/安全动作（site revert + GPL 清除）+ state/memory；**未 commit 任何 frozen surface / data**；ledger #47 行保持 in-tree 未提交原状；未跑 confirmatory/strategy/forward；未观察 E3；网络仅 PyPI 离线（uv lock）。

**续（loop 迭代 2 — owner 未回复 #47 授权 → 推进 P1 安全项）：**
- 提交 `5e2ce6d`：clean infra（`ranking_contract` 单行月 scalar→pooled-edges bugfix + Track B `oos_scores` 管线）；verified-green + ruff clean；非 scope change，**不需 owner 决策**。清树债。
- 提交 `ab43454`：2 份 S0 intake 文档（baostock A 股价格 7-gate + CN 宏观双层级 7-gate），**2 并行 sonnet `general-purpose` agent** 产出（绕过 `[1210]`，file-isolated，未触冻结面/未拉真实数据/未观察 rank-IC）。关键裁决：baostock 价格 **G3 CONDITIONAL**（复权因子 adjustflag 可追溯回改 → 需冻结策略：raw+本地因子快照 或 前复权全序列快照）；CN 宏观 **headline(ALFRED/OECD vintage) PASS 全 7 门** / **exploratory(NBS via mbk-dev/nbsc) G2+G3 FAIL → snapshot+sha256+exploratory-only**（EPU 先例）。
- **仍 pending owner**：① 修订 #47（A 股 cninfo→exploratory）授权确认；② mount② 净成本成本参数（slippage bps 等）；③ NBS G1 license 验证 + baostock G3 复权冻结策略裁决。
- **下一 loop 优先级（无 owner 回复时）**：qlib 双区域 mount 接线点④ 调研（S0 基础设施，POC 标注 ~3h 接线）或 cninfo MIT fetch（`rollysys/use_cninfo`）路径设计（exploratory 基本面）。子代理 `[1210]` 已验证 `general-purpose`+sonnet 可靠绕过 → 可继续 ≤2 并行 file-isolated 派发。

**续（loop 迭代 3 — owner 仍未回复决策；推进 P1 具体研究基础设施）：**
- 提交 `178d1fd`：**baostock A 股价格 ingest 适配器**（`src/aionis/ingest/ashare_price.py` + 5 hermetic 测试）。镜像 `market.py` US 侧模式；lazy import（baostock 非 core dep，`uv add baostock` 激活）；G3 默认 `adjustflag="3"`（raw，G3 方案 A，冻结策略延后到 config）；停牌→NaN（G6）；≥2s pause（G7）。**决策零依赖**（baostock 是冻结 prereg 批准源；intake 文档已提交；G3 策略延后 config）。5/5 测试通过 + ruff clean。未拉真实数据/未触冻结面/未写 ledger。
- **本轮累计 3 提交**（`5e2ce6d` infra + `ab43454` intake 文档 + `178d1fd` 适配器）—— 全部具体、安全、reuse-first、verified。
- **5 项 pending owner 决策不变**（修订 #47 授权 / mount② 成本参数 / NBS G1 license / baostock G3 冻结策略选方案 / 下一 S0 切片优先级）。**最高价值路径（真实 S0 数据、Track C rank-IC）仍被门控。**
- **下一 loop（无回复）候选**：A 股交易日历对齐（pandas-market-calendars XSHG/XSHE，配 baostock 适配器）或 CSI300 PIT 成分 intake（`index-constitution` MIT）。

**续（loop 迭代 4 — 改做独立质量门，不再造脚手架）：**
- 批判判断：连续 3 轮"找安全切片建造"边际价值递减 + 建错方向风险升（owner 未确认 baostock vs qlib+AKShare；未确认 G3）。改为关闭真正的质量缺口——本会话 3 commit 此前全是**自我批准**（违反 OMC 分车道）。
- **独立 opus `general-purpose` reviewer 审 `30ae69f..HEAD`**：**APPROVE，无 blocking**。验证：anti-leakage/PIT（停牌 NaN ✓ / adjustflag G3 延后 ✓ / 单 login finally-logout ✓ / oos_scores 仅 test-fold ✓）、license 完整性（uv.lock 无 backtrader/finsaber ✓ / baostock lazy-import 非硬依赖 ✓）、正确性、测试充分性、代码质量。2 条 advisory（非阻塞，未改）。
- **全局 hermetic pytest exit 0**（全绿，确认 3 commit 无回归）。
- **结论**：3 commit 现已"独立审查 + 全局验证"双门通过，不再仅自证。
- **5 项 pending owner 决策仍不变**；最高价值路径仍门控。**建议**：若 owner 近期无法回复，`CronDelete 2344a544` 暂停 loop（避免重复读状态开销 = token 浪费，owner 自己的优先级）。若回复，最阻塞 = 修订 #47 授权确认。
- **下一 loop（无回复）候选**：交易日历对齐 或 CSI300 成分 intake（仍属安全外围，边际价值递减——故本轮选择改做质量门而非继续造）。

## 2026-08-03 `/goal` 批次 — Option A′ 推进（docs/design only，未 commit）

owner `/goal` 授权推进 Option A′（多 agent 按优先级 + 模型分层省 token + reuse-first 禁造轮子）。**[1210] 现实**：opus/sonnet 子代理今天执行不稳；本批分层 = ① orchestrator 直接 opus 设计 + ② sonnet 后台 agent + ③ haiku 后台 agent。

**产出（全部 PROPOSED/docs，未触冻结面/ledger/E3）：**
- `reports/design/2026-08-03-conditional-rank-ic-multiplicity.md` — **gate 7 解决**：conditioning = 单个预指定交互项（预算 1，非 K），批判者 #4 "完全炸掉 n_trials" → PARTIAL 解决；复用 `purgedcv`/`arch`/`YannickKae`；Deflated-RankICIR（FARS 2026，DSR 适配因子级 RankIC）待 license。
- `reports/design/2026-08-03-track-c-prereg-skeleton.md` — **Track C（A 股 + 条件化 rank-IC）预注册骨架 PROPOSED v0.1**；§3 features / §5 双区域折设计 / §1 regime PIT 定义 = TBD（待 T1 + owner 冻结）；§4/§6/§7/§8/§9 复用 Track B + ADR-010。

**后台 agent（运行中，待回报）：**
- `ashare-gate-research`（sonnet）— A 股 filed-date 基本面源 7-gate 调研（cninfo / Tushare-`ann_date` / akshare）。**P0 关键路径**（gate 4，解 baostock G3 结构性失败）。
- `drankicir-check`（haiku）— Deflated-RankICIR 代码/license 核查（解 gate 7 待查）。

**未解 / 下一步：** T1 回报 → 填 Track C §3 + 定 A 股源（headline 可行 vs exploratory-only）；drankicir 回报 → 定 gate 7 主轮子；A 股**价格** PIT（§3 ①，survivorship 退市/停牌→NaN/复权）+ 中国宏观 vintage（§3 ②，NBS G3）待后续 intake 调研。regime PIT 定义（TACO 范式）待 owner 冻结。

**边界：** 本批仅 docs/design + state；未 commit；未运行 confirmatory/strategy/forward 脚本；未观察 E3；网络仅 GitHub/PyPI/WebSearch（无 baostock.com 数据调用）。

**Track C v1.0 PROPOSED（2026-08-03 续）：** owner approved §12 默认 → 起草完整 `docs/track-c-preregistration.md`（PROPOSED v1.0，12KB；§12 全填：联合折叠 / 三层 PIT regime / cninfo 源 / qlib scaffold；§3 ①②③ 全调研解决）。取代 `reports/design/2026-08-03-track-c-prereg-skeleton.md`。**未冻结**——无 `config_committed` ledger 行；feature_cols 待冻结前完整枚举（US 复用 Track B 23 + A 股 price/cninfo/ALFRED/regime 字段）。**待 owner**：审 v1.0 → 授权 `config_committed` 冻结（写 ledger 行，= owner 动作）→ impl 切片（post-freeze）。agents 7/7 `[1210]` 死，全 orchestrator 直接完成。冻结面守卫 = 空（仅新增 docs/track-c-preregistration.md，未改 phase-*/track-b/ADR/ledger/config）。

**Track C FROZEN（2026-08-03 续 2，owner 二次 approved）：** owner 确认 4 个冻结子参数（regime expanding-as-of σ TACO；DY spillover window=250/H=10/generalized FEVD；三层等权 composite；A 股 FF v1.0 排除）→ 写 `scripts/track_c_commit.py`（纯 stdlib，复用 phase_b `commit_config` 机制：`sig=sha256(json.dumps(config,sort_keys=True))`，行格式 `{ts,event:"config_committed",phase,config_sig,config}`）。**dry-run → --commit**：ledger 45→46 行，phase=track_c，`config_sig=758ca4d739f09331ee4dceb726d9d0d0f7c5110303acc6dcac59919701374fad`，**sha256 自洽已验**（重算==行内 sig），**未观察任何 OOS**（config_committed 行 only）。`docs/track-c-preregistration.md` §0/§13 更新为 FROZEN。**Track C 反泄漏 anchor 就位**；冻结后允许 S0 数据构造（不写新 ledger、不观察 rank-IC）。`runs/ledger.jsonl` 现有未提交改动（+1 行，TRACKED，按惯例提交时机 owner 定）。

## 2026-08-03 qlib 双区域 POC（Option A 可行性取证，docs/state only — 未 commit）

owner 授权的可逆证据 POC，解决 Option A 辩论（独立批判者 REJECT；辩护/裁断 agent 因 `[1210]` 5 次失败缺失）。完整报告 `reports/2026-08-03-qlib-dualregion-poc.md`。
- **5 硬证据:** ①qlib 双区域特性存在（`REG_CN/US`+`LocalPITProvider`+CSI300/500 采集器[从 csindex 历史公告重建]+pit 采集器）→**推翻批判者 #2/#8/#10**; ②cp313 门（pyqlib 0.9.7 无 cp313 wheel；3.11 隔离 venv `IMPORT_OK` 0.9.7 已验绕过）; ③RobustZScoreNorm 泄漏陷阱实证确认 + 折内钉 fit 修复有效（CLEAN train z-median 0.0000 vs LEAKY −0.3453）; ④DatasetH 手术点③需 3h 接线; ⑤**baostock G3 结构性不可合规**（`query_profit/balance_data(code,year,quarter)` 期末键、无 as-of/vintage）→**验证并强化批判者 #1**。
- **Net:** Option A′ **条件-sound**，8 门实证背书（报告 §3）。A 股基本面须换 filed-date 键源（cninfo/Tushare-`ann_date`/自建）或降 exploratory-only；baostock 不可进 headline。
- **边界:** scratch `/home/re/code/aionis-qlib-poc/`（仓库外），合成数据，未 commit/未触冻结面/ledger；网络仅 GitHub+PyPI；无 baostock.com 数据调用、无 research/forward 脚本、未观察 E3。
- **未解:** baostock 返回字段 pubDate 可重建性; A 股 filed-date 源 7-gate; DatasetH 手术点③接线; `index-constitution` 7-gate。
- **loop cron `3219e84b` 已取消**（POC scope 完成，避免与暂停冲突）。
- **独立性局限:** 批判者真独立; 辩护/裁断由 orchestrator 非独立核查替代（已做偏向校正）。proxy 恢复后可补完整三方辩论。

- **2026-08-03 `/goal` batch 8 — BASELINE-FF5-001 + BASELINE-RANK-001 EXECUTED (COMMITTED `104b21e`):**
  owner authorized real-data execution ("全部approved"). Both baselines now have REAL CV-proxy results:
  - **BASELINE-FF5-001** (sig `0b0b9934…`, 18 cols: 9 frozen + 9 FF5 exposures; `beta_dff`/`beta_dff_x_lev`
    excluded by RD-13: 42 CONSTANT months 2024-08+ — rate-plateau): **mean_IC=0.0106, ci_half=0.0196,
    t_hac=1.059, n_months=125; H6=True**.
  - **BASELINE-RANK-001** (sig `22817980…`, lambdarank/rank_bins=5, month-end-sampled panel,
    analysis_start=2015-08-01): **mean rank-IC=0.015420, ci_half=0.014870, t_hac=2.0323, p_hac=0.0421,
    n_months=125; H6=True**.
  Both EXPLORATORY CV-proxy only; config_committed ledger rows appended BEFORE results (2 RES-02 + 2 RES-03 rows).
  **Fixes surfaced by real runs**: (1) RES-02 SIG_ONLY mode (exit before OOS) + analysis window
  2015-08-01 (DFF vintages begin 2015-01-01; owner decision option A) + month_ends pre-window;
  (2) features/ff5.py beta_dff NaN no longer contaminates FF5 5-factor betas (independent OLS masks);
  (3) RES-03 month-end sampling (RD-15 group=query-month ~500 rows, not ~11,300 — LightGBM 10k/group cap)
  + folds on month-end panel via two_arm._folds_from_panel + config-driven analysis_start;
  (4) RES-03 _require_owner_commit ledger gate. Full suite exit 0; ruff clean.
  **Data acquisitions**: FF5 daily snapshot frozen (`ccf509fb…`, 15833 rows) + DFF ALFRED vintages
  293,510 rows (2015→2026, sharded yearly — FRED 2000-vintage cap workaround).
  **NOT yet done**: evals/trials registry entries for both trials; RES-08/RES-10 (owner gold-set annotation).
- **2026-08-03 `/goal` batch 7 — E3 Slice 7 E2E + AUD-06 contract freeze (COMMITTED `0f94620`):**
  closed the final E3 code gap. `tests/test_forward_e2e.py` (NEW, 290 lines, 2 tests) wires the full
  hermetic chain on labeled synthetic fixtures in tmp_path: COMMIT (Slice 3d, long-scores both arms,
  sha256 seal) → **I1** gate (reveal before target_t refused, no scored rows) → REVEAL+SCORE (Slice 4b,
  both arms ic_point float) → **I2** (idempotent re-reveal appends nothing + immutable sealed-scores
  sha256, byte-mutation flips hash) → ACCUMULATE (Slice 4c, n_months=1, summary key set,
  dm_flag=degenerate) → **I9** (forward chain writes ONLY runs/forward/ + ledger.jsonl, never
  runs/results/). I3–I8 explicitly NOT duplicated (owned by existing invariant suites).
  `config/e3_live_contracts.yaml`: `max_age_sessions` 23 → **22** + `authoritative_refresh: null`
  explicit + PROPOSED → **FROZEN (D2, 2026-08-03)**; cron stays DISABLED, headline still needs owner GO.
  `tests/test_e3_forward_trigger.py`: 7× 23 → 22 + proposed-marker test renamed frozen-marker.
  **Verified: 7 forward suites 84 passed; full hermetic suite exit 0; ruff clean; real-ledger guard
  PASS; git diff --name-only = the 3 files; pre-existing Track-B WIP untouched.** Slice 7 code complete;
  only E3 headline (AUD-06 done + owner GO) and RES-08/RES-10 (owner-gated) remain.
- **2026-08-03 `/goal` batch 6 — RES-02 + RES-03 EXECUTED via 2 worktree-isolated agents (COMMITTED
  + pushed, `825658b`):** owner authorized execution ("授权你继续执行"). **2 sonnet agents in isolated
  git worktrees** (the correct "各自推进/不影响各自进程" mechanism — no writer race, no Track-B WIP
  conflict), each delivered INLINE this time. Merged into main; both exploratory baselines PREPARED but
  NOT registered (runners refuse to run until the owner's `config_committed` ledger row exists):
  - **RES-02 (BASELINE-FF5-001)**: ff5.py ingest (bulk-ZIP, sha256 snapshot, ≥2s politeness) + macro_dff.py
    (ALFRED vintage, strictly-before as-of) + features/ff5.py (stock-specific rolling exposures +
    interactions, RD-13 gate) + runner (aborts without owner ledger row) + config (20 cols) + 41 tests.
  - **RES-03 (BASELINE-RANK-001)**: learner.py rank-aware branch enforcing frozen RD-15 enum
    (validate_objective("lambdarank"); "regression" branch untouched) + runner (frozen chain
    construct_month_groups→…→fit_predict_rank) + config + 15 tests. `ranking_contract.py` 0-diff.
  - **Full hermetic suite: 1408 passed / 0 failed** (+56 new tests); ruff clean; ledger 0 diff; no
    frozen surface touched; no real data run. docs: data-intake-french-ff5.md (7-gate, owner 签注
    PENDING) + baseline-ladder{,-ff5,-rank}.md (index + per-baseline, conflict-merged).
  - **Both baselines now await: owner authorization + `config_committed` ledger row before any OOS
    metric.**
- **2026-08-03 `/goal` batch 5 — RES specs rewritten via 4 parallel agents (COMMITTED + pushed, `2f87970`):**
  executed approved D5 (RES restart) the RIGHT way this time: **4 sonnet agents dispatched in 2 batches of
  2 (≤2 concurrent proxy cap), file-isolated (each writes only its own task file — parallel without the
  writer race), verified each touched ONLY its target**. Each rewrite fixes its root defect:
  - RES-02: raw market-wide FF5/DFF columns (zero cross-sectional variation → unrankable) → stock-specific
    rolling beta-to-factor + loading×characteristic interactions; PIT proof + RD-13 guard + French 7-gate
  - RES-03: defined the rank-label/query contract anchored to FROZEN RD-15 + ranking_contract.py; removed
    invalid objective names; forbidden to modify frozen impl
  - RES-08: monolithic → durable 5-stage schema/sample/annotation/adjudication/freeze (ADR-006), REUSING
    the existing docs/llm-extractor-eval.md + src/aionis/schema/gold_annotation.py schema (not reinventing)
  - RES-10: every metric anchored to RD-04/06/07/08/11 + RES-08 gold set (no re-spec from scratch)
  All 4 agents went idle without reports (idle-without-result pattern) but their work landed in the tree —
  verified from repo state, NOT prose (§8 recovery path). 8 files (+679/-340); ledger 0 diff; no
  src/frozen-surface change. All 4 specs now "REWRITTEN 2026-08-03 — ready for owner authorization".
- **2026-08-03 `/goal` batch 4 — approved owner decisions executed (COMMITTED + pushed, `c09bd0b`):**
  owner approved all recommendations (D1-D8). Evidence in `reports/design/2026-08-03-owner-decision-execution.md`.
  D1: Track B config VERIFIED already frozen 2026-08-02 (ledger #41/#42) — no new row. D2: AUD-06 contracts
  FROZEN (`max_age_sessions=22`, `authoritative_refresh=None` — factual, no standalone universe script;
  `block_on_unknown=True`) → **E3 Slice 6/7 may proceed to implementation** (headline still gated by owner GO).
  D3: C5 Option A — politeness split in CLAUDE.md L49 (data-fetch ≥2s; model APIs RPM/TPM+cooldown+cache);
  C5 → OWNER-APPROVED. D4: FF 7-gate recorded. D5: RES restart approved (4 specs need rewrite first). D6: RD
  safe queue exhausted. D7: KAIROS verified (MIT, 0-star demo-grade — cite valid). D8: FinLake-Bench CONFIRMED
  NOT RELEASED (name inconsistency FinLake/FinLeak); audit §5 corrected. Docs/state only; no frozen
  surface/ledger/data touched; verification agents used WebFetch only.
- **2026-08-03 `/goal` batch 3 — citation-integrity audit (COMMITTED + pushed, `20191fd`):** directly
  answered the hook's (a)/(c)/(d) requirements. **4 parallel verification agents, tiered by difficulty**
  (haiku ×2: 1-entry E3 + 3 inline IDs; sonnet ×2: 5 frontier + 4 E2 entries) audited ALL arXiv
  citations across frontier_positioning.md / phase-e2 / phase-e3 / theory-of-computable-reality.
  **Result: 11/11 real, none fabricated.** Precision fixes applied to frontier_positioning.md:
  L62-65 overstatement (`2504.14765` = recall-level memorization; "functional lookahead bias" term +
  `market_impact` detail NOT in abstract — possible sister-paper conflation), L49 anchored to real
  title, L35-36 bare IDs → full URLs. **External-reuse verdict (7-gate)**: purgedcv (MIT, installed/
  pinned/importable) = only compliant wheel; lookaheadbench + CAMEF no LICENSE → non-reusable;
  Alpha Illusion code link dead (404); 2504.14765 CC BY-NC-ND → citation-only; CausalStock no repo;
  **FINSABER = Apache-2.0 → passes allowlist (the wheel Track B is mounting — independent license
  evidence)**. Profit Mirage's "51-62% Sharpe decay" verified verbatim. Full ledger:
  `reports/design/2026-08-03-citation-integrity-audit.md`. Docs-only, no code/frozen-surface change.
- **2026-08-03 `/goal` batch 2 — Slice-2 backlog fully closed (COMMITTED + pushed):** completed the
  remaining Slice-2 items. (1) **`5ffdbe1`** — first-run `last_poll_ts=None` seeding docstring notes in
  all 3 forward collectors (13D/macro/8-K; docstring-only). (2) **`758d87e`** — structlog warning when
  `persist_snapshot` writes the REAL ledger (`runs_dir=None`): the shared persist tail covers all 3
  collectors at once; the backlog's `forward_only=True` wording was stale (row-level constant, not a
  param). Not unit-tested by design (exercising the branch would write the real ledger, which
  `test_real_ledger_jsonl_untouched` pins as forbidden). **Full hermetic suite: 1352 passed / 0 failed**
  (final verification); ruff clean; forward-ingest 16/16. Both pushed. Track-B WIP untouched; no frozen
  surface / ledger / data touched; no real network/LLM/trial.
- **2026-08-03 `/goal` reuse-first batch (COMMITTED + pushed, `f6e0536` + `e6c71ec`):** resumed the
  priority offline program under the owner `/goal` (更多 agents 按优先等级推进; 难度分级模型; 复用轮子禁止重造).
  Proxy is `[1210]`-flaky → direct-write (opus) chosen over dispatch for coherence + token-efficiency.
  (1) **`f6e0536`** — Slice-2 "S cleanup": DRY'd the identical archive→cumulative→ledger tail of the 3
  forward collectors (13D/macro/8-K) into `_common.persist_snapshot(...)` (n_rows appended LAST to keep
  per-collector ledger key order → byte-identical output, H6). Also dropped the redundant `keyfn=str.upper`
  dead branch in earnings_8k. (2) **`e6c71ec`** — full-suite was RED (12 `test_static_site.py` failures,
  pre-existing on clean HEAD): tests were stale vs the committed Track B page (English/base64/tabs). Aligned
  them (Chinese Track B assertions: 探索性/非投资建议/null-预期可发表, SESOI 0.010, 诚实边界, 七主题, 差分
  #41/#42, FF5/mounts, data-driven plotly, no runtime fetch, H6 determinism) AND added `--out-dir` so tests
  build to tmp_path — **hermetic, never touches the `site/` WIP** (Track B's uncommitted `M site/index.html`
  + `D` 2 JSON files stay untouched). **Full hermetic suite now 1352 passed / 0 failed; ruff clean.** Both
  pushed. 状态: state/current.md updated.
- **2026-08-03 ORCH-02 second wave (REJECTED — no code change):** attempted to mirror the
  cumulative-preserve test for 8-K, but the premise was a **grep-suffix miss**: 8-K already has the
  invariant via `test_8k_forward_idempotent_and_cumulative_preserve` (`tests/test_forward_ingest.py:504`).
  A `[1210]`-failed executor had nonetheless written a complete (redundant) test into the working tree
  before its API error; detected via `git diff`, discarded via `git restore` (redundant duplication,
  contra 治理复杂度 ≤ 产出). **Three binding findings**: (1) `[1210]` hit 2 consecutive sonnet spawns
  (`oh-my-claudecode:executor` + `general-purpose`) — today's proxy is flakier than the handoff's
  "transient, single retry works" note, and `general-purpose` did NOT bypass it this time; (2) a
  "failed" subagent can mutate the tree before its API error — always `git status`/`git diff` after a
  failed spawn (folded into `docs/orchestration-protocol.md §8`); (3) gap-analysis must grep the
  CONCEPT (`grep -iE "cumulative.*preserve"`), not a name suffix — the suffix grep manufactured a
  false gap. Task recorded as REJECTED in `tasks/rejected/TASK-ORCH-02-*.md`. Subagent dispatch is
  currently unreliable in this proxy — for the next wave, prefer direct-write (opus) for S test
  mirrors unless the proxy recovers.
- **2026-08-03 ORCH-01 first wave (COMMITTED `8d19b28`):** validated the ADR-012 dispatch protocol
  end-to-end. Picked the backlog "macro cumulative-preserve test" (S, hermetic). Ran
  `scripts/orchestrate_dispatch.py --lane executor` → clean 6-layer contract (exit 0). Dispatched sonnet
  `executor` (orch01-executor) → implemented `test_macro_forward_cumulative_parquet_preserves_prior_rows`
  (tests/test_forward_ingest.py:373, +75 lines; faithful 13D mirror — cumulative==24, snapshot_ts=={t1,t2},
  T1+T2 pub-dates ⊂ cum). Orchestrator independent verify: pytest 16/16 green, ruff clean.
  **Reviewer-lane operability gap (binding finding)**: the dispatched `code-reviewer` (sonnet) went idle
  WITHOUT returning a verdict (×2); per WORKFLOW §17 (2-identical-failures stop) the Orchestrator
  proceeded on independent deterministic verification + line-by-line diff review, deviation explicitly
  disclosed in the commit. **Harness behavior**: sync subagents return via `idle_notification`, not inline
  — reclaim L6 via SendMessage; for code lanes, recover from repo state (git diff + pytest + ruff), never
  trust worker prose. Folded into `docs/orchestration-protocol.md §8`.
- **2026-08-03 orchestration protocol (COMMITTED `daa92e8`):** owner directive — "主agent编排+验收,
  高等级模型监工(低频), 分配任务给其他模型, review+e2e会话, 跨会话降噪, issue编排任务" — implemented by
  **binding existing OMC primitives**, not building a new framework (reuse-first). Owner chose **local task
  files = issues** (zero GitHub surface; minimizes the 治理复杂度>产出 drift). New additive artifacts:
  `decisions/ADR-012-orchestration-protocol.md` (ACCEPTED) + `docs/orchestration-protocol.md` (operational
  spec) + `scripts/orchestrate_dispatch.py` (6-layer contract emitter, reuses RD-01 `lint_task_file`) +
  `tests/test_orchestrate_dispatch.py` (11/11 green, ruff clean) + `tasks/templates/DISPATCH-CONTRACT.md`.
  Registered ADR-011 + ADR-012 in `decisions/index.md`; added CLAUDE.md see-also pointer. Lane model: opus
  Orchestrator + **low-freq opus Supervisor (监工, gates only)** + sonnet `executor`/haiku workers
  (serialized, ≤2 concurrent — parallel-writer race + `[1210]` cap) + independent `verifier`(验收) /
  `code-reviewer` / `qa-tester`(e2e) lanes. Denoising = 6-layer dispatch contract (WORKFLOW §10) + structured
  handoff (workers return files/tests/evidence/next-action, never narrative; no full-chat forwarding).
  Anti-leakage guardrails binding on every dispatch (no real network/LLM/forward; frozen surfaces read-only;
  config_committed-before-result; ledger 0-diff). **Additive only** — no frozen surface / ledger / data /
  Track-B code touched; no real network/LLM/trial ran. Next: owner commissions the first wave (pick a task →
  run the helper → dispatch to `executor`).

- **2026-08-02 strategic review:** "是否跑偏 + 七主题低成本覆盖" deep-dive → `reports/2026-08-02-strategic-review-coverage-and-alignment.md` + 6 `reports/design/` artifacts (Track A/B slice plans, slice review, qlib POC, wheel-mount pack, reuse-catalog v2) + `src/aionis/eval/ff5_residual.py` (挂接③, 18 tests green, ruff clean; exploratory, not wired to pipeline/ledger). Verdict: direction sound; two失调. **Owner decision (2026-08-02):** Track B adopted + new prereg (`decisions/ADR-011-track-b-seven-theme-platform.md` + `docs/track-b-preregistration.md` PROPOSED); 挂接③ first slice done. **Pending:** owner freezes config sha256 before real-data. 未触冻结面/ledger/E3；无真实 network/LLM/trial.
- **round:** Wave-A execution. AUD-05B is closed after authorized re-Review. Dashboard extraction
  and C4 Option A cleanup are committed in `7dede9b`. C1 BLS disable, C2 VIX FRED adapter and C3
  PRAW requestor wrapper are COMPLETE after Engineer evidence, independent Verifier PASS and
  independent Reviewer APPROVE, and are ready for the Group A commit. 2026-08-01.
- **outcome:** project remains an evidence-first PIT research harness, not a validated stock-picking strategy.
  Historical B/C/D/E1 are shared-fold purged CV-proxies (not chronological OOS); LLM not in headlines;
  E3 NO-GO for headline.
- **COMPLETE:** AUD-01/02/03/04/05A/05B (each Verifier PASS + Reviewer APPROVE); AUD-05C disposition
  (Reviewer APPROVE; 10 boundaries → C1-C5 + Kenneth-French task files); **AUD-07 FROZEN** via
  [ADR-010](../decisions/ADR-010-sesoi-tost-sequential-gate.md) + E3 pre-reg §7 (SESOI ±0.010 / HAC-TOST
  90% / O'Brien-Fleming 60·90·120mo / n_trials=30; 3× cross-validated; equivalence+sequential
  construction amended).
- **STATISTICAL HOLD:** AUD-07B reopens the implementation-level proof only: ADR-010's amendment says
  TOST p-values “exceed alpha”, which appears reversed, and the sequential equivalence construction
  requires strong independent review. Do not implement or expose E3 inferential verdicts meanwhile.
- **C-series prepped → owner-decidable:**
  - **C3 (PRAW 7-gate)**: OWNER APPROVED WITH CONDITIONS (all 7 gates PASS; G1 BSD-2/Apache-2.0, G2 PIT,
    G3 snapshot handles user-edits, G4 sha256+append, G5/G6 exploratory-only, G7 PRAW 1.5s+ToS).
    Conditions: Reddit ToS internal-only/no-redistribute; permanent `mode:exploratory`. Engineer,
    Verifier and Reviewer are complete; no live pull is authorized.
  - **C1 (BLS disable)**: owner-authorized disable-only implementation is complete. CPI/NFP cache
    misses fail closed before HTTP; FOMC/cache behavior is preserved. Independent Verifier PASS and
    Reviewer APPROVE are recorded; Group A commit is next.
  - **C2 (VIX/FRED)**: owner-authorized implementation replaces SDK fetches with the shared-policy
    FRED observations adapter while retaining ADR-003 PIT/cache/ledger behavior. Independent
    Verifier PASS and Reviewer APPROVE are recorded.
  - **C4 (health_check)**: standalone Option A is owner-authorized and complete in `7dede9b`.
    The blocked data/wheel probes and stale text are removed; seven hermetic tests, lint, scan and
    review pass.
  - **C5 (model-API ≥2s)**: **Option A (SDK-exempt)** recommended — model APIs throttled by provider
    RPM/TPM + ProviderRouter cooldown + idempotent cache; ≥2s redundant for GLM (RPM 30), harmful for
    SiliconFlow (RPM 1000). Rule wording drafted. → owner accept.
- **P2 legacy split → partially replan-required**: 10 prior `TASK-RES-01..10` files exist (baseline-ladder
  RES-01/02/03 [mom/FF5/rank-objective]; economic-lens RES-04/05/06/07 [next-open/turnover-slippage/
  liquidity-borrow/delisting-capacity]; LLM-eval RES-08/09/10 [gold-set/zero-LLM-ablation/eval-metrics]).
  RES-02/03/08/10 are now HOLD/REPLAN because of cross-sectional-variation, rank-label,
  durable-gold and remote-determinism defects. Do not authorize those files as written; use RD tasks first.
- **owner-decision queue (consolidated — further progress needs these):**
  - **C5**: accept Option A + record the rule wording?
  - **Kenneth-French / selection-panel FRED+Fama-French**: data-intake 7-gate decision.
  - **AUD-06**: owner contract (E3 live-input readiness acceptance points).
  - **RES program**: no legacy RES task should start before RD-17 and its listed prerequisites; RES-02/03/08/10
    specifically require rewritten specs.
  - **RD program**: launch only P0 closure, P0 + the offline RD-01..17 program, or selected RD tasks?
  - **Commit?** audit remediation is committed as `e8545d4` and dashboard/C4 remediation as
    `7dede9b` (both on remote `main`). C1/C2 await independent review before their own commit.
- **verification:** the full hermetic pytest suite currently passes (existing forward-score warnings
  only), `uv run --offline ruff check` and `git diff --check` pass, and frozen
  prereg/ADR/config/ledger/results/data/forward remain untouched. Group A C1/C2/C3 each have
  independent Verifier PASS and Reviewer APPROVE. `runs/ledger.jsonl` remains unchanged; no E3
  outcome was observed and no confirmatory/strategy/horizon/forward/real-network/LLM script ran.
- **planning artifact:** `reports/milestone/2026-08-01-low-reasoning-development-roadmap.md` and
  the Wave-A launch brief and `TASK-RD-00..17` split the next safe work into a 10.75–16 hour first
  offline wave and a 25.5–40 hour complete Engineer package. `TASK-AUD-07B` is strong-only. This is a
  frozen task proposal. The final unattended prompt selects C1/C2/C3 + RD-04/05/06/07/09/10/12,
  has explicit context-compaction/token rules, and received independent Reviewer APPROVE. It becomes
  implementation GO only when the owner pastes it into the new Goal session.
- **proxy note:** 3-parallel subagent spawns fail with proxy 400 `[1210]`; ≤2-parallel / single work.
  Future dispatch ≤2 concurrent.
- **do NOT:** run confirmatory/strategy/horizon/forward scripts; edit frozen prereg/ADR/config; infer
  B's paired differential CI; call historical cross-fit chronological OOS; inspect E3 outcome metrics;
  ignite E3 headline.
- **git:** branch `feat/e3-forward-ledger`; remote `main` includes `7dede9b`. Current uncommitted
  code includes approved C1/C2/C3 implementation/tests plus planning/state/task documentation; the
  Group A commit will use explicit file lists only.

## Overnight checkpoint (Wave-A)

- Goal: execute Wave-A C1/C2/C3 + RD-04/05/06/07/09/10/12 with independent gates and safe push. **COMPLETE.**
- All gates passed: C1/C2/C3 + RD-04/05/06/07/09/10/12 each have independent Verifier PASS + Reviewer APPROVE.
  Fixes applied and re-gated: RD-07 (generated_at caller-provided for byte-stability), RD-10 (vol_adj_mom
  last-12 window + std<=0), RD-12 (additive constituents_manifest_on + 3 unskipped manifest oracles;
  constituents_on behavior unchanged).
- Commits: `6085e92` Group A, `2653907` Group B, `5f884a3` Group C. Final docs/state bundle (this commit).
- Final gates: full hermetic pytest green (zero skips; only pre-existing forward_score warnings);
  `uv run --offline ruff check` clean; `git diff --check` clean; frozen/ledger/results/data/forward diff
  empty; no data/.env/*.parquet staged; no real network/LLM/research/forward script ran; E3 outcome unobserved.
- Files: RD-01/02/03/08/11/13..17 task specs remain PLANNED (future waves) — committed as planning docs.
- Blockers: none. Next: optional fast-forward push HEAD:main (origin/main is ancestor of HEAD).

## Wave-B checkpoint (2026-08-01, in progress)

- **Launch authorization:** owner `/goal` — "启用更多 agents 根据优先等级在不影响各自进程的前提下各自推进".
  Treated as owner authorization for the priority (P0→P1) offline RD program (the safe sonnet-tier set).
  Per-task authorization is recorded in each task file's 状态 line by the Orchestrator as the audit trail.
- **COMPLETE so far** (each: Engineer → independent Verifier PASS → independent Reviewer APPROVE → atomic
  commit; offline/hermetic; `runs/ledger.jsonl` untouched; no frozen surface touched):
  - RD-02 validation manifest — `97e5688`
  - RD-01 task-contract linter — `feb80ba` (first attempt lost to the parallel-writer race below; redone serially)
  - RD-13 cross-sectional variation guard — `2f0efd0`
- **KEY OPERATIONAL FINDING (binding):** spawning ≥2 writer subagents concurrently in the SHARED working tree
  loses one agent's untracked deliverables (RD-01 first attempt: `.pyc` survived in gitignored `__pycache__`,
  `.py` + README diff gone — consistent with a `git clean -fd`/`restore` across parallel-agent boundaries).
  **Writers are now SERIALIZED: exactly ONE Engineer subagent per message.** Parallel is reserved for read-only
  preflights only. See memory `aionis-parallel-writer-race`.
- **Model routing (binding):** only `sonnet`/`haiku` subagent aliases resolve to subagent-safe IDs; `opus`/`fable`
  resolve to `[1M]`-suffixed IDs and are DENIED by the enforcer. The RD program is sonnet-tier so this is fine.
  `TASK-AUD-07B` (strong-only, STATISTICAL HOLD) and `RD-15` (strong precondition) are DEFERRED until opus
  routing is fixed (drop `[1M]` suffix from `ANTHROPIC_DEFAULT_OPUS_MODEL`).
- **Authorization bookkeeping:** the first RD-02 Reviewer returned BLOCKED solely because the task file still said
  "PLANNED — not implementation-authorized"; resolved by recording the /goal authorization in the task 状态 line.
  All subsequently launched RD tasks are pre-authorized in their task files before dispatch.
- **Remaining safe queue (P1, sonnet-tier):** RD-17 (trial-intent registry) → RD-16 (eval uncertainty) → RD-11
  (provider replay) → RD-03 (chronological oracle, unlocked by RD-02 APPROVE) → RD-14 (reproducibility capsule,
  unlocked by RD-02 APPROVE). RD-08 remains HOLD (needs a strong-Researcher-frozen rule table first). RD-15 deferred (strong).
- **Verification status:** per-task pytest + ruff green; ledger empty diff across all Wave-B commits; no frozen
  prereg/ADR/config/result/data/forward surface touched; no real network/LLM/trial ran. The full hermetic suite
  has NOT been re-run this wave yet (defer to a pre-push gate).
- **Git:** branch `feat/e3-forward-ledger` ahead of origin by 8 (Wave-A + Wave-B). Not pushed (owner's call).
- **Do NOT:** run confirmatory/strategy/horizon/forward scripts; edit frozen prereg/ADR/config; observe E3
  outcome; spawn >1 writer subagent per message.

## Wave-B FINAL (2026-08-01, COMPLETE)

All 8 safe sonnet-tier RD tasks implemented, each with independent Verifier PASS + Reviewer APPROVE and an
atomic commit; offline/hermetic throughout:
- RD-02 validation manifest — `97e5688`
- RD-01 task-contract linter — `feb80ba` (first attempt lost to the parallel-writer race; redone serially)
- RD-13 cross-sectional variation guard — `2f0efd0`
- RD-17 trial-intent registry (HIGH-risk; ledger-bypass cleared) — `5dfe849`
- RD-16 eval uncertainty (Wilson≠Wald; seed=0 stratified bootstrap) — `ee223ae`
- RD-11 provider replay (salvaged a cut-off partial; audited + completed; providers/llm_client 0 diff) — `8a46179`
- RD-03 chronological oracle (HIGH-risk; cv.py 0 diff; lookahead rejected; real purgedcv) — `af7d673`
- RD-14 reproducibility capsule (outcome-free; deterministic capsule_id; atomic write + refuse-overwrite) — `f397383`

Final pre-push verification: full hermetic pytest GREEN (zero failures/skips; only the pre-existing
forward-score UserWarnings documented in Wave-A); `uv run --offline ruff check` clean; `runs/ledger.jsonl`
0 diff across the whole wave; frozen-surface audit (docs/phase-*, decisions/, runs/ledger, config/, data/,
*.parquet, pyproject.toml, uv.lock) — NONE touched; no real network/LLM/trial/forward script ran; E3 outcome
unobserved.

Process notes (binding for future waves):
- Writers are SERIALIZED (exactly one Engineer subagent per message) — parallel writers in the shared tree
  lost untracked deliverables (see memory aionis-parallel-writer-race).
- Only `sonnet`/`haiku` subagent aliases are dispatchable; `opus`/`fable` resolve to `[1M]` IDs and are
  denied by the enforcer → `TASK-AUD-07B` (strong-only) + `RD-15` (strong precondition) are DEFERRED until
  opus routing is fixed.
- The `[1210]` proxy "API parameter" error is transient on Reviewer spawns — a single retry has succeeded
  every time; it is NOT the 5-hour usage cap.
- Owner authorization for the priority RD program was the `/goal` directive; recorded per-task in each task
  file's 状态 line. (The first RD-02 Reviewer BLOCKed on the stale "PLANNED — not implementation-authorized"
  status, which is why all later tasks were pre-authorized in their task files before dispatch.)
- Per the owner: do not spend tokens checking whether the 5-hour usage cap has reset — if the session is
  running, it is reset (see memory aionis-no-rate-limit-check).

Remaining (NOT started — legitimately blocked, not merely unauthorized):
- RD-08 HOLD — needs a strong-Researcher-frozen zero-LLM rule table before low-reasoning implementation.
- RD-15 DEFERRED — rank-objective contract is a strong-model decision precondition (lambdarank vs rank_xendcg,
  monthly relevance binning, ties, missing, group=query-month); also needs opus routing.
- AUD-07B — STATISTICAL HOLD on ADR-010 TOST p-value direction / sequential-equivalence construction; strong-only.
- RES-02/03/08/10 — HOLD/replan per roadmap; their foundations (RD-13 done; RD-15/RD-08 still pending) must
  precede them.

Git: branch `feat/e3-forward-ledger` ahead of origin by 13 (Wave-A + Wave-B). Not pushed — owner's call.
Safe RD queue now exhausted for the sonnet tier.

## Track B 首个 OOS 观察（2026-08-02）

**treatment 臂（config #41）**: mean_ic 0.0055, 95% HAC CI (-0.021, 0.033), p=0.689（null）。**price-only 臂（#42）**: mean_ic -0.0021, CI (-0.032, 0.028), p=0.891（null）。**差分（#41 − #42, §1 headline）**: mean_diff 0.0076, CI (-0.004, 0.020) 跨零, p=0.219 → treatment 未显著优于 price-only（null，符合 null-favored）；CI 上界 0.020 > SESOI 0.010 → 不构成严格等价（需更多样本）。见 docs/track-b-results.md。

## AUD-07B — statistical review COMPLETE (2026-08-01, CRITICAL finding)

AUD-07B (P0 / CRITICAL) is now reviewed by TWO opus agents (a strong-statistician audit + an INDEPENDENT
opus Reviewer, APPROVE). Both confirm ADR-010's equivalence/sequential gate has TWO CRITICAL defects:
1. **TOST rejection direction is REVERSED.** ADR-010 Line 42 requires the two one-sided p-values to
   "exceed alpha" (p > α); the correct Schuirmann (1987) rule is: declare equivalence iff p1 < α AND p2 < α.
   As written, the gate would declare NON-equivalence, not equivalence.
2. **Sequential CI duality is BROKEN.** ADR-010 pairs a fixed 90% CI with look-specific O'Brien-Fleming αk,
   which breaks the TOST⇔CI duality at looks 2–3 and inflates first-look Type I error ~9.6× (0.05 vs
   ~0.0052). Correct construction: look-specific (1−2αk) CIs (98.96% / 96.84% / 91.26%), or a recognized
   group-sequential equivalence construction (Jennison–Turnbull 2000).
CI duality at α=0.05 (90% CI), the union–intersection composite null, and HAC (Newey-West) SE all PASS.
Report: `reports/audits/e3-tost-sequential-correction-review.md`.

CONSEQUENCE (binding): the E3 inferential-verdict and headline remain HOLD. Implementing or exposing any E3
equivalence verdict before the owner authorizes an ADR-010 + prereg §7 amendment (p < αk; look-specific CI)
is FORBIDDEN. This is an owner decision — ADR-010 and the prereg are frozen; the audit does NOT modify them.
Open non-blocking note: ADR-010's αk source (0.0052 / 0.0158 / 0.0437) is undocumented and did not match the
reviewer's independent Lan-DeMets OBF recomputation — owner should confirm the αk provenance as part of the
amendment.

## Model-differentiation policy (2026-08-01, per owner /goal)

opus subagent routing was fixed (`ANTHROPIC_DEFAULT_OPUS_MODEL` now `claude-opus-4-8`, no `[1M]` suffix).
Difficulty-based dispatch is now in effect to save tokens:
- **opus** — only genuinely hard analysis/decisions (AUD-07B statistician + reviewer done; RD-15 rank-objective
  contract and the RD-08 zero-LLM rule-table draft are the next opus candidates).
- **sonnet** — standard code/review (Wave-B RD tasks).
- **haiku** — mechanical verification, simple doc/grep checks.
Writers remain SERIALIZED (one Engineer per message; parallel-writer rule still binds).

## RD-15 — rank-objective DECISION PACKET proposed (2026-08-01, pending owner freeze)

RD-15 (P2 / HIGH-risk) decision precondition is now drafted by an opus Architect at
`reports/design/2026-08-01-rd15-rank-objective-contract.md` (PROPOSED — pending owner freeze). 7 of 8
choices are determined by theory; ONE is an owner-preference question:
- **Open owner question:** bin count for monthly relevance — **quintiles (5, robust, default)** vs
  **deciles (10, aggressive)**. Ranking theory does not uniquely determine this for the rank-IC estimand.
Theory-fixed choices: objective = **lambdarank** (rank_xendcg rejected; allowed-enum fixed so non-existent
objectives are rejected); per-month quantile binning fit ONLY on the train fold; group = query-month; ties
share the relevance integer; NaN returns excluded (NaN features → LightGBM default); test out-of-range
returns clamped to nearest train-fold edge + reason code (never refit). Four testable leakage invariants
specified (month-permutation, future-truncation, train-fold-only fit, group-size stability).

After owner freeze, a sonnet Engineer implements `src/aionis/eval/ranking_contract.py` + tests mechanically
(no self-selection). No code/learner/frozen surface changed by the decision packet.

### Update (2026-08-01, continued — model-differentiated dispatch)
- **RD-15 implementation COMPLETE** — `ea335c8` (sonnet Engineer + independent Verifier PASS + Reviewer
  APPROVE; 0 blocking). `src/aionis/eval/ranking_contract.py` implements the decision packet (objective enum
  lambdarank/rank_xendcg; per-month train-fold-only binning; out-of-range clamp+reason; group=query-month; 4
  leakage invariants). `bin_count` is a parameter (default 5/quintiles, supports 10/deciles) — the methodology
  freeze of the actual value remains the owner's (via config), not hard-coded. learner.py untouched (0 diff);
  31 module tests + full suite (1348) green.
- **RD-08 rule table PROPOSED** — `evals/expected/zero_llm_rules_v1.yaml` (opus strong-Researcher), pending
  owner freeze. 10 conservative abstain-heavy rules (FOMC×3, CPI×2, NFP×2, 13D×3); default/conflict=abstain;
  8k_2_02 deferred. Two owner decisions flagged: 13D actor_type (COLLECTIVE vs ORGANIZATION) and whether to
  include 8k_2_02. After freeze, a sonnet Engineer implements `src/aionis/extraction/zero_llm_baseline.py`
  verbatim from the table.
- **Tier usage this session:** opus for AUD-07B (statistician + independent reviewer) and RD-15 decision +
  RD-08 rule-table draft (genuinely hard analysis/domain-modeling); sonnet for all Wave-B code + RD-15 impl +
  verifications/reviews (standard). haiku unused — no remaining priority task is mechanical-tier (forcing it
  would be false economy). Reviewer `[1210]` proxy errors were bypassed by switching `oh-my-claudecode:code-
  reviewer` → `general-purpose` (same sonnet tier) when they recurred.

## Owner decisions + independent opus reviews (2026-08-01)

Owner decisions: ADR-010 → Jennison-Turnbull construction (B); RD-15 bin_count → quintiles/5 (A); RD-08 → freeze
(A) + COLLECTIVE + defer 8k_2_02; RES → hold (A); commission independent opus review of RD-08 + RD-15 (5B);
housekeeping done (local main FF to origin/main; remote feat/e3-forward-ledger deleted). All Wave-B/AUD-07B/
RD-15/RD-08 work pushed to origin/main (HEAD e58b16e).

Independent opus review outcomes:
- **RD-15 decision packet: APPROVE** (0 CRITICAL/MAJOR; leakage guards sufficient, implementation faithful).
  Owner froze bin_count=5.
- **RD-08 rule table: REQUEST CHANGES → FIXED → FROZEN.** Review found 4 CRITICAL (enum NAME vs lowercase VALUE;
  FOMC forward-guidance false positives; 13D→13d; negation-window unit undefined) + 2 MAJOR (CPI/NFP secondary
  patterns; rule-count comment). An opus fixer resolved all: lowercase enum values; added fomc_guidance_abstain_001
  (precedence 110, abstain-only); 13d; negation = whitespace words; tightened CPI/NFP; accurate count (now 11).
  event_type semantics confirmed: FOMC/CPI/NFP are valid (`src/aionis/config.py` ECONOMIC_EVENT_TYPES); the gold
  `Literal["13d","8k_2_02"]` is filing-specific. Table FROZEN.

Still queued (owner-authorized, not yet done this session): RD-08 sonnet implementation of `zero_llm_baseline.py`;
ADR-010 Jennison-Turnbull amendment (opus design + independent opus review + apply to frozen ADR-010/prereg §7).

## ADR-010 Amendment APPLIED (2026-08-01) — Jennison-Turnbull; RD-08 implemented

- **RD-08 zero-LLM baseline COMPLETE** — `src/aionis/extraction/zero_llm_baseline.py` (sonnet Engineer + haiku
  lint-fix + independent Verifier functional PASS + independent Reviewer APPROVE). Mechanically applies the
  FROZEN rule table (11 rules; lowercase enum values; sha256 provenance; 6 abstain paths; fomc_guidance_abstain_001
  precedence-110 suppresses forward-guidance false positives). Structural-only (no sentiment/market_impact);
  providers/llm_client/frozen table untouched. Committed + pushed.
- **ADR-010 Amendment 2026-08-01 APPLIED** (owner Decision 1 = option B). The broken "Cross-validation amendment
  (2026-07-31)" is VOID; replaced by a Jennison-Turnbull (2000) group-sequential equivalence construction
  (OBF zₖ = z_α/√Iₖ → look-specific RCI levels 99.44 / 97.64 / 95.00%; equivalence iff RCIₖ ⊂ [−SESOI, +SESOI],
  which structurally prevents the reversed-direction error; Type I ≤ 0.05). Prereg §7 amended in lockstep.
  Ratified sub-choices: standard OBF (over Lan-DeMets — more conservative early), no futility, 95% final look.
  Frozen params unchanged (SESOI ±0.010, looks {60,90,120}, n_trials=30, HAC SE). Double-opus (design +
  independent review) at `reports/audits/e3-jt-amendment-proposal.md`; audit at
  `reports/audits/e3-tost-sequential-correction-review.md`.
- **CONSEQUENCE:** the E3 statistical-gate HOLD from AUD-07B is LIFTED (the gate is now mathematically valid).
  E3 itself remains gated by AUD-06 (live-input readiness) + a separate owner GO (per the AUD-00 dependency
  graph); no E3 ignition is authorized here. Eval-code implementation of the RCI rule is a separate future task.

All owner decisions 2026-08-01 are now executed except RES restart (intentionally held) and optional follow-ups
(RD-08 rule-table re-review, eval-code RCI implementation). Everything is on origin/main.

## Dashboard v2 — near-final-product analysis interface (2026-08-01, built + gated)

Per owner intent ("把现有研究工作台做成接近最终产品形态的分析界面"; data demonstrative only), built a Streamlit+plotly
dashboard realizing `docs/dashboard-v2-design.md`'s 5 dimensions on deterministic synthetic data:
- `dashboard/{demo_data,charts_v2,app_v2}.py` + `dashboard/README_v2.md` + `tests/test_dashboard_v2.py` +
  `reports/design/2026-08-01-dashboard-v2-deploy-research.md`.
- 5 tabs (拟合质量/波动结构/曲线演化/事件前后差异/不确定性), sidebar (Phase/Arm/Horizon/Event-type), publishability gate
  (ci_half<0.015) + "Preliminary data — demonstrates the method" caption on every tab. 11 plotly chart builders
  (alphalens/pyfolio/empyrical methodology, Apache-2.0; no new deps).
- Gated: independent Verifier (AppTest headless render — caught + fixed a `StreamlitDuplicateElementId` crash via
  unique `key=`) + Reviewer APPROVE. 32 tests pass; ruff clean. `src/aionis/**`, `dashboard/app.py` (v1),
  `runs/ledger.jsonl`, data, frozen surfaces all UNMODIFIED.
- RUN: `uv run streamlit run dashboard/app_v2.py`. Deploy: GitHub Pages CANNOT host Streamlit (static-only);
  for the interactive dashboard on a private repo, Hugging Face Spaces (Streamlit runtime, free, private-OK) is
  the recommended host (see the research report). Not yet deployed — owner's call.
- **STATIC site DEPLOYED to GitHub Pages (2026-08-01):** `https://rethymus.github.io/Aionis/` — owner chose
  "static, no interactivity, early-stage presentation." `scripts/build_static_site.py` reuses charts_v2/demo_data
  read-only → `site/index.html` (13 plotly charts, 5 dimensions, EXPLORATORY/DEMONSTRATIVE banner, publishability
  gate). `.github/workflows/deploy-pages.yml` (astral-sh/setup-uv + `uv sync --extra dashboard`; build→upload→deploy
  on push to main). Repo stays PRIVATE; Pages site is public (owner account supports private-repo Pages). Verified
  live (HTTP 200, full content). Independent Verifier PASSED (build, 13 Plotly.newPlot, MD5-deterministic, boundaries).
- **J-T SESOI gate IMPLEMENTED (2026-08-01):** `src/aionis/eval/sesoi_gate.py` + `tests/test_sesoi_gate.py` — the
  executable follow-through of ADR-010's Amendment 2026-08-01. Pure statistical functions (obf_z/obf_alpha/rci_level/
  compute_rci/equivalence_verdict/look_summary/sequential_equivalence_gate) implementing the frozen OBF zₖ=(2.772,
  2.263, 1.960), look-specific RCI levels (99.44/97.64/95.00%), strict-containment equivalence RCIₖ⊂[−0.010,+0.010],
  first-look stopping; reuses `aionis.eval.rank_ic.rank_ic_summary` for HAC SE (not reimplemented). Consumes
  caller-provided IC series ONLY (no E3/ledger/result reads — pure gate logic). Independent Verifier PASS (oracle
  recomputed, strict-boundary, first-look stopping) + Reviewer APPROVE. 28 tests; ruff clean. NOTE: implementing the
  gate does NOT ignite E3 or observe any outcome; E3 still needs AUD-06 + owner GO.
- **AUD-06 live-input readiness gate IMPLEMENTED (2026-08-01, parameterized):** `src/aionis/eval/forward_live_readiness.py`
  (+ tests) + opt-in wiring in `forward_commit_runner.py` (`enforce_live_readiness: bool = False` → historical/no-ledger
  paths SKIP the gate, preserving `_clean_panel`/forward behavior; the live Slice 6/7 caller sets the flag). Fail-closed
  preflight BEFORE any fit/LLM/write/ledger (spy-asserted fit_calls==0 on failure); 25 actionable reason codes; concrete
  checks (predict_session via NYSE, train realized+21-embargo / test retains unknown labels via a forward-specific helper
  NOT `_clean_panel`, price coverage, universe match `constituents_on(t)`, empty-LLM-text→fail, provider-cutoff-not-faked).
  The 2 OWNER-GATED checks are PARAMETERIZED + FAIL-CLOSED when unset: `membership_freshness_contract` (max age /
  authoritative refresh) + `provider_cutoff_policy` (block_on_unknown) — the owner must freeze these before E3 launch
  (the task forbids self-freezing, e.g. treating a 2026-04 snapshot as fresh for 2026-07). Salvaged from a rate-limited
  partial (opus fixer: opt-in flag fixed 2 regressions; fixture/timezone fixes for 8 new tests; ruff). Independent opus
  Verifier PASS (historical-preserved, `_mem_stub` change benign, spy-asserts, fail-closed) + sonnet Reviewer APPROVE.
  47 forward tests pass; ruff clean; ledger/prereg/forward_commit.py untouched. Does NOT ignite E3.
