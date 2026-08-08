#!/usr/bin/env python3
"""Track Adaptive config_committed freeze (HIGH-1 anti-leakage anchor).

Writes the Track Adaptive frozen config's sha256 to ``runs/ledger.jsonl`` BEFORE
any OOS IC_diff is observed (CLAUDE.md: config_committed BEFORE result). Mirrors
the tested ``commit_config`` mechanism in ``scripts/track_c_commit.py`` /
``scripts/phase_b_run.py`` (sig = sha256(json.dumps(config, sort_keys=True))).

Owner authorized 2026-08-08 ("全默认" = D1-D6 all recommended defaults, incl. D6
GO). This reverses the 2026-08-05 option-A "don't chase new alpha" lock for THIS
specific disciplined path only (memory aionis-publication-framing-option-a 2026-
08-08 addendum). Pre-reg: ``docs/track-adaptive-preregistration.md``.

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
PHASE = "track_adaptive"

# LightGBM frozen params — IDENTICAL to Track C / Phase B frozen family so the
# only treatment variable is the update cadence (not the learner).
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

# Track C confirmatory substrate — the adaptive learner reuses this EXACT frozen
# surface as its feature/universe/learner substrate (zero change → isolates
# "update cadence" as the single treatment variable). The runner resolves the
# concrete feature_cols via ``scripts/track_c_amend2.py::build_amendment()``.
_TRACK_C_FROZEN_SIG = "e14b9d445411e74cc3418af3bde1148163725875b01ab75175bdde002225e738"

TRACK_ADAPTIVE_CONFIG: dict = {
    "track": "adaptive",
    "claim": (
        "two-tailed, null-expected: does expanding-window monthly refit change "
        "monthly cross-sectional rank-IC vs the FROZEN Track-C baseline? "
        "IC_diff = mean(IC_adaptive) - mean(IC_frozen), paired per month per "
        "region, HAC inference, two-tailed. Honest expectation = null (power "
        "floor sigma(IC)~0.10; Gu-Kelly-Xiu 2020 update-frequency non-dominance)."
    ),
    "estimand": {
        "name": "IC_diff",
        "definition": (
            "mean over OOS months of (IC_adaptive_t - IC_frozen_t), paired per "
            "month per region; IC = cross-sectional Spearman(score, fwd_return_h)"
        ),
        "inference": "HAC (Newey-West) regression d_t ~ 1; two-tailed",
        "baseline": (
            f"Track C confirmatory #49 (frozen config sig {_TRACK_C_FROZEN_SIG}); "
            "IC_frozen reproduced bit-identically (H6). The baseline is FROZEN by "
            "definition — never refit."
        ),
    },
    "mechanism": {
        "owner_decision": "D1 = A (expanding-window refit; GKX 2020 standard)",
        "cadence": "monthly — refit at each OOS month start",
        "fit_window": (
            "expanding: all realized panel rows with date < month_start(t), "
            "purge + embargo(21 sessions) applied; min_train_months=60"
        ),
        "alternatives_not_run_this_config": [
            "B_online_gbm (river/online GBM)",
            "C_rolling_window (fixed-length)",
        ],
    },
    "universe": (
        "identical to Track C frozen (US S&P 500 + CN CSI300 PIT, "
        "window_start 2016-01-01) — D2; ensures clean pairing with IC_frozen"
    ),
    "feature_cols": (
        f"identical to Track C frozen config sig {_TRACK_C_FROZEN_SIG} (41 "
        "asymmetric cols: US 23 + CN 12 + macro 6 + regime 3); ZERO change to "
        "isolate update cadence as the single treatment variable. Runner "
        "resolves via track_c_amend2.build_amendment()."
    ),
    "learner": {
        "objective": "lambdarank",
        "bin_count": 5,
        "params": _FROZEN_LGBM,
        "note": "same frozen family as Track C; only the refit cadence differs",
    },
    "validation": {
        "method": "chronological walk-forward with expanding-window refit",
        "oos_window": "Track C OOS months (paired with IC_frozen) — D2",
        "purge_embargo": "embargo=21 sessions; min_train_months=60 (reuse Track C)",
        "chronological_assert": "fit.max(date) < predict.month_start(t), per region",
    },
    "horizon": 21,
    "sesoi_diff": 0.010,  # D3; revisit only via a new ledger row
    "gates": {
        "primary": (
            "two-tailed HAC p-value on mean(IC_diff); alpha=0.05; expected NOT "
            "to reject H0 (null)"
        ),
        "secondary_equivalence": (
            "RCI of IC_diff within +/-sesoi_diff (examined only if primary is "
            "null); explicitly NOT a rescue path (rerun-to-significance forbidden)"
        ),
    },
    "n_trials": 1,  # this run evaluates ONE strategy (mechanism A, frozen hyperparams, no sweep)
    "n_trials_note": (
        "Corrects pre-reg D4 (~77): refit cycles are the OOS walk-forward of ONE "
        "strategy, not independent trials. n_trials = strategy variants evaluated. "
        "Bumping (e.g. adding mechanism B/C or a hyperparam sweep) requires a new "
        "config_committed row."
    ),
    "multiplicity": {
        "dsr": (
            "src/aionis/eval/deflated_sharpe.py::deflated_sharpe_ratio "
            "(Bailey-Lopez de Prado 2014); applied with n_trials above"
        ),
        "pbo": "deflated_sharpe.probability_of_backtest_overfit (CSCV); reported",
        "rule": (
            "any observed IC improvement reported RAW and DEFLATED; the deflated "
            "value is the claim-bearing number"
        ),
    },
    "h6_determinism": {
        "n_jobs": 1,
        "seed": 0,
        "version_pinned": "uv.lock",
        "assert": "IC_adaptive series + raw scores bit-identical across reruns",
    },
    "frozen_surface_isolation": (
        "new prereg line (docs/track-adaptive-preregistration.md); NEVER mutates "
        "Track C / B(seven-theme) / D / E1 frozen configs or ledger rows; the "
        "Track-C climax (#49, combined rank-IC -0.0088 null) stands unchanged"
    ),
    "honest_expectation": (
        "null. Value = disciplined adaptive infrastructure + leakage-safe "
        "honest tracking, NOT manufacturing positive IC. A null IC_diff is a "
        "second independent null that REINFORCES the power-floor conclusion."
    ),
}


def config_sig(config: dict) -> str:
    """sha256 over canonical JSON (sort_keys), matching track_c/phase_b commit_config."""
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
    print(f"[track_adaptive] config_sig={row['config_sig']}")
    print(f"[track_adaptive] phase={row['phase']} event={row['event']} ledger={LEDGER}")
    print(f"[track_adaptive] config keys={sorted(TRACK_ADAPTIVE_CONFIG.keys())}")
    preview = {k: row[k] for k in ("ts", "event", "phase", "config_sig")}
    print(f"[track_adaptive] row preview: {json.dumps(preview)}")

    if not args.commit:
        print("[track_adaptive] DRY-RUN (no append). Re-run with --commit to freeze.")
        return 0

    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")
    print(f"[track_adaptive] COMMITTED -> {LEDGER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
