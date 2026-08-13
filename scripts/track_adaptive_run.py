#!/usr/bin/env python3
"""Track Adaptive weekly runner — truly-frozen vs expanding-window weekly refit.

Implements the FROZEN Track Adaptive config #52 (sig
ffd0c9227e692fe826faeac964607577f3a9ff3de3384907297bc396887c4659). Two arms
sharing one frozen-train binner (leakage-safe — binner fit only on the frozen
train window, applied to all):
  - frozen:   LightGBM lambdarank fit ONCE on 2016-2020 weekly rows, predict all
              OOS weeks. NEVER refit (the "truly-frozen" baseline).
  - expanding: at each OOS week's close, refit lambdarank on realized rows
              (date <= week_close − embargo sessions, 5-session forward realized),
              predict that week.

Estimand: IC_diff_weekly = IC_adaptive − IC_frozen, paired per week, HAC
(Newey-West), two-tailed, null-expected. DSR (n_trials=1) reported. H6 = run
twice, assert bit-identical IC series.

Anti-leakage (the load-bearing parts):
  - fwd_5s computed from daily close (shift −5 sessions); realized only where the
    +5 session exists + is strictly before the predict point.
  - embargo: train rows with date <= predict_week_close − 5 sessions (session
    index from the DAILY panel, so holiday weeks are handled exactly).
  - binner: global 5-quantile edges fit on FROZEN-train fwd_5s ONLY; both arms
    transform with these same frozen edges (no per-arm refit of the binner).
  - frozen arm: fit only on rows with date <= 2020-12-31; OOS rows never enter.

Outputs (gitignored): runs/track_adaptive_*.parquet + summary.json. The first
OOS metric lands in a NEW ledger row (not this script).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import norm

from aionis.eval.deflated_sharpe import deflated_sharpe_ratio
from aionis.eval.learner import LightGBMFrozen
from aionis.eval.rank_ic import rank_ic_by_date

# amend2 #53 (n_estimators=100)
FROZEN_SIG = (
    "b7621e6b089bb8c3d0a692d671c8446eec23b16e48b709efc51dc9b97a632116"
)
PANEL = Path("data/cache/track_b_panel.parquet")
OUT_DIR = Path("runs")

# Daily per-stock features (cross-sectionally varying). Macro levels (cpi/payems/
# vix) are cross-sectionally constant → excluded (carry no rank signal). Close is
# the price used to build fwd_5s, not a feature. fwd_5s is the label.
FEATURES: list[str] = [
    "momentum_5d",
    "momentum_10d",
    "momentum_21d",
    "momentum_42d",
    "reversal_5d",
    "volatility_21d",
    "volatility_63d",
    "turnover_21d",
    "beta_252d",
    "amihud_illiquidity_21d",
    "accruals",
    "asset_growth_12m",
    "asset_growth_1m",
    "book_value_per_share",
    "debt_to_equity",
    "equity_growth_1m",
    "investment_12m",
    "leverage",
    "profit_margin",
    "revenue_growth_12m",
    "revenue_growth_1m",
    "roa",
    "roe",
]
FWD_H = 5  # sessions (1 trading week)
EMBARGO = 5  # sessions — train rows must realize (date+5 <= predict point)
TRAIN_END = "2020-12-31"  # frozen-train window end (inclusive)
OOS_START = "2021-01-01"
MIN_TRAIN_ROWS = 5000  # min realized train rows for a stable weekly refit

_FROZEN_LGBM = {
    "n_estimators": 100,  # amend2: 500→100 for feasibility (~5min vs ~27min); both arms
    "learning_rate": 0.05,
    "num_leaves": 31,
    "min_child_samples": 20,
    "reg_lambda": 1.0,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 1,
    "n_jobs": 1,
    "random_state": 0,
    "verbose": -1,
}


def weekly_reduce(daily: pd.DataFrame) -> pd.DataFrame:
    """Daily panel → weekly-close rows + 5-session forward return + week_id.

    Weekly close = last trading session of each ISO week. fwd_5s is computed on
    the DAILY series first (shift −5 sessions) so it is a true 5-session return,
    then the weekly close carries its already-realized-or-not fwd_5s.
    """
    d = daily.copy()
    d["date"] = pd.to_datetime(d["date"])
    d = d.sort_values(["ticker", "date"])
    d["fwd_5s"] = d.groupby("ticker")["close"].shift(-FWD_H) / d["close"] - 1.0
    iso = d["date"].dt.isocalendar()
    d["week_id"] = iso["year"].astype(int) * 100 + iso["week"].astype(int)
    last_in_week = d.groupby("week_id")["date"].transform("max")
    return d[d["date"] == last_in_week].sort_values(["week_id", "ticker"]).reset_index(drop=True)


def fit_binner(fwd: pd.Series, n_bins: int = 5) -> np.ndarray:
    """Global n-quantile edges on the frozen-train fwd_5s (leakage-safe)."""
    finite = fwd.dropna().to_numpy(dtype=float)
    edges = np.quantile(finite, np.linspace(0.0, 1.0, n_bins + 1))
    return np.unique(edges)


def to_relevance(fwd: np.ndarray, edges: np.ndarray) -> np.ndarray:
    """Map fwd → integer relevance 0..(n_bins-1) via frozen edges."""
    return np.digitize(np.asarray(fwd, dtype=float), edges[1:-1], right=False)


def week_group_sizes(week_ids: np.ndarray) -> np.ndarray:
    """Lambdarank query-group sizes (consecutive same-week rows, train-sorted)."""
    _, counts = np.unique(week_ids, return_counts=True)
    return counts.astype(np.int32)


def _arm_scores_to_ic(scored: pd.DataFrame) -> pd.Series:
    """Per-week Spearman(score, fwd_5s) — the weekly IC series."""
    return rank_ic_by_date(scored, score_col="score", y_col="fwd_5s", date_col="date")


def run_frozen_arm(
    weekly: pd.DataFrame,
    train_end: str,
    features: list[str],
    edges: np.ndarray,
) -> pd.DataFrame:
    """Fit lambdarank ONCE on rows date <= train_end; predict ALL OOS weeks."""
    train = (
        weekly[weekly["date"] <= pd.Timestamp(train_end)]
        .dropna(subset=["fwd_5s"])
        .sort_values(["week_id", "ticker"])
    )
    rel = to_relevance(train["fwd_5s"].to_numpy(), edges)
    groups = week_group_sizes(train["week_id"].to_numpy())
    oos = weekly[weekly["date"] > pd.Timestamp(train_end)].sort_values(["week_id", "ticker"])
    model = LightGBMFrozen(_FROZEN_LGBM)
    oos = oos.assign(score=model.fit_predict_rank(train, oos, features, rel, groups).to_numpy())
    return oos[["date", "ticker", "score", "fwd_5s"]]


def _refit_one_week(
    t_w: pd.Timestamp,
    weekly: pd.DataFrame,
    sess_list: pd.DatetimeIndex,
    features: list[str],
    edges: np.ndarray,
    embargo: int,
) -> pd.DataFrame | None:
    """Refit lambdarank on realized rows (date <= t_w − embargo), predict week t_w.

    Extracted so joblib can parallelize the per-week refits across cores. Each
    refit is independent + deterministic (n_jobs=1 LightGBM, seed=0), so running
    weeks concurrently yields identical per-week scores to sequential (H6 holds).
    """
    idx_t = sess_list.get_loc(pd.Timestamp(t_w))
    cutoff = sess_list[max(idx_t - embargo, 0)]  # embargo sessions before predict
    train = weekly[weekly["date"] <= cutoff].dropna(subset=["fwd_5s"])
    if len(train) < MIN_TRAIN_ROWS:
        return None
    train = train.sort_values(["week_id", "ticker"])
    rel = to_relevance(train["fwd_5s"].to_numpy(), edges)
    groups = week_group_sizes(train["week_id"].to_numpy())
    test = weekly[weekly["date"] == pd.Timestamp(t_w)].sort_values("ticker")
    model = LightGBMFrozen(_FROZEN_LGBM)
    test = test.assign(
        score=model.fit_predict_rank(train, test, features, rel, groups).to_numpy()
    )
    return test[["date", "ticker", "score", "fwd_5s"]]


def run_expanding_arm(
    weekly: pd.DataFrame,
    daily_sessions: np.ndarray,
    features: list[str],
    edges: np.ndarray,
    embargo: int = EMBARGO,
    n_jobs: int = 1,
) -> pd.DataFrame:
    """Each OOS week: refit on realized rows (date <= week_close − embargo), predict.

    SEQUENTIAL (n_jobs=1) by default — reliable. n_jobs>1 (threading) crashed
    repeatedly via a LightGBM concurrency race (silent segfault, no traceback),
    independent of memory; the original sequential 500-tree run was stable for
    15+ min. Per-week refits are independent + deterministic (H6 holds); the
    ``Parallel`` wrapper is kept so n_jobs can be raised on a host where the
    race does not trigger.
    """
    oos_dates = sorted(weekly.loc[weekly["date"] > pd.Timestamp(OOS_START), "date"].unique())
    sess_list = pd.DatetimeIndex(daily_sessions)
    results = Parallel(n_jobs=n_jobs, backend="threading")(
        delayed(_refit_one_week)(t_w, weekly, sess_list, features, edges, embargo)
        for t_w in oos_dates
    )
    out = [r for r in results if r is not None]
    return (
        pd.concat(out, ignore_index=True)
        if out
        else pd.DataFrame(columns=["date", "ticker", "score", "fwd_5s"])
    )


def hac_mean(series: pd.Series, maxlag: int | None = None) -> dict:
    """Newey-West HAC mean + SE + two-tailed p of a (paired-diff) series."""
    s = pd.Series(series).dropna().to_numpy(dtype=float)
    n = len(s)
    if n < 5:
        return {
            "mean": float("nan"),
            "se": float("nan"),
            "t": float("nan"),
            "p": float("nan"),
            "n": n,
        }
    x = s - s.mean()
    if maxlag is None:
        maxlag = max(1, int(4 * (n / 100.0) ** (2 / 9)))
    lag_var = 0.0
    for lag in range(1, maxlag + 1):
        w = 1 - lag / (maxlag + 1)
        lag_var += w * np.sum(x[lag:] * x[:-lag]) / n
    var = np.sum(x**2) / n + 2 * lag_var
    se = float(np.sqrt(max(var, 1e-30) / n))
    mean = float(s.mean())
    t = mean / se
    p = float(2 * (1 - norm.cdf(abs(t))))
    return {"mean": round(mean, 6), "se": round(se, 6), "t": round(t, 4), "p": round(p, 4), "n": n}


def main() -> int:
    daily = pd.read_parquet(PANEL)
    daily_sessions = np.sort(pd.to_datetime(daily["date"]).unique())
    weekly = weekly_reduce(daily)

    train = weekly[weekly["date"] <= pd.Timestamp(TRAIN_END)]
    edges = fit_binner(train["fwd_5s"])
    print(
        f"[track_adaptive] weekly rows={len(weekly)} OOS weeks="
        f"{(weekly['date'] > pd.Timestamp(TRAIN_END)).sum()} bins={len(edges) - 1}",
        flush=True,
    )

    frozen_oos = run_frozen_arm(weekly, TRAIN_END, FEATURES, edges)
    ic_frozen = _arm_scores_to_ic(frozen_oos)
    print(f"[track_adaptive] frozen IC mean={ic_frozen.mean():.4f} n={len(ic_frozen)}", flush=True)

    expanding_oos = run_expanding_arm(weekly, daily_sessions, FEATURES, edges)
    ic_adaptive = _arm_scores_to_ic(expanding_oos)
    print(
        f"[track_adaptive] expanding IC mean={ic_adaptive.mean():.4f} n={len(ic_adaptive)}",
        flush=True,
    )

    # Paired weekly diff (intersect on date).
    diff = pd.concat([ic_adaptive.rename("adp"), ic_frozen.rename("frz")], axis=1).dropna()
    diff_series = (diff["adp"] - diff["frz"]).rename("ic_diff")
    hac = hac_mean(diff_series)
    dsr = deflated_sharpe_ratio(
        observed_sharpe=hac["mean"] / hac["se"] if hac["se"] else 0.0,
        n_trials=1,
        n_obs=hac["n"],
    )
    summary = {
        "frozen_config_sig": FROZEN_SIG,
        "estimand": "IC_diff_weekly = IC_adaptive - IC_frozen (paired, HAC two-tailed)",
        "ic_frozen_mean": round(float(ic_frozen.mean()), 6),
        "ic_adaptive_mean": round(float(ic_adaptive.mean()), 6),
        "ic_diff_hac": hac,
        "dsr_n1": round(float(dsr), 4),
        "n_oos_weeks_frozen": int(len(ic_frozen)),
        "n_oos_weeks_adaptive": int(len(ic_adaptive)),
        "n_paired_weeks": int(len(diff)),
        "honest_note": "null-expected (weekly IC noisier than monthly; power floor)",
    }
    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "track_adaptive_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    ic_frozen.rename("frozen").to_frame().to_parquet(OUT_DIR / "track_adaptive_ic_frozen.parquet")
    ic_adaptive.rename("adaptive").to_frame().to_parquet(
        OUT_DIR / "track_adaptive_ic_adaptive.parquet"
    )
    print(
        f"[track_adaptive] IC_diff mean={hac['mean']} p={hac['p']} "
        f"n={hac['n']} DSR(n1)={summary['dsr_n1']}",
        flush=True,
    )
    print(
        "[track_adaptive] wrote runs/track_adaptive_"
        "{summary.json,ic_frozen.parquet,ic_adaptive.parquet}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
