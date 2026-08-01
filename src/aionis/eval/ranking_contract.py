"""Ranking objective contract for rank-IC estimand.

Provides label → relevance transformation, group construction, and leakage guards
for LightGBM LGBMRanker with frozen lambdarank objective.

Leakage guards:
  - Per-month quantile fitting ONLY on train fold
  - Transform uses frozen bin edges (never refits)
  - NaN returns excluded from ranking
  - Test-fold out-of-range clamping with reason codes
"""
from __future__ import annotations

from enum import Enum
from typing import Literal

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Objective enum (FIXED — do NOT modify without owner approval)
# ---------------------------------------------------------------------------


class LightGBMRankingObjective(str, Enum):
    """Allowed LightGBM ranking objectives (version 4.3+)."""

    LAMBDARANK = "lambdarank"
    RANK_XENDCG = "rank_xendcg"


# Target version
LIGHTGBM_MIN_VERSION = (4, 3)


def validate_objective(objective: str) -> LightGBMRankingObjective:
    """Validate that objective is in the allowed enum.

    Args:
        objective: Objective string to validate

    Returns:
        The validated objective enum

    Raises:
        ValueError: If objective is not allowed
    """
    try:
        return LightGBMRankingObjective(objective)
    except ValueError as exc:
        allowed = [obj.value for obj in LightGBMRankingObjective]
        raise ValueError(
            f"Invalid ranking objective: {objective!r}. "
            f"Allowed objectives: {allowed}"
        ) from exc


# ---------------------------------------------------------------------------
# Reason codes for ranking transformation
# ---------------------------------------------------------------------------


class RankingReasonCode(str, Enum):
    """Reason codes for ranking transformation."""

    NORMAL = "normal"
    RETURN_MISSING = "return_missing"
    OUT_OF_RANGE_LOW = "oor_low"
    OUT_OF_RANGE_HIGH = "oor_high"
    UNSEEN_MONTH_POOLED = "unseen_pooled"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def construct_month_groups(dates: pd.DatetimeIndex) -> np.ndarray:
    """Construct month IDs for LightGBM ranking groups.

    Each calendar month (YYYY-MM) is assigned a unique integer group ID.
    Group boundaries are stable: group_id = year * 12 + (month - 1).

    Args:
        dates: Prediction/evaluation timestamps

    Returns:
        groups: Integer group IDs (one per sample)
    """
    if len(dates) == 0:
        raise ValueError("dates cannot be empty")

    years = dates.year.values
    months = dates.month.values

    # group_id = year * 12 + (month - 1)
    # Example: 2020-01 → 2020*12 + 0 = 24240
    #          2020-02 → 2020*12 + 1 = 24241
    #          2021-01 → 2021*12 + 0 = 24252
    groups = years * 12 + (months - 1)

    return groups


def get_group_sizes(groups: np.ndarray) -> np.ndarray:
    """Convert group IDs to group size array for LightGBM.

    Args:
        groups: Integer group IDs (one per sample)

    Returns:
        group_sizes: Array of unique group sizes, ordered by group ID
    """
    if len(groups) == 0:
        raise ValueError("groups cannot be empty")

    # Check if groups are sorted BEFORE unique (lightGBM expects sorted group IDs)
    if len(groups) > 1 and not np.all(groups[:-1] <= groups[1:]):
        raise ValueError("Group IDs must be sorted")

    unique_groups, counts = np.unique(groups, return_counts=True)
    return counts


def fit_monthly_bins(
    train_returns: pd.Series,
    train_groups: np.ndarray,
    n_bins: Literal[5, 10],
) -> dict[int, np.ndarray]:
    """Fit quantile bin edges FOR EACH MONTH separately, using ONLY train-fold data.

    Args:
        train_returns: Continuous forward returns for train fold, indexed by sample
        train_groups: Month ID for each sample (from construct_month_groups)
        n_bins: Number of relevance bins (5 = quintiles, 10 = deciles)

    Returns:
        fitted_bins: dict mapping month_id → bin edges (array of shape (n_bins + 1,))
                     Also stores train_month_stats (min, max) for each month
    """
    if len(train_returns) == 0:
        raise ValueError("train_returns cannot be empty")

    if len(train_returns) != len(train_groups):
        raise ValueError(
            f"length mismatch: train_returns ({len(train_returns)}) != "
            f"train_groups ({len(train_groups)})"
        )

    if n_bins not in (5, 10):
        raise ValueError(f"n_bins must be 5 or 10, got {n_bins}")

    # Convert to pandas Series for easier grouping
    returns_series = pd.Series(train_returns.values, index=train_groups)

    # Get unique months in train fold
    unique_months = np.unique(train_groups)

    # Compute pooled quantiles across all train months (fallback for months with no data)
    valid_returns = returns_series.dropna()
    if len(valid_returns) == 0:
        raise ValueError("train_returns contains no valid (non-NaN) returns")

    pooled_edges = np.quantile(
        valid_returns, q=np.linspace(0, 1, n_bins + 1)
    )

    # Fit per-month bins
    fitted_bins: dict[int, np.ndarray] = {}

    for month_id in unique_months:
        month_returns = returns_series[month_id]

        # Remove NaN returns for quantile computation
        month_valid = month_returns.dropna()

        if len(month_valid) == 0:
            # No valid data for this month, use pooled edges
            fitted_bins[month_id] = pooled_edges.copy()
        else:
            # Compute quantile edges for this month
            # np.quantile handles cases with fewer unique values gracefully
            edges = np.quantile(month_valid, q=np.linspace(0, 1, n_bins + 1))
            fitted_bins[month_id] = edges

    return fitted_bins


def transform_to_relevance(
    returns: pd.Series,
    groups: np.ndarray,
    fitted_bins: dict[int, np.ndarray],
    n_bins: Literal[5, 10],
) -> tuple[np.ndarray, list[str]]:
    """Transform continuous returns to integer relevance using FROZEN train-fold bin edges.

    NEVER refits bin edges. Handles NaN returns, out-of-range values, and unseen months.

    Args:
        returns: Continuous forward returns (train OR test fold)
        groups: Month IDs (from construct_month_groups)
        fitted_bins: FROZEN bin edges from fit_monthly_bins (NEVER refit here)
        n_bins: Number of bins (must match fitted_bins)

    Returns:
        relevance: Integer relevance labels (1..n_bins, or -1 for NaN returns)
        reason_codes: Reason code for each sample (RankingReasonCode)
    """
    if len(returns) != len(groups):
        raise ValueError(
            f"length mismatch: returns ({len(returns)}) != groups ({len(groups)})"
        )

    if len(fitted_bins) == 0:
        raise ValueError("fitted_bins cannot be empty")

    if n_bins not in (5, 10):
        raise ValueError(f"n_bins must be 5 or 10, got {n_bins}")

    # Initialize outputs
    relevance = np.full(len(returns), fill_value=-1, dtype=int)
    reason_codes: list[str] = [""] * len(returns)

    # Compute pooled edges for unseen months
    all_edges = list(fitted_bins.values())
    pooled_edges = np.mean(all_edges, axis=0)

    # Transform each sample
    for i in range(len(returns)):
        ret = returns.iloc[i] if isinstance(returns, pd.Series) else returns[i]
        month_id = groups[i]

        # Handle NaN returns
        if pd.isna(ret) or (isinstance(ret, float) and np.isnan(ret)):
            relevance[i] = -1
            reason_codes[i] = RankingReasonCode.RETURN_MISSING.value
            continue

        # Get bin edges for this month
        if month_id not in fitted_bins:
            # Month not seen in train fold, use pooled edges
            edges = pooled_edges
            reason_codes[i] = RankingReasonCode.UNSEEN_MONTH_POOLED.value
        else:
            edges = fitted_bins[month_id]

        # Check for out-of-range values
        train_min = edges[0]
        train_max = edges[-1]

        if ret < train_min:
            # Below train-fold minimum, clamp to lowest bin
            relevance[i] = 1
            base_reason = RankingReasonCode.OUT_OF_RANGE_LOW.value
            reason_codes[i] = (
                base_reason
                if month_id in fitted_bins
                else f"{base_reason},{RankingReasonCode.UNSEEN_MONTH_POOLED.value}"
            )
        elif ret > train_max:
            # Above train-fold maximum, clamp to highest bin
            relevance[i] = n_bins
            base_reason = RankingReasonCode.OUT_OF_RANGE_HIGH.value
            reason_codes[i] = (
                base_reason
                if month_id in fitted_bins
                else f"{base_reason},{RankingReasonCode.UNSEEN_MONTH_POOLED.value}"
            )
        else:
            # Normal case: digitize within range
            # np.digitize returns 1-based bin index, edges[1:] excludes left edge
            rel = np.digitize(ret, edges[1:]) + 1
            relevance[i] = int(np.clip(rel, 1, n_bins))
            reason_codes[i] = (
                RankingReasonCode.NORMAL.value
                if month_id in fitted_bins
                else RankingReasonCode.UNSEEN_MONTH_POOLED.value
            )

    return relevance, reason_codes


def filter_valid_ranking_samples(
    returns: pd.Series,
    relevance: np.ndarray,
    groups: np.ndarray,
) -> tuple[pd.Series, np.ndarray, np.ndarray]:
    """Remove samples with NaN returns from ranking dataset.

    LightGBM LGBMRanker requires valid relevance for ALL samples in a group.
    Samples with NaN returns must be EXCLUDED.

    Args:
        returns: Forward returns (may contain NaN)
        relevance: Relevance labels (from transform_to_relevance, may contain -1)
        groups: Group IDs

    Returns:
        returns_clean: Returns with NaN samples removed
        relevance_clean: Relevance with -1 samples removed
        groups_clean: Groups with filtered samples removed
    """
    if len(returns) != len(relevance) or len(returns) != len(groups):
        raise ValueError(
            f"returns, relevance, and groups must have same length: "
            f"{len(returns)} != {len(relevance)} != {len(groups)}"
        )

    # Valid samples: non-NaN returns AND relevance != -1
    valid_mask = ~pd.isna(returns) & (relevance != -1)

    if not np.any(valid_mask):
        raise ValueError("No valid samples after filtering NaN returns")

    returns_clean = returns[valid_mask]
    relevance_clean = relevance[valid_mask]
    groups_clean = groups[valid_mask]

    return returns_clean, relevance_clean, groups_clean


__all__ = [
    "LightGBMRankingObjective",
    "LIGHTGBM_MIN_VERSION",
    "validate_objective",
    "RankingReasonCode",
    "construct_month_groups",
    "get_group_sizes",
    "fit_monthly_bins",
    "transform_to_relevance",
    "filter_valid_ranking_samples",
]
