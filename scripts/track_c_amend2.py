#!/usr/bin/env python3
"""Track C amendment #48 — confirmatory GO (owner D1=A 2026-08-05).

Owner signed D1=A on 2026-08-05 (reports/design/2026-08-05-track-c-confirmatory-go-brief.md):
retain the joint US-CN chronological walk-forward machinery; narrow meso to US-only SIC
(Lane A 2026-08-04 verdict: CN shenwan baostock G3-fail -> exploratory-only); freeze the
confirmatory estimand's group construction, IC aggregation, feature_cols (41 asymmetric),
and baostock G3 strategy. This row ENABLES the first confirmatory OOS run (still requires a
separate owner GO to execute the run + observe outcomes).

Cumulative on #46 (original freeze) + #47 (cninfo -> exploratory). The frozen rows are
unchanged (durable-registry / append-only). Reuses the tested config_sig mechanism
(sha256(json.dumps(config, sort_keys=True))) via track_c_commit / track_c_amend1.

Default = DRY-RUN; --commit appends ledger row #48. Observes NO OOS metric.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from track_c_amend1 import build_amendment as build_amendment_47
from track_c_commit import LEDGER, PHASE, config_sig

AMENDMENT_NOTE = (
    "#46/#47 -> #48 confirmatory GO (owner D1=A 2026-08-05): retain joint fold machinery; "
    "meso narrowed to US-only SIC (CN shenwan G3-fail per Lane A 2026-08-04 shenwan-meso-7gate); "
    "confirmatory feature_cols = 41 (US 23 fundamentals+price + CN 12 price-only + macro 6; "
    "cn_fundamentals exploratory per #47); group = region-month (D2 spec); joint IC = "
    "equal-weight per-region IC (D3 spec); baostock G3 adjustflag=3 raw frozen. Enables first "
    "confirmatory OOS (separate owner GO + this row)."
)


def build_amendment() -> dict:
    """Cumulative: #46 + #47 (cninfo exploratory) + #48 (confirmatory GO)."""
    cfg = build_amendment_47()  # apply #47 first (cumulative on #46)

    cfg["claim"] = (
        "dual-region (US S&P500 + CN CSI300) JOINT chronological walk-forward cross-sectional "
        "monthly rank-IC; confirmatory feature_cols = US 23 (13 fundamentals EDGAR-filed-date "
        "+ 10 price) + CN 12 (price-only; cn_fundamentals exploratory per amendment #47) + "
        "macro_headline 6 = 41; single pre-specified interaction score x regime_state "
        "(multiplicity budget 1); group = region-month; joint IC = equal-weight per-region IC; "
        "meso = US-only SIC (CN shenwan exploratory per Lane A G3-fail); null-favored"
    )

    cfg["regime_state"]["meso"] = (
        "US SIC-peer momentum ONLY (confirmatory headline); CN shenwan (SWFC) EXPLORATORY-ONLY "
        "(G3-fail per Lane A 2026-08-04 shenwan-meso-7gate verdict: baostock no as-of/vintage, "
        "SWFC backfill)"
    )

    cfg["confirmatory_go"] = {
        "owner_authorization": (
            "D1=A 2026-08-05 (retain joint fold; feature_cols 41 asymmetric)"
        ),
        "d1_estimator": (
            "joint chronological walk-forward "
            "(retain #46 section 5 machinery; src/aionis/eval/track_c_joint.py)"
        ),
        "d2_group": (
            "region-month: (year*12+month-1)*2 + region_code (US=0, CN=1); "
            "per-region ranking (US vs US, CN vs CN) -> currency-clean labels; "
            "joint model fit with shared params"
        ),
        "d3_joint_ic": "equal-weight of per-region monthly IC: mean(us_ic_t, cn_ic_t)",
        "d4_feature_cols": {
            "count": 41,
            "us_confirmatory_23": (
                "us_fundamentals_13 (EDGAR filed-date PIT) + us_price_10 (Tiingo/Alpaca)"
            ),
            "cn_confirmatory_12": (
                "cn_price_12 = us_price_10 mirror + limit_up_down_distance + "
                "suspension_flag (baostock raw)"
            ),
            "macro_confirmatory_6": (
                "macro_headline_6 (US: dff_surprise, term_spread, vix, credit_spread; "
                "CN: gdp_surprise, cpi_surprise; ALFRED/OECD vintage-safe)"
            ),
            "cn_fundamentals_exploratory": (
                "NOT in confirmatory headline (amendment #47: cninfo G1 exploratory-only)"
            ),
            "regime_interaction_1": (
                "regime_state (3-layer composite: meso-US-SIC + macro-5line + "
                "global-DY spillover); single pre-specified interaction "
                "score x regime_state; multiplicity budget 1"
            ),
            "asymmetry_note": (
                "US 23 vs CN 12; LightGBM default handles CN-row US-fundamental as missing"
            ),
        },
        "d5_meso": "US-only SIC (this amendment; CN shenwan exploratory-only per Lane A)",
        "d6_go": (
            "owner GO + this config_committed row -> first confirmatory OOS run "
            "authorized (run execution still a separate owner GO)"
        ),
        "baostock_g3_strategy": (
            "adjustflag='3' raw (frozen); local factor snapshot; "
            "NO backfill (CN price PIT dependency)"
        ),
        "estimator_artifact": (
            "src/aionis/eval/track_c_joint.py (fit_track_c_joint + build_joint_panel; "
            "9/9 anti-degeneracy tests; H6 bit-identical asserted)"
        ),
    }
    return cfg


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--commit", action="store_true", help="append the row (default: dry-run)")
    args = ap.parse_args()

    cfg = build_amendment()
    sig = config_sig(cfg)
    row = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": "config_committed",
        "phase": PHASE,
        "config_sig": sig,
        "amends": AMENDMENT_NOTE,
        "config": cfg,
    }
    print(f"[track_c-amend2] config_sig={sig}")
    print(f"[track_c-amend2] amends={AMENDMENT_NOTE[:100]}...")
    print(f"[track_c-amend2] claim now: {cfg['claim'][:100]}...")
    print(f"[track_c-amend2] meso now: {cfg['regime_state']['meso'][:80]}...")
    print(f"[track_c-amend2] confirmatory_go keys: {sorted(cfg['confirmatory_go'].keys())}")
    fc_count = cfg["confirmatory_go"]["d4_feature_cols"]["count"]
    print(f"[track_c-amend2] feature_cols count: {fc_count}")

    if not args.commit:
        print("[track_c-amend2] DRY-RUN (no append). Re-run with --commit to append ledger #48.")
        return 0

    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")
    print(f"[track_c-amend2] COMMITTED -> {LEDGER} (amendment row, #48)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
