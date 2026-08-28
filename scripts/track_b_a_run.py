"""Track B rank-IC runner. Binds to config #41 (treatment, 23 features) or #42 (price-only, 10).

Anti-leakage: config_committed (rows #41/#42) PRECEDE these observations.
Modes:
  treatment    -> 23-feature arm (config #41)
  price_only   -> 10-price-feature baseline arm (config #42)
  differential -> both arms + paired monthly IC differential (treatment - price_only),
                  the pre-reg section 1 headline claim (HAC CI via rank_ic_summary).

Runtime config binding: at run time a sha256 fingerprint is recomputed over the
effective feature-column sets (both arms) + the panel file bytes, printed to
stdout as ``[track_b] config_sha256=...`` and stamped into the differential
site_data JSON (``config_sha256``). This makes the "config #41/#42" claim
verifiable per run; a changed feature set or panel changes the fingerprint.
No ledger write here — the frozen-config ledger rule lives upstream.

Run:  uv run python scripts/track_b_a_run.py --mode differential
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pandas as pd

from aionis.config import settings
from aionis.eval.rank_ic import rank_ic_summary
from aionis.eval.track_b_baseline import fit_track_b_baseline
from aionis.features.corporate_vital_signs import TRACK_B_FEATURE_COLS
from aionis.features.price_features import TRACK_B_PRICE_FEATURE_COLS

PANEL_PATH = settings.data_dir / "cache" / "track_b_panel.parquet"
ARMS: dict[str, list[str]] = {
    "treatment": [*TRACK_B_FEATURE_COLS, *TRACK_B_PRICE_FEATURE_COLS],  # 23, config #41
    "price_only": TRACK_B_PRICE_FEATURE_COLS,  # 10, config #42
}
ARM_CONFIG = {"treatment": "#41 (sig bf620b...)", "price_only": "#42 (sig 9af9e8b...)"}


def _config_sha256(panel_path: Path) -> str:
    """Runtime config fingerprint: sha256 over feature-column sets + panel file bytes.

    Deterministic given the same feature sets + panel artifact (sorted arm names,
    byte-exact file read). The docstring "config #41/#42" binding is only honest
    if recomputed from live state at run time — this is that recomputation.
    """
    hasher = hashlib.sha256()
    for arm in sorted(ARMS):
        hasher.update(f"arm={arm};features={','.join(ARMS[arm])};".encode())
    hasher.update(panel_path.read_bytes())
    return hasher.hexdigest()


def _run_arm(panel: pd.DataFrame, arm: str) -> object:
    feats = ARMS[arm]
    print(f"--- arm: {arm} ({len(feats)} features, config {ARM_CONFIG[arm]}) ---", flush=True)
    result = fit_track_b_baseline(
        panel=panel,
        feature_cols=feats,
        horizon=21,
        min_train_months=60,
        embargo_sessions=21,
        bin_count=5,
    )
    lo, hi = result.ci_95
    print(f"mean_ic: {result.mean_ic:.6f}   ci_95: ({lo:.6f}, {hi:.6f})", flush=True)
    print(
        f"  p_hac: {result.p_hac:.4f}   dm_stat: {result.dm_stat:.4f}   "
        f"dm_p: {result.dm_p:.4f}",
        flush=True,
    )
    print(
        f"  n_folds: {result.n_walk_folds}   ic_start: {result.ic_series.index.min()}",
        flush=True,
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["treatment", "price_only", "differential"],
        default="treatment",
    )
    args = parser.parse_args()

    panel = pd.read_parquet(PANEL_PATH)
    config_sha256 = _config_sha256(PANEL_PATH)
    print(f"[track_b] config_sha256={config_sha256}", flush=True)
    print(
        f"[track_b] arms={ {a: len(f) for a, f in sorted(ARMS.items())} } "
        f"panel={PANEL_PATH}",
        flush=True,
    )
    print(f"panel: {panel.shape}, dates {panel['date'].min()}..{panel['date'].max()}", flush=True)
    print(f"mode: {args.mode}", flush=True)

    if args.mode == "differential":
        rt = _run_arm(panel, "treatment")
        rp = _run_arm(panel, "price_only")
        # Paired monthly IC differential (pre-reg section 1 headline): align, subtract.
        diff = (rt.ic_series - rp.ic_series).dropna()
        summary = rank_ic_summary(diff)
        mean_d = summary["mean_ic"]
        half_d = summary["ci_half"]
        lo_d, hi_d = mean_d - half_d, mean_d + half_d
        print("=== DIFFERENTIAL (treatment - price_only, paired by month, HAC) ===", flush=True)
        print(f"mean_diff: {mean_d:.6f}   hac_se: {summary['se_hac']:.6f}", flush=True)
        print(f"ci_95:     ({lo_d:.6f}, {hi_d:.6f})", flush=True)
        print(
            f"t_hac: {summary['t_hac']:.4f}   p_hac: {summary['p_hac']:.4f}   "
            f"n_months: {len(diff)}",
            flush=True,
        )
        # Persist real IC series + headline numbers + OOS scores for the static site
        # (GitHub Pages) and net-cost backtest (mount② FINSABER).
        import json

        # Convert oos_scores to dict for JSON serialization
        treatment_scores_dict = {
            "dates": rt.oos_scores["date"].dt.strftime("%Y-%m-%d").tolist(),
            "tickers": rt.oos_scores["ticker"].tolist(),
            "scores": rt.oos_scores["score"].tolist(),
        }
        price_only_scores_dict = {
            "dates": rp.oos_scores["date"].dt.strftime("%Y-%m-%d").tolist(),
            "tickers": rp.oos_scores["ticker"].tolist(),
            "scores": rp.oos_scores["score"].tolist(),
        }

        site_data = {
            "treatment": {
                "mean_ic": rt.mean_ic,
                "ci95": list(rt.ci_95),
                "p_hac": rt.p_hac,
                "ic_series": {str(k): v for k, v in rt.ic_series.items()},
                "monthly_dates": rt.monthly_dates,
                "monthly_model_returns": rt.monthly_model_returns,
                "monthly_ew_returns": rt.monthly_ew_returns,
                "oos_scores": treatment_scores_dict,
            },
            "price_only": {
                "mean_ic": rp.mean_ic,
                "ci95": list(rp.ci_95),
                "p_hac": rp.p_hac,
                "ic_series": {str(k): v for k, v in rp.ic_series.items()},
                "monthly_dates": rp.monthly_dates,
                "monthly_model_returns": rp.monthly_model_returns,
                "monthly_ew_returns": rp.monthly_ew_returns,
                "oos_scores": price_only_scores_dict,
            },
            "differential": {
                "mean_diff": mean_d,
                "ci95": [lo_d, hi_d],
                "p_hac": summary["p_hac"],
                "ic_series": {str(k): v for k, v in diff.items()},
            },
        }
        # Runtime config binding stamp (feature sets + panel bytes) into the
        # output summary — honest provenance, no ledger write.
        site_data["config_sha256"] = config_sha256
        site_path = settings.data_dir.parent / "site" / "track_b_data.json"
        site_path.parent.mkdir(parents=True, exist_ok=True)
        site_path.write_text(json.dumps(site_data, indent=2), encoding="utf-8")
        print(f"saved site data + OOS scores -> {site_path}", flush=True)
    else:
        _run_arm(panel, args.mode)


if __name__ == "__main__":
    main()
