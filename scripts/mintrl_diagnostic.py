"""minTRL diagnostic — how long a track record would the Track C IC need?

Second, independent angle on the power story (the J-T look analysis in
RESULTS §0 already says the frozen 60/90/120-month schedule needs ~36+ years
to declare equivalence). Here we ask the complementary Bailey & López de
Prado (2012) question with ``purgedcv.min_track_record_length``:

    given the observed annualized IC-IR of the realized Track C combined
    monthly series, how many months n* would make PSR(target=0) >= 95%?

A tiny/negative observed Sharpe yields an astronomically large (or undefined)
n* — which is precisely the corroboration: the realized series cannot
distinguish itself from zero at any practical horizon.

EXPLORATORY diagnostic (ledger row + report json); not a claim, not a gate.

Usage::

    uv run python scripts/mintrl_diagnostic.py
    MINTRL_NO_LEDGER=1 uv run python scripts/mintrl_diagnostic.py
"""
from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import purgedcv

ROOT = Path(__file__).resolve().parent.parent
SERIES = ROOT / "web" / "src" / "data" / "aionis" / "ic_monthly.json"
OUT = ROOT / "reports" / "exploratory" / "mintrl-diagnostic.json"
LEDGER = ROOT / "runs" / "ledger.jsonl"

ALPHA = 0.05  # 95% one-sided (PSR >= 1 - alpha)
MONTHS_PER_YEAR = 12


def _main() -> int:
    rows = json.loads(SERIES.read_text(encoding="utf-8"))
    ic = [r["combined"] for r in rows if r["combined"] is not None]
    x = np.asarray(ic, dtype=float)
    n = len(x)
    mean, sd = float(x.mean()), float(x.std(ddof=1))
    skew = float(((x - mean) ** 3).mean() / sd**3)
    kurt = float(((x - mean) ** 4).mean() / sd**4)
    sharpe_annual = (mean / sd) * math.sqrt(MONTHS_PER_YEAR)

    try:
        n_star_months = purgedcv.min_track_record_length(
            observed_sharpe=sharpe_annual / math.sqrt(MONTHS_PER_YEAR),
            target_sharpe=0.0, alpha=ALPHA, skew=skew, kurtosis=kurt,
        )
        note = None
    except Exception as exc:  # negative/degenerate observed Sharpe
        n_star_months = None
        note = f"minTRL undefined for this input ({exc})"
    if n_star_months is not None and math.isinf(n_star_months):
        # observed IC-IR below target -> PSR(0) < 50% at ANY n. Serialize
        # strictly (no bare Infinity tokens — the 09-11 strict-JSON lesson).
        n_star_months = None
        note = (
            "minTRL is INFINITE: the observed annualized IC-IR is below the "
            "target (0), so PSR never reaches 1-alpha at any finite record "
            "length — no horizon makes this series claim-worthy."
        )

    payload = {
        "as_of": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "kind": "mintrl-diagnostic",
        "exploratory": True,
        "series": "ic_monthly.json combined (realized Track C monthly IC)",
        "n_months_realized": n,
        "mean_ic": mean,
        "sd_ic": sd,
        "skew": skew,
        "kurtosis": kurt,
        "sharpe_annualized_ic_ir": sharpe_annual,
        "alpha": ALPHA,
        "target_sharpe": 0.0,
        "min_track_record_months": n_star_months,
        "min_track_record_years": (n_star_months / MONTHS_PER_YEAR
                                   if n_star_months else None),
        "interpretation": (
            "minTRL is the record length at which the observed IC-IR would "
            "first become statistically distinguishable from zero at 95%. "
            "An astronomically large or undefined n* corroborates, from a "
            "second estimator (Bailey & Lopez de Prado 2012), the J-T "
            "look analysis conclusion: no practical horizon makes this "
            "series claim-worthy — the honest deliverable is the null."
        ),
        "note": note,
        "tool": f"purgedcv {getattr(purgedcv, '__version__', '?')} "
                "min_track_record_length (Bailey-LdP 2012 Eq. 11)",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    years = payload["min_track_record_years"]
    print(f"[minTRL] realized months={n}  mean IC={mean:+.5f}  sd={sd:.5f}  "
          f"annualized IC-IR={sharpe_annual:+.3f}")
    if years is not None:
        print(f"[minTRL] n* = {payload['min_track_record_months']:,} months "
              f"(≈{years:,.0f} years) for PSR(0) >= {1 - ALPHA:.0%}")
    else:
        print(f"[minTRL] n* unavailable — {note}")
    print(f"[minTRL] wrote {OUT}")

    if not os.environ.get("MINTRL_NO_LEDGER"):
        entry = {
            "ts": payload["as_of"],
            "event": "exploratory",
            "phase": "mintrl_diagnostic",
            "n_months_realized": n,
            "sharpe_annualized_ic_ir": sharpe_annual,
            "min_track_record_months": n_star_months,
            "notes": (
                "Bailey-LdP 2012 minTRL on the realized Track C combined "
                "monthly IC (committed panel ic_monthly.json). EXPLORATORY "
                "corroboration of the power story; not a claim, not a gate. "
                "Full payload: reports/exploratory/mintrl-diagnostic.json"
            ),
        }
        with open(LEDGER, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
        print(f"[minTRL] appended exploratory row to {LEDGER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
