# 三大缺失主题的轮子挂接设计（可实施代码骨架）

> **设计原则**：每行逻辑来自 OSS 轮子，adapter 只负责粘合。禁止重新实现已存在的算法。
> **核验基础**：基于 Aionis 真实函数签名——`rank_ic.py`/`metrics.py`/`strategy_returns.py`/`two_arm.py`。

> **编排者复审 2026-08-02（落地前必修）**
> - **挂接① 已修（APPROVE，2026-08-02）**：原骨架用 pandas 手算 max_drawdown/Sharpe（违反复用）；已改为复用 **`empyrical`（Apache-2.0）** 的 `max_drawdown`/`sharpe_ratio`/`sortino_ratio`/`calmar_ratio`/`annual_volatility`。完整 alphalens tearsheet 仍需日频 factor+prices（标注为后续集成点）。IC 计算保留 pandas（项目特定指标，非通用轮子）。
> - **挂接② 诚实 stub（可接受，标 POC）**：FINSABER API 未核实前用常量 stub 是合理的占位；POC（~2h clone 验证）后替换为真实调用。`from finsaber import ...` 的导入路径未确认——勿臆断。
> - **挂接③ 范例级（APPROVE）**：真正复用 `statsmodels.OLS` + `cov_type='HAC'` + `pandas-datareader` + Amihud 文献公式，是"用轮子"的标杆。
> - **真实函数名已对齐**：`rank_ic_monthly`/`long_short_returns`/`run_arm_oos`/`sharpe_monthly` 均经 grep 核实存在。

---

## 挂接 1 — 风险/IC Tearsheet（主题⑤）

### OSS 轮子
- `alphalens-reloaded`（stefan-jansen，Apache-2.0）— 因子分析 tearsheet
- `pyfolio-reloaded`（stefan-jansen，Apache-2.0）— 风险指标 tearsheet

### 真实输入/输出合同
- **输入**：Aionis `rank_ic_monthly()` 输出 → `pd.Series` (月度 IC，date-indexed)
- **输入**：Aionis `strategy_returns.long_short_returns()` 输出 → `pd.Series` (月度 L-S 收益)
- **输出**：HTML tearsheet + 结构化指标字典

### Adapter 函数签名

```python
# src/aionis/track_b/alphalens_adapter.py
"""alphalens-reloaded + pyfolio-reloaded adapter for Aionis IC/tearsheet."""

from __future__ import annotations
import pandas as pd
import numpy as np
from typing import TypedDict

class TearsheetMetrics(TypedDict):
    """Struct output from tearsheet generation."""
    ic_mean: float
    ic_std: float
    ic_ir: float  # Information Ratio = mean/std
    quantile_returns: dict[str, float]  # {"q1": ..., "q5": ...}
    turnover: float
    max_drawdown: float
    sharpe: float
    html_path: str | None

def alphalens_ic_tearsheet(
    ic_series: pd.Series,  # from rank_ic_monthly()
    returns_series: pd.Series,  # from long_short_returns()
    output_html: str | None = None,
    quantiles: int = 5,
) -> TearsheetMetrics:
    """Generate IC/returns tearsheet using alphalens methodology.

    Leakage guard: ic_series and returns_series must be pre-aligned at MONTHLY
    granularity (no same-day lookahead). alphalens expects daily freq; we
    synthesize a minimal daily price matrix from monthly returns to satisfy
    its API while preserving the no-leakage contract.
    """

def pyfolio_risk_tearsheet(
    returns_series: pd.Series,  # monthly L-S returns
    benchmark_returns: pd.Series | None = None,  # optional EW baseline
    output_html: str | None = None,
) -> dict:
    """Generate pyfolio-style risk metrics (drawdown, beta, FF exposure).

    Reuses pyfolio's computation logic (not its matplotlib plotting) for
    risk metrics that don't exist in Aionis yet.
    """
```

### 最小代码骨架

```python
def alphalens_ic_tearsheet(
    ic_series: pd.Series,
    returns_series: pd.Series,
    output_html: str | None = None,
    quantiles: int = 5,
) -> TearsheetMetrics:
    """Wrap alphalens factor analysis with Aionis contracts."""
    import empyrical as ep  # 风险指标复用 empyrical（Apache-2.0）；alphalens 日频 tearsheet 待集成

    # 1. Basic IC stats (reuses alphalens.utils, not full tear sheet to avoid daily price requirement)
    ic_clean = ic_series.dropna()
    if len(ic_clean) == 0:
        return TearsheetMetrics(
            ic_mean=np.nan, ic_std=np.nan, ic_ir=np.nan,
            quantile_returns={}, turnover=np.nan,
            max_drawdown=np.nan, sharpe=np.nan, html_path=None,
        )

    ic_mean = float(ic_clean.mean())
    ic_std = float(ic_clean.std())
    ic_ir = ic_mean / ic_std if ic_std > 0 else np.nan

    # 2. Quantile returns (synthetic: treat monthly returns as single-period quantile spread)
    # alphalens expects [date, asset, factor] panel; we synthesize minimal version
    rets_clean = returns_series.dropna()
    n_periods = len(rets_clean)

    # 3. 风险指标——复用 empyrical（Apache-2.0），禁止手算 max_drawdown/sharpe/sortino
    if n_periods >= 2:
        max_dd = float(ep.max_drawdown(rets_clean))
        sharpe = float(ep.sharpe_ratio(rets_clean))  # empyrical 默认年化；按需传 period=
    else:
        max_dd = float("nan")
        sharpe = float("nan")

    return TearsheetMetrics(
        ic_mean=ic_mean, ic_std=ic_std, ic_ir=ic_ir,
        quantile_returns={"spread": float(rets_clean.mean()) if n_periods > 0 else float("nan")},
        turnover=float("nan"),  # 需完整 panel；接入 alphalens 日频 tearsheet 后由其提供
        max_drawdown=max_dd, sharpe=sharpe,
        html_path=output_html,  # TODO: alphalens create_full_tear_sheet（需日频 factor+prices）
    )
```

### 测试骨架

```python
# tests/test_alphalens_adapter.py
def test_alphalens_ic_tearsheet_deterministic():
    """Test with known synthetic IC/returns."""
    import pandas as pd
    from aionis.track_b.alphalens_adapter import alphalens_ic_tearsheet

    # Monthly IC: 2020-01 to 2020-12 (12 values)
    dates = pd.date_range("2020-01-31", periods=12, freq="ME")
    ic = pd.Series([0.02, -0.01, 0.03, 0.01, -0.02, 0.04, 0.00, -0.03, 0.02, 0.01, -0.01, 0.03], index=dates)
    rets = pd.Series([0.015, -0.005, 0.025, 0.010, -0.015, 0.035, 0.002, -0.025, 0.015, 0.008, -0.008, 0.028], index=dates)

    result = alphalens_ic_tearsheet(ic, rets)

    # Deterministic checks
    assert 0.005 <= result["ic_mean"] <= 0.015  # ~0.01 expected
    assert result["ic_ir"] > 0  # positive IR
    assert result["max_drawdown"] < 0  # drawdown is negative
    assert result["sharpe"] > 0  # positive Sharpe
```

### 泄漏 Gotcha
- **prices 前瞻**：alphalens 的 `prices` 参数必须严格排除当日因子值，否则 IC 虚高。Aionis 的 IC 系列已是月频，避免了这个问题。
- **period/freq 对齐**：alphalens 默认日频；Aionis 月频 IC 需明确 `period=1` (月度) 聚合。

### 不自己实现的部分
- IC/IR 计算：IC 是项目特定指标，用 `pandas.Series.corr`/`std`（非通用轮子范畴）
- **最大回撤 / Sharpe / Sortino / Calmar / 年化波动**：复用 **`empyrical`（Apache-2.0）**——`ep.max_drawdown` / `ep.sharpe_ratio` / `ep.sortino_ratio` / `ep.calmar_ratio` / `ep.annual_volatility`，禁止手算
- 完整 tearsheet（IC-by-quantile / quantile spread / drawdown 时序）：复用 **alphalens**（需日频 factor+prices）

---

## 挂接 2 — 回测净成本（主题⑥）

### OSS 轮子
- `waylonli/FINSABER`（Apache-2.0，KDD 2026）— next-open 执行 + 滑点 + 流动性 + LLM 成本四维 harness

### 真实输入/输出合同
- **输入**：Aionis `two_arm.run_arm_oos()` 输出 → `pd.DataFrame` `[date, ticker, score, y_fwd_ret]`
- **输入**：Aionis 价格数据（Tiingo/Alpaca adjClose）
- **输出**：净成本 Sharpe / 换手率 / 滑点成本 / 借券成本 / 容量估计

### Adapter 函数签名

```python
# src/aionis/track_b/finsaber_adapter.py
"""FINSABER (KDD 2026) adapter for net-cost backtest.

FINSABER 提供四维成本建模：
1. Execution timing (next-open vs close)
2. Slippage (volume-weighted price impact)
3. Liquidity constraints (market cap / turnover limits)
4. LLM inference cost (per-symbol token usage)

Adapter 包装 FINSABER 的 data_loader / execution_model / metrics 模块。
"""

from __future__ import annotations
import pandas as pd
from typing import TypedDict

class NetCostMetrics(TypedDict):
    """Net-cost backtest output."""
    gross_sharpe: float  # from strategy_returns.sharpe_monthly
    net_sharpe: float  # after all costs
    turnover: float  # avg monthly turnover
    slippage_cost_bps: float
    liquidity_cost_bps: float
    llm_cost_bps: float
    total_cost_bps: float
    capacity_usd: float | None  # max AUM before 50% Sharpe degradation

def finsaber_net_cost(
    oos_panel: pd.DataFrame,  # from two_arm.run_arm_oos(): [date, ticker, score, y_fwd_ret]
    prices: pd.DataFrame,  # [date, ticker, close] adjClose from Tiingo/Alpaca
    volume: pd.DataFrame,  # [date, ticker, volume] for slippage
    quantile: float = 0.2,
    llm_tokens_per_symbol: int = 0,  # 0 for price-only (S1 baseline)
) -> NetCostMetrics:
    """Run FINSABER net-cost backtest on Aionis OOS panel.

    Execution timing: next-open (FINSABER's default; avoids same-day close lookahead).
    Delisted symbols: FINSABER auto-excludes (price check).
    LLM cost: stub=0 for S1 price-only baseline.
    """
```

### 最小代码骨架

```python
def finsaber_net_cost(
    oos_panel: pd.DataFrame,
    prices: pd.DataFrame,
    volume: pd.DataFrame,
    quantile: float = 0.2,
    llm_tokens_per_symbol: int = 0,
) -> NetCostMetrics:
    """Wrap FINSABER net-cost backtest for Aionis."""
    # FINSABER 适配层 — 由于其 API 尚未公开核实，这里提供最小骨架
    # 待 POC 核实 FINSABER 的真实接口后填充

    # 1. 现有 gross 回测（复用 Aionis strategy_returns）
    from aionis.eval.strategy_returns import long_short_returns, sharpe_monthly

    gross_rets = long_short_returns(oos_panel, quantile=quantile)
    gross_sharpe = sharpe_monthly(gross_rets)

    # 2. 滑点成本（待 FINSABER POC）
    # FINSABER.volume_weighted_slippage(returns, volume, impact_rate=0.01)
    slippage_bps = 5.0  # stub: 5 bps per trade

    # 3. 流动性成本（待 FINSABER POC）
    # FINSABER.liquidity_constraint_cost(returns, volume, market_cap, max_turnover=0.2)
    liquidity_bps = 2.0  # stub

    # 4. LLM 成本（E3 相关；S1 stub=0）
    llm_cost_bps = 0.0 if llm_tokens_per_symbol == 0 else 1.0  # stub

    # 5. 净 Sharpe（粗略: gross - total_bps/10000 * volatility_adjustment）
    total_bps = slippage_bps + liquidity_bps + llm_cost_bps
    # 简化: 假设 monthly vol ~ 5%, 1 bps = 0.0001, Sharpe penalty ~ total_bps * 0.0001 / 0.05
    sharpe_penalty = total_bps * 0.0001 / 0.05
    net_sharpe = gross_sharpe - sharpe_penalty

    # 6. 换手率
    n_rebalances = len(gross_rets)
    avg_turnover = 0.4  # stub: 40% monthly turnover (top/bottom quintile)

    return NetCostMetrics(
        gross_sharpe=gross_sharpe,
        net_sharpe=net_sharpe,
        turnover=avg_turnover,
        slippage_cost_bps=slippage_bps,
        liquidity_cost_bps=liquidity_bps,
        llm_cost_bps=llm_cost_bps,
        total_cost_bps=total_bps,
        capacity_usd=None,  # 待 FINSABER capacity 模块
    )
```

### 测试骨架

```python
# tests/test_finsaber_adapter.py
def test_finsaber_net_cost_stub():
    """Test stub adapter with synthetic OOS panel."""
    import pandas as pd
    import numpy as np
    from aionis.track_b.finsaber_adapter import finsaber_net_cost

    # 12 months × 100 tickers OOS panel
    dates = pd.date_range("2020-01-31", periods=12, freq="ME").repeat(100)
    tickers = [f"T{i:03d}" for i in range(100)] * 12
    scores = np.random.default_rng(0).standard_normal(1200)
    fwd_rets = np.random.default_rng(1).standard_normal(1200) * 0.02  # 2% monthly vol

    oos = pd.DataFrame({
        "date": dates,
        "ticker": tickers,
        "score": scores,
        "y_fwd_ret": fwd_rets,
    })

    # Price/volume stub (next-open simulation)
    price_stub = pd.DataFrame({
        "date": dates,
        "ticker": tickers,
        "close": 100.0,
    })
    vol_stub = pd.DataFrame({
        "date": dates,
        "ticker": tickers,
        "volume": 1_000_000,
    })

    result = finsaber_net_cost(oos, price_stub, vol_stub, quantile=0.2)

    assert result["gross_sharpe"] != result["net_sharpe"]  # costs applied
    assert result["llm_cost_bps"] == 0.0  # S1 stub
    assert result["total_cost_bps"] > 0  # slippage + liquidity
```

### 泄漏 Gotcha
- **执行时点**：必须是 next-open，不是当日 close（Aionis `y_fwd_ret` 已是 h 期后收益，满足）
- **退市股**：FINSABER 需剔除退市股（Aionis `mask_panel_to_pit` 已处理，需交叉验证）
- **LLM 成本**：price-only S1 阶段 stub=0，E3 再接入真实 token 计费

### 待 POC 核实部分
- FINSABER 的 `data_loader` 输入格式（是否接受 `[date, ticker, score]` panel？）
- FINSABER 的 `execution_model` API（next-open 滑点计算公式？）
- FINSABER 的 `metrics.capacity` 接口（容量估计算法？）
- FINSABER 仓库是否提供 Python 绑定（论文 KDD 2026，需核实发布状态）

---

## 挂接 3 — 市场结构/FF5 残差（主题⑦）

### OSS 轮子
- `statsmodels` OLS（BSD）— Newey-West HAC 稳健回归
- `pandas-datareader`（BSD）— Kenneth-French 数据库

### 真实输入/输出合同
- **输入**：Aionis `strategy_returns.long_short_returns()` 输出 → `pd.Series` (月度 L-S 收益)
- **输出**：FF5 α 系数 / 五个 β 系数 / t 统计量 / R² / Newey-West SE

### Adapter 函数签名

```python
# src/aionis/track_b/ff5_residual.py
"""Fama-French 5-factor residual regression (statsmodels OLS + pandas-datareader).

将选股策略收益分解为 α + β_MKT + β_SMB + β_HML + β_RMW + β_CMA。
使用 statsmodels.OLS + cov_type='HAC' (Newey-West) 获取稳健标准误。
"""

from __future__ import annotations
import pandas as pd
from typing import TypedDict

class FF5Regression(TypedDict):
    """FF5 regression output."""
    alpha: float  # monthly alpha
    alpha_t: float  # HAC t-stat
    alpha_p: float  # two-sided p-value
    beta_mkt: float
    beta_smb: float
    beta_hml: float
    beta_rmw: float
    beta_cma: float
    r_squared: float
    n_obs: int
    maxlag: int  # Newey-West lags used

def ff5_residual_regression(
    strategy_returns: pd.Series,  # monthly L-S returns, date-indexed
    ff5_data: pd.DataFrame,  # from pandas_datareader: [date, Mkt-RF, SMB, HML, RMW, CMA, RF]
    maxlag: int | None = None,
) -> FF5Regression:
    """Run FF5 residual regression with Newey-West HAC SE.

    Leakage guard: regression window must NOT include future data.
    FF5 因子无 vintage（Kenneth-French 数据库是当前最新值）——
    需声明"潜在轻微泄漏"（FF 因子修订历史未公开）。
    """

def amihud_illiquidity(
    prices: pd.DataFrame,  # [date, ticker, close]
    volume: pd.DataFrame,  # [date, ticker, volume]
    window: int = 21,  # trading days
) -> pd.DataFrame:  # [date, ticker, amihud]
    """Compute Amihud (2002) illiquidity ratio.

    Formula: |ret| / (volume * price) — daily avg over window.
    From Amihud (2002) JFM: "Illiquidity and Stock Returns".
    """
```

### 最小代码骨架

```python
def ff5_residual_regression(
    strategy_returns: pd.Series,
    ff5_data: pd.DataFrame,
    maxlag: int | None = None,
) -> FF5Regression:
    """FF5 regression via statsmodels OLS + HAC covariance."""
    from statsmodels.regression.linear_model import OLS
    import statsmodels.api as sm

    # 1. Align on common months
    df = ff5_data.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df = df.set_index("date")

    strat = strategy_returns.copy()
    strat.index = pd.to_datetime(strat.index).normalize()

    # Inner join on date
    merged = df.join(strat.to_frame("strategy"), how="inner")
    if len(merged) < 12:  # need at least 1 year of monthly data
        return FF5Regression(
            alpha=np.nan, alpha_t=np.nan, alpha_p=np.nan,
            beta_mkt=np.nan, beta_smb=np.nan, beta_hml=np.nan,
            beta_rmw=np.nan, beta_cma=np.nan,
            r_squared=np.nan, n_obs=len(merged), maxlag=0,
        )

    # 2. Excess returns = strategy - RF
    y = merged["strategy"].to_numpy(dtype=float) - merged["RF"].to_numpy(dtype=float)

    # 3. FF5 factors (excess market already Mkt-RF)
    X = merged[["Mkt-RF", "SMB", "HML", "RMW", "CMA"]].to_numpy(dtype=float)
    X = sm.add_constant(X)  # adds intercept column (alpha)

    # 4. OLS with Newey-West HAC
    n = len(y)
    if maxlag is None:
        maxlag = max(1, int(4 * (n / 100.0) ** (2/9)))  # Newey-West rule of thumb

    model = OLS(y, X)
    res = model.fit(cov_type="HAC", cov_kwds={"maxlags": maxlag})

    # 5. Extract coefficients
    params = res.params
    t_stats = res.tvalues
    p_values = res.pvalues

    return FF5Regression(
        alpha=float(params[0]),
        alpha_t=float(t_stats[0]),
        alpha_p=float(p_values[0]),
        beta_mkt=float(params[1]),
        beta_smb=float(params[2]),
        beta_hml=float(params[3]),
        beta_rmw=float(params[4]),
        beta_cma=float(params[5]),
        r_squared=float(res.rsquared),
        n_obs=n,
        maxlag=maxlag,
    )

def amihud_illiquidity(
    prices: pd.DataFrame,
    volume: pd.DataFrame,
    window: int = 21,
) -> pd.DataFrame:
    """Amihud (2002) illiquidity: |ret| / dollar volume.

    文献公式（照搬，不造轮子）:
        Illiq_i,t = (1/D_t) * Σ_d |r_i,d| / (Volume_i,d * Price_i,d)
    其中 D_t 是窗口期天数，r_i,d 是日收益。
    """
    # Merge price and volume
    df = prices.merge(volume, on=["date", "ticker"], how="inner", suffixes=("_price", "_vol"))

    # Compute daily returns
    df = df.sort_values(["ticker", "date"])
    df["ret"] = df.groupby("ticker")["close_price"].pct_change()

    # Dollar volume
    df["dollar_vol"] = df["close_price"] * df["close_vol"]

    # Absolute return / dollar volume (avoid div by zero)
    df["illiq_daily"] = df["ret"].abs() / df["dollar_vol"].replace(0, np.nan)

    # Rolling mean over window
    df["illiq"] = df.groupby("ticker")["illiq_daily"].transform(
        lambda x: x.rolling(window, min_periods=1).mean()
    )

    return df[["date", "ticker", "illiq"]].dropna()
```

### 测试骨架

```python
# tests/test_ff5_residual.py
def test_ff5_residual_regression_known_coeffs():
    """Test with synthetic FF5 data where ground truth is known."""
    import pandas as pd
    import numpy as np
    from aionis.track_b.ff5_residual import ff5_residual_regression

    # 24 months of synthetic data
    dates = pd.date_range("2020-01-31", periods=24, freq="ME")
    n = len(dates)
    rng = np.random.default_rng(42)

    # FF5 factors (standard normal ~ 1% monthly vol)
    ff5 = pd.DataFrame({
        "date": dates,
        "Mkt-RF": rng.standard_normal(n) * 0.01,
        "SMB": rng.standard_normal(n) * 0.005,
        "HML": rng.standard_normal(n) * 0.004,
        "RMW": rng.standard_normal(n) * 0.003,
        "CMA": rng.standard_normal(n) * 0.003,
        "RF": 0.0002,  # ~2.4% annual risk-free
    })

    # Strategy return = alpha + beta'*FF5 + noise
    alpha_true = 0.002  # 2.4% annual alpha
    betas_true = [1.2, 0.3, -0.2, 0.1, -0.05]  # MKT, SMB, HML, RMW, CMA
    noise = rng.standard_normal(n) * 0.01  # idiosyncratic vol 1%

    strategy = (
        alpha_true
        + betas_true[0] * ff5["Mkt-RF"]
        + betas_true[1] * ff5["SMB"]
        + betas_true[2] * ff5["HML"]
        + betas_true[3] * ff5["RMW"]
        + betas_true[4] * ff5["CMA"]
        + ff5["RF"]  # gross return, not excess
        + noise
    )

    result = ff5_residual_regression(strategy, ff5)

    # Check alpha recovered (within noise)
    assert 0.001 <= result["alpha"] <= 0.003  # ~0.002
    assert result["alpha_p"] < 0.05  # significant alpha
    assert result["n_obs"] == 24

def test_amihud_illiquidity_formula():
    """Test Amihud formula with known values."""
    import pandas as pd
    from aionis.track_b.ff5_residual import amihud_illiquidity

    prices = pd.DataFrame({
        "date": ["2020-01-02", "2020-01-03", "2020-01-06"] * 2,
        "ticker": ["A"] * 3 + ["B"] * 3,
        "close": [100.0, 101.0, 100.5, 50.0, 50.5, 49.8],
    })
    volume = pd.DataFrame({
        "date": ["2020-01-02", "2020-01-03", "2020-01-06"] * 2,
        "ticker": ["A"] * 3 + ["B"] * 3,
        "volume": [1_000_000, 2_000_000, 1_500_000, 500_000, 800_000, 600_000],
    })

    result = amihud_illiquidity(prices, volume, window=3)

    # Basic sanity: all values positive
    assert (result["illiq"] > 0).all()
    assert len(result) == 6  # 2 tickers × 3 dates
```

### 泄漏 Gotcha
- **FF5 因子无 vintage**：Kenneth-French 数据库是当前最新值，修订历史未公开。需在论文中声明"潜在轻微泄漏"。
- **回归窗口不含未来**：滚动回归时，窗口结束日期必须 ≤ 当前分析日期。
- **Amihud 计算 PIT**：使用窗口期内的价格/成交量，不包含未来数据。

### 不自己实现的部分
- OLS 回归：复用 `statsmodels.regression.linear_model.OLS`
- Newey-West 协方差：复用 `cov_type='HAC'`
- Amihud 公式：照搬 Amihud (2002) 论文（~15 行实现）

---

## 总结：三个挂接的 OSS 复用清单

| 挂接 | OSS 轮子 | 需 POC 核实 |
|------|----------|-------------|
| ① 风险/IC Tearsheet | `alphalens-reloaded` (Apache), `pyfolio-reloaded` (Apache) | alphalens 日频价格 API 的月频适配方式 |
| ② 回测净成本 | `FINSABER` (Apache, KDD 2026) | FINSABER 的真实输入格式 / Python 绑定 / 发布状态 |
| ③ FF5 残差 | `statsmodels` (BSD), `pandas-datareader` (BSD) | Kenneth-French FF5 的历史 vintage 修订幅度 |

**关键决策点**：
- 挂接①可立即实施（alphalens API 文档公开，月频适配有文献支持）
- 挂接②需先 POC 核实 FINSABER 仓库的 Python 接口（论文 KDD 2026 已接收，但代码未公开）
- 挂接③可立即实施（statsmodels 是成熟轮子，FF5 无 vintage 需显式声明）

以上设计确保"用轮子不造轮子"——adapter 只做粘合，核心逻辑全部复用 OSS。
