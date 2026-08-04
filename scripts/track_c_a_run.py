"""Track C A-share price-only rank-IC runner (EXPLORATORY first look).

Mirrors scripts/track_b_a_run.py for the CN side. Loads the CSI300 month-end price panel
and runs fit_track_b_baseline (chronological walk-forward lambdarank) -> A-share monthly
rank-IC + HAC inference + DM-vs-EW.

EXPLORORATORY: uses Track B's fitter on CN data as a first peek at A-share price signal;
this is NOT the Track C joint dual-region confirmatory claim (which needs the regime_state
interaction + per-region joint fold under frozen config #46/#47). Writes NO ledger.
Anti-leakage: the panel's config_committed anchor is upstream (the CSI300/price snapshots);
no OOS metric is observed before the frozen Track C config for the CONFIRMATORY claim.

Run:  uv run python scripts/track_c_a_run.py
"""
from __future__ import annotations

import os

import pandas as pd

from aionis.config import settings
from aionis.eval.track_b_baseline import fit_track_b_baseline
from aionis.features.price_features import TRACK_B_PRICE_FEATURE_COLS

PANEL = settings.data_dir / "cache" / "cn_price_panel.parquet"
# 12 features = 10 Track B price features + 2 A-share extras (config cn_price_12 mirror).
CN_FEATURE_COLS = [
    *TRACK_B_PRICE_FEATURE_COLS,
    "limit_up_down_distance",
    "suspension_flag",
]


def main() -> None:
    """Run the CN A-share price-only rank-IC."""
    if not PANEL.exists():
        raise SystemExit(
            f"[ERROR] {PANEL} missing — run scripts/build_cn_price_panel.py first."
        )

    panel = pd.read_parquet(PANEL)
    print(
        f"[S] CN panel: {panel.shape} | dates {panel['date'].min()}..{panel['date'].max()} "
        f"| {panel['ticker'].nunique()} tickers",
        flush=True,
    )
    print(f"[S] feature_cols ({len(CN_FEATURE_COLS)}): {CN_FEATURE_COLS}", flush=True)

    result = fit_track_b_baseline(
        panel=panel,
        feature_cols=CN_FEATURE_COLS,
        horizon=21,
        min_train_months=60,
        embargo_sessions=21,
        bin_count=5,
    )

    lo, hi = result.ci_95
    print("=== CN A-share price-only rank-IC (exploratory, Track B fitter) ===", flush=True)
    print(f"mean_ic: {result.mean_ic:.6f}   ci_95: ({lo:.6f}, {hi:.6f})", flush=True)
    print(
        f"  p_hac: {result.p_hac:.4f}   dm_stat: {result.dm_stat:.4f}   "
        f"dm_p: {result.dm_p:.4f}",
        flush=True,
    )
    print(
        f"  n_folds: {result.n_walk_folds}   ic_range: "
        f"{result.ic_series.index.min()} .. {result.ic_series.index.max()}",
        flush=True,
    )

    # Persist OOS scores + IC series for net-cost / inspection (runs/, gitignored; NO ledger).
    out_dir = (
        settings.runs_dir
        if hasattr(settings, "runs_dir")
        else settings.data_dir.parent / "runs"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    result.oos_scores[["date", "ticker", "score"]].to_parquet(
        out_dir / "track_c_cn_oos_scores.parquet"
    )
    result.ic_series.rename("ic").to_frame().to_parquet(
        out_dir / "track_c_cn_ic_series.parquet"
    )
    print(f"[S] saved OOS scores + IC series -> {out_dir}/track_c_cn_*", flush=True)
    print("[S] DONE", flush=True)


if __name__ == "__main__":
    if os.environ.get("PHASE_C_NO_LEDGER") == "1":
        print("[S] ARTIFACTS-ONLY (exploratory; never writes ledger)", flush=True)
    main()
