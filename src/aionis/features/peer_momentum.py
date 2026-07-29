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

import pandas as pd

from aionis.features.propagation import propagate_panel


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
    # delegate the ex-self SIC-peer aggregation to the general propagator
    # (Phase E1 reuses the same mechanic for earnings surprises / 13D events)
    return propagate_panel(trail, sic_map, tickers=tickers)
