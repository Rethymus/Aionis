#!/usr/bin/env python3
"""Track C config_committed freeze (HIGH-1 anti-leakage anchor).

Writes the Track C frozen config's sha256 to ``runs/ledger.jsonl`` BEFORE any
OOS rank-IC is observed (CLAUDE.md: config_committed BEFORE result). Mirrors the
tested ``commit_config`` mechanism in ``scripts/phase_b_run.py`` /
``src/aionis/eval/phase_c.py`` (sig = sha256(json.dumps(config, sort_keys=True))).

Default = DRY-RUN (prints row + sig, no append). ``--commit`` appends the
irreversible row. This script observes NO OOS metric, fetches NO data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

LEDGER = Path(__file__).resolve().parent.parent / "runs" / "ledger.jsonl"
PHASE = "track_c"

# LightGBM frozen params (identical to Phase B / Track B frozen family).
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

TRACK_C_CONFIG: dict = {
    "track": "C",
    "claim": (
        "dual-region (US S&P500 + CN CSI300) cross-sectional monthly rank-IC; "
        "single pre-specified interaction score x regime_state (multiplicity "
        "budget 1, NOT K post-hoc subgroups); null-favored"
    ),
    "universe": {
        "us": {
            "source": "hanshof/sp500_constituents (MIT)",
            "cross_check": "pierrebrunelle/sp500-historical-constituents (MIT)",
            "window_start": "2016-01-01",
            "headline_rule": (
                "monthly Jaccard >= 0.95 else restrict window "
                "(Track B measured min 0.8544 @ 2016-01-01 -> 2016+)"
            ),
        },
        "cn": {
            "source": "index-constitution (MIT)",
            "index": "CSI300",
            "window_start": "2016-01-01",
        },
    },
    "feature_cols": {
        "us_fundamentals_13": [
            "roa", "roe", "profit_margin", "asset_growth_1m", "asset_growth_12m",
            "revenue_growth_1m", "revenue_growth_12m", "equity_growth_1m",
            "leverage", "debt_to_equity", "book_value_per_share", "accruals",
            "investment_12m",
        ],
        "us_price_10": [
            "momentum_5d", "momentum_10d", "momentum_21d", "momentum_42d",
            "reversal_5d", "volatility_21d", "volatility_63d", "turnover_21d",
            "beta_252d", "amihud_illiquidity_21d",
        ],
        "cn_fundamentals_13": (
            "mirror us_fundamentals_13 via cninfo as-filed PDF (rollysys/use_cninfo "
            "MIT fetch + Aionis self-built PyMuPDF parse), filed-date PIT"
        ),
        "cn_price_12": (
            "mirror us_price_10 + limit_up_down_distance + suspension_flag; "
            "baostock (MIT) or qlib+AKShare collector (MIT 83d089b)"
        ),
        "macro_headline_6": {
            "us": ["dff_surprise", "term_spread_1y_10y", "vix", "credit_spread"],
            "cn": ["gdp_surprise", "cpi_surprise"],
            "source": "ALFRED/OECD vintage-tracked (PIT-safe)",
        },
        "macro_exploratory_2_not_headline": {
            "cn": ["m2_yoy", "social_financing"],
            "flag": "exploratory; snapshot+sha256; NBS via mbk-dev/nbsc (latest-only, G3)",
        },
    },
    "regime_state": {
        "role": (
            "single pre-specified interaction (score x regime_state); NOT a second "
            "falsifiability anchor (market-driver-framework.md §2/§8)"
        ),
        "composite": "equal-weight of 3 standardized layers (z-scored)",
        "meso": "US SIC-peer momentum + CN shenwan (SWFC) sector momentum, equal-weight",
        "macro": "5-line: vix + credit_spread + term_spread + dff_surprise + EPU(exploratory)",
        "global": "Diebold-Yilmaz total spillover, US<->CN index return panel",
        "normalization": (
            "expanding-as-of sigma (TACO; computed on [t0, t] fixed at each t, "
            "NO retrospective recompute)"
        ),
        "dy_spillover": {
            "window_trading_days": 250,
            "horizon_H": 10,
            "fevd": "generalized (Koop-Pesaran-Shin)",
        },
    },
    "learner": {
        "objective": "lambdarank",
        "bin_count": 5,
        "params": _FROZEN_LGBM,
    },
    "validation": {
        "method": "joint_chronological_walk_forward",
        "folds": "purged_walk_forward_splits(expanding=True, min_train_months=60, embargo=21)",
        "alignment": "per-region trading calendar; month-end cross-section sampling",
        "chronological_assert": "assert_chronological_split per-region (train.max < test.min)",
    },
    "horizon_confirmatory": 21,
    "horizon_exploratory": [10, 42],
    "embargo_sessions": 21,
    "sesoi_rank_ic": 0.010,
    "jt_gate": {
        "looks_months": [60, 90, 120],
        "rci_levels": [0.9944, 0.9764, 0.9500],
        "zk": [2.772, 2.263, 1.960],
        "rule": "RCI_k strict-containment within [-0.010,+0.010] -> equivalence",
    },
    "n_trials": 30,
    "multiplicity": {
        "dsr": "purgedcv",
        "pbo": "purgedcv CPCV",
        "spa_mcs": "arch.bootstrap",
        "haircut": "YannickKae/Evaluating-Investment-Strategies (CC0)",
    },
    "baseline": {
        "primary": "price-only S1 (momentum/reversal/vol/liquidity)",
        "secondary": "equal-weight PIT universe",
    },
    "dm_test": "portfolio return loss differential, cluster-robust SE by month (H-1 correction)",
    "scaffold": "qlib dual-region mount (REG_CN+REG_US), Python <=3.12 isolated venv",
    "a_share_ff_factor": "EXCLUDED in v1.0 (amendable via new ledger row)",
    "data_snapshot_hashes": (
        "TBD - appended in subsequent ledger rows when S0 builds data "
        "(Track B #40 -> #43 pattern); config_committed row freezes STRUCTURE only"
    ),
    "frozen_surface_isolation": (
        "new prereg line; NEVER mutates B/C/D/E1 or Track B frozen configs"
    ),
}


def config_sig(config: dict) -> str:
    """sha256 over canonical JSON (sort_keys), matching phase_b/phase_c commit_config."""
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

    row = build_row(TRACK_C_CONFIG)
    print(f"[track_c] config_sig={row['config_sig']}")
    print(f"[track_c] phase={row['phase']} event={row['event']} ledger={LEDGER}")
    print(f"[track_c] config keys={sorted(TRACK_C_CONFIG.keys())}")
    preview = {k: row[k] for k in ('ts', 'event', 'phase', 'config_sig')}
    print(f"[track_c] row preview: {json.dumps(preview)}")

    if not args.commit:
        print("[track_c] DRY-RUN (no append). Re-run with --commit to freeze.")
        return 0

    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")
    print(f"[track_c] COMMITTED -> {LEDGER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
