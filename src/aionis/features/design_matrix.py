"""Assemble the leakage-safe design matrix for the experiment.

Produces, per (event, symbol) row:
  * X       — feature vector (market-state, optionally + event-vector in Phase 3)
  * y       — realized h-session return = close[label_end]/close[label_start] - 1
  * prediction_time / evaluation_time — for purged CV
  * group   — event-date, for cluster-robust inference
All features come from ``feature_fn(prices, t_info_date, symbol)``, which by
contract reads only ``prices.loc[:t_info_date]``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from aionis.features.alignment import align_events
from aionis.features.market_state import market_state_features


@dataclass(frozen=True)
class DesignMatrix:
    X: pd.DataFrame
    y: pd.Series
    prediction_times: pd.Series
    evaluation_times: pd.Series
    groups: pd.Series
    metadata: pd.DataFrame  # event_id, event_type, symbol, t_info_date, label_*

    def __len__(self) -> int:
        return len(self.X)

    @property
    def n_events(self) -> int:
        return self.metadata["event_id"].nunique()


def build_design_matrix(
    events: pd.DataFrame,
    prices: pd.DataFrame,
    sessions: pd.DatetimeIndex,
    symbols: list[str],
    horizon: int,
    feature_fn=market_state_features,
    extra_features: pd.DataFrame | None = None,
) -> DesignMatrix:
    """Build X/y + CV/group arrays from events, prices, and a feature function.

    ``extra_features`` (Phase 3) is an optional DataFrame indexed by event_id
    whose columns are appended to X (e.g. the ERL event vector). Rows whose X or
    y contain non-finite values are dropped so downstream learners see clean data.
    """
    aligned = align_events(events, sessions, horizon)
    if aligned.empty:
        raise ValueError("no events aligned onto the session grid")

    symbols = list(symbols)
    X_rows: list[dict] = []
    y_vals: list[float] = []
    meta_rows: list[dict] = []
    for ev in aligned.itertuples(index=False):
        ls = _safe_loc(prices, ev.label_start_date)
        le = _safe_loc(prices, ev.label_end_date)
        for sym in symbols:
            feats = feature_fn(prices, ev.t_info_date, sym)
            if not feats:
                continue
            ls_s, le_s = ls.get(sym, np.nan), le.get(sym, np.nan)
            if not np.isfinite(ls_s) or not np.isfinite(le_s) or ls_s <= 0:
                continue
            target = float(le_s / ls_s - 1.0)
            if extra_features is not None and ev.event_id in extra_features.index:
                feats = {**feats, **extra_features.loc[ev.event_id].to_dict()}
            X_rows.append(feats)
            y_vals.append(target)
            meta_rows.append(
                {
                    "event_id": ev.event_id,
                    "event_type": ev.event_type,
                    "symbol": sym,
                    "event_date": ev.event_date,
                    "t_info_date": ev.t_info_date,
                    "label_start_date": ev.label_start_date,
                    "label_end_date": ev.label_end_date,
                    "prediction_time": ev.prediction_time,
                    "evaluation_time": ev.evaluation_time,
                    "group": ev.event_date,
                }
            )

    if not X_rows:
        raise ValueError("no usable rows (insufficient history or missing prices)")

    X = pd.DataFrame(X_rows)
    meta = pd.DataFrame(meta_rows)
    y = pd.Series(y_vals, name="target", dtype=float)
    keep = X.replace([np.inf, -np.inf], np.nan).notna().all(axis=1) & y.notna().values
    X, y, meta = (
        X[keep].reset_index(drop=True),
        y[keep].reset_index(drop=True),
        meta[keep].reset_index(drop=True),
    )

    return DesignMatrix(
        X=X,
        y=y,
        prediction_times=meta["prediction_time"].reset_index(drop=True),
        evaluation_times=meta["evaluation_time"].reset_index(drop=True),
        groups=meta["group"].reset_index(drop=True),
        metadata=meta,
    )


def _safe_loc(prices: pd.DataFrame, date: pd.Timestamp) -> pd.Series:
    """Return prices.loc[date] as a Series keyed by symbol, or empty if missing."""
    date = pd.Timestamp(date).tz_localize(None).normalize()
    if date in prices.index:
        return prices.loc[date]
    return pd.Series(dtype=float)
