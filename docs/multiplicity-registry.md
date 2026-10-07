# 全局多重性注册表（Multiplicity Registry）— 试验普查与记账纪律

> 状态：**v0.1 · 2026-10-08 · 审计轮 221 §A.6 的文档半边**。目的：ADR-008 "broaden
> the null family"（RES-01..10 强基线族）将增加预注册主张数——本页把"到目前为
> 止检验过什么"一次盘清，让 DSR 的 `n_trials`、审稿人的"你试了多少次"和未来
> 主张的多重性预算有一份可引用的普查基线。数据来源：`runs/ledger.jsonl`
>（61 行，逐行可溯）+ committed 面板 `evidence.json`。

## 1. Confirmatory 主张（预注册、计入主张族）

| # | 主张 | 账本行 | 判定 | 备注 |
|---|---|---|---|---|
| 1 | Phase B：基本面时点（filed vs 期末+滞后）差分 | #28 | NULL | shared-fold CV-proxy |
| 2 | Phase C：世界状态 surprise 组差分 | #30 | NULL | 同上 |
| 3 | Phase D：关系组（SIC 同业+13D）差分 | #34 | NULL | 同上 |
| 4 | Phase E1：跨公司传播差分 | #37 | NULL | 同上 |
| 5 | Track C：双区域联合时序 confirmatory OOS | #49 | NULL | 首条 chronological |

**主张族规模（DSR n_trials 的 confirmatory 口径）：5。**

## 2. Chron./explor. 主张（有预注册/冻结但证据等级低一档）

| # | 检验 | 来源 | 判定 |
|---|---|---|---|
| 6 | Track B treatment（A 股七主题平台） | evidence.json #5（prereg：`docs/track-b-preregistration.md`） | NULL（CI 跨零） |
| 7 | Track B treatment−baseline 差分 | evidence.json #6 | NULL |
| 8-11 | Track C 条件化变体（conditional beta / 3-layer / asymmetric-35 / asymmetric-41） | evidence.json #8/9/13/14 | 均跨零；同一 Track C 家族的预先指定变体，**不另计独立主张**（族内 4 变体，多重性预算按 1 族计） |

## 3. 强基线读数（CV-proxy、点估计、无独立主张）

| # | 基线 | 来源 | 备注 |
|---|---|---|---|
| 12 | FF5 横截面五因子 | evidence.json #10 | RES-02 中间产物 |
| 13 | RANK rank-aware 学习器 | evidence.json #11 | 裸 p=0.04，未校正、无 CI——**不得当发现引用** |

## 4. Exploratory 诊断（账本在册，非主张）

| # | 诊断 | 账本行 | 结果 |
|---|---|---|---|
| 14 | 策略收益次级透镜（B/C/placebo/sanity 5 策略，DSR n_trials=20） | #31/32/38 | 全不显著（DSR/SPA） |
| 15 | 视界扫描 h=10/42（4 相 × 2 视界 = 8 区间） | #36/39 | 全跨零 |
| 16 | PBO/CSCV 过拟合诊断（8 臂） | #59 | PBO=0.872 |
| 17 | minTRL 功效诊断 | #60 | ∞ |
| 18 | 数据快照基线 | #61 | 非统计诊断（完整性锚点） |

## 5. 记账纪律（多重性预算声明）

1. **DSR 惩罚数取口径最大者**：策略透镜的 `n_trials=20` 是迄今最大的显式
   试验族口径；主张族规模为 5。当 RES-01..10 强基线族落地时，**每一条新预注册
   主张入账本页 §1/§2，主张族计数随之增长，DSR n_trials 同步更新**——由
   `strategy_eval_run.py` 的 `n_trials` 参数与本页共同维护。
2. **变体归族**：同一预注册内指定的变体（如 Track C 条件化交互，多重性预算=1）
   记 1 族；未预注册的事后切分**禁止**入 confirmatory（只能入 §4 且如实标注）。
3. 本页只在**新账本行落位时**由该轮次同步更新（与 RESULTS.md 快照同属
   "confirmatory 结果变更即刷"纪律）。
4. 普查核对基线：2026-10-08，账本 61 行（19 无事件标记的早期行 + 16
   config_committed + 6 data_ingest + 2 prereg_reframe + 1 freeze + 1
   universe_crosscheck 不计入试验；试验类=5 confirmatory + 8 exploratory）。

## 6. 与文献口径的对照

Harvey-Liu-Zhu (2016) 建议因子发现的 t 门槛 ≥3.0（对应数百次检验的历史）；
Jensen-Kelly-Pedersen (JoF 2023) 估计因子动物园复制率 ~82%、有效主题 ~13——
本仓库 5 主张 + 1 族的规模远小于该口径，且**全部预注册**（trial 数在检验前
锁定，非数据挖掘后清点）。引用见 `docs/RESULTS.md` §0。
