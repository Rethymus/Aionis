# Aionis 后续研究开发任务路线（低推理模型，8+ 小时）

- 日期：2026-08-01
- 性质：研究与任务冻结；**不是实现授权**
- 适用对象：可稳定执行明确代码任务、但不应承担方法学判断的低推理模型
- 结论：继续研究有价值，但价值中心应是“可证伪的 PIT 研究基础设施 + 可审计的小模型抽取”，
  不是端到端 LLM 交易代理或短期寻找显著结果。

## 1. 当前事实与判断

- [F] B/C/D/E1 的现有证据是 purged cross-fit/CV proxy，不是 chronological/live OOS；四个
  treatment bundle 没有可靠正增量，且 headline arm 尚未真正使用 LLM 特征。
- [F] E3 commit/reveal、forward ingest、scoring 和 dashboard 已有主体代码，但 live-input readiness、
  scheduler/E2E 与人工门禁未闭合；现在启动不可逆前向序列不安全。
- [F] AUD-05C C1/C2 已 Engineer 完成但仍需独立 Verifier/Reviewer；C3 已获 owner 条件授权，
  但尚未实现；C5 仍是 owner 决策。
- [I] 当前最稀缺的不是更多因子或更多 agent，而是能说明“小模型到底抽对了什么、相比零 LLM
  增加了什么、在 chronological 与交易摩擦下还剩什么”的评估链。
- [D] 后续 8+ 小时开发优先建设确定性、离线、可回滚的评估基础件；不运行真实研究，不写 ledger，
  不观察 E3 outcome，不修改 frozen spec。

## 2. 前沿证据如何改变路线

| 证据 | 事实 | 对 Aionis 的任务含义 |
|---|---|---|
| [FinTagging](https://arxiv.org/abs/2505.20650) | 结构化金融抽取可拆成“识别”与“概念链接”；模型在细粒度链接上明显更弱 | gold set 与 evaluator 必须按字段/阶段计分，不能只给一个总体准确率 |
| [FLaME](https://arxiv.org/abs/2506.15846) / [FinBen](https://arxiv.org/abs/2402.12659) | 金融 LLM 的任务差异很大；信息抽取通常强于复杂推理/预测 | 把小模型限定为闭集结构化抽取器，不让它直接预测收益或做数值执行 |
| [AlphaForgeBench](https://arxiv.org/abs/2602.18481)（官方仓库 MIT） | 端到端动作序列有严重运行间不稳定；确定性 evaluator 更适合裁决 LLM 提案 | 保持“LLM 提取/提案，确定性代码裁决”，并记录每次输出与解析版本 |
| [FINSABER](https://arxiv.org/abs/2505.07078) | 更长窗口、更大 universe 下，许多 LLM 投资优势衰减 | chronology、survivorship、next-open 与成本必须先于盈利叙事 |
| [The Alpha Illusion](https://arxiv.org/abs/2605.16895) | LLM agent alpha 不能直接视为部署证据；需要时间完整性、摩擦、校准和模块拆分 | Aionis 继续作为 evidence-first harness，而不是 TradingAgents 类系统 |
| [Stanford EDGAR Filings Dataset](https://arxiv.org/abs/2606.18192) | EDGAR 可重建为版面忠实、token-efficient 的金融文本语料 | 未来可研究更好的文档切片，但数据许可与 PIT intake 必须单独过 7 门 |
| [Microsoft Qlib](https://github.com/microsoft/qlib) | 成熟 workflow/IC/报告架构可借鉴 | 只借鉴接口与报告思想；不引入其不合规数据源，也不替代 Aionis PIT/ledger |

注意：论文或仓库的代码许可不自动覆盖其数据、模型权重和服务条款。任何外部语料、权重或数据
进入项目前仍必须独立通过 7-gate。

## 3. 方向排序

### P0 — 先闭合可信性边界

1. `TASK-AUD-07B` 先由强统计 Reviewer 复核 TOST/序贯等价门；疑似 p-value 方向反转未解决前，
   不得实现 E3 inferential verdict。
2. 完成既有 C1/C2 的独立 Verifier/Reviewer。
3. 按已授权条件完成 C3，再独立验证与审查。
4. C5 不由低推理模型决定；到此必须停下请求 owner。
5. 运行 `TASK-RD-01`，让后续任务规格可被机器检查，减少弱模型越界。

### P1 — 8+ 小时开发主包

按依赖顺序执行 `TASK-RD-01` 至 `TASK-RD-17`。这些任务全部使用 synthetic/labeled fixtures，
不需要网络、密钥、真实 data、LLM API 或研究结果。RD-01/02/03/04/05/06/07/12 构成第一段连续
开发波次（Engineer 约 10.75–16 小时）；完整主包约 25.5–40 小时。独立 Verifier/Reviewer时间另计。

```text
RD-01 task-contract linter
├─ RD-17 trial-intent registry contract
├─ RD-02 validation manifest ──> RD-03 chronological oracle
│                            └─> RD-14 reproducibility capsule
├─ RD-04 gold schema ──> RD-05 deterministic sampler
│                    └─> RD-06 eval metrics ──> RD-07 eval report
│                                           ├─> RD-08 zero-LLM baseline
│                                           ├─> RD-11 provider replay
│                                           ├─> RD-14 reproducibility capsule
│                                           └─> RD-16 extraction uncertainty
├─ RD-09 cost kernel
├─ RD-10 momentum kernel
├─ RD-12 PIT-universe oracle
├─ RD-13 cross-sectional variation guard
└─ RD-15 rank-objective contract (strong decision precondition)
```

### P2 — 主包验收后才可研究

- 将现有 RES-08 拆为真实样本抽取、双人标注、分歧裁决和冻结四个 owner-participatory task；
  标注工件放在 tracked `evals/cases/`，只保存 accession/source hash/offset 与标签，不再放 gitignored
  `data/gold_set/`，也不重新分发 filing 原文。
- 用 RD-06/07/08/11 先比较零 LLM、规则、小模型，再决定是否值得模型蒸馏/量化或换模型。
- 将 RES-01 拆为纯特征定义、PIT 对齐、配置注册、探索性运行四步；RD-10 只是第一步。
- RES-02 继续 HOLD/重写：Kenneth-French 数据许可、发布日期/PIT 与 transport 尚未过 7 门；更重要的是
  原始 FF5/DFF 在同一月份对所有股票相同，无法直接贡献截面排序，必须先定义 stock-specific rolling
  beta 或 interaction，并通过 RD-13 的截面变化检查。
- RES-03 的 rank objective 先写精确 query-group/metric 合约，不允许弱模型在 lambdarank/rank_net
  之间自行选择。LightGBM 当前官方 ranking objective 是 `lambdarank` / `rank_xendcg`；连续收益需先
  冻结按月 relevance 分箱、ties、missing 与 group=query month 合约。见 RD-15。
- RD-09 基础成本内核通过后，可另开 no-trade/buffer-band 情景任务；参数化 bps 或 buffer 不得被
  叙述成实测市场冲击。
- 本地量化/蒸馏/QLoRA 不进入当前主包。必须先完成 gold/cached replay，再单独过模型权重许可、
  硬件/成本与 provider 边界 owner gate；只有相对零 LLM 和现有小模型有明确质量/成本收益才值得做。
- AUD-06、E3 scheduler/E2E、真实 forward launch 保持 strong-model + owner gate。

另外，`temperature=0` 不等于远程 API bit-deterministic。H6 对小模型部分应落在“原始响应 hash +
不可变 cache + parser/schema/version replay”上，而不是要求重新调用 provider 得到相同 bytes。

统计红线：ADR-010 当前写“两个 TOST p-value exceed 调整后 alpha”，而标准拒绝各自 null 的方向通常
是 p-value 小于 alpha。且固定 90% CI 与每次 look 的 alpha-spending 是否构成一致的序贯等价检验仍需
正式证明。因此已创建 AUD-07B，只允许强统计审查，不允许弱模型修公式。

## 4. 不计为完成的结果

- 只写计划或 TODO，没有可运行测试。
- 使用真实网络、真实 LLM 或真实研究数据来“证明”基础件工作。
- 修改 frozen prereg/config/ADR、ledger、results、data 或 E3 outcome surface。
- 把 cross-fit 称为 chronological OOS，或把 evaluator 通过称为产生 alpha。
- 将论文仓库的 license 误当作数据/权重许可。
- 一个 agent 同时担任同一 diff 的 Engineer 与独立 Verifier/Reviewer。
- 为凑够 8 小时扩大范围、重构无关模块或启动真实 trial。

## 5. 长时程调度规则

- Orchestrator 每次只下发一个写任务；文件边界不重叠时最多两个并行 worker。
- 每个任务使用任务文件本身作为唯一规格；低推理模型无权改变任务目标、文件白名单或研究方向。
- 每完成一个 Engineer task，必须由新上下文 Verifier 返回 PASS/FAIL/BLOCKED，再由 Reviewer
  APPROVE/REQUEST CHANGES/BLOCKED；最多两轮修复。
- 任何 owner gate、外部数据许可不清、真实 API/成本、frozen surface、ledger/result、E3 outcome 都是
  强制停止点。
- 进度只以文件、diff 和命令输出为准，不接受“基本完成”“应该可行”。

## 6. 启动条件

本路线本身不授权实现。启动前 owner 需明确指定：

1. 只执行 P0 收尾；或
2. 执行 P0 + P1 全部离线基础件；或
3. 仅选择某个 RD task。

真实数据、模型 API、trial ledger、研究运行与 E3 launch 均需要各自已有任务中的独立授权。

可直接用于下一次长时程启动的伪形式化 brief 见
`reports/milestone/2026-08-01-low-reasoning-wave-a-brief.md`。
