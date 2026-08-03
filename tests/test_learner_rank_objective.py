"""Hermetic tests for the RES-03 rank-aware learner branch (BASELINE-RANK-001).

All synthetic fixtures (no real data, no network, no ledger writes). Coverage:

1.  ``objective="lambdarank"`` model init + frozen-objective enforcement
    (the rank branch must go through ``ranking_contract.validate_objective``).
2.  Output shape / query-group structure (group sizes == filtered row counts).
3.  H6 determinism (seed=0 bit-identical reruns).
4.  Label contract: relevance in 1..5, NaN excluded, out-of-range clamp + reason
    codes (RD-15 decisions #2/#5/#6/#7, via the frozen contract chain).
5.  RD-15 §7 invariants in the learner-pipeline context (month-permutation /
    future-truncation / train-fold-only / group-size stability). Canonical
    unit-level versions live in ``tests/test_ranking_contract.py`` — these
    mirror them end-to-end through the chain ``scripts/res_03_baseline_rank_run.py``
    uses.
6.  ``config/baseline_rank_001.yaml`` parity with the frozen Phase B features +
    runner smoke.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from aionis.eval import learner as learner_mod
from aionis.eval.learner import FROZEN_PARAMS, LightGBMFrozen
from aionis.eval.rank_ic import rank_ic_monthly
from aionis.eval.ranking_contract import (
    RankingReasonCode,
    construct_month_groups,
    filter_valid_ranking_samples,
    fit_monthly_bins,
    get_group_sizes,
    transform_to_relevance,
    validate_objective,
)

CONFIG_PATH = Path("config/baseline_rank_001.yaml")
_FEATURES = ["x1", "x2"]


# ---------------------------------------------------------------------------
# Helpers (plain functions — synthetic fixtures only)
# ---------------------------------------------------------------------------


def _rank_frames() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Deterministic synthetic ranking data: train = 2 consecutive query groups
    of 60, test = 60. Group-sorted (consecutive) so ``group_sizes=[60, 60]`` is
    valid. Relevance (0..4) rises with x1, giving lambdarank a signal."""
    rng = np.random.default_rng(0)
    n = 60
    train_dates = [pd.Timestamp("2020-01-15")] * n + [pd.Timestamp("2020-02-15")] * n
    x1 = np.concatenate([rng.normal(size=n), rng.normal(size=n) + 0.5])
    x2 = rng.normal(size=2 * n)
    score = 0.6 * x1 - 0.2 * x2
    rel = np.digitize(score, np.quantile(score, [0.2, 0.4, 0.6, 0.8])).astype(np.int32)
    tr = pd.DataFrame({"date": train_dates, "x1": x1, "x2": x2, "rel": rel})
    te = pd.DataFrame(
        {
            "date": [pd.to_datetime("2020-03-15")] * n,
            "x1": rng.normal(size=n) + 0.25,
            "x2": rng.normal(size=n),
        }
    )
    return tr, te


def _panel_fixture(
    n_tickers: int = 24, n_months: int = 12, seed: int = 7
) -> pd.DataFrame:
    """Synthetic DAILY panel [date, ticker, x1, x2, y_fwd_ret] with a mild x1
    signal. Daily session density (~21 sessions/month) mirrors the real panel so
    the 21-session embargo leaves usable folds."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2023-01-02", periods=21 * n_months)
    rows: list[dict] = []
    for d in dates:
        for t in range(n_tickers):
            x1 = rng.normal()
            rows.append(
                {
                    "date": d,
                    "ticker": f"T{t:03d}",
                    "x1": x1,
                    "x2": rng.normal(),
                    "y_fwd_ret": 0.5 * x1 + 0.1 * rng.normal(),
                }
            )
    return pd.DataFrame(rows).sort_values(["date", "ticker"]).reset_index(drop=True)


def _folds_for(panel: pd.DataFrame, n_splits: int = 4) -> list:
    """PurgedGroupKFold folds on a synthetic panel (mirrors eval.two_arm
    ``_folds_from_panel``: group=calendar month, embargo=21 sessions)."""
    from aionis.eval.cv import purged_group_kfold_splits

    dates = pd.DatetimeIndex(sorted(panel["date"].unique()))
    pos = {d: i for i, d in enumerate(dates)}
    eval_dates = panel["date"].map(
        lambda d: dates[min(pos[d] + 21, len(dates) - 1)]
    )
    groups = panel["date"].dt.to_period("M").astype(str)
    embargo_td = pd.Timedelta(dates[21] - dates[0])
    return purged_group_kfold_splits(
        panel["date"], eval_dates, groups, n_splits=n_splits, embargo=embargo_td
    )


# ---------------------------------------------------------------------------
# 1. Model init + frozen objective enforcement
# ---------------------------------------------------------------------------


def test_rank_branch_init_objective_lambdarank() -> None:
    """objective='lambdarank' initializes; frozen params preserved."""
    mdl = LightGBMFrozen({**FROZEN_PARAMS, "objective": "lambdarank"})
    assert mdl.params["objective"] == "lambdarank"
    assert mdl.params["n_estimators"] == 500
    assert mdl.params["n_jobs"] == 1 and mdl.params["random_state"] == 0


def test_rank_branch_calls_frozen_validate_objective(monkeypatch: pytest.MonkeyPatch) -> None:
    """The rank branch must enforce the frozen RD-15 objective enum: it calls
    ``ranking_contract.validate_objective`` with 'lambdarank', and a rejection
    propagates (fail-fast — no free-form objective string)."""
    tr, te = _rank_frames()
    rel = tr["rel"].to_numpy(dtype=np.int32)
    group_sizes = np.array([60, 60], dtype=np.int32)

    calls: list[str] = []
    real = validate_objective

    def _spy(objective: str):
        calls.append(objective)
        return real(objective)

    monkeypatch.setattr(learner_mod, "validate_objective", _spy)
    s = LightGBMFrozen().fit_predict_rank(
        tr, te, _FEATURES, rel, group_sizes
    )
    assert calls == ["lambdarank"]
    assert len(s) == len(te)

    def _reject(objective: str):
        raise ValueError("Invalid ranking objective: rejected")

    monkeypatch.setattr(learner_mod, "validate_objective", _reject)
    with pytest.raises(ValueError, match="rejected"):
        LightGBMFrozen().fit_predict_rank(tr, te, _FEATURES, rel, group_sizes)


# ---------------------------------------------------------------------------
# 2. Output shape / query-group structure
# ---------------------------------------------------------------------------


def test_fit_predict_rank_shape_and_group_structure() -> None:
    """Scores: len == len(test), index == test index, finite; group sizes sum to
    the train row count (the contract's group-size == row-count invariant)."""
    tr, te = _rank_frames()
    rel = tr["rel"].to_numpy(dtype=np.int32)
    group_sizes = np.array([60, 60], dtype=np.int32)
    assert int(group_sizes.sum()) == len(tr)

    s = LightGBMFrozen().fit_predict_rank(tr, te, _FEATURES, rel, group_sizes)
    assert len(s) == len(te)
    assert s.index.equals(te.index)
    assert np.isfinite(s.to_numpy()).all()


def test_fit_predict_rank_picks_up_signal() -> None:
    """Scores correlate with the relevance driver (x1) — the rank objective learns."""
    tr, te = _rank_frames()
    rel = tr["rel"].to_numpy(dtype=np.int32)
    s = LightGBMFrozen().fit_predict_rank(
        tr, te, _FEATURES, rel, np.array([60, 60], dtype=np.int32)
    )
    corr = np.corrcoef(s.to_numpy(), te["x1"].to_numpy())[0, 1]
    assert corr > 0.3


# ---------------------------------------------------------------------------
# 3. H6 determinism
# ---------------------------------------------------------------------------


def test_fit_predict_rank_h6_deterministic() -> None:
    """H6 foundation for the rank branch: same data -> bit-identical scores."""
    tr, te = _rank_frames()
    rel = tr["rel"].to_numpy(dtype=np.int32)
    group_sizes = np.array([60, 60], dtype=np.int32)
    mdl = LightGBMFrozen()
    s1 = mdl.fit_predict_rank(tr, te, _FEATURES, rel, group_sizes)
    s2 = mdl.fit_predict_rank(tr, te, _FEATURES, rel, group_sizes)
    np.testing.assert_array_equal(s1.to_numpy(), s2.to_numpy())


# ---------------------------------------------------------------------------
# 4. Label contract (RD-15 #2/#5/#6/#7 via the frozen contract chain)
# ---------------------------------------------------------------------------


def test_label_contract_relevance_bounds_nan_exclusion() -> None:
    """Contract: relevance in 1..5; NaN forward return -> -1 + RETURN_MISSING and
    EXCLUDED; group sizes re-derived after filtering == filtered row count."""
    dates = pd.to_datetime(["2020-01-15"] * 5 + ["2020-02-15"] * 5)
    returns = pd.Series([0.01, 0.02, np.nan, 0.04, 0.05, -0.02, -0.01, 0.00, 0.01, 0.02])
    groups = construct_month_groups(dates)

    valid_mask = returns.notna().to_numpy()
    fitted_bins = fit_monthly_bins(returns[valid_mask], groups[valid_mask], n_bins=5)
    relevance, reason_codes = transform_to_relevance(
        returns, groups, fitted_bins, n_bins=5
    )

    nan_idx = int(np.flatnonzero(~valid_mask)[0])
    assert relevance[nan_idx] == -1
    assert reason_codes[nan_idx] == RankingReasonCode.RETURN_MISSING.value

    valid = relevance != -1
    assert np.all(relevance[valid] >= 1)
    assert np.all(relevance[valid] <= 5)

    ret_c, rel_c, grp_c = filter_valid_ranking_samples(returns, relevance, groups)
    assert len(ret_c) == len(returns) - 1  # NaN sample excluded
    assert np.all(rel_c >= 1) and np.all(rel_c <= 5)
    assert int(np.sum(get_group_sizes(grp_c))) == len(grp_c)  # sizes == rows


def test_label_contract_out_of_range_clamp_reason_codes() -> None:
    """Contract: test returns outside train-fold range clamp to bin 1 / n_bins with
    reason codes (oor_low / oor_high); unseen months use pooled edges
    (unseen_pooled); bins are NEVER refit."""
    train_dates = pd.to_datetime(["2020-01-15"] * 5)
    train_returns = pd.Series([0.01, 0.02, 0.03, 0.04, 0.05])
    train_groups = construct_month_groups(train_dates)
    fitted_bins = fit_monthly_bins(train_returns, train_groups, n_bins=5)
    frozen_copy = {k: v.copy() for k, v in fitted_bins.items()}

    test_dates = pd.to_datetime(["2020-01-15"] * 3)
    test_returns = pd.Series([-0.10, 0.03, 0.20])
    test_groups = construct_month_groups(test_dates)
    relevance, reason_codes = transform_to_relevance(
        test_returns, test_groups, fitted_bins, n_bins=5
    )

    assert relevance[0] == 1
    assert reason_codes[0] == RankingReasonCode.OUT_OF_RANGE_LOW.value
    assert relevance[2] == 5
    assert reason_codes[2] == RankingReasonCode.OUT_OF_RANGE_HIGH.value
    assert reason_codes[1] == RankingReasonCode.NORMAL.value

    # Unseen month -> pooled edges + reason code
    unseen_dates = pd.to_datetime(["2020-03-15"] * 2)
    unseen_returns = pd.Series([0.015, 0.045])
    unseen_groups = construct_month_groups(unseen_dates)
    rel_u, rc_u = transform_to_relevance(
        unseen_returns, unseen_groups, fitted_bins, n_bins=5
    )
    assert np.all(rel_u >= 1) and np.all(rel_u <= 5)
    assert all(r == RankingReasonCode.UNSEEN_MONTH_POOLED.value for r in rc_u)

    # Frozen edges untouched by any transform (no refit anywhere)
    for m in frozen_copy:
        np.testing.assert_allclose(fitted_bins[m], frozen_copy[m], rtol=1e-10)


# ---------------------------------------------------------------------------
# 5. RD-15 §7 invariants in the learner-pipeline context
#    (canonical unit-level versions: tests/test_ranking_contract.py)
# ---------------------------------------------------------------------------


def test_invariant_month_permutation_pipeline() -> None:
    """I1: permuting row order does not change per-month bin edges."""
    dates = pd.to_datetime(["2020-01-15"] * 4 + ["2020-02-15"] * 4 + ["2020-03-15"] * 4)
    returns = pd.Series(np.linspace(-0.06, 0.06, 12))
    groups = construct_month_groups(dates)

    bins_original = fit_monthly_bins(returns, groups, n_bins=5)
    rng = np.random.default_rng(0)
    perm = rng.permutation(len(returns))
    bins_permuted = fit_monthly_bins(returns.iloc[perm], groups[perm], n_bins=5)

    assert set(bins_original) == set(bins_permuted)
    for month_id in bins_original:
        np.testing.assert_allclose(
            bins_original[month_id], bins_permuted[month_id], rtol=1e-10
        )


def test_invariant_future_truncation_pipeline() -> None:
    """I2: removing future months does not change past months' bin edges."""
    dates = pd.to_datetime(
        ["2020-01-15", "2020-01-15", "2020-02-15", "2020-02-15",
         "2020-03-15", "2020-03-15", "2020-04-15", "2020-04-15"]
    )
    returns = pd.Series([0.01, 0.05, -0.02, 0.02, 0.10, 0.30, 0.15, 0.25])
    groups = construct_month_groups(dates)

    bins_full = fit_monthly_bins(returns, groups, n_bins=5)
    trunc = groups <= groups.max() - 2  # drop the last 2 months
    bins_trunc = fit_monthly_bins(returns[trunc], groups[trunc], n_bins=5)

    for month_id in bins_trunc:
        np.testing.assert_allclose(
            bins_full[month_id], bins_trunc[month_id], rtol=1e-10
        )
    assert len(bins_trunc) < len(bins_full)


def test_invariant_train_fold_only_fitting_pipeline() -> None:
    """I3: transform_to_relevance NEVER refits — extreme test data leaves the
    train-fit bin edges bit-identical."""
    train_dates = pd.to_datetime(["2020-01-15"] * 5)
    train_returns = pd.Series([0.01, 0.02, 0.03, 0.04, 0.05])
    train_groups = construct_month_groups(train_dates)
    fitted_bins = fit_monthly_bins(train_returns, train_groups, n_bins=5)
    frozen_copy = {k: v.copy() for k, v in fitted_bins.items()}

    extreme = pd.Series([-100.0, 100.0])
    extreme_groups = np.array([24240, 24240])
    relevance, reason_codes = transform_to_relevance(
        extreme, extreme_groups, fitted_bins, n_bins=5
    )
    assert relevance[0] == 1 and relevance[1] == 5
    assert reason_codes[0] == RankingReasonCode.OUT_OF_RANGE_LOW.value
    assert reason_codes[1] == RankingReasonCode.OUT_OF_RANGE_HIGH.value

    for month_id in frozen_copy:
        np.testing.assert_allclose(
            fitted_bins[month_id], frozen_copy[month_id], rtol=1e-10
        )


def test_invariant_group_size_stability_pipeline() -> None:
    """I4: filtering NaN returns updates group sizes; no group grows."""
    dates = pd.to_datetime(
        ["2020-01-15"] * 5 + ["2020-02-15"] * 3
    )
    returns = pd.Series([0.01, np.nan, 0.03, 0.04, 0.05, np.nan, 0.02, 0.08])
    groups = construct_month_groups(dates)

    valid_mask = returns.notna().to_numpy()
    fitted_bins = fit_monthly_bins(returns[valid_mask], groups[valid_mask], n_bins=5)
    relevance, _ = transform_to_relevance(returns, groups, fitted_bins, n_bins=5)

    _, counts_before = np.unique(groups, return_counts=True)
    ret_c, rel_c, grp_c = filter_valid_ranking_samples(returns, relevance, groups)
    _, counts_after = np.unique(grp_c, return_counts=True)

    assert np.all(counts_after <= counts_before)
    assert len(grp_c) < len(groups)
    assert int(np.sum(get_group_sizes(grp_c))) == len(grp_c)
    assert np.all(rel_c >= 1) and np.all(rel_c <= 5)


# ---------------------------------------------------------------------------
# 6. Config parity + runner smoke
# ---------------------------------------------------------------------------


def test_config_contract_objective_bins_features() -> None:
    """config/baseline_rank_001.yaml: objective='lambdarank', rank_bins=5,
    feature_cols IDENTICAL to the frozen Phase B runner, H6 pins intact."""
    from scripts.phase_b_run import FEATURE_COLS as FROZEN_B_FEATURE_COLS
    from scripts.res_03_baseline_rank_run import load_config

    cfg = load_config(CONFIG_PATH)
    assert cfg["objective"] == "lambdarank"
    assert cfg["rank_bins"] == 5
    assert validate_objective(cfg["objective"]).value == "lambdarank"
    assert cfg["feature_cols"] == FROZEN_B_FEATURE_COLS
    assert cfg["frozen_params"]["n_jobs"] == 1
    assert cfg["frozen_params"]["random_state"] == 0


def test_config_rejects_contract_violations(tmp_path: Path) -> None:
    """load_config is fail-fast on contract violations (frozen enum / bin count)."""
    from scripts.res_03_baseline_rank_run import load_config

    bad_objective = {"objective": "regression", "rank_bins": 5, "feature_cols": ["x"]}
    p = tmp_path / "bad.yaml"
    import yaml

    p.write_text(yaml.safe_dump(bad_objective), encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid ranking objective"):
        load_config(p)

    bad_bins = {"objective": "lambdarank", "rank_bins": 3, "feature_cols": ["x"]}
    p.write_text(yaml.safe_dump(bad_bins), encoding="utf-8")
    with pytest.raises(ValueError, match="rank_bins must be 5 or 10"):
        load_config(p)


def test_runner_module_importable() -> None:
    """The RES-03 runner imports cleanly (no real-data side effects at import)."""
    import scripts.res_03_baseline_rank_run as runner

    assert callable(runner.main)
    assert callable(runner.load_config)
    assert callable(runner.run_rank_cv)
    assert callable(runner.build_rank_panel)
    assert callable(runner.config_sig)


def test_run_rank_cv_end_to_end_synthetic() -> None:
    """Hermetic smoke of the runner's purged CV loop on a synthetic panel: OOF
    scores finite, non-empty, and a monthly rank-IC series emerges."""
    from scripts.res_03_baseline_rank_run import run_rank_cv

    panel = _panel_fixture(n_tickers=24, n_months=12, seed=7)
    folds = _folds_for(panel, n_splits=4)
    assert len(folds) >= 3  # usable purged splits on daily synthetic data

    cfg = {
        "rank_bins": 5,
        "objective": "lambdarank",
        "y_col": "y_fwd_ret",
        "date_col": "date",
        "frozen_params": {"n_estimators": 50},
    }
    oos = run_rank_cv(panel, ["x1", "x2"], folds, cfg)

    assert len(oos) > 0
    assert np.isfinite(oos["score"].to_numpy()).all()
    assert {"date", "ticker", "y_fwd_ret", "score"} <= set(oos.columns)

    ic = rank_ic_monthly(oos, "score", "y_fwd_ret", "date")
    assert len(ic) > 0
