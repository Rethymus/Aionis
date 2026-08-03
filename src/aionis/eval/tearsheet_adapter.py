"""Tearsheet risk metrics adapter —复用 empyrical（Apache-2.0）。

本模块封装 empyrical 库的风险指标计算，用于 Track B 月度组合收益的 tearsheet
生成。禁止手算 sharpe/max_drawdown/sortino/calmar/omega/alpha/beta 等指标。

复用来源：
    empyrical (Apache-2.0) - https://github.com/quantopian/empyrical
    核心函数：annual_return, annual_volatility, sharpe_ratio, sortino_ratio,
              max_drawdown, calmar_ratio, omega_ratio, alpha_beta, cum_returns

输入约定：
    monthly_returns: 月度收益序列，list[float] 或 pd.Series，索引为日期（可选）
    period: empyrical.MONTHLY（默认），适配月频数据

输出约定：
    dict[str, float]: 扁平化指标字典，键为指标名，值为浮点数（NaN 容错）
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

try:
    import empyrical as ep
except ImportError as err:
    raise ImportError(
        "empyrical is required. Install with: uv pip install empyrical"
    ) from err


def _to_series(
    returns: list[float] | pd.Series | np.ndarray,
) -> pd.Series:
    """转换为 pd.Series 并清洗无效值。

    Args:
        returns: 月度收益，支持 list/Series/ndarray

    Returns:
        pd.Series: 清洗后的收益序列（NaN 已剔除）
    """
    if isinstance(returns, list):
        returns = np.array(returns, dtype=float)
    if isinstance(returns, np.ndarray):
        returns = pd.Series(returns)
    if not isinstance(returns, pd.Series):
        returns = pd.Series(returns, dtype=float)

    # 剔除 NaN/Inf
    returns = returns.replace([np.inf, -np.inf], np.nan).dropna()
    return returns


def compute_risk_metrics(
    monthly_returns: list[float] | pd.Series,
    period: str = ep.MONTHLY,
) -> dict[str, float]:
    """计算单臂的风险指标（复用 empyrical）。

    支持指标：
        - annual_return: 年化收益率
        - annual_volatility: 年化波动率
        - sharpe_ratio: 夏普比率（默认无风险利率=0）
        - sortino_ratio: 索提诺比率
        - max_drawdown: 最大回撤（负值）
        - calmar_ratio: 卡玛比率（年化收益/最大回撤绝对值）
        - omega_ratio: 欧米茄比率

    每个指标独立 try/except，确保部分失败不阻断其他指标计算。

    Args:
        monthly_returns: 月度收益序列（支持 list/Series）
        period: empyrical 周期参数（默认 MONTHLY）

    Returns:
        dict[str, float]: {指标名: 值}，无效输入返回全 NaN
    """
    returns = _to_series(monthly_returns)

    if len(returns) < 2:
        # 少于 2 期数据，所有指标均无法有效计算
        return {
            "annual_return": np.nan,
            "annual_volatility": np.nan,
            "sharpe_ratio": np.nan,
            "sortino_ratio": np.nan,
            "max_drawdown": np.nan,
            "calmar_ratio": np.nan,
            "omega_ratio": np.nan,
        }

    metrics: dict[str, float] = {}

    # annual_return
    try:
        metrics["annual_return"] = float(ep.annual_return(returns, period=period))
    except Exception:
        metrics["annual_return"] = np.nan

    # annual_volatility
    try:
        metrics["annual_volatility"] = float(
            ep.annual_volatility(returns, period=period)
        )
    except Exception:
        metrics["annual_volatility"] = np.nan

    # sharpe_ratio
    try:
        metrics["sharpe_ratio"] = float(
            ep.sharpe_ratio(returns, period=period)
        )
    except Exception:
        metrics["sharpe_ratio"] = np.nan

    # sortino_ratio
    try:
        metrics["sortino_ratio"] = float(
            ep.sortino_ratio(returns, period=period)
        )
    except Exception:
        metrics["sortino_ratio"] = np.nan

    # max_drawdown
    try:
        metrics["max_drawdown"] = float(ep.max_drawdown(returns))
    except Exception:
        metrics["max_drawdown"] = np.nan

    # calmar_ratio
    try:
        metrics["calmar_ratio"] = float(ep.calmar_ratio(returns, period=period))
    except Exception:
        metrics["calmar_ratio"] = np.nan

    # omega_ratio
    try:
        # omega_ratio 需要 risk_free 参数，默认 0
        metrics["omega_ratio"] = float(
            ep.omega_ratio(returns, risk_free=0.0, period=period)
        )
    except Exception:
        metrics["omega_ratio"] = np.nan

    return metrics


def tearsheet_summary(
    model_returns: list[float] | pd.Series,
    ew_returns: list[float] | pd.Series,
) -> dict[str, Any]:
    """生成两臂对比 tearsheet 汇总。

    计算模型臂与等权臂的风险指标，并包含差值（model - ew）。

    Args:
        model_returns: 模型预测的月度收益
        ew_returns: 等权基准的月度收益

    Returns:
        dict: {
            "model": {指标名: 值},
            "ew": {指标名: 值},
            "diff": {指标名: 差值},
        }
    """
    model_metrics = compute_risk_metrics(model_returns)
    ew_metrics = compute_risk_metrics(ew_returns)

    diff_metrics: dict[str, float] = {}
    for key in model_metrics:
        m_val = model_metrics[key]
        ew_val = ew_metrics[key]
        if np.isfinite(m_val) and np.isfinite(ew_val):
            diff_metrics[key] = m_val - ew_val
        else:
            diff_metrics[key] = np.nan

    return {"model": model_metrics, "ew": ew_metrics, "diff": diff_metrics}


def cumulative_returns(
    monthly_returns: list[float] | pd.Series,
) -> list[float]:
    """计算累计收益（复用 empyrical.cum_returns）。

    累计收益曲线起点归一为 1.0，用于站点可视化。

    Args:
        monthly_returns: 月度收益序列

    Returns:
        list[float]: 累计收益值，单调递增（正收益时）或递减
    """
    returns = _to_series(monthly_returns)

    if len(returns) == 0:
        return []

    try:
        # empyrical.cum_returns 返回 Series，起点为 1.0
        cum = ep.cum_returns(returns, starting_value=1.0)
        return cum.tolist()
    except Exception:
        # 降级方案：简单 cumprod
        cum = (1 + returns).cumprod()
        return cum.tolist()
