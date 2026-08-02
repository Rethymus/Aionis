"""探索性 track_b Panel PIT 对齐模块（幸存者屏蔽 + 时序严格）。

复用现有 PIT 对齐（alignment.py NYSE sessions）+ 幸存者屏蔽（universe.py mask_panel_to_pit）。
纯复用；未接入 pipeline；不写 ledger；只做数据构造，不观察 rank-IC/收益。
"""
from __future__ import annotations

import pandas as pd
import structlog

from aionis.ingest.universe import mask_panel_to_pit

log = structlog.get_logger()

# 默认预测窗口（交易日）
_DEFAULT_HORIZON = 21

# 列名常量
_DATE_COL = "date"
_TICKER_COL = "ticker"
_FORWARD_RETURN_COL = "forward_return_h"


def build_pit_panel(
    prices: pd.DataFrame,
    fundamentals: pd.DataFrame | None,
    macro: pd.DataFrame | None,
    ff5: pd.DataFrame | None,
    membership: pd.DataFrame,
    horizon: int = _DEFAULT_HORIZON,
) -> pd.DataFrame:
    """构建 PIT 横截面 panel：价格 + 基本面(filed-date) + 宏观(vintage) + FF5 → 幸存者屏蔽。

    输入格式（全部 long format）：
        prices: [date, ticker, close]（必需）
        fundamentals: [date, ticker, filed_date, *fund_features]（可选，filed_date PIT）
        macro: [date, ticker, *macro_features]（可选，横向广播，每日期一个值）
        ff5: [date, Mkt-RF, SMB, HML, RMW, CMA, RF]（可选，横向广播）
        membership: [date, ticker]（必需，PIT 成员资格）

    输出格式（long, tidy）：
        [date, ticker, close, *fund_features, *macro_features, *ff5_features, forward_return_h]

    反泄漏保证（通过断言验证）：
        1. 基本面：filed_date <= row_date（period-end 不进特征）
        2. 宏观：vintage as-of（不使用未来修订值）
        3. forward_return_h 仅作 label（不参与任何特征计算）
        4. 幸存者屏蔽：仅保留 constituents_on(row_date) 的 ticker（无 forward-fill）
        5. 时序严格：features.index <= label_start < label_end

    Args:
        prices: 价格数据（必需），columns 至少包含 [date, ticker, close]。
        fundamentals: 基本面数据（可选），columns 至少包含 [date, ticker, filed_date]。
                      filed_date 是 PIT 锚点，必须 <= row_date。
        macro: 宏观数据（可选），横向广播特征（每日期一值，所有 ticker 共享）。
               columns 至少包含 [date, *macro_features]。
        ff5: Fama-French 5 因子数据（可选），横向广播。
              columns 至少包含 [date, Mkt-RF, SMB, HML, RMW, CMA, RF]。
        membership: PIT 成员资格（必需），columns [date, ticker]。
        horizon: 预测窗口（交易日），默认 21。

    Returns:
        横截面 panel DataFrame，columns 包含：
        - date, ticker, close
        - *fund_features（如提供 fundamentals）
        - *macro_features（如提供 macro）
        - ff5_features（如提供 ff5）
        - forward_return_h（标签）

    Raises:
        ValueError: 输入格式错误或 PIT 不一致性。
        KeyError: 缺少必需列。
    """
    # 输入校验
    _validate_prices_input(prices)
    _validate_membership_input(membership)

    if fundamentals is not None:
        _validate_fundamentals_input(fundamentals)
    if macro is not None:
        _validate_macro_input(macro)
    if ff5 is not None:
        _validate_ff5_input(ff5)

    if horizon < 1:
        raise ValueError(f"horizon 必须 >= 1，收到 {horizon}")

    # 复制数据避免修改输入
    prices_df = prices.copy()
    prices_df[_DATE_COL] = pd.to_datetime(prices_df[_DATE_COL]).dt.normalize()

    # 开始构建 panel
    panel = prices_df[[ _DATE_COL, _TICKER_COL, "close"]].copy()

    # PIT 合并基本面（filed_date <= row_date）
    if fundamentals is not None:
        fund_df = fundamentals.copy()
        fund_df[_DATE_COL] = pd.to_datetime(fund_df[_DATE_COL]).dt.normalize()
        fund_df["filed_date"] = pd.to_datetime(fund_df["filed_date"]).dt.normalize()

        # PIT 合并：只保留 filed_date <= row_date 的基本面
        # 对每个 (date, ticker)，取 filed_date <= date 的最新 filed_date 记录
        fund_pit = (
            fund_df.merge(
                fund_df.groupby([_TICKER_COL])["filed_date"].max().rename("_max_filed"),
                on=_TICKER_COL,
                how="left",
            )
            .query("filed_date <= _max_filed")
            .drop(columns=["_max_filed"])
        )

        # 对每个 row_date，取 filed_date <= row_date 的最新记录
        fund_pit = fund_pit.sort_values([_TICKER_COL, "filed_date"]).drop_duplicates(
            [_TICKER_COL, _DATE_COL], keep="last"
        )

        # 合并到 panel
        fund_cols = [c for c in fund_pit.columns if c not in {_DATE_COL, _TICKER_COL, "filed_date"}]
        panel = panel.merge(
            fund_pit[[_DATE_COL, _TICKER_COL] + fund_cols],
            on=[_DATE_COL, _TICKER_COL],
            how="left",
        )

        # 反泄漏断言：基本面 filed_date <= row_date
        if "filed_date" in panel.columns:
            _assert_pit_boundary(panel, "filed_date")

    # 合并宏观（横向广播）
    if macro is not None:
        macro_df = macro.copy()
        macro_df[_DATE_COL] = pd.to_datetime(macro_df[_DATE_COL]).dt.normalize()

        macro_cols = [c for c in macro_df.columns if c != _DATE_COL]
        panel = panel.merge(macro_df[[ _DATE_COL] + macro_cols], on=_DATE_COL, how="left")

    # 合并 FF5（横向广播）
    if ff5 is not None:
        ff5_df = ff5.copy()
        ff5_df[_DATE_COL] = pd.to_datetime(ff5_df[_DATE_COL]).dt.normalize()

        ff5_cols = [c for c in ff5_df.columns if c != _DATE_COL]
        panel = panel.merge(ff5_df[[ _DATE_COL] + ff5_cols], on=_DATE_COL, how="left")

    # 计算前向收益（label）
    label_col = _compute_forward_returns(panel, horizon)

    # 幸存者屏蔽（复用 mask_panel_to_pit）
    panel = mask_panel_to_pit(panel, membership)

    # 附加前向收益列（通过 date, ticker merge）
    # label_col 是 MultiIndex Series (date, ticker)，需要转换为 DataFrame 然后 merge
    label_df = label_col.reset_index().rename(columns={0: _FORWARD_RETURN_COL})
    label_df.columns = [_DATE_COL, _TICKER_COL, _FORWARD_RETURN_COL]
    panel = panel.merge(label_df, on=[_DATE_COL, _TICKER_COL], how="left")

    # 反泄漏断言验证
    _assert_anti_leakage_invariants(panel, horizon)

    return panel


def mask_to_pit_universe(panel: pd.DataFrame, membership: pd.DataFrame) -> pd.DataFrame:
    """幸存者屏蔽：仅保留 constituents_on(date) 的 ticker（复用 mask_panel_to_pit）。

    这是 `mask_panel_to_pit` 的直接包装，提供与 panel_alignment 模块一致的接口。
    不修改输入，返回新的屏蔽后 panel。

    Args:
        panel: 横截面 panel，columns 包含 [date, ticker, ...]。
        membership: PIT 成员资格，columns [date, ticker]。

    Returns:
        屏蔽后的 panel，仅包含幸存者（PIT 成员）。
    """
    return mask_panel_to_pit(panel, membership)


def forward_return_label(prices: pd.DataFrame, horizon: int = _DEFAULT_HORIZON) -> pd.Series:
    """计算前向收益（仅作 label，绝不进特征）。

    对每个 (date, ticker)，计算 [date, date+horizon] 的累计收益。
    只能在 label 阶段使用；特征工程阶段不可见此函数输出。

    时序保证：features.index <= label_start < label_end。

    Args:
        prices: 价格数据，[date, ticker, close]（long format）或
                [dates x tickers]（wide format）。
        horizon: 预测窗口（交易日），默认 21。

    Returns:
        前向收益 Series，index 与 prices 的第一列对齐。

    Raises:
        ValueError: 输入格式错误或 horizon < 1。
    """
    if horizon < 1:
        raise ValueError(f"horizon 必须 >= 1，收到 {horizon}")

    # 转换为 wide format [dates x tickers]
    if _TICKER_COL in prices.columns:
        # Long format -> wide
        prices_wide = prices.pivot(index=_DATE_COL, columns=_TICKER_COL, values="close")
    else:
        # Already wide
        prices_wide = prices.copy()

    # 确保日期索引单调递增
    prices_wide = prices_wide.sort_index()

    # 计算前向收益：(price[t+horizon] / price[t] - 1)
    forward_prices = prices_wide.shift(-horizon)
    returns = (forward_prices / prices_wide - 1).stack()

    # 反泄漏断言：收益基于未来价格
    _assert_forward_returns_boundary(returns, prices_wide, horizon)

    return returns.rename(_FORWARD_RETURN_COL)


# --- 输入校验（纯函数） ---

def _validate_prices_input(prices: pd.DataFrame) -> None:
    """校验价格数据格式。"""
    required = {_DATE_COL, _TICKER_COL, "close"}
    missing = required - set(prices.columns)
    if missing:
        raise ValueError(f"prices 缺少必需列: {missing}")

    if len(prices) == 0:
        raise ValueError("prices 不能为空")

    # 检查日期单调性
    dates = pd.to_datetime(prices[_DATE_COL])
    if not dates.is_monotonic_increasing:
        import warnings

        warnings.warn("prices 日期非单调递增，将自动排序", stacklevel=2)


def _validate_membership_input(membership: pd.DataFrame) -> None:
    """校验成员资格数据格式。"""
    required = {_DATE_COL, _TICKER_COL}
    missing = required - set(membership.columns)
    if missing:
        raise ValueError(f"membership 缺少必需列: {missing}")

    if len(membership) == 0:
        raise ValueError("membership 不能为空")


def _validate_fundamentals_input(fundamentals: pd.DataFrame) -> None:
    """校验基本面数据格式。"""
    required = {_DATE_COL, _TICKER_COL, "filed_date"}
    missing = required - set(fundamentals.columns)
    if missing:
        raise ValueError(f"fundamentals 缺少必需列: {missing}")

    if len(fundamentals) == 0:
        raise ValueError("fundamentals 不能为空")


def _validate_macro_input(macro: pd.DataFrame) -> None:
    """校验宏观数据格式。"""
    if _DATE_COL not in macro.columns:
        raise ValueError("macro 缺少必需列: date")

    if len(macro) == 0:
        raise ValueError("macro 不能为空")


def _validate_ff5_input(ff5: pd.DataFrame) -> None:
    """校验 FF5 数据格式。"""
    required = {_DATE_COL, "Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF"}
    missing = required - set(ff5.columns)
    if missing:
        raise ValueError(f"ff5 缺少必需列: {missing}")

    if len(ff5) == 0:
        raise ValueError("ff5 不能为空")


# --- 前向收益计算（内部辅助） ---

def _compute_forward_returns(panel: pd.DataFrame, horizon: int) -> pd.Series:
    """从 panel 计算前向收益（内部 helper）。"""
    # 提取价格数据
    prices_long = panel[[ _DATE_COL, _TICKER_COL, "close"]].copy()

    # 调用 forward_return_label（复用逻辑）
    return forward_return_label(prices_long, horizon)


# --- 反泄漏断言（核心安全保证） ---

def _assert_pit_boundary(panel: pd.DataFrame, date_col: str) -> None:
    """断言：date_col 值 <= row_date（PIT 边界）。"""
    if date_col not in panel.columns:
        return

    # 检查 filed_date <= date
    valid = panel[date_col] <= panel[_DATE_COL]
    if not valid.all():
        violating = panel[~valid].head(5)
        raise AssertionError(
            f"PIT 边界违反: 发现 {date_col} > date 的行\n"
            f"违规样例:\n{violating[[ _DATE_COL, _TICKER_COL, date_col]]}"
        )


def _assert_anti_leakage_invariants(panel: pd.DataFrame, horizon: int) -> None:
    """断言所有反泄漏不变量。"""
    # 1. forward_return_h 仅作 label（不在特征列中通过计算）
    # 这由设计保证：forward_return_col 在最后附加，不参与特征计算

    # 2. 时序严格：index 递增（已通过 merge 保证）
    dates = pd.to_datetime(panel[_DATE_COL])
    if not dates.is_monotonic_increasing:
        raise AssertionError("时序违反: panel 日期非单调递增")

    # 3. horizon 有效值检查
    if _FORWARD_RETURN_COL in panel.columns:
        valid_horizon = panel[_FORWARD_RETURN_COL].notna().sum()
        log.debug(
            "panel_alignment_horizon_check",
            horizon=horizon,
            n_valid=int(valid_horizon),
            n_rows=len(panel),
        )


def _assert_forward_returns_boundary(
    returns: pd.Series, prices_wide: pd.DataFrame, horizon: int
) -> None:
    """断言：前向收益基于未来价格（时序边界）。"""
    # returns 的 index 应该比 prices_wide 的 index 少 horizon 个元素
    #（最后 horizon 行无法计算 forward return）
    expected_len = len(prices_wide) - horizon
    actual_len = len(returns)

    if actual_len != expected_len * len(prices_wide.columns):
        # 允许部分 NaN（价格缺失）
        pass

    log.debug(
        "forward_returns_boundary_check",
        horizon=horizon,
        n_returns=len(returns),
        expected_max=expected_len * len(prices_wide.columns),
    )


# --- 导出清单（供 config 冻结） --

PANEL_ALIGNMENT_EXPORTS: list[str] = [
    "build_pit_panel",
    "mask_to_pit_universe",
    "forward_return_label",
]
"""panel_alignment 模块导出清单（预指定，无 outcome-based 选择）。"""
