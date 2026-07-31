# Aionis 量化选股与小模型 LLM 研究审计

> 日期：2026-07-31  
> 类型：研究方向、实证强度、时间外推、LLM 与开源生态联合审计  
> 状态：研究建议，非 ADR；不修改任何冻结 spec、pre-registration、ledger 或实验结果  
> 证据截止：仓库 HEAD `87af583`，分支 `feat/e3-forward-ledger`；外部资料截至
> 2026-07-31 的论文、官方文档与默认分支快照

## 标记与证据口径

- `[F]` Fact：由 ledger、源代码、真实日志、官方论文或官方仓库直接支持的事实。
- `[I]` Inference：由一个或多个事实推导出的解释，可能被新证据推翻。
- `[H]` Hypothesis：尚未得到本项目实证支持、但可以设计实验检验的假设。
- `[D]` Decision：本报告建议的决策；在进入 ADR 或 owner 接受前，不是项目既定决策。

证据等级沿用 [WORKFLOW.md](../../WORKFLOW.md) §4：A = 原始论文、官方文档、源代码、
真实数据或 ledger；B = 高质量复现、系统综述或权威报告；C = 工程复盘；D = 个人内容。
本文的核心结论不依赖 D 级来源。GitHub 星数只用于描述生态关注度，不作为有效性证据。

## 1. 执行摘要

- [F] Aionis 已完成 B/C/D/E1 四条、每条 125 个月的月频横截面 differential
  rank-IC 研究；四个点估计均为负、CI 或 DM 检验均没有显示处理臂相对基线的显著正增量。
- [F] Phase B 的 ledger **没有记录 differential 的 HAC SE 或 CI**，只有两条单臂 CV-proxy
  CI、differential 均值与 DM p 值。因此 B 不能与 C/D/E1 一样被审计为“differential
  CI 半宽小于 0.015”。
- [F] C 的 95% CI 为 `[-0.01953, 0.00656]`。即使事后把 `[-0.015, 0.015]` 当作
  等价区间，C 也未完全落入其中；项目当前“CI 跨零且半宽 < 0.015”的规则不是严格等价检验。
- [F] B/C/D/E1 全部是 shared-fold `PurgedGroupKFold` 的 cross-fitted/CV-proxy，**不是**
  train 严格早于 test 的 chronological OOS。purge 与 embargo 防标签窗口重叠，但训练补集可含
  测试块之后的月份。
- [F] LLM 没有进入 B/C/D/E1 四条 headline。Phase A 是历史 sector-ETF pilot；E1 为
  zero-LLM 结构传播；E3 才计划让 GLM 参与闭集 13D/8-K 因果边抽取。
- [F] E3 的 commit-reveal 原语和部分不变量已经实现，但 scheduler、真实 E2E 与完整 I1-I9
  gate 尚未完成；当前 runner 仍不能形成可信 live prediction。
- [F] 本审计当场运行标准命令 `uv run pytest -q`，在收集
  `tests/test_dashboard_curve.py` 时因 `ModuleNotFoundError: No module named 'dashboard'` 退出码 2。
  因而 [state/current.md](../../state/current.md) 的“576 tests green”不是当前干净命令可复现状态。
- [I] 项目的主要现有价值是 evidence-first、PIT-aware、可证伪的研究 harness，而不是已获验证的
  选股策略。研究治理和可复现性价值高；统计时间外推、实时链路、LLM 增量和可交易性证据较弱。
- [D] 继续项目是合理的，但应先修复术语、等价推断、chronological baseline、E3 live 链路与
  provider/data contract。可以按需增加彼此隔离的开发/验证 agent；不得把多 agent 推理、更多因子或
  更复杂叙事直接加入选股信号与未登记试验族。

## 2. 研究问题

### 2.1 主问题

[H] 在个人开发者、低预算、免费或许可合规数据、月频 S&P 500 PIT universe 的约束下，
“结构化数值基线 + 小模型 LLM 的闭集事件抽取”能否在严格前向条件下产生可重复、净成本后仍有
意义的横截面 rank-IC 增量？

### 2.2 子问题

1. [F] 当前四条 headline 实际证明了什么，哪些结论超出了 frozen config 和样本？
2. [F] purged cross-fitting 与 chronological/live OOS 的证据强度差多少？
3. [H] LLM 作为结构化传感器是否比 free-form return forecaster 更适合低成本个人研究？
4. [H] E3 是否已具备开始不可逆 live headline 的工程和统计条件？
5. [I] Aionis 相对 Qlib、RD-Agent、FinGPT、TradingAgents、FINSABER 等生态的独特价值是什么？

### 2.3 可推翻当前判断的证据

- [H] 若严格 chronological walk-forward 在强基线下复制出稳定、方向一致的 differential，当前
  “四条结果只适用于 CV-proxy”判断将被削弱。
- [H] 若 E3 完整 I1-I9 E2E、shadow 运行、人工抽取审计和真实未知标签评分均通过，当前
  “E3 未 ready”判断应更新。
- [H] 若包含 next-open、换手、滑点、退市和流动性后的前向组合仍有稳定正收益，当前
  “没有可交易性证据”判断应更新。
- [H] 若 LLM ablation 在同一 forward information set 上显示可重复正增量，当前“LLM 尚无选股
  归因证据”判断应更新。

## 3. 证据概览

| 主张 | 支持证据 | 反对证据或缺口 | 等级 | 适用条件 | 可信度 |
|---|---|---|---|---|---|
| 四条处理 bundle 未显示正增量 | ledger #28/#30/#34/#37 | 非 chronological；B 无 differential CI | A | 588 clean ticker、2016+、固定模型/特征 | 高 |
| 项目拥有强 anti-leakage 治理 | config-before-result、哈希、H6、PIT contracts | B/C/D 的 config 与 result Git commit 隔离不如 E1；依赖运行纪律 | A | ledger 和原始产物未被破坏 | 中高 |
| “四条 null 等价于零” | D/E1 CI 较窄 | 未预注册 SESOI/TOST；C 越出 ±0.015；B CI 缺失 | A+B | 需要明确经济等价界限 | 低 |
| E3 是更可信的时间外推路径 | commit-before-reveal 设计、forward ledger 原语 | scheduler/E2E 缺失，runner 有阻断缺口 | A | 真实未知标签、真实 live data | 中 |
| 小模型 LLM 适合结构抽取 | FinBen、FinTagging、FinGPT 工程证据 | forecasting 普遍弱；参数记忆和抽取误差 | A+B | 闭集 schema、人工验证、可弃权 | 中 |
| 当前策略可交易 | baseline gross Sharpe 0.62 | DSR/SPA/MCS 不支持；无成本、换手、退市 | A | 仅当前 gross exploratory lens | 很低 |
| 项目作为个人研究有价值 | 复现治理、负结果、生态缺口 | 长期数据维护和 5-10 年 E3 等待成本 | A+B+I | 目标是研究产出而非短期盈利 | 中高 |

## 4. 内部实证审计

### 4.1 Headline differential

| Phase | 处理臂 - 基线臂 mean rank-IC | 95% CI | DM p | n（月） | LLM 参与 | 审计判读 |
|---|---:|---:|---:|---:|---|---|
| B filed-date vs end+lag | -0.000800 | **ledger 未记录** | 0.870 | 125 | 否 | 未发现增量；不能审计 differential 精度门 |
| C macro/surprise bundle | -0.006487 | [-0.01953, 0.00656] | 0.355 | 125 | 否 | 未发现增量；不满足事后 ±0.015 严格等价 |
| D peer momentum + 13D | -0.002980 | [-0.01371, 0.00775] | 0.597 | 125 | 否 | 未发现增量；区间在事后 ±0.015 内 |
| E1 propagation beyond own shocks | -0.002793 | [-0.01146, 0.00587] | 0.533 | 125 | 否 | 未发现增量；区间在事后 ±0.015 内 |

[F] 上表只使用 [runs/ledger.jsonl](../../runs/ledger.jsonl) 的 `confirmatory:first` 行。
B 结果行只含 `mean_ic_diff_state_minus_base`、`dm_stat`、`dm_p_mbb`，没有 `se_hac`、
`ci_half`、`ci_lo` 或 `ci_hi`。不得用后续本地产物中的数值回填 ledger 事实，也不得把单臂
`ci_half` 当作 paired differential 的 CI。

[F] C/D/E1 的 CI 均跨 0；四个 differential 点估计均为负。h=10/42 的探索性敏感性也跨零，
但它们复用相同历史数据和研究家族，不是独立复制。

[I] 最稳健表述是：“在 frozen universe、九列基线、固定 MSE LightGBM、shared purged grouped
cross-fitting 下，没有观察到这些 bundle 的显著增量 rank-IC。”不应升级为“这些信息已被市场有效
定价”或“不存在可预测性”。

### 4.2 基线与目标函数

[F] ledger 的 frozen `feature_cols` 只有 `mktcap`、`pb_ratio`、`roa` 和六项基本面；
[phase-b-preregistration.md](../../docs/phase-b-preregistration.md) §2 却写两臂共享
momentum/reversal/vol、FF5 和 DFF 宏观。这些共享特征没有出现在实际 headline config。

[F] [learner.py](../../src/aionis/eval/learner.py) 使用 LightGBM `objective="regression"`，而 primary
指标是 Spearman rank-IC。

[I] 当前 null 是 learner/config-specific，不是“标准量价+基本面基线”或 rank-optimal learner 下的
普遍 null。较弱或错配的 baseline 对增量结论的方向影响并不单调：它可能让新 bundle 看起来更容易
增加信息，也可能让模型无法识别条件互补关系。

### 4.3 策略收益透镜

[F] ledger #31/#32 只含 B/C、placebo、sanity 五个策略；baseline gross 年化 Sharpe 约 0.621。
在 `n_trials=20` 网格下所有 DSR p 值至少约 0.47；SPA consistent p = 0.692，MCS 保留全部五个模型。
D/E1 没有对应策略收益行。

[F] 这些结果 gross-of-costs，没有 turnover、next-open 成交、冲击、借券、退市收益或容量。

[I] rank-IC 适合作为预测诊断，但不能直接解释为可实现收益。当前证据不支持称 Aionis 为有效
选股策略，更不支持资金部署。

### 4.4 Phase A 与文档漂移

[F] [frontier_positioning.md](../../docs/frontier_positioning.md) 记录的 scaled Phase A 是 53 个真实
FOMC statement、GLM-4-flash、11 个 sector ETF + SPY、XGBoost DA-lift +5.5pp，CI
[-4.2,+15.2]pp，约 43 个事件簇；它使用 legacy yfinance 路径。

[F] [RESULTS.md](../../docs/RESULTS.md) 另保留一个 Phase A pilot 快照：DA-lift +8.68pp，CI
[-0.83,+17.98]pp，44 个事件簇。两者不是四条月频个股 headline，也尚未在结果文档中清楚区分。

[I] Phase A 最多构成“值得继续检验的结构抽取 pilot”，不能作为小 LLM 已提高个股选股效果的证据。

## 5. 统计与时间外推审计

### 5.1 非显著不等于等价

[F] 项目当前 publishability 规则是 differential 95% CI 跨零且 `ci_half < 0.015`，但预注册明确
没有钉 MDE/SESOI。该规则控制精度，没有要求整个 CI 落入一个有经济含义的等价区间。

[F] Lakens 等对 TOST 的要求是：先定义可接受的最小效应界限，再要求两个单侧检验通过；等价结论
通常对应整个 90% CI 落在预注册界限内。Altman 与 Bland 的经典结论是“不显著”不是“无差异”的证据。

[I] 即便保守地用 95% CI 和事后 `±0.015` 做敏感性描述，C 的下界 -0.01953 仍越界，B 又没有
differential CI。只有 D/E1 可以描述为“当前区间落在 ±0.015 内”，仍不能把事后界限升级为原始
confirmatory equivalence claim。

[D] 新研究线应预注册经济 SESOI、HAC-aware TOST 或区间决策规则；旧 ledger 不改写。旧结果统一
使用“未发现显著增量 + 报告区间”的语言。

### 5.2 Purged CV 不等于 chronological OOS

[F] [cv.py](../../src/aionis/eval/cv.py) 调用 `purgedcv.PurgedGroupKFold`；其 candidate training set
是测试折补集，再剔除标签重叠和 embargo。除最后一个测试块外，训练索引可以包含测试块之后的月份。
仓库测试验证 group 不拆分和索引不重叠，没有验证 `max(train_time) < min(test_time)`。

[I] 该设计对同折两臂的 paired comparison 有价值，也能防止直接标签重叠；但它不能测量真实部署时
面对制度变化、数据可得性变化与模型漂移的表现。结果应称 `purged cross-fitted/OOF CV-proxy`，
不应无修饰地称 chronological OOS。

[D] 新 baseline ladder 使用 expanding/rolling walk-forward：每次训练数据必须严格早于验证和测试；
最终 forward E3 保留为最高证据层。B/C/D/E1 旧配置和结果不重跑、不重命名 ledger。

### 5.3 多重检验与持续观察

[F] 项目报告 `n_trials` 网格至 20，但历史模型、控制、horizon、feature、provider 和被放弃配置的完整
试验族尚未形成一个可独立核验的 trial registry。

[I] DSR/SPA/MCS 是重要改进，但 `n_trials=20` 只是敏感性参数，不等于证明已校正所有研究自由度。
Harvey-Liu-Zhu、Hou-Xue-Zhang 和 McLean-Pontiff 均显示因子发现中的发表、选择和样本外衰减很大。

[H] E3 每月显示累计 IC 并在首次满足 CI 门时裁定，会产生 optional stopping；固定裁定 N/日期或
time-uniform confidence sequence 可以避免普通重复 95% CI 的覆盖失真。

[D] E3 headline ignition 前应冻结最早裁定 N、固定评估日或 alpha-spending/confidence-sequence
方案；dashboard 在裁定前只标 exploratory。

### 5.4 Universe、价格与经济外推

[F] 可解析 universe 为 588/705（83.4%）；114 个改名/合并对象没有通过免费 ticker→CIK 反查。
两臂共享同一集合，减少了 arm-to-arm layout 偏差，但没有消除对完整 S&P 500 的覆盖和退市偏差。

[F] SIC 是当前 SEC snapshot 而不是 historical vintage；13D self-report filtering 和历史分页也有
已知残余误差。免费 S&P 历史成分仓库本身由 Wikipedia/公开资料重建，官方 README 承认遗漏和
早期不可验证性。

[F] [market.py](../../src/aionis/ingest/market.py) 仍实现 Tiingo→Alpaca→yfinance→Stooq fallback，
而项目约束禁止 Yahoo/yfinance 和 Stooq；`pyproject.toml` 仍直接依赖 yfinance。已审计 fetch 间隔
也有低于项目自定 `>=2s` 的路径。adjusted close 尚无明确的 corporate-action as-of contract。

[I] shared-universe differential 的内部比较比绝对组合收益更可信；对“完整历史 S&P 500、可交易、
无幸存者偏差”的外推则很弱。

## 6. E3 readiness 审计

### 6.1 已完成能力

- [F] Slice 1-5 已实现 forward ledger、forward PIT collectors、hybrid causal layer、commit plumbing、
  scoring/accumulation 和 dashboard Forward-IC 视图。
- [F] commit-before-reveal、score hash、mutation refusal、provider pin 和部分 I1-I9 unit tests 已存在。
- [F] E3 设计把宏观 frozen-beta 与 E1 propagation 设为 zero-LLM，仅让 GLM 输出 13D/8-K 的闭集
  `direction/mechanism_keyword` 边；这是比 free-form return forecast 更窄的攻击面。

### 6.2 阻断 live headline 的真实缺口

| 缺口 | 仓库事实 | 影响 |
|---|---|---|
| Scheduler/E2E | Slice 6、Slice 7 未完成；无 `scripts/forward_tick.py` | 没有可持续的月末触发与完整 I1-I9 证据 |
| 静态输入 | `forward_commit_runner._load_inputs` 读取 Phase B/D 静态 cache | 不能证明预测时点数据已更新到 as-of-t |
| LLM 文本为空 | `_events_df` 把所有事件 `text` 设为 `""`，代码注释说明 edge 被跳过 | 当前真实 runner 中 LLM 通道没有运行 |
| 未知标签被删除 | `_clean_panel` 无条件 `dropna(y_fwd_ret)` | 真正当前预测日的横截面可能被删除 |
| 预测日语义 | `run_forward_commit` 使用 `panel_base["date"].max()` | 不保证等于请求的 `predict_ts` |
| Membership gate 未启用 | runner 调用未传 `membership=mem` | I4 的精确 PIT constituent assertion 不执行 |
| Cutoff 字段误义 | `provider_cutoff=predict_ts` | 记录的是调用时间，不是模型/数据真实 cutoff |
| 测试层级 | 现有多数测试 monkeypatch collector 或使用 fixture | 不能证明真实 provider、缓存、时钟和落盘链路 |

[I] E3 的架构方向正确，但“forward zero-leakage by construction”目前仍是设计目标，不是已通过真实
E2E 的系统属性。未来标签尚未发生能消除 outcome memorization，却不能自动消除 late/revised input、
provider tools/RAG、错误 snapshot、universe stale 或模型漂移。

[D] 当前 E3 readiness 判定为 **NO-GO for headline、GO for engineering + shadow preparation**。
进入 1-2 个月 shadow 前至少需要：

1. [D] 修完上表阻断项，并通过真实 month-end dry-run 与 I1-I9 E2E。
2. [D] 原始 input/output、prompt、model id、provider response、调用 UTC、token usage 和 sha256 全量归档。
3. [D] 禁用 provider search/RAG/tools；provider 或模型漂移必须新 config/new sequence。
4. [D] 人工标注 13D/8-K 抽取样本，报告 precision、recall、coverage、abstention 和 schema failure。
5. [D] shadow 只评估运行可靠性和抽取质量，不按 alpha 决定是否更换模型。

## 7. LLM 贡献与成本审计

### 7.1 当前归因

[F] B 是 numeric EDGAR fundamentals；C 是 ALFRED/FRED/earnings 数值 surprise；D 是 SIC peer
momentum + 13D event flag；E1 是确定性 propagation。四者均没有 LLM feature。

[F] 唯一真实 LLM 经验来自 Phase A。`extract_scaled.log` 所列 prompt 约 41,689、completion 约
8,636，合计约 50,325 tokens；`frontier_positioning.md` 写总研究 token 约 72K，两个口径没有成本
registry 对账。

[F] [reports/cost/README.md](../cost/README.md) 仍是 placeholder，明确没有 paid/third-party cost data。
因此项目尚不能报告每月 E3 成本、每个有效事件成本或每个成功抽取成本。

[I] “LLM 辅助预测”目前是研究方向而非结果。低成本优势也尚未用完整账单、失败重试、缓存命中、
人工标注时间和 provider 停服风险证明。

### 7.2 适合小模型的职责

- [H] 闭集事件抽取：从明确 as-of 的 13D/8-K 原文提取实体、方向、机制和期限；允许 abstain。
- [H] 研究候选生成：在看结果前提出可登记假设；每个进入测试的候选计入试验族。
- [H] 数据质量辅助：发现 schema 异常或字段冲突，但由确定性 validator 作最终裁决。
- [I] 不适合的职责：直接输出 expected return、自由因果故事、看过 OOS 后改规则、自动搜索大量
  因子后只提交赢家、直接决定交易。

### 7.3 低成本控制

[D] 只对新增且 hash 未命中的事件调用 LLM；固定单一便宜模型、温度与 max tokens；最多一次有界重试；
以“每个归档事件、每个成功 schema、每个月”的 token/API/人工复核成本记账。不要训练自有 PIT 4B
模型，也不要为当前单一 claim 引入多 agent 辩论。

## 8. 论文与 GitHub 对照

### 8.1 学术与前沿研究

| 来源 | 主要事实 | 对 Aionis 的含义 |
|---|---|---|
| Gu, Kelly, Xiu, *Empirical Asset Pricing via ML* | 大规模美股、94 特征；momentum、liquidity、volatility 重要；严格时间切分 | [D] 补强 baseline 与 chronological split，而非直接迁移其历史 alpha |
| Kelly, Malamud, Zhou, *Virtue of Complexity* | 复杂度在正则化和诚实 OOS 下可有价值 | [I] 当前固定单模型 null 不能外推到所有模型复杂度 |
| Han et al., ML Fama-MacBeth | 200+ 特征组合和正则化改善 OOS | [D] 用基线梯而不是单一九列 baseline |
| Poh et al., learning-to-rank | 横截面排序目标可优于回归后排序 | [H] rank objective 是合理新实验，但须新预注册 |
| FinBen | 42 数据集/24 任务；LLM 文本与抽取较强，forecasting 落后传统方法 | [I] 支持 extractor，不支持 direct forecaster |
| Ke, Kelly, Xiu；Chen, Kelly, Xiu | 新闻文本表示可含收益信息 | [I] 依赖大规模、常为专有新闻；不能直接外推到免费 EDGAR 小样本 |
| Didisheim et al., *Inefficient Pricing of News* | 对已知 characteristics 残差化后的 pure news 更有预测力 | [H] E3 后续应测 novelty/residual，不应只堆原始文本标签 |
| Chronologically Consistent LMs；Scaling PIT LMs | point-in-time 模型/embedding 对历史评估重要 | [I] 支持时间一致性；其训练规模不适合个人预算 |
| FinTagging | LLM 可抽取金融文本，但细粒度概念对齐仍弱 | [D] schema + validator + human audit 必须并存 |
| FINSABER | 更长样本和多市场状态下，LLM 交易优势明显衰减 | [I] 反对从短期 demo 外推长期 alpha |
| Lakens et al.；Altman & Bland | 等价检验与“非显著不等于无效” | [D] 重写结论语言，新增 SESOI/TOST |
| Harvey-Liu-Zhu；Hou-Xue-Zhang；McLean-Pontiff | factor zoo、多重试验与发表后衰减严重 | [D] 所有自适应探索必须计入 trial registry |
| Pérignon et al. | 大规模金融复现实验的精确复现率有限 | [I] Aionis ledger/H6/null-first 具有独立研究价值 |

### 8.2 开源生态与许可证边界

| 项目 | 许可证/事实 | 可借鉴 | 不应迁移 |
|---|---|---|---|
| Microsoft Qlib | MIT；有 PIT/workflow/IC 设计 | 数据布局、workflow、报告 | Yahoo/Baostock 数据路径；不能替代 EDGAR/ALFRED/PIT membership |
| purged-cross-validation | MIT；Aionis 当前依赖 | purge/embargo/CPCV/DSR 原语 | README 明确不能检测 feature/ingest leakage；保留本项目 invariant tests |
| alphalens-reloaded | Apache-2.0；Spearman IC、turnover、quantile | 独立 IC/tearsheet oracle | 不提供 PIT、ledger、purge 或 trial control |
| ml4t/diagnostic | MIT beta；HAC IC、DSR、PBO/FDR | 独立统计核验 | Python 3.12+/Polars 与当前栈有迁移成本 |
| RD-Agent | MIT；自动因子/模型研发 | exploratory 研究循环 | contextual search 扩大隐含试验数，不作 confirmatory engine |
| FinGPT | MIT 代码；低成本 LoRA/文本任务 | schema、缓存、小模型适配 | 代码许可不覆盖权重/数据；无 PIT monthly IC 证据 |
| OpenFactor | Apache-2.0；确定性模型优先、阈值触发 LLM | 稀疏调用、闭集标签、缓存 | OpenAI provider 与 overwrite 行为不符合本项目规则 |
| AlphaForgeBench | MIT；LLM 生成因子、确定性 sandbox 验证 | “LLM proposes, evidence decides” | 公开资产/频率与 PIT S&P 500 不同 |
| FINSABER | Apache-2.0 代码；长窗评测、成本/执行约束 | next-open、slippage、liquidity、LLM 成本工件 | 数据 license 不清晰，不能直接进入 7-gate |
| TradingAgents | Apache-2.0；多角色交易 agent | payload/date-filter 回归测试是有用反例 | 热度、角色辩论或模拟收益不证明 anti-leakage；含不合规数据源 |
| FinRL / FinRobot | MIT/Apache；交易环境和报告 agent | 执行层/报告编排参考 | Yahoo、OpenAI/provider 和 DRL 目标不符合 Aionis headline |
| OpenSourceAP/CrossSection | GPL-2.0、WRDS；大量信号定义 | 方法清单 | permissive-only 规则下不可复制代码 |
| hanshof / pierrebrunelle S&P history | MIT；公开资料重建 | 交叉校验和透明 scope | 不是审计级成分真值，早期遗漏与改名问题仍在 |

[I] 没有一个现成开源项目同时提供 Aionis 所需的美国 PIT membership、EDGAR filed-date、ALFRED
vintage、config-before-result ledger、paired monthly differential、H6、multiple-testing 和 permissive-only
许可。Aionis 的生态位置不是“更强交易机器人”，而是 evidence-first research harness。

## 9. 主要争议与反方

### 9.1 “四条 null 说明市场有效”

- [F] 支持方证据：四个点估计均不为正，C/D/E1 CI 跨零且较窄，多组 placebo 和 horizon sensitivity
  没有显示稳定正增量。
- [F] 反方证据：B 无 paired CI；C 不满足事后 ±0.015 等价；baseline 缺少预注册描述的量价特征；
  learner 目标错配；CV 非 chronological。
- [I] 结论：它们反驳了四个 frozen implementation 下的强正增量叙事，但不能证明普遍市场效率。

### 9.2 “forward-live 自动等于零泄漏”

- [F] 支持方证据：预测 hash 在 outcome 发生前提交，未来 outcome 物理上尚未实现。
- [F] 反方证据：输入仍可能晚到/修订，universe 可 stale，provider 可漂移或使用外部工具，当前 runner
  尚未通过真实 E2E。
- [I] 结论：forward-live 大幅降低 outcome leakage，是最高优先路线，但“zero”必须由运行不变量持续证明。

### 9.3 “更多 agent/更大模型能提高成功率”

- [F] RD-Agent、TradingAgents 等提供更复杂探索架构；AlphaForgeBench 反而把 LLM 限制在候选生成，
  用确定性 evaluator 裁决。
- [I] 对 Aionis 的单 claim、低预算和严格 multiplicity 约束，agent 数量会提高成本和隐含试验数，
  不会自动提高证据质量。
- [D] 当前不向研究信号或预测 runtime 增加多-agent inference，也不自训练大模型。整改执行可使用
  on-demand Engineer/Verifier/Reviewer，但必须一任务一写者、独立验收，并把所有研究候选计入试验族。

### 9.4 “长达 5-10 年的 E3 不值得”

- [F] 预注册按 `sigma(IC)≈0.06` 粗估需约 60-120+ 月达到当前精度门；provider 能否持续多年未知。
- [I] 若目标是快速盈利，E3 的机会成本过高；若目标是可信前向记录、负结果和可复现软件，时间本身
  是研究设计的一部分。
- [D] 把 E3 定位为低频、自动化、可持续的长期轨道；短期产出来自方法、数据审计和 null 报告，
  不能用频繁换 config 缩短日历。

## 10. 适用边界

### 10.1 当前允许的结论

[F] 可写：

> 在 2016+、125 个月、588 个可解析候选 ticker、九列冻结基本面基线、固定 MSE LightGBM、
> shared 5-fold purged grouped cross-fitting 下，B/C/D/E1 没有观察到处理 bundle 相对基线的显著
> 正 differential rank-IC；B 的 paired differential CI 未记录。

[I] 可写：该结果增加了“这些具体 bundle 在此实现下没有大幅稳定增量”的证据，并支持继续以 null
为先验。

### 10.2 当前不允许的结论

- [F] 不得写“市场已被证明有效”或“这些信息已完全定价”。
- [F] 不得写“四条均通过严格等价检验”或“B differential CI 半宽 <0.015”。
- [F] 不得把 B/C/D/E1 称作严格 chronological OOS 或 live track record。
- [F] 不得写“LLM 改善了四条 headline”或“小模型已带来个股 alpha”。
- [F] 不得把 gross rank-IC/Sharpe 解释为净成本、可交易或可承载资金的策略。

### 10.3 外部可迁移性

[I] 结论只覆盖 S&P 500 大盘股、月频、2016+、当前免费 universe 重建和当前数据合同。不能直接迁移
到小盘股、国际市场、日内、做空可用性、不同模型、不同 provider 或不同宏观时期。

## 11. 决策建议

### P0：先修证据语义与可运行性

1. [D] 同步 README/RESULTS/state 的阶段数、测试数和 Phase A 口径；保留 ledger 为唯一结果事实源。
2. [D] 所有历史结果改称 purged cross-fitted/CV-proxy；B 明示 paired CI 缺失；C 明示非严格等价。
3. [D] 修复标准 pytest 的 dashboard import collection failure，恢复干净环境 full-suite gate。
4. [D] 移除 yfinance/Stooq runtime，并对所有研究 fetch 强制 `>=2s` 与有界退避；批准源失败时 fail closed。
5. [D] E3 在当前日期、未知标签、event text、membership 和 provider metadata 上 fail closed；
   scheduler 与 headline ignition 继续 HOLD。

### P1：先关闭数据合同与统计决策门

1. [D] 在任何 outcome-bearing E3 观察前，决定经济 SESOI、TOST/区间规则、完整 trial family 和
   固定/顺序裁定方案。
2. [D] 新 config/new ledger row 才可加入强数值基线或 rank-aware objective；不静默修改旧结果。
3. [D] adjusted-price corporate-action as-of contract 和完整 trial registry 作为独立 owner decision，
   不借整改任务暗改历史数据语义。

### P2：完成 E3，但暂不 ignite headline

1. [D] 完成 scheduler、真实 as-of 数据刷新、未知标签预测、event text、membership gate 和 I1-I9 E2E。
2. [D] 运行 1-2 个月 shadow，只按预先冻结的 operational gate 决定 readiness。
3. [D] shadow 后若 provider 不稳定，只能在 headline ignition 前换 provider；ignite 后漂移必须新序列。

### P2 后续：验证 LLM 的最小增量

1. [D] 建立人工 gold set 和 zero-LLM ablation；LLM 只处理新增闭集事件。
2. [H] 优先检验结构化 event novelty/pure-news residual，而不是增加 free-form narrative feature。
3. [D] 每次 hypothesis/config 均计入 trial registry；禁止 outcome-aware prompt 或 schema 调整。

### P2 后续：增加经济和发表透镜

1. [D] 加 next-open、turnover、slippage、liquidity、borrow、delisting 和 capacity；报告净值而非只报 IC。
2. [D] 优先把成果定位为 PIT/anti-leakage harness、可复现 null benchmark、数据审计或方法论文。
3. [D] 若到预注册日历 gate 仍无净成本前向证据，发布 null 并停止该信号线，不 rerun-to-significance。

## 12. 置信度

| 判断 | 置信度 | 原因 |
|---|---|---|
| B differential CI 未记录 | 很高 | ledger 原始行可直接核验 |
| C 不构成严格等价 | 很高 | CI、规则与 TOST 定义均明确 |
| B/C/D/E1 非 chronological OOS | 很高 | split 源码和依赖语义可直接核验 |
| LLM 未进入四条 headline | 很高 | frozen feature/config 和阶段代码可核验 |
| 当前标准 pytest 失败 | 很高 | 本审计现场复现，退出码 2 |
| E3 当前不宜 ignite headline | 高 | 多个 runner 阻断项和缺失 E2E 可直接核验 |
| Aionis 作为研究 harness 有价值 | 中高 | 治理事实明确，价值判断含主观目标权重 |
| 强基线/排序目标会改变 null | 低至中 | 有外部文献动机，尚未在 Aionis 验证 |
| E3 LLM 最终会有正 alpha | 很低 | 当前无归因实证，且需多年真实观察 |
| E3 最终能稳定运行 5-10 年 | 低 | provider、数据与维护持续性未知 |

## 13. 尚未解决的问题

- [F] B paired differential artifact 是否应在新 schema 下独立登记，只能由 ledger governance 决定；
  本审计不补写 ledger。
- [H] 四个 historical differential 在严格 chronological split 下是否保持方向和区间？
- [H] 完整量价强基线是否改变 treatment complementarity？
- [H] E3 中有效、非空 13D/8-K 文本的月度覆盖、tie rate 和 abstention rate 是多少？
- [F] 每月真实 API、重试、人工复核和存储成本尚无完整记录。
- [H] 免费 universe 与 corporate-action 合同的残余误差对 absolute return 和 differential 分别多大？
- [H] 长期累计 inference 应采用固定 N、group-sequential 还是 time-uniform confidence sequence？

## 14. 引用

### 14.1 仓库内原始证据

- [runs/ledger.jsonl](../../runs/ledger.jsonl) — config、B/C/D/E1、strategy、horizon 的权威事件记录。
- [state/current.md](../../state/current.md) — 当前自述状态；测试状态已由本审计独立复核。
- [docs/RESULTS.md](../../docs/RESULTS.md) — 结果快照及已披露 scope limits。
- [docs/phase-b-preregistration.md](../../docs/phase-b-preregistration.md) — Phase B 原始设计与基线描述。
- [docs/phase-e3-preregistration.md](../../docs/phase-e3-preregistration.md) — E3 claim、power 与 live 规则。
- [docs/phase-e3-implementation-plan.md](../../docs/phase-e3-implementation-plan.md) — I1-I9 与 slices。
- [tasks/active/TASK-E3-launch.md](../../tasks/active/TASK-E3-launch.md) — Slice 6/7 未完成状态。
- [src/aionis/eval/cv.py](../../src/aionis/eval/cv.py)；
  [two_arm.py](../../src/aionis/eval/two_arm.py) — historical split 与 panel label handling。
- [src/aionis/eval/learner.py](../../src/aionis/eval/learner.py) — frozen MSE LightGBM。
- [src/aionis/eval/forward_commit.py](../../src/aionis/eval/forward_commit.py)；
  [forward_commit_runner.py](../../src/aionis/eval/forward_commit_runner.py) — E3 实际 runner 路径。
- [src/aionis/ingest/market.py](../../src/aionis/ingest/market.py)；
  [pyproject.toml](../../pyproject.toml) — provider fallback、依赖与 pytest packaging。
- [docs/frontier_positioning.md](../../docs/frontier_positioning.md)；
  [reports/cost/README.md](../cost/README.md) — Phase A 与成本记录状态。

### 14.2 论文和官方研究

- Gu, Kelly, Xiu, [Empirical Asset Pricing via Machine Learning](https://www.nber.org/papers/w25398).
- Kelly, Malamud, Zhou, [The Virtue of Complexity in Return Prediction](https://doi.org/10.1111/jofi.13298).
- Han et al., [Machine Learning and the Cross-Section of Expected Returns](https://ideas.repec.org/a/oup/revfin/v28y2024i6p1807-1831..html).
- Chen, Pelger, Zhu, [Deep Learning in Asset Pricing](https://doi.org/10.1287/mnsc.2023.4695).
- Poh et al., [Building Cross-Sectional Systematic Strategies by Learning to Rank](https://doi.org/10.3905/jfds.2021.1.060).
- Ding et al., [FinBen](https://doi.org/10.48550/arxiv.2402.12659).
- Ke, Kelly, Xiu, [Predicting Returns with Text Data](https://www.nber.org/papers/w26186).
- Chen, Kelly, Xiu, [Expected Returns and Large Language Models](https://ssrn.com/abstract=4416687).
- Didisheim et al., [Inefficient Pricing of News](https://www.nber.org/papers/w35093).
- He et al., [Chronologically Consistent Large Language Models](https://arxiv.org/abs/2502.21206).
- Kelly et al., [Scaling Point-in-Time Language Models](https://www.nber.org/papers/w35247).
- Li et al., [FINSABER](https://arxiv.org/abs/2505.07078).
- FinTagging, [An LLM-ready Benchmark for XBRL Concept Tagging](https://doi.org/10.48550/arxiv.2505.20650).
- Lakens et al., [Equivalence Testing for Psychological Research](https://doi.org/10.1177/2515245918770963).
- Altman and Bland, [Absence of Evidence Is Not Evidence of Absence](https://www.bmj.com/content/311/7003/485).
- Howard et al., [Time-uniform Confidence Sequences](https://doi.org/10.1214/20-AOS1991).
- Harvey, Liu, Zhu, [and the Cross-Section of Expected Returns](https://www.nber.org/papers/w20592).
- Hou, Xue, Zhang, [Replicating Anomalies](https://www.nber.org/papers/w23394).
- McLean and Pontiff, [Does Academic Research Destroy Stock Return Predictability?](https://doi.org/10.1111/jofi.12365).
- Pérignon et al., [Computational Reproducibility in Finance](https://doi.org/10.1093/rfs/hhae029).
- CRSP, [Calculations and Index Methodologies](https://www.crsp.org/wp-content/uploads/guides/CRSP_Calculations_and_Index_Methodologies.pdf).
- Shumway, [The Delisting Bias in CRSP Data](https://www.tylergshumway.org/Shumway-DelistingBiasCRSP-1997.pdf).

### 14.3 官方 GitHub 仓库

- [Microsoft Qlib](https://github.com/microsoft/qlib)
- [Microsoft RD-Agent](https://github.com/microsoft/RD-Agent)
- [FinGPT](https://github.com/AI4Finance-Foundation/FinGPT)
- [FinRobot](https://github.com/AI4Finance-Foundation/FinRobot)
- [TradingAgents](https://github.com/TauricResearch/TradingAgents)
- [FinRL](https://github.com/AI4Finance-Foundation/FinRL)
- [purged-cross-validation](https://github.com/eslazarev/purged-cross-validation)
- [alphalens-reloaded](https://github.com/stefan-jansen/alphalens-reloaded)
- [ml4t/diagnostic](https://github.com/ml4t/diagnostic)
- [OpenFactor](https://github.com/ralliesai/openfactor)
- [AlphaForgeBench](https://github.com/finbrain-lab-hkustgz/AlphaForgeBench)
- [FINSABER](https://github.com/waylonli/FINSABER)
- [OpenSourceAP/CrossSection](https://github.com/OpenSourceAP/CrossSection)
- [hanshof/sp500_constituents](https://github.com/hanshof/sp500_constituents)
- [pierrebrunelle/sp500-historical-constituents](https://github.com/pierrebrunelle/sp500-historical-constituents)

## 15. 本审计验证记录

- [F] `git status --short --branch`：审计开始时分支为 `feat/e3-forward-ledger`，ahead 4，工作树无既有改动。
- [F] `uv run pytest -q`：**FAIL during collection**，退出码 2；
  `tests/test_dashboard_curve.py:7` 导入 `dashboard.app` 时 `ModuleNotFoundError: dashboard`。
- [F] 审计报告编制没有运行任何 confirmatory phase、没有生成或观察新 OOS 指标，也没有修改
  spec/pre-reg/ledger/src/scripts。并行 Planner 另行新增 `TASK-AUD-*` 任务切片和 state 记录；本轮未提交。

## 16. 整改代理执行与优先级记录

### 16.1 第一波（P0，已执行）

| 代理角色 | 隔离范围 | 结果 | 后续门禁 |
|---|---|---|---|
| Engineer | AUD-01；仅 `pyproject.toml` | 增加 pytest `pythonpath = ["."]` | 已完成 |
| Verifier | AUD-01 验收命令；只读 | PASS：576 passed、0 skipped、ruff clean | 已完成 |
| Researcher/Planner | AUD-03；只读 chronology 预检 | grouped folds 定性为 purged cross-fit；冻结半开时间边界 | 等 Engineer |
| Researcher/Planner | AUD-04/05；只读 source/request inventory | AUD-04 可执行；AUD-05 超过 M，必须重新切片 | 等 AUD-01 Reviewer |
| Engineer/Verifier/Reviewer | AUD-03 chronology contract | 第一轮修复复验 PASS / Reviewer APPROVE | COMPLETE |
| Engineer/Verifier/Reviewer | AUD-04 source allowlist | 第一轮修复复验 PASS / Reviewer APPROVE | COMPLETE |
| Engineer/Verifier/Reviewer | AUD-02 factual reconciliation | 独立复验 PASS / Reviewer APPROVE | COMPLETE |
| Engineer/Verifier/Reviewer | AUD-05A HTTP policy primitive | repair 1 substantive PASS / Reviewer APPROVE；inventory corrected | COMPLETE |

[F] 2026-07-31 的最小修复之后，Orchestrator 再次运行 `uv run pytest -q -x`，退出码 0；此前
第 15 节的 collection failure 是修复前基线，仍保留作为根因证据，不代表当前状态。

### 16.2 后续任务等级与代理边界

| 等级 | 任务 | Size / 风险 | 允许的代理推进 | 当前状态 |
|---|---|---|---|---|
| P0 | AUD-01 测试入口 | S / medium | 独立 Reviewer 只审 diff 与证据 | COMPLETE：Verifier PASS / Reviewer APPROVE |
| P0 | AUD-03 chronology contract | M / high | AUD-01 APPROVE 后单一 Engineer；独立 Verifier/Reviewer | COMPLETE：Verifier PASS / Reviewer APPROVE |
| P0 | AUD-04 source allowlist | M / medium | 与 AUD-03 并行，但独占 market/lock/Phase B fetch 文件 | COMPLETE：Verifier PASS / Reviewer APPROVE |
| P0 | AUD-02 factual reconciliation | M / high | AUD-03 完成后单一文档 Engineer | COMPLETE：Verifier PASS / Reviewer APPROVE |
| P0 | AUD-05A HTTP policy primitive | S / medium | AUD-04 APPROVE 后独立 Engineer/Verifier/Reviewer | COMPLETE：Verifier PASS / Reviewer APPROVE |
| P0 | AUD-06 E3 live readiness | M / high | 先只读准备；PASS 依赖 AUD-04/05 与 owner contract | dependency/owner hold |
| P0-L | AUD-05 politeness | L / high | 禁止整体下发；拆为 policy、adapter、边界处置三个 S/M | reslice required |
| P1 | AUD-07 SESOI/TOST/sequential | M / high | 统计 Reviewer 可只读准备；冻结需 owner decision | owner hold |
| P2 | strong baseline / economic / LLM eval | L candidates | 仅研究与规划；必须先拆分并登记新 config/trial | backlog |

[D] 多代理只用于上下文隔离、工程实现和独立验证。任何代理均未获授权运行 confirmatory、观察
E3 outcome-bearing 指标、修改 frozen prereg/config/ledger、增加因子搜索或点燃 headline。

### 16.3 波次并行规则

1. 同一时间每个文件边界只有一个写入代理；只读 Researcher/Planner 可并行。
2. 每个 S/M 实现必须依次经过 Engineer → 独立 Verifier → 独立 Reviewer。
3. AUD-03 与 AUD-04 只有在 AUD-01 Reviewer APPROVE 后才能作为第二波并行写任务。
4. AUD-04 与 AUD-05 因共同修改 market/request tests 必须串行；AUD-05 拆分前保持 HOLD。
5. 任一高风险门失败即停止其所有下游；两轮修复仍失败则标记 BLOCKED，禁止无限循环。
