"""Close-only price-technical factors (qlib alpha158 subset, Aionis lacks).

A reuse-first port of the qlib alpha158 factors that (a) Aionis does NOT already
compute and (b) need ONLY the ``close`` column (PIT-safe; OHLCV-based qlib
factors like K-Bar / volume stay out of scope until the panel carries OHLCV).
See ``docs/qlib-reuse-audit.md`` §1 for the overlap matrix.

**Display-only / exploratory.** These factors are computed fresh in the export
layer (``export_themes``) to enrich the price theme; they do NOT enter the frozen
panel or the frozen LightGBM learner. Adopting them as Track-B features is a
separate, pre-registered phase (new frozen config + ledger row) — not done here.

PIT-safety: every factor uses a trailing rolling window over the per-ticker
``close`` series (current value included, no centering, no lookahead).

qlib source formulas (``microsoft/qlib`` ``qlib/contrib/data/loader.py``, MIT):
  * RANK   = percentile rank of close in window          [qlib RANK]
  * SUMP   = sum(gains) / sum(|Δ|)  (RSI-like, 0..1)      [qlib SUMP]
  * CNTP   = mean(close.diff() > 0)  (up-day fraction)    [qlib CNTP]
  * RANGE  = (Max - Min) / close  (relative recent range) [qlib MAX/MIN]
  * IMAX   = (N-1-argmax)/（N-1)  (0=at high, 1=at low)    [qlib IMAX]
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Display + module default windows: Aionis monthly/quarterly convention (not
# qlib's [5,10,20,30,60]). The frozen learner may adopt different windows in a
# future phase.
DEFAULT_WINDOWS: tuple[int, ...] = (21, 63)
_EPS = 1e-12


def _per_ticker_factors(
    close: pd.Series,
    window: int,
) -> pd.DataFrame:
    """Compute the 5 close-only factors for one ticker's close series.

    Args:
        close: a single-ticker close series, DatetimeIndex-aligned, ascending.
        window: trailing window in sessions.

    Returns:
        DataFrame (same index) with columns
        ``rank_{w}d / rsi_{w}d / cntp_{w}d / range_{w}d / timetohigh_{w}d``.
        Leading ``window-1`` rows are NaN (insufficient history) — PIT-honest.
    """
    w = window
    diff = close.diff()
    gain = diff.clip(lower=0.0)
    abs_sum = diff.abs().rolling(w).sum()
    up = (diff > 0).astype(float)
    hi = close.rolling(w).max()
    lo = close.rolling(w).min()
    # IMAX: position of the window max. argmax over the raw window returns the
    # index of the first max; N-1 = current is the max → 0 (at high); 0 = the
    # max opened the window → 1 (farthest from high).
    imax = close.rolling(w).apply(
        lambda x: (w - 1 - int(np.argmax(x))) / (w - 1) if w > 1 else 0.0,
        raw=True,
    )
    out = pd.DataFrame(index=close.index)
    out[f"rank_{w}d"] = close.rolling(w).rank(pct=True)
    out[f"rsi_{w}d"] = gain.rolling(w).sum() / abs_sum.replace(0.0, np.nan)
    out[f"cntp_{w}d"] = up.rolling(w).mean()
    out[f"range_{w}d"] = (hi - lo) / close.replace(0.0, np.nan)
    out[f"timetohigh_{w}d"] = imax
    return out


def compute_qlib_close_factors(
    panel: pd.DataFrame,
    *,
    value_col: str = "close",
    date_col: str = "date",
    ticker_col: str = "ticker",
    windows: tuple[int, ...] = DEFAULT_WINDOWS,
) -> pd.DataFrame:
    """Add close-only qlib factor columns to a long-format panel.

    Per-ticker trailing rolling factors, appended as new columns
    (``rank_21d / rsi_21d / ... / timetohigh_63d``). PIT-safe: the input panel
    is returned with extra columns only — existing columns untouched, the frozen
    parquet on disk is never written.

    Args:
        panel: long-format ``[date, ticker, close, ...]``.
        value_col: close-price column (default ``close``).
        date_col / ticker_col: panel key columns.
        windows: trailing windows in sessions (default ``(21, 63)``).

    Returns:
        The panel with factor columns appended (sorted by ``[ticker, date]``).
    """
    if value_col not in panel.columns:
        return panel  # no close → no factors (caller handles absence)
    parts: list[pd.DataFrame] = []
    for _, g in panel.groupby(ticker_col, sort=False):
        g = g.sort_values(date_col).copy()
        for w in windows:
            g = pd.concat(
                [g, _per_ticker_factors(g[value_col].astype(float), w)],
                axis=1,
            )
        parts.append(g)
    enriched = pd.concat(parts, ignore_index=False) if parts else panel
    # Preserve the caller's original index / row identity where possible.
    enriched = enriched.reindex(panel.index) if panel.index.equals(enriched.index) else enriched
    return enriched
