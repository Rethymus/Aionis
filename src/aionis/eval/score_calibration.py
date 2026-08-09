"""Score → P(forward_return > 0) calibration via Platt scaling (default) or isotonic.

Display-only utility: produces honest per-region probabilities of positive
forward return conditional on the OOS model score. Calibration is fit on
historical (score, realized fwd_return) pairs; the latest unread month is
predicted out-of-sample.

Why Platt (sigmoid) is the default, not isotonic:
  Isotonic regression is non-parametric and **overfits noise** — on a null
  model (rank-IC ≈ 0) it produces a wandering curve and a deceptively wide
  prob range, manufacturing discrimination that is not there. Platt scaling
  (2-parameter logistic sigmoid) is constrained, so on a null model it
  collapses to a near-flat curve tightly bracketing ``base_rate`` — the
  honest signal that "the model cannot tell up from down". Isotonic remains
  available for users who want the flexible curve and accept the overfit.

Anti-leakage contract (this is the load-bearing part):
  - Calibration fit ONLY uses realized pairs — i.e. (date, ticker) rows whose
    ``forward_return_h`` is finite (already observed). The latest month, whose
    forward return is by definition unrealized, is naturally excluded by the
    NaN drop and is only *predicted*, never *fit on*.
  - Both Platt and isotonic are monotonic by construction → calibrated
    ``prob_up`` preserves score rank (does not shuffle picks). Neither can
    manufacture discrimination the score does not have.
  - Walk-forward refit is available as an opt-in DISPLAY variant
    (``calibrate_walk_forward``): each realized month is predicted by a map
    refit on strictly-prior realized pairs, producing a per-month OOS ECE series
    + a pooled OOS reliability diagram. The default ``calibrate_latest_month``
    remains a single fit on all realized history (``walk_forward = False``).
    Neither is a research estimator.
  - This module writes NO ledger / frozen surface / E3 outcome — it is a pure
    display transform, analogous to ``ff5_residual``. The research verdict
    (combined rank-IC = −0.0088, null) is unaffected.

The honest signal lives in ``CalibrationMeta``:
  - ``base_rate`` ≈ 0.50–0.55 is the empirical "did the market go up" rate.
  - ``prob_min`` / ``prob_max`` bracket the calibrated range. With Platt on a
    null model this range is tight around ``base_rate`` (e.g. 0.47–0.56), the
    visible signature of "no discrimination".
  - ``ece`` (Expected Calibration Error) → 0 means well-calibrated; a
    well-calibrated null is still a null.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss

Region = Literal["us", "cn"]
Method = Literal["platt", "isotonic"]

_DEFAULT_METHOD: Method = "platt"
_MIN_PAIRS = 30  # isotonic is non-parametric; need enough rows to be stable


@dataclass(frozen=True)
class CalibrationMeta:
    """Summary statistics for a fitted calibration curve."""

    region: str
    n_pairs: int
    base_rate: float  # mean(realized_up): empirical P(fwd_return > 0)
    ece: float  # Expected Calibration Error (lower = better calibrated)
    brier: float  # Brier score (lower = better)
    score_min: float
    score_max: float
    prob_min: float  # range of calibrated probs — tight around base_rate ⇒ null
    prob_max: float
    method: str = _DEFAULT_METHOD
    walk_forward: bool = False  # disclosed; display utility only


@dataclass
class CalibratedRegion:
    """A fitted calibration curve + its meta. ``predict_proba`` is monotonic in score.

    Holds either a sklearn IsotonicRegression (method="isotonic") or
    LogisticRegression (method="platt") under ``_model``.
    """

    meta: CalibrationMeta
    _model: Any = field(repr=False, default=None)

    def predict_proba(self, scores: np.ndarray | pd.Series | float) -> np.ndarray | float:
        """Map scores → P(forward_return > 0). Monotonic, clipped to [0.01, 0.99]."""
        scalar = np.isscalar(scores)
        arr = np.atleast_1d(np.asarray(scores, dtype=float))
        if isinstance(self._model, IsotonicRegression):
            out = self._model.predict(arr)
        else:  # LogisticRegression (Platt)
            out = self._model.predict_proba(arr.reshape(-1, 1))[:, 1]
        out = np.clip(out, 0.01, 0.99)
        return float(out[0]) if scalar else out


def _ece(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
    """Expected Calibration Error: Σ_bin (|accuracy − confidence| × weight)."""
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = len(y_true)
    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        mask = (y_prob >= lo) & (y_prob < hi if i < n_bins - 1 else y_prob <= hi)
        if mask.sum() == 0:
            continue
        acc = y_true[mask].mean()
        conf = y_prob[mask].mean()
        ece += (mask.sum() / n) * abs(acc - conf)
    return float(ece)


def fit_region(
    scores: np.ndarray | pd.Series,
    realized_up: np.ndarray | pd.Series,
    region: str,
    method: Method = _DEFAULT_METHOD,
) -> CalibratedRegion:
    """Fit calibration: score → P(realized_up = 1).

    scores:       1-D OOS model scores.
    realized_up:  1-D boolean/int (1 ⇔ forward_return > 0).
    method:       "platt" (2-param logistic sigmoid; default — honest on null)
                  or "isotonic" (non-parametric; overfits noise but more flexible).
    """
    scores = np.asarray(scores, dtype=float)
    realized_up = np.asarray(realized_up).astype(int)
    finite = np.isfinite(scores) & np.isfinite(realized_up)
    scores, realized_up = scores[finite], realized_up[finite]
    if len(scores) < _MIN_PAIRS:
        raise ValueError(
            f"Insufficient calibration pairs for {region}: {len(scores)} (need ≥{_MIN_PAIRS})."
        )
    if method == "isotonic":
        model = IsotonicRegression(out_of_bounds="clip", y_min=0.01, y_max=0.99)
        model.fit(scores, realized_up)
        prob = model.predict(scores)
    elif method == "platt":
        # C=1e6 ⇒ effectively no regularization (classic Platt); solver robust to small sets.
        model = LogisticRegression(C=1e6, solver="lbfgs")
        model.fit(scores.reshape(-1, 1), realized_up)
        prob = model.predict_proba(scores.reshape(-1, 1))[:, 1]
    else:  # pragma: no cover - exhaustive literal
        raise ValueError(f"Unknown method: {method!r} (expected 'platt' or 'isotonic')")
    return CalibratedRegion(
        meta=CalibrationMeta(
            region=region,
            n_pairs=int(len(scores)),
            base_rate=float(realized_up.mean()),
            ece=_ece(realized_up, prob),
            brier=float(brier_score_loss(realized_up, prob)),
            score_min=float(scores.min()),
            score_max=float(scores.max()),
            prob_min=float(prob.min()),
            prob_max=float(prob.max()),
            method=method,
        ),
        _model=model,
    )


def build_pair_frame(
    oos_scores: pd.DataFrame,
    panel: pd.DataFrame,
    region: str,
) -> pd.DataFrame:
    """Join OOS scores to realized forward returns on (ticker, date).

    oos_scores columns: [date, ticker, region, score]
    panel columns:      [date, ticker, forward_return_h, ...]
    Returns:            [date, ticker, score, forward_return_h, realized_up]
                        rows with NaN forward_return_h are KEPT (they indicate
                        the unrealized latest month; fit_region drops them via
                        np.isfinite, latest prediction uses them via the OOS df).
    Raises ValueError if panel is empty or missing required columns, so callers
    can decide whether to skip the region (see ``calibrate_latest_month``).
    """
    required = {"date", "ticker", "forward_return_h"}
    missing = required - set(panel.columns)
    if missing:
        raise ValueError(f"panel missing required columns for {region}: {missing}")
    if panel.empty:
        raise ValueError(f"panel empty for {region}; skip this region")
    oos = oos_scores[oos_scores["region"] == region][["date", "ticker", "score"]].copy()
    oos["date"] = pd.to_datetime(oos["date"])
    panel = panel[["date", "ticker", "forward_return_h"]].copy()
    panel["date"] = pd.to_datetime(panel["date"])
    merged = oos.merge(panel, on=["date", "ticker"], how="inner")
    merged["realized_up"] = (merged["forward_return_h"] > 0).astype("Int64")
    return merged


def calibrate_latest_month(
    oos_scores: pd.DataFrame,
    us_panel: pd.DataFrame,
    cn_panel: pd.DataFrame,
    latest_date: Any | None = None,
    method: Method = _DEFAULT_METHOD,
) -> dict[str, Any]:
    """Fit per-region calibration on realized history; predict latest unread month.

    Returns ``{latest_date, method, walk_forward, regions: {region: {meta, latest}}}``.
    The latest month is excluded from the fit (its forward_return_h is NaN by
    construction) — see the module docstring's anti-leakage contract. Regions
    with empty panels or <30 realized pairs are silently skipped.
    """
    oos = oos_scores.copy()
    oos["date"] = pd.to_datetime(oos["date"])
    global_latest = pd.Timestamp(latest_date) if latest_date is not None else oos["date"].max()

    out: dict[str, Any] = {
        "latest_date": str(global_latest.date()),
        "method": method,
        "walk_forward": False,
        "regions": {},
    }
    for region, panel in (("us", us_panel), ("cn", cn_panel)):
        # Each region's "latest unread month" is its OWN max (US and CN panels
        # may end on different dates — the panels are PIT-aligned per region).
        region_oos = oos[oos["region"] == region]
        if region_oos.empty:
            continue
        region_latest = region_oos["date"].max()
        # If caller forced a global latest_date, do not overshoot it.
        if latest_date is not None:
            region_latest = min(region_latest, global_latest)
        try:
            pairs = build_pair_frame(oos, panel, region)
        except ValueError:
            continue  # empty panel / missing cols — skip region
        history = pairs.dropna(subset=["forward_return_h"])
        history = history[history["date"] < region_latest]
        if len(history) < _MIN_PAIRS:
            continue
        cr = fit_region(
            history["score"].to_numpy(),
            history["realized_up"].dropna().to_numpy(),
            region,
            method=method,
        )
        latest = region_oos[region_oos["date"] == region_latest][["ticker", "score"]].copy()
        if len(latest) == 0:
            continue
        latest["prob_up"] = cr.predict_proba(latest["score"].to_numpy()).round(4)
        latest["score"] = latest["score"].round(3)
        out["regions"][region] = {
            "meta": cr.meta,
            "latest_date": str(region_latest.date()),
            "latest": latest.reset_index(drop=True),
        }
    return out


def _reliability_bins(
    y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10
) -> tuple[list[dict[str, Any]], float]:
    """Bin predicted probs → ([{bin_lo, bin_hi, pred_mean, emp_freq, n}], ECE).

    Per-bin reliability table (mean predicted P vs empirical frequency) plus the
    scalar Expected Calibration Error. Both inputs must be finite, aligned, and
    non-empty. ECE is computed from the same binned counts as the table (single
    pass, identical definition to ``_ece``).
    """
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    rows: list[dict[str, Any]] = []
    ece = 0.0
    n = len(y_true)
    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        mask = (y_prob >= lo) & (y_prob < hi if i < n_bins - 1 else y_prob <= hi)
        cnt = int(mask.sum())
        if cnt == 0:
            rows.append(
                {
                    "bin_lo": round(float(lo), 3),
                    "bin_hi": round(float(hi), 3),
                    "pred_mean": None,
                    "emp_freq": None,
                    "n": 0,
                }
            )
            continue
        acc = float(y_true[mask].mean())
        conf = float(y_prob[mask].mean())
        ece += (cnt / n) * abs(acc - conf)
        rows.append(
            {
                "bin_lo": round(float(lo), 3),
                "bin_hi": round(float(hi), 3),
                "pred_mean": round(conf, 4),
                "emp_freq": round(acc, 4),
                "n": cnt,
            }
        )
    return rows, float(ece)


def calibrate_walk_forward(
    oos_scores: pd.DataFrame,
    us_panel: pd.DataFrame,
    cn_panel: pd.DataFrame,
    method: Method = _DEFAULT_METHOD,
    min_train_months: int = 12,
    n_bins: int = 10,
) -> dict[str, Any]:
    """Per-region walk-forward calibration reliability (DISPLAY, leakage-safe).

    For each realized OOS month T, refit the Platt/isotonic calibration on all
    realized (score, realized_up) pairs STRICTLY before T, then predict T's
    tickers' P(up). T's own realized outcome then scores that prediction
    (a legitimate backward audit — T is realized). Produces a per-month OOS-ECE
    series + a pooled OOS reliability diagram. ``walk_forward = True`` disclosed.

    Anti-leakage contract (mirrors ``calibrate_latest_month`` — the load-bearing part):
      - Month T's fit uses ONLY pairs with date < T. T is only predicted, never fit.
      - Only the 2-param Platt sigmoid (or isotonic) DISPLAY MAP is refit; the
        frozen LightGBM learner, its hyperparameters, and its features are NEVER
        touched. A monotonic map cannot manufacture discrimination the score lacks.
      - This module writes NO ledger / frozen surface / E3 outcome / research
        estimator. It is the leakage-safe form of "use the latest data to
        self-correct the calibration" — NOT a path to positive rank-IC (research
        verdict ledger #49: combined rank-IC −0.0088, NULL).

    Returns ``{method, walk_forward, min_train_months, regions: {region:
    {n_months, series, pooled_ece, pooled_reliability}}}``. Regions with fewer
    than ``min_train_months`` realized months (or <``_MIN_PAIRS`` training pairs)
    are silently omitted.
    """
    oos = oos_scores.copy()
    oos["date"] = pd.to_datetime(oos["date"])
    out: dict[str, Any] = {
        "method": method,
        "walk_forward": True,
        "min_train_months": min_train_months,
        "regions": {},
    }
    for region, panel in (("us", us_panel), ("cn", cn_panel)):
        region_oos = oos[oos["region"] == region]
        if region_oos.empty:
            continue
        try:
            pairs = build_pair_frame(oos, panel, region)
        except ValueError:
            continue  # empty panel / missing cols — skip region
        realized = pairs.dropna(subset=["forward_return_h"]).sort_values("date").copy()
        if realized.empty:
            continue
        realized["month"] = realized["date"].dt.to_period("M")
        months = sorted(realized["month"].unique())
        if len(months) <= min_train_months:
            continue  # not enough realized history to walk forward
        series: list[dict[str, Any]] = []
        pooled_true: list[int] = []
        pooled_prob: list[float] = []
        for i in range(min_train_months, len(months)):
            target = months[i]
            train = realized[realized["month"] < target]
            if len(train) < _MIN_PAIRS:
                continue
            tgt = realized[realized["month"] == target]
            tgt = tgt[np.isfinite(tgt["score"])]
            if len(tgt) < 10:  # need a real cross-section to score the month
                continue
            cr = fit_region(
                train["score"].to_numpy(),
                train["realized_up"].dropna().to_numpy(),
                region,
                method=method,
            )
            preds = cr.predict_proba(tgt["score"].to_numpy())
            y_true = tgt["realized_up"].dropna().to_numpy().astype(int)
            _, ece_t = _reliability_bins(y_true, preds, n_bins=n_bins)
            series.append(
                {
                    "month": str(target),
                    "n_train_pairs": int(len(train)),
                    "n_pred": int(len(tgt)),
                    "ece_oos": round(ece_t, 4),
                    "base_rate": round(float(y_true.mean()), 4),
                    "prob_min": round(float(preds.min()), 4),
                    "prob_max": round(float(preds.max()), 4),
                }
            )
            pooled_true.extend(y_true.tolist())
            pooled_prob.extend(preds.tolist())
        if not series:
            continue
        bins, pooled_ece = _reliability_bins(
            np.asarray(pooled_true), np.asarray(pooled_prob), n_bins=n_bins
        )
        out["regions"][region] = {
            "n_months": len(series),
            "series": series,
            "pooled_ece": round(pooled_ece, 4),
            "pooled_reliability": bins,
        }
    return out


def meta_to_jsonable(meta: CalibrationMeta) -> dict[str, Any]:
    """JSON-safe view of CalibrationMeta (dataclasses are not json.dumps-able)."""
    return {
        "region": meta.region,
        "n_pairs": meta.n_pairs,
        "base_rate": round(meta.base_rate, 4),
        "ece": round(meta.ece, 4),
        "brier": round(meta.brier, 4),
        "score_min": round(meta.score_min, 3),
        "score_max": round(meta.score_max, 3),
        "prob_min": round(meta.prob_min, 4),
        "prob_max": round(meta.prob_max, 4),
        "method": meta.method,
        "walk_forward": meta.walk_forward,
    }
