# Aionis 未来高价值方向深度调研与优先级路线图

- 日期:2026-08-28
- 状态:PROPOSED(方向文件;每项实施前按 lane 走各自 gate)
- 调研通道(诚实披露):WebSearch 后端周配额尽(09-03 重置)→ 改用 **arXiv API 一手检索**(LLM alpha mining / agent harness / LLM 收益预测三路,20 篇 2024-2026 文献)+ 计量金融领域知识综述;仓内 backlog/tasks/active/blockers 全盘点。
- **深挖互证(2026-08-28 第二轮)**:`2026-08-28-evidence-corroboration.md` —— 追加 8 个查询面、22 篇 API 实检文献,把本路线图每条主张对账到 ≥3 独立研究(含 Look-Ahead-Freedom 可验证属性、TS-Arena 活体预注册、FinBench 校准门控、双曲衰减律);证据分级 A(API 实检)/B(领域知识待核)已声明。

---

## 1. 三条外部信号线

### 1a. LLM 因子挖掘生态(2024-2026):闭环自动化成为主流,但评估纪律缺位

一手文献(arXiv API 实检):AlphaSchema(2026-07,交易语义空间)、CogAlpha(2025-11,代码级进化)、TreEvo(2025-08,树状思维进化)、**AlphaEval(KDD2026,免回测五维评估)**、Chain-of-Alpha(2025-08,A 股全自动)、MCTS 因子挖掘(2025-05)、**AlphaAgent(2025-02,抗 alpha decay:AST 原创性检查+假设-因子对齐+复杂度约束)**、GPT-Signal(FINLP 2024)。加上领域知识线:Alpha-GPT/2.0、QuantActor(QuantAgent 双循环)、AlphaForge、QuantFactor-REIN。

**共同盲区**:这条文献线的"评估"几乎都是回测内优化——恰恰是 Aionis 预注册+purged CV+多重检验设计所反对的 overfitting 工厂。少数例外(AlphaEval 的五维免回测评估、AlphaAgent 的原创性/正交性检查)可以**移植为 Aionis 反泄漏框架内的组件**。

### 1b. AI harness 科学(2026):harness 与模型分离,"external verifiability" 是下一个分化轴

arXiv 实检(2026-08 一周内):HarnessLens(预算感知的 harness 进化验证——只跑行为相关任务省 7.6-13.6% 预算)、Recuris(验证门控的记忆进化)、StarHarness(分层搜索进化 harness,权重冻结,金融基准 +20-35pp)、**三 harness 架构收敛案例研究(五共享要素;"external verifiability" 为缺失的分化轴)**、Pufibara(232 任务基准,token 效率)、feedback backfires(错误反馈反噬=hook 设计教训)。

**对 Aionis 的映射**:Aionis 本身就是一个**量化研究 harness**(Orchestrator/Engineer/Verifier/Reviewer 角色分权、ledger 审计链、契约闸门、全套 pytest 纪律)。文献指出的"external verifiability"(外部可验证性)恰是 Aionis 的既有立身之本(ledger/config sha256/commit-then-reveal)——**这是文献承认的稀缺轴,Aionis 已站在上面,应该显式化并输出**。

### 1c. 金融计量基础:factor zoo 复制危机是 Aionis 存在的理由

Harvey-Liu-Zhu(2016 RFS,t>3.0 阈值)、Harvey haircut p 值(2017 JPM)、McLean-Pontiff(2016,发表后因子衰减 1/3-1/2)、Hou-Xue-Zhang(2020,452 异象 65% 复制失败)、Jensen-Kelly-Pedersen(2023 反驳)、Bajgrowicz-Scaillet FDR。**DatedGPT(2026-03,时间感知预训练,实测 lookahead premium = 每标准差 26.4bp)第一次定量证明了 LLM 时代 lookahead 污染的价格**——这是 Aionis 反泄漏立场的直接外部佐证。

**Aionis 的定位一句话**:文献里没有人在同一框架内同时做到——预注册可证伪主张、purged CV、commit-then-reveal forward live、LLM 提取线 vintage 纪律、诚实 NULL 呈现。Aionis = LLM 时代因子研究的**可证伪评估 harness**。

---

## 2. 与业主命题的对接

业主命题"锚定预测数据与未来真实数据之间的可能性,验证数学逻辑与计算机能力在金融领域对蝴蝶效应的拟合度与分差值"→ 本仓的正统实现即:**E3 forward-live(commit-then-reveal)+ 预测校准/分差带可视化(已上线)+ 可预测性衰减的实测(horizon sweep + 因子 decay 监测)**。"蝴蝶效应"在计量上的诚实翻译=对初始信息集的敏感性与可预测性随 horizon 的衰减,而非点命中。

---

## 3. 优先级排列(未实施项,细致阶梯)

### P0 —— 最高价值,门已开或修复型,立即排队

- **P0-1 E3 forward-live 发射准备**(旗舰;业主命题的正统锚定)
  现状:Slice 1-7 全完成(ledger 核心/PIT ingest/commit 管道/评分累积/dashboard tab/调度器/E2E+I1-I9);AUD-07B 已解(Jennison-Turnbull RCI 等价门已实现);AUD-06 已实现(`forward_live_readiness.py`)。
  剩余细项:① 业主冻结 2 个 AUD-06 契约(`membership_freshness_contract`、`provider_cutoff_policy`);② 业主 headline GO(ADR-010 门);③ shadow 1-2 月试运行(业主 2026-07-30 已定默认);④ **forward 结果接入 web 终端**(现只在 streamlit dashboard 有 tab——把 forward ledger 读数做成 web 面板+atlas 分差区块联动,display lane 可先行);⑤ E3 触发器 workflow 保持 active(0 runs,不产生噪音)。
  规模:S(①②裁决)+ M(④);前置:仅业主 GO。
- **P0-2 code-review 库 15 条 P1 修复**(修复型;多条直指 forward/multiple-testing 线)
  现状:`docs/code-review/SUMMARY.md` 列 15 条未修 P1。高危样例:multiple_testing 极端 p 值灾难性消零(+Infinity 且 survives=true,与结论相反)、forward_score 时间戳未 normalize(live 路径必炸)、runner 把 provider_cutoff 伪造成 predict_ts(恰是 AUD-06 要拦的)、冻结 config VIX 锚钉错文件(输入未入 sha256)、基本面 PIT 过滤 no-op、pytest.skip 占位测试(违反 DoD)。
  实施细项:① 逐条复核现状(68 条已被后续 commit 修复,15 条需重验是否仍存在);② 仍存者按"一条一原子任务"修复+回归测试;③ E3 GO 前必须清掉 forward 线三条(P0-1 的硬前置);④ Verifier/Reviewer 独立复核流程照 AGENTS.md。
  规模:每条 S-M;总 M-L;前置:无(研究/eval lane,需全套 pytest)。
- **P0-3 研究传播层收尾**(display lane,零门)
  细项:① horizon sweep h=10/42 补 E1 对称性(backlog 存项,S);② metrics/atlas 背景线加 Harvey t>3.0/haircut 语境(把本研究 CI 与文献阈值并列——display 派生,直接强化"NULL 判定的可信度"叙事);③ atlas 四区块的 RSC 数据随面板日更的联动自检(display 契约测试)。
  规模:S×3;前置:无。

### P1 —— 高价值,研究线,需预注册级业主 GO

- **P1-1 Track A 因子生成器**(LLM 因子挖掘 × Aionis 反泄漏 eval;业主既有授权方向)
  文献对接:AlphaAgent 的抗 decay 三件套 → Aionis 化:① LLM 生成假设/因子表达式(既有 GLM/SiliconFlow/ModelScope 池);② **trial intent registry(TASK-RD-17 已立项)先注册后评估**;③ purged CV + SESOI + **haircut p 值(FDR/Harvey 修正)作为预注册判定**;④ 与冻结因子库的正交性/原创性检查(alpha decay 防护);⑤ 全程进 ledger。实施细项即 RD 系列任务单(RD-01 linter/RD-04 gold schema/RD-05 sampler/RD-06 metrics/RD-07 report/RD-08 zero-LLM baseline/RD-11 provider replay/RD-12 PIT universe oracle/RD-13 横截面变异守卫/RD-14 复现 capsule)——它们就是 Track A 的地基,应按依赖序激活。
  规模:L;前置:RD 系列就绪 + 业主预注册 GO。
- **P1-2 LLM 提取线 vintage 纪律**(DatedGPT 启发;反泄漏立场的补全)
  细项:① provider 模型卡的知识截止 vintage 声明写入 ledger(结构化字段);② 探针式 vintage 检验(已知事后事实集探测模型知识边界,进 evals/);③ 与 AUD-06 `provider_cutoff_policy` 契约合一(E3 GO 共用);④ 26.4bp lookahead premium 作为文档动机引用。
  规模:M;前置:P0-2 的 cutoff 相关 P1 清理。
- **P1-3 R1-full decile 收益单调性**(业主门已记录)
  细项:与冻结 run 的收益口径对齐说明书(next-open/close 复算逐月对账)→ 口径一致后派生 decile 面板 + atlas 第五区块(单调性棒图)。
  规模:M;前置:业主对口径工程的 GO。

### P2 —— 中价值,基建/展示

- **P2-1 R2 独立图表工件**:构建期生成自包含 HTML/SVG 证据包(phase 报告插图、可分享单文件)——harness 语言里的 external verifiability artifact;含 Mermaid/Draw.io 源重绘通道。规模 M;display lane。
- **P2-2 部署/CI 恢复**(H1 业主门):billing 修复 re-run,或按 `2026-08-22-realtime-deployment-architecture.md` 迁 CF Pages(deploy workflow 可退役);附带修 CI 13D cron 22:00 UTC 抓传播窗口中段问题(调 cron 时间)。规模 S-M;前置:业主。
- **P2-3 预测评估层小升级**:Brier/reliability 已有;按需补 decisiveness 分解;低优先。规模 S。
- **P2-4 韩国杠杆 A/B 升级、TACO 等价源升级**(旧豁免项,源就绪即可换)。规模 M each。

### P3 —— 远期/记录性

- **P3-1 Harness 自指演进**:HarnessLens 式 budget-aware verification(Agent 只跑行为相关测试子集)——与"改共享函数后必须全套 pytest"纪律有张力,仅记录想法,不启。
- **P3-2 因子 decay 监测面板**:对冻结 IC 序列做 rolling 衰减监测(display 派生可做,价值中等)。
- **P3-3 earnings abstain 预注册臂**(backlog 存项;BLOCKED 于 E3 headline GO + 新预注册)、SIC vintage(low,效应小)。

---

## 4. 排列原则与即时建议

排序依据:① 对"可靠性主张"的证据强度(forward live > 修复评估线缺陷 > 新评估层 > 展示);② 反泄漏纯度;③ 门的状态(已开 > 低门 > 业主门)。

**若只做三件事**:P0-2 的 forward 线三条 P1(清 E3 路障)→ P0-1 业主契约冻结+shadow 启动 → P0-3 传播层收尾。研究线(P1-1/P1-2)在 E3 shadow 期间并行准备 RD 系列地基。

---

## 5. 剩余未实施项优先级排列(2026-08-30 轮㊿ 后快照,前两版第 5 节作废)

**本轮已销项(轮㊷–㊾+㊿)**:前端真实性五修+WCAG 扫零(㊷)、v2 演示面退役+navy 描边修复+ruff 0.16(㊸)、长周期查漏补缺协议建立与四轮执行(㊺–㊾:Streamlit v1 三层运行时修复/coverage 账本接线/reddit 信封类型化/docs 六死链/RESULTS 逐位对账 ALL MATCH/视觉管线根因修正/19 页双主题全量巡检零缺陷)、GitHub Pages 再更新(㊿,gh-pages 手动通道 main@606643e 在墙验证)。

### P0 —— 业主门/时间敏感(本周)
1. **E3 月末影子完整跑(时间敏感度最高——08-31 即月末)**:Phase4 缓存收尾(570/587,tiingo 429 会话自愈)→ `e3_forward_trigger.py` shadow 完整跑通(单进程 ~40min;PHASE_E3_NO_LEDGER=1)→ 此后每月末例行(计费解冻前 cron 不可用)。影子积满月数(业主 07-30 定 1-2 月)即解锁 headline 裁决。
2. **headline GO(唯一不可代行)**:业主对非影子首次提交点头——此门不可下放;建议影子满 2 个月(≈10 月末)后一并裁决。
3. **GLM cutoff 厂商声明升级**:probe v1(2023-03-10)安全常驻冻结 YAML;厂商日后声明则覆盖(provenance 升级 vendor)。无业主动作亦安全。

### P1 —— 研究线(需预注册级业主 GO)
4. **Track A 因子生成器**:RD-01~17 任务单为地基;AlphaAgent 三件套(原创性/对齐/复杂度)Aionis 化;trial registry 先注册后评估;haircut p 值判定。
5. **LLM vintage 纪律深化**:探针套件 CI 化(每 provider/模型定期实测)+ 模型卡 vintage 字段联动(probe v1 已是模板)。
6. **R1-full decile 收益单调性**:冻结收益口径对齐工程 → 面板 + atlas 第五区块。

### P2 —— 显示/基建(零门,可即刻排队)
7. **数据新鲜度扫荡(本轮新增——已到期)**:上次全量扫荡 08-29(轮㊳),日更面板已 1-2 天陈旧且 Pages 刚重发布;按轮㊳ 模板本地扫荡(13D 日更步 2400s 帽教训)+ 全套 pytest + 契约闸门。
8. **长周期查漏补缺协议·周期 2 续轮(常设节奏项)**:AppTest 随 Streamlit 改动重跑(含 earnings 真实数据路径——待 cache 补齐)、i18n 二轮(英文语法级+其余 hub 术语)、prereg↔冻结 YAML 只读一致性核验、漂移扫描器随新面板守门。协议见 `2026-08-30-longcycle-gapfill-protocol.md` §3。
9. **谱系 v3**:链上挂各配置 diff 数字与 dossier 互链(决策→结果直读)。
10. **R2-full 工件矩阵**:多 claim 档案、版本化、CI 挂钩(shadow 数据入库后自动更新 dossier)。
11. **atlas 小项**:i18n 表头残余、上游面板变更触发 dossier/工件自动重生成钩子。

### P3 —— 远期/记录性
12. 韩国杠杆 A/B / TACO 升级(源就绪即可换);13. BLS 传输策略接受(AUD-05C-C1);14. earnings abstain 臂与 SIC vintage(E3 GO 后);15. 模型卡 v2 多 run 卡片化(每 confirmatory run 一卡,清单表直链);16. **Streamlit `use_container_width` 弃用迁移 watch**(已过 2025-12-31 截止日,1.59 容忍;升级 Streamlit 时统一迁 `width=`,22 个调用点)。

**部署通道现状**(2026-08-30 复验):Actions 计费封锁 → **gh-pages 手动通道为标准**(本地 build→临时仓库→force push gh-pages→Pages legacy 源自动构建;㊿ 在墙验证 built c455849/live 内容含轮㊺+修正);Actions 解冻后恢复 deploy workflow 并退役手动通道。
