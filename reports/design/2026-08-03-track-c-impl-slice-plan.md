# Track C 实施切片计划（executes **post-freeze**）

> 日期：2026-08-03
> 类型：实施切片计划（**执行门槛:owner `config_committed` 冻结后**；每片 = 新预注册修订（若改 config）+ 新 ledger 行 + 测试 + Verifier/Reviewer 门）。
> 约束：绝不污染 B/C/D/E1 + Track B 冻结面；config_committed BEFORE result；H6 确定性；reuse-first。
> 关联：[`docs/track-c-preregistration.md`](../../docs/track-c-preregistration.md)（冻结候选）、[`2026-08-03-qlib-dualregion-poc.md`](../2026-08-03-qlib-dualregion-poc.md)（gate 1/2/3）。

## 0. 执行门槛（不可越过）

- **全部切片在 owner 写 Track C `config_committed` ledger 行之后才执行**（CLAUDE.md：config 先于 result）。
- 每片落地 = 新 ledger 行（绝不静默覆盖）；frozen prereg/ADR/config 不改。
- agents 7/7 `[1210]` 死 → 由 orchestrator 直接执行（opus 设计 + sonnet 机械；当前 sonnet 也 [1210]，故 opus 直接）。

## 切片（依赖序）

### S0 — A 股数据脊柱（**L，关键路径**）
- cninfo ingest：复用 `rollysys/use_cninfo`（MIT）fetch + Aionis 自建 PDF 数值解析（PyMuPDF MIT），filed-date PIT（`align_on="filed"`，同美股 EDGAR 范式）+ snapshot+sha256（G4）+ ≥2s 礼貌（G7）。
- A 股价格：baostock（MIT，`tradestatus`+`adjustflag`+`query_all_stock` 退市）或 qlib+AKShare 采集器（MIT `83d089b`，补 survivorship）。
- A 股成分：`index-constitution`（MIT，CSI 300/500 PIT）。
- 宏观：ALFRED/OECD CN 序列（vintage）+ NBS-only（`mbk-dev/nbsc`，snapshot+exploratory）。
- **门**：7-gate intake 每源落表（G1 rollysys MIT ✅；cninfo ToS 待核 → 可能 G6 exploratory）。
- **不可越**：不跑 rank-IC、不写 headline ledger。

### S1 — 特征构造（M）
- 复用 `features/selection_panel.py` + `fundamentals.py:pit_align` 范式，构造 §10.1 的 54 per-stock 列（US 复用 Track B 23 + A 股对称 25 + 宏观 6）。
- A 股特有：`limit_up_down_distance`、`suspension_flag`、申万行业映射。
- **门**：每特征 PIT 对齐断言（`test_alignment.py` 范式）；RD-13 截面变异 guard。

### S2 — 联合 chronological walk-forward CV（M）
- 复用 `eval/cv.py:purged_walk_forward_splits` + `assert_chronological_split`（RD-03）。
- **联合面板**：双区域按各自交易日历对齐，月末日截面，embargo=21（按区域交易日）。
- **门**：chronological oracle（train.max < test.min，双区域各自）。

### S3 — regime_state 三层 PIT 复合（M）
- meso：美股 SIC-peer（Phase D 复用）+ A 股申万动量。
- macro：5 线（market-driver §3，VIX/credit/term/DFF-surprise + EPU exploratory）。
- global：`diebold-yilmaz`/`connectedness`（PyPI）US↔CN total spillover，滚动 as-of。
- **TACO as-of 固定窗 σ-归一化**（不追溯重算；防批判者 M1 regime 泄漏）。
- **门**：regime PIT 性测试（as-of 固定窗断言）。

### S4 — learner + 交互项（S）
- LightGBM frozen（同全家族）+ `lambdarank`（RD-15，`ranking_contract.py`）。
- 交互项 `score × regime_state`（单预指定，预算 1，§1/§8）。
- **门**：H6 bit-identical 重跑断言。

### S5 — rank-IC + J-T 等价门 + 多重检验（S）
- 复用 `eval/rank_ic.py` + `sesoi_gate.py`（ADR-010 J-T）+ `multiple_testing.py`（DSR/haircut/SPA，n_trials=30）。
- **门**：应用于交互项差分序列；RCIₖ ⊂ [−0.010,+0.010] → 等价裁决。

### S6 — 净成本回测（exploratory，S）
- 复用 FINSABER（Apache，挂接②）：next-open + slippage + liquidity + LLM-cost。
- A 股特有：T+1 + 涨跌停 fill-ability + 停牌。
- **非 confirmatory**；不进 headline 裁决。

### S7 — 入手/跑路仪表盘（非主张，S）
- regime_state → 0-100 温度 → 决策辅助显示；"探索性/非投资建议" banner；轻量 PIT 合同。
- **不作 claim、不进 ledger 确认行**（§1.2）。

### S8 — forward-live（远期，L）
- Track C forward（commit-reveal，复用 E3 架构）；需 owner GO + AUD-06 类 readiness 门。
- 仅在 S0-S7 headline 跑通 + owner 授权后。

## 切片依赖与门

```
S0 (数据) → S1 (特征) → S2 (CV) → S3 (regime) → S4 (learner+交互) → S5 (rank-IC+J-T) → S6 (净成本) → S7 (仪表盘)
                                                                                              ↘ S8 (forward, 远期)
```
每片：Engineer 实现 + 测试 → 独立 Verifier PASS → 独立 Reviewer APPROVE → 原子提交（显式文件列表，新 ledger 行）。

## 估算（执行态，post-freeze）
S0（L，cninfo 解析最重）→ S1-S3（M 各）→ S4-S7（S 各）→ S8（L 远期）。总量 ≈ Track B 量级（POC 文档估 58-68h US-only；双区域 + cninfo 解析 + spillover ≈ 1.5-2×）。

## 不越界声明
- 本计划是 **post-freeze 执行蓝图**；当前不执行任何切片、不写代码、不写 ledger、不触冻结面。
- 待 owner `config_committed` 冻结 + per-slice 授权。
