"""A-share-specific price features (Track C extras).

These features are specific to the Chinese A-share market structure:
- Limit up/down rules (main-board ±10%, STAR/ChiNext ±20%)
- Trading suspensions (tradestatus flag)

Pure functions, type-annotated, hermetic for testing.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def limit_up_down_distance(
    returns_wide: pd.DataFrame,
    limit: float = 0.10,
) -> pd.DataFrame:
    """Calculate proximity to limit up/down boundaries.

    For each date and ticker, computes |return| / limit, where 1.0 means
    the return is exactly at the ±10% main-board limit. Values > 1.0 exceed
    the limit (possible for STAR/ChiNext with ±20% limits).

    Args:
        returns_wide: Wide-format returns panel [dates x tickers].
        limit: Limit threshold (default 0.10 for main-board 10%).

    Returns:
        Wide-format DataFrame [dates x tickers] with limit proximity values.
        Values in [0, ∞), where 1.0 = at limit, >1.0 = exceeds limit.

    Note:
        STAR/ChiNext boards have ±20% limits — would need per-ticker limits
        for precise classification (out of scope, documented).
    """
    # Absolute return divided by limit threshold
    proximity = returns_wide.abs() / limit
    return proximity


def suspension_flag(tradestatus_wide: pd.DataFrame) -> pd.DataFrame:
    """Convert trade status to suspension flag (1.0 = suspended, 0.0 = normal).

    Args:
        tradestatus_wide: Wide-format trade status panel [dates x tickers],
                          where "1" = normal trading, any other value = suspended.

    Returns:
        Wide-format DataFrame [dates x tickers] with 1.0 for suspended,
        0.0 for normal trading. NaN input propagates as NaN.

    Note:
        The upstream data provider already NaN's OHLCV on suspension, so
        this flag is for explicit status tracking (e.g., for analysis or
        exclusion rules).
    """
    # Convert: "1" -> 0.0 (normal), anything else -> 1.0 (suspended)
    # NaN inputs should stay NaN
    result = pd.DataFrame(
        np.where(tradestatus_wide == "1", 0.0, 1.0),
        index=tradestatus_wide.index,
        columns=tradestatus_wide.columns,
    )
    # Propagate NaN from input
    result = result.where(tradestatus_wide.notna())
    return result
