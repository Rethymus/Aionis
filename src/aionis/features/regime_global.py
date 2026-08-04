"""Regime-state global layer — Diebold-Yilmaz total spillover index (US<->CN).

The generalized FEVD (Diebold-Yilmaz 2012 / Pesaran-Shin 1998) measures
cross-market contagion. For a 2-variable VAR (US/CN equity returns), the
total spillover index is the average off-diagonal FEVD share.

Anti-leakage: rolling windows are PAST-ONLY (last 250 trading days ending
at date t, never include future). Spillover at t is knowable at t.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from statsmodels.tsa.api import VAR


def equal_weighted_market_return(wide_prices: pd.DataFrame) -> pd.Series:
    """Compute equal-weighted daily market return from a wide price panel.

    Args:
        wide_prices: DataFrame with dates (index) and tickers (columns), values
                     are prices (adjClose or close). Missing values are treated
                     as non-trading (suspensions/holidays).

    Returns:
        Series of daily equal-weighted returns (NaN if no tickers traded).
    """
    if wide_prices.empty:
        return pd.Series(dtype=float)
    # Daily percent change across all tickers
    rets = wide_prices.pct_change()
    # Equal-weighted mean across tickers, ignoring NaN (suspensions)
    result = rets.mean(axis=1, skipna=True)
    result.name = "market_return"
    return result


def dy_total_spillover(
    us_ret: pd.Series,
    cn_ret: pd.Series,
    window: int = 250,
    horizon: int = 10,
) -> pd.Series:
    """Rolling-window Diebold-Yilmaz total spillover index (US<->CN, generalized FEVD).

    For each rolling window of the LAST `window` trading days ending at date t:
      1. Fit VAR(p) on [us_ret, cn_ret] with maxlags=2, ic="aic".
         If AIC picks 0 lags, fall back to lag=1 (minimum for VAR).
      2. Compute MA coefficients Φ_h for h=0..H-1 via VARResults.ma_rep(maxn=H).
      3. Extract residual covariance Σ_u = VARResults.sigma_u.values (2×2).
      4. Generalized impulse response at horizon h:
         GIR(h)[i,j] = (Φ_h @ Σ_u)[i,j] / sqrt(Σ_u[j,j])
      5. Generalized FEVD share:
         θ[i,j] = Σ_{h=0}^{H-1} GIR(h)[i,j]^2 / Σ_{k=0}^{1} Σ_{h=0}^{H-1} GIR(h)[i,k]^2
         (each row θ[i,:] sums to 1).
      6. Total spillover at t = (θ[0,1] + θ[1,0]) / 2 (fraction in [0,1]).

    Args:
        us_ret: Series of US market daily returns (aligned trading dates).
        cn_ret: Series of CN market daily returns (aligned trading dates).
        window: Rolling window size in trading days (default 250).
        horizon: Forecast horizon H for FEVD (default 10).

    Returns:
        Series of total spillover (index = window-end dates, NaN for windows
        with insufficient data or VAR estimation failure).
    """
    # Align on intersection of trading dates
    aligned = pd.DataFrame({"us": us_ret, "cn": cn_ret}).dropna()
    if len(aligned) < window:
        return pd.Series(dtype=float, name="total_spillover")

    spillovers = []
    dates = []

    for i in range(window, len(aligned) + 1):
        window_df = aligned.iloc[i - window:i]
        t_date = window_df.index[-1]

        # Fit VAR with maxlags=2, AIC lag selection (minimum lag=1)
        try:
            model = VAR(window_df.values)
            res = model.fit(maxlags=2, ic="aic")
            if res.k_ar == 0:  # AIC picked 0 lags -> fall back to lag=1
                res = model.fit(maxlags=1)

            # MA coefficients Φ_h for h=0..H-1
            phi = res.ma_rep(maxn=horizon)  # shape (H, 2, 2)

            # Residual covariance Σ_u (2×2)
            sigma = res.sigma_u
            if isinstance(sigma, pd.DataFrame):
                sigma = sigma.values  # shape (2, 2)

            # Generalized impulse responses GIR(h)[i,j]
            gir = np.zeros((horizon, 2, 2))
            for h in range(horizon):
                # GIR(h)[i,j] = (Φ_h @ Σ_u)[i,j] / sqrt(Σ_u[j,j])
                phi_sigma = phi[h] @ sigma
                for ii in range(2):
                    for j in range(2):
                        denom = np.sqrt(sigma[j, j])
                        gir[h, ii, j] = phi_sigma[ii, j] / denom

            # Generalized FEVD shares θ[i,j]
            # Numerator: Σ_{h=0}^{H-1} GIR(h)[i,j]^2
            numer = np.sum(gir ** 2, axis=0)  # shape (2, 2)
            # Denominator: Σ_{k=0}^{1} Σ_{h=0}^{H-1} GIR(h)[i,k]^2 (sum over shock sources)
            denom = numer.sum(axis=1, keepdims=True)  # shape (2, 1)
            theta = numer / denom  # shape (2, 2), each row sums to 1

            # Total spillover = (θ[0,1] + θ[1,0]) / 2
            total = (theta[0, 1] + theta[1, 0]) / 2.0
            spillovers.append(total)
            dates.append(t_date)

        except Exception:
            # VAR estimation or FEVD computation failed -> NaN for this window
            spillovers.append(float("nan"))
            dates.append(t_date)

    return pd.Series(spillovers, index=dates, name="total_spillover")
