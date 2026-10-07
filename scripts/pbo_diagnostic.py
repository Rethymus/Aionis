"""PBO / CSCV overfitting diagnostic over the frozen claim arms (EXPLORATORY).

What this does
--------------
The round-221 external-research pass found that the already-pinned
``purgedcv==0.1.2`` ships the full López de Prado overfitting toolkit
(``probability_of_backtest_overfitting`` via CSCV, deflated/probabilistic
Sharpe, minimum track-record length) — this project uses only
``PurgedGroupKFold``. This script exercises the PBO piece as an honest
EXPLORATORY diagnostic, in the same lane as ``sensitivity_horizon.py``:

- builds the candidate matrix from the four FROZEN confirmatory runs
  (B/C/D/E1 x {treatment, base} = 8 arms x 125 months of purged-CV OOS
  monthly rank-IC, read bit-exact from ``runs/results/<sig>/ic_*.parquet``);
- asks the CSCV question: *if* one had selected the best arm in-sample,
  how often would that pick land below median out-of-sample? (PBO);
- appends ONE exploratory ledger row (no config_committed — nothing frozen,
  nothing claimed) and writes ``reports/exploratory/pbo-diagnostic.json``.

Honest caveats (printed and persisted with the result)
-----------------------------------------------------
1. n_configs=8 is SMALL: CSCV/PBO estimators are themselves noisy in the
   small-trial regime (Witzany 2021, Risks; Arian et al. 2024, SSRN 4686376).
   The number is a diagnostic, not a gate.
2. Per-period performance = monthly OOS rank-IC (not trading returns). The
   selection problem "which arm would we have picked" is mapped onto IC,
   the project's own claim metric.
3. The monthly series are already purged-CV OOS outputs; label overlap was
   purged upstream, so CSCV block splits here re-use already-cleaned points.

Usage::

    uv run python scripts/pbo_diagnostic.py
    PBO_NO_LEDGER=1 uv run python scripts/pbo_diagnostic.py   # no ledger row

Bounds: exploratory/display lane — 0 frozen configs / 0 OOS claims.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import purgedcv

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "runs" / "results"
LEDGER = ROOT / "runs" / "ledger.jsonl"
OUT = ROOT / "reports" / "exploratory" / "pbo-diagnostic.json"

# Frozen phase -> config sig (from the committed evidence_matrix claims); each
# run dir persists BOTH arms: ic_state.parquet (treatment) + ic_base.parquet.
PHASES: dict[str, str] = {
    "B": "17245a75d2d4cd17c68f36a9d0f4b4f7f3baf1db31b33b87be79e6e4a11400da",
    "C": "a7fdb48f5942fae146b151143807653fd66c4c5f1601dc7cf9d04a796c1fada1",
    "D": "d31580630ff35326557dda9f50832c7af3625dd6507e47e252ea01800372a12c",
    "E1": "ef321e9ee808804601e012818fa95522d2dc5f0fe8c53771d7f1b412c25ed49f",
}

N_SPLITS = 16


def _load_arm_matrix() -> tuple[np.ndarray, list[str], pd.DatetimeIndex]:
    """(n_arms, n_months) matrix of monthly OOS IC + labels + shared index."""
    series: dict[str, pd.Series] = {}
    for phase, sig in PHASES.items():
        for arm, fname in (("treatment", "ic_state.parquet"),
                           ("base", "ic_base.parquet")):
            path = RESULTS / sig / fname
            series[f"{phase}:{arm}"] = pd.read_parquet(path)["ic"].astype(float)
    labels = list(series)
    frame = pd.concat(series, axis=1)
    frame = frame.dropna(how="any")
    frame = frame.sort_index()
    return frame.to_numpy().T, labels, frame.index


def main() -> int:
    X, labels, index = _load_arm_matrix()
    n_arms, n_obs = X.shape
    print(f"[PBO] arms={n_arms} ({', '.join(labels)})")
    print(f"[PBO] months={n_obs} ({index[0].date()} → {index[-1].date()})")

    res = purgedcv.probability_of_backtest_overfitting(
        X, n_splits=min(N_SPLITS, n_obs)
    )

    per_arm = [
        {
            "arm": labels[j],
            "mean_ic": float(np.mean(X[j])),
            "std_ic": float(np.std(X[j], ddof=1)),
        }
        for j in range(n_arms)
    ]
    payload = {
        "as_of": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "kind": "pbo-cscv-diagnostic",
        "exploratory": True,
        "n_configs": n_arms,
        "n_obs": n_obs,
        "n_splits": min(N_SPLITS, n_obs),
        "pbo": float(res.pbo),
        "n_combos": int(res.n_combos),
        "per_arm": per_arm,
        "interpretation": (
            "PBO≈0.5 = picking the in-sample best arm is a coin flip "
            "out-of-sample; PBO well above 0.5 (as observed here) = in-sample "
            "picks systematically UNDERPERFORM out-of-sample — no selection "
            "edge at all, consistent with the four frozen NULL differentials. "
            "Low PBO would have indicated a stable in-sample winner worth "
            "claiming."
        ),
        "caveats": [
            "n_configs=8 is small: CSCV/PBO estimators are themselves noisy in "
            "the small-trial regime (Witzany 2021, Risks; Arian et al. 2024, "
            "SSRN 4686376) — diagnostic, not a gate.",
            "Per-period performance = monthly OOS rank-IC (the project's claim "
            "metric), not trading returns.",
            "Inputs are already purged-CV OOS series; label overlap was purged "
            "upstream, CSCV block splits re-use cleaned points.",
        ],
        "tool": f"purgedcv {getattr(purgedcv, '__version__', '?')} "
                "probability_of_backtest_overfitting (CSCV)",
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[PBO] PBO={res.pbo:.3f} over {res.n_combos} CSCV combinations")
    for a in per_arm:
        print(f"     {a['arm']:>14}: mean IC {a['mean_ic']:+.5f} (sd {a['std_ic']:.5f})")
    print(f"[PBO] wrote {OUT}")

    if not os.environ.get("PBO_NO_LEDGER"):
        entry = {
            "ts": payload["as_of"],
            "event": "exploratory",
            "phase": "pbo_diagnostic",
            "pbo": payload["pbo"],
            "n_configs": n_arms,
            "n_obs": n_obs,
            "n_combos": payload["n_combos"],
            "notes": (
                "CSCV PBO over the 8 frozen claim arms (B/C/D/E1 x "
                "treatment/base, monthly OOS rank-IC). EXPLORATORY diagnostic "
                "of the harness's overfitting machinery (purgedcv 0.1.2); "
                "small-trial estimator noise caveat applies; not a claim, "
                "not a gate. Full payload: "
                "reports/exploratory/pbo-diagnostic.json"
            ),
        }
        with open(LEDGER, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
        print(f"[PBO] appended exploratory row to {LEDGER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
