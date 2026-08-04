"""Track B S1-M① (price-only baseline) ignite pipeline.

Chronological walk-forward lambdarank pipeline for Track B S1-M① baseline.
This module produces the first rank-IC observations — synthetic testing only in this
round; real data runs are a separate owner-gated step bound to ledger row #41.

Anti-leakage invariants (asserted):
1. Chronological: max(train_date) < min(test_date) per fold (assert_chronological_split).
2. Train-only binner fit: lambdarank relevance bins fit ONLY on train fold, test fold
   uses frozen edges (transform_to_relevance with clamping). NEVER fit binner on full
   panel (this is the qlib RobustZScoreNorm fatal trap).
3. Fixed features: feature_cols from config #41 (pre-specified), no outcome-based
   selection; forward_return_h only as label.
4. Embargo: 21-session embargo between folds prevents label window overlap.

Reuse-first design:
- Fold generation: purged_walk_forward_splits (cv.py)
- Learner: LightGBMFrozen (learner.py) with objective=lambdarank override
- Ranking: fit_monthly_bins / transform_to_relevance / filter_valid_ranking_samples /
          construct_month_groups (ranking_contract.py)
- Rank-IC: rank_ic_by_date / rank_ic_monthly / rank_ic_summary (rank_ic.py)
- Inference: diebold_mariano (metrics.py), differential (two_arm.py)

DO NOT run on real data in this round — synthetic tests only.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from aionis.eval.learner import LightGBMFrozen
from aionis.eval.rank_ic import rank_ic_by_date, rank_ic_monthly, rank_ic_summary
from aionis.eval.ranking_contract import (
    construct_month_groups,
    filter_valid_ranking_samples,
    fit_monthly_bins,
    get_group_sizes,
    transform_to_relevance,
)

# Default frozen params from ledger #41 (objective=lambdarank, RD-15).
# LightGBMFrozen.fit_predict_rank handles the lambdarank group/query interface
# (additive; regression fit_predict path unchanged for B/C/D/E1).
_DEFAULT_FROZEN_PARAMS = {
    "objective": "lambdarank",  # config #41 (RD-15); fit_predict_rank forces lambdarank
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

# Default lambdarank bin count (ledger #41)
_DEFAULT_BIN_COUNT: Literal[5, 10] = 5

# Default embargo (ledger #41, 21 sessions converted to timedelta via session calendar)
_DEFAULT_EMBARGO_SESSIONS = 21


@dataclass(frozen=True)
class TrackBBaselineResult:
    """Result container for Track B S1-M① baseline run.

    Immutable by design (frozen=True) — prevents accidental mutation of the
    falsifiable result record.
    """

    # Per-fold details (for audit)
    n_walk_folds: int
    per_fold: list[dict]

    # Monthly IC series (headline, pre-reg §4)
    ic_series: pd.Series  # indexed by month-end date

    # Aggregated rank-IC with HAC inference (pre-reg §7 CI gate)
    mean_ic: float
    hac_se: float
    ci_95: tuple[float, float]  # (lower, upper) 95% CI
    t_hac: float
    p_hac: float

    # Diebold-Mariano vs equal-weight baseline (pre-reg §9, H-1 fix)
    # DM object is portfolio return loss differential, NOT rank-IC
    dm_stat: float
    dm_p: float

    # Fold count for sanity checks
    n_test_obs: int

    # Monthly portfolio returns (top-quantile vs equal-weight) for downstream
    # evaluation-layer mounts (tearsheet / FINSABER net-cost / FF5 residual).
    monthly_dates: list[str]
    monthly_model_returns: list[float]
    monthly_ew_returns: list[float]

    # OOS per-(date, ticker) scores for net-cost backtest (mount② FINSABER).
    # Columns: [date, ticker, score]. Only test-fold predictions included.
    oos_scores: pd.DataFrame


def fit_track_b_baseline(
    panel: pd.DataFrame,
    feature_cols: list[str],
    horizon: int = 21,
    min_train_months: int = 60,
    embargo_sessions: int = _DEFAULT_EMBARGO_SESSIONS,
    frozen_params: dict | None = None,
    bin_count: Literal[5, 10] = _DEFAULT_BIN_COUNT,
    date_col: str = "date",
    ticker_col: str = "ticker",
    y_col: str = "forward_return_h",
) -> TrackBBaselineResult:
    """Fit Track B S1-M① price-only baseline with chronological walk-forward.

    Args:
        panel: PIT-aligned panel with columns [date, ticker, *feature_cols, y_col].
               Must be sorted by date within ticker; y_col is forward_return_h.
        feature_cols: Pre-specified feature columns from config #41 (23 features).
                       NO outcome-based selection.
        horizon: Prediction horizon (trading days), default 21 (ledger #41).
        min_train_months: Minimum training months for walk-forward, default 60.
        embargo_sessions: Embargo sessions between folds, default 21.
        frozen_params: LightGBM frozen params (overrides defaults). If None,
                       uses _DEFAULT_FROZEN_PARAMS with objective=lambdarank.
        bin_count: Relevance bin count (5=quintiles, 10=deciles), default 5.
        date_col: Date column name, default "date".
        y_col: Label column name (forward return), default "forward_return_h".

    Returns:
        TrackBBaselineResult with IC series, HAC inference, and DM stats.

    Raises:
        ValueError: Input validation fails or no usable folds.
        AssertionError: Anti-leakage invariants violated (chronological, binner fit).

    Anti-leakage assertions:
    1. Each fold satisfies max(train_date) < min(test_date).
    2. Relevance binner fit ONLY on train fold, test uses frozen edges.
    3. Embargo enforced between folds.
    """
    # --- Input validation ---
    _validate_panel(panel, feature_cols, date_col, y_col)

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

    # Sort panel by date for monotonic prediction_times (purgedcv requirement)
    panel = panel.sort_values(date_col).reset_index(drop=True)

    # Sample month-end cross-sections (monthly rebalancing decision points): collapse the
    # daily panel to one row per (ticker, month-end) so each lambdarank query (calendar
    # month, via construct_month_groups) is a clean cross-section (~566 tickers) — within
    # LightGBM's 10000-rows-per-query limit. forward_return_h at month-end = next ~21
    # sessions (≈ next-month) return, matching the monthly rank-IC estimand (pre-reg §6).
    panel["_ym"] = panel[date_col].dt.to_period("M").astype(str)
    _month_end_idx = panel.groupby([ticker_col, "_ym"])[date_col].idxmax()
    panel = (
        panel.loc[_month_end_idx]
        .drop(columns=["_ym"])
        .sort_values(date_col)
        .reset_index(drop=True)
    )

    # --- Frozen params (config #41: objective=lambdarank, RD-15) ---
    # LightGBMFrozen.fit_predict_rank (learner.py) implements the lambdarank
    # group/query interface additively; the regression fit_predict path used by
    # B/C/D/E1 is unchanged.
    params = {**_DEFAULT_FROZEN_PARAMS, **(frozen_params or {})}

    # --- Walk-forward fold generation (chronological, expanding, min_train=60) ---
    # Manual expanding walk-forward with min_train_months constraint.
    # purged_walk_forward_splits only supports n_splits (equal-sized test folds),
    # not min_train constraint. We construct folds directly:
    # - For each test calendar month t (t >= month 60), train = all rows before
    #   calendar month t with embargo applied, test = rows in calendar month t.
    # - Embargo: train cutoff must be at least embargo_sessions before test start.
    embargo_td = pd.Timedelta(days=embargo_sessions)

    # Get unique calendar months (year-month periods)
    panel["_year_month"] = panel[date_col].dt.to_period("M")
    calendar_months = panel["_year_month"].unique()
    calendar_months = sorted(calendar_months)

    # Need at least min_train_months calendar months BEFORE first test fold
    if len(calendar_months) <= min_train_months:
        raise ValueError(
            f"Panel has only {len(calendar_months)} calendar months, "
            f"need > {min_train_months} for min_train_months"
        )

    # Build expanding walk-forward folds manually by calendar month
    splits = []
    fold = 1

    for month_idx in range(min_train_months, len(calendar_months)):
        test_calendar_month = calendar_months[month_idx]

        # All panel rows in this test calendar month
        test_mask = panel["_year_month"] == test_calendar_month
        test_idx_arr = np.flatnonzero(test_mask.to_numpy())

        if len(test_idx_arr) == 0:
            continue  # Skip empty test folds

        # Get the first date in the test month
        test_month_first_date = panel.loc[test_mask, date_col].min()
        train_cutoff = test_month_first_date - embargo_td

        # All panel rows on or before train cutoff (excluding test month)
        train_mask = (
            (panel["_year_month"] < test_calendar_month) |
            ((panel["_year_month"] == test_calendar_month) &
             (panel[date_col] <= train_cutoff))
        )
        # But we only want rows BEFORE the test calendar month for training
        train_mask = panel["_year_month"] < test_calendar_month
        train_idx = np.flatnonzero(train_mask.to_numpy())

        if len(train_idx) == 0:
            continue  # Skip empty train folds

        # Create CVSplit with chronological validation kind
        from aionis.eval.cv import CVSplit

        split = CVSplit(
            train_idx=train_idx,
            test_idx=test_idx_arr,
            fold=fold,
            validation_kind="chronological",
        )
        splits.append(split)
        fold += 1

    if not splits:
        raise ValueError("No valid walk-forward folds generated")

    # Clean up temporary column
    panel = panel.drop(columns=["_year_month"])

    # --- Walk-forward execution ---
    all_scores = pd.Series(np.nan, index=panel.index, dtype=float, name="score")
    per_fold_details = []

    for split in splits:
        # Anti-leakage invariant #1: chronological assertion
        # For manual expanding walk-forward, assert train < test
        train_dates = pd.to_datetime(panel[date_col].iloc[split.train_idx]).dt.normalize()
        test_dates = pd.to_datetime(panel[date_col].iloc[split.test_idx]).dt.normalize()

        assert train_dates.max() < test_dates.min(), (
            f"Fold {split.fold}: chronological invariant violated: "
            f"train_max={train_dates.max()} >= test_min={test_dates.min()}"
        )

        train_df = panel.iloc[split.train_idx].copy()
        test_df = panel.iloc[split.test_idx].copy()

        # Skip if no valid data in either partition
        if len(train_df) == 0 or len(test_df) == 0:
            continue

        # Train-test boundary for record
        train_max_date = train_df[date_col].max()
        test_min_date = test_df[date_col].min()
        n_train = len(train_df)
        n_test = len(test_df)

        # --- Ranking preparation (train-only binner fit) ---
        # Anti-leakage invariant #2: binner fit ONLY on train fold
        train_returns = train_df[y_col].reset_index(drop=True)
        train_dates = pd.to_datetime(train_df[date_col].reset_index(drop=True)).dt.normalize()
        train_groups = construct_month_groups(pd.DatetimeIndex(train_dates))

        # Fit binner on TRAIN fold only
        fitted_bins = fit_monthly_bins(
            train_returns=train_returns,
            train_groups=train_groups,
            n_bins=bin_count,
        )

        # Transform BOTH train and test with frozen bins (clamping on test)
        # Train: relevance for ranking
        train_relevance, _ = transform_to_relevance(
            returns=train_returns,
            groups=train_groups,
            fitted_bins=fitted_bins,
            n_bins=bin_count,
        )

        # Filter NaN returns (LightGBM ranker requires valid relevance)
        train_ret_clean, train_rel_clean, train_grp_clean = filter_valid_ranking_samples(
            returns=train_returns,
            relevance=train_relevance,
            groups=train_groups,
        )

        # Test: relevance transformation for evaluation (NOT for fitting)
        test_returns = test_df[y_col].reset_index(drop=True)
        test_dates = pd.to_datetime(test_df[date_col].reset_index(drop=True)).dt.normalize()
        test_groups = construct_month_groups(pd.DatetimeIndex(test_dates))

        # Transform test with FROZEN bins from train (clamping handles OOR)
        test_relevance, test_reason_codes = transform_to_relevance(
            returns=test_returns,
            groups=test_groups,
            fitted_bins=fitted_bins,
            n_bins=bin_count,
        )

        # --- LightGBM lambdarank (config #41, RD-15; via fit_predict_rank) ---
        # Align features with the cleaned (NaN-return-free) ranking samples, then
        # sort by group (ascending) so query groups are consecutive for LightGBM.
        valid_mask = train_returns.notna().to_numpy()
        train_feat_valid = train_df.iloc[np.flatnonzero(valid_mask)].reset_index(drop=True)
        sort_idx = np.argsort(train_grp_clean, kind="stable")
        train_feat_sorted = train_feat_valid.iloc[sort_idx].reset_index(drop=True)
        rel_sorted = np.asarray(train_rel_clean)[sort_idx]
        grp_sorted = np.asarray(train_grp_clean)[sort_idx]
        group_sizes = get_group_sizes(grp_sorted)
        mdl = LightGBMFrozen(params)  # objective=lambdarank (config #41)
        test_scores = mdl.fit_predict_rank(
            train=train_feat_sorted,
            test=test_df,
            feature_cols=feature_cols,
            relevance=rel_sorted,
            group_sizes=group_sizes,
        )

        # Store scores
        all_scores.iloc[split.test_idx] = test_scores.to_numpy()

        # Compute fold-level IC (for per-fold record)
        fold_panel = test_df.assign(score=test_scores.to_numpy())
        fold_ic = rank_ic_by_date(fold_panel, "score", y_col, date_col)

        per_fold_details.append({
            "fold": split.fold,
            "train_max_date": train_max_date,
            "test_min_date": test_min_date,
            "n_train": n_train,
            "n_test": n_test,
            "mean_ic": float(fold_ic.mean()) if len(fold_ic) > 0 else np.nan,
        })

    # --- Aggregate results ---
    # Build OOS panel with scores
    oos_panel = panel[[date_col, y_col]].assign(score=all_scores.to_numpy())
    oos_panel = oos_panel.dropna(subset=["score"])

    if len(oos_panel) == 0:
        raise ValueError("No valid OOS predictions (all scores NaN)")

    # Monthly rank-IC series (pre-reg §4 headline)
    ic_monthly = rank_ic_monthly(oos_panel, "score", y_col, date_col)

    # HAC inference on IC series (pre-reg §7 CI gate)
    ic_summary = rank_ic_summary(ic_monthly)
    mean_ic = ic_summary["mean_ic"]
    hac_se = ic_summary["se_hac"]
    ci_half = ic_summary["ci_half"]
    ci_95 = (mean_ic - ci_half, mean_ic + ci_half)
    t_hac = ic_summary["t_hac"]
    p_hac = ic_summary["p_hac"]

    # --- Diebold-Mariano vs equal-weight baseline (pre-reg §9, H-1 fix) ---
    # DM object is portfolio return loss, NOT rank-IC.
    # H-1 fix: Compare top-quantile portfolio returns vs equal-weight baseline.
    from aionis.eval.metrics import diebold_mariano

    # Compute monthly portfolio returns for both strategies
    # Top-quantile: top 20% tickers by score, equal-weighted
    # Equal-weight: all tickers, equal-weighted
    # Loss = -return (lower is better)

    # Filter out rows with NaN returns for portfolio construction
    oos_panel_clean = oos_panel.dropna(subset=[y_col]).copy()

    monthly_dates: list[str] = []
    monthly_model_returns: list[float] = []
    monthly_ew_returns: list[float] = []
    if len(oos_panel_clean) == 0:
        # No valid returns for DM test
        dm_stat = float("nan")
        dm_p = float("nan")
    else:
        # Group by month-end date for portfolio construction
        oos_panel_clean["month"] = pd.to_datetime(oos_panel_clean[date_col]).dt.to_period("M")

        for _month, group in oos_panel_clean.groupby("month", sort=True):
            if len(group) < 5:  # Need minimum tickers for meaningful portfolio
                continue

            # Top-quantile (top 20% by score)
            n_top = max(1, int(len(group) * 0.2))
            top_tickrs = group.nlargest(n_top, "score")
            model_ret = float(top_tickrs[y_col].mean())

            # Equal-weight (all tickers)
            ew_ret = float(group[y_col].mean())

            monthly_dates.append(str(_month))
            monthly_model_returns.append(model_ret)
            monthly_ew_returns.append(ew_ret)

        if len(monthly_model_returns) < 2:
            # Not enough data for DM test
            dm_stat = float("nan")
            dm_p = float("nan")
        else:
            # Loss = -return (lower return = higher loss)
            model_loss = -np.array(monthly_model_returns)
            ew_loss = -np.array(monthly_ew_returns)

            # Groups for clustering (by month index)
            groups = np.arange(len(monthly_model_returns))

            dm_result = diebold_mariano(
                loss_a=model_loss,
                loss_b=ew_loss,
                groups=groups,
                horizon=1,  # Monthly returns, horizon=1 month
            )

            dm_stat = dm_result["dm_stat"]
            dm_p = dm_result["p_value"]

    return TrackBBaselineResult(
        n_walk_folds=len(per_fold_details),
        per_fold=per_fold_details,
        ic_series=ic_monthly,
        mean_ic=mean_ic,
        hac_se=hac_se,
        ci_95=ci_95,
        t_hac=t_hac,
        p_hac=p_hac,
        dm_stat=dm_stat,
        dm_p=dm_p,
        n_test_obs=len(oos_panel),
        monthly_dates=monthly_dates,
        monthly_model_returns=monthly_model_returns,
        monthly_ew_returns=monthly_ew_returns,
        oos_scores=panel[[date_col, ticker_col]].assign(
            score=all_scores.to_numpy()
        ).dropna(subset=["score"])[[date_col, ticker_col, "score"]].reset_index(
            drop=True
        ),
    )


def _validate_panel(
    panel: pd.DataFrame,
    feature_cols: list[str],
    date_col: str,
    y_col: str,
) -> None:
    """Validate input panel for Track B baseline pipeline.

    Raises:
        ValueError: If panel format is invalid.
    """
    if not isinstance(panel, pd.DataFrame):
        raise ValueError(f"panel must be DataFrame, got {type(panel)}")

    if len(panel) == 0:
        raise ValueError("panel cannot be empty")

    required_cols = {date_col, y_col}
    missing_cols = required_cols - set(panel.columns)
    if missing_cols:
        raise ValueError(f"panel missing required columns: {missing_cols}")

    missing_features = set(feature_cols) - set(panel.columns)
    if missing_features:
        raise ValueError(f"panel missing feature columns: {missing_features}")

    # Check date column is datetime
    if not pd.api.types.is_datetime64_any_dtype(panel[date_col]):
        raise ValueError(f"{date_col} must be datetime type")


__all__ = [
    "TrackBBaselineResult",
    "fit_track_b_baseline",
    "_DEFAULT_FROZEN_PARAMS",
    "_DEFAULT_BIN_COUNT",
    "_DEFAULT_EMBARGO_SESSIONS",
]
