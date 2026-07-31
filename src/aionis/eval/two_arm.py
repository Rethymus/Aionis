"""Phase B two-arm cross-fit runner (arm_state=filed vs arm_base=period-end+lag).

Builds arms on the SAME prices / universe / features, masks each to PIT
constituents, computes the folds ONCE (PurgedGroupKFold, group= month) and applies
the SAME folds + frozen LightGBM. The rank-IC differential then isolates
fundamental-timing, because every other lever (prices, universe, features, folds,
learner) is shared between arms.

``run_arm_oos`` + ``compute_shared_folds`` are exposed so control gates
(``eval.phase_b_controls``) can run arm_state against a PERTURBED fundamentals frame
while arm_base retains the REAL one — both reusing the shared folds (critic HIGH-2).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from aionis.eval.cv import CVSplit, purged_group_kfold_splits
from aionis.eval.learner import LightGBMFrozen
from aionis.features.selection_panel import build_selection_panel
from aionis.ingest.universe import mask_panel_to_pit

_ARMS = {"arm_state": "filed", "arm_base": "end_lag"}


def _clean_panel(
    prices: pd.DataFrame, fundamentals_long: pd.DataFrame,
    membership: pd.DataFrame, horizon: int, align_on: str,
    *,
    macro: pd.DataFrame | None = None,
    extra_features: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build -> PIT-mask -> drop NaN-label -> canonical (date, ticker) order."""
    p = build_selection_panel(
        prices, fundamentals_long, horizon, align_on=align_on,
        macro=macro, extra_features=extra_features,
    )
    p = mask_panel_to_pit(p, membership)
    return (
        p.dropna(subset=["y_fwd_ret"])
        .sort_values(["date", "ticker"]).reset_index(drop=True)
    )


def _folds_from_panel(
    panel: pd.DataFrame, horizon: int, n_splits: int, embargo_sessions: int,
) -> list[CVSplit]:
    """Folds shared by every arm. eval_date = the session h positions after date
    (label resolution); embargo = the calendar span of ``embargo_sessions`` sessions
    (the standard trading-day approximation); group = calendar month."""
    dates_sorted = pd.DatetimeIndex(sorted(panel["date"].unique()))
    n_sess = len(dates_sorted)
    pos = {d: i for i, d in enumerate(dates_sorted)}
    emb = min(max(embargo_sessions, 0), n_sess - 1)
    embargo_td = pd.Timedelta(dates_sorted[emb] - dates_sorted[0]) if emb > 0 else pd.Timedelta(0)
    eval_dates = panel["date"].map(
        lambda d: dates_sorted[min(pos[d] + horizon, n_sess - 1)]
    )
    groups = panel["date"].dt.to_period("M").astype(str)
    return purged_group_kfold_splits(
        panel["date"], eval_dates, groups, n_splits=n_splits, embargo=embargo_td,
    )


def compute_shared_folds(
    prices: pd.DataFrame, membership: pd.DataFrame, horizon: int,
    n_splits: int = 5, embargo_sessions: int = 21,
) -> tuple[list[CVSplit], pd.DataFrame]:
    """The folds + canonical ``(date, ticker)`` row layout shared by every arm.

    Computed from an empty-fundamentals panel: rows come from prices + universe
    only (fund values never add/drop rows), so the layout is identical for any arm
    and any fund perturbation. Returns ``(folds, ref_layout)`` for ``run_arm_oos``."""
    ref = _clean_panel(prices, pd.DataFrame(), membership, horizon, "filed")
    folds = _folds_from_panel(ref, horizon, n_splits, embargo_sessions)
    return folds, ref[["date", "ticker"]].reset_index(drop=True)


def run_arm_oos(
    prices: pd.DataFrame, fundamentals_long: pd.DataFrame, membership: pd.DataFrame,
    horizon: int, feature_cols: list[str], align_on: str,
    folds: list[CVSplit], ref_layout: pd.DataFrame, params: dict | None = None,
    *,
    macro: pd.DataFrame | None = None,
    extra_features: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Run one arm against pre-computed shared folds -> cross-fitted/OOF panel
    ``[date, ticker, score, y_fwd_ret]``.

    Asserts the arm's ``(date, ticker)`` layout matches ``ref_layout`` so the fold
    indices align arm-to-arm. This is what lets a control gate run arm_state on a
    perturbed frame while arm_base uses the real one, both on the same folds.

    ``macro`` / ``extra_features`` (Phase C) thread straight into
    :func:`build_selection_panel`: ``macro`` is a date-indexed frame broadcast across
    tickers (macro/VIX surprise); ``extra_features`` is a long ``[date, ticker, ...]``
    frame for per-(ticker, date) features (earnings surprise). Both are left joins on
    the panel's existing rows, so they add columns only — the ``(date, ticker)``
    layout is identical to any other arm built on the same prices/universe, and the
    layout assertion still holds (this is why folds are computed from an
    empty-fundamentals panel in :func:`compute_shared_folds`)."""
    p = _clean_panel(
        prices, fundamentals_long, membership, horizon, align_on,
        macro=macro, extra_features=extra_features,
    )
    layout = p[["date", "ticker"]].reset_index(drop=True)
    assert layout.equals(ref_layout), (
        f"align_on={align_on} row layout diverges from ref (PIT mask / y must match)"
    )
    scores = pd.Series(np.nan, index=p.index, dtype=float, name="score")
    mdl = LightGBMFrozen(params)
    for sp in folds:
        tr, te = p.iloc[sp.train_idx], p.iloc[sp.test_idx]
        if len(tr) == 0 or len(te) == 0:
            continue
        scores.iloc[sp.test_idx] = mdl.fit_predict(
            tr, te, feature_cols, "y_fwd_ret"
        ).to_numpy()
    oos = p[["date", "ticker", "y_fwd_ret"]].assign(score=scores.to_numpy())
    return oos.dropna(subset=["score"]).reset_index(drop=True)


def run_two_arm_oos(
    prices: pd.DataFrame,
    fundamentals_long: pd.DataFrame,
    membership: pd.DataFrame,
    horizon: int,
    feature_cols: list[str],
    n_splits: int = 5,
    embargo_sessions: int = 21,
    params: dict | None = None,
) -> dict[str, pd.DataFrame]:
    """Run both Phase B arms (shared fundamentals) -> ``{arm: OOF panel}``.

    The two arms share prices / universe / features / folds / learner; ONLY the
    fundamental-timing (``align_on``) differs. OOF rows are the union of every
    fold's test block. Feed each arm's panel to ``eval.rank_ic`` for the headline."""
    folds, ref = compute_shared_folds(prices, membership, horizon, n_splits, embargo_sessions)
    return {
        a: run_arm_oos(prices, fundamentals_long, membership, horizon, feature_cols,
                       al, folds, ref, params)
        for a, al in _ARMS.items()
    }
