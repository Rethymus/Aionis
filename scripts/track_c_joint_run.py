"""Track C joint US-CN rank-IC runner (EXPLORATORY machinery proof).

Runs the joint dual-region chronological walk-forward estimator on the REAL US (track_b)
+ CN (cn_price) month-end panels, conditioned on the existing regime_state composite.
Two feature modes (env ``TRACK_C_JOINT_MODE``):
  * ``shared`` (default): 10 shared price features (``TRACK_B_PRICE_FEATURE_COLS``).
  * ``asymmetric35``: US 23 (13 EDGAR fundamentals + 10 price) + CN 12 (10 price mirror +
    2 A-share extras) = 25 unique union cols (region-missing = NaN, LightGBM default).
    Uses ``build_joint_panel`` asymmetric mode (A1, commit c98f4c8). Validates A1 on real
    data + yields an exploratory US-fundamental-signal IC point.

EXPLORATORY — NOT the Track C confirmatory claim:
  * ``asymmetric35`` lacks ``macro_headline_6`` (confirmatory needs 41 = 35 + 6 macro;
    macro fetch is A2, pending macro-7gate readiness).
  * Uses whichever regime composite currently exists in ``regime_composite.parquet``
    (2-layer or 3-layer-US-only-meso) — NOT necessarily the spec-faithful 3-layer.
  * group = region-month (currency-clean D1 default; #48 froze this per amendment #48).
  * Writes NO ledger. Confirmatory run = owner GO + new ledger row.

Anti-leakage: features are past-only (price) or filed-date PIT (EDGAR fundamentals);
forward_return_h is label-only; regime_state is PIT (TACO as-of); per-region chronological
asserted inside ``fit_track_c_joint``.

Run::

    uv run python scripts/track_c_joint_run.py                       # shared (10 price)
    TRACK_C_JOINT_MODE=asymmetric35 uv run python scripts/track_c_joint_run.py
"""

from __future__ import annotations

import json
import os

import pandas as pd

from aionis.config import settings
from aionis.eval.track_c_joint import build_joint_panel, fit_track_c_joint
from aionis.features.macro_headline import MACRO_HEADLINE_6, join_macro_to_joint_panel
from aionis.features.price_features import TRACK_B_PRICE_FEATURE_COLS

US_PANEL = settings.data_dir / "cache" / "track_b_panel.parquet"
CN_PANEL = settings.data_dir / "cache" / "cn_price_panel.parquet"
REGIME_PANEL = settings.data_dir / "cache" / "regime_composite.parquet"
WINDOW_START = "2016-01-01"  # ledger #46 universe.{us,cn}.window_start

# Asymmetric-35 feature sets (must match ledger #46/#48 feature_cols.us_fundamentals_13
# + CN extras; #48 confirmatory adds macro_headline_6 separately in A2/A3).
US_FUNDAMENTALS_13 = [
    "roa", "roe", "profit_margin", "asset_growth_1m", "asset_growth_12m",
    "revenue_growth_1m", "revenue_growth_12m", "equity_growth_1m",
    "leverage", "debt_to_equity", "book_value_per_share", "accruals",
    "investment_12m",
]
CN_EXTRAS_2 = ["limit_up_down_distance", "suspension_flag"]
US_23 = US_FUNDAMENTALS_13 + list(TRACK_B_PRICE_FEATURE_COLS)
CN_12 = list(TRACK_B_PRICE_FEATURE_COLS) + CN_EXTRAS_2
UNION_35 = sorted(set(US_23) | set(CN_12))  # 25 unique (10 shared price + 13 US fund + 2 CN extras)

MODE = os.environ.get("TRACK_C_JOINT_MODE", "shared")


def main() -> None:
    """Run the joint US-CN rank-IC estimator (exploratory, no ledger)."""
    for p in (US_PANEL, CN_PANEL, REGIME_PANEL):
        if not p.exists():
            raise SystemExit(f"[ERROR] missing {p}")

    if MODE == "asymmetric35":
        print(
            f"[S] building ASYMMETRIC joint panel "
            f"(US 23 / CN 12 -> union {len(UNION_35)} unique)...",
            flush=True,
        )
        joint = build_joint_panel(
            US_PANEL,
            CN_PANEL,
            feature_cols=[],
            us_feature_cols=US_23,
            cn_feature_cols=CN_12,
            window_start=WINDOW_START,
        )
        feature_cols_for_fit = UNION_35
        mode_tag = "asym35"
        mode_caveat = (
            "exploratory: 35 asymmetric per-ticker (US 23 fund+price / CN 12 price+extras; "
            "macro 6 pending A2)"
        )
    elif MODE == "asymmetric41":
        print(
            f"[S] building ASYMMETRIC joint panel + joining macro_headline_6 "
            f"(US 23 / CN 12 + macro 6 -> {len(UNION_35) + len(MACRO_HEADLINE_6)} unique)...",
            flush=True,
        )
        joint = build_joint_panel(
            US_PANEL,
            CN_PANEL,
            feature_cols=[],
            us_feature_cols=US_23,
            cn_feature_cols=CN_12,
            window_start=WINDOW_START,
        )
        joint = join_macro_to_joint_panel(joint)
        feature_cols_for_fit = UNION_35 + MACRO_HEADLINE_6
        mode_tag = "asym41"
        mode_caveat = (
            "confirmatory-spec 41 (US 23 + CN 12 + macro_headline_6); "
            "GDP NaN (annual releases < Z_MIN, data limit)"
        )
    elif MODE == "shared":
        print("[S] building SHARED joint panel (10 price)...", flush=True)
        joint = build_joint_panel(
            US_PANEL, CN_PANEL,
            feature_cols=TRACK_B_PRICE_FEATURE_COLS, window_start=WINDOW_START,
        )
        feature_cols_for_fit = list(TRACK_B_PRICE_FEATURE_COLS)
        mode_tag = "shared10"
        mode_caveat = "exploratory: 10 shared price feats (confirmatory needs full #48 41 cols)"
    else:
        raise SystemExit(
            f"[ERROR] unknown TRACK_C_JOINT_MODE={MODE!r}; use 'shared' or 'asymmetric35'"
        )

    print(
        f"[S] joint panel: {joint.shape} | dates {joint['date'].min()}..{joint['date'].max()} "
        f"| regions {dict(joint['region'].value_counts())}",
        flush=True,
    )
    print(
        f"[S] feature_cols ({len(feature_cols_for_fit)}, mode={MODE}): {feature_cols_for_fit}",
        flush=True,
    )

    regime_df = pd.read_parquet(REGIME_PANEL)
    if "regime_state" not in regime_df.columns:
        raise SystemExit(
            f"[ERROR] {REGIME_PANEL} has no 'regime_state' column: {regime_df.columns}"
        )
    regime_df.index = pd.to_datetime(regime_df.index)
    regime_state = regime_df["regime_state"].sort_index()
    print(
        f"[S] regime_state: n={len(regime_state)} valid={int(regime_state.notna().sum())}",
        flush=True,
    )

    print(
        f"[S] fitting joint walk-forward (lambdarank, region-month groups, mode={MODE})...",
        flush=True,
    )
    result = fit_track_c_joint(
        panel=joint,
        feature_cols=feature_cols_for_fit,
        regime_state=regime_state,
        horizon=21,
        min_train_months=60,
        embargo_sessions=21,
        bin_count=5,
    )

    lo, hi = result.ci_95
    print(f"=== Track C joint US-CN rank-IC (EXPLORATORY, mode={MODE}) ===", flush=True)
    print(
        f"  n_folds: {result.n_walk_folds}   n_months(IC): {len(result.combined_ic_series)}",
        flush=True,
    )
    print(
        f"  combined mean_ic: {result.mean_ic:.6f}   ci_95: ({lo:.6f}, {hi:.6f})   "
        f"t_hac: {result.t_hac:.4f}   p_hac: {result.p_hac:.4f}",
        flush=True,
    )
    print(
        f"  us_ic mean: {result.us_ic_series.mean():.6f} (n={len(result.us_ic_series)})   "
        f"cn_ic mean: {result.cn_ic_series.mean():.6f} (n={len(result.cn_ic_series)})",
        flush=True,
    )
    print("  --- conditional-IC (combined_ic ~ regime, HAC) ---", flush=True)
    print(
        f"  alpha: {result.cond_alpha:.6f} (p={result.cond_alpha_p:.4f})   "
        f"beta(interaction): {result.cond_beta:.6f} (p={result.cond_beta_p:.4f})   "
        f"R^2: {result.cond_r_squared:.4f}   n={result.cond_n_months}",
        flush=True,
    )

    out_dir = settings.data_dir.parent / "runs"
    out_dir.mkdir(parents=True, exist_ok=True)
    result.oos_scores.to_parquet(out_dir / f"track_c_joint_{mode_tag}_oos_scores.parquet")
    pd.concat(
        [
            result.us_ic_series.rename("us"),
            result.cn_ic_series.rename("cn"),
            result.combined_ic_series.rename("combined"),
        ],
        axis=1,
        sort=True,
    ).to_parquet(out_dir / f"track_c_joint_{mode_tag}_ic_series.parquet")
    (out_dir / f"track_c_joint_{mode_tag}_summary.json").write_text(
        json.dumps(
            {
                "mode": MODE,
                "n_folds": result.n_walk_folds,
                "n_months_ic": len(result.combined_ic_series),
                "combined_mean_ic": result.mean_ic,
                "ci_95": list(result.ci_95),
                "t_hac": result.t_hac,
                "p_hac": result.p_hac,
                "us_ic_mean": float(result.us_ic_series.mean()),
                "cn_ic_mean": float(result.cn_ic_series.mean()),
                "cond_alpha": result.cond_alpha,
                "cond_alpha_p": result.cond_alpha_p,
                "cond_beta": result.cond_beta,
                "cond_beta_p": result.cond_beta_p,
                "cond_r_squared": result.cond_r_squared,
                "cond_n_months": result.cond_n_months,
                "feature_cols_union_count": len(feature_cols_for_fit),
                "caveats": [
                    mode_caveat,
                    "exploratory: regime from regime_composite.parquet (CN meso pending 7-gate)",
                    "exploratory: group=region-month (D1, #48 frozen)",
                    "NO ledger; NOT the confirmatory claim",
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        f"[S] saved -> {out_dir}/track_c_joint_{mode_tag}_{{oos_scores,ic_series,summary}}",
        flush=True,
    )
    print("[S] DONE (exploratory; no ledger)", flush=True)


if __name__ == "__main__":
    if os.environ.get("PHASE_C_NO_LEDGER") == "1":
        print("[S] ARTIFACTS-ONLY (exploratory; never writes ledger)", flush=True)
    main()
