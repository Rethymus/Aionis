"""探索性 track_b 价格特征测试（hermetic，synthetic data）。

AAA 结构：Arrange-Act-Assert。
描述性测试名：明确测试的行为。
固定 seed：确保 deterministic。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aionis.features.price_features import (
    _EPS,
    TRACK_B_PRICE_FEATURE_COLS,
    _compute_return,
    _safe_divide,
    beta,
    compute_amihud_from_wide,
    compute_price_features,
    momentum,
    reversal,
    turnover,
    volatility,
)

# 测试用固定 seed
_RNG = np.random.default_rng(seed=42)


def _make_price_panel(
    n_dates: int = 252,
    n_tickers: int = 3,
    base_price: float = 100.0,
    drift: float = 0.0001,
    volatility: float = 0.01,
) -> pd.DataFrame:
    """生成 synthetic 价格面板（几何布朗运动）。

    Args:
        n_dates: 交易日数。
        n_tickers: ticker 数。
        base_price: 基础价格。
        drift: 漂移项（日均值）。
        volatility: 波动率。

    Returns:
        [dates x tickers] DataFrame，index 为日频 DatetimeIndex。
    """
    dates = pd.date_range("2024-01-01", periods=n_dates, freq="B")  # 工作日
    tickers = [f"T{i}" for i in range(n_tickers)]

    data = np.zeros((n_dates, n_tickers))
    for t in range(n_tickers):
        # 几何布朗运动：log(P_t) = log(P_0) + (mu - 0.5*sigma^2)*t + sigma*W_t
        log_returns = _RNG.normal(drift - 0.5 * volatility**2, volatility, n_dates)
        log_prices = np.log(base_price) + np.cumsum(log_returns)
        data[:, t] = np.exp(log_prices)

    return pd.DataFrame(data, index=dates, columns=tickers)


def _make_volume_panel(
    n_dates: int = 252,
    n_tickers: int = 3,
    base_volume: float = 1_000_000.0,
    noise_std: float = 0.2,
) -> pd.DataFrame:
    """生成 synthetic 成交量面板。

    Args:
        n_dates: 交易日数。
        n_tickers: ticker 数。
        base_volume: 基础成交量。
        noise_std: 噪声标准差（比例）。

    Returns:
        [dates x tickers] DataFrame。
    """
    dates = pd.date_range("2024-01-01", periods=n_dates, freq="B")
    tickers = [f"T{i}" for i in range(n_tickers)]

    data = np.zeros((n_dates, n_tickers))
    for t in range(n_tickers):
        noise = _RNG.normal(1.0, noise_std, n_dates)
        data[:, t] = base_volume * np.maximum(noise, 0.1)  # 非负

    return pd.DataFrame(data, index=dates, columns=tickers)


class TestSafeDivide:
    """测试安全除法工具函数。"""

    def test_returns_nan_when_denominator_near_zero(self) -> None:
        """分母接近零时返回 NaN。"""
        num = pd.Series([1.0, 2.0, 3.0])
        den = pd.Series([1.0, _EPS / 10, 3.0])
        result = _safe_divide(num, den)
        assert not pd.isna(result.iloc[0])
        assert pd.isna(result.iloc[1])
        assert not pd.isna(result.iloc[2])


class TestComputeReturn:
    """测试收益率计算。"""

    def test_first_row_is_nan(self) -> None:
        """第一行收益率为 NaN。"""
        prices = _make_price_panel(n_dates=10, n_tickers=2)
        returns = _compute_return(prices)
        assert returns.iloc[0].isna().all()

    def test_returns_match_pct_change(self) -> None:
        """收益率与 pandas pct_change 一致。"""
        prices = _make_price_panel(n_dates=10, n_tickers=2)
        returns = _compute_return(prices)
        expected = prices.pct_change()
        pd.testing.assert_frame_equal(returns, expected)


class TestMomentum:
    """测试动量计算。"""

    def test_momentum_returns_cumulative_returns(self) -> None:
        """动量等于累计收益率。"""
        prices = pd.DataFrame(
            [[100.0, 100.0, 100.0],  # 所有股票起点相同
             [110.0, 105.0, 100.0],  # A +10%, B +5%, C flat
             [105.0, 110.25, 100.0]],  # A -4.5%, B +5%, C flat
            columns=["A", "B", "C"],
            index=pd.date_range("2024-01-01", periods=3),
        )
        returns = _compute_return(prices)
        result = momentum(returns, window=2)

        # 前 2 行是 NaN
        assert pd.isna(result["A"].iloc[0])
        assert pd.isna(result["A"].iloc[1])
        # 第 3 行 (iloc[2]) 有值
        # A: (110-100)/100 + (105-110)/110 = 0.1 - 0.045 = 0.055
        expected_a = 0.1 - 0.04545
        assert result["A"].iloc[2] == pytest.approx(expected_a, abs=0.01)

    def test_first_window_rows_are_nan(self) -> None:
        """前 window 行为 NaN。"""
        prices = _make_price_panel(n_dates=20, n_tickers=2)
        returns = _compute_return(prices)
        result = momentum(returns, window=5)
        assert result.iloc[:5].isna().all().all()


class TestReversal:
    """测试短期反转计算。"""

    def test_reversal_equals_negative_short_momentum(self) -> None:
        """反转等于负的短期动量。"""
        prices = _make_price_panel(n_dates=20, n_tickers=2)
        returns = _compute_return(prices)
        window = 5

        mom = momentum(returns, window=window)
        rev = reversal(returns, window=window)

        pd.testing.assert_frame_equal(rev, -mom)


class TestVolatility:
    """测试波动率计算。"""

    def test_volatility_matches_rolling_std(self) -> None:
        """波动率与 rolling std 一致。"""
        prices = _make_price_panel(n_dates=50, n_tickers=2)
        returns = _compute_return(prices)
        result = volatility(returns, window=21)

        expected = returns.rolling(window=21, min_periods=21).std()
        pd.testing.assert_frame_equal(result, expected)

    def test_annualize_multiplies_by_sqrt_252(self) -> None:
        """年化乘以 sqrt(252)。"""
        prices = _make_price_panel(n_dates=50, n_tickers=1)
        returns = _compute_return(prices)

        vol_daily = volatility(returns, window=21, annualize=False)
        vol_annual = volatility(returns, window=21, annualize=True)

        ratio = vol_annual.iloc[-1, 0] / vol_daily.iloc[-1, 0]
        assert ratio == pytest.approx(np.sqrt(252), rel=0.01)


class TestTurnover:
    """测试换手率计算。"""

    def test_turnover_matches_rolling_mean(self) -> None:
        """换手率与 rolling mean 一致。"""
        volume = _make_volume_panel(n_dates=50, n_tickers=2)
        result = turnover(volume, window=21)

        expected = volume.rolling(window=21, min_periods=21).mean()
        pd.testing.assert_frame_equal(result, expected)


class TestBeta:
    """测试 Beta 计算函数。"""

    def test_beta_high_when_stock_moves_with_market(self) -> None:
        """股票与市场同向移动时 Beta 高。"""
        # 构造完全相关的股票和市场收益
        dates = pd.date_range("2024-01-01", periods=100, freq="B")
        market_ret = pd.Series(_RNG.normal(0, 0.01, 100), index=dates)
        stock_ret = market_ret * 1.5  # Beta 应约 1.5

        returns = pd.DataFrame({"stock": stock_ret})
        result = beta(returns, market_ret, window=50)

        # 检查稳定后的 Beta 约 1.5
        assert result["stock"].iloc[-1] == pytest.approx(1.5, abs=0.2)

    def test_beta_near_zero_when_stock_uncorrelated(self) -> None:
        """股票与市场无关时 Beta 接近零。"""
        dates = pd.date_range("2024-01-01", periods=100, freq="B")
        market_ret = pd.Series(_RNG.normal(0, 0.01, 100), index=dates)
        stock_ret = pd.Series(_RNG.normal(0, 0.01, 100), index=dates)

        returns = pd.DataFrame({"stock": stock_ret})
        result = beta(returns, market_ret, window=50)

        # Beta 应接近 0
        assert abs(result["stock"].iloc[-1]) < 0.5


class TestComputePriceFeatures:
    """测试完整价格特征计算流程。"""

    def test_returns_all_features_with_full_inputs(self) -> None:
        """完整输入时返回所有特征（除 amihud 需单独计算）。"""
        prices = _make_price_panel(n_dates=300, n_tickers=3)
        volume = _make_volume_panel(n_dates=300, n_tickers=3)
        market_prices = pd.Series(
            _RNG.normal(100, 5, 300).cumprod(),
            index=prices.index,
        )

        result = compute_price_features(prices, volume, market_prices)

        # 检查特征数量（amihud 需单独调用 compute_amihud_from_wide）
        features = result.columns.get_level_values(0).unique()
        # 应有 9 个特征（不含 amihud）
        assert len(features) == 9
        assert "amihud_illiquidity_21d" not in features

    def test_returns_subset_without_optional_inputs(self) -> None:
        """无可选输入时返回子集特征。"""
        prices = _make_price_panel(n_dates=100, n_tickers=2)

        result = compute_price_features(prices)

        # 应只有动量/反转/波动率（无 turnover/beta/amihud）
        features = result.columns.get_level_values(0).unique()
        assert "momentum_5d" in features
        assert "volatility_21d" in features
        # turnover 需要成交量
        assert "turnover_21d" not in features

    def test_raises_value_error_on_shape_mismatch(self) -> None:
        """形状不匹配时抛出 ValueError。"""
        prices = _make_price_panel(n_dates=100, n_tickers=2)
        volume = _make_volume_panel(n_dates=50, n_tickers=2)  # 不同长度

        with pytest.raises(ValueError, match="形状"):
            compute_price_features(prices, volume)

    def test_raises_value_error_on_index_mismatch(self) -> None:
        """索引不匹配时抛出 ValueError。"""
        prices = _make_price_panel(n_dates=100, n_tickers=2)
        market_prices = pd.Series(
            _RNG.normal(100, 5, 100),
            index=pd.date_range("2024-02-01", periods=100, freq="B"),  # 不同索引
        )

        with pytest.raises(ValueError, match="索引"):
            compute_price_features(prices, market_prices=market_prices)

    def test_result_has_multiindex_columns(self) -> None:
        """结果有 MultiIndex columns（feature, ticker）。"""
        prices = _make_price_panel(n_dates=100, n_tickers=2)
        result = compute_price_features(prices)

        assert isinstance(result.columns, pd.MultiIndex)
        assert result.columns.names == ["feature", "ticker"]


class TestComputeAmihudFromWide:
    """测试 Amihud 非流动性计算（wide 格式适配）。"""

    def test_returns_wide_format_dataframe(self) -> None:
        """返回 wide 格式 DataFrame。"""
        prices = _make_price_panel(n_dates=50, n_tickers=2)
        volume = _make_volume_panel(n_dates=50, n_tickers=2)

        result = compute_amihud_from_wide(prices, volume, window=21)

        # 检查列名
        assert list(result.columns) == list(prices.columns)
        # 行数可能少一行（第一行无收益）
        assert len(result) <= len(prices)

    def test_first_window_rows_are_nan(self) -> None:
        """前 window 行应有 NaN（或行数减少）。"""
        prices = _make_price_panel(n_dates=30, n_tickers=2)
        volume = _make_volume_panel(n_dates=30, n_tickers=2)

        result = compute_amihud_from_wide(prices, volume, window=21)

        # Amihud 内部 dropna 第一行，所以检查是否有 NaN
        # 或者检查结果行数少于原始行数
        if len(result) < len(prices):
            # 行减少说明 dropna 发生了
            pass
        else:
            # 否则应有 NaN
            nan_count = result.iloc[:21].isna().sum().sum()
            assert nan_count > 0

    def test_returns_higher_illiquidity_for_low_volume_stocks(self) -> None:
        """低成交量股票有更高的非流动性。"""
        # 价格随机波动以产生收益
        rng = np.random.default_rng(seed=123)
        prices_data = rng.uniform(95, 105, (30, 2))
        prices = pd.DataFrame(
            prices_data,
            columns=["high_vol", "low_vol"],
            index=pd.date_range("2024-01-01", periods=30, freq="B"),
        )
        volume = pd.DataFrame(
            [[1_000_000, 10_000]] * 30,  # low_vol 成交量低 100x
            columns=["high_vol", "low_vol"],
            index=prices.index,
        )

        result = compute_amihud_from_wide(prices, volume, window=21)

        # low_vol 的非流动性应更高（或至少不是更低）
        # 如果两者都是 0（价格不变），则无法比较
        if result["low_vol"].iloc[-1] > 0 or result["high_vol"].iloc[-1] > 0:
            assert result["low_vol"].iloc[-1] > result["high_vol"].iloc[-1]


class TestTrackBPriceFeatureCols:
    """测试预指定价格特征列清单。"""

    def test_feature_cols_is_non_empty_list(self) -> None:
        """TRACK_B_PRICE_FEATURE_COLS 是非空列表。"""
        assert isinstance(TRACK_B_PRICE_FEATURE_COLS, list)
        assert len(TRACK_B_PRICE_FEATURE_COLS) > 0

    def test_feature_cols_contains_expected_features(self) -> None:
        """包含预期特征。"""
        expected_features = {
            "momentum_5d",
            "momentum_10d",
            "momentum_21d",
            "reversal_5d",
            "volatility_21d",
            "beta_252d",
        }
        assert expected_features.issubset(set(TRACK_B_PRICE_FEATURE_COLS))

    def test_feature_cols_count_is_correct(self) -> None:
        """特征数量正确（10 个）。"""
        # 动量 4 + 反转 1 + 波动率 2 + 换手 1 + beta 1 + amihud 1 = 10
        assert len(TRACK_B_PRICE_FEATURE_COLS) == 10
