"""SIC ex-self peer-momentum feature (Phase D WRL.Relationship).

A firm's sector peers (same SIC code, excluding the firm itself) carry a
relationship signal: the recent return of the peer group is a "propagated"
expectation for the firm (market-driver framework §2: cross-entity feedback).
This module builds the per-(ticker, date) peer-group trailing return, ex-self.

Point-in-time by construction: the trailing return uses only ``close <= t``
(a backward ``window``-session difference), and the peer mean at date ``d`` is
computed from peers' trailing returns at ``d`` — no future close enters. The SIC
map comes from :mod:`aionis.ingest.stakes_13d` (free off the submissions pull).

The ex-self mean is computed exactly as ``(group_mean * group_n - self) /
(group_n - 1)`` so a ticker never contributes to its own peer signal; a singleton
SIC group (no peers) yields NaN (no peer signal to propagate). Permissive
licenses only (pandas / numpy).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def peer_momentum_panel(
    prices: pd.DataFrame,
    sic_map: dict[str, str],
    *,
    window: int = 21,
    tickers: list[str] | None = None,
) -> pd.DataFrame:
    """Wide (date x ticker) ex-self peer trailing-return panel.

    Args:
        prices: wide adjusted-close frame (date index, ticker columns).
        sic_map: ``{ticker: sic_code}`` (from
            :func:`aionis.ingest.stakes_13d.sic_for_cik`, keyed by ticker).
        window: trailing session window for the return (default 21 ~ 1 month).
        tickers: column subset (default all of ``prices``).

    Returns a wide frame where ``[d, t]`` = the mean trailing-``window`` return of
    same-SIC peers of ``t`` (excluding ``t``) at date ``d``. NaN where the peer
    group has fewer than 2 members, or the trailing return is undefined (the first
    ``window`` sessions).
    """
    tickers = list(tickers or prices.columns)
    # backward trailing return: close[t]/close[t-window] - 1 (only close <= t)
    trail = (prices[tickers] / prices[tickers].shift(window)) - 1.0
    long = (
        trail.stack().rename("trail").reset_index()
        .rename(columns={"level_0": "date", "level_1": "ticker"})
    )
    long["sic"] = long["ticker"].map(sic_map)
    # drop tickers with no SIC (cannot form a peer group) before grouping
    long = long.dropna(subset=["sic"])
    if long.empty:
        return pd.DataFrame(
            np.nan, index=pd.DatetimeIndex(prices.index), columns=tickers,
        )
    grp = long.groupby(["date", "sic"], sort=False)["trail"]
    gmean = grp.transform("mean")
    # count of NON-NaN trails (NOT size): on pandas >=3.0 `.stack()` retains NaN
    # rows, so `transform("size")` would count NaN-inclusive while `mean` skips
    # them, making `(mean*size - self)/(size-1)` wrong whenever a peer's trailing
    # return is undefined (warmup / newly entered). `count` keeps the leave-one-out
    # algebra exact, and `.where(gn > 1)` then NaNs a group with <2 valid peers.
    gn = grp.transform("count")
    # ex-self mean: (sum - self) / (n - 1), defined only when n >= 2
    long["peer_mom"] = (
        (gmean * gn - long["trail"]) / (gn - 1)
    ).where(gn > 1)
    wide = long.pivot(index="date", columns="ticker", values="peer_mom")
    # reindex to the full price index + requested tickers (NaN where no peer signal)
    return wide.reindex(index=pd.DatetimeIndex(prices.index), columns=tickers)
