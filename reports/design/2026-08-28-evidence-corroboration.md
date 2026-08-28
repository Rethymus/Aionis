# 证据互证深挖(Evidence Corroboration)— 路线图主张 × 真实研究逐条对账

- 日期:2026-08-28(深挖轮,继 `2026-08-28-future-roadmap-research.md`)
- 方法诚实声明:本文件全部 arXiv 条目来自 **arXiv API 实检抓取**(HTTPS+UA,逐条摘自官方 abstract,无凭空生成);OpenAlex/Semantic Scholar 因出口 429 未取得引用数(如实放弃,不编造)。标注 **[领域知识]** 的条目为模型知识综述、未经本次在线核验,单独分级。
- 通道:arXiv API,查询面:factor zoo / knowledge cutoff / LLM trading agent / q-fin multiple testing / probability of backtest overfitting / alpha decay / look-ahead / pre-registration forecasting(共 12 次实检索)。

---

## 主张 1:Look-ahead 泄漏是 LLM 时代金融评估的第一问题(→ 路线图全部;E3/P1-2 的立论)

| 独立研究(arXiv 实检) | 日期 | 关键证据 |
| --- | --- | --- |
| DatedGPT: Preventing Lookahead Bias in LLMs with Time-Aware Pretraining | 2026-03 | 12 个按年度截断预训练的 1.3B 模型;实测 **lookahead premium = 每标准差 26.4bp**——泄漏的价格第一次被定量 |
| Look-Ahead-Freedom as Temporal Non-Interference | 2026-07 | 提出把 look-ahead 自由定义为回测与 agentic 管道的**可验证正确性属性**(verifiable correctness property)——与 Aionis I1-I9 不变量同构的形式化路线 |
| Look-Ahead-Bench | 2026-01 | PiT LLM 金融 look-ahead 标准化基准;指出多数既有测法只测 Q&A 式"内在知识",须测工作流级泄漏 |
| OpenPM: Auditable Point-in-Time Evaluation for LLM Portfolio-Management Agents | 2026-08 | LLM 交易 agent 的已发表结果"可被 look-ahead 泄漏、乐观执行、纸面风控要求"抬高——需要**可审计 PIT 评估** |
| From Knowing to Doing: A Memory-Controlled Benchmark for LLM Trading Agents | 2026-05 | 长回测常与训练数据重叠;提出记忆受控基准防两类评估失败 |
| Can LLMs Be Constrained to the Past? | 2026-06 | 提示词式知识截止不可靠——支撑 P1-2"vintage 入 ledger + 探针检验"而非口头约定 |

**结论**:6 篇独立研究(3 个不同子领域)在 2025-2026 集中收敛——Aionis 的反泄漏宪法不是过度设计,是文献新共识。

## 主张 2:静态历史回测不可信,活体前瞻协议是唯一强证据(→ P0-1 E3)

| 独立研究 | 日期 | 关键证据 |
| --- | --- | --- |
| TS-Arena — A Live Forecast Pre-Registration Platform | 2025-12 | 因历史评估的 train-test 重叠风险,建**活体预注册平台**——与 E3 commit-then-reveal 跨域同构(时序基础模型领域) |
| LiveHouse-TS: Open-world Living Benchmark | 2026-08 | 首个流式活体基准:**静态排名在 live 协议下剧烈洗牌** |
| Fin-Analyst at FinMMEval 2026 | 2026-07 | LLM 交易 agent "缺乏 live 部署证据"——live 评估是稀缺品 |
| CLQT: Closed-Loop, Cost-Aware Benchmark for LLM PM Agents | 2026-06 | 固定窗口收益率排名是弱代理:**市场路径主导单期收益,表观 alpha 会溶解** |
| **[领域知识]** McLean & Pontiff 2016 JF | — | 发表后因子收益衰减 1/3-1/2(样本外=真实外的另一形态) |

**结论**:E3 commit-then-reveal 与 TS-Arena 的活体预注册在两个领域独立出现——P0-1 的最高优先级有跨域印证。

## 主张 3:校准与分差比点命中重要(→ atlas 分差带/校准区块;P2-3)

| 独立研究 | 日期 | 关键证据 |
| --- | --- | --- |
| FinBench: Time-Gated Calibration and Uncertainty Benchmarking | 2026-06 | 金融 LLM 的关键失败模式="**confidence–competence gap**";按时间门控测校准与不确定性 |
| TabPFN-TS 系统评估 | 2026-08 | 同精度下比较**校准质量**(better calibration)作为选型标准——校准已成为工程选型指标 |
| **[领域知识]** Gneiting & Raftery 2007 | — | 严格适当评分规则(Brier/log score)是概率预报的唯一诚实汇总 |
| 本仓 D2 分差带实测 | 2026-08 | 预测概率带对实现基准率的月度覆盖率 US 7/53=13%、CN 7/54=13%——本项目自己的"分差"实证 |

## 主张 4:试验次数必须入账,多重检验必须修正(→ RD-17 trial registry;P0-2 multiple_testing P1)

| 独立研究 | 日期 | 关键证据 |
| --- | --- | --- |
| MinervaScore: Luck or Edge? | 2026-08 | 回测常是多参数试选后的幸存者;"return/Sharpe/drawdown **不记录试过多少候选**"——试验计数本身是统计量 |
| **[领域知识]** Harvey-Liu-Zhu 2016 RFS | — | 316 个已发表因子,t≥3.0 新阈值;haircut p 值(2017 JPM) |
| **[领域知识]** Hou-Xue-Zhang 2020 RFS | — | 452 异象 65% 过不了 t≥1.96 |
| AlphaAgent | 2025-02 | AST 原创性检查+去重=对既有因子库的多重性管理 |
| 本仓 P1 实例 | 2026-08 | `multiple_testing.py` 极端 p 值灾难性消零(+Infinity 且 survives=true)——**工具链本身的缺陷会反转结论**,P0-2 必要性的直接内部证据 |

## 主张 5:Alpha 衰减是可测量的规律,不是叙事(→ P3-2 decay 监测;P1-1 Track A 正交性检查)

| 独立研究 | 日期 | 关键证据 |
| --- | --- | --- |
| Not All Factors Crowd Equally | 2025-12 | 从博弈均衡**推导双曲衰减律 α(t)=K/(1+λt)**,8 个 FF 因子 1963-2024 实证胜过线性/指数——衰减有了函数形式,P3-2 面板可直接拟合对照 |
| T-KAN for LOB | 2026-01 | 高频限价簿 alpha 随 horizon k 衰减的实证 |
| Alpha-R1 | 2025-12 | LLM 强化学习筛因子,明示信号衰减与 regime 切换为首要挑战 |
| Financial Epiplexity | 2026-07 | 市场难预测"非纯随机,而是**结构是策略性的、容量受限的、计算上困难的**"——"蝴蝶效应拟合度"命题的理论化正确表述(有界计算下的可学习性) |

## 主张 6:LLM 研究产物需要 PIT/溯源纪律(→ P1-2;extraction 线)

| 独立研究 | 日期 | 关键证据 |
| --- | --- | --- |
| Reconcile Once, Write Anytime: Trust-Tiered Librarian + Multi-Agent Writer | 2026-08 | LLM 长研究报告"漂移、自相矛盾、丢失溯源:同一指标出现不同数值,传闻与审计申报同等自信引用"——解法=**可信分级+PIT 纪律**,与 Aionis 溯源体系同构 |
| The Stanford EDGAR Filings Dataset | 2026-06 | EDGAR 一手申报重建为 token 高效预训练语料——Aionis 的核心源族正是 LLM 金融研究的公共语料基座 |
| Auditing Asset-Specific Preferences in Financial LLMs | 2026-06 | 金融 LLM 存在可测的资产偏好偏差——provider 池多路互证(GLM/SiliconFlow/ModelScope)的又一理由 |

## 主张 7:智能成本 vs 交易价值(→ RD-09 cost kernel;bps_sweep)

| 独立研究 | 日期 | 关键证据 |
| --- | --- | --- |
| Can Agentic Trading Systems Pay for Their Own Intelligence? | 2026-07 | 提出评估 agent 的"viable 性":动态推理/工具成本必须被交易价值覆盖——现有评估几乎不问 |
| FR-LUX | 2025-10 | 纸面组合死于交易成本与 regime 切换;成本感知 RL 才可实施 |
| Entropy-based randomness test (UHF) | 2023-12 | Shannon 熵/KL 散度检验超高频价格可预测度——可预测性有熵上界 |
| 本仓 bps_sweep | 既有 | 成本扫描面板已是既有实践 |

---

## 与路线图的对账结论

1. **P0-1(E3)**:主张 1+2 双重支撑,跨域(TS-Arena)同构印证——最高优先级坐实。
2. **P0-2(15 条 P1)**:MinervaScore"试验计数是统计量"+ 本仓 multiple_testing P1 = 修复优先级坐实。
3. **P1-1(Track A)**:AlphaAgent/Alpha-R1/Not All Factors Crowd Equally 提供"生成-评估-防衰减"的组件级蓝图,但**全部在历史回测内评估**——Aionis 的差异点(预注册+purged CV+haircut)恰是它们的盲区,机会坐实。
4. **P1-2(LLM vintage)**:Look-Ahead-Bench + Can LLMs Be Constrained to the Past + DatedGPT 三篇独立支撑"vintage 入 ledger+探针"设计。
5. **P3-2(decay 监测)**:双曲衰减律给了可拟合的函数形式,从"叙事"升级为"回归"。
6. **定位句**(roadmap §1b)增补:2025-2026 文献已出现 Aionis 各设计要素的**孤立镜像**(可验证 look-ahead 属性、活体预注册、PIT 溯源分级、校准门控基准),但**尚无单一框架同时集成**——"集大成者"空位真实存在,且有时间窗。

## 证据分级与残余缺口(诚实)

- **A 级(本次 API 实检)**:上表全部 arXiv 条目(22 篇,标题+日期+摘要核对)。
- **B 级(领域知识,未在线核验)**:HLY 2016/HXZ 2020/McLean-Pontiff 2016/Gneiting-Raftery 2007 的具体数字;待配额恢复后经 OpenAlex 引用数二次核验。
- **缺口**:OpenAlex/Semantic Scholar 引用数(影响力维度)未取得;经典论文的期刊卷期页码未核。路线图结论不依赖这些数字的方向,但依赖其存在性——B 级条目在转正前不作为唯一依据。
