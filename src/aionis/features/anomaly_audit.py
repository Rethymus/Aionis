"""Price-panel anomaly audit — market-driver framework reliability mechanism ⑥.

A price panel can carry four reliability defects *silently*: nonpositive prints,
interior gaps (a hole inside a ticker's traded span), discontinuities (split-
unadjusted or erroneous jumps), and stale runs (a halted / delisted name feeding
a flat line). None of these is a look-ahead leak, but each corrupts the label
(forward returns) and the cross-section (a garbage close → garbage mktcap /
ratios → garbage rank-IC). This module flags them on the wide ``date x ticker``
adjusted-close frame the selection pipeline already builds, so a run can audit
its inputs before trusting the IC.

Pure detection: it never imputes, drops, or forward-fills (the pipeline's PIT
discipline owns row handling). It only *reports* — the caller decides whether a
flagged ticker's window is acceptable, re-fetched, or masked.

Permissive licenses only (pandas / numpy, BSD).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# |session return| above this is treated as a discontinuity (split-unadjusted or
# an erroneous print). 0.50 = a 50% single-session move, well beyond any normal
# large-cap daily return; tighten for smaller names.
DEFAULT_JUMP_THRESHOLD = 0.50

# A run of >= this many consecutive IDENTICAL closes = a flat line (halted /
# delisted feeding stale data). 10 sessions ≈ two trading weeks unchanged.
DEFAULT_STALE_RUN = 10

_ANOMALY_KINDS = ("nonpositive", "interior_gap", "jump", "stale")


def price_anomalies(
    prices: pd.DataFrame,
    *,
    jump_threshold: float = DEFAULT_JUMP_THRESHOLD,
    stale_run: int = DEFAULT_STALE_RUN,
) -> pd.DataFrame:
    """Flag the four price-panel reliability defects, per ticker.

    Returns a long frame ``[ticker, anomaly, count, detail]`` with one row per
    ``(ticker, anomaly)`` that fires (a clean ticker appears in no row). Kinds:

    * ``nonpositive`` — any close ``<= 0`` (``count`` = number of such prints;
      ``detail`` = the first offending date).
    * ``interior_gap`` — NaN strictly between the first and last valid print
      (``count`` = number of interior NaN). Leading / trailing NaN (a name not
      yet listed or already delisted) is coverage, not a defect, and is never
      flagged.
    * ``jump`` — ``|pct_change| > jump_threshold`` (``count`` = number of such
      sessions; ``detail`` = the largest finite ``|return|``). A 0 → price move
      is ``+inf`` and counts as a discontinuity.
    * ``stale`` — a run of ``>= stale_run`` consecutive identical closes
      (``count`` = sessions inside such runs; ``detail`` = the longest run).

    Empty / all-NaN input yields an empty frame (never raises).
    """
    if prices is None or prices.empty:
        return pd.DataFrame(columns=["ticker", "anomaly", "count", "detail"])

    rows: list[dict] = []
    for ticker, s in prices.items():
        v = s.to_numpy(dtype=float)

        # --- nonpositive ---------------------------------------------------
        npos = (~np.isnan(v)) & (v <= 0.0)
        n_nonpos = int(npos.sum())
        if n_nonpos:
            first_bad = s.index[int(np.where(npos)[0][0])]
            rows.append({
                "ticker": ticker, "anomaly": "nonpositive", "count": n_nonpos,
                "detail": str(pd.Timestamp(first_bad).date()),
            })

        # --- interior gap (NaN strictly between first/last valid) -----------
        first = s.first_valid_index()
        last = s.last_valid_index()
        if first is not None and last is not None:
            n_gap = int(s.loc[first:last].isna().sum())
            if n_gap:
                rows.append({
                    "ticker": ticker, "anomaly": "interior_gap", "count": n_gap,
                    "detail": "",
                })

        # --- jump (|session return| > threshold) ----------------------------
        abs_ret = np.abs(s.pct_change().to_numpy(dtype=float))
        # NaN > threshold is False; inf > threshold is True (a 0 -> price jump).
        jump_mask = abs_ret > jump_threshold
        n_jump = int(jump_mask.sum())
        if n_jump:
            finite = abs_ret[np.isfinite(abs_ret)]
            max_abs = float(np.max(finite)) if finite.size else float("inf")
            rows.append({
                "ticker": ticker, "anomaly": "jump", "count": n_jump,
                "detail": f"max_abs_ret={max_abs:.2f}",
            })

        # --- stale (run of >= stale_run consecutive identical non-NaN closes)
        if len(v):
            diff = np.empty(len(v), dtype=bool)
            diff[0] = True
            diff[1:] = v[1:] != v[:-1]  # NaN != anything is True -> NaNs break runs
            run_id = np.cumsum(diff)
            notna = ~np.isnan(v)
            # non-NaN count per run id: a homogeneous non-NaN run yields its
            # length; a NaN run (every NaN is its own run) yields 0.
            run_lens = pd.Series(notna).groupby(run_id).sum()
            big = run_lens[run_lens >= stale_run]
            if len(big):
                rows.append({
                    "ticker": ticker, "anomaly": "stale", "count": int(big.sum()),
                    "detail": f"max_run={int(run_lens.max())}",
                })

    return pd.DataFrame(rows, columns=["ticker", "anomaly", "count", "detail"])


def anomaly_summary(anomalies: pd.DataFrame, n_tickers: int | None = None) -> dict:
    """Aggregate :func:`price_anomalies` output into counts for the run log / dashboard.

    * ``by_anomaly`` — each anomaly kind → number of DISTINCT tickers it affects.
    * ``n_flagged`` — tickers with >= 1 anomaly.
    * ``n_tickers`` — the audited universe size. Pass ``prices.shape[1]`` so the
      flagged share is meaningful; when omitted it defaults to ``n_flagged``
      (i.e. it assumes every audited ticker was flagged, which understates the
      clean share — pass the real count when you have it).
    """
    if anomalies is None or anomalies.empty:
        return {"n_tickers": int(n_tickers or 0), "n_flagged": 0, "by_anomaly": {}}
    by = (
        anomalies.drop_duplicates(["ticker", "anomaly"])
        .groupby("anomaly")["ticker"].nunique().to_dict()
    )
    n_flagged = int(anomalies["ticker"].nunique())
    return {
        "n_tickers": int(n_tickers) if n_tickers is not None else n_flagged,
        "n_flagged": n_flagged,
        "by_anomaly": {k: int(v) for k, v in by.items()},
    }
