"""Track C conditional rank-IC: does the A-share price-only IC vary with regime_state?

The Track C confirmatory estimand (frozen config #46) is a SINGLE pre-specified interaction
score x regime_state (multiplicity budget 1). This runner is the EXPLORATORY first look:
regress the realized monthly IC series on the regime_state (HAC SE) + split high/low regime.

Anti-leakage: regime_state is PIT (TACO uses [t0,t], knowable at t); the IC series is the
realized OUT-of-sample IC (forward returns t..t+h). The regression tests whether realized IC
co-varies with the PIT regime — standard post-hoc IC-series analysis, no lookahead.

EXPLORATORY caveats (do NOT treat as the Track C confirmatory claim):
  * 2-layer regime composite (macro+global; meso deferred).
  * Track B fitter applied to CN data (not the joint US-CN fold).
  * n=90 months; a marginal beta p-value is NOT <0.05.
The confirmatory claim needs the 3-layer composite + joint fold + J-T gate + a new ledger row.

Run: uv run python scripts/track_c_conditional_ic.py
"""

from __future__ import annotations

import json

import pandas as pd
import statsmodels.api as sm
from statsmodels.regression.linear_model import OLS

from aionis.config import settings

IC_PATH = settings.data_dir.parent / "runs" / "track_c_cn_ic_series.parquet"
REGIME_PATH = settings.data_dir / "cache" / "regime_composite.parquet"
OUT_PATH = settings.data_dir.parent / "runs" / "track_c_cn_conditional_ic.json"


def main() -> None:
    """Regress CN monthly IC on regime_state (HAC) + high/low regime split."""
    ic = pd.read_parquet(IC_PATH)
    reg = pd.read_parquet(REGIME_PATH)
    ic.index = pd.to_datetime(ic.index)
    reg.index = pd.to_datetime(reg.index)
    print(f"[S] ic: n={len(ic)} | regime: n={len(reg)}", flush=True)

    # regime_state as-of each IC month-end date (forward-fill the daily series to the
    # month-end; PIT-safe — regime uses only data <= the month-end date).
    reg_me = reg["regime_state"].reindex(ic.index, method="ffill")
    df = pd.DataFrame({"ic": ic["ic"], "regime": reg_me}).dropna()
    n = len(df)
    print(f"[S] aligned months: {n}", flush=True)

    # Single pre-specified interaction: IC_t ~ regime_t (HAC SE).
    maxlag = max(1, int(4 * (n / 100.0) ** (2 / 9)))  # Newey-West rule of thumb
    X = sm.add_constant(df["regime"])
    res = OLS(df["ic"], X).fit(cov_type="HAC", cov_kwds={"maxlags": maxlag})
    alpha = float(res.params.iloc[0])
    alpha_p = float(res.pvalues.iloc[0])
    beta = float(res.params.iloc[1])
    beta_p = float(res.pvalues.iloc[1])

    # High/low regime split (median).
    med = float(df["regime"].median())
    hi = df[df["regime"] >= med]["ic"]
    lo = df[df["regime"] < med]["ic"]

    print("=== CN conditional rank-IC (IC_t ~ regime_t, HAC) ===", flush=True)
    print(f"  n={n}  maxlag={maxlag}", flush=True)
    print(f"  alpha (IC at regime=0): {alpha:.6f}  (HAC p={alpha_p:.4f})", flush=True)
    print(f"  beta  (interaction):    {beta:.6f}  (HAC p={beta_p:.4f})", flush=True)
    corr = float(df["ic"].corr(df["regime"]))
    print(f"  R^2: {res.rsquared:.4f}  corr(IC,regime): {corr:.4f}", flush=True)
    print(f"  mean IC | high-regime (n={len(hi)}): {hi.mean():.6f}", flush=True)
    print(f"  mean IC | low-regime  (n={len(lo)}): {lo.mean():.6f}", flush=True)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(
            {
                "n_months": n,
                "maxlag": maxlag,
                "alpha": alpha,
                "alpha_p": alpha_p,
                "beta_interaction": beta,
                "beta_p": beta_p,
                "r_squared": float(res.rsquared),
                "corr_ic_regime": float(df["ic"].corr(df["regime"])),
                "mean_ic_high_regime": float(hi.mean()),
                "mean_ic_low_regime": float(lo.mean()),
                "n_high": int(len(hi)),
                "n_low": int(len(lo)),
                "caveats": [
                    "exploratory: 2-layer regime (macro+global; meso deferred)",
                    "exploratory: Track B fitter on CN (not joint US-CN fold)",
                    f"beta p={beta_p:.4f} is marginal, not <0.05",
                ],
            },
            indent=2
        ),
        encoding="utf-8",
    )
    print(f"[S] wrote {OUT_PATH}", flush=True)


if __name__ == "__main__":
    main()
