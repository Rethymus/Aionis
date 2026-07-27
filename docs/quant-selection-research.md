# 《量化选股策略研究》— Aionis 研究范围（v0.2）

> 本文把 TCR/Kernel 的**表示思想 + 反泄漏 + 可证伪**纪律保留，把研究目标收缩到一个
> 具体、可证伪、个人可做的 vibe-coding 项目：**横截面量化选股**（rank stocks → 分
> 位数组合 → leakage-aware 回测）。是 `theory-of-computable-reality.md`（理论上层）
> 与 `frontier_positioning.md`（前沿定位）的**落地范围切片**，不是新理论。
>
> 状态：**v0.2（2026-07-27）**——轮子栈 / 前沿 / 数据三节经 4 个并行研究 agent 实测回填
> （`gh api` 核验 license / star / 活跃度）；新增「整项目改造层」（`qlib` 脚手架 + 4 改造点）
> 与「抗幸存者 universe」裁决（§8.4）。验证仍 **pending powered n + 预注册冻结配置**。

---

## 0. 一句话

用 firm-level（Entity/State）+ 事件文本（Event/ERL）+ 关系（Relationship）构造的统一
状态特征，在**横截面**上选股；问：能否 OOS 显著优于 price-only / 等权 baseline，且在
neutral/shuffled 控制门下提升消失，并通过 purged CV + Deflated Sharpe/PBO 多重检验。

---

## 1. 研究问题（单一预注册、可证伪 claim）

> 从统一状态特征打分选出的 **top-quantile 组合**，其未来 $h$ 日收益（或 long-short
> spread）是否 OOS 显著优于 (a) price-only 同模型、(b) 等权 baseline；且提升在
> neutral-text / shuffled-date 控制门下消失；并通过 Deflated Sharpe / PBO 多重检验。

null 仍是下注热门；CI 跨 0 / 控制门不消失 = 合法的否定结论。

---

## 2. 范围切线（IN / OUT）

**IN**
- 横截面选股（cross-sectional ranking），不是单资产择时。
- firm-level 特征（PIT 基本面 = Corporate Vital Signs）。
- 事件/文本信号（ERL，复用现有抽取栈）。
- PIT 纪律、purged CV、cluster-robust inference、复用开源轮子。
- 日频/周频再平衡、$h$ 先钉一个值。

**OUT（明确不做）**
- 高频、衍生品、加密。
- learned generative world model（per `frontier_positioning.md` §2C：100M+ token、+7
  Sharpe 泄漏）。
- 全市场实时、Tick 级。
- 多 horizon 扫描（先钉 $h$，避免多重检验膨胀；`harvey-liu haircut` 兜底）。
- 心理诊断式 CEO 画像（只做 DSP from observable behavior）。

---

## 3. TCR → 选股 的映射（表示思想保留）

| TCR 原语 | 选股落点 | 数据源（待 data agent 定） |
|---|---|---|
| **Entity** | 单只股票 / 公司 | ticker；PIT universe 成员资格 |
| **State** | Corporate Vital Signs（PIT 基本面）+ 市场状态 | SEC EDGAR/XBRL、Sharadar SF1、SimFin |
| **Event** | ERL（事件文本，复用现有栈） | FOMC/BLS 一手文本 + ERL 缓存 |
| **Relationship** | 供应链 / 资金流 / 同业博弈（后期 phase） | 13F、供应链披露、GICS 同业 |
| **可证伪锚点** | top-quantile 收益 / long-short Sharpe / IC | 日频价（无 key 源） |

> 选股与当前 "event-window ETF return" 是**不同目标**：现有 pipeline 是事件冲击归因；
> 选股是横截面 rank。**事件/ERL 降格为"一个信号源"，不再是整个目标。**

---

## 4. 沿用的纪律（不可妥协；来自 TCR §4 + 现有代码）

1. **PIT 硬边界 $I_t$**：任何特征是 $t$ 可得信息的函数；`alignment.py` 断言保留。
2. **structural-only 抽取**：ERL 不取 `market_impact`；选股同样不把未来收益/未来排名漏进特征。
3. **控制门**：neutral-text / shuffled-date —— 提升必须消失；复用 `eval/controls.py`。
4. **purged + embargoed CV**：`purgedcv`；按群组（date 或 firm-cluster）。
5. **cluster-robust inference**：HLN DM + moving-block-bootstrap（`metrics.py`）。
6. **多重检验审计**：Deflated Sharpe + PBO；`harvey-liu` haircut 兜底 sector×horizon。
7. **determinism test**：`tests/test_determinism.py`（本轮已加）——避免重蹈 Phase-A 分布覆辙。
8. **预注册 + run ledger**：每个 stage 的主对比冻结后才解盲；所有配置进 `runs/ledger.jsonl`。

> **第一性警示（PIT universe）**：横截面选股的最大泄漏面是 **universe 成员资格的
> 幸存者偏差**（用今天的 S&P 500 成分回测过去 = 系统性高估）。无 CRSP 这类付费 PIT
> 成分数据时，必须用 PIT 成分（或坦诚声明 survivorship 未完全控制、保守结论）。这是
> 无 key 选股的结构性硬问题——**裁决见 §8.4**。

---

## 5. 最小研究循环（vibe-coding loop）

```
无 key 日频价 + PIT 基本面（轮子）
      ↓
universe（PIT 成员）+ 特征（State + Event/ERL）
      ↓
PIT 对齐（features ≤ t_info；label = [t, t+h] 收益）
      ↓
purged CV 打分（cross-sectional rank model）
      ↓
分位数组合回测（轮子；PIT 再平衡，不复用未来）
      ↓
IC / Sharpe / turnover / Deflated Sharpe / PBO + neutral/shuffled 门
      ↓
run ledger + 报告
```

每一圈是一个 falsifiable slice；每加一类特征（State → +Event → +Relationship）都是
**在同一个 benchmark 上的增量预注册对比**，不是新实验。

---

## 6. 轮子栈（reuse + 改造，不造轮子）

> 用户要求：**尽可能复用 / 在开源项目基础上改造**，试错成本最低。故分两层——
> **层 0「整项目层」**：fork+改造整个框架当脚手架；**层 1「library 层」**：按数据流 import 零件。
> 全 permissive、全 maintained，每条带**选股特有的泄漏 gotcha**（实测 2026-07-27，`gh api` 核验）。

### 层 0 · 整项目层（fork + 改造）

| 项目 | license | ★ | 活跃 | 用法 / 改造点 / 陷阱 |
|---|---|---|---|---|
| **`microsoft/qlib`** | MIT | 46.7k | 2026-07 | **当脚手架 fork**：PIT-DB（2022-03 起内置）+ Alpha158/360 + ML + 回测 + YAML 流，本就为横截面选股造。**4 个手术点**：①edgartools as-filed `dump_bin` 成二进制布局、**时间戳钉 filed-date**（非 period-end）→ PIT-DB 保证算子层读不到未申报值；②ERL structural-only 事件表挂申报日当 static field（key 在 filed-date → 不漏市场反应）；③子类化 `qlib.data.dataset.DatasetH`，把默认纯时间 `segments` 换成 `purgedcv` 折索引，逐折训练 → 折级预测喂 HLN-DM/MBB；④`RecordTemp` 链（`SignalRecord→SigAnaRecord→PortAnaRecord`）插自定义 `ControlGateRecord`（neutral/shuffled + 确定性 + DSR/PBO）。**致命陷阱**：`RobustZScoreNorm`/`CSZScoreNorm`/`Fillna` 的 `fit_start_time`/`fit_end_time` 必须钉在折内训练段——漏配=全面板 fit=**静默泄漏**（示例 config 正确钉了，fork 务必保留）。bundled Yahoo 数据必须整体换成 Tiingo/Alpaca PIT universe（含退市）。 |
| `stefan-jansen/machine-learning-for-trading` (3ed) | MIT | 20k | 2026-07 | **配方参考库**（purged CV / HLN-DM / DSR-PBO 的实现照抄），非统一 PIT 管线——**只搬技术不搬章**（书代码为教学常在全面板上 fit scaler）。 |
| `microsoft/RD-Agent` | MIT | 14k | 2026-07 | **后期倍增器**：LLM 驱动自动因子/模型迭代。S2+ 再上，不作地基。 |

### 层 1 · library 层（按数据流分组）

| 角色 | 轮子 | license | 泄漏 gotcha / 注 |
|---|---|---|---|
| 回测（横截面） | `bt` | MIT | 权重 shift 1；别把当日 close 同时当执行价 |
| 因子/IC 诊断 | `alphalens-reloaded` + `pyfolio-reloaded` | Apache | 前瞻收益来自 `prices`——别把当日 close 同时当因子和 prices；`period/freq` 对齐 |
| 回测引擎（备） | `zipline-reloaded` | Apache | 用 `Pipeline`+`as_of_date` 才 PIT-safe；ad-hoc `data.current` 会漏。qlib 执行器太粗时上 |
| **CV + 多重检验** | **`purgedcv`**（eslazarev） | MIT | **唯一折生成器**：`PurgedKFold`/`PurgedGroupKFold`/`CPCV`/`reconstruct_paths`/`DSR`/`PBO`/`PSR`/`MinBTL` 全在。必须传 event_times；所有下游模型共用同一组折 |
| 多重检验补充 | `arch.bootstrap`(SPA+MCS+StepM+RealityCheck) · `mnemox-ai/deflated-sharpe` · `YannickKae/Evaluating-Investment-Strategies`(haircut) | BSD/Apache/CC0 | SPA/MCS 喂**全部试过**的 loss（含丢弃）；DSR 的 N 必须计**所有**看过的 config |
| 因果 | `DoubleML` + `econml` · `synthdid`(R) | BSD/MIT/BSD | **必须 `set_sample_splitting(PurgedKFold)` / `cv=PurgedKFold`，禁用默认 KFold**；synthdid 走 rpy2 |
| ML 基学习器 | `lightgbm`（+xgb 交叉校验） | MIT/Apache | `y` PIT shift；`asset_id` 勿当 categorical（背名字） |
| 基本面 PIT | `edgartools` | MIT | XBRL 2009-11 渐进强制；小盘 pre-2011 稀疏（已用） |
| 宏观/因子 | `pandas-datareader` | BSD | FRED 会修订→钉 ALFRED vintage（已用） |
| 价格 | Tiingo→Alpaca→yfinance→Stooq | — | adjClose 已复权；priority 降级（已接入 `fetch_prices`） |
| **universe（PIT 抗幸存者）** | **`hanshof/sp500_constituents`** + **`pierrebrunelle/sp500-historical-constituents`** | MIT | **新增、关键**——见 §8.4 |
| 基线校准数据 | GKX `datashare.zip` | 公开下载 | 无 key，~94 特征 × ~30k 股月频 |
| 泄漏审计 | `waylonli/FINSABER`(KDD2026) + Look-Ahead-Bench 方法 | Apache / 重写 | FINSABER 当 harness（执行时点/滑点/流动性/LLM 成本）；Look-Ahead-Bench 的 P1/P2 alpha-decay **重写不 vendor**（仓库无 LICENSE） |
| LLM-金融数据 | `FinGPT` · `FNSPID` | MIT / CC BY-NC | FNSPID 非商用+未预 join+**PIT 自强制**；FinRL 只复用基建、换掉 yfinance |
| 实验 ledger | `mlflow`（local） | Apache | 自记 bundle hash + ALFRED vintage |
| 报告 | `great-tables` / `quantstats` | MIT/Apache | `quantstats` annualize `period` 对齐 |

### 显式排除 / 无可用代码

- **license 墙**：`vectorbt`(Commons Clause)、`backtrader`(GPL+停更)、`mlfinlab`(已收费/"Other")、`nautilus_trader`(LGPL)、`pypbo`(AGPL→可重写~100行)、`alphagen`/`yli188/WorldQuant_alpha101_code`(无 LICENSE=all-r)、`fastquant`/`qstrader`(停更)、`QuantConnect/Lean`(Apache 但 C# 核心，Python 改造成本高)、`xiubooth/ML_Codes`(无 LICENSE + 仅 MATLAB)、OpenBB 的 yfinance provider（被封）。
- **无公开代码**（照论文实现，引擎用 `DoubleML`/`econml`/`synthdid`）：Feng-Giglio-Xiu《Taming the Factor Zoo》、Goldsmith-Pinkham-Lyu 2025、GKX autoencoder（2020）。Profit Mirage（benchmark 无 URL）、Alpha Illusion（仓库 404）、`khrapovs/mcs`(404)。

> **备份与健康度**（用户要求）：每个轮子是 GitHub repo——记 `repo + 最后提交/版本 + license` 到 §8 注册表，配 `scripts/health_check.py` 定时探活（见 §8.3）。任一仓库停更→pin 最后可用 commit 或切备份。

---

## 7. 前沿技术采纳清单（2020-2026，agent 调研 + gh 核验）

**Top 5（采纳，按杠杆排序）**

1. **Feng-Giglio-Xiu Double-ML「Taming the Factor Zoo」(JFE 2020)** — 预注册主因子检验：高维 Double-ML 判断候选因子在 SDF 上是否有增量。**无官方公开代码** → 照论文实现，引擎 `DoubleML`/`econml`（折须包 `PurgedKFold`）。`doi.org/10.3386/w25481`
2. **Synthetic DiD（Arkhangelsky 2021 AER + Goldsmith-Pinkham-Lyu 2025 金融事件研究）** — 面板因果估计器，把 ALFRED macro-surprise 推广到事件冲击横截面归因。`synthdid`（**仅 R、BSD**，走 `rpy2` 或移植凸加权）；GKP-Lyu 2025 **无公开代码** → 照论文实现。`doi.org/10.1257/aer.20190159`
3. **LLM 抽取（ERL）泄漏审计套件** — `FINSABER`（**arXiv 2505.07078**，KDD 2026，**有代码** `waylonli/FINSABER` Apache-2.0）当 harness；`Look-Ahead-Bench`（arXiv 2601.13770）的 in-sample P1 vs 后-cutoff P2 alpha-decay 当**记忆子门**（其仓库 `benstaf/lookaheadbench` 无 LICENSE → **重写方法不 vendor**）；`Alpha Illusion`（arXiv 2605.16895）P1–P6 报告协议当 checklist（**仓库 404，无可用代码**）；Profit Mirage（arXiv 2510.07920）宣布发 benchmark 但**无 URL**。
   > ⚠️ v0.1 此处 arXiv ID 与名称错位（2601.13770 误标 Alpha Illusion、2605.16895 误标 FINSABER），v0.2 已订正。
4. **Filing embeddings（10-K Doc2Vec PV-DM）+ FinGPT/FNSPID** — PIT-locked 替代数据特征。时间戳干净（filing/announcement）、无监督、笔记本可跑。轮子 `gensim`、`FinGPT`(MIT)；`FNSPID`(CC BY-NC，PIT 自强制)。
   > ⚠️ v0.1 推的 `CentralBankRoBERTa` **无 LICENSE（all-rights-reserved）+ 1.5 年停更**，v0.2 降级、不 vendor；改以 `FinGPT`/`FNSPID` 为 LLM-金融数据骨干。
5. **Harvey-Liu haircut Sharpe + Profit Hurdle** — 补全多重检验。Python haircut 端口 = `YannickKae/Evaluating-Investment-Strategies`（CC0 公共领域，仅 haircut）；Profit Hurdle 可照 MATLAB 移植。与已用 `purgedcv` 的 DSR/PBO 配对 → **每个 Sharpe 带 deflated + haircut + PBO 三联**。`people.duke.edu/~charvey/backtesting/`

**显式跳过 / 缓**

- **TS foundation models（Chronos/Moirai/TimesFM）作主 alpha**：2025-26 多项研究显示 OOS R² 为负、输给 LightGBM、微调无益（方向 robust；**精确 R² 数查不到对应公开 benchmark 仓库** → 本项目面板自算后引用，勿引孤数）。**只作波动率/风险或辅助特征**，不作主信号。
- **Autoencoder factor models（GKX 2020/2021）**：官方代码 `xiubooth/ML_Codes` **无 LICENSE + 仅 MATLAB** → 不可 vendor；此规模下增量 R² 不明，缓。
- **LLM multi-agent 辩论选股（TradingAgents/MarketSenseAI 等）**：发表 alpha 多为 artifact（Alpha Illusion / FINSABER / Profit Mirage）；**不作主 alpha**，只采纳其审计协议（= 第 3 条）。

**已确认复用**：`purgedcv`（`github.com/eslazarev/purged-cross-validation`，MIT、活跃、JOSS 论文，含 DSR/PBO/CPCV/path-reconstruction，已核实全在）；GKX 公开月度面板（`dachxiu.chicagobooth.edu`，无 key）作基线校准。

> 注：前沿**共识**与本项目立场一致——"LLM + 因果 + 新闻"栈是泄漏重灾区；价值在**审计与纪律**，不在堆模型。与 §4 反泄漏纪律、`frontier_positioning.md` §2C 的"defer learned world model"对齐。

---

## 8. 数据解锁（实测 + 注册表 + 健康度）

**实测（2026-07-27，本出口）**：`yfinance`/Yahoo 429；Stooq 逐 symbol HTML+"Access denied"；Stooq bulk 401 Basic；**akshare/East Money `RemoteDisconnected`×3**（agent 之前声称可达但**本会话不复现**，视为 flaky/未确认）。**EDGAR、FRED、GitHub（`git clone` + `github.com/<repo>/raw/`）实测可达**；`raw.githubusercontent.com` + `codeload.github.com` 超时（所以走 clone 或 `github.com/.../raw/` 重定向，**不**直接拉 raw 主机）。

### 8.1 数据源注册表（primary + 备份 + PIT + 仓库）

| 数据类型 | 主源（实测） | 备份 | PIT-clean? | GitHub wheel / 仓库 |
|---|---|---|---|---|
| **价格（横截面日频）** | ✅ **Tiingo**（免费 token，实测可达；stocks + ETFs 含 SPY/行业 ETF） | ✅ **Alpaca**（实测可达，独立 host，adj close 与 Tiingo 同值交叉验证）；yfinance（备） | adjClose 已复权；universe 幸存者偏差见 §8.4 | `_from_tiingo`/`_from_alpaca` 已接入 `fetch_prices`（主→备自动降级） |
| **基本面（PIT）** | ✅ **SEC EDGAR XBRL**（`data.sec.gov`，实测 200；10k+ ticker→CIK；AAPL 144 as-filed facts） | SimFin free（~2400 名，免费注册，**需 key**） | **as-filed → PIT by construction** | `dgunning/edgartools`（MIT，2.5k★） |
| **宏观** | ✅ FRED / ALFRED（实测 200） | — | 钉 ALFRED vintage | `pydata/pandas-datareader`（BSD） |
| **因子组合** | ✅ Fama-French bulk ZIP（Tuck，非 Yahoo） | — | 是 | `pydata/pandas-datareader` |
| **universe 成分（PIT）** | ✅ **`hanshof/sp500_constituents`**（日频 1996+，MIT；**fork + 审行数**） | `pierrebrunelle/sp500-historical-constituents`（月频 2016+ 可复现，交叉校验）；CRSP 付费 benchmark | **必须 PIT**——裁决见 §8.4 | `hanshof` + `pierrebrunelle` |
| **事件文本** | ✅ FOMC（federalreserve.gov 可达）；10-K（EDGAR） | — | 一手、发布时刻 | 复用现有 `ingest/event_text.py` |
| **wheel / 参考数据** | ✅ `git clone` + `github.com/<repo>/raw/`（实测可达） | pin 最后可用 commit | n/a | 各 wheel 仓库（见 §6） |

### 8.2 寻宝原则（用户要求）

- **GitHub 是 wheel + 参考数据 + auto-updated 静态数据的金矿**：universe 成分、symbol 列表（`rreichel3/US-Stock-Symbols` 实测 clone 成功，但**仅当前**=幸存者偏差源）、Fama-French、各 wheel 本身。
- **活价 GitHub bulk dump 很稀**（实测搜索未找到维护中的 US 横截面 dump）——活价仍优先 API wheel（Tiingo/Alpaca）。
- **每类数据 ≥2 个备份**；仓库停更→pin 最后 commit 或切备份。
- **礼貌第一**（用户强调）：所有抓取/搜索/探活**严格限速**——≥2s 间隔 + 指数 backoff，不短时高频请求（避免被当恶意访问；本会话的 gh EOF / East Money 断连部分源于此）。

### 8.3 健康度检查（定时 + 礼貌）

- `scripts/health_check.py`：对每个源（EDGAR / FRED / GitHub 仓库 / akshare / Alpaca）轻量探活（HEAD 或小 GET），**严格限速**；输出 JSON 报告（status / latency / 仓库最近提交日期 / 是否 drift）。
- 定时跑（cron，非高峰、低频），失败→告警 + 自动切备份；仓库最近提交漂移→标记 stale。
- 探活与抓取共享同一个"礼貌客户端"（限速 + backoff + 缓存），避免重复实现。

### 8.4 幸存者偏差裁决（#1 结构性风险）

实测（2026-07-27）：**无免费 Russell 1000/2000/3000 历史成分**（GitHub 0 命中，FTSE Russell 历史成分付费专有）；**无免费退市股价格历史**（仅付费 WRDS/CRSP 镜像）。即「**可缓解、不可根除**」：

- **主源** `hanshof/sp500_constituents`（MIT，日频 1996+，`sp_500_historical_components.csv`）——唯一免费日频 PIT 成分；**但历史部分来源不透明**（脚本只 append 今天、不能重建历史）→ **fork + 审行数/日期范围**再用。
- **交叉校验** `pierrebrunelle/sp500-historical-constituents`（MIT，月频 2016+，从 Wikipedia 增删可复现）。两者在 2016+ 重叠窗口**分歧大 → headline 回测限到 2016 后可复现窗口**。
- **显式排除** Russell 策略（无数据）；**显式声明**退市股收益缺失。
- **论文诚实措辞**：*"S&P 500 成分用重建 PIT 控制；退市股收益缺失 + 无免费 Russell PIT 数据，使结果是抗幸存信号的**保守上界**，而非完全干净估计。"*——比静默用今天 500 成分回测强得多。

> **价格门已关：Tiingo（实测可达，2026-07-27；key 在 `.env` 的 `TIINGO_API_KEY`）。** S0 数据脊柱可全量搭起：**EDGAR 基本面（PIT）+ Fama-French 因子组合 + FRED 宏观 + Tiingo 价格 + hanshof/pierrebrunelle PIT universe**。

---

## 9. 分阶段（每阶段一个预注册 claim；通过才进下一阶段）

| Stage | 表示 | 可证伪 claim（预注册） |
|---|---|---|
| **S0** 数据脊柱 | — | 无 key 价 + PIT 基本面 wheel 就绪；universe 幸存者偏差被显式处理或声明 |
| **S1** price-only 基线 | reversal/momentum | 建立"要 beat 的数"：price-only ML 选股 vs 等权，IC/Sharpe + DM |
| **S2** + State | + Corporate Vital Signs（PIT） | richer firm-level > price-only，同一 universe/h/CV，控制门消失提升 |
| **S3** + Event/ERL | + 事件/文本信号 | ERL 提供增量（超 +State），PiT 记忆审计通过 |
| **S4** + Relationship（后期） | + 供应链/资金流/博弈 | 关系结构提供增量 |
| **S5**（stretch） | TS foundation prior / causal | 表示先验或因果估计改善 OOS |

**Stage S0/S1 是当前地基修复的直接延续**：先把"无 key 数据 + price-only 基线"跑通，才能
谈 S2+。Phase-A 的教训（在 underpowered n 上调参 = 噪声里挑点）在这里复用为"每 stage
的 claim 必须在足量 n + 冻结预注册配置下检验"。

---

## 10. 与现有代码的关系

**复用**：`features/alignment.py`（PIT 脊柱）、`eval/cv.py`（purged CV）、`eval/metrics.py`
（DM + MBB + Deflated Sharpe/PBO）、`eval/pit_audit.py`、`eval/controls.py`（neutral/
shuffled 门）、`extraction/`（ERL + embedding cache）、`schema/erl.py`（structural-only）、
`tests/test_alignment.py` / `test_determinism.py`（泄漏 + 确定性门）。

**新增**（S0/S1）：
- 横截面 universe（PIT 成分）+ 无 key 价 ingest（替换/补充 `ingest/market.py`）。
- PIT 基本面 ingest（新，Entity/State；仿 `macro_surprise.py` 的 ALFRED-vintage PIT 纪律）。
- 分位数组合回测 + IC/Sharpe（轮子，替换/补充当前 `eval/compare.py` 的 DA-lift 评估）。

> 选股版不是推倒重来：现有 ERL-only event-impact 实验（Phase A）保留为一个**子结果**；
> 选股是它的**横截面泛化**。`WRL = ERL 严格超集` 的桥在这里同样成立。

---

## 11. v0.2 changelog（2026-07-27）

- ✅ **§6 轮子栈**：4 个并行研究 agent 实测回填（`gh api` 核验 license/star/活跃度），拆成**层 0 整项目层（`qlib` 脚手架 + 4 改造点 + 处理器 fit 陷阱）+ 层 1 library 层**；扩充实式排除/无代码清单。
- ✅ **§7 前沿**：订正 arXiv ID 错位（2601.13770=Look-Ahead-Bench、2605.16895=Alpha Illusion、FINSABER=2505.07078、2510.07920=Profit Mirage）；软化 TSFM R² 孤数（查不到对应公开 benchmark 仓库）；降级 `CentralBankRoBERTa`（无 LICENSE + 停更）。
- ✅ **§8 数据**：universe 行升级为 `hanshof`/`pierrebrunelle` PIT 主源；新增 §8.4 幸存者裁决（**可缓解不可根除** + 论文诚实措辞）。
- ⏳ **下一步**：S0 数据脊柱落地（fork `qlib` + PIT EDGAR `dump_bin` + `purgedcv` 折注入）——**待 Phase B 预注册 claim 冻结后动手**（遵 theory-design 模式，本步仅设计文档落盘，未碰代码）。
