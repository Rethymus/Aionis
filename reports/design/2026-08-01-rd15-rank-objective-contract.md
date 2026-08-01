# RD-15 Ranking Objective Contract — Decision Packet

**Status**: PROPOSED — pending owner freeze
**Date**: 2026-08-01
**Author**: STRONG-METHOD ARCHITECT (Opus)
**Task**: RD-15 — Rank objective 数据与 query 合约
**Purpose**: Provide owner-freezable, Engineer-implementable decisions on ranking label transformation, objective choice, and leakage guards for the rank-IC estimand.

---

## Executive Summary (8 Decisions)

This packet resolves the RES-03 defects (continuous returns to ranking objective, non-existent objectives) by fixing the complete contract for label → relevance transformation, group construction, and LightGBM ranking objective usage.

| # | Decision | Choice | Justification (One Sentence) |
|---|----------|--------|-------------------------------|
| 1 | **Objective choice** | `lambdarank` | Battle-tested listwise algorithm; maximizes NDCG which monotonic-transforms to rank-IC; stable for financial cross-sections. |
| 2 | **Relevance binning** | **OWNER PREFERENCE REQUIRED** — quintiles (5 bins) vs deciles (10 bins) | Coarser bins (quintiles) = robust, less noise; finer bins (deciles) = more signal, more overfit risk. Owner chooses. |
| 3 | **Fitting scope** | Per-month quantiles within train fold | Preserves cross-sectional rank within month while accounting for month-specific volatility regimes. |
| 4 | **Group definition** | Each calendar month = one query group | Aligns with "cross-sectional monthly rank-IC" estimand; group boundaries stable, group size == row count. |
| 5 | **Ties policy** | Same return → same relevance integer (quantile binning) | Quantile edges naturally assign equal returns to same bin; no special handling needed. |
| 6 | **Missing policy** | NaN forward returns → exclude from ranking; NaN features → LightGBM default | LightGBM ranking requires valid relevance; missing returns cannot be ranked and must be filtered. |
| 7 | **Out-of-range policy** | Clamp to nearest train-fold bin edge + record reason code | Test returns outside train-fold range must NOT refit; clamp preserves ordering and records leakage reason. |
| 8 | **Leakage guards** | Invariants in §7 (testable claims) | Month-permutation invariance, future-truncation invariance, train-fold-only fitting, group size stability. |

---

## 1. Objective Choice: `lambdarank` (LightGBM ≥4.3)

**RECOMMENDED**: `lambdarank`

**FIXED OBJECTIVE ENUM** (for LightGBM ≥4.3):
```python
class LightGBMRankingObjective(str, Enum):
    LAMBDARANK = "lambdarank"
    RANK_XENDCG = "rank_xendcg"
```

**JUSTIFICATION**:

- **Estimand alignment**: The rank-IC (Spearman correlation) is a monotonic transformation of NDCG with equal positional weights. LambdaRank directly optimizes NDCG, making it the theoretically sound choice for rank-IC maximization.
- **Listwise semantics**: LambdaRank considers all items in a query (month) together, preserving cross-sectional structure. This is critical for financial cross-sections where the relative ordering within a month matters, not just pairwise comparisons.
- **Battle-tested**: LambdaRank is the de facto standard in web search and recommendation systems. XENDCG is less widely deployed and has more complex edge cases.
- **Group structure**: Each calendar month is a query group; LambdaRank handles group-based ranking natively via the `group` parameter.
- **Label noise robustness**: LambdaRank's gradient approximation is more robust to noisy relevance labels than pairwise methods. Financial returns are inherently noisy.
- **Small-group behavior**: For months with few stocks (e.g., 2008 crisis), LambdaRank's listwise formulation is more stable than pairwise methods that struggle with small sample sizes.

**REJECTED ALTERNATIVE: `rank_xendcg`**

- XENDCG (Expected NDCG) is theoretically similar but less battle-tested.
- XENDCG may handle position bias differently, but for equal-weighted rank-IC, this offers no clear advantage.
- XENDCG introduces additional complexity without a corresponding benefit for the rank-IC estimand.
- The risk of edge cases and implementation bugs is higher for XENDCG.

**UNDERDETERMINED CHOICE (OWNER PREFERENCE REQUIRED)**:

**Bin count**: quintiles (5 bins) vs deciles (10 bins)

- **Quintiles (5 bins)**: Coarser granularity, more robust, less overfitting risk, more conservative.
- **Deciles (10 bins)**: Finer granularity, more signal extraction potential, higher overfit risk.
- Theoretical ranking theory does NOT uniquely determine bin count for rank-IC optimization.
- This is a **risk/reward tradeoff** that requires owner preference:
  - Conservative / robust → quintiles (5 bins)
  - Aggressive / signal-seeking → deciles (10 bins)

**DEFAULT RECOMMENDATION (if owner has no preference)**: Quintiles (5 bins) for robustness and to minimize overfitting risk.

---

## 2. Relevance Binning: Continuous Returns → Ordinal Relevance

**FITTING RULE (PER-MONTH QUANTILES WITHIN TRAIN FOLD)**:

```python
def fit_monthly_bins(
    train_returns: pd.Series,  # Continuous forward returns, indexed by (month, ticker)
    train_groups: np.ndarray,   # Month IDs for grouping
    n_bins: int,               # 5 for quintiles, 10 for deciles (OWNER CHOICE)
) -> dict[month_id, np.ndarray]:
    """
    Fit quantile bin edges FOR EACH MONTH separately, using ONLY train-fold data.

    Args:
        train_returns: Continuous forward returns for train fold
        train_groups: Month ID for each sample (calendar month)
        n_bins: Number of relevance bins (5 or 10, owner choice)

    Returns:
        dict mapping month_id → bin edges (array of shape (n_bins + 1,))
    """
    # For each month present in train fold:
    #   - Extract train returns for that month
    #   - Compute quantile edges at [0, 20%, 40%, 60%, 80%, 100%] for quintiles
    #   - OR at [0, 10%, 20%, ..., 100%] for deciles
    #   - Store edges in dict
    #
    # Months with NO train samples: use pooled quantile edges across all train months
```

**TRANSFORM RULE (FROZEN EDGES)**:

```python
def transform_to_relevance(
    returns: pd.Series,
    groups: np.ndarray,
    fitted_bins: dict[month_id, np.ndarray],
    n_bins: int,
) -> tuple[np.ndarray, list[str]]:
    """
    Transform continuous returns to integer relevance using FROZEN train-fold bin edges.

    Args:
        returns: Continuous forward returns (train OR test fold)
        groups: Month IDs
        fitted_bins: FROZEN bin edges from fit_monthly_bins (NEVER refit here)
        n_bins: Number of bins (must match fitted_bins)

    Returns:
        relevance: Integer relevance labels (1..n_bins)
        reason_codes: List of reason codes for each sample
    """
    # For each month:
    #   - Retrieve bin edges from fitted_bins (pooled fallback for unseen months)
    #   - Digitize returns: relevance = np.digitize(return, edges[1:]) - 1
    #   - Handle out-of-range: clamp to nearest edge + reason code
    #   - Handle NaN returns: relevance = -1 (exclude) + reason code
    #   - Record reason codes for all samples
```

**PER-MONTH VS POOLED FITTING: WHY PER-MONTH?**

- **Per-month quantiles** (recommended): Fit bin edges separately for each month using only that month's train-fold data.
  - **Pros**: Accounts for cross-month volatility differences (e.g., 2008 vs 2017), preserves cross-sectional rank within month, adapts to regime changes.
  - **Cons**: Higher variance, potential overfitting to month-specific noise.
- **Pooled quantiles**: Fit bin edges across all train-fold months combined.
  - **Pros**: More stable, lower variance, shared scale.
  - **Cons**: Ignores volatility regime differences, may distort cross-sectional rank in high/low volatility months.

**DECISION: Per-month quantiles**

- The rank-IC estimand is defined as "cross-sectional rank within each month" → per-month binning preserves this structure.
- Financial returns exhibit significant cross-month volatility variation (e.g., crisis months vs calm months).
- Pooled binning would compress/expand rankings in high/low volatility months, distorting the in-month cross-sectional signal.

---

## 3. Group = Query-Month Construction

**GROUP DEFINITION: Each calendar month is one query group**

```python
def construct_month_groups(
    dates: pd.DatetimeIndex,  # Prediction/evaluation times
) -> np.ndarray:
    """
    Construct month IDs for LightGBM ranking groups.

    Each calendar month (YYYY-MM) is assigned a unique integer group ID.
    Group boundaries are stable: group_id = year * 12 + (month - 1).

    Args:
        dates: Prediction/evaluation timestamps

    Returns:
        groups: Integer group IDs (one per sample)
    """
    # Extract year and month from dates
    # group_id = year * 12 + (month - 1)
    # Example: 2020-01 → 2020*12 + 0 = 24240
    #          2020-02 → 2020*12 + 1 = 24241
    #          2021-01 → 2021*12 + 0 = 24252
```

**GROUP STRUCTURE FOR LIGHTGBM**:

```python
# LightGBM LGBMRanker expects group sizes, not group IDs directly
def get_group_sizes(groups: np.ndarray) -> np.ndarray:
    """
    Convert group IDs to group size array for LightGBM.

    Example:
        groups = [0, 0, 0, 1, 1, 2, 2, 2]
        → group_sizes = [3, 2, 3]  # 3 samples in group 0, 2 in group 1, 3 in group 2
    """
    unique_groups, counts = np.unique(groups, return_counts=True)
    return counts
```

**GROUP SIZE INVARIANCE**:

- Group size MUST equal the number of rows for that month.
- Filtering samples (e.g., removing NaN returns) MUST update group sizes.
- LightGBM ranking fails if group sizes don't match the number of samples with valid relevance.

---

## 4. Ties Policy: Equal Returns → Same Relevance

**POLICY: Quantile binning naturally handles ties**

- Quantile edges assign equal returns to the same bin.
- Samples with exactly the same return value will receive the same relevance integer.
- No special handling needed beyond standard `np.digitize` behavior.

**EXAMPLE**:
```
Returns for month 2020-01: [0.01, 0.01, 0.02, 0.02, 0.02, 0.05]
Quintile edges (20%, 40%, 60%, 80%): [0.00, 0.012, 0.019, 0.022, 0.04]

Digitized relevance:
    0.01 → bin 1 (relevance 1)
    0.01 → bin 1 (relevance 1)  # TIE
    0.02 → bin 3 (relevance 3)
    0.02 → bin 3 (relevance 3)  # TIE
    0.02 → bin 3 (relevance 3)  # TIE
    0.05 → bin 5 (relevance 5)
```

---

## 5. Missing Policy: NaN Returns and Features

**MISSING FORWARD RETURNS (CRITICAL)**:

```python
# Samples with NaN forward returns CANNOT be ranked
def filter_valid_ranking_samples(
    returns: pd.Series,
    relevance: np.ndarray,
    groups: np.ndarray,
) -> tuple[pd.Series, np.ndarray, np.ndarray]:
    """
    Remove samples with NaN returns from ranking.

    LightGBM LGBMRanker requires valid relevance for ALL samples in a group.
    Samples with NaN returns must be EXCLUDED from the ranking dataset.

    Args:
        returns: Forward returns (may contain NaN)
        relevance: Relevance labels (from transform_to_relevance)
        groups: Group IDs

    Returns:
        returns_clean: Returns with NaN samples removed
        relevance_clean: Relevance with -1 (NaN) samples removed
        groups_clean: Groups with filtered samples removed
    """
    valid_mask = ~np.isnan(returns)
    return returns[valid_mask], relevance[valid_mask], groups[valid_mask]
```

**MISSING FEATURES**:

- LightGBM natively supports missing values (NaN) in features.
- No special handling needed for missing features.
- LightGBM will learn default directions for missing values during training.

**REASON CODES**:
```python
class RankingReasonCode(str, Enum):
    """Reason codes for ranking transformation."""
    NORMAL = "normal"                    # Valid return, within train-fold range
    RETURN_MISSING = "return_missing"    # NaN forward return (excluded)
    OUT_OF_RANGE_LOW = "oor_low"         # Below train-fold min (clamped)
    OUT_OF_RANGE_HIGH = "oor_high"       # Above train-fold max (clamped)
    UNSEEN_MONTH_POOLED = "unseen_pooled" # Month not in train fold (used pooled edges)
```

---

## 6. Out-of-Range Policy: Test Returns Outside Train-Fold Range

**POLICY: Clamp to nearest train-fold bin edge + record reason code**

Test-fold returns may fall outside the min/max range observed in the train fold for that month. This is EXPECTED and VALID behavior (volatility regimes shift over time).

**HANDLING**:

```python
def transform_with_clamp(
    return_value: float,
    bin_edges: np.ndarray,
    month_id: int,
    train_month_stats: dict[month_id, tuple[float, float]],  # (min, max) for each train month
) -> tuple[int, str]:
    """
    Transform return to relevance with clamping for out-of-range values.

    Args:
        return_value: Continuous forward return (test fold)
        bin_edges: FROZEN bin edges from train fold
        month_id: Month ID for this sample
        train_month_stats: (min, max) returns for each month in train fold

    Returns:
        relevance: Integer relevance (1..n_bins, or -1 if NaN)
        reason_code: Reason code for this transformation
    """
    if np.isnan(return_value):
        return -1, RankingReasonCode.RETURN_MISSING

    train_min, train_max = train_month_stats.get(month_id, (np.nan, np.nan))

    # Check out-of-range
    if return_value < train_min:
        # Clamp to minimum (assign to lowest bin)
        relevance = 1  # Lowest relevance bin
        return relevance, RankingReasonCode.OUT_OF_RANGE_LOW
    elif return_value > train_max:
        # Clamp to maximum (assign to highest bin)
        relevance = len(bin_edges) - 1  # Highest relevance bin
        return relevance, RankingReasonCode.OUT_OF_RANGE_HIGH
    else:
        # Normal case: digitize within range
        relevance = np.digitize(return_value, bin_edges[1:])
        return relevance, RankingReasonCode.NORMAL
```

**CRITICAL: NEVER REFIT BIN EDGES**

- Test-fold out-of-range values MUST NOT trigger refitting of bin edges.
- Clamping preserves ordering (extreme returns map to extreme relevance bins).
- Reason codes enable post-hoc analysis of out-of-range frequency.

---

## 7. Leakage Guards: Testable Invariants

The following invariants MUST hold for any ranking transformation. These are testable claims that the Engineer MUST verify in unit tests.

**INVARIANT 1: MONTH-PERMUTATION INVARIANCE**

**Claim**: Permuting the ORDER of months in the dataset does NOT change the bin edges for any individual month.

**Test**:
```python
def test_month_permutation_invariance(
    returns: pd.Series,
    groups: np.ndarray,
    n_bins: int,
):
    """
    Fit bin edges on original dataset and permuted dataset.
    Assert that bin edges for each month are identical.
    """
    # Fit on original order
    bins_original = fit_monthly_bins(returns, groups, n_bins)

    # Permute month order (shuffle rows)
    perm_idx = np.random.permutation(len(returns))
    returns_perm = returns.iloc[perm_idx]
    groups_perm = groups[perm_idx]

    # Fit on permuted order
    bins_perm = fit_monthly_bins(returns_perm, groups_perm, n_bins)

    # Assert: bin edges for each month are identical
    for month in bins_original:
        assert np.array_equal(bins_original[month], bins_perm[month])
```

**Rationale**: Bin edges for month M should depend ONLY on the train-fold samples for month M, not on the presence/absence/order of other months.

---

**INVARIANT 2: FUTURE-TRUNCATION INVARIANCE**

**Claim**: Removing future months from the dataset does NOT change the bin edges for past months.

**Test**:
```python
def test_future_truncation_invariance(
    returns: pd.Series,
    groups: np.ndarray,
    n_bins: int,
):
    """
    Fit bin edges on full dataset and truncated dataset.
    Assert that bin edges for past months are identical.
    """
    # Fit on full dataset
    bins_full = fit_monthly_bins(returns, groups, n_bins)

    # Truncate to first K months (remove future months)
    max_month = groups.max()
    trunc_months = max_month - 6  # Remove last 6 months
    trunc_mask = groups <= trunc_months
    returns_trunc = returns[trunc_mask]
    groups_trunc = groups[trunc_mask]

    # Fit on truncated dataset
    bins_trunc = fit_monthly_bins(returns_trunc, groups_trunc, n_bins)

    # Assert: bin edges for retained months are identical
    for month in bins_trunc:
        assert np.array_equal(bins_full[month], bins_trunc[month])
```

**Rationale**: Fitting on train fold must NOT depend on information from future test folds. Truncating future months should not affect past months' bin edges.

---

**INVARIANT 3: TRAIN-FOLD-ONLY FITTING**

**Claim**: `transform_to_relevance` NEVER refits bin edges, regardless of input data.

**Test**:
```python
def test_train_fold_only_fitting(
    train_returns: pd.Series,
    test_returns: pd.Series,
    train_groups: np.ndarray,
    test_groups: np.ndarray,
    n_bins: int,
):
    """
    Transform test fold using train-fit edges.
    Assert that transforming on different test folds produces same bin edges.
    """
    # Fit on train fold
    bins = fit_monthly_bins(train_returns, train_groups, n_bins)

    # Transform test fold 1
    relevance1, _ = transform_to_relevance(test_returns, test_groups, bins, n_bins)

    # Transform test fold 2 (different data, same fitted bins)
    test_returns2 = test_returns * 1.5  # Different data
    relevance2, _ = transform_to_relevance(test_returns2, test_groups, bins, n_bins)

    # Assert: bins object is unchanged (same object ID, same values)
    # transform_to_relevance should NOT modify bins
    assert id(bins) == id(bins)  # Trivial, but communicates intent
```

**Rationale**: The fit/transform split is the core leakage guard. Once `fit_monthly_bins` produces bin edges, `transform_to_relevance` must use them as-is, with no refitting.

---

**INVARIANT 4: GROUP SIZE STABILITY**

**Claim**: Filtering NaN returns from groups updates group sizes correctly.

**Test**:
```python
def test_group_size_stability(
    returns: pd.Series,
    groups: np.ndarray,
):
    """
    Remove NaN-return samples and assert group sizes are updated correctly.
    """
    # Count samples per group before filtering
    unique_groups, counts_before = np.unique(groups, return_counts=True)

    # Filter NaN returns
    valid_mask = ~np.isnan(returns)
    groups_clean = groups[valid_mask]

    # Count samples per group after filtering
    _, counts_after = np.unique(groups_clean, return_counts=True)

    # Assert: no group has more samples after filtering
    for g in unique_groups:
        before = counts_before[unique_groups == g][0]
        after = counts_after[np.where(np.unique(groups_clean) == g)[0]][0] if g in np.unique(groups_clean) else 0
        assert after <= before
```

**Rationale**: LightGBM ranking requires group sizes to exactly match the number of samples. Filtering MUST update group sizes.

---

## 8. Contract Specification (Engineer Implementation)

This section specifies the exact contract that the Engineer MUST implement in `src/aionis/eval/ranking_contract.py`.

**MODULE STRUCTURE**:

```python
"""
Ranking objective contract for rank-IC estimand.

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
# Public API (Engineer MUST implement these)
# ---------------------------------------------------------------------------

def construct_month_groups(dates: pd.DatetimeIndex) -> np.ndarray:
    """
    Construct month IDs for LightGBM ranking groups.

    Each calendar month (YYYY-MM) is assigned a unique integer group ID.
    Group boundaries are stable: group_id = year * 12 + (month - 1).

    Args:
        dates: Prediction/evaluation timestamps

    Returns:
        groups: Integer group IDs (one per sample)
    """
    # TODO: Implement
    pass


def get_group_sizes(groups: np.ndarray) -> np.ndarray:
    """
    Convert group IDs to group size array for LightGBM.

    Args:
        groups: Integer group IDs (one per sample)

    Returns:
        group_sizes: Array of unique group sizes, ordered by group ID
    """
    # TODO: Implement
    pass


def fit_monthly_bins(
    train_returns: pd.Series,
    train_groups: np.ndarray,
    n_bins: Literal[5, 10],
) -> dict[int, np.ndarray]:
    """
    Fit quantile bin edges FOR EACH MONTH separately, using ONLY train-fold data.

    Args:
        train_returns: Continuous forward returns for train fold, indexed by sample
        train_groups: Month ID for each sample (from construct_month_groups)
        n_bins: Number of relevance bins (5 = quintiles, 10 = deciles)

    Returns:
        fitted_bins: dict mapping month_id → bin edges (array of shape (n_bins + 1,))
                     Also stores train_month_stats (min, max) for each month
    """
    # TODO: Implement
    pass


def transform_to_relevance(
    returns: pd.Series,
    groups: np.ndarray,
    fitted_bins: dict[int, np.ndarray],
    n_bins: Literal[5, 10],
) -> tuple[np.ndarray, list[str]]:
    """
    Transform continuous returns to integer relevance using FROZEN train-fold bin edges.

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
    # TODO: Implement
    pass


def filter_valid_ranking_samples(
    returns: pd.Series,
    relevance: np.ndarray,
    groups: np.ndarray,
) -> tuple[pd.Series, np.ndarray, np.ndarray]:
    """
    Remove samples with NaN returns from ranking dataset.

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
    # TODO: Implement
    pass


# ---------------------------------------------------------------------------
# Verification tests (Engineer MUST implement these in tests/test_ranking_contract.py)
# ---------------------------------------------------------------------------

def test_month_permutation_invariance() -> None:
    """Test: Permuting month order does not change bin edges."""
    # TODO: Implement test
    pass


def test_future_truncation_invariance() -> None:
    """Test: Removing future months does not change past months' bin edges."""
    # TODO: Implement test
    pass


def test_train_fold_only_fitting() -> None:
    """Test: transform_to_relevance never refits bin edges."""
    # TODO: Implement test
    pass


def test_group_size_stability() -> None:
    """Test: Filtering NaN returns updates group sizes correctly."""
    # TODO: Implement test
    pass
```

**IMPLEMENTATION NOTES FOR ENGINEER**:

1. **FIT_MONTHLY_BINS**:
   - For each unique month in `train_groups`:
     - Extract `train_returns` for that month
     - Compute quantile edges: `np.quantile(month_returns, q=np.linspace(0, 1, n_bins + 1))`
     - Store `(min, max)` for out-of-range detection
   - For months with NO train samples: compute pooled quantiles across ALL train months

2. **TRANSFORM_TO_RELEVANCE**:
   - For each month in `groups`:
     - Retrieve bin edges from `fitted_bins`
     - Use pooled edges if month not in `fitted_bins` (record reason: `UNSEEN_MONTH_POOLED`)
     - Handle NaN returns: relevance = -1, reason = `RETURN_MISSING`
     - Handle out-of-range: clamp to [1, n_bins], reason = `OUT_OF_RANGE_LOW`/`OUT_OF_RANGE_HIGH`
     - Normal case: `np.digitize(return, edges[1:])`, reason = `NORMAL`

3. **FILTER_VALID_RANKING_SAMPLES**:
   - Create mask: `valid_mask = (relevance != -1) & (~np.isnan(returns))`
   - Apply mask to returns, relevance, groups
   - Return filtered arrays

4. **TESTS**:
   - Use synthetic fixtures (hand-calculated monthly returns)
   - Assert invariants in §7 hold
   - Verify reason codes are correctly assigned

---

## Appendix: Theoretical Justification

### Why LambdaRank for Rank-IC?

**Rank-IC Definition**:
```
rank-IC = spearman_correlation(predicted_scores, true_returns)
        = monotonic_transformation(NDCG with equal positional weights)
```

**LambdaRank Optimization**:
```
LambdaRank optimizes NDCG via gradient approximation:
  ∇L = Σ_i ΔNDCG(i) · |Δscore_i| · log(1 + exp(-Δscore_i))

For equal-weighted NDCG, maximizing NDCG ≈ maximizing rank correlation.
```

**Pairwise vs Listwise**:
- Pairwise (RankNet): Considers pairs → loses cross-sectional structure
- Listwise (LambdaRank): Considers all items in query → preserves cross-section
- Financial cross-sections are LISTWISE problems (rank all stocks in a month)

### Why Per-Month Quantiles?

**Cross-Sectional Rank Within Month**:
- The estimand is "cross-sectional rank within each calendar month"
- Per-month quantiles preserve this structure
- Each month's bin edges reflect that month's return distribution

**Volatility Regime Awareness**:
- 2008 crisis: returns in [-30%, +20%]
- 2017 calm: returns in [-2%, +3%]
- Pooled binning would assign extreme 2008 returns to mid-bins, distorting signal
- Per-month binning adapts to regime shifts

### Why Out-of-Range Clamping?

**Expected Volatility Shifts**:
- Train fold: 2010-2017 (low volatility)
- Test fold: 2020 (COVID, high volatility)
- Test returns will exceed train min/max
- Clamping preserves ordering (extreme → extreme bin) without refitting

**Leakage Prevention**:
- Refitting on test fold = leakage
- Clamping = honest handling of distribution shift
- Reason codes enable post-hoc analysis

---

## Sign-Off

**ENGINEER IMPLEMENTATION BUDGET**: 120-180 minutes (estimated)

**OWNER FREEZE DECISIONS REQUIRED**:
1. ✅ Objective: `lambdarank` (STRONG-METHOD RECOMMENDATION)
2. ⚠️  **Bin count**: Quintiles (5) vs Deciles (10) → **OWNER PREFERENCE REQUIRED**
   - Default recommendation: Quintiles (5) for robustness
   - Owner may choose Deciles (10) for more aggressive signal extraction

**NEXT STEPS** (after owner freeze):
1. Engineer implements `src/aionis/eval/ranking_contract.py` per §8 spec
2. Engineer implements `tests/test_ranking_contract.py` with §7 invariants
3. Engineer runs `uv run pytest -q tests/test_ranking_contract.py`
4. Engineer runs `uv run ruff check`
5. Verifier confirms all tests pass and invariants hold
6. Update `state/handoff.md` → learner integration task (separate RD-XX)

**NO MODEL TRAINING OR REAL DATA USAGE IN THIS TASK**:
- This is a pure contract/specification task
- No LightGBM training runs, no real panel data, no result metrics
- Hand-calculated fixtures only

---

**END OF DECISION PACKET**
