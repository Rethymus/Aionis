"""探索性 track_b PIT 基本面特征扩展（预指定，无 outcome-based 选择）。

从 EDGAR XBRL 现有 fund_* 字段派生的标准量化特征，全部基于 filed-date PIT。
特征集是构造规则决定的预指定清单，不基于任何收益/IC 进行选择。

纯 OSS 复用：edgartools 数据（via ingest/fundamentals.py）+ pandas/numpy 计算。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import structlog

log = structlog.get_logger()

# 常量：防止除零
_EPS = 1e-9

# 资产负债表相关
_ASSETS = "assets"
_EQUITY = "equity"
_LONG_TERM_DEBT = "long_term_debt"

# 损益表相关
_REVENUE = "revenue"
_NET_INCOME = "net_income"

# 其他
_SHARES_OUT = "shares_out"


def _safe_divide(
    numerator: pd.Series,
    denominator: pd.Series,
    eps: float = _EPS,
) -> pd.Series:
    """安全除法：分母接近零时返回 NaN。

    Args:
        numerator: 分子 Series。
        denominator: 分母 Series。
        eps: 零判断阈值。

    Returns:
        除法结果 Series，分母绝对值 < eps 时为 NaN。
    """
    result = numerator / denominator
    result[denominator.abs() < eps] = np.nan
    return result


def roa(assets: pd.DataFrame, net_income: pd.DataFrame) -> pd.DataFrame:
    """Return on Assets = 净利润 / 总资产。

    衡量企业运用全部资产获取利润的能力。

    Args:
        assets: PIT 总资产面板（index=as_of_date, columns=tickers）。
        net_income: PIT 净利润面板。

    Returns:
        ROA 面板，同形状。

    PIT 来源: filed_date <= t（净利润和总资产都用各自 filed_date <= t 的值）
    """
    return _safe_divide(net_income, assets)


def roe(equity: pd.DataFrame, net_income: pd.DataFrame) -> pd.DataFrame:
    """Return on Equity = 净利润 / 股东权益。

    衡量股东权益回报率。

    Args:
        equity: PIT 股东权益面板。
        net_income: PIT 净利润面板。

    Returns:
        ROE 面板。

    PIT 来源: filed_date <= t
    """
    return _safe_divide(net_income, equity)


def profit_margin(revenue: pd.DataFrame, net_income: pd.DataFrame) -> pd.DataFrame:
    """Profit Margin = 净利润 / 营业收入。

    衡量每单位营收的盈利能力。

    Args:
        revenue: PIT 营业收入面板。
        net_income: PIT 净利润面板。

    Returns:
        利润率面板。

    PIT 来源: filed_date <= t
    """
    return _safe_divide(net_income, revenue)


def asset_growth(
    assets: pd.DataFrame,
    periods: int = 1,
) -> pd.DataFrame:
    """资产增长率 = (资产_t - 资产_{t-periods}) / 资产_{t-periods}。

    衡量资产扩张速度。增长率越高通常意味着投资意愿强，
    但过度扩张可能损害 ROA。

    Args:
        assets: PIT 总资产面板。
        periods: 滞后期数（月数），默认 1。

    Returns:
        资产增长率面板。

    PIT 来源: filed_date <= t（当前和滞后的资产值都满足 PIT）
    """
    lagged = assets.shift(periods, axis=0)
    growth = (assets - lagged) / lagged
    # 前 periods 行无滞后值，返回 NaN
    growth.iloc[:periods] = np.nan
    return growth


def revenue_growth(
    revenue: pd.DataFrame,
    periods: int = 1,
) -> pd.DataFrame:
    """营收增长率 = (营收_t - 营收_{t-periods}) / 营收_{t-periods}。

    衡量业务增长势头。

    Args:
        revenue: PIT 营业收入面板。
        periods: 滞后期数（月数），默认 1。

    Returns:
        营收增长率面板。

    PIT 来源: filed_date <= t
    """
    lagged = revenue.shift(periods, axis=0)
    growth = (revenue - lagged) / lagged
    growth.iloc[:periods] = np.nan
    return growth


def equity_growth(
    equity: pd.DataFrame,
    periods: int = 1,
) -> pd.DataFrame:
    """股东权益增长率 = (权益_t - 权益_{t-periods}) / 权益_{t-periods}。

    衡量股东权益积累速度。

    Args:
        equity: PIT 股东权益面板。
        periods: 滞后期数（月数），默认 1。

    Returns:
        权益增长率面板。

    PIT 来源: filed_date <= t
    """
    lagged = equity.shift(periods, axis=0)
    growth = (equity - lagged) / lagged
    growth.iloc[:periods] = np.nan
    return growth


def leverage(
    assets: pd.DataFrame,
    long_term_debt: pd.DataFrame,
) -> pd.DataFrame:
    """财务杠杆 = 长期债务 / 总资产。

    衡量债务融资比例。高杠杆增加财务风险但也可能放大 ROE。

    Args:
        assets: PIT 总资产面板。
        long_term_debt: PIT 长期债务面板。

    Returns:
        杠杆比率面板。

    PIT 来源: filed_date <= t
    """
    return _safe_divide(long_term_debt, assets)


def debt_to_equity(
    equity: pd.DataFrame,
    long_term_debt: pd.DataFrame,
) -> pd.DataFrame:
    """债务权益比 = 长期债务 / 股东权益。

    另一常见的杠杆度量。

    Args:
        equity: PIT 股东权益面板。
        long_term_debt: PIT 长期债务面板。

    Returns:
        债务权益比面板。

    PIT 来源: filed_date <= t
    """
    return _safe_divide(long_term_debt, equity)


def book_value_per_share(
    equity: pd.DataFrame,
    shares_out: pd.DataFrame,
) -> pd.DataFrame:
    """每股账面价值 = 股东权益 / 流通股数。

    市净率（P/B）的分母。当与市值结合时可直接计算 P/B。

    Args:
        equity: PIT 股东权益面板。
        shares_out: PIT 流通股数面板。

    Returns:
        每股账面价值面板。

    PIT 来源: filed_date <= t
    """
    return _safe_divide(equity, shares_out)


def accruals(
    assets: pd.DataFrame,
    net_income: pd.DataFrame,
    lag_periods: int = 12,
) -> pd.DataFrame:
    """应计项目 = (净利润 - 经营现金流) / 总资产的代理。

    由于我们只有净利润没有经营现金流，这里使用净利润变化与资产变化的
    关系作为应计项目的代理指标（Sloan 1996 风格的简化）。

    高应计公司通常未来收益会向下修正（应计异象）。

    Args:
        assets: PIT 总资产面板。
        net_income: PIT 净利润面板。
        lag_periods: 计算变化的滞后期数（月），默认 12（年度）。

    Returns:
        应计项目代理面板。

    PIT 来源: filed_date <= t
    """
    # 净利润变化
    ni_change = net_income - net_income.shift(lag_periods, axis=0)
    # 资产变化
    asset_change = assets - assets.shift(lag_periods, axis=0)
    # 应计代理 = 净利润变化 - 资产变化（相对于总资产）
    accruals_proxy = (ni_change - asset_change) / assets
    # 前 lag_periods 行无有效值
    accruals_proxy.iloc[:lag_periods] = np.nan
    return accruals_proxy


def investment(
    assets: pd.DataFrame,
    periods: int = 12,
) -> pd.DataFrame:
    """投资率 = 资产增长率（年度）。

    衡量资本支出强度。高投资公司通常未来收益较低（投资异象）。

    Args:
        assets: PIT 总资产面板。
        periods: 滞后期数（月），默认 12（年度）。

    Returns:
        投资率面板。

    PIT 来源: filed_date <= t
    """
    return asset_growth(assets, periods=periods)


def compute_corporate_vital_signs(
    panels: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """从 PIT 基本面面板计算所有预指定特征。

    输入面板由 `ingest.fundamentals.pit_align` 产出，每个 metric 是一个
    [as_of_dates x tickers] 的 wide DataFrame。

    Args:
        panels: dict {metric_name: wide DataFrame}。
                必需的 metrics: assets, equity, revenue, net_income,
                               shares_out, long_term_debt。

    Returns:
        一个 MultiIndex Column DataFrame [as_of_dates, (ticker, feature)]，
        可通过 stack() 转换为 [date, ticker, feature1, ..., featureN]。

    Raises:
        ValueError: 如果缺少必需的 metric。
        KeyError: 如果面板索引不一致。
    """
    required = {_ASSETS, _EQUITY, _REVENUE, _NET_INCOME, _SHARES_OUT, _LONG_TERM_DEBT}
    missing = required - set(panels.keys())
    if missing:
        raise ValueError(f"缺少必需的 metrics: {missing}")

    # 获取索引和列（假设所有面板共享同一结构）
    sample = panels[_ASSETS]
    index = sample.index
    tickers = sample.columns

    # 检查索引对齐
    for name, panel in panels.items():
        if not panel.index.equals(index):
            raise KeyError(f"{name} 的索引与 assets 不一致")
        if not panel.columns.equals(tickers):
            raise KeyError(f"{name} 的列与 assets 不一致")

    # 计算所有特征
    features: dict[str, pd.DataFrame] = {}

    # 盈利能力 (Profitability)
    features["roa"] = roa(panels[_ASSETS], panels[_NET_INCOME])
    features["roe"] = roe(panels[_EQUITY], panels[_NET_INCOME])
    features["profit_margin"] = profit_margin(panels[_REVENUE], panels[_NET_INCOME])

    # 增长率 (Growth)
    features["asset_growth_1m"] = asset_growth(panels[_ASSETS], periods=1)
    features["revenue_growth_1m"] = revenue_growth(panels[_REVENUE], periods=1)
    features["equity_growth_1m"] = equity_growth(panels[_EQUITY], periods=1)
    features["asset_growth_12m"] = asset_growth(panels[_ASSETS], periods=12)
    features["revenue_growth_12m"] = revenue_growth(panels[_REVENUE], periods=12)

    # 杠杆 (Leverage)
    features["leverage"] = leverage(panels[_ASSETS], panels[_LONG_TERM_DEBT])
    features["debt_to_equity"] = debt_to_equity(panels[_EQUITY], panels[_LONG_TERM_DEBT])

    # 每股指标 (Per-share)
    features["book_value_per_share"] = book_value_per_share(
        panels[_EQUITY],
        panels[_SHARES_OUT],
    )

    # 应计项目 (Accruals)
    features["accruals"] = accruals(panels[_ASSETS], panels[_NET_INCOME])

    # 投资 (Investment)
    features["investment_12m"] = investment(panels[_ASSETS], periods=12)

    # 合并为 MultiIndex Column DataFrame
    result = pd.concat(features, axis=1, keys=features.keys())
    result.columns.names = ["feature", "ticker"]

    return result


# 预指定特征列清单（供 config 冻结）
TRACK_B_FEATURE_COLS: list[str] = [
    # 盈利能力
    "roa",
    "roe",
    "profit_margin",
    # 增长率
    "asset_growth_1m",
    "revenue_growth_1m",
    "equity_growth_1m",
    "asset_growth_12m",
    "revenue_growth_12m",
    # 杠杆
    "leverage",
    "debt_to_equity",
    # 每股指标
    "book_value_per_share",
    # 应计项目
    "accruals",
    # 投资
    "investment_12m",
]
"""Track B 预指定基本面特征列清单。

此清单由构造规则预指定，不基于任何 outcome-based 选择。
数量：13 个特征。
"""
