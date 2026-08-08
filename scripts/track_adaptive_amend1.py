#!/usr/bin/env python3
"""Track Adaptive amendment #1 (amend1) — WEEKLY cadence + truly-frozen baseline.

Supersedes ledger #51 (sig 892fb506…): that config froze mechanism A = monthly
expanding-window refit, but investigation showed Track C's "frozen baseline" is
ITSELF an expanding-window monthly refit (each fold test = 1 month, refit on the
growing past). So #51's estimand (adaptive-monthly vs Track-C-monthly) is
redundant → IC_diff ≈ 0 by construction, meaningless. #51 stays in the ledger
(append-only) as the superseded record.

amend1 (owner 2026-08-08: "选择①, 时间改为一周, 周收盘后") makes the comparison
MEANINGFUL + weekly:
  - baseline = TRULY-FROZEN single LightGBM fit (fit once on the initial weekly
    training window, NEVER refit) — distinct from Track C, which always refits.
  - treatment = expanding-window WEEKLY refit (each week, right after the weekly
    close, refit on all realized data with a 5-session embargo).
  - estimand = weekly cross-sectional rank-IC diff (5-session forward return),
    HAC, two-tailed, null-expected.

Scope constraints (feasibility): US-only — the daily ``track_b_panel`` is US S&P
500 (the CN panel is month-end, cannot do weekly without re-fetching daily CN
prices). Substrate = the daily panel's available features (price + fundamentals +
raw macro); Track C's regime composite is month-end → excluded at weekly.

Default = DRY-RUN; ``--commit`` appends the irreversible row. Observes NO OOS.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

LEDGER = Path(__file__).resolve().parent.parent / "runs" / "ledger.jsonl"
PHASE = "track_adaptive"

_FROZEN_LGBM = {
    "n_estimators": 500,
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

TRACK_ADAPTIVE_CONFIG: dict = {
    "track": "adaptive",
    "amendment": (
        "amend1: WEEKLY cadence + truly-frozen baseline. Supersedes #51 "
        "(monthly-A, redundant with Track C)."
    ),
    "supersedes": {
        "ledger_row": 51,
        "sig": "892fb5068ed1e994db937e23c5b95f2d35ea796825c0c97937253e34605515ad",
        "reason": (
            "mechanism A (monthly expanding refit) == Track C estimator (each "
            "fold test = 1 month, refit on growing past) -> IC_diff ~ 0 by "
            "construction, meaningless. amend1 makes baseline truly-frozen + "
            "cadence weekly."
        ),
    },
    "claim": (
        "two-tailed, null-expected: does WEEKLY expanding-window refit change "
        "WEEKLY cross-sectional rank-IC vs a TRULY-FROZEN single-fit baseline? "
        "IC_diff = mean(IC_adaptive_w) - mean(IC_frozen_w), paired per week, "
        "HAC, two-tailed. Track C never had a truly-frozen baseline, so this "
        "is a genuinely new comparison ('does learning from new data help')."
    ),
    "estimand": {
        "name": "IC_diff_weekly",
        "definition": (
            "mean over OOS weeks of (IC_adaptive_w - IC_frozen_w), paired per "
            "week; IC = cross-sectional Spearman(score, 5-session forward return)"
        ),
        "inference": "HAC (Newey-West) regression d_w ~ 1; two-tailed",
        "baseline": (
            "TRULY-FROZEN: LightGBM lambdarank fit ONCE on the initial weekly "
            "training window (2016-01..2020-12), NEVER refit, applied to ALL "
            "OOS weeks. The binner (rank bins) is also frozen from this single "
            "fit. Distinct from Track C (which refits monthly)."
        ),
        "treatment": (
            "expanding-window WEEKLY refit: at each OOS week's close (last "
            "trading session of the week), refit LightGBM on all realized data "
            "with date < week_close, 5-session embargo, predict the next week."
        ),
    },
    "cadence": (
        "WEEKLY — refit at each week's close (owner 2026-08-08: '周收盘后')"
    ),
    "universe": (
        "US S&P 500 PIT (ticker x date baked into the daily track_b_panel; "
        "window 2016-01-01+). US-only: the CN panel is month-end."
    ),
    "feature_cols": (
        "daily-available features from track_b_panel (price: momentum_5/10/21/42d,"
        " reversal_5d, volatility_21/63d, turnover_21d, beta_252d, "
        "amihud_illiquidity_21d; fundamentals: roa/roe/profit_margin/asset_growth"
        "/revenue_growth/equity_growth/leverage/debt_to_equity/book_value_per_share"
        "/accruals/investment_12m; raw macro: cpi/payems/vix). Track C's regime "
        "composite is month-end -> excluded at weekly. ZERO outcome-based selection."
    ),
    "learner": {
        "objective": "lambdarank",
        "bin_count": 5,
        "params": _FROZEN_LGBM,
    },
    "validation": {
        "method": "weekly walk-forward; truly-frozen baseline vs expanding-refit",
        "frozen_train_window": "2016-01-01..2020-12-31 (weekly; ~260 weeks)",
        "oos_window": "2021-01..2026-06 (weekly; ~286 weeks)",
        "forward_horizon_sessions": 5,
        "embargo_sessions": 5,
        "sampling": "last trading session of each week (weekly close)",
        "chronological_assert": "fit.max(date) < predict.week_close, 5-session embargo",
    },
    "sesoi_diff": 0.010,
    "gates": {
        "primary": (
            "two-tailed HAC p-value on mean(IC_diff_weekly); alpha=0.05; "
            "expected NOT to reject H0 (null)"
        ),
        "secondary_equivalence": (
            "RCI of IC_diff_weekly within +/-sesoi_diff (examined only if "
            "primary null); NOT a rescue path"
        ),
    },
    "n_trials": 1,
    "n_trials_note": (
        "ONE strategy (weekly expanding refit, frozen hyperparams, no sweep). "
        "Refit cycles are the OOS walk-forward of one strategy, not independent "
        "trials. Bumping requires a new ledger row."
    ),
    "multiplicity": {
        "dsr": "deflated_sharpe.deflated_sharpe_ratio (Bailey-Lopez de Prado 2014)",
        "pbo": "deflated_sharpe.probability_of_backtest_overfit (CSCV); reported",
        "rule": "observed IC improvement reported RAW and DEFLATED; deflated is claim-bearing",
    },
    "h6_determinism": {
        "n_jobs": 1,
        "seed": 0,
        "version_pinned": "uv.lock",
        "assert": "IC_adaptive weekly series + raw scores bit-identical across reruns",
    },
    "frozen_surface_isolation": (
        "new prereg line; NEVER mutates Track C / B(seven-theme) / D / E1 frozen "
        "configs or ledger rows; Track-C climax (#49, monthly null) stands unchanged"
    ),
    "honest_expectation": (
        "null. Weekly IC is noisier than monthly (5-session horizon); power floor "
        "applies. Value = disciplined adaptive infrastructure + leakage-safe "
        "honest tracking, NOT manufacturing positive IC. A null IC_diff_weekly is "
        "a second independent null reinforcing the power-floor conclusion."
    ),
}


def config_sig(config: dict) -> str:
    return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()


def build_row(config: dict) -> dict:
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": "config_committed",
        "phase": PHASE,
        "config_sig": config_sig(config),
        "config": config,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--commit", action="store_true", help="append the row (default: dry-run)")
    args = ap.parse_args()

    row = build_row(TRACK_ADAPTIVE_CONFIG)
    print(f"[track_adaptive amend1] config_sig={row['config_sig']}")
    print(f"[track_adaptive amend1] phase={row['phase']} event={row['event']} ledger={LEDGER}")
    print(f"[track_adaptive amend1] config keys={sorted(TRACK_ADAPTIVE_CONFIG.keys())}")
    preview = {k: row[k] for k in ("ts", "event", "phase", "config_sig")}
    print(f"[track_adaptive amend1] row preview: {json.dumps(preview)}")

    if not args.commit:
        print("[track_adaptive amend1] DRY-RUN (no append). Re-run with --commit to freeze.")
        return 0

    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")
    print(f"[track_adaptive amend1] COMMITTED -> {LEDGER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
