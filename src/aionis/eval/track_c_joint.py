"""Track C joint US-CN chronological walk-forward rank-IC estimator (CONFIRMATORY machinery).

Implements the §5 joint dual-region fold: ONE LightGBM lambdarank model fit on US+CN
month-end cross-sections together, with per-region trading-calendar month-end sampling,
per-region chronological assertion, and region-month ranking groups (currency-clean).

This module is the confirmatory *machinery*. It writes NO ledger and makes NO confirmatory
verdict — the exploratory runner proves correctness; the confirmatory run is owner-gated
(new ledger row + GO). See `reports/design/2026-08-04-track-c-joint-fold-spec.md`.

Anti-leakage invariants (asserted):
  I1  per-region chronological: for each fold, train.max(date) < test.min(date) WITHIN each
      region (us and cn independently) — #46 ``validation.chronological_assert``.
  I2  binner fit ONLY on train fold; test uses frozen edges (ranking_contract, RD-15).
  I3  regime_state as-of month-end via ffill (PIT; regime uses only <= month-end data;
      TACO normalization already enforced in regime_composite).
  I4  forward_return_h is label-only; shared features are the 10 price columns.
  I5  ranking group = region-month (no cross-currency label contamination).
  I6  H6 determinism: seed=0, n_jobs=1 (#46 learner params).

Reuse-first (0 modification to frozen surfaces):
  - fold logic mirrors ``track_b_baseline.fit_track_b_baseline`` (calendar-month walk-forward;
    month-end boundary == per-region 21-session embargo for month-end sampling).
  - ranking_contract / rank_ic / learner / metrics — reused as-is.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd

from aionis.eval.learner import LightGBMFrozen
from aionis.eval.rank_ic import rank_ic_monthly, rank_ic_summary
from aionis.eval.ranking_contract import (
    filter_valid_ranking_samples,
    fit_monthly_bins,
    get_group_sizes,
    transform_to_relevance,
)

# ---------------------------------------------------------------------------
# Frozen params (ledger #46 ``learner``) — mirrored, not imported, to keep
# track_b_baseline.py (Track B frozen #41 path) at 0 diff.
# ---------------------------------------------------------------------------

_DEFAULT_FROZEN_PARAMS: dict = {
    "objective": "lambdarank",
    "n_estimators": 500,
    "learning_rate": 0.05,
    "num_leaves": 31,
    "min_child_samples": 20,
    "reg_lambda": 1.0,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 1,
    "n_jobs": 1,
    "random_state": 0,
    "bagging_seed": 0,
    "feature_fraction_seed": 0,
    "drop_seed": 0,
    "verbose": -1,
}

_DEFAULT_BIN_COUNT: Literal[5, 10] = 5
_DEFAULT_EMBARGO_SESSIONS = 21  # ledger #46; realized as calendar-month boundary (spec §2)
_DEFAULT_MIN_TRAIN_MONTHS = 60

# Region code map for region-month group construction (D1). Code < N_REGIONS so the
# composite group id (year*12+month-1)*N_REGIONS + code stays unique + monotonic in time.
_REGION_CODE: dict[str, int] = {"us": 0, "cn": 1}
_N_REGIONS = len(_REGION_CODE)


def construct_region_month_groups(
    dates: pd.DatetimeIndex,
    regions: pd.Series,
) -> np.ndarray:
    """Construct per-region-per-month integer group IDs for LightGBM ranking (D1).

    Each (region, calendar-month) is a unique query group, so US stocks rank only among
    US and CN only among CN — no cross-currency forward-return comparison in the label.

    Group id = ``(year*12 + (month-1)) * N_REGIONS + region_code``. This is unique per
    region-month and strictly increasing in time within a region (us months are even,
    cn months are odd, interleaved chronologically — LightGBM only needs contiguous
    sorted groups, which the caller enforces via stable argsort).

    Args:
        dates: Prediction/evaluation timestamps (month-end samples).
        regions: Region label per sample ("us" or "cn"), aligned to dates.

    Returns:
        Integer group IDs (one per sample).

    Raises:
        ValueError: If an unknown region label is encountered.
    """
    if len(dates) == 0:
        raise ValueError("dates cannot be empty")
    if len(dates) != len(regions):
        raise ValueError("dates / regions length mismatch")
    years = pd.DatetimeIndex(dates).year.values
    months = pd.DatetimeIndex(dates).month.values
    try:
        codes = np.array([_REGION_CODE[r] for r in regions], dtype=np.int64)
    except KeyError as exc:
        raise ValueError(f"unknown region label {exc!r}; allowed: {list(_REGION_CODE)}") from exc
    return (years * 12 + (months - 1)) * _N_REGIONS + codes


@dataclass(frozen=True)
class TrackCJointResult:
    """Immutable result container for the Track C joint dual-region fold."""

    n_walk_folds: int
    per_fold: list[dict]

    # Per-region monthly IC series + currency-clean combined series (D2).
    us_ic_series: pd.Series
    cn_ic_series: pd.Series
    combined_ic_series: pd.Series  # equal-weight mean of us/cn per month

    # HAC inference on the combined IC series.
    mean_ic: float
    hac_se: float
    ci_95: tuple[float, float]
    t_hac: float
    p_hac: float

    # Conditional-IC: combined_ic_t ~ regime_t (HAC). beta = interaction strength.
    cond_alpha: float
    cond_alpha_p: float
    cond_beta: float
    cond_beta_p: float
    cond_r_squared: float
    cond_n_months: int

    # OOS per-(date, ticker, region) scores (test-fold predictions only).
    oos_scores: pd.DataFrame


def build_joint_panel(
    us_panel_path: str | Path,
    cn_panel_path: str | Path,
    feature_cols: list[str],
    *,
    us_feature_cols: list[str] | None = None,
    cn_feature_cols: list[str] | None = None,
    window_start: str = "2016-01-01",
    date_col: str = "date",
    ticker_col: str = "ticker",
    y_col: str = "forward_return_h",
    region_col: str = "region",
) -> pd.DataFrame:
    """Build the joint US+CN month-end panel with a region tag.

    Two modes:
      * **Shared** (default, backward-compatible): ``feature_cols`` lists columns present
        in BOTH panels (the exploratory 10 price cols). US-only and CN-only columns drop.
      * **Asymmetric** (confirmatory #48, 41-feature path): pass ``us_feature_cols`` AND
        ``cn_feature_cols``; US rows keep US-specific columns (e.g. 13 EDGAR fundamentals +
        10 price = 23), CN rows keep CN-specific columns (e.g. 10 price mirror + 2 A-share
        extras = 12). The concatenated panel has the UNION of columns; US rows are NaN in
        CN-only columns and vice versa (LightGBM's default missing-value handling covers
        this — no manual fillna).

    In both modes, loads US (daily or month-end) + CN (month-end), restricts to
    ``window_start`` (#46: 2016-01-01), tags region, concatenates. Month-end sampling of
    daily US rows is performed downstream by ``fit_track_c_joint`` (idempotent on CN).

    Args:
        us_panel_path: Path to ``track_b_panel.parquet`` (US, daily or month-end).
        cn_panel_path: Path to ``cn_price_panel.parquet`` (CN, month-end).
        feature_cols: Shared feature columns (shared mode). Kept as a required positional
               for backward-compat; ignored in asymmetric mode.
        us_feature_cols: US-specific feature columns (asymmetric mode). When both this and
               ``cn_feature_cols`` are non-None, asymmetric mode activates.
        cn_feature_cols: CN-specific feature columns (asymmetric mode).
        window_start: Inclusive lower date bound (#46 ``universe.*.window_start``).
        date_col, ticker_col, y_col, region_col: Column names.

    Returns:
        Long panel [date, ticker, region, *<features>, y_col]. In asymmetric mode the
        feature columns are the union of ``us_feature_cols`` and ``cn_feature_cols``
        (region-missing columns auto-filled NaN by pandas concat alignment).

    Raises:
        ValueError: If required columns are missing in either panel.
    """
    asymmetric = us_feature_cols is not None and cn_feature_cols is not None
    if asymmetric:
        keep_us = [date_col, ticker_col, *us_feature_cols, y_col]
        keep_cn = [date_col, ticker_col, *cn_feature_cols, y_col]
    else:
        keep_us = [date_col, ticker_col, *feature_cols, y_col]
        keep_cn = [date_col, ticker_col, *feature_cols, y_col]

    us = pd.read_parquet(us_panel_path)
    cn = pd.read_parquet(cn_panel_path)

    missing_us = [c for c in keep_us if c not in us.columns]
    missing_cn = [c for c in keep_cn if c not in cn.columns]
    if missing_us:
        raise ValueError(f"US panel missing columns: {missing_us}")
    if missing_cn:
        raise ValueError(f"CN panel missing columns: {missing_cn}")

    us = us[keep_us].copy()
    us[region_col] = "us"
    cn = cn[keep_cn].copy()
    cn[region_col] = "cn"

    ws = pd.Timestamp(window_start)
    us = us[pd.to_datetime(us[date_col]) >= ws]
    cn = cn[pd.to_datetime(cn[date_col]) >= ws]

    joint = pd.concat([us, cn], ignore_index=True, sort=False)
    joint[date_col] = pd.to_datetime(joint[date_col])
    joint = joint.sort_values([date_col, region_col, ticker_col]).reset_index(drop=True)

    if joint.empty:
        raise ValueError("joint panel is empty after window_start restriction")
    return joint


def _month_end_sample(
    panel: pd.DataFrame,
    date_col: str,
    ticker_col: str,
    region_col: str,
) -> pd.DataFrame:
    """Keep the last available date per (region, ticker, calendar month).

    Mirrors ``track_b_baseline`` month-end sampling but keyed on (region, ticker, month)
    so each region's own trading calendar determines its month-end (US NYSE vs CN XSHG/XSHE).
    Idempotent on already-month-end CN rows.
    """
    panel = panel.copy()
    panel["_ym"] = panel[date_col].dt.to_period("M").astype(str)
    me_idx = panel.groupby([region_col, ticker_col, "_ym"])[date_col].idxmax()
    out = panel.loc[me_idx].drop(columns=["_ym"])
    return out.sort_values(date_col).reset_index(drop=True)


def _assert_per_region_chronological(
    panel: pd.DataFrame,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    fold: int,
    date_col: str,
    region_col: str,
) -> None:
    """I1: per-region chronological assertion (#46 validation.chronological_assert).

    For each region present in BOTH train and test, require
    ``max(train.date[region]) < min(test.date[region])``. This is strictly stronger than a
    single global assertion and directly enforces the frozen per-region contract.
    """
    for region in ("us", "cn"):
        tr_mask = panel[region_col].iloc[train_idx].to_numpy() == region
        te_mask = panel[region_col].iloc[test_idx].to_numpy() == region
        if not (tr_mask.any() and te_mask.any()):
            continue  # region absent on one side this fold — nothing to assert for it
        tr_dates = pd.to_datetime(panel[date_col].iloc[train_idx].to_numpy()[tr_mask])
        te_dates = pd.to_datetime(panel[date_col].iloc[test_idx].to_numpy()[te_mask])
        tr_max = tr_dates.max()
        te_min = te_dates.min()
        if not tr_max < te_min:
            raise AssertionError(
                f"fold {fold} region={region!r} chronological violation: "
                f"train.max={tr_max} >= test.min={te_min}"
            )


def fit_track_c_joint(
    panel: pd.DataFrame,
    feature_cols: list[str],
    regime_state: pd.Series,
    horizon: int = 21,
    min_train_months: int = _DEFAULT_MIN_TRAIN_MONTHS,
    embargo_sessions: int = _DEFAULT_EMBARGO_SESSIONS,
    frozen_params: dict | None = None,
    bin_count: Literal[5, 10] = _DEFAULT_BIN_COUNT,
    date_col: str = "date",
    ticker_col: str = "ticker",
    y_col: str = "forward_return_h",
    region_col: str = "region",
) -> TrackCJointResult:
    """Fit the Track C joint dual-region chronological walk-forward rank-IC estimator.

    Args:
        panel: Joint panel [date, ticker, region, *feature_cols, y_col] (US may be daily;
               CN month-end). Month-end sampling is applied internally per region.
        feature_cols: Shared feature columns (the 10 price cols). No outcome-based selection.
        regime_state: Daily PIT regime_state series (indexed by date); used as-of month-end.
        horizon: Forward-return horizon (sessions), default 21 (#46).
        min_train_months: Minimum training calendar months, default 60.
        embargo_sessions: Embargo sessions, default 21 — realized as the calendar-month
               boundary (spec §2; month-end spacing >= 21 sessions per region calendar).
        frozen_params: LightGBM params override (defaults = #46 learner).
        bin_count: Relevance bins (5=quintiles), default 5 (#46).
        date_col, ticker_col, y_col, region_col: Column names.

    Returns:
        TrackCJointResult with per-region + combined IC, HAC inference, and conditional-IC.

    Raises:
        ValueError: Input validation fails or no usable folds.
        AssertionError: Anti-leakage invariant violated (I1 per-region chronological).

    Anti-leakage: I1 per-region chronological; I2 train-only binner; I5 region-month groups.
    """
    # --- input validation ---
    required = {date_col, ticker_col, region_col, y_col, *feature_cols}
    missing = required - set(panel.columns)
    if missing:
        raise ValueError(f"panel missing columns: {sorted(missing)}")
    if not isinstance(panel, pd.DataFrame) or panel.empty:
        raise ValueError("panel must be a non-empty DataFrame")
    if not pd.api.types.is_datetime64_any_dtype(panel[date_col]):
        panel = panel.copy()
        panel[date_col] = pd.to_datetime(panel[date_col])
    if horizon < 1:
        raise ValueError(f"horizon must be >= 1, got {horizon}")
    if min_train_months < 1:
        raise ValueError(f"min_train_months must be >= 1, got {min_train_months}")
    if embargo_sessions < 0:
        raise ValueError(f"embargo_sessions must be >= 0, got {embargo_sessions}")
    if not feature_cols:
        raise ValueError("feature_cols cannot be empty")
    if bin_count not in (5, 10):
        raise ValueError(f"bin_count must be 5 or 10, got {bin_count}")
    regions_present = set(panel[region_col].unique())
    if not regions_present.issubset({"us", "cn"}):
        raise ValueError(f"region_col must be in {{us,cn}}, got {sorted(regions_present)}")
    if len(regions_present) < 2:
        raise ValueError(
            f"joint fold requires BOTH regions; got only {sorted(regions_present)}"
        )
    if regime_state.dropna().empty:
        raise ValueError("regime_state is empty after dropna")

    params = {**_DEFAULT_FROZEN_PARAMS, **(frozen_params or {})}

    # --- per-region month-end sampling (I1 precondition: each region on its calendar) ---
    panel = _month_end_sample(panel, date_col, ticker_col, region_col)

    # --- expanding walk-forward by calendar month (mirrors track_b_baseline §fold logic) ---
    # train = all rows with _year_month < test_calendar_month; test = rows in test month.
    # The calendar-month boundary IS the per-region 21-session embargo (spec §2), so no
    # separate Timedelta embargo is applied to the train mask (consistent with the frozen
    # Track B fitter). embargo_sessions is asserted >= 21 as a documentation guard.
    assert embargo_sessions >= 21, (
        "embargo_sessions < 21 violates the month-boundary embargo contract"
    )

    panel["_year_month"] = panel[date_col].dt.to_period("M")
    calendar_months = sorted(panel["_year_month"].unique())
    if len(calendar_months) <= min_train_months:
        raise ValueError(
            f"Panel has only {len(calendar_months)} calendar months, "
            f"need > {min_train_months}"
        )

    splits: list[tuple[np.ndarray, np.ndarray, int]] = []
    fold = 1
    for month_idx in range(min_train_months, len(calendar_months)):
        test_cm = calendar_months[month_idx]
        test_mask = (panel["_year_month"] == test_cm).to_numpy()
        test_idx = np.flatnonzero(test_mask)
        if len(test_idx) == 0:
            continue
        train_mask = (panel["_year_month"] < test_cm).to_numpy()
        train_idx = np.flatnonzero(train_mask)
        if len(train_idx) == 0:
            continue
        # I1: per-region chronological assertion
        _assert_per_region_chronological(panel, train_idx, test_idx, fold, date_col, region_col)
        splits.append((train_idx, test_idx, fold))
        fold += 1

    if not splits:
        raise ValueError("No valid walk-forward folds generated")
    panel = panel.drop(columns=["_year_month"])

    # --- walk-forward execution ---
    all_scores = pd.Series(np.nan, index=panel.index, dtype=float, name="score")
    per_fold_details: list[dict] = []

    for train_idx, test_idx, fld in splits:
        train_df = panel.iloc[train_idx].copy()
        test_df = panel.iloc[test_idx].copy()

        # I2: binner fit ONLY on train fold (region-month groups, D1)
        train_dates = pd.to_datetime(train_df[date_col].to_numpy()).normalize()
        train_regions = train_df[region_col].reset_index(drop=True)
        train_groups = construct_region_month_groups(
            pd.DatetimeIndex(train_dates), train_regions
        )
        train_returns = train_df[y_col].reset_index(drop=True)
        fitted_bins = fit_monthly_bins(
            train_returns=train_returns, train_groups=train_groups, n_bins=bin_count
        )
        train_relevance, _ = transform_to_relevance(
            returns=train_returns, groups=train_groups, fitted_bins=fitted_bins, n_bins=bin_count
        )
        train_ret_clean, train_rel_clean, train_grp_clean = filter_valid_ranking_samples(
            returns=train_returns, relevance=train_relevance, groups=train_groups
        )

        # Align features to cleaned (NaN-return-free) ranking samples, sort by group (stable).
        valid_mask = train_returns.notna().to_numpy()
        train_feat_valid = train_df.iloc[np.flatnonzero(valid_mask)].reset_index(drop=True)
        sort_idx = np.argsort(train_grp_clean, kind="stable")
        train_feat_sorted = train_feat_valid.iloc[sort_idx].reset_index(drop=True)
        rel_sorted = np.asarray(train_rel_clean)[sort_idx]
        grp_sorted = np.asarray(train_grp_clean)[sort_idx]
        group_sizes = get_group_sizes(grp_sorted)

        mdl = LightGBMFrozen(params)
        test_scores = mdl.fit_predict_rank(
            train=train_feat_sorted,
            test=test_df,
            feature_cols=feature_cols,
            relevance=rel_sorted,
            group_sizes=group_sizes,
        )
        all_scores.iloc[test_idx] = test_scores.to_numpy()

        per_fold_details.append(
            {
                "fold": fld,
                "test_month": str(test_df[date_col].dt.to_period("M").iloc[0]),
                "n_train": len(train_df),
                "n_test": len(test_df),
                "n_test_us": int((test_df[region_col] == "us").sum()),
                "n_test_cn": int((test_df[region_col] == "cn").sum()),
            }
        )

    # --- OOS scores + per-region monthly IC (D2) ---
    oos = panel[[date_col, ticker_col, region_col, y_col]].assign(score=all_scores.to_numpy())
    oos = oos.dropna(subset=["score"])
    if oos.empty:
        raise ValueError("No valid OOS predictions (all scores NaN)")

    us_oos = oos[oos[region_col] == "us"]
    cn_oos = oos[oos[region_col] == "cn"]
    us_ic = rank_ic_monthly(us_oos, "score", y_col, date_col)
    cn_ic = rank_ic_monthly(cn_oos, "score", y_col, date_col)
    us_ic.name = "us_ic"
    cn_ic.name = "cn_ic"

    # combined IC = equal-weight mean of per-region IC per month (currency-clean, D2)
    combined = pd.concat([us_ic.rename("us"), cn_ic.rename("cn")], axis=1)
    combined_ic = combined.mean(axis=1, skipna=True).dropna()
    combined_ic.name = "combined_ic"

    if combined_ic.empty:
        raise ValueError("combined IC series is empty")
    ic_summary = rank_ic_summary(combined_ic)
    mean_ic = ic_summary["mean_ic"]
    ci_half = ic_summary["ci_half"]
    ci_95 = (mean_ic - ci_half, mean_ic + ci_half)

    # --- conditional-IC: combined_ic_t ~ regime_t (HAC); beta = interaction (spec §1) ---
    regime_daily = pd.Series(regime_state, dtype=float)
    regime_daily.index = pd.to_datetime(regime_daily.index)
    regime_at_me = regime_daily.reindex(combined_ic.index, method="ffill")
    cond_df = pd.DataFrame({"ic": combined_ic, "regime": regime_at_me}).dropna()
    cond_n = len(cond_df)

    if cond_n >= 3 and cond_df["regime"].nunique() > 1:
        import statsmodels.api as sm
        from statsmodels.regression.linear_model import OLS

        maxlag = max(1, int(4 * (cond_n / 100.0) ** (2 / 9)))
        X = sm.add_constant(cond_df["regime"])
        res = OLS(cond_df["ic"], X).fit(cov_type="HAC", cov_kwds={"maxlags": maxlag})
        cond_alpha = float(res.params.iloc[0])
        cond_alpha_p = float(res.pvalues.iloc[0])
        cond_beta = float(res.params.iloc[1])
        cond_beta_p = float(res.pvalues.iloc[1])
        cond_r2 = float(res.rsquared)
    else:
        cond_alpha = cond_alpha_p = cond_beta = cond_beta_p = cond_r2 = float("nan")

    return TrackCJointResult(
        n_walk_folds=len(per_fold_details),
        per_fold=per_fold_details,
        us_ic_series=us_ic,
        cn_ic_series=cn_ic,
        combined_ic_series=combined_ic,
        mean_ic=mean_ic,
        hac_se=ic_summary["se_hac"],
        ci_95=ci_95,
        t_hac=ic_summary["t_hac"],
        p_hac=ic_summary["p_hac"],
        cond_alpha=cond_alpha,
        cond_alpha_p=cond_alpha_p,
        cond_beta=cond_beta,
        cond_beta_p=cond_beta_p,
        cond_r_squared=cond_r2,
        cond_n_months=cond_n,
        oos_scores=oos[[date_col, ticker_col, region_col, "score"]].reset_index(drop=True),
    )


__all__ = [
    "TrackCJointResult",
    "fit_track_c_joint",
    "build_joint_panel",
    "construct_region_month_groups",
]
