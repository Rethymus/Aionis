"""探索性 track_b 价格特征工程（预指定，无 outcome-based 选择）。

纯价格技术特征，使用预指定窗口计算 momentum、reversal、volatility、
turnover、beta 等。复用 eval.ff5_residual 中的 amihud_illiquidity。

纯 OSS 复用：pandas/numpy 计算 + ff5_residual 的 Amihud 实现。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import structlog

from aionis.eval.ff5_residual import amihud_illiquidity

log = structlog.get_logger()

# 常量：防止除零
_EPS = 1e-9

# 预指定窗口（交易日）
_MOMENTUM_WINDOWS = (5, 10, 21, 42)
_REVERSAL_WINDOW = 5
_VOLATILITY_WINDOWS = (21, 63)
_TURNOVER_WINDOW = 21
_BETA_WINDOW = 252  # 约 1 年


def _safe_divide(
    numerator: pd.Series | pd.DataFrame,
    denominator: pd.Series | pd.DataFrame,
    eps: float = _EPS,
) -> pd.Series | pd.DataFrame:
    """安全除法：分母接近零时返回 NaN。

    Args:
        numerator: 分子 Series 或 DataFrame。
        denominator: 分母 Series 或 DataFrame。
        eps: 零判断阈值。

    Returns:
        除法结果，分母绝对值 < eps 时为 NaN。
    """
    result = numerator / denominator
    result[denominator.abs() < eps] = np.nan
    return result


def _compute_return(prices: pd.DataFrame) -> pd.DataFrame:
    """计算日收益率（pct_change）。

    Args:
        prices: 价格面板 [dates x tickers]。

    Returns:
        收益率面板，第一行为 NaN。
    """
    return prices.pct_change()


def momentum(
    returns: pd.DataFrame,
    window: int,
) -> pd.DataFrame:
    """动量 = 累计收益率（过去 window 日）。

    正动量表示过去期间价格上涨，可能延续（动量效应）。

    Args:
        returns: 收益率面板 [dates x tickers]。
        window: 回溯窗口（交易日）。

    Returns:
        动量面板，前 window 行为 NaN。
    """
    # 累计收益 = (1+r1)*(1+r2)*...*(1+rw) - 1
    # 等价于 log(1+r) 之和后取 exp，或直接用 product
    # 使用简化：sum(returns) 当日收益较小时近似累计收益
    # 精确计算：(1 + returns).rolling(window).apply(lambda x: np.prod(x) - 1)
    # 为效率使用 rolling sum 的近似（日收益 < 5% 时误差 < 0.1%）
    return returns.rolling(window=window, min_periods=window).sum()


def reversal(
    returns: pd.DataFrame,
    window: int = 5,
) -> pd.DataFrame:
    """短期反转 = 负的短期动量。

    短期价格反转（overreaction 修正）。

    Args:
        returns: 收益率面板。
        window: 回溯窗口（交易日），默认 5。

    Returns:
        反转面板，前 window 行为 NaN。
    """
    # 反转 = -momentum_short
    return -momentum(returns, window)


def volatility(
    returns: pd.DataFrame,
    window: int,
    annualize: bool = False,
) -> pd.DataFrame:
    """波动率 = 收益率标准差（过去 window 日）。

    高波动股票通常有更高的预期收益（风险溢价）。

    Args:
        returns: 收益率面板。
        window: 回溯窗口（交易日）。
        annualize: 是否年化（sqrt(252)），默认 False。

    Returns:
        波动率面板，前 window 行为 NaN。
    """
    vol = returns.rolling(window=window, min_periods=window).std()
    if annualize:
        vol *= np.sqrt(252)
    return vol


def turnover(
    volume: pd.DataFrame,
    window: int = 21,
) -> pd.DataFrame:
    """换手率 = 成交量滚动均值（过去 window 日）。

    衡量交易活跃度。高换手可能表示关注度或投机性。

    Args:
        volume: 成交量面板 [dates x tickers]。
        window: 回溯窗口（交易日），默认 21。

    Returns:
        换手率面板，前 window 行为 NaN。
    """
    return volume.rolling(window=window, min_periods=window).mean()


def beta(
    returns: pd.DataFrame,
    market_returns: pd.Series,
    window: int = 252,
) -> pd.DataFrame:
    """Beta = 与市场收益的协方差 / 市场收益方差。

    衡量系统性风险暴露。Beta > 1 表示放大市场波动。

    Args:
        returns: 收益率面板 [dates x tickers]。
        market_returns: 市场收益率 Series（如 SPY），index 与 returns 对齐。
        window: 回溯窗口（交易日），默认 252。
        min_periods: 最小观察数，默认 window//2。

    Returns:
        Beta 面板 [dates x tickers]，前 min_periods 行为 NaN。
    """
    min_periods = max(2, window // 2)

    # 市场收益滚动方差
    market_var = market_returns.rolling(
        window=window, min_periods=min_periods
    ).var()

    # 每个股票的滚动协方差
    betas = pd.DataFrame(index=returns.index, columns=returns.columns, dtype=float)

    for ticker in returns.columns:
        stock_ret = returns[ticker]
        cov = stock_ret.rolling(window=window, min_periods=min_periods).cov(
            market_returns
        )
        betas[ticker] = _safe_divide(cov, market_var)

    return betas


def compute_price_features(
    prices: pd.DataFrame,
    volume: pd.DataFrame | None = None,
    market_prices: pd.Series | None = None,
) -> pd.DataFrame:
    """从价格/成交量数据计算所有预指定价格特征。

    Args:
        prices: 价格面板 [dates x tickers]，adj close。
        volume: 成交量面板 [dates x tickers]（可选，如无则跳过 turnover/amihud）。
        market_prices: 市场基准价格 Series（如 SPY），index 与 prices 对齐
                      （可选，如无则跳过 beta）。

    Returns:
        一个 MultiIndex Column DataFrame [dates, (ticker, feature)]，
        可通过 stack() 转换为 [date, ticker, feature1, ..., featureN]。

    Raises:
        ValueError: 如果输入形状不一致。
    """
    # 输入校验
    if not isinstance(prices, pd.DataFrame):
        raise ValueError("prices 必须是 DataFrame")
    if volume is not None and not volume.shape == prices.shape:
        raise ValueError("volume 与 prices 形状必须一致")
    if market_prices is not None and not market_prices.index.equals(prices.index):
        raise ValueError("market_prices 的索引必须与 prices 对齐")

    # 计算收益率
    returns = _compute_return(prices)

    # 计算市场收益率
    market_returns = None
    if market_prices is not None:
        market_returns = market_prices.pct_change()

    features: dict[str, pd.DataFrame] = {}

    # 动量（多个窗口）
    for w in _MOMENTUM_WINDOWS:
        features[f"momentum_{w}d"] = momentum(returns, window=w)

    # 短期反转
    features[f"reversal_{_REVERSAL_WINDOW}d"] = reversal(returns, window=_REVERSAL_WINDOW)

    # 波动率（多个窗口）
    for w in _VOLATILITY_WINDOWS:
        features[f"volatility_{w}d"] = volatility(returns, window=w)

    # 换手率（需要成交量）
    if volume is not None:
        features[f"turnover_{_TURNOVER_WINDOW}d"] = turnover(volume, window=_TURNOVER_WINDOW)

    # Beta（需要市场基准）
    if market_returns is not None:
        features[f"beta_{_BETA_WINDOW}d"] = beta(
            returns,
            market_returns,
            window=_BETA_WINDOW,
        )

    # 合并为 MultiIndex Column DataFrame
    result = pd.concat(features, axis=1, keys=features.keys())
    result.columns.names = ["feature", "ticker"]

    return result


def compute_amihud_from_wide(
    prices: pd.DataFrame,
    volume: pd.DataFrame,
    window: int = 21,
) -> pd.DataFrame:
    """从 wide 格式价格/成交量计算 Amihud 非流动性。

    复用 `eval.ff5_residual.amihud_illiquidity`，但需要转换格式。

    Args:
        prices: 价格面板 [dates x tickers]。
        volume: 成交量面板 [dates x tickers]。
        window: 滚动窗口（交易日），默认 21。

    Returns:
        Amihud 非流动性面板 [dates x tickers]。
    """
    # 将 wide 转换为 long format (stack)
    prices_long = prices.stack().reset_index()
    prices_long.columns = ["date", "ticker", "close"]

    volume_long = volume.stack().reset_index()
    volume_long.columns = ["date", "ticker", "volume"]

    # 调用 ff5_residual 的实现
    result_long = amihud_illiquidity(prices_long, volume_long, window=window)

    # 转换回 wide format
    result = result_long.pivot(index="date", columns="ticker", values="illiq")
    return result


# 预指定特征列清单（供 config 冻结）
TRACK_B_PRICE_FEATURE_COLS: list[str] = [
    # 动量
    "momentum_5d",
    "momentum_10d",
    "momentum_21d",
    "momentum_42d",
    # 反转
    "reversal_5d",
    # 波动率
    "volatility_21d",
    "volatility_63d",
    # 换手率
    "turnover_21d",
    # Beta
    "beta_252d",
    # Amihud 非流动性
    "amihud_illiquidity_21d",
]
"""Track B 预指定价格特征列清单。

此清单由构造规则预指定，不基于任何 outcome-based 选择。
数量：10 个特征。

注意：turnover_21d 和 beta_252d 需要可选的 volume/market_prices 输入；
      amihud_illiquidity_21d 需要 compute_amihud_from_wide 单独计算。
"""
