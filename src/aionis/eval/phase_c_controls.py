"""Phase C control gates (pre-reg §5): the bundle-shuffle placebo.

Phase C's headline is the ``arm_macro`` vs ``arm_base`` rank-IC differential. The
core control (§5 #2) simultaneously breaks the alignment of EVERY bundle
component: macro/VIX-surprise are date-broadcast, so their value→date mapping is
scrambled across dates; earnings-surprise is per-(ticker, date), so its
value→ticker mapping is scrambled within each date. Timing / coverage / NaN
structure are preserved — only the *alignment* of the value to the thing it
claims to describe is destroyed. If the bundle's differential is a real
world-state signal, it must vanish under this shuffle.

Both helpers are NaN-preserving and seed-deterministic (the placebo must be
reproducible — H6). They operate on the exact frames the Phase C runner assembles
for :func:`aionis.eval.two_arm.run_arm_oos` (a date-indexed ``macro`` frame and a
long ``[date, ticker, value]`` extra-features frame), so the placebo re-runs the
SAME arm on the SAME folds with ONLY the alignment perturbed.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def shuffle_date_broadcast(
    frame: pd.DataFrame, seed: int = 0
) -> pd.DataFrame:
    """Permute each column's non-NaN values across the date index.

    For a date-broadcast feature (macro / VIX surprise), the value at date ``d``
    is the signal markets saw at ``d``. Scrambling which value lands on which date
    destroys the date→value alignment while preserving the marginal distribution
    of surprises AND the NaN / coverage structure (a release published at ``r`` is
    still "known" at ``r``'s position in the sense that the NaN pattern — the
    pre-first-release gap — is unchanged). A single value, or all-NaN, is left
    untouched (nothing to permute).
    """
    rng = np.random.default_rng(seed)
    out = frame.copy()
    for col in out.columns:
        vals = out[col].to_numpy(dtype=float).copy()
        mask = ~np.isnan(vals)
        if int(mask.sum()) > 1:
            picked = vals[mask].copy()
            rng.shuffle(picked)
            vals[mask] = picked
            out[col] = vals
    return out


def shuffle_earnings_across_tickers(
    extra_long: pd.DataFrame, seed: int = 0
) -> pd.DataFrame:
    """Permute the earnings-surprise value across tickers WITHIN each date.

    The earnings surprise is per-(ticker, date). Scrambling it across tickers at
    a fixed date preserves the date (so each value stays at a date it was
    genuinely knowable) and the NaN structure, but destroys which company's
    surprise is whose — "保时点、乱公司→值" (phase-c-preregistration §5 #2). The
    value column is ``earnings_surprise`` when present, else the last column.
    """
    rng = np.random.default_rng(seed)
    out = extra_long.copy()
    val_col = "earnings_surprise" if "earnings_surprise" in out.columns else out.columns[-1]
    for _d, grp in out.groupby("date", sort=False):
        idx = grp.index.to_numpy()
        vals = grp[val_col].to_numpy(dtype=float).copy()
        mask = ~np.isnan(vals)
        if int(mask.sum()) > 1:
            picked = vals[mask].copy()
            rng.shuffle(picked)
            vals[mask] = picked
            out.loc[idx, val_col] = vals
    return out
