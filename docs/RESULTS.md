# Aionis 结果快照（RESULTS）— 当前证据边界

> 状态：**v0.1 · 2026-07-31 · factual snapshot**。本页只报告仓库现有
> ledger、审计和已记录历史材料；没有补算缺失指标。完整逐项对账见
> [`../reports/audits/claim-reconciliation.md`](../reports/audits/claim-reconciliation.md)。

## 0. 结论与术语

Aionis 是可证伪、PIT-aware、anti-leakage 的研究 harness，不是已验证的选股策略。
B/C/D/E1 的历史结果来自 shared-fold `PurgedGroupKFold(5, embargo=21)`：它们是
**purged cross-fitted/OOF differential**，不是 train 严格早于 test 的 chronological OOS，
也不是 live track record。purge/embargo 防止标签区间重叠，但候选训练补集可包含测试块之后的月份。

在 2016+、125 个月、588 个可解析 ticker、冻结九列基线和固定 MSE LightGBM 下，四个
treatment-minus-baseline 点估计均为负，没有观察到显著正增量。这个结论只适用于上述实现和样本：
它不证明市场有效、信息已完全定价、效应严格等价于零或策略可交易。

## 1. Phase A：LLM pilot，非个股 headline

仓库当前可核验的 scaled Phase A 记录是 53 个真实 FOMC-statement ERL、11 个 sector ETF + SPY；
XGBoost DA-lift 为 +5.5pp，cluster CI 为 [-4.2pp, +15.2pp]，约 43 个事件簇。CI 跨零，样本欠功率，
因此它只是 historical pilot，不是 B/C/D/E1 的月频个股 rank-IC claim，也不能证明 LLM 带来个股 alpha。

Phase A 口径必须分开报告：历史 extraction log 记录 prompt 41,689 + completion 8,636 =
50,325 tokens；`frontier_positioning.md` 报告的是约 72K 的**总研究 token 估算**。两者不是同一口径，
也没有账单 registry 对账。paid API cost、每个有效事件成本和人工复核成本均 **not tracked**。

## 2. B/C/D/E1 headline differential

全部 `n=125` 月，数值直接来自 `runs/ledger.jsonl` 的 `confirmatory:first` 行。

| Phase | treatment - baseline mean rank-IC | 95% paired HAC CI | DM p (MBB) | LLM feature | 证据判读 |
|---|---:|---:|---:|---|---|
| B filed-date vs end+lag | -0.0008003561696833403 | [-0.01057, +0.00897]（2026-08-05 补算） | 0.8695652173913043 | 否 | 未发现显著正增量；paired CI 跨零（补算见下注） |
| C surprise bundle | -0.006487473568317837 | [-0.019530768568940524, 0.006555821432304851] | 0.3553223388305847 | 否 | 未发现显著正增量；不满足事后 +/-0.015 严格等价 |
| D peer momentum + 13D | -0.0029798406036171702 | [-0.013714495699179569, 0.007754814491945227] | 0.5972013993003499 | 否 | 未发现显著正增量；区间在事后 +/-0.015 内 |
| E1 propagation beyond own shocks | -0.0027928949986939897 | [-0.01145659242594545, 0.005870802428557472] | 0.5332333833083458 | 否 | 未发现显著正增量；区间在事后 +/-0.015 内 |

Phase B 的 ledger 行 #28 只记录 `mean_ic_diff_state_minus_base`、`dm_stat`、`dm_p_mbb`、
`n_months`（无 paired `se_hac`/`ci_half`/`ci_lo`/`ci_hi`）。**2026-08-05 补算**：对 #28 save_run
产物 `ic_state`/`ic_base` 月度系列配对差分，复用 `aionis.eval.rank_ic.rank_ic_summary(maxlag=4)` 得
paired HAC 95% CI = [−0.01057, +0.00897]（ci_half 0.00977，se_hac 0.00499，t_hac −0.1605，p_hac
0.872，与 dm_p_mbb=0.870 同尾）；mean_diff **bit-identical** 于 #28（same-input 重算，非 rerun）。
**ledger 行 #28 未改（append-only）**；补算独立性局限与方法见
[`reports/audits/2026-08-05-phase-b-paired-ci-recompute.md`](../reports/audits/2026-08-05-phase-b-paired-ci-recompute.md)。C/D/E1 的 95% CI 均跨零。D/E1 的区间落在事后 +/-0.015 内只能作为
敏感性描述；项目未预注册 SESOI/TOST，非显著与 historical `ci_half` flag 都不是严格等价证明。

四条 headline 都是 **zero-LLM**：B 是 EDGAR 数值基本面时点，C 是宏观/盈利数值 surprise，
D 是 SIC peer momentum + 13D event flag，E1 是确定性传播。

## 3. Horizon sensitivity：exploratory

ledger #39 改变冻结的 confirmatory horizon `h=21`，只评估 `h=10` 和 `h=42`。它复用同一历史
数据和研究家族，不是 confirmatory rerun 或独立复制。下表为 differential 及其 95% HAC CI。

| h | Phase | n（月） | mean differential | 95% CI | DM p (MBB) |
|---:|---|---:|---:|---:|---:|
| 10 | B | 126 | 0.0008433987021642504 | [-0.007753139780905697, 0.009439937185234198] | 0.8555722138930535 |
| 10 | C | 126 | -0.0021182332777918314 | [-0.016175216864588848, 0.011938750309005186] | 0.777111444277861 |
| 10 | D | 126 | -0.0017889096684366723 | [-0.012938863859537856, 0.009361044522664511] | 0.7706146926536732 |
| 10 | E1 | 126 | 0.0016496284922720287 | [-0.008769789561647697, 0.012069046546191755] | 0.7781109445277361 |
| 42 | B | 124 | -0.004679723157718146 | [-0.015742525065532555, 0.006383078750096263] | 0.40729635182408797 |
| 42 | C | 124 | 0.0018597777350683653 | [-0.01209416889834892, 0.01581372436848565] | 0.8095952023988006 |
| 42 | D | 124 | -0.004800521999415512 | [-0.016364855980428628, 0.006763811981597604] | 0.41879060469765117 |
| 42 | E1 | 124 | -0.0019900106603546112 | [-0.010687854949497215, 0.006707833628787992] | 0.6286856571714143 |

所有八个探索性区间都跨零。这里只能说没有在该 sensitivity sweep 中观察到显著 differential，
不能说它“确认”或“复制”了 h=21 结果。

## 4. Strategy-return 次级透镜：exploratory、gross

ledger #38 只覆盖 B/C、placebo 和 sanity 五个策略，`n=125` 月；D/E1 没有 strategy row。

| 策略 | gross 年化 Sharpe | DSR p (`n_trials=20`) |
|---|---:|---:|
| B_arm_state | 0.42185547404242635 | 0.7432854842358372 |
| arm_base | 0.6205757339836699 | 0.503795982911974 |
| C_arm_macro | 0.24211861932063053 | 0.8812553123232412 |
| C_placebo | 0.5381237497077501 | 0.6264684423697051 |
| C_sanity | 0.6628862001996021 | 0.47354684493774823 |

SPA consistent p = 0.692；MCS 保留全部五个模型。结果是 **gross-of-costs**，没有 turnover、
next-open execution、slippage/impact、borrow、delisting return 或 capacity，因此不能解释为净成本收益、
可交易策略或资金部署证据。

## 5. 证据和适用边界

- `config_committed` 先于 result、H6 和 PIT contracts 是研究治理事实；它们不把 cross-fit 自动变成
  chronological OOS，也不替代经济等价检验。
- universe 是 2016+ 的 588/705 可解析 ticker；免费重建和未解析公司限制外部有效性。
- SIC 是当前 SEC snapshot，不是 historical vintage；13D self-report filtering 和历史分页仍有残余误差。
- E3 仍是 headline **NO-GO**：没有 scheduler、真实 E2E、shadow/headline result 或 live track record。
- 当前结论只覆盖 frozen universe/features/learner/validation。严格 chronological re-analysis、强基线、
  rank-aware learner、净成本回测和 LLM ablation 都是尚未执行的新研究问题。

## 6. Ledger 索引

| 结果 | ledger 行 | 类型 |
|---|---:|---|
| Phase B | #28 | `confirmatory:first` |
| Phase C | #30 | `confirmatory:first` |
| Phase D | #34 | `confirmatory:first` |
| Phase E1 | #37 | `confirmatory:first` |
| strategy lens | #38 | `exploratory` |
| h=10/42 sensitivity | #39 | `exploratory` |

历史 pre-registration/ADR/ledger 不因本次术语校正而改写；冲突的旧措辞只代表历史状态。
