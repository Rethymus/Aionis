# OSS 轮子调研综合 —— 最合适的轮子组合（2026-08-04）

> **触发**：owner "为什么这么多关联项没实现 + 先调研 GitHub + 给最合适的轮子，别再手搓"。
> **方法**：原计划 3 并行 sonnet web-agent → `[1210]` 5 连败（proxy 今日对子代理 spawn 整体不稳）→ **按 handoff 既定策略降级为 orchestrator 直接 opus web 调研**（WebFetch/WebSearch）。**复用**既有 catalog（不重查 CV/多重检验）。

> **⚠️ 勘误（2026-08-04 同日，交付后核查 `src/aionis/eval/` 发现）**：本报告对 mount①② 状态的判断有误，已修正：
> - **mount① tearsheet**：原说"待挂"——实际**已实现并已接线**（`tearsheet_adapter.py`，empyrical 全套 annual_return/vol/sharpe/sortino/max_drawdown/calmar/omega；`compute_risk_metrics`/`tearsheet_summary`/`cumulative_returns`；由 `scripts/track_b_mounts_run.py` 调用 + `test_tearsheet_adapter.py`）。
> - **mount② 净成本**：原说"无轮子，需建 empyrical+~50 行薄层"——实际 **`execution_costs.py` 已实现**（正是该方案：`next_session_open` 次日开盘 + `one_way_turnover` drift-adjusted 换手 + `linear_bps_slippage` bps 成本，非负校验）+ `test_execution_costs.py`，但**孤儿未接线**（全仓无调用方）。Gap 是**接线**（需 bps 参数 + 日频 open 数据），非造轮子。
> - 修正后结论：未实现项比原报告**更少**；§6 切片 #1（mount① adapter）**已完成应删**；真实 gap 见 §6 修正版。
> **许可证基线**：permissive ONLY（MIT/Apache/BSD）。硬排除：vectorbt、backtrader(GPL)、mlfinlab、nautilus(LGPL)、pypbo(AGPL)、Lean(C#)。
> **状态**：研究参考；未触冻结面/ledger/E3；OSS 能力以 GitHub/PyPI 核实为准。

---

## 1. 框架级候选（"覆盖最多未实现项"的问题）

| 框架 | 许可 | 活跃度（核实） | 解决的问题 | 覆盖 Aionis 哪些未实现项 | 裁决 |
|---|---|---|---|---|---|
| **microsoft/qlib** | MIT | **~47k★，活跃**（PIT-DB 2022-03；RD-Agent 2024-08；2066 commits）| 选股全管线：PIT DB + 双区域(US+CN) + Alpha158/360 特征 + walk-forward IC + LightGBM | 双区域数据、特征管线、walk-forward IC、CN 采集器（CSI300/500）| **LIBRARY 复用（选择性 import），不 fork、不整体采用** |
| stefan-jansen/zipline-reloaded | Apache-2.0 | 维护中（Python 3.x 移植）| 事件驱动回测 + 交易成本/slippage | 净成本回测（但 US-centric，CN 日历弱）| **AVOID**（过重、US-centric、与 Aionis 月频 L-S 需求不匹配）|
| OpenBB-Platform/OpenBB | MIT | 活跃 | 数据聚合 + 分析 + dashboard | 数据层——但 yfinance provider 被封 | **AVOID**（retail 导向，依赖被封源）|
| AI4Finance-Foundation/FinRL | MIT | 活跃 | 强化学习交易 | 无（Aionis 不是 RL）| **AVOID**（不匹配范式）|
| pmorissette/bt | MIT | ~3k★，"alpha"标签（历史遗留），CI 活跃 | 树形策略回测 + commission + bid/offer slippage | 净成本回测（commission/slippage ✓；turnover/next-open 非原生）| **备选**（见 §2）|
| vectorbt | BSD-3（base）/ Commons-Clause（pro） | 活跃 | 向量化高性能回测 | 净成本 | **AVOID**（CLAUDE.md 明令排除；pro 版 Commons Clause）|

**qlib 的决定性裁断（fork vs library vs avoid）：**
- **avoid**：不可能——它是唯一覆盖双区域 PIT + walk-forward IC + LightGBM 的 permissive 框架。
- **fork**：否——继承 47k★ 框架的维护负担，且 Aionis 的反泄漏脊柱（ledger/config-before-result/PurgedGroupKFold/H6）比 qlib 自带的 RollingWalkForwardCV 更严格；fork 会稀释这些。
- **整体采用**：否——DatasetH/ExpressionEngine/RD-Agent 全栈导入 = 加剧"治理复杂度 > 研究产出"失调。
- **✅ 选择性 LIBRARY 复用**：import qlib 的 **CN 数据采集器**（`cn_index/collector.py` CSI300/500 历史成分，从 csindex 公告重建 = PIT；baostock 价格采集器）+ 参考 **Alpha158** 因子定义。**保留 Aionis 自己的 harness 为脊柱**（PurgedGroupKFold、ledger、config-before-result）。冻结 config 里"scaffold = qlib dual-region mount"应理解为"挂载 qlib 的**数据层**，非采用其全管线"。

---

## 2. 净成本回测（mount② —— FINSABER 被 GPL 排除后的替代）

> 既有 catalog 把 FINSABER(Apache) 列为主轮子是**错的**：FINSABER 硬依赖 backtrader(GPLv3+)（PyPI Requires-Dist 已证）→ 装它就污染 dep 树。**净成本 mount 现在无轮子。**

| 候选 | 许可 | 覆盖 next-open / slippage / turnover / commission | 裁决 |
|---|---|---|---|
| **empyrical + ~50 行薄成本层** | Apache-2.0（已在 lock）| empyrical 给 Sharpe/max_dd/Sortino/Calmar；next-open + bps slippage + turnover 用标准公式 ~50 行 | **✅ 主推（reuse-first 正解）** |
| pmorissette/bt | MIT | commission ✓ / bid-offer slippage ✓ / turnover 不原生 / next-open 不原生 | 备选（需更富成本模型时升级）|
| zipline-reloaded | Apache | 全事件驱动 + 成本 | AVOID（过重、US-centric）|
| quantstats | MIT | 仅报告/指标，无回测 | 仅报告层 |

**裁断**：Aionis 的净成本需求是**月频 top-quantile L-S**，不是高频事件驱动。净成本 = gross Sharpe(empyrical) − slippage(bps)×turnover − commission×trades，可直接在月度 panel 上算。**这不是重造轮子**——empyrical 是指标轮子，~50 行成本层是 FINSABER 论文模型（next-open + bps slippage + 流动性上限）的标准复现，比引入 bt/zipline 整个回测器更轻、更少泄漏面。若日后需 volume-weighted slippage + 流动性上限，升级到 **bt(MIT)**。

---

## 3. 风险 Tearsheet（mount① —— "待挂"）

alphalens-reloaded + pyfolio-reloaded（Apache，维护中）。**但 alphalens 期望日频 factor+prices panel；Aionis 是月频 IC——mismatch。**

**裁断**：现在挂 **empyrical-only 薄 adapter**（max_drawdown/Sharpe/Sortino/Calmar——即 wheel-mount-design-pack §挂接① 的 APPROVED 方案）；完整 alphalens tearsheet **延后**到有日频 factor panel 时。不要为月频管线硬塞日频 tearsheet。

---

## 4. A 股 / 双区域数据（Track C S0）

汇总自既有 intake 文档（`data-intake-ashare-price-baostock.md` + `data-intake-cn-macro.md` + `ashare-fundamentals-source.md` + qlib POC）：

| 数据 | 最合适的轮子 | 许可 | 备注 |
|---|---|---|---|
| A 股价格 | **baostock**（已接，`ingest/ashare_price.py` committed）| MIT | G3 raw+冻结因子策略 |
| CSI300/500 PIT 成分 | **qlib `cn_index/collector.py`** 或 `index-constitution` | MIT | 从 csindex 公告重建 = PIT，含退市 |
| CN 宏观 headline | **ALFRED/OECD**（`macro_dff.py` 模式复用）| FRED 公开 | vintage-safe |
| CN 宏观 exploratory | `mbk-dev/nbsc`（NBS latest-only）| 待验 | G3-fail → snapshot+exploratory |
| A 股交易日历 | `pandas-market-calendars` XSHG/XSHE | MIT | 已在 lock |
| **A 股 filed-date 基本面** | **❌ 无 permissive 轮子存在** | — | baostock=G3-fail(期末键)；cninfo=exploratory(反爬+商业授权)；Tushare=付费。**结构性数据可得性 gap，非手搓失败** → 修订 #47 已正确降为 exploratory |

---

## 5. 最终推荐：三桶分类（直接回答"为什么没实现 + 别手搓"）

未实现项分三类，每类处置不同：

### 桶 A —— 有轮子，**现在就采用**（停止手搓）
| 未实现项 | 采用的轮子 | 动作 |
|---|---|---|
| CSI300 PIT 成分 | qlib `cn_index/collector.py` (MIT) | import 复用，不自建成分重建 |
| 月频风险指标（Sharpe/dd/Sortino/Calmar）| empyrical (Apache, 已在 lock) | 挂 mount① 薄 adapter（替代手算）|
| CV / 多重检验 | purgedcv + arch.bootstrap (已用) | 无需动作 |
| CN 宏观 headline | ALFRED vintage（复用 `macro_dff.py`）| 镜像既有 fetcher |

### 桶 B —— 轮子 + 薄胶水（非重造）
| 未实现项 | 方案 | 为什么不算手搓 |
|---|---|---|
| 净成本回测（mount②）| empyrical + ~50 行成本层 | empyrical=指标轮子；成本层=FINSABER 论文模型标准复现，比引回测器框架更轻 |
| 双区域数据脚手架 | qlib **数据层**（采集器）library-import | 复用 qlib CN 采集器 + Alpha158 参考；脊柱仍是 Aionis harness |

### 桶 C —— **无 permissive 轮子**（必须自建 or 保持 exploratory，诚实）
| 未实现项 | 现实 | 处置 |
|---|---|---|
| A 股 filed-date PIT 基本面（headline）| 无 MIT/Apache 源给 filed-date 键 A 股基本面 | 修订 #47 降为 exploratory 是**正确**的；headline 用 US 基本面 + A 股价格/宏观 |

---

## 6. 立即可执行的"采用轮子"切片（按优先级，⚠️ 勘误后修正）

1. ~~**mount① empyrical 薄 adapter**~~ —— **已完成**（`tearsheet_adapter.py`，已接线 `track_b_mounts_run.py`）。删除。
2. **mount② 净成本接线**（`execution_costs.py` 已存在但孤儿）—— 把 `next_session_open` / `one_way_turnover` / `linear_bps_slippage` 接入 mounts runner 或专用 net-cost runner。**M 任务，需 owner 定 bps 参数 + 确认日频 open 数据可得**（当前 mounts runner 只用月度收益；net-cost 需日频 open 才能算 next-open 执行）。
3. **CSI300 PIT 成分 intake** —— 复用 qlib `cn_index/collector.py`（MIT）。**S-M 任务，需 owner 定是否引 qlib 为依赖**（cp313 wheel 门 → 3.11 隔离 venv，或仅复用采集器脚本逻辑）。
4. **qlib CN 采集器 library-import** —— 取代手搓 A 股数据采集。**M 任务，同上 qlib 依赖决策。**

> **诚实结论（勘误后）**：真正"零 owner 决策依赖"的切片已基本耗尽——mount① 已完成、baostock 适配器已完成、排名契约/oos_scores 已完成。其余真实 gap（mount② 接线 / CSI300 / qlib 引入 / S0 真实数据获取）**都需要 owner 决策**（bps 参数 / qlib 依赖 / 日频数据 / 真实数据拉取授权）。继续 loop 只会在外围打转。

**不做的**：fork qlib；整体采用 zipline/bt/vectorbt；为月频管线硬挂 alphalens 日频 tearsheet；为 A 股 headline 基本面找不存在的 permissive 源。

---

## 引用

- GitHub 核实：[microsoft/qlib](https://github.com/microsoft/qlib)（MIT, 47k★）、[pmorissette/bt](https://github.com/pmorissette/bt)（MIT）、[stefan-jansen/pyfolio-reloaded](https://github.com/stefan-jansen/pyfolio-reloaded)（Apache）、[bt 文档](https://pmorissette.github.io/bt/)
- 内部既有：`2026-08-02-reuse-catalog-v2.md`、`2026-08-02-qlib-fork-vs-library-poc.md`、`2026-08-02-wheel-mount-design-pack.md`、`2026-08-03-citation-integrity-audit.md`、`docs/data-intake-ashare-price-baostock.md`、`docs/data-intake-cn-macro.md`
- 排除证据：FINSABER→backtrader GPL 硬依赖（PyPI Requires-Dist，见记忆 `aionis-finsaber-backtrader-gpl`）
