"""VIX surprise transform — turns the VIX level into a risk-premium surprise.

The VIX *level* is widely watched and likely priced; the *surprise* — how far
today's VIX deviates from what its own recent pattern implied — is the candidate
selection signal for Phase C (main line ③ of ``docs/market-driver-framework.md``:
a CHANGE / surprise in the risk premium, not its level). This module is a pure
transform: ``vix_as_of`` (the PIT-safe level) is the input; the caller fetches it.

Two surprises:
  * :func:`vix_delta` — the simple session change ``ΔVIX = VIX_t − VIX_{t-lag}``.
  * :func:`vix_ar_surprise` — the one-step residual of an ``AR(ar_lags)`` model fit
    on a rolling ``window`` of strictly-past sessions, z-scored by a
    strictly-past residual std (the 'VIX surprise': deviation from the recent
    autoregressive pattern, standardized exactly like
    :mod:`aionis.features.macro_surprise` — ``shift(1)`` before ``rolling`` so the
    denominator cannot see the residual being standardized, then clipped).

Point-in-time, by construction: every quantity at date ``t`` is a function of VIX
values dated ``<= t``. The diff is backward; the AR fit window and every regressor
it consumes are dated ``<= t-1``, so the only ``t``-dated value entering the
residual is ``VIX_t`` itself (the differenced target) — i.e. exactly the new
information in the session. An autoregressive expectation is the recognized
statistical fallback when survey consensus is unavailable (cf. Pearce-Roley 1985
on time-series vs survey expectations; Scotti 2016 on real-time surprise indexes);
standardizing by a trailing surprise std follows Balduzzi-Elton-Green 2001.

Coefficients are fit by numpy least-squares (:func:`numpy.linalg.lstsq`); no
statsmodels coupling and fully deterministic. Licenses: pandas / numpy (BSD).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import structlog

from aionis.ingest.vix import vix_as_of

log = structlog.get_logger()

AR_WINDOW = 21  # default rolling fit window (trading sessions)
AR_LAGS = 5  # default AR order
Z_CLIP = 5.0  # |z| cap on the surprise (matches macro_surprise)


def vix_delta(vix: pd.Series, lag: int = 1) -> pd.Series:
    """ΔVIX = VIX_t − VIX_{t-lag} (default 1-session change).

    PIT-safe: a backward difference uses only the value at ``t`` and one strictly
    before it; a future VIX value cannot move ``ΔVIX_t``. The leading ``lag`` rows
    are NaN (no prior to difference against); internal gaps propagate as NaN.
    """
    out = vix.astype(float).diff(lag)
    out.name = "vix_delta"
    return out


def _ar_residuals(vix: pd.Series, window: int, ar_lags: int) -> pd.Series:
    """One-step ``AR(ar_lags)`` residuals over a rolling ``window`` of past sessions.

    For each date ``t``, an OLS regression
    ``VIX_s = c + Σ_{l=1..ar_lags} b_l·VIX_{s-l}`` is fit on the ``window``
    sessions strictly before ``t`` (targets ``s ∈ [t-window, t-1]``); the fitted
    coefficients forecast ``VIX_t`` and the residual
    ``r_t = VIX_t − forecast_t`` is returned. numpy :func:`numpy.linalg.lstsq`,
    fully deterministic.

    PIT: the fit window and every regressor are dated ``<= t-1``; the only
    ``t``-dated value in ``r_t`` is ``VIX_t`` (the differenced target). The first
    ``window + ar_lags`` rows are NaN — the fit needs ``window`` complete target
    rows, and the earliest of those needs ``ar_lags`` prior values. A fit window
    containing any incomplete (NaN) row is dropped (``mask.sum() < window``) rather
    than fit on partial data and leaking through imputation.
    """
    v = vix.astype(float)
    n = int(len(v))
    if n == 0:
        return pd.Series(dtype=float, name="vix_ar_resid", index=v.index)

    vals = v.to_numpy()
    idx = v.index

    # Lag matrix: lags[i, k] = VIX_{i-(k+1)}, NaN where the lag precedes the series.
    lags = np.full((n, ar_lags), np.nan)
    for k in range(ar_lags):
        lags[k + 1 :, k] = vals[: n - (k + 1)]
    design = np.column_stack([np.ones(n), lags])  # row i: [1, VIX_{i-1}, ..., VIX_{i-ar_lags}]

    resid = np.full(n, np.nan)
    for t in range(window, n):
        lo = t - window
        if lo < ar_lags:  # the earliest target row in the window is still incomplete
            continue
        y = vals[lo:t]
        x = design[lo:t]
        mask = ~(np.isnan(x).any(axis=1) | np.isnan(y))
        if mask.sum() < window:  # require a full window of complete rows
            continue
        beta = np.linalg.lstsq(x[mask], y[mask], rcond=None)[0]
        x_t = design[t]
        if np.isnan(x_t).any():
            continue
        resid[t] = vals[t] - float(x_t @ beta)

    return pd.Series(resid, index=idx, name="vix_ar_resid")


def vix_ar_surprise(
    vix: pd.Series, window: int = AR_WINDOW, ar_lags: int = AR_LAGS
) -> pd.Series:
    """AR(ar_lags) one-step residual, z-scored by a strictly-past residual std.

    Wraps :func:`_ar_residuals`: the raw residual ``r_t`` (``VIX_t`` minus its AR
    forecast from a fit on the ``window`` sessions strictly before ``t``) is
    standardized by the rolling std (``ddof=1``) of the last ``window`` residuals
    strictly before ``t`` — ``shift(1)`` before ``rolling`` mirrors
    :mod:`aionis.features.macro_surprise` so the denominator cannot see ``r_t`` —
    then clipped to ``±Z_CLIP``. This normalized deviation from the recent
    autoregressive pattern is the 'VIX surprise'.

    PIT proof: ``r_t``'s fit window and regressors are dated ``<= t-1``; only
    ``VIX_t`` (the target) is ``t``-dated. The z denominator uses residuals dated
    ``<= t-1``. Hence a perturbation of VIX at any index ``> t`` cannot move
    ``r_t`` or ``z_t`` (the no-lookahead test perturbs exactly this); perturbing
    ``VIX_t`` moves only the numerator.
    """
    raw = _ar_residuals(vix, window=window, ar_lags=ar_lags)
    min_periods = max(ar_lags + 2, window // 2)
    scale = raw.shift(1).rolling(window, min_periods=min_periods).std(ddof=1)
    z = (raw / scale).clip(-Z_CLIP, Z_CLIP)
    z.name = "vix_ar_surprise"
    return z


def vix_surprise_panel(
    as_of_dates: pd.DatetimeIndex, *, kind: str = "ar", cache_dir: Path | None = None
) -> pd.Series:
    """Convenience: VIX surprise aligned to ``as_of_dates`` for the selection panel.

    Loads the PIT-safe VIX level via :func:`aionis.ingest.vix.vix_as_of` (the caller
    does not fetch — this is the only networked entry point in this module),
    computes the surprise (``kind='ar'`` → :func:`vix_ar_surprise`, ``kind='delta'``
    → :func:`vix_delta`), and returns a date-indexed Series aligned to
    ``as_of_dates`` — ready to hand to
    :func:`aionis.features.selection_panel.build_selection_panel` as the ``macro=``
    argument (a date-indexed frame broadcast across the cross-section).
    """
    vix = vix_as_of(as_of_dates, cache_dir=cache_dir)
    if kind == "ar":
        s = vix_ar_surprise(vix)
    elif kind == "delta":
        s = vix_delta(vix)
    else:
        raise ValueError(f"unknown kind {kind!r} (expected 'ar' or 'delta')")
    out = s.reindex(pd.DatetimeIndex(as_of_dates).normalize())
    log.info(
        "vix_surprise_built",
        kind=kind,
        n=len(out),
        n_valid=int(out.notna().sum()),
    )
    return out
