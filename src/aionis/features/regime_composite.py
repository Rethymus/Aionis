"""Regime-state composite: equal-weight of standardized layers + TACO expanding-as-of σ.

Frozen Track C config (#46): ``regime_state.composite = equal-weight of 3 z-scored layers
(meso + macro + global); normalization = expanding-as-of sigma (TACO; computed on [t0, t]
fixed at each t, NO retrospective recompute); role = single pre-specified interaction
(score x regime_state).``

This module is GENERIC over N layers. Currently fed macro + global only (meso deferred —
shenwan/SIC sector data sourcing is the hardest 7-gate gap). The 2-layer composite is
EXPLORATORY; the frozen 3-layer composite + a new ledger row is required for the
confirmatory Track C claim.

Anti-leakage: layer z-scores use PAST-ONLY rolling windows (shift(1) before the rolling
mean/std); TACO expanding σ uses [t0, t] (includes t = the as-of observation; never future).
``regime_state_t`` is therefore knowable at t (PIT-safe).
"""

from __future__ import annotations

import pandas as pd

# Past-only standardization window (trading days).
_Z_WINDOW = 252
_Z_MIN = 126
# TACO expanding-σ warmup.
_TACO_MIN = 252


def rolling_zscore(
    series: pd.Series,
    window: int = _Z_WINDOW,
    min_periods: int = _Z_MIN,
) -> pd.Series:
    """Past-only rolling z-score: (x_t - mean[x_{<t}]) / std[x_{<t}].

    The mean/std are computed on the shift(1)-gated series (strictly before t), so the
    current value x_t is scored against its own recent PAST only — no future leakage.
    """
    past = series.shift(1)
    mean = past.rolling(window=window, min_periods=min_periods).mean()
    std = past.rolling(window=window, min_periods=min_periods).std()
    return (series - mean) / std


def taco_normalize(series: pd.Series, min_periods: int = _TACO_MIN) -> pd.Series:
    """TACO expanding-as-of σ normalization: x_t / std(x[t0..t]).

    The expanding std at t is computed over [t0, t] (the as-of observation included; never
    future; never retroactively recomputed when new data arrives). This is the frozen
    config's ``regime_state.normalization``.
    """
    expanding_std = series.expanding(min_periods=min_periods).std()
    return series / expanding_std


def regime_composite(
    layers: dict[str, pd.Series],
    taco_min_periods: int = _TACO_MIN,
    zscore_window: int = _Z_WINDOW,
    zscore_min_periods: int = _Z_MIN,
) -> pd.Series:
    """Equal-weight composite of z-scored layers + TACO normalization -> regime_state.

    Each layer is independently past-only z-scored (puts macro/global/... on a comparable
    "current-vs-recent-past" scale), then equal-weighted, then TACO-normalized.

    Args:
        layers: {name: daily Series} (e.g. {"macro": macro_regime, "global": spillover}).
        taco_min_periods: TACO expanding-σ warmup (default 252).

    Returns:
        Daily ``regime_state`` Series (PIT-safe, TACO-normalized), named "regime_state".
    """
    if not layers:
        return pd.Series(dtype=float, name="regime_state")
    z = pd.DataFrame(
        {
            name: rolling_zscore(s, window=zscore_window, min_periods=zscore_min_periods)
            for name, s in layers.items()
        }
    )
    composite_raw = z.mean(axis=1, skipna=True)
    out = taco_normalize(composite_raw, min_periods=taco_min_periods)
    out.name = "regime_state"
    return out
