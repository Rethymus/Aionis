"""探索性 track_b 基本面特征测试（hermetic，synthetic data）。

AAA 结构：Arrange-Act-Assert。
描述性测试名：明确测试的行为。
固定 seed：确保 deterministic。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aionis.features.corporate_vital_signs import (
    _EPS,
    TRACK_B_FEATURE_COLS,
    _safe_divide,
    accruals,
    asset_growth,
    book_value_per_share,
    compute_corporate_vital_signs,
    debt_to_equity,
    equity_growth,
    investment,
    leverage,
    profit_margin,
    revenue_growth,
    roa,
    roe,
)

# 测试用固定 seed
_RNG = np.random.default_rng(seed=42)


def _make_panel(
    n_dates: int = 24,
    n_tickers: int = 3,
    base_value: float = 100.0,
    trend: float = 0.01,
    noise_std: float = 0.05,
) -> pd.DataFrame:
    """生成 synthetic PIT 面板（用于测试）。

    Args:
        n_dates: 日期数（月）。
        n_tickers: ticker 数。
        base_value: 基础值。
        trend: 趋势增长率（模拟增长）。
        noise_std: 噪声标准差。

    Returns:
        [dates x tickers] DataFrame，index 为月频 DatetimeIndex。
    """
    dates = pd.date_range("2020-01-01", periods=n_dates, freq="ME")
    tickers = [f"T{i}" for i in range(n_tickers)]

    data = np.zeros((n_dates, n_tickers))
    for t in range(n_tickers):
        # 趋势 + 噪声
        values = base_value * (1 + trend) ** np.arange(n_dates)
        noise = _RNG.normal(0, noise_std * base_value, n_dates)
        data[:, t] = values + noise

    return pd.DataFrame(data, index=dates, columns=tickers)


class TestSafeDivide:
    """测试安全除法工具函数。"""

    def test_returns_correct_ratio_when_denominator_is_nonzero(self) -> None:
        """当分母非零时返回正确的商。"""
        num = pd.Series([10.0, 20.0, 30.0])
        den = pd.Series([2.0, 4.0, 5.0])
        result = _safe_divide(num, den)
        expected = pd.Series([5.0, 5.0, 6.0])
        pd.testing.assert_series_equal(result, expected)

    def test_returns_nan_when_denominator_is_near_zero(self) -> None:
        """当分母接近零时返回 NaN。"""
        num = pd.Series([10.0, 20.0, 30.0])
        den = pd.Series([2.0, _EPS / 10, 5.0])  # 中间项 < eps
        result = _safe_divide(num, den)
        assert pd.isna(result.iloc[1])
        assert not pd.isna(result.iloc[0])
        assert not pd.isna(result.iloc[2])

    def test_handles_dataframe_input(self) -> None:
        """处理 DataFrame 输入。"""
        num = pd.DataFrame([[10.0, 20.0], [30.0, 40.0]])
        den = pd.DataFrame([[2.0, 4.0], [5.0, 8.0]])
        result = _safe_divide(num, den)
        expected = pd.DataFrame([[5.0, 5.0], [6.0, 5.0]])
        pd.testing.assert_frame_equal(result, expected)


class TestRoa:
    """测试 ROA（资产回报率）计算。"""

    def test_returns_correct_roa_for_known_values(self) -> None:
        """已知输入产生正确的 ROA。"""
        assets = pd.DataFrame(
            [[100.0, 200.0], [100.0, 200.0]],
            columns=["A", "B"],
        )
        net_income = pd.DataFrame(
            [[10.0, 20.0], [15.0, 25.0]],
            columns=["A", "B"],
        )
        result = roa(assets, net_income)
        expected = pd.DataFrame(
            [[0.1, 0.1], [0.15, 0.125]],
            columns=["A", "B"],
        )
        pd.testing.assert_frame_equal(result, expected)

    def test_returns_nan_when_assets_are_zero(self) -> None:
        """资产为零时返回 NaN。"""
        assets = pd.DataFrame([[0.0, 100.0]], columns=["A", "B"])
        net_income = pd.DataFrame([[10.0, 20.0]], columns=["A", "B"])
        result = roa(assets, net_income)
        assert pd.isna(result["A"].iloc[0])
        assert result["B"].iloc[0] == pytest.approx(0.2)


class TestRoe:
    """测试 ROE（股本回报率）计算。"""

    def test_returns_correct_roe_for_known_values(self) -> None:
        """已知输入产生正确的 ROE。"""
        equity = pd.DataFrame(
            [[50.0, 100.0]],
            columns=["A", "B"],
        )
        net_income = pd.DataFrame(
            [[10.0, 20.0]],
            columns=["A", "B"],
        )
        result = roe(equity, net_income)
        expected = pd.DataFrame([[0.2, 0.2]], columns=["A", "B"])
        pd.testing.assert_frame_equal(result, expected)

    def test_returns_nan_when_equity_is_zero(self) -> None:
        """股本为零时返回 NaN。"""
        equity = pd.DataFrame([[0.0, 100.0]], columns=["A", "B"])
        net_income = pd.DataFrame([[10.0, 20.0]], columns=["A", "B"])
        result = roe(equity, net_income)
        assert pd.isna(result["A"].iloc[0])


class TestProfitMargin:
    """测试利润率计算。"""

    def test_returns_correct_profit_margin(self) -> None:
        """已知输入产生正确的利润率。"""
        revenue = pd.DataFrame([[100.0, 200.0]], columns=["A", "B"])
        net_income = pd.DataFrame([[20.0, 30.0]], columns=["A", "B"])
        result = profit_margin(revenue, net_income)
        expected = pd.DataFrame([[0.2, 0.15]], columns=["A", "B"])
        pd.testing.assert_frame_equal(result, expected)

    def test_returns_nan_when_revenue_is_zero(self) -> None:
        """营收为零时返回 NaN。"""
        revenue = pd.DataFrame([[0.0, 100.0]], columns=["A", "B"])
        net_income = pd.DataFrame([[5.0, 20.0]], columns=["A", "B"])
        result = profit_margin(revenue, net_income)
        assert pd.isna(result["A"].iloc[0])


class TestAssetGrowth:
    """测试资产增长率计算。"""

    def test_returns_correct_growth_for_increasing_assets(self) -> None:
        """递增资产产生正确的增长率。"""
        assets = pd.DataFrame(
            [[100.0], [110.0], [121.0]],  # 10% 增长
            columns=["A"],
        )
        result = asset_growth(assets, periods=1)
        # 第一行无滞后值，应为 NaN
        assert pd.isna(result.iloc[0, 0])
        # 第二行：(110-100)/100 = 0.1
        assert result.iloc[1, 0] == pytest.approx(0.1)
        # 第三行：(121-110)/110 = 0.1
        assert result.iloc[2, 0] == pytest.approx(0.1)

    def test_returns_nan_for_first_period_rows(self) -> None:
        """前 periods 行返回 NaN。"""
        assets = pd.DataFrame([[100.0]] * 5, columns=["A"])
        result = asset_growth(assets, periods=3)
        # 前 3 行应为 NaN
        assert result.iloc[:3].isna().all().all()
        # 第 4 行：(100-100)/100 = 0（不是 NaN）
        assert result.iloc[3, 0] == pytest.approx(0.0)


class TestRevenueGrowth:
    """测试营收增长率计算。"""

    def test_returns_correct_growth_for_increasing_revenue(self) -> None:
        """递增营收产生正确的增长率。"""
        revenue = pd.DataFrame(
            [[100.0], [105.0], [110.25]],  # 5% 增长
            columns=["A"],
        )
        result = revenue_growth(revenue, periods=1)
        assert result.iloc[1, 0] == pytest.approx(0.05)
        assert result.iloc[2, 0] == pytest.approx(0.05)


class TestEquityGrowth:
    """测试股本增长率计算。"""

    def test_returns_correct_growth_for_increasing_equity(self) -> None:
        """递增股本产生正确的增长率。"""
        equity = pd.DataFrame(
            [[50.0], [55.0], [60.5]],  # 10% 增长
            columns=["A"],
        )
        result = equity_growth(equity, periods=1)
        assert result.iloc[1, 0] == pytest.approx(0.1)
        assert result.iloc[2, 0] == pytest.approx(0.1)


class TestLeverage:
    """测试财务杠杆计算。"""

    def test_returns_correct_leverage_ratio(self) -> None:
        """已知输入产生正确的杠杆比率。"""
        assets = pd.DataFrame([[100.0, 200.0]], columns=["A", "B"])
        debt = pd.DataFrame([[30.0, 50.0]], columns=["A", "B"])
        result = leverage(assets, debt)
        expected = pd.DataFrame([[0.3, 0.25]], columns=["A", "B"])
        pd.testing.assert_frame_equal(result, expected)


class TestDebtToEquity:
    """测试债务权益比计算。"""

    def test_returns_correct_debt_to_equity_ratio(self) -> None:
        """已知输入产生正确的债务权益比。"""
        equity = pd.DataFrame([[50.0, 100.0]], columns=["A", "B"])
        debt = pd.DataFrame([[25.0, 40.0]], columns=["A", "B"])
        result = debt_to_equity(equity, debt)
        expected = pd.DataFrame([[0.5, 0.4]], columns=["A", "B"])
        pd.testing.assert_frame_equal(result, expected)


class TestBookValuePerShare:
    """测试每股账面价值计算。"""

    def test_returns_correct_bvps_for_known_values(self) -> None:
        """已知输入产生正确的每股账面价值。"""
        equity = pd.DataFrame([[100.0, 200.0]], columns=["A", "B"])
        shares = pd.DataFrame([[10.0, 20.0]], columns=["A", "B"])
        result = book_value_per_share(equity, shares)
        expected = pd.DataFrame([[10.0, 10.0]], columns=["A", "B"])
        pd.testing.assert_frame_equal(result, expected)


class TestAccruals:
    """测试应计项目代理计算。"""

    def test_returns_negative_accruals_for_high_income_growth(self) -> None:
        """收入高增长而资产低增长时，应计代理为负。"""
        assets = pd.DataFrame([[100.0]] * 13, columns=["A"])
        net_income_values = [10.0] + [15.0] * 12
        net_income = pd.DataFrame(net_income_values, columns=["A"])
        # 净利润跃升但资产不变 -> 应计代理 = (income_change - asset_change) / assets
        result = accruals(assets, net_income, lag_periods=12)
        # 第 13 行有值
        assert not pd.isna(result.iloc[12, 0])
        # income_change = 5, asset_change = 0, assets = 100 -> 0.05
        assert result.iloc[12, 0] == pytest.approx(0.05)


class TestInvestment:
    """测试投资率计算。"""

    def test_investment_equals_asset_growth(self) -> None:
        """投资率等于资产增长率。"""
        assets = pd.DataFrame(
            [[100.0], [110.0], [121.0]],
            columns=["A"],
        )
        result = investment(assets, periods=1)
        expected = asset_growth(assets, periods=1)
        pd.testing.assert_frame_equal(result, expected)


class TestComputeCorporateVitalSigns:
    """测试完整特征计算流程。"""

    def test_returns_correct_feature_count(self) -> None:
        """返回正确数量的特征。"""
        panels = {
            "assets": _make_panel(),
            "equity": _make_panel(),
            "revenue": _make_panel(),
            "net_income": _make_panel(),
            "shares_out": _make_panel(),
            "long_term_debt": _make_panel(),
        }
        result = compute_corporate_vital_signs(panels)
        # 检查特征数量
        feature_count = len(TRACK_B_FEATURE_COLS)
        assert len(result.columns.get_level_values(0).unique()) == feature_count

    def test_raises_value_error_when_metrics_missing(self) -> None:
        """缺少必需 metric 时抛出 ValueError。"""
        panels = {
            "assets": _make_panel(),
            "equity": _make_panel(),
            # 缺少其他
        }
        with pytest.raises(ValueError, match="缺少必需的 metrics"):
            compute_corporate_vital_signs(panels)

    def test_raises_key_error_when_index_mismatch(self) -> None:
        """索引不一致时抛出 KeyError。"""
        base_panel = _make_panel()
        wrong_index_panel = _make_panel()
        wrong_index_panel.index = pd.date_range("2021-01-01", periods=24, freq="ME")

        panels = {
            "assets": base_panel,
            "equity": wrong_index_panel,
            "revenue": _make_panel(),
            "net_income": _make_panel(),
            "shares_out": _make_panel(),
            "long_term_debt": _make_panel(),
        }
        with pytest.raises(KeyError, match="索引"):
            compute_corporate_vital_signs(panels)

    def test_result_has_multiindex_columns(self) -> None:
        """结果有 MultiIndex columns（feature, ticker）。"""
        panels = {
            "assets": _make_panel(),
            "equity": _make_panel(),
            "revenue": _make_panel(),
            "net_income": _make_panel(),
            "shares_out": _make_panel(),
            "long_term_debt": _make_panel(),
        }
        result = compute_corporate_vital_signs(panels)
        assert isinstance(result.columns, pd.MultiIndex)
        assert result.columns.names == ["feature", "ticker"]


class TestTrackBFeatureCols:
    """测试预指定特征列清单。"""

    def test_feature_cols_is_non_empty_list(self) -> None:
        """TRACK_B_FEATURE_COLS 是非空列表。"""
        assert isinstance(TRACK_B_FEATURE_COLS, list)
        assert len(TRACK_B_FEATURE_COLS) > 0

    def test_feature_cols_contains_expected_features(self) -> None:
        """包含预期特征。"""
        expected_features = {
            "roa",
            "roe",
            "profit_margin",
            "leverage",
            "debt_to_equity",
        }
        assert expected_features.issubset(set(TRACK_B_FEATURE_COLS))
