"""Retail-sentiment pressure: GameStop-style mention-volume surge detection.

Display-only utility: computes velocity, crowding, and directional pressure metrics
from per-ticker mention history. The module answers "is this ticker experiencing
retail attention right now?" using three complementary signals:

  - VELOCITY: mention-volume acceleration (7-day pct change).
  - CROWDING: z-score of latest daily volume vs trailing mean/std.
  - BULL/BEAR LEAN: mean sentiment polarity (-1=bearish, +1=bullish).

The GameStop 2021 squeeze was preceded by a mention-volume SURGE on r/wallstreetbets,
not just elevated sentiment polarity. Pressure grade combines velocity and crowding
to classify tickers into: 'surge', 'elevated', 'quiet', or 'normal'.

Anti-leakage contract (this is the load-bearing part):
  - This module writes NO ledger / frozen surface / E3 outcome. It is a pure
    display transform, analogous to ``ff5_residual`` and ``score_calibration``.
  - ``compute_pressure`` reads ONLY the passed-in mention history — it performs
    no data fetch, no model inference, and no market data access.
  - No live prices or forward-looking metrics leak into the computation. All inputs
    are historical mentions (already observed) and the ``latest_date`` cursor (which
    merely selects a trailing window, not a future outcome).
  - The module is deterministic and hermetic: same input history → identical output,
    suitable for cached display layers without affecting research integrity.
  - Metrics are computed over a trailing window (default 30 days) ending at
    ``latest_date``; tickers with <14 days of history are silently skipped
    (insufficient data for stable velocity estimation).

The honest signal lives in ``PressureSummary``:
  - ``velocity``: >1.0 means mentions doubled in the last 7 days vs prior 7 days.
  - ``crowding_z``: >2.5 means latest daily volume is 2.5σ above trailing mean.
  - ``grade``: 'surge' (high velocity OR high crowding), 'elevated' (moderate),
    'quiet' (declining), 'normal' (baseline).
  - ``bull_bear_lean``: mean sentiment; NaN values are ignored.
  - ``n_days``: trailing window length (excludes days with missing data).

This module is designed for the Aionis display terminal's retail-sentiment panel.
It does NOT affect any research estimator, OOS rank-IC, or frozen config.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

_MIN_HISTORY_DAYS = 14  # minimum trailing window for stable velocity
_SENTIMENT_RANGE = (-1.0, 1.0)  # valid sentiment bounds (for validation, not enforcement)


@dataclass(frozen=True)
class PressureSummary:
    """Retail-sentiment pressure metrics for a single ticker.

    Attributes:
        ticker: Ticker symbol.
        latest_mentions: Mention count on the latest day in the window.
        velocity: 7-day mention-volume pct change (cur_7d - prev_7d) / max(prev_7d, 1).
                   Positive = accelerating mentions, negative = decelerating.
        crowding_z: Z-score of latest daily volume vs trailing window mean/std.
                    Positive = above historical norm, negative = below norm.
        bull_bear_lean: Mean sentiment polarity over the window (-1=bear, +1=bull).
                        NaN sentiments are ignored; 0.0 = neutral/no data.
        grade: Discrete pressure level: 'surge', 'elevated', 'normal', 'quiet'.
        n_days: Number of days in the trailing window (excludes missing days).
    """

    ticker: str
    latest_mentions: int
    velocity: float
    crowding_z: float
    bull_bear_lean: float
    grade: str
    n_days: int


def velocity(cur_7d: int, prev_7d: int) -> float:
    """Compute 7-day mention-volume velocity (pct change).

    Args:
        cur_7d: Total mentions in the last 7 days.
        prev_7d: Total mentions in the prior 7 days.

    Returns:
        Percentage change: (cur - prev) / max(prev, 1).
        Returns 0.0 if both periods have zero mentions.
        Returns 1.0 if prev_7d <= 0 and cur_7d > 0 (infinite acceleration).

    Examples:
        >>> velocity(150, 100)
        0.5
        >>> velocity(100, 100)
        0.0
        >>> velocity(50, 100)
        -0.5
        >>> velocity(100, 0)  # division guard
        1.0
    """
    if prev_7d <= 0:
        return 1.0 if cur_7d > 0 else 0.0
    return (cur_7d - prev_7d) / max(prev_7d, 1)


def crowding_z(latest: float, mean: float, std: float) -> float:
    """Compute crowding z-score (latest mentions vs trailing distribution).

    Args:
        latest: Latest daily mention count.
        mean: Trailing window mean (historical average).
        std: Trailing window standard deviation.

    Returns:
        (latest - mean) / std, or 0.0 if std < 1e-9 (guard division by zero).

    Examples:
        >>> crowding_z(150, 100, 20)
        2.5
        >>> crowding_z(100, 100, 0)  # division guard
        0.0
    """
    if std < 1e-9:
        return 0.0
    return (latest - mean) / std


def bull_bear_lean(sentiments: np.ndarray | pd.Series | list[float]) -> float:
    """Compute mean sentiment polarity (bull/bear lean).

    Args:
        sentiments: Sequence of sentiment values in [-1, 1]. NaN values are ignored.

    Returns:
        Mean of finite sentiments, or 0.0 if all values are NaN or empty.

    Examples:
        >>> bull_bear_lean([0.5, 0.3, -0.1])
        0.23333333333333334
        >>> bull_bear_lean([np.nan, 0.5])
        0.5
        >>> bull_bear_lean([np.nan, np.nan])
        0.0
    """
    arr = np.asarray(sentiments, dtype=float)
    finite = arr[np.isfinite(arr)]
    if len(finite) == 0:
        return 0.0
    return float(finite.mean())


def pressure_grade(velocity_val: float, crowding_z_val: float) -> str:
    """Classify pressure level from velocity and crowding z-score.

    Args:
        velocity_val: 7-day mention-volume pct change.
        crowding_z_val: Z-score of latest daily volume vs trailing norm.

    Returns:
        'surge' if velocity >= 1.0 OR crowding_z >= 2.5 (extreme acceleration).
        'elevated' if velocity >= 0.5 OR crowding_z >= 1.5 (moderate acceleration).
        'quiet' if velocity <= -0.3 AND crowding_z <= -1.0 (declining).
        'normal' otherwise (baseline activity).

    Examples:
        >>> pressure_grade(1.2, 1.0)  # high velocity
        'surge'
        >>> pressure_grade(0.8, 2.0)  # high crowding
        'surge'
        >>> pressure_grade(0.6, 1.0)  # moderate
        'elevated'
        >>> pressure_grade(-0.5, -1.5)  # declining
        'quiet'
        >>> pressure_grade(0.0, 0.0)  # baseline
        'normal'
    """
    if velocity_val >= 1.0 or crowding_z_val >= 2.5:
        return "surge"
    if velocity_val >= 0.5 or crowding_z_val >= 1.5:
        return "elevated"
    if velocity_val <= -0.3 and crowding_z_val <= -1.0:
        return "quiet"
    return "normal"


def compute_pressure(
    history: list[dict[str, Any]] | pd.DataFrame,
    latest_date: str,
    lookback_days: int = 30,
) -> dict[str, PressureSummary]:
    """Compute retail-sentiment pressure metrics per ticker.

    Args:
        history: Per-ticker mention history. Either:
            - list[dict] with keys: date (YYYY-MM-DD), ticker, mentions, sentiment
            - pd.DataFrame with columns: date, ticker, mentions, sentiment
        latest_date: End of the trailing window (YYYY-MM-DD format).
        lookback_days: Trailing window length (default 30 days). Tickers with
                       <_MIN_HISTORY_DAYS (14) in the window are skipped.

    Returns:
        Dict mapping ticker → PressureSummary. Only tickers with >=14 days of
        history in the window are included. Empty dict if no tickers qualify.

    Raises:
        ValueError: If history is empty or missing required columns/keys.

    Examples:
        >>> history = [
        ...     {"date": "2024-01-01", "ticker": "GME", "mentions": 100, "sentiment": 0.5},
        ...     {"date": "2024-01-02", "ticker": "GME", "mentions": 120, "sentiment": 0.6},
        ... ]
        >>> results = compute_pressure(history, "2024-01-31", lookback_days=30)
        >>> "GME" in results
        False  # insufficient history (only 2 days)
    """
    # Convert to DataFrame if needed
    if isinstance(history, list):
        if len(history) == 0:
            raise ValueError("history is empty")
        df = pd.DataFrame(history)
    else:
        df = history.copy()

    # Validate required columns
    required = {"date", "ticker", "mentions", "sentiment"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"history missing required columns: {missing}")

    # Parse dates and filter to trailing window
    df["date"] = pd.to_datetime(df["date"])
    latest_dt = pd.Timestamp(latest_date)
    cutoff = latest_dt - pd.Timedelta(days=lookback_days)
    window = df[(df["date"] > cutoff) & (df["date"] <= latest_dt)].copy()

    if window.empty:
        return {}

    results: dict[str, PressureSummary] = {}

    for ticker in window["ticker"].unique():
        ticker_df = window[window["ticker"] == ticker].sort_values("date").copy()

        # Skip if insufficient history
        n_days = len(ticker_df)
        if n_days < _MIN_HISTORY_DAYS:
            continue

        # Compute trailing statistics
        mentions = ticker_df["mentions"].astype(int)
        sentiments = ticker_df["sentiment"].astype(float)

        latest_mentions = int(mentions.iloc[-1])
        trailing_mean = float(mentions.mean())
        trailing_std = float(mentions.std())

        # Split into cur_7d and prev_7d
        cutoff_7d = latest_dt - pd.Timedelta(days=7)
        cutoff_14d = latest_dt - pd.Timedelta(days=14)

        cur_7d = int(mentions[ticker_df["date"] > cutoff_7d].sum())
        prev_7d = int(
            mentions[
                (ticker_df["date"] > cutoff_14d) & (ticker_df["date"] <= cutoff_7d)
            ].sum()
        )

        # Compute metrics
        vel = velocity(cur_7d, prev_7d)
        crowd_z = crowding_z(float(latest_mentions), trailing_mean, trailing_std)
        lean = bull_bear_lean(sentiments.to_numpy())
        grade = pressure_grade(vel, crowd_z)

        results[ticker] = PressureSummary(
            ticker=ticker,
            latest_mentions=latest_mentions,
            velocity=round(vel, 4),
            crowding_z=round(crowd_z, 4),
            bull_bear_lean=round(lean, 4),
            grade=grade,
            n_days=n_days,
        )

    return results


def pressure_summary_to_jsonable(p: PressureSummary) -> dict[str, Any]:
    """JSON-safe view of PressureSummary (dataclasses are not json.dumps-able).

    Args:
        p: PressureSummary instance.

    Returns:
        Dict with all fields rounded for JSON serialization.
    """
    return {
        "ticker": p.ticker,
        "latest_mentions": p.latest_mentions,
        "velocity": p.velocity,
        "crowding_z": p.crowding_z,
        "bull_bear_lean": p.bull_bear_lean,
        "grade": p.grade,
        "n_days": p.n_days,
    }
