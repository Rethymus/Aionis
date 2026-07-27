"""Market-state features — provably point-in-time.

Every function here slices ``prices.loc[:t_info_date]`` so it is mathematically
impossible to read a close at or after ``label_start_date``. The behavioral
leakage test in ``tests/test_alignment.py`` perturbs all prices after
``t_info_date`` and asserts the features are unchanged.
"""

from __future__ import annotations

import pandas as pd

# Rolling lookbacks in trading sessions.
_LOOKBACKS = {"1d": 1, "5d": 5, "21d": 21}
_MIN_HISTORY = 22  # need >= 22 closes for the 21d windows


def _ret(series: pd.Series, lookback: int) -> float:
    if len(series) <= lookback:
        return float("nan")
    return float(series.iloc[-1] / series.iloc[-1 - lookback] - 1.0)


def _vol(series: pd.Series, lookback: int) -> float:
    if len(series) <= lookback:
        return float("nan")
    return float(series.pct_change().iloc[-lookback:].std(ddof=0))


def market_state_features(
    prices: pd.DataFrame,
    t_info_date: pd.Timestamp,
    symbol: str,
    benchmark: str = "SPY",
) -> dict[str, float]:
    """Symbol-relative market-state features as of ``t_info_date`` (inclusive).

    ``prices`` is a wide DataFrame (index = NYSE session date, columns = symbols,
    values = adjusted close). Only data up to and including ``t_info_date`` is
    read; columns describe the target ``symbol`` plus the benchmark.
    """
    t_info_date = pd.Timestamp(t_info_date).tz_localize(None).normalize()
    hist = prices.loc[:t_info_date]
    if symbol not in hist.columns or benchmark not in hist.columns:
        raise KeyError(f"missing symbol columns for {symbol!r}/{benchmark!r}")

    s = hist[symbol].dropna()
    b = hist[benchmark].dropna()
    if len(s) < _MIN_HISTORY:
        # Not enough pre-event history to form features -> caller drops the row.
        return {}

    feats: dict[str, float] = {
        "ret_1d": _ret(s, _LOOKBACKS["1d"]),
        "ret_5d": _ret(s, _LOOKBACKS["5d"]),
        "ret_21d": _ret(s, _LOOKBACKS["21d"]),
        "vol_21d": _vol(s, _LOOKBACKS["21d"]),
        "bench_ret_1d": _ret(b, _LOOKBACKS["1d"]),
        "bench_ret_5d": _ret(b, _LOOKBACKS["5d"]),
        "bench_ret_21d": _ret(b, _LOOKBACKS["21d"]),
        "bench_vol_21d": _vol(b, _LOOKBACKS["21d"]),
    }
    # Relative momentum: symbol minus benchmark over 21d (regime/relative-strength).
    feats["mom_rel_21d"] = feats["ret_21d"] - feats["bench_ret_21d"]
    # Pre-event realized vol regime flag (confound guard: ERL must beat this signal).
    # Use `s` (the dropna'd series) consistently so NaN gaps don't skew the 63d window.
    longer_vol = s.pct_change().iloc[-63:].std(ddof=0) if len(s) >= 63 else feats["vol_21d"]
    feats["pre_vol_high"] = float(feats["vol_21d"] > longer_vol)
    return feats
