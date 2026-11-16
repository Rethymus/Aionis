# 训练期点火：2016 起步 walk-forward 黑箱预推演（三段式）设计

> 业主定夺（2026-11-17）：历史数据黑箱式预推演作为点火期，2016 起步、逐月掩蔽 walk-forward，
> **推演过程中允许调参与自我蒸馏**——将 RLCD 训练法个性化适配拉满。
> 本文档 = 该架构的权威规格（轮 24 任务书级）；执行载体 = aionis-iterate 轮 24。
>
> **框架演化如实注记**：主会话 2026-11-16 曾提「回放期禁调参」三铁律（保守彩排定性）；
> 业主 11-17 定夺改为**训练期定性**——本设计将三铁律改写为四条（禁调参 → 训练/验证分离）。
> 禁调参条款并未消失，而是移动到了冻结验证期与真实在线期。

## 0. 定性：回放 = 训练期，非彩排

原版 RLCD 的本义是在历史数据上训练、在未见数据上验证。Aionis 的外环训练法（不改权重、
训练信号作用于上下文与流程）与此完全同构：2016→2025-12 是**训练语料**，回放 = 训练运行。
推论：训练期内的拟合度提升是**训练拟合**，永不作为能力证据呈现；能力证据只来自冻结验证期
与真实在线期。这与 ML 通行的 train/validation/test 三分法在时间轴上的映射一致。

## 1. 三段式时间轴

| 段 | 窗口 | 轮次 | 系统状态 | 结果的地位 |
|---|---|---|---|---|
| 训练期 | 2016-01 → 2025-12 | ~120 月 | **自由调参**：逐月推演+比对真实+反思+蒸馏+年界调参 | 训练拟合度（in-sample，不作能力声称） |
| 冻结验证期 | 2026-01 → 2026-10 | 10 月 | **系统冻结**（参数快照+SHA256 落盘，回放层 config_committed 同构） | 第一个诚实 holdout 读数 |
| 真实在线期 | 2026-11-30 起 | 逐月 | 冻结系统 + 预训练 lessons 热启动 | 持续真实检验（test 段） |

- 训练/验证切点（2025-12/2026-01）为默认值，业主可改；**改动须在看到任何 y 之前**。
- 真实点火照常从 11-30 开始——回放不预烧真实飞轮的第一个月；真实期 ledger
  `prediction:/outcome:` 双零区照常从零起步。
- 预训练 lessons 库（训练期蒸馏产物）以 `distilled-from-replay` 溯源标签进入真实期
  热启动；其效应于真实期如实注记「lessons 非未见数据」。

## 2. 四条铁律（改写自 11-16 三铁律）

1. **拟合度 = 校准拟合，非方向命中**：可追求的是校准可靠性——p 是否匹配经验命中率
   （Brier (p−y)² / BSS vs climatology / 可靠性曲线 / ECE）与判别流程零错率；
   **明确不追方向命中率提升**——confirmatory IC=-0.0088（null 结果），历史 sign 无可学信号，
   训练期方向命中率的任何"改善"按噪声拟合处理并如实标记。蒸馏方向同理：insight 沉淀
   校准教训（"此类月 p 压向 0.5"），不沉淀方向规律（"CPI 月 IC 偏正"= 噪声拟合）。
2. **零账本污染 + 全程 EXPLORATORY 标签**：不写 `runs/ledger.jsonl`、不写
   `state/calibration-months.md`、不触研究管线（`src/aionis/`、`scripts/phase_*`、
   冻结 config、预注册两尾主张）；产物隔离 `reports/exploratory/replay/`；全标签
   EXPLORATORY REPLAY——not a claim, not a gate（沿 ledger exploratory 事件语义）。
3. **掩蔽证明随轮归档**：t 轮黑箱上下文 = 全序列截断至 t-1；每轮留档上下文快照
   SHA256 + 行数断言 `rows ≤ t-1`（沿 data_snapshot_audit 的 history-rewrite 绊网先例）——
   「没偷看」是可审计事实而非声称。LLM 轮次 prompt+输出逐轮存档（诚实注记：引擎侧
   确定性可复现；LLM 侧非位一致，存证不复算）。
4. **配置先冻结后观察**：窗口、切点、黑箱提供方、claim 形态、insight 注入预算——
   全部参数在看到第一个 y 之前落盘 `config-frozen.json` 并记录 SHA256 于报告；
   杜绝「边跑边改窗口」的元污染。

## 3. y 源与覆盖审计（轮 24 第一步）

- **y 源**：realized rank-IC 序列（confirmatory 管线逐月冻结产物）。claim 形态（v1 单族）：
  `{claim: "t 月 realized rank-IC 为正", due: t, p: <黑箱于 t-1 时点>}`，outcome
  `y = 1[IC_t > 0]`。sign 预测本质接近掷硬币——这正是校准演练的价值所在。
- **覆盖审计分支**：PBO 诊断 `n_obs=125`（≈10.4 年）暗示面板回到 ~2016；若
  `ic_monthly.json` 早段（2016→面板起点）缺行，则用冻结管线
  `PHASE_*_NO_LEDGER=1` 模式补算历史 IC（影子 runbook 先例，EXPLORATORY 诊断语义）。
  审计结论决定走「读现成序列」或「NO-LEDGER 补算」分支——两分支都不触研究面语义、
  都不改冻结 config 字节。

## 4. 调参治理（训练期）

- **年界检查点**：每个年界（~10 次）为调参周期——比对当年逐月记录与真实数据，
  调参 delta 落 append-only 调参日志（`tuning-log.md`：日期/参数/旧值/新值/依据轮次区间），
  训练轨迹可审计、可回放。
- **可动（ops/meta 层）**：prompt 模板与 lesson 格式；五桶宽度→自适应分位桶
  （nci/scores 锚：isotonic/分位桶口径）；注入预算 top-N；insight 三判据阈值与分级；
  **X-N-Y-M 定标**（悬置项就此解决：用训练期校准数据定标，业主保留最终采纳钥匙）；
  对比对构建（训练期天然产生好/坏 episode 语料）。
- **永不可动（研究面红线）**：`src/aionis/`、`scripts/phase_*`、冻结 config 字节、
  `runs/ledger.jsonl` 语义、预注册两尾主张——飞轮是 meta/ops 层训练，研究主张证据链
  与之完全隔离。
- 调参在检查点之间禁用（检查点内逐轮不调）——保证训练轨迹的分段可归因。

## 5. 自我蒸馏语料生产线（RLCD 个性化适配「拉满」的落地）

125 轮逐月完整循环（预测→对账→反思→insight→下月注入）产出四件套：

1. **预训练 lessons 库**：带 `distilled-from-replay` 溯源标签，真实期热启动；
   lifecycle（ADD/UPDATE supersedes，Memp 程序性记忆同构）在 120 轮下全速压力测试——
   注入按 top-N active 上限（参数冻结先行）。
2. **对比对语料**（环1b 的 RLCD 对比信号弥合）：最好/最差预测月的成对案例
   （contexts + p + y），供真实期环1b 注入与未来语义判据训练。
3. **校准曲线**：125 点 reliability plot + 分年 ECE/BSS 轨迹——比 12 点演示有说服力
   一个数量级。
4. **多模型对照（T2，可选）**：GLM vs SiliconFlow 同题分歧 = 判别器弱信号
   （llm_memory_probe 先例）。

## 6. 三层执行与规模

| 层 | 黑箱 | 验证什么 | 规模 |
|---|---|---|---|
| T0 引擎验证 | climatology 基线（恒 p̄） | 引擎算术在真实数据自洽；BSS≡0 为构造性预期（非零=bug） | 全窗口，零 LLM |
| T1 飞轮回放 | LLM 会话（GLM；按年分块 ~11 会话，lessons 跨块累积） | 完整训练循环真实转动 | ~40 万 token |
| T2 多模型对照 | SiliconFlow 同题 | 分歧信号预演 | T1 ×~1 |

politeness：模型 API 不适用 ≥2s host-spacing（AGENTS.md 既有口径）；RPM/TPM 由
ProviderRouter 承担。

## 7. 产物清单（全部落 `reports/exploratory/replay/`）

`config-frozen.json`（+SHA256 入报告）/ 逐月记录表（prompt、{answer,p}、y、(p−y)²、
快照 SHA、行数断言）/ `tuning-log.md` / lessons 库+对比对 / 校准曲线图 /
`replay-report.md`（逐月表+分段拟合度+冻结验证期读数+掩蔽证明汇总+预期对照）。
九段式证据链结构沿首月剧本步序（--propose 打卡→填 p→--verify-bounded→outcome→
reconciliation→lessons）逐月留档——彩排欠的证据链由真实历史数据补齐。

## 8. 与在册锚的关系（不重登，只引用）

⑱ RainCheck 2610.38211（BSS 相对 climatology 报告口径）/ ⑲ Anytime-Valid 2610.28979
（月度连续监控须 anytime 校正——回放为批处理离线，不受此约束，注记即可）/ ⑳ LIMBO
2609.14138（回放非免费、注入须显式预算）/ ERL 2603.24639（INSIGHT 0-2 上限）/
data_snapshot_baseline 绊网（history-rewrite 检测）/ 轮 6+轮 10 彩排先例
（--repo tmp 覆写 + SYNTHETIC 标注——本回放沿用机制、换真实历史数据）/ RLCDAlignBench
80 + JevAdvBench 81（问句设计与置信行动边界的实证读数）/ 2610.25846（verbalized
confidence 单通道效度）。

## 9. 预期管理（先写下来，防回放后误读）

- sign 预测 ≈ 掷硬币：**成功判据 = p 收敛诚实（→0.5）+ 校准机器全链零错 + 蒸馏产物
  质量**，而非方向命中率高。
- T0 的 BSS≡0 是构造性成功；T1 的 BSS≈climatology 是**诚实性成功**。
- 冻结验证期读数低于训练期拟合度属预期（in-sample→holdout 回退）；回退幅度本身是
  第一条有价值的 meta-读数。

## 10. 边界

本文档 docs-only（`reports/design/` lane）；轮 24 施工前 `test -f` 实证不存在。
ledger/frozen/OOS/研究面零改动；零装包零新依赖（T0/T1 全部复用现有引擎与 provider 池）；
引擎侧改动（若覆盖审计要求回放装载器）限于 `scripts/` ops lane，逐条 mission 指名。
