# Aionis 结果快照（RESULTS）— 当前证据边界

> 状态：**v0.2 · 2026-10-07 · factual snapshot**（v0.1 · 2026-07-31）。本页只报告仓库现有
> ledger、审计和已记录历史材料；没有补算缺失指标。v0.2 增量：§4c Track B 七主题与
> 强基线（面板逐位）、§4d PBO/CSCV 过拟合诊断（exploratory）、§5 E3 边界措辞更新
> （工程就绪+影子窗，headline NO-GO 不变）、§6 索引补行；外部验证文献补注见 §0。
> 完整逐项对账见
> [`../reports/audits/claim-reconciliation.md`](../reports/audits/claim-reconciliation.md)。

## 0. 结论与术语

Aionis 是可证伪、PIT-aware、anti-leakage 的研究 harness，不是已验证的选股策略。
B/C/D/E1 的历史结果来自 shared-fold `PurgedGroupKFold(5, embargo=21)`：它们是
**purged cross-fitted/OOF differential**，不是 train 严格早于 test 的 chronological OOS，
也不是 live track record。purge/embargo 防止标签区间重叠，但候选训练补集可包含测试块之后的月份。

外部参照（2026-10 补注）：独立研究对大盘股截面可达成 IC 的实证上界亦接近零
（SSRN 6742700, 2025）；Jensen-Kelly-Pedersen（*Journal of Finance*, 2023）的复制率
~82%、收敛于 ~13 主题界定了因子研究多重检验的现实区间——本项目的"紧 CI null"落在这两支
文献的预期之内，而非 harness 失效的信号。

**Track C 联合 confirmatory（ledger #49，2026-08-05 climax）**是项目首条 chronological
confirmatory OOS：双区域（US S&P500 + CN CSI300）联合 walk-forward，41 特征 + regime 条件化，
combined rank-IC = **−0.0088**（null，p_hac=0.484，n=71 月）；J-T look-1（n=60，RCI 99.44%）
= **NOT_EQUIVALENT**（RCI [−0.051,+0.027] 宽于 ±0.010 SESOI = look-1 OBF 欠功率，非效应信号；
look-2/3 需 E3 forward-live）。H6 双跑 bit-identical PASS。详见
[`archive/docs/methods-and-results-draft.md`](../archive/docs/methods-and-results-draft.md) §5（v1.0-draft；已随 2026-08-15 发表线废除归档）。

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

## 4b. R1-full decile 单调性透镜：display 派生（无账本行）

P1-6（2026-09-02 裁决 GO）把冻结 OOS 截面的分数十等分（D1=最低分…D10=最高分），
桶收益走与训练标签同一冻结函数 `forward_returns`（close[t+21]/close[t]−1）作用于同一
研究价格面板。**这是纯展示派生读数，没有账本行、不构成 confirmatory 主张**；面板
`ic_deciles.json`（155 截面：US/CN）逐行公示，`/atlas` 第五区块渲染，未实现月诚实 null。

- 已实现：US 66 月、CN 66 月（均 2021-01-29 → 2026-06-30）。
- 最新 US 读数 **非单调**：D1 +4.48% 为最高、D10 −0.81%，D10−D1 = −5.29%——与
  headline NULL 一致（噪声截面不欠任何形状）。
- 口径勘误（2026-09-04）：导出器曾把桶收益错取自 [t+21, t+42] 窗口（偏移一个
  horizon），且 CN 快照网格的月度索引使位置式 +21 守卫错误截断 CN 已实现面
  （45 月）；已修正为"行 t 即标签窗口 + 值规则守卫"并加确定性回归测试钉死。
  修正前后读数均非单调，headline 结论不受影响（该面板自始无账本行）。

## 4c. Track B 七主题平台与强基线：面板逐位（v0.2 增补）

以下读数逐位来自 committed 面板 `web/src/data/aionis/evidence.json`（裁决榜
`/verdicts` 同源渲染），均为 **chron./explor. 或 CV-proxy 级**，无新的
confirmatory 账本行——不是本页 §2 那族预注册 confirmatory 主张的成员。

| 检验 | 点估计 | 95% CI | p | n（月） | 证据等级 |
|---|---:|---|---:|---:|---|
| Track B treatment（A 股七主题平台） | +0.0055 | [-0.021, +0.033] | 0.69 | 125 | chron./explor. |
| Track B treatment − baseline 差分 | +0.0076 | [-0.004, +0.020] | 0.22 | 125 | chron./explor. |
| 强基线 FF5（横截面五因子） | +0.0106 | —（无 CI） | — | 125 | CV-proxy |
| 强基线 RANK（rank-aware 学习器） | +0.0154 | —（无 CI） | 0.04 | 125 | CV-proxy |

判读纪律：两行 Track B 均跨零——七主题平台未显示超出基线的增量（与 §2 四相
NULL 同向）。强基线两行是 RES-01..03 基线族 ladder 的中间读数，**仅点估计无 CI**：
RANK 基线 p=0.04 是未做多重性校正的裸 p，且基线不是"treatment 增量"主张——
不得当作"找到了显著因子"引用；其完整预注册路径见
[`../tasks/active/TASK-RES-03-baseline-rank.md`](../tasks/active/TASK-RES-03-baseline-rank.md)。

## 4d. PBO / CSCV 过拟合诊断：exploratory（v0.2 增补，ledger #59）

对 8 个冻结主张臂（B/C/D/E1 × {treatment, base}，125 个月度 OOS rank-IC，逐位读自
`runs/results/<sig>/ic_*.parquet`）运行 CSCV 概率回测过拟合估计
（`purgedcv 0.1.2 probability_of_backtest_overfitting`，n_splits=16）：

**PBO = 0.872**（12,870 个 CSCV 组合）。读法：若有人在样本内从 8 臂中挑"最优"，
该选择在样本外落入中位以下的概率为 87%——不存在任何稳定的选拔边际，与 §2 的
四相 NULL 差分完全一致。低 PBO 才会指示"有值得主张的稳定样本内赢家"。

三条诚实告示（与结果一同入册 `reports/exploratory/pbo-diagnostic.json`）：
① n_configs=8 属小试验域，CSCV/PBO 估计器自身噪声大（Witzany 2021, *Risks*；
Arian et al. 2024, SSRN 4686376）——这是诊断，不是门；② 逐期表现映射为月度 OOS
rank-IC（本项目的主张量纲），非交易收益；③ 输入序列已是 purged-CV 的 OOS 产物，
CSCV 块切分复用已清洗点。**EXPLORATORY——不是 claim，不是 gate。**

同族补强（同日，ledger 探索行）：以 Bailey-López de Prado (2012) 最短成绩单长度
（`purgedcv.min_track_record_length`）对同一已实现序列（66 个非空月，年化 IC-IR
= −0.21）反推"多长的 track record 才能让 PSR(0)≥95%"——**minTRL = ∞**：观测
IC-IR 低于目标 0，任何有限时长都不足以把该序列与零区分开。这与 J-T look 分析的
"~36+ 年才能宣告等价"从第二个估计器独立佐证：诚实的交付物就是 null。
payload：`reports/exploratory/mintrl-diagnostic.json`。

**LLM 记忆探针（同族，探索行）**：以 Glasserman-Lin (arXiv 2309.17322) 的两种污染
形态与 Didisheim 等（Econ. Letters 2025）的记忆测量法为方法锚，对 extraction 池
（glm-4-flash / Qwen2.5-7B / Qwen3-Next-80B）提 4 个**截止前**（≤2023-02）"该月
S&P 500 最大月收益成分股是谁"的 JSON 模式问句（温度 0.1，地面真值=展示面板月末
收盘收益）。结果：**top-1 回忆 0 命中**——siliconflow 4/4 自信作答但全错（恰为
"事后叙事"型污染的形态学证据：模型会编造貌似合理的历史赢家）；glm 2 答全错、
2 空；modelscope 全程 HTTP 400（上游模型目录变化，计 no_answer 非拒答）。
严格 top-1 口径的告示：低命中**不能**证明无记忆（更宽召回口径未测）；且本池为
刻意的廉价小模型档（token 纪律），前沿模型的记忆面（Didisheim 文档化对象）不在
本探针范围。对 E3 的语境价值：本项目 frozen OOS 全程 zero-LLM 特征 + 该池 top-1
无记忆的实证，双保险地支撑"LLM 不进冻结 OOS"的纪律。payload：
`reports/exploratory/llm-memory-probe.json`。

## 5. 证据和适用边界

- `config_committed` 先于 result、H6 和 PIT contracts 是研究治理事实；它们不把 cross-fit 自动变成
  chronological OOS，也不替代经济等价检验。
- universe 是 2016+ 的 588/705 可解析 ticker；免费重建和未解析公司限制外部有效性。
- SIC 是当前 SEC snapshot，不是 historical vintage；13D self-report filtering 和历史分页仍有残余误差。
- E3 headline 仍 **NO-GO**：没有 shadow/headline 结果、没有 live track record。v0.2
  措辞更新：工程已就绪（`scripts/forward_score.py` / `forward_commit.py` /
  `e3_forward_trigger.py` 在库），前向影子窗已启动——10-01 首窗完成（月报五步核验
  PASS，见 [`../reports/audits/2026-10-06-evening-lane-monthly-review.md`](../reports/audits/2026-10-06-evening-lane-monthly-review.md)
  专节），10-31 为第二窗；点火（headline 评估开始）是业主 GO 门（ADR-010）。
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
| **Track C 联合 confirmatory（climax）** | **#49** | **`confirmatory:first`** |
| PBO/CSCV 过拟合诊断 | #59 | `exploratory` |

Track B 七主题与强基线读数（§4c）来源于 committed 面板 `evidence.json` 而非独立
confirmatory 账本行——见该节的证据等级标注。

历史 pre-registration/ADR/ledger 不因本次术语校正而改写；冲突的旧措辞只代表历史状态。
