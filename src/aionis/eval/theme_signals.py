"""Theme signal summarizer — pure display transform, anti-leakage safe.

This module operationalizes the seven theme signals for the Aionis display terminal.
It converts a cross-sectional panel of raw signal values into actionable summaries:
- DIRECTION (bullish/bearish/neutral)
- STRENGTH (normalized magnitude)
- FAVORED (top-N tickers by that signal)

Anti-leakage contract (load-bearing):
  - This module reads ONLY a passed-in panel — it NEVER touches the ledger, frozen
    surfaces, or out-of-sample model scores.
  - It does NOT recompute OOS predictions or modify any research state.
  - This is a pure display transform, analogous to ``ff5_residual`` or calibration.
  - The frozen panel's latest cross-section is already in the terminal; this module
    only formats it for human consumption.
  - SIGNAL_POLARITY is a simplifying heuristic: 'bullish_high' means a high raw
    value is conventionally bullish (e.g., momentum_21d), 'bearish_high' means
    a high raw value is conventionally bearish (e.g., volatility_21d), 'neutral'
    means the signal is direction-agnostic (e.g., beta_252d). Polarity does NOT
    encode a trading strategy — it's interpretive metadata for display.
  - For 'bearish_high' signals, "favored" still means highest raw value — this is
    honest labeling as "most exposed" to that bearish signal, NOT a buy rec.

The module produces NO ledger rows, frozen surfaces, or E3 outcomes. It is
leakage-safe by construction (read-only, display-only).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

# Signal polarity is a documented simplifying heuristic.
# 'bullish_high': higher raw value → conventionally bullish (e.g., momentum)
# 'bearish_high': higher raw value → conventionally bearish (e.g., volatility)
# 'neutral': signal has no clear directional interpretation (e.g., beta)
SIGNAL_POLARITY: dict[str, str] = {
    # Momentum signals (high = bullish)
    "momentum_21d": "bullish_high",
    "momentum_42d": "bullish_high",
    # Fundamental signals (high = bullish)
    "roe": "bullish_high",
    "profit_margin": "bullish_high",
    "revenue_growth_12m": "bullish_high",
    "turnover_21d": "bullish_high",
    # Risk signals (high = bearish)
    "volatility_21d": "bearish_high",
    "volatility_63d": "bearish_high",
    "leverage": "bearish_high",
    "debt_to_equity": "bearish_high",
    "amihud_illiquidity_21d": "bearish_high",
    # Market beta (neutral — directional interpretation depends on context)
    "beta_252d": "neutral",
}


@dataclass(frozen=True)
class ThemeSignalSummary:
    """Cross-sectional summary of a single theme signal.

    Attributes:
        signal: Signal column name.
        polarity: 'bullish_high', 'bearish_high', or 'neutral' (from SIGNAL_POLARITY).
        direction: 'bullish', 'bearish', or 'neutral' — derived from polarity + mean.
        strength: Normalized magnitude of the signal (mean absolute z-score, clipped to ~3).
        mean: Cross-sectional mean of the signal (finite values only).
        n: Number of finite values in the cross-section.
        favored: Top-N tickers by the signal value (list of {ticker, value, name?, sector?}).
                  For 'bearish_high' signals, this is "most exposed", not a buy rec.
    """

    signal: str
    polarity: str
    direction: str
    strength: float
    mean: float
    n: int
    favored: list[dict[str, Any]]


def summarize_theme(
    panel: pd.DataFrame,
    signal_cols: list[str],
    top_n: int = 5,
) -> dict[str, ThemeSignalSummary]:
    """Summarize each theme signal in a cross-sectional panel.

    Args:
        panel: DataFrame with at least a 'ticker' column and the signal columns.
               Optional 'name' and 'sector' columns are included in favored if present.
        signal_cols: List of signal column names to summarize.
        top_n: Number of top tickers to return per signal (default 5).

    Returns:
        Dictionary mapping signal name → ThemeSignalSummary. Signals with <10 finite
        values are silently skipped.

    Notes:
        - Direction is derived from polarity + the sign of (mean - median). For 'neutral'
          polarity, direction is always 'neutral'.
        - Strength is the mean absolute z-score, clipped to [0, ~3] — a normalized
          magnitude that is comparable across signals.
        - For 'bearish_high' signals, favored tickers have the highest raw values
          (most exposed to that bearish signal), not the lowest.
    """
    summaries: dict[str, ThemeSignalSummary] = {}

    for signal in signal_cols:
        if signal not in panel.columns:
            continue

        # Extract finite values only
        values = panel[signal].dropna()
        n = len(values)

        # Skip signals with insufficient cross-section
        if n < 10:
            continue

        # Get polarity (default to 'neutral' if unknown)
        polarity = SIGNAL_POLARITY.get(signal, "neutral")

        # Compute cross-sectional statistics
        mean = float(values.mean())

        # Direction from polarity + value magnitude
        # For bullish_high: high values are good → direction based on sign
        # For bearish_high: high values are bad → invert logic
        #   (low positive = bullish, high positive = bearish)
        # For neutral: always neutral
        if polarity == "bullish_high":
            direction = "bullish" if mean > 0 else "bearish" if mean < 0 else "neutral"
        elif polarity == "bearish_high":
            # For bearish signals, compare mean to a threshold (0.2 for vol)
            # Low values (< threshold) → bullish, high values (> threshold) → bearish
            threshold = 0.2  # conservative threshold for "low" volatility
            direction = (
                "bullish"
                if mean < threshold
                else "bearish"
                if mean > threshold
                else "neutral"
            )
        else:  # neutral
            direction = "neutral"

        # Strength: mean absolute z-score, clipped to [0, ~3]
        z_scores = (values - values.mean()) / values.std()
        strength = float(np.abs(z_scores).mean())
        strength = min(strength, 3.0)  # Clip extreme values

        # Top-N tickers by the signal value
        # For bearish_high, this is "most exposed", not a buy rec (documented in docstring)
        top_idx = values.nlargest(top_n).index
        favored_rows = panel.loc[top_idx, ["ticker", signal]].copy()

        # Add optional columns if present
        if "name" in panel.columns:
            favored_rows = pd.concat(
                [favored_rows, panel.loc[top_idx, ["name"]]], axis=1
            )
        if "sector" in panel.columns:
            favored_rows = pd.concat(
                [favored_rows, panel.loc[top_idx, ["sector"]]], axis=1
            )

        # Build favored list (drop NaN names/sectors)
        favored: list[dict[str, Any]] = []
        for _, row in favored_rows.iterrows():
            entry: dict[str, Any] = {
                "ticker": row["ticker"],
                "value": round(float(row[signal]), 4),
            }
            if "name" in row and pd.notna(row["name"]):
                entry["name"] = str(row["name"])
            if "sector" in row and pd.notna(row["sector"]):
                entry["sector"] = str(row["sector"])
            favored.append(entry)

        summaries[signal] = ThemeSignalSummary(
            signal=signal,
            polarity=polarity,
            direction=direction,
            strength=round(strength, 4),
            mean=round(mean, 4),
            n=int(n),
            favored=favored,
        )

    return summaries


def theme_summary_to_jsonable(summary: ThemeSignalSummary) -> dict[str, Any]:
    """Convert a ThemeSignalSummary to a JSON-safe dict (dataclasses are not json.dumps-able)."""
    return {
        "signal": summary.signal,
        "polarity": summary.polarity,
        "direction": summary.direction,
        "strength": summary.strength,
        "mean": summary.mean,
        "n": summary.n,
        "favored": summary.favored,
    }
