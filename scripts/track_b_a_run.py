"""Track B (a-run): first OOS rank-IC observation. Binds to config #41 (ledger row 41).

Anti-leakage: config_committed (row #41, sig bf620bdf...c32ba4f9) PRECEDES this
observation. The 23 feature_cols match the materialized panel (all materialized with
good coverage after volume+SPY fetch).

Loads data/cache/track_b_panel.parquet, runs the chronological walk-forward lambdarank
baseline (fit_track_b_baseline), prints rank-IC + HAC CI + DM vs equal-weight.

Run:  uv run python scripts/track_b_a_run.py
"""
from __future__ import annotations

import pandas as pd

from aionis.config import settings
from aionis.eval.track_b_baseline import fit_track_b_baseline
from aionis.features.corporate_vital_signs import TRACK_B_FEATURE_COLS
from aionis.features.price_features import TRACK_B_PRICE_FEATURE_COLS

PANEL_PATH = settings.data_dir / "cache" / "track_b_panel.parquet"
FEATURE_COLS = [*TRACK_B_FEATURE_COLS, *TRACK_B_PRICE_FEATURE_COLS]  # 23, config #41


def main() -> None:
    panel = pd.read_parquet(PANEL_PATH)
    print(f"panel: {panel.shape}, dates {panel['date'].min()}..{panel['date'].max()}", flush=True)
    print(f"features: {len(FEATURE_COLS)} (config #41, sig bf620b...)", flush=True)

    result = fit_track_b_baseline(
        panel=panel,
        feature_cols=FEATURE_COLS,
        horizon=21,
        min_train_months=60,
        embargo_sessions=21,
        bin_count=5,
    )

    print("=== Track B first rank-IC (config #41, chronological walk-forward lambdarank) ===",
          flush=True)
    print(f"mean_ic:     {result.mean_ic:.6f}", flush=True)
    print(f"hac_se:      {result.hac_se:.6f}", flush=True)
    print(f"ci_95:       ({result.ci_95[0]:.6f}, {result.ci_95[1]:.6f})", flush=True)
    print(f"t_hac:       {result.t_hac:.4f}    p_hac: {result.p_hac:.4f}", flush=True)
    print(f"dm_stat:     {result.dm_stat:.4f}    dm_p:  {result.dm_p:.4f}", flush=True)
    print(f"n_walk_folds:{result.n_walk_folds}    n_test_obs: {result.n_test_obs}", flush=True)
    print(f"ic_series (first 6 months):\n{result.ic_series.head(6)}", flush=True)


if __name__ == "__main__":
    main()
