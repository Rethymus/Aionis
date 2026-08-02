# Aionis 战略复盘：是否跑偏 + 如何低成本覆盖七大主题

> 日期：2026-08-02
> 类型：研究方向与覆盖度战略复盘（研究建议，**非 ADR、非决策**）
> 状态：研究建议；不修改任何冻结 spec / pre-registration / ledger / config / 结果。
> 证据截止：仓库 HEAD；外部事实经 `WebFetch` 核实（qlib / FINSABER）或引自
> [`reports/audits/2026-07-31-quant-llm-research-audit.md`](audits/2026-07-31-quant-llm-research-audit.md)、
> [`docs/quant-selection-research.md`](../docs/quant-selection-research.md) v0.2、
> [`docs/frontier_positioning.md`](../docs/frontier_positioning.md)（均为 2026-07-27..31 一手调研）。
> 触发：2026-08-02 owner 提问——"判断项目是否跑偏，以及如何低成本覆盖
> '行情/宏观/基本面/新闻情绪/风险/回测/市场结构'的量化选股主题"。

## 标记与证据口径

- `[F]` Fact：由 ledger、源代码、真实日志、官方论文或官方仓库直接支持。
- `[I]` Inference：由一个或多个事实推导，可能被新证据推翻。
- `[H]` Hypothesis：尚未被本项目实证支持、但可设计实验检验。
- `[D]` Decision：本报告建议的决策；owner 接受前不是项目既定决策。

## 0. 一句话结论

**方向没有跑偏，但存在两处真实的"失调"。** 反泄漏纪律与 null-first 立场是稀缺且正确的
价值；问题不在"走错路"，而在 **(1) 目标叙事双轨未裁断**，与 **(2) 治理/审计机器的复杂度
已超过它所治理的研究产出**。七大主题中"行情/宏观/基本面"已覆盖或路径清晰，而
"新闻情绪/风险/回测净成本/市场结构"四项基本未建——但这并非"不知怎么做"，而是审计整改
占用了带宽，且 [`quant-selection-research.md`](../docs/quant-selection-research.md) v0.2 早已把
低成本复用蓝图设计完毕。

## 1. "是否跑偏"——分两层判断

### 1.1 方向层：没跑偏（证据强）

- `[F]` [`docs/00-vision.md`](../docs/00-vision.md) / [`docs/01-problem.md`](../docs/01-problem.md) /
  [`CLAUDE.md`](../CLAUDE.md) 三处一致：这是**可证伪、anti-leakage 的研究 harness**，null 即成果，
  明确非交易机器人、非认知系统。
- `[F]` B/C/D/E1 四条 differential 全为负、CI 跨零（[`docs/RESULTS.md`](../docs/RESULTS.md) §2）——
  **这正是预注册预期的结果**，不是失败。
- `[F]` 独立审计（2026-07-31，§11）结论："继续项目是合理的"；生态定位（§8.2）
  "evidence-first research harness"与前沿共识（Look-Ahead-Bench / Profit Mirage / FINSABER /
  Alpha Illusion 均指 LLM-trading alpha 多为泄漏 artifact）完全对齐。
- `[I]` 在"个人开发者、免费或许可合规数据、月频 PIT"约束下，**null-first + 可复现治理本身
  就是可发表贡献**（对照 Pérignon et al. 复现率有限）。方向是对的。

### 1.2 失调层：两处真实风险（证据中强）

**失调一：目标叙事双轨，未裁断。**

- `[F]` `00-vision` / `01-problem` = **窄 harness**（单 claim/phase，null 即终）。
- `[F]` `quant-selection-research.md` v0.2（2026-07-27）= **宽选股平台**（S0–S5，qlib 脚手架 +
  4 改造点，覆盖 price/fundamentals/event/relationship）。
- `[F]` 审计（2026-07-31）又把叙事**拉回窄 harness**（"not a validated strategy"）。
- `[I]` owner 2026-08-02 提问（"覆盖七大主题的量化选股"）本质是**站 v0.2 宽平台叙事**。两套
  叙事并存而无 owner 裁决 → 精力在"窄化审计"与"宽化蓝图"间摆动，是当前最大的隐性成本。

**失调二：治理复杂度 > 研究产出，进入边际收益递减。**

- `[F]` 已建成研究产出：4 条 null differential（且被重分类为 CV-proxy，非 chronological OOS）+
  一个 NO-GO 的 E3（[`state/current.md`](../state/current.md)）。
- `[F]` 已建成治理机器：`TASK-AUD-00` 含 ~15 子任务（AUD-01..07B）、`TASK-RD-00..17` 共 18 个
  RD 任务、双 opus 审计、ADR-010 的 TOST 方向修复 + Jennison-Turnbull 顺序构造（RCI 精确到
  99.44 / 97.64 / 95.00%）。
- `[I]` 近期 commit（`162702d` Slice 6 调度器、`38457c6` 静态站点、`7dede9b` dashboard v2）多为
  **工程抛光**，非研究推进。AUD-07B 发现的"TOST p 值方向反了"是 CRITICAL——但这恰恰说明：
  **在一组 4 条 null 上精修统计门到 4 位小数，不改变底层证据**（4 个负点估计、LLM 未进 headline、
  E3 仍需数年）。
- `[D]` 治理层已"足够好"。RCI 门数学有效（AUD-07B 已修）、purged CV 折生成器在位（RD-03
  chronological oracle 已完成）、reproducibility capsule 已落地（RD-14）。**继续精修剩余 RD 微
  任务的边际收益，低于把带宽转向研究覆盖。**

> 这不是"纪律过头"的批评——纪律是 null-first 项目的核心资产。而是**时机判断**：治理基础
> 设施已过阈值，应从"完善治理"切换到"用治理去产出研究"。

## 2. 七大主题覆盖度矩阵（逐项有据）

| 主题 | 当前覆盖 | 缺口 | 低成本复用路径（已验证 OSS） |
|---|---|---|---|
| **① 行情/价格** | `[F]` Tiingo+Alpaca 已接 `fetch_prices`（adj close，主备降级）；h=10/21/42 已扫 | corporate-action as-of 合同未冻结；**无退市股价格**（结构性，不可免费根除） | 保留现状；补 adj-close 合同 + 论文显式声明退市缺失（保守上界措辞，见 v0.2 §8.4） |
| **② 宏观** | `[F]` ALFRED vintage 已 PIT；C phase 的 surprise bundle 已做；FRED 观测适配器（C2 已落地） | B 的 macro 特征未进 frozen headline config | **已覆盖**，复用 `pandas-datareader` + ALFRED vintage 钉法 |
| **③ 基本面** | `[F]` EDGAR XBRL filed-date PIT（B phase，`edgartools`）；9 列 frozen baseline | 仅 9 列；缺 momentum/reversal/vol/liquidity/size 等量价特征；learner 用 MSE 非 rank objective | **RES-01/02/03 baseline ladder**（已规划但 HOLD）；rank objective 已由 RD-15 落地（lambdarank，bin_count=5） |
| **④ 新闻情绪** | `[F]` FinBERT ProsusAI reddit ingest 存在（前向收集，无回填）；FinGPT/FNSPID 已评估 | 未进 headline；无人工 gold set；LLM 参数记忆泄漏（Lopez-Lira 2025 证明即便 structural-only 仍残留） | **RD-04..07**（gold schema/sampler/metrics/report）+ RD-08 zero-LLM baseline（已完成）；E3 闭集 13D/8-K 抽取是唯一低泄漏入口 |
| **⑤ 风险** | `[F]` 几乎未建模（vol/beta/exposure 均无） | 无风险模型、无因子暴露分解、无波动结构 | 复用 **alphalens-reloaded + pyfolio-reloaded**（Apache）做 tearsheet；FF5 residual（=RES-02）作风险因子 |
| **⑥ 回测** | `[F]` `strategy_eval_run.py` gross（B/C + placebo/sanity）；DSR/SPA/MCS（`arch`） | **无净成本**：换手/next-open/滑点/借券/退市收益/容量全缺 | 复用 **FINSABER（Apache-2.0，已 WebFetch 核实）**：next-open 执行 + slippage + liquidity + LLM cost 四维，正是缺的那块 |
| **⑦ 市场结构** | `[F]` SIC peer momentum（D phase）；13D 关系事件 | 无 microstructure；无流动性/借券容量 | 复用 FF5 + liquidity factor；**RES-04..07 economic lens**（next-open/turnover/slippage/liquidity-borrow/delisting-capacity，已规划） |

**关键洞察**：缺口不是"不知道怎么做"——**v0.2 §6 轮子栈 + §9 S0–S5 分阶段已把每条映射到
具体 permissive OSS**（qlib 脚手架 / purgedcv / alphalens / pyfolio / FINSABER / arch / DoubleML）。
缺口是"审计整改占用了带宽，S0/S1 从未执行"。

## 3. 低成本覆盖路径（双轨，不污染历史）

核心原则：**复用优先 + 新研究线不污染 B/C/D/E1**（反泄漏铁律：新 config = 新 ledger row，
从不静默覆盖）。

### 轨道 A（近端、低成本、可发表）：把现有 null 做扎实并发表

1. `[D]` **chronological 再验证**：RD-03 chronological oracle 已完成——用它把 B/C/D/E1 从
   "CV-proxy"升级到"walk-forward"。**不重跑、不改 ledger**，只补一层更强证据，把 null 写得更硬。
2. `[D]` **诚实写 null**：4 条负 differential + CV-proxy 诚实措辞 + 治理方法（config-before-result
   ledger / PIT / purged CV / H6），定位为**可复现 null benchmark + 反泄漏方法论**（审计 §11 P2 后续第 2 条）。
3. `[I]` 成本低（数据/代码已就绪）；价值：把"未完成的宽平台"转化为"已完成的窄贡献"。

### 轨道 B（宽覆盖、中等成本、新预注册线）：执行 v0.2 的 S0→S1→S2

这是**真正覆盖七大主题**的路径，因 OSS 成熟而低成本：

1. `[D]` **S0 数据脊柱**：v0.2 §8 已实测可达——EDGAR PIT 基本面 + Fama-French + FRED/ALFRED +
   Tiingo 价格 + hanshof/pierrebrunelle PIT universe。**已 90% 就绪**（Aionis 现有 ingest 即此脊柱）。
2. `[D]` **fork qlib 当脚手架**（v0.2 §6 层 0，4 个手术点）：①edgartools `dump_bin` 钉 filed-date；
   ②ERL 挂申报日；③`DatasetH` 注入 purgedcv 折索引；④`RecordTemp` 链插 ControlGateRecord。
   **致命陷阱已记录**（`RobustZScoreNorm` 的 `fit_start/end` 必须钉折内训练段，否则静默泄漏）。
3. `[D]` **S1 price-only baseline**：建立"要 beat 的数"——当前**完全缺失**的基准（审计 §4.2 指出
   frozen 9 列 baseline 既缺量价特征、learner 又是 MSE 非 rank）。RD-15 rank objective 已为它铺路。
4. `[D]` **回测/风险/市场结构一次性补齐**：挂 FINSABER（净成本回测）+ alphalens/pyfolio
   （IC/tearsheet）+ FF5 residual（风险）。**这三项是"挂轮子"而非"造轮子"**，是七大主题中
   性价比最高的一击。
5. `[D]` **新闻情绪留到最后且最谨慎**：依赖 E3 闭集抽取 + RD-08 zero-LLM ablation + gold set
   （RD-04..07）。前沿共识（Profit Mirage 51–62% Sharpe 衰减、Alpha Illusion）强烈警告——
   **只作受控 ablation，不作主 alpha**。

> 两轨并行不冲突：轨道 A 用现有冻结面产出可发表 null；轨道 B 是**新预注册、新 config、新 ledger
> row**，天然满足"不静默改历史"。这避免了"窄 vs 宽"的伪二选一。

## 4. 给业主的决策（阻塞项）

当前最大成本不在工程，而在**目标叙事未定**导致精力分散。三个聚焦问题：

1. **目标裁断**：是 (A) 收敛为"窄 harness + 发表 null"（轨道 A 为主），还是 (B) 推进为
   "v0.2 七主题选股平台"（轨道 B 为主），还是 (A+B) 双轨？——**这是停摆治理微任务、释放带宽
   的前置条件。**
2. **治理止损线**：剩余 RD 微任务（RD-08 已 done、RD-15 已 done；剩探索性项）是否宣告"足够"，
   把带宽切到轨道 A 的 chronological 重验证 + 轨道 B 的 S0/S1？
3. **回测/风险覆盖优先级**：是否授权一条新预注册线，挂 FINSABER + alphalens/pyfolio + FF5，
   把"⑥回测净成本 + ⑤风险"作为轨道 B 的第一个 S1 切片？（七大主题里 ROI 最高、纯复用的一块。）

## 5. 适用边界与不越界声明

- `[F]` 本复盘**未运行任何 confirmatory/forward 脚本、未观察 E3 outcome、未改任何冻结面或
  ledger**——符合当前 STATISTICAL/E3 HOLD（[`state/handoff.md`](../state/handoff.md)）。
- `[I]` 本报告是研究建议；owner 未裁决前，不构成项目方向变更。轨道 B 的任何落地都是
  **新预注册 + 新 config + 新 ledger row**，绝不静默修改 B/C/D/E1。
- `[F]` "可缓解不可根除"的幸存者偏差（无免费 Russell/退市 PIT 数据）依然成立（v0.2 §8.4）；
  任何宽覆盖都是**抗幸存信号的保守上界**，非完全干净估计。

## 6. 引用

### 内部一手来源
- [`docs/00-vision.md`](../docs/00-vision.md) · [`docs/01-problem.md`](../docs/01-problem.md) ·
  [`docs/07-roadmap.md`](../docs/07-roadmap.md) — 项目目标与路线图。
- [`docs/quant-selection-research.md`](../docs/quant-selection-research.md) v0.2 — 横截面选股
  范围切片 + 轮子栈 + 数据解锁（本报告轨道 B 的蓝图来源）。
- [`docs/frontier_positioning.md`](../docs/frontier_positioning.md) — 前沿定位与下一 6 步。
- [`docs/RESULTS.md`](../docs/RESULTS.md) — 四条 null differential 证据边界。
- [`reports/audits/2026-07-31-quant-llm-research-audit.md`](audits/2026-07-31-quant-llm-research-audit.md) —
  独立研究审计（论文/GitHub/许可证/泄漏全景）。
- [`state/current.md`](../state/current.md) · [`state/handoff.md`](../state/handoff.md) ·
  [`state/backlog.md`](../state/backlog.md) — 当前运行状态与 HOLD 边界。

### 外部（本轮 WebFetch 核实）
- [microsoft/qlib](https://github.com/microsoft/qlib) — MIT；PIT-DB 2022-03 起；Alpha158/360；
  v0.9.0；46.9k★；2024-08 起 RD-Agent 集成。
- [waylonli/FINSABER](https://github.com/waylonli/FINSABER) — Apache-2.0；next-open 执行 +
  slippage + liquidity + LLM cost 四维泄漏 harness；集成 FinMem/FinAgent/FinCon/FinRL。

### 论文（引自审计 §14.2，不重复列全）
- Gu-Kelly-Xiu（Empirical Asset Pricing via ML）；Harvey-Liu-Zhu（Factor Zoo）；
  McLean-Pontiff（发表后衰减）；Lakens（TOST 等价检验）；Lopez-Lira et al. 2025（LLM 参数记忆泄漏）；
  Li et al. FINSABER（arXiv 2505.07078）；Look-Ahead-Bench / Profit Mirage / Alpha Illusion
  （LLM-trading alpha 泄漏 artifact 三联）。
