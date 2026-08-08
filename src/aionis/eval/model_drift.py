"""Model-drift health monitor — leakage-safe display utility.

Detects when the frozen model's *recent* realized behavior diverges from its
*historical* realized behavior: a score-distribution shift (Population Stability
Index) + a rolling cross-sectional rank-IC comparison. This is the closest
leakage-safe analogue of "the model notices it is drifting" — it raises a
human-readable flag for attention; it never triggers a retrains.

Anti-leakage contract (mirrors ``score_calibration.py`` — the load-bearing part):
  - Every metric uses ONLY realized pairs: (date, ticker) rows whose
    ``forward_return_h`` is finite AND whose month is strictly before the latest
    unread month. The latest month is never consumed.
  - PSI compares the *historical* score distribution (reference) to the *recent*
    one (sample) — both fully realized. No future information is touched.
  - This module writes NO ledger / frozen surface / E3 outcome — pure display
    transform, analogous to ``score_calibration`` / ``ff5_residual``. The research
    verdict (combined rank-IC = −0.0088, null) is unaffected.

Why PSI + rank-IC (not a retrain trigger):
  - PSI (Population Stability Index) is the standard credit/risk drift metric:
    PSI<0.1 stable, 0.1–0.25 moderate, ≥0.25 significant. It answers "is the
    model seeing a different score distribution lately?"
  - Rolling rank-IC (recent mean vs full-sample mean) answers "has ranking skill
    degraded lately?" On a null model (IC≈0) this is noisy by design — PSI is the
    lead signal; IC is reported for context, never as an effect claim.

Honest-disclosure note: a "drift" flag is informational (display). It does NOT
imply the model should be retrained (rerun-to-significance is forbidden), and on
a null model a wide PSI band is often just the noise floor, not regime change.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from aionis.eval.score_calibration import build_pair_frame

Region = str  # "us" | "cn"

_MIN_HISTORY = 120  # realized pairs needed for a stable historical reference
_MIN_RECENT = 30  # realized pairs needed for a recent window
_RECENT_MONTHS_DEFAULT = 6  # last N realized months vs the rest
_PSI_BINS = 10
_EPS = 1e-6  # zero-count bin guard for PSI log


@dataclass(frozen=True)
class DriftMeta:
    """Per-region drift summary (all realized-only)."""

    region: str
    n_history: int  # realized pairs in the historical window
    n_recent: int  # realized pairs in the recent window
    recent_months: int  # window size used
    psi: float  # score-distribution shift (reference=hist, sample=recent)
    ic_full: float  # mean monthly cross-sectional rank-IC over all realized months
    ic_recent: float  # mean monthly rank-IC over the recent window
    base_rate_full: float  # P(fwd>0) over history
    base_rate_recent: float  # P(fwd>0) over recent
    regime: str  # "stable" | "moderate" | "significant" (from PSI)


def _psi(reference: pd.Series, sample: pd.Series, n_bins: int = _PSI_BINS) -> float:
    """Population Stability Index.

    Bin edges are the quantiles of the REFERENCE (historical) distribution; we
    then count the SAMPLE (recent) into the same bins. PSI = Σ (p_sample −
    p_ref) · ln(p_sample / p_ref). Returns 0.0 for degenerate (constant) inputs.
    """
    ref = reference.to_numpy(dtype=float)
    sam = sample.to_numpy(dtype=float)
    if ref.std() < _EPS or sam.std() < _EPS:
        return 0.0  # constant distribution → no meaningful shift
    edges = np.quantile(ref, np.linspace(0.0, 1.0, n_bins + 1))
    edges = np.unique(edges)  # collapse duplicate edges from ties
    if len(edges) <= 2:
        return 0.0
    # Bin counts (right-open except the last).
    ref_counts, _ = np.histogram(ref, bins=edges)
    sam_counts, _ = np.histogram(sam, bins=edges)
    ref_pct = ref_counts / max(ref_counts.sum(), 1)
    sam_pct = sam_counts / max(sam_counts.sum(), 1)
    ref_pct = ref_pct + _EPS  # avoid log(0); negligible bias
    sam_pct = sam_pct + _EPS
    return float(np.sum((sam_pct - ref_pct) * np.log(sam_pct / ref_pct)))


def _monthly_rank_ic(pairs: pd.DataFrame) -> float:
    """Mean monthly cross-sectional Spearman(score, forward_return_h).

    Standard quant rank-IC: per realized month, correlate score vs forward return
    across tickers; average. Returns 0.0 if no month has enough cross-section.
    """
    df = pairs.copy()
    df["month"] = df["date"].dt.to_period("M").astype(str)
    ics: list[float] = []
    for _, sub in df.groupby("month"):
        sub = sub.dropna(subset=["score", "forward_return_h"])
        if len(sub) < 10:  # need a real cross-section
            continue
        ic = sub["score"].corr(sub["forward_return_h"], method="spearman")
        if np.isfinite(ic):
            ics.append(float(ic))
    return float(np.mean(ics)) if ics else 0.0


def compute_drift(
    oos_scores: pd.DataFrame,
    panel: pd.DataFrame,
    region: str,
    recent_months: int = _RECENT_MONTHS_DEFAULT,
) -> DriftMeta | None:
    """Compute the drift summary for one region, realized-only.

    Returns None if there is not enough realized history (caller skips). Uses
    ``score_calibration.build_pair_frame`` so the realized/anti-leakage contract
    is identical to the calibration module.
    """
    try:
        pairs = build_pair_frame(oos_scores, panel, region)
    except ValueError:
        return None  # empty panel / missing cols
    realized = pairs.dropna(subset=["forward_return_h"]).sort_values("date").copy()
    if len(realized) < _MIN_HISTORY:
        return None
    realized["month"] = realized["date"].dt.to_period("M")
    months = sorted(realized["month"].unique())
    # Need at least recent_months history BEFORE the recent window.
    if len(months) <= recent_months:
        return None
    recent_start = months[-recent_months]
    hist = realized[realized["month"] < recent_start]
    recent = realized[realized["month"] >= recent_start]
    if len(hist) < _MIN_HISTORY or len(recent) < _MIN_RECENT:
        return None
    psi = _psi(hist["score"], recent["score"])
    regime = "stable" if psi < 0.1 else ("moderate" if psi < 0.25 else "significant")
    full_up = realized["realized_up"].dropna()
    return DriftMeta(
        region=region,
        n_history=int(len(hist)),
        n_recent=int(len(recent)),
        recent_months=int(recent_months),
        psi=round(psi, 4),
        ic_full=round(_monthly_rank_ic(hist), 4),
        ic_recent=round(_monthly_rank_ic(recent), 4),
        base_rate_full=round(float(full_up.mean()), 4),
        base_rate_recent=round(float(recent["realized_up"].dropna().mean()), 4),
        regime=regime,
    )


def drift_summary(
    oos_scores: pd.DataFrame,
    us_panel: pd.DataFrame,
    cn_panel: pd.DataFrame,
    recent_months: int = _RECENT_MONTHS_DEFAULT,
) -> dict[str, Any]:
    """Per-region drift summary for terminal export.

    Returns ``{recent_months, methodology, regions: {region: DriftMeta-jsonable}}``.
    Regions with insufficient realized history are omitted (not errored).
    """
    out: dict[str, Any] = {
        "recent_months": recent_months,
        "methodology": (
            "Leakage-safe model-drift monitor (display-only). Population Stability "
            "Index (PSI) compares the recent realized score distribution to the "
            "historical one; rolling cross-sectional rank-IC (recent mean vs full "
            "mean) is reported for context. All metrics use only realized "
            "(score, forward_return) pairs strictly before the latest unread month. "
            "PSI<0.1 stable / 0.1–0.25 moderate / ≥0.25 significant. NOT a research "
            "claim and NOT a retrain trigger (rerun-to-significance is forbidden)."
        ),
        "regions": {},
    }
    for region, panel in (("us", us_panel), ("cn", cn_panel)):
        meta = compute_drift(oos_scores, panel, region, recent_months=recent_months)
        if meta is not None:
            out["regions"][region] = drift_meta_to_jsonable(meta)
    return out


def drift_meta_to_jsonable(meta: DriftMeta) -> dict[str, Any]:
    """JSON-safe view of DriftMeta."""
    return {
        "region": meta.region,
        "n_history": meta.n_history,
        "n_recent": meta.n_recent,
        "recent_months": meta.recent_months,
        "psi": meta.psi,
        "ic_full": meta.ic_full,
        "ic_recent": meta.ic_recent,
        "base_rate_full": meta.base_rate_full,
        "base_rate_recent": meta.base_rate_recent,
        "regime": meta.regime,
    }
