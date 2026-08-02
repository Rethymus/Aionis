# 复用目录增补 v2 —— 七大主题选股管线（selection-pipeline）

> 日期：2026-08-02
> 状态：[`2026-08-01-reuse-catalog.md`](2026-08-01-reuse-catalog.md) 的**增补**（非重写）
> 判断：**需增补**——既有目录是 **dashboard v2 中心**（tearsheet/plotly 静态导出/E3 调度），未覆盖"七大主题选股管线"的轮子映射；本增补补齐该缺口 + 纳入 2026-08-02 新核实发现。
> 原则：permissive license ONLY（MIT/Apache/BSD）；每条带泄漏 gotcha。

## Delta 1 — 本次新核实发现（2026-08-02 WebFetch）

| 轮子 | 许可证 | 新核实事实 | 影响 |
|---|---|---|---|
| `stefan-jansen/machine-learning-for-trading` | MIT（3ed） | 含 **6 个生产级 Python 库**（非仅 notebook）：`ml4t-diagnostic`（独立包，DSR / walk-forward CV / BH-FDR / White Reality Check）/ `ml4t-data` / `ml4t-engineer` / `ml4t-models` / `ml4t-backtest` / `ml4t-live` | **升级定位**：从审计的"配方参考库"→"可 import 的诊断库"；`ml4t-diagnostic` 可作 DSR/特征验证的备选（与 `purgedcv` 互补） |
| `waylonli/FINSABER` | Apache-2.0（KDD 2026） | 已核实：`next_open` 默认执行 + `slippage_perc`/`slippage_impact` + `liquidity_cap_pct` + `finsaber.toolkit.llm_cost_monitor`；输出 `metrics.json`/`equity_curve.csv`/`trades.csv`/`llm_costs.csv`；集成 FinMem/FinAgent/FinCon/FinRL | **净成本回测（主题⑥）的主轮子**——见 [`wheel-mount-design-pack.md`](2026-08-02-wheel-mount-design-pack.md) §2 |
| `microsoft/qlib` | MIT | PIT-DB 2022-03 起；Alpha158/360；v0.9.0；46.9k★；2024-08 起 RD-Agent 集成 | 选股脚手架候选（fork vs library——见 [`qlib-fork-vs-library-poc.md`](2026-08-02-qlib-fork-vs-library-poc.md)） |
| `AI4Finance/FinGPT` | MIT | **无 PIT 月频横截面 IC 证据**；最新动态停于 2023 末；依赖 Yahoo（幸存者偏差风险） | **只作 NLP 骨干（embedding/抽取），不作选股 alpha**——与审计 §8.2 一致 |

## Delta 2 — 七大主题 → OSS 轮子映射（selection-pipeline 视角，既有目录未覆盖）

| 主题 | 主轮子（license） | 复用方式 | 泄漏 gotcha |
|---|---|---|---|
| **① 行情/价格** | Tiingo + Alpaca（已接 `ingest/market.py`） | 直接复用 `fetch_prices` | adj-close as-of 合同未冻结；退市价缺失（结构性） |
| **② 宏观** | `pandas-datareader`（BSD）FRED/ALFRED | 钉 ALFRED vintage（已实现 `ingest/macro_surprise.py`） | macro 会修订→必须 vintage |
| **③ 基本面** | `edgartools`（MIT）SEC EDGAR XBRL | filed-date PIT（已实现 `ingest/fundamentals.py`） | 用 filed 非 period-end；XBRL pre-2011 稀疏 |
| **④ 新闻情绪** | `FinGPT`（MIT，NLP 骨干）+ `FNSPID`（CC BY-NC） | **仅闭集抽取/embedding**，不作 alpha | LLM 参数记忆泄漏（Lopez-Lira 2025）；FNSPID 非商用 |
| **⑤ 风险** | `alphalens-reloaded` + `pyfolio-reloaded`（Apache） | tearsheet/IC/分位/drawdown（见挂接①） | `prices` 不含当日因子值 |
| **⑥ 回测净成本** | `FINSABER`（Apache） | next-open/slippage/liquidity/LLM-cost（见挂接②） | 执行=next-open；退市剔除 |
| **⑦ 市场结构** | `statsmodels`（BSD）+ `pandas-datareader`（FF5）+ Amihud(文献) | FF5 残差 + 非流动性（见挂接③） | FF 无 vintage（声明） |

## Delta 3 — CV / 多重检验轮子（深化既有目录）

既有目录未单独列 CV/多重检验的可复用实现。补齐：

| 角色 | 轮子（license） | 复用点 | 注 |
|---|---|---|---|
| purged CV + DSR + PBO + path-reconstruction | `eslazarev/purgedcv`（MIT） | `PurgedGroupKFold` / `CPCV` / `DSR` / `PBO`（Aionis 已依赖 `eval/cv.py` 封装） | 唯一折生成器；所有下游模型共用同一组折 |
| DSR / haircut 备选 | `ml4t-diagnostic`（MIT，3ed 独立包） | Deflated Sharpe / walk-forward / BH-FDR / White Reality Check | 与 `purgedcv` 的 DSR 互补验证 |
| SPA / MCS | `arch.bootstrap`（BSD） | `SPA` / `MCS` / `StepM` / `reality_check` | 喂**全部试过**的 loss（含丢弃） |

## Delta 4 — 显式排除（许可证墙，沿用 v0.2 §6）

`vectorbt`（Commons Clause）、`backtrader`（GPL+停更）、`mlfinlab`（收费）、`nautilus_trader`（LGPL）、`pypbo`（AGPL，可重写~100行）、`alphagen`/`WorldQuant_alpha101_code`（无 LICENSE）、`QuantConnect/Lean`（Apache 但 C# 核心，Python 改造成本高）、OpenBB 的 yfinance provider（被封）。

## 不越界声明

- 本增补是**研究参考**；不触冻结面/ledger/E3；未运行脚本；OSS 能力以 WebFetch + gh 核实为准，未臆断。
- 与既有 `2026-08-01-reuse-catalog.md` 互补（那个是 dashboard 中心，这个是 selection-pipeline 中心），不重复。
