#!/usr/bin/env python
"""Track B wheel-mount 分析：tearsheet + FF5 残差。

复用现有 adapter（tearsheet_adapter / ff5_residual），在真实月度组合收益上运行：
- wheel-mount①：tearsheet 风险指标（sharpe/sortino/max_drawdown/calmar/omega）
- wheel-mount③：FF5 残差回归（α + 5 betas + R²）

输入：site/track_b_data.json（treatment / price_only 的月度收益）
输出：site/mount_metrics.json（供站点展示）

不写 ledger、不触冻结面、不跑模型。
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import structlog

from aionis.eval.ff5_residual import ff5_residual_regression, load_ff5
from aionis.eval.tearsheet_adapter import tearsheet_summary

log = structlog.get_logger()

# 路径常量
TRACK_B_DATA = Path("site/track_b_data.json")
MOUNT_METRICS_OUTPUT = Path("site/mount_metrics.json")


def load_track_b_data(path: Path) -> dict:
    """加载 Track B 数据。

    Returns:
        dict: {treatment: {monthly_dates, monthly_model_returns, monthly_ew_returns},
               price_only: {...}}
    """
    if not path.exists():
        raise FileNotFoundError(f"Track B 数据不存在: {path}")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    # 输入校验：必需字段
    for arm in ("treatment", "price_only"):
        if arm not in data:
            raise ValueError(f"数据缺少臂: {arm}")
        required = ("monthly_dates", "monthly_model_returns", "monthly_ew_returns")
        missing = [k for k in required if k not in data[arm]]
        if missing:
            raise ValueError(f"{arm} 缺少字段: {missing}")

    log.info("track_b_data_loaded", arms=list(data.keys()))
    return data


def make_series(dates: list[str], returns: list[float]) -> pd.Series:
    """将日期列表 + 收益列表转为 pd.Series。

    日期格式：YYYY-MM (e.g., "2021-01")
    索引：月末日期（转为 pandas Timestamp）

    Args:
        dates: 月度日期列表（YYYY-MM 格式）
        returns: 月度收益列表

    Returns:
        pd.Series: 索引为月末日期的收益序列
    """
    # 将 YYYY-MM 转为月末日期
    index = [pd.to_datetime(d).to_period("M").to_timestamp("M") for d in dates]
    return pd.Series(returns, index=index)


def compute_ff5_for_arm(
    arm_data: dict, arm_name: str
) -> dict | None:
    """为单个臂计算 FF5 残差回归。

    Args:
        arm_data: {monthly_dates, monthly_model_returns, monthly_ew_returns}
        arm_name: 臂名称（treatment / price_only）

    Returns:
        FF5Regression dict 或 None（网络失败时）
    """
    try:
        # 构造 pd.Series
        dates = arm_data["monthly_dates"]
        returns = arm_data["monthly_model_returns"]
        strategy = make_series(dates, returns)

        # 确定日期范围（FF5 需要 start/end）
        start = strategy.index.min().strftime("%Y-%m-%d")
        end = strategy.index.max().strftime("%Y-%m-%d")

        log.info("loading_ff5", arm=arm_name, start=start, end=end)
        ff5_data = load_ff5(start, end)

        # 运行回归
        result = ff5_residual_regression(strategy, ff5_data)

        log.info(
            "ff5_regression_done",
            arm=arm_name,
            alpha=result["alpha"],
            r_squared=result["r_squared"],
            n_obs=result["n_obs"],
        )

        return result

    except Exception as e:
        log.warning("ff5_failed", arm=arm_name, error=str(e))
        return None


def compute_mount_metrics(data: dict) -> dict:
    """计算所有臂的 mount 指标。

    Args:
        data: Track B 数据（treatment / price_only）

    Returns:
        dict: {treatment: {tearsheet: {...}, ff5: {...}|null},
               price_only: {...}}
    """
    output = {}

    for arm_name, arm_data in data.items():
        if arm_name == "differential":
            continue  # 跳过 differential

        log.info("processing_arm", arm=arm_name)

        # 1. Tearsheet
        model_returns = arm_data["monthly_model_returns"]
        ew_returns = arm_data["monthly_ew_returns"]

        tearsheet = tearsheet_summary(model_returns, ew_returns)

        # 2. FF5
        ff5 = compute_ff5_for_arm(arm_data, arm_name)

        output[arm_name] = {
            "tearsheet": tearsheet,
            "ff5": ff5,
        }

    return output


def save_metrics(metrics: dict, path: Path) -> None:
    """持久化 mount_metrics.json。

    Args:
        metrics: {arm: {tearsheet, ff5}}
        path: 输出路径
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    # 序列化时处理 NaN
    def json_serializer(obj):
        if isinstance(obj, (np.floating, float)):
            if np.isnan(obj) or np.isinf(obj):
                return None
            return float(obj)
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, pd.Series):
            return obj.tolist()
        raise TypeError(f"无法序列化: {type(obj)}")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, default=json_serializer, indent=2)

    log.info("mount_metrics_saved", path=str(path))


def print_summary(metrics: dict) -> None:
    """打印控制台摘要。

    Args:
        metrics: {arm: {tearsheet, ff5}}
    """
    print("\n=== Track B Mount 指标摘要 ===\n")

    for arm_name, arm_metrics in metrics.items():
        print(f"【{arm_name}】")

        # Tearsheet 关键指标
        ts = arm_metrics["tearsheet"]
        model = ts.get("model", {})

        sharpe = model.get("sharpe_ratio")
        max_dd = model.get("max_drawdown")
        annual_ret = model.get("annual_return")

        print(f"  Sharpe: {sharpe:.3f}" if sharpe is not None else "  Sharpe: N/A")
        print(f"  Max Drawdown: {max_dd:.3f}" if max_dd is not None else "  Max Drawdown: N/A")
        print(
            f"  年化收益: {annual_ret:.3f}"
            if annual_ret is not None
            else "  年化收益: N/A"
        )

        # FF5 关键指标
        ff5 = arm_metrics["ff5"]
        if ff5 is not None:
            alpha = ff5.get("alpha")
            alpha_t = ff5.get("alpha_t")
            r2 = ff5.get("r_squared")
            print(
                f"  FF5 α: {alpha:.4f} (t={alpha_t:.2f})"
                if alpha is not None
                else "  FF5 α: N/A"
            )
            print(f"  FF5 R²: {r2:.3f}" if r2 is not None else "  FF5 R²: N/A")
        else:
            print("  FF5: 未取得（网络失败）")

        print()

    print(f"详细指标已写入: {MOUNT_METRICS_OUTPUT}")


def main() -> None:
    """主流程。"""
    # 1. 加载数据
    data = load_track_b_data(TRACK_B_DATA)

    # 2. 计算指标
    metrics = compute_mount_metrics(data)

    # 3. 持久化
    save_metrics(metrics, MOUNT_METRICS_OUTPUT)

    # 4. 打印摘要
    print_summary(metrics)


if __name__ == "__main__":
    main()
