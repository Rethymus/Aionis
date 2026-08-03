"""Hermetic tests for the stock-specific FF5/DFF exposure + interaction
features (RES-02).

Covers: window semantics (last 252 obs <= t, min 126 obs), true-beta recovery
on a synthetic DGP, the PIT invariants (future-truncation invariance,
knowledge-date: features at t ignore every observation after t), bit-identical
determinism (H6), the hand-computed interactions, filed-date asset growth,
the session-grid PIT broadcast (no same-month future), the fail-closed RD-13
gate (market-wide raw factor columns structurally excluded), and config-file
consistency. All fixtures are synthetic; no network.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from aionis.features.ff5 import (
    ALL_FEATURE_COLS,
    BETA_MIN_OBS,
    BETA_WINDOW,
    EXPOSURE_COLS,
    INTERACTION_COLS,
    asset_growth_from_filings,
    broadcast_monthly_exposures,
    build_ff5_interactions,
    rd13_diagnostics,
    rd13_filter_columns,
    rolling_factor_exposures,
    verdict_rollup,
)

# --- fixture builders -----------------------------------------------------------


def _fixture(n_days: int = 300, n_tickers: int = 8, seed: int = 0) -> tuple:
    """Synthetic DGP: ret = rf + Σ β_k F_k + β_dff ΔDFF + ε (per ticker)."""
    rng = np.random.default_rng(seed)
    dates = pd.DatetimeIndex(pd.bdate_range("2023-01-02", periods=n_days)).normalize()
    factors = pd.DataFrame(
        {
            "mkt_rf": rng.normal(0, 0.01, n_days),
            "smb": rng.normal(0, 0.005, n_days),
            "hml": rng.normal(0, 0.005, n_days),
            "rmw": rng.normal(0, 0.004, n_days),
            "cma": rng.normal(0, 0.004, n_days),
            "rf": rng.normal(0.0002, 0.0001, n_days),
            "dff_change": rng.normal(0, 0.01, n_days),
        },
        index=dates,
    )
    betas = {
        "beta_mkt": 1.2,
        "beta_smb": 0.3,
        "beta_hml": -0.5,
        "beta_rmw": 0.2,
        "beta_cma": 0.1,
        "beta_dff": 0.4,
    }
    rets: dict[str, np.ndarray] = {}
    for i in range(n_tickers):
        eps = rng.normal(0, 0.003, n_days)
        rets[f"T{i:02d}"] = (
            factors["rf"].to_numpy()
            + betas["beta_mkt"] * factors["mkt_rf"].to_numpy()
            + betas["beta_smb"] * factors["smb"].to_numpy()
            + betas["beta_hml"] * factors["hml"].to_numpy()
            + betas["beta_rmw"] * factors["rmw"].to_numpy()
            + betas["beta_cma"] * factors["cma"].to_numpy()
            + betas["beta_dff"] * factors["dff_change"].to_numpy()
            + eps
        )
    returns = pd.DataFrame(rets, index=dates)
    return returns, factors, betas


def _month_ends_from(returns: pd.DataFrame) -> pd.DatetimeIndex:
    """Month-end dates with >= BETA_MIN_OBS obs (the post-warmup grid)."""
    return pd.DatetimeIndex(
        [
            returns.index[i]
            for i in range(len(returns))
            if i + 1 >= BETA_MIN_OBS
            and (i + 1 == len(returns) or returns.index[i].month != returns.index[i + 1].month)
        ]
    )


def _stock_features_for(index: pd.MultiIndex) -> pd.DataFrame:
    """Hand-built PIT stock features on the exposure grid (8 tickers)."""
    n = index.get_level_values(0).nunique()
    tickers = sorted(index.get_level_values(1).unique())
    rng = np.random.default_rng(42)
    frame = pd.DataFrame(index=index)
    frame["mktcap"] = rng.uniform(5e8, 5e10, len(index))
    frame["pb_ratio"] = rng.uniform(0.5, 6.0, len(index))
    frame["roa"] = rng.uniform(-0.10, 0.20, len(index))
    frame["fund_assets"] = rng.uniform(1e8, 5e10, len(index))
    frame["fund_long_term_debt"] = rng.uniform(0.0, 2e10, len(index))
    frame["asset_growth"] = rng.uniform(-0.3, 0.5, len(index))
    assert n >= 5 and len(tickers) == 8  # MIN_VALID_COUNT=5 in RD-13 needs >= 5 per month
    return frame


def _manual_betas(returns: pd.DataFrame, factors: pd.DataFrame, t, ticker: str) -> tuple:
    """Independent reference: the exact window + OLS the module must reproduce."""
    idx = returns.index
    j = idx.searchsorted(t, side="right")
    lo = max(0, j - BETA_WINDOW)
    y = returns[ticker].to_numpy()[lo:j] - factors["rf"].to_numpy()[lo:j]
    x5 = factors[["mkt_rf", "smb", "hml", "rmw", "cma"]].to_numpy()[lo:j]
    x_dff = factors["dff_change"].to_numpy()[lo:j]
    ok = np.isfinite(y) & np.isfinite(x5).all(axis=1) & np.isfinite(x_dff)
    yv, x5v, x_dff_v = y[ok], x5[ok], x_dff[ok]
    if len(yv) < BETA_MIN_OBS:
        return (float("nan"),) * 6
    b5, *_ = np.linalg.lstsq(np.column_stack([np.ones(len(yv)), x5v]), yv, rcond=None)
    bd, *_ = np.linalg.lstsq(np.column_stack([np.ones(len(yv)), x_dff_v]), yv, rcond=None)
    return (float(b5[1]), float(b5[2]), float(b5[3]), float(b5[4]), float(b5[5]), float(bd[1]))


# --- exposure estimation ----------------------------------------------------------


def test_rolling_exposures_recover_true_betas() -> None:
    returns, factors, betas = _fixture()
    t = returns.index[-1]
    exp = rolling_factor_exposures(returns, factors, pd.DatetimeIndex([t]))

    got = exp.loc[(t, "T00")]
    for col in EXPOSURE_COLS:
        assert got[col] == pytest.approx(betas[col], abs=0.10), col


def test_exposure_matches_independent_reference_at_window_boundary() -> None:
    returns, factors, _ = _fixture()
    t = returns.index[-1]
    exp = rolling_factor_exposures(returns, factors, pd.DatetimeIndex([t]))

    for ticker in returns.columns[:3]:
        manual = _manual_betas(returns, factors, t, ticker)
        for col, val in zip(EXPOSURE_COLS, manual, strict=True):
            assert exp.loc[(t, ticker), col] == pytest.approx(val, abs=1e-12), (ticker, col)


def test_future_truncation_invariance() -> None:
    """Deleting every observation after t must not change the features at t —
    the PIT no-lookahead invariant (TASK-RES-02 可测不变量 5)."""
    returns, factors, _ = _fixture()
    t = returns.index[200]  # mid-series month-end
    full = rolling_factor_exposures(returns, factors, pd.DatetimeIndex([t]))

    truncated = rolling_factor_exposures(
        returns.loc[:t], factors.loc[:t], pd.DatetimeIndex([t])
    )

    pd.testing.assert_frame_equal(full.loc[t], truncated.loc[t], check_exact=True)


def test_exposure_at_t_ignores_every_observation_after_t() -> None:
    """Knowledge-date assertion: poisoning day t+1 (returns AND factors) must
    leave the exposure at t bit-identical."""
    returns, factors, _ = _fixture()
    t = returns.index[200]
    day_after = returns.index[201]
    clean = rolling_factor_exposures(returns, factors, pd.DatetimeIndex([t]))

    poisoned_rets = returns.copy()
    poisoned_rets.loc[day_after] = poisoned_rets.loc[day_after] * 1000.0
    poisoned_factors = factors.copy()
    poisoned_factors.loc[day_after] = poisoned_factors.loc[day_after] * 1000.0
    got = rolling_factor_exposures(
        poisoned_rets, poisoned_factors, pd.DatetimeIndex([t])
    )

    pd.testing.assert_frame_equal(clean.loc[t], got.loc[t], check_exact=True)


def test_min_obs_boundary_126_computed_125_nan() -> None:
    returns, factors, _ = _fixture(n_days=126, n_tickers=3)
    t = returns.index[-1]
    exp = rolling_factor_exposures(returns, factors, pd.DatetimeIndex([t]))
    assert exp.loc[(t, "T00"), "beta_mkt"] == pytest.approx(1.2, abs=0.15)

    # 125 obs: the last available date is 125 rows in -> window < min_obs -> NaN
    t_short = returns.index[124]
    short = rolling_factor_exposures(
        returns.iloc[:125], factors.iloc[:125], pd.DatetimeIndex([t_short])
    )
    assert np.isnan(short.loc[(t_short, "T00"), "beta_mkt"])


def test_missing_observations_dropped_not_filled() -> None:
    returns, factors, _ = _fixture()
    t = returns.index[-1]
    mid = returns.index[150]
    rets_nan = returns.copy()
    rets_nan.loc[mid, "T00"] = np.nan
    factors_nan = factors.copy()
    factors_nan.loc[mid, "mkt_rf"] = np.nan

    exp = rolling_factor_exposures(rets_nan, factors_nan, pd.DatetimeIndex([t]))
    manual = _manual_betas(rets_nan, factors_nan, t, "T00")

    for col, val in zip(EXPOSURE_COLS, manual, strict=True):
        assert exp.loc[(t, "T00"), col] == pytest.approx(val, abs=1e-12)


def test_as_of_beyond_history_is_a_lookahead_guard_error() -> None:
    returns, factors, _ = _fixture(n_days=200, n_tickers=3)
    with pytest.raises(ValueError, match="beyond the daily history"):
        rolling_factor_exposures(
            returns, factors, pd.DatetimeIndex([returns.index[-1] + pd.Timedelta(days=1)])
        )


def test_missing_factor_columns_raise() -> None:
    returns, factors, _ = _fixture(n_days=200, n_tickers=3)
    bad = factors.drop(columns=["hml"])
    with pytest.raises(ValueError, match="missing columns"):
        rolling_factor_exposures(returns, bad, pd.DatetimeIndex([returns.index[-1]]))


def test_bit_identical_reruns_h6() -> None:
    returns, factors, _ = _fixture()
    t = returns.index[-1]
    a = rolling_factor_exposures(returns, factors, pd.DatetimeIndex([t]))
    b = rolling_factor_exposures(returns, factors, pd.DatetimeIndex([t]))
    pd.testing.assert_frame_equal(a, b, check_exact=True)


# --- interactions (hand-computed fixtures) ------------------------------------------


def test_interactions_are_hand_computed_products() -> None:
    index = pd.MultiIndex.from_product(
        [pd.DatetimeIndex(["2024-01-31"]), ["AAA", "BBB"]], names=["date", "ticker"]
    )
    exposures = pd.DataFrame(
        {
            "beta_mkt": [1.2, 0.8],
            "beta_smb": [0.3, -0.2],
            "beta_hml": [-0.5, 0.6],
            "beta_rmw": [0.2, 0.1],
            "beta_cma": [0.1, -0.3],
            "beta_dff": [0.4, -0.1],
        },
        index=index,
    )
    stock = pd.DataFrame(
        {
            "mktcap": [1e9, 4e9],
            "pb_ratio": [1.5, 0.8],
            "roa": [0.05, -0.03],
            "fund_assets": [1e8, 2e8],
            "fund_long_term_debt": [4e7, 5e7],
            "asset_growth": [0.10, -0.05],
        },
        index=index,
    )

    out = build_ff5_interactions(exposures, stock)

    assert list(out.columns) == list(INTERACTION_COLS)
    # AAA (row 0)
    assert out.loc[index[0], "beta_smb_x_size"] == pytest.approx(0.3 * np.log(1e9))
    assert out.loc[index[0], "beta_hml_x_value"] == pytest.approx(-0.5 * 1.5)
    assert out.loc[index[0], "beta_rmw_x_prof"] == pytest.approx(0.2 * 0.05)
    assert out.loc[index[0], "beta_cma_x_invest"] == pytest.approx(0.1 * 0.10)
    assert out.loc[index[0], "beta_dff_x_lev"] == pytest.approx(0.4 * (4e7 / 1e8))
    # BBB (row 1)
    assert out.loc[index[1], "beta_smb_x_size"] == pytest.approx(-0.2 * np.log(4e9))
    assert out.loc[index[1], "beta_dff_x_lev"] == pytest.approx(-0.1 * (5e7 / 2e8))


def test_interactions_propagate_nan_and_guard_domains() -> None:
    index = pd.MultiIndex.from_product(
        [pd.DatetimeIndex(["2024-01-31"]), ["AAA", "BBB", "CCC", "DDD"]],
        names=["date", "ticker"],
    )
    exposures = pd.DataFrame(
        {col: [0.5, 0.5, 0.5, np.nan] for col in EXPOSURE_COLS}, index=index
    )
    stock = pd.DataFrame(
        {
            "mktcap": [np.nan, -100.0, 1e9, 1e9],  # NaN / non-positive -> ln NaN
            "pb_ratio": [1.0, 1.0, np.nan, 1.0],  # missing pb -> NaN
            "roa": [0.1, 0.1, 0.1, 0.1],
            "fund_assets": [1e8, 0.0, 1e8, np.nan],  # 0 / NaN -> leverage NaN
            "fund_long_term_debt": [1e7, 1e7, 1e7, 1e7],
            "asset_growth": [0.1, 0.1, 0.1, 0.1],
        },
        index=index,
    )

    out = build_ff5_interactions(exposures, stock)

    assert np.isnan(out.loc[index[0], "beta_smb_x_size"])  # mktcap NaN
    assert np.isnan(out.loc[index[1], "beta_smb_x_size"])  # mktcap <= 0
    assert np.isnan(out.loc[index[2], "beta_hml_x_value"])  # pb missing
    assert np.isnan(out.loc[index[1], "beta_dff_x_lev"])  # assets == 0
    assert np.isnan(out.loc[index[3], "beta_dff_x_lev"])  # assets missing
    assert np.isnan(out.loc[index[3], "beta_smb_x_size"])  # NaN beta x ln -> NaN
    # valid cell keeps the exact product
    assert out.loc[index[0], "beta_dff_x_lev"] == pytest.approx(0.5 * (1e7 / 1e8))


# --- filed-date asset growth ---------------------------------------------------------


def _long_assets() -> pd.DataFrame:
    rows = [
        {"ticker": "AAA", "metric": "assets", "filed": "2023-01-15", "value": 100.0},
        {"ticker": "AAA", "metric": "assets", "filed": "2023-04-10", "value": 110.0},
        {"ticker": "AAA", "metric": "assets", "filed": "2023-07-20", "value": 121.0},
        {"ticker": "AAA", "metric": "assets", "filed": "2023-07-20", "value": 130.0},  # dup day
        {"ticker": "BBB", "metric": "assets", "filed": "2023-02-01", "value": 50.0},
        {"ticker": "BBB", "metric": "assets", "filed": "2023-06-01", "value": 60.0},
        {"ticker": "CCC", "metric": "assets", "filed": "2023-03-01", "value": 25.0},  # single
    ]
    return pd.DataFrame(rows)


def test_asset_growth_uses_two_most_recent_filings_pit() -> None:
    dates = pd.DatetimeIndex(
        ["2023-01-31", "2023-04-30", "2023-08-31", "2023-12-31"]
    ).normalize()
    long = _long_assets()

    growth = asset_growth_from_filings(long, dates, ["AAA", "BBB", "CCC"])

    assert np.isnan(growth.loc["2023-01-31", "AAA"])  # 1 filing -> NaN
    assert growth.loc["2023-04-30", "AAA"] == pytest.approx(110.0 / 100.0 - 1.0)
    # 2023-07-20 duplicate keeps the LAST value (130.0), previous = 110.0
    assert growth.loc["2023-08-31", "AAA"] == pytest.approx(130.0 / 110.0 - 1.0)
    assert np.isnan(growth.loc["2023-01-31", "BBB"])
    assert growth.loc["2023-12-31", "BBB"] == pytest.approx(60.0 / 50.0 - 1.0)
    assert np.isnan(growth.loc["2023-12-31", "CCC"])  # single filing -> NaN


def test_asset_growth_non_positive_previous_is_nan() -> None:
    dates = pd.DatetimeIndex(["2023-06-30"]).normalize()
    long = pd.DataFrame(
        [
            {"ticker": "AAA", "metric": "assets", "filed": "2023-01-15", "value": 0.0},
            {"ticker": "AAA", "metric": "assets", "filed": "2023-04-10", "value": 10.0},
        ]
    )
    growth = asset_growth_from_filings(long, dates, ["AAA"])
    assert np.isnan(growth.loc["2023-06-30", "AAA"])


def test_asset_growth_empty_long_frame_returns_all_nan() -> None:
    dates = pd.DatetimeIndex(["2023-06-30"]).normalize()
    growth = asset_growth_from_filings(pd.DataFrame(), dates, ["AAA"])
    assert growth.shape == (1, 1)
    assert np.isnan(growth.iloc[0, 0])


# --- PIT session-grid broadcast ----------------------------------------------------------


def test_broadcast_carries_values_to_strictly_later_sessions() -> None:
    sessions = pd.DatetimeIndex(pd.bdate_range("2023-01-02", "2023-03-31")).normalize()
    t1, t2 = pd.Timestamp("2023-01-31"), pd.Timestamp("2023-02-28")
    monthly = pd.DataFrame(
        {"v": [1.0, 2.0]},
        index=pd.MultiIndex.from_tuples(
            [(t1, "AAA"), (t2, "AAA")], names=["date", "ticker"]
        ),
    )

    out = broadcast_monthly_exposures(monthly, sessions)

    assert list(out.index.names) == ["date", "ticker"]
    s = out["v"]
    # before the first month-end: NaN (nothing knowable)
    assert s.loc[sessions[sessions <= t1]].isna().all()
    # sessions in (t1, t2]: the value computed at t1
    between = sessions[(sessions > t1) & (sessions <= t2)]
    assert (s.loc[between] == 1.0).all()
    # after t2: the value computed at t2
    after = sessions[sessions > t2]
    assert (s.loc[after] == 2.0).all()


def test_broadcast_no_same_month_future() -> None:
    """A session inside month t must never see the value computed at month-end
    t — that value uses month t's own data and is only knowable in t+1."""
    sessions = pd.DatetimeIndex(pd.bdate_range("2023-01-02", "2023-03-31")).normalize()
    t1, t2 = pd.Timestamp("2023-01-31"), pd.Timestamp("2023-02-28")
    monthly = pd.DataFrame(
        {"v": [1.0, 2.0]},
        index=pd.MultiIndex.from_tuples(
            [(t1, "AAA"), (t2, "AAA")], names=["date", "ticker"]
        ),
    )
    out = broadcast_monthly_exposures(monthly, sessions)["v"]

    # February sessions BEFORE Feb 28 carry January's value (1.0), not 2.0.
    feb_before = sessions[(sessions > t1) & (sessions < t2)]
    assert (out.loc[feb_before] == 1.0).all()


def test_broadcast_handles_multiple_tickers_and_nan_values() -> None:
    sessions = pd.DatetimeIndex(pd.bdate_range("2023-01-02", "2023-02-28")).normalize()
    t1, t2 = pd.Timestamp("2023-01-31"), pd.Timestamp("2023-02-28")
    monthly = pd.DataFrame(
        {"v": [1.0, np.nan, 3.0, 4.0]},
        index=pd.MultiIndex.from_tuples(
            [(t1, "AAA"), (t1, "BBB"), (t2, "AAA"), (t2, "BBB")],
            names=["date", "ticker"],
        ),
    )
    out = broadcast_monthly_exposures(monthly, sessions)
    wide = out["v"].unstack()
    after = sessions[sessions > t2]
    assert (wide.loc[after, "AAA"] == 3.0).all()
    assert wide.loc[after, "BBB"].isna().all()  # NaN carried (missing policy)


# --- RD-13 cross-sectional variation gate -------------------------------------------------


def test_rd13_gate_excludes_market_wide_and_all_missing_columns() -> None:
    dates = pd.DatetimeIndex(["2024-01-31", "2024-02-29"])
    tickers = [f"T{i:02d}" for i in range(8)]
    index = pd.MultiIndex.from_product([dates, tickers], names=["date", "ticker"])
    rng = np.random.default_rng(1)
    panel = pd.DataFrame(index=index)
    panel["varying"] = rng.normal(0, 1.0, len(index))
    # market-wide raw factor analog: identical across tickers within a month
    panel["mkt_rf_raw"] = np.repeat([0.5, -0.3], len(tickers))
    # near-constant: real spread but std below the 1e-6 threshold
    panel["near_const"] = np.tile(np.arange(len(tickers)) * 1e-9, 2)
    panel["all_missing"] = np.nan

    diag = rd13_diagnostics(panel)
    passing, failing = rd13_filter_columns(
        diag, ["varying", "mkt_rf_raw", "near_const", "all_missing"]
    )

    assert passing == ["varying"]
    assert "mkt_rf_raw" in failing
    assert "near_const" in failing
    assert "all_missing" in failing
    assert any("CONSTANT" in reason for reason in failing["mkt_rf_raw"])
    assert any("NEAR_CONSTANT" in reason for reason in failing["near_const"])
    assert any("ALL_MISSING" in reason for reason in failing["all_missing"])
    rollup = verdict_rollup(diag, ["varying", "mkt_rf_raw"])
    assert rollup.set_index("feature").loc["varying", "n_variation"] == 2


def test_rd13_gate_few_valid_months_fail_closed() -> None:
    dates = pd.DatetimeIndex(["2024-01-31"])
    index = pd.MultiIndex.from_product([dates, ["T00", "T01"]], names=["date", "ticker"])
    panel = pd.DataFrame({"v": [0.1, 0.2]}, index=index)  # only 2 valid < MIN_VALID_COUNT=5
    diag = rd13_diagnostics(panel)
    passing, failing = rd13_filter_columns(diag, ["v"])
    assert passing == []
    assert any("FEW_VALID" in reason for reason in failing["v"])


# --- end-to-end: the full feature family clears RD-13 on a synthetic panel -------


def test_all_ff5_columns_vary_cross_sectionally_and_pass_rd13() -> None:
    """The RD-13 非-常量证明: on a synthetic cross-section every one of the 11
    new columns is VARIATION in every month (no CONSTANT/NEAR_CONSTANT/
    ALL_MISSING/FEW_VALID), so the full family is config-eligible."""
    returns, factors, _ = _fixture()
    month_ends = _month_ends_from(returns)
    assert len(month_ends) >= 5

    exposures = rolling_factor_exposures(returns, factors, month_ends)
    stock = _stock_features_for(exposures.index)
    interactions = build_ff5_interactions(exposures, stock)
    monthly = exposures.join(interactions)
    assert list(monthly.columns) == list(ALL_FEATURE_COLS)

    # Session grid = the post-warmup panel grid (the real runner's frozen panel
    # starts AFTER at least one exposure month-end, so every session has a
    # strictly-prior value; pre-warmup months are ALL_MISSING and fail closed —
    # covered by test_early_warmup_months_all_missing_fail_closed).
    sessions = returns.index[returns.index >= month_ends[1]]
    broadcast = broadcast_monthly_exposures(monthly, sessions)
    diag = rd13_diagnostics(broadcast)
    passing, failing = rd13_filter_columns(diag, list(ALL_FEATURE_COLS))

    assert failing == {}, failing
    assert passing == list(ALL_FEATURE_COLS)
    # every (month, column) verdict is VARIATION
    assert set(diag["verdict"].unique()) == {"VARIATION"}


def test_early_warmup_months_all_missing_fail_closed() -> None:
    """A month-end with < BETA_MIN_OBS history is ALL_MISSING -> the column is
    excluded from config (fail closed) until the warmup completes."""
    returns, factors, _ = _fixture(n_days=160, n_tickers=8)
    early = pd.DatetimeIndex([returns.index[99]])  # 100 obs < 126
    late = pd.DatetimeIndex([returns.index[-1]])
    exp_early = rolling_factor_exposures(returns, factors, early)
    exp_late = rolling_factor_exposures(returns, factors, late)
    assert exp_early["beta_mkt"].isna().all()  # warmup month fully NaN
    panel = pd.concat([exp_early, exp_late])  # ONE column across both months

    diag = rd13_diagnostics(panel)
    passing, failing = rd13_filter_columns(diag, ["beta_mkt"])
    assert passing == []
    assert "beta_mkt" in failing
    assert any("ALL_MISSING" in reason for reason in failing["beta_mkt"])


# --- config-file consistency ---------------------------------------------------------


def test_config_yaml_lists_exactly_the_feature_columns() -> None:
    text = Path("config/baseline_ff5_001.yaml").read_text()
    frozen = [
        "mktcap", "pb_ratio", "roa",
        "fund_assets", "fund_revenue", "fund_net_income",
        "fund_equity", "fund_shares_out", "fund_long_term_debt",
    ]
    for name in frozen + list(ALL_FEATURE_COLS):
        assert f"- {name}" in text, name
    # NO market-wide raw factor columns may ever appear in the feature list
    raw = {"MKTRF", "SMB", "HML", "RMW", "CMA", "DFF"}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            assert stripped[2:] not in raw, stripped
    assert "rd13_gate" in text
    assert "beta_min_obs: 126" in text
    assert "beta_window_days: 252" in text
