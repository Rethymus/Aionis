"""PIT cross-section panel for stock selection (the S0/S1 feature table).

Reuses, not hand-rolls:
  * ``features.alignment`` (NYSE session grid)
  * ``ingest.fundamentals.pit_align`` (as-filed join on **filed** date)
  * ``pandas-datareader`` (Fama-French factor portfolios + FRED macro)

Every feature column is a function of info knowable at date ``t``:
  * price-derived (close[t], and derived market-cap / ratios using shares filed
    <= t) — never the future close;
  * fundamentals: the latest value FILED on or before t (pit_align);
  * FF factors + macro: published daily at t, broadcast across tickers.
The label ``y_fwd_ret`` is the h-session forward return — future, target-only.
"""
from __future__ import annotations

import pandas as pd
import structlog

from aionis.features.alignment import nyse_sessions
from aionis.ingest.fundamentals import pit_align

log = structlog.get_logger()

_FF5 = "F-F_Research_Data_5_Factors_2x3_daily"


def fama_french_daily(start: str, end: str) -> pd.DataFrame:
    """FF5 daily factor portfolio returns (Mkt-RF, SMB, HML, RMW, CMA, RF), %.
    Bulk from Tuck — not Yahoo/Stooq."""
    import pandas_datareader as pdr

    ff = pdr.get_data_famafrench(_FF5, start=start, end=end)[0]
    if isinstance(ff.index, pd.PeriodIndex):  # FF daily comes back as PeriodDtype
        ff.index = ff.index.to_timestamp()
    ff.index = pd.DatetimeIndex(ff.index).tz_localize(None).normalize()
    ff.columns = [f"ff_{c.lower().replace('-', '_')}" for c in ff.columns]
    return ff


def fred_series(series_id: str, start: str, end: str) -> pd.DataFrame:
    """One FRED series (daily macro), broadcast across the cross-section."""
    import pandas_datareader as pdr

    df = pdr.get_data_fred(series_id, start=start, end=end)
    if isinstance(df.index, pd.PeriodIndex):
        df.index = df.index.to_timestamp()
    df.index = pd.DatetimeIndex(df.index).tz_localize(None).normalize()
    df.columns = [f"macro_{series_id.lower()}"]
    return df


def forward_returns(prices: pd.DataFrame, h: int) -> pd.DataFrame:
    """h-session forward return: close[t+h]/close[t] - 1 (wide date x ticker)."""
    return prices.shift(-h) / prices - 1.0


def build_selection_panel(
    prices: pd.DataFrame,
    fundamentals_long: pd.DataFrame,
    horizon: int,
    tickers: list[str] | None = None,
    ff: pd.DataFrame | None = None,
    macro: pd.DataFrame | None = None,
    align_on: str = "filed",
    extra_features: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Assemble the PIT cross-section panel [date, ticker, features..., y_fwd_ret].

    PIT invariants: features use close[t] + fundamentals filed<=t; y_fwd_ret uses
    close[t+h] (future, target-only). ``ff``/``macro`` are date-indexed frames
    broadcast across tickers (both published at t). Forward-fill is NEVER applied
    to prices (a gap = a missing row), so no leak through imputation.

    ``align_on`` selects the fundamental-timing arm (Phase B): ``"filed"`` (default,
    ``arm_state`` — value knowable at its SEC filing date) or ``"end_lag"`` (``arm_base``
    — value knowable at period-end + a form-dependent lag; see
    :func:`aionis.ingest.fundamentals.pit_align`). The two arms share prices /
    universe / features; ONLY fundamental timing differs.

    ``extra_features`` (Phase C) is a long frame ``[date, ticker, <cols>...]`` joined
    on ``(date, ticker)`` with ``how="left"`` — for per-(ticker, date) features such as
    earnings-surprise that are NOT date-broadcast (``macro``/``ff``) and NOT
    fundamentals. It is a left join on the panel's existing rows, so it adds COLUMNS
    only (never rows) — the ``(date, ticker)`` layout is unchanged, which is what lets
    ``run_arm_oos`` assert layout equality across arms that differ only in their
    feature set. Missing (ticker, date) pairs fill as NaN (native LightGBM handling).
    """
    tickers = list(tickers or prices.columns)
    sessions = nyse_sessions(prices.index.min(), prices.index.max())
    P = prices.reindex(sessions)[tickers]

    tidy = P.stack().rename("close").to_frame()
    tidy["y_fwd_ret"] = forward_returns(P, horizon).stack()
    tidy.index.set_names(["date", "ticker"], inplace=True)
    tidy = tidy.reset_index()

    # PIT fundamentals: latest value FILED <= date (pit_align).
    if len(fundamentals_long):
        fpanels = pit_align(fundamentals_long, sessions, tickers, align_on=align_on)
        for metric, pan in fpanels.items():
            s = pan[tickers].stack().reset_index()
            s.columns = ["date", "ticker", f"fund_{metric}"]
            tidy = tidy.merge(s, on=["date", "ticker"], how="left")

    # Derived ratios (PIT: close[t] x shares filed<=t).
    sh = tidy.get("fund_shares_out")
    eq = tidy.get("fund_equity")
    ni = tidy.get("fund_net_income")
    ass = tidy.get("fund_assets")
    if sh is not None:
        tidy["mktcap"] = tidy["close"] * sh
    if sh is not None and eq is not None:
        tidy["pb_ratio"] = (tidy["close"] * sh / eq).where((sh > 0) & (eq > 0))
    if ni is not None and ass is not None:
        tidy["roa"] = (ni / ass).where(ass > 0)

    # Date-broadcast factors + macro (published at t, identical across tickers).
    if ff is not None:
        tidy = tidy.merge(ff.reset_index(names="date"), on="date", how="left")
    if macro is not None:
        tidy = tidy.merge(macro.reset_index(names="date"), on="date", how="left")

    # Per-(ticker, date) extra features (Phase C bundle, e.g. earnings-surprise).
    # Left join on the existing (date, ticker) rows -> columns only, never rows.
    if extra_features is not None and len(extra_features):
        ef = extra_features.copy()
        ef["date"] = pd.to_datetime(ef["date"]).dt.normalize()
        tidy = tidy.merge(ef, on=["date", "ticker"], how="left")
    return tidy
