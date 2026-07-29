"""Event-study (cumulative abnormal return, CAR) for the dashboard v2
"pre/post-event differences" dimension.

PIT NOTE (read me): this module is DESCRIPTIVE analysis of *realized* post-event
drift, produced for visualization only. It intentionally uses forward
(post-event) returns to measure drift -- the CAR curve *is* the post-event price
path of an event-ticker minus an equal-weight cross-section benchmark. That is
the same lens as the strategy-return / rank-IC evaluation modules, which also
consume realized forward returns. This is NOT a point-in-time feature feeding the
predictive model: nothing here enters the ERL / design matrix, so the use of
post-event returns is not lookahead leakage. The predictive pipeline's
anti-leakage discipline (filed-date vs period-end, PIT audit, freeze ledger)
lives in the feature builders (:mod:`aionis.eval.phase_b_controls`,
:mod:`aionis.eval.pit_audit`), not here.

CAR definition (per event_type):
    For each event, AR[offset] = ret[ticker, event_date+offset]
                                 - ret[benchmark, event_date+offset]
    for trading-session offsets in [-k_before, +k_after] (price-index positions,
    offset 0 = the event session). benchmark="cross_section" is the equal-weight
    cross-section mean daily return per date (the "market").

    Per-event CAR is the cumulative sum of the AR series along the offset axis
    (prefix sum from -k_before). The headline ``car`` is the mean of that
    per-event cumsum across events; ``car_se`` is the across-event standard error
    of that cumsum statistic; the 95% CI is ``car +/- 1.96 * car_se``.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

Z_95 = 1.96

# ALFRED series id -> human event-type label for broadcast macro events.
_MACRO_EVENT_TYPE = {"CPIAUCSL": "CPI", "PAYEMS": "NFP"}


def cumulative_abnormal_return(
    prices: pd.DataFrame,
    events: pd.DataFrame,
    *,
    k_before: int = 10,
    k_after: int = 20,
    benchmark: str = "cross_section",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compute cumulative abnormal return (CAR) curves around events.

    Parameters
    ----------
    prices : pd.DataFrame
        Wide ``date x ticker`` daily price frame (rows = trading sessions sorted
        ascending, columns = tickers, values = prices). ``daily_return`` is
        derived here via ``pct_change`` (so the first row is NaN).
    events : pd.DataFrame
        Long frame with columns ``[ticker, event_date, event_type]``.
        ``event_date`` must be a trading session present in ``prices.index`` for
        the event to be used. Broadcast macro events (``ticker`` is None / NaN,
        see :func:`events_macro`) are skipped here -- the caller is expected to
        subsample them to concrete tickers (or use the benchmark-only AR) per the
        broadcast contract.
    k_before, k_after : int
        Number of trading sessions before / after the event session to include.
        offset 0 is the event session; the window spans ``[-k_before, +k_after]``.
    benchmark : str
        Only ``"cross_section"`` is implemented: the equal-weight mean daily
        return across all tickers per date.

    Returns
    -------
    (summary, per_event) : tuple[pd.DataFrame, pd.DataFrame]
        ``summary`` columns: ``[event_type, offset, n_events, car, car_se,
        car_ci_lo, car_ci_hi]`` -- one row per (event_type, offset); ``car_ci_*``
        are ``car +/- 1.96 * car_se``. ``per_event`` columns: ``[event_type,
        event_id, ticker, event_date, offset, ar]`` -- the raw abnormal return
        per event per offset (``event_id`` is the row index in ``events``).

    Notes
    -----
    Events whose full window does not fit inside ``prices`` (or whose AR series
    contains any NaN, e.g. a missing return) are dropped so every surviving
    event contributes to every offset and ``car`` / ``car_se`` stay well-defined.
    """
    if benchmark != "cross_section":
        raise NotImplementedError(
            f"benchmark={benchmark!r} is not implemented; only 'cross_section'."
        )

    prices = prices.sort_index()
    returns = prices.pct_change()
    bench = returns.mean(axis=1)  # equal-weight cross-section daily return per date
    bench_vals = bench.to_numpy()
    n_dates = len(prices.index)
    tickers_in_panel = set(returns.columns)
    position = {pd.Timestamp(d): i for i, d in enumerate(prices.index)}
    offsets = np.arange(-k_before, k_after + 1)

    # event_id (row label in `events`) -> (event_type, AR ndarray over offsets)
    series: dict[object, tuple[str, np.ndarray]] = {}
    order: list[object] = []
    per_event_rows: list[dict] = []

    for event_id, ev in events.iterrows():
        ticker = ev["ticker"]
        if pd.isna(ticker) or ticker not in tickers_in_panel:
            continue  # broadcast macro event (ticker=None) -- caller must subsample
        event_date = pd.Timestamp(ev["event_date"])
        if event_date not in position:
            continue
        p = position[event_date]
        lo, hi = p - k_before, p + k_after
        if lo < 0 or hi >= n_dates:
            continue  # full window must fit inside the panel
        ar = returns[ticker].to_numpy()[lo : hi + 1] - bench_vals[lo : hi + 1]
        if np.isnan(ar).any():
            continue  # keep car / car_se well-defined across events

        event_type = str(ev["event_type"])
        series[event_id] = (event_type, ar)
        order.append(event_id)
        for off, val in zip(offsets, ar, strict=True):
            per_event_rows.append(
                {
                    "event_type": event_type,
                    "event_id": event_id,
                    "ticker": ticker,
                    "event_date": event_date,
                    "offset": int(off),
                    "ar": float(val),
                }
            )

    per_event = pd.DataFrame(
        per_event_rows,
        columns=["event_type", "event_id", "ticker", "event_date", "offset", "ar"],
    )

    by_type: dict[str, list[object]] = {}
    for event_id in order:
        event_type = series[event_id][0]
        by_type.setdefault(event_type, []).append(event_id)

    summary_rows: list[dict] = []
    for event_type, event_ids in by_type.items():
        cum = np.vstack([series[eid][1] for eid in event_ids]).cumsum(axis=1)
        n_events = cum.shape[0]
        car = cum.mean(axis=0)
        if n_events > 1:
            se = cum.std(axis=0, ddof=1) / np.sqrt(n_events)
        else:
            se = np.full(cum.shape[1], np.nan)
        for off, c, s in zip(offsets, car, se, strict=True):
            summary_rows.append(
                {
                    "event_type": event_type,
                    "offset": int(off),
                    "n_events": n_events,
                    "car": float(c),
                    "car_se": float(s),
                    "car_ci_lo": float(c - Z_95 * s),
                    "car_ci_hi": float(c + Z_95 * s),
                }
            )

    summary = pd.DataFrame(
        summary_rows,
        columns=[
            "event_type",
            "offset",
            "n_events",
            "car",
            "car_se",
            "car_ci_lo",
            "car_ci_hi",
        ],
    )
    return summary, per_event


def events_13d(events_parquet: str | Path) -> pd.DataFrame:
    """Build a 13D event frame from the cached Phase D 13D filings parquet.

    Reads ``data/cache/phase_d_13d_events.parquet`` (the dashboard passes that
    path) and returns ``[ticker, event_date, event_type]`` where ``event_date``
    is the filing date and ``event_type`` is ``"13D"``. Both initial ``SC 13D``
    and amendment ``SC 13D/A`` rows are kept (a re-disclosure is itself an event);
    dedup / amendment filtering is left to the caller.
    """
    df = pd.read_parquet(events_parquet)
    out = df[["ticker", "filing_date"]].rename(columns={"filing_date": "event_date"})
    out["event_date"] = pd.to_datetime(out["event_date"])
    out["event_type"] = "13D"
    return out[["ticker", "event_date", "event_type"]]


def events_earnings(fund_parquet: str | Path) -> pd.DataFrame:
    """Build an earnings event frame from the cached Phase B fundamentals parquet.

    Reads ``data/cache/phase_b_fundamentals.parquet`` (passed by the dashboard),
    keeps rows whose ``form`` is in ``{10-K, 10-Q}``, takes distinct
    ``(ticker, filed)`` (a single filing carries many metric rows), and returns
    ``[ticker, event_date, event_type]`` with ``event_type`` = ``"earnings"`` and
    ``event_date`` = the filed date.
    """
    df = pd.read_parquet(fund_parquet)
    df = df[df["form"].isin(["10-K", "10-Q"])]
    out = (
        df[["ticker", "filed"]]
        .drop_duplicates()
        .rename(columns={"filed": "event_date"})
    )
    out["event_date"] = pd.to_datetime(out["event_date"])
    out["event_type"] = "earnings"
    return out[["ticker", "event_date", "event_type"]]


def events_macro(alfred_dir: str | Path, series: str) -> pd.DataFrame:
    """Build a broadcast macro event frame from a cached ALFRED vintage JSON.

    Reads ``<alfred_dir>/alfred_{series}.json`` (e.g. ``CPIAUCSL`` / ``PAYEMS``)
    and returns the *first print* per reference month: for each distinct ref
    ``date`` it takes the vintage with the minimum ``realtime_start`` (the
    earliest publication date = first print). Returns ``[ticker, event_date,
    event_type]`` where ``event_date`` is that first-print ``realtime_start``,
    ``event_type`` is ``"CPI"`` for ``CPIAUCSL`` / ``"NFP"`` for ``PAYEMS`` (the
    series id upper-cased otherwise), and ``ticker`` is None -- a broadcast event
    that applies to the whole cross-section. Per the broadcast contract the
    caller subsamples it to concrete tickers (or uses the benchmark-only AR)
    before feeding :func:`cumulative_abnormal_return`.
    """
    path = Path(alfred_dir) / f"alfred_{series}.json"
    obs = json.loads(path.read_text())["observations"]
    df = pd.DataFrame(obs)
    df["date"] = pd.to_datetime(df["date"])
    df["realtime_start"] = pd.to_datetime(df["realtime_start"])

    first_print_idx = df.groupby("date")["realtime_start"].idxmin()
    first_print = df.loc[first_print_idx].sort_values("date")

    out = pd.DataFrame(
        {
            "ticker": [None] * len(first_print),
            "event_date": first_print["realtime_start"].to_numpy(),
            "event_type": _MACRO_EVENT_TYPE.get(series, series.upper()),
        }
    )
    return out[["ticker", "event_date", "event_type"]]
