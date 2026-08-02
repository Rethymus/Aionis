# 轨道 B（v0.2 七主题选股平台）S0/S1 切片实施计划

> 日期：2026-08-02
> 状态：规划文档（未冻结，未实施）
> 类型：战略切片计划 —— **本轮只规划不写代码**
> 范围：S0（数据脊柱）+ S1（price-only baseline + 回测/风险/市场结构）
> 约束：新预注册线，绝不污染 B/C/D/E1；E3 仍 HOLD

---

## 1. 目标与边界

### 1.1 核心目标

轨道 B 是**新预注册线**，与现有 B/C/D/E1 冻结面完全隔离：
- **新 config = 新 ledger row**：任何配置变更都产生新的 ledger 行，绝不静默覆盖历史
- **E3 仍 HOLD**：本轮只规划，不触碰 E3 的 forward/调度器/统计门
- **只规划不实施**：本文档落盘后，等待 owner 裁断 + 冻结预注册 claim 后才动代码

### 1.2 不污染历史的原则

1. **数据隔离**：轨道 B 使用独立的 `runs/ledger_track_b.jsonl`（或前缀区分），绝不追加到主 ledger
2. **代码路径**：新增 `src/aionis/track_b/` 子模块（或 `cross_sectional/`），复用核心工具但隔离入口
3. **测试隔离**：`tests/test_track_b/` 独立套件，不修改现有测试
4. **文档隔离**：`docs/track-b-*` 预注册文档，独立于现有 phase-*

### 1.3 成功定义

轨道 B 的"成功"与 Aionis 窄 harness 一致：**null-with-tight-CI 是可发表成果**。
- S0 验收：PIT 数据脊柱就绪，幸存者偏差显式处理或声明
- S1 验收：price-only baseline 数字跑通，IC/Sharpe/DM 可复现

---

## 2. S0 数据脊柱切片（覆盖主题 ①行情 ②宏观 ③基本面）

S0 目标：搭建"无 key 日频价 + PIT 基本面"的横截面数据脊柱，幸存者偏差被显式处理。

### 2.1 S0-M：现有能力盘点与复用（M=Medium）

**目标**：盘点现有模块，明确哪些可直接复用、哪些需改造、哪些需新建。

| 现有模块 | 复用状态 | 泄漏风险 | 改造点 |
|---|---|---|---|
| `ingest/market.py`（Tiingo/Alpaca） | ✅ 直接复用 | adjClose 已复权；universe 幸存者偏差 | 补充 corporate-action as-of 合同文本 |
| `ingest/fundamentals.py`（EDGAR XBRL） | ✅ 直接复用 | filed-date PIT by construction | 扩展 METRIC_TAGS（仅 9 列 → 量价特征） |
| `ingest/universe.py`（hanshof/pb） | ✅ 直接复用 | 日频 PIT 成分；历史来源不透明 | fork + 审行数（§2.2 独立任务） |
| `ingest/vix.py` | ✅ 直接复用 | FRED 无修订 PIT | 已有 |
| `features/alignment.py`（NYSE sessions） | ✅ 直接复用 | PIT 对齐断言已存在 | 无需改造 |
| `eval/cv.py`（purgedcv 适配器） | ✅ 直接复用 | PurgedGroupKFold 已封装 | 已支持 group=month |
| `eval/rank_ic.py` | ✅ 直接复用 | 月频 rank-IC 已实现 | 无需改造 |
| `eval/learner.py`（LightGBM frozen） | ⚠️ 需 RD-15 | MSE 目标非 rank | RD-15 已完成（lambdarank） |

**验收标准**：
- [ ] 产生一份"复用清单表"（上表细化到每个函数）
- [ ] 明确标注"不可复用"的模块及原因
- [ ] 识别需 owner 裁断的模糊点

**前置依赖**：无

**反泄漏不变量**：
- PIT 对齐断言保留：`assert all(features.index <= labels.index)` 永真
- purged CV 折生成器统一：所有下游模型共用同一组折

---

### 2.2 S0-S①：PIT Universe 验证与交叉校验（S=Small）

**目标**：fork `hanshof/sp500_constituents`，审计行数/日期范围，与 `pierrebrunelle/sp500-historical-constituents` 交叉校验 Jaccard。

**要创建/修改的文件**：
- `scripts/audit_hanshof_universe.py`（新建）—— fork 审计脚本
- `src/aionis/ingest/universe.py`（可能修改）—— 补充审计函数

**验收标准**：
- [ ] hanshof CSV 行数 > X（待审计后填）
- [ ] 日期范围覆盖 1996-01-02 → 最新（待审计后填）
- [ ] 2016+ 重叠窗口的月度 Jaccard ≥ 0.95（或记录分歧）
- [ ] fork 仓库创建 + sha256 pinned
- [ ] 审计报告落盘 `reports/audits/hanshof-universe-*.md`

**前置依赖**：S0-M

**反泄漏不变量**：
- 成员资格查询永远是"最新 snapshot ≤ 查询日期"，无 forward-fill
- 最早日期之前的 cross-section 被丢弃（不虚构成分）

**挂接 OSS**：
- `hanshof/sp500_constituents`（MIT，46k★，日频 1996+）
- `pierrebrunelle/sp500-historical-constituents`（MIT，月频 2016+，可复现交叉校验）

---

### 2.3 S0-S②：PIT 基本面扩展（Corporate Vital Signs 扩充）

**目标**：从现有 9 列 baseline 扩展到覆盖 size / value / profitability / leverage / momentum / volatility / liquidity 的量价特征。

**要创建/修改的文件**：
- `src/aionis/features/corporate_vital_signs.py`（新建）—— 特征工程模块
- `src/aionis/ingest/fundamentals.py`（修改）—— 扩展 METRIC_TAGS

**验收标准**：
- [ ] 至少 20 列 PIT 特征（9 基础 + 11 量价衍生）
- [ ] 每列特征附带 `filed_date` PIT 标记
- [ ] NaN 前置（无 filed 值之前）正确处理
- [ ] 特征计算单元测试覆盖

**前置依赖**：S0-M

**反泄漏不变量**：
- 特征值永远是 `f(filed_date <= t)` 的函数，绝不依赖 `end` 或未申报值
- 衍生特征（如 momentum）的计算窗口严格在折内训练段

**挂接 OSS**：
- `edgartools`（MIT，2.5k★）—— SEC EDGAR XBRL as-filed
- `Sharadar SF1`（付费，备用）或 `SimFin`（免费需 key，备用）

---

### 2.4 S0-S③：宏观/因子组合挂接（Fama-French + FRED/ALFRED）

**目标**：复用现有 ALFRED vintage PIT 纪律，挂接 Fama-French 五因子组合作为后续风险调整的基准。

**要创建/修改的文件**：
- `src/aionis/ingest/fama_french.py`（新建）—— FF bulk ZIP 解析
- `src/aionis/ingest/macro_surprise.py`（复用）—— ALFRED vintage 纪律

**验收标准**：
- [ ] FF5 因子日频数据就绪（market / smb / hml / rmw / cma）
- [ ] 每个因子附带 vintge 标记（as-of date）
- [ ] ALFRED 宏观 surprise 复用现有实现
- [ ] 数据缓存 sha256 可 pin

**前置依赖**：S0-M

**反泄漏不变量**：
- FF 因子值使用"发布时可用"的 vintage（通过 Kenneth-French 官方或重建）
- 宏观 surprise 的 `as_of` 纪律保留（C phase 已实现）

**挂接 OSS**：
- `pandas-datareader`（BSD）—— FRED/ALFRED
- Kenneth-French 官方数据库（无 key，bulk ZIP）

---

### 2.5 S0-L：横截面 Panel PIT 对齐与幸存者屏蔽（L=Large）

**目标**：实现"价格 + 基本面 + 宏观"的 PIT 对齐横截面 Panel，并应用幸存者屏蔽。

**要创建/修改的文件**：
- `src/aionis/features/panel_alignment.py`（新建）—— PIT join 逻辑
- `src/aionis/ingest/universe.py`（复用）—— `mask_panel_to_pit`

**验收标准**：
- [ ] Panel 结构：`[date, ticker, feature1, ..., featureN, forward_return_h]`
- [ ] 每行的特征值都满足 `filed_date <= row_date`（断言测试）
- [ ] `forward_return_h` 的计算窗口严格在 `[row_date, row_date+h]`
- [ ] 幸存者屏蔽应用：只保留 `constituents_on(row_date)` 的 ticker
- [ ] 单元测试覆盖所有泄漏路径

**前置依赖**：S0-S① + S0-S② + S0-S③

**反泄漏不变量**：
- `fit_start/end` 钉在折内训练段（ qlib `RobustZScoreNorm`/`CSZScoreNorm` 的致命陷阱）
- 全面板 fit 禁止：每个 fold 的 scaler 只能在该 fold 的 train 行上 fit
- `forward_return_h` 不参与任何特征变换（只作 label）

**挂接 OSS**：
- `microsoft/qlib` 的 PIT-DB 模块（参考，不直接 vendor）
- 现有 `features/alignment.py`（复用 NYSE sessions）

---

## 3. S1 price-only baseline + 回测/风险/市场结构挂轮切片

S1 目标：建立"要 beat 的数" —— price-only ML 选股 vs 等权，并一次性补齐回测/风险/市场结构评估能力。

### 3.1 S1-M①：price-only baseline 训练管道（M=Medium）

**目标**：搭建纯价格特征（momentum/reversal/volatility）的 LightGBM 训练管道，输出月度 rank-IC。

**要创建/修改的文件**：
- `src/aionis/track_b/price_baseline.py`（新建）—— price-only 训练入口
- `src/aionis/features/price_features.py`（新建）—— 纯价格特征工程
- `src/aionis/eval/learner.py`（复用）—— LightGBM frozen
- `src/aionis/eval/ranking_contract.py`（复用）—— RD-15 lambdarank

**验收标准**：
- [ ] 价格特征至少包含：momentum_5d/10d/21d/42d、reversal、volatility、ATR-like
- [ ] 训练使用 `PurgedGroupKFold(5, group=month, embargo=21)`
- [ ] 输出月度 rank-IC 系列（时间戳 × IC 值）
- [ ] HAC SE / CI 半宽计算（复用 `rank_ic_summary`）
- [ ] 可复现性：同一数据 bit-identical 输出

**前置依赖**：S0-L（Panel PIT 对齐）

**反泄漏不变量**：
- 价格特征的计算窗口严格不包含 `row_date` 的收盘价（否则超前泄漏）
- purged CV 折的 `embargo=21` 确保标签不泄漏

**挂接 OSS**：
- `purgedcv`（MIT，eslazarev）—— PurgedGroupKFold
- `lightgbm`（MIT）—— 冻结学习器
- `statsmodels`（BSD）—— Newey-West HAC

---

### 3.2 S1-M②：等权 baseline + DM 检验（M=Medium）

**目标**：建立"等权组合"作为 price-only top-quantile 组合的对照基准，用 Diebold-Mariano 检验两者**组合收益**差异是否显著。【已按复审 H-1 修订 2026-08-02：等权组合无排序、rank-IC 无定义；DM 对象是组合收益损失，非 rank-IC】

**要创建/修改的文件**：
- `src/aionis/track_b/equal_weight_baseline.py`（新建）—— 等权组合收益（复用 `eval/strategy_returns.py` 的 `long_short_returns` / `strategy_returns_by_symbol`，不重写）
- `src/aionis/eval/metrics.py`（复用）—— diebold_mariano

**验收标准**：
- [ ] 等权组合：每月对 PIT universe 等权持仓 → forward_return 序列
- [ ] price-only 组合：top-quantile（按 price-only score）持仓 → forward_return 序列
- [ ] DM 检验对象：`loss(price-only 组合收益) - loss(等权组合收益)`（**收益损失，非 rank-IC**）
- [ ] cluster-robust SE（按 month 分组）
- [ ] HLN 小样本修正应用

**前置依赖**：S1-M①

**反泄漏不变量**：
- 等权组合的 forward_return 窗口与 price-only 组合完全相同
- DM 的 cluster 按 month 分组（同一天事件对所有 sector 冲击相同）

**挂接 OSS**：
- `statsmodels`（BSD）—— OLS + HAC
- `scipy`（BSD）—— Student-t 分布

---

### 3.3 S1-L①：FINSABER 净成本回测挂接（L=Large）

**目标**：挂接 `FINSABER`（KDD 2026，Apache-2.0）作为净成本回测 harness，补齐"换手/next-open/滑点/借券/退市收益/容量"六维。

**要创建/修改的文件**：
- `src/aionis/track_b/finsaber_adapter.py`（新建）—— FINSABER 接口适配
- `scripts/track_b_backtest_run.py`（新建）—— 回测运行脚本

**验收标准**：
- [ ] FINSABER 仓库 clone + license 验证（Apache-2.0）
- [ ] 适配器输入：`{date, ticker, score}` + 价格数据
- [ ] 适配器输出：净成本 Sharpe / 换手率 / 滑点成本 / 借券成本 / 容量估计
- [ ] 单元测试：模拟场景的成本计算正确性
- [ ] 与现有 `strategy_returns.py` 的 gross 回测交叉校验

**前置依赖**：S1-M①（需要 score 输入）

**反泄漏不变量**：
- 执行价格严格是"下一开盘价"（next-open），不是当日收盘价
- 换手率计算基于"实际可交易"的成分（退市股剔除）
- LLM 成本计入（E3 相关，S1 可 stub）

**挂接 OSS**：
- `waylonli/FINSABER`（Apache-2.0，KDD 2026）—— next-open 执行 + slippage + liquidity + LLM cost
- 参考：`bt`（MIT）—— 备用回测引擎

**许可证确认**：
- FINSABER：Apache-2.0（✅ permissive，可商用）
- 已通过 2026-08-01 WebFetch 核实仓库存在

---

### 3.4 S1-L②：alphalens-reloaded + pyfolio-reloaded IC/tearsheet 挂接（L=Large）

**目标**：挂接 `alphalens-reloaded`（Apache-2.0）和 `pyfolio-reloaded`（Apache-2.0），生成标准的 IC tearsheet 和风险指标。

**要创建/修改的文件**：
- `src/aionis/track_b/alphalens_adapter.py`（新建）—— alphalens 接口
- `scripts/track_b_tearsheet_run.py`（新建）—— tearsheet 生成脚本

**验收标准**：
- [ ] alphalens 因子分析：IC/IR/分位数收益/ turnover
- [ ] pyfolio 风险指标：beta/Fama-French exposure/最大回撤
- [ ] 输出 HTML/PDF tearsheet（或 Streamlit 集成）
- [ ] 与手写 `rank_ic.py` 的 IC 值交叉校验
- [ ] 单元测试：已知数据的 tearsheet 稳定性

**前置依赖**：S1-M①（需要 score + forward_return）

**反泄漏不变量**：
- `prices` 输入严格不含当日因子值（否则前瞻泄漏）
- `period/freq` 对齐：日频 → 月频 IC 的聚合方式正确
- 分位数组合的再平衡日期严格 PIT

**挂接 OSS**：
- `alphalens-reloaded`（Apache-2.0）—— 因子 IC 诊断
- `pyfolio-reloaded`（Apache-2.0）—— 风险 tearsheet
- 参考：`zipline-reloaded`（Apache-2.0）—— 备用 Pipeline 引擎

**许可证确认**：
- 两者均为 Apache-2.0（✅ permissive）

---

### 3.5 S1-M③：FF5 残差风险因子挂接（M=Medium）

**目标**：实现 Fama-French 五因子残差回归，将选股策略的收益分解为"alpha + FF5 beta"。

**要创建/修改的文件**：
- `src/aionis/track_b/ff5_residual.py`（新建）—— FF5 回归
- `src/aionis/ingest/fama_french.py`（复用 S0-S③）—— FF5 数据

**验收标准**：
- [ ] 策略收益序列 vs FF5 五因子的滚动回归（月频）
- [ ] 输出：alpha（截距）、五个 beta 系数、R²、t 统计量
- [ ] Newey-West HAC SE 应用
- [ ] 单元测试：已知回归的系数稳定性

**前置依赖**：S0-S③（FF5 数据就绪）+ S1-L①（策略收益序列）

**反泄漏不变量**：
- FF5 因子值的日期严格"发布时可用"（vintage 纪律）
- 回归窗口不包含未来数据

**挂接 OSS**：
- `statsmodels`（BSD）—— OLS 回归
- `pandas-datareader`（BSD）—— Kenneth-French 数据

---

### 3.6 S1-S①：市场结构流动性/借券容量挂接（S=Small）

**目标**：实现基础的流动性/借券容量指标，作为市场结构的入门分析。

**要创建/修改的文件**：
- `src/aionis/track_b/market_structure.py`（新建）—— 流动性指标
- `src/aionis/ingest/market.py`（复用）—— 成交量数据

**验收标准**：
- [ ] 流动性指标：平均日成交额/ Amihud 非流动性比率
- [ ] 借券容量：基于做空成本的估计（数据源待定）
- [ ] 与 FINSABER 的 capacity 估计交叉校验
- [ ] 单元测试：指标计算正确性

**前置依赖**：S1-L①（FINSABER capacity 参考）

**反泄漏不变量**：
- 流动性指标的计算窗口严格 PIT
- 借券成本使用"发布时可用"的数据

**挂接 OSS**：
- 待定（借券数据无免费源，可能需要 stub 或付费备份）

---

## 4. 新闻情绪（主题④）的延后理由

### 4.1 为什么留最后

前沿共识（Profit Mirage / Alpha Illusion / Lopez-Lira 2025）强烈警告：**LLM-trading alpha 多为泄漏 artifact**。

- **Profit Mirage**（arXiv 2510.07920）：51–62% Sharpe 衰减 —— LLM alpha 在受控 ablation 下大幅缩水
- **Alpha Illusion**（arXiv 2605.16895）：P1–P6 报告协议 —— 记忆泄漏是系统性问题
- **Lopez-Lira et al. 2025**：即便 structural-only 抽取（无 `market_impact`），LLM 参数仍残存训练期市场记忆

### 4.2 低泄漏入口（E3 闭集抽取）

轨道 B 的新闻情绪只通过以下受控入口进入：
- **E3 闭集 13D/8-K 抽取**：仅限有 filing-date PIT 的事件类型
- **RD-08 zero-LLM baseline**：作为 ablation 对照，禁止 LLM 推理
- **RD-04..07 gold set**：人工标注的 golden set，校准抽取器

### 4.3 只作受控 ablation

新闻情绪的定位：
- **不作主 alpha**：只作为 S3 的增量检验，不进入 S0/S1
- **受控 ablation**：通过 neutral-text / shuffled-date 控制门验证提升是否消失
- **PiT 记忆审计**：使用 FINSABER + Look-Ahead-Bench 的记忆子门检验

---

## 5. 切片依赖图与建议执行顺序

```
S0-M (现有能力盘点) ──────┐
   ├─ S0-S① (PIT Universe 验证)
   ├─ S0-S② (PIT 基本面扩展)
   ├─ S0-S③ (宏观/因子组合挂接)
   └─ S0-L (横截面 Panel PIT 对齐与幸存者屏蔽)
         │
         ├─────────────────────────────────────┐
         │                                     │
S1-M① (price-only baseline 训练管道)    S1-M② (等权 baseline + DM 检验)
   │                                     │
   ├─ S1-L① (FINSABER 净成本回测挂接) ──┤
   ├─ S1-L② (alphalens/pyfolio 挂接) ────┤
   ├─ S1-M③ (FF5 残差风险因子挂接) ─────┤
   └─ S1-S① (市场结构流动性/借券挂接) ──┘
```

### 建议执行顺序

1. **Wave 0（规划）**：S0-M → 产出复用清单表 → owner 裁断模糊点
2. **Wave 1（数据脊柱）**：S0-S① → S0-S② → S0-S③ → S0-L（串行，依赖链）
3. **Wave 2（price-only baseline）**：S1-M① → S1-M②（可并行）
4. **Wave 3（回测/风险挂接）**：S1-L① + S1-L② + S1-M③ + S1-S①（可并行，都依赖 Wave 2）

### 预估工作量（粗略）

| 切片 | 规模 | 预估工时 | 风险 |
|---|---|---|---|
| S0-M | M | 4–6 h | 低 |
| S0-S① | S | 2–3 h | 低 |
| S0-S② | M | 8–12 h | 中（XBRL 标签多样性） |
| S0-S③ | S | 4–6 h | 低（复用现有） |
| S0-L | L | 16–24 h | 高（PIT 对齐泄漏面大） |
| S1-M① | M | 8–12 h | 中（价格特征工程） |
| S1-M② | M | 6–8 h | 低 |
| S1-L① | L | 20–30 h | 中（适配复杂度） |
| S1-L② | L | 16–24 h | 中（tearsheet 稳定性） |
| S1-M③ | M | 6–8 h | 低 |
| S1-S① | S | 4–6 h | 中（数据源不确定） |

**总计**：约 90–140 工时（纯实施，不含规划/审查/调试）

---

## 6. 风险与开放问题

### 6.1 幸存者偏差：可缓解不可根除

**裁决**（v0.2 §8.4）：
- **主源** `hanshof/sp500_constituents`（MIT，日频 1996+）—— 历史部分来源不透明
- **交叉校验** `pierrebrunelle/sp500-historical-constituents`（MIT，月频 2016+）—— 可复现
- **显式排除** Russell 策略（无免费 PIT 数据）
- **显式声明** 退市股收益缺失

**论文诚实措辞**：
> *"S&P 500 成分用重建 PIT 控制；退市股收益缺失 + 无免费 Russell PIT 数据，使结果是抗幸存信号的**保守上界**，而非完全干净估计。"*

### 6.2 qlib Yahoo 数据必须换掉

**问题**：qlib bundled Yahoo 数据包含：
- 非 PIT 成分（今天的 500 回测过去）
- 非 adj-close 价格
- 无退市股

**改造点 ①**（v0.2 §6 层 0）：
- 用 Tiingo/Alpaca 替换 qlib 的数据源
- 或 fork qlib 的 `qlib.data` 模块，接自定义数据提供器

### 6.3 FINSABER 适配复杂度

**风险点**：
- FINSABER 的输入格式可能与 Aionis 的 Panel 结构不匹配
- next-open 执行时间需要精确对齐 NYSE calendar
- LLM 成本模块在 S1 可 stub（E3 再接入）

**缓解措施**：
- 先写单股单期模拟测试，验证成本计算
- 与现有 `strategy_returns.py` 的 gross 回测交叉校验

### 6.4 借券数据无免费源

**问题**：
- 无免费的美股做空成本数据（WRDS/Markit 付费）
- `ShortInterest` 数据延迟（月度 T+2）

**缓解措施**：
- S1-S① 先实现 stub（固定成本假设）
- 论文显式声明"借券成本未建模"或使用保守估计

### 6.5 FF5 因子 vintage 纪律

**问题**：
- Kenneth-French 数据库是"当前最新值"，无 historical vintage
- FF 因子的修订历史未公开

**缓解措施**：
- 验证 FF5 因子的修订幅度（历史数据对比最新值）
- 如修订显著，在论文中声明为"潜在泄漏源"

---

## 7. 需 owner 裁断的关键点

### 7.1 目标裁断（最优先）

**问题**：是 (A) 收敛为"窄 harness + 发表 null"（轨道 A），还是 (B) 推进为"v0.2 七主题选股平台"（轨道 B），还是 (A+B) 双轨？

**当前状态**：两套叙事并存，精力在"窄化审计"与"宽化蓝图"间摆动。

**建议**：先裁断目标，再决定 S0/S1 实施优先级。

---

### 7.2 qlib 脚手架 vs 纯 library 拼装

**问题**：v0.2 §6 层 0 建议 fork `qlib` 当脚手架（4 个手术点），但 4 个改造点的复杂度可能超过纯 library 拼装。

**选项**：
- **A**：fork qlib，执行 4 个手术点（ PIT-DB dump_bin / ERL 挂 / purgedcv 折注入 / RecordTemp 链）
- **B**：纯 library 拼装（`bt` + `alphalens` + `pyfolio` + `purgedcv`），不 fork qlib

**建议**：先跑一个"最小 qlib scaffold POC"，验证 4 个手术点的工时，再决定 A/B。

---

### 7.3 hanshof Universe 信任阈值

**问题**：hanshof 与 pierrebrunelle 的月度 Jaccard 重合度如果 < 0.95， headline 是否限制到 2016+ 窗口？

**选项**：
- **A**：信任 hanshof 全量（1996+），Jaccard 只作敏感性报告
- **B**：headline 限制到 2016+（pierrebrunelle 可复现窗口），1996–2016 只作敏感性

**建议**：等 S0-S① 审计结果后再裁断。

---

### 7.4 FINSABER LLM 成本模块在 S1 的处理

**问题**：S1 是 price-only baseline，不应包含 LLM 成本，但 FINSABER 的成本模块可能强依赖 LLM 调用记录。

**选项**：
- **A**：S1 stub LLM 成本为 0（price-only 无 LLM）
- **B**：S1 先接入成本模块接口，E3 再喂真实数据

**建议**：选 A（S1 stub），E3 再接真实数据。

---

### 7.5 回测/风险覆盖优先级

**问题**：是否授权一条新预注册线，把"⑥回测净成本 + ⑤风险"作为轨道 B 的第一个 S1 切片？

**选项**：
- **A**：优先 S1-L①（FINSABER）+ S1-L②（alphalens/pyfolio）—— ROI 最高
- **B**：优先 S0（数据脊柱）—— 地基优先

**建议**：地基优先（S0），但 S1-L①/L② 可与 S0 并行（都依赖 Tiingo/Alpaca 价格）。

---

## 8. 适用边界与不越界声明

- `[F]` 本规划**未运行任何 confirmatory/strategy/horizon/forward 脚本、未观察任何 outcome、未改任何冻结面或 ledger**。
- `[I]` 本计划是研究建议；owner 未裁决前，不构成项目方向变更。
- `[F]` 轨道 B 的任何落地都是**新预注册 + 新 config + 新 ledger row**，绝不静默修改 B/C/D/E1。
- `[F]` "可缓解不可根除"的幸存者偏差（无免费 Russell/退市 PIT 数据）依然成立（v0.2 §8.4）。

---

## 9. 引用

### 内部来源
- [`docs/quant-selection-research.md`](../docs/quant-selection-research.md) v0.2 — 横截面选股范围切片 + 轮子栈 + 数据解锁
- [`reports/2026-08-02-strategic-review-coverage-and-alignment.md`](../reports/2026-08-02-strategic-review-coverage-and-alignment.md) — 战略复盘，轨道 B 五步
- [`state/current.md`](../state/current.md) + [`state/handoff.md`](../state/handoff.md) — 当前状态

### 外部（OSS 轮子）
- `microsoft/qlib`（MIT，46.9k★）—— 横截面选股框架
- `waylonli/FINSABER`（Apache-2.0，KDD 2026）—— 净成本回测 harness
- `alphalens-reloaded` + `pyfolio-reloaded`（Apache-2.0）—— IC/tearsheet
- `eslazarev/purgedcv`（MIT）—— PurgedGroupKFold + DSR/PBO
- `hanshof/sp500_constituents`（MIT）—— PIT S&P 500 成分
- `pierrebrunelle/sp500-historical-constituents`（MIT）—— 月度 PIT 成分交叉校验

---

**文档结束**
