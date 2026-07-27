"""Phase B control gates (pre-reg §5): lag-shift + within-month placebo.

Both perturb the arm_state fundamentals to test whether the filed-date timing
differential is robust. ``arm_base`` (period-end+lag) is itself the primary control
(C3) — the headline IS the arm_state-vs-arm_base differential. These two are the
SECONDARY controls: if the differential shrinks/vanishes under them, the signal is
NOT from precise filed timing.

  * :func:`lag_shift_filed` — per-ticker constant random lag added to ``filed``
    (a constant shift is order-preserving by construction). "Does shifting ALL of a
    company's filed dates kill arm_state's edge?"
  * :func:`within_month_placebo` — permute ``value`` across tickers within
    (metric, filed-month); timing + metric labels kept, company-value alignment
    broken. "Is arm_state's edge from the value-at-timing alignment?"

USAGE (critic HIGH-2): apply the perturbation to arm_state's fundamentals ONLY and
run it via ``two_arm.run_arm_oos`` against arm_base on the REAL fundamentals (same
``compute_shared_folds``). Do NOT feed a perturbed frame to ``run_two_arm_oos`` —
that would scramble arm_base too (arm_base ignores ``filed`` for ALIGNMENT but still
consumes ``value``), collapsing the differential trivially. lag_shift mutates only
``filed`` (which arm_base ignores entirely), so it is safe either way; placebo
mutates ``value`` and MUST be isolated to arm_state.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def lag_shift_filed(
    long: pd.DataFrame, seed: int = 0, lag_days: tuple[int, int] = (15, 90),
) -> pd.DataFrame:
    """Per-ticker constant random lag (uniform in ``lag_days``) added to ``filed``.
    The empirical filing-lag distribution (filed - end) is ~30-90 days; this span
    covers it. Constant-per-ticker => intra-ticker filing order is preserved."""
    rng = np.random.default_rng(seed)
    out = long.copy()
    out["filed"] = pd.to_datetime(out["filed"])
    shifts = {t: int(rng.integers(lag_days[0], lag_days[1] + 1)) for t in out["ticker"].unique()}
    out["filed"] = out["filed"] + pd.to_timedelta(out["ticker"].map(shifts), unit="D")
    return out


def within_month_placebo(long: pd.DataFrame, seed: int = 0) -> pd.DataFrame:
    """Permute ``value`` across tickers within each (metric, filed-month) group.
    Filed dates + metric labels are UNCHANGED; only which company's value lands on a
    given (ticker, metric, filed) row is scrambled -> destroys company-value
    alignment while keeping the full timing structure."""
    rng = np.random.default_rng(seed)
    out = long.copy()
    out["_fm"] = pd.to_datetime(out["filed"]).dt.to_period("M").astype(str)
    groups = out.groupby(["metric", "_fm"]).groups
    for _key, idx in groups.items():
        idx = list(idx)
        if len(idx) > 1:
            vals = out.loc[idx, "value"].to_numpy(dtype=float).copy()
            rng.shuffle(vals)
            out.loc[idx, "value"] = vals
    return out.drop(columns=["_fm"])
