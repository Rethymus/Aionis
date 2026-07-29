"""Network shock propagation (Phase E1) — ex-self SIC-peer mean of any shock panel.

The WRL simulation/propagation layer's zero-leakage baseline: a firm's connected
entities' shocks propagate to it. This module is the general ex-self aggregator —
for each (ticker, date), the mean of same-SIC peers' shock at ``d`` (ex-self,
non-NaN). It generalizes :mod:`aionis.features.peer_momentum` (which propagates
trailing *returns*) to ANY shock panel — earnings surprise, a 13D-event indicator,
a return surprise — so Phase E1 can test whether propagated *shocks* (not levels)
carry cross-sectional signal beyond the firm's own features.

PIT: the shock at date ``d`` must be knowable at ``d`` (the caller's
responsibility — earnings-surprise via filed-date, 13D-event via filing_date).
The ex-self mean uses peers' shocks at ``d`` only — no future shock enters.

Permissive licenses only (pandas / numpy).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def propagate_panel(
    shock_wide: pd.DataFrame,
    sic_map: dict[str, str],
    *,
    tickers: list[str] | None = None,
) -> pd.DataFrame:
    """Ex-self SIC-peer mean of a shock panel -> wide (date x ticker).

    Args:
        shock_wide: wide frame (date index, ticker columns) of ANY shock knowable
            at the date (earnings surprise, 13D-event indicator, return, ...).
        sic_map: ``{ticker: sic_code}`` (from
            :func:`aionis.ingest.stakes_13d.sic_for_cik`, keyed by ticker).
        tickers: column subset (default all of ``shock_wide``).

    Returns a wide frame where ``[d, t]`` = the mean of same-SIC peers' shock at
    ``d`` (excluding ``t``, excluding NaN). NaN where the SIC group has <2 valid
    (non-NaN) members, or the ticker has no SIC.

    PIT: the caller guarantees the input shock at ``d`` is knowable at ``d``; the
    ex-self mean then uses only peers' shocks at ``d`` (no future). The ex-self
    algebra uses ``transform("count")`` (non-NaN), NOT ``transform("size")`` — on
    pandas >=3.0 ``.stack()`` retains NaN rows, so ``size`` would count NaN-
    inclusive and break the leave-one-out (see :mod:`peer_momentum`'s HIGH-1 fix).
    """
    tickers = list(tickers or shock_wide.columns)
    long = (
        shock_wide[tickers].stack().rename("shock").reset_index()
        .rename(columns={"level_0": "date", "level_1": "ticker"})
    )
    long["sic"] = long["ticker"].map(sic_map)
    long = long.dropna(subset=["sic"])
    idx = pd.DatetimeIndex(shock_wide.index)
    if long.empty:
        return pd.DataFrame(np.nan, index=idx, columns=tickers)
    grp = long.groupby(["date", "sic"], sort=False)["shock"]
    gmean = grp.transform("mean")   # mean of non-NaN (mean skips NaN)
    gn = grp.transform("count")     # count of non-NaN (NOT size — pandas>=3.0 NaN-safe)
    # ex-self mean: (sum_nonNaN - self) / (count_nonNaN - 1), defined when count >= 2
    long["prop"] = ((gmean * gn - long["shock"]) / (gn - 1)).where(gn > 1)
    wide = long.pivot(index="date", columns="ticker", values="prop")
    return wide.reindex(index=idx, columns=tickers)
