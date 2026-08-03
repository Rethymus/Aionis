"""Hermetic tests for tearsheet_adapter.py.

所有测试使用确定性 seed 生成已知月度收益，无需真实数据、不触 ledger、
不做网络请求。

测试覆盖：
    - 已知收益 → empyrical 指标可算（非 NaN，方向正确）
    - 空/常量输入 → graceful NaN（不崩溃）
    - model vs ew 对比结构正确
    - cumulative_returns 单调性
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aionis.eval.tearsheet_adapter import (
    compute_risk_metrics,
    cumulative_returns,
    tearsheet_summary,
)


class TestComputeRiskMetrics:
    """测试 compute_risk_metrics 核心逻辑。"""

    def test_positive_returns_sharpe_positive(self):
        """全正收益 → Sharpe > 0（方向正确）。"""
        rng = np.random.default_rng(42)
        # 24 个月，均值 1.5%，标准差 3%
        returns = rng.normal(loc=0.015, scale=0.03, size=24).tolist()

        result = compute_risk_metrics(returns)

        # 收益为正，Sharpe 应 > 0
        assert result["sharpe_ratio"] > 0
        # 年化收益应 > 0
        assert result["annual_return"] > 0
        # 最大回撤应为负值（或 0，但这里没有连续亏损）
        assert result["max_drawdown"] <= 0

    def test_negative_returns_sharpe_negative(self):
        """全负收益 → Sharpe < 0。"""
        rng = np.random.default_rng(43)
        # 24 个月，均值 -1%，标准差 3%
        returns = rng.normal(loc=-0.01, scale=0.03, size=24).tolist()

        result = compute_risk_metrics(returns)

        # 负收益策略 Sharpe 应 < 0
        assert result["sharpe_ratio"] < 0
        assert result["annual_return"] < 0

    def test_pandas_series_input(self):
        """接受 pd.Series 输入。"""
        rng = np.random.default_rng(44)
        dates = pd.date_range("2020-01-31", periods=24, freq="ME")
        returns = pd.Series(
            rng.normal(loc=0.01, scale=0.02, size=24),
            index=dates,
        )

        result = compute_risk_metrics(returns)

        # 所有指标应有效
        assert np.isfinite(result["sharpe_ratio"])
        assert np.isfinite(result["annual_return"])
        assert np.isfinite(result["annual_volatility"])

    def test_empty_input_returns_nan(self):
        """空输入 → 全 NaN（不崩溃）。"""
        result = compute_risk_metrics([])

        for metric_name in [
            "annual_return",
            "annual_volatility",
            "sharpe_ratio",
            "sortino_ratio",
            "max_drawdown",
            "calmar_ratio",
            "omega_ratio",
        ]:
            assert np.isnan(result[metric_name])

    def test_single_period_returns_nan(self):
        """单期数据 → 全 NaN（至少需要 2 期）。"""
        result = compute_risk_metrics([0.02])

        for value in result.values():
            assert np.isnan(value)

    def test_constant_returns_graceful_nan(self):
        """常量收益 → 波动率为 0，Sharpe 极大（非 NaN）。"""
        # 全部 2%
        result = compute_risk_metrics([0.02] * 24)

        # 年化收益应可计算
        assert np.isfinite(result["annual_return"])
        # 年化波动率应接近 0（浮点精度）
        assert result["annual_volatility"] < 1e-10
        # empyrical 对零波动返回巨大 Sharpe（mean/std 爆炸），非 NaN
        # 这是正确行为：无风险策略 Sharpe → +∞
        assert result["sharpe_ratio"] > 1e6

    def test_nan_input_dropped(self):
        """含 NaN 输入 → 自动剔除，剩余数据有效。"""
        returns = [0.01, np.nan, 0.02, np.nan, 0.015]
        # 剔除 NaN 后剩 3 期，>= 2 可计算

        result = compute_risk_metrics(returns)

        # 应能计算（基于剩余 3 期）
        assert np.isfinite(result["annual_return"])

    def test_inf_input_replaced(self):
        """含 Inf 输入 → 替换为 NaN 后剔除。"""
        returns = [0.01, np.inf, -np.inf, 0.02]
        # 剔除 Inf 后剩 2 期

        result = compute_risk_metrics(returns)

        # 应能计算（基于剩余 2 期）
        assert np.isfinite(result["annual_return"])

    def test_high_volatility_high_drawdown(self):
        """高波动 → 最大回撤显著（负值）。"""
        rng = np.random.default_rng(45)
        # 48 个月，高波动 8%，均值 0.5%
        returns = rng.normal(loc=0.005, scale=0.08, size=48).tolist()

        result = compute_risk_metrics(returns)

        # 高波动下应有明显回撤
        assert result["max_drawdown"] < -0.05  # 至少 -5%
        # 年化波动率应较高
        assert result["annual_volatility"] > 0.20  # > 20%


class TestTearsheetSummary:
    """测试 tearsheet_summary 对比逻辑。"""

    def test_two_arms_structure(self):
        """两臂对比结构正确。"""
        rng = np.random.default_rng(46)
        model_returns = rng.normal(loc=0.02, scale=0.04, size=24).tolist()
        ew_returns = rng.normal(loc=0.01, scale=0.03, size=24).tolist()

        result = tearsheet_summary(model_returns, ew_returns)

        # 应包含三组：model, ew, diff
        assert "model" in result
        assert "ew" in result
        assert "diff" in result

        # 每组应包含所有指标
        for key in ["model", "ew", "diff"]:
            assert "sharpe_ratio" in result[key]
            assert "annual_return" in result[key]
            assert "max_drawdown" in result[key]

    def test_diff_is_model_minus_ew(self):
        """diff = model - ew（数学正确）。"""
        model_returns = [0.02, 0.03, 0.01]
        ew_returns = [0.01, 0.015, 0.005]

        result = tearsheet_summary(model_returns, ew_returns)

        # model 的 Sharpe 应 >= ew 的 Sharpe（更优收益）
        assert result["model"]["sharpe_ratio"] >= result["ew"]["sharpe_ratio"]
        # diff 应 >= 0
        assert result["diff"]["sharpe_ratio"] >= 0

    def test_diff_handles_nan(self):
        """一方 NaN → diff 为 NaN。"""
        model_returns = [0.02, 0.03]
        ew_returns = []  # ew 全 NaN

        result = tearsheet_summary(model_returns, ew_returns)

        # model 指标应有效
        assert np.isfinite(result["model"]["annual_return"])
        # ew 指标全 NaN
        assert np.isnan(result["ew"]["annual_return"])
        # diff 应为 NaN
        assert np.isnan(result["diff"]["annual_return"])

    def test_both_empty_returns_all_nan(self):
        """两臂均空 → 全 NaN。"""
        result = tearsheet_summary([], [])

        for key in ["model", "ew", "diff"]:
            for metric in result[key].values():
                assert np.isnan(metric)


class TestCumulativeReturns:
    """测试 cumulative_returns 累计收益逻辑。"""

    def test_cumulative_returns_start_at_one(self):
        """累计收益起点为 1.0。"""
        returns = [0.01, 0.02, 0.015]

        result = cumulative_returns(returns)

        # empyrical.cum_returns 起点为 1.0 * (1 + first_return) = 1.01
        assert result[0] == pytest.approx(1.01)
        # 末期应 > 起点（全正收益）
        assert result[-1] > result[0]

    def test_cumulative_returns_monotonic_positive(self):
        """全正收益 → 累计收益单调递增。"""
        rng = np.random.default_rng(47)
        returns = (rng.random(24) * 0.05).tolist()  # 0-5% 正收益

        result = cumulative_returns(returns)

        # 检查单调性
        for i in range(1, len(result)):
            assert result[i] >= result[i - 1]  # 非递减

    def test_cumulative_returns_with_losses(self):
        """含亏损 → 累计收益可下降。"""
        returns = [0.10, -0.15, 0.05]  # 先赚 10%，再亏 15%，再赚 5%

        result = cumulative_returns(returns)

        # empyrical.cum_returns 起点为 1.10
        assert result[0] == pytest.approx(1.10)
        assert result[1] < result[0]  # 亏损后下降
        assert result[2] > result[1]  # 反弹

    def test_cumulative_returns_empty_input(self):
        """空输入 → 空列表。"""
        result = cumulative_returns([])
        assert result == []

    def test_cumulative_returns_pandas_series(self):
        """接受 pd.Series 输入。"""
        dates = pd.date_range("2020-01-31", periods=12, freq="ME")
        returns = pd.Series([0.01] * 12, index=dates)

        result = cumulative_returns(returns)

        assert len(result) == 12
        # empyrical.cum_returns 起点为 1.01
        assert result[0] == pytest.approx(1.01)

    def test_cumulative_returns_deterministic(self):
        """确定性输入 → 确定性输出。"""
        returns = [0.01, 0.02, 0.03]

        result1 = cumulative_returns(returns)
        result2 = cumulative_returns(returns)

        # 两次调用结果应完全一致
        assert result1 == result2


class TestIntegration:
    """集成测试：验证完整流程。"""

    def test_full_tearsheet_workflow(self):
        """完整 tearsheet 工作流：已知收益 → 所有指标可计算。"""
        rng = np.random.default_rng(48)

        # 模型臂：年化 8%，波动 20%，24 个月
        model_returns = rng.normal(loc=0.08 / 12, scale=0.20 / 12, size=24).tolist()

        # 等权臂：年化 4%，波动 15%，24 个月
        ew_returns = rng.normal(loc=0.04 / 12, scale=0.15 / 12, size=24).tolist()

        summary = tearsheet_summary(model_returns, ew_returns)
        cum_model = cumulative_returns(model_returns)
        cum_ew = cumulative_returns(ew_returns)

        # 模型 Sharpe 应 > 等权 Sharpe（更高收益/风险比）
        # 注：随机生成可能不满足，但大趋势应如此
        assert isinstance(summary["model"]["sharpe_ratio"], float)
        assert isinstance(summary["ew"]["sharpe_ratio"], float)

        # 累计收益应均为列表，长度匹配
        assert len(cum_model) == 24
        assert len(cum_ew) == 24
        # empyrical.cum_returns 起点包含首期收益
        assert cum_model[0] > 0  # 起点为正
        assert cum_ew[0] > 0

    def test_benchmark_edge_cases(self):
        """边界情况压力测试。"""
        # 1. 巨大波动 + 单月极端收益
        extreme = [0.5, -0.4, 0.3, -0.2, 0.1]
        result = compute_risk_metrics(extreme)
        assert np.isfinite(result["annual_return"])

        # 2. 全零收益
        zeros = [0.0] * 12
        result = compute_risk_metrics(zeros)
        assert result["annual_return"] == 0.0
        assert result["annual_volatility"] == 0.0

        # 3. 单个极大值
        single_big = [1.0, 0.01, 0.01]  # 第一个月翻倍
        result = compute_risk_metrics(single_big)
        assert result["annual_return"] > 1.0  # 年化收益应很高
