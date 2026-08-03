"""RES-03 rank-aware baseline runner (trial BASELINE-RANK-001, EXPLORATORY ONLY).

Adds the lambdarank rung to the baseline ladder: same frozen Phase B features
(scripts/phase_b_run.py FEATURE_COLS), same purged cross-fitted CV evidence
strength (5-fold PurgedGroupKFold, group=month, embargo=21 sessions, shared
folds via eval.two_arm.compute_shared_folds), same H6 determinism pins — only the
objective changes (MSE regression -> lambdarank, RD-15 frozen contract).

Anti-leakage contract (all via the FROZEN ranking_contract API, read-only):
  1. Relevance bin edges fit on the TRAIN fold ONLY, per calendar month
     (construct_month_groups -> fit_monthly_bins -> transform_to_relevance).
  2. Test fold uses frozen edges: out-of-range returns are CLAMPED to the nearest
     train-fold bin (1 / n_bins) with a reason code — NEVER refit.
  3. NaN forward returns -> relevance -1 -> EXCLUDED
     (filter_valid_ranking_samples); group sizes re-derived AFTER filtering
     (get_group_sizes), so LightGBM groups always match row counts.
  4. objective is validated against the frozen enum (validate_objective) inside
     the learner's rank branch (fail-fast).

NO CONFIRMATORY HEADLINE: this runner writes NO ledger row and NO runs/results
artifacts. config_committed for BASELINE-RANK-001 requires explicit owner
authorization (task gate) before any out-of-sample metric is observed.

Run (owner-authorized, real data):  uv run python scripts/res_03_baseline_rank_run.py
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from aionis.config import settings
from aionis.eval.cv import CVSplit
from aionis.eval.learner import LightGBMFrozen
from aionis.eval.rank_ic import rank_ic_monthly, rank_ic_summary
from aionis.eval.ranking_contract import (
    construct_month_groups,
    filter_valid_ranking_samples,
    fit_monthly_bins,
    get_group_sizes,
    transform_to_relevance,
    validate_objective,
)
from aionis.features.selection_panel import build_selection_panel
from aionis.ingest.universe import load_pierrebrunelle_membership, mask_panel_to_pit

CONFIG_PATH = Path("config/baseline_rank_001.yaml")
CACHE = settings.data_dir / "cache"
HORIZON = 21
N_SPLITS = 5
EMBARGO = 21
ALIGN_ON = "filed"


def load_config(path: Path | str = CONFIG_PATH) -> dict:
    """Load and validate ``config/baseline_rank_001.yaml``.

    Raises:
        ValueError: contract violations — objective not in the frozen enum,
            ``rank_bins`` not in {5, 10}, missing/empty ``feature_cols``, or H6
            determinism pins (n_jobs/random_state) deviating from 1/0.
    """
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if not isinstance(cfg, dict):
        raise ValueError(f"config {path} must be a YAML mapping")

    objective = cfg.get("objective")
    if objective is None:
        raise ValueError(f"config {path}: missing 'objective'")
    validate_objective(str(objective))  # frozen enum gate (RD-15 decision #1)

    rank_bins = cfg.get("rank_bins")
    if rank_bins not in (5, 10):
        raise ValueError(f"config {path}: rank_bins must be 5 or 10, got {rank_bins!r}")

    feature_cols = cfg.get("feature_cols")
    if not isinstance(feature_cols, list) or not feature_cols:
        raise ValueError(f"config {path}: feature_cols must be a non-empty list")

    frozen_params = cfg.get("frozen_params") or {}
    if frozen_params.get("n_jobs", 1) != 1:
        raise ValueError("frozen_params.n_jobs must be 1 (H6 determinism)")
    if frozen_params.get("random_state", 0) != 0:
        raise ValueError("frozen_params.random_state must be 0 (H6 determinism)")

    return cfg


def config_sig(cfg: dict) -> str:
    """sha256 of the frozen config — the anti-leakage anchor (mirrors phase_b_run)."""
    return hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()


def build_rank_panel(
    prices: pd.DataFrame,
    fundamentals_long: pd.DataFrame,
    membership: pd.DataFrame,
    horizon: int = HORIZON,
    align_on: str = ALIGN_ON,
) -> pd.DataFrame:
    """PIT-masked, NaN-label-dropped panel in canonical (date, ticker) order.

    Mirrors ``eval.two_arm._clean_panel`` so fold indices produced by
    ``compute_shared_folds`` align with this panel's rows.
    """
    p = build_selection_panel(prices, fundamentals_long, horizon, align_on=align_on)
    p = mask_panel_to_pit(p, membership)
    return (
        p.dropna(subset=["y_fwd_ret"])
        .sort_values(["date", "ticker"])
        .reset_index(drop=True)
    )


def run_rank_cv(
    panel: pd.DataFrame,
    feature_cols: list[str],
    folds: list[CVSplit],
    cfg: dict,
) -> pd.DataFrame:
    """Cross-fitted OOF lambdarank scores on shared PurgedGroupKFold folds.

    Per-fold ranking preparation goes through the FROZEN RD-15 API chain ONLY:
    ``construct_month_groups`` -> ``fit_monthly_bins`` -> ``transform_to_relevance``
    -> ``filter_valid_ranking_samples`` -> ``get_group_sizes``, then
    ``LightGBMFrozen.fit_predict_rank`` (whose rank branch validates the objective
    via ``ranking_contract.validate_objective``). Bins are fitted on the TRAIN
    fold only; the test fold is transformed with frozen edges (clamp + reason
    codes; never refit).

    Args:
        panel: clean panel ``[date, ticker, *feature_cols, y_fwd_ret]`` in
            canonical (date, ticker) order (see ``build_rank_panel``).
        feature_cols: pre-specified features (config, identical to frozen B).
        folds: shared folds from ``eval.two_arm.compute_shared_folds``.
        cfg: validated config dict (see ``load_config``).

    Returns:
        OOF panel ``[date, ticker, y_fwd_ret, score]`` (rows with a score only).
    """
    n_bins: int = cfg["rank_bins"]
    params = {**(cfg.get("frozen_params") or {}), "objective": cfg["objective"]}
    y_col = cfg.get("y_col", "y_fwd_ret")
    date_col = cfg.get("date_col", "date")

    scores = pd.Series(np.nan, index=panel.index, dtype=float, name="score")

    for sp in folds:
        train_df = panel.iloc[sp.train_idx]
        test_df = panel.iloc[sp.test_idx]
        if len(train_df) == 0 or len(test_df) == 0:
            continue

        # --- Train: frozen contract chain (binner fit on TRAIN fold only) ---
        train_returns = train_df[y_col].reset_index(drop=True)
        train_dates = pd.DatetimeIndex(
            pd.to_datetime(train_df[date_col].reset_index(drop=True))
        )
        train_groups = construct_month_groups(train_dates)
        fitted_bins = fit_monthly_bins(train_returns, train_groups, n_bins=n_bins)
        train_rel, _ = transform_to_relevance(
            train_returns, train_groups, fitted_bins, n_bins=n_bins
        )
        ret_clean, rel_clean, grp_clean = filter_valid_ranking_samples(
            train_returns, train_rel, train_groups
        )

        # Align features with the filtered samples and sort by group (ascending)
        # so query rows are consecutive for LightGBM; group sizes are re-derived
        # AFTER filtering (contract: group sizes == filtered row counts).
        valid_mask = train_returns.notna().to_numpy()
        tr_feat = train_df.iloc[np.flatnonzero(valid_mask)].reset_index(drop=True)
        sort_idx = np.argsort(grp_clean, kind="stable")
        tr_feat_sorted = tr_feat.iloc[sort_idx].reset_index(drop=True)
        rel_sorted = np.asarray(rel_clean)[sort_idx]
        grp_sorted = np.asarray(grp_clean)[sort_idx]
        group_sizes = get_group_sizes(grp_sorted)

        mdl = LightGBMFrozen(params)
        test_scores = mdl.fit_predict_rank(
            train=tr_feat_sorted,
            test=test_df,
            feature_cols=feature_cols,
            relevance=rel_sorted,
            group_sizes=group_sizes,
        )
        scores.iloc[sp.test_idx] = test_scores.to_numpy()

    oos = panel[[date_col, "ticker", y_col]].assign(score=scores.to_numpy())
    return oos.dropna(subset=["score"]).reset_index(drop=True)


def _scores_equal(a: pd.DataFrame, b: pd.DataFrame) -> bool:
    """Bit-identical raw score arrays, aligned by (date, ticker)."""
    sa = a.set_index(["date", "ticker"])["score"].sort_index()
    sb = b.set_index(["date", "ticker"])["score"].sort_index()
    if not sa.index.equals(sb.index):
        return False
    return bool(np.array_equal(sa.to_numpy(), sb.to_numpy()))


def main() -> None:
    cfg = load_config()
    sig = config_sig(cfg)
    print(
        f"[RES-03] config_sig={sig}  EXPLORATORY ONLY — no ledger row; "
        f"config_committed for BASELINE-RANK-001 requires owner authorization",
        flush=True,
    )

    from aionis.eval.two_arm import compute_shared_folds

    fund = pd.read_parquet(CACHE / "phase_b_fundamentals.parquet")
    px = pd.read_parquet(CACHE / "phase_b_prices.parquet")
    mem = load_pierrebrunelle_membership()

    # Shared folds (same evidence strength as frozen B/C/D/E1) + canonical layout.
    folds, ref = compute_shared_folds(px, mem, HORIZON, N_SPLITS, EMBARGO)
    panel = build_rank_panel(px, fund, mem, HORIZON, ALIGN_ON)
    layout = panel[["date", "ticker"]].reset_index(drop=True)
    if not layout.equals(ref):
        raise SystemExit("ABORT: panel layout diverges from shared-fold reference")
    print(f"[RES-03] panel={panel.shape} folds={len(folds)}", flush=True)

    feature_cols = cfg["feature_cols"]
    oos = run_rank_cv(panel, feature_cols, folds, cfg)
    ic = rank_ic_monthly(oos, "score", cfg["y_col"], cfg["date_col"])
    summary = rank_ic_summary(ic)
    print(
        f"[RES-03] rank-IC (CV-proxy): mean={summary['mean_ic']:.6f} "
        f"ci_half={summary['ci_half']:.6f} t_hac={summary['t_hac']:.4f} "
        f"p_hac={summary['p_hac']:.4f} n_months={summary['n']}",
        flush=True,
    )

    # H6 determinism: rerun -> bit-identical IC series AND raw scores.
    oos2 = run_rank_cv(panel, feature_cols, folds, cfg)
    ic2 = rank_ic_monthly(oos2, "score", cfg["y_col"], cfg["date_col"])
    det_ok = bool(
        np.array_equal(ic.to_numpy(), ic2.to_numpy()) and _scores_equal(oos, oos2)
    )
    print(f"[RES-03] H6 deterministic (IC + raw scores) = {det_ok}", flush=True)

    print(
        "[RES-03] DONE — exploratory CV-proxy only; no confirmatory headline, "
        "no ledger row, no runs/results artifacts",
        flush=True,
    )


if __name__ == "__main__":
    main()
