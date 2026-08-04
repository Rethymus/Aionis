"""Track C joint US-CN rank-IC runner (EXPLORATORY machinery proof).

Runs the joint dual-region chronological walk-forward estimator on the REAL US (track_b)
+ CN (cn_price) month-end panels with the 10 shared price features, conditioned on the
existing regime_state composite. Proves the confirmatory machinery on real data.

EXPLORATORY — NOT the Track C confirmatory claim:
  * Uses 10 shared price features only (confirmatory needs the full frozen feature_cols
    per ledger #46, including fundamentals — cninfo fetch is a separate owner-gated slice).
  * Uses whichever regime composite currently exists in data/cache/regime_composite.parquet
    (2-layer or 3-layer-US-only-meso) — NOT necessarily the spec-faithful 3-layer with CN
    shenwan meso (pending the shenwan 7-gate verdict).
  * group = region-month (currency-clean D1 default); #46 did not freeze group construction,
    so this is a recommended default pending owner sign-off (Q1).
  * Writes NO ledger. The confirmatory run = owner GO + new ledger row.

Anti-leakage: shared features are price-only (past-only); forward_return_h is label-only;
regime_state is PIT (TACO as-of); per-region chronological asserted inside fit_track_c_joint.

Run:  uv run python scripts/track_c_joint_run.py
"""

from __future__ import annotations

import json
import os

import pandas as pd

from aionis.config import settings
from aionis.eval.track_c_joint import build_joint_panel, fit_track_c_joint
from aionis.features.price_features import TRACK_B_PRICE_FEATURE_COLS

US_PANEL = settings.data_dir / "cache" / "track_b_panel.parquet"
CN_PANEL = settings.data_dir / "cache" / "cn_price_panel.parquet"
REGIME_PANEL = settings.data_dir / "cache" / "regime_composite.parquet"
WINDOW_START = "2016-01-01"  # ledger #46 universe.{us,cn}.window_start


def main() -> None:
    """Run the joint US-CN rank-IC estimator (exploratory, no ledger)."""
    for p in (US_PANEL, CN_PANEL, REGIME_PANEL):
        if not p.exists():
            raise SystemExit(f"[ERROR] missing {p}")

    print(f"[S] building joint panel (window_start={WINDOW_START})...", flush=True)
    joint = build_joint_panel(
        US_PANEL, CN_PANEL, feature_cols=TRACK_B_PRICE_FEATURE_COLS, window_start=WINDOW_START
    )
    print(
        f"[S] joint panel: {joint.shape} | dates {joint['date'].min()}..{joint['date'].max()} "
        f"| regions {dict(joint['region'].value_counts())}",
        flush=True,
    )
    print(
        f"[S] feature_cols ({len(TRACK_B_PRICE_FEATURE_COLS)}): {TRACK_B_PRICE_FEATURE_COLS}",
        flush=True,
    )

    regime_df = pd.read_parquet(REGIME_PANEL)
    if "regime_state" not in regime_df.columns:
        raise SystemExit(
            f"[ERROR] {REGIME_PANEL} has no 'regime_state' column: {regime_df.columns}"
        )
    regime_df.index = pd.to_datetime(regime_df.index)
    regime_state = regime_df["regime_state"].sort_index()
    print(
        f"[S] regime_state: n={len(regime_state)} valid={int(regime_state.notna().sum())}",
        flush=True,
    )

    print("[S] fitting joint walk-forward (lambdarank, region-month groups)...", flush=True)
    result = fit_track_c_joint(
        panel=joint,
        feature_cols=TRACK_B_PRICE_FEATURE_COLS,
        regime_state=regime_state,
        horizon=21,
        min_train_months=60,
        embargo_sessions=21,
        bin_count=5,
    )

    lo, hi = result.ci_95
    print("=== Track C joint US-CN rank-IC (EXPLORATORY machinery) ===", flush=True)
    print(
        f"  n_folds: {result.n_walk_folds}   n_months(IC): {len(result.combined_ic_series)}",
        flush=True,
    )
    print(
        f"  combined mean_ic: {result.mean_ic:.6f}   ci_95: ({lo:.6f}, {hi:.6f})   "
        f"t_hac: {result.t_hac:.4f}   p_hac: {result.p_hac:.4f}",
        flush=True,
    )
    print(
        f"  us_ic mean: {result.us_ic_series.mean():.6f} (n={len(result.us_ic_series)})   "
        f"cn_ic mean: {result.cn_ic_series.mean():.6f} (n={len(result.cn_ic_series)})",
        flush=True,
    )
    print("  --- conditional-IC (combined_ic ~ regime, HAC) ---", flush=True)
    print(
        f"  alpha: {result.cond_alpha:.6f} (p={result.cond_alpha_p:.4f})   "
        f"beta(interaction): {result.cond_beta:.6f} (p={result.cond_beta_p:.4f})   "
        f"R^2: {result.cond_r_squared:.4f}   n={result.cond_n_months}",
        flush=True,
    )

    out_dir = settings.data_dir.parent / "runs"
    out_dir.mkdir(parents=True, exist_ok=True)
    result.oos_scores.to_parquet(out_dir / "track_c_joint_oos_scores.parquet")
    pd.concat(
        [
            result.us_ic_series.rename("us"),
            result.cn_ic_series.rename("cn"),
            result.combined_ic_series.rename("combined"),
        ],
        axis=1,
    ).to_parquet(out_dir / "track_c_joint_ic_series.parquet")
    (out_dir / "track_c_joint_summary.json").write_text(
        json.dumps(
            {
                "n_folds": result.n_walk_folds,
                "n_months_ic": len(result.combined_ic_series),
                "combined_mean_ic": result.mean_ic,
                "ci_95": list(result.ci_95),
                "t_hac": result.t_hac,
                "p_hac": result.p_hac,
                "us_ic_mean": float(result.us_ic_series.mean()),
                "cn_ic_mean": float(result.cn_ic_series.mean()),
                "cond_alpha": result.cond_alpha,
                "cond_alpha_p": result.cond_alpha_p,
                "cond_beta": result.cond_beta,
                "cond_beta_p": result.cond_beta_p,
                "cond_r_squared": result.cond_r_squared,
                "cond_n_months": result.cond_n_months,
                "caveats": [
                    "exploratory: 10 shared price feats (confirmatory needs full #46 cols)",
                    "exploratory: regime from regime_composite.parquet (CN meso pending 7-gate)",
                    "exploratory: group=region-month (D1 default; #46 did not freeze groups)",
                    "NO ledger; NOT the confirmatory claim",
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[S] saved -> {out_dir}/track_c_joint_{{oos_scores,ic_series,summary}}", flush=True)
    print("[S] DONE (exploratory; no ledger)", flush=True)


if __name__ == "__main__":
    if os.environ.get("PHASE_C_NO_LEDGER") == "1":
        print("[S] ARTIFACTS-ONLY (exploratory; never writes ledger)", flush=True)
    main()
