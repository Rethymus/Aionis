"""Cross-sectional feature variation diagnostics — monthly variation guard ⑪.

A feature panel (long-form: date × ticker × feature → value) can carry silent defects:
month-constant columns (no cross-sectional spread), near-constant features, all-missing
coverage, or few valid values. None of these is a look-ahead leak, but each corrupts the
cross-sectional rank signal. This module flags them per (date, feature) so a run can
audit its features before trusting the rank-IC.

Pure detection: it never constructs interactions, mutates inputs, or drops features.
It only *reports* — the caller decides whether a flagged feature is acceptable,
masked, or used only for macro-only interaction inputs.

Permissive licenses only (pandas / numpy, BSD).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Thresholds for cross-sectional variation classification (explicit named constants)
# A feature with std <= this threshold is classified as NEAR_CONSTANT
NEAR_CONSTANT_STD_THRESHOLD = 1e-6

# Minimum number of non-missing (valid) values required to treat a (date, feature) as
# having meaningful coverage. Below this, we classify as FEW_VALID.
MIN_VALID_COUNT = 5

# Verdict categories for cross-sectional variation signals
VERDICT_CONSTANT = "CONSTANT"          # Month-constant: unique count <= 1 or std == 0
VERDICT_NEAR_CONSTANT = "NEAR_CONSTANT"  # std below explicit threshold
VERDICT_ALL_MISSING = "ALL_MISSING"    # Coverage 0 (no valid values)
VERDICT_FEW_VALID = "FEW_VALID"        # Non-missing count below minimum
VERDICT_VARIATION = "VARIATION"        # Real cross-sectional spread

_ALL_VERDICTS = (
    VERDICT_CONSTANT,
    VERDICT_NEAR_CONSTANT,
    VERDICT_ALL_MISSING,
    VERDICT_FEW_VALID,
    VERDICT_VARIATION,
)


def feature_variation_diagnostics(
    features: pd.DataFrame,
    *,
    near_constant_std_threshold: float = NEAR_CONSTANT_STD_THRESHOLD,
    min_valid_count: int = MIN_VALID_COUNT,
) -> pd.DataFrame:
    """Compute cross-sectional variation diagnostics for a feature panel.

    Takes a long-form panel (date × ticker × feature → value), groups by date, and
    for each (date, feature) computes:
        * unique_value_count — number of distinct non-missing values
        * std — sample standard deviation (ddof=1)
        * coverage — proportion of non-missing values (0.0 to 1.0)

    Classifies each (date, feature) into explicit verdict categories:

        * ``CONSTANT`` — month-constant (unique count <= 1 or std == 0)
        * ``NEAR_CONSTANT`` — std below explicit threshold (very low variation)
        * ``ALL_MISSING`` — coverage 0 (no valid values)
        * ``FEW_VALID`` — non-missing count below minimum (sparse data)
        * ``VARIATION`` — real cross-sectional spread (acceptable)

    The output is a deterministic, sorted diagnostic report with one row per
    (date, feature) and columns: [date, feature, verdict, unique_count, std,
    coverage, valid_count, reason].

    Args:
        features: Long-form DataFrame with MultiIndex (date, ticker) and feature
                  columns. Expected to have DatetimeIndex for the date level.
        near_constant_std_threshold: Std threshold for NEAR_CONSTANT classification.
                                     Default: 1e-6.
        min_valid_count: Minimum non-missing count for meaningful coverage.
                         Default: 5.

    Returns:
        Sorted DataFrame with columns: [date, feature, verdict, unique_count,
        std, coverage, valid_count, reason]. Sorted by date, then feature, then verdict.

    Raises:
        ValueError: If features is empty, missing required index levels, or date level
                    is not DatetimeIndex.
    """
    # Input validation at boundaries (fail closed)
    if features is None:
        raise ValueError("features DataFrame must not be None")

    if not isinstance(features.index, pd.MultiIndex):
        raise ValueError("features must have MultiIndex (date, ticker)")

    if features.index.nlevels != 2:
        raise ValueError("features index must have exactly 2 levels: (date, ticker)")

    # Check for no columns BEFORE checking empty (DataFrame with index but no columns)
    if features.shape[1] == 0:
        raise ValueError("features must have at least one feature column")

    if features.empty:
        raise ValueError("features DataFrame must not be empty")

    # Validate date level is DatetimeIndex
    date_level = features.index.levels[0]
    if not isinstance(date_level, pd.DatetimeIndex):
        raise ValueError("features date level (index level 0) must be DatetimeIndex")

    rows: list[dict] = []

    # Group by date (the month/time index)
    for date, group in features.groupby(level=0):
        date_ts = pd.Timestamp(date)

        # For each feature column, compute cross-sectional statistics
        for feature_col in features.columns:
            series = group[feature_col]

            # Compute statistics
            valid_mask = series.notna()
            valid_count = int(valid_mask.sum())
            total_count = len(series)
            coverage = valid_count / total_count if total_count > 0 else 0.0

            # Handle all-missing case first
            if valid_count == 0:
                rows.append({
                    "date": date_ts,
                    "feature": feature_col,
                    "verdict": VERDICT_ALL_MISSING,
                    "unique_count": 0,
                    "std": np.nan,
                    "coverage": coverage,
                    "valid_count": valid_count,
                    "reason": "No valid values (coverage = 0)",
                })
                continue

            # Extract non-missing values for statistics
            valid_values = series[valid_mask]
            unique_count = int(valid_values.nunique(dropna=False))

            # Compute sample std (ddof=1); handle edge case of single value
            if valid_count == 1:
                sample_std = 0.0  # Single value has no variation
            else:
                sample_std = float(valid_values.std(ddof=1))

            # Check for constant (unique count <= 1 or std == 0)
            if unique_count <= 1 or sample_std == 0.0:
                rows.append({
                    "date": date_ts,
                    "feature": feature_col,
                    "verdict": VERDICT_CONSTANT,
                    "unique_count": unique_count,
                    "std": sample_std,
                    "coverage": coverage,
                    "valid_count": valid_count,
                    "reason": f"Unique count = {unique_count}, std = {sample_std}",
                })
                continue

            # Check for few valid (below minimum threshold)
            if valid_count < min_valid_count:
                rows.append({
                    "date": date_ts,
                    "feature": feature_col,
                    "verdict": VERDICT_FEW_VALID,
                    "unique_count": unique_count,
                    "std": sample_std,
                    "coverage": coverage,
                    "valid_count": valid_count,
                    "reason": f"Valid count ({valid_count}) < min_valid ({min_valid_count})",
                })
                continue

            # Check for near-constant (std below threshold)
            if sample_std <= near_constant_std_threshold:
                threshold_str = f"{near_constant_std_threshold:.2e}"
                rows.append({
                    "date": date_ts,
                    "feature": feature_col,
                    "verdict": VERDICT_NEAR_CONSTANT,
                    "unique_count": unique_count,
                    "std": sample_std,
                    "coverage": coverage,
                    "valid_count": valid_count,
                    "reason": f"Std ({sample_std:.2e}) <= threshold ({threshold_str})",
                })
                continue

            # Otherwise, real variation
            rows.append({
                "date": date_ts,
                "feature": feature_col,
                "verdict": VERDICT_VARIATION,
                "unique_count": unique_count,
                "std": sample_std,
                "coverage": coverage,
                "valid_count": valid_count,
                "reason": f"Real variation (std = {sample_std:.4f})",
            })

    # Build deterministic, sorted output
    df = pd.DataFrame(rows, columns=[
        "date", "feature", "verdict", "unique_count", "std", "coverage",
        "valid_count", "reason",
    ])

    # Sort by date, then feature, then verdict (stable ordering)
    df = df.sort_values(by=["date", "feature", "verdict"]).reset_index(drop=True)

    return df
